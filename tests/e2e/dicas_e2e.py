import sys, json, time, urllib.request
from playwright.sync_api import sync_playwright
SP=sys.argv[1]; erros=[]
def api(p):
    return json.loads(urllib.request.urlopen('http://localhost:8099/'+p).read())
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':396,'height':860}, device_scale_factor=2, color_scheme='dark', extra_http_headers={'X-Remote-User-Display-Name': 'Ana Souza'})
    pg.on('pageerror', lambda e: erros.append('PAGEERROR '+str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type=='error' else None)
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    for i in range(20):
        st=api('api/dicas')
        if not st['conferindo'] and st['assinaturas'] and all(a['status']!='pendente' for a in st['assinaturas']): break
        time.sleep(0.5)
    print('ASSINATURAS', [(a['descricao'], a['valor'], a['status'], a.get('economia_ano')) for a in st['assinaturas']])
    print('DICAS', [(d['id'], d['economia_ano'], d['preco_anual'], d['estimado']) for d in st['dicas']])
    pg.wait_for_timeout(7000)  # front faz polling
    pg.screenshot(path=f'{SP}/shots/e1-inicio.png', full_page=True)
    # mudar Nabu Casa para anual
    ids=[d['id'] for d in st['dicas']]
    nabu=[d for d in st['dicas'] if d['servico']=='nabucasa'][0]
    pg.click(f'[data-a="dica-anual"][data-v="{nabu["id"]}"]'); pg.wait_for_timeout(500)
    pg.fill('#da-valor', ''); pg.type('#da-valor', '35500'); pg.wait_for_timeout(200)
    print('ECO', pg.inner_text('#da-eco'))
    pg.screenshot(path=f'{SP}/shots/e2-anual.png')
    pg.click('[data-a="da-ok"]'); pg.wait_for_timeout(1500)
    d=api('api/state')
    rs=[r for r in d['recorrencias'] if 'Nabu' in r['descricao']]
    print('RECS NABU', [(r['id'], r.get('freq'), r['valor'], r['inicio'], r.get('fim'), r['dia']) for r in rs])
    st=api('api/dicas')
    print('DEPOIS', [(a['descricao'], a['status']) for a in st['assinaturas']], [d['id'] for d in st['dicas']])
    # dispensar spotify
    sp=[x for x in st['dicas'] if x['servico']=='spotify']
    if sp:
        pg.click(f'[data-a="dica-fora"][data-v="{sp[0]["id"]}"]'); pg.wait_for_timeout(1200)
        print('FORA', api('api/state')['ajustes'].get('dicas_fora'))
    pg.screenshot(path=f'{SP}/shots/e3-inicio-depois.png', full_page=True)
    # Mais
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(800)
    pg.click('.mais-abas [data-v="caixa"]'); pg.wait_for_timeout(800)
    el=pg.locator('#dicas'); el.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
    el.screenshot(path=f'{SP}/shots/e4-mais-dicas.png')
    pg.locator('#fixos').screenshot(path=f'{SP}/shots/e5-fixos.png')
    # form com Todo ano
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(400)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.type('#lf-valor', '150000'); pg.fill('#lf-desc', 'IPVA')
    pg.click('[data-a="lf-set"][data-k="repete"][data-v="anual"]'); pg.wait_for_timeout(300)
    pg.locator('.folha-corpo').evaluate('e => e.scrollTop = e.scrollHeight'); pg.wait_for_timeout(200)
    pg.screenshot(path=f'{SP}/shots/e6-form-anual.png')
    pg.click('[data-a="lf-salvar"]:not([data-mais])'); pg.wait_for_timeout(1200)
    d=api('api/state')
    print('IPVA', [(r.get('freq'), r['inicio'], r['dia'], r['valor']) for r in d['recorrencias'] if r['descricao']=='IPVA'])
    # fluxo
    pg.click('[data-a="cx-modo"][data-v="fluxo"]'); pg.wait_for_timeout(500)
    pg.click('[data-a="cx-periodo"][data-v="futuro"]'); pg.wait_for_timeout(500)
    pg.screenshot(path=f'{SP}/shots/e7-fluxo-futuro.png', full_page=True)
    print('ERROS', erros); b.close()
