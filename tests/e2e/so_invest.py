"""Colar mensagem a partir do Novo investimento: só investimentos (nada vai para o caixa); um valor com banco ou nome é o
saldo dele, "dinheiro" vira um investimento sem rendimento e o dono vem do texto ("tudo dinheiro da mãe")."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
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
    st0 = get('api/state'); nl0 = len(st0['lancamentos']); ni0 = len(st0['investimentos'])
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="ia-de"][data-ini="texto"]'); pg.wait_for_timeout(400)
    pg.fill('#ia-txt', '15mil dinheiro\n30.350,00 Banco Lua\n\nTudo dinheiro da mãe'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2600)
    igual(pg.inner_text('.folha-cab h2'), 'Conferir investimentos', 'conferir só investimentos')
    igual(pg.locator('[data-iai="contasel"]').count(), 0, 'nenhum lançamento para o caixa')
    itens = [it.inner_text().split('\n') for it in pg.locator('.ia-item').all()]
    igual([x[0] for x in itens], ['Dinheiro', 'Banco Lua'], 'um investimento por valor')
    igual([[y for y in x if y.startswith('Novo investimento de')] for x in itens], [['Novo investimento de Mãe, com R$ 15.000,00'], ['Novo investimento de Mãe, com R$ 30.350,00']], 'novos, da Mãe, com o saldo lido ("15mil", "30.350,00")')
    pg.screenshot(path=f'{SP}/shots/so-invest.png')
    pg.click('[data-a="ia-salvar"]'); pg.wait_for_timeout(1200)
    st = get('api/state')
    igual(len(st['lancamentos']) - nl0, 0, 'salvar não lança nada no caixa')
    igual([(i['nome'], i['tipo'], i['titular'], i.get('terceiro'), i['valor'], i['indexador']) for i in st['investimentos'][ni0:]],
          [('Dinheiro', 'dinheiro', 'terceiros', 'Mãe', 15000, 'parado'), ('Banco Lua', 'outro', 'terceiros', 'Mãe', 30350, 'cdi_pct')], 'os novos da Mãe: o dinheiro sem rendimento e o saldo do Banco Lua')
    print('ERROS', erros); b.close()
