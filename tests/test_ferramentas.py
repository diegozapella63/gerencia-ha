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


def chamar(nome, args, d, bens=None):
    return F.chamar(nome, args, d, HOJE, bens=bens)


def json_de(nome, args, d):
    t, mudou = chamar(nome, args, d)
    assert not mudou
    return json.loads(t)


class TestLista(unittest.TestCase):
    def test_formato_do_contrato(self):
        fs = F.lista()
        nomes = [f["nome"] for f in fs]
        self.assertEqual(nomes, ["resumo", "lancamentos", "comparar_meses", "fora_do_padrao", "projecao", "contas_a_pagar", "investimentos", "cadastros", "faturas_do_email", "beneficios", "oportunidades", "dicas", "lancar",
                                 "editar_lancamento", "alterar_lancamentos", "apagar_lancamento", "marcar_pago", "atualizar_investimento", "novo_investimento",
                                 "ajustar_saldo", "lancar_fatura_do_email", "ignorar_fatura_do_email", "editar_fixo", "encerrar_fixo",
                                 "usar_beneficio", "atualizar_milhas", "nova_categoria", "editar_categoria", "editar_banco", "novo_banco", "novo_fixo"])
        for f in fs:
            self.assertRegex(f["nome"], r"^[a-z0-9_]{1,40}$")
            self.assertTrue(f["titulo"] and f["descricao"])
            self.assertEqual((f["entrada"]["type"], f["entrada"]["additionalProperties"]), ("object", False))
            self.assertTrue(set(f["entrada"]["required"]) <= set(f["entrada"]["properties"]), f["nome"])
            self.assertIsInstance(f["grava"], bool)
            self.assertIsInstance(f["apaga"], bool)
        self.assertEqual([f["nome"] for f in fs if f["apaga"]], ["apagar_lancamento", "encerrar_fixo", "editar_categoria"])
        self.assertEqual([f["nome"] for f in fs if not f["grava"]], nomes[:12])
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
        # 1.78.0: o patrimônio da tela: só o seu (investido mais os bens), com os bens da casa do InventarIA
        self.assertEqual(r["patrimonio"]["patrimonio"], r["patrimonio"]["investido"] + r["patrimonio"]["bens"])
        com = json.loads(chamar("investimentos", {}, d, bens={"ok": True, "hoje": 12345.67, "n": 3})[0])["patrimonio"]
        self.assertEqual(com["bens_da_casa"], {"valor_hoje": 12345.67, "itens": 3, "de_onde": "InventarIA, com a depreciação de cada categoria"})
        self.assertAlmostEqual(com["patrimonio"], r["patrimonio"]["patrimonio"] + 12345.67, places=2)
        self.assertIn("R$ 12.345,67", chamar("resumo", {}, d, bens={"ok": True, "hoje": 12345.67, "n": 3})[0])
        i2 = next(i for i in r["investimentos"] if i["id"] == "i2")
        self.assertEqual((i2["de_quem"], i2["banco"], i2["liquidez"]), ("Beto", "Banco Azul", "diária"))
        c = json_de("cadastros", {}, d)
        self.assertEqual(c["contas"], [{"id": "cc", "nome": "Banco Azul · Ana", "banco": "Banco Azul", "pessoa": "Ana", "cartao_de_debito": True,
                                        "cartao_de_credito": {"fecha_dia": 5, "vence_dia": 10}}])
        d["bancos"][0]["contas"][0]["debito"] = False
        self.assertFalse(json_de("cadastros", {}, d)["contas"][0]["cartao_de_debito"], "1.57.0: sem cartão de débito")
        del d["bancos"][0]["contas"][0]["debito"]
        # 1.62.0: os cartões globais, cada um com a moeda; o de crédito diz se tem adicional
        d["bancos"][0]["contas"][0].update(debito_global="USD", credito_global="EUR", credito_global_adicional=True)
        g = json_de("cadastros", {}, d)["contas"][0]
        self.assertEqual((g["cartao_de_debito_global"], g["cartao_de_credito_global"]), ({"moeda": "USD", "adicional": False}, {"moeda": "EUR", "adicional": True}))
        d["bancos"][0]["contas"][0].update(debito_global_adicional=True, debito_global_para="Ana")  # 1.77.0: o adicional do débito global
        self.assertEqual(json_de("cadastros", {}, d)["contas"][0]["cartao_de_debito_global"], {"moeda": "USD", "adicional": True, "adicional_para": "Ana"})
        for k in ("debito_global_adicional", "debito_global_para"):
            del d["bancos"][0]["contas"][0][k]
        d["bancos"][0]["contas"][0]["credito_global_para"] = "Beto"
        self.assertEqual(json_de("cadastros", {}, d)["contas"][0]["cartao_de_credito_global"], {"moeda": "EUR", "adicional": True, "adicional_para": "Beto"}, "1.74.2")
        del d["bancos"][0]["contas"][0]["credito_global_para"]
        d["bancos"][0]["contas"][0].update(cartao=True, adicionais=[{"id": "a1", "pessoa": "Beto", "mesmo_limite": True}])
        self.assertEqual(json_de("cadastros", {}, d)["contas"][0]["cartao_de_credito"]["adicionais"], [{"pessoa": "Beto", "limite": "o mesmo do cartão principal"}], "1.74.3")
        del d["bancos"][0]["contas"][0]["adicionais"]
        for k in ("debito_global", "credito_global", "credito_global_adicional"):
            del d["bancos"][0]["contas"][0][k]
        self.assertEqual(c["pessoas_terceiros"], ["Beto"])
        d["bancos"][0]["contas"][0].update(limite=5000, adicionais=[{"id": "a1", "pessoa": "Beto", "limite": 1500}, {"id": "a2", "pessoa": ""}])
        cc = json_de("cadastros", {}, d)["contas"][0]["cartao_de_credito"]
        self.assertEqual(cc, {"fecha_dia": 5, "vence_dia": 10, "limite": 5000, "adicionais": [{"pessoa": "Beto", "limite": 1500}]}, "o limite e os adicionais")
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

    def test_ajustar_saldo(self):
        """1.85.0: o Ajustar saldo da tela, pela ferramenta: a diferença vira um lançamento de ajuste, pago hoje."""
        d = dados()
        antes = round(F.calc.caixa(d, HOJE)["saldo"], 2)
        n = len(d["lancamentos"])
        t, mudou = chamar("ajustar_saldo", {"saldo": antes}, d)
        self.assertEqual((t, len(d["lancamentos"])), (f"O saldo já está certo: {F._brl(antes)}.", n))
        t, mudou = chamar("ajustar_saldo", {"saldo": antes + 150.5}, d)
        l = d["lancamentos"][-1]
        self.assertEqual((mudou, l["tipo"], l["descricao"], l["valor"], l["ajuste"], l["pago"], l["data"], l["categoria"]),
                         (True, "receita", "Ajuste de saldo", 150.5, True, True, HOJE.isoformat(), ""))
        self.assertIn("(ajuste de +R$ 150,50)", t)
        self.assertAlmostEqual(F.calc.caixa(d, HOJE)["saldo"], antes + 150.5, places=2)
        chamar("ajustar_saldo", {"saldo": -20}, d)
        self.assertEqual((d["lancamentos"][-1]["tipo"], round(F.calc.caixa(d, HOJE)["saldo"], 2)), ("despesa", -20))
        for ruim in ("mil", None, True, float("nan")):
            with self.assertRaises(F.ErroFerramenta):
                chamar("ajustar_saldo", {"saldo": ruim}, d)

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


class TestBordas(unittest.TestCase):
    """O que a IA pode mandar torto: cada erro diz o que vale e nada é gravado pela metade."""

    def erro(self, nome, args, msg, d=None):
        d = d if d is not None else dados()
        antes = json.dumps(d, sort_keys=True)
        with self.assertRaisesRegex(F.ErroFerramenta, msg):
            chamar(nome, args, d)
        self.assertEqual(json.dumps(d, sort_keys=True), antes, f"{nome} {args}: nada gravado")

    def test_datas_e_valores(self):
        d = dados()
        chamar("lancar", {"tipo": "despesa", "descricao": "Pão", "valor": "12,50", "data": "amanhã"}, d)
        self.assertEqual((d["lancamentos"][-1]["data"], d["lancamentos"][-1]["valor"]), ("2026-11-16", 12.5))
        self.erro("lancar", {"tipo": "despesa", "descricao": "a", "valor": 2e10}, "Valor grande demais")

    def test_lancamentos_do_periodo_e_detalhes(self):
        d = dados()
        d["lancamentos"] += [{"id": "l-d", "tipo": "despesa", "descricao": "Desconto da luz", "valor": 5, "data": "2026-11-21", "desconto": True, "pai": "l-luz"},
                             {"id": "l-tv", "tipo": "despesa", "descricao": "TV", "valor": 50, "data": "2026-11-08", "parcela": "2/10", "obs": "loja"}]
        r = json_de("lancamentos", {"de": "2026-11-10", "ate": "2026-11-30"}, d)
        nomes = {x["descricao"] for x in r["lancamentos"]}
        self.assertNotIn("Água", nomes, "dia 3: fora do período, mesmo sendo do mês")
        desc = next(x for x in r["lancamentos"] if x["descricao"] == "Desconto da luz")
        self.assertEqual((desc["de"], "id" in desc), ("l-luz", False), "o desconto diz de quem é e não tem id próprio")
        tv = json_de("lancamentos", {"busca": "tv"}, d)["lancamentos"][0]
        self.assertEqual((tv["parcela"], tv["obs"]), ("2/10", "loja"))
        r = json_de("lancamentos", {"categoria": "cas"}, d)
        self.assertEqual({x["descricao"] for x in r["lancamentos"]}, {"Luz", "Internet"}, "sem tipo, também pelo começo do nome")
        self.erro("lancamentos", {"categoria": "Viagem"}, "Categoria não encontrada: Viagem")

    def test_contas_a_pagar_periodo_invalido(self):
        self.erro("contas_a_pagar", {"de": "2026-12-01", "ate": "2026-11-01"}, "Período inválido")

    def test_investimentos_e_fixos_com_detalhes(self):
        d = dados()
        d["investimentos"][0].update(vencimento="2028-01-10", obs="para a reforma")
        d["recorrencias"][0]["fim"] = "2027-06"
        i1 = json_de("investimentos", {}, d)["investimentos"][0]
        self.assertEqual((i1["vencimento"], i1["obs"]), ("2028-01-10", "para a reforma"))
        self.assertEqual(json_de("cadastros", {}, d)["fixos"][0]["ate"], "2027-06")

    def test_parcelas_fora_do_limite(self):
        base = {"tipo": "despesa", "descricao": "Sofá", "valor": 1200}
        self.erro("lancar", dict(base, parcelas=1), "parcelas: de 2 a 120")
        self.erro("lancar", dict(base, parcelas=121), "parcelas: de 2 a 120")
        self.erro("lancar", dict(base, parcelas=3, parcela_atual=4), "parcela_atual: de 1 até o total")

    def test_ids_ruins(self):
        self.erro("editar_lancamento", {"id": " ", "valor": 1}, "Falta o id")
        for lid in ("v:", "v:r-net", "v:r-net:2026-13", "v:r-net:26-1"):
            with self.subTest(lid=lid):
                self.erro("editar_lancamento", {"id": lid, "valor": 1}, "Id inválido")

    def test_editar_cada_campo(self):
        d = dados()
        t, _ = chamar("editar_lancamento", {"id": "l-luz", "descricao": "Conta de luz", "data": "2026-11-22", "pago": True}, d)
        l = next(x for x in d["lancamentos"] if x["id"] == "l-luz")
        self.assertEqual((l["descricao"], l["data"], l["pago"]), ("Conta de luz", "2026-11-22", True))
        chamar("editar_lancamento", {"id": "l-luz", "descricao": "  "}, d)
        self.assertEqual(l["descricao"], "Conta de luz", "descrição vazia: fica a de antes")
        self.erro("editar_lancamento", {"id": "l-luz", "cartao": True}, "Essa conta não tem cartão de crédito", d)
        self.erro("editar_lancamento", {"id": "l-pulado", "valor": 2}, "apagado deste mês", d)
        d["lancamentos"].append({"id": "l-ap", "tipo": "despesa", "descricao": "Aplicação", "valor": 500, "data": "2026-11-09", "aporte": True,
                                 "categoria": "c-investimentos"})
        chamar("editar_lancamento", {"id": "l-ap", "conta": "cc", "cartao": True}, d)
        self.assertIs(d["lancamentos"][-1]["cartao"], False, "aporte nunca vai no cartão")

    def test_marcar_pago_bordas(self):
        d = dados()
        self.erro("marcar_pago", {"id": "l-pulado"}, "apagado deste mês", d)
        t, mudou = chamar("marcar_pago", {"id": "v:r-net:2026-12", "pago": False}, d)
        self.assertTrue(t.startswith("Já estava a pagar: Internet"))
        self.assertFalse(any(l.get("competencia") == "2026-12" for l in d["lancamentos"]), "nada criado")

    def test_novo_investimento_bordas(self):
        self.erro("novo_investimento", {"nome": " ", "valor": 1, "tipo": "cdb"}, "Falta o nome")
        self.erro("novo_investimento", {"nome": "X", "valor": 1, "tipo": "cdb", "indexador": "bitcoin"}, "Rendimento inválido")
        d = dados()
        t, _ = chamar("novo_investimento", {"nome": "Reserva", "valor": 100, "tipo": "cdb", "de_quem": "Meu"}, d)
        self.assertEqual((d["investimentos"][-1]["titular"], d["investimentos"][-1]["terceiro"]), ("meu", ""))
        self.assertNotIn(" · de ", t)

    def test_novo_fixo_bordas(self):
        base = {"tipo": "despesa", "descricao": "Academia", "valor": 99, "data": "2026-11-20"}
        self.erro("novo_fixo", dict(base, tipo="gasto"), "tipo: despesa")
        self.erro("novo_fixo", dict(base, descricao=""), "Falta a descrição")
        self.erro("novo_fixo", dict(base, cartao=True), "Diga a conta do cartão de crédito")
        d = dados()
        d["bancos"][0]["contas"].append({"id": "cd", "pessoa": "Beto"})
        self.erro("novo_fixo", dict(base, cartao=True, conta="cd"), "Essa conta não tem cartão de crédito", d)
        chamar("novo_fixo", dict(base, descricao="Aplicação mensal", categoria="c-investimentos", cartao=True, conta="cc"), d)
        r = d["recorrencias"][-1]
        self.assertEqual((r["aporte"], r["cartao"]), (True, False), "aporte: sem cartão, como na tela")


if __name__ == "__main__":
    unittest.main()


class TestNovas188(unittest.TestCase):
    """1.88.0 (o dono: "todas"): mudar e encerrar um fixo, usar um benefício, resgatar e atualizar milhas, criar categoria e
    cadastrar banco ou conta, com as regras da tela."""

    def setUp(self):
        self.d = dados()
        self.d["beneficios"] = [
            {"id": "bn-vip", "nome": "Sala VIP", "tipo": "contagem", "total": 4, "renova": "ano", "desde": "2026-01-01", "usos": []},
            {"id": "bn-cred", "nome": "Crédito de viagem", "tipo": "saldo", "total": 300, "renova": "ano", "desde": "2026-01-01", "usos": []},
            {"id": "bn-van", "nome": "Seguro de viagem", "tipo": "vantagem", "renova": "nunca", "desde": "2026-01-01"},
            {"id": "bn-mil", "nome": "Voa Mais", "tipo": "milhas", "pessoa": "Ana", "saldo": 10000, "saldo_em": "2026-11-01", "usos": []},
        ]

    def gravar(self, _nome, **a):
        t, mudou = chamar(_nome, a, self.d)
        self.assertTrue(mudou)
        return t

    def test_editar_fixo_de_agora_em_diante(self):
        self.d["lancamentos"].append({"id": "m-out", "tipo": "despesa", "descricao": "Internet", "valor": 120, "data": "2026-10-25", "pago": True,
                                      "recorrencia": "r-net", "competencia": "2026-10"})
        t = self.gravar("editar_fixo", id="v:r-net:2026-11", valor=149.9, dia=28, categoria="Casa")
        r = next(x for x in self.d["recorrencias"] if x.get("id") == "r-net")
        self.assertEqual((r["valor"], r["dia"], r["categoria"]), (149.9, 28, "c-casa"))
        self.assertIn("Os meses já lançados ficam como foram", t)
        self.assertEqual(next(x for x in self.d["lancamentos"] if x["id"] == "m-out")["valor"], 120)
        self.gravar("editar_fixo", id="Salário fixo", conta="Banco Azul")
        self.assertEqual(next(x for x in self.d["recorrencias"] if x.get("id") == "r-sal")["conta"], "cc", "pelo nome também")
        for args, erro in (({"id": "r-net"}, "Diga o que muda"), ({"id": "r-nada", "valor": 1}, "Fixo não encontrado"),
                           ({"id": "r-net", "dia": 40}, "dia: de 1 a 31"), ({"id": "r-net", "cartao": True}, "não tem cartão")):
            with self.assertRaisesRegex(F.ErroFerramenta, erro):
                chamar("editar_fixo", args, self.d)

    def test_encerrar_a_partir_de_um_mes_e_apagar_tudo(self):
        self.d["lancamentos"] += [
            {"id": "n-nov", "tipo": "despesa", "descricao": "Internet", "valor": 120, "data": "2026-11-25", "pago": True, "recorrencia": "r-net", "competencia": "2026-11"},
            {"id": "n-dez", "tipo": "despesa", "descricao": "Internet", "valor": 120, "data": "2026-12-25", "pago": False, "recorrencia": "r-net", "competencia": "2026-12"}]
        t = self.gravar("encerrar_fixo", id="r-net", a_partir="2026-12")
        self.assertIn("a partir de 12/2026", t)
        r = next(x for x in self.d["recorrencias"] if x.get("id") == "r-net")
        self.assertEqual(r["fim"], "2026-11")
        self.assertEqual({x["id"] for x in self.d["lancamentos"] if x.get("recorrencia") == "r-net"}, {"n-nov"}, "o de dezembro, não pago, sai")
        self.gravar("encerrar_fixo", id="r-sal")
        self.assertEqual(next(x for x in self.d["recorrencias"] if x.get("id") == "r-sal")["fim"], "2026-10", "sem a_partir: o mês de hoje")
        self.d["lancamentos"].append({"id": "d-plano", "tipo": "despesa", "descricao": "Plano", "valor": 1, "data": "2026-11-05", "vinculo": "r-net"})
        t = self.gravar("encerrar_fixo", id="r-net", apagar_tudo=True)
        self.assertIn("com os 1 meses", t)
        self.assertFalse(any(x.get("id") == "r-net" for x in self.d["recorrencias"]))
        self.assertNotIn("vinculo", next(x for x in self.d["lancamentos"] if x["id"] == "d-plano"))
        self.d["recorrencias"].append({"id": "r-novo", "tipo": "despesa", "descricao": "Academia", "valor": 90, "dia": 3, "inicio": "2026-12"})
        self.gravar("encerrar_fixo", id="r-novo", a_partir="2026-12")
        self.assertFalse(any(x.get("id") == "r-novo" for x in self.d["recorrencias"]), "parado antes de começar: sai")
        with self.assertRaisesRegex(F.ErroFerramenta, "a_partir inválido"):
            chamar("encerrar_fixo", {"id": "r-sal", "a_partir": "2026-13"}, self.d)

    def test_usar_beneficio_e_milhas(self):
        self.assertIn("Restam 3", self.gravar("usar_beneficio", beneficio="sala vip"))
        self.assertIn("Restam R$ 180,00", self.gravar("usar_beneficio", beneficio="bn-cred", quantidade=120, data="2026-11-10"))
        self.assertIn("Ficam 7.500", self.gravar("usar_beneficio", beneficio="Voa Mais", quantidade=2500))
        self.assertEqual([u["data"] for u in self.d["beneficios"][0]["usos"]], ["2026-11-15"], "sem data: hoje")
        self.assertIn("(antes, 7.500)", self.gravar("atualizar_milhas", beneficio="voa mais ana", saldo=12000))
        b = self.d["beneficios"][3]
        self.assertEqual((b["saldo_em"], calc.milhas_de(b, HOJE)["saldo"]), ("2026-11-15", 12000), "o resgate de hoje não desconta de novo do saldo dito")
        for nome, args, erro in (("usar_beneficio", {"beneficio": "Seguro de viagem"}, "vantagem"), ("usar_beneficio", {"beneficio": "bn-cred"}, "o valor usado"),
                                 ("usar_beneficio", {"beneficio": "Nada"}, "Benefício não encontrado"), ("atualizar_milhas", {"beneficio": "bn-vip", "saldo": 1}, "não é um programa"),
                                 ("atualizar_milhas", {"beneficio": "bn-mil", "saldo": -1}, "0 ou mais")):
            with self.assertRaisesRegex(F.ErroFerramenta, erro):
                chamar(nome, args, self.d)

    def test_nova_categoria_e_novo_banco(self):
        t = self.gravar("nova_categoria", nome="Viagens", tipo="despesa")
        c = self.d["categorias"][-1]
        self.assertEqual((c["nome"], c["tipo"], c["id"] in t, c["cor"] in F.CORES_CATEGORIA), ("Viagens", "despesa", True, True))
        self.assertEqual(F._categoria(self.d, "viagens", "despesa"), c["id"], "e já serve para lançar")
        with self.assertRaisesRegex(F.ErroFerramenta, "Já existe"):
            chamar("nova_categoria", {"nome": "viagens", "tipo": "despesa"}, self.d)
        self.gravar("novo_banco", banco="Banco Verde", pessoa="Beto", cartao_de_credito=True, fecha_dia=3, vence_dia=10, limite=5000, cartao_de_debito=False)
        b = self.d["bancos"][-1]
        self.assertEqual((b["nome"], b["contas"][0]["pessoa"], b["contas"][0]["fechamento"], b["contas"][0]["limite"], b["contas"][0]["debito"]),
                         ("Banco Verde", "Beto", 3, 5000, False))
        t = self.gravar("novo_banco", banco="banco azul", pessoa="Beto")
        self.assertIn("Conta acrescentada em Banco Azul", t)
        self.assertEqual([c["pessoa"] for c in self.d["bancos"][0]["contas"]], ["Ana", "Beto"])
        self.assertEqual(F._conta(self.d, "Banco Azul · Beto"), self.d["bancos"][0]["contas"][1]["id"], "e já serve para lançar")
        for args, erro in (({"banco": "Banco Azul", "pessoa": "Ana"}, "já tem a conta"), ({"banco": "Banco Lua", "cartao_de_credito": True}, "fecha_dia e vence_dia"),
                           ({"banco": " "}, "Falta o nome")):
            with self.assertRaisesRegex(F.ErroFerramenta, erro):
                chamar("novo_banco", args, self.d)


class TestNovas190(unittest.TestCase):
    """1.90.0 (as rondas do CorrerIA: "revisa se mais etapas ou ferramentas devem ser integradas"): os benefícios e as
    oportunidades, só leitura."""

    def test_beneficios_com_o_que_sobra_as_milhas_e_o_proximo_nivel(self):
        d = dados()
        self.assertEqual(chamar("beneficios", {}, d), ("Nenhum benefício em Mais › Benefícios.", False))
        d["beneficios"] = [
            {"id": "bn-vip", "nome": "Sala VIP", "tipo": "contagem", "total": 4, "renova": "ano", "desde": "2026-01-01", "usos": [{"data": "2026-03-01", "qtd": 1}]},
            {"id": "bn-mil", "nome": "Voa Mais", "tipo": "milhas", "pessoa": "Ana", "saldo": 12000, "saldo_em": "2026-11-01",
             "vencem": [{"qtd": 2000, "data": "2027-01-10"}], "proximo": {"nivel": "Ouro", "pede": 20000, "tem": 15000}},
        ]
        t, mudou = chamar("beneficios", {}, d)
        self.assertFalse(mudou)
        self.assertIn("Sala VIP |", t)
        self.assertIn("sobram 3 de 4", t)
        self.assertIn("Voa Mais | Ana | 12.000", t)
        self.assertIn("2.000 em 2027-01-10", t)
        self.assertIn("nível Ouro | Voa Mais · Ana | 20.000 qualificáveis | faltam 5.000", t)
        self.assertIn(t, F.chat.resumo(d, HOJE), "o mesmo texto do resumo")

    def test_oportunidades_so_pelo_servidor_e_o_texto(self):
        with self.assertRaises(LookupError):
            chamar("oportunidades", {}, dados())
        x = {"id": "td:a", "nome": "Tesouro IPCA+ 2035", "fonte": "Tesouro Direto", "indexador": "ipca_mais", "taxa": 7.5, "vencimento": "2035-05-15",
             "minimo": 35.2, "eq": {"grupo": "ipca", "valor": 7.5}, "passa": "alvo", "meus": None}
        outras = [dict(x, id=f"td:{k}", nome=f"Tesouro Selic 20{k}", indexador="selic_mais", taxa=0.1, eq={"grupo": "pos", "valor": 100}, passa="") for k in range(29, 34)]
        t = F.texto_oportunidades([x] + outras, [{"nome": "Cine Mais", "preco": 9.9, "meses": 3, "normal": 29.9, "ate": "2026-12-10"}])
        self.assertIn("Investimentos que passam do que a casa quer:\n- Tesouro IPCA+ 2035: IPCA + 7,50% · Tesouro Direto · vence em 15/05/2035 · mínimo R$ 35,20", t)
        self.assertEqual(t.count("Tesouro Selic"), 3, "das que não passam, as três melhores de cada tipo")
        self.assertIn("- Cine Mais: R$ 9,90 por mês por 3 meses (depois R$ 29,90), até 10/12/2026", t)
        t = F.texto_oportunidades([x] + outras, [], so_passam=True)
        self.assertEqual((t.count("Tesouro Selic"), "Nenhuma assinatura em promoção." in t), (0, True))
        t = F.texto_oportunidades(outras, [], ia=False, avisos="O Tesouro Direto ainda não foi lido.")
        self.assertIn("Nenhum investimento passa do que a casa quer agora.", t)
        self.assertIn("pedem o Usar IA ligado", t)
        self.assertTrue(t.endswith("O Tesouro Direto ainda não foi lido."))
        self.assertEqual([f["nome"] for f in F.lista() if not f["grava"]][-3:], ["beneficios", "oportunidades", "dicas"])


class TestAlterarLancamentos(unittest.TestCase):
    """1.94.0 (o dono, às ferramentas que faltavam para o CorrerIA: "pode colocar todas"): o Alterar do Caixa › Selecionar."""

    def setUp(self):
        self.d = dados()

    def gravar(self, **a):
        t, mudou = chamar("alterar_lancamentos", a, self.d)
        self.assertTrue(mudou)
        return t

    def lanc(self, lid):
        return next(x for x in self.d["lancamentos"] if x["id"] == lid)

    def test_categoria_e_situacao_de_varios_e_o_fixo_do_mes(self):
        t = self.gravar(ids=["l-luz", "l-agua", "v:r-net:2026-11"], categoria="Casa", pago=True)
        self.assertEqual(t, "3 lançamentos alterados (categoria Casa e pago).")
        self.assertEqual((self.lanc("l-luz")["pago"], self.lanc("l-agua")["categoria"]), (True, "c-casa"))
        fixo = next(x for x in self.d["lancamentos"] if x.get("recorrencia") == "r-net" and x.get("competencia") == "2026-11")
        self.assertEqual((fixo["pago"], fixo["categoria"]), (True, "c-casa"), "o fixo do mês vira lançamento, só ele")
        self.assertIn("já estavam assim", self.gravar(ids=["l-luz", "l-velha"], pago=True))
        self.assertEqual(self.gravar(ids=["l-luz"], pago=True), "Nada mudou: os 1 já estavam assim.")
        self.assertIn("(a receber)", self.gravar(ids=["l-sal"], pago=False))

    def test_a_receita_fixa_leva_as_vinculadas(self):
        self.d["recorrencias"].append({"id": "r-plano", "tipo": "despesa", "descricao": "Plano", "valor": 80, "dia": 5, "inicio": "2026-01", "vinculo": "r-sal"})
        self.d["lancamentos"].append({"id": "l-avulsa", "tipo": "despesa", "descricao": "Avulsa", "valor": 10, "data": "2026-11-02", "vinculo": "r-sal"})
        self.gravar(ids=["v:r-sal:2026-11"], pago=True)
        plano = next(x for x in self.d["lancamentos"] if x.get("recorrencia") == "r-plano")
        self.assertEqual((plano["pago"], plano["cartao"], plano["competencia"]), (True, False, "2026-11"))
        self.assertTrue(self.lanc("l-avulsa")["pago"])
        self.gravar(ids=["v:r-sal:2026-11"], pago=False)
        self.assertFalse(plano["pago"])
        self.assertFalse(self.lanc("l-avulsa")["pago"])

    def test_o_que_vale(self):
        for args, erro in (({"ids": ["l-luz"]}, "Diga o que muda"), ({"ids": []}, "ids"), ({"ids": ["l-luz"], "pago": "sim"}, "true ou false"),
                           ({"ids": ["l-luz", "l-sal"], "pago": True}, "um tipo só"), ({"ids": ["k2"], "pago": True}, "Compras no cartão"),
                           ({"ids": ["l-aj"], "pago": True}, "não mudam assim"), ({"ids": ["l-vin"], "pago": True}, "não mudam assim"),
                           ({"ids": ["l-luz"], "categoria": "Viagem"}, "Categoria não encontrada"), ({"ids": ["nada"], "pago": True}, "Não encontrei")):
            with self.subTest(args=args), self.assertRaisesRegex(F.ErroFerramenta, erro):
                chamar("alterar_lancamentos", args, self.d)
        self.assertIn("1 lançamento alterado", self.gravar(ids=["k2"], categoria="Casa"), "no cartão, só a categoria")


class TestDicas(unittest.TestCase):
    """1.95.0 (o dono, às ferramentas que faltavam para o CorrerIA: "pode seguir neles"): o texto das dicas de economia."""

    def test_as_que_valem_e_as_outras(self):
        subs = [{"chave": "r:a", "nome": "Som Livre Exemplo", "valor": 21.9}, {"chave": "r:b", "nome": "Vídeo Exemplo", "valor": 39.9}]
        vale = [dict(subs[0], preco_anual=219.0, real=38.5, conferido="2026-11-10T08:00:00")]
        t = F.texto_dicas(vale, subs)
        self.assertEqual(t.split("\n"), ["1 dica de economia (pagar o plano anual; o que sobra por ano, já com o que o dinheiro renderia):",
                                         "- Som Livre Exemplo: paga R$ 21,90 por mês; o anual custa R$ 219,00 e sobram uns R$ 38,50 por ano (preço conferido em 10/11/2026)",
                                         "As outras assinaturas que o app acompanha: Vídeo Exemplo (R$ 39,90)."])
        self.assertTrue(F.texto_dicas([], subs).startswith("Nenhuma dica de economia agora."))
        self.assertIn("não achou assinaturas", F.texto_dicas([], []))
        self.assertIn("estão desligadas", F.texto_dicas([], subs, True))
        with self.assertRaises(LookupError):
            chamar("dicas", {}, dados())


class TestCompararMeses(unittest.TestCase):
    """1.96.0 (o dono, às ferramentas que faltavam para o CorrerIA: "pode seguir em todas"): os gastos por categoria de um mês contra outro."""

    def setUp(self):
        self.d = dados()
        self.d["lancamentos"] += [
            {"id": "o1", "tipo": "despesa", "descricao": "Luz de outubro", "valor": 100, "data": "2026-10-10", "categoria": "c-casa"},
            {"id": "o2", "tipo": "despesa", "descricao": "Fim do mês", "valor": 70, "data": "2026-10-28", "categoria": "c-casa"},
            {"id": "o3", "tipo": "despesa", "descricao": "Feira", "valor": 300, "data": "2026-10-05"}]

    def test_o_mes_atual_vai_ate_hoje_nos_dois(self):
        t, mudou = chamar("comparar_meses", {}, self.d)
        self.assertFalse(mudou)
        self.assertEqual(t.split("\n"), ["Gastos de novembro de 2026 (até o dia 15): R$ 191,00; de outubro de 2026 (até o dia 15): R$ 451,00, −58%.",
                                         "Nenhuma categoria subiu.", "Caíram (2):",
                                         "- Sem categoria: R$ 191,00 (antes R$ 351,00; −R$ 160,00)", "- Casa: R$ 0,00 (antes R$ 100,00; −R$ 100,00)"])

    def test_meses_inteiros_o_que_mais_subiu_primeiro(self):
        t = chamar("comparar_meses", {"mes": "2026-10", "com": "2026-09"}, self.d)[0].split("\n")
        self.assertEqual(t[:2], ["Gastos de outubro de 2026: R$ 641,00; de setembro de 2026: R$ 121,00, +430%.", "Subiram (2):"])
        self.assertEqual(t[3], "- Casa: R$ 290,00 (antes R$ 120,00; +R$ 170,00, +142%)")
        self.assertEqual(len(t), 4)
        vazio = {"lancamentos": [], "recorrencias": [], "categorias": []}
        self.assertTrue(chamar("comparar_meses", {"mes": "2026-10"}, vazio)[0].endswith("Nenhum gasto nos dois."))

    def test_o_que_nao_vale(self):
        for args, erro in (({"mes": "outubro"}, "mes: um mês"), ({"com": "2026-13"}, "com: um mês"), ({"mes": "2026-10", "com": "2026-10"}, "o mesmo"),
                           ({"mes": "2026-12"}, "ainda não chegou")):
            with self.assertRaisesRegex(F.ErroFerramenta, erro):
                chamar("comparar_meses", args, self.d)


class TestForaDoPadrao(unittest.TestCase):
    """1.97.0 (o dono, ao «Algo estranho»: "pode fazer todos"): o que foge do costume nos gastos do mês, sem a IA."""

    def base(self):
        ls = []
        for i, (m, luz) in enumerate((("08", 100), ("09", 110), ("10", 90))):
            ls += [{"id": f"l{i}", "tipo": "despesa", "descricao": f"Luz de {['agosto', 'setembro', 'outubro'][i]}", "valor": luz, "data": f"2026-{m}-10"},
                   {"id": f"m{i}", "tipo": "despesa", "descricao": "Mercado", "valor": 80, "data": f"2026-{m}-05"},
                   {"id": f"n{i}", "tipo": "despesa", "descricao": "Mercado", "valor": 60, "data": f"2026-{m}-20"}]
        return {"lancamentos": ls, "recorrencias": [], "categorias": [], "bancos": [], "investimentos": []}

    def test_nada_fora_do_padrao(self):
        d = self.base()
        d["lancamentos"].append({"id": "a", "tipo": "despesa", "descricao": "Luz de novembro", "valor": 105, "data": "2026-11-10"})
        t, mudou = chamar("fora_do_padrao", {}, d)
        self.assertFalse(mudou)
        self.assertEqual(t, "Nada fora do padrão nos gastos de novembro de 2026 (até o dia 15).")

    def test_mais_caro_repetido_e_compra_grande(self):
        d = self.base()
        d["lancamentos"] += [
            {"id": "a", "tipo": "despesa", "descricao": "Luz de novembro", "valor": 150, "data": "2026-11-10"},
            {"id": "b", "tipo": "despesa", "descricao": "Padaria Pão Bom", "valor": 18.5, "data": "2026-11-12"},
            {"id": "c", "tipo": "despesa", "descricao": "Padaria Pão Bom", "valor": 18.5, "data": "2026-11-12"},
            {"id": "d", "tipo": "despesa", "descricao": "Geladeira nova 1/10", "valor": 900, "data": "2026-11-03"},
            {"id": "e", "tipo": "despesa", "descricao": "Bala", "valor": 2, "data": "2026-11-04"},
            {"id": "f", "tipo": "despesa", "descricao": "Bala", "valor": 2, "data": "2026-11-04"},
            {"id": "g", "tipo": "despesa", "descricao": "Mercado", "valor": 500, "data": "2026-11-20"},
            {"id": "h", "tipo": "receita", "descricao": "Salário extra", "valor": 5000, "data": "2026-11-05"},
            {"id": "i", "tipo": "despesa", "descricao": "Acerto", "valor": 5000, "data": "2026-11-05", "ajuste": True}]
        t = chamar("fora_do_padrao", {}, d)[0].split("\n")
        self.assertEqual(t, ["Fora do padrão nos gastos de novembro de 2026 (até o dia 15): 3.",
                             "Mais caro que o costume (1):",
                             "- Luz de novembro: R$ 150,00 (a média de 3 meses é R$ 100,00; +R$ 50,00, +50%)",
                             "Parece repetido (1):",
                             "- Padaria Pão Bom: 2 vezes de R$ 18,50 em 12/11",
                             "Compra grande, fora do costume (1):",
                             "- Geladeira nova 1/10: R$ 900,00 em 03/11 (uma compra de costume fica perto de R$ 80,00)"])

    def test_pouco_para_comparar(self):
        d = {"lancamentos": [{"id": "a", "tipo": "despesa", "descricao": "Sofá", "valor": 3000, "data": "2026-11-03"},
                             {"id": "b", "tipo": "despesa", "descricao": "Luz", "valor": 300, "data": "2026-11-03"},
                             {"id": "c", "tipo": "despesa", "descricao": "Luz", "valor": 100, "data": "2026-10-03"},
                             {"id": "x", "tipo": "despesa", "descricao": "2026", "valor": 9, "data": "2026-11-03"}], "recorrencias": [], "categorias": []}
        self.assertTrue(chamar("fora_do_padrao", {}, d)[0].startswith("Nada fora do padrão"), "um mês só de histórico e menos de 5 compras: não acusa")
        self.assertEqual(F._chave_gasto("Luz de Outubro 2026 (3/10)"), "luz")


class TestNovas196(unittest.TestCase):
    """1.96.0: a projeção dos investimentos e mudar categoria e banco (o que a tela faz em Mais › Invest, Caixa e Bancos)."""

    def setUp(self):
        self.d = dados()

    def test_projecao(self):
        t, mudou = chamar("projecao", {}, self.d)
        self.assertFalse(mudou)
        self.assertEqual(t.split("\n"), ["Hoje: R$ 10.000,00. Em 12 meses (1 ano), sem aportes: R$ 11.065,00 (+R$ 1.065,00), antes do IR, com a taxa de hoje de cada um.",
                                         "- CDB Azul: R$ 10.000,00 → R$ 11.065,00 (100% do CDI)"])
        t = chamar("projecao", {"meses": 24, "aporte_mensal": 500}, self.d)[0].split("\n")
        self.assertTrue(t[0].startswith("Hoje: R$ 10.000,00. Em 24 meses (2 anos), sem aportes: R$ 12.243,42"))
        self.assertEqual(t[1], "Com R$ 500,00 por mês: R$ 25.488,09 (R$ 12.000,00 de aportes e R$ 1.244,67 do que eles rendem, pela taxa média de 10,7% ao ano).")
        self.assertIn("Em 1 mês, sem", chamar("projecao", {"meses": 1}, self.d)[0])
        self.assertEqual(chamar("projecao", {}, {"investimentos": []})[0], "Nenhum investimento seu cadastrado para projetar.")
        self.assertIn("Com R$ 100,00 por mês", chamar("projecao", {"aporte_mensal": 100}, {"investimentos": []})[0])
        with self.assertRaisesRegex(F.ErroFerramenta, "de 1 a 480"):
            chamar("projecao", {"meses": 999}, self.d)

    def test_editar_categoria(self):
        self.assertEqual(chamar("editar_categoria", {"categoria": "Casa", "nome": "Lar", "cor": "verde"}, self.d), ("Categoria mudada (Lar): Casa → Lar, cor Verde.", True))
        c = next(x for x in self.d["categorias"] if x["id"] == "c-casa")
        self.assertEqual((c["nome"], c["cor"]), ("Lar", "#8BD45F"))
        for args, erro in (({"categoria": "Nada"}, "não encontrada"), ({"categoria": "c-casa"}, "Diga o que muda"), ({"categoria": "c-casa", "nome": " "}, "vazio"),
                           ({"categoria": "c-casa", "cor": "bege"}, "cor: Vermelho"), ({"categoria": "c-casa", "nome": "Mercado"}, "Já existe")):
            with self.assertRaisesRegex(F.ErroFerramenta, erro):
                chamar("editar_categoria", args, self.d)
        self.d["categorias"].append({"id": "c-lar2", "nome": "Lar", "tipo": "receita"})
        with self.assertRaisesRegex(F.ErroFerramenta, "diga o tipo"):
            chamar("editar_categoria", {"categoria": "lar", "cor": "Azul"}, self.d)
        self.assertEqual(chamar("editar_categoria", {"categoria": "lar", "tipo": "receita", "apagar": True}, self.d)[0], "Categoria apagada: Lar.")
        self.assertEqual(chamar("editar_categoria", {"categoria": "c-casa", "apagar": True}, self.d)[0], "Categoria apagada: Lar. 2 lançamentos ficaram sem categoria.")
        self.assertEqual(next(x for x in self.d["lancamentos"] if x["id"] == "l-luz")["categoria"], "")
        self.assertTrue(next(f for f in F.lista() if f["nome"] == "editar_categoria")["apaga"])

    def test_editar_banco(self):
        t = chamar("editar_banco", {"banco": "banco azul", "nome": "Banco Anil", "cor": "Rosa", "obs": "o de sempre", "fecha_dia": 8, "vence_dia": 15, "limite": 3000}, self.d)[0]
        self.assertEqual(t, "Banco Anil: nome Banco Anil, cor Rosa, observação, fecha dia 8, vence dia 15, limite R$ 3.000,00.")
        b = self.d["bancos"][0]
        self.assertEqual((b["cor"], b["contas"][0]["fechamento"], b["contas"][0]["vencimento"], b["contas"][0]["limite"]), ("#FF77A9", 8, 15, 3000.0))
        self.assertEqual(chamar("editar_banco", {"banco": "b1", "conta": "Ana", "pessoa": "Beto", "cartao_de_credito": False}, self.d)[0], "Banco Anil: a conta é de Beto, sem cartão de crédito.")
        b["contas"].append({"id": "k2", "pessoa": "Ana", "cartao": False})
        self.assertEqual(chamar("editar_banco", {"banco": "b1", "conta": "k2", "pessoa": ""}, self.d)[0], "Banco Anil: a conta fica sem pessoa.")
        self.d["bancos"].append({"id": "b2", "nome": "Banco Verde", "contas": []})
        for args, erro in (({"banco": "Nada"}, "não encontrado"), ({"banco": "b1"}, "Diga o que muda"), ({"banco": "b1", "nome": ""}, "vazio"),
                           ({"banco": "b1", "nome": "Banco Verde"}, "Já existe"), ({"banco": "b1", "limite": 10}, "Diga a conta de Banco Anil"),
                           ({"banco": "b1", "conta": "k2"}, "o que muda na conta"), ({"banco": "b1", "conta": "k2", "pessoa": "Beto"}, "já tem a conta de Beto"),
                           ({"banco": "b1", "conta": "k2", "limite": 10}, "não tem cartão")):
            with self.assertRaisesRegex(F.ErroFerramenta, erro):
                chamar("editar_banco", args, self.d)
