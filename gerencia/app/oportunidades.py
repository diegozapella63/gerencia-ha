"""Oportunidades de investimento (Mais › Invest › Oportunidades): as taxas do dia do Tesouro Direto e as ofertas das
páginas que a pessoa escolher, comparadas com o que ela quer (Avisar quando passar de) e com os investimentos dela.

1. Tesouro Direto: a tabela "Investir" do site oficial (CSV com ;, título, rendimento, mínimo, preço e vencimento);
   se ela não abrir, os dados abertos do Tesouro Transparente (todas as datas; ficam os títulos à venda no dia mais novo).
2. Páginas de ofertas (só com a IA ligada): o app abre a página, a IA do Home Assistant lista os CDB, RDB, LC, LCI e
   LCA que aparecem lá, e cada taxa só vale se o trecho citado pela IA estiver escrito na página, com aquele número
   (como as dicas de economia, em assinaturas.py). Entram CDB, RDB, LC, LCI, LCA e as caixinhas e cofrinhos das contas
   (Mercado Pago, Nubank…), com o nome e a condição que a página escreve (ex.: "clientes Ultravioleta").
3. A conta (equivalente, passa_alvo e comparar_meus) fica no calc.py, igual à do app.js.
Só biblioteca padrão do Python.
"""
import hashlib
import re
import unicodedata
from datetime import date, datetime
from urllib.parse import urlparse

import assinaturas
import calc

TESOURO_URL = "https://www.tesourodireto.com.br/documents/d/guest/rendimento-investir-csv?download=true"
TRANSPARENTE_URL = ("https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/"
                    "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv")
# as famílias do Tesouro que entram nas oportunidades; Renda+ e Educa+ (para a aposentadoria e a faculdade, pagos em
# parcelas) e IGP-M ficam de fora
FAMILIAS = ("selic", "pre", "ipca")
INDEXADOR_FAMILIA = {"selic": "selic_mais", "pre": "pre", "ipca": "ipca_mais", "renda": "ipca_mais", "educa": "ipca_mais"}
PRODUTOS = {"cdb": "CDB", "rdb": "RDB", "lc": "LC", "lci": "LCI", "lca": "LCA", "conta": "Caixinha"}
# páginas públicas conferidas (a taxa está escrita no texto da página): um toque põe na lista
SUGESTOES = [
    {"nome": "Mercado Pago", "url": "https://www.mercadopago.com.br/cofrinhos"},
    {"nome": "Nubank", "url": "https://nubank.com.br/nu/caixinhas"},
    {"nome": "PagBank", "url": "https://pagbank.com.br/cdb"},
    {"nome": "Inter", "url": "https://inter.co/pra-voce/investimentos/meu-porquinho/"},
    {"nome": "Comparativo de CDBs", "url": "https://www.idinheiro.com.br/investimentos/melhor-cdb-liquidez-diaria-hoje/"},
]
ISENTOS = {"lci", "lca"}
# a taxa que faz sentido em cada indexador (fora disso, a IA leu errado)
FAIXA = {"cdi_pct": (50, 250), "cdi_mais": (0.01, 15), "pre": (2, 40), "ipca_mais": (0.5, 20)}
# quanto a taxa precisa subir para uma oportunidade já avisada ser avisada de novo, na unidade da família
SUBIU = {"pos": 1.0, "pre": 0.10, "ipca": 0.10}
MAX_PAGINAS = 10
URL_RE = re.compile(r"^https?://[^\s/$.?#][^\s]*$", re.I)


def normal(t):
    t = unicodedata.normalize("NFKD", str(t or ""))
    return re.sub(r"\s+", " ", "".join(c for c in t if not unicodedata.combining(c)).lower()).strip()


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", normal(t).replace("+", " mais ")).strip("-")


def decodificar(bruto):
    """O CSV do Tesouro vem em Windows-1252 (às vezes em UTF-8)."""
    if isinstance(bruto, str):
        return bruto
    try:
        return bruto.decode("utf-8")
    except UnicodeDecodeError:
        return bruto.decode("cp1252", "replace")


def data_br(s):
    """dd/mm/aaaa -> aaaa-mm-dd ("" se não for data)."""
    m = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*", str(s or ""))
    if not m:
        return ""
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except ValueError:
        return ""


def familia_tesouro(nome):
    n = normal(nome)
    for chave, fam in (("renda+", "renda"), ("educa+", "educa"), ("igpm", "igpm"), ("igp-m", "igpm"), ("ipca", "ipca"),
                       ("prefixado", "pre"), ("selic", "selic"), ("reserva", "selic")):
        if chave in n:
            return fam
    return ""


_REND_IDX = re.compile(r"^\s*(SELIC|IPCA)\s*(?:\+\s*(-?\d[\d.,]*)\s*%?)?\s*$", re.I)
_REND_PRE = re.compile(r"^\s*(\d[\d.,]*)\s*%\s*$")


def rendimento(txt):
    """ "SELIC + 0,1064%" -> ("selic_mais", 0.1064); "SELIC" -> ("selic_mais", 0); "IPCA + 7,82%" -> ("ipca_mais",
    7.82); "15,10%" -> ("pre", 15.1). Outra coisa: None."""
    m = _REND_IDX.match(str(txt or ""))
    if m:
        return ("selic_mais" if m.group(1).upper() == "SELIC" else "ipca_mais", calc.num_br(m.group(2), 0.0) if m.group(2) else 0.0)
    m = _REND_PRE.match(str(txt or ""))
    if m:
        return ("pre", calc.num_br(m.group(1)))
    return None


def titulo(nome, indexador, taxa, vencimento, minimo=0.0, preco=0.0):
    return {"id": "td:" + slug(nome), "nome": nome, "origem": "tesouro", "fonte": "Tesouro Direto", "produto": "tesouro",
            "familia": familia_tesouro(nome), "indexador": indexador, "taxa": round(float(taxa), 4), "isento": False,
            "vencimento": vencimento, "liquidez": "diaria", "minimo": round(float(minimo or 0), 2), "preco": round(float(preco or 0), 2)}


def ler_investir(bruto):
    """A tabela Investir do site do Tesouro Direto: Título;Rendimento anual do título;Investimento mínimo;Preço
    unitário de investimento;Vencimento do Título. Devolve os títulos (as linhas que não se entendem ficam fora)."""
    out = []
    for linha in decodificar(bruto).splitlines():
        cols = [c.strip().strip('"').strip() for c in linha.split(";")]
        if len(cols) < 5 or not cols[0]:
            continue
        r, venc = rendimento(cols[1]), data_br(cols[4])
        if not r or not venc:
            continue
        out.append(titulo(re.sub(r"\s+", " ", cols[0]), r[0], r[1], venc, calc.num_br(cols[2]), calc.num_br(cols[3])))
    return out


def ler_transparente(linhas):
    """Os dados abertos do Tesouro Transparente (Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;...): todas as
    datas, uma linha por título e dia. Fica o dia mais novo, só com os títulos à venda (taxa de compra maior que 0).
    Devolve (títulos, o dia das taxas)."""
    dia, lista = "", []
    for linha in linhas:
        cols = [c.strip().strip('"').strip() for c in decodificar(linha).strip().split(";")]
        if len(cols) < 4:
            continue
        venc, base = data_br(cols[1]), data_br(cols[2])
        taxa = calc.num_br(cols[3], 0.0)
        fam = familia_tesouro(cols[0])
        if not venc or not base or taxa <= 0 or fam not in INDEXADOR_FAMILIA or base < dia:
            continue
        if base > dia:
            dia, lista = base, []
        nome = re.sub(r"\s+", " ", cols[0])
        lista.append(titulo(f"{nome} {venc[:4]}", INDEXADOR_FAMILIA[fam], taxa, venc))
    return lista, dia


def do_tesouro(titulos):
    """Os títulos que entram nas oportunidades (Selic, Prefixado e IPCA+), do vencimento mais perto ao mais longe."""
    return sorted((t for t in titulos or [] if t.get("familia") in FAMILIAS), key=lambda t: (FAMILIAS.index(t["familia"]), t["vencimento"], t["nome"]))


# ---------------------------------------------------------------- páginas de ofertas (lidas pela IA)

_TAXA = re.compile(r"\d[\d.,]*\s?%|\bCDI\b|\bIPCA\b|\bpr[eé][- ]?fixad", re.I)


def limpar_url(u):
    u = str(u or "").strip()
    return u if URL_RE.match(u) and len(u) <= 400 else ""


def dominio(url):
    return (urlparse(url).hostname or "").removeprefix("www.")


def trechos_taxa(texto):
    """Só as partes da página com taxa (%, CDI, IPCA, prefixado), para mandar pouco texto à IA."""
    return assinaturas.trechos_preco(texto, limite=14000, margem=260, padrao=_TAXA)


PROMPT = """Este é o texto de uma página de investimentos de um banco, corretora ou conta digital ({url}).
Liste as ofertas de CDB, RDB, LC, LCI e LCA e as caixinhas, cofrinhos e contas que rendem uma taxa (produto "conta"),
com a taxa escrita no texto. Uma oferta por taxa: "100% do CDI" e "até 120% do CDI para clientes X" são duas.

Responda só com JSON, sem texto fora dele:
{{"ofertas": [{{"emissor": "o banco ou a conta (ex.: Nubank)", "nome": "o nome do produto na página (ex.: Caixinha Turbo), ou vazio",
  "produto": "cdb | rdb | lc | lci | lca | conta", "condicao": "a condição para essa taxa, curta (ex.: clientes Ultravioleta; até R$ 10 mil), ou vazio",
  "indexador": "cdi_pct | cdi_mais | pre | ipca_mais",
  "taxa": número (110 para 110% do CDI; 1.5 para CDI + 1,5%; 14.2 para 14,2% ao ano; 7.1 para IPCA + 7,1%),
  "vencimento": "AAAA-MM-DD ou vazio", "liquidez": "diaria | vencimento | vazio", "minimo": número em reais ou 0,
  "trecho": "o pedaço do texto, copiado igual, com a taxa"}}]}}

Regras: só o que está escrito no texto (não invente nem calcule); fundos, ações, debêntures, CRI, CRA e Tesouro ficam
de fora; "rende até X% do CDI" vale X; sem nenhuma oferta, {{"ofertas": []}}.

Texto da página:
<<<
{trechos}
>>>"""


def prompt_ofertas(url, trechos):
    return PROMPT.format(url=url, trechos=trechos)


def limpar_ofertas(parsed, texto, url, hoje=None):
    """Fica só com as ofertas que a página confirma: produto com FGC, indexador conhecido, taxa que faz sentido e o trecho
    escrito na página com aquele número. Devolve (ofertas, quantas a página não confirmou)."""
    hoje = hoje or date.today()
    lista = parsed.get("ofertas") if isinstance(parsed, dict) else parsed if isinstance(parsed, list) else []
    cmp = assinaturas.para_comparar(texto)
    out, vistos, recusadas = [], set(), 0
    for o in (lista if isinstance(lista, list) else [])[:60]:
        if not isinstance(o, dict):
            continue
        prod = str(o.get("produto") or "").strip().lower()
        idx = str(o.get("indexador") or "").strip().lower()
        taxa = calc.num_br(o.get("taxa"), None)
        if prod not in PRODUTOS or idx not in FAIXA or taxa is None or not FAIXA[idx][0] <= taxa <= FAIXA[idx][1]:
            recusadas += 1
            continue
        if not assinaturas.confere(str(o.get("trecho") or ""), taxa, cmp):
            recusadas += 1
            continue
        emissor = re.sub(r"\s+", " ", str(o.get("emissor") or "")).strip()[:60]
        nome_prod = re.sub(r"\s+", " ", str(o.get("nome") or "")).strip()[:40]
        condicao = re.sub(r"\s+", " ", str(o.get("condicao") or "")).strip().rstrip(".")[:90]
        venc = calc.parse_data(o.get("vencimento"))
        venc = venc.isoformat() if venc and venc > hoje else ""
        liq = o.get("liquidez") if o.get("liquidez") in ("diaria", "vencimento") else ""
        chave = (prod, emissor.lower(), nome_prod.lower(), idx, round(taxa, 4), venc, liq, condicao.lower())
        if chave in vistos:
            continue
        vistos.add(chave)
        out.append({"id": "of:" + hashlib.sha1(repr((url,) + chave).encode()).hexdigest()[:12],
                    "nome": (f"{nome_prod} ({emissor})" if nome_prod and emissor and emissor.lower() not in nome_prod.lower() else nome_prod)
                            or f"{PRODUTOS[prod]} {emissor}".strip(), "origem": "pagina", "fonte": dominio(url), "url": url,
                    "produto": prod, "emissor": emissor, "condicao": condicao, "familia": calc.GRUPO_IDX[idx], "indexador": idx, "taxa": round(taxa, 4),
                    "isento": prod in ISENTOS, "vencimento": venc, "liquidez": liq,
                    "minimo": round(max(0.0, calc.num_br(o.get("minimo"), 0.0)), 2)})
    return out, recusadas


_SIMULADA = re.compile(r"\b(CDB|RDB|LCI|LCA|LC|Caixinha|Cofrinho)\s+(.+?)\s+(?:(\d+(?:,\d+)?)%\s+do\s+CDI|CDI\s*\+\s*(\d+(?:,\d+)?)%|"
                       r"IPCA\s*\+\s*(\d+(?:,\d+)?)%|(\d+(?:,\d+)?)%\s+ao\s+ano)", re.I)


def simuladas(texto):
    """A IA de mentira (GERENCIA_IA_MOCK, nos testes e na prévia do servidor): "CDB Banco Sol 130% do CDI",
    "LCA Banco Lua IPCA + 6,5%"… cada linha assim vira uma oferta."""
    out = []
    for linha in str(texto or "").splitlines():
        m = _SIMULADA.search(linha)
        if not m:
            continue
        idx, taxa = next((k, v) for k, v in zip(("cdi_pct", "cdi_mais", "ipca_mais", "pre"), m.groups()[2:]) if v)
        venc = re.search(r"vence em (\d{1,2}/\d{1,2}/\d{4})", linha)
        cond = re.search(r"\(([^)]{3,90})\)", linha)
        conta = m.group(1).lower() in ("caixinha", "cofrinho")
        out.append({"emissor": m.group(2).strip(), "produto": "conta" if conta else m.group(1).lower(), "indexador": idx, "taxa": calc.num_br(taxa),
                    "nome": m.group(1) if conta else "", "condicao": cond.group(1) if cond else "",
                    "vencimento": data_br(venc.group(1)) if venc else "", "liquidez": "diaria" if "diária" in linha.lower() else "",
                    "minimo": 0, "trecho": linha.strip()})
    return {"ofertas": out}


# ---------------------------------------------------------------- avaliar e avisar

def num_txt(v, casas=2):
    """15.1 -> "15,10"; 130 -> "130"; 113.94 -> "113,9" (casas=0: inteiro quando dá, senão uma casa)."""
    if casas == 0:
        return str(int(round(v))) if abs(v - round(v)) < 0.05 else f"{v:.1f}".replace(".", ",")
    return f"{v:.{casas}f}".replace(".", ",")


def taxa_txt(x):
    """Como o banco escreve: "Selic + 0,11%", "15,10% ao ano", "IPCA + 7,82%", "130% do CDI", "CDI + 1,50%"."""
    t, k = float(x.get("taxa") or 0), x.get("indexador")
    if k == "selic_mais":
        return f"Selic + {num_txt(t)}%" if t > 0.004 else "Selic"
    if k == "pre":
        return f"{num_txt(t)}% ao ano"
    if k == "ipca_mais":
        return f"IPCA + {num_txt(t)}%"
    if k == "cdi_pct":
        return f"{num_txt(t, 0)}% do CDI"
    if k == "cdi_mais":
        return f"CDI + {num_txt(t)}%"
    return ""


def valor_txt(grupo, v):
    """O valor na unidade da família: "112% do CDI", "13,20% ao ano", "IPCA + 6,10%"."""
    return {"pos": f"{num_txt(v, 0)}% do CDI", "pre": f"{num_txt(v)}% ao ano", "ipca": f"IPCA + {num_txt(v)}%"}.get(grupo, "")


def todas(cache, paginas):
    """As oportunidades de agora: os títulos do Tesouro e as ofertas das páginas que a pessoa ainda tem na lista."""
    ops = do_tesouro((cache.get("tesouro") or {}).get("titulos"))
    for url in paginas or []:
        ops += [o for o in ((cache.get("paginas") or {}).get(url) or {}).get("ofertas") or [] if isinstance(o, dict)]
    return ops


def avaliar(ops, d, hoje=None):
    """Cada oportunidade com o equivalente em CDB, se passa do que a pessoa quer e como fica perto dos investimentos
    dela; da melhor para a pior dentro de cada família."""
    ind, aj, invs = d.get("indices") or {}, d.get("ajustes") or {}, d.get("investimentos") or []
    out = []
    for x in ops:
        eq = calc.equivalente(x, ind, hoje)
        if not eq:
            continue
        out.append({**x, "eq": eq, "passa": calc.passa_alvo(x, aj, ind, hoje, invs), "meus": calc.comparar_meus(x, invs, ind, hoje)})
    ordem = list(calc.ALVO_GRUPO)
    return sorted(out, key=lambda x: (ordem.index(x["eq"]["grupo"]), -x["eq"]["valor"], x["nome"]))


def para_avisar(avaliadas, avisadas):
    """As que passam do que a pessoa quer e ainda não foram avisadas (ou subiram desde o aviso). Devolve (novas, o
    registro novo dos avisos: {id: valor avisado}); a que deixou de passar é esquecida (volta a avisar se passar de novo)."""
    passam = [x for x in avaliadas if x["passa"]]
    novas = [x for x in passam if x["id"] not in avisadas
             or x["eq"]["valor"] >= float(avisadas[x["id"]]) + SUBIU[x["eq"]["grupo"]] - 1e-9]
    ids = {x["id"] for x in novas}
    return novas, {x["id"]: (x["eq"]["valor"] if x["id"] in ids else avisadas[x["id"]]) for x in passam}


def linha_aviso(x):
    """ "Tesouro IPCA+ 2032: IPCA + 7,82%"; isento: ", como CDB de 112% do CDI"; acima de todos os seus: "(o seu
    melhor: IPCA + 6,10%)"."""
    t = f"{x['nome']}: {taxa_txt(x)}"
    if x.get("condicao"):
        t += f" ({x['condicao']})"
    if x.get("isento"):
        t += f", como CDB de {valor_txt(x['eq']['grupo'], x['eq']['valor'])}"
    m = x.get("meus")
    if m and m["abaixo"] == m["n"]:
        t += f" (o seu melhor: {valor_txt(x['eq']['grupo'], m['melhor']['valor'])})"
    return t


def agora_txt(dt=None):
    return (dt or datetime.now()).strftime("%d/%m às %H:%M")
