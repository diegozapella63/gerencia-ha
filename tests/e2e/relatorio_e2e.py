"""Relatório de patrimônio com o servidor de verdade e o InventarIA ao lado (dados de exemplo, inventados): abre de Mais no
tema do app, com o cabeçalho dos relatórios dos apps (o ícone, GerencIA, o que é, a contagem e quando); o filtro Todos /
Meus / De terceiros troca o resumo e as seções e fica no endereço com o tema, sem empilhar páginas; os bens (os cadastrados
no GerencIA e os itens do InventarIA) entram em Bens, com Bens no InventarIA ligado; Baixar PDF baixa um arquivo de verdade
(patrimonio-AAAA-MM-DD-terceiros.pdf), com o mesmo cabeçalho, as colunas Por mês, Em 1 ano e Em 5 anos e só o que foi
filtrado; Voltar volta ao app. Capturas no escuro (celular) e no claro, e das páginas do PDF quando há o pdftoppm."""
import sys, json, re, zlib, shutil, subprocess, urllib.request
from datetime import date
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sem, sim, valores
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'; INV = 'http://127.0.0.1:8098/'
def req(base, p, c=None, m='GET'):
    r = urllib.request.Request(base + p, data=json.dumps(c).encode() if c is not None else None, method=m, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
def st(): return req(B, 'api/state')
def textos_pdf(b):
    out = []
    for m in re.finditer(rb"/Length (\d+) /Filter /FlateDecode >>\nstream\n", b):
        ops = zlib.decompress(b[m.end():m.end() + int(m.group(1))])
        out += [re.sub(rb"\\(.)", rb"\1", t).decode('cp1252') for t in re.findall(rb"\(((?:\\.|[^\\)])*)\) Tj", ops)]
    return out
def caixas(pg, sel):
    return pg.evaluate(f"[...document.querySelectorAll('{sel}')].map(a => {{ const r = a.getBoundingClientRect(); return [a.textContent.trim(), Math.round(r.width), Math.round(r.top)] }})")
# InventarIA com itens inventados (nenhum dado real)
sala = req(INV, 'api/rooms', {'name': 'Sala'}, 'POST')['room']['id']
for nome, cat, val in [('Televisão 55"', 'eletronicos', 3000), ('Sofá 3 lugares', 'moveis', 2500)]:
    req(INV, 'api/items', {'room': sala, 'name': nome, 'cat': cat, 'value': val}, 'POST')
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 390, 'height': 844}, color_scheme='dark', device_scale_factor=2, accept_downloads=True)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    d = st()
    terc = [i for i in d['investimentos'] if i.get('titular') == 'terceiros']
    meus = [i for i in d['investimentos'] if i.get('titular') != 'terceiros' and i.get('tipo') != 'bens']
    bens_aqui = [i for i in d['investimentos'] if i.get('titular') != 'terceiros' and i.get('tipo') == 'bens']
    sim(terc and meus, 'o exemplo tem investimentos meus e de terceiros', (len(meus), len(terc)))
    # de Mais, a linha do relatório
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(300)
    with pg.expect_navigation():
        pg.click('#app .menu-row[data-a="relatorio"]')
    pg.wait_for_timeout(400)
    tem(pg.url, 'relatorio?tema=escuro', 'abre no tema do app')
    igual(pg.inner_text('.cab h1'), 'Relatório de patrimônio', 'título no cabeçalho')
    igual(pg.inner_text('.cab .app'), 'GerencIA · finanças da casa', 'o app e o que é (fora do Home Assistant, sem o nome da casa)')
    sim(re.fullmatch(r'\d+ investimentos em \d+ bancos · \d+ bens · \d\d/\d\d/\d{4} às \d\d:\d\d', pg.inner_text('.cab p')), 'a contagem e quando', pg.inner_text('.cab p'))
    igual(pg.locator('.cab .ic').count(), 1, 'o ícone do app')
    igual([c[0] for c in caixas(pg, '.barra a')], ['Voltar', 'Baixar PDF'], 'Voltar e Baixar PDF (sem o Imprimir)')
    bx = caixas(pg, '.barra a'); igual(bx[0][1:], bx[1][1:], 'os dois botões do mesmo tamanho, alinhados')
    fl = caixas(pg, '.filtro a')
    igual([c[0] for c in fl], ['Todos', 'Meus', 'De terceiros'], 'o filtro')
    igual(len({c[1] for c in fl}), 1, 'os três do mesmo tamanho')
    igual(pg.inner_text('.filtro a.on'), 'Todos', 'começa em Todos')
    igual(pg.locator('.resumo span').all_inner_texts(), ['Patrimônio', 'Investido', 'Bens', 'De terceiros'], 'o resumo, como no Início')
    titulos = [h.split('\n')[0] for h in pg.locator('h2 span').all_inner_texts()]
    igual(titulos[:2], ['Seu dinheiro', 'Bens'], 'o seu dinheiro e os bens primeiro')
    secao_bens = pg.locator('section', has=pg.locator('h2 span', has_text='Bens')).inner_text()
    for nome in ['Televisão 55"', 'Sofá 3 lugares'] + [i['nome'] for i in bens_aqui]:
        tem(secao_bens, nome, f'Bens: {nome}')
    tem(secao_bens, 'perde 20% a.a.', 'Bens: a taxa da categoria')
    sim(not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"), 'nada sai da tela (390 px)')
    pg.screenshot(path=f'{SP}/shots/relatorio-todos.png', full_page=True)
    # Meus: o filtro não empilha páginas
    n0 = pg.evaluate('history.length')
    with pg.expect_navigation():
        pg.click('.filtro a:has-text("Meus")')
    tem(pg.url, 'quem=meus&tema=escuro', 'Meus fica no endereço, com o tema')
    igual(pg.evaluate('history.length'), n0, 'trocar o filtro não empilha páginas')
    igual(pg.inner_text('.filtro a.on'), 'Meus', 'Meus marcado')
    tem(pg.inner_text('.cab p'), 'Só os seus · ', 'o cabeçalho diz o filtro')
    igual(pg.locator('.resumo span').all_inner_texts(), ['Patrimônio', 'Investido', 'Bens'], 'Meus: sem o de terceiros')
    sem(pg.inner_text('main'), terc[0]['nome'], 'nada de terceiros')
    # De terceiros
    with pg.expect_navigation():
        pg.click('.filtro a:has-text("De terceiros")')
    igual(pg.inner_text('.filtro a.on'), 'De terceiros', 'De terceiros marcado')
    igual(pg.locator('.resumo span').all_inner_texts(), ['De terceiros'], 'De terceiros: só o de terceiros')
    sem(pg.inner_text('main'), 'Seu dinheiro', 'sem a sua seção')
    sem(pg.inner_text('main'), 'Televisão', 'sem os bens da casa (são seus)')
    pg.screenshot(path=f'{SP}/shots/relatorio-terceiros.png', full_page=True)
    # Baixar PDF
    with pg.expect_download() as dl:
        pg.click('.barra a:has-text("Baixar PDF")')
    arq = dl.value
    igual(arq.suggested_filename, f'patrimonio-{date.today().isoformat()}-terceiros.pdf', 'o PDF baixa com o nome do filtro')
    caminho = f'{SP}/shots/relatorio-terceiros.pdf'; arq.save_as(caminho)
    corpo = open(caminho, 'rb').read()
    sim(corpo.startswith(b'%PDF-1.4') and corpo.rstrip().endswith(b'%%EOF'), 'é um PDF')
    t = textos_pdf(corpo)
    igual(t[2:6], ['Gerenc', 'IA', '· finanças da casa', 'Relatório de patrimônio'], 'PDF: o cabeçalho dos relatórios dos apps')
    tem(t[6], 'De terceiros · ', 'PDF: o filtro no cabeçalho')
    for col in ('VALOR HOJE', 'POR MÊS', 'EM 1 ANO', 'EM 5 ANOS'):
        tem(' | '.join(t), col, f'PDF: coluna {col}')
    for i in terc:
        tem(' | '.join(t), i['nome'][:20], f'PDF: {i["nome"]}')
    sem(' | '.join(t), meus[0]['nome'], 'PDF: nada seu')
    tem(t[-1], 'GerencIA · relatório gerado em ', 'PDF: o pé da página')
    if shutil.which('pdftoppm'):
        subprocess.run(['pdftoppm', '-r', '80', '-png', caminho, f'{SP}/shots/relatorio-pdf'], check=False)
    # o PDF de todos, direto do servidor: os bens da casa e os cadastrados aqui
    todos = urllib.request.urlopen(B + 'relatorio.pdf').read()
    open(f'{SP}/shots/relatorio-todos.pdf', 'wb').write(todos)
    t = ' | '.join(textos_pdf(todos))
    for nome in [i['nome'][:20] for i in meus[:3] + terc[:1] + bens_aqui] + ['Televisão 55"', 'Sofá 3 lugares']:
        tem(t, nome, f'PDF de todos: {nome}')
    tem(t, 'BEM | CÔMODO | POR ANO | INFORMADO EM', 'PDF de todos: as colunas dos bens')
    if shutil.which('pdftoppm'):
        subprocess.run(['pdftoppm', '-r', '80', '-png', '-l', '2', f'{SP}/shots/relatorio-todos.pdf', f'{SP}/shots/relatorio-todos-pdf'], check=False)
    # Voltar volta ao app
    with pg.expect_navigation():
        pg.click('.barra a:has-text("Voltar")')
    pg.wait_for_timeout(800)
    sim(pg.locator('#nav').count() == 1, 'Voltar: de volta ao app')
    # Bens no InventarIA desligado: os itens de lá saem do relatório (os cadastrados aqui ficam)
    d = st(); d['ajustes']['bens'] = False
    req(B, 'api/state', d, 'PUT')
    h = urllib.request.urlopen(B + 'relatorio').read().decode()
    sem(h, 'Televisão', 'desligado: sem os itens do InventarIA')
    for i in bens_aqui:
        tem(h, i['nome'], f'desligado: {i["nome"]} (cadastrado aqui) continua')
    # no claro
    pg2 = b.new_page(viewport={'width': 390, 'height': 844}, color_scheme='light', device_scale_factor=2)
    pg2.goto(B + 'relatorio?tema=claro&quem=meus'); pg2.wait_for_timeout(400)
    igual(pg2.evaluate("getComputedStyle(document.body).backgroundColor"), 'rgb(246, 247, 249)', 'claro: o fundo claro')
    igual(pg2.evaluate("getComputedStyle(document.querySelector('.cab')).backgroundColor"), 'rgb(255, 255, 255)', 'claro: o cabeçalho branco')
    igual(pg2.inner_text('.filtro a.on'), 'Meus', 'claro: Meus marcado')
    pg2.screenshot(path=f'{SP}/shots/relatorio-claro.png', full_page=True)
    b.close()
print('ERROS', erros)
