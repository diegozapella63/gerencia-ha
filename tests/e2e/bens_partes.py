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
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1200)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="f-set"][data-k="titular"][data-v="terceiros"]'); pg.wait_for_timeout(200)
    pg.fill('[data-f="terceiro"]', 'Mãe')
    pg.click('[data-a="f-tipo"][data-v="bens"]'); pg.wait_for_timeout(300)
    print('1 categorias:', pg.locator('[data-k="categoria_bem"]').all_inner_texts())
    pg.click('[data-a="f-dividir"][data-v="1"]'); pg.wait_for_timeout(300)
    print('2 partes:', pg.locator('[data-fparte]').count(), '| valor readonly:', pg.get_attribute('#f-valor', 'readonly') is not None)
    for k, v in [('imoveis', '50000000'), ('veiculos', '6000000'), ('moveis', '2000000')]:
        pg.locator(f'[data-fparte="{k}"]').click(); pg.keyboard.type(v)
    pg.wait_for_timeout(200)
    print('  soma:', pg.inner_text('#partes-soma'), '| valor:', pg.input_value('#f-valor'))
    pg.fill('#f-nome', 'Bens da mãe')
    pg.screenshot(path=f'{SP}/shots/bens-partes.png', full_page=False)
    pg.click('[data-a="f-salvar"]:not([data-mais])'); pg.wait_for_timeout(900)
    inv = [i for i in get('api/state')['investimentos'] if i['nome'] == 'Bens da mãe'][0]
    print('3 salvo:', inv['valor'], inv['taxa'], inv['categoria_bem'], [(x['categoria'], x['valor'], x['taxa']) for x in inv['partes']])
    print('  cartão:', pg.locator('.inv:has-text("Bens da mãe")').inner_text().replace('\n', ' | '))
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="mais-aba"][data-v="invest"]'); pg.wait_for_timeout(400)
    print('4 tabela:', pg.inner_text('#perda-bens').replace('\n', ' | '))
    pg.fill('[data-bens-taxa="imoveis"]', '-4'); pg.press('[data-bens-taxa="imoveis"]', 'Tab'); pg.wait_for_timeout(900)
    inv = [i for i in get('api/state')['investimentos'] if i['nome'] == 'Bens da mãe'][0]
    print('  imóveis -4:', [(x['categoria'], x['taxa']) for x in inv['partes']], '| taxa média', inv['taxa'])
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="evolucao"] >> nth=-1'); pg.wait_for_timeout(400)
    pg.click('[data-a="g"][data-k="gEscopo"][data-v="terc"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="g"][data-k="gAnos"][data-v="10"]'); pg.wait_for_timeout(400)
    print('5 evolução terceiros:', pg.inner_text('.stat-duo').replace('\n', ' | '))
    # reabrir: as partes voltam
    pg.click('[data-a="inv-modo"][data-v="carteira"] >> nth=-1'); pg.wait_for_timeout(300)
    pg.locator('.inv:has-text("Bens da mãe")').click(); pg.wait_for_timeout(400)
    print('6 reaberto: partes', [pg.input_value(f'[data-fparte="{k}"]') for k in ('imoveis', 'veiculos', 'moveis')])
    print('ERROS', erros); b.close()
