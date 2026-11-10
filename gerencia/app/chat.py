"""Conversar com a IA (o balão ao lado do microfone): o resumo dos dados que a IA recebe, as instruções, as ações
que ela propõe (a pessoa confirma na tela) e a conversa guardada (as últimas mensagens, em /data/chat.json).

A IA é a mesma da leitura (ação ai_task.generate_data do Home Assistant); o server.py chama, limpa as ações com as
mesmas regras da leitura por IA e grava. Aqui só biblioteca padrão e nada de rede."""
import json
import re
import secrets
import threading
from datetime import date, datetime, timedelta

import calc
import integracao

MAX_GUARDADAS = 60   # mensagens que ficam guardadas
MAX_HISTORICO = 16   # as últimas que vão para a IA, para ela lembrar da conversa
MAX_TEXTO = 2000     # uma mensagem da pessoa
MAX_TELA = 3000      # o texto da tela que a pessoa está vendo
MAX_RESPOSTA = 4000
GRUPOS = ("lancamentos", "investimentos", "pagar")
ESTADOS = ("feito", "dispensado")
DIAS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")
ABAS = {"inicio": "Início", "caixa": "Caixa", "investimentos": "Investimentos", "mais": "Mais"}


def uid():
    return secrets.token_hex(6)


def agora():
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------- a conversa guardada

class Conversa:
    """As mensagens: {id, papel: "eu" | "ia", texto, em, fala?, acoes?: {lancamentos, investimentos, pagar}, estado?: {grupo: feito|dispensado}}."""

    def __init__(self, arquivo, gravar):
        self.arquivo = arquivo
        self.gravar = gravar  # gravar(caminho, texto): a gravação segura do server.py
        self.trava = threading.Lock()

    def ler(self):
        try:
            with open(self.arquivo, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            return []
        m = d.get("mensagens") if isinstance(d, dict) else None
        return [x for x in m if isinstance(x, dict) and x.get("papel") in ("eu", "ia")] if isinstance(m, list) else []

    def salvar(self, mensagens):
        mensagens = mensagens[-MAX_GUARDADAS:]
        self.gravar(self.arquivo, json.dumps({"mensagens": mensagens}, ensure_ascii=False))
        return mensagens

    def acrescentar(self, *novas):
        with self.trava:
            return self.salvar(self.ler() + list(novas))

    def limpar(self):
        with self.trava:
            return self.salvar([])

    def marcar(self, mid, chave, estado):
        """Uma ação confirmada (feito) ou deixada de lado (dispensado): o cartão dela muda na conversa.
        chave: "lancamentos" e "investimentos" (um cartão para o grupo) ou "pagar.<n>" (um cartão por conta)."""
        m_ch = re.fullmatch(r"(lancamentos|investimentos)|pagar\.(\d{1,2})", str(chave or ""))
        if not m_ch or estado not in ESTADOS:
            raise ValueError("Ação inválida.")
        grupo = m_ch.group(1) or "pagar"
        with self.trava:
            msgs = self.ler()
            m = next((x for x in msgs if x.get("id") == mid and x.get("papel") == "ia"), None)
            lista = (m.get("acoes") or {}).get(grupo) if m else None
            if not lista or (m_ch.group(2) is not None and int(m_ch.group(2)) >= len(lista)):
                raise LookupError("Essa mensagem não está mais na conversa.")
            m.setdefault("estado", {})[chave] = estado
            return self.salvar(msgs)


# ---------------------------------------------------------------- o que a IA sabe dos dados

def _brl(v):
    return calc.fmt_brl(v)


def contas_a_pagar(d, hoje):
    """Do jeito do CronologIA (o mesmo id serve para pagar): atrasadas dos últimos 2 meses e as dos próximos 45 dias."""
    try:
        return integracao.listar(d, hoje, hoje + timedelta(days=45), hoje)["contas"]
    except (ValueError, KeyError, TypeError):
        return []


def resumo(d, hoje=None):
    hoje = hoje or date.today()
    contas = calc.mapa_contas(d)
    cats = {c.get("id"): c.get("nome", "") for c in d.get("categorias", [])}
    L = [f"Hoje é {DIAS[hoje.weekday()]}, {hoje:%d/%m/%Y}."]

    if contas:
        L.append("\nContas no banco (id | banco · pessoa | cartão de crédito):")
        for cid, c in contas.items():
            cart = f"cartão, fecha dia {c.get('fechamento')}, vence dia {c.get('vencimento')}" if c.get("cartao") else "sem cartão"
            L.append(f"{cid} | {calc.nome_conta(c) or c.get('banco_nome', '')} | {cart}")

    cx = calc.caixa(d, hoje)
    L.append(f"\nCaixa: saldo de hoje {_brl(cx['saldo'])}. Neste mês: entrou {_brl(cx['entrou_mes'])}, saiu {_brl(cx['saiu_mes'])}, "
             f"a receber {_brl(cx['a_receber_mes'])}, a pagar {_brl(cx['a_pagar_mes'])}. Atrasado: {_brl(cx['atrasado'])}.")

    ap = contas_a_pagar(d, hoje)
    if ap:
        L.append("\nContas a pagar (id | descrição | valor | vencimento | situação):")
        for c in ap[:60]:
            sit = "paga" if c["pago"] else "ATRASADA" if c.get("atrasada") else "a pagar"
            L.append(f"{c['id']} | {c['descricao']} | {_brl(c['valor'])} | {c['vencimento']} | {sit}")

    desde = (hoje - timedelta(days=45)).isoformat()
    lanc = sorted((l for l in d.get("lancamentos", []) if not l.get("pulado") and str(l.get("data") or "") >= desde),
                  key=lambda l: str(l.get("data") or ""), reverse=True)
    if lanc:
        L.append("\nLançamentos dos últimos 45 dias e os já lançados para a frente (data | tipo | descrição | valor | categoria | situação | conta):")
        for l in lanc[:80]:
            rec = l.get("tipo") == "receita"
            sit = ("recebido" if rec else "pago") if l.get("pago") else ("a receber" if rec else "a pagar")
            conta = calc.nome_conta(contas.get(l.get("conta"))) + (" (cartão)" if l.get("cartao") else "")
            tipo = "aporte" if l.get("aporte") else "recebimento" if rec else "gasto"
            L.append(f"{l.get('data')} | {tipo} | {l.get('descricao', '')} | {_brl(calc.num(l.get('valor')))} | {cats.get(l.get('categoria'), '')} | {sit} | {conta}")

    fixos = [r for r in d.get("recorrencias", []) if not r.get("fim") or str(r.get("fim")) >= hoje.isoformat()[:7]]
    if fixos:
        L.append("\nFixos (descrição | tipo | valor | quando | categoria):")
        for r in fixos[:40]:
            quando = f"todo ano, dia {r.get('dia')}/{str(r.get('inicio') or '')[5:7]}" if r.get("freq") == "anual" else f"todo dia {r.get('dia')}"
            tipo = "aporte" if r.get("aporte") else "recebimento" if r.get("tipo") == "receita" else "gasto"
            L.append(f"{r.get('descricao', '')} | {tipo} | {_brl(calc.num(r.get('valor')))} | {quando} | {cats.get(r.get('categoria'), '')}")

    invs = d.get("investimentos", [])
    if invs:
        bancos = {b.get("id"): b.get("nome", "") for b in d.get("bancos", [])}
        ind, corrigir = d.get("indices", {}), d.get("ajustes", {}).get("corrigir", True)
        L.append("\nInvestimentos (id | nome | banco | de quem | valor hoje | rendimento | vencimento | liquidez):")
        for i in invs[:80]:
            de = "meu" if i.get("titular") != "terceiros" else (i.get("terceiro") or "terceiros")
            L.append(f"{i.get('id')} | {i.get('nome', '')} | {bancos.get(i.get('banco'), '')} | {de} | {_brl(calc.valor_hoje(i, ind, corrigir, hoje))} | "
                     f"{calc.rotulo_taxa(i)} | {i.get('vencimento') or '-'} | {'diária' if i.get('liquidez') == 'diaria' else 'no vencimento'}")
        t = calc.totais(d, hoje)
        L.append(f"Patrimônio: meu {_brl(t['meu'])}, de outras pessoas {_brl(t['terceiros'])}, total {_brl(t['total'])}; rende uns {_brl(t['rende_mes'])} por mês.")
        ix = d.get("indices", {})
        L.append(f"Índices ao ano: CDI {calc.fmt_pct(ix.get('cdi', 0))}%, Selic {calc.fmt_pct(ix.get('selic', 0))}%, IPCA {calc.fmt_pct(ix.get('ipca', 0))}%.")

    metas = [m for m in d.get("metas", []) if isinstance(m, dict)] + calc.metas_conta(d)
    if metas:  # Mais › Benefícios › Oportunidades: o que falta para ganhar mais (o mesmo da tela)
        L.append("\nOportunidades nos benefícios (o que ganha | de onde | condição | situação):")
        for m in metas[:30]:
            pr = calc.progresso_meta(m, d, hoje)
            cond = (f"{_brl(pr['pede'])} investidos" if m.get("tipo") == "investido" else f"gastar {_brl(pr['pede'])} por mês no cartão"
                    if m.get("tipo") == "gasto" else f"plano {m.get('plano') or ''} de {_brl(pr['pede'])} por mês".replace("  ", " "))
            sit = ("sem como saber" if pr["sem"] else "já dá" if pr["ja"] else f"custa {_brl(pr['falta'])} a mais por mês" if m.get("tipo") == "plano"
                   else f"faltam {_brl(pr['falta'])} (tem {_brl(pr['tem'])}{' de média' if m.get('tipo') == 'gasto' else ''})")
            nome = ("nível " if m.get("nivel") else "") + str(m.get("ganha") or "")
            L.append(f"{nome} | {calc.origem_beneficio(m, d, hoje)['nome']} | {cond} | {sit}")

    if cats:
        L.append("\nCategorias (id: nome, tipo): " + "; ".join(f"{c.get('id')}: {c.get('nome', '')}, {c.get('tipo', 'despesa')}" for c in d.get("categorias", [])))
    return "\n".join(L)


REGRAS_ACOES = """Ações: quando a pessoa pedir para lançar um gasto ou um recebimento, pagar uma conta, atualizar o saldo de um investimento ou aplicar num investimento, proponha a ação. O app mostra a ação para ela conferir e confirmar: nada é feito sem o toque dela. Não proponha ação que ela não pediu, e diga na resposta, numa frase, o que vai ficar para ela confirmar.
- "lancamentos": cada gasto ou recebimento para lançar, com "tipo" ("despesa" ou "receita"), "descricao" (curta, como a pessoa escreveria), "valor" (número positivo; em parcelas, o valor da parcela), "data" (AAAA-MM-DD; sem data, hoje; "ontem" e "amanhã" pela data de hoje), "categoria" (um id da lista de categorias, do mesmo tipo), "parcela_atual" e "parcelas_total" (números, só em compra parcelada; senão 0), "cartao" (true se foi no cartão de crédito), "banco" (o banco citado ou ""), "situacao" ("feito" se já foi pago ou recebido, "pendente" se ainda vai pagar ou receber).
- "pagar": cada conta da lista de contas a pagar que ela disse que pagou, com "id" (exatamente o id da lista) e "valor" (o que ela pagou, se disse um valor diferente; senão 0). Uma conta que já está na lista se paga por aqui, não se lança de novo.
- "investimentos": cada saldo novo ou aplicação, com "existente" (o id da lista de investimentos, se for um deles; senão ""), "valor" (o saldo de agora, se ela disse; senão 0), "aporte" (quanto aplicou agora; senão 0) e, só para um investimento novo, "nome", "banco", "tipo" (cdb, lci, tesouro, poupanca, caixinha, fundo, acoes, ouro, dinheiro, previdencia, outro), "indexador" (cdi_pct, cdi_mais, pre, ipca_mais, selic_mais, poupanca, estimado, parado), "taxa", "vencimento" (AAAA-MM-DD ou "") e "liquidez" ("diaria" ou "vencimento"), e "dono" ("" se for da própria pessoa)."""


WHATSAPP = """Você responde pelo WhatsApp da CorrerIA Code, o contato dos apps da casa (o GerencIA é o das finanças). Converse em português do Brasil, curto e direto, como no WhatsApp: frases simples, no máximo uns 4 parágrafos curtos. Formatação do WhatsApp: *negrito* com um asterisco de cada lado e listas com "- "; nada de tabelas, títulos nem links. Valores como R$ 1.234,56 e datas como 20/11.
Responda sobre as finanças da casa com os dados abaixo. Não invente números: se faltar o dado, diga o que falta. Contas de cabeça podem errar: some e compare com cuidado.
Por aqui você só ajuda com as finanças e os apps da casa: para qualquer outro assunto, diga numa frase, com gentileza, que pelo WhatsApp você ajuda só com os apps da CorrerIA Code.
Pelo WhatsApp ainda não dá para lançar, pagar nem mudar um saldo: se a pessoa pedir, diga que por enquanto isso é no app GerencIA (o botão Conversar com a IA faz isso com um toque)."""


# a conversa na tela do CorrerIA (o app que junta os apps da casa): sem a regra do WhatsApp sobre outros assuntos
CORRERIA = """Você responde pela conversa do CorrerIA, o app que junta os apps da casa (o GerencIA é o das finanças). Converse em português do Brasil, curto e direto, como num chat de celular: frases simples, no máximo uns 4 parágrafos curtos. Formatação: *negrito* com um asterisco de cada lado e listas com "- "; nada de tabelas, títulos nem links. Valores como R$ 1.234,56 e datas como 20/11.
Responda sobre as finanças da casa com os dados abaixo. Não invente números: se faltar o dado, diga o que falta. Contas de cabeça podem errar: some e compare com cuidado. Também pode conversar sobre outros assuntos.
Por aqui ainda não dá para lançar, pagar nem mudar um saldo: se a pessoa pedir, diga que isso é no app GerencIA (o botão Conversar com a IA faz isso com um toque)."""


def instrucoes_whatsapp(d, historico, usuario="", hoje=None, canal="whatsapp"):
    """O pedido para a IA quando a pergunta vem pelo CorrerIA: pelo WhatsApp (só sobre os apps, a regra da Meta) ou
    pela conversa na tela dele (canal correria). Só responde, sem ações."""
    hoje = hoje or date.today()
    nome = (usuario or "").split(" ")[0]
    partes = [(CORRERIA if canal == "correria" else WHATSAPP) + (f"\nQuem está conversando: {nome}." if nome else ""),
              "Dados do app:\n" + resumo(d, hoje)]
    conversa = [("IA: " if m.get("papel") == "ia" else "Pessoa: ") + str(m.get("texto") or "").strip()[:MAX_TEXTO]
                for m in historico[-MAX_HISTORICO:] if str(m.get("texto") or "").strip()]
    partes.append("A conversa (a última mensagem é a que você responde agora):\n" + "\n".join(conversa))
    partes.append('Responda somente com JSON válido, sem markdown e sem texto antes ou depois, neste formato:\n{"resposta":""}')
    return "\n\n".join(partes)


def instrucoes(d, historico, tela="", aba="", usuario="", hoje=None):
    """O pedido para a IA: quem ela é, a tela que a pessoa vê, os dados, as ações e a conversa (a última mensagem é a pergunta)."""
    hoje = hoje or date.today()
    nome = (usuario or "").split(" ")[0]
    partes = [
        f"Você é a IA do GerencIA, o app das finanças da casa{' de ' + nome if nome else ''}, no Brasil, dentro do Home Assistant. "
        "Converse em português do Brasil, curto e direto, como num chat de celular: frases simples, no máximo uns 5 parágrafos curtos. "
        "Pode usar **negrito** e listas com \"- \"; nada de tabelas nem títulos. Valores como R$ 1.234,56 e datas como 20/11.",
        "Responda sobre as finanças com os dados abaixo. Não invente números: se faltar o dado, diga o que falta. "
        "Contas de cabeça podem errar: some e compare com cuidado. Também pode conversar sobre qualquer outro assunto.",
    ]
    tela = (tela or "").strip()[:MAX_TELA]
    if tela:
        partes.append(f"A pessoa está na tela {ABAS.get(aba, aba or 'do app')}. O que aparece nela agora:\n<<<\n{tela}\n>>>")
    partes.append("Dados do app:\n" + resumo(d, hoje))
    partes.append(REGRAS_ACOES)
    conversa = []
    for m in historico[-MAX_HISTORICO:]:
        txt = str(m.get("texto") or "").strip()
        if m.get("papel") == "ia":
            feitos = _resumo_acoes(m)
            conversa.append("IA: " + txt + (f" [{feitos}]" if feitos else ""))
        else:
            conversa.append("Pessoa: " + txt)
    partes.append("A conversa (a última mensagem é a que você responde agora):\n" + "\n".join(conversa))
    partes.append('Responda somente com JSON válido, sem markdown e sem texto antes ou depois, neste formato:\n'
                  '{"resposta":"","lancamentos":[],"pagar":[],"investimentos":[]}')
    return "\n\n".join(partes)


def _resumo_acoes(m):
    a, e = m.get("acoes") or {}, m.get("estado") or {}
    nomes = {"lancamentos": "lançar", "pagar": "pagar", "investimentos": "investimentos"}
    out = []
    for g in GRUPOS:
        if a.get(g):
            est = {"feito": "confirmado", "dispensado": "deixado de lado"}.get(e.get(g), "ainda sem confirmar")
            out.append(f"propôs {nomes[g]} ({len(a[g])}): {est}")
    return "; ".join(out)


def separar(parsed):
    """A resposta da IA em texto + ações cruas. Se ela respondeu só texto (sem JSON), o texto é a resposta."""
    if isinstance(parsed, str):
        return parsed.strip()[:MAX_RESPOSTA], {}
    p = parsed if isinstance(parsed, dict) else {}
    texto = str(p.get("resposta") or p.get("texto") or "").strip()[:MAX_RESPOSTA]
    return texto, {g: p.get(g) for g in GRUPOS if isinstance(p.get(g), list) and p.get(g)}


def limpar_pagar(lista, d, hoje=None):
    """Só contas que existem e ainda não foram pagas; leva junto o que o cartão mostra (nome, vencimento, valor)."""
    hoje = hoje or date.today()
    try:
        abertas = {c["id"]: c for c in integracao.listar(d, hoje - timedelta(days=62), hoje + timedelta(days=90), hoje)["contas"] if not c["pago"]}
    except (ValueError, KeyError, TypeError):
        abertas = {}
    out, vistos = [], set()
    for it in (lista or [])[:20]:
        if not isinstance(it, dict):
            continue
        c = abertas.get(str(it.get("id") or ""))
        if not c or c["id"] in vistos:
            continue
        vistos.add(c["id"])
        v = round(abs(calc.num_br(it.get("valor"))), 2)
        out.append({"id": c["id"], "descricao": c["descricao"], "vencimento": c["vencimento"], "valor_conta": c["valor"],
                    "valor": v if v > 0 else c["valor"], "tipo": c["tipo"]})
    return out


# ---------------------------------------------------------------- a IA simulada (testes e computador)

def _valor(t):
    m = re.search(r"(\d+(?:[.,]\d{1,2})?)\s*(mil\b|reais|real|r\$)?", t)
    if not m:
        return 0.0
    return calc.num_br(m.group(1)) * (1000 if m.group(2) == "mil" else 1)


def simulado(texto, d, hoje=None):
    """Respostas previsíveis para testar o caminho todo sem IA: pagar uma conta da lista, aplicar, saldo e um gasto."""
    hoje = hoje or date.today()
    t = (texto or "").lower()
    ap = [c for c in contas_a_pagar(d, hoje) if not c["pago"]]
    if re.search(r"\bpaguei\b", t):
        for c in ap:
            if c["descricao"].lower() in t:
                return {"resposta": f"Certo: marco **{c['descricao']}** como paga. Confira e confirme.", "pagar": [{"id": c["id"], "valor": _valor(t.split(c['descricao'].lower(), 1)[1]) or 0}]}
    if re.search(r"\b(apliquei|investi|guardei)\b", t):
        inv = next((i for i in d.get("investimentos", []) if any(w in t for w in re.findall(r"[a-zà-ú0-9]{3,}", str(i.get("nome", "")).lower()))), None)
        if inv:
            return {"resposta": f"Anotei o aporte em **{inv.get('nome')}**. Confira e confirme.", "investimentos": [{"existente": inv.get("id"), "valor": 0, "aporte": _valor(t)}]}
    m = re.search(r"\bsaldo d[oa] (.+?) (?:é|e|está|ta|tá) (?:de )?(\d[\d.,]*)", t)
    if m:
        inv = next((i for i in d.get("investimentos", []) if m.group(1).strip() in str(i.get("nome", "")).lower()), None)
        if inv:
            return {"resposta": f"Atualizo o saldo de **{inv.get('nome')}**. Confira e confirme.", "investimentos": [{"existente": inv.get("id"), "valor": calc.num_br(m.group(2))}]}
    if re.search(r"\b(gastei|comprei|paguei)\b", t) and _valor(t):
        desc = re.search(r"\b(?:no|na|em|de|do|da)\s+([a-zà-ú]+)", t)
        nome = (desc.group(1) if desc else "Gasto").capitalize()
        cat = "c-mercado" if "mercado" in t else "c-outros-gastos"
        return {"resposta": f"Lanço **{nome}**, {_brl(_valor(t))}. Confira e confirme.",
                "lancamentos": [{"tipo": "despesa", "descricao": nome, "valor": _valor(t), "data": hoje.isoformat(), "categoria": cat,
                                 "cartao": "cartão" in t or "cartao" in t, "situacao": "feito"}]}
    if re.search(r"patrim[oô]nio|investimentos?|investido", t):
        tt = calc.totais(d, hoje)
        return {"resposta": f"Seus investimentos somam **{_brl(tt['meu'])}** e rendem uns {_brl(tt['rende_mes'])} por mês."}
    if re.search(r"saldo|caixa|quanto (eu )?tenho", t):
        cx = calc.caixa(d, hoje)
        return {"resposta": f"O saldo do caixa hoje é **{_brl(cx['saldo'])}**. Neste mês entrou {_brl(cx['entrou_mes'])} e saiu {_brl(cx['saiu_mes'])}."}
    if re.search(r"vence|a pagar|\bcontas\b", t):
        if not ap:
            return {"resposta": "Não tem conta a pagar nos próximos dias."}
        linhas = "\n".join(f"- {c['descricao']}: {_brl(c['valor'])}, {c['vencimento'][8:10]}/{c['vencimento'][5:7]}" for c in ap[:5])
        return {"resposta": "As próximas contas:\n" + linhas}
    return {"resposta": "Posso responder sobre o seu caixa, as contas e os investimentos, lançar gastos, marcar contas pagas e atualizar saldos. Também converso sobre outros assuntos."}
