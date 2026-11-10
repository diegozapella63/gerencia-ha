"""Fala para texto à escolha (Mais › Configurações › Integrações › IA do Home Assistant): a lista com Padrão do Home Assistant e as falas para
texto do HA, o status do Falar com o nome da escolhida, a transcrição usando a escolhida e a volta ao padrão."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, ir_mais
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
STATUS = 'Falar: pronto. A voz vira texto com “{}”; quem entende e separa os lançamentos é a IA usada pelo app. O microfone fica no alto de cada tela.'
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    falar = lambda: [x for x in pg.locator('#ia .status').all_inner_texts() if x.startswith('Falar')]
    v = get('api/voz/status')
    igual((v['nome'], [o['id'] for o in v['opcoes']], v['selecionada']), ('Fala simulada (teste)', ['stt.simulada', 'stt.outra_simulada'], ''), 'api: as falas para texto do HA, no padrão')
    pg.goto(B); pg.wait_for_timeout(800)
    ir_mais(pg, 'config', 'integracoes', 1500)
    igual(pg.locator('#voz-motor option').all_inner_texts(), ['Padrão do Home Assistant', 'Fala simulada (teste)', 'Outra fala simulada (teste)'], 'lista Fala para texto: o padrão e cada uma pelo nome')
    igual(falar(), [STATUS.format('Fala simulada (teste)')], 'status do Falar com a do padrão')
    pg.select_option('#voz-motor', 'stt.outra_simulada'); pg.wait_for_timeout(1500)
    v = get('api/voz/status')
    igual((get('api/state')['ajustes'].get('voz_motor'), v['nome'], v['selecionada']), ('stt.outra_simulada', 'Outra fala simulada (teste)', 'stt.outra_simulada'), 'a escolhida fica salva')
    igual(falar(), [STATUS.format('Outra fala simulada (teste)')], 'status do Falar com a escolhida')
    igual(pg.eval_on_selector('#voz-motor', 'e => e.value'), 'stt.outra_simulada', 'a lista mostra a escolhida')
    el = pg.locator('#ia'); el.scroll_into_view_if_needed(); el.screenshot(path=f'{SP}/shots/fala-motor.png')
    # falar usa a escolhida
    pcm = b'\x00\x01' * 16000
    r = urllib.request.Request(B + 'api/voz', data=pcm, method='POST', headers={'Content-Type': 'application/octet-stream'})
    igual(json.loads(urllib.request.urlopen(r).read()).get('nome'), 'Outra fala simulada (teste)', 'a transcrição usa a escolhida')
    pg.select_option('#voz-motor', ''); pg.wait_for_timeout(1500)
    igual((get('api/state')['ajustes'].get('voz_motor'), get('api/voz/status')['nome']), ('', 'Fala simulada (teste)'), 'Padrão do Home Assistant: volta à do padrão')
    print('ERROS', erros); b.close()
