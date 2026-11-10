"""Tela: Benefícios (Mais › Benefícios), num Chromium de verdade, sem servidor (a prévia). Confere o cadastro (nome, de
onde vem, quantidade, saldo ou vantagem, renova, desde e vale até), o Usei (a quantidade desconta 1; o saldo pergunta
quanto), o período que renova, os usos do período, a origem que acabou (fixo ou conta), os avisos do Início, o menu e a
contagem nos fixos e nos bancos. O relógio fica em 02/11/2026. Dados inventados (Ana, Banco Azul, Plano Sol)."""
import unittest

from tests.tela_base import base, BANCOS
from tests.test_tela_mais import TelaMais

FIXO = {"id": "r-sol", "tipo": "despesa", "descricao": "Plano Sol", "valor": 110, "dia": 5, "freq": "mensal", "inicio": "2026-01", "categoria": "c-assinaturas"}
VIP = {"id": "bn-vip", "nome": "Sala VIP", "origem": "conta:k-ana", "tipo": "contagem", "total": 6, "renova": "ano", "desde": "2026-03-15",
       "usos": [{"id": "u1", "data": "2026-04-10", "qtd": 1}, {"id": "u0", "data": "2026-01-10", "qtd": 1}]}
CREDITO = {"id": "bn-cred", "nome": "Créditos de uso", "origem": "fixo:r-sol", "tipo": "saldo", "total": 100, "moeda": "USD", "renova": "mes", "desde": "2026-01-20",
           "usos": [{"id": "u2", "data": "2026-10-25", "qtd": 30}]}
SEGURO = {"id": "bn-seg", "nome": "Seguro viagem", "origem": "conta:k-ana", "tipo": "vantagem", "renova": "nunca", "desde": "2026-01-01"}
BENS = {"tab": "mais", "maisTela": "beneficios"}


class TelaBen(TelaMais):
    def abrir_ben(self, beneficios=(), **mais):
        d = base(bancos=BANCOS, recorrencias=[FIXO], beneficios=list(beneficios))
        d.update(mais)
        self.abrir(d, ui=BENS)

    def linhas(self):
        return self.js("""[...document.querySelectorAll('#beneficios .ben-row')].map(r => [r.querySelector('.ben-t b').textContent, r.querySelector('.ben-t > span').textContent,
            (r.querySelector('.ben-v b') || {}).textContent || '', (r.querySelector('.ben-v small') || {}).textContent || ''])""")


class TestLista(TelaBen):
    def test_menu_e_lista_agrupada_pela_origem(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais"})
        self.assertEqual(self.linha(".menu-row", "Benefícios"), "Benefícios Salas VIP, créditos e vantagens dos seus planos e cartões.")
        self.abrir_ben([VIP, CREDITO, SEGURO])
        self.assertEqual(self.texto("#app .cab h1"), "Benefícios")
        self.assertEqual(self.textos("#beneficios .ben-grupo-cab b"), ["Banco Azul · Ana", "Plano Sol"])
        self.assertEqual(self.linhas(), [
            ["Sala VIP", "6 por ano · renova em 15/03/2027", "restam 5", "de 6"],  # o uso de janeiro foi no período anterior
            ["Seguro viagem", "Vantagem", "", ""],
            ["Créditos de uso", "US$ 100 por mês · renova em 20/11/2026", "restam US$ 70", "de US$ 100"]])

    def test_usei_desconta_um(self):
        self.abrir_ben([VIP])
        self.clicar('[data-a="ben-usar"]')
        self.esperar()
        self.assertEqual(self.esperar_aviso("Sala VIP"), "Sala VIP: restam 4")
        self.assertEqual(self.linhas()[0][2], "restam 4")
        self.assertEqual(self.dados()["beneficios"][0]["usos"][-1]["data"], "2026-11-02")

    def test_saldo_pergunta_quanto(self):
        self.abrir_ben([CREDITO])
        self.clicar('[data-a="ben-usar"]')
        self.assertEqual(self.folha(), "Quanto usou de Créditos de uso?")
        self.clicar('#folhas [data-a="fben-usou"]')
        self.assertEqual(self.esperar_aviso("Diga"), "Diga quanto usou.")
        self.preencher("#fben-usou", "12,50")
        self.clicar('#folhas [data-a="fben-usou"]')
        self.esperar()
        self.assertIsNone(self.folha())
        self.assertEqual(self.linhas()[0][2], "restam US$ 57,50")

    def test_acabou_nao_deixa_usar(self):
        self.abrir_ben([dict(VIP, total=1)])
        self.assertEqual(self.linhas()[0][2], "acabou")
        self.assertTrue(self.pg.is_disabled('[data-a="ben-usar"]'))

    def test_origem_que_acabou(self):
        fixo_fim = dict(FIXO, fim="2026-10")
        self.abrir_ben([CREDITO, dict(VIP, origem="conta:k-sumiu")], recorrencias=[fixo_fim])
        # (pedido do dono: o que acabou fica no fim, recolhido, e abre num toque)
        self.assertEqual(self.texto("#beneficios .vazio"), "Nenhum benefício valendo.")
        self.assertEqual(self.texto('#beneficios [data-a="recolher"]'), "Encerrados (2)")
        self.assertEqual(self.conta("#beneficios .ben-row"), 0, "fechado por padrão")
        self.clicar('#beneficios [data-a="recolher"]')
        self.assertEqual(self.textos("#beneficios .ben-acabou"), ["o fixo acabou", "a conta saiu"])


class TestCadastro(TelaBen):
    def test_cadastrar_quantidade_ligada_ao_cartao(self):
        self.abrir_ben()
        self.assertEqual(self.texto("#beneficios .vazio"), "Nenhum benefício ainda.")
        self.clicar('[data-a="ben-novo"]')
        self.assertEqual(self.folha(), "Novo benefício")
        self.clicar('#folhas [data-a="fben-salvar"]')
        self.assertEqual(self.esperar_aviso("Dê"), "Dê um nome ao benefício.")
        self.preencher("#fben-nome", "Sala VIP")
        self.clicar('#folhas [data-a="fben-salvar"]')
        self.assertEqual(self.esperar_aviso("Diga"), "Diga quantos.")
        self.clicar('.folha [data-a="fben-origem"][data-v="conta:k-ana"]')
        self.preencher("#fben-total", "6")
        self.preencher("#fben-desde", "2026-03-15")
        self.clicar('#folhas [data-a="fben-salvar"]')
        self.esperar()
        b = self.dados()["beneficios"][0]
        self.assertEqual({k: b[k] for k in ("nome", "origem", "tipo", "total", "renova", "desde")},
                         {"nome": "Sala VIP", "origem": "conta:k-ana", "tipo": "contagem", "total": 6, "renova": "ano", "desde": "2026-03-15"})
        self.assertEqual(self.linhas(), [["Sala VIP", "6 por ano · renova em 15/03/2027", "restam 6", "de 6"]])

    def test_saldo_em_dolar_do_fixo_e_vantagem(self):
        self.abrir_ben()
        self.clicar('[data-a="ben-novo"]')
        self.preencher("#fben-nome", "Créditos de uso")
        self.clicar('.folha [data-a="fben-origem"][data-v="fixo:r-sol"]')
        self.clicar('#folhas [data-a="fben-seg"][data-k="tipo"][data-v="saldo"]')
        self.clicar('#folhas [data-a="fben-seg"][data-k="moeda"][data-v="USD"]')
        self.clicar('#folhas [data-a="fben-seg"][data-k="renova"][data-v="mes"]')
        self.preencher("#fben-total", "100")
        self.clicar('#folhas [data-a="fben-salvar"]')
        self.esperar()
        b = self.dados()["beneficios"][0]
        self.assertEqual((b["tipo"], b["moeda"], b["total"], b["renova"]), ("saldo", "USD", 100, "mes"))
        self.clicar('[data-a="ben-novo"]')
        self.preencher("#fben-nome", "Seguro viagem")
        self.clicar('#folhas [data-a="fben-seg"][data-k="tipo"][data-v="vantagem"]')
        self.assertEqual(self.conta("#fben-total"), 0, "vantagem não tem quantidade")
        self.clicar('#folhas [data-a="fben-salvar"]')
        self.esperar()
        self.assertEqual([(x["nome"], x["tipo"], x.get("total")) for x in self.dados()["beneficios"]], [("Créditos de uso", "saldo", 100), ("Seguro viagem", "vantagem", None)])

    def test_editar_tira_um_uso_e_excluir(self):
        self.abrir_ben([VIP])
        self.clicar('[data-a="ben-editar"]')
        self.assertEqual(self.folha(), "Editar benefício")
        self.assertIn("Usos deste período · 1 de 6", self.texto("#folhas .folha-corpo"))
        self.clicar('#folhas [data-a="fben-uso-rm"][data-v="u1"]')
        self.clicar('#folhas [data-a="fben-salvar"]')
        self.esperar()
        self.assertEqual(self.linhas()[0][2], "restam 6")
        self.assertEqual([u["id"] for u in self.dados()["beneficios"][0]["usos"]], ["u0"], "o uso do período anterior fica")
        self.clicar('[data-a="ben-editar"]')
        self.clicar('#folhas [data-a="fben-excluir"]')
        self.clicar('#folhas [data-a="confirmar"]')
        self.esperar()
        self.assertEqual(self.dados()["beneficios"], [])


    def test_de_onde_vem_em_botoes_como_a_escolha_do_banco(self):
        """1.51: De onde vem fica na tela, em botões (era uma caixa que abria embaixo), como a escolha do banco."""
        self.abrir_ben()
        self.clicar('[data-a="ben-novo"]')
        self.assertEqual(self.conta('.folha select#fben-origem'), 0)
        ops = self.textos('.folha [data-a="fben-origem"]')
        self.assertEqual(ops[0], "Nenhum")
        self.assertTrue(any(o.startswith("Banco Azul · Ana") for o in ops), ops)
        self.assertEqual(self.texto('.folha [data-a="fben-origem"].on'), "Nenhum", "começa em Nenhum")
        self.assertEqual(self.conta('.folha [data-a="fben-origem"][data-v="conta:k-ana"] .bol'), 1, "a conta com a cor do banco")
        self.clicar('.folha [data-a="fben-origem"][data-v="conta:k-ana"]')
        self.assertEqual(self.js("T.FBEN.origem"), "conta:k-ana")
        self.assertEqual(self.js("document.querySelector('.folha [data-a=\"fben-origem\"][data-v=\"conta:k-ana\"]').getAttribute('aria-checked')"), "true")

class TestLerComIA(TelaBen):
    """Ler com IA: a IA simulada da prévia (a mesma regra do servidor) lê o texto, a página ou a imagem; a pessoa confere
    (o que já está cadastrado vem desmarcado) e cadastra os escolhidos."""
    TEXTO = "6 acessos à sala VIP por ano\nUS$ 100 em créditos de uso por mês\nFrete grátis\nAnuidade de R$ 1.200,00"

    def ler(self):
        self.clicar('#folhas [data-a="bler-ler"]')
        self.pg.wait_for_function("() => { const s = window.GERENCIA_TESTE.BLER; return s && s.etapa !== 'lendo'; }")
        self.esperar()

    def itens(self):
        return self.js("""[...document.querySelectorAll('#folhas .bler-it')].map(b => [b.getAttribute('aria-checked') === 'true',
            b.querySelector('.bler-t b').textContent, b.querySelector('.bler-t > span').textContent, (b.querySelector('em') || {}).textContent || ''])""")

    def test_texto_conferir_e_cadastrar(self):
        self.abrir_ben([VIP])
        self.assertEqual(self.textos("#beneficios .ben-botoes .btn"), ["Cadastrar", "Ler com IA"])
        self.clicar('[data-a="ben-ler"]')
        self.assertEqual(self.folha(), "Ler benefícios com IA")
        self.assertTrue(self.js("document.querySelector('[data-a=\"bler-ler\"]').disabled"))
        self.clicar('.folha [data-a="bler-origem"][data-v="conta:k-ana"]')
        self.preencher("#bler-txt", self.TEXTO)
        self.assertFalse(self.js("document.querySelector('[data-a=\"bler-ler\"]').disabled"))
        self.ler()
        self.assertEqual(self.folha(), "Benefícios encontrados")
        self.assertIn("De Banco Azul · Ana.", self.texto("#folhas .da-intro"))
        self.assertEqual(self.itens(), [[False, "Sala VIP", "6 por ano", "já cadastrado"], [True, "Créditos de uso", "US$ 100 por mês", ""],
                                        [True, "Frete grátis", "Vantagem", ""]], "a anuidade é preço, não benefício")
        self.assertEqual(self.texto('#folhas [data-a="bler-salvar"]'), "Cadastrar 2")
        self.clicar('#folhas [data-a="bler-marca"][data-v="2"]')
        self.assertEqual(self.texto('#folhas [data-a="bler-salvar"]'), "Cadastrar 1")
        self.clicar('#folhas [data-a="bler-salvar"]')
        self.assertEqual(self.esperar_aviso("cadastrado"), "Benefício cadastrado")
        self.assertIsNone(self.folha())
        b = self.dados()["beneficios"][1]
        self.assertEqual({k: v for k, v in b.items() if k != "id"},
                         {"nome": "Créditos de uso", "origem": "conta:k-ana", "tipo": "saldo", "total": 100, "moeda": "USD", "renova": "mes", "desde": "2026-11-02", "usos": []})
        self.assertEqual(self.linhas()[1], ["Créditos de uso", "US$ 100 por mês · renova em 02/12/2026", "restam US$ 100", "de US$ 100"])

    def test_imagem_voltar_e_nada_achado(self):
        from tests.test_tela_ia import _SOLTAR
        self.abrir_ben()
        self.clicar('[data-a="ben-ler"]')
        self.preencher("#bler-txt", "Nada que sirva")
        self.ler()
        self.assertEqual((self.folha(), self.texto("#folhas .msg-erro")), ("Ler benefícios com IA", "A IA não achou benefícios aqui."))
        self.preencher("#bler-txt", "")
        self.assertEqual(self.conta("#folhas .msg-erro"), 0, "digitando, o aviso sai")
        self.pg.evaluate(_SOLTAR, {"como": "colar", "tipo": "png", "nome": "beneficios.png"})
        self.pg.wait_for_selector("#folhas .ia-prev")
        self.assertEqual(self.texto("#folhas .ia-prev b"), "beneficios.png")
        self.ler()
        self.assertEqual([x[1] for x in self.itens()], ["Sala VIP", "Créditos de uso", "Seguro viagem"])
        self.assertEqual(self.itens()[0][2], "6 por ano · com 1 acompanhante")
        self.clicar('#folhas [data-a="bler-voltar"]')
        self.assertEqual(self.folha(), "Ler benefícios com IA")
        self.assertEqual(self.texto("#folhas .ia-prev b"), "beneficios.png", "a imagem continua")
        self.clicar('#folhas [data-a="bler-arq-rm"]')
        self.assertEqual(self.conta("#folhas .ia-prev"), 0)
        self.voltar()
        self.assertIsNone(self.folha(), "o Voltar do celular fecha a janela")
        self.assertEqual(self.dados()["beneficios"], [])

    def test_ia_simulada_igual_a_do_servidor(self):
        import beneficios as B  # o tela_base põe gerencia/app no caminho
        texto = self.TEXTO + "\nSala VIP liberada\n2 visitas ao lounge ao ano, com 2 acompanhantes\nR$ 50 de bônus\nSeguro celular; Cashback de 1%"
        self.abrir_ben()
        js = self.js("T.simBeneficios(" + __import__("json").dumps(texto) + ")")
        self.assertEqual(js, B.limpar(B.simulados(texto), texto)[0])

    def test_sem_ia_so_cadastrar(self):
        self.abrir_ben(ajustes={"corrigir": True, "ia": False})
        self.assertEqual(self.textos("#beneficios > .btn"), ["Cadastrar benefício"])
        self.assertEqual(self.conta('[data-a="ben-ler"]'), 0)


class TestAvisosEContagem(TelaBen):
    def test_avisos_do_inicio(self):
        perto = dict(VIP, desde="2025-11-20")  # renova em 20/11/2026: o que sobrou vence em 19/11
        fixo_fim = dict(FIXO, fim="2026-10")
        self.abrir(base(bancos=BANCOS, recorrencias=[fixo_fim], beneficios=[perto, CREDITO]), ui={"tab": "inicio"})
        tela = " ".join(self.tela().split())
        self.assertIn("Benefício para usar Sala VIP (4) até 19/11", tela, "os dois usos foram neste período")
        self.assertIn("Benefício que vai parar Créditos de uso: o fixo Plano Sol acabou", tela)
        self.clicar('[data-a="mais-tela"][data-v="beneficios"]')
        self.assertEqual(self.js("[T.S.ui.tab, T.S.ui.maisTela]"), ["mais", "beneficios"])

    def test_contagem_nos_fixos_e_nos_bancos(self):
        self.abrir(base(bancos=BANCOS, recorrencias=[FIXO], beneficios=[VIP, CREDITO, SEGURO]), ui={"tab": "mais", "maisTela": "caixa"})
        self.assertIn("1 benefício", self.linha("#fixos .banco-row", "Plano Sol"))
        self.abrir(base(bancos=BANCOS, recorrencias=[FIXO], beneficios=[VIP, CREDITO, SEGURO]), ui={"tab": "mais", "maisTela": "bancos"})
        self.assertTrue(self.linha(".banco-row", "Banco Azul").endswith("2 benefícios"))


if __name__ == "__main__":
    unittest.main()
