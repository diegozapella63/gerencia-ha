"""Quadro Dicas de economia no Início (tema escuro e claro): uma dica por assinatura com plano anual conferido (Nabu Casa
e Spotify do exemplo), a economia real (desconto menos o que o dinheiro renderia), a fonte e o total no alto."""
import sys
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, valores
SP=sys.argv[1]; erros=[]
textos = {}
with sync_playwright() as p:
    b=p.chromium.launch()
    for esquema in ('dark','light'):
        pg=b.new_page(viewport={'width':396,'height':860}, device_scale_factor=2, color_scheme=esquema)
        pg.on('pageerror', lambda e: erros.append('PAGEERROR '+str(e)))
        pg.on('console', lambda m: erros.append(m.text) if m.type=='error' else None)
        pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
        if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]')
        pg.wait_for_timeout(9000)
        c=pg.locator('.card.dicas'); c.scroll_into_view_if_needed()
        igual(c.count(), 1, f'{esquema}: o quadro de dicas no Início')
        subs = pg.locator('.card.dicas .dica:has([data-a="dica-anual"])')
        nomes = sorted(x.split(' no plano anual')[0] for x in subs.locator('.dica-t b').all_inner_texts())
        igual(nomes, ['Nabu Casa', 'Spotify'], f'{esquema}: dicas do plano anual das assinaturas do exemplo')
        soma = 0
        for i in range(subs.count()):
            d = subs.nth(i)
            v = valores(d.locator('.dica-v').inner_text())[0]; soma += v
            desc, rende = valores(d.locator('.dica-calc').inner_text())[:2]
            nome = d.locator('.dica-t b').inner_text()
            sim(abs(v - (desc - rende)) <= 1, f'{esquema}: {nome}: economia = desconto − o que renderia', (v, desc, rende))
            tem(d.locator('.dica-fonte').inner_text(), 'Preço conferido em', f'{esquema}: {nome}: com a fonte do preço')
            igual([x.strip() for x in d.locator('.dica-acoes .btn').all_inner_texts()], ['Mudar para anual', 'Agora não'], f'{esquema}: {nome}: botões')
        topo = c.locator('.rot b').inner_text()
        tem(topo, 'até R$', f'{esquema}: o total no alto (até, com mais de uma dica)')
        sim(abs(valores(topo)[0] - soma) <= subs.count(), f'{esquema}: o total soma as dicas', (topo, soma))
        textos[esquema] = c.inner_text()
        c.screenshot(path=f'{SP}/shots/e8-card-{esquema}.png')
        pg.close()
    igual(textos.get('dark'), textos.get('light'), 'o mesmo quadro nos dois temas')
    print('ERROS', erros); b.close()
