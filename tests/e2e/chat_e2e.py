"""Conversar com a IA, com o servidor de verdade (IA simulada): perguntar, lançar um gasto, pagar a conta de luz
pelo chat (Confirmar e Editar), a conversa guardada no servidor depois de recarregar e o Voltar do celular."""
import sys, json, urllib.request
from datetime import date
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, mes

SP = sys.argv[1]; erros = []
B = 'http://localhost:8099/'
def get(p): return json.loads(urllib.request.urlopen(B + p).read())

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2, color_scheme='dark', extra_http_headers={'X-Remote-User-Display-Name': 'Ana'})
    pg.on('pageerror', lambda e: erros.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    titulo = lambda: pg.inner_text('.folha-cab h2') if pg.locator('.folha-cab h2').count() else '(nenhuma)'
    def enviar(t):
        pg.fill('#ch-txt', t); pg.press('#ch-txt', 'Enter')
        pg.wait_for_function("!document.querySelector('.ch-pensando')", timeout=10000); pg.wait_for_timeout(200)

    pg.goto(B); pg.wait_for_timeout(800)
    pg.click('[data-a="carregar-exemplo"]'); pg.wait_for_timeout(1500)
    igual([x.get_attribute('data-a') for x in pg.locator('.cab-topo button').all()], ['chat', 'falar'], 'o balão ao lado do microfone')
    pg.click('.cab-topo [data-a="chat"]'); pg.wait_for_timeout(600)
    igual(titulo(), 'Conversar com a IA', 'abre o chat')
    igual(pg.locator('.ch-sug .chip').count(), 3, 'conversa nova com sugestões')
    pg.screenshot(path=f'{SP}/shots/chat-vazio.png')

    enviar('qual o saldo do caixa?')
    tem(pg.locator('.ch-msg.ia .ch-bolha').last.inner_text(), 'O saldo do caixa hoje é', 'responde com os dados do app')

    n0 = len(get('api/state')['lancamentos'])
    enviar('gastei 45 no mercado')
    tem(pg.locator('.ch-acao').last.inner_text(), 'Mercado', 'propõe o lançamento')
    pg.locator('[data-a="ch-ok"]').last.click(); pg.wait_for_timeout(900)
    d = get('api/state')
    novo = [l for l in d['lancamentos'] if l['descricao'] == 'Mercado' and l['data'] == date.today().isoformat() and l['valor'] == 45]
    igual((len(d['lancamentos']) - n0, len(novo)), (1, 1), 'Confirmar lança no caixa')
    igual(pg.locator('.ch-feito').last.inner_text().strip(), 'Lançado', 'o cartão fica como lançado')

    luz = next(l for l in get('api/state')['recorrencias'] if l['id'] == 'r-luz')
    enviar(f"paguei a {luz['descricao'].lower()}, 287,45")
    tem(pg.locator('.ch-acao').last.inner_text(), 'R$ 287,45', 'propõe pagar a conta com o valor dito')
    pg.locator('[data-a="ch-editar"]').last.click(); pg.wait_for_timeout(500)
    igual((titulo(), pg.input_value('#pg-v')), ('Confirmar pagamento', '287,45'), 'Editar abre o Confirmar pagamento')
    pg.go_back(); pg.wait_for_timeout(400)
    igual(titulo(), 'Conversar com a IA', 'Voltar do celular volta para a conversa')
    pg.locator('[data-a="ch-editar"]').last.click(); pg.wait_for_timeout(400)
    pg.click('[data-a="pg-ok"]'); pg.wait_for_timeout(900)
    igual(titulo(), 'Conversar com a IA', 'Paguei volta para a conversa')
    pago = [l for l in get('api/state')['lancamentos'] if l.get('recorrencia') == 'r-luz' and l.get('pago') and l['valor'] == 287.45]
    igual(len(pago), 1, 'a conta de luz ficou paga com o valor')
    pg.screenshot(path=f'{SP}/shots/chat-conversa.png')

    msgs = get('api/chat')['mensagens']
    igual(len(msgs), 6, 'a conversa fica guardada no servidor')
    igual([m.get('estado') for m in msgs if m.get('acoes')], [{'lancamentos': 'feito'}, {'pagar.0': 'feito'}], 'com o que foi confirmado')
    sim(get('api/ia/uso')['today'].get('kinds', {}).get('chat', 0) >= 3, 'conta no uso da IA como conversa')

    pg.reload(); pg.wait_for_timeout(1200)
    pg.click('.cab-topo [data-a="chat"]'); pg.wait_for_timeout(700)
    igual(pg.locator('.ch-msg').count(), 6, 'depois de recarregar, a conversa volta de onde parou')
    igual(pg.locator('[data-a="ch-ok"]').count(), 0, 'e o que foi confirmado não pede de novo')
    pg.go_back(); pg.wait_for_timeout(400)
    igual(titulo(), '(nenhuma)', 'Voltar fecha o chat')

    pg.click('.cab-topo [data-a="chat"]'); pg.wait_for_timeout(500)
    pg.click('[data-a="ch-limpar"]'); pg.click('[data-a="ch-limpar-sim"]'); pg.wait_for_timeout(500)
    igual((pg.locator('.ch-msg').count(), get('api/chat')['mensagens']), (0, []), 'apagar a conversa')
    print('ERROS', erros); b.close()
