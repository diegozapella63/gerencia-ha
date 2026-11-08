"""Ferramentas do GerencIA para o Claude e o Gemini, pelo CorrerIA (o MCP da casa): ler as finanças e gravar
(lançar, editar, apagar, marcar como pago, saldos e investimentos, fixos). O CorrerIA lista as ferramentas
(GET /api/integracao/ferramentas) e chama uma (POST {nome, argumentos, pessoa, cliente}); o server.py lê e grava os
dados (com a revisão e as versões automáticas) e aqui ficam as regras, as mesmas da tela (app.js). Só biblioteca padrão.

Cada ferramenta: {nome, titulo, descricao, entrada (JSON Schema), grava, apaga}. chamar() devolve (texto, mudou)."""
import json
import re
import unicodedata
from datetime import date, datetime, timedelta

import calc
import chat
import integracao

MAX_PERIODO = 400   # dias de uma busca de lançamentos
MAX_LISTA = 1000

TIPOS_INV = {  # tipo: (nome, indexador, taxa, liquidez) — os padrões do app (TIPOS no app.js), menos os bens
    "cdb": ("CDB", "cdi_pct", 100, "vencimento"), "lci": ("LCI/LCA", "cdi_pct", 90, "vencimento"),
    "tesouro": ("Tesouro", "selic_mais", 0, "diaria"), "poupanca": ("Poupança", "poupanca", 0, "diaria"),
    "caixinha": ("Caixinha", "cdi_pct", 100, "diaria"), "fundo": ("Fundo", "cdi_pct", 100, "diaria"),
    "acoes": ("Ações/FII", "estimado", 10, "diaria"), "ouro": ("Ouro", "estimado", 10, "diaria"),
    "dinheiro": ("Dinheiro", "parado", 0, "diaria"), "previdencia": ("Previdência", "cdi_pct", 95, "vencimento"),
    "outro": ("Outro", "pre", 12, "vencimento"),
}
INDEXADORES = {"cdi_pct": "% do CDI", "cdi_mais": "CDI + taxa ao ano", "pre": "prefixado (taxa ao ano)", "ipca_mais": "IPCA + taxa ao ano",
               "selic_mais": "Selic + taxa ao ano", "poupanca": "poupança", "estimado": "estimado (taxa ao ano)", "parado": "sem rendimento"}
CORES_BANCO = ["#56AEFF", "#B79BFF", "#4CD3A5", "#FFA23A", "#FF77A8", "#F2C14E", "#FF8A65", "#E04B8A", "#FF5A4E", "#B8B0B0"]

INSTRUCOES = ("GerencIA: as finanças da casa (caixa, contas a pagar, cartões e faturas, investimentos e patrimônio). Valores em "
              "reais e datas no formato AAAA-MM-DD. Comece por gerencia_resumo; os ids que ele mostra servem nas outras "
              "ferramentas. Uma conta que já está em contas a pagar (fixo ou fatura) se paga com gerencia_marcar_pago, não se "
              "lança de novo. Antes de gravar, diga à pessoa o que vai ser feito.")


class ErroFerramenta(ValueError):
    pass


# ---------------------------------------------------------------- a lista

def _obj(props, obrig=()):
    return {"type": "object", "properties": props, "required": list(obrig), "additionalProperties": False}


_DATA = {"type": "string", "description": "AAAA-MM-DD"}
_ID = {"type": "string", "description": "O id do lançamento (de gerencia_lancamentos, gerencia_resumo ou gerencia_contas_a_pagar)."}

FERRAMENTAS = [
    {"nome": "resumo", "titulo": "Resumo das finanças", "grava": False,
     "descricao": "Visão geral de hoje: contas no banco e cartões, saldo do caixa e o movimento do mês, contas a pagar (atrasadas "
                  "e dos próximos 45 dias), lançamentos dos últimos 45 dias, fixos, investimentos, patrimônio e as categorias. "
                  "Comece por aqui: os ids servem nas outras ferramentas.",
     "entrada": _obj({})},
    {"nome": "lancamentos", "titulo": "Buscar lançamentos", "grava": False,
     "descricao": "Gastos e recebimentos de um período (pela data da compra ou do recebimento), com os totais e os gastos por "
                  "categoria. Os fixos que ainda não foram lançados entram também (o id começa com v:). Sem período, o mês atual.",
     "entrada": _obj({"de": _DATA, "ate": _DATA,
                      "busca": {"type": "string", "description": "Parte da descrição ou da observação."},
                      "categoria": {"type": "string", "description": "Id ou nome da categoria."},
                      "tipo": {"type": "string", "enum": ["despesa", "receita"]},
                      "conta": {"type": "string", "description": "Id ou nome do banco/conta."},
                      "limite": {"type": "integer", "minimum": 1, "maximum": MAX_LISTA, "description": "Padrão: 200."}})},
    {"nome": "contas_a_pagar", "titulo": "Contas a pagar", "grava": False,
     "descricao": "Contas, fixos e faturas de cartão a pagar (e as já pagas) num período, com as atrasadas dos últimos 2 meses. "
                  "Sem período, de hoje a 45 dias. O id serve em gerencia_marcar_pago.",
     "entrada": _obj({"de": _DATA, "ate": _DATA})},
    {"nome": "investimentos", "titulo": "Investimentos", "grava": False,
     "descricao": "Cada investimento (e bem) com o valor de hoje, o rendimento, o vencimento, a liquidez e de quem é; e os totais "
                  "do patrimônio.",
     "entrada": _obj({})},
    {"nome": "cadastros", "titulo": "Cadastros", "grava": False,
     "descricao": "Contas de banco (com o cartão de crédito: dia de fechamento e de vencimento), categorias, bancos, fixos, as "
                  "pessoas dos investimentos de terceiros, os tipos de investimento e os rendimentos aceitos.",
     "entrada": _obj({})},
    {"nome": "lancar", "titulo": "Lançar gasto ou recebimento", "grava": True,
     "descricao": "Lança um gasto (despesa) ou um recebimento (receita). Compra parcelada: valor de cada parcela, parcelas e "
                  "parcela_atual (as próximas entram nos meses seguintes). Sem pago, fica pago se a data já passou (no cartão de "
                  "crédito, segue a fatura). Para pagar uma conta que já existe, use gerencia_marcar_pago.",
     "entrada": _obj({"tipo": {"type": "string", "enum": ["despesa", "receita"]},
                      "descricao": {"type": "string", "description": "Curta, como a pessoa escreveria."},
                      "valor": {"type": "number", "exclusiveMinimum": 0, "description": "Em reais; em parcelas, o valor de cada uma."},
                      "data": {"type": "string", "description": "AAAA-MM-DD; sem data, hoje. Em parcelas, a data da parcela atual."},
                      "categoria": {"type": "string", "description": "Id ou nome da categoria (do mesmo tipo)."},
                      "conta": {"type": "string", "description": "Id ou nome do banco/conta."},
                      "cartao": {"type": "boolean", "description": "No cartão de crédito da conta."},
                      "parcelas": {"type": "integer", "minimum": 2, "maximum": 120},
                      "parcela_atual": {"type": "integer", "minimum": 1, "maximum": 120},
                      "pago": {"type": "boolean"},
                      "obs": {"type": "string"}}, ["tipo", "descricao", "valor"])},
    {"nome": "editar_lancamento", "titulo": "Editar lançamento", "grava": True,
     "descricao": "Muda um lançamento (só o que vier). Num fixo, muda só o daquele mês.",
     "entrada": _obj({"id": _ID, "descricao": {"type": "string"}, "valor": {"type": "number", "exclusiveMinimum": 0}, "data": _DATA,
                      "categoria": {"type": "string"}, "conta": {"type": "string", "description": "Id ou nome; vazio tira a conta."},
                      "cartao": {"type": "boolean"}, "pago": {"type": "boolean"}, "obs": {"type": "string"}}, ["id"])},
    {"nome": "apagar_lancamento", "titulo": "Apagar lançamento", "grava": True, "apaga": True,
     "descricao": "Apaga um lançamento. Num fixo, apaga só o daquele mês (o fixo continua nos outros). Numa compra parcelada, "
                  "só aquela parcela.",
     "entrada": _obj({"id": _ID}, ["id"])},
    {"nome": "marcar_pago", "titulo": "Marcar como pago", "grava": True,
     "descricao": "Marca uma conta, um fixo ou uma fatura de cartão como paga (ou um recebimento como recebido); com pago "
                  "false, desfaz. valor: o que foi pago, se diferente.",
     "entrada": _obj({"id": {"type": "string", "description": "O id de gerencia_contas_a_pagar (fatura: f:...; fixo: v:...) ou de um lançamento."},
                      "pago": {"type": "boolean", "description": "Padrão: true."},
                      "valor": {"type": "number", "exclusiveMinimum": 0}}, ["id"])},
    {"nome": "atualizar_investimento", "titulo": "Atualizar investimento", "grava": True,
     "descricao": "Muda o valor de um investimento: o saldo de agora, ou um aporte (soma ao valor de hoje), ou um resgate "
                  "(tira). Um dos três.",
     "entrada": _obj({"id": {"type": "string", "description": "O id do investimento."},
                      "saldo": {"type": "number", "minimum": 0}, "aporte": {"type": "number", "exclusiveMinimum": 0},
                      "resgate": {"type": "number", "exclusiveMinimum": 0}}, ["id"])},
    {"nome": "novo_investimento", "titulo": "Novo investimento", "grava": True,
     "descricao": "Cadastra um investimento. Sem rendimento, o padrão do tipo (CDB: 100% do CDI). de_quem vazio: da própria "
                  "pessoa; com um nome, de outra pessoa (fica fora do patrimônio dela).",
     "entrada": _obj({"nome": {"type": "string"}, "valor": {"type": "number", "minimum": 0, "description": "O valor de hoje."},
                      "tipo": {"type": "string", "enum": list(TIPOS_INV)}, "banco": {"type": "string", "description": "O nome do banco ou corretora."},
                      "indexador": {"type": "string", "enum": list(INDEXADORES)},
                      "taxa": {"type": "number", "description": "Pelo indexador: 110 (% do CDI), 6.5 (IPCA + 6,5% a.a.), 13 (prefixado)."},
                      "vencimento": _DATA, "liquidez": {"type": "string", "enum": ["diaria", "vencimento"]},
                      "de_quem": {"type": "string"}}, ["nome", "valor", "tipo"])},
    {"nome": "novo_fixo", "titulo": "Novo fixo", "grava": True,
     "descricao": "Cadastra um gasto ou recebimento que se repete todo mês (ou todo ano), como aluguel, salário ou IPVA. Aparece "
                  "nas contas a pagar a cada mês.",
     "entrada": _obj({"tipo": {"type": "string", "enum": ["despesa", "receita"]}, "descricao": {"type": "string"},
                      "valor": {"type": "number", "exclusiveMinimum": 0},
                      "data": {"type": "string", "description": "A primeira vez (AAAA-MM-DD): o dia vale para os próximos meses."},
                      "repete": {"type": "string", "enum": ["mensal", "anual"], "description": "Padrão: mensal."},
                      "categoria": {"type": "string"}, "conta": {"type": "string"}, "cartao": {"type": "boolean"}},
                     ["tipo", "descricao", "valor", "data"])},
]
POR_NOME = {f["nome"]: f for f in FERRAMENTAS}


def lista():
    return [dict(f, apaga=bool(f.get("apaga"))) for f in FERRAMENTAS]


# ---------------------------------------------------------------- ajudantes

def _norm(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t or "")) if unicodedata.category(c) != "Mn").lower().strip()


def _brl(v):
    return "R$ " + calc.fmt_brl(v) if not calc.fmt_brl(v).startswith("R$") else calc.fmt_brl(v)


def _dm(iso):
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}" if iso and len(iso) >= 10 else (iso or "")


def _json(v):
    return json.dumps(v, ensure_ascii=False, separators=(",", ":"))


def _data(v, hoje, campo="data", padrao=True):
    s = str(v or "").strip().lower()
    if not s or s == "hoje":
        if padrao:
            return hoje
        raise ErroFerramenta(f"Falta {campo}.")
    if s == "ontem":
        return hoje - timedelta(days=1)
    if s == "amanha" or s == "amanhã":
        return hoje + timedelta(days=1)
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else date.fromisoformat(s[:10])
    except ValueError:
        raise ErroFerramenta(f"{campo.capitalize()} inválida: {v}. Use AAAA-MM-DD.") from None


def _valor(v, campo="valor", zero=False):
    x = calc.num_br(v) if isinstance(v, str) else calc.num(v, None) if v is not None else None
    if x is None or x != x or (x < 0 if zero else x <= 0):
        raise ErroFerramenta(f"{campo.capitalize()} inválido: {v}.")
    if x > 1e10:
        raise ErroFerramenta(f"{campo.capitalize()} grande demais.")
    return round(float(x), 2)


def _texto(v, n=120):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _categoria(d, v, tipo):
    """Pelo id ou pelo nome; sem nada, Outros gastos / Outros recebimentos (se existirem)."""
    cats = [c for c in d.get("categorias", []) if c.get("tipo", "despesa") == tipo]
    if v is None or str(v).strip() == "":
        padrao = "c-outros-gastos" if tipo == "despesa" else "c-outros-receb"
        return padrao if any(c.get("id") == padrao for c in cats) else ""
    n = _norm(v)
    c = (next((c for c in cats if c.get("id") == v), None) or next((c for c in cats if _norm(c.get("nome")) == n), None)
         or next((c for c in cats if n and n in _norm(c.get("nome"))), None))
    if not c:
        nomes = ", ".join(f"{c.get('nome')} ({c.get('id')})" for c in cats)
        raise ErroFerramenta(f"Categoria não encontrada: {v}. As de {'gasto' if tipo == 'despesa' else 'recebimento'}: {nomes}.")
    return c["id"]


def _conta(d, v):
    """Pelo id, pelo nome (Banco · pessoa) ou só pelo banco, se for uma conta só."""
    if v is None or str(v).strip() == "":
        return ""
    contas = calc.mapa_contas(d)
    if v in contas:
        return v
    n = _norm(v)
    iguais = [k for k, c in contas.items() if _norm(calc.nome_conta(c)) == n] or \
             [k for k, c in contas.items() if _norm(c.get("banco_nome")) == n] or \
             [k for k, c in contas.items() if n and n in _norm(calc.nome_conta(c))]
    if len(iguais) == 1:
        return iguais[0]
    todas = ", ".join(f"{calc.nome_conta(c)} ({k})" for k, c in contas.items()) or "nenhuma cadastrada"
    raise ErroFerramenta(("Mais de uma conta com esse nome" if iguais else f"Conta não encontrada: {v}") + f". As contas: {todas}.")


def _nome_cat(d, cid):
    return next((c.get("nome", "") for c in d.get("categorias", []) if c.get("id") == cid), "")


def _situacao(l):
    rec = l.get("tipo") == "receita"
    return ("recebido" if rec else "pago") if l.get("pago") else ("a receber" if rec else "a pagar")


def _descrever(d, l, contas=None):
    """Uma linha para a resposta: Mercado · R$ 45,90 · 08/11/2026 · Mercado · Banco Lua · Ana (cartão, fatura de 10/12) · pago."""
    contas = contas if contas is not None else calc.mapa_contas(d)
    partes = [l.get("descricao") or "Sem descrição", _brl(calc.num(l.get("valor"))), _dm(l.get("data"))]
    if l.get("parcela"):
        partes[0] += f" ({l['parcela']})"
    cat = _nome_cat(d, l.get("categoria"))
    if cat:
        partes.append(cat)
    c = contas.get(l.get("conta"))
    if c:
        nome = calc.nome_conta(c)
        if l.get("cartao") and c.get("cartao"):
            dc = calc.data_caixa(l, contas, d)
            nome += f" (cartão de crédito, fatura de {_dm(dc.isoformat())})" if dc else " (cartão de crédito)"
        partes.append(nome)
    partes.append(_situacao(l))
    return " · ".join(partes)


def _pago_pela_data(d, l, hoje):
    dc = calc.data_caixa(l, calc.mapa_contas(d), d)
    return bool(dc and dc <= hoje)


def _meses(de, ate):
    ym, fim = de.isoformat()[:7], ate.isoformat()[:7]
    while ym <= fim:
        yield ym
        ym = integracao.add_ym(ym, 1)


# ---------------------------------------------------------------- leitura

def _lancamentos(d, a, hoje):
    de = _data(a.get("de"), hoje.replace(day=1), "de") if a.get("de") else hoje.replace(day=1)
    ate = _data(a.get("ate"), hoje, "ate") if a.get("ate") else calc._data_mes(hoje.year, hoje.month, 31)
    if ate < de:
        raise ErroFerramenta("O fim do período vem antes do começo.")
    if (ate - de).days > MAX_PERIODO:
        raise ErroFerramenta(f"Período grande demais (até {MAX_PERIODO} dias).")
    tipo = a.get("tipo") if a.get("tipo") in ("despesa", "receita") else None
    cat = _categoria(d, a["categoria"], tipo or "despesa") if a.get("categoria") and tipo else None
    if a.get("categoria") and not tipo:  # sem tipo: a categoria pode ser dos dois
        n = _norm(a["categoria"])
        achadas = [c.get("id") for c in d.get("categorias", []) if c.get("id") == a["categoria"] or _norm(c.get("nome")) == n]
        if not achadas:
            achadas = [c.get("id") for c in d.get("categorias", []) if n in _norm(c.get("nome"))]
        if not achadas:
            raise ErroFerramenta(f"Categoria não encontrada: {a['categoria']}.")
        cat = set(achadas)
    conta = _conta(d, a.get("conta")) if a.get("conta") else None
    busca = _norm(a.get("busca"))
    limite = max(1, min(int(calc.num(a.get("limite"), 200) or 200), MAX_LISTA))
    contas = calc.mapa_contas(d)
    achados = []
    for ym in _meses(de, ate):
        for l in calc.ocorrencias_mes(d, ym):
            dt = str(l.get("data") or "")[:10]
            if not (de.isoformat() <= dt <= ate.isoformat()):
                continue
            if tipo and l.get("tipo", "despesa") != tipo:
                continue
            if cat and l.get("categoria") not in (cat if isinstance(cat, set) else {cat}):
                continue
            if conta and l.get("conta") != conta:
                continue
            if busca and busca not in _norm(l.get("descricao")) and busca not in _norm(l.get("obs")):
                continue
            achados.append(l)
    achados.sort(key=lambda l: (str(l.get("data") or ""), str(l.get("descricao") or "")), reverse=True)
    entradas = saidas = 0.0
    por_cat = {}
    for l in achados:
        if l.get("ajuste"):
            continue
        v = calc.num(l.get("valor"))
        if l.get("tipo") == "receita":
            entradas += v
        else:
            saidas += v
            nome = _nome_cat(d, l.get("categoria")) or "Sem categoria"
            por_cat[nome] = por_cat.get(nome, 0) + v
    itens = []
    for l in achados[:limite]:
        virtual = bool(l.get("recorrencia")) and l.get("id") in (None, "", l.get("recorrencia"))  # o fixo ainda não lançado
        it = {"id": f"v:{l['recorrencia']}:{l['competencia']}" if virtual else (l.get("id") or ""),
              "data": l.get("data"), "tipo": "ajuste de saldo" if l.get("ajuste") else "desconto" if l.get("desconto") else
              "aporte" if l.get("aporte") else "recebimento" if l.get("tipo") == "receita" else "gasto",
              "descricao": l.get("descricao") or "", "valor": round(calc.num(l.get("valor")), 2),
              "categoria": _nome_cat(d, l.get("categoria")), "situacao": _situacao(l)}
        c = contas.get(l.get("conta"))
        if c:
            it["conta"] = calc.nome_conta(c) + (" · cartão de crédito" if l.get("cartao") and c.get("cartao") else "")
            dc = calc.data_caixa(l, contas, d)
            if dc and dc.isoformat() != it["data"]:
                it["data_caixa"] = dc.isoformat()
        for k in ("parcela", "obs"):
            if l.get(k):
                it[k] = l[k]
        if l.get("recorrencia"):
            it["fixo"] = "ainda não lançado" if virtual else True
        if l.get("desconto"):
            it["de"] = l.get("pai") or ""
            it.pop("id")
        itens.append(it)
    return _json({"periodo": {"de": de.isoformat(), "ate": ate.isoformat()}, "encontrados": len(achados), "mostrando": len(itens),
                  "entradas": round(entradas, 2), "saidas": round(saidas, 2),
                  "gastos_por_categoria": {k: round(v, 2) for k, v in sorted(por_cat.items(), key=lambda x: -x[1])},
                  "lancamentos": itens})


def _contas_a_pagar(d, a, hoje):
    de = _data(a.get("de"), hoje, "de") if a.get("de") else hoje
    ate = _data(a.get("ate"), hoje, "ate") if a.get("ate") else hoje + timedelta(days=45)
    try:
        r = integracao.listar(d, de, ate, hoje)
    except ValueError as e:
        raise ErroFerramenta(str(e)) from None
    out = []
    for c in r["contas"]:
        it = {"id": c["id"], "tipo": c["tipo"], "descricao": c["descricao"], "valor": c["valor"], "vencimento": c["vencimento"],
              "situacao": "paga" if c["pago"] else "atrasada" if c.get("atrasada") else "a pagar"}
        for k in ("categoria", "conta"):
            if c.get(k):
                it[k] = c[k]
        if c.get("itens"):
            it["compras"] = c["itens"]
        out.append(it)
    abertas = [c for c in out if c["situacao"] != "paga"]
    return _json({"hoje": hoje.isoformat(), "a_pagar": round(sum(c["valor"] for c in abertas), 2),
                  "atrasadas": round(sum(c["valor"] for c in abertas if c["situacao"] == "atrasada"), 2), "contas": out})


def _investimentos(d, hoje):
    ind, corrigir = d.get("indices", {}), d.get("ajustes", {}).get("corrigir", True)
    bancos = {b.get("id"): b.get("nome", "") for b in d.get("bancos", [])}
    out = []
    for i in d.get("investimentos", []):
        it = {"id": i.get("id"), "nome": i.get("nome", ""), "banco": bancos.get(i.get("banco"), ""), "tipo": i.get("tipo", ""),
              "de_quem": "meu" if i.get("titular") != "terceiros" else (i.get("terceiro") or "terceiros"),
              "valor_hoje": round(calc.valor_hoje(i, ind, corrigir, hoje), 2), "valor_informado": round(calc.num(i.get("valor")), 2),
              "informado_em": i.get("data_valor") or "", "rendimento": calc.rotulo_taxa(i),
              "liquidez": "diária" if i.get("liquidez") == "diaria" else "no vencimento"}
        if i.get("vencimento"):
            it["vencimento"] = i["vencimento"]
        if i.get("obs"):
            it["obs"] = i["obs"]
        out.append(it)
    t = calc.totais(d, hoje)
    return _json({"patrimonio": {"meu": t["meu"], "de_outras_pessoas": t["terceiros"], "total": t["total"], "rende_por_mes": t["rende_mes"]},
                  "investimentos": out})


def _cadastros(d):
    contas = []
    for k, c in calc.mapa_contas(d).items():
        it = {"id": k, "nome": calc.nome_conta(c), "banco": c.get("banco_nome", "")}
        if c.get("pessoa"):
            it["pessoa"] = c["pessoa"]
        if c.get("cartao"):
            it["cartao_de_credito"] = {"fecha_dia": c.get("fechamento"), "vence_dia": c.get("vencimento")}
        contas.append(it)
    fixos = []
    for r in d.get("recorrencias", []):
        it = {"id": r.get("id"), "descricao": r.get("descricao", ""), "tipo": r.get("tipo", "despesa"), "valor": round(calc.num(r.get("valor")), 2),
              "dia": r.get("dia"), "repete": "anual" if r.get("freq") == "anual" else "mensal", "desde": r.get("inicio")}
        if r.get("fim"):
            it["ate"] = r["fim"]
        if r.get("categoria"):
            it["categoria"] = _nome_cat(d, r["categoria"])
        fixos.append(it)
    terceiros = sorted({i.get("terceiro") for i in d.get("investimentos", []) if i.get("titular") == "terceiros" and i.get("terceiro")})
    return _json({"contas": contas, "categorias": [{"id": c.get("id"), "nome": c.get("nome", ""), "tipo": c.get("tipo", "despesa")} for c in d.get("categorias", [])],
                  "bancos": [{"id": b.get("id"), "nome": b.get("nome", "")} for b in d.get("bancos", [])], "fixos": fixos,
                  "pessoas_terceiros": terceiros, "tipos_investimento": {k: v[0] for k, v in TIPOS_INV.items()}, "rendimentos": INDEXADORES})


# ---------------------------------------------------------------- gravação

def _lancar(d, a, hoje):
    tipo = a.get("tipo")
    if tipo not in ("despesa", "receita"):
        raise ErroFerramenta("tipo: despesa (gasto) ou receita (recebimento).")
    desc = _texto(a.get("descricao"))
    if not desc:
        raise ErroFerramenta("Falta a descrição.")
    valor = _valor(a.get("valor"))
    data = _data(a.get("data"), hoje)
    cat = _categoria(d, a.get("categoria"), tipo)
    conta = _conta(d, a.get("conta"))
    contas = calc.mapa_contas(d)
    cartao = tipo == "despesa" and a.get("cartao") is True
    if cartao and not (contas.get(conta) or {}).get("cartao"):
        raise ErroFerramenta("Essa conta não tem cartão de crédito." if conta else "Diga a conta do cartão de crédito.")
    base = {"tipo": tipo, "descricao": desc, "valor": valor, "categoria": cat, "conta": conta, "cartao": cartao, "obs": _texto(a.get("obs"), 500)}
    if tipo == "despesa" and cat == "c-investimentos":  # aplicação nos investimentos: uma saída do tipo Aporte
        base.update(aporte=True, cartao=False)
    total = int(calc.num(a.get("parcelas"), 0) or 0)
    atual = int(calc.num(a.get("parcela_atual"), 1) or 1)
    if total and not 2 <= total <= 120:
        raise ErroFerramenta("parcelas: de 2 a 120.")
    if total and not 1 <= atual <= total:
        raise ErroFerramenta("parcela_atual: de 1 até o total de parcelas.")
    iguais = [x for x in d.get("lancamentos", []) if not x.get("pulado") and x.get("data") == data.isoformat()
              and abs(calc.num(x.get("valor")) - valor) < 0.005 and _norm(x.get("descricao")) == _norm(desc)]
    novos = []
    if total:
        grupo = "g-" + integracao.uid()
        for p in range(atual, total + 1):
            dt = calc._data_mes(data.year, data.month + (p - atual), data.day).isoformat()
            novos.append(dict(base, id=integracao.uid(), data=dt, parcela=f"{p}/{total}", grupo=grupo, pago=False))
        novos[0]["pago"] = a["pago"] if isinstance(a.get("pago"), bool) else _pago_pela_data(d, novos[0], hoje)
    else:
        l = dict(base, id=integracao.uid(), data=data.isoformat())
        l["pago"] = a["pago"] if isinstance(a.get("pago"), bool) else _pago_pela_data(d, l, hoje)
        novos.append(l)
    d["lancamentos"].extend(novos)
    if len(novos) == 1:
        txt = "Lançado: " + _descrever(d, novos[0], contas) + f". id: {novos[0]['id']}"
    else:
        txt = (f"Lançadas {len(novos)} parcelas de {_brl(valor)} ({novos[0]['parcela']} a {novos[-1]['parcela']}), de "
               f"{_dm(novos[0]['data'])} a {_dm(novos[-1]['data'])}. A primeira: " + _descrever(d, novos[0], contas)
               + ". ids: " + ", ".join(x["id"] for x in novos))
    if iguais:
        txt += f"\nAtenção: já havia um lançamento igual (id {iguais[0].get('id')}). Se foi engano, apague um deles."
    return txt


def _achar_lanc(d, lid):
    lid = str(lid or "").strip()
    if not lid:
        raise ErroFerramenta("Falta o id.")
    if lid.startswith("f:"):
        raise ErroFerramenta("Isso é uma fatura de cartão: mude as compras dela, uma a uma.")
    try:
        return integracao._achar(d, lid)
    except LookupError:
        raise ErroFerramenta(f"Não encontrei o lançamento {lid}. Busque o id com gerencia_lancamentos.") from None
    except ValueError:
        raise ErroFerramenta(f"Id inválido: {lid}.") from None


def _real(d, l):
    """O lançamento que fica nos dados: um fixo ainda não lançado vira lançamento daquele mês."""
    if l.get("virtual"):
        x = integracao._materializar(l, pago=False)
        d["lancamentos"].append(x)
        return x
    return l


def _editar(d, a, hoje):
    l = _achar_lanc(d, a.get("id"))
    contas = calc.mapa_contas(d)
    antes = _descrever(d, l, contas)
    novo = {}
    if "descricao" in a:
        novo["descricao"] = _texto(a["descricao"]) or l.get("descricao", "")
    if "valor" in a:
        novo["valor"] = _valor(a["valor"])
    if "data" in a:
        novo["data"] = _data(a["data"], hoje).isoformat()
    if "categoria" in a:
        novo["categoria"] = _categoria(d, a["categoria"], l.get("tipo", "despesa"))
    if "conta" in a:
        novo["conta"] = _conta(d, a["conta"])
    if "obs" in a:
        novo["obs"] = _texto(a["obs"], 500)
    if "pago" in a:
        novo["pago"] = a["pago"] is True
    if "cartao" in a or "conta" in novo:
        cartao = (a.get("cartao") if "cartao" in a else l.get("cartao")) is True and l.get("tipo") != "receita"
        conta = novo.get("conta", l.get("conta"))
        if cartao and not (contas.get(conta) or {}).get("cartao"):
            if "cartao" in a:
                raise ErroFerramenta("Essa conta não tem cartão de crédito.")
            cartao = False
        novo["cartao"] = cartao
    if not novo:
        raise ErroFerramenta("Diga o que muda (descricao, valor, data, categoria, conta, cartao, pago ou obs).")
    if l.get("pulado"):
        raise ErroFerramenta("Esse lançamento foi apagado deste mês.")
    x = _real(d, l)
    x.update(novo)
    if x.get("aporte"):
        x["cartao"] = False
    return f"Alterado: {_descrever(d, x, contas)}. Antes: {antes}. id: {x['id']}"


def _apagar(d, a, hoje):
    l = _achar_lanc(d, a.get("id"))
    txt = _descrever(d, l)
    if l.get("recorrencia"):  # num fixo, só o daquele mês: a ocorrência fica marcada como pulada (como no app)
        x = integracao._materializar(l, pulado=True) if l.get("virtual") else l
        if l.get("virtual"):
            d["lancamentos"].append(x)
        x["pulado"] = True
        return f"Apagado só deste mês (o fixo continua nos outros): {txt}"
    d["lancamentos"] = [x for x in d["lancamentos"] if x.get("id") != l.get("id")]
    return f"Apagado: {txt}"


def _marcar_pago(d, a, hoje):
    cid = str(a.get("id") or "").strip()
    pago = a.get("pago") is not False
    valor = _valor(a["valor"]) if a.get("valor") not in (None, "", 0) else None
    if cid.startswith("f:"):
        try:
            f = integracao._achar_fatura(d, cid)
        except (LookupError, ValueError):
            raise ErroFerramenta(f"Fatura não encontrada: {cid}. Veja em gerencia_contas_a_pagar.") from None
        if valor is not None:
            raise ErroFerramenta("Uma fatura se paga inteira (sem valor). Para mudar um valor, edite a compra.")
        integracao.pagar(d, cid, None, pago=pago)
        return f"{'Paga' if pago else 'Voltou para a pagar'}: {f['descricao']} · {_brl(f['valor'])} · vence {_dm(f['vencimento'])} ({f['itens']} compras)."
    l = _achar_lanc(d, cid)
    if l.get("pulado"):
        raise ErroFerramenta("Esse lançamento foi apagado deste mês.")
    if l.get("ajuste") or l.get("desconto"):
        raise ErroFerramenta("Esse lançamento não se paga.")
    x = integracao._marcar(d, l, pago, valor if pago else None)
    if x is None:
        return f"Já estava a pagar: {_descrever(d, l)}."
    return ("Marcado: " if pago else "Desfeito: ") + _descrever(d, x) + f". id: {x['id']}"


def _definir_valor(inv, novo, data, ind, corrigir, hoje):
    """definirValor do app.js: um bem separado por categoria divide o valor novo na proporção de hoje."""
    novo = round(novo, 2)
    if inv.get("tipo") == "bens" and isinstance(inv.get("partes"), list) and inv["partes"]:
        ps = calc.partes_hoje(inv, ind, corrigir, hoje)
        tot = sum(p["valor"] for p in ps)
        resto, partes = novo, []
        for k, p in enumerate(inv["partes"]):
            v = resto if k == len(ps) - 1 else (round(ps[k]["valor"] * novo / tot, 2) if tot > 0 else 0)
            resto = round(resto - v, 2)
            partes.append(dict(p, valor=v))
        inv["partes"] = partes
    inv.update(valor=novo, data_valor=data.isoformat(), atualizado_em=datetime.now().isoformat(timespec="seconds"))


def _atualizar_inv(d, a, hoje):
    iid = str(a.get("id") or "").strip()
    inv = next((i for i in d.get("investimentos", []) if i.get("id") == iid), None)
    if not inv:
        raise ErroFerramenta(f"Investimento não encontrado: {iid}. Veja os ids em gerencia_investimentos.")
    dados = [k for k in ("saldo", "aporte", "resgate") if a.get(k) is not None]
    if len(dados) != 1:
        raise ErroFerramenta("Mande um só: saldo (o de agora), aporte ou resgate.")
    ind, corrigir = d.get("indices", {}), d.get("ajustes", {}).get("corrigir", True)
    antes = round(calc.valor_hoje(inv, ind, corrigir, hoje), 2)
    k = dados[0]
    v = _valor(a[k], k, zero=k == "saldo")
    novo = v if k == "saldo" else antes + v if k == "aporte" else antes - v
    if novo < 0:
        raise ErroFerramenta(f"O resgate é maior que o valor de hoje ({_brl(antes)}).")
    _definir_valor(inv, novo, hoje, ind, corrigir, hoje)
    dif = round(novo - antes, 2)
    obs = "sem mudança" if abs(dif) < 0.005 else f"{'aporte' if dif > 0 else 'resgate'} de {_brl(abs(dif))}"
    return f"Atualizado: {inv.get('nome', '')}: {_brl(antes)} → {_brl(novo)} ({obs})."


def _novo_inv(d, a, hoje):
    nome = _texto(a.get("nome"), 80)
    if not nome:
        raise ErroFerramenta("Falta o nome.")
    tipo = a.get("tipo")
    if tipo not in TIPOS_INV:
        raise ErroFerramenta("Tipo inválido. Use: " + ", ".join(TIPOS_INV) + ".")
    _, idx_p, taxa_p, liq_p = TIPOS_INV[tipo]
    idx = a.get("indexador") or idx_p
    if idx not in INDEXADORES:
        raise ErroFerramenta("Rendimento inválido. Use: " + ", ".join(INDEXADORES) + ".")
    taxa = 0 if idx in ("poupanca", "parado") else (calc.num(a.get("taxa")) if a.get("taxa") is not None else (taxa_p if idx == idx_p else 0))
    liq = a.get("liquidez") if a.get("liquidez") in ("diaria", "vencimento") else liq_p
    venc = _data(a.get("vencimento"), hoje, "vencimento").isoformat() if a.get("vencimento") else None
    valor = _valor(a.get("valor"), zero=True)
    banco_nome = _texto(a.get("banco"), 60)
    b = None
    if banco_nome:
        n = _norm(banco_nome)
        b = next((x for x in d["bancos"] if _norm(x.get("nome")) == n), None) or \
            next((x for x in d["bancos"] if _norm(x.get("nome")) and (_norm(x.get("nome")) in n or n in _norm(x.get("nome")))), None)
        if not b:
            usadas = {x.get("cor") for x in d["bancos"]}
            b = {"id": "b-" + integracao.uid(), "nome": banco_nome, "cor": next((c for c in CORES_BANCO if c not in usadas), CORES_BANCO[0]),
                 "obs": "", "contas": []}
            d["bancos"].append(b)
    dono = _texto(a.get("de_quem"), 60)
    if _norm(dono) in ("meu", "minha", "eu", "proprio", "propria"):
        dono = ""
    agora = datetime.now().isoformat(timespec="seconds")
    inv = {"id": integracao.uid(), "nome": nome, "banco": b["id"] if b else "", "tipo": tipo, "valor": valor, "data_valor": hoje.isoformat(),
           "indexador": idx, "taxa": taxa, "liquidez": liq, "vencimento": venc, "titular": "terceiros" if dono else "meu", "terceiro": dono,
           "obs": "", "fotos": [], "criado_em": agora, "atualizado_em": agora}
    d["investimentos"].append(inv)
    return (f"Cadastrado: {nome}{' · ' + b['nome'] if b else ''} · {TIPOS_INV[tipo][0]} · {calc.rotulo_taxa(inv)} · {_brl(valor)}"
            + (f" · vence {_dm(venc)}" if venc else "") + (f" · de {dono}" if dono else "") + f". id: {inv['id']}")


def _novo_fixo(d, a, hoje):
    tipo = a.get("tipo")
    if tipo not in ("despesa", "receita"):
        raise ErroFerramenta("tipo: despesa (gasto) ou receita (recebimento).")
    desc = _texto(a.get("descricao"))
    if not desc:
        raise ErroFerramenta("Falta a descrição.")
    valor = _valor(a.get("valor"))
    data = _data(a.get("data"), hoje, padrao=False)
    cat = _categoria(d, a.get("categoria"), tipo)
    conta = _conta(d, a.get("conta"))
    cartao = tipo == "despesa" and a.get("cartao") is True
    if cartao and not (calc.mapa_contas(d).get(conta) or {}).get("cartao"):
        raise ErroFerramenta("Essa conta não tem cartão de crédito." if conta else "Diga a conta do cartão de crédito.")
    anual = a.get("repete") == "anual"
    r = {"id": "r-" + integracao.uid(), "tipo": tipo, "descricao": desc, "valor": valor, "categoria": cat, "conta": conta, "cartao": cartao,
         "obs": "", "dia": data.day, "inicio": data.isoformat()[:7], "fim": None}
    if anual:
        r["freq"] = "anual"
    if tipo == "despesa" and cat == "c-investimentos":
        r.update(aporte=True, cartao=False)
    d["recorrencias"].append(r)
    quando = f"todo ano em {data.day:02d}/{data.month:02d}" if anual else f"todo dia {data.day}"
    return (f"Fixo cadastrado: {desc} · {_brl(valor)} · {quando}, a partir de {_dm(data.isoformat())}"
            + (f" · {_nome_cat(d, cat)}" if cat else "") + f". O deste mês: id v:{r['id']}:{data.isoformat()[:7]}.")


# ---------------------------------------------------------------- chamar

def chamar(nome, argumentos, d, hoje=None):
    """Roda a ferramenta nos dados d (as de gravar mudam d). Devolve (texto para a IA, mudou)."""
    hoje = hoje or date.today()
    f = POR_NOME.get(str(nome or ""))
    if not f:
        raise LookupError(f"Ferramenta desconhecida: {nome}.")
    a = argumentos if isinstance(argumentos, dict) else {}
    for k in ("lancamentos", "recorrencias", "investimentos", "bancos", "categorias"):
        d.setdefault(k, [])
    if nome == "resumo":
        return chat.resumo(d, hoje), False
    if nome == "lancamentos":
        return _lancamentos(d, a, hoje), False
    if nome == "contas_a_pagar":
        return _contas_a_pagar(d, a, hoje), False
    if nome == "investimentos":
        return _investimentos(d, hoje), False
    if nome == "cadastros":
        return _cadastros(d), False
    faz = {"lancar": _lancar, "editar_lancamento": _editar, "apagar_lancamento": _apagar, "marcar_pago": _marcar_pago,
           "atualizar_investimento": _atualizar_inv, "novo_investimento": _novo_inv, "novo_fixo": _novo_fixo}[nome]
    return faz(d, a, hoje), True
