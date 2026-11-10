"""Base dos testes da tela (tests/test_tela*.py): o app.js de verdade num Chromium, sem servidor.

A página abre com window.GERENCIA_DEMO = true (a "prévia": os dados ficam na memória, em apiDemo) e
window.GERENCIA_TESTE = true, que entrega qualquer função ou variável de dentro do app.js pelo nome:
T.totais(...), T.S (o estado da tela), T.api, T.FOLHA, T.LF (o formulário de lançamento aberto)...

O relógio fica parado em 02/11/2026 10:00 (segunda-feira), no fuso de São Paulo, e a tela tem 390 px (celular).
Precisa do playwright (pip install playwright; playwright install chromium); sem ele, os testes são pulados.

Dados sempre inventados (Ana, Beto, Banco Azul...): nunca nomes, bancos ou valores reais de ninguém.
"""
import json
import os
import unittest
from datetime import date

from tests.base import RAIZ, INDICES

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

# ---- cobertura do app.js (só com tools/cobertura.py, que liga GERENCIA_COBERTURA): cada página nova grava, pelo
# Profiler do Chromium, quais trechos do app.js rodaram; antes de fechar a página, o resultado vai para COBERTURA_JS.
COBERTURA_JS = []


def _instalar_cobertura():
    from playwright.sync_api._generated import Browser, BrowserContext, Page
    abertas = {}  # id(página) -> (página, sessão do Chromium)

    def colher(pagina):
        p, cdp = abertas.pop(id(pagina), (None, None))
        if cdp:
            try:
                r = cdp.send("Profiler.takePreciseCoverage")
                COBERTURA_JS.extend(x for x in r["result"] if x["url"].endswith("/www/app.js"))
            except Exception:  # noqa: BLE001  (página já fechada)
                pass

    nova, fechar_p, fechar_c, fechar_b = BrowserContext.new_page, Page.close, BrowserContext.close, Browser.close

    def new_page(self, *a, **k):
        pg = nova(self, *a, **k)
        try:
            cdp = self.new_cdp_session(pg)
            cdp.send("Profiler.enable")
            cdp.send("Profiler.startPreciseCoverage", {"callCount": True, "detailed": True})
            abertas[id(pg)] = (pg, cdp)
        except Exception:  # noqa: BLE001
            pass
        return pg

    def close_p(self, *a, **k):
        colher(self)
        return fechar_p(self, *a, **k)

    def close_c(self, *a, **k):
        for pg, _ in list(abertas.values()):
            if pg.context == self:
                colher(pg)
        return fechar_c(self, *a, **k)

    def close_b(self, *a, **k):
        for pg, _ in list(abertas.values()):
            colher(pg)
        return fechar_b(self, *a, **k)

    BrowserContext.new_page, Page.close, BrowserContext.close, Browser.close = new_page, close_p, close_c, close_b


if os.environ.get("GERENCIA_COBERTURA") and sync_playwright:
    _instalar_cobertura()


def relatorio_cobertura_js(entradas=None):
    """Linhas e funções do app.js que os testes da tela percorreram: {linhas, linhas_ok, funcoes, funcoes_ok, faltando: [linhas]}.
    Uma linha conta como percorrida quando o primeiro caractere dela rodou; linhas vazias e só de comentário ficam fora."""
    entradas = COBERTURA_JS if entradas is None else entradas
    fonte = open(os.path.join(RAIZ, "gerencia", "app", "www", "app.js"), encoding="utf-8").read()
    n = len(fonte)
    rodou = bytearray(n)
    funcoes = {}
    for script in entradas:
        cont = [0] * n
        faixas = []
        for f in script["functions"]:
            r0 = f["ranges"][0]
            if r0["startOffset"] > 0 or r0["endOffset"] < n:  # a função do arquivo todo não conta
                k = (r0["startOffset"], r0["endOffset"])
                funcoes[k] = funcoes.get(k, False) or r0["count"] > 0
            faixas += f["ranges"]
        for r in sorted(faixas, key=lambda r: (r["startOffset"], -r["endOffset"])):  # a de dentro vale sobre a de fora
            a, b = r["startOffset"], min(r["endOffset"], n)
            cont[a:b] = [r["count"]] * (b - a)
        for i in range(n):
            if cont[i] > 0:
                rodou[i] = 1
    linhas, ok, faltando, pos = 0, 0, [], 0
    for num, linha in enumerate(fonte.split("\n"), 1):
        t = linha.strip()
        ini = pos + (len(linha) - len(linha.lstrip()))
        pos += len(linha) + 1
        if not t or t.startswith(("//", "/*", "*")):
            continue
        linhas += 1
        if rodou[ini]:
            ok += 1
        else:
            faltando.append(num)
    return {"linhas": linhas, "linhas_ok": ok, "funcoes": len(funcoes), "funcoes_ok": sum(funcoes.values()), "faltando": faltando}


HOJE = date(2026, 11, 2)
INDEX = "file://" + os.path.join(RAIZ, "gerencia", "app", "www", "index.html")


def base(**mais):
    """Dados mínimos (como o servidor guarda), com os índices de exemplo."""
    d = {"indices": dict(INDICES), "ajustes": {"corrigir": True}, "bancos": [], "investimentos": [], "lancamentos": [], "recorrencias": []}
    d.update(mais)
    return d


BANCOS = [
    {"id": "b-azul", "nome": "Banco Azul", "cor": "#56AEFF", "contas": [
        {"id": "k-ana", "pessoa": "Ana", "cartao": True, "fechamento": 5, "vencimento": 12},
        {"id": "k-beto", "pessoa": "Beto", "cartao": True, "fechamento": 25, "vencimento": 5}]},
    {"id": "b-verde", "nome": "Banco Verde", "cor": "#4CD3A5", "contas": [{"id": "k-verde", "pessoa": "Ana", "cartao": False, "fechamento": 1, "vencimento": 10}]},
]

_ABRIR = """async (a) => {
  const T = window.GERENCIA_TESTE;
  T.fecharFolha(true);
  if (T.CAM) T.fecharCamera(true);
  try { localStorage.removeItem('gerencia.tema'); } catch (e) { /* o tema é de cada aparelho: um teste não passa o seu para o próximo */ }
  let rev = 0;
  try { await T.api.save({ rev: -1 }); } catch (e) { rev = e.d.rev; }
  const d = a.d;
  let r = await T.api.save(Object.assign({ bancos: [], investimentos: [], lancamentos: [], recorrencias: [], beneficios: [], ajustes: {}, exemplo: false,
    categorias: T.clone(T.CATEGORIAS_PADRAO) }, d, { rev, substituir_historico: true, historico: d.historico || [] }));
  if (d.indices) r = await T.api.indices({ cdi: d.indices.cdi, selic: d.indices.selic, ipca: d.indices.ipca, tr: d.indices.tr });
  const u0 = JSON.parse(window.__UI0);
  for (const k of Object.keys(T.S.ui)) if (!(k in u0)) delete T.S.ui[k]; // o que um teste deixou (ex.: descAberto) não passa para o próximo
  Object.assign(T.S.ui, u0, a.ui || {});
  Object.assign(T.S, { oculto: false, bens: a.bens === undefined ? null : a.bens, dicas: null, ia: null, uso: null, backups: null, senhas: undefined, senhasPedido: null, oport: undefined });
  T.OP_TODAS = false;
  T.api._senhas = [];  // as senhas dos PDFs da prévia (na memória)
  T.S.d = T.normalizar(r);
  const t = document.getElementById('toast'); if (t) { t.classList.remove('on'); t.textContent = ''; }
  // o histórico começa sem janelas nem telas de Mais; uma tela de Mais aberta aqui ganha a entrada dela (o Voltar volta ao menu)
  try { history.replaceState(null, ''); } catch (e) { /* ok */ }
  T.TELA_VISTA = ''; T.TELA_DE = null;
  T.render();
  return true;
}"""


@unittest.skipUnless(sync_playwright, "precisa do playwright")
class Tela(unittest.TestCase):
    LARGURA, ALTURA = 390, 844

    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.b = cls.pw.chromium.launch()
        cls.ctx = cls.b.new_context(timezone_id="America/Sao_Paulo", locale="pt-BR", viewport={"width": cls.LARGURA, "height": cls.ALTURA})
        cls.pg = cls.ctx.new_page()
        cls.erros = []
        cls.pg.on("pageerror", lambda e: cls.erros.append(str(e)))
        cls.pg.clock.set_fixed_time("2026-11-02T10:00:00-03:00")
        cls.pg.add_init_script("window.GERENCIA_DEMO = true; window.GERENCIA_TESTE = true;")
        cls.pg.goto(INDEX)
        cls.pg.wait_for_function("window.GERENCIA_TESTE && window.GERENCIA_TESTE.S && window.GERENCIA_TESTE.S.d")
        cls.pg.evaluate("window.__UI0 = JSON.stringify(window.GERENCIA_TESTE.S.ui)")

    @classmethod
    def tearDownClass(cls):
        cls.b.close()
        cls.pw.stop()

    def tearDown(self):
        erros, self.erros[:] = list(self.erros), []
        self.assertEqual(erros, [], "nenhum erro na página")

    # ---- funções do app
    def js(self, expr, arg=None):
        """Roda uma expressão com T (as funções do app) e a (o argumento); devolve o resultado (espera Promises)."""
        return self.pg.evaluate(f"async (a) => {{ const T = window.GERENCIA_TESTE; return ({expr}); }}", arg)

    def usar(self, d):
        """Só troca os dados (para testar cálculos; não salva nem redesenha)."""
        self.js("(T.S.d = T.normalizar(a), T.S.bens = null, T.S.oculto = false, true)", d)

    # ---- a tela
    def abrir(self, d=None, ui=None, bens=None):
        """Abre o app com estes dados (gravados na prévia, como se viessem do servidor), na tela Início, sem janelas."""
        self.pg.evaluate(_ABRIR, {"d": d if d is not None else base(), "ui": ui or {}, "bens": bens})
        self.esperar()

    def esperar(self):
        """Espera o que foi salvo voltar e a tela se redesenhar."""
        self.pg.evaluate("() => window.GERENCIA_TESTE.fila")
        self.pg.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")

    def ir(self, aba):
        """Vai para uma aba: inicio, caixa, investimentos ou mais (o menu)."""
        self.pg.click(f'#nav [data-a="tab"][data-v="{aba}"]')
        self.esperar()

    def ir_mais(self, tela, aba=None):
        """Pelo menu de Mais, abre uma tela (bancos, caixa, invest ou config) e, em Configurações, uma aba
        (integracoes, dados, aparencia ou opcoes), como a pessoa faz."""
        self.ir("mais")
        self.pg.click(f'#app .menu-row[data-v="{tela}"]')
        self.esperar()
        if aba:
            self.pg.click(f'#app .mais-abas [data-a="mais-aba"][data-v="{aba}"]')
            self.esperar()

    def clicar(self, sel, n=0):
        self.pg.locator(sel).nth(n).click()
        self.esperar()

    def digitar(self, sel, texto):
        """Clica no campo, apaga e digita (nos campos de dinheiro, os números entram como centavos: 5990 = 59,90)."""
        el = self.pg.locator(sel).first
        el.click()
        el.press("Control+a")
        el.press("Backspace")
        if texto:
            self.pg.keyboard.type(str(texto))
        self.esperar()

    def preencher(self, sel, texto):
        if self.pg.locator(sel).first.evaluate("e => e.hasAttribute('data-dcv')"):
            self.escolher_data(sel, texto)
            return
        self.pg.fill(sel, str(texto))
        self.pg.locator(sel).first.dispatch_event("input")
        self.esperar()

    def escolher_data(self, sel, iso):
        """Uma data no campo de data (os atalhos e o Outra data): pela escolha do campo, como um toque num dia do mês
        (os testes das datas, em test_tela_datas.py, tocam nos botões de verdade)."""
        self.pg.locator(sel).first.evaluate("(e, v) => window.GERENCIA_TESTE.dcEscolher(e.id, v)", str(iso))
        self.esperar()

    def texto(self, sel):
        loc = self.pg.locator(sel)
        return loc.first.inner_text() if loc.count() else None

    def textos(self, sel):
        return self.pg.locator(sel).all_inner_texts()

    def conta(self, sel):
        return self.pg.locator(sel).count()

    def tela(self):
        """O texto da tela principal (sem as janelas)."""
        return self.pg.inner_text("#app")

    def folha(self):
        """Título da janela de cima, ou None (sem janela aberta, mesmo que a animação de fechar ainda esteja na tela)."""
        return self.js("T.FOLHA ? document.querySelector('#folhas .folha-cab h2').innerText : null")

    def folha_texto(self):
        """O texto da janela de cima ('' sem janela)."""
        return self.js("T.FOLHA ? document.querySelector('#folhas .folha').innerText : ''")

    def niveis(self):
        """Quantas janelas abertas (a de cima e as de baixo dela)."""
        return self.js("T.FOLHA ? T.PILHA.length + 1 : 0")

    def voltar(self):
        """O Voltar do celular."""
        self.pg.go_back()
        self.pg.wait_for_timeout(50)
        self.esperar()

    def dados(self):
        """Os dados como estão salvos agora (cópia)."""
        return self.js("JSON.parse(JSON.stringify(T.S.d))")

    def aviso(self):
        """O aviso que está na tela (embaixo, some sozinho), ou None."""
        return self.js("(e => e && e.classList.contains('on') ? (e.querySelector('.toast-t') || e).textContent : null)(document.getElementById('toast'))")


def dump(x):  # para depurar um teste: print(dump(self.dados()))
    return json.dumps(x, ensure_ascii=False, indent=1)
