"""1.71.0, o padrão da família: toda seção com o cabeçalho (ícone e título), toda linha com título com um ícone pequeno
antes dele, todo botão com texto com ícone, e sem linha entre as linhas de opções. Confere as telas do app e as janelas
mais usadas, com dados inventados (Ana, Beto, Banco Azul, Banco Verde)."""
import unittest

from tests.tela_base import Tela, base, BANCOS
from tests.test_tela_invest import INVS

# o que fica de fora: as linhas de listas de dados (lançamentos, investimentos, benefícios, vencimentos, calendário), as
# sugestões de texto e as abas; uma escolha com a bolinha da cor (categoria, conta, banco) já tem a sua marca
CONFERE = """() => {
  const vis = e => e && e.getClientRects().length;
  const fora = '.abas, nav, .tabbar, .bar, .sug-box, .cal, .lista-lanc, .inv-lista, .venc-lista, .side, .placar, p, .ajuda, .nota';  // um link no meio do texto não é botão
  const ruins = [];
  for (const b of document.querySelectorAll('#app button, #app a.btn, #folhas button, #folhas a.btn, #toast button')) {
    if (!vis(b) || b.closest(fora)) continue;
    const t = b.textContent.trim();
    if (!t || b.querySelector('svg, img, .bol, .tsw, .sw-ring')) continue;
    if (b.matches('.lanc, .inv, .ben-t, .venc-it, .venc-bar, .sug-op, .hl-row, .op, .linha, .menu-row, .side-item, .cal-d, .cal-m, .cal-tit, .sw, .email-l, .ia-item, .cat-l, .fx-l, .dia, .bc-l')) continue;
    ruins.push('botão sem ícone: ' + t.replace(/\\s+/g, ' ').slice(0, 40));
  }
  // com o ícone, o texto continua cabendo no botão
  for (const b of document.querySelectorAll('#app button, #folhas button')) {
    if (vis(b) && b.querySelector('svg') && b.textContent.trim() && getComputedStyle(b).overflowX !== 'auto' && b.scrollWidth > b.clientWidth + 1)
      ruins.push('texto cortado: ' + b.textContent.trim().replace(/\\s+/g, ' ').slice(0, 40));
  }
  for (const b of document.querySelectorAll('#app .card .linha-sw > div > b, #app .card .campo > label, #app .card .campo > .lbl, #app .card .opts > li > .ot > b')) {
    if (vis(b) && !b.querySelector('svg')) ruins.push('linha sem ícone: ' + b.textContent.trim().slice(0, 40));
  }
  for (const c of document.querySelectorAll('#app .mais-painel > section.card, #app .mais-painel > .card')) {
    if (vis(c) && !c.querySelector(':scope > .mais-head svg')) ruins.push('seção sem cabeçalho: ' + (c.id || c.className));
  }
  // o título da tela e o de cada janela com o ícone
  const tt = document.querySelector('#app .cab-linha h1');
  if (vis(tt) && !tt.querySelector('.mais-ic svg')) ruins.push('tela sem ícone no título: ' + tt.textContent.trim());
  const fh = document.querySelector('#folhas .folha-cab h2');
  if (vis(fh) && !fh.querySelector('.folha-ic svg')) ruins.push('janela sem ícone no título: ' + fh.textContent.trim());
  // 1.71.2: as abas que não cabem mostram a seta do lado de onde há mais (por cima das abas); as que cabem, nenhuma
  const tb = document.querySelector('#app .abas-wrap > .mais-abas');
  if (vis(tb)) {
    const w = tb.parentElement, mais = tb.scrollWidth > tb.clientWidth + 2;
    if (mais !== (w.classList.contains('tem-dir') || w.classList.contains('tem-esq'))) ruins.push('abas: a seta não bate com o que cabe');
    const f = w.querySelector('.abas-fim.dir');
    if (w.classList.contains('tem-dir')) { const r = f.getBoundingClientRect(); f.style.pointerEvents = 'auto'; const e = document.elementFromPoint(r.right - 6, (r.top + r.bottom) / 2); f.style.pointerEvents = ''; if (!(e && e.closest('.abas-fim'))) ruins.push('abas: a seta escondida'); }
  }
  for (const l of document.querySelectorAll('#app .card .opts, #app .card .opts > li')) {
    if (vis(l) && (parseFloat(getComputedStyle(l).borderTopWidth) > 0 || parseFloat(getComputedStyle(l).borderBottomWidth) > 0)) { ruins.push('linha na lista de opções: ' + l.textContent.trim().slice(0, 30)); break; }
  }
  for (const l of document.querySelectorAll('#app .card .linha-sw')) {
    if (vis(l) && parseFloat(getComputedStyle(l).borderTopWidth) > 0) { ruins.push('linha entre as opções: ' + l.textContent.trim().slice(0, 30)); break; }
  }
  return [...new Set(ruins)];
}"""


class TestIcones(Tela):
    def conferir(self, onde):
        self.assertEqual(self.pg.evaluate(CONFERE), [], onde)

    def dados(self):
        return base(bancos=BANCOS, investimentos=INVS, ajustes={"corrigir": True, "ia": True, "dicas": True},
                    lancamentos=[{"id": "l1", "tipo": "despesa", "descricao": "Feira", "valor": 10, "data": "2026-11-01", "categoria": "c-mercado", "pago": True}],
                    recorrencias=[{"id": "r1", "descricao": "Aluguel", "valor": 1500, "inicio": "2026-01", "tipo": "despesa", "dia": 5, "categoria": "c-moradia"}])

    def test_as_telas(self):
        self.telas()

    def test_as_telas_num_celular_estreito(self):
        self.pg.set_viewport_size({"width": 320, "height": 700})
        self.addCleanup(lambda: self.pg.set_viewport_size({"width": self.LARGURA, "height": self.ALTURA}))
        self.telas()
        self.janelas()

    def telas(self):
        for tab in ("inicio", "caixa", "investimentos"):
            self.abrir(self.dados(), ui={"tab": tab})
            self.conferir(tab)
        for tela in ("bancos", "caixa", "invest", "beneficios", "sobre"):
            self.abrir(self.dados(), ui={"tab": "mais", "maisTela": tela})
            self.conferir("Mais › " + tela)
        for aba in ("integracoes", "dados", "aparencia", "opcoes"):
            self.abrir(self.dados(), ui={"tab": "mais", "maisTela": "config", "maisAba": aba})
            self.conferir("Configurações › " + aba)

    def test_as_janelas(self):
        self.janelas()

    def janelas(self):
        janelas = [
            ("Adicionar", "T.abrirEscolhaNovo()"),
            ("Nova despesa", "T.abrirLancamento(null, { tipo: 'despesa' })"),
            ("Novo recebimento", "T.abrirLancamento(null, { tipo: 'receita' })"),
            ("Novo investimento", "T.abrirInvestimento(null)"),
            ("Editar banco", "T.abrirBanco('b-azul')"),
            ("Pagar", "T.abrirPagar('v:r1:2026-11')"),
            ("Ler benefícios", "T.abrirLerBeneficios('conta:k-ana')"),
            ("Horizonte", "T.abrirHorizonte()"),
            ("Período", "T.abrirPeriodo()"),
            ("Ajustar saldo", "T.abrirAjuste()"),
            ("Nova categoria", "T.abrirCategoria(null, 'despesa')"),
            ("Ler com IA", "T.abrirIA('caixa')"),
            ("Nova oportunidade", "T.abrirMeta(null)"),
            ("Novo benefício", "T.abrirBeneficio(null)"),
            ("Aplicar", "T.abrirAplicar(T.S.d.investimentos[0].id)"),
            ("Transferir", "T.abrirTransferir(T.S.d.investimentos[0].id)"),
            ("Índice", "T.abrirIndice('cdi')"),
            ("Senha do PDF", "T.abrirSenhaNova()"),
        ]
        for nome, abrir in janelas:
            self.abrir(self.dados())
            self.js(f"({abrir}, true)")
            self.pg.wait_for_selector("#folhas .folha", timeout=3000)
            self.conferir(nome)


class TestSubOpcoes(Tela):
    """1.71.0: o que só vale com a chave de cima ligada fica num quadro recuado, logo abaixo dela: o De quanto em quanto
    tempo do Conferir sozinho, o Quem recebe e o Testar do Avisar no celular (Dicas, Faturas por e-mail, Oportunidades)."""
    def test_quadros_embaixo_das_chaves(self):
        aj = {"ia": True, "dicas": True, "dicas_auto": True, "dicas_aviso": True, "email": True, "email_aviso": True, "op_aviso": True}
        self.abrir(base(ajustes=aj), ui={"tab": "mais", "maisTela": "config", "maisAba": "opcoes"})
        q = self.js("""[...document.querySelectorAll('#app .sub-box')].map(b => { const de = b.parentElement.previousElementSibling, r = b.getBoundingClientRect(), rc = de.getBoundingClientRect();
          return [b.closest('section').id, (de.querySelector('.sw') || {}).dataset?.k || '', Math.round(r.left - rc.left), parseFloat(getComputedStyle(b).borderTopWidth) > 0]; })""")
        self.assertEqual([x[:2] for x in q], [["op-dicas", "dicas_auto"], ["op-dicas", "dicas_aviso"], ["op-email", "email_aviso"], ["op-oport", "op_aviso"]])
        self.assertTrue(all(x[2] >= 20 and x[3] for x in q), f"recuados e com a borda: {q}")
        self.assertEqual(self.conta('#op-dicas .sub-box [data-a="dicas-freq"]'), 3)
        self.assertEqual(self.conta('#op-dicas .sub-box [data-a="aviso-testar"]'), 1)
        self.assertEqual(self.conta('#op-oport .sub-box [data-op-hora]'), 1)
        # 1.71.2: o que cada seção faz, no começo dela
        self.assertEqual([self.texto(f"#{i} .painel-lead")[:30].strip() for i in ("op-dicas", "op-email", "op-oport")],
                         ["A IA confere as assinaturas e", "A fatura que chega por e-mail", "Avisa quando um investimento c"])
        # 1.71.3: e o que depende de Usar IA (o estado, a IA, a fala para texto e o Verificar de novo)
        self.abrir(base(ajustes=aj), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"})
        self.assertEqual(self.js("(b => b && [!!b.querySelector('.status'), !!b.querySelector('#ia-ent'), !!b.querySelector('[data-a=ia-verificar]'), b.parentElement.previousElementSibling.querySelector('.sw').dataset.k])(document.querySelector('#ia .sub-box'))"),
                         [True, True, True, "ia"])


if __name__ == "__main__":
    unittest.main()
