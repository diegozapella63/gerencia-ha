# GerencIA

Controle dos seus investimentos dentro do Home Assistant: quanto você tem, onde está, de quem é o dinheiro e quanto vai ter daqui a alguns anos.

## Instalar

1. No Home Assistant, abra **Configurações > Apps > Loja de apps**, toque no menu, escolha **Repositórios** e cole `https://github.com/diegozapella63/gerencia-ha`.
2. Abra **GerencIA**, toque em **Instalar**, depois em **Iniciar**, e ligue **Mostrar na barra lateral**.

O app abre pela barra lateral (Ingress). Quem já está logado no Home Assistant usa direto, sem outra senha, e o app cumprimenta pelo nome.

## Telas

- **Início**: o placar do patrimônio, com plaquinhas que viram como num painel de cotações (seu, de terceiros e quanto rende por mês), quanto rende por mês, melhor rendimento, o que vence primeiro, maior banco e quanto seu dinheiro deve valer em 1 ano. Abaixo, o dinheiro de terceiros por pessoa e os avisos (vencimentos, valores desatualizados, índices).
- **Investimentos**: lista com filtro Todos, Meus e Terceiros, por pessoa e por banco. Cada cartão mostra o rendimento, o dono (Meu ou De fulano) e a liquidez.
- **Adicionar**: valor, data do valor, banco, tipo, rendimento e de quem é o dinheiro. Se for de terceiros, diga de quem.
- **Gráficos**: *Evolução* mostra o que foi registrado até hoje e a projeção (1, 2, 5 ou 10 anos), com aporte mensal opcional, desconto de IR e o valor em dinheiro de hoje (descontando o IPCA). *Dinheiro atual* divide o total por banco, dono, tipo ou liquidez.
- **Mais**: aparência (tema e cor), cadastro de bancos, índices de mercado, cálculos, sensores e dados (exportar, relatório, backup, importar, versões).

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

Eles são atualizados a cada alteração e a cada 15 minutos. Depois de reiniciar o Home Assistant, voltam em até 15 minutos.

## Dados e backup

- Tudo fica em `/data/gerencia.json`, que entra nos backups do Home Assistant.
- **Criar backup** salva um `.zip` em `share/gerencia`.
- O app guarda uma versão a cada 10 minutos de uso (as 60 mais recentes) e antes de importar ou restaurar.
- **Exportar** gera CSV (abre no Excel, separado por ponto e vírgula), JSON e ZIP.

## Avisos

Projeções usam os índices de hoje mantidos no período. São estimativas, não promessas de rendimento.
