"""Colar ou soltar uma imagem na Nova despesa e no Novo investimento abre a leitura com a imagem; X volta."""
from _confere import igual, tem, sim
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
    igual(pg.inner_text('.imp-campo .lbl'), 'Trazer de mensagem ou imagem', 'Novo investimento: trazer de mensagem ou imagem')
    igual([x.replace('\n', ' ').replace('\xa0', ' ') for x in pg.locator('.imp-tile').all_inner_texts()], ['Colar mensagem', 'Escolher fotos', 'Digitalizar com IA', 'Falar'], 'os quadrinhos')
    igual(pg.inner_text('.imp-ajuda'), 'Dá para colar a imagem direto aqui.', 'ajuda')
    pg.screenshot(path=f'{SP}/shots/colar-inv.png')
    pg.evaluate(JS, [img, 'paste']); pg.wait_for_timeout(1200)
    igual((pg.inner_text('.folha-cab h2'), pg.locator('.folha .seg').count(), pg.locator('.ia-prev').count()), ('Escolher fotos', 0, 1), 'colou: abre a leitura com a imagem, sem escolher tipo')
    pg.click('[data-a="ia-ler"]'); pg.wait_for_timeout(2800)
    igual(pg.inner_text('.folha-cab h2'), 'Conferir investimentos', 'leu os investimentos')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Novo investimento', 'X volta para o Novo investimento')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.evaluate(JS, [img, 'drop']); pg.wait_for_timeout(1200)
    igual((pg.inner_text('.folha-cab h2'), pg.locator('.folha .seg').count(), pg.locator('.ia-prev').count()), ('Escolher fotos ou PDF', 0, 1), 'soltou na despesa: abre com a imagem')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Nova despesa', 'X volta para a Nova despesa')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # colar texto num campo do formulário continua normal
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    pg.click('#lf-desc'); pg.keyboard.insert_text('Mercado')
    igual((pg.input_value('#lf-desc'), pg.inner_text('.folha-cab h2')), ('Mercado', 'Nova despesa'), 'colar texto num campo é só texto')
    print('ERROS', erros); b.close()
