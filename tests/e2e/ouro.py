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
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    sel = pg.locator('[data-a="f-tipo"][data-v="ouro"]')
    print('chip ouro:', sel.count()); sel.first.click(); pg.wait_for_timeout(300)
    pg.fill('#f-nome', 'Ouro 10g'); 
    v = pg.locator('[data-f="valor"]'); v.click(); pg.keyboard.type('860000'); pg.wait_for_timeout(200)
    print('taxa:', pg.inner_text('#aj-taxa'))
    pg.click('.folha-pe .btn.pri'); pg.wait_for_timeout(900)
    o = [i for i in get('api/state')['investimentos'] if i['nome'] == 'Ouro 10g']
    print('salvo:', [(i['tipo'], i['indexador'], i['taxa'], i['liquidez'], i['valor']) for i in o])
    print('ERROS', erros); b.close()
