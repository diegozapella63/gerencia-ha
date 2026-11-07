"""Relatório de patrimônio com o servidor de verdade (dados de exemplo, inventados): abre de Mais no tema do app; o filtro
Todos / Meus / De terceiros troca o resumo e as seções e fica no endereço com o tema; Baixar PDF baixa um arquivo de verdade
(patrimonio-AAAA-MM-DD-terceiros.pdf) com o cabeçalho do app e só o que foi filtrado; Voltar volta ao app. Capturas no
escuro (celular) e no claro, e das páginas do PDF quando há o pdftoppm."""
import sys, json, re, zlib, shutil, subprocess, urllib.request
from datetime import date
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sem, sim, ir_mais
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def st(): return json.loads(urllib.request.urlopen(B + 'api/state').read())
def textos_pdf(b):
    out = []
    for m in re.finditer(rb"/Length (\d+) /Filter /FlateDecode >>\nstream\n", b):
        ops = zlib.decompress(b[m.end():m.end() + int(m.group(1))])
        out += [re.sub(rb"\\(.)", rb"\1", t).decode('cp1252') for t in re.findall(rb"\(((?:\\.|[^\\)])*)\) Tj", ops)]
    return out
def caixas(pg, sel):
    return pg.evaluate(f"[...document.querySelectorAll('{sel}')].map(a => {{ const r = a.getBoundingClientRect(); return [a.textContent.trim(), Math.round(r.width), Math.round(r.top)] }})")
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 390, 'height': 844}, color_scheme='dark', device_scale_factor=2, accept_downloads=True)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    d = st()
    terc = [i for i in d['investimentos'] if i.get('titular') == 'terceiros']
    meus = [i for i in d['investimentos'] if i.get('titular') != 'terceiros']
    sim(terc and meus, 'o exemplo tem investimentos meus e de terceiros', (len(meus), len(terc)))
    # de Mais, a linha do relatório
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(300)
    with pg.expect_navigation():
        pg.click('#app .menu-row[data-a="relatorio"]')
    pg.wait_for_timeout(400)
    tem(pg.url, 'relatorio?tema=escuro', 'abre no tema do app')
    igual(pg.inner_text('h1'), 'Relatório de patrimônio', 'título')
    igual([c[0] for c in caixas(pg, '.barra a')], ['Voltar', 'Baixar PDF'], 'Voltar e Baixar PDF (sem o Imprimir)')
    bx = caixas(pg, '.barra a'); igual(bx[0][1:], bx[1][1:], 'os dois botões do mesmo tamanho, alinhados')
    fl = caixas(pg, '.filtro a')
    igual([c[0] for c in fl], ['Todos', 'Meus', 'De terceiros'], 'o filtro')
    igual(len({c[1] for c in fl}), 1, 'os três do mesmo tamanho')
    igual(pg.inner_text('.filtro a.on'), 'Todos', 'começa em Todos')
    igual(pg.locator('.resumo b').count(), 3, 'Todos: patrimônio total, seu dinheiro e de terceiros')
    sim(not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"), 'nada sai da tela (390 px)')
    pg.screenshot(path=f'{SP}/shots/relatorio-todos.png', full_page=True)
    # Meus
    with pg.expect_navigation():
        pg.click('.filtro a:has-text("Meus")')
    tem(pg.url, 'quem=meus&tema=escuro', 'Meus fica no endereço, com o tema')
    igual(pg.inner_text('.filtro a.on'), 'Meus', 'Meus marcado')
    igual(pg.locator('.resumo span').all_inner_texts(), ['Seu dinheiro'], 'Meus: só o seu dinheiro')
    igual([h.split('\n')[0] for h in pg.locator('h2').all_inner_texts()], ['Seu dinheiro', 'Por banco'], 'só a sua seção')
    sem(pg.inner_text('main'), terc[0]['nome'], 'nada de terceiros')
    igual(pg.locator('.inv tbody tr').count(), len(meus), 'todos os seus investimentos')
    # De terceiros
    with pg.expect_navigation():
        pg.click('.filtro a:has-text("De terceiros")')
    igual(pg.inner_text('.filtro a.on'), 'De terceiros', 'De terceiros marcado')
    igual(pg.locator('.resumo span').all_inner_texts(), ['De terceiros'], 'De terceiros: só o de terceiros')
    sem(pg.inner_text('main'), 'Seu dinheiro', 'sem a sua seção')
    igual(pg.locator('.inv tbody tr').count(), len(terc), 'todos os de terceiros')
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
    igual(t[2:4], ['GerencIA', 'Finanças da casa'], 'PDF: cabeçalho com o app e o que é')
    tem(' | '.join(t), 'Relatório de patrimônio | De terceiros', 'PDF: título e o filtro')
    for i in terc:
        tem(' | '.join(t), i['nome'][:20], f'PDF: {i["nome"]}')
    sem(' | '.join(t), meus[0]['nome'], 'PDF: nada seu')
    igual(t[-1], 'GerencIA · Relatório de patrimônio', 'PDF: o pé da página')
    if shutil.which('pdftoppm'):
        subprocess.run(['pdftoppm', '-r', '80', '-png', caminho, f'{SP}/shots/relatorio-pdf'], check=False)
    # o PDF de todos, direto do servidor
    t = textos_pdf(urllib.request.urlopen(B + 'relatorio.pdf').read())
    tem(' | '.join(t), 'Relatório de patrimônio | Todos', 'PDF de todos')
    for i in meus[:3] + terc[:1]:
        tem(' | '.join(t), i['nome'][:20], f'PDF de todos: {i["nome"]}')
    # Voltar volta ao app
    with pg.expect_navigation():
        pg.click('.barra a:has-text("Voltar")')
    pg.wait_for_timeout(800)
    sim(pg.locator('#nav').count() == 1, 'Voltar: de volta ao app')
    # no claro
    pg2 = b.new_page(viewport={'width': 390, 'height': 844}, color_scheme='light', device_scale_factor=2)
    pg2.goto(B + 'relatorio?tema=claro&quem=meus'); pg2.wait_for_timeout(400)
    igual(pg2.evaluate("getComputedStyle(document.body).backgroundColor"), 'rgb(255, 255, 255)', 'claro: fundo branco')
    igual(pg2.inner_text('.filtro a.on'), 'Meus', 'claro: Meus marcado')
    pg2.screenshot(path=f'{SP}/shots/relatorio-claro.png', full_page=True)
    b.close()
print('ERROS', erros)
