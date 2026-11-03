"""Salário bruto com impostos na fonte e despesa ligada: a lista mostra os descontos e o líquido; confirmar o salário de
outro valor recalcula os impostos e dá baixa no plano de saúde junto; o formulário do plano mostra a ligação; Ler recibo
com IA preenche o bruto, os impostos em % e as despesas ligadas e confere com o líquido; o CSV traz os descontos."""
import os, sys, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, perto, valores, valores_s, mes
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'gerencia', 'app'))
import calc
SP=sys.argv[1]; erros=[]
B='http://localhost:8099/'
def st(): return json.loads(urllib.request.urlopen(B+'api/state').read())
INSS, TAXA, PLANO = 7, 4.5, 698.46  # descontos do salário do exemplo
r2 = lambda v: round(v + 1e-9, 2)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':396,'height':860}, device_scale_factor=2, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR '+str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type=='error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(500)
    lin=pg.locator('.lanc:has-text("Salário")').first
    bruto = valores(lin.locator('.lanc-d b').inner_text())[0]
    tog=pg.locator('.desc-tog').first
    desc = r2(r2(bruto * INSS / 100) + r2(bruto * TAXA / 100) + PLANO)
    igual(tog.inner_text().split('\n'), ['3 descontos · líquido ' + calc.fmt_brl(bruto - desc), '− ' + calc.fmt_brl(desc)], 'salário na lista: 3 descontos e o líquido')
    tog.click(); pg.wait_for_timeout(300)
    itens = [t.split('\n') for t in pg.locator('.desc-itens .lanc').all_inner_texts()]
    igual([(x[1], x[2], valores(x[3])[0]) for x in itens],
          [('INSS', 'Impostos e taxas · 7% do bruto · na fonte', r2(bruto * INSS / 100)), ('Taxa administrativa', 'Impostos e taxas · 4,5% do bruto · na fonte', r2(bruto * TAXA / 100)), ('Plano de saúde', 'Saúde · fixo · baixa junto', PLANO)],
          'os descontos: impostos em % do bruto e o plano ligado')
    lin.screenshot(path=f'{SP}/shots/s0-linha.png')
    box=lin.bounding_box()
    pg.screenshot(path=f'{SP}/shots/s1-lista.png', clip={'x':0,'y':max(0,box['y']-60),'width':396,'height':420})
    # próximo mês: Recebi no salário
    pg.click('[data-a="cx-mes"][data-v="1"]'); pg.wait_for_timeout(400)
    sal=pg.locator('.lanc:has-text("Salário")').first
    igual(sal.inner_text().split('\n')[1:], ['Salário', 'Salário · Banco Coral · Ana · fixo', '+ R$ 11.800,00', 'A receber'], 'mês que vem: o salário com o bruto padrão, a receber')
    sal.locator('[data-a="lanc-pagar"]').click(); pg.wait_for_timeout(500)
    igual(pg.inner_text('.folha-cab h2'), 'Confirmar recebimento', 'o círculo abre Confirmar recebimento')
    igual(pg.locator('[data-a="lf-pago"][data-v="1"].on').count(), 1, 'já como recebido')
    pg.fill('#lf-valor',''); pg.type('#lf-valor','1250000'); pg.wait_for_timeout(300)
    d125 = r2(875 + 562.5 + PLANO)
    igual(pg.inner_text('#lf-desc-res').split('\n')[:7], ['Bruto', 'R$ 12.500,00', 'Descontos', '− ' + calc.fmt_brl(d125), 'Líquido', calc.fmt_brl(12500 - d125), 'cai na conta'], 'outro bruto: os impostos acompanham')
    pg.locator('.desc-sec').screenshot(path=f'{SP}/shots/s2-impostos.png')
    pg.click('[data-a="lf-salvar"][data-v="este"]'); pg.wait_for_timeout(1200)
    d=st(); prox = mes(1)
    sl=[l for l in d['lancamentos'] if l.get('recorrencia')=='r-sal' and l.get('competencia')==prox]
    pl=[l for l in d['lancamentos'] if l.get('recorrencia')=='r-plano' and l.get('competencia')==prox]
    igual([(x['valor'], x['pago'], x['data']) for x in sl], [(12500, True, f'{prox}-05')], 'Só este mês: o salário recebido com o valor do mês')
    igual([(x['valor'], x['pago'], x['data'], x.get('vinculo')) for x in pl], [(PLANO, True, f'{prox}-05', 'r-sal')], 'o plano de saúde fica pago junto, no mesmo dia')
    igual([r['valor'] for r in d['recorrencias'] if r['id']=='r-sal'], [11800], 'o bruto padrão continua o mesmo')
    # plano: formulário
    pg.locator('.desc-tog').first.click(); pg.wait_for_timeout(300)
    pg.locator('.desc-itens .lanc:has-text("Plano de saúde")').first.click(); pg.wait_for_timeout(500)
    igual((pg.locator('#lf-vinc').input_value(), pg.inner_text('.vinc-st').strip()), ('r-sal', 'Baixa com Salário'), 'o formulário do plano: descontado do salário, baixa com ele')
    pg.screenshot(path=f'{SP}/shots/s3-plano.png')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # novo recebimento fixo lendo recibo
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('[data-a="lf-tipo"][data-v="receita"]'); pg.wait_for_timeout(300)
    pg.fill('#lf-desc','Cooperativa')
    pg.click('[data-a="lf-set"][data-k="repete"][data-v="mensal"]'); pg.wait_for_timeout(200)
    pg.click('[data-a="lf-desc-abrir"]'); pg.wait_for_timeout(300)
    with pg.expect_file_chooser() as fc: pg.click('[data-a="lf-ler-recibo"]')
    fc.value.set_files(f'{SP}/recibo-teste.pdf'); pg.wait_for_timeout(2500)
    # recibo de teste: créditos R$ 13.050,00; INSS 840,00 e taxa 587,25 (impostos); plano 320,00 e coparticipação 85,40; líquido 11.217,35
    igual(pg.input_value('#lf-valor'), '13.050,00', 'recibo: o bruto é a soma dos créditos')
    igual([pg.input_value(f'[data-lfd="valor"][data-i="{i}"]') for i in range(pg.locator('[data-lfd="valor"]').count())], ['6,4368', '4,5'], 'recibo: os impostos viram % do bruto')
    igual([t.split('\n') for t in pg.locator('.lig-l').all_inner_texts()], [['Plano de saúde titular · nova despesa fixa ligada', '− R$ 320,00'], ['Coparticipação · nova despesa fixa ligada', '− R$ 85,40']], 'recibo: os outros descontos viram despesas fixas ligadas')
    res = pg.inner_text('#lf-desc-res')
    igual(res.split('\n')[:7], ['Bruto', 'R$ 13.050,00', 'Descontos', '− R$ 1.832,65', 'Líquido', 'R$ 11.217,35', 'cai na conta'], 'recibo: bruto, descontos e líquido')
    tem(res, 'Confere com o líquido do recibo: R$ 11.217,35.', 'recibo: confere com o líquido')
    pg.locator('.desc-sec').screenshot(path=f'{SP}/shots/s4-recibo.png')
    pg.click('[data-a="lf-salvar"]:not([data-mais])'); pg.wait_for_timeout(1300)
    d=st(); r=[x for x in d['recorrencias'] if x['descricao']=='Cooperativa'][0]
    igual((r['valor'], [(x['descricao'], x['modo'], x['valor'], x['categoria']) for x in r.get('descontos') or []]),
          (13050, [('INSS', 'pct', 6.4368, 'c-impostos'), ('Taxa administrativa', 'pct', 4.5, 'c-impostos')]), 'recebimento fixo com os impostos em %')
    igual([(x['descricao'], x['valor'], x['categoria'], x.get('tipo')) for x in d['recorrencias'] if x.get('vinculo')==r['id']],
          [('Plano de saúde titular', 320, 'c-saude', 'despesa'), ('Coparticipação', 85.4, 'c-saude', 'despesa')], 'as despesas ligadas ao recebimento')
    csv=urllib.request.urlopen(B+'api/export/lancamentos').read().decode('utf-8')
    igual(sum(1 for ln in csv.splitlines() if 'Desconto do recebimento' in ln), sum(len(calc.descontos_de(l)) for l in d['lancamentos']), 'CSV: uma linha por desconto de cada recebimento lançado')
    # categorias do mês (o mês que vem): os impostos saem em Impostos e taxas
    pg.click('[data-a="cx-modo"][data-v="categorias"]'); pg.wait_for_timeout(500)
    imp = pg.locator('.comps .comp:has-text("Impostos e taxas")')
    igual(imp.count(), 1, 'Categorias: os impostos na fonte em Impostos e taxas')
    if imp.count():
        perto(valores(imp.locator('.vl').inner_text())[0], round(875 + 562.5 + 840 + 587.25), 'Categorias: os impostos do salário e da Cooperativa', tol=0.6)
    print('ERROS', erros); b.close()
