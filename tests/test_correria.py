"""O CorrerIA (o contato da CorrerIA Code no WhatsApp) perguntando ao GerencIA: a chave própria em
share/gerencia/correria.json (só com a opção e a IA ligadas), a rota /api/integracao/conversa e o pedido para a IA
(só responde, sem ações, só sobre os apps). Pessoas e valores inventados (Ana, Beto)."""
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
        self.assertTrue(S.correria_ligada())
        self.assertFalse(S.correria_ligada({"ajustes": {"correria": True, "ia": False}}))
        self.assertFalse(S.correria_ligada({"ajustes": {"ia": True}}))
        self.assertFalse(S.normalizar({})["ajustes"]["correria"], "vem desligado")
        self.assertFalse(S.normalizar({"ajustes": {"correria": "sim"}})["ajustes"]["correria"])


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
        self.ligar(True, ia=False)
        self.assertFalse(os.path.exists(self.arq), "sem a IA, também some")

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

    def test_sem_a_chave_certa_nao_entra(self):
        self.ligar(True)
        with open(os.path.join(self.s.dirs["share"], "integracao.json"), encoding="utf-8") as f:
            do_cronologia = json.load(f)["chave"]
        for cab in ({}, {"Authorization": "Bearer errada"}, {"Authorization": f"Bearer {do_cronologia}"}):
            st, _, r = self.s.post("/api/integracao/conversa", {"texto": "oi"}, cabecalhos=cab)
            self.assertEqual((st, r["erro"]), (401, "Chave inválida ou CorrerIA desligado no GerencIA."))
        chave = self.chave()
        st, _, r = self.s.get("/api/integracao/contas", cabecalhos={"Authorization": f"Bearer {chave}"})
        self.assertEqual(st, 401, "a chave do CorrerIA não abre as contas do CronologIA")
        self.ligar(False)
        st, _, r = self.s.post("/api/integracao/conversa", {"texto": "oi"}, cabecalhos={"Authorization": f"Bearer {chave}"})
        self.assertEqual(st, 401, "desligado, nem com a chave")


if __name__ == "__main__":
    unittest.main()
