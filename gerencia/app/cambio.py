"""Câmbio do Banco Central (1.100.0): a PTAX de venda do dólar, do euro e da libra, pelos dados abertos do Banco Central
(Olinda, sem chave). Só biblioteca padrão. Quem guarda a cotação do dia e decide quando buscar é o server.py.

A PTAX é a taxa de referência: a compra no cartão ou na conta global sai um pouco diferente (a cotação do banco, o
spread e o IOF), então a conversão daqui é uma estimativa, e o texto diz isso.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

BASE = os.environ.get("GERENCIA_PTAX", "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata")  # GERENCIA_PTAX: só para testes
MOEDAS = {"USD": ("Dólar", "US$"), "EUR": ("Euro", "€"), "GBP": ("Libra", "£")}
APELIDOS = {"dolar": "USD", "dolares": "USD", "us$": "USD", "usd": "USD", "euro": "EUR", "euros": "EUR", "eur": "EUR", "€": "EUR",
            "libra": "GBP", "libras": "GBP", "gbp": "GBP", "£": "GBP", "real": "BRL", "reais": "BRL", "brl": "BRL", "r$": "BRL"}
DIAS = 10  # a janela pedida: cobre fim de semana e feriado emendado


class Erro(Exception):
    pass


def moeda(v):
    """USD, EUR, GBP ou BRL pelo código ou pelo nome (dólar, euros, libra); "" se não é uma delas."""
    t = str(v or "").strip().lower().replace("ó", "o")
    return APELIDOS.get(t, "")


def da_resposta(d):
    """(venda, AAAA-MM-DD) do boletim mais recente de uma resposta da PTAX (cada dia tem até cinco; o último é o fechamento)."""
    linhas = d.get("value") if isinstance(d, dict) else None
    melhor = None
    for x in linhas if isinstance(linhas, list) else []:
        if not isinstance(x, dict):
            continue
        v, q = x.get("cotacaoVenda"), str(x.get("dataHoraCotacao") or "")
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 < v < 1000 or len(q) < 10:
            continue
        if melhor is None or q > melhor[1]:
            melhor = (round(float(v), 4), q)
    if not melhor:
        raise Erro("O Banco Central não trouxe a cotação.")
    return melhor[0], melhor[1][:10]


def ptax(cod, hoje=None, timeout=15, base=None):
    """(venda, data) da PTAX mais recente da moeda (USD, EUR ou GBP)."""
    if cod not in MOEDAS:
        raise Erro(f"Moeda desconhecida: {cod}.")
    fim = hoje or date.today()
    ini = fim - timedelta(days=DIAS)
    q = urllib.parse.urlencode({"@moeda": f"'{cod}'", "@dataInicial": f"'{ini:%m-%d-%Y}'", "@dataFinalCotacao": f"'{fim:%m-%d-%Y}'",
                                "$format": "json", "$select": "cotacaoVenda,dataHoraCotacao,tipoBoletim"}, safe="@$'")
    url = f"{base or BASE}/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?{q}"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "GerencIA/1.0 (Home Assistant)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read(400000).decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError):
        raise Erro("Sem resposta do Banco Central.") from None
    return da_resposta(d)


def todas(hoje=None, base=None):
    """{USD: {valor, data}, ...} das que responderam (pode vir vazio)."""
    out = {}
    for cod in MOEDAS:
        try:
            v, dt = ptax(cod, hoje, base=base)
            out[cod] = {"valor": v, "data": dt}
        except Erro:
            pass
    return out


def em_reais(valor, cod, moedas):
    """O valor em reais pela PTAX guardada, ou None sem a cotação."""
    c = (moedas or {}).get(cod) or {}
    return round(float(valor) * c["valor"], 2) if c.get("valor") else None
