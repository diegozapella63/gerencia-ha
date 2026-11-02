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
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(500)
    pg.locator('.inv').first.click(); pg.wait_for_timeout(500)
    print('0 imagens: botão Ler', pg.locator('[data-a="f-foto-ia"]').count(), '|', pg.locator('.fotos + .ajuda').inner_text())
    iid = pg.get_attribute('[data-a="inv-aplicar"]', 'data-v')
    pg.click('[data-a="inv-aplicar"]'); pg.wait_for_timeout(500)
    pg.click('[data-a="ap-modo"][data-v="total"]'); pg.wait_for_timeout(300)
    print('1 rótulo:', pg.inner_text('label[for="ap-v"]'), '| ajuda:', pg.inner_text('#ap-ajuda'))
    pg.type('#ap-v', '1000000'); pg.wait_for_timeout(200)
    print('2 menor:', pg.inner_text('#ap-ajuda'), '| botão', pg.inner_text('[data-a="ap-ok"]'))
    pg.click('[data-a="ap-ok"]'); pg.wait_for_timeout(300)
    print('  erro:', pg.locator('.msg-erro').all_inner_texts())
    pg.fill('#ap-v', ''); pg.type('#ap-v', '3000000'); pg.wait_for_timeout(200)
    print('3 maior:', pg.inner_text('#ap-ajuda'), '| botão', pg.inner_text('[data-a="ap-ok"]'))
    pg.click('[data-a="ap-destino"][data-v="nenhum"]'); pg.wait_for_timeout(200)
    print('  valor mantido depois de trocar destino:', pg.input_value('#ap-v'))
    pg.screenshot(path=f'{SP}/shots/aplicar-total.png')
    pg.click('[data-a="ap-ok"]'); pg.wait_for_timeout(900)
    inv = [i for i in get('api/state')['investimentos'] if i['id'] == iid][0]
    print('4 salvo:', inv['valor'], inv['data_valor'], '| janela', pg.locator('.folha').count())
    print('ERROS', erros); b.close()
