"""Tela: oportunidades de investimento (Mais › Invest) e o aviso no celular (Mais › Configurações › Opções), num
Chromium de verdade, sem servidor (a prévia, com as taxas de exemplo do oportDemo). Confere as famílias com o alvo ao
lado, as melhores taxas, o "No alvo", o equivalente em CDB, a comparação com os seus investimentos, quanto rende (em
destaque), as ofertas dos bancos cadastrados (só com a IA; a página pronta pelo nome ou a do banco), o Conferir agora, o horário com o Testar ao lado e quem recebe, como no ResolvIA, e o toque no aviso.
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
# o banco com a página de ofertas (na prévia, cada banco com página dá três ofertas inventadas do Banco Sol)
SOL = {"id": "b-sol", "nome": "Banco Sol", "cor": "#FFA23E", "ofertas": PAGINA, "contas": [{"id": "k-sol", "pessoa": "Ana", "cartao": False, "fechamento": 1, "vencimento": 10}]}
OPCOES = {"tab": "mais", "maisTela": "config", "maisAba": "opcoes"}


class TelaOport(TelaMais):
    def abrir_invest(self, sol=False, **aj):
        self.abrir(base(bancos=BANCOS + ([SOL] if sol else []), investimentos=INVS, ajustes=dict({"corrigir": True}, **aj)), ui=INVEST)
        self.pg.wait_for_selector("#oportunidades .op-row")

    def grupo(self, g):
        """[(nome, taxa, o que vem embaixo da taxa, quanto rende perto do seu melhor, no alvo)] de uma família."""
        return self.js("""[...document.querySelectorAll(`#oportunidades .op-grupo[data-grupo="${a}"] .op-row`)].map(r => [
            r.querySelector('.op-t b').textContent, r.querySelector('.op-v b').textContent,
            (r.querySelector('.op-v small') || {}).textContent || '', (r.querySelector('.op-dif') || {}).textContent || '',
            r.classList.contains('passa')])""", g)


class TestCartao(TelaOport):
    def test_as_tres_familias_com_as_melhores_taxas(self):
        self.abrir_invest()
        self.assertEqual(self.texto("#oportunidades h2"), "Oportunidades")
        self.assertEqual(self.textos("#oportunidades .op-grupo-cab > b"), ["Pós-fixado", "Prefixado", "IPCA+"])
        self.assertEqual(self.grupo("pos"), [["Tesouro Selic 2031", "Selic + 0,09%", "101,5% do CDI", "R$ 28 a menos que o seu melhor", False],
                                             ["Tesouro Reserva 2036", "Selic", "100,7% do CDI", "R$ 37 a menos que o seu melhor", False]],
                         "perto do seu CDB de 104% (o de terceiros, de 200%, não conta como seu)")
        self.assertEqual(self.grupo("pre"), [["Tesouro Prefixado 2032", "13,71% ao ano", "", "", False],
                                             ["Tesouro Prefixado 2029", "13,42% ao ano", "", "", False]], "sem prefixado seu: sem comparação")
        self.assertEqual([r[0] for r in self.grupo("ipca")], ["Tesouro IPCA+ 2032", "Tesouro IPCA+ 2040", "Tesouro IPCA+ com Juros Semestrais 2045"])
        self.assertTrue(self.grupo("ipca")[0][3].endswith("a mais que o seu melhor"))
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
        self.abrir_invest(sol=True)
        self.assertEqual(self.texto("#oportunidades .op-todas"), "Ver mais 2")
        self.clicar('#oportunidades [data-a="op-todas"]')
        self.assertEqual(len(self.grupo("pos")), 5)
        self.assertEqual(self.texto("#oportunidades .op-todas"), "Ver menos")

    def test_ofertas_das_paginas_com_o_equivalente_em_cdb(self):
        self.abrir_invest(sol=True, op_cdi=110)
        pos = self.grupo("pos")
        self.assertEqual(pos[0][:3] + pos[0][4:], ["CDB Banco Sol", "118% do CDI", "", True])
        self.assertTrue(pos[0][3].endswith("a mais que o seu melhor"))
        self.assertEqual(pos[1][:3], ["LCA Banco Sol", "94% do CDI", "como CDB de 113,9%"], "isenta: a LCA de 94% vale um CDB de 113,9% (IR de 17,5% até o vencimento)")
        self.assertIn("bancosol.exemplo · vence 06/11/2028", self.linha("#oportunidades .op-row", "CDB Banco Sol"))
        self.assertEqual(self.texto("#oportunidades .op-bancos"), "Ofertas dos seus bancos: Banco Sol (3 ofertas).")
        self.assertEqual(self.texto("#oportunidades .op-sem"), "Sem página de ofertas: Banco Azul, Banco Verde.")
        cx = self.grupo("pos")[2]
        self.assertEqual(cx[:2], ["Caixinha (Banco Sol)", "112% do CDI"])
        self.assertIn("liquidez diária · clientes Sol Mais", self.linha("#oportunidades .op-row", "Caixinha"), "a condição da taxa")

    def test_sem_alvo_vale_o_que_rende_mais_que_os_seus(self):
        self.abrir_invest(sol=True)
        pos = self.grupo("pos")
        self.assertEqual([(r[0], r[4]) for r in pos], [("CDB Banco Sol", True), ("LCA Banco Sol", True), ("Caixinha (Banco Sol)", True)],
                         "acima do seu CDB de 104%")
        self.assertIn("Melhor que os seus", self.linha("#oportunidades .op-row.passa", "CDB Banco Sol"))
        self.assertEqual([r[4] for r in self.grupo("ipca")], [True, True, True], "acima do seu IPCA + 6,20%")
        self.assertEqual([r[4] for r in self.grupo("pre")], [False, False], "sem prefixado seu: nada")
        self.assertIn("Sem alvo, vale o que render mais que os seus.", self.texto("#oportunidades .painel-lead"))

    def test_as_ofertas_vem_dos_bancos(self):
        nubank = {"id": "b-nu", "nome": "Nubank", "cor": "#8A05BE", "contas": [{"id": "k-nu", "pessoa": "Ana", "cartao": False, "fechamento": 1, "vencimento": 10}]}
        self.abrir(base(bancos=[nubank, BANCOS[0]], investimentos=INVS, ajustes={"corrigir": True}), ui=INVEST)
        self.pg.wait_for_selector("#oportunidades .op-row")
        self.assertEqual(self.conta("#op-url, #oportunidades .op-sug, #oportunidades .op-pag"), 0, "sem lista de páginas para pôr à mão")
        self.assertEqual(self.texto("#oportunidades .op-bancos"), "Ofertas dos seus bancos: Nubank (3 ofertas).", "a página pronta do Nubank, pelo nome")
        self.assertEqual(self.texto("#oportunidades .op-sem"), "Sem página de ofertas: Banco Azul.")
        self.assertTrue(self.texto("#oportunidades .painel-lead").startswith("Taxas de hoje do Tesouro Direto e dos seus bancos, perto"))
        # o banco sem página abre o formulário dele, com o campo da página
        self.clicar('#oportunidades .op-sem [data-a="banco"]')
        self.assertEqual(self.folha(), "Editar banco")
        self.assertEqual(self.pg.get_attribute("#b-ofertas", "placeholder"), "https://…")
        self.preencher("#b-ofertas", "não é endereço")
        self.clicar('#folhas [data-a="b-salvar"]')
        self.assertEqual(self.texto("#folhas .campo .msg-erro"), "Use o endereço da página, começando com https://")
        self.preencher("#b-ofertas", "bancoazul.exemplo/cdb")
        self.clicar('#folhas [data-a="b-salvar"]')
        self.esperar()
        self.assertIsNone(self.folha())
        self.assertEqual(self.dados()["bancos"][1]["ofertas"], "https://bancoazul.exemplo/cdb", "o https:// entra sozinho")
        self.pg.wait_for_function("() => (document.querySelector('#oportunidades .op-bancos') || {}).textContent.includes('Banco Azul (3')")
        self.assertEqual(self.texto("#oportunidades .op-bancos"), "Ofertas dos seus bancos: Nubank (3 ofertas), Banco Azul (3 ofertas).")
        self.assertEqual(self.conta("#oportunidades .op-sem"), 0)
        # no Nubank, a página é a pronta
        self.js("(T.abrirBanco('b-nu'), true)")
        self.assertEqual(self.pg.get_attribute("#b-ofertas", "placeholder"), "Automática: nubank.com.br")
        self.voltar()
        self.abrir(base(bancos=[nubank], ajustes={"corrigir": True, "ia": False}), ui={"tab": "mais", "maisTela": "bancos"})
        self.js("(T.abrirBanco('b-nu'), true)")
        self.assertEqual(self.conta("#b-ofertas"), 0, "sem a IA, sem o campo")

    def test_igual_ao_servidor(self):
        import oportunidades as O  # o tela_base põe gerencia/app no caminho
        nomes = ["Nubank", "Nu", "NuBank Ultravioleta", "Banco Inter", "inter", "Mercado Pago", "PagSeguro", "Pag Bank", "Interamericano", "Banco Coral", "Nuvem", ""]
        self.abrir_invest()
        self.assertEqual(self.js("a.map(n => T.paginaPronta(n))", nomes), [O.pagina_pronta(n) for n in nomes])
        d = {"bancos": [{"id": "b1", "nome": "Nubank"}, {"id": "b2", "nome": "Banco Coral", "ofertas": "https://bancocoral.exemplo/cdb"}, {"id": "b3", "nome": "Banco Lua"},
                        {"id": "b4", "nome": "Nu Pagamentos"}, {"id": "b5", "nome": "Inter", "ofertas": "ftp://inter.co"}, {"id": "b6", "nome": " "}]}
        js = self.js("T.paginasDosBancos(a)", d)
        py = O.paginas_dos_bancos(d)
        self.assertEqual((js["paginas"], [b["nome"] for b in js["sem"]]), py)

    def test_quanto_rende_e_o_nivel_no_banco_da_oferta(self):
        bancos = [dict(BANCOS[0]), {"id": "b-sol", "nome": "Banco Sol", "cor": "#FFA23E", "ofertas": PAGINA, "contas": [
            {"id": "k-sol", "pessoa": "Ana", "cartao": False, "fechamento": 1, "vencimento": 10, "meta_nivel": "Black", "meta_valor": 50000}]}]
        self.abrir(base(bancos=bancos, investimentos=INVS, ajustes={"corrigir": True}), ui=INVEST)
        self.pg.wait_for_selector("#oportunidades .op-row")
        self.assertEqual(self.pg.input_value("[data-op-simular]"), "10.000")
        cdb = self.linha("#oportunidades .op-row", "CDB Banco Sol")
        # 118% do CDI de 13,65% = 16,107% ao ano; menos 17,5% de IR = R$ 1.329 em 1 ano; o seu CDB de 104% renderia R$ 1.171
        self.assertEqual(self.js("[...document.querySelectorAll('#oportunidades .op-row')].filter(r => r.textContent.includes('CDB Banco Sol')).map(r => [...r.querySelectorAll('.op-ganho > *')].map(e => [e.textContent, e.className]))[0]"),
                         [["+R$ 1.329", ""], ["em 1 ano com R$ 10 mil", ""], ["R$ 158 a mais que o seu melhor", "op-dif mais"]],
                         "o rendimento em destaque; a diferença para o seu melhor embaixo, em verde quando é a mais")
        self.assertEqual(self.js("(() => { const r = [...document.querySelectorAll('#oportunidades .op-row')].find(r => r.textContent.includes('CDB Banco Sol')); "
                                 "const g = r.querySelector('.op-ganho'), b = g.querySelector('b'); return [Math.round(g.getBoundingClientRect().width) === Math.round(r.getBoundingClientRect().width), "
                                 "getComputedStyle(b).color === getComputedStyle(r.querySelector('.op-dif')).color, getComputedStyle(b).color !== getComputedStyle(g.querySelector('span')).color]; })()"),
                         [True, True, True], "na largura toda da linha, na cor de destaque")
        self.assertEqual(self.js("[...document.querySelectorAll('#oportunidades .op-dif')].map(e => e.textContent.includes('a mais') === e.classList.contains('mais'))"
                                 ".every(Boolean)"), True, "em verde só o que rende a mais")
        self.assertIn("Faltam R$ 50 mil para o Black no Banco Sol", cdb, "a oferta é do banco onde você tem uma meta de nível")
        self.assertNotIn("Faltam", self.linha("#oportunidades .op-row", "Tesouro Prefixado 2032"), "no Tesouro, não")
        self.pg.fill("[data-op-simular]", "50.000")
        self.pg.locator("[data-op-simular]").dispatch_event("change")
        self.esperar()
        self.assertEqual(self.dados()["ajustes"]["op_simular"], 50000)
        self.assertIn("+R$ 6.644 em 1 ano com R$ 50 mil", self.linha("#oportunidades .op-row", "CDB Banco Sol"))
        self.pg.fill("[data-op-simular]", "5")
        self.pg.locator("[data-op-simular]").dispatch_event("change")
        self.assertEqual(self.esperar_aviso("Use um valor"), "Use um valor a partir de R$ 100.")
        self.assertEqual(self.dados()["ajustes"]["op_simular"], 50000)

    def test_com_a_ia_desligada_so_o_tesouro(self):
        self.abrir_invest(sol=True, ia=False)
        self.assertEqual(self.conta("#oportunidades .op-bancos, #oportunidades .op-sem"), 0)
        self.assertNotIn("Banco Sol", self.texto("#oportunidades"))
        self.assertTrue(self.texto("#oportunidades .painel-lead").startswith("Taxas de hoje do Tesouro Direto, perto"))


class TestPaginas(TelaOport):
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
        self.assertIn("O que chegou ao alvo ou, sem alvo, rende mais que os seus.", self.texto("#op-oport"))
        self.assertEqual(self.pg.input_value("#op-dias"), "1")

    def test_horario_quem_recebe_e_testar(self):
        self.abrir(base(bancos=BANCOS, ajustes={"op_aviso": True, "op_para": ["person.ana"], "op_cdi": 120}), ui=OPCOES)
        self.pg.wait_for_selector("#op-oport .quem-p")
        self.pg.fill("#op-dias", "3")
        self.pg.locator("#op-dias").dispatch_event("change")
        self.esperar()
        self.assertEqual(self.dados()["ajustes"]["op_dias"], 3)
        self.assertIn("Ligado: a cada 3 dias, no horário.", self.texto("#op-oport"))
        self.assertEqual(self.texto("#op-oport .op-dias > span"), "dias")
        self.pg.fill("#op-dias", "90")
        self.pg.locator("#op-dias").dispatch_event("change")
        self.assertEqual(self.esperar_aviso("Use de 1"), "Use de 1 a 30 dias.")
        self.assertEqual((self.pg.input_value("#op-dias"), self.dados()["ajustes"]["op_dias"]), ("3", 3))
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
