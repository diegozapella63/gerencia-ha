"""Verificações dos testes visuais. Cada uma imprime "ok <o quê>" ou "FALHOU <o quê>: <detalhe>";
o run.sh dá o teste como falho se aparecer qualquer linha FALHOU (o script segue até o fim, para as capturas)."""
import json
import re
from datetime import date

falhas = []


def _saida(ok, o_que, detalhe=""):
    if ok:
        print("ok", o_que)
    else:
        falhas.append(o_que)
        print("FALHOU", o_que + (": " + detalhe if detalhe else ""))
    return ok


def igual(obtido, esperado, o_que):
    return _saida(obtido == esperado, o_que, f"veio {obtido!r}, esperado {esperado!r}")


def tem(texto, trecho, o_que):
    return _saida(trecho in (texto or ""), o_que, f"{trecho!r} não está em {str(texto)[:160]!r}")


def sem(texto, trecho, o_que):
    return _saida(trecho not in (texto or ""), o_que, f"{trecho!r} está em {str(texto)[:160]!r}")


def sim(cond, o_que, detalhe=""):
    return _saida(bool(cond), o_que, str(detalhe))


def estado(pg):
    """Os dados que o servidor tem agora."""
    return json.loads(pg.evaluate("fetch('api/state').then(r=>r.text())"))


def mes(delta=0, hoje=None):
    """AAAA-MM de daqui a delta meses."""
    h = hoje or date.today()
    m = h.year * 12 + h.month - 1 + delta
    return f"{m // 12:04d}-{m % 12 + 1:02d}"


def valores(texto):
    """Os valores em reais de um texto, na ordem ("R$ 1.234,56 → R$ 2.000" -> [1234.56, 2000.0])."""
    return [float(x.replace(".", "").replace(",", ".")) for x in re.findall(r"R\$\s*(\d[\d.]*(?:,\d{1,2})?)", texto or "")]


def perto(a, b, o_que, tol=0.011):
    return _saida(a is not None and b is not None and abs(a - b) <= tol, o_que, f"veio {a!r}, esperado {b!r}")
