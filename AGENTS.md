# Instruções para quem for mexer neste repositório (pessoas ou IAs)

GerencIA é um app (add-on) do Home Assistant para as finanças da casa: caixa (recebimentos, despesas, fixos, cartões e faturas), investimentos com projeção, patrimônio, bens do InventarIA e leitura por IA (fatura, print, foto, mensagem ou fala). Faz parte de uma família de apps do mesmo dono, que conversam entre si pelo Home Assistant:

| App | Repositório | O que é |
|---|---|---|
| GerencIA | `diegozapella63/gerencia-ha` (este) | finanças: caixa, investimentos, contas a pagar |
| CronologIA | `diegozapella63/cronologia-ha` | calendário, rotinas, remédios, placar (mostra as contas daqui) |
| ResolvIA | `diegozapella63/resolvia-ha` | listas de tarefas, pontos, repetição |
| InventarIA | `diegozapella63/inventario-ha` | inventário da casa: cômodos e itens com valor (vira "Bens da casa" aqui) |

O Home Assistant instala direto do GitHub (`repository.yaml` + `gerencia/config.yaml`), a partir da branch `main`: o que está em `main` é o que os usuários recebem.

## Estrutura

```
gerencia/config.yaml          versão e opções do app
gerencia/CHANGELOG.md         o que mudou em cada versão (o HA mostra ao atualizar)
gerencia/DOCS.md              manual do usuário (aba Documentação no HA)
gerencia/app/server.py        servidor HTTP (Python, só biblioteca padrão): rotas /api/*, dados, versões, IA, sensores
gerencia/app/calc.py          cálculos (taxas, valor de hoje, totais, caixa, cartão e fatura); espelho do app.js
gerencia/app/integracao.py    conexão com o CronologIA (contas a pagar, pagar, desfazer, nova)
gerencia/app/bens.py          bens do InventarIA, depreciados por categoria
gerencia/app/voz.py           Falar: fala para texto do Home Assistant (WebSocket feito à mão)
gerencia/app/assinaturas.py   dicas de economia com preços conferidos na página oficial
gerencia/app/chat.py          Conversar com a IA: resumo dos dados para a IA, ações propostas (lançar, pagar, saldo) e a conversa guardada
gerencia/app/pdf.py           PDF feito à mão (Helvetica, A4) para o Baixar PDF do Relatório de patrimônio
gerencia/app/www/             a tela: index.html, app.js (JavaScript puro, sem build), styles.css, fontes
tools/montar_previa.py        gera preview/gerencia-previa.html (o app num arquivo só, com dados de exemplo)
tests/                        testes (ver tests/README.md)
docs/                         capturas de tela do README
```

Os dados ficam em `/data/gerencia.json` (com `rev`: um PUT com revisão velha recebe 409 e o estado atual), versões automáticas em `/data/versoes` (as 3 últimas), imagens dos investimentos em `/data/fotos`, a conversa com a IA em `/data/chat.json` (as últimas 60 mensagens; fora do backup) e backups em `/share/gerencia`.

## Rodar no computador

```
cd gerencia/app
GERENCIA_DEV=1 GERENCIA_IA_MOCK=1 GERENCIA_DATA=/tmp/g/data GERENCIA_SHARE=/tmp/g/share GERENCIA_MEDIA=/tmp/g/media python3 server.py
```

Abra `http://localhost:8099`. Em **Carregar exemplo** aparecem dados inventados. A prévia sem servidor: `python3 tools/montar_previa.py` e abra `preview/gerencia-previa.html`.

## Checklist de toda mudança

1. Implementar. Servidor: só biblioteca padrão do Python. Tela: `gerencia/app/www/app.js` (um IIFE; ações por `data-a`, janelas de baixo com `abrirFolha`/`pintarFolha`/`fecharFolha`, gravação com `persistir`). Cálculo novo vale nos dois lados (`calc.py` e `app.js`).
2. Testar: `python3 -m unittest discover -s tests -t .` (servidor e tela; a tela precisa do playwright) e os visuais ligados à mudança (`tests/e2e/run.sh nome ...`). Toda mudança ou bug corrigido vem com o teste dele: na tela, em `tests/test_tela_<área>.py` (ver `tests/README.md`); no servidor, no `tests/test_*.py` da parte; num visual, com verificações do `_confere.py`.
3. Subir a versão nos três lugares (iguais): `gerencia/config.yaml` (`version:`), `gerencia/app/server.py` (`VERSAO`) e `gerencia/app/www/app.js` (`const VERSAO`). Correção = patch (1.23.0 → 1.23.1); novidade = minor (1.23.x → 1.24.0).
4. `gerencia/CHANGELOG.md`: nova seção no topo, em português, do ponto de vista de quem usa (o que mudou na tela, não no código).
5. `gerencia/DOCS.md` quando muda o comportamento ou aparece algo novo.
6. `python3 tools/montar_previa.py` e commit também de `preview/gerencia-previa.html`.
7. Commit em `main` com mensagem em português ("GerencIA 1.24.0: ..."), `git pull --rebase` e push. O GitHub roda todos os testes a cada push (aba Actions).

## Como os apps conversam

Pela pasta `/share` do Home Assistant. Mudar um formato aqui exige mudar o outro app junto.

- **GerencIA → CronologIA**: este app grava `share/gerencia/integracao.json` (`url`, `ip_url`, `chave`) e responde em `/api/integracao/contas`, `/pagar`, `/desfazer` e `/nova` com `Authorization: Bearer <chave>` (`integracao.py`). Desligado em **Mais › Configurações › Integrações**, o arquivo some e as rotas respondem 401. Um fixo do mês tem sempre o id `v:<fixo>:<AAAA-MM>`, lançado ou não; uma fatura, `f:<conta>|<vencimento>`.
- **InventarIA → GerencIA**: o InventarIA grava `share/inventario/integracao.json` e este app lê `/api/integracao/itens` e `/comodos` (`bens.py`, cache de 10 min). Só lê; nada muda lá. Patrimônio = investimentos meus + bens (os de terceiros ficam fora).
- **Home Assistant**: IA pela ação `ai_task.generate_data` para a leitura, as dicas e o chat (anexos em `/media/gerencia/ia-temp`, apagados depois; no chat a IA devolve `{resposta, lancamentos, pagar, investimentos}` e a tela confirma cada ação com as funções da leitura por IA e do Pagar), fala para texto (`voz.py`), sensores opcionais e índices do Banco Central (CDI, Selic, IPCA, TR) a cada 12 h.

## Como o dono gosta (interface)

- Tudo em português do Brasil, sem palavras em inglês na tela.
- **Menos é mais**: textos curtos, sem explicar o óbvio, sem avisos repetidos.
- Botões lado a lado com o mesmo tamanho e alinhados; números nunca cortados nem por cima uns dos outros (`ajustarTextos` diminui a fonte quando não cabe).
- **Mais** é um menu, não uma tela de ajustes (como no InventarIA): cada função tem a sua linha e a sua tela (Bancos, Caixa, Invest; o Relatório de patrimônio abre direto) e **Configurações** (abas Integrações, Dados, Aparência, Opções) vem por último, seguida só do **Sobre** (o mesmo dos outros apps). Nada de misturar uma função do app com as configurações. A tela aberta fica em `S.ui.maisTela` (`''` é o menu) e ocupa uma entrada no histórico (`marcarTela`): o Voltar do celular, o **‹ Mais** no alto e arrastar para a direita voltam ao menu.
- O que depende da IA respeita o interruptor **Usar IA** (desligado: some, inclusive as dicas). O que depende de uma integração só aparece com ela ligada.
- Uma janela aberta de dentro de outra (Fatura, print ou foto a partir da Nova despesa; uma confirmação como Apagar lançamento; o Editar do chat) volta para ela no Voltar do celular, no X e no Cancelar (`abrirFolha(..., sobre)`).
- Interruptores de análise (Descontar IR, Ocultar bens) começam desligados toda vez; filtros e abas ficam guardados.
- Em http (sem https) não há câmera nem microfone: explicar e oferecer escolher a foto.
- Celular primeiro (390 px); com 1000 px ou mais, barra lateral. Tema claro e escuro.
- Dados de exemplo e de testes sempre inventados (Ana, Beto, bancos e valores fictícios): nunca nomes, bancos, investimentos ou valores reais do dono.

## Conversa com o dono

Respostas curtas, em português. Ao terminar uma mudança: o que mudou, a versão e se está publicado. Ele usa o app do Home Assistant no Android: pense no Voltar do celular, no teclado e na câmera.
