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
