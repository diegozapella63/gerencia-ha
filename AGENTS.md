# Instruções para quem for mexer neste repositório (pessoas ou IAs)

GerencIA é um app (add-on) do Home Assistant para as finanças da casa: caixa (recebimentos, despesas, fixos, cartões e faturas), investimentos com projeção, patrimônio, bens do InventarIA e leitura por IA (fatura, print, foto, mensagem ou fala). Faz parte de uma família de apps do mesmo dono, que conversam entre si pelo Home Assistant:

| App | Repositório | O que é |
|---|---|---|
| GerencIA | `diegozapella63/gerencia-ha` (este) | finanças: caixa, investimentos, contas a pagar |
| CronologIA | `diegozapella63/cronologia-ha` | calendário, rotinas, remédios, placar (mostra as contas daqui) |
| ResolvIA | `diegozapella63/resolvia-ha` | listas de tarefas, pontos, repetição |
| InventarIA | `diegozapella63/inventario-ha` | inventário da casa: cômodos e itens com valor (vira "Bens da casa" aqui) |
| CorrerIA | `diegozapella63/correria-ha` | o contato da CorrerIA Code no WhatsApp: as perguntas sobre finanças vêm para cá |

O Home Assistant instala direto do GitHub (`repository.yaml` + `gerencia/config.yaml`), a partir da branch `main`: o que está em `main` é o que os usuários recebem.

No `config.yaml`, `url` aponta para o repositório e o `panel_admin` fica no padrão do Home Assistant (o painel só para administradores): são as finanças da casa (saldos, investimentos, senhas dos PDFs, exportar e Começar do zero); abrir para todos é decisão do dono.

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
gerencia/app/oportunidades.py oportunidades de investimento: as taxas do Tesouro Direto (tabela Investir do site; reserva:
                              dados abertos do Tesouro Transparente), as ofertas dos bancos cadastrados lidas pela IA (a página
                              pronta pelo nome do banco, PAGINAS_BANCOS, ou a Página de ofertas do banco, `ofertas`; o trecho
                              conferido, só com FGC), o que avisar e os textos; a conta (equivalente, passa_alvo, comparar_meus)
                              fica no calc.py, igual à do app.js
gerencia/app/beneficios.py    benefícios lidos pela IA (print, foto, PDF, texto ou a página oficial): o pedido, o trecho conferido
                              e o número no trecho; a conta do período fica no calc.py (ciclo_beneficio)
gerencia/app/chat.py          Conversar com a IA: resumo dos dados para a IA, ações propostas (lançar, pagar, saldo) e a conversa guardada
gerencia/app/ferramentas.py   as ferramentas do CorrerIA (WhatsApp, Claude e Gemini): ler e gravar com as regras da tela, sem a IA daqui
gerencia/app/pdfsenha.py      abre PDF com senha (RC4 e AES de 128 e 256 bits, só biblioteca padrão) para a leitura por IA; as
                              senhas ficam em /data/senhas_pdf.json (fora das exportações e dos backups da pasta share)
gerencia/app/emails.py        faturas por e-mail: escuta o evento imap_content do Home Assistant (WebSocket aberto, reconecta
                              sozinho), acha o PDF anexado e decide se é fatura; o resto (imap.fetch_part, senhas, IA) no server.py
gerencia/app/pdf.py           PDF feito à mão (Helvetica, A4 em pé ou deitada, fotos JPG) para o Baixar PDF do Relatório de patrimônio;
                              o mesmo arquivo do InventarIA (inventario/app/pdf.py): ao mudar, copie para lá
gerencia/app/avisos.py        avisos no celular: as pessoas da casa e os celulares delas (mesma regra do phones.js do ResolvIA), o envio
gerencia/app/www/             a tela: index.html, app.js (JavaScript puro, sem build), styles.css, fontes
gerencia/app/www/selectsheet.js  as caixas de seleção no visual do app: arquivo igual em todos os apps (no ResolvIA e no
                              CronologIA, frontend/src/selectsheet.js); ao mudar, copie para os outros
tools/montar_previa.py        gera preview/gerencia-previa.html (o app num arquivo só, com dados de exemplo)
tools/versao.py               sobe a versão nos três lugares de uma vez (patch, minor ou a versão inteira)
tools/cobertura.py            roda os testes e mostra a cobertura do servidor e do app.js (--faltando arquivo: as linhas)
tools/capturas_docs.py        refaz as capturas do README (docs/*.png) a partir da prévia
tests/                        testes (ver tests/README.md): tests/run.sh (servidor e tela), tests/e2e/run.sh (visuais)
docs/                         capturas de tela do README
```

Os dados ficam em `/data/gerencia.json` (com `rev`: um PUT com revisão velha recebe 409 e o estado atual), versões automáticas em `/data/versoes` (as 3 últimas), imagens dos investimentos em `/data/fotos`, a conversa com a IA em `/data/chat.json` (as últimas 60 mensagens; fora do backup), as senhas dos PDFs em `/data/senhas_pdf.json` (fora das exportações e do backup da pasta share; a tela só vê o fim, ••••45), as faturas por e-mail em `/data/emails.json` e os PDFs delas em `/data/emails` (os últimos 30; fora das exportações), as taxas do Tesouro, as ofertas das páginas e o que já foi avisado em `/data/oportunidades.json` (os benefícios ficam no próprio `gerencia.json`, em `beneficios`: `{id, nome, origem: fixo:<id>|conta:<id>, tipo: contagem|saldo|vantagem, total, moeda, renova: mes|ano|nunca, desde, validade, usos}`; a conta do período em `calc.ciclo_beneficio`, igual ao app.js) e backups em `/share/gerencia`.

## Rodar no computador

```
cd gerencia/app
GERENCIA_DEV=1 GERENCIA_IA_MOCK=1 GERENCIA_DATA=/tmp/g/data GERENCIA_SHARE=/tmp/g/share GERENCIA_MEDIA=/tmp/g/media python3 server.py
```

Abra `http://localhost:8099`. Em **Carregar exemplo** aparecem dados inventados. A prévia sem servidor: `python3 tools/montar_previa.py` e abra `preview/gerencia-previa.html`.

## Checklist de toda mudança

1. Implementar. Servidor: só biblioteca padrão do Python. Tela: `gerencia/app/www/app.js` (um IIFE; ações por `data-a`, janelas de baixo com `abrirFolha`/`pintarFolha`/`fecharFolha`, gravação com `persistir`). Cálculo novo vale nos dois lados (`calc.py` e `app.js`).
2. Testar: `tests/run.sh` (servidor e tela; a tela precisa do playwright) e os visuais ligados à mudança (`tests/e2e/run.sh nome ...`). Toda mudança ou bug corrigido vem com o teste dele: na tela, em `tests/test_tela_<área>.py` (ver `tests/README.md`); no servidor, no `tests/test_*.py` da parte; num visual, com verificações do `_confere.py`.
3. Subir a versão: `python3 tools/versao.py patch` (correção, 1.23.0 → 1.23.1) ou `minor` (novidade, 1.23.x → 1.24.0). Ela fica escrita em três lugares, `gerencia/config.yaml` (`version:`), `gerencia/app/server.py` (`VERSAO`) e `gerencia/app/www/app.js` (`const VERSAO`), porque cada um é lido sozinho (a imagem só leva a pasta app/; a tela abre direto do arquivo nos testes e na prévia); o `tests/test_versao.py` confere que estão iguais e que o CHANGELOG começa por ela. A cobertura (`python3 tools/cobertura.py`) fica em pelo menos 95% das linhas de cada arquivo.
4. `gerencia/CHANGELOG.md`: nova seção no topo, em português, do ponto de vista de quem usa (o que mudou na tela, não no código).
5. `gerencia/DOCS.md` quando muda o comportamento ou aparece algo novo.
6. `python3 tools/montar_previa.py` e commit também de `preview/gerencia-previa.html`.
7. Commit em `main` com mensagem em português ("GerencIA 1.24.0: ..."), `git pull --rebase` e push. O GitHub roda todos os testes a cada push (aba Actions).

## Como os apps conversam

Pela pasta `/share` do Home Assistant. Mudar um formato aqui exige mudar o outro app junto.

- **GerencIA → CronologIA**: este app grava `share/gerencia/integracao.json` (`url`, `ip_url`, `chave`) e responde em `/api/integracao/contas`, `/pagar`, `/desfazer` e `/nova` com `Authorization: Bearer <chave>` (`integracao.py`). Desligado em **Mais › Configurações › Integrações**, o arquivo some e as rotas respondem 401. Um fixo do mês tem sempre o id `v:<fixo>:<AAAA-MM>`, lançado ou não; uma fatura, `f:<conta>|<vencimento>`.
- **CorrerIA → GerencIA**: com **Mais › Configurações › Integrações › CorrerIA** ligado, este app grava `share/gerencia/correria.json` (`app`, `nome`, `assunto`, `url`, `ip_url`, `chave`, `ferramentas` e, com a IA ligada, `rota` e `anexos`; chave própria em `/data/correria.key`). O contrato é o mesmo para todos os apps da família (ver o AGENTS.md do CorrerIA). **Ferramentas** (sem a IA daqui; o CorrerIA as usa no WhatsApp e como servidor MCP do Claude e do Gemini): `GET /api/integracao/ferramentas` → `{instrucoes, ferramentas: [{nome, titulo, descricao, entrada (JSON Schema), grava, apaga}]}` e `POST` `{nome, argumentos, pessoa, cliente}` → `{texto}` (400 `{erro}` dizendo o que vale; 404 ferramenta desconhecida), com as regras em `ferramentas.py` (as mesmas da tela: parcelas, cartão pela fatura, fixo do mês `v:<fixo>:<AAAA-MM>`, fatura `f:<conta>|<vencimento>`); uma gravação sobe a `rev` e a tela vê pelo `/api/rev` (`correria_uso`: o último uso). **Conversa** (só com a IA ligada; hoje só para fotos e PDFs, e como reserva): `POST /api/integracao/conversa` (`{texto, historico, pessoa, canal: whatsapp|correria, anexo?: {tipo, nome, b64}}` → `{resposta}`, sem ações, pelo `chat.instrucoes_whatsapp`; com anexo, `conversa_anexo` lê como o Ler com IA e o que achar vira um pendente `origem: whatsapp` na lista das faturas por e-mail, `/data/emails.json`, para conferir no Início).
- **InventarIA → GerencIA**: o InventarIA grava `share/inventario/integracao.json` e este app lê `/api/integracao/itens` e `/comodos` (`bens.py`, cache de 10 min). Só lê; nada muda lá. Patrimônio = investimentos meus + bens (os de terceiros ficam fora).
- **Home Assistant**: IA pela ação `ai_task.generate_data` para a leitura, as dicas e o chat (anexos em `/media/gerencia/ia-temp`, apagados depois; no chat a IA devolve `{resposta, lancamentos, pagar, investimentos}` e a tela confirma cada ação com as funções da leitura por IA e do Pagar), fala para texto (`voz.py`, que também tem a `ConexaoWS` usada pelo `emails.py`), faturas por e-mail (`emails.py`: assina `imap_content` pelo WebSocket, pega o PDF com `imap.fetch_part?return_response` e lista as contas com `config_entries/get` do domínio `imap`; o **Procurar faturas agora** (`email_procurar`) abre os 30 mais novos com `imap.fetch?return_response`: o "uid" da integração é o número da mensagem na pasta (1 é o mais antigo), então `_ultimo_email` acha o último dobrando e dividindo ao meio, e cada um com PDF vai para o `email_chegou(..., avisar=False)`; com a IA simulada (testes), `/api/emails/simular` faz um e-mail chegar), aviso das dicas nos celulares das pessoas escolhidas (`avisos.py`: `notify.mobile_app_*`, achados pelos rastreadores de cada `person.*` e o aparelho no registro, como no ResolvIA), sensores opcionais, índices do Banco Central (CDI, Selic, IPCA, TR) a cada 12 h e o aviso das oportunidades de investimento no horário escolhido (`rotina_oport`; o toque abre `/app/<app>/oportunidades`, que o painel passa à tela por `home-assistant/properties`).

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
- Relatórios (a página e o PDF) com o cabeçalho dos apps, o mesmo do ResolvIA: um cartão com a faixa na cor do app, o ícone, Gerenc**IA** (o IA na cor) · finanças, o título, a contagem e quando (a hora só ali); no fim, a marca da CorrerIA Code como no **Sobre**, a mesma do ResolvIA e do InventarIA (o raio no quadrado inclinado na cor do app, Correr**IA** Code e DESENVOLVIMENTO DE SOFTWARES; no PDF, no pé de cada folha, com a página). Nada repetido (sem o nome da casa). No app do Home Assistant no Android a página não imprime: o PDF é feito pelo servidor e baixado.
- **Inativos no fim, recolhidos**: o que está inativo, cancelado, encerrado, arquivado ou ignorado de propósito (por uma opção, como Nunca considerar) fica numa seção no fim da lista, recolhida por padrão, com o nome e a contagem (ex.: **Arquivados (3)**); abre num toque. Vale para todos os apps da família. Aqui: `recolhido(id, titulo, n, corpo)` no app.js (aberto só até sair do app, em `ABERTOS`).
- **Caixas de seleção no visual do app**: nenhuma janela nativa do celular. Toda caixa de seleção abre pelo selectsheet.js; sugestões de texto (no lugar do `<datalist>`) e horários (sem AM/PM) também no visual do app; a caixa fechada igual aos outros campos (altura, cantos, seta), no claro e no escuro. Aqui: `data-sug="<id do datalist>"` no campo (a lista `.sug-box` embaixo dele), nunca `list=`.
- Dados de exemplo e de testes sempre inventados (Ana, Beto, bancos e valores fictícios): nunca nomes, bancos, investimentos ou valores reais do dono.

**Padrão da família (igual em todos os apps)**
- Barra de baixo: o botão do meio é **Adicionar** (no EconomIA, a ação principal dele); **Buscar**, quando houver, é a 2ª aba; **Mais** é a última, com o ícone de três pontos.
- **Mais** é um menu: as funções do app, depois **Configurações** e por último **Sobre**. Os relatórios se chamam **Relatório de/do …**.
- **Configurações** em 4 abas, nesta ordem: **Integrações › Dados › Aparência › Opções**; abre em Integrações. Nenhuma função do app vira aba.
- **Integrações**, nesta ordem: os outros apps da família › CorrerIA › **IA do Home Assistant** (o Usar IA) › Falar › Uso da IA › Sensores. Aqui, depois do Uso da IA, vêm as Faturas por e-mail e as Senhas dos PDFs (só com a IA ligada).
- IA: as entradas se chamam **Colar mensagem**, **Escolher fotos** (ou **Escolher fotos ou PDF**, onde PDF vale) e **Digitalizar com IA**; a conversa recomeça em **Nova conversa**; o Voltar do celular fecha a Conversa.
- Palavras: **Apagar** (nunca Excluir); **Testar no meu celular**; **Home Assistant Cloud** (não Nabu Casa); recolhidos como **Nome (n)**; o CHANGELOG começa com "# Mudanças".
- **Dados**: Exportar › Backup na pasta share › Importar › Versões anteriores › Onde ficam os dados › Começar do zero.
- **Aparência**: o tema vale no aparelho (começa em Automático; aqui, `localStorage` `gerencia.tema`, e o `ajustes.tema` de antes vale até escolher); a cor do app vale para a casa toda; uma paleta só, de 12 cores (Vermelho, Coral, Laranja, Ouro, Verde, Menta, Turquesa, Azul, Índigo, Lilás, Rosa, Grafite; `CORES_APP` no app.js e no calc.py); a Cor do dia é a mesma em todos os apps (as 11 sem o Grafite, pelo número do dia).

## Conversa com o dono

Respostas curtas, em português. Ao terminar uma mudança: o que mudou, a versão e se está publicado. Ele usa o app do Home Assistant no Android: pense no Voltar do celular, no teclado e na câmera.
