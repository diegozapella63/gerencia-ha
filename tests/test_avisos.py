"""Dicas de economia sozinhas e o aviso no celular (avisos.py e as partes do server.py), como o aviso de prazos do
ResolvIA: conferir no horário escolhido, os celulares de cada pessoa da casa (pelo aparelho do app Home Assistant,
não pelo nome do rastreador), quem recebe, cada dica avisada uma vez, Testar e o que muda com tudo desligado.
O Home Assistant é de mentira; pessoas, aparelhos e valores inventados (Ana, Beto)."""
import os
import unittest
from datetime import date, datetime
from unittest import mock

from tests.base import ServidorFalso, importar_servidor, INDICES
S = importar_servidor()
import avisos as A  # noqa: E402  (o importar_servidor põe gerencia/app no caminho)
import calc  # noqa: E402

FONTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "e2e", "fixtures", "fontes")

# o Home Assistant: a Ana tem um Pixel (rastreador com outro nome) e um relógio; o Beto, só o rastreador do roteador
ESTADOS = [
    {"entity_id": "person.ana", "attributes": {"friendly_name": "Ana", "user_id": "u-ana", "device_trackers": ["device_tracker.meu_celular", "device_tracker.relogio"]}},
    {"entity_id": "person.beto", "attributes": {"friendly_name": "Beto", "user_id": "u-beto", "device_trackers": ["device_tracker.roteador_beto"]}},
    {"entity_id": "sensor.qualquer", "attributes": {}},
]
SERVICOS = [{"domain": "light", "services": {"turn_on": {}}},
            {"domain": "notify", "services": {"mobile_app_pixel_8": {}, "mobile_app_relogio_da_ana": {}, "notify": {}, "mobile_app_outro": {}}}]
ENTIDADES = {"entities": [{"ei": "device_tracker.meu_celular", "di": "d1"}, {"ei": "device_tracker.relogio", "di": "d2"},
                          {"ei": "device_tracker.roteador_beto", "di": "d3"}, {"ei": "light.sala", "di": "d4"}]}
APARELHOS = [{"id": "d1", "name": "Pixel 8", "identifiers": [["mobile_app", "abc"]]},
             {"id": "d2", "name": "Relógio da Ana", "identifiers": [["mobile_app", "def"]]},
             {"id": "d3", "name": "Roteador", "identifiers": [["unifi", "x"]]}]


class Trocar:
    def __init__(self, caso, **mudar):
        self.antes = {k: getattr(S, k) for k in mudar}
        for k, v in mudar.items():
            setattr(S, k, v)
        caso.addCleanup(lambda: [setattr(S, k, v) for k, v in self.antes.items()])


def ha_falso(enviados=None, falha=()):
    """O rest(metodo, caminho, corpo) de um Home Assistant de mentira; os avisos mandados vão para a lista enviados."""
    def rest(metodo, caminho, corpo=None):
        if caminho == "/states":
            return ESTADOS
        if caminho == "/services":
            return SERVICOS
        if caminho.startswith("/services/notify/"):
            alvo = caminho.rsplit("/", 1)[1]
            if alvo in falha:
                raise S.ErroHA("recusado")
            if enviados is not None:
                enviados.append((alvo, corpo))
            return []
        raise AssertionError(caminho)
    return rest


def ws_falso(comando):
    return {"config/entity_registry/list_for_display": ENTIDADES, "config/device_registry/list": APARELHOS}[comando["type"]]


# ---------------------------------------------------------------------------------------------------------------
class TestCelulares(unittest.TestCase):
    def test_slug_como_o_home_assistant(self):
        self.assertEqual(A.slug("Relógio da Ana"), "relogio_da_ana")
        self.assertEqual(A.slug("  Pixel-8 (Ana) "), "pixel_8_ana")
        self.assertEqual(A.slug(None), "")

    def test_aparelho_de_cada_rastreador(self):
        ap = A.aparelhos(ENTIDADES, APARELHOS)
        self.assertEqual(ap["device_tracker.meu_celular"], {"nome": "Pixel 8", "app": True})
        self.assertEqual(ap["device_tracker.roteador_beto"], {"nome": "Roteador", "app": False})
        self.assertNotIn("light.sala", ap)
        self.assertIsNone(A.aparelhos(None, APARELHOS), "sem os registros")
        self.assertEqual(A.aparelhos({"entities": [{"ei": "device_tracker.x"}]}, []), {"device_tracker.x": None})

    def test_o_celular_pelo_aparelho_nao_pelo_rastreador(self):
        servicos = {"mobile_app_pixel_8", "mobile_app_relogio_da_ana", "mobile_app_meu_celular"}
        ap = A.aparelhos(ENTIDADES, APARELHOS)
        self.assertEqual(A.celulares(["device_tracker.meu_celular", "device_tracker.relogio"], servicos, ap),
                         ["mobile_app_pixel_8", "mobile_app_relogio_da_ana"])
        self.assertEqual(A.celulares(["device_tracker.roteador_beto"], servicos | {"mobile_app_roteador_beto"}, ap), [],
                         "o rastreador do roteador não é celular")

    def test_sem_os_registros_pelo_id_do_rastreador(self):
        self.assertEqual(A.celulares(["device_tracker.pixel_8", "device_tracker.pixel_8"], {"mobile_app_pixel_8"}), ["mobile_app_pixel_8"])
        self.assertEqual(A.celulares(["device_tracker.nao_tem"], {"mobile_app_pixel_8"}), [])
        self.assertEqual(A.celulares(None, {"mobile_app_pixel_8"}), [])

    def test_endereco_do_app_para_o_toque(self):
        self.assertEqual(A.endereco_app("a1b2c3d4-gerencia"), "/app/a1b2c3d4_gerencia")
        self.assertIsNone(A.endereco_app("meu-computador"))
        with mock.patch.dict(os.environ, {"GERENCIA_HOST": "e5f6a7b8-gerencia"}):
            self.assertEqual(A.endereco_app(), "/app/e5f6a7b8_gerencia", "o mesmo caminho do Atalho no celular (GERENCIA_HOST nos testes)")

    def test_texto_do_aviso(self):
        um = A.texto_dicas([{"nome": "Spotify", "real": 31.4}])
        self.assertEqual(um, {"title": "💡 Dica de economia", "message": "• Spotify: R$ 31 por ano no plano anual"})
        varias = A.texto_dicas([{"nome": f"S{k}", "real": 100 - k} for k in range(7)])
        self.assertEqual(varias["title"], "💡 Dicas de economia: 7")
        self.assertEqual(varias["message"].splitlines()[-1], "e mais 2")
        self.assertEqual(len(varias["message"].splitlines()), 6)


class TestPessoas(unittest.TestCase):
    def test_pessoas_e_celulares(self):
        av = A.Avisos(ha_falso(), ws_falso, lambda *a: None)
        p = av.pessoas()
        self.assertEqual([(x["id"], x["nome"], x["user_id"], x["celulares"]) for x in p], [
            ("person.ana", "Ana", "u-ana", ["mobile_app_pixel_8", "mobile_app_relogio_da_ana"]),
            ("person.beto", "Beto", "u-beto", [])])

    def test_guarda_por_um_minuto(self):
        chamadas = []
        rest = ha_falso()
        av = A.Avisos(lambda m, c, b=None: (chamadas.append(c), rest(m, c, b))[1], ws_falso, lambda *a: None)
        av.pessoas()
        av.pessoas()
        self.assertEqual(chamadas.count("/states"), 1)
        av.pessoas(forcar=True)
        self.assertEqual(chamadas.count("/states"), 2)

    def test_sem_os_registros_segue_pelo_rastreador(self):
        def ws_quebrado(comando):
            raise OSError("fora")
        log = []
        av = A.Avisos(ha_falso(), ws_quebrado, lambda *a: log.append(a))
        self.assertEqual(av.pessoas()[0]["celulares"], [], "meu_celular não tem mobile_app_meu_celular")
        self.assertTrue(log)

    def test_enviar(self):
        enviados = []
        av = A.Avisos(ha_falso(enviados, falha={"mobile_app_relogio_da_ana"}), ws_falso, lambda *a: None)
        with mock.patch.object(A, "endereco_app", return_value="/app/x_gerencia"):
            n = av.enviar(["mobile_app_pixel_8", "mobile_app_relogio_da_ana"], {"title": "T", "message": "M"}, "gerencia-dicas")
        self.assertEqual(n, 1, "só o que o Home Assistant aceitou")
        alvo, corpo = enviados[0]
        self.assertEqual(alvo, "mobile_app_pixel_8")
        self.assertEqual(corpo["title"], "GerencIA · T", "o nome do app na frente, como em todos os apps da família")
        self.assertEqual(corpo["data"], {"tag": "gerencia-dicas", "group": "gerencia-dicas", "channel": "Dicas de economia", "notification_icon": "mdi:wallet-outline",
                                         "url": "/app/x_gerencia", "clickAction": "/app/x_gerencia"})
        self.assertEqual((A.titulo_do_app("GerencIA · T"), A.titulo_do_app("")), ("GerencIA · T", "GerencIA"), "uma vez só")


# ---------------------------------------------------------------------------------------------------------------
class TestAjustes(unittest.TestCase):
    def test_padrao(self):
        a = S.vazio()["ajustes"]
        self.assertEqual((a["dicas_auto"], a["dicas_hora"], a["dicas_aviso"], a["dicas_para"]), (True, "08:00", False, []))
        self.assertEqual(a["dicas_freq"], "mes", "todo mês, como antes")

    def test_frequencia(self):
        d = S.vazio()
        for f, dias in (("semana", 7), ("quinzena", 15), ("mes", 30)):
            d["ajustes"]["dicas_freq"] = f
            self.assertEqual(S.dias_dicas(S.normalizar(d)), dias)
        d["ajustes"]["dicas_freq"] = "ano"
        self.assertEqual(S.normalizar(d)["ajustes"]["dicas_freq"], "mes")

    def test_limpa_o_que_chega(self):
        d = S.vazio()
        d["ajustes"].update(dicas_auto=0, dicas_hora="25:00", dicas_aviso="sim", dicas_para=["person.ana", "person.ana", "luz.sala", 3, "person.beto"])
        a = S.normalizar(d)["ajustes"]
        self.assertEqual((a["dicas_auto"], a["dicas_hora"], a["dicas_aviso"], a["dicas_para"]), (True, "08:00", False, ["person.ana", "person.beto"]))
        d["ajustes"].update(dicas_auto=False, dicas_hora="21:30", dicas_aviso=True, dicas_para="person.ana")
        a = S.normalizar(d)["ajustes"]
        self.assertEqual((a["dicas_auto"], a["dicas_hora"], a["dicas_aviso"], a["dicas_para"]), (False, "21:30", True, []))

    def test_hora_das_dicas(self):
        d = S.vazio()
        d["ajustes"]["dicas_hora"] = "08:30"
        self.assertFalse(S.hora_das_dicas(d, datetime(2026, 11, 2, 8, 29)))
        self.assertTrue(S.hora_das_dicas(d, datetime(2026, 11, 2, 8, 30)))
        self.assertTrue(S.hora_das_dicas(d, datetime(2026, 11, 2, 23, 0)))


class TestConferirSozinho(unittest.TestCase):
    """Uma assinatura nova é conferida logo; o preço mais velho que a frequência (toda semana, a cada 15 dias ou todo
    mês), a partir das 8h; desligado, só no Conferir agora."""

    def setUp(self):
        Trocar(self, FONTES_MOCK=FONTES, IA_MOCK=True, DOLAR_FIXO="5.04")
        self.d = S.vazio()
        self.d["recorrencias"] = [{"id": "r-sp", "tipo": "despesa", "descricao": "Spotify", "valor": 23.9, "dia": 22}]
        if os.path.exists(S.DICAS_ARQ):
            os.remove(S.DICAS_ARQ)
        self.conf = mock.patch.object(S, "iniciar_conferencia").start()
        self.addCleanup(mock.patch.stopall)

    def velha(self):
        S.gravar_arquivo(S.DICAS_ARQ, S.json.dumps({"fontes": {"spotify": {"conferido": "2026-01-01", "status": "ok", "planos": []}}, "atualizado": "2026-01-01T08:00:00"}))

    def test_assinatura_nova_confere_logo(self):
        with mock.patch.object(S, "hora_das_dicas", return_value=False):
            S.dicas_estado(self.d)
        self.conf.assert_called_once_with()

    def test_mais_de_30_dias_espera_o_horario(self):
        self.velha()
        with mock.patch.object(S, "hora_das_dicas", return_value=False):
            S.dicas_estado(self.d)
        self.conf.assert_not_called()
        self.assertEqual(S.dicas_ler()["atualizado"], "2026-01-01T08:00:00", "a procura do dia também espera")
        with mock.patch.object(S, "hora_das_dicas", return_value=True):
            S.dicas_estado(self.d)
        self.conf.assert_called_once_with()

    def test_preco_vale_o_tempo_escolhido(self):
        """Conferido há 10 dias: toda semana confere de novo; a cada 15 dias e todo mês, ainda não."""
        from datetime import timedelta
        dez = (date.today() - timedelta(days=10)).isoformat()
        for freq, confere in (("semana", True), ("quinzena", False), ("mes", False)):
            with self.subTest(freq=freq):
                self.conf.reset_mock()
                S.gravar_arquivo(S.DICAS_ARQ, S.json.dumps({"fontes": {"spotify": {"conferido": dez, "status": "ok", "planos": []}},
                                                            "atualizado": date.today().isoformat() + "T08:00:00"}))
                self.d["ajustes"]["dicas_freq"] = freq
                with mock.patch.object(S, "hora_das_dicas", return_value=True):
                    S.dicas_estado(self.d)
                self.assertEqual(self.conf.called, confere)

    def test_velha(self):
        ok = lambda dias: {"conferido": (date.today() - __import__("datetime").timedelta(days=dias)).isoformat(), "status": "ok"}
        self.assertTrue(S._velha(ok(7), dias_ok=7))
        self.assertFalse(S._velha(ok(6), dias_ok=7))
        self.assertFalse(S._velha(ok(29)), "sem dizer: 30 dias")
        self.assertTrue(S._velha({"conferido": ok(1)["conferido"], "status": "erro"}, dias_ok=30), "um erro tenta de novo no dia seguinte")

    def test_desligado_so_no_conferir_agora(self):
        self.d["ajustes"]["dicas_auto"] = False
        with mock.patch.object(S, "hora_das_dicas", return_value=True):
            r = S.dicas_estado(self.d)
        self.conf.assert_not_called()
        self.assertEqual((r["auto"], r["freq"]), (False, "mes"))

    def test_procura_do_dia_no_horario(self):
        S.gravar_arquivo(S.DICAS_ARQ, S.json.dumps({"fontes": {"spotify": {"conferido": date.today().isoformat(), "status": "ok", "planos": []}},
                                                    "atualizado": "2026-01-01T08:00:00"}))
        with mock.patch.object(S, "hora_das_dicas", return_value=True):
            S.dicas_estado(self.d)
        self.conf.assert_not_called()
        self.assertEqual(S.dicas_ler()["atualizado"][:10], date.today().isoformat())


# ---------------------------------------------------------------------------------------------------------------
DICA_SP = {"id": "anual:r:r-sp", "nome": "Spotify", "servico": "spotify", "valor": 23.9, "preco_anual": 239.0, "economia_ano": 47.8}
DICA_NB = {"id": "anual:r:r-nb", "nome": "Nabu Casa", "servico": "nabucasa", "valor": 35.1, "preco_anual": 330.0, "economia_ano": 91.2}


class TestQueValem(unittest.TestCase):
    def test_so_as_que_economizam_de_verdade(self):
        d = S.vazio()
        d["indices"] = dict(INDICES)
        ruim = {**DICA_SP, "id": "anual:x", "preco_anual": 23.9 * 12 - 5}  # R$ 5 de desconto: o dinheiro rendendo daria mais
        with mock.patch.object(S, "dicas_estado", return_value={"dicas": [DICA_SP, ruim, DICA_NB]}):
            r = S.dicas_que_valem(d)
        self.assertEqual([x["id"] for x in r], ["anual:r:r-nb", "anual:r:r-sp"], "a maior primeiro, sem a que não vale")
        reserva = calc.renda_reserva(d)
        self.assertAlmostEqual(r[1]["real"], calc.economia_real(23.9, 239.0, reserva)["real"])

    def test_dispensadas_ficam_fora(self):
        d = S.vazio()
        d["ajustes"]["dicas_fora"] = ["anual:r:r-sp"]
        with mock.patch.object(S, "dicas_estado", return_value={"dicas": [DICA_SP, DICA_NB]}):
            self.assertEqual([x["id"] for x in S.dicas_que_valem(d)], ["anual:r:r-nb"])


class TestAvisarDicas(unittest.TestCase):
    def setUp(self):
        if os.path.exists(S.DICAS_ARQ):
            os.remove(S.DICAS_ARQ)
        self.enviados = []
        Trocar(self, AVISOS=A.Avisos(ha_falso(self.enviados), ws_falso, lambda *a: None), IA_MOCK=True)
        self.d = S.vazio()
        self.d["ajustes"].update(dicas_aviso=True, dicas_para=["person.ana"])
        self.dicas = [dict(DICA_SP, real=40.0)]
        mock.patch.object(S, "dicas_que_valem", side_effect=lambda d, est=None: list(self.dicas)).start()
        self.addCleanup(mock.patch.stopall)

    def test_dica_nova_vai_para_os_celulares_de_quem_foi_escolhido(self):
        self.assertEqual(S.avisar_dicas(self.d), 2, "os dois celulares da Ana")
        self.assertEqual([a for a, _ in self.enviados], ["mobile_app_pixel_8", "mobile_app_relogio_da_ana"])
        self.assertEqual(self.enviados[0][1]["title"], "GerencIA · 💡 Dica de economia")
        self.assertIn("Spotify: R$ 40 por ano no plano anual", self.enviados[0][1]["message"])
        self.assertEqual(S.dicas_ler()["avisadas"], {"anual:r:r-sp": date.today().isoformat()})

    def test_cada_dica_uma_vez(self):
        S.avisar_dicas(self.d)
        self.assertEqual(S.avisar_dicas(self.d), 0)
        self.dicas.append(dict(DICA_NB, real=80.0))
        S.avisar_dicas(self.d)
        self.assertIn("Nabu Casa", self.enviados[-1][1]["message"])
        self.assertNotIn("Spotify", self.enviados[-1][1]["message"], "só a nova")

    def test_dica_que_some_e_volta_avisa_de_novo(self):
        S.avisar_dicas(self.d)
        self.dicas.clear()
        S.avisar_dicas(self.d)
        self.assertEqual(S.dicas_ler()["avisadas"], {})
        self.dicas.append(dict(DICA_SP, real=40.0))
        self.assertEqual(S.avisar_dicas(self.d), 2)

    def test_conferir_agora_so_anota(self):
        self.assertEqual(S.avisar_dicas(self.d, silencioso=True), 0)
        self.assertEqual(self.enviados, [])
        self.assertEqual(S.avisar_dicas(self.d), 0, "já anotada: não avisa depois")

    def test_aviso_desligado_anota_sem_mandar(self):
        """Ligar o aviso depois não manda as dicas antigas de uma vez."""
        self.d["ajustes"]["dicas_aviso"] = False
        self.assertEqual(S.avisar_dicas(self.d), 0)
        self.assertIn("anual:r:r-sp", S.dicas_ler()["avisadas"])

    def test_ninguem_ou_sem_celular(self):
        self.d["ajustes"]["dicas_para"] = ["person.beto"]
        self.assertEqual(S.avisar_dicas(self.d), 0)
        self.assertEqual(self.enviados, [])

    def test_dicas_ou_ia_desligadas_nem_olha(self):
        for k in ("dicas", "ia"):
            with self.subTest(k=k):
                d = S.vazio()
                d["ajustes"].update(dicas_aviso=True, dicas_para=["person.ana"], **{k: False})
                self.assertEqual(S.avisar_dicas(d), 0)
        self.assertFalse(os.path.exists(S.DICAS_ARQ))

    def test_conferindo_espera(self):
        S._conferindo.set()
        try:
            self.assertEqual(S.avisar_dicas(self.d), 0)
        finally:
            S._conferindo.clear()
        self.assertEqual(self.enviados, [])

    def test_home_assistant_fora_tenta_de_novo_depois(self):
        def quebra(forcar=False):
            raise S.ErroHA("fora")
        S.AVISOS.pessoas = quebra
        self.assertEqual(S.avisar_dicas(self.d), 0)
        self.assertNotIn("avisadas", S.dicas_ler(), "não anota: avisa quando voltar")


class TestQuemRecebeETestar(unittest.TestCase):
    def setUp(self):
        self.enviados = []
        Trocar(self, AVISOS=A.Avisos(ha_falso(self.enviados), ws_falso, lambda *a: None), TOKEN="t")

    def test_pessoas_para_a_tela(self):
        self.assertEqual(S.pessoas_aviso("u-ana"), [{"id": "person.ana", "nome": "Ana", "celular": True, "eu": True},
                                                    {"id": "person.beto", "nome": "Beto", "celular": False, "eu": False}])
        self.assertFalse(any(p["eu"] for p in S.pessoas_aviso(None)))

    def test_fora_do_home_assistant(self):
        Trocar(self, TOKEN=None)
        with self.assertRaises(S.ErroHA):
            S.pessoas_aviso("u-ana")
        with self.assertRaisesRegex(ValueError, "Fora do Home Assistant"):
            S.testar_aviso("u-ana")

    def test_testar_no_meu_celular(self):
        with mock.patch.object(S, "dicas_que_valem", return_value=[]):
            self.assertEqual(S.testar_aviso("u-ana"), {"enviados": 2})
        self.assertEqual(self.enviados[0][1]["message"], "Nenhuma dica agora. Quando aparecer, o aviso vem assim.")
        self.assertEqual(self.enviados[0][1]["data"]["tag"], "gerencia-dicas-teste")
        with mock.patch.object(S, "dicas_que_valem", return_value=[dict(DICA_SP, real=40.0)]):
            S.testar_aviso("u-ana")
        self.assertIn("Spotify", self.enviados[-1][1]["message"], "com as dicas de agora")

    def test_testar_sem_ser_pessoa_ou_sem_celular(self):
        with self.assertRaisesRegex(ValueError, "não é uma pessoa da casa"):
            S.testar_aviso("u-outro")
        with self.assertRaisesRegex(ValueError, "Sem celular ligado a você"):
            S.testar_aviso("u-beto")

    def test_home_assistant_nao_entrega(self):
        Trocar(self, AVISOS=A.Avisos(ha_falso(falha={"mobile_app_pixel_8", "mobile_app_relogio_da_ana"}), ws_falso, lambda *a: None))
        with mock.patch.object(S, "dicas_que_valem", return_value=[]), self.assertRaisesRegex(ValueError, "não entregou"):
            S.testar_aviso("u-ana")


class TestRotas(unittest.TestCase):
    """As rotas, com o servidor de verdade (sem Home Assistant)."""

    @classmethod
    def setUpClass(cls):
        from tests.base import Servidor
        cls.s = Servidor()

    @classmethod
    def tearDownClass(cls):
        cls.s.parar()

    def test_pessoas_fora_do_home_assistant(self):
        st, _, r = self.s.get("/api/avisos/pessoas")
        self.assertEqual((st, r), (200, {"pessoas": None, "erro": "Fora do Home Assistant não dá para avisar no celular."}))

    def test_testar_fora_do_home_assistant(self):
        st, _, r = self.s.post("/api/avisos/testar", {})
        self.assertEqual((st, r["erro"]), (400, "Fora do Home Assistant não dá para avisar no celular."))


if __name__ == "__main__":
    unittest.main()
