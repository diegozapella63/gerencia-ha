"""Avisos no celular (Mais › Configurações › Opções › Dicas de economia › Avisar no celular), como o aviso de prazos do
ResolvIA: o app olha para a pessoa, nunca para um aparelho escolhido aqui. Os celulares de uma pessoa são os apps do
Home Assistant (no celular ou no relógio) entre os rastreadores dela (Configurações › Pessoas); o serviço de aviso de
cada um (notify.mobile_app_*) tem o nome do aparelho, não o do rastreador (device_tracker.meu_celular pode ser
notify.mobile_app_pixel_8). A mesma regra do phones.js do ResolvIA e da CronologIA. Só biblioteca padrão do Python.
"""
import os
import re
import time
import unicodedata

PESSOA_RE = re.compile(r"^person\.[a-z0-9_]+$")
CELULAR_RE = re.compile(r"^mobile_app_[a-z0-9_]+$")
CACHE_S = 60


def slug(s):
    """Como o Home Assistant nomeia as coisas: "Relógio Davi" -> "relogio_davi"."""
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def aparelhos(entidades, dispositivos):
    """O aparelho de cada rastreador, pelos registros: {entity_id: {"nome", "app"} ou None}. app: é um aparelho com
    o app Home Assistant. Sem os registros (None), devolve None."""
    if not isinstance(entidades, dict) or not isinstance(entidades.get("entities"), list) or not isinstance(dispositivos, list):
        return None
    por_id = {x.get("id"): x for x in dispositivos if isinstance(x, dict)}
    out = {}
    for e in entidades["entities"]:
        ei = str((e or {}).get("ei") or "")
        if not ei.startswith("device_tracker."):
            continue
        dv = por_id.get(e.get("di")) if e.get("di") else None
        out[ei] = {"nome": dv.get("name") or "", "app": any(isinstance(i, list) and i[:1] == ["mobile_app"] for i in dv.get("identifiers") or [])} if dv else None
    return out


def celulares(rastreadores, servicos, aparelhos_=None):
    """Os serviços de aviso (mobile_app_*, os que existem em notify) destes rastreadores: pelo nome do aparelho do app
    Home Assistant; um rastreador de outro tipo (o roteador, uma câmera) não é celular. Sem os registros, ou um
    rastreador fora deles, pelo id do rastreador (device_tracker.pixel_8 -> mobile_app_pixel_8)."""
    out = []
    for t in rastreadores if isinstance(rastreadores, list) else []:
        t = str(t)
        pelo_id = "mobile_app_" + re.sub(r"^device_tracker\.", "", t)
        cands = [pelo_id]
        if aparelhos_ is not None and t in aparelhos_:
            a = aparelhos_[t]
            cands = ["mobile_app_" + slug(a["nome"]), pelo_id] if a and a["app"] else []
        alvo = next((c for c in cands if c in servicos), None)
        if alvo and alvo not in out:
            out.append(alvo)
    return out


def endereco_app(host=None):
    """O endereço deste app no Home Assistant, para o toque no aviso abrir o app: /app/<slug> desde o HA 2026.2.
    Hostname a1b2c3d4-gerencia -> /app/a1b2c3d4_gerencia; fora do Home Assistant, None. É também o caminho do Atalho no
    celular (Configurações › Opções); GERENCIA_HOST troca o nome do contêiner (testes)."""
    host = host if host is not None else (os.environ.get("GERENCIA_HOST") or os.uname().nodename)
    return "/app/" + host.replace("-", "_", 1) if re.fullmatch(r"[a-z0-9]+-gerencia", host or "") else None


def texto_faturas(itens):
    """O aviso das faturas que chegaram por e-mail e já foram lidas: "📧 Fatura do e-mail" e uma linha por fatura."""
    linhas = [f"• {x['de']}: {x['resumo']}" for x in itens[:5]]
    if len(itens) > 5:
        linhas.append(f"e mais {len(itens) - 5}")
    return {"title": "📧 Fatura do e-mail para conferir" if len(itens) == 1 else f"📧 Faturas do e-mail para conferir: {len(itens)}",
            "message": "\n".join(linhas)}


def texto_dicas(dicas):
    """O aviso: "💡 Dica de economia" e uma linha por dica (até 5), com quanto economiza por ano no plano anual."""
    from calc import fmt_brl  # noqa: PLC0415  (calc fica ao lado; evita importar no topo para os testes deste módulo)
    linhas = [f"• {x['nome']}: {fmt_brl(x['real'], 0)} por ano no plano anual" for x in dicas[:5]]
    if len(dicas) > 5:
        linhas.append(f"e mais {len(dicas) - 5}")
    return {"title": "💡 Dica de economia" if len(dicas) == 1 else f"💡 Dicas de economia: {len(dicas)}", "message": "\n".join(linhas)}


def texto_oportunidades(linhas):
    """O aviso: "📈 Oportunidade de investimento" e uma linha por oportunidade (até 5), já escritas
    (oportunidades.linha_aviso: "Tesouro IPCA+ 2032: IPCA + 7,82%")."""
    corpo = [f"• {x}" for x in linhas[:5]]
    if len(linhas) > 5:
        corpo.append(f"e mais {len(linhas) - 5}")
    return {"title": "📈 Oportunidade de investimento" if len(linhas) == 1 else f"📈 Oportunidades de investimento: {len(linhas)}",
            "message": "\n".join(corpo)}



APP_AVISO, ICONE_AVISO = "GerencIA", "mdi:wallet-outline"


def titulo_do_app(titulo):
    """O título do aviso com o nome do app na frente (uma vez só)."""
    t = str(titulo or "").strip()
    return t if t.startswith(APP_AVISO + " · ") else f"{APP_AVISO} · {t}" if t else APP_AVISO

class Avisos:
    """As pessoas da casa e os celulares delas, e o envio do aviso. rest(metodo, caminho, corpo) fala com a API REST
    do Home Assistant; ws(comando) faz uma pergunta à API WebSocket (os registros de entidades e aparelhos)."""

    def __init__(self, rest, ws, log):
        self.rest, self.ws, self.log = rest, ws, log
        self.cache = None  # (quando, pessoas)

    def pessoas(self, forcar=False):
        """[{"id": "person.ana", "nome", "user_id", "celulares": [...]}], pelo nome."""
        if not forcar and self.cache and time.time() - self.cache[0] < CACHE_S:
            return self.cache[1]
        estados = self.rest("GET", "/states") or []
        servicos = set()
        for dom in self.rest("GET", "/services") or []:
            if isinstance(dom, dict) and dom.get("domain") == "notify":
                servicos = {k for k in (dom.get("services") or {}) if CELULAR_RE.match(k)}
        try:
            ap = aparelhos(self.ws({"type": "config/entity_registry/list_for_display"}), self.ws({"type": "config/device_registry/list"}))
        except Exception as e:  # noqa: BLE001  (sem os registros: pelo id do rastreador)
            self.log("Avisos: sem os registros do Home Assistant:", e)
            ap = None
        out = []
        for st in estados:
            ei = str((st or {}).get("entity_id") or "")
            if not PESSOA_RE.match(ei):
                continue
            a = st.get("attributes") or {}
            out.append({"id": ei, "nome": a.get("friendly_name") or ei[7:], "user_id": a.get("user_id"),
                        "celulares": celulares(a.get("device_trackers"), servicos, ap)})
        out.sort(key=lambda p: slug(p["nome"]))
        self.cache = (time.time(), out)
        return out

    def enviar(self, alvos, texto, tag, grupo="gerencia-dicas", canal="Dicas de economia", caminho=""):
        """Manda o aviso para estes celulares (notify.mobile_app_*); devolve quantos o Home Assistant aceitou. grupo e
        canal separam os avisos no Android (as dicas de um lado, as faturas do e-mail do outro); caminho: a tela que o
        toque abre (/oportunidades, que a tela recebe do Home Assistant). Como em todos os apps da família, o título
        começa pelo nome do app ("GerencIA · 💡 Dica de economia") e o ícone pequeno é o do app: no celular, todos
        chegam como Home Assistant."""
        url = endereco_app()
        url = url + caminho if url else None
        dados = {"tag": tag, "group": grupo, "channel": canal, "notification_icon": ICONE_AVISO, **({"url": url, "clickAction": url} if url else {})}
        n = 0
        for alvo in alvos:
            try:
                self.rest("POST", f"/services/notify/{alvo}", {"title": titulo_do_app(texto["title"]), "message": texto["message"], "data": dados})
                n += 1
                self.log(f"Aviso ({canal}) para {alvo}")
            except Exception as e:  # noqa: BLE001
                self.log(f"Aviso ({canal}) para {alvo}:", e)
        return n
