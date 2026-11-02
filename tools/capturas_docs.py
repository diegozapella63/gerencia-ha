"""Refaz as capturas de tela do README (docs/*.png) a partir da prévia, com os dados de exemplo.
Uso: python3 tools/montar_previa.py && python3 tools/capturas_docs.py   (precisa do playwright)"""
import os
from playwright.sync_api import sync_playwright

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIA = "file://" + os.path.join(RAIZ, "preview", "gerencia-previa.html")
DOCS = os.path.join(RAIZ, "docs")

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, color_scheme="dark")
    pg.goto(PREVIA)
    pg.wait_for_timeout(1500)
    tirar = lambda nome: (pg.wait_for_timeout(700), pg.screenshot(path=os.path.join(DOCS, nome)))
    tirar("inicio.png")
    pg.locator(".card", has_text="Dicas de economia").first.evaluate("el => window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 90)")
    tirar("dicas.png")
    pg.click('#nav [data-v="caixa"]')
    pg.wait_for_timeout(400)
    pg.get_by_role("button", name="Fluxo", exact=True).first.click()
    tirar("caixa.png")
    pg.click('#nav [data-v="investimentos"]')
    pg.wait_for_timeout(400)
    pg.get_by_role("button", name="Evolução", exact=True).first.click()
    tirar("invest.png")
    b.close()
print("capturas em", DOCS)
