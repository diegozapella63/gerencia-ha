import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    print('placar:', pg.get_attribute('.placar-num', 'aria-label'), '|', pg.inner_text('.placar-cols').replace('\n', ' '))
    print('rende:', pg.locator('.hl-row').first.inner_text().replace('\n', ' | '))
    print('ERROS', erros); b.close()
