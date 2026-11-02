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
    invs = get('api/state')['investimentos']
    n0 = len(invs)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(500)
    pg.locator('.inv').first.click(); pg.wait_for_timeout(600)
    print('1 botões:', pg.locator('.inv-acoes .btn').all_inner_texts(), '| larguras', [round(pg.locator('.inv-acoes .btn').nth(i).bounding_box()['width']) for i in range(pg.locator('.inv-acoes .btn').count())])
    pg.locator('.inv-aplicar').screenshot(path=f'{SP}/shots/inv-acoes.png')
    pg.click('[data-a="inv-transferir"]'); pg.wait_for_timeout(500)
    tit = pg.inner_text('.folha-cab h2'); print('2 janela:', tit, '| destinos', pg.locator('[data-a="tr-para"]').count())
    de_nome = tit.replace('Transferir de ', '')
    de = [i for i in invs if i['nome'] == de_nome][0]
    pg.click('[data-a="tr-ok"]'); pg.wait_for_timeout(300)
    print('3 sem valor:', pg.locator('.msg-erro').all_inner_texts())
    pg.fill('#tr-v', ''); pg.type('#tr-v', '500000'); pg.wait_for_timeout(200)
    print('  ajuda:', pg.inner_text('#tr-ajuda'), '| botão', pg.inner_text('[data-a="tr-ok"]'))
    pg.click('[data-a="tr-ok"]'); pg.wait_for_timeout(300)
    print('4 sem destino:', pg.locator('.msg-erro').all_inner_texts())
    alvo = pg.locator('[data-a="tr-para"]').nth(1); alvo_id = alvo.get_attribute('data-v'); alvo.click(); pg.wait_for_timeout(300)
    para0 = [i for i in invs if i['id'] == alvo_id][0]
    print('  ajuda:', pg.inner_text('#tr-ajuda'))
    pg.screenshot(path=f'{SP}/shots/transferir.png')
    pg.click('[data-a="tr-ok"]'); pg.wait_for_timeout(1000)
    st = get('api/state')['investimentos']
    de1 = [i for i in st if i['id'] == de['id']][0]; para1 = [i for i in st if i['id'] == alvo_id][0]
    print('5 depois: de', de['valor'], '->', de1['valor'], '| para', para0['valor'], '->', para1['valor'], '| janela aberta', pg.locator('.folha').count(), '| aviso', pg.locator('.toast').all_inner_texts())
    # tudo e tirar da carteira
    pg.locator(f'.inv').first.click(); pg.wait_for_timeout(500)
    pg.click('[data-a="inv-transferir"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="tr-tudo"]'); pg.wait_for_timeout(300)
    print('6 tudo:', pg.inner_text('#tr-v') or pg.input_value('#tr-v'), '| escolha zerado:', pg.locator('[data-a="tr-apagar"]').all_inner_texts())
    pg.click('[data-a="tr-apagar"][data-v="1"]'); pg.wait_for_timeout(200)
    pg.locator('[data-a="tr-para"]').nth(0).click(); pg.wait_for_timeout(200)
    pg.click('[data-a="tr-ok"]'); pg.wait_for_timeout(1000)
    print('7 investimentos:', n0, '->', len(get('api/state')['investimentos']))
    # mais que o valor
    pg.locator('.inv').first.click(); pg.wait_for_timeout(500)
    pg.click('[data-a="inv-transferir"]'); pg.wait_for_timeout(400)
    pg.type('#tr-v', '999999999'); pg.locator('[data-a="tr-para"]').nth(0).click(); pg.click('[data-a="tr-ok"]'); pg.wait_for_timeout(300)
    print('8 demais:', pg.locator('.msg-erro').all_inner_texts())
    print('ERROS', erros); b.close()
