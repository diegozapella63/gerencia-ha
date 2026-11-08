"""Benefícios lidos pela IA (beneficios.py e o beneficios_ler do server.py): o trecho conferido na página e no texto, o
número que precisa estar no trecho (em algarismos ou por extenso), a moeda, os repetidos, de onde vem (fixo ou conta,
com o nível e o cartão), o pedido à IA e a rota, com a IA simulada e páginas de mentira. Dados inventados (Banco Azul,
Plano Sol)."""
import base64
import os
import unittest
from unittest import mock

from tests.base import ServidorFalso, Servidor, importar_servidor
from tests.test_avisos import Trocar
S = importar_servidor()
import beneficios as B  # noqa: E402  (o importar_servidor põe gerencia/app no caminho)

PAGINA = """<html><head><title>Cartão Azul Black</title><script>var x = "10 acessos";</script></head><body>
<h1>Benefícios do cartão Azul Black</h1><ul>
<li>6 acessos à sala VIP por ano, com 1 acompanhante</li>
<li>US$ 100 em créditos de uso por mês no app parceiro</li>
<li>Seguro viagem internacional para toda a família</li>
<li>Anuidade de R$ 1.200,00</li></ul></body></html>"""
JPG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 64).decode()
D = {"recorrencias": [{"id": "r-sol", "descricao": "Plano Sol"}],
     "bancos": [{"id": "b1", "nome": "Banco Azul", "contas": [{"id": "k1", "pessoa": "Ana", "nivel": "Prime", "cartao": True, "cartao_nivel": "Black"},
                                                               {"id": "k2", "pessoa": "Beto"}]}]}


class TestLimpar(unittest.TestCase):
    TEXTO = "6 acessos à sala VIP por ano, com 1 acompanhante\nSeis entradas no lounge\nUS$ 100 em créditos de uso por mês\nCashback de 1%"

    def test_so_fica_o_que_esta_escrito(self):
        itens, recusados = B.limpar({"beneficios": [
            {"nome": "Sala VIP", "tipo": "contagem", "total": 6, "renova": "ano", "condicao": "com 1 acompanhante", "trecho": "6 acessos à sala VIP por ano"},
            {"nome": "Milhas", "tipo": "vantagem", "trecho": "milhas em dobro"},  # não está no texto
            {"nome": "Créditos", "tipo": "saldo", "total": "100", "moeda": "", "renova": "mes", "trecho": "US$ 100 em créditos de uso por mês"}]}, self.TEXTO)
        self.assertEqual(recusados, 1)
        self.assertEqual(itens, [
            {"nome": "Sala VIP", "tipo": "contagem", "renova": "ano", "trecho": "6 acessos à sala VIP por ano", "total": 6.0, "obs": "com 1 acompanhante"},
            {"nome": "Créditos", "tipo": "saldo", "renova": "mes", "trecho": "US$ 100 em créditos de uso por mês", "total": 100.0, "moeda": "USD"}])

    def test_o_numero_precisa_estar_no_trecho(self):
        itens, _ = B.limpar({"beneficios": [
            {"nome": "Sala VIP", "tipo": "contagem", "total": 8, "renova": "ano", "trecho": "6 acessos à sala VIP por ano"},
            {"nome": "Lounge", "tipo": "contagem", "total": 6, "renova": "ano", "trecho": "Seis entradas no lounge"},
            {"nome": "Cashback", "tipo": "saldo", "total": 0, "renova": "mes", "trecho": "Cashback de 1%"}]}, self.TEXTO)
        self.assertEqual([(i["nome"], i["tipo"], i.get("total"), i["renova"]) for i in itens],
                         [("Sala VIP", "vantagem", None, "nunca"), ("Lounge", "contagem", 6.0, "ano"), ("Cashback", "vantagem", None, "nunca")],
                         "8 não está no trecho: fica a vantagem, sem o número; seis por extenso vale")

    def test_sem_texto_para_conferir_e_repetidos(self):
        itens, recusados = B.limpar({"beneficios": [
            {"nome": "Sala VIP", "tipo": "contagem", "total": 4, "renova": "ano", "trecho": ""},
            {"nome": "sala  vip", "tipo": "contagem", "total": 4, "renova": "ano", "trecho": ""},
            {"nome": "Bônus", "tipo": "saldo", "total": 50, "moeda": "EUR", "renova": "xx", "trecho": "R$ 50 de bônus"},
            {"nome": "", "tipo": "vantagem"}, "lixo"]})
        self.assertEqual(recusados, 0, "do print não há texto para conferir")
        self.assertEqual([(i["nome"], i["tipo"], i.get("total"), i.get("moeda"), i["renova"]) for i in itens],
                         [("Sala VIP", "contagem", 4.0, None, "ano"), ("Bônus", "saldo", 50.0, "BRL", "nunca")])
        self.assertEqual(len(B.limpar({"beneficios": [{"nome": f"Vantagem {k}", "tipo": "vantagem"} for k in range(30)]})[0]), B.MAX)

    def test_moeda_pelo_trecho(self):
        self.assertEqual(B._moeda("", "$20 in credits"), "USD")
        self.assertEqual(B._moeda("", "R$ 20 de crédito"), "BRL")
        self.assertEqual(B._moeda("usd", "R$ 20"), "USD")
        self.assertEqual(B._moeda("", "20 créditos"), "BRL")


class TestOrigemEPedido(unittest.TestCase):
    def test_de_onde_vem(self):
        self.assertEqual(B.nome_origem(D, "fixo:r-sol"), "Plano Sol")
        self.assertEqual(B.nome_origem(D, "conta:k1"), "Banco Azul, nível Prime, cartão Black")
        self.assertEqual(B.nome_origem(D, "conta:k2"), "Banco Azul")
        self.assertEqual((B.nome_origem(D, "conta:x"), B.nome_origem(D, "fixo:x"), B.nome_origem(D, "")), ("", "", ""))

    def test_pedido_a_ia(self):
        p = B.prompt("Banco Azul, cartão Black", "https://exemplo.com/black", "trecho da página")
        self.assertIn("Você lê a página https://exemplo.com/black (de: Banco Azul, cartão Black)", p)
        self.assertIn("fique só com os de Banco Azul, cartão Black", p)
        self.assertIn("Use só o que estiver escrito na página", p)
        self.assertTrue(p.endswith("Trechos da página:\n<<<\ntrecho da página\n>>>"))
        a = B.prompt("", anexo=True)
        self.assertIn("Você lê a imagem ou o PDF anexado e lista", a)
        self.assertNotIn("fique só", a)
        self.assertTrue(a.endswith("]}"), "sem texto, o pedido acaba no formato")

    def test_trechos_da_pagina(self):
        texto = "Menu\n" + "Abra sua conta. " * 400 + "\n6 acessos à sala VIP por ano\n" + "Rodapé. " * 400
        t = B.trechos(texto)
        self.assertIn("sala VIP", t)
        self.assertLess(len(t), 1000)
        self.assertEqual(B.trechos("Nada aqui"), "Nada aqui", "sem nenhuma palavra de benefício, vai o começo do texto")

    def test_ia_simulada(self):
        r = B.simulados(B.EXEMPLO_ANEXO + "\nFrete grátis\nCashback de 1%\nOutra coisa")
        self.assertEqual([(b["nome"], b["tipo"], b["total"], b["renova"]) for b in r["beneficios"]],
                         [("Sala VIP", "contagem", 6, "ano"), ("Créditos de uso", "saldo", 100.0, "mes"), ("Seguro viagem", "vantagem", 0, "nunca"),
                          ("Frete grátis", "vantagem", 0, "nunca"), ("Cashback", "vantagem", 0, "nunca")])


class TestLerNoServidor(unittest.TestCase):
    def setUp(self):
        if os.path.exists(S.ARQ):
            os.remove(S.ARQ)
        self.falso = ServidorFalso({"/black": (200, PAGINA), "/vazia": (200, "<html><body><div id=app></div></body></html>")})
        self.addCleanup(self.falso.fechar)
        Trocar(self, IA_MOCK=True)

    def salvar(self, **aj):
        with S.TRAVA:
            d = S.ler()
            d.update({k: v for k, v in D.items()})
            d["ajustes"].update(aj)
            S.salvar(d, versao=False)

    def test_pagina(self):
        self.salvar()
        r = S.beneficios_ler({"origem": "conta:k1", "texto": self.falso.url + "/black"})
        self.assertEqual([(b["nome"], b["tipo"], b.get("total"), b.get("moeda"), b["renova"], b.get("obs")) for b in r["beneficios"]],
                         [("Sala VIP", "contagem", 6.0, None, "ano", "com 1 acompanhante"), ("Créditos de uso", "saldo", 100.0, "USD", "mes", None),
                          ("Seguro viagem", "vantagem", None, None, "nunca", None)])
        self.assertEqual((r["origem"], r["recusados"]), ("conta:k1", 0))

    def test_o_que_a_pagina_nao_confirma(self):
        self.salvar()
        with mock.patch.object(B, "simulados", return_value={"beneficios": [{"nome": "Milhas", "tipo": "vantagem", "trecho": "milhas em dobro"}]}):
            with self.assertRaisesRegex(ValueError, "A IA citou benefícios que não estão escritos na página"):
                S.beneficios_ler({"texto": self.falso.url + "/black"})

    def test_texto_imagem_e_erros(self):
        self.salvar()
        r = S.beneficios_ler({"texto": "Frete grátis\nCashback de 2% nas compras"})
        self.assertEqual([b["nome"] for b in r["beneficios"]], ["Frete grátis", "Cashback"])
        r = S.beneficios_ler({"anexo": {"b64": "data:image/jpeg;base64," + JPG}})
        self.assertEqual([b["nome"] for b in r["beneficios"]], ["Sala VIP", "Créditos de uso", "Seguro viagem"])
        casos = [({}, "Envie um print"), ({"texto": "Nada que sirva"}, "A IA não achou benefícios aqui."),
                 ({"texto": self.falso.url + "/nao-existe"}, "Não deu para abrir a página"),
                 ({"texto": self.falso.url + "/vazia"}, "A página não mostrou o texto"),
                 ({"texto": "file:///data/senhas_pdf.json"}, "Cole um endereço que comece com https://."),
                 ({"anexo": {"b64": base64.b64encode(b"texto qualquer").decode()}}, "Envie uma imagem")]
        for corpo, msg in casos:
            with self.subTest(corpo=corpo), self.assertRaisesRegex(ValueError, msg):
                S.beneficios_ler(corpo)
        self.salvar(ia=False)
        with self.assertRaisesRegex(ValueError, "A IA está desligada"):
            S.beneficios_ler({"texto": "Frete grátis"})

    def test_endereco_sem_https(self):
        self.salvar()
        abertos = []

        def abrir(url, *a, **k):
            abertos.append(url)
            raise OSError("fora")
        with mock.patch.object(S, "_abrir_url", side_effect=abrir), self.assertRaises(ValueError):
            S.beneficios_ler({"texto": "www.bancoazul.exemplo/black"})
        self.assertEqual(abertos, ["https://www.bancoazul.exemplo/black"])


class TestRota(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Servidor()

    @classmethod
    def tearDownClass(cls):
        cls.srv.parar()

    def test_ler(self):
        st, _, r = self.srv.post("/api/beneficios/ler", {"texto": "6 acessos à sala VIP por ano"})
        self.assertEqual((st, [b["nome"] for b in r["beneficios"]]), (200, ["Sala VIP"]))
        st, _, r = self.srv.post("/api/beneficios/ler", {})
        self.assertEqual((st, r["erro"]), (400, "Envie um print, uma foto ou um PDF, ou cole o texto ou o endereço da página."))
        st, _, r = self.srv.get("/api/ia/uso")
        self.assertEqual(st, 200)
        self.assertIn("beneficios", str(r), "conta no Uso da IA")


if __name__ == "__main__":
    unittest.main()
