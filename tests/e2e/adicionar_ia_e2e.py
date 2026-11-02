import sys, json, urllib.request
from playwright.sync_api import sync_playwright
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
        print('1 cabeçalho', tab, ':', [x.get_attribute('data-a') for x in vis])
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.screenshot(path=f'{SP}/shots/ai-invest-cab.png', clip={'x': 0, 'y': 0, 'width': 412, 'height': 260})
    # Invest › Adicionar: Novo investimento com os quadrinhos
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(500)
    print('2 janela:', pg.inner_text('.folha-cab h2'), '| quadrinhos:', [x.replace('\n', ' ') for x in pg.locator('.imp-tile').all_inner_texts()])
    pg.screenshot(path=f'{SP}/shots/ai-novo-inv.png')
    with pg.expect_file_chooser() as fc: pg.click('[data-a="ia-de"][data-ini="arquivo"]')
    fc.value.set_files(f'{SP}/print.jpg'); pg.wait_for_timeout(1200)
    print('3 arquivo: janela', pg.inner_text('.folha-cab h2'), '| escolha de tipo:', pg.locator('.folha .seg').count(), '| anexo', pg.locator('.ia-prev').count())
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    print('  X volta para:', pg.inner_text('.folha-cab h2')); pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # Caixa › Adicionar: Nova despesa com os quadrinhos
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(500)
    print('4 janela:', pg.inner_text('.folha-cab h2'), '| quadrinhos:', [x.replace('\n', ' ') for x in pg.locator('.imp-tile').all_inner_texts()])
    pg.screenshot(path=f'{SP}/shots/ai-nova-despesa.png')
    pg.click('[data-a="ia-de"][data-ini="texto"]'); pg.wait_for_timeout(500)
    print('5 colar: janela', pg.inner_text('.folha-cab h2'), '| escolha de tipo:', pg.locator('.folha .seg').count(), '| foco', pg.evaluate('document.activeElement.id'))
    pg.keyboard.type('gastei 45 no mercado ontem'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2600)
    print('  revisão:', pg.inner_text('.folha-cab h2'))
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    print('  X volta para:', pg.inner_text('.folha-cab h2')); pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(500)
    pg.click('[data-a="ia-de"][data-ini="voz"]'); pg.wait_for_timeout(1500)
    print('6 falar:', pg.inner_text('.folha-cab h2'), '|', pg.inner_text('.folha-corpo')[:40].replace('\n', ' '))
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    print('  X volta para:', pg.inner_text('.folha-cab h2')); pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # editar não mostra os quadrinhos
    pg.locator('.lanc[data-a="lanc"]').first.click(); pg.wait_for_timeout(400)
    print('7 editar: quadrinhos', pg.locator('.imp-tile').count())
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # Início › Adicionar ainda tem Ler com IA
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    print('8 Início › Adicionar:', [x.split('\n')[0] for x in pg.locator('.escolhas .op').all_inner_texts()])
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # computador: Ler com IA continua no alto à direita
    pg.set_viewport_size({'width': 1366, 'height': 860}); pg.wait_for_timeout(300)
    print('9 computador:', [x.strip() for x in pg.locator('.top-acts > *').all_inner_texts() if x.strip()])
    print('ERROS', erros); b.close()
