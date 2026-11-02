import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'; INV = 'http://127.0.0.1:8098/'
def req(base, p, c=None, m='GET'):
    r = urllib.request.Request(base + p, data=json.dumps(c).encode() if c is not None else None, method=m, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
sala = req(INV, 'api/rooms', {'name': 'Sala'}, 'POST')['room']['id']
for nome, cat, val in [('Televisão', 'eletronicos', 3000), ('Sofá', 'moveis', 2500)]:
    req(INV, 'api/items', {'room': sala, 'name': nome, 'cat': cat, 'value': val}, 'POST')
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(400)
    for f in ('todos', 'meus', 'terc'):
        pg.click(f'[data-a="filtro"][data-v="{f}"]'); pg.wait_for_timeout(300)
        print(f, '→ cartão bens:', pg.locator('.inv-ro').count())
    pg.click('[data-a="filtro"][data-v="meus"]'); pg.wait_for_timeout(300)
    c = pg.locator('.inv-ro'); c.scroll_into_view_if_needed()
    print('cartão:', c.inner_text().replace('\n', ' | '))
    c.screenshot(path=f'{SP}/shots/bens-carteira.png')
    c.click(); pg.wait_for_timeout(400)
    print('abre:', pg.inner_text('.folha-cab h2'), '| evolução:', pg.inner_text('.bens-evo').replace(chr(10), ' '))
    pg.screenshot(path=f'{SP}/shots/bens-janela2.png')
    pg.click('[data-a="bens-evolucao"]'); pg.wait_for_timeout(600)
    print('ver na evolução:', pg.locator('[data-a="inv-modo"].on').first.inner_text(), '| linha bens', pg.locator('#ch-evo .l-bens').count())
    print('ERROS', erros); b.close()
