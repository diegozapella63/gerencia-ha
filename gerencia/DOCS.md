# GerencIA

Seu dinheiro dentro do Home Assistant: o caixa do dia a dia (o que entra, o que sai, fixos, parcelas e faturas de cartão) e os investimentos (quanto você tem, onde está, de quem é e quanto vai ter daqui a alguns anos).

## Instalar

1. No Home Assistant, abra **Configurações > Apps > Loja de apps**, toque no menu, escolha **Repositórios** e cole `https://github.com/diegozapella63/gerencia-ha`.
2. Abra **GerencIA**, toque em **Instalar**, depois em **Iniciar**, e ligue **Mostrar na barra lateral**.

O app abre pela barra lateral (Ingress). Quem já está logado no Home Assistant usa direto, sem outra senha, e o app cumprimenta pelo nome.

## Telas

- **Início**: o placar com plaquinhas que viram, como num painel de cotações (patrimônio, ou o saldo em caixa se ainda não houver investimentos). Abaixo, o caixa do mês (entrou, saiu, a pagar), os destaques dos investimentos, o dinheiro de terceiros por pessoa e os avisos (fatura atrasada, contas que vencem em até 5 dias, vencimentos, valores desatualizados, índices).
- **Caixa**: seu próprio dinheiro, mês a mês.
  - *Lançamentos*: o mês escolhido dia a dia, com filtro Tudo, Entradas, Saídas e A pagar e receber. Compras no cartão aparecem juntas na fatura, no dia em que ela vence.
  - *Fluxo*: entradas e saídas por mês, o que sobrou e o saldo em caixa, com 12 meses atrás, 6 + 6 ou 12 à frente.
  - *Categorias*: para onde foi o dinheiro (gastos) e de onde veio (recebimentos) no mês.
- **Adicionar**: escolha despesa, recebimento, investimento ou ler com IA. Na aba Caixa ou Invest, o botão já sugere o que faz sentido ali.
- **Invest**: *Carteira* (lista com filtro Todos, Meus, Terceiros, por pessoa e por banco), *Evolução* (registrado e projeção de 1, 2, 5 ou 10 anos, com aporte mensal, IR e valor em dinheiro de hoje) e *Divisão* (por banco, dono, tipo ou liquidez).
- **Mais**: aparência (tema e cor), bancos e contas, categorias, fixos, leitura por IA, índices de mercado, cálculos, sensores e dados (exportar, relatório, backup, importar, versões).

## Caixa

### Fixos

Ao lançar uma despesa ou recebimento, escolha **Repetir: Todo mês**. O fixo aparece em todos os meses à frente, inclusive nos gráficos, com o valor padrão.

Quando o valor real de um mês for diferente (um salário maior, uma conta de luz menor), toque no lançamento, troque o valor e salve em **Só este mês**. O valor padrão continua o mesmo para os próximos meses. Para mudar o padrão, salve em **Todos os meses** ou abra **Mais > Fixos**. Ao apagar um fixo, você escolhe entre tirar só aquele mês ou parar dali para frente.

### Parcelas

Escolha **Repetir: Parcelado** e o número de parcelas. Cada parcela entra no mês certo, também nas faturas futuras.

### Cartão de crédito

Em **Mais > Bancos**, diga quem tem conta em cada banco e se a pessoa tem cartão, com o dia em que a fatura fecha e o dia em que vence. Exemplo: Nubank, Diego com cartão (fecha dia 3, vence dia 10) e Dessa com cartão (fecha dia 28, vence dia 5).

Uma compra no cartão entra no mês em que a fatura vence, não no dia da compra. Compras feitas no dia do fechamento ou depois vão para a fatura seguinte. Isso vale para compras avulsas, parcelas e fixos: uma assinatura fixa no cartão aparece nas faturas e no fluxo dos próximos meses. Para pagar a fatura inteira, toque nela na lista.

### Dia a dia

No gráfico de fluxo, os meses à frente somam os fixos, as parcelas e as faturas já lançadas. Com **Prever o dia a dia** ligado, eles somam também a média dos gastos variáveis dos últimos 3 meses (mercado, restaurante, combustível), para a previsão não ficar otimista demais.

### Acertar o saldo

Se o saldo do app não bater com o do banco, use **Ajustar saldo** na aba Caixa. O app lança a diferença como ajuste.

## Leitura por IA

O app usa a IA configurada no Home Assistant (ação `ai_task.generate_data`) para ler:

- fatura do cartão em PDF;
- print ou foto de papel (nota, recibo, extrato);
- print do WhatsApp ou texto colado da conversa;
- print do banco ou da corretora, para cadastrar investimentos.

Toque em **Adicionar > Ler com IA**, envie o arquivo ou cole o texto (dá para colar uma imagem direto). O app mostra o que encontrou para você conferir antes de lançar: desmarque o que não quiser, troque a categoria e escolha a conta ou o cartão. Em uma fatura, as próximas parcelas também podem ser lançadas.

Para funcionar, é preciso ter uma integração de IA com **Tarefa de IA** no Home Assistant (por exemplo Google Gemini, OpenAI ou Anthropic). Para ler imagem e PDF, a IA precisa aceitar anexos. Se ela não aceitar o PDF, o app tenta de novo mandando só o texto do arquivo. Em **Mais > Leitura por IA** dá para escolher qual IA usar e ver se ela está pronta.

Os arquivos enviados ficam em `media/gerencia/ia-temp` só durante a leitura.

## Imagens

Investimentos e lançamentos podem ter fotos (comprovante, print do banco). No formulário, toque em **Adicionar** na área de imagens. Numa imagem já anexada, o botão **Ler** usa a IA para preencher o formulário. As fotos ficam em `/data/fotos` e entram no backup.

## Rendimento no padrão de mercado

| Escolha | Exemplo | Como calcula |
|---|---|---|
| % do CDI | 110% do CDI | CDI × 110% |
| CDI + | CDI + 1,5% a.a. | (1 + CDI) × (1 + 1,5%) − 1 |
| Prefixado | 13,5% a.a. | taxa fixa |
| IPCA + | IPCA + 7% a.a. | (1 + IPCA) × (1 + 7%) − 1 |
| Selic + | Selic + 0,05% a.a. | (1 + Selic) × (1 + 0,05%) − 1 |
| Poupança | — | 0,5% ao mês + TR (com Selic acima de 8,5%) |
| Estimado | 10% a.a. | sua estimativa (ações, FIIs); não corrige o valor sozinho |
| Sem rendimento | — | o valor fica parado |

O valor de hoje é estimado a partir do último valor informado, contando dias úteis (base 252). Atualize o valor de vez em quando com o saldo do banco; o app avisa quando passa de 2 meses.

Os índices (CDI, Selic, IPCA 12 meses e TR) vêm do Banco Central a cada 12 horas. Dá para digitar à mão em **Mais > Índices de mercado**.

## Sensores

Com **Sensores no Home Assistant** ligado, o app cria:

- `sensor.gerencia_patrimonio` (com os atributos `seu`, `de_terceiros` e `investimentos`)
- `sensor.gerencia_meu`
- `sensor.gerencia_terceiros` (atributo `por_pessoa`)
- `sensor.gerencia_rendimento_mensal`
- `sensor.gerencia_saldo_caixa`
- `sensor.gerencia_entradas_mes` (atributo `a_receber`)
- `sensor.gerencia_saidas_mes` (atributos `a_pagar` e `atrasado`)

Eles são atualizados a cada alteração e a cada 15 minutos. Depois de reiniciar o Home Assistant, voltam em até 15 minutos.

## Dados e backup

- Tudo fica em `/data/gerencia.json`, que entra nos backups do Home Assistant. As fotos ficam em `/data/fotos`.
- **Criar backup** salva um `.zip` em `share/gerencia`, com os dados e as fotos.
- O app guarda uma versão a cada 10 minutos de uso (as 60 mais recentes) e antes de importar ou restaurar.
- **Exportar** gera CSV dos investimentos e dos lançamentos (abre no Excel, separado por ponto e vírgula), JSON e ZIP.

## Avisos

Projeções usam os índices de hoje mantidos no período, e a previsão do caixa usa os fixos, parcelas e médias lançados. São estimativas, não promessas.
