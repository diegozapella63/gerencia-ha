"""Digitalizar com IA sem câmera no navegador (http, sem mediaDevices): o quadrinho avisa que precisa de https, a janela
explica e oferece tirar ou escolher a foto pelo celular (com a câmera de trás), e a foto escolhida já vai para a IA."""
import sys
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim
SP = sys.argv[1]; erros = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark')
    pg.add_init_script("Object.defineProperty(navigator, 'mediaDevices', { value: undefined })")
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    igual(pg.inner_text('[data-ini="camera"]').replace('\xa0', ' ').split('\n'), ['Digitalizar com IA', 'Precisa de https'], 'o quadrinho avisa que precisa de https')
    pg.click('[data-ini="camera"]'); pg.wait_for_timeout(500)
    igual(pg.inner_text('.cam-msg p'), 'Este navegador não deixa usar a câmera aqui. Dá para tirar a foto pelo celular e escolher.', 'explica por que a câmera não abre')
    igual(pg.locator('[data-a="cam-galeria"]').count(), 1, 'oferece tirar ou escolher a foto')
    pg.screenshot(path=f'{SP}/shots/cam-erro.png')
    with pg.expect_file_chooser() as fc: pg.click('[data-a="cam-galeria"]')
    igual(fc.value.element.get_attribute('capture'), 'environment', 'o seletor já pede a câmera de trás do celular')
    fc.value.set_files(f'{SP}/print.jpg'); pg.wait_for_timeout(3500)
    igual(pg.inner_text('.folha-cab h2'), 'Conferir lançamentos', 'a foto escolhida vai direto para a IA')
    sim(pg.locator('.ia-item').count() > 0, 'com o que a IA leu', pg.locator('.ia-item').count())
    print('ERROS', erros); b.close()
