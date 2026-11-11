"""Assinaturas em promoção (Mais › Benefícios › Oportunidades), 1.64.0.

1. O catálogo: as assinaturas de vídeo, música e jogos usadas na TV, no celular e no videogame, cada uma com a página
   oficial e onde ela funciona.
2. Os aparelhos da casa vêm do InventarIA (TV Samsung, Xbox, celular Android...): ficam as assinaturas que funcionam
   em algum deles (sem o InventarIA, todas). Todo celular roda o que tem app no Android e no iPhone.
3. Uma vez por dia o app abre a página oficial e, só quando os preços dela mudaram, a IA do Home Assistant lista os
   planos e as promoções. Cada preço só vale se o trecho citado estiver escrito na página, com aquele número (como as
   dicas de economia, em assinaturas.py), e uma promoção só vale se for por tempo limitado (escrito perto do preço) e,
   quando o app sabe o preço de sempre, mais barata que ele.
Só biblioteca padrão do Python.
"""
import hashlib
import json
import re
from datetime import date

import assinaturas
import calc

TVS = ("tv_samsung", "tv_lg", "android_tv", "fire_tv", "roku", "apple_tv")
CELULAR = ("android", "ios")
TUDO = TVS + CELULAR + ("xbox", "playstation")

NOMES_APARELHO = {"tv_samsung": "TV Samsung", "tv_lg": "TV LG", "android_tv": "Google TV", "fire_tv": "Fire TV", "roku": "Roku",
                  "apple_tv": "Apple TV", "android": "Android", "ios": "iPhone", "xbox": "Xbox", "playstation": "PlayStation",
                  "switch": "Nintendo Switch"}
TIPOS = {"video": "Vídeo", "musica": "Música", "jogos": "Jogos"}

CATALOGO = [
    # vídeo
    {"id": "netflix", "nome": "Netflix", "tipo": "video", "url": "https://www.netflix.com/br/", "onde": TUDO, "padrao": r"\bnetflix\b"},
    {"id": "prime_video", "nome": "Prime Video", "tipo": "video", "url": "https://www.amazon.com.br/amazonprime", "onde": TUDO,
     "padrao": r"\bprime ?video\b|\bamazon prime\b|\bprime amazon\b"},
    {"id": "disney", "nome": "Disney+", "tipo": "video", "url": "https://www.disneyplus.com/pt-br", "onde": TUDO, "padrao": r"\bdisney\b"},
    {"id": "hbo_max", "nome": "HBO Max", "tipo": "video", "url": "https://www.hbomax.com/br/pt", "onde": TUDO, "padrao": r"\bhbo\b|^max$"},
    {"id": "globoplay", "nome": "Globoplay", "tipo": "video", "url": "https://globoplay.globo.com/assine/", "onde": TVS + CELULAR + ("xbox",),
     "padrao": r"\bglobo ?play\b"},
    {"id": "paramount", "nome": "Paramount+", "tipo": "video", "url": "https://www.paramountplus.com/br/", "onde": TUDO, "padrao": r"\bparamount\b"},
    {"id": "apple_tv", "nome": "Apple TV", "tipo": "video", "url": "https://www.apple.com/br/apple-tv-plus/", "onde": TUDO, "padrao": r"\bapple ?tv\b"},
    {"id": "youtube", "nome": "YouTube Premium", "tipo": "video", "url": "https://www.youtube.com/premium", "onde": TUDO + ("switch",),
     "padrao": r"\byoutube\b|\byt premium\b"},
    {"id": "crunchyroll", "nome": "Crunchyroll", "tipo": "video", "url": "https://www.crunchyroll.com/pt-br/premium", "onde": TUDO,
     "padrao": r"\bcrunchyroll\b"},
    {"id": "viki", "nome": "Rakuten Viki", "tipo": "video", "url": "https://www.viki.com/pass", "onde": TVS + CELULAR, "padrao": r"\bviki\b"},
    {"id": "mubi", "nome": "MUBI", "tipo": "video", "url": "https://mubi.com/pt/br", "onde": TVS + CELULAR, "padrao": r"\bmubi\b"},
    # música
    {"id": "spotify", "nome": "Spotify", "tipo": "musica", "url": "https://www.spotify.com/br-pt/premium/", "onde": TUDO, "padrao": r"\bspotify\b"},
    {"id": "deezer", "nome": "Deezer", "tipo": "musica", "url": "https://www.deezer.com/br/offers", "onde": TUDO, "padrao": r"\bdeezer\b"},
    {"id": "apple_music", "nome": "Apple Music", "tipo": "musica", "url": "https://www.apple.com/br/apple-music/", "onde": TUDO,
     "padrao": r"\bapple ?music\b"},
    {"id": "amazon_music", "nome": "Amazon Music Unlimited", "tipo": "musica", "url": "https://www.amazon.com.br/music/unlimited",
     "onde": TVS + CELULAR, "padrao": r"\bamazon ?music\b"},
    # jogos
    {"id": "game_pass", "nome": "Xbox Game Pass", "tipo": "jogos", "onde": ("xbox", "tv_samsung", "tv_lg", "fire_tv") + CELULAR,
     "url": "https://www.xbox.com/pt-BR/games/store/xbox-game-pass-ultimate/cfq7ttc0khs0", "padrao": r"\bgame ?pass\b|\bxbox\b"},
    {"id": "ps_plus", "nome": "PlayStation Plus", "tipo": "jogos", "url": "https://www.playstation.com/pt-br/ps-plus/", "onde": ("playstation",),
     "padrao": r"\bps ?plus\b|\bplaystation\b|\bpsn\b"},
    {"id": "nintendo", "nome": "Nintendo Switch Online", "tipo": "jogos", "url": "https://www.nintendo.com/pt-br/switch/online/",
     "onde": ("switch",), "padrao": r"\bnintendo\b"},
    {"id": "geforce_now", "nome": "GeForce NOW", "tipo": "jogos", "url": "https://abya.com/gfn/pt-BR",
     "onde": ("tv_samsung", "tv_lg", "android_tv") + CELULAR, "padrao": r"\bgeforce\b|\bgfn\b|\babya\b"},
    {"id": "boosteroid", "nome": "Boosteroid", "tipo": "jogos", "url": "https://boosteroid.com/",
     "onde": ("tv_samsung", "tv_lg", "android_tv") + CELULAR, "padrao": r"\bboosteroid\b"},
    {"id": "blacknut", "nome": "Blacknut", "tipo": "jogos", "url": "https://www.blacknut.com/pt-br",
     "onde": ("tv_samsung", "tv_lg", "android_tv", "fire_tv") + CELULAR, "padrao": r"\bblacknut\b"},
    {"id": "ea_play", "nome": "EA Play", "tipo": "jogos", "url": "https://www.ea.com/pt-br/ea-play", "onde": ("xbox", "playstation"),
     "padrao": r"\bea play\b"},
    {"id": "ubisoft_plus", "nome": "Ubisoft+", "tipo": "jogos", "url": "https://www.ubisoft.com/pt-br/ubisoft-plus", "onde": ("xbox", "playstation"),
     "padrao": r"\bubisoft\b"},
    {"id": "apple_arcade", "nome": "Apple Arcade", "tipo": "jogos", "url": "https://www.apple.com/br/apple-arcade/", "onde": ("ios", "apple_tv"),
     "padrao": r"\bapple ?arcade\b"},
    {"id": "play_pass", "nome": "Google Play Pass", "tipo": "jogos", "url": "https://play.google.com/intl/pt-BR/about/play-pass/",
     "onde": ("android",), "padrao": r"\bplay ?pass\b"},
]
POR_ID = {c["id"]: c for c in CATALOGO}

# ---------------------------------------------------------------- os aparelhos da casa (itens do InventarIA)

_TV = r"(?:tv|televis\w*|smart ?tv|qled|oled|crystal|the frame|nanocell|qned)"
APARELHOS = [
    ("tv_samsung", rf"\b{_TV}\b.*\bsamsung\b|\bsamsung\b.*\b{_TV}\b"),
    ("tv_lg", rf"\b{_TV}\b.*\blg\b|\blg\b.*\b{_TV}\b"),
    ("android_tv", rf"\b(?:google tv|android tv|chromecast|mi box|mi stick|tv box)\b"
                   rf"|\b(?:tcl|philips|sony|bravia|xiaomi|aiwa|toshiba|semp|multilaser|hisense)\b.*\b{_TV}\b"
                   rf"|\b{_TV}\b.*\b(?:tcl|philips|sony|bravia|xiaomi|aiwa|toshiba|semp|multilaser|hisense)\b"),
    ("fire_tv", r"\bfire ?tv\b|\bfire ?stick\b"),
    ("roku", r"\broku\b"),
    ("apple_tv", r"\bapple ?tv\b"),
    ("xbox", r"\bxbox\b"),
    ("playstation", r"\bplaystation\b|\bps ?[345]\b"),
    ("switch", r"\bnintendo\b|\bswitch (?:oled|lite|2)\b"),
    ("ios", r"\biphone\b|\bipad\b"),
    ("android", r"\b(?:galaxy|motorola|moto ?[a-z]\d*|redmi|poco|pixel|realme|oneplus|zenfone|android)\b"
                r"|\b(?:celular|smartphone|tablet)\b.*\b(?:samsung|xiaomi|lg|asus|tcl|nokia)\b"),
]


def aparelhos(itens):
    """{aparelho: [nomes dos itens]}: os aparelhos que rodam assinaturas, pelos nomes dos itens do InventarIA."""
    out = {}
    for it in itens or []:
        nome = str((it or {}).get("nome") or "").strip() if isinstance(it, dict) else ""
        n = assinaturas.normal(nome)
        if not n:
            continue
        for k, padrao in APARELHOS:
            if re.search(padrao, n) and nome not in out.setdefault(k, []):
                out[k].append(nome)
    return {k: v for k, v in out.items() if v}


def cabe(serv, tem):
    """A assinatura funciona em algum aparelho da casa? Todo celular roda o que tem app no Android e no iPhone."""
    onde = set(serv["onde"])
    return bool(onde & set(tem)) or {"android", "ios"} <= onde


def servicos(tem):
    """(as que funcionam nos aparelhos, as que ficam de fora); sem aparelhos (sem o InventarIA), todas."""
    if not tem:
        return list(CATALOGO), []
    dentro = [c for c in CATALOGO if cabe(c, tem)]
    return dentro, [c for c in CATALOGO if c not in dentro]


def nomes_aparelhos(tem):
    """ "TV Samsung, Xbox e celular": os aparelhos, na ordem do catálogo, e o celular no fim (todo mundo tem)."""
    ordem = [NOMES_APARELHO[k] for k in NOMES_APARELHO if k in tem and k not in CELULAR]
    cel = [NOMES_APARELHO[k] for k in CELULAR if k in tem]
    ordem += [f"celular ({' e '.join(cel)})" if cel else "celular"]
    return ordem


def de_quem_paga(d, hoje=None):
    """{id do serviço: valor por mês}: as assinaturas que já estão nos fixos de despesa."""
    ym = (hoje or date.today()).isoformat()[:7]
    out = {}
    for r in d.get("recorrencias") or []:
        if not isinstance(r, dict) or r.get("tipo") == "receita" or not calc.ativa_em(dict(r, freq="mensal"), ym):
            continue
        n = assinaturas.normal(r.get("descricao"))
        for c in CATALOGO:
            if n and re.search(c["padrao"], n):
                out[c["id"]] = round(out.get(c["id"], 0) + calc.mensal_recorrencia(r), 2)
                break
    return out


# ---------------------------------------------------------------- a página

_PRECO_BR = re.compile(r"R\$\s?\d")
_STR_JSON = re.compile(r'"((?:[^"\\\n]|\\.){4,400})"')
_SCRIPT = re.compile(r"<script\b[^>]*>(.*?)</script\s*>", re.S | re.I)


def texto_pagina(raw, max_extras=80):
    """O texto da página e, das páginas feitas em JavaScript (o preço vem num JSON dentro de um <script>), os textos
    com R$ escritos lá, uma linha cada."""
    texto = assinaturas.html_texto(raw)
    vistos, extras = set(), []
    for bloco in _SCRIPT.findall(raw or ""):
        for m in _STR_JSON.finditer(bloco):
            s = m.group(1)
            if "R$" not in s and "R\\u0024" not in s:
                continue
            try:
                s = json.loads(f'"{s}"')
            except ValueError:
                continue
            s = re.sub(r"\s+", " ", assinaturas.html_texto(s) if "<" in s else s).strip()
            if _PRECO_BR.search(s) and len(s) <= 300 and s not in vistos and s not in texto:
                vistos.add(s)
                extras.append(s)
            if len(extras) >= max_extras:
                break
    return "\n".join([texto] + extras if texto else extras)


def trechos(texto):
    """Só as partes com preço em reais, para mandar pouco texto à IA (e para saber se a página mudou)."""
    return assinaturas.trechos_preco(texto, limite=12000, margem=200, padrao=_PRECO_BR)


def assinatura_trechos(t):
    return hashlib.sha1(assinaturas.para_comparar(t).encode()).hexdigest()[:16]


PROMPT = """Você lê a página oficial de {nome} ({url}). Abaixo estão os trechos da página com preços em reais.
Responda só com JSON válido, sem texto antes ou depois:
{{"planos": [{{"plano": "nome do plano", "mensal": 29.9, "trecho": "..."}}],
 "promocoes": [{{"plano": "nome do plano", "preco": 9.9, "total": 0, "meses": 3, "depois": 29.9, "ate": "AAAA-MM-DD",
   "quem": "para quem vale, curto", "trecho": "..."}}]}}
Regras:
- planos: o preço de sempre de cada plano pago mês a mês (o número escrito; não calcule).
- promocoes: só preços promocionais por tempo limitado: os primeiros meses mais baratos, um desconto até uma data, Black
  Friday. O plano anual ou semestral de sempre não é promoção, nem teste grátis.
- preco: o preço por mês na promoção, como está escrito; se a página só escrever o total, deixe 0 e ponha o total em "total".
- meses: por quantos meses vale o preço (0 se não disser); depois: o preço depois da promoção, se escrito (senão 0);
  ate: até quando dá para assinar, se escrito (senão ""); quem: novos assinantes, quem volta... se escrito (senão "").
- trecho: copie exatamente o pedaço da página com o preço (até 160 caracteres).
Use só números escritos nos trechos; não use preços que você conhece de memória. Sem promoção, "promocoes": [].

Trechos da página:
<<<
{trechos}
>>>"""


def prompt(serv, t):
    return PROMPT.format(nome=serv["nome"], url=serv["url"], trechos=t)


# ---------------------------------------------------------------- o que a IA leu, conferido

# o que diz que é por tempo limitado (perto do preço, na página)
_LIMITADA = re.compile(r"promo|oferta|black ?friday|cyber|desconto|\d+ ?% off|\boff\b|tempo limitado|so ate|somente ate|"
                       r"valid[oa] ate|ate o dia|primeiro mes|primeiros \d+ meses|\d+ primeiros meses|nos primeiros|metade do preco")
_MESES = ("janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
BARATA = 0.92  # a promoção custa no máximo 92% do preço de sempre


def _linha(v, n=60):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _perto(trecho_cmp, texto, margem=120):
    """A linha da página com o trecho e a de cima (o "Black Friday" escrito acima do preço); o trecho que passa de uma
    linha, com um pedaço em volta."""
    linhas = [assinaturas.para_comparar(x) for x in str(texto or "").splitlines()]
    for i, ln in enumerate(linhas):
        if trecho_cmp in ln:
            return " ".join(linhas[max(0, i - 1):i + 1])
    cmp = " ".join(linhas)
    i = cmp.find(trecho_cmp)
    return cmp[max(0, i - margem):i + len(trecho_cmp) + margem] if i >= 0 else trecho_cmp


def _data_escrita(d, perto):
    """A data está escrita perto do preço (30/11, 30/11/2026 ou 30 de novembro)?"""
    n = assinaturas.normal(perto)
    return bool(re.search(rf"\b0?{d.day}/0?{d.month}\b", perto) or re.search(rf"\b0?{d.day} de {_MESES[d.month - 1]}\b", n))


def limpar(parsed, texto, hoje=None, antes=None):
    """Fica só com o que a página confirma. antes: {plano normalizado: preço de sempre} de uma leitura anterior (a
    página da promoção às vezes não mostra o preço de sempre). Devolve ({planos, promocoes}, recusados)."""
    hoje = hoje or date.today()
    p = parsed if isinstance(parsed, dict) else {}
    cmp = assinaturas.para_comparar(texto)
    recusados = 0
    planos = []
    for x in (p.get("planos") if isinstance(p.get("planos"), list) else [])[:16]:
        if not isinstance(x, dict):
            continue
        v = round(calc.num_br(x.get("mensal")), 2)
        if v <= 0:
            continue
        if not assinaturas.confere(str(x.get("trecho") or ""), v, cmp):
            recusados += 1
            continue
        nome = _linha(x.get("plano"), 50) or "Plano"
        if all(assinaturas.normal(nome) != assinaturas.normal(y["plano"]) for y in planos):
            planos.append({"plano": nome, "mensal": v})
    ref = dict(antes or {})
    ref.update({assinaturas.normal(y["plano"]): y["mensal"] for y in planos})
    promos, vistos = [], set()
    for x in (p.get("promocoes") if isinstance(p.get("promocoes"), list) else [])[:16]:
        if not isinstance(x, dict):
            continue
        trecho = _linha(x.get("trecho"), 200)
        tc = assinaturas.para_comparar(trecho)
        preco, total = round(calc.num_br(x.get("preco")), 2), round(calc.num_br(x.get("total")), 2)
        meses = int(calc.num_br(x.get("meses")))
        nums = assinaturas.numeros(trecho)
        if not (1 <= meses <= 36 and any(abs(n - meses) < 0.01 for n in nums)):
            meses = 0
        if preco <= 0 and total > 0 and meses:
            preco, por_total = round(total / meses, 2), total
        else:
            por_total = 0
        if preco <= 0 or len(tc) < 3 or tc not in cmp or not any(abs(n - (por_total or preco)) < 0.006 for n in nums):
            recusados += 1
            continue
        perto = _perto(tc, texto)
        ate = calc.parse_data(str(x.get("ate") or "")[:10])
        if ate and ate < hoje:
            continue  # já acabou
        ate = ate if ate and _data_escrita(ate, perto) else None
        if not ate and not _LIMITADA.search(assinaturas.normal(perto)):
            continue  # não diz que é por tempo limitado: o plano de sempre
        plano = _linha(x.get("plano"), 50)
        depois = round(calc.num_br(x.get("depois")), 2)
        if depois and not any(abs(n - depois) < 0.006 for n in assinaturas.numeros(perto)):
            depois = 0
        normal = depois or ref.get(assinaturas.normal(plano)) or (min(ref.values()) if len(ref) == 1 else 0)
        if normal and preco > normal * BARATA:
            continue  # não é mais barato que o de sempre
        quem = _linha(x.get("quem"), 60)
        if quem and assinaturas.para_comparar(quem) not in cmp:
            quem = ""
        chave = (assinaturas.normal(plano), preco, meses)
        if chave in vistos:
            continue
        vistos.add(chave)
        promos.append({"plano": plano, "preco": preco, "meses": meses, "normal": round(normal, 2), "ate": ate.isoformat() if ate else "",
                       "quem": quem, "trecho": trecho[:160], **({"total": por_total} if por_total else {})})
    return {"planos": planos, "promocoes": sorted(promos, key=lambda y: y["preco"])}, recusados


def id_promo(sid, x):
    return "promo:" + sid + ":" + hashlib.sha1(repr((assinaturas.normal(x.get("plano")), x["preco"], x.get("meses") or 0)).encode()).hexdigest()[:10]


def valendo(lida, hoje=None):
    """As promoções de uma leitura que ainda valem (a data de até quando não passou)."""
    hoje = (hoje or date.today()).isoformat()
    return [x for x in (lida or {}).get("promocoes") or [] if not x.get("ate") or x["ate"] >= hoje]


def linha(nome, x):
    """ "HBO Max: R$ 9,90 por mês por 3 meses (depois R$ 29,90)"."""
    t = f"{nome}: {calc.fmt_brl(x['preco'])} por mês"
    if x.get("meses"):
        t += f" por {x['meses']} {'mês' if x['meses'] == 1 else 'meses'}"
    if x.get("normal"):
        t += f" (depois {calc.fmt_brl(x['normal'])})"
    return t


TEXTOS = {
    "pendente": "ainda não conferida",
    "sem_acesso": "a página não abriu",
    "sem_precos": "a página não mostra preços para o app",
    "erro_ia": "a IA não conseguiu ler",
    "nao_confere": "a IA citou preços que não estão na página",
    "ia_desligada": "a IA está desligada",
    "sem_ia": "sem IA no Home Assistant",
}

# ---------------------------------------------------------------- a IA simulada (testes e desenvolvimento)

_SIM_PLANO = re.compile(r"^(?:Plano )?(.+?): R\$ ?(\d+,\d{2}) por m[eê]s$", re.I)
_SIM_PROMO = re.compile(r"^(?:Oferta|Promoção|Black Friday)[^:]*: (.+?) por R\$ ?(\d+,\d{2}) por m[eê]s(?: nos (\d+) primeiros meses)?"
                        r"(?:, depois R\$ ?(\d+,\d{2}))?(?:, até (\d{2})/(\d{2})/(\d{4}))?(?:, para (.+?))?\.?$", re.I)


def simulados(texto):
    """A IA de mentira: "Plano Básico: R$ 29,90 por mês" é um plano; "Oferta: Básico por R$ 9,90 por mês nos 3
    primeiros meses, depois R$ 29,90, até 30/11/2026, para novos assinantes" é uma promoção."""
    out = {"planos": [], "promocoes": []}
    for ln in str(texto or "").splitlines():
        ln = ln.strip()
        m = _SIM_PROMO.match(ln)
        if m:
            out["promocoes"].append({"plano": m.group(1), "preco": calc.num_br(m.group(2)), "meses": int(m.group(3) or 0),
                                     "depois": calc.num_br(m.group(4)) if m.group(4) else 0,
                                     "ate": f"{m.group(7)}-{m.group(6)}-{m.group(5)}" if m.group(5) else "",
                                     "quem": m.group(8) or "", "trecho": ln[:160]})
            continue
        m = _SIM_PLANO.match(ln)
        if m:
            out["planos"].append({"plano": m.group(1), "mensal": calc.num_br(m.group(2)), "trecho": ln[:120]})
    return out
