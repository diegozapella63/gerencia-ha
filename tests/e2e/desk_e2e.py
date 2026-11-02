import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
def post(p, c):
    r = urllib.request.Request(B + p, data=json.dumps(c).encode(), method='POST', headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1366, 'height': 860}, color_scheme='dark', extra_http_headers={'X-Remote-User-Display-Name': 'Ana Souza'})
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    # Uso da IA antes de qualquer chamada: os quadros aparecem zerados
    pg.click('#lado [data-v="mais"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="mais-aba"][data-v="integracoes"]'); pg.wait_for_timeout(1200)
    print('1 uso zerado: quadros', pg.locator('#uso-ia .uso-tile').count(), '| hoje', pg.locator('#uso-ia .uso-tile .v').first.inner_text())
    pg.click('#lado [data-v="inicio"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    print('2 lado visível:', pg.locator('#lado').is_visible(), '| nav visível:', pg.locator('#nav').is_visible(), '| marca no cabeçalho:', pg.locator('.cab .brand').is_visible(), '| eyebrow:', pg.inner_text('.cab .eyebrow'))
    print('  lado:', pg.inner_text('#lado').replace('\n', ' | '))
    print('  ações no alto:', [x.strip() for x in pg.locator('.top-acts > *').all_inner_texts()], '| mic do celular visível:', pg.locator('.cab-topo .mic-top').is_visible())
    # navegação
    pg.click('#lado [data-v="caixa"]'); pg.wait_for_timeout(400)
    print('3 Caixa atual:', pg.inner_text('#lado [aria-current="page"]').replace('\n', ' '), '| h1:', pg.inner_text('.cab h1'))
    lado = pg.locator('.cx-lado').bounding_box(); lista = pg.locator('.cx-lista').bounding_box()
    print('  mês à direita da lista:', lado['x'] > lista['x'] + lista['width'] - 1, '| lado fixo:', pg.evaluate("getComputedStyle(document.querySelector('.cx-lado')).position"))
    # banco na barra lateral
    nu = [i for i in get('api/state')['investimentos'] if i.get('banco') == 'b-nu']
    pg.click('#lado [data-a="lado-banco"][data-v="b-nu"]'); pg.wait_for_timeout(400)
    print('4 Nubank: cartões', pg.locator('.inv').count(), 'esperado', len(nu), '| chip:', pg.inner_text('.chip.on >> nth=-1'), '| marcados:', [x.replace('\n', ' ') for x in pg.locator('#lado [aria-current="page"]').all_inner_texts()])
    cols = pg.evaluate("getComputedStyle(document.querySelector('.inv-lista')).gridTemplateColumns")
    print('  colunas da carteira:', len(cols.split()))
    pg.click('#lado [data-a="pessoa"] >> nth=1'); pg.wait_for_timeout(400)
    print('5 pessoa:', [x.replace('\n', ' ') for x in pg.locator('#lado [aria-current="page"]').all_inner_texts()], '| cartões', pg.locator('.inv').count(), '| filtro Terceiros on:', pg.locator('[data-a="filtro"][data-v="terc"].on').count())
    # tecla /
    pg.click('#lado [data-v="inicio"]'); pg.wait_for_timeout(300)
    pg.keyboard.press('/'); pg.wait_for_timeout(400)
    print('6 tecla /: foco em', pg.evaluate("document.activeElement.id"), '| tela', pg.inner_text('.cab h1'))
    pg.keyboard.type('tesouro'); pg.wait_for_timeout(400)
    print('  busca tesouro:', pg.locator('.inv').count())
    pg.click('#lado [data-a="buscar"]'); pg.wait_for_timeout(300)
    print('  Buscar na barra: foco em', pg.evaluate("document.activeElement.id"))
    # Adicionar no alto: janela no meio
    pg.click('#lado [data-v="inicio"]'); pg.wait_for_timeout(300)
    pg.click('.top-acts [data-a="novo"]'); pg.wait_for_timeout(500)
    f = pg.locator('.folha').bounding_box()
    cx = f['x'] + f['width'] / 2; cy = f['y'] + f['height'] / 2
    print('7 janela:', pg.inner_text('.folha-cab h2'), '| centro x', round(cx), 'esperado', round(272 + (1366 - 272) / 2), '| centro y', round(cy), '| largura', round(f['width']))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    print('  fechou:', pg.locator('.folha').count() == 0)
    pg.click('.top-acts [data-a="ia"]'); pg.wait_for_timeout(400)
    print('  Ler com IA:', pg.inner_text('.folha-cab h2')); pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    # esconder valores
    pg.click('.top-acts [data-a="olho"]'); pg.wait_for_timeout(300)
    print('8 escondido: lado', pg.inner_text('#lado .sl-num >> nth=0'), '| placar', pg.get_attribute('.placar-num', 'aria-label'))
    pg.click('.top-acts [data-a="olho"]'); pg.wait_for_timeout(300)
    # Exportar em linhas
    pg.click('#lado [data-v="mais"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="mais-aba"][data-v="dados"]'); pg.wait_for_timeout(800)
    linhas = pg.locator('#exportar .opts > li')
    print('9 exportar:', linhas.count(), 'linhas')
    for i in range(linhas.count()):
        li = linhas.nth(i)
        a = li.locator('a[href]')
        href = a.get_attribute('href') if a.count() else None
        st = urllib.request.urlopen(B + href).status if href else '-'
        print('  ', li.locator('.ot b').inner_text(), '|', li.locator('.btn').inner_text().strip(), '|', href, st)
    # Uso da IA: fala conta como Falar
    post('api/ia/ler', {'modo': 'caixa', 'texto': 'gastei 45 no mercado', 'fala': True})
    post('api/ia/ler', {'modo': 'caixa', 'texto': 'gastei 45 no mercado'})
    u = get('api/ia/uso')
    print('10 tipos hoje:', u['today'].get('kinds'))
    pg.reload(); pg.wait_for_timeout(1000)
    pg.click('[data-a="mais-aba"][data-v="integracoes"]'); pg.wait_for_timeout(1000)
    print('  tipos na tela:', pg.locator('.uso-tipos li').all_inner_texts())
    # tablet: volta às abas de baixo
    pg.set_viewport_size({'width': 900, 'height': 860}); pg.wait_for_timeout(300)
    print('11 900 px: lado', pg.locator('#lado').is_visible(), '| nav', pg.locator('#nav').is_visible(), '| ações no alto', pg.locator('.top-acts').is_visible())
    print('ERROS', erros); b.close()
