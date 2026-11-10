"""A tela do chat com a IA (o balão ao lado do microfone): abrir, conversar, ditar, as ações com Confirmar e Editar,
o Voltar do celular, apagar a conversa e o interruptor Usar IA. Na prévia (apiDemo), com respostas de exemplo;
onde precisa, a api é trocada por uma falsa que guarda o que foi enviado. Dados inventados."""
import unittest

from tests.tela_base import Tela, base, BANCOS

LUZ = {"id": "l-luz", "tipo": "despesa", "descricao": "Luz", "valor": 180, "data": "2026-11-20", "categoria": "c-contas"}
CDB = {"id": "i1", "nome": "CDB Azul", "banco": "b-azul", "valor": 1000, "indexador": "parado", "taxa": 0, "tipo": "cdb", "data_valor": "2026-11-02"}


def dados(**mais):
    return base(bancos=BANCOS, lancamentos=[dict(LUZ)], investimentos=[dict(CDB)], **mais)


class TelaChat(Tela):
    def abrir(self, d=None, ui=None, bens=None, conversa=()):
        super().abrir(d if d is not None else dados(), ui, bens)
        self.js("(T.CHAT_DEMO.length = 0, T.CHAT_DEMO.push(...a), true)", list(conversa))

    def abrir_chat(self, onde=".cab-topo"):
        self.clicar(f'{onde} [data-a="chat"]')
        self.pg.wait_for_function("window.GERENCIA_TESTE.CH && window.GERENCIA_TESTE.CH.msgs")
        self.esperar()

    def enviar(self, texto, enter=False):
        self.preencher("#ch-txt", texto)
        if enter:
            self.pg.press("#ch-txt", "Enter")
        else:
            self.clicar('[data-a="ch-enviar"]')
        self.pg.wait_for_function("!window.GERENCIA_TESTE.CH || !window.GERENCIA_TESTE.CH.enviando")
        self.esperar()

    def bolhas(self):
        return [t.strip() for t in self.textos(".ch-msg .ch-bolha")]

    def confirmar(self, n=-1):
        self.pg.locator('[data-a="ch-ok"]').nth(n).click()
        self.esperar()
        self.pg.wait_for_function("!document.querySelector('.ch-acao [data-a=\"ch-ok\"]') || true")
        self.esperar()

    def falsa(self, metodo, js):
        """Troca um método da api por uma função (texto JS); o original volta no fim do teste."""
        self.js(f"(window.__orig_{metodo} = window.__orig_{metodo} || T.api.{metodo}, T.api.{metodo} = {js}, true)")
        self.addCleanup(lambda: self.js(f"(T.api.{metodo} = window.__orig_{metodo}, true)"))


# ---------------------------------------------------------------------------------------------------------------
class TestBotao(TelaChat):
    def test_ao_lado_do_microfone(self):
        self.abrir()
        self.assertEqual([b.get_attribute("data-a") for b in self.pg.locator(".cab-topo button").all()], ["chat", "falar"])

    def test_em_todas_as_abas(self):
        self.abrir()
        for aba in ("inicio", "caixa", "investimentos", "mais"):
            self.ir(aba)
            self.assertEqual(self.conta('.cab-topo [data-a="chat"]'), 1, aba)

    def test_some_com_a_ia_desligada(self):
        self.abrir(dados(ajustes={"ia": False}))
        self.assertEqual(self.conta('[data-a="chat"]'), 0)

    def test_no_computador_nas_acoes_do_topo(self):
        self.abrir()
        self.assertEqual(self.conta('.top-acts [data-a="chat"]'), 1)


class TestComputador(TelaChat):
    LARGURA, ALTURA = 1280, 800

    def test_abre_pelo_alto_a_direita(self):
        self.abrir()
        self.abrir_chat(".top-acts")
        self.assertEqual(self.folha(), "Conversar com a IA")
        caixa = self.pg.locator("#folhas .folha").bounding_box()
        self.assertLess(caixa["width"], 1280 - 200, "janela no meio, não a tela toda")


# ---------------------------------------------------------------------------------------------------------------
class TestConversar(TelaChat):
    def test_abre_vazia_com_sugestoes_da_aba(self):
        self.abrir(ui={"tab": "investimentos"})
        self.abrir_chat()
        self.assertEqual(self.folha(), "Conversar com a IA")
        self.assertIn("Quanto rende a carteira por mês?", self.textos(".ch-sug .chip"))
        self.assertEqual(self.conta('[data-a="ch-nova"]'), 0, "sem conversa, sem Nova conversa")

    def test_sugestao_vira_pergunta(self):
        self.abrir()
        self.abrir_chat()
        self.clicar('.ch-sug .chip:has-text("Quais contas vencem esta semana?")')
        self.pg.wait_for_function("!window.GERENCIA_TESTE.CH.enviando")
        self.esperar()
        b = self.bolhas()
        self.assertEqual(b[0], "Quais contas vencem esta semana?")
        self.assertIn("Luz: R$ 180,00, 20/11", b[1])

    def test_enviar_com_o_botao_e_com_enter(self):
        self.abrir()
        self.abrir_chat()
        self.enviar("qual o saldo do caixa?")
        self.enviar("e as contas?", enter=True)
        self.assertEqual(self.bolhas()[0::2], ["qual o saldo do caixa?", "e as contas?"])
        self.assertEqual(self.pg.input_value("#ch-txt"), "", "o campo limpa")

    def test_botao_enviar_so_com_texto(self):
        self.abrir()
        self.abrir_chat()
        self.assertTrue(self.pg.locator('[data-a="ch-enviar"]').is_disabled())
        self.preencher("#ch-txt", "  ")
        self.assertTrue(self.pg.locator('[data-a="ch-enviar"]').is_disabled())
        self.preencher("#ch-txt", "oi")
        self.assertFalse(self.pg.locator('[data-a="ch-enviar"]').is_disabled())

    def test_shift_enter_quebra_a_linha(self):
        self.abrir()
        self.abrir_chat()
        self.pg.click("#ch-txt")
        self.pg.keyboard.type("linha 1")
        self.pg.keyboard.press("Shift+Enter")
        self.pg.keyboard.type("linha 2")
        self.assertEqual(self.pg.input_value("#ch-txt"), "linha 1\nlinha 2")
        self.assertEqual(self.conta(".ch-msg"), 0, "não enviou")

    def test_mostra_pensando_enquanto_espera(self):
        self.abrir()
        self.abrir_chat()
        self.falsa("chatEnviar", "() => new Promise(r => { window.__soltar = () => r({ mensagens: [] }); })")
        self.preencher("#ch-txt", "oi")
        self.clicar('[data-a="ch-enviar"]')
        self.assertEqual(self.conta(".ch-pensando"), 1)
        self.assertEqual(self.bolhas()[0], "oi", "a pergunta aparece na hora")
        self.assertTrue(self.pg.locator("#ch-txt").is_enabled())
        self.js("(window.__soltar(), true)")
        self.pg.wait_for_function("!window.GERENCIA_TESTE.CH.enviando")
        self.esperar()
        self.assertEqual(self.conta(".ch-pensando"), 0)

    def test_manda_a_tela_e_a_aba(self):
        self.abrir(ui={"tab": "caixa"})
        self.abrir_chat()
        self.falsa("chatEnviar", "c => (window.__corpo = c, Promise.resolve({ mensagens: [] }))")
        self.enviar("o que é isso?")
        c = self.js("window.__corpo")
        self.assertEqual((c["texto"], c["aba"], c["fala"]), ("o que é isso?", "caixa", False))
        self.assertIn("Caixa", c["tela"])
        self.assertLessEqual(len(c["tela"]), 3000)

    def test_erro_devolve_o_texto_para_o_campo(self):
        self.abrir()
        self.abrir_chat()
        self.falsa("chatEnviar", "() => Promise.reject(new Error('A IA não respondeu.'))")
        self.enviar("quanto gastei?")
        self.assertEqual(self.texto(".ch-pe .msg-erro"), "A IA não respondeu.")
        self.assertEqual(self.pg.input_value("#ch-txt"), "quanto gastei?")
        self.assertEqual(self.conta(".ch-msg"), 0, "a pergunta que não foi sai da conversa")

    def test_conversa_guardada_abre_de_onde_parou(self):
        self.abrir(conversa=[{"id": "m1", "papel": "eu", "texto": "oi"}, {"id": "m2", "papel": "ia", "texto": "Olá, Ana!"}])
        self.abrir_chat()
        self.assertEqual(self.bolhas(), ["oi", "Olá, Ana!"])
        self.assertEqual(self.conta(".ch-sug"), 0)
        corpo = self.pg.locator("#folhas .folha-corpo")
        self.assertGreaterEqual(corpo.evaluate("e => e.scrollTop + e.clientHeight"), corpo.evaluate("e => e.scrollHeight") - 2, "rola até a última mensagem")

    def test_erro_ao_abrir(self):
        self.abrir()
        self.falsa("chat", "() => Promise.reject(new Error('fora do ar'))")
        self.clicar('.cab-topo [data-a="chat"]')
        self.pg.wait_for_function("window.GERENCIA_TESTE.CH && window.GERENCIA_TESTE.CH.msgs")
        self.esperar()
        self.assertEqual(self.texto(".ch-pe .msg-erro"), "Não consegui abrir a conversa. fora do ar")

    def test_falada_tem_o_microfone_na_bolha(self):
        self.abrir(conversa=[{"id": "m1", "papel": "eu", "texto": "oi", "fala": True}, {"id": "m2", "papel": "eu", "texto": "tchau"}])
        self.abrir_chat()
        self.assertEqual([self.pg.locator(".ch-msg.eu").nth(i).locator(".ic-s").count() for i in range(2)], [1, 0])


class TestTextoDaIA(TelaChat):
    def fmt(self, t):
        return self.js("T.fmtIA(a)", t)

    def test_negrito_lista_e_paragrafos(self):
        self.abrir()
        self.assertEqual(self.fmt("Seu saldo é **R$ 10**.\n\nContas:\n- Luz\n- Água\nFim"),
                         "<p>Seu saldo é <b>R$ 10</b>.</p><p>Contas:</p><ul><li>Luz</li><li>Água</li></ul><p>Fim</p>")

    def test_html_da_ia_nao_entra(self):
        self.abrir()
        self.assertEqual(self.fmt('<img src=x onerror="alert(1)"> **<b>oi</b>**'), "<p>&lt;img src=x onerror=&quot;alert(1)&quot;&gt; <b>&lt;b&gt;oi&lt;/b&gt;</b></p>")

    def test_texto_da_pessoa_escapado(self):
        self.abrir(conversa=[{"id": "m1", "papel": "eu", "texto": "<i>oi</i>\nlinha"}])
        self.abrir_chat()
        self.assertEqual(self.pg.locator(".ch-msg.eu .ch-bolha").inner_html(), "&lt;i&gt;oi&lt;/i&gt;<br>linha")


# ---------------------------------------------------------------------------------------------------------------
class TestAcoes(TelaChat):
    def test_lancar_confirmar(self):
        self.abrir()
        self.abrir_chat()
        self.enviar("gastei 45 no mercado")
        self.assertEqual(self.texto(".ch-acao-t"), "LANÇAR", "o título do cartão (em maiúsculas pelo estilo)")
        self.assertIn("Mercado", self.texto(".ch-acao"))
        self.assertIn("hoje · Mercado", self.texto(".ch-acao"))
        self.confirmar()
        l = [x for x in self.dados()["lancamentos"] if x["descricao"] == "Mercado"]
        self.assertEqual([(x["valor"], x["data"], x["pago"], x["categoria"], x["conta"]) for x in l], [(45, "2026-11-02", True, "c-mercado", "k-ana")])
        self.assertEqual(self.textos(".ch-feito"), ["Lançado"])
        self.assertEqual(self.aviso(), "Lançado")
        self.assertEqual(self.conta('[data-a="ch-ok"]'), 0, "confirmado não confirma de novo")

    def test_lancar_no_cartao(self):
        self.abrir()
        self.abrir_chat()
        self.enviar("gastei 80 no mercado no cartão")
        self.assertIn("no cartão", self.texto(".ch-acao"))
        self.confirmar()
        l = next(x for x in self.dados()["lancamentos"] if x["descricao"] == "Mercado")
        self.assertEqual((l["cartao"], l["conta"], l["pago"]), (True, "k-ana", False), "no cartão fica para a fatura")

    def test_lancar_editar_abre_a_conferencia_por_cima_e_volta(self):
        self.abrir()
        self.abrir_chat()
        self.enviar("gastei 45 no mercado")
        self.clicar('[data-a="ch-editar"]')
        self.assertEqual((self.folha(), self.niveis()), ("Conferir lançamentos", 2))
        self.clicar('[data-a="ia-salvar"]')
        self.pg.wait_for_timeout(50)
        self.esperar()
        self.assertEqual((self.folha(), self.niveis()), ("Conversar com a IA", 1), "salvar volta para a conversa")
        self.assertEqual(self.textos(".ch-feito"), ["Lançado"])
        self.assertEqual(len([x for x in self.dados()["lancamentos"] if x["descricao"] == "Mercado"]), 1)

    def test_editar_e_voltar_sem_salvar(self):
        self.abrir()
        self.abrir_chat()
        self.enviar("gastei 45 no mercado")
        self.clicar('[data-a="ch-editar"]')
        self.voltar()
        self.assertEqual((self.folha(), self.niveis()), ("Conversar com a IA", 1))
        self.assertEqual(self.conta('[data-a="ch-ok"]'), 1, "a ação continua esperando")
        self.assertFalse(any(x["descricao"] == "Mercado" for x in self.dados()["lancamentos"]))

    def test_repetido_abre_a_conferencia_em_vez_de_lancar(self):
        d = dados()
        d["lancamentos"].append({"id": "m0", "tipo": "despesa", "descricao": "Mercado", "valor": 45, "data": "2026-11-02", "pago": True, "categoria": "c-mercado"})
        self.abrir(d)
        self.abrir_chat()
        self.enviar("gastei 45 no mercado")
        self.confirmar()
        self.assertEqual(self.folha(), "Conferir lançamentos", "parece repetido: mostra para conferir")
        self.assertEqual(len([x for x in self.dados()["lancamentos"] if x["descricao"] == "Mercado"]), 1, "não lançou de novo")

    def test_pagar_confirmar_com_outro_valor(self):
        self.abrir()
        self.abrir_chat()
        self.enviar("paguei a luz, 190 reais")
        cartao = self.texto(".ch-acao")
        self.assertIn("vence 20/11 · conta de R$ 180,00", cartao)
        self.assertIn("R$ 190,00", cartao)
        self.confirmar()
        luz = next(x for x in self.dados()["lancamentos"] if x["id"] == "l-luz")
        self.assertEqual((luz["pago"], luz["valor"]), (True, 190))
        self.assertEqual((self.textos(".ch-feito"), self.aviso()), (["Pago"], "Pagamento confirmado"))

    def test_pagar_editar_abre_confirmar_pagamento(self):
        self.abrir()
        self.abrir_chat()
        self.enviar("paguei a luz")
        self.clicar('[data-a="ch-editar"]')
        self.assertEqual((self.folha(), self.niveis(), self.pg.input_value("#pg-v")), ("Confirmar pagamento", 2, "180,00"))
        self.clicar('[data-a="pg-ok"]')
        self.pg.wait_for_timeout(50)
        self.esperar()
        self.assertEqual((self.folha(), self.textos(".ch-feito")), ("Conversar com a IA", ["Pago"]))

    def test_pagar_fixo_do_mes_ainda_nao_lancado(self):
        d = base(bancos=BANCOS, recorrencias=[{"id": "r-net", "tipo": "despesa", "descricao": "Internet", "valor": 120, "dia": 25, "inicio": "2026-11", "categoria": "c-contas"}])
        self.abrir(d)
        self.abrir_chat()
        self.enviar("paguei a internet")
        self.confirmar()
        l = [x for x in self.dados()["lancamentos"] if x.get("recorrencia") == "r-net"]
        self.assertEqual([(x["competencia"], x["pago"], x["valor"]) for x in l], [("2026-11", True, 120)])

    def test_pagar_conta_ja_paga_avisa(self):
        self.abrir()
        self.abrir_chat()
        self.enviar("paguei a luz")
        self.js("(T.S.d.lancamentos.find(l => l.id === 'l-luz').pago = true, true)")
        self.confirmar()
        self.assertEqual(self.aviso(), "Essa conta não está mais em aberto.")
        self.assertEqual(self.conta('[data-a="ch-ok"]'), 1)

    def test_pagar_fatura(self):
        d = dados()
        d["lancamentos"].append({"id": "k1", "tipo": "despesa", "descricao": "Farmácia", "valor": 60, "data": "2026-10-28", "conta": "k-ana", "cartao": True})
        self.abrir(d)
        self.abrir_chat()
        self.js("""(T.api.__c = T.api.chatEnviar, T.api.chatEnviar = async c => {
            T.CHAT_DEMO.push({ id: 'e1', papel: 'eu', texto: c.texto }, { id: 'a1', papel: 'ia', texto: 'Marco a fatura.',
              acoes: { pagar: [{ id: 'f:k-ana|2026-11-12', descricao: 'Fatura Banco Azul · Ana', vencimento: '2026-11-12', valor_conta: 60, valor: 60, tipo: 'fatura' }] } });
            return { mensagens: JSON.parse(JSON.stringify(T.CHAT_DEMO)) }; }, true)""")
        self.addCleanup(lambda: self.js("(T.api.chatEnviar = T.api.__c, true)"))
        self.enviar("paguei a fatura do azul")
        self.assertEqual(self.texto(".ch-acao-t"), "PAGAR FATURA")
        self.confirmar()
        self.assertTrue(next(x for x in self.dados()["lancamentos"] if x["id"] == "k1")["pago"])
        self.assertEqual(self.aviso(), "Fatura paga")

    def test_um_cartao_por_conta(self):
        self.abrir()
        self.js("""(T.CHAT_DEMO.push({ id: 'a1', papel: 'ia', texto: 'Marco as duas.', acoes: { pagar: [
            { id: 'l-luz', descricao: 'Luz', vencimento: '2026-11-20', valor_conta: 180, valor: 180, tipo: 'conta' },
            { id: 'l-agua', descricao: 'Água', vencimento: '2026-11-21', valor_conta: 90, valor: 90, tipo: 'conta' }] } }), true)""")
        self.abrir_chat()
        self.assertEqual(self.conta(".ch-acao"), 2)
        self.pg.locator('[data-a="ch-ok"]').nth(0).click()
        self.esperar()
        self.pg.wait_for_timeout(50)
        self.assertEqual(self.js("T.CHAT_DEMO[0].estado"), {"pagar.0": "feito"}, "só o primeiro cartão fica pago")
        self.assertEqual(self.conta('[data-a="ch-ok"]'), 1)

    def test_aplicar_no_investimento(self):
        self.abrir()
        self.abrir_chat()
        self.enviar("apliquei 300 no cdb azul")
        self.assertIn("Aplicar em CDB Azul", self.texto(".ch-acao"))
        self.assertIn("R$ 1.000,00 → R$ 1.300,00", self.texto(".ch-acao"))
        self.confirmar()
        self.assertEqual(self.dados()["investimentos"][0]["valor"], 1300)
        self.assertEqual(self.aviso(), "Aporte aplicado")
        self.assertNotIn("→", self.texto(".ch-acao"), "confirmado não recalcula o antes → depois")

    def test_investimento_editar_abre_conferir_investimentos(self):
        self.abrir()
        self.abrir_chat()
        self.enviar("apliquei 300 no cdb azul")
        self.clicar('[data-a="ch-editar"]')
        self.assertEqual((self.folha(), self.niveis()), ("Conferir investimentos", 2))
        self.clicar('[data-a="ia-salvar"]')
        self.pg.wait_for_timeout(50)
        self.esperar()
        self.assertEqual((self.folha(), self.textos(".ch-feito")), ("Conversar com a IA", ["Atualizado"]))
        self.assertEqual(self.dados()["investimentos"][0]["valor"], 1300)

    def test_saldo_novo(self):
        self.abrir()
        self.js("""(T.CHAT_DEMO.push({ id: 'a1', papel: 'ia', texto: 'Atualizo.', acoes: { investimentos: [
            { existente: 'i1', nome: 'CDB Azul', banco: '', tipo: 'cdb', valor: 1500, aporte: 0, indexador: 'parado', taxa: 0, vencimento: '', liquidez: 'vencimento', dono: '', confianca: 'alta' }] } }), true)""")
        self.abrir_chat()
        self.assertIn("Saldo de CDB Azul", self.texto(".ch-acao"))
        self.confirmar()
        self.assertEqual((self.dados()["investimentos"][0]["valor"], self.aviso()), (1500, "Investimento atualizado"))

    def test_cartao_feito_ou_deixado_de_lado_vindo_guardado(self):
        acao = {"lancamentos": [{"tipo": "despesa", "descricao": "Feira", "valor": 30, "data": "2026-11-01", "categoria": "c-mercado"}]}
        self.abrir(conversa=[{"id": "a1", "papel": "ia", "texto": "x", "acoes": acao, "estado": {"lancamentos": "feito"}},
                             {"id": "a2", "papel": "ia", "texto": "y", "acoes": acao, "estado": {"lancamentos": "dispensado"}}])
        self.abrir_chat()
        self.assertEqual(self.textos(".ch-feito"), ["Lançado", "Deixado de lado"])
        self.assertEqual(self.conta('[data-a="ch-ok"]'), 0)

    def test_falha_ao_marcar_nao_desfaz_o_que_foi_feito(self):
        self.abrir()
        self.abrir_chat()
        self.enviar("gastei 45 no mercado")
        self.falsa("chatAcao", "() => Promise.reject(new Error('fora'))")
        self.confirmar()
        self.assertEqual(self.textos(".ch-feito"), ["Lançado"], "o cartão fica marcado aqui")
        self.assertTrue(any(x["descricao"] == "Mercado" for x in self.dados()["lancamentos"]))


# ---------------------------------------------------------------------------------------------------------------
class TestJanela(TelaChat):
    def test_voltar_do_celular_fecha(self):
        self.abrir()
        self.abrir_chat()
        self.voltar()
        self.assertEqual(self.niveis(), 0)

    def test_x_fecha_e_reabrir_mantem_a_conversa(self):
        self.abrir()
        self.abrir_chat()
        self.enviar("oi")
        self.clicar('.folha-cab [data-a="fechar"]')
        self.assertEqual(self.niveis(), 0)
        self.abrir_chat()
        self.assertEqual(self.bolhas()[0], "oi")

    def test_texto_digitado_sobrevive_ao_redesenho(self):
        self.abrir()
        self.abrir_chat()
        self.preencher("#ch-txt", "metade da pergunta")
        self.js("(T.render(), true)")
        self.assertEqual(self.pg.input_value("#ch-txt"), "metade da pergunta")

    def test_nova_conversa_recomeca(self):
        self.abrir(conversa=[{"id": "m1", "papel": "eu", "texto": "oi"}])
        self.abrir_chat()
        self.assertEqual(self.js("document.querySelector('[data-a=\"ch-nova\"]').getAttribute('aria-label')"), "Nova conversa")
        self.clicar('[data-a="ch-nova"]')
        self.pg.wait_for_timeout(30)
        self.esperar()
        self.assertEqual((self.conta(".ch-msg"), self.conta(".ch-sug .chip"), self.js("T.CHAT_DEMO.length")), (0, 3, 0))
        self.assertEqual(self.folha(), "Conversar com a IA", "continua aberto, vazio")

    def test_sem_mensagens_sem_nova_conversa(self):
        self.abrir()
        self.abrir_chat()
        self.assertEqual(self.conta('[data-a="ch-nova"]'), 0)

    def test_nova_conversa_com_erro_avisa(self):
        self.abrir(conversa=[{"id": "m1", "papel": "eu", "texto": "oi"}])
        self.abrir_chat()
        self.js("(window._limpar = T.api.chatLimpar, T.api.chatLimpar = () => Promise.reject(new Error('sem rede')), true)")
        self.addCleanup(lambda: self.js("(T.api.chatLimpar = window._limpar, true)"))
        self.clicar('[data-a="ch-nova"]')
        self.assertIn("Não consegui começar uma nova conversa. sem rede", self.aviso())
        self.assertEqual(self.bolhas(), ["oi"], "a conversa fica")


class TestDitar(TelaChat):
    def test_sem_voz_sem_microfone(self):
        self.abrir()
        self.js("(T.S.voz = { pronta: false }, true)")
        self.addCleanup(lambda: self.js("(T.S.voz = { pronta: true }, true)"))
        self.abrir_chat()
        self.assertEqual(self.conta('[data-a="ch-mic"]'), 0)

    def test_ditar_manda_como_fala(self):
        self.abrir()
        self.js("(T.S.voz = { pronta: true }, true)")
        self.abrir_chat()
        self.falsa("vozTexto", "() => Promise.resolve({ texto: 'gastei 45 no mercado' })")
        self.js("""(window.__G = T.Gravador, T.Gravador = class { async start() {} segundos() { return 2; } stop() { return new Int16Array(32000); } cancel() {} }, true)""")
        self.addCleanup(lambda: self.js("(T.Gravador = window.__G, true)"))
        self.clicar('[data-a="ch-mic"]')
        self.pg.wait_for_function("window.GERENCIA_TESTE.CH.rec === 'on'")
        self.esperar()
        self.assertTrue(self.pg.locator("#ch-txt").is_disabled(), "enquanto ouve, o campo espera")
        self.assertIn("Ouvindo", self.pg.get_attribute("#ch-txt", "placeholder"))
        self.clicar('[data-a="ch-mic"]')
        self.pg.wait_for_function("window.GERENCIA_TESTE.CH.msgs.length >= 2 && !window.GERENCIA_TESTE.CH.enviando")
        self.esperar()
        self.assertEqual(self.bolhas()[0], "gastei 45 no mercado")
        self.assertEqual(self.js("T.CHAT_DEMO[0].fala"), True)

    def test_microfone_bloqueado_explica(self):
        self.abrir()
        self.js("(T.S.voz = { pronta: true }, true)")
        self.abrir_chat()
        self.js("""(window.__G = T.Gravador, window.__D = T.DEMO, T.Gravador = class { async start() { throw Object.assign(new Error('x'), { name: 'NotAllowedError' }); } cancel() {} }, true)""")
        self.addCleanup(lambda: self.js("(T.Gravador = window.__G, true)"))
        # na prévia ele seguiria com o simulado; aqui vale a mensagem do app (DEMO não muda; só confere o texto do erro)
        self.assertIn("O microfone está bloqueado", self.js("T.erroMicrofone({ name: 'NotAllowedError' })"))

    def test_nada_ouvido(self):
        self.abrir()
        self.js("(T.S.voz = { pronta: true }, true)")
        self.abrir_chat()
        self.js("""(window.__G = T.Gravador, T.Gravador = class { async start() {} segundos() { return 0; } stop() { return new Int16Array(10); } cancel() {} }, true)""")
        self.addCleanup(lambda: self.js("(T.Gravador = window.__G, true)"))
        self.clicar('[data-a="ch-mic"]')
        self.pg.wait_for_function("window.GERENCIA_TESTE.CH.rec === 'on'")
        self.clicar('[data-a="ch-mic"]')
        self.assertEqual(self.texto(".ch-pe .msg-erro"), "Não ouvi nada. Toque no microfone e fale.")
        self.assertEqual(self.conta(".ch-msg"), 0)

    def test_fechar_enquanto_ouve_desliga_o_microfone(self):
        self.abrir()
        self.js("(T.S.voz = { pronta: true }, window.__cancelou = 0, true)")
        self.abrir_chat()
        self.js("""(window.__G = T.Gravador, T.Gravador = class { async start() {} segundos() { return 1; } stop() { return new Int16Array(0); } cancel() { window.__cancelou++; } }, true)""")
        self.addCleanup(lambda: self.js("(T.Gravador = window.__G, true)"))
        self.clicar('[data-a="ch-mic"]')
        self.pg.wait_for_function("window.GERENCIA_TESTE.CH.rec === 'on'")
        self.voltar()
        self.assertEqual((self.niveis(), self.js("window.__cancelou"), self.js("T.CHG")), (0, 1, None))


if __name__ == "__main__":
    unittest.main()
