"""Faturas por e-mail: a integração IMAP do Home Assistant (o Gmail, com uma senha de app) avisa cada e-mail novo com o
evento imap_content. O app fica escutando esse evento pela API WebSocket; quando o e-mail é de uma fatura, pega o PDF
anexado (ação imap.fetch_part), abre com as senhas cadastradas e lê com a IA (server.py). Nada é lançado sozinho:
a fatura lida espera a conferência na tela.

Só biblioteca padrão: a conexão é a do voz.py (ConexaoWS), que fica aberta e reconecta sozinha.
"""
import base64
import binascii
import email.utils
import quopri
import re
import threading
import time
import unicodedata
from datetime import datetime

import voz

EVENTO = "imap_content"


def _sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t or "")) if unicodedata.category(c) != "Mn").lower()


def anexo_pdf(partes):
    """(chave da parte, nome do arquivo) do primeiro PDF anexado, ou (None, None). partes vem do evento ou do
    imap.fetch: {"1": {"content_type": "application/pdf", "filename": "fatura.pdf"}, ...}."""
    if not isinstance(partes, dict):
        return None, None
    for chave, p in partes.items():
        if not isinstance(p, dict):
            continue
        tipo = str(p.get("content_type") or "").lower()
        nome = str(p.get("filename") or "")
        if tipo == "application/pdf" or nome.lower().endswith(".pdf"):
            return str(chave), nome or "fatura.pdf"
    return None, None


def decodificar(dados, codificacao):
    """Os bytes de uma parte do e-mail (o imap.fetch_part devolve como veio no e-mail: base64, de costume)."""
    cte = str(codificacao or "").strip().lower()
    dados = str(dados or "")
    if cte == "base64":
        try:
            return base64.b64decode(re.sub(r"\s+", "", dados), validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("O anexo do e-mail veio estragado.") from None
    if cte == "quoted-printable":
        return quopri.decodestring(dados.encode("latin-1", "replace"))
    return dados.encode("latin-1", "replace")  # 7bit, 8bit, binary


def endereco(remetente):
    """Só o endereço: "Banco Azul <fatura@bancoazul.com.br>" → "fatura@bancoazul.com.br"."""
    m = re.search(r"<([^<>@\s]+@[^<>\s]+)>", str(remetente or ""))
    if m:
        return m.group(1).lower()
    m = re.search(r"[^\s<>\"']+@[^\s<>\"']+", str(remetente or ""))
    return m.group(0).lower() if m else str(remetente or "").strip().lower()


def nome_remetente(remetente):
    """O nome de quem mandou ("Banco Azul <...>" → "Banco Azul"); sem nome, o endereço."""
    t = str(remetente or "").strip()
    m = re.match(r'^\s*"?([^"<]+?)"?\s*<', t)
    return m.group(1).strip() if m else endereco(t)


def limpar_remetente(texto):
    """Um remetente para cadastrar: o endereço, ou a parte depois do @ (ex.: bancoazul.com.br), sem espaços."""
    t = endereco(texto) if "<" in str(texto or "") else str(texto or "").strip().lower()
    t = re.sub(r"\s+", "", t).lstrip("@")
    return t[:80]


# o que no assunto (ou no nome do PDF) diz que é conta: fatura, boleto, recibo, cobrança, nota fiscal e assinatura
PALAVRAS = ("fatura", "boleto", "recibo", "receipt", "invoice", "cobranca", "nota fiscal", "assinatura", "subscription",
            "renovacao", "renewal", "mensalidade")


def casa(de, r):
    """O endereço é o remetente r: o endereço inteiro ou o fim dele (bancoazul.com.br, ou um subdomínio)."""
    return bool(r) and (de == r or de.endswith("@" + r) or de.endswith("." + r))


def regra(remetente, regras):
    """A regra do remetente (Sempre é um fixo ou Nunca considerar), ou None; a mais precisa vale (o endereço inteiro
    sobre o domínio)."""
    de = endereco(remetente)
    achadas = [r for r in regras or [] if isinstance(r, dict) and casa(de, r.get("de"))]
    return max(achadas, key=lambda r: len(r["de"]), default=None)


def e_fatura(remetente, assunto, arquivo, remetentes, regras=None):
    """É e-mail de conta? A regra do remetente vale primeiro (Sempre é um fixo: sim; Nunca considerar: não). Com
    remetentes cadastrados, o endereço de quem mandou tem um deles (o endereço inteiro ou o fim, como bancoazul.com.br);
    sem nenhum, uma das PALAVRAS no assunto ou no nome do PDF."""
    rg = regra(remetente, regras)
    if rg:
        return rg.get("acao") == "fixo"
    de = endereco(remetente)
    lista = [limpar_remetente(r) for r in remetentes or [] if str(r or "").strip()]
    if lista:
        return any(casa(de, r) for r in lista)
    t = _sem_acento(f"{assunto} {arquivo}")
    return any(p in t for p in PALAVRAS)


def chave(ev):
    """O que identifica um e-mail (o Home Assistant manda o último de novo quando reinicia)."""
    return f"{ev.get('entry_id') or ''}|{ev.get('uid') or ''}|{str(ev.get('subject') or '')[:60]}"


def _data_chave(d):
    """A data do e-mail num jeito só (a hora como está escrita, até o segundo, sem o fuso: a data guardada é cortada e
    pode ter ficado sem ele), venha ela em ISO ou no formato do cabeçalho."""
    s = str(d or "").strip()
    if not s:
        return ""
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = email.utils.parsedate_to_datetime(s)
        except (TypeError, ValueError, IndexError):
            return s[:40]
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def chave_conteudo(entry, remetente, data, assunto, arquivo=""):
    """O mesmo e-mail mesmo com outro número: o aviso do Home Assistant e o Procurar faturas agora não numeram igual, e o
    número muda quando a pasta muda (um e-mail apagado ou movido). Pela conta, o remetente, a data e o assunto (sem a
    data, o nome do anexo). Vazio quando não há como saber (sem a conta)."""
    if not entry:
        return ""
    return "|".join(("c", str(entry), endereco(remetente), _data_chave(data) or "a:" + str(arquivo or "")[:80], _sem_acento(assunto)[:60]))


class Escuta:
    """Fica escutando o evento imap_content no WebSocket do Home Assistant enquanto ligada() disser que sim. Cada
    evento vai para ao_receber(dados do evento), numa linha de execução própria. Caiu, reconecta sozinha
    (5 s, 10 s, 20 s... até 5 min). conectada diz se está escutando agora."""

    def __init__(self, url, token, ao_receber, ligada, log, espera=60, abrir=None, atraso=5):
        self.url, self.token, self.ao_receber, self.ligada, self.log, self.espera = url, token, ao_receber, ligada, log, espera
        self.atraso = atraso
        self.abrir = abrir or (lambda: voz.ConexaoWS(self.url, self.token, timeout=15))
        self.conectada = False
        self.erro = ""
        self._parar = threading.Event()
        self._acorda = threading.Event()
        self._thread = None

    def iniciar(self):
        if self._thread and self._thread.is_alive():
            return
        self._parar.clear()
        self._thread = threading.Thread(target=self._laco, daemon=True)
        self._thread.start()

    def parar(self):
        self._parar.set()
        self._acorda.set()

    def acordar(self):
        """Acabou de ligar (ou a tela quer saber agora): conecta sem esperar a próxima volta."""
        self._acorda.set()

    def _esperar(self, s):
        self._acorda.wait(s)
        self._acorda.clear()

    def _laco(self):
        atraso = self.atraso
        while not self._parar.is_set():
            if not self._ligada():
                self.conectada = False
                self._esperar(self.espera)
                continue
            try:
                self._escutar()
                atraso = self.atraso
            except Exception as e:  # noqa: BLE001  (caiu: tenta de novo daqui a pouco)
                if str(e) != self.erro:
                    self.log("E-mail: sem a conexão com o Home Assistant:", e)
                self.erro = str(e)
                self.conectada = False
                self._esperar(atraso)
                atraso = min(atraso * 2, self.atraso * 60)

    def _ligada(self):
        try:
            return bool(self.ligada())
        except Exception:  # noqa: BLE001
            return False

    def _escutar(self):
        c = self.abrir()
        try:
            c.enviar({"id": 1, "type": "subscribe_events", "event_type": EVENTO})
            m = c.ler(self.espera)
            if not m or m.get("id") != 1 or m.get("type") != "result":
                raise voz.ErroVoz("O Home Assistant não respondeu.")
            if not m.get("success"):
                raise voz.ErroVoz((m.get("error") or {}).get("message") or "O Home Assistant recusou o pedido.")
            self.conectada, self.erro = True, ""
            n, visto, ping = 2, time.monotonic(), None
            passo = max(0.05, min(self.espera, 15))
            while not self._parar.is_set():
                m = c.ler(passo)
                agora = time.monotonic()
                if m is None:
                    if not self._ligada():
                        return
                    # um ping de tempos em tempos: uma conexão que caiu calada aparece aqui
                    if ping is not None and agora - ping > passo * 2:
                        raise voz.ErroVoz("O Home Assistant parou de responder.")
                    if ping is None and agora - visto > self.espera:
                        c.enviar({"id": n, "type": "ping"})
                        n, ping = n + 1, agora
                    continue
                visto, ping = agora, None
                if m.get("type") == "event" and m.get("id") == 1:
                    dados = ((m.get("event") or {}).get("data")) or {}
                    if isinstance(dados, dict):
                        threading.Thread(target=self._receber, args=(dados,), daemon=True).start()
        finally:
            self.conectada = False
            c.fechar()

    def _receber(self, dados):
        try:
            self.ao_receber(dados)
        except Exception as e:  # noqa: BLE001
            self.log("E-mail:", e)
