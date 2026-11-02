import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'; INV = 'http://127.0.0.1:8098/'
def req(base, p, c=None, m='GET'):
    r = urllib.request.Request(base + p, data=json.dumps(c).encode() if c is not None else None, method=m, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
sala = req(INV, 'api/rooms', {'name': 'Sala'}, 'POST')['room']['id']
for nome, cat, val in [('Televisão', 'eletronicos', 60000), ('Sofá', 'moveis', 45000), ('Geladeira', 'cozinha', 30504)]:
    req(INV, 'api/items', {'room': sala, 'name': nome, 'cat': cat, 'value': val}, 'POST')
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 340, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1200)
    # só dinheiro de terceiros, como o de uma pessoa de fora
    d = req(B, 'api/state')
    d['investimentos'] = [i for i in d['investimentos'] if i.get('titular') == 'terceiros']
    d['recorrencias'] = [r for r in d['recorrencias'] if not r.get('aporte')]
    d['lancamentos'] = [l for l in d['lancamentos'] if not l.get('aporte')]
    req(B, 'api/state', {'d': d, 'rev': d['rev']} if False else d, 'PUT')
    pg.reload(); pg.wait_for_timeout(1200)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="evolucao"] >> nth=-1'); pg.wait_for_timeout(400)
    pg.click('[data-a="g"][data-k="gEscopo"][data-v="meu"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="g"][data-k="gAnos"][data-v="10"]'); pg.wait_for_timeout(600)
    # simula a fonte grande do Android: letras 50% maiores
    pg.add_style_tag(content='.stat-duo div b { font-size: 60px; } .hl-n { font-size: 40px; }'); pg.click('[data-a="g"][data-k="gAnos"][data-v="5"]'); pg.wait_for_timeout(300); pg.click('[data-a="g"][data-k="gAnos"][data-v="10"]'); pg.wait_for_timeout(500)
    bs = pg.locator('.stat-duo b'); r0 = bs.nth(0).bounding_box(); r1 = bs.nth(1).bounding_box()
    print('  cortado:', [bs.nth(i).evaluate('e => e.scrollWidth > e.clientWidth + 1') for i in range(2)])
    print('1 números:', bs.all_inner_texts(), '| sobrepõe:', r0['x'] + r0['width'] > r1['x'] + 1, '| letra', [bs.nth(i).evaluate('e => getComputedStyle(e).fontSize') for i in range(2)])
    print('  textos:', pg.inner_text('.stat-duo').replace('\n', ' | '), '| linhas', [c for c in ['a-proj', 'l-apl', 'l-real', 'l-proj', 'l-bens'] if pg.locator(f'#ch-evo .{c}').count()], '| legenda', pg.inner_text('.leg'))
    pg.locator('.graf-card').first.screenshot(path=f'{SP}/shots/so-bens.png')
    pg.click('[data-a="g"][data-k="gEscopo"][data-v="tudo"]'); pg.wait_for_timeout(500)
    bs = pg.locator('.stat-duo b'); r0 = bs.nth(0).bounding_box(); r1 = bs.nth(1).bounding_box()
    print('2 tudo:', bs.all_inner_texts(), '| sobrepõe:', r0['x'] + r0['width'] > r1['x'] + 1)
    print('ERROS', erros); b.close()
