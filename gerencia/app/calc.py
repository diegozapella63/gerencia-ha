"""Cálculos do GerencIA (espelho dos cálculos de www/app.js).

Taxas são guardadas em porcentagem (13.65 = 13,65% a.a.) e convertidas aqui.
"""
from datetime import date, datetime

INDEXADORES = {
    "cdi_pct": "% do CDI",
    "cdi_mais": "CDI +",
    "pre": "Prefixado",
    "ipca_mais": "IPCA +",
    "selic_mais": "Selic +",
    "poupanca": "Poupança",
    "estimado": "Estimado",
    "parado": "Sem rendimento",
}

TIPOS = {
    "cdb": "CDB",
    "lci": "LCI/LCA",
    "tesouro": "Tesouro",
    "poupanca": "Poupança",
    "caixinha": "Caixinha",
    "fundo": "Fundo",
    "acoes": "Ações/FII",
    "previdencia": "Previdência",
    "outro": "Outro",
}

# Indexadores de renda variável/sem rendimento não são corrigidos automaticamente.
SEM_CORRECAO = {"estimado", "parado"}


def parse_data(s):
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def dias_uteis(d0, d1):
    """Dias úteis (seg-sex) depois de d0 até d1, inclusive. Feriados não entram."""
    if d0 is None or d1 is None or d1 <= d0:
        return 0
    total = (d1 - d0).days
    semanas, resto = divmod(total, 7)
    n = semanas * 5
    wd = d0.weekday()
    for i in range(1, resto + 1):
        if (wd + i) % 7 < 5:
            n += 1
    return n


def num(v, padrao=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return padrao


def taxa_anual(inv, ind):
    """Taxa anual efetiva estimada (decimal) com os índices de hoje."""
    t = num(inv.get("taxa")) / 100
    cdi = num(ind.get("cdi")) / 100
    selic = num(ind.get("selic")) / 100
    ipca = num(ind.get("ipca")) / 100
    tr = num(ind.get("tr")) / 100
    k = inv.get("indexador")
    if k == "cdi_pct":
        return cdi * t
    if k == "cdi_mais":
        return (1 + cdi) * (1 + t) - 1
    if k == "pre":
        return t
    if k == "ipca_mais":
        return (1 + ipca) * (1 + t) - 1
    if k == "selic_mais":
        return (1 + selic) * (1 + t) - 1
    if k == "poupanca":
        mensal = 0.005 if selic > 0.085 else (1 + 0.7 * selic) ** (1 / 12) - 1
        return ((1 + mensal) * (1 + tr)) ** 12 - 1
    if k == "estimado":
        return t
    return 0.0


def valor_hoje(inv, ind, corrigir=True, hoje=None):
    hoje = hoje or date.today()
    v = num(inv.get("valor"))
    if not corrigir or inv.get("indexador") in SEM_CORRECAO:
        return v
    d0 = parse_data(inv.get("data_valor")) or hoje
    du = dias_uteis(d0, hoje)
    return v * (1 + taxa_anual(inv, ind)) ** (du / 252)


def rende_mes(v, r):
    return v * ((1 + r) ** (1 / 12) - 1)


def fmt_num(x, casas=2):
    s = f"{x:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(x):
    s = fmt_num(x, 2)
    if "," in s:
        s = s.rstrip("0").rstrip(",")
    return s


def fmt_brl(x, casas=2):
    return "R$ " + fmt_num(x, casas)


def rotulo_taxa(inv):
    t = num(inv.get("taxa"))
    k = inv.get("indexador")
    if k == "cdi_pct":
        return f"{fmt_pct(t)}% do CDI"
    if k == "cdi_mais":
        return f"CDI + {fmt_pct(t)}% a.a."
    if k == "pre":
        return f"{fmt_pct(t)}% a.a. pré"
    if k == "ipca_mais":
        return f"IPCA + {fmt_pct(t)}% a.a."
    if k == "selic_mais":
        return "Selic" if t == 0 else f"Selic + {fmt_pct(t)}% a.a."
    if k == "poupanca":
        return "Poupança"
    if k == "estimado":
        return f"≈ {fmt_pct(t)}% a.a. estimado"
    return "Sem rendimento"


def dono(inv):
    if inv.get("titular") == "terceiros":
        return (inv.get("terceiro") or "").strip() or "Terceiros"
    return "Meu"


def totais(data, hoje=None):
    ind = data.get("indices", {})
    corrigir = data.get("ajustes", {}).get("corrigir", True)
    total = meu = terc = mes = 0.0
    pessoas = {}
    for inv in data.get("investimentos", []):
        v = valor_hoje(inv, ind, corrigir, hoje)
        r = taxa_anual(inv, ind)
        total += v
        mes += rende_mes(v, r)
        if inv.get("titular") == "terceiros":
            terc += v
            p = dono(inv)
            pessoas[p] = pessoas.get(p, 0) + v
        else:
            meu += v
    return {
        "total": round(total, 2),
        "meu": round(meu, 2),
        "terceiros": round(terc, 2),
        "rende_mes": round(mes, 2),
        "pessoas": {k: round(v, 2) for k, v in pessoas.items()},
        "quantidade": len(data.get("investimentos", [])),
    }
