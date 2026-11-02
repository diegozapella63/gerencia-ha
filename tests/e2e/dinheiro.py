import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="f-tipo"][data-v="dinheiro"]'); pg.wait_for_timeout(300)
    vis = lambda t: pg.locator(f'.folha .campo:has(.lbl:text-is("{t}"))').first.is_visible() if pg.locator(f'.folha .campo:has(.lbl:text-is("{t}"))').count() else None
    print('banco visível:', vis('Banco'), '| rendimento:', vis('Rendimento'), '| liquidez:', vis('Liquidez'), '| vencimento:', pg.locator('#f-venc').is_visible())
    pg.fill('#f-nome', 'Dinheiro em casa'); pg.locator('#f-valor').click(); pg.keyboard.type('1500000')
    pg.screenshot(path=f'{SP}/shots/dinheiro.png')
    pg.click('[data-a="f-salvar"]:not([data-mais])'); pg.wait_for_timeout(900)
    o = [i for i in get('api/state')['investimentos'] if i['nome'] == 'Dinheiro em casa']
    print('salvo:', [(i['tipo'], i['banco'], i['indexador'], i['taxa'], i['valor']) for i in o])
    print('cartão:', pg.locator('.inv:has-text("Dinheiro em casa") .inv-meta').inner_text())
    print('ERROS', erros); b.close()
