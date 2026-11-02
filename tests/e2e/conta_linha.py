import sys, json, urllib.request
from playwright.sync_api import sync_playwright
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
    n0 = len(get('api/state')['lancamentos'])
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300)
    pg.click('.op[data-a="ia"]'); pg.wait_for_timeout(300)
    pg.fill('#ia-txt', 'fatura do mês'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2600)
    sels = pg.locator('.ia-item-x.dois')
    print('1 linhas:', sels.count(), '| larguras das categorias:', sorted({round(pg.locator('[data-iai="categoria"]').nth(i).bounding_box()['width']) for i in range(sels.count())}))
    print('  contas por linha:', [pg.locator('[data-iai="contasel"]').nth(i).evaluate('e => e.options[e.selectedIndex].text') for i in range(sels.count())])
    print('  opções da 1ª:', pg.locator('[data-iai="contasel"]').first.evaluate('e => [...e.options].map(o => o.text)'))
    # a última linha (Pix do João, receita) num débito; a 1ª (iFood) muda para outra conta sem cartão
    opts = pg.locator('[data-iai="contasel"]').first.evaluate('e => [...e.options].map(o => o.value)')
    outra = [o for o in opts if o and '|c' not in o][-1]
    pg.select_option('[data-iai="contasel"] >> nth=0', outra); pg.wait_for_timeout(300)
    print('2 1ª linha:', pg.locator('.ia-item').first.inner_text().split('\n')[1], '| todos em marcado:', pg.locator('[data-a="iac-conta"].on').count())
    pg.screenshot(path=f'{SP}/shots/conta-linha.png')
    pg.click('[data-a="ia-salvar"]'); pg.wait_for_timeout(1200)
    st = get('api/state'); novos = st['lancamentos'][n0:]
    print('3 salvos:', [(l['descricao'], l.get('conta'), l.get('cartao')) for l in novos][:6])
    print('ERROS', erros); b.close()
