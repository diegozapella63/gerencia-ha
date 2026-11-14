"""A área Investimentos da tela (gerencia/app/www/app.js) num Chromium de verdade: o que a pessoa vê e faz.

Carteira (filtros, cartões, busca), Evolução e Divisão (escopo, horizonte, IR, aporte, gráficos), o que fica guardado
e o que começa desligado, esconder valores, o formulário de investimento (cada tipo e rendimento, erros, editar,
duplicar, excluir, imagens), os índices, os vencimentos, os bens da casa (InventarIA) e a barra lateral do computador.
Os cálculos puros (taxaAnual, valorHoje, totais, projetar...) já estão em tests/test_tela.py; aqui os valores esperados
são feitos à mão (com os índices de exemplo: CDI 13,65%, Selic 13,75%, IPCA 4,5%, TR 0,1% a.m.).

Base e ajudantes em tests/tela_base.py (relógio parado em 02/11/2026 10:00, tela de 390 px). Dados inventados.
Os testes marcados com @unittest.expectedFailure ("BUG: ...") descrevem o comportamento certo de algo que hoje está errado.
"""
import base64
import unittest
from decimal import Decimal, ROUND_HALF_UP

from tests.tela_base import Tela, base, BANCOS, INDEX

CDI, SELIC, IPCA, TR = 13.65, 13.75, 4.5, 0.1
HOJE_ISO = "2026-11-02"


# ---------------------------------------------------------------------------------------------------- contas à mão
def taxa(indexador, t=0.0):
    """A taxa ao ano, como no DOCS.md ("Rendimento no padrão de mercado")."""
    cdi, selic, ipca, tr, t = CDI / 100, SELIC / 100, IPCA / 100, TR / 100, t / 100
    return {"cdi_pct": cdi * t, "cdi_mais": (1 + cdi) * (1 + t) - 1, "pre": t, "ipca_mais": (1 + ipca) * (1 + t) - 1,
            "selic_mais": (1 + selic) * (1 + t) - 1, "poupanca": (1.005 * (1 + tr)) ** 12 - 1, "estimado": t, "deprecia": -t}.get(indexador, 0.0)


def rende_mes(v, r):
    return max(0.0, v * ((1 + r) ** (1 / 12) - 1))


def brl(v, casas=2):
    """Como o app escreve dinheiro: R$ 12.345,67 (ou R$ 12.346 sem centavos)."""
    q = Decimal(repr(v)).quantize(Decimal(1) if casas == 0 else Decimal("0.01"), rounding=ROUND_HALF_UP)
    return "R$ " + f"{q:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def inv(id_, nome, valor, indexador, taxa_=0, **mais):
    d = {"id": id_, "nome": nome, "valor": valor, "indexador": indexador, "taxa": taxa_, "data_valor": HOJE_ISO, "tipo": "cdb",
         "banco": "", "liquidez": "vencimento", "vencimento": None, "titular": "meu", "terceiro": "", "obs": ""}
    d.update(mais)
    return d


# Todos com o valor de hoje (data_valor = hoje): o valor de hoje é o próprio valor.
CDB = inv("cdb", "CDB Azul 2028", 10000, "cdi_pct", 110, banco="b-azul", vencimento="2028-03-15")
LCI = inv("lci", "LCI Verde", 5000, "cdi_pct", 90, banco="b-verde", tipo="lci", vencimento="2027-06-01", obs="resgatar em março")
TES = inv("tes", "Tesouro Selic", 2000, "selic_mais", 0, banco="b-azul", tipo="tesouro", liquidez="diaria")
DIN = inv("din", "Dinheiro em casa", 300, "parado", tipo="dinheiro", liquidez="diaria")
POUP = inv("poup", "Poupança do Beto", 1500, "poupanca", banco="b-verde", tipo="poupanca", liquidez="diaria", titular="terceiros", terceiro="Beto")
CX = inv("cx", "Caixinha da Carla", 800, "cdi_pct", 100, banco="b-azul", tipo="caixinha", liquidez="diaria", titular="terceiros", terceiro="Carla")
INVS = [CDB, LCI, TES, DIN, POUP, CX]
# total 19.600 · meus 17.300 (CDB, LCI, Tesouro, Dinheiro) · de terceiros 2.300 (Beto 1.500, Carla 800)
RENDE = {i["id"]: rende_mes(i["valor"], taxa(i["indexador"], i["taxa"])) for i in INVS}
# os mesmos com o valor de maio: o valor de hoje já rendeu (para conferir com totais())
INVS_VELHOS = [dict(i, data_valor="2026-05-04") for i in INVS]

PRE = inv("pre", "CDB Prefixado", 10000, "pre", 12, banco="b-azul")  # 10.000 a 12% a.a.: 11.200 em 1 ano, 17.623 em 5

# os bens da casa como o servidor devolve (/api/bens): 7 itens, 12.000 hoje, perdem 1.700 por ano
BENS = {"ok": True, "hoje": 12000, "registrado": 15000, "perde_ano": 1700, "n": 7, "versao": "1.17.0",
        "categorias": [{"id": "moveis", "nome": "Móveis", "taxa": 10, "hoje": 7000, "registrado": 9000, "n": 4},
                       {"id": "eletronicos", "nome": "Eletrônicos", "taxa": 20, "hoje": 5000, "registrado": 6000, "n": 3}],
        "comodos": [{"id": "sala", "nome": "Sala", "hoje": 8000, "n": 4}, {"id": "quarto", "nome": "Quarto", "hoje": 4000, "n": 3}]}
# bens em N anos: 7.000 × 0,9^N + 5.000 × 0,8^N
BENS_1, BENS_5, BENS_10 = 7000 * 0.9 + 5000 * 0.8, 7000 * 0.9 ** 5 + 5000 * 0.8 ** 5, 7000 * 0.9 ** 10 + 5000 * 0.8 ** 10

# uma imagem PNG de 1 × 1 pixel
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==")

SALVAR = '[data-a="f-salvar"]:not([data-mais])'


class _TelaInvest(Tela):
    """Ajudantes da área Investimentos."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # sem as animações (janela que sobe, plaquinhas): o Playwright não precisa esperar cada clique "parar de mexer"
        cls.pg.add_style_tag(content="*, *::before, *::after { transition: none !important; animation: none !important; }")

    def invest(self, d=None, ui=None, bens=None):
        """Abre o app na aba Invest."""
        u = {"tab": "investimentos"}
        u.update(ui or {})
        self.abrir(d if d is not None else base(bancos=BANCOS, investimentos=INVS), ui=u, bens=bens)

    def nomes(self):
        """Os nomes dos cartões da Carteira, na ordem da tela (sem o cartão dos bens da casa)."""
        return self.textos('#app .inv:not(.inv-ro) .inv-nome')

    def resumo(self):
        return self.texto('#app .resumo-lista span'), self.texto('#app .resumo-lista b')

    def stat(self):
        """Os pares de números (Hoje e Em N anos; Total e Rende por mês): [(rótulo, valor, nota)]."""
        return [tuple(x) for x in self.js("[...document.querySelectorAll('#app .stat-duo > div')].map(d => "
                                          "[d.querySelector('span').textContent, d.querySelector('b').textContent, d.querySelector('small')?.textContent || ''])")]

    def comps(self):
        """As linhas da Divisão: [(nome, detalhe, valor, %)]."""
        return [tuple(x) for x in self.js("[...document.querySelectorAll('#app .comp')].map(c => [c.querySelector('.nm b').textContent, "
                                          "c.querySelector('.sub').textContent, c.querySelector('.vl').firstChild.textContent, c.querySelector('.vl small').textContent])")]

    def modo(self, m):
        self.clicar(f'#app [data-a="inv-modo"][data-v="{m}"]')

    def novo(self, d=None, ui=None):
        """Abre o Novo investimento pelo Adicionar da aba Invest."""
        self.invest(d if d is not None else base(bancos=BANCOS), ui)
        self.clicar('#nav [data-a="novo"]')
        self.assertEqual(self.folha(), "Novo investimento")

    def editar(self, id_):
        self.clicar(f'#app .inv[data-id="{id_}"]')
        self.assertEqual(self.folha(), "Editar investimento")

    def salvo(self, nome=None):
        """O investimento salvo (pelo nome; sem nome, o último)."""
        invs = self.dados()["investimentos"]
        return invs[-1] if nome is None else next(i for i in invs if i["nome"] == nome)

    def visivel(self, rotulo):
        """O campo do formulário com esse rótulo está à mostra?"""
        loc = self.pg.locator(f'.folha .campo:has(> .lbl:text-is("{rotulo}"))')
        return loc.count() > 0 and loc.first.is_visible()

    def tc(self, sel):
        """O texto como está no HTML (sem as maiúsculas do CSS e mesmo dentro de um detalhe fechado), espaços juntados."""
        return self.js("[...document.querySelectorAll(a)].map(e => e.textContent.replace(/\\s+/g, ' ').trim())", sel)

    def placar(self):
        """O placar do Início: o rótulo (aria-label) e as colunas [(rótulo, valor)]."""
        return (self.pg.get_attribute(".placar-num", "aria-label"),
                [tuple(x) for x in self.js("[...document.querySelectorAll('.placar-cols > div')].map(d => [...d.children].map(c => c.textContent))")])

    def ui_guardada(self):
        return self.js("JSON.parse(localStorage.getItem('gerencia.ui') || '{}')")

    def cabe(self, sel):
        """Nenhum número cortado: a largura do texto cabe na caixa."""
        return self.js("[...document.querySelectorAll(a)].every(e => e.scrollWidth <= e.clientWidth + 1)", sel)


# ---------------------------------------------------------------------------------------------------------------
class TestCarteira(_TelaInvest):
    def test_sem_investimentos_mostra_como_comecar(self):
        self.invest(base(bancos=BANCOS))
        self.assertIn("Nada cadastrado ainda.", self.texto("#app .vazio"))
        self.assertEqual(self.conta("#q"), 0, "sem busca nem abas sem investimentos")
        self.clicar('#app [data-a="novo-inv"]')
        self.assertEqual(self.folha(), "Novo investimento")

    def test_numeros_do_topo_batem_com_totais(self):
        """O total da Carteira em Todos, Meus e Terceiros e o placar do Início são os de totais() (valores que já renderam)."""
        self.invest(base(bancos=BANCOS, investimentos=INVS_VELHOS))
        t = self.js("T.totais()")
        self.assertGreater(t["meu"], 17300, "os valores de maio já renderam")
        for filtro, k, n in (("todos", "total", 6), ("meus", "meu", 4), ("terc", "terc", 2)):
            with self.subTest(filtro=filtro):
                self.clicar(f'#app [data-a="filtro"][data-v="{filtro}"]')
                txt, soma = self.resumo()
                self.assertEqual(soma, brl(t[k], 0))
                self.assertTrue(txt.startswith(f"{n} investimentos · rende ≈ "), txt)
        self.ir("inicio")
        self.assertEqual(self.pg.get_attribute(".placar-num", "aria-label"), f"Patrimônio de {brl(t['meu'], 0)}", "o patrimônio é só o seu")
        self.assertEqual(self.conta('#app .card:has-text("Dinheiro de terceiros")'), 0, "o dinheiro de terceiros fica no Invest, fora do Início")

    def test_filtros_todos_meus_e_terceiros(self):
        self.invest()
        self.assertEqual(self.tc('#app [data-a="filtro"]'), ["Todos 6", "Meus 4", "Terceiros 2"])
        self.assertEqual(self.nomes(), ["CDB Azul 2028", "LCI Verde", "Tesouro Selic", "Poupança do Beto", "Caixinha da Carla", "Dinheiro em casa"],
                         "do maior para o menor valor")
        self.assertEqual(self.resumo(), (f"6 investimentos · rende ≈ {brl(sum(RENDE.values()), 0)}/mês", "R$ 19.600"))
        self.clicar('#app [data-a="filtro"][data-v="meus"]')
        self.assertEqual(self.nomes(), ["CDB Azul 2028", "LCI Verde", "Tesouro Selic", "Dinheiro em casa"])
        self.assertEqual(self.resumo()[1], "R$ 17.300")
        self.clicar('#app [data-a="filtro"][data-v="terc"]')
        self.assertEqual(self.nomes(), ["Poupança do Beto", "Caixinha da Carla"])
        self.assertEqual(self.resumo()[1], "R$ 2.300")
        self.assertEqual(self.tc('#app [data-a="filtro"].on'), ["Terceiros 2"])

    def test_filtro_por_pessoa(self):
        self.invest()
        self.clicar('#app [data-a="filtro"][data-v="terc"]')
        self.assertEqual(self.textos('#app [data-a="pessoa-f"]'), ["Todas as pessoas", "Beto", "Carla"])
        self.clicar('#app [data-a="pessoa-f"][data-v="Carla"]')
        self.assertEqual(self.nomes(), ["Caixinha da Carla"])
        self.assertEqual(self.resumo()[1], "R$ 800")
        self.clicar('#app [data-a="filtro"][data-v="todos"]')
        self.clicar('#app [data-a="filtro"][data-v="terc"]')
        self.assertEqual(self.nomes(), ["Poupança do Beto", "Caixinha da Carla"], "trocar o filtro esquece a pessoa")
        self.assertEqual(self.texto('#app [data-a="pessoa-f"].on'), "Todas as pessoas")
        # com uma pessoa só, não há o que escolher
        self.invest(base(bancos=BANCOS, investimentos=[CDB, POUP]), ui={"filtro": "terc"})
        self.assertEqual(self.conta('#app [data-a="pessoa-f"]'), 0)

    def test_filtro_por_banco(self):
        self.invest()
        self.assertEqual(self.textos('#app [data-a="banco-f"]'), ["Todos os bancos", "Banco Azul", "Banco Verde", "Sem banco"])
        self.clicar('#app [data-a="banco-f"][data-v="b-verde"]')
        self.assertEqual(self.nomes(), ["LCI Verde", "Poupança do Beto"])
        self.assertEqual(self.resumo()[1], "R$ 6.500")
        self.clicar('#app [data-a="filtro"][data-v="terc"]')
        self.assertEqual(self.nomes(), ["Poupança do Beto"], "o banco vale junto com Terceiros")
        self.clicar('#app [data-a="banco-f"]:text-is("Todos os bancos")')
        self.assertEqual(self.nomes(), ["Poupança do Beto", "Caixinha da Carla"])

    # (era bug até a 1.24.0)
    def test_filtro_sem_banco_mostra_so_os_sem_banco(self):
        self.invest()
        self.clicar('#app [data-a="banco-f"]:text-is("Sem banco")')
        self.assertEqual(self.nomes(), ["Dinheiro em casa"], "só o que não tem banco")
        self.assertEqual(self.texto('#app [data-a="banco-f"].on'), "Sem banco", "o chip fica marcado")

    def test_cartao_mostra_nome_valor_banco_taxa_dono_e_vencimento(self):
        self.invest()
        c = '#app .inv[data-id="cdb"]'
        self.assertEqual(self.texto(c + " .inv-nome"), "CDB Azul 2028")
        self.assertEqual(self.texto(c + " .inv-valor"), "R$ 10.000,00")
        self.assertEqual(self.texto(c + " .inv-meta"), "Banco Azul · Ana · CDB", "o Banco Azul tem a Ana e o Beto: de quem é a conta (1.52)")
        self.assertEqual(self.textos(c + " .tag"), ["110% do CDI", "Meu", "Vence 15/03/2028"])
        self.assertEqual(self.textos(c + " .inv-pe span"), [f"≈ {brl(RENDE['cdb'])} por mês", "valor de 02/11"])
        self.assertEqual(self.js("getComputedStyle(document.querySelector(a)).getPropertyValue('--c').trim()", c), "#56AEFF", "a cor do banco")

    def test_etiqueta_de_liquidez(self):
        self.invest(base(bancos=BANCOS, investimentos=[
            TES, inv("venc", "CDB sem data", 900, "pre", 12, banco="b-azul"),
            inv("velho", "CDB vencido", 800, "pre", 12, banco="b-azul", vencimento="2026-10-01"), DIN,
            inv("moto", "Moto", 7000, "deprecia", 15, tipo="bens", categoria_bem="veiculos", liquidez="diaria")]))
        casos = {"tes": ["Liquidez diária"], "venc": ["No vencimento"], "velho": ["Venceu 01/10/2026"], "din": [], "moto": []}
        for id_, liq in casos.items():
            with self.subTest(id_):
                tags = self.textos(f'#app .inv[data-id="{id_}"] .tag')[2:]
                self.assertEqual(tags, liq)
        self.assertEqual(self.conta('#app .inv[data-id="velho"] .tag.alerta'), 1, "vencido em destaque")
        self.assertEqual(self.texto('#app .inv[data-id="din"] .inv-meta'), "Em espécie")
        self.assertEqual(self.texto('#app .inv[data-id="din"] .inv-pe span'), "Não rende")

    def test_valor_desatualizado_fica_em_vermelho(self):
        self.invest(base(bancos=BANCOS, investimentos=[
            inv("velho", "CDB antigo", 1000, "pre", 12, data_valor="2025-08-01"), inv("novo", "CDB recente", 1000, "pre", 12, data_valor="2026-10-20"),
            inv("parado", "Cofre", 1000, "parado", data_valor="2025-08-01", tipo="dinheiro")]))
        data = lambda i: self.pg.locator(f'#app .inv[data-id="{i}"] .inv-pe span').nth(1)
        self.assertEqual(data("velho").inner_text(), "valor de 01/08/25", "de outro ano, com o ano")
        self.assertEqual(data("novo").inner_text(), "valor de 20/10")
        cor = lambda i: data(i).get_attribute("style") or ""
        self.assertIn("danger", cor("velho"), "mais de 2 meses sem atualizar")
        self.assertNotIn("danger", cor("novo"))
        self.assertNotIn("danger", cor("parado"), "dinheiro parado não precisa atualizar")


# ---------------------------------------------------------------------------------------------------------------
class TestBusca(_TelaInvest):
    def test_busca_por_nome_banco_pessoa_tipo_e_observacao(self):
        self.invest()
        casos = {"azul 2028": ["CDB Azul 2028"], "verde": ["LCI Verde", "Poupança do Beto"], "carla": ["Caixinha da Carla"],
                 "Tesouro": ["Tesouro Selic"], "poupança": ["Poupança do Beto"], "março": ["LCI Verde"], "CDB": ["CDB Azul 2028"]}
        for q, esperado in casos.items():
            with self.subTest(q=q):
                self.preencher("#q", q)
                self.assertEqual(self.nomes(), esperado)
                self.assertTrue(self.resumo()[0].startswith(f"{len(esperado)} investimento"))

    # (era bug até a 1.24.0)
    def test_busca_sem_acento(self):
        self.invest()
        self.preencher("#q", "poupanca")
        self.assertEqual(self.nomes(), ["Poupança do Beto"])
        self.preencher("#q", "marco")
        self.assertEqual(self.nomes(), ["LCI Verde"], "a observação também")

    def test_digitar_na_busca_volta_para_a_carteira(self):
        self.invest(ui={"invModo": "evolucao"})
        self.pg.click("#q")
        self.pg.keyboard.type("cdb")
        self.esperar()
        self.assertEqual(self.js("T.S.ui.invModo"), "carteira")
        self.assertEqual(self.texto('#app .seg [data-a="inv-modo"].on'), "Carteira")
        self.assertEqual(self.nomes(), ["CDB Azul 2028"])
        self.assertEqual((self.js("document.activeElement.id"), self.pg.input_value("#q")), ("q", "cdb"), "o cursor continua na busca")

    def test_limpar_a_busca(self):
        self.invest()
        self.preencher("#q", "verde")
        self.clicar('#app [data-a="busca-limpar"]')
        self.assertEqual(len(self.nomes()), 6)
        self.assertEqual((self.pg.input_value("#q"), self.js("document.activeElement.id")), ("", "q"))
        self.preencher("#q", "verde")
        self.pg.press("#q", "Escape")
        self.esperar()
        self.assertEqual((self.js("T.S.ui.busca"), len(self.nomes())), ("", 6), "Esc também limpa")

    def test_busca_dentro_do_filtro(self):
        self.invest(ui={"filtro": "meus"})
        self.preencher("#q", "azul")
        self.assertEqual(self.nomes(), ["CDB Azul 2028", "Tesouro Selic"], "a Caixinha da Carla é do Banco Azul, mas de terceiros")
        self.preencher("#q", "carla")
        self.assertEqual(self.texto("#app .vazio"), "Nenhum investimento com esse filtro.")


# ---------------------------------------------------------------------------------------------------------------
class TestEvolucao(_TelaInvest):
    def test_hoje_de_cada_escopo_bate_com_totais(self):
        self.invest(base(bancos=BANCOS, investimentos=[CDB, LCI]), ui={"invModo": "evolucao"})
        self.assertEqual(self.conta('#app [data-k="gEscopo"]'), 0, "sem terceiros, não há escopo para escolher")
        self.invest(base(bancos=BANCOS, investimentos=INVS_VELHOS), ui={"invModo": "evolucao"})
        self.assertEqual(self.textos('#app [data-k="gEscopo"]'), ["Tudo", "Só o meu", "De terceiros"])
        t = self.js("T.totais()")
        for esc, k in (("tudo", "total"), ("meu", "meu"), ("terc", "terc")):
            with self.subTest(esc):
                self.clicar(f'#app [data-k="gEscopo"][data-v="{esc}"]')
                self.assertEqual(self.stat()[0][:2], ("Hoje", brl(t[k], 0)))

    def test_em_n_anos_bate_com_a_conta(self):
        self.invest(base(bancos=BANCOS, investimentos=[PRE]), ui={"invModo": "evolucao", "gAnos": 5})
        self.assertEqual(self.stat(), [("Hoje", "R$ 10.000", ""), ("Em 5 anos", brl(10000 * 1.12 ** 5, 0), "+R$ 7.623 de rendimento")])
        self.assertIn("rendimento médio de 12% a.a.", self.texto("#app .nota"))
        self.assertIn("CDI 13,65%, IPCA 4,5%", self.texto("#app .nota"))

    def test_horizonte_de_1_2_5_e_10_anos(self):
        self.invest(base(bancos=BANCOS, investimentos=[PRE]), ui={"invModo": "evolucao"})
        self.assertEqual(self.textos('#app [data-k="gAnos"]'), ["1 ano", "2 anos", "5 anos", "10 anos"])
        for anos, rot in ((1, "Em 1 ano"), (2, "Em 2 anos"), (10, "Em 10 anos")):
            with self.subTest(anos=anos):
                self.clicar(f'#app [data-k="gAnos"][data-v="{anos}"]')
                self.assertEqual(self.stat()[1][:2], (rot, brl(10000 * 1.12 ** anos, 0)))
                self.assertEqual(self.conta("#app .tabela tbody tr"), anos, "uma linha por ano na tabela")
                self.assertEqual(self.texto('#app [data-k="gAnos"].on'), "1 ano" if anos == 1 else f"{anos} anos")

    def test_horizonte_outro(self):
        self.invest(base(bancos=BANCOS, investimentos=[PRE]), ui={"invModo": "evolucao"})
        self.clicar('#app [data-a="g-anos-outro"]')
        self.assertEqual(self.folha(), "Horizonte da projeção")
        self.assertEqual(self.textos('.folha [data-a="g-anos-pre"]'), ["3 anos", "15 anos", "20 anos", "25 anos", "30 anos", "40 anos"])
        self.assertEqual(self.pg.input_value("#hz-anos"), "20", "começa em 20 quando o de agora é um dos fixos")
        self.clicar('.folha [data-a="g-anos-pre"][data-v="30"]')
        self.assertIsNone(self.folha())
        self.assertEqual(self.texto('#app [data-a="g-anos-outro"]'), "30 anos")
        self.assertEqual(self.stat()[1][:2], ("Em 30 anos", brl(10000 * 1.12 ** 30, 0)))
        self.assertEqual(self.conta("#app .tabela tbody tr"), 30)
        # de novo: abre com o de agora; digitar e Enter
        self.clicar('#app [data-a="g-anos-outro"]')
        self.assertEqual(self.pg.input_value("#hz-anos"), "30")
        self.pg.fill("#hz-anos", "7")
        self.pg.press("#hz-anos", "Enter")
        self.esperar()
        self.assertIsNone(self.folha())
        self.assertEqual(self.stat()[1][0], "Em 7 anos")
        self.assertEqual(self.ui_guardada().get("gAnos"), 7, "o horizonte fica guardado")

    def test_horizonte_outro_fora_de_1_a_50_nao_muda(self):
        self.invest(base(bancos=BANCOS, investimentos=[PRE]), ui={"invModo": "evolucao", "gAnos": 5})
        self.clicar('#app [data-a="g-anos-outro"]')
        for v in ("0", "51", "", "-3"):
            with self.subTest(v=v):
                self.pg.fill("#hz-anos", v)
                self.clicar('.folha [data-a="g-anos-ok"]')
                self.assertEqual(self.aviso(), "Escolha de 1 a 50 anos.")
                self.assertEqual(self.folha(), "Horizonte da projeção", "a janela fica aberta")
                self.assertEqual(self.js("T.S.ui.gAnos"), 5)

    def test_descontar_imposto_de_renda(self):
        """CDB de 10.000 a 12% por 1 ano: 1.200 de rendimento, 17,5% de IR (mais de 360 dias) = 10.990. LCI é isenta: 11.200."""
        lci = dict(PRE, id="lci", nome="LCI Prefixada", tipo="lci")
        self.invest(base(bancos=BANCOS, investimentos=[PRE, lci]), ui={"invModo": "evolucao", "gAnos": 1})
        self.assertEqual(self.stat()[1][:2], ("Em 1 ano", "R$ 22.400"))
        self.assertEqual(self.conta('#app [data-k="gIR"].on'), 0, "começa desligado")
        self.clicar('#app [data-k="gIR"]')
        self.assertEqual(self.stat()[1], ("Em 1 ano, líquido", "R$ 22.190", "+R$ 2.190 de rendimento"))
        self.assertEqual(self.conta('#app [data-k="gIR"].on'), 1)
        self.clicar('#app [data-k="gIR"]')
        self.assertEqual(self.stat()[1][:2], ("Em 1 ano", "R$ 22.400"))

    def test_aporte_por_mes_entra_na_projecao_so_do_meu(self):
        ap = {"id": "ap1", "tipo": "despesa", "aporte": True, "descricao": "Aporte", "valor": 500, "dia": 6, "inicio": "2026-01", "categoria": "c-investimentos"}
        self.invest(base(bancos=BANCOS, investimentos=[PRE, POUP], recorrencias=[ap]), ui={"invModo": "evolucao", "gEscopo": "meu", "gAnos": 1})
        self.assertEqual(self.textos("#app .aporte-info > *"), ["R$ 500,00", "Todo dia 6."])
        self.assertEqual(self.textos("#app .btns-2 .btn"), ["Mudar o aporte", "Outro aporte"])
        f = 1.12 ** (1 / 12)
        com_aporte = 11200 + 500 * (f ** 12 - 1) / (f - 1)  # 12 aportes de 500 rendendo 12% a.a.
        self.assertEqual(self.stat()[1], ("Em 1 ano", brl(com_aporte, 0), f"+{brl(com_aporte - 16000, 0)} de rendimento"))
        self.assertIn("Investido + aportes", self.texto("#app .leg"))
        self.clicar('#app [data-k="gEscopo"][data-v="terc"]')
        self.assertIn("Aportes contam só nos seus investimentos.", self.texto("#app .ctrl"))
        self.assertEqual(self.stat()[1][1], brl(1500 * (1 + taxa("poupanca")), 0), "o dinheiro de terceiros sem aporte")
        self.assertNotIn("Investido + aportes", self.texto("#app .leg"))

    def test_sem_aporte_oferece_cadastrar(self):
        self.invest(base(bancos=BANCOS, investimentos=[PRE]), ui={"invModo": "evolucao"})
        self.assertIn("Nenhum. Cadastre uma conta a pagar do tipo Aporte, todo mês.", self.texto("#app .ctrl"))
        self.clicar('#app [data-a="aporte-novo"]')
        self.assertEqual(self.folha(), "Novo aporte")

    def test_grafico_desenha_as_linhas_e_a_legenda(self):
        self.invest(base(bancos=BANCOS, investimentos=[PRE]), ui={"invModo": "evolucao"})
        classes = lambda: self.js("[...document.querySelectorAll('#ch-evo svg path')].map(p => p.getAttribute('class'))")
        self.assertEqual(classes(), ["a-proj", "l-apl", "l-real", "l-proj"])
        self.assertEqual(self.textos("#app .leg span"), ["Projetado", "Valor investido", "Em dinheiro de hoje"])
        self.assertEqual(self.js("document.querySelector('#ch-evo svg').getAttribute('width') == document.querySelector('#ch-evo').clientWidth"), True,
                         "o gráfico ocupa a largura do cartão")
        hist = [{"d": "2026-05-04", "total": 8000, "meu": 8000, "terceiros": 0}, {"d": "2026-08-03", "total": 9000, "meu": 9000, "terceiros": 0}]
        self.invest(base(bancos=BANCOS, investimentos=[PRE], historico=hist), ui={"invModo": "evolucao"})
        self.assertIn("l-hist", classes(), "a linha do que foi registrado")
        self.assertIn("hoje", self.js("[...document.querySelectorAll('#ch-evo svg text')].map(t => t.textContent)"))
        self.assertEqual(self.textos("#app .leg span")[0], "Registrado")

    def test_tocar_no_grafico_mostra_os_valores(self):
        self.invest(base(bancos=BANCOS, investimentos=[PRE]), ui={"invModo": "evolucao", "gAnos": 5})
        svg = self.pg.locator("#ch-evo svg")
        w = svg.bounding_box()["width"]
        svg.click(position={"x": w - 11, "y": 100})
        self.assertEqual(self.texto("#ch-evo .tip").split("\n"),
                         ["nov/31 · projetado", "R$ 17.623", "Projetado", "R$ 10.000", "Valor investido", brl(10000 * 1.12 ** 5 / 1.045 ** 5, 0), "Em dinheiro de hoje"])
        svg.click(position={"x": 52, "y": 100})
        self.assertEqual(self.texto("#ch-evo .tip").split("\n")[:3], ["Hoje", "R$ 10.000", "Projetado"])

    def test_tabela_por_ano(self):
        self.invest(base(bancos=BANCOS, investimentos=[PRE]), ui={"invModo": "evolucao", "gAnos": 5})
        self.clicar("#app details.card summary")
        self.assertEqual(self.textos("#app .tabela thead th"), ["Quando", "Projetado", "Rendeu", "Em dinheiro de hoje"])
        linhas = self.js("[...document.querySelectorAll('#app .tabela tbody tr')].map(r => [...r.cells].map(c => c.textContent))")
        esperado = [[f"nov/{27 + k - 1}", brl(10000 * 1.12 ** k, 0), brl(10000 * 1.12 ** k - 10000, 0), brl(10000 * 1.12 ** k / 1.045 ** k, 0)] for k in range(1, 6)]
        self.assertEqual(linhas, esperado)


# ---------------------------------------------------------------------------------------------------------------
class TestDivisao(_TelaInvest):
    def test_divisao_por_banco(self):
        self.invest(ui={"invModo": "divisao"})
        self.assertEqual(self.textos('#app [data-k="gAgrup"]'), ["Banco", "De quem", "Tipo", "Liquidez"])
        self.assertEqual(self.texto('#app [data-k="gAgrup"].on'), "Banco")
        azul = RENDE["cdb"] + RENDE["tes"] + RENDE["cx"]
        verde = RENDE["lci"] + RENDE["poup"]
        self.assertEqual(self.comps(), [("Banco Azul", f"3 investimentos · ≈ {brl(azul, 0)}/mês", "R$ 12.800", "65,3%"),
                                        ("Banco Verde", f"2 investimentos · ≈ {brl(verde, 0)}/mês", "R$ 6.500", "33,2%"),
                                        ("Sem banco", "1 investimento · ≈ R$ 0/mês", "R$ 300", "1,5%")])
        self.assertEqual(self.stat(), [("Total", "R$ 19.600", ""), ("Rende por mês", brl(sum(RENDE.values()), 0), "")])
        partes = self.js("[...document.querySelectorAll('#app .pilha i')].map(i => +i.style.flexGrow)")
        self.assertEqual([round(p, 4) for p in partes], [round(12800 / 19600, 4), round(6500 / 19600, 4), round(300 / 19600, 4)], "a barra na proporção")

    def test_divisao_por_dono_tipo_e_liquidez(self):
        self.invest(ui={"invModo": "divisao"})
        casos = {"dono": [("Seu", "R$ 17.300", "88,3%"), ("Beto", "R$ 1.500", "7,7%"), ("Carla", "R$ 800", "4,1%")],
                 "tipo": [("CDB", "R$ 10.000", "51,0%"), ("LCI/LCA", "R$ 5.000", "25,5%"), ("Tesouro", "R$ 2.000", "10,2%"),
                          ("Poupança", "R$ 1.500", "7,7%"), ("Caixinha", "R$ 800", "4,1%"), ("Dinheiro", "R$ 300", "1,5%")],
                 "liq": [("Só no vencimento", "R$ 15.000", "76,5%"), ("Liquidez diária", "R$ 4.600", "23,5%")]}
        for agrup, esperado in casos.items():
            with self.subTest(agrup):
                self.clicar(f'#app [data-k="gAgrup"][data-v="{agrup}"]')
                self.assertEqual([(n, v, p) for n, _, v, p in self.comps()], esperado)

    def test_tocar_numa_parte_mostra_o_valor(self):
        self.invest(ui={"invModo": "divisao"})
        self.assertEqual(self.texto("#app .pilha-cap"), "Toque numa parte para ver o valor")
        self.clicar('#app .comp[data-v="b-verde"]')
        self.assertEqual(self.texto("#app .pilha-cap"), "Banco Verde · R$ 6.500 · 33,2%")
        self.assertEqual(self.conta('#app .comp.on[data-v="b-verde"]'), 1)
        self.clicar('#app .pilha i[data-v="b-azul"]')
        self.assertEqual(self.texto("#app .pilha-cap"), "Banco Azul · R$ 12.800 · 65,3%", "na barra também")
        self.clicar('#app .pilha i[data-v="b-azul"]')
        self.assertEqual(self.texto("#app .pilha-cap"), "Toque numa parte para ver o valor", "tocar de novo desmarca")
        self.clicar('#app .comp[data-v="b-verde"]')
        self.clicar('#app [data-k="gAgrup"][data-v="tipo"]')
        self.assertEqual(self.texto("#app .pilha-cap"), "Toque numa parte para ver o valor", "trocar o agrupamento desmarca")

    def test_maior_banco_do_inicio_abre_a_divisao(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS), ui={"tab": "inicio", "invModo": "carteira", "gAgrup": "tipo", "gEscopo": "meu"})
        linha = '#app .hl-row[data-a="graf-comp"]'
        self.assertEqual(self.textos(linha + " .hl-k, " + linha + " .hl-v"), ["Maior banco", "Banco Azul"])
        self.assertEqual(self.texto(linha + " .hl-n"), "65%\nR$ 12.800")
        self.clicar(linha)
        self.assertEqual(self.js("[T.S.ui.tab, T.S.ui.invModo, T.S.ui.gAgrup, T.S.ui.gEscopo]"), ["investimentos", "divisao", "banco", "tudo"])
        self.assertEqual(self.comps()[0][0], "Banco Azul")


# ---------------------------------------------------------------------------------------------------------------
# Divisão › Liquidez › Vencimentos (1.65.0): quando o dinheiro de Só no vencimento libera, por ano ou por mês, com o valor de hoje
VELHO = inv("velho", "CDB que já venceu", 3000, "cdi_pct", 100, banco="b-azul", vencimento="2026-10-01")
DEZ = inv("dez", "CDB de dezembro", 4000, "cdi_pct", 105, banco="b-verde", vencimento="2026-12-10")
LCA = inv("lca", "LCA Verde", 7000, "cdi_pct", 92, banco="b-verde", tipo="lci", vencimento="2027-09-20")
IPCA35 = inv("ipca", "Tesouro IPCA+ 2035", 9000, "ipca_mais", 6.5, banco="b-azul", tipo="tesouro", vencimento="2035-05-15")
SELIC29 = inv("selic29", "Tesouro Selic 2029", 6000, "selic_mais", 0, banco="b-azul", tipo="tesouro", liquidez="diaria", vencimento="2029-03-01")
COM_DATA = INVS + [VELHO, DEZ, LCA, IPCA35, SELIC29]
# por ano: 2026 = 3.000 + 4.000 · 2027 = 5.000 (LCI) + 7.000 · 2028 = 10.000 (CDB) · 2035 = 9.000
# o Tesouro Selic 2029 tem data, mas liquidez diária: o dinheiro já está livre, não entra


class TestVencimentos(_TelaInvest):
    CARD = "#app .venc-card"

    def liq(self, invs=COM_DATA, **ui):
        self.invest(base(bancos=BANCOS, investimentos=invs), ui=dict({"invModo": "divisao", "gAgrup": "liq"}, **ui))

    def cap(self):
        return self.texto(self.CARD + " .venc-cap")

    def lista(self):
        """As linhas: (nome, banco · tipo, valor, quando)."""
        return [tuple(x) for x in self.js("[...document.querySelectorAll('#app .venc-it')].map(c => [c.querySelector('.nm b').textContent, "
                                          "c.querySelector('.sub').textContent, c.querySelector('.vl').firstChild.textContent, c.querySelector('.vl small').textContent])")]

    def barras(self):
        """As colunas: (v do data-v, aria-label, apertada, desligada)."""
        return [tuple(x) for x in self.js("[...document.querySelectorAll('#app .venc-bar')].map(b => [b.dataset.v, b.getAttribute('aria-label'), "
                                          "b.getAttribute('aria-pressed'), b.disabled])")]

    def test_so_na_liquidez_e_so_com_alguma_data(self):
        self.liq(gAgrup="banco")
        self.assertEqual(self.conta(self.CARD), 0, "por banco, não")
        self.clicar('#app [data-k="gAgrup"][data-v="liq"]')
        self.assertEqual(self.conta(self.CARD), 1)
        self.assertEqual(self.texto(self.CARD + " .g-tit"), "Vencimentos")
        self.assertEqual(self.comps()[0][0], "Só no vencimento", "a divisão por liquidez continua igual, em cima")
        self.liq([TES, DIN, POUP, CX])
        self.assertEqual(self.conta(self.CARD), 0, "nenhum com data: não aparece")
        self.liq([TES, SELIC29])
        self.assertEqual(self.conta(self.CARD), 0, "só de liquidez diária, mesmo com data: o dinheiro já está livre")
        self.liq(gEscopo="terc")
        self.assertEqual(self.conta(self.CARD), 0, "De terceiros: só os deles, e nenhum tem data")

    def test_por_ano(self):
        self.liq()
        self.assertEqual(self.textos(self.CARD + ' [data-k="ano"]'), ["Por ano", "Por mês"])
        self.assertEqual(self.texto(self.CARD + ' [data-k="ano"].on'), "Por ano")
        self.assertEqual(self.cap(), "Com vencimento · R$ 38.000 · 6 investimentos")
        self.assertEqual(self.barras(), [("2026", "2026: R$ 7.000, 2 investimentos", "false", False), ("2027", "2027: R$ 12.000, 2 investimentos", "false", False),
                                         ("2028", "2028: R$ 10.000, 1 investimento", "false", False), ("2035", "2035: R$ 9.000, 1 investimento", "false", False)])
        self.assertEqual(self.textos(self.CARD + " .venc-bar small"), ["7\xa0mil", "12\xa0mil", "10\xa0mil", "9\xa0mil"], "o valor em cima de cada coluna (o espaço que não quebra)")
        self.assertEqual(self.textos(self.CARD + " .venc-eixo span"), ["2026", "2027", "2028", "2035"], "só os anos com vencimento")
        self.assertEqual(self.textos(self.CARD + " .venc-eixo .hoje"), ["2026"], "este ano em destaque")
        alturas = self.js("[...document.querySelectorAll('#app .venc-bar i')].map(i => parseFloat(i.style.height))")
        self.assertEqual(alturas, [round(7000 / 12000 * 80), 80, round(10000 / 12000 * 80), round(9000 / 12000 * 80)], "na proporção do maior")
        self.assertEqual(self.lista(), [("CDB que já venceu", "Banco Azul · Ana · CDB", "R$ 3.000", "venceu 01/10/2026"),
                                        ("CDB de dezembro", "Banco Verde · CDB", "R$ 4.000", "vence 10/12/2026"),
                                        ("LCI Verde", "Banco Verde · LCI/LCA", "R$ 5.000", "vence 01/06/2027"),
                                        ("LCA Verde", "Banco Verde · LCI/LCA", "R$ 7.000", "vence 20/09/2027"),
                                        ("CDB Azul 2028", "Banco Azul · Ana · CDB", "R$ 10.000", "vence 15/03/2028"),
                                        ("Tesouro IPCA+ 2035", "Banco Azul · Ana · Tesouro", "R$ 9.000", "vence 15/05/2035")], "em ordem de data")
        self.assertEqual(self.conta('#app .venc-it .vl small.alerta'), 1, "o que já venceu em vermelho")
        self.assertTrue(self.cabe(self.CARD + " .venc-it .vl, " + self.CARD + " .venc-bar small"), "nenhum número cortado")

    def test_tocar_num_ano_mostra_o_valor_e_os_dele(self):
        self.liq()
        self.clicar(self.CARD + ' .venc-bar[data-v="2027"]')
        self.assertEqual(self.cap(), "2027 · R$ 12.000 · 2 investimentos")
        self.assertEqual([n for n, *_ in self.lista()], ["LCI Verde", "LCA Verde"])
        self.assertEqual([p for _, _, p, _ in self.barras()], ["false", "true", "false", "false"])
        self.assertEqual(self.conta(self.CARD + " .venc-chart.sel"), 1, "as outras colunas apagadas")
        self.clicar(self.CARD + ' .venc-bar[data-v="2027"]')
        self.assertEqual(self.cap(), "Com vencimento · R$ 38.000 · 6 investimentos", "tocar de novo desmarca")
        self.assertEqual(len(self.lista()), 6)

    def test_por_mes(self):
        self.liq()
        self.clicar(self.CARD + ' .venc-bar[data-v="2027"]')
        self.clicar(self.CARD + ' [data-k="ano"]:text-is("Por mês")')
        self.assertEqual(self.texto(self.CARD + ' [data-k="ano"].on'), "Por mês")
        self.assertEqual(self.texto(self.CARD + " .mes-nome"), "2027", "abre o ano marcado")
        self.assertEqual(self.textos(self.CARD + " .venc-eixo span"), ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"])
        self.assertEqual(self.textos(self.CARD + " .venc-eixo .hoje"), [], "nov/26 não está em 2027")
        b = self.barras()
        self.assertEqual([x for x in b if not x[3]], [("2027-06", "Junho de 2027: R$ 5.000, 1 investimento", "false", False),
                                                      ("2027-09", "Setembro de 2027: R$ 7.000, 1 investimento", "false", False)])
        self.assertEqual(b[0], ("2027-01", "Janeiro de 2027: nada vence", "false", True), "mês sem nada: sem coluna e sem toque")
        self.assertEqual(self.textos(self.CARD + " .venc-bar small"), [], "por mês, sem o valor em cima (não cabe)")
        self.assertEqual(self.cap(), "2027 · R$ 12.000 · 2 investimentos")
        self.clicar(self.CARD + ' .venc-bar[data-v="2027-09"]')
        self.assertEqual(self.cap(), "Setembro de 2027 · R$ 7.000 · 1 investimento")
        self.assertEqual([n for n, *_ in self.lista()], ["LCA Verde"])
        # ‹ › passam pelos anos com vencimento (2028 e depois 2035, sem os do meio)
        self.clicar(self.CARD + ' [aria-label="Próximo ano com vencimento"]')
        self.assertEqual((self.texto(self.CARD + " .mes-nome"), self.cap()), ("2028", "2028 · R$ 10.000 · 1 investimento"), "trocar de ano desmarca o mês")
        self.clicar(self.CARD + ' [aria-label="Próximo ano com vencimento"]')
        self.assertEqual(self.texto(self.CARD + " .mes-nome"), "2035")
        self.assertTrue(self.pg.locator(self.CARD + ' [aria-label="Próximo ano com vencimento"]').is_disabled(), "o último")
        for _ in range(3):
            self.clicar(self.CARD + ' [aria-label="Ano anterior com vencimento"]')
        self.assertEqual(self.texto(self.CARD + " .mes-nome"), "2026")
        self.assertTrue(self.pg.locator(self.CARD + ' [aria-label="Ano anterior com vencimento"]').is_disabled(), "o primeiro")
        self.assertEqual(self.textos(self.CARD + " .venc-eixo .hoje"), ["nov"], "este mês em destaque")
        self.clicar(self.CARD + ' [data-k="ano"]:text-is("Por ano")')
        self.assertEqual((self.conta(self.CARD + " .mes-nome"), self.cap()), (0, "Com vencimento · R$ 38.000 · 6 investimentos"))

    def test_por_mes_sem_ano_marcado_abre_o_proximo_vencimento(self):
        antigo = inv("antigo", "CDB de 2025", 2000, "cdi_pct", 100, banco="b-azul", vencimento="2025-04-10")
        self.liq(INVS + [antigo])
        self.assertEqual(self.textos(self.CARD + " .venc-eixo span"), ["2025", "2027", "2028"])
        self.clicar(self.CARD + ' [data-k="ano"]:text-is("Por mês")')
        self.assertEqual(self.texto(self.CARD + " .mes-nome"), "2027", "o primeiro a partir deste ano, não o que já passou")
        self.liq([antigo])
        self.clicar(self.CARD + ' [data-k="ano"]:text-is("Por mês")')
        self.assertEqual(self.texto(self.CARD + " .mes-nome"), "2025", "só um que já passou: ele mesmo")

    def test_ano_guardado_e_ano_que_sumiu(self):
        self.liq()
        self.clicar(self.CARD + ' [data-k="ano"]:text-is("Por mês")')
        self.assertEqual(self.texto(self.CARD + " .mes-nome"), "2026")
        self.clicar(self.CARD + ' [aria-label="Próximo ano com vencimento"]')
        self.assertEqual(self.ui_guardada().get("gVenc"), "2027", "fica guardado, como os outros filtros")
        self.liq(gVenc="2031")
        self.assertEqual(self.texto(self.CARD + " .mes-nome"), "2026", "um ano sem vencimento volta para o próximo")

    def test_muitos_anos_sem_o_valor_em_cima(self):
        anos = [inv(f"a{a}", f"CDB {a}", 1000, "cdi_pct", 100, vencimento=f"{a}-01-15") for a in range(2027, 2036)]
        self.liq(anos)
        self.assertEqual(len(self.barras()), 9)
        self.assertEqual(self.textos(self.CARD + " .venc-bar small"), [], "9 colunas: o valor fica no toque")
        self.clicar(self.CARD + ' .venc-bar[data-v="2030"]')
        self.assertEqual(self.cap(), "2030 · R$ 1.000 · 1 investimento")

    def test_tocar_na_linha_abre_o_investimento(self):
        self.liq()
        self.clicar('#app .venc-it[data-id="lca"]')
        self.assertEqual(self.folha(), "Editar investimento")
        self.assertEqual(self.pg.input_value('.folha #f-nome'), "LCA Verde")

    def test_olho_esconde_os_valores(self):
        self.liq()
        self.clicar('#app [data-a="olho"]')
        self.assertEqual(self.cap(), "Com vencimento · R$ ••••• · 6 investimentos")
        self.assertEqual(set(self.textos(self.CARD + " .venc-bar small")), {"•••"})
        self.assertEqual({v for _, _, v, _ in self.lista()}, {"R$ •••••"})


class TestVencimentos320(TestVencimentos):
    """Os mesmos, no celular pequeno (320 px), e os nomes dos 12 meses cabem cada um na sua coluna."""
    LARGURA = 320

    def test_os_meses_cabem(self):
        self.liq(gVenc="2027")
        larguras = self.js("[...document.querySelectorAll('#app .venc-eixo span')].map(e => { const r = document.createRange(); r.selectNodeContents(e); "
                           "return [r.getBoundingClientRect().width, e.getBoundingClientRect().width]; })")
        self.assertEqual(len(larguras), 12)
        self.assertTrue(all(t <= c for t, c in larguras), larguras)
        self.assertEqual(self.js("document.documentElement.scrollWidth"), 320, "nada passa da largura")


# ---------------------------------------------------------------------------------------------------------------
class TestGuardadoEDesligado(_TelaInvest):
    def test_filtros_e_abas_ficam_guardados(self):
        self.invest()
        self.clicar('#app [data-a="filtro"][data-v="terc"]')
        self.modo("divisao")
        self.clicar('#app [data-k="gAgrup"][data-v="tipo"]')
        self.modo("evolucao")
        self.clicar('#app [data-k="gAnos"][data-v="10"]')
        self.clicar('#app [data-k="gEscopo"][data-v="meu"]')
        ui = self.ui_guardada()
        self.assertEqual({k: ui.get(k) for k in ("tab", "filtro", "invModo", "gAgrup", "gAnos", "gEscopo")},
                         {"tab": "investimentos", "filtro": "terc", "invModo": "evolucao", "gAgrup": "tipo", "gAnos": 10, "gEscopo": "meu"})

    def test_descontar_ir_e_ocultar_bens_nao_ficam_guardados(self):
        self.invest(base(bancos=BANCOS, investimentos=INVS), ui={"invModo": "evolucao"}, bens=BENS)
        self.clicar('#app [data-k="gIR"]')
        self.clicar('#app [data-k="gSemBens"]')
        self.assertEqual(self.js("[T.S.ui.gIR, T.S.ui.gSemBens]"), [True, True], "ligados agora")
        ui = self.ui_guardada()
        self.assertNotIn("gIR", ui)
        self.assertNotIn("gSemBens", ui)

    def test_reabrir_o_app_comeca_sem_ir_e_sem_ocultar_bens(self):
        """Mesmo que tenham ficado guardados (versões até a 1.23.0 guardavam), ao abrir os dois começam desligados; o resto volta."""
        self.invest()
        guardado = {"tab": "investimentos", "filtro": "terc", "invModo": "evolucao", "gEscopo": "meu", "gAnos": 10, "gAgrup": "tipo", "gIR": True, "gSemBens": True}
        self.js("(localStorage.setItem('gerencia.ui', JSON.stringify(a)), true)", guardado)
        p2 = self.ctx.new_page()
        try:
            p2.on("pageerror", lambda e: self.erros.append(str(e)))
            p2.add_init_script("window.GERENCIA_DEMO = true; window.GERENCIA_TESTE = true;")
            p2.goto(INDEX)
            p2.wait_for_function("window.GERENCIA_TESTE && window.GERENCIA_TESTE.S && window.GERENCIA_TESTE.S.d && document.querySelector('#app .seg')")
            ui = p2.evaluate("() => { const u = window.GERENCIA_TESTE.S.ui; return [u.gIR, u.gSemBens, u.filtro, u.invModo, u.gEscopo, u.gAnos, u.gAgrup]; }")
            self.assertEqual(ui, [False, False, "terc", "evolucao", "meu", 10, "tipo"])
            self.assertEqual(p2.locator('[data-k="gIR"]').count(), 1)
            self.assertEqual(p2.locator('[data-k="gIR"].on').count(), 0, "a chave aparece desligada")
        finally:
            p2.close()


# ---------------------------------------------------------------------------------------------------------------
class TestEsconderValores(_TelaInvest):
    def test_olho_esconde_os_valores_da_carteira(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS))
        self.js("(localStorage.setItem('gerencia.oculto', 'false'), true)")
        self.clicar('#app [data-a="olho"]')
        self.assertTrue(self.js("JSON.parse(localStorage.getItem('gerencia.oculto'))"), "fica guardado")
        self.ir("investimentos")
        self.assertEqual(set(self.textos("#app .inv-valor")), {"R$ •••••"})
        self.assertEqual(self.resumo(), ("6 investimentos · rende ≈ R$ •••••/mês", "R$ •••••"))
        self.assertNotRegex(" ".join(self.textos("#app .inv-pe")), r"\d+,\d\d", "nenhum valor no pé dos cartões")

    def test_olho_esconde_evolucao_divisao_e_grafico(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS))
        self.clicar('#app [data-a="olho"]')
        self.ir("investimentos")
        self.modo("evolucao")
        self.assertEqual({v for _, v, _ in self.stat()}, {"R$ •••••"})
        eixo = self.js("[...document.querySelectorAll('#ch-evo svg text')].map(t => t.textContent).filter(t => t !== 'hoje' && !/^(\\d{4}|[a-z]{3}\\/\\d\\d)$/.test(t))")
        self.assertTrue(eixo and set(eixo) == {"•••"}, f"os números do eixo também ({eixo})")
        self.modo("divisao")
        self.assertEqual({v for _, _, v, _ in self.comps()}, {"R$ •••••"})


# ---------------------------------------------------------------------------------------------------------------
class TestFormulario(_TelaInvest):
    def test_novo_na_aba_invest_ja_vem_com_a_pessoa_filtrada(self):
        self.novo(base(bancos=BANCOS, investimentos=INVS), ui={"filtro": "terc", "pessoa": "Carla"})
        self.assertEqual(self.texto(".folha .dono-seg button.on"), "De terceiros")
        self.assertEqual(self.pg.input_value('.folha [data-f="terceiro"]'), "Carla")

    def test_criar_cdb_no_percentual_do_cdi(self):
        self.novo()
        self.assertEqual(self.texto('.folha [data-a="f-tipo"].on'), "CDB")
        self.assertEqual(self.texto('.folha [data-a="f-idx"].on'), "% do CDI")
        self.assertEqual(self.pg.input_value('.folha [data-f="taxa"]'), "100")
        self.assertEqual(self.texto('.folha [data-a="f-banco"].on'), "Banco Azul · Ana", "o primeiro banco, na conta de quem usa o app")
        self.preencher("#f-nome", "CDB Azul 2029")
        self.digitar("#f-valor", "1000000")
        self.assertEqual(self.pg.input_value("#f-valor"), "10.000,00", "os números entram como centavos")
        self.preencher('.folha [data-f="taxa"]', "120")
        self.assertEqual(self.texto("#aj-taxa"), f"≈ 16,38% ao ano hoje, com CDI de 13,65% · rende ≈ {brl(rende_mes(10000, 0.1638))} por mês")
        self.clicar(SALVAR)
        self.assertEqual(self.aviso(), "Investimento cadastrado")
        self.assertIsNone(self.folha())
        i = self.salvo("CDB Azul 2029")
        self.assertEqual({k: i[k] for k in ("tipo", "banco", "valor", "data_valor", "indexador", "taxa", "liquidez", "vencimento", "titular", "terceiro")},
                         {"tipo": "cdb", "banco": "b-azul", "valor": 10000, "data_valor": HOJE_ISO, "indexador": "cdi_pct", "taxa": 120,
                          "liquidez": "vencimento", "vencimento": None, "titular": "meu", "terceiro": ""})
        self.assertEqual(self.nomes(), ["CDB Azul 2029"], "aparece na Carteira")

    def test_rendimentos_com_taxa(self):
        casos = [("cdi_mais", "1,5", ["CDI +", "% a.a."], "≈ 15,35% ao ano hoje, com CDI de 13,65%", 1.5, "CDI + 1,5% a.a."),
                 ("ipca_mais", "6", ["IPCA +", "% a.a."], "≈ 10,77% ao ano hoje, com IPCA de 4,5%", 6, "IPCA + 6% a.a."),
                 ("pre", "13,5", ["% a.a."], "≈ 13,5% ao ano hoje, com taxa fixa", 13.5, "13,5% a.a. pré"),
                 ("selic_mais", None, ["Selic +", "% a.a."], "≈ 13,75% ao ano hoje, com Selic de 13,75%", 0, "Selic")]
        for idx, digitado, pref, ajuda, salva, rotulo in casos:
            with self.subTest(idx):
                self.novo()
                self.clicar(f'.folha [data-a="f-idx"][data-v="{idx}"]')
                self.assertEqual(self.textos('.folha .pref:has([data-f="taxa"]) span'), pref)
                self.assertEqual(self.pg.input_value('.folha [data-f="taxa"]'), "0" if idx == "selic_mais" else "", "a taxa começa vazia (Selic + 0)")
                if digitado:
                    self.preencher('.folha [data-f="taxa"]', digitado)
                self.assertEqual(self.texto("#aj-taxa"), ajuda)
                self.preencher("#f-nome", "Teste " + idx)
                self.digitar("#f-valor", "100000")
                self.clicar(SALVAR)
                self.assertIsNone(self.folha(), "salvou (Selic + 0 vale)")
                i = self.salvo()
                self.assertEqual((i["indexador"], i["taxa"]), (idx, salva))
                self.assertEqual(self.textos(f'#app .inv[data-id="{i["id"]}"] .tag.taxa'), [rotulo])

    def test_rendimentos_sem_taxa(self):
        self.novo()
        self.clicar('.folha [data-a="f-tipo"][data-v="poupanca"]')
        self.assertEqual(self.texto('.folha [data-a="f-idx"].on'), "Poupança")
        self.assertEqual(self.conta('.folha [data-f="taxa"]'), 0, "poupança não pede taxa")
        self.assertEqual(self.texto('.folha [data-k="liquidez"].on'), "Diária")
        # Selic acima de 8,5%: 0,5% ao mês + TR → (1,005 × 1,001)^12 − 1 = 7,45% a.a.
        self.assertAlmostEqual(taxa("poupanca") * 100, 7.45, places=2)
        self.assertEqual(self.texto("#aj-taxa"), "≈ 7,45% ao ano hoje, com Selic de 13,75% e TR de 0,1% a.m.")
        self.digitar("#f-valor", "100000")
        self.clicar(SALVAR)
        self.assertEqual({k: self.salvo()[k] for k in ("tipo", "indexador", "taxa", "liquidez")}, {"tipo": "poupanca", "indexador": "poupanca", "taxa": 0, "liquidez": "diaria"})
        # sem rendimento
        self.novo()
        self.clicar('.folha [data-a="f-idx"][data-v="parado"]')
        self.assertEqual(self.conta('.folha [data-f="taxa"]'), 0)
        self.assertEqual(self.texto("#aj-taxa"), "O valor fica parado, sem render.")
        self.digitar("#f-valor", "50000")
        self.clicar(SALVAR)
        i = self.salvo()
        self.assertEqual((i["indexador"], i["taxa"]), ("parado", 0))
        self.assertEqual(self.textos(f'#app .inv[data-id="{i["id"]}"] .inv-pe span')[0], "Não rende")

    def test_ouro_vem_com_estimado_de_10(self):
        self.novo()
        self.clicar('.folha [data-a="f-tipo"][data-v="ouro"]')
        self.assertEqual(self.texto('.folha [data-a="f-idx"].on'), "Estimado")
        self.assertEqual(self.pg.input_value('.folha [data-f="taxa"]'), "10")
        self.assertEqual(self.texto("#aj-taxa"), "Estimativa sua, ≈ 10% a.a. Entra na projeção, mas o valor de hoje não é corrigido sozinho.")
        self.preencher("#f-nome", "Ouro 10 g")
        self.digitar("#f-valor", "860000")
        self.clicar(SALVAR)
        i = self.salvo("Ouro 10 g")
        self.assertEqual((i["tipo"], i["indexador"], i["taxa"], i["liquidez"], i["valor"]), ("ouro", "estimado", 10, "diaria", 8600))
        self.assertEqual(self.textos('#app .inv[data-id="%s"] .tag.taxa' % i["id"]), ["≈ 10% a.a. estimado"])

    def test_dinheiro_so_pede_nome_e_valor(self):
        self.novo()
        self.clicar('.folha [data-a="f-tipo"][data-v="dinheiro"]')
        for rot in ("Banco", "Rendimento", "Liquidez"):
            self.assertFalse(self.visivel(rot), f"sem {rot}")
        self.assertFalse(self.pg.locator("#f-venc").is_visible(), "sem vencimento")
        self.assertEqual(self.pg.get_attribute("#f-nome", "placeholder"), "Ex.: Dinheiro em casa")
        self.preencher("#f-nome", "Cofre")
        self.digitar("#f-valor", "150000")
        self.clicar(SALVAR)
        i = self.salvo("Cofre")
        self.assertEqual((i["tipo"], i["banco"], i["indexador"], i["taxa"], i["vencimento"]), ("dinheiro", "", "parado", 0, None))
        self.assertEqual(self.texto(f'#app .inv[data-id="{i["id"]}"] .inv-meta'), "Em espécie")

    # (era bug até a 1.24.0)
    def test_sem_nome_dinheiro_e_bens_nao_levam_banco_no_nome(self):
        for tipo, nome in (("dinheiro", "Dinheiro"), ("bens", "Bens")):
            with self.subTest(tipo):
                self.novo()
                self.clicar(f'.folha [data-a="f-tipo"][data-v="{tipo}"]')
                self.digitar("#f-valor", "100000")
                self.clicar(SALVAR)
                self.assertEqual(self.salvo()["nome"], nome)

    def test_sem_nome_usa_o_tipo_e_o_banco(self):
        self.novo()
        self.clicar('.folha [data-a="f-tipo"][data-v="lci"]')
        self.clicar('.folha [data-a="f-banco"][data-v="b-verde"]')
        self.digitar("#f-valor", "100000")
        self.clicar(SALVAR)
        self.assertEqual((self.salvo()["nome"], self.salvo()["banco"]), ("LCI/LCA Banco Verde", "b-verde"))

    def test_bens_por_categoria(self):
        self.novo()
        self.clicar('.folha [data-a="f-tipo"][data-v="bens"]')
        for rot in ("Banco", "Rendimento", "Liquidez"):
            self.assertFalse(self.visivel(rot), f"sem {rot}")
        self.assertTrue(self.visivel("Categoria"))
        self.assertEqual(self.texto('.folha [data-k="categoria_bem"].on'), "Outros")
        ajuda = lambda: self.texto('.folha .campo:has(> .lbl:text-is("Categoria")) .ajuda')
        self.assertEqual(ajuda(), "Perde 10% por ano. As taxas ficam em Mais › Invest.")
        self.clicar('.folha [data-k="categoria_bem"][data-v="imoveis"]')
        self.assertEqual(ajuda(), "Mantém o valor. As taxas ficam em Mais › Invest.")
        self.clicar('.folha [data-k="categoria_bem"][data-v="veiculos"]')
        self.assertEqual(ajuda(), "Perde 15% por ano. As taxas ficam em Mais › Invest.")
        self.preencher("#f-nome", "Moto")
        self.digitar("#f-valor", "6000000")
        self.clicar(SALVAR)
        i = self.salvo("Moto")
        self.assertEqual({k: i.get(k) for k in ("tipo", "indexador", "taxa", "categoria_bem", "banco", "liquidez", "vencimento")},
                         {"tipo": "bens", "indexador": "deprecia", "taxa": 15, "categoria_bem": "veiculos", "banco": "", "liquidez": "diaria", "vencimento": None})
        c = f'#app .inv[data-id="{i["id"]}"]'
        self.assertEqual(self.texto(c + " .inv-meta"), "Bens · Veículos")
        self.assertEqual(self.textos(c + " .tag.taxa"), ["perde 15% a.a."])
        self.assertEqual(self.textos(c + " .inv-pe span")[0], f"perde ≈ {brl(60000 * (1 - 0.85 ** (1 / 12)))} por mês")

    # (era bug até a 1.28.0: com Corrigir valores pelo rendimento desligado, a ajuda dizia que o valor ia mudar daqui para a frente)
    def test_ajuda_do_valor_segue_corrigir_valores(self):
        self.novo()
        self.assertEqual(self.texto("#aj-valor"), "O saldo de hoje; o rendimento conta daqui para a frente.")
        self.clicar('.folha [data-a="f-tipo"][data-v="bens"]')
        self.assertEqual(self.texto("#aj-valor"), "O valor de hoje; a taxa da categoria conta daqui para a frente.")
        self.novo(base(bancos=BANCOS, ajustes={"corrigir": False}))
        self.assertEqual(self.texto("#aj-valor"), "O saldo de hoje.")
        self.clicar('.folha [data-a="f-tipo"][data-v="bens"]')
        self.assertEqual(self.texto("#aj-valor"), "O valor de hoje.")

    def test_bens_separado_por_categoria(self):
        self.novo()
        self.clicar('.folha [data-a="f-tipo"][data-v="bens"]')
        self.clicar('.folha [data-a="f-dividir"][data-v="1"]')
        self.assertEqual(self.conta(".folha [data-fparte]"), 15, "uma linha por categoria")
        self.assertIsNotNone(self.pg.get_attribute("#f-valor", "readonly"), "o total é a soma")
        self.digitar('.folha [data-fparte="imoveis"]', "50000000")
        self.digitar('.folha [data-fparte="moveis"]', "2000000")
        self.assertEqual(self.pg.input_value("#f-valor"), "520.000,00")
        self.assertEqual(self.texto("#partes-soma"), "Total: R$ 520.000,00. As taxas ficam em Mais › Invest.")
        self.preencher("#f-nome", "Casa da praia")
        self.clicar(SALVAR)
        i = self.salvo("Casa da praia")
        self.assertEqual([(p["categoria"], p["valor"], p["taxa"]) for p in i["partes"]], [("imoveis", 500000, 0), ("moveis", 20000, 10)])
        self.assertEqual((i["valor"], i["taxa"], i["categoria_bem"]), (520000, 0.38, "varias"), "taxa = média pesada pelo valor")
        self.assertEqual(self.texto(f'#app .inv[data-id="{i["id"]}"] .inv-meta'), "Bens · 2 categorias")
        # reabrir: as partes voltam
        self.editar(i["id"])
        self.assertEqual([self.pg.input_value(f'.folha [data-fparte="{k}"]') for k in ("imoveis", "moveis", "veiculos")], ["500.000,00", "20.000,00", ""])

    def test_erro_sem_valor(self):
        self.novo()
        self.clicar(SALVAR)
        self.assertEqual(self.textos(".folha .msg-erro"), ["Coloque o valor."])
        self.assertEqual(self.conta('.folha .pref.erro:has(#f-valor)'), 1)
        self.assertEqual(self.aviso(), "Falta preencher 1 campo")
        self.assertEqual(self.folha(), "Novo investimento")
        self.assertEqual(self.dados()["investimentos"], [])

    def test_erro_sem_taxa(self):
        self.novo()
        self.clicar('.folha [data-a="f-idx"][data-v="ipca_mais"]')
        self.digitar("#f-valor", "100000")
        self.clicar(SALVAR)
        self.assertEqual(self.textos(".folha .msg-erro"), ["Coloque a taxa."])
        self.assertEqual(self.aviso(), "Falta preencher 1 campo")
        self.assertEqual(self.dados()["investimentos"], [])

    def test_erro_de_terceiros_sem_dizer_de_quem(self):
        self.novo()
        self.clicar('.folha [data-a="f-set"][data-k="titular"][data-v="terceiros"]')
        self.assertEqual(self.pg.get_attribute('.folha [data-f="terceiro"]', "placeholder"), "De quem? Ex.: Mãe, Pedro, condomínio")
        self.clicar(SALVAR)
        self.assertEqual(sorted(self.textos(".folha .msg-erro")), ["Coloque o valor.", "Diga de quem é."])
        self.assertEqual(self.aviso(), "Falta preencher 2 campos")

    def test_de_terceiros_salva_o_dono(self):
        self.novo(base(bancos=BANCOS, investimentos=[POUP]))
        self.clicar('.folha [data-a="f-set"][data-k="titular"][data-v="terceiros"]')
        self.assertEqual(self.textos('.folha [data-a="f-set"][data-k="terceiro"]'), ["Beto"], "quem já tem dinheiro aqui")
        self.clicar('.folha [data-a="f-set"][data-k="terceiro"][data-v="Beto"]')
        self.assertEqual(self.pg.input_value('.folha [data-f="terceiro"]'), "Beto")
        self.digitar("#f-valor", "100000")
        self.preencher("#f-nome", "CDB do Beto")
        self.clicar(SALVAR)
        self.assertEqual((self.salvo("CDB do Beto")["titular"], self.salvo("CDB do Beto")["terceiro"]), ("terceiros", "Beto"))
        # digitado, sem os espaços
        self.novo()
        self.clicar('.folha [data-a="f-set"][data-k="titular"][data-v="terceiros"]')
        self.preencher('.folha [data-f="terceiro"]', "  Carla ")
        self.digitar("#f-valor", "100000")
        self.preencher("#f-nome", "CDB da Carla")
        self.clicar(SALVAR)
        i = self.salvo("CDB da Carla")
        self.assertEqual((i["titular"], i["terceiro"]), ("terceiros", "Carla"))
        self.assertIn("De Carla", self.textos(f'#app .inv[data-id="{i["id"]}"] .tag'))

    def test_vencimento_e_liquidez(self):
        self.novo()
        self.assertEqual(self.texto('.folha [data-k="liquidez"].on'), "No vencimento", "CDB: no vencimento")
        self.preencher("#f-venc", "2027-05-10")
        self.digitar("#f-valor", "100000")
        self.preencher("#f-nome", "CDB com data")
        self.clicar(SALVAR)
        self.assertEqual((self.salvo()["vencimento"], self.salvo()["liquidez"]), ("2027-05-10", "vencimento"))
        self.assertIn("Vence 10/05/2027", self.textos('#app .inv .tag'))
        self.novo()
        self.clicar('.folha [data-a="f-set"][data-k="liquidez"][data-v="diaria"]')
        self.preencher("#f-venc", "2027-05-10")
        self.digitar("#f-valor", "100000")
        self.clicar(SALVAR)
        self.assertEqual((self.salvo()["vencimento"], self.salvo()["liquidez"]), ("2027-05-10", "diaria"))
        self.assertIn("Liquidez diária", self.textos('#app .inv .tag'))

    def test_trocar_o_tipo_traz_os_padroes_mas_mantem_o_rendimento_escolhido(self):
        self.novo()
        on = lambda: (self.texto('.folha [data-a="f-idx"].on'), self.pg.input_value('.folha [data-f="taxa"]'), self.texto('.folha [data-k="liquidez"].on'))
        self.clicar('.folha [data-a="f-tipo"][data-v="lci"]')
        self.assertEqual(on(), ("% do CDI", "90", "No vencimento"))
        self.clicar('.folha [data-a="f-tipo"][data-v="tesouro"]')
        self.assertEqual(on(), ("Selic +", "0", "Diária"))
        self.clicar('.folha [data-a="f-idx"][data-v="pre"]')
        self.preencher('.folha [data-f="taxa"]', "13")
        self.clicar('.folha [data-a="f-tipo"][data-v="cdb"]')
        self.assertEqual(on(), ("Prefixado", "13", "No vencimento"), "o rendimento escolhido fica; a liquidez é a do tipo")

    def test_banco_novo_no_formulario(self):
        self.novo()
        self.clicar('.folha [data-a="f-nb"]')
        self.clicar('.folha [data-a="f-nbok"]')
        self.assertEqual(self.textos(".folha .msg-erro"), ["Dê um nome."])
        self.preencher('.folha [data-f="nb-nome"]', "banco verde")
        self.clicar('.folha [data-a="f-nbok"]')
        self.assertEqual(self.texto('.folha [data-a="f-banco"].on'), "Banco Verde", "um banco que já existe é reaproveitado")
        self.assertEqual(self.js("T.F.bancosNovos.length"), 0)
        self.clicar('.folha [data-a="f-nb"]')
        self.preencher('.folha [data-f="nb-nome"]', "Banco Roxo")
        self.clicar('.folha [data-a="f-nbcor"][data-v="#B79BFF"]')
        self.clicar('.folha [data-a="f-nbok"]')
        self.assertEqual(self.texto('.folha [data-a="f-banco"].on'), "Banco Roxo")
        self.digitar("#f-valor", "100000")
        self.clicar(SALVAR)
        roxo = next(b for b in self.dados()["bancos"] if b["nome"] == "Banco Roxo")
        self.assertEqual((roxo["cor"], self.salvo()["banco"]), ("#B79BFF", roxo["id"]))

    def test_salvar_e_adicionar_outro(self):
        self.novo()
        self.clicar('.folha [data-a="f-set"][data-k="titular"][data-v="terceiros"]')
        self.preencher('.folha [data-f="terceiro"]', "Carla")
        self.clicar('.folha [data-a="f-tipo"][data-v="lci"]')
        self.clicar('.folha [data-a="f-banco"][data-v="b-verde"]')
        self.preencher("#f-nome", "LCI da Carla")
        self.digitar("#f-valor", "300000")
        self.clicar('.folha [data-a="f-salvar"][data-mais]')
        self.assertEqual(self.aviso(), "Salvo. Pode cadastrar o próximo.")
        self.assertEqual(self.folha(), "Novo investimento", "a janela continua aberta")
        self.assertEqual(len(self.dados()["investimentos"]), 1)
        self.assertEqual((self.pg.input_value("#f-nome"), self.pg.input_value("#f-valor"), self.js("document.activeElement.id")), ("", "", "f-nome"))
        self.assertEqual(self.js("[T.F.tipo, T.F.banco, T.F.titular, T.F.terceiro]"), ["lci", "b-verde", "terceiros", "Carla"], "o próximo começa igual")


# ---------------------------------------------------------------------------------------------------------------
class TestEditar(_TelaInvest):
    """Abrir um investimento: editar, duplicar, excluir e as imagens guardadas."""

    def test_banco_com_duas_pessoas_um_botao_por_pessoa(self):
        """1.51: onde se escolhe o banco, um banco com mais de uma pessoa aparece uma vez por pessoa; o investimento guarda
        a conta, e o próximo nível de cada pessoa conta os investimentos dela."""
        self.invest()
        ana_antes = self.js("T.investidoNaConta(T.S.d.bancos[0].contas[0], 'b-azul')")
        self.editar("cdb")
        self.assertEqual(self.textos('.folha [data-a="f-banco"]')[:3], ["Banco Azul · Ana", "Banco Azul · Beto", "Banco Verde"])
        self.clicar('.folha [data-a="f-banco"][data-conta="k-beto"]')
        self.assertEqual(self.texto('.folha [data-a="f-banco"].on'), "Banco Azul · Beto")
        self.clicar('.folha [data-a="f-salvar"]')
        cdb = next(i for i in self.dados()["investimentos"] if i["id"] == "cdb")
        self.assertEqual((cdb["banco"], cdb["conta"]), ("b-azul", "k-beto"))
        self.assertEqual(self.js("T.investidoNaConta(T.S.d.bancos[0].contas[1], 'b-azul')"), self.js("T.valorHoje(T.S.d.investimentos.find(i => i.id === 'cdb'))"),
                         "os 10 mil contam para o Beto")
        self.assertEqual(round(self.js("T.investidoNaConta(T.S.d.bancos[0].contas[0], 'b-azul')"), 2),
                         round(ana_antes - self.js("T.valorHoje(T.S.d.investimentos.find(i => i.id === 'cdb'))"), 2), "e saem da Ana")
        self.assertEqual(self.texto('#app .inv[data-id="cdb"] .inv-meta'), "Banco Azul · Beto · CDB", "o card diz de quem é a conta")
        self.editar("cdb")
        self.assertEqual(self.texto('.folha [data-a="f-banco"].on'), "Banco Azul · Beto", "aberto de novo, a conta escolhida")

    def test_editar_abre_com_os_dados(self):
        self.invest()
        self.editar("cdb")
        self.assertEqual(self.pg.input_value("#f-nome"), "CDB Azul 2028")
        self.assertEqual(self.pg.input_value("#f-valor"), "10.000,00")
        self.assertEqual(self.pg.input_value('.folha [data-f="taxa"]'), "110")
        self.assertEqual(self.pg.input_value("#f-venc"), "2028-03-15")
        self.assertEqual([self.texto('.folha [data-a="f-banco"].on'), self.texto('.folha [data-k="liquidez"].on')], ["Banco Azul · Ana", "No vencimento"],
                         "o Banco Azul tem a Ana e o Beto: o CDB (meu, de antes, sem a conta) fica na de quem usa o app")
        self.assertEqual(self.textos(".folha .folha-pe .btn"), ["Duplicar", "Salvar"])
        self.assertEqual(self.conta('.folha .folha-cab [data-a="f-excluir"]'), 1, "a lixeira no alto")
        self.assertEqual(self.textos(".folha .inv-acoes .btn"), ["Aplicar mais", "Transferir"])
        self.assertEqual(self.conta(".folha .imp-campo"), 0, "editar não tem os quadrinhos da IA")
        self.invest(base(bancos=BANCOS, investimentos=[CDB]))
        self.editar("cdb")
        self.assertEqual(self.textos(".folha .inv-acoes .btn"), ["Aplicar mais"], "Transferir só com outro investimento")

    def test_editar_salva_no_mesmo_investimento(self):
        self.invest(base(bancos=BANCOS, investimentos=[dict(CDB, criado_em="2026-01-10T12:00:00.000Z"), LCI]))
        self.editar("cdb")
        self.preencher('.folha [data-f="taxa"]', "120")
        self.clicar(SALVAR)
        self.assertEqual(self.aviso(), "Investimento salvo")
        invs = self.dados()["investimentos"]
        self.assertEqual([i["id"] for i in invs], ["cdb", "lci"])
        self.assertEqual((invs[0]["taxa"], invs[0]["criado_em"], invs[0]["valor"]), (120, "2026-01-10T12:00:00.000Z", 10000))
        self.assertEqual(self.textos('#app .inv[data-id="cdb"] .tag.taxa'), ["120% do CDI"])

    def test_mudar_o_valor_poe_a_data_de_hoje(self):
        self.invest(base(bancos=BANCOS, investimentos=[dict(PRE, data_valor="2026-08-03")]))
        self.editar("pre")
        self.assertEqual(self.pg.input_value("#f-data"), "2026-08-03")
        self.digitar("#f-valor", "1234567")
        self.assertEqual(self.pg.input_value("#f-data"), HOJE_ISO, "o valor novo é o de hoje")
        self.clicar(SALVAR)
        self.assertEqual((self.salvo()["valor"], self.salvo()["data_valor"]), (12345.67, HOJE_ISO))

    def test_usar_o_valor_corrigido(self):
        """10.000 a 12% desde 03/08/2026 (segunda): 65 dias úteis até 02/11/2026 (13 semanas)."""
        self.invest(base(bancos=BANCOS, investimentos=[dict(PRE, data_valor="2026-08-03")]))
        self.editar("pre")
        hoje = 10000 * 1.12 ** (65 / 252)
        self.assertEqual(self.texto("#aj-valor"), f"Hoje: ≈ {brl(hoje)}, corrigido desde 03/08/2026. Usar este valor")
        self.clicar('.folha [data-a="f-usar-est"]')
        self.assertEqual((self.pg.input_value("#f-valor"), self.pg.input_value("#f-data")), (brl(hoje)[3:], HOJE_ISO))
        self.clicar(SALVAR)
        self.assertEqual(self.salvo()["valor"], round(hoje, 2))

    def test_duplicar(self):
        self.invest()
        self.editar("cdb")
        self.clicar('.folha [data-a="f-duplicar"]')
        self.assertEqual(self.folha(), "Duplicar investimento")
        self.assertEqual(self.pg.input_value("#f-nome"), "CDB Azul 2028 (cópia)")
        self.assertEqual(self.conta('.folha [data-a="f-excluir"]'), 0)
        self.clicar(SALVAR)
        invs = self.dados()["investimentos"]
        self.assertEqual(len(invs), 7)
        copia = invs[-1]
        self.assertNotEqual(copia["id"], "cdb")
        self.assertEqual((copia["nome"], copia["valor"], copia["taxa"], copia["banco"]), ("CDB Azul 2028 (cópia)", 10000, 110, "b-azul"))
        self.assertEqual(self.salvo("CDB Azul 2028")["id"], "cdb", "o original continua")

    def test_excluir_pede_confirmacao(self):
        self.invest()
        self.editar("lci")
        self.clicar('.folha [data-a="f-excluir"]')
        self.assertEqual(self.folha(), "Apagar investimento?")
        self.assertIn("LCI Verde sai da lista e dos gráficos. Uma cópia fica em Versões anteriores.", self.folha_texto())
        self.assertEqual(self.textos(".folha .folha-pe .btn"), ["Cancelar", "Apagar"])
        self.clicar('.folha [data-a="fechar"]:text-is("Cancelar")')
        self.assertIn("LCI Verde", [i["nome"] for i in self.dados()["investimentos"]], "cancelar não exclui")
        self.assertEqual(self.folha(), "Editar investimento", "Cancelar volta para o investimento")
        self.clicar('.folha [data-a="f-excluir"]')
        self.clicar('.folha [data-a="confirmar"]')
        self.assertEqual(self.aviso(), "Investimento apagado")
        self.assertNotIn("LCI Verde", [i["nome"] for i in self.dados()["investimentos"]])
        self.assertNotIn("LCI Verde", self.nomes())

    # BUG: o "Apagar investimento?" abre no lugar do formulário; Cancelar (ou o Voltar) fecha tudo e a pessoa perde a
    # edição, em vez de voltar para o investimento (AGENTS.md: "Uma janela aberta de dentro de outra volta para ela no Voltar
    # do celular, no X e no Cancelar"). Reproduzir: abrir um investimento, tocar na lixeira, Cancelar: cai na Carteira.
    def test_cancelar_a_exclusao_volta_para_o_investimento(self):
        self.invest()
        self.editar("lci")
        self.clicar('.folha [data-a="f-excluir"]')
        self.clicar('.folha [data-a="fechar"]:text-is("Cancelar")')
        self.assertEqual(self.folha(), "Editar investimento")


    # imagens do investimento (só guardam, sem IA)
    def test_miniaturas_ver_e_remover(self):
        self.invest(base(bancos=BANCOS, investimentos=[dict(CDB, fotos=["a.jpg", "b.jpg"])]))
        self.editar("cdb")
        self.assertEqual(self.pg.get_attribute(".folha .foto img >> nth=0", "data-v"), "a.jpg")
        self.assertEqual(self.conta(".folha .foto img"), 2)
        self.assertEqual(self.texto('.folha [data-a="f-foto-add"]'), "Guardar")
        self.clicar('.folha .foto img[data-v="a.jpg"]')
        self.assertEqual((self.folha(), self.niveis()), ("Imagem", 2), "abre por cima do investimento")
        self.voltar()
        self.assertEqual((self.folha(), self.niveis()), ("Editar investimento", 1), "o Voltar retorna ao investimento")
        self.clicar('.folha [data-a="f-foto-rm"][data-v="a.jpg"]')
        self.assertEqual(self.js("[...document.querySelectorAll('.folha .foto img')].map(i => i.dataset.v)"), ["b.jpg"])
        self.clicar(SALVAR)
        self.assertEqual(self.salvo()["fotos"], ["b.jpg"])

    def test_guardar_imagem(self):
        self.novo()
        with self.pg.expect_file_chooser() as fc:
            self.pg.click('.folha [data-a="f-foto-add"]')
        fc.value.set_files(files=[{"name": "comprovante.png", "mimeType": "image/png", "buffer": PNG}])
        self.pg.wait_for_function("window.GERENCIA_TESTE.F && window.GERENCIA_TESTE.F.fotos.length === 1")
        self.esperar()
        self.assertTrue(self.pg.get_attribute(".folha .foto img", "src").startswith("data:image/jpeg"), "a miniatura aparece")
        self.digitar("#f-valor", "100000")
        self.clicar(SALVAR)
        fotos = self.salvo()["fotos"]
        self.assertEqual(len(fotos), 1)
        self.assertTrue(fotos[0].endswith(".jpg"), fotos)


# ---------------------------------------------------------------------------------------------------------------
class TestIndices(_TelaInvest):
    def mais_invest(self, d=None):
        self.abrir(d or base(bancos=BANCOS, investimentos=[CDB]), ui={"tab": "mais", "maisTela": "invest"})

    def test_editar_um_indice_a_mao(self):
        self.mais_invest()
        self.assertEqual(self.textos("#indices .idx-row .vl"), ["13,65%", "13,75%", "4,5%", "0,1%"])
        self.clicar('#indices [data-a="indice"][data-v="cdi"]')
        self.assertEqual(self.folha(), "CDI")
        self.assertEqual(self.pg.input_value("#i-v"), "13,65")
        self.assertIn("Mudar à mão desliga a atualização pelo Banco Central.", self.folha_texto())
        self.preencher("#i-v", "14,15")
        self.clicar('.folha [data-a="i-salvar"]')
        self.assertEqual(self.aviso(), "Índice atualizado")
        self.assertIsNone(self.folha())
        ind = self.js("T.S.d.indices")
        self.assertEqual((ind["cdi"], ind["fonte"], ind["auto"]), (14.15, "manual", False))
        self.assertEqual(self.texto("#indices .idx-row .vl"), "14,15%")
        self.assertEqual(self.texto("#indices .status"), "Valores digitados à mão em 02/11/2026.")
        self.assertEqual(self.pg.get_attribute('#indices [data-a="indices-auto"]', "aria-checked"), "false")
        self.ir("investimentos")
        self.assertEqual(self.textos('#app .inv[data-id="cdb"] .inv-pe span')[0], f"≈ {brl(rende_mes(10000, 0.1415 * 1.1))} por mês", "o investimento rende pelo índice novo")

    def test_indice_invalido_nao_muda(self):
        self.mais_invest()
        self.clicar('#indices [data-a="indice"][data-v="ipca"]')
        self.assertEqual(self.folha(), "IPCA em 12 meses")
        self.preencher("#i-v", "abc")
        self.clicar('.folha [data-a="i-salvar"]')
        self.assertEqual(self.aviso(), "Valor inválido")
        self.assertEqual(self.folha(), "IPCA em 12 meses")
        self.assertEqual(self.js("T.S.d.indices.ipca"), 4.5)

    def test_atualizar_sozinho_liga_e_desliga(self):
        self.mais_invest()
        self.js("T.api.indices({ auto: false }).then(d => { T.S.d = T.normalizar(d); T.render(); return true; })")
        chave = '#indices [data-a="indices-auto"]'
        self.assertEqual(self.pg.get_attribute(chave, "aria-checked"), "false")
        self.clicar(chave)
        self.assertEqual((self.pg.get_attribute(chave, "aria-checked"), self.js("T.S.d.indices.auto")), ("true", True))
        self.clicar(chave)
        self.assertEqual((self.pg.get_attribute(chave, "aria-checked"), self.js("T.S.d.indices.auto")), ("false", False))


# ---------------------------------------------------------------------------------------------------------------
class TestVencimentosEDono(_TelaInvest):
    def test_vence_primeiro_no_inicio(self):
        casos = [("2026-11-02", "hoje", True), ("2026-11-03", "amanhã", True), ("2026-11-22", "em 20 dias", True),
                 ("2027-01-15", "em 74 dias", False), ("2027-06-01", "01/06/2027", False)]
        for venc, txt, alerta in casos:
            with self.subTest(venc):
                self.abrir(base(bancos=BANCOS, investimentos=[dict(CDB, vencimento=venc)]))
                n = self.pg.locator('#app .hl-row:has(.hl-k:text-is("Vence primeiro")) .hl-n')
                self.assertEqual(n.evaluate("e => e.firstChild.textContent"), txt)
                self.assertEqual("alerta" in n.get_attribute("class"), alerta, "em destaque até 30 dias")

    def test_avisos_de_vencimento(self):
        self.abrir(base(bancos=BANCOS, investimentos=[dict(CDB, vencimento="2026-11-12"), dict(LCI, vencimento="2026-10-01")]))
        av = self.pg.locator('#app .op:has-text("Vence em 10 dias")')
        self.assertEqual(av.locator(".op-t span").inner_text(), "CDB Azul 2028 · decida para onde vai o dinheiro")
        self.assertEqual(self.texto('#app .op:has-text("venceu") .op-t'), "Um investimento venceu\nLCI Verde")
        self.abrir(base(bancos=BANCOS, investimentos=[dict(CDB, vencimento="2026-09-15"), dict(LCI, vencimento="2026-10-01")]))
        self.assertEqual(self.texto('#app .op:has-text("venceram") .op-t b'), "2 investimentos venceram")
        self.clicar('#app .op:has-text("venceram")')
        self.assertEqual(self.folha(), "Editar investimento", "tocar abre o investimento")

    def test_aviso_de_valores_desatualizados(self):
        self.abrir(base(bancos=BANCOS, investimentos=[dict(CDB, data_valor="2026-08-01"), dict(LCI, data_valor="2026-07-01"), dict(DIN, data_valor="2025-01-01")]))
        self.assertEqual(self.texto('#app .op:has-text("Atualize os valores") .op-t span'), "2 investimentos estão sem atualizar há mais de 2 meses",
                         "dinheiro parado não conta")
        self.abrir(base(bancos=BANCOS, investimentos=[dict(CDB, data_valor="2026-08-01"), LCI]))
        self.assertEqual(self.texto('#app .op:has-text("Atualize os valores") .op-t span'), "CDB Azul 2028 está sem atualizar há mais de 2 meses")

    def test_etiqueta_do_dono(self):
        sem_nome = inv("sn", "Fundo sem dono", 700, "cdi_pct", 100, banco="b-azul", tipo="fundo", titular="terceiros", terceiro="  ")
        self.invest(base(bancos=BANCOS, investimentos=[CDB, POUP, sem_nome]))
        dono = lambda i: self.pg.locator(f'#app .inv[data-id="{i}"] .tag.meu, #app .inv[data-id="{i}"] .tag.terc').inner_text()
        self.assertEqual([dono("cdb"), dono("poup"), dono("sn")], ["Meu", "De Beto", "De Terceiros"])
        self.clicar('#app [data-a="filtro"][data-v="terc"]')
        self.assertEqual(self.textos('#app [data-a="pessoa-f"]'), ["Todas as pessoas", "Beto", "Terceiros"])


# ---------------------------------------------------------------------------------------------------------------
class TestBensDaCasa(_TelaInvest):
    def test_bem_em_partes_perde_por_mes_somando_as_partes(self):
        """Cada parte perde na sua taxa (como no valor de hoje e na Evolução), não na média pesada sobre o total."""
        partes = [{"categoria": "imoveis", "valor": 500000, "taxa": 0}, {"categoria": "veiculos", "valor": 60000, "taxa": 15},
                  {"categoria": "moveis", "valor": 20000, "taxa": 10}]
        casa = inv("casa", "Casa e carro", 580000, "deprecia", 1.9, tipo="bens", partes=partes)
        self.invest(base(bancos=BANCOS, investimentos=[casa]))
        esperado = 60000 * (1 - 0.85 ** (1 / 12)) + 20000 * (1 - 0.9 ** (1 / 12))
        self.assertIn(f"perde ≈ {brl(esperado)} por mês", self.texto('#app .inv[data-id="casa"] .inv-pe'))

    def test_cartao_dos_bens_na_carteira(self):
        self.invest(bens=BENS)
        for filtro, n in (("todos", 1), ("meus", 1), ("terc", 0)):
            with self.subTest(filtro):
                self.clicar(f'#app [data-a="filtro"][data-v="{filtro}"]')
                self.assertEqual(self.conta("#app .inv-ro"), n)
        self.clicar('#app [data-a="filtro"][data-v="meus"]')
        c = "#app .inv-ro"
        self.assertEqual((self.texto(c + " .inv-nome"), self.texto(c + " .inv-valor"), self.texto(c + " .inv-meta")), ("Bens da casa", "R$ 12.000,00", "InventarIA · 7 itens"))
        self.assertEqual(self.textos(c + " .tag"), ["Só leitura", "Meu"])
        self.assertEqual(self.textos(c + " .inv-pe span"), ["perde ≈ R$ 141,67 por mês", "o valor muda no InventarIA"])
        self.assertEqual(self.resumo()[1], "R$ 17.300", "os bens não entram no total dos investimentos")

    def test_cartao_dos_bens_some_com_banco_ou_busca(self):
        self.invest(bens=BENS)
        self.clicar('#app [data-a="banco-f"][data-v="b-azul"]')
        self.assertEqual(self.conta("#app .inv-ro"), 0, "com um banco escolhido")
        self.clicar('#app [data-a="banco-f"]:text-is("Todos os bancos")')
        self.preencher("#q", "cdb")
        self.assertEqual(self.conta("#app .inv-ro"), 0, "a busca não é dele")
        self.preencher("#q", "bens")
        self.assertEqual((self.conta("#app .inv-ro"), self.nomes()), (1, []), "buscar bens acha o cartão")

    def test_janela_bens_da_casa(self):
        self.invest(bens=BENS, ui={"gEscopo": "terc"})
        self.clicar("#app .inv-ro")
        self.assertEqual(self.folha(), "Bens da casa")
        self.assertEqual(self.textos(".folha .bens-evo b"), [brl(BENS_1, 0), brl(BENS_5, 0), brl(BENS_10, 0)], "quanto valem em 1, 5 e 10 anos")
        self.assertEqual(self.textos(".folha .stat-duo b"), ["R$ 12.000", "R$ 1.700"])
        linhas = self.textos(".folha .bens-l")
        self.assertEqual([l.split("\n") for l in linhas], [["Móveis", "4 itens · −10% ao ano", "R$ 7.000"], ["Eletrônicos", "3 itens · −20% ao ano", "R$ 5.000"],
                                                           ["Sala", "4 itens", "R$ 8.000"], ["Quarto", "3 itens", "R$ 4.000"]])
        self.clicar('.folha [data-a="bens-evolucao"]')
        self.assertIsNone(self.folha())
        self.assertEqual(self.js("[T.S.ui.invModo, T.S.ui.gEscopo]"), ["evolucao", "meu"], "de terceiros não tem bens: vai para o meu")
        self.assertEqual(self.conta("#ch-evo .l-bens"), 1)

    def test_patrimonio_com_e_sem_os_bens(self):
        meus_mes = brl(RENDE["cdb"] + RENDE["lci"] + RENDE["tes"], 0)
        self.abrir(base(bancos=BANCOS, investimentos=INVS), bens=BENS)
        self.assertEqual(self.placar(), ("Patrimônio de R$ 29.300", [("Investido", "R$ 17.300"), ("Bens", "R$ 12.000"), ("Por mês", "+" + meus_mes)]),
                         "17.300 seus + 12.000 em bens; terceiros fora")
        self.assertEqual(self.texto('#app .hl-row[data-a="bens"]').split("\n"), ["Bens da casa", "7 itens no InventarIA", "R$ 12.000", "perdem ≈ R$ 1.700/ano"])
        self.abrir(base(bancos=BANCOS, investimentos=INVS))
        self.assertEqual(self.placar(), ("Patrimônio de R$ 17.300", [("Investimentos", "4"), ("Bancos", "2"), ("Por mês", "+" + meus_mes)]))
        self.assertEqual(self.conta('#app .hl-row[data-a="bens"]'), 0)

    def test_bens_de_terceiros_ficam_fora_do_patrimonio(self):
        carro = inv("carro", "Carro do Beto", 30000, "deprecia", 15, tipo="bens", categoria_bem="veiculos", liquidez="diaria", titular="terceiros", terceiro="Beto")
        moto = inv("moto", "Moto", 8000, "deprecia", 15, tipo="bens", categoria_bem="veiculos", liquidez="diaria")
        self.abrir(base(bancos=BANCOS, investimentos=INVS + [carro, moto]))
        pat, cols = self.placar()
        self.assertEqual(pat, "Patrimônio de R$ 25.300", "17.300 + a moto; o carro do Beto fica fora")
        self.assertEqual(cols[:2], [("Investido", "R$ 17.300"), ("Bens", "R$ 8.000")])

    def test_evolucao_soma_os_bens(self):
        self.invest(bens=BENS, ui={"invModo": "evolucao", "gAnos": 5})
        hoje, em5 = self.stat()
        self.assertEqual(hoje, ("Hoje", "R$ 31.600", "com R$ 12.000 em bens"))
        self.assertTrue(em5[2].endswith(f"bens −{brl(12000 - BENS_5, 0)}"), em5[2])
        self.assertIn("Bens", self.textos("#app .leg span"))
        self.assertEqual(self.conta("#ch-evo .l-bens"), 1)
        self.assertEqual(self.tc("#app .tabela thead th")[-1], "Bens", "a coluna Bens na tabela por ano")
        self.clicar('#app [data-k="gEscopo"][data-v="terc"]')
        self.assertEqual(self.stat()[0][:2], ("Hoje", "R$ 2.300"), "os bens são seus: fora de De terceiros")
        self.assertEqual(self.conta("#ch-evo .l-bens"), 0)

    def test_ocultar_bens_na_evolucao(self):
        self.invest(ui={"invModo": "evolucao"})
        self.assertEqual(self.conta('#app [data-k="gSemBens"]'), 0, "sem bens, sem a chave")
        moto = inv("moto", "Moto", 8000, "deprecia", 15, tipo="bens", categoria_bem="veiculos", liquidez="diaria")
        self.invest(base(bancos=BANCOS, investimentos=INVS + [moto]), bens=BENS, ui={"invModo": "evolucao"})
        self.assertEqual(self.stat()[0][1], "R$ 39.600", "19.600 + 8.000 da moto + 12.000 da casa")
        self.assertEqual(self.pg.get_attribute('#app [data-k="gSemBens"]', "aria-checked"), "false", "começa desligado")
        self.clicar('#app [data-k="gSemBens"]')
        self.assertEqual(self.stat()[0], ("Hoje", "R$ 19.600", ""), "só os investimentos")
        self.assertEqual(self.conta("#ch-evo .l-bens"), 0)
        self.assertNotIn("Bens", self.textos("#app .leg span"))
        self.assertEqual(self.pg.get_attribute('#app [data-k="gSemBens"]', "aria-checked"), "true")

    def test_ocultar_bens_na_divisao(self):
        self.invest(bens=BENS, ui={"invModo": "divisao"})
        self.assertEqual(self.comps()[1], ("Bens da casa", "7 itens · perdem ≈ R$ 1.700/ano", "R$ 12.000", "38,0%"))
        self.assertEqual(self.stat()[0][1], "R$ 31.600")
        self.clicar('#app [data-k="gSemBens"]')
        self.assertNotIn("Bens da casa", [c[0] for c in self.comps()])
        self.assertEqual(self.stat()[0][1], "R$ 19.600")

    def test_so_bens_na_evolucao(self):
        """Sem investimentos seus nem aporte: só a linha dos bens perdendo valor."""
        self.invest(base(bancos=BANCOS, investimentos=[POUP]), bens=BENS, ui={"invModo": "evolucao", "gEscopo": "meu", "gAnos": 5})
        self.assertEqual(self.stat(), [("Bens hoje", "R$ 12.000", ""), ("Em 5 anos", brl(BENS_5, 0), f"perdem {brl(12000 - BENS_5, 0)}")])
        self.assertEqual(self.textos("#app .leg span"), ["Bens"])
        self.assertEqual(self.js("[...document.querySelectorAll('#ch-evo svg path')].map(p => p.getAttribute('class'))"), ["l-bens so"])

    def test_somar_os_bens_desligado(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS, ajustes={"corrigir": True, "bens": False}), bens=BENS)
        self.assertEqual(self.pg.get_attribute(".placar-num", "aria-label"), "Patrimônio de R$ 17.300")
        self.assertEqual(self.conta('#app .hl-row[data-a="bens"]'), 0)
        self.ir("investimentos")
        self.assertEqual(self.conta("#app .inv-ro"), 0)
        self.modo("divisao")
        self.assertNotIn("Bens da casa", [c[0] for c in self.comps()])


# ---------------------------------------------------------------------------------------------------------------
class TestComoODonoGosta(_TelaInvest):
    def test_numeros_grandes_cabem(self):
        grande = inv("g", "CDB Grande", 98765432.1, "pre", 12, banco="b-azul")
        self.invest(base(bancos=BANCOS, investimentos=[grande, PRE]), ui={"invModo": "evolucao", "gAnos": 50})
        self.assertTrue(self.cabe("#app .stat-duo b"), f"Hoje e Em 50 anos inteiros: {self.stat()}")
        tamanhos = self.js("[...document.querySelectorAll('#app .stat-duo b')].map(b => getComputedStyle(b).fontSize)")
        self.assertEqual(len(set(tamanhos)), 1, f"os dois do mesmo tamanho ({tamanhos})")
        self.modo("carteira")
        self.assertTrue(self.cabe("#app .inv-valor"), self.textos("#app .inv-valor"))

    def test_botoes_lado_a_lado_alinhados(self):
        caixa = lambda sel: self.js("[...document.querySelectorAll(a)].map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.top), Math.round(r.height), Math.round(r.width)]; })", sel)
        ap = {"id": "ap1", "tipo": "despesa", "aporte": True, "descricao": "Aporte", "valor": 500, "dia": 6, "inicio": "2026-01"}
        self.invest(base(bancos=BANCOS, investimentos=[PRE], recorrencias=[ap]), ui={"invModo": "evolucao"})
        for sel in ("#app .btns-2 .btn", "#app .chips.c5 .chip"):
            with self.subTest(sel):
                cx = caixa(sel)
                self.assertGreater(len(cx), 1)
                self.assertEqual(len({(t, h) for t, h, _ in cx}), 1, f"na mesma linha e da mesma altura ({cx})")
                self.assertLessEqual(max(w for *_, w in cx) - min(w for *_, w in cx), 1, f"da mesma largura ({cx})")
        self.clicar('#nav [data-a="novo"]')
        cx = caixa(".folha .folha-pe .btn")
        self.assertEqual(len({(t, h) for t, h, _ in cx}), 1, f"Salvar e adicionar outro e Salvar alinhados ({cx})")

    def test_ia_desligada_some_do_invest(self):
        self.invest(base(bancos=BANCOS, investimentos=INVS), ui={"filtro": "terc", "pessoa": "Carla"})
        self.assertEqual(self.texto("#app .ia-saldos-btn"), "Atualizar saldos de Carla com IA", "com a IA ligada")
        self.clicar('#nav [data-a="novo"]')
        self.assertEqual(self.textos(".folha .imp-tile")[:2], ["Colar mensagem", "Escolher fotos"])
        sem_ia = {"corrigir": True, "ia": False}
        self.invest(base(bancos=BANCOS, investimentos=INVS, ajustes=sem_ia), ui={"filtro": "terc", "pessoa": "Carla"})
        self.assertEqual(self.conta("#app .ia-saldos-btn"), 0)
        self.clicar('#nav [data-a="novo"]')
        self.assertEqual(self.conta(".folha .imp-campo"), 0, "sem os quadrinhos da IA")
        self.invest(base(bancos=BANCOS, ajustes=sem_ia))
        self.assertFalse(self.pg.locator('#app .vazio [data-a="ia"]').is_visible(), "sem o Ler print com IA")
        self.assertTrue(self.pg.locator('#app [data-a="novo-inv"]').is_visible())


# ---------------------------------------------------------------------------------------------------------------
class TestComputador(_TelaInvest):
    """Com 1000 px ou mais: barra lateral com Buscar, os bancos e as pessoas."""
    LARGURA, ALTURA = 1280, 900

    def test_buscar_da_barra_lateral_abre_a_carteira_com_o_cursor(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS))
        self.clicar('#lado [data-a="buscar"]')
        self.assertEqual(self.js("[T.S.ui.tab, T.S.ui.invModo, document.activeElement.id]"), ["investimentos", "carteira", "q"])

    # (era bug até a 1.24.0)
    def test_buscar_da_barra_lateral_procura_em_todos(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS), ui={"tab": "investimentos", "filtro": "terc", "banco": "b-verde"})
        self.clicar('#lado [data-a="buscar"]')
        self.assertEqual(self.js("[T.S.ui.filtro, T.S.ui.banco]"), ["todos", None])
        self.assertEqual(len(self.nomes()), 6)

    def test_tecla_barra_abre_a_busca_em_todos(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS), ui={"filtro": "terc", "banco": "b-verde"})
        self.pg.keyboard.press("/")
        self.esperar()
        self.assertEqual(self.js("[T.S.ui.tab, T.S.ui.filtro, T.S.ui.banco, document.activeElement.id]"), ["investimentos", "todos", None, "q"])
        self.assertEqual(len(self.nomes()), 6)

    def test_banco_e_pessoa_da_barra_lateral_abrem_a_carteira_filtrada(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS))
        self.assertEqual([t.split("\n")[1] for t in self.textos('#lado [data-a="lado-banco"]')], ["Banco Azul", "Banco Verde", "Sem banco"])
        self.clicar('#lado [data-a="lado-banco"][data-v="b-verde"]')
        self.assertEqual(self.nomes(), ["LCI Verde", "Poupança do Beto"])
        self.assertEqual(self.pg.get_attribute('#lado [data-a="lado-banco"][data-v="b-verde"]', "aria-current"), "page")
        self.clicar('#lado [data-a="pessoa"][data-v="Beto"]')
        self.assertEqual(self.nomes(), ["Poupança do Beto"])
        self.assertEqual(self.js("[T.S.ui.filtro, T.S.ui.pessoa, T.S.ui.banco]"), ["terc", "Beto", None])

    # (era bug até a 1.24.0)
    def test_esconder_valores_tambem_no_invest(self):
        self.abrir(base(bancos=BANCOS, investimentos=INVS), ui={"tab": "investimentos"})
        self.assertEqual(self.conta('.top-acts [data-a="olho"]'), 1)
        self.clicar('.top-acts [data-a="olho"]')
        self.assertEqual(set(self.textos("#app .inv-valor")), {"R$ •••••"})


if __name__ == "__main__":
    unittest.main()
