"""Alinhamento dos pares de valores e das categorias: no Caixa › Categorias, o valor do mês e a média na mesma linha,
as barras todas com a mesma largura e os percentuais com uma casa; no Fluxo e no Invest, cada par de valores na mesma altura."""
import re, sys
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
SP = sys.argv[1]; erros = []
TOPOS = "() => [...document.querySelectorAll('.stat-duo')].map(d => [...d.querySelectorAll(':scope > div > b')].map(b => Math.round(b.getBoundingClientRect().top)))"
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    def pares(onde):
        ys = pg.evaluate(TOPOS)
        sim(ys and all(len(set(y)) == 1 for y in ys), f'{onde}: cada par de valores na mesma altura', ys)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="cx-modo"][data-v="categorias"]'); pg.wait_for_timeout(600)
    ys = pg.evaluate(TOPOS)
    igual([len(y) for y in ys], [2], 'Categorias: o valor do mês e a média')
    pares('Categorias')
    bars = pg.evaluate("() => [...document.querySelectorAll('.comps .barra')].map(b => [Math.round(b.getBoundingClientRect().left), Math.round(b.getBoundingClientRect().width)])")
    sim(len(bars) > 2 and len(set(map(tuple, bars))) == 1, 'Categorias: as barras começam no mesmo ponto e têm a mesma largura', bars)
    pcts = pg.locator('.comps .vl small').all_inner_texts()
    sim(pcts and all(re.match(r'^\d+,\d%', x) for x in pcts), 'Categorias: percentuais com uma casa', pcts)
    pg.locator('.graf-card').screenshot(path=f'{SP}/shots/cat-alinha.png')
    pg.click('[data-a="cx-modo"][data-v="fluxo"]'); pg.wait_for_timeout(600)
    igual([len(y) for y in pg.evaluate(TOPOS)], [2, 2], 'Fluxo: dois pares (sobrou e saldo)')
    pares('Fluxo')
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(400)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(400)
    for modo, nome in (('evolucao', 'Evolução'), ('divisao', 'Divisão')):
        pg.click(f'[data-a="inv-modo"][data-v="{modo}"] >> nth=-1'); pg.wait_for_timeout(500)
        pares(f'Invest › {nome}')
    print('ERROS', erros); b.close()
