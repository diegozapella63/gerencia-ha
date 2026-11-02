import sys, json, urllib.request
from playwright.sync_api import sync_playwright
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
    print('0 adicionar tem Atualizar saldos:', pg.locator('.op[data-a="ia-saldos"]').count())
    pg.click('.op[data-a="novo-inv"]'); pg.wait_for_timeout(400)
    print('  link no novo investimento:', pg.locator('.imp-saldos').count())
    pg.click('[data-a="ia-de"][data-ini="texto"]'); pg.wait_for_timeout(400)
    print('  ler do novo investimento:', pg.inner_text('.folha-cab h2'), '|', pg.get_attribute('#ia-txt', 'placeholder')[:50])
    pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    if pg.locator('.folha').count(): pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(400)
    # Carteira > Terceiros > pessoa
    pg.click('[data-a="filtro"][data-v="terc"]'); pg.wait_for_timeout(300)
    if pg.locator(f'[data-a="pessoa-f"][data-v="{pessoa}"]').count(): pg.click(f'[data-a="pessoa-f"][data-v="{pessoa}"]'); pg.wait_for_timeout(300)
    print('1 botão:', pg.inner_text('.ia-saldos-btn'))
    pg.click('.ia-saldos-btn'); pg.wait_for_timeout(400)
    print('2 janela:', pg.inner_text('.folha-cab h2'), '| dono marcado:', pg.inner_text('[data-a="ias-pessoa"].on'))
    pg.screenshot(path=f'{SP}/shots/saldos-entrada.png')
    pg.fill('#ia-txt', texto); pg.wait_for_timeout(100)
    pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2500)
    print('3 conferir:', pg.inner_text('.folha-cab h2'), '| resumo:', pg.inner_text('.ia-saldos-res').replace('\n', ' ') if pg.locator('.ia-saldos-res').count() else '-')
    for it in pg.locator('.ia-item').all(): print('   ', it.inner_text().replace('\n', ' | '))
    print('  botão:', pg.inner_text('[data-a="ia-salvar"]'))
    pg.screenshot(path=f'{SP}/shots/saldos-conferir.png', full_page=False)
    # troca o segundo para um investimento existente e depois volta a novo
    pg.click('[data-a="ia-salvar"]'); pg.wait_for_timeout(1200)
    st2 = get('api/state')
    a2 = [i for i in st2['investimentos'] if i['id'] == alvo['id']][0]
    novo = [i for i in st2['investimentos'] if i['nome'] == 'Serasa']
    print('4 salvou:', alvo['valor'], '->', a2['valor'], '| novo Serasa:', [(n['titular'], n.get('terceiro'), n['valor']) for n in novo], '| aviso', pg.locator('.toast').all_inner_texts())
    print('  uso:', get('api/ia/uso')['today'].get('kinds'))
    print('ERROS', erros); b.close()
