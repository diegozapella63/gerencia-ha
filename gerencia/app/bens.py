"""Bens da casa, do InventarIA: o valor de cada item, depreciado por categoria desde a data do valor.

O InventarIA grava share/inventario/integracao.json com o endereço dele na rede interna dos apps e uma chave
(o mesmo que o ResolvIA usa). Daqui só se lê /api/integracao/itens e /api/integracao/comodos; nada muda lá.
Só biblioteca padrão do Python.
"""
import json
import os
import threading
import time
import urllib.request
from datetime import date

ARQ = os.environ.get("GERENCIA_INVENTARIO", "/share/inventario/integracao.json")
CACHE_S = 10 * 60

# perda de valor por ano, em %, por categoria do InventarIA (dá para mudar em Mais › Invest)
TAXAS_PADRAO = {
    "imoveis": 0, "veiculos": 15, "eletronicos": 20, "moveis": 10, "decoracao": 5, "colecao": 0, "cozinha": 10, "texteis": 15, "plantas": 0,
    "livros": 5, "pets": 15, "saude": 10, "vestuario": 25, "utilidades": 10, "outros": 10,
}
NOMES_PADRAO = {
    "imoveis": "Imóveis", "veiculos": "Veículos", "eletronicos": "Eletrônicos", "moveis": "Móveis", "decoracao": "Decoração e arte", "colecao": "Colecionáveis",
    "cozinha": "Cozinha e bar", "texteis": "Tapetes e têxteis", "plantas": "Plantas", "livros": "Livros e jogos",
    "pets": "Pets", "saude": "Saúde", "vestuario": "Roupas e calçados", "utilidades": "Utilidades", "outros": "Outros",
}


class ErroBens(Exception):
    pass


class Bens:
    def __init__(self, log):
        self.log = log
        self.cache = None  # (quando, dados)
        self.trava = threading.Lock()

    def conexao(self):
        try:
            with open(ARQ, encoding="utf-8") as f:
                c = json.load(f)
        except (OSError, ValueError):
            return None
        return c if isinstance(c, dict) and c.get("chave") and (c.get("url") or c.get("ip_url")) else None

    def _get(self, c, caminho):
        erro = None
        for base in [x for x in (c.get("url"), c.get("ip_url")) if x]:
            req = urllib.request.Request(base.rstrip("/") + caminho, headers={"Authorization": f"Bearer {c['chave']}", "X-App": "GerencIA"})
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    return json.loads(r.read() or b"{}")
            except Exception as e:  # noqa: BLE001  (tenta o outro endereço)
                erro = e
        raise ErroBens(f"O InventarIA não respondeu ({erro}).")

    def ler(self, forcar=False, guardar=True):
        """{"itens": [...], "comodos": {id: nome}, "categorias": {id: nome}, "versao", "lido_em"}; erro vira ErroBens.
        guardar=False (os aparelhos das promoções, 1.64.1): lê sem trocar o que os Bens da casa guardaram."""
        with self.trava:
            if not forcar and self.cache and time.time() - self.cache[0] < CACHE_S:
                return self.cache[1]
            c = self.conexao()
            if not c:
                raise ErroBens("O InventarIA não foi encontrado. Ele precisa estar instalado e aberto uma vez (versão 1.16.0 ou mais nova).")
            itens = self._get(c, "/api/integracao/itens")
            lista = itens.get("itens") or []
            if lista and "valor" not in lista[0]:
                raise ErroBens("Atualize o InventarIA para a versão 1.16.0 ou mais nova: a versão instalada não envia os valores.")
            try:
                comodos = {x.get("id"): x.get("nome") or "" for x in (self._get(c, "/api/integracao/comodos").get("comodos") or [])}
            except ErroBens:
                comodos = {}
            # as categorias da casa vêm do InventarIA (lá dá para renomear, criar e excluir); sem elas, as de costume
            dados = {"itens": lista, "comodos": comodos, "categorias": dict(itens.get("categorias") or NOMES_PADRAO),
                     "versao": itens.get("versao") or c.get("versao") or "", "lido_em": time.strftime("%Y-%m-%dT%H:%M:%S")}
            if guardar:
                self.cache = (time.time(), dados)
            return dados


def taxas(ajustes):
    t = dict(TAXAS_PADRAO)
    for k, v in ((ajustes or {}).get("bens_taxas") or {}).items():
        try:
            t[k] = max(-50.0, min(100.0, float(v)))  # negativa: valoriza (um imóvel, por exemplo)
        except (TypeError, ValueError):
            pass
    return t


def valor_hoje(valor, valor_em, taxa, hoje=None):
    """Perde a taxa por ano, composta, desde a data do valor."""
    try:
        d0 = date.fromisoformat(str(valor_em)[:10])
    except ValueError:
        return valor
    anos = max(0, ((hoje or date.today()) - d0).days) / 365.25
    return valor * (1 - taxa / 100) ** anos


def itens_hoje(dados, ajustes, hoje=None):
    """Todos os itens com valor, já com o valor de hoje, a taxa da categoria (negativa: valoriza) e os nomes da
    categoria e do cômodo, do maior para o menor (para o Relatório de patrimônio)."""
    tx = taxas(ajustes)
    lista = []
    for it in dados.get("itens") or []:
        try:
            v = float(it.get("valor") or 0)
        except (TypeError, ValueError):
            continue
        if v <= 0:
            continue
        cat = it.get("categoria") or "outros"
        cm = it.get("comodo") or ""
        lista.append({"nome": it.get("nome") or "", "categoria": cat, "categoria_nome": (dados.get("categorias") or {}).get(cat, cat),
                      "comodo": cm, "comodo_nome": (dados.get("comodos") or {}).get(cm) or "", "valor": v,
                      "valor_em": it.get("valor_em") or "", "taxa": tx.get(cat, 10), "hoje": valor_hoje(v, it.get("valor_em"), tx.get(cat, 10), hoje)})
    return sorted(lista, key=lambda x: -x["hoje"])


def resumo(dados, ajustes, hoje=None):
    """Totais para a tela e os sensores: hoje (depreciado), registrado, perde por ano, por categoria e por cômodo."""
    tx = taxas(ajustes)
    cats, coms, itens = {}, {}, []
    tot_hoje = tot_reg = perde = 0.0
    for it in dados.get("itens") or []:
        v = float(it.get("valor") or 0)
        if v <= 0:
            continue
        cat = it.get("categoria") or "outros"
        h = valor_hoje(v, it.get("valor_em"), tx.get(cat, 10), hoje)
        tot_hoje += h
        tot_reg += v
        perde += h * tx.get(cat, 10) / 100
        c = cats.setdefault(cat, {"id": cat, "nome": dados["categorias"].get(cat, cat), "taxa": tx.get(cat, 10), "hoje": 0.0, "registrado": 0.0, "n": 0})
        c["hoje"] += h
        c["registrado"] += v
        c["n"] += 1
        cm = it.get("comodo") or ""
        k = coms.setdefault(cm, {"id": cm, "nome": dados["comodos"].get(cm) or "Sem cômodo", "hoje": 0.0, "n": 0})
        k["hoje"] += h
        k["n"] += 1
        itens.append({"nome": it.get("nome") or "", "categoria": cat, "comodo": cm, "valor": round(v, 2), "valor_em": it.get("valor_em") or "", "hoje": round(h, 2)})
    arred = lambda xs: sorted(({**x, "hoje": round(x["hoje"], 2), **({"registrado": round(x["registrado"], 2)} if "registrado" in x else {})} for x in xs), key=lambda x: -x["hoje"])
    return {"ok": True, "hoje": round(tot_hoje, 2), "registrado": round(tot_reg, 2), "perde_ano": round(perde, 2), "n": len(itens),
            "categorias": arred(cats.values()), "comodos": arred(coms.values()),
            # todas as categorias do InventarIA, na ordem de lá, para o tipo Bens do GerencIA usar as mesmas
            "todas": [{"id": k, "nome": n, "taxa": tx.get(k, 10)} for k, n in (dados.get("categorias") or {}).items()],
            "maiores": sorted(itens, key=lambda x: -x["hoje"])[:10], "versao": dados.get("versao"), "lido_em": dados.get("lido_em")}
