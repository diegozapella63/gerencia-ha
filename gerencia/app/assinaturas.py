"""Dicas de economia em assinaturas.

Só entra o que dá para conferir na origem:
1. a assinatura é reconhecida pelo nome (catálogo abaixo, cada uma com a página oficial de preços);
2. o app abre a página oficial e a IA do Home Assistant lista os planos que aparecem lá;
3. cada preço só vale se o trecho citado pela IA estiver escrito na página, com aquele número;
4. o valor que a pessoa paga precisa bater com o preço mensal de um único plano.
"""
import html
import re
import unicodedata

CATALOGO = [
    {"id": "nabucasa", "nome": "Nabu Casa (Home Assistant Cloud)", "curto": "Nabu Casa",
     "padrao": r"\bnabu ?casa\b|\bhome assistant cloud\b|\bha cloud\b",
     "url": "https://www.nabucasa.com/pricing/"},
    {"id": "claude", "nome": "Claude", "curto": "Claude",
     "padrao": r"\bclaude\b|\banthropic\b",
     "url": "https://claude.com/pricing"},
    {"id": "spotify", "nome": "Spotify Premium", "curto": "Spotify",
     "padrao": r"\bspotify\b",
     "url": "https://www.spotify.com/br-pt/premium/"},
    {"id": "microsoft365", "nome": "Microsoft 365", "curto": "Microsoft 365",
     "padrao": r"\bmicrosoft ?365\b|\boffice ?365\b|\bm365\b",
     "url": "https://www.microsoft.com/pt-br/microsoft-365/buy/compare-all-microsoft-365-products"},
    {"id": "deezer", "nome": "Deezer", "curto": "Deezer",
     "padrao": r"\bdeezer\b",
     "url": "https://www.deezer.com/br/offers"},
]
POR_ID = {c["id"]: c for c in CATALOGO}

MOEDAS = ("BRL", "USD", "EUR", "GBP")
SIMBOLO = {"BRL": "R$", "USD": "US$", "EUR": "€", "GBP": "£"}

# Quanto o valor pago pode diferir do preço do plano para dizer que é aquele plano.
# Em reais: arredondamento. Em dólar: câmbio do cartão, IOF e spread em cima do dólar do Banco Central.
TOLERANCIA = {"BRL": (0.95, 1.06), "USD": (0.97, 1.25)}
ALVO = {"BRL": 1.0, "USD": 1.08}
MINIMO_ANO = 10.0     # economia mínima (R$ por ano) para virar dica
MINIMO_PCT = 0.03     # e pelo menos 3%


def normal(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", t)).strip()


def identificar(descricao):
    n = normal(descricao)
    if not n:
        return None
    for c in CATALOGO:
        if re.search(c["padrao"], n):
            return c
    return None


# ---------------------------------------------------------------- página -> texto

_BLOCOS_FORA = re.compile(r"<(script|style|noscript|svg|template|head|iframe)\b.*?</\1\s*>", re.S | re.I)
_QUEBRA = re.compile(r"<\s*(br|/p|/div|/li|/h[1-6]|/tr|/section|/article|/header|/footer|/ul|/ol|/table|/button|/a)\b[^>]*>", re.I)


def html_texto(raw):
    t = _BLOCOS_FORA.sub(" ", raw or "")
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = _QUEBRA.sub("\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ").replace(" ", " ")
    linhas = (re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in t.split("\n"))
    return "\n".join(ln for ln in linhas if ln)


_PRECO = re.compile(r"(?:R\$|US\$|\$|€|£)\s?\d|\d[\d.,]*\s?(?:USD|BRL|EUR|reais|d[oó]lares)\b", re.I)


def trechos_preco(texto, limite=14000, margem=220):
    """Só as partes da página que têm preço, para mandar pouco texto à IA."""
    faixas = []
    for m in _PRECO.finditer(texto):
        a, b = max(0, m.start() - margem), min(len(texto), m.end() + margem)
        if faixas and a <= faixas[-1][1]:
            faixas[-1][1] = b
        else:
            faixas.append([a, b])
    saida, total = [], 0
    for a, b in faixas:
        pedaco = texto[a:b].strip()
        if total + len(pedaco) > limite:
            break
        saida.append(pedaco)
        total += len(pedaco) + 5
    return "\n[...]\n".join(saida)


def para_comparar(t):
    return re.sub(r"\s+", " ", str(t or "").replace("\xa0", " ").lower()).strip()


def numeros(t):
    """Números escritos num trecho, entendendo 1.299,00 / 1,299.00 / 6.50 / 6,50 / 65."""
    out = set()
    for tok in re.findall(r"\d[\d.,]*\d|\d", str(t or "")):
        if "." in tok and "," in tok:
            dec = "," if tok.rfind(",") > tok.rfind(".") else "."
            mil = "." if dec == "," else ","
            v = tok.replace(mil, "").replace(dec, ".")
        elif "," in tok:
            v = tok.replace(",", ".") if len(tok) - tok.rfind(",") - 1 in (1, 2) and tok.count(",") == 1 else tok.replace(",", "")
        elif "." in tok:
            v = tok if len(tok) - tok.rfind(".") - 1 in (1, 2) and tok.count(".") == 1 else tok.replace(".", "")
        else:
            v = tok
        try:
            out.add(round(float(v), 2))
        except ValueError:
            pass
    return out


def confere(trecho, valor, texto_cmp):
    """O trecho está escrito na página e tem esse número?"""
    if not trecho or not valor or valor <= 0:
        return False
    tc = para_comparar(trecho)
    if len(tc) < 3 or tc not in texto_cmp:
        return False
    return any(abs(n - valor) < 0.006 for n in numeros(trecho))


def _num(v):
    try:
        return float(str(v).replace(",", ".")) if v not in (None, "") else 0.0
    except ValueError:
        return 0.0


def limpar_planos(parsed, texto):
    """Fica só com os preços que a página confirma."""
    lista = parsed.get("planos") if isinstance(parsed, dict) else parsed
    texto_cmp = para_comparar(texto)
    planos, so_anual, recusados = [], [], 0
    for p in (lista or [])[:16]:
        if not isinstance(p, dict):
            continue
        moeda = str(p.get("moeda") or "").upper()
        if moeda not in MOEDAS:
            tm = str(p.get("trecho_mensal") or "") + str(p.get("trecho_anual") or "")
            moeda = "BRL" if "R$" in tm else "USD" if "$" in tm else ""
        if not moeda:
            recusados += 1
            continue
        mensal = round(_num(p.get("mensal")), 2)
        at, apm = round(_num(p.get("anual_total")), 2), round(_num(p.get("anual_por_mes")), 2)
        ok_m = confere(p.get("trecho_mensal"), mensal, texto_cmp)
        anual, por_mes = 0.0, False
        if at > 0 and confere(p.get("trecho_anual"), at, texto_cmp):
            anual = at
        elif apm > 0 and confere(p.get("trecho_anual"), apm, texto_cmp):
            anual, por_mes = round(apm * 12, 2), True
        if (mensal > 0 and not ok_m) or ((at > 0 or apm > 0) and not anual):
            recusados += 1
        if not ok_m:
            if anual and mensal <= 0:
                so_anual.append({"moeda": moeda, "anual": anual, "anual_por_mes": por_mes,
                                 "trecho_anual": str(p.get("trecho_anual") or "").strip()[:140]})
            continue
        planos.append({
            "plano": str(p.get("plano") or "").strip()[:60] or "Plano",
            "moeda": moeda, "mensal": mensal, "anual": anual, "anual_por_mes": por_mes,
            "trecho_mensal": str(p.get("trecho_mensal") or "").strip()[:140],
            "trecho_anual": str(p.get("trecho_anual") or "").strip()[:140] if anual else "",
            "anual_recusado": bool((at > 0 or apm > 0) and not anual),
        })
    # página com um cartão "mensal" e outro "anual" do mesmo serviço: junta os dois
    sem_anual = [p for p in planos if not p["anual"]]
    if len(sem_anual) == 1 and len(so_anual) == 1 and sem_anual[0]["moeda"] == so_anual[0]["moeda"]:
        sem_anual[0].update(so_anual[0], anual_recusado=False)
    return planos, recusados


PROMPT = """Você lê a página oficial de preços de {nome} ({url}). Abaixo estão os trechos da página que têm preços.
Liste cada plano pago para pessoa física que aparece, com o preço cobrado mês a mês e o preço do plano anual, quando houver.
Para cada plano, devolva:
- "plano": o nome do plano como está na página.
- "moeda": "BRL", "USD", "EUR" ou "GBP".
- "mensal": preço do plano pago mês a mês, como número (6.5 para $6.50; 23.9 para R$ 23,90); 0 se a página não mostrar.
- "trecho_mensal": o pedaço do texto, copiado exatamente como está abaixo (até 80 caracteres), onde aparece o preço mensal.
- "anual_total": preço total de 1 ano pago de uma vez, como número; 0 se não houver.
- "anual_por_mes": se a página só mostrar o anual como valor por mês (ex.: "$17 por mês no plano anual"), esse valor; senão 0.
- "trecho_anual": o pedaço do texto, copiado exatamente como está abaixo, onde aparece o preço anual; "" se não houver.
Se a página mostrar o mesmo serviço em dois cartões, um mensal e outro anual, junte os dois num plano só.
Use só números escritos nos trechos. Não use preços que você conhece de memória. Ignore teste grátis, promoções por tempo limitado, planos de empresa ou equipe, planos de 3 ou 6 meses e complementos.
Responda somente com JSON válido, sem markdown e sem texto antes ou depois, neste formato:
{{"planos":[{{"plano":"","moeda":"BRL","mensal":0,"trecho_mensal":"","anual_total":0,"anual_por_mes":0,"trecho_anual":""}}]}}

Trechos da página:
<<<
{trechos}
>>>"""


def prompt(servico, trechos):
    return PROMPT.format(nome=servico["nome"], url=servico["url"], trechos=trechos)


# ---------------------------------------------------------------- casar com o que a pessoa paga

def casar(valor, planos, dolar):
    """Qual plano da página é o que a pessoa paga? Devolve (plano, motivo)."""
    candidatos = []
    for p in planos:
        if p["mensal"] <= 0:
            continue
        if p["moeda"] == "BRL":
            preco = p["mensal"]
        elif p["moeda"] == "USD" and dolar:
            preco = p["mensal"] * dolar
        else:
            continue
        lo, hi = TOLERANCIA[p["moeda"]]
        razao = valor / preco
        if lo <= razao <= hi:
            candidatos.append((abs(razao - ALVO[p["moeda"]]), p))
    if not candidatos:
        return None, "plano_nao_bate"
    candidatos.sort(key=lambda x: x[0])
    melhor = candidatos[0][1]
    # dois planos com o mesmo preço mensal e anuais diferentes: não dá para saber qual é
    iguais = [p for _, p in candidatos if abs(p["mensal"] - melhor["mensal"]) < 0.01 and p["moeda"] == melhor["moeda"]]
    if len({p["anual"] for p in iguais}) > 1:
        return None, "ambiguo"
    return melhor, None


def avaliar(valor, fonte, dolar):
    """Uma assinatura (valor mensal em reais) contra a fonte conferida. Devolve status e, se valer, a economia."""
    if not fonte:
        return {"status": "pendente"}
    if fonte.get("status") != "ok":
        return {"status": fonte.get("status") or "erro"}
    usa_dolar = any(p["moeda"] == "USD" for p in fonte.get("planos", []))
    if usa_dolar and not dolar and not any(p["moeda"] == "BRL" for p in fonte["planos"]):
        return {"status": "sem_dolar"}
    plano, motivo = casar(valor, fonte.get("planos", []), dolar)
    if not plano:
        return {"status": motivo}
    base = {"plano": plano["plano"], "moeda": plano["moeda"], "mensal": plano["mensal"], "anual": plano["anual"],
            "anual_por_mes": plano["anual_por_mes"], "trecho_mensal": plano["trecho_mensal"], "trecho_anual": plano["trecho_anual"]}
    if not plano["anual"]:
        return {"status": "nao_confere" if plano.get("anual_recusado") else "sem_anual", **base}
    pct = 1 - plano["anual"] / (12 * plano["mensal"])
    economia = round(12 * valor * pct, 2)
    if pct < MINIMO_PCT or economia < MINIMO_ANO:
        return {"status": "sem_vantagem", "pct": round(pct * 100, 1), **base}
    preco_anual = round(plano["anual"], 2) if plano["moeda"] == "BRL" else round(12 * valor * (1 - pct), 2)
    return {"status": "ok", "pct": round(pct * 100, 1), "economia_ano": economia, "preco_anual": preco_anual,
            "estimado": plano["moeda"] != "BRL", **base}


TEXTOS = {
    "pendente": "Ainda não conferido.",
    "conferindo": "Conferindo na página oficial…",
    "sem_ia": "Para ler a página oficial, o app precisa da IA do Home Assistant.",
    "sem_acesso": "Não deu para abrir a página oficial agora. O app tenta de novo amanhã.",
    "sem_precos": "A página oficial não mostrou preços para o app (pode depender do navegador).",
    "erro_ia": "A IA não conseguiu ler a página. O app tenta de novo amanhã.",
    "nao_confere": "A IA citou preços que não estão escritos na página, então o app ignorou.",
    "sem_dolar": "Faltou a cotação do dólar do Banco Central para comparar.",
    "plano_nao_bate": "O valor que você paga não bate com nenhum plano da página.",
    "ambiguo": "Há mais de um plano com esse preço; não dá para saber qual é o seu.",
    "sem_anual": "A página não mostra plano anual para o seu plano.",
    "sem_vantagem": "O plano anual custa quase o mesmo que pagar por mês.",
    "ja_anual": "Já está no plano anual.",
    "ok": "Dá para economizar no plano anual.",
    "erro": "Não deu para conferir.",
}
