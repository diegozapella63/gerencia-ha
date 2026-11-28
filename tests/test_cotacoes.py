"""Cotações da B3 pela brapi (1.99.0; o dono: "Cotações da B3 (brapi). Pode seguir neste"): o cotacoes.py e as partes do
server.py (a chave em /data/brapi.json, o estado para a tela, atualizar agora e sozinho) e as ferramentas do CorrerIA.
A brapi é de mentira; papéis, preços e a chave inventados."""
import json
import os
import stat
import unittest
from datetime import date, datetime
from unittest import mock

from tests.base import ServidorFalso, importar_servidor
S = importar_servidor()
from tests.test_integracao import dados as dados_base  # noqa: E402
import cotacoes as C  # noqa: E402
import ferramentas as F  # noqa: E402

CHAVE = "chave-de-teste-abcd"


def papel(iid, ticker, qtd, valor=0):
    return {"id": iid, "nome": ticker, "banco": "", "tipo": "acoes", "valor": valor, "data_valor": "2026-01-01", "indexador": "estimado", "taxa": 10,
            "liquidez": "diaria", "titular": "meu", "ticker": ticker, "qtd": qtd}


class Base(unittest.TestCase):
    def setUp(self):
        self.precos = {"BOLA3": 10.5, "CASA11": 100}
        self.status = {}

        def rota(t):
            def f(h, corpo):
                if h.headers.get("Authorization") != f"Bearer {CHAVE}":
                    return 401, {"error": True}
                if t in self.status:
                    return self.status[t], {"error": True}
                return 200, {"results": [{"symbol": t, "longName": f"Empresa {t}", "regularMarketPrice": self.precos[t], "regularMarketTime": "2026-11-13T20:07:00.000Z"}]}
            return f
        self.brapi = ServidorFalso({f"/quote/{t}": rota(t) for t in ("BOLA3", "CASA11", "BBAS3", "RUIM3")})
        self.addCleanup(self.brapi.fechar)
        self.precos.update(BBAS3=20, RUIM3="x")
        p = mock.patch.object(C, "BASE", self.brapi.url)
        p.start()
        self.addCleanup(p.stop)
        if os.path.exists(S.BRAPI_ARQ):
            os.remove(S.BRAPI_ARQ)
        self.addCleanup(lambda: os.path.exists(S.BRAPI_ARQ) and os.remove(S.BRAPI_ARQ))
        antes = S.ler()  # o servidor é um só para todos os testes: no fim, os dados voltam a ser os de antes
        self.addCleanup(lambda: S.salvar(antes, versao=False))
        d = dados_base()
        d["investimentos"] = [papel("i1", "BOLA3", 100), papel("i2", "casa11", "2,5", 7), papel("i3", "BOLA3", 1),
                              {"id": "i4", "nome": "CDB", "tipo": "cdb", "valor": 500, "data_valor": "2026-01-01", "indexador": "cdi_pct", "taxa": 100}]
        S.salvar(d, versao=False)


class TestModulo(Base):
    def test_codigo_e_quantidade(self):
        self.assertEqual([C.limpar_ticker(x) for x in (" petr4 ", "MXRF11", "PETR4F", "bova-11", "AAPL34", "oi", "1234", "", None, "TOOLONGXX1")],
                         ["PETR4", "MXRF11", "PETR4", "BOVA11", "AAPL34", "", "", "", "", ""])
        self.assertEqual([C.quantidade(x) for x in (10, "2,5", "3.25", 0, -1, "x", None, True, 1e12)], [10.0, 2.5, 3.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    def test_cotacao_e_os_erros(self):
        self.assertEqual(C.cotacao("bola3", CHAVE), {"preco": 10.5, "em": "2026-11-13T20:07:00", "nome": "Empresa BOLA3"})
        self.assertEqual(self.brapi.pedidos[-1][1], "/quote/BOLA3", "a chave não vai no endereço")
        for t, tok, status, frase, fatal in (("BOLA3", "errada", None, "recusou a chave", True), ("BOLA3", CHAVE, 429, "limite de consultas", True),
                                             ("BOLA3", CHAVE, 404, "não foi encontrado", False), ("BOLA3", CHAVE, 500, "erro (500)", False),
                                             ("RUIM3", CHAVE, None, "não trouxe o preço", False), ("??", CHAVE, None, "não parece um código", False)):
            self.status = {t: status} if status else {}
            with self.assertRaises(C.Erro) as cm:
                C.cotacao(t, tok)
            self.assertIn(frase, str(cm.exception))
            self.assertEqual(cm.exception.fatal, fatal, frase)
        with self.assertRaises(C.Erro) as cm:
            C.cotacao("BOLA3", CHAVE, base="http://127.0.0.1:9/brapi", timeout=2)
        self.assertEqual((str(cm.exception), cm.exception.fatal), ("Sem resposta da brapi.", True))

    def test_papeis_e_aplicar(self):
        d = S.ler()
        self.assertEqual([(i["id"], t, q) for i, t, q in C.papeis(d)], [("i1", "BOLA3", 100.0), ("i2", "CASA11", 2.5), ("i3", "BOLA3", 1.0)])
        with mock.patch.object(C, "MAX_PAPEIS", 1):
            self.assertEqual([i["id"] for i, _, _ in C.papeis(d)], ["i1", "i3"], "passou do limite de códigos: o mesmo código ainda entra")
        self.assertEqual(C.aplicar(d, {"BOLA3": {"preco": 10.5, "em": "x"}}, "2026-11-15"), 2)
        i1, i2 = d["investimentos"][0], d["investimentos"][1]
        self.assertEqual((i1["valor"], i1["data_valor"], i1["cotacao"]), (1050.0, "2026-11-15", {"preco": 10.5, "em": "x"}))
        self.assertEqual((i2["valor"], i2["data_valor"]), (7, "2026-01-01"), "sem o preço dele, fica como estava")
        self.assertEqual(C.aplicar(d, {"BOLA3": {"preco": 10.5, "em": "x"}}, "2026-11-15"), 0, "nada mudou: nada a gravar")


class TestServidor(Base):
    def test_sem_chave(self):
        self.assertEqual(S.cotacoes_estado(), {"tem": False, "fim": "", "atualizado_em": "", "erro": "", "papeis": 3})
        self.assertFalse(S.cotacoes_na_hora())
        with self.assertRaisesRegex(ValueError, "Ponha a chave"):
            S.atualizar_cotacoes()
        for tok in ("", "curta", "com espaço no meio", "x" * 201):
            with self.assertRaisesRegex(ValueError, "Cole a chave"):
                S.cotacoes_mudar({"token": tok})
        with self.assertRaisesRegex(ValueError, "recusou a chave. A chave não foi guardada"):
            S.cotacoes_mudar({"token": "chave-errada-1234"})
        self.assertFalse(os.path.exists(S.BRAPI_ARQ))

    def test_guardar_a_chave_atualiza_os_papeis(self):
        rev = S.ler()["rev"]
        e = S.cotacoes_mudar({"token": f" {CHAVE} "})
        self.assertEqual((e["tem"], e["fim"], e["erro"], e["papeis"]), (True, "••••abcd", "", 3))
        self.assertTrue(e["atualizado_em"])
        self.assertNotIn(CHAVE, json.dumps(e), "a chave não volta para a tela")
        self.assertEqual(stat.S_IMODE(os.stat(S.BRAPI_ARQ).st_mode), 0o600)
        d = S.ler()
        hoje = date.today().isoformat()
        self.assertEqual([(i["valor"], i["data_valor"]) for i in d["investimentos"]], [(1050.0, hoje), (250.0, hoje), (10.5, hoje), (500, "2026-01-01")])
        self.assertGreater(d["rev"], rev, "a tela vê a mudança pelo /api/rev")
        self.assertNotIn(CHAVE, json.dumps(d), "a chave fica fora dos dados (e das exportações)")
        self.assertEqual(len([p for p in self.brapi.pedidos if p[1] == "/quote/BOLA3"]), 2, "um pedido por código (a conferência e a atualização)")
        # um papel que a bolsa não conhece não para os outros; a chave recusada ou o limite, sim
        self.status = {"BOLA3": 404}
        self.precos["CASA11"] = 110
        e = S.cotacoes_mudar({"atualizar": True})
        self.assertEqual(e["erro"], "BOLA3 não foi encontrado na B3.")
        self.assertEqual(S.ler()["investimentos"][1]["valor"], 275.0)
        self.status = {"BOLA3": 429}
        self.precos["CASA11"] = 120
        self.assertIn("limite de consultas", S.atualizar_cotacoes()["erro"])
        self.assertEqual(S.ler()["investimentos"][1]["valor"], 275.0, "parou no limite: o resto fica para a próxima")
        self.assertEqual(S.cotacoes_mudar({"apagar": True})["tem"], False)

    def test_na_hora_de_6_em_6_horas_nos_dias_de_semana(self):
        S._brapi_gravar({"token": CHAVE})
        sexta, sabado = datetime(2026, 11, 13, 12, 0), datetime(2026, 11, 14, 12, 0)
        self.assertTrue(S.cotacoes_na_hora(sabado), "nunca atualizou: atualiza, mesmo no sábado")
        S._brapi_gravar({"token": CHAVE, "em": "2026-11-13T07:00:00"})
        self.assertFalse(S.cotacoes_na_hora(sexta), "há 5 horas")
        self.assertTrue(S.cotacoes_na_hora(datetime(2026, 11, 13, 13, 1)))
        self.assertFalse(S.cotacoes_na_hora(sabado), "fim de semana: a bolsa está fechada")
        d = S.ler()
        d["investimentos"] = d["investimentos"][3:]
        S.salvar(d, versao=False)
        self.assertFalse(S.cotacoes_na_hora(datetime(2026, 11, 13, 13, 1)), "sem papel com código, nada a buscar")
        S.cotacoes_mudar({"token": CHAVE})
        self.assertEqual([p[1] for p in self.brapi.pedidos], ["/quote/BBAS3"], "sem papel da casa, a conferência usa um qualquer; nada a atualizar")
        with open(S.BRAPI_ARQ, "w", encoding="utf-8") as f:
            f.write("[1]")
        self.assertEqual(S._brapi_ler(), {})
        with mock.patch.object(S, "atualizar_cotacoes", side_effect=RuntimeError("x")):
            S.cotacoes_sem_erro()

    def test_rotas(self):
        from tests.base import Servidor
        s = Servidor(env={"GERENCIA_BRAPI": self.brapi.url})
        self.addCleanup(s.parar)
        self.assertEqual(s.get("/api/cotacoes")[2]["tem"], False)
        st, _, r = s.post("/api/cotacoes", {"token": "x"})
        self.assertEqual((st, r), (400, {"erro": "Cole a chave da brapi (o token do painel dela)."}))
        st, _, r = s.post("/api/cotacoes", {"token": CHAVE})
        self.assertEqual((st, r["fim"]), (200, "••••abcd"))


class TestFerramentas(Base):
    def test_cadastrar_e_mudar_a_quantidade(self):
        d = S.ler()
        hoje = date(2026, 11, 15)
        t, mudou = F.chamar("novo_investimento", {"nome": "Bola", "tipo": "acoes", "codigo": "bola3", "quantidade": 50}, d, hoje)
        self.assertTrue(mudou)
        self.assertIn("50 de BOLA3 (o valor acompanha a cotação", t)
        novo = d["investimentos"][-1]
        self.assertEqual((novo["ticker"], novo["qtd"], novo["valor"]), ("BOLA3", 50.0, 0))
        for args, erro in (({"nome": "x", "tipo": "acoes", "codigo": "??", "quantidade": 1}, "codigo:"), ({"nome": "x", "tipo": "acoes", "codigo": "BOLA3"}, "juntos"),
                           ({"nome": "x", "tipo": "acoes", "quantidade": 3}, "juntos"), ({"nome": "x", "tipo": "cdb"}, "Falta o valor")):
            with self.assertRaisesRegex(F.ErroFerramenta, erro):
                F.chamar("novo_investimento", args, d, hoje)
        self.assertIn("O valor entra na próxima atualização", F.chamar("atualizar_investimento", {"id": novo["id"], "quantidade": 60}, d, hoje)[0])
        C.aplicar(d, {"BOLA3": {"preco": 10.5, "em": "x"}}, hoje.isoformat())
        t = F.chamar("atualizar_investimento", {"id": novo["id"], "quantidade": 80}, d, hoje)[0]
        self.assertEqual(t, "Atualizado: Bola: 80 de BOLA3 a R$ 10,50 = R$ 840,00 (antes R$ 630,00).")
        self.assertEqual((novo["qtd"], novo["valor"]), (80.0, 840.0))
        for args, erro in (({"id": "i4", "quantidade": 2}, "não tem código"), ({"id": novo["id"], "quantidade": 0}, "maior que zero"),
                           ({"id": novo["id"], "quantidade": 2, "saldo": 1}, "Mande um só")):
            with self.assertRaisesRegex(F.ErroFerramenta, erro):
                F.chamar("atualizar_investimento", args, d, hoje)
        lista = json.loads(F.chamar("investimentos", {}, d, hoje)[0])["investimentos"]
        it = next(x for x in lista if x["id"] == novo["id"])
        self.assertEqual((it["codigo"], it["quantidade"], it["cotacao"]), ("BOLA3", 80.0, 10.5))
        self.assertNotIn("codigo", next(x for x in lista if x["id"] == "i4"))

    def test_pelo_correria_o_papel_novo_ja_busca_a_cotacao(self):
        S._brapi_gravar({"token": CHAVE})
        idos = []
        with mock.patch.object(S.threading, "Thread", lambda *a, **k: mock.Mock(start=lambda: k.get("target") is S.cotacoes_sem_erro and idos.append(k["target"]))):
            S.usar_ferramenta({"nome": "novo_investimento", "argumentos": {"nome": "Casa", "tipo": "acoes", "codigo": "CASA11", "quantidade": 3}, "cliente": "Claude"})
            S.usar_ferramenta({"nome": "investimentos", "argumentos": {}, "cliente": "Claude"})
        self.assertEqual(idos, [S.cotacoes_sem_erro])


if __name__ == "__main__":
    unittest.main()
