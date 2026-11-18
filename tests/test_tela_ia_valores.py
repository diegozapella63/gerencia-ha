"""Os valores da IA são os da tela, conferidos no app.js de verdade (1.78.0): os mesmos dados abertos na tela e passados
para a Conversa e as ferramentas do CorrerIA dão o mesmo valor de hoje de cada investimento, o mesmo patrimônio do
placar do Agora (com Somar os bens ligado e desligado, e com Corrigir valores pelo rendimento ligado e desligado) e o
mesmo caixa (o saldo de hoje e o que entrou e saiu no mês). O test_ia_valores.py confere a parte da IA sozinha.

Dados inventados (Ana, Beto, Banco Azul); o relógio da tela parado em 02/11/2026."""
import json
import unittest

from tests.tela_base import Tela, BANCOS, HOJE
from tests.test_ia_valores import CASA, INDICES, dados as dados_ia
import calc  # noqa: E402  (o tela_base já pôs o app no caminho)
import chat  # noqa: E402
import ferramentas as F  # noqa: E402

# a conta do placar do Agora (telaInicio, no app.js), sem arredondar
PATRIMONIO_DA_TELA = """(() => {
  const B = T.bensOn() ? T.S.bens : null;
  const meus = T.porEscopo('meu'), tm = T.totais(meus.filter(i => i.tipo !== 'bens'));
  const bensT = (B ? B.hoje : 0) + meus.filter(i => i.tipo === 'bens').reduce((a, i) => a + T.valorHoje(i), 0);
  const terc = T.totais(T.porEscopo('terc')).total;
  const rot = document.querySelector('#app .placar-num')?.getAttribute('aria-label') || '';
  return { patrimonio: tm.total + bensT, investido: tm.total, bens: bensT, de_outras_pessoas: terc, rende_por_mes: tm.mes, rotulo: rot };
})()"""


def dados(**ajustes):
    d = dados_ia(**ajustes)
    d["indices"] = dict(INDICES)
    d["bancos"] = json.loads(json.dumps(BANCOS))
    for i in d["investimentos"]:
        if i.get("banco"):
            i["banco"] = "b-azul"
    return d


class ValoresDaIA(Tela):
    def abrir_com(self, d, bens=None):
        self.abrir(json.loads(json.dumps(d)), bens=bens)
        return self.js("T.S.d")  # como a tela guardou (normalizado)

    def valores_da_tela(self):
        return dict(self.js("T.S.d.investimentos.map(i => [i.id, T.valorHoje(i)])"))

    def patrimonio_da_ia(self, d, bens):
        t, _ = F.chamar("investimentos", {}, d, HOJE, bens=bens)
        return json.loads(t)

    def conferir(self, d, bens=None):
        visto = self.abrir_com(d, bens)
        tela = self.valores_da_tela()
        ia = self.patrimonio_da_ia(visto, bens)
        for i in ia["investimentos"]:
            self.assertAlmostEqual(i["valor_hoje"], tela[i["id"]], delta=0.006, msg=f"{i['nome']}: o valor de hoje da IA é o da tela")
        p = self.js(PATRIMONIO_DA_TELA)
        for k in ("patrimonio", "investido", "bens", "de_outras_pessoas", "rende_por_mes"):
            self.assertAlmostEqual(ia["patrimonio"][k], p[k], delta=0.006, msg=f"{k}: o da IA é o da tela")
        # o placar mostra o mesmo número, em reais inteiros, e a Conversa recebe o mesmo
        self.assertEqual(p["rotulo"].replace("\xa0", " "), "Patrimônio de R$ " + f"{round(p['patrimonio']):,}".replace(",", "."))
        linha = next(l for l in chat.resumo(visto, HOJE, bens).splitlines() if l.startswith("Patrimônio"))
        self.assertIn(f"{chat._brl(ia['patrimonio']['patrimonio'])} = investido", linha)
        return ia, p

    def test_corrigido_com_os_bens_da_casa(self):
        ia, p = self.conferir(dados(corrigir=True, bens=True), CASA)
        self.assertAlmostEqual(p["bens"] - CASA["hoje"], sum(i["valor_hoje"] for i in ia["investimentos"] if i["tipo"] == "bens"), delta=0.02)

    def test_somar_os_bens_desligado(self):
        ia, p = self.conferir(dados(corrigir=True, bens=False), CASA)
        self.assertNotIn("bens_da_casa", ia["patrimonio"])

    def test_sem_corrigir(self):
        ia, _ = self.conferir(dados(corrigir=False, bens=True), CASA)
        self.assertEqual({i["id"]: i["valor_hoje"] for i in ia["investimentos"]}["a"], 10000)

    def test_inventaria_sem_resposta(self):
        self.conferir(dados(corrigir=True, bens=True), {"ok": False, "motivo": "O InventarIA não respondeu."})

    def test_o_caixa_da_ia_e_o_da_tela(self):
        """O saldo de hoje e o que entrou e saiu no mês (o placar do Caixa) são os da Conversa."""
        d = dados(corrigir=True)
        d["lancamentos"] = [
            {"id": "l1", "tipo": "receita", "descricao": "Salário", "valor": 8000, "data": "2026-11-01", "pago": True, "conta": "k-verde", "categoria": "c-salario"},
            {"id": "l2", "tipo": "despesa", "descricao": "Mercado", "valor": 412.35, "data": "2026-11-01", "pago": True, "conta": "k-verde", "categoria": "c-mercado"},
            {"id": "l3", "tipo": "despesa", "descricao": "Aluguel", "valor": 2500, "data": "2026-11-10", "pago": False, "conta": "k-verde", "categoria": "c-moradia"},
            {"id": "l4", "tipo": "despesa", "descricao": "Luz", "valor": 230.5, "data": "2026-10-28", "pago": False, "conta": "k-verde", "categoria": "c-contas"},
            {"id": "l5", "tipo": "despesa", "descricao": "Farmácia", "valor": 89.9, "data": "2026-10-20", "pago": True, "conta": "k-verde", "categoria": "c-saude"},
            {"id": "l6", "tipo": "receita", "descricao": "Freela", "valor": 1200, "data": "2026-11-20", "pago": False, "conta": "k-verde", "categoria": "c-freelance"},
            {"id": "l7", "tipo": "despesa", "descricao": "Ajuste", "valor": 50, "data": "2026-10-15", "pago": True, "ajuste": True, "conta": "k-verde"},
        ]
        visto = self.abrir_com(d)
        tela = self.js("(() => { const r = T.resumoMes(T.ymHoje()); return { saldo: T.saldoCaixa(), entrou: r.entrou, saiu: r.saiu, aEntrar: r.aEntrar, aSair: r.aSair }; })()")
        cx = calc.caixa(visto, HOJE)
        self.assertAlmostEqual(cx["saldo"], tela["saldo"], delta=0.006)
        self.assertAlmostEqual(cx["entrou_mes"], tela["entrou"], delta=0.006)
        self.assertAlmostEqual(cx["saiu_mes"], tela["saiu"], delta=0.006)
        self.assertAlmostEqual(cx["a_receber_mes"], tela["aEntrar"], delta=0.006)
        self.assertAlmostEqual(cx["a_pagar_mes"], tela["aSair"], delta=0.006)
        texto = chat.resumo(visto, HOJE)
        self.assertIn(f"Caixa: saldo de hoje {chat._brl(tela['saldo'])}. Neste mês: entrou {chat._brl(tela['entrou'])}, saiu {chat._brl(tela['saiu'])}", texto)


if __name__ == "__main__":
    unittest.main()
