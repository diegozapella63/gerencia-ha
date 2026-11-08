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

    def test_abre_o_pdf_com_o_campo_da_senha(self):
        self.abrir_com([email(2, "senha", "Banco Verde", erro="Nenhuma das senhas cadastradas abre este PDF.")])
        self.trocar_api("emailPdf", "async id => ({ b64: '" + self.PDF + "', nome: 'fatura-2.pdf' })")
        self.clicar('[data-a="email-abrir"]')
        self.pg.wait_for_selector("#ia-senha")
        self.assertEqual(self.folha(), "Fatura, print ou foto", "só o arquivo, sem as outras opções")
        self.assertEqual(self.texto("#folhas .ia-prev b"), "fatura-2.pdf")
        self.assertEqual(self.texto("#folhas .msg-erro"), "Nenhuma das senhas cadastradas abre este PDF.")
        self.pg.wait_for_function("document.activeElement && document.activeElement.id === 'ia-senha'")

    def test_com_a_senha_le_e_ao_lancar_marca_a_fatura(self):
        self.abrir_com([email(2, "senha", "Banco Verde")])
        self.trocar_api("emailPdf", "async id => ({ b64: '" + self.PDF + "', nome: 'fatura-2.pdf' })")
        self.js("(window.__ped = [], true)")
        self.trocar_api("iaLer", "async c => { window.__ped.push(c); return { lancamentos: [{ tipo: 'despesa', descricao: 'Posto Bom', valor: 80, data: '2026-11-01', categoria: 'c-transporte', cartao: true }], investimentos: [] }; }")
        self.clicar('[data-a="email-abrir"]')
        self.pg.wait_for_selector("#ia-senha")
        self.preencher("#ia-senha", "12345")
        self.clicar('#folhas [data-a="ia-ler"]')
        self.pg.wait_for_function("() => window.GERENCIA_TESTE.IAS && window.GERENCIA_TESTE.IAS.etapa === 'revisao'")
        p = self.js("window.__ped[0]")
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
        self.assertIn("Sem nenhum, os e-mails com PDF e “fatura” no assunto.", self.cartao())

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
                                  ["Loja", "Seu boleto · 01/11", "Ler"], ["Banco Azul", "Fatura 4 · 01/11", "Lançada"], ["Banco Azul", "Fatura 5 · 01/11", "Ler"]],
                         "os 5 últimos; o que não parecia fatura e o ignorado dá para ler")
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
                         ["outros-apps", "bens", "ia", "senhas-pdf", "email", "correria", "uso-ia", "sensores"])


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
