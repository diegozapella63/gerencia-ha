import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    st0 = get('api/state'); nl0 = len(st0['lancamentos']); ni0 = len(st0['investimentos'])
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="ia-de"][data-ini="texto"]'); pg.wait_for_timeout(400)
    pg.fill('#ia-txt', '15mil dinheiro\n30.350,00 nubank\n\nTudo dinheiro da mãe'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2600)
    print('1 conferir:', pg.inner_text('.folha-cab h2'), '| lançamentos', pg.locator('[data-iai="contasel"]').count(), '| investimentos', pg.locator('.ia-item').count())
    for it in pg.locator('.ia-item').all(): print('   ', it.inner_text().split('\n')[0], '|', [x for x in it.inner_text().split('\n') if 'Novo' in x or 'Aporte' in x or 'Atualiza' in x])
    pg.screenshot(path=f'{SP}/shots/so-invest.png')
    pg.click('[data-a="ia-salvar"]'); pg.wait_for_timeout(1200)
    st = get('api/state')
    novos = st['investimentos'][ni0:]
    print('2 salvou: lançamentos +', len(st['lancamentos']) - nl0, '| investimentos novos', [(i['nome'], i['titular'], i.get('terceiro'), i['valor'], i['indexador']) for i in novos])
    print('ERROS', erros); b.close()
