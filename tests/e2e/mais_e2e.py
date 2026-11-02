import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP=sys.argv[1]; erros=[]
B='http://localhost:8099/'
def st(): return json.loads(urllib.request.urlopen(B+'api/state').read())
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':396,'height':860}, device_scale_factor=2, color_scheme='dark', extra_http_headers={'X-Remote-User-Display-Name': 'Ana Souza'})
    pg.on('pageerror', lambda e: erros.append('PAGEERROR '+str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type=='error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    # uma leitura por IA para ter uso
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300); pg.click('.op[data-a="ia"]'); pg.wait_for_timeout(400)
    pg.fill('[data-ias="texto"]', 'gastei 50 no mercado'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2500)
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="backup"]') if pg.locator('[data-a="backup"]').count() else None
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(800)
    abas=pg.locator('.mais-abas button'); n=abas.count()
    print('abas:', [abas.nth(i).inner_text() for i in range(n)])
    for i in range(n):
        abas.nth(i).click(); pg.wait_for_timeout(900)
        nome=abas.nth(i).inner_text().strip()
        if nome=='Dados':
            pg.click('[data-a="backup"]'); pg.wait_for_timeout(900)
        h=pg.evaluate('document.documentElement.scrollHeight')
        pg.set_viewport_size({'width':396,'height':max(860,h)}); pg.wait_for_timeout(300)
        pg.screenshot(path=f'{SP}/shots/m{i}-{nome}.png')
        print(nome, '| títulos:', pg.locator('.mais-painel .mais-head h2').all_inner_texts(), '| status:', pg.inner_text('.sync').strip())
        pg.set_viewport_size({'width':396,'height':860})
    # desligar IA
    abas.nth(3).click(); pg.wait_for_timeout(600)
    pg.click('#ia [data-a="ajuste"][data-k="ia"]'); pg.wait_for_timeout(1000)
    print('IA ligada?', st()['ajustes'].get('ia'), '| uso card:', pg.locator('#uso-ia').count())
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(500)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300)
    print('Ler com IA no Adicionar (IA desligada):', pg.locator('.op[data-a="ia"]').is_visible())
    pg.click('.escolhas [data-a="lanc-novo"][data-v="despesa"]'); pg.wait_for_timeout(300)
    print('quadrinhos de IA na despesa (IA desligada):', pg.locator('.imp-tile').count())
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    r=urllib.request.Request(B+'api/ia/ler', data=json.dumps({'modo':'caixa','texto':'x'}).encode(), method='POST', headers={'Content-Type':'application/json'})
    try: urllib.request.urlopen(r); print('ia/ler: ok?!')
    except urllib.error.HTTPError as e: print('ia/ler bloqueado:', e.code, json.loads(e.read())['erro'])
    # Invest: busca sempre à mostra
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="inv-modo"][data-v="carteira"]'); pg.wait_for_timeout(300)
    print('busca visível:', pg.locator('#q').is_visible())
    pg.fill('#q','tesouro'); pg.wait_for_timeout(400)
    print('  resultados:', pg.locator('.inv').count(), '| limpar:', pg.locator('[data-a="busca-limpar"]').count())
    pg.screenshot(path=f'{SP}/shots/m-busca.png')
    print('ERROS', erros); b.close()
