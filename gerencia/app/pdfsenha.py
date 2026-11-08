"""Abrir PDF com senha (as faturas dos bancos) só com a biblioteca padrão do Python, para a leitura por IA.

O PDF com senha tem o conteúdo cifrado (o "Standard Security Handler" do formato PDF): RC4 de 40 ou 128 bits, AES de
128 bits ou AES de 256 bits (o mais comum nas faturas de hoje). Com a senha certa (a de abrir, ou a do dono do
arquivo), este módulo decifra cada texto e cada fluxo e grava um PDF novo, sem senha, que a IA consegue ler.
Os objetos guardados dentro de "object streams" viram objetos comuns e a tabela de posições (xref) é refeita.

Como o Python não traz AES, a cifra está aqui, feita à mão (a mesma do padrão FIPS-197, conferida com os vetores dele
nos testes). É lenta para arquivos grandes, mas uma fatura de algumas centenas de KB abre em poucos segundos.
"""
import hashlib
import re
import struct
import zlib


class SenhaErrada(Exception):
    """Nenhuma das senhas abre o PDF."""


class PdfInvalido(Exception):
    """Não é um PDF que este módulo entende (estrutura quebrada ou cifra que não é a do padrão)."""


# ---------------------------------------------------------------------------------------------- AES (FIPS-197)

def _tabelas():
    exp, log = [0] * 512, [0] * 256
    x = 1
    for i in range(255):  # 3 gera o grupo multiplicativo de GF(2^8)
        exp[i] = x
        log[x] = i
        x ^= (x << 1) ^ (0x11B if x & 0x80 else 0)
        x &= 0xFF
    for i in range(255, 512):
        exp[i] = exp[i - 255]

    def mul(a, b):
        return exp[log[a] + log[b]] if a and b else 0

    sbox, inv = [0] * 256, [0] * 256
    for a in range(256):
        b = exp[255 - log[a]] if a else 0  # o inverso multiplicativo
        s = b
        for _ in range(4):
            b = ((b << 1) | (b >> 7)) & 0xFF
            s ^= b
        s ^= 0x63
        sbox[a], inv[s] = s, a
    te = [[0] * 256 for _ in range(4)]
    td = [[0] * 256 for _ in range(4)]
    for a in range(256):
        s, i = sbox[a], inv[a]
        w = (mul(s, 2) << 24) | (s << 16) | (s << 8) | mul(s, 3)
        v = (mul(i, 14) << 24) | (mul(i, 9) << 16) | (mul(i, 13) << 8) | mul(i, 11)
        for k in range(4):
            te[k][a] = ((w >> (8 * k)) | (w << (32 - 8 * k))) & 0xFFFFFFFF
            td[k][a] = ((v >> (8 * k)) | (v << (32 - 8 * k))) & 0xFFFFFFFF
    return sbox, inv, te, td


_SBOX, _INV, _TE, _TD = _tabelas()


class AES:
    """AES de 128 ou 256 bits, bloco a bloco (com tabelas de 32 bits)."""

    def __init__(self, chave):
        nk = len(chave) // 4
        if len(chave) not in (16, 24, 32):
            raise ValueError("chave AES de 16, 24 ou 32 bytes")
        self.nr = nk + 6
        w = list(struct.unpack(f">{nk}I", chave))
        rcon = 1
        for i in range(nk, 4 * (self.nr + 1)):
            t = w[i - 1]
            if i % nk == 0:
                t = ((t << 8) | (t >> 24)) & 0xFFFFFFFF
                t = (_SBOX[t >> 24] << 24) | (_SBOX[(t >> 16) & 255] << 16) | (_SBOX[(t >> 8) & 255] << 8) | _SBOX[t & 255]
                t ^= rcon << 24
                rcon = ((rcon << 1) ^ (0x11B if rcon & 0x80 else 0)) & 0xFF
            elif nk > 6 and i % nk == 4:
                t = (_SBOX[t >> 24] << 24) | (_SBOX[(t >> 16) & 255] << 16) | (_SBOX[(t >> 8) & 255] << 8) | _SBOX[t & 255]
            w.append(w[i - nk] ^ t)
        self.ek = w
        # a chave da volta (decifrar) é a mesma, de trás para frente, com InvMixColumns nas voltas do meio
        dk = []
        for r in range(self.nr, -1, -1):
            bloco = w[4 * r:4 * r + 4]
            if 0 < r < self.nr:
                bloco = [_TD[0][_SBOX[x >> 24]] ^ _TD[1][_SBOX[(x >> 16) & 255]] ^ _TD[2][_SBOX[(x >> 8) & 255]] ^ _TD[3][_SBOX[x & 255]]
                         for x in bloco]
            dk.extend(bloco)
        self.dk = dk

    def cifrar_bloco(self, b):
        k, (t0, t1, t2, t3) = self.ek, _TE
        s0, s1, s2, s3 = struct.unpack(">4I", b)
        s0 ^= k[0]
        s1 ^= k[1]
        s2 ^= k[2]
        s3 ^= k[3]
        for r in range(1, self.nr):
            j = 4 * r
            s0, s1, s2, s3 = (t0[s0 >> 24] ^ t1[(s1 >> 16) & 255] ^ t2[(s2 >> 8) & 255] ^ t3[s3 & 255] ^ k[j],
                              t0[s1 >> 24] ^ t1[(s2 >> 16) & 255] ^ t2[(s3 >> 8) & 255] ^ t3[s0 & 255] ^ k[j + 1],
                              t0[s2 >> 24] ^ t1[(s3 >> 16) & 255] ^ t2[(s0 >> 8) & 255] ^ t3[s1 & 255] ^ k[j + 2],
                              t0[s3 >> 24] ^ t1[(s0 >> 16) & 255] ^ t2[(s1 >> 8) & 255] ^ t3[s2 & 255] ^ k[j + 3])
        S, j = _SBOX, 4 * self.nr
        return struct.pack(">4I",
                           ((S[s0 >> 24] << 24) | (S[(s1 >> 16) & 255] << 16) | (S[(s2 >> 8) & 255] << 8) | S[s3 & 255]) ^ k[j],
                           ((S[s1 >> 24] << 24) | (S[(s2 >> 16) & 255] << 16) | (S[(s3 >> 8) & 255] << 8) | S[s0 & 255]) ^ k[j + 1],
                           ((S[s2 >> 24] << 24) | (S[(s3 >> 16) & 255] << 16) | (S[(s0 >> 8) & 255] << 8) | S[s1 & 255]) ^ k[j + 2],
                           ((S[s3 >> 24] << 24) | (S[(s0 >> 16) & 255] << 16) | (S[(s1 >> 8) & 255] << 8) | S[s2 & 255]) ^ k[j + 3])

    def decifrar_bloco(self, b):
        k, (t0, t1, t2, t3) = self.dk, _TD
        s0, s1, s2, s3 = struct.unpack(">4I", b)
        s0 ^= k[0]
        s1 ^= k[1]
        s2 ^= k[2]
        s3 ^= k[3]
        for r in range(1, self.nr):
            j = 4 * r
            s0, s1, s2, s3 = (t0[s0 >> 24] ^ t1[(s3 >> 16) & 255] ^ t2[(s2 >> 8) & 255] ^ t3[s1 & 255] ^ k[j],
                              t0[s1 >> 24] ^ t1[(s0 >> 16) & 255] ^ t2[(s3 >> 8) & 255] ^ t3[s2 & 255] ^ k[j + 1],
                              t0[s2 >> 24] ^ t1[(s1 >> 16) & 255] ^ t2[(s0 >> 8) & 255] ^ t3[s3 & 255] ^ k[j + 2],
                              t0[s3 >> 24] ^ t1[(s2 >> 16) & 255] ^ t2[(s1 >> 8) & 255] ^ t3[s0 & 255] ^ k[j + 3])
        S, j = _INV, 4 * self.nr
        return struct.pack(">4I",
                           ((S[s0 >> 24] << 24) | (S[(s3 >> 16) & 255] << 16) | (S[(s2 >> 8) & 255] << 8) | S[s1 & 255]) ^ k[j],
                           ((S[s1 >> 24] << 24) | (S[(s0 >> 16) & 255] << 16) | (S[(s3 >> 8) & 255] << 8) | S[s2 & 255]) ^ k[j + 1],
                           ((S[s2 >> 24] << 24) | (S[(s1 >> 16) & 255] << 16) | (S[(s0 >> 8) & 255] << 8) | S[s3 & 255]) ^ k[j + 2],
                           ((S[s3 >> 24] << 24) | (S[(s2 >> 16) & 255] << 16) | (S[(s1 >> 8) & 255] << 8) | S[s0 & 255]) ^ k[j + 3])

    def cifrar_cbc(self, dados, iv):
        """Sem preenchimento (o tamanho já vem múltiplo de 16)."""
        out, ant = bytearray(), iv
        for i in range(0, len(dados), 16):
            ant = self.cifrar_bloco(bytes(a ^ b for a, b in zip(dados[i:i + 16], ant)))
            out += ant
        return bytes(out)

    def decifrar_cbc(self, dados, iv):
        out, ant = bytearray(), iv
        for i in range(0, len(dados) - len(dados) % 16, 16):
            bloco = dados[i:i + 16]
            out += bytes(a ^ b for a, b in zip(self.decifrar_bloco(bloco), ant))
            ant = bloco
        return bytes(out)


def rc4(chave, dados):
    s = list(range(256))
    j = 0
    n = len(chave)
    for i in range(256):
        j = (j + s[i] + chave[i % n]) & 255
        s[i], s[j] = s[j], s[i]
    out = bytearray(len(dados))
    i = j = 0
    for k, c in enumerate(dados):
        i = (i + 1) & 255
        j = (j + s[i]) & 255
        s[i], s[j] = s[j], s[i]
        out[k] = c ^ s[(s[i] + s[j]) & 255]
    return bytes(out)


def _aes_texto(chave, dados):
    """AES no PDF: os 16 primeiros bytes são o vetor inicial; no fim, o preenchimento PKCS#5."""
    if len(dados) < 32:
        return b""
    out = AES(chave).decifrar_cbc(dados[16:], dados[:16])
    n = out[-1] if out else 0
    return out[:-n] if 1 <= n <= 16 and out.endswith(bytes([n]) * n) else out


# ---------------------------------------------------------------------------------------------- leitura do PDF

class Nome(str):
    """Um nome do PDF (/Root vira Nome("Root"))."""


class Ref(tuple):
    """Uma referência a outro objeto: 12 0 R."""


_ESPACO = b"\x00\t\n\x0c\r "
_DELIM = b"()<>[]{}/%"
_ESC = {ord("n"): b"\n", ord("r"): b"\r", ord("t"): b"\t", ord("b"): b"\b", ord("f"): b"\f", ord("("): b"(", ord(")"): b")", ord("\\"): b"\\"}


def _pular(d, i):
    n = len(d)
    while i < n:
        c = d[i]
        if c in _ESPACO:
            i += 1
        elif c == 0x25:  # % comentário até o fim da linha
            while i < n and d[i] not in b"\r\n":
                i += 1
        else:
            break
    return i


def _texto_literal(d, i):
    """O texto entre parênteses que começa em d[i] == '(': (bytes, fim)."""
    out, nivel, i, n = bytearray(), 1, i + 1, len(d)
    while i < n:
        c = d[i]
        if c == 0x5C:  # \
            i += 1
            if i >= n:
                break
            c = d[i]
            if c in _ESC:
                out += _ESC[c]
            elif 0x30 <= c <= 0x37:  # \ddd octal
                j = i
                while j < n and j < i + 3 and 0x30 <= d[j] <= 0x37:
                    j += 1
                out.append(int(d[i:j], 8) & 0xFF)
                i = j - 1
            elif c == 0x0D:  # \ no fim da linha: continua na próxima
                if i + 1 < n and d[i + 1] == 0x0A:
                    i += 1
            elif c != 0x0A:
                out.append(c)
        elif c == 0x28:
            nivel += 1
            out.append(c)
        elif c == 0x29:
            nivel -= 1
            if nivel == 0:
                return bytes(out), i + 1
            out.append(c)
        else:
            out.append(c)
        i += 1
    raise PdfInvalido("texto sem fim")


def _texto_hex(d, i):
    j = d.index(b">", i)
    h = re.sub(rb"[^0-9A-Fa-f]", b"", d[i + 1:j])
    if len(h) % 2:
        h += b"0"
    return bytes.fromhex(h.decode()), j + 1


def _valor(d, i):
    """Lê um valor do PDF a partir de d[i]: (valor, fim). Números, nomes, textos, listas, dicionários, referências."""
    i = _pular(d, i)
    c = d[i:i + 1]
    if c == b"<":
        if d[i + 1:i + 2] == b"<":
            out, i = {}, i + 2
            while True:
                i = _pular(d, i)
                if d[i:i + 2] == b">>":
                    return out, i + 2
                k, i = _valor(d, i)
                v, i = _valor(d, i)
                out[str(k)] = v
        return _texto_hex(d, i)
    if c == b"[":
        out, i = [], i + 1
        while True:
            i = _pular(d, i)
            if d[i:i + 1] == b"]":
                return out, i + 1
            v, i = _valor(d, i)
            out.append(v)
    if c == b"(":
        return _texto_literal(d, i)
    if c == b"/":
        j = i + 1
        while j < len(d) and d[j] not in _ESPACO and d[j] not in _DELIM:
            j += 1
        nome = re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), d[i + 1:j])
        return Nome(nome.decode("latin-1")), j
    m = re.compile(rb"(\d+)\s+(\d+)\s+R(?![A-Za-z])").match(d, i)
    if m:
        return Ref((int(m.group(1)), int(m.group(2)))), m.end()
    m = re.compile(rb"[+-]?(\d+\.?\d*|\.\d+)").match(d, i)
    if m:
        t = m.group(0)
        return (float(t) if b"." in t else int(t)), m.end()
    m = re.compile(rb"true|false|null").match(d, i)
    if m:
        return {b"true": True, b"false": False, b"null": None}[m.group(0)], m.end()
    raise PdfInvalido(f"valor estranho na posição {i}")


_OBJ = re.compile(rb"(\d+)\s+(\d+)\s+obj\b")


class _Leitor:
    def __init__(self, dados):
        self.d = dados
        self.xref = {}  # número -> ("n", posição, geração) ou ("c", número do object stream, índice)
        self.trailer = {}
        self._ler_xref()

    # --- a tabela de posições (xref): a última atualização vale; tabela clássica ou fluxo (PDF 1.5+)
    def _ler_xref(self):
        m = list(re.finditer(rb"startxref\s+(\d+)", self.d))
        pos, vistos = (int(m[-1].group(1)) if m else -1), set()
        while 0 <= pos < len(self.d) and pos not in vistos:
            vistos.add(pos)
            if self.d.startswith(b"xref", _pular(self.d, pos)):
                trailer = self._tabela(_pular(self.d, pos))
                if isinstance(trailer.get("XRefStm"), int):
                    self._fluxo_xref(trailer["XRefStm"])
            else:
                trailer = self._fluxo_xref(pos)
            for k, v in trailer.items():
                self.trailer.setdefault(k, v)
            pos = trailer.get("Prev", -1) if isinstance(trailer.get("Prev"), int) else -1
        if not self.xref or "Root" not in self.trailer:
            self._varrer()

    def _tabela(self, i):
        i += 4
        while True:
            i = _pular(self.d, i)
            if self.d.startswith(b"trailer", i):
                return _valor(self.d, i + 7)[0]
            m = re.compile(rb"(\d+)\s+(\d+)").match(self.d, i)
            if not m:
                raise PdfInvalido("tabela xref quebrada")
            ini, qtd = int(m.group(1)), int(m.group(2))
            i = m.end()
            for k in range(qtd):
                i = _pular(self.d, i)
                e = re.compile(rb"(\d{10})\s(\d{5})\s([nf])").match(self.d, i)
                if not e:
                    raise PdfInvalido("linha da xref quebrada")
                if e.group(3) == b"n":
                    self.xref.setdefault(ini + k, ("n", int(e.group(1)), int(e.group(2))))
                else:
                    self.xref.setdefault(ini + k, ("f",))
                i = e.end()

    def _fluxo_xref(self, pos):
        num, gen, dic, dados = self._objeto_em(pos)
        if not isinstance(dic, dict) or dic.get("Type") != "XRef" or dados is None:
            raise PdfInvalido("xref não encontrada")
        cru = _decodificar(dic, dados)
        w = dic.get("W") or [1, 2, 1]
        indice = dic.get("Index") or [0, dic.get("Size", 0)]
        tam, j = sum(w), 0
        for ini, qtd in zip(indice[0::2], indice[1::2]):
            for k in range(qtd):
                linha = cru[j:j + tam]
                j += tam
                if len(linha) < tam:
                    break
                c = [int.from_bytes(linha[sum(w[:x]):sum(w[:x + 1])], "big") for x in range(3)]
                tipo = c[0] if w[0] else 1
                if tipo == 1:
                    self.xref.setdefault(ini + k, ("n", c[1], c[2]))
                elif tipo == 2:
                    self.xref.setdefault(ini + k, ("c", c[1], c[2]))
                else:
                    self.xref.setdefault(ini + k, ("f",))
        return dic

    def _varrer(self):
        """Sem xref que preste: procura os objetos no arquivo (o último de cada número vale)."""
        for m in re.finditer(rb"(?:^|[\r\n])\s*(\d+)\s+(\d+)\s+obj\b", self.d):
            self.xref[int(m.group(1))] = ("n", m.start(1), int(m.group(2)))
        for m in re.finditer(rb"trailer\s*(<<)", self.d):
            try:
                self.trailer.update(_valor(self.d, m.start(1))[0])
            except PdfInvalido:
                pass
        if "Root" not in self.trailer:  # só fluxos xref: o dicionário deles é o trailer
            for num, ent in self.xref.items():
                try:
                    _, _, dic, _ = self._objeto_em(ent[1])
                except (PdfInvalido, ValueError, IndexError):
                    continue
                if isinstance(dic, dict) and dic.get("Type") == "XRef":
                    self.trailer.update(dic)
        if "Root" not in self.trailer:
            raise PdfInvalido("sem /Root")

    # --- os objetos
    def _objeto_em(self, pos):
        """O objeto que começa em pos: (número, geração, valor, dados do fluxo ou None), mais as posições."""
        m = _OBJ.match(self.d, _pular(self.d, pos))
        if not m:
            raise PdfInvalido(f"objeto não encontrado em {pos}")
        ini = m.end()
        val, fim = _valor(self.d, ini)
        self._ultimo = (ini, fim, None)
        dados = None
        j = _pular(self.d, fim)
        if isinstance(val, dict) and self.d.startswith(b"stream", j):
            j += 6
            if self.d[j:j + 2] == b"\r\n":
                j += 2
            elif self.d[j:j + 1] in (b"\n", b"\r"):
                j += 1
            n = val.get("Length")
            if isinstance(n, Ref):
                n = self._inteiro(n)
            if not isinstance(n, int) or not self.d.startswith(b"endstream", _pular(self.d, j + n)):
                k = self.d.find(b"endstream", j)
                if k < 0:
                    raise PdfInvalido("fluxo sem fim")
                n = k - j
                while n > 0 and self.d[j + n - 1] in b"\r\n":
                    n -= 1
            dados = self.d[j:j + n]
            self._ultimo = (ini, fim, (j, j + n))
        return int(m.group(1)), int(m.group(2)), val, dados

    def _inteiro(self, ref):
        ent = self.xref.get(ref[0])
        if not ent or ent[0] != "n":
            return None
        m = _OBJ.match(self.d, _pular(self.d, ent[1]))
        if not m:
            return None
        v, _ = _valor(self.d, m.end())
        return v if isinstance(v, int) else None

    def valor(self, ref):
        """O valor de um objeto comum (não de dentro de object stream), para o dicionário de cifra."""
        if not isinstance(ref, Ref):
            return ref
        ent = self.xref.get(ref[0])
        if not ent or ent[0] != "n":
            raise PdfInvalido("objeto não encontrado")
        return self._objeto_em(ent[1])[2]


def _png(dados, colunas, cores=1, bits=8):
    """O preditor PNG (/Predictor 10 a 15) dos fluxos de xref."""
    bpp = max(1, cores * bits // 8)
    lin = colunas * cores * bits // 8
    out, ant, i = bytearray(), bytearray(lin), 0
    while i + lin < len(dados) + 1 and i < len(dados):
        tipo, linha = dados[i], bytearray(dados[i + 1:i + 1 + lin])
        i += lin + 1
        for k in range(len(linha)):
            a = linha[k - bpp] if k >= bpp else 0
            b = ant[k] if k < len(ant) else 0
            c = ant[k - bpp] if k >= bpp else 0
            if tipo == 1:
                linha[k] = (linha[k] + a) & 255
            elif tipo == 2:
                linha[k] = (linha[k] + b) & 255
            elif tipo == 3:
                linha[k] = (linha[k] + (a + b) // 2) & 255
            elif tipo == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                linha[k] = (linha[k] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out += linha
        ant = linha
    return bytes(out)


def _decodificar(dic, dados):
    """Os dados de um fluxo sem compressão (só FlateDecode, com ou sem preditor: o que xref e object streams usam)."""
    f = dic.get("Filter")
    filtros = f if isinstance(f, list) else [f] if f else []
    p = dic.get("DecodeParms")
    parms = p if isinstance(p, list) else [p] * len(filtros)
    for filtro, parm in zip(filtros, parms):
        if filtro not in ("FlateDecode", "Fl"):
            raise PdfInvalido(f"filtro {filtro} não suportado")
        try:
            dados = zlib.decompress(dados)
        except zlib.error:
            dados = zlib.decompressobj().decompress(dados)
        if isinstance(parm, dict) and (parm.get("Predictor") or 1) >= 10:
            dados = _png(dados, parm.get("Columns") or 1, parm.get("Colors") or 1, parm.get("BitsPerComponent") or 8)
    return dados


# ---------------------------------------------------------------------------------------------- a cifra do PDF

_PAD = bytes.fromhex("28bf4e5e4e758a4164004e56fffa01082e2e00b6d0683e802f0ca9fe6453697a")


def _hash_r6(senha, sal, udata, r):
    """Algoritmo 2.B (PDF 2.0, R6); na R5, só o SHA-256."""
    k = hashlib.sha256(senha + sal + udata).digest()
    if r == 5:
        return k
    rodada = 0
    while True:
        k1 = (senha + k + udata) * 64
        e = AES(k[:16]).cifrar_cbc(k1, k[16:32])
        k = (hashlib.sha256, hashlib.sha384, hashlib.sha512)[sum(e[:16]) % 3](e).digest()
        rodada += 1
        if rodada >= 64 and e[-1] <= rodada - 32:
            return k[:32]


class _Cifra:
    """A chave do arquivo e como decifrar textos e fluxos de cada objeto."""

    def __init__(self, enc, ident):
        if enc.get("Filter") != "Standard":
            raise PdfInvalido(f"cifra {enc.get('Filter')} não suportada")
        self.enc, self.id0 = enc, ident
        self.v, self.r = int(enc.get("V") or 0), int(enc.get("R") or 2)
        self.o, self.u = bytes(enc.get("O") or b""), bytes(enc.get("U") or b"")
        self.p = struct.pack("<I", int(enc.get("P") or 0) & 0xFFFFFFFF)
        self.metadados = enc.get("EncryptMetadata") is not False
        self.n = 5 if self.v == 1 else max(5, min(16, int(enc.get("Length") or (128 if self.v >= 4 else 40)) // 8))
        self.metodo_fluxo = self.metodo_texto = "rc4"
        if self.v >= 4:
            cf = enc.get("CF") or {}
            self.metodo_fluxo = self._metodo(cf, enc.get("StmF") or "Identity")
            self.metodo_texto = self._metodo(cf, enc.get("StrF") or "Identity")
        self.chave = None

    @staticmethod
    def _metodo(cf, nome):
        if nome == "Identity":
            return None
        cfm = (cf.get(nome) or {}).get("CFM")
        return {"V2": "rc4", "AESV2": "aes", "AESV3": "aes256", "None": None, None: None}.get(cfm, "rc4")

    # --- as senhas
    def _chave_r4(self, senha):
        h = hashlib.md5((senha + _PAD)[:32] + self.o + self.p + self.id0)
        if self.r >= 4 and not self.metadados:
            h.update(b"\xff\xff\xff\xff")
        k = h.digest()
        if self.r >= 3:
            for _ in range(50):
                k = hashlib.md5(k[:self.n]).digest()
        return k[:self.n]

    def _confere_usuario(self, chave):
        if self.r == 2:
            return rc4(chave, _PAD) == self.u[:32]
        x = rc4(chave, hashlib.md5(_PAD + self.id0).digest())
        for i in range(1, 20):
            x = rc4(bytes(b ^ i for b in chave), x)
        return x[:16] == self.u[:16]

    def tentar(self, senha):
        """A senha abre o PDF (como a de abrir ou a do dono)? Guarda a chave."""
        if self.r >= 5:
            s = senha.encode("utf-8")[:127]
            if _hash_r6(s, self.u[32:40], b"", self.r) == self.u[:32]:
                self.chave = AES(_hash_r6(s, self.u[40:48], b"", self.r)).decifrar_cbc(bytes(self.enc.get("UE") or b""), b"\0" * 16)
                return True
            if _hash_r6(s, self.o[32:40], self.u[:48], self.r) == self.o[:32]:
                self.chave = AES(_hash_r6(s, self.o[40:48], self.u[:48], self.r)).decifrar_cbc(bytes(self.enc.get("OE") or b""), b"\0" * 16)
                return True
            return False
        s = senha.encode("latin-1", "ignore")[:32]
        k = self._chave_r4(s)
        if self._confere_usuario(k):
            self.chave = k
            return True
        # a do dono: tira a senha de abrir de dentro de /O
        k = hashlib.md5((s + _PAD)[:32]).digest()
        if self.r >= 3:
            for _ in range(50):
                k = hashlib.md5(k).digest()
        k = k[:self.n]
        if self.r == 2:
            usuario = rc4(k, self.o)
        else:
            usuario = self.o
            for i in range(19, -1, -1):
                usuario = rc4(bytes(b ^ i for b in k), usuario)
        k2 = self._chave_r4(usuario)
        if self._confere_usuario(k2):
            self.chave = k2
            return True
        return False

    # --- decifrar
    def _chave_obj(self, num, gen, metodo):
        if metodo == "aes256":
            return self.chave
        h = hashlib.md5(self.chave + struct.pack("<I", num)[:3] + struct.pack("<I", gen)[:2] + (b"sAlT" if metodo == "aes" else b""))
        return h.digest()[:min(self.n + 5, 16)]

    def decifrar(self, dados, num, gen, fluxo):
        metodo = self.metodo_fluxo if fluxo else self.metodo_texto
        if not metodo:
            return dados
        k = self._chave_obj(num, gen, metodo)
        return rc4(k, dados) if metodo == "rc4" else _aes_texto(k, dados)


# ---------------------------------------------------------------------------------------------- reescrever sem senha

def _hex(b):
    return b"<" + b.hex().encode() + b">"


def _trocar_textos(corpo, troca):
    """O corpo de um objeto com cada texto (literal ou hexadecimal) trocado por troca(bytes) em hexadecimal."""
    out, i, n = bytearray(), 0, len(corpo)
    while i < n:
        c = corpo[i]
        if c == 0x28:
            t, i = _texto_literal(corpo, i)
            out += _hex(troca(t))
        elif c == 0x3C and corpo[i + 1:i + 2] != b"<" and (i == 0 or corpo[i - 1] != 0x3C):
            t, i = _texto_hex(corpo, i)
            out += _hex(troca(t))
        elif c == 0x3C:
            out += b"<<"
            i += 2
        elif c == 0x25:
            while i < n and corpo[i] not in b"\r\n":
                out.append(corpo[i])
                i += 1
        else:
            out.append(c)
            i += 1
    return bytes(out)


def _ref_txt(v):
    return f"{v[0]} {v[1]} R".encode() if isinstance(v, Ref) else None


def _serializar(v):
    if isinstance(v, Ref):
        return _ref_txt(v)
    if isinstance(v, bytes):
        return _hex(v)
    if isinstance(v, list):
        return b"[" + b" ".join(_serializar(x) for x in v) + b"]"
    if isinstance(v, Nome):
        return b"/" + v.encode("latin-1")
    if isinstance(v, bool):
        return b"true" if v else b"false"
    if v is None:
        return b"null"
    if isinstance(v, dict):
        return b"<<" + b" ".join(b"/" + k.encode("latin-1") + b" " + _serializar(x) for k, x in v.items()) + b">>"
    return str(v).encode()


def _sem_length(corpo, novo):
    """O dicionário do fluxo com /Length direto (o novo tamanho), no nível de cima do dicionário."""
    m = re.compile(rb"/Length(?![A-Za-z0-9])\s*(\d+\s+\d+\s+R|\d+)").search(corpo)
    if not m:
        return corpo.rstrip()[:-2] + f"/Length {novo}>>".encode() if corpo.rstrip().endswith(b">>") else corpo
    return corpo[:m.start(1)] + str(novo).encode() + corpo[m.end(1):]


def tem_senha(dados):
    """O PDF tem cifra (/Encrypt no trailer)?"""
    if not dados.startswith(b"%PDF"):
        return False
    try:
        return "Encrypt" in _Leitor(dados).trailer
    except (PdfInvalido, ValueError, IndexError, KeyError):
        return b"/Encrypt" in dados[-4096:] or bool(re.search(rb"/Encrypt\s+\d+\s+\d+\s+R", dados))


def protecao(dados):
    """Só o tipo de proteção do PDF, para o registro (nada do conteúdo nem da senha). Nunca levanta erro."""
    try:
        lido = _Leitor(dados)
        enc = lido.valor(lido.trailer["Encrypt"])
        partes = [str(enc.get("Filter") or "?"), f"V{enc.get('V') or 0}", f"R{enc.get('R') or '?'}"]
        cf = enc.get("CF") or {}
        metodos = sorted({str((cf.get(enc.get(k)) or {}).get("CFM")) for k in ("StmF", "StrF") if enc.get(k) not in (None, "Identity")})
        partes += metodos + ([f"{enc.get('Length')} bits"] if enc.get("Length") else [])
        return " ".join(partes)
    except Exception as e:  # noqa: BLE001 (só para o registro)
        return f"não li a proteção ({type(e).__name__})"


def abrir(dados, senhas):
    """O PDF sem senha, aberto com a primeira senha que servir (também a vazia, para PDFs só com a senha do dono).
    Levanta SenhaErrada se nenhuma servir e PdfInvalido se o arquivo não for entendido."""
    try:
        lido = _Leitor(dados)
        if "Encrypt" not in lido.trailer:
            return dados
        ref_enc = lido.trailer["Encrypt"]
        enc = lido.valor(ref_enc)
        ident = lido.trailer.get("ID") or [b""]
        cifra = _Cifra(enc, bytes(ident[0]) if ident and isinstance(ident[0], bytes) else b"")
    except (ValueError, IndexError, KeyError, TypeError, zlib.error) as e:
        raise PdfInvalido(str(e)) from e
    if not any(cifra.tentar(s) for s in [""] + [str(s) for s in senhas if s is not None]):
        raise SenhaErrada("Nenhuma senha abre este PDF.")
    try:
        return _reescrever(lido, cifra, ref_enc)
    except (ValueError, IndexError, KeyError, TypeError, zlib.error) as e:
        raise PdfInvalido(str(e)) from e


def _reescrever(lido, cifra, ref_enc):
    d = lido.d
    objetos = {}  # número -> (geração, corpo, dados do fluxo ou None)
    num_enc = ref_enc[0] if isinstance(ref_enc, Ref) else None
    for num, ent in sorted(lido.xref.items()):
        if ent[0] != "n" or num == num_enc or num == 0:
            continue
        try:
            n, gen, val, dados = lido._objeto_em(ent[1])
        except PdfInvalido:
            continue
        ini, fim, fl = lido._ultimo
        corpo = d[ini:fim].strip()
        if isinstance(val, dict) and val.get("Type") == "XRef":
            continue  # as tabelas de posições são refeitas no fim
        if dados is not None:
            if not (val.get("Type") == "Metadata" and not cifra.metadados):
                dados = cifra.decifrar(dados, num, gen, True)
            if val.get("Type") == "ObjStm":
                # os objetos guardados aqui viram objetos comuns (os textos deles não são cifrados à parte)
                cru = _decodificar(val, dados)
                primeiro, qtd = int(val.get("First") or 0), int(val.get("N") or 0)
                nums = [int(x) for x in cru[:primeiro].split()[:2 * qtd]]
                pares = list(zip(nums[0::2], nums[1::2]))
                for k, (onum, pos) in enumerate(pares):
                    ent2 = lido.xref.get(onum)
                    if not ent2 or ent2[0] != "c" or ent2[1] != num:
                        continue  # uma versão mais nova vale
                    fimo = primeiro + pares[k + 1][1] if k + 1 < len(pares) else len(cru)
                    objetos[onum] = (0, cru[primeiro + pos:fimo].strip(), None)
                continue
            corpo = _sem_length(corpo, len(dados))
        corpo = _trocar_textos(corpo, lambda t, a=num, b=gen: cifra.decifrar(t, a, b, False))
        objetos[num] = (gen, corpo, dados)

    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    pos = {}
    for num in sorted(objetos):
        gen, corpo, dados = objetos[num]
        pos[num] = (len(out), gen)
        out += f"{num} {gen} obj\n".encode() + corpo
        if dados is not None:
            out += b"\nstream\n" + dados + b"\nendstream"
        out += b"\nendobj\n"
    tam = (max(pos) if pos else 0) + 1
    xref = len(out)
    out += f"xref\n0 {tam}\n0000000000 65535 f \n".encode()
    for k in range(1, tam):
        out += (b"%010d %05d n \n" % pos[k]) if k in pos else b"0000000000 00000 f \n"
    t = {"Size": tam, "Root": lido.trailer["Root"]}
    for k in ("Info", "ID"):
        if k in lido.trailer:
            t[k] = lido.trailer[k]
    out += b"trailer\n" + _serializar(t) + b"\nstartxref\n%d\n%%%%EOF\n" % xref
    return bytes(out)
