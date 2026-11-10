"""Tela: faturas por e-mail. O aviso no Início, a conferência do que a IA leu, o PDF com senha, ler de novo e
ignorar; o cartão em Mais › Configurações › Integrações (conta de e-mail, De quem, Recebidos) e o aviso no celular em
Opções. A lista de e-mails vem da api da prévia (T.api._emails), com faturas e remetentes inventados."""
import unittest

from tests.tela_base import Tela, base, BANCOS

SEM_ANIMACAO = "*, *::before, *::after { transition: none !important; animation: none !important; }"


def lanc(desc, valor, cat="c-mercado", dia="2026-11-01", tipo="despesa"):
    return {"tipo": tipo, "descricao": desc, "valor": valor, "data": dia, "categoria": cat, "parcela_atual": 0, "parcelas_total": 0,
            "cartao": True, "banco": "Banco Azul", "situacao": "", "confianca": "alta"}


def email(n, estado, de="Banco Azul", assunto=None, **mais):
    it = {"id": f"e0000000000{n}", "de": de, "endereco": "fatura@" + de.lower().replace(" ", "") + ".com.br", "assunto": assunto or f"Fatura {n}",
          "arquivo": f"fatura-{n}.pdf", "data": "2026-11-01T08:00:00", "recebido_em": "2026-11-01T08:00:05", "estado": estado, "erro": ""}
    if estado == "conferir":
        it["resultado"] = {"lancamentos": [lanc("Mercado Bom", 123.45), lanc("Farmácia Sol", 45.9, "c-saude", "2026-11-02")], "investimentos": []}
    it.update(mais)
    return it


INTEG = {"tab": "mais", "maisTela": "config", "maisAba": "integracoes"}


class TelaEmail(Tela):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pg.add_style_tag(content=SEM_ANIMACAO)
        cls.pg.set_default_timeout(5000)

    def abrir_com(self, itens=(), ui=None, **aj):
        """Abre com a opção ligada (e estes ajustes) e estes e-mails na api da prévia."""
        ajustes = dict({"email": True, "email_de": []}, **aj)
        self.js("(T.api._emails = a, T.S.emails = undefined, T.S.emailsPedido = null, clearTimeout(T.S.emailsTimer), true)", list(itens))
        self.abrir(base(bancos=BANCOS, lancamentos=[{"id": "l1", "tipo": "despesa", "descricao": "Feira", "valor": 10, "data": "2026-11-01", "categoria": "c-mercado", "pago": True}],
                        ajustes=ajustes), ui=ui)
        self.js("T.carregarEmails()")
        self.esperar()

    def trocar_api(self, nome, corpo_js):
        """Troca uma função da api por uma falsa (JavaScript) até o fim do teste (trocar de novo vale a última)."""
        primeira = self.js("!(window.__api0 && a in window.__api0)", nome)
        self.js("(window.__api0 = window.__api0 || {}, (a[0] in window.__api0) || (window.__api0[a[0]] = T.api[a[0]]), "
                "T.api[a[0]] = new Function('return (' + a[1] + ')')(), true)", [nome, corpo_js])
        if primeira:
            self.addCleanup(lambda: self.js("(T.api[a] = window.__api0[a], delete window.__api0[a], true)", nome))

    def avisos(self):
        return self.js("[...document.querySelectorAll('[data-a=\"email-abrir\"]')].map(b => [b.querySelector('.op-t b').textContent, b.querySelector('.op-t span').textContent, (b.querySelector('.op-n') || {}).textContent || ''])")

    def estados(self):
        return self.js("T.api._emails.map(x => x.estado)")


# ---------------------------------------------------------------------------------------------------------------
class TestAvisoNoInicio(TelaEmail):
    def test_cada_fatura_pendente_aparece_nos_avisos(self):
        self.abrir_com([email(1, "conferir"), email(2, "senha", "Banco Verde"), email(3, "lendo", "Banco Lua"), email(4, "erro", "Banco Sol", erro="Sem resposta do Home Assistant."),
                        email(5, "fora", "Loja"), email(6, "feito"), email(7, "ignorado")])
        self.assertEqual(self.avisos(), [["Fatura Banco Azul", "Por e-mail · 2 lançamentos", "R$ 169"],
                                         ["Fatura Banco Verde", "Por e-mail · o PDF tem senha", ""],
                                         ["Fatura Banco Lua", "Por e-mail · lendo com IA…", ""],
                                         ["Fatura Banco Sol", "Por e-mail · Sem resposta do Home Assistant.", ""]])
        self.assertTrue(self.js("document.querySelector('[data-a=\"email-abrir\"][data-v=\"e00000000003\"]').disabled"), "lendo: ainda não dá para abrir")
        self.assertEqual(self.js("document.querySelector('.rot-t') && [...document.querySelectorAll('.rot-t')].map(e => e.textContent).includes('Avisos')"), True)

    def test_foto_do_whatsapp_tambem_aparece(self):
        """O CorrerIA: uma foto ou PDF lido pelo WhatsApp fica para conferir no Início, mesmo com o e-mail desligado."""
        zap = email(8, "conferir", "Ana", assunto="", origem="whatsapp", endereco="", arquivo="Foto")
        self.abrir_com([zap, email(1, "conferir")], email=False, correria=True)
        self.assertEqual(self.avisos(), [["Enviado por Ana", "Pelo WhatsApp · 2 lançamentos", "R$ 169"]], "a fatura do e-mail não (e-mail desligado)")
        self.clicar('[data-a="email-abrir"]')
        self.assertEqual(self.folha(), "Conferir lançamentos")
        self.assertEqual(self.textos("#folhas .folha-pe .btn")[0], "Ignorar")
        self.clicar('#folhas [data-a="email-ignorar"]')
        self.assertEqual(self.estados()[0], "ignorado")
        self.abrir_com([zap], email=False, correria=False)
        self.assertEqual(self.avisos(), [], "sem o CorrerIA e sem o e-mail, nada")

    def test_foto_do_whatsapp_fora_dos_recebidos_do_email(self):
        zap = email(8, "fora", "Ana", origem="whatsapp", endereco="")
        self.abrir_com([zap, email(1, "conferir")], ui=INTEG, correria=True)
        self.assertEqual(self.js("[...document.querySelectorAll('#email .email-l b')].map(b => b.textContent)"), ["Banco Azul"])

    def test_some_com_a_opcao_ou_a_ia_desligada(self):
        self.abrir_com([email(1, "conferir")], email=False)
        self.assertEqual(self.avisos(), [])
        self.abrir_com([email(1, "conferir")], ia=False)
        self.assertEqual(self.avisos(), [])

    def test_lendo_olha_de_novo_sozinho(self):
        self.abrir_com([email(1, "lendo")])
        self.assertTrue(self.js("!!T.S.emailsTimer"))
        self.js("(T.api._emails[0] = a, true)", email(1, "conferir"))
        self.pg.wait_for_function("() => document.querySelector('[data-a=\"email-abrir\"]') && !document.querySelector('[data-a=\"email-abrir\"]').disabled", timeout=8000)
        self.assertEqual(self.avisos()[0][1], "Por e-mail · 2 lançamentos")


class TestConferir(TelaEmail):
    def test_tocar_abre_a_conferencia_com_o_que_a_ia_leu(self):
        self.abrir_com([email(1, "conferir")])
        self.clicar('[data-a="email-abrir"]')
        self.assertEqual(self.folha(), "Conferir lançamentos")
        self.assertEqual(self.textos("#folhas .ia-item-t b"), ["Mercado Bom", "Farmácia Sol"])
        self.assertEqual(self.textos("#folhas .folha-pe .btn"), ["Ignorar", "Lançar 2 · −R$ 169"])

    def test_lancar_grava_e_marca_a_fatura_como_lancada(self):
        self.abrir_com([email(1, "conferir")])
        self.clicar('[data-a="email-abrir"]')
        self.clicar('#folhas [data-a="ia-salvar"]')
        self.pg.wait_for_function("() => !window.GERENCIA_TESTE.FOLHA")
        self.pg.wait_for_function("() => window.GERENCIA_TESTE.api._emails[0].estado === 'feito'")
        self.esperar()
        self.assertEqual(sorted(l["descricao"] for l in self.dados()["lancamentos"]), ["Farmácia Sol", "Feira", "Mercado Bom"])
        self.assertEqual(self.js("T.S.ui.tab"), "caixa", "vai para o Caixa, como a leitura por IA")
        self.ir("inicio")
        self.assertEqual(self.avisos(), [], "o aviso some")

    def test_ignorar_fecha_sem_lancar(self):
        self.abrir_com([email(1, "conferir")])
        self.clicar('[data-a="email-abrir"]')
        self.clicar('#folhas [data-a="email-ignorar"]')
        self.assertEqual(self.aviso(), "Fatura ignorada")
        self.assertEqual((self.niveis(), self.estados()), (0, ["ignorado"]))
        self.assertEqual([l["descricao"] for l in self.dados()["lancamentos"]], ["Feira"])
        self.assertEqual(self.avisos(), [])

    def test_voltar_do_celular_fecha_e_a_fatura_continua_esperando(self):
        self.abrir_com([email(1, "conferir")])
        self.clicar('[data-a="email-abrir"]')
        self.voltar()
        self.assertEqual((self.niveis(), self.estados()), (0, ["conferir"]))
        self.assertEqual(len(self.avisos()), 1)

    def test_erro_le_de_novo(self):
        self.abrir_com([email(1, "erro", erro="Sem resposta do Home Assistant.")])
        self.clicar('[data-a="email-abrir"]')
        self.assertEqual(self.aviso(), "Lendo de novo")
        self.assertEqual(self.estados(), ["lendo"])
        self.assertEqual(self.niveis(), 0, "não abre janela")
        self.assertEqual(self.avisos()[0][1], "Por e-mail · lendo com IA…")


class TestSenha(TelaEmail):
    PDF = "data:application/pdf;base64,JVBERi0xLjQKJSBmYXR1cmEgaW52ZW50YWRhCiUlRU9GCg=="

    SEM_SENHA = ("async c => { window.__ped.push(c); if (!c.senha) throw Object.assign(new Error('Nenhuma das senhas cadastradas abre este PDF.'), "
                 "{ codigo: 'senha_pdf' }); return { lancamentos: [{ tipo: 'despesa', descricao: 'Posto Bom', valor: 80, data: '2026-11-01', "
                 "categoria: 'c-transporte', cartao: true }], investimentos: [] }; }")

    def test_tenta_as_senhas_cadastradas_e_so_entao_pede_a_senha(self):
        self.abrir_com([email(2, "senha", "Banco Verde", erro="Este PDF tem senha.")])
        self.trocar_api("emailPdf", "async id => ({ b64: '" + self.PDF + "', nome: 'fatura-2.pdf' })")
        self.js("(window.__ped = [], true)")
        self.trocar_api("iaLer", self.SEM_SENHA)
        self.clicar('[data-a="email-abrir"]')
        self.pg.wait_for_selector("#ia-senha")
        self.assertEqual(self.folha(), "Escolher fotos ou PDF", "só o arquivo, sem as outras opções")
        self.assertEqual(self.texto("#folhas .ia-prev b"), "fatura-2.pdf")
        self.assertEqual(self.texto("#folhas .msg-erro"), "Nenhuma das senhas cadastradas abre este PDF.")
        self.pg.wait_for_function("document.activeElement && document.activeElement.id === 'ia-senha'")
        self.assertEqual([("senha" in p, p["anexo"]["b64"]) for p in self.js("window.__ped")], [(False, self.PDF)], "primeiro sem digitar nada")

    def test_uma_senha_cadastrada_abre_direto(self):
        # a senha entrou depois que o e-mail chegou (digitada em outra fatura): abre sem pedir
        self.abrir_com([email(2, "senha", "Banco Verde", erro="Este PDF tem senha.")])
        self.trocar_api("emailPdf", "async id => ({ b64: '" + self.PDF + "', nome: 'fatura-2.pdf' })")
        self.trocar_api("iaLer", "async c => ({ lancamentos: [{ tipo: 'despesa', descricao: 'Posto Bom', valor: 80, data: '2026-11-01', categoria: 'c-transporte' }], investimentos: [] })")
        self.clicar('[data-a="email-abrir"]')
        self.pg.wait_for_function("() => window.GERENCIA_TESTE.IAS && window.GERENCIA_TESTE.IAS.etapa === 'revisao'")
        self.assertEqual(self.folha(), "Conferir lançamentos")
        self.assertEqual(self.conta("#ia-senha"), 0)

    def test_com_a_senha_le_e_ao_lancar_marca_a_fatura(self):
        self.abrir_com([email(2, "senha", "Banco Verde")])
        self.trocar_api("emailPdf", "async id => ({ b64: '" + self.PDF + "', nome: 'fatura-2.pdf' })")
        self.js("(window.__ped = [], true)")
        self.trocar_api("iaLer", self.SEM_SENHA)
        self.clicar('[data-a="email-abrir"]')
        self.pg.wait_for_selector("#ia-senha")
        self.preencher("#ia-senha", "12345")
        self.clicar('#folhas [data-a="ia-ler"]')
        self.pg.wait_for_function("() => window.GERENCIA_TESTE.IAS && window.GERENCIA_TESTE.IAS.etapa === 'revisao'")
        p = self.js("window.__ped[1]")
        self.assertEqual((p["senha"], p["guardar_senha"], p["nome_arquivo"], p["anexo"]["b64"]), ("12345", True, "fatura-2.pdf", self.PDF))
        self.assertEqual(self.textos("#folhas .folha-pe .btn")[0], "Ignorar")
        self.clicar('#folhas [data-a="ia-salvar"]')
        self.pg.wait_for_function("() => window.GERENCIA_TESTE.api._emails[0].estado === 'feito'")

    def test_pdf_que_sumiu(self):
        self.abrir_com([email(2, "senha", "Banco Verde")])
        self.clicar('[data-a="email-abrir"]')  # a prévia não tem o PDF
        self.pg.wait_for_function("() => (document.querySelector('#folhas .msg-erro') || {}).textContent === 'Na prévia não há PDF.'")
        self.assertEqual(self.conta("#ia-senha"), 0)


# ---------------------------------------------------------------------------------------------------------------
class TestCartaoIntegracoes(TelaEmail):
    def cartao(self):
        return self.texto("#email")

    def test_comeca_desligado_e_ligar_mostra_a_conta(self):
        self.abrir_com([], ui=INTEG, email=False)
        self.assertEqual(self.texto("#email h2"), "Faturas por e-mail")
        self.assertIn("Desligado.", self.cartao())
        self.assertEqual(self.conta("#email-de"), 0)
        self.clicar('#email [data-a="ajuste"][data-k="email"]')
        self.assertTrue(self.dados()["ajustes"]["email"])
        self.pg.wait_for_selector("#email .status")
        self.assertEqual(self.texto("#email .status"), "ana@exemplo.com")
        self.assertIn("Ligado: recebendo os e-mails pelo Home Assistant.", self.cartao())
        self.assertIn("Sem nenhum, os e-mails com PDF e “fatura”, “boleto”, “recibo” ou “assinatura” no assunto.", self.cartao())

    def test_some_sem_a_ia(self):
        self.abrir_com([], ui=INTEG, ia=False)
        self.assertEqual(self.conta("#email"), 0)

    def test_sem_conta_de_email_explica_o_que_fazer(self):
        self.abrir_com([], ui=INTEG)
        self.trocar_api("emails", "async () => ({ ligado: true, conectada: true, contas: [], itens: [] })")
        self.js("(T.S.emails = undefined, T.render(), T.carregarEmails())")
        self.esperar()
        self.assertEqual(self.texto("#email .status"), "Nenhuma conta de e-mail no Home Assistant. Adicione a integração IMAP: no Gmail, imap.gmail.com, porta 993, com uma senha de app.")

    def test_conta_com_erro_e_sem_resposta(self):
        self.abrir_com([], ui=INTEG)
        self.trocar_api("emails", "async () => ({ ligado: true, conectada: false, contas: [{ id: 'e', nome: 'ana@exemplo.com', ok: false }], itens: [] })")
        self.js("(T.S.emails = undefined, T.render(), T.carregarEmails())")
        self.esperar()
        self.assertEqual(self.texto("#email .status"), "ana@exemplo.com (com erro no Home Assistant) · conectando…")
        self.assertTrue(self.js("document.querySelector('#email .status').classList.contains('manual')"))
        self.trocar_api("emails", "async () => ({ ligado: true, conectada: false, contas: null, itens: [] })")
        self.js("(T.S.emails = undefined, T.render(), T.carregarEmails())")
        self.esperar()
        self.assertEqual(self.texto("#email .status"), "Não consegui ver as contas de e-mail do Home Assistant.")

    def test_de_quem_adicionar_e_tirar(self):
        self.abrir_com([], ui=INTEG)
        self.preencher("#email-de", "Banco Azul <Fatura@BancoAzul.com.br>")
        self.clicar('#email [data-a="email-de-add"]')
        self.preencher("#email-de", "@bancoverde.com.br")
        self.pg.press("#email-de", "Enter")
        self.esperar()
        self.clicar('#email [data-a="email-de-add"]')  # vazio: nada
        self.assertEqual(self.dados()["ajustes"]["email_de"], ["fatura@bancoazul.com.br", "bancoverde.com.br"])
        self.assertEqual(self.textos("#email .email-de .chip"), ["fatura@bancoazul.com.br", "bancoverde.com.br"])
        self.assertIn("Só os e-mails desses remetentes.", self.cartao())
        self.clicar('#email [data-a="email-de-rm"][data-v="fatura@bancoazul.com.br"]')
        self.assertEqual(self.dados()["ajustes"]["email_de"], ["bancoverde.com.br"])
        self.preencher("#email-de", "bancoverde.com.br")
        self.clicar('#email [data-a="email-de-add"]')
        self.assertEqual(self.dados()["ajustes"]["email_de"], ["bancoverde.com.br"], "sem repetir")

    def test_recebidos_com_o_estado_e_ler(self):
        self.abrir_com([email(1, "conferir"), email(2, "senha", "Banco Verde"), email(3, "fora", "Loja", "Seu boleto"), email(4, "feito"), email(5, "ignorado"), email(6, "erro")], ui=INTEG)
        linhas = self.js("[...document.querySelectorAll('#email .email-l')].map(l => [l.querySelector('b').textContent, l.querySelector('small').textContent, l.querySelector('em, button').textContent])")
        self.assertEqual(linhas, [["Banco Azul", "Fatura 1 · 01/11", "Para conferir"], ["Banco Verde", "Fatura 2 · 01/11", "Precisa da senha"],
                                  ["Loja", "Seu boleto · 01/11", "Ler"], ["Banco Azul", "Fatura 4 · 01/11", "Lançada"], ["Banco Azul", "Fatura 6 · 01/11", "Ler"]],
                         "os 5 últimos; o que não parecia fatura e o com erro dá para ler")
        # o ignorado fica no fim, recolhido (pedido do dono: o que foi ignorado de propósito, recolhido)
        self.assertEqual(self.texto('#email [data-a="recolher"][data-v="email-ignorados"]'), "Ignorados (1)")
        self.clicar('#email [data-a="recolher"][data-v="email-ignorados"]')
        self.assertEqual(self.textos('#email [data-rec="email-ignorados"] .email-l small'), ["Fatura 5 · 01/11"])
        self.assertEqual(self.texto('#email [data-rec="email-ignorados"] [data-a="email-ler"]'), "Ler")
        self.clicar('#email [data-a="email-ler"][data-v="e00000000003"]')
        self.assertEqual(self.aviso(), "Lendo com IA")
        self.assertEqual(self.estados()[2], "lendo")
        self.assertEqual(self.js("[...document.querySelectorAll('#email .email-l')].filter(l => l.scrollWidth > l.clientWidth + 1).length"), 0, "nada sai da linha")

    def test_procurar_faturas_agora(self):
        self.abrir_com([], ui=INTEG)
        self.assertEqual(self.texto("#email [data-a=\"email-procurar\"]"), "Procurar faturas agora")
        self.assertEqual(self.texto("#email .email-procurar + .ajuda"), "Abre os 30 e-mails mais novos e lê as faturas que achar.")
        rodando = "{ ligado: true, conectada: true, contas: [{ id: 'e', nome: 'ana@exemplo.com', ok: true }], itens: [], procura: { rodando: true, vistos: 3, total: 30, pdfs: 0, achados: 0, erro: '', etapa: 'Abrindo os e-mails de ana@exemplo.com…', fim: null } }"
        self.trocar_api("emailProcurar", f"async () => ({rodando})")
        self.trocar_api("emails", f"async () => ({rodando})")
        self.clicar('#email [data-a="email-procurar"]')
        self.pg.wait_for_selector("#email .email-procurar[disabled]")
        self.assertEqual(self.texto("#email .email-procurar"), "Procurando… 3 de 30")
        self.assertEqual(self.texto("#email .email-procurar + .ajuda"), "Abrindo os e-mails de ana@exemplo.com…")
        self.trocar_api("emails", "async () => ({ ligado: true, conectada: true, contas: [{ id: 'e', nome: 'ana@exemplo.com', ok: true }], itens: [], procura: { rodando: false, vistos: 30, total: 30, pdfs: 3, achados: 2, erro: '', etapa: '', fim: '2026-11-02T10:00:00' } })")
        self.pg.wait_for_function("() => (document.querySelector('#email .email-procurar + .ajuda') || {}).textContent === 'Achei 2 faturas nos 30 e-mails mais novos.'", timeout=8000)
        self.assertEqual(self.texto("#email [data-a=\"email-procurar\"]"), "Procurar faturas agora", "olha de novo sozinho enquanto procura")
        self.trocar_api("emails", "async () => ({ ligado: true, conectada: true, contas: [{ id: 'e', nome: 'ana@exemplo.com', ok: true }], itens: [], procura: { rodando: false, vistos: 30, total: 30, pdfs: 1, achados: 0, erro: '', etapa: '', fim: '2026-11-02T10:00:00' } })")
        self.js("T.carregarEmails()")
        self.esperar()
        self.assertEqual(self.texto("#email .email-procurar + .ajuda"), "Nenhuma fatura nos 30 e-mails mais novos; o PDF que achei está em Recebidos.")

    def test_procurar_na_previa_explica(self):
        self.abrir_com([], ui=INTEG)
        self.clicar('#email [data-a="email-procurar"]')
        self.assertEqual(self.aviso(), "Na prévia não há caixa de entrada.")
        self.assertFalse(self.js("document.querySelector('#email .email-procurar').disabled"))

    def test_sem_conta_funcionando_sem_procurar(self):
        self.abrir_com([], ui=INTEG)
        self.trocar_api("emails", "async () => ({ ligado: true, conectada: false, contas: [{ id: 'e', nome: 'ana@exemplo.com', ok: false }], itens: [] })")
        self.js("(T.S.emails = undefined, T.render(), T.carregarEmails())")
        self.esperar()
        self.assertEqual(self.conta("#email .email-procurar"), 0)

    def test_ordem_dos_cartoes(self):
        self.abrir_com([], ui=INTEG)
        self.assertEqual(self.js("[...document.querySelectorAll('#app section.card')].map(s => s.id)"),
                         ["outros-apps", "bens", "correria", "ia", "uso-ia", "email", "senhas-pdf", "sensores"])


class TestRemetente(TelaEmail):
    """Recebidos › ⋯: Sempre é um fixo (lido sempre; o valor vai para o fixo do mês, que pode ser criado ali) e Nunca
    considerar (some dos Recebidos e do Início); as regras ficam listadas e saem pela lixeira."""
    FIXO = {"id": "r-nuvem", "tipo": "despesa", "descricao": "Nuvem Sol", "valor": 30, "dia": 5, "categoria": "c-assinaturas", "conta": "k-verde", "cartao": False,
            "obs": "", "inicio": "2026-01", "fim": None}

    def abrir_rem(self, itens, regras=(), recorrencias=(), ui=INTEG):
        self.js("(T.api._emails = a, T.S.emails = undefined, T.S.emailsPedido = null, clearTimeout(T.S.emailsTimer), true)", list(itens))
        self.abrir(base(bancos=BANCOS, recorrencias=list(recorrencias), ajustes={"email": True, "email_de": [], "email_remetentes": list(regras)}), ui=ui)
        self.js("T.carregarEmails()")
        self.esperar()

    def test_nunca_considerar(self):
        self.abrir_rem([email(1, "conferir"), email(2, "fora", "Loja Lua", "Seu boleto")])
        self.clicar('#email [data-a="email-remetente"][data-v="e00000000002"]')
        self.assertEqual(self.folha(), "E-mails deste remetente")
        self.assertEqual(self.textos("#folhas .chips .chip"), ["fatura@lojalua.com.br", "Todo o lojalua.com.br"])
        self.assertEqual(self.textos("#folhas .seg button"), ["Normal", "É um fixo", "Nunca"])
        self.clicar('#folhas [data-a="frem-de"][data-v="lojalua.com.br"]')
        self.clicar('#folhas [data-a="frem-acao"][data-v="nunca"]')
        self.assertEqual(self.texto("#folhas .ajuda"), "Não entra, mesmo com fatura ou boleto no assunto.")
        self.clicar('#folhas [data-a="frem-salvar"]')
        self.assertEqual(self.aviso(), "Os e-mails de lojalua.com.br não entram mais")
        self.assertEqual(self.dados()["ajustes"]["email_remetentes"], [{"de": "lojalua.com.br", "acao": "nunca"}])
        self.pg.wait_for_function("() => document.querySelectorAll('#email .emails .email-l').length === 1")
        # Nunca considerar fica no fim, recolhido
        self.assertEqual(self.texto('#email [data-a="recolher"][data-v="email-nunca"]'), "Nunca considerar (1)")
        self.assertEqual(self.conta("#email .email-regras .email-l"), 0, "fechado por padrão")
        self.clicar('#email [data-a="recolher"][data-v="email-nunca"]')
        self.assertEqual(self.textos("#email .email-regras .email-l b"), ["lojalua.com.br"])
        self.assertEqual(self.textos("#email .email-regras .email-l small"), ["Nunca considerar"])
        # tirar a regra: o e-mail volta
        self.clicar('#email [data-a="email-regra-rm"][data-v="lojalua.com.br"]')
        self.pg.wait_for_function("() => document.querySelectorAll('#email .emails .email-l').length === 2")
        self.assertEqual(self.dados()["ajustes"]["email_remetentes"], [])

    def test_sempre_um_fixo_novo_le_e_lanca_no_fixo(self):
        res = {"lancamentos": [lanc("Nuvem assinatura", 32.5, "c-outros-gastos", "2026-11-03")], "investimentos": []}
        self.abrir_rem([email(1, "fora", "Nuvem", "Subscription receipt")])
        self.clicar('#email [data-a="email-remetente"]')
        self.clicar('#folhas [data-a="frem-acao"][data-v="fixo"]')
        self.clicar('#folhas [data-a="frem-salvar"]')
        self.assertEqual(self.texto("#folhas .msg-erro"), "Escolha o fixo.")
        self.pg.select_option("#frem-fixo", "novo")
        self.assertEqual(self.pg.input_value("#frem-nome"), "Nuvem")
        self.assertEqual(self.texto("#folhas .frem-novo .ajuda"), "Todo dia 1, em Assinaturas. O valor vem da leitura do e-mail.")
        self.preencher("#frem-nome", "Nuvem Sol")
        # ao salvar, o e-mail que não parecia fatura já é lido (na prévia, a IA simulada devolve o recibo)
        self.trocar_api("emailAcao", "async function (acao, id) { const it = this._emails.find(x => x.id === id); it.estado = 'conferir'; it.resultado = " + __import__("json").dumps(res) + "; return this.emails(); }")
        self.clicar('#folhas [data-a="frem-salvar"]')
        self.assertEqual(self.aviso(), "Os e-mails de fatura@nuvem.com.br vão para Nuvem Sol")
        d = self.dados()
        fx = [r for r in d["recorrencias"] if r["descricao"] == "Nuvem Sol"][0]
        self.assertEqual({k: fx[k] for k in ("tipo", "valor", "dia", "categoria", "inicio", "fim")},
                         {"tipo": "despesa", "valor": 0, "dia": 1, "categoria": "c-assinaturas", "inicio": "2026-11", "fim": None})
        self.assertEqual(d["ajustes"]["email_remetentes"], [{"de": "fatura@nuvem.com.br", "acao": "fixo", "fixo": fx["id"]}])
        self.pg.wait_for_function("() => (document.querySelector('#email .email-fixo') || {}).textContent === 'Nuvem Sol'")
        # a conferência: a despesa vai para o fixo do mês
        self.ir("inicio")
        self.clicar('[data-a="email-abrir"]')
        self.assertEqual(self.texto("#folhas .ia-fixo"), "Fixo Nuvem Sol · nov/26")
        self.clicar('#folhas [data-a="ia-salvar"]')
        self.pg.wait_for_function("() => !window.GERENCIA_TESTE.FOLHA")
        self.esperar()
        d = self.dados()
        fx = [r for r in d["recorrencias"] if r["id"] == fx["id"]][0]
        self.assertEqual(fx["valor"], 32.5, "o fixo sem valor fica com o valor lido")
        lc = [l for l in d["lancamentos"] if l.get("recorrencia") == fx["id"]]
        self.assertEqual([(l["descricao"], l["valor"], l["competencia"], l["categoria"]) for l in lc], [("Nuvem Sol", 32.5, "2026-11", "c-assinaturas")])
        self.assertEqual([l for l in d["lancamentos"] if l["descricao"] == "Nuvem assinatura"], [], "sem lançamento solto")

    def test_fixo_ja_lancado_muda_o_valor_e_regra_listada(self):
        res = {"lancamentos": [lanc("Nuvem", 31.9, "c-outros-gastos", "2026-11-05")], "investimentos": []}
        mes = {"id": "l-nv", "tipo": "despesa", "descricao": "Nuvem Sol", "valor": 30, "data": "2026-11-05", "categoria": "c-assinaturas", "conta": "k-verde",
               "cartao": False, "pago": False, "recorrencia": "r-nuvem", "competencia": "2026-11", "obs": ""}
        self.js("(T.api._emails = a, T.S.emails = undefined, T.S.emailsPedido = null, clearTimeout(T.S.emailsTimer), true)", [email(1, "conferir", "Nuvem", resultado=res)])
        self.abrir(base(bancos=BANCOS, recorrencias=[self.FIXO], lancamentos=[mes],
                        ajustes={"email": True, "email_de": [], "email_remetentes": [{"de": "nuvem.com.br", "acao": "fixo", "fixo": "r-nuvem"}]}), ui=INTEG)
        self.js("T.carregarEmails()")
        self.esperar()
        self.assertEqual(self.textos("#email .email-regras small"), ["Fixo: Nuvem Sol"])
        self.clicar('#email [data-a="email-remetente"]')
        self.assertEqual(self.js("[T.FREM.de, T.FREM.acao, T.FREM.fixo]"), ["nuvem.com.br", "fixo", "r-nuvem"], "abre com a regra que vale")
        self.voltar()
        self.ir("inicio")
        self.clicar('[data-a="email-abrir"]')
        self.assertEqual(self.texto("#folhas .ia-fixo"), "Fixo Nuvem Sol · nov/26")
        self.clicar('#folhas [data-a="ia-salvar"]')
        self.pg.wait_for_function("() => !window.GERENCIA_TESTE.FOLHA")
        self.esperar()
        lc = [l for l in self.dados()["lancamentos"] if l.get("recorrencia") == "r-nuvem"]
        self.assertEqual([(l["id"], l["valor"], l["conta"]) for l in lc], [("l-nv", 31.9, "k-verde")], "o mês já lançado muda o valor, na conta do fixo")

    def test_na_conferencia_uma_despesa_vira_fixo(self):
        # (pedido do dono: da conferência, criar uma despesa fixa ou ligar a linha a um fixo que já existe)
        self.js("(T.api._emails = a, T.S.emails = undefined, T.S.emailsPedido = null, clearTimeout(T.S.emailsTimer), true)", [email(1, "conferir")])
        self.abrir(base(bancos=BANCOS, recorrencias=[self.FIXO], ajustes={"email": True, "email_de": []}))
        self.js("T.carregarEmails()")
        self.esperar()
        self.clicar('[data-a="email-abrir"]')
        self.assertEqual(self.textos("#folhas .ia-fixar"), ["Fixo", "Fixo"])
        # Mercado Bom: um fixo novo, feito da linha
        self.clicar('#folhas [data-a="ia-fixo"][data-i="0"]')
        self.assertEqual(self.folha(), "Despesa fixa")
        self.assertEqual(self.textos("#folhas .ia-fixos .op-t b"), ["Novo fixo", "Nuvem Sol"])
        self.assertEqual(self.textos("#folhas .ia-fixos .op-t span")[0], "Mercado Bom · R$ 123,45 todo dia 1")
        self.clicar('#folhas [data-a="ia-fixo-usar"][data-v="novo"]')
        self.assertEqual(self.folha(), "Conferir lançamentos", "volta para a conferência")
        self.assertEqual(self.texto('#folhas [data-a="ia-fixo"][data-i="0"]'), "Novo fixo · todo dia 1")
        # Farmácia Sol: no fixo que já existe; depois, Não é fixo e de novo
        self.clicar('#folhas [data-a="ia-fixo"][data-i="1"]')
        self.clicar('#folhas [data-a="ia-fixo-usar"][data-v="r-nuvem"]')
        self.assertEqual(self.texto('#folhas [data-a="ia-fixo"][data-i="1"]'), "Fixo Nuvem Sol · nov/26")
        self.clicar('#folhas [data-a="ia-fixo"][data-i="1"]')
        self.assertEqual(self.textos("#folhas .ia-fixos .op-t b")[-1], "Não é fixo")
        self.clicar('#folhas [data-a="ia-fixo-usar"][data-v=""]')
        self.assertEqual(self.texto('#folhas [data-a="ia-fixo"][data-i="1"]'), "Fixo")
        self.clicar('#folhas [data-a="ia-fixo"][data-i="1"]')
        self.clicar('#folhas [data-a="ia-fixo-usar"][data-v="r-nuvem"]')
        self.clicar('#folhas [data-a="ia-salvar"]')
        self.pg.wait_for_function("() => !window.GERENCIA_TESTE.FOLHA")
        self.esperar()
        d = self.dados()
        novo = [r for r in d["recorrencias"] if r["descricao"] == "Mercado Bom"]
        self.assertEqual([(r["valor"], r["dia"], r["inicio"], r["categoria"], r["fim"]) for r in novo], [(123.45, 1, "2026-11", "c-mercado", None)])
        mes = sorted((l["descricao"], l["valor"], l.get("recorrencia"), l.get("competencia")) for l in d["lancamentos"] if l.get("recorrencia"))
        self.assertEqual(mes, [("Mercado Bom", 123.45, novo[0]["id"], "2026-11"), ("Nuvem Sol", 45.9, "r-nuvem", "2026-11")])
        self.assertEqual([l for l in d["lancamentos"] if not l.get("recorrencia")], [], "nada solto")

    def test_pagamento_da_fatura_fica_no_fim_desmarcado(self):
        # (pedido do dono: o Pagamento online da fatura entrava como recebimento; agora fica numa seção no fim, desmarcado)
        pag = dict(lanc("Pagamento online", 1200, "c-outros-receb", "2026-10-09", "receita"), cartao=False)
        flag = dict(lanc("Crédito recebido", 50, "c-outros-receb", "2026-10-10", "receita"), pagamento_fatura=True)
        pix = dict(lanc("Pagamento recebido de Beto", 80, "c-outros-receb", "2026-10-11", "receita"), cartao=False)
        res = {"lancamentos": [lanc("Mercado Bom", 123.45), pag, flag, lanc("Farmácia Sol", 45.9, "c-saude")], "investimentos": []}
        self.abrir_com([email(1, "conferir", resultado=res)])
        self.clicar('[data-a="email-abrir"]')
        self.assertEqual(self.texto('#folhas [data-a="recolher"][data-v="ia-fora"]'), "Pagamentos desconsiderados (2)")
        self.assertEqual(self.conta("#folhas .ia-itens"), 1, "recolhidos por padrão")
        self.clicar('#folhas [data-a="recolher"][data-v="ia-fora"]')
        secoes = self.js("[...document.querySelectorAll('#folhas .ia-itens')].map(g => [...g.querySelectorAll('.ia-item-t > b')].map(b => b.textContent))")
        self.assertEqual(secoes, [["Mercado Bom", "Farmácia Sol"], ["Pagamento online", "Crédito recebido"]])
        self.assertEqual(self.js("[...document.querySelectorAll('#folhas .ia-itens')][1].querySelectorAll('.ia-check.on').length"), 0, "desmarcados")
        self.assertEqual(self.texto('#folhas [data-a="ia-salvar"]'), "Lançar 2 · −R$ 169")
        # (era bug na 1.47.0: o aviso no Início descontava o pagamento do total da fatura)
        self.assertEqual(self.js("[T.totalEmail(T.api._emails[0]), T.resumoEmail(T.api._emails[0])]"), [169.35, "2 lançamentos"])
        self.clicar('#folhas .ia-itens:last-of-type [data-a="ia-marca"]')
        self.assertEqual(self.texto('#folhas [data-a="ia-salvar"]'), "Lançar 3 · R$ 1.031", "marcado, entra")
        # fora de uma fatura de cartão, um recebimento com "pagamento" no nome continua normal
        res2 = {"lancamentos": [dict(lanc("Aluguel", 900), cartao=False), pix], "investimentos": []}
        self.abrir_com([email(2, "conferir", resultado=res2)])
        self.clicar('[data-a="email-abrir"]')
        self.assertEqual(self.conta('#folhas [data-v="ia-fora"]'), 0)
        self.assertEqual(self.texto('#folhas [data-a="ia-salvar"]'), "Lançar 2 · −R$ 820")

    def test_pagamento_da_fatura_igual_ao_servidor(self):
        import calc
        casos = [{"tipo": "receita", "descricao": "Pagamento online", "cartao": True}, {"tipo": "receita", "descricao": "PAGTO DEBITO AUTOMATICO", "cartao": False},
                 {"tipo": "receita", "descricao": "Pagamento recebido de Beto", "cartao": False}, {"tipo": "receita", "descricao": "Débito automático da fatura", "cartao": True},
                 {"tipo": "despesa", "descricao": "Pagamento online", "cartao": True}, {"tipo": "receita", "descricao": "Estorno", "pagamento_fatura": True},
                 {"tipo": "receita", "descricao": "Salário", "cartao": True}]
        self.abrir_com([])
        for cartao in (False, True):
            with self.subTest(cartao=cartao):
                self.assertEqual(self.js("a[0].map(x => T.ehPagamentoFatura(x, a[1]))", [casos, cartao]), [calc.e_pagamento_fatura(x, cartao) for x in casos])
        linhas = [lanc("Mercado Bom", 10), lanc("Farmácia", 5), {"tipo": "receita", "descricao": "Pagamento online", "valor": 99, "cartao": False}]
        self.assertEqual(self.js("T.semPagamentosFatura(a).map(x => x.descricao)", linhas), [x["descricao"] for x in calc.sem_pagamentos_fatura(linhas)])
        self.assertEqual([x["descricao"] for x in calc.sem_pagamentos_fatura(linhas)], ["Mercado Bom", "Farmácia"])

    def test_igual_ao_servidor(self):
        import emails as E  # o tela_base põe gerencia/app no caminho
        regras = [{"de": "nuvem.com.br", "acao": "fixo", "fixo": "r1"}, {"de": "fatura@nuvem.com.br", "acao": "nunca"}, {"de": "lua.com", "acao": "nunca"}]
        casos = ["fatura@nuvem.com.br", "outro@nuvem.com.br", "x@mail.nuvem.com.br", "x@nuvem.com.br.falso", "x@lua.com", "x@sol.com", ""]
        self.abrir_rem([])
        self.assertEqual(self.js("a[0].map(e => T.regraEmail(e, a[1]))", [casos, regras]), [E.regra(c, regras) for c in casos])


class TestAvisoNoCelular(TelaEmail):
    OP = {"tab": "mais", "maisTela": "config", "maisAba": "opcoes"}

    def test_opcao_so_com_a_leitura_do_email_ligada(self):
        self.abrir_com([], ui=self.OP, email=False)
        self.assertEqual(self.conta("#op-email"), 0)
        self.abrir_com([], ui=self.OP)
        self.assertEqual(self.texto("#op-email h2"), "Faturas por e-mail")
        self.assertIn("Desligado.", self.texto("#op-email"))
        self.assertEqual(self.conta("#op-email .quem-p"), 0)

    def test_ligar_comeca_com_quem_esta_usando_e_escolher_outras(self):
        self.abrir_com([], ui=self.OP)
        self.js("(T.S.avisoPessoas = undefined, T.S.avisoPedido = null, true)")
        self.clicar('#op-email [data-a="ajuste"][data-k="email_aviso"]')
        self.pg.wait_for_function("() => (window.GERENCIA_TESTE.S.d.ajustes.email_para || []).length === 1")
        self.esperar()
        self.assertEqual(self.dados()["ajustes"]["email_para"], ["person.ana"], "começa com quem está usando o app")
        self.assertEqual(self.dados()["ajustes"].get("dicas_para") or [], [], "as dicas ficam como estavam")
        self.assertEqual(self.conta("#op-email .op-testar"), 0, "o Testar fica só nas dicas")
        self.clicar('#op-email [data-a="aviso-pessoa"][data-v="person.beto"]')
        self.assertEqual(self.dados()["ajustes"]["email_para"], ["person.ana", "person.beto"])
        self.assertIn("Sem celular para Beto", self.texto("#op-email"))


if __name__ == "__main__":
    unittest.main()
