"""Tipo Dinheiro (em espécie): o formulário só pede nome e valor (sem banco, rendimento, liquidez nem vencimento); salva
sem rendimento e aparece na Carteira como "Em espécie", sem render."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="f-tipo"][data-v="dinheiro"]'); pg.wait_for_timeout(300)
    vis = lambda t: pg.locator(f'.folha .campo:has(.lbl:text-is("{t}"))').first.is_visible() if pg.locator(f'.folha .campo:has(.lbl:text-is("{t}"))').count() else False
    igual({t: vis(t) for t in ('Banco', 'Rendimento', 'Liquidez')}, {'Banco': False, 'Rendimento': False, 'Liquidez': False}, 'Dinheiro: sem banco, rendimento nem liquidez')
    igual(pg.locator('#f-venc').is_visible() if pg.locator('#f-venc').count() else False, False, 'Dinheiro: sem vencimento')
    sim(pg.locator('#f-nome').is_visible() and pg.locator('#f-valor').is_visible(), 'Dinheiro: pede nome e valor')
    pg.fill('#f-nome', 'Dinheiro em casa'); pg.locator('#f-valor').click(); pg.keyboard.type('1500000')
    pg.screenshot(path=f'{SP}/shots/dinheiro.png')
    pg.click('[data-a="f-salvar"]:not([data-mais])'); pg.wait_for_timeout(900)
    o = [i for i in get('api/state')['investimentos'] if i['nome'] == 'Dinheiro em casa']
    igual([(i['tipo'], i['banco'], i['indexador'], i['taxa'], i['valor'], i['titular']) for i in o], [('dinheiro', '', 'parado', 0, 15000, 'meu')], 'salvo sem banco e sem rendimento')
    card = pg.locator('.inv:has-text("Dinheiro em casa")')
    igual(card.locator('.inv-meta').inner_text(), 'Em espécie', 'na Carteira: Em espécie')
    tem(card.inner_text(), 'R$ 15.000,00', 'com o valor')
    tem(card.locator('.inv-pe').inner_text(), 'Não rende', 'não rende')
    print('ERROS', erros); b.close()
