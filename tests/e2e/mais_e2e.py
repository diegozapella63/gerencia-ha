"""Mais em abas (capturas de cada uma): as seções de cada aba, o backup na pasta share, a chave Usar IA (desligada some
tudo o que usa IA e o servidor recusa a leitura) e o Buscar sempre à mostra na Carteira."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
SP=sys.argv[1]; erros=[]
B='http://localhost:8099/'
def st(): return json.loads(urllib.request.urlopen(B+'api/state').read())
def get(p): return json.loads(urllib.request.urlopen(B+p).read())
TITULOS = {
    'Bancos': ['Bancos e contas'],
    'Caixa': ['Fixos', 'Categorias', 'Dicas de economia'],
    'Invest': ['Índices de mercado'],
    'Integrações': ['Contas no CronologIA', 'Bens no InventarIA', 'Leitura por IA', 'Uso da IA', 'Sensores no Home Assistant'],
    'Dados': ['Exportar', 'Backup na pasta share', 'Importar', 'Versões anteriores', 'Onde ficam os dados', 'Começar do zero'],
    'Aparência': ['Tema', 'Cor do app'],
    'Opções': ['Início', 'Fluxo de caixa', 'Investimentos'],
}
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':396,'height':860}, device_scale_factor=2, color_scheme='dark', extra_http_headers={'X-Remote-User-Display-Name': 'Ana Souza'})
    pg.on('pageerror', lambda e: erros.append('PAGEERROR '+str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type=='error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    d0 = st()
    # uma leitura por IA para ter uso
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300); pg.click('.op[data-a="ia"]'); pg.wait_for_timeout(400)
    pg.fill('[data-ias="texto"]', 'gastei 50 no mercado'); pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2500)
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="backup"]') if pg.locator('[data-a="backup"]').count() else None
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(800)
    abas=pg.locator('.mais-abas button'); n=abas.count()
    igual([abas.nth(i).inner_text().strip() for i in range(n)], list(TITULOS), 'Mais: as abas')
    for i in range(n):
        abas.nth(i).click(); pg.wait_for_timeout(900)
        nome=abas.nth(i).inner_text().strip()
        if nome=='Dados':
            pg.click('[data-a="backup"]'); pg.wait_for_timeout(900)
        h=pg.evaluate('document.documentElement.scrollHeight')
        pg.set_viewport_size({'width':396,'height':max(860,h)}); pg.wait_for_timeout(300)
        pg.screenshot(path=f'{SP}/shots/m{i}-{nome}.png')
        igual(pg.locator('.mais-painel .mais-head h2').all_inner_texts(), TITULOS.get(nome), f'Mais › {nome}: as seções')
        sync = pg.inner_text('.sync').strip()
        if nome == 'Bancos':
            contas = [c for x in d0['bancos'] for c in x['contas']]
            igual(sync, f"{len(d0['bancos'])} bancos · {len(contas)} contas · {sum(1 for c in contas if c.get('cartao'))} cartões", 'Bancos: quantos bancos, contas e cartões')
        elif nome == 'Invest':
            igual(sync, 'Sem conexão com o Banco Central', 'Invest: sem o Banco Central (nos testes)')
        elif nome == 'Integrações':
            igual(sync, 'IA do Home Assistant pronta', 'Integrações: IA pronta')
        elif nome == 'Dados':
            sim(len(get('api/backups')) >= 1, 'Dados: Criar backup grava o .zip na pasta share', get('api/backups'))
        pg.set_viewport_size({'width':396,'height':860})
    # desligar IA
    abas.nth(3).click(); pg.wait_for_timeout(600)
    sim(pg.locator('#uso-ia').count() == 1, 'com a IA ligada, o Uso da IA aparece')
    pg.click('#ia [data-a="ajuste"][data-k="ia"]'); pg.wait_for_timeout(1000)
    igual(st()['ajustes'].get('ia'), False, 'Usar IA desligado e salvo')
    igual(pg.locator('#uso-ia').count(), 0, 'desligada: sem o Uso da IA')
    pg.click('#nav [data-v="inicio"]'); pg.wait_for_timeout(500)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300)
    igual(pg.locator('.op[data-a="ia"]').is_visible() if pg.locator('.op[data-a="ia"]').count() else False, False, 'desligada: sem Ler com IA no Adicionar')
    pg.click('.escolhas [data-a="lanc-novo"][data-v="despesa"]'); pg.wait_for_timeout(300)
    igual(pg.locator('.imp-tile').count(), 0, 'desligada: sem os quadrinhos de IA na Nova despesa')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    r=urllib.request.Request(B+'api/ia/ler', data=json.dumps({'modo':'caixa','texto':'x'}).encode(), method='POST', headers={'Content-Type':'application/json'})
    try: urllib.request.urlopen(r); igual('aceitou', 'recusou', 'desligada: o servidor recusa a leitura por IA')
    except urllib.error.HTTPError as e: igual((e.code, json.loads(e.read())['erro']), (400, 'A IA está desligada. Para usar, ligue em Mais › Integrações.'), 'desligada: o servidor recusa a leitura por IA')
    # Invest: busca sempre à mostra
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="inv-modo"][data-v="carteira"]'); pg.wait_for_timeout(300)
    igual(pg.locator('#q').is_visible(), True, 'Carteira: a busca à mostra')
    pg.fill('#q','tesouro'); pg.wait_for_timeout(400)
    igual(sorted(pg.locator('.inv .inv-nome').all_inner_texts()), sorted(i['nome'] for i in d0['investimentos'] if 'tesouro' in i['nome'].lower()), 'busca: os Tesouros')
    igual(pg.locator('[data-a="busca-limpar"]').count(), 1, 'com o botão de limpar')
    pg.screenshot(path=f'{SP}/shots/m-busca.png')
    print('ERROS', erros); b.close()
