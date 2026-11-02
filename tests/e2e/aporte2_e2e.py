import sys, json, urllib.request
from datetime import date
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
def put(d):
    r = urllib.request.Request(B + 'api/state', data=json.dumps(d).encode(), method='PUT', headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(r)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 396, 'height': 900}, device_scale_factor=2, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    # 1 Evolução: sem campo; mostra o aporte das contas a pagar
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="evolucao"]'); pg.wait_for_timeout(500)
    print('1 campo de digitar:', pg.locator('#aporte').count(), '| info:', pg.inner_text('.aporte-info').replace('\n', ' | '), '| botões:', pg.locator('.ctrl .btns .btn').all_inner_texts())
    pg.locator('.ctrl').screenshot(path=f'{SP}/shots/ap2-evolucao.png')
    pg.click('[data-a="aporte-ajustar"]'); pg.wait_for_timeout(400)
    print('2 mudar: janela', pg.inner_text('.folha-cab h2'), '|', pg.inner_text('.folha .aviso-fixo'))
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # 3 Adicionar › Aporte
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300)
    print('3 opções:', [x.split('\n')[0] for x in pg.locator('.escolhas .op').all_inner_texts()])
    pg.click('.escolhas [data-a="aporte-novo"]'); pg.wait_for_timeout(400)
    print('  janela:', pg.inner_text('.folha-cab h2'), '| tipo:', pg.inner_text('.tipo-seg button.on'), '| repetir:', pg.inner_text('[data-k="repete"].on'),
          '| categorias:', pg.locator('[data-a="lf-set"][data-k="categoria"]').count(), '| situação:', pg.locator('[data-a="lf-pago"]').all_inner_texts(), '| cartão:', pg.locator('[data-a="lf-cartao"]').count())
    pg.screenshot(path=f'{SP}/shots/ap2-novo.png', full_page=True)
    pg.click('#lf-valor'); pg.keyboard.type('20000')
    pg.fill('#lf-data', '2026-11-15'); pg.wait_for_timeout(500)
    print('  situação depois da data:', pg.inner_text('[data-a="lf-pago"].on'))
    pg.click('[data-a="lf-salvar"]:not([data-mais])'); pg.wait_for_timeout(800)
    rs = [(r['descricao'], r['valor'], r['dia'], r['inicio'], r.get('categoria'), r.get('cartao'), r.get('aporte')) for r in get('api/state')['recorrencias'] if r.get('aporte')]
    print('4 aportes fixos:', rs)
    print('  Início em 1 ano:', pg.locator('.hl-row').nth(4).inner_text().replace('\n', ' | '))
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(400)
    print('  Evolução:', pg.inner_text('.aporte-info').replace('\n', ' | '), '| botões:', pg.locator('.ctrl .btns .btn').all_inner_texts())
    pg.click('[data-a="aporte-ajustar"]'); pg.wait_for_timeout(500)
    print('  com dois, abre:', pg.inner_text('.cab h1'), pg.inner_text('.mais-abas button.on'))
    # 5 trocar de Aporte para Despesa
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    print('5 Caixa › Adicionar:', pg.inner_text('.folha-cab h2'), '| tipos:', pg.locator('.tipo-seg button').all_inner_texts())
    pg.click('[data-a="lf-tipo"][data-v="aporte"]'); pg.wait_for_timeout(300)
    r1 = (pg.inner_text('.folha-cab h2'), pg.inner_text('[data-k="repete"].on'), pg.locator('[data-k="categoria"]').count())
    pg.click('[data-a="lf-tipo"][data-v="despesa"]'); pg.wait_for_timeout(300)
    r2 = (pg.inner_text('.folha-cab h2'), pg.inner_text('[data-k="repete"].on'), pg.locator('[data-k="categoria"]').count())
    print('  aporte:', r1, '| despesa de novo:', r2)
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # 6 aporte vencido sem aplicar: é compromisso (conta atrasada, a pagar e CronologIA)
    d = get('api/state')
    ap = [r for r in d['recorrencias'] if r.get('aporte') and r['id'] == 'r-aporte'][0]
    ap['dia'] = 20
    d['lancamentos'] = [l for l in d['lancamentos'] if not (l.get('recorrencia') == 'r-aporte' and l.get('competencia') == '2026-10')]
    put(d); pg.reload(); pg.wait_for_timeout(1200)
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(400)
    print('6 avisos:', [x.replace('\n', ' · ') for x in pg.locator('.op-t').all_inner_texts() if 'atrasad' in x or 'Vence nos' in x])
    print('  resumo Saiu:', pg.inner_text('.cx-resumo > div:nth-child(2)').replace('\n', ' | '))
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(400)
    print('  linha:', pg.locator('.lanc:has-text("Aporte nos investimentos")').first.inner_text().replace('\n', ' | '))
    import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'gerencia', 'app'))
    import integracao
    lst = integracao.listar(get('api/state'), date(2026, 9, 1), date(2026, 12, 31), date(2026, 10, 28))
    print('  CronologIA:', [(c['descricao'], c['vencimento'], c.get('pago')) for c in lst['contas'] if 'Aporte' in c['descricao']][:4])
    # 7 terceiros
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="evolucao"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="g"][data-k="gEscopo"][data-v="terc"]') if pg.locator('[data-a="g"][data-k="gEscopo"][data-v="terc"]').count() else None
    pg.wait_for_timeout(300)
    print('7 terceiros:', pg.inner_text('.ctrl').split('\n')[2:4])
    print('ERROS', erros); b.close()
