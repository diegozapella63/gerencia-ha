"""Telas principais com o exemplo (capturas): Início com o cumprimento e o caixa do mês, Caixa (lista, fluxo com o
dedo no gráfico e categorias) e a Evolução do Invest; confere que os números de cada tela fecham entre si."""
import sys
from datetime import date
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, perto, valores, valores_s
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
SP=sys.argv[1]; erros=[]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':396,'height':860}, device_scale_factor=2, color_scheme='dark', extra_http_headers={'X-Remote-User-Display-Name': 'Ana Souza'})
    pg.on('pageerror', lambda e: erros.append('PAGEERROR '+str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type=='error' else None)
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1200)
    tem(pg.inner_text('.cab .eyebrow').lower(), 'olá, ana', 'Início: cumprimenta pelo primeiro nome')
    tem(pg.get_attribute('.placar-num', 'aria-label'), 'Patrimônio de R$', 'Início: o placar do patrimônio')
    igual(pg.inner_text('.cx-card .rot-t'), f'Caixa de {MESES[date.today().month - 1]}', 'Início: o caixa do mês atual')
    resumo_inicio = pg.inner_text('.cx-card .cx-resumo')
    pg.screenshot(path=f'{SP}/shots/c1-inicio.png', full_page=True)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(500)
    igual(pg.inner_text('.cx-lado .cx-resumo'), resumo_inicio, 'Caixa: o mesmo resumo do Início')
    ent, sai, sob = (valores_s(pg.inner_text(f'.cx-lado .cx-resumo > div:nth-child({k}) b'))[0] for k in (1, 2, 3))
    sim(abs(sob - (ent - sai)) <= 1, 'Caixa: sobrou = entrou − saiu', (ent, sai, sob))
    sim(pg.locator('.cx-lista .lanc').count() > 5, 'Caixa: os lançamentos do mês', pg.locator('.cx-lista .lanc').count())
    pg.screenshot(path=f'{SP}/shots/c2-caixa.png', full_page=True)
    pg.click('[data-a="cx-modo"][data-v="fluxo"]'); pg.wait_for_timeout(500)
    igual(pg.inner_text('.chips.c4 .chip.on'), '6 + 6', 'Fluxo: começa em 6 + 6')
    igual(pg.locator('#ch-fluxo .pt-net').count(), 12, 'Fluxo: 12 meses no gráfico')
    box=pg.locator('#ch-fluxo').bounding_box(); pg.mouse.move(box['x']+box['width']*0.62, box['y']+80); pg.wait_for_timeout(200)
    sim(pg.locator('#ch-fluxo .tip').is_visible(), 'Fluxo: o dedo no gráfico mostra o mês')
    tip = pg.evaluate("() => [...document.querySelectorAll('#ch-fluxo .tip .t-r')].map(r => [r.querySelector('span').textContent, r.querySelector('b').textContent])")
    linhas = {n: valores_s(v)[0] for n, v in tip}
    conta = linhas.get('Entradas', 0) - linhas.get('Saídas', linhas.get('Saídas lançadas', 0)) - linhas.get('Aportes', 0) - linhas.get('Dia a dia (média)', 0)
    sim('Sobrou' in linhas and abs(linhas['Sobrou'] - conta) <= 2, 'Fluxo: no mês tocado, sobrou = entradas − saídas − aportes − dia a dia', linhas)
    pg.screenshot(path=f'{SP}/shots/c3-fluxo.png', full_page=True)
    pg.click('[data-a="cx-modo"][data-v="categorias"]'); pg.wait_for_timeout(500)
    total = valores(pg.inner_text('.stat-duo > div:nth-child(1) b'))[0]
    vls = pg.locator('.comps .vl').all_inner_texts()
    sim(abs(sum(valores(v)[0] for v in vls) - total) <= len(vls), 'Categorias: as categorias somam os gastos do mês', (total, vls))
    pcts = [float(v.split('%')[0].replace(',', '.')) for v in pg.locator('.comps .vl small').all_inner_texts()]
    sim(abs(sum(pcts) - 100) <= 0.1 * len(pcts), 'Categorias: as porcentagens somam 100%', pcts)
    pg.screenshot(path=f'{SP}/shots/c4-cat.png', full_page=True)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="inv-modo"][data-v="evolucao"]'); pg.wait_for_timeout(400)
    igual(pg.locator('#ch-evo svg').count(), 1, 'Evolução: o gráfico')
    duo = pg.inner_text('.stat-duo')
    tem(duo, 'Em 5 anos', 'Evolução: projeção de 5 anos')
    h, f = valores(duo)[:2]
    sim(f > h > 0, 'Evolução: em 5 anos vale mais que hoje', (h, f))
    pg.screenshot(path=f'{SP}/shots/c5-inv-evo.png')
    print('ERROS', erros); b.close()
