"""O PDF feito à mão (pdf.py), usado pelo Relatório de patrimônio: a estrutura (objetos, xref, páginas) que os leitores
de PDF exigem, os acentos em WinAnsi, os caracteres que precisam de escape, as medidas do texto (largura, cortar com
"…", quebrar linhas), as formas e as páginas. Textos inventados."""
import re
import shutil
import subprocess
import unittest
import zlib

from tests.base import ler_pdf, pasta_temp
import pdf  # noqa: E402  (o tests.base põe gerencia/app no caminho)


def conteudo(doc, k=0):
    """Os comandos da página k, já descompactados."""
    b = doc.bytes()
    streams = [zlib.decompress(b[m.end():m.end() + int(m.group(1))])
               for m in re.finditer(rb"/Length (\d+) /Filter /FlateDecode >>\nstream\n", b)]
    return streams[k].decode("latin-1")


class TestEstrutura(unittest.TestCase):
    def doc(self):
        d = pdf.Documento("Relatório de teste")
        d.texto(40, 60, "Olá, Ana!", 12, True)
        d.nova_pagina()
        d.texto(40, 60, "Segunda página", 10)
        return d

    def test_cabecalho_e_fim(self):
        b = self.doc().bytes()
        self.assertTrue(b.startswith(b"%PDF-1.4\n"))
        self.assertTrue(b.endswith(b"%%EOF\n"))

    def test_xref_aponta_para_cada_objeto(self):
        """Cada posição da tabela xref cai exatamente no começo do objeto (senão o leitor reclama ou não abre)."""
        b = self.doc().bytes()
        inicio = int(re.search(rb"startxref\n(\d+)\n", b).group(1))
        self.assertTrue(b[inicio:].startswith(b"xref\n0 "))
        n = int(re.search(rb"xref\n0 (\d+)\n", b).group(1))
        posicoes = re.findall(rb"(\d{10}) 00000 n \n", b)
        self.assertEqual(len(posicoes), n - 1)
        for i, p in enumerate(posicoes, 1):
            self.assertTrue(b[int(p):].startswith(b"%d 0 obj\n" % i), f"objeto {i}")
        self.assertIn(b"/Size %d /Root 1 0 R" % n, b)

    def test_paginas_e_fontes(self):
        b = self.doc().bytes()
        self.assertIn(b"/Type /Pages /Kids [", b)
        self.assertIn(b"/Count 2", b)
        self.assertEqual(b.count(b"/Type /Page /Parent 2 0 R"), 2)
        self.assertIn(b"/BaseFont /Helvetica /Encoding /WinAnsiEncoding", b)
        self.assertIn(b"/BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding", b)
        self.assertIn(b"/MediaBox [0 0 595.28 841.89]", b, "A4")

    def test_titulo_nos_dados_do_arquivo(self):
        self.assertIn(b"/Title (Relat\xf3rio de teste) /Producer (GerencIA)", self.doc().bytes())

    def test_texto_de_cada_pagina(self):
        self.assertEqual(ler_pdf(self.doc().bytes()), [["Olá, Ana!"], ["Segunda página"]])

    @unittest.skipUnless(shutil.which("qpdf"), "precisa do qpdf")
    def test_qpdf_nao_acha_erro(self):
        arq = pasta_temp() + "/t.pdf"
        with open(arq, "wb") as f:
            f.write(self.doc().bytes())
        r = subprocess.run(["qpdf", "--check", arq], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    @unittest.skipUnless(shutil.which("pdftotext"), "precisa do pdftotext (poppler)")
    def test_um_leitor_de_verdade_le_os_acentos(self):
        arq = pasta_temp() + "/t.pdf"
        with open(arq, "wb") as f:
            f.write(self.doc().bytes())
        r = subprocess.run(["pdftotext", arq, "-"], capture_output=True)
        self.assertIn("Olá, Ana!", r.stdout.decode("utf-8"))
        self.assertIn("Segunda página", r.stdout.decode("utf-8"))


class TestTexto(unittest.TestCase):
    def test_acentos_em_winansi(self):
        d = pdf.Documento()
        d.texto(0, 0, "Patrimônio · Mãe · ação · R$ 1.000,00")
        self.assertEqual(ler_pdf(d.bytes())[0], ["Patrimônio · Mãe · ação · R$ 1.000,00"])
        self.assertIn("Patrim\xf4nio \xb7 M\xe3e", conteudo(d))

    def test_parenteses_e_barra_com_escape(self):
        d = pdf.Documento()
        d.texto(0, 0, r"LCI (ação) \ fim")
        self.assertIn(r"(LCI \(a", conteudo(d))
        self.assertIn(r"\) \\ fim) Tj", conteudo(d))
        self.assertEqual(ler_pdf(d.bytes())[0], [r"LCI (ação) \ fim"])

    def test_o_que_nao_cabe_em_winansi_vira_interrogacao(self):
        d = pdf.Documento()
        d.texto(0, 0, "Casa 🏠")
        self.assertEqual(ler_pdf(d.bytes())[0], ["Casa ?"])

    def test_negrito_cor_e_posicao(self):
        d = pdf.Documento()
        d.texto(40, 100, "Ana", 12, True, (1, 0, 0))
        c = conteudo(d)
        self.assertIn("/F2 12.00 Tf 1.000 0.000 0.000 rg 40.00 741.89 Td (Ana) Tj", c, "y conta de cima: 841.89 - 100")
        d.texto(40, 100, "Beto")
        self.assertIn("/F1 10.00 Tf", conteudo(d))

    def test_alinhar_a_direita_e_no_centro(self):
        d = pdf.Documento()
        w = pdf.largura("Beto", 10)
        d.texto(100, 0, "Beto", alinhar="direita")
        d.texto(100, 0, "Beto", alinhar="centro")
        c = conteudo(d)
        self.assertIn(f"{100 - w:.2f} 841.89 Td (Beto)", c)
        self.assertIn(f"{100 - w / 2:.2f} 841.89 Td (Beto)", c)


class TestMedidas(unittest.TestCase):
    def test_largura_pelas_metricas_da_helvetica(self):
        self.assertAlmostEqual(pdf.largura("Hello", 10), (722 + 556 + 222 + 222 + 556) / 100)
        self.assertAlmostEqual(pdf.largura("Hello", 10, True), (722 + 556 + 278 + 278 + 611) / 100)
        self.assertEqual(pdf.largura("", 10), 0)

    def test_letra_acentuada_mede_como_sem_acento(self):
        self.assertEqual(pdf.largura("ação", 10), pdf.largura("acao", 10))
        self.assertEqual(pdf.largura("Ã", 10, True), pdf.largura("A", 10, True))

    def test_simbolos(self):
        self.assertAlmostEqual(pdf.largura("…", 10), 10)
        self.assertAlmostEqual(pdf.largura("·", 10), 2.78)
        self.assertAlmostEqual(pdf.largura("中", 10), 5.56, msg="o que não conhece mede como uma letra comum")

    def test_cortar(self):
        self.assertEqual(pdf.cortar("CDB Azul", 200, 10), "CDB Azul", "cabe: inteiro")
        t = pdf.cortar("CDB do Banco Azul com um nome bem comprido", 80, 10)
        self.assertTrue(t.endswith("…"))
        self.assertLessEqual(pdf.largura(t, 10), 80)
        self.assertNotIn(" …", t, "sem espaço antes do …")
        self.assertEqual(pdf.cortar(12345, 200, 10), "12345")

    def test_cortar_numa_largura_minima(self):
        self.assertEqual(pdf.cortar("Ana", 2, 10), "…")

    def test_quebrar(self):
        texto = "Valores de hoje estimados a partir do último valor informado e dos índices. Antes do imposto de renda."
        linhas = pdf.quebrar(texto, 150, 8)
        self.assertGreater(len(linhas), 1)
        self.assertEqual(" ".join(linhas), texto)
        for l in linhas:
            self.assertLessEqual(pdf.largura(l, 8), 150)

    def test_quebrar_respeita_as_linhas_do_texto(self):
        self.assertEqual(pdf.quebrar("Ana\nBeto", 500, 10), ["Ana", "Beto"])

    def test_palavra_maior_que_a_linha_fica_inteira(self):
        self.assertEqual(pdf.quebrar("Supercalifragilístico", 20, 10), ["Supercalifragilístico"])

    def test_cor(self):
        self.assertEqual(pdf.cor_rgb("#ff0000"), (1, 0, 0))
        self.assertEqual(pdf.cor_rgb("56AEFF"), (0x56 / 255, 0xAE / 255, 1))
        self.assertEqual(pdf.cor_rgb("#fff"), (0, 0, 0), "só #rrggbb")
        self.assertEqual(pdf.cor_rgb("#zzzzzz"), (0, 0, 0))
        self.assertEqual(pdf.cor_rgb(None), (0, 0, 0))


class TestFormas(unittest.TestCase):
    def test_linha(self):
        d = pdf.Documento()
        d.linha(40, 100, 200, 100, (0, 0, 1), 1.5)
        self.assertIn("0.000 0.000 1.000 RG 1.50 w 40.00 741.89 m 200.00 741.89 l S", conteudo(d))

    def test_retangulo_com_borda_fundo_ou_os_dois(self):
        d = pdf.Documento()
        d.retangulo(10, 20, 100, 50, borda=(0, 0, 0))
        d.retangulo(10, 20, 100, 50, fundo=(1, 1, 1))
        d.retangulo(10, 20, 100, 50, borda=(0, 0, 0), fundo=(1, 1, 1))
        linhas = conteudo(d).splitlines()
        self.assertEqual(linhas[0], "0.000 0.000 0.000 RG 0.60 w 10.00 771.89 100.00 50.00 re S")
        self.assertEqual(linhas[1], "1.000 1.000 1.000 rg 10.00 771.89 100.00 50.00 re f")
        self.assertTrue(linhas[2].endswith("re B"))

    def test_retangulo_arredondado(self):
        d = pdf.Documento()
        d.retangulo(10, 20, 100, 50, fundo=(1, 1, 1), raio=6)
        c = conteudo(d)
        self.assertEqual(c.count(" c "), 4, "um arco em cada canto")
        self.assertTrue(c.endswith(" h f"))
        self.assertIn("16.00 771.89 m", c, "começa depois do arco de baixo")

    def test_raio_maior_que_a_metade_vira_pilula(self):
        d = pdf.Documento()
        d.retangulo(0, 0, 100, 10, fundo=(0, 0, 0), raio=50)
        self.assertIn("5.00 831.89 m 95.00 831.89 l", conteudo(d), "o raio fica na metade da altura")


class TestPaginas(unittest.TestCase):
    def test_ir_para_uma_pagina_anterior(self):
        d = pdf.Documento()
        d.texto(0, 0, "Um")
        d.nova_pagina()
        d.texto(0, 0, "Dois")
        d.ir_para(0)
        d.texto(0, 0, "Pé da primeira")
        self.assertEqual(ler_pdf(d.bytes()), [["Um", "Pé da primeira"], ["Dois"]])

    def test_nova_pagina_desenha_na_nova(self):
        d = pdf.Documento()
        d.ir_para(0)
        d.nova_pagina()
        self.assertEqual(d.atual, 1)

    def test_medidas_da_pagina(self):
        d = pdf.Documento()
        self.assertEqual((d.largura_pagina, d.altura_pagina), pdf.A4)


if __name__ == "__main__":
    unittest.main()
