"""Conexão com outros apps do mesmo Home Assistant (hoje, o CronologIA).

O GerencIA grava em /share/gerencia/integracao.json o endereço dele na rede interna dos apps
e uma chave. Outro app com a pasta share lê o arquivo e chama /api/integracao/* com o
cabeçalho Authorization: Bearer <chave>. Quem já lê a pasta share também lê os backups do
GerencIA que ficam lá, então a chave não abre nada que já não estivesse aberto.

Rotas:
  GET  /api/integracao/contas?de=AAAA-MM-DD&ate=AAAA-MM-DD   contas a pagar (e pagas) no período
  POST /api/integracao/pagar     {id, valor?}                 dá baixa, como o "Paguei" do app
  POST /api/integracao/desfazer  {id}                         volta para "a pagar"
  POST /api/integracao/nova      {descricao, valor, vencimento, repete: nao|mensal|anual, categoria?}
"""
import hmac
import json
import os
import secrets
import socket
import time
from datetime import date, datetime, timedelta

import calc

MAX_DIAS = 400


def uid():
    return secrets.token_hex(4) + format(int(time.time() * 1000) % (36 ** 4), "x")


def add_ym(ym, k):
    a, m = int(ym[:4]), int(ym[5:7]) + k
    a += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return f"{a:04d}-{m:02d}"


# ---------------------------------------------------------------- chave e arquivo

class Conexao:
    def __init__(self, data_dir, share_dir, porta, versao, log):
        self.arq_chave = os.path.join(data_dir, "integracao.key")
        self.arq_share = os.path.join(share_dir, "integracao.json")
        self.porta = porta
        self.versao = versao
        self.log = log
        self.ultimo = None  # {"app": "CronologIA", "em": "..."}
        self._chave = None

    def chave(self):
        if self._chave:
            return self._chave
        try:
            with open(self.arq_chave, encoding="utf-8") as f:
                self._chave = f.read().strip()
        except OSError:
            self._chave = ""
        if len(self._chave) < 32:
            self._chave = secrets.token_urlsafe(32)
            os.makedirs(os.path.dirname(self.arq_chave), exist_ok=True)
            with open(self.arq_chave, "w", encoding="utf-8") as f:
                f.write(self._chave)
            os.chmod(self.arq_chave, 0o600)
        return self._chave

    def endereco(self):
        url = os.environ.get("GERENCIA_URL_INTERNA")
        if url:
            return url.rstrip("/"), None
        host = socket.gethostname()
        try:
            ip = socket.gethostbyname(host)
        except OSError:
            ip = None
        return f"http://{host}:{self.porta}", ip

    def publicar(self, ligado=True):
        """Grava (ou apaga, se desligado) o arquivo que os outros apps leem."""
        try:
            if not ligado:
                if os.path.exists(self.arq_share):
                    os.remove(self.arq_share)
                return
            url, ip = self.endereco()
            corpo = {"app": "gerencia", "versao": self.versao, "url": url,
                     "ip_url": f"http://{ip}:{self.porta}" if ip else None,
                     "chave": self.chave(), "gravado_em": datetime.now().isoformat(timespec="seconds")}
            os.makedirs(os.path.dirname(self.arq_share), exist_ok=True)
            tmp = self.arq_share + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(corpo, f, ensure_ascii=False, indent=1)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.arq_share)
        except OSError as e:
            self.log("Conexão com outros apps: não consegui gravar", self.arq_share, e)

    def autorizado(self, headers):
        h = headers.get("Authorization") or ""
        if not h.startswith("Bearer "):
            return False
        ok = hmac.compare_digest(h[7:].strip().encode(), self.chave().encode())
        if ok:
            self.ultimo = {"app": (headers.get("X-App") or "outro app")[:40],
                           "em": datetime.now().isoformat(timespec="seconds")}
        return ok


# ---------------------------------------------------------------- contas

def _nome_categoria(d, cid):
    for c in d.get("categorias", []):
        if c.get("id") == cid:
            return c.get("nome", "")
    return ""


def _ocorrencias(d, ym_ini, ym_fim):
    """Lançamentos e fixos (ainda não lançados) cuja data do caixa cai entre os dois meses."""
    contas = calc.mapa_contas(d)
    out = []
    for l in d.get("lancamentos", []):
        if l.get("pulado"):
            continue
        dc = calc.data_caixa(l, contas)
        if dc and ym_ini <= dc.isoformat()[:7] <= ym_fim:
            out.append(dict(l, dc=dc.isoformat()))
    feitos = {(l.get("recorrencia"), l.get("competencia")) for l in d.get("lancamentos", []) if l.get("recorrencia")}
    ym = add_ym(ym_ini, -2)  # o cartão empurra a saída até dois meses para frente
    while ym <= ym_fim:
        a, m = int(ym[:4]), int(ym[5:7])
        for r in d.get("recorrencias", []):
            if not r.get("id") or not calc.ativa_em(r, ym) or (r["id"], ym) in feitos:
                continue
            o = dict(r, id=f"v:{r['id']}:{ym}", virtual=True, recorrencia=r["id"], competencia=ym,
                     data=calc._data_mes(a, m, r.get("dia")).isoformat(), pago=False)
            for k in ("inicio", "fim", "dia"):
                o.pop(k, None)
            dc = calc.data_caixa(o, contas)
            if dc and ym_ini <= dc.isoformat()[:7] <= ym_fim:
                out.append(dict(o, dc=dc.isoformat()))
        ym = add_ym(ym, 1)
    return out


def _e_conta(l, aportes=frozenset()):
    # o aporte mensal nos investimentos não é conta a pagar (nem quando o mês foi editado e virou lançamento)
    return (l.get("tipo") != "receita" and not l.get("ajuste") and not l.get("desconto")
            and not l.get("vinculo") and not l.get("aporte") and l.get("recorrencia") not in aportes)


def _faturas_e_contas(d, lista):
    contas = calc.mapa_contas(d)
    aportes = frozenset(r.get("id") for r in d.get("recorrencias", []) if r.get("aporte"))
    faturas, avulsas = {}, []
    for l in lista:
        c = contas.get(l.get("conta")) if l.get("cartao") else None
        if c and c.get("cartao"):
            k = f"f:{l['conta']}|{l['dc']}"
            f = faturas.setdefault(k, {"id": k, "tipo": "fatura", "descricao": "Fatura " + calc.nome_conta(c),
                                       "valor": 0.0, "vencimento": l["dc"], "pago": True, "itens": 0,
                                       "categoria": "", "conta": calc.nome_conta(c), "_itens": []})
            f["valor"] += (-1 if l.get("tipo") == "receita" else 1) * calc.num(l.get("valor"))
            f["itens"] += 1
            f["_itens"].append(l)
            if not l.get("pago"):
                f["pago"] = False
            continue
        if not _e_conta(l, aportes):
            continue
        # o fixo do mês tem sempre o mesmo id, lançado ou não: "v:<fixo>:<mês>"
        fixo = l.get("recorrencia") and l.get("competencia")
        avulsas.append({"id": f"v:{l['recorrencia']}:{l['competencia']}" if fixo else l["id"],
                        "tipo": "fixo" if l.get("recorrencia") else "conta",
                        "descricao": l.get("descricao") or "Conta", "valor": round(calc.num(l.get("valor")), 2),
                        "vencimento": l["dc"], "pago": bool(l.get("pago")),
                        "categoria": _nome_categoria(d, l.get("categoria")),
                        "conta": calc.nome_conta(contas.get(l.get("conta")))})
    for f in faturas.values():
        f["valor"] = round(f["valor"], 2)
    return list(faturas.values()), avulsas


def listar(d, de, ate, hoje=None):
    hoje = hoje or date.today()
    if (ate - de).days > MAX_DIAS or ate < de:
        raise ValueError("Período inválido.")
    limite_atraso = hoje - timedelta(days=62)
    ini = min(de, limite_atraso)
    faturas, avulsas = _faturas_e_contas(d, _ocorrencias(d, ini.isoformat()[:7], ate.isoformat()[:7]))
    out = []
    for c in faturas + avulsas:
        c.pop("_itens", None)
        v = date.fromisoformat(c["vencimento"])
        atrasada = not c["pago"] and v < hoje
        if de <= v <= ate or (atrasada and v >= limite_atraso):
            c["atrasada"] = atrasada
            out.append(c)
    out.sort(key=lambda c: (c["vencimento"], c["descricao"]))
    categorias = [{"id": c.get("id"), "nome": c.get("nome", "")} for c in d.get("categorias", [])
                  if c.get("tipo", "despesa") == "despesa"]
    return {"hoje": hoje.isoformat(), "contas": out, "categorias": categorias}


def _materializar(l, **extra):
    o = {"id": uid(), "tipo": l.get("tipo", "despesa"), "descricao": l.get("descricao", ""),
         "valor": calc.num(l.get("valor")), "categoria": l.get("categoria", ""), "conta": l.get("conta", ""),
         "cartao": bool(l.get("cartao")), "data": l.get("data"), "pago": bool(l.get("pago")), "obs": l.get("obs", ""),
         "recorrencia": l.get("recorrencia"), "competencia": l.get("competencia")}
    for k in ("aporte", "vinculo", "partes", "descontos"):
        if l.get(k):
            o[k] = json.loads(json.dumps(l[k]))
    o.update(extra)
    return o


def _achar_fatura(d, cid):
    conta, dc = cid[2:].split("|", 1)
    ym = dc[:7]
    faturas, _ = _faturas_e_contas(d, _ocorrencias(d, ym, ym))
    for f in faturas:
        if f["id"] == cid:
            return f
    raise LookupError("Fatura não encontrada.")


def _marcar(d, l, pago, valor=None):
    """Marca um lançamento (ou a ocorrência de um fixo) como pago ou a pagar. Devolve o lançamento real."""
    if l.get("virtual") or str(l.get("id", "")).startswith("v:"):
        x = next((y for y in d["lancamentos"] if y.get("recorrencia") == l.get("recorrencia")
                  and y.get("competencia") == l.get("competencia")), None)
        if x is None:
            if not pago:
                return None
            x = _materializar(l, pago=True)
            d["lancamentos"].append(x)
    else:
        x = next((y for y in d["lancamentos"] if y.get("id") == l.get("id")), None)
        if x is None:
            raise LookupError("Conta não encontrada.")
    x["pago"] = bool(pago)
    if pago and valor is not None and valor > 0:
        x["valor"] = round(float(valor), 2)
    return x


def _achar(d, cid):
    if cid.startswith("v:"):
        _, rid, ym = cid.split(":", 2)
        r = next((x for x in d.get("recorrencias", []) if x.get("id") == rid), None)
        if not r:
            raise LookupError("Fixo não encontrado.")
        feito = next((y for y in d["lancamentos"] if y.get("recorrencia") == rid and y.get("competencia") == ym), None)
        if feito:
            return feito
        a, m = int(ym[:4]), int(ym[5:7])
        return dict(r, id=cid, virtual=True, recorrencia=rid, competencia=ym,
                    data=calc._data_mes(a, m, r.get("dia")).isoformat(), pago=False)
    x = next((y for y in d.get("lancamentos", []) if y.get("id") == cid), None)
    if not x:
        raise LookupError("Conta não encontrada.")
    return x


def pagar(d, cid, valor=None, pago=True):
    cid = str(cid or "")
    if cid.startswith("f:"):
        f = _achar_fatura(d, cid)
        for l in f["_itens"]:
            if bool(l.get("pago")) != pago:
                _marcar(d, l, pago)
        return
    l = _achar(d, cid)
    if l.get("tipo") == "receita":
        raise ValueError("Isso é um recebimento, não uma conta.")
    _marcar(d, l, pago, valor if pago else None)


def nova(d, corpo):
    desc = str(corpo.get("descricao") or "").strip()[:120]
    if not desc:
        raise ValueError("Coloque o nome da conta.")
    try:
        valor = round(float(corpo.get("valor")), 2)
    except (TypeError, ValueError):
        raise ValueError("Coloque o valor.") from None
    if valor <= 0:
        raise ValueError("Coloque o valor.")
    try:
        venc = date.fromisoformat(str(corpo.get("vencimento")))
    except ValueError:
        raise ValueError("Data de vencimento inválida.") from None
    cat = str(corpo.get("categoria") or "")
    if cat and not any(c.get("id") == cat for c in d.get("categorias", [])):
        cat = ""
    repete = corpo.get("repete") or "nao"
    base = {"tipo": "despesa", "descricao": desc, "valor": valor, "categoria": cat, "conta": "", "cartao": False, "obs": ""}
    if repete in ("mensal", "anual"):
        r = dict(base, id="r-" + uid(), dia=venc.day, inicio=venc.isoformat()[:7], fim=None)
        if repete == "anual":
            r["freq"] = "anual"
        d["recorrencias"].append(r)
        return f"v:{r['id']}:{venc.isoformat()[:7]}"
    l = dict(base, id=uid(), data=venc.isoformat(), pago=False)
    d["lancamentos"].append(l)
    return l["id"]
