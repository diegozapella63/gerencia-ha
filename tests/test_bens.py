"""bens.py: os bens do InventarIA, depreciados por categoria (só lê; nada muda lá)."""
import json
import os
import unittest
from datetime import date

from tests.base import ServidorFalso, pasta_temp, porta_fechada
import bens

ITENS = [
    {"nome": "Televisão", "categoria": "eletronicos", "comodo": "sala", "valor": 3000, "valor_em": "2025-11-02"},
    {"nome": "Sofá", "categoria": "moveis", "comodo": "sala", "valor": 2000, "valor_em": "2026-11-02"},
    {"nome": "Carro", "categoria": "veiculos", "comodo": "", "valor": 50000, "valor_em": "2024-11-02"},
    {"nome": "Quadro", "categoria": "nova", "comodo": "quarto", "valor": 100, "valor_em": "sem data"},
    {"nome": "Sem valor", "categoria": "moveis", "valor": 0},
    {"nome": "Negativo", "categoria": "moveis", "valor": -5},
]


class TestTaxasEValor(unittest.TestCase):
    def test_taxas_padrao_e_ajustes(self):
        t = bens.taxas({})
        self.assertEqual((t["imoveis"], t["veiculos"], t["eletronicos"], t["vestuario"]), (0, 15, 20, 25))
        t = bens.taxas({"bens_taxas": {"moveis": "12.5", "imoveis": -3, "x": 500, "y": -90, "z": "abc", "w": None}})
        self.assertEqual((t["moveis"], t["imoveis"], t["x"], t["y"]), (12.5, -3, 100, -50))
        self.assertNotIn("z", t)
        self.assertNotIn("w", t)
        self.assertEqual(bens.taxas(None)["outros"], 10)

    def test_valor_hoje(self):
        self.assertAlmostEqual(bens.valor_hoje(1000, "2025-11-02", 20, hoje=date(2026, 11, 2)), 1000 * 0.8 ** (365 / 365.25))
        self.assertEqual(bens.valor_hoje(1000, "data ruim", 20), 1000)
        self.assertEqual(bens.valor_hoje(1000, "2030-01-01", 20, hoje=date(2026, 11, 2)), 1000, "data no futuro: não perde")
        self.assertAlmostEqual(bens.valor_hoje(1000, "2024-11-02T10:00:00", -10, hoje=date(2026, 11, 2)), 1000 * 1.1 ** (730 / 365.25), msg="taxa negativa: valoriza")


class TestResumo(unittest.TestCase):
    def setUp(self):
        self.dados = {"itens": ITENS, "comodos": {"sala": "Sala", "quarto": "Quarto"}, "categorias": dict(bens.NOMES_PADRAO, nova="Nova"),
                      "versao": "1.17.0", "lido_em": "2026-11-02T10:00:00"}
        self.r = bens.resumo(self.dados, {"bens_taxas": {"veiculos": 10}}, hoje=date(2026, 11, 2))

    def test_totais(self):
        r = self.r
        self.assertEqual((r["ok"], r["n"], r["registrado"], r["versao"]), (True, 4, 55100, "1.17.0"))
        tv = 3000 * 0.8 ** (365 / 365.25)
        carro = 50000 * 0.9 ** (730 / 365.25)
        self.assertAlmostEqual(r["hoje"], round(tv + 2000 + carro + 100, 2), places=1)
        self.assertAlmostEqual(r["perde_ano"], round(tv * 0.2 + 2000 * 0.1 + carro * 0.1 + 100 * 0.1, 2), places=1)

    def test_categorias_e_comodos(self):
        cats = {c["id"]: c for c in self.r["categorias"]}
        self.assertEqual(cats["veiculos"]["taxa"], 10, "a taxa ajustada")
        self.assertEqual(cats["nova"]["taxa"], 10, "categoria nova: 10% ao ano")
        self.assertEqual(cats["moveis"]["n"], 1, "sem valor não conta")
        self.assertEqual(self.r["categorias"][0]["id"], "veiculos", "a maior primeiro")
        coms = {c["id"]: c for c in self.r["comodos"]}
        self.assertEqual(coms[""]["nome"], "Sem cômodo")
        self.assertEqual(coms["sala"]["n"], 2)
        self.assertNotIn("registrado", coms["sala"])

    def test_maiores_e_todas(self):
        self.assertEqual([m["nome"] for m in self.r["maiores"]], ["Carro", "Televisão", "Sofá", "Quadro"])
        self.assertEqual(self.r["todas"][0], {"id": "imoveis", "nome": "Imóveis", "taxa": 0})
        self.assertEqual(self.r["todas"][-1]["id"], "nova")

    def test_no_maximo_10_maiores(self):
        dados = dict(self.dados, itens=[{"nome": f"i{k}", "categoria": "moveis", "valor": k + 1, "valor_em": "2026-11-02"} for k in range(15)])
        self.assertEqual(len(bens.resumo(dados, {}, hoje=date(2026, 11, 2))["maiores"]), 10)


class TestItensHoje(unittest.TestCase):
    """Todos os itens, um por um, para o Relatório de patrimônio."""

    def setUp(self):
        dados = {"itens": ITENS + [{"nome": "Valor ruim", "categoria": "moveis", "valor": "abc"}],
                 "comodos": {"sala": "Sala", "quarto": "Quarto"}, "categorias": dict(bens.NOMES_PADRAO)}
        self.l = bens.itens_hoje(dados, {"bens_taxas": {"veiculos": 10}}, hoje=date(2026, 11, 2))

    def test_so_com_valor_do_maior_para_o_menor(self):
        self.assertEqual([i["nome"] for i in self.l], ["Carro", "Televisão", "Sofá", "Quadro"])

    def test_cada_item(self):
        carro, tv, sofa, quadro = self.l
        self.assertEqual((carro["taxa"], carro["categoria_nome"], carro["comodo_nome"]), (10, "Veículos", ""), "a taxa ajustada; sem cômodo")
        self.assertAlmostEqual(carro["hoje"], 50000 * 0.9 ** (730 / 365.25))
        self.assertEqual((tv["comodo_nome"], tv["valor"], tv["valor_em"]), ("Sala", 3000, "2025-11-02"))
        self.assertEqual((quadro["categoria_nome"], quadro["taxa"], quadro["hoje"]), ("nova", 10, 100), "categoria que não está na lista: o id")

    def test_soma_igual_ao_resumo(self):
        dados = {"itens": ITENS, "comodos": {}, "categorias": dict(bens.NOMES_PADRAO)}
        r = bens.resumo(dados, {}, hoje=date(2026, 11, 2))
        self.assertAlmostEqual(sum(i["hoje"] for i in bens.itens_hoje(dados, {}, hoje=date(2026, 11, 2))), r["hoje"], places=1)

    def test_sem_itens(self):
        self.assertEqual(bens.itens_hoje({}, {}), [])


class TestLeitura(unittest.TestCase):
    def setUp(self):
        self.pasta = pasta_temp()
        self.arq = os.path.join(self.pasta, "integracao.json")
        self._arq0 = bens.ARQ
        bens.ARQ = self.arq
        self.logs = []
        self.b = bens.Bens(self.logs.append)
        self.servidores = []

    def tearDown(self):
        bens.ARQ = self._arq0
        for s in self.servidores:
            s.fechar()

    def servidor(self, itens=ITENS, categorias=None, comodos_status=200):
        corpo = {"itens": itens, "versao": "1.17.0"}
        if categorias is not None:
            corpo["categorias"] = categorias
        s = ServidorFalso({"/api/integracao/itens": (200, corpo), "/api/integracao/comodos": (comodos_status, {"comodos": [{"id": "sala", "nome": "Sala"}]})})
        self.servidores.append(s)
        return s

    def conexao(self, **c):
        with open(self.arq, "w", encoding="utf-8") as f:
            f.write(c.pop("_texto", None) or json.dumps(c))

    def test_sem_arquivo_ou_arquivo_ruim(self):
        self.assertIsNone(self.b.conexao())
        self.conexao(_texto="{não é json")
        self.assertIsNone(self.b.conexao())
        self.conexao(url="http://x")
        self.assertIsNone(self.b.conexao(), "sem chave")
        self.conexao(chave="k")
        self.assertIsNone(self.b.conexao(), "sem endereço")
        self.conexao(_texto="[1, 2]")
        self.assertIsNone(self.b.conexao())
        with self.assertRaisesRegex(bens.ErroBens, "não foi encontrado"):
            self.b.ler()

    def test_le_com_a_chave_e_guarda_por_10_minutos(self):
        s = self.servidor(categorias={"moveis": "Móveis da casa"})
        self.conexao(url=s.url, chave="segredo")
        d = self.b.ler()
        self.assertEqual(len(d["itens"]), len(ITENS))
        self.assertEqual(d["comodos"], {"sala": "Sala"})
        self.assertEqual(d["categorias"], {"moveis": "Móveis da casa"})
        self.assertEqual(d["versao"], "1.17.0")
        metodo, caminho, cab, _ = s.pedidos[0]
        self.assertEqual((metodo, caminho, cab["Authorization"], cab["X-App"]), ("GET", "/api/integracao/itens", "Bearer segredo", "GerencIA"))
        n = len(s.pedidos)
        self.b.ler()
        self.assertEqual(len(s.pedidos), n, "do cache")
        self.b.ler(forcar=True)
        self.assertEqual(len(s.pedidos), n * 2, "Atualizar lê de novo")

    def test_sem_categorias_usa_as_de_costume_e_sem_comodos_segue(self):
        s = self.servidor(comodos_status=500)
        self.conexao(url=s.url, chave="k")
        d = self.b.ler()
        self.assertEqual(d["categorias"], bens.NOMES_PADRAO)
        self.assertEqual(d["comodos"], {})

    def test_versao_antiga_sem_valores(self):
        s = self.servidor(itens=[{"nome": "x"}])
        self.conexao(url=s.url, chave="k")
        with self.assertRaisesRegex(bens.ErroBens, "1.16.0 ou mais nova"):
            self.b.ler()

    def test_tenta_o_outro_endereco(self):
        s = self.servidor()
        self.conexao(url=f"http://127.0.0.1:{porta_fechada()}", ip_url=s.url, chave="k")
        self.assertEqual(len(self.b.ler()["itens"]), len(ITENS))

    def test_nenhum_endereco_responde(self):
        self.conexao(url=f"http://127.0.0.1:{porta_fechada()}", chave="k")
        with self.assertRaisesRegex(bens.ErroBens, "O InventarIA não respondeu"):
            self.b.ler()


if __name__ == "__main__":
    unittest.main()
