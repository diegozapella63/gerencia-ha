import sys, json, urllib.request
from playwright.sync_api import sync_playwright
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
    print('1 feitos', pg.locator('.lanc.feito').count(), '| círculos para pagar', pg.locator('button.visto').count(), '| vistos', pg.locator('.visto.on').count(), '| botão antigo', pg.locator('.pagar').count())
    pg.screenshot(path=f'{SP}/shots/caixa-vistos.png')
    pg.click('[data-a="filtro-cx"][data-v="pend"]') if pg.locator('[data-a="filtro-cx"][data-v="pend"]').count() else None
    btn = pg.locator('button.visto[data-a="lanc-pagar"]').first
    if btn.count():
        nome = btn.get_attribute('aria-label'); lid = btn.get_attribute('data-id')
        btn.scroll_into_view_if_needed(); btn.click(); pg.wait_for_timeout(600)
        print('2 tocou em', nome, '| janela:', pg.locator('.folha-cab h2').all_inner_texts())
        print('  botões:', pg.locator('.folha-pe .btn').all_inner_texts())
        # a janela de confirmar: o botão principal (Recebi/Paguei) grava
        pg.locator('.folha-pe .btn.pri').last.click(); pg.wait_for_timeout(900)
        print('  janela depois:', pg.locator('.folha-cab h2').all_inner_texts())
        lancs = get('api/state')['lancamentos']
        # um fixo do mês ainda não lançado vira um lançamento novo ao pagar (com outro id)
        l = next((x for x in lancs if x['id'] == lid), None) or next(x for x in lancs if x.get('recorrencia') and x.get('pago') and x['descricao'] in nome)
        print('  pago:', l.get('pago'), '| card verde:', pg.locator(f'.lanc.feito[data-id="{l["id"]}"]').count())
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(300)
    print('ERROS', erros); b.close()
