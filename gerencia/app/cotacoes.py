"""Cotações da B3 pela brapi (1.99.0): o preço de uma ação, fundo imobiliário, ETF ou BDR pelo código (PETR4, MXRF11).

Só biblioteca padrão. A chave é a de cada casa (o plano grátis da brapi dá 15 mil consultas por mês, um ativo por consulta);
vai no cabeçalho Authorization, nunca no endereço. Quem guarda a chave e decide quando atualizar é o server.py.
"""
import json
import os
import re
import urllib.error
import urllib.request

BASE = os.environ.get("GERENCIA_BRAPI", "https://brapi.dev/api")
TICKER_RE = re.compile(r"^(?=.*[A-Z])[A-Z0-9]{4,8}$")
MAX_PAPEIS = 40


class Erro(Exception):
    """O que deu errado, numa frase para a tela. fatal: não adianta tentar os outros papéis (a chave, o limite, sem internet)."""

    def __init__(self, texto, fatal=False):
        super().__init__(texto)
        self.fatal = fatal


def limpar_ticker(v):
    """O código como a bolsa escreve (PETR4); "" se não parece um código. O fracionário (PETR4F) é o mesmo papel."""
    t = re.sub(r"[^A-Z0-9]", "", str(v or "").upper())
    if re.match(r"^[A-Z]{4}[0-9]{1,2}F$", t):
        t = t[:-1]
    return t if TICKER_RE.match(t) else ""


def quantidade(v):
    """A quantidade de cotas ou ações (0 se não é um número que valha)."""
    if isinstance(v, bool):
        return 0.0
    try:
        n = float(str(v).replace(",", ".")) if isinstance(v, str) else float(v)
    except (TypeError, ValueError):
        return 0.0
    return round(n, 6) if 0 < n < 1e9 else 0.0


def cotacao(ticker, token, timeout=15, base=None):
    """{preco, em, nome} do papel agora. Erro diz o que houve."""
    t = limpar_ticker(ticker)
    if not t:
        raise Erro(f"{ticker} não parece um código da bolsa (como PETR4 ou MXRF11).")
    req = urllib.request.Request(f"{base or BASE}/quote/{t}", headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "GerencIA"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read(200000).decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise Erro("A brapi recusou a chave.", fatal=True) from None
        if e.code == 404:
            raise Erro(f"{t} não foi encontrado na B3.") from None
        if e.code == 429:
            raise Erro("O limite de consultas da brapi acabou por agora.", fatal=True) from None
        raise Erro(f"A brapi respondeu com erro ({e.code}).") from None
    except (urllib.error.URLError, OSError, ValueError):
        raise Erro("Sem resposta da brapi.", fatal=True) from None
    res = d.get("results") if isinstance(d, dict) else None
    r0 = res[0] if isinstance(res, list) and res and isinstance(res[0], dict) else {}
    p = r0.get("regularMarketPrice")
    if isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 < p < 1e7:
        raise Erro(f"A brapi não trouxe o preço de {t}.")
    return {"preco": round(float(p), 4), "em": str(r0.get("regularMarketTime") or "")[:19], "nome": str(r0.get("longName") or r0.get("shortName") or "")[:80]}


def papeis(d):
    """Os investimentos com código e quantidade: [(investimento, código, quantidade)], até MAX_PAPEIS códigos diferentes."""
    out, vistos = [], set()
    for i in d.get("investimentos", []):
        t, q = limpar_ticker(i.get("ticker")), quantidade(i.get("qtd"))
        if not t or not q:
            continue
        if t not in vistos and len(vistos) >= MAX_PAPEIS:
            continue
        vistos.add(t)
        out.append((i, t, q))
    return out


def aplicar(d, precos, hoje):
    """Põe o valor de hoje (quantidade × preço) em cada investimento com código cujo preço veio. Devolve quantos mudaram."""
    n = 0
    for i, t, q in papeis(d):
        c = precos.get(t)
        if not c:
            continue
        valor = round(q * c["preco"], 2)
        nova = {"preco": c["preco"], "em": c.get("em") or ""}
        if abs((i.get("valor") or 0) - valor) >= 0.005 or i.get("data_valor") != hoje or i.get("cotacao") != nova:
            i.update(valor=valor, data_valor=hoje, cotacao=nova, ticker=t, qtd=q)
            n += 1
    return n
