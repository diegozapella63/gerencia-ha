"""A tela do GerencIA nas partes de sistema: a conversa com o servidor, o microfone, o toque, o tema, as opções e casos de canto.

Roda o app.js de verdade num Chromium (base em tests/tela_base.py: relógio parado em 02/11/2026 10:00, 390 px), com
microfone falso do próprio Chromium (--use-fake-device-for-media-stream: um bipe) e permissão de microfone.
Dois jeitos de abrir a página:
  - a prévia (window.GERENCIA_DEMO): os dados ficam na memória (apiDemo), como nos outros testes da tela;
  - "com servidor" (sem GERENCIA_DEMO): o app usa apiServidor, e um window.fetch falso faz o papel do server.py
    (window.__srv: guarda cada pedido com método, rota, corpo e cabeçalhos; responde como o servidor, ou o que o teste
    mandar em __srv.resp; com __srv.segurar a resposta só vem quando o teste soltar). O relógio de 20 s que confere se
    outro app mudou algo fica guardado em __srv.aCada20s, para o teste chamar na hora certa.

Um teste marcado com @unittest.expectedFailure e "BUG:" descreve o comportamento certo que o app ainda não tem.
Dados sempre inventados (Ana, Beto, Carla, Banco Azul, Banco Verde).
"""
import json
import unittest

from tests.tela_base import Tela, base, BANCOS, INDEX, sync_playwright

PRONTO = "window.GERENCIA_TESTE && window.GERENCIA_TESTE.S && window.GERENCIA_TESTE.S.d"

# o servidor de mentira (só nas páginas "com servidor"): as mesmas rotas do server.py, com as respostas de costume
SERVIDOR = r"""
(() => {
  const clone = x => JSON.parse(JSON.stringify(x));
  const srv = window.__srv = { pedidos: [], resp: Object.assign({}, window.__srvInicio || {}), segurar: {}, presos: [], ultimo: null, aCada20s: null };
  srv.d = { rev: 1, ajustes: {}, bancos: [], investimentos: [], lancamentos: [], recorrencias: [], historico: [],
    indices: { cdi: 13.65, selic: 13.75, ipca: 4.58, tr: 0.17, auto: true, fonte: 'padrao', atualizado_em: null, datas: {}, erro: null } };
  const estado = () => Object.assign(clone(srv.d), { usuario: 'Ana', integracao_ultimo: srv.ultimo });
  const dicas = () => [200, { dicas: [], assinaturas: [], conferindo: false, catalogo: ['Spotify'], dolar: null }];
  const bens = () => [200, { ok: false, motivo: 'O InventarIA não está instalado.' }];
  const padrao = {
    'GET api/state': () => [200, estado()],
    'PUT api/state': c => {
      if (c.rev !== srv.d.rev) return [409, estado()];
      for (const k of ['bancos', 'investimentos', 'ajustes', 'exemplo', 'lancamentos', 'recorrencias', 'categorias']) if (k in c) srv.d[k] = c[k];
      if (c.substituir_historico) srv.d.historico = c.historico || [];
      srv.d.rev++;
      return [200, estado()];
    },
    'PUT api/indices': c => {
      for (const k of ['cdi', 'selic', 'ipca', 'tr']) if (k in c) Object.assign(srv.d.indices, { [k]: c[k], fonte: 'manual' });
      if ('auto' in c) srv.d.indices.auto = !!c.auto;
      return [200, estado()];
    },
    'POST api/indices/atualizar': () => { Object.assign(srv.d.indices, { cdi: 14.15, fonte: 'bcb', atualizado_em: '2026-11-02T09:30:00-03:00', erro: null }); return [200, estado()]; },
    'POST api/backup': () => [200, { arquivo: 'gerencia-2026-11-02-1000.zip', pasta: 'share/gerencia' }],
    'POST api/importar': () => [200, estado()],
    'GET api/versoes': () => [200, []],
    'POST api/versoes/restaurar': () => [200, estado()],
    'POST api/fotos': () => [200, { arquivo: 'foto-1.jpg' }],
    'GET api/ia/status': () => [200, { pronta: true, entidades: [{ id: 'ai_task.ia_da_casa', nome: 'IA da Casa', imagens: true }], selecionada: '' }],
    'POST api/ia/ler': () => [200, { lancamentos: [], investimentos: [], entidade: 'ai_task.ia_da_casa' }],
    'GET api/dicas': dicas, 'POST api/dicas/conferir': dicas,
    'GET api/bens': bens, 'POST api/bens/atualizar': bens,
    'GET api/ia/uso': () => [200, { today: null, days: [] }],
    'GET api/voz/status': () => [200, { pronta: true, nome: 'Fala da Casa', selecionada: '',
      opcoes: [{ id: 'stt.fala_da_casa', nome: 'Fala da Casa', idioma: 'pt-BR', preferido: true }] }],
    'POST api/voz': () => [200, { texto: 'gastei 45 no mercado', nome: 'Fala da Casa' }],
    'GET api/backups': () => [200, []],
    'POST api/backups/restaurar': () => [200, estado()],
    'GET api/chat': () => [200, { mensagens: [] }],
    'POST api/chat': c => [200, { mensagens: [{ id: 'm1', papel: 'eu', texto: c.texto, fala: !!c.fala }, { id: 'm2', papel: 'ia', texto: 'Anotado.' }] }],
    'POST api/chat/acao': () => [200, { mensagens: [] }],
    'POST api/chat/limpar': () => [200, { mensagens: [] }],
    'GET api/rev': () => [200, { rev: srv.d.rev, integracao_ultimo: srv.ultimo }],
  };
  const corpoDe = b => {
    if (b == null) return null;
    if (typeof b === 'string') { try { return JSON.parse(b); } catch (e) { return b; } }
    if (b instanceof File) return { arquivo: b.name, tamanho: b.size, tipo: b.type };
    if (ArrayBuffer.isView(b)) return { bytes: b.byteLength, amostras: b.length };
    return String(b);
  };
  window.fetch = async (url, op = {}) => {
    const metodo = (op.method || 'GET').toUpperCase(), rota = String(url).split('?')[0], chave = metodo + ' ' + rota;
    const corpo = corpoDe(op.body);
    srv.pedidos.push({ metodo, rota, corpo, cabecalhos: op.headers || {}, cache: op.cache || '' });
    const responder = () => {
      const r = srv.resp[chave];
      const [status, json] = r ? [r.status || 200, r.corpo] : padrao[chave] ? padrao[chave](corpo) : [404, { erro: 'Rota não existe: ' + chave }];
      const txt = json === undefined ? '' : typeof json === 'string' ? json : JSON.stringify(json);
      return new Response(txt, { status, headers: { 'Content-Type': typeof json === 'string' ? 'text/html' : 'application/json' } });
    };
    if (srv.segurar[chave]) return new Promise(ok => srv.presos.push({ chave, ir: () => ok(responder()) }));
    return responder();
  };
  srv.soltar = chave => {
    delete srv.segurar[chave];
    const p = srv.presos.filter(x => x.chave === chave);
    srv.presos = srv.presos.filter(x => x.chave !== chave);
    p.forEach(x => x.ir());
    return p.length;
  };
  // o app confere a cada 20 s se outro app mudou algo: aqui o teste chama quando quiser
  const si = window.setInterval;
  window.setInterval = (fn, ms, ...a) => { if (ms === 20000) { srv.aCada20s = fn; return 0; } return si(fn, ms, ...a); };
})();
"""

# um pequeno PDF inventado (o conteúdo não importa: a IA é falsa nestes testes)
PDF = b"%PDF-1.4\n% recibo inventado\n%%EOF\n"

CDB = {"id": "cdb-azul", "nome": "CDB Azul", "banco": "b-azul", "tipo": "cdb", "valor": 10000, "data_valor": "2026-05-04", "indexador": "cdi_pct",
       "taxa": 100, "liquidez": "vencimento", "vencimento": "2028-01-10", "titular": "meu"}
RESERVA = {"id": "res-verde", "nome": "Reserva Verde", "banco": "b-verde", "tipo": "caixinha", "valor": 2000, "data_valor": "2026-11-02",
           "indexador": "parado", "taxa": 0, "liquidez": "diaria", "titular": "meu"}
CDB_BETO = {"id": "cdb-beto", "nome": "CDB do Beto", "banco": "b-azul", "tipo": "cdb", "valor": 700, "data_valor": "2026-11-02",
            "indexador": "parado", "taxa": 0, "liquidez": "vencimento", "titular": "terceiros", "terceiro": "Beto"}

# o dia a dia (restaurante): agosto 450, setembro 500 e outubro 900 (média dos 3 meses: 616,67)
RESTAURANTES = [{"id": f"rest{m}", "tipo": "despesa", "descricao": "Restaurante", "valor": v, "data": f"2026-{m:02d}-15", "pago": True,
                 "categoria": "c-restaurantes"} for m, v in ((7, 400), (8, 450), (9, 500), (10, 900))]

# bens do InventarIA como o servidor entrega (/api/bens), inventados
BENS = {"ok": True, "hoje": 30000, "registrado": 36000, "perde_ano": 4200, "n": 12, "versao": "1.18.0",
        "categorias": [{"id": "eletronicos", "nome": "Eletrônicos", "taxa": 20, "registrado": 16000, "hoje": 12000, "n": 5},
                       {"id": "moveis", "nome": "Móveis", "taxa": 10, "registrado": 20000, "hoje": 18000, "n": 7}],
        "comodos": [{"id": "sala", "nome": "Sala", "hoje": 20000, "n": 8}, {"id": "quarto", "nome": "Quarto", "hoje": 10000, "n": 4}]}
BENS_NOVOS = dict(BENS, hoje=31500, n=13)
# bens cadastrados aqui (tipo Bens): o carro da Carla (veículos) e os móveis da casa de praia, separados em duas categorias
CARRO = {"id": "carro-carla", "nome": "Carro da Carla", "banco": "", "tipo": "bens", "valor": 40000, "data_valor": "2026-11-02", "indexador": "deprecia",
         "taxa": 15, "categoria_bem": "veiculos", "liquidez": "diaria", "titular": "terceiros", "terceiro": "Carla"}
PRAIA = {"id": "moveis-praia", "nome": "Casa de praia", "banco": "", "tipo": "bens", "valor": 10000, "data_valor": "2026-11-02", "indexador": "deprecia",
         "taxa": 12, "categoria_bem": "varias", "liquidez": "diaria", "titular": "meu",
         "partes": [{"categoria": "moveis", "valor": 8000, "taxa": 10}, {"categoria": "eletronicos", "valor": 2000, "taxa": 20}]}

# o salário fixo da Ana (dia 5, 5.000 brutos, INSS de 11% na fonte) e o plano de saúde descontado dele (250 por mês)
SALARIO = {"id": "r-sal", "tipo": "receita", "descricao": "Salário", "valor": 5000, "dia": 5, "inicio": "2026-01", "conta": "k-verde", "categoria": "c-salario",
           "descontos": [{"id": "d-inss", "descricao": "INSS", "modo": "pct", "valor": 11, "base": "", "categoria": "c-impostos"}]}
PLANO = {"id": "r-plano", "tipo": "despesa", "descricao": "Plano de saúde", "valor": 250, "dia": 5, "inicio": "2026-01", "categoria": "c-saude", "vinculo": "r-sal"}
# o recibo de novembro: bruto 5.000, INSS 550 (11%), IR 300 (6%) e o plano agora de 300 (líquido 3.850)
HOLERITE = {"data": "2026-11-05", "creditos": [{"descricao": "Salário base", "valor": 5000}],
            "debitos": [{"descricao": "INSS", "valor": 550, "tipo": "imposto"}, {"descricao": "Imposto de renda", "valor": 300, "tipo": "imposto"},
                        {"descricao": "Plano de saúde", "valor": 300, "tipo": "saude"}],
            "total_creditos": 5000, "total_debitos": 1150, "liquido": 3850}

APORTE = {"id": "r-apo", "tipo": "despesa", "descricao": "Aporte mensal", "valor": 800, "dia": 10, "inicio": "2026-01", "aporte": True,
          "categoria": "c-investimentos", "conta": "k-verde"}


def _limpo(t):
    return " ".join(str(t or "").replace("\xa0", " ").split())


# Um Chromium só para o arquivo todo, com o microfone falso (cada classe abre a sua página num contexto novo)
_NAV = {}


def setUpModule():
    if sync_playwright:
        _NAV["pw"] = sync_playwright().start()
        _NAV["b"] = _NAV["pw"].chromium.launch(args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
                                                      "--autoplay-policy=no-user-gesture-required"])


def tearDownModule():
    if _NAV:
        _NAV.pop("b").close()
        _NAV.pop("pw").stop()


class TelaSistema(Tela):
    """A página da prévia (DEMO = True) ou com o servidor de mentira (DEMO = False), sem animação de janelas (reduzir movimento)."""
    DEMO = True
    MOVIMENTO = "reduce"
    TOQUE = False

    @classmethod
    def setUpClass(cls):
        cls.pw, cls.b = _NAV["pw"], _NAV["b"]
        cls.ctx = cls.b.new_context(timezone_id="America/Sao_Paulo", locale="pt-BR", viewport={"width": cls.LARGURA, "height": cls.ALTURA},
                                    reduced_motion=cls.MOVIMENTO, has_touch=cls.TOQUE, permissions=["microphone"])
        cls.erros = []
        cls.pg = cls.nova_pagina(cls.erros)
        cls.pg.wait_for_function(PRONTO)
        cls.pg.evaluate("window.__UI0 = JSON.stringify(window.GERENCIA_TESTE.S.ui)")

    @classmethod
    def nova_pagina(cls, erros, antes=""):
        """Uma página nova deste contexto, com o app aberto (antes: um script que roda antes de tudo)."""
        pg = cls.ctx.new_page()
        pg.set_default_timeout(5000)
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.clock.set_fixed_time("2026-11-02T10:00:00-03:00")
        pg.add_init_script(antes + ("window.GERENCIA_DEMO = true;" if cls.DEMO else SERVIDOR) + "window.GERENCIA_TESTE = true;")
        pg.goto(INDEX)
        return pg

    @classmethod
    def tearDownClass(cls):
        cls.ctx.close()

    def abrir(self, d=None, ui=None, bens=None):
        # um pedido de dicas agendado por um teste anterior não entra no meio deste
        self.js("(clearTimeout(T.dicasAgenda), clearTimeout(T.dicasTimer), true)")
        super().abrir(d, ui, bens)
        # a janela do teste anterior some na hora (o fundo escuro dela seguraria o primeiro toque)
        self.js("(T.FOLHA || (document.getElementById('folhas').innerHTML = ''), true)")

    def esperar_aviso(self, parte, ms=4000):
        """Espera o aviso (embaixo) com este texto e devolve o texto inteiro."""
        self.pg.wait_for_function("t => { const e = document.getElementById('toast'); return e.classList.contains('on') && e.textContent.includes(t); }",
                                  arg=parte, timeout=ms)
        return self.aviso()

    def trocar_api(self, nome, corpo_js):
        """Troca uma função da api por uma falsa (JavaScript) até o fim do teste."""
        self.js("(window.__api0 = window.__api0 || {}, (a[0] in window.__api0) || (window.__api0[a[0]] = T.api[a[0]]), "
                "T.api[a[0]] = new Function('return (' + a[1] + ')')(), true)", [nome, corpo_js])
        self.addCleanup(lambda: self.js("(T.api[a] = window.__api0[a], delete window.__api0[a], true)", nome))

    def linha(self, sel, contem):
        """O texto (espaços juntados) do primeiro elemento com este texto, ou None."""
        return self.js("(e => e ? e.innerText.replace(/\\s+/g, ' ').trim() : null)([...document.querySelectorAll(a[0])].find(e => e.innerText.includes(a[1])))",
                       [sel, contem])

    def limpo(self, sel):
        return _limpo(self.texto(sel))

    def galeria(self, sel):
        """Toca num botão que abre a escolha de arquivo; devolve a escolha aberta."""
        with self.pg.expect_file_chooser() as fc:
            self.pg.locator(sel).first.click()
        return fc.value


class TelaServidor(TelaSistema):
    """O app como no Home Assistant (apiServidor), com o servidor de mentira."""
    DEMO = False

    def setUp(self):
        self.js("(Object.assign(window.__srv, { resp: {}, segurar: {}, ultimo: null }), true)")

    def abrir(self, d=None, ui=None, bens=None):
        super().abrir(d, ui, bens)
        self.limpar_pedidos()

    def limpar_pedidos(self):
        self.js("(window.__srv.pedidos = [], true)")

    def pedidos(self, rota=None):
        """Os pedidos que a tela fez ao servidor ([metodo, rota]), em ordem; com rota, só os dela."""
        p = self.js("window.__srv.pedidos.map(p => [p.metodo, p.rota])")
        return [x for x in p if rota is None or x[1] == rota]

    def responder(self, chave, status=200, corpo=None):
        self.js("(window.__srv.resp[a[0]] = { status: a[1], corpo: a[2] === null ? undefined : a[2] }, true)", [chave, status, corpo])

    def segurar(self, chave):
        self.js("(window.__srv.segurar[a] = true)", chave)

    def soltar(self, chave):
        n = self.js("window.__srv.soltar(a)", chave)
        self.esperar()
        return n


# ---------------------------------------------------------------------------------------------------------------
class TestApiServidor(TelaServidor):
    """apiServidor e jsonOk: a rota, o método, o corpo e os cabeçalhos de cada pedido, e como os erros do servidor chegam."""

    CHAMADAS = [
        ("T.api.state()", "GET", "api/state", None),
        ("T.api.indices({ cdi: 14.15 })", "PUT", "api/indices", {"cdi": 14.15}),
        ("T.api.atualizarIndices()", "POST", "api/indices/atualizar", None),
        ("T.api.backup()", "POST", "api/backup", None),
        ("T.api.versoes()", "GET", "api/versoes", None),
        ("T.api.restaurar('v-2026-11-01')", "POST", "api/versoes/restaurar", {"nome": "v-2026-11-01"}),
        ("T.api.foto('data:image/jpeg;base64,AAAA')", "POST", "api/fotos", {"jpg": "data:image/jpeg;base64,AAAA"}),
        ("T.api.iaStatus()", "GET", "api/ia/status", None),
        ("T.api.iaLer({ modo: 'auto', texto: 'gastei 45 no mercado' })", "POST", "api/ia/ler", {"modo": "auto", "texto": "gastei 45 no mercado"}),
        ("T.api.dicas()", "GET", "api/dicas", None),
        ("T.api.dicasConferir()", "POST", "api/dicas/conferir", None),
        ("T.api.bens()", "GET", "api/bens", None),
        ("T.api.bensAtualizar()", "POST", "api/bens/atualizar", None),
        ("T.api.iaUso()", "GET", "api/ia/uso", None),
        ("T.api.vozStatus()", "GET", "api/voz/status", None),
        ("T.api.backups()", "GET", "api/backups", None),
        ("T.api.restaurarBackup('gerencia-2026-10-26-2105.zip')", "POST", "api/backups/restaurar", {"nome": "gerencia-2026-10-26-2105.zip"}),
        ("T.api.chat()", "GET", "api/chat", None),
        ("T.api.chatEnviar({ texto: 'oi', aba: 'inicio', fala: false })", "POST", "api/chat", {"texto": "oi", "aba": "inicio", "fala": False}),
        ("T.api.chatAcao('m2', 'lancamentos', 'feito')", "POST", "api/chat/acao", {"id": "m2", "grupo": "lancamentos", "estado": "feito"}),
        ("T.api.chatLimpar()", "POST", "api/chat/limpar", None),
    ]

    def ultimo(self):
        return self.js("window.__srv.pedidos[window.__srv.pedidos.length - 1]")

    def erro_de(self, chamada):
        """A mensagem do erro que a chamada dá (ou None, se não deu erro)."""
        return self.js(f"{chamada}.then(() => null, e => e.message)")

    def test_com_servidor_o_app_usa_a_api_do_servidor(self):
        self.abrir(base())
        self.assertTrue(self.js("T.api === T.apiServidor && !T.DEMO"))

    def test_cada_metodo_vai_na_rota_certa_com_o_corpo_certo(self):
        self.abrir(base())
        for chamada, metodo, rota, corpo in self.CHAMADAS:
            with self.subTest(chamada):
                self.limpar_pedidos()
                self.js(chamada)
                self.assertEqual(self.js("window.__srv.pedidos.length"), 1, "um pedido só")
                p = self.ultimo()
                self.assertEqual((p["metodo"], p["rota"], p["corpo"]), (metodo, rota, corpo))
                if corpo is not None:
                    self.assertEqual(p["cabecalhos"], {"Content-Type": "application/json"})
                if metodo == "GET":
                    self.assertEqual(p["cache"], "no-store", "o que o servidor guarda nunca vem do cache")

    def test_cada_metodo_devolve_o_que_o_servidor_respondeu(self):
        self.abrir(base())
        self.assertEqual(self.js("T.api.backup()"), {"arquivo": "gerencia-2026-11-02-1000.zip", "pasta": "share/gerencia"})
        self.assertEqual(self.js("T.api.iaStatus().then(s => s.entidades[0].nome)"), "IA da Casa")
        self.assertEqual(self.js("T.api.state().then(s => [s.usuario, s.rev])"), ["Ana", self.js("window.__srv.d.rev")])

    def test_salvar_manda_os_dados_e_devolve_o_novo_estado(self):
        self.abrir(base())
        rev = self.js("T.S.d.rev")
        r = self.js("T.api.save({ rev: a, bancos: [{ id: 'b-azul', nome: 'Banco Azul', cor: '#56AEFF', contas: [] }] })", rev)
        p = self.ultimo()
        self.assertEqual((p["metodo"], p["rota"], p["cabecalhos"]), ("PUT", "api/state", {"Content-Type": "application/json"}))
        self.assertEqual(p["corpo"], {"rev": rev, "bancos": [{"id": "b-azul", "nome": "Banco Azul", "cor": "#56AEFF", "contas": []}]})
        self.assertEqual((r["rev"], r["bancos"][0]["nome"]), (rev + 1, "Banco Azul"))

    def test_salvar_com_revisao_velha_da_conflito_com_os_dados_de_agora(self):
        self.abrir(base(bancos=BANCOS))
        rev = self.js("T.S.d.rev")
        e = self.js("T.api.save({ rev: a - 1, bancos: [] }).then(() => null, e => ({ m: e.message, c: e.conflito, rev: e.d.rev, b: e.d.bancos.map(b => b.nome) }))", rev)
        self.assertEqual(e, {"m": "conflito", "c": True, "rev": rev, "b": ["Banco Azul", "Banco Verde"]}, "o erro traz o que está salvo agora")
        self.assertEqual(self.js("window.__srv.d.bancos.length"), 2, "nada mudou no servidor")

    def test_erro_do_servidor_chega_com_a_mensagem_dele(self):
        self.abrir(base())
        self.responder("GET api/state", 500, {"erro": "Disco cheio"})
        self.responder("PUT api/state", 500, {"erro": "Disco cheio"})
        self.responder("POST api/ia/ler", 429, {"erro": "A IA do Home Assistant passou da cota de hoje."})
        self.assertEqual(self.erro_de("T.api.state()"), "Disco cheio")
        self.assertEqual(self.erro_de("T.api.save({ rev: T.S.d.rev })"), "Disco cheio", "no salvar, um erro que não é conflito também")
        self.assertEqual(self.erro_de("T.api.iaLer({ texto: 'x' })"), "A IA do Home Assistant passou da cota de hoje.")

    def test_erro_sem_mensagem_vira_erro_com_o_numero(self):
        self.abrir(base())
        self.responder("GET api/dicas", 502)  # sem corpo (o proxy do Home Assistant caiu)
        self.responder("GET api/bens", 404, "<html>Não encontrado</html>")  # uma página, não JSON
        self.responder("GET api/backups", 500, {"detalhe": "sem a chave erro"})
        self.assertEqual(self.erro_de("T.api.dicas()"), "Erro 502")
        self.assertEqual(self.erro_de("T.api.bens()"), "Erro 404")
        self.assertEqual(self.erro_de("T.api.backups()"), "Erro 500")

    def test_ler_com_ia_e_conversar_zeram_o_relogio_do_uso_mesmo_com_erro(self):
        self.abrir(base())
        self.js("(T.S.usoEm = 12345, true)")
        self.js("T.api.iaLer({ texto: 'x' })")
        self.assertEqual(self.js("T.S.usoEm"), 0, "o uso da IA é buscado de novo na próxima vez")
        self.responder("POST api/chat", 500, {"erro": "A IA não respondeu."})
        self.js("(T.S.usoEm = 12345, true)")
        self.assertEqual(self.erro_de("T.api.chatEnviar({ texto: 'oi' })"), "A IA não respondeu.")
        self.assertEqual(self.js("T.S.usoEm"), 0)

    def test_importar_manda_o_arquivo_com_o_nome_no_cabecalho(self):
        self.abrir(base())
        self.js("T.api.importar(new File(['{\"bancos\": []}'], 'gerência de março.json', { type: 'application/json' }))")
        p = self.ultimo()
        self.assertEqual((p["metodo"], p["rota"]), ("POST", "api/importar"))
        self.assertEqual(p["cabecalhos"], {"X-Nome-Arquivo": "ger%C3%AAncia%20de%20mar%C3%A7o.json"}, "o nome com acento vai codificado")
        self.assertEqual(p["corpo"], {"arquivo": "gerência de março.json", "tamanho": 14, "tipo": "application/json"}, "o arquivo vai inteiro")

    def test_fala_manda_o_audio_cru(self):
        self.abrir(base())
        r = self.js("T.api.vozTexto(new Int16Array(16000))")
        p = self.ultimo()
        self.assertEqual((p["metodo"], p["rota"], p["cabecalhos"]), ("POST", "api/voz", {"Content-Type": "application/octet-stream"}))
        self.assertEqual(p["corpo"], {"bytes": 32000, "amostras": 16000}, "1 s em 16 kHz, 16 bits")
        self.assertEqual(r, {"texto": "gastei 45 no mercado", "nome": "Fala da Casa"})


# ---------------------------------------------------------------------------------------------------------------
class TestAbrirComServidor(TelaServidor):
    """Abrir o app quando o servidor não entrega os dados (iniciar)."""

    def pagina_com_erro(self, status, corpo):
        """Uma página nova em que o primeiro GET api/state dá erro (o recarregar, não: window.name continua de uma carga para a outra)."""
        erros = []
        falha = json.dumps({"GET api/state": {"status": status, "corpo": corpo}})
        pg = self.nova_pagina(erros, f"if (window.name !== 'falhou') {{ window.name = 'falhou'; window.__srvInicio = {falha}; }}")
        self.addCleanup(pg.close)
        pg.wait_for_function("document.querySelector('#app .vazio')")
        return pg, erros

    def test_sem_os_dados_explica_e_tentar_de_novo_recarrega(self):
        pg, erros = self.pagina_com_erro(500, {"erro": "Disco cheio"})
        self.assertEqual(pg.inner_text("#app .vazio").split("\n")[:2], ["Não consegui abrir os dados.", "Disco cheio"])
        self.assertEqual(pg.inner_text("#app .vazio button"), "Tentar de novo")
        self.assertFalse(pg.evaluate("!!window.GERENCIA_TESTE.S.d"), "sem dados, nada mais é desenhado")
        with pg.expect_navigation():
            pg.click("#app .vazio button")
        pg.wait_for_function(PRONTO)
        self.assertEqual(pg.evaluate("window.GERENCIA_TESTE.S.usuario"), "Ana", "na segunda vez abriu")
        self.assertEqual(pg.locator("#app .vazio").count(), 0)
        self.assertEqual(erros, [])

    def test_erro_sem_mensagem_mostra_o_numero(self):
        pg, erros = self.pagina_com_erro(502, None)
        self.assertEqual(pg.inner_text("#app .vazio").split("\n")[:2], ["Não consegui abrir os dados.", "Erro 502"])
        self.assertEqual(erros, [])


# ---------------------------------------------------------------------------------------------------------------
class TestTelaComServidor(TelaServidor):
    """O que só aparece com o servidor: a situação da IA, exportar e backups, importar, outro app mudando os dados."""

    def test_ia_aparece_verificando_e_depois_pronta(self):
        self.segurar("GET api/ia/status")
        self.segurar("GET api/voz/status")
        self.abrir(base(), ui={"tab": "mais", "maisTela": "bancos"})
        self.js("(T.S.voz = null, true)")  # como na primeira vez, antes de o assistente de voz responder
        self.ir_mais("config", "integracoes")
        st = self.textos("#ia .status")
        self.assertEqual(st, ["Verificando a IA do Home Assistant…", "Falar: verificando o assistente de voz…"])
        self.assertEqual(self.js("[...document.querySelectorAll('#ia .status')].map(e => e.className)"), ["status manual", "status manual"])
        self.clicar('#ia [data-a="ia-verificar"]')  # Verificar de novo, ainda esperando
        self.assertEqual(self.pedidos("api/voz/status"), [["GET", "api/voz/status"]], "Verificar de novo pergunta também pela fala")
        self.assertEqual(self.soltar("GET api/voz/status"), 1)
        self.assertGreaterEqual(self.soltar("GET api/ia/status"), 2, "o pedido de quando abriu e o do Verificar de novo")
        self.assertEqual(self.esperar_aviso("IA"), "IA pronta")
        st = [_limpo(t) for t in self.textos("#ia .status")]
        self.assertEqual(st[0], "Pronta. Usando a IA padrão do Home Assistant.")
        self.assertEqual(st[1], "Falar: pronto. A voz vira texto com “Fala da Casa”; quem entende e separa os lançamentos é a IA usada pelo app. "
                                "O microfone fica no alto de cada tela.")
        self.assertEqual(self.js("[...document.querySelectorAll('#ia-ent option')].map(o => o.textContent)"), ["Padrão do Home Assistant", "IA da Casa"])

    def test_mais_pede_a_situacao_da_ia_uma_vez_so(self):
        """Enquanto o Home Assistant não responde, redesenhar Mais não pede de novo (até a 1.24.3 pedia a cada vez)."""
        self.segurar("GET api/ia/status")
        self.abrir(base(), ui={"tab": "mais", "maisTela": "bancos"})
        self.js("(T.S.ia = null, T.S.iaPedido = false, true)")
        self.limpar_pedidos()
        for _ in range(3):
            self.js("(T.render(), true)")
        self.assertEqual(self.pedidos("api/ia/status"), [["GET", "api/ia/status"]])
        self.soltar("GET api/ia/status")
        self.assertIsNotNone(self.js("T.S.ia"), "a resposta chega e fica guardada")

    def test_ia_escolhida_aparece_pelo_nome(self):
        self.abrir(base(ajustes={"corrigir": True, "ia_entidade": "ai_task.ia_da_casa"}), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"})
        self.responder("GET api/ia/status", 200, {"pronta": True, "entidades": [{"id": "ai_task.ia_da_casa", "nome": "IA da Casa", "imagens": False}],
                                                  "selecionada": "ai_task.ia_da_casa"})
        self.clicar('#ia [data-a="ia-verificar"]')
        self.esperar_aviso("IA pronta")
        self.assertEqual(self.limpo("#ia .status"), "Pronta. Usando IA da Casa.")
        self.assertEqual(self.js("document.querySelector('#ia-ent').selectedOptions[0].textContent"), "IA da Casa (só texto)")

    def test_ia_nao_pronta_mostra_o_motivo(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"})
        self.responder("GET api/ia/status", 200, {"pronta": False, "motivo": "Nenhuma IA configurada no Home Assistant.", "entidades": []})
        self.responder("GET api/voz/status", 200, {"pronta": False, "motivo": "nenhum assistente com fala para texto."})
        self.clicar('#ia [data-a="ia-verificar"]')
        self.assertEqual(self.esperar_aviso("Nenhuma"), "Nenhuma IA configurada no Home Assistant.")
        self.assertEqual(self.js("[...document.querySelectorAll('#ia .status')].map(e => [e.className, e.textContent])"),
                         [["status erro", "Nenhuma IA configurada no Home Assistant."], ["status manual", "Falar: nenhum assistente com fala para texto."]])
        self.assertEqual(self.conta('#app .cab-topo [data-a="falar"]'), 0, "sem a IA pronta, o microfone do alto some")

    # (era bug até a 1.28.0: a fala para texto pronta e a IA não, a linha dizia "Falar: pronto… O microfone fica no alto de cada tela", sem microfone)
    def test_falar_nao_diz_pronto_sem_a_ia_pronta(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"})
        self.responder("GET api/ia/status", 200, {"pronta": False, "motivo": "Nenhuma IA configurada no Home Assistant.", "entidades": []})
        self.clicar('#ia [data-a="ia-verificar"]')
        self.esperar_aviso("Nenhuma")
        self.assertEqual(self.js("T.S.voz.pronta"), True, "a fala para texto está pronta")
        self.assertEqual(self.js("[...document.querySelectorAll('#ia .status')].map(e => [e.className, e.textContent])"),
                         [["status erro", "Nenhuma IA configurada no Home Assistant."], ["status manual", "Falar: só com a IA pronta."]])
        self.assertEqual(self.conta('#app [data-a="falar"]'), 0, "e o microfone não aparece")

    def test_verificar_de_novo_com_o_servidor_fora_avisa(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"})
        self.responder("GET api/ia/status", 502)
        self.clicar('#ia [data-a="ia-verificar"]')
        self.assertEqual(self.esperar_aviso("Erro"), "Erro 502")

    def test_exportar_baixa_do_servidor_e_backups_carregam(self):
        self.segurar("GET api/backups")
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        links = self.js("[...document.querySelectorAll('#exportar a.btn')].map(a => [a.getAttribute('href'), a.hasAttribute('download'), a.textContent.trim()])")
        self.assertEqual(links, [["api/export/lancamentos", True, "Baixar CSV"], ["api/export/csv", True, "Baixar CSV"],
                                 ["api/export/json", True, "Baixar JSON"], ["api/export/zip", True, "Baixar ZIP"]])
        self.assertEqual(self.limpo("#backup .status"), "Carregando backups…")
        self.responder("GET api/backups", 200, [{"nome": "gerencia-2026-11-01-2105.zip", "tamanho": 182000, "quando": "2026-11-01T21:05:00-03:00"},
                                                {"nome": "gerencia-2026-10-25-2105.zip", "tamanho": 2621440, "quando": "2026-10-25T21:05:00-03:00"}])
        self.soltar("GET api/backups")
        self.assertEqual([_limpo(t) for t in self.textos("#backup .bk-row > div")],
                         ["01/11/2026 às 21:05 178 KB · gerencia-2026-11-01-2105.zip", "25/10/2026 às 21:05 2,5 MB · gerencia-2026-10-25-2105.zip"])

    def test_restaurar_backup_troca_os_dados(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        self.js("(T.S.backups = [{ nome: 'gerencia-2026-11-01-2105.zip', tamanho: 182000, quando: '2026-11-01T21:05:00-03:00' }], T.render(), true)")
        restaurado = dict(base(), rev=40, bancos=[BANCOS[1]], usuario="Ana")
        self.responder("POST api/backups/restaurar", 200, restaurado)
        self.clicar('#backup [data-a="bk-restaurar"]')
        self.assertEqual(self.folha(), "Restaurar backup?")
        self.assertIn("gerencia-2026-11-01-2105.zip", self.folha_texto())
        self.clicar('#folhas [data-a="confirmar"]')
        self.assertEqual(self.esperar_aviso("restaurado"), "Backup restaurado")
        self.assertEqual(self.js("window.__srv.pedidos.filter(p => p.rota === 'api/backups/restaurar').map(p => p.corpo)"), [{"nome": "gerencia-2026-11-01-2105.zip"}])
        self.assertEqual(([b["nome"] for b in self.dados()["bancos"]], self.dados()["rev"]), (["Banco Verde"], 40))

    def test_restaurar_backup_com_erro_avisa_e_nao_muda_nada(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        self.js("(T.S.backups = [{ nome: 'gerencia-2026-11-01-2105.zip', tamanho: 182000, quando: '2026-11-01T21:05:00-03:00' }], T.render(), true)")
        self.responder("POST api/backups/restaurar", 400, {"erro": "Esse backup está corrompido."})
        self.clicar('#backup [data-a="bk-restaurar"]')
        self.clicar('#folhas [data-a="confirmar"]')
        self.assertEqual(self.esperar_aviso("restaurar"), "Não consegui restaurar. Esse backup está corrompido.")
        self.assertEqual(len(self.dados()["bancos"]), 2)

    def test_importar_troca_os_dados_e_volta_para_o_inicio(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        self.responder("POST api/importar", 200, dict(base(), rev=7, bancos=BANCOS, usuario="Ana"))
        self.galeria('#importar [data-a="importar"]').set_files({"name": "gerência 2026.zip", "mimeType": "application/zip", "buffer": b"PK\x03\x04 inventado"})
        self.esperar()
        self.assertEqual(self.folha(), "Importar arquivo?")
        self.assertIn("gerência 2026.zip", self.folha_texto())
        self.assertEqual(self.pedidos("api/importar"), [], "só importa depois de confirmar")
        self.clicar('#folhas [data-a="confirmar"]')
        self.assertEqual(self.esperar_aviso("importados"), "Dados importados")
        p = self.js("window.__srv.pedidos.find(p => p.rota === 'api/importar')")
        self.assertEqual((p["cabecalhos"], p["corpo"]["tamanho"]), ({"X-Nome-Arquivo": "ger%C3%AAncia%202026.zip"}, 14))
        self.assertEqual((self.js("T.S.ui.tab"), [b["nome"] for b in self.dados()["bancos"]]), ("inicio", ["Banco Azul", "Banco Verde"]))
        self.assertEqual(self.js("document.getElementById('arquivo').value"), "", "o mesmo arquivo pode ser escolhido de novo")

    def test_importar_com_erro_avisa(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        self.responder("POST api/importar", 400, {"erro": "Esse arquivo não é um backup do GerencIA."})
        self.galeria('#importar [data-a="importar"]').set_files({"name": "fotos.zip", "mimeType": "application/zip", "buffer": b"PK"})
        self.esperar()
        self.clicar('#folhas [data-a="confirmar"]')
        self.assertEqual(self.esperar_aviso("importar"), "Não consegui importar. Esse arquivo não é um backup do GerencIA.")
        self.assertEqual((self.js("T.S.ui.tab"), len(self.dados()["bancos"])), ("mais", 2))

    def test_desistir_de_escolher_o_arquivo_nao_abre_nada(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        self.js("(document.getElementById('arquivo').dispatchEvent(new Event('change')), true)")
        self.esperar()
        self.assertIsNone(self.folha())

    def outro_app_pagou_a_luz(self):
        """O CronologIA dá baixa na luz (Paguei): o servidor muda e a revisão sobe."""
        self.js("""(() => { const s = window.__srv; s.d.lancamentos = s.d.lancamentos.map(l => l.id === 'l-luz' ? Object.assign({}, l, { pago: true }) : l);
            s.d.rev++; s.ultimo = { app: 'CronologIA', em: '2026-11-02T09:15:00-03:00' }; return true; })()""")

    def test_conta_paga_em_outro_app_aparece_sozinha(self):
        luz = {"id": "l-luz", "tipo": "despesa", "descricao": "Luz", "valor": 180, "data": "2026-11-01", "pago": False, "categoria": "c-contas"}
        self.abrir(base(lancamentos=[luz]), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"})
        self.assertEqual(self.limpo("#outros-apps .status"), "Nenhum app conectou ainda.")
        self.outro_app_pagou_a_luz()
        self.js("(window.__srv.aCada20s(), true)")
        self.pg.wait_for_function("window.GERENCIA_TESTE.S.d.lancamentos[0].pago === true")
        self.esperar()
        self.assertEqual(self.pedidos(), [["GET", "api/rev"], ["GET", "api/state"]])
        self.assertEqual(self.limpo("#outros-apps .status"), "CronologIA usou hoje às 09:15.")
        self.assertEqual(self.js("T.S.d.rev"), self.js("window.__srv.d.rev"))

    def test_sem_mudanca_so_confere_a_revisao(self):
        self.abrir(base())
        self.js("(window.__srv.aCada20s(), true)")
        self.esperar()
        self.assertEqual(self.pedidos(), [["GET", "api/rev"]], "a mesma revisão: não busca os dados de novo")

    def test_com_janela_aberta_ou_tela_escondida_nao_confere(self):
        self.abrir(base())
        self.clicar('#nav [data-a="novo"]')
        self.assertEqual(self.folha(), "Adicionar")
        self.js("(window.__srv.aCada20s(), true)")
        self.esperar()
        self.assertEqual(self.pedidos(), [], "não troca os dados com uma janela aberta")
        self.voltar()
        self.js("(Object.defineProperty(document, 'hidden', { value: true, configurable: true }), window.__srv.aCada20s(), true)")
        self.addCleanup(lambda: self.js("(delete document.hidden, true)"))
        self.esperar()
        self.assertEqual(self.pedidos(), [], "nem com o app escondido (outra aba, tela apagada)")

    def test_voltar_para_o_app_busca_os_dados_de_novo(self):
        luz = {"id": "l-luz", "tipo": "despesa", "descricao": "Luz", "valor": 180, "data": "2026-11-01", "pago": False, "categoria": "c-contas"}
        self.abrir(base(lancamentos=[luz]))
        self.outro_app_pagou_a_luz()
        self.js("(document.dispatchEvent(new Event('visibilitychange')), true)")
        self.pg.wait_for_function("window.GERENCIA_TESTE.S.d.lancamentos[0].pago === true")
        self.esperar()
        self.assertEqual(self.pedidos(), [["GET", "api/state"]])

    def test_voltar_para_o_app_com_janela_aberta_nao_troca_os_dados(self):
        self.abrir(base())
        self.clicar('#nav [data-a="novo"]')
        self.js("(document.dispatchEvent(new Event('visibilitychange')), true)")
        self.esperar()
        self.assertEqual(self.pedidos(), [])

    def test_indices_de_partida_e_digitados_a_mao(self):
        d = base()
        del d["indices"]  # sem mexer nos índices do servidor
        self.js("(Object.assign(window.__srv.d.indices, { fonte: 'padrao', atualizado_em: null, erro: null }), true)")
        self.abrir(d, ui={"tab": "mais", "maisTela": "invest"})
        self.assertEqual(self.limpo("#indices .status"), "Valores de partida (outubro de 2026).")
        self.clicar('#indices [data-a="indice"][data-v="cdi"]')
        self.preencher("#i-v", "14,4")
        self.clicar('#folhas [data-a="i-salvar"]')
        self.assertEqual(self.esperar_aviso("Índice"), "Índice atualizado")
        self.assertEqual(self.js("window.__srv.pedidos.filter(p => p.rota === 'api/indices').map(p => p.corpo)"), [{"cdi": 14.4}])
        self.assertEqual(self.limpo("#indices .status"), "Valores digitados à mão.")
        self.assertEqual(self.limpo('#indices [data-v="cdi"] .vl'), "14,4%")

    # (era bug até a 1.28.0: com Atualizar sozinho desligado, o alto dizia "Esperando os índices do Banco Central", que não vinham)
    def test_sem_atualizar_sozinho_o_alto_nao_espera_o_banco_central(self):
        d = base()
        del d["indices"]  # sem mexer nos índices do servidor
        self.js("(Object.assign(window.__srv.d.indices, { auto: true, fonte: 'padrao', atualizado_em: null, erro: null }), true)")
        self.addCleanup(lambda: self.js("(window.__srv.d.indices.auto = true)"))
        self.abrir(d, ui={"tab": "mais", "maisTela": "invest"})
        self.assertEqual(self.limpo("#app .sync"), "Esperando os índices do Banco Central")
        self.clicar('#indices [data-a="indices-auto"]')
        self.assertEqual(self.js("T.S.d.indices.auto"), False)
        self.assertEqual(self.limpo("#app .sync"), "Índices de partida (outubro de 2026)")
        self.assertEqual(self.limpo("#indices .status"), "Valores de partida (outubro de 2026).")
        self.ir("inicio")
        self.assertEqual(self.limpo("#app .sync"), "Índices de partida (outubro de 2026)", "no alto das outras telas também")

    def test_indices_do_banco_central_fora_do_ar(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "invest"})
        fora = dict(base(), rev=self.js("T.S.d.rev"), usuario="Ana")
        fora["indices"] = dict(fora["indices"], fonte="bcb", atualizado_em="2026-11-01T21:00:00-03:00", erro="O Banco Central não respondeu")
        self.responder("POST api/indices/atualizar", 200, fora)
        self.clicar('#indices [data-a="indices-atualizar"]')
        self.assertEqual(self.esperar_aviso("Banco Central"), "Banco Central não respondeu. Mantive os valores.")
        self.assertEqual(self.js("(e => [e.className, e.textContent])(document.querySelector('#indices .status'))"),
                         ["status erro", "O Banco Central não respondeu. Usando os últimos valores."])


# ---------------------------------------------------------------------------------------------------------------
class TestTemaDoHomeAssistant(TelaServidor):
    """Tema Automático dentro do Home Assistant: segue o tema do HA (darkMode); fora dele, o do aparelho."""

    def dentro_do_ha(self, dark_mode):
        """Finge que o app está num iframe do Home Assistant com este darkMode (o parent tem o <home-assistant>)."""
        self.js("(window.parent = { document: { querySelector: s => s === 'home-assistant' ? { hass: { themes: { darkMode: a } } } : null } }, true)", dark_mode)
        self.addCleanup(lambda: self.js("(window.parent = window, true)"))

    def automatico(self):
        self.clicar('#tema [data-a="tema"][data-v="auto"]')
        return self.js("document.documentElement.dataset.theme")

    def test_segue_o_modo_escuro_e_o_claro_do_home_assistant(self):
        self.abrir(base(ajustes={"corrigir": True, "tema": "claro"}), ui={"tab": "mais", "maisTela": "config", "maisAba": "aparencia"})
        self.pg.emulate_media(color_scheme="light")
        self.addCleanup(lambda: self.pg.emulate_media(color_scheme="no-preference"))
        self.dentro_do_ha(True)
        self.assertEqual(self.automatico(), "dark", "o HA escuro manda, mesmo com o aparelho claro")
        self.assertEqual(self.dados()["ajustes"]["tema"], "auto")
        self.dentro_do_ha(False)
        self.assertEqual(self.js("(T.aplicarTema(), document.documentElement.dataset.theme)"), "light")

    def test_sem_o_home_assistant_segue_o_aparelho(self):
        self.abrir(base(ajustes={"corrigir": True, "tema": "escuro"}), ui={"tab": "mais", "maisTela": "config", "maisAba": "aparencia"})
        self.pg.emulate_media(color_scheme="light")
        self.addCleanup(lambda: self.pg.emulate_media(color_scheme="no-preference"))
        self.assertEqual(self.automatico(), "light", "fora de um iframe: o tema do aparelho")
        self.pg.emulate_media(color_scheme="dark")
        self.pg.wait_for_function("document.documentElement.dataset.theme === 'dark'", timeout=3000)  # o aparelho mudou para escuro: o app acompanha

    def test_home_assistant_sem_dark_mode_ou_bloqueado_segue_o_aparelho(self):
        self.abrir(base(ajustes={"corrigir": True, "tema": "escuro"}), ui={"tab": "mais", "maisTela": "config", "maisAba": "aparencia"})
        self.pg.emulate_media(color_scheme="light")
        self.addCleanup(lambda: self.pg.emulate_media(color_scheme="no-preference"))
        self.dentro_do_ha(None)  # o HA ainda não carregou o tema
        self.assertEqual(self.automatico(), "light")
        # outro endereço (o navegador não deixa ler a página de fora): também segue o aparelho, sem erro
        self.js("(window.parent = { get document() { throw new DOMException('Blocked a frame', 'SecurityError'); } }, true)")
        self.pg.emulate_media(color_scheme="dark")
        self.assertEqual(self.js("(T.aplicarTema(), document.documentElement.dataset.theme)"), "dark")

    def test_claro_e_escuro_escolhidos_nao_seguem_o_home_assistant(self):
        self.abrir(base(ajustes={"corrigir": True, "tema": "auto"}), ui={"tab": "mais", "maisTela": "config", "maisAba": "aparencia"})
        self.dentro_do_ha(True)
        self.clicar('#tema [data-a="tema"][data-v="claro"]')
        self.assertEqual(self.js("document.documentElement.dataset.theme"), "light")
        self.dentro_do_ha(False)
        self.clicar('#tema [data-a="tema"][data-v="escuro"]')
        self.assertEqual(self.js("document.documentElement.dataset.theme"), "dark")


# ---------------------------------------------------------------------------------------------------------------
class TestCorDoDiaComOAppAberto(TelaSistema):
    """Com o app aberto, a Cor do dia confere a cada minuto se o dia virou (o relógio de 1 min fica em __aCadaMinuto)."""

    MINUTO = "(() => { const si = window.setInterval; window.setInterval = (fn, ms, ...a) => { if (ms === 60000) { window.__aCadaMinuto = fn; return 0; } return si(fn, ms, ...a); }; })();"

    def test_o_relogio_de_um_minuto_troca_a_cor_quando_o_dia_vira(self):
        erros = []
        pg = self.nova_pagina(erros, self.MINUTO)
        self.addCleanup(pg.close)
        pg.wait_for_function(PRONTO)
        acento = lambda: pg.evaluate("document.documentElement.style.getPropertyValue('--accent')")
        self.assertEqual(acento(), "#FFA23E", "02/11/2026: Laranja")
        pg.evaluate("window.__aCadaMinuto()")
        self.assertEqual(acento(), "#FFA23E", "o mesmo dia: a mesma cor")
        pg.clock.set_fixed_time("2026-11-03T00:00:20-03:00")
        pg.evaluate("window.__aCadaMinuto()")
        self.assertEqual(acento(), "#F2C14E", "virou o dia: Ouro, sem recarregar")
        self.assertEqual(erros, [])


# ---------------------------------------------------------------------------------------------------------------
class TestPrevia(TelaSistema):
    """A prévia (apiDemo): o que ela não faz avisa, e o que ela simula responde como o servidor."""

    def test_restaurar_backup_na_previa_explica(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        self.pg.wait_for_selector("#backup .bk-row")
        self.assertEqual(self.conta("#backup .bk-row"), 3)
        self.clicar('#backup [data-a="bk-restaurar"]')
        self.assertEqual(self.folha(), "Restaurar backup?")
        self.clicar('#folhas [data-a="confirmar"]')
        self.assertEqual(self.esperar_aviso("backups"), "Não consegui restaurar. Na prévia não dá para restaurar backups.")
        self.assertEqual(len(self.dados()["bancos"]), 2, "nada mudou")

    def test_restaurar_versao_na_previa_explica(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        self.clicar('#versoes [data-a="versoes"]')
        self.pg.wait_for_selector("#folhas .versao-row")
        self.assertEqual(self.conta("#folhas .versao-row"), 3)
        self.clicar('#folhas [data-a="restaurar"]')
        self.assertEqual((self.folha(), self.niveis()), ("Restaurar esta versão?", 2), "a confirmação abre por cima da lista")
        self.clicar('#folhas [data-a="confirmar"]')
        self.assertEqual(self.esperar_aviso("versões"), "Na prévia não dá para restaurar versões.")

    def test_importar_na_previa_explica(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "config", "maisAba": "dados"})
        self.galeria('#importar [data-a="importar"]').set_files({"name": "gerencia.json", "mimeType": "application/json", "buffer": b'{"bancos": []}'})
        self.esperar()
        self.assertEqual(self.folha(), "Importar arquivo?")
        self.assertEqual(self.limpo("#folhas .folha p"), "Os dados de agora são trocados pelos de gerencia.json. Antes, o app guarda uma cópia do que existe hoje.")
        self.clicar('#folhas [data-a="confirmar"]')
        self.assertEqual(self.esperar_aviso("importar"), "Não consegui importar. Na prévia não dá para importar arquivos.")
        self.assertEqual(len(self.dados()["bancos"]), 2)

    def test_atualizar_indices_busca_e_mostra_a_hora_do_banco_central(self):
        ind = {"cdi": 12.0, "selic": 12.25, "ipca": 4.0, "tr": 0.1}
        self.abrir(base(indices=ind), ui={"tab": "mais", "maisTela": "invest"})
        self.clicar('#indices [data-a="indices-atualizar"]')
        b = self.pg.locator('#indices [data-a="indices-atualizar"]')
        self.assertEqual((b.inner_text().strip(), b.is_disabled()), ("Buscando…", True), "enquanto busca, o botão espera")
        self.assertEqual(self.esperar_aviso("Índices"), "Índices atualizados")
        self.assertEqual(self.js("(e => [e.classList.contains('manual') || e.classList.contains('erro'), e.textContent])(document.querySelector('#indices .status'))"),
                         [False, "Atualizado pelo Banco Central em 02/11/2026 às 10:00."], "sem o tom de aviso")
        self.assertEqual([_limpo(t) for t in self.textos("#indices .idx-row .vl")], ["13,65%", "13,75%", "4,58%", "0,17%"], "os índices de partida")
        self.assertEqual(self.limpo('#indices [data-a="indices-atualizar"]'), "Atualizar agora")

    def test_atualizar_indices_sem_internet_avisa_e_volta_o_botao(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "invest"})
        self.trocar_api("atualizarIndices", "async () => { throw new Error('Sem internet.'); }")
        self.clicar('#indices [data-a="indices-atualizar"]')
        self.assertEqual(self.esperar_aviso("atualizar"), "Não consegui atualizar. Sem internet.")
        self.assertFalse(self.pg.locator('#indices [data-a="indices-atualizar"]').is_disabled())
        self.assertEqual(self.limpo('#indices [data-a="indices-atualizar"]'), "Atualizar agora")

    def test_conferir_dicas_agora_na_previa(self):
        spotify = {"id": "r-spot", "tipo": "despesa", "descricao": "Spotify", "valor": 23.9, "dia": 22, "inicio": "2026-01", "conta": "k-ana", "cartao": True,
                   "categoria": "c-assinaturas"}
        self.abrir(base(bancos=BANCOS, recorrencias=[spotify]), ui={"tab": "mais", "maisTela": "caixa"})
        self.js("T.carregarDicas()")
        self.esperar()
        self.clicar('#dicas [data-a="dicas-conferir"]')
        b = self.pg.locator('#dicas [data-a="dicas-conferir"]')
        self.assertEqual((_limpo(b.inner_text()), b.is_disabled()), ("Conferindo…", True))
        self.pg.wait_for_function("!document.querySelector('#dicas [data-a=\"dicas-conferir\"]').disabled", timeout=4000)
        self.assertEqual(self.js("T.S.dicas.assinaturas.map(a => a.descricao)"), ["Spotify"])
        self.assertEqual(self.limpo('#dicas [data-a="dicas-conferir"]'), "Conferir agora")

    def test_verificar_a_ia_na_previa(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"})
        self.assertEqual(self.textos("#ia .status"), ["Na prévia, a leitura por IA é simulada.", "Falar: na prévia, a fala é simulada."])
        self.clicar('#ia [data-a="ia-verificar"]')
        self.assertEqual(self.esperar_aviso("IA"), "IA pronta")
        self.assertEqual(self.js("T.S.ia.pronta"), True)

    def test_atualizar_os_bens_na_previa_traz_os_bens_simulados(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"}, bens={"ok": False, "motivo": "O InventarIA não respondeu."})
        self.clicar('#bens [data-a="bens-atualizar"]')
        self.assertTrue(self.js("T.S.bens.ok && T.S.bens.n > 0"))
        self.assertRegex(self.limpo("#bens .linha-sw span"), r"^Ligado: R\$ [\d.]+ em \d+ itens\.$")

    def test_leitura_e_fala_simuladas_respondem_como_o_servidor(self):
        self.abrir(base(bancos=BANCOS, investimentos=[CDB, RESERVA]))
        r = self.js("""Promise.all([T.api.iaLer({ modo: 'holerite', anexo: { b64: 'x' } }), T.api.iaLer({ modo: 'auto', dica: 'caixa', texto: 'gastei 30 na farmácia' }),
            T.api.iaLer({ modo: 'invest', texto: 'apliquei 2 mil num cdb' }), T.api.iaLer({ modo: 'auto', dica: 'invest', texto: 'olha isso' }),
            T.api.vozTexto(new Int16Array(16000)), T.api.iaLer({ modo: 'auto', dica: 'caixa', texto: 'gastei 45 no mercado e recebi 150 do Beto pelo pix' })])
            .then(([h, cx, iv, so, voz, fala]) => ({ h: h.holerite, cx, iv, so, voz, fala, cats: T.CATEGORIAS_PADRAO.map(c => c.id) }))""")
        h = r["h"]
        soma = lambda l: round(sum(x["valor"] for x in l), 2)  # noqa: E731
        self.assertEqual(soma(h["creditos"]), h["total_creditos"], "o bruto é a soma dos créditos")
        self.assertEqual(soma(h["debitos"]), h["total_debitos"])
        self.assertAlmostEqual(h["total_creditos"] - h["total_debitos"], h["liquido"], places=2, msg="o líquido bate")
        self.assertTrue({d["tipo"] for d in h["debitos"]} <= {"imposto", "saude"})
        for cx in (r["cx"], r["fala"]):
            self.assertEqual(cx["investimentos"], [], "texto de gasto: só lançamentos")
            self.assertGreater(len(cx["lancamentos"]), 0)
            for it in cx["lancamentos"]:
                self.assertIn(it["tipo"], ("despesa", "receita"))
                self.assertGreater(it["valor"], 0)
                self.assertRegex(it["data"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertIn(it["categoria"], r["cats"])
        self.assertEqual(r["iv"]["itens"][0]["existente"], "cdb-azul", "investimento: acha o CDB que já existe")
        self.assertEqual((r["so"]["lancamentos"], len(r["so"]["investimentos"]) > 0), ([], True), "sem palavras de gasto, na tela de investimentos: investimentos")
        self.assertTrue(r["voz"]["texto"].strip())

    def test_saldos_simulados_acham_cada_investimento(self):
        self.abrir(base(bancos=BANCOS, investimentos=[CDB, RESERVA, CDB_BETO]))
        meus, beto = self.js("""Promise.all([T.api.iaLer({ modo: 'auto', saldos: true, pessoa: 'meu', texto: 'Banco Azul 30.350\\nCofre 1.200,50\\nBanco Verde 2 mil' }),
            T.api.iaLer({ modo: 'auto', saldos: true, texto: 'saldos do beto\\nBanco Azul, valor atualizado, R$ 800' })]).then(l => l.map(r => r.investimentos))""")
        self.assertEqual([(i["nome"], i["valor"], i["existente"], i["dono"]) for i in meus],
                         [("CDB Azul", 30350, "cdb-azul", ""), ("Cofre", 1200.5, "", ""), ("Reserva Verde", 2000, "res-verde", "")])
        self.assertEqual((meus[1]["tipo"], meus[1]["indexador"]), ("dinheiro", "parado"), "o cofre é dinheiro parado")
        self.assertEqual([(i["valor"], i["existente"], i["dono"]) for i in beto], [(800, "cdb-beto", "Beto")], "o dono vem da linha 'do Beto'")


# ---------------------------------------------------------------------------------------------------------------
class TestGravador(TelaSistema):
    """A gravação de verdade (classe Gravador) com o microfone falso do Chromium: PCM de 16 kHz, 16 bits, mono."""

    def test_grava_o_microfone_em_16_khz_e_mostra_o_nivel(self):
        self.abrir(base())
        r = self.js("""(async () => {
          const md = navigator.mediaDevices, gum = md.getUserMedia;
          let pedido = null;
          md.getUserMedia = c => { pedido = c; return gum.call(md, c); };
          try {
            const niveis = [], g = new T.Gravador(l => niveis.push(l));
            await g.start();
            const stream = g.stream, ctx = g.ctx;
            // pelo menos 3 pedaços de 4096 amostras e o bipe do microfone falso (até uns 4 s)
            for (let k = 0; k < 40 && (g.total < 3 * 4096 || !niveis.some(l => l > 0.05)); k++) await new Promise(r => setTimeout(r, 100));
            const total = g.total, seg = g.segundos(), taxa = g.taxa;
            const out = g.stop();
            await new Promise(r => setTimeout(r, 50));
            let mx = 0; for (const v of out) mx = Math.max(mx, Math.abs(v));
            return { pedido, taxa, total, seg, n: out.length, tipo: out.constructor.name, mx, niveis: niveis.length, min: Math.min(...niveis), max: Math.max(...niveis),
              trilhas: stream.getTracks().map(t => t.readyState), ctx: ctx.state, depois: [g.stream, g.no, g.src, g.pedacos.length] };
          } finally { delete md.getUserMedia; }
        })()""")
        self.assertEqual(r["pedido"], {"audio": {"channelCount": 1, "echoCancellation": True, "noiseSuppression": True, "autoGainControl": True}})
        self.assertEqual(r["taxa"], 16000, "o navegador grava direto em 16 kHz")
        self.assertGreaterEqual(r["seg"], 3 * 4096 / 16000)
        self.assertAlmostEqual(r["seg"], r["total"] / 16000)
        self.assertEqual((r["tipo"], r["n"]), ("Int16Array", r["total"]), "em 16 kHz, uma amostra por amostra gravada")
        self.assertTrue(0 < r["mx"] <= 32767, "o bipe do microfone falso chega")
        self.assertGreater(r["niveis"], 0)
        self.assertTrue(0 <= r["min"] and r["max"] <= 1 and r["max"] > 0, f"o nível fica entre 0 e 1 ({r['min']}..{r['max']})")
        self.assertEqual(r["trilhas"], ["ended"], "o microfone desliga")
        self.assertEqual(r["ctx"], "closed")
        self.assertEqual(r["depois"], [None, None, None, 0])

    def test_navegador_que_so_grava_na_taxa_dele_reamostra_para_16_khz(self):
        self.abrir(base())
        r = self.js("""(async () => {
          const AC0 = window.AudioContext;
          window.AudioContext = class extends AC0 { constructor(o) { if (o) throw new Error('taxa não suportada'); super({ sampleRate: 48000 }); } };
          try {
            const g = new T.Gravador();
            await g.start();
            for (let k = 0; k < 40 && g.total < 3 * 4096; k++) await new Promise(r => setTimeout(r, 100));
            const total = g.total, taxa = g.taxa, seg = g.segundos();
            return { total, taxa, seg, n: g.stop().length };
          } finally { window.AudioContext = AC0; }
        })()""")
        self.assertEqual(r["taxa"], 48000)
        self.assertAlmostEqual(r["seg"], r["total"] / 48000)
        self.assertEqual(r["n"], r["total"] // 3, "48 kHz vira 16 kHz: um terço das amostras")

    def test_reamostrar_tira_a_media_de_cada_janela(self):
        self.abrir(base())
        r = self.js("""(() => {
          const reamostrar = (taxa, pedacos) => { const g = new T.Gravador(); g.taxa = taxa; g.pedacos = pedacos.map(p => new Float32Array(p));
            g.total = pedacos.reduce((s, p) => s + p.length, 0); return Array.from(g.stop()); };
          return {
            k3: reamostrar(48000, [[0.5, 0.5, 0.5, 1, 0], [-1, 2, 2, 2, -0.5, -0.5, -0.5]]),
            k1: reamostrar(16000, [[0.1, -0.1, -2]]),
            k441: reamostrar(44100, [Array(441).fill(0.25)]),
            vazio: reamostrar(16000, []),
          };
        })()""")
        self.assertEqual(r["k3"], [16383, 0, 32767, -16384], "média de 3 em 3; acima de 1 fica no máximo; os pedaços se juntam")
        self.assertEqual(r["k1"], [3276, -3276, -32768], "em 16 kHz, cada amostra como está")
        self.assertEqual((len(r["k441"]), set(r["k441"])), (160, {8191}), "44,1 kHz: 441 amostras viram 160")
        self.assertEqual(r["vazio"], [])

    def test_cancelar_desliga_o_microfone_e_joga_fora(self):
        self.abrir(base())
        r = self.js("""(async () => {
          const g = new T.Gravador();
          await g.start();
          const stream = g.stream;
          for (let k = 0; k < 40 && !g.total; k++) await new Promise(r => setTimeout(r, 100));
          const antes = g.total;
          g.cancel();
          return { antes, total: g.total, pedacos: g.pedacos.length, seg: g.segundos(), trilhas: stream.getTracks().map(t => t.readyState), stream: g.stream };
        })()""")
        self.assertGreater(r["antes"], 0)
        self.assertEqual((r["total"], r["pedacos"], r["seg"], r["trilhas"], r["stream"]), (0, 0, 0, ["ended"], None))

    def test_sem_microfone_ou_bloqueado_o_erro_diz_o_motivo(self):
        self.abrir(base())
        r = self.js("""(async () => {
          const nome = async () => { const g = new T.Gravador(); try { await g.start(); return 'gravou'; } catch (e) { g.cancel(); return e.name; } };
          const md = navigator.mediaDevices;
          md.getUserMedia = async () => { throw Object.assign(new Error('Permission denied'), { name: 'NotAllowedError' }); };
          const bloqueado = await nome();
          delete md.getUserMedia;
          Object.defineProperty(navigator, 'mediaDevices', { value: undefined, configurable: true });
          const semApi = await nome();
          delete navigator.mediaDevices;
          return [bloqueado, semApi, !!navigator.mediaDevices.getUserMedia];
        })()""")
        self.assertEqual(r, ["NotAllowedError", "NoApi", True])


# ---------------------------------------------------------------------------------------------------------------
LANC_MERCADO = {"tipo": "despesa", "descricao": "Mercado", "valor": 45, "data": "2026-11-02", "categoria": "c-mercado", "parcela_atual": 0, "parcelas_total": 0,
                "cartao": False, "banco": "", "situacao": "feito", "confianca": "alta"}
_BLOQUEAR = "(navigator.mediaDevices.getUserMedia = async () => { throw Object.assign(new Error(a[1]), { name: a[0] }); }, true)"


class TelaFala(TelaSistema):
    def setUp(self):
        self.addCleanup(lambda: self.js("(delete navigator.mediaDevices, navigator.mediaDevices && delete navigator.mediaDevices.getUserMedia, true)"))

    def bloquear_microfone(self, nome, mensagem=""):
        self.js(_BLOQUEAR, [nome, mensagem])

    def sem_microfone(self):
        self.js("(Object.defineProperty(navigator, 'mediaDevices', { value: undefined, configurable: true }), true)")

    def falsos_da_fala(self):
        """A fala para texto e a IA falsas: guardam o que receberam (window.__pcm, window.__lido)."""
        self.trocar_api("vozTexto", "async pcm => { window.__pcm = pcm.length; return { texto: 'gastei 45 no mercado', nome: 'Fala da Casa' }; }")
        self.trocar_api("iaLer", "async c => { window.__lido = c; return { lancamentos: [" + json.dumps(LANC_MERCADO) + "], investimentos: [] }; }")
        self.trocar_api("chatEnviar", "async c => { window.__chat = c; return { mensagens: [{ id: 'm1', papel: 'eu', texto: c.texto, fala: !!c.fala }, "
                                      "{ id: 'm2', papel: 'ia', texto: 'Anotado.' }] }; }")
        self.js("(window.__pcm = null, window.__lido = null, window.__chat = null, true)")

    def falar(self):
        self.clicar('#app .cab-topo [data-a="falar"]')
        self.pg.wait_for_function("() => { const s = window.GERENCIA_TESTE.IAS; return s && s.etapa === 'voz' && s.rec !== 'starting'; }")
        self.esperar()

    def abrir_chat(self):
        self.clicar('#app .cab-topo [data-a="chat"]')
        self.pg.wait_for_function("window.GERENCIA_TESTE.CH && window.GERENCIA_TESTE.CH.msgs")
        self.esperar()

    def ditar(self):
        self.clicar('#folhas [data-a="ch-mic"]')
        self.pg.wait_for_function("() => { const c = window.GERENCIA_TESTE.CH; return c && c.rec !== 'starting'; }")
        self.esperar()


class TestFalaNaPrevia(TelaFala):
    """Na prévia, sem microfone ou sem permissão, o Falar e o ditado do chat seguem com a gravação simulada."""

    def test_microfone_bloqueado_na_previa_segue_simulado_ate_a_conferencia(self):
        self.abrir(base(bancos=BANCOS))
        self.falsos_da_fala()
        self.bloquear_microfone("NotAllowedError", "Permission denied")
        self.falar()
        self.assertTrue(self.js("T.GRAV instanceof T.GravadorSimulado"), "segue com a gravação simulada")
        self.assertIn("Ouvindo…", self.texto("#folhas .voz-estado"))
        self.assertEqual(self.conta("#folhas .msg-erro"), 0, "na prévia não aparece o erro do microfone")
        self.pg.wait_for_function("+getComputedStyle(document.querySelector('.voz-mic')).getPropertyValue('--lvl') > 0")  # o nível simulado mexe o anel
        self.clicar('#folhas [data-a="fala-ok"]')
        self.pg.wait_for_function("() => !window.GERENCIA_TESTE.IAS || window.GERENCIA_TESTE.IAS.etapa === 'revisao'")
        self.esperar()
        self.assertEqual(self.js("window.__pcm"), 16000, "pelo menos 1 s de áudio simulado (o relógio está parado)")
        self.assertEqual(self.js("[window.__lido.texto, window.__lido.fala]"), ["gastei 45 no mercado", True])
        self.assertEqual(self.folha(), "Conferir lançamentos")

    def test_sem_microfone_na_previa_usa_o_simulado(self):
        self.abrir(base(bancos=BANCOS))
        self.falsos_da_fala()
        self.sem_microfone()
        self.falar()
        self.assertEqual(self.js("[T.GRAV instanceof T.GravadorSimulado, T.IAS.rec]"), [True, "on"])
        self.voltar()
        self.assertEqual((self.niveis(), self.js("T.GRAV")), (0, None), "fechar desliga a gravação")

    def test_ditado_na_previa_sem_permissao_segue_simulado(self):
        self.abrir(base(bancos=BANCOS))
        self.js("(T.CHAT_DEMO.length = 0, true)")
        self.abrir_chat()
        self.bloquear_microfone("NotAllowedError", "Permission denied")
        self.ditar()
        self.assertEqual(self.js("[T.CHG instanceof T.GravadorSimulado, T.CH.rec, T.CH.erro]"), [True, "on", ""])
        self.voltar()
        self.assertEqual(self.js("T.CHG"), None)

    def test_ditado_mostra_o_tempo_e_para_sozinho_em_dois_minutos(self):
        self.abrir(base(bancos=BANCOS))
        self.js("(T.CHAT_DEMO.length = 0, true)")
        self.falsos_da_fala()
        self.js("(window.__G = T.Gravador, window.__seg = 0, T.Gravador = class { async start() {} segundos() { return window.__seg; } "
                "stop() { return new Int16Array(16000 * 3); } cancel() {} }, true)")
        self.addCleanup(lambda: self.js("(T.Gravador = window.__G, true)"))
        self.abrir_chat()
        self.ditar()
        self.js("(window.__seg = 65, true)")
        self.pg.wait_for_function("document.querySelector('#ch-txt').placeholder.includes('1:05')")
        self.assertEqual(self.pg.get_attribute("#ch-txt", "placeholder"), "Ouvindo… 1:05 · toque no visto quando terminar")
        self.assertIsNone(self.js("window.__pcm"), "ainda ouvindo")
        self.js("(window.__seg = 120, true)")
        self.pg.wait_for_function("window.__chat !== null")
        self.esperar()
        self.assertEqual(self.js("window.__pcm"), 48000, "parou sozinho e mandou o que ouviu")
        self.assertEqual(self.js("[window.__chat.texto, window.__chat.fala]"), ["gastei 45 no mercado", True])
        self.assertEqual(self.js("T.CH.rec"), "off")


class TestFalaComServidor(TelaFala, TelaServidor):
    """Com o servidor (no app de verdade): o microfone grava de verdade; sem ele, a mensagem explica o que fazer."""

    def setUp(self):
        TelaServidor.setUp(self)
        TelaFala.setUp(self)

    def test_falar_grava_de_verdade_manda_o_audio_e_le_com_a_ia(self):
        self.abrir(base(bancos=BANCOS))
        self.responder("POST api/ia/ler", 200, {"lancamentos": [LANC_MERCADO], "investimentos": [], "entidade": "ai_task.ia_da_casa"})
        self.falar()
        self.assertTrue(self.js("T.GRAV instanceof T.Gravador"), "o gravador de verdade")
        self.pg.wait_for_function("window.GERENCIA_TESTE.GRAV.segundos() >= 0.7")
        self.pg.wait_for_function("getComputedStyle(document.querySelector('.voz-mic')).getPropertyValue('--lvl').trim() !== '0'")
        self.assertRegex(self.texto("#folhas .voz-tempo"), r"^0:0\d$")
        self.clicar('#folhas [data-a="fala-ok"]')
        self.pg.wait_for_function("() => window.GERENCIA_TESTE.IAS && window.GERENCIA_TESTE.IAS.etapa === 'revisao'")
        self.esperar()
        voz = self.js("window.__srv.pedidos.find(p => p.rota === 'api/voz')")
        self.assertEqual(voz["corpo"]["bytes"], 2 * voz["corpo"]["amostras"], "16 bits por amostra")
        self.assertGreaterEqual(voz["corpo"]["amostras"], 0.7 * 16000)
        lido = self.js("window.__srv.pedidos.find(p => p.rota === 'api/ia/ler').corpo")
        self.assertEqual((lido["texto"], lido["fala"]), ("gastei 45 no mercado", True))
        self.assertEqual(self.folha(), "Conferir lançamentos")
        self.assertEqual(_limpo(self.texto("#folhas .ouvido")), "“gastei 45 no mercado”")

    def test_erros_do_microfone_explicam_o_que_fazer(self):
        casos = [
            ("NotAllowedError", "Permission denied", "O microfone está bloqueado. Permita o microfone para o Home Assistant (no navegador, no cadeado ao lado "
                                                     "do endereço; no app do celular, nas permissões do app Home Assistant) e tente de novo."),
            ("NotFoundError", "Requested device not found", "Não achei um microfone neste aparelho."),
            ("NotReadableError", "Could not start audio source", "O microfone está sendo usado por outro app. Feche o outro e tente de novo."),
            ("AbortError", "O driver de áudio travou", "Não consegui abrir o microfone (O driver de áudio travou)."),
            ("", "", "Não consegui abrir o microfone (erro)."),
            (None, None, "Este navegador não deixa usar o microfone aqui. Abra o Home Assistant pelo endereço com https (como o do Nabu Casa) ou pelo app."),
        ]
        for nome, msg, esperado in casos:
            with self.subTest(nome):
                self.abrir(base(bancos=BANCOS))
                if nome is None:
                    self.sem_microfone()
                else:
                    self.bloquear_microfone(nome, msg)
                self.falar()
                self.assertEqual(self.texto("#folhas .msg-erro"), esperado)
                self.assertEqual((self.texto("#folhas .voz-estado"), self.js("[T.GRAV, T.IAS.rec]")), ("Toque no microfone e fale", [None, "off"]))
                self.assertTrue(self.pg.locator('#folhas [data-a="fala-ok"]').is_disabled())
                self.js("(delete navigator.mediaDevices, delete navigator.mediaDevices.getUserMedia, true)")

    def test_ditado_sem_microfone_explica_no_chat(self):
        self.abrir(base(bancos=BANCOS))
        self.abrir_chat()
        self.bloquear_microfone("NotFoundError", "Requested device not found")
        self.ditar()
        self.assertEqual(self.texto("#folhas .ch-pe .msg-erro"), "Não achei um microfone neste aparelho.")
        self.assertEqual(self.js("[T.CH.rec, T.CHG]"), ["off", None])
        self.assertFalse(self.pg.locator("#ch-txt").is_disabled(), "dá para escrever")

    def test_ditado_grava_de_verdade_e_manda_como_fala(self):
        self.abrir(base(bancos=BANCOS))
        self.abrir_chat()
        self.ditar()
        self.assertTrue(self.js("T.CHG instanceof T.Gravador"))
        self.pg.wait_for_function("document.querySelector('#ch-txt').placeholder.startsWith('Ouvindo… 0:0')")
        self.pg.wait_for_function("window.GERENCIA_TESTE.CHG.segundos() >= 0.6")
        self.clicar('#folhas [data-a="ch-mic"]')
        self.pg.wait_for_function("window.__srv.pedidos.some(p => p.rota === 'api/chat' && p.metodo === 'POST')")
        self.pg.wait_for_function("!window.GERENCIA_TESTE.CH.enviando")
        self.esperar()
        voz = self.js("window.__srv.pedidos.find(p => p.rota === 'api/voz').corpo")
        self.assertGreaterEqual(voz["amostras"], 0.6 * 16000)
        chat = self.js("window.__srv.pedidos.find(p => p.rota === 'api/chat' && p.metodo === 'POST').corpo")
        self.assertEqual((chat["texto"], chat["fala"], chat["aba"]), ("gastei 45 no mercado", True, "inicio"))
        self.assertEqual([_limpo(t) for t in self.textos(".ch-msg .ch-bolha")], ["gastei 45 no mercado", "Anotado."])

    def test_ditado_com_erro_ao_transcrever_mostra_o_erro(self):
        self.abrir(base(bancos=BANCOS))
        self.responder("POST api/voz", 502, {"erro": "A fala para texto do Home Assistant não respondeu."})
        self.js("(window.__G = T.Gravador, T.Gravador = class { async start() {} segundos() { return 2; } stop() { return new Int16Array(32000); } cancel() {} }, true)")
        self.addCleanup(lambda: self.js("(T.Gravador = window.__G, true)"))
        self.abrir_chat()
        self.ditar()
        self.clicar('#folhas [data-a="ch-mic"]')
        self.pg.wait_for_function("window.GERENCIA_TESTE.CH.rec === 'off'")
        self.esperar()
        self.assertEqual(self.texto("#folhas .ch-pe .msg-erro"), "A fala para texto do Home Assistant não respondeu.")
        self.assertEqual(self.pedidos("api/chat"), [["GET", "api/chat"]], "nada vai para a IA")
        self.assertEqual(self.conta(".ch-msg"), 0)


# ---------------------------------------------------------------------------------------------------------------
class TestArrastar(TelaSistema):
    """Arrastar o dedo para o lado troca de aba (Início ⇄ Caixa ⇄ Invest ⇄ Mais), com toques de verdade (CDP) e animação de entrada."""
    MOVIMENTO = "no-preference"
    TOQUE = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cdp = cls.ctx.new_cdp_session(cls.pg)
        # guarda as animações pedidas (a tela nova entra pelo lado do dedo)
        cls.pg.evaluate("""() => { const o = Element.prototype.animate; window.__anim = [];
            Element.prototype.animate = function (k, op) { window.__anim.push({ id: this.id, de: k[0].transform, ms: op && op.duration }); return o.call(this, k, op); }; }""")
        # no primeiro arraste de uma página nova, o Chromium de teste cancela o toque logo no começo (pointercancel) e não entrega o fim:
        # arrastes para a direita no Início (que não trocam nada) antes dos testes. Um só às vezes não bastava no GitHub (o primeiro
        # teste da classe, test_a_tela_nova_entra_pelo_lado_do_dedo, falhou assim uma vez na 1.29.0): três, com uma pausa entre eles
        for _ in range(3):
            for tipo, x in [("touchStart", 100), ("touchMove", 160), ("touchMove", 220), ("touchMove", 300), ("touchEnd", None)]:
                cls.toque(cls, tipo, [] if x is None else [(x, 80)])
            cls.pg.wait_for_timeout(80)

    def setUp(self):
        self.js("(window.__anim = [], true)")

    def toque(self, tipo, pontos):
        self.cdp.send("Input.dispatchTouchEvent", {"type": tipo, "touchPoints": [{"x": x, "y": y, "id": k} for k, (x, y) in enumerate(pontos)]})

    def arrastar(self, x0, x1, y=None, y1=None, dedos=1, antes_de_soltar=None, cancelar=False):
        """Um dedo (ou mais) de x0 a x1; y: a altura do título da tela (onde nada impede o arraste)."""
        y = self.y_titulo() if y is None else y
        y1 = y if y1 is None else y1
        extra = [(60, y + 60)] * (dedos - 1)
        self.toque("touchStart", [(x0, y)] + extra)
        for k in range(1, 6):
            self.toque("touchMove", [(x0 + (x1 - x0) * k / 5, y + (y1 - y) * k / 5)] + extra)
        if antes_de_soltar:
            antes_de_soltar()
        self.toque("touchCancel" if cancelar else "touchEnd", [])
        self.esperar()

    def y_titulo(self):
        return self.js("(r => r.top + r.height / 2)(document.querySelector('#app .cab h1').getBoundingClientRect())")

    def meio(self, sel):
        return self.js("(r => [r.left + r.width / 2, r.top + r.height / 2])(document.querySelector(a).getBoundingClientRect())", sel)

    def aba(self):
        return self.js("T.S.ui.tab")

    def entradas(self):
        """As animações da tela principal: [de onde entrou, duração]."""
        return [[a["de"], a["ms"]] for a in self.js("window.__anim") if a["id"] == "app"]

    def test_dedo_para_a_esquerda_vai_para_a_proxima_aba_ate_mais(self):
        self.abrir(base(bancos=BANCOS))
        vistas = []
        for _ in range(4):
            self.arrastar(300, 100)
            vistas.append(self.aba())
        self.assertEqual(vistas, ["caixa", "investimentos", "mais", "mais"], "depois de Mais não há outra")
        self.assertEqual(self.js("document.querySelector('#app .cab h1').textContent"), "Mais")
        self.assertEqual(self.js("JSON.parse(localStorage.getItem('gerencia.ui')).tab"), "mais", "a aba fica guardada")

    def test_dedo_para_a_direita_volta_ate_o_inicio(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais"})
        vistas = []
        for _ in range(4):
            self.arrastar(100, 300)
            vistas.append(self.aba())
        self.assertEqual(vistas, ["investimentos", "caixa", "inicio", "inicio"])

    def test_a_tela_nova_entra_pelo_lado_do_dedo(self):
        self.abrir(base(bancos=BANCOS))
        self.arrastar(300, 100)
        self.assertEqual(self.entradas(), [["translateX(40px)", 280]], "a próxima aba entra pela direita")
        self.js("(window.__anim = [], true)")
        self.arrastar(100, 300)
        self.assertEqual(self.entradas(), [["translateX(-40px)", 280]], "a anterior, pela esquerda")
        self.js("(window.__anim = [], true)")
        self.ir("mais")
        self.assertEqual(self.entradas(), [], "tocar na aba embaixo troca sem animação")

    def test_com_reduzir_movimento_troca_sem_animar(self):
        self.abrir(base(bancos=BANCOS))
        self.pg.emulate_media(reduced_motion="reduce")
        self.addCleanup(lambda: self.pg.emulate_media(reduced_motion="no-preference"))
        self.arrastar(300, 100)
        self.assertEqual((self.aba(), self.entradas()), ("caixa", []))

    def test_o_que_nao_troca_de_aba(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "caixa"})
        y = self.y_titulo()
        nav = self.meio("#nav")
        casos = [
            ("começando na borda esquerda (é o Voltar do celular)", lambda: self.arrastar(10, 230)),
            ("começando na borda direita", lambda: self.arrastar(380, 180)),
            ("arraste curto", lambda: self.arrastar(250, 190)),
            ("mais para baixo que para o lado", lambda: self.arrastar(300, 200, y, y + 80)),
            ("dois dedos (zoom)", lambda: self.arrastar(300, 100, dedos=2)),
            ("cancelado pelo sistema", lambda: self.arrastar(300, 100, cancelar=True)),
            ("na barra de abas embaixo", lambda: self.arrastar(300, 100, nav[1])),
        ]
        for nome, fazer in casos:
            with self.subTest(nome):
                fazer()
                self.assertEqual(self.aba(), "caixa")
        self.assertEqual(self.entradas(), [])

    def test_arraste_devagar_nao_troca(self):
        self.abrir(base(bancos=BANCOS))
        self.addCleanup(lambda: self.pg.clock.set_fixed_time("2026-11-02T10:00:00-03:00"))
        self.arrastar(300, 100, antes_de_soltar=lambda: self.pg.clock.set_fixed_time("2026-11-02T10:00:01-03:00"))
        self.assertEqual(self.aba(), "inicio", "mais de 0,8 s: é rolagem, não troca de aba")

    def test_num_grafico_o_dedo_mostra_os_valores_e_nao_troca(self):
        self.abrir(base(bancos=BANCOS, lancamentos=RESTAURANTES), ui={"tab": "caixa", "cxModo": "fluxo"})
        x, y = self.meio("#ch-fluxo")
        self.arrastar(x + 80, x - 100, y)
        self.assertEqual(self.aba(), "caixa")

    def test_numa_fileira_que_rola_para_o_lado_nao_troca(self):
        self.pg.set_viewport_size({"width": 320, "height": 700})
        self.addCleanup(lambda: self.pg.set_viewport_size({"width": self.LARGURA, "height": self.ALTURA}))
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "config"})
        self.assertGreater(self.js("(e => e.scrollWidth - e.clientWidth)(document.querySelector('.mais-abas'))"), 2, "as abas de Configurações rolam no celular estreito")
        x, y = self.meio(".mais-abas")
        self.arrastar(x - 100, x + 100, y)
        self.assertEqual((self.aba(), self.js("T.S.ui.maisTela")), ("mais", "config"))

    def test_numa_tela_de_mais_para_a_direita_volta_ao_menu(self):
        self.abrir(base(bancos=BANCOS))
        self.ir_mais("config")
        self.arrastar(300, 100)
        self.assertEqual((self.aba(), self.js("T.S.ui.maisTela")), ("mais", "config"), "para a esquerda, nada (não há tela depois)")
        self.arrastar(100, 300)
        self.assertEqual((self.aba(), self.js("T.S.ui.maisTela"), self.texto("#app .cab h1")), ("mais", "", "Mais"), "para a direita, o menu")
        self.assertEqual(self.entradas(), [["translateX(-40px)", 280]], "o menu entra pela esquerda")
        self.pg.wait_for_function("!(history.state && history.state.tela)")
        self.arrastar(100, 300)
        self.assertEqual(self.aba(), "investimentos", "do menu, a aba anterior")

    def test_com_janela_aberta_nao_troca(self):
        self.abrir(base(bancos=BANCOS))
        y = self.y_titulo()
        self.clicar('#nav [data-a="novo"]')
        self.arrastar(300, 100, y)
        self.assertEqual((self.aba(), self.folha()), ("inicio", "Adicionar"))

    def test_no_computador_nao_troca(self):
        self.abrir(base(bancos=BANCOS))
        self.pg.set_viewport_size({"width": 1200, "height": 800})
        self.addCleanup(lambda: self.pg.set_viewport_size({"width": self.LARGURA, "height": self.ALTURA}))
        self.esperar()
        self.arrastar(700, 450)
        self.assertEqual(self.aba(), "inicio", "no computador há a barra lateral")


# ---------------------------------------------------------------------------------------------------------------
class TestOpcoes(TelaSistema):
    """Mais › Configurações › Opções: cada chave, o texto dela e o que ela muda nas outras telas."""

    def casa(self, **ajustes):
        """Os dados de entrada: restaurante de julho a outubro e um CDB de maio (100% do CDI)."""
        return base(bancos=BANCOS, lancamentos=RESTAURANTES, investimentos=[CDB], ajustes=dict({"corrigir": True}, **ajustes))

    def textos_opcoes(self):
        return [_limpo(t) for t in self.textos("#app .mais-painel .linha-sw span")]

    def chave(self, k):
        self.clicar(f'#app .mais-painel [data-a="ajuste"][data-k="{k}"]')

    def test_as_tres_chaves_comecam_ligadas_com_o_que_fazem(self):
        self.abrir(self.casa(), ui={"tab": "mais", "maisTela": "config", "maisAba": "opcoes"})
        self.assertEqual(self.textos("#app .mais-painel .linha-sw b"), ["Dicas de economia", "Prever o dia a dia", "Corrigir valores pelo rendimento"])
        self.assertEqual(self.textos_opcoes(), [
            "Ligado: no Início, planos anuais mais baratos e categorias acima da média.",
            "Ligado: os próximos meses somam a média do dia a dia, R$ 617 por mês.",  # (450 + 500 + 900) / 3
            "Estima o valor de hoje desde o último informado. Renda variável não muda."])
        self.assertEqual(self.js("[...document.querySelectorAll('#app .mais-painel .sw')].map(b => b.getAttribute('aria-checked'))"), ["true", "true", "true"])

    def test_com_a_ia_desligada_as_dicas_explicam_que_planos_anuais_precisam_dela(self):
        self.abrir(self.casa(ia=False), ui={"tab": "mais", "maisTela": "config", "maisAba": "opcoes"})
        self.assertEqual(self.textos_opcoes()[0], "Ligado: no Início, categorias acima da média. Planos anuais precisam da IA.")

    def test_desligar_as_dicas_tira_do_inicio(self):
        self.abrir(self.casa(), ui={"tab": "mais", "maisTela": "config", "maisAba": "opcoes"})
        self.ir("inicio")
        self.assertIn("Restaurantes acima da média", self.texto(".card.dicas"))
        self.ir_mais("config", "opcoes")
        self.chave("dicas")
        self.assertIs(self.dados()["ajustes"]["dicas"], False)
        self.assertEqual(self.textos_opcoes()[0], "Desligado: sem dicas.")
        self.ir("inicio")
        self.assertEqual(self.conta(".card.dicas"), 0)
        self.ir_mais("caixa")
        self.assertEqual(self.limpo("#dicas .status"), "Desligadas em Mais › Configurações › Opções.")
        self.ir_mais("config", "opcoes")
        self.chave("dicas")
        self.ir("inicio")
        self.assertIn("Restaurantes acima da média", self.texto(".card.dicas"), "ligada de novo, a dica volta")

    def test_desligar_prever_o_dia_a_dia_tira_a_media_do_fluxo(self):
        self.abrir(self.casa(), ui={"tab": "caixa", "cxModo": "fluxo"})
        self.assertIn("fixos, parcelas, faturas e dia a dia", self.texto("#app .stat-duo"))
        self.assertIn("Dia a dia (média)", self.texto("#app .leg"))
        self.assertTrue(self.js("T.serieFluxo().some(m => m.prev && m.est > 600)"), "os meses à frente somam a média")
        self.ir_mais("config", "opcoes")
        self.chave("prever_dia")
        self.assertIs(self.dados()["ajustes"]["prever_dia"], False)
        self.assertEqual(self.textos_opcoes()[1], "Desligado: só fixos, parcelas e faturas.")
        self.ir("caixa")
        self.assertIn("fixos, parcelas e faturas já lançados", self.texto("#app .stat-duo"))
        self.assertNotIn("Dia a dia (média)", self.texto("#app .leg"))
        self.assertTrue(self.js("T.serieFluxo().every(m => m.est === 0)"))

    def test_desligar_corrigir_mostra_o_valor_informado(self):
        self.abrir(self.casa(), ui={"tab": "investimentos", "invModo": "carteira"})
        corrigido = self.js("T.valorHoje(T.S.d.investimentos[0])")
        self.assertGreater(corrigido, 10500, "100% do CDI desde maio")
        self.ir_mais("config", "opcoes")
        self.chave("corrigir")
        self.assertIs(self.dados()["ajustes"]["corrigir"], False)
        self.assertEqual(self.js("document.querySelector('#op-invest .sw').getAttribute('aria-checked')"), "false")
        self.ir("investimentos")
        self.assertEqual(self.js("document.querySelector('.inv-valor').textContent"), "R$ 10.000,00", "o valor informado em maio, sem rendimento")
        self.ir_mais("config")
        self.chave("corrigir")
        self.assertAlmostEqual(self.js("T.valorHoje(T.S.d.investimentos[0])"), corrigido, places=2)


# ---------------------------------------------------------------------------------------------------------------
class TestBens(TelaSistema):
    """Bens do InventarIA: Atualizar (no card e na janela Bens da casa) e a perda de valor por categoria em Mais › Invest."""

    def setUp(self):
        self.trocar_api("bens", "async () => { window.__bens.chamadas.push('bens'); return JSON.parse(JSON.stringify(window.__bens.resp)); }")
        self.trocar_api("bensAtualizar", """() => { const b = window.__bens; b.chamadas.push('atualizar'); const r = () => JSON.parse(JSON.stringify(b.resp));
            return b.segura ? new Promise(ok => { b.soltar = () => ok(r()); }) : Promise.resolve(r()); }""")
        self.js("(window.__bens = { chamadas: [], resp: a, segura: false, soltar: null }, true)", BENS_NOVOS)

    def segurar(self):
        self.js("(window.__bens.segura = true)")

    def soltar(self):
        self.js("(window.__bens.soltar(), true)")
        self.esperar()

    def chamadas(self):
        return self.js("window.__bens.chamadas")

    def test_atualizar_do_inventario_mostra_procurando_e_depois_o_novo_total(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"}, bens=BENS)
        self.assertEqual(self.limpo("#bens .linha-sw span"), "Ligado: R$ 30.000 em 12 itens.")
        self.segurar()
        self.clicar('#bens [data-a="bens-atualizar"]')
        self.assertEqual(self.limpo("#bens .status"), "Procurando o InventarIA…")
        self.assertEqual(self.chamadas(), ["atualizar"], "pede ao InventarIA de novo (sem a cópia de 10 minutos)")
        self.soltar()
        self.assertEqual(self.limpo("#bens .linha-sw span"), "Ligado: R$ 31.500 em 13 itens.")
        self.assertEqual(self.limpo('#bens [data-a="bens-atualizar"]'), "Atualizar do InventarIA")

    def test_atualizar_dentro_de_bens_da_casa_redesenha_a_janela(self):
        self.abrir(base(bancos=BANCOS, investimentos=[CDB]), bens=BENS)
        self.clicar('.hl-row[data-a="bens"]')
        self.assertEqual(self.folha(), "Bens da casa")
        self.assertEqual(self.limpo("#folhas .stat-duo > div b"), "R$ 30.000")
        self.segurar()
        self.clicar('#folhas [data-a="bens-atualizar"]')
        self.assertEqual(self.limpo("#folhas .status"), "Procurando o InventarIA…")
        self.soltar()
        self.assertEqual((self.folha(), self.limpo("#folhas .stat-duo > div b")), ("Bens da casa", "R$ 31.500"))

    def test_inventario_fora_do_ar_tenta_de_novo(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "config", "maisAba": "integracoes"}, bens={"ok": False, "motivo": "O InventarIA não respondeu."})
        self.assertEqual(self.limpo("#bens .status"), "O InventarIA não respondeu.")
        self.clicar('#bens [data-a="bens-atualizar"]')
        self.assertEqual(self.limpo('#bens .linha-sw span'), "Ligado: R$ 31.500 em 13 itens.")
        self.assertEqual(self.conta("#bens .status"), 0)

    def perda(self, k, texto):
        sel = f'#perda-bens [data-bens-taxa="{k}"]'
        self.pg.fill(sel, texto)
        self.pg.locator(sel).dispatch_event("change")
        self.esperar()

    def test_perda_de_valor_lista_as_categorias_pelo_valor(self):
        self.abrir(base(investimentos=[CARRO, PRAIA]), ui={"tab": "mais", "maisTela": "invest"}, bens=BENS)
        linhas = self.js("[...document.querySelectorAll('#perda-bens .bens-tx')].map(l => [l.querySelector('span').innerText.replace(/\\s+/g, ' '), l.querySelector('input').value])")
        self.assertEqual(linhas, [["Veículos R$ 40.000", "15"], ["Móveis R$ 26.000", "10"], ["Eletrônicos R$ 14.000", "20"]],
                         "o carro, os móveis (8 mil daqui e 18 mil do InventarIA) e os eletrônicos (2 mil e 12 mil)")

    def test_mudar_a_perda_salva_e_vale_para_os_bens_daqui(self):
        self.abrir(base(investimentos=[CARRO, PRAIA]), ui={"tab": "mais", "maisTela": "invest"}, bens=BENS)
        self.perda("eletronicos", "25")
        d = self.dados()
        self.assertEqual(d["ajustes"]["bens_taxas"], {"eletronicos": 25})
        carro, praia = d["investimentos"]
        self.assertEqual([p["taxa"] for p in praia["partes"]], [10, 25], "só a parte de eletrônicos muda")
        self.assertEqual(praia["taxa"], 13, "a taxa do bem é a média das partes, pelo valor: (8000×10 + 2000×25) / 10000")
        self.assertEqual(carro["taxa"], 15, "o carro não é eletrônico")
        self.assertEqual(self.esperar_aviso("Perde"), "Perde 25% por ano")
        self.assertIn("bens", self.chamadas(), "os bens do InventarIA são recalculados")
        self.assertEqual(self.pg.input_value('#perda-bens [data-bens-taxa="eletronicos"]'), "25")
        self.perda("veiculos", "12")
        self.assertEqual(self.dados()["investimentos"][0]["taxa"], 12, "um bem de uma categoria só leva a taxa nova")

    def dir_on(self, k):
        return self.texto(f'#perda-bens [data-a="bens-dir"][data-k="{k}"].on')

    def test_valoriza_ao_lado_da_perda(self):
        self.abrir(base(investimentos=[CARRO, PRAIA]), ui={"tab": "mais", "maisTela": "invest"}, bens=BENS)
        self.assertEqual(self.texto("#perda-bens h2"), "Valor dos bens por ano")
        self.assertEqual(self.js("[...document.querySelectorAll('#perda-bens .tx-dir')].map(g => [...g.querySelectorAll('button')].map(b => b.textContent))"),
                         [["Perde", "Valoriza"]] * 3, "cada categoria: Perde ou Valoriza")
        self.assertEqual(self.dir_on("moveis"), "Perde", "de costume, perde")
        larg = self.js("[...document.querySelectorAll('#perda-bens .tx-dir button')].map(b => Math.round(b.getBoundingClientRect().width))")
        self.assertEqual(len(set(larg)), 1, f"os dois botões do mesmo tamanho ({larg})")
        self.clicar('#perda-bens [data-a="bens-dir"][data-k="moveis"][data-v="-1"]')
        self.esperar()
        self.assertEqual(self.dados()["ajustes"]["bens_taxas"]["moveis"], -10, "Valoriza: a mesma %, agora valorizando")
        self.assertEqual(self.dados()["investimentos"][1]["partes"][0]["taxa"], -10, "e vale para os bens daqui")
        self.assertEqual(self.esperar_aviso("Valoriza"), "Valoriza 10% por ano")
        self.assertEqual((self.dir_on("moveis"), self.pg.input_value('#perda-bens [data-bens-taxa="moveis"]')), ("Valoriza", "10"))
        self.perda("moveis", "3")
        self.assertEqual(self.dados()["ajustes"]["bens_taxas"]["moveis"], -3, "com Valoriza marcado, a % digitada valoriza")
        self.clicar('#perda-bens [data-a="bens-dir"][data-k="moveis"][data-v="1"]')
        self.esperar()
        self.assertEqual(self.dados()["ajustes"]["bens_taxas"]["moveis"], 3, "Perde de novo")

    def test_bens_que_valorizam_dizem_quanto_ganham(self):
        self.abrir(base(investimentos=[CARRO]), bens={**BENS, "perde_ano": -900})
        self.assertEqual(self.texto('#app .hl-row[data-a="bens"]').split("\n")[-1], "valorizam ≈ R$ 900/ano", "no Início")
        self.abrir(base(investimentos=[CARRO]), bens={**BENS, "perde_ano": 0})
        self.assertEqual(self.texto('#app .hl-row[data-a="bens"]').split("\n")[-1], "mantêm o valor")

    def test_perda_fica_entre_menos_50_e_100(self):
        self.abrir(base(investimentos=[PRAIA]), ui={"tab": "mais", "maisTela": "invest"}, bens=BENS)
        # um número negativo digitado também vale: vira Valoriza, e o campo mostra a % sem sinal
        for digitado, salvo, mostrado in [("150", 100, "100"), ("-80", -50, "50"), ("abc", 0, "0"), ("−5", -5, "5"), ("7,5", -7.5, "7,5")]:  # com Valoriza marcado, a % digitada valoriza
            with self.subTest(digitado):
                self.perda("moveis", digitado)
                self.assertEqual(self.dados()["ajustes"]["bens_taxas"]["moveis"], salvo)
                self.assertEqual(self.dados()["investimentos"][0]["partes"][0]["taxa"], salvo)
                self.assertEqual(self.pg.input_value('#perda-bens [data-bens-taxa="moveis"]'), mostrado)


# ---------------------------------------------------------------------------------------------------------------
class TestFormularios(TelaSistema):
    """Casos do formulário de lançamento e da leitura por IA que dependem de tempo, foco e arquivos."""

    def nova_despesa(self):
        self.ir("caixa")
        self.clicar('#nav [data-a="novo"]')
        self.assertEqual(self.folha(), "Nova despesa")

    def ajuda_parcelas(self):
        return self.js("(e => e ? e.textContent.trim() : null)(document.querySelector('#folhas [data-lf=\"vezes\"]').closest('.duo').querySelector('.ajuda'))")

    def test_vezes_do_parcelado_redesenha_depois_sem_perder_o_foco(self):
        self.abrir(base(bancos=BANCOS))
        self.nova_despesa()
        self.digitar("#lf-valor", "100000")
        self.clicar('#folhas [data-a="lf-set"][data-k="repete"][data-v="parcelado"]')
        self.assertEqual(self.ajuda_parcelas(), "10x de R$ 100,00")
        self.digitar('#folhas [data-lf="vezes"]', "4")
        self.assertEqual(self.ajuda_parcelas(), "10x de R$ 100,00", "enquanto digita, a janela não se redesenha")
        self.pg.wait_for_function("document.querySelector('#folhas [data-lf=\"vezes\"]').closest('.duo').querySelector('.ajuda').textContent.includes('4x')")
        self.assertEqual(self.ajuda_parcelas(), "4x de R$ 250,00")
        self.assertEqual(self.js("[document.activeElement.dataset.lf, document.activeElement.selectionStart]"), ["vezes", 1], "o cursor continua no campo")

    def test_data_futura_vira_a_pagar_depois_de_digitar(self):
        self.abrir(base(bancos=BANCOS))
        self.nova_despesa()
        self.assertEqual(self.limpo('#folhas [data-a="lf-pago"].on'), "Pago")
        self.preencher("#lf-data", "2026-11-20")
        self.pg.wait_for_function("document.querySelector('#folhas [data-a=\"lf-pago\"].on').textContent === 'A pagar'")
        self.assertEqual(self.js("document.activeElement.id"), "lf-data", "o foco volta para a data")

    def test_observacao_abre_e_e_salva(self):
        self.abrir(base(bancos=BANCOS))
        self.nova_despesa()
        self.assertEqual(self.conta('#folhas [data-lf="obs"]'), 0, "fechada no começo")
        self.clicar('#folhas [data-a="lf-obs"]')
        self.preencher('#folhas [data-lf="obs"]', "Dividido com o Beto")
        self.clicar('#folhas [data-a="lf-obs"]')
        self.assertEqual(self.conta('#folhas [data-lf="obs"]'), 0)
        self.clicar('#folhas [data-a="lf-obs"]')
        self.assertEqual(self.pg.input_value('#folhas [data-lf="obs"]'), "Dividido com o Beto", "fechar não apaga")
        self.digitar("#lf-valor", "4500")
        self.clicar('#folhas [data-a="lf-salvar"]:not([data-mais])')
        self.assertIsNone(self.folha())
        self.assertEqual(self.dados()["lancamentos"][0]["obs"], "Dividido com o Beto")

    def test_salvar_e_lancar_outro_limpa_e_continua_na_janela(self):
        self.abrir(base(bancos=BANCOS))
        self.nova_despesa()
        self.digitar("#lf-valor", "4500")
        self.preencher("#lf-desc", "Mercado")
        self.clicar('#folhas [data-a="lf-set"][data-k="categoria"][data-v="c-mercado"]')
        self.clicar('#folhas [data-a="lf-conta"][data-v="k-verde"]')
        self.clicar('#folhas [data-a="lf-obs"]')
        self.preencher('#folhas [data-lf="obs"]', "Feira de domingo")
        self.clicar('#folhas [data-a="lf-salvar"][data-mais="1"]')
        self.assertEqual(self.esperar_aviso("Lançado"), "Lançado")
        self.assertEqual(self.folha(), "Nova despesa", "a janela continua aberta")
        self.assertEqual((self.pg.input_value("#lf-valor"), self.pg.input_value("#lf-desc"), self.conta('#folhas [data-lf="obs"]')), ("", "", 0),
                         "valor, descrição e observação limpos")
        self.assertEqual(self.js("document.activeElement.id"), "lf-valor", "pronto para digitar o próximo valor")
        self.assertEqual(self.limpo('#folhas [data-a="lf-conta"].on'), "Banco Verde · Ana", "a conta continua")
        self.digitar("#lf-valor", "1200")
        self.preencher("#lf-desc", "Padaria")
        self.clicar('#folhas [data-a="lf-salvar"]:not([data-mais])')
        self.assertIsNone(self.folha())
        ls = self.dados()["lancamentos"]
        self.assertEqual([(l["descricao"], l["valor"], l["conta"], l["categoria"], l["obs"]) for l in ls],
                         [("Mercado", 45, "k-verde", "c-mercado", "Feira de domingo"), ("Padaria", 12, "k-verde", "c-mercado", "")])

    def test_mudar_o_aporte_abre_o_aporte_fixo_do_proximo_mes(self):
        self.abrir(base(bancos=BANCOS, investimentos=[CDB], recorrencias=[APORTE]), ui={"tab": "investimentos", "invModo": "evolucao"})
        self.assertEqual(self.limpo('#app [data-a="aporte-ajustar"]'), "Mudar o aporte")
        self.clicar('#app [data-a="aporte-ajustar"]')
        self.assertEqual(self.folha(), "Aporte")
        self.assertEqual(self.js("[T.LF.recorrencia, T.LF.competencia, T.LF.valor]"), ["r-apo", "2026-12", 800])
        self.assertIn("Aporte nos seus investimentos, todo dia 10. Valor padrão R$ 800,00", _limpo(self.folha_texto()))

    def test_ver_os_aportes_leva_aos_fixos(self):
        outro = dict(APORTE, id="r-apo2", descricao="Aporte do décimo terceiro", valor=2400, freq="anual", inicio="2026-12", dia=20)
        self.abrir(base(bancos=BANCOS, investimentos=[CDB], recorrencias=[APORTE, outro]), ui={"tab": "investimentos", "invModo": "evolucao"})
        self.assertEqual(self.limpo('#app [data-a="aporte-ajustar"]'), "Ver os aportes")
        self.clicar('#app [data-a="aporte-ajustar"]')
        self.assertIsNone(self.folha())
        self.assertEqual(self.js("[T.S.ui.tab, T.S.ui.maisTela]"), ["mais", "caixa"], "abre Mais › Caixa, nos fixos")
        fixos = self.texto("#fixos")
        self.assertIn("Aporte mensal", fixos)
        self.assertIn("Aporte do décimo terceiro", fixos)

    def test_trocar_o_modo_do_desconto_converte_o_valor(self):
        # obs.: nenhum botão da tela chama lf-desc-modo hoje (os impostos são sempre em %); a função segue no app
        self.abrir(base(bancos=BANCOS))
        r = self.js("""(() => {
          T.abrirLancamento(null, { tipo: 'receita' });
          Object.assign(T.LF, { valor: 5000, descAberto: true, descontos: [{ id: 'd1', descricao: 'INSS', modo: 'fixo', valor: 550, base: '', categoria: 'c-impostos' }] });
          const v = () => [T.LF.descontos[0].modo, T.LF.descontos[0].valor];
          const out = [];
          T.trocarModoDesc(0, 'pct'); out.push(v());
          T.trocarModoDesc(0, 'pct'); out.push(v());
          T.trocarModoDesc(0, 'fixo'); out.push(v());
          T.LF.valor = 0; T.trocarModoDesc(0, 'pct'); out.push(v());
          T.trocarModoDesc(7, 'fixo');
          return out;
        })()""")
        self.assertEqual(r, [["pct", 11], ["pct", 11], ["fixo", 550], ["pct", 0]], "550 de 5.000 = 11%; sem bruto, 0%; um desconto que não existe é ignorado")

    def abrir_salario(self, lancamentos=()):
        self.abrir(base(bancos=BANCOS, recorrencias=[SALARIO, PLANO], lancamentos=list(lancamentos)), ui={"tab": "caixa"})
        self.clicar('#app [data-id="v:r-sal:2026-11"]')
        self.assertEqual(self.folha(), "Recebimento")

    def resumo(self):
        return self.js("[...document.querySelectorAll('#lf-desc-res > div')].map(d => d.querySelector('b').textContent)")

    def ligados(self):
        return [_limpo(t) for t in self.textos("#folhas .lig-l")]

    def test_plano_ligado_aparece_no_salario_fixo_e_desconta_do_liquido(self):
        self.abrir_salario()
        self.assertEqual(self.ligados(), ["Plano de saúde − R$ 250,00"])
        self.assertEqual(self.resumo(), ["R$ 5.000,00", "− R$ 800,00", "R$ 4.200,00"], "INSS 550 e plano 250")

    def test_plano_com_outro_valor_neste_mes_usa_o_do_mes(self):
        mes = {"id": "l-plano-nov", "tipo": "despesa", "descricao": "Plano de saúde", "valor": 280, "data": "2026-11-05", "recorrencia": "r-plano",
               "competencia": "2026-11", "categoria": "c-saude", "vinculo": "r-sal", "pago": False}
        self.abrir_salario([mes])
        self.assertEqual(self.ligados(), ["Plano de saúde − R$ 280,00"])
        self.assertEqual(self.resumo()[2], "R$ 4.170,00")

    def test_plano_pulado_neste_mes_nao_desconta(self):
        pulado = {"id": "l-plano-nov", "tipo": "despesa", "descricao": "Plano de saúde", "valor": 250, "data": "2026-11-05", "recorrencia": "r-plano",
                  "competencia": "2026-11", "categoria": "c-saude", "vinculo": "r-sal", "pago": False, "pulado": True}
        self.abrir_salario([pulado])
        self.assertEqual(self.ligados(), [])
        self.assertEqual(self.resumo()[2], "R$ 4.450,00")

    def ler_recibo(self, holerite):
        self.trocar_api("iaLer", "async c => { window.__recibo = c; return { holerite: " + json.dumps(holerite) + ", entidade: 'ai_task.ia_da_casa' }; }")
        self.galeria('#folhas [data-a="lf-ler-recibo"]').set_files({"name": "recibo-novembro.pdf", "mimeType": "application/pdf", "buffer": PDF})
        self.esperar_aviso("Recibo lido")
        self.esperar()

    def plano_de_novembro(self):
        return [(l["valor"], l.get("pulado", False)) for l in self.dados()["lancamentos"] if l.get("recorrencia") == "r-plano" and l.get("competencia") == "2026-11"]

    def test_recibo_com_plano_de_outro_valor_lanca_so_neste_mes(self):
        self.abrir_salario()
        self.ler_recibo(HOLERITE)
        self.assertEqual(self.js("[window.__recibo.modo, window.__recibo.anexo.b64.startsWith('data:application/pdf')]"), ["holerite", True])
        self.assertEqual(self.ligados(), ["Plano de saúde · valor do recibo neste mês − R$ 300,00"])
        self.assertEqual(self.limpo("#folhas .desc-conf"), "Confere com o líquido do recibo: R$ 3.850,00.")
        self.clicar('#folhas [data-a="lf-salvar"][data-v="este"]')
        self.assertIsNone(self.folha())
        self.assertEqual(self.plano_de_novembro(), [(300, False)], "o plano de novembro com o valor do recibo")
        d = self.dados()
        self.assertEqual(next(r for r in d["recorrencias"] if r["id"] == "r-plano")["valor"], 250, "o fixo continua 250 nos outros meses")
        sal = next(l for l in d["lancamentos"] if l.get("recorrencia") == "r-sal")
        self.assertEqual([(x["descricao"], x["modo"], x["valor"]) for x in sal["descontos"]], [("INSS", "pct", 11), ("Imposto de renda", "pct", 6)])

    def test_recibo_atualiza_o_plano_ja_lancado_no_mes(self):
        mes = {"id": "l-plano-nov", "tipo": "despesa", "descricao": "Plano de saúde", "valor": 250, "data": "2026-11-05", "recorrencia": "r-plano",
               "competencia": "2026-11", "categoria": "c-saude", "vinculo": "r-sal", "pago": False}
        self.abrir_salario([mes])
        self.ler_recibo(HOLERITE)
        self.clicar('#folhas [data-a="lf-salvar"][data-v="este"]')
        self.assertEqual(self.plano_de_novembro(), [(300, False)], "o mesmo lançamento, com o valor novo (sem repetir)")

    def test_recibo_com_o_mesmo_valor_nao_mexe_no_plano(self):
        self.abrir_salario()
        igual = dict(HOLERITE, debitos=HOLERITE["debitos"][:2] + [{"descricao": "Plano de saúde", "valor": 250, "tipo": "saude"}], total_debitos=1100, liquido=3900)
        self.ler_recibo(igual)
        self.clicar('#folhas [data-a="lf-salvar"][data-v="este"]')
        self.assertEqual(self.plano_de_novembro(), [], "nada novo: o fixo de 250 já vale")

    # (era bug até a 1.24.3)
    def test_recibo_com_o_plano_pulado_no_mes_volta_a_lancar_o_plano(self):
        # BUG: com o plano pulado em novembro, o recibo lido mostra o plano como "nova despesa fixa ligada" e o desconta do líquido
        # (confere com o recibo), mas ao salvar o app só muda o valor do lançamento pulado: ele continua pulado e não entra no caixa,
        # e nenhuma despesa nova é criada. O caixa de novembro não bate com o recibo.
        pulado = {"id": "l-plano-nov", "tipo": "despesa", "descricao": "Plano de saúde", "valor": 250, "data": "2026-11-05", "recorrencia": "r-plano",
                  "competencia": "2026-11", "categoria": "c-saude", "vinculo": "r-sal", "pago": False, "pulado": True}
        self.abrir_salario([pulado])
        self.ler_recibo(HOLERITE)
        self.assertEqual(self.limpo("#folhas .desc-conf"), "Confere com o líquido do recibo: R$ 3.850,00.")
        self.clicar('#folhas [data-a="lf-salvar"][data-v="este"]')
        self.assertEqual(self.plano_de_novembro(), [(300, False)], "o plano de 300 entra em novembro")

    def ler_com_ia(self, itens):
        self.trocar_api("iaLer", "async c => ({ lancamentos: " + json.dumps(itens) + ", investimentos: [], entidade: 'ai_task.ia_da_casa' })")
        self.clicar('#nav [data-a="novo"]')
        self.clicar('#folhas .op[data-a="ia"]')

    def test_lancar_todos_no_cartao_de_credito(self):
        self.abrir(base(bancos=BANCOS))
        pix = dict(LANC_MERCADO, tipo="receita", descricao="Pix do Beto", valor=150, categoria="c-reembolso")
        self.ler_com_ia([LANC_MERCADO, pix])
        self.preencher("#ia-txt", "gastei 45 no mercado e o Beto mandou 150")
        self.clicar('#folhas [data-a="ia-ler"]')
        self.pg.wait_for_function("window.GERENCIA_TESTE.IAS.etapa === 'revisao'")
        self.esperar()
        self.clicar('#folhas [data-a="iac-conta"][data-v="k-verde"]')
        self.assertEqual(self.conta('#folhas [data-a="iac-cartao"]'), 0, "conta sem cartão: sem a escolha")
        self.clicar('#folhas [data-a="iac-conta"][data-v="k-ana"]')
        self.clicar('#folhas [data-a="iac-cartao"][data-v="1"]')
        self.assertEqual(self.js("T.IAS.itens.map(i => [i.descricao, i.noCartao])"), [["Mercado", True], ["Pix do Beto", False]], "só o gasto vai para o cartão")
        self.assertIn("na fatura", self.texto("#folhas .ia-item"))
        self.assertEqual(self.limpo('#folhas [data-a="iac-cartao"].on'), "Cartão de crédito")
        self.clicar('#folhas [data-a="iac-cartao"][data-v=""]')
        self.assertEqual(self.js("T.IAS.itens.map(i => i.noCartao)"), [False, False])
        self.clicar('#folhas [data-a="iac-cartao"][data-v="1"]')
        self.clicar('#folhas [data-a="ia-salvar"]')
        self.pg.wait_for_function("!window.GERENCIA_TESTE.IAS")
        self.esperar()
        self.assertEqual([(l["descricao"], l["conta"], l["cartao"]) for l in self.dados()["lancamentos"]],
                         [("Mercado", "k-ana", True), ("Pix do Beto", "k-ana", False)])

    def test_tirar_o_arquivo_da_leitura(self):
        self.abrir(base(bancos=BANCOS))
        self.ler_com_ia([LANC_MERCADO])
        self.galeria('#folhas [data-a="ia-arq"]').set_files({"name": "fatura-azul.pdf", "mimeType": "application/pdf", "buffer": PDF})
        self.pg.wait_for_function("window.GERENCIA_TESTE.IAS.arquivo")
        self.esperar()
        self.assertEqual(self.limpo("#folhas .ia-prev b"), "fatura-azul.pdf")
        self.assertFalse(self.pg.locator('#folhas [data-a="ia-ler"]').is_disabled())
        self.clicar('#folhas [data-a="ia-arq-rm"]')
        self.assertEqual((self.js("T.IAS.arquivo"), self.conta("#folhas .ia-prev")), (None, 0))
        self.assertTrue(self.pg.locator('#folhas [data-a="ia-ler"]').is_disabled(), "sem arquivo nem texto, não há o que ler")
        self.assertEqual(self.conta('#folhas [data-a="ia-arq"]'), 1, "o botão de escolher volta")


# ---------------------------------------------------------------------------------------------------------------
class TestCasosDeCanto(TelaSistema):
    """Pequenas coisas: datas da última verificação, dicas sendo conferidas, sugestões de banco, relatório na prévia."""

    def test_quando_foi_a_ultima_verificacao(self):
        self.abrir(base())
        r = self.js("['2026-11-02T09:15:00-03:00', '2026-11-01T21:05:00-03:00', '2026-10-28T14:20:00-03:00', '2025-12-30T08:00:00-03:00', 'ontem'].map(T.quandoLongo)")
        self.assertEqual(r, ["hoje às 09:15", "ontem às 21:05", "28/10 às 14:20", "30/12/2025 às 08:00", ""])

    def test_imposto_do_recibo_vira_porcentagem_redonda_quando_bate(self):
        self.abrir(base())
        r = self.js("[[550, 5000], [300, 5000], [123.45, 5000], [1000, 3333.33], [0, 5000], [100, 0]].map(([v, b]) => T.pctDoBruto(v, b))")
        self.assertEqual(r, [11, 6, 2.469, 30, 0, 0], "uma casa quando reproduz o valor (30% de 3.333,33 dá 1.000,00 nos centavos); "
                                                      "senão até 4 casas; sem bruto ou sem valor, 0")

    def test_navegador_sem_camera_explica_e_oferece_escolher_a_foto(self):
        self.abrir(base(bancos=BANCOS))
        self.clicar('#nav [data-a="novo"]')
        self.clicar('#folhas .op[data-a="ia"]')
        self.js("(Object.defineProperty(navigator, 'mediaDevices', { value: undefined, configurable: true }), true)")
        self.addCleanup(lambda: self.js("(delete navigator.mediaDevices, true)"))
        self.clicar('#folhas [data-a="ia-cam"]')
        self.assertEqual(self.limpo("#camera .cam-msg p"), "Este navegador não deixa usar a câmera aqui. Dá para tirar a foto pelo celular e escolher.",
                         "com https mas sem a câmera no navegador")
        self.assertEqual(self.limpo('#camera [data-a="cam-galeria"]'), "Tirar ou escolher foto")
        self.js("(T.fecharCamera(true), true)")

    def test_dicas_mostram_a_ultima_verificacao(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "caixa"})
        self.js("(T.S.dicas = { dicas: [], assinaturas: [], conferindo: false, catalogo: ['Spotify'], atualizado: '2026-11-01T21:05:00-03:00' }, T.render(), true)")
        self.assertEqual(self.limpo("#dicas .dica-quando"), "Última verificação: ontem às 21:05.")

    def test_dicas_sendo_conferidas_aparecem_no_inicio(self):
        luz = {"id": "l-luz", "tipo": "despesa", "descricao": "Luz", "valor": 180, "data": "2026-11-01", "pago": True, "categoria": "c-contas"}
        self.abrir(base(bancos=BANCOS, lancamentos=[luz]))
        self.js("(T.S.dicas = { dicas: [], assinaturas: [{ chave: 'r:x', status: 'conferindo', nome: 'Spotify', descricao: 'Spotify', valor: 23.9 }], conferindo: true }, T.render(), true)")
        self.assertEqual(self.limpo(".card.dicas .dica-conf"), "Conferindo os preços das suas assinaturas nas páginas oficiais…")

    def test_sugestao_de_banco_abre_o_cadastro_com_o_nome(self):
        self.abrir(base(), ui={"tab": "mais", "maisTela": "bancos"})
        nome = self.js("document.querySelector('[data-a=\"banco-sug\"]').dataset.v")
        self.clicar('[data-a="banco-sug"]')
        self.assertEqual((self.folha(), self.pg.input_value("#b-nome")), ("Novo banco", nome))

    def test_adicionar_recebimento_e_lancar_um_fixo(self):
        self.abrir(base(bancos=BANCOS))
        self.clicar('#nav [data-a="novo"]')
        self.clicar('#folhas [data-a="lanc-novo"][data-v="receita"]')
        self.assertEqual((self.folha(), self.js("T.LF.tipo")), ("Novo recebimento", "receita"))
        self.voltar()
        self.ir_mais("caixa")
        self.assertIn("Ao lançar, escolha Repetir: Todo mês ou Todo ano.", self.texto("#fixos"), "sem fixos, o card explica")
        self.clicar('#fixos [data-a="lanc-novo"]')
        self.assertEqual((self.folha(), self.js("T.LF.tipo")), ("Nova despesa", "despesa"))

    def test_tirar_uma_pessoa_do_banco(self):
        self.abrir(base(bancos=BANCOS), ui={"tab": "mais", "maisTela": "bancos"})
        self.clicar('#bancos [data-a="banco"][data-id="b-azul"]')
        self.assertEqual(self.conta('#folhas [data-a="bc-rm"]'), 2)
        self.clicar('#folhas [data-a="bc-rm"][data-i="1"]')
        self.assertEqual(self.conta('#folhas [data-a="bc-rm"]'), 0, "com uma pessoa só, não dá para tirar")
        self.clicar('#folhas [data-a="b-salvar"]')
        self.assertIsNone(self.folha())
        self.assertEqual([c["pessoa"] for c in self.dados()["bancos"][0]["contas"]], ["Ana"], "o Beto saiu do Banco Azul")

    def test_observacao_do_investimento_abre_e_guarda_o_texto(self):
        self.abrir(base(bancos=BANCOS, investimentos=[RESERVA]), ui={"tab": "investimentos"})
        self.clicar('#app [data-a="inv"][data-id="res-verde"]')
        self.assertEqual(self.conta('#folhas [data-f="obs"]'), 0)
        self.clicar('#folhas [data-a="f-obs"]')
        self.preencher('#folhas [data-f="obs"]', "Reserva de emergência da casa")
        self.clicar('#folhas [data-a="f-salvar"]:not([data-mais])')
        self.assertIsNone(self.folha())
        self.assertEqual(self.dados()["investimentos"][0]["obs"], "Reserva de emergência da casa")

    def test_relatorio_e_arquivos_na_previa_explicam(self):
        self.abrir(base(), ui={"tab": "mais"})
        self.clicar('#app .menu-row[data-a="relatorio"]')
        self.assertEqual(self.esperar_aviso("relatório"), "Na prévia o relatório não abre.")
        self.ir_mais("config", "dados")
        self.assertEqual(self.conta('#exportar [data-a="relatorio"]'), 0, "o relatório saiu de Exportar: tem a sua linha no menu")
        self.clicar('#exportar [data-a="demo-arq"]')
        self.assertEqual(self.esperar_aviso("arquivos"), "Na prévia os arquivos não são baixados.")


if __name__ == "__main__":
    unittest.main()
