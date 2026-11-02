"""Transferir entre investimentos: valor, destino, tudo (e tirar da carteira) e mais do que tem."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, perto, valores
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
    igual(pg.locator('.inv-acoes .btn').all_inner_texts(), ['Aplicar mais', 'Transferir'], 'botões lado a lado')
    larg = [round(pg.locator('.inv-acoes .btn').nth(i).bounding_box()['width']) for i in range(pg.locator('.inv-acoes .btn').count())]
    igual(len(set(larg)), 1, f'do mesmo tamanho {larg}')
    pg.locator('.inv-aplicar').screenshot(path=f'{SP}/shots/inv-acoes.png')
    pg.click('[data-a="inv-transferir"]'); pg.wait_for_timeout(500)
    tit = pg.inner_text('.folha-cab h2'); tem(tit, 'Transferir de ', 'janela Transferir')
    igual(pg.locator('[data-a="tr-para"]').count(), n0 - 1, 'destinos: todos os outros')
    de_nome = tit.replace('Transferir de ', '')
    de = [i for i in invs if i['nome'] == de_nome][0]
    pg.click('[data-a="tr-ok"]'); pg.wait_for_timeout(300)
    igual(pg.locator('.msg-erro').all_inner_texts(), ['Coloque o valor.'], 'sem valor não transfere')
    pg.fill('#tr-v', ''); pg.type('#tr-v', '500000'); pg.wait_for_timeout(200)
    igual(pg.inner_text('[data-a="tr-ok"]'), 'Transferir R$ 5.000', 'o valor no botão')
    pg.click('[data-a="tr-ok"]'); pg.wait_for_timeout(300)
    igual(pg.locator('.msg-erro').all_inner_texts(), ['Escolha para onde vai o dinheiro.'], 'sem destino não transfere')
    alvo = pg.locator('[data-a="tr-para"]').nth(1); alvo_id = alvo.get_attribute('data-v'); alvo.click(); pg.wait_for_timeout(300)
    para0 = [i for i in invs if i['id'] == alvo_id][0]
    fica, para_antes, para_depois = valores(pg.inner_text('#tr-ajuda'))
    perto(para_depois - para_antes, 5000, 'mostra como fica o destino')
    pg.screenshot(path=f'{SP}/shots/transferir.png')
    pg.click('[data-a="tr-ok"]'); pg.wait_for_timeout(1000)
    st = get('api/state')['investimentos']
    de1 = [i for i in st if i['id'] == de['id']][0]; para1 = [i for i in st if i['id'] == alvo_id][0]
    perto(de1['valor'], fica, 'a origem fica com o que foi mostrado')
    perto(para1['valor'], para_depois, 'o destino recebe')
    igual(pg.locator('.folha').count(), 0, 'a janela fecha')
    # tudo e tirar da carteira
    pg.locator(f'.inv').first.click(); pg.wait_for_timeout(500)
    pg.click('[data-a="inv-transferir"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="tr-tudo"]'); pg.wait_for_timeout(300)
    sim(valores('R$ ' + pg.input_value('#tr-v'))[0] > 0, 'Tudo preenche o valor de hoje')
    igual(pg.locator('[data-a="tr-apagar"]').all_inner_texts(), ['Manter na carteira', 'Tirar da carteira'], 'tudo: pergunta se tira da carteira')
    pg.click('[data-a="tr-apagar"][data-v="1"]'); pg.wait_for_timeout(200)
    pg.locator('[data-a="tr-para"]').nth(0).click(); pg.wait_for_timeout(200)
    pg.click('[data-a="tr-ok"]'); pg.wait_for_timeout(1000)
    igual(len(get('api/state')['investimentos']), n0 - 1, 'zerado e tirado da carteira')
    # mais que o valor
    pg.locator('.inv').first.click(); pg.wait_for_timeout(500)
    pg.click('[data-a="inv-transferir"]'); pg.wait_for_timeout(400)
    pg.type('#tr-v', '999999999'); pg.locator('[data-a="tr-para"]').nth(0).click(); pg.click('[data-a="tr-ok"]'); pg.wait_for_timeout(300)
    tem(' '.join(pg.locator('.msg-erro').all_inner_texts()), 'Passa do valor de hoje', 'mais do que tem: recusa')
    print('ERROS', erros); b.close()
