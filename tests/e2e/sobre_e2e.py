"""Mais › Sobre (1.27.0), a última linha do menu, como no CronologIA 1.51.0: CorrerIA Code (desenvolvimento de
softwares) e por que o nome, os sete apps da família, cada um com a sua linha e o GitHub (este marcado com a versão),
e Meu GitHub. Capturas em 390 px escuro, 320 px claro e no computador; um toque abre o GitHub noutra aba e o app fica
em Sobre; o Voltar e o "‹ Mais" voltam ao menu."""
import os, re, sys
from playwright.sync_api import sync_playwright
from _confere import igual, sim
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
GH = 'https://github.com/diegozapella63'
APPS = [('CronologIA', 'cronologia-ha'), ('ResolvIA', 'resolvia-ha'), ('GerencIA', 'gerencia-ha'), ('InventarIA', 'inventario-ha'),
        ('EconomIA', 'economia-ha'), ('MemorIA', 'memoria-ha'), ('CorrerIA', 'correria-ha')]
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
with open(f'{RAIZ}/gerencia/config.yaml', encoding='utf-8') as f:
    VERSAO = re.search(r'^version:\s*"?([\d.]+)', f.read(), re.M).group(1)
junta = lambda t: ' '.join((t or '').split())

with sync_playwright() as p:
    b = p.chromium.launch()
    for i, (tema, w) in enumerate((('dark', 390), ('light', 320), ('dark', 1280))):
        ctx = b.new_context(viewport={'width': w, 'height': 844 if w < 1000 else 900}, device_scale_factor=2, color_scheme=tema, has_touch=w < 1000,
                            extra_http_headers={'X-Remote-User-Display-Name': 'Ana Souza'})
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
        pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
        pg.goto(B); pg.wait_for_timeout(800)
        if i == 0:
            pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
        nome = f'{tema} {w}px'
        pg.click('#lado [data-v="mais"]' if w >= 1000 else '#nav [data-v="mais"]'); pg.wait_for_timeout(500)
        ultima = pg.locator('#app .menu-row').last
        igual((ultima.get_attribute('data-v'), junta(ultima.inner_text())), ('sobre', 'Sobre CorrerIA Code, os apps e o GitHub.'), f'{nome}: Sobre é a última linha do menu')
        ultima.click(); pg.wait_for_timeout(600)
        igual((pg.inner_text('#app .cab h1'), pg.inner_text('#app .uplink').strip()), ('Sobre', 'Mais'), f'{nome}: Sobre, com ‹ Mais')
        topo = junta(pg.inner_text('.sobre-topo'))
        sim(topo.startswith('CorrerIA Code') and 'desenvolvimento de softwares' in topo.lower() and topo.endswith('Feito na correria, rodado pela IA.'),
            f'{nome}: CorrerIA Code, desenvolvimento de softwares e o lema', topo)
        por = junta(pg.inner_text('#por-que'))
        sim(por.startswith('Por que CorrerIA?') and 'programador sem tempo' in por and 'reclamo dos botões tortos.' in por, f'{nome}: Por que CorrerIA?', por[:80])
        linhas = pg.locator('#os-apps .sb-app')
        igual([linhas.nth(k).get_attribute('href') for k in range(linhas.count())], [f'{GH}/{r}' for _, r in APPS], f'{nome}: os sete apps, cada um no seu GitHub')
        nomes = [junta(t) for t in linhas.locator('b').all_inner_texts()]
        igual([n.split(' Este app')[0] for n in nomes], [n for n, _ in APPS], f'{nome}: os nomes')
        txt = linhas.locator('.mb > span').all_inner_texts()
        sim(len(txt) == 7 and all(0 < len(t) <= 55 for t in txt), f'{nome}: uma linha curta cada', txt)
        aqui = pg.locator('#os-apps .sb-app.aqui')
        igual((aqui.count(), aqui.get_attribute('href'), junta(aqui.locator('.sb-aqui').inner_text())), (1, f'{GH}/gerencia-ha', f'Este app · v{VERSAO}'),
              f'{nome}: este app marcado, com a v{VERSAO}')
        alvos = pg.locator('.sb-pagina a').evaluate_all("xs => xs.map(x => x.target + ' ' + x.rel)")
        igual(alvos, ['_blank noopener'] * 8, f'{nome}: os 8 links abrem fora')
        gh = pg.locator('a.sb-github')
        igual((gh.get_attribute('href'), gh.inner_text().strip()), (GH, 'Meu GitHub'), f'{nome}: Meu GitHub')
        passa = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        fora = pg.evaluate("""() => { const p = document.querySelector('.sb-pagina').getBoundingClientRect();
          return [...document.querySelectorAll('.sb-pagina .sobre-topo, .sb-pagina .card, .sb-pagina .sb-app, .sb-pagina .sb-github')]
            .filter(x => { const r = x.getBoundingClientRect(); return r.left < p.left - 1 || r.right > p.right + 1; }).length; }""")
        igual((passa <= 0, fora), (True, 0), f'{nome}: nada passa da borda')
        lg, lc = gh.bounding_box()['width'], pg.locator('#os-apps').bounding_box()['width']
        sim(abs(lg - lc) <= 1, f'{nome}: Meu GitHub da largura dos cartões', f'{lg:.0f} / {lc:.0f}')
        a, f = pg.locator('.sb-oque').evaluate("x => [x.getBoundingClientRect().height, parseFloat(getComputedStyle(x).fontSize)]")
        sim(a < f * 2, f'{nome}: desenvolvimento de softwares numa linha só', (a, f))
        # a captura sem o aviso de Carregar exemplo e sem o mouse em cima de uma linha
        pg.wait_for_function("!document.getElementById('toast') || !document.getElementById('toast').classList.contains('on')", timeout=8000)
        pg.mouse.move(0, 0); pg.wait_for_timeout(500)
        pg.screenshot(path=f'{SP}/shots/sobre-{tema}-{w}.png')
        gh.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
        pg.screenshot(path=f'{SP}/shots/sobre-{tema}-{w}-fim.png')
        if w == 390:
            ctx.route('https://github.com/**', lambda r: r.fulfill(body='<title>GitHub</title>ok', content_type='text/html'))
            with ctx.expect_page() as nova:
                linhas.nth(1).click()
            np = nova.value; np.wait_for_load_state()
            igual(np.url, f'{GH}/resolvia-ha', f'{nome}: um toque abre o GitHub do app noutra aba')
            np.close()
            igual(pg.locator('.sobre-topo').count(), 1, f'{nome}: o app fica em Sobre')
            pg.go_back(); pg.wait_for_timeout(500)
            igual((pg.inner_text('#app .cab h1'), pg.locator('#app .menu-list').count()), ('Mais', 1), f'{nome}: o Voltar volta ao menu')
            pg.click('#app .menu-row[data-v="sobre"]'); pg.wait_for_timeout(400)
            pg.click('#app .uplink'); pg.wait_for_timeout(400)
            igual((pg.inner_text('#app .cab h1'), pg.evaluate('!!(history.state && history.state.tela)')), ('Mais', False), f'{nome}: ‹ Mais volta ao menu')
        ctx.close()
    print('ERROS', erros); b.close()
