"""Conversar com a IA (chat.py e as rotas no server.py): a conversa guardada, o que a IA recebe (dados, tela e
histórico), as ações que ela propõe (limpas antes de chegar na tela), a IA simulada e a IA de verdade contra um
Home Assistant de mentira. Dados inventados (Ana, Banco Azul)."""
import json
import os
import unittest
from datetime import date

from tests.base import ServidorFalso, importar_servidor, pasta_temp, Servidor
S = importar_servidor()
import chat as C  # noqa: E402  (o importar_servidor põe gerencia/app no caminho)

HOJE = date(2026, 11, 2)


def dados():
    d = S.vazio()
    d["bancos"] = [{"id": "b-azul", "nome": "Banco Azul", "contas": [
        {"id": "k-ana", "pessoa": "Ana", "cartao": True, "fechamento": 5, "vencimento": 12},
        {"id": "k-beto", "pessoa": "Beto", "cartao": False, "fechamento": 1, "vencimento": 10}]}]
    d["lancamentos"] = [
        {"id": "l-luz", "tipo": "despesa", "descricao": "Luz", "valor": 180, "data": "2026-11-20", "categoria": "c-contas"},
        {"id": "l-sal", "tipo": "receita", "descricao": "Salário", "valor": 5000, "data": "2026-11-01", "pago": True, "categoria": "c-salario"},
        {"id": "l-pago", "tipo": "despesa", "descricao": "Água", "valor": 90, "data": "2026-11-01", "pago": True},
        {"id": "l-velho", "tipo": "despesa", "descricao": "Muito antigo", "valor": 1, "data": "2026-01-01", "pago": True},
        {"id": "k1", "tipo": "despesa", "descricao": "Mercado", "valor": 100, "data": "2026-11-06", "conta": "k-ana", "cartao": True},
    ]
    d["recorrencias"] = [{"id": "r-net", "tipo": "despesa", "descricao": "Internet", "valor": 120, "dia": 25, "inicio": "2026-11", "categoria": "c-contas"},
                         {"id": "r-acad", "tipo": "despesa", "descricao": "Academia", "valor": 99, "dia": 10, "inicio": "2026-01", "fim": "2026-05"}]
    d["investimentos"] = [{"id": "i-cdb", "nome": "CDB Azul", "banco": "b-azul", "valor": 1000, "indexador": "cdi_pct", "taxa": 100, "tipo": "cdb", "data_valor": "2026-11-02"},
                          {"id": "i-mae", "nome": "Poupança da Mãe", "valor": 500, "indexador": "parado", "tipo": "poupanca", "titular": "terceiros", "terceiro": "Mãe"}]
    return d


# ---------------------------------------------------------------------------------------------------------------
class TestConversaGuardada(unittest.TestCase):
    def setUp(self):
        self.arq = os.path.join(pasta_temp(), "sub", "chat.json")
        self.c = C.Conversa(self.arq, S._gravar_chat)

    def msg(self, papel="eu", **mais):
        return dict({"id": C.uid(), "papel": papel, "texto": "oi"}, **mais)

    def test_sem_arquivo_comeca_vazia(self):
        self.assertEqual(self.c.ler(), [])

    def test_acrescentar_e_ler(self):
        a, b = self.msg(), self.msg("ia", texto="olá")
        self.c.acrescentar(a, b)
        self.assertEqual([m["texto"] for m in C.Conversa(self.arq, S._gravar_chat).ler()], ["oi", "olá"], "fica gravado (abre de onde parou)")

    def test_guarda_so_as_ultimas(self):
        for k in range(C.MAX_GUARDADAS + 7):
            self.c.acrescentar(self.msg(texto=str(k)))
        m = self.c.ler()
        self.assertEqual((len(m), m[0]["texto"], m[-1]["texto"]), (C.MAX_GUARDADAS, "7", str(C.MAX_GUARDADAS + 6)))

    def test_arquivo_estragado_ou_estranho(self):
        os.makedirs(os.path.dirname(self.arq), exist_ok=True)
        for conteudo in ("{", "[]", '{"mensagens": "x"}', '{"mensagens": [1, {"papel": "outro"}, {"papel": "eu", "texto": "fica"}]}'):
            with open(self.arq, "w") as f:
                f.write(conteudo)
            with self.subTest(conteudo=conteudo):
                self.assertEqual([m.get("texto") for m in self.c.ler()], ["fica"] if "fica" in conteudo else [])

    def test_limpar(self):
        self.c.acrescentar(self.msg())
        self.assertEqual((self.c.limpar(), self.c.ler()), ([], []))

    def test_marcar_grupo_e_conta(self):
        ia = self.msg("ia", acoes={"lancamentos": [{"descricao": "x"}], "pagar": [{"id": "a"}, {"id": "b"}]})
        self.c.acrescentar(self.msg(), ia)
        self.c.marcar(ia["id"], "lancamentos", "feito")
        m = self.c.marcar(ia["id"], "pagar.1", "dispensado")[-1]
        self.assertEqual(m["estado"], {"lancamentos": "feito", "pagar.1": "dispensado"})

    def test_marcar_invalido(self):
        ia = self.msg("ia", acoes={"pagar": [{"id": "a"}]})
        eu = self.msg()
        self.c.acrescentar(eu, ia)
        for mid, chave, estado, erro in ((ia["id"], "pagar", "feito", ValueError), (ia["id"], "lancamentos.0", "feito", ValueError),
                                          (ia["id"], "pagar.0", "talvez", ValueError), (ia["id"], "pagar.3", "feito", LookupError),
                                          (ia["id"], "investimentos", "feito", LookupError), ("sumiu", "pagar.0", "feito", LookupError),
                                          (eu["id"], "pagar.0", "feito", LookupError)):
            with self.subTest(chave=chave, estado=estado), self.assertRaises(erro):
                self.c.marcar(mid, chave, estado)


# ---------------------------------------------------------------------------------------------------------------
class TestOQueAIARecebe(unittest.TestCase):
    def setUp(self):
        self.r = C.resumo(dados(), HOJE)

    def test_dia_de_hoje(self):
        self.assertTrue(self.r.startswith("Hoje é segunda-feira, 02/11/2026."))

    def test_oportunidades_dos_beneficios(self):
        """1.54: o que falta para ganhar mais (Mais › Benefícios › Oportunidades), para a IA responder "tenho alguma oportunidade?"."""
        d = dados()
        d["bancos"][0]["contas"][1].update(meta_nivel="Black", meta_valor=10000)
        d["metas"] = [{"id": "m1", "tipo": "investido", "origem": "conta:k-ana", "valor": 5000, "ganha": "Sem anuidade"},
                      {"id": "m2", "tipo": "gasto", "origem": "conta:k-ana", "valor": 3000, "periodo": "mes", "ganha": "Sala VIP"},
                      {"id": "m3", "tipo": "plano", "origem": "fixo:r-net", "valor": 150, "periodo": "mes", "ganha": "Mais velocidade", "plano": "1 giga"},
                      {"id": "m4", "tipo": "investido", "origem": "conta:k-ana", "valor": 500, "ganha": "Cashback"}, "lixo"]
        r = C.resumo(d, HOJE)
        self.assertIn("Oportunidades nos benefícios (o que ganha | de onde | condição | situação):", r)
        self.assertIn("Sem anuidade | Banco Azul · Ana | R$ 5.000,00 investidos | faltam R$ 4.000,00 (tem R$ 1.000,00)", r)
        self.assertIn("Sala VIP | Banco Azul · Ana | gastar R$ 3.000,00 por mês no cartão | sem como saber", r, "sem faturas nos últimos 3 meses")
        self.assertIn("Mais velocidade | Internet | plano 1 giga de R$ 150,00 por mês | custa R$ 30,00 a mais por mês", r)
        self.assertIn("Cashback | Banco Azul · Ana | R$ 500,00 investidos | já dá", r)
        self.assertIn("nível Black | Banco Azul · Beto | R$ 10.000,00 investidos | faltam R$ 9.000,00 (tem R$ 1.000,00)", r,
                      "o próximo nível da conta; o CDB de antes, sem a conta, conta como seu (como no card)")
        self.assertNotIn("Oportunidades nos benefícios", C.resumo(dados(), HOJE), "sem nenhuma, nada")

    def test_contas_e_cartoes(self):
        self.assertIn("k-ana | Banco Azul · Ana | cartão, fecha dia 5, vence dia 12", self.r)
        self.assertIn("k-beto | Banco Azul · Beto | sem cartão", self.r)
        d = dados()
        d["bancos"][0]["contas"][1]["debito"] = False
        self.assertIn("k-beto | Banco Azul · Beto | sem cartão; sem cartão de débito (só Pix)", C.resumo(d, HOJE), "1.57.0")

    def test_caixa_do_mes(self):
        self.assertIn("Caixa: saldo de hoje R$ 4.909,00. Neste mês: entrou R$ 5.000,00, saiu R$ 90,00", self.r)

    def test_contas_a_pagar_com_o_id_para_pagar(self):
        self.assertIn("l-luz | Luz | R$ 180,00 | 2026-11-20 | a pagar", self.r)
        self.assertIn("v:r-net:2026-11 | Internet | R$ 120,00 | 2026-11-25 | a pagar", self.r, "o fixo do mês com o id de sempre")
        self.assertIn("f:k-ana|2026-12-12 | Fatura Banco Azul · Ana | R$ 100,00", self.r, "a fatura do cartão")

    def test_lancamentos_recentes_sem_os_antigos(self):
        self.assertIn("2026-11-01 | recebimento | Salário | R$ 5.000,00 | Salário | recebido |", self.r)
        self.assertNotIn("Muito antigo", self.r)

    def test_fixos_sem_os_encerrados(self):
        self.assertIn("Internet | gasto | R$ 120,00 | todo dia 25 | Contas da casa", self.r)
        self.assertNotIn("Academia", self.r)

    def test_investimentos_e_patrimonio(self):
        self.assertIn("i-cdb | CDB Azul | Banco Azul | meu | R$ 1.000,00 | 100% do CDI | - | no vencimento", self.r)
        self.assertIn("i-mae | Poupança da Mãe |  | Mãe | R$ 500,00", self.r)
        self.assertIn("Patrimônio: meu R$ 1.000,00, de outras pessoas R$ 500,00, total R$ 1.500,00", self.r)
        self.assertIn("CDI 13,65%", self.r)

    def test_categorias_com_id(self):
        self.assertIn("c-mercado: Mercado, despesa", self.r)

    def test_sem_dados_nao_quebra(self):
        r = C.resumo(S.vazio(), HOJE)
        self.assertIn("Caixa: saldo de hoje R$ 0,00", r)
        self.assertNotIn("Investimentos (", r)

    def test_instrucoes(self):
        hist = [{"papel": "eu", "texto": "oi"}, {"papel": "ia", "texto": "Olá!", "acoes": {"lancamentos": [{}], "pagar": [{}]}, "estado": {"lancamentos": "feito"}},
                {"papel": "eu", "texto": "quanto gastei?"}]
        t = C.instrucoes(dados(), hist, "Caixa\nSaldo R$ 4.910", "caixa", "Ana Souza", HOJE)
        self.assertIn("finanças da casa de Ana,", t, "só o primeiro nome")
        self.assertIn("A pessoa está na tela Caixa. O que aparece nela agora:\n<<<\nCaixa\nSaldo R$ 4.910\n>>>", t)
        self.assertIn("Pessoa: oi\nIA: Olá! [propôs lançar (1): confirmado; propôs pagar (1): ainda sem confirmar]\nPessoa: quanto gastei?", t)
        self.assertTrue(t.rstrip().endswith('{"resposta":"","lancamentos":[],"pagar":[],"investimentos":[]}'))
        self.assertIn('"pagar": cada conta da lista', t)

    def test_instrucoes_sem_tela_e_historico_curto(self):
        hist = [{"papel": "eu", "texto": f"m{k}"} for k in range(30)]
        t = C.instrucoes(dados(), hist, "", "", "", HOJE)
        self.assertNotIn("A pessoa está na tela", t)
        self.assertNotIn("Pessoa: m13\n", t)
        self.assertIn("Pessoa: m14\n", t, f"só as últimas {C.MAX_HISTORICO}")
        self.assertIn("finanças da casa, no Brasil", t, "sem nome")

    def test_tela_cortada(self):
        t = C.instrucoes(dados(), [{"papel": "eu", "texto": "oi"}], "x" * 9000, "mais", "", HOJE)
        self.assertIn("x" * C.MAX_TELA + "\n>>>", t)
        self.assertNotIn("x" * (C.MAX_TELA + 1), t)


# ---------------------------------------------------------------------------------------------------------------
class TestRespostaEAcoes(unittest.TestCase):
    def test_separar(self):
        self.assertEqual(C.separar("  Só texto  "), ("Só texto", {}))
        self.assertEqual(C.separar({"resposta": "Ok", "pagar": [{"id": "x"}], "lancamentos": [], "investimentos": "x"}), ("Ok", {"pagar": [{"id": "x"}]}))
        self.assertEqual(C.separar({"texto": "Também vale"}), ("Também vale", {}))
        self.assertEqual(C.separar(["lista"]), ("", {}))
        self.assertEqual(len(C.separar("x" * 9000)[0]), C.MAX_RESPOSTA)

    def test_pagar_so_contas_abertas_que_existem(self):
        p = C.limpar_pagar([{"id": "l-luz", "valor": "190,50"}, {"id": "l-luz"}, {"id": "l-pago"}, {"id": "inventado"}, {"id": "v:r-net:2026-11", "valor": 0}, "x"], dados(), HOJE)
        self.assertEqual(p, [
            {"id": "l-luz", "descricao": "Luz", "vencimento": "2026-11-20", "valor_conta": 180.0, "valor": 190.5, "tipo": "conta"},
            {"id": "v:r-net:2026-11", "descricao": "Internet", "vencimento": "2026-11-25", "valor_conta": 120.0, "valor": 120.0, "tipo": "fixo"}])

    def test_pagar_fatura(self):
        p = C.limpar_pagar([{"id": "f:k-ana|2026-12-12"}], dados(), HOJE)
        self.assertEqual([(x["tipo"], x["valor"]) for x in p], [("fatura", 100.0)])

    def test_acoes_limpas_pelo_servidor(self):
        d = dados()
        a = S.chat_acoes({"lancamentos": [{"tipo": "despesa", "descricao": "Feira", "valor": "45,90", "categoria": "c-mercado"}, {"valor": 0}],
                          "investimentos": [{"existente": "i-cdb", "aporte": 300}, {"existente": "inventado", "valor": 0}, {"nome": "Novo", "valor": 200}],
                          "pagar": [{"id": "inventado"}]}, d)
        self.assertEqual([(l["descricao"], l["valor"], l["categoria"]) for l in a["lancamentos"]], [("Feira", 45.9, "c-mercado")], "valor zero sai")
        self.assertEqual([(i["existente"], i["aporte"], i["valor"]) for i in a["investimentos"]], [("i-cdb", 300.0, 0.0), ("", 0.0, 200.0)], "id inventado sem valor sai")
        self.assertNotIn("pagar", a, "grupo vazio não vai")


class TestIASimulada(unittest.TestCase):
    def sim(self, t):
        return C.simulado(t, dados(), HOJE)

    def test_pagar_conta_da_lista(self):
        r = self.sim("paguei a luz, 190 reais")
        self.assertEqual(r["pagar"], [{"id": "l-luz", "valor": 190.0}])

    def test_gasto_novo(self):
        r = self.sim("gastei 45 no mercado no cartão")
        self.assertEqual({k: r["lancamentos"][0][k] for k in ("descricao", "valor", "categoria", "cartao", "data")},
                         {"descricao": "Mercado", "valor": 45.0, "categoria": "c-mercado", "cartao": True, "data": "2026-11-02"})

    def test_aporte_e_saldo(self):
        self.assertEqual(self.sim("apliquei 2 mil no cdb azul")["investimentos"], [{"existente": "i-cdb", "valor": 0, "aporte": 2000.0}])
        self.assertEqual(self.sim("o saldo do cdb azul é 1500")["investimentos"], [{"existente": "i-cdb", "valor": 1500.0}])

    def test_perguntas(self):
        self.assertIn("R$ 4.909,00", self.sim("qual o saldo do caixa?")["resposta"])
        self.assertIn("R$ 1.000,00", self.sim("quanto tenho em investimentos")["resposta"])
        self.assertIn("- Luz: R$ 180,00, 20/11", self.sim("quais contas vencem?")["resposta"])
        self.assertNotIn("contas", self.sim("me conta uma piada")["resposta"].split(",")[0].lower())


# ---------------------------------------------------------------------------------------------------------------
class TestEnviarSimulado(unittest.TestCase):
    def setUp(self):
        self.antes = S.IA_MOCK
        S.IA_MOCK = True
        S.salvar(dados(), versao=False)
        S.CHAT.limpar()

    def tearDown(self):
        S.IA_MOCK = self.antes

    def test_pergunta_e_resposta_guardadas(self):
        r = S.chat_enviar({"texto": "  gastei 45 no mercado  ", "fala": True})
        eu, ia = r["mensagens"]
        self.assertEqual((eu["papel"], eu["texto"], eu["fala"]), ("eu", "gastei 45 no mercado", True))
        self.assertEqual((ia["papel"], ia["acoes"]["lancamentos"][0]["descricao"]), ("ia", "Mercado"))
        self.assertEqual(len(S.chat_estado()["mensagens"]), 2)
        self.assertEqual(S.resumo_uso()["today"]["kinds"].get("chat", 0) >= 1, True, "conta no uso da IA como conversa")

    def test_erros(self):
        with self.assertRaisesRegex(ValueError, "Escreva uma mensagem"):
            S.chat_enviar({"texto": "   "})
        d = dados()
        d["ajustes"]["ia"] = False
        S.salvar(d, versao=False)
        with self.assertRaisesRegex(ValueError, "A IA está desligada"):
            S.chat_enviar({"texto": "oi"})
        self.assertEqual(S.chat_estado()["mensagens"], [], "erro não grava nada")

    def test_texto_longo_cortado(self):
        r = S.chat_enviar({"texto": "a" * 5000})
        self.assertEqual(len(r["mensagens"][0]["texto"]), C.MAX_TEXTO)


class TestEnviarIAReal(unittest.TestCase):
    """O pedido ai_task.generate_data de verdade, num Home Assistant de mentira."""

    def setUp(self):
        self.resp = (200, {"service_response": {"data": {"resposta": "Lanço a feira.", "lancamentos": [{"tipo": "despesa", "descricao": "Feira", "valor": 30, "data": "2026-11-02"}]}}})
        self.ha = ServidorFalso({"/services/ai_task/generate_data": lambda h, c: self.resp, "/states": (200, [])})
        self.antes = (S.IA_MOCK, S.TOKEN, S.HA_API)
        S.IA_MOCK, S.TOKEN, S.HA_API = False, "token-teste", self.ha.url
        d = dados()
        d["ajustes"]["ia_entidade"] = "ai_task.minha"
        S.salvar(d, versao=False)
        S.CHAT.limpar()

    def tearDown(self):
        S.IA_MOCK, S.TOKEN, S.HA_API = self.antes
        self.ha.fechar()

    def pedido(self):
        return json.loads([p for p in self.ha.pedidos if p[1].startswith("/services/ai_task/generate_data")][-1][3])

    def test_pedido_com_a_tela_a_conversa_e_a_ia_escolhida(self):
        S.chat_enviar({"texto": "oi", "tela": "Investimentos\nCDB Azul", "aba": "investimentos"}, "Ana Souza")
        S.chat_enviar({"texto": "e agora?"})
        p = self.pedido()
        self.assertEqual((p["task_name"], p["entity_id"]), ("GerencIA: conversa", "ai_task.minha"))
        self.assertIn("Pessoa: oi\nIA: Lanço a feira. [propôs lançar (1): ainda sem confirmar]\nPessoa: e agora?", p["instructions"])

    def test_resposta_so_texto(self):
        self.resp = (200, {"service_response": {"data": "Olá, Ana! Tudo certo por aqui."}})
        ia = S.chat_enviar({"texto": "oi"})["mensagens"][-1]
        self.assertEqual((ia["texto"], "acoes" in ia), ("Olá, Ana! Tudo certo por aqui.", False))

    def test_resposta_json_em_texto(self):
        self.resp = (200, {"service_response": {"data": '```json\n{"resposta": "Marco a luz.", "pagar": [{"id": "l-luz"}]}\n```'}})
        ia = S.chat_enviar({"texto": "paguei a luz"})["mensagens"][-1]
        self.assertEqual((ia["texto"], ia["acoes"]["pagar"][0]["id"]), ("Marco a luz.", "l-luz"))

    def test_so_acao_sem_texto(self):
        self.resp = (200, {"service_response": {"data": {"pagar": [{"id": "l-luz"}]}}})
        self.assertEqual(S.chat_enviar({"texto": "paguei a luz"})["mensagens"][-1]["texto"], "Confira e confirme.")

    def test_nada_que_preste(self):
        self.resp = (200, {"service_response": {"data": {"outra": 1}}})
        self.assertEqual(S.chat_enviar({"texto": "?"})["mensagens"][-1]["texto"], "Não entendi. Pode dizer de outro jeito?")

    def test_erros_do_home_assistant(self):
        for resp, msg in (((500, {"message": "Cota excedida"}), "Cota excedida"), ((200, {"service_response": {}}), "não devolveu")):
            self.resp = resp
            with self.subTest(msg=msg), self.assertRaisesRegex(ValueError, msg):
                S.chat_enviar({"texto": "oi"})
        self.assertEqual(S.chat_estado()["mensagens"], [], "nada gravado")


# ---------------------------------------------------------------------------------------------------------------
class TestRotas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Servidor()

    @classmethod
    def tearDownClass(cls):
        cls.s.parar()

    def test_conversa_pela_api(self):
        self.s.post("/api/chat/limpar")
        self.assertEqual(self.s.get("/api/chat")[2], {"mensagens": []})
        st, _, r = self.s.post("/api/chat", {"texto": "gastei 30 na farmácia", "tela": "Início", "aba": "inicio"})
        self.assertEqual(st, 200)
        ia = r["mensagens"][-1]
        self.assertEqual(ia["acoes"]["lancamentos"][0]["valor"], 30)
        st, _, r = self.s.post("/api/chat/acao", {"id": ia["id"], "grupo": "lancamentos", "estado": "feito"})
        self.assertEqual((st, r["mensagens"][-1]["estado"]), (200, {"lancamentos": "feito"}))
        self.assertEqual(len(self.s.get("/api/chat")[2]["mensagens"]), 2, "guardada no servidor")
        self.assertEqual(self.s.post("/api/chat/limpar")[2], {"mensagens": []})

    def test_erros(self):
        self.assertEqual(self.s.post("/api/chat", {"texto": ""})[0], 400)
        self.assertEqual(self.s.post("/api/chat/acao", {"id": "x", "grupo": "pagar", "estado": "feito"})[0], 400)
        self.assertEqual(self.s.post("/api/chat/acao", {"id": "x", "grupo": "pagar.0", "estado": "feito"})[0], 404)


if __name__ == "__main__":
    unittest.main()
