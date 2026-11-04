"""Bem de terceiros (tipo Bens, sem o InventarIA): o formulário só pede nome, valor e categoria; salva com a taxa da
categoria, fica fora do patrimônio, muda com a tabela de Mais › Invest e aparece na Evolução e na Divisão de terceiros."""
import sys, json, urllib.request
from datetime import date
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, perto, valores, ir_mais
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
perde_mes = lambda v, t: v * (1 - (1 - t / 100) ** (1 / 12))
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1200)
    pat0 = pg.get_attribute('.placar-num', 'aria-label')
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="f-set"][data-k="titular"][data-v="terceiros"]'); pg.wait_for_timeout(200)
    pg.fill('[data-f="terceiro"]', 'Mãe')
    pg.click('[data-a="f-tipo"][data-v="bens"]'); pg.wait_for_timeout(300)
    vis = lambda t: pg.locator(f'.folha .campo:has(.lbl:text-is("{t}"))').first.is_visible() if pg.locator(f'.folha .campo:has(.lbl:text-is("{t}"))').count() else False
    igual({t: vis(t) for t in ('Banco', 'Rendimento', 'Categoria', 'Liquidez')}, {'Banco': False, 'Rendimento': False, 'Categoria': True, 'Liquidez': False}, 'tipo Bens: só a categoria (sem banco, rendimento nem liquidez)')
    pg.click('[data-a="f-set"][data-k="categoria_bem"][data-v="veiculos"]'); pg.wait_for_timeout(200)
    igual(pg.locator('.campo:has(.lbl:text-is("Categoria")) .ajuda').inner_text(), 'Perde 15% por ano. As taxas ficam em Mais › Invest.', 'Veículos: perde 15% por ano')
    pg.fill('#f-nome', 'Carro da mãe'); pg.locator('#f-valor').click(); pg.keyboard.type('6000000')
    pg.screenshot(path=f'{SP}/shots/bens-terc-form.png')
    pg.click('[data-a="f-salvar"]:not([data-mais])'); pg.wait_for_timeout(900)
    inv = [i for i in get('api/state')['investimentos'] if i['nome'] == 'Carro da mãe'][0]
    igual((inv['tipo'], inv['indexador'], inv['taxa'], inv.get('categoria_bem'), inv['banco'], inv['titular'], inv['terceiro'], inv['valor']),
          ('bens', 'deprecia', 15, 'veiculos', '', 'terceiros', 'Mãe', 60000), 'salvo como bem de terceiros, perdendo 15% a.a.')
    card = pg.locator('.inv:has-text("Carro da mãe")').inner_text()
    igual(card.split('\n')[:5], ['Carro da mãe', 'R$ 60.000,00', 'Bens · Veículos', 'perde 15% a.a.', 'De Mãe'], 'cartão: valor, categoria, perda e dono')
    perto(valores(card)[1], round(perde_mes(60000, 15), 2), 'cartão: perde por mês', tol=0.02)
    tem(card, 'valor de ' + date.today().strftime('%d/%m'), 'cartão: valor de hoje')
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(400)
    igual(pg.get_attribute('.placar-num', 'aria-label'), pat0, 'o patrimônio não muda (bens de terceiros ficam fora)')
    ir_mais(pg, 'invest', espera=500)
    tem(pg.inner_text('#perda-bens'), 'Veículos\nR$ 60.000', 'Mais › Invest: Veículos na tabela de perda, com o valor')
    igual(pg.input_value('[data-bens-taxa="veiculos"]'), '15', 'tabela: veículos 15%')
    pg.fill('[data-bens-taxa="veiculos"]', '12'); pg.press('[data-bens-taxa="veiculos"]', 'Tab'); pg.wait_for_timeout(1000)
    st = get('api/state')
    inv = [i for i in st['investimentos'] if i['nome'] == 'Carro da mãe'][0]
    igual((inv['taxa'], st['ajustes'].get('bens_taxas')), (12, {'veiculos': 12}), 'mudar a taxa da categoria muda o carro')
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('[data-a="inv-modo"][data-v="evolucao"] >> nth=-1'); pg.wait_for_timeout(400)
    pg.click('[data-a="g"][data-k="gEscopo"][data-v="terc"]'); pg.wait_for_timeout(500)
    anos = int(pg.inner_text('.chips.c5 .chip.on').split()[0])
    duo = pg.inner_text('.stat-duo')
    hoje_terc = valores(duo)[0]
    perto(valores(duo.split('bens −')[-1])[0] if 'bens −' in duo else None, round(60000 - 60000 * 0.88 ** anos), f'Evolução de terceiros: o carro perde 12% a.a. em {anos} anos', tol=0.6)
    pg.click('[data-a="inv-modo"][data-v="divisao"] >> nth=-1'); pg.wait_for_timeout(400)
    pg.click('[data-a="g"][data-k="gAgrup"][data-v="tipo"]'); pg.wait_for_timeout(400)
    comps = pg.locator('.comp').all_inner_texts()
    igual([x.split('\n')[0] for x in comps], ['Bens', 'Poupança', 'CDB', 'Caixinha'], 'Divisão de terceiros por tipo, Bens primeiro')
    tem(comps[0], f'1 investimento · perde ≈ R$ {round(perde_mes(60000, 12))}/mês', 'Divisão: o bem perde por mês, com a taxa nova')
    sim(abs(sum(valores(x)[-1] for x in comps) - hoje_terc) <= len(comps), 'a Divisão soma o Hoje da Evolução', (hoje_terc, comps))
    perto(float(comps[0].split('\n')[-1].rstrip('%').replace(',', '.')), round(60000 / hoje_terc * 100, 1), 'Divisão: a porcentagem do bem', tol=0.051)
    print('ERROS', erros); b.close()
