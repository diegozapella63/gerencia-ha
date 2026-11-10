"""A área Caixa na tela (gerencia/app/www/app.js), do jeito que a pessoa usa: tocar, digitar, salvar e conferir.

Nova despesa, Novo recebimento e Novo aporte, editar e apagar, cartão e faturas, parcelas, fixos (todo mês e todo ano),
salário com descontos na fonte, despesa descontada do salário, Paguei/Recebi/Apliquei, Ajustar saldo, a lista do mês
(meses, filtros, números do topo, saldo), Categorias, Fluxo e os avisos de contas no Início.

Os cálculos puros (saldo, resumo do mês, faturas, materializar...) já estão em tests/test_tela.py: aqui é a tela.
O relógio está parado em 02/11/2026 (segunda-feira); o Banco Azul tem os cartões da Ana (fecha 5, vence 12) e do Beto
(fecha 25, vence 5) e o Banco Verde, uma conta da Ana sem cartão (tests/tela_base.py). Dados sempre inventados.

Os testes marcados com @unittest.expectedFailure esperam o certo e falham hoje: são bugs suspeitos (veja o "BUG:").
"""
import unittest

from tests.tela_base import Tela, base, BANCOS


def desp(id, descricao, valor, data, pago=False, **mais):
    return dict(id=id, tipo="despesa", descricao=descricao, valor=valor, data=data, pago=pago, **mais)


def rec(id, descricao, valor, data, pago=False, **mais):
    return dict(id=id, tipo="receita", descricao=descricao, valor=valor, data=data, pago=pago, **mais)


def fixo(id, descricao, valor, dia, inicio, tipo="despesa", **mais):
    return dict(id=id, tipo=tipo, descricao=descricao, valor=valor, dia=dia, inicio=inicio, **mais)


LUZ = fixo("r-luz", "Luz", 150, 10, "2026-01", categoria="c-contas")
SAL_FIXO = fixo("r-sal", "Salário", 5000, 5, "2026-01", tipo="receita", conta="k-verde", categoria="c-salario")
PLANO = fixo("r-plano", "Plano de saúde", 400, 20, "2026-01", categoria="c-saude", vinculo="r-sal")
INSS = {"id": "x-inss", "descricao": "INSS", "modo": "pct", "valor": 11, "base": "", "categoria": "c-impostos"}


_PAGINA = {}  # um Chromium só para todas as classes deste arquivo (abrir um por classe custava ~0,6 s cada)


def tearDownModule():
    if _PAGINA:
        _PAGINA["b"].close()
        _PAGINA["pw"].stop()
        _PAGINA.clear()


class Caixa(Tela):
    """Ajudantes da área Caixa (sem testes aqui)."""

    @classmethod
    def setUpClass(cls):
        if not _PAGINA:
            super().setUpClass()
            # "reduzir movimento" do celular: o app tira as animações (styles.css) e o clique não espera a janela parar de subir
            cls.pg.emulate_media(reduced_motion="reduce")
            _PAGINA.update(pw=cls.pw, b=cls.b, ctx=cls.ctx, pg=cls.pg, erros=cls.erros)
        for k, v in _PAGINA.items():
            setattr(cls, k, v)

    @classmethod
    def tearDownClass(cls):
        pass  # o navegador fecha no fim do arquivo (tearDownModule)

    def tearDown(self):
        # a janela que ia se redesenhar sozinha (depois de digitar) não se redesenha no meio do próximo teste
        self.js("(clearTimeout(T.pfT), true)")
        super().tearDown()

    def caixa(self, ui=None, **dados):
        """Abre o app na aba Caixa com os bancos de exemplo e estes dados."""
        # descAberto (os descontos de um recebimento abertos na lista) não está no estado inicial da base: volta fechado
        self.abrir(base(bancos=BANCOS, **dados), ui=dict({"tab": "caixa", "descAberto": None}, **(ui or {})))

    def nova(self, tipo="despesa"):
        """O Adicionar da aba Caixa (abre a Nova despesa) e, se pedir, troca para Recebimento ou Aporte."""
        self.clicar('#nav [data-a="novo"]')
        if tipo != "despesa":
            self.clicar(f'.folha [data-a="lf-tipo"][data-v="{tipo}"]')

    def redesenhar(self):
        """Depois de digitar a data, as vezes ou uma descrição conhecida, a janela se redesenha sozinha logo depois: agora."""
        self.js("(clearTimeout(T.pfT), T.FOLHA && T.pintarFolha(), true)")

    def data(self, valor):
        self.preencher('#lf-data', valor)
        self.redesenhar()

    def salvar(self, alcance=None):
        """Salvar (no fixo: alcance 'este' para Só este mês, 'todos' para Todos os meses)."""
        self.clicar(f'.folha [data-a="lf-salvar"][data-v="{alcance}"]' if alcance else '.folha [data-a="lf-salvar"]:not([data-mais])')

    def situacao(self):
        return self.texto('.folha [data-a="lf-pago"].on')

    def marcados(self, sel):
        """Os botões escolhidos (acesos) na janela."""
        return self.textos(f'.folha {sel}.on')

    def categoria(self, id):
        self.clicar(f'.folha [data-a="lf-set"][data-k="categoria"][data-v="{id}"]')

    def repetir(self, como):
        self.clicar(f'.folha [data-a="lf-set"][data-k="repete"][data-v="{como}"]')

    def lanc(self, id):
        return next(l for l in self.dados()["lancamentos"] if l["id"] == id)

    def lancs(self):
        return sorted(self.dados()["lancamentos"], key=lambda l: (l["data"], l["descricao"]))

    def ids(self):
        """Os lançamentos soltos na lista do caixa, na ordem da tela (sem os de dentro das faturas e dos recebimentos)."""
        return self.js("[...document.querySelectorAll('.cx-lista > .lanc[data-a=\"lanc\"]')].map(e => e.dataset.id)")

    def faturas(self):
        return self.textos('.cx-lista > .lanc.fatura')

    def mes(self, n):
        """Anda n meses na lista (negativo: para trás)."""
        for _ in range(abs(n)):
            self.clicar(f'[data-a="cx-mes"][data-v="{1 if n > 0 else -1}"]')

    def excluir(self):
        self.clicar('.folha [data-a="lf-excluir"]')

    def opcoes(self):
        return self.textos('.folha-pe [data-a="escolha"]')

    def desfazer(self):
        """O Desfazer do aviso de baixo (depois de um Apagar)."""
        self.assertEqual(self.js("(b => b && b.textContent)(document.querySelector('#toast.on .toast-a'))"), "Desfazer")
        self.clicar('#toast .toast-a')
        self.esperar()

    def escolher(self, rotulo):
        ops = self.opcoes()
        self.assertIn(rotulo, ops, "a opção existe")
        self.clicar('.folha-pe [data-a="escolha"]', ops.index(rotulo))

    def resumo(self):
        """Os números do topo do mês (Entrou, Saiu, Sobrou) e as linhas pequenas embaixo deles."""
        return self.pg.locator('.cx-resumo b').all_text_contents(), self.pg.locator('.cx-resumo small').all_text_contents()


# ---------------------------------------------------------------------------------------------------------------
class TestNovoLancamento(Caixa):
    """Nova despesa, Novo recebimento e Novo aporte: o que já vem preenchido, os erros e o que fica salvo."""

    def test_adicionar_no_caixa_abre_nova_despesa_de_hoje(self):
        self.caixa()
        self.clicar('#nav [data-a="novo"]')
        self.assertEqual(self.folha(), "Nova despesa")
        self.assertEqual(self.pg.input_value('#lf-data'), "2026-11-02", "a data começa em hoje")
        self.assertEqual(self.pg.input_value('#lf-valor'), "", "o valor começa vazio")
        self.assertEqual(self.marcados('[data-a="lf-set"][data-k="repete"]'), ["Uma vez"])

    def test_salvar_sem_valor_mostra_erro_e_nao_lanca(self):
        self.caixa()
        self.nova()
        self.salvar()
        self.assertEqual(self.folha(), "Nova despesa", "a janela continua aberta")
        self.assertEqual(self.textos('.folha .msg-erro'), ["Coloque o valor."])
        self.assertEqual(self.conta('.folha .pref.erro'), 1, "o campo do valor fica marcado")
        self.assertEqual(self.dados()["lancamentos"], [], "nada foi lançado")

    def test_despesa_de_hoje_comeca_paga(self):
        self.caixa()
        self.nova()
        self.assertEqual(self.situacao(), "Pago")
        self.digitar('#lf-valor', '2500')
        self.salvar()
        self.assertTrue(self.dados()["lancamentos"][0]["pago"], "gravada como paga")

    def test_despesa_com_data_futura_fica_a_pagar(self):
        self.caixa()
        self.nova()
        self.data("2026-11-20")
        self.assertEqual(self.situacao(), "A pagar", "vence depois de hoje: a pagar")
        self.digitar('#lf-valor', '9990')
        self.salvar()
        l = self.dados()["lancamentos"][0]
        self.assertEqual((l["data"], l["pago"], l["valor"]), ("2026-11-20", False, 99.9))

    def test_categorias_acompanham_o_tipo(self):
        self.caixa()
        self.nova()
        cats = lambda: self.textos('.folha [data-a="lf-set"][data-k="categoria"]')
        self.assertIn("Mercado", cats(), "na despesa, as categorias de gasto")
        self.assertNotIn("Salário", cats(), "sem as de recebimento")
        self.categoria("c-mercado")
        self.clicar('.folha [data-a="lf-tipo"][data-v="receita"]')
        self.assertEqual(cats(), ["Salário", "Freelance", "Rendimentos", "Vendas", "Reembolso", "Outros recebimentos"], "no recebimento, só as de recebimento")
        self.assertEqual(self.marcados('[data-a="lf-set"][data-k="categoria"]'), [], "a categoria de gasto não passa para o recebimento")

    def test_sem_descricao_usa_o_nome_da_categoria(self):
        self.caixa()
        self.nova()
        self.digitar('#lf-valor', '4590')
        self.assertEqual(self.pg.input_value('#lf-valor'), "45,90", "os números entram como centavos")
        self.categoria("c-mercado")
        self.salvar()
        l = self.dados()["lancamentos"][0]
        self.assertEqual((l["descricao"], l["categoria"], l["valor"]), ("Mercado", "c-mercado", 45.9))
        self.assertEqual(self.aviso(), "Lançado")
        self.assertIsNone(self.folha(), "a janela fecha")

    def test_descricao_ja_usada_traz_categoria_e_conta(self):
        self.caixa(lancamentos=[
            desp("l1", "Padaria Sol", 12.5, "2026-10-01", True, categoria="c-mercado", conta="k-beto", cartao=True),
            desp("l2", "Farmácia", 40, "2026-10-20", True, categoria="c-saude", conta="k-verde")])
        self.nova()
        self.assertEqual(self.marcados('[data-a="lf-conta"]'), ["Banco Verde · Ana"], "começa na conta da última despesa")
        self.preencher('#lf-desc', 'padaria sol')
        self.redesenhar()
        self.assertEqual(self.marcados('[data-a="lf-set"][data-k="categoria"]'), ["Mercado"], "a categoria da última Padaria Sol")
        self.assertEqual(self.marcados('[data-a="lf-conta"]'), ["Banco Azul · Beto"], "a conta da última Padaria Sol")
        self.assertEqual(self.marcados('[data-a="lf-cartao"]'), ["Cartão de crédito"], "no cartão, como da outra vez")

    def test_1_57_sem_cartao_de_debito_e_pix(self):
        bancos = [dict(BANCOS[0], contas=[dict(BANCOS[0]["contas"][0], debito=False), BANCOS[0]["contas"][1]]), BANCOS[1]]
        self.abrir(base(bancos=bancos), ui={"tab": "caixa"})
        self.nova()
        self.clicar('.folha [data-a="lf-conta"][data-v="k-ana"]')
        self.assertEqual(self.textos('.folha [data-a="lf-cartao"]'), ["Pix", "Cartão de crédito"], "a conta da Ana não tem cartão de débito")
        self.clicar('.folha [data-a="lf-conta"][data-v="k-beto"]')
        self.assertEqual(self.textos('.folha [data-a="lf-cartao"]'), ["Débito ou Pix", "Cartão de crédito"], "a do Beto tem")

    def test_categoria_nova_criada_no_formulario(self):
        self.caixa()
        self.nova()
        self.digitar('#lf-valor', '30000')
        self.clicar('.folha [data-a="lf-cat-nova"]')
        self.preencher('.folha [data-lf="novaCat"]', 'Viagens')
        self.clicar('.folha [data-a="lf-cat-ok"]')
        self.assertEqual(self.marcados('[data-a="lf-set"][data-k="categoria"]'), ["Viagens"], "a categoria nova já fica escolhida")
        self.salvar()
        d = self.dados()
        nova = [c for c in d["categorias"] if c["nome"] == "Viagens"]
        self.assertEqual([c["tipo"] for c in nova], ["despesa"], "uma categoria de gasto, criada uma vez")
        self.assertEqual(d["lancamentos"][0]["categoria"], nova[0]["id"])

    def test_novo_aporte_nasce_a_aplicar_e_todo_mes(self):
        self.abrir(base(bancos=BANCOS))
        self.clicar('#nav [data-a="novo"]')
        self.clicar('.escolhas [data-a="aporte-novo"]')
        self.assertEqual(self.folha(), "Novo aporte")
        self.assertEqual(self.situacao(), "A aplicar", "o compromisso nasce a aplicar")
        self.assertEqual(self.marcados('[data-a="lf-set"][data-k="repete"]'), ["Todo mês"])
        self.digitar('#lf-valor', '80000')
        self.salvar()
        d = self.dados()
        self.assertEqual(d["lancamentos"], [], "nada sai do caixa ainda")
        r = d["recorrencias"][0]
        self.assertEqual((r["aporte"], r["valor"], r["dia"], r["inicio"], r["categoria"], r["descricao"]),
                         (True, 800, 2, "2026-11", "c-investimentos", "Aporte nos investimentos"))
        self.assertEqual(self.aviso(), "Aporte cadastrado: todo mês, também na projeção")


# ---------------------------------------------------------------------------------------------------------------
PADARIA = desp("l1", "Padaria", 12.5, "2026-11-01", True, conta="k-verde", categoria="c-mercado")


class TestEditarExcluir(Caixa):
    def test_tocar_no_lancamento_abre_para_editar(self):
        self.caixa(lancamentos=[PADARIA])
        self.clicar('.lanc[data-id="l1"]')
        self.assertEqual(self.folha(), "Despesa")
        self.assertEqual((self.pg.input_value('#lf-valor'), self.pg.input_value('#lf-desc'), self.pg.input_value('#lf-data')),
                         ("12,50", "Padaria", "2026-11-01"), "com o que foi lançado")
        self.assertEqual(self.marcados('[data-a="lf-conta"]'), ["Banco Verde · Ana"])
        self.assertEqual(self.conta('.folha-cab [data-a="lf-excluir"]'), 1, "com a lixeira")
        self.assertEqual(self.conta('.folha [data-k="repete"]'), 0, "sem o Repetir, que é só do lançamento novo")
        self.assertEqual(self.textos('.folha-pe .btn'), ["Duplicar", "Salvar"])

    def test_editar_muda_o_mesmo_lancamento(self):
        self.caixa(lancamentos=[PADARIA])
        self.clicar('.lanc[data-id="l1"]')
        self.digitar('#lf-valor', '1590')
        self.salvar()
        self.assertEqual([(l["id"], l["valor"], l["descricao"]) for l in self.dados()["lancamentos"]], [("l1", 15.9, "Padaria")], "o mesmo, sem criar outro")
        self.assertEqual(self.aviso(), "Salvo")
        self.assertIn("− R$ 15,90", self.texto('.lanc[data-id="l1"]'))

    def test_excluir_pede_confirmacao_e_apaga(self):
        self.caixa(lancamentos=[PADARIA])
        self.clicar('.lanc[data-id="l1"]')
        self.excluir()
        self.assertEqual(self.folha(), "Apagar lançamento?")
        self.assertIn("Padaria, R$ 12,50.", self.folha_texto())
        self.assertEqual(len(self.dados()["lancamentos"]), 1, "nada apagado antes de confirmar")
        self.clicar('.folha-pe [data-a="confirmar"]')
        self.assertEqual(self.dados()["lancamentos"], [])
        self.assertEqual(self.aviso(), "Lançamento apagado")
        self.assertEqual(self.ids(), [], "sai da lista")

    def test_cancelar_exclusao_nao_apaga(self):
        self.caixa(lancamentos=[PADARIA])
        self.clicar('.lanc[data-id="l1"]')
        self.excluir()
        self.clicar('.folha-pe [data-a="fechar"]')
        self.assertEqual([l["id"] for l in self.dados()["lancamentos"]], ["l1"])
        self.assertEqual(self.ids(), ["l1"])

    # BUG: "Apagar lançamento?" (e "Apagar fixo", "Apagar parcela") abre no lugar da janela do lançamento (confirmar/escolher
    # chamam abrirFolha sem "sobre"), então Cancelar, X e o Voltar do celular fecham tudo. Pelo AGENTS.md, uma janela aberta
    # de dentro de outra volta para ela. Reproduzir: Caixa › tocar num lançamento › lixeira › Cancelar: volta para a tela do
    # caixa, não para a Despesa.
    def test_cancelar_exclusao_volta_para_o_lancamento(self):
        self.caixa(lancamentos=[PADARIA])
        self.clicar('.lanc[data-id="l1"]')
        self.excluir()
        self.clicar('.folha-pe [data-a="fechar"]')
        self.assertEqual(self.folha(), "Despesa", "o Cancelar volta para a janela de onde a confirmação saiu")

    def test_desfazer_pagamento_pelo_formulario(self):
        self.caixa(lancamentos=[PADARIA])
        self.assertEqual(self.conta('.lanc.feito[data-id="l1"] .visto.on'), 1, "pago: verde, com o visto")
        self.clicar('.lanc[data-id="l1"]')
        self.clicar('.folha [data-a="lf-pago"][data-v=""]')
        self.salvar()
        self.assertFalse(self.lanc("l1")["pago"], "voltou para a pagar")
        self.assertEqual(self.conta('button.visto[data-a="lanc-pagar"][data-id="l1"]'), 1, "volta o círculo para dar baixa")
        self.assertIn("Atrasada", self.texto('.lanc[data-id="l1"]'), "era de ontem")


# ---------------------------------------------------------------------------------------------------------------
class TestParcelas(Caixa):
    def parcelar(self, valor, vezes, conta=None, cartao=False):
        self.nova()
        if conta:
            self.clicar(f'.folha [data-a="lf-conta"][data-v="{conta}"]')
        if cartao:
            self.clicar('.folha [data-a="lf-cartao"][data-v="1"]')
        self.digitar('#lf-valor', valor)
        self.preencher('#lf-desc', 'Geladeira')
        self.repetir("parcelado")
        self.digitar('.folha [data-lf="vezes"]', vezes)
        self.redesenhar()
        self.salvar()

    def test_parcelado_mostra_o_valor_de_cada_parcela(self):
        self.caixa()
        self.nova()
        self.digitar('#lf-valor', '100000')
        self.repetir("parcelado")
        self.digitar('.folha [data-lf="vezes"]', '3')
        self.redesenhar()
        self.assertEqual(self.texto('.folha label[for="lf-valor"]'), "Valor total", "o valor digitado é o da compra")
        self.assertIn("3x de R$ 333,33", self.folha_texto())

    def test_parcelas_viram_lancamentos_nos_meses_seguintes(self):
        self.caixa()
        self.parcelar('100000', '3')
        ls = self.lancs()
        self.assertEqual([(l["parcela"], l["data"], l["valor"]) for l in ls],
                         [("1/3", "2026-11-02", 333.33), ("2/3", "2026-12-02", 333.33), ("3/3", "2027-01-02", 333.34)],
                         "uma por mês; a última leva os centavos que sobram")
        self.assertEqual([l["pago"] for l in ls], [True, False, False], "só a de hoje nasce paga")
        self.assertEqual(len({l["grupo"] for l in ls}), 1, "as três são da mesma compra")
        self.assertEqual(self.aviso(), "3 parcelas lançadas")
        self.mes(1)
        self.assertIn("parcela 2/3", self.texto('.cx-lista > .lanc[data-a="lanc"]'), "dezembro mostra a parcela 2/3")

    def test_parcelas_fora_de_2_a_120_dao_erro(self):
        self.caixa()
        self.nova()
        self.digitar('#lf-valor', '100000')
        self.repetir("parcelado")
        for vezes in ("1", "121"):
            with self.subTest(vezes=vezes):
                self.digitar('.folha [data-lf="vezes"]', vezes)
                self.redesenhar()
                self.salvar()
                self.assertEqual(self.textos('.folha .msg-erro'), ["De 2 a 120 vezes."])
        self.assertEqual(self.dados()["lancamentos"], [], "nada foi lançado")

    def test_parcelas_no_cartao_entram_uma_em_cada_fatura(self):
        self.caixa()
        self.parcelar('90000', '3', conta="k-ana", cartao=True)
        self.assertTrue(all(l["cartao"] and l["conta"] == "k-ana" for l in self.lancs()), "todas no cartão da Ana")
        for mes, vence in (("novembro", "12/11"), ("dezembro", "12/12"), ("janeiro", "12/01")):
            with self.subTest(mes=mes):
                fat = self.faturas()
                self.assertEqual(len(fat), 1, "uma fatura no mês")
                self.assertIn(f"1 compra · vence {vence}", fat[0])
                self.assertIn("− R$ 300,00", fat[0])
            self.mes(1)

    def test_apagar_esta_e_as_proximas_parcelas(self):
        ps = [desp(f"p{k}", "Geladeira", 300, d, k == 1, parcela=f"{k}/3", grupo="g-gel")
              for k, d in ((1, "2026-11-02"), (2, "2026-12-02"), (3, "2027-01-02"))]
        self.caixa(lancamentos=ps)
        self.mes(1)
        self.clicar('.lanc[data-id="p2"]')
        self.excluir()
        self.assertEqual(self.folha(), "Apagar parcela")
        self.assertEqual(self.opcoes(), ["Só esta parcela", "Esta e as próximas"])
        self.escolher("Esta e as próximas")
        self.assertEqual([l["id"] for l in self.dados()["lancamentos"]], ["p1"], "fica só a primeira")
        self.assertEqual(self.aviso(), "Parcelas apagadas")


# ---------------------------------------------------------------------------------------------------------------
class TestCartao(Caixa):
    def no_cartao(self, conta):
        self.caixa()
        self.nova()
        self.clicar(f'.folha [data-a="lf-conta"][data-v="{conta}"]')
        self.clicar('.folha [data-a="lf-cartao"][data-v="1"]')

    def fatura(self):
        """O texto de ajuda: em que fatura a compra entra."""
        return next((t for t in self.textos('.folha .ajuda') if t.startswith("Entra na fatura")), None)

    def test_compra_no_cartao_diz_em_que_fatura_entra(self):
        self.no_cartao("k-ana")
        self.assertEqual(self.fatura(), "Entra na fatura que vence em 12/11/2026 (fecha dia 5, vence dia 12).")
        self.assertEqual(self.texto('.folha #lf-data-l'), "Data da compra", "no cartão, a data é a da compra")

    def test_compra_no_dia_do_fechamento_vai_para_a_fatura_seguinte(self):
        self.no_cartao("k-ana")
        self.data("2026-11-04")
        self.assertIn("vence em 12/11/2026", self.fatura(), "na véspera do fechamento: esta fatura")
        self.data("2026-11-05")
        self.assertIn("vence em 12/12/2026", self.fatura(), "no dia do fechamento: a seguinte")

    def test_cartao_que_vence_antes_de_fechar_vai_para_o_outro_mes(self):
        self.no_cartao("k-beto")  # fecha dia 25, vence dia 5: a fatura que fecha em novembro vence em dezembro
        self.data("2026-11-02")
        self.assertIn("vence em 05/12/2026", self.fatura())
        self.data("2026-11-25")
        self.assertIn("vence em 05/01/2027", self.fatura(), "no dia do fechamento: a de janeiro")

    def test_compra_no_cartao_fica_a_pagar_ate_a_fatura(self):
        self.no_cartao("k-ana")
        self.assertEqual(self.situacao(), "A pagar", "a fatura de 12/11 ainda não venceu")
        self.digitar('#lf-valor', '4000')
        self.salvar()
        l = self.dados()["lancamentos"][0]
        self.assertEqual((l["conta"], l["cartao"], l["pago"]), ("k-ana", True, False))

    def test_compra_no_cartao_entra_no_caixa_no_mes_da_fatura(self):
        self.no_cartao("k-ana")
        self.data("2026-11-06")
        self.digitar('#lf-valor', '4000')
        self.preencher('#lf-desc', 'Livraria')
        self.salvar()
        self.assertEqual((self.ids(), self.faturas()), ([], []), "em novembro não sai nada")
        self.mes(1)
        fat = self.faturas()
        self.assertEqual(len(fat), 1)
        self.assertIn("Fatura Banco Azul · Ana\n1 compra · vence 12/12", fat[0])
        self.assertEqual(self.ids(), [], "a compra fica dentro da fatura")


# ---------------------------------------------------------------------------------------------------------------
class TestFixos(Caixa):
    """Repetir todo mês ou todo ano: o fixo, o mês antes de lançado (v:<fixo>:<AAAA-MM>), pagar, editar e apagar."""

    def abrir_fixo(self, ym="2026-11", id="r-luz"):
        self.clicar(f'.lanc[data-id="v:{id}:{ym}"]')

    def test_todo_mes_cria_o_fixo_com_dia_e_inicio(self):
        self.caixa()
        self.nova()
        self.data("2026-11-10")
        self.digitar('#lf-valor', '15000')
        self.preencher('#lf-desc', 'Luz')
        self.repetir("mensal")
        self.assertIn("Todo dia 10, a partir de novembro.", self.folha_texto())
        self.salvar()
        d = self.dados()
        r = d["recorrencias"][0]
        self.assertEqual((r["descricao"], r["valor"], r["dia"], r["inicio"], r.get("fim"), r.get("freq")), ("Luz", 150, 10, "2026-11", None, None))
        self.assertEqual(d["lancamentos"], [], "a pagar: o mês fica como fixo, sem lançamento")
        self.assertEqual(self.aviso(), "Fixo cadastrado: aparece todo mês")
        self.assertEqual(self.ids(), [f"v:{r['id']}:2026-11"], "e já aparece no caixa de novembro")

    def test_fixo_pago_no_cadastro_ja_lanca_o_mes(self):
        self.caixa()
        self.nova()
        self.digitar('#lf-valor', '120000')
        self.preencher('#lf-desc', 'Aluguel')
        self.repetir("mensal")
        self.salvar()
        d = self.dados()
        r, l = d["recorrencias"][0], d["lancamentos"][0]
        self.assertEqual((l["recorrencia"], l["competencia"], l["pago"], l["valor"]), (r["id"], "2026-11", True, 1200))
        self.assertEqual(self.ids(), [l["id"]], "o fixo de novembro não aparece duas vezes")

    def test_fixo_aparece_antes_de_lancado_neste_mes_e_nos_seguintes(self):
        self.caixa(recorrencias=[LUZ])
        linha = self.texto('.lanc[data-id="v:r-luz:2026-11"]')
        self.assertIn("Contas da casa · fixo", linha)
        self.assertIn("A pagar", linha)
        for ym in ("2026-11", "2026-12", "2027-01"):
            with self.subTest(ym=ym):
                self.assertEqual(self.ids(), [f"v:r-luz:{ym}"])
            self.mes(1)
        self.assertEqual(self.dados()["lancamentos"], [], "sem lançar nada")

    def test_todo_ano_aparece_so_no_mes_da_data(self):
        self.caixa()
        self.nova()
        self.data("2026-12-15")
        self.digitar('#lf-valor', '180000')
        self.preencher('#lf-desc', 'IPVA')
        self.repetir("anual")
        self.assertIn("Todo ano em 15 de dezembro.", self.folha_texto())
        self.salvar()
        r = self.dados()["recorrencias"][0]
        self.assertEqual((r["freq"], r["dia"], r["inicio"]), ("anual", 15, "2026-12"))
        self.assertEqual(self.aviso(), "Fixo cadastrado: aparece todo ano")
        meses = []
        for _ in range(14):  # de novembro de 2026 a dezembro de 2027
            meses.append(self.ids())
            self.mes(1)
        self.assertEqual([k for k, ids in enumerate(meses) if ids], [1, 13], "só nos dezembros")
        self.assertEqual(meses[13], [f"v:{r['id']}:2027-12"])

    def test_fixo_aberto_mostra_que_o_mes_nao_foi_confirmado(self):
        self.caixa(recorrencias=[LUZ])
        self.abrir_fixo()
        self.assertEqual(self.folha(), "Despesa")
        t = self.folha_texto()
        self.assertIn("Gasto fixo, todo dia 10. Valor padrão R$ 150,00. Este mês ainda não foi confirmado.", t)
        self.assertEqual(self.texto('.folha label[for="lf-valor"]'), "Valor deste mês")
        self.assertEqual(self.textos('.folha-pe .btn'), ["Só este mês", "Todos os meses"])

    def test_pagar_fixo_com_outro_valor_nao_muda_o_padrao(self):
        self.caixa(recorrencias=[LUZ])
        self.clicar('button.visto[data-id="v:r-luz:2026-11"]')
        self.assertEqual(self.folha(), "Confirmar pagamento")
        self.assertIn("Os próximos meses continuam com R$ 150,00.", self.folha_texto())
        self.digitar('#pg-v', '18000')
        self.clicar('.folha-pe [data-a="pg-ok"]')
        d = self.dados()
        l = d["lancamentos"][0]
        self.assertEqual((l["valor"], l["pago"], l["recorrencia"], l["competencia"], l["data"]), (180, True, "r-luz", "2026-11", "2026-11-10"))
        self.assertEqual(d["recorrencias"][0]["valor"], 150, "o valor padrão continua")
        self.mes(1)
        self.assertIn("− R$ 150,00", self.texto('.lanc[data-id="v:r-luz:2026-12"]'), "dezembro com o padrão")

    def test_salvar_so_este_mes_nao_muda_o_padrao(self):
        self.caixa(recorrencias=[LUZ])
        self.abrir_fixo()
        self.digitar('#lf-valor', '12000')
        self.salvar("este")
        d = self.dados()
        l = d["lancamentos"][0]
        self.assertEqual((l["valor"], l["recorrencia"], l["competencia"], l["pago"]), (120, "r-luz", "2026-11", False))
        self.assertEqual(d["recorrencias"][0]["valor"], 150, "o padrão continua")
        self.assertEqual(self.ids(), [l["id"]], "o mês lançado fica no lugar do fixo")

    def test_salvar_todos_os_meses_muda_os_proximos(self):
        self.caixa(recorrencias=[LUZ])
        self.abrir_fixo()
        self.digitar('#lf-valor', '17000')
        self.salvar("todos")
        d = self.dados()
        self.assertEqual(d["recorrencias"][0]["valor"], 170, "o valor padrão mudou")
        self.assertEqual(d["lancamentos"], [], "sem lançar nada")
        self.mes(1)
        self.assertIn("− R$ 170,00", self.texto('.lanc[data-id="v:r-luz:2026-12"]'))

    def test_mudar_o_dia_em_todos_os_meses_muda_o_dia_do_fixo(self):
        self.caixa(recorrencias=[LUZ])
        self.abrir_fixo()
        self.data("2026-11-20")
        self.salvar("todos")
        self.assertEqual(self.dados()["recorrencias"][0]["dia"], 20)
        self.mes(1)
        self.assertEqual(self.pg.locator('.dia-cab b').all_text_contents(), ["dom, 20 de dez"], "dezembro no dia 20")

    # (era bug até a 1.24.0: o fixo do dia 31 virava do dia 30 ao salvar num mês de 30 dias)
    def test_mudar_so_o_valor_de_um_fixo_do_dia_31_num_mes_de_30_dias_mantem_o_dia(self):
        self.caixa(recorrencias=[fixo("r-alug", "Aluguel", 1500, 31, "2026-01", categoria="c-moradia")])
        self.abrir_fixo(id="r-alug")
        self.digitar('#lf-valor', '160000')
        self.salvar("todos")
        r = self.dados()["recorrencias"][0]
        self.assertEqual(r["valor"], 1600)
        self.assertEqual(r["dia"], 31, "só o valor mudou: o aluguel continua no dia 31 (31/12, 31/01...)")

    def test_apagar_fixo_oferece_tres_escolhas(self):
        self.caixa(recorrencias=[LUZ], lancamentos=[desp("l-out", "Luz", 140, "2026-10-10", True, recorrencia="r-luz", competencia="2026-10")])
        self.abrir_fixo()
        self.excluir()
        self.assertEqual(self.folha(), "Apagar fixo")
        self.assertEqual(self.opcoes(), ["Só o de novembro", "Parar a partir de novembro", "Apagar o fixo e o que ele já lançou (1)"])
        self.assertEqual(len(self.dados()["recorrencias"]), 1, "nada muda antes de escolher")

    def test_apagar_so_este_mes_pula_o_mes(self):
        self.caixa(recorrencias=[LUZ])
        self.abrir_fixo()
        self.excluir()
        self.escolher("Só o de novembro")
        self.assertEqual(self.ids(), [], "novembro sem a Luz")
        d = self.dados()
        l = d["lancamentos"][0]
        self.assertEqual((l["recorrencia"], l["competencia"], l["pulado"]), ("r-luz", "2026-11", True))
        self.assertEqual(len(d["recorrencias"]), 1, "o fixo continua")
        self.assertEqual(self.aviso(), "Apagado deste mês")
        self.mes(1)
        self.assertEqual(self.ids(), ["v:r-luz:2026-12"], "dezembro continua com a Luz")

    def test_parar_a_partir_do_mes_mantem_o_que_ja_foi_pago(self):
        luz = fixo("r-luz", "Luz", 150, 10, "2026-09", categoria="c-contas")
        pagos = [desp("l-set", "Luz", 140, "2026-09-10", True, recorrencia="r-luz", competencia="2026-09"),
                 desp("l-out", "Luz", 160, "2026-10-10", True, recorrencia="r-luz", competencia="2026-10")]
        dez = desp("l-dez", "Luz", 155, "2026-12-10", False, recorrencia="r-luz", competencia="2026-12")
        self.caixa(recorrencias=[luz], lancamentos=pagos + [dez])
        self.mes(1)
        self.clicar('.lanc[data-id="l-dez"]')
        self.excluir()
        self.escolher("Parar a partir de dezembro")
        d = self.dados()
        self.assertEqual(d["recorrencias"][0]["fim"], "2026-11", "o último mês é novembro")
        self.assertEqual(sorted(l["id"] for l in d["lancamentos"]), ["l-out", "l-set"],
                         "setembro e outubro, pagos, continuam; o de dezembro, ainda a pagar, sai junto com o fixo")
        self.assertEqual(self.aviso(), "Fixo encerrado: o que já foi lançado continua")
        self.assertEqual(self.ids(), [], "dezembro sem a Luz")
        self.mes(-1)
        self.assertEqual(self.ids(), ["v:r-luz:2026-11"], "novembro ainda tem")

    def test_apagar_o_fixo_e_o_que_ele_lancou(self):
        self.caixa(recorrencias=[LUZ], lancamentos=[
            desp("l-out", "Luz", 160, "2026-10-10", True, recorrencia="r-luz", competencia="2026-10"),
            desp("l-merc", "Mercado", 80, "2026-11-01", True)])
        self.abrir_fixo()
        self.excluir()
        self.escolher("Apagar o fixo e o que ele já lançou (1)")
        d = self.dados()
        self.assertEqual(d["recorrencias"], [])
        self.assertEqual([l["id"] for l in d["lancamentos"]], ["l-merc"], "o resto do caixa fica")
        self.assertEqual(self.aviso(), "Fixo apagado")
        self.assertEqual(self.ids(), ["l-merc"])

    def test_fixo_parado_sai_da_lista_de_fixos(self):
        self.caixa(recorrencias=[LUZ, fixo("r-net", "Internet", 99.9, 20, "2026-01", categoria="c-contas")])
        self.ir_mais("caixa")
        self.assertEqual(self.conta('#fixos .banco-row'), 2)
        self.clicar('#fixos .banco-row[data-id="r-luz"]')  # abre o do próximo mês (dezembro)
        self.excluir()
        self.escolher("Parar a partir de dezembro")
        fixos = self.textos('#fixos .banco-row')
        self.assertEqual(len(fixos), 1, "a Luz parada sai da lista")
        self.assertIn("Internet", fixos[0])


# ---------------------------------------------------------------------------------------------------------------
SALARIO = rec("l-sal", "Salário", 5000, "2026-11-02", True, conta="k-verde", categoria="c-salario", descontos=[INSS])


class TestDesfazer(Caixa):
    """Depois de apagar, o aviso tem o Desfazer (como nos outros apps da família): volta tudo como era."""

    def test_lancamento_volta_no_mesmo_lugar(self):
        mercado = desp("l2", "Mercado", 80, "2026-11-03", True)
        self.caixa(lancamentos=[PADARIA, mercado])
        antes = self.dados()["lancamentos"]
        self.clicar('.lanc[data-id="l1"]')
        self.excluir()
        self.clicar('.folha-pe [data-a="confirmar"]')
        self.assertEqual([l["id"] for l in self.dados()["lancamentos"]], ["l2"])
        self.desfazer()
        self.assertEqual(self.dados()["lancamentos"], antes, "o mesmo lançamento, na mesma posição")
        self.assertEqual(self.aviso(), "Desfeito")
        self.assertEqual(self.js("document.querySelector('#toast .toast-a')"), None, "o Desfeito não tem outro Desfazer")
        self.assertIn("l1", self.ids())

    def abrir_fixo(self, ym="2026-11", id="r-luz"):
        self.clicar(f'.lanc[data-id="v:{id}:{ym}"]')

    def test_fixo_so_deste_mes_e_parar(self):
        self.caixa(recorrencias=[LUZ])
        self.abrir_fixo()
        self.excluir()
        self.escolher("Só o de novembro")
        self.assertEqual(len(self.dados()["lancamentos"]), 1, "a linha que pula o mês")
        self.desfazer()
        self.assertEqual(self.dados()["lancamentos"], [], "a linha que pulava o mês sai")
        self.assertEqual(self.ids(), ["v:r-luz:2026-11"])
        self.abrir_fixo()
        self.excluir()
        self.escolher("Parar a partir de novembro")
        self.desfazer()
        self.assertEqual(self.dados()["recorrencias"][0].get("fim"), LUZ.get("fim"), "o fixo volta a valer")

    def test_o_que_mudou_depois_fica(self):
        mercado = desp("l2", "Mercado", 80, "2026-11-03", True)
        self.caixa(lancamentos=[PADARIA, mercado])
        self.clicar('.lanc[data-id="l1"]')
        self.excluir()
        self.clicar('.folha-pe [data-a="confirmar"]')
        # outro aparelho muda o Mercado antes do Desfazer
        self.js("(T.persistir(d => { d.lancamentos.find(l => l.id === 'l2').valor = 99; }), true)")
        self.esperar()
        self.desfazer()
        d = {l["id"]: l["valor"] for l in self.dados()["lancamentos"]}
        self.assertEqual(d, {"l1": 12.5, "l2": 99}, "a Padaria volta e o Mercado fica com o valor novo")

    def test_aviso_comum_sem_desfazer_e_some(self):
        self.caixa(lancamentos=[PADARIA])
        self.js("(T.toast('Salvo'), true)")
        self.assertEqual(self.aviso(), "Salvo")
        self.assertEqual(self.js("document.getElementById('toast').classList.contains('com-acao')"), False)


class TestSalario(Caixa):
    """Salário pelo bruto, impostos na fonte e a despesa descontada do salário (vínculo)."""

    def salario_com_inss(self):
        self.caixa()
        self.nova("receita")
        self.digitar('#lf-valor', '500000')
        self.clicar('.folha [data-a="lf-desc-abrir"]')
        self.clicar('.folha [data-a="lf-desc-add"][data-v="0"]')  # INSS
        self.digitar('.folha [data-lfd="valor"][data-i="0"]', '11')

    def test_descontos_na_fonte_mostram_bruto_e_liquido(self):
        self.salario_com_inss()
        self.assertEqual(self.texto('.folha label[for="lf-valor"]'), "Valor bruto")
        self.assertEqual(self.pg.input_value('.folha [data-lfd="descricao"][data-i="0"]'), "INSS")
        self.assertEqual(self.texto('#lfd-v-0'), "− R$ 550,00", "11% de 5.000")
        self.assertEqual(self.texto('#lf-desc-res').split("\n"),
                         ["Bruto", "R$ 5.000,00", "Descontos", "− R$ 550,00", "Líquido", "R$ 4.450,00", "cai na conta"])

    def test_imposto_fica_salvo_como_porcentagem_do_bruto(self):
        self.salario_com_inss()
        self.salvar()
        l = self.dados()["lancamentos"][0]
        self.assertEqual(l["valor"], 5000, "o recebimento é o bruto")
        self.assertEqual([{k: x[k] for k in ("descricao", "modo", "valor", "categoria")} for x in l["descontos"]],
                         [{"descricao": "INSS", "modo": "pct", "valor": 11, "categoria": "c-impostos"}])

    def test_salario_na_lista_mostra_bruto_descontos_e_liquido(self):
        self.caixa(lancamentos=[SALARIO])
        self.assertEqual(self.ids(), ["l-sal"], "o imposto não aparece solto")
        self.assertIn("+ R$ 5.000,00", self.texto('.lanc[data-id="l-sal"]'), "o salário pelo bruto")
        self.assertEqual(self.texto('.desc-tog').split("\n"), ["1 desconto · líquido R$ 4.450,00", "− R$ 550,00"])
        self.clicar('.desc-tog')
        self.assertIn("INSS\nImpostos e taxas · 11% do bruto · já pago, na fonte\n− R$ 550,00", self.texto('.desc-itens .lanc'))

    def test_imposto_sai_do_caixa_no_mesmo_dia(self):
        self.caixa(lancamentos=[SALARIO])
        self.assertEqual(self.resumo()[0], ["R$ 5.000", "R$ 550", "R$ 4.450"], "entrou o bruto, saiu o imposto")
        self.assertIn("R$ 4.450,00", self.texto('.cx-saldo'), "no saldo de hoje, o líquido")
        self.assertEqual(self.pg.locator('.dia-cab span').all_text_contents(), ["+ R$ 4.450"], "no mesmo dia do salário")

    def test_despesa_descontada_do_salario_tem_baixa_com_ele(self):
        self.caixa(recorrencias=[SAL_FIXO])
        self.nova()
        self.assertEqual(self.pg.locator('#lf-vinc option').all_text_contents(),
                         ["Por conta própria (conta, Pix ou cartão)", "Descontado de: Salário (dia 5)"])
        self.pg.select_option('#lf-vinc', 'r-sal')
        self.esperar()
        self.assertEqual(self.texto('.folha .vinc-st'), "Baixa com Salário")
        self.assertEqual(self.conta('.folha [data-a="lf-pago"]'), 0, "sem Pago e A pagar: segue o salário")
        self.assertEqual(self.conta('.folha [data-a="lf-conta"]'), 0, "sem conta: sai da conta do salário")
        self.digitar('#lf-valor', '40000')
        self.preencher('#lf-desc', 'Plano de saúde')
        self.salvar()
        l = self.dados()["lancamentos"][0]
        self.assertEqual((l["vinculo"], l["conta"], l["pago"], l["cartao"]), ("r-sal", "k-verde", False, False), "o salário de novembro ainda não entrou")

    def test_receber_o_salario_da_baixa_na_despesa_ligada(self):
        self.caixa(recorrencias=[SAL_FIXO, PLANO])
        self.clicar('button.visto[data-id="v:r-sal:2026-11"]')
        self.assertEqual(self.folha(), "Confirmar recebimento")
        self.clicar('.folha-pe [data-a="pg-ok"]')
        plano = [l for l in self.dados()["lancamentos"] if l.get("recorrencia") == "r-plano"]
        self.assertEqual([(l["pago"], l["data"], l["conta"], l["competencia"]) for l in plano], [(True, "2026-11-05", "k-verde", "2026-11")],
                         "pago no dia e na conta do salário")
        self.assertEqual(self.aviso(), "Recebimento confirmado")

    def test_despesa_ligada_fica_dentro_do_salario(self):
        self.caixa(recorrencias=[SAL_FIXO, PLANO], lancamentos=[
            rec("l-sal", "Salário", 5000, "2026-11-02", True, conta="k-verde", categoria="c-salario", recorrencia="r-sal", competencia="2026-11"),
            desp("l-plano", "Plano de saúde", 400, "2026-11-02", True, conta="k-verde", categoria="c-saude", recorrencia="r-plano", competencia="2026-11", vinculo="r-sal")])
        self.assertEqual(self.ids(), ["l-sal"], "o plano não aparece solto")
        self.assertEqual(self.texto('.desc-tog').split("\n"), ["1 desconto · líquido R$ 4.600,00", "− R$ 400,00"])
        self.clicar('.desc-tog')
        self.assertIn("Plano de saúde\nSaúde · fixo · já pago, descontado", self.texto('.desc-itens .lanc'))
        self.assertIn("R$ 4.600,00", self.texto('.cx-saldo'))

    def test_receber_salario_com_descontos_abre_o_formulario(self):
        self.caixa(recorrencias=[dict(SAL_FIXO, descontos=[INSS])])
        self.clicar('button.visto[data-id="v:r-sal:2026-11"]')
        self.assertEqual(self.folha(), "Confirmar recebimento")
        self.assertEqual(self.situacao(), "Recebido")
        self.assertIn("Líquido\nR$ 4.450,00", self.texto('#lf-desc-res'), "o líquido para conferir com o que caiu na conta")
        self.salvar("este")
        l = self.dados()["lancamentos"][0]
        self.assertEqual((l["pago"], l["valor"], l["competencia"], [x["descricao"] for x in l["descontos"]]), (True, 5000, "2026-11", ["INSS"]))


# ---------------------------------------------------------------------------------------------------------------
NET = desp("l-net", "Internet", 99.9, "2026-11-20", False, conta="k-verde", categoria="c-contas")


class TestPagar(Caixa):
    """O círculo do lado do valor: Paguei, Recebi, Apliquei."""

    def test_circulo_abre_confirmar_pagamento(self):
        self.caixa(lancamentos=[NET])
        self.assertIn("A pagar", self.texto('.lanc[data-id="l-net"]'))
        self.clicar('button.visto[data-id="l-net"]')
        self.assertEqual(self.folha(), "Confirmar pagamento")
        self.assertIn("Internet · 20/11/2026", self.folha_texto())
        self.assertEqual(self.pg.input_value('#pg-v'), "99,90", "com o valor lançado")
        self.assertEqual(self.textos('.folha-pe .btn'), ["Cancelar", "Paguei"])

    def test_paguei_com_outro_valor_fica_pago_e_verde(self):
        self.caixa(lancamentos=[NET])
        self.clicar('button.visto[data-id="l-net"]')
        self.digitar('#pg-v', '10500')
        self.clicar('.folha-pe [data-a="pg-ok"]')
        l = self.lanc("l-net")
        self.assertEqual((l["pago"], l["valor"], l["data"]), (True, 105, "2026-11-20"), "pago com o valor certo, na mesma data")
        self.assertIsNone(self.folha())
        self.assertEqual(self.aviso(), "Pagamento confirmado")
        self.assertEqual(self.conta('.lanc.feito[data-id="l-net"] .visto.on'), 1, "verde, com o visto")
        self.assertNotIn("A pagar", self.texto('.lanc[data-id="l-net"]'))

    def test_pagar_sem_valor_avisa(self):
        self.caixa(lancamentos=[NET])
        self.clicar('button.visto[data-id="l-net"]')
        self.digitar('#pg-v', '')
        self.clicar('.folha-pe [data-a="pg-ok"]')
        self.assertEqual(self.aviso(), "Coloque o valor.")
        self.assertEqual(self.folha(), "Confirmar pagamento", "a janela continua aberta")
        self.assertFalse(self.lanc("l-net")["pago"])

    def test_recebimento_pendente_pede_recebi(self):
        self.caixa(lancamentos=[rec("l-fr", "Freela", 400, "2026-11-28", False, categoria="c-freelance")])
        self.assertIn("A receber", self.texto('.lanc[data-id="l-fr"]'))
        btn = self.pg.locator('button.visto[data-id="l-fr"]')
        self.assertEqual(btn.get_attribute("aria-label"), "Recebi: Freela")
        self.clicar('button.visto[data-id="l-fr"]')
        self.assertEqual(self.folha(), "Confirmar recebimento")
        self.assertIn("Quanto entrou", self.folha_texto())
        self.assertEqual(self.textos('.folha-pe .btn'), ["Cancelar", "Recebi"])
        self.clicar('.folha-pe [data-a="pg-ok"]')
        self.assertTrue(self.lanc("l-fr")["pago"])
        self.assertEqual(self.aviso(), "Recebimento confirmado")

    def test_aporte_aplicado_soma_no_investimento(self):
        inv = {"id": "i-cdb", "nome": "CDB Azul", "banco": "b-azul", "valor": 10000, "indexador": "parado", "tipo": "cdb", "data_valor": "2026-11-02"}
        ap = fixo("r-ap", "Aporte", 800, 6, "2026-01", aporte=True, categoria="c-investimentos")
        self.caixa(recorrencias=[ap], investimentos=[inv])
        self.assertIn("A aplicar", self.texto('.lanc[data-id="v:r-ap:2026-11"]'))
        self.clicar('button.visto[data-id="v:r-ap:2026-11"]')
        self.assertEqual(self.folha(), "Confirmar aporte")
        self.assertEqual(self.marcados('[data-a="pg-inv"]'), ["CDB Azul"], "o único investimento já vem escolhido")
        self.assertIn("CDB Azul: R$ 10.000,00 → R$ 10.800,00.", self.folha_texto())
        self.clicar('.folha-pe [data-a="pg-ok"]')
        d = self.dados()
        self.assertEqual(d["investimentos"][0]["valor"], 10800, "o aporte soma ao investimento")
        l = d["lancamentos"][0]
        self.assertEqual((l["pago"], l["valor"], l["investimento"], l["competencia"]), (True, 800, "i-cdb", "2026-11"))
        self.assertEqual(self.aviso(), "Aplicado em CDB Azul")


# ---------------------------------------------------------------------------------------------------------------
class TestAjusteSaldo(Caixa):
    """Ajustar saldo: a diferença para o saldo do banco vira um lançamento de ajuste."""

    def com_mil(self):
        self.caixa(lancamentos=[rec("l-sal", "Salário", 1000, "2026-11-01", True, categoria="c-salario")])
        self.clicar('[data-a="cx-ajuste"]')

    def ajustes(self):
        return [l for l in self.dados()["lancamentos"] if l.get("ajuste")]

    def test_ajuste_para_mais_lanca_entrada_de_ajuste(self):
        self.com_mil()
        self.assertEqual(self.folha(), "Ajustar saldo")
        self.assertEqual(self.pg.input_value('#aj-v'), "1.000,00", "começa com o saldo de hoje")
        self.digitar('#aj-v', '125000')
        self.clicar('.folha-pe [data-a="aj-ok"]')
        aj = self.ajustes()
        self.assertEqual([(l["tipo"], l["valor"], l["pago"], l["data"], l["descricao"]) for l in aj], [("receita", 250, True, "2026-11-02", "Ajuste de saldo")])
        self.assertIsNone(self.folha())
        self.assertEqual(self.aviso(), "Saldo ajustado")
        self.assertIn("R$ 1.250,00", self.texto('.cx-saldo'))

    def test_ajuste_para_menos_lanca_saida_de_ajuste(self):
        self.com_mil()
        self.digitar('#aj-v', '80000')
        self.clicar('.folha-pe [data-a="aj-ok"]')
        self.assertEqual([(l["tipo"], l["valor"]) for l in self.ajustes()], [("despesa", 200)])
        self.assertIn("R$ 800,00", self.texto('.cx-saldo'))

    def test_ajuste_igual_ao_saldo_nao_lanca_nada(self):
        self.com_mil()
        self.clicar('.folha-pe [data-a="aj-ok"]')
        self.assertEqual(self.aviso(), "O saldo já está certo.")
        self.assertEqual(self.ajustes(), [])
        self.assertIsNone(self.folha())

    def test_ajuste_fica_fora_das_entradas_saidas_e_categorias(self):
        self.com_mil()
        self.digitar('#aj-v', '125000')
        self.clicar('.folha-pe [data-a="aj-ok"]')
        self.assertEqual(self.resumo()[0], ["R$ 1.000", "R$ 0", "R$ 1.000"], "Entrou continua R$ 1.000")
        aj = self.ajustes()[0]
        self.assertIn("Ajuste de saldo", self.texto(f'.lanc[data-id="{aj["id"]}"]'))
        self.assertEqual(self.conta(f'.lanc[data-id="{aj["id"]}"] .visto'), 0, "sem círculo nem visto")
        self.clicar('[data-a="cx-modo"][data-v="categorias"]')
        self.clicar('[data-a="cx-cat-tipo"][data-v="receita"]')
        self.assertEqual(self.textos('.comp .nm b'), ["Salário"], "o ajuste não entra nas categorias")

    # (era bug até a 1.24.0: o saldo negativo aparecia sem o sinal)
    def test_ajuste_com_saldo_negativo_mostra_o_sinal(self):
        self.caixa(lancamentos=[desp("l-al", "Aluguel", 500, "2026-11-01", True)])
        self.clicar('[data-a="cx-ajuste"]')
        self.assertIn(self.pg.input_value('#aj-v'), ("-500,00", "−500,00"), "o saldo de hoje é −R$ 500,00, não R$ 500,00")
        self.assertEqual(self.texto('[data-a="aj-sinal"].on'), "Negativo")

    def test_ajuste_negativo_pelo_botao_e_pelo_sinal(self):
        self.caixa(lancamentos=[desp("l-al", "Aluguel", 500, "2026-11-01", True)])
        self.clicar('[data-a="cx-ajuste"]')
        self.digitar('#aj-v', '30000')
        self.assertEqual(self.pg.input_value('#aj-v'), "-300,00", "o sinal continua ao redigitar")
        self.clicar('[data-a="aj-ok"]')
        aj = self.ajustes()[0]
        self.assertEqual((aj["tipo"], aj["valor"]), ("receita", 200), "de −500 para −300: entra 200")

    def test_ajuste_positivo_quando_estava_negativo(self):
        self.caixa(lancamentos=[desp("l-al", "Aluguel", 500, "2026-11-01", True)])
        self.clicar('[data-a="cx-ajuste"]')
        self.clicar('[data-a="aj-sinal"][data-v="+"]')
        self.digitar('#aj-v', '10000')
        self.clicar('[data-a="aj-ok"]')
        aj = self.ajustes()[0]
        self.assertEqual((aj["tipo"], aj["valor"]), ("receita", 600), "de −500 para +100: entra 600")


# ---------------------------------------------------------------------------------------------------------------
FARM = desp("l-farm", "Farmácia", 90, "2026-10-20", False, conta="k-ana", cartao=True, categoria="c-saude")
POSTO = desp("l-posto", "Posto", 210, "2026-10-28", False, conta="k-ana", cartao=True, categoria="c-transporte")
LIVRO = desp("l-livro", "Livraria", 60, "2026-10-10", False, conta="k-beto", cartao=True, categoria="c-educacao")


class TestFaturas(Caixa):
    def test_compras_no_cartao_viram_uma_fatura_por_cartao_e_vencimento(self):
        self.caixa(lancamentos=[FARM, POSTO, LIVRO])
        fat = self.faturas()
        self.assertEqual(len(fat), 2, "uma fatura por cartão")
        self.assertIn("Fatura Banco Azul · Beto\n1 compra · vence 05/11", fat[0])
        self.assertIn("− R$ 60,00", fat[0])
        self.assertIn("Fatura Banco Azul · Ana\n2 compras · vence 12/11", fat[1])
        self.assertIn("− R$ 300,00", fat[1])
        self.assertIn("Aberta", fat[1])
        self.assertEqual(self.ids(), [], "as compras ficam dentro das faturas")
        self.assertEqual(self.pg.locator('.dia-cab b').all_text_contents(), ["qui, 5 de nov", "qui, 12 de nov"], "no dia do vencimento")

    def test_abrir_fatura_mostra_as_compras(self):
        self.caixa(lancamentos=[FARM, POSTO])
        self.clicar('.lanc.fatura')
        itens = self.textos('.fatura-itens .lanc')
        self.assertEqual(len(itens), 2)
        self.assertIn("Farmácia\nSaúde · 20/10", itens[0], "com a data da compra")
        self.assertIn("Posto\nTransporte · 28/10", itens[1])
        self.assertIn("toque para fechar", self.texto('.lanc.fatura'))
        self.clicar('.lanc.fatura')
        self.assertEqual(self.conta('.fatura-itens'), 0, "tocar de novo fecha")

    def test_pagar_fatura_confirma_o_total(self):
        self.caixa(lancamentos=[FARM, POSTO])
        self.clicar('button.visto[data-a="fatura-pagar"]')
        self.assertEqual(self.folha(), "Pagar fatura")
        self.assertIn("Fatura Banco Azul · Ana que vence em 12/11/2026: R$ 300,00 em 2 compras. Todas ficam pagas.", self.folha_texto())
        self.assertEqual(self.textos('.folha-pe .btn'), ["Cancelar", "Paguei a fatura"])
        self.assertFalse(any(l["pago"] for l in self.dados()["lancamentos"]), "nada pago antes de confirmar")

    def test_pagar_fatura_marca_todas_as_compras(self):
        self.caixa(lancamentos=[FARM, POSTO, LIVRO])
        self.clicar('button.visto[data-a="fatura-pagar"][data-v="k-ana|2026-11-12"]')
        self.clicar('.folha-pe [data-a="confirmar"]')
        pagos = {l["id"]: l["pago"] for l in self.dados()["lancamentos"]}
        self.assertEqual(pagos, {"l-farm": True, "l-posto": True, "l-livro": False}, "só as compras daquela fatura")
        self.assertEqual(self.aviso(), "Fatura paga")
        self.assertEqual(self.conta('.lanc.fatura.feito .visto.on'), 1, "a fatura fica verde, com o visto")

    def test_fixo_no_cartao_e_pago_com_a_fatura(self):
        stream = fixo("r-stream", "Streaming", 55.9, 15, "2026-01", conta="k-ana", cartao=True, categoria="c-assinaturas")
        self.caixa(recorrencias=[stream], lancamentos=[FARM])
        self.assertIn("2 compras · vence 12/11", self.faturas()[0], "a assinatura de outubro entra na fatura de novembro")
        self.assertIn("− R$ 145,90", self.faturas()[0])
        self.clicar('button.visto[data-a="fatura-pagar"]')
        self.clicar('.folha-pe [data-a="confirmar"]')
        d = self.dados()
        st = [l for l in d["lancamentos"] if l.get("recorrencia") == "r-stream"]
        self.assertEqual([(l["competencia"], l["data"], l["pago"], l["cartao"], l["valor"]) for l in st], [("2026-10", "2026-10-15", True, True, 55.9)])
        self.assertTrue(self.lanc("l-farm")["pago"])
        self.assertEqual(d["recorrencias"][0]["valor"], 55.9, "o fixo continua igual")


# ---------------------------------------------------------------------------------------------------------------
LISTA = [
    rec("l-sal", "Salário", 5000, "2026-11-01", True, conta="k-verde", categoria="c-salario"),
    rec("l-freela", "Freela", 400, "2026-11-28", False, categoria="c-freelance"),
    desp("l-alug", "Aluguel", 1200, "2026-11-01", True, categoria="c-moradia"),
    desp("l-net", "Internet", 99.9, "2026-11-20", False, categoria="c-contas", conta="k-verde"),
    desp("l-luz", "Luz", 150, "2026-10-30", False, categoria="c-contas"),
    desp("l-merc", "Mercado", 300, "2026-11-02", True, categoria="c-mercado"),
]


class TestListaCaixa(Caixa):
    """A lista do mês: navegar, filtros, números do topo, dias e saldo."""

    def test_mudar_de_mes_e_voltar_para_hoje(self):
        self.caixa(lancamentos=LISTA)
        self.assertEqual(self.texto('.mes-nome'), "Novembro de 2026", "abre no mês de hoje")
        self.mes(1)
        self.assertEqual(self.texto('.mes-nome'), "Dezembro de 2026\nvoltar para hoje")
        self.assertIn("Nada lançado em dezembro.", self.tela())
        self.mes(-2)
        self.assertEqual(self.ids(), ["l-luz"], "outubro")
        self.clicar('.mes-nome')
        self.assertEqual(self.texto('.mes-nome'), "Novembro de 2026")

    def test_numeros_do_topo_batem_com_os_lancamentos(self):
        self.caixa(lancamentos=LISTA)
        b, small = self.resumo()
        self.assertEqual(b, ["R$ 5.000", "R$ 1.500", "R$ 3.500"], "entrou 5.000; saiu 1.200 + 300; sobrou 3.500")
        self.assertEqual(small, ["+ R$ 400 a receber", "+ R$ 100 a pagar", "previsto R$ 3.800"], "a Luz de outubro não conta em novembro")

    def test_filtros_tudo_entradas_saidas_e_a_pagar(self):
        self.caixa(lancamentos=LISTA)
        casos = (("entradas", ["l-sal", "l-freela"]), ("saidas", ["l-alug", "l-merc", "l-net"]), ("pendentes", ["l-luz", "l-net", "l-freela"]),  # a Luz de outubro, atrasada, vem primeiro
                 ("tudo", ["l-sal", "l-alug", "l-merc", "l-net", "l-freela"]))
        for filtro, esperado in casos:
            with self.subTest(filtro=filtro):
                self.clicar(f'[data-a="cx-filtro"][data-v="{filtro}"]')
                self.assertEqual(self.ids(), esperado)

    def test_filtro_escolhido_fica_guardado(self):
        self.caixa(lancamentos=LISTA)
        self.clicar('[data-a="cx-filtro"][data-v="entradas"]')
        self.ir("inicio")
        self.ir("caixa")
        self.assertEqual(self.textos('[data-a="cx-filtro"].on'), ["Entradas"])
        self.assertEqual(self.js("T.store.get('ui', {}).cxFiltro"), "entradas", "guardado para quando o app abrir de novo")

    def test_lista_agrupa_por_dia_com_a_soma_do_dia(self):
        self.caixa(lancamentos=LISTA)
        self.assertEqual(self.pg.locator('.dia-cab b').all_text_contents(), ["dom, 1 de nov", "Hoje, 2 de nov", "sex, 20 de nov", "sáb, 28 de nov"])
        self.assertEqual(self.pg.locator('.dia-cab span').all_text_contents(), ["+ R$ 3.800", "− R$ 300", "− R$ 100", "+ R$ 400"])

    def test_saldo_de_hoje_do_fim_do_mes_e_dos_outros_meses(self):
        self.caixa(lancamentos=LISTA)
        self.assertEqual(self.texto('.cx-saldo').split("\n"), ["Saldo em caixa hoje", "R$ 3.500,00", "No fim do mês: R$ 3.650", "Ajustar saldo"],
                         "fim do mês: 3.500 + 400 − 99,90 − 150 (a Luz atrasada)")
        self.mes(-1)
        self.assertEqual(self.texto('.cx-saldo').split("\n"), ["Saldo no fim do mês", "R$ 0,00"], "mês passado: sem Ajustar saldo")
        self.mes(2)
        self.assertEqual(self.texto('.cx-saldo').split("\n"), ["Saldo previsto no fim do mês", "R$ 3.650,10"])


# ---------------------------------------------------------------------------------------------------------------
CATS = [
    desp("c1", "Aluguel", 1200, "2026-11-01", True, categoria="c-moradia"),
    desp("c2", "Feira", 200, "2026-11-01", True, categoria="c-mercado"),
    desp("c3", "Mercado", 100, "2026-11-02", True, categoria="c-mercado"),
    desp("c4", "Posto", 100, "2026-11-06", False, categoria="c-transporte", conta="k-ana", cartao=True),  # fatura de dezembro
    rec("c5", "Salário", 5000, "2026-11-01", True, categoria="c-salario"),
    rec("c6", "Freela", 500, "2026-11-01", True, categoria="c-freelance"),
]


class TestCategorias(Caixa):
    def comps(self):
        """Cada categoria na tela: nome, valor do mês e a porcentagem (com a variação, se houver)."""
        return self.js("[...document.querySelectorAll('.comp')].map(c => [c.querySelector('.nm b').textContent, "
                       "c.querySelector('.vl').firstChild.textContent, c.querySelector('.vl small').textContent])")

    def test_gastos_e_recebimentos_por_categoria(self):
        self.caixa(ui={"cxModo": "categorias"}, lancamentos=CATS)
        self.assertEqual(self.comps(), [["Moradia", "R$ 1.200", "75,0%"], ["Mercado", "R$ 300", "18,8%"], ["Transporte", "R$ 100", "6,3%"]])
        self.assertIn("2 lançamentos", self.textos('.comp .sub')[1])
        self.assertEqual(self.pg.locator('#app .stat-duo b').first.text_content(), "R$ 1.600", "gastos em novembro")
        self.clicar('[data-a="cx-cat-tipo"][data-v="receita"]')
        self.assertEqual(self.comps(), [["Salário", "R$ 5.000", "90,9%"], ["Freelance", "R$ 500", "9,1%"]])

    def test_categorias_contam_pela_data_da_compra(self):
        self.caixa(ui={"cxModo": "categorias"}, lancamentos=[CATS[3]])
        self.assertEqual([c[0] for c in self.comps()], ["Transporte"], "compra de novembro no cartão: novembro, mesmo com a fatura em dezembro")
        self.assertIn("Pela data da compra.", self.tela())
        self.mes(1)
        self.assertIn("Nenhum gasto em dezembro.", self.tela())

    def test_media_dos_3_meses_antes(self):
        lanc = [desp(f"m{m}", "Mercado", v, f"2026-{m:02d}-10", True, categoria="c-mercado") for m, v in ((8, 300), (9, 600), (10, 900), (11, 300))]
        self.caixa(ui={"cxModo": "categorias"}, lancamentos=lanc)
        self.assertEqual(self.pg.locator('#app .stat-duo b').all_text_contents(), ["R$ 300", "R$ 600"], "novembro e a média de agosto a outubro")
        self.assertEqual(self.textos('.comp .sub'), ["1 lançamento · média R$ 600"])
        self.assertEqual(self.comps()[0][2], "100,0% · ▼ 50%", "metade da média")

    def test_tocar_numa_categoria_mostra_o_valor(self):
        self.caixa(ui={"cxModo": "categorias"}, lancamentos=CATS)
        self.assertEqual(self.texto('.pilha-cap'), "Toque numa parte para ver o valor")
        self.clicar('.comp[data-v="c-mercado"]')
        self.assertEqual(self.texto('.pilha-cap'), "Mercado · R$ 300 · 18,8%")
        self.assertEqual(self.conta('.comp.on[data-v="c-mercado"]'), 1)


# ---------------------------------------------------------------------------------------------------------------
class TestFluxo(Caixa):
    """Fluxo: períodos prontos e Outro (com a validação), a tabela por mês e Prever o dia a dia."""

    def meses_da_tabela(self):
        return [t.strip() for t in self.pg.locator('.tabela tbody tr td:first-child').all_text_contents()]

    def fluxo(self, lancamentos, prever=True):
        self.caixa(ui={"cxModo": "fluxo"}, ajustes={"corrigir": True, "prever_dia": prever}, lancamentos=lancamentos)

    def outro(self, atras, frente):
        self.clicar('[data-a="cx-periodo"][data-v="outro"]')
        self.pg.fill('#per-atras', atras)
        self.pg.fill('#per-frente', frente)
        self.clicar('.folha-pe [data-a="cx-per-ok"]')

    def test_periodos_prontos(self):
        self.fluxo([rec("l1", "Salário", 5000, "2026-11-01", True)])
        casos = (("meio", "6 + 6", "jun/26", "mai/27 *"), ("passado", "12 atrás", "dez/25", "nov/26"), ("futuro", "12 à frente", "nov/26", "out/27 *"))
        for k, rotulo, primeiro, ultimo in casos:
            with self.subTest(periodo=rotulo):
                self.clicar(f'[data-a="cx-periodo"][data-v="{k}"]')
                self.assertEqual(self.textos('[data-a="cx-periodo"].on'), [rotulo])
                m = self.meses_da_tabela()
                self.assertEqual((len(m), m[0], m[-1]), (12, primeiro, ultimo), "12 meses; * nos previstos")
                self.assertEqual(self.conta('#ch-fluxo .pt-net'), 12, "um ponto por mês no gráfico")

    def test_outro_com_atalho(self):
        self.fluxo([rec("l1", "Salário", 5000, "2026-11-01", True)])
        self.clicar('[data-a="cx-periodo"][data-v="outro"]')
        self.assertEqual(self.folha(), "Período do fluxo")
        self.assertEqual(self.textos('.folha [data-a="cx-per-pre"]'), ["24 atrás", "12 + 12", "24 à frente", "36 atrás", "24 + 12", "36 à frente"])
        self.clicar('.folha [data-a="cx-per-pre"][data-v="24,0"]')
        self.assertIsNone(self.folha())
        self.assertEqual(self.textos('[data-a="cx-periodo"].on'), ["24 atrás"], "o botão mostra o período escolhido")
        m = self.meses_da_tabela()
        self.assertEqual((len(m), m[0], m[-1]), (24, "dez/24", "nov/26"), "para trás conta o mês atual")

    def test_outro_com_meses_digitados(self):
        self.fluxo([rec("l1", "Salário", 5000, "2026-11-01", True)])
        self.outro("12", "12")
        self.assertIsNone(self.folha())
        self.assertEqual(self.textos('[data-a="cx-periodo"].on'), ["12 + 12"])
        m = self.meses_da_tabela()
        self.assertEqual((len(m), m[0], m[-1]), (24, "dez/25", "nov/27 *"))

    def test_outro_com_periodo_invalido_avisa_e_nao_muda(self):
        self.fluxo([rec("l1", "Salário", 5000, "2026-11-01", True)])
        self.clicar('[data-a="cx-periodo"][data-v="outro"]')
        casos = (("0", "1", "Escolha pelo menos 2 meses."), ("61", "0", "Até 60 meses de cada lado."), ("-1", "12", "Use números de 0 a 60."))
        for atras, frente, msg in casos:
            with self.subTest(atras=atras, frente=frente):
                self.pg.fill('#per-atras', atras)
                self.pg.fill('#per-frente', frente)
                self.clicar('.folha-pe [data-a="cx-per-ok"]')
                self.assertEqual(self.aviso(), msg)
                self.assertEqual(self.folha(), "Período do fluxo", "a janela continua aberta para corrigir")
        self.clicar('.folha-cab [data-a="fechar"]')
        self.assertEqual(self.textos('[data-a="cx-periodo"].on'), ["6 + 6"], "o período continua o de antes")
        self.assertEqual(len(self.meses_da_tabela()), 12)

    def test_tabela_do_fluxo_bate_com_o_mes(self):
        self.fluxo([rec("l1", "Salário", 5000, "2026-11-01", True), desp("l2", "Aluguel", 1200, "2026-11-01", True),
                    desp("l3", "Internet", 99.9, "2026-11-20", False)], prever=False)
        nov = self.js("[...document.querySelectorAll('.tabela tbody tr')].map(r => [...r.cells].map(c => c.textContent)).find(r => r[0] === 'nov/26')")
        self.assertEqual(nov, ["nov/26", "R$ 5.000", "R$ 1.300", "R$ 3.700", "R$ 3.700"],
                         "entrou 5.000; saiu 1.200 + 99,90 (a pagar conta); sobrou e saldo 3.700")

    def test_media_do_que_sobrou_comeca_no_primeiro_mes_com_lancamentos(self):
        self.fluxo([rec("l1", "Freela", 1000, "2026-10-05", True), rec("l2", "Salário", 2000, "2026-11-01", True),
                    desp("l3", "Aluguel", 500, "2026-11-01", True)], prever=False)
        self.clicar('[data-a="cx-periodo"][data-v="passado"]')
        self.assertEqual(self.texto('#app .stat-duo').split("\n")[:3], ["Sobrou por mês, em média", "R$ 1.250", "out/26 a nov/26"],
                         "(1.000 + 1.500) / 2: os meses antes de outubro, vazios, não puxam a média")

    def test_prever_dia_a_dia_pode_ser_desligado(self):
        self.fluxo([desp(f"m{m}", "Mercado", v, f"2026-{m:02d}-10", True, categoria="c-mercado") for m, v in ((8, 300), (9, 600), (10, 900))])
        self.assertIn("Média dos gastos que não são fixos nem parcelas: R$ 600 por mês.", self.tela())
        self.assertIn("Dia a dia (média)", self.texto('#app .leg'))
        self.clicar('[data-a="ajuste"][data-k="prever_dia"]')
        self.assertIs(self.dados()["ajustes"]["prever_dia"], False, "vale para todos os aparelhos")
        self.assertNotIn("Dia a dia (média)", self.texto('#app .leg'))
        self.assertIn("fixos, parcelas e faturas já lançados", self.texto('#app .stat-duo'))


# ---------------------------------------------------------------------------------------------------------------
class TestAvisos(Caixa):
    """Os avisos do caixa no Início: atrasadas, as que vencem em até 5 dias e o caminho até elas."""

    def inicio(self, **dados):
        self.abrir(base(bancos=BANCOS, **dados), ui={"descAberto": None})

    def avisos(self):
        return self.textos('#app .op[data-a="cx-ir"]')

    def test_conta_atrasada_aparece_nos_avisos(self):
        self.inicio(lancamentos=[desp("l-luz", "Luz", 150, "2026-10-30", False), desp("l-merc", "Mercado", 80, "2026-10-29", True)])
        av = self.avisos()
        self.assertEqual(len(av), 1)
        self.assertIn("Uma conta atrasada\nLuz", av[0])
        self.assertIn("R$ 150", av[0])

    def test_conta_que_vence_em_ate_5_dias_aparece_nos_avisos(self):
        self.inicio(lancamentos=[desp("l-net", "Internet", 99.9, "2026-11-06", False), desp("l-agua", "Água", 80, "2026-11-08", False)])
        av = self.avisos()
        self.assertEqual(len(av), 1)
        self.assertIn("Vence nos próximos 5 dias\nInternet", av[0])
        self.assertIn("R$ 100", av[0])
        self.assertNotIn("Água", av[0], "a de daqui a 6 dias fica de fora")

    def test_fatura_atrasada_aparece_pelo_nome_da_fatura(self):
        self.inicio(lancamentos=[desp("l1", "Farmácia", 90, "2026-09-20", False, conta="k-ana", cartao=True),
                                 desp("l2", "Posto", 60, "2026-09-25", False, conta="k-ana", cartao=True)])
        av = self.avisos()
        self.assertEqual(len(av), 1)
        self.assertIn("Uma conta atrasada\nFatura Banco Azul · Ana", av[0], "uma fatura, não duas compras")
        self.assertIn("R$ 150", av[0])
        self.ir("caixa")
        self.mes(-1)
        self.assertIn("Atrasada", self.faturas()[0], "a fatura de 12/10 está atrasada")

    def test_aporte_atrasado_aparece_nos_avisos(self):
        self.inicio(recorrencias=[fixo("r-ap", "Aporte", 800, 1, "2026-11", aporte=True, categoria="c-investimentos")])
        av = self.avisos()
        self.assertEqual(len(av), 1)
        self.assertIn("Uma conta atrasada\nAporte", av[0], "o aporte é um compromisso, como as contas")

    def test_tocar_no_aviso_abre_o_caixa_em_a_pagar_e_receber(self):
        self.inicio(lancamentos=[desp("l-net", "Internet", 99.9, "2026-11-01", False), desp("l-merc", "Mercado", 80, "2026-11-01", True)])
        self.clicar('#app .op[data-a="cx-ir"]')
        self.assertEqual(self.js("T.S.ui.tab"), "caixa")
        self.assertEqual(self.textos('[data-a="cx-filtro"].on'), ["A pagar e receber"])
        self.assertEqual(self.ids(), ["l-net"])

    def test_1_56_1_os_indices_so_quando_pedem_uma_acao(self):
        # os índices não são um aviso: ficam em Mais › Invest; sem nada a fazer, nenhum cartão de Avisos
        self.inicio(investimentos=[{"id": "cdb-azul", "nome": "CDB Azul", "banco": "b-azul", "valor": 1000, "indexador": "parado", "tipo": "cdb", "data_valor": "2026-11-01", "titular": "meu"}])
        indices = lambda **x: self.js("(Object.assign(T.S.d.indices, a), T.render(), true)", x)
        indices(fonte="bcb", auto=True, atualizado_em="2026-11-02T09:00:00-03:00", erro=None)
        self.assertEqual(self.conta('#app .op[data-ancora="indices"]'), 0, "índices em dia: fora dos Avisos")
        self.assertNotIn("Avisos", self.textos("#app .rot-t"), "nada a fazer: sem o cartão")
        indices(atualizado_em="2026-10-31T09:00:00-03:00")
        self.assertEqual(self.conta('#app .op[data-ancora="indices"]'), 0, "há 2 dias: ainda em dia")
        # do Banco Central, mas parados há mais de 3 dias: aí sim, para conferir
        indices(atualizado_em="2026-10-28T09:00:00-03:00", erro="Sem resposta do Banco Central")
        self.assertEqual(self.textos('#app .op[data-ancora="indices"]'), ["Índices sem atualizar\nO Banco Central não responde desde 28/10"])
        self.assertIn("Avisos", self.textos("#app .rot-t"))
        self.clicar('#app .op[data-ancora="indices"]')
        self.assertEqual(self.js("T.S.ui.maisTela"), "invest", "toca e abre Mais › Invest, nos índices")
        self.inicio(investimentos=[{"id": "cdb-azul", "nome": "CDB Azul", "banco": "b-azul", "valor": 1000, "indexador": "parado", "tipo": "cdb", "data_valor": "2026-11-01", "titular": "meu"}])
        indices(fonte="manual", atualizado_em="2026-09-01T09:00:00-03:00", erro=None)
        self.assertEqual(self.conta('#app .op[data-ancora="indices"]'), 0, "digitados à mão: nunca")

    # (era bug até a 1.24.0: o aviso abria o mês de hoje, sem a conta atrasada do mês passado)
    def test_tocar_no_aviso_mostra_a_conta_atrasada_do_mes_passado(self):
        self.inicio(lancamentos=[desp("l-luz", "Luz", 150, "2026-10-30", False)])
        self.clicar('#app .op[data-a="cx-ir"]')
        self.assertIn("l-luz", self.ids(), "a conta do aviso aparece no caixa")


if __name__ == "__main__":
    unittest.main()
