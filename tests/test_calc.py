"""calc.py: números do jeito brasileiro, taxas, valor de hoje, totais, o caixa e a Cor do dia."""
import unittest
from datetime import date, timedelta

from tests.base import INDICES
import calc


class TestDatas(unittest.TestCase):
    def test_parse_data(self):
        self.assertEqual(calc.parse_data("2026-11-02"), date(2026, 11, 2))
        self.assertEqual(calc.parse_data("2026-11-02T10:00:00"), date(2026, 11, 2))
        for ruim in (None, "", "02/11/2026", "2026-13-01"):
            self.assertIsNone(calc.parse_data(ruim))

    def test_dias_uteis(self):
        seg = date(2026, 11, 2)
        self.assertEqual(calc.dias_uteis(seg, date(2026, 11, 6)), 4, "ter a sex")
        self.assertEqual(calc.dias_uteis(seg, date(2026, 11, 9)), 5, "uma semana")
        self.assertEqual(calc.dias_uteis(date(2026, 11, 6), date(2026, 11, 9)), 1, "sex para seg: só a segunda")
        self.assertEqual(calc.dias_uteis(date(2026, 11, 7), date(2026, 11, 8)), 0, "sábado para domingo")
        self.assertEqual(calc.dias_uteis(seg, seg), 0)
        self.assertEqual(calc.dias_uteis(date(2026, 11, 9), seg), 0, "para trás")
        self.assertEqual(calc.dias_uteis(None, seg), 0)
        self.assertEqual(calc.dias_uteis(date(2025, 1, 6), date(2025, 12, 24)), 252)

    def test_data_mes(self):
        self.assertEqual(calc._data_mes(2026, 13, 5), date(2027, 1, 5), "mês 13 é janeiro do ano seguinte")
        self.assertEqual(calc._data_mes(2026, 0, 5), date(2025, 12, 5), "mês 0 é dezembro do ano anterior")
        self.assertEqual(calc._data_mes(2026, 2, 31), date(2026, 2, 28), "dia limitado ao fim do mês")
        self.assertEqual(calc._data_mes(2028, 2, 31), date(2028, 2, 29), "ano bissexto")
        self.assertEqual(calc._data_mes(2026, 12, 31), date(2026, 12, 31))
        self.assertEqual(calc._data_mes(2026, 5, None), date(2026, 5, 1))
        self.assertEqual(calc._data_mes(2026, 5, 0), date(2026, 5, 1))


class TestNumeros(unittest.TestCase):
    def test_num(self):
        self.assertEqual(calc.num("12.5"), 12.5)
        self.assertEqual(calc.num(None), 0.0)
        self.assertEqual(calc.num("abc", 7), 7)

    def test_num_br(self):
        casos = {
            "15.000": 15000, "15.000,50": 15000.5, "R$ 1.234,56": 1234.56, "13,65": 13.65, "1,234.56": 1234.56,
            "6.50": 6.5, "1.234.567": 1234567, "1,234": 1234, "1,2,3": 123, "1234.567": 1234.567, "-1.234,56": -1234.56,
            "R$ -50": -50, "100.000,00": 100000, "0,5": 0.5, "12.5": 12.5, " 30.350 ": 30350, "2 mil": 2,
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertAlmostEqual(calc.num_br(texto), esperado)
        self.assertEqual(calc.num_br(42), 42.0)
        self.assertEqual(calc.num_br(3.5), 3.5)
        self.assertEqual(calc.num_br(True, 9), 9, "booleano não é número")
        self.assertEqual(calc.num_br("abc", 9), 9)
        self.assertEqual(calc.num_br(None), 0.0)
        self.assertEqual(calc.num_br("R$ ,", 9), 9, "sem dígitos")

    def test_formatos(self):
        self.assertEqual(calc.fmt_num(1234.5), "1.234,50")
        self.assertEqual(calc.fmt_num(1234567.891, 0), "1.234.568")
        self.assertEqual(calc.fmt_num(-12.3), "-12,30")
        self.assertEqual(calc.fmt_pct(110.0), "110")
        self.assertEqual(calc.fmt_pct(13.65), "13,65")
        self.assertEqual(calc.fmt_pct(13.5), "13,5")
        self.assertEqual(calc.fmt_brl(0.5), "R$ 0,50")
        self.assertEqual(calc.fmt_brl(1500, 0), "R$ 1.500")

    def test_r2_arredonda_como_o_app(self):
        self.assertEqual(calc._r2(0.125), 0.13)
        self.assertEqual(calc._r2(10), 10)
        self.assertEqual(calc._r2(1.234), 1.23)
        self.assertEqual(calc._r2(-1.236), -1.24)


class TestTaxas(unittest.TestCase):
    def taxa(self, indexador, taxa=0, ind=INDICES):
        return calc.taxa_anual({"indexador": indexador, "taxa": taxa}, ind)

    def test_cada_indexador(self):
        self.assertAlmostEqual(self.taxa("cdi_pct", 110), 0.1365 * 1.10)
        self.assertAlmostEqual(self.taxa("cdi_mais", 2), 1.1365 * 1.02 - 1)
        self.assertAlmostEqual(self.taxa("pre", 12), 0.12)
        self.assertAlmostEqual(self.taxa("ipca_mais", 6), 1.045 * 1.06 - 1)
        self.assertAlmostEqual(self.taxa("selic_mais", 0), 0.1375)
        self.assertAlmostEqual(self.taxa("estimado", 8), 0.08)
        self.assertAlmostEqual(self.taxa("deprecia", 15), -0.15, msg="bens perdem a taxa da categoria")
        self.assertAlmostEqual(self.taxa("deprecia", -5), 0.05, msg="taxa negativa: valoriza")
        self.assertEqual(self.taxa("parado", 10), 0.0)
        self.assertEqual(self.taxa("inventado", 10), 0.0)

    def test_poupanca(self):
        self.assertAlmostEqual(self.taxa("poupanca"), (1.005 * 1.001) ** 12 - 1, msg="Selic acima de 8,5%: 0,5% ao mês + TR")
        baixa = dict(INDICES, selic=7.0, tr=0)
        self.assertAlmostEqual(self.taxa("poupanca", ind=baixa), 1.049 - 1, places=10, msg="Selic baixa: 70% da Selic")

    def test_indices_ausentes(self):
        self.assertEqual(self.taxa("cdi_pct", 100, {}), 0.0)

    def test_rotulos(self):
        r = lambda k, t=0: calc.rotulo_taxa({"indexador": k, "taxa": t})
        self.assertEqual(r("cdi_pct", 110), "110% do CDI")
        self.assertEqual(r("cdi_mais", 1.5), "CDI + 1,5% a.a.")
        self.assertEqual(r("pre", 12.25), "12,25% a.a. pré")
        self.assertEqual(r("ipca_mais", 6), "IPCA + 6% a.a.")
        self.assertEqual(r("selic_mais"), "Selic")
        self.assertEqual(r("selic_mais", 0.1), "Selic + 0,1% a.a.")
        self.assertEqual(r("poupanca"), "Poupança")
        self.assertEqual(r("estimado", 9), "≈ 9% a.a. estimado")
        self.assertEqual(r("parado"), "Sem rendimento")
        # bens (era bug até a 1.29.0: o relatório dizia "Sem rendimento" num bem, que perde ou ganha a taxa da categoria)
        self.assertEqual(r("deprecia", 15), "perde 15% a.a.")
        self.assertEqual(r("deprecia", -2.5), "valoriza 2,5% a.a.")
        self.assertEqual(r("deprecia", 0), "mantém o valor")


class TestValorHoje(unittest.TestCase):
    D0, HOJE = "2025-01-06", date(2025, 12, 24)  # 252 dias úteis

    def test_um_ano_de_dias_uteis_rende_a_taxa(self):
        inv = {"valor": 1000, "indexador": "pre", "taxa": 10, "data_valor": self.D0}
        self.assertAlmostEqual(calc.valor_hoje(inv, INDICES, hoje=self.HOJE), 1100)

    def test_sem_correcao(self):
        inv = {"valor": 1000, "indexador": "pre", "taxa": 10, "data_valor": self.D0}
        self.assertEqual(calc.valor_hoje(inv, INDICES, corrigir=False, hoje=self.HOJE), 1000)
        for k in ("estimado", "parado"):
            self.assertEqual(calc.valor_hoje(dict(inv, indexador=k), INDICES, hoje=self.HOJE), 1000, k)

    def test_sem_data_vale_o_informado(self):
        self.assertEqual(calc.valor_hoje({"valor": "500", "indexador": "pre", "taxa": 10}, INDICES), 500)

    def test_bem_perde_valor(self):
        inv = {"valor": 1000, "indexador": "deprecia", "taxa": 20, "data_valor": self.D0}
        self.assertAlmostEqual(calc.valor_hoje(inv, INDICES, hoje=self.HOJE), 800)

    def test_bem_em_partes_cada_uma_com_sua_taxa(self):
        inv = {"valor": 1500, "indexador": "deprecia", "taxa": 10, "data_valor": self.D0,
               "partes": [{"valor": 1000, "taxa": 20}, {"valor": 500, "taxa": 0}, "lixo"]}
        self.assertAlmostEqual(calc.valor_hoje(inv, INDICES, hoje=self.HOJE), 1300)

    def test_partes_so_valem_para_bens(self):
        inv = {"valor": 1000, "indexador": "pre", "taxa": 10, "data_valor": self.D0, "partes": [{"valor": 1, "taxa": 0}]}
        self.assertAlmostEqual(calc.valor_hoje(inv, INDICES, hoje=self.HOJE), 1100)

    def test_rende_mes(self):
        self.assertAlmostEqual(calc.rende_mes(1200, 0.12), 1200 * (1.12 ** (1 / 12) - 1))


class TestValorEm(unittest.TestCase):
    """O valor daqui a uns anos (Relatório de patrimônio: em 1 e em 5 anos), como a projeção do app."""
    D0, HOJE = "2025-01-06", date(2025, 12, 24)  # 252 dias úteis

    def test_cresce_a_taxa_a_partir_de_hoje(self):
        inv = {"valor": 1000, "indexador": "pre", "taxa": 10, "data_valor": self.D0}
        self.assertAlmostEqual(calc.valor_em(inv, INDICES, 0, hoje=self.HOJE), 1100, msg="0 anos: o valor de hoje")
        self.assertAlmostEqual(calc.valor_em(inv, INDICES, 1, hoje=self.HOJE), 1210)
        self.assertAlmostEqual(calc.valor_em(inv, INDICES, 5, hoje=self.HOJE), 1100 * 1.1 ** 5)

    def test_sem_corrigir_parte_do_ultimo_valor(self):
        inv = {"valor": 1000, "indexador": "pre", "taxa": 10, "data_valor": self.D0}
        self.assertAlmostEqual(calc.valor_em(inv, INDICES, 1, corrigir=False, hoje=self.HOJE), 1100)

    def test_parado_fica_igual_e_estimado_cresce(self):
        self.assertEqual(calc.valor_em({"valor": 300, "indexador": "parado"}, INDICES, 5), 300)
        self.assertAlmostEqual(calc.valor_em({"valor": 300, "indexador": "estimado", "taxa": 9}, INDICES, 1), 327)

    def test_bem_perde_e_bem_que_valoriza_ganha(self):
        self.assertAlmostEqual(calc.valor_em({"valor": 1000, "indexador": "deprecia", "taxa": 20}, INDICES, 1), 800)
        self.assertAlmostEqual(calc.valor_em({"valor": 1000, "indexador": "deprecia", "taxa": -5}, INDICES, 2), 1102.5)

    def test_bem_em_partes_muda_parte_por_parte(self):
        inv = {"valor": 1500, "indexador": "deprecia", "taxa": 10, "data_valor": self.D0,
               "partes": [{"valor": 1000, "taxa": 20}, {"valor": 500, "taxa": -10}, "lixo"]}
        self.assertAlmostEqual(calc.valor_em(inv, INDICES, 1, hoje=self.HOJE), 1000 * 0.8 ** 2 + 500 * 1.1 ** 2)
        self.assertAlmostEqual(calc.valor_em(inv, INDICES, 1, corrigir=False, hoje=self.HOJE), 1000 * 0.8 + 500 * 1.1)
        self.assertEqual(calc.rende_mes(1000, -0.2), 0.0, "bem que perde valor não rende")


class TestTotais(unittest.TestCase):
    def dados(self, corrigir=True):
        return {
            "indices": INDICES,
            "ajustes": {"corrigir": corrigir},
            "investimentos": [
                {"valor": 1000, "indexador": "parado"},
                {"valor": 2000, "indexador": "pre", "taxa": 12, "titular": "terceiros", "terceiro": "Mãe"},
                {"valor": 500, "indexador": "parado", "titular": "terceiros", "terceiro": "  "},
                {"valor": 300, "indexador": "parado", "titular": "terceiros", "terceiro": "Mãe"},
            ],
        }

    def test_meu_terceiros_e_pessoas(self):
        t = calc.totais(self.dados(), hoje=date(2026, 11, 2))
        self.assertEqual((t["total"], t["meu"], t["terceiros"], t["quantidade"]), (3800, 1000, 2800, 4))
        self.assertEqual(t["pessoas"], {"Mãe": 2300, "Terceiros": 500})
        self.assertAlmostEqual(t["rende_mes"], round(2000 * (1.12 ** (1 / 12) - 1), 2))

    def test_vazio(self):
        self.assertEqual(calc.totais({}), {"total": 0, "meu": 0, "terceiros": 0, "rende_mes": 0, "pessoas": {}, "quantidade": 0})

    def test_dono(self):
        self.assertEqual(calc.dono({"titular": "terceiros", "terceiro": " Ana "}), "Ana")
        self.assertEqual(calc.dono({"titular": "terceiros"}), "Terceiros")
        self.assertEqual(calc.dono({}), "Meu")

    def test_listas_fixas(self):
        self.assertIn("deprecia", calc.INDEXADORES)
        self.assertIn("bens", calc.TIPOS)
        cats = calc.categorias_padrao()
        self.assertEqual(len({c["id"] for c in cats}), len(cats), "ids únicos")
        self.assertEqual({c["tipo"] for c in cats}, {"despesa", "receita"})


class TestContas(unittest.TestCase):
    DADOS = {"bancos": [
        {"id": "b1", "nome": "Banco Azul", "contas": [{"id": "c1", "pessoa": "Ana", "cartao": True, "fechamento": 5, "vencimento": 12}, "lixo", {"sem": "id"}]},
        {"id": "b2", "nome": "Banco Verde", "contas": [{"id": "c2", "cartao": True, "fechamento": 25, "vencimento": 5}, {"id": "c3"}]},
        {"id": "b3", "nome": "Sem contas"},
    ]}

    def test_mapa_e_nome(self):
        m = calc.mapa_contas(self.DADOS)
        self.assertEqual(sorted(m), ["c1", "c2", "c3"])
        self.assertEqual((m["c1"]["banco"], m["c1"]["banco_nome"]), ("b1", "Banco Azul"))
        self.assertEqual(calc.nome_conta(m["c1"]), "Banco Azul · Ana")
        self.assertEqual(calc.nome_conta(m["c3"]), "Banco Verde")
        self.assertEqual(calc.nome_conta(None), "")

    def test_data_do_caixa_no_cartao(self):
        m = calc.mapa_contas(self.DADOS)
        dc = lambda d, conta="c1", cartao=True: calc.data_caixa({"data": d, "conta": conta, "cartao": cartao}, m)
        self.assertEqual(dc("2026-11-03"), date(2026, 11, 12), "antes do fechamento: vence no mês")
        self.assertEqual(dc("2026-11-05"), date(2026, 12, 12), "no dia do fechamento: próxima fatura")
        self.assertEqual(dc("2026-12-20"), date(2027, 1, 12), "virada do ano")
        self.assertEqual(dc("2026-11-10", "c2"), date(2026, 12, 5), "vencimento antes do fechamento: mês seguinte")
        self.assertEqual(dc("2026-11-26", "c2"), date(2027, 1, 5))
        self.assertEqual(dc("2026-11-03", cartao=False), date(2026, 11, 3), "no débito: o próprio dia")
        self.assertEqual(dc("2026-11-03", "c3"), date(2026, 11, 3), "conta sem cartão")
        self.assertIsNone(dc(None))


class TestDespesaLigada(unittest.TestCase):
    """Plano de saúde descontado do salário (vínculo): sai do caixa no dia em que o salário entra, como na tela."""
    DADOS = {"recorrencias": [{"id": "r-sal", "tipo": "receita", "valor": 5000, "dia": 5, "inicio": "2026-01", "fim": "2026-12"}],
             "lancamentos": [{"id": "s-nov", "recorrencia": "r-sal", "competencia": "2026-11", "data": "2026-11-01"},
                             {"id": "s-out", "recorrencia": "r-sal", "competencia": "2026-10", "data": "2026-10-07", "pulado": True}]}

    def dc(self, **l):
        return calc.data_caixa(dict({"tipo": "despesa", "vinculo": "r-sal"}, **l), {}, self.DADOS)

    def test_dia_do_recebimento(self):
        self.assertEqual(self.dc(competencia="2026-11", data="2026-11-20"), date(2026, 11, 1), "o salário lançado (adiantado)")
        self.assertEqual(self.dc(competencia="2026-09", data="2026-09-20"), date(2026, 9, 5), "não lançado: o dia do fixo")
        self.assertEqual(self.dc(data="2026-12-20"), date(2026, 12, 5), "sem competência: o mês da data")
        self.assertEqual(self.dc(competencia="2026-10", data="2026-10-20"), date(2026, 10, 5), "salário pulado: o dia do fixo")

    def test_quando_nao_vale(self):
        self.assertEqual(self.dc(competencia="2027-01", data="2027-01-20"), date(2027, 1, 20), "o fixo acabou: a própria data")
        self.assertEqual(self.dc(competencia="2026-11", data="2026-11-20", tipo="receita"), date(2026, 11, 20), "recebimento não segue vínculo")
        self.assertEqual(calc.data_caixa({"vinculo": "r-sal", "data": "2026-11-20"}, {}), date(2026, 11, 20), "sem os dados: a própria data")
        self.assertEqual(self.dc(vinculo="nada", data="2026-11-20"), date(2026, 11, 20))
        self.assertIsNone(calc.data_vinculo({"vinculo": "r-sal", "data": ""}, self.DADOS))


class TestDescontosERecorrencias(unittest.TestCase):
    def test_descontos_na_fonte(self):
        salario = {"tipo": "receita", "descricao": "Salário", "valor": 5000, "data": "2026-11-05", "conta": "c1", "pago": True,
                   "partes": [{"id": "base", "valor": 4000}],
                   "descontos": [{"descricao": "INSS", "modo": "pct", "valor": 11, "base": "base", "categoria": "c-impostos"},
                                 {"descricao": "Plano", "valor": 250.4}, {"modo": "pct", "valor": 1}, {"valor": 0}, "lixo"]}
        d = calc.descontos_de(salario)
        self.assertEqual([(x["descricao"], x["valor"]) for x in d], [("INSS", 440.0), ("Plano", 250.4), ("Desconto", 50.0)])
        self.assertTrue(all(x["desconto"] and x["tipo"] == "despesa" and x["pai"] == "Salário" and x["pago"] for x in d))
        self.assertEqual(d[0]["categoria"], "c-impostos")

    def test_descontos_so_de_recebimentos(self):
        self.assertEqual(calc.descontos_de({"tipo": "despesa", "descontos": [{"valor": 1}]}), [])
        self.assertEqual(calc.descontos_de({"tipo": "receita", "desconto": True, "descontos": [{"valor": 1}]}), [])
        self.assertEqual(calc.descontos_de({"tipo": "receita", "descontos": "x"}), [])

    def test_ativa_em(self):
        mensal = {"inicio": "2026-03", "fim": "2026-12"}
        self.assertFalse(calc.ativa_em(mensal, "2026-02"))
        self.assertTrue(calc.ativa_em(mensal, "2026-03"))
        self.assertTrue(calc.ativa_em(mensal, "2026-12"))
        self.assertFalse(calc.ativa_em(mensal, "2027-01"))
        anual = {"inicio": "2025-04", "freq": "anual"}
        self.assertTrue(calc.ativa_em(anual, "2027-04"))
        self.assertFalse(calc.ativa_em(anual, "2027-05"))
        self.assertFalse(calc.ativa_em({}, "2026-01"), "sem início: nunca")

    def test_ocorrencias_do_mes(self):
        dados = {
            "lancamentos": [
                {"id": "l1", "descricao": "Mercado", "tipo": "despesa", "valor": 200, "data": "2026-11-03"},
                {"id": "l2", "descricao": "Aluguel pago", "recorrencia": "r1", "competencia": "2026-11", "data": "2026-11-10", "valor": 1500, "tipo": "despesa"},
                {"id": "l3", "descricao": "Outubro", "valor": 1, "data": "2026-10-30"},
                {"id": "l4", "descricao": "Pulado", "valor": 9, "data": "2026-11-04", "pulado": True},
            ],
            "recorrencias": [
                {"id": "r1", "descricao": "Aluguel", "tipo": "despesa", "valor": 1500, "dia": 10, "inicio": "2026-01"},
                {"id": "r2", "descricao": "Internet", "tipo": "despesa", "valor": 100, "dia": 31, "inicio": "2026-01"},
                {"id": "r3", "descricao": "Salário", "tipo": "receita", "valor": 3000, "dia": 5, "inicio": "2026-01", "descontos": [{"descricao": "INSS", "valor": 300}]},
                {"id": "r4", "descricao": "IPTU", "tipo": "despesa", "valor": 800, "dia": 1, "inicio": "2026-02", "freq": "anual"},
            ],
        }
        o = calc.ocorrencias_mes(dados, "2026-11")
        self.assertEqual([x["descricao"] for x in o], ["Mercado", "Aluguel pago", "Internet", "Salário", "INSS"])
        internet = o[2]
        self.assertEqual((internet["data"], internet["pago"], internet["recorrencia"], internet["competencia"]), ("2026-11-30", False, "r2", "2026-11"))


class TestCaixa(unittest.TestCase):
    HOJE = date(2026, 11, 15)

    def test_saldo_e_movimento(self):
        dados = {
            "bancos": [{"id": "b", "nome": "Banco", "contas": [{"id": "cc", "cartao": True, "fechamento": 5, "vencimento": 10}]}],
            "lancamentos": [
                {"tipo": "receita", "valor": 5000, "data": "2026-11-05", "pago": True, "descontos": [{"valor": 500}]},
                {"tipo": "despesa", "valor": 1200, "data": "2026-11-10", "pago": True},
                {"tipo": "despesa", "valor": 300, "data": "2026-11-20", "pago": True},  # pago para o futuro: não entra no saldo
                {"tipo": "despesa", "valor": 150, "data": "2026-11-12", "pago": False},  # atrasado
                {"tipo": "despesa", "valor": 80, "data": "2026-11-25", "pago": False},
                {"tipo": "receita", "valor": 400, "data": "2026-11-28", "pago": False},
                {"tipo": "despesa", "valor": 90, "data": "2026-10-20", "conta": "cc", "cartao": True, "pago": False},  # fatura de 10/11, atrasada
                {"tipo": "despesa", "valor": 70, "data": "2026-11-08", "conta": "cc", "cartao": True, "pago": True},  # fatura de 10/12
                {"tipo": "receita", "valor": 1000, "data": "2026-11-01", "pago": True, "ajuste": True},  # ajuste: só no saldo
                {"tipo": "despesa", "valor": 999, "data": "2026-11-02", "pago": True, "pulado": True},
            ],
        }
        c = calc.caixa(dados, hoje=self.HOJE)
        self.assertEqual(c["saldo"], 5000 - 500 - 1200 + 1000)
        self.assertEqual(c["entrou_mes"], 5000)
        self.assertEqual(c["saiu_mes"], 1200 + 300 + 500)
        self.assertEqual(c["a_pagar_mes"], 150 + 80 + 90)
        self.assertEqual(c["a_receber_mes"], 400)
        self.assertEqual(c["atrasado"], 150 + 90)

    def test_vazio(self):
        self.assertEqual(calc.caixa({}, hoje=self.HOJE), {"saldo": 0, "entrou_mes": 0, "saiu_mes": 0, "a_receber_mes": 0, "a_pagar_mes": 0, "atrasado": 0})


class TestCorDoDia(unittest.TestCase):
    """A Cor do dia: as cores do app em ordem, uma por dia, sem as neutras; o dia contado desde 01/01/1970."""

    def test_paleta_sem_as_neutras(self):
        nomes = [n for n, _ in calc.CORES_DIA]
        self.assertEqual(nomes, ["Vermelho", "Coral", "Laranja", "Ouro", "Verde", "Menta", "Turquesa", "Azul", "Índigo", "Lilás", "Rosa"],
                         "as do seletor, na mesma ordem, sem o Grafite")
        self.assertIn(("Grafite", "#B5B9C2"), calc.CORES_APP, "o Grafite continua para escolher à mão")

    def test_numero_do_dia(self):
        self.assertEqual(calc.numero_do_dia(date(1970, 1, 1)), 0)
        self.assertEqual(calc.numero_do_dia(date(2026, 11, 2)), 20759, "Math.floor(Date.UTC(2026, 10, 2) / 86400000)")

    def test_datas_fixas(self):
        self.assertEqual(calc.cor_do_dia(date(2026, 11, 2)), "#FFA23E", "20759 % 11 = 2: Laranja")
        self.assertEqual(calc.cor_do_dia(date(2026, 11, 3)), "#F2C14E", "amanhã a próxima: Ouro")
        self.assertEqual(calc.cor_do_dia(date(2026, 11, 4)), "#8BD45F", "Verde")

    def test_depois_da_ultima_volta_para_a_primeira(self):
        self.assertEqual(calc.cor_do_dia(date(2026, 11, 10)), "#FF77A9", "Rosa, a última")
        self.assertEqual(calc.cor_do_dia(date(2026, 11, 11)), "#FF5A4F", "Vermelho, a primeira")
        self.assertEqual(calc.cor_do_dia(date(2026, 11, 22)), calc.cor_do_dia(date(2026, 11, 11)), "11 dias depois, a mesma")

    def test_um_ciclo_passa_por_todas_uma_vez(self):
        ciclo = [calc.cor_do_dia(date(2026, 11, 11) + timedelta(days=i)) for i in range(11)]
        self.assertEqual(ciclo, [h for _, h in calc.CORES_DIA])
        self.assertNotIn("#B5B9C2", [calc.cor_do_dia(date(2026, 1, 1) + timedelta(days=i)) for i in range(400)], "nunca o Grafite")

    def test_ligada_por_padrao(self):
        hoje = date(2026, 11, 2)
        for ajustes in ({}, None, {"cor": "#8BD45F"}, {"cor": "#8BD45F", "cor_dia": True}, {"cor_dia": None}):
            with self.subTest(ajustes=ajustes):
                self.assertEqual(calc.cor_app(ajustes, hoje), "#FFA23E", "só um False desliga, mesmo para quem já tinha escolhido uma cor")

    def test_desligada_fica_a_escolhida(self):
        hoje = date(2026, 11, 2)
        self.assertEqual(calc.cor_app({"cor": "#8BD45F", "cor_dia": False}, hoje), "#8BD45F")
        self.assertEqual(calc.cor_app({"cor_dia": False}, hoje), "#62B5FF", "sem cor escolhida, o azul da paleta da família")
        self.assertEqual(calc.cor_app({"cor": "#ff0000;background:url(x)", "cor_dia": False}, hoje), "#ff0000", "nada além de #rrggbb")
        self.assertEqual(calc.cor_app({"cor": "azul", "cor_dia": False}, hoje), "#62B5FF")

    def test_o_azul_de_antes_vira_o_da_familia(self):
        hoje = date(2026, 11, 2)
        for antiga in ("#56AEFF", "#56aeff"):
            with self.subTest(antiga=antiga):
                self.assertEqual(calc.cor_app({"cor": antiga, "cor_dia": False}, hoje), "#62B5FF")
        self.assertIn(("Azul", "#62B5FF"), calc.CORES_APP)


if __name__ == "__main__":
    unittest.main()
