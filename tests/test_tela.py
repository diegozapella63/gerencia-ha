"""A tela (gerencia/app/www/app.js) testada função por função num Chromium de verdade.

O app.js abre com window.GERENCIA_TESTE = true e deixa as funções de dentro à mão (só nos testes). O relógio fica
parado em 02/11/2026 10:00 (segunda-feira), no fuso de São Paulo. Os cálculos que existem nos dois lados (calc.py e
app.js) são conferidos um contra o outro: a tela e os sensores do Home Assistant precisam dar o mesmo número.
Base e ajudantes em tests/tela_base.py. Sem o playwright, estes testes são pulados.
"""
import math
import unittest
from datetime import date

from tests.base import INDICES
from tests.tela_base import Tela, base, BANCOS, HOJE
import calc


# ---------------------------------------------------------------------------------------------------------------
class TestIgualAoServidor(Tela):
    """O mesmo cálculo no calc.py e no app.js dá o mesmo resultado."""

    INVS = [
        {"id": "i1", "valor": 1000, "indexador": "cdi_pct", "taxa": 110, "data_valor": "2025-11-03", "tipo": "cdb"},
        {"id": "i2", "valor": 2500, "indexador": "cdi_mais", "taxa": 1.5, "data_valor": "2026-06-30", "tipo": "cdb", "titular": "terceiros", "terceiro": "Mãe"},
        {"id": "i3", "valor": 800, "indexador": "pre", "taxa": 12, "data_valor": "2024-01-15", "tipo": "outro"},
        {"id": "i4", "valor": 5000, "indexador": "ipca_mais", "taxa": 6, "data_valor": "2026-10-01", "tipo": "tesouro"},
        {"id": "i5", "valor": 300, "indexador": "selic_mais", "taxa": 0.1, "data_valor": "2026-11-02", "tipo": "tesouro"},
        {"id": "i6", "valor": 1200, "indexador": "poupanca", "data_valor": "2026-01-10", "tipo": "poupanca"},
        {"id": "i7", "valor": 900, "indexador": "estimado", "taxa": 9, "data_valor": "2025-02-01", "tipo": "acoes"},
        {"id": "i8", "valor": 400, "indexador": "parado", "data_valor": "2020-01-01", "tipo": "dinheiro"},
        {"id": "i9", "valor": 30000, "indexador": "deprecia", "taxa": 15, "data_valor": "2025-05-20", "tipo": "bens"},
        {"id": "i10", "valor": 10000, "indexador": "deprecia", "taxa": 10, "data_valor": "2024-11-04", "tipo": "bens", "titular": "terceiros", "terceiro": "Beto",
         "partes": [{"categoria": "moveis", "valor": 6000, "taxa": 10}, {"categoria": "imoveis", "valor": 4000, "taxa": -5}]},
        {"id": "i11", "valor": 700, "indexador": "cdi_pct", "taxa": 100, "tipo": "caixinha"},
    ]

    def test_taxa_anual(self):
        for inv in self.INVS:
            with self.subTest(inv=inv["id"]):
                self.assertAlmostEqual(self.js("T.taxaAnual(a, T.S.d.indices)", inv) if self.usar(base()) is None else 0, calc.taxa_anual(inv, INDICES), places=12)

    def test_poupanca_com_selic_baixa(self):
        ind = dict(INDICES, selic=7.0, tr=0.05)
        self.usar(base(indices=ind))
        inv = {"indexador": "poupanca"}
        self.assertAlmostEqual(self.js("T.taxaAnual(a, T.S.d.indices)", inv), calc.taxa_anual(inv, ind), places=12)

    def test_dias_uteis(self):
        pares = [("2026-11-02", "2026-11-06"), ("2026-11-06", "2026-11-09"), ("2026-11-07", "2026-11-08"), ("2025-01-06", "2025-12-24"),
                 ("2024-02-28", "2024-03-04"), ("2026-11-02", "2026-11-02"), ("2026-11-09", "2026-11-02"), ("2020-01-01", "2026-11-02")]
        for a, b in pares:
            with self.subTest(a=a, b=b):
                self.assertEqual(self.js("T.diasUteis(T.pData(a[0]), T.pData(a[1]))", [a, b]), calc.dias_uteis(calc.parse_data(a), calc.parse_data(b)))

    def test_valor_de_hoje(self):
        for corrigir in (True, False):
            self.usar(base(ajustes={"corrigir": corrigir}))
            for inv in self.INVS:
                with self.subTest(inv=inv["id"], corrigir=corrigir):
                    self.assertAlmostEqual(self.js("T.valorHoje(a)", inv), calc.valor_hoje(inv, INDICES, corrigir, HOJE), places=6)

    def test_valor_em_1_e_5_anos_igual_a_projecao(self):
        """O relatório (calc.valor_em) e a projeção do app (projetar, sem aportes e sem IR) dão o mesmo valor."""
        for corrigir in (True, False):
            self.usar(base(ajustes={"corrigir": corrigir}))
            for inv in self.INVS:
                for anos in (1, 5):
                    with self.subTest(inv=inv["id"], corrigir=corrigir, anos=anos):
                        js = self.js(f"T.projetar([a], {anos}, 0, false).pts[{anos * 12}].valor", inv)
                        self.assertAlmostEqual(js, calc.valor_em(inv, INDICES, anos, corrigir, HOJE), places=4)

    def test_economia_real_do_plano_anual(self):
        """O aviso das dicas (calc.renda_reserva e economia_real) e a tela (rendaReserva e economiaReal) concordam."""
        diaria = [dict(self.INVS[0], liquidez="diaria"), dict(self.INVS[1], liquidez="diaria", titular=None),
                  {"id": "x", "valor": 50, "indexador": "cdi_pct", "taxa": 120, "tipo": "lci", "liquidez": "diaria"}]
        for nome, invs in (("média dos seus", self.INVS), ("o de liquidez diária que mais rende", diaria), ("sem investimentos: o CDI", [])):
            with self.subTest(nome):
                d = base(investimentos=invs)
                self.usar(d)
                js = self.js("T.rendaReserva()")
                py = calc.renda_reserva(d, HOJE)
                self.assertAlmostEqual(js["r"], py["r"], places=9)
                self.assertEqual(js["ir"], py["ir"])
                for mensal, anual in ((23.9, 239), (60, 599), (35.1, 330)):
                    self.assertAlmostEqual(self.js(f"T.economiaReal({mensal}, {anual}).real"), calc.economia_real(mensal, anual, py)["real"], places=6)

    def test_aliquota(self):
        for ir in ("reg", "15", "isento", "nao"):
            for dias in (0, 180, 181, 360, 361, 720, 721, 2000):
                self.assertEqual(self.js(f"T.aliquota('{ir}', {dias})"), calc.aliquota(ir, dias), (ir, dias))

    # oportunidades de investimento: a tela (Mais › Invest) e o aviso no celular (servidor) precisam concordar
    OPS = [{"indexador": "cdi_pct", "taxa": 118}, {"indexador": "cdi_pct", "taxa": 94, "isento": True, "vencimento": "2027-11-08"},
           {"indexador": "cdi_pct", "taxa": 92, "isento": True, "vencimento": "2027-02-01"}, {"indexador": "cdi_pct", "taxa": 95, "isento": True},
           {"indexador": "selic_mais", "taxa": 0.0950}, {"indexador": "selic_mais", "taxa": 0}, {"indexador": "cdi_mais", "taxa": 1.2},
           {"indexador": "pre", "taxa": 13.71}, {"indexador": "pre", "taxa": 12.1, "isento": True, "vencimento": "2028-05-01"},
           {"indexador": "ipca_mais", "taxa": 7.04}, {"indexador": "ipca_mais", "taxa": 6.4, "isento": True, "vencimento": "2029-08-15"},
           {"indexador": "estimado", "taxa": 9}]

    def test_oportunidades_equivalente_alvo_e_comparacao(self):
        import oportunidades as O
        aj = {"op_cdi": 110, "op_pre": 13.71, "op_ipca": 7.5}
        self.usar(base(investimentos=self.INVS, ajustes=aj))
        for x in self.OPS:
            with self.subTest(x=x):
                self.assertEqual(self.js("T.equivalente(a)", x), calc.equivalente(x, INDICES, HOJE))
                self.assertEqual(self.js("T.passaAlvo(a)", x), calc.passa_alvo(x, aj, INDICES, HOJE, self.INVS))
                self.assertEqual(self.js("T.passaAlvo(a, {})", x), calc.passa_alvo(x, {}, INDICES, HOJE, self.INVS), "sem alvo: melhor que os seus")
                self.assertEqual(self.js("T.compararMeus(a)", x), calc.comparar_meus(x, self.INVS, INDICES, HOJE))
                self.assertEqual(self.js("T.taxaOp(a)", x), O.taxa_txt(x))
        for g, v in (("pos", 113.94), ("pos", 120.0), ("pos", 101.02), ("pre", 13.2), ("ipca", 6.88)):
            self.assertEqual(self.js("T.valorOp(a[0], a[1])", [g, v]), O.valor_txt(g, v), (g, v))

    def test_totais(self):
        self.usar(base(investimentos=self.INVS))
        js = self.js("T.totais()")
        py = calc.totais(base(investimentos=self.INVS), HOJE)
        self.assertAlmostEqual(js["total"], py["total"], places=1)
        self.assertAlmostEqual(js["meu"], py["meu"], places=1)
        self.assertAlmostEqual(js["terc"], py["terceiros"], places=1)
        self.assertAlmostEqual(js["mes"], py["rende_mes"], places=1)

    def test_data_do_caixa_no_cartao(self):
        self.usar(base(bancos=BANCOS))
        casos = [("2026-11-03", "k-ana"), ("2026-11-05", "k-ana"), ("2026-12-20", "k-ana"), ("2026-11-10", "k-beto"), ("2026-11-26", "k-beto"),
                 ("2026-02-28", "k-beto"), ("2026-11-03", "k-verde"), ("2026-11-03", "")]
        contas = calc.mapa_contas(base(bancos=BANCOS))
        for data, conta in casos:
            for cartao in (True, False):
                l = {"data": data, "conta": conta, "cartao": cartao}
                with self.subTest(l=l):
                    self.assertEqual(self.js("T.dataCaixa(a)", l), calc.data_caixa(l, contas).isoformat())

    def test_descontos_na_fonte(self):
        sal = {"id": "s1", "tipo": "receita", "descricao": "Salário", "valor": 5000, "data": "2026-11-05", "conta": "k-verde", "pago": True,
               "partes": [{"id": "p1", "descricao": "Base", "valor": 4000}],
               "descontos": [{"id": "x1", "descricao": "INSS", "modo": "pct", "valor": 11, "base": "p1"}, {"id": "x2", "descricao": "Plano", "valor": 250.4},
                             {"id": "x3", "modo": "pct", "valor": 1}, {"id": "x4", "valor": 0}]}
        self.usar(base(bancos=BANCOS))
        js = self.js("T.descontosDe(a).map(x => [x.descricao, x.valor, x.pago, x.desconto])", sal)
        py = [[x["descricao"], x["valor"], x["pago"], x["desconto"]] for x in calc.descontos_de(sal)]
        self.assertEqual(js, py)
        self.assertEqual(self.js("T.liquidoDe(a)", sal), round(5000 - 440 - 250.4 - 50, 2))

    def test_recorrencia_ativa(self):
        recs = [{"inicio": "2026-03", "fim": "2026-12"}, {"inicio": "2025-04", "freq": "anual"}, {}, {"inicio": "2026-11"}]
        for r in recs:
            for ym in ("2026-02", "2026-03", "2026-04", "2026-11", "2026-12", "2027-01", "2027-04"):
                with self.subTest(r=r, ym=ym):
                    self.assertEqual(self.js("T.ativaEm(a[0], a[1])", [r, ym]), calc.ativa_em(r, ym))

    CAIXA = {
        "bancos": BANCOS,
        "lancamentos": [
            {"id": "l1", "tipo": "receita", "descricao": "Salário", "valor": 5000, "data": "2026-11-05", "pago": True, "conta": "k-verde", "descontos": [{"id": "d", "valor": 500}]},
            {"id": "l2", "tipo": "despesa", "descricao": "Aluguel", "valor": 1200, "data": "2026-11-01", "pago": True, "conta": "k-verde"},
            {"id": "l3", "tipo": "despesa", "descricao": "Luz", "valor": 150, "data": "2026-11-01", "pago": False},
            {"id": "l4", "tipo": "despesa", "descricao": "Internet", "valor": 99.9, "data": "2026-11-20", "pago": False},
            {"id": "l5", "tipo": "receita", "descricao": "Freela", "valor": 400, "data": "2026-11-28", "pago": False},
            {"id": "l6", "tipo": "despesa", "descricao": "Farmácia", "valor": 90, "data": "2026-10-20", "conta": "k-ana", "cartao": True, "pago": False},
            {"id": "l7", "tipo": "despesa", "descricao": "Mercado", "valor": 70, "data": "2026-11-06", "conta": "k-ana", "cartao": True, "pago": True},
            {"id": "l8", "tipo": "receita", "descricao": "Ajuste", "valor": 1000, "data": "2026-10-01", "pago": True, "ajuste": True},
            {"id": "l9", "tipo": "despesa", "descricao": "Pulado", "valor": 999, "data": "2026-11-02", "pago": True, "pulado": True},
            {"id": "l10", "tipo": "despesa", "descricao": "Futuro pago", "valor": 30, "data": "2026-11-10", "pago": True},
        ],
        "recorrencias": [
            {"id": "r-net", "tipo": "despesa", "descricao": "Streaming", "valor": 55.9, "dia": 15, "inicio": "2026-01", "conta": "k-ana", "cartao": True},
            {"id": "r-cond", "tipo": "despesa", "descricao": "Condomínio", "valor": 680, "dia": 10, "inicio": "2026-01"},
            {"id": "r-iptu", "tipo": "despesa", "descricao": "IPTU", "valor": 800, "dia": 1, "inicio": "2026-02", "freq": "anual"},
        ],
    }

    def test_saldo_e_movimento_do_mes(self):
        d = base(**self.CAIXA)
        self.usar(d)
        py = calc.caixa(d, hoje=HOJE)
        self.assertAlmostEqual(self.js("T.saldoCaixa()"), py["saldo"], places=2)
        r = self.js("T.resumoMes('2026-11')")
        self.assertAlmostEqual(r["entrou"], py["entrou_mes"], places=2)
        self.assertAlmostEqual(r["saiu"], py["saiu_mes"], places=2)
        self.assertAlmostEqual(r["aEntrar"], py["a_receber_mes"], places=2)
        self.assertAlmostEqual(r["aSair"], py["a_pagar_mes"], places=2)

    def test_ocorrencias_do_mes(self):
        d = base(**self.CAIXA)
        self.usar(d)
        for ym in ("2026-10", "2026-11", "2026-12", "2027-02"):
            with self.subTest(ym=ym):
                js = sorted(self.js("T.lancamentosCompetencia(a).map(l => l.descricao + ' ' + l.valor)", ym))
                py = sorted(f"{l['descricao']} {calc.num(l['valor']):g}" for l in calc.ocorrencias_mes(d, ym))
                self.assertEqual(js, py)

    def test_despesa_ligada_ao_recebimento(self):
        """Um plano descontado do salário (vínculo): sai no dia em que o salário entra, nos dois lados.
        Aqui o salário de novembro entrou adiantado (01/11) e o plano é do dia 20: já saiu do caixa."""
        d = base(bancos=BANCOS, recorrencias=[
            {"id": "r-sal", "tipo": "receita", "descricao": "Salário", "valor": 5000, "dia": 5, "inicio": "2026-01"},
            {"id": "r-plano", "tipo": "despesa", "descricao": "Plano", "valor": 400, "dia": 20, "inicio": "2026-01", "vinculo": "r-sal"}],
            lancamentos=[{"id": "l-sal", "tipo": "receita", "descricao": "Salário", "valor": 5000, "data": "2026-11-01", "pago": True, "recorrencia": "r-sal", "competencia": "2026-11"},
                         {"id": "l-plano", "tipo": "despesa", "descricao": "Plano", "valor": 400, "data": "2026-11-20", "pago": True, "recorrencia": "r-plano", "competencia": "2026-11", "vinculo": "r-sal"}])
        self.usar(d)
        self.assertEqual(self.js("T.dataCaixa(T.S.d.lancamentos[1])"), "2026-11-01", "a tela usa a data do salário")
        self.assertAlmostEqual(self.js("T.saldoCaixa()"), 4600, places=2)
        self.assertAlmostEqual(calc.caixa(d, hoje=HOJE)["saldo"], 4600, places=2, msg="o saldo do servidor (sensores) é o mesmo")

    def test_cor_do_dia(self):
        """A Cor do dia é a mesma na tela e no relatório do servidor, pela data daqui (não a de Greenwich)."""
        self.assertEqual(self.js("T.CORES_APP"), [list(c) for c in calc.CORES_APP], "as mesmas cores")
        self.assertEqual(self.js("T.CORES_DIA"), [list(c) for c in calc.CORES_DIA], "e as mesmas sem as neutras")
        for dia in ("2026-11-02", "2026-11-03", "2026-11-10", "2026-11-11", "2027-02-28", "2028-02-29", "1970-01-01", "1969-12-31"):
            with self.subTest(dia=dia):
                d = date.fromisoformat(dia)
                self.assertEqual(self.js("T.numeroDoDia(T.pData(a))", dia), calc.numero_do_dia(d))
                self.assertEqual(self.js("T.corDoDia(T.pData(a))", dia), calc.cor_do_dia(d))
        # 23:30 em São Paulo já é dia 3 em Greenwich: vale o dia 2 daqui; 00:10 do dia 3, a do dia 3
        self.assertEqual(self.js("T.corDoDia(new Date('2026-11-03T02:30:00Z'))"), calc.cor_do_dia(date(2026, 11, 2)))
        self.assertEqual(self.js("T.corDoDia(new Date('2026-11-03T03:10:00Z'))"), calc.cor_do_dia(date(2026, 11, 3)))
        self.assertEqual(self.js("T.corDoDia()"), calc.cor_do_dia(HOJE), "sem data: hoje")

# ---------------------------------------------------------------------------------------------------------------
class TestInvestimentos(Tela):
    def test_projecao_sem_aporte_nem_ir(self):
        inv = {"id": "a", "valor": 10000, "indexador": "pre", "taxa": 12, "data_valor": "2026-11-02", "tipo": "cdb"}
        self.usar(base(investimentos=[inv]))
        p = self.js("(() => { const r = T.projetar(T.S.d.investimentos, 5, 0, false); return { fim: r.pts.at(-1), n: r.pts.length, V0: r.V0, rMed: r.rMed, m12: r.pts[12] }; })()")
        self.assertEqual(p["n"], 61, "um ponto por mês, do mês 0 ao 60")
        self.assertAlmostEqual(p["V0"], 10000)
        self.assertAlmostEqual(p["rMed"], 0.12)
        self.assertAlmostEqual(p["m12"]["valor"], 11200, places=6)
        self.assertAlmostEqual(p["fim"]["valor"], 10000 * 1.12 ** 5, places=4)
        self.assertAlmostEqual(p["fim"]["aplicado"], 10000)
        self.assertAlmostEqual(p["fim"]["real"], 10000 * 1.12 ** 5 / (1 + INDICES["ipca"] / 100) ** 5, places=4, msg="em dinheiro de hoje: sem a inflação")

    def test_projecao_com_aporte(self):
        inv = {"id": "a", "valor": 10000, "indexador": "pre", "taxa": 12, "data_valor": "2026-11-02", "tipo": "cdb"}
        self.usar(base(investimentos=[inv]))
        p = self.js("T.projetar(T.S.d.investimentos, 1, 500, false).pts.at(-1)")
        f = 1.12 ** (1 / 12)
        self.assertAlmostEqual(p["valor"], 11200 + 500 * (f ** 12 - 1) / (f - 1), places=4)
        self.assertAlmostEqual(p["aplicado"], 10000 + 12 * 500)

    def test_projecao_com_imposto(self):
        cdb = {"id": "a", "valor": 10000, "indexador": "pre", "taxa": 12, "data_valor": "2026-11-02", "tipo": "cdb"}
        lci = dict(cdb, id="b", tipo="lci")
        self.usar(base(investimentos=[cdb]))
        bruto = self.js("T.projetar(T.S.d.investimentos, 1, 0, false).pts.at(-1).valor")
        liquido = self.js("T.projetar(T.S.d.investimentos, 1, 0, true).pts.at(-1).valor")
        self.assertAlmostEqual(liquido, 10000 + 1200 * (1 - 0.175), places=4, msg="CDB com 365 dias: 17,5% sobre o rendimento")
        self.assertLess(liquido, bruto)
        self.usar(base(investimentos=[lci]))
        self.assertAlmostEqual(self.js("T.projetar(T.S.d.investimentos, 1, 0, true).pts.at(-1).valor"), 11200, places=4, msg="LCI é isenta")

    def test_aliquota_regressiva(self):
        casos = [("reg", 0, 0.225), ("reg", 180, 0.225), ("reg", 181, 0.2), ("reg", 360, 0.2), ("reg", 361, 0.175), ("reg", 720, 0.175), ("reg", 721, 0.15),
                 ("15", 10, 0.15), ("isento", 900, 0), ("nao", 900, 0)]
        for ir, dias, esperado in casos:
            self.assertEqual(self.js("T.aliquota(a[0], a[1])", [ir, dias]), esperado, (ir, dias))

    def test_bens_na_projecao_perdem_valor(self):
        bem = {"id": "c", "valor": 20000, "indexador": "deprecia", "taxa": 10, "data_valor": "2026-11-02", "tipo": "bens"}
        self.usar(base(investimentos=[bem]))
        fim = self.js("T.projetar(T.S.d.investimentos, 2, 0, true).pts.at(-1).valor")
        self.assertAlmostEqual(fim, 20000 * 0.9 ** 2, places=4, msg="perde 10% ao ano, sem imposto")
        self.assertEqual(self.js("T.rendeMes(20000, -0.1)"), 0)
        self.assertAlmostEqual(self.js("T.perdeMes(20000, -0.1)"), 20000 * (1 - 0.9 ** (1 / 12)), places=6)

    def test_bem_em_partes(self):
        bem = {"id": "c", "valor": 10000, "indexador": "deprecia", "taxa": 0, "data_valor": "2025-11-03", "tipo": "bens",
               "partes": [{"categoria": "moveis", "valor": 6000, "taxa": 10}, {"categoria": "imoveis", "valor": 4000, "taxa": 0}]}
        self.usar(base(investimentos=[bem]))
        anos = calc.dias_uteis(date(2025, 11, 3), HOJE) / 252
        partes = self.js("T.partesHoje(a).map(p => [p.categoria, p.v, p.r])", bem)
        self.assertEqual(partes[0][0], "moveis")
        self.assertAlmostEqual(partes[0][1], 6000 * 0.9 ** anos, places=6)
        self.assertEqual(partes[1][1:], [4000, 0])
        self.assertEqual(self.js("T.taxaPartes(a)", bem["partes"]), 6.0, "média pesada pelo valor")
        self.assertEqual(self.js("T.taxaPartes([])"), 0)

    def test_rotulos(self):
        r = lambda inv: self.js("T.rotuloTaxa(a)", inv)
        self.assertEqual(r({"indexador": "deprecia", "taxa": 15}), "perde 15% a.a.")
        self.assertEqual(r({"indexador": "deprecia", "taxa": -2.5}), "valoriza 2,5% a.a.")
        self.assertEqual(r({"indexador": "deprecia", "taxa": 0}), "mantém o valor")
        self.assertEqual(r({"indexador": "cdi_pct", "taxa": 110}), "110% do CDI")
        self.assertEqual(r({"indexador": "selic_mais", "taxa": 0}), "Selic")
        self.assertEqual(r({"indexador": "parado"}), "Sem rendimento")

    def test_divisao_por_banco_dono_tipo_liquidez(self):
        invs = [
            {"id": "1", "banco": "b-azul", "valor": 1000, "indexador": "parado", "tipo": "cdb", "liquidez": "diaria"},
            {"id": "2", "banco": "b-azul", "valor": 500, "indexador": "parado", "tipo": "lci", "titular": "terceiros", "terceiro": "Mãe"},
            {"id": "3", "banco": "", "valor": 3000, "indexador": "parado", "tipo": "cdb", "liquidez": "vencimento"},
        ]
        self.usar(base(bancos=BANCOS, investimentos=invs))
        g = lambda k: self.js("T.grupos(T.S.d.investimentos, a).map(x => [x.nome, x.v, x.n])", k)
        self.assertEqual(g("banco"), [["Sem banco", 3000, 1], ["Banco Azul", 1500, 2]])
        self.assertEqual(g("dono"), [["Seu", 4000, 2], ["Mãe", 500, 1]])
        self.assertEqual(g("tipo"), [["CDB", 4000, 2], ["LCI/LCA", 500, 1]])
        self.assertEqual(g("liquidez"), [["Só no vencimento", 3500, 2], ["Liquidez diária", 1000, 1]])

    def test_escopo_e_historico(self):
        invs = [{"id": "1", "valor": 100, "indexador": "parado"}, {"id": "2", "valor": 50, "indexador": "parado", "titular": "terceiros", "terceiro": "Mãe"}]
        self.usar(base(investimentos=invs, historico=[{"d": "2026-11-02", "total": 1}, {"d": "2026-10-01", "total": 9}]))
        self.assertEqual(self.js("['tudo', 'meu', 'terc'].map(e => T.porEscopo(e).length)"), [2, 1, 1])
        h = self.js("(T.registrarHistorico(T.S.d), T.S.d.historico)")
        self.assertEqual([x["d"] for x in h], ["2026-10-01", "2026-11-02"], "um ponto por dia, em ordem")
        self.assertEqual((h[-1]["total"], h[-1]["meu"], h[-1]["terceiros"]), (150, 100, 50))

    def test_categorias_e_taxas_dos_bens(self):
        self.usar(base(ajustes={"bens_taxas": {"moveis": 12, "veiculos": ""}}))
        self.assertEqual(self.js("T.taxaBem('moveis')"), 12, "a taxa ajustada")
        self.assertEqual(self.js("T.taxaBem('veiculos')"), 15, "vazio: a de costume")
        self.assertEqual(self.js("T.taxaBem('nova')"), 10, "categoria nova: 10% ao ano")
        self.assertEqual(self.js("T.catsBens()[0][0]"), "imoveis")
        # com o InventarIA: as categorias de lá, mais Imóveis e Veículos
        self.js("(T.S.bens = { ok: true, todas: [{ id: 'eletronicos', nome: 'Eletrônicos', taxa: 20 }, { id: 'arte', nome: 'Arte', taxa: 0 }] }, true)")
        self.assertEqual(self.js("T.catsBens().map(c => c[0])"), ["imoveis", "veiculos", "eletronicos", "arte"])
        self.assertEqual(self.js("T.nomeCatBem('arte')"), "Arte")


# ---------------------------------------------------------------------------------------------------------------
class TestCaixa(Tela):
    def setUp(self):
        self.usar(base(**TestIgualAoServidor.CAIXA))

    def test_meses_e_datas(self):
        self.assertEqual(self.js("[T.addYm('2026-11', 2), T.addYm('2026-01', -1), T.addYm('2026-05', 0)]"), ["2027-01", "2025-12", "2026-05"])
        self.assertEqual(self.js("[T.dataNoMes('2026-02', 31), T.dataNoMes('2028-02', 30), T.dataNoMes('2026-05', 0), T.dataNoMes('2026-05', '')]"),
                         ["2026-02-28", "2028-02-29", "2026-05-01", "2026-05-01"])
        self.assertEqual(self.js("[T.somaMeses('2026-01-31', 1), T.somaMeses('2026-11-15', 3)]"), ["2026-02-28", "2027-02-15"], "parcela de dia 31 cai no fim do mês")
        self.assertEqual(self.js("[T.nomeMes('2026-11'), T.nomeMes('2026-11', true)]"), ["novembro de 2026", "nov/26"])

    def test_lancamentos_pela_data_do_caixa(self):
        nov = self.js("T.lancamentosEntre('2026-11', '2026-11').map(l => [l.descricao, l.dc])")
        nomes = [n for n, _ in nov]
        self.assertIn(["Farmácia", "2026-11-12"], nov, "compra de outubro no cartão: vence em novembro")
        self.assertNotIn("Mercado", nomes, "compra de novembro depois do fechamento: dezembro")
        self.assertIn(["Streaming", "2026-11-12"], nov, "fixo de outubro no cartão")
        self.assertIn("Condomínio", nomes)
        self.assertIn("Desconto", nomes, "o desconto na fonte do salário")
        self.assertNotIn("Pulado", nomes)
        self.assertEqual(nov, sorted(nov, key=lambda x: x[1]) if False else nov)
        datas = [dc for _, dc in nov]
        self.assertEqual(datas, sorted(datas), "em ordem de data")

    def test_faturas(self):
        dez = self.js("T.faturasDe(T.lancamentosEntre('2026-12', '2026-12')).map(f => [f.k, f.total, f.pago, f.itens.length])")
        self.assertEqual(dez, [["k-ana|2026-12-12", 70 + 55.9, False, 2]], "Mercado (pago) e o Streaming de novembro (a pagar)")

    def test_fixo_lancado_some_o_virtual(self):
        d = base(**TestIgualAoServidor.CAIXA)
        d["lancamentos"].append({"id": "l-cond", "tipo": "despesa", "descricao": "Condomínio", "valor": 700, "data": "2026-11-10", "recorrencia": "r-cond", "competencia": "2026-11", "pago": True})
        self.usar(d)
        conds = self.js("T.lancamentosEntre('2026-11', '2026-11').filter(l => l.descricao === 'Condomínio').map(l => [l.id, l.valor])")
        self.assertEqual(conds, [["l-cond", 700]])

    def test_achar_lancamento(self):
        self.assertEqual(self.js("T.acharLanc('v:r-cond:2026-12')").get("data"), "2026-12-10")
        self.assertEqual(self.js("T.acharLanc('l2').dc"), "2026-11-01")
        self.assertEqual(self.js("T.acharLanc('d:l1:d').id"), "l1", "um desconto acha o recebimento")
        self.assertIsNone(self.js("T.acharLanc('v:nada:2026-11')"))
        self.assertIsNone(self.js("T.acharLanc('nada')"))

    def test_materializar(self):
        o = self.js("T.materializar({ tipo: 'despesa', descricao: 'X', valor: '10', aporte: true, vinculo: 'r', partes: [{ id: 'p' }], descontos: [{ id: 'd' }], data: '2026-11-01' }, { pago: true })")
        self.assertEqual((o["valor"], o["aporte"], o["vinculo"], o["pago"], o["partes"], o["descontos"]), (10, True, "r", True, [{"id": "p"}], [{"id": "d"}]))
        self.assertTrue(o["id"])

    def test_saldo_previsto(self):
        s = self.js("T.saldoCaixa('2026-11-30')")
        prev = self.js("T.saldoPrevisto('2026-11')")
        pend = self.js("T.lancamentosEntre(T.addYm('2026-11', -2), '2026-11').filter(l => !l.pago).reduce((t, l) => t + (l.tipo === 'receita' ? 1 : -1) * l.valor, 0)")
        self.assertAlmostEqual(prev, s + pend, places=6)
        self.assertAlmostEqual(self.js("T.saldoPrevisto('2025-01')"), self.js("T.saldoCaixa('2025-01-31')"), msg="mês antigo: só o que foi pago")

    def test_baixa_do_salario_leva_o_plano(self):
        d = base(recorrencias=[
            {"id": "r-sal", "tipo": "receita", "descricao": "Salário", "valor": 5000, "dia": 5, "inicio": "2026-01"},
            {"id": "r-plano", "tipo": "despesa", "descricao": "Plano", "valor": 400, "dia": 20, "inicio": "2026-01", "vinculo": "r-sal", "conta": "x"}],
            lancamentos=[{"id": "avulsa", "tipo": "despesa", "descricao": "Coparticipação", "valor": 30, "data": "2026-11-15", "vinculo": "r-sal"}])
        self.usar(d)
        r = self.js("""(() => { const d = T.S.d, rec = { tipo: 'receita', recorrencia: 'r-sal', competencia: '2026-11', data: '2026-11-07', pago: true, conta: 'k-verde' };
            T.baixaVinculados(d, rec); return d.lancamentos.map(l => [l.descricao, l.pago, l.data, l.conta]); })()""")
        self.assertIn(["Plano", True, "2026-11-07", "k-verde"], r, "o plano do mês nasce pago, no dia e na conta do salário")
        self.assertIn(["Coparticipação", True, "2026-11-07", "k-verde"], r)
        r2 = self.js("(T.baixaVinculados(T.S.d, { tipo: 'receita', recorrencia: 'r-sal', competencia: '2026-11', data: '2026-11-07', pago: false }), T.S.d.lancamentos.filter(l => l.descricao === 'Plano').map(l => l.pago))")
        self.assertEqual(r2, [False], "desfazer o salário desfaz o plano")

    def test_aportes(self):
        d = base(recorrencias=[
            {"id": "a1", "tipo": "despesa", "aporte": True, "descricao": "Aporte", "valor": 800, "dia": 6, "inicio": "2026-01"},
            {"id": "a2", "tipo": "despesa", "aporte": True, "descricao": "Aporte anual", "valor": 1200, "dia": 1, "inicio": "2026-03", "freq": "anual"},
            {"id": "a3", "tipo": "despesa", "aporte": True, "descricao": "Aporte velho", "valor": 999, "dia": 1, "inicio": "2025-01", "fim": "2026-05"}],
            lancamentos=[{"id": "x", "tipo": "despesa", "recorrencia": "a1", "competencia": "2026-10", "data": "2026-10-06", "valor": 800, "pago": True}])
        self.usar(d)
        self.assertEqual(self.js("T.aporteMensal()"), 900, "800 por mês + 1200 por ano / 12; o que acabou não conta")
        self.assertTrue(self.js("T.ehAporte(T.S.d.lancamentos[0])"), "lançado de um aporte fixo")
        self.assertEqual(self.js("T.aportesPendentes().map(l => l.id)"), ["v:a1:2026-11"], "o de novembro, ainda a aplicar; o de outubro já foi")

    def test_fluxo_com_dia_a_dia_previsto(self):
        d = base(ajustes={"prever_dia": True}, lancamentos=[
            {"id": f"m{k}", "tipo": "despesa", "descricao": "Mercado", "valor": v, "data": f"2026-{m:02d}-10", "pago": True}
            for k, (m, v) in enumerate([(8, 300), (9, 600), (10, 900)])])
        self.usar(d)
        self.assertAlmostEqual(self.js("T.mediaVariaveis()"), 600, msg="média dos 3 meses anteriores")
        self.js("(T.S.ui.cxPeriodo = 'meio', true)")
        s = self.js("T.serieFluxo()")
        self.assertEqual([x["ym"] for x in s][:2], ["2026-06", "2026-07"])
        nov = next(x for x in s if x["ym"] == "2026-11")
        self.assertEqual((nov["est"], nov["atual"]), (600, True), "o dia a dia previsto no mês atual")
        out = next(x for x in s if x["ym"] == "2026-10")
        self.assertEqual((out["sai"], out["est"], out["net"]), (900, 0, -900))
        self.usar(dict(d, ajustes={"prever_dia": False}))
        self.assertEqual(next(x for x in self.js("T.serieFluxo()") if x["ym"] == "2026-12")["est"], 0, "sem prever o dia a dia")


# ---------------------------------------------------------------------------------------------------------------
class TestLeituraPorIA(Tela):
    def setUp(self):
        self.usar(base(bancos=BANCOS, investimentos=[
            {"id": "cdb", "nome": "CDB Azul", "banco": "b-azul", "valor": 1000, "indexador": "parado", "tipo": "cdb", "data_valor": "2026-11-01"},
            {"id": "poup-mae", "nome": "Poupança", "banco": "b-verde", "valor": 500, "indexador": "parado", "tipo": "poupanca", "titular": "terceiros", "terceiro": "Mãe"}],
            lancamentos=[{"id": "ja", "tipo": "despesa", "descricao": "Padaria Sol", "valor": 12.5, "data": "2026-11-01"}]))
        self.js("(T.IAS = { situacao: 'auto', futuras: true, itens: [], invs: [], saldos: false, pessoa: '', arquivo: null }, true)")

    def preparar(self, itens):
        return self.js("(T.IAS.itens = a.map(x => Object.assign({ marcado: true, categoria: '' }, x)), T.prepararRevisaoCaixa(), T.IAS.itens.map(i => [i.conta, i.noCartao, i.categoria, i.dup, i.marcado]))", itens)

    def test_conta_de_cada_linha(self):
        r = self.preparar([
            {"tipo": "despesa", "descricao": "Posto", "valor": 200, "data": "2026-11-01", "banco": "banco azul", "cartao": True},
            {"tipo": "despesa", "descricao": "Feira", "valor": 50, "data": "2026-11-01", "banco": "Verde"},
            {"tipo": "receita", "descricao": "Pix", "valor": 150, "data": "2026-11-01", "categoria": "c-reembolso"},
        ])
        self.assertEqual(r[0][:2], ["k-ana", True], "o banco que a IA viu, no cartão")
        self.assertEqual(r[1][:2], ["k-verde", False], "pelo nome parecido do banco")
        self.assertEqual(r[2][:3], ["k-ana", False, "c-reembolso"], "sem banco: a conta de todos; receita nunca no cartão")
        self.assertEqual(r[1][2], "c-outros-gastos", "sem categoria: Outros gastos")

    def test_parece_ja_lancado(self):
        r = self.preparar([{"tipo": "despesa", "descricao": "PADARIA SOL LTDA", "valor": 12.5, "data": "2026-11-02"}])
        self.assertEqual(r[0][3:], [True, False], "mesmo valor, dois dias, mesmo começo de nome: desmarca")

    def test_pago_ou_pendente(self):
        pago = lambda it, sit="auto": self.js("(T.IAS.situacao = a[1], T.iaPago(a[0], a[0].data))", [it, sit])
        self.assertTrue(pago({"tipo": "despesa", "situacao": "feito", "data": "2026-12-01"}))
        self.assertFalse(pago({"tipo": "despesa", "situacao": "pendente", "data": "2026-10-01"}))
        self.assertTrue(pago({"tipo": "despesa", "data": "2026-10-01"}), "sem dizer: pela data")
        self.assertFalse(pago({"tipo": "despesa", "data": "2026-11-20"}))
        self.assertFalse(pago({"tipo": "despesa", "situacao": "feito", "data": "2026-11-01", "conta": "k-ana", "noCartao": True}), "no cartão: paga quando a fatura vence")
        self.assertTrue(pago({"tipo": "despesa", "data": "2026-10-02", "conta": "k-ana", "noCartao": True}), "fatura de 12/10 já venceu")
        self.assertTrue(pago({"tipo": "despesa", "situacao": "pendente", "data": "2026-12-01"}, "pago"))
        self.assertFalse(pago({"tipo": "despesa", "situacao": "feito", "data": "2026-10-01"}, "apagar"))

    def test_parcelas(self):
        it = {"tipo": "despesa", "descricao": "Geladeira", "valor": 300, "data": "2026-10-31", "categoria": "c-compras", "conta": "k-ana", "noCartao": True,
              "parcela_atual": 2, "parcelas_total": 4}
        todas = self.js("(() => { const d = { lancamentos: [] }; T.IAS.futuras = true; T.aplicarIACaixa(d, [a]); return d.lancamentos.map(l => [l.parcela, l.data, l.pago, l.cartao]); })()", it)
        self.assertEqual([x[:2] for x in todas], [["2/4", "2026-10-31"], ["3/4", "2026-11-30"], ["4/4", "2026-12-31"]])
        self.assertTrue(all(x[3] for x in todas))
        self.assertEqual([x[2] for x in todas], [False, False, False], "no cartão, a fatura de dezembro ainda não venceu")
        so = self.js("(() => { const d = { lancamentos: [] }; T.IAS.futuras = false; T.aplicarIACaixa(d, [a]); return d.lancamentos.length; })()", it)
        self.assertEqual(so, 1, "sem as próximas parcelas: só a de agora")

    def test_aplicacao_vira_aporte(self):
        it = {"tipo": "despesa", "descricao": "Aplicação CDB", "valor": 1000, "data": "2026-11-01", "categoria": "c-investimentos", "conta": "k-ana", "noCartao": True}
        l = self.js("(() => { const d = { lancamentos: [] }; T.aplicarIACaixa(d, [a]); return d.lancamentos[0]; })()", it)
        self.assertEqual((l["aporte"], l["cartao"]), (True, False))

    def test_investimentos(self):
        itens = [
            {"existente": "cdb", "valor": 0, "aporte": 300},  # "apliquei 300 no CDB": soma ao valor de hoje
            {"existente": "poup-mae", "valor": 650, "data_valor": "2026-10-31"},  # saldo novo
            {"nome": "Tesouro Selic", "banco": "Banco Roxo", "tipo": "tesouro", "valor": 2000, "indexador": "selic_mais", "taxa": 0.1, "liquidez": "diaria", "dono": "Tia", "aplicado": 1900},
            {"nome": "Poupança nova", "banco": "banco azul", "tipo": "poupanca", "valor": 100, "indexador": "poupanca", "taxa": 5},
        ]
        r = self.js("""(() => { const d = T.S.d; T.aplicarIAInvest(d, a); return { invs: d.investimentos.map(i => [i.nome, i.valor, i.data_valor, i.titular, i.terceiro, i.taxa, i.banco]),
            bancos: d.bancos.map(b => b.nome), obs: d.investimentos[2].obs }; })()""", itens)
        invs = r["invs"]
        self.assertEqual(invs[0][:3], ["CDB Azul", 1300, "2026-11-02"])
        self.assertEqual(invs[1][:3], ["Poupança", 650, "2026-10-31"])
        self.assertEqual(invs[2][:6], ["Tesouro Selic", 2000, "2026-11-02", "terceiros", "Tia", 0.1])
        self.assertIn("Banco Roxo", r["bancos"], "banco novo criado")
        self.assertEqual(r["obs"], "Valor aplicado: R$ 1.900,00")
        self.assertEqual((invs[3][5], invs[3][6]), (0, "b-azul"), "poupança não tem taxa; o banco pelo nome")

    def test_atualizar_saldos_de_uma_pessoa(self):
        r = self.js("""(() => { T.IAS.pessoa = 'Mãe'; T.IAS.saldos = true; const d = T.S.d;
            T.aplicarIAInvest(d, [{ nome: 'Caixinha', valor: 50, dono: 'Beto', indexador: 'cdi_pct', taxa: 100 }]); return d.investimentos.at(-1); })()""")
        self.assertEqual((r["titular"], r["terceiro"]), ("terceiros", "Mãe"), "a pessoa escolhida vale mais que a lida")

    def test_diferenca_do_saldo(self):
        d = lambda it, saldos=False: self.js("(T.IAS.saldos = a[1], T.difSaldo(a[0]))", [it, saldos])
        self.assertEqual(d({"existente": "cdb", "valor": 1250}), {"ex": d({"existente": "cdb", "valor": 1250})["ex"], "antes": 1000, "dif": 250})
        self.assertEqual(d({"existente": "cdb", "valor": 900})["dif"], -100, "resgate")
        self.assertIsNone(d({"existente": "cdb", "valor": 0}))
        self.assertIsNone(d({"existente": "nada", "valor": 10}))
        self.assertIsNone(d({"existente": "cdb", "valor": 1200, "aporte": 50}), "com aporte: não é saldo")
        self.assertEqual(d({"existente": "cdb", "valor": 1200, "aporte": 50}, True)["dif"], 200, "no Atualizar saldos, sim")

    def test_dono_e_achar_investimento(self):
        self.assertEqual(self.js("['mãe', 'MAE', 'eu', 'minha', '', 'tia ana'].map(T.donoDe)"), ["Mãe", "Mãe", "", "", "", "Tia ana"])
        a = lambda it, p="": self.js("T.acharInvSaldo(a[0], a[1])", [it, p])
        self.assertEqual(a({"banco": "azul"}), "cdb")
        self.assertEqual(a({"nome": "poupança"}, "Mãe"), "poup-mae")
        self.assertEqual(a({"banco": "verde"}, "meu"), "", "o do dono escolhido")
        self.assertEqual(a({"banco": ""}), "")


# ---------------------------------------------------------------------------------------------------------------
class TestDicasEFormatos(Tela):
    def test_meses_gratis(self):
        self.assertEqual(self.js("T.mesesGratis({ mensal: 23.9, anual: 239 })"), 2)
        self.assertEqual(self.js("T.mesesGratis({ mensal: 10, anual: 115 })"), 0, "meio mês não conta")
        self.assertEqual(self.js("T.mesesGratis({ mensal: 10, anual: 120 })"), 0)

    def test_onde_o_dinheiro_renderia(self):
        self.usar(base())
        self.assertEqual(self.js("T.rendaReserva().curto"), "100% do CDI", "sem investimentos")
        self.usar(base(investimentos=[{"id": "a", "nome": "CDB longo", "valor": 1000, "indexador": "pre", "taxa": 12, "tipo": "cdb", "liquidez": "vencimento"}]))
        self.assertEqual(self.js("T.rendaReserva().curto"), "seus investimentos", "sem liquidez diária: a média")
        self.usar(base(investimentos=[
            {"id": "a", "nome": "Caixinha", "valor": 1000, "indexador": "cdi_pct", "taxa": 100, "tipo": "caixinha", "liquidez": "diaria"},
            {"id": "b", "nome": "LCI diária", "valor": 1000, "indexador": "cdi_pct", "taxa": 95, "tipo": "lci", "liquidez": "diaria"},
            {"id": "c", "nome": "Da mãe", "valor": 1000, "indexador": "cdi_pct", "taxa": 200, "tipo": "lci", "liquidez": "diaria", "titular": "terceiros"}]))
        self.assertEqual(self.js("T.rendaReserva().curto"), "LCI diária", "a de liquidez diária que rende mais depois do IR; a de terceiros não conta")

    def test_economia_real_do_anual(self):
        self.usar(base())
        e = self.js("T.economiaReal(23.9, 239)")
        self.assertAlmostEqual(e["desconto"], 12 * 23.9 - 239, places=6)
        self.assertGreater(e["rende"], 0)
        self.assertAlmostEqual(e["real"], e["desconto"] - e["rende"], places=6)

    def test_categoria_acima_do_normal(self):
        lanc = []
        for m, v in ((7, 400), (8, 450), (9, 500), (10, 900)):
            lanc.append({"id": f"r{m}", "tipo": "despesa", "descricao": "Restaurante", "valor": v, "data": f"2026-{m:02d}-15", "categoria": "c-restaurantes"})
        lanc.append({"id": "m10", "tipo": "despesa", "descricao": "Mercado", "valor": 700, "data": "2026-10-15", "categoria": "c-mercado"})
        self.usar(base(lancamentos=lanc))
        c = self.js("T.dicaCategoria()")
        self.assertEqual((c["cat"], c["v"], c["media"], c["id"]), ("c-restaurantes", 900, 450, "cat:c-restaurantes:2026-10"))
        self.usar(base(lancamentos=lanc[:3] + [dict(lanc[3], valor=520)]))
        self.assertIsNone(self.js("T.dicaCategoria()"), "menos de R$ 150 acima da média: sem dica")

    def test_formatos(self):
        self.usar(base())
        self.assertEqual(self.js("[T.brl(1234.5), T.brl(1234.5, 0), T.brlS(-10), T.brlS(-0.001), T.plural(1, 'item', 'itens'), T.plural(2, 'item', 'itens')]"),
                         ["R$ 1.234,50".replace(" ", " "), "R$ 1.235", "−R$ 10,00", "R$ 0,00", "1 item", "2 itens"])
        self.assertEqual(self.js("[T.parseNum('1.234,56'), T.parseNum('12.5'), T.parseNum(' 2 000,00 '), T.parseNum('')].map(x => Number.isNaN(x) ? 'NaN' : x)"),
                         [1234.56, 12.5, 2000, "NaN"])
        self.assertEqual(self.js("(T.S.oculto = true, [T.brl(10), (T.S.oculto = false)])"), ["R$ •••••", False], "esconder valores")
        self.assertEqual(self.js("[T.niceStep(7), T.niceStep(13), T.niceStep(240), T.niceStep(0.3)]"), [10, 20, 250, 0.5])
        self.assertEqual(self.js("[T.round2(1.005), T.round2(2.675), T.semAcento('Ação Já')]")[2], "acao ja")

    def test_exemplo(self):
        """Carregar exemplo: dados inventados e consistentes."""
        ex = self.js("T.normalizar(T.gerarExemplo())")
        pessoas = {c.get("pessoa") for b in ex["bancos"] for c in b["contas"] if c.get("pessoa")}
        self.assertTrue(pessoas <= {"Ana", "Beto", "Mãe"}, f"nomes inventados ({pessoas})")
        ids = {c["id"] for b in ex["bancos"] for c in b["contas"]}
        usados = {l.get("conta") for l in ex["lancamentos"] + ex["recorrencias"] if l.get("conta")}
        self.assertTrue(usados <= ids, f"toda conta usada existe ({usados - ids})")
        self.assertTrue(ex["investimentos"] and ex["lancamentos"] and ex["recorrencias"])


if __name__ == "__main__":
    unittest.main()
