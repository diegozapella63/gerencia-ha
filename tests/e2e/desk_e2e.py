"""No computador (1366 px): barra lateral com bancos e pessoas que filtram a Carteira, ações no alto à direita, tecla /,
janelas no meio da tela, esconder valores, Exportar em linhas, Uso da IA (zerado antes da primeira chamada; a fala conta
como Falar) e, a 900 px, as abas de baixo de volta."""
import re, sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sem, sim, ir_mais
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
def post(p, c):
    r = urllib.request.Request(B + p, data=json.dumps(c).encode(), method='POST', headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
mil = lambda t: float(re.search(r'([\d.,]+)\s*mil', t.replace('\xa0', ' ')).group(1).replace(',', '.'))
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1366, 'height': 860}, color_scheme='dark', extra_http_headers={'X-Remote-User-Display-Name': 'Ana Souza'})
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    # Uso da IA antes de qualquer chamada: os quadros aparecem zerados
    ir_mais(pg, 'config', 'integracoes', 1200)
    igual(pg.locator('#uso-ia .uso-tile').count(), 3, 'Uso da IA: os três quadros antes da primeira chamada')
    igual([x.strip() for x in pg.locator('#uso-ia .uso-tile .v').all_inner_texts()], ['0', '0', '0'], 'Uso da IA: zerados')
    pg.click('#lado [data-v="inicio"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    st = get('api/state')
    igual((pg.locator('#lado').is_visible(), pg.locator('#nav').is_visible(), pg.locator('.cab .brand').is_visible()), (True, False, False), 'barra lateral no lugar das abas de baixo (a marca fica nela)')
    igual(pg.inner_text('.cab .eyebrow').lower(), 'olá, ana', 'cumprimenta pelo primeiro nome')
    lado = pg.inner_text('#lado')
    for t in ('Início', 'Buscar', 'Caixa', 'Investimentos', 'Mais', 'Bancos', 'De terceiros'):
        tem(lado, t, f'barra lateral: {t}')
    igual(pg.inner_text('#lado .side-badge'), '1', 'barra lateral: Caixa com o número de contas atrasadas (o IPTU)')
    bancos = pg.locator('#lado [data-a="lado-banco"]')
    igual(sorted(bancos.nth(i).get_attribute('data-v') for i in range(bancos.count())), sorted(x['id'] for x in st['bancos']), 'barra lateral: os bancos')
    vs = [mil(t) for t in bancos.all_inner_texts()]
    igual(vs, sorted(vs, reverse=True), 'bancos do maior para o menor')
    terc = sorted({i['terceiro'] for i in st['investimentos'] if i.get('titular') == 'terceiros'})
    igual(sorted(x.split('\n')[1] for x in pg.locator('#lado [data-a="pessoa"]').all_inner_texts()), terc, 'barra lateral: as pessoas de fora')
    igual([x.strip() for x in pg.locator('.top-acts > *').all_inner_texts()][-2:], ['Ler com IA', 'Adicionar'], 'no alto à direita: Ler com IA e Adicionar')
    igual([m.get_attribute('data-a') for m in pg.locator('.cab-topo .mic-top').all() if m.is_visible()], [], 'sem os botões redondos do cabeçalho do celular (ficam no alto à direita)')
    # navegação
    pg.click('#lado [data-v="caixa"]'); pg.wait_for_timeout(400)
    tem(pg.inner_text('#lado [aria-current="page"]'), 'Caixa', 'Caixa marcado na barra lateral')
    igual(pg.inner_text('.cab h1'), 'Caixa', 'título grande: Caixa')
    lado_b = pg.locator('.cx-lado').bounding_box(); lista = pg.locator('.cx-lista').bounding_box()
    sim(lado_b['x'] > lista['x'] + lista['width'] - 1, 'no Caixa, o mês fica à direita da lista', (lado_b, lista))
    igual(pg.evaluate("getComputedStyle(document.querySelector('.cx-lado')).position"), 'sticky', 'o mês fica parado ao rolar')
    # banco na barra lateral
    nu = [i for i in st['investimentos'] if i.get('banco') == 'b-lua']
    pg.click('#lado [data-a="lado-banco"][data-v="b-lua"]'); pg.wait_for_timeout(400)
    igual(sorted(pg.locator('.inv .inv-nome').all_inner_texts()), sorted(i['nome'] for i in nu), 'Banco Lua na barra: a Carteira só com os do Banco Lua')
    igual(pg.inner_text('.chip.on >> nth=-1'), 'Banco Lua', 'com o filtro do banco')
    marc = pg.locator('#lado [aria-current="page"]').all_inner_texts()
    sim(len(marc) == 1 and 'Banco Lua' in marc[0], 'só o Banco Lua marcado na barra', marc)
    igual(len(pg.evaluate("getComputedStyle(document.querySelector('.inv-lista')).gridTemplateColumns").split()), 2, 'Carteira em duas colunas')
    pessoa = pg.locator('#lado [data-a="pessoa"] >> nth=1')
    nome = pessoa.inner_text().split('\n')[1]
    pessoa.click(); pg.wait_for_timeout(400)
    marc = pg.locator('#lado [aria-current="page"]').all_inner_texts()
    sim(len(marc) == 1 and nome in marc[0], f'{nome} marcada na barra', marc)
    igual(sorted(pg.locator('.inv .inv-nome').all_inner_texts()), sorted(i['nome'] for i in st['investimentos'] if i.get('terceiro') == nome), f'a Carteira só com os de {nome}')
    igual(pg.locator('[data-a="filtro"][data-v="terc"].on').count(), 1, 'com o filtro Terceiros')
    # tecla /
    pg.click('#lado [data-v="inicio"]'); pg.wait_for_timeout(300)
    pg.keyboard.press('/'); pg.wait_for_timeout(400)
    igual((pg.evaluate("document.activeElement.id"), pg.inner_text('.cab h1')), ('q', 'Investimentos'), 'tecla /: abre a Carteira com o cursor na busca')
    pg.keyboard.type('tesouro'); pg.wait_for_timeout(400)
    igual(sorted(pg.locator('.inv .inv-nome').all_inner_texts()), sorted(i['nome'] for i in st['investimentos'] if 'tesouro' in i['nome'].lower()), 'busca: os Tesouros')
    pg.click('#lado [data-a="buscar"]'); pg.wait_for_timeout(300)
    igual(pg.evaluate("document.activeElement.id"), 'q', 'Buscar na barra: cursor na busca')
    # Adicionar no alto: janela no meio
    pg.click('#lado [data-v="inicio"]'); pg.wait_for_timeout(300)
    pg.click('.top-acts [data-a="novo"]'); pg.wait_for_timeout(500)
    igual(pg.inner_text('.folha-cab h2'), 'Adicionar', 'Adicionar no alto abre a janela')
    f = pg.locator('.folha').bounding_box()
    cx = f['x'] + f['width'] / 2; cy = f['y'] + f['height'] / 2
    sim(abs(cx - (272 + (1366 - 272) / 2)) <= 2 and abs(cy - 860 / 2) <= 2, 'a janela abre no meio da área ao lado da barra', (cx, cy))
    igual(round(f['width']), 640, 'janela com 640 px de largura')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    igual(pg.locator('.folha').count(), 0, 'Esc fecha a janela')
    pg.click('.top-acts [data-a="ia"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Ler com IA', 'Ler com IA no alto'); pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    # esconder valores
    pg.click('.top-acts [data-a="olho"]'); pg.wait_for_timeout(300)
    num_lado, num_placar = pg.inner_text('#lado .sl-num >> nth=0'), pg.get_attribute('.placar-num', 'aria-label')
    sim(not re.search(r'\d', num_lado) and '•' in num_lado, 'escondido: a barra lateral sem números', num_lado)
    igual(num_placar, 'Patrimônio de R$ •••••', 'escondido: o placar sem números')
    pg.click('.top-acts [data-a="olho"]'); pg.wait_for_timeout(300)
    sim(re.search(r'\d', pg.inner_text('#lado .sl-num >> nth=0')), 'mostrar de novo: os números voltam')
    # Exportar em linhas
    pg.click('#lado [data-v="mais"]'); pg.wait_for_timeout(300)
    igual(pg.locator('#app .menu-row b').all_inner_texts(), ['Bancos', 'Caixa', 'Invest', 'Relatório de patrimônio', 'Configurações'], 'Mais: o menu, com Configurações por último')
    igual(pg.inner_text('#lado [aria-current="page"]').strip(), 'Mais', 'Mais marcado na barra lateral')
    pg.screenshot(path=f'{SP}/shots/desk-menu.png')
    ir_mais(pg, 'config', 'dados', 800)
    igual((pg.inner_text('#app .uplink').strip(), pg.inner_text('#app .cab h1'), pg.inner_text('#lado [aria-current="page"]').strip()), ('Mais', 'Configurações', 'Mais'), 'Configurações: ‹ Mais no alto e Mais marcado')
    linhas = pg.locator('#exportar .opts > li')
    igual([linhas.nth(i).locator('.ot b').inner_text() for i in range(linhas.count())], ['Lançamentos (CSV)', 'Investimentos (CSV)', 'Dados completos (JSON)', 'Tudo (ZIP)'], 'Exportar: uma linha por arquivo (o relatório tem a sua linha no menu)')
    igual([linhas.nth(i).locator('.btn').inner_text().strip() for i in range(linhas.count())], ['Baixar CSV', 'Baixar CSV', 'Baixar JSON', 'Baixar ZIP'], 'Exportar: o botão de cada um')
    hrefs = [linhas.nth(i).locator('a[href]').get_attribute('href') if linhas.nth(i).locator('a[href]').count() else None for i in range(linhas.count())]
    igual(hrefs, ['api/export/lancamentos', 'api/export/csv', 'api/export/json', 'api/export/zip'], 'Exportar: os endereços')
    igual([urllib.request.urlopen(B + h).status for h in hrefs if h], [200, 200, 200, 200], 'Exportar: os quatro arquivos baixam')
    # Uso da IA: fala conta como Falar
    k0 = get('api/ia/uso')['today'].get('kinds', {})
    post('api/ia/ler', {'modo': 'caixa', 'texto': 'gastei 45 no mercado', 'fala': True})
    post('api/ia/ler', {'modo': 'caixa', 'texto': 'gastei 45 no mercado'})
    k = get('api/ia/uso')['today'].get('kinds', {})
    igual((k.get('fala', 0) - k0.get('fala', 0), k.get('caixa', 0) - k0.get('caixa', 0)), (1, 1), 'Uso da IA: a fala conta como Falar, o texto como ler lançamentos')
    pg.reload(); pg.wait_for_timeout(1000)
    igual(pg.inner_text('.cab h1'), 'Configurações', 'recarregar volta em Configurações')
    pg.click('[data-a="mais-aba"][data-v="integracoes"]'); pg.wait_for_timeout(1000)
    tipos = pg.locator('.uso-tipos li').all_inner_texts()
    sim('Falar 1' in tipos and 'Ler lançamentos 1' in tipos, 'Uso da IA na tela: Falar e Ler lançamentos', tipos)
    # tablet: volta às abas de baixo
    pg.set_viewport_size({'width': 900, 'height': 860}); pg.wait_for_timeout(300)
    igual((pg.locator('#lado').is_visible(), pg.locator('#nav').is_visible(), pg.locator('.top-acts').is_visible()), (False, True, False), 'a 900 px: abas de baixo, sem barra lateral nem ações no alto')
    print('ERROS', erros); b.close()
