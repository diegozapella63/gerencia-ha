"""Evolução só com bens (sem investimentos seus nem aportes), numa tela estreita e com a fonte grande do Android: só a
linha dos bens, "Bens hoje" e quanto perdem (sem "+R$ 0 de rendimento"), e os números grandes cabem sem cortar nem se
sobrepor (também em Tudo)."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sem, sim, perto, valores
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'; INV = 'http://127.0.0.1:8098/'
def req(base, p, c=None, m='GET'):
    r = urllib.request.Request(base + p, data=json.dumps(c).encode() if c is not None else None, method=m, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
ITENS = [('Televisão', 'eletronicos', 60000, 20), ('Sofá', 'moveis', 45000, 10), ('Geladeira', 'cozinha', 30504, 10)]
sala = req(INV, 'api/rooms', {'name': 'Sala'}, 'POST')['room']['id']
for nome, cat, val, _ in ITENS:
    req(INV, 'api/items', {'room': sala, 'name': nome, 'cat': cat, 'value': val}, 'POST')
hoje_b = sum(v for _, _, v, _ in ITENS); em10 = sum(v * (1 - t / 100) ** 10 for _, _, v, t in ITENS)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 340, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1200)
    # só dinheiro de terceiros, como o de uma pessoa de fora
    d = req(B, 'api/state')
    d['investimentos'] = [i for i in d['investimentos'] if i.get('titular') == 'terceiros']
    d['recorrencias'] = [r for r in d['recorrencias'] if not r.get('aporte')]
    d['lancamentos'] = [l for l in d['lancamentos'] if not l.get('aporte')]
    req(B, 'api/state', d, 'PUT')
    pg.reload(); pg.wait_for_timeout(1200)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="evolucao"] >> nth=-1'); pg.wait_for_timeout(400)
    pg.click('[data-a="g"][data-k="gEscopo"][data-v="meu"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="g"][data-k="gAnos"][data-v="10"]'); pg.wait_for_timeout(600)
    # simula a fonte grande do Android: letras 50% maiores
    pg.add_style_tag(content='.stat-duo div b { font-size: 60px; } .hl-n { font-size: 40px; }'); pg.click('[data-a="g"][data-k="gAnos"][data-v="5"]'); pg.wait_for_timeout(300); pg.click('[data-a="g"][data-k="gAnos"][data-v="10"]'); pg.wait_for_timeout(500)
    def cabem(onde):
        bs = pg.locator('.stat-duo b'); r0 = bs.nth(0).bounding_box(); r1 = bs.nth(1).bounding_box()
        igual([bs.nth(i).evaluate('e => e.scrollWidth > e.clientWidth + 1') for i in range(2)], [False, False], f'{onde}: os números não ficam cortados')
        sim(r0['x'] + r0['width'] <= r1['x'] + 1, f'{onde}: um número não invade o outro', (r0, r1))
        fs = [bs.nth(i).evaluate('e => getComputedStyle(e).fontSize') for i in range(2)]
        sim(fs[0] == fs[1] and float(fs[0][:-2]) < 60, f'{onde}: a letra diminui, igual nos dois', fs)
        return [valores(t)[0] for t in bs.all_inner_texts()]
    v = cabem('Só o meu')
    igual(v, [round(hoje_b), round(em10)], 'Só o meu: os bens hoje e em 10 anos')
    duo = pg.inner_text('.stat-duo')
    igual(duo.split('\n')[0::2][:2], ['Bens hoje', 'Em 10 anos'], 'Só o meu: "Bens hoje" e "Em 10 anos"')
    tem(duo, 'perdem ' + 'R$ {:,.0f}'.format(round(hoje_b) - round(em10)).replace(',', '.'), 'Só o meu: quanto os bens perdem')
    sem(duo, 'rendimento', 'Só o meu: sem "+R$ 0 de rendimento"')
    igual([c for c in ['a-proj', 'l-apl', 'l-real', 'l-proj', 'l-bens'] if pg.locator(f'#ch-evo .{c}').count()], ['l-bens'], 'Só o meu: só a linha dos bens')
    igual(pg.inner_text('.leg').strip(), 'Bens', 'Só o meu: legenda só com Bens')
    pg.locator('.graf-card').first.screenshot(path=f'{SP}/shots/so-bens.png')
    pg.click('[data-a="g"][data-k="gEscopo"][data-v="tudo"]'); pg.wait_for_timeout(500)
    v2 = cabem('Tudo')
    sim(v2[0] > v[0], 'Tudo: soma o dinheiro de terceiros aos bens', (v, v2))
    print('ERROS', erros); b.close()
