"""PDF com senha (pdfsenha.py e as senhas no server.py): as faturas dos bancos vêm cifradas (AES de 256 bits, AES de 128,
RC4); com a senha de abrir ou a do dono, o PDF sai sem senha para a IA. A cifra AES feita à mão confere com os vetores
do FIPS-197 e do NIST. As faturas de teste são inventadas (tests/fixtures/pdf_senha, feitas com o qpdf)."""
import base64
import io
import os
import re
import shutil
import subprocess
import unittest
import zipfile
import zlib
from unittest import mock

from tests.base import importar_servidor, pasta_temp, Servidor
S = importar_servidor()
import pdfsenha as P  # noqa: E402  (o importar_servidor põe gerencia/app no caminho)

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "pdf_senha")
CIFRADAS = ["fatura-aes256.pdf", "fatura-aes128-objstm.pdf", "fatura-rc4-128.pdf", "fatura-rc4-40.pdf"]


def arq(nome):
    with open(os.path.join(FIX, nome), "rb") as f:
        return f.read()


def conteudo(pdf_bytes):
    """Todo o conteúdo das páginas (os fluxos descompactados), para achar os textos da fatura."""
    out = b""
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf_bytes, re.S):
        try:
            out += zlib.decompress(m.group(1))
        except zlib.error:
            out += m.group(1)
    return out


# ---------------------------------------------------------------------------------------------------------------
class TestCifras(unittest.TestCase):
    PT = bytes.fromhex("00112233445566778899aabbccddeeff")

    def test_aes_fips_197(self):
        for chave, esperado in ((bytes(range(16)), "69c4e0d86a7b0430d8cdb78070b4c55a"),
                                (bytes(range(24)), "dda97ca4864cdfe06eaf70a0ec0d7191"),
                                (bytes(range(32)), "8ea2b7ca516745bfeafc49904b496089")):
            a = P.AES(chave)
            self.assertEqual(a.cifrar_bloco(self.PT).hex(), esperado)
            self.assertEqual(a.decifrar_bloco(bytes.fromhex(esperado)), self.PT)

    def test_aes_cbc_nist(self):
        """NIST SP 800-38A, F.2.1 (CBC-AES128)."""
        chave = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
        iv = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
        claro = bytes.fromhex("6bc1bee22e409f96e93d7e117393172aae2d8a571e03ac9c9eb76fac45af8e51")
        cifrado = bytes.fromhex("7649abac8119b246cee98e9b12e9197d5086cb9b507219ee95db113a917678b2")
        self.assertEqual(P.AES(chave).cifrar_cbc(claro, iv), cifrado)
        self.assertEqual(P.AES(chave).decifrar_cbc(cifrado, iv), claro)

    def test_chave_de_tamanho_errado(self):
        with self.assertRaises(ValueError):
            P.AES(b"curta")

    def test_rc4(self):
        self.assertEqual(P.rc4(b"Key", b"Plaintext").hex(), "bbf316e8d940af0ad3")
        self.assertEqual(P.rc4(b"Wiki", b"pedia").hex(), "1021bf0420")

    def test_aes_do_pdf_tira_o_preenchimento(self):
        chave, iv = bytes(range(16)), bytes(16)
        cifrado = iv + P.AES(chave).cifrar_cbc(b"Mercado Bom" + bytes([5]) * 5, iv)
        self.assertEqual(P._aes_texto(chave, cifrado), b"Mercado Bom")
        self.assertEqual(P._aes_texto(chave, b"curto"), b"", "menos que o vetor e um bloco: nada")


class TestLeituraDoPdf(unittest.TestCase):
    def test_valores(self):
        v, _ = P._valor(b"<< /Type /Page /Kids [1 0 R 2 0 R] /N 3 /F 1.5 /T (a\\(b\\)c) /H <414243> /B true /X null /Nome#20Esp 1 >>", 0)
        self.assertEqual(v["Type"], "Page")
        self.assertEqual(v["Kids"], [(1, 0), (2, 0)])
        self.assertIsInstance(v["Kids"][0], P.Ref)
        self.assertEqual((v["N"], v["F"], v["T"], v["H"], v["B"], v["X"]), (3, 1.5, b"a(b)c", b"ABC", True, None))
        self.assertIn("Nome Esp", v)

    def test_texto_literal(self):
        self.assertEqual(P._texto_literal(b"(um (dois) \\101\\n\\\nfim)", 0)[0], b"um (dois) A\nfim")
        with self.assertRaises(P.PdfInvalido):
            P._texto_literal(b"(sem fim", 0)

    def test_trocar_textos(self):
        self.assertEqual(P._trocar_textos(b"<< /T (ab) /H <6364> /D << /X (e) >> >>", lambda t: t.upper()),
                         b"<< /T <4142> /H <4344> /D << /X <45> >> >>")

    def test_preditor_png(self):
        # duas linhas de 2 colunas com o filtro Up (2): a segunda soma a de cima
        self.assertEqual(P._png(bytes([2, 1, 2, 2, 1, 1]), 2), bytes([1, 2, 2, 3]))
        self.assertEqual(P._png(bytes([1, 1, 2]), 2), bytes([1, 3]), "Sub")

    def test_filtro_que_nao_entende(self):
        with self.assertRaises(P.PdfInvalido):
            P._decodificar({"Filter": P.Nome("DCTDecode")}, b"x")


class TestAbrir(unittest.TestCase):
    def test_tem_senha(self):
        for nome in CIFRADAS + ["fatura-so-dono.pdf"]:
            self.assertTrue(P.tem_senha(arq(nome)), nome)
        self.assertFalse(P.tem_senha(arq("fatura-azul.pdf")))
        self.assertFalse(P.tem_senha(b"\xff\xd8 uma imagem"))
        self.assertFalse(P.tem_senha(b"%PDF-1.4 quebrado"))

    def test_abre_com_a_senha_de_abrir_e_com_a_do_dono(self):
        for nome in CIFRADAS:
            for senha in ("12345", "dono789"):
                with self.subTest(nome=nome, senha=senha):
                    aberto = P.abrir(arq(nome), ["errada", senha])
                    self.assertFalse(P.tem_senha(aberto))
                    self.assertTrue(aberto.startswith(b"%PDF-1.7"))
                    c = conteudo(aberto)
                    self.assertIn(b"Mercado Bom", c)
                    self.assertIn(b"Total R$ 169,35", c)
                    self.assertIn(b"(P\xe1gina 2", c, "a segunda página, com acento")

    def test_senha_errada(self):
        for nome in CIFRADAS:
            with self.subTest(nome=nome), self.assertRaises(P.SenhaErrada):
                P.abrir(arq(nome), ["00000", "123456", None])

    def test_so_com_a_senha_do_dono_abre_sem_digitar(self):
        self.assertIn(b"Mercado Bom", conteudo(P.abrir(arq("fatura-so-dono.pdf"), [])))

    def test_sem_senha_volta_igual(self):
        b = arq("fatura-azul.pdf")
        self.assertIs(P.abrir(b, ["12345"]), b)

    def test_metadados_do_arquivo_decifrados(self):
        """O título (no /Info) também vem cifrado; sai legível (em hexadecimal, ou como estava dentro do object stream)."""
        self.assertIn(b"Fatura Banco Azul".hex().encode(), P.abrir(arq("fatura-aes256.pdf"), ["12345"]))
        self.assertIn(b"(Fatura Banco Azul)", P.abrir(arq("fatura-aes128-objstm.pdf"), ["12345"]))

    def test_arquivo_quebrado(self):
        with self.assertRaises(P.PdfInvalido):
            P.abrir(b"%PDF-1.4\n1 0 obj << /Encrypt 2 0 R >> endobj\ntrailer << /Encrypt 9 0 R >>\n%%EOF", ["x"])

    def test_cifra_que_nao_e_a_do_padrao(self):
        b = arq("fatura-rc4-40.pdf").replace(b"/Filter /Standard", b"/Filter /PubSec00")
        with self.assertRaises(P.PdfInvalido):
            P.abrir(b, ["12345"])

    def test_tipo_de_protecao_para_o_registro(self):
        self.assertEqual([P.protecao(arq(n)) for n in CIFRADAS],
                         ["Standard V5 R6 AESV3 256 bits", "Standard V4 R4 AESV2 128 bits", "Standard V2 R3 128 bits", "Standard V1 R2 40 bits"])
        self.assertEqual(P.protecao(b"lixo"), "não li a proteção (PdfInvalido)", "nunca levanta erro")
        self.assertTrue(P.protecao(arq("fatura-azul.pdf")).startswith("não li"))

    @unittest.skipUnless(shutil.which("qpdf"), "precisa do qpdf")
    def test_qpdf_nao_acha_erro_no_aberto(self):
        for nome in CIFRADAS:
            caminho = os.path.join(pasta_temp(), "aberto.pdf")
            with open(caminho, "wb") as f:
                f.write(P.abrir(arq(nome), ["12345"]))
            r = subprocess.run(["qpdf", "--check", caminho], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, nome + ": " + r.stdout + r.stderr)

    @unittest.skipUnless(shutil.which("pdftotext"), "precisa do pdftotext (poppler)")
    def test_um_leitor_de_verdade_le_o_aberto(self):
        caminho = os.path.join(pasta_temp(), "aberto.pdf")
        with open(caminho, "wb") as f:
            f.write(P.abrir(arq("fatura-aes256.pdf"), ["12345"]))
        txt = subprocess.run(["pdftotext", caminho, "-"], capture_output=True).stdout.decode()
        self.assertIn("Mercado Bom", txt)
        self.assertIn("Vencimento 10/12/2026", txt)



def montar(objs, trailer=lambda pos: b"/Root 1 0 R", antes=b""):
    """Um PDF pequeno com a tabela xref clássica: objs = {número: corpo}; trailer recebe as posições dos objetos."""
    out = bytearray(b"%PDF-1.4\n" + antes)
    pos = {}
    for n in sorted(objs):
        pos[n] = len(out)
        out += b"%d 0 obj\n" % n + objs[n] + b"\nendobj\n"
    x, tam = len(out), max(pos) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % tam
    for k in range(1, tam):
        out += (b"%010d 00000 n \n" % pos[k]) if k in pos else b"0000000000 00000 f \n"
    out += b"trailer\n<< /Size %d " % tam + trailer(pos) + b" >>\nstartxref\n%d\n%%%%EOF\n" % x
    return bytes(out), pos


class _SemCifra:
    """Uma cifra que não muda nada, para reescrever um PDF sem senha pelos mesmos caminhos."""
    metadados = True

    def decifrar(self, dados, num, gen, fluxo):
        return dados


class TestPdfFeitoDeQualquerJeito(unittest.TestCase):
    """Os PDFs dos bancos nem sempre seguem o padrão à risca: comentários, escapes raros, xref quebrada ou híbrida,
    fluxos sem o tamanho certo. O que dá para entender é lido; o resto é PdfInvalido, nunca outro erro."""

    def test_valores_raros(self):
        self.assertEqual(P._valor(b"% um comentario\n  7", 0)[0], 7, "comentário antes do valor")
        self.assertEqual(P._valor(b"<414>", 0)[0], b"A@", "hexadecimal com número ímpar de dígitos: completa com 0")
        self.assertEqual(P._texto_literal(b"(a\\\r\nb)", 0)[0], b"ab", "barra no fim da linha (\\r\\n) continua")
        self.assertEqual(P._texto_literal(b"(\\q)", 0)[0], b"q", "escape que não existe: fica a letra")
        with self.assertRaises(P.PdfInvalido):
            P._texto_literal(b"(a\\", 0)
        with self.assertRaises(P.PdfInvalido):
            P._valor(b"@", 0)

    def test_preditor_png_media_e_paeth(self):
        # linha 1 com Média (3), linha 2 com Paeth (4), 2 colunas
        self.assertEqual(P._png(bytes([3, 10, 20, 4, 1, 1]), 2), bytes([10, 25, 11, 26]))

    def test_fluxo_compactado_cortado(self):
        self.assertEqual(P._decodificar({"Filter": P.Nome("FlateDecode")}, zlib.compress(b"Mercado Bom")[:-4]), b"Mercado Bom",
                         "sem o fim (a soma de conferência), o que veio vale")

    def test_xref_quebrada(self):
        for xref in (b"xref\nlixo\ntrailer << >>\n", b"xref\n0 2\n0000000000 65535 f \nlixo\ntrailer << >>\n"):
            with self.subTest(xref=xref):
                d = b"%PDF-1.4\n" + xref
                with self.assertRaises(P.PdfInvalido):
                    P._Leitor(d + b"startxref\n9\n%%EOF")
        with self.assertRaises(P.PdfInvalido, msg="startxref no meio do nada"):
            P._Leitor(b"%PDF-1.4\n1 0 obj 5 endobj\nlixo\nstartxref\n29\n%%EOF")
        with self.assertRaises(P.PdfInvalido, msg="startxref num objeto que não é xref"):
            P._Leitor(b"%PDF-1.4\n1 0 obj 5 endobj\nstartxref\n9\n%%EOF")

    def test_xref_hibrida(self):
        """Tabela clássica com /XRefStm (PDFs 1.5 "híbridos"): os objetos do fluxo também entram."""
        fluxo = b"<< /Type /XRef /W [1 1 1] /Index [5 2] /Size 7 /Length 5 >>\nstream\n\x01\x00\x00\x01\x00\nendstream"
        d, _ = montar({1: b"<< /Type /Catalog >>", 3: fluxo}, trailer=lambda pos: b"/Root 1 0 R /XRefStm %d" % pos[3])
        lido = P._Leitor(d)
        self.assertEqual(lido.xref[5], ("n", 0, 0))
        self.assertNotIn(6, lido.xref, "a linha incompleta do fluxo fica de fora")
        self.assertEqual(lido.trailer["Root"], (1, 0))

    def test_so_com_fluxos_xref_e_sem_startxref(self):
        """Sem startxref nem trailer: procura os objetos e usa o dicionário do fluxo xref como trailer."""
        d = (b"%PDF-1.5\n1 0 obj << /Type /Catalog >> endobj\n3 0 obj @ endobj\n"
             b"2 0 obj << /Type /XRef /Root 1 0 R /W [1 1 1] /Size 1 /Length 0 >>\nstream\n\nendstream\nendobj\n"
             b"trailer << /Quebrado @ >>\n%%EOF")
        lido = P._Leitor(d)
        self.assertEqual(lido.trailer["Root"], (1, 0))
        self.assertFalse(P.tem_senha(d))

    def test_fluxos(self):
        d, pos = montar({
            1: b"<< /Type /Catalog >>",
            2: b"3",
            3: b"<< /Length 2 0 R >>\nstream\r\nabc\r\nendstream",
            4: b"<< /Length 9 0 R >>\nstream\nabcd\n\nendstream",
            5: b"<< /Length 99 >>\nstream\nxyz\nendstream",
        })
        lido = P._Leitor(d)
        self.assertEqual(lido._objeto_em(pos[3])[3], b"abc", "o tamanho em outro objeto, depois de \\r\\n")
        self.assertEqual(lido._objeto_em(pos[4])[3], b"abcd", "tamanho que não existe: até o endstream")
        self.assertEqual(lido._objeto_em(pos[5])[3], b"xyz", "tamanho errado: até o endstream")
        with self.assertRaises(P.PdfInvalido, msg="no meio de um objeto"):
            lido._objeto_em(pos[3] + 1)
        with self.assertRaises(P.PdfInvalido):
            lido.valor(P.Ref((99, 0)))
        self.assertEqual(lido.valor(5), 5, "um valor direto volta igual")
        lido.xref[8] = ("n", pos[2] + 1, 0)
        self.assertIsNone(lido._inteiro(P.Ref((8, 0))), "a posição não é de um objeto")
        self.assertIsNone(lido._inteiro(P.Ref((1, 0))), "não é um número")
        with self.assertRaises(P.PdfInvalido, msg="sem xref nem trailer, e o único objeto sem fim"):
            P._Leitor(b"%PDF-1.4\n1 0 obj << /Length 3 >>\nstream\nabc")
        sem_fim = montar({1: b"<< /Type /Catalog >>", 2: b"<< /Length 3 >>\nstream\nabc"})
        with self.assertRaises(P.PdfInvalido):
            P._Leitor(sem_fim[0])._objeto_em(sem_fim[1][2])

    def test_reescrever_pula_o_que_nao_entende_e_fica_com_a_versao_nova(self):
        objstm = b"<< /Type /ObjStm /N 2 /First 8 /Length 19 >>\nstream\n5 0 6 7 (velho)(seis)\nendstream"
        d, pos = montar({1: b"<< /Type /Catalog /Pages 2 0 R >>", 2: b"<< /Type /Pages /Kids [] /Count 0 >>", 4: objstm, 5: b"(novo)"})
        lido = P._Leitor(d)
        lido.xref[6] = ("c", 4, 1)
        lido.xref[7] = ("n", pos[5] + 1, 0)  # aponta para o meio de um objeto
        novo = P._reescrever(lido, _SemCifra(), None)
        self.assertIn(b"6 0 obj\n(seis)", novo, "o objeto guardado no ObjStm vira um objeto comum")
        self.assertIn(b"5 0 obj\n<6e6f766f>", novo, "o 5 de fora é o mais novo")
        self.assertNotIn(b"velho", novo)
        self.assertNotIn(b"7 0 obj", novo)
        self.assertEqual(P._Leitor(novo).trailer["Root"], (1, 0))

    def test_trocar_textos_sem_mexer_nos_comentarios(self):
        self.assertEqual(P._trocar_textos(b"% (ab)\n(ab)", lambda t: t.upper()), b"% (ab)\n<4142>")

    def test_serializar(self):
        self.assertEqual(P._serializar({"A": True, "B": False, "C": None, "D": {"E": 1}, "F": [P.Nome("G"), b"h"]}),
                         b"<</A true /B false /C null /D <</E 1>> /F [/G <68>]>>")

    def test_length_que_nao_existe(self):
        self.assertEqual(P._sem_length(b"<< /Type /X >>", 5), b"<< /Type /X /Length 5>>")
        self.assertEqual(P._sem_length(b"lixo", 5), b"lixo")
        self.assertEqual(P._sem_length(b"<< /Length 9 0 R /Filter /FlateDecode >>", 5), b"<< /Length 5 /Filter /FlateDecode >>")


class TestCifrasRaras(unittest.TestCase):
    def test_r5_e_so_o_sha256(self):
        import hashlib
        self.assertEqual(P._hash_r6(b"12345", b"salsalsa", b"", 5), hashlib.sha256(b"12345salsalsa").digest())

    def test_identity_nao_decifra(self):
        c = P._Cifra({"Filter": "Standard", "V": 4, "R": 4, "CF": {"StdCF": {"CFM": "AESV2"}}, "StmF": "StdCF", "StrF": "Identity"}, b"")
        self.assertEqual((c.metodo_fluxo, c.metodo_texto), ("aes", None))
        self.assertEqual(c.decifrar(b"Mercado Bom", 3, 0, False), b"Mercado Bom")
        c2 = P._Cifra({"Filter": "Standard", "V": 4, "R": 4, "CF": {"X": {"CFM": "None"}}, "StmF": "X"}, b"")
        self.assertEqual((c2.metodo_fluxo, c2.metodo_texto), (None, None), "StrF faltando é Identity")

    @unittest.skipUnless(shutil.which("qpdf"), "precisa do qpdf")
    def test_aes128_com_metadados_sem_cifra(self):
        """--cleartext-metadata (/EncryptMetadata false): a chave muda e o fluxo de metadados fica como está."""
        pasta = pasta_temp()
        saida = os.path.join(pasta, "fatura.pdf")
        r = subprocess.run(["qpdf", "--encrypt", "12345", "dono789", "128", "--use-aes=y", "--cleartext-metadata", "--",
                            os.path.join(FIX, "fatura-azul.pdf"), saida], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(saida, "rb") as f:
            dados = f.read()
        self.assertIn(b"/EncryptMetadata false", dados)
        aberto = P.abrir(dados, ["12345"])
        self.assertFalse(P.tem_senha(aberto))
        self.assertIn(b"Mercado Bom", conteudo(aberto))
        with self.assertRaises(P.SenhaErrada):
            P.abrir(dados, ["errada"])


# ---------------------------------------------------------------------------------------------------------------
class TestSenhasNoServidor(unittest.TestCase):
    def setUp(self):
        if os.path.exists(S.SENHAS_ARQ):
            os.remove(S.SENHAS_ARQ)

    def test_cadastrar_listar_apagar(self):
        self.assertEqual(S.senhas_listar(), [])
        l = S.senha_nova("CPF da Ana", " 12345 ")
        self.assertEqual([(x["nome"], x["fim"]) for x in l], [("CPF da Ana", "••••45")], "a tela só vê o fim")
        self.assertNotIn("senha", l[0])
        self.assertEqual(S.senhas_pdf()[0]["senha"], "12345", "guardada sem os espaços")
        l = S.senha_nova("", "987")
        self.assertEqual([(x["nome"], x["fim"]) for x in l], [("CPF da Ana", "••••45"), ("Senha 2", "••••")], "curta: nada à mostra")
        l = S.senha_nova("CPF do Beto", "12345")
        self.assertEqual(len(l), 2, "a mesma senha só troca o nome")
        self.assertEqual(l[0]["nome"], "CPF do Beto")
        l = S.senha_apagar(l[1]["id"])
        self.assertEqual([x["nome"] for x in l], ["CPF do Beto"])

    def test_senha_vazia_e_limite(self):
        with self.assertRaisesRegex(ValueError, "Digite a senha"):
            S.senha_nova("Nada", "  ")
        for k in range(20):
            S.senha_nova("", f"senha{k}")
        with self.assertRaisesRegex(ValueError, "20 senhas"):
            S.senha_nova("", "mais uma")

    def test_arquivo_estragado(self):
        S.gravar_arquivo(S.SENHAS_ARQ, "não é json")
        self.assertEqual(S.senhas_listar(), [])
        S.gravar_arquivo(S.SENHAS_ARQ, '{"senhas": [{"id": "a", "senha": 5}, "x", {"id": "b", "senha": "ok"}]}')
        self.assertEqual([x["id"] for x in S.senhas_listar()], ["b"])

    def test_abre_com_as_cadastradas(self):
        S.senha_nova("Outra", "000")
        S.senha_nova("CPF da Ana", "12345")
        self.assertIn(b"Mercado Bom", conteudo(S.abrir_pdf(arq("fatura-aes256.pdf"))))
        b = arq("fatura-azul.pdf")
        self.assertIs(S.abrir_pdf(b), b, "sem senha: nem tenta")

    def test_pede_a_senha(self):
        with self.assertRaises(S.ErroSenhaPdf) as e:
            S.abrir_pdf(arq("fatura-aes256.pdf"))
        self.assertEqual((str(e.exception), e.exception.codigo), ("Este PDF tem senha.", "senha_pdf"))
        S.senha_nova("Outra", "000")
        with self.assertRaisesRegex(S.ErroSenhaPdf, "Nenhuma das senhas cadastradas abre este PDF."):
            S.abrir_pdf(arq("fatura-aes256.pdf"))
        with self.assertRaisesRegex(S.ErroSenhaPdf, "Senha errada para este PDF."):
            S.abrir_pdf(arq("fatura-aes256.pdf"), "111")

    def test_digitada_e_guardada_para_as_proximas(self):
        S.abrir_pdf(arq("fatura-aes256.pdf"), "12345", guardar=True, nome_arquivo="fatura-novembro.pdf")
        self.assertEqual([(x["nome"], x["fim"]) for x in S.senhas_listar()], [("Da fatura fatura-novembro", "••••45")])
        S.abrir_pdf(arq("fatura-rc4-40.pdf"))  # agora abre sozinha
        S.abrir_pdf(arq("fatura-rc4-40.pdf"), "dono789", guardar=False)
        self.assertEqual(len(S.senhas_listar()), 1, "sem guardar: não guarda")

    def test_nao_guarda_a_digitada_que_nao_abriu(self):
        S.senha_nova("CPF da Ana", "12345")
        S.abrir_pdf(arq("fatura-aes256.pdf"), "999", guardar=True)  # abriu com a cadastrada
        self.assertEqual(len(S.senhas_listar()), 1)

    def test_pdf_que_nao_entende(self):
        b = arq("fatura-rc4-40.pdf").replace(b"/Filter /Standard", b"/Filter /PubSec00")
        with self.assertRaisesRegex(ValueError, "Não consegui abrir este PDF com senha. Tente um print da fatura."):
            S.abrir_pdf(b, "12345")

    def test_registro_so_com_o_tipo_de_protecao(self):
        registro = []
        with mock.patch.object(S, "log", lambda *a: registro.append(" ".join(map(str, a)))):
            with self.assertRaises(S.ErroSenhaPdf):
                S.abrir_pdf(arq("fatura-aes256.pdf"))
            self.assertEqual(registro, [], "sem senha nenhuma: só pede, nada no registro")
            S.senha_nova("Outra", "00077")
            with self.assertRaises(S.ErroSenhaPdf):
                S.abrir_pdf(arq("fatura-aes256.pdf"), "11166")
            with self.assertRaises(ValueError):
                S.abrir_pdf(arq("fatura-rc4-40.pdf").replace(b"/Filter /Standard", b"/Filter /PubSec00"), "12345")
        self.assertEqual(registro[0], "PDF com senha: nenhuma senha serviu · Standard V5 R6 AESV3 256 bits")
        self.assertTrue(registro[1].startswith("PDF com senha: não consegui abrir · PubSec00 V1 R2 40 bits"), registro[1])
        for senha in ("00077", "11166", "12345", "Mercado"):
            self.assertNotIn(senha, " ".join(registro), "nem a senha nem o conteúdo vão para o registro")

    def test_leitura_por_ia_com_pdf_com_senha(self):
        corpo = {"modo": "auto", "anexo": {"b64": "data:application/pdf;base64," + base64.b64encode(arq("fatura-aes256.pdf")).decode()}}
        enviado = []
        with mock.patch.object(S.time, "sleep"), mock.patch.object(S, "IA_MOCK", True), \
                mock.patch.object(S, "registrar_uso", side_effect=lambda *a, **k: enviado.append(a)):
            with self.assertRaises(S.ErroSenhaPdf):
                S.ia_ler(dict(corpo))
            r = S.ia_ler(dict(corpo, senha="12345", guardar_senha=True, nome_arquivo="azul.pdf"))
        self.assertEqual(r["entidade"], "ai_task.simulada")
        self.assertEqual(S.senhas_listar()[0]["nome"], "Da fatura azul")

    def test_pdf_aberto_e_o_que_vai_para_a_ia(self):
        S.senha_nova("CPF da Ana", "12345")
        visto = {}
        real = S.abrir_pdf

        def espia(*a, **k):
            visto["aberto"] = real(*a, **k)
            return visto["aberto"]
        corpo = {"modo": "auto", "anexo": {"b64": base64.b64encode(arq("fatura-rc4-128.pdf")).decode()}}
        with mock.patch.object(S.time, "sleep"), mock.patch.object(S, "IA_MOCK", True), mock.patch.object(S, "abrir_pdf", side_effect=espia):
            S.ia_ler(corpo)
        self.assertFalse(P.tem_senha(visto["aberto"]))


class TestRotas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Servidor()

    @classmethod
    def tearDownClass(cls):
        cls.s.parar()

    def test_senhas_pela_api(self):
        for x in self.s.get("/api/senhas")[2]["senhas"]:  # começa sem nenhuma (os testes dividem o servidor)
            self.s.post("/api/senhas/apagar", {"id": x["id"]})
        st, _, r = self.s.post("/api/senhas", {"nome": "CPF da Ana", "senha": "12345"})
        self.assertEqual((st, [x["fim"] for x in r["senhas"]]), (200, ["••••45"]))
        st, _, r = self.s.get("/api/senhas")
        self.assertEqual(r["senhas"][0]["nome"], "CPF da Ana")
        self.assertNotIn("12345", str(r), "a senha nunca vai para a tela")
        st, _, r = self.s.post("/api/senhas", {"nome": "x", "senha": ""})
        self.assertEqual((st, r["erro"]), (400, "Digite a senha."))
        st, _, r = self.s.post("/api/senhas/apagar", {"id": self.s.get("/api/senhas")[2]["senhas"][0]["id"]})
        self.assertEqual(r["senhas"], [])

    def test_fora_das_exportacoes(self):
        self.s.post("/api/senhas", {"nome": "CPF", "senha": "senha-secreta-77"})
        for rota in ("/api/export/json", "/api/export/zip", "/api/state"):
            st, _, corpo = self.s.get(rota, cru=True)
            self.assertEqual(st, 200, rota)
            self.assertNotIn(b"senha-secreta-77", corpo, rota)
            if rota.endswith("zip"):
                with zipfile.ZipFile(io.BytesIO(corpo)) as z:
                    self.assertFalse(any(b"senha-secreta-77" in z.read(n) for n in z.namelist()), "nem dentro do zip")

    def test_ler_pdf_com_senha_pede_a_senha(self):
        b64 = base64.b64encode(arq("fatura-aes256.pdf")).decode()
        st, _, r = self.s.post("/api/ia/ler", {"modo": "auto", "anexo": {"b64": b64}})
        self.assertEqual((st, r.get("codigo")), (400, "senha_pdf"))
        st, _, r = self.s.post("/api/ia/ler", {"modo": "auto", "anexo": {"b64": b64}, "senha": "12345"})
        self.assertEqual(st, 200)


if __name__ == "__main__":
    unittest.main()
