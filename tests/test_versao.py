"""A versão: igual no config.yaml, no server.py, no app.js e no topo do CHANGELOG.md; e o tools/versao.py, que grava
as três de uma vez."""
import os
import re
import shutil
import sys
import unittest

from tests.base import pasta_temp

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "tools"))
import versao  # noqa: E402


class TestIguais(unittest.TestCase):
    def test_os_tres_lugares_e_o_changelog(self):
        vs = versao.ler()
        self.assertEqual(len(set(vs.values())), 1, vs)
        v = vs[versao.LUGARES[0][0]]
        self.assertRegex(v, versao.VERSAO_RE)
        with open(os.path.join(RAIZ, "gerencia", "CHANGELOG.md"), encoding="utf-8") as f:
            topo = f.read()
        self.assertTrue(topo.startswith("# Mudanças\n"), "o CHANGELOG começa com # Mudanças, como nos outros apps")
        self.assertEqual(re.search(r"^## (\S+)", topo, re.M).group(1), v, "a primeira seção do CHANGELOG é a da versão")

    def test_o_servidor_responde_com_ela(self):
        import server  # o tests.base põe gerencia/app no caminho
        self.assertEqual(server.VERSAO, versao.ler()[versao.LUGARES[1][0]])


class TestFerramenta(unittest.TestCase):
    def copia(self):
        raiz = pasta_temp()
        for rel, _ in versao.LUGARES:
            os.makedirs(os.path.join(raiz, os.path.dirname(rel)), exist_ok=True)
            shutil.copy(os.path.join(RAIZ, rel), os.path.join(raiz, rel))
        return raiz

    def test_grava_nos_tres(self):
        raiz = self.copia()
        versao.gravar("9.8.7", raiz)
        self.assertEqual(set(versao.ler(raiz).values()), {"9.8.7"})
        with open(os.path.join(raiz, "gerencia", "app", "www", "app.js"), encoding="utf-8") as f:
            self.assertIn("const VERSAO = '9.8.7';", f.read())

    def test_versao_invalida_nao_grava(self):
        raiz = self.copia()
        antes = versao.ler(raiz)
        for ruim in ("1.2", "v1.2.3", "1.2.3-beta", ""):
            with self.subTest(ruim=ruim):
                with self.assertRaises(ValueError):
                    versao.gravar(ruim, raiz)
        self.assertEqual(versao.ler(raiz), antes)

    def test_patch_e_minor(self):
        self.assertEqual(versao.seguinte("1.49.0", "patch"), "1.49.1")
        self.assertEqual(versao.seguinte("1.49.3", "minor"), "1.50.0")
        self.assertEqual(versao.seguinte("1.9.9", "minor"), "1.10.0")


if __name__ == "__main__":
    unittest.main()
