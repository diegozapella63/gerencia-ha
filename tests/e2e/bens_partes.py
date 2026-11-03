"""Bem de terceiros separado por categoria: as partes (Imóveis, Veículos, Móveis) somam o total, cada uma com a taxa da
sua categoria (a do bem é a média ponderada); a tabela de Mais › Invest muda a taxa das partes (negativa valoriza),
a Evolução de terceiros mostra a valorização e, ao reabrir, as partes voltam."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, perto, valores
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
PARTES = {'imoveis': 500000, 'veiculos': 60000, 'moveis': 20000}
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1200)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="f-set"][data-k="titular"][data-v="terceiros"]'); pg.wait_for_timeout(200)
    pg.fill('[data-f="terceiro"]', 'Mãe')
    pg.click('[data-a="f-tipo"][data-v="bens"]'); pg.wait_for_timeout(300)
    cats = pg.locator('[data-k="categoria_bem"]').all_inner_texts()
    igual(cats[:2], ['Imóveis', 'Veículos'], 'categorias: Imóveis e Veículos primeiro')
    sim({'Eletrônicos', 'Móveis', 'Outros'} <= set(cats) and cats[-1] == 'Outros', 'categorias de costume (sem o InventarIA), Outros por último', cats)
    pg.click('[data-a="f-dividir"][data-v="1"]'); pg.wait_for_timeout(300)
    igual(pg.locator('[data-fparte]').count(), len(cats), 'separar: um campo por categoria')
    sim(pg.get_attribute('#f-valor', 'readonly') is not None, 'separado, o total não se digita')
    for k, v in PARTES.items():
        pg.locator(f'[data-fparte="{k}"]').click(); pg.keyboard.type(str(v * 100))
    pg.wait_for_timeout(200)
    tem(pg.inner_text('#partes-soma'), 'Total: R$ 580.000,00.', 'a soma das partes')
    igual(pg.input_value('#f-valor'), '580.000,00', 'o total é a soma')
    pg.fill('#f-nome', 'Bens da mãe')
    pg.screenshot(path=f'{SP}/shots/bens-partes.png', full_page=False)
    pg.click('[data-a="f-salvar"]:not([data-mais])'); pg.wait_for_timeout(900)
    inv = [i for i in get('api/state')['investimentos'] if i['nome'] == 'Bens da mãe'][0]
    media = round((500000 * 0 + 60000 * 15 + 20000 * 10) / 580000, 2)
    igual((inv['valor'], inv['taxa'], inv['categoria_bem'], inv['titular'], inv['terceiro']), (580000, media, 'varias', 'terceiros', 'Mãe'), 'salvo com o total e a taxa média ponderada')
    igual([(x['categoria'], x['valor'], x['taxa']) for x in inv['partes']], [('imoveis', 500000, 0), ('veiculos', 60000, 15), ('moveis', 20000, 10)], 'cada parte com a taxa da categoria')
    card = pg.locator('.inv:has-text("Bens da mãe")').inner_text()
    igual(card.split('\n')[:5], ['Bens da mãe', 'R$ 580.000,00', 'Bens · 3 categorias', 'perde 1,9% a.a.', 'De Mãe'], 'cartão: total, 3 categorias, perda média e dono')
    # o "perde ≈ por mês" do cartão soma a perda de cada parte, na taxa dela (como o valor de hoje e a Evolução)
    perto(valores(card)[1], round(60000 * (1 - 0.85 ** (1 / 12)) + 20000 * (1 - 0.9 ** (1 / 12)), 2), 'cartão: perde por mês, somando as partes', tol=0.02)
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="mais-aba"][data-v="invest"]'); pg.wait_for_timeout(400)
    tab = pg.inner_text('#perda-bens')
    tem(tab, 'Perda de valor dos bens', 'Mais › Invest: a tabela de perda')
    for nome, v in (('Imóveis', 'R$ 500.000'), ('Veículos', 'R$ 60.000'), ('Móveis', 'R$ 20.000')):
        tem(tab, f'{nome}\n{v}', f'tabela: {nome} com o valor que tem')
    igual([pg.input_value(f'[data-bens-taxa="{k}"]') for k in PARTES], ['0', '15', '10'], 'tabela: as taxas de costume (imóveis 0%)')
    pg.fill('[data-bens-taxa="imoveis"]', '-4'); pg.press('[data-bens-taxa="imoveis"]', 'Tab'); pg.wait_for_timeout(900)
    inv = [i for i in get('api/state')['investimentos'] if i['nome'] == 'Bens da mãe'][0]
    igual([(x['categoria'], x['taxa']) for x in inv['partes']], [('imoveis', -4), ('veiculos', 15), ('moveis', 10)], 'imóveis −4%: a parte de imóveis muda')
    igual(inv['taxa'], round((500000 * -4 + 60000 * 15 + 20000 * 10) / 580000, 2), 'e a taxa média do bem acompanha')
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="evolucao"] >> nth=-1'); pg.wait_for_timeout(400)
    pg.click('[data-a="g"][data-k="gEscopo"][data-v="terc"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="g"][data-k="gAnos"][data-v="10"]'); pg.wait_for_timeout(400)
    duo = pg.inner_text('.stat-duo')
    em10 = 500000 * 1.04 ** 10 + 60000 * 0.85 ** 10 + 20000 * 0.9 ** 10
    tem(duo, 'bens +R$', 'Evolução de terceiros: os bens valorizam no total')
    perto(valores(duo.split('bens +')[-1])[0] if 'bens +' in duo else None, round(em10 - 580000), 'cada parte com a sua taxa em 10 anos', tol=1)
    # reabrir: as partes voltam
    pg.click('[data-a="inv-modo"][data-v="carteira"] >> nth=-1'); pg.wait_for_timeout(300)
    pg.locator('.inv:has-text("Bens da mãe")').click(); pg.wait_for_timeout(400)
    igual([pg.input_value(f'[data-fparte="{k}"]') for k in PARTES], ['500.000,00', '60.000,00', '20.000,00'], 'reaberto: as partes voltam')
    print('ERROS', erros); b.close()
