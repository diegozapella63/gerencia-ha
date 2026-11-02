import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'; INV = 'http://127.0.0.1:8098/'
def req(base, p, c=None, m='GET'):
    r = urllib.request.Request(base + p, data=json.dumps(c).encode() if c is not None else None, method=m, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
# InventarIA com itens inventados (nenhum dado real)
sala = req(INV, 'api/rooms', {'name': 'Sala'}, 'POST')['room']['id']
coz = req(INV, 'api/rooms', {'name': 'Cozinha'}, 'POST')['room']['id']
for nome, cat, val, room in [('Televisão 55"', 'eletronicos', 3000, sala), ('Sofá 3 lugares', 'moveis', 2500, sala), ('Notebook', 'eletronicos', 4200, sala), ('Geladeira', 'cozinha', 3800, coz), ('Quadro', 'decoracao', 600, sala)]:
    req(INV, 'api/items', {'room': room, 'name': nome, 'cat': cat, 'value': val}, 'POST')
print('1 bens api:', {k: v for k, v in req(B, 'api/bens').items() if k in ('ok', 'hoje', 'registrado', 'perde_ano', 'n', 'motivo')})
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    print('2 placar:', pg.get_attribute('.placar-num', 'aria-label'), '| colunas:', pg.inner_text('.placar-cols').replace('\n', ' '))
    print('  destaque:', pg.locator('.hl-row[data-a="bens"]').inner_text().replace('\n', ' | ') if pg.locator('.hl-row[data-a="bens"]').count() else '-')
    pg.locator('.placar').screenshot(path=f'{SP}/shots/bens-placar.png')
    pg.click('.hl-row[data-a="bens"]'); pg.wait_for_timeout(500)
    print('3 janela:', pg.inner_text('.folha-cab h2'), '|', pg.inner_text('.folha .stat-duo').replace('\n', ' '))
    pg.screenshot(path=f'{SP}/shots/bens-janela.png')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="mais-aba"][data-v="integracoes"]'); pg.wait_for_timeout(800)
    print('4 quadro:', pg.inner_text('#bens').replace('\n', ' | ')[:300])
    pg.click('[data-a="mais-aba"][data-v="invest"]'); pg.wait_for_timeout(500)
    print('  tabela em Mais › Invest:', pg.inner_text('#perda-bens').replace(chr(10), ' | ')[:160])
    pg.fill('[data-bens-taxa="eletronicos"]', '30'); pg.press('[data-bens-taxa="eletronicos"]', 'Tab'); pg.wait_for_timeout(1200)
    print('  taxa salva:', req(B, 'api/state')['ajustes'].get('bens_taxas'))
    pg.wait_for_timeout(800)
    pg.click('[data-a="mais-aba"][data-v="integracoes"]'); pg.wait_for_timeout(500)
    pg.click('[data-a="ajuste"][data-k="bens"]'); pg.wait_for_timeout(800)
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(500)
    print('5 desligado: placar', pg.get_attribute('.placar-num', 'aria-label'), '| destaque', pg.locator('.hl-row[data-a="bens"]').count())
    print('ERROS', erros); b.close()
