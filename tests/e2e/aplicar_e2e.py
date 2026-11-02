"""Aplicar mais num investimento: baixa no aporte do mês, lançar à parte, Apliquei no caixa, IA e aporte novo."""
import sys, json, urllib.request
from datetime import date
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, perto, valores, mes
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
    igual(pg.inner_text('.folha-cab h2'), 'Editar investimento', 'abre o investimento')
    igual(pg.locator('.inv-aplicar .btn').all_inner_texts(), ['Aplicar mais', 'Transferir'], 'botões do investimento')
    pg.click('[data-a="inv-aplicar"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Aplicar em ' + cdb['nome'], 'janela Aplicar')
    igual(pg.evaluate('document.activeElement.id'), 'ap-v', 'o teclado abre no valor')
    igual(pg.locator('[data-a="ap-destino"]').all_inner_texts()[1:], ['Lançar à parte', 'Não lançar'], 'opções no caixa')
    tem(pg.inner_text('[data-a="ap-destino"].on'), 'Baixa no aporte de', 'com aporte do mês a aplicar, a baixa vem marcada')
    pg.keyboard.type('300000'); pg.wait_for_timeout(200)
    antes_depois = valores(pg.inner_text('#ap-ajuda'))
    perto(antes_depois[1] - antes_depois[0], 3000, 'mostra de quanto para quanto vai')
    igual(pg.inner_text('[data-a="ap-ok"]'), 'Aplicar R$ 3.000', 'o valor no botão')
    pg.screenshot(path=f'{SP}/shots/aplicar.png')
    pg.click('[data-a="ap-destino"][data-v="novo"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="ap-ok"]'); pg.wait_for_timeout(900)
    d = get('api/state'); x = inv(cdb['id'])
    novos = [l for l in d['lancamentos'] if l.get('investimento') == cdb['id']]
    perto(x['valor'], antes_depois[1], 'o investimento fica com o valor mostrado')
    igual(x['data_valor'], date.today().isoformat(), 'valor de hoje')
    igual(len(d['lancamentos']) - n0, 1, 'um lançamento à parte')
    igual([(l['descricao'], l['valor'], l.get('aporte'), l['pago'], l['categoria']) for l in novos], [('Aporte: ' + cdb['nome'], 3000, True, True, 'c-investimentos')], 'o aporte no caixa')
    # Apliquei no aporte do mês, com o investimento
    rec = next(r for r in d['recorrencias'] if r.get('aporte'))
    rec['dia'] = 20
    d['lancamentos'] = [l for l in d['lancamentos'] if not (l.get('recorrencia') == rec['id'] and l.get('competencia') == mes(-1))]
    urllib.request.urlopen(urllib.request.Request(B + 'api/state', data=json.dumps(d).encode(), method='PUT', headers={'Content-Type': 'application/json'}))
    pg.reload(); pg.wait_for_timeout(1000)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.locator('.lanc:has-text("Aporte nos investimentos") [data-a="lanc-pagar"]').first.click(); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Confirmar aporte', 'Apliquei no caixa')
    sim(pg.locator('[data-a="pg-inv"]').count() >= 2, 'pergunta em qual investimento')
    pg.click(f'[data-a="pg-inv"][data-v="{cdb["id"]}"]'); pg.wait_for_timeout(200)
    v0 = inv(cdb['id'])['valor']
    pg.click('[data-a="pg-ok"]'); pg.wait_for_timeout(900)
    d = get('api/state'); x = inv(cdb['id'])
    r2 = next(r for r in d['recorrencias'] if r['id'] == rec['id'])
    perto(x['valor'], v0 + rec['valor'], 'o aporte soma no investimento')
    igual(r2.get('investimento'), cdb['id'], 'o fixo lembra o investimento')
    # aplicar com o aporte do mês a aplicar: oferece a baixa
    d['lancamentos'] = [l for l in d['lancamentos'] if not (l.get('recorrencia') == rec['id'] and l.get('competencia') == mes(-1))]
    urllib.request.urlopen(urllib.request.Request(B + 'api/state', data=json.dumps(d).encode(), method='PUT', headers={'Content-Type': 'application/json'}))
    pg.reload(); pg.wait_for_timeout(1000)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click(f'.inv[data-id="{cdb["id"]}"]'); pg.wait_for_timeout(400); pg.click('[data-a="inv-aplicar"]'); pg.wait_for_timeout(400)
    tem(pg.inner_text('[data-a="ap-destino"].on'), 'Baixa no aporte de', 'oferece a baixa no aporte que falta')
    pg.keyboard.type('80000'); pg.click('[data-a="ap-ok"]'); pg.wait_for_timeout(900)
    d = get('api/state')
    mat = [l for l in d['lancamentos'] if l.get('recorrencia') == rec['id'] and l.get('competencia') == mes(-1)]
    igual([(l['valor'], l['pago'], l.get('investimento') == cdb['id']) for l in mat], [(rec['valor'], True, True)], 'baixa no aporte do mês')
    # IA: "apliquei 3000 no cdb"
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300); pg.click('.op[data-a="ia"]'); pg.wait_for_timeout(300)
    pg.fill('#ia-txt', 'apliquei 3000 no cdb'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2600)
    tem(' '.join(pg.locator('.ia-atualiza').all_inner_texts()), 'Aplica R$ 3.000,00 em ' + cdb['nome'], 'IA: entende que é um aporte no CDB')
    v0 = inv(cdb['id'])['valor']; n1 = len(get('api/state')['lancamentos'])
    pg.click('[data-a="ia-salvar"]'); pg.wait_for_timeout(900)
    d = get('api/state'); x = inv(cdb['id'])
    perto(x['valor'], v0 + 3000, 'IA: soma no CDB')
    # Novo aporte: a aplicar não pede investimento; aplicado pede e soma
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300); pg.click('[data-a="lf-tipo"][data-v="aporte"]'); pg.wait_for_timeout(300)
    igual(pg.inner_text('[data-a="lf-pago"].on'), 'A aplicar', 'aporte novo começa a aplicar')
    igual(pg.locator('[data-a="lf-inv"]').count(), 0, 'a aplicar não pede investimento')
    pg.click('#lf-valor'); pg.keyboard.type('50000')
    pg.click('[data-a="lf-pago"][data-v="1"]'); pg.wait_for_timeout(300)
    sim(pg.locator('[data-a="lf-inv"]').count() > 0, 'aplicado pede o investimento')
    igual(pg.locator('[data-a="lf-inv"].on').count(), 0, 'nenhum escolhido de início')
    pg.screenshot(path=f'{SP}/shots/aporte-aplicado.png', full_page=True)
    pg.click('[data-a="lf-salvar"]:not([data-mais])'); pg.wait_for_timeout(500)
    igual(pg.inner_text('.folha .msg-erro') if pg.locator('.folha .msg-erro').count() else 'salvou', 'Escolha em qual investimento o aporte foi aplicado.', 'sem escolher não salva')
    v0 = inv(cdb['id'])['valor']
    pg.click(f'[data-a="lf-inv"][data-v="{cdb["id"]}"]'); pg.wait_for_timeout(300)
    tem(pg.locator('.folha .campo:has([data-a="lf-inv"]) .ajuda').inner_text(), cdb['nome'] + ': R$', 'mostra como fica o investimento')
    pg.click('[data-a="lf-salvar"]:not([data-mais])'); pg.wait_for_timeout(900)
    d = get('api/state'); x = inv(cdb['id'])
    r3 = [r for r in d['recorrencias'] if r.get('aporte') and r.get('valor') == 500]
    perto(x['valor'], v0 + 500, 'aporte aplicado soma no investimento')
    igual([(r['valor'], r.get('investimento') == cdb['id']) for r in r3], [(500, True)], 'fixo de aporte com o investimento')
    print('ERROS', erros); b.close()
