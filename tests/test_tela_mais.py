"""A tela do GerencIA nas áreas Início, Mais e navegação, testada num Chromium de verdade (sem servidor).

Confere o que a pessoa vê e faz: boas-vindas e exemplo, os cards e avisos do Início com os números batendo com os
dados, Mais (o menu e as telas: bancos, categorias, fixos, Configurações, Sobre), dicas de economia, abas e o que fica guardado,
barra lateral no computador, o Voltar do celular com janelas umas sobre as outras, conflito ao salvar, avisos e
números longos. Os cálculos puros ficam em tests/test_tela.py; a base e os ajudantes, em tests/tela_base.py.
Para andar rápido, as animações do CSS ficam desligadas nestes testes (o comportamento é o mesmo).

Um teste marcado com @unittest.expectedFailure mostra um defeito achado (comentário "BUG"): quando for corrigido,
ele passa a "unexpected success" e o marcador sai.

Dados sempre inventados (Ana, Beto, Carla, Banco Azul, Banco Verde): nunca nomes, bancos ou valores reais.
"""
import json
import os
import re
import unittest

from tests.base import RAIZ
from tests.tela_base import Tela, base, BANCOS


def brl0(v):
    """Como o app mostra um valor sem centavos (R$ 1.234)."""
    return "R$ " + f"{int(v + 0.5):,}".replace(",", ".")


def rende_mes(v, r):
    """O rendimento de um mês de quem rende r ao ano."""
    return max(0.0, v * ((1 + r) ** (1 / 12) - 1))


# ---------------------------------------------------------------------------------------------------------------
# dados de exemplo (inventados)

# o caixa de novembro: entrou 5.000 e saiu 1.200; a luz de outubro atrasou, a internet vence em 3 dias e a academia em 6
LANC = [
    {"id": "l-sal", "tipo": "receita", "descricao": "Salário", "valor": 5000, "data": "2026-11-01", "pago": True, "conta": "k-verde", "categoria": "c-salario"},
    {"id": "l-alug", "tipo": "despesa", "descricao": "Aluguel", "valor": 1200, "data": "2026-11-01", "pago": True, "conta": "k-verde", "categoria": "c-moradia"},
    {"id": "l-luz", "tipo": "despesa", "descricao": "Luz", "valor": 150, "data": "2026-10-30", "pago": False, "categoria": "c-contas"},
    {"id": "l-net", "tipo": "despesa", "descricao": "Internet", "valor": 100, "data": "2026-11-05", "pago": False, "categoria": "c-contas"},
    {"id": "l-acad", "tipo": "despesa", "descricao": "Academia", "valor": 90, "data": "2026-11-08", "pago": False, "categoria": "c-saude"},
]

# valores de hoje (02/11/2026): o valor de hoje é o próprio valor
INV_CDB = {"id": "i-cdb", "nome": "CDB Azul", "banco": "b-azul", "tipo": "cdb", "valor": 10000, "data_valor": "2026-11-02", "indexador": "cdi_pct",
           "taxa": 100, "liquidez": "vencimento", "vencimento": "2027-11-03", "titular": "meu"}
INV_TES = {"id": "i-tes", "nome": "Tesouro Verde", "banco": "b-verde", "tipo": "tesouro", "valor": 4000, "data_valor": "2026-11-02", "indexador": "selic_mais",
           "taxa": 0, "liquidez": "diaria", "titular": "meu"}
INV_CARLA = {"id": "i-carla", "nome": "Poupança da Carla", "banco": "b-verde", "tipo": "poupanca", "valor": 2500, "data_valor": "2026-11-02",
             "indexador": "poupanca", "taxa": 0, "liquidez": "diaria", "titular": "terceiros", "terceiro": "Carla"}
INVS = [INV_CDB, INV_TES, INV_CARLA]
RENDE_MEU = rende_mes(10000, 0.1365) + rende_mes(4000, 0.1375)  # CDI 13,65% e Selic 13,75% (índices da base)

# bens do InventarIA como o servidor entrega (/api/bens), inventados
BENS = {"ok": True, "hoje": 30000, "registrado": 36000, "perde_ano": 4200, "n": 12, "versao": "1.18.0",
        "categorias": [{"id": "eletronicos", "nome": "Eletrônicos", "taxa": 20, "registrado": 16000, "hoje": 12000, "n": 5},
                       {"id": "moveis", "nome": "Móveis", "taxa": 10, "registrado": 20000, "hoje": 18000, "n": 7}],
        "comodos": [{"id": "sala", "nome": "Sala", "hoje": 20000, "n": 8}, {"id": "quarto", "nome": "Quarto", "hoje": 10000, "n": 4}]}

# fixos: salário, aluguel, internet no cartão, IPTU uma vez por ano e uma academia que parou em outubro
FIXOS = [
    {"id": "r-sal", "tipo": "receita", "descricao": "Salário", "valor": 5000, "dia": 5, "inicio": "2026-01", "conta": "k-verde", "categoria": "c-salario"},
    {"id": "r-alug", "tipo": "despesa", "descricao": "Aluguel", "valor": 1200, "dia": 10, "inicio": "2026-01", "conta": "k-verde", "categoria": "c-moradia"},
    {"id": "r-net", "tipo": "despesa", "descricao": "Internet", "valor": 100, "dia": 15, "inicio": "2026-01", "conta": "k-ana", "cartao": True, "categoria": "c-contas"},
    {"id": "r-iptu", "tipo": "despesa", "descricao": "IPTU", "valor": 800, "dia": 1, "inicio": "2026-02", "freq": "anual", "categoria": "c-impostos"},
    {"id": "r-acad", "tipo": "despesa", "descricao": "Academia", "valor": 90, "dia": 3, "inicio": "2025-01", "fim": "2026-10", "categoria": "c-saude"},
]

# uma assinatura com plano anual mais barato e a dica como o servidor entrega (/api/dicas), com o preço já conferido
SPOTIFY = {"id": "r-spot", "tipo": "despesa", "descricao": "Spotify", "valor": 23.9, "dia": 22, "inicio": "2026-01", "conta": "k-ana", "cartao": True,
           "categoria": "c-assinaturas"}
_ASS = {"chave": "r:r-spot", "rid": "r-spot", "origem": "fixo", "servico": "spotify", "nome": "Spotify", "descricao": "Spotify", "valor": 23.9, "freq_anual": False,
        "conta": "k-ana", "cartao": True, "categoria": "c-assinaturas", "dia": 22, "fonte": "https://www.spotify.com/br-pt/premium/", "dominio": "spotify.com",
        "conferido": "2026-10-18", "status": "ok", "texto": "Dá para economizar no plano anual.", "plano": "Premium Individual", "moeda": "BRL",
        "mensal": 23.9, "anual": 239, "pct": 16.7, "economia_ano": 47.8, "preco_anual": 239, "estimado": False}
DICA_SPOTIFY = "anual:r:r-spot"
DICAS = {"dicas": [dict(_ASS, id=DICA_SPOTIFY)], "assinaturas": [_ASS], "conferindo": False,
         "catalogo": ["Nabu Casa", "Claude", "Spotify", "Microsoft 365", "Deezer"], "dolar": None}

# restaurantes: outubro bem acima da média de julho a setembro
RESTAURANTES = [{"id": f"rest{m}", "tipo": "despesa", "descricao": "Restaurante", "valor": v, "data": f"2026-{m:02d}-15", "pago": True, "categoria": "c-restaurantes"}
                for m, v in ((7, 400), (8, 450), (9, 500), (10, 900))]

SEM_ANIMACAO = "*, *::before, *::after { transition: none !important; animation: none !important; }"


# ---------------------------------------------------------------------------------------------------------------
class TelaMais(Tela):
    """A base da tela com ajudantes a mais e sem animações."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pg.add_style_tag(content=SEM_ANIMACAO)
        cls.pg.set_default_timeout(5000)  # um clique que não acha o botão falha logo, sem esperar 30 s

    def abrir(self, d=None, ui=None, bens=None):
        # um pedido de dicas agendado por um teste anterior não entra no meio deste
        self.js("(clearTimeout(T.dicasAgenda), clearTimeout(T.dicasTimer), true)")
        super().abrir(d, ui, bens)

    def esperar_aviso(self, parte, ms=3000):
        """Espera o aviso (toast) com este texto e devolve o texto inteiro."""
        self.pg.wait_for_function("t => { const e = document.getElementById('toast'); return e.classList.contains('on') && e.textContent.includes(t); }",
                                  arg=parte, timeout=ms)
        return self.aviso()

    def guardado(self):
        """O que a tela guardou no aparelho (localStorage): abas, filtros e modos."""
        return self.js("JSON.parse(localStorage.getItem('gerencia.ui') || '{}')")

    def trocar_api(self, nome, corpo_js):
        """Troca uma função da api por uma falsa (JavaScript) até o fim do teste."""
        self.js("(window.__api0 = window.__api0 || {}, (a[0] in window.__api0) || (window.__api0[a[0]] = T.api[a[0]]), "
                "T.api[a[0]] = new Function('return (' + a[1] + ')')(), true)", [nome, corpo_js])
        self.addCleanup(lambda: self.js("(T.api[a] = window.__api0[a], delete window.__api0[a], true)", nome))

    def pares(self, sel):
        """[rótulo, valor] de cada coluna (span + b), pelo texto de verdade (sem as maiúsculas do CSS)."""
        return self.js("[...document.querySelectorAll(a)].map(d => [d.querySelector('span').textContent.trim(), d.querySelector('b').textContent.trim()])", sel)

    def linha(self, sel, contem):
        """O texto do primeiro elemento que contém este texto (como aparece, com os espaços juntados), ou None."""
        return self.js("(e => e ? e.innerText.replace(/\\s+/g, ' ').trim() : null)([...document.querySelectorAll(a[0])].find(e => e.innerText.includes(a[1])))",
                       [sel, contem])

    def rotulo_placar(self):
        return self.js("document.querySelector('.placar-num').getAttribute('aria-label')")

    def visivel(self, sel):
        return self.pg.locator(sel).first.is_visible() if self.conta(sel) else False

    def cortados(self, sel):
        """[(texto, scrollWidth, clientWidth)] dos elementos cujo conteúdo não cabe (número cortado)."""
        return self.js("[...document.querySelectorAll(a)].filter(e => e.scrollWidth > e.clientWidth + 1).map(e => [e.textContent, e.scrollWidth, e.clientWidth])", sel)


# ---------------------------------------------------------------------------------------------------------------
class TestBoasVindasEExemplo(TelaMais):
    def test_sem_dados_mostra_boas_vindas_com_os_caminhos_para_comecar(self):
        self.abrir(base())
        self.assertIn("Vamos começar", self.tela())
        botoes = [t.strip() for t in self.textos(".comeco .btns button")]
        self.assertEqual(botoes, ["Cadastrar salário e gastos fixos", "Cadastrar investimento", "Ler fatura ou print com IA", "Importar backup", "Ver com dados de exemplo"])
        self.assertEqual(self.conta(".placar-cols"), 0, "sem números ainda")

    def test_boas_vindas_sem_o_botao_de_ia_com_a_ia_desligada(self):
        self.abrir(base(ajustes={"ia": False}))
        self.assertFalse(self.visivel('.comeco [data-a="ia"]'), "Ler fatura ou print com IA some com a IA desligada")
        self.assertTrue(self.visivel('.comeco [data-a="novo-inv"]'))

    def test_ver_com_dados_de_exemplo_carrega_e_avisa_que_e_exemplo(self):
        self.abrir(base())
        self.clicar('[data-a="carregar-exemplo"]')
        self.assertEqual(self.esperar_aviso("Exemplo"), "Exemplo carregado")
        d = self.dados()
        self.assertTrue(d["exemplo"])
        self.assertTrue(d["investimentos"] and d["lancamentos"] and d["recorrencias"] and d["bancos"], "investimentos, caixa e bancos de exemplo")
        self.assertIn("Patrimônio", self.js("document.querySelector('.placar-cab').textContent"))
        self.assertIn("Estes valores são de demonstração", self.texto(".exemplo"))
        self.assertTrue(self.visivel('.exemplo [data-a="apagar-exemplo"]'))

    def test_apagar_exemplo_pede_confirmacao_e_volta_ao_comeco(self):
        self.abrir(base())
        self.clicar('[data-a="carregar-exemplo"]')
        self.clicar('[data-a="apagar-exemplo"]')
        self.assertEqual(self.folha(), "Apagar exemplo?")
        self.clicar('.folha-pe [data-a="confirmar"]')
        d = self.dados()
        self.assertEqual((d["exemplo"], d["bancos"], d["investimentos"], d["lancamentos"], d["recorrencias"]), (False, [], [], [], []))
        self.assertEqual(self.esperar_aviso("Exemplo apagado"), "Exemplo apagado")
        self.assertIn("Vamos começar", self.tela())
        self.assertEqual(self.conta(".exemplo"), 0, "sem o aviso de exemplo")

    def test_cancelar_apagar_exemplo_mantem_os_dados(self):
        self.abrir(base())
        self.clicar('[data-a="carregar-exemplo"]')
        n = len(self.dados()["investimentos"])
        self.clicar('[data-a="apagar-exemplo"]')
        self.clicar('.folha-pe [data-a="fechar"]')
        self.assertIsNone(self.folha())
        self.assertEqual(len(self.dados()["investimentos"]), n)
        self.assertTrue(self.dados()["exemplo"])


# ---------------------------------------------------------------------------------------------------------------
class TestInicio(TelaMais):
    def test_so_com_caixa_o_placar_mostra_o_saldo_e_o_mes(self):
        self.abrir(base(bancos=BANCOS, lancamentos=LANC))
        self.assertEqual(self.rotulo_placar(), "Saldo em caixa de R$ 3.800")
        self.assertEqual(self.pares(".placar-cols > div"), [["Entrou", "R$ 5.000"], ["Saiu", "R$ 1.200"], ["Sobrou", "R$ 3.800"]])

    def test_aviso_de_conta_atrasada_com_o_valor(self):
        self.abrir(base(bancos=BANCOS, lancamentos=LANC))
        self.assertEqual(self.linha("#app .op", "atrasada"), "Uma conta atrasada Luz R$ 150")

    def test_aviso_do_que_vence_em_ate_5_dias(self):
        self.abrir(base(bancos=BANCOS, lancamentos=LANC))
        self.assertEqual(self.linha("#app .op", "próximos 5 dias"), "Vence nos próximos 5 dias Internet R$ 100",
                         "a internet vence em 3 dias; a academia, em 6, fica de fora")

    def test_compras_atrasadas_no_cartao_viram_um_aviso_so_da_fatura(self):
        lanc = [{"id": "c1", "tipo": "despesa", "descricao": "Farmácia", "valor": 120, "data": "2026-10-01", "conta": "k-ana", "cartao": True, "pago": False},
                {"id": "c2", "tipo": "despesa", "descricao": "Mercado", "valor": 180, "data": "2026-10-03", "conta": "k-ana", "cartao": True, "pago": False}]
        self.abrir(base(bancos=BANCOS, lancamentos=lanc))
        self.assertEqual(self.linha("#app .op", "atrasada"), "Uma conta atrasada Fatura Banco Azul · Ana R$ 300", "a fatura de 12/10 com as duas compras")

    def test_tocar_no_aviso_de_atrasada_abre_o_caixa_no_a_pagar(self):
        self.abrir(base(bancos=BANCOS, lancamentos=LANC))
        self.pg.locator("#app .op", has_text="atrasada").first.click()
        self.esperar()
        u = self.js("T.S.ui")
        self.assertEqual((u["tab"], u["cxModo"], u["cxFiltro"], u["cxMes"]), ("caixa", "lista", "pendentes", None))

    def test_patrimonio_e_so_o_seu_sem_o_dinheiro_de_terceiros(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS))
        self.assertEqual(self.rotulo_placar(), "Patrimônio de R$ 14.000", "10.000 + 4.000; os 2.500 da Carla ficam de fora")
        self.assertEqual(self.pares(".placar-cols > div"), [["Investimentos", "2"], ["Bancos", "2"], ["Por mês", "+" + brl0(RENDE_MEU)]])

    def test_dinheiro_de_terceiros_por_pessoa(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS))
        card = self.linha("#app .card.flush", "Dinheiro de terceiros")
        self.assertIn("Dinheiro de terceiros R$ 2.500", card)
        self.assertIn("Carla 1 investimento · Banco Verde R$ 2.500", card)

    def test_destaques_batem_com_os_investimentos(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS))
        self.assertIn(brl0(RENDE_MEU), self.linha(".hl-row", "Rende por mês"))
        self.assertEqual(self.linha(".hl-row", "Melhor rendimento"), "Melhor rendimento Tesouro Verde 13,75% Selic")
        self.assertEqual(self.linha(".hl-row", "Maior banco"), "Maior banco Banco Azul 61% R$ 10.000", "10.000 de 16.500")
        self.assertEqual(self.linha(".hl-row", "Vence primeiro"), "Vence primeiro CDB Azul 03/11/2027 R$ 10.000", "a mais de 90 dias: mostra a data")

    def test_card_do_caixa_do_mes_com_saldo_de_hoje_e_do_fim_do_mes(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS, lancamentos=LANC))
        card = self.linha(".cx-card", "Caixa de")
        self.assertTrue(card.startswith("Caixa de novembro"), card)
        self.assertEqual(self.pares(".cx-card .cx-resumo > div"), [["Entrou", "R$ 5.000"], ["Saiu", "R$ 1.200"], ["Sobrou", "R$ 3.800"]])
        self.assertIn("+ R$ 190 a pagar", card, "internet e academia de novembro")
        self.assertIn("Saldo hoje R$ 3.800 · fim do mês R$ 3.460", card, "3.800 menos luz, internet e academia")

    def test_investimento_que_vence_em_breve_avisa(self):
        self.abrir(base(bancos=BANCOS, investimentos=[dict(INV_CDB, vencimento="2026-11-20")]))
        self.assertEqual(self.linha("#app .op", "Vence em"), "Vence em 18 dias CDB Azul · decida para onde vai o dinheiro 18 dias")
        self.assertIn("em 18 dias", self.linha(".hl-row", "Vence primeiro"))

    def test_investimento_vencido_avisa(self):
        self.abrir(base(bancos=BANCOS, investimentos=[dict(INV_CDB, vencimento="2026-10-01")]))
        self.assertEqual(self.linha("#app .op", "venceu"), "Um investimento venceu CDB Azul")

    def test_valor_sem_atualizar_ha_mais_de_2_meses_avisa(self):
        parado = {"id": "din", "nome": "Cofre", "tipo": "dinheiro", "valor": 300, "data_valor": "2026-01-01", "indexador": "parado"}
        self.abrir(base(bancos=BANCOS, investimentos=[dict(INV_CDB, data_valor="2026-08-01"), parado]))
        self.assertIn("CDB Azul está sem atualizar há mais de 2 meses", self.linha("#app .op", "Atualize os valores"),
                      "só o CDB: dinheiro parado não precisa atualizar")

    # (era bug até a 1.24.0: o aviso Índices abria a aba de Mais que estivesse aberta)
    def test_tocar_nos_indices_abre_mais_invest_nos_indices(self):
        self.abrir(base(bancos=BANCOS, investimentos=[INV_CDB]), ui={"maisTela": "bancos"})
        self.assertIn("CDI 13,65% · Selic 13,75% · IPCA 4,5%", self.linha("#app .op", "Índices"))
        self.pg.locator("#app .op", has_text="Índices").first.click()
        self.esperar()
        self.assertEqual(self.js("[T.S.ui.tab, T.S.ui.maisTela]"), ["mais", "invest"])
        self.assertTrue(self.visivel("#indices"), "a seção Índices de mercado (Mais › Invest) na tela")
        self.voltar()
        self.assertEqual((self.js("T.S.ui.tab"), self.texto(".cab h1")), ("inicio", "Início"), "o Voltar volta para o Início, de onde veio")

    def test_bens_do_inventaria_somam_no_patrimonio(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS), bens=BENS)
        self.assertEqual(self.rotulo_placar(), "Patrimônio de R$ 44.000")
        self.assertEqual(self.pares(".placar-cols > div")[:2], [["Investido", "R$ 14.000"], ["Bens", "R$ 30.000"]])
        self.assertEqual(self.linha(".hl-row", "Bens da casa"), "Bens da casa 12 itens no InventarIA R$ 30.000 perdem ≈ R$ 4.200/ano")

    def test_bens_desligados_nao_somam_nem_aparecem(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS, ajustes={"bens": False}), bens=BENS)
        self.assertEqual(self.rotulo_placar(), "Patrimônio de R$ 14.000")
        self.assertIsNone(self.linha(".hl-row", "Bens da casa"))

    def test_esconder_valores_vale_em_todas_as_telas_e_fica_guardado(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS, lancamentos=LANC))
        self.addCleanup(lambda: self.js("(T.S.oculto = false, localStorage.setItem('gerencia.oculto', 'false'), true)"))
        self.clicar('.cab-linha [data-a="olho"]')
        self.assertEqual(self.rotulo_placar(), "Patrimônio de R$ •••••")
        self.assertNotIn("14.000", self.tela())
        self.ir("caixa")
        self.assertIn("R$ •••••", self.tela())
        self.assertNotIn("5.000", self.tela())
        self.assertEqual(self.js("localStorage.getItem('gerencia.oculto')"), "true")


# ---------------------------------------------------------------------------------------------------------------
class TestMaisBancos(TelaMais):
    def abrir_bancos(self, d=None):
        self.abrir(d or base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "bancos"})

    def banco(self, id_):
        return next(b for b in self.dados()["bancos"] if b["id"] == id_)

    def test_lista_os_bancos_com_pessoas_cartoes_e_investimentos(self):
        self.abrir_bancos(base(bancos=BANCOS, investimentos=INVS))
        self.assertEqual(self.js("document.querySelector('.sync').textContent.trim()"), "2 bancos · 3 contas · 2 cartões")
        self.assertEqual(self.linha(".banco-row", "Banco Azul"), "B Banco Azul Ana (cartão) · Beto (cartão) · 1 investimento · R$ 10.000")
        self.assertEqual(self.linha(".banco-row", "Banco Verde"), "B Banco Verde Ana · 2 investimentos · R$ 6.500")

    def test_cadastrar_banco_com_pessoa_e_cartao(self):
        self.abrir_bancos()
        self.clicar('.btn[data-a="banco"]')
        self.assertEqual(self.folha(), "Novo banco")
        self.preencher("#b-nome", "Banco Roxo")
        self.assertEqual(self.pg.input_value('[data-fbc="pessoa"]'), "Ana", "começa com quem está usando o app")
        self.clicar('.folha [data-a="bc-cartao"][data-i="0"]')
        self.preencher('[data-fbc="fechamento"]', "3")
        self.preencher('[data-fbc="vencimento"]', "10")
        self.clicar('[data-a="b-salvar"]')
        self.assertIsNone(self.folha(), "salvou e fechou")
        roxo = next(b for b in self.dados()["bancos"] if b["nome"] == "Banco Roxo")
        self.assertEqual([(c["pessoa"], c["cartao"], c["fechamento"], c["vencimento"]) for c in roxo["contas"]], [("Ana", True, 3, 10)])
        self.assertEqual(self.esperar_aviso("Banco"), "Banco cadastrado")
        self.assertIsNotNone(self.linha(".banco-row", "Banco Roxo"), "já aparece na lista")

    def test_nivel_da_conta_do_cartao_e_o_proximo(self):
        # Banco Azul: Ana tem 10.000 (CDB Azul, dela); o próximo nível pede 25.000
        self.abrir_bancos(base(bancos=BANCOS, investimentos=INVS))
        self.clicar('.banco-row[data-id="b-azul"]')
        self.assertEqual(self.texto('.folha .nivel-meta[data-meta="0"]'), "Você tem R$ 10.000 investidos aqui.")
        self.preencher('[data-fbc="nivel"][data-i="0"]', "One")
        self.preencher('[data-fbc="cartao_nivel"][data-i="0"]', "Gold")
        self.preencher('[data-fbc="meta_nivel"][data-i="0"]', "Black")
        self.preencher('[data-fbc="meta_valor"][data-i="0"]', "25.000")
        self.assertEqual(self.texto('.folha .nivel-meta[data-meta="0"]'), "Você tem R$ 10.000 aqui; o Black pede R$ 25.000. Faltam R$ 15.000.", "muda enquanto digita")
        self.clicar('[data-a="b-salvar"]')
        c = self.banco("b-azul")["contas"][0]
        self.assertEqual({k: c.get(k) for k in ("nivel", "cartao_nivel", "meta_nivel", "meta_valor")},
                         {"nivel": "One", "cartao_nivel": "Gold", "meta_nivel": "Black", "meta_valor": 25000})
        self.assertNotIn("nivel", self.banco("b-azul")["contas"][1], "o vazio não é gravado")
        self.assertEqual(self.linha(".banco-row", "Banco Azul"),
                         "B Banco Azul Ana (One, cartão Gold) · faltam R$ 15 mil para Black · Beto (cartão) · 1 investimento · R$ 10.000")

    def test_meta_de_um_terceiro_conta_os_investimentos_dele(self):
        bancos = [{"id": "b-verde", "nome": "Banco Verde", "cor": "#4CD3A5", "contas": [
            {"id": "k-verde", "pessoa": "Ana", "cartao": False, "fechamento": 1, "vencimento": 10, "meta_nivel": "Prime", "meta_valor": 3000},
            {"id": "k-carla", "pessoa": "Carla", "cartao": False, "fechamento": 1, "vencimento": 10, "meta_nivel": "Prime", "meta_valor": 3000}]}]
        self.abrir_bancos(base(bancos=bancos, investimentos=INVS))
        self.assertEqual(self.linha(".banco-row", "Banco Verde"),
                         "B Banco Verde Ana · já dá para Prime · Carla · faltam R$ 500 para Prime · 2 investimentos · R$ 6.500",
                         "Ana: o Tesouro Verde (4.000, dela); Carla: a poupança dela (2.500)")

    def test_banco_sem_nome_nao_salva(self):
        self.abrir_bancos()
        self.clicar('.btn[data-a="banco"]')
        self.clicar('[data-a="b-salvar"]')
        self.assertEqual(self.folha(), "Novo banco", "a janela continua aberta")
        self.assertEqual(self.texto(".folha .msg-erro"), "Dê um nome ao banco.")
        self.assertEqual(len(self.dados()["bancos"]), 2)

    def test_banco_com_nome_repetido_nao_salva(self):
        self.abrir_bancos()
        self.clicar('.btn[data-a="banco"]')
        self.preencher("#b-nome", "banco azul")
        self.clicar('[data-a="b-salvar"]')
        self.assertEqual(self.texto(".folha .msg-erro"), "Já existe um banco com esse nome.", "sem diferença de maiúsculas")
        self.assertEqual(len(self.dados()["bancos"]), 2)

    def test_dia_do_cartao_so_aceita_numeros_e_fica_dentro_do_mes(self):
        self.abrir_bancos()
        self.clicar('[data-a="banco"][data-id="b-verde"]')
        self.clicar('.folha [data-a="bc-cartao"][data-i="0"]')
        self.digitar('[data-fbc="fechamento"]', "4x5")
        self.assertEqual(self.pg.input_value('[data-fbc="fechamento"]'), "45", "letras não entram")
        self.digitar('[data-fbc="vencimento"]', "12")
        self.clicar('[data-a="b-salvar"]')
        c = self.banco("b-verde")["contas"][0]
        self.assertEqual((c["cartao"], c["fechamento"], c["vencimento"]), (True, 31, 12), "dia 45 vira o último dia possível (31)")

    def test_editar_banco_troca_a_cor_e_adiciona_pessoa(self):
        self.abrir_bancos()
        self.clicar('[data-a="banco"][data-id="b-verde"]')
        self.assertEqual(self.folha(), "Editar banco")
        self.clicar('.folha [data-a="b-cor"][data-v="#FF77A8"]')
        self.clicar('.folha [data-a="bc-add"]')
        self.preencher('[data-fbc="pessoa"][data-i="1"]', "Carla")
        self.clicar('[data-a="b-salvar"]')
        verde = self.banco("b-verde")
        self.assertEqual((verde["cor"], [c["pessoa"] for c in verde["contas"]]), ("#FF77A8", ["Ana", "Carla"]))
        self.assertEqual(self.esperar_aviso("Banco"), "Banco salvo")
        self.assertEqual(self.js("document.querySelector('[data-a=\"banco\"][data-id=\"b-verde\"] .ini').style.getPropertyValue('--c')"), "#FF77A8",
                         "a cor nova na lista")

    def test_excluir_banco_pede_confirmacao_e_solta_investimentos_e_lancamentos(self):
        lanc = [{"id": "c1", "tipo": "despesa", "descricao": "Farmácia", "valor": 120, "data": "2026-10-01", "conta": "k-ana", "cartao": True, "pago": True}]
        self.abrir_bancos(base(bancos=BANCOS, investimentos=[INV_CDB], lancamentos=lanc))
        self.clicar('[data-a="banco"][data-id="b-azul"]')
        self.clicar('.folha [data-a="b-excluir"]')
        self.assertEqual(self.folha(), "Excluir banco?")
        self.assertIn("1 investimento fica sem banco.", self.folha_texto())
        self.clicar('.folha-pe [data-a="confirmar"]')
        d = self.dados()
        self.assertEqual([b["nome"] for b in d["bancos"]], ["Banco Verde"])
        self.assertEqual(d["investimentos"][0]["banco"], "")
        self.assertEqual((d["lancamentos"][0]["conta"], d["lancamentos"][0]["cartao"]), ("", False), "a compra perde a conta e o cartão que sumiram")
        self.assertEqual(self.esperar_aviso("Banco"), "Banco excluído")

    # BUG: a confirmação "Excluir banco?" é aberta de dentro de "Editar banco", mas o Cancelar fecha tudo em vez de voltar
    # para o banco (a regra do AGENTS.md: uma janela aberta de dentro de outra volta para ela no Voltar, no X e no Cancelar).
    # Igual nas outras confirmações abertas de uma janela (Apagar categoria?, Restaurar esta versão?, Apagar lançamento?).
    def test_cancelar_a_exclusao_volta_para_editar_banco_sem_apagar(self):
        self.abrir_bancos()
        self.clicar('[data-a="banco"][data-id="b-azul"]')
        self.clicar('.folha [data-a="b-excluir"]')
        self.clicar('.folha-pe [data-a="fechar"]')
        self.assertEqual(len(self.dados()["bancos"]), 2, "nada apagado")
        self.assertEqual(self.folha(), "Editar banco")


# ---------------------------------------------------------------------------------------------------------------
class TestMaisCaixa(TelaMais):
    def abrir_caixa(self, d):
        self.abrir(d, ui={"tab": "mais", "maisTela": "caixa"})

    def test_nova_categoria_de_gasto_com_cor(self):
        self.abrir_caixa(base())
        self.clicar('[data-a="categoria-nova"][data-v="despesa"]')
        self.assertEqual(self.folha(), "Nova categoria")
        self.assertEqual(self.texto('.folha [data-a="cat-tipo"].on'), "Gasto", "pelo botão de Gastos, já é de gasto")
        self.preencher("#cat-nome", "Viagens")
        self.clicar('.folha [data-a="cat-cor"][data-v="#E04B8A"]')
        self.clicar('[data-a="cat-salvar"]')
        self.assertIsNone(self.folha())
        nova = self.dados()["categorias"][-1]
        self.assertEqual((nova["nome"], nova["tipo"], nova["cor"]), ("Viagens", "despesa", "#E04B8A"))
        self.assertEqual(self.esperar_aviso("Categoria"), "Categoria criada")
        self.assertEqual(self.pg.locator('#categorias [data-a="categoria"]', has_text="Viagens").count(), 1)

    def test_categoria_sem_nome_nao_salva(self):
        self.abrir_caixa(base())
        n = len(self.dados()["categorias"])
        self.clicar('[data-a="categoria-nova"][data-v="receita"]')
        self.clicar('[data-a="cat-salvar"]')
        self.assertEqual(self.texto(".folha .msg-erro"), "Dê um nome.")
        self.assertEqual(len(self.dados()["categorias"]), n)

    def test_editar_categoria_mostra_quantos_usam_e_troca_nome_e_cor(self):
        lanc = [{"id": "m1", "tipo": "despesa", "descricao": "Feira", "valor": 80, "data": "2026-11-01", "pago": True, "categoria": "c-mercado"}]
        rec = [{"id": "r-m", "tipo": "despesa", "descricao": "Cesta", "valor": 200, "dia": 3, "inicio": "2026-01", "categoria": "c-mercado"}]
        self.abrir_caixa(base(lancamentos=lanc, recorrencias=rec))
        self.clicar('[data-a="categoria"][data-id="c-mercado"]')
        self.assertEqual(self.folha(), "Editar categoria")
        self.assertIn("2 lançamentos usam esta categoria.", self.folha_texto())
        self.preencher("#cat-nome", "Supermercado")
        self.clicar('.folha [data-a="cat-cor"][data-v="#F2C14E"]')
        self.clicar('[data-a="cat-salvar"]')
        c = next(x for x in self.dados()["categorias"] if x["id"] == "c-mercado")
        self.assertEqual((c["nome"], c["cor"]), ("Supermercado", "#F2C14E"))
        self.assertEqual(self.esperar_aviso("Categoria"), "Categoria salva")

    def test_apagar_categoria_deixa_os_lancamentos_sem_categoria(self):
        lanc = [{"id": "m1", "tipo": "despesa", "descricao": "Feira", "valor": 80, "data": "2026-11-01", "pago": True, "categoria": "c-mercado"},
                {"id": "o1", "tipo": "despesa", "descricao": "Cinema", "valor": 40, "data": "2026-11-01", "pago": True, "categoria": "c-lazer"}]
        rec = [{"id": "r-m", "tipo": "despesa", "descricao": "Cesta", "valor": 200, "dia": 3, "inicio": "2026-01", "categoria": "c-mercado"}]
        self.abrir_caixa(base(lancamentos=lanc, recorrencias=rec))
        self.clicar('[data-a="categoria"][data-id="c-mercado"]')
        self.clicar('.folha [data-a="cat-excluir"]')
        self.assertEqual(self.folha(), "Apagar categoria?")
        self.assertIn("Os lançamentos dela ficam sem categoria.", self.folha_texto())
        self.clicar('.folha-pe [data-a="confirmar"]')
        d = self.dados()
        self.assertNotIn("c-mercado", [c["id"] for c in d["categorias"]])
        self.assertEqual([l["categoria"] for l in d["lancamentos"]], ["", "c-lazer"], "só os dela ficam sem categoria")
        self.assertEqual(d["recorrencias"][0]["categoria"], "", "o fixo também")
        self.assertEqual(self.esperar_aviso("Categoria"), "Categoria apagada")

    def test_fixos_separados_com_o_total_por_mes_e_sem_os_parados(self):
        self.abrir_caixa(base(bancos=BANCOS, recorrencias=FIXOS))
        self.assertEqual(self.js("document.querySelector('#fixos .mais-aside').textContent"), "R$ 3.700 por mês", "5.000 menos 1.300 de gastos mensais")
        self.assertEqual(self.js("[...document.querySelectorAll('#fixos h3')].map(h => h.textContent)"), ["Recebimentos · R$ 5.000", "Gastos · R$ 1.300", "Uma vez por ano"])
        self.assertIn("Todo dia 15 · Banco Azul · Ana · cartão", self.linha("#fixos .banco-row", "Internet"))
        self.assertIn("Todo ano, 1 de fevereiro", self.linha("#fixos .banco-row", "IPTU"))
        self.assertIsNone(self.linha("#fixos .banco-row", "Academia"), "parou em outubro: sai da lista")

    def test_tocar_no_fixo_abre_o_do_proximo_mes(self):
        self.abrir_caixa(base(bancos=BANCOS, recorrencias=FIXOS))
        self.clicar('#fixos [data-a="fixo"][data-id="r-alug"]')
        self.assertEqual(self.folha(), "Despesa")
        self.assertEqual(self.js("[T.LF.competencia, T.LF.data, T.LF.valor]"), ["2026-12", "2026-12-10", 1200])
        self.assertEqual([t.strip() for t in self.textos(".folha-pe .btn")], ["Só este mês", "Todos os meses"])


# ---------------------------------------------------------------------------------------------------------------
class TestIntegracoes(TelaMais):
    def abrir_int(self, d=None, bens=None):
        self.abrir(d or base(bancos=BANCOS, investimentos=[INV_CDB]), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"}, bens=bens)

    def test_desligar_usar_ia_some_com_os_botoes_de_ia(self):
        self.abrir_int()
        self.clicar('#ia [data-a="ajuste"][data-k="ia"]')
        self.assertFalse(self.dados()["ajustes"]["ia"])
        self.assertEqual(self.js("document.querySelector('.sync').textContent.trim()"), "IA desligada")
        self.assertIn("Desligado: os botões de IA somem em todos os aparelhos.", self.texto("#ia"))
        self.assertEqual((self.conta("#uso-ia"), self.conta("#ia-ent")), (0, 0), "somem o Uso da IA e a escolha da IA")
        self.ir("caixa")
        self.clicar('#nav [data-a="novo"]')
        self.assertEqual(self.folha(), "Nova despesa")
        self.assertEqual(self.conta(".imp-tile"), 0, "sem Colar mensagem, Fatura e Digitalizar")
        self.clicar('.folha-cab [data-a="fechar"]')
        self.ir("inicio")
        self.clicar('#nav [data-a="novo"]')
        self.assertFalse(self.visivel('.escolhas [data-a="ia"]'), "Ler com IA some do Adicionar")

    # ---- Senhas dos PDFs (as senhas ficam no servidor; a tela só vê o nome e o fim escondido)
    def senhas(self):
        return self.js("[...document.querySelectorAll('#senhas-pdf .senha-l')].map(l => [l.querySelector('b').textContent, l.querySelector('small').textContent])")

    def janela_fechada(self):
        """Espera a janela fechar e o Voltar que ela deu no histórico chegar (antes dele, uma janela nova fecharia junto)."""
        self.pg.wait_for_function("() => !window.GERENCIA_TESTE.FOLHA && !(history.state && history.state.g)")
        self.esperar()

    def nova_senha(self, nome, senha):
        self.clicar('#senhas-pdf [data-a="senha-nova"]')
        self.preencher("#sn-nome", nome)
        self.preencher("#sn-senha", senha)
        self.clicar('#folhas [data-a="senha-salvar"]')
        self.janela_fechada()

    def test_senhas_dos_pdfs_comeca_vazio_e_some_sem_ia(self):
        self.abrir_int()
        self.pg.wait_for_selector("#senhas-pdf .nota")
        self.assertEqual(self.texto("#senhas-pdf h2"), "Senhas dos PDFs")
        self.assertEqual(self.texto("#senhas-pdf .nota"), "Nenhuma senha cadastrada.")
        self.assertEqual(self.conta('#senhas-pdf [data-a="senha-nova"]'), 1)
        self.abrir(base(bancos=BANCOS, ajustes={"ia": False}), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"})
        self.assertEqual(self.conta("#senhas-pdf"), 0, "sem a IA, as senhas não servem para nada")

    def test_cadastrar_senha_mostra_so_o_fim(self):
        self.abrir_int()
        self.clicar('#senhas-pdf [data-a="senha-nova"]')
        self.assertEqual(self.folha(), "Nova senha")
        self.pg.wait_for_function("document.activeElement && document.activeElement.id === 'sn-nome'")
        self.preencher("#sn-nome", "CPF da Ana")
        self.preencher("#sn-senha", "12345")
        self.clicar('#folhas [data-a="senha-salvar"]')
        self.janela_fechada()
        self.assertEqual(self.esperar_aviso("Senha guardada"), "Senha guardada")
        self.assertEqual(self.senhas(), [["CPF da Ana", "••••45"]])
        self.assertNotIn("12345", self.js("document.body.innerHTML"), "a senha nunca vai para a tela")
        self.nova_senha("Beto", "987")
        self.assertEqual(self.senhas(), [["CPF da Ana", "••••45"], ["Beto", "••••"]], "curta: nada à mostra")
        self.assertEqual(self.cortados("#senhas-pdf .senha-l b"), [])

    def test_sem_senha_nao_salva_e_o_aviso_sai_ao_digitar(self):
        self.abrir_int()
        self.clicar('#senhas-pdf [data-a="senha-nova"]')
        self.preencher("#sn-nome", "CPF da Ana")
        self.clicar('#folhas [data-a="senha-salvar"]')
        self.assertEqual(self.texto("#folhas .msg-erro"), "Digite a senha.")
        self.assertEqual(self.folha(), "Nova senha", "continua aberta")
        self.assertEqual(self.pg.input_value("#sn-nome"), "CPF da Ana", "o nome não se perde")
        self.digitar("#sn-senha", "1")
        self.assertEqual(self.conta("#folhas .msg-erro"), 0, "ao digitar, o aviso sai")
        self.assertEqual(self.js("document.activeElement.id"), "sn-senha", "sem perder o cursor")
        self.assertEqual(self.senhas(), [])

    def test_erro_do_servidor_aparece_na_janela(self):
        self.abrir_int()
        self.trocar_api("senhaNova", "async () => { throw new Error('Já são 20 senhas. Apague uma antes.'); }")
        self.clicar('#senhas-pdf [data-a="senha-nova"]')
        self.preencher("#sn-senha", "12345")
        self.clicar('#folhas [data-a="senha-salvar"]')
        self.pg.wait_for_selector("#folhas .msg-erro")
        self.assertEqual(self.texto("#folhas .msg-erro"), "Já são 20 senhas. Apague uma antes.")

    def test_apagar_senha(self):
        self.abrir_int()
        self.nova_senha("CPF da Ana", "12345")
        self.nova_senha("Beto", "98765")
        self.clicar('#senhas-pdf [data-a="senha-apagar"]', 1)
        self.esperar_aviso("Senha apagada")
        self.assertEqual(self.senhas(), [["CPF da Ana", "••••45"]])
        self.assertEqual(self.js("document.querySelector('#senhas-pdf [data-a=\"senha-apagar\"]').getAttribute('aria-label')"), "Apagar a senha CPF da Ana")

    def test_voltar_do_celular_fecha_a_nova_senha_e_fica_nas_integracoes(self):
        self.abrir_int()
        self.clicar('#senhas-pdf [data-a="senha-nova"]')
        self.preencher("#sn-senha", "12345")
        self.voltar()
        self.assertEqual(self.niveis(), 0, "fecha a janela")
        self.assertEqual((self.js("T.S.ui.maisTela"), self.js("T.S.ui.maisAba")), ("config", "integracoes"), "continua nas Integrações")
        self.assertEqual(self.senhas(), [], "sem salvar")

    # ---- CorrerIA (WhatsApp, Claude e Gemini leem e gravam pelas ferramentas)
    def test_correria_comeca_desligado_e_mostra_o_ultimo_uso(self):
        self.abrir_int()
        self.assertEqual(self.texto("#correria h2"), "CorrerIA")
        self.assertIn("Desligado.", self.texto("#correria"))
        self.assertEqual(self.conta("#correria .status"), 0)
        self.clicar('#correria [data-a="ajuste"][data-k="correria"]')
        self.assertTrue(self.dados()["ajustes"]["correria"])
        self.assertIn("Ligado: pelo WhatsApp, o Claude e o Gemini leem e mudam as finanças.", self.texto("#correria"))
        self.assertEqual(self.texto("#correria .status"), "Nenhum uso ainda. Conecte no app CorrerIA.")
        self.js("(T.S.correriaUltimo = { app: 'CorrerIA', em: new Date(Date.now() - 60000).toISOString() }, T.render(), true)")
        self.assertRegex(self.texto("#correria .status"), r"^CorrerIA perguntou hoje às \d\d:\d\d\.$")
        self.assertFalse(self.js("document.querySelector('#correria .status').classList.contains('manual')"))
        self.js("(T.S.correriaUso = { app: 'Claude', nome: 'lancar', em: new Date().toISOString() }, T.render(), true)")
        self.assertRegex(self.texto("#correria .status"), r"^Claude usou hoje às \d\d:\d\d\.$", "o mais recente")

    def test_correria_sem_a_ia_continua(self):
        self.abrir(base(bancos=BANCOS, ajustes={"ia": False, "correria": True}), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"})
        self.assertEqual(self.conta("#correria"), 1, "as ferramentas não precisam da IA daqui")
        self.assertEqual(self.textos("#correria .status")[-1], "Fotos e PDFs pelo WhatsApp precisam da IA ligada.")

    def test_falar_so_aparece_com_a_ia_ligada(self):
        self.abrir(base(bancos=BANCOS, investimentos=[INV_CDB]))
        self.addCleanup(lambda: self.js("(T.S.voz = null, true)"))
        self.js("(T.S.voz = { pronta: true, nome: 'Fala de teste', opcoes: [] }, T.render(), true)")
        self.assertGreater(self.conta('.cab [data-a="falar"]'), 0, "o microfone no alto")
        self.abrir(base(bancos=BANCOS, investimentos=[INV_CDB], ajustes={"ia": False}))
        self.assertEqual(self.conta('[data-a="falar"]'), 0)

    def test_uso_da_ia_com_hoje_7_dias_e_o_mes(self):
        self.js("(T.S.usoSel = null, true)")
        self.abrir_int()
        self.pg.wait_for_selector("#uso-ia .uso-tile")
        tiles = self.js("[...document.querySelectorAll('#uso-ia .uso-tile')].map(t => [t.querySelector('.uk').textContent, t.querySelector('.v').textContent])")
        self.assertEqual(tiles, [["Hoje", "5"], ["7 dias", "16"], ["Este mês", "38"]])
        self.assertEqual(self.conta("#uso-ia .uso-bar"), 7, "uma barra por dia")
        self.assertEqual(self.js("document.querySelector('#uso-ia .uso-cap').textContent"), "Hoje: 5 chamadas, 1 sem cota.")
        self.clicar("#uso-ia .uso-bar", 3)
        self.assertEqual(self.js("document.querySelector('#uso-ia .uso-cap').textContent"), "Sex, 30/10: 2 chamadas, 1 com erro.", "tocar num dia mostra o dele")

    def test_ligar_os_sensores(self):
        self.abrir_int()
        self.assertIn("Desligado: nenhum sensor no Home Assistant.", self.texto("#sensores"))
        self.clicar('#sensores [data-a="ajuste"][data-k="sensores"]')
        self.assertTrue(self.dados()["ajustes"]["sensores"])
        self.assertIn("Ligado: sensor.gerencia_patrimonio", self.texto("#sensores"))

    # (era bug até a 1.28.0: desligados, a nota do sensor de IA aparecia; ligados, listavam _ia_hoje e _bens mesmo sem a IA e sem o InventarIA)
    def test_sensores_so_falam_dos_que_o_app_cria(self):
        sens = {"corrigir": True, "sensores": True}
        self.abrir_int()
        self.assertEqual(self.conta("#sensores .nota"), 0, "desligados: sem a nota do sensor de IA")
        self.clicar('#sensores [data-a="ajuste"][data-k="sensores"]')
        t = self.texto("#sensores")
        self.assertIn("_saidas_mes e _ia_hoje. Atualizam", t, "sem o InventarIA, sem o sensor dos bens")
        self.assertNotIn("_bens", t)
        self.assertEqual(self.texto("#sensores .nota"), "sensor.gerencia_ia_hoje: chamadas de IA de hoje, com erros, cota e tokens.")
        self.abrir_int(base(bancos=BANCOS, investimentos=[INV_CDB], ajustes=sens), bens=BENS)
        self.assertIn("_saidas_mes, _ia_hoje e _bens. Atualizam", self.texto("#sensores"), "com o InventarIA, o dos bens")
        self.abrir_int(base(bancos=BANCOS, investimentos=[INV_CDB], ajustes=dict(sens, ia=False)), bens=BENS)
        t = self.texto("#sensores")
        self.assertIn("_saidas_mes e _bens. Atualizam", t, "com a IA desligada, sem o sensor da IA")
        self.assertNotIn("_ia_hoje", t)
        self.assertEqual(self.conta("#sensores .nota"), 0)

    # (era bug até a 1.28.0: o quadro mandava para Mais › Invest, que não tinha as categorias do InventarIA)
    def test_bens_sem_item_com_valor_nao_manda_para_mais_invest(self):
        vazio = {"ok": True, "hoje": 0, "registrado": 0, "perde_ano": 0, "n": 0, "categorias": [], "comodos": []}
        self.abrir_int(bens=vazio)
        t = self.texto("#bens")
        self.assertIn("Ligado: R$ 0 em 0 itens.", t)
        self.assertNotIn("Mais › Invest", t)
        self.ir_mais("invest")
        self.assertEqual(self.conta("#perda-bens"), 0, "não há o quadro Valor dos bens por ano")
        self.abrir_int(bens=BENS)
        self.assertIn("Quanto cada categoria perde ou valoriza por ano fica em Mais › Invest.", self.texto("#bens"))
        self.ir_mais("invest")
        self.assertEqual(self.conta("#perda-bens"), 1)

    def test_contas_no_cronologia_mostra_quando_foi_usada(self):
        self.abrir_int()
        self.addCleanup(lambda: self.js("(T.S.integracaoUltimo = null, true)"))
        self.assertIn("Nenhum app conectou ainda.", self.texto("#outros-apps"))
        self.js("(T.S.integracaoUltimo = { app: 'CronologIA', em: '2026-11-02T09:15:00-03:00' }, T.render(), true)")
        self.assertIn("CronologIA usou hoje às 09:15.", self.texto("#outros-apps"))

    def test_desligar_o_cronologia_esconde_o_estado_da_ligacao(self):
        self.abrir_int()
        self.clicar('#outros-apps [data-a="ajuste"][data-k="integracao"]')
        self.assertFalse(self.dados()["ajustes"]["integracao"])
        t = self.texto("#outros-apps")
        self.assertIn("Desligado: o CronologIA não vê as contas do GerencIA.", t)
        self.assertNotIn("Nenhum app conectou ainda.", t)

    def test_bens_do_inventaria_ligado_mostra_o_total_e_a_perda_em_mais_invest(self):
        self.abrir_int(bens=BENS)
        self.assertIn("Ligado: R$ 30.000 em 12 itens.", self.texto("#bens"))
        self.assertTrue(self.visivel('#bens [data-a="bens-atualizar"]'))
        self.ir_mais("invest")
        self.assertEqual(self.js("[...document.querySelectorAll('#perda-bens .bens-tx input')].map(i => [i.dataset.bensTaxa, i.value])"),
                         [["moveis", "10"], ["eletronicos", "20"]], "a perda por ano de cada categoria, da que vale mais para a que vale menos")

    def test_bens_desligado_some_da_carteira_e_da_perda_de_valor(self):
        self.abrir_int(base(bancos=BANCOS, investimentos=[INV_CDB], ajustes={"bens": False}), bens=BENS)
        self.assertIn("Desligado: o patrimônio fica só com os investimentos.", self.texto("#bens"))
        self.assertEqual(self.conta('#bens [data-a="bens-atualizar"]'), 0)
        self.ir_mais("invest")
        self.assertEqual(self.conta("#perda-bens"), 0, "sem bens, sem a tabela de perda de valor")
        self.ir("investimentos")
        self.assertEqual(self.conta(".inv-ro"), 0, "sem o cartão Bens da casa na Carteira")

    def test_inventaria_fora_do_ar_oferece_tentar_de_novo(self):
        self.abrir_int(bens={"ok": False, "motivo": "O InventarIA não respondeu."})
        self.assertIn("O InventarIA não respondeu.", self.texto("#bens"))
        self.assertEqual(self.texto('#bens [data-a="bens-atualizar"]').strip(), "Tentar de novo")


# ---------------------------------------------------------------------------------------------------------------
class TestAparenciaEDados(TelaMais):
    def test_tema_claro_e_escuro(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "aparencia"})
        self.clicar('[data-a="tema"][data-v="claro"]')
        self.assertEqual((self.js("document.documentElement.dataset.theme"), self.dados()["ajustes"]["tema"]), ("light", "claro"))
        self.assertEqual(self.js("document.querySelector('[data-a=\"tema\"][data-v=\"claro\"]').getAttribute('aria-checked')"), "true")
        self.clicar('[data-a="tema"][data-v="escuro"]')
        self.assertEqual((self.js("document.documentElement.dataset.theme"), self.dados()["ajustes"]["tema"]), ("dark", "escuro"))

    def test_tema_automatico_segue_o_sistema(self):
        self.abrir(base(ajustes={"tema": "escuro"}), ui={"tab": "mais", "maisTela": "config", "maisAba": "aparencia"})
        self.addCleanup(lambda: self.pg.emulate_media(color_scheme="null"))
        fundo = lambda: self.js("getComputedStyle(document.body).backgroundColor")
        self.pg.emulate_media(color_scheme="light")
        escuro_fixo = fundo()
        self.clicar('[data-a="tema"][data-v="auto"]')
        self.assertEqual(self.dados()["ajustes"]["tema"], "auto")
        claro = fundo()
        self.pg.emulate_media(color_scheme="dark")
        self.esperar()
        escuro = fundo()
        self.assertNotEqual(claro, escuro, "o fundo muda com o tema do sistema")
        self.assertEqual(escuro, escuro_fixo, "no escuro do sistema, igual ao tema Escuro")

    # ---- Cor do app e Cor do dia (o relógio parado em 02/11/2026: a cor do dia é o Laranja)
    def acento(self):
        return self.js("document.documentElement.style.getPropertyValue('--accent')")

    def marcada(self):
        """As etiquetas de cor marcadas (o nome)."""
        return self.js("[...document.querySelectorAll('#cor .tsw[aria-checked=\"true\"]')].map(b => b.textContent.trim())")

    def chave_cor_dia(self):
        return self.js("document.querySelector('#cor [data-a=\"ajuste\"][data-k=\"cor_dia\"]').getAttribute('aria-checked')")

    def test_cor_do_dia_ligada_por_padrao(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "aparencia"})
        self.assertEqual(self.linha("#cor .linha-sw", "Cor do dia"), "Cor do dia Muda a cor do app todo dia.")
        self.assertEqual(self.chave_cor_dia(), "true")
        self.assertEqual(self.acento(), "#FFA23E", "02/11/2026: Laranja, no app todo")
        self.assertEqual(self.marcada(), ["Laranja"], "a cor do dia é a marcada")

    def test_quem_ja_tinha_escolhido_uma_cor_tambem_fica_com_a_do_dia(self):
        self.abrir(base(ajustes={"cor": "#8BD45F"}), ui={"tab": "mais", "maisTela": "config", "maisAba": "aparencia"})
        self.assertEqual((self.chave_cor_dia(), self.acento(), self.marcada()), ("true", "#FFA23E", ["Laranja"]))

    def test_cor_do_dia_muda_todo_dia_pela_paleta(self):
        self.abrir(base())
        dias = {"2026-11-02": "#FFA23E", "2026-11-03": "#F2C14E", "2026-11-10": "#FF77A9", "2026-11-11": "#FF5A4F"}
        self.assertEqual({d: self.js("T.corDoDia(T.pData(a))", d) for d in dias}, dias, "Laranja, Ouro; Rosa e de volta ao Vermelho")
        self.assertNotIn("Grafite", [n for n, _ in self.js("T.CORES_DIA")], "sem as neutras")

    def test_cor_do_app(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "aparencia"})
        self.clicar('[data-a="cor"][data-v="#8BD45F"]')
        self.assertEqual((self.dados()["ajustes"]["cor"], self.dados()["ajustes"]["cor_dia"]), ("#8BD45F", False), "escolher uma cor desliga a Cor do dia")
        self.assertEqual(self.acento(), "#8BD45F", "a cor vale no app todo")
        self.assertEqual(self.marcada(), ["Verde"])
        self.assertEqual(self.chave_cor_dia(), "false")

    def test_escolher_a_propria_cor_do_dia_tambem_desliga(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "aparencia"})
        self.clicar('[data-a="cor"][data-v="#FFA23E"]')
        self.assertEqual((self.dados()["ajustes"]["cor"], self.dados()["ajustes"]["cor_dia"]), ("#FFA23E", False))
        self.assertEqual((self.chave_cor_dia(), self.acento()), ("false", "#FFA23E"), "fica com ela, mesmo amanhã")

    def test_ligar_a_cor_do_dia_volta_para_ela_e_desligar_volta_para_a_escolhida(self):
        self.abrir(base(ajustes={"cor": "#8BD45F", "cor_dia": False}), ui={"tab": "mais", "maisTela": "config", "maisAba": "aparencia"})
        self.assertEqual((self.chave_cor_dia(), self.acento(), self.marcada()), ("false", "#8BD45F", ["Verde"]))
        self.clicar('#cor [data-a="ajuste"][data-k="cor_dia"]')
        self.assertIs(self.dados()["ajustes"]["cor_dia"], True)
        self.assertEqual((self.chave_cor_dia(), self.acento(), self.marcada()), ("true", "#FFA23E", ["Laranja"]))
        self.clicar('#cor [data-a="ajuste"][data-k="cor_dia"]')
        self.assertEqual((self.dados()["ajustes"]["cor_dia"], self.dados()["ajustes"]["cor"]), (False, "#8BD45F"))
        self.assertEqual((self.acento(), self.marcada()), ("#8BD45F", ["Verde"]))

    def mudar_relogio(self, quando):
        self.pg.clock.set_fixed_time(quando)
        self.addCleanup(lambda: self.pg.clock.set_fixed_time("2026-11-02T10:00:00-03:00"))

    def test_a_meia_noite_a_cor_muda_sem_recarregar(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "aparencia"})
        self.mudar_relogio("2026-11-02T23:59:00-03:00")
        self.js("(window.dispatchEvent(new Event('focus')), true)")
        self.esperar()
        self.assertEqual(self.acento(), "#FFA23E", "ainda é dia 2")
        self.mudar_relogio("2026-11-03T00:00:30-03:00")
        self.js("(window.dispatchEvent(new Event('focus')), true)")
        self.esperar()
        self.assertEqual((self.acento(), self.marcada()), ("#F2C14E", ["Ouro"]), "dia 3: Ouro, também marcado em Aparência")

    def test_voltar_para_o_app_no_outro_dia_troca_a_cor(self):
        self.abrir(base(bancos=BANCOS))
        self.mudar_relogio("2026-11-04T08:00:00-03:00")
        self.js("(document.dispatchEvent(new Event('visibilitychange')), true)")
        self.esperar()
        self.assertEqual(self.acento(), "#8BD45F", "dia 4: Verde, em qualquer tela")
        self.assertIn('fill="var(--accent)"', self.js("document.querySelector('.app-ic').outerHTML"), "o ícone do app segue a cor")

    def test_com_a_cor_do_dia_desligada_o_dia_nao_muda_a_cor(self):
        self.abrir(base(ajustes={"cor": "#8BD45F", "cor_dia": False}))
        self.mudar_relogio("2026-11-03T00:00:30-03:00")
        self.js("(window.dispatchEvent(new Event('focus')), true)")
        self.esperar()
        self.assertEqual(self.acento(), "#8BD45F")

    def test_criar_backup_avisa_onde_ficou(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        self.clicar('[data-a="backup"]')
        self.assertEqual(self.esperar_aviso("Backup"), "Backup salvo em share/gerencia/gerencia-2026-11-02.zip")

    def test_lista_os_backups_da_pasta(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        self.pg.wait_for_selector(".bk-row")
        linhas = self.js("[...document.querySelectorAll('.bk-row')].map(r => [r.querySelector('b').textContent, r.querySelector('span').textContent])")
        self.assertEqual(len(linhas), 3)
        self.assertEqual(linhas[0], ["02/11/2026 às 07:00", "178 KB · gerencia-2026-11-02-2105.zip"], "o mais novo primeiro")

    def test_restaurar_backup_pede_confirmacao_e_troca_os_dados(self):
        self.trocar_api("restaurarBackup", "async (nome) => { window.__restaurado = nome; return { bancos: [{ id: 'b-lilas', nome: 'Banco Lilás', cor: '#B79BFF', "
                                           "contas: [] }], investimentos: [], lancamentos: [], recorrencias: [] }; }")
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        self.pg.wait_for_selector(".bk-row")
        self.clicar('[data-a="bk-restaurar"]')
        self.assertEqual(self.folha(), "Restaurar backup?")
        self.assertIn("gerencia-2026-11-02-2105.zip", self.folha_texto())
        self.assertIsNone(self.js("window.__restaurado || null"), "antes de confirmar, nada muda")
        self.clicar('.folha-pe [data-a="confirmar"]')
        self.assertEqual(self.esperar_aviso("Backup"), "Backup restaurado")
        self.assertEqual(self.js("window.__restaurado"), "gerencia-2026-11-02-2105.zip")
        self.assertEqual([b["nome"] for b in self.dados()["bancos"]], ["Banco Lilás"])

    def test_versoes_anteriores_lista_e_pede_confirmacao_para_restaurar(self):
        self.abrir(base(bancos=BANCOS, investimentos=[INV_CDB]), ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        self.clicar('[data-a="versoes"]')
        self.assertEqual(self.folha(), "Versões anteriores")
        self.pg.wait_for_selector(".versao-row")
        self.assertEqual(self.conta(".versao-row"), 3, "as 3 mais recentes")
        self.assertIn("1 investimento · R$ 10.000 · automática", self.texto(".versao-row"))
        self.clicar('.versao-row [data-a="restaurar"]')
        self.assertEqual(self.folha(), "Restaurar esta versão?")

    def test_apagar_tudo_pede_confirmacao_e_mantem_categorias_e_preferencias(self):
        self.abrir(base(bancos=BANCOS, investimentos=[INV_CDB], lancamentos=LANC, recorrencias=FIXOS, ajustes={"tema": "escuro"}),
                   ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        self.js("T.persistir(d => { d.categorias.push(a); })", {"id": "c-viagens", "nome": "Viagens", "tipo": "despesa", "cor": "#E04B8A"})
        self.esperar()
        self.clicar('[data-a="apagar-tudo"]')
        self.assertEqual(self.folha(), "Apagar tudo?")
        self.assertIn("Saem 1 investimento e 2 bancos.", self.folha_texto())
        self.clicar('.folha-pe [data-a="confirmar"]')
        d = self.dados()
        self.assertEqual((d["bancos"], d["investimentos"], d["lancamentos"], d["recorrencias"]), ([], [], [], []))
        self.assertIn("c-viagens", [c["id"] for c in d["categorias"]], "as categorias continuam")
        self.assertEqual(d["ajustes"]["tema"], "escuro", "as preferências continuam")
        self.assertEqual(self.esperar_aviso("apagado"), "Tudo apagado")


# ---------------------------------------------------------------------------------------------------------------
class TestDicas(TelaMais):
    def abrir_dicas(self, d, ui=None, assinaturas=True):
        """Abre com estes dados e as dicas que o servidor entregou (o preço do Spotify já conferido na página oficial)."""
        self.abrir(d, ui=ui)
        self.js("(T.S.dicas = a, T.render(), true)", DICAS if assinaturas else dict(DICAS, dicas=[], assinaturas=[]))
        self.esperar()

    def test_dica_de_plano_anual_aparece_no_inicio_com_a_economia_real(self):
        self.abrir_dicas(base(bancos=BANCOS, recorrencias=[SPOTIFY]))
        card = self.linha(".card.dicas", "Dicas")
        self.assertIsNotNone(card, "o quadro de dicas aparece")
        self.assertIn("Spotify no plano anual R$ 239 por ano em vez de R$ 23,90 por mês, 2 meses grátis.", card)
        real = self.js("T.economiaReal(23.9, 239)")
        self.assertGreater(real["real"], 10)
        self.assertEqual(self.js("document.querySelector('.card.dicas .dica-v').firstChild.textContent"), brl0(real["real"]),
                         "a economia real: o desconto menos o que o dinheiro renderia")
        self.assertIn(f"Desconto de {brl0(real['desconto'])} menos {brl0(real['rende'])}", card)
        self.assertIn("Preço conferido em spotify.com em 18/10/2026", card)

    def test_agora_nao_dispensa_a_dica(self):
        self.abrir_dicas(base(bancos=BANCOS, recorrencias=[SPOTIFY]))
        self.clicar(f'[data-a="dica-fora"][data-v="{DICA_SPOTIFY}"]')
        self.assertEqual(self.dados()["ajustes"]["dicas_fora"], [DICA_SPOTIFY])
        self.assertEqual(self.conta(".card.dicas"), 0)
        self.assertEqual(self.esperar_aviso("Dica"), "Dica dispensada")

    def test_mostrar_dispensadas_traz_a_dica_de_volta(self):
        self.abrir_dicas(base(bancos=BANCOS, recorrencias=[SPOTIFY], ajustes={"dicas_fora": [DICA_SPOTIFY]}), ui={"tab": "mais", "maisTela": "caixa"})
        self.assertEqual(self.texto('[data-a="dicas-voltar"]').strip(), "Mostrar dispensadas (1)")
        self.clicar('[data-a="dicas-voltar"]')
        self.assertEqual(self.dados()["ajustes"]["dicas_fora"], [])
        self.assertEqual(self.esperar_aviso("Dicas"), "Dicas de volta")
        self.ir("inicio")
        self.assertIn("Spotify no plano anual", self.texto(".card.dicas"))

    def test_mudar_para_anual_abre_a_janela_com_o_preco_e_a_data(self):
        self.abrir_dicas(base(bancos=BANCOS, recorrencias=[SPOTIFY]))
        self.clicar(f'[data-a="dica-anual"][data-v="{DICA_SPOTIFY}"]')
        self.assertEqual(self.folha(), "Spotify no plano anual")
        self.assertEqual(self.pg.input_value("#da-valor"), "239,00", "o preço da página oficial")
        self.assertEqual(self.pg.input_value("#da-data"), "2026-11-22", "a próxima cobrança, no dia 22")
        self.assertIn("Você economiza", self.texto("#da-eco"))

    def test_confirmar_o_anual_para_o_mensal_e_cria_o_fixo_anual(self):
        self.abrir_dicas(base(bancos=BANCOS, recorrencias=[SPOTIFY]))
        self.clicar(f'[data-a="dica-anual"][data-v="{DICA_SPOTIFY}"]')
        self.clicar('[data-a="da-ok"]')
        self.assertIsNone(self.folha())
        mensal, anual = self.dados()["recorrencias"]
        self.assertEqual(mensal["fim"], "2026-10", "o mensal para antes de novembro")
        self.assertEqual((anual["descricao"], anual["valor"], anual["freq"], anual["inicio"], anual["dia"], anual["conta"], anual["cartao"]),
                         ("Spotify", 239, "anual", "2026-11", 22, "k-ana", True))
        self.assertEqual(self.esperar_aviso("anual"), "Pronto: agora é anual")

    def test_dica_de_categoria_acima_da_media(self):
        self.abrir_dicas(base(lancamentos=RESTAURANTES), assinaturas=False)
        card = self.linha(".card.dicas", "Dicas")
        self.assertIn("Restaurantes acima da média Em outubro foram R$ 900, R$ 450 a mais que a média de julho a setembro.", card)
        self.assertEqual(self.js("document.querySelector('.card.dicas .dica-v').firstChild.textContent"), "+R$ 450")

    def test_dicas_desligadas_nas_opcoes_somem_do_inicio(self):
        self.abrir_dicas(base(bancos=BANCOS, recorrencias=[SPOTIFY], lancamentos=RESTAURANTES, ajustes={"dicas": False}))
        self.assertEqual(self.conta(".card.dicas"), 0)

    def test_com_a_ia_desligada_a_dica_de_categoria_continua(self):
        self.abrir_dicas(base(lancamentos=RESTAURANTES, ajustes={"ia": False}), ui={"tab": "mais", "maisTela": "caixa"}, assinaturas=False)
        self.assertIn("Com a IA desligada, os planos anuais não são conferidos.", self.texto("#dicas"))
        self.ir("inicio")
        self.assertIn("Restaurantes acima da média", self.texto(".card.dicas"), "não usa IA")

    # (era bug até a 1.24.0: com a IA desligada a dica de plano anual continuava no Início)
    def test_com_a_ia_desligada_a_dica_de_plano_anual_some_do_inicio(self):
        self.abrir_dicas(base(bancos=BANCOS, recorrencias=[SPOTIFY], ajustes={"ia": False}))
        self.assertNotIn("plano anual", self.tela())

    # (era bug até a 1.28.0: com a IA desligada, o Início dizia que estava conferindo os preços, que só a IA confere)
    def test_com_a_ia_desligada_o_inicio_nao_diz_que_confere_precos(self):
        conferindo = dict(DICAS, dicas=[], assinaturas=[dict(_ASS, status="conferindo", texto="Conferindo na página oficial…")], conferindo=True)
        for ia, quadro in ((True, 1), (False, 0)):
            with self.subTest(ia=ia):
                self.abrir(base(bancos=BANCOS, recorrencias=[SPOTIFY], ajustes={"corrigir": True, "ia": ia}))
                self.js("(T.S.dicas = a, T.render(), true)", conferindo)
                self.assertEqual(self.conta(".card.dicas .dica-conf"), quadro)
        self.assertNotIn("Conferindo", self.tela())


# ---------------------------------------------------------------------------------------------------------------
CLARO = "rgb(246, 247, 249)"


class TestRelatorioNoTema(TelaMais):
    """O relatório de patrimônio (uma página do servidor) abre no tema que o app está usando; no papel, branco."""
    # o fundo claro da página (cinza bem claro, com os cartões brancos, como no relatório do ResolvIA)

    def url(self, tema):
        self.abrir(base(bancos=BANCOS, ajustes={"tema": tema}))
        self.js("(T.aplicarTema(), true)")
        return self.js("T.urlRelatorio()")

    def test_app_escuro_abre_o_relatorio_escuro(self):
        self.assertEqual(self.url("escuro"), "relatorio?tema=escuro")

    def test_app_claro_abre_o_relatorio_claro(self):
        self.assertEqual(self.url("claro"), "relatorio?tema=claro")

    def fundo(self, tema, impressao=False, esquema="light", ha=None):
        """A cor de fundo do relatório de verdade (gerado pelo server.py) num Chromium."""
        import os
        import tempfile
        from tests.base import importar_servidor
        S = importar_servidor()
        d = S.vazio()
        d["investimentos"] = [{"id": "1", "nome": "CDB Azul", "valor": 1000, "indexador": "parado"}]
        arq = os.path.join(tempfile.mkdtemp(), "relatorio.html")
        with open(arq, "wb") as f:
            f.write(S.gerar_relatorio(d, tema))
        pg = self.ctx.new_page()
        try:
            if ha is not None:  # aberto dentro do Home Assistant, com este modo escuro
                pg.add_init_script(f"window.parent = {{ document: {{ querySelector: s => s === 'home-assistant' ? {{ hass: {{ themes: {{ darkMode: {str(ha).lower()} }} }} }} : null }} }};")
            pg.emulate_media(media="print" if impressao else "screen", color_scheme=esquema)
            pg.goto("file://" + arq)
            return pg.evaluate("getComputedStyle(document.body).backgroundColor")
        finally:
            pg.close()

    def test_relatorio_escuro_e_claro_na_tela(self):
        self.assertEqual(self.fundo("escuro"), "rgb(15, 19, 24)")
        self.assertEqual(self.fundo("claro", esquema="dark"), CLARO, "o tema do app vale mais que o do aparelho")

    def test_relatorio_automatico_segue_o_aparelho(self):
        self.assertEqual(self.fundo(None, esquema="dark"), "rgb(15, 19, 24)")
        self.assertEqual(self.fundo(None, esquema="light"), CLARO)

    def test_relatorio_automatico_dentro_do_home_assistant_segue_o_tema_dele(self):
        self.assertEqual(self.fundo(None, esquema="light", ha=True), "rgb(15, 19, 24)", "HA escuro com o aparelho claro")
        self.assertEqual(self.fundo(None, esquema="dark", ha=False), CLARO, "HA claro com o aparelho escuro")

    def test_relatorio_no_celular_nao_corta_o_valor(self):
        """390 px com um valor de milhão: o banco vai embaixo do nome e a página não rola para o lado."""
        import os
        import tempfile
        from tests.base import importar_servidor
        S = importar_servidor()
        d = S.vazio()
        d["bancos"] = [{"id": "b", "nome": "Corretora Norte"}]
        d["investimentos"] = [{"id": "1", "nome": "Tesouro Selic 2029 com nome comprido", "banco": "b", "valor": 1218500, "indexador": "parado", "tipo": "tesouro"}]
        arq = os.path.join(tempfile.mkdtemp(), "relatorio.html")
        with open(arq, "wb") as f:
            f.write(S.gerar_relatorio(d, "escuro"))
        pg = self.ctx.new_page()
        try:
            pg.set_viewport_size({"width": 390, "height": 844})
            pg.goto("file://" + arq)
            self.assertFalse(pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"), "nada sai da tela")
            self.assertEqual(pg.inner_text(".inv td small"), "Tesouro · Corretora Norte")
            self.assertFalse(pg.locator(".inv td:nth-child(2)").is_visible(), "a coluna Banco some no celular")
            pg.set_viewport_size({"width": 1100, "height": 800})
            self.assertTrue(pg.locator(".inv td:nth-child(2)").is_visible(), "no computador, a coluna Banco volta")
            self.assertEqual(pg.inner_text(".inv td small"), "Tesouro")
        finally:
            pg.close()

    def test_relatorio_filtro_e_botoes_no_celular(self):
        """390 px: Voltar e Baixar PDF do mesmo tamanho, lado a lado; Todos, Meus e De terceiros do mesmo tamanho, o
        escolhido marcado; nada sai da tela. Com o filtro, só os investimentos de quem foi escolhido."""
        import os
        import tempfile
        from tests.base import importar_servidor
        S = importar_servidor()
        d = S.vazio()
        d["investimentos"] = [{"id": "1", "nome": "CDB Azul", "valor": 1000, "indexador": "parado"},
                              {"id": "2", "nome": "Poupança do Beto", "valor": 1218500, "indexador": "parado", "titular": "terceiros", "terceiro": "Beto"}]
        arq = os.path.join(tempfile.mkdtemp(), "relatorio.html")
        with open(arq, "wb") as f:
            f.write(S.gerar_relatorio(d, "escuro", "terceiros"))
        pg = self.ctx.new_page()
        try:
            pg.set_viewport_size({"width": 390, "height": 844})
            pg.goto("file://" + arq)
            self.assertFalse(pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"))
            caixas = pg.evaluate("[...document.querySelectorAll('.barra a')].map(a => { const r = a.getBoundingClientRect(); return [a.textContent, Math.round(r.width), Math.round(r.top), Math.round(r.height)] })")
            self.assertEqual([c[0] for c in caixas], ["Voltar", "Baixar PDF"])
            self.assertEqual(caixas[0][1:], caixas[1][1:], "mesmo tamanho e alinhados")
            filtro = pg.evaluate("[...document.querySelectorAll('.filtro a')].map(a => [a.textContent, Math.round(a.getBoundingClientRect().width), a.className])")
            self.assertEqual([f[0] for f in filtro], ["Todos", "Meus", "De terceiros"])
            self.assertEqual(len({f[1] for f in filtro}), 1, f"os três do mesmo tamanho: {filtro}")
            self.assertEqual([f[2] for f in filtro], ["", "", "on"])
            self.assertEqual(pg.locator("h2").all_inner_texts()[0].split("\n")[0], "De Beto")
            self.assertEqual(pg.locator("text=CDB Azul").count(), 0)
            self.assertEqual(pg.inner_text(".resumo"), "De terceiros\nR$ 1.218.500,00")
            # o cabeçalho dos relatórios dos apps: o ícone, o app, o título e a linha de baixo, sem nada cortado
            self.assertEqual(pg.inner_text(".cab h1"), "Relatório de patrimônio")
            self.assertEqual(pg.inner_text(".cab .app"), "GerencIA · finanças")
            self.assertEqual(" ".join(pg.inner_text(".marca").split()), "CorrerIA Code DESENVOLVIMENTO DE SOFTWARES")
            self.assertEqual(pg.evaluate("document.querySelector('main').lastElementChild.className"), "marca", "a marca é a última coisa")
            self.assertNotEqual(pg.evaluate("getComputedStyle(document.querySelector('.marca .raio')).transform"), "none", "o raio inclinado, como no Sobre")
            self.assertTrue(pg.inner_text(".cab p").startswith("De terceiros · 1 investimento"))
            caixa = pg.evaluate("(c => { const r = c.getBoundingClientRect(), i = c.querySelector('.ic').getBoundingClientRect(); return [r.left, r.right, i.width] })(document.querySelector('.cab'))")
            self.assertEqual(caixa[2], 52, "o ícone inteiro")
            self.assertLessEqual(caixa[1], 390 - 16 + 0.5, "o cabeçalho cabe na tela")
        finally:
            pg.close()

    def test_relatorio_escuro_imprime_em_branco(self):
        self.assertEqual(self.fundo("escuro", impressao=True, esquema="dark"), "rgb(255, 255, 255)")


class TestOpcoesDicas(TelaMais):
    """Mais › Configurações › Opções › Dicas de economia: conferir sozinho no horário e avisar no celular de quem for
    escolhido (as pessoas da casa no Home Assistant), como o aviso de prazos do ResolvIA."""

    PESSOAS = [{"id": "person.ana", "nome": "Ana", "celular": True, "eu": True}, {"id": "person.beto", "nome": "Beto", "celular": False, "eu": False}]

    def trocar_api(self, metodo, js):
        self.js(f"(window.__od_{metodo} = window.__od_{metodo} || T.api.{metodo}, T.api.{metodo} = {js}, true)")
        self.addCleanup(lambda: self.js(f"(T.api.{metodo} = window.__od_{metodo}, T.S.avisoPessoas = undefined, T.S.avisoPedido = null, true)"))

    def abrir_opcoes(self, ajustes=None, pessoas=None):
        self.trocar_api("avisoPessoas", f"async () => ({json.dumps({'pessoas': self.PESSOAS if pessoas is None else pessoas})})")
        self.js("(T.S.avisoPessoas = undefined, T.S.avisoPedido = null, true)")
        self.abrir(base(bancos=BANCOS, ajustes=ajustes or {}))
        self.ir_mais("config", "opcoes")

    def test_com_a_ia_e_as_dicas(self):
        self.abrir_opcoes()
        self.assertEqual(self.textos("#op-dicas .linha-sw b"), ["Conferir sozinho", "Avisar no celular"])
        self.assertEqual(self.texto("#op-dicas .linha-sw span"), "Ligado: uma assinatura nova é conferida logo.")
        self.assertEqual(self.textos("#op-dicas .op-freq button"), ["Toda semana", "A cada 15 dias", "Todo mês"])
        self.assertEqual(self.textos("#op-dicas .op-freq button.on"), ["Todo mês"], "começa em todo mês (como antes)")
        self.assertEqual(self.conta("#op-dicas .quem"), 0, "o aviso começa desligado")

    def test_some_sem_a_ia_ou_sem_as_dicas(self):
        for ajustes in ({"ia": False}, {"dicas": False}):
            with self.subTest(ajustes=ajustes):
                self.abrir_opcoes(ajustes)
                self.assertEqual(self.conta("#op-dicas"), 0)

    def test_conferir_sozinho_desligado(self):
        self.abrir_opcoes()
        self.clicar('#op-dicas [data-k="dicas_auto"]')
        self.assertIs(self.dados()["ajustes"]["dicas_auto"], False)
        self.assertEqual(self.texto("#op-dicas .linha-sw span"), "Desligado: só no Conferir agora.")
        self.assertEqual(self.conta("#op-dicas .op-freq"), 0)

    def test_de_quanto_em_quanto_tempo(self):
        """Como as escolhas do ResolvIA: toda semana, a cada 15 dias ou todo mês (no lugar do horário, que o app do
        Home Assistant no Android mostrava vazio)."""
        self.abrir_opcoes()
        self.clicar('#op-dicas [data-a="dicas-freq"][data-v="quinzena"]')
        self.assertEqual(self.dados()["ajustes"]["dicas_freq"], "quinzena")
        self.assertEqual(self.textos("#op-dicas .op-freq button.on"), ["A cada 15 dias"])
        self.assertEqual(self.pg.get_attribute('#op-dicas [data-v="quinzena"]', "aria-checked"), "true")
        self.assertEqual(self.conta('#op-dicas input[type="time"]'), 0)
        larguras = self.js("[...document.querySelectorAll('#op-dicas .op-freq button')].map(b => [Math.round(b.getBoundingClientRect().width), b.scrollWidth > b.clientWidth])")
        self.assertEqual(len({l for l, _ in larguras}), 1, f"os três do mesmo tamanho: {larguras}")
        self.assertFalse(any(c for _, c in larguras), "nenhum texto cortado")

    def test_avisar_comeca_com_quem_esta_usando(self):
        self.abrir_opcoes()
        self.clicar('#op-dicas [data-k="dicas_aviso"]')
        self.pg.wait_for_selector("#op-dicas .quem-p.on")
        self.assertIs(self.dados()["ajustes"]["dicas_aviso"], True)
        self.assertEqual(self.dados()["ajustes"]["dicas_para"], ["person.ana"])
        self.assertEqual(self.textos("#op-dicas .quem-p"), ["Ana", "Beto\nsem celular"])
        self.assertEqual(self.textos("#op-dicas .quem-p.on"), ["Ana"])
        self.assertEqual(self.textos("#op-dicas .linha-sw > div > span")[1], "Ligado: quando aparece uma dica nova.")

    def test_quem_recebe(self):
        self.abrir_opcoes({"dicas_aviso": True, "dicas_para": ["person.ana"]})
        self.pg.wait_for_selector("#op-dicas .quem-p")
        self.clicar('#op-dicas [data-a="aviso-pessoa"][data-v="person.beto"]')
        self.assertEqual(self.dados()["ajustes"]["dicas_para"], ["person.ana", "person.beto"])
        self.assertEqual(self.texto("#op-dicas .nota"), "Sem celular para Beto: ligue o celular à pessoa no Home Assistant.")
        self.clicar('#op-dicas [data-a="aviso-pessoa"][data-v="person.ana"]')
        self.clicar('#op-dicas [data-a="aviso-pessoa"][data-v="person.beto"]')
        self.assertEqual(self.dados()["ajustes"]["dicas_para"], [])
        self.assertEqual(self.texto("#op-dicas .nota"), "Escolha quem recebe.")

    def test_testar_no_meu_celular(self):
        self.abrir_opcoes({"dicas_aviso": True, "dicas_para": ["person.ana"]})
        self.trocar_api("avisoTestar", "async () => ({ enviados: 1 })")
        self.pg.wait_for_selector('#op-dicas [data-a="aviso-testar"]:not([disabled])')
        self.clicar('#op-dicas [data-a="aviso-testar"]')
        self.assertEqual(self.esperar_aviso("Aviso"), "Aviso enviado para o seu celular.")

    def test_testar_com_erro_do_servidor(self):
        self.abrir_opcoes({"dicas_aviso": True, "dicas_para": ["person.ana"]})
        self.trocar_api("avisoTestar", "async () => { throw new Error('O Home Assistant não entregou o aviso.') }")
        self.pg.wait_for_selector('#op-dicas [data-a="aviso-testar"]:not([disabled])')
        self.clicar('#op-dicas [data-a="aviso-testar"]')
        self.assertEqual(self.esperar_aviso("entregou"), "O Home Assistant não entregou o aviso.")

    def test_testar_inativo_sem_celular(self):
        sem = [dict(p, celular=False) for p in self.PESSOAS]
        self.abrir_opcoes({"dicas_aviso": True, "dicas_para": ["person.ana"]}, pessoas=sem)
        self.pg.wait_for_selector("#op-dicas .quem-p")
        b = self.pg.locator('#op-dicas [data-a="aviso-testar"]')
        self.assertTrue(b.is_disabled())
        self.assertEqual(b.get_attribute("title"), "Sem celular ligado a você no Home Assistant.")

    def test_fora_do_home_assistant(self):
        self.trocar_api("avisoPessoas", "async () => ({ pessoas: null, erro: 'Fora do Home Assistant não dá para avisar no celular.' })")
        self.js("(T.S.avisoPessoas = undefined, T.S.avisoPedido = null, true)")
        self.abrir(base(bancos=BANCOS, ajustes={"dicas_aviso": True}))
        self.ir_mais("config", "opcoes")
        self.pg.wait_for_function("() => !document.querySelector('#op-dicas .nota').textContent.includes('Procurando')")
        self.assertEqual(self.texto("#op-dicas .nota"), "Fora do Home Assistant não dá para avisar no celular.")
        self.assertTrue(self.pg.locator('#op-dicas [data-a="aviso-testar"]').is_disabled())

    def test_sem_pessoas_e_pedido_que_falha(self):
        self.abrir_opcoes({"dicas_aviso": True}, pessoas=[])
        self.pg.wait_for_function("() => !document.querySelector('#op-dicas .nota').textContent.includes('Procurando')")
        self.assertEqual(self.texto("#op-dicas .nota"), "Nenhuma pessoa da casa no Home Assistant.")
        self.trocar_api("avisoPessoas", "async () => { throw new Error('rede') }")
        self.js("(T.S.avisoPessoas = undefined, T.S.avisoPedido = null, T.render(), true)")
        self.pg.wait_for_function("() => !document.querySelector('#op-dicas .nota').textContent.includes('Procurando')")
        self.assertEqual(self.texto("#op-dicas .nota"), "Não consegui ver as pessoas da casa.")


class TestAtalhosParaMais(TelaMais):
    """Os atalhos do Início para um quadro de Mais abrem a tela (e a aba de Configurações) onde ele está."""

    def atalho(self, ancora):
        self.abrir(base(bancos=BANCOS), ui={"maisTela": "", "maisAba": "aparencia"})
        # o botão entra e é tocado no mesmo passo (a tela pode se redesenhar no meio e levar o botão embora)
        self.js("(document.querySelector('#app').insertAdjacentHTML('beforeend', `<button id=at data-a=tab data-v=mais data-ancora=${a}>x</button>`), document.getElementById('at').click(), true)", ancora)
        self.esperar()
        return self.js("[T.S.ui.maisTela, T.S.ui.maisAba]")

    def test_dicas_abre_mais_caixa(self):
        self.assertEqual(self.atalho("dicas"), ["caixa", "aparencia"])
        self.assertTrue(self.visivel("#dicas"))

    def test_indices_abre_mais_invest(self):
        self.assertEqual(self.atalho("indices"), ["invest", "aparencia"])

    def test_ia_abre_configuracoes_nas_integracoes(self):
        self.assertEqual(self.atalho("ia"), ["config", "integracoes"])
        self.assertTrue(self.visivel("#ia"))

    def test_ancora_desconhecida_abre_o_menu(self):
        self.assertEqual(self.atalho("outra"), ["", "aparencia"])
        self.assertEqual(self.conta("#app .menu-row"), 6)


class TestMenuMais(TelaMais):
    """Mais é um menu (como no InventarIA): uma linha por função, cada uma com a sua tela, e Configurações e Sobre por último.
    Numa tela, "‹ Mais" no alto, o Voltar do celular e arrastar para a direita voltam ao menu; Mais fica marcado embaixo."""

    LINHAS = [("Bancos", "Quem tem conta e os cartões."), ("Caixa", "Fixos, categorias e dicas de economia."),
              ("Invest", "Índices de mercado e oportunidades."), ("Relatório de patrimônio", "Para imprimir ou salvar em PDF."),
              ("Configurações", "Integrações, dados, aparência e opções."), ("Sobre", "CorrerIA Code, os apps e o GitHub.")]
    # tela: (título, os quadros que ela tem)
    TELAS = {"bancos": ("Bancos", ["bancos"]), "caixa": ("Caixa", ["fixos", "categorias", "dicas"]),
             "invest": ("Invest", ["indices", "oportunidades"]), "config": ("Configurações", ["outros-apps", "bens", "ia", "senhas-pdf", "email", "correria", "uso-ia", "sensores"]),
             "sobre": ("Sobre", ["por-que", "os-apps"])}

    def no_menu(self):
        return self.js("[T.S.ui.tab, T.S.ui.maisTela, document.querySelector('#app .cab h1').textContent, !!document.querySelector('#app .menu-list')]") == ["mais", "", "Mais", True]

    def marcada(self):
        return self.js("[...document.querySelectorAll('#nav [aria-current=\"page\"]')].map(e => e.dataset.v)")

    def test_as_linhas_do_menu_na_ordem_com_configuracoes_e_sobre_por_ultimo(self):
        self.abrir(base(bancos=BANCOS))
        self.ir("mais")
        self.assertTrue(self.no_menu())
        linhas = self.js("[...document.querySelectorAll('#app .menu-row')].map(r => [r.querySelector('b').textContent, r.querySelector('.mb > span').textContent])")
        self.assertEqual([tuple(x) for x in linhas], self.LINHAS)
        self.assertEqual(self.js("[...document.querySelectorAll('#app .menu-row')].map(r => r.dataset.v || r.dataset.a)"),
                         ["bancos", "caixa", "invest", "relatorio", "config", "sobre"])
        self.assertEqual(self.conta("#app .menu-row .mais-ic svg"), 6, "cada linha com o ícone no quadradinho")
        self.assertEqual(self.conta("#app .uplink"), 0, "no menu não há ‹ Mais")
        self.assertEqual(self.conta("#app .sync"), 0, "nem a linha embaixo do título")
        self.assertEqual(self.conta("#app .mais-abas"), 0, "as abas ficaram em Configurações")
        self.assertEqual(self.marcada(), ["mais"])
        self.assertEqual(self.conta('#nav [data-v="mais"] svg circle'), 3, "o ícone de Mais são três pontos")

    def test_com_bens_a_linha_do_invest_fala_da_perda_de_valor(self):
        carro = {"id": "carro", "nome": "Carro", "tipo": "bens", "valor": 30000, "data_valor": "2026-11-02", "indexador": "deprecia", "taxa": 15, "categoria_bem": "veiculos"}
        self.abrir(base(bancos=BANCOS, investimentos=[carro]), ui={"tab": "mais"})
        self.assertEqual(self.linha("#app .menu-row", "Invest"), "Invest Índices, oportunidades e valor dos bens.")

    def test_cada_linha_abre_a_sua_tela_com_mais_no_alto(self):
        self.abrir(base(bancos=BANCOS))
        for tela, (titulo, quadros) in self.TELAS.items():
            with self.subTest(tela):
                self.ir("mais")
                self.clicar(f'#app .menu-row[data-v="{tela}"]')
                self.assertEqual(self.js("[T.S.ui.tab, T.S.ui.maisTela, history.state && history.state.tela]"), ["mais", tela, tela])
                self.assertEqual(self.texto("#app .cab h1"), titulo)
                self.assertEqual(self.texto("#app .cab .uplink").strip(), "Mais")
                self.assertEqual(self.js("[...document.querySelectorAll('#app .mais-painel > section.card')].map(s => s.id)"), quadros)
                self.assertEqual(self.marcada(), ["mais"], "Mais continua marcado embaixo")
                self.assertEqual(self.conta("#app .menu-list"), 0)

    def test_configuracoes_em_abas_e_a_aba_fica_guardada(self):
        self.abrir(base(bancos=BANCOS))
        self.ir_mais("config")
        self.assertEqual([t.strip() for t in self.textos("#app .mais-abas button")], ["Integrações", "Dados", "Aparência", "Opções"])
        for aba, quadros in (("dados", ["exportar", "backup", "importar", "versoes", "onde", "zerar"]), ("aparencia", ["tema", "cor"]),
                             ("opcoes", ["op-inicio", "op-dicas", "op-caixa", "op-invest", "op-oport"])):
            self.clicar(f'#app .mais-abas [data-v="{aba}"]')
            self.assertEqual(self.js("[...document.querySelectorAll('#app .mais-painel > section.card')].map(s => s.id)"), quadros)
            self.assertEqual(self.js("document.querySelector('#app .mais-abas [aria-selected=\"true\"]').dataset.v"), aba)
        self.assertEqual(self.texto("#app .cab h1"), "Configurações", "trocar de aba não troca de tela")
        self.ir("inicio")
        self.ir_mais("config")
        self.assertEqual(self.js("T.S.ui.maisAba"), "opcoes", "volta na última aba")
        self.assertEqual(self.guardado()["maisAba"], "opcoes")

    def test_versoes_anteriores_explicam_quando_guardam(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        self.assertEqual(self.texto("#versoes .painel-lead"), "Uma cópia a cada 10 minutos de uso e antes de importar ou restaurar. Ficam as 3 mais recentes.")

    def test_mais_no_alto_volta_ao_menu(self):
        self.abrir(base(bancos=BANCOS))
        self.ir_mais("bancos")
        self.clicar("#app .uplink")
        self.assertTrue(self.no_menu())
        self.pg.wait_for_function("!(history.state && history.state.tela)")
        self.assertEqual(self.marcada(), ["mais"])

    def test_voltar_do_celular_volta_ao_menu(self):
        self.abrir(base(bancos=BANCOS))
        for tela in self.TELAS:
            with self.subTest(tela):
                self.ir_mais(tela)
                self.voltar()
                self.assertTrue(self.no_menu())
                self.assertEqual(self.guardado()["maisTela"], "", "o menu fica guardado")

    def test_voltar_com_uma_janela_aberta_fecha_so_a_janela(self):
        self.abrir(base(bancos=BANCOS))
        self.ir_mais("bancos")
        self.clicar('#bancos [data-a="banco"][data-id="b-azul"]')
        self.assertEqual(self.folha(), "Editar banco")
        self.voltar()
        self.assertEqual((self.folha(), self.texto("#app .cab h1")), (None, "Bancos"), "fechou a janela e ficou em Bancos")
        self.clicar('#bancos [data-a="banco"][data-id="b-verde"]')
        self.clicar('.folha-cab [data-a="fechar"]')
        self.assertEqual(self.texto("#app .cab h1"), "Bancos", "o X também fica em Bancos")
        self.voltar()
        self.assertTrue(self.no_menu(), "o Voltar seguinte volta ao menu")

    def test_mais_embaixo_numa_tela_volta_ao_menu(self):
        self.abrir(base(bancos=BANCOS))
        self.ir_mais("caixa")
        self.ir("mais")
        self.assertTrue(self.no_menu())

    def test_sair_pela_barra_de_baixo_e_o_voltar_nao_cai_na_tela(self):
        self.abrir(base(bancos=BANCOS))
        self.ir_mais("invest")
        self.ir("caixa")
        self.pg.wait_for_function("!(history.state && history.state.tela)")
        self.assertEqual(self.texto("#app .cab h1"), "Caixa")
        self.ir("mais")
        self.assertTrue(self.no_menu(), "Mais abre o menu, não a última tela")

    def test_atalho_do_inicio_volta_para_o_inicio_e_mais_no_alto_vai_ao_menu(self):
        self.abrir(base(bancos=BANCOS, investimentos=[INV_CDB]))
        self.pg.locator("#app .op", has_text="Índices").first.click()
        self.esperar()
        self.assertEqual(self.texto("#app .cab h1"), "Invest")
        self.clicar("#app .uplink")
        self.assertTrue(self.no_menu())

    def test_caixa_diz_quantos_fixos_e_categorias(self):
        self.abrir(base(bancos=BANCOS, recorrencias=FIXOS), ui={"tab": "mais", "maisTela": "caixa"})
        self.assertEqual(self.texto(".sync").strip(), f'4 fixos · {self.js("T.S.d.categorias.length")} categorias', "a academia parou: fica fora")
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "caixa"})
        self.assertTrue(self.texto(".sync").strip().startswith("Nenhum fixo ainda · "))

    def test_relatorio_abre_direto_do_menu(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais"})
        self.clicar('#app .menu-row[data-a="relatorio"]')
        self.assertEqual(self.esperar_aviso("relatório"), "Na prévia o relatório não abre.")
        self.assertTrue(self.no_menu(), "não é uma tela: o menu continua")

    def test_nada_passa_da_largura_no_celular_estreito(self):
        self.pg.set_viewport_size({"width": 320, "height": 700})
        self.addCleanup(lambda: self.pg.set_viewport_size({"width": self.LARGURA, "height": self.ALTURA}))
        self.abrir(base(bancos=BANCOS, investimentos=INVS, recorrencias=FIXOS))
        largura = "document.documentElement.scrollWidth"
        self.ir("mais")
        self.assertLessEqual(self.js(largura), 320, "o menu")
        for tela in self.TELAS:
            with self.subTest(tela):
                self.ir_mais(tela)
                self.assertLessEqual(self.js(largura), 320)


class TestMaisSobre(TelaMais):
    """Mais › Sobre, a última linha do menu: quem faz os apps (CorrerIA Code) e por que o nome, os sete apps da família,
    cada um com a sua linha e o link para o GitHub (este marcado com a versão), e Meu GitHub. A mesma página do CronologIA."""

    GH = "https://github.com/diegozapella63"
    APPS = [("CronologIA", "cronologia-ha", "Agenda da família, remédios, rotinas e placar."),
            ("ResolvIA", "resolvia-ha", "Listas de tarefas com prazos, pontos e repetição."),
            ("GerencIA", "gerencia-ha", "Finanças da casa: caixa, cartões e investimentos."),
            ("InventarIA", "inventario-ha", "Inventário da casa: cômodos, itens e valores."),
            ("EconomIA", "economia-ha", "Lista de compras com o melhor preço perto de casa."),
            ("MemorIA", "memoria-ha", "Cadernos de anotação que abrem na hora certa."),
            ("CorrerIA", "correria-ha", "O contato no WhatsApp: os apps respondem por lá.")]

    def versao(self):
        """A versão do config.yaml (a mesma do app.js e do server.py)."""
        with open(os.path.join(RAIZ, "gerencia", "config.yaml"), encoding="utf-8") as f:
            return re.search(r'^version:\s*"?([\d.]+)', f.read(), re.M).group(1)

    def abrir_sobre(self):
        self.abrir(base(bancos=BANCOS))
        self.ir_mais("sobre")

    def test_a_ultima_linha_do_menu_com_o_icone_de_informacao(self):
        self.abrir(base(bancos=BANCOS))
        self.ir("mais")
        ultima = self.pg.locator("#app .menu-row").last
        self.assertEqual((ultima.get_attribute("data-a"), ultima.get_attribute("data-v")), ("mais-tela", "sobre"))
        self.assertEqual(" ".join(ultima.inner_text().split()), "Sobre CorrerIA Code, os apps e o GitHub.")
        self.assertEqual(self.js("document.querySelector('#app .menu-row[data-v=\"sobre\"] .mais-ic svg').innerHTML"),
                         self.js("(d => (d.innerHTML = T.ic('info'), d.firstChild.innerHTML))(document.createElement('div'))"), "o ícone de informação")

    def test_o_alto_com_o_nome_o_que_faz_e_o_lema(self):
        self.abrir_sobre()
        self.assertEqual(self.js("[T.S.ui.maisTela, history.state && history.state.tela]"), ["sobre", "sobre"])
        self.assertEqual((self.texto("#app .cab h1"), self.texto("#app .uplink").strip()), ("Sobre", "Mais"))
        self.assertEqual((self.conta("#app .sync"), self.conta("#app .foot")), (0, 0), "a versão já está em Este app: sem a linha do alto nem o rodapé")
        self.assertEqual(self.js("document.querySelector('.sb-nome').innerHTML"), "Correr<span>IA</span> Code", "o IA na cor de destaque")
        self.assertEqual(self.js("getComputedStyle(document.querySelector('.sb-nome span')).color"),
                         self.js("getComputedStyle(document.querySelector('.cab .brand span')).color"), "a mesma cor do IA de GerencIA no alto")
        self.assertEqual(self.js("document.querySelector('.sb-oque').textContent"), "desenvolvimento de softwares")
        self.assertEqual(self.js("getComputedStyle(document.querySelector('.sb-oque')).textTransform"), "uppercase")
        self.assertEqual(self.texto(".sb-lema"), "Feito na correria, rodado pela IA.")
        self.assertEqual(self.js("getComputedStyle(document.querySelector('.sb-lema')).fontStyle"), "italic")
        self.assertEqual(self.conta(".sobre-topo .sb-raio svg"), 1, "o raio")

    def test_por_que_correria(self):
        self.abrir_sobre()
        self.assertEqual(self.texto("#por-que .mais-head h2"), "Por que CorrerIA?")
        self.assertEqual(self.texto("#por-que .sb-txt"), "Porque eu sou um programador sem tempo: vivo na correria. Então eu uso a IA para rodar tudo isso aqui. "
                                                         "Ela escreve, testa e publica; eu dou as ideias e reclamo dos botões tortos.")

    def test_os_sete_apps_cada_um_com_a_linha_e_o_github(self):
        self.abrir_sobre()
        self.assertEqual(self.texto("#os-apps .mais-head h2"), "Os apps")
        linhas = self.js("[...document.querySelectorAll('#os-apps .sb-app')].map(a => [a.querySelector('.sb-wm').textContent, a.getAttribute('href'), a.querySelector('.mb > span').textContent])")
        self.assertEqual([tuple(x) for x in linhas], [(n, f"{self.GH}/{r}", t) for n, r, t in self.APPS])
        self.assertEqual(self.js("[...document.querySelectorAll('#os-apps .sb-wm')].map(w => w.innerHTML)"),
                         [f"{n[:-2]}<span>IA</span>" for n, _, _ in self.APPS], "o IA de cada nome na cor de destaque, sem espaço no meio")
        self.assertEqual(self.conta("#os-apps .sb-app .mais-ic svg"), 7, "cada app com o seu ícone")

    def test_este_app_marcado_com_a_versao(self):
        self.abrir_sobre()
        v = self.versao()
        self.assertEqual(self.js("T.VERSAO"), v, "a mesma versão do config.yaml")
        aqui = self.pg.locator("#os-apps .sb-app.aqui")
        self.assertEqual(aqui.count(), 1)
        self.assertEqual(aqui.get_attribute("href"), f"{self.GH}/gerencia-ha")
        self.assertEqual(self.textos("#os-apps .sb-aqui"), [f"Este app · v{v}"])

    def test_os_oito_links_abrem_fora_e_meu_github(self):
        self.abrir_sobre()
        links = self.js("[...document.querySelectorAll('#app .sb-pagina a')].map(a => [a.getAttribute('href'), a.target, a.rel])")
        self.assertEqual(links, [[f"{self.GH}/{r}", "_blank", "noopener"] for _, r, _ in self.APPS] + [[self.GH, "_blank", "noopener"]])
        gh = self.pg.locator("#app a.sb-github")
        self.assertEqual((gh.inner_text().strip(), gh.get_attribute("class")), ("Meu GitHub", "btn pri larga sb-github"))
        self.assertEqual(self.js("[...document.querySelectorAll('#app .sb-pagina a')].some(a => a.closest('[data-a]'))"), False, "um toque abre o link, não uma ação do app")

    def test_voltar_e_mais_no_alto_voltam_ao_menu(self):
        self.abrir_sobre()
        self.voltar()
        self.assertEqual(self.js("[T.S.ui.tab, T.S.ui.maisTela, !!document.querySelector('#app .menu-list')]"), ["mais", "", True], "o Voltar do celular")
        self.clicar('#app .menu-row[data-v="sobre"]')
        self.clicar("#app .uplink")
        self.assertEqual(self.js("[T.S.ui.tab, T.S.ui.maisTela, !!document.querySelector('#app .menu-list')]"), ["mais", "", True], "o ‹ Mais")
        self.pg.wait_for_function("!(history.state && history.state.tela)")

    def test_fica_guardado_e_reabre_em_sobre(self):
        self.abrir_sobre()
        self.assertEqual(self.guardado()["maisTela"], "sobre")
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "sobre"})
        self.assertEqual(self.texto("#app .cab h1"), "Sobre")

    def test_de_320_px_ao_computador_nada_passa_da_borda(self):
        self.addCleanup(lambda: self.pg.set_viewport_size({"width": self.LARGURA, "height": self.ALTURA}))
        for w in (320, 390, 1280):
            with self.subTest(w):
                self.pg.set_viewport_size({"width": w, "height": 844})
                self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "sobre"})
                self.assertLessEqual(self.js("document.documentElement.scrollWidth"), w)
                fora = self.js("""(() => { const p = document.querySelector('.sb-pagina').getBoundingClientRect();
                  return [...document.querySelectorAll('.sb-pagina .sobre-topo, .sb-pagina .card, .sb-pagina .sb-app, .sb-pagina .sb-github, .sb-pagina .sb-app b')]
                    .filter(x => { const b = x.getBoundingClientRect(); return b.left < p.left - 1 || b.right > p.right + 1; }).length; })()""")
                self.assertEqual(fora, 0)
                gh, card = self.js("[document.querySelector('.sb-github').getBoundingClientRect().width, document.querySelector('#os-apps').getBoundingClientRect().width]")
                self.assertAlmostEqual(gh, card, delta=1, msg="Meu GitHub da largura dos cartões")
                altura, fonte = self.js("(x => [x.getBoundingClientRect().height, parseFloat(getComputedStyle(x).fontSize)])(document.querySelector('.sb-oque'))")
                self.assertLess(altura, fonte * 2, "desenvolvimento de softwares numa linha só")
                self.assertLess(self.js("document.querySelector('.sb-nome').getBoundingClientRect().height"), 60, "CorrerIA Code numa linha só")

    def test_tema_claro_e_escuro(self):
        cores = {}
        for tema in ("claro", "escuro"):
            self.abrir(base(bancos=BANCOS, ajustes={"corrigir": True, "tema": tema}))
            self.ir_mais("sobre")
            cores[tema] = self.js("[getComputedStyle(document.body).backgroundColor, getComputedStyle(document.querySelector('.sobre-topo')).backgroundColor, getComputedStyle(document.querySelector('.sb-nome')).color]")
        self.assertNotEqual(cores["claro"][0], cores["escuro"][0])
        self.assertEqual(cores["claro"][1:], ["rgb(255, 255, 255)", "rgb(18, 24, 32)"], "no claro, o cartão branco e o nome escuro")
        self.assertEqual(cores["escuro"][1:], ["rgb(21, 26, 33)", "rgb(238, 242, 246)"], "no escuro, o cartão escuro e o nome claro")


class TestNavegacao(TelaMais):
    def setUp(self):
        self.js("(localStorage.removeItem('gerencia.ui'), true)")

    def nova_despesa_com_colar(self):
        """Nova despesa (pelo Adicionar do Caixa) e, por cima dela, Colar mensagem: duas janelas."""
        self.abrir(base(bancos=BANCOS), ui={"tab": "caixa"})
        self.clicar('#nav [data-a="novo"]')
        self.assertEqual(self.folha(), "Nova despesa", "no Caixa, o Adicionar já abre a despesa")
        self.clicar('.imp-tile[data-ini="texto"]')
        self.assertEqual((self.folha(), self.niveis()), ("Colar mensagem", 2))

    def test_janela_aberta_logo_depois_de_fechar_outra_fica_aberta(self):
        """Salvou uma janela e já abriu outra, antes do Voltar que a primeira deu no histórico chegar: a nova fica
        aberta (antes, esse Voltar atrasado fechava a nova), e o Voltar do celular fecha só ela."""
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"})
        self.js("(T.abrirSenhaNova(), new Promise(r => setTimeout(r, 30)))")
        self.js("(T.fecharFolha(), T.abrirSenhaNova(), new Promise(r => setTimeout(r, 300)))")
        self.assertEqual((self.folha(), self.js("history.state && history.state.g")), ("Nova senha", 1), "aberta e no histórico")
        self.voltar()
        self.pg.wait_for_function("() => !window.GERENCIA_TESTE.FOLHA")
        self.assertEqual((self.js("T.S.ui.maisTela"), self.js("history.state && history.state.tela")), ("config", "config"), "fecha só a janela")
        # fechou também antes do Voltar chegar: nada sobra no histórico e a tela continua
        self.js("(T.abrirSenhaNova(), new Promise(r => setTimeout(r, 30)))")
        self.js("(T.fecharFolha(), T.abrirSenhaNova(), T.fecharFolha(), new Promise(r => setTimeout(r, 300)))")
        self.assertEqual((self.niveis(), self.js("T.S.ui.maisTela"), self.js("history.state && history.state.tela")), (0, "config", "config"))

    def test_menu_de_baixo_troca_de_aba(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS, lancamentos=LANC))
        for aba, titulo in (("caixa", "Caixa"), ("investimentos", "Investimentos"), ("mais", "Mais"), ("inicio", "Início")):
            self.ir(aba)
            self.assertEqual(self.js("document.querySelector('.cab h1').textContent"), titulo)
            self.assertEqual(self.js("document.querySelector('#nav [aria-current=\"page\"]').dataset.v"), aba, "a aba aberta fica marcada")

    def test_aba_filtros_e_modos_ficam_guardados(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS, lancamentos=LANC))
        self.ir("caixa")
        self.clicar('[data-a="cx-modo"][data-v="fluxo"]')
        self.ir("investimentos")
        self.clicar('[data-a="filtro"][data-v="meus"]')
        self.clicar('[data-a="inv-modo"][data-v="evolucao"]')
        self.ir_mais("config", "dados")
        g = self.guardado()
        self.assertEqual((g["tab"], g["cxModo"], g["filtro"], g["invModo"], g["maisTela"], g["maisAba"]), ("mais", "fluxo", "meus", "evolucao", "config", "dados"))

    def test_descontar_ir_e_ocultar_bens_nao_ficam_guardados(self):
        carro = {"id": "carro", "nome": "Carro", "tipo": "bens", "valor": 30000, "data_valor": "2026-11-02", "indexador": "deprecia", "taxa": 15, "categoria_bem": "veiculos"}
        self.abrir(base(bancos=BANCOS, investimentos=[INV_CDB, carro]), ui={"tab": "investimentos", "invModo": "evolucao"})
        self.clicar('[data-a="g"][data-k="gIR"]')
        self.clicar('[data-a="g"][data-k="gSemBens"]')
        self.assertEqual(self.js("[T.S.ui.gIR, T.S.ui.gSemBens]"), [True, True], "ligados na tela")
        g = self.guardado()
        self.assertNotIn("gIR", g)
        self.assertNotIn("gSemBens", g)
        self.assertEqual(g["invModo"], "evolucao", "o resto fica guardado")

    def test_voltar_do_celular_fecha_so_a_janela_de_cima(self):
        self.nova_despesa_com_colar()
        self.voltar()
        self.assertEqual((self.folha(), self.niveis()), ("Nova despesa", 1))
        self.voltar()
        self.assertEqual(self.niveis(), 0)

    def test_voltar_com_tres_janelas_fecha_uma_de_cada_vez(self):
        self.nova_despesa_com_colar()
        self.js("(T.abrirFolha(() => ({ titulo: 'Terceira', corpo: '<p>três</p>' }), null, true), true)")
        self.assertEqual((self.folha(), self.niveis()), ("Terceira", 3))
        self.voltar()
        self.assertEqual((self.folha(), self.niveis()), ("Colar mensagem", 2))
        self.voltar()
        self.assertEqual((self.folha(), self.niveis()), ("Nova despesa", 1))
        self.voltar()
        self.assertEqual(self.niveis(), 0)

    def test_x_volta_para_a_janela_de_baixo(self):
        self.nova_despesa_com_colar()
        self.clicar('.folha-cab [data-a="fechar"]')
        self.assertEqual((self.folha(), self.niveis()), ("Nova despesa", 1))

    def test_cancelar_volta_para_a_janela_de_baixo(self):
        self.nova_despesa_com_colar()
        self.clicar('.folha-pe [data-a="fechar"]')
        self.assertEqual((self.folha(), self.niveis()), ("Nova despesa", 1))

    def test_o_que_foi_digitado_na_janela_de_baixo_continua_ao_voltar(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "caixa"})
        self.clicar('#nav [data-a="novo"]')
        self.digitar("#lf-valor", "4590")
        self.preencher("#lf-desc", "Padaria do bairro")
        self.clicar('.imp-tile[data-ini="texto"]')
        self.voltar()
        self.assertEqual((self.pg.input_value("#lf-valor"), self.pg.input_value("#lf-desc")), ("45,90", "Padaria do bairro"))

    def test_fundo_escuro_fecha_a_janela(self):
        self.abrir(base(bancos=BANCOS, investimentos=[INV_CDB]))
        self.clicar('#nav [data-a="novo"]')
        self.assertEqual(self.folha(), "Adicionar")
        self.pg.locator("#folhas .veu").click(position={"x": 20, "y": 20})
        self.esperar()
        self.assertEqual(self.niveis(), 0)

    def test_salvar_na_janela_de_cima_fecha_todas(self):
        self.trocar_api("iaLer", "async () => ({ lancamentos: [{ tipo: 'despesa', descricao: 'Padaria', valor: 12.5, data: '2026-11-02', categoria: 'c-restaurantes', "
                                  "parcela_atual: 0, parcelas_total: 0, cartao: false, banco: '', situacao: 'feito', confianca: 'alta' }], investimentos: [] })")
        self.nova_despesa_com_colar()
        self.preencher("#ia-txt", "padaria 12,50")
        self.clicar('[data-a="ia-ler"]')
        self.pg.wait_for_selector('[data-a="ia-salvar"]')
        self.clicar('[data-a="ia-salvar"]')
        self.assertEqual(self.niveis(), 0, "fechou as duas janelas")
        self.assertEqual([(l["descricao"], l["valor"]) for l in self.dados()["lancamentos"]], [("Padaria", 12.5)])
        self.assertEqual(self.esperar_aviso("IA"), "1 lançamento pela IA")

    def test_busca_no_invest_filtra_e_limpa(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS), ui={"tab": "investimentos", "invModo": "carteira"})
        self.preencher("#q", "carla")
        self.assertEqual(self.textos(".inv .inv-nome"), ["Poupança da Carla"], "acha pela pessoa")
        self.preencher("#q", "banco verde")
        self.assertEqual(sorted(self.textos(".inv .inv-nome")), ["Poupança da Carla", "Tesouro Verde"], "acha pelo banco")
        self.preencher("#q", "nada disso")
        self.assertIn("Nenhum investimento com esse filtro.", self.tela())
        self.clicar('[data-a="busca-limpar"]')
        self.assertEqual(self.conta(".inv"), 3)
        self.assertEqual(self.js("document.activeElement.id"), "q", "o cursor continua na busca")

    def test_digitar_na_busca_da_evolucao_volta_para_a_carteira(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS), ui={"tab": "investimentos", "invModo": "evolucao"})
        self.preencher("#q", "cdb")
        self.assertEqual(self.js("T.S.ui.invModo"), "carteira")
        self.assertEqual(self.textos(".inv .inv-nome"), ["CDB Azul"])


# ---------------------------------------------------------------------------------------------------------------
class TestComputador(TelaMais):
    """Com 1000 px ou mais: barra lateral, ações no alto à direita e janelas no meio."""
    LARGURA, ALTURA = 1200, 800

    def test_barra_lateral_no_lugar_do_menu_de_baixo(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS))
        self.assertTrue(self.visivel("#lado"))
        self.assertFalse(self.visivel("#nav"))
        self.assertEqual([t.strip() for t in self.textos(".top-acts .btn")], ["Ler com IA", "Adicionar"], "as ações no alto à direita")
        nomes = self.js("[...document.querySelectorAll('#lado .side-nav .side-link span:first-of-type')].map(s => s.textContent)")
        self.assertEqual(nomes, ["Início", "Buscar", "Caixa", "Investimentos", "Mais"])
        self.clicar('#lado [data-a="tab"][data-v="mais"]')
        self.assertEqual(self.js("[...document.querySelectorAll('#lado [aria-current=\"page\"]')].map(e => e.textContent.trim())"), ["Mais"], "a seção aberta marcada")
        self.clicar('#app .menu-row[data-v="config"]')
        self.assertEqual(self.js("[...document.querySelectorAll('#lado [aria-current=\"page\"]')].map(e => e.textContent.trim())"), ["Mais"],
                         "numa tela de Mais, Mais continua marcado")
        up, h1 = self.pg.locator("#app .uplink").bounding_box(), self.pg.locator("#app .cab h1").bounding_box()
        self.assertLess(up["y"] + up["height"], h1["y"] + 8, "‹ Mais em cima do título")
        self.assertLess(abs(up["x"] - h1["x"]), 12, "alinhado com o título")

    def test_caixa_na_barra_lateral_mostra_quantas_contas_atrasaram(self):
        self.abrir(base(bancos=BANCOS, lancamentos=LANC))
        self.assertEqual(self.texto('#lado [data-v="caixa"] .side-badge'), "1")
        self.assertEqual(self.conta('#lado [data-a="buscar"]'), 0, "sem investimentos, sem o Buscar")

    def test_bancos_e_pessoas_na_barra_lateral_abrem_a_carteira_filtrada(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS))
        self.assertEqual(self.js("[...document.querySelectorAll('#lado [data-a=\"lado-banco\"] .sl-nome')].map(s => s.textContent)"), ["Banco Azul", "Banco Verde"])
        self.clicar('#lado [data-a="lado-banco"][data-v="b-verde"]')
        u = self.js("T.S.ui")
        self.assertEqual((u["tab"], u["invModo"], u["filtro"], u["banco"]), ("investimentos", "carteira", "todos", "b-verde"))
        self.assertEqual(sorted(self.textos(".inv .inv-nome")), ["Poupança da Carla", "Tesouro Verde"])
        self.clicar('#lado [data-a="pessoa"][data-v="Carla"]')
        self.assertEqual(self.textos(".inv .inv-nome"), ["Poupança da Carla"])
        self.assertEqual(self.js("[...document.querySelectorAll('#lado [aria-current=\"page\"]')].map(e => e.querySelector('.sl-nome').textContent)"), ["Carla"],
                         "só a pessoa aberta fica marcada")

    def test_tecla_barra_abre_a_busca(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS))
        self.pg.keyboard.press("/")
        self.esperar()
        self.assertEqual(self.js("[T.S.ui.tab, T.S.ui.invModo, document.activeElement.id]"), ["investimentos", "carteira", "q"])

    def test_janelas_abrem_no_meio_da_tela(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS))
        self.clicar('.top-acts [data-a="novo"]')
        self.assertEqual(self.folha(), "Adicionar")
        f = self.pg.locator("#folhas .folha").bounding_box()
        meio = 272 + (self.LARGURA - 272) / 2
        self.assertAlmostEqual(f["x"] + f["width"] / 2, meio, delta=20, msg="no meio do espaço ao lado da barra")
        self.assertAlmostEqual(f["y"] + f["height"] / 2, self.ALTURA / 2, delta=40, msg="no meio da altura, não presa embaixo")


# ---------------------------------------------------------------------------------------------------------------
class TestReabrir(TelaMais):
    """O que fica guardado ao fechar e abrir o app de novo (recarrega a página)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.UI0 = cls.pg.evaluate("window.__UI0")

    def reabrir(self, guardado):
        self.pg.evaluate("u => localStorage.setItem('gerencia.ui', JSON.stringify(u))", guardado)
        self.addCleanup(lambda: self.pg.evaluate("() => localStorage.removeItem('gerencia.ui')"))
        self.pg.evaluate("() => history.replaceState(null, '')")  # a entrada de antes, sem tela de Mais
        self.pg.reload()
        self.pg.wait_for_function("window.GERENCIA_TESTE && window.GERENCIA_TESTE.S && window.GERENCIA_TESTE.S.d")
        self.pg.evaluate("u => { window.__UI0 = u; }", self.UI0)
        self.pg.add_style_tag(content=SEM_ANIMACAO)
        self.esperar()

    def test_reabrir_volta_na_aba_e_nos_modos_guardados(self):
        self.reabrir({"tab": "caixa", "cxModo": "fluxo", "invModo": "divisao", "maisTela": "", "maisAba": "dados", "filtro": "terc"})
        u = self.js("T.S.ui")
        self.assertEqual((u["tab"], u["cxModo"], u["invModo"], u["maisAba"], u["filtro"]), ("caixa", "fluxo", "divisao", "dados", "terc"))
        self.assertEqual(self.js("document.querySelector('.cab h1').textContent"), "Caixa")
        self.assertEqual(self.js("T.iso(T.hoje())"), "2026-11-02", "o relógio continua parado")

    def test_reabrir_numa_tela_de_mais_volta_nela_e_o_voltar_vai_ao_menu(self):
        self.reabrir({"tab": "mais", "maisTela": "config", "maisAba": "aparencia"})
        self.assertEqual((self.texto(".cab h1"), self.texto(".mais-abas button.on").strip()), ("Configurações", "Aparência"))
        self.voltar()
        self.assertEqual((self.texto(".cab h1"), self.js("T.S.ui.maisTela")), ("Mais", ""))

    def test_quem_estava_numa_aba_antiga_de_mais_cai_no_lugar_novo(self):
        """Até a 1.25, Mais era em abas (maisAba): Dados, Integrações, Aparência e Opções viraram abas de Configurações;
        Bancos, Caixa e Invest, telas do menu."""
        for velha, tela, titulo, aba in (("dados", "config", "Configurações", "dados"), ("opcoes", "config", "Configurações", "opcoes"),
                                         ("invest", "invest", "Invest", "integracoes"), ("bancos", "bancos", "Bancos", "integracoes")):
            with self.subTest(velha):
                self.reabrir({"tab": "mais", "maisAba": velha})
                u = self.js("T.S.ui")
                self.assertEqual((u["maisTela"], u["maisAba"], self.texto(".cab h1")), (tela, aba, titulo))
        self.reabrir({"tab": "caixa", "maisAba": "aparencia"})
        self.assertEqual(self.js("[T.S.ui.tab, T.S.ui.maisTela, T.S.ui.maisAba]"), ["caixa", "", "aparencia"], "fora de Mais, Mais abre no menu")

    def test_reabrir_descontar_ir_e_ocultar_bens_comecam_desligados(self):
        self.reabrir({"tab": "investimentos", "invModo": "evolucao", "gIR": True, "gSemBens": True})
        self.assertEqual(self.js("[T.S.ui.gIR, T.S.ui.gSemBens, T.S.ui.invModo]"), [False, False, "evolucao"])


# ---------------------------------------------------------------------------------------------------------------
class TestConflitoAvisosENumeros(TelaMais):
    def outro_aparelho_salva(self):
        """Outro aparelho grava um banco a mais (a revisão da prévia sobe; esta tela fica com a velha)."""
        self.js("""T.api.save({ rev: T.S.d.rev, bancos: T.S.d.bancos.concat([{ id: 'b-lilas', nome: 'Banco Lilás', cor: '#B79BFF',
            contas: [{ id: 'k-lilas', pessoa: 'Carla', cartao: false, fechamento: 1, vencimento: 10 }] }]), investimentos: T.S.d.investimentos,
            ajustes: T.S.d.ajustes, exemplo: false, lancamentos: T.S.d.lancamentos, recorrencias: T.S.d.recorrencias, categorias: T.S.d.categorias }).then(() => true)""")

    def cadastrar_banco_roxo(self):
        self.clicar('.btn[data-a="banco"]')
        self.preencher("#b-nome", "Banco Roxo")
        self.clicar('[data-a="b-salvar"]')

    def test_conflito_ao_salvar_avisa_e_recarrega_os_dados(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "bancos"})
        self.outro_aparelho_salva()
        self.cadastrar_banco_roxo()
        self.assertEqual(self.esperar_aviso("aparelho"), "Os dados mudaram em outro aparelho. Confira e tente de novo.")
        self.assertEqual([b["nome"] for b in self.dados()["bancos"]], ["Banco Azul", "Banco Verde", "Banco Lilás"], "os dados do outro aparelho")
        self.assertIsNotNone(self.linha(".banco-row", "Banco Lilás"), "a lista já mostra o que mudou")
        self.assertEqual((self.folha(), self.pg.input_value("#b-nome")), ("Novo banco", "Banco Roxo"), "a janela continua, com o que foi digitado")

    def test_depois_do_conflito_salvar_de_novo_nao_perde_nada(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "bancos"})
        self.outro_aparelho_salva()
        self.cadastrar_banco_roxo()
        self.clicar('[data-a="b-salvar"]')
        self.assertIsNone(self.folha())
        self.assertEqual([b["nome"] for b in self.dados()["bancos"]], ["Banco Azul", "Banco Verde", "Banco Lilás", "Banco Roxo"])

    def test_erro_ao_salvar_avisa_e_nao_muda_nada(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"})
        self.trocar_api("save", "async () => { throw new Error('Sem conexão.'); }")
        self.clicar('#sensores [data-a="ajuste"][data-k="sensores"]')
        self.assertEqual(self.esperar_aviso("salvar"), "Não consegui salvar. Sem conexão.")
        self.assertFalse(self.dados()["ajustes"]["sensores"])
        self.assertIn("Desligado", self.texto("#sensores"), "a chave continua desligada")

    def test_numeros_longos_cabem_nos_destaques_do_inicio(self):
        self.abrir(base(bancos=BANCOS, investimentos=[dict(INV_CDB, valor=987654321.98), INV_TES]))
        self.assertGreater(self.conta(".hl-n"), 3)
        self.assertEqual(self.cortados(".hl-n"), [], "nenhum número cortado")

    def test_numeros_longos_cabem_na_carteira_sem_cobrir_o_nome(self):
        self.abrir(base(bancos=BANCOS, investimentos=[dict(INV_CDB, valor=987654321.98), INV_TES]), ui={"tab": "investimentos", "invModo": "carteira"})
        self.assertEqual(self.js("document.querySelector('.inv-valor').textContent"), "R$ 987.654.321,98")
        self.assertEqual(self.cortados(".inv-valor"), [])
        nome, valor = self.pg.locator(".inv .inv-nome").first.bounding_box(), self.pg.locator(".inv .inv-valor").first.bounding_box()
        self.assertLessEqual(nome["x"] + nome["width"], valor["x"] + 1, "o nome termina antes do valor")

    def test_numeros_grandes_do_placar_nao_se_sobrepoem(self):
        # uma casa com muito dinheiro: 12 milhões investidos e 4,5 milhões em bens
        self.abrir(base(bancos=BANCOS, investimentos=[dict(INV_CDB, valor=12345678.9)]), bens=dict(BENS, hoje=4567890, n=300))
        cols = self.js("""[...document.querySelectorAll('.placar-cols > div')].map(d => { const r = document.createRange(); r.selectNodeContents(d.querySelector('b'));
            const t = r.getBoundingClientRect(), c = d.getBoundingClientRect(); return [t.left, t.right, c.left, c.right]; })""")
        self.assertEqual(len(cols), 3)
        for k, (tl, tr, cl, cr) in enumerate(cols):
            self.assertGreaterEqual(tl, cl - 0.5, f"o número {k + 1} começa dentro da coluna")
            self.assertLessEqual(tr, cr + 0.5, f"o número {k + 1} termina dentro da coluna")
        self.assertLessEqual(self.js("document.querySelector('.placar').scrollWidth"), self.js("document.querySelector('.placar').clientWidth") + 1, "o placar cabe na tela")

    def test_os_dois_numeros_do_par_ficam_do_mesmo_tamanho_e_cabem(self):
        self.abrir(base(bancos=BANCOS, investimentos=[INV_CDB]), bens=dict(BENS, hoje=876543210.55, perde_ano=4321, n=1200))
        self.clicar('.hl-row[data-a="bens"]')
        self.assertEqual(self.folha(), "Bens da casa")
        self.assertIn("Por categoria", self.folha_texto())
        self.js("(T.ajustarTextos(), true)")
        self.assertEqual(self.cortados(".folha .stat-duo b"), [])
        tamanhos = self.js("[...document.querySelectorAll('.folha .stat-duo > div > b')].map(b => getComputedStyle(b).fontSize)")
        self.assertEqual(len(set(tamanhos)), 1, f"Hoje e Perdem por ano do mesmo tamanho ({tamanhos})")


if __name__ == "__main__":
    unittest.main()
