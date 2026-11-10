"""Sobe a versão do GerencIA nos três lugares de uma vez (config.yaml, server.py e app.js), para não ficar nenhum para trás.

  python3 tools/versao.py            mostra a versão de cada lugar
  python3 tools/versao.py 1.50.0     grava 1.50.0 nos três
  python3 tools/versao.py patch      1.49.0 → 1.49.1 (correção)
  python3 tools/versao.py minor      1.49.3 → 1.50.0 (novidade)

A versão fica escrita nos três porque cada um é lido sozinho: o config.yaml pelo Home Assistant, o server.py dentro da
imagem (que só leva a pasta app/) e o app.js direto do arquivo nos testes da tela e na prévia. O tests/test_versao.py
confere que os três e o topo do CHANGELOG.md estão iguais."""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUGARES = (
    (os.path.join("gerencia", "config.yaml"), r'^(version: ")([^"]+)(")'),
    (os.path.join("gerencia", "app", "server.py"), r'^(VERSAO = ")([^"]+)(")'),
    (os.path.join("gerencia", "app", "www", "app.js"), r"^(const VERSAO = ')([^']+)(';)"),
)
VERSAO_RE = re.compile(r"^\d+\.\d+\.\d+$")


def ler(raiz=RAIZ):
    """{arquivo: versão} de cada lugar (None se não achou)."""
    out = {}
    for rel, padrao in LUGARES:
        with open(os.path.join(raiz, rel), encoding="utf-8") as f:
            m = re.search(padrao, f.read(), re.M)
        out[rel] = m.group(2) if m else None
    return out


def seguinte(atual, tipo):
    a, b, c = (int(x) for x in atual.split("."))
    return f"{a}.{b}.{c + 1}" if tipo == "patch" else f"{a}.{b + 1}.0"


def gravar(nova, raiz=RAIZ):
    if not VERSAO_RE.match(nova):
        raise ValueError(f"versão inválida: {nova} (use 1.2.3)")
    for rel, padrao in LUGARES:
        caminho = os.path.join(raiz, rel)
        with open(caminho, encoding="utf-8") as f:
            texto = f.read()
        texto, n = re.subn(padrao, lambda m: m.group(1) + nova + m.group(3), texto, count=1, flags=re.M)
        if n != 1:
            raise ValueError(f"não achei a versão em {rel}")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(texto)


def main(args):
    atuais = ler()
    if not args:
        for rel, v in atuais.items():
            print(f"{v or '?':10} {rel}")
        return 0 if len(set(atuais.values())) == 1 else 1
    vs = set(atuais.values())
    if len(vs) != 1 and args[0] in ("patch", "minor"):
        print("As versões não estão iguais; diga a nova versão inteira (ex.: 1.50.0).")
        return 1
    nova = seguinte(vs.pop(), args[0]) if args[0] in ("patch", "minor") else args[0]
    gravar(nova)
    print(f"{nova} em {', '.join(rel for rel, _ in LUGARES)}. Falta a seção dela no topo do gerencia/CHANGELOG.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
