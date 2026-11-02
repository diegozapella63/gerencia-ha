import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    v = get('api/voz/status'); print('1 api:', v['nome'], '| opções', [o['id'] for o in v['opcoes']], '| sel', repr(v['selecionada']))
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="mais-aba"][data-v="integracoes"]'); pg.wait_for_timeout(1500)
    print('2 opções na tela:', pg.locator('#voz-motor option').all_inner_texts())
    print('  status:', [x for x in pg.locator('#ia .status').all_inner_texts() if x.startswith('Falar')])
    pg.select_option('#voz-motor', 'stt.outra_simulada'); pg.wait_for_timeout(1500)
    v = get('api/voz/status'); print('3 escolhida:', get('api/state')['ajustes'].get('voz_motor'), '| api nome', v['nome'], '| sel', v['selecionada'])
    print('  status:', [x for x in pg.locator('#ia .status').all_inner_texts() if x.startswith('Falar')], '| selecionado', pg.eval_on_selector('#voz-motor', 'e => e.value'))
    el = pg.locator('#ia'); el.scroll_into_view_if_needed(); el.screenshot(path=f'{SP}/shots/fala-motor.png')
    # falar usa a escolhida
    pcm = b'\x00\x01' * 16000
    r = urllib.request.Request(B + 'api/voz', data=pcm, method='POST', headers={'Content-Type': 'application/octet-stream'})
    print('4 transcrição com:', json.loads(urllib.request.urlopen(r).read()).get('nome'))
    pg.select_option('#voz-motor', ''); pg.wait_for_timeout(1500)
    print('5 volta ao padrão:', repr(get('api/state')['ajustes'].get('voz_motor')), get('api/voz/status')['nome'])
    print('ERROS', erros); b.close()
