"""O servidor de verdade (HTTP): estado com revisão, índices, exportar, backup, versões, importar, imagens,
leitura por IA simulada (com as páginas da câmera), conexão com o CronologIA, bens e páginas."""
import base64
import io
import json
import os
import re
import unittest
import zipfile

from tests.base import Servidor, ler_pdf

JPG = b"\xff\xd8\xff\xe0" + b"\0" * 400 + b"\xff\xd9"
B64 = "data:image/jpeg;base64," + base64.b64encode(JPG).decode()


class TestHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Servidor()

    @classmethod
    def tearDownClass(cls):
        cls.s.parar()

    def estado(self, **mudar):
        _, _, d = self.s.get("/api/state")
        if not mudar:
            return d
        d.update(mudar)
        st, _, novo = self.s.put("/api/state", d)
        self.assertEqual(st, 200, novo)
        return novo

    # ---- páginas
    def test_paginas_e_arquivos(self):
        st, cab, corpo = self.s.get("/")
        self.assertEqual(st, 200)
        self.assertIn(b"<html", corpo.lower())
        self.assertEqual(self.s.get("/app.js")[0], 200)
        self.assertIn("javascript", self.s.get("/app.js")[1]["Content-Type"])
        self.assertEqual(self.s.get("/nao-existe.css")[0], 404)
        self.assertEqual(self.s.get("/..%2fserver.py")[0], 404, "nada fora da pasta www")
        self.assertEqual(self.s.get("/../server.py")[0], 404)
        self.assertEqual(cab.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(self.s.pedir("HEAD", "/")[0], 200)

    # ---- estado
    def test_estado_com_revisao(self):
        d = self.estado()
        self.assertEqual((d["schema"], d["usuario"]), (1, None))
        _, _, comnome = self.s.get("/api/state", cabecalhos={"X-Remote-User-Display-Name": "Ana"})
        self.assertEqual(comnome["usuario"], "Ana", "o ingress diz quem está usando")
        velho = dict(d, rev=d["rev"] - 1, bancos=[{"id": "x"}])
        st, _, atual = self.s.put("/api/state", velho)
        self.assertEqual((st, atual["rev"]), (409, d["rev"]), "revisão velha: devolve a atual")
        novo = self.estado(bancos=[{"id": "b1", "nome": "Banco Azul"}, "lixo"], usuario="ignorado", schema=99)
        self.assertEqual((novo["rev"], len(novo["bancos"]), novo["schema"]), (d["rev"] + 1, 1, 1), "só os campos do usuário; lixo sai")
        self.assertEqual(self.s.get("/api/rev")[2]["rev"], novo["rev"])

    def test_cor_do_dia_ligada_por_padrao_e_desligada_quando_escolhida(self):
        d = self.estado()
        self.assertIs(d["ajustes"]["cor_dia"], True, "ligada sem ninguém escolher")
        a = {k: v for k, v in d["ajustes"].items() if k != "cor_dia"}
        self.assertIs(self.estado(ajustes=dict(a, cor="#8BD45F"))["ajustes"]["cor_dia"], True, "quem só tinha a cor salva fica com a do dia")
        novo = self.estado(ajustes=dict(a, cor="#8BD45F", cor_dia=False))
        self.assertEqual((novo["ajustes"]["cor"], novo["ajustes"]["cor_dia"]), ("#8BD45F", False), "escolher uma cor desliga e guarda")
        self.assertIs(self.estado()["ajustes"]["cor_dia"], False, "e continua desligada")
        self.assertIs(self.estado(ajustes=dict(a, cor_dia=True))["ajustes"]["cor_dia"], True)

    def test_indices_a_mao(self):
        st, _, r = self.s.put("/api/indices", {"cdi": 500})
        self.assertEqual((st, r["erro"]), (400, "Valor fora do esperado."))
        st, _, d = self.s.put("/api/indices", {"cdi": 12.5})
        self.assertEqual((st, d["indices"]["cdi"], d["indices"]["fonte"], d["indices"]["auto"]), (200, 12.5, "manual", False))
        _, _, d = self.s.put("/api/indices", {"auto": True})
        self.assertTrue(d["indices"]["auto"])
        self.assertEqual(self.s.put("/api/indices", {"cdi": "abc"})[0], 400)
        self.assertEqual(self.s.put("/api/outra", {})[0], 404)

    # ---- exportar, backup, versões e importar
    def test_exportar(self):
        self.estado(investimentos=[{"id": "i1", "nome": "CDB Exemplo", "valor": 1000, "indexador": "parado", "tipo": "cdb"}],
                    lancamentos=[{"id": "l1", "tipo": "despesa", "descricao": "Mercado", "valor": 50, "data": "2026-11-03", "pago": True}])
        st, cab, corpo = self.s.get("/api/export/json")
        self.assertEqual(st, 200)
        self.assertRegex(cab["Content-Disposition"], r'attachment; filename="gerencia-\d{4}-\d{2}-\d{2}-\d{4}\.json"')
        self.assertEqual(corpo["investimentos"][0]["nome"], "CDB Exemplo")
        self.assertIn("CDB Exemplo", self.s.get("/api/export/csv", cru=True)[2].decode("utf-8-sig"))
        st, cab, corpo = self.s.get("/api/export/lancamentos", cru=True)
        self.assertIn("Mercado", corpo.decode("utf-8-sig"))
        self.assertRegex(cab["Content-Disposition"], r"lancamentos-")
        z = zipfile.ZipFile(io.BytesIO(self.s.get("/api/export/zip")[2]))
        self.assertIn("gerencia.json", z.namelist())
        st, _, html = self.s.get("/relatorio")
        self.assertIn(b"CDB Exemplo", html)
        self.assertIn("attachment", self.s.get("/relatorio?baixar=1")[1]["Content-Disposition"])
        self.assertIn(b'data-theme="dark"', self.s.get("/relatorio?tema=escuro")[2], "o relatório no tema do app")
        self.assertIn(b"class=on aria-current=page>De terceiros</a>", self.s.get("/relatorio?quem=terceiros")[2])

    def test_relatorio_em_pdf_para_baixar(self):
        """Baixar PDF: um arquivo de verdade (o app do Home Assistant no Android não imprime a página)."""
        st, cab, corpo = self.s.get("/relatorio.pdf?quem=meus")
        self.assertEqual(st, 200)
        self.assertEqual(cab["Content-Type"], "application/pdf")
        self.assertRegex(cab["Content-Disposition"], r'^attachment; filename="patrimonio-\d{4}-\d{2}-\d{2}-meus\.pdf"$')
        self.assertTrue(corpo.startswith(b"%PDF-1.4") and corpo.endswith(b"%%EOF\n"))
        self.assertTrue(any(t.startswith("Só os seus · ") for p in ler_pdf(corpo) for t in p))
        self.assertRegex(self.s.get("/relatorio.pdf")[1]["Content-Disposition"], r'filename="patrimonio-\d{4}-\d{2}-\d{2}\.pdf"$')

    def test_relatorio_sabe_quem_abriu(self):
        """1.52: a conta de um investimento de antes num banco com várias pessoas é a de quem abriu (o nome vem do ingress)."""
        _, _, d = self.s.get("/api/state")
        antes = json.loads(json.dumps(d))
        d["bancos"] = [{"id": "bq", "nome": "Banco Quartzo", "contas": [{"id": "qa", "pessoa": "Ana"}, {"id": "qb", "pessoa": "Beto"}]}]
        d["investimentos"] = [{"id": "iq", "nome": "CDB Quartzo", "banco": "bq", "tipo": "cdb", "valor": 1000, "indexador": "parado"}]
        _, _, d = self.s.put("/api/state", d)
        self.addCleanup(lambda: self.s.put("/api/state", dict(antes, rev=self.s.get("/api/state")[2]["rev"])))
        self.assertIn("Banco Quartzo · Beto".encode(), self.s.get("/relatorio", cabecalhos={"X-Remote-User-Name": "Beto"})[2])
        self.assertIn("Banco Quartzo · Ana".encode(), self.s.get("/relatorio")[2], "fora do ingress: a primeira conta")
        pdf = self.s.get("/relatorio.pdf", cabecalhos={"X-Remote-User-Display-Name": "Beto Souza"})[2]
        t = [x for p in ler_pdf(pdf) for x in p]
        self.assertTrue({"Banco Quartzo", "Beto"} <= set(t), "no PDF, o banco e a pessoa embaixo dele")

    def test_relatorio_detalhado(self):
        self.assertEqual(self.s.get("/relatorio?detalhar=1")[0], 200)
        st, _, corpo = self.s.get("/relatorio.pdf?detalhar=1&quem=meus")
        self.assertEqual(st, 200)
        self.assertTrue(corpo.startswith(b"%PDF"))

    def test_relatorio_em_pdf_nao_poe_o_pedido_no_cabecalho(self):
        st, cab, _ = self.s.get("/relatorio.pdf?quem=x%22%0D%0AX-Falso:%201")
        self.assertEqual(st, 200)
        self.assertNotIn("X-Falso", cab)
        self.assertRegex(cab["Content-Disposition"], r'filename="patrimonio-\d{4}-\d{2}-\d{2}\.pdf"$')

    def test_backup_na_pasta_share_e_restaurar(self):
        self.estado(investimentos=[{"id": "i1", "nome": "Antes do backup", "valor": 1, "indexador": "parado"}])
        st, _, r = self.s.post("/api/backup")
        self.assertEqual((st, r["pasta"]), (200, "share/gerencia"))
        self.assertTrue(os.path.isfile(os.path.join(self.s.dirs["share"], r["arquivo"])))
        lista = self.s.get("/api/backups")[2]
        self.assertIn(r["arquivo"], [b["nome"] for b in lista])
        self.estado(investimentos=[])
        st, _, d = self.s.post("/api/backups/restaurar", {"nome": r["arquivo"]})
        self.assertEqual((st, d["investimentos"][0]["nome"]), (200, "Antes do backup"))
        self.assertEqual(self.s.post("/api/backups/restaurar", {"nome": "../../etc/passwd"})[0], 400)
        self.assertEqual(self.s.post("/api/backups/restaurar", {"nome": "gerencia-nao-existe.zip"})[2]["erro"], "Esse backup não existe mais.")

    def test_versoes(self):
        self.estado(categorias=[{"id": "c1", "nome": "Versão 1", "tipo": "despesa"}])
        vs = self.s.get("/api/versoes")[2]
        self.assertTrue(vs, "a primeira gravação guarda uma versão")
        st, _, d = self.s.post("/api/versoes/restaurar", {"nome": vs[0]["nome"]})
        self.assertEqual(st, 200)
        self.assertGreater(d["rev"], 0)
        self.assertEqual(self.s.post("/api/versoes/restaurar", {"nome": "x.json"})[2]["erro"], "Versão inválida.")
        self.assertEqual(self.s.post("/api/versoes/restaurar", {"nome": "gerencia-20000101-000000-x.json"})[2]["erro"], "Essa versão não existe mais.")

    def test_importar(self):
        dados = {"investimentos": [{"id": "imp", "nome": "Importado", "valor": 10, "indexador": "parado"}]}
        st, _, d = self.s.pedir("POST", "/api/importar", json.dumps(dados).encode(), {"X-Nome-Arquivo": "dados.json"})
        self.assertEqual((st, d["investimentos"][0]["nome"]), (200, "Importado"))
        st, _, r = self.s.pedir("POST", "/api/importar", b'{"outra": 1}', {"X-Nome-Arquivo": "x.json"})
        self.assertEqual((st, r["erro"]), (400, "Esse arquivo não parece um backup do GerencIA."))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("leia.txt", "nada")
        st, _, r = self.s.pedir("POST", "/api/importar", buf.getvalue(), {"X-Nome-Arquivo": "x.zip"})
        self.assertEqual((st, r["erro"]), (400, "O .zip não tem o arquivo gerencia.json."))
        self.assertEqual(self.s.pedir("POST", "/api/importar", b"PK\x03\x04lixo", {"X-Nome-Arquivo": "x.zip"})[0], 400)

    # ---- imagens
    def test_imagens(self):
        st, _, r = self.s.post("/api/fotos", {"jpg": B64})
        self.assertEqual(st, 200)
        self.assertRegex(r["arquivo"], r"^\d{8}-\d{6}-[0-9a-f]{6}\.jpg$")
        st, cab, corpo = self.s.get("/fotos/" + r["arquivo"])
        self.assertEqual((st, cab["Content-Type"], corpo), (200, "image/jpeg", JPG))
        self.assertEqual(self.s.get("/fotos/../gerencia.json")[0], 404)
        self.assertEqual(self.s.get("/fotos/20260101-000000-abcdef.jpg")[0], 404)
        self.assertEqual(self.s.post("/api/fotos", {"jpg": "não é base64!"})[2]["erro"], "Imagem inválida.")
        self.assertEqual(self.s.post("/api/fotos", {"jpg": base64.b64encode(b"PNG" * 100).decode()})[2]["erro"], "Envie a imagem em JPG.")

    # ---- leitura por IA (simulada)
    def test_ler_com_ia(self):
        st, _, r = self.s.post("/api/ia/ler", {"modo": "auto", "dica": "caixa", "texto": "gastei 64,90 no ifood"})
        self.assertEqual(st, 200)
        self.assertTrue(r["lancamentos"])
        self.assertEqual(r["entidade"], "ai_task.simulada")
        st, _, r = self.s.post("/api/ia/ler", {"modo": "auto", "dica": "invest", "texto": "cdb a 110% do cdi", "so_invest": True})
        self.assertEqual(r["lancamentos"], [], "do Novo investimento: só investimentos")
        self.assertEqual(self.s.post("/api/ia/ler", {"modo": "auto"})[2]["erro"], "Envie uma imagem, um PDF ou cole um texto.")
        self.assertEqual(self.s.post("/api/ia/ler", {"modo": "auto", "anexo": {"b64": "!!!"}})[2]["erro"], "Arquivo inválido.")
        self.assertEqual(self.s.post("/api/ia/ler", {"modo": "auto", "anexo": {"b64": base64.b64encode(b"GIF89a").decode()}})[2]["erro"], "Envie uma imagem (JPG, PNG ou WebP) ou um PDF.")

    def test_digitalizar_varias_paginas(self):
        antes = self.s.get("/api/ia/uso")[2]["today"]["images"]
        st, _, r = self.s.post("/api/ia/ler", {"modo": "auto", "dica": "caixa", "texto": "", "anexos": [{"b64": B64}, {"b64": B64}, {"b64": B64}]})
        self.assertEqual(st, 200, r)
        self.assertEqual(self.s.get("/api/ia/uso")[2]["today"]["images"], antes + 3, "o uso conta as 3 imagens")
        pdf = "data:application/pdf;base64," + base64.b64encode(b"%PDF-1.4 exemplo").decode()
        self.assertEqual(self.s.post("/api/ia/ler", {"modo": "auto", "anexos": [{"b64": B64}, {"b64": pdf}]})[2]["erro"], "Envie um PDF por vez.")
        st, _, r = self.s.post("/api/ia/ler", {"modo": "auto", "anexos": [{"b64": B64}] * 9})
        self.assertEqual(st, 200, "mais de 6: lê as 6 primeiras")

    def test_status_da_ia_e_da_fala(self):
        st, _, r = self.s.get("/api/ia/status")
        self.assertEqual(st, 200)
        self.assertIn("pronta", r)
        st, _, v = self.s.get("/api/voz/status")
        self.assertEqual((st, v["pronta"]), (200, True))
        st, _, t = self.s.pedir("POST", "/api/voz", b"\0\1" * 8000, {"Content-Type": "application/octet-stream"})
        self.assertEqual(st, 200, t)
        self.assertIn("mercado", t["texto"])
        st, _, t = self.s.pedir("POST", "/api/voz", b"\0" * 10, {"Content-Type": "application/octet-stream"})
        self.assertEqual(st, 400)
        self.assertIn("Não ouvi nada", t["erro"])

    def test_ia_desligada(self):
        d = self.estado()
        self.estado(ajustes=dict(d["ajustes"], ia=False))
        try:
            v = self.s.get("/api/voz/status")[2]
            self.assertEqual((v["pronta"], v["motivo"]), (False, "A IA está desligada em Mais › Configurações › Integrações."))
        finally:
            d = self.estado()
            self.estado(ajustes=dict(d["ajustes"], ia=True))

    # ---- bens e dicas
    def test_bens_sem_inventaria(self):
        st, _, b = self.s.get("/api/bens")
        self.assertEqual((st, b["ok"]), (200, False))
        self.assertIn("InventarIA não foi encontrado", b["motivo"])
        d = self.estado()
        self.estado(ajustes=dict(d["ajustes"], bens=False))
        self.assertEqual(self.s.get("/api/bens")[2], {"ok": False, "desligado": True})
        d = self.estado()
        self.estado(ajustes=dict(d["ajustes"], bens=True))

    def test_dicas(self):
        st, _, r = self.s.get("/api/dicas")
        self.assertEqual(st, 200)
        self.assertIsInstance(r, dict)
        st, _, r = self.s.post("/api/dicas/conferir")
        self.assertEqual(st, 200)
        self.assertIn("assinaturas", r)

    def test_atualizar_indices_e_bens(self):
        st, _, d = self.s.post("/api/indices/atualizar")
        self.assertEqual((st, d["indices"]["erro"]), (200, "Sem resposta do Banco Central"), "o Banco Central do teste não responde")
        st, _, b = self.s.post("/api/bens/atualizar")
        self.assertEqual((st, b["ok"]), (200, False))

    def test_falar(self):
        st, _, r = self.s.post("/api/voz", b"\0\1" * 8000, cabecalhos={"Content-Type": "audio/wav"})
        self.assertEqual(st, 200)
        self.assertTrue(r["texto"])
        st, _, r = self.s.post("/api/voz", b"\0" * 10, cabecalhos={"Content-Type": "audio/wav"})
        self.assertEqual(st, 400)
        self.assertTrue(r["erro"])

    def test_backup_com_imagens_ida_e_volta(self):
        _, _, f = self.s.post("/api/fotos", {"jpg": B64})
        self.estado(investimentos=[{"id": "ft", "nome": "Com imagem", "valor": 5, "indexador": "parado", "fotos": [f["arquivo"]]}])
        _, _, z = self.s.get("/api/export/zip")
        os.remove(os.path.join(self.s.dirs["data"], "fotos", f["arquivo"]))
        self.assertEqual(self.s.get("/fotos/" + f["arquivo"])[0], 404)
        st, _, d = self.s.pedir("POST", "/api/importar", z, {"X-Nome-Arquivo": "backup.zip"})
        self.assertEqual((st, d["investimentos"][0]["fotos"]), (200, [f["arquivo"]]))
        self.assertEqual(self.s.get("/fotos/" + f["arquivo"], cru=True)[2], JPG, "a imagem volta do backup")

    # ---- rotas que não existem
    def test_nao_encontrado(self):
        self.assertEqual(self.s.post("/api/nada")[0], 404)


class TestConexaoComOCronologIA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Servidor()
        with open(os.path.join(cls.s.dirs["share"], "integracao.json"), encoding="utf-8") as f:
            cls.arquivo = json.load(f)
        cls.chave = cls.arquivo["chave"]
        cls.auth = {"Authorization": f"Bearer {cls.chave}", "X-App": "CronologIA"}

    def test_o_arquivo_comeca_como_o_dos_outros_apps(self):
        self.assertEqual({k: self.arquivo[k] for k in ("app", "nome")}, {"app": "gerencia", "nome": "GerencIA"})
        self.assertRegex(self.arquivo["versao"], r"^\d+\.\d+\.\d+$")

    @classmethod
    def tearDownClass(cls):
        cls.s.parar()

    def test_publica_o_endereco_e_a_chave(self):
        with open(os.path.join(self.s.dirs["share"], "integracao.json"), encoding="utf-8") as f:
            p = json.load(f)
        self.assertEqual((p["app"], p["url"]), ("gerencia", self.s.url))
        self.assertGreaterEqual(len(p["chave"]), 32)

    def test_a_depreciacao_dos_bens_para_o_inventaria(self):
        # 1.55.0: a perda por ano de cada categoria (a padrão e a mudada em Mais › Invest) vai no arquivo; sem Bens, sai
        ler = lambda: json.load(open(os.path.join(self.s.dirs["share"], "integracao.json"), encoding="utf-8"))
        self.assertEqual((ler()["depreciacao"]["eletronicos"], ler()["depreciacao"]["imoveis"]), (20, 0))
        _, _, d = self.s.get("/api/state")
        d["ajustes"]["bens_taxas"] = {"eletronicos": 30, "imoveis": -3}
        self.assertEqual(self.s.put("/api/state", d)[0], 200)
        try:
            self.assertEqual((ler()["depreciacao"]["eletronicos"], ler()["depreciacao"]["imoveis"], ler()["chave"]), (30, -3, self.chave), "a taxa mudada, a mesma chave")
            _, _, d = self.s.get("/api/state")
            d["ajustes"]["bens"] = False
            self.s.put("/api/state", d)
            self.assertNotIn("depreciacao", ler(), "sem Bens da casa, nada")
        finally:
            _, _, d = self.s.get("/api/state")
            d["ajustes"].update(bens=True, bens_taxas={})
            self.s.put("/api/state", d)
        self.assertEqual(ler()["depreciacao"]["eletronicos"], 20)

    def test_sem_chave_nao_entra(self):
        for cab in ({}, {"Authorization": "Bearer errada"}):
            st, _, r = self.s.get("/api/integracao/contas", cabecalhos=cab)
            self.assertEqual(st, 401)
            self.assertIn("Chave inválida", r["erro"])

    def test_contas_pagar_desfazer_e_nova(self):
        st, _, r = self.s.post("/api/integracao/nova", {"descricao": "Conta de luz", "valor": 180.5, "vencimento": "2026-11-20"}, cabecalhos=self.auth)
        self.assertEqual(st, 200, r)
        cid = r["id"]
        st, _, lista = self.s.get("/api/integracao/contas?de=2026-11-01&ate=2026-11-30", cabecalhos=self.auth)
        self.assertEqual(st, 200)
        self.assertIn(cid, [c["id"] for c in lista["contas"]])
        self.assertTrue(lista["versao"])
        st, _, r = self.s.post("/api/integracao/pagar", {"id": cid, "valor": "190"}, cabecalhos=self.auth)
        self.assertEqual(st, 200)
        _, _, d = self.s.get("/api/state")
        luz = next(l for l in d["lancamentos"] if l["id"] == cid)
        self.assertEqual((luz["pago"], luz["valor"]), (True, 190.0))
        self.s.post("/api/integracao/desfazer", {"id": cid}, cabecalhos=self.auth)
        _, _, d = self.s.get("/api/state")
        self.assertFalse(next(l for l in d["lancamentos"] if l["id"] == cid)["pago"])
        self.assertEqual(self.s.get("/api/rev")[2]["integracao_ultimo"]["app"], "CronologIA", "o app mostra quem usou por último")

    def test_erros(self):
        self.assertEqual(self.s.post("/api/integracao/pagar", {"id": "nada"}, cabecalhos=self.auth)[0], 404)
        st, _, r = self.s.post("/api/integracao/nova", {"descricao": ""}, cabecalhos=self.auth)
        self.assertEqual((st, r["erro"]), (400, "Coloque o nome da conta."))
        st, _, r = self.s.get("/api/integracao/contas?de=2026-01-01&ate=2028-01-01", cabecalhos=self.auth)
        self.assertEqual((st, r["erro"]), (400, "Período inválido."))
        self.assertEqual(self.s.get("/api/integracao/contas?de=ontem", cabecalhos=self.auth)[0], 400, "data ruim")

    def test_desligar_apaga_o_arquivo_e_fecha_a_porta(self):
        _, _, d = self.s.get("/api/state")
        d["ajustes"]["integracao"] = False
        self.assertEqual(self.s.put("/api/state", d)[0], 200)
        try:
            self.assertFalse(os.path.exists(os.path.join(self.s.dirs["share"], "integracao.json")))
            self.assertEqual(self.s.get("/api/integracao/contas", cabecalhos=self.auth)[0], 401)
        finally:
            _, _, d = self.s.get("/api/state")
            d["ajustes"]["integracao"] = True
            self.s.put("/api/state", d)
        self.assertTrue(os.path.exists(os.path.join(self.s.dirs["share"], "integracao.json")), "religou: volta o arquivo")


if __name__ == "__main__":
    unittest.main()
