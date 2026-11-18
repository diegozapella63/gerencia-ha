"""Os valores que a IA recebe (a Conversa, o WhatsApp e as ferramentas do CorrerIA) são os da tela, com cada opção.

Depois que a IA do InventarIA somou valores diferentes dos da tela (1.78.0), este arquivo confere, para cada
investimento e para o patrimônio, que o que vai para a IA (chat.resumo e as ferramentas resumo e investimentos) é a
mesma conta da tela (o calc.py, espelho do app.js; o test_tela_ia_valores.py confere o app.js de verdade):

- o valor de hoje de cada investimento, corrigido pelo rendimento ou o informado (Corrigir valores pelo rendimento);
- a renda variável (estimado) e o parado não mudam; os bens perdem valor, também separados em partes;
- o patrimônio: só o seu, investido mais os bens (os seus do tipo Bens e os do InventarIA, só com Somar os bens ligado
  e o InventarIA respondendo); o dinheiro de outras pessoas fica fora; o rende por mês é só dos investimentos.

Dados inventados (Ana, Beto, Banco Azul), a data fixa."""
import json
import re
import unittest
from datetime import date

from tests.base import importar_servidor
importar_servidor()
import calc  # noqa: E402
import chat  # noqa: E402
import ferramentas as F  # noqa: E402

HOJE = date(2026, 11, 2)
INDICES = {"cdi": 13.65, "selic": 13.75, "ipca": 4.5, "tr": 0.1}
CASA = {"ok": True, "hoje": 25432.17, "registrado": 31000.0, "n": 7}


def investimentos():
    return [
        {"id": "a", "nome": "CDB Azul", "banco": "b-azul", "tipo": "cdb", "valor": 10000, "data_valor": "2026-05-04", "indexador": "cdi_pct", "taxa": 110, "liquidez": "diaria"},
        {"id": "b", "nome": "Tesouro IPCA+ 2035", "tipo": "tesouro", "valor": 5000, "data_valor": "2026-08-03", "indexador": "ipca_mais", "taxa": 6.2},
        {"id": "c", "nome": "CDB Prefixado", "banco": "b-azul", "tipo": "cdb", "valor": 3000, "data_valor": "2026-02-02", "indexador": "pre", "taxa": 12},
        {"id": "d", "nome": "Poupança", "tipo": "poupanca", "valor": 1500, "data_valor": "2026-10-01", "indexador": "poupanca", "taxa": 0, "liquidez": "diaria"},
        {"id": "e", "nome": "Ações", "tipo": "acoes", "valor": 7000, "data_valor": "2026-01-05", "indexador": "estimado", "taxa": 8},
        {"id": "f", "nome": "Dinheiro parado", "tipo": "conta", "valor": 900, "data_valor": "2026-03-01", "indexador": "parado", "taxa": 0},
        {"id": "g", "nome": "Carro", "tipo": "bens", "valor": 60000, "data_valor": "2025-11-03", "indexador": "deprecia", "taxa": 15, "categoria_bem": "veiculos"},
        {"id": "h", "nome": "Casa da praia", "tipo": "bens", "valor": 320000, "data_valor": "2025-06-02", "indexador": "deprecia", "taxa": 0,
         "partes": [{"categoria": "imoveis", "valor": 300000, "taxa": -3}, {"categoria": "moveis", "valor": 20000, "taxa": 10}]},
        {"id": "t", "nome": "CDB da Mãe", "banco": "b-azul", "tipo": "cdb", "valor": 4000, "data_valor": "2026-07-01", "indexador": "cdi_pct", "taxa": 100,
         "titular": "terceiros", "terceiro": "Mãe"},
    ]


def dados(**ajustes):
    return {"indices": dict(INDICES), "ajustes": ajustes, "bancos": [{"id": "b-azul", "nome": "Banco Azul", "contas": []}],
            "investimentos": investimentos(), "lancamentos": [], "recorrencias": [], "categorias": calc.categorias_padrao()}


def brl(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def investimentos_da_ia(d, bens=None):
    t, mudou = F.chamar("investimentos", {}, d, HOJE, bens=bens)
    assert not mudou
    return json.loads(t)


def linha_do_resumo(texto, nome):
    return next(l for l in texto.splitlines() if f"| {nome} |" in l)


class ValorDeHoje(unittest.TestCase):
    """Cada investimento, como a tela mostra: o valor de hoje é a conta da tela (o valorHoje do app.js)."""

    def test_corrigido_pelo_rendimento(self):
        d = dados(corrigir=True)
        vh = {i["id"]: calc.valor_hoje(i, INDICES, True, HOJE) for i in d["investimentos"]}
        # o que cada um faz desde a data do valor
        for k in "abcd":
            self.assertGreater(vh[k], calc.num(next(i for i in d["investimentos"] if i["id"] == k)["valor"]), f"{k} rende")
        self.assertEqual((vh["e"], vh["f"]), (7000, 900), "a renda variável (estimado) e o parado ficam como informados")
        self.assertLess(vh["g"], 60000, "o carro perde valor")
        dias = calc.dias_uteis(date(2025, 6, 2), HOJE) / 252
        self.assertAlmostEqual(vh["h"], 300000 * 1.03 ** dias + 20000 * 0.9 ** dias, places=6, msg="cada parte na taxa dela")
        ia = investimentos_da_ia(d)
        self.assertEqual({i["id"]: i["valor_hoje"] for i in ia["investimentos"]}, {k: round(v, 2) for k, v in vh.items()})
        self.assertEqual({i["id"]: i["valor_informado"] for i in ia["investimentos"]}["a"], 10000)
        texto = chat.resumo(d, HOJE)
        for i in d["investimentos"]:
            self.assertIn(f"| {brl(round(vh[i['id']], 2))} |", linha_do_resumo(texto, i["nome"]), i["nome"])

    def test_sem_corrigir_o_informado(self):
        d = dados(corrigir=False)
        ia = investimentos_da_ia(d)
        self.assertEqual({i["id"]: i["valor_hoje"] for i in ia["investimentos"]}, {i["id"]: float(i["valor"]) for i in d["investimentos"]})
        texto = chat.resumo(d, HOJE)
        self.assertIn("| R$ 10.000,00 |", linha_do_resumo(texto, "CDB Azul"))
        self.assertIn("| R$ 320.000,00 |", linha_do_resumo(texto, "Casa da praia"))

    def test_sem_a_opcao_gravada_corrige_como_a_tela(self):
        """O app.js só deixa de corrigir com corrigir === false: sem a opção, ou com null, corrige (antes, null aqui não)."""
        certo = investimentos_da_ia(dados(corrigir=True))
        self.assertEqual(investimentos_da_ia(dados()), certo)
        self.assertEqual(investimentos_da_ia(dados(corrigir=None)), certo)
        self.assertEqual(calc.patrimonio(dados(corrigir=None), HOJE), calc.patrimonio(dados(corrigir=True), HOJE))
        self.assertEqual(chat.resumo(dados(corrigir=None), HOJE), chat.resumo(dados(corrigir=True), HOJE))


class Patrimonio(unittest.TestCase):
    """O patrimônio do placar do Agora: só o seu, investido mais os bens."""

    def conta_da_tela(self, d, casa=0.0):
        corrigir = d["ajustes"].get("corrigir", True) is not False
        meus = [i for i in d["investimentos"] if i.get("titular") != "terceiros"]
        investido = sum(calc.valor_hoje(i, INDICES, corrigir, HOJE) for i in meus if i["tipo"] != "bens")
        bens = casa + sum(calc.valor_hoje(i, INDICES, corrigir, HOJE) for i in meus if i["tipo"] == "bens")
        mes = sum(calc.rende_mes(calc.valor_hoje(i, INDICES, corrigir, HOJE), calc.taxa_anual(i, INDICES)) for i in meus if i["tipo"] != "bens")
        outras = sum(calc.valor_hoje(i, INDICES, corrigir, HOJE) for i in d["investimentos"] if i.get("titular") == "terceiros")
        return {"patrimonio": round(investido + bens, 2), "investido": round(investido, 2), "bens": round(bens, 2),
                "de_outras_pessoas": round(outras, 2), "rende_por_mes": round(mes, 2)}

    def da_ia(self, d, bens=None):
        p = investimentos_da_ia(d, bens)["patrimonio"]
        return {k: p[k] for k in ("patrimonio", "investido", "bens", "de_outras_pessoas", "rende_por_mes")}

    def test_com_os_bens_da_casa(self):
        d = dados(corrigir=True, bens=True)
        esperado = self.conta_da_tela(d, CASA["hoje"])
        self.assertEqual(self.da_ia(d, CASA), esperado)
        p = investimentos_da_ia(d, CASA)["patrimonio"]
        self.assertEqual(p["bens_da_casa"], {"valor_hoje": 25432.17, "itens": 7, "de_onde": "InventarIA, com a depreciação de cada categoria"})
        linha = next(l for l in chat.resumo(d, HOJE, CASA).splitlines() if l.startswith("Patrimônio"))
        self.assertIn(f"Patrimônio (como na tela; o dinheiro de outras pessoas fica fora): {brl(esperado['patrimonio'])} = investido {brl(esperado['investido'])} + bens {brl(esperado['bens'])}", linha)
        self.assertIn("os bens da casa do InventarIA, com o valor de hoje: R$ 25.432,17, 7 itens", linha)
        self.assertIn(f"De outras pessoas: {brl(esperado['de_outras_pessoas'])}.", linha)
        self.assertIn(f"rendem uns {brl(esperado['rende_por_mes'])} por mês", linha)

    def test_o_de_outras_pessoas_e_os_bens_nao_rendem_no_mes(self):
        d = dados(corrigir=True)
        p = self.da_ia(d)
        so_meus = [i for i in d["investimentos"] if i.get("titular") != "terceiros" and i["tipo"] != "bens"]
        self.assertAlmostEqual(p["investido"], round(sum(calc.valor_hoje(i, INDICES, True, HOJE) for i in so_meus), 2))
        self.assertGreater(p["de_outras_pessoas"], 4000, "o CDB da Mãe, corrigido, à parte")
        self.assertGreater(p["rende_por_mes"], 0)
        sem_bens = dict(d, investimentos=[i for i in d["investimentos"] if i["tipo"] != "bens"])
        self.assertEqual(self.da_ia(sem_bens)["rende_por_mes"], p["rende_por_mes"], "os bens que perdem valor não descontam do rende por mês")

    def test_somar_os_bens_desligado(self):
        """Mais › Configurações › Integrações › Bens no InventarIA desligado: o patrimônio fica sem os da casa, mesmo que
        eles cheguem (a tela faz igual: bensOn() é falso)."""
        d = dados(corrigir=True, bens=False)
        self.assertEqual(self.da_ia(d, CASA), self.conta_da_tela(d, 0))
        self.assertNotIn("bens_da_casa", investimentos_da_ia(d, CASA)["patrimonio"])
        self.assertNotIn("InventarIA", chat.resumo(d, HOJE, CASA))

    def test_inventaria_fora_do_ar_ou_sem_itens(self):
        d = dados(corrigir=True)
        sem = self.conta_da_tela(d, 0)
        for b in ({"ok": False, "motivo": "O InventarIA não respondeu."}, {"ok": True, "hoje": 900.0, "n": 0}, None, {"ok": False, "desligado": True}):
            self.assertEqual(self.da_ia(d, b), sem, b)
        self.assertEqual(calc.patrimonio(d, HOJE, bens_casa=-50)["bens_da_casa"], 0, "um valor negativo não tira do patrimônio")

    def test_sem_corrigir(self):
        d = dados(corrigir=False)
        p = self.da_ia(d, CASA)
        self.assertEqual(p["investido"], 10000 + 5000 + 3000 + 1500 + 7000 + 900)
        self.assertEqual(p["bens"], round(60000 + 320000 + CASA["hoje"], 2))
        self.assertEqual(p["de_outras_pessoas"], 4000)
        self.assertEqual(p, self.conta_da_tela(d, CASA["hoje"]))

    def test_resumo_da_ferramenta_e_o_da_conversa(self):
        """A ferramenta resumo do CorrerIA é o mesmo texto da Conversa (os mesmos números)."""
        d = dados(corrigir=True)
        t, _ = F.chamar("resumo", {}, d, HOJE, bens=CASA)
        self.assertEqual(t, chat.resumo(d, HOJE, CASA))

    def test_so_investimentos_de_outras_pessoas(self):
        d = dados(corrigir=True)
        d["investimentos"] = [i for i in d["investimentos"] if i.get("titular") == "terceiros"]
        p = self.da_ia(d)
        self.assertEqual((p["patrimonio"], p["investido"], p["bens"], p["rende_por_mes"]), (0, 0, 0, 0))
        self.assertGreater(p["de_outras_pessoas"], 4000)


class MuitosInvestimentos(unittest.TestCase):
    def test_a_lista_cortada_e_os_totais_de_todos(self):
        """Com mais de 80 investimentos, a Conversa recebe 80 e diz quantos são; o patrimônio conta todos."""
        d = dados(corrigir=False)
        d["investimentos"] = [{"id": f"x{k}", "nome": f"CDB {k:03d}", "tipo": "cdb", "valor": 100, "indexador": "parado"} for k in range(90)]
        texto = chat.resumo(d, HOJE)
        self.assertEqual(len(re.findall(r"^x\d+ \| CDB", texto, re.M)), 80)
        self.assertIn("… e mais 10 investimentos (os totais abaixo contam todos) que não couberam aqui (são 90 ao todo).", texto)
        self.assertIn("Patrimônio (como na tela; o dinheiro de outras pessoas fica fora): R$ 9.000,00", texto)


if __name__ == "__main__":
    unittest.main()
