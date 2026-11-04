"""Refaz as capturas de tela do README (docs/*.png) a partir da prévia, com os dados de exemplo (inventados).
Uso: python3 tools/montar_previa.py && python3 tools/capturas_docs.py   (precisa do playwright)

Celular de 390x844 (PNG 780x1688), tema escuro. O relógio fica parado em DIA, para as capturas saírem iguais a cada vez:
o exemplo é montado a partir de hoje, e a Cor do dia desse dia é o Azul, a cor do GerencIA."""
import os
from playwright.sync_api import sync_playwright

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIA = "file://" + os.path.join(RAIZ, "preview", "gerencia-previa.html")
DOCS = os.path.join(RAIZ, "docs")
DIA = "2026-11-18T10:00:00-03:00"
# o aviso "Exemplo. Estes valores são de demonstração" só existe na prévia
SEM_AVISO = ".exemplo { display: none !important; }"

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, color_scheme="dark",
                    locale="pt-BR", timezone_id="America/Sao_Paulo")
    pg.clock.set_fixed_time(DIA)
    pg.goto(PREVIA)
    pg.add_style_tag(content=SEM_AVISO)
    pg.wait_for_timeout(1500)
    tirar = lambda nome: (pg.wait_for_timeout(700), pg.screenshot(path=os.path.join(DOCS, nome)))
    tirar("inicio.png")
    pg.click('#nav [data-v="caixa"]')
    pg.wait_for_timeout(400)
    pg.get_by_role("button", name="Fluxo", exact=True).first.click()
    tirar("caixa.png")
    pg.click('#nav [data-v="investimentos"]')
    pg.wait_for_timeout(400)
    pg.get_by_role("button", name="Evolução", exact=True).first.click()
    tirar("invest.png")
    # Conversar com a IA, no Início: uma pergunta e um gasto, com o cartão de Confirmar
    pg.click('#nav [data-v="inicio"]')
    pg.wait_for_timeout(400)
    pg.locator('.cab [data-a="chat"]').first.click()
    pg.wait_for_selector(".ch-vazio")
    for texto in ["Quais são as próximas contas?", "Gastei 45 no mercado no cartão"]:
        pg.fill("#ch-txt", texto)
        pg.click('[data-a="ch-enviar"]')
        pg.wait_for_timeout(1200)
    tirar("chat.png")
    b.close()
print("capturas em", DOCS)
