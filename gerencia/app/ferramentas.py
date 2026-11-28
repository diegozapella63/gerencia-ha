"""Ferramentas do GerencIA para o Claude e o Gemini, pelo CorrerIA (o MCP da casa): ler as finanças e gravar
(lançar, editar, apagar, marcar como pago, saldos e investimentos, fixos). O CorrerIA lista as ferramentas
(GET /api/integracao/ferramentas) e chama uma (POST {nome, argumentos, pessoa, cliente}); o server.py lê e grava os
dados (com a revisão e as versões automáticas) e aqui ficam as regras, as mesmas da tela (app.js). Só biblioteca padrão.

Cada ferramenta: {nome, titulo, descricao, entrada (JSON Schema), grava, apaga}. chamar() devolve (texto, mudou)."""
import json
import re
import unicodedata
from datetime import date, datetime, timedelta

import calc
import cambio
import chat
import cotacoes
import integracao

MAX_PERIODO = 400   # dias de uma busca de lançamentos
MAX_LISTA = 1000

TIPOS_INV = {  # tipo: (nome, indexador, taxa, liquidez) — os padrões do app (TIPOS no app.js), menos os bens
    "cdb": ("CDB", "cdi_pct", 100, "vencimento"), "lci": ("LCI/LCA", "cdi_pct", 90, "vencimento"),
    "tesouro": ("Tesouro", "selic_mais", 0, "diaria"), "poupanca": ("Poupança", "poupanca", 0, "diaria"),
    "caixinha": ("Caixinha", "cdi_pct", 100, "diaria"), "fundo": ("Fundo", "cdi_pct", 100, "diaria"),
    "acoes": ("Ações/FII", "estimado", 10, "diaria"), "ouro": ("Ouro", "estimado", 10, "diaria"),
    "dinheiro": ("Dinheiro", "parado", 0, "diaria"), "previdencia": ("Previdência", "cdi_pct", 95, "vencimento"),
    "outro": ("Outro", "pre", 12, "vencimento"),
}
INDEXADORES = {"cdi_pct": "% do CDI", "cdi_mais": "CDI + taxa ao ano", "pre": "prefixado (taxa ao ano)", "ipca_mais": "IPCA + taxa ao ano",
               "selic_mais": "Selic + taxa ao ano", "poupanca": "poupança", "estimado": "estimado (taxa ao ano)", "parado": "sem rendimento"}
CORES_BANCO = ["#62B5FF", "#B99BFF", "#4ED3A6", "#FFA23E", "#FF77A9", "#F2C14E", "#FF8A65", "#3CCBDA", "#FF5A4F", "#8F9BFF", "#8BD45F", "#B5B9C2"]  # 1.91.0: a paleta da família

INSTRUCOES = ("GerencIA: as finanças da casa (caixa, contas a pagar, cartões e faturas, investimentos e patrimônio). Valores em "
              "reais e datas no formato AAAA-MM-DD. Comece por gerencia_resumo; os ids que ele mostra servem nas outras "
              "ferramentas. Uma conta que já está em contas a pagar (fixo ou fatura) se paga com gerencia_marcar_pago, não se "
              "lança de novo. As faturas e contas que chegaram por e-mail (e as fotos e PDFs mandados pelo WhatsApp) e esperam a "
              "conferência estão em gerencia_faturas_do_email. Antes de gravar, diga à pessoa o que vai ser feito.")


class ErroFerramenta(ValueError):
    pass


# ---------------------------------------------------------------- a lista

def _obj(props, obrig=()):
    return {"type": "object", "properties": props, "required": list(obrig), "additionalProperties": False}


_DATA = {"type": "string", "description": "AAAA-MM-DD"}
_ID = {"type": "string", "description": "O id do lançamento (de gerencia_lancamentos, gerencia_resumo ou gerencia_contas_a_pagar)."}
_FIXO = {"type": "string", "description": "O id do fixo (r-...; em gerencia_cadastros) ou o de um mês dele (v:r-...:AAAA-MM)."}

FERRAMENTAS = [
    {"nome": "resumo", "titulo": "Resumo das finanças", "grava": False,
     "descricao": "Visão geral de hoje: contas no banco e cartões, saldo do caixa e o movimento do mês, contas a pagar (atrasadas "
                  "e dos próximos 45 dias), lançamentos dos últimos 45 dias, fixos, investimentos, patrimônio e as categorias. "
                  "Comece por aqui: os ids servem nas outras ferramentas.",
     "entrada": _obj({})},
    {"nome": "lancamentos", "titulo": "Buscar lançamentos", "grava": False,
     "descricao": "Gastos e recebimentos de um período (pela data da compra ou do recebimento), com os totais e os gastos por "
                  "categoria. Os fixos que ainda não foram lançados entram também (o id começa com v:). Sem período, o mês atual.",
     "entrada": _obj({"de": _DATA, "ate": _DATA,
                      "busca": {"type": "string", "description": "Parte da descrição ou da observação."},
                      "categoria": {"type": "string", "description": "Id ou nome da categoria."},
                      "tipo": {"type": "string", "enum": ["despesa", "receita"]},
                      "conta": {"type": "string", "description": "Id ou nome do banco/conta."},
                      "limite": {"type": "integer", "minimum": 1, "maximum": MAX_LISTA, "description": "Padrão: 200."}})},
    # 1.96.0 (o dono, às ferramentas que faltavam para o CorrerIA: "pode seguir em todas")
    {"nome": "comparar_meses", "titulo": "Comparar meses", "grava": False,
     "descricao": "Os gastos por categoria de um mês contra outro (sem mês, o atual contra o anterior), com o que mais subiu "
                  "primeiro. No mês atual, os dois vão só até o dia de hoje, para a comparação ser justa.",
     "entrada": _obj({"mes": {"type": "string", "description": "AAAA-MM. Padrão: o mês atual."},
                      "com": {"type": "string", "description": "AAAA-MM. Padrão: o mês anterior ao primeiro."}})},
    # 1.97.0 (o dono, ao «Algo estranho»: "pode fazer todos")
    {"nome": "fora_do_padrao", "titulo": "Gastos fora do padrão", "grava": False,
     "descricao": "O que foge do costume nos gastos deste mês, sem IA: o que veio mais caro que a média dos 3 meses anteriores, o "
                  "lançamento que parece repetido (mesma descrição, valor e dia) e a compra grande que não é de costume. A primeira "
                  "linha diz quantos.",
     "entrada": _obj({})},
    {"nome": "previsao_mes", "titulo": "Previsão de gastos do mês", "grava": False,
     "descricao": "Quanto a casa deve gastar neste mês, sem IA: o que já saiu, o que já está marcado até o fim do mês (fixos, parcelas "
                  "e contas lançadas) e o dia a dia que ainda deve vir, pela média dos últimos meses; com a média deles para comparar.",
     "entrada": _obj({})},
    {"nome": "conta_de_luz", "titulo": "Conta de luz pelo consumo", "grava": False,
     "descricao": "Quanto a conta de luz deste mês já deu até hoje e a projeção do mês inteiro, pelo medidor de energia do Home "
                  "Assistant ligado a um fixo (Mais › Configurações › Integrações › Conta de luz). Só lê.",
     "entrada": _obj({})},
    {"nome": "cambio", "titulo": "Câmbio do Banco Central", "grava": False,
     "descricao": "A cotação de hoje do dólar, do euro e da libra (a PTAX de venda do Banco Central). Com valor e moeda, "
                  "converte para reais; com moeda BRL e para (USD, EUR ou GBP), de reais para a moeda. É a taxa de referência: "
                  "no cartão ou na conta global sai um pouco diferente (a cotação do banco e o IOF).",
     "entrada": _obj({"valor": {"type": "number", "exclusiveMinimum": 0},
                      "moeda": {"type": "string", "enum": ["USD", "EUR", "GBP", "BRL"], "description": "A moeda do valor."},
                      "para": {"type": "string", "enum": ["USD", "EUR", "GBP"], "description": "Só com moeda BRL: para qual converter."}})},
    {"nome": "projecao", "titulo": "Projeção dos investimentos", "grava": False,
     "descricao": "Quanto os seus investimentos viram daqui a tantos meses, com a taxa de hoje de cada um, antes do IR (a projeção "
                  "da tela); com aporte_mensal, soma o que você põe todo mês, rendendo pela taxa média. Sem os bens e sem o dinheiro "
                  "de outras pessoas.",
     "entrada": _obj({"meses": {"type": "integer", "minimum": 1, "maximum": 480, "description": "Padrão: 12."},
                      "aporte_mensal": {"type": "number", "minimum": 0, "description": "Quanto entra por mês (opcional)."}})},
    {"nome": "contas_a_pagar", "titulo": "Contas a pagar", "grava": False,
     "descricao": "Contas, fixos e faturas de cartão a pagar (e as já pagas) num período, com as atrasadas dos últimos 2 meses. "
                  "Sem período, de hoje a 45 dias. O id serve em gerencia_marcar_pago.",
     "entrada": _obj({"de": _DATA, "ate": _DATA})},
    {"nome": "investimentos", "titulo": "Investimentos", "grava": False,
     "descricao": "Cada investimento (e bem) com o valor de hoje, o rendimento, o vencimento, a liquidez e de quem é; e os totais "
                  "do patrimônio.",
     "entrada": _obj({})},
    {"nome": "cadastros", "titulo": "Cadastros", "grava": False,
     "descricao": "Contas de banco (com o cartão de crédito: dia de fechamento e de vencimento), categorias, bancos, fixos, as "
                  "pessoas dos investimentos de terceiros, os tipos de investimento e os rendimentos aceitos.",
     "entrada": _obj({})},
    # 1.87.0 (o dono: "Tem algum email para revisar hj?" e a IA não achou): as faturas do e-mail que esperam a conferência
    {"nome": "faturas_do_email", "titulo": "Faturas do e-mail para conferir", "grava": False,
     "descricao": "As faturas, contas e recibos que chegaram por e-mail (ou por foto e PDF pelo WhatsApp), foram lidos pela IA do "
                  "GerencIA e esperam a conferência (o aviso Fatura do e-mail para conferir): de quem, o assunto, quando chegou e cada "
                  "linha lida (o número, a descrição, o valor, a data, a categoria, a conta, se vai para um fixo e se parece já lançada). "
                  "Use para \"tem e-mail para revisar?\", \"chegou alguma fatura?\".",
     "entrada": _obj({})},
    # 1.90.0 (o dono: "revisa se mais etapas ou ferramentas devem ser integradas nas rondas"): Mais › Benefícios e as
    # Oportunidades, só leitura
    {"nome": "beneficios", "titulo": "Benefícios e milhas", "grava": False,
     "descricao": "Mais › Benefícios: cada benefício (sala VIP, crédito, cupom, vantagem) com o que sobra no período e até quando; "
                  "as milhas de cada pessoa (o saldo de hoje, o nível, o que vence e as trocas que já dão); e as oportunidades dos "
                  "benefícios (o que falta para o próximo nível ou para ganhar mais). "
                  "Use para \"quantas salas VIP eu tenho?\", \"minhas milhas vencem?\".",
     "entrada": _obj({})},
    {"nome": "oportunidades", "titulo": "Oportunidades de investimento e assinaturas em promoção", "grava": False,
     "descricao": "Mais › Oportunidades: os títulos do Tesouro Direto e as ofertas das páginas dos bancos cadastrados, com o equivalente "
                  "em CDB, se passam do que a casa quer e como ficam perto dos investimentos dela (as que passam primeiro); e as "
                  "assinaturas de vídeo, música e jogos em promoção nos aparelhos da casa. Use para \"tem algum investimento bom?\", "
                  "\"alguma assinatura em promoção?\".",
     "entrada": _obj({"so_as_que_passam": {"type": "boolean", "description": "Só as que passam do que a casa quer (sem as outras do Tesouro)."}})},
    # 1.95.0 (o dono, às ferramentas que faltavam para o CorrerIA: "pode seguir neles"): as Dicas da tela
    {"nome": "dicas", "titulo": "Dicas de economia", "grava": False,
     "descricao": "As dicas de economia das assinaturas da casa (as que o app achou nos fixos e nas faturas): quanto sobra por ano "
                  "pagando o plano anual, com o preço conferido na página oficial, e as assinaturas que ele acompanha. Só lê o que "
                  "já foi conferido. Use para \"onde dá para economizar?\".",
     "entrada": _obj({})},
    # 1.103.0: a foto ou o PDF da conversa, lido pela IA daqui (o CorrerIA manda o arquivo em anexo, fora dos argumentos)
    {"nome": "ler_arquivo", "titulo": "Ler a foto ou o PDF", "grava": False, "anexo": ["image/jpeg", "image/png", "application/pdf"],
     "descricao": "Lê a foto, o print ou o PDF que a pessoa mandou e devolve o que achou, sem gravar nada. o_que lancamentos (padrão): "
                  "os gastos, os recebimentos e os investimentos de uma nota, um comprovante ou uma fatura. o_que beneficios: um saldo, "
                  "um crédito, um vale, um cupom ou os benefícios de um cartão ou plano. Depois, proponha a mudança com gerencia_lancar, "
                  "gerencia_novo_beneficio ou a que couber.",
     "entrada": _obj({"o_que": {"type": "string", "enum": ["lancamentos", "beneficios"]}})},
    {"nome": "lancar", "titulo": "Lançar gasto ou recebimento", "grava": True,
     "descricao": "Lança um gasto (despesa) ou um recebimento (receita). Compra parcelada: valor de cada parcela, parcelas e "
                  "parcela_atual (as próximas entram nos meses seguintes). Sem pago, fica pago se a data já passou (no cartão de "
                  "crédito, segue a fatura). Para pagar uma conta que já existe, use gerencia_marcar_pago.",
     "entrada": _obj({"tipo": {"type": "string", "enum": ["despesa", "receita"]},
                      "descricao": {"type": "string", "description": "Curta, como a pessoa escreveria."},
                      "valor": {"type": "number", "exclusiveMinimum": 0, "description": "Em reais; em parcelas, o valor de cada uma."},
                      "moeda": {"type": "string", "enum": ["USD", "EUR", "GBP"],
                                "description": "Só quando o valor está em dólar, euro ou libra: vira reais pela cotação de hoje do Banco Central."},
                      "data": {"type": "string", "description": "AAAA-MM-DD; sem data, hoje. Em parcelas, a data da parcela atual."},
                      "categoria": {"type": "string", "description": "Id ou nome da categoria (do mesmo tipo)."},
                      "conta": {"type": "string", "description": "Id ou nome do banco/conta."},
                      "cartao": {"type": "boolean", "description": "No cartão de crédito da conta."},
                      "parcelas": {"type": "integer", "minimum": 2, "maximum": 120},
                      "parcela_atual": {"type": "integer", "minimum": 1, "maximum": 120},
                      "pago": {"type": "boolean"},
                      "obs": {"type": "string"}}, ["tipo", "descricao", "valor"])},
    {"nome": "editar_lancamento", "titulo": "Editar lançamento", "grava": True,
     "descricao": "Muda um lançamento (só o que vier). Num fixo, muda só o daquele mês.",
     "entrada": _obj({"id": _ID, "descricao": {"type": "string"}, "valor": {"type": "number", "exclusiveMinimum": 0}, "data": _DATA,
                      "categoria": {"type": "string"}, "conta": {"type": "string", "description": "Id ou nome; vazio tira a conta."},
                      "cartao": {"type": "boolean"}, "pago": {"type": "boolean"}, "obs": {"type": "string"}}, ["id"])},
    # 1.94.0 (o dono, às ferramentas que faltavam para o CorrerIA: "pode colocar todas"): o Alterar do Caixa › Selecionar
    {"nome": "alterar_lancamentos", "titulo": "Alterar vários lançamentos", "grava": True,
     "descricao": "Muda de uma vez a categoria e/ou a situação (pago ou a pagar; numa receita, recebido ou a receber) de vários "
                  "lançamentos, como o Alterar do Caixa › Lançamentos › Selecionar: todos do mesmo tipo (só despesas ou só receitas); "
                  "num fixo, só o daquele mês. Uma compra no cartão não muda a situação (quem paga é a fatura).",
     "entrada": _obj({"ids": {"type": "array", "minItems": 1, "maxItems": 200, "items": _ID}, "categoria": {"type": "string"},
                      "pago": {"type": "boolean"}}, ["ids"])},
    {"nome": "apagar_lancamento", "titulo": "Apagar lançamento", "grava": True, "apaga": True,
     "descricao": "Apaga um lançamento. Num fixo, apaga só o daquele mês (o fixo continua nos outros). Numa compra parcelada, "
                  "só aquela parcela.",
     "entrada": _obj({"id": _ID}, ["id"])},
    {"nome": "marcar_pago", "titulo": "Marcar como pago", "grava": True,
     "descricao": "Marca uma conta, um fixo ou uma fatura de cartão como paga (ou um recebimento como recebido); com pago "
                  "false, desfaz. valor: o que foi pago, se diferente.",
     "entrada": _obj({"id": {"type": "string", "description": "O id de gerencia_contas_a_pagar (fatura: f:...; fixo: v:...) ou de um lançamento."},
                      "pago": {"type": "boolean", "description": "Padrão: true."},
                      "valor": {"type": "number", "exclusiveMinimum": 0}}, ["id"])},
    {"nome": "atualizar_investimento", "titulo": "Atualizar investimento", "grava": True,
     "descricao": "Muda o valor de um investimento: o saldo de agora, ou um aporte (soma ao valor de hoje), ou um resgate "
                  "(tira), ou, num papel da bolsa, a quantidade de agora. Um só.",
     "entrada": _obj({"id": {"type": "string", "description": "O id do investimento."},
                      "saldo": {"type": "number", "minimum": 0}, "aporte": {"type": "number", "exclusiveMinimum": 0},
                      "resgate": {"type": "number", "exclusiveMinimum": 0},
                      "quantidade": {"type": "number", "exclusiveMinimum": 0, "description": "Num papel da bolsa (com código): quantas ações ou cotas a "
                                                                                           "pessoa tem agora. O valor é a quantidade vezes a cotação."}}, ["id"])},
    {"nome": "novo_investimento", "titulo": "Novo investimento", "grava": True,
     "descricao": "Cadastra um investimento. Sem rendimento, o padrão do tipo (CDB: 100% do CDI). de_quem vazio: da própria "
                  "pessoa; com um nome, de outra pessoa (fica fora do patrimônio dela).",
     "entrada": _obj({"nome": {"type": "string"}, "valor": {"type": "number", "minimum": 0, "description": "O valor de hoje."},
                      "tipo": {"type": "string", "enum": list(TIPOS_INV)}, "banco": {"type": "string", "description": "O nome do banco ou corretora."},
                      "indexador": {"type": "string", "enum": list(INDEXADORES)},
                      "taxa": {"type": "number", "description": "Pelo indexador: 110 (% do CDI), 6.5 (IPCA + 6,5% a.a.), 13 (prefixado)."},
                      "vencimento": _DATA, "liquidez": {"type": "string", "enum": ["diaria", "vencimento"]},
                      "de_quem": {"type": "string"},
                      "codigo": {"type": "string", "description": "Numa ação, fundo imobiliário, ETF ou BDR: o código na bolsa (PETR4, MXRF11). Com a "
                                                                  "quantidade, o valor se atualiza sozinho pela cotação (com a chave da brapi posta no app)."},
                      "quantidade": {"type": "number", "exclusiveMinimum": 0, "description": "Quantas ações ou cotas, junto com o codigo."}}, ["nome", "tipo"])},
    # 1.85.0 (o dono: "pode criar" as ferramentas que faltavam para as rondas do CorrerIA): o Ajustar saldo do Caixa da tela
    {"nome": "ajustar_saldo", "titulo": "Ajustar o saldo do caixa", "grava": True,
     "descricao": "Acerta o saldo do caixa com o que a pessoa diz que tem de verdade (o saldo de hoje está em gerencia_resumo). "
                  "A diferença entra como um lançamento \"Ajuste de saldo\", fora das entradas, das saídas e das categorias, como o "
                  "Ajustar saldo da tela. Use só quando a pessoa disser o saldo certo: nunca para lançar um gasto.",
     "entrada": _obj({"saldo": {"type": "number", "description": "O saldo certo de agora, em reais (pode ser negativo)."}}, ["saldo"])},
    {"nome": "lancar_fatura_do_email", "titulo": "Lançar fatura do e-mail", "grava": True,
     "descricao": "Lança o que a IA leu de uma fatura do e-mail (de gerencia_faturas_do_email), como o Conferir lançamentos da tela: "
                  "sem linhas, as que a tela já marca (fora as que parecem já lançadas e o pagamento da própria fatura). A linha que "
                  "vai para um fixo entra no fixo do mês. As linhas que ficarem continuam para conferir.",
     "entrada": _obj({"id": {"type": "string", "description": "O id da fatura em gerencia_faturas_do_email."},
                      "linhas": {"type": "array", "items": {"type": "integer", "minimum": 1}, "description": "Os números das linhas a lançar."},
                      "conta": {"type": "string", "description": "Id ou nome da conta, para todas as linhas (sem ela, a que a tela escolhe)."},
                      "pago": {"type": "boolean", "description": "Tudo pago (true) ou tudo pendente (false); sem ele, pela data e pelo que a IA leu."}},
                     ["id"])},
    {"nome": "ignorar_fatura_do_email", "titulo": "Ignorar fatura do e-mail", "grava": True,
     "descricao": "Tira uma fatura do e-mail da conferência sem lançar nada (o Ignorar da tela).",
     "entrada": _obj({"id": {"type": "string", "description": "O id da fatura em gerencia_faturas_do_email."}}, ["id"])},
    # 1.88.0 (o dono: "todas", das que faltavam): o que a tela faz e a IA não fazia
    {"nome": "editar_fixo", "titulo": "Mudar um fixo", "grava": True,
     "descricao": "Muda um fixo de agora em diante (o valor, a descrição, o dia, a categoria, a conta): os meses que ainda não foram "
                  "lançados seguem o novo; os já lançados ficam como foram. Para mudar só um mês, use gerencia_editar_lancamento.",
     "entrada": _obj({"id": _FIXO, "descricao": {"type": "string"}, "valor": {"type": "number", "exclusiveMinimum": 0},
                      "dia": {"type": "integer", "minimum": 1, "maximum": 31}, "categoria": {"type": "string"},
                      "conta": {"type": "string", "description": "Id ou nome; vazio tira a conta."}, "cartao": {"type": "boolean"}}, ["id"])},
    {"nome": "encerrar_fixo", "titulo": "Encerrar ou apagar um fixo", "grava": True, "apaga": True,
     "descricao": "Para um fixo a partir de um mês: o que foi lançado antes continua, e os meses dali em diante que não foram pagos "
                  "saem. Com apagar_tudo, apaga o fixo e tudo o que ele já lançou (como o Apagar fixo da tela).",
     "entrada": _obj({"id": _FIXO, "a_partir": {"type": "string", "description": "AAAA-MM; sem ele, o mês de hoje."},
                      "apagar_tudo": {"type": "boolean"}}, ["id"])},
    {"nome": "usar_beneficio", "titulo": "Usar um benefício ou resgatar milhas", "grava": True,
     "descricao": "Anota o uso de um benefício de Mais › Benefícios (sala VIP, crédito, cupom...: os de gerencia_resumo): numa "
                  "contagem desconta 1 (ou a quantidade), num saldo desconta o valor; num programa de milhas, as milhas resgatadas.",
     "entrada": _obj({"beneficio": {"type": "string", "description": "O id ou o nome do benefício (ou do programa de milhas)."},
                      "quantidade": {"type": "number", "exclusiveMinimum": 0, "description": "Contagem: padrão 1. Saldo: o valor usado. Milhas: as resgatadas."},
                      "data": _DATA}, ["beneficio"])},
    {"nome": "novo_beneficio", "titulo": "Novo benefício", "grava": True,
     "descricao": "Cadastra um benefício em Mais › Benefícios, para usar depois: um saldo ou crédito (um vale, um cupom, o crédito de "
                  "uma loja: tipo saldo, com o valor em total), uma quantidade de usos (acessos à sala VIP, diárias: tipo contagem, com "
                  "quantos em total) ou uma vantagem sem conta (seguro, frete grátis: tipo vantagem). É o que a pessoa pede com "
                  "«adiciona esse saldo», «guarda esse crédito», «tenho um vale de…». Não é um lançamento do caixa.",
     "entrada": _obj({"nome": {"type": "string", "description": "O nome do benefício, como «Crédito na Google Store»."},
                      "tipo": {"type": "string", "enum": ["saldo", "contagem", "vantagem"]},
                      "total": {"type": "number", "exclusiveMinimum": 0, "description": "Saldo: o valor. Contagem: quantos. Vantagem: não tem."},
                      "moeda": {"type": "string", "enum": ["BRL", "USD"], "description": "Só num saldo; padrão BRL."},
                      "renova": {"type": "string", "enum": ["mes", "ano", "nunca"], "description": "De quanto em quanto tempo volta ao total; padrão nunca."},
                      "validade": {"type": "string", "description": "AAAA-MM-DD: até quando vale (se tiver)."},
                      "origem": {"type": "string", "description": "De onde vem, se vier de um banco ou de um fixo cadastrado: o nome dele."},
                      "observacao": {"type": "string"}, "descricao": {"type": "string", "description": "O que é, em poucas palavras."}}, ["nome", "tipo"])},
    {"nome": "editar_beneficio", "titulo": "Mudar ou apagar um benefício", "grava": True, "apaga": True,
     "descricao": "Muda um benefício de Mais › Benefícios (o nome, o total, a moeda, quando renova, a validade, a observação) ou apaga "
                  "(apagar true). Para anotar um uso, é o gerencia_usar_beneficio.",
     "entrada": _obj({"beneficio": {"type": "string", "description": "O id ou o nome do benefício."}, "nome": {"type": "string"},
                      "total": {"type": "number", "exclusiveMinimum": 0}, "moeda": {"type": "string", "enum": ["BRL", "USD"]},
                      "renova": {"type": "string", "enum": ["mes", "ano", "nunca"]},
                      "validade": {"type": "string", "description": "AAAA-MM-DD; vazio tira."}, "observacao": {"type": "string"},
                      "apagar": {"type": "boolean"}}, ["beneficio"])},
    {"nome": "atualizar_milhas", "titulo": "Atualizar o saldo de milhas", "grava": True,
     "descricao": "Põe o saldo de hoje de um programa de milhas (o que a pessoa vê no app do programa).",
     "entrada": _obj({"beneficio": {"type": "string", "description": "O id ou o nome do programa de milhas."},
                      "saldo": {"type": "integer", "minimum": 0}}, ["beneficio", "saldo"])},
    {"nome": "nova_categoria", "titulo": "Nova categoria", "grava": True,
     "descricao": "Cria uma categoria de gasto (despesa) ou de recebimento (receita), com uma cor da paleta.",
     "entrada": _obj({"nome": {"type": "string"}, "tipo": {"type": "string", "enum": ["despesa", "receita"]}}, ["nome", "tipo"])},
    {"nome": "editar_categoria", "titulo": "Mudar ou apagar categoria", "grava": True, "apaga": True,
     "descricao": "Muda o nome ou a cor de uma categoria, ou apaga (os lançamentos dela ficam sem categoria). As categorias de "
                  "agora estão em gerencia_cadastros.",
     "entrada": _obj({"categoria": {"type": "string", "description": "O id ou o nome."}, "tipo": {"type": "string", "enum": ["despesa", "receita"], "description": "Só se há duas com o mesmo nome."},
                      "nome": {"type": "string", "description": "O nome novo."}, "cor": {"type": "string", "enum": [n for n, _ in calc.CORES_APP]},
                      "apagar": {"type": "boolean"}}, ["categoria"])},
    {"nome": "editar_banco", "titulo": "Mudar banco ou conta", "grava": True,
     "descricao": "Muda o nome, a cor ou a observação de um banco e, numa conta dele, de quem é, os dias da fatura do cartão e o "
                  "limite. Apagar um banco ou uma conta, só pela tela (Mais › Bancos).",
     "entrada": _obj({"banco": {"type": "string", "description": "O id ou o nome do banco."}, "nome": {"type": "string", "description": "O nome novo do banco."},
                      "cor": {"type": "string", "enum": [n for n, _ in calc.CORES_APP]}, "obs": {"type": "string"},
                      "conta": {"type": "string", "description": "O id da conta ou de quem é (só para mudar a conta; com uma conta só, não precisa)."},
                      "pessoa": {"type": "string", "description": "De quem a conta passa a ser."},
                      "cartao_de_credito": {"type": "boolean"}, "fecha_dia": {"type": "integer", "minimum": 1, "maximum": 31},
                      "vence_dia": {"type": "integer", "minimum": 1, "maximum": 31}, "limite": {"type": "number", "exclusiveMinimum": 0}}, ["banco"])},
    {"nome": "novo_banco", "titulo": "Cadastrar banco ou conta", "grava": True,
     "descricao": "Cadastra um banco com a conta de uma pessoa, ou acrescenta a conta de outra pessoa num banco que já existe; com o "
                  "cartão de crédito (o dia em que a fatura fecha e o dia em que vence), se houver.",
     "entrada": _obj({"banco": {"type": "string", "description": "O nome do banco."}, "pessoa": {"type": "string", "description": "De quem é a conta."},
                      "cartao_de_credito": {"type": "boolean"}, "fecha_dia": {"type": "integer", "minimum": 1, "maximum": 31},
                      "vence_dia": {"type": "integer", "minimum": 1, "maximum": 31}, "limite": {"type": "number", "exclusiveMinimum": 0},
                      "cartao_de_debito": {"type": "boolean", "description": "Padrão: true."}}, ["banco"])},
    {"nome": "novo_fixo", "titulo": "Novo fixo", "grava": True,
     "descricao": "Cadastra um gasto ou recebimento que se repete todo mês (ou todo ano), como aluguel, salário ou IPVA. Aparece "
                  "nas contas a pagar a cada mês.",
     "entrada": _obj({"tipo": {"type": "string", "enum": ["despesa", "receita"]}, "descricao": {"type": "string"},
                      "valor": {"type": "number", "exclusiveMinimum": 0},
                      "data": {"type": "string", "description": "A primeira vez (AAAA-MM-DD): o dia vale para os próximos meses."},
                      "repete": {"type": "string", "enum": ["mensal", "anual"], "description": "Padrão: mensal."},
                      "categoria": {"type": "string"}, "conta": {"type": "string"}, "cartao": {"type": "boolean"}},
                     ["tipo", "descricao", "valor", "data"])},
]
POR_NOME = {f["nome"]: f for f in FERRAMENTAS}


def lista():
    return [dict(f, apaga=bool(f.get("apaga"))) for f in FERRAMENTAS]


# ---------------------------------------------------------------- ajudantes

def _norm(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t or "")) if unicodedata.category(c) != "Mn").lower().strip()


def _brl(v):
    return "R$ " + calc.fmt_brl(v) if not calc.fmt_brl(v).startswith("R$") else calc.fmt_brl(v)


def _dm(iso):
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}" if iso and len(iso) >= 10 else (iso or "")


def _json(v):
    return json.dumps(v, ensure_ascii=False, separators=(",", ":"))


def _data(v, hoje, campo="data", padrao=True):
    s = str(v or "").strip().lower()
    if not s or s == "hoje":
        if padrao:
            return hoje
        raise ErroFerramenta(f"Falta {campo}.")
    if s == "ontem":
        return hoje - timedelta(days=1)
    if s == "amanha" or s == "amanhã":
        return hoje + timedelta(days=1)
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else date.fromisoformat(s[:10])
    except ValueError:
        raise ErroFerramenta(f"{campo.capitalize()} inválida: {v}. Use AAAA-MM-DD.") from None


def _valor(v, campo="valor", zero=False):
    x = calc.num_br(v) if isinstance(v, str) else calc.num(v, None) if v is not None else None
    if x is None or x != x or (x < 0 if zero else x <= 0):
        raise ErroFerramenta(f"{campo.capitalize()} inválido: {v}.")
    if x > 1e10:
        raise ErroFerramenta(f"{campo.capitalize()} grande demais.")
    return round(float(x), 2)


def _texto(v, n=120):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _categoria(d, v, tipo):
    """Pelo id ou pelo nome; sem nada, Outros gastos / Outros recebimentos (se existirem)."""
    cats = [c for c in d.get("categorias", []) if c.get("tipo", "despesa") == tipo]
    if v is None or str(v).strip() == "":
        padrao = "c-outros-gastos" if tipo == "despesa" else "c-outros-receb"
        return padrao if any(c.get("id") == padrao for c in cats) else ""
    n = _norm(v)
    c = (next((c for c in cats if c.get("id") == v), None) or next((c for c in cats if _norm(c.get("nome")) == n), None)
         or next((c for c in cats if n and n in _norm(c.get("nome"))), None))
    if not c:
        nomes = ", ".join(f"{c.get('nome')} ({c.get('id')})" for c in cats)
        raise ErroFerramenta(f"Categoria não encontrada: {v}. As de {'gasto' if tipo == 'despesa' else 'recebimento'}: {nomes}.")
    return c["id"]


def _conta(d, v):
    """Pelo id, pelo nome (Banco · pessoa) ou só pelo banco, se for uma conta só."""
    if v is None or str(v).strip() == "":
        return ""
    contas = calc.mapa_contas(d)
    if v in contas:
        return v
    n = _norm(v)
    iguais = [k for k, c in contas.items() if _norm(calc.nome_conta(c)) == n] or \
             [k for k, c in contas.items() if _norm(c.get("banco_nome")) == n] or \
             [k for k, c in contas.items() if n and n in _norm(calc.nome_conta(c))]
    if len(iguais) == 1:
        return iguais[0]
    todas = ", ".join(f"{calc.nome_conta(c)} ({k})" for k, c in contas.items()) or "nenhuma cadastrada"
    raise ErroFerramenta(("Mais de uma conta com esse nome" if iguais else f"Conta não encontrada: {v}") + f". As contas: {todas}.")


def _nome_cat(d, cid):
    return next((c.get("nome", "") for c in d.get("categorias", []) if c.get("id") == cid), "")


def _situacao(l):
    rec = l.get("tipo") == "receita"
    return ("recebido" if rec else "pago") if l.get("pago") else ("a receber" if rec else "a pagar")


def _descrever(d, l, contas=None):
    """Uma linha para a resposta: Mercado · R$ 45,90 · 08/11/2026 · Mercado · Banco Lua · Ana (cartão, fatura de 10/12) · pago."""
    contas = contas if contas is not None else calc.mapa_contas(d)
    partes = [l.get("descricao") or "Sem descrição", _brl(calc.num(l.get("valor"))), _dm(l.get("data"))]
    if l.get("parcela"):
        partes[0] += f" ({l['parcela']})"
    cat = _nome_cat(d, l.get("categoria"))
    if cat:
        partes.append(cat)
    c = contas.get(l.get("conta"))
    if c:
        nome = calc.nome_conta(c)
        if l.get("cartao") and c.get("cartao"):
            dc = calc.data_caixa(l, contas, d)
            nome += f" (cartão de crédito, fatura de {_dm(dc.isoformat())})" if dc else " (cartão de crédito)"
        partes.append(nome)
    partes.append(_situacao(l))
    return " · ".join(partes)


def _pago_pela_data(d, l, hoje):
    dc = calc.data_caixa(l, calc.mapa_contas(d), d)
    return bool(dc and dc <= hoje)


def _meses(de, ate):
    ym, fim = de.isoformat()[:7], ate.isoformat()[:7]
    while ym <= fim:
        yield ym
        ym = integracao.add_ym(ym, 1)


# ---------------------------------------------------------------- leitura

def _lancamentos(d, a, hoje):
    de = _data(a.get("de"), hoje.replace(day=1), "de") if a.get("de") else hoje.replace(day=1)
    ate = _data(a.get("ate"), hoje, "ate") if a.get("ate") else calc._data_mes(hoje.year, hoje.month, 31)
    if ate < de:
        raise ErroFerramenta("O fim do período vem antes do começo.")
    if (ate - de).days > MAX_PERIODO:
        raise ErroFerramenta(f"Período grande demais (até {MAX_PERIODO} dias).")
    tipo = a.get("tipo") if a.get("tipo") in ("despesa", "receita") else None
    cat = _categoria(d, a["categoria"], tipo or "despesa") if a.get("categoria") and tipo else None
    if a.get("categoria") and not tipo:  # sem tipo: a categoria pode ser dos dois
        n = _norm(a["categoria"])
        achadas = [c.get("id") for c in d.get("categorias", []) if c.get("id") == a["categoria"] or _norm(c.get("nome")) == n]
        if not achadas:
            achadas = [c.get("id") for c in d.get("categorias", []) if n in _norm(c.get("nome"))]
        if not achadas:
            raise ErroFerramenta(f"Categoria não encontrada: {a['categoria']}.")
        cat = set(achadas)
    conta = _conta(d, a.get("conta")) if a.get("conta") else None
    busca = _norm(a.get("busca"))
    limite = max(1, min(int(calc.num(a.get("limite"), 200) or 200), MAX_LISTA))
    contas = calc.mapa_contas(d)
    achados = []
    for ym in _meses(de, ate):
        for l in calc.ocorrencias_mes(d, ym):
            dt = str(l.get("data") or "")[:10]
            if not (de.isoformat() <= dt <= ate.isoformat()):
                continue
            if tipo and l.get("tipo", "despesa") != tipo:
                continue
            if cat and l.get("categoria") not in (cat if isinstance(cat, set) else {cat}):
                continue
            if conta and l.get("conta") != conta:
                continue
            if busca and busca not in _norm(l.get("descricao")) and busca not in _norm(l.get("obs")):
                continue
            achados.append(l)
    achados.sort(key=lambda l: (str(l.get("data") or ""), str(l.get("descricao") or "")), reverse=True)
    entradas = saidas = 0.0
    por_cat = {}
    for l in achados:
        if l.get("ajuste"):
            continue
        v = calc.num(l.get("valor"))
        if l.get("tipo") == "receita":
            entradas += v
        else:
            saidas += v
            nome = _nome_cat(d, l.get("categoria")) or "Sem categoria"
            por_cat[nome] = por_cat.get(nome, 0) + v
    itens = []
    for l in achados[:limite]:
        virtual = bool(l.get("recorrencia")) and l.get("id") in (None, "", l.get("recorrencia"))  # o fixo ainda não lançado
        it = {"id": f"v:{l['recorrencia']}:{l['competencia']}" if virtual else (l.get("id") or ""),
              "data": l.get("data"), "tipo": "ajuste de saldo" if l.get("ajuste") else "desconto" if l.get("desconto") else
              "aporte" if l.get("aporte") else "recebimento" if l.get("tipo") == "receita" else "gasto",
              "descricao": l.get("descricao") or "", "valor": round(calc.num(l.get("valor")), 2),
              "categoria": _nome_cat(d, l.get("categoria")), "situacao": _situacao(l)}
        c = contas.get(l.get("conta"))
        if c:
            it["conta"] = calc.nome_conta(c) + (" · cartão de crédito" if l.get("cartao") and c.get("cartao") else "")
            dc = calc.data_caixa(l, contas, d)
            if dc and dc.isoformat() != it["data"]:
                it["data_caixa"] = dc.isoformat()
        for k in ("parcela", "obs"):
            if l.get(k):
                it[k] = l[k]
        if l.get("recorrencia"):
            it["fixo"] = "ainda não lançado" if virtual else True
        if l.get("desconto"):
            it["de"] = l.get("pai") or ""
            it.pop("id")
        itens.append(it)
    return _json({"periodo": {"de": de.isoformat(), "ate": ate.isoformat()}, "encontrados": len(achados), "mostrando": len(itens),
                  "entradas": round(entradas, 2), "saidas": round(saidas, 2),
                  "gastos_por_categoria": {k: round(v, 2) for k, v in sorted(por_cat.items(), key=lambda x: -x[1])},
                  "lancamentos": itens})


MESES_NOME = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")


def _gastos_do_mes(d, ym, ate_dia):
    """{categoria: total} das despesas de um mês até um dia (sem os ajustes de saldo, os aportes, o pagamento de fatura e os pulados)."""
    out = {}
    for l in calc.ocorrencias_mes(d, ym):
        dt = str(l.get("data") or "")[:10]
        if dt[:7] != ym or int(dt[8:10] or 0) > ate_dia or l.get("tipo") == "receita" or l.get("ajuste") or l.get("aporte") or l.get("vinculo") or l.get("pulado"):
            continue
        nome = _nome_cat(d, l.get("categoria")) or "Sem categoria"
        out[nome] = out.get(nome, 0.0) + calc.num(l.get("valor"))
    return out


def _comparar_meses(d, a, hoje):
    """1.96.0: os gastos por categoria de um mês contra outro, o que mais subiu primeiro."""
    def ym_de(v, campo):
        s = str(v or "").strip()
        if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", s):
            raise ErroFerramenta(f"{campo}: um mês, AAAA-MM.")
        return s
    agora = hoje.isoformat()[:7]
    mes = ym_de(a["mes"], "mes") if a.get("mes") else agora
    com = ym_de(a["com"], "com") if a.get("com") else integracao.add_ym(mes, -1)
    if mes == com:
        raise ErroFerramenta("Os dois meses são o mesmo.")
    if max(mes, com) > agora:
        raise ErroFerramenta("Um mês que ainda não chegou não tem gastos para comparar.")
    parcial = agora in (mes, com)
    dia = hoje.day if parcial else 31
    g1, g2 = _gastos_do_mes(d, mes, dia), _gastos_do_mes(d, com, dia)
    t1, t2 = sum(g1.values()), sum(g2.values())

    def nome(ym):
        return f"{MESES_NOME[int(ym[5:7]) - 1]} de {ym[:4]}" + (f" (até o dia {dia})" if parcial else "")

    def pct(v, antes):
        return f", {'+' if v >= antes else '−'}{abs(round((v - antes) / antes * 100))}%" if antes else ""
    linhas = [f"Gastos de {nome(mes)}: {_brl(t1)}; de {nome(com)}: {_brl(t2)}{pct(t1, t2)}."]
    if not g1 and not g2:
        return linhas[0] + " Nenhum gasto nos dois."
    dif = sorted(((g1.get(c, 0.0) - g2.get(c, 0.0), c) for c in set(g1) | set(g2)), key=lambda x: (-x[0], x[1]))
    subiu = [(v, c) for v, c in dif if v >= 0.005]
    caiu = [(v, c) for v, c in reversed(dif) if v <= -0.005]
    if subiu:
        linhas.append(f"Subiram ({len(subiu)}):")
        linhas += [f"- {c}: {_brl(g1.get(c, 0))} (antes {_brl(g2.get(c, 0))}; +{_brl(v)}{pct(g1.get(c, 0), g2.get(c, 0))})" for v, c in subiu[:10]]
    else:
        linhas.append("Nenhuma categoria subiu.")
    if caiu:
        linhas.append(f"Caíram ({len(caiu)}):")
        linhas += [f"- {c}: {_brl(g1.get(c, 0))} (antes {_brl(g2.get(c, 0))}; −{_brl(-v)})" for v, c in caiu[:10]]
    return "\n".join(linhas)


MAIS_CARO, MAIS_CARO_MIN = 1.3, 20.0     # 30% acima da média e pelo menos R$ 20 a mais
GRANDE, GRANDE_MIN, GRANDE_BASE = 3.0, 200.0, 5   # 3 vezes a mediana das compras, pelo menos R$ 200, com 5 compras para comparar


def _br_data(dt):
    return f"{dt[8:10]}/{dt[5:7]}"


def _chave_gasto(texto):
    """A descrição sem o que muda de um mês para outro: o mês, os números (a parcela 3/10, o ano) e a pontuação."""
    return calc.chave_descricao(texto)


def _despesas_do_mes(d, ym, ate_dia):
    """As despesas de um mês até um dia, uma a uma (as mesmas do _gastos_do_mes): [(chave, descrição, valor, data, fixo)]."""
    out = []
    for l in calc.ocorrencias_mes(d, ym):
        dt = str(l.get("data") or "")[:10]
        if dt[:7] != ym or int(dt[8:10] or 0) > ate_dia or l.get("tipo") == "receita" or l.get("ajuste") or l.get("aporte") or l.get("vinculo") or l.get("pulado"):
            continue
        desc = " ".join(str(l.get("descricao") or "").split())
        k, v = _chave_gasto(desc), calc.num(l.get("valor"))
        if k and v > 0:
            out.append((k, desc, v, dt, bool(l.get("recorrencia"))))
    return out


def _fora_do_padrao(d, hoje):
    """1.97.0: o que foge do costume nos gastos do mês, só com a conta (sem a IA): mais caro que a média dos 3 meses anteriores,
    repetido (descrição, valor e dia iguais) e a compra grande que não é de costume."""
    ym = hoje.isoformat()[:7]
    agora = _despesas_do_mes(d, ym, hoje.day)
    antes = [_despesas_do_mes(d, integracao.add_ym(ym, -i), 31) for i in (1, 2, 3)]
    por_mes = []
    for m in antes:
        t = {}
        for k, _, v, _, _ in m:
            t[k] = t.get(k, 0.0) + v
        por_mes.append(t)
    soma, nome = {}, {}
    for k, desc, v, _, _ in agora:
        soma[k] = soma.get(k, 0.0) + v
        nome.setdefault(k, desc)
    caro = []
    for k, v in soma.items():
        vs = [t[k] for t in por_mes if k in t]
        if len(vs) < 2:
            continue
        media = sum(vs) / len(vs)
        if v >= media * MAIS_CARO and v - media >= MAIS_CARO_MIN:
            caro.append((v - media, f"- {nome[k]}: {_brl(v)} (a média de {len(vs)} meses é {_brl(media)}; +{_brl(v - media)}, +{round((v - media) / media * 100)}%)"))
    vistos, rep = {}, []
    for k, desc, v, dt, _ in agora:
        vistos.setdefault((k, round(v, 2), dt), []).append(desc)
    for (k, v, dt), ls in vistos.items():
        if len(ls) > 1 and v >= 5:
            rep.append((dt, f"- {ls[0]}: {len(ls)} vezes de {_brl(v)} em {_br_data(dt)}"))
    base = sorted(v for m in antes for _, _, v, _, _ in m)
    grande = []
    if len(base) >= GRANDE_BASE:
        mediana = base[len(base) // 2] if len(base) % 2 else (base[len(base) // 2 - 1] + base[len(base) // 2]) / 2
        conhecidas = set().union(*por_mes) if por_mes else set()
        for k, desc, v, dt, fixo in agora:
            if not fixo and k not in conhecidas and v >= GRANDE_MIN and v >= mediana * GRANDE:
                grande.append((-v, f"- {desc}: {_brl(v)} em {_br_data(dt)} (uma compra de costume fica perto de {_brl(mediana)})"))
    n = len(caro) + len(rep) + len(grande)
    mes = f"{MESES_NOME[hoje.month - 1]} de {hoje.year} (até o dia {hoje.day})"
    if not n:
        return f"Nada fora do padrão nos gastos de {mes}."
    linhas = [f"Fora do padrão nos gastos de {mes}: {n}."]
    for titulo, ls in (("Mais caro que o costume", sorted(caro, key=lambda x: -x[0])), ("Parece repetido", sorted(rep)), ("Compra grande, fora do costume", sorted(grande))):
        if ls:
            linhas.append(f"{titulo} ({len(ls)}):")
            linhas += [t for _, t in ls[:10]]
    return "\n".join(linhas)


def _previsao_mes(d, hoje):
    """1.98.0: a previsão de gastos do mês, pela conta do calc.previsao_mes (a mesma do cartão do Agora)."""
    p = calc.previsao_mes(d, hoje)
    mes = f"{MESES_NOME[hoje.month - 1]} de {hoje.year}"
    falta = p["dias_mes"] - p["dia"]
    linhas = [f"Previsão de gastos de {mes}: {_brl(p['previsto'])}.",
              f"- Até hoje (dia {p['dia']}): {_brl(p['ate_hoje'])}",
              f"- Já marcado até o fim do mês (fixos, parcelas e contas lançadas): {_brl(p['marcado'])}"]
    if p["meses_base"] and falta:
        linhas.append(f"- Dia a dia que ainda deve vir ({_brl(p['por_dia'])} por dia, a média de {p['meses_base']} "
                      f"{'mês' if p['meses_base'] == 1 else 'meses'}, em {falta} {'dia' if falta == 1 else 'dias'}): {_brl(p['dia_a_dia'])}")
    if p["meses_base"]:
        dif = p["previsto"] - p["media"]
        pct = f", {abs(round(dif / p['media'] * 100))}% {'acima' if dif >= 0 else 'abaixo'}" if p["media"] else ""
        linhas.append((f"A média dos últimos {p['meses_base']} meses foi" if p["meses_base"] > 1 else "O mês anterior com gastos somou") + f" {_brl(p['media'])}{pct}.")
    else:
        linhas.append("Sem meses anteriores para comparar: a previsão é só o que já saiu e o que está marcado.")
    return "\n".join(linhas)


def _contas_a_pagar(d, a, hoje):
    de = _data(a.get("de"), hoje, "de") if a.get("de") else hoje
    ate = _data(a.get("ate"), hoje, "ate") if a.get("ate") else hoje + timedelta(days=45)
    try:
        r = integracao.listar(d, de, ate, hoje)
    except ValueError as e:
        raise ErroFerramenta(str(e)) from None
    out = []
    for c in r["contas"]:
        it = {"id": c["id"], "tipo": c["tipo"], "descricao": c["descricao"], "valor": c["valor"], "vencimento": c["vencimento"],
              "situacao": "paga" if c["pago"] else "atrasada" if c.get("atrasada") else "a pagar"}
        for k in ("categoria", "conta"):
            if c.get(k):
                it[k] = c[k]
        if c.get("itens"):
            it["compras"] = c["itens"]
        out.append(it)
    abertas = [c for c in out if c["situacao"] != "paga"]
    return _json({"hoje": hoje.isoformat(), "a_pagar": round(sum(c["valor"] for c in abertas), 2),
                  "atrasadas": round(sum(c["valor"] for c in abertas if c["situacao"] == "atrasada"), 2), "contas": out})


def _investimentos(d, hoje, bens=None):
    ind, corrigir = d.get("indices", {}), calc.corrige_valores(d)
    bancos = {b.get("id"): b.get("nome", "") for b in d.get("bancos", [])}
    out = []
    for i in d.get("investimentos", []):
        it = {"id": i.get("id"), "nome": i.get("nome", ""), "banco": bancos.get(i.get("banco"), ""), "tipo": i.get("tipo", ""),
              "de_quem": "meu" if i.get("titular") != "terceiros" else (i.get("terceiro") or "terceiros"),
              "valor_hoje": round(calc.valor_hoje(i, ind, corrigir, hoje), 2), "valor_informado": round(calc.num(i.get("valor")), 2),
              "informado_em": i.get("data_valor") or "", "rendimento": calc.rotulo_taxa(i),
              "liquidez": "diária" if i.get("liquidez") == "diaria" else "no vencimento"}
        if i.get("vencimento"):
            it["vencimento"] = i["vencimento"]
        if i.get("obs"):
            it["obs"] = i["obs"]
        if cotacoes.limpar_ticker(i.get("ticker")):  # 1.99.0: um papel da bolsa
            it.update(codigo=i["ticker"], quantidade=cotacoes.quantidade(i.get("qtd")))
            if isinstance(i.get("cotacao"), dict) and i["cotacao"].get("preco"):
                it["cotacao"] = i["cotacao"]["preco"]
        out.append(it)
    # 1.78.0: o patrimônio da tela (o placar do Agora): o seu, investido mais os bens (os do InventarIA, com o valor de
    # hoje); antes, a soma dos investimentos (com os de outras pessoas no total)
    casa = bens.get("hoje") or 0 if isinstance(bens, dict) and bens.get("ok") and bens.get("n") and d.get("ajustes", {}).get("bens") is not False else 0
    p = calc.patrimonio(d, hoje, casa)
    pat = {"patrimonio": p["patrimonio"], "investido": p["investido"], "bens": p["bens"], "de_outras_pessoas": p["de_outras_pessoas"],
           "rende_por_mes": p["rende_mes"], "como": "o da tela: só o seu, investido mais os bens; o rende por mês é antes do IR"}
    if casa:
        pat["bens_da_casa"] = {"valor_hoje": p["bens_da_casa"], "itens": bens.get("n"), "de_onde": "InventarIA, com a depreciação de cada categoria"}
    return _json({"patrimonio": pat, "investimentos": out})


def _cadastros(d):
    contas = []
    for k, c in calc.mapa_contas(d).items():
        it = {"id": k, "nome": calc.nome_conta(c), "banco": c.get("banco_nome", "")}
        if c.get("pessoa"):
            it["pessoa"] = c["pessoa"]
        it["cartao_de_debito"] = c.get("debito") is not False
        if c.get("cartao"):
            it["cartao_de_credito"] = {"fecha_dia": c.get("fechamento"), "vence_dia": c.get("vencimento")}
            if calc.num(c.get("limite"), 0) > 0:
                it["cartao_de_credito"]["limite"] = round(calc.num(c.get("limite")), 2)
            adic = [{"pessoa": a.get("pessoa"), **({"limite": "o mesmo do cartão principal"} if a.get("mesmo_limite") is True else
                                                   {"limite": round(calc.num(a.get("limite")), 2)} if calc.num(a.get("limite"), 0) > 0 else {})}
                    for a in (c.get("adicionais") or []) if isinstance(a, dict) and a.get("pessoa")]
            if adic:
                it["cartao_de_credito"]["adicionais"] = adic
        if c.get("debito_global"):
            it["cartao_de_debito_global"] = {"moeda": c["debito_global"], "adicional": c.get("debito_global_adicional") is True}
            if c.get("debito_global_adicional") is True and c.get("debito_global_para"):  # 1.77.0
                it["cartao_de_debito_global"]["adicional_para"] = str(c["debito_global_para"])
        if c.get("credito_global"):
            it["cartao_de_credito_global"] = {"moeda": c["credito_global"], "adicional": c.get("credito_global_adicional") is True}
            if c.get("credito_global_adicional") is True and c.get("credito_global_para"):
                it["cartao_de_credito_global"]["adicional_para"] = str(c["credito_global_para"])
        contas.append(it)
    fixos = []
    for r in d.get("recorrencias", []):
        it = {"id": r.get("id"), "descricao": r.get("descricao", ""), "tipo": r.get("tipo", "despesa"), "valor": round(calc.num(r.get("valor")), 2),
              "dia": r.get("dia"), "repete": "anual" if r.get("freq") == "anual" else "mensal", "desde": r.get("inicio")}
        if r.get("fim"):
            it["ate"] = r["fim"]
        if r.get("categoria"):
            it["categoria"] = _nome_cat(d, r["categoria"])
        fixos.append(it)
    terceiros = sorted({i.get("terceiro") for i in d.get("investimentos", []) if i.get("titular") == "terceiros" and i.get("terceiro")})
    return _json({"contas": contas, "categorias": [{"id": c.get("id"), "nome": c.get("nome", ""), "tipo": c.get("tipo", "despesa")} for c in d.get("categorias", [])],
                  "bancos": [{"id": b.get("id"), "nome": b.get("nome", "")} for b in d.get("bancos", [])], "fixos": fixos,
                  "pessoas_terceiros": terceiros, "tipos_investimento": {k: v[0] for k, v in TIPOS_INV.items()}, "rendimentos": INDEXADORES})


# ---------------------------------------------------------------- gravação

def _fmt_moeda(v, cod):
    return f"{cambio.MOEDAS[cod][1]} {calc.fmt_num(v, 2)}"


def _cotacao_de(moedas, cod):
    c = (moedas or {}).get(cod) or {}
    if not c.get("valor"):
        raise ErroFerramenta(f"Sem a cotação do {cambio.MOEDAS[cod][0].lower()} do Banco Central agora: diga o valor em reais.")
    return c


def _em_reais(a, moedas):
    """1.100.0: o lançamento dito em dólar, euro ou libra vira reais pela PTAX de hoje; a obs guarda o valor na moeda."""
    cod = cambio.moeda(a.get("moeda"))
    if cod not in cambio.MOEDAS:
        raise ErroFerramenta("moeda: USD, EUR ou GBP (em reais, não mande a moeda).")
    c = _cotacao_de(moedas, cod)
    v = _valor(a.get("valor"))
    nota = f"{_fmt_moeda(v, cod)} a R$ {calc.fmt_num(c['valor'], 4)} (Banco Central, {_dm(c['data'])[:5]})"
    obs = _texto(a.get("obs"), 400)
    return {**{k: x for k, x in a.items() if k != "moeda"}, "valor": round(v * c["valor"], 2), "obs": (obs + " · " if obs else "") + nota}


def texto_conta_de_luz(e, d):
    """O atual e o projetado da conta de luz do mês (a ferramenta conta_de_luz; quem lê o medidor é o server.py)."""
    if not e.get("ligado"):
        return "A conta de luz pelo consumo está desligada: liga em Mais › Configurações › Integrações › Conta de luz (o fixo, o medidor e o preço do kWh)."
    u = e.get("ultimo")
    if not u:
        return e.get("erro") or "Ainda não há consumo lido neste mês."
    fixo = next((r.get("descricao") for r in d.get("recorrencias", []) if r.get("id") == e.get("fixo")), "") or "o fixo"
    k = lambda v: calc.fmt_num(v, 1)  # noqa: E731
    out = [f"{fixo}, pelo consumo de energia deste mês:",
           f"- Até hoje (dia {u['dia']} de {u['dias']}): {k(u['kwh'])} kWh, {_brl(u['atual'])}",
           f"- Projeção do mês: {k(u['kwh_projetado'])} kWh, {_brl(u['projetado'])}",
           f"Conta: kWh × R$ {calc.fmt_num(e.get('preco') or 0, 4)}" + (f" + {calc.fmt_num(e.get('extra') or 0, 0)}%" if e.get("extra") else "") + "."]
    out.append("O fixo deste mês já está pago: o valor dele não muda." if u.get("pago") else "O fixo deste mês fica com a projeção até ser pago.")
    if e.get("erro"):
        out.append(e["erro"])
    return "\n".join(out)


def texto_cambio(moedas, a):
    """As cotações de hoje e, com valor, a conversão (a ferramenta cambio; quem busca a PTAX é o server.py)."""
    if not moedas:
        raise ErroFerramenta("O Banco Central não respondeu agora: tente daqui a pouco.")
    linhas = [f"- {cambio.MOEDAS[k][0]}: R$ {calc.fmt_num(moedas[k]['valor'], 4)} ({_dm(moedas[k]['data'])})" for k in cambio.MOEDAS if k in moedas]
    out = []
    if a.get("valor") is not None:
        v = _valor(a.get("valor"))
        cod = cambio.moeda(a.get("moeda") or "USD")
        if cod == "BRL":
            para = cambio.moeda(a.get("para") or "USD")
            if para not in cambio.MOEDAS:
                raise ErroFerramenta("para: USD, EUR ou GBP.")
            c = _cotacao_de(moedas, para)
            out.append(f"{_brl(v)} são {_fmt_moeda(v / c['valor'], para)} pela cotação de {_dm(c['data'])}.")
        elif cod in cambio.MOEDAS:
            c = _cotacao_de(moedas, cod)
            out.append(f"{_fmt_moeda(v, cod)} são {_brl(v * c['valor'])} pela cotação de {_dm(c['data'])}.")
        else:
            raise ErroFerramenta("moeda: USD, EUR, GBP ou BRL.")
    out += ["Cotação de venda do Banco Central (PTAX):"] + linhas
    out.append("No cartão ou na conta global o valor sai um pouco diferente (a cotação do banco e o IOF).")
    return "\n".join(out)


def _lancar(d, a, hoje):
    tipo = a.get("tipo")
    if tipo not in ("despesa", "receita"):
        raise ErroFerramenta("tipo: despesa (gasto) ou receita (recebimento).")
    desc = _texto(a.get("descricao"))
    if not desc:
        raise ErroFerramenta("Falta a descrição.")
    valor = _valor(a.get("valor"))
    data = _data(a.get("data"), hoje)
    # 1.98.0: sem categoria no pedido, a que a casa costuma dar a essa descrição (aprendida do que já foi lançado e corrigido)
    sem_cat = a.get("categoria") is None or str(a.get("categoria")).strip() == ""
    cat = (calc.categoria_aprendida(d, tipo, desc) if sem_cat else "") or _categoria(d, a.get("categoria"), tipo)
    conta = _conta(d, a.get("conta"))
    contas = calc.mapa_contas(d)
    cartao = tipo == "despesa" and a.get("cartao") is True
    if cartao and not (contas.get(conta) or {}).get("cartao"):
        raise ErroFerramenta("Essa conta não tem cartão de crédito." if conta else "Diga a conta do cartão de crédito.")
    base = {"tipo": tipo, "descricao": desc, "valor": valor, "categoria": cat, "conta": conta, "cartao": cartao, "obs": _texto(a.get("obs"), 500)}
    if tipo == "despesa" and cat == "c-investimentos":  # aplicação nos investimentos: uma saída do tipo Aporte
        base.update(aporte=True, cartao=False)
    total = int(calc.num(a.get("parcelas"), 0) or 0)
    atual = int(calc.num(a.get("parcela_atual"), 1) or 1)
    if total and not 2 <= total <= 120:
        raise ErroFerramenta("parcelas: de 2 a 120.")
    if total and not 1 <= atual <= total:
        raise ErroFerramenta("parcela_atual: de 1 até o total de parcelas.")
    iguais = [x for x in d.get("lancamentos", []) if not x.get("pulado") and x.get("data") == data.isoformat()
              and abs(calc.num(x.get("valor")) - valor) < 0.005 and _norm(x.get("descricao")) == _norm(desc)]
    novos = []
    if total:
        grupo = "g-" + integracao.uid()
        for p in range(atual, total + 1):
            dt = calc._data_mes(data.year, data.month + (p - atual), data.day).isoformat()
            novos.append(dict(base, id=integracao.uid(), data=dt, parcela=f"{p}/{total}", grupo=grupo, pago=False))
        novos[0]["pago"] = a["pago"] if isinstance(a.get("pago"), bool) else _pago_pela_data(d, novos[0], hoje)
    else:
        l = dict(base, id=integracao.uid(), data=data.isoformat())
        l["pago"] = a["pago"] if isinstance(a.get("pago"), bool) else _pago_pela_data(d, l, hoje)
        novos.append(l)
    d["lancamentos"].extend(novos)
    if len(novos) == 1:
        txt = "Lançado: " + _descrever(d, novos[0], contas) + f". id: {novos[0]['id']}"
    else:
        txt = (f"Lançadas {len(novos)} parcelas de {_brl(valor)} ({novos[0]['parcela']} a {novos[-1]['parcela']}), de "
               f"{_dm(novos[0]['data'])} a {_dm(novos[-1]['data'])}. A primeira: " + _descrever(d, novos[0], contas)
               + ". ids: " + ", ".join(x["id"] for x in novos))
    if iguais:
        txt += f"\nAtenção: já havia um lançamento igual (id {iguais[0].get('id')}). Se foi engano, apague um deles."
    return txt


def _achar_lanc(d, lid):
    lid = str(lid or "").strip()
    if not lid:
        raise ErroFerramenta("Falta o id.")
    if lid.startswith("f:"):
        raise ErroFerramenta("Isso é uma fatura de cartão: mude as compras dela, uma a uma.")
    try:
        return integracao._achar(d, lid)
    except LookupError:
        raise ErroFerramenta(f"Não encontrei o lançamento {lid}. Busque o id com gerencia_lancamentos.") from None
    except ValueError:
        raise ErroFerramenta(f"Id inválido: {lid}.") from None


def _real(d, l):
    """O lançamento que fica nos dados: um fixo ainda não lançado vira lançamento daquele mês."""
    if l.get("virtual"):
        x = integracao._materializar(l, pago=False)
        d["lancamentos"].append(x)
        return x
    return l


def _editar(d, a, hoje):
    l = _achar_lanc(d, a.get("id"))
    contas = calc.mapa_contas(d)
    antes = _descrever(d, l, contas)
    novo = {}
    if "descricao" in a:
        novo["descricao"] = _texto(a["descricao"]) or l.get("descricao", "")
    if "valor" in a:
        novo["valor"] = _valor(a["valor"])
    if "data" in a:
        novo["data"] = _data(a["data"], hoje).isoformat()
    if "categoria" in a:
        novo["categoria"] = _categoria(d, a["categoria"], l.get("tipo", "despesa"))
    if "conta" in a:
        novo["conta"] = _conta(d, a["conta"])
    if "obs" in a:
        novo["obs"] = _texto(a["obs"], 500)
    if "pago" in a:
        novo["pago"] = a["pago"] is True
    if "cartao" in a or "conta" in novo:
        cartao = (a.get("cartao") if "cartao" in a else l.get("cartao")) is True and l.get("tipo") != "receita"
        conta = novo.get("conta", l.get("conta"))
        if cartao and not (contas.get(conta) or {}).get("cartao"):
            if "cartao" in a:
                raise ErroFerramenta("Essa conta não tem cartão de crédito.")
            cartao = False
        novo["cartao"] = cartao
    if not novo:
        raise ErroFerramenta("Diga o que muda (descricao, valor, data, categoria, conta, cartao, pago ou obs).")
    if l.get("pulado"):
        raise ErroFerramenta("Esse lançamento foi apagado deste mês.")
    x = _real(d, l)
    x.update(novo)
    if x.get("aporte"):
        x["cartao"] = False
    return f"Alterado: {_descrever(d, x, contas)}. Antes: {antes}. id: {x['id']}"


def texto_dicas(valem, assinaturas, desligadas=False):
    """1.95.0: as dicas de economia para a IA: as que valem (o plano anual, com o que sobra por ano) e as assinaturas achadas."""
    if desligadas:
        return "As dicas de economia estão desligadas no GerencIA (Mais › Configurações › Opções)."
    if not assinaturas:
        return "O GerencIA não achou assinaturas nos fixos nem nas faturas: sem dicas por enquanto."
    L = []
    if valem:
        L.append(f"{len(valem)} {'dica' if len(valem) == 1 else 'dicas'} de economia (pagar o plano anual; o que sobra por ano, já com o que o dinheiro renderia):")
        L += [f"- {x['nome']}: paga {_brl(x['valor'])} por mês; o anual custa {_brl(x['preco_anual'])} e sobram uns {_brl(x['real'])} por ano"
              + (f" (preço conferido em {_dm(str(x['conferido'])[:10])})" if x.get("conferido") else "") for x in valem[:10]]
    else:
        L.append("Nenhuma dica de economia agora.")
    resto = [a for a in assinaturas if not any(v.get("chave") == a.get("chave") for v in valem)]
    if resto:
        L.append("As outras assinaturas que o app acompanha: " + "; ".join(f"{a['nome']} ({_brl(a['valor'])})" for a in resto[:12]) + ".")
    return "\n".join(L)


def _baixa_vinculados(d, rec):
    """baixaVinculados do app.js: a receita fixa recebida (ou desfeita) leva junto as despesas fixas e avulsas vinculadas a ela
    no mesmo mês (o mesmo dia, a mesma conta, fora do cartão)."""
    if not rec or not rec.get("recorrencia") or rec.get("tipo") != "receita":
        return
    ym = rec.get("competencia") or str(rec.get("data") or "")[:7]
    pago = bool(rec.get("pago"))
    for r in d.get("recorrencias", []):
        if r.get("tipo") == "receita" or r.get("vinculo") != rec["recorrencia"] or not calc.ativa_em(r, ym):
            continue
        x = next((y for y in d["lancamentos"] if y.get("recorrencia") == r.get("id") and y.get("competencia") == ym), None)
        if x:
            if not x.get("pulado"):
                x.update(pago=pago, data=rec.get("data"), conta=rec.get("conta") or x.get("conta", ""), cartao=False)
        elif pago:
            d["lancamentos"].append(integracao._materializar(dict(r, data=rec.get("data"), recorrencia=r["id"], competencia=ym),
                                                             pago=True, conta=rec.get("conta") or r.get("conta", ""), cartao=False))
    for x in d["lancamentos"]:
        if x.get("tipo") != "receita" and not x.get("recorrencia") and x.get("vinculo") == rec["recorrencia"] and str(x.get("data") or "")[:7] == ym:
            x.update(pago=pago, data=rec.get("data"), conta=rec.get("conta") or x.get("conta", ""), cartao=False)


def _alterar_lote(d, a, hoje):
    """O Alterar do Caixa › Selecionar (lselAlterar e mutLote do app.js): a categoria e a situação de vários, de um tipo só."""
    ids = a.get("ids")
    if not isinstance(ids, list) or not ids:
        raise ErroFerramenta("ids: a lista dos ids (de gerencia_lancamentos).")
    if "categoria" not in a and "pago" not in a:
        raise ErroFerramenta("Diga o que muda: categoria e/ou pago.")
    if "pago" in a and not isinstance(a["pago"], bool):
        raise ErroFerramenta("pago é true ou false.")
    ls = [_achar_lanc(d, i) for i in dict.fromkeys(str(x) for x in ids)]
    nao = [l for l in ls if str(l.get("id")).startswith("d:") or l.get("desconto") or (l.get("vinculo") and l.get("tipo") != "receita")
           or l.get("ajuste") or l.get("aporte") or l.get("pulado")]
    if nao:
        raise ErroFerramenta("Estes não mudam assim (desconto, despesa vinculada a um recebimento, ajuste, aporte ou apagado do mês): "
                             + "; ".join(_descrever(d, l) for l in nao) + ".")
    tipos = {l.get("tipo", "despesa") for l in ls}
    if len(tipos) > 1:
        raise ErroFerramenta("Uma seleção é de um tipo só: mande só despesas ou só receitas.")
    tipo = tipos.pop()
    if "pago" in a and any(l.get("cartao") for l in ls):
        raise ErroFerramenta("Compras no cartão não mudam a situação (quem paga é a fatura): tire-as do pedido ou mude só a categoria.")
    cat = _categoria(d, a["categoria"], tipo) if "categoria" in a else None
    n = 0
    for l in ls:
        muda = {}
        if cat is not None and (l.get("categoria") or "") != cat:
            muda["categoria"] = cat
        if "pago" in a and bool(l.get("pago")) != a["pago"]:
            muda["pago"] = a["pago"]
        if not muda:
            continue
        x = integracao._materializar(l, **muda) if l.get("virtual") else l
        if l.get("virtual"):
            d["lancamentos"].append(x)
        else:
            x.update(muda)
        if "pago" in muda:
            _baixa_vinculados(d, x)
        n += 1
    if not n:
        return f"Nada mudou: os {len(ls)} já estavam assim."
    o_que = " e ".join(([f"categoria {next((c.get('nome') for c in d['categorias'] if c.get('id') == cat), cat) or 'sem categoria'}"] if cat is not None else [])
                       + ([("recebido" if a["pago"] else "a receber") if tipo == "receita" else ("pago" if a["pago"] else "a pagar")] if "pago" in a else []))
    return f"{n} {'lançamento alterado' if n == 1 else 'lançamentos alterados'} ({o_que})" + (f"; {len(ls) - n} já estavam assim." if n < len(ls) else ".")


def _apagar(d, a, hoje):
    l = _achar_lanc(d, a.get("id"))
    txt = _descrever(d, l)
    if l.get("recorrencia"):  # num fixo, só o daquele mês: a ocorrência fica marcada como pulada (como no app)
        x = integracao._materializar(l, pulado=True) if l.get("virtual") else l
        if l.get("virtual"):
            d["lancamentos"].append(x)
        x["pulado"] = True
        return f"Apagado só deste mês (o fixo continua nos outros): {txt}"
    d["lancamentos"] = [x for x in d["lancamentos"] if x.get("id") != l.get("id")]
    return f"Apagado: {txt}"


def _marcar_pago(d, a, hoje):
    cid = str(a.get("id") or "").strip()
    pago = a.get("pago") is not False
    valor = _valor(a["valor"]) if a.get("valor") not in (None, "", 0) else None
    if cid.startswith("f:"):
        try:
            f = integracao._achar_fatura(d, cid)
        except (LookupError, ValueError):
            raise ErroFerramenta(f"Fatura não encontrada: {cid}. Veja em gerencia_contas_a_pagar.") from None
        if valor is not None:
            raise ErroFerramenta("Uma fatura se paga inteira (sem valor). Para mudar um valor, edite a compra.")
        integracao.pagar(d, cid, None, pago=pago)
        return f"{'Paga' if pago else 'Voltou para a pagar'}: {f['descricao']} · {_brl(f['valor'])} · vence {_dm(f['vencimento'])} ({f['itens']} compras)."
    l = _achar_lanc(d, cid)
    if l.get("pulado"):
        raise ErroFerramenta("Esse lançamento foi apagado deste mês.")
    if l.get("ajuste") or l.get("desconto"):
        raise ErroFerramenta("Esse lançamento não se paga.")
    x = integracao._marcar(d, l, pago, valor if pago else None)
    if x is None:
        return f"Já estava a pagar: {_descrever(d, l)}."
    return ("Marcado: " if pago else "Desfeito: ") + _descrever(d, x) + f". id: {x['id']}"


def _definir_valor(inv, novo, data, ind, corrigir, hoje):
    """definirValor do app.js: um bem separado por categoria divide o valor novo na proporção de hoje."""
    novo = round(novo, 2)
    if inv.get("tipo") == "bens" and isinstance(inv.get("partes"), list) and inv["partes"]:
        ps = calc.partes_hoje(inv, ind, corrigir, hoje)
        tot = sum(p["valor"] for p in ps)
        resto, partes = novo, []
        for k, p in enumerate(inv["partes"]):
            v = resto if k == len(ps) - 1 else (round(ps[k]["valor"] * novo / tot, 2) if tot > 0 else 0)
            resto = round(resto - v, 2)
            partes.append(dict(p, valor=v))
        inv["partes"] = partes
    inv.update(valor=novo, data_valor=data.isoformat(), atualizado_em=datetime.now().isoformat(timespec="seconds"))


def _atualizar_inv(d, a, hoje):
    iid = str(a.get("id") or "").strip()
    inv = next((i for i in d.get("investimentos", []) if i.get("id") == iid), None)
    if not inv:
        raise ErroFerramenta(f"Investimento não encontrado: {iid}. Veja os ids em gerencia_investimentos.")
    dados = [k for k in ("saldo", "aporte", "resgate", "quantidade") if a.get(k) is not None]
    if len(dados) != 1:
        raise ErroFerramenta("Mande um só: saldo (o de agora), aporte, resgate ou, num papel da bolsa, quantidade.")
    ind, corrigir = d.get("indices", {}), calc.corrige_valores(d)
    antes = round(calc.valor_hoje(inv, ind, corrigir, hoje), 2)
    if dados[0] == "quantidade":  # 1.99.0: um papel da bolsa: a quantidade de agora; o valor é ela vezes a última cotação
        q = cotacoes.quantidade(a["quantidade"])
        if not cotacoes.limpar_ticker(inv.get("ticker")):
            raise ErroFerramenta("Esse investimento não tem código da bolsa: mande saldo, aporte ou resgate.")
        if not q:
            raise ErroFerramenta("quantidade: quantas ações ou cotas, um número maior que zero.")
        inv["qtd"] = q
        preco = (inv.get("cotacao") or {}).get("preco")
        if preco:
            _definir_valor(inv, round(q * preco, 2), hoje, ind, corrigir, hoje)
            return f"Atualizado: {inv.get('nome', '')}: {q:g} de {inv['ticker']} a {_brl(preco)} = {_brl(round(q * preco, 2))} (antes {_brl(antes)})."
        return f"Atualizado: {inv.get('nome', '')}: {q:g} de {inv['ticker']}. O valor entra na próxima atualização das cotações."
    k = dados[0]
    v = _valor(a[k], k, zero=k == "saldo")
    novo = v if k == "saldo" else antes + v if k == "aporte" else antes - v
    if novo < 0:
        raise ErroFerramenta(f"O resgate é maior que o valor de hoje ({_brl(antes)}).")
    _definir_valor(inv, novo, hoje, ind, corrigir, hoje)
    dif = round(novo - antes, 2)
    obs = "sem mudança" if abs(dif) < 0.005 else f"{'aporte' if dif > 0 else 'resgate'} de {_brl(abs(dif))}"
    return f"Atualizado: {inv.get('nome', '')}: {_brl(antes)} → {_brl(novo)} ({obs})."


def _ajustar_saldo(d, a, hoje):
    """O Ajustar saldo da tela (confirmarAjuste no app.js): a diferença para o saldo dito vira um lançamento de ajuste, pago hoje."""
    v = a.get("saldo")
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or abs(v) > 1e11:
        raise ErroFerramenta("saldo precisa ser um número, em reais (o saldo certo de agora).")
    antes = round(calc.caixa(d, hoje)["saldo"], 2)
    dif = round(float(v) - antes, 2)
    if abs(dif) < 0.01:
        return f"O saldo já está certo: {_brl(antes)}."
    d["lancamentos"].append({"id": integracao.uid(), "tipo": "receita" if dif > 0 else "despesa", "descricao": "Ajuste de saldo", "valor": abs(dif),
                             "categoria": "", "conta": "", "cartao": False, "data": hoje.isoformat(), "pago": True, "ajuste": True, "obs": ""})
    return f"Saldo ajustado: {_brl(antes)} → {_brl(round(float(v), 2))} (ajuste de {'+' if dif > 0 else '-'}{_brl(abs(dif))})."


def _novo_inv(d, a, hoje):
    nome = _texto(a.get("nome"), 80)
    if not nome:
        raise ErroFerramenta("Falta o nome.")
    tipo = a.get("tipo")
    if tipo not in TIPOS_INV:
        raise ErroFerramenta("Tipo inválido. Use: " + ", ".join(TIPOS_INV) + ".")
    _, idx_p, taxa_p, liq_p = TIPOS_INV[tipo]
    idx = a.get("indexador") or idx_p
    if idx not in INDEXADORES:
        raise ErroFerramenta("Rendimento inválido. Use: " + ", ".join(INDEXADORES) + ".")
    taxa = 0 if idx in ("poupanca", "parado") else (calc.num(a.get("taxa")) if a.get("taxa") is not None else (taxa_p if idx == idx_p else 0))
    liq = a.get("liquidez") if a.get("liquidez") in ("diaria", "vencimento") else liq_p
    venc = _data(a.get("vencimento"), hoje, "vencimento").isoformat() if a.get("vencimento") else None
    # 1.99.0: um papel da bolsa: o código e a quantidade (o valor vem da cotação; sem ela ainda, o que a pessoa disse ou zero)
    ticker = cotacoes.limpar_ticker(a.get("codigo")) if a.get("codigo") else ""
    qtd = cotacoes.quantidade(a.get("quantidade")) if a.get("quantidade") is not None else 0
    if a.get("codigo") and not ticker:
        raise ErroFerramenta("codigo: o código na bolsa, como PETR4 ou MXRF11.")
    if bool(ticker) != bool(qtd):
        raise ErroFerramenta("Num papel da bolsa, mande o codigo e a quantidade juntos.")
    if a.get("valor") is None and not ticker:
        raise ErroFerramenta("Falta o valor de hoje.")
    valor = _valor(a.get("valor"), zero=True) if a.get("valor") is not None else 0
    banco_nome = _texto(a.get("banco"), 60)
    b = None
    if banco_nome:
        n = _norm(banco_nome)
        b = next((x for x in d["bancos"] if _norm(x.get("nome")) == n), None) or \
            next((x for x in d["bancos"] if _norm(x.get("nome")) and (_norm(x.get("nome")) in n or n in _norm(x.get("nome")))), None)
        if not b:
            usadas = {x.get("cor") for x in d["bancos"]}
            b = {"id": "b-" + integracao.uid(), "nome": banco_nome, "cor": next((c for c in CORES_BANCO if c not in usadas), CORES_BANCO[0]),
                 "obs": "", "contas": []}
            d["bancos"].append(b)
    dono = _texto(a.get("de_quem"), 60)
    if _norm(dono) in ("meu", "minha", "eu", "proprio", "propria"):
        dono = ""
    agora = datetime.now().isoformat(timespec="seconds")
    inv = {"id": integracao.uid(), "nome": nome, "banco": b["id"] if b else "", "tipo": tipo, "valor": valor, "data_valor": hoje.isoformat(),
           "indexador": idx, "taxa": taxa, "liquidez": liq, "vencimento": venc, "titular": "terceiros" if dono else "meu", "terceiro": dono,
           "obs": "", "fotos": [], "criado_em": agora, "atualizado_em": agora}
    if ticker:
        inv.update(ticker=ticker, qtd=qtd)
    d["investimentos"].append(inv)
    return (f"Cadastrado: {nome}{' · ' + b['nome'] if b else ''} · {TIPOS_INV[tipo][0]} · {calc.rotulo_taxa(inv)} · {_brl(valor)}"
            + (f" · {qtd:g} de {ticker} (o valor acompanha a cotação, com a chave da brapi posta no app)" if ticker else "")
            + (f" · vence {_dm(venc)}" if venc else "") + (f" · de {dono}" if dono else "") + f". id: {inv['id']}")


def _novo_fixo(d, a, hoje):
    tipo = a.get("tipo")
    if tipo not in ("despesa", "receita"):
        raise ErroFerramenta("tipo: despesa (gasto) ou receita (recebimento).")
    desc = _texto(a.get("descricao"))
    if not desc:
        raise ErroFerramenta("Falta a descrição.")
    valor = _valor(a.get("valor"))
    data = _data(a.get("data"), hoje, padrao=False)
    cat = _categoria(d, a.get("categoria"), tipo)
    conta = _conta(d, a.get("conta"))
    cartao = tipo == "despesa" and a.get("cartao") is True
    if cartao and not (calc.mapa_contas(d).get(conta) or {}).get("cartao"):
        raise ErroFerramenta("Essa conta não tem cartão de crédito." if conta else "Diga a conta do cartão de crédito.")
    anual = a.get("repete") == "anual"
    r = {"id": "r-" + integracao.uid(), "tipo": tipo, "descricao": desc, "valor": valor, "categoria": cat, "conta": conta, "cartao": cartao,
         "obs": "", "dia": data.day, "inicio": data.isoformat()[:7], "fim": None}
    if anual:
        r["freq"] = "anual"
    if tipo == "despesa" and cat == "c-investimentos":
        r.update(aporte=True, cartao=False)
    d["recorrencias"].append(r)
    quando = f"todo ano em {data.day:02d}/{data.month:02d}" if anual else f"todo dia {data.day}"
    return (f"Fixo cadastrado: {desc} · {_brl(valor)} · {quando}, a partir de {_dm(data.isoformat())}"
            + (f" · {_nome_cat(d, cat)}" if cat else "") + f". O deste mês: id v:{r['id']}:{data.isoformat()[:7]}.")


# ---------------------------------------------------------------- fixos, benefícios, categorias e bancos (1.88.0)

def _fixo(d, v):
    v = str(v or "").strip()
    rid = v.split(":")[1] if v.startswith("v:") and v.count(":") == 2 else v
    r = next((x for x in d.get("recorrencias", []) if x.get("id") == rid), None)
    if not r:
        n = _norm(v)
        achados = [x for x in d.get("recorrencias", []) if n and _norm(x.get("descricao")) == n]
        r = achados[0] if len(achados) == 1 else None
    if not r:
        fixos = ", ".join(f"{x.get('descricao')} ({x.get('id')})" for x in d.get("recorrencias", [])) or "nenhum"
        raise ErroFerramenta(f"Fixo não encontrado: {v}. Os fixos: {fixos}.")
    return r


def _ym_de(v, hoje):
    s = str(v or "").strip()
    if not s:
        return hoje.isoformat()[:7]
    if not re.fullmatch(r"\d{4}-\d{2}", s[:7]) or not 1 <= int(s[5:7]) <= 12:
        raise ErroFerramenta(f"a_partir inválido: {v}. Use AAAA-MM.")
    return s[:7]


def _editar_fixo(d, a, hoje):
    r = _fixo(d, a.get("id"))
    mud = []
    if a.get("descricao") not in (None, ""):
        r["descricao"] = _texto(a["descricao"], 60)
        mud.append("descrição")
    if a.get("valor") is not None:
        r["valor"] = _valor(a["valor"])
        mud.append("valor")
    if a.get("dia") is not None:
        dia = int(calc.num(a["dia"], 0))
        if not 1 <= dia <= 31:
            raise ErroFerramenta("dia: de 1 a 31.")
        r["dia"] = dia
        mud.append("dia")
    if a.get("categoria") is not None:
        r["categoria"] = _categoria(d, a["categoria"], r.get("tipo", "despesa"))
        mud.append("categoria")
    if a.get("conta") is not None:
        r["conta"] = _conta(d, a["conta"])
        if not r["conta"]:
            r["cartao"] = False
        mud.append("conta")
    if isinstance(a.get("cartao"), bool):
        if a["cartao"] and not (calc.mapa_contas(d).get(r.get("conta")) or {}).get("cartao"):
            raise ErroFerramenta("A conta desse fixo não tem cartão de crédito.")
        r["cartao"] = a["cartao"] and r.get("tipo") == "despesa"
        mud.append("cartão")
    if not mud:
        raise ErroFerramenta("Diga o que muda: descricao, valor, dia, categoria, conta ou cartao.")
    quando = "todo ano" if r.get("freq") == "anual" else f"todo dia {r.get('dia')}"
    return (f"Fixo mudado ({', '.join(mud)}): {r.get('descricao')} · {_brl(calc.num(r.get('valor')))} · {quando}"
            + (f" · {_nome_cat(d, r.get('categoria'))}" if r.get("categoria") else "") + ". Os meses já lançados ficam como foram.")


def _encerrar_fixo(d, a, hoje):
    r = _fixo(d, a.get("id"))
    rid = r["id"]
    if a.get("apagar_tudo") is True:
        n = len([x for x in d["lancamentos"] if x.get("recorrencia") == rid and not x.get("pulado")])
        d["recorrencias"] = [x for x in d["recorrencias"] if x.get("id") != rid]
        d["lancamentos"] = [x for x in d["lancamentos"] if x.get("recorrencia") != rid]
        for x in d["recorrencias"] + d["lancamentos"]:  # as despesas descontadas deste recebimento ficam por conta própria
            if x.get("vinculo") == rid:
                x.pop("vinculo", None)
        return f"Fixo apagado: {r.get('descricao')}" + (f", com os {n} meses que ele já tinha lançado." if n else ".")
    ym = _ym_de(a.get("a_partir"), hoje)
    if ym <= (r.get("inicio") or ""):
        d["recorrencias"] = [x for x in d["recorrencias"] if x.get("id") != rid]
    else:
        y, m = int(ym[:4]), int(ym[5:7]) - 1
        r["fim"] = f"{y - (m == 0):04d}-{(m - 1) % 12 + 1 if m else 12:02d}"
    d["lancamentos"] = [x for x in d["lancamentos"] if not (x.get("recorrencia") == rid and (x.get("competencia") or "") >= ym and not x.get("pago"))]
    return f"Fixo encerrado: {r.get('descricao')} não aparece mais a partir de {ym[5:]}/{ym[:4]}. O que já foi lançado antes continua."


def _beneficio(d, v):
    v = str(v or "").strip()
    bs = [b for b in d.get("beneficios", []) if isinstance(b, dict)]
    b = next((x for x in bs if x.get("id") == v), None)
    if not b:
        n = _norm(v)
        achados = [x for x in bs if n and (_norm(x.get("nome")) == n or _norm(f"{x.get('nome')} {x.get('pessoa') or ''}") == n)] or \
                  [x for x in bs if n and n in _norm(f"{x.get('nome')} {x.get('pessoa') or ''}")]
        b = achados[0] if len(achados) == 1 else None
    if not b:
        nomes = ", ".join(f"{x.get('nome')}{' · ' + x['pessoa'] if x.get('pessoa') else ''} ({x.get('id')})" for x in bs) or "nenhum cadastrado"
        raise ErroFerramenta(f"Benefício não encontrado: {v}. Os de Mais › Benefícios: {nomes}.")
    return b


def _usar_beneficio(d, a, hoje):
    b = _beneficio(d, a.get("beneficio"))
    data = _data(a.get("data"), hoje)
    if b.get("tipo") == "vantagem":
        raise ErroFerramenta(f"{b.get('nome')} é uma vantagem: não tem o que descontar.")
    milhas = b.get("tipo") == "milhas"
    if b.get("tipo") == "contagem" and a.get("quantidade") is None:
        qtd = 1.0
    elif a.get("quantidade") is None:
        raise ErroFerramenta("Diga a quantidade: " + ("as milhas resgatadas." if milhas else "o valor usado."))
    else:
        qtd = _valor(a.get("quantidade"), "quantidade")
    if milhas:
        qtd = float(round(qtd))
    b["usos"] = (b.get("usos") or []) + [{"id": "u-" + integracao.uid(), "data": data.isoformat(), "qtd": qtd}]
    b["usos"] = b["usos"][-200:]
    if milhas:
        m = calc.milhas_de(b, hoje)
        return f"Resgate anotado em {b.get('nome')}{' · ' + b['pessoa'] if b.get('pessoa') else ''}: {calc.fmt_num(qtd, 0)} milhas. Ficam {calc.fmt_num(m['saldo'], 0)}."
    cb = calc.ciclo_beneficio(b, hoje)
    resto = _brl(cb["restante"] or 0) if b.get("tipo") == "saldo" else calc.fmt_num(cb["restante"] or 0, 0)
    return f"Uso anotado em {b.get('nome')} ({_dm(data.isoformat())}). Restam {resto} neste período."


# 1.103.0 (o dono, com a foto de um crédito e «adiciona esse saldo… na parte de benefícios pendentes para usar», que a IA não
# sabia fazer): cadastrar, mudar e apagar um benefício, com as regras do salvarBeneficio da tela
MAX_BENEFICIOS = 200


def _origem_beneficio(d, v):
    """«fixo:<id>» ou «conta:<id>» pelo nome de um fixo ou de um banco cadastrado; vazio fica sem origem."""
    v = _texto(v, 80)
    if not v:
        return ""
    if re.fullmatch(r"(fixo|conta):[A-Za-z0-9_-]+", v):
        return v
    n = _norm(v)
    fixos = [r for r in d.get("recorrencias", []) if isinstance(r, dict) and _norm(r.get("descricao")) == n]
    if len(fixos) == 1:
        return "fixo:" + fixos[0]["id"]
    b = _banco_por_nome(d, v)
    contas = [c for c in (b.get("contas") or []) if isinstance(c, dict) and c.get("id")] if b else []
    if contas:
        return "conta:" + contas[0]["id"]
    return ""


def _campos_beneficio(b, a, hoje):
    conta = b["tipo"] != "vantagem"
    if "total" in a and conta:
        b["total"] = _valor(a.get("total"), "total")
    if conta and not (b.get("total") or 0) > 0:
        raise ErroFerramenta("Falta o total: " + ("o valor do saldo." if b["tipo"] == "saldo" else "quantos usos."))
    if not conta:
        b.pop("total", None)
    if b["tipo"] == "saldo":
        if "moeda" in a and a.get("moeda") not in ("BRL", "USD"):
            raise ErroFerramenta("moeda: BRL ou USD.")
        b["moeda"] = a.get("moeda") or b.get("moeda") or "BRL"
    else:
        b.pop("moeda", None)
    if "renova" in a and a.get("renova") not in ("mes", "ano", "nunca"):
        raise ErroFerramenta("renova: mes, ano ou nunca.")
    b["renova"] = (a.get("renova") or b.get("renova") or "nunca") if conta else "nunca"
    if "validade" in a:
        if _texto(a.get("validade")):
            b["validade"] = _data(a.get("validade"), hoje, "validade", padrao=False).isoformat()
        else:
            b.pop("validade", None)
    if "observacao" in a:
        if _texto(a.get("observacao"), 80):
            b["obs"] = _texto(a.get("observacao"), 80)
        else:
            b.pop("obs", None)
    if _texto(a.get("descricao"), 200):
        b["descricao"] = _texto(a.get("descricao"), 200)


def _texto_beneficio(b):
    if b["tipo"] == "vantagem":
        quanto = "vantagem"
    elif b["tipo"] == "saldo":
        quanto = ("US$ " + calc.fmt_num(b["total"], 2)) if b.get("moeda") == "USD" else _brl(b["total"])
    else:
        quanto = calc.fmt_num(b["total"], 0) + (" uso" if b["total"] == 1 else " usos")
    renova = {"mes": ", renova todo mês", "ano": ", renova todo ano"}.get(b.get("renova"), "")
    return f"{b['nome']}: {quanto}{renova}{', vale até ' + _dm(b['validade']) if b.get('validade') else ''}"


def _novo_beneficio(d, a, hoje):
    nome = _texto(a.get("nome"), 60)
    if not nome:
        raise ErroFerramenta("Falta o nome do benefício.")
    if a.get("tipo") not in ("saldo", "contagem", "vantagem"):
        raise ErroFerramenta("tipo: saldo (um valor para gastar), contagem (uma quantidade de usos) ou vantagem.")
    bs = d.setdefault("beneficios", [])
    if len(bs) >= MAX_BENEFICIOS:
        raise ErroFerramenta(f"Já há {MAX_BENEFICIOS} benefícios cadastrados.")
    if any(isinstance(x, dict) and x.get("tipo") != "milhas" and _norm(x.get("nome")) == _norm(nome) for x in bs):
        raise ErroFerramenta(f"Já há um benefício «{nome}». Para mudar, use gerencia_editar_beneficio.")
    b = {"id": "bn-" + integracao.uid(), "nome": nome, "origem": _origem_beneficio(d, a.get("origem")), "tipo": a["tipo"],
         "renova": "nunca", "desde": hoje.isoformat(), "usos": []}
    _campos_beneficio(b, a, hoje)
    bs.append(b)
    return f"Benefício cadastrado em Mais › Benefícios: {_texto_beneficio(b)}."


def _editar_beneficio(d, a, hoje):
    b = _beneficio(d, a.get("beneficio"))
    if a.get("apagar") is True:
        d["beneficios"] = [x for x in d.get("beneficios", []) if x is not b]
        return f"Benefício apagado: {b.get('nome')}."
    if b.get("tipo") == "milhas":
        raise ErroFerramenta(f"{b.get('nome')} é um programa de milhas: o saldo muda pelo gerencia_atualizar_milhas.")
    if not any(k in a for k in ("nome", "total", "moeda", "renova", "validade", "observacao")):
        raise ErroFerramenta("Nada a mudar: mande nome, total, moeda, renova, validade ou observacao (ou apagar true).")
    if "nome" in a:
        nome = _texto(a.get("nome"), 60)
        if not nome:
            raise ErroFerramenta("O nome não pode ficar vazio.")
        b["nome"] = nome
    b.setdefault("tipo", "contagem")
    _campos_beneficio(b, a, hoje)
    return f"Benefício mudado: {_texto_beneficio(b)}."


def texto_arquivo_lido(o_que, r):
    """O que a IA daqui leu do arquivo, em texto, para a IA do CorrerIA propor a mudança (nada foi gravado)."""
    if o_que == "beneficios":
        out = []
        for b in (r.get("beneficios") or [])[:12]:
            if b.get("tipo") == "vantagem":
                quanto = "vantagem"
            elif b.get("tipo") == "saldo":
                quanto = ("US$ " + calc.fmt_num(b.get("total") or 0, 2)) if b.get("moeda") == "USD" else _brl(b.get("total") or 0)
            else:
                quanto = calc.fmt_num(b.get("total") or 0, 0) + " (contagem)"
            renova = {"mes": ", renova todo mês", "ano": ", renova todo ano"}.get(b.get("renova"), "")
            out.append(f"- {b.get('nome')}: {quanto}{renova} [tipo {b.get('tipo')}]")
        if not out:
            return "A IA não achou benefícios no arquivo."
        return "Benefícios lidos do arquivo (nada foi cadastrado; para cadastrar, gerencia_novo_beneficio):\n" + "\n".join(out)
    lanc, invs = r.get("lancamentos") or [], r.get("investimentos") or []
    out = [f"- {x.get('descricao') or 'Sem descrição'}: {_brl(float(x.get('valor') or 0))} ({'recebimento' if x.get('tipo') == 'receita' else 'gasto'}"
           + (f", {_dm(x['data'])}" if x.get("data") else "") + (f", parcela {x['parcela_atual']}/{x['parcelas_total']}" if x.get("parcelas_total") else "") + ")"
           for x in lanc[:20]]
    out += [f"- investimento {x.get('nome') or ''}: {_brl(float(x.get('valor') or x.get('aporte') or 0))}" for x in invs[:5]]
    if len(lanc) > 20:
        out.append(f"- e mais {len(lanc) - 20}")
    if not out:
        return ("Não há gastos, recebimentos nem investimentos no arquivo. Se for um saldo, um crédito, um vale ou um benefício, leia de novo "
                "com o_que beneficios ou cadastre com gerencia_novo_beneficio pelo que a pessoa disse.")
    return "Lido do arquivo (nada foi lançado; para lançar, gerencia_lancar):\n" + "\n".join(out)


def _atualizar_milhas(d, a, hoje):
    b = _beneficio(d, a.get("beneficio"))
    if b.get("tipo") != "milhas":
        raise ErroFerramenta(f"{b.get('nome')} não é um programa de milhas.")
    saldo = calc.num(a.get("saldo"), -1)
    if saldo < 0:
        raise ErroFerramenta("saldo: as milhas de hoje, 0 ou mais.")
    antes = calc.milhas_de(b, hoje)["saldo"]
    # o saldo dito já tem os resgates de hoje: eles não descontam de novo (o milhas_de tira os de saldo_em em diante)
    hoje_ja = sum(calc.num(u.get("qtd")) for u in b.get("usos") or [] if isinstance(u, dict) and (calc.parse_data(u.get("data")) or date.min) >= hoje)
    b.update(saldo=int(round(saldo + hoje_ja)), saldo_em=hoje.isoformat())
    return f"Saldo de {b.get('nome')}{' · ' + b['pessoa'] if b.get('pessoa') else ''}: {calc.fmt_num(saldo, 0)} milhas (antes, {calc.fmt_num(antes, 0)})."


CORES_CATEGORIA = ["#FF5A4F", "#FF8A65", "#FFA23E", "#F2C14E", "#8BD45F", "#4ED3A6", "#3CCBDA", "#62B5FF", "#8F9BFF", "#B99BFF", "#FF77A9"]


def _nova_categoria(d, a, hoje):
    tipo = a.get("tipo")
    if tipo not in ("despesa", "receita"):
        raise ErroFerramenta("tipo: despesa (gasto) ou receita (recebimento).")
    nome = _texto(a.get("nome"), 40)
    if not nome:
        raise ErroFerramenta("Falta o nome da categoria.")
    cats = d.setdefault("categorias", [])
    igual = next((c for c in cats if _norm(c.get("nome")) == _norm(nome) and c.get("tipo", "despesa") == tipo), None)
    if igual:
        raise ErroFerramenta(f"Já existe a categoria {igual.get('nome')} ({igual.get('id')}).")
    usadas = [str(c.get("cor") or "").upper() for c in cats]
    cor = min(CORES_CATEGORIA, key=lambda x: (usadas.count(x.upper()), CORES_CATEGORIA.index(x)))
    c = {"id": "c-" + integracao.uid(), "nome": nome, "tipo": tipo, "cor": cor}
    cats.append(c)
    return f"Categoria criada: {nome} ({'gasto' if tipo == 'despesa' else 'recebimento'}). id: {c['id']}"


def _cor(v):
    c = next((h for n, h in calc.CORES_APP if _norm(n) == _norm(v)), None)
    if not c:
        raise ErroFerramenta("cor: " + ", ".join(n for n, _ in calc.CORES_APP) + ".")
    return c


def _editar_categoria(d, a, hoje):
    """1.96.0: o nome, a cor ou apagar uma categoria (Mais › Caixa › Categorias): apagada, os lançamentos e os fixos dela ficam sem."""
    cats = d.setdefault("categorias", [])
    v, n = str(a.get("categoria") or "").strip(), _norm(a.get("categoria"))
    tipo = a.get("tipo") if a.get("tipo") in ("despesa", "receita") else None
    achadas = [c for c in cats if c.get("id") == v] or [c for c in cats if _norm(c.get("nome")) == n and (not tipo or c.get("tipo", "despesa") == tipo)]
    if not achadas:
        raise ErroFerramenta(f"Categoria não encontrada: {v or '(vazio)'}. Veja as de agora em gerencia_cadastros.")
    if len(achadas) > 1:
        raise ErroFerramenta(f"Há duas categorias {achadas[0].get('nome')}: diga o tipo (despesa ou receita).")
    c = achadas[0]
    if a.get("apagar") is True:
        usam = 0
        for l in d.get("lancamentos", []) + d.get("recorrencias", []):
            if l.get("categoria") == c.get("id"):
                l["categoria"] = ""
                usam += 1
        cats.remove(c)
        return f"Categoria apagada: {c.get('nome')}." + (f" {usam} {'lançamento ficou' if usam == 1 else 'lançamentos ficaram'} sem categoria." if usam else "")
    mudou = []
    if a.get("nome") is not None:
        nome = _texto(a.get("nome"), 40)
        if not nome:
            raise ErroFerramenta("O nome novo está vazio.")
        if any(x is not c and _norm(x.get("nome")) == _norm(nome) and x.get("tipo", "despesa") == c.get("tipo", "despesa") for x in cats):
            raise ErroFerramenta(f"Já existe a categoria {nome}.")
        mudou.append(f"{c.get('nome')} → {nome}")
        c["nome"] = nome
    if a.get("cor") is not None:
        c["cor"] = _cor(a["cor"])
        mudou.append("cor " + next(n for n, h in calc.CORES_APP if h == c["cor"]))
    if not mudou:
        raise ErroFerramenta("Diga o que muda: nome, cor ou apagar.")
    return f"Categoria mudada ({c.get('nome')}): " + ", ".join(mudou) + "."


def _editar_banco(d, a, hoje):
    """1.96.0: o banco (nome, cor, observação) e uma conta dele (de quem é, o cartão e os dias da fatura, o limite), como Mais › Bancos."""
    b = next((x for x in d.get("bancos", []) if x.get("id") == a.get("banco")), None) or _banco_por_nome(d, a.get("banco"))
    if not b:
        raise ErroFerramenta(f"Banco não encontrado: {a.get('banco') or '(vazio)'}. Veja os de agora em gerencia_cadastros.")
    mudou = []
    if a.get("nome") is not None:
        nome = _texto(a.get("nome"), 40)
        if not nome:
            raise ErroFerramenta("O nome novo está vazio.")
        if any(x is not b and _norm(x.get("nome")) == _norm(nome) for x in d.get("bancos", [])):
            raise ErroFerramenta(f"Já existe o banco {nome}.")
        mudou.append(f"nome {nome}")
        b["nome"] = nome
    if a.get("cor") is not None:
        b["cor"] = _cor(a["cor"])
        mudou.append("cor " + next(n for n, h in calc.CORES_APP if h == b["cor"]))
    if a.get("obs") is not None:
        b["obs"] = _texto(a.get("obs"), 200)
        mudou.append("observação")
    da_conta = [k for k in ("pessoa", "cartao_de_credito", "fecha_dia", "vence_dia", "limite") if a.get(k) is not None]
    if da_conta or a.get("conta"):
        contas = [c for c in b.get("contas") or [] if isinstance(c, dict)]
        v = str(a.get("conta") or "").strip()
        c = next((x for x in contas if x.get("id") == v), None) or next((x for x in contas if v and _norm(x.get("pessoa")) == _norm(v)), None) \
            or (contas[0] if len(contas) == 1 and not v else None)
        if not c:
            raise ErroFerramenta(f"Diga a conta de {b.get('nome')}: " + "; ".join(f"{x.get('pessoa') or 'sem pessoa'} ({x.get('id')})" for x in contas) + ".")
        if not da_conta:
            raise ErroFerramenta("Diga o que muda na conta: pessoa, cartao_de_credito, fecha_dia, vence_dia ou limite.")
        if a.get("pessoa") is not None:
            pessoa = _texto(a.get("pessoa"), 40)
            if any(x is not c and _norm(x.get("pessoa")) == _norm(pessoa) for x in contas):
                raise ErroFerramenta(f"{b.get('nome')} já tem a conta {'de ' + pessoa if pessoa else 'sem pessoa'}.")
            c["pessoa"] = pessoa
            mudou.append(f"a conta é de {pessoa}" if pessoa else "a conta fica sem pessoa")
        if a.get("cartao_de_credito") is not None:
            c["cartao"] = a["cartao_de_credito"] is True
            mudou.append("com cartão de crédito" if c["cartao"] else "sem cartão de crédito")
        for k, campo, rot in (("fecha_dia", "fechamento", "fecha dia"), ("vence_dia", "vencimento", "vence dia")):
            if a.get(k) is not None:
                c[campo] = min(31, max(1, int(calc.num(a.get(k), 1) or 1)))
                mudou.append(f"{rot} {c[campo]}")
        if a.get("limite") is not None:
            c["limite"] = _valor(a.get("limite"), "limite")
            mudou.append(f"limite {_brl(c['limite'])}")
        if any(a.get(k) is not None for k in ("fecha_dia", "vence_dia", "limite")) and not c.get("cartao"):
            raise ErroFerramenta("Essa conta não tem cartão de crédito: mande cartao_de_credito true junto.")
    if not mudou:
        raise ErroFerramenta("Diga o que muda: nome, cor, obs ou, na conta, pessoa, cartao_de_credito, fecha_dia, vence_dia ou limite.")
    return f"{b.get('nome')}: " + ", ".join(mudou) + "."


def _projecao(d, a, hoje):
    """1.96.0: os seus investimentos daqui a tantos meses (calc.valor_em, a projeção da tela), com o aporte de cada mês pela taxa média."""
    meses = int(calc.num(a.get("meses"), 12) or 12)
    if not 1 <= meses <= 480:
        raise ErroFerramenta("meses: de 1 a 480.")
    aporte = _valor(a.get("aporte_mensal"), "aporte_mensal", zero=True) if a.get("aporte_mensal") is not None else 0.0
    ind, corrigir = d.get("indices", {}), calc.corrige_valores(d)
    meus = [i for i in d.get("investimentos", []) if i.get("titular") != "terceiros" and i.get("tipo") != "bens"]
    if not meus and not aporte:
        return "Nenhum investimento seu cadastrado para projetar."
    linhas, hoje_t, depois_t = [], 0.0, 0.0
    for i in meus:
        v0, v1 = calc.valor_hoje(i, ind, corrigir, hoje), calc.valor_em(i, ind, meses / 12, corrigir, hoje)
        hoje_t, depois_t = hoje_t + v0, depois_t + v1
        linhas.append((v1, f"- {i.get('nome', '')}: {_brl(v0)} → {_brl(v1)} ({calc.rotulo_taxa(i)})"))
    taxa = (sum(calc.valor_hoje(i, ind, corrigir, hoje) * calc.taxa_anual(i, ind) for i in meus) / hoje_t) if hoje_t else calc.taxa_anual({"indexador": "cdi", "taxa": 100}, ind)
    quando = f"{meses} {'mês' if meses == 1 else 'meses'}" + (f" ({meses // 12} {'ano' if meses == 12 else 'anos'})" if meses % 12 == 0 else "")
    out = [f"Hoje: {_brl(hoje_t)}. Em {quando}, sem aportes: {_brl(depois_t)} (+{_brl(depois_t - hoje_t)}), antes do IR, com a taxa de hoje de cada um."]
    if aporte:
        m = (1 + taxa) ** (1 / 12) - 1
        dos_aportes = aporte * (((1 + m) ** meses - 1) / m if m else meses)
        out.append(f"Com {_brl(aporte)} por mês: {_brl(depois_t + dos_aportes)} ({_brl(aporte * meses)} de aportes e {_brl(dos_aportes - aporte * meses)} do que eles rendem, pela taxa média de {f'{taxa * 100:.1f}'.replace('.', ',')}% ao ano).")
    out += [t for _, t in sorted(linhas, key=lambda x: -x[0])[:15]]
    return "\n".join(out)


def _novo_banco(d, a, hoje):
    nome = _texto(a.get("banco"), 40)
    if not nome:
        raise ErroFerramenta("Falta o nome do banco.")
    pessoa = _texto(a.get("pessoa"), 40)
    cartao = a.get("cartao_de_credito") is True
    dia = lambda v, p: min(31, max(1, int(calc.num(v, p) or p)))  # noqa: E731
    if cartao and (a.get("fecha_dia") is None or a.get("vence_dia") is None):
        raise ErroFerramenta("Com cartão de crédito, diga fecha_dia e vence_dia (os dias da fatura).")
    conta = {"id": "k-" + integracao.uid(), "pessoa": pessoa, "cartao": cartao, "fechamento": dia(a.get("fecha_dia"), 1), "vencimento": dia(a.get("vence_dia"), 10)}
    if a.get("cartao_de_debito") is False:
        conta["debito"] = False
    if cartao and a.get("limite") is not None:
        conta["limite"] = _valor(a.get("limite"), "limite")
    bancos = d.setdefault("bancos", [])
    b = next((x for x in bancos if _norm(x.get("nome")) == _norm(nome)), None)
    if b:
        if any(_norm(c.get("pessoa")) == _norm(pessoa) for c in b.get("contas") or []):
            raise ErroFerramenta(f"{b.get('nome')} já tem a conta {'de ' + pessoa if pessoa else 'sem pessoa'}. Para mudar o cartão, use a tela (Mais › Bancos).")
        b.setdefault("contas", []).append(conta)
        txt = f"Conta acrescentada em {b.get('nome')}"
    else:
        usadas = [str(x.get("cor") or "").upper() for x in bancos]
        cor = min(CORES_BANCO, key=lambda x: (usadas.count(x.upper()), CORES_BANCO.index(x)))
        bancos.append({"id": "b-" + integracao.uid(), "nome": nome, "cor": cor, "obs": "", "contas": [conta]})
        txt = f"Banco cadastrado: {nome}"
    return (txt + (f", de {pessoa}" if pessoa else "") + (f", com cartão de crédito (fecha dia {conta['fechamento']}, vence dia {conta['vencimento']})" if cartao else "")
            + f". id da conta: {conta['id']}")


# ---------------------------------------------------------------- chamar

# ---------------------------------------------------------------- as faturas do e-mail (1.87.0)
# As linhas como o Conferir lançamentos da tela as mostra (prepararRevisaoCaixa, iaPago e aplicarIACaixa no app.js): a conta
# pelo banco que a IA viu, o cartão, a categoria, o que parece já lançado, o pagamento da própria fatura e o fixo do remetente.
EMAIL_ESTADO = {"conferir": "para conferir", "lendo": "a IA ainda está lendo",
                "senha": "o PDF tem senha (cadastre em Mais › Configurações › Integrações › Senhas dos PDFs)", "erro": "não consegui ler"}
RE_PAG_FATURA = re.compile(r"^(pagamento|pagto|pgto)\b|debito automatico|pagamento (recebido|online|da fatura|de fatura|efetuado)")


def _banco_por_nome(d, nome):
    n = _norm(nome)
    if not n:
        return None
    bs = [b for b in d.get("bancos", []) if isinstance(b, dict) and _norm(b.get("nome"))]
    return next((b for b in bs if _norm(b.get("nome")) == n), None) or next((b for b in bs if _norm(b["nome"]) in n or n in _norm(b["nome"])), None)


def _conta_do_banco(contas, b, cartao):
    cs = [k for k, c in contas.items() if c.get("banco") == b.get("id")]
    return (cartao and next((k for k in cs if contas[k].get("cartao")), None)) or (cs[0] if cs else "")


def linhas_email(d, resultado, fixo="", hoje=None):
    """As linhas lidas de uma fatura, prontas para lançar como na tela (cada uma com o número na leitura, _k)."""
    hoje = hoje or date.today()
    contas, its = calc.mapa_contas(d), []
    for k, x in enumerate((resultado or {}).get("lancamentos") or []):
        if not isinstance(x, dict) or calc.num(x.get("valor"), 0) <= 0:
            continue
        tipo = "receita" if x.get("tipo") == "receita" else "despesa"
        its.append({"_k": k, "tipo": tipo, "descricao": _texto(x.get("descricao")) or ("Recebimento" if tipo == "receita" else "Despesa"),
                    "valor": round(calc.num(x.get("valor"), 0), 2), "data": (calc.parse_data(x.get("data")) or hoje).isoformat(),
                    "categoria": str(x.get("categoria") or ""), "cartao": x.get("cartao"), "banco": str(x.get("banco") or ""),
                    "situacao": x.get("situacao") or "", "parcela_atual": int(calc.num(x.get("parcela_atual"), 0) or 0),
                    "parcelas_total": int(calc.num(x.get("parcelas_total"), 0) or 0), "pagamento_fatura": x.get("pagamento_fatura") is True})
    maioria = sum(1 for i in its if i["cartao"]) > len(its) / 2
    nome_banco = next((i["banco"] for i in its if i["banco"]), "")
    b, lista = _banco_por_nome(d, nome_banco), list(contas)
    if b:
        conta = _conta_do_banco(contas, b, maioria)
    elif nome_banco:  # um banco que não está cadastrado: sem conta, em vez de cair noutro banco
        conta = ""
    else:
        conta = (next((k for k in lista if contas[k].get("cartao")), "") if maioria else "") or (lista[0] if lista else "")
    no_cartao_todas = maioria and bool((contas.get(conta) or {}).get("cartao"))
    cats = {c.get("id"): c for c in d.get("categorias", [])}
    for it in its:
        bi = _banco_por_nome(d, it["banco"])
        ci = _conta_do_banco(contas, bi, it["cartao"]) if bi else ""
        it["conta"] = ci or ("" if it["banco"] and not bi else conta) or ""
        tem = bool((contas.get(it["conta"]) or {}).get("cartao"))
        it["no_cartao"] = it["tipo"] == "despesa" and tem and (it["cartao"] is True if ci else no_cartao_todas and it["cartao"] is not False)
        if not it["categoria"] or it["categoria"] in ("c-outros-receb", "c-outros-gastos"):  # 1.98.0: a IA não soube: o costume da casa
            it["categoria"] = calc.categoria_aprendida(d, it["tipo"], it.get("descricao")) or it["categoria"]
        if not it["categoria"]:
            it["categoria"] = "c-outros-receb" if it["tipo"] == "receita" else "c-outros-gastos"
        if it["categoria"] not in cats:
            it["categoria"] = next((c.get("id") for c in d.get("categorias", []) if c.get("tipo", "despesa") == it["tipo"]), "")
        di = date.fromisoformat(it["data"])
        it["dup"] = any(l.get("tipo") == it["tipo"] and abs(calc.num(l.get("valor")) - it["valor"]) < 0.01
                        and abs(((calc.parse_data(l.get("data")) or hoje) - di).days) <= 2 and _norm(l.get("descricao"))[:4] == _norm(it["descricao"])[:4]
                        for l in d.get("lancamentos", []))
        it["desconsiderado"] = it["pagamento_fatura"] or (it["tipo"] == "receita" and (bool(it["cartao"]) or maioria)
                                                          and bool(RE_PAG_FATURA.search(_norm(it["descricao"]))))
        it["fixo"] = ""
    r = next((x for x in d.get("recorrencias", []) if fixo and x.get("id") == fixo), None)
    alvo = r and next((i for i in its if i["tipo"] == "despesa"), None)
    if alvo:  # o remetente é um fixo (Sempre é um fixo): a primeira despesa vai para o fixo do mês, na conta e na categoria dele
        ym = alvo["data"][:7]
        m = next((l for l in d.get("lancamentos", []) if l.get("recorrencia") == r["id"] and l.get("competencia") == ym and not l.get("pulado")), None)
        alvo.update(fixo=r["id"], fixo_nome=r.get("descricao", ""), fixo_mes=ym,
                    dup=bool(m and m.get("pago") and abs(calc.num(m.get("valor")) - alvo["valor"]) < 0.01))
        if r.get("categoria") in cats:
            alvo["categoria"] = r["categoria"]
        if r.get("conta") in contas:
            alvo["conta"], alvo["no_cartao"] = r["conta"], bool(r.get("cartao")) and bool(contas[r["conta"]].get("cartao"))
    return its


def _pago_email(d, it, data, hoje, contas, pago=None):
    if isinstance(pago, bool):
        return pago
    if not it["no_cartao"] and it["situacao"] in ("feito", "pendente"):
        return it["situacao"] == "feito"
    dc = calc.data_caixa({"data": data, "conta": it["conta"], "cartao": it["no_cartao"]}, contas, d)
    return bool(dc and dc <= hoje)


def texto_faturas_email(d, itens, regras_fixo, hoje=None):
    """A lista das faturas do e-mail que esperam a conferência. itens: as do email_publico do server.py; regras_fixo: o
    fixo de cada uma (id do e-mail -> id do fixo, ou "")."""
    hoje = hoje or date.today()
    if not itens:
        return "Nenhuma fatura do e-mail (nem foto ou PDF do WhatsApp) esperando a conferência."
    contas = calc.mapa_contas(d)
    L = [f"{len(itens)} {'fatura' if len(itens) == 1 else 'faturas'} esperando a conferência:"]
    for it in itens:
        de = it.get("de") or it.get("endereco") or ("WhatsApp" if it.get("origem") == "whatsapp" else "e-mail")
        quando = _dm(str(it.get("recebido_em") or it.get("data") or "")[:10])
        L.append(f"\n- id {it['id']}: {de}{' (pelo WhatsApp)' if it.get('origem') == 'whatsapp' else ''}"
                 + (f", «{it['assunto']}»" if it.get("assunto") else "") + (f", chegou em {quando}" if quando else "")
                 + f" · {EMAIL_ESTADO.get(it.get('estado'), it.get('estado'))}" + (f" ({it['erro']})" if it.get("estado") == "erro" and it.get("erro") else ""))
        if it.get("estado") != "conferir":
            continue
        res = it.get("resultado") or {}
        linhas = linhas_email(d, res, "" if res.get("sem_fixo") else regras_fixo.get(it["id"], ""), hoje)
        for i in linhas:
            c = contas.get(i["conta"])
            extra = [_nome_cat(d, i["categoria"]), (calc.nome_conta(c) + (" (cartão de crédito)" if i["no_cartao"] else "")) if c else "sem conta"]
            if i["parcelas_total"]:
                extra.append(f"parcela {i['parcela_atual']}/{i['parcelas_total']}")
            if i["fixo"]:
                extra.append(f"vai para o fixo {i['fixo_nome']} de {i['fixo_mes'][5:]}/{i['fixo_mes'][:4]}")
            if i["dup"]:
                extra.append("parece já lançado")
            if i["desconsiderado"]:
                extra.append("é o pagamento da própria fatura (não se lança)")
            L.append(f"  {i['_k'] + 1}. {'+' if i['tipo'] == 'receita' else '−'} {i['descricao']} · {_brl(i['valor'])} · {_dm(i['data'])} · "
                     + " · ".join(x for x in extra if x))
        invs = [x for x in res.get("investimentos") or [] if isinstance(x, dict)]
        if invs:
            L.append(f"  E {len(invs)} {'investimento' if len(invs) == 1 else 'investimentos'} (esses se conferem na tela).")
    L.append("\nPara lançar: gerencia_lancar_fatura_do_email (com os números das linhas, ou sem eles para as que valem); para tirar "
             "da conferência sem lançar: gerencia_ignorar_fatura_do_email.")
    return "\n".join(L)


def lancar_email(d, it, a, fixo="", hoje=None):
    """Lança as linhas de uma fatura do e-mail (it: a do email_publico, em conferir). Devolve (texto, as linhas que ficam
    para conferir, sem_fixo)."""
    hoje = hoje or date.today()
    res = it.get("resultado") or {}
    linhas = linhas_email(d, res, "" if res.get("sem_fixo") else fixo, hoje)
    pedidas = a.get("linhas")
    if pedidas is not None:
        if not isinstance(pedidas, list) or not all(isinstance(n, int) and not isinstance(n, bool) for n in pedidas):
            raise ErroFerramenta("linhas: uma lista com os números das linhas (1, 2, …).")
        validos = {i["_k"] + 1 for i in linhas}
        fora = [n for n in pedidas if n not in validos]
        if fora:
            raise ErroFerramenta(f"Essa fatura não tem a linha {fora[0]}. As linhas: {', '.join(str(n) for n in sorted(validos))}.")
        escolhidas = [i for i in linhas if i["_k"] + 1 in pedidas]
    else:
        escolhidas = [i for i in linhas if not i["dup"] and not i["desconsiderado"]]
    if not escolhidas:
        raise ErroFerramenta("Nenhuma linha para lançar: as que a IA leu parecem já lançadas ou são o pagamento da fatura. "
                             "Diga os números das linhas, se quiser lançar mesmo assim, ou ignore a fatura.")
    contas = calc.mapa_contas(d)
    if a.get("conta") not in (None, ""):
        conta = _conta(d, a.get("conta"))
        for i in escolhidas:
            i["conta"], i["no_cartao"] = conta, i["no_cartao"] and bool(contas[conta].get("cartao"))
    pago = a.get("pago") if isinstance(a.get("pago"), bool) else None
    feitos = []
    for i in escolhidas:
        base = {"tipo": i["tipo"], "descricao": i["descricao"], "valor": i["valor"], "categoria": i["categoria"], "conta": i["conta"],
                "cartao": i["no_cartao"], "obs": ""}
        if i["tipo"] == "despesa" and i["categoria"] == "c-investimentos":
            base.update(aporte=True, cartao=False)
        if i["fixo"]:
            r = next(x for x in d["recorrencias"] if x["id"] == i["fixo"])
            ym, pg = i["fixo_mes"], _pago_email(d, i, i["data"], hoje, contas, pago)
            if not calc.num(r.get("valor")) > 0:
                r["valor"] = i["valor"]
            if not r.get("conta") and i["conta"]:
                r.update(conta=i["conta"], cartao=base["cartao"])
            m = next((l for l in d["lancamentos"] if l.get("recorrencia") == r["id"] and l.get("competencia") == ym), None)
            if m:
                m.update(valor=i["valor"], conta=i["conta"] or m.get("conta", ""), cartao=base["cartao"], categoria=i["categoria"] or m.get("categoria", ""))
                if not m.get("pago"):
                    m.update(pago=pg, data=i["data"])
                m.pop("pulado", None)
            else:
                m = {"id": integracao.uid(), "tipo": r.get("tipo", "despesa"), "descricao": r.get("descricao", i["descricao"]), "valor": i["valor"],
                     "categoria": i["categoria"] or r.get("categoria", ""), "conta": i["conta"], "cartao": base["cartao"], "data": i["data"],
                     "pago": pg, "obs": r.get("obs", ""), "recorrencia": r["id"], "competencia": ym}
                d["lancamentos"].append(m)
            feitos.append(m)
            continue
        if i["parcelas_total"] and i["parcela_atual"]:
            g = "g-" + integracao.uid()
            d0 = date.fromisoformat(i["data"])
            for p in range(i["parcela_atual"], i["parcelas_total"] + 1):  # as próximas parcelas também (o padrão da tela)
                dt = calc._data_mes(d0.year, d0.month + (p - i["parcela_atual"]), d0.day).isoformat()
                l = dict(base, id=integracao.uid(), data=dt, parcela=f"{p}/{i['parcelas_total']}", grupo=g,
                         pago=_pago_email(d, i, dt, hoje, contas, pago) if p == i["parcela_atual"] else False)
                d["lancamentos"].append(l)
                if p == i["parcela_atual"]:
                    feitos.append(l)
        else:
            l = dict(base, id=integracao.uid(), data=i["data"], pago=_pago_email(d, i, i["data"], hoje, contas, pago))
            d["lancamentos"].append(l)
            feitos.append(l)
    lancadas = {i["_k"] for i in escolhidas}
    resto = [i["_k"] for i in linhas if i["_k"] not in lancadas and not i["dup"] and not i["desconsiderado"]]
    invs = [k for k, x in enumerate(res.get("investimentos") or []) if isinstance(x, dict)]
    txt = f"Lançado da fatura de {it.get('de') or 'e-mail'}:\n" + "\n".join("- " + _descrever(d, l, contas) for l in feitos)
    txt += (f"\nFicam para conferir {len(resto)} {'linha' if len(resto) == 1 else 'linhas'}." if resto
            else "\nA fatura saiu da conferência." if not invs else "")
    if invs:
        txt += f"\nOs {len(invs)} investimentos lidos continuam para conferir na tela."
    return txt, {"lancamentos": resto, "investimentos": invs}, any(i["fixo"] for i in escolhidas)


def texto_beneficios(d, hoje):
    """A ferramenta beneficios: o mesmo texto do resumo."""
    L = chat.beneficios_linhas(d, hoje)
    return "\n".join(L).strip() if L else "Nenhum benefício em Mais › Benefícios."


def texto_oportunidades(avaliadas, promos, so_passam=False, ia=True, avisos=""):
    """A ferramenta oportunidades (o server.py junta o que foi lido): os investimentos que passam do que a casa quer
    primeiro, as três melhores de cada família que não passam (sem so_passam) e as assinaturas em promoção."""
    import oportunidades as op
    import promocoes
    passam = [x for x in avaliadas if x.get("passa")]
    outras, vistos = [], {}
    if not so_passam:
        for x in avaliadas:
            if not x.get("passa") and vistos.get(x["eq"]["grupo"], 0) < 3:
                vistos[x["eq"]["grupo"]] = vistos.get(x["eq"]["grupo"], 0) + 1
                outras.append(x)

    def linha(x):
        t = f"- {op.linha_aviso(x)} · {x.get('fonte') or ''}"
        if x.get("vencimento"):
            t += f" · vence em {_dm(x['vencimento'])}"
        if x.get("minimo"):
            t += f" · mínimo {_brl(x['minimo'])}"
        return t

    L = ["Investimentos que passam do que a casa quer:" if passam else "Nenhum investimento passa do que a casa quer agora."]
    L += [linha(x) for x in passam]
    if outras:
        L.append("Outros, os melhores de cada tipo:")
        L += [linha(x) for x in outras]
    if not ia:
        L.append("As ofertas dos bancos e as assinaturas em promoção pedem o Usar IA ligado no GerencIA.")
    elif promos:
        L.append("Assinaturas em promoção:")
        L += [f"- {promocoes.linha(x['nome'], x)}" + (f", até {_dm(x['ate'])}" if x.get("ate") else "") for x in promos]
    else:
        L.append("Nenhuma assinatura em promoção.")
    if avisos:
        L.append(avisos)
    return "\n".join(L)


def chamar(nome, argumentos, d, hoje=None, bens=None, extras="", moedas=None):
    """Roda a ferramenta nos dados d (as de gravar mudam d). Devolve (texto para a IA, mudou). bens (1.78.0): os bens
    da casa do InventarIA, como a tela (o bens_estado do server.py), para o patrimônio ser o mesmo da tela."""
    hoje = hoje or date.today()
    f = POR_NOME.get(str(nome or ""))
    if not f:
        raise LookupError(f"Ferramenta desconhecida: {nome}.")
    a = argumentos if isinstance(argumentos, dict) else {}
    for k in ("lancamentos", "recorrencias", "investimentos", "bancos", "categorias"):
        d.setdefault(k, [])
    if nome == "lancar" and a.get("moeda") not in (None, "", "BRL"):
        a = _em_reais(a, moedas)
    if nome == "resumo":
        return chat.resumo(d, hoje, bens, extras), False
    if nome == "lancamentos":
        return _lancamentos(d, a, hoje), False
    if nome == "contas_a_pagar":
        return _contas_a_pagar(d, a, hoje), False
    if nome == "comparar_meses":
        return _comparar_meses(d, a, hoje), False
    if nome == "previsao_mes":
        return _previsao_mes(d, hoje), False
    if nome == "fora_do_padrao":
        return _fora_do_padrao(d, hoje), False
    if nome == "projecao":
        return _projecao(d, a, hoje), False
    if nome == "investimentos":
        return _investimentos(d, hoje, bens), False
    if nome == "cadastros":
        return _cadastros(d), False
    if nome == "beneficios":
        return texto_beneficios(d, hoje), False
    if nome.endswith("_email") or nome in ("oportunidades", "dicas", "cambio", "conta_de_luz", "ler_arquivo"):  # ficam com o server.py (as faturas do e-mail, as páginas lidas)
        raise LookupError(f"{nome}: só pelo servidor.")
    faz = {"lancar": _lancar, "editar_lancamento": _editar, "alterar_lancamentos": _alterar_lote, "apagar_lancamento": _apagar, "marcar_pago": _marcar_pago,
           "atualizar_investimento": _atualizar_inv, "novo_investimento": _novo_inv, "novo_fixo": _novo_fixo,
           "ajustar_saldo": _ajustar_saldo, "editar_fixo": _editar_fixo, "encerrar_fixo": _encerrar_fixo, "usar_beneficio": _usar_beneficio,
           "novo_beneficio": _novo_beneficio, "editar_beneficio": _editar_beneficio,
           "atualizar_milhas": _atualizar_milhas, "nova_categoria": _nova_categoria, "novo_banco": _novo_banco,
           "editar_categoria": _editar_categoria, "editar_banco": _editar_banco}[nome]
    return faz(d, a, hoje), True
