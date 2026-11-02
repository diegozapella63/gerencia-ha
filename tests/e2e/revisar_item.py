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
    n0 = len(get('api/state')['investimentos'])
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300)
    pg.click('.op[data-a="ia-saldos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="ias-pessoa"][data-v="meu"]'); pg.wait_for_timeout(200)
    pg.fill('#ia-txt', 'Nubank, valor atualizado, R$ 30.000\nBanco Pan, valor atualizado, R$ 700'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2500)
    print('1 conferir:', pg.inner_text('.folha-cab h2'), '| itens', pg.locator('.ia-item').count())
    pg.locator('[data-a="iai-revisar"]').nth(1).click(); pg.wait_for_timeout(400)
    print('2 revisar:', pg.inner_text('.folha-cab h2'), '| campos', pg.locator('[data-iae]').count(), '| ainda na janela de IA:', pg.locator('[data-a="iae-ok"]').count())
    pg.fill('#iae-nome', 'CDB Pan 2027'); pg.select_option('#iae-tipo', 'cdb'); pg.wait_for_timeout(200)
    pg.fill('#iae-taxa', '120'); pg.fill('#iae-venc', '2027-12-01')
    pg.screenshot(path=f'{SP}/shots/revisar-item.png')
    pg.click('[data-a="iae-ok"]'); pg.wait_for_timeout(300)
    print('3 voltou:', pg.inner_text('.folha-cab h2'), '| linha 2:', pg.locator('.ia-item').nth(1).inner_text().split('\n')[0])
    pg.locator('[data-a="iai-revisar"]').first.click(); pg.wait_for_timeout(300)
    print('4 existente:', pg.inner_text('.folha-cab h2'), '| campos', pg.locator('[data-iae]').count())
    pg.click('[data-a="iae-voltar"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="ia-salvar"]'); pg.wait_for_timeout(1200)
    st = get('api/state')['investimentos']
    novo = [i for i in st if i['nome'] == 'CDB Pan 2027']
    print('5 salvou:', n0, '->', len(st), '| novo:', [(i['tipo'], i['indexador'], i['taxa'], i['vencimento'], i['valor']) for i in novo])
    print('ERROS', erros); b.close()
