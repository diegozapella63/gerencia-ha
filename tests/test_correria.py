"""O CorrerIA (WhatsApp, Claude e Gemini) no GerencIA: a chave própria em share/gerencia/correria.json (com a opção
ligada), as ferramentas (/api/integracao/ferramentas, sem precisar da IA daqui), a rota /api/integracao/conversa (com a
IA ligada: fotos e PDFs) e o pedido para a IA (só responde, sem ações). Pessoas e valores inventados (Ana, Beto)."""
import json
import os
import unittest
from datetime import date
from unittest import mock

from tests.base import importar_servidor, pasta_temp, Servidor
S = importar_servidor()
import chat  # noqa: E402
import integracao as I  # noqa: E402

HOJE = date(2026, 11, 15)


class TestConexaoComNome(unittest.TestCase):
    def test_arquivo_e_chave_proprios(self):
        data, share = pasta_temp(), pasta_temp()
        os.environ["GERENCIA_URL_INTERNA"] = "http://g:8099"
        self.addCleanup(os.environ.pop, "GERENCIA_URL_INTERNA", None)
        cron = I.Conexao(data, share, 8099, "9.9.9", print)
        cor = I.Conexao(data, share, 8099, "9.9.9", print, nome="correria", extra={"nome": "GerencIA", "rota": "/api/integracao/conversa"})
        cron.publicar()
        cor.publicar()
        self.assertEqual(sorted(os.listdir(share)), ["correria.json", "integracao.json"])
        self.assertEqual(sorted(os.listdir(data)), ["correria.key", "integracao.key"])
        with open(os.path.join(share, "correria.json"), encoding="utf-8") as f:
            p = json.load(f)
        self.assertEqual((p["app"], p["nome"], p["rota"], p["url"], p["chave"]), ("gerencia", "GerencIA", "/api/integracao/conversa", "http://g:8099", cor.chave()))
        self.assertNotEqual(cor.chave(), cron.chave(), "uma chave para cada app")
        cor.publicar(ligado=False)
        self.assertEqual(os.listdir(share), ["integracao.json"])


class TestInstrucoes(unittest.TestCase):
    def d(self):
        return {"bancos": [], "investimentos": [], "lancamentos": [{"id": "l1", "tipo": "despesa", "descricao": "Mercado Bom", "valor": 123.45,
                                                                    "data": "2026-11-10", "pago": True}], "recorrencias": [], "categorias": [], "ajustes": {}}

    def test_so_responde_e_so_sobre_os_apps(self):
        hist = [{"papel": "eu", "texto": f"pergunta {n}"} for n in range(30)] + [{"papel": "ia", "texto": "resposta"}, {"papel": "eu", "texto": "Quanto gastei?"}]
        t = chat.instrucoes_whatsapp(self.d(), hist, "Ana Exemplo", HOJE)
        self.assertIn("WhatsApp da CorrerIA Code", t)
        self.assertIn("Quem está conversando: Ana.", t)
        self.assertIn("*negrito* com um asterisco", t)
        self.assertIn("só com os apps da CorrerIA Code", t, "outros assuntos, não (a regra da Meta)")
        self.assertIn("ainda não dá para lançar, pagar nem mudar um saldo", t)
        self.assertIn("Mercado Bom", t, "com os dados do app")
        self.assertTrue(t.rstrip().endswith('{"resposta":""}'), "só a resposta, sem ações")
        self.assertNotIn('"lancamentos":[]', t)
        self.assertNotIn("Também pode conversar sobre qualquer outro assunto", t)
        conversa = t.split("A conversa (a última mensagem é a que você responde agora):\n", 1)[1].split("\n\n")[0].splitlines()
        self.assertEqual(len(conversa), chat.MAX_HISTORICO)
        self.assertEqual(conversa[-2:], ["IA: resposta", "Pessoa: Quanto gastei?"])

    def test_na_conversa_do_correria(self):
        t = chat.instrucoes_whatsapp(self.d(), [{"papel": "eu", "texto": "oi"}], "Ana", HOJE, canal="correria")
        self.assertIn("conversa do CorrerIA", t)
        self.assertIn("Também pode conversar sobre outros assuntos.", t, "a regra da Meta é só do WhatsApp")
        self.assertNotIn("WhatsApp", t)
        self.assertIn("ainda não dá para lançar", t)

    def test_sem_nome(self):
        self.assertNotIn("Quem está conversando", chat.instrucoes_whatsapp(self.d(), [{"papel": "eu", "texto": "oi"}], "", HOJE))


class TestConversa(unittest.TestCase):
    def setUp(self):
        with S.TRAVA:
            d = S.ler()
            d["ajustes"].update(ia=True, correria=True)
            S.salvar(d, versao=False)

    def test_simulada(self):
        r = S.conversa_correria({"texto": "Quanto gastei este mês?", "pessoa": {"id": "person.ana", "nome": "Ana"}})
        self.assertTrue(r["resposta"])
        self.assertEqual(list(r), ["resposta"])

    def test_pela_ia_do_home_assistant(self):
        pedidos = []

        def ia(tipo, payload, imagens, timeout):
            pedidos.append((tipo, payload))
            return {"service_response": {"data": {"resposta": "Você gastou *R$ 123,45*.", "lancamentos": [{"descricao": "x"}]}}}
        antes = S.CHAT.ler()
        with mock.patch.object(S, "IA_MOCK", False), mock.patch.object(S, "ia_chamar", ia):
            r = S.conversa_correria({"texto": "Quanto gastei?", "historico": [{"papel": "eu", "texto": "oi"}, {"papel": "ia", "texto": "Olá!"}, "lixo"],
                                     "pessoa": {"id": "person.ana", "nome": "Ana"}})
        self.assertEqual(r, {"resposta": "Você gastou *R$ 123,45*."}, "as ações ficam de fora")
        tipo, payload = pedidos[0]
        self.assertEqual((tipo, payload["task_name"]), ("whatsapp", "GerencIA: WhatsApp"))
        with mock.patch.object(S, "IA_MOCK", False), mock.patch.object(S, "ia_chamar", ia):
            S.conversa_correria({"texto": "oi", "canal": "correria"})
        self.assertEqual(pedidos[1][1]["task_name"], "GerencIA: CorrerIA")
        self.assertIn("conversa do CorrerIA", pedidos[1][1]["instructions"])
        self.assertIn("Pessoa: oi\nIA: Olá!\nPessoa: Quanto gastei?", payload["instructions"])
        self.assertEqual(S.CHAT.ler(), antes, "a conversa do app não muda")

    def test_resposta_so_com_texto_e_erros(self):
        with mock.patch.object(S, "IA_MOCK", False), mock.patch.object(S, "ia_chamar", return_value={"service_response": {"data": "Oi, Ana!"}}):
            self.assertEqual(S.conversa_correria({"texto": "oi"}), {"resposta": "Oi, Ana!"})
        with mock.patch.object(S, "IA_MOCK", False), mock.patch.object(S, "ia_chamar", side_effect=S.ErroHA("A IA não respondeu.")):
            with self.assertRaisesRegex(ValueError, "A IA não respondeu."):
                S.conversa_correria({"texto": "oi"})
        with mock.patch.object(S, "IA_MOCK", False), mock.patch.object(S, "ia_chamar", return_value={}):
            with self.assertRaisesRegex(ValueError, "A IA não devolveu resposta."):
                S.conversa_correria({"texto": "oi"})
        with self.assertRaisesRegex(ValueError, "Escreva uma mensagem."):
            S.conversa_correria({"texto": "  "})

    def test_ligada_so_com_a_opcao_e_a_ia(self):
        self.assertTrue(S.correria_conversa())
        self.assertFalse(S.correria_conversa({"ajustes": {"correria": True, "ia": False}}), "a conversa precisa da IA")
        self.assertTrue(S.correria_ligada({"ajustes": {"correria": True, "ia": False}}), "as ferramentas, não")
        self.assertFalse(S.correria_ligada({"ajustes": {"ia": True}}))
        self.assertFalse(S.normalizar({})["ajustes"]["correria"], "vem desligado")
        self.assertFalse(S.normalizar({"ajustes": {"correria": "sim"}})["ajustes"]["correria"])


JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "pdf_senha")


def b64(b, mime="image/jpeg"):
    import base64
    return f"data:{mime};base64," + base64.b64encode(b).decode()


class TestAnexo(unittest.TestCase):
    """Uma foto ou um PDF pelo WhatsApp: a IA lê e o que achar fica para conferir no Início."""

    def setUp(self):
        for arq in (S.EMAILS_ARQ, S.SENHAS_ARQ):
            if os.path.exists(arq):
                os.remove(arq)
        with S.TRAVA:
            d = S.ler()
            d["ajustes"].update(ia=True, correria=True, email=False)
            S.salvar(d, versao=False)
        p = mock.patch.object(S.time, "sleep")
        p.start()
        self.addCleanup(p.stop)

    def test_tipos_de_arquivo(self):
        self.assertEqual(S.mime_anexo(JPG), "image/jpeg")
        self.assertEqual(S.mime_anexo(b"\x89PNG\r\n\x1a\n" + b"x"), "image/png")
        self.assertEqual(S.mime_anexo(b"RIFF\x00\x00\x00\x00WEBPVP8 "), "image/webp")
        self.assertEqual(S.mime_anexo(b"%PDF-1.7"), "application/pdf")
        self.assertIsNone(S.mime_anexo(b"GIF89a"))
        with self.assertRaisesRegex(ValueError, r"Envie uma imagem \(JPG, PNG ou WebP\) ou um PDF."):
            S.ia_ler({"anexo": {"b64": b64(b"GIF89a", "image/gif")}})
        self.assertTrue(S.ia_ler({"dica": "caixa", "anexo": {"b64": b64(b"\x89PNG\r\n\x1a\n" + b"x" * 40, "image/png")}})["lancamentos"], "PNG também")

    def test_foto_lida_fica_para_conferir(self):
        r = S.conversa_correria({"texto": "", "pessoa": {"id": "person.ana", "nome": "Ana"}, "anexo": {"tipo": "image/jpeg", "nome": "", "b64": b64(JPG)}})
        self.assertTrue(r["resposta"].startswith("Li 4 lançamentos · R$ "), r["resposta"])
        self.assertIn("na foto:\n- iFood: R$ 64,90", r["resposta"])
        self.assertIn("- Magazine Luiza: R$ 189,90 (2/6)", r["resposta"])
        self.assertTrue(r["resposta"].endswith("Para lançar, confira no GerencIA: está nos Avisos do Início."))
        it = S.emails_ler()["itens"][0]
        self.assertEqual((it["origem"], it["de"], it["estado"], it["arquivo"]), ("whatsapp", "Ana", "conferir", "Foto"))
        self.assertEqual(len(it["resultado"]["lancamentos"]), 4)
        pub = S.email_publico(it)
        self.assertEqual((pub["origem"], pub["de"]), ("whatsapp", "Ana"))
        self.assertEqual(S.email_publico({"id": "a" * 12, "estado": "fora"})["origem"], "email")

    def test_pdf_com_senha_que_nenhuma_abre(self):
        with open(os.path.join(FIX, "fatura-aes256.pdf"), "rb") as f:
            pdf = f.read()
        r = S.conversa_correria({"anexo": {"tipo": "application/pdf", "nome": "fatura.pdf", "b64": b64(pdf, "application/pdf")}})
        self.assertIn("Esse PDF tem senha", r["resposta"])
        self.assertEqual(S.emails_ler()["itens"], [])
        S.senha_nova("CPF da Ana", "12345")
        r = S.conversa_correria({"anexo": {"tipo": "application/pdf", "nome": "fatura.pdf", "b64": b64(pdf, "application/pdf")}})
        self.assertIn("no PDF:", r["resposta"], "com a senha cadastrada, abre")
        self.assertEqual(S.emails_ler()["itens"][0]["arquivo"], "fatura.pdf")

    def test_arquivo_que_nao_le(self):
        r = S.conversa_correria({"anexo": {"tipo": "image/gif", "b64": b64(b"GIF89a", "image/gif")}})
        self.assertEqual(r, {"resposta": "Esse tipo de arquivo eu não leio. Mande uma foto ou um PDF."})
        with self.assertRaisesRegex(ValueError, "Arquivo inválido."):
            S.conversa_correria({"anexo": {"b64": "!!"}})

    def test_nada_encontrado(self):
        with mock.patch.object(S, "ia_ler", return_value={"lancamentos": [], "investimentos": []}):
            r = S.conversa_correria({"anexo": {"b64": b64(JPG)}})
        self.assertEqual(r, {"resposta": "Não encontrei gastos nem recebimentos na foto."})
        self.assertEqual(S.emails_ler()["itens"], [])

    def test_pergunta_junto_com_a_foto(self):
        pedidos = []

        def ia(tipo, payload, imagens, timeout):
            pedidos.append(payload["instructions"])
            return {"service_response": {"data": {"resposta": "Deu R$ 314,80 no total."}}}
        with mock.patch.object(S, "IA_MOCK", False), mock.patch.object(S, "ia_chamar", ia), \
                mock.patch.object(S, "ia_ler", return_value={"lancamentos": [{"tipo": "despesa", "descricao": "Mercado Bom", "valor": 314.8}], "investimentos": []}):
            r = S.conversa_correria({"texto": "Quanto deu essa nota?", "pessoa": {"nome": "Ana"}, "anexo": {"b64": b64(JPG)}})
        self.assertEqual(r["resposta"], "Deu R$ 314,80 no total.\n\nPara lançar, confira no GerencIA: está nos Avisos do Início.")
        self.assertIn("Pessoa: Quanto deu essa nota?\n\n(A pessoa mandou a foto junto. Li 1 lançamento · R$ 314,80 na foto:\n- Mercado Bom: R$ 314,80)", pedidos[0])
        self.assertTrue(S.PERGUNTA_RE.search("quanto foi?") and S.PERGUNTA_RE.search("Qual o total") and not S.PERGUNTA_RE.search("fatura do Banco Azul"))

    def test_legenda_sem_pergunta_so_le(self):
        with mock.patch.object(S, "conversa_correria", wraps=S.conversa_correria) as c:
            r = S.conversa_correria({"texto": "fatura do Banco Azul", "anexo": {"b64": b64(JPG)}})
        self.assertEqual(c.call_count, 1, "sem pergunta, nada de conversa")
        self.assertTrue(r["resposta"].startswith("Li 4 lançamentos"))
        self.assertEqual(S.emails_ler()["itens"][0]["assunto"], "fatura do Banco Azul")


class TestRota(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Servidor()
        cls.arq = os.path.join(cls.s.dirs["share"], "correria.json")

    @classmethod
    def tearDownClass(cls):
        cls.s.parar()

    def ligar(self, correria=True, ia=True):
        _, _, d = self.s.get("/api/state")
        d["ajustes"].update(correria=correria, ia=ia)
        st, _, d = self.s.put("/api/state", d)
        self.assertEqual(st, 200)

    def chave(self):
        with open(self.arq, encoding="utf-8") as f:
            return json.load(f)["chave"]

    def test_arquivo_so_com_a_opcao_ligada(self):
        self.ligar(False)
        self.assertFalse(os.path.exists(self.arq), "começa desligado: sem arquivo")
        self.ligar(True)
        with open(self.arq, encoding="utf-8") as f:
            p = json.load(f)
        self.assertEqual((p["app"], p["nome"], p["rota"], p["url"]), ("gerencia", "GerencIA", "/api/integracao/conversa", self.s.url))
        self.assertIn("finanças", p["assunto"])
        self.assertEqual(p["anexos"], ["application/pdf", "image/jpeg", "image/png", "image/webp"], "o que o GerencIA lê")
        self.assertEqual(p["ferramentas"], "/api/integracao/ferramentas")
        chave = p["chave"]
        self.ligar(True, ia=False)
        with open(self.arq, encoding="utf-8") as f:
            p = json.load(f)
        self.assertEqual((p["ferramentas"], p["chave"]), ("/api/integracao/ferramentas", chave), "sem a IA, ficam as ferramentas")
        self.assertNotIn("rota", p, "sem a IA, sem a conversa (fotos e PDFs)")
        self.assertNotIn("anexos", p)
        self.ligar(False)
        self.assertFalse(os.path.exists(self.arq))

    def test_conversa(self):
        self.ligar(True)
        cab = {"Authorization": f"Bearer {self.chave()}", "X-App": "CorrerIA"}
        st, _, r = self.s.post("/api/integracao/conversa", {"texto": "Quanto gastei?", "pessoa": {"nome": "Ana"}}, cabecalhos=cab)
        self.assertEqual(st, 200, r)
        self.assertTrue(r["resposta"])
        _, _, d = self.s.get("/api/state")
        self.assertEqual(d["correria_ultimo"]["app"], "CorrerIA", "a tela mostra quando o CorrerIA perguntou")
        self.assertEqual(self.s.get("/api/rev")[2]["correria_ultimo"]["app"], "CorrerIA")
        st, _, r = self.s.post("/api/integracao/conversa", {"texto": ""}, cabecalhos=cab)
        self.assertEqual((st, r["erro"]), (400, "Escreva uma mensagem."))

    def test_conversa_com_foto(self):
        self.ligar(True)
        cab = {"Authorization": f"Bearer {self.chave()}", "X-App": "CorrerIA"}
        st, _, r = self.s.post("/api/integracao/conversa", {"texto": "", "pessoa": {"nome": "Beto"}, "anexo": {"tipo": "image/jpeg", "b64": b64(JPG)}}, cabecalhos=cab)
        self.assertEqual(st, 200, r)
        self.assertTrue(r["resposta"].startswith("Li "))
        st, _, e = self.s.get("/api/emails")
        it = next(x for x in e["itens"] if x["de"] == "Beto")
        self.assertEqual((it["origem"], it["estado"]), ("whatsapp", "conferir"))

    def test_ferramentas(self):
        self.ligar(True, ia=False)
        cab = {"Authorization": f"Bearer {self.chave()}", "X-App": "CorrerIA"}
        st, _, r = self.s.get("/api/integracao/ferramentas", cabecalhos=cab)
        self.assertEqual(st, 200, r)
        self.assertEqual(r["ferramentas"][0]["nome"], "resumo")
        self.assertIn("gerencia_resumo", r["instrucoes"])
        self.assertTrue(all("entrada" in f and "grava" in f and "apaga" in f for f in r["ferramentas"]))
        st, _, r = self.s.post("/api/integracao/ferramentas", {"nome": "resumo", "argumentos": {}, "cliente": "Claude"}, cabecalhos=cab)
        self.assertEqual(st, 200, r)
        self.assertIn("Hoje é", r["texto"])
        _, _, d = self.s.get("/api/state")
        rev = d["rev"]
        st, _, r = self.s.post("/api/integracao/ferramentas", {"nome": "lancar", "argumentos": {"tipo": "despesa", "descricao": "Feira", "valor": 32.5},
                                                                "pessoa": {"id": "person.ana", "nome": "Ana"}, "cliente": "Gemini"}, cabecalhos=cab)
        self.assertEqual(st, 200, r)
        self.assertTrue(r["texto"].startswith("Lançado: Feira · R$ 32,50"))
        _, _, d = self.s.get("/api/state")
        self.assertEqual(d["rev"], rev + 1, "a tela vê a mudança pela revisão")
        self.assertEqual(d["lancamentos"][-1]["descricao"], "Feira")
        self.assertEqual((d["correria_uso"]["app"], d["correria_uso"]["nome"]), ("Gemini", "lancar"))
        self.assertEqual(self.s.get("/api/rev")[2]["correria_uso"]["app"], "Gemini")
        st, _, r = self.s.post("/api/integracao/ferramentas", {"nome": "lancar", "argumentos": {"tipo": "despesa"}}, cabecalhos=cab)
        self.assertEqual((st, r["erro"]), (400, "Falta a descrição."))
        st, _, r = self.s.post("/api/integracao/ferramentas", {"nome": "sacar"}, cabecalhos=cab)
        self.assertEqual((st, r["erro"]), (404, "Ferramenta desconhecida: sacar."))
        st, _, r = self.s.post("/api/integracao/conversa", {"texto": "oi"}, cabecalhos=cab)
        self.assertEqual(st, 401, "sem a IA, a conversa não entra (as ferramentas sim)")
        self.ligar(False)
        st, _, r = self.s.get("/api/integracao/ferramentas", cabecalhos=cab)
        self.assertEqual(st, 401, "desligado, nem com a chave")

    def test_sem_a_chave_certa_nao_entra(self):
        self.ligar(True)
        with open(os.path.join(self.s.dirs["share"], "integracao.json"), encoding="utf-8") as f:
            do_cronologia = json.load(f)["chave"]
        for cab in ({}, {"Authorization": "Bearer errada"}, {"Authorization": f"Bearer {do_cronologia}"}):
            st, _, r = self.s.post("/api/integracao/conversa", {"texto": "oi"}, cabecalhos=cab)
            self.assertEqual((st, r["erro"]), (401, "Chave inválida ou CorrerIA desligado no GerencIA."))
            st, _, r = self.s.post("/api/integracao/ferramentas", {"nome": "resumo"}, cabecalhos=cab)
            self.assertEqual(st, 401)
        chave = self.chave()
        st, _, r = self.s.get("/api/integracao/contas", cabecalhos={"Authorization": f"Bearer {chave}"})
        self.assertEqual(st, 401, "a chave do CorrerIA não abre as contas do CronologIA")
        self.ligar(False)
        st, _, r = self.s.post("/api/integracao/conversa", {"texto": "oi"}, cabecalhos={"Authorization": f"Bearer {chave}"})
        self.assertEqual(st, 401, "desligado, nem com a chave")


if __name__ == "__main__":
    unittest.main()
