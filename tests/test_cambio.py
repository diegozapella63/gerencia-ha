"""Câmbio do Banco Central (1.100.0; o dono: "Câmbio do Banco Central (dólar, euro, libra) no GerencIA… Pode fazer"): o
cambio.py (a PTAX de venda), a cotação guardada no server.py, a rota, a ferramenta cambio e o lancar com moeda.
O Banco Central é de mentira e as cotações, inventadas."""
import json
import os
import unittest
import urllib.parse
from datetime import date, datetime, timedelta
from unittest import mock

from tests.base import ServidorFalso, importar_servidor
S = importar_servidor()
from tests.test_integracao import dados as dados_base  # noqa: E402
import cambio as C  # noqa: E402
import ferramentas as F  # noqa: E402

ROTA = "/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
VENDA = {"USD": 5.4321, "EUR": 5.9, "GBP": 6.8}
MOEDAS = {k: {"valor": v, "data": "2026-11-27"} for k, v in VENDA.items()}


class Base(unittest.TestCase):
    def setUp(self):
        self.fora = set()

        def rota(h, corpo):
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(h.path).query)
            cod = q["@moeda"][0].strip("'")
            if cod in self.fora:
                return 500, {}
            return 200, {"value": [{"cotacaoVenda": 1.0, "dataHoraCotacao": "2026-11-26 13:09:00.0", "tipoBoletim": "Fechamento"},
                                   {"cotacaoVenda": VENDA[cod], "dataHoraCotacao": "2026-11-27 13:04:25.3", "tipoBoletim": "Fechamento"},
                                   {"cotacaoVenda": 2.0, "dataHoraCotacao": "2026-11-27 10:04:00.0", "tipoBoletim": "Abertura"},
                                   {"cotacaoVenda": True, "dataHoraCotacao": "2026-11-28 10:00:00.0"}, "x"]}
        self.bc = ServidorFalso({ROTA: rota})
        self.addCleanup(self.bc.fechar)
        p = mock.patch.object(C, "BASE", self.bc.url)
        p.start()
        self.addCleanup(p.stop)
        if os.path.exists(S.CAMBIO_ARQ):
            os.remove(S.CAMBIO_ARQ)
        self.addCleanup(lambda: os.path.exists(S.CAMBIO_ARQ) and os.remove(S.CAMBIO_ARQ))


class TestModulo(Base):
    def test_ptax_o_boletim_mais_recente(self):
        self.assertEqual(C.ptax("EUR", date(2026, 11, 28)), (5.9, "2026-11-27"))
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.bc.pedidos[-1][1]).query)
        self.assertEqual((q["@moeda"], q["@dataInicial"], q["@dataFinalCotacao"], q["$format"]), (["'EUR'"], ["'11-18-2026'"], ["'11-28-2026'"], ["json"]))
        self.assertEqual(C.todas(date(2026, 11, 28)), MOEDAS)
        self.fora = {"GBP"}
        self.assertEqual(sorted(C.todas()), ["EUR", "USD"])
        for ruim in ({}, {"value": []}, {"value": [{"cotacaoVenda": 0, "dataHoraCotacao": "2026-11-27 13:00"}]}, []):
            with self.assertRaises(C.Erro):
                C.da_resposta(ruim)
        with self.assertRaises(C.Erro):
            C.ptax("JPY")
        with self.assertRaises(C.Erro) as cm:
            C.ptax("USD", base="http://127.0.0.1:9/ptax", timeout=2)
        self.assertEqual(str(cm.exception), "Sem resposta do Banco Central.")

    def test_moeda_pelo_nome_e_em_reais(self):
        self.assertEqual([C.moeda(x) for x in ("usd", "Dólar", "dolares", "EUR", "euros", "libra", "£", "reais", "iene", None)],
                         ["USD", "USD", "USD", "EUR", "EUR", "GBP", "GBP", "BRL", "", ""])
        self.assertEqual((C.em_reais(10, "USD", MOEDAS), C.em_reais(10, "USD", {}), C.em_reais(10, "EUR", None)), (54.32, None, None))


class TestServidor(Base):
    def test_guarda_e_so_busca_de_novo_quando_fica_velho(self):
        e = S.cambio_estado()
        self.assertEqual(e["moedas"], MOEDAS)
        n = len(self.bc.pedidos)
        self.assertEqual(S.cambio_estado()["moedas"], MOEDAS)
        self.assertEqual(len(self.bc.pedidos), n, "dentro do prazo, nada é buscado")
        with open(S.CAMBIO_ARQ, encoding="utf-8") as f:
            c = json.load(f)
        c["buscado_em"] = (datetime.now() - timedelta(hours=S.CAMBIO_HORAS + 1)).isoformat()[:19]
        with open(S.CAMBIO_ARQ, "w", encoding="utf-8") as f:
            json.dump(c, f)
        self.assertEqual(S.cambio_estado(buscar=False)["moedas"], MOEDAS)
        self.assertEqual(len(self.bc.pedidos), n)
        self.fora = {"USD", "EUR", "GBP"}
        self.assertEqual(S.cambio_estado()["moedas"], MOEDAS, "sem resposta, vale a guardada")
        self.assertEqual(len(self.bc.pedidos), n + 3)
        with open(S.CAMBIO_ARQ, "w", encoding="utf-8") as f:
            f.write("[1]")
        self.assertEqual(S.cambio_estado()["moedas"], {})

    def test_rota_e_ferramentas_pelo_correria(self):
        from tests.base import Servidor
        s = Servidor(env={"GERENCIA_PTAX": self.bc.url})
        self.addCleanup(s.parar)
        self.assertEqual(s.get("/api/cambio")[2]["moedas"], MOEDAS)
        antes = S.ler()
        self.addCleanup(lambda: S.salvar(antes, versao=False))
        S.salvar(dados_base(), versao=False)
        t = S.usar_ferramenta({"nome": "cambio", "argumentos": {"valor": 20, "moeda": "USD"}})["texto"].split("\n")
        self.assertEqual(t[0], "US$ 20,00 são R$ 108,64 pela cotação de 27/11/2026.")
        with self.assertRaises(ValueError):
            S.usar_ferramenta({"nome": "cambio", "argumentos": {"valor": 20, "moeda": "JPY"}})
        n = len(S.ler()["lancamentos"])
        t = S.usar_ferramenta({"nome": "lancar", "argumentos": {"tipo": "despesa", "descricao": "Hotel", "valor": 100, "moeda": "EUR", "data": "2026-11-20"}})["texto"]
        novo = S.ler()["lancamentos"]
        self.assertEqual(len(novo), n + 1)
        l = next(x for x in novo if x["descricao"] == "Hotel")
        self.assertEqual((l["valor"], l["obs"]), (590.0, "€ 100,00 a R$ 5,9000 (Banco Central, 27/11)"))
        self.assertIn("590,00", t)


class TestFerramentas(unittest.TestCase):
    def test_cambio_as_cotacoes_e_a_conversao(self):
        self.assertEqual(F.texto_cambio(MOEDAS, {}).split("\n"),
                         ["Cotação de venda do Banco Central (PTAX):", "- Dólar: R$ 5,4321 (27/11/2026)", "- Euro: R$ 5,9000 (27/11/2026)", "- Libra: R$ 6,8000 (27/11/2026)",
                          "No cartão ou na conta global o valor sai um pouco diferente (a cotação do banco e o IOF)."])
        self.assertEqual(F.texto_cambio(MOEDAS, {"valor": 50, "moeda": "libras"}).split("\n")[0], "£ 50,00 são R$ 340,00 pela cotação de 27/11/2026.")
        self.assertEqual(F.texto_cambio(MOEDAS, {"valor": 10}).split("\n")[0], "US$ 10,00 são R$ 54,32 pela cotação de 27/11/2026.")
        self.assertEqual(F.texto_cambio(MOEDAS, {"valor": 590, "moeda": "BRL", "para": "EUR"}).split("\n")[0], "R$ 590,00 são € 100,00 pela cotação de 27/11/2026.")
        for a, frase in (({"valor": 1, "moeda": "JPY"}, "moeda: USD, EUR, GBP ou BRL."), ({"valor": 1, "moeda": "BRL", "para": "x"}, "para: USD, EUR ou GBP."),
                         ({"valor": 0, "moeda": "USD"}, "Valor inválido")):
            with self.assertRaises(F.ErroFerramenta) as cm:
                F.texto_cambio(MOEDAS, a)
            self.assertIn(frase, str(cm.exception))
        with self.assertRaises(F.ErroFerramenta) as cm:
            F.texto_cambio({}, {})
        self.assertIn("não respondeu", str(cm.exception))
        with self.assertRaises(F.ErroFerramenta) as cm:
            F.texto_cambio({"USD": MOEDAS["USD"]}, {"valor": 1, "moeda": "GBP"})
        self.assertIn("Sem a cotação do libra", str(cm.exception))
        with self.assertRaises(LookupError):
            F.chamar("cambio", {}, dados_base())

    def test_lancar_em_outra_moeda(self):
        d = dados_base()
        hoje = date(2026, 11, 28)
        t, mudou = F.chamar("lancar", {"tipo": "despesa", "descricao": "Livro", "valor": 20, "moeda": "dólar", "obs": "presente"}, d, hoje, moedas=MOEDAS)
        self.assertTrue(mudou)
        l = d["lancamentos"][-1]
        self.assertEqual((l["valor"], l["obs"]), (108.64, "presente · US$ 20,00 a R$ 5,4321 (Banco Central, 27/11)"))
        self.assertNotIn("moeda", l)
        n = len(d["lancamentos"])
        for a, m, frase in (({"moeda": "USD"}, None, "Sem a cotação do dólar"), ({"moeda": "JPY"}, MOEDAS, "moeda: USD, EUR ou GBP")):
            with self.assertRaises(F.ErroFerramenta) as cm:
                F.chamar("lancar", {"tipo": "despesa", "descricao": "Livro", "valor": 20, **a}, d, hoje, moedas=m)
            self.assertIn(frase, str(cm.exception))
        self.assertEqual(len(d["lancamentos"]), n)
        F.chamar("lancar", {"tipo": "despesa", "descricao": "Pão", "valor": 20, "moeda": "BRL"}, d, hoje)
        self.assertEqual(d["lancamentos"][-1]["valor"], 20.0)
