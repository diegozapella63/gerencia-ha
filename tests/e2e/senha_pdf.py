"""Fatura em PDF com senha, com o servidor de verdade (IA simulada; fatura inventada em tests/fixtures/pdf_senha):
a leitura pede a senha, avisa a senha errada e, com a certa, lê e guarda para as próximas; a senha aparece escondida em
Mais › Configurações › Integrações › Senhas dos PDFs, onde dá para cadastrar outra e apagar; a próxima fatura abre
sozinha. Capturas no celular (390 px)."""
import sys, os, json, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sem, sim, ir_mais
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fixtures', 'pdf_senha')
def senhas(): return json.loads(urllib.request.urlopen(B + 'api/senhas').read())['senhas']
def ler_pdf(pg, nome):
    with pg.expect_file_chooser() as fc:
        pg.click('[data-a="ia-de"][data-ini="arquivo"]')
    fc.value.set_files(os.path.join(FIX, nome)); pg.wait_for_timeout(800)
    pg.click('.folha [data-a="ia-ler"]')
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 390, 'height': 844}, color_scheme='dark', device_scale_factor=2)
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' and '400' not in m.text else None)
    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1200)
    igual(senhas(), [], 'começa sem senhas')
    # Caixa › Adicionar › Fatura, print ou foto: o PDF com senha
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(500)
    ler_pdf(pg, 'fatura-aes256.pdf')
    pg.wait_for_selector('#ia-senha', timeout=8000)
    igual(pg.inner_text('.folha .msg-erro'), 'Este PDF tem senha.', 'pede a senha')
    igual(pg.evaluate("document.activeElement.id"), 'ia-senha', 'o cursor já na senha')
    tem(pg.inner_text('.folha .linha-sw'), 'Guardar para as próximas faturas', 'oferece guardar')
    igual(pg.get_attribute('.folha [data-a="ias-guardar"]', 'aria-checked'), 'true', 'guardar vem ligado')
    sim(not pg.evaluate("document.querySelector('.folha-corpo').scrollWidth > document.querySelector('.folha-corpo').clientWidth"), 'nada sai da folha')
    pg.screenshot(path=f'{SP}/shots/senha-pede.png')
    # a errada
    pg.fill('#ia-senha', '000'); pg.click('.folha [data-a="ia-ler"]')
    pg.wait_for_function("() => (document.querySelector('.folha .msg-erro') || {}).textContent === 'Senha errada para este PDF.'", timeout=8000)
    igual(pg.inner_text('.folha .msg-erro'), 'Senha errada para este PDF.', 'senha errada')
    # a certa: lê e guarda
    pg.fill('#ia-senha', '12345'); pg.click('.folha [data-a="ia-ler"]')
    pg.wait_for_selector('.folha [data-a="ia-salvar"]', timeout=15000)
    sem(pg.inner_text('.folha'), 'tem senha', 'leu a fatura')
    s = senhas()
    igual([(x['nome'], x['fim']) for x in s], [('Da fatura fatura-aes256', '••••45')], 'guardou a senha (escondida)')
    pg.screenshot(path=f'{SP}/shots/senha-leu.png')
    pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    if pg.locator('.folha').count():
        pg.click('.folha-cab [data-a="fechar"]'); pg.wait_for_timeout(400)
    # Mais › Configurações › Integrações › Senhas dos PDFs
    ir_mais(pg, 'config', 'integracoes')
    card = pg.locator('#senhas-pdf')
    card.scroll_into_view_if_needed()
    igual(card.locator('.senha-l b').all_inner_texts(), ['Da fatura fatura-aes256'], 'a senha guardada na lista')
    igual(card.locator('.senha-l small').all_inner_texts(), ['••••45'], 'escondida')
    sem(card.inner_text(), '12345', 'a senha nunca aparece')
    pg.click('#senhas-pdf [data-a="senha-nova"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('.folha-cab h2'), 'Nova senha', 'abre a janela')
    pg.click('.folha [data-a="senha-salvar"]'); pg.wait_for_timeout(300)
    igual(pg.inner_text('.folha .msg-erro'), 'Digite a senha.', 'sem senha não salva')
    pg.fill('#sn-nome', 'CPF do Beto'); pg.fill('#sn-senha', '98765')
    pg.screenshot(path=f'{SP}/shots/senha-nova.png')
    pg.click('.folha [data-a="senha-salvar"]'); pg.wait_for_timeout(600)
    igual(pg.locator('.folha').count(), 0, 'fecha ao salvar')
    igual(card.locator('.senha-l b').all_inner_texts(), ['Da fatura fatura-aes256', 'CPF do Beto'], 'a nova na lista')
    pg.screenshot(path=f'{SP}/shots/senha-lista.png')
    pg.click('#senhas-pdf [data-a="senha-apagar"] >> nth=1'); pg.wait_for_timeout(600)
    igual(card.locator('.senha-l b').all_inner_texts(), ['Da fatura fatura-aes256'], 'apagou')
    igual(len(senhas()), 1, 'apagou no servidor')
    # a próxima fatura (outra cifra, a mesma senha) abre sozinha
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(500)
    ler_pdf(pg, 'fatura-rc4-128.pdf')
    pg.wait_for_selector('.folha [data-a="ia-salvar"]', timeout=15000)
    igual(pg.locator('#ia-senha').count(), 0, 'a próxima abre sozinha, sem pedir')
    b.close()
print('ERROS', erros)
