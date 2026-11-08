"""Benefícios lidos pela IA (Mais › Benefícios › Ler com IA): de um print, uma foto, um PDF, um texto colado ou a página
oficial do plano ou do cartão.

1. A IA do Home Assistant lista os benefícios (nome, quantidade ou valor, se renova, a condição e o trecho de onde tirou).
2. Do texto colado e da página, cada benefício só vale se o trecho citado estiver escrito lá; com quantidade ou valor, o
   número precisa estar no trecho (senão vira vantagem, sem o número). Do print e da foto não há texto para conferir.
3. A tela mostra a lista para conferir e cadastra os escolhidos. A conta do período fica no calc.py (ciclo_beneficio).
Só biblioteca padrão do Python.
"""
import re

import assinaturas
import calc

TIPOS = ("contagem", "saldo", "vantagem")
RENOVA = ("mes", "ano", "nunca")
MOEDAS = ("BRL", "USD")
MAX = 20

# as partes da página que falam de benefício (para mandar pouco texto à IA)
_CHAVE = re.compile(r"sala vip|lounge|priority pass|acesso|cashback|seguro|milha|pontos|cr[eé]dito|anuidade|frete|desconto|"
                    r"benef[ií]cio|vantage|gr[aá]tis|gratuit|assist[eê]ncia|concierge|inclu[ií]|incluso|US\$|R\$|"
                    r"por m[eê]s|por ano|credit|perk|benefit|lounge|insurance|included", re.I)
EXTENSO = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8,
           "nove": 9, "dez": 10, "onze": 11, "doze": 12, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
           "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12}


def trechos(texto, limite=14000):
    t = assinaturas.trechos_preco(texto, limite=limite, margem=300, padrao=_CHAVE)
    return t or str(texto or "")[:limite]


def nome_origem(d, origem):
    """De onde vem o benefício, em palavras, para a IA saber qual plano ou cartão olhar na página."""
    o = str(origem or "")
    if o.startswith("fixo:"):
        r = next((x for x in d.get("recorrencias") or [] if isinstance(x, dict) and x.get("id") == o[5:]), None)
        return str(r.get("descricao") or "").strip() if r else ""
    if o.startswith("conta:"):
        for bc in d.get("bancos") or []:
            for c in (bc.get("contas") or []) if isinstance(bc, dict) else []:
                if isinstance(c, dict) and c.get("id") == o[6:]:
                    partes = [str(bc.get("nome") or "banco").strip()]
                    if c.get("nivel"):
                        partes.append("nível " + str(c["nivel"]).strip())
                    if c.get("cartao"):
                        partes.append(("cartão " + str(c.get("cartao_nivel") or "").strip()).strip())
                    return ", ".join(partes)
    return ""


PROMPT = """Você lê {fonte}{de} e lista os benefícios que a pessoa ganha: salas VIP, créditos de uso, cashback, seguros, milhas, frete grátis, descontos e serviços incluídos.
Para cada benefício, devolva:
- "nome": curto e claro, até 40 caracteres (ex.: "Sala VIP", "Créditos de API", "Seguro viagem", "Cashback").
- "tipo": "contagem" se for uma quantidade de usos (ex.: 6 acessos à sala VIP por ano); "saldo" se for um valor em dinheiro para gastar (ex.: US$ 100 de créditos por mês); "vantagem" para o resto (seguro, cashback em %, desconto, frete grátis, acesso ilimitado).
- "total": a quantidade ou o valor, como número (6; 100); 0 numa vantagem.
- "moeda": "BRL" ou "USD" no saldo; "" no resto.
- "renova": "mes" se renova todo mês, "ano" se renova todo ano, "nunca" se não renova ou não diz.
- "condicao": a condição, curta (ex.: "com 1 acompanhante", "gastando R$ 5 mil por mês"); "" se não houver.
- "trecho": o pedaço do texto onde aparece o benefício, copiado exatamente como está (até 100 caracteres).
Use só o que estiver escrito{onde}. Não use o que você sabe de memória. Ignore preços, tarifas, taxas de juros e propaganda sem benefício concreto.{qual} No máximo 20 benefícios.
Responda somente com JSON válido, sem markdown e sem texto antes ou depois, neste formato:
{{"beneficios":[{{"nome":"","tipo":"vantagem","total":0,"moeda":"","renova":"nunca","condicao":"","trecho":""}}]}}{texto}"""


def prompt(origem="", url="", texto="", anexo=False):
    if url:
        fonte, onde = f"a página {url}", " na página"
    elif anexo:
        fonte, onde = "a imagem ou o PDF anexado" + (" e o texto abaixo" if texto else ""), " ali"
    else:
        fonte, onde = "o texto abaixo", " no texto"
    qual = f" Se houver vários planos, níveis ou cartões, fique só com os de {origem}." if origem else ""
    corpo = f"\n\n{'Trechos da página' if url else 'Texto'}:\n<<<\n{texto}\n>>>" if texto else ""
    return PROMPT.format(fonte=fonte, de=f" (de: {origem})" if origem else "", onde=onde, qual=qual, texto=corpo)


def tem_numero(trecho, valor):
    """O número (em algarismos ou por extenso, até doze) está escrito no trecho?"""
    if any(abs(n - valor) < 0.006 for n in assinaturas.numeros(trecho)):
        return True
    return any(EXTENSO.get(w) == valor for w in assinaturas.normal(trecho).split())


def _moeda(m, trecho):
    m = str(m or "").upper()
    if m in MOEDAS:
        return m
    if "R$" in trecho:
        return "BRL"
    return "USD" if re.search(r"US\$|USD|d[oó]lar|\$", trecho, re.I) else "BRL"


def limpar(parsed, texto=None):
    """Os benefícios que a IA devolveu, limpos. Com texto (a página ou o que foi colado), só fica o que está escrito lá.
    Devolve (beneficios, recusados)."""
    lista = parsed.get("beneficios") if isinstance(parsed, dict) else parsed
    cmp = assinaturas.para_comparar(texto) if texto else None
    saida, recusados, vistos = [], 0, set()
    for b in (lista if isinstance(lista, list) else [])[:40]:
        if not isinstance(b, dict):
            continue
        nome = re.sub(r"\s+", " ", str(b.get("nome") or "")).strip()[:60]
        if not nome:
            continue
        trecho = re.sub(r"\s+", " ", str(b.get("trecho") or "")).strip()[:160]
        if cmp is not None:
            tc = assinaturas.para_comparar(trecho)
            if len(tc) < 3 or tc not in cmp:
                recusados += 1
                continue
        tipo = b.get("tipo") if b.get("tipo") in TIPOS else "vantagem"
        total = round(calc.num_br(b.get("total")), 2) if tipo != "vantagem" else 0
        # a quantidade ou o valor precisa estar no trecho (a IA não inventa o número)
        if tipo != "vantagem" and (total <= 0 or (trecho and not tem_numero(trecho, total))):
            tipo, total = "vantagem", 0
        renova = b.get("renova") if b.get("renova") in RENOVA and tipo != "vantagem" else "nunca"
        obs = re.sub(r"\s+", " ", str(b.get("condicao") or b.get("obs") or "")).strip()[:80]
        chave = (assinaturas.normal(nome), tipo, total)
        if chave in vistos:
            continue
        vistos.add(chave)
        item = {"nome": nome, "tipo": tipo, "renova": renova, "trecho": trecho}
        if tipo != "vantagem":
            item["total"] = total
        if tipo == "saldo":
            item["moeda"] = _moeda(b.get("moeda"), trecho)
        if obs:
            item["obs"] = obs
        saida.append(item)
        if len(saida) >= MAX:
            break
    return saida, recusados


# ---------------------------------------------------------------- a IA simulada (testes e desenvolvimento)

EXEMPLO_ANEXO = "6 acessos à sala VIP por ano, com 1 acompanhante\nUS$ 100 em créditos de uso por mês\nSeguro viagem internacional"


def simulados(texto):
    """O que a IA simulada acha: uma linha por benefício (sala VIP, créditos em R$ ou US$, seguro, cashback, frete)."""
    saida = []
    for ln in re.split(r"[\n;•]+", str(texto or "")):
        ln = ln.strip()
        n = assinaturas.normal(ln)
        if not n or re.search(r"\b(anuidade|tarifa|mensalidade|preco)\b", n):  # preço não é benefício
            continue
        renova = "ano" if re.search(r"\bpor ano\b|\bao ano\b|\banua", n) else "mes" if re.search(r"\bpor mes\b|\bao mes\b|\bmensa", n) else "nunca"
        cond = re.search(r"com \d+ acompanhantes?", ln)
        b = {"trecho": ln[:100], "renova": renova, "condicao": cond.group(0) if cond else "", "moeda": "", "total": 0}
        qtd = re.search(r"\b(\d+)\s+(acessos?|entradas?|usos?|visitas?)\b", n)
        din = re.search(r"(US\$|R\$)\s?([\d.,]+)", ln)
        if "sala vip" in n or "lounge" in n:
            b.update(nome="Sala VIP", tipo="contagem" if qtd else "vantagem", total=int(qtd.group(1)) if qtd else 0)
        elif din:
            b.update(nome="Créditos de uso" if "credito" in n else "Saldo", tipo="saldo", total=calc.num_br(din.group(2)),
                     moeda="USD" if din.group(1) == "US$" else "BRL")
        elif "seguro" in n:
            b.update(nome="Seguro viagem" if "viagem" in n else "Seguro", tipo="vantagem", renova="nunca")
        elif "cashback" in n:
            b.update(nome="Cashback", tipo="vantagem", renova="nunca")
        elif "frete" in n:
            b.update(nome="Frete grátis", tipo="vantagem", renova="nunca")
        else:
            continue
        saida.append(b)
    return {"beneficios": saida}
