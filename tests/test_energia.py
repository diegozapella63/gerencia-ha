"""Conta de luz pelo consumo (1.101.0; o dono: "vincular uma conta fixa no gerencia com o consumo de energia… um percentual
fixo a mais"; "tem que mostrar os dois, o atual e o projetado"; "se a IA sabe o valor, faz ela baixar, sem ia ligada deixa
o campo para livre digitação"): o energia.py (os medidores, as estatísticas do Home Assistant, a conta), a escolha
guardada, o fixo do mês com a projeção (só enquanto não está pago), o preço pela IA e a ferramenta do CorrerIA.
O Home Assistant é de mentira; o medidor, o consumo e o preço são inventados."""
import json
import os
import unittest
from datetime import datetime
from unittest import mock

from tests.base import WSFalso, importar_servidor
S = importar_servidor()
from tests.test_integracao import dados as dados_base  # noqa: E402
import energia as E  # noqa: E402
import ferramentas as F  # noqa: E402

AGORA = datetime(2026, 11, 16, 12, 0).astimezone()
MED = [{"id": "sensor.energia_da_casa", "nome": "Energia da casa"}]


class Base(unittest.TestCase):
    def setUp(self):
        if os.path.exists(S.ENERGIA_ARQ):
            os.remove(S.ENERGIA_ARQ)
        self.addCleanup(lambda: os.path.exists(S.ENERGIA_ARQ) and os.remove(S.ENERGIA_ARQ))
        antes = S.ler()
        self.addCleanup(lambda: S.salvar(antes, versao=False))
        S.salvar(dados_base(), versao=False)
        self.kwh = [120]
        for nome, val in (("energia_medidores", lambda: MED), ("energia_kwh", lambda sensor, agora: self.kwh[0])):
            p = mock.patch.object(S, nome, val)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(E, "agora_local", lambda: AGORA)
        p.start()
        self.addCleanup(p.stop)

    def ligar(self, **mais):
        return S.energia_mudar({"fixo": "r-net", "sensor": "sensor.energia_da_casa", "preco": "0,95", "extra": "20%", "ligado": True, **mais})

    def do_mes(self):
        return next((l for l in S.ler()["lancamentos"] if l.get("recorrencia") == "r-net" and l.get("competencia") == "2026-11"), None)


class Modulo(unittest.TestCase):
    def test_medidores_pedido_e_resposta(self):
        est = [{"entity_id": "sensor.b", "attributes": {"friendly_name": "Zeta", "device_class": "energy", "state_class": "total_increasing", "unit_of_measurement": "kWh"}},
               {"entity_id": "sensor.a", "attributes": {"device_class": "energy", "state_class": "total", "unit_of_measurement": "Wh"}},
               {"entity_id": "sensor.potencia", "attributes": {"device_class": "power", "state_class": "measurement", "unit_of_measurement": "W"}},
               {"entity_id": "sensor.gas", "attributes": {"device_class": "energy", "state_class": "total", "unit_of_measurement": "m³"}},
               {"entity_id": "light.sala", "attributes": {}}, "ruim", {"entity_id": "sensor.sem"}]
        self.assertEqual(E.medidores(est), [{"id": "sensor.a", "nome": "sensor.a"}, {"id": "sensor.b", "nome": "Zeta"}])
        self.assertEqual(E.medidores(None), [])
        p = E.pedido("sensor.a", AGORA)
        self.assertEqual((p["type"], p["statistic_ids"], p["period"], p["types"], p["units"], p["start_time"][:19]),
                         ("recorder/statistics_during_period", ["sensor.a"], "day", ["change"], {"energy": "kWh"}, "2026-11-01T00:00:00"))
        self.assertEqual(E.kwh_da_resposta({"sensor.a": [{"change": 10.5}, {"change": 2}, {"change": -1}, {"change": None}, {"change": True}, "x"]}, "sensor.a"), 12.5)
        for vazio in ({}, {"sensor.a": []}, {"sensor.a": [{"change": 0}]}, None, {"sensor.a": "x"}):
            self.assertIsNone(E.kwh_da_resposta(vazio, "sensor.a"))

    def test_conta_atual_e_projetada(self):
        c = E.conta(120, 0.95, 20, datetime(2026, 11, 16, 12, 0))
        self.assertEqual(c, {"kwh": 120, "atual": 136.8, "projetado": 264.77, "dia": 16, "dias": 30, "kwh_projetado": 232.3})
        self.assertEqual(E.obs(c), "Energia: 120,0 kWh até o dia 16 (R$ 136,80) · projeção do mês: 232,3 kWh (R$ 264,77)")
        self.assertEqual(E.conta(10, 1, 0, datetime(2026, 11, 1, 6, 0))["projetado"], 300.0, "no primeiro dia, a conta é de um dia inteiro")
        self.assertEqual(E.conta(300, 1, 0, datetime(2026, 11, 30, 23, 59))["projetado"], 300.01)
        self.assertEqual([E.numero(v, 0, 200) for v in ("20%", "0,5", 3, "abc", None, True, 500, "-1")], [20.0, 0.5, 3.0, None, None, None, None, None])
        self.assertIsNotNone(E.agora_local().tzinfo)


class Servidor(Base):
    def test_escolher_ligar_e_o_fixo_do_mes(self):
        e = S.energia_estado()
        self.assertEqual((e["ligado"], e["fixos"], e["medidores"], e["ultimo"]), (False, [{"id": "r-net", "nome": "Internet"}], MED, None))
        for corpo, frase in (({"ligado": True}, "Antes de ligar"), ({"fixo": "nao-existe"}, "um fixo que exista"), ({"fixo": "r-sal"}, "um fixo que exista"),
                             ({"sensor": "light.sala"}, "um medidor de energia"), ({"preco": "50"}, "entre R$ 0,01 e R$ 10,00"), ({"extra": "900"}, "de 0 a 200")):
            with self.assertRaises(ValueError) as cm:
                S.energia_mudar(corpo)
            self.assertIn(frase, str(cm.exception))
        self.assertIsNone(self.do_mes())
        rev = S.ler()["rev"]
        e = self.ligar()
        self.assertEqual((e["ligado"], e["preco"], e["extra"], e["erro"]), (True, 0.95, 20.0, ""))
        self.assertEqual(e["ultimo"], {"kwh": 120.0, "atual": 136.8, "projetado": 264.77, "dia": 16, "dias": 30, "kwh_projetado": 232.3, "mes": "2026-11", "pago": False})
        x = self.do_mes()
        self.assertEqual((x["valor"], x["pago"], x["descricao"], x["categoria"]), (264.77, False, "Internet", "c-casa"), "o fixo do mês fica com a projeção")
        self.assertEqual(x["obs"], "Energia: 120,0 kWh até o dia 16 (R$ 136,80) · projeção do mês: 232,3 kWh (R$ 264,77)")
        self.assertEqual(S.ler()["rev"], rev + 1)
        self.assertEqual(next(r for r in S.ler()["recorrencias"] if r.get("id") == "r-net")["valor"], 120, "o fixo dos outros meses não muda")
        S.atualizar_energia()
        self.assertEqual(S.ler()["rev"], rev + 1, "sem mudança, não regrava")
        self.kwh[0] = 150
        S.atualizar_energia()
        x = self.do_mes()
        self.assertEqual((x["valor"], x["obs"].count("Energia:")), (330.97, 1), "o consumo andou: o valor e a linha são trocados")
        self.assertEqual(len([l for l in S.ler()["lancamentos"] if l.get("recorrencia") == "r-net"]), 1)

    def test_pago_nao_muda_e_os_erros(self):
        self.ligar()
        d = S.ler()
        x = next(l for l in d["lancamentos"] if l.get("recorrencia") == "r-net")
        x.update(pago=True, obs="paga no dia 20")
        S.salvar(d, versao=False)
        self.kwh[0] = 400
        e = S.atualizar_energia()
        self.assertEqual((self.do_mes()["valor"], self.do_mes()["obs"], e["ultimo"]["pago"], e["ultimo"]["kwh"]), (264.77, "paga no dia 20", True, 400.0), "pago: o valor fica; o atual e o projetado continuam à vista")
        self.kwh[0] = None
        self.assertEqual(S.atualizar_energia()["erro"], "O medidor ainda não tem consumo guardado neste mês.")
        with mock.patch.object(S, "energia_kwh", side_effect=RuntimeError("x")):
            self.assertEqual(S.atualizar_energia()["erro"], "Não consegui ler o medidor no Home Assistant agora.")
        self.kwh[0] = 10
        d = S.ler()
        d["recorrencias"] = [r for r in d["recorrencias"] if r.get("id") != "r-net"]
        S.salvar(d, versao=False)
        self.assertIn("não existe mais", S.atualizar_energia()["erro"])
        S.energia_mudar({"ligado": False})
        self.assertFalse(S.atualizar_energia()["ligado"])
        self.assertFalse(S.energia_na_hora())
        with mock.patch.object(S, "atualizar_energia", side_effect=RuntimeError("x")):
            S.energia_sem_erro()

    def test_de_tempos_em_tempos_e_a_obs_de_antes(self):
        d = S.ler()
        d["lancamentos"].append({"id": "l-net", "tipo": "despesa", "descricao": "Internet", "valor": 120, "data": "2026-11-25", "pago": False, "recorrencia": "r-net",
                                 "competencia": "2026-11", "obs": "plano novo"})
        S.salvar(d, versao=False)
        self.ligar(extra="")
        x = self.do_mes()
        self.assertEqual((x["id"], x["valor"]), ("l-net", 220.65))
        self.assertTrue(x["obs"].startswith("plano novo · Energia: 120,0 kWh"), "o que a pessoa escreveu fica")
        self.assertFalse(S.energia_na_hora())
        c = S._energia_ler()
        c["em"] = "2026-01-01T00:00:00"
        S._energia_gravar(c)
        self.assertTrue(S.energia_na_hora())
        c["em"] = "ruim"
        S._energia_gravar(c)
        self.assertTrue(S.energia_na_hora())
        with open(S.ENERGIA_ARQ, "w", encoding="utf-8") as f:
            f.write("[1]")
        self.assertEqual(S._energia_ler(), {})

    def test_preco_pela_ia_ou_escrito(self):
        d = S.ler()
        d["ajustes"]["ia"] = False
        S.salvar(d, versao=False)
        with self.assertRaises(ValueError) as cm:
            S.energia_mudar({"buscar_preco": True, "onde": "Cidade Exemplo, EX"})
        self.assertIn("A IA está desligada: escreva o preço", str(cm.exception))
        self.assertEqual(S.energia_mudar({"preco": "1,10"})["preco"], 1.1, "sem a IA, o campo é livre")
        d = S.ler()
        d["ajustes"]["ia"] = True
        S.salvar(d, versao=False)
        with self.assertRaises(ValueError) as cm:
            S.energia_mudar({"buscar_preco": True, "onde": "x"})
        self.assertIn("Diga a cidade", str(cm.exception))
        resposta = {"service_response": {"data": json.dumps({"preco_kwh": 0.87, "sem_impostos": 0.7, "distribuidora": "Luz Exemplo", "bandeira": "verde",
                                                               "como": "0,70 com os impostos", "fonte": "https://luz.exemplo/tarifas"})}}
        with mock.patch.object(S, "IA_MOCK", False), mock.patch.object(S, "ia_chamar", return_value=resposta) as ia:
            e = S.energia_mudar({"buscar_preco": True, "onde": "  Cidade   Exemplo, EX "})
            self.assertIn("Cidade Exemplo, EX", ia.call_args[0][1]["instructions"])
            self.assertIn("com o ICMS, o PIS e a COFINS", ia.call_args[0][1]["instructions"])
        self.assertEqual((e["preco"], e["onde"], e["tarifa"]["distribuidora"], e["tarifa"]["fonte"], e["tarifa"]["sem_impostos"]), (0.87, "Cidade Exemplo, EX", "Luz Exemplo", "https://luz.exemplo/tarifas", 0.7))
        for ruim in ({"service_response": {"data": '{"erro": "sem_tarifa"}'}}, {"service_response": {"data": '{"preco_kwh": 900}'}}, None):
            with mock.patch.object(S, "IA_MOCK", False), mock.patch.object(S, "ia_chamar", return_value=ruim), self.assertRaises(ValueError) as cm:
                S.energia_mudar({"buscar_preco": True, "onde": "Cidade Exemplo"})
            self.assertIn("não achou o preço do kWh", str(cm.exception))
        with mock.patch.object(S, "IA_MOCK", False), mock.patch.object(S, "ia_chamar", side_effect=S.ErroHA("fora do ar")), self.assertRaises(ValueError):
            S.energia_mudar({"buscar_preco": True, "onde": "Cidade Exemplo"})
        self.assertEqual(S._energia_ler()["preco"], 0.87, "o que falhou não troca o preço")
        with mock.patch.object(S, "IA_MOCK", True):
            self.ligar()
            e = S.energia_mudar({"buscar_preco": True, "onde": "Cidade Exemplo"})
        self.assertEqual((e["preco"], e["ultimo"]["atual"]), (0.98, 141.12), "ligado: a conta já sai com o preço novo")

    def test_ferramenta_e_rotas(self):
        t = S.usar_ferramenta({"nome": "conta_de_luz", "argumentos": {}})["texto"]
        self.assertIn("está desligada", t)
        self.ligar()
        t = S.usar_ferramenta({"nome": "conta_de_luz", "argumentos": {}})["texto"].split("\n")
        self.assertEqual(t[:4], ["Internet, pelo consumo de energia deste mês:", "- Até hoje (dia 16 de 30): 120,0 kWh, R$ 136,80", "- Projeção do mês: 232,3 kWh, R$ 264,77",
                                 "Conta: kWh × R$ 0,9500 + 20%."])
        self.assertEqual(t[4], "O fixo deste mês fica com a projeção até ser pago.")
        with self.assertRaises(LookupError):
            F.chamar("conta_de_luz", {}, dados_base())
        self.assertEqual(F.texto_conta_de_luz({"ligado": True, "ultimo": None, "erro": ""}, {}), "Ainda não há consumo lido neste mês.")
        self.assertIn("já está pago", F.texto_conta_de_luz({"ligado": True, "fixo": "x", "preco": 1, "extra": 0, "erro": "Aviso.",
                                                           "ultimo": {"kwh": 1, "atual": 1, "projetado": 2, "dia": 1, "dias": 30, "kwh_projetado": 2, "pago": True}}, {}))
        from tests.base import Servidor as Srv
        s = Srv(env={"GERENCIA_ENERGIA_MOCK": json.dumps({"medidores": MED, "kwh": 50})})
        self.addCleanup(s.parar)
        e = s.get("/api/energia")[2]
        self.assertEqual((e["ligado"], e["medidores"], e["disponivel"]), (False, MED, True))
        st, _, r = s.post("/api/energia", {"ligado": True})
        self.assertEqual((st, r["erro"]), (400, "Antes de ligar, escolha o fixo, o medidor e o preço do kWh."))


class Real(unittest.TestCase):
    def test_o_consumo_pelas_estatisticas_do_home_assistant(self):
        def responder(c):
            return [{"id": c["id"], "type": "result", "success": True, "result": {"sensor.e": [{"start": 1, "end": 2, "change": 4.5}, {"change": 5.5}]}}]
        ws = WSFalso(responder)
        self.addCleanup(ws.fechar)
        with mock.patch.object(S, "HA_WS", ws.url), mock.patch.object(S, "TOKEN", "token-teste"):
            self.assertEqual(S.energia_kwh("sensor.e", AGORA), 10.0)
        pedido = next(m for m in (json.loads(x[2]) for x in ws.recebido if x[0] == 1) if m.get("type") == "recorder/statistics_during_period")
        self.assertEqual((pedido["statistic_ids"], pedido["period"]), (["sensor.e"], "day"))
        est = [{"entity_id": "sensor.e", "attributes": {"friendly_name": "Medidor", "device_class": "energy", "state_class": "total", "unit_of_measurement": "kWh"}}]
        with mock.patch.object(S, "ha_request", return_value=est):
            self.assertEqual(S.energia_medidores(), [{"id": "sensor.e", "nome": "Medidor"}])
        with mock.patch.object(S, "ha_request", side_effect=S.ErroHA("x")):
            self.assertEqual(S.energia_medidores(), [])
        with mock.patch.object(S, "ENERGIA_MOCK", "ruim"):
            self.assertIsNone(S._energia_mock())
        with mock.patch.object(S, "ENERGIA_MOCK", json.dumps({"medidores": [{"id": "sensor.x", "nome": "X"}, 1], "kwh": 7})):
            self.assertEqual((S.energia_medidores(), S.energia_kwh("sensor.x", AGORA)), ([{"id": "sensor.x", "nome": "X"}], 7))
