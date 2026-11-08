"""ferramentas.py: o que o CorrerIA (WhatsApp, Claude e Gemini) lê e grava no GerencIA. Com a data fixa e dados
inventados (Ana, Banco Azul). As regras são as da tela: parcelas, cartão (paga com a fatura), fixo do mês, aporte."""
import json
import re
import unittest
from datetime import date

from tests.base import importar_servidor
importar_servidor()
import calc  # noqa: E402
import ferramentas as F  # noqa: E402
from tests.test_integracao import dados as dados_base  # noqa: E402

HOJE = date(2026, 11, 15)


def dados():
    d = dados_base()
    d["categorias"] = calc.categorias_padrao() + d["categorias"]
    d["investimentos"] = [
        {"id": "i1", "nome": "CDB Azul", "banco": "b1", "tipo": "cdb", "valor": 10000, "data_valor": "2026-11-15", "indexador": "cdi_pct", "taxa": 100, "liquidez": "diaria"},
        {"id": "i2", "nome": "Poupança do Beto", "banco": "b1", "tipo": "poupanca", "valor": 800, "data_valor": "2026-11-15", "indexador": "poupanca",
         "taxa": 0, "liquidez": "diaria", "titular": "terceiros", "terceiro": "Beto"},
    ]
    d["indices"] = {"cdi": 10.65, "selic": 10.75, "ipca": 4.5, "tr": 0.1}
    d["ajustes"] = {}
    return d


def chamar(nome, args, d):
    return F.chamar(nome, args, d, HOJE)


def json_de(nome, args, d):
    t, mudou = chamar(nome, args, d)
    assert not mudou
    return json.loads(t)


class TestLista(unittest.TestCase):
    def test_formato_do_contrato(self):
        fs = F.lista()
        nomes = [f["nome"] for f in fs]
        self.assertEqual(nomes, ["resumo", "lancamentos", "contas_a_pagar", "investimentos", "cadastros", "lancar", "editar_lancamento",
                                 "apagar_lancamento", "marcar_pago", "atualizar_investimento", "novo_investimento", "novo_fixo"])
        for f in fs:
            self.assertRegex(f["nome"], r"^[a-z0-9_]{1,40}$")
            self.assertTrue(f["titulo"] and f["descricao"])
            self.assertEqual((f["entrada"]["type"], f["entrada"]["additionalProperties"]), ("object", False))
            self.assertTrue(set(f["entrada"]["required"]) <= set(f["entrada"]["properties"]), f["nome"])
            self.assertIsInstance(f["grava"], bool)
            self.assertIsInstance(f["apaga"], bool)
        self.assertEqual([f["nome"] for f in fs if f["apaga"]], ["apagar_lancamento"])
        self.assertEqual([f["nome"] for f in fs if not f["grava"]], nomes[:5])
        json.dumps(fs)  # vai como JSON

    def test_desconhecida(self):
        with self.assertRaises(LookupError):
            chamar("sacar", {}, dados())


class TestLeitura(unittest.TestCase):
    def test_resumo_e_o_da_ia_do_app(self):
        t, mudou = chamar("resumo", {}, dados())
        self.assertFalse(mudou)
        self.assertIn("Hoje é domingo, 15/11/2026.", t)
        self.assertIn("v:r-net:2026-11 | Internet", t, "com os ids das contas")

    def test_lancamentos_do_mes(self):
        r = json_de("lancamentos", {}, dados())
        self.assertEqual(r["periodo"], {"de": "2026-11-01", "ate": "2026-11-30"})
        por_id = {x.get("id"): x for x in r["lancamentos"]}
        self.assertNotIn("l-pulado", por_id)
        self.assertEqual(por_id["v:r-net:2026-11"]["fixo"], "ainda não lançado", "o fixo do mês, com o id que paga")
        self.assertEqual(por_id["k1"]["conta"], "Banco Azul · Ana · cartão de crédito")
        self.assertEqual(por_id["k1"]["data_caixa"], "2026-12-10", "a compra no cartão sai na fatura")
        self.assertEqual(por_id["l-aj"]["tipo"], "ajuste de saldo")
        self.assertEqual(r["entradas"], 5000 + 3000 + 15)
        self.assertEqual(r["gastos_por_categoria"]["Casa"], 300.46)
        self.assertNotIn("Ajuste", json.dumps(r["gastos_por_categoria"]))
        datas = [x["data"] for x in r["lancamentos"]]
        self.assertEqual(datas, sorted(datas, reverse=True))

    def test_lancamentos_filtros_e_limite(self):
        d = dados()
        r = json_de("lancamentos", {"busca": "mercado"}, d)
        self.assertEqual([x["id"] for x in r["lancamentos"]], ["k1"])
        r = json_de("lancamentos", {"tipo": "receita"}, d)
        self.assertEqual({x["descricao"] for x in r["lancamentos"]}, {"Salário", "Salário fixo", "Estorno"})
        r = json_de("lancamentos", {"categoria": "casa"}, d)
        self.assertEqual({x["descricao"] for x in r["lancamentos"]}, {"Luz", "Internet"})
        r = json_de("lancamentos", {"conta": "Banco Azul", "limite": 2}, d)
        self.assertEqual((r["encontrados"], r["mostrando"]), (3, 2))
        r = json_de("lancamentos", {"de": "2026-10-01", "ate": "2026-10-31"}, d)
        self.assertEqual({x["descricao"] for x in r["lancamentos"]}, {"Atrasada", "Internet", "Salário fixo", "Sem id"})
        with self.assertRaisesRegex(F.ErroFerramenta, "Período grande demais"):
            chamar("lancamentos", {"de": "2024-01-01", "ate": "2026-01-01"}, d)
        with self.assertRaisesRegex(F.ErroFerramenta, "antes do começo"):
            chamar("lancamentos", {"de": "2026-11-10", "ate": "2026-11-01"}, d)
        with self.assertRaisesRegex(F.ErroFerramenta, "Data inválida|De inválida"):
            chamar("lancamentos", {"de": "ontem à noite"}, d)

    def test_contas_a_pagar(self):
        r = json_de("contas_a_pagar", {}, dados())
        ids = [c["id"] for c in r["contas"]]
        self.assertIn("f:cc|2026-12-10", ids, "a fatura do cartão")
        self.assertIn("v:r-net:2026-11", ids)
        f = next(c for c in r["contas"] if c["id"] == "f:cc|2026-12-10")
        self.assertEqual((f["tipo"], f["valor"], f["situacao"]), ("fatura", 125.0, "a pagar"))
        self.assertGreater(r["atrasadas"], 0)

    def test_investimentos_e_cadastros(self):
        d = dados()
        r = json_de("investimentos", {}, d)
        self.assertEqual(r["patrimonio"]["de_outras_pessoas"], 800.0)
        i2 = next(i for i in r["investimentos"] if i["id"] == "i2")
        self.assertEqual((i2["de_quem"], i2["banco"], i2["liquidez"]), ("Beto", "Banco Azul", "diária"))
        c = json_de("cadastros", {}, d)
        self.assertEqual(c["contas"], [{"id": "cc", "nome": "Banco Azul · Ana", "banco": "Banco Azul", "pessoa": "Ana",
                                        "cartao_de_credito": {"fecha_dia": 5, "vence_dia": 10}}])
        self.assertEqual(c["pessoas_terceiros"], ["Beto"])
        self.assertIn("cdb", c["tipos_investimento"])
        self.assertEqual(c["fixos"][0]["id"], "r-net")


class TestLancar(unittest.TestCase):
    def test_gasto_simples_pago_pela_data(self):
        d = dados()
        t, mudou = chamar("lancar", {"tipo": "despesa", "descricao": "Padaria", "valor": "12,50", "categoria": "Mercado", "data": "ontem"}, d)
        self.assertTrue(mudou)
        l = d["lancamentos"][-1]
        self.assertEqual((l["descricao"], l["valor"], l["data"], l["categoria"], l["pago"], l["cartao"]), ("Padaria", 12.5, "2026-11-14", "c-mercado", True, False))
        self.assertTrue(t.startswith("Lançado: Padaria · R$ 12,50 · 14/11/2026 · Mercado · pago. id: "))
        chamar("lancar", {"tipo": "receita", "descricao": "Pix do João", "valor": 50, "data": "2026-11-30"}, d)
        l = d["lancamentos"][-1]
        self.assertEqual((l["categoria"], l["pago"]), ("c-outros-receb", False), "sem categoria: Outros; no futuro: a receber")

    def test_no_cartao_segue_a_fatura(self):
        d = dados()
        t, _ = chamar("lancar", {"tipo": "despesa", "descricao": "Posto", "valor": 200, "conta": "Banco Azul · Ana", "cartao": True}, d)
        self.assertFalse(d["lancamentos"][-1]["pago"], "a fatura vence em 10/12")
        self.assertIn("cartão de crédito, fatura de 10/12/2026", t)
        with self.assertRaisesRegex(F.ErroFerramenta, "Diga a conta do cartão"):
            chamar("lancar", {"tipo": "despesa", "descricao": "X", "valor": 1, "cartao": True}, d)

    def test_parcelado(self):
        d = dados()
        antes = len(d["lancamentos"])
        t, _ = chamar("lancar", {"tipo": "despesa", "descricao": "Geladeira", "valor": 250, "parcelas": 10, "parcela_atual": 3,
                                 "data": "2026-11-12", "conta": "cc", "cartao": True}, d)
        novos = d["lancamentos"][antes:]
        self.assertEqual([x["parcela"] for x in novos], [f"{p}/10" for p in range(3, 11)])
        self.assertEqual(novos[1]["data"], "2026-12-12")
        self.assertEqual(len({x["grupo"] for x in novos}), 1)
        self.assertTrue(all(not x["pago"] for x in novos))
        self.assertTrue(t.startswith("Lançadas 8 parcelas de R$ 250,00 (3/10 a 10/10), de 12/11/2026 a 12/06/2027."))
        with self.assertRaisesRegex(F.ErroFerramenta, "parcela_atual"):
            chamar("lancar", {"tipo": "despesa", "descricao": "X", "valor": 1, "parcelas": 3, "parcela_atual": 5}, d)

    def test_aporte_e_aviso_de_repetido(self):
        d = dados()
        chamar("lancar", {"tipo": "despesa", "descricao": "Aplicação", "valor": 500, "categoria": "c-investimentos"}, d)
        self.assertTrue(d["lancamentos"][-1]["aporte"])
        t, _ = chamar("lancar", {"tipo": "despesa", "descricao": "aplicação", "valor": 500, "categoria": "Investimentos"}, d)
        self.assertIn("Atenção: já havia um lançamento igual", t)

    def test_erros_dizem_o_que_vale(self):
        d = dados()
        casos = [({"tipo": "gasto", "descricao": "a", "valor": 1}, "tipo: despesa"), ({"tipo": "despesa", "descricao": " ", "valor": 1}, "Falta a descrição"),
                 ({"tipo": "despesa", "descricao": "a", "valor": 0}, "Valor inválido"), ({"tipo": "despesa", "descricao": "a", "valor": 1, "categoria": "Salário"}, "As de gasto: Moradia"),
                 ({"tipo": "despesa", "descricao": "a", "valor": 1, "conta": "Banco Roxo"}, "Conta não encontrada: Banco Roxo. As contas: Banco Azul · Ana (cc)"),
                 ({"tipo": "despesa", "descricao": "a", "valor": 1, "data": "31/02/2026"}, "Data inválida")]
        for args, msg in casos:
            with self.assertRaisesRegex(F.ErroFerramenta, re.escape(msg)):
                chamar("lancar", args, d)
        self.assertEqual(d["lancamentos"], dados()["lancamentos"], "nada gravado")


class TestMudar(unittest.TestCase):
    def test_editar(self):
        d = dados()
        t, _ = chamar("editar_lancamento", {"id": "l-luz", "valor": 200, "categoria": "Contas da casa", "obs": "veio alta"}, d)
        l = next(x for x in d["lancamentos"] if x["id"] == "l-luz")
        self.assertEqual((l["valor"], l["categoria"], l["obs"]), (200, "c-contas", "veio alta"))
        self.assertIn("Antes: Luz · R$ 180,46", t)
        chamar("editar_lancamento", {"id": "k2", "conta": ""}, d)
        k2 = next(x for x in d["lancamentos"] if x["id"] == "k2")
        self.assertEqual((k2["conta"], k2["cartao"]), ("", False), "sem conta, sem cartão")
        with self.assertRaisesRegex(F.ErroFerramenta, "Diga o que muda"):
            chamar("editar_lancamento", {"id": "l-luz"}, d)
        with self.assertRaisesRegex(F.ErroFerramenta, "Não encontrei o lançamento zzz"):
            chamar("editar_lancamento", {"id": "zzz", "valor": 1}, d)
        with self.assertRaisesRegex(F.ErroFerramenta, "fatura de cartão"):
            chamar("editar_lancamento", {"id": "f:cc|2026-12-10", "valor": 1}, d)

    def test_editar_o_fixo_do_mes_so_naquele_mes(self):
        d = dados()
        chamar("editar_lancamento", {"id": "v:r-net:2026-11", "valor": 130}, d)
        x = next(l for l in d["lancamentos"] if l.get("recorrencia") == "r-net")
        self.assertEqual((x["competencia"], x["valor"], x["pago"]), ("2026-11", 130, False))
        self.assertEqual(d["recorrencias"][0]["valor"], 120, "o fixo continua igual")

    def test_apagar(self):
        d = dados()
        t, _ = chamar("apagar_lancamento", {"id": "l-agua"}, d)
        self.assertFalse(any(x["id"] == "l-agua" for x in d["lancamentos"]))
        self.assertTrue(t.startswith("Apagado: Água"))
        t, _ = chamar("apagar_lancamento", {"id": "v:r-net:2026-12"}, d)
        x = next(l for l in d["lancamentos"] if l.get("recorrencia") == "r-net")
        self.assertEqual((x["competencia"], x["pulado"]), ("2026-12", True))
        self.assertTrue(t.startswith("Apagado só deste mês"))
        r = json_de("contas_a_pagar", {"de": "2026-12-01", "ate": "2026-12-31"}, d)
        self.assertNotIn("v:r-net:2026-12", [c["id"] for c in r["contas"]])

    def test_marcar_pago(self):
        d = dados()
        t, _ = chamar("marcar_pago", {"id": "v:r-net:2026-11", "valor": 125}, d)
        x = next(l for l in d["lancamentos"] if l.get("recorrencia") == "r-net")
        self.assertEqual((x["pago"], x["valor"]), (True, 125))
        self.assertTrue(t.startswith("Marcado: Internet · R$ 125,00"))
        t, _ = chamar("marcar_pago", {"id": "v:r-net:2026-11", "pago": False}, d)
        self.assertFalse(x["pago"])
        self.assertTrue(t.startswith("Desfeito: "))
        chamar("marcar_pago", {"id": "v:r-sal:2026-11"}, d)  # recebimento também
        self.assertTrue(next(l for l in d["lancamentos"] if l.get("recorrencia") == "r-sal")["pago"])
        t, _ = chamar("marcar_pago", {"id": "f:cc|2026-12-10"}, d)
        self.assertTrue(t.startswith("Paga: Fatura Banco Azul · Ana · R$ 125,00 · vence 10/12/2026 (3 compras)."))
        self.assertTrue(all(l["pago"] for l in d["lancamentos"] if l["id"] in ("k1", "k2", "k3")))
        with self.assertRaisesRegex(F.ErroFerramenta, "inteira"):
            chamar("marcar_pago", {"id": "f:cc|2026-12-10", "valor": 10}, d)
        with self.assertRaisesRegex(F.ErroFerramenta, "Fatura não encontrada"):
            chamar("marcar_pago", {"id": "f:cc|2030-01-10"}, d)
        with self.assertRaisesRegex(F.ErroFerramenta, "não se paga"):
            chamar("marcar_pago", {"id": "l-aj"}, d)


class TestInvestimentos(unittest.TestCase):
    def test_saldo_aporte_e_resgate(self):
        d = dados()
        t, _ = chamar("atualizar_investimento", {"id": "i1", "aporte": 3000}, d)
        self.assertEqual((d["investimentos"][0]["valor"], d["investimentos"][0]["data_valor"]), (13000, "2026-11-15"))
        self.assertEqual(t, "Atualizado: CDB Azul: R$ 10.000,00 → R$ 13.000,00 (aporte de R$ 3.000,00).")
        t, _ = chamar("atualizar_investimento", {"id": "i1", "resgate": 1000}, d)
        self.assertIn("resgate de R$ 1.000,00", t)
        chamar("atualizar_investimento", {"id": "i1", "saldo": 0}, d)
        self.assertEqual(d["investimentos"][0]["valor"], 0)
        for args, msg in (({"id": "i1"}, "Mande um só"), ({"id": "i1", "saldo": 1, "aporte": 1}, "Mande um só"),
                          ({"id": "i1", "resgate": 50}, "maior que o valor de hoje"), ({"id": "x", "saldo": 1}, "Investimento não encontrado")):
            with self.assertRaisesRegex(F.ErroFerramenta, msg):
                chamar("atualizar_investimento", args, d)

    def test_bem_com_partes_divide_o_valor(self):
        d = dados()
        d["investimentos"].append({"id": "bem", "nome": "Carro", "tipo": "bens", "indexador": "deprecia", "taxa": 0, "valor": 100,
                                   "data_valor": "2026-11-15", "partes": [{"categoria": "veiculos", "valor": 75, "taxa": 0}, {"categoria": "outros", "valor": 25, "taxa": 0}]})
        chamar("atualizar_investimento", {"id": "bem", "saldo": 200}, d)
        self.assertEqual([p["valor"] for p in d["investimentos"][-1]["partes"]], [150, 50])

    def test_novo(self):
        d = dados()
        t, _ = chamar("novo_investimento", {"nome": "Tesouro Selic", "valor": 500, "tipo": "tesouro", "banco": "Corretora Sol"}, d)
        i = d["investimentos"][-1]
        self.assertEqual((i["indexador"], i["taxa"], i["liquidez"], i["titular"]), ("selic_mais", 0, "diaria", "meu"))
        b = d["bancos"][-1]
        self.assertEqual((b["nome"], i["banco"]), ("Corretora Sol", b["id"]), "banco novo")
        self.assertNotEqual(b["cor"], d["bancos"][0].get("cor"))
        self.assertIn("Tesouro Selic · Corretora Sol · Tesouro", t)
        chamar("novo_investimento", {"nome": "LCI", "valor": 1000, "tipo": "lci", "banco": "banco azul", "taxa": 92, "vencimento": "2028-01-10", "de_quem": "Beto"}, d)
        i = d["investimentos"][-1]
        self.assertEqual((i["banco"], i["taxa"], i["vencimento"], i["titular"], i["terceiro"]), ("b1", 92, "2028-01-10", "terceiros", "Beto"))
        with self.assertRaisesRegex(F.ErroFerramenta, "Tipo inválido"):
            chamar("novo_investimento", {"nome": "X", "valor": 1, "tipo": "bens"}, d)

    def test_novo_fixo(self):
        d = dados()
        t, _ = chamar("novo_fixo", {"tipo": "despesa", "descricao": "Academia", "valor": 99.9, "data": "2026-11-20", "categoria": "Saúde"}, d)
        r = d["recorrencias"][-1]
        self.assertEqual((r["dia"], r["inicio"], r["fim"], r["categoria"]), (20, "2026-11", None, "c-saude"))
        self.assertIn(f"id v:{r['id']}:2026-11", t)
        ids = [c["id"] for c in json_de("contas_a_pagar", {}, d)["contas"]]
        self.assertIn(f"v:{r['id']}:2026-11", ids, "já aparece nas contas a pagar")
        chamar("novo_fixo", {"tipo": "despesa", "descricao": "IPVA", "valor": 1500, "data": "2027-03-10", "repete": "anual"}, d)
        self.assertEqual(d["recorrencias"][-1]["freq"], "anual")
        with self.assertRaisesRegex(F.ErroFerramenta, "Falta data"):
            chamar("novo_fixo", {"tipo": "despesa", "descricao": "X", "valor": 1}, d)


if __name__ == "__main__":
    unittest.main()
