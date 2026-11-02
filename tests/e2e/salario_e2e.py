import sys, json, urllib.request
from playwright.sync_api import sync_playwright
SP=sys.argv[1]; erros=[]
B='http://localhost:8099/'
def st(): return json.loads(urllib.request.urlopen(B+'api/state').read())
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':396,'height':860}, device_scale_factor=2, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR '+str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type=='error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(500)
    tog=pg.locator('.desc-tog').first
    print('1 toggle:', tog.inner_text().replace('\n',' | '))
    tog.click(); pg.wait_for_timeout(300)
    print('  itens:', [t.replace('\n',' | ') for t in pg.locator('.desc-itens .lanc').all_inner_texts()])
    pg.locator('.lanc:has-text("Salário")').first.screenshot(path=f'{SP}/shots/s0-linha.png')
    lin=pg.locator('.lanc:has-text("Salário")').first; box=lin.bounding_box()
    pg.screenshot(path=f'{SP}/shots/s1-lista.png', clip={'x':0,'y':max(0,box['y']-60),'width':396,'height':420})
    # próximo mês: Recebi no salário
    pg.click('[data-a="cx-mes"][data-v="1"]'); pg.wait_for_timeout(400)
    sal=pg.locator('.lanc:has-text("Salário")').first
    print('2 próximo mês, salário:', sal.inner_text().replace('\n',' | '))
    sal.locator('[data-a="lanc-pagar"]').click(); pg.wait_for_timeout(500)
    print('  folha:', pg.inner_text('.folha-cab h2'), '| situação recebido?', pg.locator('[data-a="lf-pago"][data-v="1"].on').count())
    pg.fill('#lf-valor',''); pg.type('#lf-valor','1250000'); pg.wait_for_timeout(300)
    print('  resumo:', pg.inner_text('#lf-desc-res').replace('\n',' | '))
    pg.locator('.desc-sec').screenshot(path=f'{SP}/shots/s2-impostos.png')
    pg.click('[data-a="lf-salvar"][data-v="este"]'); pg.wait_for_timeout(1200)
    d=st(); ym=[l for l in d['lancamentos'] if l.get('recorrencia')=='r-sal'][-1]
    pl=[l for l in d['lancamentos'] if l.get('recorrencia')=='r-plano' and l.get('competencia')==ym['competencia']]
    print('  salário materializado:', ym['valor'], ym['pago'], ym['data'], '| plano:', [(x['valor'], x['pago'], x['data'], x.get('vinculo')) for x in pl])
    # plano: formulário
    pg.locator('.desc-tog').first.click(); pg.wait_for_timeout(300)
    pg.locator('.desc-itens .lanc:has-text("Plano de saúde")').first.click(); pg.wait_for_timeout(500)
    print('3 form plano:', pg.locator('#lf-vinc').input_value(), '|', pg.inner_text('.vinc-st').strip())
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
    print('4 depois do recibo, bruto:', pg.input_value('#lf-valor'), '| impostos:', [pg.input_value(f'[data-lfd="valor"][data-i="{i}"]') for i in range(pg.locator('[data-lfd="valor"]').count())])
    print('  ligados:', [t.replace('\n',' | ') for t in pg.locator('.lig-l').all_inner_texts()])
    print('  resumo:', pg.inner_text('#lf-desc-res').replace('\n',' | '))
    pg.locator('.desc-sec').screenshot(path=f'{SP}/shots/s4-recibo.png')
    pg.click('[data-a="lf-salvar"]:not([data-mais])'); pg.wait_for_timeout(1300)
    d=st(); r=[x for x in d['recorrencias'] if x['descricao']=='Cooperativa'][0]
    print('  recorrência:', r['valor'], r.get('descontos'), '| ligadas:', [(x['descricao'], x['valor'], x['categoria']) for x in d['recorrencias'] if x.get('vinculo')==r['id']])
    csv=urllib.request.urlopen(B+'api/export/lancamentos').read().decode('utf-8')
    print('5 csv descontos:', sum(1 for ln in csv.splitlines() if 'Desconto do recebimento' in ln))
    # categorias do mês
    pg.click('[data-a="cx-modo"][data-v="categorias"]'); pg.wait_for_timeout(500)
    print('6 categorias:', pg.inner_text('#app').count('Impostos e taxas'), 'menções de impostos')
    print('ERROS', erros); b.close()
