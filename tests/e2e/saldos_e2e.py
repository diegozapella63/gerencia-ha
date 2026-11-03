"""Atualizar saldos com IA (de uma pessoa de fora): conferir, aporte no existente e investimento novo dela."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
def post(p, c):
    r = urllib.request.Request(B + p, data=json.dumps(c).encode(), method='POST', headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    st = get('api/state'); bancos = {x['id']: x['nome'] for x in st['bancos']}
    terc = [i for i in st['investimentos'] if i.get('titular') == 'terceiros']
    print('terceiros:', [(i['nome'], bancos.get(i['banco']), i.get('terceiro'), i['valor']) for i in terc])
    alvo = terc[0]; pessoa = alvo['terceiro']; banco = bancos.get(alvo['banco'])
    texto = f"{banco}, valor atualizado, R$ {int(alvo['valor']) + 1500}\nSerasa, valor atualizado, R$ 600"
    # Novo investimento > Ler: textos de investimento
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    igual(pg.locator('.op[data-a="ia-saldos"]').count(), 1, 'Adicionar tem Atualizar saldos')
    pg.click('.op[data-a="novo-inv"]'); pg.wait_for_timeout(400)
    igual(pg.locator('.imp-saldos').count(), 1, 'o novo investimento oferece atualizar saldos')
    pg.click('[data-a="ia-de"][data-ini="texto"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Colar mensagem', 'ler um texto')
    tem(pg.get_attribute('#ia-txt', 'placeholder'), 'Ex.:', 'com exemplo de investimento')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    if pg.locator('.folha').count(): pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(400)
    # Carteira > Terceiros > pessoa
    pg.click('[data-a="filtro"][data-v="terc"]'); pg.wait_for_timeout(300)
    if pg.locator(f'[data-a="pessoa-f"][data-v="{pessoa}"]').count(): pg.click(f'[data-a="pessoa-f"][data-v="{pessoa}"]'); pg.wait_for_timeout(300)
    igual(pg.inner_text('.ia-saldos-btn'), f'Atualizar saldos de {pessoa} com IA', 'botão com o nome da pessoa')
    pg.click('.ia-saldos-btn'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), f'Atualizar saldos de {pessoa}', 'janela da pessoa')
    igual(pg.inner_text('[data-a="ias-pessoa"].on'), pessoa, 'a pessoa já marcada')
    pg.screenshot(path=f'{SP}/shots/saldos-entrada.png')
    pg.fill('#ia-txt', texto); pg.wait_for_timeout(100)
    pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2500)
    igual(pg.inner_text('.folha-cab h2'), 'Conferir os saldos', 'janela de conferir')
    tem(pg.inner_text('.ia-saldos-res') if pg.locator('.ia-saldos-res').count() else '', 'Aportes R$', 'resumo com os aportes')
    itens = pg.locator('.ia-item').all_inner_texts()
    igual(len(itens), 2, 'um item por saldo')
    tem(itens[0], alvo['nome'], 'o primeiro é o investimento que já existe')
    tem(itens[0], '+ R$', 'com a diferença')
    tem(itens[1], 'Serasa', 'o segundo é novo')
    tem(itens[1], 'R$ 600,00', 'com o valor')
    igual(pg.inner_text('[data-a="ia-salvar"]'), 'Atualizar 2', 'botão')
    pg.screenshot(path=f'{SP}/shots/saldos-conferir.png', full_page=False)
    # troca o segundo para um investimento existente e depois volta a novo
    pg.click('[data-a="ia-salvar"]'); pg.wait_for_timeout(1200)
    st2 = get('api/state')
    a2 = [i for i in st2['investimentos'] if i['id'] == alvo['id']][0]
    novo = [i for i in st2['investimentos'] if i['nome'] == 'Serasa']
    igual(a2['valor'], int(alvo['valor']) + 1500, 'o saldo novo no investimento que existia')
    igual([(n['titular'], n.get('terceiro'), n['valor']) for n in novo], [('terceiros', pessoa, 600)], 'o novo fica com a mesma pessoa')
    igual(get('api/ia/uso')['today'].get('kinds', {}).get('saldos'), 1, 'conta no uso da IA')
    print('ERROS', erros); b.close()
