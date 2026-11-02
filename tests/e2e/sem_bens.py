import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'; INV = 'http://127.0.0.1:8098/'
def req(base, p, c=None, m='GET'):
    r = urllib.request.Request(base + p, data=json.dumps(c).encode() if c is not None else None, method=m, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
sala = req(INV, 'api/rooms', {'name': 'Sala'}, 'POST')['room']['id']
req(INV, 'api/items', {'room': sala, 'name': 'Televisão', 'cat': 'eletronicos', 'value': 3000}, 'POST')
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="evolucao"] >> nth=-1'); pg.wait_for_timeout(500)
    print('1 com bens:', pg.inner_text('.stat-duo').replace('\n', ' | '), '| linha', pg.locator('#ch-evo .l-bens').count())
    sw = pg.locator('[data-k="gSemBens"]'); print('  chave:', sw.count()); sw.scroll_into_view_if_needed()
    pg.locator('.ctrl').screenshot(path=f'{SP}/shots/sem-bens-chave.png')
    sw.click(); pg.wait_for_timeout(500)
    print('2 sem bens:', pg.inner_text('.stat-duo').replace('\n', ' | '), '| linha', pg.locator('#ch-evo .l-bens').count())
    pg.click('[data-a="inv-modo"][data-v="divisao"] >> nth=-1'); pg.wait_for_timeout(400)
    print('3 divisão:', pg.locator('.comp[data-v="_bens"]').count(), '| chave on:', pg.get_attribute('[data-k="gSemBens"]', 'aria-checked'))
    pg.reload(); pg.wait_for_timeout(1200)
    print('4 depois de recarregar:', pg.get_attribute('[data-k="gSemBens"]', 'aria-checked'))
    print('ERROS', erros); b.close()
