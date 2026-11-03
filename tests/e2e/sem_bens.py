"""Ocultar bens e imóveis: na Evolução tira os bens do InventarIA do Hoje e do Em N anos (e a linha Bens), vale também
na Divisão e começa desligado de novo toda vez que o app abre."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sem, sim, perto, valores
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'; INV = 'http://127.0.0.1:8098/'
def req(base, p, c=None, m='GET'):
    r = urllib.request.Request(base + p, data=json.dumps(c).encode() if c is not None else None, method=m, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
sala = req(INV, 'api/rooms', {'name': 'Sala'}, 'POST')['room']['id']
req(INV, 'api/items', {'room': sala, 'name': 'Televisão', 'cat': 'eletronicos', 'value': 3000}, 'POST')
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="evolucao"] >> nth=-1'); pg.wait_for_timeout(500)
    anos = int(pg.inner_text('.chips.c5 .chip.on').split()[0])
    duo1 = pg.inner_text('.stat-duo')
    h1, f1 = valores(duo1.split('\n')[1])[0], valores(duo1.split('Em ')[1])[0]
    tem(duo1, 'com R$ 3.000 em bens', 'com bens: o Hoje soma os bens')
    perto(valores(duo1.split('bens −')[-1])[0] if 'bens −' in duo1 else None, round(3000 - 3000 * 0.8 ** anos), f'com bens: a televisão perde 20% a.a. em {anos} anos', tol=0.6)
    igual(pg.locator('#ch-evo .l-bens').count(), 1, 'com bens: a linha dos bens')
    sw = pg.locator('[data-k="gSemBens"]')
    igual((sw.count(), sw.get_attribute('aria-checked') if sw.count() else None), (1, 'false'), 'a chave Ocultar bens, desligada')
    sw.scroll_into_view_if_needed()
    pg.locator('.ctrl').screenshot(path=f'{SP}/shots/sem-bens-chave.png')
    sw.click(); pg.wait_for_timeout(500)
    duo2 = pg.inner_text('.stat-duo')
    h2, f2 = valores(duo2.split('\n')[1])[0], valores(duo2.split('Em ')[1])[0]
    igual(h1 - h2, 3000.0, 'sem bens: o Hoje sem os R$ 3.000')
    perto(f1 - f2, round(3000 * 0.8 ** anos), f'sem bens: o Em {anos} anos sem o que os bens valerão', tol=1)
    sem(duo2, 'bens', 'sem bens: nada de bens nos números')
    igual(pg.locator('#ch-evo .l-bens').count(), 0, 'sem bens: sem a linha dos bens')
    igual(duo2.split('\n')[-1], duo1.split('\n')[-1].split(' · bens')[0], 'sem bens: o rendimento dos investimentos não muda')
    pg.click('[data-a="inv-modo"][data-v="divisao"] >> nth=-1'); pg.wait_for_timeout(400)
    igual((pg.locator('.comp[data-v="_bens"]').count(), pg.get_attribute('[data-k="gSemBens"]', 'aria-checked')), (0, 'true'), 'Divisão: continua ligado, sem a fatia dos bens')
    pg.reload(); pg.wait_for_timeout(1200)
    igual(pg.get_attribute('[data-k="gSemBens"]', 'aria-checked'), 'false', 'ao abrir de novo, começa desligado')
    igual(pg.locator('.comp[data-v="_bens"]').count(), 1, 'e a fatia dos bens volta')
    print('ERROS', erros); b.close()
