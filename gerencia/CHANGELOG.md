# Mudanças

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
