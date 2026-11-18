"""1.78.0: o fundo e os cartões são os do tema do Home Assistant (hatema.js, o mesmo arquivo em todos os apps da família),
para todos os apps terem o mesmo fundo. Dentro de um Home Assistant de mentira, com um tema dele (claro e depois escuro,
trocado com o app aberto), o app pinta aquele fundo e publica aquele cartão; aberto sozinho (sem o Home Assistant), as
cores do tema padrão dele (#fafafa e #111111).

Usa a prévia (tools/montar_previa.py), servida por um endereço de mentira (o Home Assistant e o app na mesma origem)."""
import os
import subprocess
import sys
import tempfile
import unittest

from tests.base import RAIZ

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

# o Home Assistant em volta do app: o tema no <html>, como ele pinta, e o <home-assistant> com o hass.themes
HA = """<!doctype html><html style="--primary-background-color:#eef3fb;--card-background-color:#fcfdff"><body style="margin:0">
<home-assistant></home-assistant><iframe id="app" src="/app/" style="position:fixed;inset:0;width:100%;height:100%;border:0"></iframe>
<script>document.querySelector("home-assistant").hass = { themes: { darkMode: false } };
window.modo = (dark, bg, card) => { document.querySelector("home-assistant").hass = { themes: { darkMode: dark } };
  document.documentElement.style.setProperty("--primary-background-color", bg); document.documentElement.style.setProperty("--card-background-color", card); };</script></body></html>"""

# o fundo atrás da beira esquerda da tela (o que a pessoa vê em volta dos cartões)
FUNDO = """() => {
  const y = Math.round(innerHeight * 0.55);
  let el = document.elementFromPoint(3, y);
  while (el && el.shadowRoot) { const inner = el.shadowRoot.elementFromPoint(3, y); if (!inner || inner === el) break; el = inner; }
  for (let e = el; e; e = e.parentElement || (e.getRootNode() && e.getRootNode().host) || null) {
    const bg = getComputedStyle(e).backgroundColor;
    if (bg && bg !== "rgba(0, 0, 0, 0)" && bg !== "transparent") return bg;
  }
  return getComputedStyle(document.body).backgroundColor;
}"""
CORES = "() => ['--ha-bg-light', '--ha-card-light', '--ha-bg-dark', '--ha-card-dark'].map((v) => document.documentElement.style.getPropertyValue(v))"
CARTAO = "() => { const c = document.querySelector('.card'); return c ? getComputedStyle(c).backgroundColor : null; }"


@unittest.skipIf(sync_playwright is None, "sem o playwright")
class TemaDoHomeAssistant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.previa = os.path.join(cls.tmp, "previa.html")
        subprocess.run([sys.executable, os.path.join(RAIZ, "tools", "montar_previa.py"), cls.previa], check=True, capture_output=True)
        cls.pw = sync_playwright().start()
        cls.b = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.b.close()
        cls.pw.stop()

    def servir(self, route):
        url = route.request.url.rstrip("/")
        if url.endswith("/app"):
            with open(self.previa, "rb") as f:
                route.fulfill(body=f.read(), content_type="text/html")
        elif url == "http://ha.test":
            route.fulfill(body=HA, content_type="text/html")
        else:
            route.fulfill(status=404, body="")

    def test_dentro_do_home_assistant_o_fundo_e_o_cartao_do_tema(self):
        ctx = self.b.new_context(viewport={"width": 390, "height": 844}, color_scheme="light")
        ctx.route("http://ha.test/**", self.servir)
        pg = ctx.new_page()
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.goto("http://ha.test/")
        app = pg.frames[1]
        app.wait_for_selector(".card")
        pg.wait_for_timeout(600)
        self.assertEqual(app.evaluate("() => window.__haTema.doHA"), "light")
        self.assertEqual(app.evaluate(CORES), ["#eef3fb", "#fcfdff", "#111111", "#1c1c1c"])
        self.assertEqual(app.evaluate(FUNDO), "rgb(238, 243, 251)", "o fundo do tema claro")
        self.assertEqual(app.evaluate(CARTAO), "rgb(252, 253, 255)", "o cartão do tema claro")
        # a pessoa deixa o Home Assistant escuro (um tema com o escuro dele): o app vai junto, sem abrir de novo
        pg.emulate_media(color_scheme="dark")
        pg.evaluate("() => window.modo(true, '#0d1a26', '#172636')")
        pg.wait_for_timeout(900)
        self.assertEqual(app.evaluate("() => window.__haTema.doHA"), "dark")
        self.assertEqual(app.evaluate(CORES), ["#fafafa", "#ffffff", "#0d1a26", "#172636"])
        self.assertEqual(app.evaluate(FUNDO), "rgb(13, 26, 38)", "o fundo do tema escuro")
        self.assertEqual(app.evaluate(CARTAO), "rgb(23, 38, 54)", "o cartão do tema escuro")
        self.assertEqual(erros, [])
        ctx.close()

    def test_sozinho_as_cores_do_tema_padrao_do_home_assistant(self):
        for esquema, fundo, cartao in (("light", "rgb(250, 250, 250)", "rgb(255, 255, 255)"), ("dark", "rgb(17, 17, 17)", "rgb(28, 28, 28)")):
            ctx = self.b.new_context(viewport={"width": 390, "height": 844}, color_scheme=esquema)
            pg = ctx.new_page()
            pg.goto("file://" + self.previa)
            pg.wait_for_selector(".card")
            self.assertIsNone(pg.evaluate("() => window.__haTema.doHA"), esquema)
            self.assertEqual(pg.evaluate(FUNDO), fundo, esquema)
            self.assertEqual(pg.evaluate(CARTAO), cartao, esquema)
            ctx.close()


if __name__ == "__main__":
    unittest.main()
