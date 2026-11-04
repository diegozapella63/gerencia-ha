"""server.py, o resto: índices do Banco Central, sensores no Home Assistant, dicas de economia (assinaturas,
página oficial, dólar), status da IA, imagens dos investimentos, backups, versões e a rotina (contra serviços de mentira)."""
import json
import os
import time
import unittest
from unittest import mock
from datetime import date, timedelta

from tests.base import ServidorFalso, importar_servidor, porta_fechada, RAIZ
S = importar_servidor()

FONTES = os.path.join(RAIZ, "tests", "e2e", "fixtures", "fontes")
JPG = b"\xff\xd8\xff\xe0" + b"\2" * 400 + b"\xff\xd9"


class Trocar:
    """Troca variáveis do server.py durante um teste e devolve as de antes no fim."""

    def __init__(self, caso, **mudar):
        self.antes = {k: getattr(S, k) for k in mudar}
        for k, v in mudar.items():
            setattr(S, k, v)
        caso.addCleanup(lambda: [setattr(S, k, v) for k, v in self.antes.items()])


def dados(**mais):
    d = S.vazio()
    d.update(mais)
    return d


# ---------------------------------------------------------------------------------------------------------------
class TestBancoCentral(unittest.TestCase):
    def setUp(self):
        S.salvar(S.vazio(), versao=False)

    def bcb(self, rotas):
        srv = ServidorFalso(rotas)
        self.addCleanup(srv.fechar)
        Trocar(self, BCB=srv.url + "/serie/{s}")
        return srv

    def test_atualiza_os_quatro(self):
        self.bcb({f"/serie/{s}/ultimos/1": (200, [{"data": "31/10/2026", "valor": v}]) for s, v in ((432, "15,00"), (4389, "14.90"), (13522, "0,35"), (226, "0.1234"))})
        d = S.atualizar_indices()
        ind = d["indices"]
        self.assertEqual((ind["selic"], ind["cdi"], ind["ipca"], ind["tr"]), (15.0, 14.9, 0.35, 0.1234))
        self.assertEqual((ind["fonte"], ind["erro"], ind["datas"]["cdi"]), ("bcb", None, "31/10/2026"))
        self.assertTrue(ind["atualizado_em"])
        self.assertEqual(S.ler()["indices"]["selic"], 15.0, "gravado")

    def test_sem_o_cdi_usa_a_selic_menos_0_10(self):
        self.bcb({"/serie/432/ultimos/1": (200, [{"data": "31/10/2026", "valor": "15"}])})
        ind = S.atualizar_indices()["indices"]
        self.assertEqual(ind["cdi"], 14.9)
        self.assertEqual(ind["erro"], "Faltou: cdi, ipca, tr")

    def test_tenta_o_periodo_quando_o_ultimo_falha(self):
        srv = self.bcb({"/serie/432": (200, [{"data": "30/10/2026", "valor": "14"}, {"data": "31/10/2026", "valor": "15"}])})
        self.assertEqual(S.bcb_ultimo(432), (15.0, "31/10/2026"), "o último da lista")
        self.assertIn("dataInicial=", srv.pedidos[-1][1])

    def test_banco_central_fora(self):
        Trocar(self, BCB=f"http://127.0.0.1:{porta_fechada()}/serie/{{s}}")
        antes = S.ler()["indices"]
        ind = S.atualizar_indices()["indices"]
        self.assertEqual(ind["erro"], "Sem resposta do Banco Central")
        self.assertEqual((ind["cdi"], ind["fonte"]), (antes["cdi"], antes["fonte"]), "fica com os de antes")
        with self.assertRaisesRegex(RuntimeError, "série 432"):
            S.bcb_ultimo(432)


# ---------------------------------------------------------------------------------------------------------------
class TestSensores(unittest.TestCase):
    def setUp(self):
        self.ha = ServidorFalso({})
        self.ha.rotas = _Tudo200()
        self.addCleanup(self.ha.fechar)
        Trocar(self, TOKEN="token-teste", HA_API=self.ha.url, IA_MOCK=False)
        antes = dict(S._sensores)
        self.addCleanup(lambda: S._sensores.update(antes))
        S._sensores["ligado"] = None

    def enviados(self, metodo):
        return {p[1].split("/states/")[1]: json.loads(p[3] or b"{}") for p in self.ha.pedidos if p[0] == metodo and "/states/" in p[1]}

    def test_sem_acesso_ao_home_assistant_nao_faz_nada(self):
        Trocar(self, TOKEN=None)
        S.publicar_sensores(dados())
        self.assertEqual(self.ha.pedidos, [])

    def test_desligado_apaga_os_sensores_uma_vez(self):
        S.publicar_sensores(dados())
        self.assertEqual(set(self.enviados("DELETE")), set(S.SENSORES))
        n = len(self.ha.pedidos)
        S.publicar_sensores(dados())
        self.assertEqual(len(self.ha.pedidos), n, "já apagados: não pede de novo")

    def test_ligado_publica_patrimonio_e_caixa(self):
        d = dados(investimentos=[{"id": "a", "valor": 1000, "indexador": "parado"}, {"id": "b", "valor": 300, "indexador": "parado", "titular": "terceiros", "terceiro": "Mãe"}],
                  lancamentos=[{"id": "l", "tipo": "receita", "valor": 200, "data": date.today().isoformat(), "pago": True}])
        d["ajustes"]["sensores"] = True
        Trocar(self, bens_estado=lambda d, forcar=False: {"ok": True, "hoje": 5000, "registrado": 6000, "perde_ano": 400, "n": 3})
        S.publicar_sensores(d)
        s = self.enviados("POST")
        p = s["sensor.gerencia_patrimonio"]
        self.assertEqual(p["state"], 1000, "o patrimônio é só o seu")
        self.assertEqual((p["attributes"]["de_terceiros"], p["attributes"]["com_terceiros"], p["attributes"]["com_bens"]), (300, 1300, 6000))
        self.assertEqual((p["attributes"]["unit_of_measurement"], p["attributes"]["device_class"]), ("BRL", "monetary"))
        self.assertEqual(s["sensor.gerencia_terceiros"]["attributes"]["por_pessoa"], {"Mãe": 300})
        self.assertEqual(s["sensor.gerencia_saldo_caixa"]["state"], 200)
        self.assertEqual(s["sensor.gerencia_bens"]["attributes"]["itens"], 3)
        self.assertEqual(self.ha.pedidos[0][2]["Authorization"], "Bearer token-teste")

    def test_home_assistant_recusando_para_no_primeiro(self):
        self.ha.rotas = _Tudo(500)
        d = dados()
        d["ajustes"]["sensores"] = True
        S.publicar_sensores(d)
        self.assertEqual(len([p for p in self.ha.pedidos if p[0] == "POST"]), 1)


class _Tudo:
    """Rotas que respondem tudo com o mesmo status."""

    def __init__(self, status):
        self.status = status

    def get(self, caminho, padrao=None):
        return (self.status, {"ok": self.status < 400})


def _Tudo200():
    return _Tudo(200)


# ---------------------------------------------------------------------------------------------------------------
class TestAssinaturasDoUsuario(unittest.TestCase):
    HOJE = date(2026, 11, 2)

    def subs(self, recorrencias=(), lancamentos=()):
        return S.assinaturas_do_usuario(dados(recorrencias=list(recorrencias), lancamentos=list(lancamentos)), hoje=self.HOJE)

    def test_fixos(self):
        s = self.subs(recorrencias=[
            {"id": "r1", "tipo": "despesa", "descricao": "Spotify Família", "valor": 40.9, "dia": 22, "conta": "k", "cartao": True},
            {"id": "r2", "tipo": "despesa", "descricao": "Aluguel", "valor": 2000},
            {"id": "r3", "tipo": "despesa", "descricao": "Deezer", "valor": 20, "fim": "2026-12"},
            {"id": "r4", "tipo": "receita", "descricao": "Spotify (reembolso)", "valor": 10}])
        self.assertEqual([(x["servico"], x["origem"], x["valor"], x["dia"], x["cartao"]) for x in s], [("spotify", "fixo", 40.9, 22, True)])

    def test_ja_no_anual_nao_repete_o_mensal(self):
        s = self.subs(recorrencias=[{"id": "a", "descricao": "Nabu Casa anual", "valor": 325, "freq": "anual"}, {"id": "m", "descricao": "Nabu Casa", "valor": 32.5}])
        self.assertEqual([(x["rid"], x["freq_anual"]) for x in s], [("a", True)])

    def test_cobrancas_que_se_repetem(self):
        l = lambda d, v, desc="Claude.ai": {"tipo": "despesa", "descricao": desc, "valor": v, "data": d}
        s = self.subs(lancamentos=[l("2026-09-05", 110), l("2026-10-05", 112), l("2026-11-01", 111)])
        self.assertEqual([(x["servico"], x["origem"], x["valor"], x["dia"]) for x in s], [("claude", "lancamentos", 111, 1)])
        self.assertEqual(self.subs(lancamentos=[l("2026-10-05", 110), l("2026-10-25", 110)]), [], "um mês só: não dá para saber")
        self.assertEqual(self.subs(lancamentos=[l("2026-09-05", 110), l("2026-10-05", 300)]), [], "valores muito diferentes")
        self.assertEqual(self.subs(lancamentos=[l("2026-01-05", 110), l("2026-02-05", 110)]), [], "mais de 100 dias atrás")
        coberto = self.subs(recorrencias=[{"id": "r", "descricao": "Claude", "valor": 110}], lancamentos=[l("2026-09-05", 110), l("2026-10-05", 110)])
        self.assertEqual([x["origem"] for x in coberto], ["fixo"], "já tem o fixo: as cobranças não contam de novo")


class TestFonteOficial(unittest.TestCase):
    def setUp(self):
        Trocar(self, FONTES_MOCK=FONTES, IA_MOCK=True)

    def test_pagina_conferida(self):
        f = S.conferir_fonte(S.assinaturas.POR_ID["spotify"], dados())
        self.assertEqual(f["status"], "ok")
        self.assertIn("Premium Individual", [p["plano"] for p in f["planos"]])
        self.assertEqual(f["conferido"], date.today().isoformat())

    def test_preco_inventado_pela_ia_e_recusado(self):
        f = S.conferir_fonte(S.assinaturas.POR_ID["claude"], dados())
        p = f["planos"][0]
        self.assertEqual((p["mensal"], p["anual"], p["anual_recusado"]), (20.0, 0.0, True), "o anual que a página não mostra sai")
        Trocar(self, DICAS_SIMULADAS={"claude": {"planos": [{"plano": "Pro", "moeda": "USD", "mensal": 19, "trecho_mensal": "$19 por mês"}]}})
        self.assertEqual(S.conferir_fonte(S.assinaturas.POR_ID["claude"], dados())["status"], "nao_confere", "nada confere")
        Trocar(self, DICAS_SIMULADAS={"claude": "não é JSON"})
        self.assertEqual(S.conferir_fonte(S.assinaturas.POR_ID["claude"], dados())["status"], "erro_ia")

    def test_sem_pagina_sem_precos_e_sem_ia(self):
        self.assertEqual(S.conferir_fonte(S.assinaturas.POR_ID["deezer"], dados())["status"], "sem_acesso", "sem a página de teste")
        vazia = S.assinaturas.POR_ID["deezer"]
        pasta = os.path.join(S.DATA_DIR, "fontes-vazias")
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, "deezer.html"), "w") as f:
            f.write("<html><body>Planos em breve</body></html>")
        Trocar(self, FONTES_MOCK=pasta)
        self.assertEqual(S.conferir_fonte(vazia, dados())["status"], "sem_precos")
        Trocar(self, FONTES_MOCK=FONTES)
        d = dados()
        d["ajustes"]["ia"] = False
        self.assertEqual(S.conferir_fonte(S.assinaturas.POR_ID["spotify"], d)["status"], "ia_desligada")
        Trocar(self, IA_MOCK=False, TOKEN=None)
        self.assertEqual(S.conferir_fonte(S.assinaturas.POR_ID["spotify"], dados())["status"], "sem_ia")

    def test_velha(self):
        hoje = date.today()
        f = lambda dias, status="ok": {"conferido": (hoje - timedelta(days=dias)).isoformat(), "status": status}
        self.assertTrue(S._velha(None))
        self.assertTrue(S._velha({"conferido": "ontem"}))
        self.assertFalse(S._velha(f(29)))
        self.assertTrue(S._velha(f(30)), "confere de novo a cada 30 dias")
        self.assertFalse(S._velha(f(0, "sem_acesso")))
        self.assertTrue(S._velha(f(1, "sem_acesso")), "o que deu errado tenta de novo no dia seguinte")
        self.assertFalse(S._velha(f(0), forcar=True), "Conferir agora: o de hoje já basta")
        self.assertTrue(S._velha(f(1), forcar=True))

    def test_dolar(self):
        Trocar(self, DOLAR_FIXO=None)
        hoje = date.today().isoformat()
        self.assertEqual(S.dolar_atual({"dolar": {"valor": 5.1, "buscado": hoje}})["valor"], 5.1, "o de hoje, guardado")
        srv = ServidorFalso({"/serie/1/ultimos/1": (200, [{"data": "31/10/2026", "valor": "5,4321"}])})
        self.addCleanup(srv.fechar)
        Trocar(self, BCB=srv.url + "/serie/{s}")
        self.assertEqual(S.dolar_atual({}), {"valor": 5.4321, "data": "31/10/2026", "buscado": hoje})
        Trocar(self, BCB=f"http://127.0.0.1:{porta_fechada()}/{{s}}")
        self.assertEqual(S.dolar_atual({"dolar": {"valor": 5.0, "buscado": "2026-01-01"}}), {"valor": 5.0, "buscado": hoje}, "fora do ar: o último que tinha")
        Trocar(self, DOLAR_FIXO="5.04")
        self.assertEqual(S.dolar_atual({})["valor"], 5.04)


class TestDicasEstado(unittest.TestCase):
    def setUp(self):
        Trocar(self, FONTES_MOCK=FONTES, IA_MOCK=True, DOLAR_FIXO="5.04")
        self.d = dados(recorrencias=[
            {"id": "r-sp", "tipo": "despesa", "descricao": "Spotify", "valor": 23.9, "dia": 22},
            {"id": "r-nabu", "tipo": "despesa", "descricao": "Nabu Casa", "valor": 35.1, "dia": 9},
            {"id": "r-ms", "tipo": "despesa", "descricao": "Microsoft 365 anual", "valor": 599, "freq": "anual", "inicio": "2026-03"}])
        S.salvar(self.d, versao=False)
        if os.path.exists(S.DICAS_ARQ):
            os.remove(S.DICAS_ARQ)

    def test_desligadas(self):
        self.d["ajustes"]["dicas"] = False
        r = S.dicas_estado(self.d)
        self.assertEqual((r["desligadas"], r["dicas"]), (True, []))
        self.assertIn("Spotify", r["catalogo"])

    def test_confere_na_origem_e_mostra_a_economia(self):
        S._conferindo.set()
        S._conferir(False)  # roda direto (no app, numa linha separada)
        self.assertFalse(S._conferindo.is_set())
        cache = S.dicas_ler()
        self.assertEqual(sorted(cache["fontes"]), ["nabucasa", "spotify"], "o anual já não precisa conferir")
        r = S.dicas_estado(self.d, disparar=False)
        st = {a["servico"]: a["status"] for a in r["assinaturas"]}
        self.assertEqual(st, {"spotify": "ok", "nabucasa": "ok", "microsoft365": "ja_anual"})
        self.assertEqual([x["servico"] for x in r["dicas"]], ["nabucasa", "spotify"], "a maior economia primeiro")
        sp = next(x for x in r["dicas"] if x["servico"] == "spotify")
        self.assertEqual((sp["preco_anual"], sp["dominio"], sp["economia_ano"]), (239.0, "spotify.com", round(12 * 23.9 * (1 - 239 / (12 * 23.9)), 2)))

    def test_pendente_vira_conferindo(self):
        S._conferindo.set()
        try:
            r = S.dicas_estado(self.d, disparar=False)
        finally:
            S._conferindo.clear()
        self.assertEqual({a["status"] for a in r["assinaturas"] if a["servico"] != "microsoft365"}, {"conferindo"})
        self.assertTrue(r["conferindo"])

    def test_disparar_confere_em_segundo_plano(self):
        S.dicas_estado(self.d)
        for _ in range(100):
            if not S._conferindo.is_set() and S.dicas_ler().get("fontes"):
                break
            time.sleep(0.05)
        self.assertEqual(sorted(S.dicas_ler()["fontes"]), ["nabucasa", "spotify"])


# ---------------------------------------------------------------------------------------------------------------
class TestStatusDaIA(unittest.TestCase):
    def setUp(self):
        self.estados = [{"entity_id": "ai_task.texto", "attributes": {"friendly_name": "IA de texto", "supported_features": 1}},
                        {"entity_id": "ai_task.google", "attributes": {"friendly_name": "Google", "supported_features": 3}},
                        {"entity_id": "light.sala", "attributes": {}}]
        self.ha = ServidorFalso({"/states": lambda h, c: (200, self.estados)})
        self.addCleanup(self.ha.fechar)
        Trocar(self, TOKEN="t", HA_API=self.ha.url, IA_MOCK=False)

    def test_entidades_com_imagem_primeiro(self):
        self.assertEqual(S.ia_entidades(), [{"id": "ai_task.google", "nome": "Google", "imagens": True}, {"id": "ai_task.texto", "nome": "IA de texto", "imagens": False}])

    def test_status(self):
        d = dados()
        self.assertTrue(S.ia_status(d)["pronta"])
        d["ajustes"]["ia_entidade"] = "ai_task.texto"
        self.assertTrue(S.ia_status(d)["pronta"], "a escolhida existe")
        d["ajustes"]["ia_entidade"] = "ai_task.sumiu"
        st = S.ia_status(d)
        self.assertEqual((st["pronta"], st["motivo"]), (False, "A IA escolhida não está mais no Home Assistant."))
        self.estados = self.estados[:1]
        d["ajustes"]["ia_entidade"] = ""
        self.assertFalse(S.ia_status(d)["pronta"], "só IA de texto: não lê imagens")
        self.estados = []
        self.assertIn("Nenhuma IA configurada", S.ia_status(d)["motivo"])
        d["ajustes"]["ia"] = False
        self.assertEqual(S.ia_status(d)["motivo"], "A IA está desligada.")

    def test_fora_do_home_assistant_e_erro(self):
        d = dados()
        Trocar(self, TOKEN=None)
        self.assertIn("Fora do Home Assistant", S.ia_status(d)["motivo"])
        self.assertFalse(S.ia_disponivel(d))
        Trocar(self, TOKEN="t", HA_API=f"http://127.0.0.1:{porta_fechada()}")
        self.assertIn("Sem resposta do Home Assistant", S.ia_status(d)["motivo"])
        self.assertFalse(S.ia_disponivel(d))

    def test_disponivel_para_texto(self):
        d = dados()
        self.assertTrue(S.ia_disponivel(d))
        d["ajustes"]["ia_entidade"] = "ai_task.texto"
        self.assertTrue(S.ia_disponivel(d), "para ler a página basta uma IA de texto")
        d["ajustes"]["ia_entidade"] = "ai_task.sumiu"
        self.assertFalse(S.ia_disponivel(d))

    def test_ha_request_explica_o_erro(self):
        self.ha.rotas["/erro"] = (400, {"message": "Entidade não existe"})
        with self.assertRaisesRegex(S.ErroHA, "recusou o pedido: Entidade não existe"):
            S.ha_request("GET", "/erro")
        self.ha.rotas["/vazio"] = (200, b"")
        self.assertIsNone(S.ha_request("GET", "/vazio"))


# ---------------------------------------------------------------------------------------------------------------
class TestImagensBackupsVersoes(unittest.TestCase):
    def test_imagens(self):
        r = S.salvar_foto({"jpg": "data:image/jpeg;base64," + __import__("base64").b64encode(JPG).decode()})
        self.assertRegex(r["arquivo"], r"^\d{8}-\d{6}-[0-9a-f]{6}\.jpg$")
        for corpo, msg in (({"jpg": "!!"}, "Imagem inválida"), ({"jpg": "QUJD"}, "Envie a imagem em JPG"),
                           ({"jpg": __import__("base64").b64encode(b"\xff\xd8" + b"0" * (9 * 1024 * 1024)).decode()}, "grande demais")):
            with self.assertRaisesRegex(ValueError, msg):
                S.salvar_foto(corpo)

    def test_limpar_imagens_sem_uso(self):
        os.makedirs(S.FOTOS, exist_ok=True)
        nomes = {"usada": "20260101-000000-aaaaaa.jpg", "velha": "20260101-000000-bbbbbb.jpg", "nova": "20260101-000000-cccccc.jpg", "outra": "leia-me.txt"}
        for n in nomes.values():
            open(os.path.join(S.FOTOS, n), "wb").close()
        antigo = time.time() - 8 * 86400
        for k in ("usada", "velha", "outra"):
            os.utime(os.path.join(S.FOTOS, nomes[k]), (antigo, antigo))
        d = dados(investimentos=[{"id": "i", "fotos": [nomes["usada"], "../fora.jpg", 3]}])
        self.assertEqual(S.fotos_usadas(d), {nomes["usada"]})
        S.limpar_fotos(d)
        ficou = set(os.listdir(S.FOTOS))
        self.assertTrue({nomes["usada"], nomes["nova"], nomes["outra"]} <= ficou, "usada, recente e o que não é imagem ficam")
        self.assertNotIn(nomes["velha"], ficou, "sem uso há mais de 7 dias: sai")

    def test_backups(self):
        os.makedirs(S.SHARE_DIR, exist_ok=True)
        for f in os.listdir(S.SHARE_DIR):
            os.remove(os.path.join(S.SHARE_DIR, f)) if f.endswith(".zip") else None
        S.salvar(dados(investimentos=[{"id": "x", "nome": "Do backup", "valor": 1, "indexador": "parado"}]), versao=False)
        for k in range(14):
            nome = f"gerencia-2026-10-{k + 1:02d}-1000.zip"
            with open(os.path.join(S.SHARE_DIR, nome), "wb") as f:
                f.write(S.gerar_zip(S.ler()))
            os.utime(os.path.join(S.SHARE_DIR, nome), (time.time() - (20 - k) * 3600,) * 2)
        open(os.path.join(S.SHARE_DIR, "outro.zip"), "wb").close()
        lista = S.listar_backups()
        self.assertEqual(len(lista), 12, "os 12 mais recentes")
        self.assertEqual(lista[0]["nome"], "gerencia-2026-10-14-1000.zip")
        self.assertNotIn("outro.zip", [b["nome"] for b in lista])
        S.salvar(S.vazio(), versao=False)
        r = S.restaurar_backup(lista[0]["nome"])
        self.assertEqual(r["investimentos"][0]["nome"], "Do backup")
        for ruim in ("../x.zip", "outro.zip", "gerencia-nao-existe.zip", ""):
            with self.assertRaisesRegex(ValueError, "não existe mais"):
                S.restaurar_backup(ruim)

    def test_nome_dos_arquivos(self):
        self.assertRegex(S.nome_arquivo("zip"), r"^gerencia-\d{4}-\d{2}-\d{2}-\d{4}\.zip$")

    def test_versoes_com_motivo_e_total(self):
        S.salvar(dados(investimentos=[{"id": "x", "valor": 250, "indexador": "parado"}]), versao=False)
        S.guardar_versao("antes-de-importar", forcar=True)
        with open(os.path.join(S.VERSOES, "quebrada.json"), "w") as f:
            f.write("{")
        v = S.listar_versoes()
        self.assertEqual((v[0]["motivo"], v[0]["investimentos"], v[0]["total"]), ("antes-de-importar", 1, 250))
        self.assertNotIn("quebrada.json", [x["nome"] for x in v])
        os.remove(os.path.join(S.VERSOES, "quebrada.json"))

    def test_relatorio(self):
        d = dados(bancos=[{"id": "b", "nome": "Banco Azul", "cor": "#123456"}], investimentos=[
            {"id": "1", "nome": "CDB <b>Azul</b>", "banco": "b", "valor": 1000, "indexador": "cdi_pct", "taxa": 100, "tipo": "cdb", "vencimento": "2028-01-01"},
            {"id": "2", "nome": "Da Mãe", "valor": 500, "indexador": "parado", "titular": "terceiros", "terceiro": "Mãe"}])
        d["ajustes"].update(cor="#ff0000;background:url(x)", cor_dia=False)
        h = S.gerar_relatorio(d)
        h = h.decode() if isinstance(h, bytes) else h
        self.assertIn("CDB &lt;b&gt;Azul&lt;/b&gt;", h, "o nome não vira HTML")
        self.assertIn("Mãe", h)
        self.assertNotIn("url(x)", h, "a cor não injeta CSS")
        self.assertIn(":root{--a:#ff0000;", h, "com a Cor do dia desligada, a cor escolhida")

    def test_relatorio_na_cor_do_dia(self):
        class Dia(date):
            @classmethod
            def today(cls):
                return date(2026, 11, 11)
        d = dados(investimentos=[{"id": "1", "nome": "CDB Azul", "valor": 1000, "indexador": "parado", "tipo": "cdb"}])
        d["ajustes"]["cor"] = "#8BD45F"  # escolhida antes: a Cor do dia vale mesmo assim
        with mock.patch.object(S.calc, "date", Dia):
            h = S.gerar_relatorio(d)
        h = h.decode() if isinstance(h, bytes) else h
        self.assertIn(":root{--a:#FF5A4F;", h, "11/11/2026: Vermelho")

    def relatorio(self, tema=None, ajuste="auto"):
        d = dados(investimentos=[{"id": "1", "nome": "CDB Azul", "valor": 1000, "indexador": "parado"}])
        d["ajustes"]["tema"] = ajuste
        return S.gerar_relatorio(d, tema).decode()

    def test_relatorio_no_tema_que_o_app_manda(self):
        self.assertIn('<html lang="pt-BR" data-theme="dark">', self.relatorio("escuro"))
        self.assertIn('<html lang="pt-BR" data-theme="light">', self.relatorio("claro", ajuste="escuro"), "vale o que o app está usando")

    def test_relatorio_sem_o_app_usa_mais_aparencia(self):
        self.assertIn('data-theme="dark"', self.relatorio(ajuste="escuro"))
        self.assertIn('data-theme="light"', self.relatorio("qualquer", ajuste="claro"), "tema desconhecido: o de Mais › Aparência")

    def test_relatorio_automatico_segue_o_home_assistant_e_o_aparelho(self):
        h = self.relatorio()
        self.assertIn('<html lang="pt-BR">', h)
        self.assertIn("parent.document.querySelector('home-assistant')", h, "o tema do Home Assistant, quando abre dentro dele")
        self.assertIn('@media (prefers-color-scheme:dark){:root:not([data-theme="light"])', h, "senão, o do aparelho")
        self.assertNotIn("home-assistant", self.relatorio("escuro"), "com o tema do app, não precisa adivinhar")

    def test_relatorio_no_papel_e_sempre_claro(self):
        h = self.relatorio("escuro")
        impressao = h[h.index("@media print"):]
        self.assertIn(':root,:root[data-theme],:root:not([data-theme="light"]){--bg:#fff;--fg:#141a22', impressao)

    def test_bens_quando_o_inventaria_quebra(self):
        Trocar(self, BENS=type("B", (), {"ler": lambda self, forcar=False: (_ for _ in ()).throw(KeyError("x"))})())
        self.assertIn("Não consegui ler o InventarIA", S.bens_estado(dados())["motivo"])

    def test_falar_pelo_servidor(self):
        Trocar(self, IA_MOCK=True)
        self.assertTrue(S.voz_status()["pronta"])
        self.assertIn("mercado", S.voz_texto(b"\0\1" * 8000)["texto"])
        with self.assertRaises(ValueError):
            S.voz_texto(b"\0" * 10)


# ---------------------------------------------------------------------------------------------------------------
class TestPlanilhaDoCaixa(unittest.TestCase):
    def test_linhas(self):
        import csv
        import io
        d = dados(bancos=[{"id": "b", "nome": "Banco Azul", "contas": [{"id": "k", "pessoa": "Ana"}]}], categorias=[{"id": "c-mer", "nome": "Mercado"}],
                  recorrencias=[{"id": "r-ap", "tipo": "despesa", "descricao": "Reserva", "valor": 500, "dia": 5, "inicio": "2026-01", "aporte": True},
                                {"id": "r-seg", "tipo": "despesa", "descricao": "Seguro", "valor": 1200, "dia": 10, "inicio": "2026-03", "fim": "2027-12", "freq": "anual"}],
                  lancamentos=[{"id": "s", "tipo": "receita", "descricao": "Salário", "valor": 5000, "data": "2026-11-01", "conta": "k", "pago": True,
                                "descontos": [{"descricao": "Plano de saúde", "valor": 400, "categoria": "c-mer"}]},
                               {"id": "m", "tipo": "despesa", "descricao": "Feira", "valor": 1234.5, "data": "2026-11-03", "categoria": "c-mer", "obs": "sábado"},
                               {"id": "a", "tipo": "despesa", "descricao": "Reserva", "valor": 500, "data": "2026-11-05", "recorrencia": "r-ap", "competencia": "2026-11"},
                               {"id": "j", "tipo": "despesa", "descricao": "Ajuste", "valor": 3, "data": "2026-11-04", "ajuste": True},
                               {"id": "p", "tipo": "despesa", "descricao": "Pulado", "valor": 9, "data": "2026-11-06", "pulado": True}])
        b = S.gerar_csv_lancamentos(S.normalizar(d))
        self.assertTrue(b.startswith("\ufeff".encode()), "o Excel abre com acento")
        linhas = list(csv.reader(io.StringIO(b.decode("utf-8-sig")), delimiter=";"))
        cab, corpo = linhas[0], linhas[1:]
        col = lambda nome: [r[cab.index(nome)] for r in corpo]
        self.assertEqual(col("Tipo"), ["Recebimento", "Desconto do recebimento", "Despesa", "Despesa", "Aporte", "Aporte mensal", "Despesa fixa"])
        self.assertNotIn("Pulado", col("Descrição"))
        self.assertEqual(col("Descrição")[1], "Plano de saúde (de Salário)")
        self.assertEqual(col("Valor")[2], "1.234,50", "como no Brasil")
        self.assertEqual(col("Situação")[:3], ["Recebido", "Pago", "A pagar"])
        self.assertEqual(col("Categoria")[3], "Ajuste de saldo")
        self.assertEqual(col("Conta")[:2], ["Banco Azul · Ana"] * 2, "o desconto sai da mesma conta")
        self.assertEqual(col("Data")[-2:], ["todo dia 5", "todo ano, dia 10/03"])
        self.assertEqual(col("Situação")[-1], "desde 2026-03 até 2027-12")
        self.assertEqual(col("Fixo")[-2:], ["Sim", "Anual"])


class TestPedidosAIA(unittest.TestCase):
    def test_instrucoes_por_modo(self):
        d = S.normalizar(dados(bancos=[{"id": "b", "nome": "Banco Azul"}], investimentos=[{"id": "i1", "nome": "CDB Azul", "banco": "b", "valor": 1500}]))
        h = S.ia_prompt(d, "holerite", False, "Salário bruto 5.000")
        self.assertIn("recibos de pagamento", h)
        self.assertIn("<<<\nSalário bruto 5.000\n>>>", h)
        self.assertIn("Leia o anexo.", S.ia_prompt(d, "holerite", True, ""))
        inv = S.ia_prompt(d, "invest", True, "")
        self.assertIn("i1 | CDB Azul | Banco Azul | 1500.00", inv, "a IA vê o que já existe para não duplicar")
        self.assertIn("Leia o texto colado", S.ia_prompt(d, "invest", False, "aplicação"))

    def test_ler_uma_imagem_guardada(self):
        import base64
        Trocar(self, IA_MOCK=True)
        S.salvar(S.vazio(), versao=False)
        f = S.salvar_foto({"jpg": base64.b64encode(JPG).decode()})["arquivo"]
        r = S.ia_ler({"modo": "invest", "foto": f})
        self.assertEqual(r["entidade"], "ai_task.simulada")
        self.assertTrue(r["itens"])
        with self.assertRaisesRegex(ValueError, "A imagem não foi encontrada"):
            S.ia_ler({"modo": "invest", "foto": "20990101-000000-ffffff.jpg"})

    def test_ia_dos_precos_no_home_assistant(self):
        resp = {"r": (200, {"service_response": {"data": {"planos": []}}})}
        ha = ServidorFalso({"/services/ai_task/generate_data": lambda h, c: resp["r"]})
        self.addCleanup(ha.fechar)
        Trocar(self, TOKEN="t", HA_API=ha.url, IA_MOCK=False)
        d = dados()
        d["ajustes"]["ia_entidade"] = "ai_task.minha"
        self.assertEqual(S.ia_gerar(d, "GerencIA: preços", "leia"), {"planos": []})
        enviado = json.loads(ha.pedidos[-1][3])
        self.assertEqual((enviado["entity_id"], enviado["task_name"]), ("ai_task.minha", "GerencIA: preços"))
        resp["r"] = (200, {"service_response": {}})
        with self.assertRaisesRegex(ValueError, "não devolveu"):
            S.ia_gerar(d, "x", "y")
        resp["r"] = (500, "pane")
        with self.assertRaisesRegex(S.ErroHA, "recusou o pedido: pane"):
            S.ia_gerar(d, "x", "y")

    def test_pagina_de_verdade(self):
        html = "<html><body>Plano R$ 23,90 por mês</body></html>"
        srv = ServidorFalso({"/precos": (200, html)})
        self.addCleanup(srv.fechar)
        Trocar(self, FONTES_MOCK=None)
        self.assertEqual(S.buscar_pagina({"id": "x", "url": srv.url + "/precos"}), html)
        cab = srv.pedidos[-1][2]
        self.assertIn("GerencIA/", cab["User-Agent"])
        self.assertTrue(cab["Accept-Language"].startswith("pt-BR"))


class TestSensorDeUsoDaIA(unittest.TestCase):
    def setUp(self):
        self.ha = ServidorFalso({})
        self.ha.rotas = _Tudo200()
        self.addCleanup(self.ha.fechar)
        Trocar(self, TOKEN="t", HA_API=self.ha.url, IA_MOCK=False)
        d = dados()
        d["ajustes"]["sensores"] = True
        S.salvar(d, versao=False)

    def test_publica_as_chamadas_de_hoje(self):
        S.registrar_uso("caixa", "ai_task.x", 100, 50, 1, 1.0, "ok")
        S.publicar_uso_sensor()
        p = [x for x in self.ha.pedidos if x[1] == "/states/" + S.USO_SENSOR]
        corpo = json.loads(p[-1][3])
        self.assertGreaterEqual(corpo["state"], 1)
        self.assertEqual(corpo["attributes"]["unit_of_measurement"], "chamadas")
        self.assertIn("caixa", corpo["attributes"]["por_tipo"])

    def test_sem_sensores_ou_sem_ia_nao_publica(self):
        d = S.ler()
        d["ajustes"]["ia"] = False
        S.salvar(d, versao=False)
        S.publicar_uso_sensor()
        self.assertEqual([x for x in self.ha.pedidos if x[1] == "/states/" + S.USO_SENSOR], [])

    def test_home_assistant_fora_nao_quebra(self):
        Trocar(self, HA_API=f"http://127.0.0.1:{porta_fechada()}")
        S._uso_sensor["dia"] = None
        S.publicar_uso_sensor()
        self.assertEqual(S._uso_sensor["dia"], S.uso_dia())


# ---------------------------------------------------------------------------------------------------------------
class TestRotina(unittest.TestCase):
    def test_uma_volta(self):
        """A rotina de 15 em 15 minutos: índices (se precisa), o ponto do dia, a conexão com outros apps e as dicas."""
        srv = ServidorFalso({f"/serie/{s}/ultimos/1": (200, [{"data": "31/10/2026", "valor": "12"}]) for s in (432, 4389, 13522, 226)})
        self.addCleanup(srv.fechar)
        d = dados(investimentos=[{"id": "x", "valor": 100, "indexador": "parado"}])
        d["indices"]["fonte"] = "padrao"
        S.salvar(d, versao=False)
        S.gravar_arquivo(S.ARQ, json.dumps(dict(S.ler(), historico=[])))

        class Para(Exception):
            pass

        def dormir(_):
            raise Para()

        Trocar(self, BCB=srv.url + "/serie/{s}", FONTES_MOCK=FONTES, IA_MOCK=True)
        Trocar(self, time=type("T", (), {"sleep": staticmethod(dormir), "time": staticmethod(time.time)}))
        with self.assertRaises(Para):
            S.rotina()
        d = S.ler()
        self.assertEqual((d["indices"]["fonte"], d["indices"]["cdi"]), ("bcb", 12.0))
        self.assertEqual([h["d"] for h in d["historico"]], [date.today().isoformat()], "o ponto de hoje")
        self.assertTrue(os.path.exists(os.path.join(S.SHARE_DIR, "integracao.json")), "a conexão com outros apps publicada")


if __name__ == "__main__":
    unittest.main()
