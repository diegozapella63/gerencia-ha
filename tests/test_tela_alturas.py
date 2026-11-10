"""Tela: uma altura só, a mesma em todos os apps da família (50 px), num Chromium de verdade, sem servidor (a prévia).
Botões, campos, caixas de seleção, botões de escolha (as abas de Configurações, o Tema, Toda semana/Todo mês...) e as
escolhas em botões: nas quatro abas de Configurações, nas telas de Mais e nos formulários, no celular e no computador.
Ficam de fora os botões só com ícone, os quadrinhos da IA, as linhas das listas, os interruptores e as cores.
Dados inventados (Ana, Beto, Banco Azul)."""
import unittest

from tests.tela_base import Tela, base, BANCOS
from tests.test_tela_datas import INV

ALTURA = 50
CONTROLES = ".btn, .chip, .inp, select, .pref, .seg, .mais-abas, .quem-p"
MEDIR = """(sel) => [...document.querySelectorAll(sel)].filter(e => e.offsetParent && e.getBoundingClientRect().width > 4 && (e.textContent.trim() || e.matches('input, select, .pref')))
  .map(e => [e.offsetHeight, (e.className || e.tagName) + ' ' + e.textContent.replace(/\\s+/g, ' ').trim().slice(0, 30)])"""


class TestAlturas(Tela):
    maxDiff = None
    def fora(self, onde, dentro="body", vazio=False):
        """Os controles visíveis (de dentro de `dentro`) que não têm a altura da família."""
        hs = self.pg.evaluate(MEDIR, ", ".join(f"{dentro} {c.strip()}" for c in CONTROLES.split(",")))
        self.assertTrue(hs or vazio, f"{onde}: achou os controles")
        return [x for x in hs if x[0] != ALTURA]

    def conferir(self, onde, dentro="body", vazio=False):
        self.assertEqual(self.fora(onde, dentro, vazio), [], f"{onde}: tudo com {ALTURA} px")

    def todas(self):
        d = base(bancos=BANCOS, investimentos=[INV])
        for aba in ("integracoes", "dados", "aparencia", "opcoes"):
            self.abrir(d, ui={"tab": "mais", "maisTela": "config", "maisAba": aba})
            self.conferir(f"Configurações › {aba}", "#app")
        for tela in ("bancos", "invest", "caixa", "beneficios"):
            self.abrir(d, ui={"tab": "mais", "maisTela": tela})
            self.conferir(f"Mais › {tela}", "#app")
        for tab in ("inicio", "caixa", "investimentos"):
            self.abrir(d, ui={"tab": tab})
            self.conferir(tab, "#app", vazio=True)
        for abrir, onde in (("T.abrirLancamento(null, { tipo: 'despesa' })", "Nova despesa"), ("T.abrirInvestimento(null)", "Novo investimento"),
                            ("T.abrirInvestimento('i-cdb')", "Editar investimento"), ("T.abrirBanco('b-azul')", "Editar banco"),
                            ("T.abrirBeneficio(null)", "Novo benefício"), ("(T.abrirMeta(null), T.FMETA.tipo = 'gasto', T.pintarFolha())", "Nova oportunidade"),
                            ("T.abrirEscolhaNovo()", "Adicionar")):
            self.abrir(d)
            self.js(f"({abrir}, true)")
            self.esperar()
            self.conferir(onde, "#folhas", vazio=onde == "Adicionar")
        self.clicar('#folhas .op[data-a="ia"]')
        self.conferir("Ler com IA", "#folhas")

    def tamanho(self, w, h):
        self.pg.set_viewport_size({"width": w, "height": h})
        self.addCleanup(lambda: self.pg.set_viewport_size({"width": self.LARGURA, "height": self.ALTURA}))

    def test_celular(self):
        self.todas()

    def test_celular_estreito(self):
        self.tamanho(320, 700)
        self.todas()

    def test_computador(self):
        self.tamanho(1280, 860)
        self.todas()


if __name__ == "__main__":
    unittest.main()
