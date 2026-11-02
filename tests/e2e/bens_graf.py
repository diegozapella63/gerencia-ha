import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'; INV = 'http://127.0.0.1:8098/'
def req(base, p, c=None, m='GET'):
    r = urllib.request.Request(base + p, data=json.dumps(c).encode() if c is not None else None, method=m, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
sala = req(INV, 'api/rooms', {'name': 'Sala'}, 'POST')['room']['id']
for nome, cat, val in [('Televisão', 'eletronicos', 3000), ('Sofá', 'moveis', 2500), ('Notebook', 'eletronicos', 4200)]:
    req(INV, 'api/items', {'room': sala, 'name': nome, 'cat': cat, 'value': val}, 'POST')
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="divisao"] >> nth=-1'); pg.wait_for_timeout(500)
    print('1 divisão:', [x.split('\n')[0] for x in pg.locator('.comp').all_inner_texts()], '| total', pg.inner_text('.stat-duo b >> nth=0'))
    print('  bens:', pg.locator('.comp[data-v="_bens"]').inner_text().replace('\n', ' | '))
    pg.locator('.graf-card').first.screenshot(path=f'{SP}/shots/bens-divisao.png')
    pg.click('[data-a="g"][data-k="gEscopo"][data-v="terc"]'); pg.wait_for_timeout(300)
    print('  terceiros sem bens:', pg.locator('.comp[data-v="_bens"]').count())
    pg.click('[data-a="g"][data-k="gEscopo"][data-v="meu"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="evolucao"] >> nth=-1'); pg.wait_for_timeout(600)
    pg.click('[data-a="g"][data-k="gAnos"][data-v="10"]'); pg.wait_for_timeout(500)
    print('2 evolução:', pg.inner_text('.stat-duo').replace('\n', ' | '), '| linha bens', pg.locator('#ch-evo .l-bens').count(), '| legenda', pg.locator('.leg').inner_text().replace('\n', ' '))
    pg.click('details.card summary'); pg.wait_for_timeout(200)
    print('  tabela:', pg.locator('.tabela thead th').all_inner_texts(), pg.locator('.tabela tbody tr').first.inner_text().replace('\t', ' '))
    print('  cabe:', pg.evaluate("() => { const t = document.querySelector('.tabela-rola'); return [t.scrollWidth, t.clientWidth] }"))
    pg.locator('.graf-card').first.screenshot(path=f'{SP}/shots/bens-evolucao.png')
    print('ERROS', erros); b.close()
