"""Quanto do código do app (gerencia/app/*.py) os testes unitários percorrem, sem instalar nada.
Uso: python3 tools/cobertura.py [--faltando arquivo.py | --faltando app.js]
Conta também o server.py que os testes HTTP sobem em outro processo (tests/base.py: Servidor), pela variável
GERENCIA_COBERTURA: cada processo grava as linhas que percorreu numa pasta, e a conta junta tudo.
A tela (gerencia/app/www/app.js) é medida nos testes da tela pelo Profiler do Chromium (tests/tela_base.py)."""
import json
import os
import signal
import sys
import tempfile
import threading
import types
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "gerencia", "app")
vistos = {}


def rastro(frame, evento, arg):
    f = frame.f_code.co_filename
    if not f.startswith(APP):
        return None
    if evento == "line":
        vistos.setdefault(f, set()).add(frame.f_lineno)
    return rastro


def linhas_executaveis(caminho):
    codigo = compile(open(caminho, encoding="utf-8").read(), caminho, "exec")
    linhas, pilha = set(), [codigo]
    while pilha:
        c = pilha.pop()
        linhas.update(l for _, _, l in c.co_lines() if l)
        pilha.extend(x for x in c.co_consts if isinstance(x, types.CodeType))
    return linhas


def gravar(pasta):
    with open(os.path.join(pasta, f"{os.getpid()}.json"), "w") as f:
        json.dump({k: sorted(v) for k, v in vistos.items()}, f)


if "--filho" in sys.argv:
    # python3 cobertura.py --filho <pasta> server.py: roda o servidor contando as linhas; ao ser parado, grava
    import runpy
    i = sys.argv.index("--filho")
    pasta, alvo = sys.argv[i + 1], sys.argv[i + 2]

    def parar(*_):
        gravar(pasta)
        os._exit(0)

    signal.signal(signal.SIGTERM, parar)
    threading.settrace(rastro)
    sys.settrace(rastro)
    sys.argv = [alvo]
    sys.path.insert(0, os.path.dirname(alvo))
    runpy.run_path(alvo, run_name="__main__")
    sys.exit(0)

sys.path.insert(0, RAIZ)
pasta = tempfile.mkdtemp(prefix="cobertura-")
os.environ["GERENCIA_COBERTURA"] = pasta
threading.settrace(rastro)
sys.settrace(rastro)
suite = unittest.defaultTestLoader.discover(os.path.join(RAIZ, "tests"), top_level_dir=RAIZ)
r = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w")).run(suite)
sys.settrace(None)
threading.settrace(None)
for nome in os.listdir(pasta):
    for k, v in json.load(open(os.path.join(pasta, nome))).items():
        vistos.setdefault(k, set()).update(v)
print(f"{r.testsRun} testes, {len(r.failures) + len(r.errors)} com problema")

faltando = sys.argv[sys.argv.index("--faltando") + 1] if "--faltando" in sys.argv else None
tot_e = tot_v = 0
for nome in sorted(os.listdir(APP)):
    if not nome.endswith(".py"):
        continue
    p = os.path.join(APP, nome)
    e = linhas_executaveis(p)
    v = vistos.get(p, set()) & e
    tot_e += len(e)
    tot_v += len(v)
    print(f"{nome:18} {100 * len(v) / max(1, len(e)):5.1f}%  ({len(v)}/{len(e)} linhas)")
    if faltando == nome:
        falta = sorted(e - v)
        blocos, ini = [], None
        for i, l in enumerate(falta):
            if ini is None:
                ini = l
            if i + 1 == len(falta) or falta[i + 1] != l + 1:
                blocos.append(f"{ini}-{l}" if l != ini else str(ini))
                ini = None
        print("   faltando:", " ".join(blocos))
print(f"{'total':18} {100 * tot_v / max(1, tot_e):5.1f}%")

# a tela: o app.js nos testes da tela (pelo Profiler do Chromium; ver tests/tela_base.py)
try:
    from tests import tela_base
    js = tela_base.relatorio_cobertura_js()
except Exception as e:  # noqa: BLE001
    js = None
    print("app.js: não deu para medir (" + str(e) + ")")
if js and js["linhas"]:
    print(f"\n{'www/app.js':18} {100 * js['linhas_ok'] / js['linhas']:5.1f}%  ({js['linhas_ok']}/{js['linhas']} linhas, "
          f"{js['funcoes_ok']}/{js['funcoes']} funções = {100 * js['funcoes_ok'] / max(1, js['funcoes']):.1f}%)")
    if faltando == "app.js":
        falta, blocos, ini = js["faltando"], [], None
        for i, l in enumerate(falta):
            ini = l if ini is None else ini
            if i + 1 == len(falta) or falta[i + 1] != l + 1:
                blocos.append(f"{ini}-{l}" if l != ini else str(ini))
                ini = None
        print("   faltando:", " ".join(blocos))
