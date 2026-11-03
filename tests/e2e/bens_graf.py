"""Bens da casa (InventarIA) nos gráficos do Invest: uma fatia própria na Divisão (fora em De terceiros) e, na Evolução,
somados no Hoje e no Em N anos, com a perda de valor, a linha Bens, a legenda e a coluna Bens na tabela por ano."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, perto, valores
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'; INV = 'http://127.0.0.1:8098/'
def req(base, p, c=None, m='GET'):
    r = urllib.request.Request(base + p, data=json.dumps(c).encode() if c is not None else None, method=m, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
ITENS = [('Televisão', 'eletronicos', 3000, 20), ('Sofá', 'moveis', 2500, 10), ('Notebook', 'eletronicos', 4200, 20)]
sala = req(INV, 'api/rooms', {'name': 'Sala'}, 'POST')['room']['id']
for nome, cat, val, _ in ITENS:
    req(INV, 'api/items', {'room': sala, 'name': nome, 'cat': cat, 'value': val}, 'POST')
em = lambda anos: sum(v * (1 - t / 100) ** anos for _, _, v, t in ITENS)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="divisao"] >> nth=-1'); pg.wait_for_timeout(500)
    comps = pg.locator('.comp').all_inner_texts()
    nomes = [x.split('\n')[0] for x in comps]
    sim(set(nomes) == {'Corretora Norte', 'Banco Lua', 'Banco Coral', 'Banco Sol', 'Banco Azul', 'Banco Verde', 'Bens da casa'}, 'Divisão por banco com a fatia Bens da casa', nomes)
    total = valores(pg.inner_text('.stat-duo b >> nth=0'))[0]
    sim(abs(sum(valores(x)[-1] for x in comps) - total) <= len(comps), 'as fatias somam o total', (total, comps))
    bens = pg.locator('.comp[data-v="_bens"]').inner_text().split('\n')
    igual(bens[:3], ['Bens da casa', '3 itens · perdem ≈ R$ 1.690/ano', 'R$ 9.700'], 'fatia dos bens: itens, perda por ano e valor')
    perto(float(bens[3].rstrip('%').replace(',', '.')), round(9700 / total * 100, 1), 'fatia dos bens: a porcentagem do total', tol=0.051)
    pg.locator('.graf-card').first.screenshot(path=f'{SP}/shots/bens-divisao.png')
    pg.click('[data-a="g"][data-k="gEscopo"][data-v="terc"]'); pg.wait_for_timeout(300)
    igual(pg.locator('.comp[data-v="_bens"]').count(), 0, 'De terceiros: sem os bens')
    pg.click('[data-a="g"][data-k="gEscopo"][data-v="meu"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="evolucao"] >> nth=-1'); pg.wait_for_timeout(600)
    pg.click('[data-a="g"][data-k="gAnos"][data-v="10"]'); pg.wait_for_timeout(500)
    duo = pg.inner_text('.stat-duo')
    tem(duo, 'com R$ 9.700 em bens', 'Evolução: o Hoje soma os bens')
    perto(valores(duo.split('bens ')[-1])[0] if 'bens −' in duo else None, round(9700 - em(10)), 'Evolução: em 10 anos, os bens perdem a taxa de cada categoria', tol=0.6)
    igual(pg.locator('#ch-evo .l-bens').count(), 1, 'Evolução: a linha dos bens')
    tem(pg.inner_text('.leg'), 'Bens', 'Evolução: Bens na legenda')
    pg.click('details.card summary'); pg.wait_for_timeout(200)
    igual(pg.locator('.tabela thead th').all_inner_texts(), ['Quando', 'Projetado', 'Rendeu', 'Em dinheiro de hoje', 'Bens'], 'tabela por ano com a coluna Bens')
    igual(pg.locator('.tabela tbody tr').count(), 10, 'uma linha por ano')
    perto(valores(pg.locator('.tabela tbody tr').first.locator('td').last.inner_text())[0], round(em(1)), 'tabela: os bens em 1 ano', tol=0.6)
    perto(valores(pg.locator('.tabela tbody tr').last.locator('td').last.inner_text())[0], round(em(10)), 'tabela: os bens em 10 anos', tol=0.6)
    larg = pg.evaluate("() => { const t = document.querySelector('.tabela-rola'); return [t.scrollWidth, t.clientWidth] }")
    sim(larg[0] <= larg[1], 'a tabela cabe no celular, sem rolar para o lado', larg)
    pg.locator('.graf-card').first.screenshot(path=f'{SP}/shots/bens-evolucao.png')
    print('ERROS', erros); b.close()
