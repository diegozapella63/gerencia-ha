import sys
from playwright.sync_api import sync_playwright
SP=sys.argv[1]; erros=[]
with sync_playwright() as p:
    b=p.chromium.launch()
    for esquema in ('dark','light'):
        pg=b.new_page(viewport={'width':396,'height':860}, device_scale_factor=2, color_scheme=esquema)
        pg.on('pageerror', lambda e: erros.append('PAGEERROR '+str(e)))
        pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
        if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]')
        pg.wait_for_timeout(9000)
        c=pg.locator('.card.dicas'); c.scroll_into_view_if_needed()
        c.screenshot(path=f'{SP}/shots/e8-card-{esquema}.png')
        pg.close()
    print('ERROS', erros); b.close()
