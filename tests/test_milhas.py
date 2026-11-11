"""Milhas (1.63.0): a conta (calc.milhas_de: o saldo de hoje com os resgates, o próximo lote que vence, o próximo nível e
as trocas que já dão; metas_milhas e progresso_meta), a leitura pela IA (milhas.py: o trecho e o número conferidos no
texto e na página, o print sem conferir) e a rota /api/milhas/ler, com a IA simulada, a IA "de verdade" falsa e uma página
de mentira; o aviso das milhas que vencem (integracao.avisos) e o resumo da Conversa. Dados inventados (Voa Mais, Ana)."""
import base64
import os
import unittest
from datetime import date
from unittest import mock

from tests.base import ServidorFalso, Servidor, importar_servidor
from tests.test_avisos import Trocar
S = importar_servidor()
import calc  # noqa: E402
import chat  # noqa: E402
import integracao  # noqa: E402
import milhas as M  # noqa: E402

HOJE = date(2026, 11, 15)
VOA = {"id": "bn-voa", "tipo": "milhas", "nome": "Voa Mais", "pessoa": "Ana", "origem": "conta:k1", "saldo": 12300, "saldo_em": "2026-11-01",
       "nivel": "Prata", "proximo": {"nivel": "Ouro", "pede": 25000, "tem": 3200, "unidade": "milhas"},
       "vencem": [{"qtd": 1500, "data": "2027-06-30"}, {"qtd": 2000, "data": "2026-12-31"}, {"qtd": 900, "data": "2026-10-01"}],
       "resgates": [{"nome": "Cidade A – Cidade C", "milhas": 12500}, {"nome": "Cidade A – Cidade B", "milhas": 7500}, {"nome": "", "milhas": 1},
                    {"nome": "Upgrade", "milhas": 0}],
       "usos": [{"id": "u1", "data": "2026-11-10", "qtd": 1000}, {"id": "u0", "data": "2026-10-20", "qtd": 5000}]}
PAGINA = """<html><body><h1>Programa Voa Mais</h1><h2>Nível Ouro</h2><p>Ouro: 25.000 milhas qualificáveis por ano</p>
<ul><li>Bagagem extra de 23 kg</li><li>Embarque com prioridade</li></ul>
<h2>Tabela de resgate</h2><ul><li>Cidade A – Cidade B: 7.500 milhas</li><li>Cidade A – Cidade C: 12.500 milhas</li></ul>
<p>Resgate no site ou no app, em Usar milhas.</p></body></html>"""
JPG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 64).decode()


class TestConta(unittest.TestCase):
    def test_saldo_lote_nivel_e_trocas(self):
        m = calc.milhas_de(VOA, HOJE)
        self.assertEqual(m["saldo"], 11300, "o resgate depois do saldo desconta; o de antes já estava no saldo")
        self.assertEqual(m["vence"], {"qtd": 2000, "data": "2026-12-31"}, "o próximo lote, sem o que já venceu")
        self.assertEqual(m["proximo"], {"nivel": "Ouro", "pede": 25000, "tem": 3200, "falta": 21800, "pct": 12.8, "ja": False, "unidade": "milhas"})
        self.assertEqual([r["nome"] for r in m["da"]], ["Cidade A – Cidade B"])
        self.assertEqual(m["falta"]["nome"], "Cidade A – Cidade C")
        vazio = calc.milhas_de({"tipo": "milhas", "proximo": {"nivel": "Ouro", "pede": 0}, "vencem": ["lixo"], "usos": [None, {"data": "x"}]}, HOJE)
        self.assertEqual(vazio, {"saldo": 0, "vence": None, "proximo": None, "da": [], "falta": None})
        ja = calc.milhas_de({"saldo": 100, "proximo": {"nivel": "Ouro", "pede": 10, "tem": 12, "unidade": "trechos"}}, HOJE)["proximo"]
        self.assertEqual((ja["ja"], ja["falta"], ja["pct"], ja["unidade"]), (True, 0, 100.0, "trechos"))

    def test_proximo_nivel_vira_oportunidade(self):
        d = {"beneficios": [VOA, {"id": "bn-x", "tipo": "milhas", "nome": "Sem nível"}, {"id": "bn-v", "tipo": "vantagem", "nome": "Seguro"}, "lixo"]}
        metas = calc.metas_milhas(d, HOJE)
        self.assertEqual(metas, [{"id": "milhas:bn-voa", "origem": "conta:k1", "tipo": "milhas", "valor": 25000, "ganha": "Ouro", "nivel": True, "milhas": "bn-voa"}])
        p = calc.progresso_meta(metas[0], d, HOJE)
        self.assertEqual((p["tem"], p["pede"], p["falta"], p["pct"], p["ja"], p["sem"]), (3200, 25000, 21800, 12.8, False, ""))
        self.assertEqual(calc.progresso_meta(dict(metas[0], milhas="bn-sumiu"), d, HOJE)["sem"], "origem")


class TestLimpar(unittest.TestCase):
    TEXTO = "Saldo: 12.300 milhas. Nível Prata. Ouro: 25.000 milhas qualificáveis. Bagagem extra de 23 kg. Cidade A – Cidade B: 7.500 milhas. Resgate no app."

    def test_com_texto_so_o_que_esta_escrito(self):
        lido, rec = M.limpar({
            "programa": " Voa   Mais ", "saldo": "12.300", "nivel": "Prata", "qualificaveis": 9999,
            "proximo": {"nivel": "Ouro", "pede": 25000, "unidade": "milhas", "trecho": "Ouro: 25.000 milhas qualificáveis"},
            "vencem": [{"qtd": 7500, "data": "2027-01-31"}, {"qtd": 1234, "data": "2027-01-31"}, {"qtd": 1, "data": "ontem"}],
            "vantagens": [{"nome": "Bagagem extra", "trecho": "Bagagem extra de 23 kg"}, {"nome": "Sala VIP", "trecho": "sala vip grátis"}, "Bagagem extra"],
            "resgates": [{"nome": "Cidade A – Cidade B", "milhas": 7500, "trecho": "Cidade A – Cidade B: 7.500 milhas"},
                         {"nome": "Cidade A – Cidade Z", "milhas": 9000, "trecho": "Cidade A – Cidade B: 7.500 milhas"}],
            "como": [{"texto": "Resgate no app", "trecho": "Resgate no app"}, {"texto": "Ligue para nós", "trecho": "Ligue"}]}, self.TEXTO)
        self.assertEqual(lido, {"programa": "Voa Mais", "saldo": 12300, "nivel": "Prata",
                                "vencem": [{"qtd": 7500, "data": "2027-01-31"}],
                                "proximo": {"nivel": "Ouro", "pede": 25000, "unidade": "milhas", "trecho": "Ouro: 25.000 milhas qualificáveis"},
                                "vantagens": [{"nome": "Bagagem extra", "trecho": "Bagagem extra de 23 kg"}],
                                "resgates": [{"nome": "Cidade A – Cidade B", "milhas": 7500, "trecho": "Cidade A – Cidade B: 7.500 milhas"}],
                                "como": ["Resgate no app"]})
        self.assertEqual(rec, 5, "as qualificáveis, um lote, a sala VIP, o resgate de 9.000, o Ligue para nós")
        _, rec = M.limpar({"proximo": {"nivel": "Ouro", "pede": 30000, "trecho": "Ouro: 25.000 milhas qualificáveis"}}, self.TEXTO)
        self.assertEqual(rec, 1, "o número fora do trecho")

    def test_do_print_sem_conferir(self):
        lido, rec = M.limpar({"saldo": 12300, "nivel": "Prata", "qualificaveis": "3.200", "vencem": [{"qtd": 2000, "data": "2027-06-30"}] * 8,
                              "vantagens": [{"nome": f"V{k}"} for k in range(20)], "resgates": [{"nome": f"R{k}", "milhas": 1000 + k} for k in range(20)],
                              "como": [f"Passo {k}" for k in range(8)], "proximo": {"nivel": "Ouro", "pede": 10, "unidade": "trechos"}})
        self.assertEqual(rec, 0)
        self.assertEqual((lido["qualificaveis"], len(lido["vencem"]), len(lido["vantagens"]), len(lido["resgates"]), len(lido["como"]), lido["proximo"]),
                         (3200, 6, 15, 15, 5, {"nivel": "Ouro", "pede": 10, "unidade": "trechos"}))
        self.assertEqual(M.limpar("lixo"), ({}, 0))
        self.assertEqual(M.limpar({"resgates": ["x", {"nome": "R", "milhas": 0}], "vencem": "x", "como": [""]}), ({}, 0))

    def test_pedido_e_trechos(self):
        p = M.prompt("Voa Mais", "Prata", "https://voamais.exemplo/niveis", "Ouro: 25.000")
        self.assertIn("a página https://voamais.exemplo/niveis sobre um programa de milhas ou pontos (Voa Mais)", p)
        self.assertIn('os benefícios do nível "Prata"', p)
        self.assertIn("Trechos da página:", p)
        self.assertIn("a imagem ou o PDF anexado", M.prompt(anexo=True))
        self.assertIn("de agora (ou o básico)", M.prompt(texto="x"))
        longo = "texto qualquer " * 2000 + " Ouro: 25.000 milhas qualificáveis " + "outro texto " * 2000
        self.assertIn("25.000 milhas", M.trechos(longo))
        self.assertLess(len(M.trechos(longo)), len(longo))

    def test_simulados(self):
        r = M.simulados(M.EXEMPLO_ANEXO + "\nOuro: 25.000 milhas qualificáveis\nCidade A – Cidade B: 7.500 milhas\nEmbarque com prioridade\nResgate no app")
        self.assertEqual((r["programa"], r["saldo"], r["nivel"], r["qualificaveis"], r["vencem"], r["proximo"]["pede"], r["resgates"][0]["milhas"],
                          r["vantagens"][0]["nome"], r["como"][0]["texto"]),
                         ("Voa Mais", 12300, "Prata", 3200, [{"qtd": 2000, "data": "2027-06-30"}], 25000, 7500, "Embarque com prioridade", "Resgate no app"))


class TestLerNoServidor(unittest.TestCase):
    def setUp(self):
        if os.path.exists(S.ARQ):
            os.remove(S.ARQ)
        self.falso = ServidorFalso({"/voa": (200, PAGINA)})
        self.addCleanup(self.falso.fechar)
        Trocar(self, IA_MOCK=True)

    def test_print_pagina_e_erros(self):
        r = S.milhas_ler({"anexo": {"b64": "data:image/jpeg;base64," + JPG}, "programa": "Voa Mais"})
        self.assertEqual((r["saldo"], r["nivel"], r["qualificaveis"], r["vencem"], r["recusados"]), (12300, "Prata", 3200, [{"qtd": 2000, "data": "2027-06-30"}], 0))
        r = S.milhas_ler({"texto": self.falso.url + "/voa"})
        self.assertEqual((r["proximo"]["nivel"], r["proximo"]["pede"], [x["milhas"] for x in r["resgates"]], [v["nome"] for v in r["vantagens"]], r["como"], r["url"]),
                         ("Ouro", 25000, [7500, 12500], ["Bagagem extra de 23 kg", "Embarque com prioridade"], ["Resgate no site ou no app, em Usar milhas."],
                          self.falso.url + "/voa"))
        with self.assertRaisesRegex(ValueError, "A IA não achou milhas aqui."):
            S.milhas_ler({"texto": "Nada que sirva"})
        with mock.patch.object(M, "simulados", return_value={"resgates": [{"nome": "Lua", "milhas": 999, "trecho": "Lua: 999 milhas"}]}), \
                self.assertRaisesRegex(ValueError, "A IA citou coisas que não estão escritas na página"):
            S.milhas_ler({"texto": self.falso.url + "/voa"})
        with self.assertRaisesRegex(ValueError, "Envie um print"):
            S.milhas_ler({})


class TestIaDeVerdade(unittest.TestCase):
    def setUp(self):
        if os.path.exists(S.ARQ):
            os.remove(S.ARQ)
        Trocar(self, IA_MOCK=False, ia_disponivel=lambda d: True)
        self.pedidos = []

    def ia(self, *respostas):
        fila = list(respostas)

        def chamar(tipo, payload, n, timeout=None):
            self.pedidos.append((tipo, payload, n))
            r = fila.pop(0)
            if isinstance(r, Exception):
                raise r
            return {"service_response": {"data": r}}
        Trocar(self, ia_chamar=chamar)

    def test_texto_e_pdf(self):
        self.ia({"saldo": 12300, "nivel": "Prata"})
        r = S.milhas_ler({"texto": "Seu saldo: 12.300 milhas, nível Prata", "programa": "Voa Mais", "nivel": "Prata"})
        self.assertEqual((r["saldo"], r["nivel"]), (12300, "Prata"))
        tipo, payload, _ = self.pedidos[0]
        self.assertEqual((tipo, payload["task_name"]), ("milhas", "GerencIA: ler milhas"))
        self.assertIn("(Voa Mais)", payload["instructions"])
        pdf = base64.b64encode(b"%PDF-1.4 extrato").decode()
        self.ia(S.ErroHA("Formato não aceito."), {"saldo": 4000})
        with mock.patch.object(S, "pdf_texto", return_value="Saldo de 4.000 milhas"):
            self.assertEqual(S.milhas_ler({"anexo": {"b64": pdf}})["saldo"], 4000)
        self.ia(S.ErroHA("Formato não aceito."), S.ErroHA("De novo não."))
        with mock.patch.object(S, "pdf_texto", return_value="Saldo"), self.assertRaisesRegex(ValueError, "De novo não."):
            S.milhas_ler({"anexo": {"b64": pdf}})
        self.ia(S.ErroHA("Formato não aceito."))
        with mock.patch.object(S, "pdf_texto", return_value=""), self.assertRaisesRegex(ValueError, "Formato não aceito."):
            S.milhas_ler({"anexo": {"b64": pdf}})


class TestRota(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Servidor()

    @classmethod
    def tearDownClass(cls):
        cls.srv.parar()

    def test_ler(self):
        st, _, r = self.srv.post("/api/milhas/ler", {"texto": "Saldo: 12.300 milhas"})
        self.assertEqual((st, r["saldo"]), (200, 12300))
        st, _, r = self.srv.post("/api/milhas/ler", {})
        self.assertEqual(st, 400)
        self.assertIn("milhas", str(self.srv.get("/api/ia/uso")[2]), "conta no Uso da IA")


class TestAvisoEConversa(unittest.TestCase):
    def test_milhas_que_vencem_no_agora_do_cronologia(self):
        d = {"beneficios": [dict(VOA, vencem=[{"qtd": 2000, "data": "2026-12-31"}]), dict(VOA, id="bn-b", pessoa="", nome="Céu Azul", vencem=[{"qtd": 300, "data": "2027-06-30"}])]}
        av = integracao.avisos(d, [], HOJE)
        self.assertEqual([(a["id"], a["tipo"], a["titulo"], a["texto"], a["caminho"]) for a in av],
                         [("ben:milhas", "beneficio", "Milhas que vencem", "Voa Mais · Ana: 2.000 em 31/12", "/beneficios")], "até 60 dias; a conta não vira 'vai parar'")
        d["beneficios"][1]["vencem"] = [{"qtd": 300, "data": "2027-01-10"}]
        self.assertEqual(integracao.avisos(d, [], HOJE)[0]["titulo"], "Milhas que vencem em 2 programas")

    def test_resumo_da_conversa(self):
        d = S.ler()
        d["beneficios"] = [VOA]
        r = chat.resumo(d, HOJE)
        self.assertIn("Milhas (programa | de quem | saldo | nível | vencem | trocas que já dão):", r)
        self.assertIn("Voa Mais | Ana | 11.300 | Prata | 2.000 em 2026-12-31 | Cidade A – Cidade B (7.500)", r)
        self.assertIn("nível Ouro | Voa Mais · Ana | 25.000 qualificáveis | faltam 21.800 (tem 3.200)", r)
        d["beneficios"] = [dict(VOA, pessoa="", vencem=[], resgates=[], nivel="", proximo={"nivel": "Ouro", "pede": 100, "tem": 120})]
        r = chat.resumo(d, HOJE)
        self.assertIn("Voa Mais | - | 11.300 | - | - | -", r)
        self.assertIn("nível Ouro | Voa Mais | 100 qualificáveis | já dá", r)


if __name__ == "__main__":
    unittest.main()
