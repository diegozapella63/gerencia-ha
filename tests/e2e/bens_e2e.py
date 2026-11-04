"""Bens da casa (InventarIA): somados no patrimônio, janela, quadro em Mais, perda por categoria e desligar."""
import sys, json, re, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, valores, ir_mais
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
igual({k: v for k, v in req(B, 'api/bens').items() if k in ('ok', 'hoje', 'registrado', 'perde_ano', 'n', 'motivo')},
      {'ok': True, 'hoje': 14100.0, 'registrado': 14100.0, 'perde_ano': 2100.0, 'n': 5}, 'os 5 itens do InventarIA, com a perda por ano')
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    total = valores(pg.get_attribute('.placar-num', 'aria-label'))[0]
    investido, bens = valores(pg.inner_text('.placar-cols'))[:2]
    igual(bens, 14100.0, 'bens no placar')
    sim(abs(total - (investido + bens)) <= 1, 'patrimônio = investido + bens', (total, investido, bens))
    destaque = pg.locator('.hl-row[data-a="bens"]').inner_text() if pg.locator('.hl-row[data-a="bens"]').count() else ''
    tem(destaque, '5 itens no InventarIA', 'destaque dos bens')
    tem(destaque, 'perdem ≈ R$ 2.100/ano', 'com a perda por ano')
    pg.locator('.placar').screenshot(path=f'{SP}/shots/bens-placar.png')
    pg.click('.hl-row[data-a="bens"]'); pg.wait_for_timeout(500)
    igual(pg.inner_text('.folha-cab h2'), 'Bens da casa', 'janela dos bens')
    igual(valores(pg.inner_text('.folha .stat-duo')), [14100.0, 14100.0, 2100.0], 'hoje, registrado e perda por ano')
    pg.screenshot(path=f'{SP}/shots/bens-janela.png')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    ir_mais(pg, 'config', 'integracoes', 800)
    tem(pg.inner_text('#bens'), 'Ligado: R$ 14.100 em 5 itens.', 'quadro em Mais › Configurações › Integrações')
    ir_mais(pg, 'invest', espera=500)
    tem(pg.inner_text('#perda-bens'), 'Eletrônicos', 'perda por categoria em Mais › Invest')
    pg.fill('[data-bens-taxa="eletronicos"]', '30'); pg.press('[data-bens-taxa="eletronicos"]', 'Tab'); pg.wait_for_timeout(1200)
    igual(req(B, 'api/state')['ajustes'].get('bens_taxas'), {'eletronicos': 30}, 'a perda escolhida fica salva')
    pg.wait_for_timeout(800)
    ir_mais(pg, 'config', 'integracoes', 500)
    pg.click('[data-a="ajuste"][data-k="bens"]'); pg.wait_for_timeout(800)
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(500)
    sim(abs(valores(pg.get_attribute('.placar-num', 'aria-label'))[0] - investido) <= 1, 'desligado: o patrimônio volta a ser só o investido')
    igual(pg.locator('.hl-row[data-a="bens"]').count(), 0, 'desligado: sem o destaque dos bens')
    print('ERROS', erros); b.close()
