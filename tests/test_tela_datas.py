"""Tela: o campo de data da família (o modelo é o Prazo do ResolvIA), num Chromium de verdade, sem servidor (a prévia).
Nada da janela de data do celular: atalhos em botões (Hoje, Amanhã, Sábado, Próx. semana; Hoje e Ontem numa data que
não passa de hoje; Hoje, Ontem e Amanhã num lançamento) e Outra data, que abre o mês ali embaixo, com ‹ e › e os meses
do ano no nome do mês. Vale no lançamento, no investimento (Valor em e Vencimento), no Aplicar mais, no benefício e na
revisão da leitura por IA. O relógio fica em 02/11/2026 (uma segunda). Dados inventados (Ana, Banco Azul)."""
import unittest

from tests.tela_base import Tela, base, BANCOS

INV = {"id": "i-cdb", "nome": "CDB Azul", "banco": "b-azul", "tipo": "cdb", "valor": 10000, "data_valor": "2026-08-03", "indexador": "cdi_pct",
       "taxa": 100, "titular": "eu", "liquidez": "diaria", "vencimento": "2028-03-15"}


class TelaDatas(Tela):
    def campo(self, id_):
        return f'#folhas [data-dc="{id_}"]'

    def atalhos(self, id_):
        return self.js(f"[...document.querySelectorAll('{self.campo(id_)} .dc-ch .chip')].map(b => [b.textContent.trim(), b.dataset.v || '', b.classList.contains('on')])")

    def valor(self, id_):
        return self.pg.input_value(f"#{id_}")

    def titulo_mes(self, id_):
        return self.texto(f"{self.campo(id_)} .cal-tit")

    def nova_despesa(self):
        self.ir("caixa")
        self.clicar('#nav [data-a="novo"]')
        self.assertEqual(self.folha(), "Nova despesa")


class TestLancamento(TelaDatas):
    def test_atalhos_sem_a_janela_do_celular(self):
        self.abrir(base(bancos=BANCOS))
        self.nova_despesa()
        self.assertEqual(self.pg.locator('#folhas input[type="date"]').count(), 0, "nenhum campo de data do celular")
        self.assertEqual(self.texto("#lf-data-l"), "Data")
        self.assertEqual(self.atalhos("lf-data"), [["Hoje", "2026-11-02", True], ["Ontem", "2026-11-01", False], ["Amanhã", "2026-11-03", False],
                                                   ["Outra data", "", False]], "começa em hoje")
        self.clicar(f'{self.campo("lf-data")} [data-v="2026-11-01"]')
        self.assertEqual(self.valor("lf-data"), "2026-11-01", "Ontem")
        self.assertEqual([x[0] for x in self.atalhos("lf-data") if x[2]], ["Ontem"], "o botão escolhido fica marcado")
        self.assertEqual(self.js("T.LF.data"), "2026-11-01", "o lançamento recebe a data")

    def test_outra_data_abre_o_mes_e_escolhe_o_dia(self):
        self.abrir(base(bancos=BANCOS))
        self.nova_despesa()
        self.assertEqual(self.pg.locator(f'{self.campo("lf-data")} .cal').count(), 0, "o mês fica fechado")
        self.clicar(f'{self.campo("lf-data")} [data-a="dc-cal"]')
        self.assertEqual(self.titulo_mes("lf-data"), "Novembro de 2026", "abre no mês da data")
        self.assertEqual(self.texto(f'{self.campo("lf-data")} .cal-d.hoje'), "2", "hoje marcado")
        self.assertEqual(self.pg.get_attribute(f'{self.campo("lf-data")} [data-a="dc-cal"]', "aria-expanded"), "true")
        self.assertEqual(self.textos(f'{self.campo("lf-data")} .cal-s'), ["D", "S", "T", "Q", "Q", "S", "S"], "domingo primeiro")
        self.clicar(f'{self.campo("lf-data")} [data-a="dc-mes"][data-v="1"]')
        self.assertEqual(self.titulo_mes("lf-data"), "Dezembro de 2026")
        self.clicar(f'{self.campo("lf-data")} .cal-d[data-v="2026-12-24"]')
        self.assertEqual(self.valor("lf-data"), "2026-12-24")
        self.assertEqual(self.pg.locator(f'{self.campo("lf-data")} .cal').count(), 0, "escolher fecha o mês")
        self.assertEqual(self.atalhos("lf-data")[-1], ["24 dez", "", True], "o Outra data mostra o dia escolhido")
        self.pg.wait_for_function("document.querySelector('#folhas [data-a=\"lf-pago\"].on').textContent === 'A pagar'")

    def test_o_mes_aberto_continua_quando_a_janela_se_redesenha(self):
        self.abrir(base(bancos=BANCOS))
        self.nova_despesa()
        self.clicar(f'{self.campo("lf-data")} [data-a="dc-cal"]')
        self.clicar(f'{self.campo("lf-data")} [data-a="dc-mes"][data-v="-1"]')
        self.js("(T.pintarFolha(), true)")
        self.assertEqual(self.titulo_mes("lf-data"), "Outubro de 2026", "o mesmo mês, depois de redesenhar")
        self.clicar(f'{self.campo("lf-data")} [data-a="dc-cal"]')
        self.assertEqual(self.pg.locator(f'{self.campo("lf-data")} .cal').count(), 0, "Outra data de novo fecha")

    def test_meses_do_ano_no_nome_do_mes(self):
        self.abrir(base(bancos=BANCOS))
        self.nova_despesa()
        self.clicar(f'{self.campo("lf-data")} [data-a="dc-cal"]')
        self.clicar(f'{self.campo("lf-data")} .cal-tit')
        self.assertEqual(self.titulo_mes("lf-data"), "2026", "o ano, com os meses")
        self.assertEqual(self.textos(f'{self.campo("lf-data")} .cal-m'), ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"])
        self.clicar(f'{self.campo("lf-data")} [data-a="dc-mes"][data-v="12"]')
        self.assertEqual(self.titulo_mes("lf-data"), "2027", "› vai para o ano seguinte")
        self.clicar(f'{self.campo("lf-data")} .cal-m[data-v="2027-05"]')
        self.assertEqual(self.titulo_mes("lf-data"), "Maio de 2027", "o mês escolhido, com os dias")
        self.clicar(f'{self.campo("lf-data")} .cal-d[data-v="2027-05-10"]')
        self.assertEqual(self.valor("lf-data"), "2027-05-10")
        self.assertEqual(self.atalhos("lf-data")[-1][0], "10 mai 2027", "de outro ano, com o ano")

    def test_salva_a_data_escolhida(self):
        self.abrir(base(bancos=BANCOS))
        self.nova_despesa()
        self.digitar("#lf-valor", "4590")
        self.preencher("#lf-desc", "Mercado")
        self.clicar(f'{self.campo("lf-data")} [data-v="2026-11-01"]')
        self.clicar('#folhas [data-a="lf-salvar"]')
        l = [x for x in self.js("T.S.d.lancamentos") if x["descricao"] == "Mercado"]
        self.assertEqual((len(l), l[0]["data"] if l else None), (1, "2026-11-01"))


class TestInvestimento(TelaDatas):
    def editar(self):
        self.abrir(base(bancos=BANCOS, investimentos=[INV]))
        self.js("(T.abrirInvestimento('i-cdb'), true)")
        self.esperar()

    def test_valor_em_so_ate_hoje(self):
        self.editar()
        self.assertEqual(self.atalhos("f-data"), [["Hoje", "2026-11-02", False], ["Ontem", "2026-11-01", False], ["3 ago", "", True]],
                         "Hoje e Ontem; a data de antes no Outra data")
        self.clicar(f'{self.campo("f-data")} [data-a="dc-cal"]')
        self.assertEqual(self.titulo_mes("f-data"), "Agosto de 2026", "abre no mês da data")
        self.clicar(f'{self.campo("f-data")} [data-a="dc-mes"][data-v="1"]')
        self.clicar(f'{self.campo("f-data")} [data-a="dc-mes"][data-v="1"]')
        self.clicar(f'{self.campo("f-data")} [data-a="dc-mes"][data-v="1"]')
        self.assertEqual(self.titulo_mes("f-data"), "Novembro de 2026")
        self.assertTrue(self.pg.is_disabled(f'{self.campo("f-data")} [data-a="dc-mes"][data-v="1"]'), "nada depois deste mês")
        self.assertTrue(self.pg.is_disabled(f'{self.campo("f-data")} .cal-d[data-v="2026-11-03"]'), "nem depois de hoje")
        self.assertFalse(self.pg.is_disabled(f'{self.campo("f-data")} .cal-d[data-v="2026-11-02"]'))

    def test_vencimento_longe_pelos_meses_e_sem_data(self):
        self.editar()
        self.assertEqual(self.texto("#f-venc-l"), "Vencimento (opcional)")
        at = self.atalhos("f-venc")
        self.assertEqual((at[-2], at[-1]), (["15 mar 2028", "", True], ["Sem data", "", False]), "o vencimento de antes e o Sem data")
        self.clicar(f'{self.campo("f-venc")} [data-a="dc-cal"]')
        self.clicar(f'{self.campo("f-venc")} .cal-tit')
        self.clicar(f'{self.campo("f-venc")} [data-a="dc-mes"][data-v="12"]')
        self.clicar(f'{self.campo("f-venc")} .cal-m[data-v="2029-01"]')
        self.clicar(f'{self.campo("f-venc")} .cal-d[data-v="2029-01-15"]')
        self.assertEqual((self.valor("f-venc"), self.js("T.F.vencimento")), ("2029-01-15", "2029-01-15"))
        self.clicar(f'{self.campo("f-venc")} .chip:has-text("Sem data")')
        self.assertEqual((self.valor("f-venc"), self.js("T.F.vencimento")), ("", ""), "Sem data tira o vencimento")
        self.assertEqual([x[0] for x in self.atalhos("f-venc")], ["Hoje", "Amanhã", "Sábado", "Próx. semana", "Outra data"], "sem o Sem data quando não há data")

    def test_valor_novo_traz_a_data_de_hoje_no_campo(self):
        self.editar()
        self.digitar("#f-valor", "1234567")
        self.assertEqual(self.valor("f-data"), "2026-11-02")
        self.assertEqual([x[0] for x in self.atalhos("f-data") if x[2]], ["Hoje"], "o Hoje fica marcado")


class TestOutros(TelaDatas):
    def test_beneficio_desde_e_vale_ate(self):
        self.abrir(base(bancos=BANCOS, beneficios=[]), ui={"tab": "mais", "maisTela": "beneficios"})
        self.js("(T.abrirBeneficio(null), true)")
        self.esperar()
        self.assertEqual([x[0] for x in self.atalhos("fben-desde")], ["Hoje", "Ontem", "Amanhã", "Outra data"])
        self.assertEqual([x[0] for x in self.atalhos("fben-validade")], ["Hoje", "Amanhã", "Sábado", "Próx. semana", "Outra data"])
        self.assertEqual(self.atalhos("fben-validade")[2][1], "2026-11-07", "o sábado desta semana")
        self.assertEqual(self.atalhos("fben-validade")[3][1], "2026-11-09", "a segunda que vem")
        self.clicar(f'{self.campo("fben-validade")} [data-v="2026-11-09"]')
        self.assertEqual(self.js("T.FBEN.validade"), "2026-11-09")

    def test_atalhos_de_sabado_e_proxima_semana_conforme_o_dia(self):
        self.assertEqual(self.js("T.atalhosData('futuro', new Date(2026, 10, 6)).map(x => x[0] + ' ' + x[1])"),
                         ["Hoje 2026-11-06", "Amanhã 2026-11-07", "Próx. semana 2026-11-09"], "na sexta, o sábado é amanhã")
        self.assertEqual(self.js("T.atalhosData('futuro', new Date(2026, 10, 8)).map(x => x[0] + ' ' + x[1])"),
                         ["Hoje 2026-11-08", "Amanhã 2026-11-09", "Sábado 2026-11-14"], "no domingo, a próxima semana é amanhã")
        self.assertEqual(self.js("T.atalhosData('futuro', new Date(2026, 10, 7)).map(x => x[0])"), ["Hoje", "Amanhã", "Sábado", "Próx. semana"],
                         "no sábado, o próximo sábado")

    def test_aplicar_mais_ate_hoje(self):
        self.abrir(base(bancos=BANCOS, investimentos=[INV]))
        self.js("(T.abrirInvestimento('i-cdb'), true)")
        self.esperar()
        self.clicar('.folha [data-a="inv-aplicar"]')
        self.assertEqual(self.atalhos("ap-data"), [["Hoje", "2026-11-02", True], ["Ontem", "2026-11-01", False], ["Outra data", "", False]])
        self.clicar(f'{self.campo("ap-data")} [data-v="2026-11-01"]')
        self.assertEqual(self.js("T.AP.data"), "2026-11-01")

    def test_mes_no_escuro_e_no_claro_sem_passar_da_tela(self):
        for tema in ("escuro", "claro"):
            self.abrir(base(bancos=BANCOS, ajustes={"tema": tema}))
            self.nova_despesa()
            self.clicar(f'{self.campo("lf-data")} [data-a="dc-cal"]')
            larg = self.js(f"[document.querySelector('{self.campo('lf-data')} .cal').getBoundingClientRect().right, innerWidth]")
            self.assertLessEqual(larg[0], larg[1], f"{tema}: o mês cabe na tela")
            dias = self.js(f"[...document.querySelectorAll('{self.campo('lf-data')} .cal-d')].map(b => Math.round(b.getBoundingClientRect().height))")
            self.assertEqual(len(set(dias)), 1, f"{tema}: os dias do mesmo tamanho ({set(dias)})")


if __name__ == "__main__":
    unittest.main()
