import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'; INV = 'http://127.0.0.1:8098/'
def req(base, p, c=None, m='GET'):
    r = urllib.request.Request(base + p, data=json.dumps(c).encode() if c is not None else None, method=m, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
req(INV, 'api/cats', {'name': 'Ferramentas'}, 'POST')
req(INV, 'api/cats/plantas', {'name': 'Jardim'}, 'PUT')
req(INV, 'api/cats/pets', None, 'DELETE')
sala = req(INV, 'api/rooms', {'name': 'Sala'}, 'POST')['room']['id']
req(INV, 'api/items', {'room': sala, 'name': 'Televisão', 'cat': 'eletronicos', 'value': 3000}, 'POST')
print('1 todas:', [(c['id'], c['nome']) for c in req(B, 'api/bens').get('todas', [])])
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="f-tipo"][data-v="bens"]'); pg.wait_for_timeout(300)
    print('2 chips:', pg.locator('[data-k="categoria_bem"]').all_inner_texts())
    pg.click('[data-a="f-dividir"][data-v="1"]'); pg.wait_for_timeout(300)
    print('3 partes:', [x.split('\n')[0] for x in pg.locator('.bens-partes .bens-tx').all_inner_texts()])
    print('ERROS', erros); b.close()
