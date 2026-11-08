# Testes do GerencIA

Três camadas, rodando a cada push no GitHub (aba Actions):

| Camada | Onde | Como rodar | O que confere |
|---|---|---|---|
| Unitários e servidor | `tests/test_*.py` (fora `test_tela*`) | `python3 -m unittest discover -s tests -t .` | cada parte do servidor (`calc.py`, `bens.py`, `voz.py`, `integracao.py`, `ferramentas.py`, `assinaturas.py`, `oportunidades.py`, `pdf.py`, `pdfsenha.py`, `emails.py`, `server.py`), funções e rotas HTTP, com a IA, a fala, o Banco Central e o Home Assistant de mentira |
| Tela | `tests/test_tela*.py` | o mesmo comando (precisa do playwright) | o `app.js` de verdade num Chromium, sem servidor: os cálculos um a um (iguais ao `calc.py`) e o que a pessoa faz em cada área: caixa, investimentos, aplicar/transferir/gráficos, IA/câmera/fala, início/mais/navegação, chat e sistema (o caminho do servidor com um fetch falso, o microfone de verdade do Chromium, arrastar, tema, opções) |
| Visuais | `tests/e2e/*.py` | `tests/e2e/run.sh` (ou `tests/e2e/run.sh fluxo2 bens_e2e`) | o app inteiro com o servidor de verdade: clica, digita, confere e grava capturas |

O GitHub instala o Chromium, o `qpdf` e o `pdftotext` e falha se algum teste for pulado. No computador: `pip install playwright && playwright install chromium` (sem ele, os testes da tela são pulados) e `apt install qpdf poppler-utils` (sem eles, os testes que abrem o PDF num leitor de verdade são pulados). As faturas com senha de `tests/fixtures/pdf_senha` são inventadas (ver o LEIAME de lá).

## Testes da tela (`tests/tela_base.py`)

A página abre por `file://` com `window.GERENCIA_DEMO = true` (a prévia: os dados ficam na memória) e `window.GERENCIA_TESTE = true`. Com isso, o `app.js` entrega qualquer função ou variável de dentro pelo nome: `T.totais(...)`, `T.S` (estado da tela), `T.LF` (formulário aberto), `T.api` (dá para trocar uma função por uma falsa). Fora dos testes isso não existe.

O relógio fica parado em 02/11/2026 10:00 (São Paulo) e a tela tem 390 px. A classe `Tela` tem os ajudantes: `abrir(dados)` (grava os dados e abre na tela Início), `ir("caixa")`, `clicar`, `digitar` (dinheiro entra em centavos: 5990 = 59,90), `preencher`, `texto`, `folha()` (título da janela de cima), `niveis()`, `voltar()` (o Voltar do celular), `dados()`, `aviso()` e `js("expressão com T")`. Cada teste começa com `abrir(...)` com só os dados de que precisa.

## Visuais (`tests/e2e`)

Cada script confere com `tests/e2e/_confere.py` (`igual`, `tem`, `sim`, `perto`, `valores`...): cada verificação imprime `ok ...` ou `FALHOU ...`. O `run.sh` dá o script como falho se aparecer `FALHOU`, uma exceção ou erro de JavaScript (linha `ERROS [...]` não vazia), e mostra quantas verificações passaram. Usa as portas 8099 (GerencIA) e 8098 (InventarIA, para os testes de bens, a partir de `../inventario-ha`): não rode duas baterias ao mesmo tempo. As capturas ficam em `$E2E_TMP/shots`. Valores que dependem do dia (juros, datas) são conferidos por relação (antes + aporte = depois) ou calculados a partir de hoje.

## Peças que ajudam (`tests/base.py`)

- `Servidor()`: sobe o `server.py` num processo, numa porta livre, com pastas temporárias, a IA e a fala simuladas e o Banco Central desligado; `get`, `post`, `put` devolvem `(status, cabeçalhos, corpo)`.
- `importar_servidor()`: importa o `server.py` com as mesmas pastas temporárias, para testar as funções direto.
- `ServidorFalso(rotas)`: um servidor HTTP de mentira (o InventarIA, o Home Assistant, o Banco Central, a página de preços) que guarda os pedidos.
- `WSFalso(responder)`: a API WebSocket do Home Assistant, só o bastante para o `voz.py` e a escuta dos e-mails (`emails.Escuta`).

## Cobertura

`python3 tools/cobertura.py` roda os testes e mostra quanto de cada arquivo do servidor foi percorrido (inclusive o `server.py` que os testes HTTP sobem em outro processo) e do `app.js` nos testes da tela (pelo Profiler do Chromium: linhas e funções); `--faltando server.py` ou `--faltando app.js` lista as linhas que nenhum teste passou. Só biblioteca padrão (e o playwright, para a tela). Os testes visuais não entram nessa conta (Aplicar, Transferir e a conversa com o servidor de verdade estão neles).

## Variáveis do servidor para testar

`GERENCIA_DEV=1` (aceita qualquer endereço), `GERENCIA_IA_MOCK=1` (IA e fala simuladas), `GERENCIA_FONTES_MOCK=<pasta>` (páginas de preço das assinaturas, ver `tests/e2e/fixtures/fontes`), `GERENCIA_DOLAR=5.04`, `GERENCIA_BCB=<url>` (Banco Central), `GERENCIA_TESOURO=<url>` e `GERENCIA_TESOURO_DADOS=<url>` (o Tesouro Direto: a tabela Investir e os dados abertos; nos testes, um endereço que não responde ou `tests/e2e/fixtures/tesouro-investir.csv`), `GERENCIA_DATA`, `GERENCIA_SHARE`, `GERENCIA_MEDIA`, `GERENCIA_INVENTARIO` (o integracao.json do InventarIA), `GERENCIA_URL_INTERNA` e `GERENCIA_PORTA`.

Dados de exemplo e de testes sempre inventados: nada de nomes, bancos ou valores reais de ninguém.
