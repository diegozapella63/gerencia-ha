#!/usr/bin/env bash
# Testes visuais do GerencIA: cada script abre o app no Chromium (Playwright), clica, confere e grava capturas.
# Para cada um, este script sobe o servidor com dados limpos, a IA e a fala simuladas, as páginas de preço de
# exemplo (fixtures/fontes) e o dólar fixo; os testes de bens sobem também o InventarIA (../inventario-ha).
#
#   tests/e2e/run.sh                 todos
#   tests/e2e/run.sh fluxo2 bens_e2e  só esses
#
# Precisa de python3 e playwright (pip install playwright; playwright install chromium).
# Usa as portas 8099 (GerencIA) e 8098 (InventarIA): não rode duas baterias ao mesmo tempo.
# Um teste falha se o script der erro, se aparecer "Traceback", se a linha "ERROS [...]" (erros do JavaScript) não
# estiver vazia ou se uma verificação imprimir "FALHOU ..." (_confere.py: igual, tem, sim...).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
export E2E_INVENTARIA="${E2E_INVENTARIA:-$(dirname "$ROOT")/inventario-ha}"
export E2E_TMP="${E2E_TMP:-$(mktemp -d)}"
export TZ="${TZ:-America/Sao_Paulo}"
mkdir -p "$E2E_TMP/shots" "$E2E_TMP/logs"
cp "$HERE"/fixtures/*.jpg "$HERE"/fixtures/*.pdf "$E2E_TMP/"
PIDS=()
parar() { for p in "${PIDS[@]:-}"; do [ -n "$p" ] && kill "$p" 2>/dev/null; done; PIDS=(); sleep 0.3; }
trap parar EXIT
esperar() { for _ in $(seq 1 100); do curl -s -o /dev/null "$1" && return 0; sleep 0.05; done; return 1; }

if [ $# -gt 0 ]; then names=("$@"); else names=($(cd "$HERE" && ls *.py | grep -v '^_' | sed 's/\.py$//' | sort)); fi
pass=0; fail=0; skip=0; bad=()
for t in "${names[@]}"; do
  f="$HERE/$t.py"
  [ -f "$f" ] || { echo "?? $t (não existe)"; bad+=("$t"); fail=$((fail+1)); continue; }
  # sobe o InventarIA para quem fala com ele (a porta 8098 ou as rotas dele), não para quem só cita o nome (o Sobre)
  inv=0; grep -q "integracao/itens\|8098" "$f" && inv=1
  if [ $inv = 1 ] && [ ! -d "$E2E_INVENTARIA" ]; then echo "-- $t (pulado: falta o inventario-ha)"; skip=$((skip+1)); continue; fi
  parar
  D="$E2E_TMP/run-$t"; rm -rf "$D"; mkdir -p "$D/data" "$D/share/gerencia" "$D/share/inventario" "$D/inv" "$D/media"
  if [ $inv = 1 ]; then
    (cd "$E2E_INVENTARIA/inventario/app" && INV_DEV=1 INV_DATA="$D/inv" INV_SEED=../seed INV_WEB=web INV_SHARE="$D/share/inventario" INV_MEDIA="$D/media" \
      INV_PORT=8098 INV_URL_INTERNA=http://127.0.0.1:8098 exec python3 server.py > "$D/inv.log" 2>&1) &
    PIDS+=($!)
    esperar http://127.0.0.1:8098/ || echo "   (o InventarIA demorou para subir)"
  fi
  (cd "$ROOT/gerencia/app" && GERENCIA_DEV=1 GERENCIA_DATA="$D/data" GERENCIA_SHARE="$D/share/gerencia" GERENCIA_MEDIA="$D/media" GERENCIA_IA_MOCK=1 \
    GERENCIA_FONTES_MOCK="$HERE/fixtures/fontes" GERENCIA_DOLAR=5.04 GERENCIA_BCB="http://127.0.0.1:9/{s}" \
    GERENCIA_TESOURO="file://$HERE/fixtures/tesouro-investir.csv" GERENCIA_TESOURO_DADOS="http://127.0.0.1:9/dados.csv" GERENCIA_PROMOS_BASE="http://127.0.0.1:9/promo/" \
    GERENCIA_INVENTARIO="$D/share/inventario/integracao.json" exec python3 server.py > "$D/server.log" 2>&1) &
  PIDS+=($!)
  esperar http://127.0.0.1:8099/api/rev || echo "   (o GerencIA demorou para subir)"
  (cd "$E2E_TMP" && timeout 400 python3 -u "$f" "$E2E_TMP") > "$E2E_TMP/logs/$t.txt" 2>&1
  code=$?
  erros=$(grep -h "^ERROS " "$E2E_TMP/logs/$t.txt" | grep -v "^ERROS \[\]$")
  if [ $code -ne 0 ] || grep -q "Traceback\|^FALHOU" "$E2E_TMP/logs/$t.txt" || [ -n "$erros" ]; then
    echo "XX $t"; (grep -h "Error\|^ERROS \[.\|^FALHOU" "$E2E_TMP/logs/$t.txt" | head -5 | sed 's/^/     /')
    bad+=("$t"); fail=$((fail+1))
  else
    echo "ok $t ($(grep -c '^ok ' "$E2E_TMP/logs/$t.txt") verificações)"; pass=$((pass+1))
  fi
done
parar
echo
echo "$pass ok, $fail com falha, $skip pulados · capturas e saídas em $E2E_TMP"
[ $fail -eq 0 ] || { echo "Falharam: ${bad[*]}"; exit 1; }
