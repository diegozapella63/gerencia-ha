import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, device_scale_factor=2, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300); pg.click('.op[data-a="ia"]'); pg.wait_for_timeout(400)
    print('1 entrada: escolha de tipo', pg.locator('.folha .seg').count(), '| botão', pg.inner_text('[data-a="ia-arq"]'))
    pg.fill('#ia-txt', 'paguei 180 da luz ontem, tenho que pagar o boleto do IPVA e apliquei 15 mil no CDB do Inter a 112% do CDI')
    pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2600)
    print('2 conferir:', pg.inner_text('.folha-cab h2'), '|', pg.inner_text('.folha-corpo p').split('.')[0], '| seções', pg.locator('.ia-sec').all_inner_texts())
    print('  botão:', pg.inner_text('[data-a="ia-salvar"]'))
    pg.screenshot(path=f'{SP}/shots/ia-auto-conferir.png', full_page=True)
    n0 = len(get('api/state')['lancamentos']); i0 = len(get('api/state')['investimentos'])
    pg.click('[data-a="ia-salvar"]'); pg.wait_for_timeout(1000)
    d = get('api/state')
    print('3 salvou: lançamentos +', len(d['lancamentos']) - n0, '| investimentos +', len(d['investimentos']) - i0, '| tela', pg.inner_text('.cab h1'))
    # só investimento
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300); pg.click('[data-a="ia-de"][data-ini="texto"]'); pg.wait_for_timeout(400)
    pg.fill('#ia-txt', 'saldo da LCA do BB e do CDB do Inter'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2600)
    print('4 só investimento:', pg.inner_text('.folha-cab h2'), '| seções', pg.locator('.ia-sec').count(), '| botão', pg.inner_text('[data-a="ia-salvar"]'))
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # Falar, sem escolher
    print('5 uso:', get('api/ia/uso')['today'].get('kinds'))
    print('ERROS', erros); b.close()
