"""Tela: oportunidades de investimento (Mais › Invest) e o aviso no celular (Mais › Configurações › Opções), num
Chromium de verdade, sem servidor (a prévia, com as taxas de exemplo do oportDemo). Confere as famílias com o alvo ao
lado, as melhores taxas, o "No alvo", o equivalente em CDB, a comparação com os seus investimentos, as páginas de ofertas
(só com a IA), o Conferir agora, o horário com o Testar ao lado e quem recebe, como no ResolvIA, e o toque no aviso.
Os cálculos (equivalente, passaAlvo, compararMeus) são conferidos contra o calc.py em tests/test_tela.py.
Dados inventados (Ana, Beto, Banco Sol, Banco Azul, taxas de exemplo)."""
import unittest

from tests.tela_base import base, BANCOS
from tests.test_tela_mais import TelaMais

INVS = [{"id": "i1", "nome": "CDB Lua 2028", "banco": "b-azul", "valor": 5000, "indexador": "cdi_pct", "taxa": 104, "tipo": "cdb", "data_valor": "2026-11-01", "titular": "meu"},
        {"id": "i2", "nome": "Tesouro IPCA+ 2035", "banco": "b-verde", "valor": 3000, "indexador": "ipca_mais", "taxa": 6.2, "tipo": "tesouro", "data_valor": "2026-11-01", "titular": "meu"},
        {"id": "i3", "nome": "Da Carla", "banco": "b-verde", "valor": 900, "indexador": "cdi_pct", "taxa": 200, "tipo": "cdb", "data_valor": "2026-11-01", "titular": "terceiros", "terceiro": "Carla"}]
PAGINA = "https://www.bancosol.exemplo/investimentos"
INVEST = {"tab": "mais", "maisTela": "invest"}
OPCOES = {"tab": "mais", "maisTela": "config", "maisAba": "opcoes"}


class TelaOport(TelaMais):
    def abrir_invest(self, **aj):
        self.abrir(base(bancos=BANCOS, investimentos=INVS, ajustes=dict({"corrigir": True}, **aj)), ui=INVEST)
        self.pg.wait_for_selector("#oportunidades .op-row")

    def grupo(self, g):
        """[(nome, taxa, o que vem embaixo da taxa, comparação, no alvo)] de uma família."""
        return self.js("""[...document.querySelectorAll(`#oportunidades .op-grupo[data-grupo="${a}"] .op-row`)].map(r => [
            r.querySelector('.op-t b').textContent, r.querySelector('.op-v b').textContent,
            (r.querySelector('.op-v small') || {}).textContent || '', (r.querySelector('.op-meus') || {}).textContent || '',
            r.classList.contains('passa')])""", g)


class TestCartao(TelaOport):
    def test_as_tres_familias_com_as_melhores_taxas(self):
        self.abrir_invest()
        self.assertEqual(self.texto("#oportunidades h2"), "Oportunidades")
        self.assertEqual(self.textos("#oportunidades .op-grupo-cab > b"), ["Pós-fixado", "Prefixado", "IPCA+"])
        self.assertEqual(self.grupo("pos"), [["Tesouro Selic 2031", "Selic + 0,09%", "101,5% do CDI", "Menos que o seu", False],
                                             ["Tesouro Reserva 2036", "Selic", "100,7% do CDI", "Menos que o seu", False]],
                         "a de terceiros não conta como sua")
        self.assertEqual(self.grupo("pre"), [["Tesouro Prefixado 2032", "13,71% ao ano", "", "", False],
                                             ["Tesouro Prefixado 2029", "13,42% ao ano", "", "", False]], "sem prefixado seu: sem comparação")
        self.assertEqual([r[0] for r in self.grupo("ipca")], ["Tesouro IPCA+ 2032", "Tesouro IPCA+ 2040", "Tesouro IPCA+ com Juros Semestrais 2045"])
        self.assertEqual(self.grupo("ipca")[0][3], "Mais que o seu")
        self.assertIn("Tesouro Direto: taxas de hoje", self.texto("#oportunidades .dica-quando"))
        self.assertIn("Não é recomendação", self.texto("#oportunidades .op-nota"))

    def test_alvo_marca_o_que_passou_e_fica_guardado(self):
        self.abrir_invest(op_ipca=6.88)
        self.assertEqual([r[4] for r in self.grupo("ipca")], [True, True, False], "igual ao alvo também passa")
        self.assertEqual(self.pg.input_value('[data-op-alvo="op_ipca"]'), "6,88")
        self.pg.fill('[data-op-alvo="op_pre"]', "13,5")
        self.pg.locator('[data-op-alvo="op_pre"]').dispatch_event("change")
        self.esperar()
        self.assertEqual(self.dados()["ajustes"]["op_pre"], 13.5)
        self.assertEqual([r[4] for r in self.grupo("pre")], [True, False])
        self.assertEqual(self.esperar_aviso("Alvo salvo"), "Alvo salvo")
        self.pg.fill('[data-op-alvo="op_pre"]', "")
        self.pg.locator('[data-op-alvo="op_pre"]').dispatch_event("change")
        self.esperar()
        self.assertIsNone(self.dados()["ajustes"]["op_pre"], "vazio: sem alvo")

    def test_alvo_fora_do_que_faz_sentido_volta(self):
        self.abrir_invest(op_cdi=110)
        self.pg.fill('[data-op-alvo="op_cdi"]', "900")
        self.pg.locator('[data-op-alvo="op_cdi"]').dispatch_event("change")
        self.assertEqual(self.esperar_aviso("Use um número"), "Use um número de 50 a 300.")
        self.assertEqual((self.pg.input_value('[data-op-alvo="op_cdi"]'), self.dados()["ajustes"]["op_cdi"]), ("110", 110))
        self.pg.fill('[data-op-alvo="op_cdi"]', "abc")
        self.pg.locator('[data-op-alvo="op_cdi"]').dispatch_event("change")
        self.assertEqual(self.dados()["ajustes"]["op_cdi"], 110)

    def test_ver_mais_e_ver_menos(self):
        self.abrir_invest()
        self.assertEqual(self.conta("#oportunidades .op-todas"), 0, "nenhuma família com mais de 3")
        self.abrir_invest(op_paginas=[PAGINA])
        self.assertEqual(self.texto("#oportunidades .op-todas"), "Ver mais 1")
        self.clicar('#oportunidades [data-a="op-todas"]')
        self.assertEqual(len(self.grupo("pos")), 4)
        self.assertEqual(self.texto("#oportunidades .op-todas"), "Ver menos")

    def test_ofertas_das_paginas_com_o_equivalente_em_cdb(self):
        self.abrir_invest(op_paginas=[PAGINA], op_cdi=110)
        pos = self.grupo("pos")
        self.assertEqual(pos[0], ["CDB Banco Sol", "118% do CDI", "", "Mais que o seu", True])
        self.assertEqual(pos[1][:3], ["LCA Banco Sol", "94% do CDI", "como CDB de 113,9%"], "isenta: a LCA de 94% vale um CDB de 113,9% (IR de 17,5% até o vencimento)")
        self.assertIn("bancosol.exemplo · vence 06/11/2028", self.linha("#oportunidades .op-row", "CDB Banco Sol"))
        self.assertEqual(self.textos("#oportunidades .op-pag b"), ["bancosol.exemplo"])
        self.assertEqual(self.textos("#oportunidades .op-pag .op-t span"), ["2 ofertas"])

    def test_com_a_ia_desligada_so_o_tesouro(self):
        self.abrir_invest(op_paginas=[PAGINA], ia=False)
        self.assertEqual(self.conta("#oportunidades .op-paginas"), 0)
        self.assertNotIn("Banco Sol", self.texto("#oportunidades"))
        self.assertTrue(self.texto("#oportunidades .painel-lead").startswith("Taxas de hoje do Tesouro Direto, perto"))


class TestPaginas(TelaOport):
    def test_adicionar_e_tirar(self):
        self.abrir_invest()
        self.pg.fill("#op-url", "banco sem endereço")
        self.clicar('#oportunidades [data-a="op-pagina-add"]')
        self.assertEqual(self.esperar_aviso("Escreva"), "Escreva o endereço da página, começando com https://")
        self.pg.fill("#op-url", PAGINA)
        self.pg.press("#op-url", "Enter")
        self.esperar()
        self.assertEqual(self.dados()["ajustes"]["op_paginas"], [PAGINA])
        self.pg.wait_for_function("() => document.querySelectorAll('#oportunidades .op-pag').length === 1")
        self.pg.fill("#op-url", PAGINA)
        self.clicar('#oportunidades [data-a="op-pagina-add"]')
        self.assertEqual(self.esperar_aviso("já está"), "Essa página já está na lista.")
        self.clicar('#oportunidades [data-a="op-pagina-tirar"]')
        self.esperar()
        self.assertEqual(self.dados()["ajustes"]["op_paginas"], [])

    def test_ate_dez(self):
        self.abrir_invest(op_paginas=[f"https://b{k}.exemplo/cdb" for k in range(10)])
        self.assertEqual(self.conta("#op-url"), 0, "com 10, o campo some")

    def test_conferir_agora_busca_tudo(self):
        self.abrir_invest()
        self.js("(window.__f = [], true)")
        self.trocar_api("oportConferir", "async f => { window.__f.push(f); return T.oportDemo(); }".replace("T.", "window.GERENCIA_TESTE."))
        self.clicar('#oportunidades [data-a="op-conferir"]')
        self.pg.wait_for_function("() => window.__f.length === 1")
        self.assertEqual(self.js("window.__f"), [True])
        self.trocar_api("oportunidades", "async () => ({ titulos: [], ofertas: [], paginas: [], tesouro: { erro: 'Não consegui ler as taxas do Tesouro Direto.', dia: '2026-10-30' }, conferindo: false })")
        self.js("(T.S.oport = undefined, T.render(), true)")
        self.pg.wait_for_function("() => (document.querySelector('#oportunidades .dica-quando') || {}).textContent.includes('Não consegui')")
        self.assertEqual(self.texto("#oportunidades .dica-quando"), "Não consegui ler as taxas do Tesouro Direto. Taxas de 30/10/2026.")
        self.assertIn("erro", self.pg.get_attribute("#oportunidades .dica-quando", "class"))


class TestAvisoNoCelular(TelaOport):
    def test_ligar_comeca_com_quem_esta_usando(self):
        self.abrir(base(bancos=BANCOS), ui=OPCOES)
        self.assertEqual(self.texto("#op-oport h2"), "Oportunidades de investimento")
        self.assertIn("Desligado.", self.texto("#op-oport"))
        self.assertEqual(self.conta("#op-hora"), 0)
        self.clicar('#op-oport [data-a="ajuste"][data-k="op_aviso"]')
        self.esperar()
        self.pg.wait_for_function("() => (window.GERENCIA_TESTE.S.d.ajustes.op_para || []).length === 1")
        a = self.dados()["ajustes"]
        self.assertEqual((a["op_aviso"], a["op_para"]), (True, ["person.ana"]))
        self.pg.wait_for_selector("#op-oport .quem-p")
        self.assertEqual(self.pg.input_value("#op-hora"), "10:00")
        self.assertEqual(self.textos("#op-oport .op-hora-l .btn"), ["Testar"], "o Testar ao lado do horário, como no ResolvIA")
        self.assertIn("Nenhum alvo ainda.", self.texto("#op-oport"))

    def test_horario_quem_recebe_e_testar(self):
        self.abrir(base(bancos=BANCOS, ajustes={"op_aviso": True, "op_para": ["person.ana"], "op_cdi": 120}), ui=OPCOES)
        self.pg.wait_for_selector("#op-oport .quem-p")
        self.assertNotIn("Nenhum alvo", self.texto("#op-oport"))
        self.pg.fill("#op-hora", "08:30")
        self.pg.locator("#op-hora").dispatch_event("change")
        self.esperar()
        self.assertEqual(self.dados()["ajustes"]["op_hora"], "08:30")
        self.clicar('#op-oport [data-a="aviso-pessoa"][data-v="person.beto"]')
        self.esperar()
        self.assertEqual(self.dados()["ajustes"]["op_para"], ["person.ana", "person.beto"])
        self.clicar('#op-oport [data-a="op-testar"]')
        self.assertEqual(self.esperar_aviso("prévia"), "Na prévia o aviso não é enviado.")
        self.trocar_api("oportTestar", "async () => ({ enviados: 1, passam: 0 })")
        self.clicar('#op-oport [data-a="op-testar"]')
        self.assertEqual(self.esperar_aviso("celular"), "Aviso enviado para o seu celular (nada no alvo agora).")

    def test_escolher_o_alvo_leva_para_mais_invest(self):
        self.abrir(base(bancos=BANCOS, ajustes={"op_aviso": True, "op_para": ["person.ana"]}), ui=OPCOES)
        self.clicar('#op-oport [data-a="tab"][data-ancora="oportunidades"]')
        self.assertEqual(self.js("[T.S.ui.tab, T.S.ui.maisTela]"), ["mais", "invest"])
        self.pg.wait_for_selector("#oportunidades")

    def test_o_toque_no_aviso_abre_as_oportunidades(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "inicio"})
        self.js("(T.ROTA_HA = '/oportunidades', T.irRotaHA(), true)")
        self.assertEqual(self.js("[T.S.ui.tab, T.S.ui.maisTela]"), ["mais", "invest"])
        self.pg.wait_for_selector("#oportunidades")
        self.js("(T.ROTA_HA = '/outra', T.irRotaHA(), true)")
        self.assertEqual(self.js("T.S.ui.maisTela"), "invest", "outro caminho não muda nada")

    def test_menu_mais_fala_das_oportunidades(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais"})
        self.assertEqual(self.linha(".menu-row", "Invest"), "Invest Índices de mercado e oportunidades.")


if __name__ == "__main__":
    unittest.main()
