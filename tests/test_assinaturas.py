"""assinaturas.py: dicas de economia só com preços conferidos na página oficial (página e preços de exemplo)."""
import unittest

from tests.base import APP  # noqa: F401 (o caminho do app)
import assinaturas as A

PAGINA = """<html><head><title>Planos</title><style>.x{color:red}</style><script>var preco = "R$ 1,00";</script></head>
<body><!-- R$ 2,00 escondido --><h1>Escolha seu plano</h1>
<div class="card"><h2>Individual</h2><p>R$&nbsp;23,90 por mês</p><p>ou R$ 239,00 por ano</p></div>
<div class="card"><h2>Família</h2><p>R$ 40,90/mês</p></div>
<div><h2>Anual</h2><p>US$ 65.00 per year</p></div><svg><text>R$ 3,00</text></svg>
<p>Plano Duo: 1.299,00 reais por ano</p></body></html>"""


class TestIdentificar(unittest.TestCase):
    def test_reconhece_pelo_nome(self):
        casos = {"Spotify": "spotify", "SPOTIFY PREMIUM família": "spotify", "Nabu Casa": "nabucasa", "nabucasa": "nabucasa",
                 "Home Assistant Cloud": "nabucasa", "Assinatura Claude Pro": "claude", "Anthropic": "claude",
                 "Microsoft 365 Family": "microsoft365", "Office365": "microsoft365", "Deezer Premium": "deezer"}
        for desc, cid in casos.items():
            with self.subTest(desc=desc):
                self.assertEqual(A.identificar(desc)["id"], cid)
        for desc in ("", None, "Netflix", "claudete", "spotifyx"):
            self.assertIsNone(A.identificar(desc), desc)

    def test_normal(self):
        self.assertEqual(A.normal("  Ação—Família  2026! "), "acao familia 2026")
        self.assertEqual(A.identificar("Assinatura—Claude")["id"], "claude", "travessão não gruda as palavras")
        self.assertEqual(A.identificar("Spotify·Família")["id"], "spotify")
        self.assertEqual(A.POR_ID["deezer"]["curto"], "Deezer")


class TestPagina(unittest.TestCase):
    def test_html_texto_tira_o_que_nao_se_le(self):
        t = A.html_texto(PAGINA)
        self.assertIn("R$ 23,90 por mês", t)
        for fora in ("R$ 1,00", "R$ 2,00", "R$ 3,00", "color:red", "Planos"):
            self.assertNotIn(fora, t, fora)
        self.assertIn("Individual\nR$ 23,90 por mês\nou R$ 239,00 por ano", t, "uma linha por bloco")
        self.assertEqual(A.html_texto(None), "")

    def test_trechos_so_onde_ha_preco(self):
        texto = "a" * 1000 + " R$ 10,00 " + "b" * 1000 + " 20 USD " + "c" * 1000
        t = A.trechos_preco(texto, margem=50)
        self.assertEqual(t.count("[...]"), 1)
        self.assertIn("R$ 10,00", t)
        self.assertIn("20 USD", t)
        self.assertLess(len(t), 300)
        perto = A.trechos_preco("x R$ 1 y R$ 2 z", margem=50)
        self.assertNotIn("[...]", perto, "faixas que se tocam viram uma")
        self.assertLessEqual(len(A.trechos_preco(("R$ 1 " + "x" * 400 + " ") * 100, limite=1000, margem=10)), 1100)
        self.assertEqual(A.trechos_preco("sem preço nenhum"), "")

    def test_numeros(self):
        self.assertEqual(A.numeros("R$ 1.299,00 ou $1,299.00"), {1299.0})
        self.assertEqual(A.numeros("6.50 e 6,50 e 65"), {6.5, 65.0})
        self.assertEqual(A.numeros("1.234.567"), {1234567.0})
        self.assertEqual(A.numeros("1,234"), {1234.0})
        self.assertEqual(A.numeros(None), set())

    def test_confere(self):
        tc = A.para_comparar(A.html_texto(PAGINA))
        self.assertTrue(A.confere("R$ 23,90 por mês", 23.9, tc))
        self.assertTrue(A.confere("r$  23,90 POR MÊS", 23.9, tc), "sem diferença de caixa e espaços")
        self.assertFalse(A.confere("R$ 23,90 por mês", 24.9, tc), "o número não está no trecho")
        self.assertFalse(A.confere("R$ 19,90 por mês", 19.9, tc), "o trecho não está na página")
        self.assertFalse(A.confere("R$", 1, tc), "trecho curto demais")
        self.assertFalse(A.confere("", 23.9, tc))
        self.assertFalse(A.confere("R$ 23,90 por mês", 0, tc))


class TestPlanos(unittest.TestCase):
    TEXTO = A.html_texto(PAGINA)

    def test_fica_so_com_o_que_a_pagina_confirma(self):
        parsed = {"planos": [
            {"plano": "Individual", "moeda": "BRL", "mensal": 23.9, "trecho_mensal": "R$ 23,90 por mês", "anual_total": 239, "trecho_anual": "R$ 239,00 por ano"},
            {"plano": "Família", "moeda": "brl", "mensal": "40,90", "trecho_mensal": "R$ 40,90/mês", "anual_total": 400, "trecho_anual": "R$ 400 por ano"},
            {"plano": "Inventado", "moeda": "BRL", "mensal": 9.9, "trecho_mensal": "R$ 9,90 por mês"},
            {"plano": "Sem moeda", "mensal": 5, "trecho_mensal": "5 por mês"},
            "lixo",
        ]}
        planos, recusados = A.limpar_planos(parsed, self.TEXTO)
        self.assertEqual([p["plano"] for p in planos], ["Individual", "Família"])
        ind, fam = planos
        self.assertEqual((ind["mensal"], ind["anual"], ind["anual_por_mes"], ind["anual_recusado"]), (23.9, 239.0, False, False))
        self.assertEqual((fam["mensal"], fam["anual"], fam["anual_recusado"], fam["trecho_anual"]), (40.9, 0.0, True, ""))
        self.assertEqual(recusados, 3, "o anual da Família, o inventado e o sem moeda")

    def test_anual_por_mes_e_moeda_pelo_trecho(self):
        texto = "Pro: $20 per month\nAnnual: $17 per month billed yearly"
        planos, _ = A.limpar_planos([{"plano": "Pro", "mensal": 20, "trecho_mensal": "$20 per month", "anual_por_mes": 17, "trecho_anual": "$17 per month billed yearly"}], texto)
        self.assertEqual((planos[0]["moeda"], planos[0]["anual"], planos[0]["anual_por_mes"]), ("USD", 204.0, True))

    def test_junta_cartao_mensal_e_cartao_anual(self):
        texto = "Mensal: US$ 6.50 por mês\nAnual: US$ 65.00 por ano"
        parsed = [{"plano": "Mensal", "moeda": "USD", "mensal": 6.5, "trecho_mensal": "US$ 6.50 por mês"},
                  {"plano": "Anual", "moeda": "USD", "mensal": 0, "anual_total": 65, "trecho_anual": "US$ 65.00 por ano"}]
        planos, recusados = A.limpar_planos(parsed, texto)
        self.assertEqual(len(planos), 1)
        self.assertEqual((planos[0]["plano"], planos[0]["mensal"], planos[0]["anual"]), ("Mensal", 6.5, 65.0))
        self.assertEqual(recusados, 0)

    def test_no_maximo_16_e_nomes_curtos(self):
        parsed = {"planos": [{"plano": "x" * 100, "moeda": "BRL", "mensal": 23.9, "trecho_mensal": "R$ 23,90 por mês"}] * 20}
        planos, _ = A.limpar_planos(parsed, self.TEXTO)
        self.assertEqual(len(planos), 16)
        self.assertEqual(len(planos[0]["plano"]), 60)
        self.assertEqual(A.limpar_planos(None, "")[0], [])

    def test_prompt(self):
        p = A.prompt(A.POR_ID["spotify"], "R$ 23,90")
        self.assertIn("Spotify Premium (https://www.spotify.com/br-pt/premium/)", p)
        self.assertIn("<<<\nR$ 23,90\n>>>", p)
        self.assertIn('{"planos":[{"plano":"","moeda":"BRL"', p)


class TestAvaliar(unittest.TestCase):
    BRL = {"plano": "Individual", "moeda": "BRL", "mensal": 23.9, "anual": 239.0, "anual_por_mes": False, "trecho_mensal": "a", "trecho_anual": "b", "anual_recusado": False}
    USD = {"plano": "Monthly", "moeda": "USD", "mensal": 6.5, "anual": 65.0, "anual_por_mes": False, "trecho_mensal": "c", "trecho_anual": "d", "anual_recusado": False}

    def test_casar(self):
        self.assertEqual(A.casar(23.9, [self.BRL], None), (self.BRL, None))
        self.assertEqual(A.casar(30, [self.BRL], None), (None, "plano_nao_bate"))
        self.assertEqual(A.casar(6.5 * 5.0 * 1.08, [self.USD], 5.0), (self.USD, None), "dólar com IOF e spread")
        self.assertEqual(A.casar(40, [self.USD], None), (None, "plano_nao_bate"), "sem dólar não dá para comparar")
        outro = dict(self.BRL, plano="Outro", anual=200.0)
        self.assertEqual(A.casar(23.9, [self.BRL, outro], None), (None, "ambiguo"))
        mesmo = dict(self.BRL, plano="Igual")
        self.assertEqual(A.casar(23.9, [self.BRL, mesmo], None)[1], None, "mesmo preço e mesmo anual: tanto faz")
        self.assertEqual(A.casar(10, [dict(self.BRL, mensal=0), dict(self.BRL, moeda="EUR")], 5), (None, "plano_nao_bate"))

    def test_economia(self):
        r = A.avaliar(23.9, {"status": "ok", "planos": [self.BRL]}, None)
        self.assertEqual((r["status"], r["pct"], r["economia_ano"], r["preco_anual"], r["estimado"]), ("ok", 16.7, 47.8, 239.0, False))
        u = A.avaliar(35.1, {"status": "ok", "planos": [self.USD]}, 5.0)
        self.assertEqual((u["status"], u["estimado"], u["preco_anual"]), ("ok", True, round(12 * 35.1 * (65 / 78), 2)))

    def test_status(self):
        self.assertEqual(A.avaliar(10, None, 5), {"status": "pendente"})
        self.assertEqual(A.avaliar(10, {"status": "sem_acesso"}, 5), {"status": "sem_acesso"})
        self.assertEqual(A.avaliar(10, {"planos": []}, 5), {"status": "erro"})
        self.assertEqual(A.avaliar(35, {"status": "ok", "planos": [self.USD]}, None), {"status": "sem_dolar"})
        self.assertEqual(A.avaliar(23.9, {"status": "ok", "planos": [dict(self.BRL, anual=0.0)]}, None)["status"], "sem_anual")
        self.assertEqual(A.avaliar(23.9, {"status": "ok", "planos": [dict(self.BRL, anual=0.0, anual_recusado=True)]}, None)["status"], "nao_confere")
        r = A.avaliar(23.9, {"status": "ok", "planos": [dict(self.BRL, anual=280.0)]}, None)
        self.assertEqual((r["status"], r["pct"]), ("sem_vantagem", 2.4))
        self.assertEqual(A.avaliar(2.0, {"status": "ok", "planos": [dict(self.BRL, mensal=2.0, anual=20.0)]}, None)["status"], "sem_vantagem", "menos de R$ 10 por ano")

    def test_todo_status_tem_texto(self):
        for s in ("pendente", "ok", "sem_dolar", "plano_nao_bate", "ambiguo", "sem_anual", "sem_vantagem", "nao_confere", "erro"):
            self.assertTrue(A.TEXTOS[s].endswith((".", "…")), s)


if __name__ == "__main__":
    unittest.main()
