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
        self.pg.select_option("#fben-origem", "conta:k-ana")
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
        self.pg.select_option("#fben-origem", "fixo:r-sol")
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
