"""Sensores no Home Assistant (Mais › Configurações › Integrações): desligados por padrão, sem falar de sensor nenhum; ligados,
listam só os que o app cria (o da IA com a IA ligada; o dos bens só com o InventarIA, que este teste não sobe). A nota do
sensor.gerencia_ia_hoje fica nesse quadro (não no Uso da IA), só com os sensores ligados, e some com a IA desligada."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sem, sim, ir_mais
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
    ir_mais(pg, 'config', 'integracoes', 1200)
    igual(pg.locator('#uso-ia').count(), 1, 'o quadro Uso da IA')
    sem(pg.inner_text('#uso-ia'), 'gerencia_ia_hoje', 'Uso da IA sem a explicação do sensor')
    tem(pg.inner_text('#sensores'), 'Desligado: nenhum sensor no Home Assistant.', 'sensores desligados por padrão')
    igual(pg.locator('#sensores .nota').count(), 0, 'desligados: sem a nota do sensor de IA')
    pg.locator('#sensores').screenshot(path=f'{SP}/shots/sensores.png')
    pg.click('#sensores [data-a="ajuste"][data-k="sensores"]'); pg.wait_for_timeout(800)
    igual(get('api/state')['ajustes'].get('sensores'), True, 'ligar os sensores fica salvo')
    txt = pg.inner_text('#sensores')
    tem(txt, 'Ligado: sensor.gerencia_patrimonio', 'ligados: lista os sensores')
    for s in ('_meu', '_terceiros', '_rendimento_mensal', '_saldo_caixa', '_entradas_mes', '_saidas_mes', '_ia_hoje'):
        tem(txt, s, f'ligados: {s}')
    sem(txt, '_bens', 'sem o InventarIA, sem o sensor dos bens')
    igual(pg.inner_text('#sensores .nota'), NOTA, 'a nota do sensor de IA fica em Sensores')
    pg.locator('#sensores').screenshot(path=f'{SP}/shots/sensores-ligados.png')
    pg.click('#ia [data-a="ajuste"][data-k="ia"]'); pg.wait_for_timeout(800)
    igual((pg.locator('#uso-ia').count(), pg.locator('#sensores .nota').count()), (0, 0), 'com a IA desligada: sem o Uso da IA e sem a nota do sensor de IA')
    sem(pg.inner_text('#sensores'), '_ia_hoje', 'com a IA desligada, sem o sensor da IA na lista')
    print('ERROS', erros); b.close()
