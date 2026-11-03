"""Tipo Ouro: vem com Estimado de 10% a.a. (o valor de hoje não corrige sozinho), mostra quanto rende por mês e salva
com liquidez diária."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
rende = lambda v, t: v * ((1 + t / 100) ** (1 / 12) - 1)
brl = lambda v: f'R$ {v:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    sel = pg.locator('[data-a="f-tipo"][data-v="ouro"]')
    igual(sel.count(), 1, 'o tipo Ouro no formulário'); sel.first.click(); pg.wait_for_timeout(300)
    pg.fill('#f-nome', 'Ouro 10g')
    v = pg.locator('[data-f="valor"]'); v.click(); pg.keyboard.type('860000'); pg.wait_for_timeout(200)
    igual(pg.inner_text('#aj-taxa'), f'Estimativa sua, ≈ 10% a.a. Entra na projeção, mas o valor de hoje não é corrigido sozinho. · rende ≈ {brl(round(rende(8600, 10), 2))} por mês', 'Ouro: estimado em 10% a.a., com quanto rende por mês')
    pg.screenshot(path=f'{SP}/shots/ouro.png')
    pg.click('.folha-pe .btn.pri'); pg.wait_for_timeout(900)
    o = [i for i in get('api/state')['investimentos'] if i['nome'] == 'Ouro 10g']
    igual([(i['tipo'], i['indexador'], i['taxa'], i['liquidez'], i['valor']) for i in o], [('ouro', 'estimado', 10, 'diaria', 8600)], 'salvo como ouro, estimado 10% a.a., liquidez diária')
    card = pg.locator('.inv:has-text("Ouro 10g")')
    igual(card.count(), 1, 'na Carteira')
    if card.count(): tem(card.locator('.inv-pe').inner_text(), f'≈ {brl(round(rende(8600, 10), 2))} por mês', 'o cartão com quanto rende por mês')
    print('ERROS', erros); b.close()
