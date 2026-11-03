"""Colar mensagem abre só o campo da mensagem (sem arquivo nem Falar), com o teclado no texto e o exemplo de cada tela
(investimento ou gasto); Esc volta para a janela de baixo; no caixa, a IA lê os lançamentos."""
import sys
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sem, sim
SP = sys.argv[1]; erros = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="ia-de"][data-ini="texto"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Colar mensagem', 'Invest: Colar mensagem')
    igual((pg.locator('.folha [data-a="ia-arq"]').count(), pg.locator('.folha [data-a="ia-falar"]').count()), (0, 0), 'Invest: só o campo da mensagem (sem arquivo nem Falar)')
    igual(pg.evaluate('document.activeElement.id'), 'ia-txt', 'Invest: o teclado abre no texto')
    ph = pg.get_attribute('#ia-txt', 'placeholder')
    tem(ph, 'Ex.:', 'Invest: com exemplo')
    sem(ph, 'mercado', 'Invest: o exemplo é de investimento, não de gasto')
    pg.screenshot(path=f'{SP}/shots/so-texto.png')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    igual(pg.inner_text('.folha-cab h2'), 'Novo investimento', 'Esc volta para o Novo investimento')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    igual(pg.locator('.folha').count(), 0, 'Esc de novo fecha tudo')
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="ia-de"][data-ini="texto"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Colar mensagem', 'Caixa: Colar mensagem')
    igual(pg.get_attribute('#ia-txt', 'placeholder'), 'Ex.: “gastei 45 no mercado”, “recebi 300 do João”, “boleto do IPVA vence dia 10”', 'Caixa: exemplo de gastos e recebimentos')
    pg.fill('#ia-txt', 'gastei 45 no mercado e recebi 150 do joão'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2600)
    igual((pg.inner_text('.folha-cab h2'), pg.locator('.ia-item').count()), ('Conferir lançamentos', 4), 'Caixa: a IA lê os lançamentos para conferir')
    print('ERROS', erros); b.close()
