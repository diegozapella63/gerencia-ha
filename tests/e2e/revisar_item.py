"""Revisar antes, sem sair da conferência do Atualizar saldos: no investimento novo, todos os dados (valor, nome, banco,
tipo, rendimento, taxa, vencimento e liquidez); no que já existe, só o saldo; Pronto e Voltar retornam à lista e Atualizar
grava o novo com o que foi revisado e o saldo novo no que existia."""
import sys, json, urllib.request
from datetime import date
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
    st0 = get('api/state'); n0 = len(st0['investimentos'])
    bancos = {x['nome']: x['id'] for x in st0['bancos']}
    reserva = [i for i in st0['investimentos'] if i.get('banco') == bancos['Banco Lua'] and i.get('titular') != 'terceiros'][0]
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300)
    pg.click('.op[data-a="ia-saldos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="ias-pessoa"][data-v="meu"]'); pg.wait_for_timeout(200)
    pg.fill('#ia-txt', 'Banco Lua, valor atualizado, R$ 30.000\nBanco Mar, valor atualizado, R$ 700'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2500)
    igual((pg.inner_text('.folha-cab h2'), pg.locator('.ia-item').count()), ('Conferir os saldos', 2), 'conferir: um item por saldo')
    pg.locator('[data-a="iai-revisar"]').nth(1).click(); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Revisar investimento novo', 'Revisar antes do novo (Banco Mar)')
    igual(sorted(pg.locator('[data-iae]').evaluate_all('es => es.map(e => e.dataset.iae)')), sorted(['valor', 'nome', 'banco', 'tipo', 'indexador', 'taxa', 'vencimento']), 'novo: valor, nome, banco, tipo, rendimento, taxa e vencimento')
    igual(pg.locator('[data-a="iae-liq"]').all_inner_texts(), ['Diária', 'No venc.'], 'novo: e a liquidez')
    igual(pg.locator('[data-a="iae-ok"]').count(), 1, 'continua na janela da IA (com Pronto)')
    pg.fill('#iae-nome', 'CDB Mar 2027'); pg.select_option('#iae-tipo', 'cdb'); pg.wait_for_timeout(200)
    pg.fill('#iae-taxa', '120'); pg.fill('#iae-venc', '2027-12-01')
    pg.screenshot(path=f'{SP}/shots/revisar-item.png')
    pg.click('[data-a="iae-ok"]'); pg.wait_for_timeout(300)
    igual(pg.inner_text('.folha-cab h2'), 'Conferir os saldos', 'Pronto volta para a conferência')
    igual(pg.locator('.ia-item').nth(1).inner_text().split('\n')[0], 'Banco Mar · CDB Mar 2027', 'a linha mostra o que foi revisado')
    igual(pg.locator('.ia-item').count(), 2, 'o resto como estava')
    pg.locator('[data-a="iai-revisar"]').first.click(); pg.wait_for_timeout(300)
    igual(pg.inner_text('.folha-cab h2'), f"Revisar {reserva['nome']}", 'Revisar o que já existe (o do Banco Lua)')
    igual(pg.locator('[data-iae]').evaluate_all('es => es.map(e => e.dataset.iae)'), ['valor'], 'existente: só o saldo')
    pg.click('[data-a="iae-voltar"]'); pg.wait_for_timeout(300)
    igual(pg.inner_text('.folha-cab h2'), 'Conferir os saldos', 'Voltar volta para a conferência')
    pg.click('[data-a="ia-salvar"]'); pg.wait_for_timeout(1200)
    st = get('api/state')['investimentos']
    igual(len(st), n0 + 1, 'Atualizar: um investimento novo')
    novo = [i for i in st if i['nome'] == 'CDB Mar 2027']
    igual([(i['tipo'], i['indexador'], i['taxa'], i['vencimento'], i['valor'], i['titular']) for i in novo], [('cdb', 'cdi_pct', 120, '2027-12-01', 700, 'meu')], 'o novo com os dados revisados')
    r = [i for i in st if i['id'] == reserva['id']][0]
    igual((r['valor'], r['data_valor']), (30000, date.today().isoformat()), 'o que existia com o saldo novo, de hoje')
    print('ERROS', erros); b.close()
