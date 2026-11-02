import sys
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="mais-aba"][data-v="integracoes"]'); pg.wait_for_timeout(1200)
    print('uso-ia com sensor:', 'gerencia_ia_hoje' in pg.inner_text('#uso-ia'), '| sensores com nota:', 'gerencia_ia_hoje' in pg.inner_text('#sensores'))
    pg.locator('#sensores').screenshot(path=f'{SP}/shots/sensores.png')
    print('ERROS', erros); b.close()
