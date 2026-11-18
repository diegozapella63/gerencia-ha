"""Benefícios lidos pela IA (Mais › Benefícios › Ler com IA): de um print, uma foto, um PDF, um texto colado ou a página
oficial do plano ou do cartão.

1. A IA do Home Assistant lista os benefícios (nome, quantidade ou valor, se renova, a condição e o trecho de onde tirou).
2. Do texto colado e da página, cada benefício só vale se o trecho citado estiver escrito lá; com quantidade ou valor, o
   número precisa estar no trecho (senão vira vantagem, sem o número). Do print e da foto não há texto para conferir.
3. A tela mostra a lista para conferir e cadastra os escolhidos. A conta do período fica no calc.py (ciclo_beneficio).
4. Na mesma leitura, as oportunidades: o que a pessoa ganha a mais cumprindo uma condição escrita ali (ter um valor
   investido, gastar um valor no cartão por mês, um plano mais caro). Conferidas do mesmo jeito: o trecho escrito lá e o
   valor no trecho. Quanto falta fica no calc.py (progresso_meta).
Só biblioteca padrão do Python.
"""
import re
from datetime import date

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
                    if c.get("debito_global"):
                        partes.append(f"cartão de débito global em {c['debito_global']}")
                    if c.get("credito_global"):
                        partes.append(f"cartão de crédito global em {c['credito_global']}")
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
- "descricao": o que é e para que serve, para quem nunca ouviu falar, em uma ou duas frases curtas (até 160 caracteres; ex.: "Clube de restaurantes: dois pratos pelo preço de um nos parceiros"); aqui pode usar o que você sabe.
- "site": o endereço oficial do benefício (https://…), se houver um conhecido; "" se não souber.
Liste também, em "oportunidades", o que a pessoa ganha a mais cumprindo uma condição escrita ali, com o valor da condição:
- "tipo": "investido" se for ter um valor investido ou aplicado (ex.: anuidade grátis com R$ 50 mil investidos; o nível Black a partir de R$ 100 mil); "gasto" se for gastar um valor no cartão (ex.: sala VIP gastando R$ 3 mil por mês); "plano" se for um plano mais caro, com o preço dele (ex.: o plano de 2 TB por R$ 34,99 por mês).
- "valor": o valor da condição ou o preço do plano, em reais, como número (50000; 3000; 34.99).
- "periodo": "mes" ou "ano", como estiver escrito (no gasto e no plano); "" no investido.
- "ganha": o que a pessoa ganha, curto, até 40 caracteres (ex.: "Sem anuidade", "Sala VIP", "Nível Black", "2 TB e mais 4 pessoas").
- "plano": o nome do plano mais caro, só no tipo "plano"; "" no resto.
- "trecho": o pedaço do texto onde aparece a condição com o valor, copiado exatamente como está (até 100 caracteres).
Use só o que estiver escrito{onde}. Não use o que você sabe de memória (só na "descricao" e no "site"). Ignore preços, tarifas, taxas de juros e propaganda sem benefício concreto.{qual} No máximo 20 benefícios e 10 oportunidades.{prox}
Responda somente com JSON válido, sem markdown e sem texto antes ou depois, neste formato:
{{"beneficios":[{{"nome":"","tipo":"vantagem","total":0,"moeda":"","renova":"nunca","condicao":"","trecho":"","descricao":"","site":""}}],"oportunidades":[{{"tipo":"investido","valor":0,"periodo":"","ganha":"","plano":"","trecho":""}}]{prox_fmt}}}{texto}"""


# 1.74.0: só com o banco e o nível (Identificar benefícios sem print, texto nem página): o que a IA sabe dele, para conferir
ABRE = "Você lê {fonte}{de} e lista os benefícios que a pessoa ganha:"
REGRA = "Use só o que estiver escrito{onde}. Não use o que você sabe de memória (só na \"descricao\" e no \"site\")."
# 1.76.1: pesquisando na internet, no site oficial de hoje (a IA Para pesquisar na internet): de memória, a IA trazia nomes
# e valores velhos, como um nível que o banco já trocou de nome e de valor
PROMPT_MEMORIA = PROMPT.replace(ABRE, "Pesquise na internet, no site oficial do banco ou da empresa, os benefícios que a pessoa ganha com {de}:").replace(
    REGRA, "Hoje é {hoje}. Use o que o site oficial de {de} diz hoje, para o nível e o cartão dela: os bancos trocam os nomes dos"
    " níveis, os valores e os benefícios, então não use o que você lembra de antes. Sem achar no site, use o que outras páginas"
    " recentes dizem; sem certeza de um número, use \"vantagem\" com total 0; se não souber, devolva as listas vazias. Em"
    " \"trecho\", escreva \"\".").replace("o nível Black a partir de R$ 100 mil", "o nível de cima a partir de R$ 100 mil").replace(
    "\"Nível Black\", ", "")


# 1.74.2: numa conta de banco, o nível de conta logo acima do dela e quanto ele pede investido (vai para Próximo nível e
# Pede investido, em Editar banco; não entra nas oportunidades, que já mostram o próximo nível da conta)
PROX = ("\nEm \"proximo_nivel\", o nível de conta logo acima do da pessoa nesse banco, com o nome que o banco usa hoje: \"nivel\" (o nome), \"valor\""
        " (quanto ele pede investido, em reais, como número) e \"trecho\" (como acima); {{\"nivel\":\"\",\"valor\":0,\"trecho\":\"\"}} se não"
        " houver. Esse nível não entra em \"oportunidades\", nem o que vale para o nível que ela já tem (o que ele pede para"
        " continuar nele não é oportunidade).")
PROX_FMT = ',"proximo_nivel":{{"nivel":"","valor":0,"trecho":""}}'


def prompt(origem="", url="", texto="", anexo=False, preco=0, memoria=False, conta=False, hoje=""):
    prox = {"prox": PROX.replace("{{", "{").replace("}}", "}") if conta else "", "prox_fmt": PROX_FMT.replace("{{", "{").replace("}}", "}") if conta else ""}
    if memoria:
        qual = (" Os benefícios são só os do nível e do cartão dela; os de um nível acima entram em \"oportunidades\", com o valor que"
                " ele pede" + (", menos o logo acima, que vai em \"proximo_nivel\"." if conta else "."))
        return PROMPT_MEMORIA.format(de=origem, qual=qual, texto="", hoje=hoje or date.today().strftime("%d/%m/%Y"), **prox)
    if url:
        fonte, onde = f"a página {url}", " na página"
    elif anexo:
        fonte, onde = "a imagem ou o PDF anexado" + (" e o texto abaixo" if texto else ""), " ali"
    else:
        fonte, onde = "o texto abaixo", " no texto"
    # os benefícios são só os do plano ou do cartão da pessoa; os planos mais caros entram nas oportunidades
    qual = (f" Se houver vários planos, níveis ou cartões, os benefícios são só os de {origem}; os outros, mais caros, entram em"
            f" \"oportunidades\"." if origem else "")
    if preco > 0:
        qual += f" A pessoa paga hoje {calc.fmt_brl(preco)} por mês: num \"plano\", só os que custam mais que isso."
    corpo = f"\n\n{'Trechos da página' if url else 'Texto'}:\n<<<\n{texto}\n>>>" if texto else ""
    return PROMPT.format(fonte=fonte, de=f" (de: {origem})" if origem else "", onde=onde, qual=qual, texto=corpo, **prox)


def tem_numero(trecho, valor):
    """O número (em algarismos ou por extenso, até doze) está escrito no trecho?"""
    if any(abs(n - valor) < 0.006 for n in assinaturas.numeros(trecho)):
        return True
    return any(EXTENSO.get(w) == valor for w in assinaturas.normal(trecho).split())


def tem_valor(trecho, valor):
    """O valor está no trecho, em algarismos ou com "mil" ("R$ 50 mil" é 50000)?"""
    if tem_numero(trecho, valor):
        return True
    for m in re.finditer(r"(\d[\d.,]*)\s*mil\b", str(trecho or ""), re.I):
        if any(abs(n * 1000 - valor) < 0.6 for n in assinaturas.numeros(m.group(1))):
            return True
    return False


TIPOS_META = ("investido", "gasto", "plano")
MAX_METAS = 10


def limpar_metas(parsed, texto=None):
    """As oportunidades que a IA devolveu, limpas: com texto, só as que estão escritas lá, com o valor no trecho (a IA
    não inventa o número). Devolve (oportunidades, recusadas)."""
    lista = parsed.get("oportunidades") if isinstance(parsed, dict) else None
    cmp = assinaturas.para_comparar(texto) if texto else None
    saida, recusadas, vistos = [], 0, set()
    for o in (lista if isinstance(lista, list) else [])[:30]:
        if not isinstance(o, dict) or o.get("tipo") not in TIPOS_META:
            continue
        ganha = re.sub(r"\s+", " ", str(o.get("ganha") or "")).strip()[:60]
        valor = round(calc.num_br(o.get("valor")), 2)
        trecho = re.sub(r"\s+", " ", str(o.get("trecho") or "")).strip()[:160]
        if not ganha or valor <= 0:
            continue
        if cmp is not None:
            tc = assinaturas.para_comparar(trecho)
            if len(tc) < 3 or tc not in cmp:
                recusadas += 1
                continue
        if trecho and not tem_valor(trecho, valor):
            recusadas += 1
            continue
        chave = (o["tipo"], valor, assinaturas.normal(ganha))
        if chave in vistos:
            continue
        vistos.add(chave)
        item = {"tipo": o["tipo"], "valor": valor, "ganha": ganha, "trecho": trecho}
        if o["tipo"] != "investido":
            item["periodo"] = "ano" if o.get("periodo") == "ano" else "mes"
        plano = re.sub(r"\s+", " ", str(o.get("plano") or "")).strip()[:40]
        if o["tipo"] == "plano" and plano:
            item["plano"] = plano
        saida.append(item)
        if len(saida) >= MAX_METAS:
            break
    return saida, recusadas


def niveis_da_conta(d, origem, so_conta=False):
    """Os níveis que a pessoa já tem na conta (o da conta e o do cartão; so_conta: só o da conta), para não virarem
    oportunidade nem próximo nível (1.74.3)."""
    o = str(origem or "")
    if not o.startswith("conta:"):
        return []
    for bc in d.get("bancos") or []:
        for c in (bc.get("contas") or []) if isinstance(bc, dict) else []:
            if isinstance(c, dict) and c.get("id") == o[6:]:
                return [str(c[k]).strip() for k in (("nivel",) if so_conta else ("nivel", "cartao_nivel")) if str(c.get(k) or "").strip()]
    return []


def do_nivel_atual(ganha, niveis):
    """A oportunidade é só o nível que a pessoa já tem ("Inter Prime" sendo Prime)?"""
    g = f" {assinaturas.normal(ganha)} "
    return any(f" {assinaturas.normal(n)} " in g for n in niveis if assinaturas.normal(n))


SITE_RE = re.compile(r"https://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/\S*)?")


def sobre(b):
    """O que é o benefício e o site oficial (1.75.0), limpos: {descricao?, url?}."""
    out = {}
    d = re.sub(r"\s+", " ", str((b or {}).get("descricao") or "")).strip()[:200] if isinstance(b, dict) else ""
    if d:
        out["descricao"] = d
    u = str((b or {}).get("site") or (b or {}).get("url") or "").strip() if isinstance(b, dict) else ""
    if SITE_RE.fullmatch(u) and len(u) <= 300:
        out["url"] = u
    return out


# 1.76.1: pesquisando na internet, como está hoje (a IA Para pesquisar na internet), e não de memória
PROMPT_EXPLICAR = """Pesquise na internet e explique, para quem nunca ouviu falar, o benefício "{nome}"{de}, como ele é hoje ({hoje}): o que é e para que serve, em uma ou duas frases curtas (até 200 caracteres), e o endereço oficial dele (https://…), de preferência a página do próprio banco ou da empresa.
Use o que os sites oficiais dizem hoje, não o que você lembra de antes. Não invente: sem achar o que é, devolva "descricao" vazia; sem achar o site, "site" vazio.
Responda somente com JSON válido, sem markdown e sem texto antes ou depois, neste formato:
{{"descricao":"","site":""}}"""


def prompt_explicar(nome, origem="", hoje=""):
    return PROMPT_EXPLICAR.format(nome=str(nome or "").strip()[:60], de=f" (de {origem})" if origem else "",
                                  hoje=hoje or date.today().strftime("%d/%m/%Y"))


def explicado_simulado(nome):
    """A IA simulada (testes e prévia): um texto inventado, sem site."""
    return {"descricao": f"{str(nome).strip()}: benefício de exemplo, explicado pela IA simulada.", "site": ""}


def limpar_proximo(parsed, texto=None):
    """O próximo nível da conta que a IA devolveu (1.74.2): {nivel, valor, trecho} ou None. Com texto, só se estiver escrito
    lá, com o valor no trecho (como as oportunidades)."""
    p = parsed.get("proximo_nivel") if isinstance(parsed, dict) else None
    if not isinstance(p, dict):
        return None
    nivel = re.sub(r"\s+", " ", str(p.get("nivel") or "")).strip()[:30]
    valor = round(calc.num_br(p.get("valor")), 2)
    trecho = re.sub(r"\s+", " ", str(p.get("trecho") or "")).strip()[:160]
    if not nivel or valor <= 0:
        return None
    if texto:
        tc = assinaturas.para_comparar(trecho)
        if len(tc) < 3 or tc not in assinaturas.para_comparar(texto) or not tem_valor(trecho, valor):
            return None
    elif trecho and not tem_valor(trecho, valor):
        return None
    return {"nivel": nivel, "valor": valor, "trecho": trecho}


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
        item.update(sobre(b))
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

# o que a IA simulada "sabe" de um banco (só o nome e o nível, sem fonte): um exemplo inventado
EXEMPLO_MEMORIA = "Cashback de 1% nas compras no cartão\n2 acessos à sala VIP por ano\nSeguro viagem internacional\nPróximo nível: Ouro, a partir de R$ 250 mil investidos"

EXEMPLO_ANEXO = ("6 acessos à sala VIP por ano, com 1 acompanhante\nUS$ 100 em créditos de uso por mês\nSeguro viagem internacional\n"
                 "Anuidade grátis com R$ 50 mil investidos")


def simulados(texto):
    """O que a IA simulada acha: uma linha por benefício (sala VIP, créditos em R$ ou US$, seguro, cashback, frete)."""
    saida, metas, prox = [], [], None
    for ln in re.split(r"[\n;•]+", str(texto or "")):
        ln = ln.strip()
        n = assinaturas.normal(ln)
        din = re.search(r"R\$\s?([\d.,]+)(\s*mil\b)?", ln)
        # o próximo nível da conta: "Próximo nível: Ouro, a partir de R$ 250 mil investidos"
        pn = re.match(r"(?i)pr[oó]ximo n[ií]vel:\s*([^,]+)", ln)
        if pn and din:
            prox = {"nivel": pn.group(1).strip(), "valor": calc.num_br(din.group(1)) * (1000 if din.group(2) else 1), "trecho": ln[:100]}
            continue
        # a condição para ganhar mais: investindo, gastando no cartão ou um plano mais caro ("Plano X por R$ 120 por mês")
        if din and re.search(r"\binvestid|\baplicad|\bgastando\b|\bgastar\b|^plano\b", n):
            v = calc.num_br(din.group(1)) * (1000 if din.group(2) else 1)
            tipo = "investido" if re.search(r"\binvestid|\baplicad", n) else "gasto" if re.search(r"\bgast", n) else "plano"
            ganha = ("Sem anuidade" if "anuidade" in n else "Sala VIP" if "sala vip" in n else
                     re.sub(r"(?i)\s*(por|com|gastando|gastar|a partir de)\s+R\$.*$", "", ln).strip() or "Benefício")
            metas.append({"tipo": tipo, "valor": v, "periodo": "ano" if re.search(r"\bpor ano\b|\bao ano\b", n) else "mes" if tipo != "investido" else "",
                          "ganha": ganha[:40], "plano": re.sub(r"(?i)\s+por\s+R\$.*$", "", ln).strip() if tipo == "plano" else "", "trecho": ln[:100]})
            continue
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
    r = {"beneficios": saida, "oportunidades": metas}
    if prox:
        r["proximo_nivel"] = prox
    return r
