"""Buscar no alto do Invest (acima de Carteira, Evolução e Divisão): digitar nele abre a Carteira com o que achou,
sem perder o foco; com a IA desligada, as dicas dizem que os planos anuais precisam da IA e somem com o Conferir agora."""
import sys, json
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, estado
SP = sys.argv[1]; erros = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(500)
    yb = pg.locator('.inv-busca').bounding_box()['y']; ys = pg.locator('[data-a="inv-modo"]').first.bounding_box()['y']
    sim(yb < ys, 'a busca fica acima de Carteira, Evolução e Divisão', (yb, ys))
    pg.screenshot(path=f'{SP}/shots/invest-topo.png')
    pg.click('[data-a="inv-modo"][data-v="evolucao"] >> nth=-1'); pg.wait_for_timeout(500)
    pg.click('#q'); pg.keyboard.type('cdb'); pg.wait_for_timeout(500)
    igual(pg.locator('[data-a="inv-modo"].on').inner_text(), 'Carteira', 'digitar na Evolução abre a Carteira')
    esperado = sorted(i['nome'] for i in estado(pg)['investimentos'] if 'cdb' in i['nome'].lower())
    igual(sorted(pg.locator('.inv .inv-nome').all_inner_texts()), esperado, 'mostra os CDBs')
    igual((pg.evaluate('document.activeElement.id'), pg.input_value('#q')), ('q', 'cdb'), 'o cursor continua na busca, com o que foi digitado')
    # IA desligada: dicas
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="mais-aba"][data-v="integracoes"]'); pg.wait_for_timeout(600)
    pg.click('[data-a="ajuste"][data-k="ia"]'); pg.wait_for_timeout(800)
    igual(estado(pg)['ajustes'].get('ia'), False, 'Usar IA desligado e salvo')
    pg.click('[data-a="mais-aba"][data-v="caixa"]'); pg.wait_for_timeout(600)
    igual(pg.locator('#dicas .status').all_inner_texts(), ['Com a IA desligada, os planos anuais não são conferidos.'], 'Dicas: com a IA desligada, planos anuais não são conferidos')
    igual(pg.locator('[data-a="dicas-conferir"]').count(), 0, 'sem o Conferir agora')
    pg.click('[data-a="mais-aba"][data-v="opcoes"]'); pg.wait_for_timeout(500)
    tem(pg.inner_text('#op-inicio'), 'Planos anuais precisam da IA.', 'Opções: a dica do Início diz que os planos anuais precisam da IA')
    print('ERROS', erros); b.close()
