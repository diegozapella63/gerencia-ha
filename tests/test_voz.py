"""voz.py: Falar (fala para texto do Home Assistant) e o WebSocket feito à mão para uma pergunta."""
import json
import time
import unittest

from tests.base import ServidorFalso, WSFalso, porta_fechada
import voz

PIPES = {"pipelines": [
    {"id": "p1", "name": "Home Assistant", "language": "pt", "stt_engine": "stt.home_assistant_cloud", "stt_language": "pt-BR"},
    {"id": "p2", "name": "Local", "language": "pt", "stt_engine": "stt.faster_whisper"},
    {"id": "p3", "name": "Sem fala", "language": "pt", "stt_engine": None},
    {"id": "p4", "name": "", "language": "en", "stt_engine": "stt.faster_whisper", "stt_language": "en-US"},
], "preferred_pipeline": "p1"}
ESTADOS = [
    {"entity_id": "stt.home_assistant_cloud", "attributes": {"friendly_name": "Home Assistant Cloud"}},
    {"entity_id": "stt.faster_whisper", "attributes": {}},
    {"entity_id": "stt.vosk", "attributes": {"friendly_name": "Vosk"}},
    {"entity_id": "light.sala", "attributes": {}},
]
PCM = b"\0\1" * 8000  # meio segundo


def resultado(cmd, res=PIPES):
    return [{"id": cmd["id"], "type": "result", "success": True, "result": res}]


class TestWebSocket(unittest.TestCase):
    def setUp(self):
        self.srvs = []

    def tearDown(self):
        for s in self.srvs:
            s.fechar()

    def ws(self, responder, **kw):
        s = WSFalso(responder, **kw)
        self.srvs.append(s)
        return s

    def test_pergunta_e_resposta(self):
        s = self.ws(resultado)
        self.assertEqual(voz._ws_comando(s.url, "token-teste", {"type": "assist_pipeline/pipeline/list"}), PIPES)
        textos = [json.loads(d) for op, _, d in s.recebido if op == 1]
        self.assertEqual(textos, [{"type": "auth", "access_token": "token-teste"}, {"id": 1, "type": "assist_pipeline/pipeline/list"}])
        self.assertTrue(all(mascarado for _, mascarado, _ in s.recebido), "o cliente mascara tudo")
        for _ in range(50):  # o servidor lê o fechamento logo depois
            if s.recebido[-1][0] == 8:
                break
            time.sleep(0.02)
        self.assertEqual(s.recebido[-1][0], 8, "e fecha no fim")

    def test_mensagens_grandes_nos_dois_sentidos(self):
        grande = {"x": "a" * 70000}
        s = self.ws(lambda cmd: resultado(cmd, {"eco": cmd.get("dados"), "media": "b" * 300}))
        r = voz._ws_comando(s.url, "token-teste", {"type": "eco", "dados": grande})
        self.assertEqual(r["eco"], grande)
        self.assertEqual(len(r["media"]), 300)
        s2 = self.ws(lambda cmd: resultado(cmd, cmd.get("dados")))
        self.assertEqual(voz._ws_comando(s2.url, "token-teste", {"type": "eco", "dados": "c" * 200}), "c" * 200)

    def test_ignora_outras_mensagens_responde_ping_e_junta_pedacos(self):
        s = self.ws(lambda cmd: [{"type": "event", "id": 7}, ("ping", b"oi"), ("partes", {"id": 1, "type": "result", "success": True, "result": [1, 2]})])
        self.assertEqual(voz._ws_comando(s.url, "token-teste", {"type": "x"}), [1, 2])
        pong = next(d for op, _, d in s.recebido if op == 10)
        self.assertEqual(pong, b"oi")

    def test_erros(self):
        casos = [
            (dict(responder=resultado, token="outro"), "recusou o acesso"),
            (dict(responder=lambda c: [{"id": 1, "type": "result", "success": False, "error": {"message": "Comando desconhecido"}}]), "Comando desconhecido"),
            (dict(responder=lambda c: [{"id": 1, "type": "result", "success": False}]), "recusou o pedido"),
            (dict(responder=lambda c: [("fechar",)]), "fechou a conexão"),
            (dict(responder=lambda c: [("cortar",)]), "fechou a conexão"),
            (dict(responder=resultado, http101=False), "não aceitou a conexão"),
        ]
        for kw, msg in casos:
            with self.subTest(msg=msg):
                s = self.ws(**kw)
                with self.assertRaisesRegex(voz.ErroVoz, msg):
                    voz._ws_comando(s.url, "token-teste", {"type": "x"}, timeout=3)

    def test_ninguem_escutando(self):
        with self.assertRaises(OSError):
            voz._ws_comando(f"ws://127.0.0.1:{porta_fechada()}/api/websocket", "t", {"type": "x"}, timeout=2)


class TestMotores(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.ws = WSFalso(resultado)
        self.rest = ServidorFalso({"/api/states": (200, ESTADOS)})

    def tearDown(self):
        self.ws.fechar()
        self.rest.fechar()

    def v(self, token="token-teste", ws=None):
        return voz.Voz(self.rest.url + "/api", ws or self.ws.url, token, lambda *a: self.logs.append(a))

    def test_opcoes_juntam_assistentes_e_entidades(self):
        ops = self.v().opcoes()
        self.assertEqual([o["id"] for o in ops], ["stt.home_assistant_cloud", "stt.faster_whisper", "stt.vosk"])
        self.assertEqual(ops[0], {"id": "stt.home_assistant_cloud", "nome": "Home Assistant Cloud", "idioma": "pt-BR", "assistentes": ["Home Assistant"], "preferido": True})
        self.assertEqual((ops[1]["nome"], ops[1]["idioma"], ops[1]["assistentes"]), ("Local", "pt", ["Local"]), "sem nome: o do assistente; vazio sai da lista")
        self.assertEqual((ops[2]["nome"], ops[2]["idioma"], ops[2]["assistentes"]), ("Vosk", "pt-BR", []))

    def test_guarda_por_um_minuto(self):
        v = self.v()
        v.opcoes()
        v.opcoes()
        self.assertEqual(len(self.rest.pedidos), 1)
        v.cache = (0, v.cache[1])
        v.opcoes()
        self.assertEqual(len(self.rest.pedidos), 2)

    def test_sem_token_nao_pergunta(self):
        self.assertEqual(self.v(token="").opcoes(), [])
        self.assertEqual(self.rest.pedidos, [])

    def test_assistentes_falhando_ainda_lista_as_entidades(self):
        ops = self.v(ws=f"ws://127.0.0.1:{porta_fechada()}/api/websocket").opcoes()
        self.assertEqual([o["id"] for o in ops], ["stt.home_assistant_cloud", "stt.faster_whisper", "stt.vosk"], "sem preferido: pelo nome (Home…, stt.faster…, Vosk)")
        self.assertFalse(any(o["preferido"] for o in ops))
        self.assertTrue(any("Assistentes de voz:" in l[0] for l in self.logs))

    def test_motor_e_status(self):
        v = self.v()
        self.assertEqual(v.motor(), {"engine": "stt.home_assistant_cloud", "language": "pt-BR", "name": "Home Assistant Cloud"})
        self.assertEqual(v.motor("stt.vosk")["engine"], "stt.vosk")
        self.assertEqual(v.motor("stt.sumiu")["engine"], "stt.home_assistant_cloud", "a escolhida sumiu: a preferida")
        st = v.status("stt.vosk")
        self.assertEqual((st["pronta"], st["motor"], st["selecionada"], len(st["opcoes"])), (True, "stt.vosk", "stt.vosk", 3))
        self.assertEqual(v.status("stt.sumiu")["selecionada"], "")

    def test_sem_motor(self):
        self.rest.rotas["/api/states"] = (200, [])
        v = self.v(ws=f"ws://127.0.0.1:{porta_fechada()}/api/websocket")
        self.assertIsNone(v.motor())
        st = v.status()
        self.assertEqual((st["pronta"], st["opcoes"]), (False, []))
        self.assertIn("assistente de voz", st["motivo"])
        with self.assertRaisesRegex(voz.ErroVoz, "assistente de voz"):
            v.texto(PCM)

    def test_states_com_erro(self):
        self.rest.rotas["/api/states"] = (500, {"erro": 1})
        self.assertEqual([o["id"] for o in self.v().opcoes()], ["stt.home_assistant_cloud", "stt.faster_whisper"])


class TestTexto(unittest.TestCase):
    def setUp(self):
        self.ws = WSFalso(resultado)
        self.rest = ServidorFalso({"/api/states": (200, ESTADOS)})
        self.logs = []
        self.v = voz.Voz(self.rest.url + "/api", self.ws.url, "token-teste", lambda *a: self.logs.append(a))

    def tearDown(self):
        self.ws.fechar()
        self.rest.fechar()

    def stt(self, status, corpo):
        self.rest.rotas["/api/stt/stt.home_assistant_cloud"] = (status, corpo)

    def test_tamanho(self):
        with self.assertRaisesRegex(voz.ErroVoz, "Não ouvi nada"):
            self.v.texto(b"\0" * (voz.MIN_BYTES - 1))
        with self.assertRaisesRegex(voz.ErroVoz, "Não ouvi nada"):
            self.v.texto(None)
        with self.assertRaisesRegex(voz.ErroVoz, "até 2 minutos"):
            self.v.texto(b"\0" * (voz.MAX_BYTES + 1))

    def test_manda_o_audio_com_os_cabecalhos_certos(self):
        self.stt(200, {"result": "success", "text": "  gastei 45 no mercado  "})
        self.assertEqual(self.v.texto(PCM), {"texto": "gastei 45 no mercado", "nome": "Home Assistant Cloud"})
        metodo, caminho, cab, corpo = self.rest.pedidos[-1]
        self.assertEqual((metodo, caminho, corpo), ("POST", "/api/stt/stt.home_assistant_cloud", PCM))
        self.assertIn("X-Speech-Content", cab, "escrito assim: o proxy do Supervisor só repassa desse jeito")
        self.assertEqual(cab["X-Speech-Content"], "format=wav; codec=pcm; sample_rate=16000; bit_rate=16; channel=1; language=pt-BR")
        self.assertEqual(cab["Authorization"], "Bearer token-teste")

    def test_erros_da_fala(self):
        for status, corpo, msg in ((400, "formato ruim", "não aceitou o áudio \\(formato ruim\\)"), (415, "", "não aceitou o áudio \\(415\\)"),
                                   (500, "quebrou", "falhou \\(500: quebrou\\)"), (502, "", "falhou \\(502\\)"),
                                   (200, {"result": "error"}, "Não entendi"), (200, {"result": "success", "text": " "}, "Não entendi"), (200, "não é json", "Não entendi")):
            with self.subTest(status=status, corpo=corpo):
                self.stt(status, corpo)
                with self.assertRaisesRegex(voz.ErroVoz, msg):
                    self.v.texto(PCM)
        self.stt(503, "fora do ar")
        with self.assertRaises(voz.ErroVoz):
            self.v.texto(PCM)
        self.assertIsNone(self.v.cache, "depois de um erro do Home Assistant, lê os motores de novo")
        self.assertTrue(any("503" in l[0] for l in self.logs))

    def test_sem_resposta(self):
        v = voz.Voz(f"http://127.0.0.1:{porta_fechada()}/api", self.ws.url, "token-teste", print)
        v.cache = (9e18, ([], None, [{"entity_id": "stt.x", "attributes": {}}]))
        with self.assertRaisesRegex(voz.ErroVoz, "Sem resposta da fala para texto"):
            v.texto(PCM)


class TestSimulada(unittest.TestCase):
    def test_simulada(self):
        v = voz.Voz("", "", "", print, simulada=True)
        self.assertEqual([o["id"] for o in v.opcoes()], ["stt.simulada", "stt.outra_simulada"])
        self.assertEqual(v.status("stt.outra_simulada")["selecionada"], "stt.outra_simulada")
        self.assertIn("mercado", v.texto(PCM)["texto"])


if __name__ == "__main__":
    unittest.main()
