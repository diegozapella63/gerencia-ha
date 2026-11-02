import sys
from playwright.sync_api import sync_playwright
SP=sys.argv[1]; erros=[]
with sync_playwright() as p:
    b=p.chromium.launch(args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'])
    ctx=b.new_context(viewport={'width':396,'height':860}, device_scale_factor=2, color_scheme='dark', permissions=['microphone'])
    pg=ctx.new_page()
    pg.on('pageerror', lambda e: erros.append('PAGEERROR '+str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type=='error' else None)
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(1000)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(2000)
    print('mic no topo:', pg.locator('.mic-top').count())
    pg.screenshot(path=f'{SP}/shots/v0-topo.png', clip={'x':0,'y':0,'width':396,'height':200})
    pg.click('.mic-top'); pg.wait_for_timeout(2500)
    print('estado:', pg.inner_text('.voz-estado'))
    pg.screenshot(path=f'{SP}/shots/v1-ouvindo.png')
    pg.click('[data-a="fala-ok"]'); pg.wait_for_timeout(3500)
    print('título:', pg.inner_text('.folha-cab h2'), '| ouvido:', pg.inner_text('.ouvido') if pg.locator('.ouvido').count() else '-')
    pg.screenshot(path=f'{SP}/shots/v2-revisao.png')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(500)
    pg.click('.mais-abas [data-v="integracoes"]'); pg.wait_for_timeout(1200)
    print('status falar:', [t for t in pg.locator('#ia .status').all_inner_texts() if 'Falar' in t])
    print('ERROS', erros); b.close()
