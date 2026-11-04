"""Aporte como conta a pagar: a Evolução mostra o aporte das contas a pagar (sem campo de digitar), Adicionar › Aporte
cria um aporte fixo A aplicar, a projeção soma os dois, trocar Aporte ⇄ Despesa no formulário e o aporte vencido
sem aplicar vira conta atrasada (avisos, lista e contas do CronologIA); com De terceiros, o aporte não entra."""
import sys, os, json, calendar, urllib.request
from datetime import date
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sem, sim, valores, mes
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
def put(d):
    r = urllib.request.Request(B + 'api/state', data=json.dumps(d).encode(), method='PUT', headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(r)
hoje = date.today()
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 396, 'height': 900}, device_scale_factor=2, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    a_pagar = lambda: valores(pg.inner_text('.cx-resumo > div:nth-child(2)'))[-1]
    pagar0 = a_pagar()
    # 1 Evolução: sem campo; mostra o aporte das contas a pagar
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="evolucao"]'); pg.wait_for_timeout(500)
    igual(pg.locator('#aporte').count(), 0, 'Evolução sem campo para digitar o aporte')
    igual(pg.inner_text('.aporte-info').split('\n'), ['R$ 800,00', 'Todo dia 6, saindo de Banco Coral · Ana.'], 'o aporte fixo do exemplo, com dia e conta')
    igual([x.strip() for x in pg.locator('.ctrl .btns-2 .btn').all_inner_texts()], ['Mudar o aporte', 'Outro aporte'], 'botões do aporte')
    pg.locator('.ctrl').screenshot(path=f'{SP}/shots/ap2-evolucao.png')
    pg.click('[data-a="aporte-ajustar"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Aporte', 'Mudar o aporte abre o aporte do mês')
    tem(pg.inner_text('.folha .aviso-fixo'), 'todo dia 6. Valor padrão R$ 800,00', 'com o dia e o valor padrão')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # 3 Adicionar › Aporte
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300)
    igual([x.split('\n')[0] for x in pg.locator('.escolhas .op').all_inner_texts()], ['Despesa', 'Recebimento', 'Aporte', 'Ler com IA', 'Investimento', 'Atualizar saldos'], 'opções do Adicionar')
    pg.click('.escolhas [data-a="aporte-novo"]'); pg.wait_for_timeout(400)
    igual((pg.inner_text('.folha-cab h2'), pg.inner_text('.tipo-seg button.on').strip(), pg.inner_text('[data-k="repete"].on').strip()), ('Novo aporte', 'Aporte', 'Todo mês'), 'Novo aporte, todo mês')
    igual((pg.locator('[data-a="lf-set"][data-k="categoria"]').count(), pg.locator('[data-a="lf-cartao"]').count()), (0, 0), 'aporte sem categoria nem cartão')
    igual([x.strip() for x in pg.locator('[data-a="lf-pago"]').all_inner_texts()], ['Aplicado', 'A aplicar'], 'situação: Aplicado ou A aplicar')
    pg.screenshot(path=f'{SP}/shots/ap2-novo.png', full_page=True)
    pg.click('#lf-valor'); pg.keyboard.type('20000')
    pg.fill('#lf-data', hoje.isoformat()); pg.wait_for_timeout(500)
    igual(pg.inner_text('[data-a="lf-pago"].on').strip(), 'A aplicar', 'o aporte novo nasce A aplicar (mesmo com a data de hoje)')
    pg.click('[data-a="lf-salvar"]:not([data-mais])'); pg.wait_for_timeout(800)
    rs = [(r['descricao'], r['valor'], r['dia'], r['inicio'], r.get('categoria'), bool(r.get('cartao')), r.get('aporte')) for r in get('api/state')['recorrencias'] if r.get('aporte')]
    igual(rs, [('Aporte nos investimentos', 800, 6, mes(-6), 'c-investimentos', False, True), ('Aporte nos investimentos', 200, hoje.day, mes(), 'c-investimentos', False, True)], 'dois aportes fixos (o do exemplo e o novo)')
    igual(round(a_pagar() - pagar0, 2), 200.0, 'o aporte novo entra no "a pagar" do mês')
    um_ano = pg.locator('.hl-row:has-text("Seu dinheiro em 1 ano")').inner_text()
    tem(um_ano, 'Com aporte de R$ 1.000 por mês', 'Início: o dinheiro em 1 ano conta os dois aportes')
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.aporte-info').split('\n'), ['R$ 1.000,00', '2 aportes fixos nas contas a pagar.'], 'Evolução: a soma dos aportes fixos')
    igual([x.strip() for x in pg.locator('.ctrl .btns-2 .btn').all_inner_texts()], ['Ver os aportes', 'Outro aporte'], 'com dois aportes: Ver os aportes')
    pg.click('[data-a="aporte-ajustar"]'); pg.wait_for_timeout(500)
    igual((pg.inner_text('.cab h1'), pg.inner_text('.uplink').strip()), ('Caixa', 'Mais'), 'com dois, abre Mais › Caixa (os fixos)')
    # 5 trocar de Aporte para Despesa
    cats_despesa = len([c for c in get('api/state')['categorias'] if c.get('tipo', 'despesa') == 'despesa'])
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Nova despesa', 'Caixa › Adicionar abre a Nova despesa')
    igual([x.strip() for x in pg.locator('.tipo-seg button').all_inner_texts()], ['Despesa', 'Recebimento', 'Aporte'], 'tipos no formulário')
    pg.click('[data-a="lf-tipo"][data-v="aporte"]'); pg.wait_for_timeout(300)
    r1 = (pg.inner_text('.folha-cab h2'), pg.inner_text('[data-k="repete"].on').strip(), pg.locator('[data-k="categoria"]').count())
    pg.click('[data-a="lf-tipo"][data-v="despesa"]'); pg.wait_for_timeout(300)
    r2 = (pg.inner_text('.folha-cab h2'), pg.inner_text('[data-k="repete"].on').strip(), pg.locator('[data-k="categoria"]').count())
    igual(r1, ('Novo aporte', 'Todo mês', 0), 'trocar para Aporte: todo mês, sem categoria')
    igual(r2, ('Nova despesa', 'Uma vez', cats_despesa), 'voltar para Despesa: uma vez, com as categorias de gasto')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # 6 aporte vencido sem aplicar: é compromisso (conta atrasada, a pagar e CronologIA)
    passado = mes(-1)
    d = get('api/state')
    ap = [r for r in d['recorrencias'] if r.get('aporte') and r['id'] == 'r-aporte'][0]
    ap['dia'] = 20
    d['lancamentos'] = [l for l in d['lancamentos'] if not (l.get('recorrencia') == 'r-aporte' and l.get('competencia') == passado)]
    put(d); pg.reload(); pg.wait_for_timeout(1200)
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(400)
    atras = [x.replace('\n', ' · ') for x in pg.locator('.op-t').all_inner_texts() if 'atrasad' in x]
    igual(atras, ['2 contas atrasadas · Aporte nos investimentos, IPTU'], 'aviso: o aporte do mês passado atrasado, junto do IPTU')
    tem(pg.inner_text('.cx-resumo > div:nth-child(2)'), 'a pagar', 'o resumo do mês tem o a pagar')
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(400)
    linha = pg.locator('.lanc:has-text("Aporte nos investimentos"):has-text("200,00")').first.inner_text()
    tem(linha, 'A aplicar', 'na lista, o aporte novo fica A aplicar')
    tem(linha, 'fixo', 'marcado como fixo')
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'gerencia', 'app'))
    import integracao
    ult = mes(1); de = date.fromisoformat(mes(-2) + '-01'); ate = date(int(ult[:4]), int(ult[5:]), calendar.monthrange(int(ult[:4]), int(ult[5:]))[1])
    lst = integracao.listar(get('api/state'), de, ate, hoje)
    aps = {c['id']: c for c in lst['contas'] if c['descricao'] == 'Aporte nos investimentos'}
    v = aps.get(f'v:r-aporte:{passado}') or {}
    igual((v.get('vencimento'), v.get('pago'), v.get('atrasada')), (f'{passado}-20', False, True), 'CronologIA: o aporte do mês passado é conta atrasada')
    sim(any(not c['pago'] and c['vencimento'] == hoje.isoformat() and c['valor'] == 200 for c in aps.values()), 'CronologIA: o aporte novo é conta a pagar de hoje', list(aps.values()))
    # 7 terceiros
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="evolucao"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="g"][data-k="gEscopo"][data-v="terc"]'); pg.wait_for_timeout(300)
    ctrl = pg.inner_text('.ctrl')
    tem(ctrl, 'Aportes contam só nos seus investimentos.', 'De terceiros: o aporte não entra')
    igual(pg.locator('[data-a="aporte-ajustar"]').count(), 0, 'De terceiros: sem Mudar o aporte')
    tem(pg.inner_text('.leg'), 'Valor investido', 'De terceiros: legenda sem aportes')
    sem(pg.inner_text('.leg'), 'aportes', 'De terceiros: sem "Investido + aportes"')
    print('ERROS', erros); b.close()
