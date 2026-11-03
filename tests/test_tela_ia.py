"""A tela da leitura por IA, da câmera (Digitalizar com IA) e do Falar, testada como quem usa: toca, escolhe, confere.

Roda o app.js de verdade num Chromium (base em tests/tela_base.py: prévia, relógio parado em 02/11/2026 10:00, 390 px).
Para ser rápido e exato, cada teste troca por falsos (em setUp) o que depende do Home Assistant e do aparelho:
  - a IA (api.iaLer): guarda o que foi enviado em window.__ia.pedidos e responde window.__ia.resp (ou o erro __ia.erro);
    com __ia.segura, só responde quando o teste chama soltar_ia(), para ver a tela "lendo";
  - a fala para texto (api.vozTexto), do mesmo jeito, em window.__voz;
  - o microfone (a classe Gravador): quantos segundos e quantas amostras "gravou", em window.__grav;
  - a câmera (navigator.mediaDevices.getUserMedia): um vídeo de um canvas, sem permissão ou com erro, em window.__cam;
  - guardar imagem (api.foto), em window.__fotos.
As funções puras da IA (prepararRevisaoCaixa, aplicarIACaixa, aplicarIAInvest, iaPago, difSaldo, donoDe...) já estão
em tests/test_tela.py; aqui fica o que aparece na tela e o que é gravado depois de tocar nos botões.

Um teste marcado com @unittest.expectedFailure e "BUG:" descreve o comportamento certo (DOCS.md, AGENTS.md) que o app
ainda não tem. Dados sempre inventados (Ana, Beto, Carla, Banco Azul...).
"""
import os
import unittest

from tests.base import RAIZ
from tests.tela_base import Tela, base, BANCOS, INDEX, sync_playwright

JPG = os.path.join(RAIZ, "tests", "e2e", "fixtures", "print.jpg")
PDF = os.path.join(RAIZ, "tests", "e2e", "fixtures", "recibo-teste.pdf")

IA_DESLIGADA = {"corrigir": True, "ia": False}

# investimentos sem rendimento (o valor de hoje é o valor informado: as contas da tela ficam exatas)
CDB = {"id": "cdb-azul", "nome": "CDB Azul", "banco": "b-azul", "valor": 1000, "indexador": "parado", "tipo": "cdb", "data_valor": "2026-11-01", "titular": "meu"}
RESERVA = {"id": "res-verde", "nome": "Reserva Verde", "banco": "b-verde", "valor": 2000, "indexador": "parado", "tipo": "caixinha", "data_valor": "2026-11-01", "titular": "meu"}
CARLA = {"id": "poup-carla", "nome": "Poupança da Carla", "banco": "b-verde", "valor": 500, "indexador": "parado", "tipo": "poupanca",
         "data_valor": "2026-10-01", "titular": "terceiros", "terceiro": "Carla"}
BETO = {"id": "cdb-beto", "nome": "CDB do Beto", "banco": "b-azul", "valor": 700, "indexador": "parado", "tipo": "cdb",
        "data_valor": "2026-10-01", "titular": "terceiros", "terceiro": "Beto"}


def gasto(descricao, valor, **kw):
    """Um lançamento como a IA devolve."""
    it = {"tipo": "despesa", "descricao": descricao, "valor": valor, "data": "2026-11-01", "categoria": "c-mercado",
          "parcela_atual": 0, "parcelas_total": 0, "cartao": False, "banco": "", "situacao": "feito", "confianca": "alta"}
    it.update(kw)
    return it


def recebido(descricao, valor, **kw):
    return gasto(descricao, valor, **dict({"tipo": "receita", "categoria": "c-reembolso"}, **kw))


def inv(nome, valor, **kw):
    """Um investimento como a IA devolve."""
    it = {"nome": nome, "banco": "", "tipo": "cdb", "valor": valor, "aplicado": 0, "data_valor": "2026-11-02", "indexador": "cdi_pct",
          "taxa": 100, "vencimento": "", "liquidez": "vencimento", "existente": "", "confianca": "alta"}
    it.update(kw)
    return it


FEIRA = gasto("Feira do bairro", 45, data="2026-11-01", categoria="c-mercado")
PIX = recebido("Pix do Beto", 150, data="2026-11-02", categoria="c-reembolso")

# um recibo de pagamento inventado: bruto 5.000, INSS 11%, IR 6% e um plano de saúde de 250 (líquido 3.900)
HOLERITE = {"data": "2026-11-05", "creditos": [{"descricao": "Salário base", "valor": 5000}],
            "debitos": [{"descricao": "INSS", "valor": 550, "tipo": "imposto"}, {"descricao": "Imposto de renda", "valor": 300, "tipo": "imposto"},
                        {"descricao": "Plano de saúde", "valor": 250, "tipo": "saude"}],
            "total_creditos": 5000, "total_debitos": 1100, "liquido": 3900}

_FALSOS = r"""async () => {
  const T = window.GERENCIA_TESTE;
  if (!window.__apiOrig) window.__apiOrig = Object.assign({}, T.api);
  Object.assign(T.api, window.__apiOrig);
  (window.__camIv || []).forEach(clearInterval); window.__camIv = [];
  // responde no próximo giro ou, com segura, quando o teste chamar soltar()
  const responder = (q, fim) => new Promise((ok, erro) => {
    const ir = () => { try { ok(fim()); } catch (e) { erro(e); } };
    if (q.segura) q.soltar = ir; else setTimeout(ir, 0);
  });
  const ia = window.__ia = { pedidos: [], resp: { lancamentos: [], investimentos: [] }, erro: '', segura: false, soltar: null };
  T.api.iaLer = c => { ia.pedidos.push(JSON.parse(JSON.stringify(c))); return responder(ia, () => { if (ia.erro) throw new Error(ia.erro); return JSON.parse(JSON.stringify(ia.resp)); }); };
  const voz = window.__voz = { pedidos: [], texto: 'gastei 45 no mercado hoje', erro: '', segura: false, soltar: null };
  T.api.vozTexto = pcm => { voz.pedidos.push(pcm.length); return responder(voz, () => { if (voz.erro) throw new Error(voz.erro); return { texto: voz.texto, nome: 'Home Assistant Cloud' }; }); };
  const fotos = window.__fotos = [];
  T.api.foto = async jpg => { fotos.push(jpg); return { arquivo: 'foto-' + fotos.length + '.jpg' }; };
  const grav = window.__grav = { seg: 3, n: 3 * 16000, iniciou: 0, parou: 0, cancelou: 0 };
  T.Gravador = class { constructor(f) { this.f = f; } async start() { grav.iniciou++; } segundos() { return grav.seg; }
    stop() { grav.parou++; return new Int16Array(grav.n); } cancel() { grav.cancelou++; } };
  const cam = window.__cam = { modo: 'ok', luz: false, luzes: [], pedidos: [], trilhas: [] };
  if (navigator.mediaDevices) navigator.mediaDevices.getUserMedia = async c => {
    cam.pedidos.push(JSON.parse(JSON.stringify(c)));
    const erro = n => Object.assign(new Error(n), { name: n });
    if (!c.video) throw erro('NotFoundError');
    if (cam.modo !== 'ok') throw erro(cam.modo);
    const cv = document.createElement('canvas'); cv.width = 64; cv.height = 48;
    const g = cv.getContext('2d'); g.fillStyle = '#2a6'; g.fillRect(0, 0, 64, 48);
    const s = cv.captureStream(25), tr = s.getVideoTracks()[0];
    window.__camIv.push(setInterval(() => { g.fillStyle = '#' + (0x100000 + Math.floor(Math.random() * 0xefffff)).toString(16); g.fillRect(0, 0, 8, 8); }, 40));
    if (cam.luz) { tr.getCapabilities = () => ({ torch: true }); tr.applyConstraints = async k => { cam.luzes.push(k.advanced[0].torch); }; }
    cam.trilhas.push(tr);
    return s;
  };
  T.S.voz = { pronta: true, nome: 'Home Assistant Cloud', selecionada: '', opcoes: [
    { id: 'stt.home_assistant_cloud', nome: 'Home Assistant Cloud', idioma: 'pt-BR', preferido: true },
    { id: 'stt.google_ai_stt', nome: 'Google AI STT', idioma: 'pt-BR', preferido: false }] };
  T.S.usoSel = null;
  return true;
}"""

# uma imagem (feita num canvas) ou um PDF, colados (Ctrl+V) ou soltos (arrastar) na janela de cima
_SOLTAR = r"""async (a) => {
  let f;
  if (a.tipo === 'pdf') f = new File(['%PDF-1.4\n% fatura inventada\n%%EOF\n'], a.nome, { type: 'application/pdf' });
  else {
    const cv = document.createElement('canvas'); cv.width = 40; cv.height = 30;
    const g = cv.getContext('2d'); g.fillStyle = '#c33'; g.fillRect(0, 0, 40, 30);
    f = new File([await new Promise(r => cv.toBlob(r, 'image/png'))], a.nome, { type: 'image/png' });
  }
  const dt = new DataTransfer(); dt.items.add(f);
  if (a.como === 'colar') (document.activeElement || document.body).dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
  else {
    const alvo = document.querySelector('#folhas .folha');
    alvo.dispatchEvent(new DragEvent('dragover', { dataTransfer: dt, bubbles: true, cancelable: true }));
    alvo.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
  }
  return true;
}"""


def _limpo(t):
    return " ".join(str(t or "").replace("\xa0", " ").split())


# Um Chromium só para o arquivo todo (cada classe abre a sua página, num contexto novo): bem mais rápido que um por classe.
_NAV = {}


def setUpModule():
    if sync_playwright:
        _NAV["pw"] = sync_playwright().start()
        _NAV["b"] = _NAV["pw"].chromium.launch()


def tearDownModule():
    if _NAV:
        _NAV.pop("b").close()
        _NAV.pop("pw").stop()


class TelaIA(Tela):
    """Base desta área: a página como na Tela (tests/tela_base.py), os falsos da IA, da fala, do microfone e da câmera, e ajudantes.
    INICIO: um script a mais que roda antes do app (por exemplo, para fingir que não há https)."""
    INICIO = ""

    @classmethod
    def setUpClass(cls):
        cls.pw, cls.b = _NAV["pw"], _NAV["b"]
        # "reduzir movimento" do aparelho: as janelas abrem sem animação (o app respeita) e os toques não esperam o fim dela
        cls.ctx = cls.b.new_context(timezone_id="America/Sao_Paulo", locale="pt-BR", viewport={"width": cls.LARGURA, "height": cls.ALTURA}, reduced_motion="reduce")
        cls.pg = cls.ctx.new_page()
        cls.pg.set_default_timeout(5000)
        cls.erros = []
        cls.pg.on("pageerror", lambda e: cls.erros.append(str(e)))
        cls.pg.clock.set_fixed_time("2026-11-02T10:00:00-03:00")
        cls.pg.add_init_script("window.GERENCIA_DEMO = true; window.GERENCIA_TESTE = true;" + cls.INICIO)
        cls.pg.goto(INDEX)
        cls.pg.wait_for_function("window.GERENCIA_TESTE && window.GERENCIA_TESTE.S && window.GERENCIA_TESTE.S.d")
        cls.pg.evaluate("window.__UI0 = JSON.stringify(window.GERENCIA_TESTE.S.ui)")

    @classmethod
    def tearDownClass(cls):
        cls.ctx.close()

    def setUp(self):
        self.pg.evaluate(_FALSOS)

    def abrir(self, d=None, ui=None, bens=None):
        super().abrir(d, ui, bens)
        # a janela do teste anterior some na hora (o app tira o fundo escuro dela 240 ms depois, e ele seguraria o primeiro toque)
        self.js("(T.FOLHA || (document.getElementById('folhas').innerHTML = ''), true)")

    # ---- os falsos
    def responder(self, lanc=(), invs=()):
        """O que a IA vai responder na próxima leitura."""
        self.js("(window.__ia.resp = a, true)", {"lancamentos": list(lanc), "investimentos": list(invs), "entidade": "simulada"})

    def segurar_ia(self):
        self.js("(window.__ia.segura = true)")

    def soltar_ia(self):
        self.js("(window.__ia.segura = false, window.__ia.soltar(), true)")
        self.esperar_ia()

    def pedidos(self):
        """O que a tela mandou para a IA, em ordem."""
        return self.js("window.__ia.pedidos")

    def esperar_ia(self):
        """Espera a IA (ou a fala para texto) responder e a tela se redesenhar."""
        self.pg.wait_for_function("() => { const s = window.GERENCIA_TESTE.IAS; return !s || !['lendo', 'transcrevendo'].includes(s.etapa); }")
        self.esperar()

    # ---- caminhos da tela
    def ler_com_ia(self):
        """Início › Adicionar › Ler com IA."""
        self.clicar('#nav [data-a="novo"]')
        self.clicar('#folhas .op[data-a="ia"]')

    def nova_despesa(self):
        """Caixa › Adicionar: a Nova despesa, com os quadrinhos da IA no alto."""
        self.ir("caixa")
        self.clicar('#nav [data-a="novo"]')

    def novo_investimento(self):
        self.ir("investimentos")
        self.clicar('#nav [data-a="novo"]')

    def colar_e_ler(self, texto):
        self.preencher("#ia-txt", texto)
        self.clicar('#folhas [data-a="ia-ler"]')
        self.esperar_ia()

    def ler(self, lanc=(), invs=(), texto="mensagem do WhatsApp"):
        """Ler com IA uma mensagem colada, com esta resposta da IA, até a conferência."""
        self.responder(lanc, invs)
        self.ler_com_ia()
        self.colar_e_ler(texto)

    def salvar_ia(self):
        """O botão da conferência (Lançar, Salvar, Atualizar): espera gravar e fechar."""
        self.clicar('#folhas [data-a="ia-salvar"]')
        self.pg.wait_for_function("() => !window.GERENCIA_TESTE.IAS")
        self.esperar()

    def galeria(self, sel):
        """Toca num botão que abre a galeria do aparelho; devolve a escolha de arquivo aberta."""
        with self.pg.expect_file_chooser() as fc:
            self.pg.locator(sel).first.click()
        return fc.value

    def escolher(self, sel, arquivo):
        self.galeria(sel).set_files(arquivo)

    def soltar_arquivo(self, como, tipo, nome):
        """Cola (como='colar') ou solta (como='soltar') uma imagem ('png') ou um PDF ('pdf') na janela."""
        self.pg.evaluate(_SOLTAR, {"como": como, "tipo": tipo, "nome": nome})

    def camera_ao_vivo(self):
        self.pg.wait_for_function("() => { const v = document.querySelector('#camera video'); const C = window.GERENCIA_TESTE.CAM;"
                                  " return v && v.videoWidth > 0 && C && C.status === 'ao-vivo'; }")
        self.esperar()

    def fotografar(self, n):
        for _ in range(n):
            self.clicar('#camera [data-a="cam-foto"]')

    def esperar_gravando(self):
        self.pg.wait_for_function("() => { const s = window.GERENCIA_TESTE.IAS; return s && s.etapa === 'voz' && s.rec === 'on'; }")
        self.esperar()

    # ---- leitura da tela
    def desligado(self, sel):
        return self.js("document.querySelector(a).disabled", sel)

    def quadrinhos(self):
        return [_limpo(t) for t in self.textos("#folhas .imp-tile")]

    def nomes(self):
        return [_limpo(t) for t in self.textos("#folhas .ia-item-t b")]

    def detalhes(self):
        return [_limpo(t) for t in self.textos("#folhas .ia-item-t span")]

    def botao_salvar(self):
        return _limpo(self.texto('#folhas [data-a="ia-salvar"]'))

    def lancamentos(self, *campos):
        return [tuple(l.get(c) for c in campos) for l in self.dados()["lancamentos"]]


# ---------------------------------------------------------------------------------------------------------------
class TestJanelaLerComIA(TelaIA):
    """Ler com IA (Início › Adicionar): as opções, o que vai para a IA e o que aparece enquanto ela lê."""

    def test_abre_com_arquivo_camera_falar_e_campo_de_texto(self):
        self.abrir(base(bancos=BANCOS))
        self.ler_com_ia()
        self.assertEqual(self.folha(), "Ler com IA")
        self.assertEqual([_limpo(b) for b in self.textos("#folhas .ia-arq .btn")], ["Fatura, print, foto ou PDF", "Digitalizar com a câmera", "Falar"])
        self.assertEqual(self.conta("#folhas #ia-txt"), 1, "campo para colar o texto")
        self.assertTrue(self.desligado('#folhas [data-a="ia-ler"]'), "sem texto nem arquivo, Ler com IA fica desligado")

    def test_mensagem_colada_vai_para_a_ia_sem_anexo(self):
        self.abrir(base(bancos=BANCOS))
        self.ler([FEIRA], texto="gastei 45 na feira")
        self.assertEqual(self.pedidos(), [{"modo": "auto", "dica": "caixa", "texto": "gastei 45 na feira"}],
                         "a IA separa sozinha (modo auto), só com o texto")

    def test_enquanto_le_mostra_lendo_sem_botoes(self):
        self.abrir(base(bancos=BANCOS))
        self.responder([FEIRA])
        self.segurar_ia()
        self.ler_com_ia()
        self.preencher("#ia-txt", "gastei 45 na feira")
        self.clicar('#folhas [data-a="ia-ler"]')
        self.assertEqual(self.folha(), "Lendo com IA")
        self.assertIn("Lendo o texto com a IA do Home Assistant…", self.folha_texto())
        self.assertEqual(self.conta("#folhas .folha-pe"), 0, "sem botões enquanto a IA lê")
        self.soltar_ia()
        self.assertEqual(self.folha(), "Conferir lançamentos", "quando a IA responde, vem a conferência")

    def test_imagem_escolhida_vai_como_anexo_jpeg(self):
        self.abrir(base(bancos=BANCOS))
        self.responder([FEIRA])
        self.ler_com_ia()
        self.escolher('#folhas [data-a="ia-arq"]', JPG)
        self.pg.wait_for_selector("#folhas .ia-prev")
        self.assertEqual((self.texto("#folhas .ia-prev b"), self.texto("#folhas .ia-prev small")), ("print.jpg", "Imagem"))
        self.clicar('#folhas [data-a="ia-ler"]')
        self.esperar_ia()
        p = self.pedidos()[0]
        self.assertEqual((p["modo"], p["dica"], p["texto"]), ("auto", "caixa", ""))
        self.assertTrue(p["anexo"]["b64"].startswith("data:image/jpeg;base64,"), "a imagem vai em JPEG")
        self.assertNotIn("anexos", p, "uma imagem só: um anexo")

    def test_pdf_escolhido_vai_como_pdf(self):
        self.abrir(base(bancos=BANCOS))
        self.responder([FEIRA])
        self.segurar_ia()
        self.ler_com_ia()
        self.escolher('#folhas [data-a="ia-arq"]', PDF)
        self.pg.wait_for_selector("#folhas .ia-prev")
        self.assertEqual(self.texto("#folhas .ia-prev small"), "PDF")
        self.clicar('#folhas [data-a="ia-ler"]')
        self.assertIn("Lendo o PDF", self.folha_texto())
        self.soltar_ia()
        self.assertTrue(self.pedidos()[0]["anexo"]["b64"].startswith("data:application/pdf;base64,"), "o PDF vai como PDF, sem virar imagem")

    def test_erro_da_ia_aparece_e_a_mensagem_continua_la(self):
        self.abrir(base(bancos=BANCOS))
        self.js("(window.__ia.erro = 'A IA do Home Assistant não respondeu.', true)")
        self.ler_com_ia()
        self.colar_e_ler("gastei 45 na feira")
        self.assertEqual(self.folha(), "Ler com IA", "volta para a entrada")
        self.assertEqual(self.texto("#folhas .msg-erro"), "Não consegui ler. A IA do Home Assistant não respondeu.")
        self.assertEqual(self.pg.input_value("#ia-txt"), "gastei 45 na feira", "o texto não se perde")

    def test_ia_que_nao_acha_nada_explica(self):
        self.abrir(base(bancos=BANCOS))
        self.ler([], [], texto="bom dia")
        self.assertEqual(self.folha(), "Ler com IA")
        self.assertEqual(self.texto("#folhas .msg-erro"), "A IA não encontrou gasto, recebimento, conta nem investimento. Tente outra imagem ou cole o texto.")


# ---------------------------------------------------------------------------------------------------------------
class TestQuadrinhos(TelaIA):
    """Os quadrinhos do alto da Nova despesa e do Novo investimento: cada um abre só aquilo."""

    def test_nova_despesa_tem_os_quatro_quadrinhos(self):
        self.abrir(base(bancos=BANCOS))
        self.nova_despesa()
        self.assertEqual(self.folha(), "Nova despesa")
        self.assertEqual(self.quadrinhos(), ["Colar mensagem", "Fatura, print ou foto", "Digitalizar com IA", "Falar"],
                         "com https e fala para texto, nenhum aviso nos quadrinhos")

    def test_novo_investimento_tem_imagem_ou_print_e_atualizar_saldos(self):
        self.abrir(base(bancos=BANCOS, investimentos=[CDB]))
        self.novo_investimento()
        self.assertEqual(self.folha(), "Novo investimento")
        self.assertEqual(self.quadrinhos(), ["Colar mensagem", "Imagem ou print", "Digitalizar com IA", "Falar"])
        self.assertEqual(_limpo(self.texto("#folhas .imp-saldos")), "Atualizar saldos de vários")

    def test_colar_mensagem_abre_so_o_campo_da_mensagem(self):
        self.abrir(base(bancos=BANCOS))
        self.nova_despesa()
        self.clicar('#folhas [data-a="ia-de"][data-ini="texto"]')
        self.assertEqual(self.folha(), "Colar mensagem")
        self.assertEqual(self.conta('#folhas [data-a="ia-arq"], #folhas [data-a="ia-cam"], #folhas [data-a="ia-falar"]'), 0, "sem imagem, câmera nem Falar")
        self.pg.wait_for_function("() => document.activeElement && document.activeElement.id === 'ia-txt'")  # o teclado já abre no campo

    def test_do_novo_investimento_so_vem_investimentos_e_nada_vai_para_o_caixa(self):
        self.abrir(base(bancos=BANCOS, investimentos=[CDB]))
        self.responder([gasto("Taxa de custódia", 12)], [inv("LCI Verde", 2000, banco="Banco Verde", tipo="lci", taxa=95)])
        self.novo_investimento()
        self.clicar('#folhas [data-a="ia-de"][data-ini="texto"]')
        self.colar_e_ler("2.000 na LCI do Banco Verde")
        p = self.pedidos()[0]
        self.assertEqual((p["dica"], p.get("so_invest")), ("invest", True), "a IA só procura investimentos")
        self.assertEqual(self.folha(), "Conferir investimentos")
        self.assertEqual(self.conta('#folhas [data-a="ia-marca"]'), 0, "nenhum lançamento para conferir")
        self.salvar_ia()
        d = self.dados()
        self.assertEqual(d["lancamentos"], [], "nada vai para o caixa")
        self.assertEqual([i["nome"] for i in d["investimentos"]], ["CDB Azul", "LCI Verde"])

    def test_fatura_print_ou_foto_abre_a_galeria_sem_trocar_a_janela(self):
        self.abrir(base(bancos=BANCOS))
        self.nova_despesa()
        escolha = self.galeria('#folhas [data-a="ia-de"][data-ini="arquivo"]')
        self.assertEqual((self.folha(), self.niveis()), ("Nova despesa", 1), "com a galeria aberta, a Nova despesa continua")
        escolha.set_files(JPG)
        self.pg.wait_for_selector("#folhas .ia-prev")
        self.assertEqual((self.folha(), self.niveis()), ("Fatura, print ou foto", 2), "escolheu: a leitura abre por cima da Nova despesa")

    def test_colar_imagem_na_nova_despesa_abre_a_leitura_com_ela(self):
        self.abrir(base(bancos=BANCOS))
        self.nova_despesa()
        self.soltar_arquivo("colar", "png", "colada.png")
        self.pg.wait_for_selector("#folhas .ia-prev")
        self.assertEqual((self.folha(), self.niveis()), ("Fatura, print ou foto", 2))
        self.assertEqual(self.texto("#folhas .ia-prev b"), "colada.png")

    def test_soltar_pdf_no_novo_investimento_abre_imagem_ou_print(self):
        """No computador: arrastar o PDF para a janela."""
        self.abrir(base(bancos=BANCOS, investimentos=[CDB]))
        self.novo_investimento()
        self.soltar_arquivo("soltar", "pdf", "extrato.pdf")
        self.pg.wait_for_selector("#folhas .ia-prev")
        self.assertEqual((self.folha(), self.niveis()), ("Imagem ou print", 2))
        self.assertEqual((self.texto("#folhas .ia-prev b"), self.texto("#folhas .ia-prev small")), ("extrato.pdf", "PDF"))


# ---------------------------------------------------------------------------------------------------------------
class TestVoltarParaANovaDespesa(TelaIA):
    """Fatura, print ou foto e Falar, abertos da Nova despesa (ou do Novo investimento), voltam para ela. O X, o Cancelar,
    o que foi digitado e o salvar que fecha tudo, a partir do Colar mensagem, estão em test_tela_mais.py (TestNavegacao)."""

    def abrir_fatura(self):
        self.nova_despesa()
        self.escolher('#folhas [data-a="ia-de"][data-ini="arquivo"]', JPG)
        self.pg.wait_for_selector("#folhas .ia-prev")
        self.assertEqual(self.folha(), "Fatura, print ou foto")

    def test_voltar_do_celular_na_fatura_volta_para_a_nova_despesa(self):
        self.abrir(base(bancos=BANCOS))
        self.abrir_fatura()
        self.voltar()
        self.assertEqual((self.folha(), self.niveis()), ("Nova despesa", 1))

    def test_x_no_falar_volta_para_o_novo_investimento_e_para_de_gravar(self):
        self.abrir(base(bancos=BANCOS))
        self.novo_investimento()
        self.clicar('#folhas [data-a="ia-de"][data-ini="voz"]')
        self.esperar_gravando()
        self.assertEqual(self.folha(), "Falar")
        self.clicar('#folhas .folha-cab [data-a="fechar"]')
        self.assertEqual((self.folha(), self.niveis()), ("Novo investimento", 1))
        self.assertEqual(self.js("window.__grav.cancelou"), 1, "o microfone para de gravar")


# ---------------------------------------------------------------------------------------------------------------
class TestCamera(TelaIA):
    """Digitalizar com IA: a câmera aqui dentro, até 4 páginas, e o Pronto já lê."""

    def abrir_camera(self):
        self.nova_despesa()
        self.clicar('#folhas [data-a="ia-de"][data-ini="camera"]')

    def test_abre_a_camera_de_tras_ao_vivo(self):
        self.abrir(base(bancos=BANCOS))
        self.abrir_camera()
        self.camera_ao_vivo()
        self.assertEqual(self.texto("#camera .cam-titulo"), "Digitalizar com IA")
        self.assertEqual(self.texto("#camera .cam-dica"), "Enquadre a fatura, a nota ou a lista e toque no botão")
        self.assertTrue(self.desligado('#camera [data-a="cam-pronto"]'), "sem foto, Pronto fica desligado")
        pedido = self.js("window.__cam.pedidos[0]")
        self.assertEqual((pedido["audio"], pedido["video"]["facingMode"]), (False, {"ideal": "environment"}), "a câmera de trás, sem som")

    def test_cada_foto_conta_uma_pagina(self):
        self.abrir(base(bancos=BANCOS))
        self.abrir_camera()
        self.camera_ao_vivo()
        self.fotografar(2)
        self.assertEqual(self.texto("#camera .cam-dica"), "2 páginas. Fotografe outra ou toque em Pronto.")
        self.assertEqual(self.texto("#camera .cam-pronto"), "Pronto (2)")
        self.assertEqual(self.conta("#camera .cam-fotos img"), 2)

    def test_no_maximo_quatro_paginas(self):
        self.abrir(base(bancos=BANCOS))
        self.abrir_camera()
        self.camera_ao_vivo()
        self.fotografar(4)
        self.assertTrue(self.desligado('#camera [data-a="cam-foto"]'), "na quarta, o botão de fotografar desliga")
        self.assertEqual(self.texto("#camera .cam-dica"), "4 páginas. Toque em Pronto.")
        self.js("T.camFoto()")
        self.assertEqual(self.js("T.CAM.fotos.length"), 4, "não passa de 4")
        self.assertEqual((self.conta("#camera .cam-fotos img"), self.texto("#camera .cam-fotos span")), (3, "+1"), "as 3 últimas e quantas mais")

    def test_pronto_manda_as_paginas_numa_leitura_so(self):
        self.abrir(base(bancos=BANCOS))
        self.responder([FEIRA])
        self.abrir_camera()
        self.camera_ao_vivo()
        self.fotografar(3)
        self.clicar('#camera [data-a="cam-pronto"]')
        self.esperar_ia()
        ps = self.pedidos()
        self.assertEqual(len(ps), 1, "uma leitura só")
        self.assertEqual(len(ps[0]["anexos"]), 3, "as 3 páginas juntas")
        self.assertTrue(all(a["b64"].startswith("data:image/jpeg;base64,") for a in ps[0]["anexos"]))
        self.assertNotIn("anexo", ps[0])

    def test_pronto_fecha_a_camera_e_mostra_a_conferencia_sobre_a_nova_despesa(self):
        self.abrir(base(bancos=BANCOS))
        self.responder([FEIRA])
        self.abrir_camera()
        self.camera_ao_vivo()
        self.fotografar(1)
        self.clicar('#camera [data-a="cam-pronto"]')
        self.esperar_ia()
        self.assertEqual(self.conta("#camera"), 0)
        self.assertEqual(self.js("window.__cam.trilhas[0].readyState"), "ended", "a câmera desliga")
        self.assertEqual((self.folha(), self.niveis()), ("Conferir lançamentos", 2), "a IA já leu; a Nova despesa fica embaixo")

    def test_voltar_do_celular_fecha_a_camera_e_desliga(self):
        self.abrir(base(bancos=BANCOS))
        self.abrir_camera()
        self.camera_ao_vivo()
        self.voltar()
        self.assertEqual(self.conta("#camera"), 0)
        self.assertEqual(self.js("window.__cam.trilhas[0].readyState"), "ended", "a câmera desliga")
        self.assertEqual((self.folha(), self.niveis()), ("Nova despesa", 1))

    def test_x_da_camera_fecha_e_volta_para_a_nova_despesa(self):
        self.abrir(base(bancos=BANCOS))
        self.abrir_camera()
        self.camera_ao_vivo()
        self.clicar('#camera [data-a="cam-fechar"]')
        self.assertEqual(self.conta("#camera"), 0)
        self.assertEqual(self.js("window.__cam.trilhas[0].readyState"), "ended")
        self.assertEqual((self.folha(), self.niveis()), ("Nova despesa", 1))

    def test_voltar_depois_de_ler_volta_para_a_nova_despesa(self):
        self.abrir(base(bancos=BANCOS))
        self.responder([FEIRA])
        self.abrir_camera()
        self.camera_ao_vivo()
        self.fotografar(1)
        self.clicar('#camera [data-a="cam-pronto"]')
        self.esperar_ia()
        self.voltar()
        self.assertEqual((self.folha(), self.niveis()), ("Nova despesa", 1), "a conferência ficou no lugar da câmera: um Voltar só")

    def test_camera_do_ler_com_ia_volta_para_ele(self):
        self.abrir(base(bancos=BANCOS))
        self.ler_com_ia()
        self.clicar('#folhas [data-a="ia-cam"]')
        self.camera_ao_vivo()
        self.voltar()
        self.assertEqual(self.conta("#camera"), 0)
        self.assertEqual((self.folha(), self.niveis()), ("Ler com IA", 1))

    def test_sem_permissao_explica_e_oferece_escolher_foto(self):
        self.abrir(base(bancos=BANCOS))
        self.js("(window.__cam.modo = 'NotAllowedError', true)")
        self.abrir_camera()
        self.pg.wait_for_selector("#camera .cam-msg")
        self.assertEqual(self.texto("#camera .cam-msg p"), "Sem permissão para usar a câmera. Libere a câmera para o app do Home Assistant "
                                                           "nas configurações do celular, ou escolha uma foto.")
        self.assertEqual(_limpo(self.texto('#camera [data-a="cam-galeria"]')), "Tirar ou escolher foto")
        self.assertEqual(self.conta('#camera [data-a="cam-foto"]'), 0, "sem o botão de fotografar")

    def test_tirar_ou_escolher_foto_usa_a_camera_do_celular_e_le(self):
        self.abrir(base(bancos=BANCOS))
        self.responder([FEIRA])
        self.js("(window.__cam.modo = 'NotFoundError', true)")
        self.abrir_camera()
        self.pg.wait_for_selector("#camera .cam-msg")
        self.assertEqual(self.texto("#camera .cam-msg p"), "Não deu para abrir a câmera. Dá para escolher uma foto.")
        escolha = self.galeria('#camera [data-a="cam-galeria"]')
        self.assertEqual((escolha.element.get_attribute("capture"), escolha.element.get_attribute("accept")), ("environment", "image/*"),
                         "abre a câmera do celular (ou a galeria)")
        escolha.set_files(JPG)
        self.pg.wait_for_function("() => { const s = window.GERENCIA_TESTE.IAS; return s && s.etapa === 'revisao'; }")
        self.esperar()
        self.assertEqual(self.conta("#camera"), 0)
        self.assertEqual((self.folha(), self.niveis()), ("Conferir lançamentos", 2))
        self.assertTrue(self.pedidos()[0]["anexo"]["b64"].startswith("data:image/jpeg;base64,"))

    def test_lanterna_liga_e_desliga_quando_o_celular_tem(self):
        self.abrir(base(bancos=BANCOS))
        self.js("(window.__cam.luz = true)")
        self.abrir_camera()
        self.camera_ao_vivo()
        self.clicar('#camera [data-a="cam-luz"]')
        self.assertEqual(self.pg.get_attribute('#camera [data-a="cam-luz"]', "aria-pressed"), "true")
        self.clicar('#camera [data-a="cam-luz"]')
        self.assertEqual(self.pg.get_attribute('#camera [data-a="cam-luz"]', "aria-pressed"), "false")
        self.assertEqual(self.js("window.__cam.luzes"), [True, False], "liga e desliga a lanterna do celular")


class TestCameraSemHttps(TelaIA):
    """Sem https (http no navegador), não há câmera aqui: o app explica e oferece tirar ou escolher a foto pelo celular."""
    INICIO = ("Object.defineProperty(window, 'isSecureContext', { value: false, configurable: true });"
              "Object.defineProperty(navigator, 'mediaDevices', { value: undefined, configurable: true });")

    def test_quadrinho_da_camera_avisa_que_precisa_de_https(self):
        self.abrir(base(bancos=BANCOS))
        self.nova_despesa()
        self.assertEqual(self.quadrinhos()[2], "Digitalizar com IA Precisa de https")

    def test_camera_explica_e_oferece_tirar_a_foto_pelo_celular(self):
        self.abrir(base(bancos=BANCOS))
        self.responder([FEIRA])
        self.nova_despesa()
        self.clicar('#folhas [data-a="ia-de"][data-ini="camera"]')
        self.assertEqual(self.texto("#camera .cam-msg p"), "A câmera só abre aqui com o Home Assistant num endereço seguro (https), "
                                                           "como o do Nabu Casa. Dá para tirar a foto pelo celular e escolher.")
        escolha = self.galeria('#camera [data-a="cam-galeria"]')
        self.assertEqual(escolha.element.get_attribute("capture"), "environment")
        escolha.set_files(JPG)
        self.pg.wait_for_function("() => { const s = window.GERENCIA_TESTE.IAS; return s && s.etapa === 'revisao'; }")
        self.esperar()
        self.assertEqual(self.folha(), "Conferir lançamentos", "a foto escolhida já vai para a IA")


# ---------------------------------------------------------------------------------------------------------------
class TestConferirLancamentos(TelaIA):
    """A conferência do que a IA leu para o caixa: marcar, categoria, conta, cartão, situação, parcelas e salvar."""

    def test_mostra_cada_lancamento_com_o_valor_e_o_total_no_botao(self):
        self.abrir(base(bancos=BANCOS))
        self.ler([FEIRA, PIX])
        self.assertEqual(self.folha(), "Conferir lançamentos")
        self.assertEqual(_limpo(self.texto("#folhas .folha-corpo > p")), "Achei 2 lançamentos. Desmarque o que não quiser.")
        self.assertEqual(self.nomes(), ["Feira do bairro", "Pix do Beto"])
        self.assertEqual(self.detalhes(), ["01/11", "02/11"])
        self.assertEqual([_limpo(t) for t in self.textos("#folhas .ia-item > b")], ["− R$ 45,00", "+ R$ 150,00"])
        self.assertEqual(self.botao_salvar(), "Lançar 2 · R$ 105", "150 que entram menos 45 que saem")

    def test_salvar_lanca_so_o_que_esta_marcado_e_vai_para_o_caixa(self):
        self.abrir(base(bancos=BANCOS))
        self.ler([FEIRA, PIX])
        self.clicar('#folhas [data-a="ia-marca"]', 1)
        self.assertEqual(self.botao_salvar(), "Lançar 1 · −R$ 45")
        self.salvar_ia()
        l = self.dados()["lancamentos"]
        self.assertEqual(len(l), 1, "o desmarcado não entra")
        self.assertEqual({k: l[0][k] for k in ("tipo", "descricao", "valor", "data", "categoria", "conta", "cartao", "pago")},
                         {"tipo": "despesa", "descricao": "Feira do bairro", "valor": 45, "data": "2026-11-01", "categoria": "c-mercado",
                          "conta": "k-ana", "cartao": False, "pago": True})
        self.assertEqual(self.aviso(), "1 lançamento pela IA")
        self.assertEqual((self.folha(), self.js("T.S.ui.tab")), (None, "caixa"), "fecha e mostra o caixa")

    def test_parecido_com_um_ja_lancado_vem_desmarcado(self):
        self.abrir(base(bancos=BANCOS, lancamentos=[{"id": "ja", "tipo": "despesa", "descricao": "FEIRA DO BAIRRO LTDA", "valor": 45,
                                                       "data": "2026-11-02", "categoria": "c-mercado", "pago": True}]))
        self.ler([FEIRA, PIX])
        self.assertIn("off", self.pg.get_attribute("#folhas .ia-item >> nth=0", "class"), "a Feira vem desmarcada")
        self.assertEqual(self.detalhes()[0], "01/11 · parece já lançado")
        self.assertEqual(self.botao_salvar(), "Lançar 1 · R$ 150")

    def test_trocar_a_categoria_vale_no_lancamento(self):
        self.abrir(base(bancos=BANCOS))
        self.ler([FEIRA])
        self.pg.locator('#folhas [data-iai="categoria"]').first.select_option("c-restaurantes")
        self.esperar()
        self.salvar_ia()
        self.assertEqual(self.lancamentos("descricao", "categoria"), [("Feira do bairro", "c-restaurantes")])

    def test_conta_no_credito_vai_para_a_fatura(self):
        self.abrir(base(bancos=BANCOS))
        self.ler([FEIRA])
        self.pg.locator('#folhas [data-iai="contasel"]').first.select_option("k-ana|c")
        self.esperar()
        self.assertEqual(self.detalhes(), ["01/11 · na fatura"])
        self.salvar_ia()
        self.assertEqual(self.lancamentos("conta", "cartao", "pago"), [("k-ana", True, False)], "na fatura de 12/11, que ainda vai vencer")

    def test_lancar_todos_em_muda_a_conta_de_todas_as_linhas(self):
        self.abrir(base(bancos=BANCOS))
        self.ler([FEIRA, PIX])
        self.clicar('#folhas [data-a="iac-conta"][data-v="k-verde"]')
        self.assertEqual(self.js("[...document.querySelectorAll('#folhas [data-iai=\"contasel\"]')].map(s => s.value)"), ["k-verde", "k-verde"])
        self.salvar_ia()
        self.assertEqual(self.lancamentos("descricao", "conta"), [("Feira do bairro", "k-verde"), ("Pix do Beto", "k-verde")])

    def test_tudo_pendente_lanca_a_pagar_e_a_receber(self):
        self.abrir(base(bancos=BANCOS))
        self.ler([FEIRA, PIX])
        self.clicar('#folhas [data-a="iac-sit"][data-v="apagar"]')
        self.assertEqual(self.detalhes(), ["01/11 · a pagar", "02/11 · a receber"])
        self.salvar_ia()
        self.assertEqual(self.lancamentos("descricao", "pago"), [("Feira do bairro", False), ("Pix do Beto", False)])

    def test_parcela_lanca_as_proximas_nos_meses_seguintes(self):
        self.abrir(base(bancos=BANCOS))
        self.ler([gasto("Geladeira", 300, data="2026-10-15", categoria="c-compras", parcela_atual=2, parcelas_total=4)])
        self.assertEqual(self.detalhes(), ["15/10 · parcela 2/4"])
        self.assertIn("on", self.pg.get_attribute('#folhas [data-a="iac-futuras"]', "class"), "Lançar as próximas parcelas começa ligado")
        self.salvar_ia()
        l = self.dados()["lancamentos"]
        self.assertEqual([(x["parcela"], x["data"], x["valor"]) for x in l], [("2/4", "2026-10-15", 300), ("3/4", "2026-11-15", 300), ("4/4", "2026-12-15", 300)])
        self.assertEqual(len({x["grupo"] for x in l}), 1, "as parcelas ficam juntas")

    def test_lancamentos_e_investimentos_juntos_salvam_de_uma_vez(self):
        self.abrir(base(bancos=BANCOS))
        self.ler([FEIRA], [inv("Tesouro Selic 2029", 3000, banco="Banco Verde", tipo="tesouro", indexador="selic_mais", taxa=0.1)])
        self.assertEqual(self.folha(), "Conferir o que a IA leu")
        self.assertEqual(_limpo(self.texto("#folhas .folha-corpo > p")), "Achei 1 lançamento e 1 investimento. Desmarque o que não quiser.")
        self.assertEqual([_limpo(t) for t in self.textos("#folhas .ia-sec")], ["Lançamentos", "Investimentos"])
        self.assertEqual(self.botao_salvar(), "Salvar 2")
        self.salvar_ia()
        d = self.dados()
        self.assertEqual(([l["descricao"] for l in d["lancamentos"]], [i["nome"] for i in d["investimentos"]]), (["Feira do bairro"], ["Tesouro Selic 2029"]))
        self.assertEqual(self.aviso(), "1 lançamento e 1 investimento pela IA")


# ---------------------------------------------------------------------------------------------------------------
class TestConferirInvestimentos(TelaIA):
    """A conferência dos investimentos lidos: atualizar um que existe ou criar, aporte, dono, Revisar antes e a imagem."""

    DADOS = base(bancos=BANCOS, investimentos=[CDB, CARLA])

    def test_existente_mostra_a_diferenca_de_quanto_para_quanto(self):
        self.abrir(self.DADOS)
        self.ler([], [inv("CDB Azul", 1250, banco="Banco Azul", existente="cdb-azul")])
        self.assertEqual(self.folha(), "Conferir investimentos")
        self.assertEqual(_limpo(self.texto("#folhas .ia-atualiza")), "Aporte de R$ 250,00: R$ 1.000,00 → R$ 1.250,00")
        self.assertEqual(_limpo(self.texto("#folhas .ia-item > b")), "+ R$ 250,00")
        self.assertEqual(self.botao_salvar(), "Salvar 1")

    def test_salvar_grava_o_saldo_novo_no_existente(self):
        self.abrir(self.DADOS)
        self.ler([], [inv("CDB Azul", 1250, banco="Banco Azul", existente="cdb-azul")])
        self.salvar_ia()
        invs = self.dados()["investimentos"]
        self.assertEqual(len(invs), 2, "não cria outro")
        cdb = next(i for i in invs if i["id"] == "cdb-azul")
        self.assertEqual((cdb["valor"], cdb["data_valor"]), (1250, "2026-11-02"))
        self.assertEqual(self.aviso(), "1 investimento pela IA")
        self.assertEqual(self.js("[T.S.ui.tab, T.S.ui.invModo]"), ["investimentos", "carteira"], "mostra a Carteira")

    def test_novo_cria_o_investimento_e_o_banco_que_faltava(self):
        self.abrir(self.DADOS)
        self.ler([], [inv("Tesouro Selic 2029", 3000, banco="Banco Amarelo", tipo="tesouro", indexador="selic_mais", taxa=0.1,
                          liquidez="diaria", vencimento="2029-03-01", aplicado=2900)])
        self.assertEqual(_limpo(self.texto("#folhas .ia-atualiza")), "Novo investimento")
        self.assertEqual(self.detalhes(), ["Banco Amarelo · Tesouro · Selic + 0,1% a.a. · vence 01/03/2029"])
        self.salvar_ia()
        d = self.dados()
        novo = d["investimentos"][-1]
        banco = next(b for b in d["bancos"] if b["nome"] == "Banco Amarelo")
        self.assertEqual({k: novo[k] for k in ("nome", "banco", "tipo", "valor", "indexador", "taxa", "liquidez", "vencimento", "titular", "obs")},
                         {"nome": "Tesouro Selic 2029", "banco": banco["id"], "tipo": "tesouro", "valor": 3000, "indexador": "selic_mais", "taxa": 0.1,
                          "liquidez": "diaria", "vencimento": "2029-03-01", "titular": "meu", "obs": "Valor aplicado: R$ 2.900,00"})

    def test_aplicacao_soma_ao_valor_de_hoje(self):
        self.abrir(self.DADOS)
        self.ler([], [inv("CDB Azul", 0, banco="Banco Azul", existente="cdb-azul", aporte=300)])
        self.assertEqual(_limpo(self.texto("#folhas .ia-atualiza")), "Aplica R$ 300,00 em CDB Azul: R$ 1.000,00 → R$ 1.300,00")
        self.salvar_ia()
        self.assertEqual(next(i["valor"] for i in self.dados()["investimentos"] if i["id"] == "cdb-azul"), 1300)

    def test_revisar_antes_corrige_sem_sair_da_conferencia(self):
        self.abrir(self.DADOS)
        self.ler([], [inv("LCI Verde", 2000, banco="Banco Verde", tipo="lci", taxa=95)])
        self.clicar('#folhas [data-a="iai-revisar"]')
        self.assertEqual(self.folha(), "Revisar investimento novo")
        self.preencher("#iae-nome", "LCI Verde 2029")
        self.preencher("#iae-taxa", "97")
        self.clicar('#folhas [data-a="iae-ok"]')
        self.assertEqual(self.folha(), "Conferir investimentos", "Pronto volta para a lista")
        self.assertEqual(self.nomes(), ["LCI Verde 2029"])
        self.assertIn("97% do CDI", self.detalhes()[0])

    def test_revisar_antes_nao_aceita_sem_valor(self):
        self.abrir(self.DADOS)
        self.ler([], [inv("CDB Azul", 1250, banco="Banco Azul", existente="cdb-azul")])
        self.clicar('#folhas [data-a="iai-revisar"]')
        self.assertEqual(self.folha(), "Revisar CDB Azul")
        self.assertEqual(self.conta("#folhas [data-iae]"), 1, "do que já existe, só o saldo")
        self.digitar("#iae-v", "")
        self.clicar('#folhas [data-a="iae-ok"]')
        self.assertEqual(self.aviso(), "Coloque o valor.")
        self.assertEqual(self.folha(), "Revisar CDB Azul")

    def test_imagem_lida_fica_guardada_no_investimento(self):
        self.abrir(self.DADOS)
        self.responder([], [inv("LCI Verde", 2000, banco="Banco Verde", tipo="lci", taxa=95)])
        self.ler_com_ia()
        self.escolher('#folhas [data-a="ia-arq"]', JPG)
        self.pg.wait_for_selector("#folhas .ia-prev")
        self.clicar('#folhas [data-a="ia-ler"]')
        self.esperar_ia()
        self.salvar_ia()
        self.assertEqual(self.dados()["investimentos"][-1]["fotos"], ["foto-1.jpg"])
        self.assertTrue(self.js("window.__fotos.length === 1 && window.__fotos[0].startsWith('data:image/jpeg')"), "a imagem lida é guardada uma vez")


# ---------------------------------------------------------------------------------------------------------------
class TestAtualizarSaldos(TelaIA):
    """Atualizar saldos: a listinha com o valor de agora; o aporte é a diferença para o valor de hoje."""

    DADOS = base(bancos=BANCOS, investimentos=[CDB, RESERVA, CARLA, BETO])
    SALDOS = [inv("CDB Azul", 1250, banco="Banco Azul", existente="cdb-azul"), inv("Reserva Verde", 1900, banco="Banco Verde", existente="res-verde")]

    def abrir_saldos(self):
        self.clicar('#nav [data-a="novo"]')
        self.clicar('#folhas .op[data-a="ia-saldos"]')

    def test_adicionar_abre_com_de_quem_sao_a_escolher(self):
        self.abrir(self.DADOS)
        self.abrir_saldos()
        self.assertEqual(self.folha(), "Atualizar saldos")
        self.assertEqual(self.textos('#folhas [data-a="ias-pessoa"]'), ["Vários", "Meus", "Beto", "Carla"])
        self.assertEqual(self.texto('#folhas [data-a="ias-pessoa"].on'), "Vários")
        self.assertEqual(_limpo(self.texto('#folhas [data-a="ia-ler"]')), "Ler os saldos")

    def test_manda_a_lista_como_saldos_da_pessoa_escolhida(self):
        self.abrir(self.DADOS)
        self.responder([], self.SALDOS)
        self.abrir_saldos()
        self.clicar('#folhas [data-a="ias-pessoa"][data-v="meu"]')
        self.colar_e_ler("Banco Azul, valor atualizado, R$ 1.250")
        self.assertEqual(self.pedidos(), [{"modo": "auto", "dica": "invest", "texto": "Banco Azul, valor atualizado, R$ 1.250", "saldos": True, "pessoa": "meu"}])

    def test_conferencia_mostra_aporte_resgate_e_os_totais(self):
        self.abrir(self.DADOS)
        self.responder([], self.SALDOS)
        self.abrir_saldos()
        self.colar_e_ler("Banco Azul 1.250\nReserva Verde 1.900")
        self.assertEqual(self.folha(), "Conferir os saldos")
        self.assertEqual(_limpo(self.texto("#folhas .ia-saldos-res")), "Aportes R$ 250,00 Resgates R$ 100,00")
        self.assertEqual([_limpo(t) for t in self.textos("#folhas .ia-atualiza")],
                         ["Aporte de R$ 250,00: R$ 1.000,00 → R$ 1.250,00", "Resgate de R$ 100,00: R$ 2.000,00 → R$ 1.900,00"])
        self.assertEqual(self.botao_salvar(), "Atualizar 2")

    def test_atualizar_grava_os_saldos_e_avisa_os_aportes(self):
        self.abrir(self.DADOS)
        self.responder([], self.SALDOS)
        self.abrir_saldos()
        self.colar_e_ler("Banco Azul 1.250\nReserva Verde 1.900")
        self.salvar_ia()
        valores = {i["id"]: i["valor"] for i in self.dados()["investimentos"]}
        self.assertEqual((valores["cdb-azul"], valores["res-verde"], len(valores)), (1250, 1900, 4))
        self.assertEqual(self.aviso(), "2 saldos atualizados · aportes R$ 250")

    def test_carteira_de_terceiros_abre_com_a_pessoa_escolhida(self):
        self.abrir(self.DADOS)
        self.ir("investimentos")
        self.clicar('#app [data-a="filtro"][data-v="terc"]')
        self.clicar('#app [data-a="pessoa-f"][data-v="Carla"]')
        self.assertEqual(_limpo(self.texto("#app .ia-saldos-btn")), "Atualizar saldos de Carla com IA")
        self.clicar("#app .ia-saldos-btn")
        self.assertEqual(self.folha(), "Atualizar saldos de Carla")
        self.assertEqual(self.texto('#folhas [data-a="ias-pessoa"].on'), "Carla")

    def test_saldo_sem_investimento_igual_vira_novo_da_pessoa(self):
        self.abrir(self.DADOS)
        self.responder([], [inv("Banco Roxo", 600, banco="Banco Roxo", tipo="outro")])
        self.abrir_saldos()
        self.clicar('#folhas [data-a="ias-pessoa"][data-v="Carla"]')
        self.colar_e_ler("Banco Roxo, valor atualizado, R$ 600")
        self.assertEqual(_limpo(self.texto("#folhas .ia-atualiza")), "Novo investimento de Carla, com R$ 600,00")
        self.salvar_ia()
        novo = self.dados()["investimentos"][-1]
        self.assertEqual((novo["valor"], novo["titular"], novo["terceiro"]), (600, "terceiros", "Carla"))


# ---------------------------------------------------------------------------------------------------------------
class TestReciboDePagamento(TelaIA):
    """Ler recibo com IA (Descontos na fonte do recebimento): bruto, impostos em %, plano ligado e o líquido conferido."""

    def ler_recibo(self, holerite=HOLERITE, fixo=False):
        self.js("(window.__ia.resp = { holerite: a, entidade: 'simulada' }, true)", holerite)
        self.nova_despesa()
        self.clicar('#folhas [data-a="lf-tipo"][data-v="receita"]')
        if fixo:
            self.clicar('#folhas [data-a="lf-set"][data-k="repete"][data-v="mensal"]')
        self.clicar('#folhas [data-a="lf-desc-abrir"]')
        escolha = self.galeria('#folhas [data-a="lf-ler-recibo"]')
        accept = escolha.element.get_attribute("accept")
        escolha.set_files(PDF)
        self.pg.wait_for_function("() => window.__ia.pedidos.length > 0 && !window.GERENCIA_TESTE.LF.lendoRecibo")
        self.esperar()
        return accept

    def test_manda_o_arquivo_no_modo_recibo(self):
        self.abrir(base(bancos=BANCOS))
        accept = self.ler_recibo()
        self.assertEqual(accept, "application/pdf,image/*")
        p = self.pedidos()
        self.assertEqual((len(p), sorted(p[0]), p[0]["modo"]), (1, ["anexo", "modo"], "holerite"))
        self.assertTrue(p[0]["anexo"]["b64"].startswith("data:application/pdf;base64,"))
        self.assertEqual(self.aviso(), "Recibo lido. Confira antes de salvar.")

    def test_preenche_bruto_descricao_categoria_e_data(self):
        self.abrir(base(bancos=BANCOS))
        self.ler_recibo()
        self.assertEqual((self.pg.input_value("#lf-valor"), self.pg.input_value("#lf-desc"), self.pg.input_value("#lf-data")),
                         ("5.000,00", "Salário", "2026-11-05"))
        self.assertEqual(_limpo(self.texto('#folhas [data-a="lf-set"][data-k="categoria"].on')), "Salário")

    def test_impostos_viram_porcentagem_do_bruto(self):
        self.abrir(base(bancos=BANCOS))
        self.ler_recibo()
        self.assertEqual(self.js("[...document.querySelectorAll('#folhas [data-lfd=\"descricao\"]')].map(e => e.value)"), ["INSS", "Imposto de renda"])
        self.assertEqual(self.js("[...document.querySelectorAll('#folhas [data-lfd=\"valor\"]')].map(e => e.value)"), ["11", "6"])
        self.assertEqual([_limpo(t) for t in self.textos("#folhas .desc-v")], ["− R$ 550,00", "− R$ 300,00"])

    def test_confere_com_o_liquido_do_recibo(self):
        self.abrir(base(bancos=BANCOS))
        self.ler_recibo()
        self.assertEqual(_limpo(self.texto("#folhas .desc-res .liq b")), "R$ 3.900,00")
        self.assertEqual(_limpo(self.texto("#folhas .desc-conf")), "Confere com o líquido do recibo: R$ 3.900,00.")

    def test_liquido_diferente_do_recibo_avisa(self):
        self.abrir(base(bancos=BANCOS))
        self.ler_recibo(dict(HOLERITE, liquido=4000))
        self.assertEqual(_limpo(self.texto("#folhas .desc-conf")), "O recibo diz líquido de R$ 4.000,00; aqui deu R$ 3.900,00. Confira os valores.")

    def test_salario_fixo_cria_o_plano_como_despesa_ligada(self):
        self.abrir(base(bancos=BANCOS))
        self.ler_recibo(fixo=True)
        self.assertEqual([_limpo(t) for t in self.textos("#folhas .lig-l")], ["Plano de saúde · nova despesa fixa ligada − R$ 250,00"])
        self.clicar('#folhas [data-a="lf-salvar"]:not([data-mais])')
        recs = self.dados()["recorrencias"]
        sal = next(r for r in recs if r["tipo"] == "receita")
        self.assertEqual((sal["descricao"], sal["valor"], [(x["descricao"], x["modo"], x["valor"]) for x in sal["descontos"]]),
                         ("Salário", 5000, [("INSS", "pct", 11), ("Imposto de renda", "pct", 6)]))
        plano = next(r for r in recs if r["tipo"] == "despesa")
        self.assertEqual((plano["descricao"], plano["valor"], plano["categoria"], plano["vinculo"]), ("Plano de saúde", 250, "c-saude", sal["id"]))

    # (era bug até a 1.24.0: o plano conferido no líquido sumia ao salvar um recebimento de uma vez)
    def test_recibo_avulso_nao_perde_o_plano_que_entrou_no_liquido(self):
        self.abrir(base(bancos=BANCOS))
        self.ler_recibo()
        self.assertEqual(_limpo(self.texto("#folhas .desc-conf")), "Confere com o líquido do recibo: R$ 3.900,00.")
        self.clicar('#folhas [data-a="lf-salvar"]:not([data-mais])')
        d = self.dados()
        planos = [x for x in d["lancamentos"] + d["recorrencias"] if x.get("descricao") == "Plano de saúde"]
        self.assertEqual([p["valor"] for p in planos], [250], "o plano conferido no líquido também é gravado")
        sal = next(x for x in d["lancamentos"] if x["tipo"] == "receita")
        self.assertEqual((planos[0]["data"], planos[0]["conta"], planos[0]["tipo"]), (sal["data"], sal["conta"], "despesa"), "no mesmo dia e na mesma conta")


# ---------------------------------------------------------------------------------------------------------------
class TestIADesligada(TelaIA):
    """Usar IA desligado (Mais › Integrações): tudo o que usa IA some. O que já está em test_tela_mais.py (quadrinhos,
    Ler com IA do Adicionar, microfone, Uso da IA, dicas) e em test_tela_invest.py (Atualizar saldos da Carteira, Ler print)
    não se repete aqui."""

    def visivel(self, sel):
        return self.conta(sel) > 0 and self.pg.locator(sel).first.is_visible()

    def test_descontos_na_fonte_sem_ler_recibo_com_ia(self):
        self.abrir(base(bancos=BANCOS, ajustes=IA_DESLIGADA))
        self.nova_despesa()
        self.clicar('#folhas [data-a="lf-tipo"][data-v="receita"]')
        self.clicar('#folhas [data-a="lf-desc-abrir"]')
        self.assertTrue(self.visivel('#folhas [data-lfd], #folhas [data-a="lf-desc-add"]'), "os impostos na fonte continuam")
        self.assertFalse(self.visivel('#folhas [data-a="lf-ler-recibo"]'), "sem Ler recibo com IA")

    def test_colar_imagem_na_nova_despesa_nao_abre_a_leitura(self):
        self.abrir(base(bancos=BANCOS, ajustes=IA_DESLIGADA))
        self.nova_despesa()
        self.soltar_arquivo("colar", "png", "colada.png")
        self.esperar()
        self.assertEqual((self.folha(), self.niveis()), ("Nova despesa", 1))

    # (era bug até a 1.24.0)
    def test_adicionar_sem_atualizar_saldos(self):
        self.abrir(base(bancos=BANCOS, investimentos=[CDB], ajustes=IA_DESLIGADA))
        self.clicar('#nav [data-a="novo"]')
        self.assertEqual(self.folha(), "Adicionar")
        self.assertFalse(self.visivel('#folhas .escolhas [data-a="ia-saldos"]'))


class TestIADesligadaNoComputador(TelaIA):
    """No computador (1000 px ou mais), o Ler com IA fica no alto à direita; com a IA desligada, some."""
    LARGURA, ALTURA = 1366, 860

    def test_com_ia_desligada_o_alto_fica_sem_ler_com_ia(self):
        self.abrir(base(bancos=BANCOS, investimentos=[CDB], ajustes=IA_DESLIGADA))
        self.assertTrue(self.pg.locator('#app .top-acts [data-a="novo"]').is_visible(), "as ações do alto à direita estão na tela")
        self.assertFalse(self.pg.locator('#app .top-acts [data-a="ia"]').is_visible())

# ---------------------------------------------------------------------------------------------------------------
class TestFalar(TelaIA):
    """Falar: o microfone do alto grava, a fala para texto transcreve e a IA lê como uma mensagem."""

    def falar(self):
        self.clicar('#app .cab-topo [data-a="falar"]')
        self.esperar_gravando()

    def test_microfone_do_alto_abre_falar_ja_ouvindo(self):
        self.abrir(base(bancos=BANCOS))
        self.falar()
        self.assertEqual(self.folha(), "Falar")
        self.assertIn("Ouvindo…", self.texto("#folhas .voz-estado"))
        self.assertFalse(self.desligado('#folhas [data-a="fala-ok"]'), "Pronto liga enquanto grava")
        self.assertEqual(self.js("window.__grav.iniciou"), 1)

    def test_pronto_mostra_transcrevendo(self):
        self.abrir(base(bancos=BANCOS))
        self.js("(window.__voz.segura = true)")
        self.falar()
        self.clicar('#folhas [data-a="fala-ok"]')
        self.assertEqual(self.folha(), "Falar")
        self.assertEqual(self.texto("#folhas .ia-lendo p"), "Transcrevendo o que você disse…")
        self.js("(window.__voz.segura = false, window.__voz.soltar(), true)")
        self.esperar_ia()

    def test_o_que_foi_ouvido_vai_para_a_ia_como_fala(self):
        self.abrir(base(bancos=BANCOS))
        self.responder([FEIRA])
        self.falar()
        self.clicar('#folhas [data-a="fala-ok"]')
        self.esperar_ia()
        self.assertEqual(self.js("window.__voz.pedidos"), [3 * 16000], "o áudio gravado vai para a fala para texto")
        self.assertEqual(self.pedidos(), [{"modo": "auto", "dica": "caixa", "texto": "gastei 45 no mercado hoje", "fala": True}])

    def test_conferencia_mostra_o_que_foi_ouvido(self):
        self.abrir(base(bancos=BANCOS))
        self.responder([FEIRA])
        self.falar()
        self.clicar('#folhas [data-a="fala-ok"]')
        self.esperar_ia()
        self.assertEqual(self.folha(), "Conferir lançamentos")
        self.assertEqual(_limpo(self.texto("#folhas .ouvido")), "“gastei 45 no mercado hoje”")

    def test_fala_curta_demais_pede_para_falar_de_novo(self):
        self.abrir(base(bancos=BANCOS))
        self.js("(window.__grav.n = 4000, true)")  # um quarto de segundo
        self.falar()
        self.clicar('#folhas [data-a="fala-ok"]')
        self.assertEqual(self.texto("#folhas .msg-erro"), "Não ouvi nada. Toque no microfone e fale.")
        self.assertEqual(self.texto("#folhas .voz-estado"), "Toque no microfone e fale")
        self.assertTrue(self.desligado('#folhas [data-a="fala-ok"]'))
        self.assertEqual(self.js("window.__voz.pedidos"), [], "nada vai para a fala para texto")

    def test_erro_ao_transcrever_aparece(self):
        self.abrir(base(bancos=BANCOS))
        self.js("(window.__voz.erro = 'A fala para texto do Home Assistant não respondeu.', true)")
        self.falar()
        self.clicar('#folhas [data-a="fala-ok"]')
        self.esperar_ia()
        self.assertEqual(self.folha(), "Falar")
        self.assertEqual(self.texto("#folhas .msg-erro"), "A fala para texto do Home Assistant não respondeu.")
        self.assertEqual(self.texto("#folhas .voz-estado"), "Toque no microfone e fale", "dá para tentar de novo")
        self.assertEqual(self.pedidos(), [], "nada vai para a IA")

    def test_para_sozinho_em_dois_minutos(self):
        self.abrir(base(bancos=BANCOS))
        self.responder([FEIRA])
        self.js("(window.__grav.seg = 120, true)")
        self.clicar('#app .cab-topo [data-a="falar"]')
        self.pg.wait_for_function("() => window.__voz.pedidos.length === 1")
        self.esperar_ia()
        self.assertEqual(self.js("window.__grav.parou"), 1, "terminou sem tocar em Pronto")
        self.assertEqual(self.folha(), "Conferir lançamentos")

    def test_sem_fala_para_texto_o_microfone_some(self):
        self.abrir(base(bancos=BANCOS))
        self.js("(T.S.voz = { pronta: false, motivo: 'Nenhuma fala para texto no Home Assistant.' }, T.render(), true)")
        self.assertEqual(self.conta('#app [data-a="falar"]'), 0, "sem o microfone no alto")
        self.nova_despesa()
        self.assertEqual(self.quadrinhos(), ["Colar mensagem", "Fatura, print ou foto", "Digitalizar com IA"], "sem o quadrinho Falar")

    def test_mensagens_de_erro_do_microfone_explicam_o_que_fazer(self):
        self.abrir(base())
        m = self.js("['NotAllowedError', 'NotFoundError', 'NotReadableError', 'NoApi'].map(n => T.erroMicrofone({ name: n }))")
        self.assertEqual(m[0], "O microfone está bloqueado. Permita o microfone para o Home Assistant (no navegador, no cadeado ao lado do endereço; "
                               "no app do celular, nas permissões do app Home Assistant) e tente de novo.")
        self.assertEqual(m[1], "Não achei um microfone neste aparelho.")
        self.assertEqual(m[2], "O microfone está sendo usado por outro app. Feche o outro e tente de novo.")
        self.assertEqual(m[3], "Este navegador não deixa usar o microfone aqui. Abra o Home Assistant pelo endereço com https (como o do Nabu Casa) ou pelo app.",
                         "sem https: explica onde abrir")


# ---------------------------------------------------------------------------------------------------------------
class TestCardsDaIAEmMais(TelaIA):
    """Mais › Integrações: Leitura por IA (a chave, a situação, qual IA) e os tipos do Uso da IA (os números e o gráfico por dia
    estão em test_tela_mais.py)."""

    def integracoes(self):
        self.ir("mais")
        self.clicar('#app [data-a="mais-aba"][data-v="integracoes"]')
        self.pg.wait_for_selector("#uso-ia .uso-tiles")
        self.esperar()

    def test_leitura_por_ia_mostra_a_chave_ligada_e_a_situacao(self):
        self.abrir(base(bancos=BANCOS))
        self.integracoes()
        self.assertEqual((self.texto("#ia .linha-sw b"), self.texto("#ia .linha-sw span")), ("Usar IA", "Ligado: Ler com IA, Ler recibo, Falar e os preços das dicas."))
        self.assertEqual(self.pg.get_attribute('#ia [data-a="ajuste"][data-k="ia"]', "aria-checked"), "true")
        self.assertEqual(self.textos("#ia .status"), ["Na prévia, a leitura por IA é simulada.", "Falar: na prévia, a fala é simulada."])
        self.assertEqual(_limpo(self.texto("#app .sync")), "IA simulada na prévia")

    def test_ia_sem_anexos_aparece_como_so_texto_e_a_escolha_fica_gravada(self):
        self.abrir(base(bancos=BANCOS))
        self.integracoes()
        self.js("(T.S.ia = { pronta: true, selecionada: '', entidades: [{ id: 'ai_task.ia_azul', nome: 'IA Azul', imagens: true },"
                " { id: 'ai_task.ia_texto', nome: 'IA Texto', imagens: false }] }, T.render(), true)")
        self.assertEqual(self.textos("#ia-ent option"), ["Padrão do Home Assistant", "IA Azul", "IA Texto (só texto)"])
        self.pg.select_option("#ia-ent", "ai_task.ia_azul")
        self.esperar()
        self.assertEqual(self.dados()["ajustes"]["ia_entidade"], "ai_task.ia_azul")
        self.assertEqual(self.aviso(), "IA escolhida")

    def test_uso_por_tipo_com_nomes_em_portugues(self):
        self.abrir(base(bancos=BANCOS))
        self.integracoes()
        self.assertEqual([_limpo(t) for t in self.textos("#uso-ia .uso-tipos li")],
                         ["Ler lançamentos 6", "Conferir preço de assinatura 4", "Falar 2", "Ler recibo de pagamento 2", "Ler investimentos 2"])


if __name__ == "__main__":
    unittest.main()
