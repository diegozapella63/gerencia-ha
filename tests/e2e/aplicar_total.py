"""Aplicar pelo total: diz quanto tem agora e o app calcula o aporte (e recusa um total menor)."""
import sys, json, urllib.request
from datetime import date
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
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(500)
    pg.locator('.inv').first.click(); pg.wait_for_timeout(500)
    igual(pg.locator('[data-a="f-foto-ia"]').count(), 0, 'sem imagem, sem o botão de ler')
    iid = pg.get_attribute('[data-a="inv-aplicar"]', 'data-v')
    pg.click('[data-a="inv-aplicar"]'); pg.wait_for_timeout(500)
    pg.click('[data-a="ap-modo"][data-v="total"]'); pg.wait_for_timeout(300)
    igual(pg.inner_text('label[for="ap-v"]'), 'Quanto tem agora, no total', 'pelo total: o rótulo muda')
    tem(pg.inner_text('#ap-ajuda'), 'Hoje: R$', 'mostra o valor de hoje')
    hoje = valores(pg.inner_text('#ap-ajuda'))[0]
    pg.type('#ap-v', '1000000'); pg.wait_for_timeout(200)
    tem(pg.inner_text('#ap-ajuda'), 'É menos que', 'total menor: avisa')
    igual(pg.inner_text('[data-a="ap-ok"]'), 'Aplicar', 'sem aporte, sem valor no botão')
    pg.click('[data-a="ap-ok"]'); pg.wait_for_timeout(300)
    tem(' '.join(pg.locator('.msg-erro').all_inner_texts()), 'O total precisa ser maior', 'total menor não salva')
    pg.fill('#ap-v', ''); pg.type('#ap-v', '3000000'); pg.wait_for_timeout(200)
    v = valores(pg.inner_text('#ap-ajuda'))
    perto(v[0], 30000 - hoje, 'o aporte é a diferença')
    igual(v[1:], [hoje, 30000.0], 'de quanto para quanto')
    pg.click('[data-a="ap-destino"][data-v="nenhum"]'); pg.wait_for_timeout(200)
    igual(pg.input_value('#ap-v'), '30.000,00', 'trocar a opção do caixa não apaga o valor')
    pg.screenshot(path=f'{SP}/shots/aplicar-total.png')
    pg.click('[data-a="ap-ok"]'); pg.wait_for_timeout(900)
    inv = [i for i in get('api/state')['investimentos'] if i['id'] == iid][0]
    igual((inv['valor'], inv['data_valor']), (30000, date.today().isoformat()), 'fica com o total, com a data de hoje')
    igual(pg.locator('.folha').count(), 0, 'a janela fecha')
    print('ERROS', erros); b.close()
