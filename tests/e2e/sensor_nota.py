"""Sensores no Home Assistant (Mais › Integrações): desligados por padrão; ligados, listam os sensores; a nota do
sensor.gerencia_ia_hoje fica nesse quadro (não no Uso da IA) e some com a IA desligada."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sem, sim
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
NOTA = 'sensor.gerencia_ia_hoje: chamadas de IA de hoje, com erros, cota e tokens.'
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="mais-aba"][data-v="integracoes"]'); pg.wait_for_timeout(1200)
    igual(pg.locator('#uso-ia').count(), 1, 'o quadro Uso da IA')
    sem(pg.inner_text('#uso-ia'), 'gerencia_ia_hoje', 'Uso da IA sem a explicação do sensor')
    tem(pg.inner_text('#sensores'), 'Desligado: nenhum sensor no Home Assistant.', 'sensores desligados por padrão')
    igual(pg.inner_text('#sensores .nota'), NOTA, 'a nota do sensor de IA fica em Sensores')
    pg.locator('#sensores').screenshot(path=f'{SP}/shots/sensores.png')
    pg.click('#sensores [data-a="ajuste"][data-k="sensores"]'); pg.wait_for_timeout(800)
    igual(get('api/state')['ajustes'].get('sensores'), True, 'ligar os sensores fica salvo')
    txt = pg.inner_text('#sensores')
    tem(txt, 'Ligado: sensor.gerencia_patrimonio', 'ligados: lista os sensores')
    for s in ('_meu', '_terceiros', '_rendimento_mensal', '_saldo_caixa', '_entradas_mes', '_saidas_mes', '_ia_hoje', '_bens'):
        tem(txt, s, f'ligados: {s}')
    pg.locator('#sensores').screenshot(path=f'{SP}/shots/sensores-ligados.png')
    pg.click('#ia [data-a="ajuste"][data-k="ia"]'); pg.wait_for_timeout(800)
    igual((pg.locator('#uso-ia').count(), pg.locator('#sensores .nota').count()), (0, 0), 'com a IA desligada: sem o Uso da IA e sem a nota do sensor de IA')
    print('ERROS', erros); b.close()
