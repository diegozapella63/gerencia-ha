"""O app.js é um arquivo só (um IIFE): duas funções com o mesmo nome não dão erro, a de baixo toma o lugar da de cima
em todo o arquivo. Aconteceu na 1.54 (o textoMeta das oportunidades apagou o do Próximo nível, em Editar banco)."""
import collections
import os
import re
import unittest

APP = os.path.join(os.path.dirname(__file__), "..", "gerencia", "app", "www", "app.js")


class TestNomes(unittest.TestCase):
    def test_nenhuma_funcao_ou_constante_com_o_mesmo_nome(self):
        with open(APP, encoding="utf-8") as f:
            texto = f.read()
        nomes = re.findall(r"^(?:async )?function\s+([A-Za-z_$][\w$]*)", texto, re.M)
        nomes += re.findall(r"^(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=", texto, re.M)
        repetidos = sorted(n for n, k in collections.Counter(nomes).items() if k > 1)
        self.assertEqual(repetidos, [])
        self.assertGreater(len(nomes), 500, "achou as funções do arquivo")


if __name__ == "__main__":
    unittest.main()
