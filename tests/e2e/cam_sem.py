import sys
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; erros = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 412, 'height': 900}, color_scheme='dark')
    pg.add_init_script("Object.defineProperty(navigator, 'mediaDevices', { value: undefined })")
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.goto('http://localhost:8099/'); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    pg.click('#nav [data-v="caixa"]'); pg.wait_for_timeout(300)
    pg.click('#nav [data-a="novo"]'); pg.wait_for_timeout(400)
    print('tile:', pg.inner_text('[data-ini="camera"]').replace('\n', ' | '))
    pg.click('[data-ini="camera"]'); pg.wait_for_timeout(500)
    print('msg:', pg.inner_text('.cam-msg p'))
    pg.screenshot(path=f'{SP}/shots/cam-erro.png')
    with pg.expect_file_chooser() as fc: pg.click('[data-a="cam-galeria"]')
    print('capture:', fc.value.element.get_attribute('capture'))
    fc.value.set_files(f'{SP}/print.jpg'); pg.wait_for_timeout(3500)
    print('leu:', pg.inner_text('.folha-cab h2'))
    print('ERROS', erros); b.close()
