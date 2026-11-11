"""integracao.py: o que o CronologIA lê e faz no GerencIA (contas a pagar, pagar, desfazer, nova) e a chave."""
import json
import os
import re
import stat
import unittest
from datetime import date

from tests.base import pasta_temp
import integracao as I

HOJE = date(2026, 11, 15)


def dados():
    return {
        "categorias": [{"id": "c-casa", "nome": "Casa", "tipo": "despesa"}, {"id": "c-sal", "nome": "Salário", "tipo": "receita"}, {"id": "c-x", "nome": "Sem tipo"}],
        "bancos": [{"id": "b1", "nome": "Banco Azul", "contas": [{"id": "cc", "pessoa": "Ana", "cartao": True, "fechamento": 5, "vencimento": 10}]}],
        "lancamentos": [
            {"id": "l-luz", "tipo": "despesa", "descricao": "Luz", "valor": 180.456, "data": "2026-11-20", "pago": False, "categoria": "c-casa"},
            {"id": "l-agua", "tipo": "despesa", "descricao": "Água", "valor": 90, "data": "2026-11-03", "pago": True},
            {"id": "l-velha", "tipo": "despesa", "descricao": "Atrasada", "valor": 50, "data": "2026-10-01", "pago": False},
            {"id": "l-antiga", "tipo": "despesa", "descricao": "Muito antiga", "valor": 50, "data": "2026-08-01", "pago": False},
            {"id": "l-sal", "tipo": "receita", "descricao": "Salário", "valor": 5000, "data": "2026-11-05", "pago": True},
            {"id": "l-aj", "tipo": "despesa", "descricao": "Ajuste", "valor": 1, "data": "2026-11-06", "ajuste": True},
            {"id": "l-vin", "tipo": "despesa", "descricao": "Pagamento de fatura", "valor": 1, "data": "2026-11-06", "vinculo": "x"},
            {"id": "l-pulado", "tipo": "despesa", "descricao": "Pulado", "valor": 1, "data": "2026-11-06", "pulado": True},
            # cartão: fecha dia 5, vence dia 10
            {"id": "k1", "tipo": "despesa", "descricao": "Mercado", "valor": 100, "data": "2026-11-06", "conta": "cc", "cartao": True, "pago": True},
            {"id": "k2", "tipo": "despesa", "descricao": "Farmácia", "valor": 40, "data": "2026-11-20", "conta": "cc", "cartao": True, "pago": False},
            {"id": "k3", "tipo": "receita", "descricao": "Estorno", "valor": 15, "data": "2026-11-21", "conta": "cc", "cartao": True, "pago": True},
        ],
        "recorrencias": [
            {"id": "r-net", "tipo": "despesa", "descricao": "Internet", "valor": 120, "dia": 25, "inicio": "2026-01", "categoria": "c-casa"},
            {"id": "r-sal", "tipo": "receita", "descricao": "Salário fixo", "valor": 3000, "dia": 5, "inicio": "2026-01"},
            {"descricao": "Sem id", "valor": 1, "dia": 1, "inicio": "2026-01"},
        ],
    }


class TestUtilitarios(unittest.TestCase):
    def test_add_ym(self):
        self.assertEqual(I.add_ym("2026-11", 2), "2027-01")
        self.assertEqual(I.add_ym("2026-01", -1), "2025-12")
        self.assertEqual(I.add_ym("2026-05", 0), "2026-05")
        self.assertEqual(I.add_ym("2026-05", -17), "2024-12")

    def test_uid(self):
        ids = {I.uid() for _ in range(200)}
        self.assertEqual(len(ids), 200)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{8}[0-9a-z]+", x) for x in ids))


class TestConexao(unittest.TestCase):
    def setUp(self):
        self.data, self.share = pasta_temp(), pasta_temp()
        self.logs = []
        self.c = I.Conexao(self.data, self.share, 8099, "9.9.9", lambda *a: self.logs.append(a))
        os.environ.pop("GERENCIA_URL_INTERNA", None)

    def tearDown(self):
        os.environ.pop("GERENCIA_URL_INTERNA", None)

    def test_chave_criada_uma_vez_e_so_para_o_dono(self):
        k = self.c.chave()
        self.assertGreaterEqual(len(k), 32)
        self.assertEqual(stat.S_IMODE(os.stat(self.c.arq_chave).st_mode), 0o600)
        self.assertEqual(I.Conexao(self.data, self.share, 1, "", print).chave(), k, "lida do arquivo")

    def test_chave_curta_e_trocada(self):
        with open(os.path.join(self.data, "integracao.key"), "w") as f:
            f.write("curta")
        self.assertNotEqual(self.c.chave(), "curta")

    def test_endereco(self):
        os.environ["GERENCIA_URL_INTERNA"] = "http://gerencia.local:8099/"
        self.assertEqual(self.c.endereco(), ("http://gerencia.local:8099", None))
        os.environ.pop("GERENCIA_URL_INTERNA")
        url, _ = self.c.endereco()
        self.assertTrue(url.startswith("http://") and url.endswith(":8099"))

    def test_publicar_e_apagar(self):
        os.environ["GERENCIA_URL_INTERNA"] = "http://g:8099"
        self.c.publicar()
        with open(self.c.arq_share, encoding="utf-8") as f:
            p = json.load(f)
        self.assertEqual((p["app"], p["versao"], p["url"], p["chave"]), ("gerencia", "9.9.9", "http://g:8099", self.c.chave()))
        self.assertIsNone(p["ip_url"])
        self.assertRegex(p["gravado_em"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$", "com o fuso, como nos outros apps")
        self.assertEqual(stat.S_IMODE(os.stat(self.c.arq_share).st_mode), 0o600)
        self.c.publicar(ligado=False)
        self.assertFalse(os.path.exists(self.c.arq_share))
        self.c.publicar(ligado=False)  # de novo: nada a apagar

    def test_o_comeco_igual_ao_dos_outros_apps(self):
        """share/<app>/integracao.json começa igual em todos os apps: app (o id), nome, versao e gravado_em."""
        c = I.Conexao(self.data, self.share, 8099, "9.9.9", print, extra={"nome": "GerencIA"})
        c.publicar()
        with open(c.arq_share, encoding="utf-8") as f:
            p = json.load(f)
        self.assertEqual(list(p)[:2], ["app", "nome"])
        self.assertEqual((p["app"], p["nome"], p["versao"]), ("gerencia", "GerencIA", "9.9.9"))
        cor = I.Conexao(self.data, self.share, 8099, "9.9.9", print, nome="correria")
        cor.publicar()
        with open(cor.arq_share, encoding="utf-8") as f:
            self.assertRegex(json.load(f)["gravado_em"], r"T\d\d:\d\d:\d\d$", "o correria.json segue o contrato dele (a hora da casa)")

    def test_publicar_sem_pasta_avisa(self):
        arquivo = os.path.join(self.share, "um-arquivo")
        open(arquivo, "w").close()
        c = I.Conexao(self.data, os.path.join(arquivo, "sub"), 1, "", lambda *a: self.logs.append(a))
        c.publicar()
        self.assertTrue(self.logs and "não consegui gravar" in self.logs[0][0])

    def test_autorizado(self):
        k = self.c.chave()
        self.assertFalse(self.c.autorizado({}))
        self.assertFalse(self.c.autorizado({"Authorization": k}))
        self.assertFalse(self.c.autorizado({"Authorization": "Bearer errada"}))
        self.assertIsNone(self.c.ultimo)
        self.assertTrue(self.c.autorizado({"Authorization": f"Bearer {k} ", "X-App": "CronologIA" + "x" * 50}))
        self.assertEqual(self.c.ultimo["app"], ("CronologIA" + "x" * 50)[:40])
        self.assertTrue(self.c.autorizado({"Authorization": f"Bearer {k}"}))
        self.assertEqual(self.c.ultimo["app"], "outro app")


class TestListar(unittest.TestCase):
    def test_periodo_invalido(self):
        for de, ate in ((date(2026, 1, 1), date(2027, 6, 1)), (date(2026, 2, 1), date(2026, 1, 1))):
            with self.assertRaisesRegex(ValueError, "Período inválido"):
                I.listar(dados(), de, ate, HOJE)

    def test_contas_do_mes(self):
        r = I.listar(dados(), date(2026, 11, 1), date(2026, 11, 30), HOJE)
        self.assertEqual(r["hoje"], "2026-11-15")
        por = {c["descricao"]: c for c in r["contas"]}
        self.assertEqual(sorted(por), ["Atrasada", "Internet", "Luz", "Água"], "as compras do cartão vencem em dezembro")
        self.assertEqual(por["Luz"], {"id": "l-luz", "tipo": "conta", "descricao": "Luz", "valor": 180.46, "vencimento": "2026-11-20", "pago": False,
                                      "categoria": "Casa", "conta": "", "atrasada": False})
        nets = [(c["id"], c["tipo"], c["vencimento"], c["categoria"], c["atrasada"]) for c in r["contas"] if c["descricao"] == "Internet"]
        self.assertEqual(nets, [("v:r-net:2026-09", "fixo", "2026-09-25", "Casa", True), ("v:r-net:2026-10", "fixo", "2026-10-25", "Casa", True),
                                ("v:r-net:2026-11", "fixo", "2026-11-25", "Casa", False)], "os fixos dos meses passados sem pagar entram como atrasados")
        self.assertTrue(por["Atrasada"]["atrasada"], "atrasada há menos de 62 dias aparece mesmo fora do período")
        self.assertEqual([c["vencimento"] for c in r["contas"]], sorted(c["vencimento"] for c in r["contas"]))
        self.assertEqual(r["categorias"], [{"id": "c-casa", "nome": "Casa"}, {"id": "c-x", "nome": "Sem tipo"}])

    def test_fatura_junta_o_cartao(self):
        r = I.listar(dados(), date(2026, 12, 1), date(2026, 12, 31), HOJE)
        f = next(c for c in r["contas"] if c["tipo"] == "fatura")
        self.assertEqual((f["id"], f["valor"], f["itens"], f["vencimento"], f["pago"]), ("f:cc|2026-12-10", 125.0, 3, "2026-12-10", False))
        self.assertNotIn("_itens", f)
        self.assertIn("Internet", [c["descricao"] for c in r["contas"]], "o fixo de dezembro")

    def test_lancado_some_o_virtual(self):
        d = dados()
        d["lancamentos"].append({"id": "l-net", "tipo": "despesa", "descricao": "Internet", "valor": 130, "data": "2026-11-25", "recorrencia": "r-net", "competencia": "2026-11", "pago": True})
        nets = [c for c in I.listar(d, date(2026, 11, 1), date(2026, 11, 30), HOJE)["contas"] if c["descricao"] == "Internet"]
        self.assertEqual([(c["id"], c["valor"], c["pago"]) for c in nets if c["id"].endswith("2026-11")], [("v:r-net:2026-11", 130, True)], "mesmo id, lançado ou não")


class TestPagar(unittest.TestCase):
    def test_pagar_conta_com_outro_valor_e_desfazer(self):
        d = dados()
        I.pagar(d, "l-luz", valor=199.999)
        luz = next(l for l in d["lancamentos"] if l["id"] == "l-luz")
        self.assertEqual((luz["pago"], luz["valor"]), (True, 200.0))
        I.pagar(d, "l-luz", valor=1, pago=False)
        self.assertEqual((luz["pago"], luz["valor"]), (False, 200.0), "desfazer não muda o valor")
        I.pagar(d, "l-luz", valor=0)
        self.assertEqual(luz["valor"], 200.0, "valor zero é ignorado")

    def test_pagar_fixo_vira_lancamento(self):
        d = dados()
        n = len(d["lancamentos"])
        I.pagar(d, "v:r-net:2026-11")
        novo = d["lancamentos"][-1]
        self.assertEqual(len(d["lancamentos"]), n + 1)
        self.assertEqual((novo["descricao"], novo["valor"], novo["pago"], novo["recorrencia"], novo["competencia"], novo["data"]), ("Internet", 120, True, "r-net", "2026-11", "2026-11-25"))
        self.assertNotIn("dia", novo)
        I.pagar(d, "v:r-net:2026-11", pago=False)
        self.assertEqual((len(d["lancamentos"]), novo["pago"]), (n + 1, False), "desfazer usa o lançamento que já existe")

    def test_fixo_com_mes_que_nao_existe_e_recusado(self):
        d = dados()
        n = len(d["lancamentos"])
        for cid in ("v:r-net:2026-13", "v:r-net:2026-00", "v:r-net:2026-1"):
            with self.subTest(cid=cid), self.assertRaises(ValueError):
                I.pagar(d, cid)
        self.assertEqual(len(d["lancamentos"]), n, "nada lançado")

    def test_desfazer_fixo_nao_lancado_nao_cria_nada(self):
        d = dados()
        n = len(d["lancamentos"])
        I.pagar(d, "v:r-net:2026-12", pago=False)
        self.assertEqual(len(d["lancamentos"]), n)

    def test_pagar_fatura_inteira(self):
        d = dados()
        I.pagar(d, "f:cc|2026-12-10")
        self.assertTrue(all(l["pago"] for l in d["lancamentos"] if l["id"] in ("k2", "k3")))
        I.pagar(d, "f:cc|2026-12-10", pago=False)
        self.assertFalse(any(l["pago"] for l in d["lancamentos"] if l["id"] in ("k2", "k3")))
        with self.assertRaisesRegex(LookupError, "Fatura não encontrada"):
            I.pagar(d, "f:cc|2026-07-10")

    def test_erros(self):
        d = dados()
        with self.assertRaisesRegex(ValueError, "recebimento"):
            I.pagar(d, "l-sal")
        with self.assertRaisesRegex(ValueError, "recebimento"):
            I.pagar(d, "v:r-sal:2026-11")
        with self.assertRaisesRegex(LookupError, "Conta não encontrada"):
            I.pagar(d, "nada")
        with self.assertRaisesRegex(LookupError, "Fixo não encontrado"):
            I.pagar(d, "v:r-nada:2026-11")
        with self.assertRaises(LookupError):
            I.pagar(d, None)

    def test_materializar_copia_o_que_importa(self):
        o = I._materializar({"descricao": "X", "valor": "10", "aporte": {"inv": "i1"}, "descontos": [{"valor": 1}], "data": "2026-11-01"}, pago=True)
        self.assertEqual((o["tipo"], o["valor"], o["pago"], o["aporte"], o["descontos"]), ("despesa", 10.0, True, {"inv": "i1"}, [{"valor": 1}]))
        self.assertNotIn("vinculo", o)


class TestNova(unittest.TestCase):
    def test_validacao(self):
        for corpo, msg in (({}, "nome da conta"), ({"descricao": "  "}, "nome"), ({"descricao": "X"}, "valor"), ({"descricao": "X", "valor": "abc"}, "valor"),
                           ({"descricao": "X", "valor": 0}, "valor"), ({"descricao": "X", "valor": 10, "vencimento": "10/11/2026"}, "vencimento inválida")):
            with self.subTest(corpo=corpo), self.assertRaisesRegex(ValueError, msg):
                I.nova(dados(), corpo)

    def test_avulsa(self):
        d = dados()
        cid = I.nova(d, {"descricao": "  Conserto  " + "x" * 200, "valor": "99.999", "vencimento": "2026-11-30", "categoria": "c-casa"})
        l = d["lancamentos"][-1]
        self.assertEqual((l["id"], len(l["descricao"]), l["valor"], l["data"], l["pago"], l["categoria"]), (cid, 120, 100.0, "2026-11-30", False, "c-casa"))
        self.assertTrue(l["descricao"].startswith("Conserto"))

    def test_mensal_e_anual(self):
        d = dados()
        cid = I.nova(d, {"descricao": "Academia", "valor": 99, "vencimento": "2026-11-08", "repete": "mensal", "categoria": "inexistente"})
        r = d["recorrencias"][-1]
        self.assertEqual(cid, f"v:{r['id']}:2026-11")
        self.assertEqual((r["dia"], r["inicio"], r["fim"], r["categoria"]), (8, "2026-11", None, ""))
        self.assertNotIn("freq", r)
        I.nova(d, {"descricao": "IPVA", "valor": 1200, "vencimento": "2027-01-20", "repete": "anual"})
        self.assertEqual(d["recorrencias"][-1]["freq"], "anual")
        contas = I.listar(d, date(2026, 11, 1), date(2026, 11, 30), HOJE)["contas"]
        self.assertIn(cid, [c["id"] for c in contas], "aparece na lista como fixo")



class TestBordasDoContrato(unittest.TestCase):
    """O que o CronologIA mostra e faz em casos de borda (o formato não pode mudar sem mudar o outro app)."""

    def base(self, lancamentos=(), recorrencias=()):
        d = dados()
        d["lancamentos"], d["recorrencias"] = list(lancamentos), list(recorrencias)
        return d

    def contas(self, d, de=date(2026, 11, 1), ate=date(2026, 11, 30), hoje=HOJE):
        return I.listar(d, de, ate, hoje)["contas"]

    def test_aporte_entra_como_conta(self):
        d = self.base(recorrencias=[{"id": "r-ap", "tipo": "despesa", "descricao": "Reserva", "valor": 500, "dia": 20, "inicio": "2026-11", "aporte": True}])
        self.assertEqual([(c["id"], c["tipo"]) for c in self.contas(d)], [("v:r-ap:2026-11", "fixo")], "o compromisso de aplicar")

    def test_fixo_encerrado_some_depois_do_fim(self):
        d = self.base(recorrencias=[{"id": "r", "tipo": "despesa", "descricao": "Academia", "valor": 99, "dia": 10, "inicio": "2026-01", "fim": "2026-10"}])
        c = self.contas(d, hoje=date(2026, 11, 1))
        self.assertEqual([(x["id"], x["atrasada"]) for x in c], [("v:r:2026-09", True), ("v:r:2026-10", True)], "só os atrasados de antes do fim; novembro não")

    def test_fixo_anual_so_no_mes_dele(self):
        d = self.base(recorrencias=[{"id": "r", "tipo": "despesa", "descricao": "IPVA", "valor": 900, "dia": 15, "inicio": "2026-03", "freq": "anual"}])
        self.assertEqual(self.contas(d), [], "em novembro não")
        c = self.contas(d, date(2027, 3, 1), date(2027, 3, 31), hoje=date(2027, 3, 1))
        self.assertEqual([(x["id"], x["vencimento"]) for x in c], [("v:r:2027-03", "2027-03-15")])

    def test_dia_31_em_fevereiro_vira_o_ultimo_dia(self):
        d = self.base(recorrencias=[{"id": "r", "tipo": "despesa", "descricao": "Aluguel", "valor": 2000, "dia": 31, "inicio": "2026-01"}])
        c = self.contas(d, date(2027, 2, 1), date(2027, 2, 28), hoje=date(2027, 2, 1))
        self.assertEqual([x["vencimento"] for x in c if not x["atrasada"]], ["2027-02-28"])
        self.assertEqual([x["vencimento"] for x in c if x["atrasada"]], ["2026-12-31", "2027-01-31"], "e os de dezembro e janeiro sem pagar")

    def test_fixo_pulado_no_mes_nao_aparece(self):
        d = self.base(lancamentos=[{"id": "p", "tipo": "despesa", "descricao": "Internet", "valor": 120, "data": "2026-11-25", "recorrencia": "r-net", "competencia": "2026-11", "pulado": True}],
                      recorrencias=[{"id": "r-net", "tipo": "despesa", "descricao": "Internet", "valor": 120, "dia": 25, "inicio": "2026-11"}])
        self.assertEqual(self.contas(d), [])

    def test_fixo_no_cartao_vai_para_a_fatura(self):
        d = self.base(recorrencias=[{"id": "r-mus", "tipo": "despesa", "descricao": "Música", "valor": 21.9, "dia": 8, "inicio": "2026-11", "conta": "cc", "cartao": True}])
        c = self.contas(d, date(2026, 12, 1), date(2026, 12, 31))
        self.assertEqual([(x["id"], x["tipo"], x["valor"], x["itens"]) for x in c], [("f:cc|2026-12-10", "fatura", 21.9, 1)], "compra do dia 8 (fecha dia 5): fatura de dezembro")

    def test_fatura_de_dezembro_vence_em_janeiro(self):
        d = self.base(lancamentos=[{"id": "k", "tipo": "despesa", "descricao": "Presentes", "valor": 300, "data": "2026-12-20", "conta": "cc", "cartao": True}])
        c = self.contas(d, date(2027, 1, 1), date(2027, 1, 31))
        self.assertEqual([x["id"] for x in c], ["f:cc|2027-01-10"])

    def test_fatura_toda_paga_fica_paga(self):
        d = self.base(lancamentos=[{"id": "k", "tipo": "despesa", "descricao": "Mercado", "valor": 80, "data": "2026-11-06", "conta": "cc", "cartao": True, "pago": True}])
        f = self.contas(d, date(2026, 12, 1), date(2026, 12, 31))[0]
        self.assertEqual((f["pago"], f["atrasada"], f["descricao"], f["conta"]), (True, False, "Fatura Banco Azul · Ana", "Banco Azul · Ana"))

    def test_pagar_fatura_lanca_o_fixo_do_cartao_e_desfazer_desmarca(self):
        d = self.base(lancamentos=[{"id": "k", "tipo": "despesa", "descricao": "Mercado", "valor": 80, "data": "2026-11-06", "conta": "cc", "cartao": True}],
                      recorrencias=[{"id": "r-mus", "tipo": "despesa", "descricao": "Música", "valor": 21.9, "dia": 8, "inicio": "2026-11", "conta": "cc", "cartao": True}])
        I.pagar(d, "f:cc|2026-12-10")
        self.assertEqual(sorted((l["descricao"], l["pago"], l.get("competencia")) for l in d["lancamentos"]), [("Mercado", True, None), ("Música", True, "2026-11")])
        I.pagar(d, "f:cc|2026-12-10", pago=False)
        self.assertEqual({l["pago"] for l in d["lancamentos"]}, {False})
        self.assertEqual(len(d["lancamentos"]), 2, "desfazer não apaga o fixo lançado")

    def test_pagar_com_valor_zero_ou_desfazer_nao_muda_o_valor(self):
        d = self.base(lancamentos=[{"id": "l", "tipo": "despesa", "descricao": "Gás", "valor": 110, "data": "2026-11-12"}])
        I.pagar(d, "l", valor=0)
        self.assertEqual((d["lancamentos"][0]["valor"], d["lancamentos"][0]["pago"]), (110, True))
        I.pagar(d, "l", valor=999, pago=False)
        self.assertEqual((d["lancamentos"][0]["valor"], d["lancamentos"][0]["pago"]), (110, False))
        I.pagar(d, "l", valor=118.456)
        self.assertEqual(d["lancamentos"][0]["valor"], 118.46)

    def test_recebimento_nao_se_paga_por_aqui(self):
        d = self.base(lancamentos=[{"id": "s", "tipo": "receita", "descricao": "Salário", "valor": 5000, "data": "2026-11-05"}])
        with self.assertRaisesRegex(ValueError, "recebimento"):
            I.pagar(d, "s")

    def test_ids_que_nao_existem(self):
        d = self.base()
        for cid, msg in (("v:r-sumiu:2026-11", "Fixo não encontrado"), ("l-sumiu", "Conta não encontrada"), ("f:cc|2026-12-10", "Fatura não encontrada"), ("", "Conta não encontrada")):
            with self.subTest(cid=cid), self.assertRaisesRegex(LookupError, msg):
                I.pagar(d, cid)

    def test_paga_e_antiga_nao_aparece_fora_do_periodo(self):
        d = self.base(lancamentos=[{"id": "l", "tipo": "despesa", "descricao": "Paga em outubro", "valor": 10, "data": "2026-10-20", "pago": True}])
        self.assertEqual(self.contas(d), [], "só as atrasadas sem pagar voltam")

    def test_mesma_data_em_ordem_de_nome(self):
        d = self.base(lancamentos=[{"id": n, "tipo": "despesa", "descricao": n, "valor": 1, "data": "2026-11-20"} for n in ("Luz", "Água", "Gás")])
        self.assertEqual([c["descricao"] for c in self.contas(d)], ["Gás", "Luz", "Água"])

    def test_conta_sem_nome_e_conta_do_banco(self):
        d = self.base(lancamentos=[{"id": "l", "tipo": "despesa", "descricao": "", "valor": 5, "data": "2026-11-20", "conta": "cc"}])
        c = self.contas(d)[0]
        self.assertEqual((c["descricao"], c["conta"]), ("Conta", "Banco Azul · Ana"))

    def test_nova_limpa_o_que_vem(self):
        d = self.base()
        cid = I.nova(d, {"descricao": "  " + "x" * 200, "valor": "45.678", "vencimento": "2026-11-30", "categoria": "c-nao-existe", "repete": "semanal"})
        l = d["lancamentos"][0]
        self.assertEqual((cid, len(l["descricao"]), l["valor"], l["categoria"], d["recorrencias"]), (l["id"], 120, 45.68, "", []), "repete desconhecido vira conta avulsa")
        for corpo, msg in (({"descricao": "A", "valor": "abc", "vencimento": "2026-11-30"}, "Coloque o valor"),
                           ({"descricao": "A", "valor": -3, "vencimento": "2026-11-30"}, "Coloque o valor"),
                           ({"descricao": "A", "valor": 3, "vencimento": "30/11/2026"}, "vencimento inválida")):
            with self.subTest(corpo=corpo), self.assertRaisesRegex(ValueError, msg):
                I.nova(d, corpo)

    def test_nova_mensal_aparece_com_o_id_do_fixo(self):
        d = self.base()
        cid = I.nova(d, {"descricao": "Faxina", "valor": 200, "vencimento": "2026-11-28", "categoria": "c-casa", "repete": "mensal"})
        c = self.contas(d)
        self.assertEqual([(x["id"], x["vencimento"], x["categoria"]) for x in c], [(cid, "2026-11-28", "Casa")])
        I.pagar(d, cid, valor=210)
        self.assertEqual([(l["valor"], l["competencia"]) for l in d["lancamentos"]], [(210, "2026-11")])
        self.assertEqual(d["recorrencias"][0]["valor"], 200, "pagar com outro valor não muda o fixo")


class TestSensoresContas(unittest.TestCase):
    """1.60.0: a próxima conta, a conta vencida e a fatura de cada cartão."""

    def test_proxima_e_vencidas(self):
        s = I.sensores_contas(dados(), HOJE)
        valor, p = s["sensor.gerencia_proxima_conta"]
        self.assertEqual(valor, 180.46)
        self.assertEqual((p["descricao"], p["vencimento"], p["dias"], p["tipo"], p["categoria"], p["conta"]),
                         ("Luz", "2026-11-20", 5, "conta", "Casa", None))
        self.assertEqual((p["device_class"], p["unit_of_measurement"], p["a_pagar_7_dias"], p["vence_hoje"]), ("monetary", "BRL", 180.46, 0))
        self.assertNotIn("state_class", p)
        self.assertEqual([c["descricao"] for c in p["proximas"]], ["Luz", "Internet", "Fatura Banco Azul · Ana"])
        estado, v = s["binary_sensor.gerencia_conta_vencida"]
        self.assertEqual((estado, v["device_class"], v["quantidade"], v["total"]), ("on", "problem", 3, 290.0))
        self.assertEqual(v["contas"][1], {"descricao": "Atrasada", "vencimento": "2026-10-01", "valor": 50.0})
        self.assertNotIn("Muito antiga", json.dumps(v), "mais de 2 meses: fica de fora, como no CronologIA")

    def test_nada_a_pagar(self):
        s = I.sensores_contas({"lancamentos": [], "recorrencias": [], "bancos": []}, HOJE)
        valor, p = s["sensor.gerencia_proxima_conta"]
        self.assertEqual((valor, p["descricao"], p["dias"], p["proximas"]), ("unknown", None, None, []))
        self.assertEqual(s["binary_sensor.gerencia_conta_vencida"][0], "off")
        self.assertEqual(len(s), 2, "sem cartão, sem sensor de fatura")

    def test_fatura_aberta_e_limite(self):
        d = dados()
        d["bancos"][0]["contas"][0]["limite"] = 1000
        valor, f = I.sensores_contas(d, HOJE)["sensor.gerencia_fatura_banco_azul_ana"]
        self.assertEqual(valor, 125.0, "a compra de hoje cai na fatura de 10/12: mercado, farmácia e o estorno")
        self.assertEqual((f["fecha"], f["vence"], f["dias_para_fechar"], f["fechada"]), ("2026-12-05", "2026-12-10", 20, None))
        self.assertEqual((f["limite"], f["usado"], f["disponivel"], f["uso_limite"]), (1000.0, 40.0, 960.0, 4.0), "usado: as compras não pagas")
        self.assertEqual(f["friendly_name"], "GerencIA Fatura Banco Azul · Ana")

    def test_fatura_fechada_falta_pagar(self):
        valor, f = I.sensores_contas(dados(), date(2026, 12, 7))["sensor.gerencia_fatura_banco_azul_ana"]
        self.assertEqual(valor, 0, "a de janeiro ainda não tem nada")
        self.assertEqual((f["fecha"], f["vence"], f["fechada"]), ("2027-01-05", "2027-01-10", {"valor": 125.0, "vence": "2026-12-10"}))
        self.assertNotIn("limite", f, "sem limite: sem o uso do limite")

    def test_dois_cartoes_com_o_mesmo_nome(self):
        d = dados()
        d["bancos"].append({"id": "b2", "nome": "Banco Azul", "contas": [{"id": "conta-x9", "pessoa": "Ana", "cartao": True}, {"id": "cc2", "pessoa": "Beto"}]})
        ids = sorted(e for e in I.sensores_contas(d, HOJE) if "fatura" in e)
        self.assertEqual(ids, ["sensor.gerencia_fatura_banco_azul_ana", "sensor.gerencia_fatura_banco_azul_ana_tax9"], "a conta sem cartão fica de fora")

class TestAvisos(unittest.TestCase):
    """1.61.0: os avisos do Início para o Agora do CronologIA (as contas ficam de fora: lá já estão em Contas a pagar)."""

    def test_sem_nada(self):
        self.assertEqual(I.avisos({"investimentos": [], "beneficios": []}, [], HOJE), [])

    def test_faturas_e_fotos_para_conferir(self):
        itens = [
            {"id": "a1", "estado": "conferir", "origem": "email", "de": "Banco Azul", "endereco": "fatura@bancoazul.com.br",
             "resultado": {"lancamentos": [{"tipo": "despesa", "valor": 100, "cartao": True}, {"tipo": "despesa", "valor": 20.5, "cartao": True},
                                           {"tipo": "receita", "valor": 300, "cartao": True, "descricao": "Pagamento recebido"}]}},
            {"id": "a2", "estado": "conferir", "origem": "email", "de": "", "endereco": "x@corretora.com", "resultado": {"investimentos": [{}]}},
            {"id": "a3", "estado": "senha", "origem": "email", "de": "Banco Azul"},
            {"id": "a4", "estado": "erro", "origem": "email", "de": "Banco Azul", "erro": ""},
            {"id": "a5", "estado": "lendo", "origem": "whatsapp", "de": "Ana"},
        ]
        av = I.avisos({}, itens, HOJE)
        self.assertEqual([(a["id"], a["tipo"], a["titulo"], a["texto"], a.get("valor")) for a in av], [
            ("email:a1", "email", "Fatura Banco Azul", "Por e-mail · 2 lançamentos", 120.5),
            ("email:a2", "email", "Fatura x@corretora.com", "Por e-mail · 1 investimento", None),
            ("email:a3", "senha", "Fatura Banco Azul", "Por e-mail · o PDF tem senha", None),
            ("email:a4", "erro", "Fatura Banco Azul", "Por e-mail · não consegui ler", None),
            ("email:a5", "whatsapp", "Enviado por Ana", "Pelo WhatsApp · lendo com IA…", None)])
        self.assertTrue(all(a["caminho"] == "/agora" for a in av))

    def test_investimentos_e_indices(self):
        invs = [{"nome": "CDB Azul", "vencimento": "2026-11-10", "data_valor": "2026-11-01"},
                {"nome": "LCI Verde", "vencimento": "2026-12-01", "data_valor": "2026-11-01"},
                {"nome": "CDB Lilás", "vencimento": "2026-11-15", "data_valor": "2026-08-01"},
                {"nome": "Poupança", "indexador": "parado", "data_valor": "2025-01-01"}]
        d = {"investimentos": invs, "indices": {"fonte": "bcb", "atualizado_em": "2026-11-10T08:00:00-03:00"}}
        av = {a["id"]: a for a in I.avisos(d, [], HOJE)}
        self.assertEqual((av["inv:vencidos"]["titulo"], av["inv:vencidos"]["texto"]), ("Um investimento venceu", "CDB Azul"))
        self.assertEqual((av["inv:vence"]["titulo"], av["inv:vence"]["dias"], av["inv:vence"]["texto"]),
                         ("Vence hoje", 0, "CDB Lilás · decida para onde vai o dinheiro"))
        self.assertEqual((av["inv:valores"]["texto"], av["inv:valores"]["n"]), ("CDB Lilás está sem atualizar há mais de 2 meses", 1), "o parado fica de fora")
        self.assertEqual(av["indices"]["texto"], "Sem os do Banco Central desde 10/11")
        invs[1]["vencimento"] = "2026-11-16"
        invs[3]["indexador"] = "cdi"
        d["indices"].update(erro="sem resposta")
        av = {a["id"]: a for a in I.avisos(d, [], HOJE)}
        self.assertEqual((av["inv:vence"]["titulo"], av["inv:valores"]["texto"]), ("Vence hoje", "2 investimentos estão sem atualizar há mais de 2 meses"))
        self.assertEqual(av["indices"]["texto"], "O Banco Central não responde desde 10/11")
        invs[2]["vencimento"] = "2026-11-17"
        self.assertEqual(next(a for a in I.avisos(d, [], HOJE) if a["id"] == "inv:vence")["titulo"], "Vence amanhã")
        invs[1]["vencimento"] = invs[2]["vencimento"] = "2026-12-01"
        self.assertEqual(next(a for a in I.avisos(d, [], HOJE) if a["id"] == "inv:vence")["titulo"], "Vence em 16 dias")
        invs[1]["vencimento"] = invs[2]["vencimento"] = "2027-01-01"
        invs[0]["vencimento"] = "2026-11-01"
        invs.append({"nome": "LCA Rosa", "vencimento": "2026-10-01", "data_valor": "2026-11-01"})
        d["indices"] = {"fonte": "bcb", "auto": False, "atualizado_em": "2026-10-01"}
        av = {a["id"]: a for a in I.avisos(d, [], HOJE)}
        self.assertEqual(av["inv:vencidos"]["titulo"], "2 investimentos venceram")
        self.assertNotIn("inv:vence", av, "mais de 30 dias")
        self.assertNotIn("indices", av, "à mão: sem aviso")
        d["indices"] = {"fonte": "bcb", "atualizado_em": "2026-11-13T08:00:00-03:00"}
        self.assertNotIn("indices", {a["id"] for a in I.avisos(d, [], HOJE)}, "até 3 dias, nada")

    def test_beneficios(self):
        d = dados()
        d["beneficios"] = [
            {"id": "b1", "nome": "Sala VIP", "origem": "conta:cc", "tipo": "contagem", "total": 4, "renova": "ano", "desde": "2025-12-01", "usos": [{"data": "2026-01-10", "qtd": 1}]},
            {"id": "b2", "nome": "Créditos", "origem": "", "tipo": "saldo", "total": 50, "moeda": "USD", "renova": "mes", "desde": "2026-01-01", "usos": [{"data": "2026-11-02", "qtd": 12.5}]},
            {"id": "b3", "nome": "Frete grátis", "origem": "fixo:sumiu", "tipo": "vantagem", "renova": "nunca"},
            {"id": "b4", "nome": "Seguro", "origem": "conta:apagada", "tipo": "vantagem"},
            {"id": "b5", "nome": "Cashback", "tipo": "saldo", "total": 30, "renova": "ano", "desde": "2026-06-01"},
            {"id": "b6", "nome": "Milhas", "tipo": "saldo", "total": 30, "renova": "nunca", "validade": "2026-11-01"},
        ]
        av = {a["id"]: a for a in I.avisos(d, [], HOJE)}
        self.assertEqual((av["ben:usar"]["titulo"], av["ben:usar"]["texto"], av["ben:usar"]["caminho"]),
                         ("2 benefícios para usar", "Sala VIP (3) até 30/11, Créditos (US$ 37,50) até 30/11", "/beneficios"))
        self.assertEqual((av["ben:parar"]["titulo"], av["ben:parar"]["texto"]),
                         ("2 benefícios que vão parar", "Frete grátis: o fixo Fixo apagado acabou, Seguro: a conta saiu de Bancos"))
        d["beneficios"] = [{"id": "b7", "nome": "Lavagem", "tipo": "saldo", "total": 100, "renova": "mes", "desde": "2026-01-01"}]
        self.assertEqual([(a["titulo"], a["texto"]) for a in I.avisos(d, [], HOJE)], [("Benefício para usar", "Lavagem (R$ 100) até 30/11")])
        d["beneficios"] = [{"id": "b8", "nome": "Netflix", "origem": "fixo:r-net", "tipo": "vantagem"}, "lixo"]
        self.assertEqual(I.avisos(d, [], HOJE), [], "o fixo continua: nada")
        d["beneficios"][0]["origem"] = "conta:apagada"
        self.assertEqual([a["titulo"] for a in I.avisos(d, [], HOJE)], ["Benefício que vai parar"])


if __name__ == "__main__":
    unittest.main()
