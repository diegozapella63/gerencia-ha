"""Monta preview/gerencia-previa.html: o app inteiro num arquivo só, com dados de exemplo (window.GERENCIA_DEMO),
para abrir sem servidor (ou publicar como página). Uso: python3 tools/montar_previa.py [saida.html]"""
import base64
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(RAIZ, "gerencia", "app", "www")
SAIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "preview", "gerencia-previa.html")

css = open(os.path.join(W, "styles.css"), encoding="utf-8").read()
js = open(os.path.join(W, "app.js"), encoding="utf-8").read()
assert "</script" not in js


def embute(m):
    b64 = base64.b64encode(open(os.path.join(W, "fonts", m.group(1) + ".woff2"), "rb").read()).decode()
    return f'url("data:font/woff2;base64,{b64}") format("woff2")'


css = re.sub(r'url\("fonts/([\w-]+)\.woff2"\) format\("woff2"\), url\("fonts/[\w-]+\.woff"\) format\("woff"\)', embute, css)
assert "fonts/" not in css
html = f'''<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>GerencIA</title>
<meta name="theme-color" content="#0f1318">
<style>
{css}
</style>
<main id="app" aria-live="polite"></main>
<nav id="nav" aria-label="Menu principal"><div class="in"></div></nav>
<div id="folhas"></div>
<div id="toast" role="status"></div>
<input type="file" id="arquivo" accept=".zip,.json" hidden>
<script>window.GERENCIA_DEMO = true;</script>
<script>
{js}
</script>
'''
os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
open(SAIDA, "w", encoding="utf-8").write(html)
print(SAIDA, len(html), "bytes")
