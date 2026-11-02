import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
def inv(nome_id):
    return next(i for i in get('api/state')['investimentos'] if i['id'] == nome_id)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, device_scale_factor=2, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    d = get('api/state')
    cdb = next(i for i in d['investimentos'] if i['tipo'] == 'cdb' and i.get('titular') != 'terceiros')
    n0 = len(d['lancamentos'])
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click(f'.inv[data-id="{cdb["id"]}"]'); pg.wait_for_timeout(400)
    print('1 editar:', pg.inner_text('.folha-cab h2'), '|', pg.inner_text('.inv-aplicar').replace('\n', ' | '))
    pg.click('[data-a="inv-aplicar"]'); pg.wait_for_timeout(400)
    print('2 aplicar:', pg.inner_text('.folha-cab h2'), '| foco', pg.evaluate('document.activeElement.id'), '| no caixa:', pg.locator('[data-a="ap-destino"]').all_inner_texts(), '| marcado:', pg.inner_text('[data-a="ap-destino"].on'))
    pg.keyboard.type('300000'); pg.wait_for_timeout(200)
    print('  ajuda:', pg.inner_text('#ap-ajuda'), '| botão', pg.inner_text('[data-a="ap-ok"]'))
    pg.screenshot(path=f'{SP}/shots/aplicar.png')
    pg.click('[data-a="ap-destino"][data-v="novo"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="ap-ok"]'); pg.wait_for_timeout(900)
    d = get('api/state'); x = inv(cdb['id'])
    novos = [l for l in d['lancamentos'] if l.get('investimento') == cdb['id']]
    print('3 depois: valor', x['valor'], 'data', x['data_valor'], '| lançamentos', len(d['lancamentos']) - n0, [(l['descricao'], l['valor'], l.get('aporte'), l['pago'], l['categoria'], l['conta']) for l in novos])
    # Apliquei no aporte do mês, com o investimento
    rec = next(r for r in d['recorrencias'] if r.get('aporte'))
    rec['dia'] = 20
    d['lancamentos'] = [l for l in d['lancamentos'] if not (l.get('recorrencia') == rec['id'] and l.get('competencia') == '2026-10')]
    urllib.request.urlopen(urllib.request.Request(B + 'api/state', data=json.dumps(d).encode(), method='PUT', headers={'Content-Type': 'application/json'}))
    pg.reload(); pg.wait_for_timeout(1000)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.locator('.lanc:has-text("Aporte nos investimentos") [data-a="lanc-pagar"]').first.click(); pg.wait_for_timeout(400)
    print('4 Apliquei:', pg.inner_text('.folha-cab h2'), '| investimentos:', pg.locator('[data-a="pg-inv"]').count())
    pg.click(f'[data-a="pg-inv"][data-v="{cdb["id"]}"]'); pg.wait_for_timeout(200)
    v0 = inv(cdb['id'])['valor']
    pg.click('[data-a="pg-ok"]'); pg.wait_for_timeout(900)
    d = get('api/state'); x = inv(cdb['id'])
    r2 = next(r for r in d['recorrencias'] if r['id'] == rec['id'])
    print('5 depois: valor', v0, '->', x['valor'], '| recorrência lembra:', r2.get('investimento') == cdb['id'])
    # aplicar com o aporte do mês a aplicar: oferece a baixa
    d['lancamentos'] = [l for l in d['lancamentos'] if not (l.get('recorrencia') == rec['id'] and l.get('competencia') == '2026-10')]
    urllib.request.urlopen(urllib.request.Request(B + 'api/state', data=json.dumps(d).encode(), method='PUT', headers={'Content-Type': 'application/json'}))
    pg.reload(); pg.wait_for_timeout(1000)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click(f'.inv[data-id="{cdb["id"]}"]'); pg.wait_for_timeout(400); pg.click('[data-a="inv-aplicar"]'); pg.wait_for_timeout(400)
    print('6 com aporte a aplicar:', pg.locator('[data-a="ap-destino"]').all_inner_texts(), '| marcado:', pg.inner_text('[data-a="ap-destino"].on'))
    pg.keyboard.type('80000'); pg.click('[data-a="ap-ok"]'); pg.wait_for_timeout(900)
    d = get('api/state')
    mat = [l for l in d['lancamentos'] if l.get('recorrencia') == rec['id'] and l.get('competencia') == '2026-10']
    print('  baixa:', [(l['valor'], l['pago'], l.get('investimento') == cdb['id']) for l in mat])
    # IA: "apliquei 3000 no cdb"
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300); pg.click('.op[data-a="ia"]'); pg.wait_for_timeout(300)
    pg.fill('#ia-txt', 'apliquei 3000 no cdb'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2600)
    print('7 IA:', pg.locator('.ia-sec').all_inner_texts(), '|', pg.locator('.ia-atualiza').all_inner_texts())
    v0 = inv(cdb['id'])['valor']; n1 = len(get('api/state')['lancamentos'])
    pg.click('[data-a="ia-salvar"]'); pg.wait_for_timeout(900)
    d = get('api/state'); x = inv(cdb['id'])
    print('  depois: valor', v0, '->', x['valor'], '| lançamento aporte:', [(l['descricao'], l.get('aporte')) for l in d['lancamentos'][n1 - len(d['lancamentos']):]] if len(d['lancamentos']) > n1 else None)
    # Novo aporte: a aplicar não pede investimento; aplicado pede e soma
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300); pg.click('[data-a="lf-tipo"][data-v="aporte"]'); pg.wait_for_timeout(300)
    print('8 novo aporte: situação', pg.inner_text('[data-a="lf-pago"].on'), '| pede investimento?', pg.locator('[data-a="lf-inv"]').count())
    pg.click('#lf-valor'); pg.keyboard.type('50000')
    pg.click('[data-a="lf-pago"][data-v="1"]'); pg.wait_for_timeout(300)
    print('  aplicado: investimentos', pg.locator('[data-a="lf-inv"]').count(), '| escolhido', pg.locator('[data-a="lf-inv"].on').count())
    pg.screenshot(path=f'{SP}/shots/aporte-aplicado.png', full_page=True)
    pg.click('[data-a="lf-salvar"]:not([data-mais])'); pg.wait_for_timeout(500)
    print('  sem escolher:', pg.inner_text('.folha .msg-erro') if pg.locator('.folha .msg-erro').count() else 'salvou?!')
    v0 = inv(cdb['id'])['valor']
    pg.click(f'[data-a="lf-inv"][data-v="{cdb["id"]}"]'); pg.wait_for_timeout(300)
    print('  ajuda:', pg.locator('.folha .campo:has([data-a="lf-inv"]) .ajuda').inner_text())
    pg.click('[data-a="lf-salvar"]:not([data-mais])'); pg.wait_for_timeout(900)
    d = get('api/state'); x = inv(cdb['id'])
    r3 = [r for r in d['recorrencias'] if r.get('aporte') and r.get('valor') == 500]
    print('  salvou: valor', v0, '->', x['valor'], '| recorrência com investimento:', [(r['valor'], r.get('investimento') == cdb['id']) for r in r3])
    print('ERROS', erros); b.close()
