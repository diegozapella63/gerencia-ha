"""Leitura por IA sem escolher o tipo: a IA separa lançamentos e investimentos; da tela de investimentos, só investimentos."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, device_scale_factor=2, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300); pg.click('.op[data-a="ia"]'); pg.wait_for_timeout(400)
    igual(pg.locator('.folha .seg').count(), 0, 'não pede para escolher o tipo')
    igual(pg.inner_text('[data-a="ia-arq"]'), 'Fatura, print, foto ou PDF', 'botão do arquivo')
    pg.fill('#ia-txt', 'paguei 180 da luz ontem, tenho que pagar o boleto do IPVA e apliquei 15 mil no CDB do Banco Sol a 112% do CDI')
    pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2600)
    igual(pg.inner_text('.folha-cab h2'), 'Conferir o que a IA leu', 'janela de conferir')
    tem(pg.inner_text('.folha-corpo p'), 'Achei 1 lançamento e 1 investimento', 'diz o que achou')
    igual(pg.locator('.ia-sec').all_inner_texts(), ['Lançamentos', 'Investimentos'], 'separa em duas partes')
    igual(pg.inner_text('[data-a="ia-salvar"]'), 'Salvar 2', 'salva os dois')
    pg.screenshot(path=f'{SP}/shots/ia-auto-conferir.png', full_page=True)
    n0 = len(get('api/state')['lancamentos']); i0 = len(get('api/state')['investimentos'])
    pg.click('[data-a="ia-salvar"]'); pg.wait_for_timeout(1000)
    d = get('api/state')
    igual(len(d['lancamentos']) - n0, 1, 'um lançamento novo')
    igual(len(d['investimentos']) - i0, 0, 'o aporte vai no CDB que já existe (não cria outro)')
    igual(pg.inner_text('.cab h1'), 'Caixa', 'depois de salvar, mostra o caixa')
    # só investimento
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300); pg.click('[data-a="ia-de"][data-ini="texto"]'); pg.wait_for_timeout(400)
    pg.fill('#ia-txt', 'saldo da LCA do Banco Mar e do CDB do Banco Sol'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2600)
    igual(pg.inner_text('.folha-cab h2'), 'Conferir investimentos', 'da tela de investimentos: só investimentos')
    igual(pg.locator('.ia-sec').count(), 0, 'sem a parte de lançamentos')
    igual(pg.inner_text('[data-a="ia-salvar"]'), 'Salvar 2', 'os dois investimentos')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # Falar, sem escolher
    igual(get('api/ia/uso')['today'].get('kinds', {}).get('ler'), 2, 'as duas leituras contam no uso da IA')
    print('ERROS', erros); b.close()
