"""Data da última verificação das dicas: mesmo sem assinaturas (e sem dados), o app verifica no dia e mostra "Última
verificação: hoje às HH:MM"; o Conferir agora atualiza a data; e o status do Falar em Mais › Integrações."""
import re, sys, json, urllib.request
from datetime import date
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    # sem dados: dicas_estado marca a verificação do dia
    at1 = get('api/dicas').get('atualizado') or ''
    tem(at1, date.today().isoformat() + 'T', 'sem assinaturas: a verificação de hoje fica marcada')
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="mais-aba"][data-v="caixa"]'); pg.wait_for_timeout(1200)
    igual(pg.inner_text('#dicas .dica-quando'), f'Última verificação: hoje às {at1[11:16]}.', 'Mais › Caixa: a data e a hora da última verificação')
    pg.click('[data-a="dicas-conferir"]'); pg.wait_for_timeout(9000)
    at2 = get('api/dicas').get('atualizado') or ''
    sim(at2 >= at1 and at2.startswith(date.today().isoformat()), 'Conferir agora: verifica de novo', (at1, at2))
    igual(pg.inner_text('#dicas .dica-quando'), f'Última verificação: hoje às {at2[11:16]}.', 'depois de conferir: a hora da verificação nova')
    sim(pg.locator('[data-a="dicas-conferir"]:not([disabled])').count() == 1, 'o botão Conferir agora volta a funcionar')
    pg.locator('#dicas').scroll_into_view_if_needed(); pg.wait_for_timeout(200)
    pg.locator('#dicas').screenshot(path=f'{SP}/shots/dicas-quando.png')
    # Falar: texto do status
    pg.click('[data-a="mais-aba"][data-v="integracoes"]'); pg.wait_for_timeout(1200)
    t = [x for x in pg.locator('#integ-ia .status, .status').all_inner_texts() if x.startswith('Falar')]
    igual(t, ['Falar: pronto. A voz vira texto com “Fala simulada (teste)”; quem entende e separa os lançamentos é a IA usada pelo app. O microfone fica no alto de cada tela.'], 'o status do Falar')
    print('ERROS', erros); b.close()
