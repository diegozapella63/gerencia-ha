"""1.64.0: as assinaturas em promoção (promocoes.py e o server.py): o catálogo, os aparelhos do InventarIA, a página
oficial lida e conferida (o trecho escrito na página, por tempo limitado e mais barato que o preço de sempre), a IA só
quando a página muda, o aviso no celular, na Agora e no CronologIA. Serviços, itens e preços inventados nas páginas de
mentira (Ana, TV da sala); os nomes do catálogo são os das assinaturas de verdade."""
import json
import os
import re
import tempfile
import unittest
from datetime import date
from unittest import mock

from tests.base import ServidorFalso, Servidor, importar_servidor
from tests.test_avisos import Trocar
S = importar_servidor()
import integracao  # noqa: E402
import promocoes as P  # noqa: E402

HOJE = date(2026, 11, 2)
APARELHOS_DE_VERDADE = S.promos_aparelhos  # os testes trocam por aparelhos fixos

PAGINA_PROMO = """<html><head><script>var dados = {"preco": "R$ 49,90 por m\\u00eas no plano Premium", "outro": "sem pre\\u00e7o"};</script></head><body>
<h2>Planos</h2><p>Plano Padrão: R$ 29,90 por mês</p>
<p>Oferta por tempo limitado: Padrão por R$ 9,90 por mês nos 3 primeiros meses, depois R$ 29,90, até 30/11/2099, para novos assinantes</p>
</body></html>"""
PAGINA_SO_PLANOS = "<html><body><p>Plano Básico: R$ 19,90 por mês</p><p>Plano Família: R$ 34,90 por mês</p></body></html>"
PAGINA_SEM_REAIS = "<html><body><p>Plans start at $8.99/month</p></body></html>"


class TestCatalogo(unittest.TestCase):
    def test_cada_assinatura_tem_pagina_oficial_e_onde_funciona(self):
        ids = [c["id"] for c in P.CATALOGO]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 25)
        for c in P.CATALOGO:
            self.assertTrue(c["url"].startswith("https://"), c["id"])
            self.assertTrue(set(c["onde"]) <= set(P.NOMES_APARELHO), c["id"])
            self.assertIn(c["tipo"], P.TIPOS)
            re.compile(c["padrao"])
        nomes = {c["nome"] for c in P.CATALOGO}
        self.assertTrue({"YouTube Premium", "Netflix", "Prime Video", "HBO Max", "Disney+", "Rakuten Viki", "Blacknut", "Paramount+",
                         "Crunchyroll", "GeForce NOW", "Globoplay", "Boosteroid", "Xbox Game Pass"} <= nomes, "as que o dono pediu")


class TestAparelhos(unittest.TestCase):
    ITENS = [{"nome": "TV LG 55 polegadas"}, {"nome": "Smart TV Samsung Crystal 50"}, {"nome": "Celular Moto G84"}, {"nome": "PlayStation 5"},
             {"nome": "Geladeira Samsung"}, {"nome": "iPhone 13"}, {"nome": "Fire TV Stick"}, {"nome": "Xbox Series S"}, {"nome": ""}, "lixo",
             {"nome": "Galaxy Tab A8"}, {"nome": "TV Sala TCL"}, {"nome": "Nintendo Switch OLED"}, {"nome": "Apple TV 4K"}, {"nome": "Roku Express"}]

    def test_pelos_nomes_dos_itens(self):
        a = P.aparelhos(self.ITENS)
        self.assertEqual(a, {"tv_lg": ["TV LG 55 polegadas"], "tv_samsung": ["Smart TV Samsung Crystal 50"], "android": ["Celular Moto G84", "Galaxy Tab A8"],
                             "playstation": ["PlayStation 5"], "ios": ["iPhone 13"], "fire_tv": ["Fire TV Stick"], "xbox": ["Xbox Series S"],
                             "android_tv": ["TV Sala TCL"], "switch": ["Nintendo Switch OLED"], "apple_tv": ["Apple TV 4K"], "roku": ["Roku Express"]},
                         "a geladeira Samsung não é TV")
        self.assertEqual(P.aparelhos(None), {})

    def test_as_que_funcionam_nos_aparelhos(self):
        dentro, fora = P.servicos({"tv_lg": ["TV"], "playstation": ["PS5"]})
        ids_d, ids_f = {c["id"] for c in dentro}, {c["id"] for c in fora}
        self.assertTrue({"netflix", "ps_plus", "game_pass", "geforce_now", "ea_play"} <= ids_d)
        self.assertEqual(ids_f, {"nintendo", "apple_arcade", "play_pass"}, "todo celular roda o que tem app no Android e no iPhone")
        self.assertEqual(P.servicos({})[1], [], "sem aparelhos, todas")
        self.assertEqual(P.nomes_aparelhos({"xbox": 1, "tv_samsung": 1, "android": 1}), ["TV Samsung", "Xbox", "celular (Android)"])
        self.assertEqual(P.nomes_aparelhos({"tv_lg": 1}), ["TV LG", "celular"])

    def test_quanto_ja_paga(self):
        d = {"recorrencias": [{"descricao": "Netflix", "valor": 44.9, "inicio": "2026-01", "tipo": "despesa"},
                              {"descricao": "Spotify Família", "valor": 360, "freq": "anual", "inicio": "2026-03", "tipo": "despesa"},
                              {"descricao": "Disney+", "valor": 30, "inicio": "2025-01", "fim": "2026-05", "tipo": "despesa"},
                              {"descricao": "Netflix (reembolso)", "valor": 10, "inicio": "2026-01", "tipo": "receita"}, "x"]}
        self.assertEqual(P.de_quem_paga(d, HOJE), {"netflix": 44.9, "spotify": 30.0}, "o anual por mês; o que acabou e a receita ficam de fora")


class TestPagina(unittest.TestCase):
    def test_texto_com_os_precos_do_javascript(self):
        t = P.texto_pagina(PAGINA_PROMO)
        self.assertIn("Plano Padrão: R$ 29,90 por mês", t)
        self.assertIn("R$ 49,90 por mês no plano Premium", t, "o preço que vem num JSON dentro do <script>")
        self.assertNotIn("sem preço", t)
        self.assertEqual(P.texto_pagina('<script>{"a": "R$ 1,00", "b": "R$ \\x"}</script><p>R$ 1,00</p>').count("R$ 1,00"), 1, "sem repetir")
        self.assertEqual(len(P.texto_pagina("<script>" + ",".join(f'"R$ {i},00"' for i in range(200)) + "</script>", max_extras=5).splitlines()), 5)
        self.assertTrue(P.trechos(t))
        self.assertEqual(P.trechos(P.texto_pagina(PAGINA_SEM_REAIS)), "")
        self.assertEqual(P.assinatura_trechos("A  b"), P.assinatura_trechos("a b"))
        self.assertIn("Netflix", P.prompt(P.POR_ID["netflix"], "R$ 1"))


TEXTO = ("Planos\nPlano Padrão: R$ 29,90 por mês\nPlano Premium: R$ 49,90 por mês\nAnual: 12x R$ 22,90 por mês. Compromisso de 12 meses\n"
         "Oferta por tempo limitado: Padrão por R$ 9,90 por mês nos 3 primeiros meses, depois R$ 29,90, até 30/11/2026, para novos assinantes\n"
         "Black Friday: 3 meses por R$ 59,70 no Premium\nAssine por apenas R$ 29,90 por mês")


class TestLimpar(unittest.TestCase):
    def promo(self, **x):
        base = {"plano": "Padrão", "preco": 9.9, "meses": 3, "depois": 29.9, "ate": "2026-11-30", "quem": "novos assinantes",
                "trecho": "Padrão por R$ 9,90 por mês nos 3 primeiros meses"}
        base.update(x)
        return base

    def limpar(self, promos, planos=None, **kw):
        planos = planos if planos is not None else [{"plano": "Padrão", "mensal": 29.9, "trecho": "Plano Padrão: R$ 29,90 por mês"}]
        return P.limpar({"planos": planos, "promocoes": promos}, TEXTO, HOJE, **kw)

    def test_a_promocao_conferida(self):
        lido, rec = self.limpar([self.promo()])
        self.assertEqual(rec, 0)
        self.assertEqual(lido["planos"], [{"plano": "Padrão", "mensal": 29.9}])
        self.assertEqual(lido["promocoes"], [{"plano": "Padrão", "preco": 9.9, "meses": 3, "normal": 29.9, "ate": "2026-11-30", "quem": "novos assinantes",
                                              "trecho": "Padrão por R$ 9,90 por mês nos 3 primeiros meses"}])

    def test_o_que_nao_vale(self):
        lido, rec = self.limpar([
            self.promo(trecho="Padrão por R$ 7,90 por mês", preco=7.9),                       # não está escrito
            self.promo(trecho="12x R$ 22,90 por mês", preco=22.9, meses=12, depois=0),       # o anual de sempre: nada diz que é por tempo limitado
            self.promo(trecho="Assine por apenas R$ 29,90 por mês", preco=29.9, meses=0, depois=0, ate=""),  # não é mais barato
            self.promo(ate="2026-10-01"),                                                     # já acabou
            "lixo", self.promo(preco=0, total=0)])
        self.assertEqual(lido["promocoes"], [])
        self.assertEqual(rec, 2, "o trecho que não está na página e o preço zero")

    def test_o_total_a_data_e_quem_conferidos(self):
        lido, _ = self.limpar([self.promo(plano="Premium", preco=0, total=59.7, meses=3, depois=0, ate="2026-12-31", quem="todo mundo",
                                          trecho="Black Friday: 3 meses por R$ 59,70 no Premium")],
                              planos=[{"plano": "Premium", "mensal": 49.9, "trecho": "Plano Premium: R$ 49,90 por mês"}])
        self.assertEqual(lido["promocoes"], [{"plano": "Premium", "preco": 19.9, "meses": 3, "normal": 49.9, "ate": "", "quem": "",
                                              "trecho": "Black Friday: 3 meses por R$ 59,70 no Premium", "total": 59.7}],
                         "o total dividido pelos meses; a data e o quem que não estão escritos saem")

    def test_o_preco_de_sempre_de_antes_e_os_repetidos(self):
        lido, _ = self.limpar([self.promo(depois=0), self.promo(depois=0)], planos=[], antes={"padrao": 29.9})
        self.assertEqual([(x["normal"], x["preco"]) for x in lido["promocoes"]], [(29.9, 9.9)], "o preço de sempre da leitura anterior; sem repetir")
        lido, _ = self.limpar([self.promo(depois=0, plano="Outro")], planos=[])
        self.assertEqual(lido["promocoes"][0]["normal"], 0, "sem saber o preço de sempre, vale pelo tempo limitado")
        lido, rec = self.limpar([], planos=[{"plano": "X", "mensal": 5, "trecho": "não está"}, {"plano": "Padrão", "mensal": 29.9, "trecho": "Plano Padrão: R$ 29,90"},
                                            {"plano": "padrão", "mensal": 29.9, "trecho": "Plano Padrão: R$ 29,90"}, {"plano": "Y", "mensal": 0}, "z"])
        self.assertEqual((lido["planos"], rec), ([{"plano": "Padrão", "mensal": 29.9}], 1))
        self.assertEqual(P.limpar(None, "", HOJE), ({"planos": [], "promocoes": []}, 0))

    def test_textos_e_ids(self):
        x = {"plano": "Padrão", "preco": 9.9, "meses": 3, "normal": 29.9}
        self.assertEqual(P.linha("HBO Max", x), "HBO Max: R$ 9,90 por mês por 3 meses (depois R$ 29,90)")
        self.assertEqual(P.linha("X", {"preco": 5, "meses": 1}), "X: R$ 5,00 por mês por 1 mês")
        self.assertEqual(P.id_promo("hbo_max", x), P.id_promo("hbo_max", dict(x, plano="padrao")))
        self.assertNotEqual(P.id_promo("hbo_max", x), P.id_promo("hbo_max", dict(x, preco=8.9)))
        self.assertEqual(P.valendo({"promocoes": [{"ate": "2026-11-01"}, {"ate": ""}, {"ate": "2026-12-01"}]}, HOJE), [{"ate": ""}, {"ate": "2026-12-01"}])
        self.assertEqual(P.valendo(None), [])

    def test_a_ia_simulada(self):
        r = P.simulados(TEXTO)
        self.assertEqual([p["plano"] for p in r["planos"]], ["Padrão", "Premium"])
        self.assertEqual(r["promocoes"], [{"plano": "Padrão", "preco": 9.9, "meses": 3, "depois": 29.9, "ate": "2026-11-30", "quem": "novos assinantes",
                                           "trecho": TEXTO.splitlines()[4][:160]}])


class AvisosFalso:
    def __init__(self):
        self.enviados = []

    def pessoas(self, forcar=False):
        return [{"id": "person.ana", "nome": "Ana", "user_id": "u-ana", "celulares": ["mobile_app_ana"]}]

    def enviar(self, alvos, texto, tag, grupo="gerencia-dicas", canal="Dicas de economia", caminho=""):
        self.enviados.append((alvos, texto, tag, caminho))
        return len(alvos)


class TestServidor(unittest.TestCase):
    def setUp(self):
        if os.path.exists(S.ARQ):
            os.remove(S.ARQ)
        self.falso = ServidorFalso({"/netflix": (200, PAGINA_PROMO), "/hbo_max": (200, PAGINA_SO_PLANOS), "/paramount": (200, PAGINA_SEM_REAIS)})
        self.addCleanup(self.falso.fechar)
        self.av = AvisosFalso()
        arq = os.path.join(tempfile.mkdtemp(), "promocoes.json")
        Trocar(self, IA_MOCK=True, PROMOS_BASE=self.falso.url + "/", PROMOS_ARQ=arq, AVISOS=self.av,
               promos_aparelhos=lambda d: ({"tv_lg": ["TV da sala"], "playstation": ["PS5"]}, True))
        d = S.ler()
        d["ajustes"].update(dicas_aviso=True, dicas_para=["person.ana"])
        d["recorrencias"] = [{"id": "r1", "descricao": "Netflix", "valor": 44.9, "inicio": "2026-01", "tipo": "despesa", "dia": 5}]
        S.salvar(d)

    def test_confere_avisa_e_mostra(self):
        S._conferir_promos(avisar=True)
        est = S.promos_estado(S.ler(), disparar=False)
        self.assertTrue(est["ligado"] and est["inventaria"])
        self.assertEqual(est["aparelhos"], ["TV LG", "PlayStation", "celular"])
        self.assertEqual(set(est["fora"]), {"Nintendo Switch Online", "Apple Arcade", "Google Play Pass"})
        st = {x["id"]: x["status"] for x in est["servicos"]}
        self.assertEqual((st["netflix"], st["hbo_max"], st["paramount"], st["disney"]), ("ok", "ok", "sem_precos", "sem_acesso"))
        self.assertEqual(len(est["promocoes"]), 1)
        p = est["promocoes"][0]
        self.assertEqual((p["nome"], p["preco"], p["meses"], p["normal"], p["quem"], p["paga"], p["visto"], p["url"]),
                         ("Netflix", 9.9, 3, 29.9, "novos assinantes", 44.9, date.today().isoformat(), P.POR_ID["netflix"]["url"]),
                         "a página que abre no toque é a oficial; você paga vem dos fixos")
        self.assertEqual(len(self.av.enviados), 1)
        alvos, texto, tag, caminho = self.av.enviados[0]
        self.assertEqual((alvos, texto["title"], texto["message"], tag, caminho),
                         (["mobile_app_ana"], "🏷️ Assinatura em promoção", "• Netflix: R$ 9,90 por mês por 3 meses (depois R$ 29,90)",
                          "gerencia-promocoes", "/promocoes"))
        self.assertEqual(S.avisar_promos(S.ler()), 0, "cada promoção, uma vez")
        # a CronologIA e a Agora: a dos últimos 7 dias
        rec = S.promos_recentes(S.ler())
        av = integracao.avisos(S.ler(), [], date.today(), rec)
        self.assertIn({"id": "promocoes", "tipo": "beneficio", "caminho": "/beneficios", "titulo": "Assinatura em promoção",
                       "texto": "Netflix: R$ 9,90 por mês por 3 meses"}, av)

    def test_a_ia_so_le_a_pagina_que_mudou(self):
        S._conferir_promos()
        with mock.patch.object(P, "simulados", wraps=P.simulados) as sim:
            S._conferir_promos()
            self.assertEqual(sim.call_count, 0, "lidas hoje: nem abre")
            S._conferir_promos(forcar=True)
            self.assertEqual(sim.call_count, 0, "abriu de novo, mas os preços são os mesmos: sem a IA")
            self.falso.rotas["/netflix"] = (200, PAGINA_PROMO.replace("R$ 9,90", "R$ 8,90"))
            S._conferir_promos(forcar=True)
            self.assertEqual(sim.call_count, 1, "a página mudou: a IA lê")
        self.assertEqual(S.promos_estado(S.ler(), disparar=False)["promocoes"][0]["preco"], 8.9)
        with mock.patch.object(P, "simulados", side_effect=ValueError("caiu")):
            self.falso.rotas["/netflix"] = (200, PAGINA_PROMO.replace("R$ 9,90", "R$ 7,90"))
            S._conferir_promos(forcar=True)
        lidas = S.promos_ler()["servicos"]
        self.assertEqual((lidas["netflix"]["status"], lidas["netflix"]["planos"]), ("erro_ia", [{"plano": "Padrão", "mensal": 29.9}]),
                         "a IA falhou: guarda os preços de sempre")
        with mock.patch.object(P, "simulados", return_value={"planos": [{"plano": "X", "mensal": 5, "trecho": "não está"}]}):
            self.falso.rotas["/netflix"] = (200, PAGINA_PROMO.replace("R$ 9,90", "R$ 6,90"))
            S._conferir_promos(forcar=True)
        self.assertEqual(S.promos_ler()["servicos"]["netflix"]["status"], "nao_confere")

    def test_ia_de_verdade(self):
        pedidos = []

        def chamar(tipo, payload, n, timeout=None):
            pedidos.append((tipo, payload))
            return {"service_response": {"data": json.dumps(P.simulados(P.texto_pagina(PAGINA_PROMO)))}}
        Trocar(self, IA_MOCK=False, ia_disponivel=lambda d: True, ia_chamar=chamar)
        d = S.ler()
        d["ajustes"]["ia_entidade"] = "ai_task.casa"
        lida = S.ler_pagina_promo(P.POR_ID["netflix"], d)
        self.assertEqual((lida["status"], len(lida["promocoes"])), ("ok", 1))
        self.assertEqual((pedidos[0][0], pedidos[0][1]["task_name"], pedidos[0][1]["entity_id"]), ("promocoes", "GerencIA: promoções de Netflix", "ai_task.casa"))
        Trocar(self, ia_chamar=lambda *a, **k: {})
        self.assertEqual(S.ler_pagina_promo(P.POR_ID["netflix"], d)["status"], "erro_ia", "a IA sem resposta")
        Trocar(self, ia_disponivel=lambda d: False)
        self.assertEqual(S.ler_pagina_promo(P.POR_ID["netflix"], d, {"planos": [{"plano": "A", "mensal": 1}]}),
                         {"em": mock.ANY, "status": "sem_ia", "planos": [{"plano": "A", "mensal": 1}], "promocoes": []}, "sem IA, nem abre a página")

    def test_desligado_sem_ia_ou_sem_dicas(self):
        for aj in ({"ia": False}, {"dicas": False}):
            d = S.ler()
            d["ajustes"].update(aj)
            S.salvar(d)
            self.assertEqual(S.promos_estado(S.ler()), {"ligado": False}, aj)
            self.assertEqual(S.promos_recentes(S.ler()), [])
            self.assertEqual(S.avisar_promos(S.ler()), 0)
            self.assertFalse(S.promos_vez(S.ler()))
            S._conferir_promos()
            self.assertEqual(S.promos_ler(), {}, "nem confere")
            d = S.ler()
            d["ajustes"].update(ia=True, dicas=True)
            S.salvar(d)

    def test_sem_aviso_ligado_so_anota_e_quem_nao_tem_celular(self):
        d = S.ler()
        d["ajustes"]["dicas_aviso"] = False
        S.salvar(d)
        S._conferir_promos(avisar=True)
        self.assertEqual(self.av.enviados, [])
        self.assertEqual(len(S.promos_ler()["avisadas"]), 1, "anotada: ligando depois, não chega a antiga")
        Trocar(self, _celulares_de=lambda para: (_ for _ in ()).throw(RuntimeError("sem HA")))
        c = S.promos_ler()
        c["avisadas"] = {}
        S.promos_gravar(c)
        d["ajustes"]["dicas_aviso"] = True
        S.salvar(d)
        self.assertEqual(S.avisar_promos(S.ler()), 0, "sem ver as pessoas: tenta de novo depois")

    def test_uma_vez_por_dia_no_horario_das_dicas(self):
        chamadas = []
        Trocar(self, iniciar_promos=lambda **k: chamadas.append(k) or True, hora_das_dicas=lambda d: True)
        self.assertTrue(S.promos_vez(S.ler()))
        self.assertEqual(chamadas, [{"avisar": True}])
        c = S.promos_ler()
        c["dia"] = date.today().isoformat()
        S.promos_gravar(c)
        self.assertFalse(S.promos_vez(S.ler()), "hoje já foi")
        Trocar(self, hora_das_dicas=lambda d: False)
        c["dia"] = ""
        S.promos_gravar(c)
        self.assertFalse(S.promos_vez(S.ler()), "antes do horário")

    def test_iniciar_e_velhas(self):
        S._promos_conferindo.set()
        self.assertFalse(S.iniciar_promos(), "já está conferindo")
        S._promos_conferindo.clear()
        self.assertTrue(S.iniciar_promos(esperar=True))
        self.assertFalse(S._promos_conferindo.is_set())
        self.assertTrue(S._promo_velha(None))
        self.assertTrue(S._promo_velha({"em": S.agora_iso(), "status": "ok"}, forcar=True))
        self.assertFalse(S._promo_velha({"em": S.agora_iso(), "status": "ok"}))
        self.assertTrue(S._promo_velha({"em": "2020-01-01T10:00:00", "status": "ok"}))
        self.assertFalse(S._promo_velha({"em": S.agora_iso(), "status": "sem_acesso"}), "o erro espera 6 horas")
        self.assertTrue(S._promo_velha({"em": "2020-01-01T10:00:00", "status": "sem_acesso"}))
        est = S.promos_estado(S.ler())
        self.assertTrue(est["ligado"])
        with open(S.PROMOS_ARQ, "w") as f:
            f.write("[]")
        self.assertEqual(S.promos_ler(), {})

    def test_os_aparelhos_do_inventaria(self):
        Trocar(self, promos_aparelhos=APARELHOS_DE_VERDADE)
        d = S.ler()
        with mock.patch.object(S.BENS, "ler", return_value={"itens": [{"nome": "Xbox Series S"}]}):
            self.assertEqual(S.promos_aparelhos(d), ({"xbox": ["Xbox Series S"]}, True))
        with mock.patch.object(S.BENS, "ler", side_effect=RuntimeError("sem InventarIA")):
            self.assertEqual(S.promos_aparelhos(d), ({}, False))
        d["ajustes"]["bens"] = False
        self.assertEqual(S.promos_aparelhos(d), ({}, False), "Somar os bens desligado: sem o InventarIA")

    def test_erro_ao_conferir_nao_derruba(self):
        Trocar(self, ler=lambda: (_ for _ in ()).throw(RuntimeError("disco")))
        S._conferir_promos(avisar=True)
        self.assertFalse(S._promos_conferindo.is_set())


class TestRota(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Servidor()

    @classmethod
    def tearDownClass(cls):
        cls.srv.parar()

    def test_estado_e_conferir(self):
        st, _, r = self.srv.get("/api/promocoes")
        self.assertEqual((st, r["ligado"]), (200, True))
        self.assertEqual(len(r["servicos"]), len(P.CATALOGO), "sem o InventarIA, todas")
        st, _, r = self.srv.post("/api/promocoes/conferir", {})
        self.assertEqual(st, 200)
        self.assertIn("conferindo", r)
