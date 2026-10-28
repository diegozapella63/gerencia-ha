# Mudanças

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
