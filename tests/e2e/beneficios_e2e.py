"""Benefícios lidos pela IA com o servidor de verdade (tema escuro e claro, celular e computador): a página dos
benefícios de um cartão inventado (servida aqui mesmo) lida pela IA simulada, a conferência (a anuidade fica de fora),
o cadastro ligado à conta e ao cartão, a lista com Cadastrar e Ler com IA lado a lado e do mesmo tamanho, e nada
passando da largura. Banco, cartão e pessoas inventados."""
import json
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, estado, ir_mais

SP = sys.argv[1]
B = "http://localhost:8099/"
erros = []
PAGINA = """<html><head><title>Cartão Coral Black</title></head><body><h1>Benefícios do cartão Coral Black</h1><ul>
<li>6 acessos à sala VIP por ano, com 1 acompanhante</li><li>US$ 100 em créditos de uso por mês no app parceiro</li>
<li>Seguro viagem internacional para toda a família</li><li>Anuidade de R$ 1.200,00</li></ul></body></html>""".encode()


class Pagina(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(PAGINA)))
        self.end_headers()
        self.wfile.write(PAGINA)


srv = ThreadingHTTPServer(("127.0.0.1", 0), Pagina)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/coral-black"


def req(p, c=None, m="GET"):
    r = urllib.request.Request(B + p, data=json.dumps(c).encode() if c is not None else None, method=m, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r).read())


# um banco inventado com a conta da Ana e o cartão Black
d = req("api/state")
d["bancos"] = [{"id": "b-coral", "nome": "Banco Coral", "cor": "#FF7A59", "contas": [
    {"id": "k-ana", "pessoa": "Ana", "cartao": True, "cartao_nivel": "Black", "fechamento": 5, "vencimento": 12}]}]
req("api/state", d, "PUT")

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, color_scheme="dark")
    pg.on("pageerror", lambda e: erros.append("PAGEERROR " + str(e)))
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
    pg.goto(B)
    pg.wait_for_timeout(600)
    ir_mais(pg, "beneficios")
    caixas = pg.evaluate("[...document.querySelectorAll('#beneficios .ben-botoes .btn')].map(e => { const r = e.getBoundingClientRect(); return [e.textContent.trim(), Math.round(r.width), Math.round(r.height), Math.round(r.top)]; })")
    igual([c[0] for c in caixas], ["Cadastrar", "Ler com IA"], "Cadastrar e Ler com IA lado a lado")
    sim(len(caixas) == 2 and caixas[0][1:] == caixas[1][1:], "os dois do mesmo tamanho e alinhados", caixas)

    pg.click('#beneficios [data-a="ben-ler"]')
    pg.wait_for_selector('[data-a="bler-origem"]')
    pg.click('[data-a="bler-origem"][data-v="conta:k-ana"]')
    pg.fill("#bler-txt", URL)
    pg.locator("#bler-txt").dispatch_event("input")
    pg.screenshot(path=f"{SP}/shots/ben-ler-escuro.png")
    pg.click('#folhas [data-a="bler-ler"]')
    pg.wait_for_selector("#folhas .bler-it", timeout=15000)
    itens = pg.evaluate("[...document.querySelectorAll('#folhas .bler-it')].map(b => b.innerText.replace(/\\s+/g, ' ').trim())")
    igual(itens, ["Sala VIP 6 por ano · com 1 acompanhante", "Créditos de uso US$ 100 por mês", "Seguro viagem Vantagem"],
          "a página lida pela IA: a anuidade fica de fora")
    tem(pg.inner_text("#folhas .da-intro"), "De Banco Coral · Ana · Black.", "de onde vêm")
    pg.screenshot(path=f"{SP}/shots/ben-conferir-escuro.png")
    pg.click('#folhas [data-a="bler-salvar"]')
    pg.wait_for_timeout(800)
    bs = estado(pg)["beneficios"]
    igual([(x["nome"], x["origem"], x["tipo"], x.get("total"), x.get("moeda"), x["renova"]) for x in bs],
          [("Sala VIP", "conta:k-ana", "contagem", 6, None, "ano"), ("Créditos de uso", "conta:k-ana", "saldo", 100, "USD", "mes"),
           ("Seguro viagem", "conta:k-ana", "vantagem", None, None, "nunca")], "os três cadastrados no servidor, ligados ao cartão")
    igual(pg.locator("#beneficios .ben-row").count(), 3, "a lista com os três")
    pg.locator("#beneficios").screenshot(path=f"{SP}/shots/ben-lista-escuro.png")
    uso = req("api/ia/uso")
    tem(json.dumps(uso, ensure_ascii=False), "beneficios", "conta no Uso da IA")
    pg.close()

    for nome, vp, esquema in (("claro-320", {"width": 320, "height": 800}, "light"), ("computador", {"width": 1280, "height": 900}, "light")):
        pg = b.new_page(viewport=vp, device_scale_factor=2, color_scheme=esquema)
        pg.on("pageerror", lambda e: erros.append("PAGEERROR " + str(e)))
        pg.goto(B)
        pg.wait_for_timeout(500)
        ir_mais(pg, "beneficios")
        largura = pg.evaluate("[document.documentElement.scrollWidth, innerWidth]")
        sim(largura[0] <= largura[1], f"{nome}: nada passa da largura", largura)
        pg.locator("#beneficios").screenshot(path=f"{SP}/shots/ben-lista-{nome}.png")
        pg.click('#beneficios [data-a="ben-ler"]')
        pg.wait_for_selector("#bler-txt")
        pg.click('[data-a="bler-origem"][data-v="conta:k-ana"]')
        pg.fill("#bler-txt", "6 acessos à sala VIP por ano\nFrete grátis")
        pg.locator("#bler-txt").dispatch_event("input")
        pg.click('#folhas [data-a="bler-ler"]')
        pg.wait_for_selector("#folhas .bler-it", timeout=15000)
        largura = pg.evaluate("[document.documentElement.scrollWidth, innerWidth]")
        sim(largura[0] <= largura[1], f"{nome}: a conferência cabe", largura)
        igual(pg.evaluate("[...document.querySelectorAll('#folhas .bler-it')].map(b => [b.getAttribute('aria-checked'), (b.querySelector('em') || {}).textContent || ''])"),
              [["false", "já cadastrado"], ["true", ""]], f"{nome}: o que já está cadastrado vem desmarcado")
        pg.screenshot(path=f"{SP}/shots/ben-conferir-{nome}.png")
        pg.close()
    print("ERROS", erros)
    b.close()
srv.shutdown()
