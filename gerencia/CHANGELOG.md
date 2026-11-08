# Mudanças

## 1.38.0

- **Fotos e PDFs pelo WhatsApp** (com o CorrerIA 0.2.0): mande a foto de uma nota, um print ou a fatura em PDF para o contato no WhatsApp e a IA do GerencIA lê. O que ela achar fica para conferir nos **Avisos do Início** ("Enviado por Ana · Pelo WhatsApp"), como as faturas por e-mail: toque, confira e lance (ou Ignorar). A fatura com senha abre com as Senhas dos PDFs. Com uma pergunta junto ("quanto deu essa nota?"), a resposta vem com o que foi lido.
- **Ler com IA** também aceita imagens PNG e WebP.

## 1.37.0

- **CorrerIA no WhatsApp** (Mais › Configurações › Integrações; vem desligado): com o app **CorrerIA** (o contato da CorrerIA Code no WhatsApp) instalado, as pessoas da casa perguntam sobre as finanças pelo WhatsApp e a IA do GerencIA responde com os seus dados. Por lá a IA só responde: lançar, pagar e mudar saldo continuam no app. O cartão mostra quando o CorrerIA perguntou pela última vez.

## 1.36.0

- **Faturas por e-mail** (Mais › Configurações › Integrações; vem desligado): com o seu e-mail ligado ao Home Assistant pela integração **IMAP** (no Gmail, com uma senha de app), cada fatura que chega em PDF é aberta com as **Senhas dos PDFs**, lida pela IA e fica esperando a sua conferência num aviso no **Início**. Nada é lançado sozinho: toque no aviso, confira e lance (ou **Ignorar**).
  - **De quem**: os remetentes das faturas (o endereço ou só o fim dele, como `bancoazul.com.br`). Sem nenhum, valem os e-mails com PDF e "fatura" no assunto.
  - Se nenhuma senha abrir o PDF, o aviso diz que o PDF tem senha: toque, digite a senha e ela fica guardada para as próximas. Uma senha nova cadastrada abre sozinha as faturas que esperavam.
  - **Recebidos** mostra os últimos e-mails com PDF e o que aconteceu com cada um; o que não parecia fatura dá para ler com **Ler**.
  - **Avisar no celular** (Mais › Configurações › Opções › Faturas por e-mail): quando uma fatura fica pronta para conferir, quem você escolher recebe um aviso.

## 1.35.1

- Uma janela aberta logo depois de salvar outra (por exemplo, **Adicionar senha** logo depois de guardar uma) não fecha mais sozinha, e o Voltar do celular fecha só ela.

## 1.35.0

- **Faturas em PDF com senha**: a leitura por IA abre o PDF com a senha e só então manda para a IA. Em **Mais › Configurações › Integrações › Senhas dos PDFs** você cadastra as senhas de sempre (por exemplo, os dígitos do CPF), e cada fatura com senha abre sozinha. Se nenhuma servir, a janela pede a senha; com **Guardar para as próximas faturas** (vem ligado), ela entra na lista. A senha nunca aparece de novo na tela (só o fim, como ••••45) e não vai para as exportações nem para os backups da pasta share.

## 1.34.0

- **Relatório de patrimônio**: no fim, a marca da **CorrerIA Code** como no **Sobre** (o raio na cor do app, CorrerIA Code e DESENVOLVIMENTO DE SOFTWARES), a mesma dos relatórios do ResolvIA e do InventarIA. No PDF, ela fica no pé de cada página, com o número da página.

## 1.33.1

- **Relatório de patrimônio › Baixar PDF** funciona no app do Home Assistant no celular: o PDF vai para a pasta Downloads (aparece nas notificações), e o botão diz **Baixando…**.

## 1.33.0

- **Conferir sozinho** (Mais › Configurações › Opções › Dicas de economia): no lugar do horário, que no app do Home Assistant aparecia vazio, você escolhe de quanto em quanto tempo os preços são conferidos de novo: **Toda semana**, **A cada 15 dias** ou **Todo mês** (o padrão, como antes). Uma assinatura nova continua sendo conferida logo.
- **Relatório de patrimônio**: o rodapé virou um cartão como o do cabeçalho, com o raio da **CorrerIA Code**, e fica lá embaixo (na página e em cada folha do PDF, com o número da página quando há mais de uma).
- Sem investimentos, o resumo do relatório não mostra mais "Investido R$ 0,00".

## 1.32.0

- **Caixas de seleção** (Como é pago, a categoria e a conta na leitura por IA, o tipo e o rendimento de um investimento, IA usada pelo app, Fala para texto) abrem uma janela no visual do app, de baixo para cima, com as opções em linhas e a atual marcada na cor do app, no tema claro ou escuro, e não mais a janela padrão do celular, como nos outros apps da família. O Voltar do celular, o X ou tocar fora fecham só ela; numa janela do app (como a Nova despesa), o Voltar seguinte fecha a janela.

## 1.31.0

- **Dicas de economia** com opções em **Mais › Configurações › Opções**, como o aviso de prazos do ResolvIA:
  - **Conferir sozinho** (vem ligado): todo dia, no horário que você escolher, o app procura as assinaturas nos fixos e faturas e confere os preços com mais de 30 dias. Uma assinatura nova é conferida logo. Desligado, só no **Conferir agora**.
  - **Avisar no celular** (vem desligado): quando aparece uma dica nova, quem você marcar em **Quem recebe** ganha um aviso nos celulares ligados a essa pessoa no Home Assistant (**Configurações › Pessoas**). Cada dica é avisada uma vez; tocar no aviso abre o GerencIA. **Testar no meu celular** manda um aviso agora para o seu.
- **Relatório de patrimônio**: os bens aparecem numa linha só (e os imóveis em outra). **Detalhar bens e imóveis** mostra item por item, na página e no PDF.

## 1.30.1

- **Relatório de patrimônio** mais limpo: no alto, só "GerencIA · finanças" (sem o nome da casa); no pé, só "CorrerIA Code · desenvolvimento de softwares". A hora em que foi gerado aparece uma vez, no cabeçalho.

## 1.30.0

- **Relatório de patrimônio** com o cabeçalho dos relatórios dos apps, como o do ResolvIA: o ícone, GerencIA, o nome da casa no Home Assistant, o título, quantos investimentos e bens e quando foi gerado. Igual na página e no PDF.
- **Bens** no relatório: os bens cadastrados no GerencIA e, com **Bens no InventarIA** ligado, todos os itens de lá, com o cômodo, quanto perdem ou valorizam por ano e a data do valor.
- O **Patrimônio** do relatório agora é o mesmo do Início (seus investimentos e bens), ao lado de Investido, Bens e De terceiros. O Por banco fica só com os investimentos.
- **PDF** deitado, com as colunas **Por mês**, **Em 1 ano** e **Em 5 anos** (com as taxas de hoje e sem novos aportes) e o total de cada grupo.
- Trocar entre Todos, Meus e De terceiros não empilha páginas: o Voltar (e o do celular) volta direto ao app.
- Num bem, o relatório dizia "Sem rendimento"; agora diz quanto perde ou valoriza por ano.

## 1.29.0

- **Relatório de patrimônio**: **Baixar PDF** no lugar do Imprimir. O PDF é feito pelo app e baixa como arquivo, também no app do Home Assistant no celular (lá o Imprimir não funcionava). Vem com cabeçalho (o ícone, GerencIA, Finanças da casa e a hora em que foi gerado), o resumo, os investimentos de cada um, barras por banco e o número da página no pé.
- No alto do relatório, **Todos**, **Meus** ou **De terceiros** escolhe o que entra no resumo, nas seções, no Por banco e no PDF.

## 1.28.1

- **Sensores no Home Assistant**: desligados, sem a nota do sensor da IA; ligados, a lista traz o da IA só com a IA ligada e o dos bens só com o InventarIA.
- **Falar**: com a IA fora do ar, não diz mais "pronto" nem que o microfone fica no alto (ele não aparece).
- Com **Atualizar sozinho** desligado, o alto da tela mostra "Índices de partida" em vez de esperar os do Banco Central.
- **Bens no InventarIA** só manda para Mais › Invest quando há itens com valor.
- Com a IA desligada, o Início não diz mais que está conferindo os preços das assinaturas; ligada de novo, as **Dicas de economia** dizem "Ainda não conferido." em vez de "A IA está desligada".
- Com **Corrigir valores pelo rendimento** desligado, a ajuda do valor no **Novo investimento** fica só "O saldo de hoje." e o rodapé do **Relatório de patrimônio** diz que os valores são os últimos informados. Num bem, a ajuda não fala mais em "perde" (a categoria pode valorizar).

## 1.28.0

- **Bens que valorizam**: em **Mais › Invest › Valor dos bens por ano**, cada categoria tem **Perde** ou **Valoriza** e a % por ano ao lado. Um imóvel que valoriza 5% ao ano fica com Valoriza e 5. Antes era preciso digitar um número negativo, e o teclado do celular não tem o "−".
- O Início, a Carteira, a Divisão e a janela Bens da casa dizem quanto os bens **perdem** ou **valorizam** por ano, conforme o caso.

## 1.27.0

- **Mais › Sobre**, a última linha do menu: quem faz o app (**CorrerIA Code**, desenvolvimento de softwares, e por que esse nome), os apps da família (CronologIA, ResolvIA, GerencIA, InventarIA, EconomIA e MemorIA), cada um com uma linha e o link para o GitHub, e o botão **Meu GitHub**. O Voltar do celular e o **‹ Mais** voltam ao menu.
- Com a IA fora do ar, o aviso do **Ler com IA** agora diz onde ver: Mais › Configurações › Integrações.
- A chave **Usar IA** lista tudo o que ela desliga, inclusive Conversar com a IA e Atualizar saldos.

## 1.26.1

- **Relatório de patrimônio** abre no mesmo tema do app (claro ou escuro, inclusive o automático do Home Assistant). Ao imprimir ou salvar em PDF, sai sempre em fundo branco.
- No celular, o banco aparece embaixo do nome do investimento e o **Valor hoje** não fica mais cortado na beirada.

## 1.26.0

- **Mais** agora é um menu, como no InventarIA: **Bancos**, **Caixa** (fixos, categorias e dicas de economia), **Invest** (índices de mercado e perda de valor dos bens), **Relatório de patrimônio** e, por último, **Configurações**. Cada um abre a sua tela, com **‹ Mais** no alto para voltar; o Voltar do celular e arrastar para a direita também voltam ao menu.
- **Configurações** fica com as abas Integrações, Dados, Aparência e Opções. O Relatório de patrimônio saiu de Dados e ganhou a sua linha no menu.
- Quem estava numa aba de Mais volta no mesmo lugar, já no caminho novo (por exemplo, Mais › Configurações › Dados).
- O ícone de Mais, embaixo e na barra lateral, agora são três pontos.

## 1.25.0

- **Cor do dia**: a cor do app muda todo dia, passando pelas cores de Mais › Aparência (sem o Grafite). Vem ligada, também para quem já tinha escolhido uma cor, e é a mesma o dia todo, em todos os aparelhos; com o app aberto, troca à meia-noite. A cor do dia aparece marcada em Cor do app; tocar numa cor desliga a Cor do dia e fica com ela. O placar, o ícone, os gráficos e o relatório seguem a cor.

## 1.24.3

- **Ler recibo** num salário fixo: se o plano de saúde tinha sido apagado só daquele mês e o recibo traz o plano, ele volta para o mês, e o caixa bate com o líquido.
- Em Mais › Integrações, enquanto o Home Assistant não responde, o app pergunta pela situação da IA uma vez só (antes repetia a cada redesenho).
- Por dentro: a tela quase toda testada (99% das linhas do app).

## 1.24.2

- **Aplicar mais** e **Transferir**, abertos de um investimento, voltam para ele no Cancelar, no X e no Voltar do celular.
- Num bem separado por categoria (Bens), Aplicar mais, Transferir e o saldo lido pela IA mudam as partes na mesma proporção: antes o valor de hoje não mudava (e numa transferência o dinheiro sumia).
- Um desconto do salário guardado em reais (de versões antigas) aparece em reais, não como porcentagem.

## 1.24.1

- **Carregar exemplo** e a prévia usam bancos inventados (Banco Lua, Banco Sol, Banco Coral, Corretora Norte, Banco Azul e Banco Verde), como os nomes das pessoas.

## 1.24.0

- **Conversar com a IA**: o balão ao lado do microfone abre uma conversa em qualquer tela. Pergunte sobre o que está na tela ou sobre os seus dados ("o que vence esta semana?", "quanto rende a carteira?"), ou converse sobre outro assunto. Peça para **lançar** um gasto, **pagar** uma conta ou **atualizar um saldo**: a IA mostra o que vai fazer e você toca em **Confirmar** (ou **Editar**, que abre a janela de sempre e volta para a conversa). O microfone dentro dela dita a pergunta. A conversa fica guardada; a lixeira apaga. Some com Usar IA desligado.
- **Cancelar volta para onde estava**: nas confirmações abertas de dentro de outra janela (Apagar lançamento, fixo ou parcela, Excluir investimento ou banco, Apagar categoria, Restaurar versão), Cancelar, X e Voltar voltam para ela em vez de fechar tudo.
- **Contas atrasadas**: o aviso do Início leva até elas. Em A pagar e receber, o mês de hoje mostra primeiro o que ficou sem pagar nos dois meses anteriores.
- **Ajustar saldo** com o saldo no vermelho mostra o sinal, com Positivo e Negativo para trocar.
- Mudar só o valor de um fixo do dia 31 num mês de 30 dias não muda mais o dia dele.
- Recibo lido num recebimento de uma vez só: o plano de saúde (e os outros descontos conferidos no líquido) é lançado no mesmo dia, e o caixa bate com o recibo.
- Com **Usar IA** desligado, somem também a dica de plano anual e o Atualizar saldos.
- Os atalhos **Índices** e **Ver as dicas** do Início abrem a aba certa de Mais.
- **Investimentos**: Sem banco mostra só os sem banco; a busca ignora acentos; Dinheiro e Bens sem nome não levam o nome de um banco; o Buscar da barra lateral procura em todos; esconder valores também na aba Invest; um bem separado em categorias mostra a perda por mês somando cada parte.
- Por dentro: as telas inteiras testadas (caixa, investimentos, IA, câmera, fala, Mais, navegação e o chat) e todos os testes visuais conferindo valores.

## 1.23.3

- **Despesa ligada a um recebimento**: os sensores do Home Assistant e as contas que aparecem no CronologIA passam a usar o mesmo dia da tela (o dia em que o recebimento entra). Antes, o saldo do caixa no sensor podia ficar diferente do app.
- Por dentro: muito mais testes (servidor quase todo, cálculos da tela um a um, conexão com o CronologIA) e testes visuais que conferem os valores, não só se abriu sem erro.

## 1.23.2

- **Ler com IA**: liquidez "diária" escrita com acento (como a IA costuma responder) agora fica como diária, e não "no vencimento".
- **Dicas de economia**: uma assinatura com travessão ou ponto no nome ("Assinatura—Claude") também é reconhecida.
- **Conexão com o CronologIA**: um período ou uma data inválida responde "Período inválido." em vez de erro do app.
- O exemplo usa nomes inventados (Ana e Beto).
- Por dentro: testes unitários, do servidor e visuais rodando no GitHub a cada mudança, e instruções para quem continuar o projeto (AGENTS.md).

## 1.23.1

- **Ocultar bens e imóveis** e **Descontar imposto de renda** não ficam mais guardados: começam desligados toda vez que o app abre.

## 1.23.0

- **Digitalizar com IA**, como no ResolvIA: na Nova despesa e no Novo investimento, abre a câmera aqui dentro, fotografa até 4 páginas (com lanterna, quando o celular tem) e, no Pronto, a IA já lê e mostra o que achou para conferir. Também no Ler com IA (**Digitalizar com a câmera**). Sem https, a câmera não abre aqui: dá para tirar ou escolher a foto pelo celular.
- **Voltar volta para a Nova despesa**: Fatura, print ou foto, Colar mensagem, Falar e Digitalizar, abertos da Nova despesa ou do Novo investimento, voltam para ela no Voltar do celular, no X e no Cancelar (antes iam para a tela principal). Depois de salvar, fecha tudo como antes.
- **Fatura, print ou foto abre direto a galeria**, sem trocar a janela: se desistir da escolha, continua na Nova despesa.

## 1.22.0

- **Bens da casa na Carteira**: com o InventarIA, um cartão só de leitura (borda tracejada) mostra o total dos bens, quantos itens e quanto perdem por mês, em Todos e em Meus. Tocar abre Bens da casa.
- **Evolução dos bens** na janela Bens da casa: quanto valem em 1, 5 e 10 anos, e **Ver na Evolução**.
- **Ocultar bens e imóveis** na Evolução (abaixo de Descontar IR) e na Divisão: mostra só os investimentos, sem os bens do InventarIA e os do tipo Bens. A escolha fica guardada.

## 1.21.1

- As **categorias dos bens** vêm do InventarIA (1.17.0 ou mais novo, onde dá para renomear, criar e excluir categorias), mais Imóveis e Veículos. Uma categoria nova começa perdendo 10% ao ano. Sem o InventarIA, ficam as de costume.

## 1.21.0

- **Separar um bem por categoria** (opcional): no tipo Bens, "Separar o valor por categoria" abre as categorias do InventarIA (e Imóveis e Veículos), cada uma com o seu valor. O total é a soma, e cada parte perde a taxa da sua categoria. Sem separar, continua uma categoria só para o total.
- **Imóveis** na tabela de perda de valor, começando em 0% (mantém o valor).
- **Valorizar**: na tabela de Mais › Invest, uma taxa negativa faz a categoria ganhar valor por ano (útil para um imóvel). O cartão mostra "valoriza X% a.a." e a Evolução mostra "bens +R$".

## 1.20.0

- **Bens de terceiros (e seus, sem o InventarIA)**: novo tipo **Bens** no investimento, só com nome, valor e **categoria** (Veículos, Eletrônicos, Móveis, Cozinha, Decoração, Roupas, Outros). Sem cômodos: um total por bem, de quem você quiser. Ele perde a taxa da categoria por ano.
- **Veículos** na perda de valor (15% ao ano, para começar).
- **Perda de valor dos bens** em Mais › Invest: uma tabela só, que vale para os bens do InventarIA e para os do tipo Bens. Mudar a taxa de uma categoria muda todos os bens dela.
- Bens perdem valor e não entram no "rende por mês": o cartão mostra "perde ≈ R$ X por mês", a Divisão também, e a Evolução separa o rendimento dos investimentos da perda dos bens. No placar, os seus bens do tipo Bens somam na coluna Bens; os de terceiros ficam fora do patrimônio, como o resto do dinheiro deles.

## 1.19.4

- **Números grandes cabem de verdade**: na 1.19.3 eles deixaram de se sobrepor, mas no celular com fonte grande ficavam cortados. Agora a letra diminui na proporção certa até o número caber inteiro, também com a fonte do Android aumentada, e ajusta de novo quando a tela muda de tamanho.

## 1.19.3

- **Números grandes não se sobrepõem mais**: nos pares de valores (Hoje e Em N anos, Total e Rende por mês…), um número comprido diminui a letra em vez de invadir o vizinho, e os dois ficam do mesmo tamanho.
- **Evolução só com bens** (sem investimentos seus nem aportes): mostra só a linha dos bens perdendo valor, com "Bens hoje" e quanto perdem, sem as linhas zeradas de investimento e sem "+R$ 0 de rendimento".

## 1.19.2

- **Bens na Divisão e na Evolução** (em Tudo e em Só o meu): na Divisão, os bens do InventarIA são uma fatia à parte, "Bens da casa", com quanto perdem por ano. Na Evolução, o Hoje e o Em N anos somam os bens, a linha **Bens** mostra a perda de valor ao longo dos anos e a tabela por ano ganha a coluna Bens.

## 1.19.1

- **Patrimônio sem o dinheiro de terceiros**: o placar do Início soma só os seus investimentos (e os bens do InventarIA). O rendimento por mês do placar também é só o seu. O dinheiro de terceiros continua no quadro por pessoa e na Carteira.
- `sensor.gerencia_patrimonio` passa a ser só o seu; o total com terceiros fica no atributo `com_terceiros`.

## 1.19.0

- **Bens do InventarIA no patrimônio**: com o InventarIA 1.16.0 ou mais novo, os valores dos itens somam no patrimônio. O placar mostra **Investido** e **Bens** separados, e o destaque **Bens da casa** abre os valores por categoria e por cômodo.
- **Perda de valor por categoria**: os bens perdem valor por ano desde a data do valor no InventarIA (eletrônicos 20%, móveis 10%, decoração 5%…). As taxas mudam em Mais › Integrações › Bens no InventarIA, onde também dá para desligar.
- Sensor `sensor.gerencia_bens` e o atributo `com_bens` no patrimônio.

## 1.18.5

- Tipo **Dinheiro**, para dinheiro guardado em espécie: sem banco, sem rendimento e sem vencimento (o formulário só pede nome e valor). Na Carteira aparece como "Em espécie". A IA também reconhece ("15 mil dinheiro").

## 1.18.4

- Tipo **Ouro** nos investimentos (barra, ouro ativo financeiro, ETF de ouro): sem taxa fixa, a projeção usa a valorização que você estimar por ano (começa em 10%, dá para mudar) e, com Descontar IR, 15% sobre o ganho, como em ações. A IA também reconhece ouro.

## 1.18.3

- **Do Novo investimento, só investimentos**: Colar mensagem, Imagem e Falar abertos ali não lançam nada no caixa. Um valor com um banco ou nome ("30.350 nubank") é o saldo desse investimento; "dinheiro" guardado vira um investimento sem rendimento. O Ler com IA do Início continua separando tudo sozinho.
- **De quem é**: a IA lê o dono no texto ("tudo dinheiro da mãe") e procura entre os investimentos dessa pessoa; os novos já entram como dela.

## 1.18.2

- **Revisar antes** não sai mais da conferência da IA (Ler com IA e Atualizar saldos): abre ali mesmo os dados do que a IA leu. No investimento novo: valor, nome, banco, tipo, rendimento, taxa, vencimento e liquidez. No que já existe: o saldo. **Pronto** ou **Voltar** retornam para a lista, com o resto como estava.

## 1.18.1

- **Menos texto**: as explicações do app foram enxugadas, sem os porquês do óbvio. Ficou o que ajuda a decidir (valores, datas, o que muda no caixa); saíram as frases que repetiam o que o botão ou o campo já dizem. Vale para Mais (todas as abas), Opções, Ler com IA, Atualizar saldos, aporte, transferir, fixos, fluxo, categorias e exportar.

## 1.18.0

- **Atualizar saldos com IA**: para a listinha com o valor de agora de cada investimento (de um terceiro no WhatsApp, num print: "Nubank, valor atualizado, R$ 500"). Fica em Adicionar, no Novo investimento e na Carteira › Terceiros (já com a pessoa). A IA acha cada investimento pelo banco, nome e dono; a conferência mostra o aporte de cada um (a diferença para o valor de hoje), o total dos aportes e deixa trocar o investimento de cada linha. O que não tiver correspondente vira investimento novo da pessoa. Conta como **Atualizar saldos** no Uso da IA.
- **Conta em cada linha** ao conferir os lançamentos lidos pela IA: categoria e conta lado a lado, e, se a conta tiver cartão, **débito ou crédito**. A IA já sugere a conta do banco que viu em cada linha; **Lançar todos em** muda todas.
- As escolhas de cada linha (categoria, conta, investimento) ficam **alinhadas**, na largura toda.
- **Colar mensagem** abre só o campo da mensagem, e **Imagem** só a imagem, sem misturar as outras opções.
- Aberto do **Novo investimento**, o Ler com IA fala de investimentos (exemplos e ajuda), não de gastos.

## 1.17.2

- A explicação do `sensor.gerencia_ia_hoje` saiu do Uso da IA e foi para **Sensores no Home Assistant**, junto dos outros sensores.

## 1.17.1

- **Aplicar mais pelo total**: no Aplicar mais, a opção **Quanto tem agora** recebe o total que o banco mostra; o aporte é a diferença para o valor de hoje (e entra no caixa do mesmo jeito, se quiser).
- **Imagens do investimento só guardam**, como combinado: ao editar um investimento, **Guardar** não tem mais o Ler com IA. Para a IA ler, use Ler com IA no Adicionar.

## 1.17.0

- **Pago fica verde**, como no CronologIA: no Caixa, o que já foi pago ou recebido (e a fatura paga) fica com o fundo verde e o visto. O que falta tem um **círculo do lado** do valor: toque para dar baixa (Paguei, Recebi, Apliquei), no lugar do botãozinho de antes.
- **Período à escolha no Fluxo**: além de 12 atrás, 6 + 6 e 12 à frente, o **Outro** abre os meses para trás e à frente (atalhos 24 atrás, 12 + 12, 24 à frente, 36…; até 60 de cada lado). Com muitos meses, o gráfico mostra menos nomes embaixo e o ano no lugar de janeiro. A média do que sobrou começa no primeiro mês com lançamentos.
- **Horizonte à escolha no Invest**: **Outro**, de 1 a 50 anos (atalhos 3, 15, 20, 25, 30 e 40).
- **Transferir entre investimentos**: no investimento, ao lado de Aplicar mais. Quanto (ou Tudo) e para onde; sai de um e soma no outro, sem mexer no caixa. Passando tudo, escolha manter zerado ou tirar da carteira.
- **Buscar no alto** do Invest, acima de Carteira, Evolução e Divisão.
- **Categorias alinhadas**: o valor do mês e a média ficam na mesma linha mesmo quando o rótulo quebra; as barras têm todas a mesma largura; os percentuais com uma casa (30,1%, 15,5%).
- **Tabelas cabem no celular** (tabela por ano e do fluxo): o cabeçalho quebra em duas linhas e os números ficam do mesmo tamanho.
- **Botões do aporte** do mesmo tamanho, alinhados com as escolhas do Horizonte.
- **Dicas com a IA desligada**: o quadro e a opção dizem que os planos anuais precisam da IA; as dicas de categoria continuam.
- **Uso da IA** sem o texto só do Google: uma linha para qualquer provedor.
- **Botões do mesmo tamanho em Mais**: no celular ocupam a largura toda (Exportar, Importar, Versões, Backup, Dicas, Índices, IA…); do tablet para cima, todos com a mesma largura.
- A lista **Fala para texto** ficou como a da IA: **Padrão do Home Assistant** e o nome de cada uma (Home Assistant Cloud, Google AI STT…), sem o nome do assistente de voz junto.

## 1.16.1

- O campo de escolha em Leitura por IA se chama só **Fala para texto**.

## 1.16.0

- **Dicas de economia** mostram a **data da última verificação** ("Última verificação: hoje às 15:45", "ontem às…" ou o dia). O app verifica sozinho uma vez por dia, mesmo sem nenhuma assinatura nos fixos, e na hora no **Conferir agora**.
- **Falar com escolha**, igual à IA: em **Mais › Leitura por IA** há a lista **Fala para texto**, com todas as do Home Assistant (por exemplo Home Assistant Cloud, Google AI STT, faster-whisper) No **Padrão do Home Assistant** fica a que ele já usava, como antes. O nome que aparecia (por exemplo "Gemini") era só o assistente de voz que transforma a voz em texto; quem entende e separa os lançamentos continua sendo a **IA usada pelo app**.

## 1.15.0

- **Botões do mesmo tamanho**, como no EconomIA, no ResolvIA e no CronologIA: as escolhas ficam em colunas, com o texto no meio (categorias, bancos para cadastrar, contas, tipo, rendimento, investimento do aporte e as dos formulários). As curtas (filtros do caixa, período do fluxo, horizonte, divisão) ficam três ou quatro por linha. As fileiras que rolam para o lado continuam como estavam.
- **Apagar um fixo** ficou claro: **Só o de outubro** (ou só o deste ano), **Parar a partir de** (o que já foi lançado continua) e **Apagar o fixo e o que ele já lançou**. Um fixo parado sai da lista de Fixos (antes continuava aparecendo até o fim, e parecia que não apagava).
- O **ícone do app** ao lado do nome, no alto e na barra lateral, na cor escolhida em Aparência: as plaquinhas "R$".

## 1.14.0

- **Arrastar para o lado** troca de aba no celular, como no ResolvIA, no CronologIA e no InventarIA: Início ⇄ Caixa ⇄ Invest ⇄ Mais, com a tela nova entrando pelo lado. Não vale começando na borda da tela (é o Voltar do celular), num campo, num gráfico (lá o dedo mostra os valores), numa fileira que rola para o lado ou com uma janela aberta.

## 1.13.0

- **Monitores grandes (Full HD, 2K, 4K)**: o app aproveita a tela. Fica mais largo (a Carteira em três colunas) e tudo cresce na mesma proporção conforme a largura: letras, placar, botões e gráficos (15% a mais em Full HD, 35% em 2K, até 85% em 4K). As janelas cabem na tela e os gráficos continuam respondendo ao mouse no ponto certo.
- No computador, as plaquinhas do placar crescem para ocupar o painel.
- No celular e no tablet nada muda.

## 1.12.2

- **Placar do patrimônio chamativo**, como o caderno do ResolvIA: o painel inteiro na cor do app (Ouro, Azul, Vermelho, Verde…), com as plaquinhas por cima, o texto escuro e o **Por mês** num selo aceso. No tema claro as plaquinhas ficam brancas. Troque a cor em Mais › Aparência › Cor do app.

## 1.12.1

- **Placar do patrimônio mais colorido**: um brilho da cor do app no alto e um verde de dinheiro embaixo, a borda na cor do app, e os números de baixo com cor: **Seu** em verde, **Terceiros** em âmbar e **Por mês** na cor do app (sem investimentos: Entrou em verde e Saiu em vermelho). Vale no tema escuro e no claro.

## 1.12.0

- **Aporte aplicado vai para um investimento**: ao tocar em **Apliquei** num aporte (ou marcar **Aplicado** no formulário), escolha em qual investimento foi o dinheiro; o valor soma ao valor de hoje dele. É obrigatório quando há investimentos, e o app lembra a escolha nos próximos meses. Para cadastrar o compromisso, não precisa: o aporte novo nasce **A aplicar**.
- **Aplicar mais** no investimento: diga quanto aplicou e a data. Soma ao valor de hoje e, no caixa, dá baixa no aporte do mês a aplicar, lança um aporte à parte (escolhendo a conta) ou não lança nada.
- Na leitura por IA, "apliquei 3 mil no CDB" soma ao investimento que já existe (em vez de trocar o saldo) e lança a saída como aporte.

## 1.11.0

- **Ler com IA e Falar sem escolher antes**: saiu o "Gastos e recebimentos / Investimentos". A IA separa sozinha os gastos, os recebimentos, as contas a pagar e a receber e os investimentos, e o app mostra tudo na mesma janela para conferir, com um botão que salva o que estiver marcado.
- Cada lançamento vem com a situação que a IA leu: conta, boleto ou parcela a pagar e valor a receber ficam pendentes (com "a pagar" ou "a receber" na lista); o resto segue a data, e compras no cartão seguem a fatura. A situação **Automática** pode virar **Tudo pago** ou **Tudo pendente**.
- A imagem lida fica guardada com os investimentos salvos.
- No Uso da IA, essas leituras aparecem como **Ler com IA**.

## 1.10.2

- **Novo investimento sem leitura dobrada**: a área de imagens do fim virou **Imagens guardadas**, só para guardar o comprovante ou o print junto com o investimento. Quem lê com IA no investimento novo são os quadrinhos do alto (Colar mensagem e Imagem ou print). Ao editar um investimento, o **Ler** numa imagem guardada continua, para atualizar os campos.

## 1.10.1

- **Novo investimento e Nova despesa leem mensagem e imagem**, como nos outros apps: no alto, **Colar mensagem** (do WhatsApp ou do e-mail), **Imagem ou print** (na despesa, **Fatura, print ou foto**) e **Falar**. A IA lê e você confere antes de salvar.
- Com essas janelas abertas, **colar uma imagem** já abre a leitura por IA com ela; no computador, dá para **arrastar** a imagem ou o PDF para a janela.
- O investimento que veio da leitura por IA não mostra os quadrinhos de novo.

## 1.10.0

- **Aporte é um tipo de conta a pagar**: em **Adicionar › Aporte** (ou no botão **Aporte** da Nova despesa), o compromisso de aplicar nos seus investimentos, com valor, dia, de onde sai e se é todo mês. Fica *A aplicar* com o botão **Apliquei** e, como qualquer conta, aparece atrasado nos avisos e vai para as contas a pagar do CronologIA. No resumo do mês volta a entrar no "a pagar".
- **Invest › Evolução** não tem mais o campo para digitar o aporte: o aporte por mês da projeção é a soma dos aportes fixos das contas a pagar, com **Mudar o aporte** e **Outro aporte** (ou **Cadastrar aporte** quando não houver nenhum). O aporte que já existia continua igual, agora como conta a pagar do tipo Aporte.

## 1.9.1

- **Ler com IA no Adicionar**, como no ResolvIA e no CronologIA. No celular, o cabeçalho fica só com o microfone (e o olho no Início e no Caixa). No Caixa e no Invest, o **Adicionar** abre a despesa ou o investimento com os quadrinhos **Colar mensagem**, **Fatura, print ou foto** (ou **Print ou extrato**) e **Falar** no alto. No Início, o Adicionar continua com a opção **Ler com IA**. No computador, o Ler com IA segue no alto à direita.
- **O aporte mensal não é dívida**: fica *A aplicar* até você tocar em Apliquei, mesmo depois do dia. Não aparece mais como conta atrasada nem a vencer nos avisos (nem no número da barra lateral), não vai para as contas a pagar do CronologIA e, no resumo do mês, aparece como "a aplicar", separado do "a pagar".

## 1.9.0

- **No computador** (tela de 1000 pixels ou mais), como no ResolvIA, no CronologIA e no InventarIA:
  - uma **barra lateral** no lugar das abas de baixo, com Início, **Buscar** (tecla /), Caixa (com o número de contas atrasadas), Investimentos e Mais, os **bancos** e as **pessoas** com dinheiro aqui, cada um abrindo a Carteira já filtrada;
  - no alto à direita, **Falar**, esconder valores, **Ler com IA** e **Adicionar**;
  - seções direto na página, sem cartões, com título grande e ícone e uma linha entre as linhas;
  - no Início, os números ao lado do placar e, abaixo, dois grupos lado a lado (Caixa e dicas; terceiros e avisos);
  - no Caixa, a lista à esquerda e o mês (entrou, saiu, sobrou e saldo) à direita; as categorias em duas colunas;
  - na Carteira, a busca ao lado do filtro e os investimentos em duas colunas;
  - as janelas abrem no meio da tela.
  No celular e no tablet nada muda.
- **Exportar** como nos outros apps: uma linha por arquivo, cada uma com o que ele tem e o botão **Baixar** (Lançamentos e Investimentos em CSV, Dados completos em JSON, Tudo em ZIP e o Relatório de patrimônio).
- **Uso da IA** igual ao dos outros apps: os quadros aparecem zerados antes da primeira chamada, o Falar conta como um tipo próprio e a nota do Gemini fala dos erros 429 e da hora em que a cota volta.

## 1.8.0

- **Sensores no Home Assistant desligados por padrão**: o app só cria os sensores (`sensor.gerencia_patrimonio`, `_meu`, `_terceiros`, `_rendimento_mensal`, `_saldo_caixa`, `_entradas_mes`, `_saidas_mes` e `_ia_hoje`) se você ligar em Mais › Integrações. Desligado, apaga os que tinha criado. Quem atualizar fica com eles desligados até ligar.

## 1.7.0

- **Falar**: o microfone no alto de cada tela, à direita, como no CronologIA e no ResolvIA. Fale os gastos, recebimentos ou investimentos; o Home Assistant transcreve (fala para texto do assistente de voz, como o Home Assistant Cloud) e a IA separa os lançamentos para você conferir, com o que foi ouvido no alto.
- Na leitura por IA, o botão **Falar** ao lado de "Fatura em PDF, print ou foto".
- Em Mais › Integrações › Leitura por IA, a linha do Falar mostra se está pronto e com qual motor.

## 1.6.2

- **Versões anteriores**: o app fica só com as 3 mais recentes, como o ResolvIA, o CronologIA e o InventarIA. As mais antigas são apagadas na próxima cópia.

## 1.6.1

- Cada cartão ganhou um **ícone no cabeçalho**, como no CronologIA e no ResolvIA: Caixa do mês, Dicas de economia, Dinheiro de terceiros, Avisos, Fluxo de caixa mensal e Saldo em caixa.

## 1.6.0

- **Mais em abas**, no mesmo padrão do ResolvIA, do CronologIA e do InventarIA: Bancos, Caixa, Invest, Integrações, Dados, Aparência e Opções, com o ícone de cada seção num quadradinho.
- **Usar IA**: chave em Mais › Integrações que liga e desliga tudo o que usa IA, para todos os aparelhos.
- **Uso da IA**: chamadas de hoje, 7 dias e mês, gráfico por dia, tipos e últimas chamadas, e o sensor `sensor.gerencia_ia_hoje`.
- **Dados**: os backups da pasta `share/gerencia` aparecem na tela, com **Restaurar**; exportar com Tudo (ZIP), Lançamentos e Investimentos (CSV) e Dados (JSON); e "Onde ficam os dados".
- **Aparência**: tema em três botões com ícone e cor do app em etiquetas com nome.
- **Opções**: dicas de economia, prever o dia a dia e corrigir valores, valendo para todos os aparelhos.
- **Buscar** sempre à mostra na Carteira do Invest, com botão de limpar; no computador, a tecla / põe o cursor nele.
- Valores lidos pela IA no formato brasileiro ("15.000,00") agora entram certos.

## 1.5.0

- **Contas no CronologIA**: com o [CronologIA](https://github.com/diegozapella63/cronologia-ha) no mesmo Home Assistant, as contas a pagar, os fixos e as faturas do cartão aparecem na agenda e na tela Agora dele. O **Paguei** de lá dá baixa aqui, do mesmo jeito que o daqui (o fixo do mês fica pago, a fatura fica toda paga), e o modelo **Conta a pagar** de lá cria a conta aqui, única, todo mês ou todo ano.
- A ligação é automática: o GerencIA deixa o endereço e uma chave em `share/gerencia/integracao.json` e o CronologIA encontra sozinho. Dá para desligar em **Mais › Outros apps**, que também mostra o último acesso.
- Mudanças feitas por outro app aparecem na tela em até 20 segundos, sem recarregar.

## 1.4.0

- **Salário bruto com impostos na fonte**: no recebimento, cada imposto é uma porcentagem do bruto. Quando o salário entra, os impostos saem do caixa no mesmo dia, já pagos, na categoria Impostos e taxas.
- **Despesa ligada a um recebimento**: em "Como é pago", escolha "Descontado de: Salário" (para plano de saúde, coparticipação e outros). A baixa dela acontece junto com a do salário, no mesmo dia e na mesma conta.
- **Ler recibo com IA**: o app lê o recibo de pagamento em PDF ou foto, preenche o bruto e os impostos em %, sugere os outros descontos como despesas ligadas e confere com o líquido.
- Na lista do caixa, o salário mostra os descontos e o líquido logo abaixo; nos gráficos e nas categorias, o bruto entra e os descontos saem.
- Contas ligadas ao salário não aparecem como atrasadas nos avisos.

## 1.3.1

- Dicas de economia mostram a **economia real**: o desconto do plano anual menos o que o dinheiro das mensalidades renderia nos seus investimentos (o de liquidez diária que rende mais, já com IR). Se o rendimento empatar com o desconto, a dica não aparece.

## 1.3.0

- O **aporte por mês** da aba Invest agora entra no fluxo de caixa como saída fixa, todo mês, só para os seus investimentos (com o filtro De terceiros ele não conta).
- No gráfico de fluxo, os aportes aparecem em azul, separados das saídas, e o "Sobrou" já desconta o aporte.
- Botão **Apliquei** para confirmar o aporte do mês e **Mudar dia ou conta** na aba Invest.
- Nova categoria **Investimentos**.
- No Início, "Seu dinheiro em 1 ano" já conta o aporte mensal.
- O aporte que estava guardado só no navegador vai para o fluxo de caixa na primeira vez que o app abrir.

## 1.2.0

- **Dicas de economia** no Início: quando uma assinatura sua (Nabu Casa, Claude, Spotify, Microsoft 365 ou Deezer) tem plano anual mais barato, o app mostra quanto você economiza por ano. O preço é conferido na página oficial do serviço pela IA do Home Assistant, e a dica só aparece se o preço estiver escrito na página e o valor que você paga bater com um plano.
- Botão **Mudar para anual**: encerra o fixo mensal e cria um fixo anual no fluxo.
- Aviso de categoria bem acima da média dos 3 meses anteriores.
- Fixos **Todo ano**, para anuidade, IPVA, seguro e planos anuais. Aparecem no mês certo, também nos gráficos.
- O placar do Início fica claro no tema claro.

## 1.1.0

- Nova aba **Caixa** para o seu próprio dinheiro: despesas, recebimentos, lista do mês, fluxo de caixa mensal (entradas, saídas, o que sobrou e saldo) e categorias de gastos e recebimentos.
- **Fixos** com valor padrão: aparecem em todos os meses à frente, e cada mês pode ter um valor diferente sem mudar o padrão.
- **Cartão de crédito**: compras, parcelas e fixos no cartão entram no mês em que a fatura vence, também nos gráficos futuros. Fatura agrupada na lista, com botão para pagar.
- **Bancos com contas por pessoa**: no mesmo banco, diga quem tem conta e quem tem cartão, com dia de fechamento e de vencimento.
- Previsão do dia a dia no fluxo (média dos gastos variáveis dos últimos 3 meses), que dá para desligar.
- **Leitura por IA** com a IA do Home Assistant: fatura em PDF, prints, fotos de papel, prints e textos do WhatsApp para lançar gastos e recebimentos, e prints do banco para cadastrar investimentos. Tudo passa por uma conferência antes de lançar.
- Fotos nos investimentos e nos lançamentos.
- Os gráficos dos investimentos agora ficam dentro da aba Invest (Carteira, Evolução e Divisão).
- Avisos de fatura atrasada e contas que vencem em até 5 dias no Início.
- Novos sensores: saldo em caixa, entradas e saídas do mês.
- O app agora usa a pasta `media` do Home Assistant para mandar arquivos à IA. Se a atualização pedir, reinicie o app.

## 1.0.2

- No menu de baixo, a aba Investimentos agora se chama Invest.

## 1.0.1

- Início com placar de cotações: o patrimônio aparece em plaquinhas que viram, com seu dinheiro, o de terceiros e quanto rende por mês.
- Novo ícone com as plaquinhas "R$".
- Botão Adicionar dentro do menu de baixo, sem passar da borda.
- Opções do tema (Automático, Claro, Escuro) com espaço nas laterais.

## 1.0.0

- Primeira versão.
- Início com destaques, dinheiro de terceiros e avisos.
- Tipografia Barlow e Barlow Condensed embutida, como no InventarIA (funciona sem internet).
- Investimentos com valor, rendimento no padrão de mercado (% do CDI, CDI +, prefixado, IPCA +, Selic +, poupança, estimado) e indicador de dono.
- Gráficos de evolução (registrado e projetado) e do dinheiro atual por banco, dono, tipo e liquidez.
- Cadastro de bancos, índices do Banco Central, tema, cor do app, exportar, relatório, backup em `share/gerencia`, importar e versões anteriores.
- Sensores no Home Assistant.
