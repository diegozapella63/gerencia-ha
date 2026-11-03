"""Aplicar mais, Transferir, os gráficos do Caixa ao tocar e alguns campos com tratamento próprio, na tela de verdade.

- Aplicar mais num investimento: Quanto apliquei e Quanto tem agora (o aporte é a diferença), a escolha no caixa
  (baixa no aporte do mês, lançar à parte, não lançar), a conta, os erros e o que fica gravado em cada caso.
- Transferir entre investimentos: valor, Tudo, destino (os do mesmo dono primeiro), manter ou tirar da carteira,
  mais do que tem, e o que fica gravado (o caixa não muda).
- Os gráficos do Caixa ao tocar ou passar o dedo: Fluxo e Saldo em caixa (o quadrinho com o mês e os valores) e
  Categorias com muitas categorias (as menores juntas em "Outras").
- Campos: o valor e a data do Mudar para anual (dica de plano anual), a última verificação das dicas ("hoje às..."),
  a Observação do lançamento, as vezes do parcelado (a janela se redesenha sem tirar o cursor) e o desconto em reais.

Os fluxos com o servidor de verdade estão em tests/e2e/aplicar_e2e.py, aplicar_total.py e transferir_e2e.py; aqui é a
prévia (tests/tela_base.py: relógio parado em 02/11/2026 10:00, tela de 390 px). Valores feitos à mão: os investimentos
têm o valor de hoje (data_valor = 02/11/2026), então o valor de hoje é o próprio valor.

Os testes marcados com @unittest.expectedFailure esperam o certo e falham hoje: são bugs suspeitos (veja o "BUG:").
Dados sempre inventados (Ana, Beto, Carla, Banco Azul, Banco Verde).
"""
import unittest

from tests.tela_base import Tela, base, BANCOS

HOJE_ISO = "2026-11-02"


def inv(id_, nome, valor, **mais):
    d = {"id": id_, "nome": nome, "valor": valor, "data_valor": HOJE_ISO, "tipo": "cdb", "banco": "b-azul", "indexador": "cdi_pct", "taxa": 100,
         "liquidez": "vencimento", "vencimento": None, "titular": "meu", "terceiro": "", "obs": ""}
    d.update(mais)
    return d


def desp(id_, descricao, valor, data, pago=False, **mais):
    return dict(id=id_, tipo="despesa", descricao=descricao, valor=valor, data=data, pago=pago, **mais)


def rec(id_, descricao, valor, data, pago=False, **mais):
    return dict(id=id_, tipo="receita", descricao=descricao, valor=valor, data=data, pago=pago, **mais)


CDB = inv("i-cdb", "CDB Azul", 10000)
LCI = inv("i-lci", "LCI Verde", 3000, banco="b-verde", tipo="lci")
TES = inv("i-tes", "Tesouro Verde", 4000, banco="b-verde", tipo="tesouro", indexador="selic_mais", taxa=0, liquidez="diaria")
CARLA = inv("i-carla", "Poupança da Carla", 2500, banco="b-verde", tipo="poupanca", indexador="poupanca", taxa=0, liquidez="diaria",
            titular="terceiros", terceiro="Carla")
BETO = inv("i-beto", "Caixinha do Beto", 1200, tipo="caixinha", liquidez="diaria", titular="terceiros", terceiro="Beto")

# o aporte fixo do mês (dia 10, sai do Banco Verde); o de outubro já foi aplicado
APORTE = {"id": "r-ap", "tipo": "despesa", "aporte": True, "descricao": "Aporte nos investimentos", "valor": 800, "dia": 10, "inicio": "2026-01",
          "conta": "k-verde", "categoria": "c-investimentos"}
APORTE_OUT = desp("l-ap10", "Aporte nos investimentos", 800, "2026-10-10", True, aporte=True, recorrencia="r-ap", competencia="2026-10",
                  conta="k-verde", categoria="c-investimentos", investimento="i-tes")

_PAGINA = {}  # um Chromium só para todas as classes deste arquivo


def tearDownModule():
    if _PAGINA:
        _PAGINA["b"].close()
        _PAGINA["pw"].stop()
        _PAGINA.clear()


class _Tela(Tela):
    """A base com ajudantes desta área (sem testes aqui)."""

    @classmethod
    def setUpClass(cls):
        if not _PAGINA:
            super().setUpClass()
            # "reduzir movimento": o app tira as animações e o clique não espera a janela parar de subir
            cls.pg.emulate_media(reduced_motion="reduce")
            cls.pg.set_default_timeout(5000)
            _PAGINA.update(pw=cls.pw, b=cls.b, ctx=cls.ctx, pg=cls.pg, erros=cls.erros)
        for k, v in _PAGINA.items():
            setattr(cls, k, v)

    @classmethod
    def tearDownClass(cls):
        pass  # o navegador fecha no fim do arquivo (tearDownModule)

    def tearDown(self):
        self.js("(clearTimeout(T.pfT), true)")
        super().tearDown()

    def abrir(self, d=None, ui=None, bens=None):
        # um pedido de dicas agendado por um teste anterior (depois de salvar) não entra no meio deste
        self.js("(clearTimeout(T.dicasAgenda), clearTimeout(T.dicasTimer), true)")
        super().abrir(d, ui, bens)

    def ativo(self):
        return self.js("document.activeElement && document.activeElement.id")

    def valor_campo(self, sel):
        return self.pg.input_value(sel)

    def investimento(self, id_):
        return next((i for i in self.dados()["investimentos"] if i["id"] == id_), None)

    def editar(self, d, id_):
        """Abre o app na aba Invest e o investimento (Editar investimento)."""
        self.abrir(d, ui={"tab": "investimentos"})
        self.clicar(f'#app .inv[data-id="{id_}"]')
        self.assertEqual(self.folha(), "Editar investimento")


# =============================================================================================== Aplicar mais
class TestAplicar(_Tela):
    def aplicar(self, d, id_="i-cdb"):
        self.editar(d, id_)
        self.clicar('.folha [data-a="inv-aplicar"]')

    def destinos(self):
        return [t.strip() for t in self.textos('.folha [data-a="ap-destino"]')]

    def destino_on(self):
        return [t.strip() for t in self.textos('.folha [data-a="ap-destino"].on')]

    def contas_chips(self):
        return [t.strip() for t in self.textos('.folha [data-a="ap-conta"]')]

    def ok(self):
        self.clicar('.folha-pe [data-a="ap-ok"]')

    def test_abre_do_investimento_com_o_teclado_no_valor(self):
        self.editar(base(bancos=BANCOS, investimentos=[CDB, TES]), "i-cdb")
        self.assertEqual([t.strip() for t in self.textos('.folha .inv-acoes .btn')], ["Aplicar mais", "Transferir"])
        larg = self.js("[...document.querySelectorAll('.folha .inv-acoes .btn')].map(b => Math.round(b.getBoundingClientRect().width))")
        self.assertEqual(len(set(larg)), 1, f"os dois botões do mesmo tamanho {larg}")
        self.clicar('.folha [data-a="inv-aplicar"]')
        self.assertEqual(self.folha(), "Aplicar em CDB Azul")
        self.assertEqual(self.ativo(), "ap-v", "o teclado já abre no valor")
        self.assertEqual(self.textos('.folha .ap-modo button.on'), ["Quanto apliquei"])
        self.assertEqual(self.texto('label[for="ap-v"]'), "Quanto você aplicou")
        self.assertEqual(self.texto('#ap-ajuda'), "Hoje: R$ 10.000,00.")
        self.assertEqual((self.valor_campo('#ap-data'), self.pg.get_attribute('#ap-data', 'max')), (HOJE_ISO, HOJE_ISO), "hoje, e nada depois de hoje")
        self.assertEqual(self.destinos(), ["Lançar como aporte", "Não lançar"], "sem aporte a aplicar, não há baixa")
        self.assertEqual(self.destino_on(), ["Lançar como aporte"])
        self.assertEqual(self.contas_chips(), ["Banco Azul · Ana", "Banco Azul · Beto", "Banco Verde · Ana"])
        self.assertEqual([t.strip() for t in self.textos('.folha [data-a="ap-conta"].on')], ["Banco Verde · Ana"],
                         "a conta sem cartão (o aporte sai da conta, não do cartão)")
        self.assertEqual(self.texto('.folha-pe [data-a="ap-ok"]'), "Aplicar")

    def test_conta_de_onde_saiu_a_ultima_despesa_vem_marcada(self):
        bancos = BANCOS + [{"id": "b-lar", "nome": "Banco Laranja", "cor": "#FFA23A", "contas": [{"id": "k-carla", "pessoa": "Carla", "cartao": False}]}]
        marcada = lambda: [t.strip() for t in self.textos('.folha [data-a="ap-conta"].on')]  # noqa: E731
        self.editar(base(bancos=bancos, investimentos=[CDB], lancamentos=[desp("l1", "Mercado", 80, "2026-11-01", True, conta="k-carla")]), "i-cdb")
        self.assertEqual([t.strip() for t in self.textos('.folha .inv-acoes .btn')], ["Aplicar mais"], "com um investimento só, não há para onde transferir")
        self.clicar('.folha [data-a="inv-aplicar"]')
        self.assertEqual(marcada(), ["Banco Laranja · Carla"], "a conta da última despesa")
        # a última despesa foi num cartão: a primeira conta sem cartão
        self.aplicar(base(bancos=bancos, investimentos=[CDB], lancamentos=[desp("l1", "Mercado", 80, "2026-11-01", True, conta="k-beto", cartao=True)]))
        self.assertEqual(marcada(), ["Banco Verde · Ana"])

    def test_lancar_como_aporte_grava_o_investimento_e_a_saida_no_caixa(self):
        self.aplicar(base(bancos=BANCOS, investimentos=[CDB, TES]))
        self.digitar('#ap-v', '150000')
        self.assertEqual(self.valor_campo('#ap-v'), "1.500,00", "os números entram como centavos")
        self.assertEqual(self.texto('#ap-ajuda'), "R$ 10.000,00 → R$ 11.500,00.")
        self.assertEqual(self.texto('.folha-pe [data-a="ap-ok"]'), "Aplicar R$ 1.500")
        self.clicar('.folha [data-a="ap-conta"][data-v="k-beto"]')
        self.assertEqual(self.valor_campo('#ap-v'), "1.500,00", "trocar a conta não apaga o valor")
        self.ok()
        self.assertIsNone(self.folha(), "a janela fecha")
        self.assertEqual(self.aviso(), "Aplicado R$ 1.500 em CDB Azul")
        d = self.dados()
        cdb = next(i for i in d["investimentos"] if i["id"] == "i-cdb")
        self.assertEqual((cdb["valor"], cdb["data_valor"]), (11500, HOJE_ISO), "10.000 + 1.500, com o valor de hoje")
        self.assertTrue(cdb.get("atualizado_em"))
        self.assertEqual(next(i for i in d["investimentos"] if i["id"] == "i-tes")["valor"], 4000, "o outro não muda")
        (l,) = d["lancamentos"]
        self.assertEqual((l["tipo"], l["aporte"], l["descricao"], l["valor"], l["categoria"], l["conta"], l["cartao"], l["data"], l["pago"], l["investimento"]),
                         ("despesa", True, "Aporte: CDB Azul", 1500, "c-investimentos", "k-beto", False, HOJE_ISO, True, "i-cdb"))

    def test_lancar_com_data_de_antes_vai_para_o_dia_escolhido(self):
        self.aplicar(base(bancos=BANCOS, investimentos=[CDB]))
        self.digitar('#ap-v', '20000')
        self.preencher('#ap-data', '2026-10-28')
        self.assertEqual(self.valor_campo('#ap-v'), "200,00", "a data não apaga o valor")
        self.ok()
        (l,) = self.dados()["lancamentos"]
        self.assertEqual((l["data"], l["pago"], l["valor"]), ("2026-10-28", True, 200), "o aporte no dia em que foi feito, já pago")
        self.assertEqual(self.investimento("i-cdb")["data_valor"], HOJE_ISO, "o investimento fica com o valor de hoje")

    def test_sem_a_categoria_investimentos_ela_volta(self):
        cats = self.js("T.CATEGORIAS_PADRAO.filter(c => c.id !== 'c-investimentos')")
        self.aplicar(base(bancos=BANCOS, investimentos=[CDB], categorias=cats))
        self.assertFalse(self.js("T.S.d.categorias.some(c => c.id === 'c-investimentos')"), "a categoria foi apagada")
        self.digitar('#ap-v', '10000')
        self.ok()
        d = self.dados()
        self.assertEqual([c["nome"] for c in d["categorias"] if c["id"] == "c-investimentos"], ["Investimentos"], "a categoria do aporte volta")
        self.assertEqual(d["lancamentos"][0]["categoria"], "c-investimentos")

    def test_nao_lancar_so_soma_no_investimento(self):
        self.aplicar(base(bancos=BANCOS, investimentos=[CDB]))
        self.digitar('#ap-v', '99999')
        self.clicar('.folha [data-a="ap-destino"][data-v="nenhum"]')
        self.assertEqual(self.contas_chips(), [], "sem lançar, não pergunta a conta")
        self.assertEqual(self.valor_campo('#ap-v'), "999,99")
        self.ok()
        d = self.dados()
        self.assertEqual(d["investimentos"][0]["valor"], 10999.99)
        self.assertEqual(d["lancamentos"], [], "nada no caixa")
        self.assertEqual(self.aviso(), "Aplicado R$ 1.000 em CDB Azul", "o aviso arredonda para reais")

    def test_baixa_no_aporte_do_mes(self):
        self.aplicar(base(bancos=BANCOS, investimentos=[CDB, TES], recorrencias=[APORTE], lancamentos=[APORTE_OUT]))
        self.assertEqual(self.destinos(), ["Baixa no aporte de novembro (R$ 800)", "Lançar à parte", "Não lançar"])
        self.assertEqual(self.destino_on(), ["Baixa no aporte de novembro (R$ 800)"], "com aporte a aplicar, a baixa vem marcada")
        self.assertEqual(self.texto('.folha .campo:has([data-a="ap-destino"]) .ajuda'), "Sai de Banco Verde · Ana.")
        self.assertEqual(self.contas_chips(), [], "a conta é a do aporte")
        self.digitar('#ap-v', '90000')
        self.ok()
        self.assertEqual(self.aviso(), "Aplicado R$ 900 em CDB Azul")
        d = self.dados()
        self.assertEqual(self.investimento("i-cdb")["valor"], 10900)
        nov = [l for l in d["lancamentos"] if l.get("competencia") == "2026-11"]
        self.assertEqual(len(d["lancamentos"]), 2, "o aporte de novembro passa a existir (e o de outubro continua)")
        (l,) = nov
        self.assertEqual((l["recorrencia"], l["valor"], l["pago"], l["investimento"], l["data"], l["conta"], l.get("aporte")),
                         ("r-ap", 900, True, "i-cdb", "2026-11-10", "k-verde", True), "a baixa com o valor aplicado, no dia do aporte")
        r = d["recorrencias"][0]
        self.assertEqual((r["valor"], r["investimento"]), (800, "i-cdb"), "o fixo continua 800 e passa a lembrar o investimento")
        self.assertEqual(self.js("T.aportesPendentes().length"), 0, "nada mais a aplicar")

    def test_baixa_num_aporte_ja_lancado(self):
        tes_mes = desp("l-tm", "Tesouro do mês", 500, "2026-11-08", aporte=True, conta="k-ana", categoria="c-investimentos")
        self.aplicar(base(bancos=BANCOS, investimentos=[TES, CDB], lancamentos=[tes_mes]), "i-tes")
        self.assertEqual(self.destino_on(), ["Baixa no Tesouro do mês de novembro (R$ 500)"], "o nome do aporte quando não começa com Aporte")
        self.assertEqual(self.texto('.folha .campo:has([data-a="ap-destino"]) .ajuda'), "Sai de Banco Azul · Ana.")
        self.digitar('#ap-v', '45000')
        self.ok()
        d = self.dados()
        (l,) = d["lancamentos"]
        self.assertEqual((l["id"], l["valor"], l["pago"], l["investimento"], l["data"]), ("l-tm", 450, True, "i-tes", "2026-11-08"),
                         "o mesmo lançamento, pago com o valor aplicado")
        self.assertEqual(self.investimento("i-tes")["valor"], 4450)

    def test_dois_aportes_a_aplicar_o_mais_perto_de_hoje_primeiro(self):
        # sem o de outubro lançado: outubro (dia 10, 23 dias atrás) e novembro (dia 10, daqui a 8 dias) estão a aplicar
        self.aplicar(base(bancos=BANCOS, investimentos=[CDB], recorrencias=[APORTE]))
        self.assertEqual(self.destinos(), ["Baixa no aporte de novembro (R$ 800)", "Baixa no aporte de outubro (R$ 800)", "Lançar à parte", "Não lançar"])
        self.digitar('#ap-v', '80000')
        self.clicar('.folha [data-a="ap-destino"][data-v="v:r-ap:2026-10"]')
        self.assertEqual(self.destino_on(), ["Baixa no aporte de outubro (R$ 800)"])
        self.assertEqual(self.valor_campo('#ap-v'), "800,00", "trocar a opção do caixa não apaga o valor")
        self.ok()
        (l,) = self.dados()["lancamentos"]
        self.assertEqual((l["competencia"], l["data"], l["pago"], l["valor"]), ("2026-10", "2026-10-10", True, 800), "a baixa no de outubro")
        self.assertEqual(self.js("T.aportesPendentes().map(l => l.id)"), ["v:r-ap:2026-11"], "o de novembro continua a aplicar")

    def test_lancar_a_parte_deixa_o_aporte_do_mes_a_aplicar(self):
        self.aplicar(base(bancos=BANCOS, investimentos=[CDB], recorrencias=[APORTE], lancamentos=[APORTE_OUT]))
        self.clicar('.folha [data-a="ap-destino"][data-v="novo"]')
        self.assertEqual(self.contas_chips(), ["Banco Azul · Ana", "Banco Azul · Beto", "Banco Verde · Ana"], "lançar à parte pergunta a conta")
        self.assertEqual(self.conta('.folha .campo:has([data-a="ap-destino"]) .ajuda'), 0)
        self.digitar('#ap-v', '30000')
        self.ok()
        d = self.dados()
        novos = [l for l in d["lancamentos"] if l["id"] != "l-ap10"]
        self.assertEqual([(l["descricao"], l["valor"], l["conta"], l.get("recorrencia")) for l in novos], [("Aporte: CDB Azul", 300, "k-verde", None)])
        self.assertEqual(self.js("T.aportesPendentes().map(l => l.id)"), ["v:r-ap:2026-11"], "o aporte do mês continua a aplicar")
        self.assertNotIn("investimento", d["recorrencias"][0], "o fixo não muda")

    def test_dinheiro_de_terceiros_nao_mexe_no_caixa(self):
        self.aplicar(base(bancos=BANCOS, investimentos=[CDB, CARLA], recorrencias=[APORTE], lancamentos=[APORTE_OUT]), "i-carla")
        self.assertEqual(self.folha(), "Aplicar em Poupança da Carla")
        self.assertEqual(self.destinos(), ["Lançar como aporte", "Não lançar"], "o aporte do mês é seu: não aparece para terceiros")
        self.assertEqual(self.destino_on(), ["Não lançar"])
        self.assertEqual(self.texto('.folha .campo:has([data-a="ap-destino"]) .ajuda'), "Dinheiro de terceiros não mexe no caixa.")
        self.digitar('#ap-v', '30000')
        self.ok()
        d = self.dados()
        self.assertEqual(self.investimento("i-carla")["valor"], 2800)
        self.assertEqual([l["id"] for l in d["lancamentos"]], ["l-ap10"], "nada novo no caixa")
        self.assertNotIn("investimento", d["recorrencias"][0])

    def test_sem_valor_nao_aplica(self):
        self.aplicar(base(bancos=BANCOS, investimentos=[CDB]))
        self.ok()
        self.assertEqual(self.folha(), "Aplicar em CDB Azul", "continua aberta para corrigir")
        self.assertEqual(self.textos('.folha .msg-erro'), ["Coloque o valor."])
        self.assertEqual(self.conta('.folha .pref.grande.erro'), 1, "o campo fica em vermelho")
        self.assertEqual((self.investimento("i-cdb")["valor"], self.dados()["lancamentos"]), (10000, []), "nada gravado")
        self.digitar('#ap-v', '5000')
        self.ok()
        self.assertIsNone(self.folha(), "com o valor, aplica")
        self.assertEqual(self.investimento("i-cdb")["valor"], 10050)

    def test_quanto_tem_agora_o_aporte_e_a_diferenca(self):
        self.aplicar(base(bancos=BANCOS, investimentos=[CDB]))
        self.clicar('.folha [data-a="ap-modo"][data-v="total"]')
        self.assertEqual(self.textos('.folha .ap-modo button.on'), ["Quanto tem agora"])
        self.assertEqual(self.texto('label[for="ap-v"]'), "Quanto tem agora, no total")
        self.assertEqual(self.texto('#ap-ajuda'), "Hoje: R$ 10.000,00. O aporte é a diferença.")
        self.assertEqual(self.ativo(), "ap-v", "o teclado continua no valor")
        self.digitar('#ap-v', '1250000')
        self.assertEqual(self.valor_campo('#ap-v'), "12.500,00")
        self.assertEqual(self.texto('#ap-ajuda'), "Aporte de R$ 2.500,00: de R$ 10.000,00 para R$ 12.500,00.")
        self.assertEqual(self.texto('.folha-pe [data-a="ap-ok"]'), "Aplicar R$ 2.500")
        self.ok()
        self.assertEqual(self.aviso(), "Aplicado R$ 2.500 em CDB Azul")
        d = self.dados()
        self.assertEqual(d["investimentos"][0]["valor"], 12500, "fica com o total")
        self.assertEqual([(l["descricao"], l["valor"]) for l in d["lancamentos"]], [("Aporte: CDB Azul", 2500)], "no caixa sai só a diferença")

    def test_total_menor_ou_igual_ao_de_hoje_nao_aplica(self):
        self.aplicar(base(bancos=BANCOS, investimentos=[CDB]))
        self.clicar('.folha [data-a="ap-modo"][data-v="total"]')
        self.ok()
        self.assertEqual(self.textos('.folha .msg-erro'), ["Coloque o total."], "sem total")
        self.digitar('#ap-v', '900000')
        self.assertEqual(self.texto('#ap-ajuda'), "É menos que os R$ 10.000,00 de hoje. Para corrigir o valor, edite o investimento.")
        self.assertEqual(self.texto('.folha-pe [data-a="ap-ok"]'), "Aplicar", "sem aporte, sem valor no botão")
        self.ok()
        self.assertEqual(self.textos('.folha .msg-erro'), ["O total precisa ser maior que os R$ 10.000,00 de hoje."])
        self.assertEqual(self.valor_campo('#ap-v'), "9.000,00", "o total digitado continua no campo")
        self.digitar('#ap-v', '1000000')
        self.ok()
        self.assertEqual(self.textos('.folha .msg-erro'), ["O total precisa ser maior que os R$ 10.000,00 de hoje."], "igual ao de hoje também não")
        self.assertEqual((self.investimento("i-cdb")["valor"], self.dados()["lancamentos"]), (10000, []), "nada gravado")

    def test_trocar_o_modo_comeca_do_zero(self):
        self.aplicar(base(bancos=BANCOS, investimentos=[CDB]))
        self.digitar('#ap-v', '50000')
        self.clicar('.folha [data-a="ap-modo"][data-v="aplicou"]')
        self.assertEqual(self.valor_campo('#ap-v'), "500,00", "tocar no modo que já está não apaga")
        self.clicar('.folha [data-a="ap-modo"][data-v="total"]')
        self.assertEqual((self.valor_campo('#ap-v'), self.texto('.folha-pe [data-a="ap-ok"]')), ("", "Aplicar"), "o outro modo começa vazio")
        self.digitar('#ap-v', '1100000')
        self.clicar('.folha [data-a="ap-modo"][data-v="aplicou"]')
        self.assertEqual((self.valor_campo('#ap-v'), self.texto('#ap-ajuda')), ("", "Hoje: R$ 10.000,00."))
        self.assertEqual(self.js("[T.AP.valor, T.AP.total]"), [0, 0])

    def test_valor_que_ja_rendeu_soma_no_valor_de_hoje(self):
        velho = dict(CDB, data_valor="2026-05-04")
        self.aplicar(base(bancos=BANCOS, investimentos=[velho]))
        hoje = self.js("T.valorHoje(T.S.d.investimentos[0])")
        self.assertGreater(hoje, 10500, "de maio até hoje, 100% do CDI rendeu mais de 5%")
        brl = lambda v: self.js("T.brl(a)", v)  # noqa: E731
        self.assertEqual(self.texto('#ap-ajuda'), f"Hoje: {brl(hoje)}.")
        self.digitar('#ap-v', '100000')
        self.assertEqual(self.texto('#ap-ajuda'), f"{brl(hoje)} → {brl(hoje + 1000)}.")
        self.ok()
        cdb = self.investimento("i-cdb")
        self.assertEqual((cdb["valor"], cdb["data_valor"]), (round(hoje + 1000, 2), HOJE_ISO), "o valor de hoje mais o aporte, com a data de hoje")

    def test_cancelar_nao_grava(self):
        self.aplicar(base(bancos=BANCOS, investimentos=[CDB]))
        self.digitar('#ap-v', '100000')
        self.clicar('.folha-pe [data-a="fechar"]')
        self.assertEqual((self.investimento("i-cdb")["valor"], self.dados()["lancamentos"]), (10000, []))

    # (era bug até a 1.24.2)
    def test_cancelar_volta_para_o_investimento(self):
        self.aplicar(base(bancos=BANCOS, investimentos=[CDB, TES]))
        self.clicar('.folha-pe [data-a="fechar"]')
        self.assertEqual(self.folha(), "Editar investimento")

    # (era bug até a 1.24.2)
    def test_aplicar_num_bem_separado_por_categoria_soma_no_valor_de_hoje(self):
        bem = inv("i-bem", "Móveis da sala", 10000, tipo="bens", banco="", indexador="deprecia", taxa=13, liquidez="diaria", categoria_bem="moveis",
                  partes=[{"categoria": "moveis", "valor": 7000, "taxa": 10}, {"categoria": "eletronicos", "valor": 3000, "taxa": 20}])
        self.aplicar(base(bancos=BANCOS, investimentos=[bem, CDB]), "i-bem")
        self.clicar('.folha [data-a="ap-destino"][data-v="nenhum"]')
        self.digitar('#ap-v', '100000')
        self.assertEqual(self.texto('#ap-ajuda'), "R$ 10.000,00 → R$ 11.000,00.")
        self.ok()
        self.assertAlmostEqual(self.js("T.valorHoje(T.S.d.investimentos.find(i => i.id === 'i-bem'))"), 11000, places=2)


class TestAporteNoInvestimento(_Tela):
    """O aporte do caixa já aplicado pergunta em qual investimento (só os seus) e soma nele."""

    def test_apliquei_no_caixa_pergunta_em_qual_investimento(self):
        self.abrir(base(bancos=BANCOS, investimentos=[CDB, TES, CARLA], recorrencias=[APORTE], lancamentos=[APORTE_OUT]), ui={"tab": "caixa"})
        self.clicar('button.visto[data-id="v:r-ap:2026-11"]')
        self.assertEqual(self.folha(), "Confirmar aporte")
        self.assertEqual([t.strip() for t in self.textos('.folha [data-a="pg-inv"]')], ["CDB Azul", "Tesouro Verde"], "só os seus")
        self.assertEqual(self.conta('.folha [data-a="pg-inv"].on'), 0, "com dois, nenhum vem escolhido")
        self.clicar('.folha-pe [data-a="pg-ok"]')
        self.assertEqual(self.textos('.folha .msg-erro'), ["Escolha em qual investimento o aporte foi aplicado."])
        self.clicar('.folha [data-a="pg-inv"][data-v="i-tes"]')
        self.assertEqual(self.textos('.folha .msg-erro'), [], "escolher tira o erro")
        self.assertEqual(self.texto('.folha .campo:has([data-a="pg-inv"]) .ajuda'), "Tesouro Verde: R$ 4.000,00 → R$ 4.800,00.")
        self.clicar('.folha-pe [data-a="pg-ok"]')
        self.assertEqual(self.aviso(), "Aplicado em Tesouro Verde")
        d = self.dados()
        self.assertEqual(self.investimento("i-tes")["valor"], 4800)
        self.assertEqual(d["recorrencias"][0]["investimento"], "i-tes", "o fixo lembra o investimento")
        (l,) = [x for x in d["lancamentos"] if x.get("competencia") == "2026-11"]
        self.assertEqual((l["pago"], l["valor"], l["investimento"]), (True, 800, "i-tes"))

    def test_aporte_novo_ja_aplicado_soma_no_investimento(self):
        self.abrir(base(bancos=BANCOS, investimentos=[CDB, TES, CARLA]), ui={"tab": "caixa"})
        self.clicar('#nav [data-a="novo"]')
        self.clicar('.folha [data-a="lf-tipo"][data-v="aporte"]')
        self.digitar('#lf-valor', '50000')
        self.assertEqual(self.conta('.folha [data-a="lf-inv"]'), 0, "a aplicar não pergunta o investimento")
        self.clicar('.folha [data-a="lf-pago"][data-v="1"]')
        self.assertEqual([t.strip() for t in self.textos('.folha [data-a="lf-inv"]')], ["CDB Azul", "Tesouro Verde"])
        self.clicar('.folha-pe [data-a="lf-salvar"]:not([data-mais])')
        self.assertEqual(self.textos('.folha .msg-erro'), ["Escolha em qual investimento o aporte foi aplicado."], "sem escolher não salva")
        self.clicar('.folha [data-a="lf-inv"][data-v="i-cdb"]')
        self.assertEqual(self.textos('.folha .msg-erro'), [])
        self.assertEqual(self.texto('.folha .campo:has([data-a="lf-inv"]) .ajuda'), "CDB Azul: R$ 10.000,00 → R$ 10.500,00.")
        self.clicar('.folha-pe [data-a="lf-salvar"]:not([data-mais])')
        self.assertEqual(self.aviso(), "Aporte cadastrado: todo mês, também na projeção")
        d = self.dados()
        self.assertEqual(self.investimento("i-cdb")["valor"], 10500, "o aporte soma no CDB")
        (r,) = d["recorrencias"]
        self.assertEqual((r["aporte"], r["valor"], r["investimento"], r["dia"]), (True, 500, "i-cdb", 2), "o fixo do aporte lembra o investimento")
        (l,) = d["lancamentos"]
        self.assertEqual((l["recorrencia"], l["competencia"], l["pago"], l["valor"]), (r["id"], "2026-11", True, 500), "o de novembro já aplicado")

    def test_aplicado_pelo_formulario_do_aporte_do_mes(self):
        self.abrir(base(bancos=BANCOS, investimentos=[CDB, TES], recorrencias=[APORTE], lancamentos=[APORTE_OUT]), ui={"tab": "caixa"})
        self.clicar('.lanc[data-id="v:r-ap:2026-11"]')
        self.assertEqual(self.texto('.folha [data-a="lf-pago"].on'), "A aplicar")
        self.clicar('.folha [data-a="lf-pago"][data-v="1"]')
        self.clicar('.folha [data-a="lf-inv"][data-v="i-cdb"]')
        self.clicar('.folha-pe [data-a="lf-salvar"][data-v="este"]')
        d = self.dados()
        self.assertEqual(self.investimento("i-cdb")["valor"], 10800)
        self.assertEqual(d["recorrencias"][0]["investimento"], "i-cdb", "o fixo passa a lembrar o investimento")
        (l,) = [x for x in d["lancamentos"] if x.get("competencia") == "2026-11"]
        self.assertEqual((l["pago"], l["valor"], l["recorrencia"]), (True, 800, "r-ap"))


# =============================================================================================== Transferir
class TestTransferir(_Tela):
    def transferir(self, d, id_="i-cdb"):
        self.editar(d, id_)
        self.clicar('.folha [data-a="inv-transferir"]')

    def para(self):
        return self.js("[...document.querySelectorAll('.folha [data-a=\"tr-para\"]')].map(b => b.innerText.replace(/\\s+/g, ' ').trim())")

    def ok(self):
        self.clicar('.folha-pe [data-a="tr-ok"]')

    def test_abre_com_os_do_mesmo_dono_primeiro(self):
        self.transferir(base(bancos=BANCOS, investimentos=[CDB, CARLA, TES, BETO, LCI]))
        self.assertEqual(self.folha(), "Transferir de CDB Azul")
        self.assertEqual(self.ativo(), "tr-v", "o teclado já abre no valor")
        self.assertEqual(self.para(), ["LCI Verde", "Tesouro Verde", "Caixinha do Beto · Beto", "Poupança da Carla · Carla"],
                         "os seus primeiro (em ordem de nome), depois os de terceiros com o dono")
        self.assertEqual(self.texto('.folha [data-a="tr-tudo"]'), "Tudo (R$ 10.000)")
        self.assertEqual(self.texto('#tr-ajuda'), "Hoje: R$ 10.000,00.")
        self.assertIn("Não mexe no caixa.", self.folha_texto())
        self.assertEqual(self.texto('.folha-pe [data-a="tr-ok"]'), "Transferir")
        self.assertEqual(self.conta('.folha [data-a="tr-apagar"]'), 0, "só pergunta se tira da carteira quando passa tudo")
        # de um dinheiro de terceiros: os de terceiros primeiro
        self.transferir(base(bancos=BANCOS, investimentos=[CDB, CARLA, TES, BETO]), "i-carla")
        self.assertEqual(self.para(), ["Caixinha do Beto · Beto", "CDB Azul", "Tesouro Verde"])

    def test_transferir_parte_tira_de_um_e_soma_no_outro(self):
        self.transferir(base(bancos=BANCOS, investimentos=[CDB, TES, CARLA], lancamentos=[desp("l1", "Mercado", 80, "2026-11-01", True)]))
        self.digitar('#tr-v', '250000')
        self.assertEqual(self.valor_campo('#tr-v'), "2.500,00")
        self.assertEqual(self.texto('#tr-ajuda'), "CDB Azul fica com R$ 7.500,00.")
        self.assertEqual(self.texto('.folha-pe [data-a="tr-ok"]'), "Transferir R$ 2.500")
        self.clicar('.folha [data-a="tr-para"][data-v="i-tes"]')
        self.assertEqual(self.textos('.folha [data-a="tr-para"].on'), ["Tesouro Verde"])
        self.assertEqual(self.texto('#tr-ajuda'), "CDB Azul fica com R$ 7.500,00 e Tesouro Verde passa de R$ 4.000,00 para R$ 6.500,00.")
        self.assertEqual(self.conta('.folha .campo:has([data-a="tr-para"]) .ajuda'), 0, "do mesmo dono: sem aviso")
        self.ok()
        self.assertIsNone(self.folha())
        self.assertEqual(self.aviso(), "Transferido R$ 2.500 de CDB Azul para Tesouro Verde")
        d = self.dados()
        v = {i["id"]: (i["valor"], i["data_valor"]) for i in d["investimentos"]}
        self.assertEqual(v, {"i-cdb": (7500, HOJE_ISO), "i-tes": (6500, HOJE_ISO), "i-carla": (2500, HOJE_ISO)})
        self.assertEqual([l["id"] for l in d["lancamentos"]], ["l1"], "o caixa não muda")

    def test_sem_valor_sem_destino_e_mais_do_que_tem(self):
        self.transferir(base(bancos=BANCOS, investimentos=[CDB, TES]))
        self.ok()
        self.assertEqual(self.textos('.folha .msg-erro'), ["Coloque o valor."])
        self.assertEqual(self.conta('.folha .pref.grande.erro'), 1, "o campo fica em vermelho")
        self.digitar('#tr-v', '50000')
        self.ok()
        self.assertEqual(self.textos('.folha .msg-erro'), ["Escolha para onde vai o dinheiro."])
        self.assertEqual(self.conta('.folha .tr-para.erro'), 1, "as opções ficam em vermelho")
        self.clicar('.folha [data-a="tr-para"][data-v="i-tes"]')
        self.assertEqual(self.textos('.folha .msg-erro'), [], "escolher tira o erro")
        self.assertEqual(self.conta('.folha .tr-para.erro'), 0)
        self.digitar('#tr-v', '1000001')
        self.assertEqual(self.texto('#tr-ajuda'), "CDB Azul fica com R$ 0,00 e Tesouro Verde passa de R$ 4.000,00 para R$ 14.000,01.")
        self.ok()
        self.assertEqual(self.textos('.folha .msg-erro'), ["Passa do valor de hoje (R$ 10.000,00)."], "R$ 10.000,01 é mais do que tem")
        self.assertEqual(self.folha(), "Transferir de CDB Azul", "continua aberta para corrigir")
        self.assertEqual({i["id"]: i["valor"] for i in self.dados()["investimentos"]}, {"i-cdb": 10000, "i-tes": 4000}, "nada gravado")

    def test_tudo_e_manter_na_carteira(self):
        self.transferir(base(bancos=BANCOS, investimentos=[CDB, TES]))
        self.clicar('.folha [data-a="tr-tudo"]')
        self.assertEqual(self.valor_campo('#tr-v'), "10.000,00", "Tudo preenche o valor de hoje")
        self.assertEqual(self.conta('.folha [data-a="tr-tudo"].on'), 1)
        self.assertEqual(self.texto('.folha .campo:has([data-a="tr-apagar"]) .lbl'), "CDB Azul fica zerado")
        self.assertEqual([t.strip() for t in self.textos('.folha [data-a="tr-apagar"]')], ["Manter na carteira", "Tirar da carteira"])
        self.assertEqual([t.strip() for t in self.textos('.folha [data-a="tr-apagar"].on')], ["Manter na carteira"], "manter vem marcado")
        self.assertEqual(self.texto('.folha-pe [data-a="tr-ok"]'), "Transferir R$ 10.000")
        self.clicar('.folha [data-a="tr-para"][data-v="i-tes"]')
        self.ok()
        v = {i["id"]: i["valor"] for i in self.dados()["investimentos"]}
        self.assertEqual(v, {"i-cdb": 0, "i-tes": 14000}, "o CDB fica zerado na carteira")

    def test_tudo_e_tirar_da_carteira(self):
        self.transferir(base(bancos=BANCOS, investimentos=[CDB, TES, LCI]))
        self.clicar('.folha [data-a="tr-tudo"]')
        self.clicar('.folha [data-a="tr-apagar"][data-v="1"]')
        self.assertEqual([t.strip() for t in self.textos('.folha [data-a="tr-apagar"].on')], ["Tirar da carteira"])
        self.assertEqual(self.texto('.folha .campo:has([data-a="tr-apagar"]) .ajuda'), "Uma cópia fica em Mais › Dados › Versões anteriores.")
        self.clicar('.folha [data-a="tr-para"][data-v="i-lci"]')
        self.ok()
        self.assertEqual(self.aviso(), "Transferido R$ 10.000 de CDB Azul para LCI Verde")
        self.assertEqual({i["id"]: i["valor"] for i in self.dados()["investimentos"]}, {"i-tes": 4000, "i-lci": 13000}, "o CDB sai da carteira")

    def test_tirar_da_carteira_so_vale_passando_tudo(self):
        self.transferir(base(bancos=BANCOS, investimentos=[CDB, TES]))
        self.clicar('.folha [data-a="tr-tudo"]')
        self.clicar('.folha [data-a="tr-apagar"][data-v="1"]')
        self.digitar('#tr-v', '400000')
        self.assertEqual(self.conta('.folha [data-a="tr-apagar"]'), 0, "com menos que tudo, a pergunta some")
        self.clicar('.folha [data-a="tr-para"][data-v="i-tes"]')
        self.ok()
        self.assertEqual({i["id"]: i["valor"] for i in self.dados()["investimentos"]}, {"i-cdb": 6000, "i-tes": 8000}, "o CDB continua, com o resto")

    def test_digitar_o_valor_todo_mostra_a_pergunta_sem_tirar_o_cursor(self):
        self.transferir(base(bancos=BANCOS, investimentos=[CDB, TES]))
        self.digitar('#tr-v', '1000000')
        self.assertEqual(self.conta('.folha [data-a="tr-apagar"]'), 2, "digitou o valor todo: pergunta se tira da carteira")
        self.assertEqual(self.conta('.folha [data-a="tr-tudo"].on'), 1)
        self.assertEqual(self.ativo(), "tr-v", "o cursor continua no campo")
        self.assertEqual(self.js("(e => [e.selectionStart, e.value.length])(document.getElementById('tr-v'))"), [9, 9], "no fim do número")
        self.pg.keyboard.type("1")
        self.esperar()
        self.assertEqual(self.valor_campo('#tr-v'), "100.000,01")
        self.assertEqual(self.conta('.folha [data-a="tr-apagar"]'), 0, "não é mais tudo: a pergunta some")
        self.assertEqual(self.ativo(), "tr-v")
        self.pg.keyboard.press("Backspace")
        self.esperar()
        self.assertEqual((self.valor_campo('#tr-v'), self.conta('.folha [data-a="tr-apagar"]')), ("10.000,00", 2), "apagar volta para tudo")
        self.assertEqual(self.texto('.folha-pe [data-a="tr-ok"]'), "Transferir R$ 10.000")

    def test_entre_seu_e_de_terceiros_avisa(self):
        self.transferir(base(bancos=BANCOS, investimentos=[CDB, CARLA]))
        self.digitar('#tr-v', '100000')
        self.clicar('.folha [data-a="tr-para"][data-v="i-carla"]')
        self.assertEqual(self.texto('.folha .campo:has([data-a="tr-para"]) .ajuda'), "Sai de um dinheiro seu e entra num de terceiros.")
        self.ok()
        self.assertEqual({i["id"]: i["valor"] for i in self.dados()["investimentos"]}, {"i-cdb": 9000, "i-carla": 3500})
        self.transferir(base(bancos=BANCOS, investimentos=[CDB, CARLA]), "i-carla")
        self.clicar('.folha [data-a="tr-para"][data-v="i-cdb"]')
        self.assertEqual(self.texto('.folha .campo:has([data-a="tr-para"]) .ajuda'), "Sai de um dinheiro de terceiros e entra num seu.")

    def test_valores_que_ja_renderam(self):
        velho = dict(CDB, data_valor="2026-05-04")
        self.transferir(base(bancos=BANCOS, investimentos=[velho, TES]))
        hoje = round(self.js("T.valorHoje(T.S.d.investimentos.find(i => i.id === 'i-cdb'))"), 2)
        self.assertGreater(hoje, 10500)
        self.clicar('.folha [data-a="tr-tudo"]')
        self.assertEqual(self.valor_campo('#tr-v'), self.js("T.NF2.format(a)", hoje), "Tudo é o valor de hoje, já com o rendimento")
        self.clicar('.folha [data-a="tr-para"][data-v="i-tes"]')
        self.ok()
        v = {i["id"]: i["valor"] for i in self.dados()["investimentos"]}
        self.assertEqual(v, {"i-cdb": 0, "i-tes": round(4000 + hoje, 2)})

    def test_cancelar_nao_grava(self):
        self.transferir(base(bancos=BANCOS, investimentos=[CDB, TES]))
        self.digitar('#tr-v', '100000')
        self.clicar('.folha [data-a="tr-para"][data-v="i-tes"]')
        self.clicar('.folha-pe [data-a="fechar"]')
        self.assertEqual(self.folha(), "Editar investimento", "Cancelar volta para o investimento")
        self.assertIsNone(self.js("T.TR"), "fechar esquece a transferência")
        self.assertEqual({i["id"]: i["valor"] for i in self.dados()["investimentos"]}, {"i-cdb": 10000, "i-tes": 4000})

    # (era bug até a 1.24.2)
    def test_transferir_para_um_bem_separado_nao_perde_dinheiro(self):
        bem = inv("i-bem", "Móveis da sala", 10000, tipo="bens", banco="", indexador="deprecia", taxa=13, liquidez="diaria", categoria_bem="moveis",
                  partes=[{"categoria": "moveis", "valor": 7000, "taxa": 10}, {"categoria": "eletronicos", "valor": 3000, "taxa": 20}])
        self.transferir(base(bancos=BANCOS, investimentos=[CDB, bem]))
        antes = self.js("T.totais().total")
        self.digitar('#tr-v', '100000')
        self.clicar('.folha [data-a="tr-para"][data-v="i-bem"]')
        self.ok()
        self.assertAlmostEqual(self.js("T.totais().total"), antes, places=2, msg="transferir não muda o total")


# =============================================================================================== gráficos
FLUXO = [
    rec("o-sal", "Salário", 5000, "2026-10-05", True, conta="k-verde", categoria="c-salario"),
    desp("o-alu", "Aluguel", 1200, "2026-10-10", True, conta="k-verde", categoria="c-moradia"),
    desp("o-apo", "Aporte", 500, "2026-10-15", True, aporte=True, conta="k-verde", categoria="c-investimentos"),
    rec("n-sal", "Salário", 5000, "2026-11-01", True, conta="k-verde", categoria="c-salario"),
    desp("n-alu", "Aluguel", 1200, "2026-11-01", True, conta="k-verde", categoria="c-moradia"),
    desp("n-net", "Internet", 100, "2026-11-20", conta="k-verde", categoria="c-contas"),
    desp("d-ipva", "IPVA", 9000, "2026-12-10", conta="k-verde", categoria="c-impostos"),
]
# 6 + 6: jun/26 a mai/27 (outubro é o 5º, novembro o 6º, dezembro o 7º)
# outubro: entrou 5.000, saiu 1.200 e aplicou 500 (sobrou 3.300; saldo 3.300)
# novembro: entrou 5.000, saiu 1.300 (sobrou 3.700; saldo 3.300 + 3.800 pagos − 100 a pagar = 7.000)
# dezembro: saiu 9.000 (sobrou −9.000; saldo −2.000)
OUT, NOV, DEZ = 4, 5, 6


class TestGraficos(_Tela):
    def fluxo(self, lancamentos, prever=False):
        self.abrir(base(bancos=BANCOS, lancamentos=lancamentos, ajustes={"corrigir": True, "prever_dia": prever}),
                   ui={"tab": "caixa", "cxModo": "fluxo", "cxPeriodo": "meio"})

    def ponto(self, graf, i):
        """Onde fica, na página, o mês i do gráfico (o meio da barra no Fluxo, o ponto da linha no Saldo)."""
        return self.js("""(() => {
            const el = document.querySelector('#' + a[0]), svg = el.querySelector('svg'), rc = svg.getBoundingClientRect();
            const W = +svg.getAttribute('width'), n = T.CACHE.fluxo.length;
            const x = a[0] === 'ch-fluxo' ? 46 + (a[1] + 0.5) * (W - 46 - 6) / n : 46 + (a[1] + 0.5) * (W - 46 - 10) / n;
            return [rc.left + x * rc.width / W, rc.top + rc.height / 2];
        })()""", [graf, i])

    def passar(self, graf, i):
        """Passa o dedo (o mouse) sobre o mês i."""
        self.pg.locator('#' + graf).scroll_into_view_if_needed()
        x, y = self.ponto(graf, i)
        self.pg.mouse.move(x, y)

    def tocar(self, graf, i):
        """Toca no mês i (pointerdown de um dedo)."""
        self.pg.locator('#' + graf).scroll_into_view_if_needed()
        x, y = self.ponto(graf, i)
        self.js("(document.querySelector('#' + a[0]).dispatchEvent(new PointerEvent('pointerdown', { clientX: a[1], clientY: a[2], bubbles: true, pointerType: 'touch' })), true)",
                [graf, x, y])

    def quadrinho(self, graf):
        """O quadrinho do gráfico: [título, [(valor, rótulo)...]] ou None se escondido."""
        return self.js("""(() => {
            const t = document.querySelector('#' + a + ' .tip');
            if (!t || t.style.display === 'none') return null;
            return [t.querySelector('.t-d').textContent, [...t.querySelectorAll('.t-r')].map(r => [r.querySelector('b').textContent, r.querySelector('span').textContent])];
        })()""", graf)

    def dentro(self, graf):
        """O quadrinho cabe no gráfico (nada cortado nas pontas)."""
        return self.js("""(() => { const el = document.querySelector('#' + a), t = el.querySelector('.tip'), W = +el.querySelector('svg').getAttribute('width');
            const l = parseFloat(t.style.left); return l >= 0 && l + t.offsetWidth <= W + 0.5; })()""", graf)

    def test_fluxo_ao_passar_o_dedo_mostra_o_mes(self):
        self.fluxo(FLUXO)
        self.assertIsNone(self.quadrinho("ch-fluxo"), "escondido até tocar")
        self.passar("ch-fluxo", OUT)
        self.assertEqual(self.quadrinho("ch-fluxo"), ["outubro de 2026", [["R$ 5.000", "Entradas"], ["R$ 1.200", "Saídas"], ["R$ 500", "Aportes"], ["R$ 3.300", "Sobrou"]]])
        hl = self.js("(h => [h.style.display, +h.getAttribute('x'), +h.getAttribute('width')])(document.getElementById('fx-hl'))")
        self.assertEqual(hl[0], "", "a faixa do mês acende")
        self.assertAlmostEqual(hl[1], 46 + OUT * hl[2], delta=0.11, msg="em cima de outubro")
        self.passar("ch-fluxo", NOV)
        self.assertEqual(self.quadrinho("ch-fluxo"), ["novembro de 2026 · até agora e previsto", [["R$ 5.000", "Entradas"], ["R$ 1.300", "Saídas"], ["R$ 3.700", "Sobrou"]]],
                         "sem aporte no mês, sem a linha de aportes")
        self.passar("ch-fluxo", DEZ)
        self.assertEqual(self.quadrinho("ch-fluxo"), ["dezembro de 2026 · previsto", [["R$ 0", "Entradas"], ["R$ 9.000", "Saídas"], ["−R$ 9.000", "Sobrou"]]],
                         "o que falta sai com o sinal de menos")
        self.pg.mouse.move(1, 1)
        self.assertIsNone(self.quadrinho("ch-fluxo"), "tirar o dedo esconde")
        self.assertEqual(self.js("document.getElementById('fx-hl').style.display"), "none")

    def test_fluxo_quadrinho_cabe_nas_pontas(self):
        self.fluxo(FLUXO)
        for i in (0, 11):
            with self.subTest(mes=i):
                self.tocar("ch-fluxo", i)
                q = self.quadrinho("ch-fluxo")
                self.assertEqual(q[0], "junho de 2026" if i == 0 else "maio de 2027 · previsto", "tocar também mostra")
                self.assertTrue(self.dentro("ch-fluxo"), "o quadrinho não sai do gráfico")

    def test_fluxo_com_dia_a_dia_previsto(self):
        mercado = [desp(f"m{m}", "Mercado", v, f"2026-{m:02d}-10", True, categoria="c-mercado") for m, v in ((8, 300), (9, 600), (10, 900))]
        self.fluxo(mercado, prever=True)
        self.passar("ch-fluxo", DEZ)
        self.assertEqual(self.quadrinho("ch-fluxo"), ["dezembro de 2026 · previsto",
                                                      [["R$ 0", "Entradas"], ["R$ 0", "Saídas lançadas"], ["R$ 600", "Dia a dia (média)"], ["−R$ 600", "Sobrou"]]],
                         "a média de agosto a outubro (300, 600, 900) entra como dia a dia")
        self.passar("ch-fluxo", OUT)
        self.assertEqual(self.quadrinho("ch-fluxo"), ["outubro de 2026", [["R$ 0", "Entradas"], ["R$ 900", "Saídas"], ["−R$ 900", "Sobrou"]]],
                         "nos meses que passaram, sem previsão")

    def test_saldo_ao_passar_o_dedo_mostra_o_fim_do_mes(self):
        self.fluxo(FLUXO)
        self.assertIsNone(self.quadrinho("ch-saldo"))
        self.passar("ch-saldo", OUT)
        self.assertEqual(self.quadrinho("ch-saldo"), ["Fim de outubro de 2026", [["R$ 3.300", "em caixa"]]])
        cruz = self.js("(g => [g.style.display, +g.querySelector('line').getAttribute('x1'), +g.querySelector('circle').getAttribute('cx')])(document.getElementById('sd-x'))")
        W = self.js("+document.querySelector('#ch-saldo svg').getAttribute('width')")
        x = 46 + (OUT + 0.5) * (W - 56) / 12
        self.assertEqual(cruz[0], "", "a linha do mês aparece")
        self.assertAlmostEqual(cruz[1], x, delta=0.01)
        self.assertAlmostEqual(cruz[2], x, delta=0.01)
        self.passar("ch-saldo", NOV)
        self.assertEqual(self.quadrinho("ch-saldo"), ["Fim de novembro de 2026 · previsto", [["R$ 7.000", "em caixa"]]], "conta a internet a pagar")
        self.tocar("ch-saldo", DEZ)
        self.assertEqual(self.quadrinho("ch-saldo"), ["Fim de dezembro de 2026 · previsto", [["−R$ 2.000", "em caixa"]]], "no vermelho, com o sinal")
        self.assertTrue(self.dentro("ch-saldo"))
        self.tocar("ch-saldo", 11)
        self.assertEqual(self.quadrinho("ch-saldo"), ["Fim de maio de 2027 · previsto", [["−R$ 2.000", "em caixa"]]])
        self.assertTrue(self.dentro("ch-saldo"), "na ponta direita, o quadrinho vai para a esquerda")
        self.pg.mouse.move(1, 1)
        self.assertIsNone(self.quadrinho("ch-saldo"))
        self.assertEqual(self.js("document.getElementById('sd-x').style.display"), "none")

    def test_evolucao_tocar_num_valor_registrado(self):
        pre = inv("i-pre", "CDB Prefixado", 10000, indexador="pre", taxa=12)
        hist = [{"d": "2026-05-04", "total": 8000, "meu": 8000, "terceiros": 0}, {"d": "2026-08-03", "total": 9000, "meu": 9000, "terceiros": 0}]
        self.abrir(base(bancos=BANCOS, investimentos=[pre], historico=hist), ui={"tab": "investimentos", "invModo": "evolucao", "gAnos": 1})
        svg = self.pg.locator("#ch-evo svg")
        svg.scroll_into_view_if_needed()
        svg.click(position={"x": 51, "y": 100})
        self.assertEqual(self.texto("#ch-evo .tip").split("\n"), ["04/05/2026 · registrado", "R$ 8.000", "Registrado"], "o primeiro valor registrado")
        self.assertEqual(self.js("document.querySelectorAll('#cross circle.mk').length"), 1, "um ponto só, na linha do registrado")

    def categorias(self, lancamentos):
        self.abrir(base(bancos=BANCOS, lancamentos=lancamentos), ui={"tab": "caixa", "cxModo": "categorias", "cxCatTipo": "despesa", "cxSel": None})

    def comps(self):
        return [tuple(x) for x in self.js("[...document.querySelectorAll('#app .comp')].map(c => [c.dataset.v, c.querySelector('.nm b').textContent, "
                                          "c.querySelector('.sub').textContent, c.querySelector('.vl').firstChild.textContent, c.querySelector('.vl small').textContent])")]

    def test_categorias_demais_juntam_as_menores_em_outras(self):
        cats = [("c-moradia", 1200), ("c-mercado", 800), ("c-restaurantes", 400), ("c-transporte", 300), ("c-contas", 250), ("c-saude", 200),
                ("c-educacao", 150), ("c-lazer", 60), ("c-assinaturas", 40), ("c-compras", 100)]
        lanc = [desp(f"g{k}", f"Gasto {k}", v, "2026-11-01", True, categoria=c) for k, (c, v) in enumerate(cats)]
        lanc.append(desp("g-extra", "Cinema", 40, "2026-11-01", True, categoria="c-lazer"))  # lazer: 2 lançamentos, 100
        self.categorias(lanc)
        cs = self.comps()
        self.assertEqual(len(cs), 8, "as 7 maiores e Outras")
        self.assertEqual([c[1] for c in cs[:7]], ["Moradia", "Mercado", "Restaurantes", "Transporte", "Contas da casa", "Saúde", "Educação"])
        # total 3.540; Outras: Lazer 100 (2 lançamentos), Compras 100 e Assinaturas 40 = 240 em 4 lançamentos
        self.assertEqual(cs[7], ("_outras", "Outras (3)", "4 lançamentos", "R$ 240", "6,8%"), "sem média para Outras")
        self.assertEqual(cs[0][3:], ("R$ 1.200", "33,9%"))
        self.assertEqual(self.js("[...document.querySelectorAll('#app .pilha i')].length"), 8, "a barra também com 8 partes")
        self.assertEqual(self.js("document.querySelector('#app .pilha i[data-v=\"_outras\"]').style.getPropertyValue('--c')"), "var(--c0)", "Outras em cinza")
        self.clicar('#app .comp[data-v="_outras"]')
        self.assertEqual(self.texto('.pilha-cap'), "Outras (3) · R$ 240 · 6,8%")
        topo = self.js("[...document.querySelectorAll('#app .stat-duo > div')].map(d => [d.querySelector('span').textContent, d.querySelector('b').textContent])")
        self.assertEqual(topo, [["Gastos em novembro", "R$ 3.540"], ["Média dos 3 meses antes", "R$ 0"]], "o total conta todas, também as de Outras")

    def test_oito_categorias_aparecem_todas(self):
        cats = ["c-moradia", "c-mercado", "c-restaurantes", "c-transporte", "c-contas", "c-saude", "c-educacao", "c-lazer"]
        self.categorias([desp(f"g{k}", f"Gasto {k}", 100 * (8 - k), "2026-11-01", True, categoria=c) for k, c in enumerate(cats)])
        cs = self.comps()
        self.assertEqual(len(cs), 8)
        self.assertNotIn("_outras", [c[0] for c in cs], "com 8, nenhuma fica escondida em Outras")
        self.assertEqual(cs[-1][1:4], ("Lazer", "1 lançamento", "R$ 100"))


# =============================================================================================== campos
SPOTIFY = {"id": "r-spot", "tipo": "despesa", "descricao": "Spotify", "valor": 23.9, "dia": 22, "inicio": "2026-01", "conta": "k-ana", "cartao": True,
           "categoria": "c-assinaturas"}
_ASS = {"chave": "r:r-spot", "rid": "r-spot", "origem": "fixo", "servico": "spotify", "nome": "Spotify", "descricao": "Spotify", "valor": 23.9, "freq_anual": False,
        "conta": "k-ana", "cartao": True, "categoria": "c-assinaturas", "dia": 22, "fonte": "https://www.spotify.com/br-pt/premium/", "dominio": "spotify.com",
        "conferido": "2026-10-18", "status": "ok", "texto": "Dá para economizar no plano anual.", "plano": "Premium Individual", "moeda": "BRL",
        "mensal": 23.9, "anual": 239, "pct": 16.7, "economia_ano": 47.8, "preco_anual": 239, "estimado": False}
DICA = "anual:r:r-spot"
DICAS = {"dicas": [dict(_ASS, id=DICA)], "assinaturas": [_ASS], "conferindo": False, "catalogo": ["Nabu Casa", "Claude", "Spotify", "Microsoft 365", "Deezer"], "dolar": None}


class TestCampos(_Tela):
    def dicas(self, d, ui=None, dicas=None):
        self.abrir(d, ui=ui)
        self.js("(T.S.dicas = a, T.render(), true)", dicas or DICAS)
        self.esperar()

    def mudar_para_anual(self):
        self.dicas(base(bancos=BANCOS, recorrencias=[SPOTIFY]))
        self.clicar(f'[data-a="dica-anual"][data-v="{DICA}"]')
        self.assertEqual(self.folha(), "Spotify no plano anual")

    def eco(self, anual):
        """O texto da economia, montado aqui a partir de economiaReal (o desconto é conferido à mão em cada teste)."""
        e = self.js("T.economiaReal(23.9, a)", anual)
        brl = lambda v: self.js("T.brl(a)", v)  # noqa: E731
        return e, f"Você economiza {brl(e['real'])} por ano: {brl(e['desconto'])} de desconto menos {brl(e['rende'])} que o dinheiro renderia {e['rs']['onde']}, já com IR."

    def test_valor_do_plano_anual_atualiza_a_economia(self):
        self.mudar_para_anual()
        self.digitar('#da-valor', '20000')
        self.assertEqual(self.valor_campo('#da-valor'), "200,00", "os números entram como centavos")
        e, txt = self.eco(200)
        self.assertAlmostEqual(e["desconto"], 86.8, places=6, msg="12 × 23,90 − 200")
        self.assertGreater(e["real"], 0)
        self.assertEqual(self.texto('#da-eco'), txt)
        self.digitar('#da-valor', '30000')
        self.assertEqual(self.texto('#da-eco'), "Com esse valor, o anual não sai mais barato.", "R$ 300 é mais que 12 × 23,90 = 286,80")
        self.digitar('#da-valor', '28680')
        self.assertEqual(self.texto('#da-eco'), "Com esse valor, o anual não sai mais barato.", "igual a 12 mensalidades")
        # um desconto pequeno, que o rendimento das mensalidades come
        e = self.js("T.economiaReal(23.9, 286)")
        self.assertTrue(e["desconto"] > 0 and e["real"] <= 0, e)
        self.digitar('#da-valor', '28600')
        self.assertEqual(self.texto('#da-eco'), f"O desconto é de R$ 0,80, mas deixar o dinheiro rendendo {e['rs']['onde']} e pagar por mês sai melhor.")
        self.digitar('#da-valor', '123456789012345')
        self.assertEqual(self.valor_campo('#da-valor'), "123.456.789,01", "no máximo 11 dígitos")

    def test_sem_valor_ou_sem_data_nao_muda(self):
        self.mudar_para_anual()
        self.digitar('#da-valor', '')
        self.assertEqual(self.valor_campo('#da-valor'), "")
        self.clicar('.folha-pe [data-a="da-ok"]')
        self.assertEqual(self.textos('.folha .msg-erro'), ["Coloque o valor."])
        self.assertEqual(self.conta('.folha .pref.grande.erro'), 1)
        self.digitar('#da-valor', '22000')
        self.assertEqual(self.js("T.DA.erro"), "", "digitar tira o erro")
        self.preencher('#da-data', '')
        self.clicar('.folha-pe [data-a="da-ok"]')
        self.assertEqual(self.textos('.folha .msg-erro'), ["Data inválida."])
        self.assertEqual(self.dados()["recorrencias"], [SPOTIFY], "nada muda")

    def test_valor_e_data_escolhidos_vao_para_o_fixo_anual(self):
        self.mudar_para_anual()
        self.digitar('#da-valor', '22990')
        self.preencher('#da-data', '2027-01-15')
        self.assertEqual(self.valor_campo('#da-valor'), "229,90", "a data não apaga o valor")
        e, txt = self.eco(229.9)
        self.assertAlmostEqual(e["desconto"], 56.9, places=6)
        self.assertEqual(self.texto('#da-eco'), txt, "trocar a data mantém a conta")
        self.clicar('.folha-pe [data-a="da-ok"]')
        self.assertIsNone(self.folha())
        mensal, anual = self.dados()["recorrencias"]
        self.assertEqual(mensal["fim"], "2026-12", "o mensal vai até dezembro")
        self.assertEqual((anual["valor"], anual["freq"], anual["inicio"], anual["dia"], anual["conta"], anual["cartao"]), (229.9, "anual", "2027-01", 15, "k-ana", True))

    def test_ultima_verificacao_das_dicas(self):
        casos = (("2026-11-02T08:15:00-03:00", "hoje às 08:15"), ("2026-11-01T21:40:00-03:00", "ontem às 21:40"),
                 ("2026-10-28T14:20:00-03:00", "28/10 às 14:20"), ("2025-12-28T09:05:00-03:00", "28/12/2025 às 09:05"))
        for quando, txt in casos:
            with self.subTest(quando=quando):
                self.dicas(base(bancos=BANCOS, recorrencias=[SPOTIFY]), ui={"tab": "mais", "maisAba": "caixa"}, dicas=dict(DICAS, atualizado=quando))
                self.assertEqual(self.texto('#dicas .dica-quando'), f"Última verificação: {txt}.")
        self.assertEqual(self.js("T.quandoLongo('não é data')"), "", "data inválida: nada")
        self.dicas(base(bancos=BANCOS, recorrencias=[SPOTIFY]), ui={"tab": "mais", "maisAba": "caixa"}, dicas=dict(DICAS, atualizado="2026-11-02T08:15:00-03:00", conferindo=True))
        self.assertEqual(self.texto('#dicas .dica-quando'), "Conferindo agora…")
        self.assertTrue(self.pg.is_disabled('#dicas [data-a="dicas-conferir"]'))

    def test_dica_que_nao_vale_a_pena_trocar(self):
        # o anual com só R$ 3 de desconto: o rendimento das mensalidades come a diferença
        ass = dict(_ASS, preco_anual=283.8, anual=283.8)
        er = self.js("T.economiaReal(23.9, 283.8)")
        self.assertLess(er["real"], 10)
        self.dicas(base(bancos=BANCOS, recorrencias=[SPOTIFY]), ui={"tab": "mais", "maisAba": "caixa"}, dicas=dict(DICAS, dicas=[], assinaturas=[ass]))
        self.assertIn(f"O anual tem R$ 3 de desconto, mas o dinheiro rendendo {er['rs']['onde']} daria quase o mesmo. Não vale trocar.",
                      self.texto('#dicas .ass-st'))

    def test_observacao_do_lancamento(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "caixa"})
        self.clicar('#nav [data-a="novo"]')
        self.assertEqual(self.conta('.folha [data-lf="obs"]'), 0, "fechada de início")
        self.clicar('.folha [data-a="lf-obs"]')
        self.assertEqual(self.conta('.folha [data-a="lf-obs"].on'), 1)
        self.digitar('#lf-valor', '4590')
        self.preencher('#lf-desc', 'Farmácia')
        self.preencher('.folha [data-lf="obs"]', 'Remédio da Carla')
        self.clicar('.folha-pe [data-a="lf-salvar"]:not([data-mais])')
        (l,) = self.dados()["lancamentos"]
        self.assertEqual((l["descricao"], l["valor"], l["obs"]), ("Farmácia", 45.9, "Remédio da Carla"))
        self.clicar(f'.lanc[data-id="{l["id"]}"]')
        self.assertEqual(self.pg.input_value('.folha [data-lf="obs"]'), "Remédio da Carla", "ao editar, a observação já vem aberta")
        self.clicar('.folha [data-a="lf-obs"]')
        self.assertEqual(self.conta('.folha [data-lf="obs"]'), 0, "tocar de novo fecha")

    def test_vezes_do_parcelado_redesenham_sem_tirar_o_cursor(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "caixa"})
        self.clicar('#nav [data-a="novo"]')
        self.digitar('#lf-valor', '120000')
        self.clicar('.folha [data-a="lf-set"][data-k="repete"][data-v="parcelado"]')
        self.assertEqual(self.texto('.folha .duo .ajuda'), "10x de R$ 120,00", "começa em 10 vezes")
        self.digitar('.folha [data-lf="vezes"]', '12')
        self.assertEqual(self.texto('.folha .duo .ajuda'), "10x de R$ 120,00", "enquanto digita, a janela não se redesenha")
        self.pg.wait_for_function("document.querySelector('.folha .duo .ajuda').textContent.includes('12x')", timeout=2000)
        self.assertEqual(self.texto('.folha .duo .ajuda'), "12x de R$ 100,00", "a janela se redesenha sozinha logo depois")
        self.assertEqual(self.js("(e => [e.dataset.lf, e.selectionStart, e.value])(document.activeElement)"), ["vezes", 2, "12"],
                         "o cursor continua no campo, no fim")
        self.pg.keyboard.type("x59")
        self.assertEqual(self.pg.input_value('.folha [data-lf="vezes"]'), "125", "só números, até 3")
        self.pg.wait_for_function("document.querySelector('.folha .duo .ajuda').textContent.includes('125x')", timeout=2000)
        self.clicar('.folha-pe [data-a="lf-salvar"]:not([data-mais])')
        self.assertEqual(self.textos('.folha .msg-erro'), ["De 2 a 120 vezes."], "mais de 120 não salva")

    def test_desconto_em_reais_digita_em_centavos(self):
        # um desconto em reais (modo fixo, gravado antes dos impostos em %): o campo aceita reais e centavos
        plano = {"id": "x-pl", "descricao": "Plano de saúde", "modo": "fixo", "valor": 300, "base": "", "categoria": "c-saude"}
        sal = rec("l-sal", "Salário", 5000, "2026-11-05", conta="k-verde", categoria="c-salario", descontos=[plano])
        self.abrir(base(bancos=BANCOS, lancamentos=[sal]), ui={"tab": "caixa"})
        self.clicar('.lanc[data-id="l-sal"]')
        self.assertEqual(self.texto('#lfd-v-0'), "− R$ 300,00")
        self.digitar('.folha [data-lfd="valor"][data-i="0"]', '45050')
        self.assertEqual(self.pg.input_value('.folha [data-lfd="valor"][data-i="0"]'), "450,50")
        self.assertEqual(self.texto('#lfd-v-0'), "− R$ 450,50")
        self.assertEqual(self.js("document.querySelector('#lf-desc-res .liq b').textContent"), "R$ 4.549,50", "o líquido acompanha")
        self.clicar('.folha-pe [data-a="lf-salvar"]')
        x = self.dados()["lancamentos"][0]["descontos"][0]
        self.assertEqual((x["modo"], x["valor"]), ("fixo", 450.5))

    # (era bug até a 1.24.2)
    def test_desconto_em_reais_nao_aparece_como_porcentagem(self):
        plano = {"id": "x-pl", "descricao": "Plano de saúde", "modo": "fixo", "valor": 300, "base": "", "categoria": "c-saude"}
        sal = rec("l-sal", "Salário", 5000, "2026-11-05", conta="k-verde", categoria="c-salario", descontos=[plano])
        self.abrir(base(bancos=BANCOS, lancamentos=[sal]), ui={"tab": "caixa"})
        self.clicar('.lanc[data-id="l-sal"]')
        campo = self.js("(e => [e.parentElement.innerText.trim(), e.getAttribute('aria-label')])(document.querySelector('.folha [data-lfd=\"valor\"]'))")
        self.assertNotIn("%", campo[0])
        self.assertNotEqual(campo[1], "Porcentagem do bruto")


if __name__ == "__main__":
    unittest.main()
