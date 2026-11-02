import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    # sem dados: dicas_estado marca a verificação do dia
    print('1 api sem assinaturas: atualizado', get('api/dicas').get('atualizado'))
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="mais-aba"][data-v="caixa"]'); pg.wait_for_timeout(1200)
    print('  tela:', pg.inner_text('#dicas .dica-quando'))
    pg.click('[data-a="dicas-conferir"]'); pg.wait_for_timeout(9000)
    print('2 depois de conferir:', pg.inner_text('#dicas .dica-quando'))
    pg.locator('#dicas').scroll_into_view_if_needed(); pg.wait_for_timeout(200)
    pg.locator('#dicas').screenshot(path=f'{SP}/shots/dicas-quando.png')
    # Falar: texto do status
    pg.click('[data-a="mais-aba"][data-v="integracoes"]'); pg.wait_for_timeout(1200)
    t = [x for x in pg.locator('#integ-ia .status, .status').all_inner_texts() if x.startswith('Falar')]
    print('3 falar:', t)
    print('ERROS', erros); b.close()
