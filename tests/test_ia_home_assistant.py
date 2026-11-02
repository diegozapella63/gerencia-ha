"""A leitura por IA de verdade (sem simulação), contra um Home Assistant de mentira: o pedido ai_task.generate_data,
os anexos na pasta media (as páginas da câmera juntas), o PDF que a IA não aceita e os erros."""
import base64
import json
import os
import unittest

from tests.base import ServidorFalso, importar_servidor
S = importar_servidor()

JPG = b"\xff\xd8\xff\xe0" + b"\1" * 300 + b"\xff\xd9"
B64 = "data:image/jpeg;base64," + base64.b64encode(JPG).decode()
RESPOSTA = {"lancamentos": [{"tipo": "despesa", "descricao": "Farmácia", "valor": "32,50", "data": "2026-11-01"}], "investimentos": []}


class TestIAReal(unittest.TestCase):
    def setUp(self):
        self.vistos = []  # os anexos que existiam na pasta media quando o HA foi chamado

        def gerar(handler, corpo):
            p = json.loads(corpo)
            for a in p.get("attachments") or []:
                rel = a["media_content_id"].split("media-source://media_source/local/", 1)[1]
                self.vistos.append((a["media_content_type"], os.path.isfile(os.path.join(S.MEDIA_ROOT, rel))))
            return self.responder(p)

        self.responder = lambda p: (200, {"service_response": {"data": RESPOSTA}})
        self.ha = ServidorFalso({"/services/ai_task/generate_data": gerar, "/states": (200, [])})
        self._salvo = (S.IA_MOCK, S.TOKEN, S.HA_API)
        S.IA_MOCK, S.TOKEN, S.HA_API = False, "token-teste", self.ha.url
        S.salvar(S.vazio(), versao=False)

    def tearDown(self):
        S.IA_MOCK, S.TOKEN, S.HA_API = self._salvo
        self.ha.fechar()

    def pedido(self):
        return json.loads(self.ha.pedidos[-1][3])

    def test_texto(self):
        r = S.ia_ler({"modo": "auto", "dica": "caixa", "texto": "farmácia 32,50"})
        self.assertEqual([(l["descricao"], l["valor"]) for l in r["lancamentos"]], [("Farmácia", 32.5)])
        p = self.pedido()
        self.assertEqual(p["task_name"], "GerencIA: ler lançamentos e investimentos")
        self.assertNotIn("attachments", p)
        self.assertIn("farmácia 32,50", p["instructions"])
        self.assertEqual(self.ha.pedidos[-1][2]["Authorization"], "Bearer token-teste")
        self.assertEqual(r["entidade"], "padrão do Home Assistant")

    def test_entidade_escolhida(self):
        d = S.vazio()
        d["ajustes"]["ia_entidade"] = "ai_task.minha_ia"
        S.salvar(d, versao=False)
        S.ia_ler({"modo": "auto", "texto": "x"})
        self.assertEqual(self.pedido()["entity_id"], "ai_task.minha_ia")

    def test_varias_paginas_vao_juntas_e_sao_apagadas(self):
        S.ia_ler({"modo": "auto", "dica": "caixa", "anexos": [{"b64": B64}] * 3})
        p = self.pedido()
        self.assertEqual(len(p["attachments"]), 3)
        self.assertEqual(self.vistos, [("image/jpeg", True)] * 3, "os arquivos existem enquanto a IA lê")
        self.assertIn("páginas do mesmo documento", p["instructions"])
        pasta = os.path.join(S.MEDIA_ROOT, S.IA_TMP_REL)
        self.assertEqual(os.listdir(pasta), [], "e somem depois")
        self.assertEqual(S.resumo_uso()["recent"][0]["images"], 3, "o uso conta as 3 imagens")

    def test_uma_pagina_nao_fala_de_paginas(self):
        S.ia_ler({"modo": "auto", "anexo": {"b64": B64}})
        p = self.pedido()
        self.assertEqual(len(p["attachments"]), 1)
        self.assertNotIn("páginas do mesmo documento", p["instructions"])

    def pdf(self, texto):
        return base64.b64encode(b"%PDF-1.4\n1 0 obj<<>>stream\nBT /F1 12 Tf (" + texto.encode() + b") Tj ET\nendstream endobj\n%%EOF").decode()

    def test_ia_que_nao_aceita_pdf_le_o_texto_do_pdf(self):
        chamadas = []

        def responder(p):
            chamadas.append(p)
            if p.get("attachments"):
                return (400, {"message": "This entity does not support attachments"})
            return (200, {"service_response": {"data": RESPOSTA}})

        self.responder = responder
        r = S.ia_ler({"modo": "auto", "anexo": {"b64": self.pdf("Fatura de exemplo: Farmacia 32,50 em 01/11; Mercado 120,00 em 03/11; Posto 200,00 em 05/11")}})
        self.assertEqual(len(chamadas), 2, "tenta de novo só com o texto")
        self.assertNotIn("attachments", chamadas[1])
        self.assertIn("Mercado 120,00", chamadas[1]["instructions"])
        self.assertTrue(r["lancamentos"])

    def test_pdf_sem_texto_legivel_pede_um_print(self):
        self.responder = lambda p: (400, {"message": "This entity does not support attachments"}) if p.get("attachments") else (200, {"service_response": {"data": RESPOSTA}})
        with self.assertRaisesRegex(ValueError, "tente um print da fatura"):
            S.ia_ler({"modo": "auto", "anexo": {"b64": self.pdf("curto")}})

    def test_imagem_recusada_nao_tenta_de_novo(self):
        self.responder = lambda p: (400, {"message": "This entity does not support attachments"})
        with self.assertRaisesRegex(ValueError, "does not support attachments"):
            S.ia_ler({"modo": "auto", "anexo": {"b64": B64}})
        self.assertEqual(len(self.ha.pedidos), 1)

    def test_erros_do_home_assistant(self):
        self.responder = lambda p: (500, {"message": "Quota exceeded for model"})
        with self.assertRaisesRegex(ValueError, "Quota exceeded"):
            S.ia_ler({"modo": "auto", "texto": "x"})
        self.assertEqual(S.resumo_uso()["today"]["quota"] >= 1, True, "conta como sem cota")
        self.responder = lambda p: (200, {"service_response": {}})
        with self.assertRaisesRegex(ValueError, "não devolveu resposta"):
            S.ia_ler({"modo": "auto", "texto": "x"})
        self.responder = lambda p: (200, {"service_response": {"data": "não é json"}})
        with self.assertRaisesRegex(ValueError, "Não deu para entender"):
            S.ia_ler({"modo": "auto", "texto": "x"})

    def test_sem_acesso(self):
        S.TOKEN = None
        with self.assertRaises((ValueError, S.ErroHA)):
            S.ia_ler({"modo": "auto", "texto": "x"})


if __name__ == "__main__":
    unittest.main()
