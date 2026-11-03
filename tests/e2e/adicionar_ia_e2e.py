"""Os jeitos de adicionar com IA em cada tela (quadrinhos, colar, arquivo, falar) e o X que volta para a janela de baixo."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
OLHO = {"inicio": True, "caixa": True, "investimentos": False, "mais": False}
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'])
    ctx = b.new_context(viewport={'width': 412, 'height': 900}, device_scale_factor=2, color_scheme='light', permissions=['microphone'], extra_http_headers={'X-Remote-User-Display-Name': 'Ana Souza'})
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    for tab in ('inicio', 'caixa', 'investimentos', 'mais'):
        pg.click(f'#nav [data-v="{tab}"]'); pg.wait_for_timeout(400)
        vis = [x for x in pg.locator('.cab button').all() if x.is_visible()]
        igual([x.get_attribute('data-a') for x in vis], ['chat', 'falar', 'olho'] if OLHO[tab] else ['chat', 'falar'], f'cabeçalho de {tab}: chat ao lado do microfone')
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.screenshot(path=f'{SP}/shots/ai-invest-cab.png', clip={'x': 0, 'y': 0, 'width': 412, 'height': 260})
    # Invest › Adicionar: Novo investimento com os quadrinhos
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(500)
    igual(pg.inner_text('.folha-cab h2'), 'Novo investimento', 'Adicionar nos investimentos')
    igual([x.replace('\n', ' ').replace('\xa0', ' ') for x in pg.locator('.imp-tile').all_inner_texts()], ['Colar mensagem', 'Imagem ou print', 'Digitalizar com IA', 'Falar'], 'quadrinhos do investimento')
    pg.screenshot(path=f'{SP}/shots/ai-novo-inv.png')
    with pg.expect_file_chooser() as fc: pg.click('[data-a="ia-de"][data-ini="arquivo"]')
    fc.value.set_files(f'{SP}/print.jpg'); pg.wait_for_timeout(1200)
    igual((pg.inner_text('.folha-cab h2'), pg.locator('.folha .seg').count(), pg.locator('.ia-prev').count()), ('Imagem ou print', 0, 1), 'escolheu o arquivo: abre com ele, sem escolher tipo')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Novo investimento', 'X volta para o Novo investimento'); pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # Caixa › Adicionar: Nova despesa com os quadrinhos
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(500)
    igual(pg.inner_text('.folha-cab h2'), 'Nova despesa', 'Adicionar no caixa')
    igual([x.replace('\n', ' ').replace('\xa0', ' ') for x in pg.locator('.imp-tile').all_inner_texts()], ['Colar mensagem', 'Fatura, print ou foto', 'Digitalizar com IA', 'Falar'], 'quadrinhos da despesa')
    pg.screenshot(path=f'{SP}/shots/ai-nova-despesa.png')
    pg.click('[data-a="ia-de"][data-ini="texto"]'); pg.wait_for_timeout(500)
    igual((pg.inner_text('.folha-cab h2'), pg.locator('.folha .seg').count(), pg.evaluate('document.activeElement.id')), ('Colar mensagem', 0, 'ia-txt'), 'colar: o teclado abre no texto')
    pg.keyboard.type('gastei 45 no mercado ontem'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2600)
    igual(pg.inner_text('.folha-cab h2'), 'Conferir lançamentos', 'revisão dos lançamentos')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Nova despesa', 'X volta para a Nova despesa'); pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(500)
    pg.click('[data-a="ia-de"][data-ini="voz"]'); pg.wait_for_timeout(1500)
    igual(pg.inner_text('.folha-cab h2'), 'Falar', 'Falar')
    tem(pg.inner_text('.folha-corpo'), 'Ouvindo', 'já ouvindo')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Nova despesa', 'X volta para a Nova despesa'); pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # editar não mostra os quadrinhos
    pg.locator('.lanc[data-a="lanc"]').first.click(); pg.wait_for_timeout(400)
    igual(pg.locator('.imp-tile').count(), 0, 'editar um lançamento não mostra os quadrinhos')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # Início › Adicionar ainda tem Ler com IA
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    igual([x.split('\n')[0] for x in pg.locator('.escolhas .op').all_inner_texts()], ['Despesa', 'Recebimento', 'Aporte', 'Ler com IA', 'Investimento', 'Atualizar saldos'], 'Início › Adicionar')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # computador: Ler com IA continua no alto à direita
    pg.set_viewport_size({'width': 1366, 'height': 860}); pg.wait_for_timeout(300)
    igual([x.strip() for x in pg.locator('.top-acts > *').all_inner_texts() if x.strip()], ['Ler com IA', 'Adicionar'], 'no computador, os botões no alto à direita')
    igual(pg.locator('.top-acts [data-a="chat"]').count(), 1, 'e o chat no alto à direita')
    print('ERROS', erros); b.close()
