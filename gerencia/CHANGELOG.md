# Mudanças

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
