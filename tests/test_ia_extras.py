"""1.79.0: o que o servidor junta para a IA (a Conversa, o WhatsApp e a ferramenta resumo do CorrerIA) além dos dados:
as dicas de economia (só com as dicas ligadas), as oportunidades de investimento (o Tesouro e, com a IA, as ofertas das
páginas dos bancos) e as assinaturas em promoção (só com elas ligadas). Sem buscar nada: só o que já foi conferido."""
import unittest
from unittest import mock

from tests.base import importar_servidor
S = importar_servidor()

DICA = {"id": "anual:netflix", "nome": "Netflix", "real": 61.5, "valor": 44.9, "preco_anual": 478.8}
TESOURO = {"id": "td:selic-2031", "nome": "Tesouro Selic 2031", "origem": "tesouro", "fonte": "Tesouro Direto", "familia": "selic", "indexador": "selic_mais", "taxa": 0.09,
           "isento": False, "vencimento": "2031-03-01"}
PROMO = {"nome": "HBO Max", "preco": 9.9, "meses": 3, "normal": 29.9, "ate": "2026-12-31"}


class Extras(unittest.TestCase):
    def dados(self, **aj):
        d = S.vazio()
        d["indices"] = {"cdi": 13.65, "selic": 13.75, "ipca": 4.5, "tr": 0.1}
        d["ajustes"].update(aj)
        return d

    def extras(self, d, oport=None, promos=None, dicas=None):
        with mock.patch.object(S, "dicas_que_valem", lambda d_: dicas if dicas is not None else [DICA]), \
             mock.patch.object(S, "oport_ler", lambda: oport if oport is not None else {"tesouro": {"titulos": [TESOURO]}}), \
             mock.patch.object(S, "promos_estado", lambda d_, disparar=True: {"ligado": True, "promocoes": promos if promos is not None else [PROMO]}), \
             mock.patch.object(S, "promos_on", lambda d_: d_["ajustes"].get("promos") is True):
            return S.chat_extras(d)

    def test_tudo_o_que_a_tela_mostra(self):
        t = self.extras(self.dados(promos=True))
        self.assertIn("Dicas de economia (pagar o plano anual", t)
        self.assertIn("- Netflix: uns R$ 61,50 por ano", t)
        self.assertIn("Oportunidades de investimento (o rendimento como o de um CDB, antes do IR;", t)
        self.assertRegex(t, r"- Tesouro Selic 2031 \(Tesouro Direto\): [\d,]+% do CDI, vence 2031-03-01")
        self.assertIn("Assinaturas em promoção nos aparelhos da casa:", t)
        self.assertIn("- HBO Max: R$ 9,90 por mês por 3 meses (depois R$ 29,90), até 2026-12-31", t)

    def test_cada_um_so_com_a_sua_opcao(self):
        t = self.extras(self.dados(dicas=False, promos=False))
        self.assertNotIn("Dicas", t)
        self.assertNotIn("promoção", t)
        self.assertIn("Tesouro Selic 2031", t, "as oportunidades do Tesouro não dependem da IA")
        self.assertEqual(self.extras(self.dados(), oport={}, dicas=[], promos=[]), "", "nada conferido: nada")

    def test_um_erro_numa_parte_nao_derruba_as_outras(self):
        with mock.patch.object(S.oportunidades, "todas", side_effect=RuntimeError("quebrou")):
            t = self.extras(self.dados(promos=True))
        self.assertIn("Netflix", t)
        self.assertIn("HBO Max", t)
        self.assertNotIn("Oportunidades", t)


if __name__ == "__main__":
    unittest.main()
