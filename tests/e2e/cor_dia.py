"""Cor do dia (Mais › Aparência), com o servidor de verdade: vem ligada, a cor do app é a do dia (as cores do app em
ordem, sem o Grafite, pela data de hoje) no app, no ícone e no relatório; tocar numa cor desliga e fica com ela (também
depois de recarregar); ligar de novo volta para a do dia. Capturas no escuro e no claro."""
import sys, json, urllib.request
from datetime import date
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def st(): return json.loads(urllib.request.urlopen(B + 'api/state').read())
# as cores do app sem as neutras, na ordem do seletor; uma por dia, contando os dias desde 01/01/1970
CORES = [('Vermelho', '#FF5A4F'), ('Coral', '#FF8A65'), ('Laranja', '#FFA23E'), ('Ouro', '#F2C14E'), ('Verde', '#8BD45F'), ('Menta', '#4ED3A6'),
         ('Turquesa', '#3CCBDA'), ('Azul', '#56AEFF'), ('Índigo', '#8F9BFF'), ('Lilás', '#B99BFF'), ('Rosa', '#FF77A9')]
n = (date.today() - date(1970, 1, 1)).days
NOME, COR = CORES[n % len(CORES)]
OUTRO, OUTRA = CORES[(n + 1) % len(CORES)]  # a de amanhã: uma cor diferente da de hoje
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 390, 'height': 844}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    if pg.locator('[data-a="carregar-exemplo"]').count(): pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1200)
    acento = lambda: pg.evaluate("document.documentElement.style.getPropertyValue('--accent')")
    marcada = lambda: pg.locator('#cor .tsw[aria-checked="true"]').all_inner_texts()
    chave = lambda: pg.get_attribute('#cor [data-a="ajuste"][data-k="cor_dia"]', 'aria-checked')
    igual(st()['ajustes'].get('cor_dia'), True, 'o servidor começa com a Cor do dia ligada')
    igual(acento(), COR, f'Início: a cor do dia ({NOME})')
    pg.screenshot(path=f'{SP}/shots/cor-dia-inicio.png')
    relatorio = urllib.request.urlopen(B + 'relatorio').read().decode()
    tem(relatorio, f':root{{--a:{COR}}}', 'o relatório na cor do dia')
    # Mais › Aparência
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(400)
    pg.click('.mais-abas [data-v="aparencia"]'); pg.wait_for_timeout(500)
    igual(' '.join(pg.inner_text('#cor .linha-sw').split()), 'Cor do dia Muda a cor do app todo dia.', 'a chave com a explicação curta')
    igual(chave(), 'true', 'Cor do dia ligada')
    igual(marcada(), [NOME], 'a cor do dia é a marcada')
    caixa_sw = pg.locator('#cor .linha-sw .sw').bounding_box()
    caixa_card = pg.locator('#cor').bounding_box()
    sim(caixa_sw and caixa_sw['x'] + caixa_sw['width'] <= caixa_card['x'] + caixa_card['width'], 'a chave cabe no quadro', (caixa_sw, caixa_card))
    pg.locator('#cor').screenshot(path=f'{SP}/shots/cor-dia-ligada.png')
    # tocar numa cor: desliga e fica com ela
    pg.click(f'#cor [data-a="cor"][data-v="{OUTRA}"]'); pg.wait_for_timeout(700)
    a = st()['ajustes']
    igual((a.get('cor'), a.get('cor_dia')), (OUTRA, False), f'tocar em {OUTRO}: guarda a cor e desliga a Cor do dia')
    igual((chave(), acento(), marcada()), ('false', OUTRA, [OUTRO]), 'a chave desliga e a cor escolhida vale')
    pg.locator('#cor').screenshot(path=f'{SP}/shots/cor-dia-escolhida.png')
    tem(urllib.request.urlopen(B + 'relatorio').read().decode(), f':root{{--a:{OUTRA}}}', 'o relatório na cor escolhida')
    pg.reload(); pg.wait_for_timeout(900)
    igual(acento(), OUTRA, 'recarregando, continua a escolhida')
    # ligar de novo: volta para a do dia
    pg.click('#cor [data-a="ajuste"][data-k="cor_dia"]'); pg.wait_for_timeout(700)
    igual(st()['ajustes'].get('cor_dia'), True, 'ligar de novo grava')
    igual((chave(), acento(), marcada()), ('true', COR, [NOME]), 'e volta para a cor do dia')
    # no tema claro
    pg.click('#tema [data-a="tema"][data-v="claro"]'); pg.wait_for_timeout(500)
    pg.locator('#cor').screenshot(path=f'{SP}/shots/cor-dia-claro.png')
    pg.click('#tema [data-a="tema"][data-v="auto"]'); pg.wait_for_timeout(400)
    print('ERROS', erros); b.close()
