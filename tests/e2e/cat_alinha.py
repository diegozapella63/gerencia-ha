import sys
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="cx-modo"][data-v="categorias"]'); pg.wait_for_timeout(600)
    ys = pg.evaluate("() => [...document.querySelectorAll('.stat-duo b')].map(b => Math.round(b.getBoundingClientRect().top))")
    bars = pg.evaluate("() => [...document.querySelectorAll('.comps .barra')].map(b => [Math.round(b.getBoundingClientRect().left), Math.round(b.getBoundingClientRect().width)])")
    print('valores no alto (y):', ys, '| barras (x, largura):', sorted(set(map(tuple, bars))))
    print('%:', pg.locator('.comps .vl small').all_inner_texts()[:4])
    pg.locator('.graf-card').screenshot(path=f'{SP}/shots/cat-alinha.png')
    pg.click('[data-a="cx-modo"][data-v="fluxo"]'); pg.wait_for_timeout(600)
    ys = pg.evaluate("() => [...document.querySelectorAll('.stat-duo b')].map(b => Math.round(b.getBoundingClientRect().top))")
    print('fluxo valores (y):', ys)
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(400)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(400)
    print('invest stat-duo:', pg.evaluate("() => [...document.querySelectorAll('.stat-duo b')].map(b => Math.round(b.getBoundingClientRect().top))"))
    print('ERROS', erros); b.close()
