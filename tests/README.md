# Testes do GerencIA

Duas camadas, rodando a cada push no GitHub (aba Actions):

| Camada | Onde | Como rodar | O que confere |
|---|---|---|---|
| Unitários e servidor | `tests/test_*.py` | `python3 -m unittest discover -s tests -t .` | cada parte do app (`calc.py`, `bens.py`, `voz.py`, `integracao.py`, `assinaturas.py`, `server.py`) e o servidor de verdade pelo HTTP, com a IA e a fala simuladas |
| Visuais | `tests/e2e/*.py` | `tests/e2e/run.sh` (ou `tests/e2e/run.sh fluxo2 bens_e2e`) | as telas no Chromium (Playwright): clica, digita, confere o que aparece e grava capturas |

Os unitários usam só a biblioteca padrão do Python (uns 20 segundos). Os visuais precisam de `pip install playwright && playwright install chromium`, das portas 8099 (GerencIA) e 8098 (InventarIA, para os testes de bens, a partir de `../inventario-ha`) e falham se aparecer erro na página: cada script termina com a linha `ERROS [...]`, que precisa estar vazia. As capturas ficam em `$E2E_TMP/shots`.

## Peças que ajudam (`tests/base.py`)

- `Servidor()`: sobe o `server.py` num processo, numa porta livre, com pastas temporárias, a IA e a fala simuladas e o Banco Central desligado; `get`, `post`, `put` devolvem `(status, cabeçalhos, corpo)`.
- `importar_servidor()`: importa o `server.py` com as mesmas pastas temporárias, para testar as funções direto.
- `ServidorFalso(rotas)`: um servidor HTTP de mentira (o InventarIA, o Home Assistant) que guarda os pedidos.
- `WSFalso(responder)`: a API WebSocket do Home Assistant, só o bastante para o `voz.py`.

## Variáveis do servidor para testar

`GERENCIA_DEV=1` (aceita qualquer endereço), `GERENCIA_IA_MOCK=1` (IA e fala simuladas), `GERENCIA_FONTES_MOCK=<pasta>` (páginas de preço das assinaturas, ver `tests/e2e/fixtures/fontes`), `GERENCIA_DOLAR=5.04`, `GERENCIA_BCB=<url>` (Banco Central), `GERENCIA_DATA`, `GERENCIA_SHARE`, `GERENCIA_MEDIA`, `GERENCIA_INVENTARIO` (o integracao.json do InventarIA), `GERENCIA_URL_INTERNA` e `GERENCIA_PORTA`.

Dados de exemplo sempre inventados: nada de nomes, bancos ou valores reais de ninguém.
