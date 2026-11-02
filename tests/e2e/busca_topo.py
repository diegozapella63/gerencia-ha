import sys
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(500)
    yb = pg.locator('.inv-busca').bounding_box()['y']; ys = pg.locator('[data-a="inv-modo"]').first.bounding_box()['y']
    print('1 busca acima das abas:', yb < ys)
    pg.screenshot(path=f'{SP}/shots/invest-topo.png')
    pg.click('[data-a="inv-modo"][data-v="evolucao"] >> nth=-1'); pg.wait_for_timeout(500)
    pg.click('#q'); pg.keyboard.type('cdb'); pg.wait_for_timeout(500)
    print('2 digitou em Evolução: modo', pg.locator('[data-a="inv-modo"].on').inner_text(), '| cartões', pg.locator('.inv').count(), '| foco', pg.evaluate('document.activeElement.id'), '| valor', pg.input_value('#q'))
    # IA desligada: dicas
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="mais-aba"][data-v="integracoes"]'); pg.wait_for_timeout(600)
    pg.click('[data-a="ajuste"][data-k="ia"]'); pg.wait_for_timeout(800)
    pg.click('[data-a="mais-aba"][data-v="caixa"]'); pg.wait_for_timeout(600)
    print('3 dicas com IA desligada:', pg.locator('#dicas .status').all_inner_texts(), '| conferir:', pg.locator('[data-a="dicas-conferir"]').count())
    pg.click('[data-a="mais-aba"][data-v="opcoes"]'); pg.wait_for_timeout(500)
    print('  opções:', pg.inner_text('#op-inicio').split('\n')[-1][:160])
    print('ERROS', erros); b.close()
