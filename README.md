# GerencIA

O GerencIA é um app do Home Assistant para acompanhar seus investimentos: quanto você tem, em quais bancos, de quem é cada dinheiro (seu ou de terceiros) e quanto ele deve render, com os índices do Banco Central.

[![Adicionar o repositório ao Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fdiegozapella63%2Fgerencia-ha)

## Instalação

1. Toque no botão acima. Se preferir, no Home Assistant abra **Configurações > Apps > Loja de apps**, toque no menu, escolha **Repositórios** e cole `https://github.com/diegozapella63/gerencia-ha`.
2. Na loja de apps, abra **GerencIA** e toque em **Instalar**. A primeira instalação leva alguns minutos.
3. Toque em **Iniciar** e ligue **Mostrar na barra lateral**.
4. Abra o GerencIA e cadastre o primeiro investimento, importe um backup (`.zip`) ou veja com dados de exemplo.

Atualizações aparecem sozinhas no Home Assistant, com o botão **Atualizar**.

## Seus dados

Os investimentos ficam só no seu Home Assistant, em um arquivo aberto (JSON), e entram nos backups do Home Assistant. Este repositório tem apenas o código do app.

Veja [DOCS.md](gerencia/DOCS.md) para uso, rendimentos, sensores e backups.
