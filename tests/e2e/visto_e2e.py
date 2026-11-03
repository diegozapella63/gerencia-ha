"""Pago fica verde com o visto, como no CronologIA: no Caixa, o que já foi pago tem o visto e o que falta tem o círculo
(sem o botãozinho de antes); tocar no círculo abre a confirmação (Paguei) e a linha fica verde."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, mes
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(500)
    # este mês: cada pago tem o visto; cada círculo fica numa linha que ainda falta
    feitos, vistos = pg.locator('.lanc.feito').count(), pg.locator('.lanc.feito > .visto.on').count()
    igual(vistos, feitos, 'este mês: toda linha paga (verde) tem o visto')
    igual(pg.locator('.visto.on').count(), feitos, 'este mês: só as pagas têm o visto')
    circ = pg.locator('button.visto').count()
    igual(pg.locator('.lanc:not(.feito) > button.visto').count(), circ, 'este mês: os círculos ficam nas que faltam')
    sim(feitos + circ > 0, 'este mês tem lançamentos', (feitos, circ))
    igual(pg.locator('.pagar').count(), 0, 'sem o botãozinho antigo de pagar')
    pg.screenshot(path=f'{SP}/shots/caixa-vistos.png')
    # mês que vem: tudo falta; o círculo do aluguel abre a confirmação e grava
    pg.click('[data-a="cx-mes"][data-v="1"]'); pg.wait_for_timeout(400)
    igual(pg.locator('.lanc.feito').count(), 0, 'mês que vem: nada pago ainda')
    sim(pg.locator('button.visto').count() > 0, 'mês que vem: os fixos com o círculo')
    btn = pg.locator('.lanc:has-text("Aluguel") button.visto[data-a="lanc-pagar"]')
    igual(btn.count(), 1, 'o aluguel do mês que vem tem o círculo')
    if btn.count():
        igual(btn.get_attribute('aria-label'), 'Paguei: Aluguel', 'o círculo diz o que faz')
        lid = btn.get_attribute('data-id')
        igual(lid, f'v:r-alug:{mes(1)}', 'o fixo ainda não lançado tem o id do mês')
        btn.scroll_into_view_if_needed(); btn.click(); pg.wait_for_timeout(600)
        igual(pg.locator('.folha-cab h2').all_inner_texts(), ['Confirmar pagamento'], 'tocar no círculo abre a confirmação')
        igual([x.strip() for x in pg.locator('.folha-pe .btn').all_inner_texts()], ['Cancelar', 'Paguei'], 'botões: Cancelar e Paguei')
        pg.locator('.folha-pe .btn.pri').last.click(); pg.wait_for_timeout(900)
        igual(pg.locator('.folha-cab h2').all_inner_texts(), [], 'Paguei fecha a janela')
        l = [x for x in get('api/state')['lancamentos'] if x.get('recorrencia') == 'r-alug' and x.get('competencia') == mes(1)]
        igual([(x['valor'], x['pago']) for x in l], [(2300, True)], 'o fixo vira um lançamento pago, com o valor padrão')
        if l:
            igual(pg.locator(f'.lanc.feito[data-id="{l[0]["id"]}"] > .visto.on').count(), 1, 'a linha fica verde, com o visto')
            igual(pg.locator('.lanc:has-text("Aluguel") button.visto').count(), 0, 'e sem o círculo')
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(300)
    print('ERROS', erros); b.close()
