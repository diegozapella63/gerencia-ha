"""Conta em cada linha ao conferir o que a IA leu: categoria e conta lado a lado e alinhadas, a conta do banco que a IA
viu já sugerida (com débito ou crédito quando a conta tem cartão), trocar a conta de uma linha e salvar com a conta certa."""
import sys, json, urllib.request
from datetime import date
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1000)
    st0 = get('api/state'); n0 = len(st0['lancamentos'])
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300)
    pg.click('.op[data-a="ia"]'); pg.wait_for_timeout(300)
    pg.fill('#ia-txt', 'fatura do mês'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2600)
    n = pg.locator('.ia-item-x.dois').count()
    igual(n, 4, 'uma linha com categoria e conta por lançamento lido')
    larg = lambda s: sorted({round(pg.locator(s).nth(i).bounding_box()['width']) for i in range(n)})
    lc, lk = larg('[data-iai="categoria"]'), larg('[data-iai="contasel"]')
    igual(len(lc), 1, 'as categorias com a mesma largura em todas as linhas')
    igual(lk, lc, 'a conta com a mesma largura da categoria, lado a lado')
    contas = [pg.locator('[data-iai="contasel"]').nth(i).evaluate('e => e.options[e.selectedIndex].text') for i in range(n)]
    igual(contas[:2], ['Nubank · Ana · crédito', 'Nubank · Ana · crédito'], 'a conta do banco que a IA viu (Nubank), no crédito')
    igual(contas, ['Nubank · Ana · crédito', 'Nubank · Ana · crédito', 'Nubank · Ana · crédito', 'Nubank · Ana'], 'contas sugeridas (recebimento sem débito ou crédito)')
    esperadas = ['Sem conta']
    for bc in st0['bancos']:
        for c in bc['contas']:
            nome = f"{bc['nome']} · {c['pessoa']}"
            esperadas += [nome + ' · débito', nome + ' · crédito'] if c.get('cartao') else [nome]
    igual(pg.locator('[data-iai="contasel"]').first.evaluate('e => [...e.options].map(o => o.text)'), esperadas, 'opções: cada conta, com débito e crédito quando tem cartão')
    # a 1ª linha (iFood, no cartão) muda para uma conta sem cartão
    opts = pg.locator('[data-iai="contasel"]').first.evaluate('e => [...e.options].map(o => o.value)')
    outra = [o for o in opts if o and '|c' not in o][-1]
    pg.select_option('[data-iai="contasel"] >> nth=0', outra); pg.wait_for_timeout(300)
    igual(pg.locator('.ia-item').first.inner_text().split('\n')[1], date.today().strftime('%d/%m'), 'sem cartão, sai da fatura: a data da compra, já paga')
    igual(pg.locator('[data-a="iac-conta"].on').count(), 0, 'com contas diferentes, o Lançar todos em fica sem marcar')
    pg.screenshot(path=f'{SP}/shots/conta-linha.png')
    pg.click('[data-a="ia-salvar"]'); pg.wait_for_timeout(1200)
    novos = get('api/state')['lancamentos'][n0:]
    igual([(l['descricao'], l.get('conta'), l.get('cartao')) for l in novos],
          [('iFood', outra.split('|')[0], False), ('Posto Shell', 'k-nu-ana', True)] + [('Magazine Luiza', 'k-nu-ana', True)] * 5 + [('Pix do João', 'k-nu-ana', False)],
          'salvos com a conta de cada linha (a parcelada vira as parcelas que faltam)')
    igual(outra.split('|')[0], 'k-sicredi-beto', 'a outra conta é a do Sicredi (sem cartão)')
    print('ERROS', erros); b.close()
