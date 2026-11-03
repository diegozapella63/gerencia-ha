"""Fatura, print ou foto e Digitalizar com IA a partir da Nova despesa: Voltar, X e Cancelar voltam para ela; a câmera
tira várias páginas e manda todas para a IA."""
import sys, json
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
corpos = []
with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'])
    ctx = b.new_context(viewport={'width': 412, 'height': 900}, color_scheme='dark', permissions=['camera'])
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.on('request', lambda r: corpos.append(json.loads(r.post_data)) if '/api/ia/ler' in r.url and r.post_data else None)
    titulo = lambda: pg.inner_text('.folha-cab h2') if pg.locator('.folha-cab h2').count() else '(nenhuma)'
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    igual([x.replace('\n', ' ').replace('\xa0', ' ') for x in pg.locator('.imp-tile').all_inner_texts()], ['Colar mensagem', 'Fatura, print ou foto', 'Digitalizar com IA', 'Falar'], 'os quadrinhos da Nova despesa')
    igual(titulo(), 'Nova despesa', 'na Nova despesa')
    pg.screenshot(path=f'{SP}/shots/cam-tiles.png')
    # Fatura, print ou foto: a galeria abre sem trocar a janela; desistir deixa na Nova despesa
    with pg.expect_file_chooser() as fc: pg.click('[data-a="ia-de"][data-ini="arquivo"]')
    pg.wait_for_timeout(300)
    igual(titulo(), 'Nova despesa', 'a galeria abre sem trocar a janela')
    fc.value.set_files(f'{SP}/print.jpg'); pg.wait_for_timeout(900)
    igual((titulo(), pg.locator('.ia-prev').count(), pg.evaluate('history.state && history.state.g')), ('Fatura, print ou foto', 1, 2), 'escolheu: abre por cima da Nova despesa, com a imagem')
    pg.go_back(); pg.wait_for_timeout(500)
    igual((titulo(), pg.evaluate('history.state && history.state.g')), ('Nova despesa', 1), 'Voltar do celular volta para a Nova despesa')
    with pg.expect_file_chooser() as fc: pg.click('[data-a="ia-de"][data-ini="arquivo"]')
    fc.value.set_files(f'{SP}/print.jpg'); pg.wait_for_timeout(900)
    pg.click('.folha-pe [data-a="fechar"]'); pg.wait_for_timeout(400)
    igual((titulo(), pg.evaluate('history.state && history.state.g')), ('Nova despesa', 1), 'Cancelar volta para a Nova despesa')
    # Digitalizar com IA: câmera, 2 páginas, Pronto lê na hora
    pg.click('[data-a="ia-de"][data-ini="camera"]'); pg.wait_for_timeout(1500)
    igual(pg.locator('#camera').count(), 1, 'a câmera abre')
    tem(pg.inner_text('.cam-dica'), 'Enquadre', 'com a dica')
    igual(pg.evaluate('history.state && history.state.g'), 2, 'um nível a mais no histórico')
    pg.screenshot(path=f'{SP}/shots/cam-ao-vivo.png')
    pg.go_back(); pg.wait_for_timeout(500)
    igual((pg.locator('#camera').count(), titulo()), (0, 'Nova despesa'), 'Voltar fecha a câmera e fica na Nova despesa')
    sim(pg.evaluate('!document.querySelector("#camera video")'), 'a câmera desliga')
    pg.click('[data-a="ia-de"][data-ini="camera"]'); pg.wait_for_timeout(1500)
    pg.click('[data-a="cam-foto"]'); pg.wait_for_timeout(300); pg.click('[data-a="cam-foto"]'); pg.wait_for_timeout(400)
    tem(pg.inner_text('.cam-dica'), '2 páginas', 'conta as páginas')
    igual(pg.inner_text('.cam-pronto'), 'Pronto (2)', 'botão Pronto com o número')
    pg.screenshot(path=f'{SP}/shots/cam-fotos.png')
    pg.click('[data-a="cam-pronto"]'); pg.wait_for_timeout(300)
    igual((titulo(), pg.locator('#camera').count(), pg.evaluate('history.state && history.state.g')), ('Lendo com IA', 0, 2), 'Pronto: lendo, por cima da Nova despesa')
    pg.wait_for_timeout(2600)
    c = corpos[-1]
    igual(titulo(), 'Conferir lançamentos', 'leu')
    igual((len(c.get('anexos') or []), 'anexo' in c), (2, False), 'as duas páginas vão juntas para a IA')
    pg.go_back(); pg.wait_for_timeout(500)
    igual(titulo(), 'Nova despesa', 'Voltar da revisão volta para a Nova despesa')
    # dentro do Ler com IA (cabeçalho): Digitalizar com a câmera
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(500)
    igual((titulo(), pg.evaluate('history.state && history.state.g')), ('(nenhuma)', None), 'X na Nova despesa fecha tudo')
    pg.evaluate("document.querySelector('[data-a=ia]').click()"); pg.wait_for_timeout(400)
    igual(titulo(), 'Ler com IA', 'Ler com IA')
    igual([x.strip() for x in pg.locator('.ia-arq .btn').all_inner_texts()], ['Fatura, print, foto ou PDF', 'Digitalizar com a câmera', 'Falar'], 'botões do Ler com IA')
    pg.click('[data-a="ia-cam"]'); pg.wait_for_timeout(1500)
    pg.click('[data-a="cam-foto"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="cam-pronto"]'); pg.wait_for_timeout(3000)
    igual((titulo(), 'anexo' in corpos[-1], pg.evaluate('history.state && history.state.g')), ('Conferir lançamentos', True, 1), 'uma página só vai como anexo único')
    n = pg.locator('.ia-check.on').count()
    pg.click('[data-a="ia-salvar"]'); pg.wait_for_timeout(800)
    sim(n > 0, 'salvou lançamentos', n)
    igual((titulo(), pg.evaluate('history.state && history.state.g')), ('(nenhuma)', None), 'salvar fecha tudo')
    print('ERROS', erros); b.close()
