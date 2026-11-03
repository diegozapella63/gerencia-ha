"""Bens da casa (InventarIA) na Carteira: um cartão só de leitura em Todos e em Meus (não em Terceiros), com o total,
os itens e a perda por mês; ele abre Bens da casa, com quanto valem em 1, 5 e 10 anos, e o Ver na Evolução."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, perto, valores
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'; INV = 'http://127.0.0.1:8098/'
def req(base, p, c=None, m='GET'):
    r = urllib.request.Request(base + p, data=json.dumps(c).encode() if c is not None else None, method=m, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
ITENS = [('Televisão', 'eletronicos', 3000, 20), ('Sofá', 'moveis', 2500, 10)]  # perda por ano padrão: eletrônicos 20%, móveis 10%
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
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(400)
    for f, n in (('todos', 1), ('meus', 1), ('terc', 0)):
        pg.click(f'[data-a="filtro"][data-v="{f}"]'); pg.wait_for_timeout(300)
        igual(pg.locator('.inv-ro').count(), n, f'cartão dos bens no filtro {f}: {n}')
    pg.click('[data-a="filtro"][data-v="meus"]'); pg.wait_for_timeout(300)
    c = pg.locator('.inv-ro'); c.scroll_into_view_if_needed()
    txt = c.inner_text().split('\n')
    igual(txt[:5], ['Bens da casa', 'R$ 5.500,00', 'InventarIA · 2 itens', 'Só leitura', 'Meu'], 'cartão: nome, total, itens, só leitura e dono')
    perto(valores(c.inner_text())[1], round((3000 * 0.20 + 2500 * 0.10) / 12, 2), 'cartão: perde por mês (a perda do ano / 12)')
    tem(c.inner_text(), 'o valor muda no InventarIA', 'cartão: diz onde muda o valor')
    c.screenshot(path=f'{SP}/shots/bens-carteira.png')
    c.click(); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Bens da casa', 'o cartão abre Bens da casa')
    evo = pg.inner_text('.bens-evo')
    for anos, v in zip((1, 5, 10), valores(evo)):
        perto(v, round(em(anos)), f'quanto valem em {anos} {"ano" if anos == 1 else "anos"} (cada categoria perde a sua taxa)', tol=0.6)
    igual(len(valores(evo)), 3, 'em 1, 5 e 10 anos')
    pg.screenshot(path=f'{SP}/shots/bens-janela2.png')
    pg.click('[data-a="bens-evolucao"]'); pg.wait_for_timeout(600)
    igual(pg.locator('.folha').count(), 0, 'Ver na Evolução fecha a janela')
    igual(pg.locator('[data-a="inv-modo"].on').first.inner_text(), 'Evolução', 'e abre a Evolução')
    igual(pg.locator('#ch-evo .l-bens').count(), 1, 'com a linha dos bens')
    print('ERROS', erros); b.close()
