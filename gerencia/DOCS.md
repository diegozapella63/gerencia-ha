# GerencIA

Seu dinheiro dentro do Home Assistant: o caixa do dia a dia (o que entra, o que sai, fixos, parcelas e faturas de cartão) e os investimentos (quanto você tem, onde está, de quem é e quanto vai ter daqui a alguns anos).

## Instalar

1. No Home Assistant, abra **Configurações > Apps > Loja de apps**, toque no menu, escolha **Repositórios** e cole `https://github.com/diegozapella63/gerencia-ha`.
2. Abra **GerencIA**, toque em **Instalar**, depois em **Iniciar**, e ligue **Mostrar na barra lateral**.

O app abre pela barra lateral (Ingress). Quem já está logado no Home Assistant usa direto, sem outra senha, e o app cumprimenta pelo nome.

## Telas

- **Início**: o placar com plaquinhas que viram, como num painel de cotações (patrimônio, ou o saldo em caixa se ainda não houver investimentos). O placar fica na cor do app (Mais › Aparência › Cor do app), com as plaquinhas escuras no tema escuro e brancas no tema claro. Abaixo, o caixa do mês (entrou, saiu, a pagar), as dicas de economia, os destaques dos investimentos, o dinheiro de terceiros por pessoa e os avisos (fatura atrasada, contas que vencem em até 5 dias, vencimentos, valores desatualizados, índices).
- **Caixa**: seu próprio dinheiro, mês a mês.
  - *Lançamentos*: o mês escolhido dia a dia, com filtro Tudo, Entradas, Saídas e A pagar e receber. Compras no cartão aparecem juntas na fatura, no dia em que ela vence.
  - *Fluxo*: entradas e saídas por mês, o que sobrou e o saldo em caixa, com 12 meses atrás, 6 + 6 ou 12 à frente.
  - *Categorias*: para onde foi o dinheiro (gastos) e de onde veio (recebimentos) no mês.
- **Adicionar**: escolha despesa, recebimento, aporte, investimento ou ler com IA. Na aba Caixa ou Invest, o botão já sugere o que faz sentido ali.
- **Invest**: *Carteira* (lista com filtro Todos, Meus, Terceiros, por pessoa e por banco), *Evolução* (registrado e projeção de 1, 2, 5 ou 10 anos, com o aporte por mês das contas a pagar do tipo Aporte, IR e valor em dinheiro de hoje) e *Divisão* (por banco, dono, tipo ou liquidez).
- No celular, **arrastar para o lado** troca de aba: Início ⇄ Caixa ⇄ Invest ⇄ Mais (não vale começando na borda da tela, num gráfico ou numa fileira que rola para o lado).
- **Mais**, em abas no alto, como no ResolvIA, no CronologIA e no InventarIA:
  - *Bancos*: bancos, quem tem conta em cada um e quem tem cartão.
  - *Caixa*: fixos, categorias e dicas de economia.
  - *Invest*: índices de mercado.
  - *Integrações*: contas no CronologIA, leitura por IA (com a chave **Usar IA**), uso da IA e sensores no Home Assistant.
  - *Dados*: exportar, relatório, backup na pasta share (com os backups da pasta e Restaurar), importar, versões anteriores, onde ficam os dados e começar do zero.
  - *Aparência*: tema e cor do app.
  - *Opções*: dicas de economia no Início, prever o dia a dia no fluxo e corrigir valores pelo rendimento. Valem para todos os aparelhos.

### No computador

Com a tela larga (1000 pixels ou mais, como no ResolvIA, no CronologIA e no InventarIA), as abas de baixo viram uma **barra lateral**: Início, **Buscar** (ou a tecla /, que abre a Carteira com o cursor na busca), Caixa (com o número de contas atrasadas), Investimentos e Mais, e embaixo os **bancos** e as **pessoas** com dinheiro aqui, cada um abrindo a Carteira já filtrada. No alto à direita ficam **Falar**, esconder valores, **Ler com IA** e **Adicionar**. As seções ficam direto na página, com título grande; no Início, os destaques ficam ao lado do placar; no Caixa, o mês fica à direita da lista; na Carteira, os investimentos ficam em duas colunas. As janelas abrem no meio da tela. Em monitores grandes (Full HD, 2K, 4K) o app fica mais largo, com a Carteira em três colunas, e tudo cresce na mesma proporção, para aproveitar a tela. No celular e no tablet nada muda.

## Caixa

### Fixos

Ao lançar uma despesa ou recebimento, escolha **Repetir: Todo mês**. O fixo aparece em todos os meses à frente, inclusive nos gráficos, com o valor padrão.

Para o que vence uma vez por ano (anuidade, IPVA, seguro, plano anual), escolha **Todo ano**: o fixo aparece só no mês da data escolhida, todo ano.

Quando o valor real de um mês for diferente (um salário maior, uma conta de luz menor), toque no lançamento, troque o valor e salve em **Só este mês**. O valor padrão continua o mesmo para os próximos meses. Para mudar o padrão, salve em **Todos os meses** ou abra **Mais > Fixos**. Ao apagar um fixo, você escolhe entre tirar só aquele mês ou parar dali para frente.

### Salário bruto, impostos e descontos

Cadastre o salário pelo **valor bruto** (o que você tem a receber), de preferência como fixo (Repetir: Todo mês), e toque em **Descontos na fonte**.

- **Impostos na fonte**: cada imposto é uma porcentagem do bruto (INSS, imposto de renda, taxa administrativa…). Quando o salário entra, o imposto sai do caixa no mesmo dia, já pago, na categoria Impostos e taxas. Se o bruto mudar num mês, os impostos acompanham.
- **Plano de saúde e outros descontos**: cadastre como uma despesa normal (pode ser fixa) e, em **Como é pago**, escolha **Descontado de: Salário**. A baixa dela depende do salário: quando ele for confirmado, a despesa fica paga no mesmo dia e na mesma conta. Se o valor mudar num mês (uma coparticipação, por exemplo), edite só aquele mês.
- **Ler recibo com IA**: mande o PDF ou a foto do recibo (holerite, contracheque ou recibo de produção). O app preenche o bruto, transforma os impostos em porcentagem do bruto, sugere os outros descontos como despesas fixas ligadas e confere se o resultado bate com o líquido do recibo.

Na lista do caixa, o salário mostra o bruto e, logo abaixo, os descontos e o líquido. Os gráficos e as categorias mostram o bruto como entrada e os impostos e o plano como saídas.

### Parcelas

Escolha **Repetir: Parcelado** e o número de parcelas. Cada parcela entra no mês certo, também nas faturas futuras.

### Cartão de crédito

Em **Mais > Bancos**, diga quem tem conta em cada banco e se a pessoa tem cartão, com o dia em que a fatura fecha e o dia em que vence. Exemplo: Nubank, Diego com cartão (fecha dia 3, vence dia 10) e Dessa com cartão (fecha dia 28, vence dia 5).

Uma compra no cartão entra no mês em que a fatura vence, não no dia da compra. Compras feitas no dia do fechamento ou depois vão para a fatura seguinte. Isso vale para compras avulsas, parcelas e fixos: uma assinatura fixa no cartão aparece nas faturas e no fluxo dos próximos meses. Para pagar a fatura inteira, toque nela na lista.

### Aporte

O aporte é um **tipo de conta a pagar**: o compromisso de aplicar nos seus investimentos. Em **Adicionar › Aporte** (ou em Nova despesa, no botão **Aporte**), diga o valor, o dia, de onde sai e se é **Todo mês**. Ele entra no fluxo de caixa como as outras contas, na categoria Investimentos e em azul no gráfico, com **A aplicar** e o botão **Apliquei**. Se passar do dia sem aplicar, aparece como atrasado nos avisos e nas contas a pagar do CronologIA, como qualquer compromisso.

- O **aporte por mês da projeção**, em **Invest › Evolução**, é a soma dos aportes fixos (todo mês; os de todo ano contam divididos por 12). Ali não se digita: aparece o valor, com **Mudar o aporte** e **Outro aporte**. Sem aporte cadastrado, a projeção é sem aporte.
- Um aporte de uma vez só é um compromisso daquele mês e não entra no aporte por mês da projeção.
- Vale só para o seu dinheiro: com o filtro *De terceiros*, o aporte não entra na projeção.
- O aporte novo nasce **A aplicar**: para cadastrar o compromisso não precisa dizer o investimento.
- Para dar como aplicado (no **Apliquei** da lista, ou marcando **Aplicado** no formulário), diga **em qual investimento** foi o dinheiro e quanto: o valor soma ao valor de hoje desse investimento. O app lembra o investimento para os próximos meses. Se um mês for diferente, o padrão continua o mesmo.

**Aplicar mais num investimento**: ao abrir um investimento já cadastrado, toque em **Aplicar mais**, diga quanto e a data. O valor soma ao de hoje e, no caixa, dá para dar baixa no aporte do mês que estiver a aplicar, lançar como um aporte à parte (de qual conta saiu) ou não lançar. Na leitura por IA, "apliquei 3 mil no CDB do Inter" também soma ao CDB que já existe e lança a saída como aporte.

### Dia a dia

No gráfico de fluxo, os meses à frente somam os fixos, as parcelas e as faturas já lançadas. Com **Prever o dia a dia** ligado, eles somam também a média dos gastos variáveis dos últimos 3 meses (mercado, restaurante, combustível), para a previsão não ficar otimista demais.

### Acertar o saldo

Se o saldo do app não bater com o do banco, use **Ajustar saldo** na aba Caixa. O app lança a diferença como ajuste.

## Dicas de economia

O app procura assinaturas nos seus fixos e nas cobranças que se repetem nas faturas e confere se o plano anual sai mais barato. Hoje ele reconhece Nabu Casa (Home Assistant Cloud), Claude, Spotify, Microsoft 365 e Deezer.

A dica só aparece quando dá para confirmar na origem:

1. O app abre a página oficial de preços do serviço, a partir do seu Home Assistant.
2. A IA do Home Assistant lista os planos da página, com o preço mensal e o anual.
3. O app só aceita um preço se o trecho citado pela IA estiver escrito na página, com aquele número.
4. O valor que você paga precisa bater com o preço mensal de um único plano. Em planos em dólar, o app compara com o dólar do Banco Central, com folga para o IOF e o câmbio do cartão.

No Início, a dica mostra a **economia real** por ano: o desconto do plano anual menos o que o dinheiro das mensalidades renderia se ficasse investido. Para isso o app usa os seus investimentos e as taxas cadastradas: o que você tem com liquidez diária e rende mais, já com IR (o dinheiro sai mês a mês, então precisa poder ser resgatado). Sem nenhum com liquidez diária, usa a média dos seus investimentos; sem investimentos, 100% do CDI. Se o rendimento empatar com o desconto, a dica não aparece. A dica também mostra a fonte e a data em que o preço foi conferido. Em planos em dólar, a economia em reais é estimada pelo que você paga hoje. Toque em **Mudar para anual** depois de trocar o plano no site do serviço: o fixo mensal para e entra um fixo anual no seu fluxo. **Agora não** esconde a dica.

O app também avisa quando uma categoria fica bem acima da sua média dos 3 meses anteriores, pelos seus próprios lançamentos.

Os preços são conferidos de novo a cada 30 dias, ou na hora em **Mais > Dicas de economia > Conferir agora**, onde também aparece o motivo quando uma assinatura não vira dica (sem plano anual, valor que não bate com nenhum plano, página que não abriu).

## Leitura por IA

O app usa a IA configurada no Home Assistant (ação `ai_task.generate_data`) para ler:

- fatura do cartão em PDF;
- print ou foto de papel (nota, recibo, extrato);
- print do WhatsApp ou texto colado da conversa;
- print do banco ou da corretora, para cadastrar investimentos.

No Início, toque em **Adicionar › Ler com IA**. No Caixa e no Invest, o **Adicionar** abre a despesa ou o investimento com os quadrinhos **Colar mensagem** (do WhatsApp, do e-mail), **Fatura, print ou foto** (no investimento, **Imagem ou print** do app do banco) e **Falar** no alto, como no ResolvIA e no CronologIA. Com essa janela aberta, dá também para colar a imagem direto ou, no computador, arrastar a imagem ou o PDF para ela. No computador, o **Ler com IA** também fica no alto à direita. Envie o arquivo ou cole o texto (dá para colar uma imagem direto).

Não precisa dizer o que é: a IA separa sozinha os **gastos**, os **recebimentos**, as **contas a pagar e a receber** e os **investimentos**. Na mesma janela, o app mostra o que encontrou para você conferir: os lançamentos (desmarque o que não quiser, troque a categoria e escolha a conta ou o cartão) e os investimentos (os que já existem têm o valor atualizado). Um botão salva tudo o que estiver marcado. Em uma fatura, as próximas parcelas também podem ser lançadas.

A **Situação** começa em **Automática**: o que a IA viu como conta, boleto ou parcela a pagar, ou valor que ainda vai receber, fica pendente; o resto segue a data. Compras no cartão seguem a fatura. Dá para trocar para **Tudo pago** ou **Tudo pendente**.

Para funcionar, é preciso ter uma integração de IA com **Tarefa de IA** no Home Assistant (por exemplo Google Gemini, OpenAI ou Anthropic). Para ler imagem e PDF, a IA precisa aceitar anexos. Se ela não aceitar o PDF, o app tenta de novo mandando só o texto do arquivo. Em **Mais > Leitura por IA** dá para escolher qual IA usar e ver se ela está pronta.

Os arquivos enviados ficam em `media/gerencia/ia-temp` só durante a leitura.

## Falar

O microfone fica no alto de cada tela, à direita. Toque, fale e toque de novo quando terminar (até 2 minutos). Por exemplo: "gastei 45 no mercado hoje no cartão do Nubank e recebi 300 do João pelo Pix". O Home Assistant transcreve com a fala para texto do assistente de voz preferido (Configurações › Assistentes de voz; com o Home Assistant Cloud já vem pronta) e a IA separa sozinha os gastos, os recebimentos, as contas a pagar e a receber e os investimentos, como numa mensagem colada. Você confere antes de lançar, com o que foi ouvido no alto.

- O microfone só aparece com a IA ligada e um assistente de voz com fala para texto no Home Assistant. Em **Mais › Integrações › Leitura por IA** aparece se o Falar está pronto e com qual motor.
- O navegador precisa deixar usar o microfone: abra o Home Assistant pelo endereço com https (como o do Nabu Casa) ou pelo app do celular, e permita o microfone.
- O áudio vai direto para o Home Assistant e não fica guardado no app.

## Imagens

Investimentos podem guardar imagens (comprovante, print do banco, extrato): no formulário, toque em **Guardar** em **Imagens guardadas**. No investimento novo, essa área só guarda; quem lê com IA são os quadrinhos do alto (**Colar mensagem** e **Imagem ou print**), e a imagem lida também fica guardada. Ao editar um investimento, o botão **Ler** numa imagem guardada usa a IA para atualizar os campos. As imagens ficam em `/data/fotos` e entram no backup.

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

Os índices (CDI, Selic, IPCA 12 meses e TR) vêm do Banco Central a cada 12 horas. Dá para digitar à mão em **Mais › Invest › Índices de mercado**.

## Uso da IA

Em **Mais › Integrações**, a chave **Usar IA** liga e desliga tudo o que usa IA: Ler com IA, Ler recibo, Ler nas imagens e a conferência de preços das dicas. Desligada, os botões somem nos aparelhos todos.

Logo abaixo, **Uso da IA** mostra quantas chamadas o app fez hoje, nos últimos 7 dias e no mês, com um gráfico por dia, os tipos (ler lançamentos, ler investimentos, ler recibo, conferir preço, falar) e as últimas chamadas, no mesmo jeito do InventarIA, do ResolvIA e do CronologIA. O Home Assistant não informa tokens nem custo, então o app estima os tokens pelo tamanho do texto. O consumo exato fica no painel do provedor da IA.

## Sensores

Com **Sensores no Home Assistant** ligado, o app cria:

- `sensor.gerencia_patrimonio` (com os atributos `seu`, `de_terceiros` e `investimentos`)
- `sensor.gerencia_meu`
- `sensor.gerencia_terceiros` (atributo `por_pessoa`)
- `sensor.gerencia_rendimento_mensal`
- `sensor.gerencia_saldo_caixa`
- `sensor.gerencia_entradas_mes` (atributo `a_receber`)
- `sensor.gerencia_saidas_mes` (atributos `a_pagar` e `atrasado`)
- `sensor.gerencia_ia_hoje`: chamadas de IA de hoje, com erros, cota excedida, tokens estimados, por tipo, últimos 7 dias e mês

Eles são atualizados a cada alteração e a cada 15 minutos. Depois de reiniciar o Home Assistant, voltam em até 15 minutos.

## Contas no CronologIA

O [CronologIA](https://github.com/diegozapella63/cronologia-ha) é o app de agenda da mesma família. Com os dois instalados no mesmo Home Assistant:

- as contas a pagar, os fixos e as faturas do cartão aparecem no calendário do CronologIA, no dia do vencimento, e no card **Contas a pagar** da tela Agora (atrasadas primeiro);
- **Paguei** no CronologIA dá baixa aqui: o fixo do mês vira um lançamento pago, a fatura fica toda paga e uma conta avulsa fica paga. **Desfazer** volta para "a pagar";
- o modelo **Conta a pagar** do CronologIA cria a conta aqui: única (lançamento a pagar) ou fixa, todo mês ou todo ano.

Recebimentos, ajustes de saldo e despesas descontadas do salário não aparecem como contas. Os aportes aparecem, porque são compromissos (contas a pagar do tipo Aporte).

A ligação não pede configuração. Ao iniciar, o GerencIA grava em `share/gerencia/integracao.json` o endereço dele na rede interna dos apps e uma chave, e o CronologIA (que lê a pasta `share`) usa essa chave para chamar o GerencIA. Quem já consegue ler a pasta `share` também lê os backups do GerencIA que ficam lá, então a chave não abre nada novo. Para cortar a ligação, desligue **Mais › Outros apps › Contas no CronologIA**: o arquivo é apagado e a chave deixa de valer. O mesmo cartão mostra quando o CronologIA usou a ligação pela última vez.

Rotas usadas pelo CronologIA (todas com `Authorization: Bearer <chave>`):

| Método | Rota | O que faz |
| --- | --- | --- |
| GET | `/api/integracao/contas?de=AAAA-MM-DD&ate=AAAA-MM-DD` | Contas do período e as atrasadas dos últimos 2 meses: `{id, tipo: conta\|fixo\|fatura, descricao, valor, vencimento, pago, atrasada, categoria, conta}` e as categorias de gasto. |
| POST | `/api/integracao/pagar` | `{id, valor?}`: dá baixa. |
| POST | `/api/integracao/desfazer` | `{id}`: volta para a pagar. |
| POST | `/api/integracao/nova` | `{descricao, valor, vencimento, repete: nao\|mensal\|anual, categoria?}`. |

## Dados e backup

- Tudo fica em `/data/gerencia.json`, que entra nos backups do Home Assistant. As fotos ficam em `/data/fotos`.
- **Criar backup** salva um `.zip` em `share/gerencia`, com os dados e as fotos.
- O app guarda uma versão a cada 10 minutos de uso e antes de importar ou restaurar, e fica com as 3 mais recentes, como os outros apps.
- **Exportar** (Mais › Dados), uma linha por arquivo, cada uma com o que ele tem: **Lançamentos (CSV)**, um lançamento por linha, com os fixos e os descontos do salário; **Investimentos (CSV)**, um investimento por linha; **Dados completos (JSON)**; **Tudo (ZIP)**, com os dados, as duas planilhas e as imagens, que o Importar traz de volta; e o **Relatório de patrimônio**, para imprimir ou salvar em PDF. Os CSV abrem no Excel e no Google Planilhas (separados por ponto e vírgula).

## Avisos

Projeções usam os índices de hoje mantidos no período, e a previsão do caixa usa os fixos, parcelas e médias lançados. São estimativas, não promessas.
