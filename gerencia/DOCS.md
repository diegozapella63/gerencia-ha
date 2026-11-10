# GerencIA

Seu dinheiro dentro do Home Assistant: o caixa do dia a dia (o que entra, o que sai, fixos, parcelas e faturas de cartão) e os investimentos (quanto você tem, onde está, de quem é e quanto vai ter daqui a alguns anos).

## Instalar

1. No Home Assistant, abra **Configurações › Aplicativos › Loja de aplicativos**, toque no menu **⋮ › Repositórios** e cole `https://github.com/diegozapella63/gerencia-ha`.
2. Abra **GerencIA**, toque em **Instalar**, depois em **Iniciar**, e ligue **Mostrar na barra lateral**.

O app abre pela barra lateral. Quem já está logado no Home Assistant usa direto, sem outra senha, e o app cumprimenta pelo nome.

Na primeira vez, o Início mostra **Vamos começar**: cadastrar o salário e os gastos fixos, um investimento, ler uma fatura ou um print com IA, importar um backup ou **ver com dados de exemplo** (depois, **Apagar exemplo** tira tudo).

## Telas

- **Início**: o placar com plaquinhas que viram, como num painel de cotações (patrimônio, ou o saldo em caixa se ainda não houver investimentos). O patrimônio é só o seu: seus investimentos e os bens do InventarIA; o dinheiro de terceiros fica de fora. O placar fica na cor do app (Mais › Configurações › Aparência › Cor do app, ou a Cor do dia), com as plaquinhas escuras no tema escuro e brancas no tema claro. Abaixo, o caixa do mês (entrou, saiu, a pagar), as dicas de economia, os destaques dos investimentos e os avisos (fatura atrasada, contas que vencem em até 5 dias, vencimentos, valores desatualizados, índices).
- **Caixa**: seu próprio dinheiro, mês a mês.
  - *Lançamentos*: o mês escolhido dia a dia, com filtro Tudo, Entradas, Saídas e A pagar e receber (no mês de hoje, o que ficou sem pagar nos dois meses anteriores aparece primeiro; é para onde leva o aviso de contas atrasadas). Compras no cartão aparecem juntas na fatura, no dia em que ela vence. Como no CronologIA, o que já foi pago ou recebido fica **verde, com o visto**; o que falta tem um **círculo do lado**: toque nele para dar baixa (Paguei, Recebi, Apliquei).
  - *Fluxo*: entradas e saídas por mês, o que sobrou e o saldo em caixa, com 12 meses atrás, 6 + 6, 12 à frente ou **Outro** (por exemplo 24 atrás, 12 + 12 ou o número de meses que quiser, até 60 de cada lado). A média do que sobrou começa no primeiro mês com lançamentos.
  - *Categorias*: para onde foi o dinheiro (gastos) e de onde veio (recebimentos) no mês.
- **Adicionar**: no Início, escolha despesa, recebimento, aporte, ler com IA, investimento ou atualizar saldos. No Caixa, o botão abre direto a Nova despesa (com o filtro Entradas, o Novo recebimento); no Invest, o Novo investimento. Um lançamento avulso ou um investimento aberto tem **Duplicar**, que abre uma cópia para salvar como novo.
- **Invest**: o **Buscar** fica no alto (digitar nele abre a Carteira). *Carteira* (lista com filtro Todos, Meus, Terceiros, por pessoa e por banco), *Evolução* (registrado e projeção de 1, 2, 5 ou 10 anos, ou **Outro**, de 1 a 50 anos, com o aporte por mês das contas a pagar do tipo Aporte, IR e valor em dinheiro de hoje) e *Divisão* (por banco, dono, tipo ou liquidez).
- **Transferir entre investimentos**: abra um investimento e toque em **Transferir**. Escolha quanto (ou **Tudo**) e para qual investimento: o valor sai de um e soma no outro, sem mexer no caixa. Se passar tudo, dá para manter o investimento zerado na carteira ou tirá-lo.
- O **olho** no alto esconde os valores no Início, no Caixa e no Invest (cada aparelho lembra a escolha).
- No celular, **arrastar para o lado** troca de aba: Início ⇄ Caixa ⇄ Invest ⇄ Mais (não vale começando na borda da tela, num gráfico ou numa fileira que rola para o lado). Numa tela de Mais, arrastar para a direita volta ao menu.
- **Mais** é um menu, como no InventarIA: cada linha abre a sua tela, com **‹ Mais** no alto para voltar (o Voltar do celular também volta ao menu).
  - **Bancos**: bancos, quem tem conta em cada um, quem tem cartão e o nível da conta e do cartão.
  - **Caixa**: fixos, categorias e dicas de economia.
  - **Invest**: índices de mercado, oportunidades de investimento e, com bens, a perda de valor por categoria.
  - **Benefícios**: salas VIP, créditos e vantagens dos seus planos e cartões, com o que resta e quando renova, e as oportunidades: o que falta para ganhar mais.
  - **Relatório de patrimônio**: investimentos e bens por dono, e investimentos por banco, com **Todos**, **Meus** ou **De terceiros** no alto e o botão **Baixar PDF**.
  - **Configurações**, em abas:
    - *Integrações*, nesta ordem (a mesma dos outros apps): contas no CronologIA, bens no InventarIA, CorrerIA (WhatsApp, Claude e Gemini), **IA do Home Assistant** (com a chave **Usar IA**), uso da IA, faturas por e-mail, senhas dos PDFs e sensores no Home Assistant.
    - *Dados*: exportar, backup na pasta share (com os backups da pasta e Restaurar), importar, versões anteriores, onde ficam os dados e começar do zero.
    - *Aparência*: tema e cor do app. O tema (Sistema, Claro ou Escuro) vale só no aparelho em que foi escolhido; a cor vale para a casa toda. As 12 cores são as mesmas dos outros apps da família. Com **Cor do dia** (ligada por padrão), a cor muda todo dia, passando pelas cores do app em ordem (sem o Grafite): a mesma o dia todo e em todos os aparelhos, e com o app aberto ela troca à meia-noite. A cor do dia fica marcada; tocar numa cor desliga a Cor do dia e fica com ela, e ligar de novo volta para a do dia.
    - *Opções*: dicas de economia no Início, conferir as dicas sozinho e avisar no celular, prever o dia a dia no fluxo, corrigir valores pelo rendimento e o aviso das oportunidades de investimento no celular. Valem para todos os aparelhos.
  - **Sobre**, por último: quem faz o app (**CorrerIA Code**), os apps da família, cada um com uma linha e o link para o GitHub, e **Meu GitHub**.
- As **caixas de seleção** (como **Como é pago** ou **IA usada pelo app**) abrem uma janela de baixo para cima com as opções; a atual vem marcada. O Voltar do celular, o **X** ou tocar fora fecham sem mudar nada. No computador, a janela abre no meio da tela, e dá para escolher com as setas e Enter.

### No computador

Com a tela larga (1000 pixels ou mais, como no ResolvIA, no CronologIA e no InventarIA), as abas de baixo viram uma **barra lateral**: Início, **Buscar** (ou a tecla /, que abre a Carteira com o cursor na busca), Caixa (com o número de contas atrasadas), Investimentos e Mais, e embaixo os **bancos** e as **pessoas** com dinheiro aqui, cada um abrindo a Carteira já filtrada. No alto à direita ficam **Conversar com a IA**, **Falar**, esconder valores, **Ler com IA** e **Adicionar**. As seções ficam direto na página, com título grande; no Início, os destaques ficam ao lado do placar; no Caixa, o mês fica à direita da lista; na Carteira, os investimentos ficam em duas colunas. As janelas abrem no meio da tela. Em monitores grandes (Full HD, 2K, 4K) o app fica mais largo, com a Carteira em três colunas, e tudo cresce na mesma proporção, para aproveitar a tela. No celular e no tablet nada muda.

## Caixa

### Fixos

Para apagar um fixo, abra ele (no caixa ou em Mais › Caixa › Fixos) e toque na lixeira: **só o daquele mês** (ou ano), **parar a partir dali** (o que já foi lançado continua no caixa) ou **apagar o fixo e o que ele já lançou**. Um fixo parado sai da lista de Fixos.

**Desfazer**: depois de apagar (um lançamento, uma parcela, um fixo, um investimento, um benefício, um banco ou uma categoria), o aviso embaixo traz o **Desfazer** por alguns segundos: tudo volta como era, no mesmo lugar. O que mudou depois em outro aparelho continua.

Ao lançar uma despesa ou recebimento, escolha **Repetir: Todo mês**. O fixo aparece em todos os meses à frente, inclusive nos gráficos, com o valor padrão.

Para o que vence uma vez por ano (anuidade, IPVA, seguro, plano anual), escolha **Todo ano**: o fixo aparece só no mês da data escolhida, todo ano.

Quando o valor real de um mês for diferente (um salário maior, uma conta de luz menor), toque no lançamento, troque o valor e salve em **Só este mês**. O valor padrão continua o mesmo para os próximos meses. Para mudar o padrão, salve em **Todos os meses** ou abra **Mais › Caixa › Fixos**.

### Salário bruto, impostos e descontos

Cadastre o salário pelo **valor bruto** (o que você tem a receber), de preferência como fixo (Repetir: Todo mês), e toque em **Descontos na fonte**.

- **Impostos na fonte**: cada imposto é uma porcentagem do bruto (INSS, imposto de renda, taxa administrativa…). Quando o salário entra, o imposto sai do caixa no mesmo dia, já pago, na categoria Impostos e taxas. Se o bruto mudar num mês, os impostos acompanham.
- **Plano de saúde e outros descontos**: cadastre como uma despesa normal (pode ser fixa) e, em **Como é pago**, escolha **Descontado de: Salário**. A baixa dela depende do salário: quando ele for confirmado, a despesa fica paga no mesmo dia e na mesma conta. Se o valor mudar num mês (uma coparticipação, por exemplo), edite só aquele mês.
- **Ler recibo com IA**: mande o PDF ou a foto do recibo (holerite, contracheque ou recibo de produção). O app preenche o bruto, transforma os impostos em porcentagem do bruto, sugere os outros descontos como despesas fixas ligadas (num recebimento de uma vez só, como despesas no mesmo dia e na mesma conta) e confere se o resultado bate com o líquido do recibo.

Na lista do caixa, o salário mostra o bruto e, logo abaixo, os descontos e o líquido. Os gráficos e as categorias mostram o bruto como entrada e os impostos e o plano como saídas.

### Parcelas

Escolha **Repetir: Parcelado** e o número de parcelas. Cada parcela entra no mês certo, também nas faturas futuras.

### Cartão de crédito

Em **Mais › Bancos**, diga quem tem conta em cada banco e se a pessoa tem cartão, com o dia em que a fatura fecha e o dia em que vence. Exemplo: Banco Lua, Ana com cartão (fecha dia 3, vence dia 10) e Beto com cartão (fecha dia 28, vence dia 5).

Em cada conta dá para dizer também o **Nível da conta** (ex.: One, Black) e o **Próximo nível**, com quanto ele pede investido. O app soma o que a pessoa tem investido naquele banco (os investimentos escolhidos nessa conta; os de antes, sem conta escolhida, vão para a conta de quem é dono) e mostra quanto falta ("Você tem R$ 60.000 aqui; o Black pede R$ 100.000. Faltam R$ 40.000."). Na lista de Bancos aparece "faltam R$ 40 mil para Black".

Com cartão, a conta pede também o **Cartão** (o nível, ex.: Gold) e o **Limite**. Logo abaixo aparece quanto do limite já foi usado (as compras no cartão ainda não pagas) e quanto está disponível ("Usado R$ 1.200; disponível R$ 3.800."). Em **Tem cartão adicional?**, diga para quem é cada adicional e, se quiser, o limite dele; **Outro adicional** acrescenta mais um. A lista de Bancos mostra "adicional Beto".

Onde se escolhe um banco (no investimento, por exemplo), um banco com conta de mais de uma pessoa aparece uma vez para cada uma: **Banco Azul · Ana** e **Banco Azul · Beto**. O card do investimento e o Relatório de patrimônio mostram de quem é a conta (no relatório, embaixo do banco).

Uma compra no cartão entra no mês em que a fatura vence, não no dia da compra. Compras feitas no dia do fechamento ou depois vão para a fatura seguinte. Isso vale para compras avulsas, parcelas e fixos: uma assinatura fixa no cartão aparece nas faturas e no fluxo dos próximos meses. Para pagar a fatura inteira, toque nela na lista.

### Aporte

O aporte é um **tipo de conta a pagar**: o compromisso de aplicar nos seus investimentos. Em **Adicionar › Aporte** (ou em Nova despesa, no botão **Aporte**), diga o valor, o dia, de onde sai e se é **Todo mês**. Ele entra no fluxo de caixa como as outras contas, na categoria Investimentos e em azul no gráfico, com **A aplicar** e o botão **Apliquei**. Se passar do dia sem aplicar, aparece como atrasado nos avisos e nas contas a pagar do CronologIA, como qualquer compromisso.

- O **aporte por mês da projeção**, em **Invest › Evolução**, é a soma dos aportes fixos (todo mês; os de todo ano contam divididos por 12). Ali não se digita: aparece o valor, com **Mudar o aporte** e **Outro aporte**. Sem aporte cadastrado, a projeção é sem aporte.
- Um aporte de uma vez só é um compromisso daquele mês e não entra no aporte por mês da projeção.
- Vale só para o seu dinheiro: com o filtro *De terceiros*, o aporte não entra na projeção.
- O aporte novo nasce **A aplicar**: para cadastrar o compromisso não precisa dizer o investimento.
- Para dar como aplicado (no **Apliquei** da lista, ou marcando **Aplicado** no formulário), diga **em qual investimento** foi o dinheiro e quanto: o valor soma ao valor de hoje desse investimento. O app lembra o investimento para os próximos meses. Se um mês for diferente, o padrão continua o mesmo.

**Aplicar mais num investimento**: ao abrir um investimento já cadastrado, toque em **Aplicar mais**, diga quanto e a data. Se você só sabe o total que o banco mostra agora, escolha **Quanto tem agora**: o aporte é a diferença entre esse total e o valor de hoje. O valor soma ao de hoje e, no caixa, dá para dar baixa no aporte do mês que estiver a aplicar, lançar como um aporte à parte (de qual conta saiu) ou não lançar. Na leitura por IA, "apliquei 3 mil no CDB do Banco Sol" também soma ao CDB que já existe e lança a saída como aporte.

### Datas

Nenhuma data abre a janela do celular. Os atalhos ficam em botões: **Hoje**, **Amanhã**, **Sábado** e **Próx. semana** (num lançamento, **Hoje**, **Ontem** e **Amanhã**; numa data que não passa de hoje, como o **Valor em** de um investimento, **Hoje** e **Ontem**). **Outra data** abre o mês ali embaixo: ‹ e › trocam o mês, e tocar no nome do mês mostra os meses do ano (para um vencimento daqui a anos). Numa data opcional, **Sem data** tira a data.

### Dia a dia

No gráfico de fluxo, os meses à frente somam os fixos, as parcelas e as faturas já lançadas. Com **Prever o dia a dia** ligado, eles somam também a média dos gastos variáveis dos últimos 3 meses (mercado, restaurante, combustível), para a previsão não ficar otimista demais.

### Acertar o saldo

Se o saldo do app não bater com o do banco, use **Ajustar saldo** na aba Caixa. O app lança a diferença como ajuste. Saldo no vermelho: o campo mostra o sinal, e **Positivo** e **Negativo** trocam (o teclado numérico do celular não tem o "−").

## Dicas de economia

O app procura assinaturas nos seus fixos e nas cobranças que se repetem nas faturas e confere se o plano anual sai mais barato. Hoje ele reconhece Nabu Casa (Home Assistant Cloud), Claude, Spotify, Microsoft 365 e Deezer.

A dica só aparece quando dá para confirmar na origem:

1. O app abre a página oficial de preços do serviço, a partir do seu Home Assistant.
2. A IA do Home Assistant lista os planos da página, com o preço mensal e o anual.
3. O app só aceita um preço se o trecho citado pela IA estiver escrito na página, com aquele número.
4. O valor que você paga precisa bater com o preço mensal de um único plano. Em planos em dólar, o app compara com o dólar do Banco Central, com folga para o IOF e o câmbio do cartão.

No Início, a dica mostra a **economia real** por ano: o desconto do plano anual menos o que o dinheiro das mensalidades renderia se ficasse investido. Para isso o app usa os seus investimentos e as taxas cadastradas: o que você tem com liquidez diária e rende mais, já com IR (o dinheiro sai mês a mês, então precisa poder ser resgatado). Sem nenhum com liquidez diária, usa a média dos seus investimentos; sem investimentos, 100% do CDI. Se o rendimento empatar com o desconto, a dica não aparece. A dica também mostra a fonte e a data em que o preço foi conferido. Em planos em dólar, a economia em reais é estimada pelo que você paga hoje. Toque em **Mudar para anual** depois de trocar o plano no site do serviço: o fixo mensal para e entra um fixo anual no seu fluxo. **Agora não** esconde a dica (**Mostrar dispensadas**, em Mais › Caixa, traz de volta).

O app também avisa quando uma categoria fica bem acima da sua média dos 3 meses anteriores, pelos seus próprios lançamentos.

Com **Conferir sozinho** ligado (o padrão, em **Mais › Configurações › Opções › Dicas de economia**), o app procura as assinaturas nos fixos e faturas uma vez por dia e confere os preços de novo na página oficial **toda semana**, **a cada 15 dias** ou **todo mês** (o padrão), como você escolher, sempre a partir das 8h; a data da última verificação aparece no quadro. Uma assinatura nova é conferida logo. Desligado, só quando você toca em **Mais › Caixa › Dicas de economia › Conferir agora**, que confere na hora e onde também aparece o motivo quando uma assinatura não vira dica (sem plano anual, valor que não bate com nenhum plano, página que não abriu).

**Avisar no celular** (na mesma tela, desligado por padrão) manda um aviso quando aparece uma dica nova: só as que valem a pena (a mesma economia real do Início, de R$ 10 por ano ou mais) e que você não dispensou. Cada dica é avisada uma vez; se ela sumir e voltar, é avisada de novo. O aviso vai para as pessoas marcadas em **Quem recebe**, nos celulares ligados a cada uma no Home Assistant (**Configurações › Pessoas**, os aparelhos da pessoa com o app Home Assistant), como o aviso de prazos do ResolvIA. Ao ligar, já vem marcado quem está usando o app. **Testar no meu celular** manda um aviso agora para os seus celulares. O que aparece no **Conferir agora** você já está vendo, então não vira aviso.

## IA do Home Assistant

O app usa a IA configurada no Home Assistant (ação `ai_task.generate_data`) para ler:

- fatura do cartão em PDF;
- print ou foto de papel (nota, recibo, extrato);
- print do WhatsApp ou texto colado da conversa;
- print do banco ou da corretora, para cadastrar investimentos.

No Início, toque em **Adicionar › Ler com IA**. No Caixa e no Invest, o **Adicionar** abre a despesa ou o investimento com os quadrinhos **Colar mensagem** (do WhatsApp, do e-mail), **Escolher fotos ou PDF** (no investimento, **Escolher fotos** do app do banco), **Digitalizar com IA** e **Falar** no alto, como no ResolvIA e no CronologIA. **Digitalizar com IA** abre a câmera aqui dentro: fotografe até 4 páginas (a lanterna aparece quando o celular tem) e toque em **Pronto**; a IA já lê e mostra o que achou. A câmera só abre com o Home Assistant num endereço com https (como o do Home Assistant Cloud) ou no app do celular, com a câmera liberada; sem isso, dá para tirar ou escolher a foto pelo celular. **Voltar**, o X e o Cancelar voltam para a Nova despesa (ou o Novo investimento); depois de salvar, fecha tudo. Cada quadrinho abre só aquilo: **Colar mensagem** só tem o campo da mensagem; **Imagem** só a imagem. Aberto do **Novo investimento**, a IA só procura investimentos (nada vai para o caixa): um valor com um banco ou nome ("30.350 nubank") é o saldo dele, e o dono vem do texto ("tudo dinheiro da mãe"). Com essa janela aberta, dá também para colar a imagem direto ou, no computador, arrastar a imagem ou o PDF para ela. No computador, o **Ler com IA** também fica no alto à direita. Envie o arquivo ou cole o texto (dá para colar uma imagem direto).

Não precisa dizer o que é: a IA separa sozinha os **gastos**, os **recebimentos**, as **contas a pagar e a receber** e os **investimentos**. Na mesma janela, o app mostra o que encontrou para você conferir: os lançamentos (desmarque o que não quiser e, em cada linha, troque a categoria e a conta; se a conta tiver cartão, escolha débito ou crédito. A IA já sugere a conta do banco que viu em cada linha, e **Lançar todos em** muda todas de uma vez; se o banco que ela viu não está nos seus bancos, as linhas ficam sem conta e o botão **+** com o nome que ela viu (ex.: **+ Banco Coral**) cadastra o banco ali mesmo e já escolhe a conta nova) e os investimentos (os que já existem têm o valor atualizado). Um botão salva tudo o que estiver marcado. Em uma fatura, as próximas parcelas também podem ser lançadas.

A **Situação** começa em **Automática**: o que a IA viu como conta, boleto ou parcela a pagar, ou valor que ainda vai receber, fica pendente; o resto segue a data. Compras no cartão seguem a fatura. Dá para trocar para **Tudo pago** ou **Tudo pendente**.

Para funcionar, é preciso ter uma integração de IA com **Tarefa de IA** no Home Assistant (por exemplo Google Gemini, OpenAI ou Anthropic). Para ler imagem e PDF, a IA precisa aceitar anexos. Se ela não aceitar o PDF, o app tenta de novo mandando só o texto do arquivo. Em **Mais › Configurações › Integrações › IA do Home Assistant** dá para escolher qual IA usar e ver se ela está pronta.

### Faturas com senha

Muitos bancos mandam a fatura num PDF com senha (de costume, parte do CPF). O app abre o PDF com a senha antes de mandar para a IA, então a IA recebe o arquivo já aberto.

- Em **Mais › Configurações › Integrações › Senhas dos PDFs**, toque em **Adicionar senha** e cadastre as senhas de sempre, com um nome para lembrar de quem é (até 20). Cada fatura com senha tenta todas sozinha.
- Se nenhuma servir, a janela da leitura avisa e pede a **Senha do PDF**. Com **Guardar para as próximas faturas** (vem ligado), a senha que abriu entra na lista com o nome do arquivo.
- Depois de cadastrada, a senha não aparece mais: a lista mostra só o nome e o fim (••••45). Para trocar, apague e cadastre de novo.
- As senhas ficam só neste Home Assistant, em `/data/senhas_pdf.json`: entram no backup do Home Assistant, mas não nas exportações nem nos backups da pasta share.
- Abre as proteções comuns de PDF (RC4 e AES de 128 e 256 bits), com a senha de abrir ou a do dono. Se mesmo com a senha certa o app não conseguir abrir, ele avisa; mande um print da fatura.

### Faturas por e-mail

O app lê sozinho as faturas que chegam no seu e-mail, pelo Home Assistant. Nada é lançado sem você conferir.

1. No Home Assistant, adicione a integração **IMAP** (Configurações › Dispositivos e serviços › Adicionar integração › IMAP) com o seu e-mail. No Gmail: ative a verificação em duas etapas, crie uma **senha de app** na sua Conta Google e use servidor `imap.gmail.com`, porta `993`, o seu e-mail como usuário e a senha de app (16 letras, sem espaços). A busca padrão (os não lidos) serve.
2. No GerencIA, em **Mais › Configurações › Integrações › Faturas por e-mail**, ligue **Ler as faturas do e-mail**. A conta de e-mail do Home Assistant aparece logo abaixo.
3. Em **De quem**, adicione os remetentes das faturas: o endereço (`fatura@bancoazul.com.br`) ou só o fim dele (`bancoazul.com.br`). Sem nenhum, valem os e-mails com PDF e uma destas palavras no assunto ou no nome do arquivo: fatura, boleto, recibo, cobrança, nota fiscal, assinatura, mensalidade (ou *receipt*, *invoice*, *subscription*, *renewal*). Com algum, valem só os desses remetentes.

Quando chega um e-mail com PDF de um desses remetentes, o app pega o PDF, abre com as **Senhas dos PDFs** e manda para a IA. A fatura lida aparece nos **Avisos** do **Início** ("Fatura Banco Azul · Por e-mail · 4 lançamentos"). Toque para conferir, como na leitura por IA: as compras que parecem já lançadas vêm desmarcadas. **Lançar** grava e o aviso some; **Ignorar** fecha sem lançar.

- Se nenhuma senha cadastrada abrir o PDF, o aviso diz "o PDF tem senha": toque (o app tenta de novo as senhas cadastradas), digite a senha se pedir e leia. Com **Guardar para as próximas faturas**, ela entra nas senhas. Uma senha nova, cadastrada ou guardada na leitura, abre sozinha as outras faturas que esperavam.
- Se a leitura der erro (o Home Assistant não respondeu, por exemplo), tocar no aviso lê de novo.
- **Procurar faturas agora**, no mesmo cartão: o Home Assistant só avisa os e-mails que chegam depois de ligar; para as faturas que já estão na caixa de entrada, o botão abre os 30 e-mails mais novos (de cada conta) e segue com os que têm PDF como se tivessem acabado de chegar: os de fatura são lidos e esperam a conferência no Início (sem aviso no celular) e os outros ficam em Recebidos. Pode levar uns minutos; o botão mostra quantos já abriu. Os que já estavam no app não entram de novo: o mesmo e-mail é reconhecido pela conta, pelo remetente, pela data e pelo assunto, mesmo que tenha chegado pelo aviso do Home Assistant.
- **Recebidos**, no mesmo cartão, mostra os últimos 5 e-mails com PDF: **Para conferir**, **Precisa da senha**, **Lançada**, **Ignorada**, **Não é fatura**... Os que não pareciam fatura (ou foram ignorados) têm **Ler**.
- O **⋯** de cada e-mail recebido diz o que fazer com aquele remetente (o endereço, ou **Todo o** domínio): **Normal** (como os outros), **É um fixo** (lido sempre, mesmo fora do **De quem** e sem as palavras no assunto; na conferência, a despesa vai para o fixo do mês, na conta e na categoria dele, e um mês já lançado só muda o valor; escolha o fixo ou crie um **Novo fixo**, que fica com o valor da primeira leitura) ou **Nunca** (os e-mails dele não entram, mesmo com fatura ou boleto no assunto; os que já estavam somem dos Recebidos e do Início). As regras aparecem em **Remetentes** (as de **Nunca considerar** no fim, recolhidas) e saem pela lixeira.
- Numa fatura de cartão, o pagamento da própria fatura (Pagamento online, pagamento recebido, débito automático) não é recebimento: fica em **Pagamentos desconsiderados**, no fim da conferência, desmarcado. Marque se quiser lançar.
- Na conferência (de uma fatura, print ou foto), cada despesa tem um **Fixo**: ligue a linha a uma despesa fixa que já existe (o mês dela recebe o valor, sem lançamento solto) ou crie um **Novo fixo** a partir dela (o mesmo nome, valor, categoria e conta, todo mês no dia da compra, a partir daquele mês). **Não é fixo** desfaz. As parcelas não têm essa opção.
- Uma fatura com muitos lançamentos pode passar do limite de tamanho da resposta da IA (no Claude: "reached the output token limit"). O app tenta de novo pedindo uma resposta curta; se ainda passar, aumente o máximo de tokens da resposta na tarefa de IA do Claude (Configurações › Dispositivos e serviços › Anthropic › a tarefa de IA › engrenagem, com as configurações recomendadas desligadas). O raciocínio da IA também gasta desse limite.
- **Avisar no celular**, em **Mais › Configurações › Opções › Faturas por e-mail** (vem desligado): quando uma fatura fica pronta para conferir, quem você marcar em **Quem recebe** ganha um aviso nos celulares ligados a essa pessoa no Home Assistant.
- O Home Assistant avisa um e-mail por vez (o mais novo da busca). Se chegarem dois juntos, o mais antigo pode não aparecer: leia pelo **Ler com IA**.
- Os e-mails ficam em `/data/emails.json` e os PDFs em `/data/emails`, só os últimos 30 e fora das exportações. Lançada ou ignorada, a cópia do PDF é apagada.
- O mesmo e-mail não entra duas vezes (o Home Assistant manda o último de novo quando reinicia).

### Atualizar saldos

Quando chega uma listinha com o valor de agora de cada investimento (por exemplo, de um terceiro, no WhatsApp: "Banco Lua, valor atualizado, R$ 500 / Serasa, valor atualizado, R$ 600"), use **Atualizar saldos**: em **Adicionar** (no Início), no **Novo investimento** (o link embaixo dos quadrinhos) ou na **Carteira › Terceiros**, que já abre com a pessoa escolhida. Diga de quem são (Meus, uma pessoa ou Vários), cole a lista ou mande o print. A IA acha cada investimento pelo banco, pelo nome e pelo dono, e a conferência mostra, para cada um, o **aporte**: a diferença entre o saldo novo e o valor de hoje (ou o resgate, se for menos), com o total no alto. Dá para trocar para qual investimento vai cada linha; o que não tiver correspondente vira um investimento novo da pessoa. **Revisar antes** corrige os dados de uma linha sem sair da conferência. **Atualizar** grava os saldos novos de uma vez.

Os arquivos enviados ficam em `media/gerencia/ia-temp` só durante a leitura.

## Falar

O microfone fica no alto de cada tela, à direita. Toque, fale e toque de novo quando terminar (até 2 minutos). Por exemplo: "gastei 45 no mercado hoje no cartão do Banco Lua e recebi 300 do João pelo Pix". O Home Assistant transcreve com a fala para texto do assistente de voz preferido (Configurações › Assistentes de voz; com o Home Assistant Cloud já vem pronta) e a IA separa sozinha os gastos, os recebimentos, as contas a pagar e a receber e os investimentos, como numa mensagem colada. Você confere antes de lançar, com o que foi ouvido no alto.

- O microfone só aparece com a IA ligada e uma fala para texto no Home Assistant. Em **Mais › Configurações › Integrações › IA do Home Assistant** aparece se o Falar está pronto.
- **Fala para texto**: uma lista, como a da IA, com as falas para texto do Home Assistant (Home Assistant Cloud, Google AI STT, faster-whisper…). No **Padrão do Home Assistant** fica a que o Home Assistant usa no assistente de voz principal (Configurações › Assistentes de voz). Se a escolhida sumir do Home Assistant, o app volta ao padrão.
- São duas peças: a **fala para texto** só transforma a voz em texto; quem entende o texto é a **IA usada pelo app**, a mesma de Ler com IA. Trocar uma não muda a outra.
- O navegador precisa deixar usar o microfone: abra o Home Assistant pelo endereço com https (como o do Home Assistant Cloud) ou pelo app do celular, e permita o microfone.
- O áudio vai direto para o Home Assistant e não fica guardado no app.

## Conversar com a IA

O balão ao lado do microfone abre uma conversa com a IA, a qualquer momento e em qualquer tela. Ela vê os seus dados (caixa, contas a pagar, fixos, lançamentos recentes, investimentos e patrimônio) e o que está na tela aberta, então dá para perguntar "quanto gastei com mercado este mês?", "o que vence esta semana?" ou "quanto rende a minha carteira?". Também conversa sobre outros assuntos.

Com a conversa vazia, aparecem sugestões para a tela aberta: é só tocar.

E ela faz, sempre pedindo confirmação: peça para **lançar** um gasto ou recebimento ("gastei 45 no mercado no cartão"), **pagar** uma conta que já está no app ("paguei a luz, 190 reais"; vale também para o fixo do mês e a fatura do cartão) ou **atualizar um saldo** e **aplicar** num investimento ("apliquei 500 na reserva"). A resposta traz um cartão com o que vai ser feito:

- **Confirmar** faz na hora, com as mesmas regras da leitura por IA (conta, categoria, cartão e fatura, parcelas). Se parecer repetido, abre a conferência antes.
- **Editar** abre a janela de sempre (a conferência da leitura por IA ou o Confirmar pagamento) por cima da conversa; salvar ou o Voltar do celular voltam para ela.

O microfone dentro da conversa dita a pergunta (precisa de uma fala para texto no Home Assistant, como no Falar). A conversa fica guardada no app (as últimas 60 mensagens): fechou, abre de onde parou; **Nova conversa**, no alto, recomeça do zero. O Voltar do celular fecha a conversa. Usa a mesma IA de Ler com IA e respeita a chave **Usar IA**: desligada, o balão some.

## Imagens

Investimentos podem guardar imagens (comprovante, print do banco, extrato): no formulário, toque em **Guardar** em **Imagens guardadas**. Essa área só guarda; no investimento novo, quem lê com IA são os quadrinhos do alto (**Colar mensagem** e **Escolher fotos**), e a imagem lida também fica guardada. Ao editar um investimento também: **Guardar** só guarda a imagem, sem IA. Para a IA ler, use **Ler com IA** no Adicionar. As imagens ficam em `/data/fotos` e entram no backup.

## Rendimento no padrão de mercado

| Escolha | Exemplo | Como calcula |
|---|---|---|
| % do CDI | 110% do CDI | CDI × 110% |
| CDI + | CDI + 1,5% a.a. | (1 + CDI) × (1 + 1,5%) − 1 |
| Prefixado | 13,5% a.a. | taxa fixa |
| IPCA + | IPCA + 7% a.a. | (1 + IPCA) × (1 + 7%) − 1 |
| Selic + | Selic + 0,05% a.a. | (1 + Selic) × (1 + 0,05%) − 1 |
| Poupança | — | 0,5% ao mês + TR (com Selic acima de 8,5%) |
| Estimado | 10% a.a. | sua estimativa (ações, FIIs, ouro); não corrige o valor sozinho |
| Sem rendimento | — | o valor fica parado |

**Dinheiro em espécie**: escolha o tipo Dinheiro; o formulário só pede nome e valor (sem banco, sem rendimento).

**Ouro**: escolha o tipo Ouro. Ele vem com Estimado de 10% a.a.; troque pela valorização que você espera. Com Descontar IR, 15% sobre o ganho. Atualize o valor com a cotação de vez em quando (ou pelo Atualizar saldos).

O valor de hoje é estimado a partir do último valor informado, contando dias úteis (base 252). Atualize o valor de vez em quando com o saldo do banco; o app avisa quando passa de 2 meses.

Os índices (CDI, Selic, IPCA 12 meses e TR) vêm do Banco Central a cada 12 horas. Dá para digitar à mão em **Mais › Invest › Índices de mercado**.

## Benefícios

Em **Mais › Benefícios**, o que você ganha por pagar um plano ou ter um cartão: salas VIP, créditos, seguro viagem… Cada benefício fica ligado ao que o sustenta: um **fixo** (a assinatura) ou uma **conta** de Mais › Bancos (com o nível da conta ou do cartão), e a lista fica agrupada assim. Em **De onde vem**, toque no fixo ou na conta (os botões ficam na própria tela, como na escolha do banco).

- **Tipo**: **Quantidade** (ex.: 6 salas VIP por ano; **Usei 1** desconta e mostra "restam 5"), **Saldo** (ex.: US$ 100 de créditos por mês; **Usei** pergunta quanto) ou **Vantagem** (sem contagem).
- **Renova** todo mês, todo ano ou não renova, a partir da data em **Renova a partir de** (o aniversário do plano ou do cartão): no dia, o que foi usado zera. **Vale até** (opcional) é o último dia do benefício.
- Toque no nome para editar: aparecem os usos do período, e dá para tirar um que foi lançado por engano.
- **Identificar benefícios** (só com a IA ligada): em **Editar banco**, em cada conta, e no fim de um gasto fixo (uma assinatura, por exemplo), abre o **Ler com IA** já com a conta ou o fixo em **De onde vêm**; embaixo do botão, quantos benefícios ele já tem. Ao cadastrar, volta para o banco ou para o fixo.
- **Ler com IA** (só com a IA ligada): em vez de cadastrar um por um, mande um print ou uma foto da tela de benefícios do app do banco, o PDF do regulamento, cole o texto ou o endereço da página oficial do cartão ou do plano. Escolha **De onde vêm** (o fixo ou a conta e o cartão): numa página com vários cartões ou níveis, a IA fica só com os do seu. Da página e do texto só entra o que está escrito lá, e a quantidade ou o valor precisa estar no trecho (senão o benefício entra como vantagem, sem o número); preço e anuidade não contam. Na conferência, desmarque o que não quiser (o que já está cadastrado vem desmarcado) e toque em **Cadastrar**: cada um renova a partir de hoje, e dá para ajustar depois. Páginas que só mostram os benefícios dentro do app do banco, ou depois do login, não dão para ler: mande um print.
- **No Início**: "Benefício para usar" quando o que sobrou vence em até 30 dias (antes de renovar ou da validade), e "Benefício que vai parar" quando o fixo acabou ou a conta saiu de Bancos.
- Os fixos (Mais › Caixa) e os bancos mostram quantos benefícios têm.

### Oportunidades (nos Benefícios)

Embaixo dos benefícios, **Oportunidades** mostra o que falta para ganhar mais, do mais perto para o mais longe:

- **Investindo**: ter um valor no banco (ex.: anuidade grátis com R$ 50 mil investidos). Conta o que a pessoa da conta tem investido no banco, como no card do investimento: "faltam R$ 5.000 · tem R$ 45 mil". O **Próximo nível** de cada conta (Mais › Bancos › Editar banco) entra sozinho; tocar nele abre o banco.
- **Gastando**: gastar um valor por mês no cartão (ex.: sala VIP gastando R$ 3 mil por mês). Conta a média das faturas dos 3 meses antes deste, sem o pagamento da própria fatura (um estorno desconta): "faltam R$ 500 · média R$ 2.500". O valor por ano vira por mês.
- **Outro plano**: um plano mais caro da mesma assinatura (ex.: o de 2 TB por R$ 130 em vez de R$ 110): "+R$ 20,00 por mês".
- O que já dá fica no fim, com **Já dá**. Sem como saber, a linha diz o porquê (a conta não tem cartão, sem faturas nos últimos 3 meses).
- **Cadastrar oportunidade**: o que ganha, como (Investindo, Gastando ou Outro plano), a conta, o cartão ou a assinatura, e o valor; embaixo, quanto você tem e quanto falta. Toque numa para mudar ou apagar.
- **Ler com IA** e **Identificar benefícios** também acham as oportunidades na página, no print ou no texto do banco ou do plano: elas vêm na conferência, embaixo dos benefícios, em **Oportunidades**. Da página e do texto só entra o que está escrito lá, com o valor no trecho. Numa assinatura, a IA sabe quanto você paga e traz só os planos mais caros.
- Na **Conversa**, a IA também vê as oportunidades e quanto falta para cada uma.

## Oportunidades de investimento

Em **Mais › Invest › Oportunidades**, as taxas de hoje do **Tesouro Direto** (Selic, Prefixado e IPCA+; Renda+ e Educa+ ficam de fora), separadas em três famílias: **Pós-fixado** (em % do CDI), **Prefixado** (% ao ano) e **IPCA+**. Em cada família aparecem as 3 melhores (**Ver mais** mostra todas).

- **Alvo**: ao lado do nome de cada família, a taxa que você quer (ex.: 120% do CDI, 15% ao ano, IPCA + 7,5%). O que chega ao alvo fica verde, com **No alvo**. Sem alvo, vale o que rende mais que o melhor dos seus investimentos daquela família (**Melhor que os seus**); sem investimento seu na família, nada.
- **Como um CDB**: LCI e LCA não pagam IR, então aparecem também como o CDB que renderia o mesmo depois do IR do prazo até o vencimento (sem vencimento, 15%). Ex.: uma LCA de 94% do CDI que vence em pouco mais de um ano vale um CDB de 113,9%. O Tesouro Selic aparece também em % do CDI. O alvo compara com esse valor.
- **Quanto rende** (em verde, em cada linha): quanto o valor de **Simular com** (R$ 10 mil de início) rende em 1 ano, já sem o IR (o de um CDB de 1 ano; LCI e LCA pelo equivalente em CDB), e a diferença para o seu melhor investimento da mesma família (os seus, não os de terceiros). Uma oferta de um banco onde você marcou um próximo nível (Mais › Bancos) mostra quanto falta para ele.
- **Ofertas dos seus bancos** (só com a IA ligada): o app lê a página de ofertas de cada banco cadastrado em **Mais › Bancos**. **Mercado Pago**, **Nubank**, **PagBank** e **Inter** já têm página pronta, achada pelo nome do banco; para outro banco, coloque o endereço em **Página de ofertas**, no próprio banco (no Nubank e nos outros com página pronta, o campo diz **Automática**, e um endereço ali vale no lugar da pronta). Nas Oportunidades, "Ofertas dos seus bancos" mostra quantas ofertas cada um tem, e "Sem página de ofertas" mostra os bancos sem página: tocar no nome abre o banco. A IA lista as ofertas; cada taxa só vale se estiver escrita na página. Entram CDB, RDB, LC, LCI, LCA e as caixinhas e cofrinhos das contas, com a condição de cada taxa (ex.: "clientes Ultravioleta"); fundos, debêntures, CRI e CRA ficam de fora. Páginas que só mostram as taxas dentro do app do banco, ou depois do login, não dão para ler.
- As taxas do Tesouro vêm da tabela **Investir** do site do Tesouro Direto (se ela não abrir, dos dados abertos do Tesouro Transparente, do dia útil anterior) e valem uma hora; as páginas são lidas uma vez por dia. **Conferir agora** busca tudo de novo.
- **Avisar no celular** (Mais › Configurações › Opções › Oportunidades de investimento; vem desligado): no **Horário** escolhido (10:00 de início), todo dia ou **a cada** tantos dias (de 1 a 30), o que chegou ao alvo (ou, sem alvo, rende mais que os seus) vai para o celular de quem foi escolhido em **Quem recebe**, como o aviso de prazos do ResolvIA (os celulares ligados a cada pessoa no Home Assistant). Cada oportunidade é avisada uma vez; de novo só se a taxa subir (0,10 no prefixado e no IPCA+, 1 ponto no % do CDI) ou se ela sair e voltar ao alvo. **Testar no meu celular** manda agora para o seu celular. Tocar no aviso abre as oportunidades.
- Não é recomendação: confira prazo, liquidez e garantia (FGC até R$ 250 mil por banco e instituição).

## Recolhidos no fim

O que está parado (encerrado, vencido ou ignorado de propósito) fica numa seção fechada no fim, com a contagem, que abre num toque: **Nunca considerar** e **Ignorados** (Faturas por e-mail), **Pagamentos desconsiderados** (na conferência), **Encerrados** (Mais › Caixa › Fixos e Mais › Benefícios). Ao sair do app, elas voltam a ficar fechadas.

## Uso da IA

Em **Mais › Configurações › Integrações**, a chave **Usar IA** liga e desliga tudo o que usa IA: Ler com IA, Ler recibo, Falar, Conversar com a IA, Atualizar saldos e a conferência de preços das dicas. Desligada, os botões somem nos aparelhos todos, e as dicas de plano anual também (o preço é conferido pela IA); as dicas de categoria acima da média continuam, porque não usam IA.

Logo abaixo, **Uso da IA** mostra quantas chamadas o app fez hoje, nos últimos 7 dias e no mês, com um gráfico por dia, os tipos (ler lançamentos, ler investimentos, ler recibo, atualizar saldos, conferir preço, falar, conversa) e as últimas chamadas (a que deu erro mostra o motivo, embaixo dela), no mesmo jeito do InventarIA, do ResolvIA e do CronologIA. O Home Assistant não informa tokens nem custo, então o app estima os tokens pelo tamanho do texto. O consumo exato fica no painel do provedor da IA.

## Sensores

Com **Sensores no Home Assistant** ligado (em Mais › Configurações › Integrações; vem desligado), o app cria:

- `sensor.gerencia_patrimonio`: o seu patrimônio, sem o dinheiro de terceiros (atributos `seu`, `de_terceiros`, `com_terceiros`, `investimentos` e, com o InventarIA, `com_bens`)
- `sensor.gerencia_meu`
- `sensor.gerencia_terceiros` (atributo `por_pessoa`)
- `sensor.gerencia_rendimento_mensal`
- `sensor.gerencia_saldo_caixa`
- `sensor.gerencia_entradas_mes` (atributo `a_receber`)
- `sensor.gerencia_saidas_mes` (atributos `a_pagar` e `atrasado`)
- `sensor.gerencia_ia_hoje` (com a IA ligada): chamadas de IA de hoje, com erros, cota excedida, tokens estimados, por tipo, últimos 7 dias e mês
- `sensor.gerencia_bens` (com o InventarIA): os bens da casa, já com a perda de valor (atributos `registrado`, `perde_por_ano` e `itens`)

Eles são atualizados a cada alteração e a cada 15 minutos. Depois de reiniciar o Home Assistant, voltam em até 15 minutos.

## Bens no InventarIA

Com o **InventarIA** (1.16.0 ou mais novo) no mesmo Home Assistant, os valores dos itens dele entram no patrimônio como **bens**: o placar do Início mostra o total, com **Investido** e **Bens** separados, e os destaques têm **Bens da casa**, que abre os valores por categoria e por cômodo. Na **Carteira**, em Todos e em Meus, um cartão só de leitura mostra o total dos bens do InventarIA (o valor muda lá); a janela Bens da casa mostra quanto valem em 1, 5 e 10 anos. Para ver só os investimentos, ligue **Ocultar bens e imóveis** na Evolução ou na Divisão (como o Descontar IR, começa desligado toda vez que o app abre). No Invest, em Tudo e em Só o meu, os bens também aparecem na **Divisão** (uma fatia à parte) e na **Evolução** (somados no Hoje e no Em N anos, com a linha Bens perdendo valor e a coluna Bens na tabela por ano).

Cada categoria **perde** ou **valoriza** uma % por ano (de costume, veículos perdem 15%, eletrônicos 20%, móveis 10%, cozinha 10%, decoração 5%, roupas 25%; imóveis mantêm o valor), contada desde a data em que o valor do item mudou no InventarIA. Em **Mais › Invest › Valor dos bens por ano**, cada categoria tem **Perde** ou **Valoriza** e a % ao lado: um imóvel que valoriza 5% ao ano fica com Valoriza e 5. O Início, a Carteira, a Divisão e a Evolução mostram quanto os bens perdem ou ganham; em **Mais › Configurações › Integrações › Bens no InventarIA** dá para desligar **Somar os bens**.

**No InventarIA**: as mesmas taxas vão para lá. Ligando **Valor de hoje** no InventarIA (**Mais > Configurações > Integrações > GerencIA**, 1.46.0 ou mais novo), o patrimônio, os cômodos e o relatório de lá mostram o valor de hoje, com a mesma conta daqui. Mudou uma taxa aqui, muda lá.

**Bens de terceiros, ou seus sem o InventarIA**: em **Adicionar › Investimento**, tipo **Bens**. Só nome, valor e categoria (por exemplo, "Carro da mãe", Veículos): um total, sem cômodos. Ele perde a taxa da categoria por ano, a mesma da tabela. Os de terceiros não entram no seu patrimônio; os seus somam na coluna Bens do placar. Se quiser, **Separar o valor por categoria** divide o total pelas categorias (Imóveis, Veículos, Eletrônicos, Móveis…), e cada parte perde a taxa da sua. As categorias são as do InventarIA (as que você renomeou ou criou lá aparecem aqui), mais Imóveis e Veículos; uma categoria nova começa perdendo 10% ao ano, e dá para trocar para Valoriza na mesma tabela.

**Imóveis**: começam em 0% (mantêm o valor). A construção se desgasta, mas o terreno não, e o preço de mercado costuma acompanhar a inflação ou subir, dependendo do lugar. Na tabela, uma taxa **negativa** faz a categoria **valorizar** por ano. A ligação é automática, pela chave que o InventarIA grava em `share/inventario`; nada muda lá. Os valores são lidos a cada 10 minutos (ou na hora, em **Atualizar**).

## Contas no CronologIA

O [CronologIA](https://github.com/diegozapella63/cronologia-ha) é o app de agenda da mesma família. Com os dois instalados no mesmo Home Assistant:

- as contas a pagar, os fixos e as faturas do cartão aparecem no calendário do CronologIA, no dia do vencimento, e no card **Contas a pagar** da tela Agora (atrasadas primeiro);
- **Paguei** no CronologIA dá baixa aqui: o fixo do mês vira um lançamento pago, a fatura fica toda paga e uma conta avulsa fica paga. **Desfazer** volta para "a pagar";
- o modelo **Conta a pagar** do CronologIA cria a conta aqui: única (lançamento a pagar) ou fixa, todo mês ou todo ano.

Recebimentos, ajustes de saldo e despesas descontadas do salário não aparecem como contas. Os aportes aparecem, porque são compromissos (contas a pagar do tipo Aporte).

A ligação não pede configuração. Ao iniciar, o GerencIA grava em `share/gerencia/integracao.json` o endereço dele na rede interna dos apps e uma chave, e o CronologIA (que lê a pasta `share`) usa essa chave para chamar o GerencIA. Quem já consegue ler a pasta `share` também lê os backups do GerencIA que ficam lá, então a chave não abre nada novo. Para cortar a ligação, desligue **Mais › Configurações › Integrações › Contas no CronologIA**: o arquivo é apagado e a chave deixa de valer. O mesmo cartão mostra quando o CronologIA usou a ligação pela última vez.

Rotas usadas pelo CronologIA (todas com `Authorization: Bearer <chave>`):

| Método | Rota | O que faz |
| --- | --- | --- |
| GET | `/api/integracao/contas?de=AAAA-MM-DD&ate=AAAA-MM-DD` | Contas do período e as atrasadas dos últimos 2 meses: `{id, tipo: conta\|fixo\|fatura, descricao, valor, vencimento, pago, atrasada, categoria, conta}` e as categorias de gasto. |
| POST | `/api/integracao/pagar` | `{id, valor?}`: dá baixa. |
| POST | `/api/integracao/desfazer` | `{id}`: volta para a pagar. |
| POST | `/api/integracao/nova` | `{descricao, valor, vencimento, repete: nao\|mensal\|anual, categoria?}`. |

## CorrerIA (WhatsApp, Claude e Gemini)

O [CorrerIA](https://github.com/diegozapella63/correria-ha) é um app da mesma família que junta os apps da casa no **WhatsApp** (o contato da CorrerIA Code), no **Claude** e no **Gemini**. Com **Mais › Configurações › Integrações › CorrerIA** ligado (vem desligado), eles leem e mudam as finanças pelo GerencIA, com os seus dados:

- **Ler**: o resumo de hoje, os lançamentos de um período (com os gastos por categoria), as contas a pagar e as faturas, os investimentos e os cadastros (contas, cartões, categorias, fixos). Ex.: "quanto gastei com mercado em outubro?", "o que vence esta semana?".
- **Gravar**: lançar um gasto ou recebimento (também parcelado ou no cartão), editar ou apagar um lançamento (num fixo, só o daquele mês), marcar uma conta, um fixo ou a fatura como paga (ou desfazer), atualizar o saldo de um investimento (saldo, aporte ou resgate), cadastrar um investimento e cadastrar um fixo. Ex.: "lança 45,90 de mercado no cartão do Banco Azul", "paguei a internet".
- Antes de gravar, o Claude e o Gemini mostram o que vão fazer; pelo WhatsApp, o CorrerIA pede um **sim**. A tela daqui se atualiza sozinha, e as versões automáticas (Mais › Configurações › Dados) guardam como estava.
- **Fotos e PDFs pelo WhatsApp** (precisa da IA ligada aqui): uma foto de nota, um print ou uma fatura em PDF são lidos como no Ler com IA (o PDF com senha abre com as Senhas dos PDFs). O que a IA achar fica para conferir nos **Avisos do Início** ("Enviado por Ana · Pelo WhatsApp · 4 lançamentos"), junto das faturas por e-mail: toque para conferir e **Lançar** ou **Ignorar**. Áudio chega como texto (o CorrerIA ouve antes).
- Quem pode usar é escolhido no CorrerIA: as pessoas com o WhatsApp cadastrado e quem conectou o Claude ou o Gemini (aprovado no painel do Home Assistant).
- O cartão mostra o último uso ("Claude usou hoje às 9:41"). Desligado, o arquivo `share/gerencia/correria.json` (o endereço e uma chave só do CorrerIA) é apagado e a chave deixa de valer.

O CorrerIA usa, com `Authorization: Bearer <chave>`:

| Método | Rota | O que faz |
|---|---|---|
| GET | `/api/integracao/ferramentas` | `{instrucoes, ferramentas: [{nome, titulo, descricao, entrada (JSON Schema), grava, apaga}]}`. |
| POST | `/api/integracao/ferramentas` | `{nome, argumentos, pessoa: {id, nome}, cliente}` → `{texto}`; argumento inválido: 400 `{erro}` (diz o que vale). |
| POST | `/api/integracao/conversa` | Só com a IA ligada: `{texto, historico, pessoa, canal, anexo?: {tipo, nome, b64}}` → `{resposta}`. O `correria.json` diz os tipos de anexo (`anexos`: PDF, JPG, PNG e WebP). |

## Dados e backup

- Tudo fica em `/data/gerencia.json`, que entra nos backups do Home Assistant. As imagens dos investimentos ficam em `/data/fotos`, e as senhas dos PDFs em `/data/senhas_pdf.json` (fora das exportações e dos backups da pasta share).
- **Criar backup** (Mais › Configurações › Dados) salva um `.zip` em `share/gerencia`, com os dados e as imagens. Logo abaixo ficam os últimos backups da pasta, cada um com **Restaurar**.
- **Importar** traz de volta um `.zip` ou `.json` exportado pelo GerencIA; antes, o app guarda uma cópia do que existe.
- O app guarda uma versão a cada 10 minutos de uso e antes de importar ou restaurar, e fica com as 3 mais recentes, como os outros apps.
- **Exportar** (Mais › Configurações › Dados), uma linha por arquivo, cada uma com o que ele tem: **Lançamentos (CSV)**, um lançamento por linha, com os fixos e os descontos do salário; **Investimentos (CSV)**, um investimento por linha; **Dados completos (JSON)**; **Tudo (ZIP)**, com os dados, as duas planilhas e as imagens, que o Importar traz de volta. Os CSV abrem no Excel e no Google Planilhas (separados por ponto e vírgula).
- **Relatório de patrimônio** (linha própria em Mais): o cabeçalho é o dos relatórios dos outros apps (o ícone, GerencIA, quantos investimentos e bens e quando foi gerado); no fim, a marca da **CorrerIA Code**, como no **Sobre** (no PDF, no pé de cada página). O resumo traz o **Patrimônio** (o mesmo do Início: seus investimentos e bens), **Investido**, **Bens** e **De terceiros**. Depois vêm o seu dinheiro, os **Bens** (os cadastrados aqui e, com **Bens no InventarIA** ligado, os itens de lá), o dinheiro de cada pessoa e o **Por banco** (só os investimentos). Os bens aparecem numa linha só, e os imóveis em outra, com o total, quanto mudam por ano e as projeções; **Detalhar bens e imóveis** (começa desligado) mostra item por item, com o cômodo, quanto perde ou valoriza por ano pela categoria e a data do valor, na página e no PDF. No alto, **Todos**, **Meus** ou **De terceiros** escolhe o que entra; os bens da casa são seus, então não aparecem em De terceiros. **Baixar PDF** baixa o relatório num arquivo (`patrimonio-AAAA-MM-DD.pdf`, com `-meus` ou `-terceiros` quando filtrado), com a página deitada e as colunas **Por mês**, **Em 1 ano** e **Em 5 anos** (com as taxas de hoje, sem novos aportes e reaplicando o que vence, antes do IR), o total de cada grupo e o número das páginas; funciona também no app do Home Assistant no celular. A página abre no mesmo tema do app (claro ou escuro); o PDF e o papel são sempre brancos.
- **Começar do zero** apaga lançamentos, fixos, investimentos e bancos; índices, categorias e preferências continuam, e uma cópia fica em Versões anteriores.

## Avisos

Projeções usam os índices de hoje mantidos no período, e a previsão do caixa usa os fixos, parcelas e médias lançados. São estimativas, não promessas.
