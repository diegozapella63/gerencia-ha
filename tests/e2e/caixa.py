import sys
from playwright.sync_api import sync_playwright
SP=sys.argv[1]; erros=[]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':396,'height':860}, device_scale_factor=2, color_scheme='dark', extra_http_headers={'X-Remote-User-Display-Name': 'Ana Souza'})
    pg.on('pageerror', lambda e: erros.append('PAGEERROR '+str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type=='error' else None)
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1200)
    pg.screenshot(path=f'{SP}/shots/c1-inicio.png', full_page=True)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(500)
    pg.screenshot(path=f'{SP}/shots/c2-caixa.png', full_page=True)
    pg.click('[data-a="cx-modo"][data-v="fluxo"]'); pg.wait_for_timeout(500)
    box=pg.locator('#ch-fluxo').bounding_box(); pg.mouse.move(box['x']+box['width']*0.62, box['y']+80); pg.wait_for_timeout(200)
    pg.screenshot(path=f'{SP}/shots/c3-fluxo.png', full_page=True)
    pg.click('[data-a="cx-modo"][data-v="categorias"]'); pg.wait_for_timeout(500)
    pg.screenshot(path=f'{SP}/shots/c4-cat.png', full_page=True)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="inv-modo"][data-v="evolucao"]'); pg.wait_for_timeout(400)
    pg.screenshot(path=f'{SP}/shots/c5-inv-evo.png')
    print('ERROS', erros); b.close()
