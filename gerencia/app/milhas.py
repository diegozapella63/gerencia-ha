"""Milhas lidas pela IA (Mais › Benefícios › um benefício do tipo Milhas › Ler com IA), 1.63.0: de um print ou uma foto da
conta do programa (o saldo, o nível, as qualificáveis e as que vencem), de um texto colado ou da página oficial (os
benefícios do nível, o que o próximo nível pede, como trocar e a tabela de resgate).

Da página e do texto, cada coisa só vale se o trecho citado estiver escrito lá, com o número no trecho (a IA não inventa
a tabela); do print e da foto não há texto para conferir. A conta (o saldo de hoje, quanto falta para o próximo nível, o
que dá para trocar) fica no calc.py (milhas_de). Só biblioteca padrão do Python.
"""
import re

import assinaturas
import beneficios
import calc

MAX_VANTAGENS = 15
MAX_RESGATES = 15
MAX_COMO = 5
MAX_LOTES = 6

PROMPT = """Você lê {fonte} sobre um programa de milhas ou pontos{de}. Responda só com um JSON assim:
{{"programa": "nome do programa", "saldo": 12300, "nivel": "nível de agora", "qualificaveis": 3200,
 "proximo": {{"nivel": "o nível acima", "pede": 25000, "unidade": "milhas", "trecho": "..."}},
 "vencem": [{{"qtd": 2000, "data": "AAAA-MM-DD"}}],
 "vantagens": [{{"nome": "Bagagem extra", "trecho": "..."}}],
 "resgates": [{{"nome": "Cidade A – Cidade B, econômica, só ida", "milhas": 12500, "trecho": "..."}}],
 "como": [{{"texto": "como trocar, numa frase curta", "trecho": "..."}}]}}
Regras:
- saldo, nivel, qualificaveis (as milhas ou os trechos que contam para subir de nível) e vencem (as milhas que vencem e quando): da tela ou do extrato da conta. Numa página de regras, deixe 0, "" e [].
- vantagens: os benefícios do nível {nivel} (até {max_v}).
- proximo: o nível logo acima de {nivel} e quanto ele pede ("unidade": "milhas" ou "trechos"); sem isso escrito{onde}, deixe {{}}.
- resgates: o que dá para trocar e por quantas milhas, como está na tabela (o trecho ou o produto, a classe, ida ou ida e volta), do mais barato para o mais caro (até {max_r}).
- como: como trocar as milhas, em frases curtas (até {max_c}).
- "trecho": copie exatamente o pedaço{onde} de onde tirou, com o número. Não invente nada que não esteja{onde}.{texto}"""


def prompt(programa="", nivel="", url="", texto="", anexo=False):
    if url:
        fonte, onde = f"a página {url}", " na página"
    elif anexo:
        fonte, onde = "a imagem ou o PDF anexado" + (" e o texto abaixo" if texto else ""), " ali"
    else:
        fonte, onde = "o texto abaixo", " no texto"
    corpo = f"\n\n{'Trechos da página' if url else 'Texto'}:\n<<<\n{texto}\n>>>" if texto else ""
    return PROMPT.format(fonte=fonte, de=f" ({programa})" if programa else "", nivel=f'"{nivel}"' if nivel else "de agora (ou o básico)",
                         onde=onde, texto=corpo, max_v=MAX_VANTAGENS, max_r=MAX_RESGATES, max_c=MAX_COMO)


# as partes da página que falam de milhas (para mandar pouco texto à IA)
_CHAVE = re.compile(r"milha|ponto|miles|points|n[ií]vel|categoria|status|elite|qualific|trecho|resgat|troc|emiss|"
                    r"passag|upgrade|bagagem|sala vip|lounge|prioridade|vencim|expira|validade|tier|award|redeem", re.I)


def trechos(texto, limite=14000):
    t = assinaturas.trechos_preco(texto, limite=limite, margem=300, padrao=_CHAVE)
    return t or str(texto or "")[:limite]


def _linha(v, n=80):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def limpar(parsed, texto=None):
    """O que a IA devolveu, limpo. Com texto (a página ou o que foi colado), só fica o que está escrito lá, com o número
    no trecho (ou no texto, para o saldo e o que vence). Devolve (dados, recusados)."""
    p = parsed if isinstance(parsed, dict) else {}
    cmp = assinaturas.para_comparar(texto) if texto else None
    recusados = 0

    def escrito(trecho):
        if cmp is None:
            return True
        tc = assinaturas.para_comparar(trecho)
        return len(tc) >= 3 and tc in cmp

    out = {}
    programa = _linha(p.get("programa"), 40)
    if programa:
        out["programa"] = programa
    for k in ("saldo", "qualificaveis"):
        v = round(calc.num_br(p.get(k)))
        if v > 0:
            if texto and not beneficios.tem_valor(texto, v):
                recusados += 1
            else:
                out[k] = v
    nivel = _linha(p.get("nivel"), 30)
    if nivel and (cmp is None or assinaturas.para_comparar(nivel) in cmp):
        out["nivel"] = nivel
    lotes = []
    for v in (p.get("vencem") if isinstance(p.get("vencem"), list) else [])[:20]:
        if not isinstance(v, dict):
            continue
        q, d = round(calc.num_br(v.get("qtd"))), calc.parse_data(str(v.get("data") or "")[:10])
        if q <= 0 or not d:
            continue
        if texto and not beneficios.tem_valor(texto, q):
            recusados += 1
            continue
        lotes.append({"qtd": q, "data": d.isoformat()})
    if lotes:
        out["vencem"] = sorted(lotes, key=lambda x: x["data"])[:MAX_LOTES]
    pr = p.get("proximo") if isinstance(p.get("proximo"), dict) else {}
    pn, pede, pt = _linha(pr.get("nivel"), 30), round(calc.num_br(pr.get("pede"))), _linha(pr.get("trecho"), 160)
    if pn and pede > 0:
        if escrito(pt) and (not pt or beneficios.tem_valor(pt, pede)):
            out["proximo"] = {"nivel": pn, "pede": pede, "unidade": "trechos" if pr.get("unidade") == "trechos" else "milhas"}
            if pt:
                out["proximo"]["trecho"] = pt
        else:
            recusados += 1
    vant, vistos = [], set()
    for v in (p.get("vantagens") if isinstance(p.get("vantagens"), list) else [])[:40]:
        nome = _linha(v.get("nome") if isinstance(v, dict) else v, 60)
        trecho = _linha(v.get("trecho"), 160) if isinstance(v, dict) else ""
        if not nome or assinaturas.normal(nome) in vistos:
            continue
        if not escrito(trecho):
            recusados += 1
            continue
        vistos.add(assinaturas.normal(nome))
        vant.append(dict({"nome": nome}, **({"trecho": trecho} if trecho else {})))
    if vant:
        out["vantagens"] = vant[:MAX_VANTAGENS]
    res, vistos = [], set()
    for r in (p.get("resgates") if isinstance(p.get("resgates"), list) else [])[:40]:
        if not isinstance(r, dict):
            continue
        nome, mil, trecho = _linha(r.get("nome"), 70), round(calc.num_br(r.get("milhas"))), _linha(r.get("trecho"), 160)
        if not nome or mil <= 0 or (assinaturas.normal(nome), mil) in vistos:
            continue
        if not escrito(trecho) or (trecho and not beneficios.tem_valor(trecho, mil)):
            recusados += 1
            continue
        vistos.add((assinaturas.normal(nome), mil))
        res.append(dict({"nome": nome, "milhas": mil}, **({"trecho": trecho} if trecho else {})))
    if res:
        out["resgates"] = sorted(res, key=lambda x: x["milhas"])[:MAX_RESGATES]
    como = []
    for c in (p.get("como") if isinstance(p.get("como"), list) else [])[:10]:
        t = _linha(c.get("texto") if isinstance(c, dict) else c, 120)
        trecho = _linha(c.get("trecho"), 160) if isinstance(c, dict) else ""
        if not t:
            continue
        if not escrito(trecho):
            recusados += 1
            continue
        como.append(t)
    if como:
        out["como"] = como[:MAX_COMO]
    return out, recusados


# ---------------------------------------------------------------- a IA simulada (testes e desenvolvimento)

EXEMPLO_ANEXO = ("Programa Voa Mais\nSaldo: 12.300 milhas\nNível: Prata\nMilhas qualificáveis: 3.200\n"
                 "2.000 milhas vencem em 30/06/2027")


def simulados(texto):
    """O que a IA simulada acha, uma coisa por linha: o saldo, o nível, as qualificáveis, o que vence, o próximo nível
    ("Ouro: 25.000 milhas qualificáveis"), os resgates ("Cidade A – Cidade B: 12.500 milhas"), as vantagens e o como."""
    out = {"vantagens": [], "resgates": [], "como": [], "vencem": []}
    for ln in re.split(r"[\n;•]+", str(texto or "")):
        ln = ln.strip()
        n = assinaturas.normal(ln)
        num = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)", ln)
        v = calc.num_br(num.group(1).replace(".", "")) if num else 0
        if not n:
            continue
        if n.startswith("programa "):
            out["programa"] = ln.split(" ", 1)[1].strip()
        elif n.startswith("saldo") and v:
            out["saldo"] = v
        elif n.startswith("nivel"):
            out["nivel"] = ln.split(":", 1)[-1].strip()
        elif "qualificav" in n and ":" in ln and n.startswith("milhas qualificav") and v:
            out["qualificaveis"] = v
        elif "vencem" in n and v:
            d = re.search(r"(\d{2})/(\d{2})/(\d{4})", ln)
            if d:
                out["vencem"].append({"qtd": v, "data": f"{d.group(3)}-{d.group(2)}-{d.group(1)}"})
        elif "qualificav" in n and ":" in ln and v:
            out["proximo"] = {"nivel": ln.split(":", 1)[0].strip(), "pede": v, "unidade": "trechos" if "trecho" in n else "milhas", "trecho": ln[:120]}
        elif re.search(r"\bmilhas\b", n) and ":" in ln and v:
            out["resgates"].append({"nome": ln.split(":", 1)[0].strip(), "milhas": v, "trecho": ln[:120]})
        elif n.startswith(("resgate", "troque", "para trocar")):
            out["como"].append({"texto": ln, "trecho": ln[:120]})
        elif re.search(r"bagagem|prioridade|sala vip|upgrade|assento|embarque", n):
            out["vantagens"].append({"nome": ln[:60], "trecho": ln[:120]})
    return out
