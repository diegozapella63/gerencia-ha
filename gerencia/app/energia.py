"""Conta de luz pelo consumo (1.101.0): o consumo do mês de um medidor de energia do Home Assistant vira o valor de um
fixo (a conta de luz): o que já foi gasto até hoje e a projeção do mês inteiro. Só biblioteca padrão.

A conta: kWh × preço do kWh × (1 + percentual a mais). O preço é o da conta de luz (o total dividido pelos kWh); o
percentual a mais cobre o que o medidor não vê (a iluminação pública, outras cobranças). Quem fala com o Home
Assistant e grava é o server.py.
"""
import calendar
from datetime import datetime

UNIDADES = {"kwh": 1.0, "wh": 0.001, "mwh": 1000.0}


def medidores(estados):
    """Os medidores de energia que somam o consumo: [{id, nome}], pelo nome."""
    out = []
    for s in estados if isinstance(estados, list) else []:
        a = s.get("attributes") if isinstance(s, dict) and isinstance(s.get("attributes"), dict) else {}
        eid = str(s.get("entity_id") or "") if isinstance(s, dict) else ""
        if (eid.startswith("sensor.") and a.get("device_class") == "energy" and a.get("state_class") in ("total_increasing", "total")
                and str(a.get("unit_of_measurement") or "").lower() in UNIDADES):
            out.append({"id": eid, "nome": str(a.get("friendly_name") or eid)[:80]})
    return sorted(out, key=lambda x: x["nome"].lower())[:60]


def pedido(sensor, agora):
    """O comando das estatísticas do Home Assistant: quanto o medidor andou em cada dia, do dia 1 até agora, em kWh."""
    ini = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return {"type": "recorder/statistics_during_period", "start_time": ini.isoformat(), "end_time": agora.isoformat(),
            "statistic_ids": [sensor], "period": "day", "types": ["change"], "units": {"energy": "kWh"}}


def kwh_da_resposta(r, sensor):
    """A soma do que o medidor andou (kWh), ou None sem nenhum dia."""
    linhas = r.get(sensor) if isinstance(r, dict) else None
    ns = [x.get("change") for x in linhas if isinstance(x, dict)] if isinstance(linhas, list) else []
    ns = [float(n) for n in ns if isinstance(n, (int, float)) and not isinstance(n, bool) and n > 0]
    return round(sum(ns), 3) if ns else None


def numero(v, minimo, maximo):
    """Um número escrito como a pessoa escreve («0,95», «20%», «R$ 1,20»); None fora da faixa."""
    if isinstance(v, bool) or v is None:
        return None
    try:
        n = float("".join(c for c in str(v) if c.isdigit() or c in ",.-").replace(",", ".")) if isinstance(v, str) else float(v)
    except ValueError:
        return None
    return n if minimo <= n <= maximo else None


def conta(kwh, preco, extra, agora):
    """{kwh, atual, projetado, dia, dias}: o que já deu até agora e a projeção do mês (o mesmo ritmo até o último dia)."""
    dias = calendar.monthrange(agora.year, agora.month)[1]
    passou = max(1.0, (agora.day - 1) + (agora.hour * 60 + agora.minute) / 1440)
    atual = kwh * preco * (1 + extra / 100)
    return {"kwh": round(kwh, 1), "atual": round(atual, 2), "projetado": round(atual * dias / passou, 2), "dia": agora.day, "dias": dias,
            "kwh_projetado": round(kwh * dias / passou, 1)}


def obs(c):
    """A linha que fica na observação do lançamento do mês."""
    f = lambda v: f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")  # noqa: E731
    k = lambda v: f"{v:.1f}".replace(".", ",")  # noqa: E731
    return f"Energia: {k(c['kwh'])} kWh até o dia {c['dia']} (R$ {f(c['atual'])}) · projeção do mês: {k(c['kwh_projetado'])} kWh (R$ {f(c['projetado'])})"


def agora_local():
    return datetime.now().astimezone()
