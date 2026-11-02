import sys, base64
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
img = base64.b64encode(open(f'{SP}/print.jpg', 'rb').read()).decode()
JS = """([b64, tipo]) => { const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0)); const f = new File([bin], 'print.jpg', { type: 'image/jpeg' });
  const dt = new DataTransfer(); dt.items.add(f);
  if (tipo === 'paste') document.activeElement.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
  else { const alvo = document.querySelector('.folha'); alvo.dispatchEvent(new DragEvent('dragover', { dataTransfer: dt, bubbles: true, cancelable: true })); alvo.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true })); } }"""
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark')
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-v="investimentos"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    print('1 Novo investimento:', pg.inner_text('.imp-campo .lbl'), '|', [x.replace('\n', ' ') for x in pg.locator('.imp-tile').all_inner_texts()])
    print('  ajuda:', pg.inner_text('.imp-ajuda'))
    pg.screenshot(path=f'{SP}/shots/colar-inv.png')
    pg.evaluate(JS, [img, 'paste']); pg.wait_for_timeout(1200)
    print('2 colou imagem:', pg.inner_text('.folha-cab h2'), '| escolha de tipo:', pg.locator('.folha .seg').count(), '| anexo', pg.locator('.ia-prev').count())
    pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2800)
    print('  leu:', pg.inner_text('.folha-cab h2'))
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    print('  X volta para:', pg.inner_text('.folha-cab h2'))
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.evaluate(JS, [img, 'drop']); pg.wait_for_timeout(1200)
    print('3 soltou imagem na despesa:', pg.inner_text('.folha-cab h2'), '| escolha de tipo:', pg.locator('.folha .seg').count(), '| anexo', pg.locator('.ia-prev').count())
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    print('  X volta para:', pg.inner_text('.folha-cab h2'))
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # colar texto num campo do formulário continua normal
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('#lf-desc'); pg.keyboard.insert_text('Mercado')
    print('4 texto no campo:', pg.input_value('#lf-desc'), '| janela', pg.inner_text('.folha-cab h2'))
    print('ERROS', erros); b.close()
