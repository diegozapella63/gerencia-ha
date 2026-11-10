"""server.py, as partes sem rede: dados, versões, o que a IA devolve (limpo), exportações e importação."""
import csv
import io
import json
import os
import unittest
import zipfile
from datetime import date

from tests.base import importar_servidor

S = importar_servidor()


def exemplo():
    d = S.vazio()
    d["bancos"] = [{"id": "b1", "nome": "Banco Azul", "contas": [{"id": "c1", "pessoa": "Ana"}]}]
    d["investimentos"] = [
        {"id": "i1", "nome": "CDB Azul", "banco": "b1", "tipo": "cdb", "valor": 1000, "indexador": "parado", "titular": "meu"},
        {"id": "i2", "nome": "Poupança da Mãe", "banco": "b1", "tipo": "poupanca", "valor": 500, "indexador": "parado", "titular": "terceiros", "terceiro": "Mãe"},
    ]
    d["lancamentos"] = [{"id": "l1", "tipo": "despesa", "descricao": "Mercado; feira", "valor": 120.5, "data": "2026-11-03", "categoria": "c-mercado", "conta": "c1", "pago": True}]
    return d


class TestDados(unittest.TestCase):
    def test_vazio(self):
        d = S.vazio()
        self.assertEqual((d["schema"], d["rev"], d["exemplo"], d["investimentos"]), (1, 0, False, []))
        self.assertEqual(d["ajustes"]["sensores"], False)
        self.assertTrue(d["categorias"])
        self.assertIsNot(d["ajustes"], S.AJUSTES_PADRAO, "uma cópia")

    def test_normalizar(self):
        self.assertEqual(S.normalizar("lixo"), S.vazio())
        d = S.normalizar({"rev": "7", "investimentos": [{"id": "a"}, "lixo", 3], "ajustes": {"tema": "escuro", "sensores": True}, "indices": {"cdi": 10}, "outro": 1})
        self.assertEqual((d["rev"], len(d["investimentos"]), d["ajustes"]["tema"], d["indices"]["cdi"], d["indices"]["selic"]), (7, 1, "escuro", 10, S.INDICES_PADRAO["selic"]))
        self.assertFalse(d["ajustes"]["sensores"], "sem sensores_v: os sensores antigos ficam desligados até ligar")
        self.assertTrue(S.normalizar({"ajustes": {"sensores": True, "sensores_v": 2}})["ajustes"]["sensores"])
        self.assertEqual(S.normalizar({"rev": "abc"})["rev"], 0)
        self.assertNotIn("outro", d)

    def test_cor_do_dia_ligada_por_padrao(self):
        self.assertIs(S.vazio()["ajustes"]["cor_dia"], True)
        self.assertIs(S.normalizar({"ajustes": {"cor": "#8BD45F"}})["ajustes"]["cor_dia"], True, "quem já tinha escolhido uma cor também fica com a do dia")
        self.assertIs(S.normalizar({"ajustes": {"cor": "#8BD45F", "cor_dia": False}})["ajustes"]["cor_dia"], False, "desligada continua desligada")
        for lixo in (None, "nao", 0, []):
            with self.subTest(cor_dia=lixo):
                self.assertIs(S.normalizar({"ajustes": {"cor_dia": lixo}})["ajustes"]["cor_dia"], True, "só um False desliga")

    def test_historico_um_ponto_por_dia(self):
        d = exemplo()
        S.registrar_historico(d, hoje=date(2026, 11, 1))
        S.registrar_historico(d, hoje=date(2026, 11, 2))
        d["investimentos"][0]["valor"] = 2000
        S.registrar_historico(d, hoje=date(2026, 11, 2))
        self.assertEqual([(h["d"], h["total"], h["meu"], h["terceiros"]) for h in d["historico"]], [("2026-11-01", 1500, 1000, 500), ("2026-11-02", 2500, 2000, 500)])
        vazio = S.vazio()
        S.registrar_historico(vazio)
        self.assertEqual(vazio["historico"], [], "sem investimentos e sem histórico: nada")

    def test_salvar_ler_e_versoes(self):
        d = exemplo()
        S._ultima_versao = 0
        S.salvar(d)
        self.assertEqual(S.ler()["investimentos"][0]["nome"], "CDB Azul")
        self.assertIsNotNone(S.guardar_versao("teste", forcar=True))
        self.assertIsNone(S.guardar_versao("teste"), "no máximo uma a cada 10 minutos")
        for k in range(4):
            S.guardar_versao(f"v{k}", forcar=True)
        self.assertLessEqual(len(os.listdir(S.VERSOES)), S.MAX_VERSOES, "guarda só as 3 últimas")
        vs = S.listar_versoes()
        self.assertTrue(vs and all("nome" in v for v in vs))

    def test_ler_arquivo_ruim(self):
        S.gravar_arquivo(S.ARQ, "{quebrado")
        self.assertEqual(S.ler(), S.vazio())
        os.remove(S.ARQ)
        self.assertEqual(S.ler(), S.vazio())


class TestRespostaDaIA(unittest.TestCase):
    def test_extrair_json(self):
        self.assertEqual(S.extrair_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(S.extrair_json('Claro! Aqui está: {"itens": [1, 2]} Espero ter ajudado.'), {"itens": [1, 2]})
        self.assertEqual(S.extrair_json("lista: [1, 2] fim"), [1, 2])
        self.assertEqual(S.extrair_json({"x": 1}), {"x": 1})
        with self.assertRaisesRegex(ValueError, "Não deu para entender"):
            S.extrair_json("nada aqui")
        with self.assertRaises(ValueError):
            S.extrair_json(None)

    def test_investimentos(self):
        d = exemplo()
        r = S.ia_limpar({"itens": [
            {"nome": "  CDB Azul 2028  ", "banco": "Azul", "tipo": "CDB", "valor": "R$ 15.412,37", "aplicado": "15.000", "data_valor": "2026-11-01", "indexador": "CDI_PCT", "taxa": "112", "vencimento": "2028-03-13", "liquidez": "Diária", "existente": "i1", "dono": "Mãe", "confianca": "alta"},
            {"tipo": "cripto", "valor": -5, "indexador": "nenhum", "data_valor": "31/12/2026", "vencimento": "2026-02-30", "existente": "nao-existe", "dono": "eu", "confianca": "total"},
            "lixo",
        ]}, d)
        self.assertEqual(r[0], {"nome": "CDB Azul 2028", "banco": "Azul", "tipo": "cdb", "valor": 15412.37, "aplicado": 15000.0, "data_valor": "2026-11-01", "indexador": "cdi_pct", "taxa": 112.0,
                                "vencimento": "2028-03-13", "liquidez": "diaria", "existente": "i1", "aporte": 0.0, "dono": "Mãe", "confianca": "alta"})
        self.assertEqual((r[1]["nome"], r[1]["tipo"], r[1]["valor"], r[1]["indexador"], r[1]["data_valor"], r[1]["vencimento"], r[1]["existente"], r[1]["dono"], r[1]["confianca"]),
                         ("Investimento", "outro", 0.0, "cdi_pct", "", "", "", "", "media"))
        self.assertEqual(len(S.ia_limpar({"itens": [{}] * 30}, d)), 20, "no máximo 20")

    def test_lancamentos(self):
        d = exemplo()
        r = S.ia_limpar_caixa([
            {"tipo": "Receita", "descricao": "Pix do Beto", "valor": "150,00", "data": "2026-11-02", "categoria": "c-salario", "situacao": "feito"},
            {"tipo": "despesa", "descricao": "", "valor": -89.9, "categoria": "c-salario", "parcela_atual": 2, "parcelas_total": 6, "cartao": 1, "banco": "Azul"},
            {"tipo": "despesa", "valor": 10, "parcela_atual": 7, "parcelas_total": 6},
            {"tipo": "despesa", "valor": 0},
        ], d)
        self.assertEqual(len(r), 3, "valor zero sai")
        self.assertEqual((r[0]["tipo"], r[0]["valor"], r[0]["categoria"], r[0]["situacao"]), ("receita", 150.0, "c-salario", "feito"))
        self.assertEqual((r[1]["descricao"], r[1]["valor"], r[1]["categoria"], r[1]["parcela_atual"], r[1]["parcelas_total"], r[1]["cartao"]), ("Gasto", 89.9, "", 2, 6, True), "categoria de receita numa despesa sai")
        self.assertEqual(r[1]["data"], date.today().isoformat(), "sem data: hoje")
        self.assertEqual((r[2]["parcela_atual"], r[2]["parcelas_total"]), (0, 0), "parcela 7 de 6: ignora")

    def test_automatico_separa_sozinho(self):
        d = exemplo()
        r = S.ia_limpar_auto({"lancamentos": [{"tipo": "despesa", "valor": 10}], "investimentos": [{"nome": "Caixinha", "aporte": 300}]}, d)
        self.assertEqual((len(r["lancamentos"]), r["investimentos"][0]["valor"]), (1, 300.0), "novo só com aporte: o aporte é o valor")
        r = S.ia_limpar_auto([{"descricao": "Mercado", "valor": 50}, {"nome": "CDB", "indexador": "pre", "valor": 1000}], d)
        self.assertEqual((len(r["lancamentos"]), len(r["investimentos"])), (1, 1), "uma lista só: separa pelo jeito")
        self.assertEqual(S.ia_limpar_auto("lixo", d), {"lancamentos": [], "investimentos": []})

    def test_atualizar_saldos_nunca_soma_aporte(self):
        r = S._so_saldos({"lancamentos": [1], "investimentos": [{"valor": 0, "aporte": 500}, {"valor": 800, "aporte": 100}]}, True)
        self.assertEqual((r["lancamentos"], [(i["valor"], i["aporte"]) for i in r["investimentos"]]), ([], [(500, 0), (800, 0)]))
        same = {"lancamentos": [1], "investimentos": [{"valor": 0, "aporte": 5}]}
        self.assertEqual(S._so_saldos(same, False)["investimentos"][0]["aporte"], 5)

    def test_holerite(self):
        h = S.ia_limpar_holerite({"data": "2026-10-31", "creditos": [{"descricao": "Salário", "valor": "5.000,00"}, {"valor": 0}],
                                  "debitos": [{"descricao": "INSS", "valor": -550, "tipo": "Imposto"}, {"valor": 10, "tipo": "x"}], "total_creditos": 5000, "liquido": "4.440"})
        self.assertEqual(h["creditos"], [{"descricao": "Salário", "valor": 5000.0}])
        self.assertEqual(h["debitos"], [{"descricao": "INSS", "valor": 550.0, "tipo": "imposto"}, {"descricao": "Desconto", "valor": 10.0, "tipo": "outro"}])
        self.assertEqual((h["data"], h["liquido"], h["total_debitos"]), ("2026-10-31", 4440.0, 0.0))
        self.assertEqual(S.ia_limpar_holerite([])["creditos"], [])

    def test_prompt(self):
        d = exemplo()
        p = S.ia_prompt(d, "auto", True, "", saldos=True, pessoa="Mãe")
        self.assertIsInstance(p, str)
        self.assertIn("Poupança da Mãe", p, "a IA vê os investimentos para achar cada um")
        self.assertIn("Leia o anexo", S.ia_prompt(d, "caixa", True, ""))
        self.assertIn("gastei 45", S.ia_prompt(d, "caixa", False, "gastei 45"))


class TestSimulacoes(unittest.TestCase):
    def test_saldos_simulados_acham_o_investimento(self):
        d = exemplo()
        r = S.ia_simulada_saldos("Azul, valor atualizado, R$ 1.250,50\nDinheiro 300\nNovo Banco 2 mil", d)
        inv = r["investimentos"]
        self.assertEqual([(i["nome"], i["valor"], i["existente"]) for i in inv], [("CDB Azul", 1250.5, "i1"), ("Dinheiro", 300, ""), ("Novo Banco", 2000, "")], "o nome como foi escrito, com a primeira letra maiúscula")
        self.assertEqual((inv[1]["tipo"], inv[1]["indexador"]), ("dinheiro", "parado"))
        m = S.ia_simulada_saldos("Tudo dinheiro da mãe\nAzul 600", d)["investimentos"]
        self.assertEqual((m[0]["nome"], m[0]["dono"]), ("Poupança da Mãe", "Mãe"))

    def test_auto_simulado(self):
        d = exemplo()
        self.assertTrue(S.ia_simulada_auto("gastei 50 no mercado", "caixa", d)["lancamentos"])
        self.assertTrue(S.ia_simulada_auto("um cdb a 110% do cdi", "caixa", d)["investimentos"])
        r = S.ia_simulada_auto("apliquei 3 mil no cdb", "invest", d)
        self.assertEqual((r["investimentos"][0]["existente"], r["investimentos"][0]["aporte"]), ("i1", 3000))
        self.assertEqual(S.ia_simulada_auto("texto qualquer", "invest", d)["lancamentos"], [])


class TestArquivos(unittest.TestCase):
    def test_csv_dos_investimentos(self):
        linhas = list(csv.reader(io.StringIO(S.gerar_csv(exemplo()).decode("utf-8-sig")), delimiter=";"))
        self.assertGreaterEqual(len(linhas), 3)
        self.assertTrue(any("CDB Azul" in l for l in linhas[1:]))

    def test_csv_dos_lancamentos(self):
        texto = S.gerar_csv_lancamentos(exemplo()).decode("utf-8-sig")
        self.assertIn('"Mercado; feira"', texto, "o separador dentro do texto fica entre aspas")

    def test_zip_e_importar_de_volta(self):
        d = exemplo()
        z = S.gerar_zip(d)
        nomes = zipfile.ZipFile(io.BytesIO(z)).namelist()
        self.assertIn("gerencia.json", nomes)
        S.salvar(S.vazio(), versao=False)
        r = S.importar(z, "backup.zip")
        self.assertEqual([i["nome"] for i in r["investimentos"]], ["CDB Azul", "Poupança da Mãe"])
        r = S.importar(json.dumps(d).encode(), "dados.json")
        self.assertEqual(len(r["lancamentos"]), 1)

    def test_importar_ruim(self):
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            S.importar(b"PK\x03\x04quebrado", "x.zip")
        with self.assertRaises(ValueError):
            S.importar(b"nem json nem zip", "x.txt")

    def test_relatorio(self):
        h = S.gerar_relatorio(exemplo())
        h = h.decode() if isinstance(h, bytes) else h
        self.assertIn("CDB Azul", h)
        self.assertIn("<html", h.lower())


class TestUso(unittest.TestCase):
    def test_cota(self):
        self.assertTrue(S.e_cota("429 Too Many Requests: quota exceeded"))
        self.assertFalse(S.e_cota("Timeout"))

    def test_registrar_e_resumir(self):
        S.registrar_uso("ler", "ai_task.simulada", 1000, 300, 2, 1.5, "ok")
        S.registrar_uso("ler", "ai_task.simulada", 1000, 0, 0, 0.5, "cota")
        u = S.resumo_uso()
        self.assertGreaterEqual(u["today"]["calls"], 2)
        self.assertGreaterEqual(u["today"]["quota"], 1)
        self.assertGreaterEqual(u["today"]["images"], 2)
        self.assertEqual(len(u["days"]), 7)
        self.assertEqual(u["days"][-1]["day"], S.uso_dia())

    def test_o_motivo_do_erro_fica_na_chamada(self):
        from unittest import mock
        with mock.patch.object(S, "ha_request", side_effect=S.ErroHA("O Home Assistant recusou o pedido: Error generating data:\n  arquivo grande demais")):
            with self.assertRaises(S.ErroHA):
                S.ia_chamar("caixa", {"task_name": "x", "instructions": "y"}, 1)
        c = S.resumo_uso()["recent"][0]
        self.assertEqual((c["kind"], c["result"], c["error"]), ("caixa", "erro", "O Home Assistant recusou o pedido: Error generating data: arquivo grande demais"))
        S.registrar_uso("caixa", "", 10, 10, 0, 0.1, "ok", "não guarda")
        self.assertNotIn("error", S.resumo_uso()["recent"][0], "só a chamada com erro guarda o motivo")

    def test_o_tempo_esgotado_em_portugues(self):
        from unittest import mock
        with mock.patch.object(S, "TOKEN", "x"), mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaisesRegex(S.ErroHA, "^O Home Assistant não respondeu em 180 s.$"):
                S.ha_request("POST", "/services/ai_task/generate_data", {}, timeout=180)


if __name__ == "__main__":
    unittest.main()
