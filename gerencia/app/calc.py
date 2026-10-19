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


# ---------------------------------------------------------------- caixa (recebimentos e despesas)

CATEGORIAS_PADRAO = [
    ("c-moradia", "Moradia", "despesa", "#56AEFF"),
    ("c-mercado", "Mercado", "despesa", "#4CD3A5"),
    ("c-restaurantes", "Restaurantes", "despesa", "#FFA23A"),
    ("c-transporte", "Transporte", "despesa", "#B79BFF"),
    ("c-contas", "Contas da casa", "despesa", "#F2C14E"),
    ("c-saude", "Saúde", "despesa", "#FF77A8"),
    ("c-educacao", "Educação", "despesa", "#FF8A65"),
    ("c-lazer", "Lazer", "despesa", "#E04B8A"),
    ("c-assinaturas", "Assinaturas", "despesa", "#FF5A4E"),
    ("c-compras", "Compras", "despesa", "#B8B0B0"),
    ("c-pets", "Pets", "despesa", "#4CD3A5"),
    ("c-impostos", "Impostos e taxas", "despesa", "#FFA23A"),
    ("c-outros-gastos", "Outros gastos", "despesa", "#B8B0B0"),
    ("c-salario", "Salário", "receita", "#4CD3A5"),
    ("c-freelance", "Freelance", "receita", "#56AEFF"),
    ("c-rendimentos", "Rendimentos", "receita", "#B79BFF"),
    ("c-vendas", "Vendas", "receita", "#FFA23A"),
    ("c-reembolso", "Reembolso", "receita", "#F2C14E"),
    ("c-outros-receb", "Outros recebimentos", "receita", "#B8B0B0"),
]


def categorias_padrao():
    return [{"id": i, "nome": n, "tipo": t, "cor": c} for i, n, t, c in CATEGORIAS_PADRAO]


def _data_mes(a, m, dia):
    """Data do dia `dia` no mês (a, m), com m podendo passar de 12; dia limitado ao fim do mês."""
    a += (m - 1) // 12
    m = (m - 1) % 12 + 1
    ult = (date(a + (m == 12), m % 12 + 1, 1) - date(a, m, 1)).days
    return date(a, m, max(1, min(int(dia or 1), ult)))


def mapa_contas(data):
    """Contas de cada banco, por id. Cada conta é de uma pessoa e pode ter cartão de crédito."""
    contas = {}
    for b in data.get("bancos", []):
        for c in b.get("contas") or []:
            if isinstance(c, dict) and c.get("id"):
                contas[c["id"]] = dict(c, banco=b.get("id"), banco_nome=b.get("nome", ""))
    return contas


def nome_conta(c):
    if not c:
        return ""
    return c.get("banco_nome", "") + (f" · {c['pessoa']}" if c.get("pessoa") else "")


def data_caixa(l, contas):
    """Dia em que o dinheiro sai ou entra: no cartão, o vencimento da fatura que pega a compra."""
    d = parse_data(l.get("data"))
    c = contas.get(l.get("conta")) if l.get("cartao") else None
    if not d or not c or not c.get("cartao"):
        return d
    fech, venc = int(c.get("fechamento") or 1), int(c.get("vencimento") or 10)
    m = d.month + (1 if d.day >= fech else 0)
    if venc <= fech:
        m += 1
    return _data_mes(d.year, m, venc)


def ocorrencias_mes(data, ym):
    """Lançamentos reais mais as ocorrências das recorrências (gastos fixos) da competência `ym`."""
    reais = [l for l in data.get("lancamentos", []) if str(l.get("data") or "")[:7] == ym]
    feitos = {(l.get("recorrencia"), l.get("competencia")) for l in data.get("lancamentos", []) if l.get("recorrencia")}
    a, m = int(ym[:4]), int(ym[5:7])
    out = list(reais)
    for r in data.get("recorrencias", []):
        if (r.get("inicio") or "9999") > ym or (r.get("fim") and r["fim"] < ym) or (r.get("id"), ym) in feitos:
            continue
        o = dict(r)
        o.update({"data": _data_mes(a, m, r.get("dia")).isoformat(), "pago": False, "recorrencia": r.get("id"), "competencia": ym})
        out.append(o)
    return [l for l in out if not l.get("pulado")]


def caixa(data, hoje=None):
    """Saldo em caixa (pagos até hoje, pela data do caixa) e o movimento do mês atual. Ajustes só entram no saldo."""
    hoje = hoje or date.today()
    hi = hoje.isoformat()
    ym = hi[:7]
    cartoes = mapa_contas(data)
    r = {"saldo": 0.0, "entrou_mes": 0.0, "saiu_mes": 0.0, "a_receber_mes": 0.0, "a_pagar_mes": 0.0, "atrasado": 0.0}
    for l in data.get("lancamentos", []):
        if l.get("pulado"):
            continue
        dc = data_caixa(l, cartoes)
        if l.get("pago") and dc and dc.isoformat() <= hi:
            r["saldo"] += num(l.get("valor")) * (1 if l.get("tipo") == "receita" else -1)
    # movimento do mês: competências deste mês e dos dois anteriores (o cartão empurra a saída para frente)
    a, m = hoje.year, hoje.month
    vistos = []
    for k in (2, 1, 0):
        mm = _data_mes(a, m - k, 1)
        vistos += ocorrencias_mes(data, mm.isoformat()[:7])
    for l in vistos:
        if l.get("ajuste"):
            continue
        dc = data_caixa(l, cartoes)
        if not dc:
            continue
        v = num(l.get("valor"))
        rec = l.get("tipo") == "receita"
        pago = bool(l.get("pago"))
        if not pago and not rec and dc.isoformat() < hi:
            r["atrasado"] += v
        if dc.isoformat()[:7] != ym:
            continue
        if rec:
            r["entrou_mes" if pago else "a_receber_mes"] += v
        else:
            r["saiu_mes" if pago else "a_pagar_mes"] += v
    return {k: round(x, 2) for k, x in r.items()}
