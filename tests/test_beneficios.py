"""Benefícios lidos pela IA (beneficios.py e o beneficios_ler do server.py): o trecho conferido na página e no texto, o
número que precisa estar no trecho (em algarismos ou por extenso), a moeda, os repetidos, de onde vem (fixo ou conta,
com o nível e o cartão), o pedido à IA e a rota, com a IA simulada e páginas de mentira. Dados inventados (Banco Azul,
Plano Sol)."""
import base64
import os
import json
import unittest
from unittest import mock

from tests.base import ServidorFalso, Servidor, importar_servidor, pasta_temp
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
        d = json.loads(json.dumps(D))
        next(c for bc in d["bancos"] for c in bc["contas"] if c["id"] == "k2").update(debito_global="USD", credito_global="EUR")
        self.assertEqual(B.nome_origem(d, "conta:k2"), "Banco Azul, cartão de débito global em USD, cartão de crédito global em EUR", "1.62.0")
        self.assertEqual((B.nome_origem(D, "conta:x"), B.nome_origem(D, "fixo:x"), B.nome_origem(D, "")), ("", "", ""))

    def test_pedido_a_ia(self):
        p = B.prompt("Banco Azul, cartão Black", "https://exemplo.com/black", "trecho da página")
        self.assertIn("Você lê a página https://exemplo.com/black (de: Banco Azul, cartão Black)", p)
        self.assertIn("os benefícios são só os de Banco Azul, cartão Black; os outros, mais caros, entram em \"oportunidades\"", p)
        self.assertIn("A pessoa paga hoje R$ 110,00 por mês: num \"plano\", só os que custam mais que isso.", B.prompt("Plano Sol", preco=110))
        self.assertIn("Use só o que estiver escrito na página", p)
        self.assertTrue(p.endswith("Trechos da página:\n<<<\ntrecho da página\n>>>"))
        a = B.prompt("", anexo=True)
        self.assertIn("Você lê a imagem ou o PDF anexado e lista", a)
        self.assertNotIn("só os de", a)
        self.assertTrue(a.endswith("]}"), "sem texto, o pedido acaba no formato")

    def test_o_que_e_e_o_site(self):
        """1.75.0: cada benefício diz o que é (a IA pode usar o que sabe) e o site oficial (só https)."""
        self.assertEqual(B.sobre({"descricao": " Clube  de restaurantes ", "site": "https://clube.exemplo.com/x"}),
                         {"descricao": "Clube de restaurantes", "url": "https://clube.exemplo.com/x"})
        self.assertEqual((B.sobre({"site": "http://x.com"}), B.sobre({"site": "javascript:alert(1)"}), B.sobre(None), B.sobre({"url": "https://a.exemplo.com"})),
                         ({}, {}, {}, {"url": "https://a.exemplo.com"}))
        self.assertEqual(B.sobre({"descricao": "x" * 300})["descricao"], "x" * 200)
        p = B.prompt("Banco Azul", "", "texto")
        self.assertIn('"descricao": o que é e para que serve', p)
        self.assertIn('Não use o que você sabe de memória (só na "descricao" e no "site")', p)
        self.assertIn('"descricao":"","site":""', p)
        self.assertIn('Use o que você sabe de Banco Azul', B.prompt("Banco Azul", memoria=True), "a regra continua trocada na memória")
        e = B.prompt_explicar("Clube Sabor", "Banco Azul, nível Prime")
        self.assertTrue(e.startswith('Explique, para quem nunca ouviu falar, o benefício "Clube Sabor" (de Banco Azul, nível Prime)'))
        self.assertTrue(e.endswith('{"descricao":"","site":""}'))
        self.assertEqual(B.explicado_simulado(" Clube Sabor ")["descricao"], "Clube Sabor: benefício de exemplo, explicado pela IA simulada.")
        it, _ = B.limpar({"beneficios": [{"nome": "Clube Sabor", "tipo": "vantagem", "trecho": "", "descricao": "Dois pratos pelo preço de um", "site": "https://clube.exemplo.com"}]})
        self.assertEqual((it[0]["descricao"], it[0]["url"]), ("Dois pratos pelo preço de um", "https://clube.exemplo.com"))

    def test_limpar_proximo(self):
        lp = B.limpar_proximo
        self.assertEqual(lp({"proximo_nivel": {"nivel": " Black ", "valor": "100.000", "trecho": ""}}), {"nivel": "Black", "valor": 100000, "trecho": ""})
        self.assertIsNone(lp({"proximo_nivel": {"nivel": "Black", "valor": 0}}))
        self.assertIsNone(lp({"proximo_nivel": {"nivel": "", "valor": 5}}))
        self.assertIsNone(lp({"proximo_nivel": "Black"}))
        self.assertIsNone(lp([]))
        self.assertIsNone(lp({"proximo_nivel": {"nivel": "Black", "valor": 100000, "trecho": "Black com R$ 90 mil"}}), "o valor precisa estar no trecho")
        self.assertIsNone(lp({"proximo_nivel": {"nivel": "Black", "valor": 100000, "trecho": "R$ 100 mil"}}, "outro texto"), "e o trecho no texto")
        self.assertIsNotNone(lp({"proximo_nivel": {"nivel": "Black", "valor": 100000, "trecho": "R$ 100 mil"}}, "Black com R$ 100 mil investidos"))
        self.assertIn("\"proximo_nivel\":{\"nivel\":\"\",\"valor\":0,\"trecho\":\"\"}", B.prompt("Banco Azul", "", "x", conta=True))
        self.assertNotIn("proximo_nivel", B.prompt("Plano Sol", "", "x"))

    def test_pedido_so_com_o_banco_e_o_nivel(self):
        """1.74.0: sem print, texto nem página, o que a IA sabe do banco e do nível da pessoa (a tela pede para conferir)."""
        p = B.prompt("Banco Azul, nível Prime, cartão Black", memoria=True)
        self.assertTrue(p.startswith("Você conhece os bancos, os cartões e os planos do Brasil. Liste os benefícios que a pessoa ganha com Banco Azul, nível Prime, cartão Black:"))
        self.assertIn("Use o que você sabe de Banco Azul, nível Prime, cartão Black", p)
        self.assertIn("os de um nível acima entram em \"oportunidades\"", p)
        self.assertNotIn("Não use o que você sabe de memória", p)
        self.assertNotIn("Você lê", p)
        self.assertTrue(p.endswith("]}"), "nada depois do formato")

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


class TestOportunidades(unittest.TestCase):
    """1.54: na mesma leitura, o que a pessoa ganha a mais cumprindo uma condição (investindo, gastando no cartão, um plano
    mais caro), conferido como os benefícios: o trecho escrito lá e o valor no trecho. Bancos e planos inventados."""
    TEXTO = ("Anuidade grátis com R$ 50 mil investidos\nSala VIP gastando R$ 3.000 por mês no cartão\n"
             "Plano Família por R$ 34,99 por mês, até 5 pessoas\nCashback de 1%")

    def test_o_valor_em_algarismos_ou_com_mil(self):
        for trecho, valor, ok in (("com R$ 50 mil investidos", 50000, True), ("R$ 50.000,00 investidos", 50000, True), ("R$ 1,5 mil", 1500, True),
                                  ("com R$ 50 mil investidos", 5000, False), ("Plano por R$ 34,99", 34.99, True), ("sem número", 10, False)):
            with self.subTest(trecho=trecho, valor=valor):
                self.assertEqual(B.tem_valor(trecho, valor), ok)

    def test_limpar_so_o_escrito_e_com_o_valor_no_trecho(self):
        ia = {"oportunidades": [
            {"tipo": "investido", "valor": 50000, "periodo": "mes", "ganha": "Sem anuidade", "trecho": "Anuidade grátis com R$ 50 mil investidos"},
            {"tipo": "gasto", "valor": "3.000", "periodo": "mes", "ganha": "Sala VIP", "trecho": "Sala VIP gastando R$ 3.000 por mês"},
            {"tipo": "plano", "valor": 34.99, "periodo": "mes", "ganha": "Até 5 pessoas", "plano": "Família", "trecho": "Plano Família por R$ 34,99 por mês"},
            {"tipo": "gasto", "valor": 5000, "ganha": "Milhas em dobro", "trecho": "milhas em dobro gastando R$ 5 mil"},  # não está no texto
            {"tipo": "investido", "valor": 80000, "ganha": "Nível Black", "trecho": "Anuidade grátis com R$ 50 mil investidos"},  # o valor não está no trecho
            {"tipo": "investido", "valor": 50000, "ganha": "Sem anuidade", "trecho": "Anuidade grátis com R$ 50 mil investidos"},  # repetida
            {"tipo": "outro", "valor": 1, "ganha": "x"}, {"tipo": "gasto", "valor": 0, "ganha": "Zero"}, {"tipo": "gasto", "valor": 10, "ganha": ""}, "lixo"]}
        metas, recusadas = B.limpar_metas(ia, self.TEXTO)
        self.assertEqual(metas, [
            {"tipo": "investido", "valor": 50000.0, "ganha": "Sem anuidade", "trecho": "Anuidade grátis com R$ 50 mil investidos"},
            {"tipo": "gasto", "valor": 3000.0, "ganha": "Sala VIP", "trecho": "Sala VIP gastando R$ 3.000 por mês", "periodo": "mes"},
            {"tipo": "plano", "valor": 34.99, "ganha": "Até 5 pessoas", "trecho": "Plano Família por R$ 34,99 por mês", "periodo": "mes", "plano": "Família"}])
        self.assertEqual(recusadas, 2)
        self.assertEqual(B.limpar_metas({"oportunidades": [{"tipo": "gasto", "valor": 3, "ganha": "Algo", "periodo": "ano"}]})[0][0]["periodo"], "ano",
                         "do print não há texto para conferir")
        self.assertEqual(B.limpar_metas({"beneficios": []}), ([], 0))
        self.assertEqual(B.limpar_metas([]), ([], 0))

    def test_pedido_e_ia_simulada(self):
        self.assertIn('"oportunidades"', B.prompt("Banco Azul"))
        r = B.simulados(self.TEXTO + "\nPlano Premium por R$ 1.200 por ano")
        self.assertEqual([b["nome"] for b in r["beneficios"]], ["Cashback"], "as condições não são benefícios")
        self.assertEqual([(m["tipo"], m["valor"], m["ganha"], m["periodo"]) for m in r["oportunidades"]],
                         [("investido", 50000, "Sem anuidade", ""), ("gasto", 3000, "Sala VIP", "mes"),
                          ("plano", 34.99, "Plano Família", "mes"), ("plano", 1200, "Plano Premium", "ano")])


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
        self.assertEqual(r["oportunidades"], [], "a página não tem condição para ganhar mais")

    def test_so_oportunidades(self):
        self.salvar()
        r = S.beneficios_ler({"origem": "conta:k1", "texto": "Anuidade grátis com R$ 50 mil investidos"})
        self.assertEqual((r["beneficios"], [(m["tipo"], m["valor"], m["ganha"]) for m in r["oportunidades"]]), ([], [("investido", 50000, "Sem anuidade")]))
        with mock.patch.object(B, "simulados", return_value={"oportunidades": [{"tipo": "gasto", "valor": 5000, "ganha": "Milhas", "trecho": "milhas em dobro"}]}):
            with self.assertRaisesRegex(ValueError, "não estão escritos no texto"):
                S.beneficios_ler({"texto": "Anuidade grátis com R$ 50 mil investidos"})

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
        casos = [({}, "Envie um print"), ({"texto": "Nada que sirva"}, "A IA não achou benefícios nem oportunidades aqui."),
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

    def test_so_a_conta(self):
        """1.74.0: só a conta (o banco e o nível), sem nada para ler: o que a IA sabe, marcado para conferir; o número fica."""
        self.salvar()
        r = S.beneficios_ler({"origem": "conta:k1"})
        self.assertTrue(r["memoria"])
        self.assertEqual([(b["nome"], b["tipo"], b.get("total"), b["renova"]) for b in r["beneficios"]],
                         [("Cashback", "vantagem", None, "nunca"), ("Sala VIP", "contagem", 2, "ano"), ("Seguro viagem", "vantagem", None, "nunca")])
        self.assertEqual(r["oportunidades"], [])
        self.assertEqual((r["proximo"]["nivel"], r["proximo"]["valor"]), ("Ouro", 250000), "1.74.2: o próximo nível da conta e quanto pede")
        self.assertNotIn("memoria", S.beneficios_ler({"origem": "conta:k1", "texto": "Frete grátis"}), "com texto, como antes")
        with self.assertRaisesRegex(ValueError, "Envie um print"):
            S.beneficios_ler({"origem": "conta:nao-existe"})
        with mock.patch.object(B, "simulados", return_value={"beneficios": []}), \
                self.assertRaisesRegex(ValueError, "A IA não sabe os benefícios de Banco Azul, nível Prime, cartão Black. Mande um print"):
            S.beneficios_ler({"origem": "conta:k1"})

    def test_proximo_nivel(self):
        """1.74.2: numa conta, o nível logo acima e quanto pede investido; do texto, só se estiver escrito, com o valor no
        trecho; a mesma condição não vem de novo como oportunidade; num fixo, não vem."""
        self.salvar()
        t = "Sala VIP liberada\nPróximo nível: Ouro, a partir de R$ 100 mil investidos"
        r = S.beneficios_ler({"origem": "conta:k1", "texto": t})
        self.assertEqual(r["proximo"], {"nivel": "Ouro", "valor": 100000, "trecho": "Próximo nível: Ouro, a partir de R$ 100 mil investidos"})
        self.assertNotIn("proximo", S.beneficios_ler({"origem": "fixo:r-sol", "texto": t}))
        r = S.beneficios_ler({"origem": "conta:k1", "texto": "Próximo nível: Ouro, a partir de R$ 100 mil investidos"})
        self.assertEqual((r["beneficios"], r["oportunidades"], r["proximo"]["nivel"]), ([], [], "Ouro"), "só o próximo nível já basta")
        falso = {"beneficios": [], "proximo_nivel": {"nivel": "Ouro", "valor": 100000, "trecho": "Ouro com R$ 90 mil"},
                 "oportunidades": [{"tipo": "investido", "valor": 100000, "ganha": "Nível Ouro", "trecho": "a partir de R$ 100 mil investidos"}]}
        with mock.patch.object(B, "simulados", return_value=falso):
            r = S.beneficios_ler({"origem": "conta:k1", "texto": "Ouro: a partir de R$ 100 mil investidos"})
        self.assertNotIn("proximo", r, "o trecho não está no texto")
        falso["proximo_nivel"]["trecho"] = "a partir de R$ 100 mil investidos"
        with mock.patch.object(B, "simulados", return_value=falso):
            r = S.beneficios_ler({"origem": "conta:k1", "texto": "Ouro: a partir de R$ 100 mil investidos"})
        self.assertEqual((r["proximo"]["nivel"], r["oportunidades"]), ("Ouro", []), "a mesma condição não vira oportunidade")

    def test_o_nivel_que_ja_tem_nao_e_oportunidade(self):
        """1.74.3: a conta já é Prime (cartão Black): "Inter Prime com R$ 150 mil investidos" é o que ela já tem, não
        oportunidade; nem o próximo nível igual ao de agora. Outra condição continua."""
        self.salvar()
        falso = {"beneficios": [], "proximo_nivel": {"nivel": "Prime", "valor": 50000, "trecho": ""},
                 "oportunidades": [{"tipo": "investido", "valor": 150000, "ganha": "Banco Azul Prime", "trecho": ""},
                                   {"tipo": "gasto", "valor": 7000, "periodo": "mes", "ganha": "Prime", "trecho": ""},
                                   {"tipo": "gasto", "valor": 9000, "periodo": "mes", "ganha": "Cartão Black", "trecho": ""},
                                   {"tipo": "gasto", "valor": 15000, "periodo": "mes", "ganha": "Salas VIP", "trecho": ""},
                                   {"tipo": "investido", "valor": 500000, "ganha": "Nível Primeira Classe", "trecho": ""}]}
        with mock.patch.object(B, "simulados", return_value=falso):
            r = S.beneficios_ler({"origem": "conta:k1"})
        self.assertEqual([m["ganha"] for m in r["oportunidades"]], ["Salas VIP", "Nível Primeira Classe"])
        self.assertNotIn("proximo", r)
        self.assertEqual(B.niveis_da_conta(D, "conta:k1"), ["Prime", "Black"])
        self.assertEqual(B.niveis_da_conta(D, "conta:k1", so_conta=True), ["Prime"], "o próximo nível compara só com o da conta")
        self.assertEqual((B.niveis_da_conta(D, "conta:k2"), B.niveis_da_conta(D, "fixo:r-sol"), B.niveis_da_conta(D, "conta:x")), ([], [], []))
        self.assertIn("nem o que vale para o nível que ela já tem", B.prompt("Banco Azul, nível Prime", conta=True, memoria=True))

    def test_explicar(self):
        """1.75.0: Explicar com IA (no formulário): o que é um benefício já cadastrado."""
        self.salvar()
        self.assertEqual(S.beneficios_explicar({"nome": "Clube Sabor", "origem": "conta:k1"}), {"descricao": "Clube Sabor: benefício de exemplo, explicado pela IA simulada."})
        with self.assertRaisesRegex(ValueError, "Dê um nome"):
            S.beneficios_explicar({"nome": " "})
        with mock.patch.object(B, "explicado_simulado", return_value={"descricao": ""}), self.assertRaisesRegex(ValueError, "A IA não sabe o que é Clube Sabor"):
            S.beneficios_explicar({"nome": "Clube Sabor"})
        self.salvar(ia=False)
        with self.assertRaisesRegex(ValueError, "A IA está desligada"):
            S.beneficios_explicar({"nome": "Clube Sabor"})

    def test_endereco_sem_https(self):
        self.salvar()
        abertos = []

        def abrir(url, *a, **k):
            abertos.append(url)
            raise OSError("fora")
        with mock.patch.object(S, "_abrir_url", side_effect=abrir), self.assertRaises(ValueError):
            S.beneficios_ler({"texto": "www.bancoazul.exemplo/black"})
        self.assertEqual(abertos, ["https://www.bancoazul.exemplo/black"])


class TestIaDeVerdade(unittest.TestCase):
    """Fora da IA simulada: os anexos vão pela pasta media do Home Assistant (e são apagados depois), a entidade escolhida
    vai no pedido, e uma IA que não aceita PDF recebe o texto tirado do arquivo."""

    def setUp(self):
        if os.path.exists(S.ARQ):
            os.remove(S.ARQ)
        self.media = pasta_temp()
        Trocar(self, IA_MOCK=False, MEDIA_ROOT=self.media, ia_disponivel=lambda d: True)
        self.pedidos = []
        with S.TRAVA:
            d = S.ler()
            d.update({k: v for k, v in D.items()})
            d["ajustes"]["ia_entidade"] = "ai_task.claude"
            S.salvar(d, versao=False)

    def ia(self, *respostas):
        """ia_chamar falso: guarda o pedido (e os arquivos que estavam na pasta) e devolve as respostas na ordem."""
        fila = list(respostas)

        def chamar(tipo, payload, n, timeout=None):
            pasta = os.path.join(self.media, S.IA_TMP_REL)
            self.pedidos.append((tipo, payload, n, sorted(os.listdir(pasta)) if os.path.isdir(pasta) else []))
            r = fila.pop(0)
            if isinstance(r, Exception):
                raise r
            return {"service_response": {"data": r}}
        Trocar(self, ia_chamar=chamar)

    def test_print_vai_pela_pasta_media_e_e_apagado(self):
        self.ia({"beneficios": [{"nome": "Sala VIP", "tipo": "contagem", "total": 4, "renova": "ano", "trecho": "4 acessos"}]})
        r = S.beneficios_ler({"origem": "conta:k1", "anexo": {"b64": JPG}})
        self.assertEqual([b["nome"] for b in r["beneficios"]], ["Sala VIP"])
        tipo, payload, n, na_pasta = self.pedidos[0]
        self.assertEqual((tipo, n, payload["entity_id"], payload["task_name"]), ("beneficios", 1, "ai_task.claude", "GerencIA: ler benefícios"))
        self.assertEqual(len(na_pasta), 1, "o print estava na pasta durante a leitura")
        self.assertEqual(payload["attachments"][0]["media_content_type"], "image/jpeg")
        self.assertTrue(payload["attachments"][0]["media_content_id"].startswith("media-source://media_source/local/gerencia/ia-temp/"))
        self.assertEqual(os.listdir(os.path.join(self.media, S.IA_TMP_REL)), [], "e saiu depois")

    def test_assinatura_manda_o_preco_de_agora(self):
        """1.54: lendo os planos de uma assinatura, a IA sabe quanto a pessoa paga, para trazer só os planos mais caros."""
        with S.TRAVA:
            d = S.ler()
            d["recorrencias"] = [{"id": "r-sol", "descricao": "Plano Sol", "valor": 1320, "freq": "anual", "inicio": "2026-01"}]
            S.salvar(d, versao=False)
        self.ia({"beneficios": [], "oportunidades": [{"tipo": "plano", "valor": 130, "periodo": "mes", "ganha": "Mais espaço", "plano": "2 TB",
                                                       "trecho": "2 TB por R$ 130 por mês"}]})
        r = S.beneficios_ler({"origem": "fixo:r-sol", "texto": "Plano Sol 1 TB: R$ 110 por mês. 2 TB por R$ 130 por mês."})
        self.assertEqual([m["plano"] for m in r["oportunidades"]], ["2 TB"])
        self.assertIn("A pessoa paga hoje R$ 110,00 por mês", self.pedidos[0][1]["instructions"], "o anual, por mês")

    def test_apagado_mesmo_quando_a_ia_falha(self):
        self.ia(S.ErroHA("A IA caiu."))
        with self.assertRaisesRegex(ValueError, "A IA caiu."):
            S.beneficios_ler({"anexo": {"b64": JPG}})
        self.assertEqual(os.listdir(os.path.join(self.media, S.IA_TMP_REL)), [])

    def test_ia_que_nao_aceita_pdf_recebe_o_texto(self):
        pdf = base64.b64encode(b"%PDF-1.4 fatura").decode()
        self.ia(S.ErroHA("Formato não aceito."), {"beneficios": [{"nome": "Frete grátis", "tipo": "vantagem", "trecho": "Frete grátis"}]})
        with mock.patch.object(S, "pdf_texto", return_value="Frete grátis em todas as compras"):
            r = S.beneficios_ler({"anexo": {"b64": pdf}})
        self.assertEqual([b["nome"] for b in r["beneficios"]], ["Frete grátis"])
        self.assertEqual([p[2] for p in self.pedidos], [1, 0], "a segunda vez sem anexo")
        self.assertIn("Frete grátis em todas as compras", self.pedidos[1][1]["instructions"])
        self.ia(S.ErroHA("Formato não aceito."), S.ErroHA("De novo não."))
        with mock.patch.object(S, "pdf_texto", return_value="Frete grátis"), self.assertRaisesRegex(ValueError, "De novo não."):
            S.beneficios_ler({"anexo": {"b64": pdf}})
        self.ia(S.ErroHA("Formato não aceito."))
        with mock.patch.object(S, "pdf_texto", return_value=""), self.assertRaisesRegex(ValueError, "Formato não aceito."):
            S.beneficios_ler({"anexo": {"b64": pdf}})

    def test_so_a_conta_vai_pelo_que_a_ia_sabe(self):
        self.ia({"beneficios": [{"nome": "Sala VIP", "tipo": "contagem", "total": 4, "renova": "ano", "trecho": ""}]})
        r = S.beneficios_ler({"origem": "conta:k1"})
        self.assertEqual([(b["nome"], b["total"]) for b in r["beneficios"]], [("Sala VIP", 4)], "sem trecho para conferir, o número fica")
        tipo, payload, n, _ = self.pedidos[0]
        self.assertIn("Use o que você sabe de Banco Azul, nível Prime, cartão Black", payload["instructions"])
        self.assertEqual(n, 0)
        self.assertNotIn("attachments", payload)

    def test_site_so_fica_se_abrir(self):
        """1.75.0: o site que a IA disse só fica se abrir (ela pode inventar o endereço)."""
        abre = {"https://clube.exemplo.com": True, "https://inventado.exemplo.com": False}
        self.ia({"beneficios": [{"nome": "Clube Sabor", "tipo": "vantagem", "trecho": "", "descricao": "Restaurantes", "site": "https://clube.exemplo.com"},
                                {"nome": "Seguro", "tipo": "vantagem", "trecho": "", "descricao": "Viagem", "site": "https://inventado.exemplo.com"}]},
                {"descricao": "Restaurantes", "site": "https://inventado.exemplo.com"}, {"descricao": "Restaurantes", "site": "https://clube.exemplo.com"},
                S.ErroHA("A IA caiu."))
        with mock.patch.object(S, "_site_abre", side_effect=lambda u: abre[u]):
            r = S.beneficios_ler({"origem": "conta:k1"})
            self.assertEqual([b.get("url") for b in r["beneficios"]], ["https://clube.exemplo.com", None])
            self.assertEqual(S.beneficios_explicar({"nome": "Clube Sabor"}), {"descricao": "Restaurantes"})
            self.assertEqual(S.beneficios_explicar({"nome": "Clube Sabor"}), {"descricao": "Restaurantes", "url": "https://clube.exemplo.com"})
            with self.assertRaisesRegex(ValueError, "A IA caiu."):
                S.beneficios_explicar({"nome": "Clube Sabor"})
        self.assertIn('o benefício "Clube Sabor"', self.pedidos[1][1]["instructions"])
        falso = ServidorFalso({"/ok": (200, "<html>ok</html>")})
        self.addCleanup(falso.fechar)
        self.assertEqual((S._site_abre(falso.url + "/ok"), S._site_abre(falso.url + "/nao")), (True, False))
        S._conferir_sites([])
        Trocar(self, ia_disponivel=lambda d: False)
        with self.assertRaisesRegex(ValueError, "Nenhuma IA configurada"):
            S.beneficios_explicar({"nome": "Clube Sabor"})

    def test_texto_vai_sem_anexo_e_sem_resposta_avisa(self):
        self.ia(None)
        with self.assertRaisesRegex(ValueError, "A IA não devolveu resposta"):
            S.beneficios_ler({"texto": "Frete grátis\nCashback de 2%"})
        self.assertNotIn("attachments", self.pedidos[0][1])

    def test_sem_a_pasta_media(self):
        Trocar(self, MEDIA_ROOT=os.path.join(self.media, "nao-existe"))
        self.ia({"beneficios": []})
        with self.assertRaisesRegex(ValueError, "pasta media do Home Assistant não está disponível"):
            S.beneficios_ler({"anexo": {"b64": JPG}})
        self.assertEqual(self.pedidos, [], "nem chamou a IA")

    def test_sem_ia_no_home_assistant(self):
        Trocar(self, ia_disponivel=lambda d: False)
        with self.assertRaisesRegex(ValueError, "Nenhuma IA configurada"):
            S.beneficios_ler({"texto": "Frete grátis"})

    def test_anexos_ruins(self):
        casos = [({"anexo": {"b64": "não é base64!"}}, "Arquivo inválido"),
                 ({"anexos": [{"b64": JPG}, {"b64": base64.b64encode(b"%PDF-1.4 x").decode()}]}, "Envie um PDF por vez")]
        for corpo, msg in casos:
            with self.subTest(msg=msg), self.assertRaisesRegex(ValueError, msg):
                S._anexos(corpo)
        self.assertEqual([m for _, m in S._anexos({"anexos": [{"b64": JPG}, {"b64": JPG}, {}, "lixo"]})], ["image/jpeg", "image/jpeg"])


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
        st, _, r = self.srv.post("/api/beneficios/explicar", {"nome": "Clube Sabor"})
        self.assertEqual((st, r["descricao"]), (200, "Clube Sabor: benefício de exemplo, explicado pela IA simulada."), "1.75.0")
        st, _, r = self.srv.post("/api/beneficios/ler", {})
        self.assertEqual((st, r["erro"]), (400, "Envie um print, uma foto ou um PDF, ou cole o texto ou o endereço da página."))
        st, _, r = self.srv.get("/api/ia/uso")
        self.assertEqual(st, 200)
        self.assertIn("beneficios", str(r), "conta no Uso da IA")


if __name__ == "__main__":
    unittest.main()
