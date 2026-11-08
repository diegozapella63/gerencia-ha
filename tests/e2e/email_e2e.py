"""Faturas por e-mail com o servidor de verdade (IA simulada; e-mails e faturas inventados de tests/fixtures/pdf_senha,
que chegam pela rota de teste /api/emails/simular como se viessem do Home Assistant): ligar em Integrações, De quem,
a fatura com senha pede a senha no Início e, com ela, lê e lança (e guarda a senha); a sem senha já chega lida para
conferir (as compras já lançadas vêm desmarcadas) e dá para ignorar; os avisos somem; a próxima fatura com a mesma
senha abre sozinha. Capturas no celular (390 px), no tema escuro e no claro."""
import sys, os, json, base64, urllib.request
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sem, sim, ir_mais
SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fixtures', 'pdf_senha')
def api(m, p, c=None):
    r = urllib.request.Request(B + p, data=json.dumps(c).encode() if c is not None else None, method=m, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
def chegar(nome, assunto, de='Banco Azul <fatura@bancoazul.com.br>'):
    with open(os.path.join(FIX, nome), 'rb') as f:
        api('POST', 'api/emails/simular', {'de': de, 'assunto': assunto, 'arquivo': nome, 'b64': base64.b64encode(f.read()).decode()})
def estados(): return {x['assunto']: x['estado'] for x in api('GET', 'api/emails')['itens']}
def esperar_estado(pg, assunto, estado, ms=15000):
    for _ in range(ms // 100):
        if estados().get(assunto) == estado:
            return True
        pg.wait_for_timeout(100)
    igual(estados().get(assunto), estado, f'{assunto}: {estado}')
with sync_playwright() as p:
    b = p.chromium.launch()
    for tema in ('dark', 'light'):
        pg = b.new_page(viewport={'width': 390, 'height': 844}, color_scheme=tema, device_scale_factor=2)
        pg.on('pageerror', lambda e: erros.append(str(e)))
        pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' and '400' not in m.text else None)
        pg.goto(B); pg.wait_for_timeout(800)
        if tema == 'dark':
            pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1200)
            # Mais › Configurações › Integrações › Faturas por e-mail
            ir_mais(pg, 'config', 'integracoes')
            card = pg.locator('#email'); card.scroll_into_view_if_needed()
            tem(card.inner_text(), 'Desligado.', 'começa desligado')
            pg.click('#email [data-a="ajuste"][data-k="email"]'); pg.wait_for_timeout(800)
            igual(pg.inner_text('#email .status'), 'ana@exemplo.com', 'a conta de e-mail do Home Assistant')
            pg.fill('#email-de', 'bancoazul.com.br'); pg.press('#email-de', 'Enter'); pg.wait_for_timeout(500)
            igual(pg.locator('#email .email-de .chip').all_inner_texts(), ['bancoazul.com.br'], 'De quem')
            # chegam três: com senha, sem senha e um de outro remetente
            chegar('fatura-aes256.pdf', 'Fatura de novembro')
            chegar('fatura-azul.pdf', 'Fatura de outubro')
            chegar('fatura-rc4-40.pdf', 'Boleto da loja', de='Loja Exemplo <ofertas@lojaexemplo.com>')
            esperar_estado(pg, 'Fatura de novembro', 'senha'); esperar_estado(pg, 'Fatura de outubro', 'conferir'); esperar_estado(pg, 'Boleto da loja', 'fora')
            pg.reload(); pg.wait_for_timeout(1200)
            ir_mais(pg, 'config', 'integracoes')
            card = pg.locator('#email'); card.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
            igual(sorted(pg.locator('#email .email-l em, #email .email-l button').all_inner_texts()), sorted(['Precisa da senha', 'Para conferir', 'Ler']), 'Recebidos com o estado de cada um')
            card.screenshot(path=f'{SP}/shots/email-card.png')
            # Opções: avisar no celular
            pg.click('#app .mais-abas [data-a="mais-aba"][data-v="opcoes"]'); pg.wait_for_timeout(300)
            tem(pg.inner_text('#op-email'), 'Avisar no celular', 'a opção do aviso')
        else:
            pg.wait_for_timeout(600)
        # Início: os avisos
        pg.click('#nav [data-a="tab"][data-v="inicio"]'); pg.wait_for_timeout(500)
        av = pg.locator('[data-a="email-abrir"]')
        if tema == 'dark':
            igual(sorted(pg.locator('[data-a="email-abrir"] .op-t b').all_inner_texts()), ['Fatura Banco Azul', 'Fatura Banco Azul'], 'as duas faturas nos avisos (a da loja não)')
        av.first.scroll_into_view_if_needed(); pg.wait_for_timeout(200)
        pg.screenshot(path=f'{SP}/shots/email-inicio-{tema}.png')
        if tema == 'light':
            pg.close(); break
        # a com senha: pede a senha, lê e lança
        pg.click('[data-a="email-abrir"]:has-text("o PDF tem senha")'); pg.wait_for_selector('#ia-senha', timeout=8000)
        igual(pg.inner_text('.folha-cab h2'), 'Fatura, print ou foto', 'abre o PDF que chegou')
        igual(pg.inner_text('.folha .msg-erro'), 'Este PDF tem senha.', 'pede a senha')
        pg.screenshot(path=f'{SP}/shots/email-senha.png')
        pg.fill('#ia-senha', '12345'); pg.click('.folha [data-a="ia-ler"]')
        pg.wait_for_selector('.folha [data-a="ia-salvar"]', timeout=15000)
        igual(pg.inner_text('.folha .folha-pe .btn >> nth=0'), 'Ignorar', 'Ignorar no lugar de Voltar')
        pg.click('.folha [data-a="ia-salvar"]'); pg.wait_for_timeout(1200)
        igual(estados().get('Fatura de novembro'), 'feito', 'lançada')
        igual([x['nome'] for x in api('GET', 'api/senhas')['senhas']], ['Da fatura fatura-aes256'], 'a senha ficou guardada')
        # a sem senha: já lida, é só conferir
        pg.click('#nav [data-a="tab"][data-v="inicio"]'); pg.wait_for_timeout(500)
        igual(pg.locator('[data-a="email-abrir"]').count(), 1, 'sobrou um aviso')
        pg.click('[data-a="email-abrir"]'); pg.wait_for_timeout(500)
        igual(pg.inner_text('.folha-cab h2'), 'Conferir lançamentos', 'direto na conferência')
        # a IA simulada lê as mesmas compras: vêm desmarcadas, como já lançadas (a fatura que já foi lançada não entra de novo)
        sim(pg.locator('.folha .ia-item.off').count() > 0, 'parecidas com as já lançadas vêm desmarcadas', pg.locator('.folha .ia-item.off').count())
        tem(pg.inner_text('.folha'), 'parece já lançado', 'e avisa')
        pg.screenshot(path=f'{SP}/shots/email-conferir.png')
        pg.click('.folha [data-a="email-ignorar"]'); pg.wait_for_timeout(800)
        igual(estados().get('Fatura de outubro'), 'ignorado', 'ignorada')
        pg.click('#nav [data-a="tab"][data-v="inicio"]'); pg.wait_for_timeout(500)
        igual(pg.locator('[data-a="email-abrir"]').count(), 0, 'sem avisos de e-mail')
        # a da loja dá para ler pelos Recebidos (e volta a esperar a conferência)
        chegar('fatura-aes128-objstm.pdf', 'Fatura de dezembro')
        esperar_estado(pg, 'Fatura de dezembro', 'conferir')  # a senha guardada abre sozinha
        pg.close()
    b.close()
print('ERROS', erros)
