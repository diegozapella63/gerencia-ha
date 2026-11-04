"""Falar pelo microfone do alto: ouvindo com o tempo, Pronto manda para a fala para texto e a IA, a conferência mostra o
que foi ouvido no alto, conta como Falar no Uso da IA, e Mais › Configurações › Integrações diz que o Falar está pronto."""
import re, sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, ir_mais
SP=sys.argv[1]; erros=[]
B='http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
with sync_playwright() as p:
    b=p.chromium.launch(args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'])
    ctx=b.new_context(viewport={'width':396,'height':860}, device_scale_factor=2, color_scheme='dark', permissions=['microphone'])
    pg=ctx.new_page()
    pg.on('pageerror', lambda e: erros.append('PAGEERROR '+str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type=='error' else None)
    pg.goto(B); pg.wait_for_timeout(1000)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(2000)
    igual(len([m for m in pg.locator('.mic-top[data-a="falar"]').all() if m.is_visible()]), 1, 'o microfone no alto da tela')
    pg.screenshot(path=f'{SP}/shots/v0-topo.png', clip={'x':0,'y':0,'width':396,'height':200})
    fala0 = get('api/ia/uso')['today'].get('kinds', {}).get('fala', 0)
    pg.click('.mic-top[data-a="falar"] >> visible=true'); pg.wait_for_timeout(2500)
    est = pg.inner_text('.voz-estado')
    sim(re.match(r'^Ouvindo… \d:\d\d$', est), 'ouvindo, com o tempo', est)
    pg.screenshot(path=f'{SP}/shots/v1-ouvindo.png')
    pg.click('[data-a="fala-ok"]'); pg.wait_for_timeout(3500)
    igual(pg.inner_text('.folha-cab h2'), 'Conferir lançamentos', 'Pronto: a IA lê o que foi falado')
    igual(pg.inner_text('.ouvido') if pg.locator('.ouvido').count() else '', '“Gastei 45 reais no mercado hoje no cartão e recebi 150 do João pelo Pix”', 'o que foi ouvido no alto')
    sim(pg.locator('.ia-item').count() > 0, 'com os lançamentos para conferir', pg.locator('.ia-item').count())
    igual(get('api/ia/uso')['today'].get('kinds', {}).get('fala', 0) - fala0, 1, 'conta como Falar no Uso da IA')
    pg.screenshot(path=f'{SP}/shots/v2-revisao.png')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    ir_mais(pg, 'config', 'integracoes', 1200)
    igual([t for t in pg.locator('#ia .status').all_inner_texts() if 'Falar' in t],
          ['Falar: pronto. A voz vira texto com “Fala simulada (teste)”; quem entende e separa os lançamentos é a IA usada pelo app. O microfone fica no alto de cada tela.'], 'Mais › Configurações › Integrações: Falar pronto, com a fala para texto usada')
    print('ERROS', erros); b.close()
