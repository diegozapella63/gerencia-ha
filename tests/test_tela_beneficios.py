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
        self.pg.wait_for_function("() => { const s = window.GERENCIA_TESTE.BLER; return !s || s.etapa !== 'lendo'; }")  # milhas: a folha fecha
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

    def test_identificar_beneficios_na_conta_do_banco(self):
        """1.53: em Editar banco, cada conta já salva tem Identificar benefícios: a leitura por IA abre por cima, já com
        a conta em De onde vêm; cadastrar volta para o banco, que mostra quantos a conta tem. Sem a IA, não aparece."""
        self.abrir(base(bancos=BANCOS, recorrencias=[FIXO], beneficios=[VIP]), ui={"tab": "mais", "maisTela": "bancos"})
        self.js("(T.abrirBanco('b-azul'), true)")
        self.esperar()
        self.assertEqual(self.textos('.folha [data-a="ben-identificar"]'), ["Identificar benefícios", "Identificar benefícios"], "uma para cada pessoa")
        self.assertEqual(self.textos('.folha .bc-ben-n'), ["1 benefício cadastrado."], "a Ana já tem a Sala VIP")
        self.clicar('.folha [data-a="bc-add"]')
        self.assertEqual(self.conta('.folha [data-a="ben-identificar"]'), 2, "a conta nova (ainda não salva) não tem o botão")
        self.clicar('.folha [data-a="ben-identificar"][data-v="conta:k-beto"]')
        self.assertEqual(self.folha(), "Ler benefícios com IA")
        self.assertEqual(self.texto('.folha [data-a="bler-origem"].on'), "Banco Azul · Beto · cartão", "já com a conta do Beto")
        self.preencher("#bler-txt", self.TEXTO)
        self.ler()
        self.clicar('#folhas [data-a="bler-salvar"]')
        self.assertEqual(self.esperar_aviso("cadastrados"), "3 benefícios cadastrados")
        self.assertEqual(self.folha(), "Editar banco", "volta para o banco")
        self.assertEqual(self.textos('.folha .bc-ben-n'), ["1 benefício cadastrado.", "3 benefícios cadastrados."])
        self.assertEqual(self.conta('.folha .conta-ed'), 3, "a pessoa acrescentada continua lá")
        self.abrir(base(bancos=BANCOS, ajustes={"ia": False}), ui={"tab": "mais", "maisTela": "bancos"})
        self.js("(T.abrirBanco('b-azul'), true)")
        self.esperar()
        self.assertEqual(self.conta('.folha [data-a="ben-identificar"]'), 0, "sem a IA, não aparece")

    def test_identificar_beneficios_de_uma_assinatura(self):
        """1.53: um gasto fixo, como uma assinatura, também dá benefícios: no fixo, Identificar benefícios abre a leitura
        por IA já com ele em De onde vêm (a assinatura com o nome dela); cadastrar volta para o fixo."""
        self.abrir(base(bancos=BANCOS, recorrencias=[FIXO], beneficios=[CREDITO]), ui={"tab": "mais", "maisTela": "caixa"})
        self.clicar('#app [data-a="fixo"][data-id="r-sol"]')
        self.assertEqual(self.texto('.folha [data-a="ben-identificar"]'), "Identificar benefícios")
        self.assertEqual(self.texto('.folha .bc-ben-n'), "1 benefício cadastrado.", "os Créditos de uso do Plano Sol")
        self.clicar('.folha [data-a="ben-identificar"]')
        self.assertEqual(self.folha(), "Ler benefícios com IA")
        self.assertEqual(self.texto('.folha [data-a="bler-origem"].on'), "Plano Sol (assinatura)", "já com a assinatura")
        self.preencher("#bler-txt", self.TEXTO)
        self.ler()
        self.assertEqual(self.itens()[1][0], False, "os Créditos de uso já estão cadastrados")
        self.clicar('#folhas [data-a="bler-salvar"]')
        self.assertEqual(self.esperar_aviso("cadastrados"), "2 benefícios cadastrados")
        self.assertEqual(self.folha(), "Despesa", "volta para o fixo")
        self.assertEqual(self.texto('.folha .bc-ben-n'), "3 benefícios cadastrados.")
        self.assertEqual({b["origem"] for b in self.dados()["beneficios"]}, {"fixo:r-sol"})

    def test_sem_identificar_num_recebimento_nem_num_lancamento_avulso(self):
        sal = {"id": "r-sal", "tipo": "receita", "descricao": "Salário", "valor": 5000, "dia": 5, "freq": "mensal", "inicio": "2026-01", "categoria": "c-salario"}
        self.abrir(base(bancos=BANCOS, recorrencias=[FIXO, sal]), ui={"tab": "mais", "maisTela": "caixa"})
        self.clicar('#app [data-a="fixo"][data-id="r-sal"]')
        self.assertEqual(self.conta('.folha [data-a="ben-identificar"]'), 0, "recebimento não dá benefício")
        self.js("(T.fecharFolha(true), T.abrirLancamento(null, { tipo: 'despesa' }), true)")
        self.esperar()
        self.assertEqual(self.conta('.folha [data-a="ben-identificar"]'), 0, "um gasto avulso também não")

    def test_imagem_voltar_e_nada_achado(self):
        from tests.test_tela_ia import _SOLTAR
        self.abrir_ben()
        self.clicar('[data-a="ben-ler"]')
        self.preencher("#bler-txt", "Nada que sirva")
        self.ler()
        self.assertEqual((self.folha(), self.texto("#folhas .msg-erro")), ("Ler benefícios com IA", "A IA não achou benefícios nem oportunidades aqui."))
        self.preencher("#bler-txt", "")
        self.assertEqual(self.conta("#folhas .msg-erro"), 0, "digitando, o aviso sai")
        self.pg.evaluate(_SOLTAR, {"como": "colar", "tipo": "png", "nome": "beneficios.png"})
        self.pg.wait_for_selector("#folhas .ia-prev")
        self.assertEqual(self.texto("#folhas .ia-prev b"), "beneficios.png")
        self.ler()
        self.assertEqual([x[1] for x in self.itens()], ["Sala VIP", "Créditos de uso", "Seguro viagem", "Sem anuidade"], "e embaixo a oportunidade")
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
        texto = (self.TEXTO + "\nSala VIP liberada\n2 visitas ao lounge ao ano, com 2 acompanhantes\nR$ 50 de bônus\nSeguro celular; Cashback de 1%"
                 "\nAnuidade grátis com R$ 50 mil investidos\nSala VIP gastando R$ 3.000 por mês\nPlano Família por R$ 34,99 por mês\nPlano Anual por R$ 300 por ano")
        self.abrir_ben()
        js = self.js("T.simBeneficios(" + __import__("json").dumps(texto) + ")")
        self.assertEqual(js, B.limpar(B.simulados(texto), texto)[0])
        self.assertEqual(self.js("T.simMetas(" + __import__("json").dumps(texto) + ")"), B.limpar_metas(B.simulados(texto), texto)[0])

    def test_oportunidades_na_mesma_leitura(self):
        """1.54: a leitura também acha o que a pessoa ganha a mais cumprindo uma condição; elas vêm embaixo, em
        Oportunidades, marcadas (a mesma condição já cadastrada vem desmarcada), e vão para Mais › Benefícios › Oportunidades."""
        ja = {"id": "mt-ja", "tipo": "gasto", "origem": "conta:k-ana", "valor": 3000, "periodo": "mes", "ganha": "Sala VIP"}
        self.abrir_ben(metas=[ja])
        self.clicar('[data-a="ben-ler"]')
        self.clicar('.folha [data-a="bler-origem"][data-v="conta:k-ana"]')
        self.preencher("#bler-txt", "Frete grátis\nAnuidade grátis com R$ 50 mil investidos\nSala VIP gastando R$ 3.000 por mês")
        self.ler()
        self.assertEqual(self.folha(), "Benefícios encontrados")
        self.assertEqual(self.texto("#folhas .bler-sec"), "Oportunidades")
        self.assertEqual(self.itens(), [[True, "Frete grátis", "Vantagem", ""], [True, "Sem anuidade", "Investindo R$ 50 mil", ""],
                                        [False, "Sala VIP", "Gastando R$ 3.000 por mês no cartão", "já cadastrado"]])
        self.assertEqual(self.texto('#folhas [data-a="bler-salvar"]'), "Cadastrar 2")
        self.clicar('#folhas [data-a="bler-salvar"]')
        self.assertEqual(self.esperar_aviso("cadastrad"), "1 benefício e 1 oportunidade cadastrados")
        m = self.dados()["metas"][1]
        self.assertEqual({k: v for k, v in m.items() if k != "id"},
                         {"tipo": "investido", "origem": "conta:k-ana", "valor": 50000, "ganha": "Sem anuidade", "trecho": "Anuidade grátis com R$ 50 mil investidos"})
        # só oportunidades
        self.clicar('[data-a="ben-ler"]')
        self.preencher("#bler-txt", "Plano Família por R$ 34,99 por mês")
        TestLerComIA.ler(self)
        self.assertEqual(self.folha(), "Oportunidades encontradas")
        self.assertEqual(self.conta("#folhas .bler-sec"), 0, "sem benefícios, sem o título")
        self.assertEqual(self.itens(), [[True, "Plano Família", "Plano Plano Família por R$ 34,99 por mês", ""]])
        self.clicar('#folhas [data-a="bler-meta"][data-v="0"]')
        self.assertTrue(self.js("document.querySelector('[data-a=\"bler-salvar\"]').disabled"), "nada marcado")
        self.clicar('#folhas [data-a="bler-meta"][data-v="0"]')
        self.clicar('#folhas [data-a="bler-salvar"]')
        self.assertEqual(self.esperar_aviso("cadastrada"), "Oportunidade cadastrada")
        # de uma assinatura: um plano que não custa mais que o de agora (R$ 110) não é oportunidade
        self.clicar('[data-a="ben-ler"]')
        self.clicar('.folha [data-a="bler-origem"][data-v="fixo:r-sol"]')
        self.preencher("#bler-txt", "Plano Básico por R$ 50 por mês\nPlano Família por R$ 150 por mês")
        self.ler()
        self.assertEqual([x[1] for x in self.itens()], ["Plano Família"])

    def test_sem_ia_so_cadastrar(self):
        self.abrir_ben(ajustes={"corrigir": True, "ia": False})
        self.assertEqual(self.textos("#beneficios > .btn"), ["Cadastrar benefício"])
        self.assertEqual(self.conta('[data-a="ben-ler"]'), 0)


class TestOportunidades(TelaBen):
    """1.54: Mais › Benefícios › Oportunidades: o que falta para ganhar mais, investindo (a anuidade grátis com R$ 50 mil
    investidos; o próximo nível da conta), gastando no cartão (a sala VIP gastando R$ 3 mil por mês) ou mudando de plano
    (o de 2 TB por R$ 130 em vez de R$ 110). Da mais perto para a mais longe; as que já dão no fim."""
    CDB = {"id": "i-cdb", "nome": "CDB", "banco": "b-azul", "conta": "k-ana", "titular": "meu", "valor": 45000, "data_valor": "2026-11-02", "indexador": "pre", "taxa": 10}
    ANUIDADE = {"id": "mt-anu", "tipo": "investido", "origem": "conta:k-ana", "valor": 50000, "ganha": "Sem anuidade"}
    VIP = {"id": "mt-vip", "tipo": "gasto", "origem": "conta:k-ana", "valor": 3000, "periodo": "mes", "ganha": "Sala VIP"}
    ESPACO = {"id": "mt-2tb", "tipo": "plano", "origem": "fixo:r-sol", "valor": 130, "periodo": "mes", "ganha": "Mais espaço", "plano": "2 TB"}
    CASHBACK = {"id": "mt-cb", "tipo": "gasto", "origem": "conta:k-ana", "valor": 2000, "periodo": "mes", "ganha": "Cashback"}

    def abrir_metas(self, metas=(), **mais):
        import copy
        bancos = copy.deepcopy(BANCOS)
        bancos[0]["contas"][1].update(meta_nivel="Black", meta_valor=100000)  # o próximo nível do Beto, em Editar banco
        compra = lambda dia, v: {"id": "l-" + dia, "tipo": "despesa", "descricao": "Compra", "valor": v, "data": dia, "cartao": True, "conta": "k-ana",  # noqa: E731
                                 "categoria": "c-mercado", "pago": True}
        d = base(bancos=bancos, recorrencias=[FIXO], investimentos=[self.CDB], metas=list(metas),
                 lancamentos=[compra("2026-07-10", 2400), compra("2026-08-10", 2500), compra("2026-09-10", 2600)])  # as faturas de ago, set e out
        d.update(mais)
        self.abrir(d, ui=BENS)

    def metas(self):
        return self.js("""[...document.querySelectorAll('#metas .ben-row')].map(r => [r.querySelector('.ben-t b').textContent, r.querySelector('.ben-t > span').textContent,
            (r.querySelector('.ben-v b') || {}).textContent || '', (r.querySelector('.ben-v small') || {}).textContent || ''])""")

    def test_lista_da_mais_perto_para_a_mais_longe(self):
        self.abrir_metas([self.CASHBACK, self.ESPACO, self.VIP, self.ANUIDADE])
        self.assertEqual(self.texto("#metas .mais-head h2"), "Oportunidades")
        self.assertEqual(self.metas(), [
            ["Sem anuidade", "Banco Azul · Ana · com R$ 50 mil investidos", "faltam R$ 5.000", "tem R$ 45 mil"],
            ["Sala VIP", "Banco Azul · Ana · gastando R$ 3.000 por mês no cartão", "faltam R$ 500", "média R$ 2.500"],
            ["Mais espaço", "Plano Sol · 2 TB por R$ 130,00 por mês", "+R$ 20,00", "por mês"],
            ["Nível Black", "Banco Azul · Beto · com R$ 100 mil investidos", "faltam R$ 100 mil", "tem R$ 0"],
            ["Cashback", "Banco Azul · Ana · gastando R$ 2.000 por mês no cartão", "Já dá", "média R$ 2.500"]])
        self.assertEqual(self.js("[...document.querySelectorAll('#metas .ben-barra i')].map(i => i.style.width)"), ["90%", "83.3%", "0%", "100%"])
        # o nível abre o banco (é de lá, em Editar banco); as outras, o formulário
        self.clicar('#metas [data-a="banco"]')
        self.assertEqual(self.folha(), "Editar banco")
        self.js("(T.fecharFolha(true), true)")
        self.clicar('#metas [data-a="meta-editar"][data-id="mt-vip"]')
        self.assertEqual(self.folha(), "Editar oportunidade")
        self.assertEqual(self.texto("#fmeta-st"), "Sua média no cartão: R$ 2.500 por mês. Faltam R$ 500.")

    def test_sem_como_saber(self):
        sem_cartao = dict(self.VIP, id="mt-x", origem="conta:k-verde")
        sem_fatura = dict(self.VIP, id="mt-y", origem="conta:k-beto")
        self.abrir_metas([sem_cartao, sem_fatura, dict(self.ANUIDADE, origem="conta:sumiu")], bancos=BANCOS)
        self.assertEqual([m[3] for m in self.metas()], ["A conta não tem cartão", "Sem faturas nos últimos 3 meses", "Diga de onde vem"])
        self.assertEqual(self.metas()[2][1], "Conta apagada · com R$ 50 mil investidos")

    def test_vazio(self):
        self.abrir_metas(bancos=BANCOS)
        self.assertEqual(self.texto("#metas .vazio"), "Nenhuma oportunidade ainda.")
        # 1.62.0: Cadastrar e Ler com IA lado a lado, como nos Benefícios; a leitura é a mesma, com o título das oportunidades
        self.assertEqual(self.textos("#metas .ben-botoes .btn"), ["Cadastrar", "Ler com IA"])
        med = self.js("[...document.querySelectorAll('#metas .ben-botoes .btn')].map(b => [Math.round(b.getBoundingClientRect().top), Math.round(b.getBoundingClientRect().width), b.offsetHeight])")
        self.assertTrue(med[0] == med[1], f"do mesmo tamanho, na mesma linha ({med})")
        self.clicar('#metas [data-a="meta-ler"]')
        self.assertEqual(self.folha(), "Ler oportunidades com IA")
        self.preencher("#bler-txt", "Plano Básico por R$ 50 por mês\nPlano Família por R$ 150 por mês")
        TestLerComIA.ler(self)
        self.assertEqual(self.folha(), "Oportunidades encontradas")
        self.js("(T.fecharFolha(), true)")
        self.abrir_metas(bancos=BANCOS, ajustes={"corrigir": True, "ia": False})
        self.assertEqual(self.texto("#metas .vazio"), "Nenhuma oportunidade ainda.")
        self.assertEqual(self.textos("#metas > .btn"), ["Cadastrar oportunidade"])

    def test_cadastrar_editar_e_apagar(self):
        self.abrir_metas(bancos=BANCOS)
        self.clicar('#metas [data-a="meta-nova"]')
        self.assertEqual(self.folha(), "Nova oportunidade")
        origens = lambda: self.textos('.folha [data-a="fmeta-origem"]')  # noqa: E731
        self.assertEqual(origens(), ["Banco Azul · Ana · cartão", "Banco Azul · Beto · cartão", "Banco Verde · Ana"], "investindo: as contas")
        self.clicar('.folha [data-a="fmeta-salvar"]')
        self.assertEqual(self.esperar_aviso("Diga"), "Diga o que ganha.")
        self.preencher("#fmeta-ganha", "Sala VIP")
        self.clicar('.folha [data-a="fmeta-seg"][data-k="tipo"][data-v="gasto"]')
        self.assertEqual(origens(), ["Banco Azul · Ana · cartão", "Banco Azul · Beto · cartão"], "gastando: só os cartões")
        self.assertEqual(self.texto(".folha #fmeta-origem-l"), "Qual cartão")
        self.clicar('.folha [data-a="fmeta-salvar"]')
        self.assertEqual(self.esperar_aviso("Diga o valor"), "Diga o valor.")
        self.preencher("#fmeta-valor", "36.000")
        self.clicar('.folha [data-a="fmeta-seg"][data-k="periodo"][data-v="ano"]')
        self.clicar('.folha [data-a="fmeta-salvar"]')
        self.assertEqual(self.esperar_aviso("Escolha"), "Escolha o cartão.")
        self.clicar('.folha [data-a="fmeta-origem"][data-v="conta:k-ana"]')
        self.assertEqual(self.texto("#fmeta-st"), "Sua média no cartão: R$ 2.500 por mês. Faltam R$ 500.", "R$ 36 mil por ano são R$ 3 mil por mês")
        self.preencher("#fmeta-valor", "24.000")
        self.assertEqual(self.texto("#fmeta-st"), "Sua média no cartão: R$ 2.500 por mês. Já dá.", "muda enquanto digita")
        self.clicar('.folha [data-a="fmeta-salvar"]')
        self.assertEqual(self.esperar_aviso("cadastrada"), "Oportunidade cadastrada")
        m = self.dados()["metas"][0]
        self.assertEqual({k: v for k, v in m.items() if k != "id"}, {"tipo": "gasto", "origem": "conta:k-ana", "valor": 24000, "ganha": "Sala VIP", "periodo": "ano"})
        self.assertEqual(self.metas()[-1], ["Sala VIP", "Banco Azul · Ana · gastando R$ 2.000 por mês no cartão", "Já dá", "média R$ 2.500"])
        # mudar para outro plano: só os fixos; o plano e o preço
        self.clicar('#metas [data-a="meta-editar"]')
        self.clicar('.folha [data-a="fmeta-seg"][data-k="tipo"][data-v="plano"]')
        self.assertEqual(origens(), ["Plano Sol (assinatura)"])
        self.clicar('.folha [data-a="fmeta-origem"][data-v="fixo:r-sol"]')
        self.preencher("#fmeta-plano", "2 TB")
        self.preencher("#fmeta-valor", "130")
        self.clicar('.folha [data-a="fmeta-seg"][data-k="periodo"][data-v="mes"]')
        self.assertEqual(self.texto("#fmeta-st"), "Você paga R$ 110,00 por mês. São R$ 20,00 a mais.")
        self.clicar('.folha [data-a="fmeta-salvar"]')
        self.assertEqual(self.esperar_aviso("salva"), "Oportunidade salva")
        self.assertEqual([m["tipo"], m["plano"], m["valor"]] if (m := self.dados()["metas"][0]) else None, ["plano", "2 TB", 130])
        # apagar pergunta antes
        self.clicar('#metas [data-a="meta-editar"]')
        self.clicar('.folha [data-a="fmeta-excluir"]')
        self.assertEqual(self.folha(), "Apagar oportunidade?")
        self.clicar('.folha-pe [data-a="confirmar"]')
        self.assertEqual(self.esperar_aviso("apagada"), "Oportunidade apagada")
        self.assertEqual(self.dados()["metas"], [])


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



VOA = {"id": "bn-voa", "tipo": "milhas", "nome": "Voa Mais", "pessoa": "Ana", "origem": "conta:k-ana", "saldo": 12300, "saldo_em": "2026-10-01",
       "nivel": "Prata", "proximo": {"nivel": "Ouro", "pede": 25000, "tem": 3200, "unidade": "milhas"},
       "vencem": [{"qtd": 2000, "data": "2026-12-31"}], "resgates": [{"nome": "Cidade A – Cidade B", "milhas": 7500}, {"nome": "Cidade A – Cidade C", "milhas": 12500}],
       "usos": [{"id": "u1", "data": "2026-10-20", "qtd": 1000}]}


class TestMilhas(TelaBen):
    """1.63.0: o tipo Milhas: o programa de uma pessoa, com o saldo, o nível, o que vence e o próximo nível (nas
    Oportunidades); Resgatei desconta; Ler com IA põe no formulário o que leu do print e da página do programa."""

    def test_lista_oportunidade_e_aviso(self):
        self.abrir_ben([VOA, VIP])
        self.assertEqual(self.textos("#beneficios .ben-grupo-cab b"), ["Milhas", "Banco Azul · Ana"], "as milhas em cima")
        self.assertEqual(self.linhas()[0], ["Voa Mais · Ana", "Prata · vencem 2.000 em 31/12/2026 · dá para 1 troca", "11.300", "milhas"])
        meta = self.js("""(() => { const r = [...document.querySelectorAll('#metas .meta-row')].find(x => /Ouro/.test(x.textContent));
            return [r.querySelector('.ben-t b').textContent, r.querySelector('.ben-t > span').textContent, r.querySelector('.ben-v b').textContent, r.querySelector('.ben-v small').textContent]; })()""")
        self.assertEqual(meta, ["Nível Ouro", "Voa Mais · Ana · com 25.000 milhas qualificáveis", "faltam 21.800", "milhas · tem 3.200"])
        self.abrir(base(bancos=BANCOS, recorrencias=[FIXO], beneficios=[VOA]), ui={"tab": "inicio"})
        self.assertIn("Milhas que vencem Voa Mais · Ana: 2.000 em 31/12", " ".join(self.tela().split()))
        # com investimentos, o Início também mostra os avisos dos benefícios (1.63.0)
        inv = {"id": "i1", "nome": "CDB Azul", "banco": "b-azul", "tipo": "cdb", "indexador": "cdi_pct", "taxa": 100, "valor": 1000, "data_valor": "2026-11-01", "inicio": "2026-01-01"}
        self.abrir(base(bancos=BANCOS, recorrencias=[FIXO], beneficios=[VOA], investimentos=[inv]), ui={"tab": "inicio"})
        self.assertIn("Milhas que vencem Voa Mais · Ana: 2.000 em 31/12", " ".join(self.tela().split()))

    def test_resgatei_desconta(self):
        self.abrir_ben([VOA])
        self.assertEqual(self.texto("#beneficios .mil-row .ben-usar"), "Resgatei")
        self.clicar('#beneficios .mil-row [data-a="ben-usar"]')
        self.assertEqual(self.folha(), "Quantas milhas resgatou de Voa Mais · Ana?")
        self.preencher("#fben-usou", "500")
        self.clicar('#folhas [data-a="fben-usou"]')
        self.assertEqual(self.esperar_aviso("Voa Mais"), "Voa Mais · Ana: ficam 10.800 milhas")
        self.assertEqual(self.linhas()[0][2], "10.800")

    def test_cadastrar_lendo_o_print_e_a_pagina(self):
        self.abrir_ben([])
        self.clicar('[data-a="ben-novo"]')
        self.clicar('#folhas [data-a="fben-seg"][data-k="tipo"][data-v="milhas"]')
        self.assertEqual(self.folha(), "Novas milhas")
        self.preencher("#fben-nome", "Voa Mais")
        self.preencher("#fben-pessoa", "Ana")
        # o print da conta (aqui, o texto dele): saldo, nível, qualificáveis e o que vence
        self.clicar('#folhas [data-a="fmil-ler"]')
        self.assertEqual(self.folha(), "Ler milhas com IA")
        self.assertEqual(self.js("document.querySelectorAll('#folhas [data-a=\"bler-origem\"]').length"), 0, "sem De onde vêm")
        self.preencher("#bler-txt", "Saldo: 12.000 milhas\nNível: Prata\nMilhas qualificáveis: 5.000\n3.000 milhas vencem em 31/01/2027")
        TestLerComIA.ler(self)
        self.assertEqual(self.folha(), "Novas milhas", "volta ao formulário")
        self.assertEqual(self.esperar_aviso("Lido"), "Lido: saldo, nível, qualificáveis, o que vence. Confira e salve.")
        self.assertEqual([self.js(f"document.getElementById('{i}').value") for i in ("fben-saldo", "fben-nivel", "fben-tem", "fben-venc", "fben-venc-data")],
                         ["12000", "Prata", "5000", "3000", "2027-01-31"])
        # a página do programa: o próximo nível, as vantagens, a tabela de resgate e como trocar
        self.clicar('#folhas [data-a="fmil-ler"]')
        self.preencher("#bler-txt", "voamais.exemplo/niveis")
        TestLerComIA.ler(self)
        self.assertEqual(self.esperar_aviso("Lido"), "Lido: próximo nível, 2 vantagens, 3 trocas, como trocar. Confira e salve.")
        self.assertEqual(self.js("document.getElementById('fmil-st').textContent"), "Faltam 20.000 milhas qualificáveis para o Ouro.")
        trocas = self.js("[...document.querySelectorAll('#folhas .mil-lista li')].filter(l => l.querySelector('b')).map(l => [...l.children].map(c => c.textContent).join(' '))")
        self.assertEqual(trocas[:3], ["Cidade A – Cidade B 7.500 já dá", "Cidade A – Cidade C 12.500 faltam 500", "Cidade A – Cidade D 30.000 faltam 18.000"])
        self.clicar('#folhas [data-a="fben-salvar"]')
        self.esperar()
        b = self.dados()["beneficios"][0]
        self.assertEqual({k: b.get(k) for k in ("tipo", "nome", "pessoa", "saldo", "saldo_em", "nivel", "proximo", "vencem", "url")},
                         {"tipo": "milhas", "nome": "Voa Mais", "pessoa": "Ana", "saldo": 12000, "saldo_em": "2026-11-02", "nivel": "Prata",
                          "proximo": {"nivel": "Ouro", "pede": 25000, "tem": 5000, "unidade": "milhas"}, "vencem": [{"qtd": 3000, "data": "2027-01-31"}],
                          "url": "https://voamais.exemplo/niveis"})
        self.assertEqual((len(b["vantagens"]), [r["milhas"] for r in b["resgates"]], b["como"]),
                         (2, [7500, 12500, 30000], ["Resgate no site ou no app, em Usar milhas"]))
        self.assertEqual(self.linhas()[0], ["Voa Mais · Ana", "Prata · vencem 3.000 em 31/01/2027 · dá para 1 troca", "12.000", "milhas"])

    def test_editar_e_apagar(self):
        self.abrir_ben([dict(VOA, vencem=[{"qtd": 2000, "data": "2026-12-31"}, {"qtd": 700, "data": "2027-03-31"}])])
        self.clicar('#beneficios .mil-row [data-a="ben-editar"]')
        self.assertEqual(self.folha(), "Editar milhas")
        self.assertEqual(self.js("document.querySelectorAll('#folhas [data-a=\"fben-seg\"][data-k=\"tipo\"]').length"), 0, "sem trocar o tipo")
        self.assertEqual(self.js("document.getElementById('fmil-st').textContent"), "Faltam 21.800 milhas qualificáveis para o Ouro.")
        self.assertIn("Hoje: 11.300 milhas, com os resgates.", self.folha_texto())
        self.clicar('#folhas [data-a="fmil-lote-rm"]')
        self.clicar('#folhas [data-a="fben-salvar"]')
        self.esperar()
        b = self.dados()["beneficios"][0]
        self.assertEqual((b["vencem"], b["saldo_em"]), ([{"qtd": 2000, "data": "2026-12-31"}], "2026-10-01"), "o saldo não mudou: a data dele fica")
        self.clicar('#beneficios .mil-row [data-a="ben-editar"]')
        self.clicar('#folhas [data-a="fben-excluir"]')
        self.assertIn("Voa Mais · Ana sai da lista, com os resgates.", self.folha_texto())


if __name__ == "__main__":
    unittest.main()
