"""Categorias dos bens vêm do InventarIA: a criada lá (Ferramentas) aparece, a renomeada (Plantas → Jardim) vem com o
nome novo e a excluída (Pets) some, no tipo Bens e no Separar por categoria (mais Imóveis e Veículos); a nova perde 10% a.a."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'; INV = 'http://127.0.0.1:8098/'
def req(base, p, c=None, m='GET'):
    r = urllib.request.Request(base + p, data=json.dumps(c).encode() if c is not None else None, method=m, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
req(INV, 'api/cats', {'name': 'Ferramentas'}, 'POST')
req(INV, 'api/cats/plantas', {'name': 'Jardim'}, 'PUT')
req(INV, 'api/cats/pets', None, 'DELETE')
sala = req(INV, 'api/rooms', {'name': 'Sala'}, 'POST')['room']['id']
req(INV, 'api/items', {'room': sala, 'name': 'Televisão', 'cat': 'eletronicos', 'value': 3000}, 'POST')
todas = [(c['id'], c['nome']) for c in req(B, 'api/bens').get('todas', [])]
sim(('ferramentas', 'Ferramentas') in todas, 'a categoria criada no InventarIA chega', todas)
sim(('plantas', 'Jardim') in todas, 'a renomeada chega com o nome novo', todas)
igual([c for c in todas if c[0] == 'pets'], [], 'a excluída no InventarIA some')
# Imóveis e Veículos: os do InventarIA (1.31.0 ou mais novo, na ordem de lá) ou, se ele não tiver, no começo
nomes = [n for k, n in (('imoveis', 'Imóveis'), ('veiculos', 'Veículos')) if k not in dict(todas)] + [n for _, n in todas]
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="f-tipo"][data-v="bens"]'); pg.wait_for_timeout(300)
    igual(pg.locator('[data-k="categoria_bem"]').all_inner_texts(), nomes, 'tipo Bens: Imóveis, Veículos e as categorias do InventarIA')
    pg.click('[data-a="f-set"][data-k="categoria_bem"][data-v="ferramentas"]'); pg.wait_for_timeout(200)
    tem(pg.locator('.campo:has(.lbl:text-is("Categoria")) .ajuda').inner_text(), 'Perde 10% por ano.', 'categoria nova começa perdendo 10% ao ano')
    pg.click('[data-a="f-dividir"][data-v="1"]'); pg.wait_for_timeout(300)
    igual([x.split('\n')[0] for x in pg.locator('.bens-partes .bens-tx').all_inner_texts()], nomes, 'Separar por categoria: as mesmas categorias')
    pg.screenshot(path=f'{SP}/shots/cats-inv.png')
    print('ERROS', erros); b.close()
