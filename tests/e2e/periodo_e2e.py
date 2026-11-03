"""Período à escolha no Fluxo (Outro: atalhos, meses para trás e à frente, até 60 de cada lado, inválido avisa, fica
guardado) com menos nomes embaixo quando há muitos meses e a média do que sobrou desde o primeiro mês com lançamentos;
e o horizonte à escolha no Invest (Outro, de 1 a 50 anos)."""
import sys
from datetime import date
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, perto, valores_s, mes
MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
nome_mes = lambda ym: f'{MESES[int(ym[5:]) - 1]}/{ym[2:4]}'
SP = sys.argv[1]; erros = []
hoje = date.today()
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    pontos = lambda: pg.locator('#ch-fluxo .pt-net').count()
    nomes = lambda: pg.locator('#ch-fluxo svg text[text-anchor="middle"]').all_text_contents()
    chip = lambda: pg.inner_text('.chips.c4 .chip.on')
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="cx-modo"][data-v="fluxo"]'); pg.wait_for_timeout(600)
    igual(pg.locator('.chips.c4 .chip').all_inner_texts(), ['12 atrás', '6 + 6', '12 à frente', 'Outro'], 'Fluxo: os períodos')
    igual(pontos(), 12, 'Fluxo: 12 meses')
    pg.click('[data-a="cx-periodo"][data-v="outro"]'); pg.wait_for_timeout(500)
    igual(pg.inner_text('.folha-cab h2'), 'Período do fluxo', 'Outro abre a janela do período')
    igual(pg.locator('.folha [data-a="cx-per-pre"]').all_inner_texts(), ['24 atrás', '12 + 12', '24 à frente', '36 atrás', '24 + 12', '36 à frente'], 'atalhos do período')
    pg.screenshot(path=f'{SP}/shots/periodo-folha.png')
    pg.click('.folha [data-a="cx-per-pre"][data-v="24,0"]'); pg.wait_for_timeout(600)
    igual((pontos(), chip(), pg.locator('.folha').count()), (24, '24 atrás', 0), '24 atrás: 24 meses e o chip com o período')
    # nomes embaixo: um a cada "passo" meses, contando a partir deste mês; o ano no lugar de janeiro
    w = pg.evaluate("document.querySelector('#ch-fluxo').clientWidth")
    passo = max(2, -(-24 // max(1, (max(280, w) - 52) // 30)))
    esp = [(ym[:4] if ym[5:] == '01' and k else MESES[int(ym[5:]) - 1]) for k, ym in ((k, mes(-k)) for k in range(23, -1, -1)) if k % passo == 0]
    igual(nomes(), esp, f'24 atrás: um nome a cada {passo} meses, terminando neste mês (o ano no lugar de janeiro)')
    pequeno = pg.inner_text('.stat-duo > div:nth-child(1) small')
    igual(pequeno, f'{nome_mes(mes(-6))} a {nome_mes(mes())}', 'a média do que sobrou começa no primeiro mês com lançamentos')
    media = valores_s(pg.inner_text('.stat-duo > div:nth-child(1) b'))[0]
    pg.click('details.card summary'); pg.wait_for_timeout(200)
    sobras = []
    for tr in pg.locator('.tabela tbody tr').all():
        tds = tr.locator('td').all_inner_texts()
        if mes(-6) <= f"20{tds[0][4:6]}-{MESES.index(tds[0][:3]) + 1:02d}" <= mes():
            sobras.append(valores_s(tds[3])[0])
    igual(len(sobras), 7, 'tabela: os 7 meses com lançamentos')
    perto(media, round(sum(sobras) / max(1, len(sobras))), 'a média é a dos meses com lançamentos', tol=1)
    pg.locator('.graf-card').first.screenshot(path=f'{SP}/shots/fluxo-24.png')
    pg.click('[data-a="cx-periodo"][data-v="outro"]'); pg.wait_for_timeout(400)
    pg.fill('#per-atras', '12'); pg.fill('#per-frente', '12'); pg.press('#per-frente', 'Enter'); pg.wait_for_timeout(600)
    igual((pontos(), chip()), (24, '12 + 12'), '12 + 12 digitado (Enter): 24 meses')
    pg.click('[data-a="cx-periodo"][data-v="outro"]'); pg.wait_for_timeout(400)
    pg.fill('#per-atras', '0'); pg.fill('#per-frente', '1'); pg.click('[data-a="cx-per-ok"]'); pg.wait_for_timeout(400)
    igual(pg.locator('.folha').count(), 1, 'menos de 2 meses: a janela continua aberta')
    igual(pg.inner_text('#toast.on') if pg.locator('#toast.on').count() else '', 'Escolha pelo menos 2 meses.', 'e avisa')
    pg.fill('#per-atras', '60'); pg.fill('#per-frente', '60'); pg.click('[data-a="cx-per-ok"]'); pg.wait_for_timeout(600)
    n120 = nomes()
    igual((pontos(), chip()), (120, '60 + 60'), '60 + 60: 120 meses')
    sim(2 <= len(n120) <= 15, 'com 120 meses, poucos nomes embaixo', n120)
    igual([x for x in n120 if x == 'jan'], [], 'com muitos meses, o ano no lugar de janeiro')
    pg.locator('.graf-card').first.screenshot(path=f'{SP}/shots/fluxo-120.png')
    pg.reload(); pg.wait_for_timeout(1000)
    igual(chip(), '60 + 60', 'o período fica guardado ao recarregar')
    pg.click('[data-a="cx-periodo"][data-v="meio"]'); pg.wait_for_timeout(300)
    igual(pontos(), 12, '6 + 6: 12 meses')
    # invest
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(500)
    pg.click('.seg [data-a="inv-modo"][data-v="evolucao"], [data-a="inv-modo"][data-v="evolucao"] >> nth=-1')
    pg.wait_for_timeout(500)
    igual(pg.locator('.chips.c5 .chip').all_inner_texts(), ['1 ano', '2 anos', '5 anos', '10 anos', 'Outro'], 'Horizonte: 1, 2, 5, 10 anos e Outro')
    pg.click('[data-a="g-anos-outro"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Horizonte da projeção', 'Outro abre a janela do horizonte')
    igual(pg.locator('.folha [data-a="g-anos-pre"]').all_inner_texts(), ['3 anos', '15 anos', '20 anos', '25 anos', '30 anos', '40 anos'], 'atalhos do horizonte')
    pg.screenshot(path=f'{SP}/shots/horizonte-folha.png')
    pg.fill('#hz-anos', '30'); pg.click('[data-a="g-anos-ok"]'); pg.wait_for_timeout(700)
    igual(pg.inner_text('.chips.c5 .chip.on'), '30 anos', '30 anos: o chip Outro mostra o horizonte')
    tem(pg.inner_text('.stat-duo'), 'Em 30 anos', '30 anos: Em 30 anos')
    linhas = pg.locator('.tabela tbody tr')
    igual(linhas.count(), 30, 'tabela por ano: 30 linhas')
    igual((linhas.first.locator('td').first.text_content(), linhas.last.locator('td').first.text_content()),
          (f'{MESES[hoje.month - 1]}/{(hoje.year + 1) % 100:02d}', f'{MESES[hoje.month - 1]}/{(hoje.year + 30) % 100:02d}'), 'tabela: de daqui a 1 ano até daqui a 30')
    anos = [int(t) for t in pg.locator('#ch-evo svg text').all_text_contents() if t.isdigit() and len(t) == 4]
    sim(anos and max(anos) >= hoje.year + 20, 'o eixo vai até perto de daqui a 30 anos', anos)
    pg.locator('.graf-card').first.screenshot(path=f'{SP}/shots/evo-30.png')
    pg.click('[data-a="g"][data-k="gAnos"][data-v="5"]'); pg.wait_for_timeout(400)
    igual((pg.inner_text('.chips.c5 .chip.on'), pg.inner_text('[data-a="g-anos-outro"]')), ('5 anos', 'Outro'), '5 anos: o Outro volta a ser Outro')
    pg.screenshot(path=f'{SP}/shots/invest-hz.png')
    print('ERROS', erros); b.close()
