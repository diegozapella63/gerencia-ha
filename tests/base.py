"""Ajuda dos testes: o caminho do app e dados de exemplo (nada real)."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "gerencia", "app")
if APP not in sys.path:
    sys.path.insert(0, APP)

INDICES = {"cdi": 13.65, "selic": 13.75, "ipca": 4.5, "tr": 0.1}


def pasta_temp():
    """Uma pasta temporária, apagada no fim do processo."""
    return tempfile.mkdtemp(prefix="gerencia-teste-")


import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class ServidorFalso:
    """Um servidor HTTP numa porta livre; rotas = {caminho: (status, corpo)} ou {caminho: função(handler) -> (status, corpo)}.
    Guarda os pedidos em .pedidos (método, caminho, cabeçalhos, corpo)."""

    def __init__(self, rotas):
        self.rotas = rotas
        self.pedidos = []
        dono = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _responder(self):
                n = int(self.headers.get("Content-Length") or 0)
                corpo = self.rfile.read(n) if n else b""
                dono.pedidos.append((self.command, self.path, dict(self.headers), corpo))
                r = dono.rotas.get(self.path.split("?")[0])
                if callable(r):
                    r = r(self, corpo)
                status, resp = r if r else (404, {"erro": "não achei"})
                dados = resp if isinstance(resp, (bytes, str)) else json.dumps(resp)
                dados = dados.encode() if isinstance(dados, str) else dados
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            do_GET = do_POST = do_PUT = do_DELETE = _responder

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()


def porta_fechada():
    """Uma porta onde nada escuta."""
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


import base64
import hashlib
import socket
import socketserver
import struct


class WSFalso:
    """A API WebSocket do Home Assistant, só o bastante para o voz.py: aperto de mão, auth e um comando.
    responder(comando) devolve a lista do que mandar: dicts (texto JSON), ("ping", b""), ("fechar",),
    ("partes", dict) (a mensagem em dois pedaços), ("cortar",) (cai sem aviso) ou ("bytes", b"...") (cru). Guarda o que chegou em .recebido."""

    def __init__(self, responder, token="token-teste", http101=True):
        self.responder, self.token, self.http101 = responder, token, http101
        self.recebido = []
        dono = self

        class H(socketserver.BaseRequestHandler):
            def handle(self):
                dono._atender(self.request)

        self.srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H)
        self.srv.daemon_threads = True
        self.url = f"ws://127.0.0.1:{self.srv.server_address[1]}/api/websocket"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()

    @staticmethod
    def quadro(dados, op=1, fim=True):
        n = len(dados)
        cab = bytes([(0x80 if fim else 0) | op])
        if n < 126:
            cab += bytes([n])
        elif n < 65536:
            cab += bytes([126]) + struct.pack(">H", n)
        else:
            cab += bytes([127]) + struct.pack(">Q", n)
        return cab + dados

    def _ler_quadro(self, s, buf):
        def receber(n):
            while len(buf) < n:
                p = s.recv(65536)
                if not p:
                    raise ConnectionError("fechou")
                buf.extend(p)
            out = bytes(buf[:n])
            del buf[:n]
            return out
        b1, b2 = receber(2)
        n = b2 & 0x7F
        if n == 126:
            n = struct.unpack(">H", receber(2))[0]
        elif n == 127:
            n = struct.unpack(">Q", receber(8))[0]
        mascara = receber(4) if b2 & 0x80 else b"\0\0\0\0"
        dados = bytes(c ^ mascara[i % 4] for i, c in enumerate(receber(n)))
        self.recebido.append((b1 & 0x0F, bool(b2 & 0x80), dados))
        return b1 & 0x0F, dados

    def _atender(self, s):
        try:
            pedido = b""
            while b"\r\n\r\n" not in pedido:
                pedido += s.recv(4096)
            chave = next((l.split(b":", 1)[1].strip() for l in pedido.split(b"\r\n") if l.lower().startswith(b"sec-websocket-key")), b"")
            if not self.http101:
                s.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
                return
            aceite = base64.b64encode(hashlib.sha1(chave + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest())
            s.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: " + aceite + b"\r\n\r\n"
                      + self.quadro(json.dumps({"type": "auth_required"}).encode()))
            buf = bytearray()
            _, auth = self._ler_quadro(s, buf)
            ok = json.loads(auth).get("access_token") == self.token
            s.sendall(self.quadro(json.dumps({"type": "auth_ok" if ok else "auth_invalid"}).encode()))
            if not ok:
                self._ler_quadro(s, buf)
                return
            _, cmd = self._ler_quadro(s, buf)
            for x in self.responder(json.loads(cmd)):
                if isinstance(x, dict):
                    s.sendall(self.quadro(json.dumps(x).encode()))
                elif x[0] == "ping":
                    s.sendall(self.quadro(x[1], op=9))
                    self._ler_quadro(s, buf)  # o pong
                elif x[0] == "fechar":
                    s.sendall(self.quadro(b"", op=8))
                elif x[0] == "cortar":  # cai a conexão, sem aviso
                    return
                elif x[0] == "partes":
                    t = json.dumps(x[1]).encode()
                    s.sendall(self.quadro(t[:5], op=1, fim=False) + self.quadro(t[5:], op=0))
                elif x[0] == "bytes":
                    s.sendall(x[1])
            self._ler_quadro(s, buf)  # o fechamento do app
        except (ConnectionError, OSError, ValueError):
            pass
        finally:
            s.close()


def ler_pdf(dados):
    """Os textos de um PDF feito pelo pdf.py, página por página (descompacta cada página e junta os "(...) Tj")."""
    import re
    import zlib
    paginas = []
    for m in re.finditer(rb"/Length (\d+) /Filter /FlateDecode >>\nstream\n", dados):
        ops = zlib.decompress(dados[m.end():m.end() + int(m.group(1))])
        textos = []
        for t in re.findall(rb"\(((?:\\.|[^\\)])*)\) Tj", ops):
            textos.append(re.sub(rb"\\(.)", rb"\1", t).decode("cp1252"))
        paginas.append(textos)
    return paginas


def importar_servidor():
    """Importa o server.py com as pastas num lugar temporário, a IA e a fala simuladas (nada do Home Assistant)."""
    raiz = pasta_temp()
    for k, sub in (("GERENCIA_DATA", "data"), ("GERENCIA_SHARE", "share"), ("GERENCIA_MEDIA", "media")):
        os.environ[k] = os.path.join(raiz, sub)
        os.makedirs(os.environ[k], exist_ok=True)
    os.environ["GERENCIA_INVENTARIO"] = os.path.join(raiz, "inventario-nao-existe.json")
    os.environ["GERENCIA_IA_MOCK"] = "1"
    os.environ["GERENCIA_DEV"] = "1"
    for k in ("SUPERVISOR_TOKEN", "HASSIO_TOKEN"):
        os.environ.pop(k, None)
    import server
    return server


import subprocess
import time as _time
import urllib.error
import urllib.request


class Servidor:
    """O server.py de verdade num processo, numa porta livre, com pastas temporárias e a IA e a fala simuladas."""

    def __init__(self, env=None):
        self.raiz = pasta_temp()
        self.dirs = {k: os.path.join(self.raiz, k) for k in ("data", "share", "media")}
        for p in self.dirs.values():
            os.makedirs(p, exist_ok=True)
        self.porta = porta_fechada()
        e = dict(os.environ)
        for k in ("SUPERVISOR_TOKEN", "HASSIO_TOKEN", "GERENCIA_FONTES_MOCK"):
            e.pop(k, None)
        e.update({"GERENCIA_DEV": "1", "GERENCIA_IA_MOCK": "1", "GERENCIA_PORTA": str(self.porta), "GERENCIA_DATA": self.dirs["data"],
                  "GERENCIA_SHARE": self.dirs["share"], "GERENCIA_MEDIA": self.dirs["media"], "GERENCIA_DOLAR": "5.0",
                  "GERENCIA_INVENTARIO": os.path.join(self.raiz, "inventario.json"), "GERENCIA_URL_INTERNA": f"http://127.0.0.1:{self.porta}",
                  # o Banco Central fica num endereço que não responde: os índices são os de partida
                  "GERENCIA_BCB": "http://127.0.0.1:9/serie/{s}"})
        e.update(env or {})
        self.log = open(os.path.join(self.raiz, "server.log"), "w")
        cmd = [sys.executable, "-u", os.path.join(APP, "server.py")]
        if os.environ.get("GERENCIA_COBERTURA"):  # tools/cobertura.py: conta as linhas deste processo também
            cmd[2:2] = [os.path.join(RAIZ, "tools", "cobertura.py"), "--filho", os.environ["GERENCIA_COBERTURA"]]
        self.proc = subprocess.Popen(cmd, env=e, stdout=self.log, stderr=subprocess.STDOUT, cwd=APP)
        self.url = f"http://127.0.0.1:{self.porta}"
        for _ in range(100):
            try:
                urllib.request.urlopen(self.url + "/api/rev", timeout=1)
                return
            except (urllib.error.URLError, ConnectionError, OSError):
                _time.sleep(0.05)
        raise RuntimeError("o servidor não subiu: " + open(self.log.name).read())

    def pedir(self, metodo, caminho, corpo=None, cabecalhos=None, cru=False):
        """(status, cabeçalhos, corpo): corpo em JSON quando a resposta é JSON, senão bytes."""
        dados = corpo if isinstance(corpo, (bytes, type(None))) else json.dumps(corpo).encode()
        req = urllib.request.Request(self.url + caminho, data=dados, method=metodo, headers=dict({"Content-Type": "application/json"}, **(cabecalhos or {})))
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                status, cab, b = r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            status, cab, b = e.code, dict(e.headers), e.read()
        if not cru and "json" in cab.get("Content-Type", ""):
            b = json.loads(b or b"null")
        return status, cab, b

    def get(self, caminho, **kw):
        return self.pedir("GET", caminho, **kw)

    def post(self, caminho, corpo=None, **kw):
        return self.pedir("POST", caminho, corpo if corpo is not None else {}, **kw)

    def put(self, caminho, corpo, **kw):
        return self.pedir("PUT", caminho, corpo, **kw)

    def parar(self):
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.log.close()
