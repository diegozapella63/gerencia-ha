"""Oportunidades de investimento com o servidor de verdade (tema escuro e claro, celular e computador): as taxas do
Tesouro Direto (a tabela de exemplo em fixtures/tesouro-investir.csv), o alvo de cada família, a página de ofertas de
um banco cadastrado (inventado, servida aqui mesmo) lida pela IA simulada, o equivalente em CDB da LCA, quanto rende em
destaque, o Conferir agora e, em
Opções, o aviso no celular com o horário, o Testar e quem recebe. Bancos, taxas e pessoas inventados."""
import json
import sys
import threading
import urllib.request
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from _confere import igual, tem, sim, estado

SP = sys.argv[1]
erros = []
PAGINA = """<html><body><h1>Banco Sol: renda fixa</h1><ul>
<li>CDB Banco Sol 125% do CDI, liquidez diária</li><li>LCA Banco Sol 96% do CDI vence em 10/12/2029</li>
<li>Fundo Sol Multimercado 140% do CDI no ano</li></ul></body></html>""".encode()


class Pagina(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(PAGINA)))
        self.end_headers()
        self.wfile.write(PAGINA)


# as taxas e as ofertas vêm do servidor em segundo plano: até 30 s (no GitHub, com a bateria toda, 15 s já não bastou)
srv = ThreadingHTTPServer(("127.0.0.1", 0), Pagina)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/renda-fixa"


def req(caminho, corpo=None, metodo="GET"):
    r = urllib.request.Request("http://localhost:8099/" + caminho, data=json.dumps(corpo).encode() if corpo is not None else None, method=metodo,
                               headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r).read())


def linhas(pg, g):
    return pg.evaluate("""g => [...document.querySelectorAll(`#oportunidades .op-grupo[data-grupo="${g}"] .op-row`)].map(r => [
        r.querySelector('.op-t b').textContent, r.querySelector('.op-v b').textContent, r.classList.contains('passa'),
        (r.querySelector('.op-v small') || {}).textContent || ''])""", g)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, color_scheme="dark")
    pg.on("pageerror", lambda e: erros.append("PAGEERROR " + str(e)))
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
    pg.goto("http://localhost:8099/")
    pg.wait_for_timeout(600)
    pg.click('#nav [data-a="tab"][data-v="mais"]')
    pg.click('[data-a="mais-tela"][data-v="invest"]')
    pg.wait_for_selector("#oportunidades .op-row", timeout=30000)
    igual([x[0] for x in linhas(pg, "pre")], ["Tesouro Prefixado 2032", "Tesouro Prefixado 2029"], "Tesouro: os prefixados, do maior para o menor")
    igual([x[0] for x in linhas(pg, "ipca")], ["Tesouro IPCA+ 2032", "Tesouro IPCA+ 2040"], "Tesouro: Renda+ e Educa+ ficam de fora")
    tem(pg.inner_text("#oportunidades .dica-quando"), "Tesouro Direto: taxas de hoje", "a hora das taxas")

    # o alvo do IPCA+ marca o que passou
    pg.fill('[data-op-alvo="op_ipca"]', "7")
    pg.locator('[data-op-alvo="op_ipca"]').dispatch_event("change")
    pg.wait_for_timeout(500)
    igual(estado(pg)["ajustes"]["op_ipca"], 7, "o alvo fica gravado no servidor")
    igual([(x[0], x[2]) for x in linhas(pg, "ipca")], [("Tesouro IPCA+ 2032", True), ("Tesouro IPCA+ 2040", False)], "IPCA + 7,04% passou do alvo de 7%")

    # as ofertas vêm dos bancos cadastrados: sem página, o banco aparece em "Sem página de ofertas"
    d = req("api/state")
    d["bancos"] = [{"id": "b-sol", "nome": "Banco Sol", "cor": "#FFA23E", "contas": [{"id": "k-sol", "pessoa": "Ana", "cartao": False, "fechamento": 1, "vencimento": 10}]}]
    req("api/state", d, "PUT")
    pg.reload()
    pg.wait_for_selector("#oportunidades .op-sem", timeout=30000)
    igual(pg.inner_text("#oportunidades .op-sem"), "Sem página de ofertas: Banco Sol.", "o banco sem página")
    igual(pg.locator("#op-url, #oportunidades .op-pag").count(), 0, "sem lista de páginas para pôr à mão")
    # a página do banco: a IA simulada lê, o fundo fica de fora, a LCA vem com o equivalente em CDB
    pg.click('#oportunidades .op-sem [data-a="banco"]')
    pg.fill("#b-ofertas", URL)
    pg.click('#folhas [data-a="b-salvar"]')
    pg.wait_for_function("() => (document.querySelector('#oportunidades .op-bancos') || {}).textContent === 'Ofertas dos seus bancos: Banco Sol (2 ofertas).'", timeout=30000)
    igual(estado(pg)["bancos"][0].get("ofertas"), URL, "a página gravada no banco")
    pos = linhas(pg, "pos")
    igual(pos[0][:2], ["CDB Banco Sol", "125% do CDI"], "a melhor do pós-fixado é a oferta da página")
    sim(pos[1][0] == "LCA Banco Sol" and pos[1][3].startswith("como CDB de 11"), "a LCA com o equivalente em CDB", pos[1])
    sim(all("Fundo" not in x[0] for x in pos), "o fundo não entra (sem FGC)")
    g = pg.evaluate("""(() => { const r = document.querySelector('#oportunidades .op-row'), g = r.querySelector('.op-ganho'), b = g.querySelector('b');
        return [Math.round(g.getBoundingClientRect().width) === Math.round(r.getBoundingClientRect().width), b.textContent, getComputedStyle(b).color, getComputedStyle(g.querySelector('span')).color,
                g.querySelector('span').textContent]; })()""")
    sim(g[0] and g[1].startswith("+R$ ") and g[2] != g[3] and g[4] == "em 1 ano com R$ 10 mil", "quanto rende em destaque, na largura toda", g)
    pg.locator("#oportunidades").screenshot(path=f"{SP}/shots/op-invest-escuro.png")

    # Conferir agora
    pg.click('#oportunidades [data-a="op-conferir"]')
    pg.wait_for_function("() => !document.querySelector('#oportunidades [data-a=\"op-conferir\"]').disabled", timeout=30000)
    sim(len(linhas(pg, "pos")) >= 3, "depois do Conferir agora, as linhas continuam")

    # Opções: o aviso no celular (fora do Home Assistant não há pessoas: a nota diz o porquê)
    pg.click('[data-a="mais-volta"]') if pg.locator('[data-a="mais-volta"]').count() else None
    pg.goto("http://localhost:8099/")
    pg.wait_for_timeout(500)
    pg.click('#nav [data-a="tab"][data-v="mais"]')
    pg.click('[data-a="mais-tela"][data-v="config"]')
    pg.click('[data-a="mais-aba"][data-v="opcoes"]')
    pg.click('#op-oport [data-a="ajuste"][data-k="op_aviso"]')
    pg.wait_for_selector("#op-hora")
    pg.wait_for_timeout(500)
    igual(estado(pg)["ajustes"]["op_aviso"], True, "o aviso ligado no servidor")
    igual(pg.input_value("#op-hora"), "10:00", "o horário começa às 10:00")
    tem(pg.inner_text("#op-oport"), "Fora do Home Assistant não dá para avisar no celular.", "fora do Home Assistant, o porquê")
    pg.select_option("#op-hora", "09:30")
    pg.wait_for_timeout(400)
    igual(estado(pg)["ajustes"]["op_hora"], "09:30", "o horário gravado")
    pg.locator("#op-oport").screenshot(path=f"{SP}/shots/op-opcoes-escuro.png")
    pg.close()

    # tema claro, celular estreito e computador: nada passa da largura
    for nome, vp, esquema in (("claro-320", {"width": 320, "height": 800}, "light"), ("computador", {"width": 1280, "height": 900}, "light")):
        pg = b.new_page(viewport=vp, device_scale_factor=2, color_scheme=esquema)
        pg.on("pageerror", lambda e: erros.append("PAGEERROR " + str(e)))
        pg.goto("http://localhost:8099/")
        pg.wait_for_timeout(500)
        if pg.locator('#nav [data-a="tab"][data-v="mais"]').is_visible():
            pg.click('#nav [data-a="tab"][data-v="mais"]')
        else:
            pg.click('[data-a="tab"][data-v="mais"] >> visible=true')
        pg.click('[data-a="mais-tela"][data-v="invest"]')
        pg.wait_for_selector("#oportunidades .op-row", timeout=30000)
        largura = pg.evaluate("[document.documentElement.scrollWidth, innerWidth]")
        sim(largura[0] <= largura[1], f"{nome}: nada passa da largura", largura)
        pg.locator("#oportunidades").screenshot(path=f"{SP}/shots/op-invest-{nome}.png")
        pg.close()
    print("ERROS", erros)
    b.close()
srv.shutdown()
