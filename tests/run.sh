#!/bin/sh
# Os testes do servidor e da tela (a tela precisa do playwright), como no GitHub.
#   tests/run.sh                    todos
#   tests/run.sh test_calc.py       só os arquivos que casam com o padrão (ex.: "test_tela_*.py")
# Os visuais ficam em tests/e2e/run.sh; a cobertura, em tools/cobertura.py.
cd "$(dirname "$0")/.." || exit 1
exec python3 -m unittest discover -s tests -t . -p "${1:-test_*.py}"
