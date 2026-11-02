import sys
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="ia-de"][data-ini="texto"]'); pg.wait_for_timeout(400)
    print('invest colar:', pg.inner_text('.folha-cab h2'), '| botões de arquivo', pg.locator('.folha [data-a="ia-arq"]').count(), '| falar', pg.locator('.folha [data-a="ia-falar"]').count(), '| foco', pg.evaluate('document.activeElement.id'))
    pg.screenshot(path=f'{SP}/shots/so-texto.png')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    print('  Esc volta para:', pg.inner_text('.folha-cab h2'))  # 1.23.0: volta para o Novo investimento
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="ia-de"][data-ini="texto"]'); pg.wait_for_timeout(400)
    print('caixa colar:', pg.inner_text('.folha-cab h2'), '|', pg.get_attribute('#ia-txt', 'placeholder'))
    pg.fill('#ia-txt', 'gastei 45 no mercado e recebi 150 do joão'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2600)
    print('  leu:', pg.inner_text('.folha-cab h2'), pg.locator('.ia-item').count())
    print('ERROS', erros); b.close()
