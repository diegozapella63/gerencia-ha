#!/usr/bin/env python3
"""GerencIA: servidor do app do Home Assistant (só biblioteca padrão do Python).

Dados em /data/gerencia.json, versões em /data/versoes, backups em /share/gerencia.
"""
import base64
import csv
import html
import io
import json
import math
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
import integracao  # noqa: E402
import assinaturas  # noqa: E402
import voz  # noqa: E402
import bens  # noqa: E402
import chat  # noqa: E402
import ferramentas  # noqa: E402
import avisos  # noqa: E402
import pdfsenha  # noqa: E402
import emails  # noqa: E402
import pdf  # noqa: E402

VERSAO = "1.39.0"
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
HA_WS = os.environ.get("GERENCIA_HA_WS", "ws://supervisor/core/websocket")
IA_MOCK = os.environ.get("GERENCIA_IA_MOCK") == "1"
RE_FOTO = re.compile(r"[0-9]{8}-[0-9]{6}-[0-9a-f]{6}\.jpg")
DEV = os.environ.get("GERENCIA_DEV") == "1"
TOKEN = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HASSIO_TOKEN")
# O ingress do Home Assistant sempre chega por este endereço.
PERMITIDOS = {"172.30.32.2", "127.0.0.1", "::1"}

MAX_VERSOES = 3
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

# sensores: desligado até ligar em Mais › Configurações › Integrações; sensores_v marca os dados que já têm essa escolha
# cor_dia: a Cor do dia (Mais › Configurações › Aparência), ligada por padrão, também para quem já tinha escolhido uma cor
AJUSTES_PADRAO = {"tema": "auto", "cor": "#56AEFF", "cor_dia": True, "corrigir": True, "sensores": False, "sensores_v": 2, "ia_entidade": "", "voz_motor": "", "integracao": True, "bens": True, "bens_taxas": {},
                  "ia": True, "dicas": True, "dicas_auto": True, "dicas_freq": "mes", "dicas_hora": "08:00", "dicas_aviso": False, "dicas_para": [],
                  "email": False, "email_de": [], "email_aviso": False, "email_para": [], "correria": False}
# Conferir sozinho: de quanto em quanto tempo os preços das assinaturas são conferidos de novo na página oficial
DICAS_FREQ = {"semana": 7, "quinzena": 15, "mes": 30}
HORA_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
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
        # antes os sensores vinham ligados sem ninguém escolher: agora ficam desligados até ligar
        if "sensores_v" not in d["ajustes"]:
            base["ajustes"]["sensores"] = False
    # só um "desligado" de verdade desliga a Cor do dia
    base["ajustes"]["cor_dia"] = base["ajustes"].get("cor_dia") is not False
    # Dicas de economia: conferir sozinho (no horário) e avisar no celular de quem foi escolhido
    aj = base["ajustes"]
    aj["dicas_auto"] = aj.get("dicas_auto") is not False
    aj["dicas_aviso"] = aj.get("dicas_aviso") is True
    aj["dicas_hora"] = aj.get("dicas_hora") if HORA_RE.match(str(aj.get("dicas_hora") or "")) else AJUSTES_PADRAO["dicas_hora"]
    aj["dicas_freq"] = aj.get("dicas_freq") if aj.get("dicas_freq") in DICAS_FREQ else AJUSTES_PADRAO["dicas_freq"]
    para = aj.get("dicas_para") if isinstance(aj.get("dicas_para"), list) else []
    aj["dicas_para"] = list(dict.fromkeys(p for p in para if isinstance(p, str) and avisos.PESSOA_RE.match(p)))[:20]
    # Faturas por e-mail: de quem (endereço ou o fim dele, como bancoazul.com.br) e quem recebe o aviso no celular
    aj["email"] = aj.get("email") is True
    aj["correria"] = aj.get("correria") is True
    aj["email_aviso"] = aj.get("email_aviso") is True
    de = aj.get("email_de") if isinstance(aj.get("email_de"), list) else []
    aj["email_de"] = list(dict.fromkeys(x for x in (emails.limpar_remetente(r) for r in de if isinstance(r, str)) if x))[:20]
    para = aj.get("email_para") if isinstance(aj.get("email_para"), list) else []
    aj["email_para"] = list(dict.fromkeys(p for p in para if isinstance(p, str) and avisos.PESSOA_RE.match(p)))[:20]
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

BCB = os.environ.get("GERENCIA_BCB", "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{s}/dados")  # GERENCIA_BCB: só para testes
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

SENSORES = ("sensor.gerencia_patrimonio", "sensor.gerencia_meu", "sensor.gerencia_terceiros",
            "sensor.gerencia_rendimento_mensal", "sensor.gerencia_saldo_caixa", "sensor.gerencia_entradas_mes",
            "sensor.gerencia_saidas_mes", "sensor.gerencia_ia_hoje", "sensor.gerencia_bens")
_sensores = {"ligado": None}  # o último estado visto: desligar apaga os sensores uma vez


def sensores_ligados(d):
    return (d or {}).get("ajustes", {}).get("sensores") is True


def remover_sensores():
    """Sensores no Home Assistant desligado: os sensores que o app criou somem do Home Assistant."""
    for ent in SENSORES:
        req = urllib.request.Request(f"{HA_API}/states/{ent}", method="DELETE",
                                     headers={"Authorization": f"Bearer {TOKEN}"})
        try:
            urllib.request.urlopen(req, timeout=10).read()
        except Exception:  # noqa: BLE001  (já não existia, ou o Home Assistant está fora: some no próximo reinício)
            pass


def publicar_sensores(d):
    if not TOKEN:
        return
    ligado = sensores_ligados(d)
    antes, _sensores["ligado"] = _sensores["ligado"], ligado
    if not ligado:
        if antes is not False:
            remover_sensores()
        return
    t = calc.totais(d)
    base = {"unit_of_measurement": "BRL", "device_class": "monetary", "state_class": "total"}
    sensores = {
        # o patrimônio é só o seu: o dinheiro de terceiros fica de fora (em de_terceiros e com_terceiros)
        "sensor.gerencia_patrimonio": (t["meu"], "GerencIA Patrimônio", "mdi:cash-multiple",
                                       {"seu": t["meu"], "de_terceiros": t["terceiros"], "com_terceiros": t["total"],
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
    b = bens_estado(d)
    if b.get("ok"):
        sensores["sensor.gerencia_bens"] = (b["hoje"], "GerencIA Bens da casa", "mdi:sofa", {"registrado": b["registrado"], "perde_por_ano": b["perde_ano"], "itens": b["n"]})
        sensores["sensor.gerencia_patrimonio"][3]["com_bens"] = round(t["meu"] + b["hoje"], 2)
    for ent, (valor, nome, icone, extra) in sensores.items():
        corpo = json.dumps({"state": valor, "attributes": {**base, "friendly_name": nome, "icon": icone, **extra}})
        req = urllib.request.Request(
            f"{HA_API}/states/{ent}", data=corpo.encode(), method="POST",
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=10).read()
        except Exception as e:  # noqa: BLE001
            log("Sensor", ent, "não publicado:", e)
            return
    if antes is not True:
        publicar_uso_sensor()


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
    aportes = {r.get("id") for r in d["recorrencias"] if r.get("aporte")}
    for l in sorted(d["lancamentos"], key=lambda x: str(x.get("data") or "")):
        if l.get("pulado"):
            continue
        rec = l.get("tipo") == "receita"
        aporte = l.get("aporte") or l.get("recorrencia") in aportes
        dc = calc.data_caixa(l, contas, d)
        w.writerow([l.get("data") or "", dc.isoformat() if dc else "", "Recebimento" if rec else "Aporte" if aporte else "Despesa",
                    l.get("descricao", ""), cats.get(l.get("categoria"), "Ajuste de saldo" if l.get("ajuste") else ""),
                    calc.nome_conta(contas.get(l.get("conta"))), "Sim" if l.get("cartao") else "",
                    calc.fmt_num(calc.num(l.get("valor"))),
                    ("Recebido" if rec else "Pago") if l.get("pago") else ("A receber" if rec else "A pagar"),
                    l.get("parcela") or "", "Sim" if l.get("recorrencia") else "", l.get("obs", "")])
        for x in calc.descontos_de(l):
            w.writerow([l.get("data") or "", dc.isoformat() if dc else "", "Desconto do recebimento",
                        f'{x["descricao"]} (de {l.get("descricao", "")})', cats.get(x.get("categoria"), ""),
                        calc.nome_conta(contas.get(l.get("conta"))), "", calc.fmt_num(x["valor"]),
                        "Pago" if l.get("pago") else "A pagar", "", "Sim" if l.get("recorrencia") else "", ""])
    for r in d["recorrencias"]:
        anual = r.get("freq") == "anual"
        quando = f"todo ano, dia {r.get('dia')}/{str(r.get('inicio') or '')[5:7]}" if anual else f"todo dia {r.get('dia')}"
        w.writerow([quando, "", "Recebimento fixo" if r.get("tipo") == "receita" else "Aporte mensal" if r.get("aporte") else "Despesa fixa",
                    r.get("descricao", ""), cats.get(r.get("categoria"), ""), calc.nome_conta(contas.get(r.get("conta"))),
                    "Sim" if r.get("cartao") else "", calc.fmt_num(calc.num(r.get("valor"))),
                    f"desde {r.get('inicio')}" + (f" até {r['fim']}" if r.get("fim") else ""), "", "Anual" if anual else "Sim", r.get("obs", "")])
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
                   "Para restaurar: Mais > Configurações > Dados > Importar, e escolha este .zip.\n")
    return buf.getvalue()


def nome_arquivo(ext):
    return f"gerencia-{datetime.now().strftime('%Y-%m-%d-%H%M')}.{ext}"


RE_BACKUP = re.compile(r"gerencia-[\w\-]+\.zip")


def listar_backups():
    if not os.path.isdir(SHARE_DIR):
        return []
    saida = []
    for nome in os.listdir(SHARE_DIR):
        caminho = os.path.join(SHARE_DIR, nome)
        if RE_BACKUP.fullmatch(nome) and os.path.isfile(caminho):
            st = os.stat(caminho)
            saida.append({"nome": nome, "tamanho": st.st_size, "quando": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")})
    return sorted(saida, key=lambda b: b["quando"], reverse=True)[:12]


def restaurar_backup(nome):
    if not RE_BACKUP.fullmatch(nome or "") or not os.path.isfile(os.path.join(SHARE_DIR, nome)):
        raise ValueError("Esse backup não existe mais.")
    with open(os.path.join(SHARE_DIR, nome), "rb") as f:
        return importar(f.read(), nome)


# ---------------------------------------------------------------- relatório

QUEM = {"todos": "Todos", "meus": "Meus", "terceiros": "De terceiros"}


def bens_relatorio(d):
    """Os itens do InventarIA para o relatório, quando Bens no InventarIA está ligado: {"itens", "categorias", "aviso"}.
    Instalado mas sem responder: sem itens, com o aviso; não instalado: nada (como no Início)."""
    if d["ajustes"].get("bens") is False or not BENS.conexao():
        return None
    try:
        dados = BENS.ler()
    except Exception as e:  # noqa: BLE001
        log("Bens no relatório:", e)
        return {"itens": [], "categorias": {}, "aviso": "Não consegui ler o InventarIA: os bens da casa ficaram de fora."}
    return {"itens": bens.itens_hoje(dados, d["ajustes"]), "categorias": dados.get("categorias") or {}, "aviso": ""}


COLUNAS_INVEST = ["Investimento", "Banco", "Rendimento", "Vencimento"]
COLUNAS_BENS = ["Bem", "Cômodo", "Por ano", "Informado em"]


def dados_relatorio(d, quem="todos", agora=None, inventario=None, detalhar=False):
    """O que vai no Relatório de patrimônio (na página e no PDF). quem: todos, meus ou terceiros. inventario: os itens do
    InventarIA (bens_relatorio), que entram em Bens junto com os bens cadastrados aqui (os seus; não em De terceiros).
    Patrimônio é o mesmo do Início: os seus investimentos e os bens; o dinheiro de terceiros fica à parte.
    detalhar: os bens um por um; sem ele, uma linha para os imóveis e outra para os outros bens (Detalhar bens e imóveis)."""
    quem = quem if quem in QUEM else "todos"
    ind = d["indices"]
    corrigir = d["ajustes"].get("corrigir", True)
    bancos = {b.get("id"): b for b in d["bancos"]}
    invs = [i for i in d["investimentos"]
            if quem == "todos" or (quem == "terceiros") == (i.get("titular") == "terceiros")]
    vh = {id(i): calc.valor_hoje(i, ind, corrigir) for i in invs}
    # quanto muda por mês e o valor em 1 e em 5 anos (com as taxas de hoje, sem aportes, antes do IR)
    fut = {id(i): {"mes": calc.valor_em(i, ind, 1 / 12, corrigir) - calc.valor_em(i, ind, 0, corrigir),
                   "ano1": calc.valor_em(i, ind, 1, corrigir), "ano5": calc.valor_em(i, ind, 5, corrigir)} for i in invs}
    e_bem = lambda i: i.get("tipo") == "bens"  # noqa: E731
    meu = lambda i: i.get("titular") != "terceiros"  # noqa: E731
    nomes_cat = dict(bens.NOMES_PADRAO, **((inventario or {}).get("categorias") or {}))

    def linha_inv(inv, data_bem=True):
        venc = calc.parse_data(inv.get("vencimento"))
        if e_bem(inv):  # um bem cadastrado aqui (um carro, um terreno…): a categoria no lugar do tipo; a data só em Bens
            ps = inv.get("partes") if isinstance(inv.get("partes"), list) else []
            cat = f"{len(ps)} categorias" if len(ps) > 1 else nomes_cat.get((ps[0].get("categoria") if ps else inv.get("categoria_bem")) or "outros", "Outros")
            dv = calc.parse_data(inv.get("data_valor"))
            return {"nome": inv.get("nome", ""), "tipo": cat, "banco": "", "rendimento": calc.rotulo_taxa(inv),
                    "vencimento": dv.strftime("%d/%m/%Y") if dv and data_bem else "", "valor": vh[id(inv)], **fut[id(inv)]}
        return {"nome": inv.get("nome", ""), "tipo": calc.TIPOS.get(inv.get("tipo"), ""),
                "banco": bancos.get(inv.get("banco"), {}).get("nome", ""), "rendimento": calc.rotulo_taxa(inv),
                "vencimento": venc.strftime("%d/%m/%Y") if venc else ("Diária" if inv.get("liquidez") == "diaria" else ""),
                "valor": vh[id(inv)], **fut[id(inv)]}

    def linha_casa(it):
        h, t = it["hoje"], it["taxa"] / 100
        dv = calc.parse_data(it.get("valor_em"))
        return {"nome": it["nome"], "tipo": it["categoria_nome"], "banco": it["comodo_nome"],
                "rendimento": calc.rotulo_taxa({"indexador": "deprecia", "taxa": it["taxa"]}),
                "vencimento": dv.strftime("%d/%m/%Y") if dv else "", "valor": h,
                "mes": h * ((1 - t) ** (1 / 12) - 1), "ano1": h * (1 - t), "ano5": h * (1 - t) ** 5}

    def secao(titulo, linhas, colunas):
        linhas = sorted(linhas, key=lambda l: -l["valor"])
        return {"titulo": titulo, "colunas": colunas, "linhas": linhas, "total": sum(l["valor"] for l in linhas),
                **{k: sum(l[k] for l in linhas) for k in ("mes", "ano1", "ano5")}}

    secoes = []
    seus = [i for i in invs if meu(i) and not e_bem(i)]
    if seus:
        secoes.append(secao("Seu dinheiro", [linha_inv(i) for i in seus], COLUNAS_INVEST))
    itens_casa = ((inventario or {}).get("itens") or []) if quem != "terceiros" else []
    da_casa = [linha_casa(it) for it in itens_casa]
    meus_bens = [i for i in invs if meu(i) and e_bem(i)]
    bens_seus = [linha_inv(i) for i in meus_bens] + da_casa
    # cada pedaço de bem (um item do InventarIA, um bem daqui ou uma parte dele): de quem é (para contar), categoria,
    # valor de hoje e a taxa da categoria; dá o resumo em duas linhas (imóveis e os outros bens)
    pedacos = [(("c", k), it["categoria"], it["hoje"], it["taxa"]) for k, it in enumerate(itens_casa)]
    pedacos += [(("i", k), p["categoria"], p["valor"], p["taxa"]) for k, inv in enumerate(meus_bens) for p in calc.partes_hoje(inv, ind, corrigir)]
    tem_imoveis = any(c == "imoveis" and v > 0 for _, c, v, _ in pedacos)
    if bens_seus:
        titulo_bens = "Bens e imóveis" if tem_imoveis else "Bens"
        if detalhar:
            secoes.append(secao(titulo_bens, bens_seus, COLUNAS_BENS))
        else:
            resumidas = []
            for nome, dos_imoveis in (("Imóveis", True), ("Bens", False)):
                ps = [x for x in pedacos if (x[1] == "imoveis") == dos_imoveis]
                if not ps:
                    continue
                v = sum(x[2] for x in ps)
                proj = {k: sum(x[2] * (1 - x[3] / 100) ** anos for x in ps) for k, anos in (("ano1", 1), ("ano5", 5))}
                mes = sum(x[2] * ((1 - x[3] / 100) ** (1 / 12) - 1) for x in ps)
                n = len({x[0] for x in ps})
                var = (proj["ano1"] / v - 1) * 100 if v else 0  # quanto o grupo muda num ano, em %
                rot = "mantém o valor" if abs(var) < 0.005 else f"{'valoriza' if var > 0 else 'perde'} {calc.fmt_pct(round(abs(var), 1))}% a.a."
                resumidas.append({"nome": nome, "tipo": f"{n} {'item' if n == 1 else 'itens'}", "banco": "", "rendimento": rot,
                                  "vencimento": "", "valor": v, "mes": mes, **proj})
            secoes.append(secao(titulo_bens, resumidas, ["Bem", "", "Por ano", ""]))
    grupos = {}
    for inv in invs:
        if not meu(inv):
            grupos.setdefault(calc.dono(inv), []).append(inv)
    for p in sorted(grupos, key=str.lower):
        secoes.append(secao(f"De {p}", [linha_inv(i, False) for i in grupos[p]], COLUNAS_INVEST))

    por_banco = {}
    for inv in invs:
        if not e_bem(inv):
            nome = bancos.get(inv.get("banco"), {}).get("nome", "Sem banco")
            por_banco[nome] = por_banco.get(nome, 0) + vh[id(inv)]
    total_bancos = sum(por_banco.values())
    investido = sum(vh[id(i)] for i in seus)
    v_bens = sum(l["valor"] for l in bens_seus)
    terc = sum(vh[id(i)] for i in invs if not meu(i))
    # com Corrigir valores pelo rendimento desligado, o valor de hoje é o último informado (sem estimar pelos índices)
    rodape = (f"Valores de hoje estimados a partir do último valor informado e dos índices: CDI {calc.fmt_pct(calc.num(ind.get('cdi')))}% a.a., "
              f"Selic {calc.fmt_pct(calc.num(ind.get('selic')))}% a.a., IPCA {calc.fmt_pct(calc.num(ind.get('ipca')))}% em 12 meses."
              if corrigir else "Valores de hoje: o último valor informado de cada investimento.") + " Antes do imposto de renda."
    com_bens = ([("Investido", investido)] if investido else []) + [("Bens", v_bens)] if v_bens else []
    resumo = {"todos": [("Patrimônio", investido + v_bens)] + com_bens + [("De terceiros", terc)],
              "meus": [("Patrimônio", investido + v_bens)] + com_bens, "terceiros": [("De terceiros", terc)]}[quem]
    return {"quem": quem, "gerado": (agora or datetime.now()).strftime("%d/%m/%Y às %H:%M"),
            "quantidade": sum(1 for i in invs if not e_bem(i)), "n_bens": sum(1 for i in invs if e_bem(i)) + len(da_casa),
            "total": total_bancos, "resumo": resumo, "secoes": secoes, "rodape": rodape, "cor": calc.cor_app(d["ajustes"]),
            "bancos": [(n, v, v / total_bancos * 100 if total_bancos else 0) for n, v in sorted(por_banco.items(), key=lambda x: -x[1])],
            "aviso": ((inventario or {}).get("aviso") or "") if quem != "terceiros" else "",
            "detalhar": bool(detalhar), "tem_bens": bool(bens_seus), "tem_imoveis": tem_imoveis,
            "vazio": {"todos": "Nenhum investimento cadastrado.", "meus": "Nenhum investimento seu.",
                      "terceiros": "Nenhum investimento de outras pessoas."}[quem]}


def _contagem(r):
    """30 investimentos em 3 bancos · 12 bens"""
    nb = sum(1 for n, _, _ in r["bancos"] if n != "Sem banco")
    partes = [_n_invest(r["quantidade"]) + (f" em {nb} banco{'' if nb == 1 else 's'}" if nb else "")] if r["quantidade"] or not r["n_bens"] else []
    if r["n_bens"]:
        partes.append(f"{r['n_bens']} {'bem' if r['n_bens'] == 1 else 'bens'}")
    return " · ".join(partes)


def _n_invest(n):
    return f"{n} investimento{'' if n == 1 else 's'}"


def nome_relatorio(quem):
    """patrimonio-AAAA-MM-DD.pdf (todos) ou com -meus / -terceiros; outra coisa no pedido vale como todos."""
    return f"patrimonio-{date.today().isoformat()}" + (f"-{quem}" if quem in ("meus", "terceiros") else "") + ".pdf"


# o ícone do app (icon.svg), com o $ na cor do app
ICONE_SVG = ('<svg class="ic" viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="14" fill="#0c0f13"/>'
             '<rect x="10" y="17" width="21" height="30" rx="3" fill="#1b2129"/><rect x="10" y="17" width="21" height="15" rx="3" fill="#262d37"/>'
             '<rect x="33" y="17" width="21" height="30" rx="3" fill="#1b2129"/><rect x="33" y="17" width="21" height="15" rx="3" fill="#262d37"/>'
             '<text x="20.5" y="41.5" font-family="Barlow Condensed,Arial Narrow,sans-serif" font-weight="700" font-size="25" text-anchor="middle" fill="#f3f5f8">R</text>'
             '<text x="43.5" y="41.5" font-family="Barlow Condensed,Arial Narrow,sans-serif" font-weight="700" font-size="25" text-anchor="middle" fill="var(--a)">$</text>'
             '<rect x="10" y="31.3" width="44" height="1.4" fill="#05070a"/></svg>')
FILTRO_SUB = {"todos": "", "meus": "Só os seus · ", "terceiros": "De terceiros · "}
# no fim do relatório, a marca da CorrerIA Code como no Mais › Sobre (a mesma do ResolvIA e do InventarIA): o raio no
# quadrado inclinado na cor do app, Correr IA Code e DESENVOLVIMENTO DE SOFTWARES
RAIO = [(13, 2), (3, 14), (12, 14), (11, 22), (21, 10), (12, 10)]  # o zap do Lucide, numa caixa de 24
MARCA = ('<footer class="marca"><span class="raio" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M'
         + "L".join(f"{x} {y}" for x, y in RAIO) + 'Z"/></svg></span><span><b class="nome">Correr<i>IA</i> Code</b>'
         '<small>desenvolvimento de softwares</small></span></footer>')
# Baixar PDF: a página fica num quadro da página do Home Assistant, e o app do Home Assistant no Android só baixa o que
# a página de cima pede (o link do quadro não faz nada lá). O link vai para lá e é clicado, como o Home Assistant faz
# com os backups (mesma origem, pelo ingress); sem isso (outra origem, sem quadro), o link baixa como sempre. O mesmo
# do ResolvIA (lib/report.js) e do InventarIA.
BAIXAR = ("try{var d=window.top.document,a=d.createElement('a');a.href=this.href;a.download=this.getAttribute('download')||'';a.target='_blank';"
          "a.style.display='none';d.body.appendChild(a);a.dispatchEvent(new MouseEvent('click'));d.body.removeChild(a);var b=this;"
          "b.textContent='Baixando…';setTimeout(function(){b.textContent='Baixar PDF'},4000);return false}catch(e){return true}")
RODAPE = "CorrerIA Code · desenvolvimento de softwares"  # quem faz o app (o mesmo do Mais › Sobre)


def notas_relatorio(r):
    """As notas do pé: como as colunas são calculadas e de onde vêm os valores."""
    notas = []
    if r["secoes"]:
        notas.append("Por mês, em 1 ano e em 5 anos: com as taxas de hoje, sem novos aportes e reaplicando o que vence.")
    if r["tem_bens"]:
        notas.append("Bens: perdem ou ganham por ano a taxa da categoria (Mais › Invest), contada desde a data informada.")
    return notas + [r["rodape"]]


def gerar_relatorio(d, tema=None, quem="todos", inventario=None, detalhar=False):
    """O relatório de patrimônio em HTML, para ver; Baixar PDF leva ao mesmo relatório em PDF (o app do Home Assistant no
    Android não imprime a página). tema: "claro" ou "escuro" (o app manda o que está usando); sem ele, vale o de
    Mais › Aparência e, no automático, o do Home Assistant ou do aparelho. No papel é sempre claro. quem: todos, meus ou
    terceiros. inventario: os itens do InventarIA (bens_relatorio). detalhar: os bens um por um (senão, imóveis e bens
    em duas linhas); o interruptor da página começa desligado e vai junto no filtro e no Baixar PDF.
    O cabeçalho é o dos relatórios dos outros apps (o do ResolvIA): o ícone, o app, o título, a contagem e quando;
    no pé, só quem faz o app."""
    tema = tema if tema in ("claro", "escuro") else d["ajustes"].get("tema") if d["ajustes"].get("tema") in ("claro", "escuro") else None
    attr_tema = {"claro": ' data-theme="light"', "escuro": ' data-theme="dark"'}.get(tema, "")
    r = dados_relatorio(d, quem, inventario=inventario, detalhar=detalhar)
    e = html.escape
    q_det = "&detalhar=1" if r["detalhar"] else ""
    q_tema = f"&tema={tema}" if tema else ""

    partes = []
    for s in r["secoes"]:
        linhas = "".join(
            # no celular a 2ª coluna (banco ou cômodo) some e vai embaixo do nome (senão o valor fica cortado)
            "<tr><td>{}<small>{}<span class=bm>{}</span></small></td><td>{}</td><td>{}</td><td>{}</td><td class=n>{}</td></tr>".format(
                e(l["nome"]), e(l["tipo"]), ((" · " if l["tipo"] else "") + e(l["banco"])) if l["banco"] else "",
                e(l["banco"]), e(l["rendimento"]), e(l["vencimento"]), calc.fmt_brl(l["valor"]))
            for l in s["linhas"])
        cab = "".join(f"<th>{e(c)}</th>" for c in s["colunas"])
        partes.append(f"<section><h2><span>{e(s['titulo'])}</span><b>{calc.fmt_brl(s['total'])}</b></h2>"
                      f"<table class=inv><thead><tr>{cab}<th class=n>Valor hoje</th></tr></thead><tbody>" + linhas + "</tbody></table></section>")
    if r["bancos"]:
        bancos_html = "".join(f"<tr><td>{e(n)}</td><td class=n>{calc.fmt_brl(v)}</td><td class=n>{calc.fmt_pct(p)}%</td></tr>"
                              for n, v, p in r["bancos"])
        partes.append(f"""<section><h2><span>Por banco</span><b>{calc.fmt_brl(r['total'])}</b></h2>
<table><thead><tr><th>Banco</th><th class=n>Valor</th><th class=n>Parte</th></tr></thead><tbody>{bancos_html}</tbody></table></section>""")
    if not r["secoes"]:
        partes.append(f'<p class="vazio">{e(r["vazio"])}</p>')
    # trocar o filtro não empilha páginas: o Voltar (e o do celular) volta direto ao app
    filtro = "".join(f'<a href="relatorio?quem={k}{q_det}{q_tema}" onclick="location.replace(this.href);return false"'
                     f'{" class=on aria-current=page" if k == r["quem"] else ""}>{n}</a>' for k, n in QUEM.items())
    resumo = "".join(f"<div><span>{n}</span><b>{calc.fmt_brl(v)}</b></div>" for n, v in r["resumo"])
    notas = "".join(f"<p>{e(n)}</p>" for n in notas_relatorio(r))
    rotulo_det = "Detalhar bens e imóveis" if r["tem_imoveis"] else "Detalhar bens"
    detalhe = (f'<a class="det" role="switch" aria-checked="{"true" if r["detalhar"] else "false"}" href="relatorio?quem={r["quem"]}'
               f'{"" if r["detalhar"] else "&detalhar=1"}{q_tema}" onclick="location.replace(this.href);return false">'
               f'<span>{rotulo_det}</span><i class="sw{" on" if r["detalhar"] else ""}"></i></a>') if r["tem_bens"] else ""
    cabecalho = (f'<header class="cab">{ICONE_SVG}<div><div class="app"><span class="wm">Gerenc<b>IA</b></span> · finanças</div>'
                 f'<h1>Relatório de patrimônio</h1>'
                 f'<p>{FILTRO_SUB[r["quem"]]}{e(_contagem(r))} · {r["gerado"]}</p></div></header>')

    claro = "--bg:#f6f7f9;--card:#fff;--fg:#141a22;--mut:#5b6573;--linha:#e3e7ec;--linha2:#eef1f4;--borda:#d6dbe2;--seg:#e9edf1"
    escuro = "--bg:#0f1318;--card:#161c23;--fg:#e8edf3;--mut:#9aa6b4;--linha:#2a3340;--linha2:#1f2732;--borda:#334051;--seg:#0b0f14"
    # no automático, sem o tema do app: o do Home Assistant (a página abre dentro dele) ou o do aparelho
    script_tema = "" if tema else """<script>try{var h=parent!==window?parent.document.querySelector('home-assistant'):null,m=h&&h.hass&&h.hass.themes?h.hass.themes.darkMode:null;
if(typeof m==='boolean')document.documentElement.setAttribute('data-theme',m?'dark':'light')}catch(e){}</script>"""
    return f"""<!doctype html><html lang="pt-BR"{attr_tema}><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Relatório de patrimônio · GerencIA</title>{script_tema}
<style>
:root{{--a:{r['cor']};{claro};color-scheme:light}}
:root[data-theme="dark"]{{{escuro};color-scheme:dark}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{{escuro};color-scheme:dark}}}}
@font-face{{font-family:Barlow;font-weight:400;src:url(fonts/barlow-400.woff2) format("woff2")}}
@font-face{{font-family:Barlow;font-weight:600;src:url(fonts/barlow-600.woff2) format("woff2")}}
@font-face{{font-family:"Barlow Condensed";font-weight:700;src:url(fonts/barlow-condensed-700.woff2) format("woff2")}}
*{{box-sizing:border-box}}
body{{font:15px/1.45 Barlow,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--fg);background:var(--bg);margin:0;padding:20px 16px 48px}}
main{{max-width:860px;margin:0 auto}}
.filtro{{display:flex;gap:4px;padding:4px;border-radius:12px;background:var(--seg);border:1px solid var(--linha);margin:0 0 8px}}
.filtro a{{flex:1;text-align:center;padding:8px 6px;border-radius:9px;color:var(--mut);text-decoration:none;font-weight:600;font-size:14px}}
.filtro a.on{{background:var(--card);color:var(--fg);box-shadow:0 1px 2px rgba(0,0,0,.15)}}
.barra{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:18px}}
.barra a{{display:flex;align-items:center;justify-content:center;min-height:44px;font:inherit;font-size:14px;font-weight:600;padding:8px 10px;border-radius:12px;border:1px solid var(--borda);background:var(--card);color:var(--fg);text-decoration:none}}
.barra a.pri{{background:var(--a);border-color:transparent;color:#0b0f14}}
.det{{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:-8px 0 18px;padding:10px 14px;border-radius:12px;border:1px solid var(--linha);background:var(--card);color:var(--fg);text-decoration:none;font-weight:600;font-size:14px}}
.det .sw{{flex:none;width:44px;height:26px;border-radius:13px;background:var(--borda);position:relative}}
.det .sw::after{{content:"";position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:#fff;transition:left .15s}}
.det .sw.on{{background:var(--a)}}
.det .sw.on::after{{left:21px}}
.cab{{display:flex;gap:14px;align-items:center;background:var(--card);border:1px solid var(--linha);border-left:6px solid var(--a);border-radius:16px;padding:16px 18px;margin-bottom:14px}}
.cab .ic{{width:52px;height:52px;flex:none}}
.cab .app{{font:600 13.5px/1.2 Barlow,sans-serif;color:var(--mut)}}
.cab .app .wm{{font:700 19px/1 "Barlow Condensed",Barlow,sans-serif;color:var(--fg);letter-spacing:.01em}}
.cab .app .wm b{{color:var(--a)}}
.cab h1{{font:700 30px/1.05 "Barlow Condensed",Barlow,sans-serif;margin:4px 0;letter-spacing:-.01em}}
.cab p{{margin:0;color:var(--mut);font-size:13.5px}}
.resumo{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-bottom:6px}}
.resumo div{{background:var(--card);border:1px solid var(--linha);border-radius:12px;padding:10px 12px}}
.resumo b{{display:block;font:700 26px/1.1 "Barlow Condensed",Barlow,sans-serif;font-variant-numeric:tabular-nums}}
.resumo span{{color:var(--mut);font-size:13px}}
.vazio,.aviso{{color:var(--mut)}}
.vazio{{margin:20px 0}}
.aviso{{margin:10px 0 0;font-size:13px}}
section{{background:var(--card);border:1px solid var(--linha);border-radius:16px;padding:6px 16px 10px;margin-top:14px}}
h2{{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:4px 12px;border-bottom:2px solid var(--a);padding:8px 0 6px;margin:0 0 4px}}
h2 span,h2 b{{font:700 20px/1.2 "Barlow Condensed",Barlow,sans-serif}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th{{text-align:left;color:var(--mut);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em;padding:8px 6px;border-bottom:1px solid var(--linha)}}
td{{padding:9px 6px;border-bottom:1px solid var(--linha2);vertical-align:top}}
tr:last-child td{{border-bottom:0}}
td small{{display:block;color:var(--mut);font-size:12.5px}}
.n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.notas{{color:var(--mut);font-size:12px;margin-top:22px}}
.notas p{{margin:0 0 4px}}
.marca{{display:flex;align-items:center;justify-content:center;gap:12px;margin-top:28px;padding-top:20px;border-top:1px solid var(--linha)}}
.raio{{display:grid;place-items:center;width:34px;height:34px;flex:none;border-radius:11px;background:var(--a);transform:rotate(-8deg);box-shadow:0 8px 18px -10px var(--a)}}
.raio svg{{width:19px;height:19px;fill:#0b0f14}}
.marca .nome{{display:block;font:700 20px/1 "Barlow Condensed",Barlow,sans-serif;color:var(--fg)}}
.marca .nome i{{font-style:normal;color:var(--a)}}
.marca small{{display:block;margin-top:4px;color:var(--mut);font-size:10.5px;font-weight:600;letter-spacing:.14em;text-transform:uppercase}}
.bm{{display:none}}
@media (max-width:600px){{.inv th:nth-child(2),.inv td:nth-child(2),.inv th:nth-child(4),.inv td:nth-child(4){{display:none}} .bm{{display:inline}}}}
@media print{{:root,:root[data-theme],:root:not([data-theme="light"]){{{claro};--bg:#fff;color-scheme:light}} .barra,.filtro,.det{{display:none}} body{{padding:0}} section,.marca{{break-inside:avoid-page}} .cab,section,.resumo div{{border-color:#d6dbe2}} .raio{{box-shadow:none}}}}
</style></head><body><main>
<nav class="filtro" aria-label="De quem">{filtro}</nav>
<div class="barra"><a href="./" onclick="if(history.length>1){{history.back();return false}}">Voltar</a><a class="pri" href="relatorio.pdf?quem={r['quem']}{q_det}" download="{nome_relatorio(r['quem'])}" onclick="{BAIXAR}">Baixar PDF</a></div>
{detalhe}
{cabecalho}
<div class="resumo">{resumo}</div>{f'<p class="aviso">{e(r["aviso"])}</p>' if r["aviso"] else ""}
{''.join(partes)}
<div class="notas">{notas}</div>
{MARCA}
</main></body></html>""".encode("utf-8")


def _icone_pdf(doc, x, y, tam, cor):
    """O ícone do app (o mesmo do icon.svg: R$ em duas plaquinhas), com o $ na cor do app."""
    s = tam / 64
    hx = pdf.cor_rgb
    doc.retangulo(x, y, tam, tam, borda=hx("#2b333e"), fundo=hx("#0c0f13"), esp=0.6, raio=14 * s)
    for tx in (10, 33):
        doc.retangulo(x + tx * s, y + 17 * s, 21 * s, 30 * s, fundo=hx("#1b2129"), raio=3 * s)
        doc.retangulo(x + tx * s, y + 17 * s, 21 * s, 15 * s, fundo=hx("#262d37"), raio=3 * s)
    doc.texto(x + 20.5 * s, y + 41 * s, "R", 23 * s, True, hx("#f3f5f8"), "centro")
    doc.texto(x + 43.5 * s, y + 41 * s, "$", 23 * s, True, cor, "centro")
    doc.retangulo(x + 10 * s, y + 31.3 * s, 44 * s, 1.4 * s, fundo=hx("#05070a"))


def _brl_sinal(v):
    """R$ com o sinal de menos quando perde; perto de zero, um traço."""
    if abs(v) < 0.005:
        return "—"
    return ("−" if v < 0 else "") + calc.fmt_brl(abs(v))


def gerar_relatorio_pdf(d, quem="todos", inventario=None, detalhar=False):
    """O mesmo relatório em PDF (A4 deitada, sempre claro), para baixar e compartilhar: o cabeçalho dos relatórios dos
    apps (o ícone, GerencIA, o título, a contagem e quando, como no ResolvIA), o resumo, os investimentos e os bens (com
    quanto mudam por mês e o valor em 1 e em 5 anos), a divisão por banco e, no pé de cada página, quem faz o app e a página."""
    r = dados_relatorio(d, quem, inventario=inventario, detalhar=detalhar)
    doc = pdf.Documento("Relatório de patrimônio · GerencIA", deitada=True)
    TXT, MUT, LIN, LIN2, CARTAO = (0.08, 0.10, 0.13), (0.36, 0.40, 0.45), (0.85, 0.87, 0.90), (0.92, 0.93, 0.95), pdf.cor_rgb("#f6f7f9")
    COR = pdf.cor_rgb(r["cor"])

    def tom(a):  # a cor do app clareada (a = quanto da cor fica)
        return tuple(1 - a * (1 - c) for c in COR)

    M, W, FIM = 36, doc.largura_pagina - 72, doc.altura_pagina - 62
    DIR = M + W
    # à esquerda, o texto: investimento (ou bem), banco (ou cômodo), rendimento (ou por ano), vencimento (ou data): (x, largura)
    COLS = [(M + 6, 170), (M + 184, 88), (M + 280, 84), (M + 372, 54)]
    # à direita, os valores (a ponta direita de cada um): valor hoje, por mês, em 1 ano, em 5 anos
    NUM = [DIR - 262, DIR - 182, DIR - 94, DIR - 6]
    VALORES = ["Valor hoje", "Por mês", "Em 1 ano", "Em 5 anos"]
    y = [0]

    def topo(primeira=False, continua=None):
        """O alto da página: na primeira, o cartão com o app (como no ResolvIA); nas outras, uma linha com o nome."""
        if primeira:
            t0 = 32
            doc.retangulo(M, t0, W, 88, borda=LIN, fundo=CARTAO, raio=10)
            doc.retangulo(M, t0, 5, 88, fundo=COR)
            _icone_pdf(doc, M + 18, t0 + 18, 52, COR)
            tx = M + 84
            doc.texto(tx, t0 + 24, "Gerenc", 15, True, TXT)
            w1 = pdf.largura("Gerenc", 15, True)
            doc.texto(tx + w1, t0 + 24, "IA", 15, True, COR)
            w2 = pdf.largura("IA", 15, True)
            doc.texto(tx + w1 + w2 + 6, t0 + 24, "· finanças", 10, False, MUT)
            doc.texto(tx, t0 + 52, "Relatório de patrimônio", 22, True, TXT)
            doc.texto(tx, t0 + 72, f"{FILTRO_SUB[r['quem']]}{_contagem(r)} · {r['gerado']}", 10, False, MUT)
            y[0] = t0 + 88 + 14
            return
        doc.texto(M, 42, "Relatório de patrimônio · GerencIA", 9, False, MUT)
        y[0] = 68
        if continua:
            doc.texto(M, y[0], continua + " (continuação)", 11, True, MUT)
            y[0] += 18

    def cabeca_tabela(colunas):
        doc.retangulo(M, y[0] - 12, W, 19, fundo=(0.955, 0.962, 0.972), raio=3)
        for (x, _), t in zip(COLS, colunas):
            doc.texto(x, y[0], t.upper(), 7.5, True, MUT)
        for x, t in zip(NUM, VALORES):
            doc.texto(x, y[0], t.upper(), 7.5, True, MUT, "direita")
        y[0] += 21

    def cabe(altura, titulo=None, colunas=None):
        if y[0] + altura > FIM:
            doc.nova_pagina()
            topo(False, titulo)
            if colunas:
                cabeca_tabela(colunas)

    def titulo_secao(t, valor=None):
        doc.texto(M, y[0], t, 12.5, True, TXT)
        if valor is not None:
            doc.texto(DIR, y[0], calc.fmt_brl(valor), 12.5, True, TXT, "direita")
        y[0] += 6
        doc.linha(M, y[0], DIR, y[0], COR, 1.6)
        y[0] += 18

    def valores(lin, negrito=False):
        for x, v in zip(NUM, (calc.fmt_brl(lin["valor"]), _brl_sinal(lin["mes"]), calc.fmt_brl(lin["ano1"]), calc.fmt_brl(lin["ano5"]))):
            doc.texto(x, y[0], v, 9, negrito, TXT if negrito or v != "—" else MUT, "direita")

    topo(True)
    larg = (W - 10 * (len(r["resumo"]) - 1)) / len(r["resumo"])
    for k, (n, v) in enumerate(r["resumo"]):
        x = M + k * (larg + 10)
        if k == 0:  # o primeiro (o patrimônio) em destaque, na cor do app
            doc.retangulo(x, y[0], larg, 50, borda=tom(0.45), fundo=tom(0.12), raio=8)
        else:
            doc.retangulo(x, y[0], larg, 50, borda=LIN, raio=8)
        doc.texto(x + 12, y[0] + 18, n, 8.5, False, MUT)
        doc.texto(x + 12, y[0] + 38, pdf.cortar(calc.fmt_brl(v), larg - 24, 15, True), 15, True, TXT)
    y[0] += 76
    if r["aviso"]:
        doc.texto(M, y[0] - 8, r["aviso"], 9, False, MUT)
        y[0] += 14

    for s in r["secoes"]:
        cabe(80)
        titulo_secao(s["titulo"])
        cabeca_tabela(s["colunas"])
        for k, l in enumerate(s["linhas"]):
            cabe(26 + (24 if k == len(s["linhas"]) - 1 else 0), s["titulo"], s["colunas"])  # o último vai junto com o total
            doc.texto(COLS[0][0], y[0], pdf.cortar(l["nome"], COLS[0][1], 9.5), 9.5, False, TXT)
            if l["tipo"]:
                doc.texto(COLS[0][0], y[0] + 10, pdf.cortar(l["tipo"], COLS[0][1], 7), 7, False, MUT)
            for (x, w), t, tam in zip(COLS[1:], (l["banco"], l["rendimento"], l["vencimento"]), (9, 9, 8.5)):
                doc.texto(x, y[0], pdf.cortar(t, w, tam), tam, False, TXT)
            valores(l)
            y[0] += 15
            doc.linha(M, y[0], DIR, y[0], LIN2, 0.5)
            y[0] += 11
        # o total da seção, em todas as colunas de valor
        cabe(24, s["titulo"], s["colunas"])
        doc.retangulo(M, y[0] - 12, W, 19, fundo=tom(0.10), raio=3)
        doc.texto(COLS[0][0], y[0], "Total", 9, True, TXT)
        valores({"valor": s["total"], "mes": s["mes"], "ano1": s["ano1"], "ano5": s["ano5"]}, True)
        y[0] += 28

    if r["bancos"]:
        cabe(80)
        titulo_secao("Por banco", r["total"])
        BX, BW = M + 180, W - 180 - 170  # a barra da parte de cada banco
        for n, v, p in r["bancos"]:
            cabe(24, "Por banco")
            doc.texto(M, y[0], pdf.cortar(n, 170, 9.5), 9.5, False, TXT)
            doc.retangulo(BX, y[0] - 6.5, BW, 7, fundo=LIN2, raio=3.5)
            if p > 0:
                doc.retangulo(BX, y[0] - 6.5, max(7, BW * min(p, 100) / 100), 7, fundo=COR, raio=3.5)
            doc.texto(DIR - 58, y[0], calc.fmt_brl(v), 9.5, False, TXT, "direita")
            doc.texto(DIR, y[0], f"{calc.fmt_pct(p)}%", 9.5, False, MUT, "direita")
            y[0] += 9
            doc.linha(M, y[0], DIR, y[0], LIN2, 0.5)
            y[0] += 15
    if not r["secoes"]:
        doc.texto(M, y[0], r["vazio"], 10.5, False, MUT)
        y[0] += 20

    linhas = [t for n in notas_relatorio(r) for t in pdf.quebrar(n, W, 8)]
    cabe(12 + 11 * (len(linhas) - 1))
    y[0] += 10
    for t in linhas:
        doc.texto(M, y[0], t, 8, False, MUT)
        y[0] += 11
    # no pé de cada página: a marca da CorrerIA Code como no Mais › Sobre (a mesma do ResolvIA e do InventarIA), com uma
    # linha em cima e, com mais de uma página, o número dela
    n = len(doc.paginas)
    oque = "DESENVOLVIMENTO DE SOFTWARES"
    bloco = 16 + 8 + max(pdf.largura("CorrerIA Code", 10.5, True), pdf.largura(oque, 6, True) + 0.9 * (len(oque) - 1))
    ang = math.radians(-8)
    for k in range(n):
        doc.ir_para(k)
        fy = doc.altura_pagina - 30
        doc.linha(M, fy - 16, DIR, fy - 16, LIN, 0.8)
        bx = doc.largura_pagina / 2 - bloco / 2
        cx, cy = bx + 8, fy + 1

        def gira(px, py):
            return (cx + px * math.cos(ang) - py * math.sin(ang), cy + px * math.sin(ang) + py * math.cos(ang))
        quadrado = [gira(ox + 4 * math.cos(math.radians(ini + j * 15)), oy + 4 * math.sin(math.radians(ini + j * 15)))
                    for ox, oy, ini in ((4, 4, 0), (-4, 4, 90), (-4, -4, 180), (4, -4, 270)) for j in range(7)]
        doc.poligono(quadrado, COR)
        doc.poligono([gira((x - 12) * 0.46, (y - 12) * 0.46) for x, y in RAIO], (0.04, 0.06, 0.08))
        tx = bx + 24
        doc.texto(tx, fy, "Correr", 10.5, True, TXT)
        doc.texto(tx + pdf.largura("Correr", 10.5, True), fy, "IA", 10.5, True, COR)
        doc.texto(tx + pdf.largura("CorrerIA", 10.5, True), fy, " Code", 10.5, True, TXT)
        doc.texto(tx, fy + 9, oque, 6, True, MUT, espaco=0.9)
        if n > 1:
            doc.texto(DIR, fy + 4, f"página {k + 1} de {n}", 8, False, MUT, "direita")
    return doc.bytes()


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


# -- uso da IA: o Home Assistant não devolve tokens nem custo, então o app conta as chamadas (como no InventarIA)
USO_ARQ = os.path.join(DATA_DIR, "uso_ia.json")
USO_TRAVA = threading.Lock()
USO_DIAS = 120
USO_SENSOR = "sensor.gerencia_ia_hoje"
_uso_sensor = {"dia": None, "visto": 0.0}


def ia_ligada(d=None):
    return (d or ler())["ajustes"].get("ia", True) is not False


def uso_dia(ts=None):
    t = time.time() if ts is None else ts
    if os.environ.get("TZ"):
        return time.strftime("%Y-%m-%d", time.localtime(t))
    return time.strftime("%Y-%m-%d", time.gmtime(t - 3 * 3600))  # sem fuso no ambiente: horário de Brasília


def e_cota(msg):
    t = str(msg or "").lower()
    return "429" in t or "quota" in t or "resource_exhausted" in t or "rate limit" in t


def registrar_uso(tipo, entidade, chars_in, chars_out, imagens, segundos, resultado):
    tokens = round((chars_in + chars_out) / 4)  # estimativa: uns 4 caracteres por token, só o texto
    dia = uso_dia()
    with USO_TRAVA:
        try:
            with open(USO_ARQ, encoding="utf-8") as f:
                u = json.load(f)
        except (OSError, ValueError):
            u = {}
        dias = u.setdefault("days", {})
        dd = dias.setdefault(dia, {})
        for k, v in (("calls", 1), ("tokens", tokens), ("images", imagens), ("seconds", round(segundos, 1)),
                     ("errors", 0 if resultado in ("ok", "cota") else 1), ("quota", 1 if resultado == "cota" else 0)):
            dd[k] = round(dd.get(k, 0) + v, 1)
        nome = entidade or "padrão do Home Assistant"
        for grupo, chave in (("kinds", tipo), ("entities", nome)):
            g = dd.setdefault(grupo, {})
            g[chave] = g.get(chave, 0) + 1
        for velho in sorted(dias)[:-USO_DIAS]:
            del dias[velho]
        rec = u.setdefault("recent", [])
        rec.insert(0, {"at": agora_iso(), "kind": tipo, "entity": nome, "result": resultado,
                       "seconds": round(segundos, 1), "tokens": tokens, "images": imagens})
        del rec[40:]
        os.makedirs(DATA_DIR, exist_ok=True)
        gravar_arquivo(USO_ARQ, json.dumps(u, ensure_ascii=False))
    threading.Thread(target=publicar_uso_sensor, daemon=True).start()


def resumo_uso():
    with USO_TRAVA:
        try:
            with open(USO_ARQ, encoding="utf-8") as f:
                u = json.load(f)
        except (OSError, ValueError):
            u = {}
    dias = u.get("days") or {}
    hoje = uso_dia()
    semana = [uso_dia(time.time() - i * 86400) for i in range(6, -1, -1)]

    def total(chaves):
        t = {"calls": 0, "errors": 0, "quota": 0, "tokens": 0, "images": 0, "seconds": 0, "kinds": {}, "entities": {}}
        for k in chaves:
            dd = dias.get(k) or {}
            for c in ("calls", "errors", "quota", "tokens", "images", "seconds"):
                t[c] = round(t[c] + (dd.get(c) or 0), 1)
            for grupo in ("kinds", "entities"):
                for nome, n in (dd.get(grupo) or {}).items():
                    t[grupo][nome] = t[grupo].get(nome, 0) + n
        return t

    return {"today": total([hoje]), "week": total(semana), "month": total([k for k in dias if k[:7] == hoje[:7]]),
            "days": [{"day": k, **{c: (dias.get(k) or {}).get(c, 0) for c in ("calls", "errors", "quota")}} for k in semana],
            "recent": (u.get("recent") or [])[:12], "since": min(dias) if dias else None, "sensor": USO_SENSOR}


def publicar_uso_sensor():
    """Sensor no Home Assistant com as chamadas de IA de hoje, para painel e automação."""
    if not TOKEN or IA_MOCK:
        return
    try:
        d = ler()
        if not sensores_ligados(d) or not ia_ligada(d):
            return
        r = resumo_uso()
        h = r["today"]
        ha_request("POST", "/states/" + USO_SENSOR, {"state": int(h["calls"]), "attributes": {
            "friendly_name": "GerencIA: chamadas de IA hoje", "icon": "mdi:robot-outline",
            "unit_of_measurement": "chamadas", "state_class": "total_increasing",
            "erros": int(h["errors"]), "cota_excedida": int(h["quota"]), "tokens_texto_estimados": int(h["tokens"]),
            "imagens": int(h["images"]), "por_tipo": h["kinds"], "ultimos_7_dias": int(r["week"]["calls"]),
            "este_mes": int(r["month"]["calls"]), "ultima_chamada": r["recent"][0]["at"] if r["recent"] else None}}, timeout=10)
        _uso_sensor["dia"] = uso_dia()
    except Exception as e:  # noqa: BLE001
        if _uso_sensor["dia"] != uso_dia():
            log("Sensor de uso da IA:", e)
        _uso_sensor["dia"] = uso_dia()


def ia_chamar(tipo, payload, imagens=0, timeout=180):
    """Chama a ação ai_task.generate_data e registra a chamada no uso da IA."""
    t0, resultado, saida = time.time(), "ok", 0
    try:
        res = ha_request("POST", "/services/ai_task/generate_data?return_response", payload, timeout=timeout)
        dados = ((res or {}).get("service_response") or {}).get("data")
        try:
            saida = len(dados if isinstance(dados, str) else json.dumps(dados, ensure_ascii=False))
        except (TypeError, ValueError):
            saida = 0
        return res
    except Exception as e:
        resultado = "cota" if e_cota(e) else "erro"
        raise
    finally:
        try:
            registrar_uso(tipo, payload.get("entity_id", ""), len(payload.get("instructions") or ""), saida, imagens, time.time() - t0, resultado)
        except Exception as e:  # noqa: BLE001
            log("Uso da IA:", e)


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
    if not ia_ligada(d):
        return {"pronta": False, "ligada": False, "motivo": "A IA está desligada.", "entidades": [], "selecionada": sel}
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
- "tipo": uma destas chaves: cdb, lci (LCI, LCA, CRI, CRA), tesouro, poupanca, caixinha (conta remunerada, cofrinho, caixinha), fundo, acoes (ações, FII, ETF, BDR), ouro (ouro físico, barra, ouro ativo financeiro, ETF de ouro), dinheiro (dinheiro guardado em espécie, em casa, no cofre), bens (carro, moto, móveis e outros bens de uma pessoa, pelo valor total; indexador "deprecia"), previdencia, outro.
- "valor": saldo atual bruto em reais, número sem símbolo. Se só aparecer o valor aplicado, use ele.
- "aplicado": valor aplicado originalmente, número; 0 se não aparecer.
- "data_valor": data do saldo em AAAA-MM-DD, se aparecer; senão "".
- "indexador": cdi_pct (ex.: 110% do CDI), cdi_mais (CDI + 1,5% a.a.), pre (prefixado 13% a.a.), ipca_mais (IPCA + 6% a.a.), selic_mais (Tesouro Selic, Selic + 0,1%), poupanca, estimado (renda variável e ouro), parado (sem rendimento).
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
- "situacao": "feito" se já foi pago ou recebido; "pendente" se é conta, boleto ou parcela a pagar, ou valor que ainda vai receber; "" se não der para saber.
- "confianca": "alta", "media" ou "baixa".
Em fatura, ignore "pagamento recebido", "pagamento da fatura", "saldo anterior", créditos de estorno do próprio cartão e totais. Juros, IOF, anuidade e multa entram como despesa na categoria de impostos e taxas.
Em conversas (WhatsApp, anotações), cada valor citado como gasto ou ganho vira um item. Não invente números.
Responda somente com JSON válido, sem markdown e sem texto antes ou depois, neste formato:
{{"itens":[{{"tipo":"despesa","descricao":"","valor":0,"data":"","categoria":"","parcela_atual":0,"parcelas_total":0,"cartao":false,"banco":"","situacao":"","confianca":"media"}}]}}"""


# Ler com IA sem escolher antes: a IA separa o que é lançamento (gasto, recebimento, a pagar, a receber) e o que é investimento
IA_REGRAS_AUTO = """Separe tudo em dois grupos. Um mesmo conteúdo pode ter os dois, só um ou nenhum.

"lancamentos": dinheiro que entrou ou saiu do caixa da pessoa, ou que vai entrar ou sair: gastos, compras, contas, boletos, faturas, parcelas, salário, pix recebido ou enviado, vendas e reembolsos. Para cada um:
- "tipo": "despesa" (gasto, compra, conta, débito) ou "receita" (salário, pix recebido, venda, reembolso).
- "descricao": curta e limpa, como a pessoa escreveria (ex.: "iFood", "Posto Shell", "Aluguel", "Salário").
- "valor": valor em reais, número positivo sem símbolo. Em parcelas, o valor da parcela.
- "data": AAAA-MM-DD. Em fatura de cartão, a data da compra; em conta ou boleto a pagar, o vencimento. Se só houver dia e mês, use o ano mais provável. Se não houver data, use a de hoje. "ontem", "hoje" e "amanhã" valem pela data de hoje.
- "categoria": uma destas chaves: {cats}.
- "parcela_atual" e "parcelas_total": números, quando aparecer "parcela 3/10", "PARC 03/10" ou "3 de 10"; senão 0 e 0.
- "cartao": true se for compra no cartão de crédito (fatura); senão false.
- "banco": banco ou cartão citado; "" se não aparecer.
- "situacao": "feito" se já foi pago ou recebido; "pendente" se é conta, boleto ou parcela a pagar, ou valor que ainda vai receber; "" se não der para saber.
- "confianca": "alta", "media" ou "baixa".
Em fatura, ignore "pagamento recebido", "pagamento da fatura", "saldo anterior", créditos de estorno do próprio cartão e totais. Juros, IOF, anuidade e multa entram como despesa na categoria de impostos e taxas. Em conversas, cada valor citado como gasto, conta ou ganho vira um item.
Uma aplicação nova ("apliquei 3 mil no CDB", "investi", "guardei 500 na caixinha") entra nos dois grupos: aqui, como despesa na categoria de investimentos, já feita; e em "investimentos", com o "aporte".

"investimentos": aplicações e saldos em investimentos (CDB, LCI, LCA, Tesouro, poupança, caixinha, fundo, ações, FII, previdência), como num print de app de banco ou corretora, extrato, nota de aplicação ou mensagem do gerente. Para cada um:
- "nome": nome curto e claro (ex.: "CDB Inter 2028", "Tesouro IPCA+ 2035", "LCI Itaú").
- "banco": instituição ou corretora (ex.: "Inter", "XP"); "" se não aparecer.
- "tipo": uma destas chaves: cdb, lci (LCI, LCA, CRI, CRA), tesouro, poupanca, caixinha (conta remunerada, cofrinho, caixinha), fundo, acoes (ações, FII, ETF, BDR), ouro (ouro físico, barra, ouro ativo financeiro, ETF de ouro), dinheiro (dinheiro guardado em espécie, em casa, no cofre), bens (carro, moto, móveis e outros bens de uma pessoa, pelo valor total; indexador "deprecia"), previdencia, outro.
- "valor": saldo atual bruto em reais, número sem símbolo. Se só aparecer o valor aplicado, use ele.
- "aplicado": valor aplicado originalmente, número; 0 se não aparecer.
- "data_valor": data do saldo em AAAA-MM-DD, se aparecer; senão "".
- "indexador": cdi_pct (ex.: 110% do CDI), cdi_mais (CDI + 1,5% a.a.), pre (prefixado 13% a.a.), ipca_mais (IPCA + 6% a.a.), selic_mais (Tesouro Selic, Selic + 0,1%), poupanca, estimado (renda variável e ouro), parado (sem rendimento).
- "taxa": 110 para 110% do CDI; 1.5 para CDI + 1,5%; 13 para 13% a.a.; 6.5 para IPCA + 6,5%; 0.1 para Selic + 0,1%; 0 para poupança e sem rendimento; 10 para renda variável.
- "vencimento": AAAA-MM-DD, se aparecer; senão "".
- "liquidez": "diaria" se der para resgatar a qualquer momento; senão "vencimento".
- "existente": se for o mesmo investimento de um já cadastrado (lista abaixo), o id dele; senão "".
- "dono": "" se for da própria pessoa; se o conteúdo disser de quem é (ex.: "dinheiro da mãe", "do Pedro"), o nome, de preferência como aparece no dono da lista abaixo.
- "aporte": valor aplicado agora, quando o conteúdo fala de uma aplicação nova; 0 se não. Se só falar da aplicação, sem o saldo, deixe "valor" em 0: o app soma o aporte ao que já tinha.
- "confianca": "alta", "media" ou "baixa".
Ignore saldo parado em conta corrente, cartões, limites e empréstimos.

Não invente números: se não der para ler, use 0 ou "".
Responda somente com JSON válido, sem markdown e sem texto antes ou depois, neste formato:
{{"lancamentos":[{{"tipo":"despesa","descricao":"","valor":0,"data":"","categoria":"","parcela_atual":0,"parcelas_total":0,"cartao":false,"banco":"","situacao":"","confianca":"media"}}],"investimentos":[{{"nome":"","banco":"","tipo":"cdb","valor":0,"aplicado":0,"data_valor":"","indexador":"cdi_pct","taxa":100,"vencimento":"","liquidez":"vencimento","existente":"","aporte":0,"confianca":"media"}}]}}"""


IA_REGRAS_HOLERITE = """Devolva:
- "data": data do pagamento em AAAA-MM-DD, se aparecer; senão "".
- "creditos": cada linha de crédito (proventos, vencimentos, produção, ajuda de custo, transporte), com "descricao" como está no recibo e "valor" (número).
- "debitos": cada linha de débito (descontos), com "descricao" como está, "valor" (número) e "tipo": "imposto" (INSS, IRRF, imposto de renda, taxa administrativa, contribuição sindical, ISS), "saude" (plano de saúde, assistência médica, odontológico, coparticipação) ou "outro" (vale-transporte, refeição, empréstimo consignado, adiantamento e o resto).
- "total_creditos", "total_debitos" e "liquido": números como aparecem no recibo; 0 se não aparecerem.
Ignore bases de cálculo, FGTS e linhas só informativas, que não entram no líquido. Não invente números.
Responda somente com JSON válido, sem markdown e sem texto antes ou depois, neste formato:
{"data":"","creditos":[{"descricao":"","valor":0}],"debitos":[{"descricao":"","valor":0,"tipo":"imposto"}],"total_creditos":0,"total_debitos":0,"liquido":0}"""


def _dono(inv):
    return (inv.get("terceiro") or "terceiros") if inv.get("titular") == "terceiros" else "meu"


# Atualizar saldos: uma listinha com o saldo de agora de cada investimento (às vezes de um terceiro, num print ou no WhatsApp)
# aberto do Novo investimento: só investimentos, e um valor com um banco ou nome é o saldo de agora
IA_REGRAS_SO_INVEST = """Este conteúdo veio da tela de investimentos: devolva só "investimentos" e deixe "lancamentos" vazio. Um valor citado com um banco, uma corretora ou o nome de um investimento (ex.: "30.350 nubank", "Nubank, valor atualizado, R$ 500") é o saldo de agora desse investimento: "valor" com o saldo e "existente" com o id do correspondente na lista abaixo, pelo banco, pelo nome e pelo dono. "Dinheiro" guardado (em espécie, em casa) também conta: tipo "dinheiro", indexador "parado", banco "". Uma aplicação nova ("apliquei 2 mil no CDB") vai em "aporte"."""


IA_REGRAS_SALDOS = """Este conteúdo é uma lista de saldos atualizados{de_quem}: cada linha (ou cada bloco) traz um investimento, pelo banco ou pelo nome, e quanto ele tem agora (ex.: "Nubank, valor atualizado, R$ 500"). Devolva só "investimentos" e deixe "lancamentos" vazio. Um item por investimento citado, com:
- "valor": o saldo de agora; "aporte": 0.
- "existente": o id do investimento já cadastrado que corresponde a essa linha, pelo banco, pelo nome e pelo dono{pref}; "" se nenhum corresponder.
- "nome" e "banco" como aparecem na linha; os outros campos, do jeito de sempre (se não aparecer, use os do investimento correspondente).
"Dinheiro" guardado (em espécie, em casa) também conta: tipo "dinheiro", indexador "parado", banco ""."""


def ia_prompt(d, modo, com_anexo, texto, saldos=False, pessoa=None, so_invest=False):
    hoje_txt = f"{date.today():%d/%m/%Y}"
    if modo == "holerite":
        partes = [f"Você lê recibos de pagamento de uma pessoa no Brasil (holerite, contracheque, recibo de produção de cooperativa ou pró-labore). Hoje é {hoje_txt}.",
                  "Leia o anexo." if com_anexo else "Leia o texto abaixo.", IA_REGRAS_HOLERITE]
        if texto:
            partes.append("Texto:\n<<<\n" + texto + "\n>>>")
        return "\n".join(partes)
    if modo == "auto":
        cats = ", ".join(f"{c.get('id')} ({c.get('nome')}, {c.get('tipo')})" for c in d["categorias"])
        bancos = {b.get("id"): b.get("nome", "") for b in d["bancos"]}
        partes = [f"Você ajuda uma pessoa no Brasil a organizar o dinheiro: o caixa do dia a dia e os investimentos. Hoje é {hoje_txt}.",
                  "Leia o anexo (fatura de cartão em PDF, foto de nota, cupom ou boleto, print de app de banco ou corretora, print de conversa do WhatsApp, extrato ou comprovante)."
                  if com_anexo else
                  "Leia o texto abaixo (mensagens do WhatsApp, anotações, fala transcrita, extrato, fatura ou e-mail colado).",
                  "Liste até 120 lançamentos e até 20 investimentos.", IA_REGRAS_AUTO.format(cats=cats)]
        if saldos:
            de_quem = "" if not pessoa else " dos investimentos da própria pessoa (dono \"meu\")" if pessoa == "meu" else f" dos investimentos de {pessoa} (dono \"{pessoa}\")"
            pref = "" if not pessoa else f"; prefira os do dono \"{'meu' if pessoa == 'meu' else pessoa}\""
            partes.append(IA_REGRAS_SALDOS.format(de_quem=de_quem, pref=pref))
        elif so_invest:
            partes.append(IA_REGRAS_SO_INVEST)
        if d["investimentos"]:
            partes.append("Investimentos já cadastrados (id | nome | banco | dono | valor):")
            for inv in d["investimentos"][:80]:
                partes.append(f"{inv.get('id')} | {inv.get('nome', '')} | {bancos.get(inv.get('banco'), '')} | {_dono(inv)} | {calc.num(inv.get('valor')):.2f}")
    elif modo == "caixa":
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
            "valor": round(max(0.0, calc.num_br(it.get("valor"))), 2),
            "aplicado": round(max(0.0, calc.num_br(it.get("aplicado"))), 2),
            "data_valor": _data_ou_vazio(it.get("data_valor")),
            "indexador": idx if idx in calc.INDEXADORES else "cdi_pct",
            "taxa": round(calc.num_br(it.get("taxa")), 4),
            "vencimento": _data_ou_vazio(it.get("vencimento")),
            # "diária" com acento (como a IA costuma escrever) também é diária
            "liquidez": "diaria" if str(it.get("liquidez")).lower().replace("á", "a").startswith("diar") else "vencimento",
            "existente": it.get("existente") if it.get("existente") in ids else "",
            "aporte": round(max(0.0, calc.num_br(it.get("aporte"))), 2),
            "dono": "" if str(it.get("dono") or "").strip().lower() in ("", "meu", "minha", "eu", "próprio", "proprio") else str(it.get("dono")).strip()[:40],
            "confianca": it.get("confianca") if it.get("confianca") in ("alta", "media", "baixa") else "media",
        })
    return saida


def _aporte_sem_saldo(lista):
    # investimento novo que só veio com o aporte: o aporte é o valor
    for it in lista:
        if not it["existente"] and not it["valor"] and it.get("aporte"):
            it["valor"] = it["aporte"]
    return lista


def ia_limpar_caixa(parsed, d):
    cats = {c.get("id"): c.get("tipo") for c in d["categorias"]}
    saida = []
    for it in _lista(parsed)[:120]:
        if not isinstance(it, dict):
            continue
        valor = round(abs(calc.num_br(it.get("valor"))), 2)
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
            "situacao": it.get("situacao") if it.get("situacao") in ("feito", "pendente") else "",
            "confianca": it.get("confianca") if it.get("confianca") in ("alta", "media", "baixa") else "media",
        })
    return saida


def ia_limpar_auto(parsed, d):
    """{"lancamentos": [...], "investimentos": [...]}; aceita também só uma lista (vira lançamentos ou investimentos pelo jeito)."""
    p = parsed if isinstance(parsed, dict) else {"itens": parsed if isinstance(parsed, list) else []}
    lanc = p.get("lancamentos")
    inv = p.get("investimentos")
    if lanc is None and inv is None:
        lista = _lista(p)
        eh_inv = [x for x in lista if isinstance(x, dict) and ("indexador" in x or "nome" in x and "descricao" not in x)]
        inv, lanc = eh_inv, [x for x in lista if x not in eh_inv]
    return {"lancamentos": ia_limpar_caixa({"itens": lanc or []}, d), "investimentos": _aporte_sem_saldo(ia_limpar({"itens": inv or []}, d))}


def _so_saldos(r, saldos):
    # no Atualizar saldos só interessam os investimentos; um saldo nunca é aporte somado
    if saldos:
        r["lancamentos"] = []
        for it in r["investimentos"]:
            if it.get("aporte") and not it.get("valor"):
                it["valor"] = it["aporte"]
            it["aporte"] = 0
    return r


def ia_limpar_holerite(parsed, d=None):
    p = parsed if isinstance(parsed, dict) else {}
    def linhas(k, com_tipo):
        out = []
        for it in (p.get(k) or [])[:40]:
            if not isinstance(it, dict):
                continue
            v = round(abs(calc.num_br(it.get("valor"))), 2)
            if v <= 0:
                continue
            o = {"descricao": str(it.get("descricao") or "").strip()[:60] or ("Crédito" if k == "creditos" else "Desconto"), "valor": v}
            if com_tipo:
                t = str(it.get("tipo") or "outro").lower()
                o["tipo"] = t if t in ("imposto", "saude", "outro") else "outro"
            out.append(o)
        return out
    return {"data": _data_ou_vazio(p.get("data")), "creditos": linhas("creditos", False), "debitos": linhas("debitos", True),
            "total_creditos": round(abs(calc.num_br(p.get("total_creditos"))), 2), "total_debitos": round(abs(calc.num_br(p.get("total_debitos"))), 2),
            "liquido": round(abs(calc.num_br(p.get("liquido"))), 2)}


# recibo inventado para testes (nenhum dado real)
IA_SIMULADA_HOLERITE = {"data": "", "creditos": [
    {"descricao": "Produção", "valor": 4200.00}, {"descricao": "Ajuda de custo", "valor": 7600.00}, {"descricao": "Transporte", "valor": 1250.00}],
    "debitos": [{"descricao": "INSS", "valor": 840.00, "tipo": "imposto"}, {"descricao": "Taxa administrativa", "valor": 587.25, "tipo": "imposto"},
                {"descricao": "Plano de saúde titular", "valor": 320.00, "tipo": "saude"}, {"descricao": "Coparticipação", "valor": 85.40, "tipo": "saude"}],
    "total_creditos": 13050.00, "total_debitos": 1832.65, "liquido": 11217.35}

IA_SIMULADA = {"itens": [
    {"nome": "CDB Banco Sol 2028", "banco": "Banco Sol", "tipo": "cdb", "valor": 15412.37, "aplicado": 15000,
     "data_valor": "", "indexador": "cdi_pct", "taxa": 112, "vencimento": "2028-03-13", "liquidez": "vencimento", "confianca": "alta"},
    {"nome": "Tesouro Selic 2029", "banco": "Corretora Norte", "tipo": "tesouro", "valor": 8350.10, "aplicado": 8000,
     "data_valor": "", "indexador": "selic_mais", "taxa": 0.05, "vencimento": "2029-03-01", "liquidez": "diaria", "confianca": "media"},
]}
def ia_simulada_saldos(texto, d, pessoa=None):
    """Simulação do Atualizar saldos (testes e prévia): cada linha com um valor acha o investimento pelo banco ou pelo nome."""
    bancos = {b.get("id"): b.get("nome", "") for b in d.get("bancos", [])}
    linhas = [x.strip() for x in re.split(r"[\n;]+", texto or "") if x.strip()]
    dono = pessoa
    for linha in linhas:  # "Tudo dinheiro da mãe": o dono de todos
        m = re.search(r"\b(?:da|do|de)\s+([a-zà-ú]+)\s*$", linha, re.I)
        if m and not re.search(r"\d", linha):
            dono = dono or m.group(1).capitalize()
    pessoas = {_dono(i).lower(): _dono(i) for i in d.get("investimentos", [])}
    dono = pessoas.get((dono or "").lower(), dono)
    invs = [i for i in d.get("investimentos", []) if not dono or _dono(i) == dono] or ([] if dono else d.get("investimentos", []))
    out = []
    for linha in linhas:
        m = re.search(r"(?:r\$\s*)?(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)\s*(mil\b)?", linha, re.I)
        if not m:
            continue
        valor = calc.num_br(m.group(1)) * (1000 if m.group(2) else 1)
        nome = re.sub(r"valor atualizado|saldo|atualizado|r\$", "", linha[:m.start()] + " " + linha[m.end():], flags=re.I)
        nome = re.sub(r"\s+", " ", re.sub(r"[,:;–-]", " ", nome)).strip()
        if not nome:
            continue
        n = nome.lower()
        ex = next((i for i in invs if n in (bancos.get(i.get("banco"), "") or "").lower() or n in (i.get("nome") or "").lower()), None)
        parado = n in ("dinheiro", "em casa", "em espécie", "cofre")
        out.append({"nome": ex.get("nome") if ex else nome[:1].upper() + nome[1:], "banco": "" if parado else nome, "tipo": ex.get("tipo") if ex else ("dinheiro" if parado else "outro"),
                    "valor": valor, "aporte": 0, "existente": ex.get("id") if ex else "", "dono": "" if dono in (None, "meu") else dono,
                    "indexador": ex.get("indexador") if ex else ("parado" if parado else "cdi_pct"), "taxa": ex.get("taxa") if ex else (0 if parado else 100),
                    "liquidez": ex.get("liquidez") if ex else "diaria", "confianca": "alta" if ex else "media"})
    return {"lancamentos": [], "investimentos": out}


def ia_simulada_auto(texto, dica, d=None):
    t = (texto or "").lower()
    m = re.search(r"apliquei (\d+(?:[.,]\d+)?)( mil)?", t)
    cdb = next((i for i in (d or {}).get("investimentos", []) if i.get("tipo") == "cdb"), None)
    if m and cdb:  # "apliquei 3000 no cdb": aporte num investimento que já existe
        v = calc.num_br(m.group(1)) * (1000 if m.group(2) else 1)
        return {"lancamentos": [{"tipo": "despesa", "descricao": "Aporte no CDB", "valor": v, "data": "", "categoria": "c-investimentos", "situacao": "feito"}],
                "investimentos": [{"nome": cdb.get("nome"), "banco": "", "tipo": "cdb", "valor": 0, "aporte": v, "existente": cdb.get("id"),
                                   "indexador": cdb.get("indexador"), "taxa": cdb.get("taxa"), "liquidez": cdb.get("liquidez"), "confianca": "alta"}]}
    inv = re.search(r"cdb|tesouro|\blc[ia]\b|invest|apliquei|aplica[çc]|% do cdi|caixinha|rende", t)
    cx = re.search(r"gast|receb|pagu|pagar|compr|fatura|pix|mercado|boleto|conta de|sal[áa]rio", t)
    if not inv and not cx:
        inv, cx = dica == "invest", dica != "invest"
    return {"lancamentos": IA_SIMULADA_CAIXA["itens"] if cx else [], "investimentos": IA_SIMULADA["itens"] if inv else []}


IA_SIMULADA_CAIXA = {"itens": [
    {"tipo": "despesa", "descricao": "iFood", "valor": 64.90, "data": "", "categoria": "c-restaurantes", "cartao": True, "banco": "Banco Lua"},
    {"tipo": "despesa", "descricao": "Posto Shell", "valor": 210.00, "data": "", "categoria": "c-transporte", "cartao": True, "banco": "Banco Lua"},
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


# ---------------------------------------------------------------- senhas dos PDFs (faturas com senha)

SENHAS_ARQ = os.path.join(DATA_DIR, "senhas_pdf.json")  # fora do gerencia.json: não vai nas exportações nem para a tela
_trava_senhas = threading.Lock()


class ErroSenhaPdf(ValueError):
    """O PDF tem senha e nenhuma abriu: a tela pede a senha (codigo senha_pdf)."""
    codigo = "senha_pdf"


def senhas_pdf():
    try:
        with open(SENHAS_ARQ, encoding="utf-8") as f:
            lista = json.load(f).get("senhas") or []
    except (OSError, ValueError, AttributeError):
        return []
    return [x for x in lista if isinstance(x, dict) and isinstance(x.get("senha"), str) and x.get("id")]


def _mascara(senha):
    return "••••" + (senha[-2:] if len(senha) >= 4 else "")


def senhas_listar():
    """Para a tela: o nome e só o fim da senha (••••45)."""
    return [{"id": x["id"], "nome": x.get("nome") or "Senha", "fim": _mascara(x["senha"])} for x in senhas_pdf()]


def senha_nova(nome, senha):
    nome, senha = str(nome or "").strip()[:40], str(senha or "").strip()[:64]
    if not senha:
        raise ValueError("Digite a senha.")
    with _trava_senhas:
        lista = senhas_pdf()
        igual = next((x for x in lista if x["senha"] == senha), None)
        if igual:  # a mesma senha: só troca o nome
            igual["nome"] = nome or igual.get("nome") or "Senha"
        else:
            if len(lista) >= 20:
                raise ValueError("Já são 20 senhas. Apague uma antes.")
            lista.append({"id": secrets.token_hex(4), "nome": nome or f"Senha {len(lista) + 1}", "senha": senha})
        gravar_arquivo(SENHAS_ARQ, json.dumps({"senhas": lista}, ensure_ascii=False, indent=1))
    return senhas_listar()


def senha_apagar(sid):
    with _trava_senhas:
        lista = [x for x in senhas_pdf() if x["id"] != sid]
        gravar_arquivo(SENHAS_ARQ, json.dumps({"senhas": lista}, ensure_ascii=False, indent=1))
    return senhas_listar()


def abrir_pdf(bruto, digitada="", guardar=False, nome_arquivo=""):
    """O PDF sem senha para a IA: tenta a senha digitada agora e as cadastradas. Com guardar, a digitada que abriu
    entra nas senhas cadastradas (para as próximas faturas)."""
    if not pdfsenha.tem_senha(bruto):
        return bruto
    digitada = str(digitada or "").strip()[:64]
    cadastradas = [x["senha"] for x in senhas_pdf()]
    try:
        aberto = pdfsenha.abrir(bruto, ([digitada] if digitada else []) + cadastradas)
    except pdfsenha.SenhaErrada:
        if cadastradas or digitada:
            log("PDF com senha: nenhuma senha serviu ·", pdfsenha.protecao(bruto))
        raise ErroSenhaPdf("Senha errada para este PDF." if digitada else "Nenhuma das senhas cadastradas abre este PDF."
                           if cadastradas else "Este PDF tem senha.") from None
    except pdfsenha.PdfInvalido as e:
        log("PDF com senha: não consegui abrir ·", pdfsenha.protecao(bruto), "·", e)
        raise ValueError("Não consegui abrir este PDF com senha. Tente um print da fatura.") from None
    if digitada and guardar and digitada not in cadastradas:
        try:  # só guarda se foi ela que abriu (as cadastradas sozinhas podiam abrir)
            pdfsenha.abrir(bruto, [digitada])
            senha_nova(f"Da fatura {os.path.splitext(str(nome_arquivo))[0]}"[:40] if nome_arquivo else "", digitada)
        except (pdfsenha.SenhaErrada, pdfsenha.PdfInvalido, ValueError):
            pass
    return aberto


EXT_ANEXO = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def mime_anexo(b):
    """O tipo do arquivo pelos primeiros bytes: PDF, JPG, PNG ou WebP (o resto, None)."""
    if b[:4] == b"%PDF":
        return "application/pdf"
    if b[:2] == b"\xff\xd8":
        return "image/jpeg"
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "image/webp"
    return None


def ia_ler(corpo):
    d = ler()
    if not ia_ligada(d):
        raise ValueError("A IA está desligada. Para usar, ligue em Mais › Configurações › Integrações.")
    modo = corpo.get("modo") if corpo.get("modo") in ("caixa", "holerite", "invest") else "auto"
    foto = str(corpo.get("foto") or "")
    texto = str(corpo.get("texto") or "").strip()[:12000]
    # Digitalizar com IA manda as páginas fotografadas juntas (anexos); o resto, um arquivo só (anexo)
    anexos = corpo.get("anexos") if isinstance(corpo.get("anexos"), list) else [corpo.get("anexo") or {}]
    arquivos = []  # [(bytes, mime)]
    if foto:
        if not (RE_FOTO.fullmatch(foto) and os.path.isfile(os.path.join(FOTOS, foto))):
            raise ValueError("A imagem não foi encontrada. Envie de novo.")
        with open(os.path.join(FOTOS, foto), "rb") as f:
            arquivos.append((f.read(), "image/jpeg"))
    else:
        for anexo in anexos[:6]:
            if not (isinstance(anexo, dict) and anexo.get("b64")):
                continue
            try:
                b = base64.b64decode(str(anexo["b64"]).split(",", 1)[-1], validate=True)
            except (ValueError, TypeError):
                raise ValueError("Arquivo inválido.")
            m = mime_anexo(b)
            if not m:
                raise ValueError("Envie uma imagem (JPG, PNG ou WebP) ou um PDF.")
            arquivos.append((b, m))
    if len(arquivos) > 1 and any(m == "application/pdf" for _, m in arquivos):
        raise ValueError("Envie um PDF por vez.")
    if arquivos and arquivos[0][1] == "application/pdf":  # fatura com senha: abre com a digitada ou as cadastradas
        arquivos[0] = (abrir_pdf(arquivos[0][0], corpo.get("senha"), corpo.get("guardar_senha") is True, corpo.get("nome_arquivo")), "application/pdf")
    bruto, mime = arquivos[0] if arquivos else (None, None)
    if not bruto and not texto:
        raise ValueError("Envie uma imagem, um PDF ou cole um texto.")
    limpar = ia_limpar_caixa if modo == "caixa" else ia_limpar
    saldos = modo == "auto" and bool(corpo.get("saldos"))
    so_invest = modo == "auto" and not saldos and bool(corpo.get("so_invest"))
    pessoa = str(corpo.get("pessoa") or "").strip()[:60] or None
    # o que veio do microfone conta como Falar no Uso da IA, como no InventarIA; o resto do jeito automático, como Ler com IA
    tipo_uso = "fala" if corpo.get("fala") and modo != "holerite" and not bruto else "saldos" if saldos else "ler" if modo == "auto" else modo
    if IA_MOCK:
        time.sleep(1.2)
        registrar_uso(tipo_uso, "ai_task.simulada", 1800, 600, len(arquivos), 1.2, "ok")
        if modo == "holerite":
            return {"holerite": ia_limpar_holerite(json.loads(json.dumps(IA_SIMULADA_HOLERITE))), "entidade": "ai_task.simulada"}
        if modo == "auto":
            simples = so_invest and re.search(r"\d", texto) and not re.search(r"apliquei|investi|aplica[çc]", texto, re.I)
            sim = ia_simulada_saldos(texto, d, pessoa) if saldos or simples else ia_simulada_auto(texto, "invest" if so_invest else corpo.get("dica"), d)
            r = _so_saldos(ia_limpar_auto(json.loads(json.dumps(sim)), d), saldos)
            if so_invest:
                r["lancamentos"] = []
            return dict(r, entidade="ai_task.simulada")
        return {"itens": limpar(json.loads(json.dumps(IA_SIMULADA_CAIXA if modo == "caixa" else IA_SIMULADA)), d),
                "entidade": "ai_task.simulada"}
    ent = d["ajustes"].get("ia_entidade") or ""

    def chamar(com_anexo, txt):
        instr = ia_prompt(d, modo, com_anexo, txt, saldos, pessoa, so_invest)
        if com_anexo and len(arquivos) > 1:
            instr += "\nAs imagens anexadas são páginas do mesmo documento, em ordem: leia todas e não repita o que aparecer em duas."
        payload = {"task_name": "GerencIA: " + ("atualizar saldos" if saldos else "ler " + {"caixa": "lançamentos", "holerite": "recibo de pagamento", "auto": "lançamentos e investimentos"}.get(modo, "investimentos")),
                   "instructions": instr}
        if ent:
            payload["entity_id"] = ent
        tmps = []
        try:
            if com_anexo:
                pasta = os.path.join(MEDIA_ROOT, IA_TMP_REL)
                if not os.path.isdir(MEDIA_ROOT):
                    raise ValueError("A pasta media do Home Assistant não está disponível para o app.")
                os.makedirs(pasta, exist_ok=True)
                payload["attachments"] = []
                for b, m in arquivos:
                    nome_tmp = f"{secrets.token_hex(8)}.{EXT_ANEXO[m]}"
                    tmps.append(os.path.join(pasta, nome_tmp))
                    with open(tmps[-1], "wb") as f:
                        f.write(b)
                    payload["attachments"].append({"media_content_id": f"media-source://media_source/local/{IA_TMP_REL}/{nome_tmp}",
                                                   "media_content_type": m})
            res = ia_chamar(tipo_uso, payload, len(arquivos) if com_anexo else 0, timeout=240)
        finally:
            for tmp in tmps:
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
    if modo == "holerite":
        return {"holerite": ia_limpar_holerite(extrair_json(dados)), "entidade": ent or "padrão do Home Assistant"}
    if modo == "auto":
        r = _so_saldos(ia_limpar_auto(extrair_json(dados), d), saldos)
        if so_invest:
            r["lancamentos"] = []
        return dict(r, entidade=ent or "padrão do Home Assistant")
    return {"itens": limpar(extrair_json(dados), d), "entidade": ent or "padrão do Home Assistant"}


# ---------------------------------------------------------------- conversar com a IA (o balão ao lado do microfone)

def _gravar_chat(caminho, texto):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    gravar_arquivo(caminho, texto)


CHAT = chat.Conversa(os.path.join(DATA_DIR, "chat.json"), _gravar_chat)


def chat_estado():
    return {"mensagens": CHAT.ler()}


def chat_acoes(cruas, d):
    """As ações que a IA propôs, limpas com as mesmas regras da leitura por IA (só fica o que o app consegue mostrar)."""
    a = {
        "lancamentos": ia_limpar_caixa({"itens": cruas.get("lancamentos") or []}, d)[:30],
        "investimentos": _aporte_sem_saldo(ia_limpar({"itens": cruas.get("investimentos") or []}, d))[:20],
        "pagar": chat.limpar_pagar(cruas.get("pagar"), d),
    }
    # um investimento novo sem nome nem valor não é ação
    a["investimentos"] = [i for i in a["investimentos"] if i["existente"] or i["valor"] > 0 or i["aporte"] > 0]
    return {k: v for k, v in a.items() if v}


def chat_enviar(corpo, usuario=None):
    d = ler()
    if not ia_ligada(d):
        raise ValueError("A IA está desligada. Para usar, ligue em Mais › Configurações › Integrações.")
    texto = str(corpo.get("texto") or "").strip()[:chat.MAX_TEXTO]
    if not texto:
        raise ValueError("Escreva uma mensagem.")
    eu = {"id": chat.uid(), "papel": "eu", "texto": texto, "em": chat.agora()}
    if corpo.get("fala"):
        eu["fala"] = True
    historico = CHAT.ler() + [eu]
    if IA_MOCK:
        time.sleep(0.6)
        registrar_uso("chat", "ai_task.simulada", 2000, 300, 0, 0.6, "ok")
        bruto = chat.simulado(texto, d)
    else:
        payload = {"task_name": "GerencIA: conversa",
                   "instructions": chat.instrucoes(d, historico, corpo.get("tela"), corpo.get("aba"), usuario)}
        ent = d["ajustes"].get("ia_entidade") or ""
        if ent:
            payload["entity_id"] = ent
        try:
            res = ia_chamar("chat", payload, 0, timeout=120)
        except ErroHA as e:
            raise ValueError(str(e))
        bruto = ((res or {}).get("service_response") or {}).get("data")
        if bruto is None:
            raise ValueError("A IA não devolveu resposta.")
        if isinstance(bruto, str):
            try:
                bruto = extrair_json(bruto)
            except ValueError:
                pass  # respondeu só com texto: vale como resposta
    resposta, cruas = chat.separar(bruto)
    acoes = chat_acoes(cruas, d) if cruas else {}
    ia = {"id": chat.uid(), "papel": "ia", "texto": resposta or ("Confira e confirme." if acoes else "Não entendi. Pode dizer de outro jeito?"),
          "em": chat.agora()}
    if acoes:
        ia["acoes"] = acoes
    return {"mensagens": CHAT.acrescentar(eu, ia)}


# ---------------------------------------------------------------- dicas de economia (assinaturas conferidas na origem)

DICAS_ARQ = os.path.join(DATA_DIR, "dicas.json")
FONTES_MOCK = os.environ.get("GERENCIA_FONTES_MOCK")  # pasta com <id>.html, só para testes
DOLAR_FIXO = os.environ.get("GERENCIA_DOLAR")         # só para testes
_conferindo = threading.Event()
_trava_conf = threading.Lock()

DICAS_SIMULADAS = {
    "nabucasa": {"planos": [
        {"plano": "Monthly", "moeda": "USD", "mensal": 6.5, "trecho_mensal": "$6.50 USD", "anual_total": 0, "anual_por_mes": 0, "trecho_anual": ""},
        {"plano": "Annual", "moeda": "USD", "mensal": 0, "trecho_mensal": "", "anual_total": 65, "anual_por_mes": 0, "trecho_anual": "$65.00 USD"}]},
    "spotify": {"planos": [
        {"plano": "Premium Individual", "moeda": "BRL", "mensal": 23.9, "trecho_mensal": "R$ 23,90 por 1 mês", "anual_total": 239, "trecho_anual": "R$ 239 por 1 ano"},
        {"plano": "Premium Duo", "moeda": "BRL", "mensal": 31.9, "trecho_mensal": "R$ 31,90 por 1 mês", "anual_total": 379, "trecho_anual": "R$ 379 por 1 ano"},
        {"plano": "Premium Família", "moeda": "BRL", "mensal": 40.9, "trecho_mensal": "R$ 40,90 por 1 mês", "anual_total": 490, "trecho_anual": "R$ 490 por 1 ano"},
        {"plano": "Premium Universitário", "moeda": "BRL", "mensal": 12.9, "trecho_mensal": "R$ 12,90 por 1 mês", "anual_total": 0, "trecho_anual": ""}]},
    "microsoft365": {"planos": [
        {"plano": "Microsoft 365 Personal", "moeda": "BRL", "mensal": 51, "trecho_mensal": "R$51,00/mês", "anual_total": 509, "trecho_anual": "R$509,00/ano"},
        {"plano": "Microsoft 365 Family", "moeda": "BRL", "mensal": 60, "trecho_mensal": "R$60,00/mês", "anual_total": 599, "trecho_anual": "R$599,00/ano"}]},
    # preço inventado de propósito: o app tem de recusar
    "claude": {"planos": [
        {"plano": "Pro", "moeda": "USD", "mensal": 20, "trecho_mensal": "$20 if billed monthly", "anual_total": 180, "trecho_anual": "$180 billed up front"}]},
}


def dicas_ler():
    try:
        with open(DICAS_ARQ, encoding="utf-8") as f:
            c = json.load(f)
        return c if isinstance(c, dict) else {}
    except (OSError, ValueError):
        return {}


def buscar_pagina(serv):
    if FONTES_MOCK:
        caminho = os.path.join(FONTES_MOCK, serv["id"] + ".html")
        if not os.path.isfile(caminho):
            raise OSError("sem página de teste")
        with open(caminho, encoding="utf-8") as f:
            return f.read()
    req = urllib.request.Request(serv["url"], headers={
        "User-Agent": f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 GerencIA/{VERSAO}",
        "Accept": "text/html,application/xhtml+xml", "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.6"})
    with urllib.request.urlopen(req, timeout=25) as r:
        bruto = r.read(4 * 1024 * 1024)
        cs = r.headers.get_content_charset() or "utf-8"
    return bruto.decode(cs, "replace")


def ia_disponivel(d):
    """Para ler texto basta qualquer IA com tarefa de IA (não precisa aceitar imagem)."""
    if IA_MOCK:
        return True
    if not TOKEN:
        return False
    try:
        ents = ia_entidades()
    except ErroHA:
        return False
    sel = d["ajustes"].get("ia_entidade") or ""
    return any(e["id"] == sel for e in ents) if sel else bool(ents)


def ia_gerar(d, nome, instrucoes, timeout=180):
    payload = {"task_name": nome, "instructions": instrucoes}
    ent = d["ajustes"].get("ia_entidade") or ""
    if ent:
        payload["entity_id"] = ent
    res = ia_chamar("precos", payload, 0, timeout=timeout)
    dados = ((res or {}).get("service_response") or {}).get("data")
    if dados is None:
        raise ValueError("A IA não devolveu resposta.")
    return dados


def conferir_fonte(serv, d):
    base = {"conferido": date.today().isoformat(), "url": serv["url"], "planos": [], "status": "erro"}
    try:
        pagina = buscar_pagina(serv)
    except Exception as e:  # noqa: BLE001
        log("Dicas: não abriu", serv["url"], e)
        return {**base, "status": "sem_acesso"}
    texto = assinaturas.html_texto(pagina)
    trechos = assinaturas.trechos_preco(texto)
    if not trechos:
        return {**base, "status": "sem_precos"}
    if not ia_ligada(d):
        return {**base, "status": "ia_desligada"}
    if not ia_disponivel(d):
        return {**base, "status": "sem_ia"}
    try:
        if IA_MOCK:
            dados = DICAS_SIMULADAS.get(serv["id"], {"planos": []})
            registrar_uso("precos", "ai_task.simulada", len(trechos), 400, 0, 0.6, "ok")
        else:
            dados = ia_gerar(d, f"GerencIA: preços de {serv['curto']}", assinaturas.prompt(serv, trechos))
        planos, recusados = assinaturas.limpar_planos(extrair_json(dados), texto)
    except (ErroHA, ValueError) as e:
        log("Dicas: IA em", serv["id"], e)
        return {**base, "status": "erro_ia"}
    if not planos:
        return {**base, "status": "nao_confere" if recusados else "sem_precos"}
    return {**base, "status": "ok", "planos": planos}


def dolar_atual(cache):
    hoje = date.today().isoformat()
    dl = dict(cache.get("dolar") or {})
    if DOLAR_FIXO:
        return {"valor": float(DOLAR_FIXO), "data": "teste", "buscado": hoje}
    if dl.get("buscado") == hoje and dl.get("valor"):
        return dl
    try:
        v, dt = bcb_ultimo(1)  # série 1 do SGS: dólar americano (venda)
        return {"valor": round(v, 4), "data": dt, "buscado": hoje}
    except Exception as e:  # noqa: BLE001
        log("Dólar:", e)
        dl["buscado"] = hoje
        return dl


def assinaturas_do_usuario(d, hoje=None):
    """Assinaturas reconhecidas: fixos (recorrências) e cobranças que se repetem em meses diferentes."""
    hoje = hoje or date.today()
    out = []
    ja_anuais = set()
    for r in d["recorrencias"]:
        serv = assinaturas.identificar(r.get("descricao")) if r.get("freq") == "anual" else None
        if serv and not r.get("fim"):
            ja_anuais.add(serv["id"])
    for r in d["recorrencias"]:
        # fixo com data para acabar não é assinatura que continua
        if r.get("tipo") == "receita" or r.get("fim"):
            continue
        serv = assinaturas.identificar(r.get("descricao"))
        if not serv or (r.get("freq") != "anual" and serv["id"] in ja_anuais):
            continue
        out.append({"chave": f"r:{r.get('id')}", "rid": r.get("id"), "origem": "fixo", "servico": serv["id"],
                    "descricao": r.get("descricao", ""), "valor": round(calc.num(r.get("valor")), 2),
                    "freq_anual": r.get("freq") == "anual", "conta": r.get("conta", ""), "cartao": bool(r.get("cartao")),
                    "categoria": r.get("categoria", ""), "dia": int(calc.num(r.get("dia")) or 1)})
    cobertos = {s["servico"] for s in out} | ja_anuais
    limite = (hoje - timedelta(days=100)).isoformat()
    grupos = {}
    for l in d["lancamentos"]:
        if (l.get("tipo") == "receita" or l.get("pulado") or l.get("recorrencia") or l.get("ajuste")
                or str(l.get("data") or "") < limite):
            continue
        serv = assinaturas.identificar(l.get("descricao"))
        if serv and serv["id"] not in cobertos:
            grupos.setdefault(serv["id"], []).append(l)
    for sid, ls in grupos.items():
        ls.sort(key=lambda l: str(l.get("data")))
        if len({str(l.get("data"))[:7] for l in ls}) < 2:
            continue
        ult = ls[-1]
        valores = [calc.num(l.get("valor")) for l in ls[-3:]]
        if min(valores) <= 0 or max(valores) > 1.15 * min(valores):
            continue  # valores muito diferentes: não parece a mesma mensalidade
        out.append({"chave": f"l:{sid}", "rid": None, "origem": "lancamentos", "servico": sid,
                    "descricao": ult.get("descricao", ""), "valor": round(calc.num(ult.get("valor")), 2), "freq_anual": False,
                    "conta": ult.get("conta", ""), "cartao": bool(ult.get("cartao")), "categoria": ult.get("categoria", ""),
                    "dia": int(str(ult.get("data"))[8:10] or 1)})
    return out


def _velha(fonte, forcar=False, dias_ok=30):
    """O preço precisa ser conferido de novo? Um preço bom vale dias_ok dias (a frequência do Conferir sozinho); um
    erro, 1 dia; no Conferir agora (forcar), só o conferido hoje fica."""
    if not fonte or not fonte.get("conferido"):
        return True
    try:
        dias = (date.today() - date.fromisoformat(fonte["conferido"])).days
    except ValueError:
        return True
    if forcar:
        return not (fonte.get("status") == "ok" and dias == 0)
    return dias >= (dias_ok if fonte.get("status") == "ok" else 1)


def dias_dicas(d):
    """De quantos em quantos dias o Conferir sozinho confere os preços: toda semana, a cada 15 dias ou todo mês."""
    return DICAS_FREQ.get(d["ajustes"].get("dicas_freq"), 30)


def _conferir(forcar, manual=False):
    try:
        d = ler()
        cache = dicas_ler()
        fontes = cache.get("fontes") or {}
        for sid in sorted({s["servico"] for s in assinaturas_do_usuario(d) if not s["freq_anual"]}):
            if _velha(fontes.get(sid), forcar, dias_dicas(d)):
                fontes[sid] = conferir_fonte(assinaturas.POR_ID[sid], d)
                log("Dicas:", sid, fontes[sid]["status"], len(fontes[sid]["planos"]), "planos")
        cache["fontes"] = fontes
        if any(p.get("moeda") == "USD" for f in fontes.values() for p in f.get("planos", [])):
            cache["dolar"] = dolar_atual(cache)
        cache["atualizado"] = agora_iso()
        os.makedirs(DATA_DIR, exist_ok=True)
        gravar_arquivo(DICAS_ARQ, json.dumps(cache, ensure_ascii=False, indent=1))
    except Exception as e:  # noqa: BLE001
        log("Dicas:", e)
    finally:
        _conferindo.clear()
    try:  # o que apareceu: avisa no celular (no Conferir agora, quem tocou já está vendo: só anota)
        avisar_dicas(ler(), silencioso=manual)
    except Exception as e:  # noqa: BLE001
        log("Aviso de dicas:", e)


def iniciar_conferencia(forcar=False, manual=False):
    with _trava_conf:
        if _conferindo.is_set():
            return False
        _conferindo.set()
    threading.Thread(target=_conferir, args=(forcar, manual), daemon=True).start()
    return True


def hora_das_dicas(d, agora=None):
    """Já passou do horário de conferir sozinho hoje (Mais › Configurações › Opções › Dicas de economia)?"""
    agora = agora or datetime.now()
    h, m = (int(x) for x in d["ajustes"].get("dicas_hora", AJUSTES_PADRAO["dicas_hora"]).split(":"))
    return (agora.hour, agora.minute) >= (h, m)


def dicas_estado(d, disparar=True):
    if d["ajustes"].get("dicas") is False:
        return {"dicas": [], "assinaturas": [], "conferindo": False, "desligadas": True,
                "catalogo": [c["curto"] for c in assinaturas.CATALOGO], "dolar": None, "atualizado": None}
    cache = dicas_ler()
    fontes = cache.get("fontes") or {}
    dolar = float(DOLAR_FIXO) if DOLAR_FIXO else (cache.get("dolar") or {}).get("valor")
    subs = assinaturas_do_usuario(d)
    # Conferir sozinho: uma assinatura nova é conferida logo; o preço conferido há mais tempo que a frequência escolhida
    # (toda semana, a cada 15 dias ou todo mês) e a procura do dia, a partir das 8h. Desligado, só no Conferir agora.
    auto = d["ajustes"].get("dicas_auto", True) is not False
    passou = hora_das_dicas(d)
    disparar = disparar and auto
    if disparar and any(not fontes.get(s["servico"]) or (passou and _velha(fontes.get(s["servico"]), dias_ok=dias_dicas(d))) for s in subs if not s["freq_anual"]):
        iniciar_conferencia()
    elif disparar and passou and not _conferindo.is_set() and str(cache.get("atualizado") or "")[:10] != datetime.now().date().isoformat():
        # nada para conferir na origem: a verificação do dia é procurar as assinaturas nos fixos e faturas
        cache["atualizado"] = agora_iso()
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            gravar_arquivo(DICAS_ARQ, json.dumps(cache, ensure_ascii=False, indent=1))
        except OSError as e:
            log("Dicas:", e)
    lista, dicas = [], []
    for s in subs:
        serv = assinaturas.POR_ID[s["servico"]]
        fonte = fontes.get(s["servico"])
        av = {"status": "ja_anual"} if s["freq_anual"] else assinaturas.avaliar(s["valor"], fonte, dolar)
        if av["status"] == "ia_desligada" and ia_ligada(d):  # visto com a IA desligada; ligada de novo, ainda não foi conferido
            av = {"status": "pendente"}
        if av["status"] == "pendente" and _conferindo.is_set():
            av["status"] = "conferindo"
        item = {**s, **av, "nome": serv["curto"], "fonte": serv["url"],
                "dominio": (urlparse(serv["url"]).hostname or "").replace("www.", ""),
                "conferido": (fonte or {}).get("conferido"), "texto": assinaturas.TEXTOS.get(av["status"], "")}
        lista.append(item)
        if av["status"] == "ok":
            dicas.append({"id": "anual:" + s["chave"], **item})
    dicas.sort(key=lambda x: -x["economia_ano"])
    return {"dicas": dicas, "assinaturas": lista, "conferindo": _conferindo.is_set(),
            "catalogo": [c["curto"] for c in assinaturas.CATALOGO], "dolar": cache.get("dolar") if not DOLAR_FIXO else {"valor": dolar, "data": "teste"},
            "atualizado": cache.get("atualizado"), "auto": auto, "freq": d["ajustes"].get("dicas_freq", "mes")}


# ---------------------------------------------------------------- aviso das dicas no celular (como o aviso de prazos do ResolvIA)

AVISOS = avisos.Avisos(lambda m, caminho, corpo=None: ha_request(m, caminho, corpo, timeout=15),
                       lambda comando: voz._ws_comando(HA_WS, TOKEN, comando), log)


def dicas_que_valem(d, est=None):
    """As dicas de plano anual que o app mostra: as que economizam de verdade R$ 10 ou mais por ano (já descontando o
    que o dinheiro renderia, como no app) e não foram dispensadas, da maior para a menor."""
    est = est or dicas_estado(d, disparar=False)
    fora = set(d["ajustes"].get("dicas_fora") or [])
    reserva = calc.renda_reserva(d)
    out = []
    for x in est["dicas"]:
        if x["id"] in fora:
            continue
        real = calc.economia_real(x["valor"], x["preco_anual"], reserva)["real"]
        if real >= 10:
            out.append({**x, "real": real})
    return sorted(out, key=lambda x: -x["real"])


def avisar_dicas(d, silencioso=False):
    """Uma dica nova (que ainda não foi avisada) vai para os celulares de quem foi escolhido; cada dica, uma vez. Uma
    dica que some é esquecida (volta a ser avisada se aparecer de novo). silencioso: só anota (o Conferir agora)."""
    aj = d["ajustes"]
    if aj.get("dicas") is False or not ia_ligada(d) or _conferindo.is_set():
        return 0
    atuais = {x["id"]: x for x in dicas_que_valem(d)}
    cache = dicas_ler()
    antes = cache.get("avisadas") or {}
    novas = [x for k, x in atuais.items() if k not in antes]
    avisadas = {k: v for k, v in antes.items() if k in atuais}
    enviados = 0
    if novas and aj.get("dicas_aviso") is True and not silencioso:
        alvos = []
        try:
            for pessoa in AVISOS.pessoas():
                if pessoa["id"] in (aj.get("dicas_para") or []):
                    alvos += [c for c in pessoa["celulares"] if c not in alvos]
        except Exception as e:  # noqa: BLE001
            log("Aviso de dicas: não consegui ver as pessoas da casa:", e)
            return 0  # tenta de novo na próxima volta
        enviados = AVISOS.enviar(alvos, avisos.texto_dicas(novas), "gerencia-dicas") if alvos else 0
    avisadas.update({x["id"]: date.today().isoformat() for x in novas})
    if avisadas != antes:
        cache["avisadas"] = avisadas
        try:
            gravar_arquivo(DICAS_ARQ, json.dumps(cache, ensure_ascii=False, indent=1))
        except OSError as e:
            log("Aviso de dicas:", e)
    return enviados


def pessoas_aviso(user_id=None):
    """Quem pode receber o aviso: [{"id", "nome", "celular": tem celular, "eu": é quem está usando o app}]."""
    if not TOKEN:
        raise ErroHA("Fora do Home Assistant não dá para avisar no celular.")
    return [{"id": p["id"], "nome": p["nome"], "celular": bool(p["celulares"]), "eu": bool(user_id) and p["user_id"] == user_id}
            for p in AVISOS.pessoas(forcar=True)]


def testar_aviso(user_id):
    """Testar: o aviso agora, nos celulares de quem está usando o app (as dicas de agora ou um exemplo)."""
    if not TOKEN:
        raise ValueError("Fora do Home Assistant não dá para avisar no celular.")
    eu = next((p for p in AVISOS.pessoas(forcar=True) if user_id and p["user_id"] == user_id), None)
    if not eu:
        raise ValueError("Você não é uma pessoa da casa no Home Assistant.")
    if not eu["celulares"]:
        raise ValueError("Sem celular ligado a você no Home Assistant.")
    d = ler()
    dicas = dicas_que_valem(d)
    texto = avisos.texto_dicas(dicas) if dicas else {"title": "💡 Dicas de economia", "message": "Nenhuma dica agora. Quando aparecer, o aviso vem assim."}
    if not AVISOS.enviar(eu["celulares"], texto, "gerencia-dicas-teste"):
        raise ValueError("O Home Assistant não entregou o aviso.")
    return {"enviados": len(eu["celulares"])}


# ---------------------------------------------------------------- Falar (fala para texto do Home Assistant)

VOZ = voz.Voz(HA_API, HA_WS, TOKEN, log, simulada=IA_MOCK and not os.environ.get("GERENCIA_HA_WS"))
BENS = bens.Bens(log)


def bens_estado(d, forcar=False):
    """Os bens da casa, do InventarIA, já depreciados; sem o InventarIA (ou desligado), o motivo."""
    if d["ajustes"].get("bens") is False:
        return {"ok": False, "desligado": True}
    try:
        return bens.resumo(BENS.ler(forcar), d["ajustes"])
    except bens.ErroBens as e:
        return {"ok": False, "motivo": str(e)}
    except Exception as e:  # noqa: BLE001
        log("Bens:", e)
        return {"ok": False, "motivo": f"Não consegui ler o InventarIA ({e})."}


def voz_status():
    if not ia_ligada():
        return {"pronta": False, "motivo": "A IA está desligada em Mais › Configurações › Integrações."}
    if not TOKEN and not IA_MOCK:
        return {"pronta": False, "motivo": "Fora do Home Assistant não dá para falar."}
    return VOZ.status(ler()["ajustes"].get("voz_motor") or "")


def voz_texto(pcm):
    if not ia_ligada():
        raise ValueError("A IA está desligada. Para usar, ligue em Mais › Configurações › Integrações.")
    t0 = time.time()
    try:
        r = VOZ.texto(pcm, ler()["ajustes"].get("voz_motor") or "")
    except voz.ErroVoz as e:
        log("Falar:", e)
        raise ValueError(str(e))
    log(f"Falar: {len(pcm) / 32000:.1f}s de áudio, texto em {time.time() - t0:.1f}s ({r.get('nome') or 'fala para texto'})")
    return r


# ---------------------------------------------------------------- HTTP

TIPOS_MIME = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png",
    ".json": "application/json", ".jpg": "image/jpeg", ".woff2": "font/woff2", ".woff": "font/woff", ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
}

CAMPOS_USUARIO = ("bancos", "investimentos", "ajustes", "exemplo", "lancamentos", "recorrencias", "categorias")


CONEXAO = integracao.Conexao(DATA_DIR, SHARE_DIR, PORTA, VERSAO, log)
# O CorrerIA (o WhatsApp, o Claude e o Gemini) usa as ferramentas (/api/integracao/ferramentas: ler e gravar, sem a IA
# daqui) e, com a IA ligada, pergunta pela rota /api/integracao/conversa (as fotos e os PDFs vêm por ela). A chave própria
# fica em share/gerencia/correria.json, que só existe com Mais › Configurações › Integrações › CorrerIA ligado.
CORRERIA = integracao.Conexao(DATA_DIR, SHARE_DIR, PORTA, VERSAO, log, nome="correria",
                              extra={"nome": "GerencIA", "assunto": "finanças da casa: caixa, gastos, recebimentos, contas a pagar, "
                                     "cartões e faturas, investimentos e patrimônio"})
CORRERIA_USO = {"ultimo": None}  # a última ferramenta usada: {"app": "Claude", "em", "nome"}


def integracao_ligada(d=None):
    return (d or ler()).get("ajustes", {}).get("integracao", True) is not False


def correria_ligada(d=None):
    """As ferramentas (ler e gravar pelo WhatsApp, pelo Claude e pelo Gemini): só a opção, sem precisar da IA daqui."""
    d = d or ler()
    return d.get("ajustes", {}).get("correria") is True


def correria_conversa(d=None):
    """A conversa com a IA daqui (fotos e PDFs pelo WhatsApp): a opção e a IA ligadas."""
    d = d or ler()
    return correria_ligada(d) and ia_ligada(d)


def correria_estado(d):
    return correria_ligada(d), correria_conversa(d)


def publicar_correria(d=None):
    d = d or ler()
    extra = {"ferramentas": "/api/integracao/ferramentas"}
    if correria_conversa(d):
        extra.update(rota="/api/integracao/conversa", anexos=sorted(EXT_ANEXO))
    CORRERIA.publicar(correria_ligada(d), extra)


def usar_ferramenta(corpo):
    """Uma ferramenta chamada pelo CorrerIA: as de leitura só leem; as de gravar mudam os dados (com a revisão nova, a
    versão automática e a tela atualizada como no Paguei do CronologIA)."""
    nome = str(corpo.get("nome") or "")
    pessoa = corpo.get("pessoa") if isinstance(corpo.get("pessoa"), dict) else {}
    cliente = str(corpo.get("cliente") or "CorrerIA")[:40]
    with TRAVA:
        d = ler()
        texto, mudou = ferramentas.chamar(nome, corpo.get("argumentos"), d)
        if mudou:
            d["rev"] = d["rev"] + 1
            salvar(d)
    CORRERIA_USO["ultimo"] = {"app": cliente, "em": agora_iso(), "nome": nome}
    if mudou:
        quem = str(pessoa.get("nome") or "")[:40]
        log("CorrerIA:", cliente + (f" ({quem})" if quem else ""), nome, "→", texto.split("\n")[0][:160])
    return {"texto": texto}


PERGUNTA_RE = re.compile(r"\?|^(quanto|quantos|quantas|qual|quais|quando|onde|como|o que|que|por que|porque|tem|é|e)\b", re.I)


def conversa_correria(corpo):
    """Uma pergunta que veio pelo WhatsApp (o CorrerIA manda a conversa daquela pessoa): só a resposta, sem ações e sem
    mexer na conversa do app. Com um anexo (foto ou PDF), lê com a IA e o que achar fica para conferir no Início."""
    if isinstance(corpo.get("anexo"), dict) and corpo["anexo"].get("b64"):
        return conversa_anexo(corpo)
    d = ler()
    texto = str(corpo.get("texto") or "").strip()[:chat.MAX_TEXTO]
    if not texto:
        raise ValueError("Escreva uma mensagem.")
    hist = [m for m in corpo.get("historico") or [] if isinstance(m, dict)][-chat.MAX_HISTORICO:]
    historico = [{"papel": "ia" if m.get("papel") == "ia" else "eu", "texto": str(m.get("texto") or "")[:chat.MAX_TEXTO]} for m in hist]
    historico.append({"papel": "eu", "texto": texto})
    pessoa = corpo.get("pessoa") if isinstance(corpo.get("pessoa"), dict) else {}
    nome = str(pessoa.get("nome") or "")[:60]
    if IA_MOCK:
        registrar_uso("whatsapp", "ai_task.simulada", 2000, 200, 0, 0.3, "ok")
        bruto = chat.simulado(texto, d)
    else:
        canal = "correria" if corpo.get("canal") == "correria" else "whatsapp"
        payload = {"task_name": "GerencIA: CorrerIA" if canal == "correria" else "GerencIA: WhatsApp",
                   "instructions": chat.instrucoes_whatsapp(d, historico, nome, canal=canal)}
        ent = d["ajustes"].get("ia_entidade") or ""
        if ent:
            payload["entity_id"] = ent
        try:
            res = ia_chamar("whatsapp", payload, 0, timeout=120)
        except ErroHA as e:
            raise ValueError(str(e))
        bruto = ((res or {}).get("service_response") or {}).get("data")
        if bruto is None:
            raise ValueError("A IA não devolveu resposta.")
        if isinstance(bruto, str):
            try:
                bruto = extrair_json(bruto)
            except ValueError:
                pass  # respondeu só com texto: vale como resposta
    resposta, _ = chat.separar(bruto)
    log("CorrerIA: pergunta de", nome or "alguém", "respondida")
    return {"resposta": resposta or "Não entendi. Pode dizer de outro jeito?"}


def _linhas_lidas(lanc, invs):
    out = [f"- {x.get('descricao') or 'Sem descrição'}: {calc.fmt_brl(float(x.get('valor') or 0))}"
           + (f" ({x['parcela_atual']}/{x['parcelas_total']})" if x.get("parcelas_total") else "") for x in lanc[:8]]
    out += [f"- {x.get('nome') or 'Investimento'}: {calc.fmt_brl(float(x.get('valor') or x.get('aporte') or 0))}" for x in invs[:5]]
    if len(lanc) > 8:
        out.append(f"- e mais {len(lanc) - 8}")
    return "\n".join(out)


def conversa_anexo(corpo):
    """Uma foto ou um PDF pelo WhatsApp: a IA lê como no Ler com IA (o PDF com senha abre com as Senhas dos PDFs). O que
    achar fica para conferir no Início, como as faturas por e-mail (nada é lançado sozinho). Com uma pergunta junto
    ("quanto deu essa nota?"), a IA responde com o que leu."""
    anexo = corpo["anexo"]
    texto = str(corpo.get("texto") or "").strip()[:chat.MAX_TEXTO]
    pessoa = corpo.get("pessoa") if isinstance(corpo.get("pessoa"), dict) else {}
    nome = str(pessoa.get("nome") or "")[:60]
    arquivo = str(anexo.get("nome") or "").strip()[:120]
    try:
        bruto = base64.b64decode(str(anexo["b64"]).split(",", 1)[-1], validate=True)
    except (ValueError, TypeError):
        raise ValueError("Arquivo inválido.") from None
    mime = mime_anexo(bruto)
    if not mime:
        return {"resposta": "Esse tipo de arquivo eu não leio. Mande uma foto ou um PDF."}
    try:
        r = ia_ler({"modo": "auto", "dica": "caixa", "nome_arquivo": arquivo,
                    "anexo": {"b64": f"data:{mime};base64," + base64.b64encode(bruto).decode()}})
    except ErroSenhaPdf:
        return {"resposta": "Esse PDF tem senha, e nenhuma das senhas cadastradas abre. Cadastre a senha no GerencIA "
                            "(Mais › Configurações › Integrações › Senhas dos PDFs) e mande de novo."}
    lanc, invs = r.get("lancamentos") or [], r.get("investimentos") or []
    oque = "o PDF" if mime == "application/pdf" else "a foto"
    if lanc or invs:
        it = pendente_whatsapp(nome, texto, arquivo or ("PDF" if mime == "application/pdf" else "Foto"), {"lancamentos": lanc, "investimentos": invs})
        lido = f"Li {_resumo_fatura(it)} n{oque}:\n{_linhas_lidas(lanc, invs)}"
        fim = "Para lançar, confira no GerencIA: está nos Avisos do Início."
    else:
        lido, fim = f"Não encontrei gastos nem recebimentos n{oque}.", ""
    if texto and PERGUNTA_RE.search(texto):
        contexto = f"{texto}\n\n(A pessoa mandou {oque} junto. {lido})"
        resposta = conversa_correria({"texto": contexto, "historico": corpo.get("historico"), "pessoa": pessoa, "canal": corpo.get("canal")})["resposta"]
        return {"resposta": resposta + (f"\n\n{fim}" if fim else "")}
    return {"resposta": lido + (f"\n\n{fim}" if fim else "")}


def pendente_whatsapp(nome, texto, arquivo, resultado):
    """O que a IA leu de uma foto ou PDF do WhatsApp fica para conferir no Início (junto das faturas por e-mail)."""
    it = {"id": secrets.token_hex(6), "origem": "whatsapp", "chave": "", "de": nome or "WhatsApp", "assunto": texto[:200],
          "data": agora_iso(), "recebido_em": agora_iso(), "arquivo": arquivo, "estado": "conferir", "erro": "", "resultado": resultado}
    with _trava_emails:
        e = emails_ler()
        e["itens"].insert(0, it)
        for velho in e["itens"][EMAILS_MAX:]:
            _email_apagar_pdf(velho["id"])
        e["itens"] = e["itens"][:EMAILS_MAX]
        _emails_gravar(e)
    log("CorrerIA: o que veio de", nome or "alguém", "pelo WhatsApp ficou para conferir")
    return it


class Handler(BaseHTTPRequestHandler):
    server_version = "GerencIA/" + VERSAO

    def log_message(self, fmt, *args):
        if DEV:
            log(self.address_string(), fmt % args)

    # ---- util
    def permitido(self):
        if self.caminho() in ("/api/integracao/conversa", "/api/integracao/ferramentas"):
            # o CorrerIA (WhatsApp, Claude e Gemini), com a chave de share/gerencia/correria.json
            conversa = self.caminho().endswith("conversa")
            if (correria_conversa() if conversa else correria_ligada()) and CORRERIA.autorizado(self.headers, marcar=conversa):
                return True
            self.enviar(401, {"erro": "Chave inválida ou CorrerIA desligado no GerencIA."})
            return False
        if self.caminho().startswith("/api/integracao/"):
            # Outros apps do Home Assistant (CronologIA) chegam pela rede interna, com a chave de share/gerencia.
            if integracao_ligada() and CONEXAO.autorizado(self.headers):
                return True
            self.enviar(401, {"erro": "Chave inválida ou conexão com outros apps desligada no GerencIA."})
            return False
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
                d["integracao_ultimo"] = CONEXAO.ultimo
                d["correria_ultimo"] = CORRERIA.ultimo
                d["correria_uso"] = CORRERIA_USO["ultimo"]
                return self.enviar(200, d)
            if p == "/api/rev":
                return self.enviar(200, {"rev": ler()["rev"], "integracao_ultimo": CONEXAO.ultimo, "correria_ultimo": CORRERIA.ultimo,
                                         "correria_uso": CORRERIA_USO["ultimo"], "emails": emails_carimbo()})
            if p == "/api/integracao/ferramentas":
                return self.enviar(200, {"versao": VERSAO, "instrucoes": ferramentas.INSTRUCOES, "ferramentas": ferramentas.lista()})
            if p == "/api/integracao/contas":
                hoje = date.today()
                de = date.fromisoformat(q.get("de", [(hoje - timedelta(days=31)).isoformat()])[0])
                ate = date.fromisoformat(q.get("ate", [(hoje + timedelta(days=62)).isoformat()])[0])
                return self.enviar(200, dict(integracao.listar(ler(), de, ate, hoje), versao=VERSAO))
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
            if p == "/api/ia/uso":
                return self.enviar(200, resumo_uso())
            if p == "/api/voz/status":
                return self.enviar(200, voz_status())
            if p == "/api/chat":
                return self.enviar(200, chat_estado())
            if p == "/api/backups":
                return self.enviar(200, listar_backups())
            if p == "/api/dicas":
                return self.enviar(200, dicas_estado(ler()))
            if p == "/api/senhas":
                return self.enviar(200, {"senhas": senhas_listar()})
            if p == "/api/emails":
                return self.enviar(200, emails_estado(forcar=bool(q.get("forcar"))))
            if p == "/api/emails/pdf":
                return self.enviar(200, email_pdf_b64((q.get("id") or [""])[0]))
            if p == "/api/avisos/pessoas":
                try:
                    return self.enviar(200, {"pessoas": pessoas_aviso(self.headers.get("X-Remote-User-Id"))})
                except Exception as e:  # noqa: BLE001
                    return self.enviar(200, {"pessoas": None, "erro": str(e) if isinstance(e, ErroHA) else "Não consegui ver as pessoas da casa."})
            if p == "/api/bens":
                return self.enviar(200, bens_estado(ler()))
            if p == "/api/export/zip":
                return self.baixar(gerar_zip(ler()), "application/zip", nome_arquivo("zip"))
            if p == "/api/versoes":
                return self.enviar(200, listar_versoes())
            if p == "/relatorio.pdf":
                quem, d = (q.get("quem") or ["todos"])[0], ler()
                return self.baixar(gerar_relatorio_pdf(d, quem, bens_relatorio(d), (q.get("detalhar") or [""])[0] == "1"),
                                   "application/pdf", nome_relatorio(quem))
            if p in ("/relatorio", "/relatorio.html"):
                d = ler()
                corpo = gerar_relatorio(d, (q.get("tema") or [None])[0], (q.get("quem") or ["todos"])[0], bens_relatorio(d),
                                        (q.get("detalhar") or [""])[0] == "1")
                if q.get("baixar"):
                    return self.baixar(corpo, "text/html; charset=utf-8", nome_arquivo("html"))
                return self.enviar(200, corpo, "text/html; charset=utf-8")
            return self.estatico(p)
        except ValueError as e:  # pedido inválido (um período ou uma data ruim): 400, não erro do app
            return self.enviar(400, {"erro": str(e)})
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
            if p == "/api/bens/atualizar":
                return self.enviar(200, bens_estado(ler(), forcar=True))
            if p == "/api/senhas":
                c = self.corpo_json()
                r = {"senhas": senha_nova(c.get("nome"), c.get("senha"))}
                reler_emails_com_senha()  # a senha nova pode abrir as faturas do e-mail que esperavam
                return self.enviar(200, r)
            if p in ("/api/emails/ler", "/api/emails/feito", "/api/emails/ignorar"):
                eid = str(self.corpo_json().get("id") or "")
                if p.endswith("ler"):
                    email_ler_depois(eid)
                else:
                    _email_mudar(eid, estado="feito" if p.endswith("feito") else "ignorado", erro="")
                return self.enviar(200, emails_estado())
            if p == "/api/emails/simular":
                return self.enviar(200, email_simular(self.corpo_json()))
            if p == "/api/senhas/apagar":
                return self.enviar(200, {"senhas": senha_apagar(str(self.corpo_json().get("id") or ""))})
            if p == "/api/avisos/testar":
                return self.enviar(200, testar_aviso(self.headers.get("X-Remote-User-Id")))
            if p == "/api/dicas/conferir":
                iniciar_conferencia(forcar=True, manual=True)
                return self.enviar(200, dicas_estado(ler(), disparar=False))
            if p == "/api/voz":
                return self.enviar(200, voz_texto(self.corpo()))
            if p == "/api/chat":
                return self.enviar(200, chat_enviar(self.corpo_json(), self.headers.get("X-Remote-User-Display-Name") or self.headers.get("X-Remote-User-Name")))
            if p == "/api/chat/acao":
                c = self.corpo_json()
                return self.enviar(200, {"mensagens": CHAT.marcar(str(c.get("id") or ""), c.get("grupo"), c.get("estado"))})
            if p == "/api/chat/limpar":
                return self.enviar(200, {"mensagens": CHAT.limpar()})
            if p == "/api/backups/restaurar":
                return self.enviar(200, restaurar_backup(self.corpo_json().get("nome", "")))
            if p == "/api/importar":
                d = importar(self.corpo(), self.headers.get("X-Nome-Arquivo"))
                return self.enviar(200, d)
            if p == "/api/versoes/restaurar":
                return self.restaurar(self.corpo_json().get("nome", ""))
            if p in ("/api/integracao/pagar", "/api/integracao/desfazer", "/api/integracao/nova"):
                return self.post_integracao(p.rsplit("/", 1)[1], self.corpo_json())
            if p == "/api/integracao/conversa":
                return self.enviar(200, conversa_correria(self.corpo_json()))
            if p == "/api/integracao/ferramentas":
                return self.enviar(200, usar_ferramenta(self.corpo_json()))
            return self.enviar(404, {"erro": "não encontrado"})
        except LookupError as e:
            return self.enviar(404, {"erro": str(e)})
        except (ValueError, zipfile.BadZipFile) as e:  # com o código, quando há (senha_pdf: a tela pede a senha do PDF)
            return self.enviar(400, {"erro": str(e), **({"codigo": e.codigo} if getattr(e, "codigo", None) else {})})
        except Exception as e:  # noqa: BLE001
            log("Erro POST", p, e)
            return self.enviar(500, {"erro": str(e)})

    def post_integracao(self, acao, corpo):
        with TRAVA:
            d = ler()
            if acao == "nova":
                novo = integracao.nova(d, corpo)
            else:
                v = corpo.get("valor")
                integracao.pagar(d, corpo.get("id"), float(v) if v not in (None, "") else None, pago=acao == "pagar")
                novo = corpo.get("id")
            d["rev"] = d["rev"] + 1
            salvar(d)
        log("Conexão:", CONEXAO.ultimo["app"] if CONEXAO.ultimo else "app", acao, novo)
        return self.enviar(200, {"ok": True, "id": novo, "rev": d["rev"]})

    def put_state(self, corpo):
        with TRAVA:
            atual = ler()
            if int(corpo.get("rev", -1)) != atual["rev"]:
                return self.enviar(409, atual)
            ligada_antes, correria_antes = integracao_ligada(atual), correria_estado(atual)
            for k in CAMPOS_USUARIO:
                if k in corpo:
                    atual[k] = corpo[k]
            if corpo.get("substituir_historico") and isinstance(corpo.get("historico"), list):
                atual["historico"] = corpo["historico"]
            d = normalizar(atual)
            d["rev"] = atual["rev"] + 1
            salvar(d)
        if integracao_ligada(d) != ligada_antes:
            CONEXAO.publicar(integracao_ligada(d))
        if correria_estado(d) != correria_antes:
            publicar_correria(d)
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

# ---------------------------------------------------------------- faturas por e-mail
# A integração IMAP do Home Assistant avisa cada e-mail novo (evento imap_content); o app escuta pelo WebSocket
# (emails.Escuta), pega o PDF da fatura (imap.fetch_part), abre com as senhas cadastradas e lê com a IA. A fatura lida
# espera a conferência na tela (nada é lançado sozinho). Fica em /data/emails.json e os PDFs em /data/emails, fora das
# exportações; os mais velhos saem sozinhos.
EMAILS_ARQ = os.path.join(DATA_DIR, "emails.json")
EMAILS_PDF = os.path.join(DATA_DIR, "emails")
EMAILS_MAX = 30          # os últimos e-mails com PDF guardados
EMAILS_VISTOS = 300      # os já recebidos (o Home Assistant manda o último de novo quando reinicia)
EMAIL_ESTADOS = ("lendo", "conferir", "senha", "erro", "fora", "feito", "ignorado")
RE_EMAIL_ID = re.compile(r"^[0-9a-f]{12}$")
EMAIL_SIMULADO = {}      # só com a IA simulada (testes e prévia): uid -> bytes do PDF
_trava_emails = threading.Lock()
_contas_imap = {"t": 0.0, "v": None}


def emails_ler():
    try:
        with open(EMAILS_ARQ, encoding="utf-8") as f:
            e = json.load(f)
    except (OSError, ValueError):
        e = {}
    if not isinstance(e, dict):
        e = {}
    itens = [x for x in e.get("itens") or [] if isinstance(x, dict) and RE_EMAIL_ID.match(str(x.get("id") or ""))
             and x.get("estado") in EMAIL_ESTADOS]
    vistos = [x for x in e.get("vistos") or [] if isinstance(x, str)][-EMAILS_VISTOS:]
    return {"itens": itens, "vistos": vistos}


def _emails_gravar(e):
    gravar_arquivo(EMAILS_ARQ, json.dumps(e, ensure_ascii=False, indent=1))


def _email_pdf(eid):
    return os.path.join(EMAILS_PDF, eid + ".pdf")


def _email_apagar_pdf(eid):
    try:
        os.remove(_email_pdf(eid))
    except OSError:
        pass


def emails_carimbo():
    """Muda quando os e-mails mudam: a tela pede a lista de novo (pelo /api/rev, a cada 20 s)."""
    try:
        return os.path.getmtime(EMAILS_ARQ)
    except OSError:
        return 0


def _email_mudar(eid, se=None, **campos):
    """Muda um e-mail guardado; lançado ou ignorado, o PDF e o que a IA leu saem. se: só muda se ainda estiver nesse
    estado (a leitura que termina depois de você lançar ou ignorar não volta o e-mail para conferir)."""
    with _trava_emails:
        e = emails_ler()
        it = next((x for x in e["itens"] if x["id"] == eid), None)
        if not it:
            raise ValueError("Esse e-mail não está mais aqui.")
        if se and it["estado"] != se:
            return dict(it)
        it.update(campos)
        if it["estado"] in ("feito", "ignorado"):
            it.pop("resultado", None)
            _email_apagar_pdf(eid)
        _emails_gravar(e)
        return dict(it)


def email_publico(it):
    """O que a tela vê de um e-mail (sem o id da conta nem o da mensagem)."""
    r = {k: it.get(k) or "" for k in ("id", "assunto", "data", "recebido_em", "arquivo", "estado", "erro")}
    r["origem"] = "whatsapp" if it.get("origem") == "whatsapp" else "email"
    if r["origem"] == "whatsapp":  # quem mandou, pelo nome da pessoa no Home Assistant
        r["de"], r["endereco"] = str(it.get("de") or ""), ""
    else:
        r["de"], r["endereco"] = emails.nome_remetente(it.get("de")), emails.endereco(it.get("de"))
    if it.get("estado") == "conferir":
        r["resultado"] = it.get("resultado") or {"lancamentos": [], "investimentos": []}
    return r


def _email_simulado():
    return IA_MOCK and not os.environ.get("GERENCIA_HA_WS")


def contas_imap(forcar=False):
    """As contas de e-mail da integração IMAP do Home Assistant: [{"id", "nome", "ok"}] (None: não consegui ver)."""
    if _email_simulado():
        return [{"id": "imap-simulado", "nome": "ana@exemplo.com", "ok": True}]
    if not TOKEN:
        return None
    if not forcar and _contas_imap["v"] is not None and time.time() - _contas_imap["t"] < 300:
        return _contas_imap["v"]
    try:
        r = voz._ws_comando(HA_WS, TOKEN, {"type": "config_entries/get", "domain": "imap"}) or []
        v = [{"id": str(x.get("entry_id") or ""), "nome": str(x.get("title") or "E-mail"), "ok": x.get("state") == "loaded"}
             for x in r if isinstance(x, dict) and x.get("domain", "imap") == "imap"]
    except Exception as e:  # noqa: BLE001
        log("E-mail: não consegui ver as contas do Home Assistant:", e)
        v = None
    _contas_imap.update(t=time.time(), v=v)
    return v


def emails_estado(forcar=False):
    """Para a tela: ligado, se está escutando o Home Assistant, as contas de e-mail e os e-mails com PDF recebidos."""
    d = ler()
    ligado = d["ajustes"].get("email") is True and ia_ligada(d)
    if ligado and ESCUTA and not ESCUTA.conectada:
        ESCUTA.acordar()
    return {"ligado": ligado,
            "conectada": ligado and (_email_simulado() or bool(ESCUTA and ESCUTA.conectada)),
            "contas": contas_imap(forcar) if ligado else None,
            "itens": [email_publico(x) for x in emails_ler()["itens"]]}


def email_chegou(ev):
    """O evento imap_content: um e-mail com PDF fica guardado; o de fatura (do remetente cadastrado ou, sem nenhum,
    com fatura no assunto) é lido com a IA. Devolve o id guardado, ou None."""
    d = ler()
    aj = d["ajustes"]
    if aj.get("email") is not True or not ia_ligada(d):
        return None
    parte, arquivo = emails.anexo_pdf(ev.get("parts"))
    if parte is None or not ev.get("uid") or not ev.get("entry_id"):
        return None
    k = emails.chave(ev)
    fatura = emails.e_fatura(ev.get("sender"), ev.get("subject"), arquivo, aj.get("email_de"))
    with _trava_emails:
        e = emails_ler()
        if k in e["vistos"]:
            return None
        e["vistos"] = (e["vistos"] + [k])[-EMAILS_VISTOS:]
        it = {"id": secrets.token_hex(6), "chave": k, "entry": str(ev["entry_id"]), "uid": str(ev["uid"]), "parte": parte,
              "de": str(ev.get("sender") or "")[:200], "assunto": str(ev.get("subject") or "")[:200],
              "data": str(ev.get("date") or "")[:25], "recebido_em": agora_iso(), "arquivo": str(arquivo)[:120],
              "estado": "lendo" if fatura else "fora", "erro": ""}
        e["itens"].insert(0, it)
        for velho in e["itens"][EMAILS_MAX:]:
            _email_apagar_pdf(velho["id"])
        e["itens"] = e["itens"][:EMAILS_MAX]
        _emails_gravar(e)
    log(f"E-mail de {emails.endereco(it['de'])} com PDF:", "lendo a fatura" if fatura else "não é de fatura")
    if fatura:
        email_ler(it["id"])
    return it["id"]


def _email_baixar(it):
    """Os bytes do PDF anexado, pela ação imap.fetch_part do Home Assistant."""
    if IA_MOCK and it["uid"] in EMAIL_SIMULADO:
        return EMAIL_SIMULADO[it["uid"]]
    res = ha_request("POST", "/services/imap/fetch_part?return_response", {"entry": it["entry"], "uid": it["uid"], "part": it["parte"]}, timeout=60)
    r = (res or {}).get("service_response") or {}
    bruto = emails.decodificar(r.get("part_data"), r.get("content_transfer_encoding"))
    if not bruto.startswith(b"%PDF"):
        raise ValueError("O anexo do e-mail não é um PDF.")
    return bruto


def email_ler(eid, avisar=True):
    """Pega o PDF do e-mail (guarda uma cópia), abre com as senhas cadastradas e lê com a IA: fica em conferir, senha
    (nenhuma senha cadastrada abriu) ou erro. Lida, avisa no celular de quem foi escolhido."""
    it = _email_mudar(eid, estado="lendo", erro="")
    try:
        if os.path.isfile(_email_pdf(eid)):
            with open(_email_pdf(eid), "rb") as f:
                bruto = f.read()
        else:
            bruto = _email_baixar(it)
            os.makedirs(EMAILS_PDF, exist_ok=True)
            with open(_email_pdf(eid), "wb") as f:
                f.write(bruto)
        r = ia_ler({"modo": "auto", "dica": "caixa", "nome_arquivo": it["arquivo"],
                    "anexo": {"b64": "data:application/pdf;base64," + base64.b64encode(bruto).decode()}})
        lanc, invs = r.get("lancamentos") or [], r.get("investimentos") or []
        if not lanc and not invs:
            return _email_mudar(eid, se="lendo", estado="erro", erro="A IA não encontrou lançamentos neste PDF.")
        it = _email_mudar(eid, se="lendo", estado="conferir", resultado={"lancamentos": lanc, "investimentos": invs})
    except ErroSenhaPdf as e:
        return _email_mudar(eid, se="lendo", estado="senha", erro=str(e))
    except Exception as e:  # noqa: BLE001  (lendo em segundo plano: qualquer erro vira o aviso do e-mail)
        log("E-mail:", e)
        msg = str(e) if isinstance(e, (ValueError, ErroHA, voz.ErroVoz)) else ""
        return _email_mudar(eid, se="lendo", estado="erro", erro=msg or "Não consegui ler.")
    if avisar and it["estado"] == "conferir":
        avisar_fatura(it)
    return it


def email_ler_depois(eid):
    """Ler de novo (ou ler um que não parecia fatura) sem segurar a tela: a IA pode levar um minuto."""
    _email_mudar(eid, estado="lendo", erro="")
    threading.Thread(target=email_ler, args=(eid,), daemon=True).start()


def reler_emails_com_senha():
    """Uma senha nova pode abrir as faturas que esperavam a senha."""
    for it in emails_ler()["itens"]:
        if it["estado"] == "senha":
            email_ler_depois(it["id"])


def email_pdf_b64(eid):
    if not RE_EMAIL_ID.match(str(eid or "")) or not os.path.isfile(_email_pdf(eid)):
        raise ValueError("O PDF desse e-mail não está mais aqui.")
    it = next((x for x in emails_ler()["itens"] if x["id"] == eid), {})
    with open(_email_pdf(eid), "rb") as f:
        return {"b64": "data:application/pdf;base64," + base64.b64encode(f.read()).decode(), "nome": it.get("arquivo") or "fatura.pdf"}


def _resumo_fatura(it):
    lanc = (it.get("resultado") or {}).get("lancamentos") or []
    total = sum(float(x.get("valor") or 0) * (1 if x.get("tipo") == "despesa" else -1) for x in lanc if isinstance(x, dict))
    n = len(lanc) or len((it.get("resultado") or {}).get("investimentos") or [])
    txt = f"{n} {'lançamento' if n == 1 else 'lançamentos'}" if lanc else f"{n} {'investimento' if n == 1 else 'investimentos'}"
    return txt + (f" · {calc.fmt_brl(total)}" if lanc and total > 0 else "")


def avisar_fatura(it):
    """A fatura lida vai para os celulares de quem foi escolhido (Mais › Configurações › Opções)."""
    aj = ler()["ajustes"]
    if aj.get("email_aviso") is not True or not aj.get("email_para"):
        return 0
    try:
        alvos = []
        for pessoa in AVISOS.pessoas():
            if pessoa["id"] in aj["email_para"]:
                alvos += [c for c in pessoa["celulares"] if c not in alvos]
    except Exception as e:  # noqa: BLE001
        log("Aviso de fatura: não consegui ver as pessoas da casa:", e)
        return 0
    texto = avisos.texto_faturas([{"de": emails.nome_remetente(it.get("de")), "resumo": _resumo_fatura(it)}])
    return AVISOS.enviar(alvos, texto, "gerencia-email-" + it["id"], grupo="gerencia-email", canal="Faturas do e-mail") if alvos else 0


def email_simular(c):
    """Só com a IA simulada (testes e prévia): um e-mail com PDF chega como se viesse do Home Assistant."""
    if not IA_MOCK:
        raise ValueError("Só nos testes.")
    try:
        b = base64.b64decode(str(c.get("b64") or "").split(",", 1)[-1], validate=True)
    except (ValueError, TypeError):
        raise ValueError("Arquivo inválido.") from None
    uid = str(len(EMAIL_SIMULADO) + 1)
    EMAIL_SIMULADO[uid] = b
    arquivo = str(c.get("arquivo") or "fatura.pdf")
    ev = {"entry_id": "imap-simulado", "uid": uid, "sender": str(c.get("de") or ""), "subject": str(c.get("assunto") or ""),
          "date": agora_iso(), "parts": {"0": {"content_type": "text/plain"}, "1": {"content_type": "application/pdf", "filename": arquivo}}}
    threading.Thread(target=email_chegou, args=(ev,), daemon=True).start()
    return {"ok": True}


def _email_ligado():
    d = ler()
    return d["ajustes"].get("email") is True and ia_ligada(d)


ESCUTA = emails.Escuta(HA_WS, TOKEN, email_chegou, _email_ligado, log) if TOKEN else None


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
            CONEXAO.publicar(integracao_ligada(d))
            publicar_correria(d)
            dicas_estado(d)  # confere assinaturas novas e, a partir das 8h, os preços mais velhos que a frequência escolhida
            avisar_dicas(d)  # uma dica nova vai para o celular de quem foi escolhido
            publicar_uso_sensor()  # zera na virada do dia e volta depois que o Home Assistant reinicia
        except Exception as e:  # noqa: BLE001
            log("Rotina:", e)
        time.sleep(15 * 60)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    CONEXAO.publicar(integracao_ligada())
    publicar_correria()
    threading.Thread(target=rotina, daemon=True).start()
    if ESCUTA:
        ESCUTA.iniciar()  # faturas por e-mail: só conecta com a opção ligada
    srv = ThreadingHTTPServer(("0.0.0.0", PORTA), Handler)
    log(f"GerencIA {VERSAO} ouvindo na porta {PORTA} (dados em {DATA_DIR})")
    srv.serve_forever()


if __name__ == "__main__":
    main()
