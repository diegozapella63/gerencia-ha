import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    d = get('api/state')
    ap = [r for r in d['recorrencias'] if r.get('aporte')][0]
    ap['dia'] = 20
    d['lancamentos'] = [l for l in d['lancamentos'] if not (l.get('recorrencia') == ap['id'] and l.get('competencia') == '2026-10')]
    r = urllib.request.Request(B + 'api/state', data=json.dumps(d).encode(), method='PUT', headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(r)
    pg.reload(); pg.wait_for_timeout(1200)
    avisos = pg.locator('.card.flush:has(.rot-t:text("Avisos")) .op-t b').all_inner_texts()
    print('1 avisos:', avisos, '| texto com Aporte?', any('Aporte' in x for x in pg.locator('.op-t span').all_inner_texts()))
    print('  resumo Saiu:', pg.inner_text('.cx-resumo > div:nth-child(2)').replace('\n', ' | '))
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(400)
    linha = pg.locator('.lanc:has-text("Aporte nos investimentos")').first
    print('2 linha:', linha.inner_text().replace('\n', ' | '))
    sys.path.insert(0, '/home/claude/gerencia-ha/gerencia/app')
    import integracao
    from datetime import date
    d2 = get('api/state')
    lst = integracao.listar(d2, date(2026, 9, 1), date(2026, 12, 31), date(2026, 10, 28))
    itens = lst.get('contas') or lst.get('itens') or lst
    txt = json.dumps(itens, ensure_ascii=False)
    print('3 CronologIA: aporte nas contas a pagar?', 'Aporte' in txt, '| chaves', list(lst)[:5] if isinstance(lst, dict) else type(lst))
    print('ERROS', erros); b.close()
