"""Patrimônio só o meu: o placar do Início soma só os seus investimentos (o dinheiro de terceiros fica de fora), com
quantos são, em quantos bancos e o rendimento por mês só deles, igual ao destaque Rende por mês."""
import os, sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, valores
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'gerencia', 'app'))
import calc
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    st = get('api/state')
    meus = [i for i in st['investimentos'] if i.get('titular') != 'terceiros']
    t, tm = calc.totais(st), calc.totais(dict(st, investimentos=meus))
    pat = valores(pg.get_attribute('.placar-num', 'aria-label'))[0]
    sim(abs(pat - t['meu']) <= 1, 'placar: o patrimônio é só o meu (calculado como no servidor)', (pat, t['meu']))
    sim(abs(pat - t['total']) > 100, 'placar: sem o dinheiro de terceiros', (pat, t['total'], t['terceiros']))
    cols = pg.locator('.placar-cols > div').all_inner_texts()
    igual([c.split('\n')[0].upper() for c in cols], ['INVESTIMENTOS', 'BANCOS', 'POR MÊS'], 'placar: investimentos, bancos e por mês')
    igual([c.split('\n')[1] for c in cols[:2]], [str(len(meus)), str(len({i['banco'] for i in meus if i.get('banco')}))], 'placar: quantos são os meus e em quantos bancos')
    mes_placar = valores(cols[2])[0]
    sim(abs(mes_placar - tm['rende_mes']) <= 1, 'placar: o rendimento por mês só dos meus', (mes_placar, tm['rende_mes']))
    rende = pg.locator('.hl-row').first.inner_text().split('\n')
    igual((rende[0], rende[-1]), ('Rende por mês', 'antes do IR'), 'destaque: Rende por mês, antes do IR')
    tem(rende[1], 'Média de ', 'destaque: com a média ao ano')
    igual(valores(rende[2])[0] if len(rende) > 2 and valores(rende[2]) else None, mes_placar, 'destaque: o mesmo rendimento do placar')
    pg.locator('.placar').screenshot(path=f'{SP}/shots/pat-meu.png')
    print('ERROS', erros); b.close()
