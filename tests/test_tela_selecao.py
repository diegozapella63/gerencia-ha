"""As caixas de seleção (1.30.0): www/selectsheet.js, o mesmo arquivo dos outros apps da família.

Uma caixa (<select>) não abre a janela padrão do celular: abre uma janela no visual do app, de baixo para cima, com as
opções em linhas e a atual marcada na cor do app. Escolher entra na própria caixa (o app ouve o change de sempre); o
Voltar do celular, o X e tocar fora fecham só ela, e o Voltar seguinte é o do app. No computador, no meio da tela.
Dados sempre inventados (Ana, Beto, Banco Azul).
"""
import unittest

from tests.tela_base import Tela, base, sync_playwright

IAS = "{pronta: true, selecionada: '', entidades: [{id: 'ai_task.google_ai_task', nome: 'Google AI Task', imagens: true}, {id: 'ai_task.ollama_ai_task', nome: 'Ollama AI Task', imagens: false}]}"


@unittest.skipUnless(sync_playwright, "precisa do playwright")
class Selecao(Tela):
    def setUp(self):
        self.abrir(base())
        self.ir_mais("config", "integracoes")
        self.js(f"(T.S.ia = {IAS}, T.render(), true)")
        self.esperar()

    def tearDown(self):
        # nenhuma janela de caixa aberta para o próximo teste
        self.pg.evaluate("() => window.__selectSheet && window.__selectSheet.isOpen() && window.__selectSheet.close()")
        self.pg.wait_for_timeout(500)
        super().tearDown()

    def tocar(self, sel):
        loc = self.pg.locator(sel).first
        loc.scroll_into_view_if_needed()
        bx = loc.bounding_box()
        self.pg.mouse.click(bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2)
        self.pg.wait_for_timeout(350)
        self.esperar()

    def aberta(self):
        return self.conta(".ss-wrap.in .ss-sheet") == 1

    def test_abre_a_janela_do_app(self):
        caixa = self.pg.locator("#ia-ent")
        self.assertEqual(caixa.evaluate("s => getComputedStyle(s).pointerEvents"), "none", "a caixa nunca recebe o toque")
        self.tocar("#ia-ent")
        self.assertTrue(self.aberta())
        self.assertEqual(self.texto(".ss-head b"), "IA usada pelo app", "o título vem do rótulo da caixa")
        self.assertEqual(self.textos(".ss-opt"), ["Padrão do Home Assistant", "Google AI Task", "Ollama AI Task (só texto)"])
        self.assertEqual(self.textos(".ss-opt.on"), ["Padrão do Home Assistant"], "a atual marcada")
        cores = self.js("""(() => { const s = document.querySelector('.ss-sheet'), c = getComputedStyle(document.documentElement);
          return [getComputedStyle(s).backgroundColor, getComputedStyle(s.querySelector('.ss-opt.on svg')).color,
                  c.getPropertyValue('--card').trim(), c.getPropertyValue('--accent').trim()]; })()""")
        hexa = lambda h: "rgb(%d, %d, %d)" % tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        self.assertEqual(cores[0], hexa(cores[2]), "o fundo das janelas do app")
        self.assertEqual(cores[1], hexa(cores[3]), "a marca na cor do app")
        bx = self.pg.locator(".ss-sheet").bounding_box()
        self.assertLess(abs(bx["y"] + bx["height"] - self.ALTURA), 2, "de baixo para cima")

    def test_escolher_entra_na_caixa_e_o_app_salva(self):
        self.tocar("#ia-ent")
        self.clicar(".ss-opt >> text=Ollama AI Task")
        self.pg.wait_for_timeout(400)
        self.esperar()
        self.assertEqual(self.conta(".ss-wrap"), 0, "escolher fecha")
        self.assertEqual(self.dados()["ajustes"]["ia_entidade"], "ai_task.ollama_ai_task", "o change de sempre: o app salva")
        self.assertIn("IA escolhida", self.aviso() or "")

    def test_voltar_x_e_tocar_fora_fecham_so_ela(self):
        tela = self.js("T.S.ui.maisTela")
        for como in ("voltar", "x", "fora"):
            self.tocar("#ia-ent")
            self.assertTrue(self.aberta(), como)
            if como == "voltar":
                self.voltar()
                self.pg.wait_for_timeout(300)
            elif como == "x":
                self.tocar(".ss-x")
            else:
                self.pg.mouse.click(195, 40)
                self.pg.wait_for_timeout(350)
            self.assertEqual(self.conta(".ss-wrap"), 0, f"{como}: fechou")
            self.assertEqual(self.js("T.S.ui.maisTela"), tela, f"{como}: continua na mesma tela")
            self.assertEqual(self.dados()["ajustes"].get("ia_entidade", ""), "", f"{como}: nada mudou")
        self.voltar()
        self.assertEqual(self.js("T.S.ui.maisTela"), "", "o Voltar seguinte é o do app: o menu do Mais")

    def test_dentro_de_uma_janela_do_app(self):
        """Uma caixa numa janela do app (Como é pago, na Nova despesa): o Voltar fecha só a caixa, e o seguinte, a janela."""
        sal = dict(id="r-sal", tipo="receita", descricao="Salário", valor=5000, dia=5, inicio="2026-01")
        self.abrir(base(recorrencias=[sal]), ui={"tab": "caixa"})
        self.clicar('#nav [data-a="novo"]')
        self.assertEqual(self.conta("#lf-vinc"), 1, "Como é pago, com o salário")
        titulo = self.folha()
        self.tocar("#lf-vinc")
        self.assertTrue(self.aberta())
        self.voltar()
        self.pg.wait_for_timeout(300)
        self.assertEqual(self.conta(".ss-wrap"), 0)
        self.assertEqual(self.folha(), titulo, "a janela do app continua aberta")
        self.tocar("#lf-vinc")
        self.clicar(".ss-opt >> text=Descontado de: Salário")
        self.pg.wait_for_timeout(400)
        self.esperar()
        self.assertEqual(self.pg.locator("#lf-vinc").input_value(), "r-sal", "a escolha entra na caixa da janela")
        self.assertIn("Fica pago junto com Salário", self.folha_texto(), "e o app ouve o change")
        self.voltar()
        self.assertIsNone(self.folha(), "o Voltar seguinte fecha a janela do app")


@unittest.skipUnless(sync_playwright, "precisa do playwright")
class SelecaoComputador(Tela):
    def tearDown(self):
        self.pg.set_viewport_size({"width": self.LARGURA, "height": self.ALTURA})
        super().tearDown()

    def test_no_meio_e_pelo_teclado(self):
        self.abrir(base())
        self.ir_mais("config", "integracoes")
        self.pg.set_viewport_size({"width": 1200, "height": 800})
        self.pg.wait_for_timeout(300)
        self.js(f"(T.S.ia = {IAS}, T.render(), true)")
        self.esperar()
        caixa = self.pg.locator("#ia-ent")
        caixa.scroll_into_view_if_needed()
        bx = caixa.bounding_box()
        self.pg.mouse.click(bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2)
        self.pg.wait_for_timeout(350)
        sb = self.pg.locator(".ss-wrap.in .ss-sheet").bounding_box()
        self.assertLess(abs(sb["x"] + sb["width"] / 2 - 600), 2)
        self.assertLess(abs(sb["y"] + sb["height"] / 2 - 400), 2)
        self.assertLessEqual(sb["width"], 440)
        self.pg.keyboard.press("Escape")
        self.pg.wait_for_timeout(400)
        self.assertEqual(self.conta(".ss-wrap"), 0)
        self.assertTrue(caixa.evaluate("s => document.activeElement === s"), "o foco volta para a caixa")
        self.pg.keyboard.press("Enter")
        self.pg.wait_for_timeout(300)
        self.pg.keyboard.press("ArrowDown")
        self.pg.keyboard.press("Enter")
        self.pg.wait_for_timeout(600)
        self.esperar()
        self.assertEqual(self.dados()["ajustes"]["ia_entidade"], "ai_task.google_ai_task")


if __name__ == "__main__":
    unittest.main()
