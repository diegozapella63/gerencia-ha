"""Oportunidades de investimento (oportunidades.py, a conta no calc.py e as partes do server.py): a tabela do Tesouro
Direto e os dados abertos de reserva, as páginas de ofertas lidas pela IA (simulada) com o trecho conferido, o equivalente
em CDB, o alvo de cada família, a comparação com os seus investimentos e o aviso no celular no horário, como o aviso de
prazos do ResolvIA. O Tesouro, as páginas e o Home Assistant são de mentira; pessoas, bancos e taxas inventados."""
import json
import os
import unittest
from datetime import date, datetime, timedelta
from unittest import mock

from tests.base import ServidorFalso, Servidor, importar_servidor, INDICES
from tests.test_avisos import Trocar, ha_falso, ws_falso
S = importar_servidor()
import avisos as A  # noqa: E402  (o importar_servidor põe gerencia/app no caminho)
import calc  # noqa: E402
import oportunidades as O  # noqa: E402

HOJE = date(2026, 11, 2)
CSV = ("Título;Rendimento anual do título;Investimento mínimo;Preço unitário de investimento;Vencimento do Título\r\n"
       "Tesouro Selic 2031;SELIC + 0,0950%;R$ 180,40;R$ 18.040,10;01/03/2031\r\n"
       "Tesouro Prefixado 2032;13,71%;R$ 35,20;R$ 501,40;01/01/2032\r\n"
       "\"Tesouro IPCA+ 2032\";\"IPCA + 7,04%\";\"R$ 38,90\";\"R$ 2.594,33\";\"15/08/2032\"\r\n"
       "Tesouro IPCA+ 2040;IPCA + 6,88%;R$ 34,10;R$ 1.704,85;15/08/2040\r\n"
       "Tesouro Renda+ Aposentadoria Extra 2030;IPCA + 6,95%;R$ 38,00;R$ 1.268,40;15/12/2049\r\n"
       "Tesouro Reserva 2036;SELIC;R$ 1,00;R$ 10,812345;01/01/2036\r\n"
       "Linha estragada;sem taxa;;;\r\n").encode("cp1252")
DADOS = ("Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha\n"
         "Tesouro IPCA+;15/08/2032;05/11/2026;6,90;7,02;2500,00\n"
         "Tesouro IPCA+;15/08/2032;06/11/2026;7,01;7,13;2510,00\n"
         "Tesouro Selic;01/03/2031;06/11/2026;0,0950;0,11;18000,00\n"
         "Tesouro Prefixado;01/01/2026;06/11/2026;0,00;13,1;1000,00\n"
         "Tesouro IGPM+ com Juros Semestrais;01/01/2031;06/11/2026;6,1;6,2;4000,00\n"
         "Tesouro Prefixado;01/01/2032;04/11/2026;13,9;14,0;500,00\n").encode("cp1252")
PAGINA = """<html><body><h1>Investimentos do Banco Sol</h1>
<ul><li>CDB Banco Sol 130% do CDI, liquidez diária</li><li>LCA Banco Sol 95% do CDI vence em 10/11/2027</li>
<li>CDB Banco Sol IPCA + 7,5% vence em 15/05/2030</li><li>Fundo Multimercado Sol: 120% do CDI no ano</li>
<li>Caixinha Banco Sol 115% do CDI (clientes Sol Mais)</li></ul></body></html>"""


def titulos():
    return O.ler_investir(CSV)


def dados(**aj):
    d = S.vazio()
    d["indices"].update(INDICES)
    d["ajustes"].update(aj)
    return d


# ---------------------------------------------------------------------------------------------------------------
class TestTesouro(unittest.TestCase):
    def test_tabela_investir(self):
        t = titulos()
        self.assertEqual([(x["nome"], x["familia"], x["indexador"], x["taxa"], x["vencimento"]) for x in t], [
            ("Tesouro Selic 2031", "selic", "selic_mais", 0.095, "2031-03-01"),
            ("Tesouro Prefixado 2032", "pre", "pre", 13.71, "2032-01-01"),
            ("Tesouro IPCA+ 2032", "ipca", "ipca_mais", 7.04, "2032-08-15"),
            ("Tesouro IPCA+ 2040", "ipca", "ipca_mais", 6.88, "2040-08-15"),
            ("Tesouro Renda+ Aposentadoria Extra 2030", "renda", "ipca_mais", 6.95, "2049-12-15"),
            ("Tesouro Reserva 2036", "selic", "selic_mais", 0.0, "2036-01-01")], "aspas e a linha estragada")
        self.assertEqual((t[0]["id"], t[2]["id"], t[0]["minimo"], t[0]["preco"]), ("td:tesouro-selic-2031", "td:tesouro-ipca-mais-2032", 180.4, 18040.1))
        self.assertEqual(O.ler_investir(CSV.decode("cp1252").encode("utf-8"))[2]["nome"], "Tesouro IPCA+ 2032", "também em UTF-8")

    def test_rendimento(self):
        self.assertEqual(O.rendimento("SELIC + 0,1064%"), ("selic_mais", 0.1064))
        self.assertEqual(O.rendimento(" selic "), ("selic_mais", 0.0))
        self.assertEqual(O.rendimento("IPCA + 7,82%"), ("ipca_mais", 7.82))
        self.assertEqual(O.rendimento("15,10%"), ("pre", 15.1))
        self.assertIsNone(O.rendimento("IGP-M + 6%"))
        self.assertIsNone(O.rendimento(""))

    def test_dados_abertos_ficam_com_o_dia_mais_novo(self):
        t, dia = O.ler_transparente(DADOS.splitlines(keepends=True))
        self.assertEqual(dia, "2026-11-06")
        self.assertEqual([(x["nome"], x["taxa"]) for x in t], [("Tesouro IPCA+ 2032", 7.01), ("Tesouro Selic 2031", 0.095)],
                         "sem o que não está à venda (taxa 0), o IGP-M e os dias velhos")
        self.assertEqual(t[0]["id"], titulos()[2]["id"], "o mesmo título das duas fontes tem o mesmo id")

    def test_so_selic_prefixado_e_ipca(self):
        self.assertEqual([x["nome"] for x in O.do_tesouro(titulos())],
                         ["Tesouro Selic 2031", "Tesouro Reserva 2036", "Tesouro Prefixado 2032", "Tesouro IPCA+ 2032", "Tesouro IPCA+ 2040"])
        self.assertEqual(O.do_tesouro(None), [])


class TestOfertas(unittest.TestCase):
    URL = "https://www.bancosol.exemplo/investimentos"

    def texto(self):
        return S.assinaturas.html_texto(PAGINA)

    def test_a_ia_simulada_e_a_limpeza(self):
        texto = self.texto()
        ofs, recusadas = O.limpar_ofertas(O.simuladas(texto), texto, self.URL, HOJE)
        self.assertEqual(recusadas, 0)
        self.assertEqual([(o["nome"], o["produto"], o["indexador"], o["taxa"], o["isento"], o["vencimento"], o["liquidez"], o["familia"]) for o in ofs], [
            ("CDB Banco Sol", "cdb", "cdi_pct", 130.0, False, "", "diaria", "pos"),
            ("LCA Banco Sol", "lca", "cdi_pct", 95.0, True, "2027-11-10", "", "pos"),
            ("CDB Banco Sol", "cdb", "ipca_mais", 7.5, False, "2030-05-15", "", "ipca"),
            ("Caixinha (Banco Sol)", "conta", "cdi_pct", 115.0, False, "", "", "pos")], "o fundo fica de fora")
        self.assertEqual(ofs[3]["condicao"], "clientes Sol Mais", "a condição da taxa vai junto")
        self.assertEqual({o["fonte"] for o in ofs}, {"bancosol.exemplo"})
        self.assertEqual(len({o["id"] for o in ofs}), 4)

    def test_nome_e_condicao_da_ia(self):
        texto = "Caixinha Turbo do Banco Lua: até 120% do CDI para clientes Lua Prime. Caixinhas: 100% do CDI."
        ofs, _ = O.limpar_ofertas({"ofertas": [
            {"emissor": "Banco Lua", "nome": "Caixinha Turbo", "produto": "conta", "indexador": "cdi_pct", "taxa": 120,
             "condicao": "clientes Lua Prime.", "trecho": "até 120% do CDI para clientes Lua Prime"},
            {"emissor": "Banco Lua", "nome": "Caixinha do Banco Lua", "produto": "conta", "indexador": "cdi_pct", "taxa": 100, "trecho": "Caixinhas: 100% do CDI"}]},
            texto, self.URL, HOJE)
        self.assertEqual([(o["nome"], o["condicao"]) for o in ofs], [("Caixinha Turbo (Banco Lua)", "clientes Lua Prime"), ("Caixinha do Banco Lua", "")],
                         "o banco junto do nome (quando ainda não está nele)")
        self.assertEqual(O.linha_aviso(dict(ofs[0], eq={"grupo": "pos", "valor": 120.0}, meus=None)),
                         "Caixinha Turbo (Banco Lua): 120% do CDI (clientes Lua Prime)")

    def test_paginas_prontas(self):
        self.assertTrue(all(O.limpar_url(x["url"]) == x["url"] and x["nome"] and x["nomes"] for x in O.PAGINAS_BANCOS))
        self.assertEqual(len({x["url"] for x in O.PAGINAS_BANCOS}), len(O.PAGINAS_BANCOS))
        casos = {"Nubank": "nubank.com.br", "Nu": "nubank.com.br", "NuBank Ultravioleta": "nubank.com.br", "Banco Inter": "inter.co", "inter": "inter.co",
                 "Mercado Pago": "mercadopago.com.br", "PagSeguro": "pagbank.com.br", "Pag Bank": "pagbank.com.br",
                 "Interamericano": "", "Banco Coral": "", "Nuvem": "", "": ""}
        for nome, dom in casos.items():
            with self.subTest(nome=nome):
                self.assertEqual(O.dominio(O.pagina_pronta(nome)), dom)

    def test_paginas_dos_bancos(self):
        d = {"bancos": [{"id": "b1", "nome": "Nubank"}, {"id": "b2", "nome": "Banco Coral", "ofertas": "https://bancocoral.exemplo/cdb"},
                        {"id": "b3", "nome": "Banco Lua"}, {"id": "b4", "nome": "Nu Pagamentos"}, {"id": "b5", "nome": "Inter", "ofertas": "https://inter.co/outra"},
                        {"id": "b6", "nome": " "}, "lixo"]}
        pags, sem = O.paginas_dos_bancos(d)
        self.assertEqual(pags, [{"banco": "Nubank", "url": "https://nubank.com.br/nu/caixinhas"}, {"banco": "Banco Coral", "url": "https://bancocoral.exemplo/cdb"},
                                {"banco": "Inter", "url": "https://inter.co/outra"}], "a página do banco vale sobre a pronta; a mesma página uma vez só")
        self.assertEqual(sem, ["Banco Lua"])
        muitos = {"bancos": [{"id": f"b{k}", "nome": f"Banco {k}", "ofertas": f"https://b{k}.exemplo"} for k in range(12)]}
        self.assertEqual(len(O.paginas_dos_bancos(muitos)[0]), O.MAX_PAGINAS)

    def test_as_paginas_postas_a_mao_vao_para_o_banco(self):
        d = {"bancos": [{"id": "b1", "nome": "Banco Coral"}, {"id": "b2", "nome": "Nubank"}, {"id": "b3", "nome": "Lua", "ofertas": "https://lua.exemplo/a"}]}
        O.migrar_paginas(d, ["https://www.bancocoral.exemplo/cdb", "https://nubank.com.br/nu/caixinhas", "https://lua.exemplo/b",
                             "https://www.mercadopago.com.br/cofrinhos", "javascript:alert(1)"])
        self.assertEqual([b.get("ofertas") for b in d["bancos"]], ["https://www.bancocoral.exemplo/cdb", None, "https://lua.exemplo/a"],
                         "a pronta do Nubank já vale; o banco com página fica com a dele; a do Mercado Pago, sem o banco, sai")

    def test_so_o_que_a_pagina_confirma(self):
        texto = self.texto()
        boa = {"emissor": "Banco Sol", "produto": "cdb", "indexador": "cdi_pct", "taxa": 130, "trecho": "CDB Banco Sol 130% do CDI"}
        ofs, rec = O.limpar_ofertas({"ofertas": [
            boa, dict(boa),  # repetida
            dict(boa, taxa=140),  # o número não está no trecho
            dict(boa, trecho="CDB Banco Sol 140% do CDI", taxa=140),  # o trecho não está na página
            dict(boa, produto="debenture"), dict(boa, indexador="igpm"), dict(boa, taxa=900),
            dict(boa, taxa="130", vencimento="2020-01-01"), "lixo"]}, texto, self.URL, HOJE)
        self.assertEqual([(o["taxa"], o["vencimento"]) for o in ofs], [(130.0, "")], "o vencimento que já passou some")
        self.assertEqual(rec, 5)
        self.assertEqual(O.limpar_ofertas([], texto, self.URL), ([], 0))
        self.assertEqual(O.limpar_ofertas({"ofertas": "x"}, texto, self.URL), ([], 0))

    def test_trechos_e_enderecos(self):
        self.assertIn("130% do CDI", O.trechos_taxa(self.texto()))
        self.assertEqual(O.trechos_taxa("Bem-vindo ao banco. Abra sua conta."), "")
        self.assertEqual(O.limpar_url(" https://banco.exemplo/x "), "https://banco.exemplo/x")
        self.assertEqual(O.limpar_url("ftp://banco.exemplo"), "")
        self.assertEqual(O.limpar_url("https://" + "a" * 500), "")
        self.assertEqual(O.dominio("https://www.banco.exemplo/a"), "banco.exemplo")
        self.assertIn(self.URL, O.prompt_ofertas(self.URL, "CDB 120% do CDI"))


# ---------------------------------------------------------------------------------------------------------------
class TestConta(unittest.TestCase):
    """equivalente, passa_alvo e comparar_meus (calc.py; os mesmos no app.js, conferidos em test_tela.py)."""

    def test_equivalente_em_cdb(self):
        e = lambda **x: calc.equivalente(x, INDICES, HOJE)  # noqa: E731
        self.assertEqual(e(indexador="cdi_pct", taxa=110), {"grupo": "pos", "valor": 110.0})
        self.assertEqual(e(indexador="selic_mais", taxa=0.1), {"grupo": "pos", "valor": round(((1.1375 * 1.001) - 1) / 0.1365 * 100, 2)})
        self.assertEqual(e(indexador="pre", taxa=13.71), {"grupo": "pre", "valor": 13.71})
        self.assertEqual(e(indexador="ipca_mais", taxa=7.04), {"grupo": "ipca", "valor": 7.04})
        self.assertIsNone(e(indexador="estimado", taxa=10))

    def test_isento_pelo_ir_do_prazo(self):
        e = lambda venc: calc.equivalente({"indexador": "cdi_pct", "taxa": 90, "isento": True, "vencimento": venc}, INDICES, HOJE)["valor"]  # noqa: E731
        self.assertEqual(e(""), round(90 / 0.85, 2), "sem vencimento, 15%")
        self.assertEqual(e("2026-12-01"), round(90 / 0.775, 2), "até 180 dias, 22,5%")
        self.assertEqual(e("2027-07-01"), round(90 / 0.8, 2), "até 360 dias, 20%")
        self.assertEqual(e("2028-01-10"), round(90 / 0.825, 2), "até 720 dias, 17,5%")
        self.assertEqual(e("2029-01-10"), round(90 / 0.85, 2), "mais de 720 dias, 15%")
        ipca = calc.equivalente({"indexador": "ipca_mais", "taxa": 6, "isento": True}, INDICES, HOJE)["valor"]
        self.assertEqual(ipca, round((((1.045 * 1.06 - 1) / 0.85 + 1) / 1.045 - 1) * 100, 2), "o IPCA + que um CDB precisaria ter")

    def test_sem_alvo_melhor_que_os_seus(self):
        invs = [{"nome": "CDB Lua", "tipo": "cdb", "indexador": "cdi_pct", "taxa": 104, "valor": 1000},
                {"nome": "Da Carla", "tipo": "cdb", "indexador": "cdi_pct", "taxa": 150, "valor": 900, "titular": "terceiros"}]
        p = lambda taxa, aj=None: calc.passa_alvo({"indexador": "cdi_pct", "taxa": taxa}, aj or {}, INDICES, HOJE, invs)  # noqa: E731
        self.assertEqual((p(105), p(104), p(90)), ("meus", "", ""), "só o que rende mais que o seu melhor (o de terceiros não conta)")
        self.assertEqual(p(105, {"op_cdi": 110}), "", "com alvo, vale o alvo")
        self.assertEqual(p(112, {"op_cdi": 110}), "alvo")
        self.assertEqual(calc.passa_alvo({"indexador": "pre", "taxa": 20}, {}, INDICES, HOJE, invs), "", "sem prefixado seu")
        self.assertEqual(calc.passa_alvo({"indexador": "estimado"}, {}, INDICES, HOJE, invs), "")

    def test_quanto_rende_em_um_ano(self):
        self.assertEqual(calc.rende_um_ano("pos", 118, 10000, INDICES), round(10000 * 1.18 * 0.1365 * 0.825, 2))
        self.assertEqual(calc.rende_um_ano("pre", 13.71, 10000, INDICES), round(10000 * 0.1371 * 0.825, 2))
        self.assertEqual(calc.rende_um_ano("ipca", 7, 10000, INDICES), round(10000 * (1.045 * 1.07 - 1) * 0.825, 2))

    def test_alvo(self):
        cdb = {"indexador": "cdi_pct", "taxa": 120}
        self.assertTrue(calc.passa_alvo(cdb, {"op_cdi": 120}, INDICES, HOJE), "igual ao alvo passa")
        self.assertFalse(calc.passa_alvo(cdb, {"op_cdi": 120.5}, INDICES, HOJE))
        self.assertFalse(calc.passa_alvo(cdb, {"op_cdi": None, "op_pre": 10}, INDICES, HOJE), "sem alvo da família")
        self.assertFalse(calc.passa_alvo(cdb, {"op_cdi": True}, INDICES, HOJE))
        self.assertTrue(calc.passa_alvo({"indexador": "cdi_pct", "taxa": 100, "isento": True}, {"op_cdi": 117}, INDICES, HOJE), "LCI de 100% = CDB de 117,6%")

    def test_comparar_com_os_seus(self):
        invs = [{"nome": "CDB Lua", "tipo": "cdb", "indexador": "cdi_pct", "taxa": 104, "valor": 1000},
                {"nome": "LCI Lua", "tipo": "lci", "indexador": "cdi_pct", "taxa": 92, "valor": 500},
                {"nome": "Poupança", "tipo": "poupanca", "indexador": "poupanca", "valor": 300},
                {"nome": "Da Carla", "tipo": "cdb", "indexador": "cdi_pct", "taxa": 150, "valor": 900, "titular": "terceiros"},
                {"nome": "Zerado", "tipo": "cdb", "indexador": "cdi_pct", "taxa": 150, "valor": 0},
                {"nome": "IPCA Sol", "tipo": "tesouro", "indexador": "ipca_mais", "taxa": 6.2, "valor": 800}]
        m = calc.comparar_meus({"indexador": "cdi_pct", "taxa": 106}, invs, INDICES, HOJE)
        self.assertEqual((m["n"], m["abaixo"], m["melhor"]["nome"]), (3, 2, "LCI Lua"), "a LCI de 92% vale um CDB de 108%; a de terceiros e a zerada ficam fora")
        self.assertEqual(calc.comparar_meus({"indexador": "pre", "taxa": 13}, invs, INDICES, HOJE), None, "nenhum prefixado")
        self.assertEqual(calc.comparar_meus({"indexador": "ipca_mais", "taxa": 7}, invs, INDICES, HOJE), {"n": 1, "abaixo": 1, "melhor": {"nome": "IPCA Sol", "valor": 6.2}})
        self.assertIsNone(calc.comparar_meus({"indexador": "parado"}, invs, INDICES, HOJE))


class TestAvisarQuais(unittest.TestCase):
    def avaliadas(self, **aj):
        d = dados(**aj)
        d["investimentos"] = [{"nome": "IPCA Sol", "tipo": "tesouro", "indexador": "ipca_mais", "taxa": 6.2, "valor": 800}]
        return O.avaliar(O.do_tesouro(titulos()), d, HOJE)

    def test_ordem_e_o_que_passa(self):
        av = self.avaliadas(op_ipca=7)
        self.assertEqual([(x["nome"], x["passa"]) for x in av], [
            ("Tesouro Selic 2031", ""), ("Tesouro Reserva 2036", ""), ("Tesouro Prefixado 2032", ""),
            ("Tesouro IPCA+ 2032", "alvo"), ("Tesouro IPCA+ 2040", "")])

    def test_sem_alvo_vale_o_que_rende_mais_que_os_seus(self):
        av = {x["nome"]: x["passa"] for x in self.avaliadas()}
        self.assertEqual((av["Tesouro IPCA+ 2032"], av["Tesouro IPCA+ 2040"]), ("meus", "meus"), "acima do seu IPCA + 6,20%")
        self.assertEqual(av["Tesouro Prefixado 2032"], "", "sem prefixado seu: nada para comparar")
        self.assertEqual(self.avaliadas(op_ipca=7.5)[3]["passa"], "", "o alvo escolhido vale sobre os seus")

    def test_cada_uma_uma_vez_e_de_novo_se_subir(self):
        av = self.avaliadas(op_ipca=7)
        novas, reg = O.para_avisar(av, {})
        self.assertEqual(([x["nome"] for x in novas], reg), (["Tesouro IPCA+ 2032"], {"td:tesouro-ipca-mais-2032": 7.04}))
        self.assertEqual(O.para_avisar(av, reg), ([], reg), "já avisada")
        subiu = [dict(x, eq={"grupo": "ipca", "valor": 7.14}) if x["passa"] else x for x in av]
        novas, reg2 = O.para_avisar(subiu, reg)
        self.assertEqual((len(novas), reg2), (1, {"td:tesouro-ipca-mais-2032": 7.14}), "subiu 0,10")
        quase = [dict(x, eq={"grupo": "ipca", "valor": 7.13}) if x["passa"] else x for x in av]
        self.assertEqual(O.para_avisar(quase, reg)[0], [])
        self.assertEqual(O.para_avisar(self.avaliadas(op_ipca=8), reg), ([], {}), "deixou de passar: esquecida")

    def test_textos(self):
        av = {x["nome"]: x for x in self.avaliadas(op_ipca=7)}
        self.assertEqual(O.linha_aviso(av["Tesouro IPCA+ 2032"]), "Tesouro IPCA+ 2032: IPCA + 7,04% (o seu melhor: IPCA + 6,20%)")
        self.assertEqual(O.linha_aviso(av["Tesouro Selic 2031"]), "Tesouro Selic 2031: Selic + 0,10%")
        lca = {"nome": "LCA Banco Sol", "indexador": "cdi_pct", "taxa": 95, "isento": True, "eq": {"grupo": "pos", "valor": 111.76}, "meus": None}
        self.assertEqual(O.linha_aviso(lca), "LCA Banco Sol: 95% do CDI, como CDB de 111,8% do CDI")
        self.assertEqual(O.taxa_txt({"indexador": "selic_mais", "taxa": 0}), "Selic")
        self.assertEqual(O.taxa_txt({"indexador": "cdi_mais", "taxa": 1.5}), "CDI + 1,50%")
        self.assertEqual(O.taxa_txt({"indexador": "pre", "taxa": 13.7}), "13,70% ao ano")
        self.assertEqual(O.taxa_txt({"indexador": "cdi_pct", "taxa": 112.5}), "112,5% do CDI")
        self.assertEqual(O.taxa_txt({"indexador": "outro"}), "")
        self.assertEqual(O.valor_txt("pre", 13.2), "13,20% ao ano")
        um = A.texto_oportunidades(["Tesouro IPCA+ 2032: IPCA + 7,04%"])
        self.assertEqual(um, {"title": "📈 Oportunidade de investimento", "message": "• Tesouro IPCA+ 2032: IPCA + 7,04%"})
        varias = A.texto_oportunidades([f"T{k}" for k in range(7)])
        self.assertEqual((varias["title"], varias["message"].splitlines()[-1]), ("📈 Oportunidades de investimento: 7", "e mais 2"))


# ---------------------------------------------------------------------------------------------------------------
class TestAjustes(unittest.TestCase):
    def test_padrao_e_limpeza(self):
        aj = S.vazio()["ajustes"]
        self.assertEqual({k: aj[k] for k in aj if k.startswith("op_")}, {"op_cdi": None, "op_pre": None, "op_ipca": None,
                                                                       "op_aviso": False, "op_para": [], "op_hora": "10:00", "op_dias": 1, "op_simular": 10000})
        d = S.vazio()
        d["ajustes"].update(op_cdi=120.456, op_pre="15", op_ipca=31, op_aviso="sim", op_hora="7:00", op_para=["person.ana", "x", "person.ana"], op_dias=45,
                            op_paginas=["https://bancocoral.exemplo/a", "https://b0.exemplo"])
        d["bancos"] = [{"id": "b1", "nome": "Banco Coral"}, {"id": "b2", "nome": "Banco Lua", "ofertas": "javascript:alert(1)"}, {"id": "b3", "nome": "Sol", "ofertas": " "}]
        n = S.normalizar(d)
        aj = n["ajustes"]
        self.assertEqual((aj["op_cdi"], aj["op_pre"], aj["op_ipca"], aj["op_aviso"], aj["op_hora"], aj["op_para"]),
                         (120.46, None, None, False, "10:00", ["person.ana"]))
        self.assertNotIn("op_paginas", aj, "as páginas postas à mão saem (antes da 1.46.0)")
        self.assertEqual(n["bancos"], [{"id": "b1", "nome": "Banco Coral", "ofertas": "https://bancocoral.exemplo/a"}, {"id": "b2", "nome": "Banco Lua"}, {"id": "b3", "nome": "Sol"}],
                         "a do banco vai para ele; um endereço que não é http(s) sai")
        self.assertEqual(aj["op_dias"], 1, "de 1 a 30")
        self.assertEqual(aj["op_simular"], 10000)
        d["ajustes"]["op_simular"] = 50
        self.assertEqual(S.normalizar(d)["ajustes"]["op_simular"], 10000, "a partir de R$ 100")
        d["ajustes"]["op_simular"] = 25000.5
        self.assertEqual(S.normalizar(d)["ajustes"]["op_simular"], 25000.5)
        d["ajustes"]["op_dias"] = 7
        self.assertEqual(S.normalizar(d)["ajustes"]["op_dias"], 7)


class TestBeneficiosNoServidor(unittest.TestCase):
    def test_a_lista_fica_guardada(self):
        d = S.vazio()
        self.assertEqual(d["beneficios"], [])
        d["beneficios"] = [{"id": "bn-1", "nome": "Sala VIP", "tipo": "contagem", "total": 6}, "lixo"]
        self.assertEqual(S.normalizar(d)["beneficios"], [{"id": "bn-1", "nome": "Sala VIP", "tipo": "contagem", "total": 6}])
        self.assertIn("beneficios", S.CAMPOS_USUARIO, "o PUT da tela grava os benefícios")

    def test_periodo(self):
        b = {"tipo": "contagem", "total": 6, "renova": "ano", "desde": "2026-03-15", "usos": [{"data": "2026-04-10", "qtd": 1}, {"data": "2026-01-10", "qtd": 1}]}
        self.assertEqual(calc.ciclo_beneficio(b, HOJE), {"inicio": "2026-03-15", "fim": "2027-03-15", "usado": 1.0, "restante": 5.0, "ate": "2027-03-14", "vencido": False})
        mes = calc.ciclo_beneficio(dict(b, renova="mes", desde="2026-01-31"), date(2026, 3, 1))
        self.assertEqual((mes["inicio"], mes["fim"]), ("2026-02-28", "2026-03-31"), "31/01 + 1 mês = 28/02")
        saldo = calc.ciclo_beneficio({"tipo": "saldo", "total": 100, "renova": "nunca", "desde": "2026-10-01", "validade": "2026-12-31",
                                      "usos": [{"data": "2026-10-05", "qtd": 30.5}]}, HOJE)
        self.assertEqual((saldo["restante"], saldo["ate"], saldo["fim"]), (69.5, "2026-12-31", None))
        self.assertTrue(calc.ciclo_beneficio({"tipo": "vantagem", "validade": "2026-10-01"}, HOJE)["vencido"])
        self.assertIsNone(calc.ciclo_beneficio({"tipo": "vantagem"}, HOJE)["restante"])


class ComServidor(unittest.TestCase):
    def setUp(self):
        for p in (S.OPORT_ARQ, S.ARQ):
            if os.path.exists(p):
                os.remove(p)
        self.enviados = []
        self.falso = ServidorFalso({"/tesouro.csv": (200, CSV), "/dados.csv": (200, DADOS), "/pagina": (200, PAGINA), "/vazia": (200, "<p>Abra sua conta</p>")})
        self.addCleanup(self.falso.fechar)
        Trocar(self, AVISOS=A.Avisos(ha_falso(self.enviados), ws_falso, lambda *a: None), IA_MOCK=True,
               TESOURO_URL=self.falso.url + "/tesouro.csv", TESOURO_DADOS_URL=self.falso.url + "/dados.csv")
        S._oport_conferindo.clear()

    def salvar(self, bancos=None, **aj):
        with S.TRAVA:
            d = S.ler()
            if bancos is not None:
                d["bancos"] = bancos
            d["indices"].update(INDICES)
            d["ajustes"].update(aj)
            S.salvar(d, versao=False)
        return S.ler()

    def pedidos(self, caminho):
        return [p for p in self.falso.pedidos if p[1].split("?")[0] == caminho]


class TestTesouroNoServidor(ComServidor):
    def test_tabela_do_site(self):
        c = S.atualizar_tesouro({})
        t = c["tesouro"]
        self.assertEqual((t["fonte"], t["erro"], t["dia"], len(t["titulos"])), ("investir", None, date.today().isoformat(), 6))
        self.assertEqual(self.pedidos("/dados.csv"), [], "a reserva não é usada")

    def test_sem_a_tabela_os_dados_abertos_duas_vezes_por_dia(self):
        self.falso.rotas["/tesouro.csv"] = (403, "bloqueado")
        t = S.atualizar_tesouro({})["tesouro"]
        self.assertEqual((t["fonte"], t["dia"], [x["nome"] for x in t["titulos"]]), ("dados", "2026-11-06", ["Tesouro IPCA+ 2032", "Tesouro Selic 2031"]))
        self.falso.rotas["/dados.csv"] = (500, "fora")
        t2 = S.atualizar_tesouro({"tesouro": t})["tesouro"]
        self.assertEqual(len(self.pedidos("/dados.csv")), 1, "o arquivo grande espera 12 horas")
        self.assertEqual((t2["erro"], len(t2["titulos"])), ("Não consegui ler as taxas do Tesouro Direto.", 2), "ficam as últimas taxas")

    def test_tabela_sem_titulos_conta_como_erro(self):
        self.falso.rotas["/tesouro.csv"] = (200, "<html>manutenção</html>")
        self.falso.rotas["/dados.csv"] = (404, "")
        t = S.atualizar_tesouro({})["tesouro"]
        self.assertEqual((t["erro"], t.get("titulos")), ("Não consegui ler as taxas do Tesouro Direto.", None))


class TestPaginas(ComServidor):
    def test_le_a_pagina_com_a_ia(self):
        d = self.salvar()
        p = S.ler_pagina_ofertas(self.falso.url + "/pagina", d)
        self.assertEqual((p["status"], [o["nome"] for o in p["ofertas"]]), ("ok", ["CDB Banco Sol", "LCA Banco Sol", "CDB Banco Sol", "Caixinha (Banco Sol)"]))

    def test_situacoes(self):
        d = self.salvar()
        self.assertEqual(S.ler_pagina_ofertas(self.falso.url + "/nao-existe", d)["status"], "sem_acesso")
        self.assertEqual(S.ler_pagina_ofertas(self.falso.url + "/vazia", d)["status"], "sem_ofertas")
        self.assertEqual(S.ler_pagina_ofertas(self.falso.url + "/pagina", self.salvar(ia=False))["status"], "ia_desligada")
        with mock.patch.object(O, "simuladas", return_value={"ofertas": [{"emissor": "X", "produto": "cdb", "indexador": "cdi_pct", "taxa": 150, "trecho": "inventado 150%"}]}):
            self.assertEqual(S.ler_pagina_ofertas(self.falso.url + "/pagina", self.salvar(ia=True))["status"], "nao_confere")
        with mock.patch.object(O, "simuladas", side_effect=ValueError("A IA não devolveu resposta.")):
            self.assertEqual(S.ler_pagina_ofertas(self.falso.url + "/pagina", d)["status"], "erro_ia")

    def test_pagina_velha(self):
        hoje = S.agora_iso()
        self.assertFalse(S._pagina_velha({"em": hoje, "status": "ok"}, False))
        self.assertTrue(S._pagina_velha({"em": hoje, "status": "ok"}, True), "Conferir agora")
        self.assertTrue(S._pagina_velha({"em": (datetime.now() - timedelta(days=1)).isoformat(), "status": "ok"}, False))
        self.assertFalse(S._pagina_velha({"em": hoje, "status": "sem_acesso"}, False), "um erro espera uma hora")
        self.assertTrue(S._pagina_velha({"em": (datetime.now() - timedelta(hours=2)).isoformat(), "status": "sem_acesso"}, False))
        self.assertTrue(S._pagina_velha(None, False))


class TestConferirEEstado(ComServidor):
    def test_conferir_e_o_que_a_tela_ve(self):
        url = self.falso.url + "/pagina"
        bancos = [{"id": "b-lua", "nome": "Banco Lua", "ofertas": url}, {"id": "b-sol", "nome": "Banco Sol"}]
        d = self.salvar(bancos=bancos)
        S.iniciar_oport(esperar=True)
        e = S.oport_estado(S.ler(), disparar=False)
        self.assertEqual([x["nome"] for x in e["titulos"]][:2], ["Tesouro Selic 2031", "Tesouro Reserva 2036"])
        self.assertEqual(len(e["ofertas"]), 4)
        self.assertEqual(e["paginas"], [{"banco": "Banco Lua", "url": url, "dominio": "127.0.0.1", "status": "ok", "ofertas": 4, "em": e["paginas"][0]["em"]}])
        self.assertEqual(e["sem_pagina"], ["Banco Sol"])
        self.assertNotIn("sugestoes", e)
        self.assertEqual((e["tesouro"]["fonte"], e["conferindo"]), ("investir", False))
        # de novo, sem forçar: nada é buscado (o Tesouro vale uma hora; a página, o dia)
        n = len(self.falso.pedidos)
        S.iniciar_oport(esperar=True)
        self.assertEqual(len(self.falso.pedidos), n)
        S.iniciar_oport(forcar=True, esperar=True)
        self.assertEqual(len(self.falso.pedidos), n + 2, "Conferir agora busca tudo")
        # o banco que saiu (ou ficou sem página) sai do que foi guardado; com a IA desligada, as páginas somem da tela
        self.salvar(bancos=[{"id": "b-sol", "nome": "Banco Sol"}])
        S.iniciar_oport(esperar=True)
        self.assertEqual(S.oport_ler()["paginas"], {})
        self.salvar(bancos=bancos, ia=False)
        e = S.oport_estado(S.ler(), disparar=False)
        self.assertEqual((e["ofertas"], e["paginas"], e["sem_pagina"]), ([], [], []))
        self.assertEqual(d["bancos"][0]["ofertas"], url)

    def test_olhar_busca_o_que_esta_velho(self):
        with mock.patch.object(S, "iniciar_oport", return_value=True) as ini:
            e = S.oport_estado(self.salvar())
        ini.assert_called_once_with()
        self.assertTrue(e["conferindo"], "a tela pergunta de novo, mesmo que a busca termine antes da resposta")
        S.oport_gravar({"tesouro": {"em": S.agora_iso(), "titulos": titulos()}})
        with mock.patch.object(S, "iniciar_oport") as ini:
            S.oport_estado(S.ler())
        ini.assert_not_called()

    def test_uma_conferencia_por_vez(self):
        S._oport_conferindo.set()
        self.addCleanup(S._oport_conferindo.clear)
        self.assertFalse(S.iniciar_oport())


class TestAvisar(ComServidor):
    def setUp(self):
        super().setUp()
        S.oport_gravar({"tesouro": {"em": S.agora_iso(), "titulos": titulos()}})

    def test_vai_para_os_celulares_de_quem_foi_escolhido(self):
        d = self.salvar(op_aviso=True, op_para=["person.ana"], op_ipca=7, op_pre=13.5)
        with mock.patch.object(A, "endereco_app", return_value="/app/a1b2_gerencia"):
            self.assertEqual(S.avisar_oport(d), 2, "os dois celulares da Ana")
        alvo, corpo = self.enviados[0]
        self.assertEqual(alvo, "mobile_app_pixel_8")
        self.assertEqual(corpo["title"], "📈 Oportunidades de investimento: 2")
        self.assertEqual(corpo["message"], "• Tesouro Prefixado 2032: 13,71% ao ano\n• Tesouro IPCA+ 2032: IPCA + 7,04%")
        self.assertEqual(corpo["data"], {"tag": "gerencia-oportunidades", "group": "gerencia-oportunidades", "channel": "Oportunidades de investimento",
                                         "url": "/app/a1b2_gerencia/oportunidades", "clickAction": "/app/a1b2_gerencia/oportunidades"})
        self.assertEqual(S.avisar_oport(d), 0, "cada uma uma vez")
        self.assertEqual(S.oport_ler()["avisadas"], {"td:tesouro-prefixado-2032": 13.71, "td:tesouro-ipca-mais-2032": 7.04})

    def test_desligado_nao_anota_e_conferir_agora_so_anota(self):
        d = self.salvar(op_aviso=False, op_para=["person.ana"], op_ipca=7)
        self.assertEqual(S.avisar_oport(d), 0)
        self.assertNotIn("avisadas", S.oport_ler(), "ligando depois, o que já passa é avisado")
        self.assertEqual(S.avisar_oport(d, silencioso=True), 0)
        self.assertEqual(S.oport_ler()["avisadas"], {"td:tesouro-ipca-mais-2032": 7.04})
        self.assertEqual(self.enviados, [])

    def test_ninguem_escolhido_ou_home_assistant_fora(self):
        d = self.salvar(op_aviso=True, op_para=[], op_ipca=7)
        self.assertEqual(S.avisar_oport(d), 0)
        quebrado = A.Avisos(lambda *a, **k: (_ for _ in ()).throw(S.ErroHA("fora")), ws_falso, lambda *a: None)
        Trocar(self, AVISOS=quebrado)
        S.oport_gravar({"tesouro": {"em": S.agora_iso(), "titulos": titulos()}})
        d = self.salvar(op_para=["person.ana"])
        self.assertEqual(S.avisar_oport(d), 0)
        self.assertNotIn("avisadas", S.oport_ler(), "tenta de novo depois")

    def test_a_cada_tantos_dias(self):
        d = self.salvar(op_dias=1)
        self.assertTrue(S.dia_do_aviso_oport(d, None, date(2026, 11, 2)), "nunca avisou")
        self.assertFalse(S.dia_do_aviso_oport(d, "2026-11-02", date(2026, 11, 2)), "já avisou hoje")
        self.assertTrue(S.dia_do_aviso_oport(d, "2026-11-01", date(2026, 11, 2)))
        d = self.salvar(op_dias=3)
        self.assertFalse(S.dia_do_aviso_oport(d, "2026-11-01", date(2026, 11, 3)))
        self.assertTrue(S.dia_do_aviso_oport(d, "2026-11-01", date(2026, 11, 4)), "três dias depois")

    def test_no_horario_uma_vez_por_dia_com_o_aviso_ligado(self):
        d = self.salvar(op_hora="10:00")
        self.assertFalse(S.hora_do_aviso_oport(d, datetime(2026, 11, 2, 9, 59)))
        self.assertTrue(S.hora_do_aviso_oport(d, datetime(2026, 11, 2, 10, 0)))
        S.iniciar_oport(avisar=True, esperar=True)
        self.assertEqual(S.oport_ler()["dia"], date.today().isoformat())

    def test_testar(self):
        Trocar(self, TOKEN="token-teste")
        with self.assertRaisesRegex(ValueError, "Você não é uma pessoa da casa"):
            S.testar_oport("u-ninguem")
        with self.assertRaisesRegex(ValueError, "Sem celular"):
            S.testar_oport("u-beto")
        self.salvar(op_ipca=None)
        self.assertEqual(S.testar_oport("u-ana"), {"enviados": 2, "passam": 0})
        self.assertEqual(self.enviados[-1][1]["message"], "Nada passou do que você quer agora. Quando passar, o aviso vem assim.")
        self.salvar(op_ipca=7)
        self.assertEqual(S.testar_oport("u-ana")["passam"], 1)
        self.assertIn("Tesouro IPCA+ 2032", self.enviados[-1][1]["message"])
        Trocar(self, TOKEN=None)
        with self.assertRaisesRegex(ValueError, "Fora do Home Assistant"):
            S.testar_oport("u-ana")


class TestRotas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.falso = ServidorFalso({"/tesouro.csv": (200, CSV)})
        cls.srv = Servidor({"GERENCIA_TESOURO": cls.falso.url + "/tesouro.csv"})

    @classmethod
    def tearDownClass(cls):
        cls.srv.parar()
        cls.falso.fechar()

    def test_ver_conferir_e_testar(self):
        st, _, r = self.srv.post("/api/oportunidades/conferir", {"forcar": True})
        self.assertEqual(st, 200)
        for _ in range(100):
            st, _, r = self.srv.get("/api/oportunidades")
            if not r["conferindo"] and r["titulos"]:
                break
            import time
            time.sleep(0.05)
        self.assertEqual((st, len(r["titulos"]), r["tesouro"]["fonte"]), (200, 5, "investir"))
        st, _, r = self.srv.post("/api/oportunidades/testar")
        self.assertEqual((st, r["erro"]), (400, "Fora do Home Assistant não dá para avisar no celular."))


if __name__ == "__main__":
    unittest.main()
