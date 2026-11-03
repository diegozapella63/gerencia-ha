"""Apagar um fixo pela lixeira (aberto em Mais › Caixa › Fixos, que abre a próxima ocorrência): as três opções (só
aquele mês ou ano, parar a partir dali, apagar com o que ele já lançou); parar deixa o que já foi lançado e tira o fixo
da lista; apagar tudo leva os lançamentos dele."""
import sys, json, urllib.request
from datetime import date, timedelta
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, mes
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())
hoje = date.today()
d_anual = hoje - timedelta(days=6)    # recebido há poucos dias (como no print: 27/10, visto em 02/11)
d_mensal = hoje - timedelta(days=28)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, device_scale_factor=2, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    # recebimento todo ano, recebido
    pg.click('[data-a="lanc-novo"][data-v="receita"]'); pg.wait_for_timeout(400)
    pg.click('#lf-valor'); pg.keyboard.type('2400000')
    pg.fill('#lf-data', d_anual.isoformat()); pg.wait_for_timeout(300)
    pg.click('[data-a="lf-set"][data-k="repete"][data-v="anual"]'); pg.wait_for_timeout(200)
    pg.click('[data-a="lf-salvar"]:not([data-mais])'); pg.wait_for_timeout(800)
    d = get('api/state')
    igual([(r['descricao'], r.get('freq'), r['inicio'], r['dia'], r['valor']) for r in d['recorrencias']], [('Recebimento', 'anual', d_anual.isoformat()[:7], d_anual.day, 24000)], 'recebimento fixo todo ano criado')
    igual([(l['valor'], l['pago'], l['data']) for l in d['lancamentos']], [(24000, True, d_anual.isoformat())], 'o deste ano lançado e recebido')
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(300); pg.click('[data-a="mais-aba"][data-v="caixa"]'); pg.wait_for_timeout(400)
    igual(pg.locator('#fixos .banco-row').count(), 1, 'o fixo na lista de Fixos')
    pg.locator('#fixos .banco-row').first.click(); pg.wait_for_timeout(400)
    pg.click('[data-a="lf-excluir"]'); pg.wait_for_timeout(400)
    prox = d_anual.year + 1  # a próxima ocorrência de um fixo anual que já aconteceu este ano
    igual(pg.locator('[data-a="escolha"]').all_inner_texts(), [f'Só o de {prox}', f'Parar a partir de {MESES[d_anual.month - 1]} de {prox}', 'Apagar o fixo e o que ele já lançou (1)'], 'opções para apagar o fixo anual')
    pg.screenshot(path=f'{SP}/shots/fixo-apagar.png')
    pg.click('[data-a="escolha"] >> nth=1'); pg.wait_for_timeout(800)
    d = get('api/state')
    fim = mes(-1, date(prox, d_anual.month, 1))
    igual([r.get('fim') for r in d['recorrencias']], [fim], 'parar: o fixo termina no mês anterior')
    igual(pg.locator('#fixos .banco-row').count(), 0, 'parado, sai da lista de Fixos')
    igual(len(d['lancamentos']), 1, 'o que já foi lançado continua')
    # de novo: criar e apagar tudo
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(300); pg.click('.escolhas [data-a="lanc-novo"][data-v="receita"]'); pg.wait_for_timeout(400)
    pg.click('#lf-valor'); pg.keyboard.type('100000'); pg.fill('#lf-data', d_mensal.isoformat()); pg.wait_for_timeout(300)
    pg.click('[data-a="lf-set"][data-k="repete"][data-v="mensal"]'); pg.click('[data-a="lf-salvar"]:not([data-mais])'); pg.wait_for_timeout(800)
    d = get('api/state'); n0 = len(d['lancamentos'])
    igual(n0, 2, 'o fixo mensal lançou o primeiro mês')
    pg.click('#nav [data-v="mais"]'); pg.wait_for_timeout(300); pg.click('[data-a="mais-aba"][data-v="caixa"]'); pg.wait_for_timeout(400)
    igual(pg.locator('#fixos .banco-row').count(), 1, 'só o fixo mensal na lista')
    pg.locator('#fixos .banco-row').first.click(); pg.wait_for_timeout(400)
    pg.click('[data-a="lf-excluir"]'); pg.wait_for_timeout(400)
    seguinte = MESES[int(mes(1)[5:]) - 1]  # do Fixos abre o do mês que vem
    igual(pg.locator('[data-a="escolha"]').all_inner_texts(), [f'Só o de {seguinte}', f'Parar a partir de {seguinte}', 'Apagar o fixo e o que ele já lançou (1)'], 'opções para apagar o fixo mensal')
    pg.click('[data-a="escolha"] >> nth=2'); pg.wait_for_timeout(800)
    d = get('api/state')
    igual([(r.get('freq'), r.get('fim')) for r in d['recorrencias']], [('anual', fim)], 'apagar tudo: o fixo mensal sai (o anual parado fica)')
    igual(len(d['lancamentos']), n0 - 1, 'apagar tudo: o lançamento dele também sai')
    igual([l['valor'] for l in d['lancamentos']], [24000], 'fica só o recebimento anual')
    igual(pg.locator('#fixos .banco-row').count(), 0, 'nenhum fixo na lista')
    print('ERROS', erros); b.close()
