"""Mais é um menu (capturas do menu e de cada tela, no escuro e no claro): as linhas na ordem, com Configurações por
último; cada linha abre a sua tela com "‹ Mais" no alto e Mais marcado embaixo; o Voltar e o "‹ Mais" voltam ao menu;
Configurações em abas (as seções de cada uma, o backup na pasta share); a chave Usar IA (desligada some tudo o que
usa IA e o servidor recusa a leitura); nada passa da largura em 320 px; e o Buscar sempre à mostra na Carteira."""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
SP=sys.argv[1]; erros=[]
B='http://localhost:8099/'
def st(): return json.loads(urllib.request.urlopen(B+'api/state').read())
def get(p): return json.loads(urllib.request.urlopen(B+p).read())
LINHAS = ['Bancos', 'Caixa', 'Invest', 'Relatório de patrimônio', 'Configurações', 'Sobre']
TELAS = {  # tela: (título, as seções)
    'bancos': ('Bancos', []),
    'caixa': ('Caixa', ['Fixos', 'Categorias', 'Dicas de economia']),
    'invest': ('Invest', ['Índices de mercado']),
}
ABAS = {
    'Integrações': ['Contas no CronologIA', 'Bens no InventarIA', 'Leitura por IA', 'Uso da IA', 'Sensores no Home Assistant'],
    'Dados': ['Exportar', 'Backup na pasta share', 'Importar', 'Versões anteriores', 'Onde ficam os dados', 'Começar do zero'],
    'Aparência': ['Tema', 'Cor do app'],
    'Opções': ['Início', 'Fluxo de caixa', 'Investimentos'],
}
def cheia(pg, nome):
    h=pg.evaluate('document.documentElement.scrollHeight')
    pg.set_viewport_size({'width':396,'height':max(860,h)}); pg.wait_for_timeout(300)
    pg.screenshot(path=f'{SP}/shots/{nome}.png')
    pg.set_viewport_size({'width':396,'height':860}); pg.wait_for_timeout(100)
def no_menu(pg):
    return (pg.inner_text('.cab h1'), pg.locator('#app .menu-list').count(), pg.evaluate('!!(history.state && history.state.tela)'))
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
    # o menu
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(800)
    igual(pg.locator('#app .menu-row b').all_inner_texts(), LINHAS, 'Mais: as linhas do menu, Configurações e Sobre por último')
    igual(pg.locator('#nav [aria-current="page"]').get_attribute('data-v'), 'mais', 'Mais marcado embaixo')
    igual((pg.locator('#app .uplink').count(), pg.locator('#app .mais-abas').count()), (0, 0), 'no menu, sem ‹ Mais e sem abas')
    cheia(pg, 'm0-menu-escuro')
    # cada linha abre a sua tela
    for i, (tela, (titulo, secoes)) in enumerate(TELAS.items(), 1):
        pg.click(f'#app .menu-row[data-v="{tela}"]'); pg.wait_for_timeout(800)
        igual((pg.inner_text('.cab h1'), pg.inner_text('#app .uplink').strip()), (titulo, 'Mais'), f'{titulo}: o título e ‹ Mais no alto')
        igual(pg.locator('#nav [aria-current="page"]').get_attribute('data-v'), 'mais', f'{titulo}: Mais continua marcado')
        igual(pg.locator('.mais-painel .mais-head h2').all_inner_texts(), secoes, f'Mais › {titulo}: as seções')
        sync = pg.inner_text('.sync').strip()
        if tela == 'bancos':
            contas = [c for x in d0['bancos'] for c in x['contas']]
            igual(sync, f"{len(d0['bancos'])} bancos · {len(contas)} contas · {sum(1 for c in contas if c.get('cartao'))} cartões", 'Bancos: quantos bancos, contas e cartões')
            igual(pg.locator('#bancos .banco-row').count(), len(d0['bancos']), 'Bancos: um por linha')
        elif tela == 'invest':
            igual(sync, 'Sem conexão com o Banco Central', 'Invest: sem o Banco Central (nos testes)')
        cheia(pg, f'm{i}-{titulo}')
        if i % 2:
            pg.go_back(); pg.wait_for_timeout(500)
            igual(no_menu(pg), ('Mais', 1, False), f'{titulo}: o Voltar volta ao menu')
        else:
            pg.click('#app .uplink'); pg.wait_for_timeout(500)
            igual(no_menu(pg), ('Mais', 1, False), f'{titulo}: ‹ Mais volta ao menu')
    # Configurações em abas
    pg.click('#app .menu-row[data-v="config"]'); pg.wait_for_timeout(800)
    igual(pg.inner_text('.cab h1'), 'Configurações', 'Configurações: o título')
    abas=pg.locator('.mais-abas button'); n=abas.count()
    igual([abas.nth(i).inner_text().strip() for i in range(n)], list(ABAS), 'Configurações: as abas')
    for i in range(n):
        abas.nth(i).click(); pg.wait_for_timeout(900)
        nome=abas.nth(i).inner_text().strip()
        if nome=='Dados':
            pg.click('[data-a="backup"]'); pg.wait_for_timeout(900)
            igual(pg.inner_text('#versoes .painel-lead'), 'Uma cópia a cada 10 minutos de uso e antes de importar ou restaurar. Ficam as 3 mais recentes.', 'Dados: quando as versões anteriores são guardadas')
            sim(len(get('api/backups')) >= 1, 'Dados: Criar backup grava o .zip na pasta share', get('api/backups'))
        cheia(pg, f'm{4+i}-Config-{nome}')
        igual(pg.locator('.mais-painel .mais-head h2').all_inner_texts(), ABAS.get(nome), f'Mais › Configurações › {nome}: as seções')
        if nome == 'Integrações':
            igual(pg.inner_text('.sync').strip(), 'IA do Home Assistant pronta', 'Integrações: IA pronta')
    # tema claro: o menu e Configurações
    pg.emulate_media(color_scheme='light'); pg.wait_for_timeout(300)
    abas.nth(0).click(); pg.wait_for_timeout(600)
    pg.evaluate('window.scrollTo(0, 0)'); pg.wait_for_timeout(200)
    pg.screenshot(path=f'{SP}/shots/m8-config-claro.png')
    pg.click('#app .uplink'); pg.wait_for_timeout(500)
    cheia(pg, 'm9-menu-claro')
    pg.emulate_media(color_scheme='dark'); pg.wait_for_timeout(200)
    # 320 px: nada passa da largura
    pg.set_viewport_size({'width':320,'height':700}); pg.wait_for_timeout(300)
    larg = {'menu': pg.evaluate('document.documentElement.scrollWidth')}
    for tela in ['bancos', 'caixa', 'invest', 'config', 'sobre']:
        pg.click(f'#app .menu-row[data-v="{tela}"]'); pg.wait_for_timeout(500)
        larg[tela] = pg.evaluate('document.documentElement.scrollWidth')
        pg.click('#app .uplink'); pg.wait_for_timeout(400)
    igual(larg, {k: 320 for k in larg}, '320 px: o menu e as telas cabem na largura')
    pg.set_viewport_size({'width':396,'height':860}); pg.wait_for_timeout(200)
    # desligar IA
    pg.click('#app .menu-row[data-v="config"]'); pg.wait_for_timeout(500)
    pg.click('.mais-abas [data-v="integracoes"]'); pg.wait_for_timeout(600)
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
    except urllib.error.HTTPError as e: igual((e.code, json.loads(e.read())['erro']), (400, 'A IA está desligada. Para usar, ligue em Mais › Configurações › Integrações.'), 'desligada: o servidor recusa a leitura por IA')
    # Invest: busca sempre à mostra
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="inv-modo"][data-v="carteira"]'); pg.wait_for_timeout(300)
    igual(pg.locator('#q').is_visible(), True, 'Carteira: a busca à mostra')
    pg.fill('#q','tesouro'); pg.wait_for_timeout(400)
    igual(sorted(pg.locator('.inv .inv-nome').all_inner_texts()), sorted(i['nome'] for i in d0['investimentos'] if 'tesouro' in i['nome'].lower()), 'busca: os Tesouros')
    igual(pg.locator('[data-a="busca-limpar"]').count(), 1, 'com o botão de limpar')
    pg.screenshot(path=f'{SP}/shots/m-busca.png')
    print('ERROS', erros); b.close()
