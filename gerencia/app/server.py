#!/usr/bin/env python3
"""GerencIA: servidor do app do Home Assistant (só biblioteca padrão do Python).

Dados em /data/gerencia.json, versões em /data/versoes, backups em /share/gerencia.
"""
import base64
import csv
import html
import io
import json
import os
import re
import secrets
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calc  # noqa: E402

VERSAO = "1.1.0"
PORTA = int(os.environ.get("GERENCIA_PORTA", "8099"))
DATA_DIR = os.environ.get("GERENCIA_DATA", "/data")
SHARE_DIR = os.environ.get("GERENCIA_SHARE", "/share/gerencia")
WWW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "www")
ARQ = os.path.join(DATA_DIR, "gerencia.json")
VERSOES = os.path.join(DATA_DIR, "versoes")
FOTOS = os.path.join(DATA_DIR, "fotos")
MEDIA_ROOT = os.environ.get("GERENCIA_MEDIA", "/media")
IA_TMP_REL = "gerencia/ia-temp"  # relativo a /media (fonte de mídia "local" do Home Assistant)
HA_API = os.environ.get("GERENCIA_HA_API", "http://supervisor/core/api")
IA_MOCK = os.environ.get("GERENCIA_IA_MOCK") == "1"
RE_FOTO = re.compile(r"[0-9]{8}-[0-9]{6}-[0-9a-f]{6}\.jpg")
DEV = os.environ.get("GERENCIA_DEV") == "1"
TOKEN = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HASSIO_TOKEN")
# O ingress do Home Assistant sempre chega por este endereço.
PERMITIDOS = {"172.30.32.2", "127.0.0.1", "::1"}

MAX_VERSOES = 60
INTERVALO_VERSAO = 10 * 60
MAX_CORPO = 25 * 1024 * 1024

TRAVA = threading.RLock()
_ultima_versao = 0.0

INDICES_PADRAO = {
    # Valores de partida (out/2026). São trocados pelos do Banco Central na primeira atualização.
    "cdi": 13.65,
    "selic": 13.75,
    "ipca": 4.58,
    "tr": 0.17,
    "auto": True,
    "fonte": "padrao",
    "atualizado_em": None,
    "datas": {},
    "erro": None,
}

AJUSTES_PADRAO = {"tema": "auto", "cor": "#56AEFF", "corrigir": True, "sensores": True, "ia_entidade": ""}
LISTAS = ("bancos", "investimentos", "historico", "lancamentos", "recorrencias", "categorias")


def log(*a):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), *a, flush=True)


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------- dados

def vazio():
    return {
        "schema": 1,
        "rev": 0,
        "exemplo": False,
        "bancos": [],
        "investimentos": [],
        "indices": dict(INDICES_PADRAO),
        "ajustes": dict(AJUSTES_PADRAO),
        "historico": [],
        "lancamentos": [],
        "recorrencias": [],
        "categorias": calc.categorias_padrao(),
    }


def normalizar(d):
    base = vazio()
    if not isinstance(d, dict):
        return base
    for k in ("schema", "rev", "exemplo"):
        if k in d:
            base[k] = d[k]
    for k in LISTAS:
        if isinstance(d.get(k), list):
            base[k] = [x for x in d[k] if isinstance(x, dict)]
    if isinstance(d.get("indices"), dict):
        base["indices"].update(d["indices"])
    if isinstance(d.get("ajustes"), dict):
        base["ajustes"].update(d["ajustes"])
    try:
        base["rev"] = int(base["rev"])
    except (TypeError, ValueError):
        base["rev"] = 0
    return base


def ler():
    with TRAVA:
        if not os.path.exists(ARQ):
            return vazio()
        try:
            with open(ARQ, encoding="utf-8") as f:
                return normalizar(json.load(f))
        except (OSError, ValueError) as e:
            log("Erro lendo dados:", e)
            return vazio()


def gravar_arquivo(caminho, conteudo):
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(conteudo)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, caminho)


def guardar_versao(motivo="auto", forcar=False):
    """Copia o arquivo atual para /data/versoes (no máximo a cada 10 min, salvo se forçado)."""
    global _ultima_versao
    if not os.path.exists(ARQ):
        return None
    if not forcar and time.time() - _ultima_versao < INTERVALO_VERSAO:
        return None
    os.makedirs(VERSOES, exist_ok=True)
    nome = f"gerencia-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{motivo}.json"
    shutil.copy2(ARQ, os.path.join(VERSOES, nome))
    _ultima_versao = time.time()
    arquivos = sorted(f for f in os.listdir(VERSOES) if f.endswith(".json"))
    for velho in arquivos[:-MAX_VERSOES]:
        try:
            os.remove(os.path.join(VERSOES, velho))
        except OSError:
            pass
    return nome


def registrar_historico(d, hoje=None):
    hoje = hoje or date.today()
    t = calc.totais(d, hoje)
    ponto = {"d": hoje.isoformat(), "total": t["total"], "meu": t["meu"], "terceiros": t["terceiros"]}
    hist = [h for h in d.get("historico", []) if h.get("d") != ponto["d"]]
    if d.get("investimentos") or hist:
        hist.append(ponto)
    hist.sort(key=lambda h: h.get("d", ""))
    d["historico"] = hist[-3650:]


def salvar(d, versao=True, motivo="auto"):
    with TRAVA:
        os.makedirs(DATA_DIR, exist_ok=True)
        if versao:
            guardar_versao(motivo)
        registrar_historico(d)
        gravar_arquivo(ARQ, json.dumps(d, ensure_ascii=False, indent=1))
    publicar_sensores_async(d)
    return d


# ---------------------------------------------------------------- Banco Central

BCB = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{s}/dados"
SERIES = {"selic": 432, "cdi": 4389, "ipca": 13522, "tr": 226}


def bcb_ultimo(serie):
    cab = {"User-Agent": "GerencIA/1.0 (Home Assistant)", "Accept": "application/json"}
    urls = [BCB.format(s=serie) + "/ultimos/1?formato=json"]
    fim = date.today()
    ini = fim - timedelta(days=75)
    urls.append(BCB.format(s=serie) + f"?formato=json&dataInicial={ini:%d/%m/%Y}&dataFinal={fim:%d/%m/%Y}")
    erro = None
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=cab)
            with urllib.request.urlopen(req, timeout=15) as r:
                dados = json.loads(r.read().decode("utf-8"))
            if isinstance(dados, list) and dados:
                ult = dados[-1]
                return float(str(ult["valor"]).replace(",", ".")), ult.get("data")
        except Exception as e:  # noqa: BLE001
            erro = e
    raise RuntimeError(f"série {serie}: {erro}")


def atualizar_indices():
    with TRAVA:
        d = ler()
    ind = d["indices"]
    novos, datas, falhas = {}, {}, []
    for chave, serie in SERIES.items():
        try:
            v, dt = bcb_ultimo(serie)
            novos[chave] = round(v, 4)
            datas[chave] = dt
        except Exception as e:  # noqa: BLE001
            falhas.append(chave)
            log("Banco Central:", e)
    if "cdi" not in novos and "selic" in novos:
        novos["cdi"] = round(novos["selic"] - 0.10, 4)
    with TRAVA:
        d = ler()
        ind = d["indices"]
        if novos:
            ind.update(novos)
            ind["datas"] = {**ind.get("datas", {}), **datas}
            ind["fonte"] = "bcb"
            ind["atualizado_em"] = agora_iso()
        ind["erro"] = (
            None if not falhas else
            ("Sem resposta do Banco Central" if not novos else "Faltou: " + ", ".join(falhas))
        )
        salvar(d, versao=False)
    return d


# ---------------------------------------------------------------- sensores no HA

def publicar_sensores(d):
    if not TOKEN or not d.get("ajustes", {}).get("sensores", True):
        return
    t = calc.totais(d)
    base = {"unit_of_measurement": "BRL", "device_class": "monetary", "state_class": "total"}
    sensores = {
        "sensor.gerencia_patrimonio": (t["total"], "GerencIA Patrimônio", "mdi:cash-multiple",
                                       {"seu": t["meu"], "de_terceiros": t["terceiros"],
                                        "investimentos": t["quantidade"]}),
        "sensor.gerencia_meu": (t["meu"], "GerencIA Seu dinheiro", "mdi:account-cash", {}),
        "sensor.gerencia_terceiros": (t["terceiros"], "GerencIA De terceiros", "mdi:account-group",
                                      {"por_pessoa": t["pessoas"]}),
        "sensor.gerencia_rendimento_mensal": (t["rende_mes"], "GerencIA Rende por mês", "mdi:chart-line", {}),
    }
    cx = calc.caixa(d)
    sensores.update({
        "sensor.gerencia_saldo_caixa": (cx["saldo"], "GerencIA Saldo em caixa", "mdi:wallet", {}),
        "sensor.gerencia_entradas_mes": (cx["entrou_mes"], "GerencIA Entrou no mês", "mdi:arrow-down-bold-circle",
                                         {"a_receber": cx["a_receber_mes"]}),
        "sensor.gerencia_saidas_mes": (cx["saiu_mes"], "GerencIA Saiu no mês", "mdi:arrow-up-bold-circle",
                                       {"a_pagar": cx["a_pagar_mes"], "atrasado": cx["atrasado"]}),
    })
    for ent, (valor, nome, icone, extra) in sensores.items():
        corpo = json.dumps({"state": valor, "attributes": {**base, "friendly_name": nome, "icon": icone, **extra}})
        req = urllib.request.Request(
            f"http://supervisor/core/api/states/{ent}", data=corpo.encode(), method="POST",
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=10).read()
        except Exception as e:  # noqa: BLE001
            log("Sensor", ent, "não publicado:", e)
            return


def publicar_sensores_async(d):
    threading.Thread(target=publicar_sensores, args=(json.loads(json.dumps(d)),), daemon=True).start()


# ---------------------------------------------------------------- exportar

def linhas_csv(d):
    ind = d["indices"]
    corrigir = d["ajustes"].get("corrigir", True)
    bancos = {b.get("id"): b.get("nome", "") for b in d["bancos"]}
    cab = ["Nome", "Banco", "Tipo", "De quem", "Rendimento", "Indexador", "Taxa (%)",
           "Valor informado", "Data do valor", "Valor estimado hoje", "Rende por mês",
           "Liquidez", "Vencimento", "Observação"]
    linhas = [cab]
    for inv in d["investimentos"]:
        v = calc.valor_hoje(inv, ind, corrigir)
        r = calc.taxa_anual(inv, ind)
        linhas.append([
            inv.get("nome", ""), bancos.get(inv.get("banco"), ""), calc.TIPOS.get(inv.get("tipo"), ""),
            calc.dono(inv), calc.rotulo_taxa(inv), calc.INDEXADORES.get(inv.get("indexador"), ""),
            calc.fmt_num(calc.num(inv.get("taxa")), 2), calc.fmt_num(calc.num(inv.get("valor"))),
            inv.get("data_valor") or "", calc.fmt_num(v), calc.fmt_num(calc.rende_mes(v, r)),
            "Diária" if inv.get("liquidez") == "diaria" else "No vencimento",
            inv.get("vencimento") or "", inv.get("obs", ""),
        ])
    return linhas


def gerar_csv(d):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    for l in linhas_csv(d):
        w.writerow(l)
    return ("﻿" + buf.getvalue()).encode("utf-8")


def gerar_csv_lancamentos(d):
    cats = {c.get("id"): c.get("nome", "") for c in d["categorias"]}
    contas = calc.mapa_contas(d)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow(["Data", "Data no caixa", "Tipo", "Descrição", "Categoria", "Conta", "Cartão", "Valor",
                "Situação", "Parcela", "Fixo", "Observação"])
    for l in sorted(d["lancamentos"], key=lambda x: str(x.get("data") or "")):
        if l.get("pulado"):
            continue
        rec = l.get("tipo") == "receita"
        dc = calc.data_caixa(l, contas)
        w.writerow([l.get("data") or "", dc.isoformat() if dc else "", "Recebimento" if rec else "Despesa",
                    l.get("descricao", ""), cats.get(l.get("categoria"), "Ajuste de saldo" if l.get("ajuste") else ""),
                    calc.nome_conta(contas.get(l.get("conta"))), "Sim" if l.get("cartao") else "",
                    calc.fmt_num(calc.num(l.get("valor"))),
                    ("Recebido" if rec else "Pago") if l.get("pago") else ("A receber" if rec else "A pagar"),
                    l.get("parcela") or "", "Sim" if l.get("recorrencia") else "", l.get("obs", "")])
    for r in d["recorrencias"]:
        w.writerow([f"todo dia {r.get('dia')}", "", "Recebimento fixo" if r.get("tipo") == "receita" else "Despesa fixa",
                    r.get("descricao", ""), cats.get(r.get("categoria"), ""), calc.nome_conta(contas.get(r.get("conta"))),
                    "Sim" if r.get("cartao") else "", calc.fmt_num(calc.num(r.get("valor"))),
                    f"desde {r.get('inicio')}" + (f" até {r['fim']}" if r.get("fim") else ""), "", "Sim", r.get("obs", "")])
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def gerar_zip(d):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("gerencia.json", json.dumps(d, ensure_ascii=False, indent=1))
        z.writestr("gerencia.csv", gerar_csv(d))
        z.writestr("lancamentos.csv", gerar_csv_lancamentos(d))
        for nome in fotos_usadas(d):
            p = os.path.join(FOTOS, nome)
            if os.path.isfile(p):
                z.write(p, f"fotos/{nome}")
        z.writestr("LEIA-ME.txt",
                   f"Backup do GerencIA {VERSAO} criado em {agora_iso()}.\n"
                   "Para restaurar: Mais > Dados > Importar backup, e escolha este .zip.\n")
    return buf.getvalue()


def nome_arquivo(ext):
    return f"gerencia-{datetime.now().strftime('%Y-%m-%d-%H%M')}.{ext}"


# ---------------------------------------------------------------- relatório

def gerar_relatorio(d):
    ind = d["indices"]
    corrigir = d["ajustes"].get("corrigir", True)
    cor = re.sub(r"[^#0-9A-Fa-f]", "", d["ajustes"].get("cor", "#56AEFF"))[:7] or "#56AEFF"
    bancos = {b.get("id"): b for b in d["bancos"]}
    t = calc.totais(d)
    e = html.escape

    grupos = {}
    for inv in d["investimentos"]:
        grupos.setdefault(calc.dono(inv), []).append(inv)
    ordem = sorted(grupos, key=lambda p: (p != "Meu", p.lower()))

    por_banco = {}
    for inv in d["investimentos"]:
        nome = bancos.get(inv.get("banco"), {}).get("nome", "Sem banco")
        por_banco[nome] = por_banco.get(nome, 0) + calc.valor_hoje(inv, ind, corrigir)

    partes = []
    for p in ordem:
        itens = sorted(grupos[p], key=lambda i: -calc.valor_hoje(i, ind, corrigir))
        soma = sum(calc.valor_hoje(i, ind, corrigir) for i in itens)
        titulo = "Seu dinheiro" if p == "Meu" else f"De {e(p)}"
        linhas = []
        for inv in itens:
            v = calc.valor_hoje(inv, ind, corrigir)
            venc = calc.parse_data(inv.get("vencimento"))
            linhas.append(
                "<tr><td>{}<small>{}</small></td><td>{}</td><td>{}</td><td>{}</td><td class=n>{}</td></tr>".format(
                    e(inv.get("nome", "")), e(calc.TIPOS.get(inv.get("tipo"), "")),
                    e(bancos.get(inv.get("banco"), {}).get("nome", "")), e(calc.rotulo_taxa(inv)),
                    venc.strftime("%d/%m/%Y") if venc else ("Diária" if inv.get("liquidez") == "diaria" else ""),
                    calc.fmt_brl(v)))
        partes.append(
            f"<section><h2>{titulo}<span>{calc.fmt_brl(soma)}</span></h2>"
            "<table><thead><tr><th>Investimento</th><th>Banco</th><th>Rendimento</th>"
            "<th>Vencimento</th><th class=n>Valor hoje</th></tr></thead><tbody>"
            + "".join(linhas) + "</tbody></table></section>")

    bancos_html = "".join(
        f"<tr><td>{e(n)}</td><td class=n>{calc.fmt_brl(v)}</td>"
        f"<td class=n>{calc.fmt_pct(v / t['total'] * 100 if t['total'] else 0)}%</td></tr>"
        for n, v in sorted(por_banco.items(), key=lambda x: -x[1]))

    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatório GerencIA</title>
<style>
:root{{--a:{cor}}}
*{{box-sizing:border-box}}
body{{font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:#141a22;background:#fff;margin:0;padding:24px 16px 48px}}
main{{max-width:860px;margin:0 auto}}
.barra{{display:flex;gap:8px;margin-bottom:20px}}
.barra a,.barra button{{font:inherit;font-weight:600;padding:10px 16px;border-radius:12px;border:1px solid #d6dbe2;background:#fff;color:#141a22;text-decoration:none;cursor:pointer}}
.barra button{{background:var(--a);border-color:transparent;color:#0b0f14}}
h1{{font-size:28px;margin:0 0 4px;letter-spacing:-.01em}}
.sub{{color:#5b6573;margin:0 0 20px}}
.resumo{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:24px}}
.resumo div{{border:1px solid #e3e7ec;border-radius:12px;padding:12px}}
.resumo b{{display:block;font-size:20px}}
.resumo span{{color:#5b6573;font-size:13px}}
h2{{font-size:17px;display:flex;justify-content:space-between;border-bottom:2px solid var(--a);padding-bottom:6px;margin:28px 0 6px}}
table{{width:100%;border-collapse:collapse;font-size:13.5px}}
th{{text-align:left;color:#5b6573;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em;padding:8px 6px;border-bottom:1px solid #e3e7ec}}
td{{padding:8px 6px;border-bottom:1px solid #eef1f4;vertical-align:top}}
td small{{display:block;color:#5b6573}}
.n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.rodape{{color:#5b6573;font-size:12px;margin-top:28px}}
@media (max-width:600px){{.resumo{{grid-template-columns:1fr}} th:nth-child(4),td:nth-child(4){{display:none}}}}
@media print{{.barra{{display:none}} body{{padding:0}} section{{break-inside:avoid}}}}
</style></head><body><main>
<div class="barra"><a href="./">Voltar</a><button onclick="window.print()">Imprimir ou salvar PDF</button></div>
<h1>Relatório de patrimônio</h1>
<p class="sub">Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} · {t['quantidade']} investimentos</p>
<div class="resumo">
<div><span>Patrimônio total</span><b>{calc.fmt_brl(t['total'])}</b></div>
<div><span>Seu dinheiro</span><b>{calc.fmt_brl(t['meu'])}</b></div>
<div><span>De terceiros</span><b>{calc.fmt_brl(t['terceiros'])}</b></div>
</div>
{''.join(partes)}
<section><h2>Por banco<span>{calc.fmt_brl(t['total'])}</span></h2>
<table><thead><tr><th>Banco</th><th class=n>Valor</th><th class=n>Parte</th></tr></thead><tbody>{bancos_html}</tbody></table></section>
<p class="rodape">Valores de hoje estimados a partir do último valor informado e dos índices: CDI {calc.fmt_pct(calc.num(ind.get('cdi')))}% a.a.,
Selic {calc.fmt_pct(calc.num(ind.get('selic')))}% a.a., IPCA {calc.fmt_pct(calc.num(ind.get('ipca')))}% em 12 meses. Antes do imposto de renda.</p>
</main></body></html>""".encode("utf-8")


# ---------------------------------------------------------------- importar

def importar(corpo, nome):
    nome = (nome or "").lower()
    if corpo[:2] == b"PK" or nome.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(corpo)) as z:
            alvo = next((n for n in z.namelist() if n.endswith("gerencia.json")), None)
            alvo = alvo or next((n for n in z.namelist() if n.endswith(".json")), None)
            if not alvo:
                raise ValueError("O .zip não tem o arquivo gerencia.json.")
            novo = json.loads(z.read(alvo).decode("utf-8-sig"))
            os.makedirs(FOTOS, exist_ok=True)
            for n in z.namelist():
                base = os.path.basename(n)
                if n.startswith("fotos/") and RE_FOTO.fullmatch(base):
                    with open(os.path.join(FOTOS, base), "wb") as f:
                        f.write(z.read(n))
    else:
        novo = json.loads(corpo.decode("utf-8-sig"))
    if not isinstance(novo, dict) or not isinstance(novo.get("investimentos"), list):
        raise ValueError("Esse arquivo não parece um backup do GerencIA.")
    with TRAVA:
        atual = ler()
        guardar_versao("antes-de-importar", forcar=True)
        d = normalizar(novo)
        d["rev"] = atual["rev"] + 1
        salvar(d, versao=False)
    return d



# ---------------------------------------------------------------- fotos dos investimentos

def fotos_usadas(d):
    usadas = set()
    for inv in d.get("investimentos", []):
        for f in inv.get("fotos") or []:
            if isinstance(f, str) and RE_FOTO.fullmatch(f):
                usadas.add(f)
    return usadas


def salvar_foto(corpo):
    b64 = str(corpo.get("jpg") or "")
    if b64.startswith("data:"):
        b64 = b64.split(",", 1)[-1]
    try:
        raw = base64.b64decode(b64, validate=True)
    except (ValueError, TypeError):
        raise ValueError("Imagem inválida.")
    if len(raw) < 200 or raw[:2] != b"\xff\xd8":
        raise ValueError("Envie a imagem em JPG.")
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("Imagem grande demais.")
    os.makedirs(FOTOS, exist_ok=True)
    nome = f"{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}.jpg"
    tmp = os.path.join(FOTOS, nome + ".tmp")
    with open(tmp, "wb") as f:
        f.write(raw)
    os.replace(tmp, os.path.join(FOTOS, nome))
    return {"arquivo": nome}


def limpar_fotos(d, dias=7):
    """Apaga imagens que nenhum investimento usa há mais de uma semana (as versões anteriores podem voltar a usar)."""
    if not os.path.isdir(FOTOS):
        return
    usadas = fotos_usadas(d)
    for n in os.listdir(FOTOS):
        p = os.path.join(FOTOS, n)
        if RE_FOTO.fullmatch(n) and n not in usadas and time.time() - os.path.getmtime(p) > dias * 86400:
            try:
                os.remove(p)
            except OSError:
                pass


# ---------------------------------------------------------------- leitura por IA (ação ai_task.generate_data do HA)

class ErroHA(Exception):
    pass


def ha_request(method, path, body=None, timeout=20):
    if not TOKEN:
        raise ErroHA("O app não tem acesso à API do Home Assistant.")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(HA_API + path, data=data, method=method, headers={
        "Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        det = e.read().decode("utf-8", "replace")[:600]
        try:
            det = json.loads(det).get("message", det)
        except (ValueError, AttributeError):
            pass
        raise ErroHA(f"O Home Assistant recusou o pedido: {det}")
    except (urllib.error.URLError, TimeoutError) as e:
        raise ErroHA(f"Sem resposta do Home Assistant ({e}).")


def ia_entidades():
    if IA_MOCK:
        return [{"id": "ai_task.simulada", "nome": "IA simulada (teste)", "imagens": True}]
    saida = []
    for st in ha_request("GET", "/states") or []:
        eid = st.get("entity_id", "")
        if eid.startswith("ai_task."):
            at = st.get("attributes") or {}
            saida.append({"id": eid, "nome": at.get("friendly_name") or eid,
                          "imagens": bool(int(at.get("supported_features") or 0) & 2)})
    return sorted(saida, key=lambda e: (not e["imagens"], e["nome"].lower()))


def ia_status(d):
    sel = d["ajustes"].get("ia_entidade") or ""
    if not TOKEN and not IA_MOCK:
        return {"pronta": False, "motivo": "Fora do Home Assistant a leitura por IA não funciona.", "entidades": [], "selecionada": sel}
    try:
        ents = ia_entidades()
    except ErroHA as e:
        return {"pronta": False, "motivo": str(e), "entidades": [], "selecionada": sel}
    if not ents:
        return {"pronta": False, "motivo": "Nenhuma IA configurada no Home Assistant (integração com tarefa de IA).",
                "entidades": [], "selecionada": sel}
    ok = any(e["imagens"] for e in ents) if not sel else any(e["id"] == sel for e in ents)
    return {"pronta": ok, "motivo": None if ok else "A IA escolhida não está mais no Home Assistant.",
            "entidades": ents, "selecionada": sel}


IA_REGRAS = """Para cada investimento, devolva:
- "nome": nome curto e claro (ex.: "CDB Inter 2028", "Tesouro IPCA+ 2035", "LCI Itaú").
- "banco": instituição ou corretora (ex.: "Inter", "XP"); "" se não aparecer.
- "tipo": uma destas chaves: cdb, lci (LCI, LCA, CRI, CRA), tesouro, poupanca, caixinha (conta remunerada, cofrinho, caixinha), fundo, acoes (ações, FII, ETF, BDR), previdencia, outro.
- "valor": saldo atual bruto em reais, número sem símbolo. Se só aparecer o valor aplicado, use ele.
- "aplicado": valor aplicado originalmente, número; 0 se não aparecer.
- "data_valor": data do saldo em AAAA-MM-DD, se aparecer; senão "".
- "indexador": cdi_pct (ex.: 110% do CDI), cdi_mais (CDI + 1,5% a.a.), pre (prefixado 13% a.a.), ipca_mais (IPCA + 6% a.a.), selic_mais (Tesouro Selic, Selic + 0,1%), poupanca, estimado (renda variável), parado (sem rendimento).
- "taxa": 110 para 110% do CDI; 1.5 para CDI + 1,5%; 13 para 13% a.a.; 6.5 para IPCA + 6,5%; 0.1 para Selic + 0,1%; 0 para poupança e sem rendimento; 10 para renda variável.
- "vencimento": AAAA-MM-DD, se aparecer; senão "".
- "liquidez": "diaria" se der para resgatar a qualquer momento; senão "vencimento".
- "existente": se for o mesmo investimento de um já cadastrado (lista abaixo), o id dele; senão "".
- "confianca": "alta", "media" ou "baixa".
Ignore saldo parado em conta corrente, cartões, limites e empréstimos. Não invente números: se não der para ler, use 0 ou "".
Responda somente com JSON válido, sem markdown e sem texto antes ou depois, neste formato:
{"itens":[{"nome":"","banco":"","tipo":"cdb","valor":0,"aplicado":0,"data_valor":"","indexador":"cdi_pct","taxa":100,"vencimento":"","liquidez":"vencimento","existente":"","confianca":"media"}]}"""


IA_REGRAS_CAIXA = """Para cada gasto ou recebimento, devolva:
- "tipo": "despesa" (gasto, compra, conta paga, débito) ou "receita" (salário, pix recebido, venda, reembolso).
- "descricao": curta e limpa, como a pessoa escreveria (ex.: "iFood", "Posto Shell", "Aluguel", "Salário").
- "valor": valor em reais, número positivo sem símbolo. Em parcelas, o valor da parcela.
- "data": AAAA-MM-DD. Em fatura de cartão, a data da compra. Se só houver dia e mês, use o ano mais provável. Se não houver data, use a de hoje. "ontem" e "hoje" valem pela data de hoje.
- "categoria": uma destas chaves: {cats}.
- "parcela_atual" e "parcelas_total": números, quando aparecer "parcela 3/10", "PARC 03/10" ou "3 de 10"; senão 0 e 0.
- "cartao": true se for compra no cartão de crédito (fatura); senão false.
- "banco": banco ou cartão citado; "" se não aparecer.
- "confianca": "alta", "media" ou "baixa".
Em fatura, ignore "pagamento recebido", "pagamento da fatura", "saldo anterior", créditos de estorno do próprio cartão e totais. Juros, IOF, anuidade e multa entram como despesa na categoria de impostos e taxas.
Em conversas (WhatsApp, anotações), cada valor citado como gasto ou ganho vira um item. Não invente números.
Responda somente com JSON válido, sem markdown e sem texto antes ou depois, neste formato:
{{"itens":[{{"tipo":"despesa","descricao":"","valor":0,"data":"","categoria":"","parcela_atual":0,"parcelas_total":0,"cartao":false,"banco":"","confianca":"media"}}]}}"""


def ia_prompt(d, modo, com_anexo, texto):
    hoje_txt = f"{date.today():%d/%m/%Y}"
    if modo == "caixa":
        cats = ", ".join(f"{c.get('id')} ({c.get('nome')}, {c.get('tipo')})" for c in d["categorias"])
        partes = [f"Você ajuda uma pessoa no Brasil a registrar recebimentos e despesas. Hoje é {hoje_txt}.",
                  "Leia o anexo (fatura de cartão em PDF, foto de nota ou cupom, print de app de banco ou de conversa do WhatsApp) "
                  "e liste cada lançamento, até 120." if com_anexo else
                  "Leia o texto abaixo (mensagens do WhatsApp, anotações, extrato ou fatura colada) e liste cada lançamento, até 120.",
                  IA_REGRAS_CAIXA.format(cats=cats)]
    else:
        bancos = {b.get("id"): b.get("nome", "") for b in d["bancos"]}
        partes = [f"Você ajuda a organizar os investimentos de uma pessoa no Brasil. Hoje é {hoje_txt}.",
                  "Leia o anexo (print de app de banco ou corretora, extrato em PDF, nota de aplicação ou comprovante) "
                  "e liste cada investimento que aparecer, até 20." if com_anexo else
                  "Leia o texto colado abaixo (extrato, e-mail de aplicação ou comprovante) e liste cada investimento, até 20.",
                  IA_REGRAS]
        if d["investimentos"]:
            partes.append("Investimentos já cadastrados (id | nome | banco | valor):")
            for inv in d["investimentos"][:80]:
                partes.append(f"{inv.get('id')} | {inv.get('nome', '')} | {bancos.get(inv.get('banco'), '')} | {calc.num(inv.get('valor')):.2f}")
    if texto:
        partes.append("Texto:\n<<<\n" + texto + "\n>>>")
    return "\n".join(partes)


def extrair_json(raw):
    if isinstance(raw, (dict, list)):
        return raw
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(raw or "").strip(), flags=re.I | re.S).strip()
    try:
        return json.loads(t)
    except ValueError:
        pass
    ini = min([p for p in (t.find("{"), t.find("[")) if p >= 0] or [-1])
    if ini >= 0:
        for fim in range(len(t), ini, -1):
            if t[fim - 1] in "}]":
                try:
                    return json.loads(t[ini:fim])
                except ValueError:
                    continue
    raise ValueError("Não deu para entender a resposta da IA. Tente de novo.")


def _data_ou_vazio(v):
    v = str(v or "").strip()[:10]
    return v if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) and calc.parse_data(v) else ""


def _lista(parsed):
    if isinstance(parsed, dict):
        return parsed.get("itens") or parsed.get("items") or []
    return parsed if isinstance(parsed, list) else []


def ia_limpar(parsed, d):
    ids = {i.get("id") for i in d["investimentos"]}
    saida = []
    for it in _lista(parsed)[:20]:
        if not isinstance(it, dict):
            continue
        tipo = str(it.get("tipo") or "outro").lower()
        idx = str(it.get("indexador") or "cdi_pct").lower()
        saida.append({
            "nome": str(it.get("nome") or "").strip()[:80] or "Investimento",
            "banco": str(it.get("banco") or "").strip()[:40],
            "tipo": tipo if tipo in calc.TIPOS else "outro",
            "valor": round(max(0.0, calc.num(it.get("valor"))), 2),
            "aplicado": round(max(0.0, calc.num(it.get("aplicado"))), 2),
            "data_valor": _data_ou_vazio(it.get("data_valor")),
            "indexador": idx if idx in calc.INDEXADORES else "cdi_pct",
            "taxa": round(calc.num(it.get("taxa")), 4),
            "vencimento": _data_ou_vazio(it.get("vencimento")),
            "liquidez": "diaria" if str(it.get("liquidez")).lower().startswith("diar") else "vencimento",
            "existente": it.get("existente") if it.get("existente") in ids else "",
            "confianca": it.get("confianca") if it.get("confianca") in ("alta", "media", "baixa") else "media",
        })
    return saida


def ia_limpar_caixa(parsed, d):
    cats = {c.get("id"): c.get("tipo") for c in d["categorias"]}
    saida = []
    for it in _lista(parsed)[:120]:
        if not isinstance(it, dict):
            continue
        valor = round(abs(calc.num(it.get("valor"))), 2)
        if valor <= 0:
            continue
        tipo = "receita" if str(it.get("tipo")).lower().startswith("rec") else "despesa"
        cat = it.get("categoria") if cats.get(it.get("categoria")) == tipo else ""
        pa, pt = int(calc.num(it.get("parcela_atual"))), int(calc.num(it.get("parcelas_total")))
        saida.append({
            "tipo": tipo, "descricao": str(it.get("descricao") or "").strip()[:80] or ("Recebimento" if tipo == "receita" else "Gasto"),
            "valor": valor, "data": _data_ou_vazio(it.get("data")) or date.today().isoformat(), "categoria": cat,
            "parcela_atual": pa if 0 < pa <= pt <= 120 else 0, "parcelas_total": pt if 0 < pa <= pt <= 120 else 0,
            "cartao": bool(it.get("cartao")), "banco": str(it.get("banco") or "").strip()[:40],
            "confianca": it.get("confianca") if it.get("confianca") in ("alta", "media", "baixa") else "media",
        })
    return saida


IA_SIMULADA = {"itens": [
    {"nome": "CDB Banco Inter 2028", "banco": "Inter", "tipo": "cdb", "valor": 15412.37, "aplicado": 15000,
     "data_valor": "", "indexador": "cdi_pct", "taxa": 112, "vencimento": "2028-03-13", "liquidez": "vencimento", "confianca": "alta"},
    {"nome": "Tesouro Selic 2029", "banco": "XP", "tipo": "tesouro", "valor": 8350.10, "aplicado": 8000,
     "data_valor": "", "indexador": "selic_mais", "taxa": 0.05, "vencimento": "2029-03-01", "liquidez": "diaria", "confianca": "media"},
]}
IA_SIMULADA_CAIXA = {"itens": [
    {"tipo": "despesa", "descricao": "iFood", "valor": 64.90, "data": "", "categoria": "c-restaurantes", "cartao": True, "banco": "Nubank"},
    {"tipo": "despesa", "descricao": "Posto Shell", "valor": 210.00, "data": "", "categoria": "c-transporte", "cartao": True, "banco": "Nubank"},
    {"tipo": "despesa", "descricao": "Magazine Luiza", "valor": 189.90, "data": "", "categoria": "c-compras", "parcela_atual": 2, "parcelas_total": 6, "cartao": True},
    {"tipo": "receita", "descricao": "Pix do João", "valor": 150.00, "data": "", "categoria": "c-reembolso"},
]}


def pdf_texto(raw):
    """Texto de um PDF simples (fluxos FlateDecode com Tj/TJ). Serve de reserva quando a IA não aceita PDF."""
    import zlib
    partes = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        bloco = m.group(1)
        try:
            bloco = zlib.decompress(bloco)
        except zlib.error:
            pass
        for t in re.finditer(rb"\((.*?)(?<!\\)\)\s*Tj|\[(.*?)\]\s*TJ", bloco, re.S):
            if t.group(1) is not None:
                partes.append(t.group(1))
            else:
                partes.extend(re.findall(rb"\((.*?)(?<!\\)\)", t.group(2), re.S))
            partes.append(b" ")
        partes.append(b"\n")
    txt = b"".join(partes).replace(b"\\(", b"(").replace(b"\\)", b")").decode("latin-1", "replace")
    txt = re.sub(r"[ \t]+", " ", txt)
    return txt.strip()[:12000] if len(re.findall(r"[A-Za-z0-9]", txt)) > 60 else ""


def ia_ler(corpo):
    d = ler()
    modo = "caixa" if corpo.get("modo") == "caixa" else "invest"
    foto = str(corpo.get("foto") or "")
    texto = str(corpo.get("texto") or "").strip()[:12000]
    anexo = corpo.get("anexo") or {}
    bruto, mime = None, None
    if foto:
        if not (RE_FOTO.fullmatch(foto) and os.path.isfile(os.path.join(FOTOS, foto))):
            raise ValueError("A imagem não foi encontrada. Envie de novo.")
        with open(os.path.join(FOTOS, foto), "rb") as f:
            bruto, mime = f.read(), "image/jpeg"
    elif anexo.get("b64"):
        try:
            bruto = base64.b64decode(str(anexo["b64"]).split(",", 1)[-1], validate=True)
        except (ValueError, TypeError):
            raise ValueError("Arquivo inválido.")
        mime = "application/pdf" if bruto[:4] == b"%PDF" else "image/jpeg" if bruto[:2] == b"\xff\xd8" else None
        if not mime:
            raise ValueError("Envie uma imagem (JPG) ou um PDF.")
    if not bruto and not texto:
        raise ValueError("Envie uma imagem, um PDF ou cole um texto.")
    limpar = ia_limpar_caixa if modo == "caixa" else ia_limpar
    if IA_MOCK:
        time.sleep(1.2)
        return {"itens": limpar(json.loads(json.dumps(IA_SIMULADA_CAIXA if modo == "caixa" else IA_SIMULADA)), d),
                "entidade": "ai_task.simulada"}
    ent = d["ajustes"].get("ia_entidade") or ""

    def chamar(com_anexo, txt):
        payload = {"task_name": "GerencIA: ler " + ("lançamentos" if modo == "caixa" else "investimentos"),
                   "instructions": ia_prompt(d, modo, com_anexo, txt)}
        if ent:
            payload["entity_id"] = ent
        tmp = None
        try:
            if com_anexo:
                pasta = os.path.join(MEDIA_ROOT, IA_TMP_REL)
                if not os.path.isdir(MEDIA_ROOT):
                    raise ValueError("A pasta media do Home Assistant não está disponível para o app.")
                os.makedirs(pasta, exist_ok=True)
                nome_tmp = f"{secrets.token_hex(8)}.{'pdf' if mime == 'application/pdf' else 'jpg'}"
                tmp = os.path.join(pasta, nome_tmp)
                with open(tmp, "wb") as f:
                    f.write(bruto)
                payload["attachments"] = [{"media_content_id": f"media-source://media_source/local/{IA_TMP_REL}/{nome_tmp}",
                                           "media_content_type": mime}]
            res = ha_request("POST", "/services/ai_task/generate_data?return_response", payload, timeout=240)
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        dados = ((res or {}).get("service_response") or {}).get("data")
        if dados is None:
            raise ValueError("A IA não devolveu resposta.")
        return dados

    try:
        dados = chamar(bool(bruto), texto)
    except ErroHA as e:
        # IA que não aceita PDF: tenta de novo só com o texto tirado do arquivo
        extra = pdf_texto(bruto) if mime == "application/pdf" else ""
        if not extra:
            raise ValueError(str(e) + (" Essa IA pode não aceitar PDF; tente um print da fatura." if mime == "application/pdf" else ""))
        try:
            dados = chamar(False, (texto + "\n" + extra).strip())
        except ErroHA as e2:
            raise ValueError(str(e2))
    return {"itens": limpar(extrair_json(dados), d), "entidade": ent or "padrão do Home Assistant"}


# ---------------------------------------------------------------- HTTP

TIPOS_MIME = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png",
    ".json": "application/json", ".jpg": "image/jpeg", ".woff2": "font/woff2", ".woff": "font/woff", ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
}

CAMPOS_USUARIO = ("bancos", "investimentos", "ajustes", "exemplo", "lancamentos", "recorrencias", "categorias")


class Handler(BaseHTTPRequestHandler):
    server_version = "GerencIA/" + VERSAO

    def log_message(self, fmt, *args):
        if DEV:
            log(self.address_string(), fmt % args)

    # ---- util
    def permitido(self):
        if DEV:
            return True
        ip = self.client_address[0].replace("::ffff:", "")
        if ip in PERMITIDOS:
            return True
        self.send_error(403, "Use o GerencIA pelo painel do Home Assistant.")
        return False

    def enviar(self, status, corpo, tipo="application/json", extra=None):
        if isinstance(corpo, (dict, list)):
            corpo = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
            tipo = "application/json; charset=utf-8"
        elif isinstance(corpo, str):
            corpo = corpo.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(corpo)

    def baixar(self, corpo, tipo, nome):
        self.enviar(200, corpo, tipo, {"Content-Disposition": f'attachment; filename="{nome}"'})

    def corpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_CORPO:
            raise ValueError("Arquivo grande demais.")
        return self.rfile.read(n) if n else b""

    def corpo_json(self):
        b = self.corpo()
        return json.loads(b.decode("utf-8")) if b else {}

    def caminho(self):
        return urlparse(self.path).path.rstrip("/") or "/"

    # ---- GET
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if not self.permitido():
            return
        p = self.caminho()
        q = parse_qs(urlparse(self.path).query)
        try:
            if p == "/api/state":
                d = ler()
                # O ingress do Home Assistant informa quem está usando o app.
                d["usuario"] = (self.headers.get("X-Remote-User-Display-Name")
                                or self.headers.get("X-Remote-User-Name") or None)
                return self.enviar(200, d)
            if p == "/api/export/json":
                return self.baixar(json.dumps(ler(), ensure_ascii=False, indent=1).encode(),
                                   "application/json", nome_arquivo("json"))
            if p == "/api/export/csv":
                return self.baixar(gerar_csv(ler()), "text/csv; charset=utf-8", nome_arquivo("csv"))
            if p == "/api/export/lancamentos":
                return self.baixar(gerar_csv_lancamentos(ler()), "text/csv; charset=utf-8", "lancamentos-" + nome_arquivo("csv")[9:])
            if p.startswith("/fotos/"):
                nome = p[7:]
                arq = os.path.join(FOTOS, nome)
                if not RE_FOTO.fullmatch(nome) or not os.path.isfile(arq):
                    return self.enviar(404, {"erro": "imagem não encontrada"})
                with open(arq, "rb") as f:
                    return self.enviar(200, f.read(), "image/jpeg")
            if p == "/api/ia/status":
                return self.enviar(200, ia_status(ler()))
            if p == "/api/export/zip":
                return self.baixar(gerar_zip(ler()), "application/zip", nome_arquivo("zip"))
            if p == "/api/versoes":
                return self.enviar(200, listar_versoes())
            if p in ("/relatorio", "/relatorio.html"):
                corpo = gerar_relatorio(ler())
                if q.get("baixar"):
                    return self.baixar(corpo, "text/html; charset=utf-8", nome_arquivo("html"))
                return self.enviar(200, corpo, "text/html; charset=utf-8")
            return self.estatico(p)
        except Exception as e:  # noqa: BLE001
            log("Erro GET", p, e)
            return self.enviar(500, {"erro": str(e)})

    def estatico(self, p):
        rel = "index.html" if p == "/" else p.lstrip("/")
        alvo = os.path.realpath(os.path.join(WWW, rel))
        if not alvo.startswith(os.path.realpath(WWW) + os.sep) or not os.path.isfile(alvo):
            return self.enviar(404, {"erro": "não encontrado"})
        with open(alvo, "rb") as f:
            corpo = f.read()
        tipo = TIPOS_MIME.get(os.path.splitext(alvo)[1], "application/octet-stream")
        return self.enviar(200, corpo, tipo)

    # ---- PUT/POST
    def do_PUT(self):
        if not self.permitido():
            return
        p = self.caminho()
        try:
            if p == "/api/state":
                return self.put_state(self.corpo_json())
            if p == "/api/indices":
                return self.put_indices(self.corpo_json())
            return self.enviar(404, {"erro": "não encontrado"})
        except ValueError as e:
            return self.enviar(400, {"erro": str(e)})
        except Exception as e:  # noqa: BLE001
            log("Erro PUT", p, e)
            return self.enviar(500, {"erro": str(e)})

    def do_POST(self):
        if not self.permitido():
            return
        p = self.caminho()
        try:
            if p == "/api/indices/atualizar":
                return self.enviar(200, atualizar_indices())
            if p == "/api/backup":
                return self.post_backup()
            if p == "/api/fotos":
                return self.enviar(200, salvar_foto(self.corpo_json()))
            if p == "/api/ia/ler":
                return self.enviar(200, ia_ler(self.corpo_json()))
            if p == "/api/importar":
                d = importar(self.corpo(), self.headers.get("X-Nome-Arquivo"))
                return self.enviar(200, d)
            if p == "/api/versoes/restaurar":
                return self.restaurar(self.corpo_json().get("nome", ""))
            return self.enviar(404, {"erro": "não encontrado"})
        except (ValueError, zipfile.BadZipFile) as e:
            return self.enviar(400, {"erro": str(e)})
        except Exception as e:  # noqa: BLE001
            log("Erro POST", p, e)
            return self.enviar(500, {"erro": str(e)})

    def put_state(self, corpo):
        with TRAVA:
            atual = ler()
            if int(corpo.get("rev", -1)) != atual["rev"]:
                return self.enviar(409, atual)
            for k in CAMPOS_USUARIO:
                if k in corpo:
                    atual[k] = corpo[k]
            if corpo.get("substituir_historico") and isinstance(corpo.get("historico"), list):
                atual["historico"] = corpo["historico"]
            d = normalizar(atual)
            d["rev"] = atual["rev"] + 1
            salvar(d)
        return self.enviar(200, d)

    def put_indices(self, corpo):
        with TRAVA:
            d = ler()
            ind = d["indices"]
            mudou = False
            for k in ("cdi", "selic", "ipca", "tr"):
                if k in corpo:
                    v = float(corpo[k])
                    if not -50 < v < 200:
                        raise ValueError("Valor fora do esperado.")
                    if v != ind.get(k):
                        ind[k] = v
                        mudou = True
            if mudou:
                ind["auto"] = False  # valor digitado à mão não é sobrescrito sozinho
            if "auto" in corpo:
                ind["auto"] = bool(corpo["auto"])
            if mudou:
                ind["fonte"] = "manual"
                ind["atualizado_em"] = agora_iso()
                ind["erro"] = None
            salvar(d, versao=False)
        return self.enviar(200, d)

    def post_backup(self):
        os.makedirs(SHARE_DIR, exist_ok=True)
        nome = nome_arquivo("zip")
        caminho = os.path.join(SHARE_DIR, nome)
        with open(caminho, "wb") as f:
            f.write(gerar_zip(ler()))
        return self.enviar(200, {"arquivo": nome, "pasta": "share/gerencia"})

    def restaurar(self, nome):
        if not re.fullmatch(r"gerencia-[\w\-]+\.json", nome or ""):
            raise ValueError("Versão inválida.")
        origem = os.path.join(VERSOES, nome)
        if not os.path.isfile(origem):
            raise ValueError("Essa versão não existe mais.")
        with open(origem, encoding="utf-8") as f:
            antiga = normalizar(json.load(f))
        with TRAVA:
            atual = ler()
            guardar_versao("antes-de-restaurar", forcar=True)
            antiga["rev"] = atual["rev"] + 1
            antiga["indices"] = atual["indices"]
            salvar(antiga, versao=False)
        return self.enviar(200, antiga)


def listar_versoes():
    if not os.path.isdir(VERSOES):
        return []
    saida = []
    for nome in sorted(os.listdir(VERSOES), reverse=True):
        if not nome.endswith(".json"):
            continue
        m = re.match(r"gerencia-(\d{8})-(\d{6})-?(.*)\.json", nome)
        caminho = os.path.join(VERSOES, nome)
        try:
            with open(caminho, encoding="utf-8") as f:
                d = normalizar(json.load(f))
            t = calc.totais(d)
        except (OSError, ValueError):
            continue
        quando = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").isoformat() if m else None
        saida.append({"nome": nome, "quando": quando, "motivo": (m.group(3) if m else "") or "auto",
                      "investimentos": t["quantidade"], "total": t["total"]})
    return saida


# ---------------------------------------------------------------- rotina

def rotina():
    """Atualiza índices (a cada 12 h), grava o ponto do dia e republica os sensores a cada 15 min."""
    while True:
        try:
            d = ler()
            ind = d["indices"]
            precisa = ind.get("auto", True) and (
                not ind.get("atualizado_em")
                or ind.get("fonte") == "padrao"
                or datetime.now() - datetime.fromisoformat(ind["atualizado_em"]) > timedelta(hours=12))
            if precisa:
                d = atualizar_indices()
            hoje = date.today().isoformat()
            if d.get("investimentos") and not any(h.get("d") == hoje for h in d.get("historico", [])):
                with TRAVA:
                    d = ler()
                    salvar(d, versao=False)
            else:
                publicar_sensores_async(d)
            limpar_fotos(d)
        except Exception as e:  # noqa: BLE001
            log("Rotina:", e)
        time.sleep(15 * 60)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    threading.Thread(target=rotina, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", PORTA), Handler)
    log(f"GerencIA {VERSAO} ouvindo na porta {PORTA} (dados em {DATA_DIR})")
    srv.serve_forever()


if __name__ == "__main__":
    main()
