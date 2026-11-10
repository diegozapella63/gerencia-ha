"""Faturas por e-mail (emails.py e a parte do server.py): o evento imap_content do Home Assistant, o PDF anexado
(imap.fetch_part), as senhas dos PDFs, a leitura pela IA (simulada) e o que a tela vê. Faturas e remetentes inventados
(Banco Azul, Banco Verde, ana@exemplo.com)."""
import base64
import io
import json
import os
import shutil
import threading
import time
import unittest
import zipfile
from unittest import mock

from tests.base import importar_servidor, Servidor, WSFalso
S = importar_servidor()
import emails as E  # noqa: E402  (o importar_servidor põe gerencia/app no caminho)
import voz  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "pdf_senha")


def arq(nome):
    with open(os.path.join(FIX, nome), "rb") as f:
        return f.read()


def evento(uid="101", de="Banco Azul <fatura@bancoazul.com.br>", assunto="Sua fatura de novembro", arquivo="fatura-nov.pdf", pdf=True, entry="imap-ana"):
    partes = {"0": {"content_type": "text/plain"}}
    if pdf:
        partes["1"] = {"content_type": "application/pdf", "filename": arquivo, "content_transfer_encoding": "base64"}
    return {"entry_id": entry, "uid": uid, "sender": de, "subject": assunto, "date": "2026-11-07T08:30:00-03:00", "initial": True,
            "server": "imap.gmail.com", "username": "ana@exemplo.com", "search": "UnSeen UnDeleted", "folder": "INBOX", "parts": partes}


def resposta_fetch_part(pdf, cte="base64"):
    dados = base64.encodebytes(pdf).decode() if cte == "base64" else pdf.decode("latin-1")
    return {"changed_states": [], "service_response": {"part_data": dados, "content_type": "application/pdf", "content_transfer_encoding": cte,
                                                       "filename": "fatura-nov.pdf", "part": "1", "uid": "101"}}


def esperar(cond, s=10):
    fim = time.time() + s
    while time.time() < fim:
        if cond():
            return True
        time.sleep(0.05)
    return False


# ---------------------------------------------------------------------------------------------------------------
class TestModulo(unittest.TestCase):
    def test_anexo_pdf(self):
        self.assertEqual(E.anexo_pdf(evento()["parts"]), ("1", "fatura-nov.pdf"))
        self.assertEqual(E.anexo_pdf({"0,1": {"content_type": "application/octet-stream", "filename": "Fatura.PDF"}}), ("0,1", "Fatura.PDF"),
                         "pelo nome, mesmo sem o tipo certo (e dentro de outra parte)")
        self.assertEqual(E.anexo_pdf({"1": {"content_type": "application/pdf"}}), ("1", "fatura.pdf"), "sem nome")
        self.assertEqual(E.anexo_pdf(evento(pdf=False)["parts"]), (None, None))
        self.assertEqual(E.anexo_pdf({"1": "x", "2": {"content_type": "image/png", "filename": "logo.png"}}), (None, None))
        self.assertEqual(E.anexo_pdf(None), (None, None))

    def test_decodificar(self):
        pdf = arq("fatura-azul.pdf")
        self.assertEqual(E.decodificar(base64.encodebytes(pdf).decode(), "base64"), pdf, "com as quebras de linha do e-mail")
        self.assertEqual(E.decodificar("%PDF-1.4 =C3=A9", "quoted-printable"), "%PDF-1.4 é".encode())
        self.assertEqual(E.decodificar("%PDF-1.4 abc", "7bit"), b"%PDF-1.4 abc")
        self.assertEqual(E.decodificar("%PDF", None), b"%PDF")
        with self.assertRaisesRegex(ValueError, "O anexo do e-mail veio estragado."):
            E.decodificar("isto não é base64!!", "base64")

    def test_remetente(self):
        self.assertEqual(E.endereco("Banco Azul <Fatura@BancoAzul.com.br>"), "fatura@bancoazul.com.br")
        self.assertEqual(E.endereco("fatura@bancoazul.com.br"), "fatura@bancoazul.com.br")
        self.assertEqual(E.nome_remetente('"Banco Azul" <fatura@bancoazul.com.br>'), "Banco Azul")
        self.assertEqual(E.nome_remetente("fatura@bancoazul.com.br"), "fatura@bancoazul.com.br")
        self.assertEqual(E.limpar_remetente(" @BancoAzul.com.br "), "bancoazul.com.br")
        self.assertEqual(E.limpar_remetente("Banco Azul <fatura@bancoazul.com.br>"), "fatura@bancoazul.com.br")
        self.assertEqual(len(E.limpar_remetente("a" * 200)), 80)

    def test_e_fatura(self):
        de = "Banco Azul <fatura@bancoazul.com.br>"
        self.assertTrue(E.e_fatura(de, "Qualquer", "x.pdf", ["bancoazul.com.br"]))
        self.assertTrue(E.e_fatura(de, "Qualquer", "x.pdf", ["fatura@bancoazul.com.br"]))
        self.assertTrue(E.e_fatura("x <a@mail.bancoazul.com.br>", "", "", ["bancoazul.com.br"]), "subdomínio")
        self.assertFalse(E.e_fatura("x <a@outrobancoazul.com.br>", "Fatura", "", ["bancoazul.com.br"]), "só o domínio inteiro")
        self.assertFalse(E.e_fatura("Banco Verde <fatura@bancoverde.com.br>", "Fatura", "fatura.pdf", ["bancoazul.com.br"]),
                         "com remetentes, só eles (nem o assunto vale)")
        self.assertTrue(E.e_fatura("Banco Verde <x@bancoverde.com.br>", "Sua FATURA chegou", "doc.pdf", []))
        self.assertTrue(E.e_fatura("x@y.com", "Documento", "Fatura-Novembro.pdf", None), "pelo nome do PDF")
        self.assertFalse(E.e_fatura("x@y.com", "Promoção imperdível", "folheto.pdf", ["  "]), "remetente em branco não conta")
        self.assertTrue(E.e_fatura("Imobiliária Sol <boletos@imobsol.com.br>", "Boleto de aluguel - novembro", "doc.pdf", []), "boleto também vale")
        self.assertTrue(E.e_fatura("x@condominio.com.br", "Cobrança", "Boleto_Condominio.pdf", []))

    def test_recibos_e_assinaturas_tambem_contam(self):
        for assunto in ("Home Assistant Cloud subscription receipt", "Recibo de pagamento", "Your invoice #123", "Cobrança de novembro",
                        "Nota fiscal eletrônica", "Renovação da sua assinatura", "Mensalidade de dezembro", "Your renewal"):
            with self.subTest(assunto=assunto):
                self.assertTrue(E.e_fatura("Nuvem <suporte@nuvem.exemplo>", assunto, "doc.pdf", []))
        self.assertFalse(E.e_fatura("Aérea <noreply@checkin.aerea.exemplo>", "Seu cartão de embarque está pronto!", "embarque.pdf", []))

    def test_regras_por_remetente(self):
        regras = [{"de": "nuvem.exemplo", "acao": "fixo", "fixo": "r1"}, {"de": "promo@nuvem.exemplo", "acao": "nunca"}, {"de": "lojalua.exemplo", "acao": "nunca"}]
        self.assertEqual(E.regra("Nuvem <suporte@nuvem.exemplo>", regras)["acao"], "fixo")
        self.assertEqual(E.regra("promo@nuvem.exemplo", regras)["acao"], "nunca", "o endereço inteiro vale sobre o domínio")
        self.assertIsNone(E.regra("x@outranuvem.exemplo", regras))
        self.assertTrue(E.e_fatura("suporte@nuvem.exemplo", "Olá", "doc.pdf", ["bancoazul.com.br"], regras), "um fixo é lido sempre, mesmo fora do De quem")
        self.assertFalse(E.e_fatura("Loja Lua <boleto@lojalua.exemplo>", "Seu boleto", "boleto.pdf", [], regras), "nunca, mesmo com boleto")

    def test_chave(self):
        self.assertEqual(E.chave(evento()), "imap-ana|101|Sua fatura de novembro")

    def test_chave_pelo_conteudo(self):
        """1.54.1: o mesmo e-mail com outro número (o aviso e o Procurar faturas agora numeram diferente) tem a mesma chave."""
        k = E.chave_conteudo("imap-ana", "Banco Azul <Fatura@BancoAzul.com.br>", "2026-11-07T08:30:00-03:00", "Sua Fatura de Novembro", "fatura-nov.pdf")
        self.assertEqual(k, "c|imap-ana|fatura@bancoazul.com.br|2026-11-07T08:30:00|sua fatura de novembro")
        for data in ("Sat, 07 Nov 2026 08:30:00 -0300", "2026-11-07T08:30:00.123456-03:00"[:25], "Sat, 07 Nov 2026 08:30:00 -0300"[:25]):
            with self.subTest(data=data):
                self.assertEqual(E.chave_conteudo("imap-ana", "fatura@bancoazul.com.br", data, "Sua fatura de novembro"), k, "a data em outro jeito, ou cortada")
        self.assertNotEqual(E.chave_conteudo("imap-ana", "fatura@bancoazul.com.br", "2026-12-07T08:30:00", "Sua fatura de novembro"), k, "outro e-mail")
        self.assertEqual(E.chave_conteudo("imap-ana", "x@y.com", "", "Fatura", "a.pdf"), "c|imap-ana|x@y.com|a:a.pdf|fatura", "sem a data, o anexo")
        self.assertEqual(E.chave_conteudo("imap-ana", "x@y.com", "lixo", "Fatura"), "c|imap-ana|x@y.com|lixo|fatura")
        self.assertEqual(E.chave_conteudo("", "x@y.com", "2026-11-07", "Fatura"), "", "sem a conta, não há como saber")


# ---------------------------------------------------------------------------------------------------------------
class TestEscuta(unittest.TestCase):
    """O WebSocket do Home Assistant de mentira (WSFalso): assina o evento, recebe e para quando desliga."""

    def setUp(self):
        self.recebidos, self.registro = [], []
        self.ligada = {"on": True}

    def escuta(self, url, **kw):
        e = E.Escuta(url, "token-teste", self.recebidos.append, lambda: self.ligada["on"], lambda *a: self.registro.append(" ".join(map(str, a))),
                     espera=kw.pop("espera", 0.2), atraso=kw.pop("atraso", 0.05), **kw)
        self.addCleanup(e.parar)
        return e

    def test_assina_o_evento_e_recebe_cada_email(self):
        def responder(cmd):
            self.assertEqual(cmd, {"id": 1, "type": "subscribe_events", "event_type": "imap_content"})
            return [{"id": 1, "type": "result", "success": True, "result": None},
                    {"id": 1, "type": "event", "event": {"event_type": "imap_content", "data": evento("1")}},
                    {"id": 1, "type": "event", "event": {"event_type": "imap_content", "data": evento("2")}},
                    {"id": 7, "type": "event", "event": {"data": evento("x")}}]  # de outra assinatura: fica fora
        ws = WSFalso(responder)
        self.addCleanup(ws.fechar)
        e = self.escuta(ws.url)
        e.iniciar()
        self.assertTrue(esperar(lambda: len(self.recebidos) == 2))
        self.assertTrue(e.conectada)
        self.assertEqual(sorted(x["uid"] for x in self.recebidos), ["1", "2"])
        self.ligada["on"] = False
        self.assertTrue(esperar(lambda: not e.conectada), "desligou: fecha a conexão")
        self.assertTrue(esperar(lambda: any(op == 8 for op, _, _ in ws.recebido)), "com o fechamento educado")

    def test_desligada_nem_conecta_e_acordar_conecta_logo(self):
        conexoes = []
        self.ligada["on"] = False
        ws = WSFalso(lambda c: conexoes.append(c) or [{"id": 1, "type": "result", "success": True}])
        self.addCleanup(ws.fechar)
        e = self.escuta(ws.url, espera=30)
        e.iniciar()
        time.sleep(0.3)
        self.assertEqual(conexoes, [])
        self.ligada["on"] = True
        e.acordar()
        self.assertTrue(esperar(lambda: len(conexoes) == 1, 3), "conecta sem esperar os 30 s")

    def test_caiu_reconecta_e_avisa_o_erro_uma_vez(self):
        vezes = []

        def responder(cmd):
            vezes.append(1)
            if len(vezes) < 3:
                return [("cortar",)]
            return [{"id": 1, "type": "result", "success": True}, {"id": 1, "type": "event", "event": {"data": evento("9")}}]
        ws = WSFalso(responder)
        self.addCleanup(ws.fechar)
        e = self.escuta(ws.url)
        e.iniciar()
        self.assertTrue(esperar(lambda: self.recebidos))
        self.assertEqual(len(vezes), 3)
        self.assertEqual(len([r for r in self.registro if "sem a conexão" in r]), 1, "o mesmo erro, uma vez só no registro")

    def test_assinatura_recusada(self):
        ws = WSFalso(lambda c: [{"id": 1, "type": "result", "success": False, "error": {"message": "Sem permissão"}}])
        self.addCleanup(ws.fechar)
        e = self.escuta(ws.url, atraso=10)
        e.iniciar()
        self.assertTrue(esperar(lambda: e.erro == "Sem permissão"))
        self.assertFalse(e.conectada)

    def test_sem_resposta_da_assinatura(self):
        ws = WSFalso(lambda c: [])
        self.addCleanup(ws.fechar)
        e = self.escuta(ws.url, atraso=10)
        e.iniciar()
        self.assertTrue(esperar(lambda: e.erro in ("O Home Assistant não respondeu.", "O Home Assistant fechou a conexão.")))

    def test_ping_quando_fica_calado(self):
        conexoes = []
        ws = WSFalso(lambda c: conexoes.append(c) or [{"id": 1, "type": "result", "success": True}])
        self.addCleanup(ws.fechar)
        e = self.escuta(ws.url, espera=0.2)
        e.iniciar()
        self.assertTrue(esperar(lambda: any(op == 1 and b'"ping"' in d for op, _, d in ws.recebido), 5), "manda um ping")
        self.assertTrue(esperar(lambda: len(conexoes) >= 2, 5), "sem resposta, reconecta")

    def test_erro_ao_tratar_o_evento_vai_para_o_registro(self):
        ws = WSFalso(lambda c: [{"id": 1, "type": "result", "success": True}, {"id": 1, "type": "event", "event": {"data": evento("3")}}])
        self.addCleanup(ws.fechar)
        e = E.Escuta(ws.url, "token-teste", lambda d: 1 / 0, lambda: True, lambda *a: self.registro.append(" ".join(map(str, a))), espera=0.2, atraso=10)
        self.addCleanup(e.parar)
        e.iniciar()
        self.assertTrue(esperar(lambda: any("division" in r for r in self.registro)))

    def test_ligada_que_falha_conta_como_desligada(self):
        e = E.Escuta("ws://127.0.0.1:9/x", "t", print, lambda: 1 / 0, print)
        self.assertFalse(e._ligada())

    def test_iniciar_duas_vezes_nao_abre_outra(self):
        self.ligada["on"] = False
        e = self.escuta("ws://127.0.0.1:9/x", espera=5)
        e.iniciar()
        t = e._thread
        e.iniciar()
        self.assertIs(e._thread, t)


class TestConexaoWS(unittest.TestCase):
    def test_ler_com_espera_devolve_none_sem_nada(self):
        ws = WSFalso(lambda c: [])
        self.addCleanup(ws.fechar)
        with voz.ConexaoWS(ws.url, "token-teste", timeout=3) as c:
            c.enviar({"id": 1, "type": "x"})
            t0 = time.time()
            self.assertIsNone(c.ler(0.2))
            self.assertLess(time.time() - t0, 2)

    def test_token_errado(self):
        ws = WSFalso(lambda c: [], token="outro")
        self.addCleanup(ws.fechar)
        with self.assertRaisesRegex(voz.ErroVoz, "recusou o acesso"):
            voz.ConexaoWS(ws.url, "token-teste", timeout=3)


# ---------------------------------------------------------------------------------------------------------------
class ComServidor(unittest.TestCase):
    def setUp(self):
        for p in (S.EMAILS_ARQ, S.SENHAS_ARQ):
            if os.path.exists(p):
                os.remove(p)
        shutil.rmtree(S.EMAILS_PDF, ignore_errors=True)
        S.EMAIL_SIMULADO.clear()
        self.ajustar(email=True, email_de=["bancoazul.com.br"], ia=True, email_aviso=False, email_para=[])
        self.pedidos = []
        self.resposta = resposta_fetch_part(arq("fatura-azul.pdf"))
        p = mock.patch.object(S, "ha_request", self.ha)
        p.start()
        self.addCleanup(p.stop)
        p = mock.patch.object(S.time, "sleep")  # a IA simulada espera 1,2 s
        p.start()
        self.addCleanup(p.stop)

    def ha(self, metodo, caminho, corpo=None, timeout=20):
        self.pedidos.append((metodo, caminho, corpo))
        if isinstance(self.resposta, Exception):
            raise self.resposta
        return self.resposta

    def ajustar(self, **aj):
        with S.TRAVA:
            d = S.ler()
            d["ajustes"].update(aj)
            S.salvar(d, versao=False)

    def itens(self):
        return S.emails_ler()["itens"]


class TestEmailChegou(ComServidor):
    def test_fatura_do_remetente_e_lida_e_espera_a_conferencia(self):
        eid = S.email_chegou(evento())
        self.assertEqual(self.pedidos, [("POST", "/services/imap/fetch_part?return_response", {"entry": "imap-ana", "uid": "101", "part": "1"})])
        it = self.itens()[0]
        self.assertEqual((it["id"], it["estado"], it["erro"], it["arquivo"]), (eid, "conferir", "", "fatura-nov.pdf"))
        self.assertTrue(it["resultado"]["lancamentos"], "o que a IA leu fica guardado")
        self.assertTrue(os.path.isfile(S._email_pdf(eid)), "uma cópia do PDF")
        pub = S.email_publico(it)
        self.assertEqual((pub["de"], pub["endereco"], pub["assunto"]), ("Banco Azul", "fatura@bancoazul.com.br", "Sua fatura de novembro"))
        for k in ("entry", "uid", "parte", "chave"):
            self.assertNotIn(k, pub, "a tela não vê os ids da conta e da mensagem")
        self.assertEqual(pub["resultado"], it["resultado"])

    def test_o_mesmo_email_de_novo_nao_entra_duas_vezes(self):
        S.email_chegou(evento())
        self.assertIsNone(S.email_chegou(dict(evento(), initial=False)), "o Home Assistant manda o último de novo quando reinicia")
        self.assertEqual(len(self.itens()), 1)
        self.assertEqual(len(self.pedidos), 1)

    def test_o_mesmo_email_com_outro_numero_nao_entra_duas_vezes(self):
        """1.54.1: o aviso do Home Assistant e o Procurar faturas agora davam números diferentes ao mesmo e-mail, e ele
        entrava duas vezes (e o PDF de um deles não abria)."""
        S.email_chegou(evento("9001"))
        self.assertIsNone(S.email_chegou(dict(evento("40"), date="Sat, 07 Nov 2026 08:30:00 -0300")), "o mesmo, achado pelo Procurar")
        self.assertEqual((len(self.itens()), len(self.pedidos)), (1, 1))
        self.assertIsNotNone(S.email_chegou(evento("41", assunto="Sua fatura de dezembro")), "outro e-mail do mesmo remetente entra")

    def test_o_que_nao_abriu_por_um_numero_tenta_pelo_outro(self):
        """Se o PDF não abriu pelo número de um jeito (o anexo vinha de outro e-mail), o mesmo e-mail com o outro número
        lê de novo no mesmo lugar, sem criar outro."""
        ruim, self.resposta = self.resposta, {"service_response": {"part_data": "", "content_transfer_encoding": "base64"}}
        eid = S.email_chegou(evento("9001"))
        self.assertEqual((self.itens()[0]["estado"], self.itens()[0]["erro"]), ("erro", "O anexo do e-mail não é um PDF."))
        self.resposta = ruim
        self.assertEqual(S.email_chegou(evento("40")), eid, "o mesmo, pelo número do Procurar")
        it = self.itens()
        self.assertEqual((len(it), it[0]["estado"], it[0]["uid"]), (1, "conferir", "40"))
        self.assertIsNone(S.email_chegou(evento("40")), "e não lê uma terceira vez")

    def test_os_repetidos_de_antes_viram_um(self):
        """Os que já tinham entrado duas vezes ficam um só (o que andou mais, como o que espera a conferência), e o PDF
        do outro sai. Os do WhatsApp não têm conta nem data: ficam todos."""
        base = {"entry": "imap-ana", "de": "Banco Azul <fatura@bancoazul.com.br>", "assunto": "Sua fatura de novembro", "data": "2026-11-07T08:30:00-03:00",
                "arquivo": "fatura-nov.pdf", "parte": "1", "erro": "", "recebido_em": "2026-11-07T09:00:00"}
        itens = [dict(base, id="aaaaaaaaaaaa", uid="40", estado="erro", erro="O anexo do e-mail não é um PDF."),
                 dict(base, id="bbbbbbbbbbbb", uid="9001", estado="conferir"),
                 dict(base, id="cccccccccccc", uid="39", estado="erro", erro="O anexo do e-mail não é um PDF."),
                 dict(base, id="dddddddddddd", uid="12", estado="fora", assunto="Outro"),
                 {"id": "eeeeeeeeeeee", "origem": "whatsapp", "chave": "", "de": "Ana", "assunto": "foto", "estado": "conferir"},
                 {"id": "ffffffffffff", "origem": "whatsapp", "chave": "", "de": "Ana", "assunto": "foto", "estado": "conferir"}]
        os.makedirs(S.EMAILS_PDF, exist_ok=True)
        for x in itens:
            with open(S._email_pdf(x["id"]), "wb") as f:
                f.write(b"%PDF-1.4")
        S._emails_gravar({"itens": itens, "vistos": []})
        self.assertEqual([x["id"] for x in self.itens()], ["bbbbbbbbbbbb", "dddddddddddd", "eeeeeeeeeeee", "ffffffffffff"])
        self.assertFalse(os.path.exists(S._email_pdf("aaaaaaaaaaaa")) or os.path.exists(S._email_pdf("cccccccccccc")), "os PDFs dos repetidos saem")
        self.assertTrue(os.path.exists(S._email_pdf("bbbbbbbbbbbb")))
        self.assertIsNone(S.email_chegou(evento("38")), "e o mesmo e-mail de novo não volta")

    def test_de_outro_remetente_fica_guardado_sem_ler(self):
        S.email_chegou(evento(de="Loja <ofertas@lojaexemplo.com>", assunto="Fatura da loja"))
        self.assertEqual((self.itens()[0]["estado"], self.pedidos), ("fora", []))

    def test_sem_remetentes_le_pelo_assunto(self):
        self.ajustar(email_de=[])
        S.email_chegou(evento("1", de="Banco Verde <x@bancoverde.com.br>", assunto="Promoção", arquivo="folheto.pdf"))
        S.email_chegou(evento("2", de="Banco Verde <x@bancoverde.com.br>", assunto="Sua fatura chegou"))
        self.assertEqual([x["estado"] for x in self.itens()], ["conferir", "fora"], "o mais novo primeiro")

    def test_regras_do_remetente(self):
        self.ajustar(email_remetentes=[{"de": "lojalua.exemplo", "acao": "nunca"}, {"de": "nuvem.exemplo", "acao": "fixo", "fixo": "r-nuvem"}])
        self.assertIsNone(S.email_chegou(evento("1", de="Loja Lua <boleto@lojalua.exemplo>", assunto="Seu boleto")))
        self.assertEqual(self.itens(), [], "nunca considerar: nem entra")
        self.assertIsNone(S.email_chegou(evento("1", de="Loja Lua <boleto@lojalua.exemplo>", assunto="Seu boleto")), "e não volta")
        S.email_chegou(evento("2", de="Nuvem <suporte@nuvem.exemplo>", assunto="Olá", arquivo="doc.pdf"))
        self.assertEqual(self.itens()[0]["estado"], "conferir", "sempre é um fixo: lido mesmo fora do De quem e sem fatura no assunto")
        # os que chegaram antes da regra somem da lista
        S.email_chegou(evento("3", de="Loja Sol <x@lojasol.exemplo>", assunto="Fatura"))
        self.assertEqual(len(S.emails_estado()["itens"]), 2)
        self.ajustar(email_remetentes=[{"de": "lojasol.exemplo", "acao": "nunca"}])
        self.assertEqual([x["endereco"] for x in S.emails_estado()["itens"]], ["suporte@nuvem.exemplo"])

    def test_regras_limpas(self):
        d = S.ler()
        d["ajustes"]["email_remetentes"] = [{"de": "Nuvem <Suporte@Nuvem.exemplo>", "acao": "fixo", "fixo": "r1"}, {"de": "x.exemplo", "acao": "outra"},
                                            {"de": "y.exemplo", "acao": "fixo"}, {"de": "", "acao": "nunca"}, "lixo",
                                            {"de": "suporte@nuvem.exemplo", "acao": "nunca"}]
        self.assertEqual(S.normalizar(d)["ajustes"]["email_remetentes"], [{"de": "suporte@nuvem.exemplo", "acao": "nunca"}],
                         "a última regra do mesmo remetente vale; sem fixo ou com ação desconhecida, sai")

    def test_sem_pdf_desligado_ou_sem_ia_nao_faz_nada(self):
        self.assertIsNone(S.email_chegou(evento(pdf=False)))
        self.assertIsNone(S.email_chegou(dict(evento(), uid="")))
        self.ajustar(email=False)
        self.assertIsNone(S.email_chegou(evento()))
        self.ajustar(email=True, ia=False)
        self.assertIsNone(S.email_chegou(evento()))
        self.assertEqual((self.itens(), self.pedidos), ([], []))

    def test_pdf_com_senha_espera_a_senha_e_uma_senha_nova_abre(self):
        self.resposta = resposta_fetch_part(arq("fatura-aes256.pdf"))
        eid = S.email_chegou(evento())
        it = self.itens()[0]
        self.assertEqual((it["estado"], it["erro"]), ("senha", "Este PDF tem senha."))
        self.assertTrue(S.email_pdf_b64(eid)["b64"].startswith("data:application/pdf;base64,"), "o PDF fica para digitar a senha na tela")
        self.assertEqual(S.email_pdf_b64(eid)["nome"], "fatura-nov.pdf")
        S.senha_nova("CPF da Ana", "12345")
        S.reler_emails_com_senha()
        self.assertTrue(esperar(lambda: self.itens()[0]["estado"] == "conferir"))
        self.assertEqual(len(self.pedidos), 1, "lê da cópia guardada, sem baixar de novo")

    def test_senha_guardada_no_ler_com_ia_reabre_as_outras_faturas(self):
        # duas faturas esperando a senha; a pessoa digita a senha numa delas no Ler com IA (guardar ligado)
        self.resposta = resposta_fetch_part(arq("fatura-aes256.pdf"))
        S.email_chegou(evento("101"))
        S.email_chegou(evento("102", assunto="Sua fatura de outubro"))
        self.assertEqual([x["estado"] for x in self.itens()], ["senha", "senha"])
        S.abrir_pdf(arq("fatura-aes256.pdf"), "12345", guardar=True, nome_arquivo="fatura-nov.pdf")
        self.assertEqual([x["nome"] for x in S.senhas_listar()], ["Da fatura fatura-nov"])
        self.assertTrue(esperar(lambda: [x["estado"] for x in self.itens()] == ["conferir", "conferir"]), self.itens())

    def test_reler_so_as_que_alguma_senha_abre(self):
        self.resposta = resposta_fetch_part(arq("fatura-aes256.pdf"))
        S.email_chegou(evento("101"))
        S.senha_nova("Outra", "99999")  # não abre esta fatura
        with mock.patch.object(S, "email_ler_depois") as ler:
            S.reler_emails_com_senha()
        ler.assert_not_called()
        self.assertEqual(self.itens()[0]["estado"], "senha", "continua esperando, sem passar por lendo")
        S.senha_nova("CPF da Ana", "12345")
        self.ajustar(ia=False)
        with mock.patch.object(S, "email_ler_depois") as ler:
            S.reler_emails_com_senha()
        ler.assert_not_called()  # com a IA desligada, nada
        self.ajustar(ia=True)
        with mock.patch.object(S, "email_ler_depois") as ler:
            S.reler_emails_com_senha()
        ler.assert_called_once_with(self.itens()[0]["id"])

    def test_com_a_senha_cadastrada_abre_direto(self):
        S.senha_nova("CPF da Ana", "12345")
        self.resposta = resposta_fetch_part(arq("fatura-rc4-128.pdf"))
        S.email_chegou(evento())
        self.assertEqual(self.itens()[0]["estado"], "conferir")

    def test_erro_do_home_assistant_e_ler_de_novo(self):
        self.resposta = S.ErroHA("Sem resposta do Home Assistant (timed out).")
        eid = S.email_chegou(evento())
        it = self.itens()[0]
        self.assertEqual((it["estado"], it["erro"]), ("erro", "Sem resposta do Home Assistant (timed out)."))
        self.resposta = resposta_fetch_part(arq("fatura-azul.pdf"))
        S.email_ler(eid)
        self.assertEqual(self.itens()[0]["estado"], "conferir")

    def test_anexo_que_nao_e_pdf(self):
        self.resposta = {"service_response": {"part_data": base64.b64encode(b"GIF89a").decode(), "content_transfer_encoding": "base64"}}
        S.email_chegou(evento())
        self.assertEqual(self.itens()[0]["erro"], "O anexo do e-mail não é um PDF.")

    def test_erro_inesperado_tambem_termina_em_erro(self):
        with mock.patch.object(S, "ia_ler", side_effect=KeyError("x")):
            S.email_chegou(evento())
        self.assertEqual((self.itens()[0]["estado"], self.itens()[0]["erro"]), ("erro", "Não consegui ler."))

    def test_ia_que_nao_acha_nada(self):
        with mock.patch.object(S, "ia_ler", return_value={"lancamentos": [], "investimentos": []}):
            S.email_chegou(evento())
        self.assertEqual(self.itens()[0]["erro"], "A IA não encontrou lançamentos neste PDF.")

    def test_quoted_printable(self):
        self.resposta = resposta_fetch_part(arq("fatura-azul.pdf"), cte="8bit")
        S.email_chegou(evento())
        self.assertEqual(self.itens()[0]["estado"], "conferir")

    def test_lancada_ou_ignorada_tira_o_pdf_e_o_que_a_ia_leu(self):
        a = S.email_chegou(evento("1"))
        b = S.email_chegou(evento("2", assunto="Outra fatura"))
        S._email_mudar(a, estado="feito")
        S._email_mudar(b, estado="ignorado")
        for it in self.itens():
            self.assertNotIn("resultado", it)
            self.assertFalse(os.path.exists(S._email_pdf(it["id"])))
        with self.assertRaisesRegex(ValueError, "O PDF desse e-mail não está mais aqui."):
            S.email_pdf_b64(a)
        with self.assertRaisesRegex(ValueError, "Esse e-mail não está mais aqui."):
            S._email_mudar("000000000000", estado="feito")

    def test_leitura_que_termina_depois_nao_volta_para_conferir(self):
        eid = S.email_chegou(evento())
        S._email_mudar(eid, estado="feito")
        self.assertEqual(S._email_mudar(eid, se="lendo", estado="conferir")["estado"], "feito")
        self.assertEqual(self.itens()[0]["estado"], "feito")

    def test_guarda_so_os_ultimos(self):
        with mock.patch.object(S, "EMAILS_MAX", 3):
            ids = [S.email_chegou(evento(str(n), assunto=f"Fatura {n}")) for n in range(5)]
        self.assertEqual([x["id"] for x in self.itens()], ids[::-1][:3])
        self.assertFalse(os.path.exists(S._email_pdf(ids[0])), "o PDF dos que saíram também sai")
        self.assertEqual(len(S.emails_ler()["vistos"]), 10, "mas continuam vistos (pelo número e pelo conteúdo)")

    def test_arquivo_estragado(self):
        S.gravar_arquivo(S.EMAILS_ARQ, "[1, 2]")
        self.assertEqual(S.emails_ler(), {"itens": [], "vistos": []})
        S.gravar_arquivo(S.EMAILS_ARQ, json.dumps({"itens": [{"id": "x"}, {"id": "abcdef012345", "estado": "voando"}, {"id": "abcdef012345", "estado": "fora"}], "vistos": ["a", 3]}))
        self.assertEqual(S.emails_ler(), {"itens": [{"id": "abcdef012345", "estado": "fora"}], "vistos": ["a"]})
        S.gravar_arquivo(S.EMAILS_ARQ, "não é json")
        self.assertEqual(S.emails_ler()["itens"], [])

    def test_ler_depois_em_segundo_plano(self):
        eid = S.email_chegou(evento(de="Loja <ofertas@lojaexemplo.com>"))
        S.email_ler_depois(eid)
        self.assertTrue(esperar(lambda: self.itens()[0]["estado"] == "conferir"))

    def test_carimbo_muda_quando_muda(self):
        c0 = S.emails_carimbo()
        time.sleep(0.02)
        S.email_chegou(evento())
        self.assertNotEqual(S.emails_carimbo(), c0)


class TestProcurar(ComServidor):
    """Procurar faturas agora: abre os e-mails mais novos pela ação imap.fetch (o "uid" da integração IMAP é o número
    da mensagem na pasta) e o que tiver PDF segue como um e-mail que chegou."""

    def setUp(self):
        super().setUp()
        self.caixa = {}  # número -> {sender, subject, date, parts}
        for n in range(1, 41):
            self.caixa[n] = {"sender": f"Loja {n} <oi@loja{n}.com>", "subject": f"Novidades {n}", "date": "2026-11-0%dT08:00:00" % (n % 9 + 1),
                             "parts": {"0": {"content_type": "text/plain"}}}
        pdf = lambda nome: {"0": {"content_type": "text/plain"}, "1": {"content_type": "application/pdf", "filename": nome}}  # noqa: E731
        self.caixa[40].update(sender="Banco Azul <fatura@bancoazul.com.br>", subject="Sua fatura de novembro", parts=pdf("fatura-nov.pdf"))
        self.caixa[38].update(parts=pdf("catalogo.pdf"))
        self.caixa[5].update(sender="Banco Azul <fatura@bancoazul.com.br>", subject="Fatura de março", parts=pdf("fatura-mar.pdf"))
        for alvo, valor in (("_email_simulado", lambda: False), ("contas_imap", lambda forcar=False: [{"id": "imap-ana", "nome": "ana@exemplo.com", "ok": True}])):
            p = mock.patch.object(S, alvo, valor)
            p.start()
            self.addCleanup(p.stop)
        S.PROCURA.update(rodando=False, fim=None)

    def ha(self, metodo, caminho, corpo=None, timeout=20):
        if caminho == "/services/imap/fetch?return_response":
            self.pedidos.append(("fetch", corpo["uid"]))
            n = int(corpo["uid"])
            if n not in self.caixa:
                raise S.ErroHA("O Home Assistant recusou o pedido: Fetch failed")
            return {"service_response": dict(self.caixa[n], uid=corpo["uid"], text="...")}
        return super().ha(metodo, caminho, corpo, timeout)

    def buscas(self):
        return [x for x in self.pedidos if x[0] == "fetch"]

    def test_acha_o_ultimo_email_em_poucos_passos(self):
        self.assertEqual(S._ultimo_email("imap-ana"), 40)
        self.assertLessEqual(len(self.buscas()), 14, "dobra e divide ao meio")
        self.pedidos.clear()
        self.assertEqual(S._ultimo_email("imap-ana", 38), 40, "do palpite (o último que chegou) para a frente")
        self.assertLessEqual(len(self.buscas()), 8)
        self.assertEqual(S._ultimo_email("imap-ana", 300), 40, "palpite depois do fim (e-mails apagados)")
        self.caixa.clear()
        self.assertEqual(S._ultimo_email("imap-ana"), 0, "pasta vazia")

    def test_procurar_le_as_faturas_dos_mais_novos(self):
        self.ajustar(email_aviso=True, email_para=["person.ana"])
        with mock.patch.object(S, "avisar_fatura") as aviso:
            S.PROCURA.update(rodando=True, vistos=0, total=30, pdfs=0, achados=0, erro="")
            S._procurar([{"id": "imap-ana", "nome": "ana@exemplo.com"}])
        self.assertEqual({k: S.PROCURA[k] for k in ("rodando", "vistos", "pdfs", "achados", "erro")},
                         {"rodando": False, "vistos": 30, "pdfs": 2, "achados": 1, "erro": ""})
        self.assertTrue(S.PROCURA["fim"])
        it = {x["assunto"]: x for x in self.itens()}
        self.assertEqual(sorted(it), ["Novidades 38", "Sua fatura de novembro"], "os 30 mais novos: o de março (5) fica de fora")
        self.assertEqual((it["Sua fatura de novembro"]["estado"], it["Sua fatura de novembro"]["uid"]), ("conferir", "40"))
        self.assertEqual(it["Novidades 38"]["estado"], "fora", "PDF de outro remetente fica em Recebidos, sem ler")
        self.assertEqual([x for x in self.pedidos if x[0] == "POST"], [("POST", "/services/imap/fetch_part?return_response", {"entry": "imap-ana", "uid": "40", "part": "1"})])
        aviso.assert_not_called()  # procurar não manda aviso no celular
        S.PROCURA.update(rodando=True, vistos=0, pdfs=0, achados=0)
        S._procurar([{"id": "imap-ana", "nome": "ana@exemplo.com"}])
        self.assertEqual((S.PROCURA["pdfs"], S.PROCURA["achados"], len(self.itens())), (2, 0, 2), "de novo: nada repetido")
        # 1.54.1: um e-mail apagado na pasta muda os números: a fatura vira a 39, e continua uma só
        del self.caixa[1]
        self.caixa = {n - 1: v for n, v in self.caixa.items()}
        S.PROCURA.update(rodando=True, vistos=0, pdfs=0, achados=0)
        S._procurar([{"id": "imap-ana", "nome": "ana@exemplo.com"}])
        self.assertEqual((S.PROCURA["achados"], len(self.itens())), (0, 2), "com outro número, é o mesmo e-mail")

    def test_validacoes_e_em_segundo_plano(self):
        self.ajustar(email=False)
        with self.assertRaisesRegex(ValueError, "Ligue Ler as faturas do e-mail"):
            S.email_procurar()
        self.ajustar(email=True)
        with mock.patch.object(S, "contas_imap", lambda forcar=False: [{"id": "x", "nome": "x", "ok": False}]):
            with self.assertRaisesRegex(ValueError, "Nenhuma conta de e-mail funcionando"):
                S.email_procurar()
        r = S.email_procurar()
        self.assertEqual((r["procura"]["rodando"], r["procura"]["total"]), (True, 30))
        self.assertTrue(esperar(lambda: not S.PROCURA["rodando"]))
        self.assertEqual(S.emails_estado()["procura"]["achados"], 1)

    def test_erro_aparece(self):
        S.PROCURA.update(rodando=True)
        with mock.patch.object(S, "_ultimo_email", side_effect=S.ErroHA("Sem resposta do Home Assistant (timeout).")):
            S._procurar([{"id": "imap-ana", "nome": "ana@exemplo.com"}])
        self.assertEqual((S.PROCURA["rodando"], S.PROCURA["erro"]), (False, "Sem resposta do Home Assistant (timeout)."))


class TestAvisoEContas(ComServidor):
    def test_aviso_no_celular_de_quem_foi_escolhido(self):
        self.ajustar(email_aviso=True, email_para=["person.ana"])
        enviados = []
        with mock.patch.object(S.AVISOS, "pessoas", return_value=[{"id": "person.ana", "celulares": ["mobile_app_pixel_ana"]}, {"id": "person.beto", "celulares": ["mobile_app_beto"]}]), \
                mock.patch.object(S.AVISOS, "enviar", side_effect=lambda *a, **k: enviados.append((a, k)) or 1):
            eid = S.email_chegou(evento())
        self.assertEqual(len(enviados), 1)
        (alvos, texto, tag), k = enviados[0]
        self.assertEqual((alvos, tag, k), (["mobile_app_pixel_ana"], "gerencia-email-" + eid, {"grupo": "gerencia-email", "canal": "Faturas do e-mail"}))
        self.assertEqual(texto["title"], "📧 Fatura do e-mail para conferir")
        self.assertRegex(texto["message"], r"^• Banco Azul: \d+ lançamentos · R\$ ")

    def test_sem_aviso_quando_desligado_ou_sem_ninguem(self):
        with mock.patch.object(S.AVISOS, "enviar") as env:
            S.email_chegou(evento("1"))
            self.ajustar(email_aviso=True, email_para=[])
            S.email_chegou(evento("2", assunto="b"))
        env.assert_not_called()

    def test_aviso_sem_as_pessoas_da_casa(self):
        self.ajustar(email_aviso=True, email_para=["person.ana"])
        with mock.patch.object(S.AVISOS, "pessoas", side_effect=S.ErroHA("x")):
            self.assertEqual(S.avisar_fatura({"id": "a", "de": "x", "resultado": {}}), 0)

    def test_resumo(self):
        self.assertEqual(S._resumo_fatura({"resultado": {"lancamentos": [{"tipo": "despesa", "valor": 100}, {"tipo": "receita", "valor": 30}]}}), "2 lançamentos · R$ 70,00")
        self.assertEqual(S._resumo_fatura({"resultado": {"lancamentos": [{"tipo": "despesa", "valor": 9.9}]}}), "1 lançamento · R$ 9,90")
        self.assertEqual(S._resumo_fatura({"resultado": {"investimentos": [{}]}}), "1 investimento")
        # (era bug na 1.47.0: o pagamento da própria fatura descontava do total no aviso)
        fatura = [{"tipo": "despesa", "valor": 100, "cartao": True}, {"tipo": "despesa", "valor": 50, "cartao": True},
                  {"tipo": "receita", "descricao": "Pagamento online", "valor": 1200, "cartao": False}]
        self.assertEqual(S._resumo_fatura({"resultado": {"lancamentos": fatura}}), "2 lançamentos · R$ 150,00")

    def test_contas_de_email_do_home_assistant(self):
        S._contas_imap.update(t=0, v=None)
        entradas = [{"entry_id": "e1", "domain": "imap", "title": "ana@exemplo.com", "state": "loaded"},
                    {"entry_id": "e2", "domain": "imap", "title": "beto@exemplo.com", "state": "setup_error"}]
        with mock.patch.object(S, "_email_simulado", return_value=False), mock.patch.object(S, "TOKEN", "t"), \
                mock.patch.object(S.voz, "_ws_comando", return_value=entradas) as ws:
            self.assertEqual(S.contas_imap(), [{"id": "e1", "nome": "ana@exemplo.com", "ok": True}, {"id": "e2", "nome": "beto@exemplo.com", "ok": False}])
            S.contas_imap()
            self.assertEqual(ws.call_count, 1, "guardado por 5 minutos")
            self.assertEqual(ws.call_args[0][2], {"type": "config_entries/get", "domain": "imap"})
            S.contas_imap(forcar=True)
            self.assertEqual(ws.call_count, 2)
        with mock.patch.object(S, "_email_simulado", return_value=False), mock.patch.object(S, "TOKEN", "t"), \
                mock.patch.object(S.voz, "_ws_comando", side_effect=voz.ErroVoz("x")):
            self.assertIsNone(S.contas_imap(forcar=True))
        with mock.patch.object(S, "_email_simulado", return_value=False), mock.patch.object(S, "TOKEN", None):
            self.assertIsNone(S.contas_imap(forcar=True), "fora do Home Assistant")
        self.assertEqual(S.contas_imap()[0]["nome"], "ana@exemplo.com", "simulada nos testes e na prévia")

    def test_estado_para_a_tela(self):
        S.email_chegou(evento())
        e = S.emails_estado()
        self.assertEqual((e["ligado"], e["conectada"], len(e["itens"]), e["contas"][0]["id"]), (True, True, 1, "imap-simulado"))
        self.ajustar(email=False)
        e = S.emails_estado()
        self.assertEqual((e["ligado"], e["conectada"], e["contas"]), (False, False, None))
        self.assertEqual(len(e["itens"]), 1, "os recebidos continuam")

    def test_estado_acorda_a_escuta(self):
        esc = mock.Mock(conectada=False)
        with mock.patch.object(S, "ESCUTA", esc):
            S.emails_estado()
        esc.acordar.assert_called_once()

    def test_ajustes_normalizados(self):
        d = S.normalizar({"ajustes": {"email": "sim", "email_aviso": 1, "email_de": ["Banco <fatura@bancoazul.com.br>", "@BancoVerde.com.br", 5, "", "bancoverde.com.br"],
                                      "email_para": ["person.ana", "nada", 3, "person.ana"]}})["ajustes"]
        self.assertEqual((d["email"], d["email_aviso"], d["email_de"], d["email_para"]),
                         (False, False, ["fatura@bancoazul.com.br", "bancoverde.com.br"], ["person.ana"]))
        d = S.normalizar({})["ajustes"]
        self.assertEqual((d["email"], d["email_aviso"], d["email_de"], d["email_para"]), (False, False, [], []), "vem desligado")

    def test_simular_so_com_a_ia_simulada(self):
        with mock.patch.object(S, "IA_MOCK", False):
            with self.assertRaisesRegex(ValueError, "Só nos testes."):
                S.email_simular({})
        with self.assertRaisesRegex(ValueError, "Arquivo inválido."):
            S.email_simular({"b64": "!!"})
        S.email_simular({"de": "Banco Azul <fatura@bancoazul.com.br>", "assunto": "Fatura", "arquivo": "f.pdf", "b64": base64.b64encode(arq("fatura-azul.pdf")).decode()})
        self.assertTrue(esperar(lambda: self.itens() and self.itens()[0]["estado"] == "conferir"))
        self.assertEqual(self.pedidos, [], "o PDF simulado não passa pelo Home Assistant")

    def test_escuta_liga_pelo_ajuste(self):
        self.assertTrue(S._email_ligado())
        self.ajustar(email=False)
        self.assertFalse(S._email_ligado())


# ---------------------------------------------------------------------------------------------------------------
class TestRotas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Servidor()

    @classmethod
    def tearDownClass(cls):
        cls.s.parar()

    def ligar(self):
        st, _, d = self.s.get("/api/state")
        d["ajustes"].update(email=True, email_de=["bancoazul.com.br"])
        self.s.put("/api/state", d)

    def chegar(self, nome="fatura-azul.pdf", assunto="Sua fatura"):
        st, _, r = self.s.post("/api/emails/simular", {"de": "Banco Azul <fatura@bancoazul.com.br>", "assunto": assunto, "arquivo": nome,
                                                      "b64": base64.b64encode(arq(nome)).decode()})
        self.assertEqual((st, r), (200, {"ok": True}))

    def itens(self):
        return self.s.get("/api/emails")[2]["itens"]

    def test_fluxo_pela_api(self):
        self.ligar()
        st, _, rev0 = self.s.get("/api/rev")
        self.assertIn("emails", rev0)
        self.chegar(assunto="Fatura A")
        self.assertTrue(esperar(lambda: any(x["assunto"] == "Fatura A" and x["estado"] == "conferir" for x in self.itens()), 15))
        self.assertNotEqual(self.s.get("/api/rev")[2]["emails"], rev0["emails"], "o /api/rev avisa a tela")
        it = next(x for x in self.itens() if x["assunto"] == "Fatura A")
        st, _, r = self.s.post("/api/emails/feito", {"id": it["id"]})
        self.assertEqual(next(x for x in r["itens"] if x["id"] == it["id"])["estado"], "feito")
        st, _, r = self.s.post("/api/emails/feito", {"id": "000000000000"})
        self.assertEqual((st, r["erro"]), (400, "Esse e-mail não está mais aqui."))

    def test_procurar_na_caixa_de_entrada(self):
        self.ligar()
        for assunto, nome in (("Fatura na caixa 1", "fatura-azul.pdf"), ("Fatura na caixa 2", "fatura-azul.pdf")):
            st, _, r = self.s.post("/api/emails/simular", {"de": "Banco Azul <fatura@bancoazul.com.br>", "assunto": assunto, "arquivo": nome,
                                                          "b64": base64.b64encode(arq(nome)).decode(), "caixa": True})
            self.assertEqual(st, 200)
        self.assertFalse(any(x["assunto"].startswith("Fatura na caixa") for x in self.itens()), "na caixa, ainda não chegou para o app")
        st, _, r = self.s.post("/api/emails/procurar", {})
        self.assertEqual(st, 200, r)
        self.assertTrue(esperar(lambda: not self.s.get("/api/emails")[2]["procura"]["rodando"], 20))
        p = self.s.get("/api/emails")[2]["procura"]
        self.assertEqual((p["achados"], p["erro"]), (2, ""))
        self.assertTrue(esperar(lambda: {x["assunto"] for x in self.itens() if x["estado"] == "conferir"} >= {"Fatura na caixa 1", "Fatura na caixa 2"}, 15))

    def test_senha_pdf_e_ignorar(self):
        self.ligar()
        self.chegar("fatura-aes128-objstm.pdf", assunto="Fatura B")
        self.assertTrue(esperar(lambda: any(x["assunto"] == "Fatura B" and x["estado"] == "senha" for x in self.itens()), 15))
        it = next(x for x in self.itens() if x["assunto"] == "Fatura B")
        st, _, r = self.s.get("/api/emails/pdf?id=" + it["id"])
        self.assertEqual((st, r["nome"]), (200, "fatura-aes128-objstm.pdf"))
        self.assertEqual(base64.b64decode(r["b64"].split(",", 1)[1]), arq("fatura-aes128-objstm.pdf"), "o PDF como chegou (com a senha)")
        st, _, r = self.s.get("/api/emails/pdf?id=../../x")
        self.assertEqual(st, 400)
        st, _, r = self.s.post("/api/emails/ignorar", {"id": it["id"]})
        self.assertEqual(next(x for x in r["itens"] if x["id"] == it["id"])["estado"], "ignorado")
        st, _, r = self.s.post("/api/emails/ler", {"id": it["id"]})
        self.assertEqual(next(x for x in r["itens"] if x["id"] == it["id"])["estado"], "lendo", "ler de novo (em segundo plano)")

    def test_fora_das_exportacoes(self):
        self.ligar()
        self.chegar(assunto="Fatura C")
        self.assertTrue(esperar(lambda: any(x["assunto"] == "Fatura C" and x["estado"] == "conferir" for x in self.itens()), 15))
        st, _, corpo = self.s.get("/api/export/zip", cru=True)
        with zipfile.ZipFile(io.BytesIO(corpo)) as z:
            self.assertFalse(any("Fatura C" in z.read(n).decode("utf-8", "replace") for n in z.namelist()))


if __name__ == "__main__":
    unittest.main()


class TestLimiteDaResposta(ComServidor):
    """A resposta da IA passou do limite (no Claude: "reached the output token limit"): tenta de novo pedindo curta; não
    deu, explica onde aumentar o limite."""
    def ler(self, respostas):
        pedidos = []

        def ia(tipo, payload, imagens=0, timeout=180):
            pedidos.append(payload["instructions"])
            r = respostas.pop(0)
            if isinstance(r, Exception):
                raise r
            return {"service_response": {"data": r}}
        with mock.patch.object(S, "IA_MOCK", False), mock.patch.object(S, "ia_chamar", ia):
            return S.ia_ler({"modo": "caixa", "texto": "Mercado Bom 45,90 em 01/11/2026"}), pedidos

    def test_de_novo_mais_curta(self):
        lim = S.ErroHA("O Home Assistant recusou o pedido: Claude reached the output token limit before completing the response")
        ok = '{"lancamentos":[{"tipo":"despesa","descricao":"Mercado Bom","valor":45.9,"data":"2026-11-01","categoria":"Mercado"}]}'
        r, pedidos = self.ler([lim, ok])
        self.assertEqual(len(pedidos), 2)
        self.assertNotIn(S.PEDIDO_CURTO, pedidos[0])
        self.assertTrue(pedidos[1].endswith(S.PEDIDO_CURTO))
        self.assertIn("itens", r, "a segunda resposta vale")
        with self.assertRaises(ValueError) as c:
            self.ler([lim, lim])
        self.assertEqual(str(c.exception), S.MSG_LIMITE)
        self.assertIn("aumente o máximo de tokens da resposta", S.MSG_LIMITE)
        with self.assertRaisesRegex(ValueError, "^Outro erro$"):
            self.ler([S.ErroHA("Outro erro")])


class TestPagamentoDaFatura(unittest.TestCase):
    def test_a_ia_marca_e_o_servidor_guarda_so_no_recebimento(self):
        d = S.ler()
        r = S.ia_limpar_caixa({"itens": [{"tipo": "receita", "descricao": "Pagamento online", "valor": 1200, "pagamento_fatura": True},
                                         {"tipo": "despesa", "descricao": "Mercado", "valor": 10, "pagamento_fatura": True},
                                         {"tipo": "receita", "descricao": "Pix", "valor": 5, "pagamento_fatura": "sim"}]}, d)
        self.assertEqual([x.get("pagamento_fatura") for x in r], [True, None, None])
        self.assertIn('"pagamento online"', S.ia_prompt(d, "caixa", False, "x"))
        self.assertIn('"pagamento_fatura": true', S.ia_prompt(d, "auto", False, "x"))

