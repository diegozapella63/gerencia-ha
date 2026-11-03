"""Aporte vencido sem aplicar é compromisso como qualquer conta: aparece nos avisos de contas atrasadas, como Atrasado
na lista do mês dele e nas contas a pagar do CronologIA (atrasada)."""
import sys, os, json, calendar, urllib.request
from datetime import date
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, perto, valores, mes
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
hoje = date.today(); passado = mes(-1)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    # o aporte do mês passado passa para o dia 20 e some o que tinha sido aplicado: fica vencido, sem aplicar
    d = get('api/state')
    ap = [r for r in d['recorrencias'] if r.get('aporte')][0]
    ap['dia'] = 20
    d['lancamentos'] = [l for l in d['lancamentos'] if not (l.get('recorrencia') == ap['id'] and l.get('competencia') == passado)]
    iptu = [l for l in d['lancamentos'] if l['descricao'] == 'IPTU'][0]['valor']
    r = urllib.request.Request(B + 'api/state', data=json.dumps(d).encode(), method='PUT', headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(r)
    pg.reload(); pg.wait_for_timeout(1200)
    aviso = pg.locator('.card.flush:has(.rot-t:text("Avisos")) .op:has-text("atrasad")')
    igual(aviso.count(), 1, 'um aviso de contas atrasadas')
    if aviso.count():
        igual(aviso.locator('.op-t b').inner_text(), '2 contas atrasadas', 'duas contas atrasadas')
        igual(aviso.locator('.op-t span').inner_text(), 'Aporte nos investimentos, IPTU', 'o aporte e o IPTU')
        perto(valores(aviso.locator('.op-n').inner_text())[0], round(ap['valor'] + iptu), 'o total atrasado soma o aporte e o IPTU', tol=0.6)
    pg.screenshot(path=f'{SP}/shots/aporte-divida.png')
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(400)
    if pg.locator('[data-a="cx-modo"][data-v="lista"]:not(.on)').count(): pg.click('[data-a="cx-modo"][data-v="lista"]'); pg.wait_for_timeout(300)
    linha = pg.locator('.lanc:has-text("Aporte nos investimentos")').first.inner_text()
    tem(linha, 'Investimentos · Banco Coral · Ana · fixo', 'neste mês: o aporte fixo do exemplo, na conta do Banco Coral')
    pg.click('[data-a="cx-mes"][data-v="-1"]'); pg.wait_for_timeout(400)
    linha = pg.locator('.lanc:has-text("Aporte nos investimentos")')
    igual(linha.count(), 1, 'no mês passado, o aporte aparece na lista')
    if linha.count():
        tem(linha.first.inner_text(), 'Atrasado', 'no mês passado, o aporte não aplicado está Atrasado')
        tem(linha.first.inner_text(), '− R$ 800,00', 'com o valor do aporte')
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'gerencia', 'app'))
    import integracao
    ult = mes(1); de = date.fromisoformat(mes(-2) + '-01'); ate = date(int(ult[:4]), int(ult[5:]), calendar.monthrange(int(ult[:4]), int(ult[5:]))[1])
    lst = integracao.listar(get('api/state'), de, ate, hoje)
    c = next((x for x in lst['contas'] if x['id'] == f'v:{ap["id"]}:{passado}'), None)
    sim(c, 'CronologIA: o aporte do mês passado está nas contas a pagar', [x['id'] for x in lst['contas']])
    if c:
        igual((c['descricao'], c['valor'], c['vencimento'], c['pago'], c['atrasada']), ('Aporte nos investimentos', 800, f'{passado}-20', False, True), 'CronologIA: atrasado, a pagar, no dia 20')
    print('ERROS', erros); b.close()
