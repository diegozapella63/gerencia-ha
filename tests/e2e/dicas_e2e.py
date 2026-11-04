"""Dicas de economia de ponta a ponta: as assinaturas do exemplo conferidas na página oficial (Spotify em reais, Nabu
Casa em dólar, estimada), Mudar para anual (a economia real na janela; o fixo mensal para e entra um anual), Agora não
(guardado nos ajustes), o quadro em Mais › Caixa e um fixo Todo ano pelo formulário (IPVA)."""
import sys, json, time, urllib.request
from datetime import date
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, perto, valores, mes, ir_mais
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
SP=sys.argv[1]; erros=[]
def api(p):
    return json.loads(urllib.request.urlopen('http://localhost:8099/'+p).read())
hoje = date.today()
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
    ass = {a['descricao']: a for a in st['assinaturas']}
    igual(sorted(ass), ['Nabu Casa', 'Spotify'], 'acha as assinaturas do exemplo nos fixos')
    igual({k: (a['valor'], a['status']) for k, a in ass.items()}, {'Spotify': (23.9, 'ok'), 'Nabu Casa': (34.9, 'ok')}, 'as duas conferidas na página oficial')
    dicas = {d['id']: d for d in st['dicas']}
    igual(sorted(dicas), ['anual:r:r-musica', 'anual:r:r-nabu'], 'uma dica por assinatura')
    for a in st['assinaturas']:
        perto(a.get('economia_ano'), round(12 * a['valor'] - (a.get('preco_anual') or 0), 2), f"{a['descricao']}: economia = 12 mensalidades − o anual")
    igual(sorted(d['economia_ano'] for d in st['dicas']), sorted(a.get('economia_ano') for a in st['assinaturas']), 'cada dica com a economia da assinatura')
    igual(dicas['anual:r:r-musica']['preco_anual'], 239.0, 'Spotify: o anual da página (R$ 239)')
    igual((dicas['anual:r:r-musica']['estimado'], dicas['anual:r:r-nabu']['estimado']), (False, True), 'em dólar (Nabu Casa) é estimado; em reais, não')
    pg.wait_for_timeout(7000)  # front faz polling
    pg.screenshot(path=f'{SP}/shots/e1-inicio.png', full_page=True)
    # mudar Nabu Casa para anual
    nabu=dicas['anual:r:r-nabu']
    pg.click(f'[data-a="dica-anual"][data-v="{nabu["id"]}"]'); pg.wait_for_timeout(500)
    igual(pg.inner_text('.folha-cab h2'), 'Nabu Casa no plano anual', 'janela de mudar para anual')
    dia = 9
    prim = date(hoje.year, hoje.month, dia) if dia > hoje.day else date.fromisoformat(mes(1) + f'-{dia:02d}')
    igual(pg.input_value('#da-data'), prim.isoformat(), 'a primeira cobrança anual é a próxima no dia do fixo')
    pg.fill('#da-valor', ''); pg.type('#da-valor', '35500'); pg.wait_for_timeout(200)
    eco = pg.inner_text('#da-eco')
    real, desc, rende = valores(eco)[:3]
    perto(desc, round(12 * 34.9 - 355, 2), 'o desconto: 12 mensalidades − o anual digitado')
    perto(real, round(desc - rende, 2), 'a economia real: desconto − o que o dinheiro renderia')
    tem(eco, 'já com IR', 'diz que o rendimento é já com IR')
    pg.screenshot(path=f'{SP}/shots/e2-anual.png')
    pg.click('[data-a="da-ok"]'); pg.wait_for_timeout(1500)
    d=api('api/state')
    rs=[r for r in d['recorrencias'] if 'Nabu' in r['descricao']]
    igual([(r.get('freq'), r['valor'], r['inicio'], r.get('fim'), r['dia']) for r in rs],
          [(None, 34.9, mes(-6), mes(-1, prim), 9), ('anual', 355, prim.isoformat()[:7], None, 9)], 'o fixo mensal para e entra um anual')
    st=api('api/dicas')
    igual({a['descricao']: a['status'] for a in st['assinaturas']}, {'Spotify': 'ok', 'Nabu Casa': 'ja_anual'}, 'Nabu Casa fica como já anual')
    igual([x['id'] for x in st['dicas']], ['anual:r:r-musica'], 'sobra só a dica do Spotify')
    # dispensar spotify
    sp=[x for x in st['dicas'] if x['servico']=='spotify']
    sim(sp, 'a dica do Spotify continua')
    if sp:
        pg.click(f'[data-a="dica-fora"][data-v="{sp[0]["id"]}"]'); pg.wait_for_timeout(1200)
        igual(api('api/state')['ajustes'].get('dicas_fora'), ['anual:r:r-musica'], 'Agora não: a dica fica guardada como dispensada')
        igual(pg.locator('[data-a="dica-anual"]').count(), 0, 'no Início, sem dicas de plano anual')
    pg.screenshot(path=f'{SP}/shots/e3-inicio-depois.png', full_page=True)
    # Mais
    ir_mais(pg, 'caixa', espera=800)
    el=pg.locator('#dicas'); el.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
    tem(el.inner_text(), 'Mostrar dispensadas (1)', 'Mais › Caixa: mostrar a dispensada')
    tem(el.inner_text(), 'Última verificação: hoje às', 'Mais › Caixa: a data da última verificação')
    el.screenshot(path=f'{SP}/shots/e4-mais-dicas.png')
    tem(pg.inner_text('#fixos'), f'Todo ano, 9 de {MESES[prim.month - 1]}', 'Fixos: o Nabu Casa anual')
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
    igual([(r.get('freq'), r['inicio'], r['dia'], r['valor']) for r in d['recorrencias'] if r['descricao']=='IPVA'], [('anual', mes(), hoje.day, 1500)], 'IPVA fixo todo ano, a partir de hoje')
    # fluxo
    pg.click('[data-a="cx-modo"][data-v="fluxo"]'); pg.wait_for_timeout(500)
    pg.click('[data-a="cx-periodo"][data-v="futuro"]'); pg.wait_for_timeout(500)
    igual((pg.inner_text('.chips.c4 .chip.on'), pg.locator('#ch-fluxo .pt-net').count()), ('12 à frente', 12), 'Fluxo: 12 meses à frente')
    pg.screenshot(path=f'{SP}/shots/e7-fluxo-futuro.png', full_page=True)
    print('ERROS', erros); b.close()
