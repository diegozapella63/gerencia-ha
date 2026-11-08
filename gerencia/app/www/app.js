/* GerencIA · controle de investimentos dentro do Home Assistant */
(() => {
'use strict';

const DEMO = !!window.GERENCIA_DEMO;
const VERSAO = '1.36.0';

const PALETA = ['#FF5A4E', '#FF8A65', '#FF77A8', '#E04B8A', '#FFA23A', '#F2C14E', '#B79BFF', '#56AEFF', '#4CD3A5', '#B8B0B0'];
// ordem para sugerir cor a um banco novo
const CORES_BANCO = ['#56AEFF', '#B79BFF', '#4CD3A5', '#FFA23A', '#FF77A8', '#F2C14E', '#FF8A65', '#E04B8A', '#FF5A4E', '#B8B0B0'];
// cores do app com nome, em forma de etiqueta (as mesmas do CronologIA e do ResolvIA; o azul é o do GerencIA)
const CORES_APP = [
  ['Vermelho', '#FF5A4F'], ['Coral', '#FF8A65'], ['Laranja', '#FFA23E'], ['Ouro', '#F2C14E'], ['Verde', '#8BD45F'], ['Menta', '#4ED3A6'],
  ['Turquesa', '#3CCBDA'], ['Azul', '#56AEFF'], ['Índigo', '#8F9BFF'], ['Lilás', '#B99BFF'], ['Rosa', '#FF77A9'], ['Grafite', '#B5B9C2'],
];
const rgbHex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
// Cor do dia (Mais › Configurações › Aparência, ligada por padrão): as cores do app em ordem, uma por dia, sem as neutras (Grafite).
// O dia é a data daqui contada desde 01/01/1970: a mesma cor o dia todo, em todo aparelho (igual ao calc.cor_do_dia).
const neutra = h => { const c = rgbHex(h); return Math.max(...c) - Math.min(...c) < 40; };
const CORES_DIA = CORES_APP.filter(([, h]) => !neutra(h));
const numeroDoDia = (d = new Date()) => Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 86400000);
const corDoDia = (d = new Date()) => CORES_DIA[((numeroDoDia(d) % CORES_DIA.length) + CORES_DIA.length) % CORES_DIA.length][1];
const BANCOS_COMUNS = ['Nubank', 'Itaú', 'Bradesco', 'Banco do Brasil', 'Caixa', 'Santander', 'Inter', 'BTG Pactual',
  'XP', 'C6 Bank', 'Sicredi', 'Sicoob', 'Mercado Pago', 'PicPay', 'Rico', 'Banrisul', 'Safra', 'Viacredi'];

const TIPOS = [
  { id: 'cdb', nome: 'CDB', ir: 'reg', p: { indexador: 'cdi_pct', taxa: 100, liquidez: 'vencimento' } },
  { id: 'lci', nome: 'LCI/LCA', ir: 'isento', p: { indexador: 'cdi_pct', taxa: 90, liquidez: 'vencimento' } },
  { id: 'tesouro', nome: 'Tesouro', ir: 'reg', p: { indexador: 'selic_mais', taxa: 0, liquidez: 'diaria' } },
  { id: 'poupanca', nome: 'Poupança', ir: 'isento', p: { indexador: 'poupanca', taxa: 0, liquidez: 'diaria' } },
  { id: 'caixinha', nome: 'Caixinha', ir: 'reg', p: { indexador: 'cdi_pct', taxa: 100, liquidez: 'diaria' } },
  { id: 'fundo', nome: 'Fundo', ir: 'reg', p: { indexador: 'cdi_pct', taxa: 100, liquidez: 'diaria' } },
  { id: 'acoes', nome: 'Ações/FII', ir: '15', p: { indexador: 'estimado', taxa: 10, liquidez: 'diaria' } },
  { id: 'ouro', nome: 'Ouro', ir: '15', p: { indexador: 'estimado', taxa: 10, liquidez: 'diaria' } },
  { id: 'dinheiro', nome: 'Dinheiro', ir: 'isento', p: { indexador: 'parado', taxa: 0, liquidez: 'diaria' } },
  { id: 'bens', nome: 'Bens', ir: 'isento', p: { indexador: 'deprecia', taxa: 10, liquidez: 'diaria' } },
  { id: 'previdencia', nome: 'Previdência', ir: 'nao', p: { indexador: 'cdi_pct', taxa: 95, liquidez: 'vencimento' } },
  { id: 'outro', nome: 'Outro', ir: 'reg', p: { indexador: 'pre', taxa: 12, liquidez: 'vencimento' } },
];

const IDX = [
  { id: 'cdi_pct', nome: '% do CDI', suf: '% do CDI', ph: '100', taxa: true },
  { id: 'cdi_mais', nome: 'CDI +', pre: 'CDI +', suf: '% a.a.', ph: '1,5', taxa: true },
  { id: 'pre', nome: 'Prefixado', suf: '% a.a.', ph: '13,5', taxa: true },
  { id: 'ipca_mais', nome: 'IPCA +', pre: 'IPCA +', suf: '% a.a.', ph: '7', taxa: true },
  { id: 'selic_mais', nome: 'Selic +', pre: 'Selic +', suf: '% a.a.', ph: '0', taxa: true, zero: true },
  { id: 'poupanca', nome: 'Poupança' },
  { id: 'estimado', nome: 'Estimado', suf: '% a.a.', ph: '10', taxa: true },
  { id: 'parado', nome: 'Sem rendimento' },
  { id: 'deprecia', nome: 'Perde valor', oculto: true },
];
// perda de valor por ano dos bens, por categoria (as mesmas do InventarIA, e Veículos); muda em Mais › Invest
const BENS_CATS = [['imoveis', 'Imóveis', 0], ['veiculos', 'Veículos', 15], ['eletronicos', 'Eletrônicos', 20], ['moveis', 'Móveis', 10], ['decoracao', 'Decoração e arte', 5],
  ['colecao', 'Colecionáveis', 0], ['cozinha', 'Cozinha e bar', 10], ['texteis', 'Tapetes e têxteis', 15], ['plantas', 'Plantas', 0], ['livros', 'Livros e jogos', 5],
  ['pets', 'Pets', 15], ['saude', 'Saúde', 10], ['vestuario', 'Roupas e calçados', 25], ['utilidades', 'Utilidades', 10], ['outros', 'Outros', 10]];
// As categorias dos bens são as do InventarIA (lá dá para renomear, criar e excluir), mais Imóveis e Veículos;
// sem o InventarIA, as de costume. Categoria nova começa perdendo 10% ao ano.
function catsBens() {
  const inv = S.bens && S.bens.ok && S.bens.todas && S.bens.todas.length ? S.bens.todas.map(c => [c.id, c.nome, c.taxa]) : null;
  if (!inv) return BENS_CATS;
  const extra = BENS_CATS.filter(([k]) => (k === 'imoveis' || k === 'veiculos') && !inv.some(c => c[0] === k));
  return [...extra, ...inv];
}
const nomeCatBem = k => (catsBens().find(c => c[0] === k) || BENS_CATS.find(c => c[0] === k) || [k, (S.bens && S.bens.categorias || []).find(c => c.id === k)?.nome || 'Outros'])[1];
function taxaBem(k) {
  const v = (S.d.ajustes.bens_taxas || {})[k];
  return v != null && v !== '' && !isNaN(+v) ? +v : ((BENS_CATS.find(c => c[0] === k) || [])[2] ?? 10);
}

const INDICES_PADRAO = { cdi: 13.65, selic: 13.75, ipca: 4.58, tr: 0.17, auto: true, fonte: 'padrao', atualizado_em: null, datas: {}, erro: null };
const AJUSTES_PADRAO = { tema: 'auto', cor: '#56AEFF', cor_dia: true, corrigir: true, sensores: false, sensores_v: 2, ia_entidade: '', voz_motor: '', bens: true, bens_taxas: {}, dicas_fora: [], integracao: true, ia: true, dicas: true, prever_dia: true };

/* ------------------------------------------------------------------ util */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const uid = () => Math.random().toString(36).slice(2, 9) + Date.now().toString(36).slice(-4);
const clone = o => JSON.parse(JSON.stringify(o));
const corOk = c => (/^#[0-9a-f]{6}$/i.test(c || '') ? c : null);
const store = {
  get(k, d) { try { const v = localStorage.getItem('gerencia.' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('gerencia.' + k, JSON.stringify(v)); } catch (e) { /* sem armazenamento */ } },
};

const hoje = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; };
const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const pData = s => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || ''); return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null; };
const diasEntre = (a, b) => Math.round((b - a) / 86400000);
const addMeses = (d, m) => { const x = new Date(d); x.setMonth(x.getMonth() + m); return x; };
const fData = d => d ? d.toLocaleDateString('pt-BR') : '';
const fDataC = d => d ? `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}` : '';
const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const fMesAno = d => `${MESES[d.getMonth()]}/${String(d.getFullYear()).slice(2)}`;

function diasUteis(d0, d1) {
  if (!d0 || !d1 || d1 <= d0) return 0;
  const total = diasEntre(d0, d1);
  let n = Math.floor(total / 7) * 5;
  const wd = (d0.getDay() + 6) % 7; // segunda = 0
  for (let i = 1; i <= total % 7; i++) if ((wd + i) % 7 < 5) n++;
  return n;
}

const NF2 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const NF0 = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });
const NFP = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 });
const NFC = new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 });
const OC = '•••••';
const brl = (v, c = 2) => S.oculto ? `R$ ${OC}` : 'R$ ' + (c ? NF2 : NF0).format(v);
const numf = (v, c = 2) => S.oculto ? OC : (c ? NF2 : NF0).format(v);
const pct = v => NFP.format(v);
// fatias (categorias, divisão da carteira): sempre uma casa, para os números ficarem do mesmo tamanho
const NF1 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const pct1 = v => NF1.format(v);
const brlS = (v, c = 2) => (v < -0.005 ? '−' : '') + brl(Math.abs(v), c);
const compacto = v => S.oculto ? '•••' : NFC.format(v);
const parseNum = t => { const s = String(t ?? '').trim().replace(/\s/g, ''); if (!s) return NaN; return parseFloat(s.includes(',') ? s.replace(/\./g, '').replace(',', '.') : s); };
const plural = (n, s, p) => `${n} ${n === 1 ? s : p}`;

/* ------------------------------------------------------------------ ícones */
const P = {
  'mic': '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/>',
  'smartphone': '<rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><path d="M12 18h.01"/>',
  'contrast': '<circle cx="12" cy="12" r="10"/><path d="M12 18a6 6 0 0 0 0-12v12z"/>',
  'palette': '<path d="M12 22a1 1 0 0 1 0-20 10 9 0 0 1 10 9 5 5 0 0 1-5 5h-2.25a1.75 1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z"/><circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/>',
  'blocks': '<path d="M10 22V7a1 1 0 0 0-1-1H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5a1 1 0 0 0-1-1H2"/><rect x="14" y="2" width="8" height="8" rx="1"/>',
  'toggle-right': '<circle cx="15" cy="12" r="3"/><rect width="20" height="14" x="2" y="5" rx="7"/>',
  'archive-restore': '<rect width="20" height="5" x="2" y="3" rx="1"/><path d="M4 8v11a2 2 0 0 0 2 2h2"/><path d="M20 8v11a2 2 0 0 1-2 2h-2"/><path d="m9 15 3-3 3 3"/><path d="M12 12v9"/>',
  'sheet': '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><line x1="3" x2="21" y1="9" y2="9"/><line x1="3" x2="21" y1="15" y2="15"/><line x1="9" x2="9" y1="9" y2="21"/><line x1="15" x2="15" y1="9" y2="21"/>',
  'braces': '<path d="M8 3H7a2 2 0 0 0-2 2v5a2 2 0 0 1-2 2 2 2 0 0 1 2 2v5c0 1.1.9 2 2 2h1"/><path d="M16 21h1a2 2 0 0 0 2-2v-5c0-1.1.9-2 2-2a2 2 0 0 1-2-2V5a2 2 0 0 0-2-2h-1"/>',
  'database': '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/>',
  'clipboard-paste': '<path d="M15 2H9a1 1 0 0 0-1 1v2c0 .6.4 1 1 1h6c.6 0 1-.4 1-1V3c0-.6-.4-1-1-1Z"/><path d="M8 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2"/><path d="M16 4h2a2 2 0 0 1 2 2v2"/><path d="M11 14h10"/><path d="m17 10 4 4-4 4"/>',
  'chart-column': '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
  'layers': '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z"/><path d="M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12"/><path d="M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17"/>',
  'receipt': '<path d="M12 17V7"/><path d="M16 8h-6a2 2 0 0 0 0 4h4a2 2 0 0 1 0 4H8"/><path d="M4 3a1 1 0 0 1 1-1 1.3 1.3 0 0 1 .7.2l.933.6a1.3 1.3 0 0 0 1.4 0l.934-.6a1.3 1.3 0 0 1 1.4 0l.933.6a1.3 1.3 0 0 0 1.4 0l.933-.6a1.3 1.3 0 0 1 1.4 0l.934.6a1.3 1.3 0 0 0 1.4 0l.933-.6A1.3 1.3 0 0 1 19 2a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1 1.3 1.3 0 0 1-.7-.2l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.934.6a1.3 1.3 0 0 1-1.4 0l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-1.4 0l-.934-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-.7.2 1 1 0 0 1-1-1z"/>',
  home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V20h5v-6h4v6h5V9.5"/>',
  wallet: '<path d="M4 7h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a1 1 0 0 1-1-1V7Z"/><path d="M4 7V6a2 2 0 0 1 2-2h10"/><circle cx="16" cy="13.5" r="1.3" fill="currentColor" stroke="none"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  chart: '<path d="M4 19h16"/><path d="m5 15 4-5 4 3 6-7"/>',
  sliders: '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
  // Mais (três pontos, como no InventarIA)
  dots: '<circle cx="5" cy="12" r="1.5" fill="currentColor"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/><circle cx="19" cy="12" r="1.5" fill="currentColor"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
  eyeOff: '<path d="M3 3l18 18"/><path d="M10.6 5.1A10.5 10.5 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3 3.9"/><path d="M6.6 6.6C3.7 8.4 2 12 2 12s3.5 7 10 7a9.8 9.8 0 0 0 5.4-1.6"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
  chev: '<path d="m9 6 6 6-6 6"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5a6.5 6.5 0 0 1 3.5 5.5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  bank: '<path d="M3 9.5 12 4l9 5.5"/><path d="M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 20h18"/>',
  refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>',
  download: '<path d="M12 4v11m-5-5 5 5 5-5"/><path d="M5 20h14"/>',
  upload: '<path d="M12 16V5m-5 5 5-5 5 5"/><path d="M5 20h14"/>',
  file: '<path d="M14 3H6v18h12V7l-4-4Z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
  archive: '<rect x="3" y="4" width="18" height="5" rx="1.5"/><path d="M5 9v10h14V9M10 13h4"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z"/>',
  auto: '<circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 1 0 16Z" fill="currentColor" stroke="none"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  swap: '<path d="M4 8h15l-4-4M20 16H5l4 4"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3.5 7 8.5 6 8.5-6"/>',
  sofa: '<path d="M5 10V7a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v3"/><path d="M3 18v-6a2 2 0 0 1 4 0v2h10v-2a2 2 0 0 1 4 0v6z"/><path d="M5 18v2M19 18v2"/>',
  alert: '<path d="M12 4 2.5 20h19L12 4Z"/><path d="M12 10v4M12 17h.01"/>',
  trend: '<path d="m3 17 6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
  calendar: '<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
  percent: '<path d="M19 5 5 19"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
  edit: '<path d="M4 20h4L19 9l-4-4L4 16v4Z"/>',
  fluxo: '<path d="M7 20V5M3 9l4-4 4 4"/><path d="M17 4v15M13 15l4 4 4-4"/>',
  card: '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M3 10h18M7 15h4"/>',
  camera: '<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
  scan: '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 8h8"/><path d="M7 12h10"/><path d="M7 16h6"/>',
  image: '<rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
  zap: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
  ia: '<path d="M12 3l1.8 4.7 4.7 1.8-4.7 1.8L12 16l-1.8-4.7-4.7-1.8 4.7-1.8z"/><path d="M19 15l.8 2.2 2.2.8-2.2.8L19 21l-.8-2.2-2.2-.8 2.2-.8z"/>',
  repeat: '<path d="M17 2l3 3-3 3"/><path d="M4 11V9a4 4 0 0 1 4-4h12"/><path d="M7 22l-3-3 3-3"/><path d="M20 13v2a4 4 0 0 1-4 4H4"/>',
  minus: '<path d="M5 12h14"/>',
  chevL: '<path d="m15 6-6 6 6 6"/>',
  chat: '<path d="M21 12a8 8 0 0 1-11.7 7.1L4 20.5l1.4-4.9A8 8 0 1 1 21 12Z"/><path d="M8.5 12h.01M12 12h.01M15.5 12h.01"/>',
  send: '<path d="M5 12h13M13 6l6 6-6 6"/>',
  // Mais › Sobre (Lucide, como no CronologIA)
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
  hourglass: '<path d="M5 22h14"/><path d="M5 2h14"/><path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22"/><path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>',
  'calendar-days': '<path d="M8 2v3"/><path d="M16 2v3"/><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M8 13h.01"/><path d="M12 13h.01"/><path d="M16 13h.01"/><path d="M8 17h.01"/><path d="M12 17h.01"/><path d="M16 17h.01"/>',
  'list-checks': '<path d="M13 5h8"/><path d="M13 12h8"/><path d="M13 19h8"/><path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/>',
  package: '<path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z"/><path d="M12 22V12"/><path d="M3.29 7 12 12l8.71-5"/><path d="m7.5 4.27 9 5.15"/>',
  'book-open': '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
  'external-link': '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
};
const ic = (n, c = 'ic') => `<svg class="${c}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[n] || ''}</svg>`;

/* ------------------------------------------------------------------ estado */
// Até a 1.25, Mais era em abas (maisAba). Agora Mais é um menu: Bancos, Caixa e Invest viraram telas (maisTela) e as
// outras abas ficaram em Configurações. Quem abre o app atualizado volta no mesmo lugar, já no caminho novo.
function uiGuardada() {
  const u = store.get('ui', {});
  if (u && typeof u === 'object' && u.maisTela === undefined && u.maisAba) {
    const tela = ['bancos', 'caixa', 'invest'].includes(u.maisAba) ? u.maisAba : 'config';
    u.maisTela = u.tab === 'mais' ? tela : '';
    if (tela !== 'config') u.maisAba = 'integracoes';
  }
  return u;
}
const S = {
  d: null,
  usuario: null,
  oculto: store.get('oculto', false),
  ui: Object.assign({
    tab: 'inicio', filtro: 'todos', pessoa: null, banco: null, busca: '', buscaAberta: false,
    invModo: 'carteira', gEscopo: 'tudo', gAnos: 5, gIR: false, gSemBens: false, gAgrup: 'banco', gSel: null,
    cxModo: 'lista', cxMes: null, cxFiltro: 'tudo', cxPeriodo: 'meio', cxAtras: 24, cxFrente: 0, cxCatTipo: 'despesa', cxSel: null, faturaAberta: null,
    maisTela: '', maisAba: 'integracoes',
  }, uiGuardada(), { gIR: false, gSemBens: false }), // Descontar IR e Ocultar bens começam desligados toda vez
  ia: null,
  dicas: null,
  bens: null,
};
const salvarUI = () => {
  const { tab, filtro, invModo, gEscopo, gAnos, gAgrup, cxModo, cxFiltro, cxPeriodo, cxAtras, cxFrente, cxCatTipo, maisTela, maisAba } = S.ui;
  store.set('ui', { tab, filtro, invModo, gEscopo, gAnos, gAgrup, cxModo, cxFiltro, cxPeriodo, cxAtras, cxFrente, cxCatTipo, maisTela, maisAba });
};

function normalizar(d) {
  d = d || {};
  const lista = v => Array.isArray(v) ? v : [];
  return {
    schema: 1, rev: d.rev || 0, exemplo: !!d.exemplo,
    bancos: lista(d.bancos).map(b => Object.assign({}, b, {
      contas: Array.isArray(b.contas) && b.contas.length ? b.contas : [{ id: b.id + '-c1', pessoa: '', cartao: false, fechamento: 1, vencimento: 10 }],
    })),
    lancamentos: lista(d.lancamentos),
    recorrencias: lista(d.recorrencias),
    categorias: Array.isArray(d.categorias) ? d.categorias : clone(CATEGORIAS_PADRAO),
    investimentos: Array.isArray(d.investimentos) ? d.investimentos : [],
    indices: Object.assign({}, INDICES_PADRAO, d.indices || {}),
    ajustes: Object.assign({}, AJUSTES_PADRAO, d.ajustes || {}),
    historico: Array.isArray(d.historico) ? d.historico : [],
  };
}

/* ------------------------------------------------------------------ cálculos */
function taxaAnual(inv, I = S.d.indices) {
  const t = (+inv.taxa || 0) / 100, cdi = I.cdi / 100, selic = I.selic / 100, ipca = I.ipca / 100, tr = (I.tr || 0) / 100;
  switch (inv.indexador) {
    case 'cdi_pct': return cdi * t;
    case 'cdi_mais': return (1 + cdi) * (1 + t) - 1;
    case 'pre': return t;
    case 'ipca_mais': return (1 + ipca) * (1 + t) - 1;
    case 'selic_mais': return (1 + selic) * (1 + t) - 1;
    case 'poupanca': {
      const m = selic > 0.085 ? 0.005 : Math.pow(1 + 0.7 * selic, 1 / 12) - 1;
      return Math.pow((1 + m) * (1 + tr), 12) - 1;
    }
    case 'estimado': return t;
    case 'deprecia': return -t;
    default: return 0;
  }
}
const corrige = inv => !['estimado', 'parado'].includes(inv.indexador);
function valorHoje(inv, h = hoje(), d = S.d) {
  const v = +inv.valor || 0;
  if (d.ajustes.corrigir === false || !corrige(inv)) return v;
  const d0 = pData(inv.data_valor) || h;
  // bem separado por categoria: cada parte perde a taxa da sua categoria
  if (inv.indexador === 'deprecia' && inv.partes && inv.partes.length) return partesHoje(inv, h).reduce((a, p) => a + p.v, 0);
  return v * Math.pow(1 + taxaAnual(inv, d.indices), diasUteis(d0, h) / 252);
}
function partesHoje(inv, h = hoje()) {
  const anos = S.d.ajustes.corrigir === false ? 0 : diasUteis(pData(inv.data_valor) || h, h) / 252;
  return (inv.partes || []).map(p => ({ categoria: p.categoria, v: (+p.valor || 0) * Math.pow(1 - (+p.taxa || 0) / 100, anos), r: -(+p.taxa || 0) / 100 }));
}
// a taxa de um bem separado: a média das partes, pesada pelo valor
const taxaPartes = partes => { const t = partes.reduce((a, p) => a + (+p.valor || 0), 0); return t ? round2(partes.reduce((a, p) => a + (+p.valor || 0) * (+p.taxa || 0), 0) / t) : 0; };
// quanto rende por mês; bens que perdem valor não entram (0) — a perda aparece à parte
const rendeMes = (v, r) => Math.max(0, v * (Math.pow(1 + r, 1 / 12) - 1));
const perdeMes = (v, r) => Math.max(0, -v * (Math.pow(1 + r, 1 / 12) - 1));
// bem separado em partes: cada parte perde na sua taxa (a média pesada daria outro número que o da Evolução)
const perdeMesInv = (i, v) => i.tipo === 'bens' && (i.partes || []).length ? partesHoje(i).reduce((a, p) => a + perdeMes(p.v, p.r), 0) : perdeMes(v, taxaAnual(i));
const tipoDe = id => TIPOS.find(t => t.id === id) || TIPOS[TIPOS.length - 1];
const idxDe = id => IDX.find(x => x.id === id) || IDX[0];
const bancoDe = id => S.d.bancos.find(b => b.id === id);
const dono = inv => inv.titular === 'terceiros' ? ((inv.terceiro || '').trim() || 'Terceiros') : 'Meu';
const pessoas = () => [...new Set(S.d.investimentos.filter(i => i.titular === 'terceiros').map(dono))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
function aliquota(ir, dias) {
  if (ir === 'reg') return dias <= 180 ? 0.225 : dias <= 360 ? 0.2 : dias <= 720 ? 0.175 : 0.15;
  if (ir === '15') return 0.15;
  return 0;
}

function rotuloTaxa(inv) {
  const t = pct(+inv.taxa || 0);
  switch (inv.indexador) {
    case 'cdi_pct': return `${t}% do CDI`;
    case 'cdi_mais': return `CDI + ${t}% a.a.`;
    case 'pre': return `${t}% a.a. pré`;
    case 'ipca_mais': return `IPCA + ${t}% a.a.`;
    case 'selic_mais': return +inv.taxa ? `Selic + ${t}% a.a.` : 'Selic';
    case 'poupanca': return 'Poupança';
    case 'estimado': return `≈ ${t}% a.a. estimado`;
    case 'deprecia': return +inv.taxa > 0 ? `perde ${t}% a.a.` : +inv.taxa < 0 ? `valoriza ${pct(-inv.taxa)}% a.a.` : 'mantém o valor';
    default: return 'Sem rendimento';
  }
}

function totais(lista = S.d.investimentos, d = S.d) {
  const h = hoje();
  let total = 0, meu = 0, terc = 0, mes = 0, wr = 0;
  for (const i of lista) {
    const v = valorHoje(i, h, d), r = taxaAnual(i, d.indices);
    total += v; mes += rendeMes(v, r); wr += v * r;
    if (i.titular === 'terceiros') terc += v; else meu += v;
  }
  return { total, meu, terc, mes, rMed: total ? wr / total : 0 };
}

function porEscopo(esc) {
  const l = S.d.investimentos;
  if (esc === 'meu') return l.filter(i => i.titular !== 'terceiros');
  if (esc === 'terc') return l.filter(i => i.titular === 'terceiros');
  return l;
}

function projetar(lista, anos, aporte, comIR) {
  const h = hoje(), I = S.d.indices, meses = anos * 12;
  const base = lista.flatMap(i => i.indexador === 'deprecia' && i.partes && i.partes.length
    ? partesHoje(i, h).map(p => ({ v: p.v, r: p.r, ir: 'isento', idade: 0 }))
    : [{ v: valorHoje(i, h), r: taxaAnual(i), ir: tipoDe(i.tipo).ir, idade: Math.max(0, diasEntre(pData(i.data_valor) || h, h)) }]);
  const V0 = base.reduce((s, b) => s + b.v, 0);
  const rMed = V0 > 0 ? base.reduce((s, b) => s + b.v * b.r, 0) / V0 : I.cdi / 100;
  const fMed = Math.pow(1 + rMed, 1 / 12);
  const ipcaM = Math.pow(1 + I.ipca / 100, 1 / 12);
  const pts = [];
  for (let m = 0; m <= meses; m++) {
    let bruto = 0, imposto = 0;
    for (const b of base) {
      const vm = b.v * Math.pow(1 + b.r, m / 12);
      bruto += vm;
      if (comIR) imposto += Math.max(0, vm - b.v) * aliquota(b.ir, b.idade + m * 30.44);
    }
    if (aporte > 0) {
      const ap = Math.abs(fMed - 1) < 1e-12 ? aporte * m : aporte * (Math.pow(fMed, m) - 1) / (fMed - 1);
      bruto += ap;
      if (comIR) imposto += Math.max(0, ap - aporte * m) * aliquota('reg', m * 30.44 / 2);
    }
    const valor = bruto - imposto;
    pts.push({ t: addMeses(h, m).getTime(), m, valor, aplicado: V0 + aporte * m, real: valor / Math.pow(ipcaM, m) });
  }
  return { pts, V0, rMed };
}

function registrarHistorico(d) {
  const h = hoje(), t = totais(d.investimentos, d);
  const p = { d: iso(h), total: +t.total.toFixed(2), meu: +t.meu.toFixed(2), terceiros: +t.terc.toFixed(2) };
  d.historico = (d.historico || []).filter(x => x.d !== p.d);
  if (d.investimentos.length || d.historico.length) d.historico.push(p);
  d.historico.sort((a, b) => a.d < b.d ? -1 : 1);
}

/* ------------------------------------------------------------------ exemplo */
function gerarExemplo() {
  const h = hoje();
  const dia = n => iso(new Date(h.getTime() - n * 86400000));
  const futuro = (m, dd = 15) => { const x = addMeses(h, m); x.setDate(dd); return iso(x); };
  const b = (id, nome, cor) => ({ id, nome, cor, obs: '' });
  const bancos = [
    b('b-lua', 'Banco Lua', '#B79BFF'), b('b-sol', 'Banco Sol', '#FFA23A'), b('b-coral', 'Banco Coral', '#FF8A65'),
    b('b-norte', 'Corretora Norte', '#B8B0B0'), b('b-azul', 'Banco Azul', '#56AEFF'), b('b-verde', 'Banco Verde', '#4CD3A5'),
  ];
  const inv = (o) => Object.assign({ id: uid(), obs: '', vencimento: null, terceiro: '', titular: 'meu', criado_em: dia(200) }, o);
  const investimentos = [
    inv({ nome: 'Reserva de emergência', banco: 'b-lua', tipo: 'caixinha', valor: 24380.52, data_valor: dia(17), indexador: 'cdi_pct', taxa: 100, liquidez: 'diaria' }),
    inv({ nome: 'CDB Sol 2028', banco: 'b-sol', tipo: 'cdb', valor: 15000, data_valor: dia(46), indexador: 'cdi_pct', taxa: 112, liquidez: 'vencimento', vencimento: futuro(17, 13) }),
    inv({ nome: 'LCI Coral', banco: 'b-coral', tipo: 'lci', valor: 20000, data_valor: dia(95), indexador: 'cdi_pct', taxa: 94, liquidez: 'vencimento', vencimento: iso(new Date(h.getTime() + 24 * 86400000)) }),
    inv({ nome: 'Tesouro IPCA+ 2035', banco: 'b-norte', tipo: 'tesouro', valor: 18640.1, data_valor: dia(30), indexador: 'ipca_mais', taxa: 7.1, liquidez: 'vencimento', vencimento: '2035-05-15' }),
    inv({ nome: 'Tesouro Selic 2029', banco: 'b-norte', tipo: 'tesouro', valor: 8200, data_valor: dia(30), indexador: 'selic_mais', taxa: 0.05, liquidez: 'diaria', vencimento: '2029-03-01' }),
    inv({ nome: 'Ações e FIIs', banco: 'b-norte', tipo: 'acoes', valor: 12450, data_valor: dia(9), indexador: 'estimado', taxa: 10, liquidez: 'diaria' }),
    inv({ nome: 'Poupança da mãe', banco: 'b-azul', tipo: 'poupanca', valor: 9870.35, data_valor: dia(18), indexador: 'poupanca', taxa: 0, liquidez: 'diaria', titular: 'terceiros', terceiro: 'Mãe' }),
    inv({ nome: 'CDB do Pedro', banco: 'b-verde', tipo: 'cdb', valor: 5300, data_valor: dia(73), indexador: 'cdi_pct', taxa: 105, liquidez: 'vencimento', vencimento: futuro(26, 2), titular: 'terceiros', terceiro: 'Pedro' }),
    inv({ nome: 'Vaquinha da viagem', banco: 'b-lua', tipo: 'caixinha', valor: 2150, data_valor: dia(5), indexador: 'cdi_pct', taxa: 100, liquidez: 'diaria', titular: 'terceiros', terceiro: 'Família' }),
  ];
  contasExemplo(bancos);
  const d = normalizar({ exemplo: true, bancos, investimentos });
  Object.assign(d, caixaExemplo());
  marcarFaturasPagas(d);
  const t = totais(investimentos, d);
  const historico = [];
  for (let k = 9; k >= 1; k--) {
    const fator = Math.pow(1.0108, -k);
    const meu = Math.max(0, (t.meu - 1400 * k) * fator);
    const terc = Math.max(0, (t.terc - 260 * k) * fator);
    historico.push({ d: iso(addMeses(h, -k)), total: +(meu + terc).toFixed(2), meu: +meu.toFixed(2), terceiros: +terc.toFixed(2) });
  }
  d.historico = historico;
  registrarHistorico(d);
  return d;
}

/* ------------------------------------------------------------------ API */
async function jsonOk(r) {
  if (r.ok) return r.json();
  let msg = `Erro ${r.status}`, codigo = '';
  try { const j = await r.json(); msg = j.erro || msg; codigo = j.codigo || ''; } catch (e) { /* sem corpo */ }
  throw Object.assign(new Error(msg), { codigo });
}
const apiServidor = {
  state: () => fetch('api/state', { cache: 'no-store' }).then(jsonOk),
  async save(corpo) {
    const r = await fetch('api/state', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo) });
    if (r.status === 409) { const e = new Error('conflito'); e.conflito = true; e.d = await r.json(); throw e; }
    return jsonOk(r);
  },
  indices: v => fetch('api/indices', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(v) }).then(jsonOk),
  atualizarIndices: () => fetch('api/indices/atualizar', { method: 'POST' }).then(jsonOk),
  backup: () => fetch('api/backup', { method: 'POST' }).then(jsonOk),
  importar: f => fetch('api/importar', { method: 'POST', headers: { 'X-Nome-Arquivo': encodeURIComponent(f.name) }, body: f }).then(jsonOk),
  versoes: () => fetch('api/versoes', { cache: 'no-store' }).then(jsonOk),
  restaurar: nome => fetch('api/versoes/restaurar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nome }) }).then(jsonOk),
  foto: jpg => fetch('api/fotos', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ jpg }) }).then(jsonOk),
  iaStatus: () => fetch('api/ia/status', { cache: 'no-store' }).then(jsonOk),
  iaLer: corpo => fetch('api/ia/ler', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo) }).then(jsonOk).finally(() => { S.usoEm = 0; }),
  dicas: () => fetch('api/dicas', { cache: 'no-store' }).then(jsonOk),
  bens: () => fetch('api/bens', { cache: 'no-store' }).then(jsonOk),
  bensAtualizar: () => fetch('api/bens/atualizar', { method: 'POST' }).then(jsonOk),
  iaUso: () => fetch('api/ia/uso', { cache: 'no-store' }).then(jsonOk),
  vozStatus: () => fetch('api/voz/status', { cache: 'no-store' }).then(jsonOk),
  vozTexto: pcm => fetch('api/voz', { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: pcm }).then(jsonOk),
  backups: () => fetch('api/backups', { cache: 'no-store' }).then(jsonOk),
  restaurarBackup: nome => fetch('api/backups/restaurar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nome }) }).then(jsonOk),
  dicasConferir: () => fetch('api/dicas/conferir', { method: 'POST' }).then(jsonOk),
  avisoPessoas: () => fetch('api/avisos/pessoas', { cache: 'no-store' }).then(jsonOk),
  senhas: () => fetch('api/senhas', { cache: 'no-store' }).then(jsonOk),
  senhaNova: (nome, senha) => fetch('api/senhas', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nome, senha }) }).then(jsonOk),
  senhaApagar: id => fetch('api/senhas/apagar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }) }).then(jsonOk),
  avisoTestar: () => fetch('api/avisos/testar', { method: 'POST' }).then(jsonOk),
  emails: forcar => fetch('api/emails' + (forcar ? '?forcar=1' : ''), { cache: 'no-store' }).then(jsonOk),
  emailPdf: id => fetch('api/emails/pdf?id=' + encodeURIComponent(id), { cache: 'no-store' }).then(jsonOk),
  emailAcao: (acao, id) => fetch('api/emails/' + acao, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }) }).then(jsonOk),
  chat: () => fetch('api/chat', { cache: 'no-store' }).then(jsonOk),
  chatEnviar: corpo => fetch('api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo) }).then(jsonOk).finally(() => { S.usoEm = 0; }),
  chatAcao: (id, grupo, estado) => fetch('api/chat/acao', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id, grupo, estado }) }).then(jsonOk),
  chatLimpar: () => fetch('api/chat/limpar', { method: 'POST' }).then(jsonOk),
};
function apiDemo() {
  let d = null;
  const espera = ms => new Promise(r => setTimeout(r, ms));
  return {
    async state() { d = d || gerarExemplo(); return Object.assign(clone(d), { usuario: 'Ana' }); },
    async save(c) {
      if (c.rev !== d.rev) { const e = new Error('conflito'); e.conflito = true; e.d = clone(d); throw e; }
      for (const k of ['bancos', 'investimentos', 'ajustes', 'exemplo', 'lancamentos', 'recorrencias', 'categorias']) if (k in c) d[k] = c[k];
      if (c.substituir_historico) d.historico = c.historico || [];
      d.rev++; registrarHistorico(d); return clone(d);
    },
    async indices(v) {
      let mudou = false;
      for (const k of ['cdi', 'selic', 'ipca', 'tr']) if (k in v && v[k] !== d.indices[k]) { d.indices[k] = v[k]; mudou = true; }
      if (mudou) Object.assign(d.indices, { auto: false, fonte: 'manual', atualizado_em: new Date().toISOString(), erro: null });
      if ('auto' in v) d.indices.auto = !!v.auto;
      return clone(d);
    },
    async atualizarIndices() {
      await espera(700);
      Object.assign(d.indices, INDICES_PADRAO, { auto: d.indices.auto, fonte: 'bcb', atualizado_em: new Date().toISOString() });
      return clone(d);
    },
    async backup() { await espera(400); return { arquivo: `gerencia-${iso(hoje())}.zip`, pasta: 'share/gerencia' }; },
    async importar() { throw new Error('Na prévia não dá para importar arquivos.'); },
    async versoes() {
      const t = totais(d.investimentos, d).total;
      return [0.3, 2, 26].map((h, i) => ({ nome: 'v' + i, quando: new Date(Date.now() - h * 3600000).toISOString(), motivo: 'auto', investimentos: d.investimentos.length, total: t * (1 - i * 0.004) }));
    },
    async restaurar() { throw new Error('Na prévia não dá para restaurar versões.'); },
    async foto() { await espera(200); return { arquivo: `demo-${uid()}.jpg` }; },
    async iaStatus() { return { pronta: true, entidades: [{ id: 'ai_task.google_ai_task', nome: 'Google AI Task', imagens: true }], selecionada: '' }; },
    async bens() { return bensDemo(); },
    async bensAtualizar() { return bensDemo(); },
    async dicas() {
      // Na prévia: preços conferidos nas páginas oficiais em 18/10/2026 (no app, o servidor confere de novo a cada 30 dias)
      await espera(250);
      const F = [
        { id: 'nabucasa', nome: 'Nabu Casa', re: /nabu ?casa|home assistant cloud/i, fonte: 'https://www.nabucasa.com/pricing/', dominio: 'nabucasa.com', planos: [{ plano: 'Mensal', moeda: 'USD', mensal: 6.5, anual: 65 }] },
        { id: 'spotify', nome: 'Spotify', re: /spotify/i, fonte: 'https://www.spotify.com/br-pt/premium/', dominio: 'spotify.com', planos: [{ plano: 'Premium Individual', moeda: 'BRL', mensal: 23.9, anual: 239 }, { plano: 'Premium Duo', moeda: 'BRL', mensal: 31.9, anual: 379 }, { plano: 'Premium Família', moeda: 'BRL', mensal: 40.9, anual: 490 }] },
        { id: 'microsoft365', nome: 'Microsoft 365', re: /microsoft ?365|office ?365/i, fonte: 'https://www.microsoft.com/pt-br/microsoft-365/buy/compare-all-microsoft-365-products', dominio: 'microsoft.com', planos: [{ plano: 'Personal', moeda: 'BRL', mensal: 51, anual: 509 }, { plano: 'Family', moeda: 'BRL', mensal: 60, anual: 599 }] },
      ];
      const dolar = 5.04, assinaturas = [], dicas = [];
      const anuais = new Set(d.recorrencias.filter(r => r.freq === 'anual' && !r.fim).map(r => (F.find(x => x.re.test(r.descricao || '')) || {}).id));
      for (const r of d.recorrencias) {
        if (r.tipo === 'receita' || r.fim) continue;
        const f = F.find(x => x.re.test(r.descricao || ''));
        if (!f || (r.freq !== 'anual' && anuais.has(f.id))) continue;
        const b = { chave: 'r:' + r.id, rid: r.id, origem: 'fixo', servico: f.id, nome: f.nome, descricao: r.descricao, valor: +r.valor, freq_anual: r.freq === 'anual',
          conta: r.conta, cartao: !!r.cartao, categoria: r.categoria, dia: r.dia, fonte: f.fonte, dominio: f.dominio, conferido: '2026-10-18' };
        if (b.freq_anual) { assinaturas.push(Object.assign(b, { status: 'ja_anual', texto: 'Já está no plano anual.' })); continue; }
        const p = f.planos.find(q => { const k = r.valor / (q.mensal * (q.moeda === 'USD' ? dolar : 1)); return q.moeda === 'USD' ? k >= 0.97 && k <= 1.25 : k >= 0.95 && k <= 1.06; });
        if (!p) { assinaturas.push(Object.assign(b, { status: 'plano_nao_bate', texto: 'O valor que você paga não bate com nenhum plano da página.' })); continue; }
        const pc = 1 - p.anual / (12 * p.mensal), eco = round2(12 * r.valor * pc);
        if (pc < 0.03 || eco < 10) { assinaturas.push(Object.assign(b, { status: 'sem_vantagem', texto: 'O plano anual custa quase o mesmo que pagar por mês.' })); continue; }
        const x = Object.assign(b, { status: 'ok', texto: 'Dá para economizar no plano anual.', plano: p.plano, moeda: p.moeda, mensal: p.mensal, anual: p.anual, pct: Math.round(pc * 1000) / 10,
          economia_ano: eco, preco_anual: p.moeda === 'BRL' ? p.anual : round2(12 * r.valor * (1 - pc)), estimado: p.moeda !== 'BRL' });
        assinaturas.push(x);
        dicas.push(Object.assign({ id: 'anual:' + x.chave }, x));
      }
      dicas.sort((a, b) => b.economia_ano - a.economia_ano);
      return { dicas, assinaturas, conferindo: false, catalogo: ['Nabu Casa', 'Claude', 'Spotify', 'Microsoft 365', 'Deezer'], dolar: { valor: dolar, data: '14/10/2026' } };
    },
    async dicasConferir() { await espera(900); return this.dicas(); },
    // na prévia não há Home Assistant: as pessoas da casa são inventadas e o aviso não sai
    async avisoPessoas() { return { pessoas: [{ id: 'person.ana', nome: 'Ana', celular: true, eu: true }, { id: 'person.beto', nome: 'Beto', celular: false, eu: false }] }; },
    async avisoTestar() { throw new Error('Na prévia o aviso não é enviado.'); },
    // na prévia as senhas ficam só na memória (inventadas, nunca as de verdade)
    async senhas() { return { senhas: (this._senhas || []).map(x => ({ id: x.id, nome: x.nome, fim: '••••' + (x.senha.length >= 4 ? x.senha.slice(-2) : '') })) }; },
    async senhaNova(nome, senha) { if (!String(senha || '').trim()) throw new Error('Digite a senha.'); (this._senhas = this._senhas || []).push({ id: uid(), nome: nome || 'Senha', senha: String(senha).trim() }); return this.senhas(); },
    async senhaApagar(id) { this._senhas = (this._senhas || []).filter(x => x.id !== id); return this.senhas(); },
    // faturas por e-mail na prévia: sem Home Assistant, a lista fica na memória (vazia; os testes põem e-mails inventados)
    async emails() { const ligado = S.d.ajustes.email === true && iaOn(); return { ligado, conectada: ligado, contas: ligado ? [{ id: 'imap-previa', nome: 'ana@exemplo.com', ok: true }] : null, itens: clone(this._emails || []) }; },
    async emailPdf() { throw new Error('Na prévia não há PDF.'); },
    async emailAcao(acao, id) { const it = (this._emails || []).find(x => x.id === id); if (!it) throw new Error('Esse e-mail não está mais aqui.'); it.estado = acao === 'ler' ? 'lendo' : acao === 'feito' ? 'feito' : 'ignorado'; it.erro = ''; if (acao !== 'ler') delete it.resultado; return this.emails(); },
    // a conversa com a IA na prévia: guardada na memória, com respostas de exemplo (chatDemo)
    async chat() { return { mensagens: clone(CHAT_DEMO) }; },
    async chatEnviar(c) {
      await espera(500);
      CHAT_DEMO.push({ id: uid(), papel: 'eu', texto: c.texto, fala: !!c.fala }, Object.assign({ id: uid(), papel: 'ia' }, chatDemo(c.texto)));
      CHAT_DEMO.splice(0, Math.max(0, CHAT_DEMO.length - 60));
      return { mensagens: clone(CHAT_DEMO) };
    },
    async chatAcao(id, grupo, estado) { const m = CHAT_DEMO.find(x => x.id === id); if (m) m.estado = Object.assign({}, m.estado, { [grupo]: estado }); return { mensagens: clone(CHAT_DEMO) }; },
    async chatLimpar() { CHAT_DEMO.length = 0; return { mensagens: [] }; },
    async vozStatus() {
      const opcoes = [{ id: 'stt.home_assistant_cloud', nome: 'Home Assistant Cloud', idioma: 'pt-BR', assistentes: ['Home Assistant'], preferido: true },
        { id: 'stt.google_ai_stt', nome: 'Google AI STT', idioma: 'pt-BR', assistentes: ['Gemini'], preferido: false }];
      const sel = opcoes.find(o => o.id === S.d.ajustes.voz_motor);
      return { pronta: true, nome: (sel || opcoes[0]).nome, selecionada: sel ? sel.id : '', opcoes };
    },
    async vozTexto() { await espera(900); return { texto: 'Gastei 45 reais no mercado hoje no cartão do Banco Lua e recebi 150 do João pelo Pix', nome: 'Home Assistant Cloud' }; },
    async iaUso() {
      const dia = k => iso(new Date(hoje().getTime() - (6 - k) * 864e5));
      const rec = [['fala', 'ok', 3.4, 1100, 0], ['caixa', 'ok', 9.2, 2400, 1], ['holerite', 'ok', 7.8, 2100, 1], ['precos', 'ok', 4.1, 1500, 0], ['invest', 'cota', 1.3, 900, 1]]
        .map(([kind, result, seconds, tokens, images], k) => ({ at: new Date(Date.now() - (k * 37 + 6) * 60000).toISOString(), kind, entity: 'ai_task.google_ai_task', result, seconds, tokens, images }));
      return { today: { calls: 5, errors: 0, quota: 1, tokens: 8000, images: 3, kinds: { fala: 1, caixa: 1, holerite: 1, precos: 1, invest: 1 }, entities: {} },
        week: { calls: 16, errors: 1, quota: 1, tokens: 29100, images: 9, kinds: { caixa: 6, precos: 4, fala: 2, holerite: 2, invest: 2 }, entities: { 'ai_task.google_ai_task': 15 } },
        month: { calls: 38, errors: 2, quota: 1, tokens: 71000, images: 22, kinds: {}, entities: { 'ai_task.google_ai_task': 38 } },
        days: [1, 3, 0, 2, 4, 1, 5].map((calls, k) => ({ day: dia(k), calls, errors: k === 3 ? 1 : 0, quota: k === 6 ? 1 : 0 })), recent: rec, sensor: 'sensor.gerencia_ia_hoje' };
    },
    async backups() {
      const b = k => ({ nome: `gerencia-${iso(new Date(hoje().getTime() - k * 864e5))}-2105.zip`, tamanho: 182000 - k * 1500, quando: new Date(Date.now() - k * 864e5 - 3 * 36e5).toISOString() });
      return [b(0), b(7), b(14)];
    },
    async restaurarBackup() { throw new Error('Na prévia não dá para restaurar backups.'); },
    async iaLer(c) {
      await espera(1600);
      if (c.modo === 'holerite') return { holerite: { data: '', creditos: [{ descricao: 'Produção', valor: 4200 }, { descricao: 'Ajuda de custo', valor: 7600 }, { descricao: 'Transporte', valor: 1250 }],
        debitos: [{ descricao: 'INSS', valor: 840, tipo: 'imposto' }, { descricao: 'Taxa administrativa', valor: 587.25, tipo: 'imposto' }, { descricao: 'Plano de saúde titular', valor: 320, tipo: 'saude' }, { descricao: 'Coparticipação', valor: 85.4, tipo: 'saude' }],
        total_creditos: 13050, total_debitos: 1832.65, liquido: 11217.35 }, entidade: 'simulada' };
      if (c.saldos || (c.so_invest && /\d/.test(c.texto || '') && !/apliquei|investi|aplica[çc]/i.test(c.texto || ''))) {
        // na prévia, cada linha com um valor ("30.350 banco lua", "Banco Lua, valor atualizado, R$ 500") acha o investimento pelo banco ou pelo nome
        const linhas = String(c.texto || '').split(/[\n;]+/).map(x => x.trim()).filter(Boolean);
        let dono = c.pessoa || '';
        for (const l of linhas) { const m = l.match(/\b(?:da|do|de)\s+([a-zà-ú]+)\s*$/i); if (m && !/\d/.test(l) && !dono) dono = donoDe(m[1]); }
        const invs = [];
        for (const linha of linhas) {
          const m = linha.match(/(?:r\$\s*)?(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)\s*(mil\b)?/i);
          if (!m) continue;
          const nome = (linha.slice(0, m.index) + ' ' + linha.slice(m.index + m[0].length)).replace(/valor atualizado|saldo|atualizado|r\$/gi, '').replace(/[,:;–-]/g, ' ').replace(/\s+/g, ' ').trim();
          if (!nome) continue;
          const parado = /^(dinheiro|em casa|em espécie|cofre)$/i.test(nome);
          const it = { nome: nome[0].toUpperCase() + nome.slice(1), banco: parado ? '' : nome, tipo: parado ? 'dinheiro' : 'outro', valor: +m[1].replace(/\./g, '').replace(',', '.') * (m[2] ? 1000 : 1), aporte: 0, existente: '',
            dono: dono === 'meu' ? '' : dono, indexador: parado ? 'parado' : 'cdi_pct', taxa: parado ? 0 : 100, liquidez: 'diaria', confianca: 'alta' };
          it.existente = parado ? '' : acharInvSaldo(Object.assign({}, it, { banco: nome }), dono);
          const ex = it.existente && d.investimentos.find(i => i.id === it.existente);
          if (ex) Object.assign(it, { nome: ex.nome, tipo: ex.tipo, indexador: ex.indexador, taxa: ex.taxa, liquidez: ex.liquidez });
          invs.push(it);
        }
        return { lancamentos: [], investimentos: invs, entidade: 'simulada' };
      }
      const hj = iso(hoje()), ont = iso(new Date(hoje().getTime() - 86400000));
      const t = (c.texto || '').toLowerCase();
      // na prévia, a IA "lê" pelo texto: palavras de investimento trazem investimentos, de gasto trazem lançamentos
      let inv = /cdb|tesouro|\blc[ia]\b|invest|apliquei|aplica[çc]|% do cdi|caixinha|rende/.test(t), cx = /gast|receb|pagu|pagar|compr|fatura|pix|mercado|boleto|conta de|sal[áa]rio/.test(t);
      if (!inv && !cx) { inv = c.dica === 'invest'; cx = !inv; }
      const lanc = !cx ? [] : /mercado/.test(t) && /jo[aã]o/.test(t) ? [
        { tipo: 'despesa', descricao: 'Mercado', valor: 45, data: hj, categoria: 'c-mercado', parcela_atual: 0, parcelas_total: 0, cartao: true, banco: 'Banco Lua', situacao: 'feito', confianca: 'alta' },
        { tipo: 'receita', descricao: 'Pix do João', valor: 150, data: hj, categoria: 'c-reembolso', parcela_atual: 0, parcelas_total: 0, cartao: false, banco: '', situacao: 'feito', confianca: 'alta' },
      ] : [
        { tipo: 'despesa', descricao: 'iFood', valor: 64.9, data: ont, categoria: 'c-restaurantes', parcela_atual: 0, parcelas_total: 0, cartao: true, banco: 'Banco Lua', situacao: 'feito', confianca: 'alta' },
        { tipo: 'despesa', descricao: 'Posto Shell', valor: 210, data: ont, categoria: 'c-transporte', parcela_atual: 0, parcelas_total: 0, cartao: true, banco: 'Banco Lua', situacao: 'feito', confianca: 'alta' },
        { tipo: 'despesa', descricao: 'Magazine Luiza', valor: 189.9, data: iso(addMeses(hoje(), -1)), categoria: 'c-compras', parcela_atual: 2, parcelas_total: 6, cartao: true, banco: 'Banco Lua', situacao: '', confianca: 'media' },
        { tipo: 'despesa', descricao: 'IPVA', valor: 1480, data: iso(addMeses(hoje(), 1)), categoria: 'c-impostos', parcela_atual: 0, parcelas_total: 0, cartao: false, banco: '', situacao: 'pendente', confianca: 'alta' },
        { tipo: 'receita', descricao: 'Pix do João', valor: 150, data: hj, categoria: 'c-reembolso', parcela_atual: 0, parcelas_total: 0, cartao: false, banco: '', situacao: 'feito', confianca: 'alta' },
      ];
      const cdb = d.investimentos.find(i => i.tipo === 'cdb');
      const invs = !inv ? [] : [
        { nome: 'CDB Sol 2028', banco: 'Banco Sol', tipo: 'cdb', valor: 15412.37, aplicado: 15000, data_valor: hj, indexador: 'cdi_pct', taxa: 112, vencimento: '2028-03-13', liquidez: 'vencimento', existente: cdb ? cdb.id : '', confianca: 'alta' },
        { nome: 'LCA Banco Mar 2027', banco: 'Banco Mar', tipo: 'lci', valor: 10250, aplicado: 10000, data_valor: hj, indexador: 'cdi_pct', taxa: 93, vencimento: '2027-09-20', liquidez: 'vencimento', existente: '', confianca: 'media' },
      ];
      if (c.modo === 'invest') return { itens: invs.length ? invs : [{ nome: 'CDB Sol 2028', banco: 'Banco Sol', tipo: 'cdb', valor: 15412.37, aplicado: 15000, data_valor: hj, indexador: 'cdi_pct', taxa: 112, vencimento: '2028-03-13', liquidez: 'vencimento', existente: cdb ? cdb.id : '', confianca: 'alta' }], entidade: 'simulada' };
      return { lancamentos: lanc, investimentos: invs, entidade: 'simulada' };
    },
  };
}
const api = DEMO ? apiDemo() : apiServidor;

let fila = Promise.resolve();
function persistir(mut, ok) {
  fila = fila.then(async () => {
    const novo = clone(S.d);
    mut(novo);
    const corpo = { rev: novo.rev, bancos: novo.bancos, investimentos: novo.investimentos, ajustes: novo.ajustes, exemplo: novo.exemplo,
      lancamentos: novo.lancamentos, recorrencias: novo.recorrencias, categorias: novo.categorias };
    if (novo._hist) { corpo.substituir_historico = true; corpo.historico = novo._hist; }
    try {
      S.d = normalizar(await api.save(corpo));
      render();
      if (ok) toast(ok);
      agendarDicas();
      return true;
    } catch (e) {
      if (e.conflito) { S.d = normalizar(e.d); render(); toast('Os dados mudaram em outro aparelho. Confira e tente de novo.'); }
      else toast('Não consegui salvar. ' + (e.message || ''));
      return false;
    }
  });
  return fila;
}

/* ------------------------------------------------------------------ tema */
function temaHA() {
  try {
    if (window.parent && window.parent !== window) {
      const ha = window.parent.document.querySelector('home-assistant');
      const dm = ha && ha.hass && ha.hass.themes && ha.hass.themes.darkMode;
      if (typeof dm === 'boolean') return dm ? 'dark' : 'light';
    }
  } catch (e) { /* fora do Home Assistant */ }
  return window.matchMedia && matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}
// Na prévia, o modo automático respeita o tema escolhido no visualizador.
const TEMA_HOST = document.documentElement.getAttribute('data-theme');
// a cor que vale agora: a do dia (só um "desligado" explícito desliga) ou a escolhida em Aparência
const corDiaOn = () => S.d.ajustes.cor_dia !== false;
const corDoApp = () => corDiaOn() ? corDoDia() : (corOk(S.d.ajustes.cor) || AJUSTES_PADRAO.cor);
let diaDaCor = null; // o dia da cor posta por último
function aplicarTema() {
  if (!S.d) return;
  const a = S.d.ajustes;
  const root = document.documentElement;
  if (DEMO && a.tema === 'auto') {
    if (TEMA_HOST) root.setAttribute('data-theme', TEMA_HOST); else root.removeAttribute('data-theme');
  } else {
    const t = a.tema === 'claro' ? 'light' : a.tema === 'escuro' ? 'dark' : temaHA();
    if (root.dataset.theme !== t) root.dataset.theme = t;
  }
  diaDaCor = numeroDoDia();
  root.style.setProperty('--accent', corDoApp());
  root.dataset.ia = a.ia === false ? 'off' : 'on';
  const meta = $('meta[name="theme-color"]');
  if (meta) meta.content = getComputedStyle(root).getPropertyValue('--bg').trim() || '#0f1318';
}
if (!DEMO) setInterval(() => { if (S.d && S.d.ajustes.tema === 'auto') aplicarTema(); }, 2000);
// o relatório (uma página do servidor) abre no mesmo tema que o app está usando agora
const urlRelatorio = () => 'relatorio?tema=' + (document.documentElement.dataset.theme === 'light' ? 'claro' : 'escuro');
// Com a Cor do dia, o app aberto troca de cor à meia-noite sem recarregar (confere a cada minuto e ao voltar para ele).
function conferirCorDoDia() {
  if (!S.d || !corDiaOn() || numeroDoDia() === diaDaCor) return;
  if (maisTela() === 'config' && maisAba() === 'aparencia') render(); else aplicarTema();
}
setInterval(conferirCorDoDia, 60000);
window.addEventListener('focus', conferirCorDoDia);
document.addEventListener('visibilitychange', () => { if (!document.hidden) conferirCorDoDia(); });
try { matchMedia('(prefers-color-scheme: light)').addEventListener('change', aplicarTema); } catch (e) { /* antigo */ }

/* ------------------------------------------------------------------ peças */
const toastEl = () => $('#toast');
let toastT;
function toast(msg) {
  const el = toastEl();
  el.textContent = msg;
  el.classList.add('on');
  clearTimeout(toastT);
  toastT = setTimeout(() => el.classList.remove('on'), 3200);
}

// Cabeçalho no padrão EconomIA: marca com "IA" na cor do app, saudação e linha de situação.
function syncInfo() {
  const I = S.d.indices;
  const q = I.atualizado_em ? new Date(I.atualizado_em) : null;
  const hora = q ? q.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : '';
  if (I.erro) return ['erro', 'Sem conexão com o Banco Central'];
  if (I.fonte === 'manual') return ['manual', 'Índices digitados à mão'];
  if (I.fonte === 'bcb' && q) return ['', iso(q) === iso(hoje()) ? `Índices do Banco Central de hoje, ${hora}` : `Índices do Banco Central de ${fDataC(q)}`];
  // com Atualizar sozinho desligado, os do Banco Central não vêm: ficam os de partida
  return ['manual', DEMO ? 'Exemplo com os índices de outubro de 2026' : I.auto === false ? 'Índices de partida (outubro de 2026)' : 'Esperando os índices do Banco Central'];
}
// O ícone do app ao lado do nome (no alto e na barra lateral), na cor escolhida em Aparência, como no ResolvIA e no CronologIA:
// as duas plaquinhas "R$" do placar.
const iconeApp = () => `<svg class="app-ic" viewBox="0 0 32 32" aria-hidden="true">
  <rect x="2" y="5" width="13.2" height="22" rx="3.2" fill="var(--accent)"/><rect x="16.8" y="5" width="13.2" height="22" rx="3.2" fill="var(--accent)"/>
  <rect x="2" y="5" width="28" height="11" rx="3.2" fill="#fff" fill-opacity=".16"/>
  <path d="M2 16h2.4M12.8 16h2.4M16.8 16h2.4M27.6 16h2.4" stroke="var(--bg)" stroke-width="1.6"/>
  <text x="8.6" y="23.2" text-anchor="middle" font-family="Barlow Condensed, Arial Narrow, sans-serif" font-weight="700" font-size="18.5" fill="var(--on-accent)">R</text>
  <text x="23.4" y="23.2" text-anchor="middle" font-family="Barlow Condensed, Arial Narrow, sans-serif" font-weight="700" font-size="18.5" fill="var(--on-accent)">$</text></svg>`;
// status: [classe, texto] da linha embaixo do título (sem ele, a dos índices; false, sem a linha);
// volta: numa tela de Mais, o caminho de volta para o menu no alto ("‹ Mais"), como no InventarIA
function cabecalho(titulo, acoes = '', status = null, volta = false) {
  const [cls, txt] = status || syncInfo();
  return `<header class="cab"><div class="cab-topo"><p class="eyebrow"><span class="brand">${iconeApp()}Gerenc<span>IA</span></span>${S.usuario ? `<span class="eb-sep"> · </span>Olá, ${esc(S.usuario.split(' ')[0])}` : ''}</p>${botaoChat()}${botaoFalar()}</div>
    ${volta ? `<button class="uplink" data-a="mais-volta">${ic('chevL', 'ic-s')}Mais</button>` : ''}
    <div class="cab-linha"><h1>${titulo}</h1>${acoes}</div>${acoesTopo(acoes)}</header>
    ${status === false ? '' : `<p class="sync ${cls}"><span class="dot" aria-hidden="true"></span><span>${txt}</span></p>`}`;
}

// No computador, as ações ficam no alto à direita, como no ResolvIA e no CronologIA: Falar, esconder valores, Ler com IA e Adicionar.
function acoesTopo(acoes) {
  const olho = /data-a="olho"/.test(acoes)
    ? `<button class="icbtn" data-a="olho" aria-label="${S.oculto ? 'Mostrar' : 'Esconder'} valores" title="${S.oculto ? 'Mostrar' : 'Esconder'} valores">${ic(S.oculto ? 'eyeOff' : 'eye')}</button>` : '';
  const v = S.ui.tab === 'investimentos' ? 'invest' : 'caixa';
  return `<div class="top-acts">${botaoChat()}${botaoFalar()}${olho}<button class="btn" data-a="ia" data-v="${v}">${ic('ia', 'ic-s')}Ler com IA</button>
    <button class="btn pri" data-a="novo">${ic('plus', 'ic-s')}Adicionar</button></div>`;
}

// Placar de cotações com plaquinhas que viram (split-flap): o destaque principal do Início.
let PLACAR_ULTIMO = null;
function placar({ cab, data, valor, palavra, cols, texto, rotulo }) {
  const chars = [...valor];
  const sep = ch => ch === '.' || ch === ',';
  const nSep = chars.filter(sep).length;
  const n = (chars.length - nSep) + nSep * 0.32 + (palavra ? 0 : 0.9);
  const vira = PLACAR_ULTIMO !== valor;
  PLACAR_ULTIMO = valor;
  let i = 0;
  const plaquinhas = chars.map((ch, k) => sep(ch)
    ? `<span class="flap ponto"><span>${ch}</span></span>`
    : `<span class="flap${palavra && k >= chars.length - 2 ? ' acento' : ''}" style="--i:${i++}"><span>${esc(ch)}</span></span>`).join('');
  return `<section class="placar${vira ? ' vira' : ''}">
    <div class="placar-cab"><span class="led" aria-hidden="true"></span><span>${cab}</span><span class="dt">${data}</span></div>
    <div class="placar-num" style="--n:${n.toFixed(2)}" role="img" aria-label="${esc(rotulo || valor)}">${palavra ? '' : '<span class="moeda" aria-hidden="true">R$</span>'}${plaquinhas}</div>
    ${texto ? `<p class="placar-txt">${texto}</p>`
      : `<div class="placar-cols">${cols.map(([k, v, ac]) => `<div><span>${k}</span><b${ac ? ` class="${ac === true ? 'acento' : ac}"` : ''}>${v}</b></div>`).join('')}</div>`}
  </section>`;
}

function tagDono(i) {
  return i.titular === 'terceiros'
    ? `<span class="tag terc">${ic('users')}De ${esc(dono(i))}</span>`
    : `<span class="tag meu">${ic('user')}Meu</span>`;
}

function quandoVence(dias) {
  if (dias < 0) return 'venceu';
  if (dias === 0) return 'hoje';
  if (dias === 1) return 'amanhã';
  return `em ${dias} dias`;
}

/* ------------------------------------------------------------------ Início */
function telaInicio() {
  const d = S.d;
  if (!d.investimentos.length && !temCaixa()) return telaBoasVindas();
  const h = hoje();
  const t = totais();
  const olho = `<button class="icbtn" data-a="olho" aria-label="${S.oculto ? 'Mostrar' : 'Esconder'} valores">${ic(S.oculto ? 'eyeOff' : 'eye')}</button>`;
  let html = cabecalho('Início', olho);
  if (d.exemplo) html += avisoExemplo();
  if (!d.investimentos.length) {
    const r = resumoMes(ymHoje());
    html += placar({ cab: 'Saldo em caixa', data: fData(h), valor: numf(saldoCaixa(), 0), rotulo: `Saldo em caixa de ${brl(saldoCaixa(), 0)}`,
      cols: [['Entrou', brl(r.entrou, 0), 'ent'], ['Saiu', brl(r.saiu, 0), 'sai'], ['Sobrou', brl(r.sobra, 0), true]] });
    return html.replace('<section class="placar', '<div class="ini-g so-caixa"><section class="placar') + `<div class="ini-ga">${cardDicas()}</div><div class="ini-gb">${avisosInicio(h)}</div></div>`;
  }

  // o patrimônio é só o seu: investimentos seus e, com o InventarIA, os bens da casa (o dinheiro de terceiros fica de fora)
  const B = bensOn() ? S.bens : null;
  // bens: os do InventarIA e os seus cadastrados aqui (tipo Bens, um carro…); perdem valor e não contam como investido
  const meus = porEscopo('meu'), meusInv = meus.filter(i => i.tipo !== 'bens'), tm = totais(meusInv);
  const bensT = (B ? B.hoje : 0) + meus.filter(i => i.tipo === 'bens').reduce((a, i) => a + valorHoje(i), 0), pat = tm.total + bensT;
  html += '<div class="ini-g">' + placar({
    cab: 'Patrimônio', data: fData(h), valor: numf(pat, 0), rotulo: `Patrimônio de ${brl(pat, 0)}`,
    cols: bensT > 0 ? [
      ['Investido', brl(tm.total, 0), 'meu'],
      ['Bens', brl(bensT, 0)],
      ['Por mês', (S.oculto ? '' : '+') + brl(tm.mes, 0), true],
    ] : [
      ['Investimentos', String(meusInv.length)],
      ['Bancos', String(new Set(meusInv.map(i => i.banco).filter(Boolean)).size)],
      ['Por mês', (S.oculto ? '' : '+') + brl(tm.mes, 0), true],
    ],
  });

  html += `<div class="ini-ga">${temCaixa() ? cardCaixaInicio() + cardDicas() : ''}</div>`;
  // destaques
  const rows = [];
  const tr = tm.total > 0 ? tm : t;  // só com dinheiro de terceiros, mostra o rendimento dele
  rows.push(`<button class="hl-row" data-a="inv-modo" data-v="evolucao"><div><div class="hl-k">${tm.total > 0 ? 'Rende por mês' : 'Rende por mês, de terceiros'}</div>
    <div class="hl-v">Média de ${pct(tr.rMed * 100)}% a.a.</div></div><div class="hl-n">${brl(tr.mes, 0)}<small>antes do IR</small></div></button>`);
  const fixos = d.investimentos.filter(i => i.indexador !== 'estimado' && i.indexador !== 'parado');
  if (fixos.length) {
    const melhor = fixos.reduce((a, b) => taxaAnual(b) > taxaAnual(a) ? b : a);
    rows.push(`<button class="hl-row" data-a="inv" data-id="${melhor.id}"><div><div class="hl-k">Melhor rendimento</div>
      <div class="hl-v">${esc(melhor.nome)}</div></div><div class="hl-n">${pct(taxaAnual(melhor) * 100)}%<small>${esc(rotuloTaxa(melhor))}</small></div></button>`);
  }
  const comVenc = d.investimentos.map(i => ({ i, dt: pData(i.vencimento) })).filter(x => x.dt && x.dt >= h).sort((a, b) => a.dt - b.dt);
  if (comVenc.length) {
    const { i, dt } = comVenc[0];
    const dias = diasEntre(h, dt);
    rows.push(`<button class="hl-row" data-a="inv" data-id="${i.id}"><div><div class="hl-k">Vence primeiro</div>
      <div class="hl-v">${esc(i.nome)}</div></div><div class="hl-n${dias <= 30 ? ' alerta' : ''}">${dias <= 90 ? quandoVence(dias) : fData(dt)}<small>${brl(valorHoje(i), 0)}</small></div></button>`);
  }
  if (B) rows.push(`<button class="hl-row" data-a="bens"><div><div class="hl-k">Bens da casa</div>
      <div class="hl-v">${plural(B.n, 'item', 'itens')} no InventarIA</div></div><div class="hl-n">${brl(B.hoje, 0)}<small>${varAno(B.perde_ano)}</small></div></button>`);
  const pb = {};
  for (const i of d.investimentos) pb[i.banco || ''] = (pb[i.banco || ''] || 0) + valorHoje(i);
  const [bId, bVal] = Object.entries(pb).sort((a, b) => b[1] - a[1])[0] || [];
  if (bVal) {
    rows.push(`<button class="hl-row" data-a="graf-comp" data-v="banco"><div><div class="hl-k">Maior banco</div>
      <div class="hl-v">${esc(bancoDe(bId)?.nome || 'Sem banco')}</div></div><div class="hl-n">${pct(Math.round(bVal / t.total * 100))}%<small>${brl(bVal, 0)}</small></div></button>`);
  }
  const alvo = meus.length ? meus : d.investimentos;
  const apM = aporteMensal();
  const pr = projetar(alvo, 1, apM, false).pts;
  const ganho = pr[12].valor - pr[0].valor;
  rows.push(`<button class="hl-row" data-a="inv-modo" data-v="evolucao"><div><div class="hl-k">${meus.length ? 'Seu dinheiro em 1 ano' : 'Em 1 ano'}</div>
    <div class="hl-v">${apM ? `Com aporte de ${brl(apM, 0)} por mês` : 'Sem novos aportes'}</div></div><div class="hl-n">${brl(pr[12].valor, 0)}<small>+${brl(ganho, 0)}</small></div></button>`);
  html += `<div class="hl">${rows.join('')}</div><div class="ini-gb">`;

  // terceiros
  const ps = pessoas();
  if (ps.length) {
    html += `<div class="card flush"><div class="rot">${rotIc('users', 'terc')}<span class="rot-t">Dinheiro de terceiros</span><b>${brl(t.terc, 0)}</b></div>`;
    for (const p of ps) {
      const l = d.investimentos.filter(i => i.titular === 'terceiros' && dono(i) === p);
      const v = l.reduce((s, i) => s + valorHoje(i), 0);
      const bs = [...new Set(l.map(i => bancoDe(i.banco)?.nome).filter(Boolean))].join(', ');
      html += `<button class="op" data-a="pessoa" data-v="${esc(p)}"><div class="op-ic terc">${esc(p.slice(0, 1).toUpperCase())}</div>
        <div class="op-t"><b>${esc(p)}</b><span>${plural(l.length, 'investimento', 'investimentos')}${bs ? ' · ' + esc(bs) : ''}</span></div>
        <div class="op-n terc">${brl(v, 0)}</div>${ic('chev', 'chev')}</button>`;
    }
    html += '</div>';
  }

  // avisos
  const av = avisosCaixa(h);
  const vencidos = d.investimentos.filter(i => { const v = pData(i.vencimento); return v && v < h; });
  if (vencidos.length) {
    av.push(`<button class="op" data-a="inv" data-id="${vencidos[0].id}"><div class="op-ic alerta">${ic('alert')}</div>
      <div class="op-t"><b>${vencidos.length === 1 ? 'Um investimento venceu' : `${vencidos.length} investimentos venceram`}</b><span>${esc(vencidos.map(i => i.nome).join(', '))}</span></div>${ic('chev', 'chev')}</button>`);
  }
  const breve = comVenc.filter(x => diasEntre(h, x.dt) <= 30);
  if (breve.length) {
    const x = breve[0];
    av.push(`<button class="op" data-a="inv" data-id="${x.i.id}"><div class="op-ic terc">${ic('calendar')}</div>
      <div class="op-t"><b>Vence ${quandoVence(diasEntre(h, x.dt))}</b><span>${esc(x.i.nome)} · decida para onde vai o dinheiro</span></div>
      <div class="op-n alerta">${diasEntre(h, x.dt)}<small>dias</small></div>${ic('chev', 'chev')}</button>`);
  }
  const velhos = d.investimentos.filter(i => i.indexador !== 'parado' && diasEntre(pData(i.data_valor) || h, h) > 60);
  if (velhos.length) {
    av.push(`<button class="op" data-a="inv" data-id="${velhos[0].id}"><div class="op-ic neutro">${ic('clock')}</div>
      <div class="op-t"><b>Atualize os valores</b><span>${velhos.length === 1 ? esc(velhos[0].nome) + ' está' : velhos.length + ' investimentos estão'} sem atualizar há mais de 2 meses</span></div>
      <div class="op-n">${velhos.length}</div>${ic('chev', 'chev')}</button>`);
  }
  const I = d.indices;
  const quando = I.atualizado_em ? fDataC(new Date(I.atualizado_em)) : '—';
  const fonte = I.erro ? 'sem conexão' : I.fonte === 'manual' ? 'manual' : I.fonte === 'bcb' ? 'Banco Central' : 'padrão';
  av.push(`<button class="op" data-a="tab" data-v="mais" data-ancora="indices"><div class="op-ic${I.erro ? ' alerta' : ''}">${ic('trend')}</div>
    <div class="op-t"><b>Índices</b><span>CDI ${pct(I.cdi)}% · Selic ${pct(I.selic)}% · IPCA ${pct(I.ipca)}%</span></div>
    <div class="op-n">${quando}<small>${fonte}</small></div>${ic('chev', 'chev')}</button>`);
  html += `<div class="card flush"><div class="rot">${rotIc('alert', 'aviso')}<span class="rot-t">Avisos</span></div>${av.join('')}</div>`;
  return html + '</div></div>';
}

function cardCaixaInicio() {
  const ym = ymHoje();
  return `<div class="card cx-card"><div class="rot">${rotIc('fluxo')}<span class="rot-t">Caixa de ${MESES_LONGOS[+ym.slice(5) - 1]}</span></div>${resumoCaixaHTML(ym)}
    <button class="cx-card-pe" data-a="tab" data-v="caixa"><span>Saldo hoje <b>${brl(saldoCaixa(), 0)}</b> · fim do mês <b>${brl(saldoPrevisto(ym), 0)}</b></span>${ic('chev', 'chev')}</button></div>`;
}
function avisosCaixa(h) {
  const av = avisosEmail();
  if (!temCaixa()) return av;
  const hj = iso(h);
  const pend = lancamentosEntre(addYm(ymHoje(), -2), addYm(ymHoje(), 1)).filter(l => !l.pago && !l.ajuste && !ehRec(l) && !l.vinculo && !l.desconto);
  const nomes = l => l.cartao && contaDe(l.conta)?.cartao ? 'Fatura ' + nomeConta(contaDe(l.conta)) : l.descricao;
  const agrupar = lista => { const m = new Map(); for (const l of lista) { const k = nomes(l); m.set(k, (m.get(k) || 0) + (+l.valor || 0)); } return m; };
  const atras = agrupar(pend.filter(l => l.dc < hj));
  S.nAtrasadas = atras.size;
  if (atras.size) {
    const soma = [...atras.values()].reduce((a, b) => a + b, 0);
    av.push(`<button class="op" data-a="cx-ir" data-v="pendentes"><div class="op-ic alerta">${ic('alert')}</div>
      <div class="op-t"><b>${atras.size === 1 ? 'Uma conta atrasada' : `${atras.size} contas atrasadas`}</b><span>${esc([...atras.keys()].join(', '))}</span></div>
      <div class="op-n alerta">${brl(soma, 0)}</div>${ic('chev', 'chev')}</button>`);
  }
  const breve = agrupar(pend.filter(l => l.dc >= hj && diasEntre(h, pData(l.dc)) <= 5));
  if (breve.size) {
    const soma = [...breve.values()].reduce((a, b) => a + b, 0);
    av.push(`<button class="op" data-a="cx-ir" data-v="pendentes"><div class="op-ic terc">${ic('calendar')}</div>
      <div class="op-t"><b>Vence nos próximos 5 dias</b><span>${esc([...breve.keys()].join(', '))}</span></div>
      <div class="op-n">${brl(soma, 0)}</div>${ic('chev', 'chev')}</button>`);
  }
  return av;
}
function avisosInicio(h) {
  const av = avisosCaixa(h);
  return av.length ? `<div class="card flush"><div class="rot">${rotIc('alert', 'aviso')}<span class="rot-t">Avisos</span></div>${av.join('')}</div>` : '';
}

function avisoExemplo() {
  return `<div class="exemplo"><b>Exemplo.</b> Estes valores são de demonstração. Quando quiser usar com os seus, apague o exemplo e comece a cadastrar.
    <div><button class="btn out peq" data-a="apagar-exemplo">Apagar exemplo</button></div></div>`;
}

function telaBoasVindas() {
  return `${cabecalho('Início')}
    ${placar({ cab: 'Bem-vindo', data: fData(hoje()), valor: 'GERENCIA', palavra: true, rotulo: 'GerencIA', texto: 'Seu dinheiro, seus investimentos e quanto eles vão render.' })}
    <div class="comeco"><h2>Vamos começar</h2>
    <p>Comece pelo que entra e sai todo mês e pelos seus investimentos.</p>
    <div class="btns">
      <button class="btn pri" data-a="lanc-novo" data-v="receita">${ic('plus')}Cadastrar salário e gastos fixos</button>
      <button class="btn" data-a="novo-inv">${ic('wallet')}Cadastrar investimento</button>
      <button class="btn" data-a="ia" data-v="caixa">${ic('ia')}Ler fatura ou print com IA</button>
      <button class="btn" data-a="importar">${ic('upload')}Importar backup</button>
      <button class="link" data-a="carregar-exemplo">Ver com dados de exemplo</button>
    </div></div>`;
}

/* ------------------------------------------------------------------ Investimentos */
function listaFiltrada() {
  const u = S.ui;
  let l = porEscopo(u.filtro === 'meus' ? 'meu' : u.filtro === 'terc' ? 'terc' : 'tudo');
  if (u.filtro === 'terc' && u.pessoa) l = l.filter(i => dono(i) === u.pessoa);
  if (u.banco) l = l.filter(i => (i.banco || '-') === u.banco); // "-": Sem banco
  const q = semAcento(u.busca);
  if (q) l = l.filter(i => semAcento([i.nome, bancoDe(i.banco)?.nome, tipoDe(i.tipo).nome, dono(i), i.obs].join(' ')).includes(q));
  return l.map(i => ({ i, v: valorHoje(i) })).sort((a, b) => b.v - a.v);
}

function telaInvest() {
  const u = S.ui, d = S.d;
  if (!d.investimentos.length) {
    return `${cabecalho('Investimentos')}<div class="vazio">Nada cadastrado ainda.<br><br>
      <div class="btns" style="justify-content:center"><button class="btn pri" data-a="novo-inv">${ic('plus')}Cadastrar investimento</button>
      <button class="btn" data-a="ia" data-v="invest">${ic('ia')}Ler print com IA</button></div></div>`;
  }
  const nMeu = porEscopo('meu').length, nTerc = porEscopo('terc').length;
  let html = cabecalho('Investimentos', `<button class="icbtn" data-a="olho" aria-label="${S.oculto ? 'Mostrar' : 'Esconder'} valores">${ic(S.oculto ? 'eyeOff' : 'eye')}</button>`);
  // Buscar no alto, sempre à mostra, como no ResolvIA (digitar nele volta para a Carteira); no computador, a tecla / põe o cursor nele
  html += `<div class="busca inv-busca">${ic('search', 'ic-s')}<input id="q" type="search" data-ui="busca" value="${esc(u.busca)}" placeholder="Buscar por nome, banco ou pessoa" autocomplete="off" enterkeyhint="search" aria-label="Buscar investimentos">
    ${u.busca ? `<button class="icbtn mini" data-a="busca-limpar" aria-label="Limpar busca">${ic('x', 'ic-s')}</button>` : '<kbd aria-hidden="true">/</kbd>'}</div>`;
  html += `<div class="seg">${[['carteira', 'Carteira'], ['evolucao', 'Evolução'], ['divisao', 'Divisão']].map(([k, n]) =>
    `<button class="${u.invModo === k ? 'on' : ''}" data-a="inv-modo" data-v="${k}">${n}</button>`).join('')}</div>`;
  if (u.invModo !== 'carteira') return html + invGraficos();
  html += `<div class="inv-filtros"><div class="seg">
    <button class="${u.filtro === 'todos' ? 'on' : ''}" data-a="filtro" data-v="todos">Todos <small>${d.investimentos.length}</small></button>
    <button class="${u.filtro === 'meus' ? 'on' : ''}" data-a="filtro" data-v="meus">Meus <small>${nMeu}</small></button>
    <button class="${u.filtro === 'terc' ? 'on' : ''}" data-a="filtro" data-v="terc">Terceiros <small>${nTerc}</small></button></div></div>`;
  const ps = pessoas();
  if (u.filtro === 'terc' && ps.length > 1) {
    html += `<div class="chips rola"><button class="chip${!u.pessoa ? ' on' : ''}" data-a="pessoa-f" data-v="">Todas as pessoas</button>
      ${ps.map(p => `<button class="chip${u.pessoa === p ? ' on' : ''}" data-a="pessoa-f" data-v="${esc(p)}">${esc(p)}</button>`).join('')}</div>`;
  }
  const usados = [...new Set(d.investimentos.map(i => i.banco || ''))];
  if (usados.length > 1) {
    html += `<div class="chips rola"><button class="chip${!u.banco ? ' on' : ''}" data-a="banco-f" data-v="">Todos os bancos</button>
      ${usados.map(id => { const b = bancoDe(id); return `<button class="chip${u.banco === (id || '-') ? ' on' : ''}" data-a="banco-f" data-v="${esc(id || '-')}" style="--c:${corOk(b?.cor) || 'var(--c0)'}"><span class="bol"></span>${esc(b?.nome || 'Sem banco')}</button>`; }).join('')}</div>`;
  }
  if (u.filtro === 'terc' && nTerc && iaOn()) html += `<button class="btn out larga ia-saldos-btn" data-a="ia-saldos" data-v="${esc(u.pessoa || '')}">${ic('ia', 'ic-s')}Atualizar saldos${u.pessoa ? ' de ' + esc(u.pessoa) : ''} com IA</button>`;
  const l = listaFiltrada();
  const soma = l.reduce((s, x) => s + x.v, 0);
  const mes = l.reduce((s, x) => s + rendeMes(x.v, taxaAnual(x.i)), 0);
  html += `<div class="resumo-lista"><span>${plural(l.length, 'investimento', 'investimentos')} · rende ≈ ${brl(mes, 0)}/mês</span><b>${brl(soma, 0)}</b></div>`;
  // os bens do InventarIA aparecem como um cartão só de leitura (o valor muda lá), nos seus e em Todos
  const q = semAcento(u.busca || '');
  const bensCard = bensOn() && u.filtro !== 'terc' && !u.banco && !u.pessoa && (!q || ['bens da casa', 'inventaria'].some(t => t.includes(q)));
  html += l.length || bensCard ? `<div class="inv-lista">${l.map(x => cardInv(x.i, x.v)).join('')}${bensCard ? cardBensInventaria() : ''}</div>` : '<div class="vazio">Nenhum investimento com esse filtro.</div>';
  return html;
}
function cardBensInventaria() {
  const b = S.bens;
  return `<button class="inv inv-ro" data-a="bens" style="--c:var(--c4)" aria-label="Bens da casa, do InventarIA, só leitura">
    <div class="inv-top"><div class="inv-nome">Bens da casa</div><div class="inv-valor">${brl(b.hoje)}</div></div>
    <div class="inv-meta"><i></i>InventarIA · ${plural(b.n, 'item', 'itens')}</div>
    <div class="tags"><span class="tag">${ic('lock')}Só leitura</span><span class="tag meu">${ic('user')}Meu</span></div>
    <div class="inv-pe"><span>${b.perde_ano > 0 ? `perde ≈ ${brl(b.perde_ano / 12)} por mês` : b.perde_ano < 0 ? `valoriza ≈ ${brl(-b.perde_ano / 12)} por mês` : 'mantém o valor'}</span><span>o valor muda no InventarIA</span></div>
  </button>`;
}

function cardInv(i, v) {
  const h = hoje();
  const b = bancoDe(i.banco);
  const venc = pData(i.vencimento);
  const dv = pData(i.data_valor);
  let liq;
  if (i.tipo === 'bens' || i.tipo === 'dinheiro') liq = '';
  else if (venc && venc < h) liq = `<span class="tag alerta">${ic('alert')}Venceu ${fData(venc)}</span>`;
  else if (i.liquidez === 'diaria') liq = `<span class="tag">Liquidez diária</span>`;
  else liq = `<span class="tag">${ic('calendar')}${venc ? 'Vence ' + fData(venc) : 'No vencimento'}</span>`;
  const r = taxaAnual(i);
  const velho = dv && diasEntre(dv, h) > 60 && i.indexador !== 'parado';
  return `<button class="inv" data-a="inv" data-id="${i.id}" style="--c:${corOk(b?.cor) || 'var(--line-2)'}">
    <div class="inv-top"><div class="inv-nome">${esc(i.nome)}</div><div class="inv-valor">${brl(v)}</div></div>
    <div class="inv-meta"><i></i>${i.tipo === 'dinheiro' && !b ? 'Em espécie' : i.tipo === 'bens' ? `Bens · ${i.partes && i.partes.length > 1 ? plural(i.partes.length, 'categoria', 'categorias') : esc(nomeCatBem(i.partes && i.partes.length ? i.partes[0].categoria : i.categoria_bem))}` : `${esc(b?.nome || 'Sem banco')} · ${esc(tipoDe(i.tipo).nome)}`}</div>
    <div class="tags"><span class="tag taxa">${esc(rotuloTaxa(i))}</span>${tagDono(i)}${liq}</div>
    <div class="inv-pe"><span>${r > 0 ? `≈ ${brl(rendeMes(v, r))} por mês` : r < 0 ? `perde ≈ ${brl(perdeMesInv(i, v))} por mês` : 'Não rende'}</span>
      <span${velho ? ' style="color:var(--danger)"' : ''}>${dv ? 'valor de ' + fDataC(dv) + (dv.getFullYear() !== h.getFullYear() ? '/' + String(dv.getFullYear()).slice(2) : '') : ''}</span></div>
  </button>`;
}

/* ------------------------------------------------------------------ Invest: gráficos */
function invGraficos() {
  const u = S.ui;
  let html = '';
  const temTerc = porEscopo('terc').length > 0;
  if (temTerc) {
    html += `<div class="chips c3">${[['tudo', 'Tudo'], ['meu', 'Só o meu'], ['terc', 'De terceiros']].map(([k, n]) =>
      `<button class="chip${u.gEscopo === k ? ' on' : ''}" data-a="g" data-k="gEscopo" data-v="${k}">${n}</button>`).join('')}</div>`;
  } else if (u.gEscopo !== 'tudo') u.gEscopo = 'tudo';
  const lista = porEscopo(u.gEscopo).filter(i => !(u.gSemBens && i.tipo === 'bens'));
  if (!lista.length && !comBensG()) return html + '<div class="vazio">Nada nesse filtro.</div>' + chaveSemBens();
  return html + (u.invModo === 'divisao' ? grafComposicao(lista) : grafEvolucao(lista));
}

// os bens da casa (InventarIA) entram na Divisão e na Evolução em Tudo e em Só o meu; perdem valor por categoria
const comBensG = () => bensOn() && S.ui.gEscopo !== 'terc' && !S.ui.gSemBens;
// a chave só aparece quando há bens (do InventarIA ou do tipo Bens) no que está na tela
const temBensG = () => (bensOn() && S.ui.gEscopo !== 'terc') || porEscopo(S.ui.gEscopo).some(i => i.tipo === 'bens');
const chaveSemBens = (estilo = '') => temBensG() ? `<div class="linha-sw"${estilo}><div><b>Ocultar bens e imóveis</b><span>Só os investimentos, sem os bens do InventarIA e os do tipo Bens.</span></div>
      <button class="sw${S.ui.gSemBens ? ' on' : ''}" data-a="g" data-k="gSemBens" data-v="${S.ui.gSemBens ? '' : '1'}" role="switch" aria-checked="${!!S.ui.gSemBens}" aria-label="Ocultar bens e imóveis"></button></div>` : '';
const bensEm = m => (S.bens.categorias || []).reduce((a, c) => a + c.hoje * Math.pow(1 - (c.taxa || 0) / 100, m / 12), 0);

let CACHE = {};
function grafEvolucao(lista) {
  const u = S.ui;
  const ap = u.gEscopo === 'terc' ? 0 : aporteMensal();
  const pj = projetar(lista, u.gAnos, ap, u.gIR);
  CACHE.proj = pj;
  const fim = pj.pts[pj.pts.length - 1];
  const campo = u.gEscopo === 'meu' ? 'meu' : u.gEscopo === 'terc' ? 'terceiros' : 'total';
  CACHE.hist = S.d.historico.filter(h => h.d < iso(hoje())).map(h => ({ t: pData(h.d).getTime(), v: +h[campo] || 0 }));
  CACHE.bens = comBensG() ? pj.pts.map(p => ({ t: p.t, v: bensEm(p.m) })) : null;
  const b0 = CACHE.bens ? CACHE.bens[0].v : 0, bN = CACHE.bens ? CACHE.bens[CACHE.bens.length - 1].v : 0;
  const soBens = CACHE.soBens = !!CACHE.bens && !lista.length && !ap;
  const lb = lista.filter(i => i.tipo === 'bens'), bi0 = lb.reduce((a, i) => a + valorHoje(i), 0);
  const biN = lb.reduce((a, i) => a + (i.partes && i.partes.length ? partesHoje(i).reduce((x, p) => x + p.v * Math.pow(1 + p.r, u.gAnos), 0)
    : valorHoje(i) * Math.pow(1 + taxaAnual(i), u.gAnos)), 0);
  const rend = fim.valor - fim.aplicado + (bi0 - biN), perdaBens = (bi0 - biN) + (b0 - bN);
  if (soBens) CACHE.hist = [];
  const anosTxt = u.gAnos === 1 ? '1 ano' : `${u.gAnos} anos`;
  let html = `<div class="graf-card">
    <div class="stat-duo"><div><span>${soBens ? 'Bens hoje' : 'Hoje'}</span><b>${brl(pj.pts[0].valor + b0, 0)}</b>${CACHE.bens && !soBens ? `<small class="neutro">com ${brl(b0, 0)} em bens</small>` : ''}</div>
      <div><span>Em ${anosTxt}${u.gIR && !soBens ? ', líquido' : ''}</span><b>${brl(fim.valor + bN, 0)}</b><small${soBens ? ' class="neutro"' : ''}>${soBens ? `perdem ${brl(b0 - bN, 0)}` : `+${brl(rend, 0)} de rendimento${perdaBens > 0.5 ? ` · bens −${brl(perdaBens, 0)}` : perdaBens < -0.5 ? ` · bens +${brl(-perdaBens, 0)}` : ''}`}</small></div></div>
    <div class="chart" id="ch-evo" role="img" aria-label="Evolução do dinheiro: registrado até hoje e projetado para ${anosTxt}"></div>
    <div class="leg">${soBens ? '<span><i class="k" style="--kc:var(--c4)"></i>Bens</span>' : `
      ${CACHE.hist.length ? `<span><i class="k" style="--kc:var(--accent)"></i>Registrado</span>` : ''}
      <span><i class="k tr" style="--kc:var(--accent)"></i>Projetado</span>
      <span><i class="k" style="--kc:var(--c0)"></i>${ap ? 'Investido + aportes' : 'Valor investido'}</span>
      <span><i class="k" style="--kc:var(--c2)"></i>Em dinheiro de hoje</span>
      ${CACHE.bens ? '<span><i class="k" style="--kc:var(--c4)"></i>Bens</span>' : ''}`}
    </div></div>`;
  const outroAnos = !HZ_FIXOS.includes(u.gAnos);
  html += `<div class="ctrl"><div class="lbl">Horizonte</div><div class="chips c5">${HZ_FIXOS.map(a =>
    `<button class="chip${u.gAnos === a ? ' on' : ''}" data-a="g" data-k="gAnos" data-v="${a}">${a === 1 ? '1 ano' : a + ' anos'}</button>`).join('')}<button class="chip${outroAnos ? ' on' : ''}" data-a="g-anos-outro" aria-label="Outro horizonte">${outroAnos ? u.gAnos + ' anos' : 'Outro'}</button></div>
    ${u.gEscopo === 'terc' ? `<div class="lbl">Aporte por mês</div><p class="ajuda" style="margin:0">Aportes contam só nos seus investimentos.</p>` : aporteInfo(ap)}
    <div class="sep" style="margin:18px 0"></div>
    <div class="linha-sw"><div><b>Descontar imposto de renda</b><span>Tabela regressiva na renda fixa e 15% em ações. LCI, LCA e poupança são isentas.</span></div>
      <button class="sw${u.gIR ? ' on' : ''}" data-a="g" data-k="gIR" data-v="${u.gIR ? '' : '1'}" aria-label="Descontar IR"></button></div>
    ${chaveSemBens(' style="margin-top:14px"')}
  </div>
  <p class="nota">Com os índices de hoje (CDI ${pct(S.d.indices.cdi)}%, IPCA ${pct(S.d.indices.ipca)}%): rendimento médio de ${pct(pj.rMed * 100)}% a.a. "Em dinheiro de hoje" desconta a inflação.</p>
  <details class="card" style="margin-top:16px"><summary style="cursor:pointer;font-weight:600">Ver tabela por ano</summary>
  <div class="tabela-rola"><table class="tabela"><thead><tr><th>Quando</th>${soBens ? '' : '<th class="n">Projetado</th><th class="n">Rendeu</th><th class="n">Em dinheiro de hoje</th>'}${CACHE.bens ? '<th class="n">Bens</th>' : ''}</tr></thead><tbody>
  ${Array.from({ length: u.gAnos }, (_, k) => pj.pts[(k + 1) * 12]).map(p =>
    `<tr><td>${fMesAno(new Date(p.t))}</td>${soBens ? '' : `<td class="n">${brl(p.valor, 0)}</td><td class="n">${brl(p.valor - p.aplicado, 0)}</td><td class="n">${brl(p.real, 0)}</td>`}${CACHE.bens ? `<td class="n">${brl(bensEm(p.m), 0)}</td>` : ''}</tr>`).join('')}
  </tbody></table></div></details>`;
  return html;
}

const HZ_FIXOS = [1, 2, 5, 10], HZ_MAX = 50;
function abrirHorizonte() {
  const pre = [3, 15, 20, 25, 30, 40];
  abrirFolha(() => ({
    titulo: 'Horizonte da projeção',
    corpo: `<p class="ajuda" style="margin:0 0 12px">De 1 a ${HZ_MAX} anos.</p>
      <div class="chips c3">${pre.map(a => `<button class="chip${S.ui.gAnos === a ? ' on' : ''}" data-a="g-anos-pre" data-v="${a}">${a} anos</button>`).join('')}</div>
      <div class="campo"><label class="lbl" for="hz-anos">Anos</label><input id="hz-anos" class="inp" type="number" inputmode="numeric" min="1" max="${HZ_MAX}" step="1" value="${HZ_FIXOS.includes(S.ui.gAnos) ? 20 : S.ui.gAnos}"></div>`,
    pe: `<button class="btn pri larga" data-a="g-anos-ok">Ver a projeção</button>`,
  }));
}
function aplicarHorizonte(v) {
  const a = Math.round(+v);
  if (!Number.isFinite(a) || a < 1 || a > HZ_MAX) return toast(`Escolha de 1 a ${HZ_MAX} anos.`);
  S.ui.gAnos = a; salvarUI(); fecharFolha(); render();
}

// O aporte por mês não se digita aqui: vem das contas a pagar do tipo Aporte (o compromisso de aplicar).
function aporteInfo(ap) {
  const fx = aportesFixos();
  if (!fx.length) {
    return `<div class="lbl">Aporte por mês nos seus investimentos</div>
      <p class="ajuda" style="margin:0 0 10px">Nenhum. Cadastre uma conta a pagar do tipo <b>Aporte</b>, todo mês.</p>
      <div class="btns-2"><button class="btn out" data-a="aporte-novo">${ic('plus', 'ic-s')}Cadastrar aporte</button></div>`;
  }
  const r = fx[0], conta = r.conta ? contaDe(r.conta) : null;
  const quando = fx.length > 1 ? `${fx.length} aportes fixos nas contas a pagar` : `${r.freq === 'anual' ? `todo ano em ${MESES_LONGOS[+String(r.inicio).slice(5, 7) - 1]}, dividido por 12` : `todo dia ${r.dia}`}${conta ? `, saindo de ${esc(nomeConta(conta))}` : ''}`;
  return `<div class="lbl">Aporte por mês nos seus investimentos</div>
    <div class="aporte-info"><b>${brl(ap)}</b><span>${quando[0].toUpperCase() + quando.slice(1)}.</span></div>
    <div class="btns-2" style="margin-top:10px"><button class="btn" data-a="aporte-ajustar">${ic('edit', 'ic-s')}${fx.length > 1 ? 'Ver os aportes' : 'Mudar o aporte'}</button>
      <button class="btn" data-a="aporte-novo">${ic('plus', 'ic-s')}Outro aporte</button></div>`;
}

function niceStep(x) {
  const p = Math.pow(10, Math.floor(Math.log10(x)));
  const f = x / p;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
}

function desenharEvolucao() {
  const el = $('#ch-evo');
  if (!el || !CACHE.proj) return;
  const W = Math.max(280, el.clientWidth), H = 236, pl = 50, pr = 10, pt = 22, pb = 26;
  const proj = CACHE.proj.pts;
  const anos = S.ui.gAnos;
  const t0 = proj[0].t;
  let hist = CACHE.hist.filter(p => p.t >= t0 - anos * 365.25 * 86400000);
  if (hist.length > 140) { const passo = Math.ceil(hist.length / 140); hist = hist.filter((_, k) => k % passo === 0 || k === hist.length - 1); }
  const histC = hist.length ? [...hist, { t: t0, v: proj[0].valor }] : [];
  const xMin = histC.length ? histC[0].t : t0, xMax = proj[proj.length - 1].t;
  const soBens = !!CACHE.soBens;
  const vals = soBens ? CACHE.bens.map(p => p.v) : [...proj.flatMap(p => [p.valor, p.aplicado, p.real]), ...histC.map(p => p.v), ...(CACHE.bens || []).map(p => p.v)];
  let lo = Math.min(...vals), hi = Math.max(...vals);
  if (hi - lo < 1) { hi += 1; lo = Math.max(0, lo - 1); }
  const step = niceStep((hi - lo) / 4);
  const yMin = Math.max(0, Math.floor(lo / step) * step), yMax = Math.ceil(hi / step) * step;
  const X = t => pl + (t - xMin) / ((xMax - xMin) || 1) * (W - pl - pr);
  const Y = v => pt + (1 - (v - yMin) / ((yMax - yMin) || 1)) * (H - pt - pb);
  const linha = (pts, f) => pts.map((p, k) => `${k ? 'L' : 'M'}${X(p.t).toFixed(1)},${Y(f(p)).toFixed(1)}`).join('');

  let g = '';
  for (let v = yMin; v <= yMax + step / 2; v += step) {
    const y = Y(v).toFixed(1);
    g += `<line class="grid" x1="${pl}" x2="${W - pr}" y1="${y}" y2="${y}"/><text x="${pl - 8}" y="${(+y + 4).toFixed(1)}" text-anchor="end">${compacto(v)}</text>`;
  }
  // eixo x
  const marcas = [];
  const span = (xMax - xMin) / (365.25 * 86400000);
  if (span <= 2.5) {
    const passoM = span <= 1.3 ? 3 : 6;
    let d = new Date(xMin); d.setDate(1); d.setMonth(Math.ceil(d.getMonth() / passoM) * passoM);
    while (d.getTime() <= xMax) { if (d.getTime() >= xMin) marcas.push({ t: d.getTime(), txt: fMesAno(d) }); d = addMeses(d, passoM); }
  } else {
    const passoA = span <= 7 ? 1 : Math.ceil(span / 6);
    for (let a = new Date(xMin).getFullYear() + 1; a <= new Date(xMax).getFullYear(); a += passoA) marcas.push({ t: new Date(a, 0, 1).getTime(), txt: String(a) });
  }
  for (const m of marcas) {
    const x = X(m.t);
    if (x < pl + 14 || x > W - 18) continue;
    g += `<text x="${x.toFixed(1)}" y="${H - 6}" text-anchor="middle">${m.txt}</text>`;
  }
  const xh = X(t0).toFixed(1);
  if (histC.length) g += `<line class="hoje" x1="${xh}" x2="${xh}" y1="${pt - 8}" y2="${H - pb}"/><text x="${xh}" y="${pt - 11}" text-anchor="middle">hoje</text>`;
  // área do rendimento (entre aplicado e projetado)
  if (!soBens) {
    const area = linha(proj, p => p.valor) + proj.slice().reverse().map(p => `L${X(p.t).toFixed(1)},${Y(p.aplicado).toFixed(1)}`).join('') + 'Z';
    g += `<path class="a-proj" d="${area}"/>`;
    g += `<path class="l-apl" d="${linha(proj, p => p.aplicado)}"/>`;
    g += `<path class="l-real" d="${linha(proj, p => p.real)}"/>`;
    if (histC.length) g += `<path class="l-hist" d="${linha(histC, p => p.v)}"/>`;
    g += `<path class="l-proj" d="${linha(proj, p => p.valor)}"/>`;
  }
  if (CACHE.bens) g += `<path class="l-bens${soBens ? ' so' : ''}" d="${linha(CACHE.bens, p => p.v)}"/>`;
  const ult = proj[proj.length - 1], bU = CACHE.bens ? CACHE.bens[CACHE.bens.length - 1] : null;
  if (soBens) g += `<circle class="pt" cx="${X(bU.t).toFixed(1)}" cy="${Y(bU.v).toFixed(1)}" r="4.5" fill="var(--c4)"/><circle class="pt" cx="${X(CACHE.bens[0].t).toFixed(1)}" cy="${Y(CACHE.bens[0].v).toFixed(1)}" r="4.5" fill="var(--c4)"/>`;
  else {
    g += `<circle class="pt" cx="${X(ult.t).toFixed(1)}" cy="${Y(ult.valor).toFixed(1)}" r="4.5" fill="var(--accent)"/>`;
    g += `<circle class="pt" cx="${xh}" cy="${Y(proj[0].valor).toFixed(1)}" r="4.5" fill="var(--accent)"/>`;
  }
  g += `<g id="cross" style="display:none"><line class="cross" y1="${pt}" y2="${H - pb}"/></g>`;

  el.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${g}</svg><div class="tip" style="display:none"></div>`;

  // camada de toque: cruz + dica
  const quadros = [
    ...hist.map(p => ({ t: p.t, hist: p.v })),
    ...proj.map(p => ({ t: p.t, p })),
  ].sort((a, b) => a.t - b.t);
  const svg = $('svg', el), tip = $('.tip', el), cross = $('#cross', el);
  const mostrar = ev => {
    const r = svg.getBoundingClientRect();
    const x = (ev.clientX - r.left) * (W / (r.width || W));
    const t = xMin + (x - pl) / (W - pl - pr) * (xMax - xMin);
    let q = quadros[0];
    for (const c of quadros) if (Math.abs(c.t - t) < Math.abs(q.t - t)) q = c;
    const qx = X(q.t);
    cross.style.display = '';
    $('line', cross).setAttribute('x1', qx); $('line', cross).setAttribute('x2', qx);
    $$('circle.mk', cross).forEach(c => c.remove());
    const bq = q.p && CACHE.bens ? bensEm(q.p.m) : null;
    const pontos = q.p ? [...(soBens ? [] : [[q.p.valor, 'var(--accent)'], [q.p.aplicado, 'var(--c0)'], [q.p.real, 'var(--c2)']]), ...(bq != null ? [[bq, 'var(--c4)']] : [])] : [[q.hist, 'var(--accent)']];
    for (const [v, c] of pontos) {
      const ci = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      ci.setAttribute('class', 'pt mk'); ci.setAttribute('cx', qx); ci.setAttribute('cy', Y(v)); ci.setAttribute('r', 4.5); ci.setAttribute('fill', c);
      cross.appendChild(ci);
    }
    tip.textContent = '';
    const dt = new Date(q.t);
    const cab = document.createElement('div'); cab.className = 't-d';
    cab.textContent = q.p ? (q.p.m === 0 ? 'Hoje' : `${fMesAno(dt)} · projetado`) : `${fData(dt)} · registrado`;
    tip.appendChild(cab);
    const linhas = q.p
      ? [...(soBens ? [] : [[q.p.valor, 'Projetado', 'var(--accent)', true], [q.p.aplicado, 'Valor investido', 'var(--c0)'], [q.p.real, 'Em dinheiro de hoje', 'var(--c2)']]), ...(bq != null ? [[bq, 'Bens', 'var(--c4)']] : [])]
      : [[q.hist, 'Registrado', 'var(--accent)']];
    for (const [v, n, c, tr] of linhas) {
      const row = document.createElement('div'); row.className = 't-r';
      const k = document.createElement('i'); k.className = 'k' + (tr ? ' tr' : ''); k.style.setProperty('--kc', c);
      const b = document.createElement('b'); b.textContent = brl(v, 0);
      const s = document.createElement('span'); s.textContent = n;
      row.append(k, b, s); tip.appendChild(row);
    }
    tip.style.display = '';
    const tw = tip.offsetWidth;
    tip.style.left = Math.min(Math.max(0, qx > W / 2 ? qx - tw - 12 : qx + 12), W - tw) + 'px';
  };
  const esconder = () => { tip.style.display = 'none'; cross.style.display = 'none'; };
  el.onpointerdown = mostrar;
  el.onpointermove = mostrar;
  el.onpointerleave = esconder;
}

function grupos(lista, agrup) {
  const ps = pessoas();
  const m = new Map();
  for (const i of lista) {
    let k, nome, cor;
    if (agrup === 'banco') { const b = bancoDe(i.banco); k = i.banco || '-'; nome = b?.nome || 'Sem banco'; cor = corOk(b?.cor) || 'var(--c0)'; }
    else if (agrup === 'dono') { k = dono(i); nome = k === 'Meu' ? 'Seu' : k; cor = k === 'Meu' ? 'var(--accent)' : `var(--c${(ps.indexOf(k) % 7) + 2})`; }
    else if (agrup === 'tipo') { const ti = TIPOS.findIndex(t => t.id === i.tipo); k = i.tipo || 'outro'; nome = tipoDe(i.tipo).nome; cor = ti >= 0 && ti < 8 ? `var(--c${ti + 1})` : 'var(--c0)'; }
    else { k = i.liquidez === 'diaria' ? 'diaria' : 'venc'; nome = k === 'diaria' ? 'Liquidez diária' : 'Só no vencimento'; cor = k === 'diaria' ? 'var(--c1)' : 'var(--c2)'; }
    const g = m.get(k) || { k, nome, cor, v: 0, n: 0, mes: 0, perde: 0 };
    const v = valorHoje(i);
    g.v += v; g.n++; g.mes += rendeMes(v, taxaAnual(i)); g.perde += perdeMesInv(i, v);
    m.set(k, g);
  }
  return [...m.values()].sort((a, b) => b.v - a.v);
}

function grafComposicao(lista) {
  const u = S.ui;
  const gs = grupos(lista, u.gAgrup);
  if (comBensG()) { gs.push({ k: '_bens', nome: 'Bens da casa', cor: 'var(--c4)', v: S.bens.hoje, n: S.bens.n, mes: 0, bens: true }); gs.sort((a, b) => b.v - a.v); }
  const total = gs.reduce((s, g) => s + g.v, 0) || 1;
  const sel = gs.find(g => g.k === u.gSel);
  const opts = [['banco', 'Banco'], ['dono', 'De quem'], ['tipo', 'Tipo'], ['liq', 'Liquidez']];
  let html = `<div class="chips c4">${opts.map(([k, n]) => `<button class="chip${u.gAgrup === k ? ' on' : ''}" data-a="g" data-k="gAgrup" data-v="${k}">${n}</button>`).join('')}</div>`;
  html += `<div class="graf-card" style="padding:18px 18px 8px">
    <div class="stat-duo" style="margin:0 0 10px"><div><span>Total</span><b>${brl(total, 0)}</b></div><div><span>Rende por mês</span><b>${brl(gs.reduce((s, g) => s + g.mes, 0), 0)}</b></div></div>
    <div class="pilha-cap">${sel ? `<b>${esc(sel.nome)}</b> · ${brl(sel.v, 0)} · ${pct1(sel.v / total * 100)}%` : 'Toque numa parte para ver o valor'}</div>
    <div class="pilha" role="img" aria-label="Divisão do dinheiro por ${opts.find(o => o[0] === u.gAgrup)[1].toLowerCase()}">
      ${gs.map(g => `<i data-a="g" data-k="gSel" data-v="${esc(g.k)}" style="--c:${g.cor};flex:${g.v / total} 1 0"></i>`).join('')}</div>
    <div style="margin-top:8px">${gs.map(g => `<div class="comp${u.gSel === g.k ? ' on' : ''}" data-a="g" data-k="gSel" data-v="${esc(g.k)}" style="--c:${g.cor}">
      <span class="sq"></span><div class="nm"><b>${esc(g.nome)}</b><span class="sub">${g.bens ? `${plural(g.n, 'item', 'itens')} · ${varAno(S.bens.perde_ano)}` : `${plural(g.n, 'investimento', 'investimentos')} · ${g.perde > g.mes ? `perde ≈ ${brl(g.perde - g.mes, 0)}/mês` : `≈ ${brl(g.mes, 0)}/mês`}`}</span></div>
      <div class="vl">${brl(g.v, 0)}<small>${pct1(g.v / total * 100)}%</small></div>
      <div class="barra"><i style="width:${(g.v / gs[0].v * 100).toFixed(1)}%"></i></div></div>`).join('')}</div>
  </div>`;
  return html + (temBensG() ? `<div class="ctrl">${chaveSemBens()}</div>` : '');
}

/* ------------------------------------------------------------------ caixa: base */
const CATEGORIAS_PADRAO = [
  ['c-moradia', 'Moradia', 'despesa', '#56AEFF'], ['c-mercado', 'Mercado', 'despesa', '#4CD3A5'],
  ['c-restaurantes', 'Restaurantes', 'despesa', '#FFA23A'], ['c-transporte', 'Transporte', 'despesa', '#B79BFF'],
  ['c-contas', 'Contas da casa', 'despesa', '#F2C14E'], ['c-saude', 'Saúde', 'despesa', '#FF77A8'],
  ['c-educacao', 'Educação', 'despesa', '#FF8A65'], ['c-lazer', 'Lazer', 'despesa', '#E04B8A'],
  ['c-assinaturas', 'Assinaturas', 'despesa', '#FF5A4E'], ['c-compras', 'Compras', 'despesa', '#B8B0B0'],
  ['c-pets', 'Pets', 'despesa', '#4CD3A5'], ['c-impostos', 'Impostos e taxas', 'despesa', '#FFA23A'],
  ['c-outros-gastos', 'Outros gastos', 'despesa', '#B8B0B0'], ['c-investimentos', 'Investimentos', 'despesa', '#2A78D6'],
  ['c-salario', 'Salário', 'receita', '#4CD3A5'], ['c-freelance', 'Freelance', 'receita', '#56AEFF'],
  ['c-rendimentos', 'Rendimentos', 'receita', '#B79BFF'], ['c-vendas', 'Vendas', 'receita', '#FFA23A'],
  ['c-reembolso', 'Reembolso', 'receita', '#F2C14E'], ['c-outros-receb', 'Outros recebimentos', 'receita', '#B8B0B0'],
].map(([id, nome, tipo, cor]) => ({ id, nome, tipo, cor }));
const MESES_LONGOS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
const DIAS_SEMANA = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'];

const ymDe = s => String(s || '').slice(0, 7);
const ymHoje = () => iso(hoje()).slice(0, 7);
function addYm(ym, n) { const [a, m] = ym.split('-').map(Number); return iso(new Date(a, m - 1 + n, 1)).slice(0, 7); }
function nomeMes(ym, curto) { const [a, m] = ym.split('-').map(Number); return curto ? `${MESES[m - 1]}/${String(a).slice(2)}` : `${MESES_LONGOS[m - 1]} de ${a}`; }
const maiuscula = t => t.charAt(0).toUpperCase() + t.slice(1);
function dataNoMes(ym, dia) {
  const [a, m] = ym.split('-').map(Number);
  const ult = new Date(a, m, 0).getDate();
  return `${ym}-${String(Math.min(Math.max(1, +dia || 1), ult)).padStart(2, '0')}`;
}
const somaMeses = (data, n) => dataNoMes(addYm(ymDe(data), n), +String(data).slice(8, 10));

// memória por versão dos dados (recalcula só quando S.d muda)
let MEMO = { d: null };
function memo(k, fn) { if (MEMO.d !== S.d) MEMO = { d: S.d }; if (!(k in MEMO)) MEMO[k] = fn(); return MEMO[k]; }

function contas() {
  return memo('contas', () => {
    const out = [];
    for (const b of S.d.bancos) for (const c of b.contas || []) out.push(Object.assign({}, c, { banco: b.id, bancoNome: b.nome, cor: b.cor }));
    return out;
  });
}
const contaDe = id => contas().find(c => c.id === id);
const nomeConta = c => c ? c.bancoNome + (c.pessoa ? ' · ' + c.pessoa : '') : 'Sem conta';
const ehRec = l => l.tipo === 'receita';
const sinal = l => ehRec(l) ? 1 : -1;
const catDe = id => S.d.categorias.find(c => c.id === id);
const corCat = l => l.ajuste ? '#B8B0B0' : (corOk(catDe(l.categoria)?.cor) || '#B8B0B0');

function dataCaixa(l) {
  if (l.vinculo && l.tipo !== 'receita') { const dv = dataVinculo(l); if (dv) return dv; }
  if (!l.cartao) return l.data;
  const c = contaDe(l.conta);
  const d = pData(l.data);
  if (!c || !c.cartao || !d) return l.data;
  const fech = +c.fechamento || 1, venc = +c.vencimento || 10;
  let m = d.getMonth() + (d.getDate() >= fech ? 1 : 0);
  if (venc <= fech) m += 1;
  return dataNoMes(iso(new Date(d.getFullYear(), m, 1)).slice(0, 7), venc);
}

function ocorrencia(r, ym) {
  const o = Object.assign({}, r, { id: `v:${r.id}:${ym}`, virtual: true, recorrencia: r.id, competencia: ym, data: dataNoMes(ym, r.dia), pago: false });
  delete o.inicio; delete o.fim; delete o.dia;
  o.dc = dataCaixa(o);
  return o;
}
// A recorrência acontece na competência ym? Mensal: todo mês; anual: no mês em que começou, todo ano.
function ativaEm(r, ym) {
  const ini = r.inicio || '9999-99';
  return ini <= ym && !(r.fim && r.fim < ym) && (r.freq !== 'anual' || ini.slice(5) === ym.slice(5));
}
function proximaYm(r) {
  let ym = addYm(ymHoje(), 1) < (r.inicio || '') ? r.inicio : addYm(ymHoje(), 1);
  for (let k = 0; k < 12 && !ativaEm(r, ym); k++) ym = addYm(ym, 1);
  return ym;
}
// Aporte: um tipo de conta a pagar, o compromisso de aplicar nos seus investimentos. Os aportes fixos
// (todo mês, ou todo ano dividido por 12) somam o aporte por mês da projeção na aba Invest.
const recPorId = () => memo('recId', () => new Map(S.d.recorrencias.map(r => [r.id, r])));
const ehAporte = l => !!(l.aporte || (l.recorrencia && recPorId().get(l.recorrencia)?.aporte));
const aportesFixos = () => S.d.recorrencias.filter(r => r.aporte && (!r.fim || r.fim >= ymHoje()));
const aporteMensal = () => round2(aportesFixos().reduce((s, r) => s + (+r.valor || 0) / (r.freq === 'anual' ? 12 : 1), 0));
function novoAporte() {
  abrirLancamento(null, { tipo: 'despesa', aporte: true, categoria: 'c-investimentos', repete: 'mensal', cartao: false });
}
/* --------- créditos e descontos do recebimento: o bruto entra, impostos e plano descontados na fonte saem no mesmo dia */
const temPartes = l => Array.isArray(l.partes) && l.partes.length > 0;
const temDescontos = l => ehRec(l) && Array.isArray(l.descontos) && l.descontos.length > 0;
const somaPartes = partes => round2((partes || []).reduce((s, p) => s + (+p.valor || 0), 0));
function parteDe(l, id) { return id && temPartes(l) ? l.partes.find(p => p.id === id) : null; }
const baseDesc = (l, x) => { const p = parteDe(l, x.base); return p ? (+p.valor || 0) : (+l.valor || 0); };
const valorDesc = (l, x) => round2(x.modo === 'pct' ? baseDesc(l, x) * (+x.valor || 0) / 100 : (+x.valor || 0));
function descontosDe(l) {
  if (!temDescontos(l) || l.desconto) return [];
  const out = [];
  for (const x of l.descontos) {
    const v = valorDesc(l, x);
    if (!(v > 0)) continue;
    out.push({ id: `d:${l.id}:${x.id}`, pai: l.id, paiDesc: l.descricao, desconto: true, tipo: 'despesa', descricao: x.descricao || 'Desconto',
      valor: v, categoria: x.categoria || '', conta: l.conta || '', cartao: false, data: l.data, dc: l.dc || l.data, pago: !!l.pago,
      competencia: l.competencia || null, regra: x, baseNome: parteDe(l, x.base)?.descricao || '' });
  }
  return out;
}
const totalDescontos = l => round2(descontosDe(l).reduce((s, d) => s + d.valor, 0));
const liquidoDe = l => round2((+l.valor || 0) - totalDescontos(l));
const regraDesc = d => d.regra.modo === 'pct' ? `${pct(+d.regra.valor)}% ${d.baseNome ? 'de ' + d.baseNome : 'do bruto'}` : 'valor fixo';
const NA_FONTE = 'já pago, na fonte';
function comDescontos(lista) { const out = []; for (const l of lista) { out.push(l); for (const d of descontosDe(l)) out.push(d); } return out; }

/* --------- despesa ligada a um recebimento fixo (plano de saúde descontado do salário): a baixa dela vem com a do recebimento */
const recMat = () => memo('recMat', () => { const m = new Map(); for (const l of S.d.lancamentos) if (l.recorrencia && l.competencia) m.set(l.recorrencia + '|' + l.competencia, l); return m; });
const compDe = l => l.competencia || ymDe(l.data);
function dataVinculo(l) {
  const r = recPorId().get(l.vinculo);
  if (!r) return null;
  const ym = compDe(l), m = recMat().get(r.id + '|' + ym);
  return m && !m.pulado ? m.data : (ativaEm(r, ym) ? dataNoMes(ym, r.dia) : null);
}
const nomeVinculo = l => recPorId().get(l.vinculo)?.descricao || 'recebimento';
const recebimentosFixos = () => S.d.recorrencias.filter(r => r.tipo === 'receita' && (!r.fim || r.fim >= ymHoje()));
// quando um recebimento fixo muda de situação, as despesas ligadas a ele naquele mês acompanham (mesma data e conta)
function baixaVinculados(d, rec) {
  if (!rec || !rec.recorrencia || rec.tipo !== 'receita') return;
  const ym = rec.competencia || ymDe(rec.data);
  for (const r of d.recorrencias) {
    if (r.tipo === 'receita' || r.vinculo !== rec.recorrencia || !ativaEm(r, ym)) continue;
    const x = d.lancamentos.find(l => l.recorrencia === r.id && l.competencia === ym);
    if (x) { if (!x.pulado) Object.assign(x, { pago: !!rec.pago, data: rec.data, conta: rec.conta || x.conta, cartao: false }); }
    else if (rec.pago) d.lancamentos.push(materializar(Object.assign({}, r, { data: rec.data, recorrencia: r.id, competencia: ym, pago: true, conta: rec.conta || r.conta, cartao: false })));
  }
  for (const x of d.lancamentos) {
    if (x.tipo !== 'receita' && !x.recorrencia && x.vinculo === rec.recorrencia && ymDe(x.data) === ym) Object.assign(x, { pago: !!rec.pago, data: rec.data, conta: rec.conta || x.conta, cartao: false });
  }
}

function feitos() { return memo('feitos', () => new Set(S.d.lancamentos.filter(l => l.recorrencia).map(l => l.recorrencia + '|' + l.competencia))); }

// Tudo o que entra ou sai do caixa entre dois meses (pela data do caixa: no cartão, o vencimento da fatura)
function lancamentosEntre(ymIni, ymFim) {
  return memo(`e:${ymIni}:${ymFim}`, () => {
    const out = [];
    for (const l of S.d.lancamentos) {
      if (l.pulado) continue;
      const dc = dataCaixa(l), ym = ymDe(dc);
      if (ym >= ymIni && ym <= ymFim) out.push(Object.assign({ dc }, l));
    }
    const f = feitos();
    for (let ym = addYm(ymIni, -2); ym <= ymFim; ym = addYm(ym, 1)) {
      for (const r of S.d.recorrencias) {
        if (!ativaEm(r, ym) || f.has(r.id + '|' + ym)) continue;
        const o = ocorrencia(r, ym), y = ymDe(o.dc);
        if (y >= ymIni && y <= ymFim) out.push(o);
      }
    }
    return comDescontos(out).sort((a, b) => a.dc < b.dc ? -1 : a.dc > b.dc ? 1 : (ehRec(b) - ehRec(a)));
  });
}
// Lançamentos pela data da compra (para as categorias)
function lancamentosCompetencia(ym) {
  return memo('c:' + ym, () => {
    const out = S.d.lancamentos.filter(l => !l.pulado && ymDe(l.data) === ym).map(l => Object.assign({ dc: dataCaixa(l) }, l));
    const f = feitos();
    for (const r of S.d.recorrencias) {
      if (!ativaEm(r, ym) || f.has(r.id + '|' + ym)) continue;
      out.push(ocorrencia(r, ym));
    }
    return comDescontos(out);
  });
}
function acharLanc(id) {
  if (String(id).startsWith('d:')) return acharLanc(String(id).slice(2, String(id).lastIndexOf(':')));
  if (String(id).startsWith('v:')) {
    const [, rid, ym] = id.split(':');
    const r = S.d.recorrencias.find(x => x.id === rid);
    return r ? ocorrencia(r, ym) : null;
  }
  const l = S.d.lancamentos.find(x => x.id === id);
  return l ? Object.assign({ dc: dataCaixa(l) }, l) : null;
}
function materializar(l, extra) {
  const o = { id: uid(), tipo: l.tipo, descricao: l.descricao, valor: +l.valor || 0, categoria: l.categoria || '', conta: l.conta || '',
    cartao: !!l.cartao, data: l.data, pago: !!l.pago, obs: l.obs || '', recorrencia: l.recorrencia || null, competencia: l.competencia || null };
  if (l.aporte) o.aporte = true;
  if (l.vinculo) o.vinculo = l.vinculo;
  if (temPartes(l)) o.partes = clone(l.partes);
  if (Array.isArray(l.descontos) && l.descontos.length) o.descontos = clone(l.descontos);
  return Object.assign(o, extra || {});
}

function saldoCaixa(ate = iso(hoje())) {
  return memo('s:' + ate, () => {
    let s = 0;
    for (const l of S.d.lancamentos) if (!l.pulado && l.pago && dataCaixa(l) <= ate) s += sinal(l) * (+l.valor || 0) - totalDescontos(l);
    return s;
  });
}
function resumoMes(ym) {
  let entrou = 0, saiu = 0, aEntrar = 0, aSair = 0;
  for (const l of lancamentosEntre(ym, ym)) {
    if (l.ajuste) continue;
    const v = +l.valor || 0;
    if (ehRec(l)) { if (l.pago) entrou += v; else aEntrar += v; } else if (l.pago) saiu += v; else aSair += v;
  }
  return { entrou, saiu, aEntrar, aSair, sobra: entrou - saiu, previsto: entrou + aEntrar - saiu - aSair };
}
function saldoPrevisto(ym) {
  let s = saldoCaixa(dataNoMes(ym, 31));
  const ini = addYm(ymHoje(), -2);
  if (ym < ini) return s;
  for (const l of lancamentosEntre(ini, ym)) if (!l.pago) s += sinal(l) * (+l.valor || 0);
  return s;
}
function faturasDe(lista) {
  const m = new Map();
  for (const l of lista) {
    if (!l.cartao || !contaDe(l.conta)?.cartao) continue;
    const k = l.conta + '|' + l.dc;
    const f = m.get(k) || { k, conta: l.conta, dc: l.dc, itens: [], total: 0, pago: true };
    f.itens.push(l);
    f.total += (ehRec(l) ? -1 : 1) * (+l.valor || 0);
    if (!l.pago) f.pago = false;
    m.set(k, f);
  }
  return [...m.values()];
}
function temCaixa() { return S.d.lancamentos.length > 0 || S.d.recorrencias.length > 0; }

/* ------------------------------------------------------------------ caixa: exemplo */
function contasExemplo(bancos) {
  const c = (id, pessoa, cartao, fechamento, vencimento) => ({ id, pessoa, cartao, fechamento, vencimento });
  const por = {
    'b-lua': [c('k-lua-ana', 'Ana', true, 3, 10), c('k-lua-beto', 'Beto', true, 28, 5)],
    'b-sol': [c('k-sol-ana', 'Ana', true, 25, 2)],
    'b-coral': [c('k-coral-ana', 'Ana', false, 1, 10)],
    'b-norte': [c('k-norte-ana', 'Ana', false, 1, 10)],
    'b-azul': [c('k-azul-mae', 'Mãe', false, 1, 10)],
    'b-verde': [c('k-verde-beto', 'Beto', false, 1, 10)],
  };
  for (const b of bancos) b.contas = por[b.id] || [c(b.id + '-c1', '', false, 1, 10)];
}

function caixaExemplo() {
  let semente = 11;
  const rnd = () => (semente = (semente * 16807) % 2147483647) / 2147483647;
  const entre = (a, b) => Math.round((a + rnd() * (b - a)) * 100) / 100;
  const hj = iso(hoje()), ymAtual = ymHoje();
  const inicio = addYm(ymAtual, -6);
  const lanc = [], rec = [];
  const L = o => lanc.push(Object.assign({ id: uid(), obs: '', conta: '', cartao: false, recorrencia: null, competencia: null, parcela: null, grupo: null }, o));
  const R = o => { rec.push(Object.assign({ obs: '', fim: null, inicio, cartao: false }, o)); return o.id; };

  L({ tipo: 'receita', descricao: 'Ajuste de saldo', valor: 6200, data: inicio + '-01', pago: true, ajuste: true, categoria: '' });
  const fixos = [
    R({ id: 'r-sal', tipo: 'receita', descricao: 'Salário', valor: 11800, dia: 5, categoria: 'c-salario', conta: 'k-coral-ana',
      descontos: [{ id: 'd-inss', descricao: 'INSS', modo: 'pct', valor: 7, base: '', categoria: 'c-impostos' },
        { id: 'd-taxa', descricao: 'Taxa administrativa', modo: 'pct', valor: 4.5, base: '', categoria: 'c-impostos' }] }),
    R({ id: 'r-plano', tipo: 'despesa', descricao: 'Plano de saúde', valor: 698.46, dia: 5, categoria: 'c-saude', conta: 'k-coral-ana', vinculo: 'r-sal' }),
    R({ id: 'r-alug', tipo: 'despesa', descricao: 'Aluguel', valor: 2300, dia: 10, categoria: 'c-moradia', conta: 'k-coral-ana' }),
    R({ id: 'r-cond', tipo: 'despesa', descricao: 'Condomínio', valor: 680, dia: 10, categoria: 'c-moradia', conta: 'k-coral-ana' }),
    R({ id: 'r-luz', tipo: 'despesa', descricao: 'Conta de luz', valor: 260, dia: 21, categoria: 'c-contas', conta: 'k-coral-ana' }),
    R({ id: 'r-net', tipo: 'despesa', descricao: 'Internet', valor: 119.9, dia: 18, categoria: 'c-contas', conta: 'k-coral-ana' }),
    R({ id: 'r-ingles', tipo: 'despesa', descricao: 'Inglês', valor: 420, dia: 8, categoria: 'c-educacao', conta: 'k-lua-beto', cartao: true }),
    R({ id: 'r-acad', tipo: 'despesa', descricao: 'Academia', valor: 129, dia: 3, categoria: 'c-saude', conta: 'k-lua-ana', cartao: true }),
    R({ id: 'r-stream', tipo: 'despesa', descricao: 'Streaming', valor: 55.9, dia: 15, categoria: 'c-assinaturas', conta: 'k-lua-ana', cartao: true }),
    R({ id: 'r-musica', tipo: 'despesa', descricao: 'Spotify', valor: 23.9, dia: 22, categoria: 'c-assinaturas', conta: 'k-lua-beto', cartao: true }),
    R({ id: 'r-nabu', tipo: 'despesa', descricao: 'Nabu Casa', valor: 34.9, dia: 9, categoria: 'c-assinaturas', conta: 'k-lua-ana', cartao: true }),
    R({ id: 'r-aporte', tipo: 'despesa', descricao: 'Aporte nos investimentos', valor: 800, dia: 6, categoria: 'c-investimentos', conta: 'k-coral-ana', aporte: true }),
    R({ id: 'r-cel', tipo: 'despesa', descricao: 'Celular', valor: 59.99, dia: 14, categoria: 'c-contas', conta: 'k-sol-ana', cartao: true }),
  ];
  // meses passados (e o atual até hoje): ocorrências confirmadas, com variação nos valores que mudam
  for (let ym = inicio; ym <= ymAtual; ym = addYm(ym, 1)) {
    for (const id of fixos) {
      const r = rec.find(x => x.id === id);
      const data = dataNoMes(ym, r.dia);
      if (data > hj) continue;
      let valor = r.valor;
      let extra = r.vinculo ? { vinculo: r.vinculo } : {};
      if (id === 'r-sal') {
        valor = [11800, 12280, 11800, 11530, 12630, 11800, 11800][(+ym.slice(5)) % 7];
        extra = { descontos: clone(r.descontos) };
      }
      if (id === 'r-luz') valor = entre(205, 335);
      const o = Object.assign({ tipo: r.tipo, descricao: r.descricao, valor, categoria: r.categoria, conta: r.conta, cartao: r.cartao, data, recorrencia: r.id, competencia: ym }, extra);
      o.pago = !r.cartao || o.data < addYm(ymAtual, 0) + '-01';
      L(o);
    }
    const dia = d => dataNoMes(ym, d);
    const gastos = [
      [2, 'Mercado', 'c-mercado', 180, 520, 'k-coral-ana', false], [9, 'Mercado', 'c-mercado', 150, 480, 'k-lua-ana', true],
      [16, 'Mercado', 'c-mercado', 160, 430, 'k-coral-ana', false], [26, 'Hortifruti', 'c-mercado', 60, 140, 'k-lua-beto', true],
      [6, 'iFood', 'c-restaurantes', 45, 120, 'k-lua-ana', true], [13, 'Restaurante', 'c-restaurantes', 90, 220, 'k-lua-beto', true],
      [24, 'Padaria', 'c-restaurantes', 25, 60, 'k-coral-ana', false], [7, 'Combustível', 'c-transporte', 180, 260, 'k-sol-ana', true],
      [20, 'Combustível', 'c-transporte', 170, 250, 'k-sol-ana', true], [11, 'Uber', 'c-transporte', 18, 46, 'k-lua-ana', true],
      [17, 'Cinema', 'c-lazer', 60, 140, 'k-lua-beto', true], [23, 'Pet shop', 'c-pets', 120, 220, 'k-lua-beto', true],
      [19, 'Farmácia', 'c-saude', 35, 160, 'k-lua-ana', true],
    ];
    for (const [d, desc, cat, a, b, conta, cartao] of gastos) {
      const data = dia(d);
      if (data > hj) continue;
      const o = { tipo: 'despesa', descricao: desc, valor: entre(a, b), categoria: cat, conta, cartao, data };
      L(o);
    }
  }
  // freelances e reembolsos pontuais
  [[-5, 20, 1800], [-3, 22, 2400], [-1, 19, 1200]].forEach(([k, d, v]) => L({ tipo: 'receita', descricao: 'Freelance', valor: v, categoria: 'c-freelance', conta: 'k-sol-ana', data: dataNoMes(addYm(ymAtual, k), d), pago: true }));
  L({ tipo: 'receita', descricao: 'Reembolso médico', valor: 340, categoria: 'c-reembolso', conta: 'k-coral-ana', data: dataNoMes(addYm(ymAtual, -2), 9), pago: true });
  // geladeira em 10x no cartão do Beto: as parcelas futuras aparecem nas próximas faturas
  const g = 'g-geladeira';
  for (let k = 0; k < 10; k++) {
    L({ tipo: 'despesa', descricao: 'Geladeira', valor: 389.9, categoria: 'c-compras', conta: 'k-lua-beto', cartao: true, data: dataNoMes(addYm(ymAtual, -4 + k), 14), parcela: `${k + 1}/10`, grupo: g, pago: false });
  }
  // seguro do carro: fixo anual
  R({ id: 'r-seguro', tipo: 'despesa', descricao: 'Seguro do carro', valor: 2380, dia: 12, categoria: 'c-transporte', conta: 'k-coral-ana', inicio: addYm(ymAtual, 3), freq: 'anual' });
  // IPTU atrasado (para mostrar o aviso)
  const atras = iso(new Date(hoje().getTime() - 3 * 86400000));
  L({ tipo: 'despesa', descricao: 'IPTU', valor: 212.4, categoria: 'c-impostos', conta: 'k-coral-ana', data: atras, pago: false, parcela: '8/10' });
  return { lancamentos: lanc, recorrencias: rec };
}

function marcarFaturasPagas(d) {
  // depois de montar o exemplo: compras no cartão cuja fatura venceu até hoje ficam pagas
  const antes = S.d;
  S.d = d;
  MEMO = { d: null };
  const hj = iso(hoje());
  for (const l of d.lancamentos) if (l.cartao && !l.ajuste) l.pago = dataCaixa(l) < hj;
  for (const l of d.lancamentos) if (!l.cartao && !l.ajuste && l.descricao !== 'IPTU' && !l.grupo) l.pago = l.data <= hj;
  S.d = antes;
  MEMO = { d: null };
}

/* ------------------------------------------------------------------ Caixa (telas) */
function mesCaixa() { return S.ui.cxMes || ymHoje(); }
function navMes(ym) {
  return `<div class="mes-nav"><button class="icbtn" data-a="cx-mes" data-v="-1" aria-label="Mês anterior">${ic('chevL')}</button>
    <button class="mes-nome" data-a="cx-mes" data-v="0">${maiuscula(nomeMes(ym))}${ym === ymHoje() ? '' : '<small>voltar para hoje</small>'}</button>
    <button class="icbtn" data-a="cx-mes" data-v="1" aria-label="Próximo mês">${ic('chev')}</button></div>`;
}

function telaCaixa() {
  const u = S.ui;
  let html = cabecalho('Caixa', `<button class="icbtn" data-a="olho" aria-label="${S.oculto ? 'Mostrar' : 'Esconder'} valores">${ic(S.oculto ? 'eyeOff' : 'eye')}</button>`);
  html += `<div class="seg">${[['lista', 'Lançamentos'], ['fluxo', 'Fluxo'], ['categorias', 'Categorias']].map(([k, n]) =>
    `<button class="${u.cxModo === k ? 'on' : ''}" data-a="cx-modo" data-v="${k}">${n}</button>`).join('')}</div>`;
  if (!temCaixa()) {
    return html + `<div class="vazio"><b>Comece pelo que entra e sai todo mês.</b><br><br>
      <div class="btns" style="justify-content:center"><button class="btn pri" data-a="lanc-novo" data-v="despesa">${ic('minus')}Despesa</button>
      <button class="btn" data-a="lanc-novo" data-v="receita">${ic('plus')}Recebimento</button>
      <button class="btn" data-a="ia" data-v="caixa">${ic('ia')}Ler com IA</button></div></div>`;
  }
  if (u.cxModo === 'fluxo') return html + caixaFluxo();
  if (u.cxModo === 'categorias') return html + caixaCategorias();
  return html + caixaLista();
}

function resumoCaixaHTML(ym) {
  const r = resumoMes(ym);
  return `<div class="cx-resumo">
    <div><span>Entrou</span><b class="ent">${brl(r.entrou, 0)}</b>${r.aEntrar ? `<small>+ ${brl(r.aEntrar, 0)} a receber</small>` : ''}</div>
    <div><span>Saiu</span><b class="sai">${brl(r.saiu, 0)}</b>${r.aSair ? `<small>+ ${brl(r.aSair, 0)} a pagar</small>` : ''}</div>
    <div><span>Sobrou</span><b>${brl(r.sobra, 0)}</b><small>previsto ${brl(r.previsto, 0)}</small></div></div>`;
}

function caixaLista() {
  const u = S.ui, ym = mesCaixa(), atual = ym === ymHoje(), hj = iso(hoje());
  let html = '<div class="cx-duas"><div class="cx-lado">' + navMes(ym) + resumoCaixaHTML(ym);
  const saldoTxt = atual ? 'Saldo em caixa hoje' : ym < ymHoje() ? 'Saldo no fim do mês' : 'Saldo previsto no fim do mês';
  const saldoV = atual ? saldoCaixa() : ym < ymHoje() ? saldoCaixa(dataNoMes(ym, 31)) : saldoPrevisto(ym);
  html += `<div class="cx-saldo"><div><span>${saldoTxt}</span><b>${brl(saldoV)}</b>${atual ? `<small>No fim do mês: ${brl(saldoPrevisto(ym), 0)}</small>` : ''}</div>
    ${atual ? `<button class="btn peq" data-a="cx-ajuste">Ajustar saldo</button>` : ''}</div></div><div class="cx-lista">`;
  html += `<div class="chips c4">${[['tudo', 'Tudo'], ['entradas', 'Entradas'], ['saidas', 'Saídas'], ['pendentes', 'A pagar e receber']].map(([k, n]) =>
    `<button class="chip${u.cxFiltro === k ? ' on' : ''}" data-a="cx-filtro" data-v="${k}">${n}</button>`).join('')}</div>`;
  let lista = lancamentosEntre(ym, ym);
  if (u.cxFiltro === 'entradas') lista = lista.filter(ehRec);
  if (u.cxFiltro === 'saidas') lista = lista.filter(l => !ehRec(l));
  if (u.cxFiltro === 'pendentes') {
    lista = lista.filter(l => !l.pago);
    // no mês de hoje, o que ficou para trás sem pagar (os 2 meses que o aviso de atrasadas conta) aparece primeiro
    if (atual) lista = [...lancamentosEntre(addYm(ym, -2), addYm(ym, -1)).filter(l => !l.pago && !l.ajuste && !l.vinculo && !l.desconto && l.dc < hj), ...lista];
  }
  const faturas = faturasDe(lista);
  const naFatura = new Set(faturas.flatMap(f => f.itens.map(l => l.id)));
  // impostos na fonte e despesas ligadas (plano de saúde) ficam dentro do recebimento; no filtro Saídas aparecem soltos
  const aninha = u.cxFiltro !== 'saidas';
  const ligadosDe = new Map();
  if (aninha) {
    const recs = new Map(lista.filter(l => ehRec(l) && l.recorrencia).map(l => [l.recorrencia + '|' + compDe(l), l.id]));
    for (const x of lista) if (!ehRec(x) && x.vinculo) { const pid = recs.get(x.vinculo + '|' + compDe(x)); if (pid) { if (!ligadosDe.has(pid)) ligadosDe.set(pid, []); ligadosDe.get(pid).push(x); } }
  }
  const dentro = new Set([...ligadosDe.values()].flat().map(x => x.id));
  const pais = new Set(lista.filter(l => temDescontos(l)).map(l => l.id));
  const entradas = [
    ...lista.filter(l => !naFatura.has(l.id) && !dentro.has(l.id) && !(aninha && l.desconto && pais.has(l.pai))).map(l => {
      const lig = ligadosDe.get(l.id) || [], ds = aninha && (pais.has(l.id) || lig.length);
      const menos = ds ? totalDescontos(l) + lig.reduce((s2, x) => s2 + (+x.valor || 0), 0) : 0;
      return { dc: l.dc, html: linhaLanc(l) + (ds ? blocoDescontos(l, lig) : ''), net: sinal(l) * (+l.valor || 0) - menos, ord: ehRec(l) ? 0 : 1 };
    }),
    ...faturas.map(f => ({ dc: f.dc, html: linhaFatura(f), net: -f.total, ord: 2 })),
  ].sort((a, b) => a.dc < b.dc ? -1 : a.dc > b.dc ? 1 : a.ord - b.ord);
  if (!entradas.length) {
    return html + `<div class="vazio">Nada ${u.cxFiltro === 'tudo' ? 'lançado' : 'com esse filtro'} em ${nomeMes(ym).split(' ')[0]}.<br><br>
      <button class="btn" data-a="lanc-novo" data-v="despesa">${ic('plus')}Lançar</button></div></div></div>`;
  }
  let dia = null;
  for (const e of entradas) {
    if (e.dc !== dia) {
      dia = e.dc;
      const d = pData(dia);
      const net = entradas.filter(x => x.dc === dia).reduce((s, x) => s + x.net, 0);
      html += `<div class="dia-cab"><b>${dia === hj ? 'Hoje' : DIAS_SEMANA[d.getDay()]}, ${d.getDate()} de ${MESES[d.getMonth()]}</b><span class="${net >= 0 ? 'ent' : 'sai'}">${net >= 0 ? '+' : '−'} ${brl(Math.abs(net), 0)}</span></div>`;
    }
    html += e.html;
  }
  return html + '</div></div>';
}

function linhaLanc(l, dentroFatura) {
  const cat = catDe(l.categoria);
  const nomeCat = l.ajuste ? 'Ajuste de saldo' : (cat?.nome || 'Sem categoria');
  const atras = !l.pago && (l.dc || l.data) < iso(hoje());
  const rec = ehRec(l);
  const conta = !dentroFatura && l.conta ? nomeConta(contaDe(l.conta)) + (l.cartao ? ' · cartão' : '') : '';
  const extras = [l.parcela ? 'parcela ' + l.parcela : '', l.recorrencia ? 'fixo' : '', dentroFatura ? fDataC(pData(l.data)) : '',
    l.desconto ? 'descontado de ' + (l.paiDesc || 'recebimento') : '', l.vinculo && !ehRec(l) ? 'baixa com ' + nomeVinculo(l) : ''].filter(Boolean);
  const apo = ehAporte(l);
  const estado = l.pago || dentroFatura || l.desconto || l.vinculo ? '' : `<span class="tag ${atras ? 'alerta' : 'pend'}">${atras ? (rec || apo ? 'Atrasado' : 'Atrasada') : (rec ? 'A receber' : apo ? 'A aplicar' : 'A pagar')}</span>`;
  // como no CronologIA: o que já foi pago fica verde, com o visto; o que falta tem o círculo do lado para dar baixa
  const baixa = !dentroFatura && !l.desconto && !l.vinculo && !l.ajuste;
  const verbo = rec ? 'Recebi' : apo ? 'Apliquei' : 'Paguei', feito = rec ? 'Recebido' : apo ? 'Aplicado' : 'Pago';
  const marca = !baixa ? '' : l.pago ? `<span class="visto on" role="img" aria-label="${feito}" title="${feito}">${ic('check')}</span>`
    : `<button class="visto${atras ? ' atras' : ''}" data-a="lanc-pagar" data-id="${esc(l.id)}" aria-label="${verbo}: ${esc(l.descricao)}" title="${verbo}">${ic('check')}</button>`;
  return `<div class="lanc${dentroFatura ? ' sub' : ''}${baixa && l.pago ? ' feito' : ''}" data-a="lanc" data-id="${esc(l.id)}" role="button" tabindex="0">
    <span class="ini${apo ? ' apo' : ''}" style="--c:${corCat(l)}">${apo ? ic('wallet') : esc((l.descricao || '?').slice(0, 1).toUpperCase())}</span>
    <span class="lanc-t"><b>${esc(l.descricao)}</b><span>${esc([nomeCat, conta, ...extras].filter(Boolean).join(' · '))}</span></span>
    <span class="lanc-d"><b class="${rec ? 'ent' : 'sai'}">${rec ? '+' : '−'} ${brl(+l.valor || 0)}</b>${estado}</span>${marca}
  </div>`;
}

function linhaFatura(f) {
  const c = contaDe(f.conta);
  const aberta = S.ui.faturaAberta === f.k;
  const atras = !f.pago && f.dc < iso(hoje());
  const itens = f.itens.slice().sort((a, b) => a.data < b.data ? -1 : 1);
  return `<div class="lanc fatura${aberta ? ' aberta' : ''}${f.pago ? ' feito' : ''}" data-a="fatura-abrir" data-v="${esc(f.k)}" role="button" tabindex="0" aria-expanded="${aberta}">
    <span class="ini" style="--c:${corOk(bancoDe(c?.banco)?.cor) || '#B8B0B0'}">${ic('card', 'ic-s')}</span>
    <span class="lanc-t"><b>Fatura ${esc(nomeConta(c))}</b><span>${plural(f.itens.length, 'compra', 'compras')} · vence ${fDataC(pData(f.dc))} · ${aberta ? 'toque para fechar' : 'toque para ver'}</span></span>
    <span class="lanc-d"><b class="sai">− ${brl(f.total)}</b>${f.pago ? '' : `<span class="tag ${atras ? 'alerta' : 'pend'}">${atras ? 'Atrasada' : 'Aberta'}</span>`}</span>
    ${f.pago ? `<span class="visto on" role="img" aria-label="Paga" title="Paga">${ic('check')}</span>` : `<button class="visto${atras ? ' atras' : ''}" data-a="fatura-pagar" data-v="${esc(f.k)}" aria-label="Paguei a fatura ${esc(nomeConta(c))}" title="Paguei">${ic('check')}</button>`}
  </div>${aberta ? `<div class="fatura-itens">${itens.map(l => linhaLanc(l, true)).join('')}</div>` : ''}`;
}

/* --------- fluxo de caixa */
// Período escolhido: "atrás" conta o mês atual (12 atrás = os últimos 12 meses, com este); "à frente" vem depois dele.
// Sem nenhum mês atrás, o mês atual é o primeiro dos "à frente" (12 à frente = este e os 11 seguintes), como antes.
const PER_MAX = 60;
function mesesFluxo() {
  const p = S.ui.cxPeriodo;
  if (p === 'passado') return [12, 0];
  if (p === 'futuro') return [0, 12];
  if (p === 'outro') {
    const a = Math.max(0, Math.min(PER_MAX, Math.round(+S.ui.cxAtras || 0))), f = Math.max(0, Math.min(PER_MAX, Math.round(+S.ui.cxFrente || 0)));
    if (a + f >= 2) return [a, f];
  }
  return [6, 6];
}
function periodoFluxo() {
  const [at, fr] = mesesFluxo(), a = ymHoje();
  return at ? [addYm(a, -(at - 1)), addYm(a, fr)] : [a, addYm(a, fr - 1)];
}
const rotPeriodo = (a, f) => a && f ? `${a} + ${f}` : a ? `${a} atrás` : `${f} à frente`;
function abrirPeriodo() {
  const [a0, f0] = S.ui.cxPeriodo === 'outro' ? mesesFluxo() : [24, 0];
  const pre = [[24, 0], [12, 12], [0, 24], [36, 0], [24, 12], [0, 36]];
  abrirFolha(() => ({
    titulo: 'Período do fluxo',
    corpo: `<p class="ajuda" style="margin:0 0 12px">Para trás conta o mês atual. Até ${PER_MAX} de cada lado.</p>
      <div class="chips c3">${pre.map(([a, f]) => `<button class="chip${S.ui.cxPeriodo === 'outro' && a === a0 && f === f0 ? ' on' : ''}" data-a="cx-per-pre" data-v="${a},${f}">${rotPeriodo(a, f)}</button>`).join('')}</div>
      <div class="campos-2">
        <div class="campo"><label class="lbl" for="per-atras">Meses para trás</label><input id="per-atras" class="inp" type="number" inputmode="numeric" min="0" max="${PER_MAX}" step="1" value="${a0}"></div>
        <div class="campo"><label class="lbl" for="per-frente">Meses à frente</label><input id="per-frente" class="inp" type="number" inputmode="numeric" min="0" max="${PER_MAX}" step="1" value="${f0}"></div>
      </div>`,
    pe: `<button class="btn pri larga" data-a="cx-per-ok">Ver no fluxo</button>`,
  }));
}
function aplicarPeriodo(a, f) {
  a = Math.round(+a); f = Math.round(+f);
  if (!Number.isFinite(a) || !Number.isFinite(f) || a < 0 || f < 0) return toast('Use números de 0 a ' + PER_MAX + '.');
  if (a > PER_MAX || f > PER_MAX) return toast(`Até ${PER_MAX} meses de cada lado.`);
  if (a + f < 2) return toast('Escolha pelo menos 2 meses.');
  Object.assign(S.ui, { cxPeriodo: 'outro', cxAtras: a, cxFrente: f });
  salvarUI(); fecharFolha(); render();
}
// Gastos do dia a dia: o que não é fixo nem parcela (mercado, restaurante, combustível...)
const ehVariavel = l => !ehRec(l) && !l.ajuste && !l.recorrencia && !l.grupo && !l.desconto;
function variaveisDoMes(ym) { return lancamentosEntre(ym, ym).filter(ehVariavel).reduce((s, l) => s + (+l.valor || 0), 0); }
function mediaVariaveis() { const a = ymHoje(); return memo('mv', () => [1, 2, 3].reduce((s, k) => s + variaveisDoMes(addYm(a, -k)), 0) / 3); }
function serieFluxo() {
  const [ini, fim] = periodoFluxo();
  const meses = [];
  for (let ym = ini; ym <= fim; ym = addYm(ym, 1)) meses.push(ym);
  const atual = ymHoje(), estimar = S.d.ajustes.prever_dia !== false, media = mediaVariaveis();
  let acum = 0;
  return meses.map(ym => {
    let ent = 0, sai = 0, apo = 0;
    for (const l of lancamentosEntre(ym, ym)) { if (l.ajuste) continue; if (ehRec(l)) ent += +l.valor || 0; else if (ehAporte(l)) apo += +l.valor || 0; else sai += +l.valor || 0; }
    const est = estimar && ym >= atual ? Math.max(0, media - variaveisDoMes(ym)) : 0;
    acum += est;
    const saldo = ym < atual ? saldoCaixa(dataNoMes(ym, 31)) : saldoPrevisto(ym) - acum;
    return { ym, ent, sai, apo, est, net: ent - sai - apo - est, prev: ym > atual, atual: ym === atual, saldo };
  });
}
function caixaFluxo() {
  const u = S.ui;
  const serie = serieFluxo();
  CACHE.fluxo = serie;
  // a média do que sobrou começa no primeiro mês com algum lançamento (num período longo, os meses antes do app não puxam a média para baixo)
  const ini = serie.findIndex(m => !m.prev && (m.ent || m.sai || m.apo));
  const passado = ini < 0 ? [] : serie.filter((m, k) => !m.prev && k >= ini), futuro = serie.filter(m => m.prev);
  const soma = (l, k) => l.reduce((s, m) => s + m[k], 0);
  const outroOn = u.cxPeriodo === 'outro';
  let html = `<div class="chips c4">${[['passado', '12 atrás'], ['meio', '6 + 6'], ['futuro', '12 à frente'], ['outro', outroOn ? rotPeriodo(...mesesFluxo()) : 'Outro']].map(([k, n]) =>
    `<button class="chip${u.cxPeriodo === k ? ' on' : ''}" data-a="cx-periodo" data-v="${k}"${k === 'outro' ? ' aria-label="Outro período"' : ''}>${n}</button>`).join('')}</div>`;
  html += `<div class="graf-card"><h3 class="g-tit">${rotIc('chart')}<span>Fluxo de caixa mensal</span></h3>
    <div class="stat-duo">${passado.length ? `<div><span>Sobrou por mês, em média</span><b>${brlS(soma(passado, 'net') / passado.length, 0)}</b><small>${nomeMes(passado[0].ym, true)} a ${nomeMes(passado[passado.length - 1].ym, true)}</small></div>` : ''}
      ${futuro.length ? `<div><span>Deve sobrar à frente</span><b>${brlS(soma(futuro, 'net'), 0)}</b><small>${S.d.ajustes.prever_dia !== false ? 'fixos, parcelas, faturas e dia a dia' : 'fixos, parcelas e faturas já lançados'}</small></div>` : ''}</div>
    <div class="chart" id="ch-fluxo" role="img" aria-label="Entradas e saídas por mês"></div>
    <div class="leg"><span><i class="sw-q" style="--kc:var(--entra)"></i>Entradas</span><span><i class="sw-q" style="--kc:var(--sai)"></i>Saídas</span>
      ${serie.some(m => m.apo > 0) ? '<span><i class="sw-q" style="--kc:var(--apo)"></i>Aportes</span>' : ''}
      ${S.d.ajustes.prever_dia !== false ? '<span><i class="sw-q est"></i>Dia a dia (média)</span>' : ''}<span><i class="pt-q"></i>Sobrou</span><span><i class="sw-q prev"></i>Previsto</span></div>
    <div class="sep" style="margin:14px 6px"></div>
    <div class="linha-sw" style="margin:0 6px"><div><b>Prever o dia a dia</b><span>Média dos gastos que não são fixos nem parcelas: ${brl(mediaVariaveis(), 0)} por mês.</span></div>
      ${chave('prever_dia', S.d.ajustes.prever_dia !== false, 'Prever o dia a dia')}</div></div>`;
  html += `<div class="graf-card"><h3 class="g-tit">${rotIc('wallet', 'bom')}<span>Saldo em caixa</span></h3>
    <div class="stat-duo"><div><span>Hoje</span><b>${brl(saldoCaixa(), 0)}</b></div>
      <div><span>Em ${nomeMes(serie[serie.length - 1].ym, true)}</span><b>${brl(serie[serie.length - 1].saldo, 0)}</b></div></div>
    <div class="chart" id="ch-saldo" role="img" aria-label="Saldo em caixa no fim de cada mês"></div>
    <div class="leg"><span><i class="k" style="--kc:var(--accent)"></i>Fechado</span><span><i class="k tr" style="--kc:var(--accent)"></i>Previsto</span></div></div>`;
  html += `<p class="nota">Compras no cartão entram no mês em que a fatura vence.</p>
  <details class="card" style="margin-top:16px"><summary>Ver tabela por mês</summary>
  <div class="tabela-rola"><table class="tabela"><thead><tr><th>Mês</th><th class="n">Entrou</th><th class="n">Saiu</th><th class="n">Sobrou</th><th class="n">Saldo</th></tr></thead><tbody>
  ${serie.map(m => `<tr><td>${nomeMes(m.ym, true)}${m.prev ? ' *' : ''}</td><td class="n">${brl(m.ent, 0)}</td><td class="n">${brl(m.sai, 0)}</td><td class="n">${brl(m.net, 0)}</td><td class="n">${brl(m.saldo, 0)}</td></tr>`).join('')}
  </tbody></table></div><p class="nota">* previsto</p></details>`;
  return html;
}

function desenharFluxo() {
  const el = $('#ch-fluxo');
  const serie = CACHE.fluxo;
  if (!el || !serie) return;
  const W = Math.max(280, el.clientWidth), H = 230, pl = 46, pr = 6, pt = 10, pb = 24;
  const max = Math.max(1, ...serie.map(m => Math.max(m.ent, m.sai + m.apo + m.est)));
  const step = niceStep(max / 2), top = Math.ceil(max / step) * step;
  const zero = pt + (H - pt - pb) / 2;
  const Y = v => zero - v / top * ((H - pt - pb) / 2);
  const banda = (W - pl - pr) / serie.length, bw = Math.min(22, banda * 0.62);
  // muitos meses: menos nomes embaixo (o ano no lugar de janeiro) e pontos menores
  const passoN = serie.length <= 7 ? 1 : Math.max(2, Math.ceil(serie.length / Math.max(1, Math.floor((W - pl - pr) / 30)))), rp = Math.max(1.6, Math.min(4, banda * 0.3)), longo = serie.length > 12;
  let g = '';
  for (let v = -top; v <= top + 1; v += step) {
    const y = Y(v).toFixed(1);
    g += `<line class="grid${v === 0 ? ' zero' : ''}" x1="${pl}" x2="${W - pr}" y1="${y}" y2="${y}"/><text x="${pl - 8}" y="${(+y + 4).toFixed(1)}" text-anchor="end">${v < 0 ? '−' : ''}${compacto(Math.abs(v))}</text>`;
  }
  const r = Math.min(4, bw / 2);
  serie.forEach((m, i) => {
    const x = pl + i * banda + (banda - bw) / 2, cls = m.prev ? ' prev' : '';
    if (m.ent > 0) { const h = zero - Y(m.ent); g += `<path class="b-ent${cls}" d="M${x},${zero - 1}v${-(h - r - 1)}q0,-${r} ${r},-${r}h${bw - 2 * r}q${r},0 ${r},${r}v${h - r - 1}z"/>`; }
    // barra de baixo empilhada: saídas, aportes e dia a dia (o último segmento tem a ponta arredondada)
    const segs = [[m.sai, 'b-sai' + cls], [m.apo, 'b-apo' + cls], [m.est, 'b-est']].filter(sg => sg[0] > 0);
    let acc = 0;
    segs.forEach(([v, c], k) => {
      const y0 = Y(-acc) + (k ? 2 : 1), h = Y(-(acc + v)) - y0;
      acc += v;
      if (h <= 0.5) return;
      if (k === segs.length - 1 && h > r + 1) g += `<path class="${c}" d="M${x},${y0}v${h - r}q0,${r} ${r},${r}h${bw - 2 * r}q${r},0 ${r},-${r}v${-(h - r)}z"/>`;
      else g += `<rect class="${c}" x="${x}" y="${y0}" width="${bw}" height="${h}"/>`;
    });
    const cx = pl + i * banda + banda / 2;
    g += `<circle class="pt-net" cx="${cx.toFixed(1)}" cy="${Y(m.net).toFixed(1)}" r="${rp.toFixed(1)}"/>`;
    const di = i - serie.findIndex(x => x.atual);
    const nomeia = serie.findIndex(x => x.atual) >= 0 ? di % passoN === 0 : i % passoN === 0;
    if (nomeia) g += `<text x="${cx.toFixed(1)}" y="${H - 6}" text-anchor="middle"${m.atual ? ' class="hoje-t"' : ''}>${longo && m.ym.slice(5) === '01' && !m.atual ? m.ym.slice(0, 4) : MESES[+m.ym.slice(5) - 1]}</text>`;
  });
  g += `<rect id="fx-hl" class="hl-banda" x="0" y="${pt}" width="${banda.toFixed(1)}" height="${H - pt - pb}" style="display:none"/>`;
  el.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${g}</svg><div class="tip" style="display:none"></div>`;
  const svg = $('svg', el), tip = $('.tip', el), hl = $('#fx-hl', el);
  const mostrar = ev => {
    const rc = svg.getBoundingClientRect();
    const i = Math.max(0, Math.min(serie.length - 1, Math.floor(((ev.clientX - rc.left) * (W / (rc.width || W)) - pl) / banda)));
    const m = serie[i];
    hl.setAttribute('x', (pl + i * banda).toFixed(1)); hl.style.display = '';
    tip.textContent = '';
    const cab = document.createElement('div'); cab.className = 't-d'; cab.textContent = nomeMes(m.ym) + (m.prev ? ' · previsto' : m.atual ? ' · até agora e previsto' : '');
    tip.appendChild(cab);
    const linhas = [[m.ent, 'Entradas', 'var(--entra)'], [m.sai, m.est ? 'Saídas lançadas' : 'Saídas', 'var(--sai)']];
    if (m.apo) linhas.push([m.apo, 'Aportes', 'var(--apo)']);
    if (m.est) linhas.push([m.est, 'Dia a dia (média)', 'var(--muted)']);
    linhas.push([m.net, 'Sobrou', 'var(--text)']);
    for (const [v, n, c] of linhas) {
      const row = document.createElement('div'); row.className = 't-r';
      const k = document.createElement('i'); k.className = 'k'; k.style.setProperty('--kc', c);
      const b = document.createElement('b'); b.textContent = (v < 0 ? '−' : '') + brl(Math.abs(v), 0);
      const sp = document.createElement('span'); sp.textContent = n;
      row.append(k, b, sp); tip.appendChild(row);
    }
    tip.style.display = '';
    const cx = pl + i * banda + banda / 2, tw = tip.offsetWidth;
    tip.style.left = Math.min(Math.max(0, cx > W / 2 ? cx - tw - 10 : cx + 10), W - tw) + 'px';
  };
  el.onpointerdown = mostrar; el.onpointermove = mostrar;
  el.onpointerleave = () => { tip.style.display = 'none'; hl.style.display = 'none'; };
}

function desenharSaldo() {
  const el = $('#ch-saldo');
  const serie = CACHE.fluxo;
  if (!el || !serie) return;
  const W = Math.max(280, el.clientWidth), H = 190, pl = 46, pr = 10, pt = 12, pb = 24;
  const vals = serie.map(m => m.saldo);
  let lo = Math.min(0, ...vals), hi = Math.max(...vals, 1);
  const step = niceStep((hi - lo) / 4 || 1);
  lo = Math.floor(lo / step) * step; hi = Math.ceil(hi / step) * step;
  const X = i => pl + (i + 0.5) * (W - pl - pr) / serie.length;
  const Y = v => pt + (1 - (v - lo) / ((hi - lo) || 1)) * (H - pt - pb);
  let g = '';
  for (let v = lo; v <= hi + step / 2; v += step) {
    const y = Y(v).toFixed(1);
    g += `<line class="grid${Math.abs(v) < 1e-9 ? ' zero' : ''}" x1="${pl}" x2="${W - pr}" y1="${y}" y2="${y}"/><text x="${pl - 8}" y="${(+y + 4).toFixed(1)}" text-anchor="end">${v < 0 ? '−' : ''}${compacto(Math.abs(v))}</text>`;
  }
  const ia = serie.findIndex(m => m.atual);
  const corte = ia >= 0 ? ia : serie.filter(m => !m.prev).length - 1;
  const path = (a, b) => serie.slice(a, b + 1).map((m, k) => `${k ? 'L' : 'M'}${X(a + k).toFixed(1)},${Y(m.saldo).toFixed(1)}`).join('');
  if (corte >= 0) g += `<path class="l-hist" d="${path(0, corte)}"/>`;
  if (corte < serie.length - 1) g += `<path class="l-proj" d="${path(Math.max(0, corte), serie.length - 1)}"/>`;
  serie.forEach((m, i) => {
    if (serie.length <= 7 || i % 2 === 0 || m.atual) g += `<text x="${X(i).toFixed(1)}" y="${H - 6}" text-anchor="middle"${m.atual ? ' class="hoje-t"' : ''}>${MESES[+m.ym.slice(5) - 1]}</text>`;
  });
  if (corte >= 0) g += `<circle class="pt" cx="${X(corte).toFixed(1)}" cy="${Y(serie[corte].saldo).toFixed(1)}" r="4.5" fill="var(--accent)"/>`;
  g += `<circle class="pt" cx="${X(serie.length - 1).toFixed(1)}" cy="${Y(serie[serie.length - 1].saldo).toFixed(1)}" r="4.5" fill="var(--accent)"/>`;
  g += `<g id="sd-x" style="display:none"><line class="cross" y1="${pt}" y2="${H - pb}"/><circle class="pt" r="4.5" fill="var(--accent)"/></g>`;
  el.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${g}</svg><div class="tip" style="display:none"></div>`;
  const svg = $('svg', el), tip = $('.tip', el), cr = $('#sd-x', el);
  const mostrar = ev => {
    const rc = svg.getBoundingClientRect();
    const i = Math.max(0, Math.min(serie.length - 1, Math.round(((ev.clientX - rc.left) * (W / (rc.width || W)) - pl) / ((W - pl - pr) / serie.length) - 0.5)));
    const m = serie[i], x = X(i);
    cr.style.display = ''; $('line', cr).setAttribute('x1', x); $('line', cr).setAttribute('x2', x);
    $('circle', cr).setAttribute('cx', x); $('circle', cr).setAttribute('cy', Y(m.saldo));
    tip.textContent = '';
    const cab = document.createElement('div'); cab.className = 't-d'; cab.textContent = `Fim de ${nomeMes(m.ym)}${m.prev || m.atual ? ' · previsto' : ''}`;
    const row = document.createElement('div'); row.className = 't-r';
    const b = document.createElement('b'); b.textContent = (m.saldo < 0 ? '−' : '') + brl(Math.abs(m.saldo), 0);
    const sp = document.createElement('span'); sp.textContent = 'em caixa';
    row.append(b, sp); tip.append(cab, row);
    tip.style.display = '';
    const tw = tip.offsetWidth;
    tip.style.left = Math.min(Math.max(0, x > W / 2 ? x - tw - 10 : x + 10), W - tw) + 'px';
  };
  el.onpointerdown = mostrar; el.onpointermove = mostrar;
  el.onpointerleave = () => { tip.style.display = 'none'; cr.style.display = 'none'; };
}

/* --------- categorias */
function caixaCategorias() {
  const u = S.ui, ym = mesCaixa(), tipo = u.cxCatTipo;
  let html = navMes(ym);
  html += `<div class="seg"><button class="${tipo === 'despesa' ? 'on' : ''}" data-a="cx-cat-tipo" data-v="despesa">Gastos</button>
    <button class="${tipo === 'receita' ? 'on' : ''}" data-a="cx-cat-tipo" data-v="receita">Recebimentos</button></div>`;
  const agrupar = lista => {
    const m = new Map();
    for (const l of lista) {
      if (l.ajuste || l.tipo !== tipo) continue;
      const k = l.categoria || '-';
      const g = m.get(k) || { k, v: 0, n: 0 };
      g.v += +l.valor || 0; g.n++;
      m.set(k, g);
    }
    return m;
  };
  const atual = agrupar(lancamentosCompetencia(ym));
  const ant = [1, 2, 3].map(k => agrupar(lancamentosCompetencia(addYm(ym, -k))));
  let gs = [...atual.values()].sort((a, b) => b.v - a.v);
  const total = gs.reduce((s, g) => s + g.v, 0);
  if (!gs.length) return html + `<div class="vazio">Nenhum ${tipo === 'despesa' ? 'gasto' : 'recebimento'} em ${nomeMes(ym).split(' ')[0]}.</div>`;
  if (gs.length > 8) {
    const resto = gs.slice(7);
    gs = gs.slice(0, 7).concat([{ k: '_outras', v: resto.reduce((s, g) => s + g.v, 0), n: resto.reduce((s, g) => s + g.n, 0), outras: resto.length }]);
  }
  const sel = gs.find(g => g.k === u.cxSel);
  const nome = g => g.k === '_outras' ? `Outras (${g.outras})` : g.k === '-' ? 'Sem categoria' : (catDe(g.k)?.nome || 'Sem categoria');
  const cor = g => g.k === '_outras' || g.k === '-' ? 'var(--c0)' : (corOk(catDe(g.k)?.cor) || 'var(--c0)');
  html += `<div class="graf-card" style="padding:18px 18px 8px">
    <div class="stat-duo" style="margin:0 0 10px"><div><span>${tipo === 'despesa' ? 'Gastos' : 'Recebimentos'} em ${MESES_LONGOS[+ym.slice(5) - 1]}</span><b>${brl(total, 0)}</b></div>
      <div><span>Média dos 3 meses antes</span><b>${brl(ant.reduce((s, m) => s + [...m.values()].reduce((a, g) => a + g.v, 0), 0) / 3, 0)}</b></div></div>
    <div class="pilha-cap">${sel ? `<b>${esc(nome(sel))}</b> · ${brl(sel.v, 0)} · ${pct1(sel.v / total * 100)}%` : 'Toque numa parte para ver o valor'}</div>
    <div class="pilha" role="img" aria-label="Divisão por categoria">${gs.map(g => `<i data-a="cx-sel" data-v="${esc(g.k)}" style="--c:${cor(g)};flex:${g.v / total} 1 0"></i>`).join('')}</div>
    <div class="comps">${gs.map(g => {
      const media = g.k === '_outras' ? null : ant.reduce((s, m) => s + (m.get(g.k)?.v || 0), 0) / 3;
      const dif = media ? (g.v - media) / media * 100 : null;
      return `<div class="comp${u.cxSel === g.k ? ' on' : ''}" data-a="cx-sel" data-v="${esc(g.k)}" style="--c:${cor(g)}">
        <span class="sq"></span><div class="nm"><b>${esc(nome(g))}</b><span class="sub">${plural(g.n, 'lançamento', 'lançamentos')}${media ? ` · média ${brl(media, 0)}` : ''}</span></div>
        <div class="vl">${brl(g.v, 0)}<small>${pct1(g.v / total * 100)}%${dif != null && Math.abs(dif) >= 10 ? ` · ${dif > 0 ? '▲' : '▼'} ${pct(Math.round(Math.abs(dif)))}%` : ''}</small></div>
        <div class="barra"><i style="width:${(g.v / gs[0].v * 100).toFixed(1)}%"></i></div></div>`;
    }).join('')}</div></div>
    <p class="nota">Pela data da compra.</p>`;
  return html;
}

/* ------------------------------------------------------------------ Caixa: formulários */
const round2 = v => Math.round((+v || 0) * 100) / 100;
function ultimaConta(tipo) {
  const l = S.d.lancamentos.filter(x => x.tipo === tipo && x.conta && !x.ajuste).sort((a, b) => a.data < b.data ? 1 : -1)[0];
  if (l) return { conta: l.conta, cartao: !!l.cartao };
  const c = contas().find(x => tipo === 'despesa' && x.cartao) || contas()[0];
  return { conta: c?.id || '', cartao: false };
}

// aberta de dentro de outra janela (Apagar fixo do formulário, por exemplo), fica por cima dela: Cancelar, X e Voltar voltam
// para a de baixo; escolher uma opção fecha todas e faz
function escolher({ titulo, texto, opcoes }) {
  abrirFolha(() => ({
    titulo,
    corpo: `<p style="margin:0 0 4px;color:var(--text-2)">${texto}</p>`,
    pe: `<div class="pe-col">${opcoes.map((o, i) => `<button class="btn${o.perigo ? ' perigo' : o.pri ? ' pri' : ''}" data-a="escolha" data-v="${i}">${o.rotulo}</button>`).join('')}
      <button class="btn" data-a="fechar">Cancelar</button></div>`,
  }), null, !!FOLHA);
  FOLHA.opcoes = opcoes;
}

function abrirEscolhaNovo() {
  abrirFolha(() => ({
    titulo: 'Adicionar',
    corpo: `<div class="escolhas">
      <button class="op" data-a="lanc-novo" data-v="despesa"><span class="op-ic alerta">${ic('minus')}</span><span class="op-t"><b>Despesa</b><span>Conta, compra, gasto fixo ou parcelado</span></span>${ic('chev', 'chev')}</button>
      <button class="op" data-a="lanc-novo" data-v="receita"><span class="op-ic ok">${ic('plus')}</span><span class="op-t"><b>Recebimento</b><span>Salário, freelance, pix recebido</span></span>${ic('chev', 'chev')}</button>
      <button class="op" data-a="aporte-novo"><span class="op-ic apo">${ic('wallet')}</span><span class="op-t"><b>Aporte</b><span>Compromisso de aplicar nos seus investimentos</span></span>${ic('chev', 'chev')}</button>
      <button class="op" data-a="ia" data-v="caixa"><span class="op-ic">${ic('ia')}</span><span class="op-t"><b>Ler com IA</b><span>Fatura em PDF, print, foto de papel ou texto do WhatsApp</span></span>${ic('chev', 'chev')}</button>
      <button class="op" data-a="novo-inv"><span class="op-ic neutro">${ic('wallet')}</span><span class="op-t"><b>Investimento</b><span>CDB, Tesouro, poupança, ações</span></span>${ic('chev', 'chev')}</button>
      ${S.d.investimentos.length ? `<button class="op" data-a="ia-saldos" data-v=""><span class="op-ic">${ic('ia')}</span><span class="op-t"><b>Atualizar saldos</b><span>Lista com o valor de agora de cada investimento; a IA calcula os aportes</span></span>${ic('chev', 'chev')}</button>` : ''}
    </div>`,
  }));
}

/* --------- lançamento */
let LF = null;
function abrirLancamento(id, preset) {
  const l = id ? acharLanc(id) : null;
  if (id && !l) { toast('Esse lançamento não existe mais.'); return; }
  if (l) {
    LF = { id: l.id, virtual: !!l.virtual, recorrencia: l.recorrencia || null, competencia: l.competencia || null, grupo: l.grupo || null,
      parcela: l.parcela || null, ajuste: !!l.ajuste, tipo: l.tipo, valor: +l.valor || 0, descricao: l.descricao || '', categoria: l.categoria || '',
      data: l.data, pago: !!l.pago, pagoMexido: true, conta: l.conta || '', cartao: !!l.cartao, obs: l.obs || '', obsAberta: !!l.obs,
      repete: 'nao', vezes: 12, erros: {}, novaCat: null, catsNovas: [],
      partes: clone(l.partes || []), descontos: clone(l.descontos || []), descAberto: String(id).startsWith('d:'), recibo: null, lendoRecibo: false,
      vinculo: l.vinculo || '', ligadosNovos: [], aporte: ehAporte(l), pagoOrig: !!l.pago,
      investimento: l.investimento || (l.recorrencia && recPorId().get(l.recorrencia)?.investimento) || '' };
  } else {
    const tipo = preset?.tipo || 'despesa';
    LF = Object.assign({ id: null, tipo, valor: 0, descricao: '', categoria: '', data: iso(hoje()), pago: true, pagoMexido: false,
      obs: '', obsAberta: false, repete: 'nao', vezes: 10, erros: {}, novaCat: null, catsNovas: [],
      partes: [], descontos: [], descAberto: false, recibo: null, lendoRecibo: false, vinculo: '', ligadosNovos: [], pagoOrig: false, investimento: '' }, ultimaConta(tipo), preset || {});
  }
  abrirFolha(montarFormLanc);
}

// Aporte aplicado: para onde foi o dinheiro. No cadastro do compromisso (a aplicar) não precisa;
// para dar como aplicado, sim (se houver investimentos), e o valor soma a ele.
function invsDoAporte() { return porEscopo('meu'); }
function campoInvestimentoAporte(o, chave = 'lf-inv') {
  const lista = invsDoAporte();
  if (!lista.length) return `<div class="campo"><div class="lbl">Em qual investimento</div><p class="ajuda" style="margin:0">Cadastre o investimento em Invest primeiro.</p></div>`;
  if (!o.investimento && lista.length === 1) o.investimento = lista[0].id;
  const sel = lista.find(i => i.id === o.investimento);
  return `<div class="campo"><div class="lbl">Em qual investimento</div><div class="chips" style="margin:0">
    ${lista.map(i => `<button class="chip${o.investimento === i.id ? ' on' : ''}" data-a="${chave}" data-v="${esc(i.id)}" style="--c:${corOk(bancoDe(i.banco)?.cor) || 'var(--c0)'}"><span class="bol"></span>${esc(i.nome)}</button>`).join('')}</div>
    ${o.erroInv ? `<div class="msg-erro">${esc(o.erroInv)}</div>` : ''}
    ${sel ? `<div class="ajuda">${esc(sel.nome)}: ${brl(valorHoje(sel))} → ${brl(valorHoje(sel) + (+o.valor || 0))}.</div>` : ''}</div>`;
}

// Adicionar › Nova despesa e Novo investimento: trazer de mensagem, arquivo ou fala, em quadrinhos tracejados
// no alto da janela, como no ResolvIA e no CronologIA (Ler com IA mora aqui, não no cabeçalho).
function tilesIA(modo) {
  if (!iaOn()) return '';
  const caixa = modo === 'caixa', voz = vozPronta();
  const t = (inicio, icone, txt, nota) => `<button type="button" class="imp-tile" data-a="ia-de" data-v="${modo}" data-ini="${inicio}">${ic(icone)}<span>${txt}${nota ? `<small>${nota}</small>` : ''}</span></button>`;
  return `<div class="campo imp-campo"><div class="lbl">Trazer de mensagem ou imagem</div>
    <div class="imp-tiles${voz ? ' quatro' : ''}">${t('texto', 'clipboard-paste', 'Colar mensagem')}${t('arquivo', caixa ? 'receipt' : 'image', caixa ? 'Fatura, print ou foto' : 'Imagem ou print')}${t('camera', 'scan', 'Digitalizar com\u00a0IA', camOk() ? '' : 'Precisa de https')}${voz ? t('voz', 'mic', 'Falar') : ''}</div>
    <p class="imp-ajuda">Dá para colar a imagem direto aqui.</p>
    ${!caixa && S.d.investimentos.length && !(F && F.id) ? `<button type="button" class="link imp-saldos" data-a="ia-saldos" data-sobre="1" data-v="${esc(F && F.titular === 'terceiros' ? F.terceiro || '' : '')}">${ic('ia', 'ic-s')}Atualizar saldos de vários</button>` : ''}</div>`;
}

function montarFormLanc() {
  const f = LF, rec = f.tipo === 'receita', hj = iso(hoje());
  const cats = [...S.d.categorias, ...f.catsNovas].filter(c => c.tipo === f.tipo);
  const conta = contaDe(f.conta);
  const vinc = !rec && f.vinculo ? recPorId().get(f.vinculo) : null;
  const noCartao = !rec && !vinc && f.cartao && conta?.cartao;
  const dc = dataCaixa({ data: f.data, conta: f.conta, cartao: noCartao });
  if (!f.pagoMexido) f.pago = !f.id && !rec && f.aporte ? false : dc <= hj;
  const r = f.recorrencia ? S.d.recorrencias.find(x => x.id === f.recorrencia) : null;
  const err = k => f.erros[k] ? ' erro' : '';
  const msg = k => f.erros[k] ? `<div class="msg-erro">${f.erros[k]}</div>` : '';
  const apo = !rec && !!f.aporte;
  const titulo = f.ajuste ? 'Ajuste de saldo' : f.confirmando ? 'Confirmar recebimento' : f.id ? (rec ? 'Recebimento' : apo ? 'Aporte' : 'Despesa') : (rec ? 'Novo recebimento' : apo ? 'Novo aporte' : 'Nova despesa');
  let c = '';
  if (!f.id && !f.ajuste && !f.aporte) c += tilesIA('caixa');
  if (!f.id) {
    c += `<div class="seg tipo-seg"><button class="${!rec && !apo ? 'on sai-on' : ''}" data-a="lf-tipo" data-v="despesa">${ic('minus', 'ic-s')}Despesa</button>
      <button class="${rec ? 'on ent-on' : ''}" data-a="lf-tipo" data-v="receita">${ic('plus', 'ic-s')}Recebimento</button>
      <button class="${apo ? 'on apo-on' : ''}" data-a="lf-tipo" data-v="aporte">${ic('wallet', 'ic-s')}Aporte</button></div>`;
    if (apo) c += `<div class="aviso-fixo">${ic('wallet', 'ic-s')}<span>${f.repete === 'mensal' || f.repete === 'anual' ? 'Entra no aporte por mês da projeção.' : 'Para entrar na projeção, escolha Todo mês.'}</span></div>`;
  }
  const anualR = r && r.freq === 'anual';
  if (r && r.aporte) c += `<div class="aviso-fixo">${ic('wallet', 'ic-s')}<span>Aporte nos seus investimentos, ${anualR ? `todo ano em ${MESES_LONGOS[+r.inicio.slice(5) - 1]}, dia ${r.dia}` : `todo dia ${r.dia}`}. Valor padrão ${brl(r.valor)}; ele soma o aporte por mês da projeção na aba Invest.</span></div>`;
  else if (r && r.vinculo && !rec) c += `<div class="aviso-fixo">${ic('repeat', 'ic-s')}<span>Gasto fixo, descontado de ${esc(recPorId().get(r.vinculo)?.descricao || 'um recebimento')} todo mês. Valor padrão ${brl(r.valor)}.</span></div>`;
  else if (r) c += `<div class="aviso-fixo">${ic('repeat', 'ic-s')}<span>${rec ? 'Recebimento' : 'Gasto'} fixo, ${anualR ? `todo ano em ${MESES_LONGOS[+r.inicio.slice(5) - 1]}, dia ${r.dia}` : `todo dia ${r.dia}`}. Valor padrão ${brl(r.valor)}. ${f.virtual ? (anualR ? 'Este ano ainda não foi confirmado.' : 'Este mês ainda não foi confirmado.') : ''}</span></div>`;
  if (f.parcela) c += `<div class="aviso-fixo">${ic('calendar', 'ic-s')}<span>Parcela ${esc(f.parcela)}</span></div>`;
  const comPartes = false;
  const brutoTxt = rec && (f.descontos.length || f.descAberto) ? 'bruto' : '';
  const rotValor = f.repete === 'parcelado' ? 'Valor total' : comPartes ? 'Bruto (soma dos créditos)'
    : ['Valor', brutoTxt, r ? (anualR ? 'deste ano' : 'deste mês') : ''].filter(Boolean).join(' ');
  c += comPartes
    ? `<div class="campo"><div class="lbl">${rotValor}</div><div class="pref grande lido"><span>R$</span><b id="lf-bruto">${NF2.format(somaPartes(f.partes))}</b></div>${msg('valor')}</div>`
    : `<div class="campo"><label for="lf-valor">${rotValor}</label><div class="pref grande${err('valor')}"><span>R$</span><input id="lf-valor" data-lf="valor" inputmode="numeric" value="${f.valor ? NF2.format(f.valor) : ''}" placeholder="0,00"></div>${msg('valor')}</div>`;
  c += secaoDescontos(f);
  const sugest = [...new Set(S.d.lancamentos.filter(l => l.tipo === f.tipo && !l.ajuste).map(l => l.descricao))].slice(-60);
  c += `<div class="campo"><label for="lf-desc">Descrição</label><input id="lf-desc" class="inp" data-lf="descricao" value="${esc(f.descricao)}" placeholder="${rec ? 'Ex.: Salário, Pix do João' : apo ? 'Ex.: Aporte nos investimentos, Tesouro do mês' : 'Ex.: Mercado, Aluguel, iFood'}" list="dl-desc" autocomplete="off">
    <datalist id="dl-desc">${sugest.map(n => `<option value="${esc(n)}">`).join('')}</datalist></div>`;
  if (!f.ajuste && !apo) {
    c += `<div class="campo"><div class="lbl">Categoria</div><div class="chips" style="margin:0">${cats.map(k =>
      `<button class="chip${f.categoria === k.id ? ' on' : ''}" data-a="lf-set" data-k="categoria" data-v="${k.id}" style="--c:${corOk(k.cor) || '#B8B0B0'}"><span class="bol"></span>${esc(k.nome)}</button>`).join('')}
      <button class="chip add" data-a="lf-cat-nova">${ic('plus', 'ic-s')}Categoria</button></div>`;
    if (f.novaCat) {
      c += `<div class="mini-form"><input class="inp" data-lf="novaCat" value="${esc(f.novaCat.nome)}" placeholder="Nome da categoria" autocomplete="off">
        <div class="cores p" style="margin:12px 0">${PALETA.map(cr => `<button class="cor${f.novaCat.cor === cr ? ' on' : ''}" style="--c:${cr}" data-a="lf-cat-cor" data-v="${cr}" aria-label="Cor ${cr}"></button>`).join('')}</div>
        <button class="btn out peq" data-a="lf-cat-ok">Usar esta categoria</button></div>`;
    }
    c += `</div>`;
  }
  c += `<div class="duo"><div class="campo"><label for="lf-data">${noCartao ? 'Data da compra' : 'Data'}</label><input id="lf-data" class="inp" type="date" data-lf="data" value="${esc(f.data)}"></div>
    <div class="campo"><div class="lbl">Situação</div>${vinc ? `<p class="vinc-st">${ic('repeat', 'ic-s')}Baixa com ${esc(vinc.descricao)}</p>` : `<div class="seg mini" style="margin:0">
      <button class="${f.pago ? 'on' : ''}" data-a="lf-pago" data-v="1">${rec ? 'Recebido' : apo ? 'Aplicado' : 'Pago'}</button>
      <button class="${!f.pago ? 'on' : ''}" data-a="lf-pago" data-v="">${rec ? 'A receber' : apo ? 'A aplicar' : 'A pagar'}</button></div>`}</div></div>`;
  if (apo && f.pago && !f.pagoOrig) c += campoInvestimentoAporte(f);
  const recsFixos = rec || apo || f.ajuste ? [] : recebimentosFixos();
  if (recsFixos.length || vinc) {
    c += `<div class="campo"><label for="lf-vinc">Como é pago</label><select id="lf-vinc" class="inp" data-lfv="1">
      <option value="">Por conta própria (conta, Pix ou cartão)</option>${recsFixos.map(x => `<option value="${esc(x.id)}"${f.vinculo === x.id ? ' selected' : ''}>Descontado de: ${esc(x.descricao)} (dia ${x.dia})</option>`).join('')}</select>
      ${vinc ? `<div class="ajuda">Fica pago junto com ${esc(vinc.descricao)}.</div>` : ''}</div>`;
  }
  if (!vinc) {
  c += `<div class="campo"><div class="lbl">${rec ? 'Onde entrou' : apo ? 'De onde sai' : 'Como pagou'}</div><div class="chips" style="margin:0">
    <button class="chip${!f.conta ? ' on' : ''}" data-a="lf-conta" data-v="">Sem conta</button>
    ${contas().map(k => `<button class="chip${f.conta === k.id ? ' on' : ''}" data-a="lf-conta" data-v="${k.id}" style="--c:${corOk(k.cor) || '#B8B0B0'}"><span class="bol"></span>${esc(nomeConta(k))}</button>`).join('')}</div>`;
  if (!rec && !apo && conta?.cartao) {
    c += `<div class="seg mini" style="margin:10px 0 0"><button class="${!f.cartao ? 'on' : ''}" data-a="lf-cartao" data-v="">Débito ou Pix</button>
      <button class="${f.cartao ? 'on' : ''}" data-a="lf-cartao" data-v="1">${ic('card', 'ic-s')}Cartão de crédito</button></div>`;
    if (noCartao) c += `<div class="ajuda">Entra na fatura que vence em <b>${fData(pData(dc))}</b> (fecha dia ${conta.fechamento}, vence dia ${conta.vencimento}).</div>`;
  }
  c += `</div>`;
  }
  if (!f.id) {
    c += `<div class="campo"><div class="lbl">Repetir</div><div class="seg mini" style="margin:0">
      <button class="${f.repete === 'nao' ? 'on' : ''}" data-a="lf-set" data-k="repete" data-v="nao">Uma vez</button>
      <button class="${f.repete === 'mensal' ? 'on' : ''}" data-a="lf-set" data-k="repete" data-v="mensal">Todo mês</button>
      <button class="${f.repete === 'anual' ? 'on' : ''}" data-a="lf-set" data-k="repete" data-v="anual">Todo ano</button>
      <button class="${f.repete === 'parcelado' ? 'on' : ''}" data-a="lf-set" data-k="repete" data-v="parcelado">Parcelado</button></div>`;
    if (f.repete === 'mensal') c += `<div class="ajuda">Todo dia ${+f.data.slice(8, 10)}, a partir de ${MESES_LONGOS[+f.data.slice(5, 7) - 1]}.</div>`;
    if (f.repete === 'anual') c += `<div class="ajuda">Todo ano em ${+f.data.slice(8, 10)} de ${MESES_LONGOS[+f.data.slice(5, 7) - 1]}.</div>`;
    if (f.repete === 'parcelado') {
      const n = +f.vezes || 0;
      c += `<div class="duo" style="margin-top:10px"><div class="pref${err('vezes')}"><input data-lf="vezes" inputmode="numeric" value="${f.vezes || ''}" placeholder="10"><span>vezes</span></div>
        <div class="ajuda" style="margin:0;align-self:center">${n >= 2 && f.valor ? `${n}x de <b>${brl(Math.floor(f.valor * 100 / n) / 100)}</b>` : ''}</div></div>${msg('vezes')}`;
    }
    c += `</div>`;
  }
  c += `<div class="campo"><button class="abre${f.obsAberta ? ' on' : ''}" data-a="lf-obs">${ic('chev', 'ic-s')}Observação</button>
    ${f.obsAberta ? `<textarea class="inp" data-lf="obs" rows="3" style="margin-top:10px;resize:vertical" placeholder="Algo para lembrar">${esc(f.obs)}</textarea>` : ''}</div>`;
  const cab = f.id ? `<button class="icbtn" data-a="lf-excluir" aria-label="Excluir" style="color:var(--danger)">${ic('trash')}</button>` : '';
  let pe;
  if (!f.id) pe = `<button class="btn" data-a="lf-salvar" data-mais="1">Salvar e lançar outro</button><button class="btn pri" data-a="lf-salvar">Salvar</button>`;
  else if (f.recorrencia) pe = anualR ? `<button class="btn" data-a="lf-salvar" data-v="este">Só este ano</button><button class="btn pri" data-a="lf-salvar" data-v="todos">Todos os anos</button>`
    : `<button class="btn" data-a="lf-salvar" data-v="este">Só este mês</button><button class="btn pri" data-a="lf-salvar" data-v="todos">Todos os meses</button>`;
  else pe = `<button class="btn" data-a="lf-duplicar">${ic('copy', 'ic-s')}Duplicar</button><button class="btn pri" data-a="lf-salvar">Salvar</button>`;
  return { titulo, corpo: c, pe, cab };
}

function salvarLanc(alcance, eOutro) {
  const f = LF;
  f.erros = {};
  if (!(f.valor > 0)) f.erros.valor = 'Coloque o valor.';
  if (!f.id && f.repete === 'parcelado' && !(+f.vezes >= 2 && +f.vezes <= 120)) f.erros.vezes = 'De 2 a 120 vezes.';
  if (!pData(f.data)) f.erros.valor = f.erros.valor || 'Data inválida.';
  const aplicando = f.tipo !== 'receita' && !!f.aporte && !!f.pago && !f.pagoOrig;
  f.erroInv = aplicando && invsDoAporte().length && !invsDoAporte().some(i => i.id === f.investimento) ? 'Escolha em qual investimento o aporte foi aplicado.' : '';
  if (f.erroInv) f.erros.investimento = f.erroInv;
  if (Object.keys(f.erros).length) { pintarFolha(); return; }
  const rec = f.tipo === 'receita';
  const cats = [...S.d.categorias, ...f.catsNovas];
  const apo = !rec && !!f.aporte;
  const base = {
    tipo: f.tipo, descricao: f.descricao.trim() || (apo ? 'Aporte nos investimentos' : cats.find(c => c.id === f.categoria)?.nome || (rec ? 'Recebimento' : 'Despesa')),
    valor: round2(f.valor), categoria: f.ajuste ? '' : apo ? 'c-investimentos' : f.categoria, conta: f.conta || '',
    cartao: !rec && !apo && !!f.cartao && !!contaDe(f.conta)?.cartao, data: f.data, pago: !!f.pago, obs: (f.obs || '').trim(),
  };
  if (apo) base.aporte = true;
  const invAp = aplicando ? S.d.investimentos.find(i => i.id === f.investimento) : null;
  if (apo && invAp) base.investimento = invAp.id;
  // o valor que entra no investimento agora: a parcela paga, ou o valor todo
  const valorAp = !invAp ? 0 : !f.id && f.repete === 'parcelado' ? Math.floor(base.valor * 100 / (+f.vezes || 1)) / 100 : base.valor;
  const novoValorInv = invAp ? round2(valorHoje(invAp) + valorAp) : 0;
  if (rec && f.repete !== 'parcelado') {
    const ld = limparDescontos(f);
    if (ld.partes.length) { base.partes = ld.partes; base.valor = somaPartes(ld.partes); }
    if (ld.descontos.length) base.descontos = ld.descontos;
  }
  if (!rec && !apo && f.vinculo && recPorId().get(f.vinculo)) {
    const rr = recPorId().get(f.vinculo);
    Object.assign(base, { vinculo: f.vinculo, conta: rr.conta || base.conta, cartao: false, pago: !!recMat().get(f.vinculo + '|' + ymDe(f.data))?.pago });
  }
  const semDesc = o => { if (!base.partes) delete o.partes; if (!base.descontos) delete o.descontos; if (!base.vinculo) delete o.vinculo; return o; };
  let recFinal = null, ridRec = rec ? f.recorrencia : null;
  const catsNovas = f.catsNovas.filter(c => c.id === f.categoria);
  const novo = !f.id;
  persistir(d => {
    d.categorias.push(...catsNovas);
    if (apo && !d.categorias.some(c => c.id === 'c-investimentos')) d.categorias.push(clone(CATEGORIAS_PADRAO.find(c => c.id === 'c-investimentos')));
    if (invAp) {
      const inv = d.investimentos.find(i => i.id === invAp.id);
      if (inv) Object.assign(inv, { valor: novoValorInv, data_valor: iso(hoje()), atualizado_em: new Date().toISOString() });
      const rr = f.recorrencia && d.recorrencias.find(x => x.id === f.recorrencia);
      if (rr) rr.investimento = invAp.id;
    }
    if (novo) {
      if (f.repete === 'mensal' || f.repete === 'anual') {
        const r = { id: 'r-' + uid(), tipo: base.tipo, descricao: base.descricao, valor: base.valor, categoria: base.categoria, conta: base.conta,
          cartao: base.cartao, obs: base.obs, dia: +f.data.slice(8, 10), inicio: ymDe(f.data), fim: null };
        if (f.repete === 'anual') r.freq = 'anual';
        if (base.partes) r.partes = clone(base.partes);
        if (base.descontos) r.descontos = clone(base.descontos);
        if (base.vinculo) r.vinculo = base.vinculo;
        if (apo) r.aporte = true;
        if (invAp) r.investimento = invAp.id;
        d.recorrencias.push(r);
        const mat = Object.assign({}, base, { recorrencia: r.id, competencia: ymDe(f.data) });
        if (base.pago) d.lancamentos.push(recFinal = materializar(mat)); else recFinal = mat;
        if (rec && f.repete === 'mensal') ridRec = r.id;
      } else if (f.repete === 'parcelado') {
        const n = +f.vezes, cada = Math.floor(base.valor * 100 / n) / 100, g = 'g-' + uid();
        for (let k = 0; k < n; k++) {
          d.lancamentos.push(Object.assign({}, base, { id: uid(), valor: k === n - 1 ? round2(base.valor - cada * (n - 1)) : cada,
            data: somaMeses(f.data, k), parcela: `${k + 1}/${n}`, grupo: g, pago: k === 0 ? base.pago : false }));
        }
      } else {
        d.lancamentos.push(Object.assign({ id: uid() }, base));
        // recebimento de uma vez só (recibo lido): o plano de saúde e os outros descontos conferidos no líquido viram
        // despesas no mesmo dia e na mesma conta, para o caixa bater com o recibo
        if (rec) for (const n of (f.ligadosNovos || []).filter(x => x.sel && x.valor > 0)) {
          d.lancamentos.push({ id: uid(), tipo: 'despesa', descricao: n.descricao, valor: round2(n.valor), categoria: n.categoria || '', conta: base.conta || '', cartao: false,
            data: base.data, pago: !!base.pago, obs: '' });
        }
      }
      if (rec && ridRec && recFinal) { criarLigados(d, f, ridRec, recFinal); baixaVinculados(d, recFinal); }
      return;
    }
    if (f.recorrencia && alcance === 'todos') {
      const r = d.recorrencias.find(x => x.id === f.recorrencia);
      // um fixo do dia 31 aparece no dia 30 num mês de 30 dias: se a data não mudou, o dia do fixo continua o mesmo
      const dia = r && dataNoMes(ymDe(f.data), r.dia) === f.data ? r.dia : +f.data.slice(8, 10);
      if (r) semDesc(Object.assign(r, { descricao: base.descricao, valor: base.valor, categoria: base.categoria, conta: base.conta, cartao: base.cartao, obs: base.obs, dia },
        base.partes ? { partes: clone(base.partes) } : {}, base.descontos ? { descontos: clone(base.descontos) } : {}, base.vinculo ? { vinculo: base.vinculo } : {}));
    }
    const mat = Object.assign({}, base, { recorrencia: f.recorrencia, competencia: f.competencia });
    if (f.virtual) {
      if (alcance === 'este' || base.pago) d.lancamentos.push(recFinal = materializar(mat)); else recFinal = mat;
    } else {
      const x = d.lancamentos.find(y => y.id === f.id);
      if (x) semDesc(Object.assign(x, base));
      recFinal = x;
    }
    if (rec && ridRec && recFinal) { criarLigados(d, f, ridRec, recFinal); baixaVinculados(d, recFinal); }
  }, novo ? (apo && f.repete === 'mensal' ? 'Aporte cadastrado: todo mês, também na projeção' : f.repete === 'mensal' ? 'Fixo cadastrado: aparece todo mês' : f.repete === 'anual' ? 'Fixo cadastrado: aparece todo ano' : f.repete === 'parcelado' ? `${f.vezes} parcelas lançadas` : 'Lançado') : 'Salvo').then(ok => {
    if (!ok) return;
    if (eOutro) {
      LF = Object.assign({}, LF, { id: null, valor: 0, descricao: '', obs: '', obsAberta: false, repete: 'nao', erros: {}, pagoMexido: false, catsNovas: [], partes: [], descontos: [], descAberto: false, recibo: null, ligadosNovos: [], recorrencia: null, virtual: false });
      pintarFolha();
      const v = $('#lf-valor'); if (v) v.focus();
    } else fecharFolha();
  });
}

function excluirLanc() {
  const f = LF;
  const removerReal = (d, id) => { d.lancamentos = d.lancamentos.filter(x => x.id !== id); };
  if (f.recorrencia) {
    // apagar um fixo: só esta vez, parar daqui para frente (fica o que já foi) ou apagar o fixo inteiro com o que ele lançou
    const ym = f.competencia, rid = f.recorrencia;
    const r0 = S.d.recorrencias.find(x => x.id === rid), anual = r0?.freq === 'anual';
    const lancados = S.d.lancamentos.filter(x => x.recorrencia === rid && !x.pulado).length;
    const mes = anual ? `${MESES_LONGOS[+ym.slice(5) - 1]} de ${ym.slice(0, 4)}` : MESES_LONGOS[+ym.slice(5) - 1];
    escolher({
      titulo: 'Apagar fixo', texto: `<b>${esc(f.descricao)}</b> é ${f.tipo === 'receita' ? 'um recebimento' : 'um gasto'} fixo, ${anual ? 'todo ano' : 'todo mês'}. O que você quer apagar?`,
      opcoes: [
        { rotulo: anual ? `Só o de ${ym.slice(0, 4)}` : `Só o de ${mes}`, acao: () => persistir(d => {
          if (f.virtual) d.lancamentos.push(materializar(Object.assign({}, f, { recorrencia: rid, competencia: ym }), { pulado: true }));
          else { const x = d.lancamentos.find(y => y.id === f.id); if (x) x.pulado = true; }
        }, anual ? 'Apagado deste ano' : 'Apagado deste mês') },
        { rotulo: `Parar a partir de ${mes}`, acao: () => persistir(d => {
          const r = d.recorrencias.find(x => x.id === rid);
          if (r) { if (ym <= r.inicio) d.recorrencias = d.recorrencias.filter(x => x.id !== r.id); else r.fim = addYm(ym, -1); }
          d.lancamentos = d.lancamentos.filter(x => !(x.recorrencia === rid && x.competencia >= ym && !x.pago));
        }, 'Fixo encerrado: o que já foi lançado continua') },
        { rotulo: lancados ? `Apagar o fixo e o que ele já lançou (${lancados})` : 'Apagar o fixo', perigo: true, acao: () => persistir(d => {
          d.recorrencias = d.recorrencias.filter(x => x.id !== rid);
          d.lancamentos = d.lancamentos.filter(x => x.recorrencia !== rid);
          // despesas descontadas deste recebimento ficam por conta própria
          for (const x of [...d.recorrencias, ...d.lancamentos]) if (x.vinculo === rid) delete x.vinculo;
        }, 'Fixo apagado') },
      ],
    });
  } else if (f.grupo) {
    escolher({
      titulo: 'Apagar parcela', texto: `<b>${esc(f.descricao)}</b>, parcela ${esc(f.parcela || '')}.`,
      opcoes: [
        { rotulo: 'Só esta parcela', acao: () => persistir(d => removerReal(d, f.id), 'Parcela apagada') },
        { rotulo: 'Esta e as próximas', perigo: true, acao: () => persistir(d => { d.lancamentos = d.lancamentos.filter(x => !(x.grupo === f.grupo && x.data >= f.data)); }, 'Parcelas apagadas') },
      ],
    });
  } else {
    confirmar({ titulo: 'Apagar lançamento?', texto: `<b>${esc(f.descricao)}</b>, ${brl(f.valor)}. Uma cópia fica em Versões anteriores.`, botao: 'Apagar', perigo: true,
      acao: () => persistir(d => removerReal(d, f.id), 'Lançamento apagado') });
  }
}

/* --------- confirmar pagamento, fatura e ajuste */
let PG = null;
// chat: aberto pelo Editar de uma conta que a IA propôs pagar (por cima da conversa, e volta para ela)
function abrirPagar(id, chat, valor) {
  const l = acharLanc(id);
  if (!l) return;
  const r = l.recorrencia ? S.d.recorrencias.find(x => x.id === l.recorrencia) : null;
  PG = { l, valor: valor > 0 ? valor : +l.valor || 0, inv: l.investimento || r?.investimento || '', chat: chat || null };
  if (PG.inv && !S.d.investimentos.some(i => i.id === PG.inv)) PG.inv = '';
  abrirFolha(() => ({
    titulo: ehRec(l) ? 'Confirmar recebimento' : ehAporte(l) ? 'Confirmar aporte' : 'Confirmar pagamento',
    corpo: `<p style="margin:0 0 16px;color:var(--text-2)"><b style="color:var(--text)">${esc(l.descricao)}</b> · ${fData(pData(l.dc || l.data))}${r ? ` · fixo, padrão ${brl(r.valor)}` : ''}</p>
      <div class="campo"><label for="pg-v">Quanto ${ehRec(l) ? 'entrou' : ehAporte(l) ? 'você aplicou' : 'saiu'}</label><div class="pref grande"><span>R$</span><input id="pg-v" data-pg="valor" inputmode="numeric" value="${NF2.format(PG.valor)}"></div>
      ${r ? `<div class="ajuda">Os próximos meses continuam com ${brl(r.valor)}.</div>` : ''}</div>
      ${ehAporte(l) ? campoInvestimentoAporte({ get investimento() { return PG.inv; }, set investimento(x) { PG.inv = x; }, valor: PG.valor, erroInv: PG.erroInv }, 'pg-inv') : ''}`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="pg-ok">${ehRec(l) ? 'Recebi' : ehAporte(l) ? 'Apliquei' : 'Paguei'}</button>`,
  }), null, !!chat);
}
function confirmarPagar() {
  const { l, valor } = PG;
  if (!(valor > 0)) { toast('Coloque o valor.'); return; }
  const apo = ehAporte(l), inv0 = apo && PG.inv ? S.d.investimentos.find(i => i.id === PG.inv) : null;
  if (apo && !inv0 && invsDoAporte().length) { PG.erroInv = 'Escolha em qual investimento o aporte foi aplicado.'; pintarFolha(); return; }
  const chat = PG.chat;
  persistir(d => mutPagar(d, l, valor, inv0), ehRec(l) ? 'Recebimento confirmado' : inv0 ? `Aplicado em ${inv0.nome}` : apo ? 'Aporte confirmado' : 'Pagamento confirmado')
    .then(ok => { if (!ok) return; if (chat) { fecharFolha(false, true); marcarAcaoChat(chat.id, chat.chave); } else fecharFolha(); });
}
// paga (ou recebe) um lançamento, ou o fixo do mês ainda não lançado; com investimento, o aporte soma nele
function mutPagar(d, l, valor, inv0) {
  const novoValor = inv0 ? round2(valorHoje(inv0) + valor) : 0;
  let x;
  const extra = inv0 ? { investimento: inv0.id } : {};
  if (l.virtual) d.lancamentos.push(x = materializar(l, Object.assign({ valor: round2(valor), pago: true }, extra)));
  else { x = d.lancamentos.find(y => y.id === l.id); if (x) Object.assign(x, { pago: true, valor: round2(valor) }, extra); }
  baixaVinculados(d, x);
  if (inv0) {
    const inv = d.investimentos.find(i => i.id === inv0.id);
    if (inv) definirValor(inv, novoValor, iso(hoje()));
    const r = l.recorrencia && d.recorrencias.find(y => y.id === l.recorrencia);
    if (r) r.investimento = inv0.id;
  }
}
function pagarFatura(k) {
  const [conta, dc] = k.split('|');
  const f = faturasDe(lancamentosEntre(ymDe(dc), ymDe(dc))).find(x => x.k === k);
  if (!f) return;
  confirmar({
    titulo: 'Pagar fatura', botao: 'Paguei a fatura',
    texto: `Fatura <b>${esc(nomeConta(contaDe(conta)))}</b> que vence em ${fData(pData(dc))}: <b>${brl(f.total)}</b> em ${plural(f.itens.length, 'compra', 'compras')}. Todas ficam pagas.`,
    acao: () => persistir(d => {
      for (const l of f.itens) {
        if (l.pago) continue;
        if (l.virtual) d.lancamentos.push(materializar(l, { pago: true }));
        else { const x = d.lancamentos.find(y => y.id === l.id); if (x) x.pago = true; }
      }
    }, 'Fatura paga'),
  });
}
let AJ = null;
// o saldo pode estar negativo: o campo mostra o sinal, e Positivo/Negativo troca (no teclado numérico do celular não há "−")
const ajTexto = () => (AJ.neg && AJ.abs ? '-' : '') + (AJ.abs || AJ.neg ? NF2.format(AJ.abs) : '');
function abrirAjuste() {
  const v = round2(saldoCaixa());
  AJ = { abs: Math.abs(v), neg: v < 0, get valor() { return this.neg ? -this.abs : this.abs; } };
  abrirFolha(() => ({
    titulo: 'Ajustar saldo',
    corpo: `<div class="campo"><label for="aj-v">Quanto você tem em conta hoje, somando tudo</label><div class="pref grande"><span>R$</span><input id="aj-v" data-aj="valor" inputmode="numeric" value="${ajTexto()}"></div>
      <div class="seg aj-sinal">${[['+', 'Positivo'], ['-', 'Negativo']].map(([k, n]) => `<button class="${(k === '-') === AJ.neg ? 'on' : ''}" data-a="aj-sinal" data-v="${k}">${n}</button>`).join('')}</div>
      <div class="ajuda">A diferença entra como "Ajuste de saldo", fora das entradas, saídas e categorias.</div></div>`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="aj-ok">Ajustar</button>`,
  }));
}
function confirmarAjuste() {
  const dif = round2(AJ.valor - saldoCaixa());
  if (Math.abs(dif) < 0.01) { fecharFolha(); toast('O saldo já está certo.'); return; }
  persistir(d => {
    d.lancamentos.push({ id: uid(), tipo: dif > 0 ? 'receita' : 'despesa', descricao: 'Ajuste de saldo', valor: Math.abs(dif), categoria: '', conta: '', cartao: false,
      data: iso(hoje()), pago: true, ajuste: true, obs: '' });
  }, 'Saldo ajustado').then(ok => { if (ok) fecharFolha(); });
}

/* --------- categoria */
let FC = null;
function abrirCategoria(id, tipo) {
  const c = id && S.d.categorias.find(x => x.id === id);
  const usadas = S.d.categorias.map(x => x.cor);
  FC = c ? clone(c) : { id: null, nome: '', tipo: tipo || 'despesa', cor: CORES_BANCO.find(x => !usadas.includes(x)) || CORES_BANCO[0] };
  FC.erro = '';
  abrirFolha(() => {
    const n = FC.id ? S.d.lancamentos.filter(l => l.categoria === FC.id).length + S.d.recorrencias.filter(r => r.categoria === FC.id).length : 0;
    return {
      titulo: FC.id ? 'Editar categoria' : 'Nova categoria',
      cab: FC.id ? `<button class="icbtn" data-a="cat-excluir" aria-label="Excluir" style="color:var(--danger)">${ic('trash')}</button>` : '',
      corpo: `${FC.id ? '' : `<div class="seg"><button class="${FC.tipo === 'despesa' ? 'on' : ''}" data-a="cat-tipo" data-v="despesa">Gasto</button><button class="${FC.tipo === 'receita' ? 'on' : ''}" data-a="cat-tipo" data-v="receita">Recebimento</button></div>`}
        <div class="campo"><label for="cat-nome">Nome</label><input id="cat-nome" class="inp${FC.erro ? ' erro' : ''}" data-fc="nome" value="${esc(FC.nome)}" placeholder="${FC.tipo === 'despesa' ? 'Ex.: Farmácia, Viagens' : 'Ex.: Aluguel recebido'}" autocomplete="off">${FC.erro ? `<div class="msg-erro">${FC.erro}</div>` : ''}</div>
        <div class="campo"><div class="lbl">Cor</div><div class="cores p">${PALETA.map(cr => `<button class="cor${FC.cor === cr ? ' on' : ''}" style="--c:${cr}" data-a="cat-cor" data-v="${cr}" aria-label="Cor ${cr}">${FC.cor === cr ? ic('check', 'ic-s') : ''}</button>`).join('')}</div></div>
        ${n ? `<p style="color:var(--muted);margin:0">${plural(n, 'lançamento usa', 'lançamentos usam')} esta categoria.</p>` : ''}`,
      pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="cat-salvar">Salvar</button>`,
    };
  });
}

/* ------------------------------------------------------------------ imagens e leitura por IA */
const DEMO_FOTOS = {};
const fotoSrc = n => DEMO ? (DEMO_FOTOS[n] || '') : 'fotos/' + encodeURIComponent(n);

function lerArquivo(file) {
  return new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = () => rej(new Error('Não deu para ler o arquivo.')); r.readAsDataURL(file); });
}
async function imagemJPG(file, max = 1600) {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error('Não deu para abrir a imagem.')); i.src = url; });
    const k = Math.min(1, max / Math.max(img.naturalWidth, img.naturalHeight));
    const cv = document.createElement('canvas');
    cv.width = Math.max(1, Math.round(img.naturalWidth * k)); cv.height = Math.max(1, Math.round(img.naturalHeight * k));
    const g = cv.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, cv.width, cv.height); g.drawImage(img, 0, 0, cv.width, cv.height);
    return cv.toDataURL('image/jpeg', 0.86);
  } finally { URL.revokeObjectURL(url); }
}
function escolherArquivo(accept, capture) {
  return new Promise(res => {
    const inp = document.createElement('input');
    inp.type = 'file'; inp.accept = accept; inp.style.display = 'none';
    if (capture) inp.setAttribute('capture', 'environment');
    inp.onchange = () => { res(inp.files && inp.files[0]); inp.remove(); };
    document.body.appendChild(inp); inp.click();
  });
}
async function enviarFoto(file) {
  const jpg = await imagemJPG(file);
  const r = await api.foto(jpg);
  if (DEMO) DEMO_FOTOS[r.arquivo] = jpg;
  return r.arquivo;
}

/* --------- imagens no formulário de investimento */
// Imagens guardadas com o investimento: só guardar, sem IA (como combinado). Quem lê com IA é o Ler com IA do Adicionar.
function fotosFormHTML() {
  const fotos = F.fotos || [];
  return `<div class="campo"><div class="lbl">Imagens guardadas</div><div class="fotos">
    ${fotos.map(n => `<div class="foto"><img src="${fotoSrc(n)}" alt="Imagem do investimento" data-a="foto-ver" data-v="${esc(n)}">
      <button class="foto-x" data-a="f-foto-rm" data-v="${esc(n)}" aria-label="Remover imagem">${ic('x', 'ic-s')}</button></div>`).join('')}
    <button class="foto add" data-a="f-foto-add">${ic('camera')}<span>Guardar</span></button></div>
    <div class="ajuda">Comprovante, print ou extrato.</div></div>`;
}
function verFoto(n) {
  abrirFolha(() => ({ titulo: 'Imagem', corpo: `<img class="foto-grande" src="${fotoSrc(n)}" alt="Imagem do investimento">` }), null, true);
}
function bancoPorNome(nome, d = S.d) {
  const n = semAcento(nome);
  if (!n) return null;
  return d.bancos.find(b => semAcento(b.nome) === n) || d.bancos.find(b => semAcento(b.nome).includes(n) || n.includes(semAcento(b.nome)));
}
const semAcento = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();

/* --------- leitor por IA (caixa e investimentos) */
let IAS = null;
/* ------------------------------------------------------------------ Falar (como no CronologIA e no ResolvIA) */
// O microfone grava PCM cru, 16 kHz, 16 bits, mono (o que a fala para texto do Home Assistant recebe, igual ao Assist).
// O servidor manda para o assistente de voz preferido e o texto passa pela mesma leitura por IA de uma mensagem colada.
const VOZ_TAXA = 16000, VOZ_MAX_S = 120;
class Gravador {
  constructor(aoNivel) { this.aoNivel = aoNivel; this.pedacos = []; this.total = 0; this.taxa = VOZ_TAXA; }
  async start() {
    const md = navigator.mediaDevices;
    if (!md || !md.getUserMedia) throw Object.assign(new Error('sem api'), { name: 'NoApi' });
    this.stream = await md.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
    const AC = window.AudioContext || window.webkitAudioContext;
    try { this.ctx = new AC({ sampleRate: VOZ_TAXA }); } catch (e) { this.ctx = new AC(); } // alguns navegadores só gravam na taxa deles: reamostra no fim
    if (this.ctx.state === 'suspended') await this.ctx.resume().catch(() => {});
    this.taxa = this.ctx.sampleRate;
    this.src = this.ctx.createMediaStreamSource(this.stream);
    this.no = this.ctx.createScriptProcessor(4096, 1, 1);
    this.no.onaudioprocess = e => {
      const d = e.inputBuffer.getChannelData(0);
      this.pedacos.push(new Float32Array(d));
      this.total += d.length;
      let s = 0;
      for (let i = 0; i < d.length; i += 4) s += d[i] * d[i];
      if (this.aoNivel) this.aoNivel(Math.min(1, Math.sqrt(s / (d.length / 4)) * 5));
    };
    this.src.connect(this.no);
    this.no.connect(this.ctx.destination); // a saída fica muda; só mantém o nó rodando
  }
  segundos() { return this.total / this.taxa; }
  stop() {
    this._fechar();
    const tudo = new Float32Array(this.total);
    let o = 0;
    for (const c of this.pedacos) { tudo.set(c, o); o += c.length; }
    this.pedacos = [];
    const k = this.taxa / VOZ_TAXA, n = Math.floor(tudo.length / k), out = new Int16Array(n);
    for (let i = 0; i < n; i++) {
      // a média de cada janela: um passa-baixa simples quando o navegador gravou a 44,1/48 kHz
      const a = Math.floor(i * k), b = Math.max(a + 1, Math.min(tudo.length, Math.floor((i + 1) * k)));
      let s = 0;
      for (let j = a; j < b; j++) s += tudo[j];
      const v = Math.max(-1, Math.min(1, s / (b - a)));
      out[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
    }
    return out;
  }
  cancel() { this._fechar(); this.pedacos = []; this.total = 0; }
  _fechar() {
    try { if (this.no) this.no.onaudioprocess = null; if (this.src) this.src.disconnect(); if (this.no) this.no.disconnect(); } catch (e) { /* já fechado */ }
    if (this.stream) for (const t of this.stream.getTracks()) t.stop();
    if (this.ctx && this.ctx.state !== 'closed') this.ctx.close().catch(() => {});
    this.stream = null; this.no = null; this.src = null;
  }
}
// na prévia, sem microfone: finge que ouviu, para mostrar o caminho todo
class GravadorSimulado {
  constructor(aoNivel) { this.aoNivel = aoNivel; this.t0 = 0; }
  async start() { this.t0 = Date.now(); this.iv = setInterval(() => this.aoNivel && this.aoNivel(0.2 + Math.random() * 0.6), 120); }
  segundos() { return (Date.now() - this.t0) / 1000; }
  stop() { clearInterval(this.iv); return new Int16Array(Math.round(VOZ_TAXA * Math.max(1, this.segundos()))); }
  cancel() { clearInterval(this.iv); }
}
function erroMicrofone(err) {
  const n = (err && err.name) || '';
  if (n === 'NotAllowedError' || n === 'SecurityError') return 'O microfone está bloqueado. Permita o microfone para o Home Assistant (no navegador, no cadeado ao lado do endereço; no app do celular, nas permissões do app Home Assistant) e tente de novo.';
  if (n === 'NotFoundError' || n === 'OverconstrainedError') return 'Não achei um microfone neste aparelho.';
  if (n === 'NotReadableError') return 'O microfone está sendo usado por outro app. Feche o outro e tente de novo.';
  if (n === 'NoApi') return 'Este navegador não deixa usar o microfone aqui. Abra o Home Assistant pelo endereço com https (como o do Nabu Casa) ou pelo app.';
  return `Não consegui abrir o microfone (${(err && err.message) || n || 'erro'}).`;
}

const vozPronta = () => iaOn() && !!(S.voz && S.voz.pronta) && (DEMO || !S.ia || S.ia.pronta !== false);
function carregarVoz() {
  if (!iaOn()) { S.voz = null; return; }
  api.vozStatus().then(v => { S.voz = v; if (!FOLHA) render(); }).catch(e => { S.voz = { pronta: false, motivo: e.message }; });
}
const botaoFalar = () => vozPronta() ? `<button class="mic-top" data-a="falar" aria-label="Falar: lançar falando" title="Falar">${ic('mic')}</button>` : '';

let GRAV = null, gravTimer = null, gravNivel = 0;
async function comecarFala() {
  if (GRAV || !IAS) return;
  Object.assign(IAS, { etapa: 'voz', rec: 'starting', secs: 0, erro: '' });
  pintarFolha();
  const g = DEMO && !(navigator.mediaDevices && navigator.mediaDevices.getUserMedia) ? new GravadorSimulado(l => (gravNivel = l)) : new Gravador(l => (gravNivel = l));
  GRAV = g;
  try { await g.start(); }
  catch (err) {
    g.cancel();
    if (GRAV === g) GRAV = null;
    if (DEMO) { // na prévia, sem permissão de microfone: segue simulado
      const sim = new GravadorSimulado(l => (gravNivel = l)); GRAV = sim; await sim.start();
    } else { if (IAS && IAS.etapa === 'voz') { IAS.rec = 'off'; IAS.erro = erroMicrofone(err); pintarFolha(); } return; }
  }
  if (!IAS || IAS.etapa !== 'voz') { if (GRAV) GRAV.cancel(); GRAV = null; return; }
  IAS.rec = 'on'; pintarFolha();
  clearInterval(gravTimer);
  gravTimer = setInterval(() => {
    if (!GRAV) return clearInterval(gravTimer);
    const secs = GRAV.segundos();
    const m = $('.voz-mic'), t = $('.voz-tempo');
    if (m) m.style.setProperty('--lvl', gravNivel.toFixed(2));
    if (t) t.textContent = `${Math.floor(secs / 60)}:${String(Math.floor(secs % 60)).padStart(2, '0')}`;
    if (secs >= VOZ_MAX_S) terminarFala();
  }, 120);
}
function pararFala() { clearInterval(gravTimer); if (GRAV) GRAV.cancel(); GRAV = null; }
async function terminarFala() {
  const g = GRAV;
  if (!g || !IAS) return;
  clearInterval(gravTimer); GRAV = null;
  const pcm = g.stop();
  if (pcm.length < VOZ_TAXA * 0.4) { IAS.rec = 'off'; IAS.erro = 'Não ouvi nada. Toque no microfone e fale.'; pintarFolha(); return; }
  IAS.etapa = 'transcrevendo'; IAS.erro = ''; pintarFolha();
  try {
    const r = await api.vozTexto(pcm);
    if (!IAS) return;
    IAS.texto = r.texto; IAS.ouvido = r.texto;
    iaLer();
  } catch (e) {
    if (!IAS) return;
    Object.assign(IAS, { etapa: 'voz', rec: 'off', erro: e.message || 'Não consegui transcrever.' });
    pintarFolha();
  }
}
function telaFala() {
  const s = IAS, on = s.rec === 'on', v = S.voz || {};
  const ex = s.dica === 'invest' ? '<i>“Apliquei 2 mil num CDB do Inter a 110% do CDI, vence em março de 2028”</i> ou <i>“Paguei a luz, 180 reais”</i>'
    : '<i>“Gastei 45 no mercado hoje no cartão do Nubank”</i>, <i>“Tenho que pagar o IPVA dia 10”</i> ou <i>“Apliquei 2 mil no CDB do Inter”</i>';
  return {
    titulo: 'Falar',
    corpo: `<div class="voz${on ? ' on' : ''}">
        <button class="voz-mic" style="--lvl:0" data-a="fala-mic" aria-label="${on ? 'Pronto: enviar o que falei' : 'Começar a falar'}"><span class="voz-anel"></span>${ic(on ? 'check' : 'mic')}</button>
        <div class="voz-estado">${on ? `<b>Ouvindo…</b> <span class="voz-tempo">0:00</span>` : s.rec === 'starting' ? 'Abrindo o microfone…' : 'Toque no microfone e fale'}</div>
        <p class="voz-dica">${on ? 'Toque de novo quando terminar.' : `Por exemplo: ${ex}.`}</p>
      </div>
      ${s.erro ? `<div class="msg-erro">${esc(s.erro)}</div>` : ''}
      <p class="nota" style="text-align:center">Você confere antes de lançar.</p>`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="fala-ok"${on ? '' : ' disabled'}>${ic('ia', 'ic-s')}Pronto</button>`,
  };
}
const ouvidoHTML = s => s.ouvido ? `<div class="ouvido">${ic('mic', 'ic-s')}<span>“${esc(s.ouvido)}”</span></div>` : '';

/* ------------------------------------------------------------------ Conversar com a IA (o balão ao lado do microfone) */
// A conversa fica guardada no app (as últimas mensagens). A IA vê os dados e o que está na tela aberta. Quando a pessoa pede
// para lançar, pagar ou atualizar um saldo, a IA propõe e o cartão da ação pede Confirmar; Editar abre a janela de sempre
// (a conferência da leitura por IA ou a de pagar) por cima da conversa, e volta para ela.
let CH = null, CHG = null, chTimer = null;
const chatPronto = () => iaOn() && (DEMO || !S.ia || S.ia.pronta !== false);
const botaoChat = () => chatPronto() ? `<button class="mic-top" data-a="chat" aria-label="Conversar com a IA" title="Conversar com a IA">${ic('chat')}</button>` : '';
const CH_SUGESTOES = {
  inicio: ['Como estão minhas finanças este mês?', 'Quais contas vencem esta semana?', 'Gastei 45 no mercado'],
  caixa: ['Onde eu mais gastei este mês?', 'Quais contas vencem esta semana?', 'Paguei a luz'],
  investimentos: ['Quanto rende a carteira por mês?', 'O que vence primeiro?', 'Apliquei 500 na reserva'],
  mais: ['O que dá para fazer neste app?', 'Gastei 45 no mercado', 'Quais contas vencem esta semana?'],
};
function abrirChat() {
  if (CH) return;
  CH = { msgs: null, texto: '', enviando: false, erro: '', rec: 'off', limpar: false };
  abrirFolha(montarChat, () => { pararDitado(); CH = null; });
  const s = CH;
  api.chat().then(r => { if (CH !== s) return; s.msgs = r.mensagens || []; pintarFolha(1e9); focarChat(); })
    .catch(e => { if (CH !== s) return; s.msgs = []; s.erro = 'Não consegui abrir a conversa. ' + (e.message || ''); pintarFolha(); });
}
// no celular o teclado só abre quando a pessoa toca no campo (senão cobre a conversa)
function focarChat() { requestAnimationFrame(() => { const t = $('#ch-txt'); if (t && !matchMedia('(pointer: coarse)').matches) t.focus(); }); }
function ajustarAlturaChat(t) { t.style.height = 'auto'; t.style.height = Math.min(t.scrollHeight, 132) + 'px'; }
// o que a IA escreve: **negrito**, listas com "- " e parágrafos; nada de HTML vindo dela
function fmtIA(t) {
  let html = '', lista = false;
  for (const l of esc(t || '').replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').split('\n')) {
    const m = /^\s*[-•*]\s+(.*)$/.exec(l);
    if (m) { if (!lista) { html += '<ul>'; lista = true; } html += `<li>${m[1]}</li>`; continue; }
    if (lista) { html += '</ul>'; lista = false; }
    if (l.trim()) html += `<p>${l}</p>`;
  }
  return html + (lista ? '</ul>' : '');
}
const CH_FEITO = { lancamentos: 'Lançado', investimentos: 'Atualizado', pagar: 'Pago' };
// feito: o cartão já confirmado não recalcula o antes → depois (o valor de hoje já mudou)
function linhasAcaoChat(g, lista, feito) {
  const li = (t, sub, v, cls) => `<li><span>${t}${sub ? `<small>${sub}</small>` : ''}</span><b${cls ? ` class="${cls}"` : ''}>${v}</b></li>`;
  if (g === 'lancamentos') return lista.map(it => li(esc(it.descricao) + (it.parcelas_total ? ` · ${it.parcela_atual}/${it.parcelas_total}` : ''),
    [it.data === iso(hoje()) ? 'hoje' : fData(pData(it.data)), catDe(it.categoria)?.nome, it.cartao ? 'no cartão' : '', it.situacao === 'pendente' ? (it.tipo === 'receita' ? 'a receber' : 'a pagar') : ''].filter(Boolean).map(esc).join(' · '),
    brl(it.valor), it.tipo === 'receita' ? 'ent' : 'sai')).join('');
  if (g === 'investimentos') return lista.map(it => {
    const ex = it.existente && S.d.investimentos.find(i => i.id === it.existente);
    if (ex && it.aporte > 0 && !(it.valor > 0)) return li(`Aplicar em ${esc(ex.nome)}`, feito ? '' : `${brl(valorHoje(ex))} → ${brl(valorHoje(ex) + it.aporte)}`, '+ ' + brl(it.aporte), 'ent');
    if (ex) return li(`Saldo de ${esc(ex.nome)}`, feito ? '' : `hoje ${brl(valorHoje(ex))}`, brl(it.valor));
    return li(`Novo: ${esc(it.nome)}`, esc([it.banco, rotuloTaxa(it)].filter(Boolean).join(' · ')), brl(it.valor || it.aporte));
  }).join('');
  return lista.map(it => li(esc(it.descricao), `vence ${fDataC(pData(it.vencimento))}${Math.abs(it.valor - it.valor_conta) > 0.005 ? ` · conta de ${brl(it.valor_conta)}` : ''}`, brl(it.valor), 'sai')).join('');
}
function cartaoAcaoChat(m, g, i) {
  const chave = i == null ? g : `${g}.${i}`;
  const est = (m.estado || {})[chave];
  const lista = i == null ? m.acoes[g] : [m.acoes[g][i]];
  const titulo = g === 'pagar' ? (lista[0].tipo === 'fatura' ? 'Pagar fatura' : 'Pagar conta') : g === 'lancamentos' ? (lista.length > 1 ? `Lançar ${lista.length}` : 'Lançar') : 'Investimentos';
  const pe = est === 'feito' ? `<p class="ch-feito">${ic('check', 'ic-s')}${CH_FEITO[g]}</p>` : est === 'dispensado' ? '<p class="ch-feito off">Deixado de lado</p>'
    : `<div class="ch-bts"><button class="btn" data-a="ch-editar" data-id="${esc(m.id)}" data-g="${chave}">Editar</button><button class="btn pri" data-a="ch-ok" data-id="${esc(m.id)}" data-g="${chave}">Confirmar</button></div>`;
  return `<div class="ch-acao${est ? ' ' + est : ''}" data-g="${chave}"><p class="ch-acao-t">${titulo}</p><ul class="ch-itens">${linhasAcaoChat(g, lista, est === 'feito')}</ul>${pe}</div>`;
}
function acoesChatHTML(m) {
  const a = m.acoes || {};
  return [a.lancamentos?.length ? cartaoAcaoChat(m, 'lancamentos') : '', a.investimentos?.length ? cartaoAcaoChat(m, 'investimentos') : '',
    ...(a.pagar || []).map((_, i) => cartaoAcaoChat(m, 'pagar', i))].join('');
}
function montarChat() {
  const s = CH, on = s.rec === 'on', ocupado = on || s.rec === 'starting' || s.rec === 'transcrevendo';
  let corpo;
  if (!s.msgs) corpo = '<div class="ia-lendo"><span class="giro"></span><p>Abrindo a conversa…</p></div>';
  else {
    const vazio = s.msgs.length ? '' : `<div class="ch-vazio"><p>Pergunte sobre o que está na tela, peça para lançar, pagar ou atualizar um saldo, ou converse sobre outro assunto.</p>
      <div class="ch-sug">${(CH_SUGESTOES[S.ui.tab] || CH_SUGESTOES.inicio).map(t => `<button class="chip" data-a="ch-sug" data-v="${esc(t)}">${esc(t)}</button>`).join('')}</div></div>`;
    const msgs = s.msgs.map(m => m.papel === 'eu'
      ? `<div class="ch-msg eu"><div class="ch-bolha">${m.fala ? ic('mic', 'ic-s') : ''}${esc(m.texto).replace(/\n/g, '<br>')}</div></div>`
      : `<div class="ch-msg ia"><div class="ch-bolha">${fmtIA(m.texto)}</div>${acoesChatHTML(m)}</div>`).join('');
    corpo = `<div class="ch-lista">${vazio}${msgs}${s.enviando ? '<div class="ch-msg ia"><div class="ch-bolha ch-pensando" aria-label="Pensando"><span></span><span></span><span></span></div></div>' : ''}</div>`;
  }
  const ph = on ? 'Ouvindo… toque no visto quando terminar' : s.rec === 'starting' ? 'Abrindo o microfone…' : s.rec === 'transcrevendo' ? 'Transcrevendo…' : 'Escreva para a IA';
  const pe = s.limpar
    ? '<div class="ch-pe ch-pe-limpar"><p>Apagar a conversa?</p><div class="ch-bts"><button class="btn" data-a="ch-limpar-nao">Cancelar</button><button class="btn perigo" data-a="ch-limpar-sim">Apagar</button></div></div>'
    : `<div class="ch-pe">${s.erro ? `<div class="msg-erro">${esc(s.erro)}</div>` : ''}<div class="ch-campo">
        ${vozPronta() ? `<button class="icbtn ch-mic${on ? ' on' : ''}" data-a="ch-mic" aria-label="${on ? 'Pronto: enviar o que falei' : 'Falar'}"${s.rec === 'transcrevendo' || s.enviando ? ' disabled' : ''}>${ic(on ? 'check' : 'mic')}</button>` : ''}
        <textarea id="ch-txt" data-ch="texto" rows="1" enterkeyhint="send" aria-label="Mensagem para a IA" placeholder="${ph}"${ocupado ? ' disabled' : ''}>${esc(s.texto)}</textarea>
        <button class="icbtn ch-env" data-a="ch-enviar" aria-label="Enviar"${s.enviando || ocupado || !s.texto.trim() ? ' disabled' : ''}>${ic('send')}</button></div></div>`;
  return {
    titulo: 'Conversar com a IA',
    cab: s.msgs && s.msgs.length ? `<button class="icbtn" data-a="ch-limpar" aria-label="Apagar a conversa" title="Apagar a conversa">${ic('trash')}</button>` : '',
    corpo, pe,
    depois: el => { const t = $('#ch-txt', el); if (t) ajustarAlturaChat(t); },
  };
}
// o texto da tela que a pessoa está vendo vai junto: "sobre o que está aqui" funciona
function textoTela() {
  const app = $('#app');
  return app ? app.innerText.replace(/[ \t]+/g, ' ').replace(/\n\s*\n+/g, '\n').trim().slice(0, 3000) : '';
}
async function enviarChat(texto, fala) {
  const s = CH;
  texto = String(texto || '').trim();
  if (!s || s.enviando || !texto || !s.msgs) return;
  const temp = { id: 'enviando', papel: 'eu', texto, fala: !!fala };
  Object.assign(s, { msgs: [...s.msgs, temp], enviando: true, erro: '', texto: '', limpar: false });
  pintarFolha(1e9);
  try {
    const r = await api.chatEnviar({ texto, tela: textoTela(), aba: S.ui.tab, fala: !!fala });
    if (CH !== s) return;
    s.msgs = r.mensagens || [];
  } catch (e) {
    if (CH !== s) return;
    s.msgs = s.msgs.filter(m => m !== temp);
    s.texto = texto; // o que foi escrito (ou falado) volta para o campo, para mandar de novo
    s.erro = e.message || 'Não consegui falar com a IA.';
  }
  s.enviando = false;
  pintarFolha(1e9);
}
async function comecarDitado() {
  if (!CH || CHG || CH.rec !== 'off') return;
  Object.assign(CH, { rec: 'starting', erro: '' });
  pintarFolha();
  const s = CH;
  let g = DEMO && !(navigator.mediaDevices && navigator.mediaDevices.getUserMedia) ? new GravadorSimulado() : new Gravador();
  CHG = g;
  try { await g.start(); }
  catch (err) {
    g.cancel(); CHG = null;
    if (!DEMO) { if (CH === s) { s.rec = 'off'; s.erro = erroMicrofone(err); pintarFolha(); } return; }
    g = new GravadorSimulado(); CHG = g; await g.start(); // na prévia, sem microfone: segue simulado
  }
  if (CH !== s || CHG !== g) { g.cancel(); if (CHG === g) CHG = null; return; }
  s.rec = 'on'; pintarFolha();
  clearInterval(chTimer);
  chTimer = setInterval(() => {
    if (!CHG) return clearInterval(chTimer);
    const sec = CHG.segundos(), t = $('#ch-txt');
    if (t) t.placeholder = `Ouvindo… ${Math.floor(sec / 60)}:${String(Math.floor(sec % 60)).padStart(2, '0')} · toque no visto quando terminar`;
    if (sec >= VOZ_MAX_S) terminarDitado();
  }, 250);
}
function pararDitado() { clearInterval(chTimer); if (CHG) CHG.cancel(); CHG = null; }
async function terminarDitado() {
  const g = CHG, s = CH;
  if (!g || !s) return;
  clearInterval(chTimer); CHG = null;
  const pcm = g.stop();
  if (pcm.length < VOZ_TAXA * 0.4) { s.rec = 'off'; s.erro = 'Não ouvi nada. Toque no microfone e fale.'; pintarFolha(); return; }
  s.rec = 'transcrevendo'; pintarFolha();
  try {
    const r = await api.vozTexto(pcm);
    if (CH !== s) return;
    s.rec = 'off';
    if (!String(r.texto || '').trim()) { s.erro = 'Não ouvi nada. Toque no microfone e fale.'; pintarFolha(); return; }
    enviarChat(r.texto, true);
  } catch (e) {
    if (CH !== s) return;
    s.rec = 'off'; s.erro = e.message || 'Não consegui transcrever.'; pintarFolha();
  }
}
// ---- as ações que a IA propôs: Confirmar faz direto; Editar abre a janela de sempre por cima da conversa
function acaoChat(mid, chave) {
  const m = CH && (CH.msgs || []).find(x => x.id === mid);
  const [g, i] = String(chave || '').split('.');
  if (!m || !m.acoes || !(m.acoes[g] || []).length || (m.estado || {})[chave]) return null;
  const lista = i == null ? m.acoes[g] : [m.acoes[g][+i]].filter(Boolean);
  return lista.length ? { m, g, chave, lista } : null;
}
function marcarAcaoChat(mid, chave) {
  const marcarAqui = () => { const m = CH && (CH.msgs || []).find(x => x.id === mid); if (m) { m.estado = Object.assign({}, m.estado, { [chave]: 'feito' }); pintarFolha(); } };
  marcarAqui();
  return api.chatAcao(mid, chave, 'feito').then(r => { if (CH && r && r.mensagens) { CH.msgs = r.mensagens; pintarFolha(); } }).catch(() => { /* feito nos dados; o cartão fica marcado aqui */ });
}
// os lançamentos e investimentos propostos passam pelo mesmo caminho da leitura por IA (conta, categoria, repetidos, parcelas)
function iasDoChat(a) {
  IAS = { dica: a.g === 'investimentos' ? 'invest' : 'caixa', etapa: 'revisao', rec: 'off', arquivo: null, texto: '', erro: '', conta: '', cartao: false,
    situacao: 'auto', futuras: true, ouvido: '', saldos: false, pessoa: '', soInvest: false, so: '',
    itens: a.g === 'lancamentos' ? clone(a.lista).map(it => Object.assign({ marcado: true }, it)) : [],
    invs: a.g === 'investimentos' ? clone(a.lista).map(it => Object.assign({ marcado: true }, it, { dono: donoDe(it.dono) })) : [],
    chat: { id: a.m.id, chave: a.chave } };
  if (IAS.itens.length) prepararRevisaoCaixa();
  return IAS;
}
function editarAcaoChat(mid, chave) {
  const a = acaoChat(mid, chave);
  if (!a) return;
  if (a.g === 'pagar') { if (!a.lista[0].id.startsWith('f:') && acharLanc(a.lista[0].id)) abrirPagar(a.lista[0].id, { id: mid, chave }, a.lista[0].valor); else pagarDoChat(a); return; }
  iasDoChat(a);
  abrirFolha(montarIA, () => { IAS = null; }, true);
}
function confirmarAcaoChat(mid, chave) {
  const a = acaoChat(mid, chave);
  if (!a) return;
  if (a.g === 'pagar') { pagarDoChat(a); return; }
  const s = iasDoChat(a);
  // parece repetido (já tem um igual lançado): mostra a conferência em vez de lançar direto
  if (s.itens.some(i => i.dup)) { abrirFolha(montarIA, () => { IAS = null; }, true); return; }
  const ml = s.itens.filter(i => i.marcado), mi = s.invs.filter(i => i.marcado);
  const msg = ml.length ? (ml.length > 1 ? `${ml.length} lançamentos lançados` : 'Lançado') : mi.length > 1 ? 'Investimentos atualizados' : mi[0]?.aporte > 0 && !(mi[0]?.valor > 0) ? 'Aporte aplicado' : 'Investimento atualizado';
  persistir(d => { if (ml.length) aplicarIACaixa(d, ml); if (mi.length) aplicarIAInvest(d, mi); }, msg)
    .then(ok => { if (IAS === s) IAS = null; if (ok) marcarAcaoChat(mid, chave); });
}
// na prévia, sem IA: respostas de exemplo com os dados da tela (como a IA simulada do servidor, chat.simulado)
const CHAT_DEMO = [];
function chatDemo(texto) {
  const t = semAcento(texto), hj = iso(hoje()), ym = hj.slice(0, 7);
  const valor = (x => x ? parseNum(x[1]) * (x[2] ? 1000 : 1) : 0)(/(\d+(?:[.,]\d{1,2})?)\s*(mil\b)?/.exec(t));
  const abertas = lancamentosEntre(addYm(ym, -1), addYm(ym, 1)).filter(l => !l.pago && l.tipo !== 'receita' && !l.ajuste);
  const conta = /\bpaguei\b/.test(t) && abertas.find(l => t.includes(semAcento(l.descricao)));
  if (conta) {
    const v = (x => x ? parseNum(x[1]) : 0)(/(\d+(?:[.,]\d{1,2})?)/.exec(t.split(semAcento(conta.descricao))[1] || ''));
    return { texto: `Certo: marco **${conta.descricao}** como paga. Confira e confirme.`,
      acoes: { pagar: [{ id: conta.id, descricao: conta.descricao, vencimento: conta.dc || conta.data, valor_conta: +conta.valor, valor: v || +conta.valor, tipo: conta.recorrencia ? 'fixo' : 'conta' }] } };
  }
  const inv = /\b(apliquei|investi|guardei)\b/.test(t) && S.d.investimentos.find(i => semAcento(i.nome).split(/\s+/).some(w => w.length > 3 && t.includes(w)));
  if (inv && valor) return { texto: `Anotei o aporte em **${inv.nome}**. Confira e confirme.`,
    acoes: { investimentos: [{ existente: inv.id, nome: inv.nome, banco: '', tipo: inv.tipo, valor: 0, aporte: valor, indexador: inv.indexador, taxa: inv.taxa, vencimento: '', liquidez: inv.liquidez || 'vencimento', dono: '', confianca: 'alta' }] } };
  if (/\b(gastei|comprei|paguei)\b/.test(t) && valor) {
    const m = /\b(?:no|na|em|de|do|da)\s+([a-z]+)/.exec(t), nome = m ? m[1][0].toUpperCase() + m[1].slice(1) : 'Gasto';
    return { texto: `Lanço **${nome}**, ${brl(valor)}. Confira e confirme.`,
      acoes: { lancamentos: [{ tipo: 'despesa', descricao: nome, valor, data: hj, categoria: /mercado/.test(t) ? 'c-mercado' : 'c-outros-gastos', parcela_atual: 0, parcelas_total: 0,
        cartao: /cartao/.test(t), banco: '', situacao: 'feito', confianca: 'alta' }] } };
  }
  if (/saldo|caixa|quanto (eu )?tenho/.test(t)) return { texto: `O saldo do caixa hoje é **${brl(saldoCaixa())}**.` };
  if (/vence|a pagar|\bcontas\b/.test(t)) {
    const prox = abertas.filter(l => (l.dc || l.data) >= hj).sort((x, y) => (x.dc || x.data).localeCompare(y.dc || y.data)).slice(0, 5);
    return { texto: prox.length ? 'As próximas contas:\n' + prox.map(l => `- ${l.descricao}: ${brl(+l.valor)}, ${fDataC(pData(l.dc || l.data))}`).join('\n') : 'Não tem conta a pagar nos próximos dias.' };
  }
  return { texto: 'Na prévia eu respondo só exemplos. No app, a IA do Home Assistant responde sobre o seu caixa, as contas e os investimentos, lança, marca contas pagas, atualiza saldos e conversa sobre outros assuntos.' };
}
function pagarDoChat(a) {
  const it = a.lista[0];
  if (it.id.startsWith('f:')) {
    const k = it.id.slice(2), f = faturasDe(lancamentosEntre(ymDe(k.split('|')[1]), ymDe(k.split('|')[1]))).find(x => x.k === k);
    if (!f || f.itens.every(l => l.pago)) { toast('Essa fatura não está mais em aberto.'); return; }
    persistir(d => {
      for (const l of f.itens) {
        if (l.pago) continue;
        if (l.virtual) d.lancamentos.push(materializar(l, { pago: true }));
        else { const x = d.lancamentos.find(y => y.id === l.id); if (x) x.pago = true; }
      }
    }, 'Fatura paga').then(ok => { if (ok) marcarAcaoChat(a.m.id, a.chave); });
    return;
  }
  const l = acharLanc(it.id);
  if (!l || l.pago) { toast('Essa conta não está mais em aberto.'); return; }
  // aporte: precisa dizer em qual investimento foi aplicado, como no Apliquei do caixa
  if (ehAporte(l) && invsDoAporte().length) { abrirPagar(it.id, { id: a.m.id, chave: a.chave }, it.valor); return; }
  persistir(d => mutPagar(d, l, it.valor > 0 ? it.valor : +l.valor || 0, null), ehRec(l) ? 'Recebimento confirmado' : 'Pagamento confirmado')
    .then(ok => { if (ok) marcarAcaoChat(a.m.id, a.chave); });
}

function abrirIA(modo, inicio, opts) {
  // a IA separa sozinha lançamentos (gastos, recebimentos, a pagar e a receber) e investimentos: não se escolhe antes.
  // Atualizar saldos (opts.saldos): uma listinha com o saldo de agora de cada investimento; o aporte é a diferença.
  IAS = { dica: modo === 'invest' ? 'invest' : 'caixa', etapa: inicio === 'voz' ? 'voz' : 'entrada', rec: inicio === 'voz' ? 'starting' : 'off', arquivo: null, texto: '', itens: [], invs: [], erro: '', conta: '', cartao: false,
    situacao: 'auto', futuras: true, ouvido: '', saldos: !!(opts && opts.saldos), pessoa: (opts && opts.pessoa) || '',
    // aberto do Novo investimento: só investimentos (nada vai para o caixa)
    soInvest: !!(opts && opts.soInvest),
    // veio de Colar mensagem ou de Imagem: a janela mostra só aquilo (sem misturar as outras opções)
    so: inicio === 'texto' || inicio === 'arquivo' ? inicio : inicio === 'camera' || inicio === 'colado' ? 'arquivo' : '' };
  if (!S.ia && !DEMO) api.iaStatus().then(s => { S.ia = s; if (IAS && FOLHA) pintarFolha(); }).catch(() => {});
  abrirFolha(montarIA, () => { pararFala(); IAS = null; }, !!(opts && opts.sobre));
  if (inicio === 'voz') comecarFala();
  if (inicio === 'arquivo') escolherArquivo('image/*,application/pdf').then(iaPegarArquivo);
  if (inicio === 'texto') setTimeout(() => { const t = $('#ia-txt'); if (t) t.focus(); }, 80);
}
function montarIA() {
  const s = IAS;
  if (s.etapa === 'voz') return telaFala();
  if (s.etapa === 'transcrevendo') return { titulo: 'Falar', corpo: `<div class="ia-lendo"><span class="giro"></span><p>Transcrevendo o que você disse…</p></div>` };
  if (s.etapa === 'revisao' && s.ouvido) { const r = revisaoIA(); r.corpo = ouvidoHTML(s) + r.corpo; return r; }
  if (s.etapa === 'lendo') return { titulo: 'Lendo com IA', corpo: `<div class="ia-lendo"><span class="giro"></span><p>Lendo ${s.arquivo ? (s.arquivo.pdf ? 'o PDF' : 'a imagem') : 'o texto'} com a IA do Home Assistant…<br>Pode levar até um minuto.</p></div>` };
  if (s.etapa === 'item') return revisarItemHTML();
  if (s.etapa === 'revisao') return revisaoIA();
  const aviso = S.ia && S.ia.pronta === false ? `<div class="aviso-fixo alerta">${ic('alert', 'ic-s')}<span>${esc(S.ia.motivo || 'A IA não está pronta.')} Veja em Mais › Configurações › Integrações.</span></div>` : '';
  const arq = s.arquivo;
  if (s.saldos) return entradaSaldos(aviso);
  // aberto do Novo investimento (ou do Invest): os textos falam de investimentos; a IA continua separando sozinha
  const inv = s.dica === 'invest';
  const prevArq = arq ? `<div class="ia-arq">${prevArquivo(arq)}</div>` : '';
  const pe = `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="ia-ler"${!arq && !s.texto.trim() ? ' disabled' : ''}>${ic('ia', 'ic-s')}Ler com IA</button>`;
  const erro = s.erro ? `<div class="msg-erro">${esc(s.erro)}</div>` : '';
  if (s.so === 'texto') return {
    titulo: 'Colar mensagem',
    corpo: `${aviso}${prevArq}<div class="campo"><label for="ia-txt">Mensagem</label>
        <textarea id="ia-txt" class="inp" data-ias="texto" rows="8" placeholder="${inv ? 'Ex.: “Apliquei 2 mil num CDB do Inter a 110% do CDI, vence em março de 2028” ou o e-mail da corretora' : 'Ex.: “gastei 45 no mercado”, “recebi 300 do João”, “boleto do IPVA vence dia 10”'}">${esc(s.texto)}</textarea>
      </div>${erro}`,
    pe };
  if (s.so === 'arquivo') return {
    titulo: inv ? 'Imagem ou print' : 'Fatura, print ou foto',
    corpo: `${aviso}${prevArq || `<div class="ia-arq"><button class="btn larga" data-a="ia-arq">${ic('image')}${inv ? 'Escolher o print do banco, a foto ou o PDF' : 'Escolher a fatura, o print ou a foto'}</button>${botaoCam()}</div>`}
      <p class="ajuda" style="margin:10px 0 0">Dá também para colar a imagem aqui.</p>${erro}${campoSenhaPdf()}`,
    pe };
  return {
    titulo: inv ? 'Ler investimento com IA' : 'Ler com IA',
    corpo: `${aviso}<div class="ia-arq">${arq ? prevArquivo(arq)
        : `<button class="btn larga" data-a="ia-arq">${ic('image')}${inv ? 'Print do banco, extrato ou PDF' : 'Fatura, print, foto ou PDF'}</button>${botaoCam()}`}
        ${!arq && vozPronta() ? `<button class="btn larga" data-a="ia-falar" style="margin-top:8px">${ic('mic')}Falar</button>` : ''}</div>
      <div class="campo"><label for="ia-txt">Ou cole o texto</label>
        <textarea id="ia-txt" class="inp" data-ias="texto" rows="6" placeholder="${inv ? 'Ex.: “Apliquei 2 mil num CDB do Inter a 110% do CDI, vence em março de 2028”, e-mail da corretora, nota de aplicação ou extrato'
          : 'Ex.: mensagens do WhatsApp (“gastei 45 no mercado”, “recebi 300 do João”, “boleto do IPVA vence dia 10”, “apliquei 2 mil no CDB do Inter”), fatura, extrato ou e-mail do banco'}">${esc(s.texto)}</textarea>
        <div class="ajuda">${inv ? 'Dá para colar um print aqui.' : 'Dá para colar um print aqui. A IA separa sozinha o que é cada coisa.'}</div></div>
      ${s.erro ? `<div class="msg-erro">${esc(s.erro)}</div>` : ''}${campoSenhaPdf()}`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="ia-ler"${!arq && !s.texto.trim() ? ' disabled' : ''}>${ic('ia', 'ic-s')}Ler com IA</button>`,
  };
}
function prevArquivo(arq) {
  const n = (arq.paginas || []).length;
  return `<div class="ia-prev">${arq.pdf ? `<span class="ia-pdf">${ic('file')}</span>` : `<img src="${arq.dataUrl}" alt="">`}
    <span><b>${esc(arq.nome)}</b><small>${arq.pdf ? 'PDF' : n > 1 ? `${n} páginas` : 'Imagem'}</small></span><button class="icbtn" data-a="ia-arq-rm" aria-label="Tirar arquivo">${ic('x')}</button></div>`;
}
const botaoCam = () => `<button class="btn larga" data-a="ia-cam" style="margin-top:8px">${ic('scan')}Digitalizar com a câmera</button>`;
const donosSaldos = () => [['', 'Vários'], ['meu', 'Meus'], ...pessoas().map(p => [p, p])];
function entradaSaldos(aviso) {
  const s = IAS, arq = s.arquivo;
  const de = s.pessoa === 'meu' ? 'seus investimentos' : s.pessoa ? `os investimentos de ${esc(s.pessoa)}` : 'os investimentos de cada um';
  return {
    titulo: s.pessoa && s.pessoa !== 'meu' ? `Atualizar saldos de ${esc(s.pessoa)}` : 'Atualizar saldos',
    corpo: `${aviso}<p class="da-intro" style="margin:0 0 14px">O valor de agora de cada investimento. O aporte é a diferença para o valor de hoje.</p>
      <div class="campo"><div class="lbl">De quem são</div><div class="chips" style="margin:0">${donosSaldos().map(([k, n]) =>
        `<button class="chip${s.pessoa === k ? ' on' : ''}" data-a="ias-pessoa" data-v="${esc(k)}">${esc(n)}</button>`).join('')}</div></div>
      <div class="ia-arq">${arq ? prevArquivo(arq)
        : `<button class="btn larga" data-a="ia-arq">${ic('image')}Print, foto ou PDF</button>${botaoCam()}`}</div>
      <div class="campo"><label for="ia-txt">Ou cole a lista</label>
        <textarea id="ia-txt" class="inp" data-ias="texto" rows="6" placeholder="Ex.:&#10;Nubank, valor atualizado, R$ 500&#10;Serasa, valor atualizado, R$ 600">${esc(s.texto)}</textarea>
      </div>
      ${s.erro ? `<div class="msg-erro">${esc(s.erro)}</div>` : ''}`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="ia-ler"${!arq && !s.texto.trim() ? ' disabled' : ''}>${ic('ia', 'ic-s')}Ler os saldos</button>`,
  };
}
// o dono que a IA leu ("mãe") como está nos investimentos ("Mãe"); "" é da própria pessoa
function donoDe(n) {
  const k = semAcento(n);
  if (!k || ['meu', 'minha', 'eu'].includes(k)) return '';
  return pessoas().find(p => semAcento(p) === k) || String(n).trim().replace(/^./, c => c.toUpperCase());
}
// quando a IA não achou o investimento, tenta pelo banco ou pelo nome, entre os do dono escolhido (só se houver um)
function acharInvSaldo(it, pessoa) {
  const doDono = i => !pessoa || (pessoa === 'meu' ? i.titular !== 'terceiros' : i.titular === 'terceiros' && i.terceiro === pessoa);
  const n = semAcento(it.banco || it.nome);
  if (!n) return '';
  const cands = S.d.investimentos.filter(doDono).filter(i => { const b = semAcento(bancoDe(i.banco)?.nome); return (b && (b === n || b.includes(n) || n.includes(b))) || semAcento(i.nome).includes(n); });
  return cands.length === 1 ? cands[0].id : '';
}
async function iaPegarArquivo(file) {
  if (!file) return;
  const pdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name);
  if (!pdf && !/^image\//.test(file.type)) { toast('Envie uma imagem ou um PDF.'); return; }
  if (file.size > 15 * 1024 * 1024) { toast('Arquivo grande demais (máximo 15 MB).'); return; }
  try {
    const dataUrl = pdf ? await lerArquivo(file) : await imagemJPG(file);
    IAS.arquivo = { nome: file.name || (pdf ? 'arquivo.pdf' : 'imagem.jpg'), pdf, dataUrl, foto: null };
    IAS.erro = ''; IAS.pedeSenha = false; IAS.senha = '';
    pintarFolha();
  } catch (e) { toast(e.message); }
}
// as fotos tiradas na hora (Digitalizar com IA) já vão para a leitura, como no ResolvIA
function iaUsarFotos(fotos) {
  if (!IAS || !fotos.length) return;
  IAS.arquivo = { nome: fotos.length > 1 ? 'Fotos da câmera' : 'Foto da câmera', pdf: false, dataUrl: fotos[0], paginas: fotos, foto: null };
  IAS.erro = '';
  iaLer();
}

/* --------- Digitalizar com IA: a câmera aqui dentro, como no ResolvIA (várias páginas viram uma leitura só) */
let CAM = null;
const CAM_MAX = 4;
const camOk = () => !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
async function abrirCamera(aoUsar) {
  fecharCamera(true);
  CAM = { status: 'abrindo', fotos: [], luz: false, temLuz: false, aoUsar, h: nivel() + 1 };
  marcarHist(CAM.h);
  pintarCamera();
  if (!camOk()) {
    CAM.status = 'erro';
    CAM.erro = window.isSecureContext === false
      ? 'A câmera só abre aqui com o Home Assistant num endereço seguro (https), como o do Nabu Casa. Dá para tirar a foto pelo celular e escolher.'
      : 'Este navegador não deixa usar a câmera aqui. Dá para tirar a foto pelo celular e escolher.';
    pintarCamera();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1440 } } });
    if (!CAM) { stream.getTracks().forEach(t => t.stop()); return; }
    const tr = stream.getVideoTracks()[0];
    const caps = tr && tr.getCapabilities ? tr.getCapabilities() : {};
    Object.assign(CAM, { stream, status: 'ao-vivo', temLuz: !!caps.torch });
    pintarCamera();
    const v = $('#camera video');
    if (v) { v.srcObject = stream; v.play().catch(() => {}); }
  } catch (e) {
    if (!CAM) return;
    const negado = e && (e.name === 'NotAllowedError' || e.name === 'SecurityError');
    CAM.status = 'erro';
    CAM.erro = negado ? 'Sem permissão para usar a câmera. Libere a câmera para o app do Home Assistant nas configurações do celular, ou escolha uma foto.'
      : 'Não deu para abrir a câmera. Dá para escolher uma foto.';
    pintarCamera();
  }
}
function pintarCamera() {
  let el = $('#camera');
  if (!CAM) { if (el) el.remove(); return; }
  if (!el) {
    el = document.createElement('div');
    el.id = 'camera'; el.className = 'cam'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', 'Digitalizar com IA');
    el.innerHTML = '<video playsinline muted autoplay></video><div class="cam-ui"></div>';
    document.body.appendChild(el);
  }
  const c = CAM, n = c.fotos.length;
  $('.cam-ui', el).innerHTML = `<div class="cam-top"><button class="cam-btn" data-a="cam-fechar" aria-label="Fechar">${ic('x')}</button><span class="cam-titulo">Digitalizar com IA</span>
      ${c.temLuz ? `<button class="cam-btn${c.luz ? ' on' : ''}" data-a="cam-luz" aria-label="Lanterna" aria-pressed="${c.luz}">${ic('zap')}</button>` : '<span class="cam-btn vazio"></span>'}</div>
    ${c.status === 'erro' ? `<div class="cam-msg">${ic('camera')}<p>${esc(c.erro)}</p><button class="btn pri" data-a="cam-galeria">${ic('image')}Tirar ou escolher foto</button></div>`
      : `<div class="cam-moldura"><i></i><i></i><i></i><i></i></div>
    <p class="cam-dica">${c.status === 'abrindo' ? 'Abrindo a câmera…' : n ? `${plural(n, 'página', 'páginas')}. ${n < CAM_MAX ? 'Fotografe outra ou toque em Pronto.' : 'Toque em Pronto.'}` : 'Enquadre a fatura, a nota ou a lista e toque no botão'}</p>`}
    ${c.status === 'erro' ? '' : `<div class="cam-baixo"><div class="cam-fotos">${c.fotos.slice(-3).map(f => `<img src="${f}" alt="">`).join('')}${n > 3 ? `<span>+${n - 3}</span>` : ''}</div>
      <button class="cam-disparo" data-a="cam-foto" aria-label="Fotografar"${c.status !== 'ao-vivo' || n >= CAM_MAX ? ' disabled' : ''}><span></span></button>
      <button class="cam-pronto" data-a="cam-pronto"${n ? '' : ' disabled'}>Pronto${n ? ` (${n})` : ''}</button></div>`}`;
}
function fecharCamera(semHistorico) {
  if (!CAM) return;
  if (CAM.stream) CAM.stream.getTracks().forEach(t => t.stop());
  CAM = null;
  pintarCamera();
  if (!semHistorico) voltarHist(nivel());
}
function camFoto() {
  const v = $('#camera video');
  if (!CAM || !v || !v.videoWidth || CAM.fotos.length >= CAM_MAX) return;
  const k = Math.min(1, 1600 / Math.max(v.videoWidth, v.videoHeight));
  const cv = document.createElement('canvas');
  cv.width = Math.round(v.videoWidth * k); cv.height = Math.round(v.videoHeight * k);
  cv.getContext('2d').drawImage(v, 0, 0, cv.width, cv.height);
  CAM.fotos.push(cv.toDataURL('image/jpeg', 0.86));
  try { if (navigator.vibrate) navigator.vibrate(15); } catch (e) { /* ok */ }
  const fl = document.createElement('div'); fl.className = 'cam-flash'; $('#camera').appendChild(fl); setTimeout(() => fl.remove(), 400);
  pintarCamera();
}
function camPronto() {
  if (!CAM || !CAM.fotos.length) return;
  const { fotos, aoUsar } = CAM;
  // a folha da leitura entra no lugar da câmera no histórico (sem voltar e avançar de novo)
  const h = CAM.h; fecharCamera(true);
  aoUsar(fotos);
  if (nivel() < h) voltarHist(nivel());
}
async function camLuz() {
  const tr = CAM && CAM.stream && CAM.stream.getVideoTracks()[0];
  if (!tr) return;
  try { await tr.applyConstraints({ advanced: [{ torch: !CAM.luz }] }); CAM.luz = !CAM.luz; } catch (e) { CAM.temLuz = false; }
  pintarCamera();
}
function camGaleria() {
  const aoUsar = CAM && CAM.aoUsar;
  fecharCamera();
  if (!aoUsar) return;
  escolherArquivo('image/*', true).then(async f => {
    if (!f) return;
    try { aoUsar([await imagemJPG(f)]); } catch (e) { toast(e.message); }
  });
}

async function iaLer() {
  const s = IAS;
  s.erro = ''; s.etapa = 'lendo'; pintarFolha();
  try {
    const corpo = { modo: 'auto', dica: s.dica, texto: s.texto };
    if (s.saldos) Object.assign(corpo, { saldos: true, pessoa: s.pessoa || '' });
    else if (s.soInvest) corpo.so_invest = true;
    if (s.ouvido && !s.arquivo) corpo.fala = true;
    if (s.arquivo && (s.arquivo.paginas || []).length > 1) corpo.anexos = s.arquivo.paginas.map(b64 => ({ b64 }));
    else if (s.arquivo) corpo.anexo = { b64: s.arquivo.dataUrl };
    if (s.arquivo && s.arquivo.pdf && s.pedeSenha && (s.senha || '').trim()) Object.assign(corpo, { senha: s.senha.trim(), guardar_senha: s.guardarSenha !== false, nome_arquivo: s.arquivo.nome });
    const r = await api.iaLer(corpo);
    if (s.pedeSenha && corpo.senha && corpo.guardar_senha) S.senhas = undefined;  // a senha nova entrou na lista
    if (!IAS) return;
    iaResultado(r);
  } catch (e) {
    if (!IAS) return;
    // PDF com senha: a folha pede a senha (e oferece guardar para as próximas faturas)
    if (e.codigo === 'senha_pdf') { s.pedeSenha = true; s.etapa = 'entrada'; s.erro = e.message; pintarFolha(); setTimeout(() => { const i = $('#ia-senha'); if (i) i.focus(); }, 60); return; }
    s.etapa = 'entrada'; s.erro = 'Não consegui ler. ' + e.message; pintarFolha();
  }
}
// o que a IA leu vai para a conferência (também a fatura que chegou por e-mail e já foi lida no servidor)
function iaResultado(r) {
  const s = IAS;
  const lanc = s.saldos || s.soInvest ? [] : r.lancamentos || [], invs = r.investimentos || [];
  for (const it of invs) {
    it.dono = donoDe(it.dono);
    if (s.saldos) it.aporte = 0;
    if (!it.existente && (s.saldos || s.soInvest)) it.existente = acharInvSaldo(it, s.pessoa || it.dono);
  }
  if (!lanc.length && !invs.length) { s.etapa = 'entrada'; s.erro = s.saldos ? 'A IA não encontrou nenhum saldo. Tente outro print ou cole a lista.' : s.soInvest ? 'A IA não encontrou investimento. Tente outra imagem ou cole o texto.' : 'A IA não encontrou gasto, recebimento, conta nem investimento. Tente outra imagem ou cole o texto.'; pintarFolha(); return; }
  s.itens = lanc.map(it => Object.assign({ marcado: true }, it));
  s.invs = invs.map(it => Object.assign({ marcado: true }, it));
  if (s.itens.length) prepararRevisaoCaixa();
  s.etapa = 'revisao';
  pintarFolha();
}
// o campo da senha do PDF, quando o PDF tem senha e nenhuma cadastrada abriu
function campoSenhaPdf() {
  const s = IAS;
  if (!s.pedeSenha || !s.arquivo || !s.arquivo.pdf) return '';
  return `<div class="campo ia-senha"><label for="ia-senha">Senha do PDF</label>
      <input id="ia-senha" class="inp" data-ias="senha" value="${esc(s.senha || '')}" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Ex.: os primeiros dígitos do CPF"></div>
    ${linhaChave('ias-guardar', s.guardarSenha !== false, 'Guardar para as próximas faturas', 'Fica em Mais › Configurações › Integrações › Senhas dos PDFs.', 'ias-guardar')}`;
}
function prepararRevisaoCaixa() {
  const s = IAS;
  const cartao = s.itens.filter(i => i.cartao).length > s.itens.length / 2;
  const nomeBanco = (s.itens.find(i => i.banco) || {}).banco;
  const b = bancoPorNome(nomeBanco);
  const cs = contas();
  const conta = (b && (cs.find(c => c.banco === b.id && (!cartao || c.cartao)) || cs.find(c => c.banco === b.id))) || (cartao ? cs.find(c => c.cartao) : null) || cs[0];
  s.conta = conta?.id || '';
  s.cartao = cartao && !!conta?.cartao;
  for (const it of s.itens) {
    // cada linha com a sua conta: a do banco que a IA viu nela (no cartão, se ela viu compra no cartão e a conta tem cartão); senão a de todos
    const bi = bancoPorNome(it.banco);
    const ci = bi && (cs.find(c => c.banco === bi.id && (!it.cartao || c.cartao)) || cs.find(c => c.banco === bi.id));
    it.conta = (ci || conta)?.id || '';
    it.noCartao = it.tipo === 'despesa' && !!contaDe(it.conta)?.cartao && (ci ? it.cartao === true : s.cartao && it.cartao !== false);
    if (!it.categoria) it.categoria = it.tipo === 'receita' ? 'c-outros-receb' : 'c-outros-gastos';
    if (!S.d.categorias.some(c => c.id === it.categoria)) it.categoria = S.d.categorias.find(c => c.tipo === it.tipo)?.id || '';
    const dup = S.d.lancamentos.some(l => l.tipo === it.tipo && Math.abs((+l.valor || 0) - it.valor) < 0.01 &&
      Math.abs(diasEntre(pData(l.data) || hoje(), pData(it.data) || hoje())) <= 2 && semAcento(l.descricao).slice(0, 4) === semAcento(it.descricao).slice(0, 4));
    it.dup = dup;
    if (dup) it.marcado = false;
  }
}
// Conferir o que a IA leu: lançamentos e investimentos juntos, um botão salva tudo o que estiver marcado
function revisaoIA() {
  const s = IAS, nl = s.itens.length, ni = s.invs.length;
  const ml = s.itens.filter(i => i.marcado), mi = s.invs.filter(i => i.marcado);
  const achou = [nl ? plural(nl, 'lançamento', 'lançamentos') : '', ni ? plural(ni, 'investimento', 'investimentos') : ''].filter(Boolean).join(' e ');
  let corpo = `<p style="margin:0 0 14px;color:var(--text-2)">Achei <b style="color:var(--text)">${s.saldos ? plural(ni, 'saldo', 'saldos') : achou}</b>. Desmarque o que não quiser.</p>`;
  if (nl) corpo += `${ni ? `<h3 class="ia-sec">${ic('fluxo', 'ic-s')}Lançamentos</h3>` : ''}${revisaoCaixa()}`;
  if (ni) corpo += `${nl ? `<h3 class="ia-sec">${ic('wallet', 'ic-s')}Investimentos</h3>` : ''}${revisaoInvest()}`;
  const total = ml.reduce((a, i) => a + (i.tipo === 'receita' ? i.valor : -i.valor), 0);
  const n = ml.length + mi.length;
  const rot = s.saldos ? `Atualizar ${n}` : ni && !nl ? `Salvar ${n}` : nl && !ni ? `Lançar ${n} · ${total < 0 ? '−' : ''}${brl(Math.abs(total), 0)}` : `Salvar ${n}`;
  return { titulo: s.saldos ? 'Conferir os saldos' : nl && ni ? 'Conferir o que a IA leu' : nl ? 'Conferir lançamentos' : 'Conferir investimentos', corpo,
    pe: `${s.email ? '<button class="btn" data-a="email-ignorar">Ignorar</button>' : '<button class="btn" data-a="ia-voltar">Voltar</button>'}<button class="btn pri" data-a="ia-salvar"${n ? '' : ' disabled'}>${rot}</button>` };
}
// o lançamento fica pago ou pendente: Automática segue o que a IA viu (conta a pagar, a receber) e, sem isso, a data
function iaPago(it, data) {
  const s = IAS;
  if (s.situacao === 'pago') return true;
  if (s.situacao === 'apagar') return false;
  // compra no cartão segue a fatura (paga quando a fatura vence), não o que a IA achou
  const cartao = iaNoCartao(it);
  if (!cartao && it.situacao === 'feito') return true;
  if (!cartao && it.situacao === 'pendente') return false;
  return dataCaixa({ data, conta: it.conta, cartao }) <= iso(hoje());
}
// no cartão: cada linha escolhe a conta e, se ela tiver cartão, se foi no cartão de crédito; o Lançar todos em muda todas
function iaNoCartao(it) {
  return it.tipo === 'despesa' && !!it.noCartao && !!contaDe(it.conta)?.cartao;
}
function opcoesContaIA(it) {
  const v = it.conta ? it.conta + (iaNoCartao(it) ? '|c' : '') : '';
  const op = (val, txt) => `<option value="${val}"${val === v ? ' selected' : ''}>${esc(txt)}</option>`;
  return op('', 'Sem conta') + contas().map(c => op(c.id, nomeConta(c) + (c.cartao && it.tipo === 'despesa' ? ' · débito' : '')) + (c.cartao && it.tipo === 'despesa' ? op(c.id + '|c', nomeConta(c) + ' · crédito') : '')).join('');
}
function revisaoCaixa() {
  const s = IAS;
  const temParc = s.itens.some(i => i.parcelas_total > i.parcela_atual);
  // o Lançar todos em fica marcado quando todas as linhas estão na mesma conta
  const todas = [...new Set(s.itens.map(i => i.conta || ''))], uma = todas.length === 1 ? todas[0] : null;
  const conta = uma != null ? contaDe(uma) : null, desp = s.itens.filter(i => i.tipo === 'despesa');
  const todasCartao = desp.length && desp.every(iaNoCartao), nenhumaCartao = desp.every(i => !iaNoCartao(i));
  return `<div class="campo"><div class="lbl">Lançar todos em</div><div class="chips" style="margin:0">
      <button class="chip${uma === '' ? ' on' : ''}" data-a="iac-conta" data-v="">Sem conta</button>
      ${contas().map(k => `<button class="chip${uma === k.id ? ' on' : ''}" data-a="iac-conta" data-v="${k.id}" style="--c:${corOk(k.cor) || '#B8B0B0'}"><span class="bol"></span>${esc(nomeConta(k))}</button>`).join('')}</div>
      ${conta?.cartao && desp.length ? `<div class="seg mini" style="margin:10px 0 0"><button class="${nenhumaCartao ? 'on' : ''}" data-a="iac-cartao" data-v="">Débito ou Pix</button><button class="${todasCartao ? 'on' : ''}" data-a="iac-cartao" data-v="1">${ic('card', 'ic-s')}Cartão de crédito</button></div>` : ''}</div>
    <div class="campo"><div class="lbl">Situação</div><div class="seg mini" style="margin:0">
      <button class="${s.situacao === 'auto' ? 'on' : ''}" data-a="iac-sit" data-v="auto">Automática</button>
      <button class="${s.situacao === 'pago' ? 'on' : ''}" data-a="iac-sit" data-v="pago">Tudo pago</button>
      <button class="${s.situacao === 'apagar' ? 'on' : ''}" data-a="iac-sit" data-v="apagar">Tudo pendente</button></div>
      ${s.situacao === 'auto' ? `<div class="ajuda">Contas a pagar e a receber ficam pendentes; o resto, pela data.</div>` : ''}</div>
    ${temParc ? `<div class="linha-sw" style="margin-bottom:16px"><div><b>Lançar as próximas parcelas</b><span>Aparecem nas faturas dos próximos meses.</span></div><button class="sw${s.futuras ? ' on' : ''}" data-a="iac-futuras" aria-label="Lançar parcelas futuras"></button></div>` : ''}
    <div class="ia-itens">${s.itens.map((it, k) => {
      const cats = S.d.categorias.filter(c => c.tipo === it.tipo);
      return `<div class="ia-item${it.marcado ? '' : ' off'}">
        <button class="ia-check${it.marcado ? ' on' : ''}" data-a="ia-marca" data-i="${k}" aria-label="${it.marcado ? 'Desmarcar' : 'Marcar'}">${it.marcado ? ic('check', 'ic-s') : ''}</button>
        <div class="ia-item-t"><b>${esc(it.descricao)}</b>
          <span>${fDataC(pData(it.data))}${it.parcelas_total ? ` · parcela ${it.parcela_atual}/${it.parcelas_total}` : ''}${iaNoCartao(it) ? ' · na fatura' : iaPago(it, it.data) ? '' : ` · <b class="ia-pend">${it.tipo === 'receita' ? 'a receber' : 'a pagar'}</b>`}${it.dup ? ' · <em>parece já lançado</em>' : ''}${it.confianca === 'baixa' ? ' · <em>confira</em>' : ''}</span></div>
        <b class="${it.tipo === 'receita' ? 'ent' : 'sai'}">${it.tipo === 'receita' ? '+' : '−'} ${brl(it.valor)}</b>
        <div class="ia-item-x dois">
          <select class="ia-cat" data-iai="categoria" data-i="${k}" aria-label="Categoria">${cats.map(c => `<option value="${c.id}"${c.id === it.categoria ? ' selected' : ''}>${esc(c.nome)}</option>`).join('')}</select>
          <select class="ia-cat" data-iai="contasel" data-i="${k}" aria-label="Conta">${opcoesContaIA(it)}</select></div></div>`;
    }).join('')}</div>`;
}
// salva o que estiver marcado nos dois grupos de uma vez
async function salvarIA() {
  const s = IAS;
  const ml = s.itens.filter(i => i.marcado), mi = s.invs.filter(i => i.marcado);
  if (!ml.length && !mi.length) return;
  // a imagem lida fica guardada com os investimentos salvos
  if (mi.length && s.arquivo && !s.arquivo.pdf && !s.arquivo.foto) {
    try { const r = await api.foto(s.arquivo.dataUrl); s.arquivo.foto = r.arquivo; if (DEMO) DEMO_FOTOS[r.arquivo] = s.arquivo.dataUrl; } catch (e) { /* salva sem a imagem */ }
  }
  let msg = [ml.length ? plural(ml.length, 'lançamento', 'lançamentos') : '', mi.length ? plural(mi.length, 'investimento', 'investimentos') : ''].filter(Boolean).join(' e ') + ' pela IA';
  if (s.saldos) { const ap = mi.map(difSaldo).filter(x => x && x.dif > 0).reduce((a, x) => a + x.dif, 0); msg = `${plural(mi.length, 'saldo atualizado', 'saldos atualizados')}${ap > 0 ? ` · aportes ${brl(ap, 0)}` : ''}`; }
  persistir(d => {
    if (ml.length) aplicarIACaixa(d, ml);
    if (mi.length) aplicarIAInvest(d, mi);
  }, msg).then(ok => {
    if (!ok) return;
    if (s.email) api.emailAcao('feito', s.email).then(r => { S.emails = r; render(); }).catch(() => {});
    if (s.chat) { fecharFolha(false, true); marcarAcaoChat(s.chat.id, s.chat.chave); return; } // aberta do chat: volta para a conversa
    fecharFolha();
    if (ml.length) { S.ui.tab = 'caixa'; S.ui.cxModo = 'lista'; } else { S.ui.tab = 'investimentos'; S.ui.invModo = 'carteira'; }
    render();
  });
}
function aplicarIACaixa(d, itens) {
  const s = IAS;
  {
    const antes = S.d;
    for (const it of itens) {
      const cartao = iaNoCartao(it);
      const base = { tipo: it.tipo, descricao: it.descricao, valor: it.valor, categoria: it.categoria, conta: it.conta || '', cartao, obs: '' };
      // aplicação nos investimentos vira uma saída do tipo Aporte
      if (it.tipo === 'despesa' && it.categoria === 'c-investimentos') Object.assign(base, { aporte: true, cartao: false });
      const pago = data => iaPago(it, data);
      if (it.parcelas_total && it.parcela_atual) {
        const g = 'g-' + uid();
        const ultimo = s.futuras ? it.parcelas_total : it.parcela_atual;
        for (let p = it.parcela_atual; p <= ultimo; p++) {
          const data = somaMeses(it.data, p - it.parcela_atual);
          d.lancamentos.push(Object.assign({ id: uid() }, base, { data, parcela: `${p}/${it.parcelas_total}`, grupo: g, pago: p === it.parcela_atual ? pago(data) : false }));
        }
      } else d.lancamentos.push(Object.assign({ id: uid() }, base, { data: it.data, pago: pago(it.data) }));
    }
    S.d = antes;
  }
}
// diferença entre o saldo que a IA leu e o valor de hoje do investimento: o aporte (ou o resgate, se for menos)
function difSaldo(it) {
  const ex = it.existente && S.d.investimentos.find(i => i.id === it.existente);
  if (!ex || !(it.valor > 0) || (it.aporte > 0 && !IAS.saldos)) return null;
  return { ex, antes: round2(valorHoje(ex)), dif: round2(it.valor - valorHoje(ex)) };
}
function opcoesInvSaldo(sel) {
  const meus = S.d.investimentos.filter(i => i.titular !== 'terceiros'), grupos = [['Meus', meus], ...pessoas().map(p => [p, S.d.investimentos.filter(i => i.titular === 'terceiros' && i.terceiro === p)])];
  const op = i => `<option value="${esc(i.id)}"${i.id === sel ? ' selected' : ''}>${esc(i.nome)}${bancoDe(i.banco) ? ' · ' + esc(bancoDe(i.banco).nome) : ''}</option>`;
  return `<option value=""${!sel ? ' selected' : ''}>Novo investimento</option>${grupos.filter(g => g[1].length).map(([n, l]) => `<optgroup label="${esc(n)}">${l.map(op).join('')}</optgroup>`).join('')}`;
}
function revisaoInvest() {
  const s = IAS;
  const difs = s.invs.filter(i => i.marcado).map(difSaldo).filter(Boolean);
  const ap = difs.filter(x => x.dif > 0).reduce((a, x) => a + x.dif, 0), rs = difs.filter(x => x.dif < 0).reduce((a, x) => a - x.dif, 0);
  const donoNovo = it => s.pessoa && s.pessoa !== 'meu' ? s.pessoa : s.pessoa === 'meu' ? '' : it.dono || '';
  return `${difs.length ? `<div class="ia-saldos-res"><span>Aportes <b class="ent">${brl(ap)}</b></span>${rs > 0.005 ? `<span>Resgates <b class="sai">${brl(rs)}</b></span>` : ''}</div>`
      : ''}
    <div class="ia-itens">${s.invs.map((it, k) => {
      const ex = it.existente && S.d.investimentos.find(i => i.id === it.existente), df = difSaldo(it);
      const linha = df ? (df.dif > 0.005 ? `Aporte de <b>${brl(df.dif)}</b>: ${brl(df.antes)} → ${brl(it.valor)}` : df.dif < -0.005 ? `Resgate de <b>${brl(-df.dif)}</b>: ${brl(df.antes)} → ${brl(it.valor)}` : `Sem mudança: ${brl(it.valor)}`)
        : ex && it.aporte > 0 && !(it.valor > 0) ? `Aplica ${brl(it.aporte)} em ${esc(ex.nome)}: ${brl(valorHoje(ex))} → ${brl(valorHoje(ex) + it.aporte)}` : ex ? `Atualiza ${esc(ex.nome)}: ${brl(valorHoje(ex))} → ${brl(it.valor)}` : '';
      const direita = df ? `<b class="${df.dif > 0.005 ? 'ent' : df.dif < -0.005 ? 'sai' : ''}">${df.dif > 0.005 ? '+ ' : df.dif < -0.005 ? '− ' : ''}${brl(Math.abs(df.dif))}</b>` : `<b>${brl(it.aporte > 0 && !(it.valor > 0) ? it.aporte : it.valor)}</b>`;
      return `<div class="ia-item${it.marcado ? '' : ' off'}">
        <button class="ia-check${it.marcado ? ' on' : ''}" data-a="ia-marca-inv" data-i="${k}" aria-label="${it.marcado ? 'Desmarcar' : 'Marcar'}">${it.marcado ? ic('check', 'ic-s') : ''}</button>
        <div class="ia-item-t"><b>${esc(s.saldos ? [it.banco, it.banco && semAcento(it.nome) === semAcento(it.banco) ? '' : it.nome].filter(Boolean).join(' · ') || it.nome : it.nome)}</b>
          ${s.saldos ? '' : `<span>${esc([it.banco, tipoDe(it.tipo).nome, rotuloTaxa(it), it.vencimento ? 'vence ' + fData(pData(it.vencimento)) : ''].filter(Boolean).join(' · '))}</span>`}</div>
        ${direita}
        <div class="ia-item-x">
          <select class="ia-cat" data-iav="existente" data-i="${k}" aria-label="Investimento">${opcoesInvSaldo(it.existente)}</select>
          ${linha ? `<span class="ia-atualiza">${linha}</span>` : `<span class="ia-atualiza novo">Novo investimento${donoNovo(it) ? ` de ${esc(donoNovo(it))}` : ''}${s.saldos || s.soInvest ? `, com ${brl(it.valor)}` : ''}</span>`}
          ${it.confianca === 'baixa' ? '<span><em>Confira os números</em></span>' : ''}
          <button class="link" data-a="iai-revisar" data-i="${k}">Revisar antes</button></div></div>`;
    }).join('')}</div>`;
}
const donoIA = it => IAS.pessoa && IAS.pessoa !== 'meu' ? IAS.pessoa : IAS.pessoa === 'meu' ? '' : it.dono || '';
function aplicarIAInvest(d, itens) {
  const s = IAS, hj = iso(hoje());
  const foto = s.arquivo?.foto;
  {
    for (const it of itens) {
      const ex = it.existente && d.investimentos.find(i => i.id === it.existente);
      if (ex) {
        // "apliquei 3 mil no CDB": a IA manda o aporte sem o saldo, e ele soma ao valor de hoje
        const valor = it.aporte > 0 && !(it.valor > 0) ? round2(valorHoje(ex) + it.aporte) : it.valor;
        definirValor(ex, valor, it.aporte > 0 && !(it.valor > 0) ? hj : it.data_valor || hj);
        if (!ex.vencimento && it.vencimento) ex.vencimento = it.vencimento;
        if (foto) ex.fotos = [...(ex.fotos || []), foto];
        continue;
      }
      let b = bancoPorNome(it.banco, d);
      if (!b && it.banco) { b = { id: 'b-' + uid(), nome: it.banco, cor: CORES_BANCO.find(c => !d.bancos.some(x => x.cor === c)) || CORES_BANCO[0], obs: '', contas: [] }; d.bancos.push(b); }
      d.investimentos.push({ id: uid(), nome: it.nome, banco: b?.id || '', tipo: it.tipo, valor: it.valor, data_valor: it.data_valor || hj,
        indexador: it.indexador, taxa: ['poupanca', 'parado'].includes(it.indexador) ? 0 : it.taxa, liquidez: it.liquidez, vencimento: it.vencimento || null,
        titular: donoIA(it) ? 'terceiros' : 'meu', terceiro: donoIA(it), obs: it.aplicado ? `Valor aplicado: ${brl(it.aplicado)}` : '', fotos: foto ? [foto] : [],
        criado_em: new Date().toISOString(), atualizado_em: new Date().toISOString() });
    }
  }
}
// Revisar antes: corrige o que a IA leu sem sair da conferência (Voltar ou Pronto voltam para a lista)
function revisarItemInvest(k) {
  IAS.edit = { k, r: Object.assign({}, IAS.invs[k]) };
  IAS.etapa = 'item';
  pintarFolha();
}
function revisarItemHTML() {
  const r = IAS.edit.r, ex = r.existente && S.d.investimentos.find(i => i.id === r.existente), ix = idxDe(r.indexador);
  const valor = `<div class="campo"><label for="iae-v">${ex ? 'Saldo de agora' : 'Valor de hoje'}</label><div class="pref grande"><span>R$</span><input id="iae-v" data-iae="valor" inputmode="numeric" value="${r.valor ? NF2.format(r.valor) : ''}" placeholder="0,00"></div>
      ${ex ? `<div class="ajuda">${esc(ex.nome)}: ${brl(valorHoje(ex))} hoje.</div>` : ''}</div>`;
  let corpo = valor;
  if (!ex) corpo += `<div class="campo"><label for="iae-nome">Nome</label><input id="iae-nome" class="inp" data-iae="nome" value="${esc(r.nome)}" autocomplete="off"></div>
      <div class="campo"><label for="iae-banco">Banco</label><input id="iae-banco" class="inp" data-iae="banco" value="${esc(r.banco)}" list="dl-iae-bancos" autocomplete="off">
        <datalist id="dl-iae-bancos">${[...new Set([...S.d.bancos.map(b => b.nome), ...BANCOS_COMUNS])].map(n => `<option value="${esc(n)}">`).join('')}</datalist></div>
      <div class="campos-2"><div class="campo"><label for="iae-tipo">Tipo</label><select id="iae-tipo" class="inp" data-iae="tipo">${TIPOS.map(t => `<option value="${t.id}"${t.id === r.tipo ? ' selected' : ''}>${esc(t.nome)}</option>`).join('')}</select></div>
        <div class="campo"><label for="iae-idx">Rendimento</label><select id="iae-idx" class="inp" data-iae="indexador">${IDX.filter(x => !x.oculto || x.id === r.indexador).map(x => `<option value="${x.id}"${x.id === r.indexador ? ' selected' : ''}>${esc(x.nome)}</option>`).join('')}</select></div></div>
      ${ix.taxa ? `<div class="campo"><label for="iae-taxa">Taxa (${esc(ix.suf)})</label><input id="iae-taxa" class="inp" data-iae="taxa" inputmode="decimal" value="${r.taxa || r.taxa === 0 ? String(r.taxa).replace('.', ',') : ''}" placeholder="${ix.ph}"></div>` : ''}
      <div class="campos-2"><div class="campo"><label for="iae-venc">Vencimento</label><input id="iae-venc" class="inp" type="date" data-iae="vencimento" value="${esc(r.vencimento || '')}"></div>
        <div class="campo"><div class="lbl">Liquidez</div><div class="seg mini" style="margin:0"><button class="${r.liquidez === 'diaria' ? 'on' : ''}" data-a="iae-liq" data-v="diaria">Diária</button><button class="${r.liquidez !== 'diaria' ? 'on' : ''}" data-a="iae-liq" data-v="vencimento">No venc.</button></div></div></div>`;
  return { titulo: ex ? `Revisar ${esc(ex.nome)}` : 'Revisar investimento novo', corpo,
    pe: `<button class="btn" data-a="iae-voltar">Voltar</button><button class="btn pri" data-a="iae-ok">Pronto</button>` };
}
document.addEventListener('paste', ev => {
  if (!iaOn()) return;
  const f = [...(ev.clipboardData?.files || [])].find(x => /^image\//.test(x.type) || x.type === 'application/pdf');
  if (!f) return;
  if (IAS && IAS.etapa === 'entrada') { ev.preventDefault(); iaPegarArquivo(f); return; }
  // com a Nova despesa ou o Novo investimento aberto, colar uma imagem já abre a leitura por IA com ela
  if (!IAS && FOLHA && $('#folhas .imp-campo')) {
    ev.preventDefault();
    { const inv = FOLHA.montar === montarFormInv; abrirIA(inv ? 'invest' : 'caixa', 'colado', { soInvest: inv, sobre: true }); }
    iaPegarArquivo(f);
  }
});

// No computador, dá para arrastar a imagem ou o PDF para a janela (Nova despesa, Novo investimento ou Ler com IA)
const podeSoltar = () => iaOn() && FOLHA && ((IAS && IAS.etapa === 'entrada') || (!IAS && $('#folhas .imp-campo')));
document.addEventListener('dragover', ev => {
  if (podeSoltar() && [...(ev.dataTransfer?.types || [])].includes('Files')) { ev.preventDefault(); ev.dataTransfer.dropEffect = 'copy'; }
});
document.addEventListener('drop', ev => {
  if (!podeSoltar()) return;
  const f = [...(ev.dataTransfer?.files || [])].find(x => /^image\//.test(x.type) || x.type === 'application/pdf');
  if (!f) return;
  ev.preventDefault();
  if (!IAS) { const inv = FOLHA.montar === montarFormInv; abrirIA(inv ? 'invest' : 'caixa', 'colado', { soInvest: inv, sobre: true }); }
  iaPegarArquivo(f);
});

/* ------------------------------------------------------------------ Mais: categorias, fixos, IA e bancos com pessoas */
/* ------------------------------------------------------------------ dicas de economia */
// Assinaturas conferidas na página oficial (feito no servidor, com a IA do Home Assistant)
// e categorias acima da média (dos seus próprios lançamentos).
let dicasTimer = null, dicasPedido = null, dicasAgenda = null;
function carregarDicas(forcar) {
  if (dicasPedido && !forcar) return dicasPedido;
  dicasPedido = (forcar ? api.dicasConferir() : api.dicas()).then(r => {
    S.dicas = r;
    clearTimeout(dicasTimer);
    if (r.conferindo) dicasTimer = setTimeout(() => carregarDicas(), 6000);
    if (!FOLHA && (S.ui.tab === 'inicio' || S.ui.tab === 'mais')) render();
  }).catch(() => {}).finally(() => { dicasPedido = null; });
  return dicasPedido;
}
function agendarDicas() { clearTimeout(dicasAgenda); dicasAgenda = setTimeout(() => carregarDicas(), 1200); }

const SIMBOLO = { BRL: 'R$', USD: 'US$', EUR: '€', GBP: '£' };
const fmtPreco = (v, moeda) => `${SIMBOLO[moeda] || ''} ${Math.abs(v - Math.round(v)) < 0.005 ? NF0.format(Math.round(v)) : NF2.format(v)}`;
const juntarE = l => l.length > 1 ? l.slice(0, -1).join(', ') + ' e ' + l[l.length - 1] : (l[0] || '');
function mesesGratis(x) {
  const m = (12 * x.mensal - x.anual) / x.mensal, r = Math.round(m);
  return r >= 1 && Math.abs(m - r) < 0.12 ? r : 0;
}

// Economia real do plano anual: o desconto menos o que o dinheiro das mensalidades renderia nos seus investimentos.
// O dinheiro sai mês a mês, então vale o investimento seu com liquidez diária que rende mais (líquido de IR);
// sem nenhum com liquidez diária, a média dos seus investimentos; sem investimentos, 100% do CDI.
function rendaReserva() {
  return memo('reserva', () => {
    const meus = porEscopo('meu').filter(i => !['estimado', 'parado'].includes(i.indexador) && taxaAnual(i) > 0);
    const liquida = i => taxaAnual(i) * (1 - aliquota(tipoDe(i.tipo).ir, 200));
    const liq = meus.filter(i => i.liquidez === 'diaria');
    if (liq.length) {
      const i = liq.reduce((a, b) => liquida(b) > liquida(a) ? b : a);
      return { r: taxaAnual(i), ir: tipoDe(i.tipo).ir, onde: `em ${i.nome} (${rotuloTaxa(i)})`, curto: i.nome };
    }
    if (meus.length) {
      const V = meus.reduce((s, i) => s + valorHoje(i), 0);
      const r = V > 0 ? meus.reduce((s, i) => s + valorHoje(i) * taxaAnual(i), 0) / V : 0;
      return { r, ir: 'reg', onde: `na média dos seus investimentos (${pct(r * 100)}% a.a.)`, curto: 'seus investimentos' };
    }
    return { r: (+S.d.indices.cdi || 0) / 100, ir: 'reg', onde: `a 100% do CDI (${pct(+S.d.indices.cdi || 0)}% a.a.)`, curto: '100% do CDI' };
  });
}
function economiaReal(mensal, anual) {
  const rs = rendaReserva(), rm = Math.pow(1 + rs.r, 1 / 12) - 1;
  let pv = 0; // quanto precisa estar investido hoje para pagar as 12 mensalidades
  for (let k = 0; k < 12; k++) pv += mensal / (1 + (Math.pow(1 + rm, k) - 1) * (1 - aliquota(rs.ir, k * 30.44)));
  return { real: pv - anual, rende: 12 * mensal - pv, desconto: 12 * mensal - anual, rs };
}
const realDe = x => memo('real:' + x.id + ':' + x.valor + ':' + x.preco_anual, () => economiaReal(x.valor, x.preco_anual));

function dicaCategoria() {
  return memo('dicaCat', () => {
    const ym = addYm(ymHoje(), -1), ant = [1, 2, 3].map(k => addYm(ym, -k));
    const tot = m => {
      const o = {};
      for (const l of lancamentosCompetencia(m)) if (!l.ajuste && !ehRec(l) && !ehAporte(l) && !l.desconto && l.categoria) o[l.categoria] = (o[l.categoria] || 0) + (+l.valor || 0);
      return o;
    };
    const atual = tot(ym), antes = ant.map(tot);
    let melhor = null;
    for (const [cat, v] of Object.entries(atual)) {
      const vs = antes.map(o => o[cat] || 0);
      if (vs.filter(x => x > 0).length < 2) continue;
      const media = vs.reduce((a, b) => a + b, 0) / 3, dif = v - media;
      if (v >= media * 1.25 && dif >= 150 && (!melhor || dif > melhor.dif)) melhor = { cat, v, media, dif, ym, ant };
    }
    return melhor ? Object.assign(melhor, { id: `cat:${melhor.cat}:${ym}` }) : null;
  });
}

function dicasVisiveis() {
  const fora = new Set(S.d.ajustes.dicas_fora || []);
  // os planos anuais vêm do preço conferido pela IA: com Usar IA desligado, ficam só as dicas de categoria
  const subs = (iaOn() && S.dicas && S.dicas.dicas || []).filter(x => !fora.has(x.id) && realDe(x).real >= 10)
    .sort((a, b) => realDe(b).real - realDe(a).real);
  const cat = dicaCategoria();
  return { subs, cat: cat && !fora.has(cat.id) ? cat : null };
}

function linhaDicaAssinatura(x) {
  const mg = mesesGratis(x);
  const quando = x.conferido ? fData(pData(x.conferido)) : '';
  return `<div class="dica">
    <div class="dica-cab"><span class="dica-ic">${ic('percent')}</span>
      <div class="dica-t"><b>${esc(x.nome)} no plano anual</b>
        <span>${fmtPreco(x.anual, x.moeda)} por ano em vez de ${fmtPreco(x.mensal, x.moeda)} por mês, ${mg ? (mg === 1 ? '1 mês grátis' : mg + ' meses grátis') : pct(x.pct) + '% a menos'}.</span></div>
      <div class="dica-v">${x.estimado ? '<i>cerca de</i>' : ''}${brl(realDe(x).real, 0)}<small>por ano</small></div></div>
    <div class="dica-calc">${ic('wallet', 'ic-s')}<span>Desconto de ${brl(realDe(x).desconto, 0)} menos ${brl(realDe(x).rende, 0)} que o dinheiro das mensalidades renderia ${esc(realDe(x).rs.onde)}, já com IR.</span></div>
    <div class="dica-fonte">${ic('check', 'ic-s')}<span>Preço conferido em <a href="${esc(x.fonte)}" target="_blank" rel="noopener">${esc(x.dominio)}</a>${quando ? ' em ' + quando : ''}${x.origem === 'fixo' ? '' : ' · cobrança das suas faturas'}</span></div>
    <div class="dica-acoes"><button class="btn peq pri" data-a="dica-anual" data-v="${esc(x.id)}">Mudar para anual</button><button class="btn peq" data-a="dica-fora" data-v="${esc(x.id)}">Agora não</button></div>
  </div>`;
}

function linhaDicaCategoria(c) {
  const k = catDe(c.cat);
  const per = `${MESES_LONGOS[+c.ant[2].slice(5) - 1]} a ${MESES_LONGOS[+c.ant[0].slice(5) - 1]}`;
  return `<div class="dica">
    <div class="dica-cab"><span class="dica-ic alerta">${ic('trend')}</span>
      <div class="dica-t"><b>${esc(k?.nome || 'Categoria')} acima da média</b>
        <span>Em ${MESES_LONGOS[+c.ym.slice(5) - 1]} foram ${brl(c.v, 0)}, ${brl(c.dif, 0)} a mais que a média de ${per}.</span></div>
      <div class="dica-v alerta">+${brl(c.dif, 0)}<small>no mês</small></div></div>
    <div class="dica-fonte">${ic('fluxo', 'ic-s')}<span>Pelos seus lançamentos</span></div>
    <div class="dica-acoes"><button class="btn peq out" data-a="dica-cat" data-v="${esc(c.ym)}">Ver categorias</button><button class="btn peq" data-a="dica-fora" data-v="${esc(c.id)}">Agora não</button></div>
  </div>`;
}

function cardDicas() {
  if (!temCaixa() || S.d.ajustes.dicas === false) return '';
  const { subs, cat } = dicasVisiveis();
  // os preços só são conferidos com a IA: desligada, o servidor só abre as páginas e não confere nada
  const conferindo = iaOn() && S.dicas && S.dicas.conferindo && (S.dicas.assinaturas || []).some(a => a.status === 'conferindo');
  if (!subs.length && !cat) {
    return conferindo ? `<div class="card dicas"><div class="rot">${rotIc('percent', 'bom')}<span class="rot-t">Dicas de economia</span></div>
      <div class="dica-conf"><span class="giro"></span>Conferindo os preços das suas assinaturas nas páginas oficiais…</div></div>` : '';
  }
  const total = subs.reduce((s, x) => s + realDe(x).real, 0);
  return `<div class="card dicas"><div class="rot">${rotIc('percent', 'bom')}<span class="rot-t">Dicas de economia</span>${total ? `<b>${subs.length > 1 ? 'até ' : ''}${brl(total, 0)} por ano</b>` : ''}</div>
    ${subs.slice(0, 3).map(linhaDicaAssinatura).join('')}${cat ? linhaDicaCategoria(cat) : ''}
    ${subs.length > 3 ? `<button class="link" data-a="tab" data-v="mais" data-ancora="dicas">Ver as ${subs.length} dicas</button>` : ''}</div>`;
}

function cardDicasMais() {
  const st = S.dicas;
  const catalogo = (st && st.catalogo) || ['Nabu Casa', 'Claude', 'Spotify', 'Microsoft 365', 'Deezer'];
  const fora = (S.d.ajustes.dicas_fora || []).length;
  const subs = (st && st.assinaturas) || [];
  let h = `<section class="card" id="dicas">${maisCab('percent', 'Dicas de economia')}
    ${maisLead(`Assinaturas dos fixos e faturas com plano anual mais barato, pelo preço da página oficial. Reconhece ${esc(juntarE(catalogo))}.`)}`;
  if (S.d.ajustes.dicas === false) return h + `<div class="status manual">Desligadas em Mais › Configurações › Opções.</div></section>`;
  // conferir o plano anual depende da IA; as dicas de categoria acima da média, não
  if (!iaOn()) return h + `<div class="status manual">Com a IA desligada, os planos anuais não são conferidos.</div></section>`;
  if (!st) h += `<div class="status manual">Carregando…</div>`;
  else if (!subs.length) h += `<div class="status manual">Nenhuma dessas assinaturas nos seus fixos ou faturas.</div>`;
  else {
    h += subs.map(a => {
      const er = a.status === 'ok' ? economiaReal(a.valor, a.preco_anual) : null;
      const txt = !er ? a.texto : er.real >= 10
        ? `No plano anual você economiza ${a.estimado ? 'cerca de ' : ''}${brl(er.real, 0)} por ano, já descontando o que o dinheiro renderia ${er.rs.onde}.`
        : `O anual tem ${brl(er.desconto, 0)} de desconto, mas o dinheiro rendendo ${er.rs.onde} daria quase o mesmo. Não vale trocar.`;
      const quando = a.conferido && !['conferindo', 'ja_anual'].includes(a.status) ? ` Conferido em ${fData(pData(a.conferido))}.` : '';
      const mesmoNome = semAcento(a.descricao) === semAcento(a.nome);
      return `<div class="ass-row"><span class="ini" style="--c:${corCat(a)}">${esc((a.nome || '?').slice(0, 1))}</span>
        <div class="op-t"><b>${esc(a.descricao)}</b><span>${brl(a.valor)} ${a.freq_anual ? 'por ano' : 'por mês'}${mesmoNome ? '' : ' · ' + esc(a.nome)}${a.origem === 'lancamentos' ? ' · nas faturas' : ''}</span><span class="ass-st ${a.status === 'ok' ? 'ok' : ''}">${esc(txt)}${quando}</span></div></div>`;
    }).join('');
  }
  // quando o app procurou assinaturas e conferiu os preços pela última vez (sozinho, uma vez por dia, ou no Conferir agora)
  if (st) h += `<p class="dica-quando">${ic('clock', 'ic ic-s')}<span>${st.conferindo ? 'Conferindo agora…' : st.atualizado ? `Última verificação: ${quandoLongo(st.atualizado)}.` : 'Ainda não verificado. Toque em Conferir agora.'}</span></p>`;
  h += `<div class="dica-btns"><button class="btn out" data-a="dicas-conferir"${st && st.conferindo ? ' disabled' : ''}>${ic('refresh')}${st && st.conferindo ? 'Conferindo…' : 'Conferir agora'}</button>
    ${fora ? `<button class="btn" data-a="dicas-voltar">Mostrar dispensadas (${fora})</button>` : ''}</div>`;
  if (st && st.dolar && st.dolar.valor) h += `<p class="nota" style="margin:12px 0 0">Planos em dólar: dólar do Banco Central (${brl(st.dolar.valor)} em ${esc(st.dolar.data || '')}) mais IOF e câmbio do cartão.</p>`;
  return h + `</section>`;
}

// "hoje às 15:45", "ontem às 09:10", "28/10 às 14:20"
function quandoLongo(isoTxt) {
  const d = new Date(isoTxt);
  if (!Number.isFinite(d.getTime())) return '';
  const hm = d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  const k = iso(d), hj = iso(hoje()), on = iso(new Date(hoje().getTime() - 864e5));
  return k === hj ? `hoje às ${hm}` : k === on ? `ontem às ${hm}` : `${fDataC(d)}${d.getFullYear() !== hoje().getFullYear() ? '/' + d.getFullYear() : ''} às ${hm}`;
}

/* --------- mudar para o plano anual */
let DA = null;
function abrirDicaAnual(id) {
  const x = ((S.dicas && S.dicas.dicas) || []).find(d => d.id === id);
  if (!x) { toast('Essa dica não está mais disponível.'); return; }
  const hj = iso(hoje());
  let data = dataNoMes(ymHoje(), x.dia);
  if (data <= hj) data = dataNoMes(addYm(ymHoje(), 1), x.dia);
  DA = { x, valor: x.preco_anual, data, erro: '' };
  abrirFolha(montarDicaAnual);
}
function ecoDA() {
  const e = economiaReal(DA.x.valor, +DA.valor || 0);
  if (e.desconto <= 0.005) return 'Com esse valor, o anual não sai mais barato.';
  if (e.real <= 0.005) return `O desconto é de ${brl(e.desconto)}, mas deixar o dinheiro rendendo ${esc(e.rs.onde)} e pagar por mês sai melhor.`;
  return `Você economiza <b>${brl(e.real)}</b> por ano: ${brl(e.desconto)} de desconto menos ${brl(e.rende)} que o dinheiro renderia ${esc(e.rs.onde)}, já com IR.`;
}
function montarDicaAnual() {
  const { x } = DA, mes = MESES_LONGOS[+DA.data.slice(5, 7) - 1];
  const corpo = `<p class="da-intro">Troque para o plano anual em <a href="${esc(x.fonte)}" target="_blank" rel="noopener">${esc(x.dominio)}</a> e confirme aqui: ${x.origem === 'fixo' ? 'o fixo mensal para e entra um anual.' : 'entra um fixo anual.'}</p>
    <div class="cmp-anual"><div><span>Hoje</span><b>${brl(x.valor)}</b><small>por mês · ${brl(12 * x.valor, 0)} por ano</small></div>
      <div><span>No anual</span><b>${fmtPreco(x.anual, x.moeda)}</b><small>por ano, na página oficial</small></div></div>
    <div class="campo"><label for="da-valor">Valor da cobrança anual</label><div class="pref grande${DA.erro ? ' erro' : ''}"><span>R$</span><input id="da-valor" data-da="valor" inputmode="numeric" value="${DA.valor ? NF2.format(DA.valor) : ''}"></div>
      <div class="ajuda">${x.estimado ? `Estimado no câmbio de hoje: ${fmtPreco(x.anual, x.moeda)}.` : `Preço da página oficial.`}</div>${DA.erro ? `<div class="msg-erro">${DA.erro}</div>` : ''}</div>
    <div class="campo"><label for="da-data">Primeira cobrança anual</label><input id="da-data" class="inp" type="date" data-da="data" value="${esc(DA.data)}">
      <div class="ajuda">Todo ano em ${mes}${x.cartao ? ', na fatura do cartão' : ''}.</div></div>
    <div class="eco-linha" id="da-eco">${ecoDA()}</div>`;
  return { titulo: `${esc(x.nome)} no plano anual`, corpo, pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="da-ok">Mudar para anual</button>` };
}
function confirmarDicaAnual() {
  const { x } = DA;
  if (!(DA.valor > 0)) { DA.erro = 'Coloque o valor.'; pintarFolha(); return; }
  if (!pData(DA.data)) { DA.erro = 'Data inválida.'; pintarFolha(); return; }
  const ym = ymDe(DA.data);
  persistir(d => {
    const r = x.rid ? d.recorrencias.find(y => y.id === x.rid) : null;
    if (r) {
      if (ym <= r.inicio) d.recorrencias = d.recorrencias.filter(y => y.id !== r.id); else r.fim = addYm(ym, -1);
      d.lancamentos = d.lancamentos.filter(l => !(l.recorrencia === r.id && l.competencia >= ym && !l.pago));
    }
    const base = r || x;
    d.recorrencias.push({ id: 'r-' + uid(), tipo: 'despesa', descricao: base.descricao || x.nome, valor: round2(DA.valor), categoria: base.categoria || '',
      conta: base.conta || '', cartao: !!base.cartao, obs: '', dia: +DA.data.slice(8, 10), inicio: ym, fim: null, freq: 'anual' });
  }, 'Pronto: agora é anual').then(ok => { if (ok) { fecharFolha(); carregarDicas(); } });
}

/* --------- formulário: créditos e descontos do recebimento */
const DESC_RAPIDOS = [
  ['INSS', 'pct', 'c-impostos'], ['Imposto de renda', 'pct', 'c-impostos'], ['Taxa administrativa', 'pct', 'c-impostos'], ['Outro imposto', 'pct', 'c-impostos'],
];
// despesas ligadas a este recebimento (no formulário): as já cadastradas e as que a IA achou no recibo
function ligadosDoForm(f) {
  const out = [];
  if (f.recorrencia) {
    const ym = f.competencia || ymDe(f.data);
    for (const r of S.d.recorrencias) {
      if (r.tipo === 'receita' || r.vinculo !== f.recorrencia || !ativaEm(r, ym)) continue;
      const m = recMat().get(r.id + '|' + ym);
      if (m && m.pulado) continue;
      out.push({ descricao: r.descricao, valor: +(m ? m.valor : r.valor) || 0, existe: true });
    }
  }
  (f.ligadosNovos || []).forEach((n, i) => { if (!out.some(o => semAcento(o.descricao) === semAcento(n.descricao))) out.push(Object.assign({ i }, n)); else if (n.sel) { const o = out.find(o2 => semAcento(o2.descricao) === semAcento(n.descricao)); o.valor = n.valor; o.atualiza = true; } });
  return out;
}
const NFP4 = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 4 });
const lfComo = f => ({ id: 'lf', tipo: 'receita', valor: f.valor, descontos: f.descontos });
function resumoDescHTML(f) {
  const l = lfComo(f), lig = ligadosDoForm(f).filter(o => o.existe || o.sel).reduce((s2, o) => s2 + o.valor, 0);
  const desc = round2(totalDescontos(l) + lig), liq = round2((+f.valor || 0) - desc);
  let h = `<div><span>Bruto</span><b>${brl(+f.valor || 0)}</b></div><div><span>Descontos</span><b class="sai">− ${brl(desc)}</b></div>
    <div class="liq"><span>Líquido</span><b>${brl(liq)}</b><small>cai na conta</small></div>`;
  if (f.recibo && f.recibo.liquido) {
    const ok = Math.abs(liq - f.recibo.liquido) < 0.05;
    h += `<p class="desc-conf ${ok ? 'ok' : 'erro'}">${ic(ok ? 'check' : 'alert', 'ic-s')}${ok ? `Confere com o líquido do recibo: ${brl(f.recibo.liquido)}.` : `O recibo diz líquido de ${brl(f.recibo.liquido)}; aqui deu ${brl(liq)}. Confira os valores.`}</p>`;
  }
  return h;
}
function secaoDescontos(f) {
  if (f.tipo !== 'receita' || f.repete === 'parcelado' || f.ajuste) return '';
  const lig = ligadosDoForm(f);
  if (!f.descontos.length && !lig.length && !f.descAberto) {
    return `<div class="campo"><button class="abre" data-a="lf-desc-abrir">${ic('plus', 'ic-s')}Descontos na fonte (impostos, plano de saúde)</button></div>`;
  }
  const l = lfComo(f);
  let h = `<div class="campo desc-sec"><div class="desc-cab"><div class="lbl">Impostos na fonte</div>
    <button class="btn peq out" data-a="lf-ler-recibo"${f.lendoRecibo ? ' disabled' : ''}>${f.lendoRecibo ? '<span class="giro mini"></span>Lendo…' : ic('ia', 'ic-s') + 'Ler recibo com IA'}</button></div>`;
  h += f.descontos.map((x, i) => `<div class="desc-ed2">
    <input class="inp" data-lfd="descricao" data-i="${i}" value="${esc(x.descricao)}" placeholder="Ex.: INSS" aria-label="Nome do imposto" autocomplete="off">
    ${x.modo === 'fixo' // um desconto em reais (de dados antigos): fica em reais
      ? `<div class="pref"><span>R$</span><input data-lfd="valor" data-i="${i}" inputmode="numeric" value="${x.valor ? NF2.format(x.valor) : ''}" placeholder="0,00" aria-label="Valor do desconto"></div>`
      : `<div class="pref"><input data-lfd="valor" data-i="${i}" inputmode="decimal" value="${x.valor ? NFP4.format(x.valor) : ''}" placeholder="0" aria-label="Porcentagem do bruto"><span>%</span></div>`}
    <button class="icbtn" data-a="lf-desc-rm" data-v="${i}" aria-label="Tirar imposto">${ic('x')}</button>
    <b class="desc-v" id="lfd-v-${i}">− ${brl(valorDesc(l, x))}</b></div>`).join('');
  h += `<div class="chips" style="margin:6px 0 0">${DESC_RAPIDOS.map(([n], k) => [n, k]).filter(([n]) => n === 'Outro imposto' || !f.descontos.some(x => semAcento(x.descricao) === semAcento(n))).map(([n, k]) =>
    `<button class="chip add" data-a="lf-desc-add" data-v="${k}">${ic('plus', 'ic-s')}${n}</button>`).join('')}</div>`;
  h += `<div class="ajuda">Porcentagem do bruto, lançada em Impostos e taxas.</div>`;
  h += `<div class="sub-lbl">Outros descontos ligados</div>`;
  if (lig.length) {
    h += lig.map(o => `<div class="lig-l">${o.existe ? ic('repeat', 'ic-s') : `<input type="checkbox" data-lfn="${o.i}"${o.sel ? ' checked' : ''} aria-label="Criar ${esc(o.descricao)}">`}
      <span>${esc(o.descricao)}${o.existe ? (o.atualiza ? ' · valor do recibo neste mês' : '') : f.recorrencia || f.repete === 'mensal' || f.repete === 'anual' ? ' · nova despesa fixa ligada' : ' · despesa no mesmo dia'}</span><b>− ${brl(o.valor)}</b></div>`).join('');
  }
  h += `<div class="ajuda">${f.recorrencia || f.repete === 'mensal'
    ? 'Outros descontos (plano de saúde…): na despesa, em "Como é pago", escolha este recebimento.'
    : 'Para ligar outros descontos, o recebimento precisa ser fixo (Repetir: Todo mês).'}</div>`;
  h += `<div class="desc-res" id="lf-desc-res">${resumoDescHTML(f)}</div></div>`;
  return h;
}

function atualizarDescontosVivo() {
  const f = LF, l = lfComo(f);
  if (f.partes.length) { f.valor = somaPartes(f.partes); const b = $('#lf-bruto'); if (b) b.textContent = NF2.format(f.valor); }
  f.descontos.forEach((x, i) => { const e = $('#lfd-v-' + i); if (e) e.textContent = '− ' + brl(valorDesc(l, x)); });
  const r = $('#lf-desc-res'); if (r) r.innerHTML = resumoDescHTML(f);
}
function addDesconto(k) {
  const [n, modo, cat] = DESC_RAPIDOS[k] || DESC_RAPIDOS[DESC_RAPIDOS.length - 1];
  LF.descontos.push({ id: 'd-' + uid(), descricao: n === 'Outro imposto' ? '' : n, modo, valor: 0, base: '', categoria: cat });
  LF.descAberto = true;
  pintarFolha();
}
function trocarModoDesc(i, modo) {
  const x = LF.descontos[i];
  if (!x || x.modo === modo) return;
  const l = lfComo(LF), v = valorDesc(l, x);
  if (modo === 'pct') { const b = +LF.valor || 0; x.valor = b > 0 ? Math.round(v / b * 1e6) / 1e4 : 0; x.base = ''; }
  else x.valor = v;
  x.modo = modo;
  pintarFolha();
}
// imposto em % do bruto: um percentual redondo (1 casa) quando reproduz o valor; senão o percentual exato (até 4 casas)
function pctDoBruto(v, bruto) {
  if (!(bruto > 0) || !(v > 0)) return 0;
  const p1 = Math.round(v / bruto * 1000) / 10;
  if (p1 > 0 && Math.abs(round2(bruto * p1 / 100) - v) <= 0.011) return p1;
  return Math.round(v / bruto * 1e6) / 1e4;
}
function aplicarRecibo(h) {
  const bruto = round2(h.total_creditos || h.creditos.reduce((s, c) => s + (+c.valor || 0), 0));
  const descontos = h.debitos.filter(dv => dv.tipo === 'imposto')
    .map(dv => ({ id: 'd-' + uid(), descricao: dv.descricao, modo: 'pct', valor: pctDoBruto(dv.valor, bruto), base: '', categoria: 'c-impostos' }));
  const ligadosNovos = h.debitos.filter(dv => dv.tipo !== 'imposto')
    .map(dv => ({ descricao: dv.descricao, valor: round2(dv.valor), categoria: dv.tipo === 'saude' ? 'c-saude' : 'c-outros-gastos', sel: true }));
  Object.assign(LF, { partes: [], valor: bruto, descontos, ligadosNovos, descAberto: true, recibo: { liquido: h.liquido || 0 } });
  if (!LF.id && h.data) LF.data = h.data;
  if (!LF.descricao) LF.descricao = 'Salário';
  if (!LF.categoria) LF.categoria = 'c-salario';
}
async function lerRecibo() {
  const file = await escolherArquivo('application/pdf,image/*');
  if (!file) return;
  const pdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name);
  if (!pdf && !/^image\//.test(file.type)) { toast('Envie o recibo em PDF ou imagem.'); return; }
  LF.lendoRecibo = true; pintarFolha();
  try {
    const b64 = pdf ? await lerArquivo(file) : await imagemJPG(file);
    const r = await api.iaLer({ modo: 'holerite', anexo: { b64 } });
    const h = r.holerite || {};
    if (!(h.total_creditos > 0) && !(h.creditos || []).length) { toast('A IA não achou o valor bruto nesse arquivo.'); return; }
    aplicarRecibo(h);
    toast('Recibo lido. Confira antes de salvar.');
  } catch (e) { toast('Não consegui ler o recibo. ' + e.message); }
  finally { if (LF) { LF.lendoRecibo = false; pintarFolha(); } }
}
function criarLigados(d, f, rid, rec) {
  const ym = rec.competencia || ymDe(rec.data);
  for (const n of (f.ligadosNovos || []).filter(x => x.sel && x.valor > 0)) {
    const r = d.recorrencias.find(x => x.tipo !== 'receita' && x.vinculo === rid && !x.fim && semAcento(x.descricao) === semAcento(n.descricao));
    if (r) {
      if (Math.abs((+r.valor || 0) - n.valor) < 0.005) continue;
      const m = d.lancamentos.find(l => l.recorrencia === r.id && l.competencia === ym);
      // o recibo traz o plano: se ele tinha sido apagado só deste mês, volta (senão o caixa não bate com o líquido)
      if (m) { m.valor = n.valor; if (m.pulado) { delete m.pulado; m.pago = !!rec.pago; } }
      else d.lancamentos.push(materializar(Object.assign({}, r, { valor: n.valor, data: rec.data, recorrencia: r.id, competencia: ym, pago: !!rec.pago, conta: rec.conta || r.conta, cartao: false })));
    } else {
      d.recorrencias.push({ id: 'r-' + uid(), tipo: 'despesa', descricao: n.descricao, valor: n.valor, categoria: n.categoria, conta: rec.conta || '', cartao: false,
        obs: '', dia: +String(rec.data).slice(8, 10) || 1, inicio: ym, fim: null, vinculo: rid });
    }
  }
}
function limparDescontos(f) {
  const partes = [], ids = new Set();
  const descontos = f.descontos.filter(x => +x.valor > 0).map(x => ({ id: x.id, descricao: (x.descricao || '').trim() || 'Desconto', modo: x.modo === 'pct' ? 'pct' : 'fixo',
    valor: x.modo === 'pct' ? Math.round(+x.valor * 1e4) / 1e4 : round2(x.valor), base: x.modo === 'pct' && ids.has(x.base) ? x.base : '', categoria: x.categoria || '' }));
  return { partes, descontos };
}
function linhaDesc(d) {
  const cat = catDe(d.categoria);
  return `<div class="lanc sub" data-a="lanc" data-id="${esc(d.id)}" role="button" tabindex="0">
    <span class="ini" style="--c:${corCat(d)}">${esc((d.descricao || '?').slice(0, 1).toUpperCase())}</span>
    <span class="lanc-t"><b>${esc(d.descricao)}</b><span>${esc([cat?.nome || 'Sem categoria', regraDesc(d), d.pago ? NA_FONTE : 'na fonte'].join(' · '))}</span></span>
    <span class="lanc-d"><b class="sai">− ${brl(d.valor)}</b></span></div>`;
}
function linhaLigada(x) {
  const cat = catDe(x.categoria);
  return `<div class="lanc sub" data-a="lanc" data-id="${esc(x.id)}" role="button" tabindex="0">
    <span class="ini" style="--c:${corCat(x)}">${esc((x.descricao || '?').slice(0, 1).toUpperCase())}</span>
    <span class="lanc-t"><b>${esc(x.descricao)}</b><span>${esc([cat?.nome || 'Sem categoria', x.recorrencia ? 'fixo' : '', x.pago ? 'já pago, descontado' : 'baixa junto'].filter(Boolean).join(' · '))}</span></span>
    <span class="lanc-d"><b class="sai">− ${brl(+x.valor || 0)}</b></span></div>`;
}
function blocoDescontos(l, ligados = []) {
  const ds = descontosDe(l);
  const n = ds.length + ligados.length;
  if (!n) return '';
  const aberto = S.ui.descAberto === l.id;
  const soma = ds.reduce((s2, d) => s2 + d.valor, 0) + ligados.reduce((s2, x) => s2 + (+x.valor || 0), 0);
  return `<button class="desc-tog${aberto ? ' on' : ''}" data-a="desc-abrir" data-v="${esc(l.id)}" aria-expanded="${aberto}">${ic('chev', 'ic-s')}<span>${n === 1 ? '1 desconto' : n + ' descontos'} · líquido ${brl(liquidoDe(l) - ligados.reduce((s2, x) => s2 + (+x.valor || 0), 0))}</span><b>− ${brl(soma)}</b></button>`
    + (aberto ? `<div class="desc-itens">${ds.map(linhaDesc).join('')}${ligados.map(linhaLigada).join('')}</div>` : '');
}

function cardCategorias() {
  const grupo = tipo => S.d.categorias.filter(c => c.tipo === tipo).map(c =>
    `<button class="chip" data-a="categoria" data-id="${esc(c.id)}" style="--c:${corOk(c.cor) || '#B8B0B0'}"><span class="bol"></span>${esc(c.nome)}</button>`).join('');
  return `<section class="card" id="categorias">${maisCab('layers', 'Categorias')}
    ${maisLead('Toque numa categoria para mudar o nome ou a cor.')}
    <h3>Gastos</h3><div class="chips">${grupo('despesa')}<button class="chip add" data-a="categoria-nova" data-v="despesa">${ic('plus', 'ic-s')}Nova</button></div>
    <h3>Recebimentos</h3><div class="chips" style="margin:0">${grupo('receita')}<button class="chip add" data-a="categoria-nova" data-v="receita">${ic('plus', 'ic-s')}Nova</button></div></section>`;
}
// só os que ainda vão acontecer (um fixo parado some da lista; o que ele já lançou continua no caixa)
function fixosAtivos() {
  const ym = ymHoje();
  return S.d.recorrencias.filter(r => { for (let k = 1; k <= 12; k++) if (ativaEm(r, addYm(ym, k))) return true; return false; });
}
function cardFixos() {
  const ativos = fixosAtivos();
  if (!ativos.length) return '';
  const quando = r => (r.freq === 'anual' ? `Todo ano, ${r.dia} de ${MESES_LONGOS[+String(r.inicio).slice(5) - 1]}` : `Todo dia ${r.dia}`) + (r.fim ? ` · até ${nomeMes(r.fim, true)}` : '');
  const linha = r => `<button class="banco-row" data-a="fixo" data-id="${esc(r.id)}"><span class="ini" style="--c:${corCat(r)}">${esc((r.descricao || '?').slice(0, 1).toUpperCase())}</span>
    <div class="op-t"><b>${esc(r.descricao)}</b><span>${quando(r)}${r.conta ? ' · ' + esc(nomeConta(contaDe(r.conta))) + (r.cartao ? ' · cartão' : '') : ''}</span></div>
    <span class="op-n ${r.tipo === 'receita' ? 'ent' : 'sai'}">${brl(r.valor, 0)}<small>${r.freq === 'anual' ? 'por ano' : temDescontos(r) ? 'líquido ' + brl(liquidoDe(r), 0) : 'padrão'}</small></span>${ic('chev', 'chev')}</button>`;
  const mensais = ativos.filter(r => r.freq !== 'anual'), anuais = ativos.filter(r => r.freq === 'anual');
  const rec = mensais.filter(r => r.tipo === 'receita'), des = mensais.filter(r => r.tipo !== 'receita');
  const soma = l => l.reduce((s, r) => s + (+r.valor || 0), 0);
  return `<section class="card" id="fixos">${maisCab('repeat', 'Fixos', brl(soma(rec) - soma(des), 0) + ' por mês')}
    ${maisLead('Entram sozinhos nos próximos meses. Toque para mudar ou parar.')}
    ${rec.length ? `<h3>Recebimentos · ${brl(soma(rec), 0)}</h3>${rec.map(linha).join('')}` : ''}
    ${des.length ? `<h3 style="margin-top:14px">Gastos · ${brl(soma(des), 0)}</h3>${des.map(linha).join('')}` : ''}
    ${anuais.length ? `<h3 style="margin-top:14px">Uma vez por ano</h3>${anuais.map(linha).join('')}` : ''}</section>`;
}
function cardIA() {
  const on = iaOn();
  const chaveIA = linhaChave('ia', on, 'Usar IA', on
    ? 'Ligado: Ler com IA, Ler recibo, Falar, Conversar com a IA, Atualizar saldos e os preços das dicas.'
    : 'Desligado: os botões de IA somem em todos os aparelhos.');
  const cab = `<section class="card" id="ia">${maisCab('ia', 'Leitura por IA')}
    ${maisLead('Usa a IA configurada no Home Assistant; o app não guarda chave.')}
    ${chaveIA}`;
  if (!on) return cab + `</section>`;
  const s = S.ia;
  let st;
  if (DEMO) st = ['', 'Na prévia, a leitura por IA é simulada.'];
  else if (!s) st = ['manual', 'Verificando a IA do Home Assistant…'];
  else if (s.pronta) st = ['', `Pronta. Usando ${s.selecionada ? esc((s.entidades.find(e => e.id === s.selecionada) || {}).nome || s.selecionada) : 'a IA padrão do Home Assistant'}.`];
  else st = ['erro', esc(s.motivo || 'A IA não está pronta.')];
  const ents = (s && s.entidades) || [];
  const v = S.voz;
  // o microfone só aparece com a IA pronta (vozPronta): com ela fora do ar, não diz que está pronto
  const fala = DEMO ? ['', 'Falar: na prévia, a fala é simulada.'] : !v ? ['manual', 'Falar: verificando o assistente de voz…']
    : v.pronta && s && s.pronta === false ? ['manual', 'Falar: só com a IA pronta.']
    : v.pronta ? ['', `Falar: pronto. A voz vira texto com ${v.nome ? `“${esc(v.nome)}”` : 'a fala para texto do Home Assistant'}; quem entende e separa os lançamentos é a IA usada pelo app. O microfone fica no alto de cada tela.`] : ['manual', `Falar: ${esc(v.motivo || 'não está pronto.')}`];
  const falas = (v && v.opcoes) || [];
  return cab + `<div class="status ${st[0]}">${st[1]}</div><div class="status ${fala[0]}" style="margin-top:-6px">${fala[1]}</div>
    <div class="campo"><label class="lbl" for="ia-ent">IA usada pelo app</label><select id="ia-ent" class="inp" data-ajuste-sel="ia_entidade">
      <option value="">Padrão do Home Assistant</option>${ents.map(e => `<option value="${esc(e.id)}"${e.id === S.d.ajustes.ia_entidade ? ' selected' : ''}>${esc(e.nome)}${e.imagens ? '' : ' (só texto)'}</option>`).join('')}</select></div>
    ${falas.length ? `<div class="campo"><label class="lbl" for="voz-motor">Fala para texto</label><select id="voz-motor" class="inp" data-ajuste-sel="voz_motor">
      <option value="">Padrão do Home Assistant</option>${falas.map(o => `<option value="${esc(o.id)}"${o.id === (S.d.ajustes.voz_motor || '') ? ' selected' : ''}>${esc(o.nome)}</option>`).join('')}</select></div>` : ''}
    <button class="btn out" data-a="ia-verificar">${ic('refresh')}Verificar de novo</button>
    <p class="nota" style="margin:12px 0 0">Para imagem e PDF, a IA precisa aceitar anexos.</p></section>`;
}

/* --------- Faturas por e-mail: a integração IMAP do Home Assistant (o Gmail, com uma senha de app) avisa cada e-mail
   novo; o servidor pega o PDF da fatura, abre com as Senhas dos PDFs e lê com a IA. A fatura lida espera a conferência
   (um aviso no Início); nada é lançado sozinho. */
const emailOn = () => S.d.ajustes.email === true && iaOn();
const EMAIL_PEND = ['conferir', 'senha', 'lendo', 'erro'];
const EMAIL_ST = { lendo: 'Lendo…', conferir: 'Para conferir', senha: 'Precisa da senha', erro: 'Não li', fora: 'Não é fatura', feito: 'Lançada', ignorado: 'Ignorada' };
function aplicarEmails(r) {
  S.emails = r;
  clearTimeout(S.emailsTimer);
  // alguma sendo lida pela IA: olha de novo daqui a pouco
  if (r && (r.itens || []).some(x => x.estado === 'lendo')) S.emailsTimer = setTimeout(() => carregarEmails(), 4000);
  render();
  return r;
}
function carregarEmails(forcar) {
  if (!emailOn()) { S.emails = null; return Promise.resolve(null); }
  if (S.emailsPedido) return S.emailsPedido;
  S.emailsPedido = api.emails(forcar).then(r => r, () => S.emails || null).then(r => { S.emailsPedido = null; return aplicarEmails(r); });
  return S.emailsPedido;
}
function emailAcao(acao, id, msg) {
  return api.emailAcao(acao, id).then(r => { if (msg) toast(msg); return aplicarEmails(r); }).catch(e => toast(e.message));
}
const emailsPendentes = () => (emailOn() && S.emails && S.emails.itens ? S.emails.itens.filter(x => EMAIL_PEND.includes(x.estado)) : []);
function totalEmail(it) {
  return ((it.resultado || {}).lancamentos || []).reduce((a, x) => a + (x.tipo === 'receita' ? -1 : 1) * (+x.valor || 0), 0);
}
function resumoEmail(it) {
  if (it.estado === 'lendo') return 'lendo com IA…';
  if (it.estado === 'senha') return 'o PDF tem senha';
  if (it.estado === 'erro') return it.erro || 'não consegui ler';
  const r = it.resultado || {}, l = r.lancamentos || [], v = r.investimentos || [];
  return l.length ? plural(l.length, 'lançamento', 'lançamentos') : plural(v.length, 'investimento', 'investimentos');
}
// no Início, junto dos avisos: cada fatura que chegou e ainda não foi lançada nem ignorada
function avisosEmail() {
  return emailsPendentes().map(it => {
    const t = it.estado === 'conferir' ? totalEmail(it) : 0;
    const cls = it.estado === 'erro' ? ' alerta' : it.estado === 'senha' ? ' neutro' : ' terc';
    return `<button class="op" data-a="email-abrir" data-v="${esc(it.id)}"${it.estado === 'lendo' ? ' disabled' : ''}><div class="op-ic${cls}">${ic(it.estado === 'senha' ? 'lock' : it.estado === 'erro' ? 'alert' : 'mail')}</div>
      <div class="op-t"><b>Fatura ${esc(it.de || it.endereco)}</b><span>Por e-mail · ${esc(resumoEmail(it))}</span></div>
      ${t > 0 ? `<div class="op-n">${brl(t, 0)}</div>` : ''}${it.estado === 'lendo' ? '<span class="giro peq"></span>' : ic('chev', 'chev')}</button>`;
  });
}
// tocar no aviso: a conferência do que a IA leu; com senha, o PDF com o campo da senha; com erro, lê de novo
function abrirEmail(id) {
  const it = ((S.emails && S.emails.itens) || []).find(x => x.id === id);
  if (!it || it.estado === 'lendo') return;
  if (it.estado === 'erro') { emailAcao('ler', id, 'Lendo de novo'); return; }
  abrirIA('caixa');
  Object.assign(IAS, { email: id, so: 'arquivo' });
  if (it.estado === 'conferir') { iaResultado(clone(it.resultado)); return; }
  IAS.erro = 'Abrindo o PDF…';
  pintarFolha();
  api.emailPdf(id).then(r => {
    if (!IAS || IAS.email !== id) return;
    Object.assign(IAS, { arquivo: { nome: r.nome, pdf: true, dataUrl: r.b64 }, pedeSenha: true, erro: it.erro || 'Este PDF tem senha.' });
    pintarFolha();
    setTimeout(() => { const i = $('#ia-senha'); if (i) i.focus(); }, 60);
  }).catch(e => { if (IAS && IAS.email === id) { IAS.erro = e.message; pintarFolha(); } });
}
function cardEmail() {
  const a = S.d.ajustes, on = a.email === true;
  if (on && S.emails === undefined) carregarEmails(true);
  const E = S.emails;
  let h = `<section class="card" id="email">${maisCab('mail', 'Faturas por e-mail')}
    ${maisLead('As faturas que chegam no seu e-mail são lidas pela IA e esperam a conferência no Início.')}
    ${linhaChave('email', on, 'Ler as faturas do e-mail', on ? (E && E.conectada ? 'Ligado: recebendo os e-mails pelo Home Assistant.' : 'Ligado.') : 'Desligado.')}`;
  if (!on) return h + '</section>';
  // a conta de e-mail é a integração IMAP do Home Assistant
  const C = E ? E.contas : undefined;
  if (!E) h += `<div class="status manual">Procurando as contas de e-mail…</div>`;
  else if (!C) h += `<div class="status manual">Não consegui ver as contas de e-mail do Home Assistant.</div>`;
  else if (!C.length) h += `<div class="status manual">Nenhuma conta de e-mail no Home Assistant. Adicione a integração IMAP: no Gmail, imap.gmail.com, porta 993, com uma senha de app.</div>`;
  else h += `<div class="status${C.every(c => c.ok) && E.conectada ? '' : ' manual'}">${C.map(c => esc(c.nome) + (c.ok ? '' : ' (com erro no Home Assistant)')).join(' · ')}${E.conectada ? '' : ' · conectando…'}</div>`;
  const de = a.email_de || [];
  h += `<div class="campo email-campo"><label for="email-de">De quem</label>
    ${de.length ? `<div class="chips email-de">${de.map(r => `<button class="chip on" data-a="email-de-rm" data-v="${esc(r)}" aria-label="Tirar ${esc(r)}">${esc(r)}${ic('x', 'ic-s')}</button>`).join('')}</div>` : ''}
    <div class="email-add"><input id="email-de" class="inp" placeholder="Ex.: bancoazul.com.br" autocomplete="off" autocapitalize="off" spellcheck="false" inputmode="email" enterkeyhint="done"><button class="btn out" data-a="email-de-add">Adicionar</button></div>
    <div class="ajuda">${de.length ? 'Só os e-mails desses remetentes.' : 'Sem nenhum, os e-mails com PDF e “fatura” no assunto.'}</div></div>`;
  const L = ((E && E.itens) || []).slice(0, 5);
  if (L.length) h += `<h3 class="ia-sec">Recebidos</h3><div class="emails">${L.map(linhaEmail).join('')}</div>`;
  return h + '</section>';
}
function linhaEmail(it) {
  const ler = ['fora', 'erro', 'ignorado'].includes(it.estado);
  const dt = pData(String(it.data || it.recebido_em || '').slice(0, 10));
  return `<div class="email-l"><span><b>${esc(it.de || it.endereco)}</b><small>${esc(it.assunto || it.arquivo)}${dt ? ' · ' + fDataC(dt) : ''}</small></span>
    ${ler ? `<button class="btn out peq" data-a="email-ler" data-v="${esc(it.id)}">Ler</button>` : `<em class="email-st st-${it.estado}">${EMAIL_ST[it.estado]}</em>`}</div>`;
}
function emailDeAdicionar() {
  const i = $('#email-de'), v = String(i ? i.value : '').trim().toLowerCase().replace(/^.*<([^>]+)>.*$/, '$1').replace(/\s+/g, '').replace(/^@/, '');
  if (!v) { if (i) i.focus(); return; }
  if (i) i.value = '';
  persistir(d => { const l = d.ajustes.email_de || []; if (!l.includes(v)) d.ajustes.email_de = [...l, v].slice(0, 20); });
}

/* Senhas dos PDFs: as faturas com senha (ex.: os dígitos do CPF) abrem sozinhas na leitura por IA. As senhas ficam
   no servidor, fora das exportações; a tela só vê o nome e o fim (••••45). */
function cardSenhas() {
  if (S.senhas === undefined) carregarSenhas();
  const L = S.senhas;
  const linhas = !L ? `<div class="status manual">Carregando…</div>`
    : !L.length ? `<p class="nota" style="margin:0">Nenhuma senha cadastrada.</p>`
    : `<div class="senhas">${L.map(x => `<div class="senha-l">${ic('lock', 'ic-s')}<span><b>${esc(x.nome)}</b><small>${esc(x.fim)}</small></span>
        <button class="icbtn" data-a="senha-apagar" data-v="${esc(x.id)}" aria-label="Apagar a senha ${esc(x.nome)}">${ic('trash')}</button></div>`).join('')}</div>`;
  return `<section class="card" id="senhas-pdf">${maisCab('lock', 'Senhas dos PDFs')}
    ${maisLead('As faturas com senha abrem sozinhas na leitura por IA.')}
    ${linhas}
    <button class="btn out" data-a="senha-nova" style="margin-top:12px">${ic('plus')}Adicionar senha</button></section>`;
}
function carregarSenhas() {
  if (S.senhasPedido) return;
  S.senhasPedido = api.senhas().then(r => r.senhas, () => null).then(l => { S.senhas = l || []; S.senhasPedido = null; if (S.ui.maisTela === 'config') render(); });
}
let FS = null;
function abrirSenhaNova() {
  FS = { nome: '', senha: '', erro: '' };
  abrirFolha(() => ({
    titulo: 'Nova senha',
    corpo: `<div class="campo"><label for="sn-nome">Nome</label><input id="sn-nome" class="inp" data-fs="nome" value="${esc(FS.nome)}" placeholder="Ex.: CPF da Ana" autocomplete="off"></div>
      <div class="campo"><label for="sn-senha">Senha</label><input id="sn-senha" class="inp${FS.erro ? ' erro' : ''}" data-fs="senha" value="${esc(FS.senha)}" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Ex.: os 5 primeiros dígitos do CPF"></div>
      ${FS.erro ? `<div class="msg-erro">${esc(FS.erro)}</div>` : ''}`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="senha-salvar">Salvar</button>`,
  }), () => { FS = null; });
  setTimeout(() => { const i = $('#sn-nome'); if (i) i.focus(); }, 60);
}
function salvarSenhaNova() {
  if (!FS) return;
  if (!FS.senha.trim()) { FS.erro = 'Digite a senha.'; pintarFolha(); return; }
  api.senhaNova(FS.nome.trim(), FS.senha.trim()).then(r => { S.senhas = r.senhas; fecharFolha(); render(); toast('Senha guardada'); },
    e => { if (FS) { FS.erro = e.message; pintarFolha(); } });
}

const pessoasContas = () => [...new Set(S.d.bancos.flatMap(b => (b.contas || []).map(c => c.pessoa)).filter(Boolean))];
function resumoContas(b) {
  return (b.contas || []).map(c => (c.pessoa || 'Conta') + (c.cartao ? ' (cartão)' : '')).join(' · ');
}

let FB = null;
function abrirBanco(id, nome) {
  const b = id && S.d.bancos.find(x => x.id === id);
  const usadas = S.d.bancos.map(x => x.cor);
  const eu = S.usuario ? S.usuario.split(' ')[0] : (pessoasContas()[0] || '');
  FB = b ? clone(b) : { id: null, nome: nome || '', cor: CORES_BANCO.find(c => !usadas.includes(c)) || CORES_BANCO[0], obs: '', contas: [] };
  if (!FB.contas || !FB.contas.length) FB.contas = [{ id: 'k-' + uid(), pessoa: eu, cartao: false, fechamento: '', vencimento: '' }];
  FB.erro = '';
  abrirFolha(() => {
    const n = FB.id ? S.d.investimentos.filter(i => i.banco === FB.id).length : 0;
    return {
      titulo: FB.id ? 'Editar banco' : 'Novo banco',
      cab: FB.id ? `<button class="icbtn" data-a="b-excluir" aria-label="Excluir" style="color:var(--danger)">${ic('trash')}</button>` : '',
      corpo: `<div class="campo"><label for="b-nome">Nome</label><input id="b-nome" class="inp${FB.erro ? ' erro' : ''}" data-fb="nome" value="${esc(FB.nome)}" placeholder="Ex.: Nubank, XP, Sicredi" list="dl-b" autocomplete="off">
          <datalist id="dl-b">${BANCOS_COMUNS.map(x => `<option value="${esc(x)}">`).join('')}</datalist>${FB.erro ? `<div class="msg-erro">${FB.erro}</div>` : ''}</div>
        <div class="campo"><div class="lbl">Cor</div><div class="cores p">${PALETA.map(c => `<button class="cor${FB.cor === c ? ' on' : ''}" style="--c:${c}" data-a="b-cor" data-v="${c}" aria-label="Cor ${c}">${FB.cor === c ? ic('check', 'ic-s') : ''}</button>`).join('')}</div></div>
        <div class="campo"><div class="lbl">Quem tem conta neste banco</div>
          ${FB.contas.map((c, i) => `<div class="conta-ed">
            <div class="conta-l"><input class="inp" data-fbc="pessoa" data-i="${i}" value="${esc(c.pessoa || '')}" placeholder="Nome, ex.: Ana" list="dl-pessoas" autocomplete="off" aria-label="Nome da pessoa">
              ${FB.contas.length > 1 ? `<button class="icbtn" data-a="bc-rm" data-i="${i}" aria-label="Tirar esta pessoa">${ic('trash', 'ic-s')}</button>` : ''}</div>
            <div class="linha-sw"><div><b>Tem cartão de crédito?</b></div><button class="sw${c.cartao ? ' on' : ''}" data-a="bc-cartao" data-i="${i}" aria-label="Tem cartão de crédito"></button></div>
            ${c.cartao ? `<div class="duo" style="margin-top:10px"><div><div class="lbl">Fecha dia</div><div class="pref"><input inputmode="numeric" data-fbc="fechamento" data-i="${i}" value="${c.fechamento || ''}" placeholder="3"></div></div>
              <div><div class="lbl">Vence dia</div><div class="pref"><input inputmode="numeric" data-fbc="vencimento" data-i="${i}" value="${c.vencimento || ''}" placeholder="10"></div></div></div>` : ''}
          </div>`).join('')}
          <button class="chip add" data-a="bc-add">${ic('plus', 'ic-s')}Outra pessoa</button>
          <datalist id="dl-pessoas">${pessoasContas().map(p => `<option value="${esc(p)}">`).join('')}</datalist></div>
        <div class="campo"><label for="b-obs">Observação <span style="color:var(--muted);font-weight:400">(opcional)</span></label>
          <input id="b-obs" class="inp" data-fb="obs" value="${esc(FB.obs || '')}" placeholder="Agência, conta, gerente…" autocomplete="off"></div>
        ${n ? `<p style="color:var(--muted);margin:0">${plural(n, 'investimento usa', 'investimentos usam')} este banco.</p>` : ''}`,
      pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="b-salvar">Salvar</button>`,
    };
  });
}
function salvarBanco() {
  const nome = (FB.nome || '').trim();
  if (!nome) { FB.erro = 'Dê um nome ao banco.'; pintarFolha(); return; }
  if (S.d.bancos.some(b => b.id !== FB.id && b.nome.toLowerCase() === nome.toLowerCase())) { FB.erro = 'Já existe um banco com esse nome.'; pintarFolha(); return; }
  const dia = (v, p) => Math.min(31, Math.max(1, parseInt(v, 10) || p));
  const b = { id: FB.id || 'b-' + uid(), nome, cor: FB.cor, obs: (FB.obs || '').trim(),
    contas: FB.contas.map(c => ({ id: c.id, pessoa: (c.pessoa || '').trim(), cartao: !!c.cartao, fechamento: dia(c.fechamento, 1), vencimento: dia(c.vencimento, 10) })) };
  persistir(d => { const k = d.bancos.findIndex(x => x.id === b.id); if (k >= 0) d.bancos[k] = b; else d.bancos.push(b); }, FB.id ? 'Banco salvo' : 'Banco cadastrado')
    .then(ok => { if (ok) fecharFolha(); });
}

/* ------------------------------------------------------------------ Mais: um menu, como no InventarIA */
// Mais abre um menu: cada função tem a sua linha e a sua tela (Bancos, Caixa, Invest), o Relatório de patrimônio abre
// direto, depois Configurações, com as abas Integrações, Dados, Aparência e Opções, e Sobre por último.
// A tela aberta fica em S.ui.maisTela ('' é o menu); a aba de Configurações, em S.ui.maisAba.
const MAIS_TELAS = { bancos: 'Bancos', caixa: 'Caixa', invest: 'Invest', config: 'Configurações', sobre: 'Sobre' };
const CONFIG_ABAS = [
  ['integracoes', 'Integrações', 'blocks'], ['dados', 'Dados', 'archive'], ['aparencia', 'Aparência', 'palette'], ['opcoes', 'Opções', 'toggle-right'],
];
const maisTela = () => S.ui.tab === 'mais' && Object.keys(MAIS_TELAS).includes(S.ui.maisTela) ? S.ui.maisTela : '';
const maisAba = () => CONFIG_ABAS.some(([k]) => k === S.ui.maisAba) ? S.ui.maisAba : 'integracoes';
const iaOn = () => S.d.ajustes.ia !== false;
// cabeçalho de seção: o ícone num quadradinho no tom da cor do app e o título grande
// the header of a card: an icon tile (like the CronologIA and the ResolvIA), the title and, on the right, a number
const rotIc = (icone, tom = '') => `<span class="rot-ic ${tom}" aria-hidden="true">${ic(icone)}</span>`;
const maisCab = (icone, titulo, aside = '') => `<div class="mais-head"><span class="mais-ic" aria-hidden="true">${ic(icone)}</span><h2>${titulo}</h2>${aside ? `<b class="mais-aside">${aside}</b>` : ''}</div>`;
const maisLead = t => `<p class="painel-lead">${t}</p>`;
const chave = (k, on, rotulo, acao = 'ajuste') => `<button class="sw${on ? ' on' : ''}" data-a="${acao}" data-k="${k}" role="switch" aria-checked="${on}" aria-label="${esc(rotulo)}"></button>`;
const DESLIGADAS_PADRAO = new Set(['dicas_aviso', 'email', 'email_aviso']);
const linhaChave = (k, on, titulo, texto, acao) => `<div class="linha-sw"><div><b>${titulo}</b><span>${texto}</span></div>${chave(k, on, titulo, acao)}</div>`;
const TAG_SW = 'M8 0h20a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H8L0 13V7z', FURO_SW = 'M9.7 10a2.7 2.7 0 1 0-5.4 0a2.7 2.7 0 1 0 5.4 0z';
// a etiqueta marcada: a da cor que vale agora (com a Cor do dia, a do dia)
function corAppAtual() {
  const [r, g, b] = rgbHex(corDoApp().toUpperCase());
  let melhor = null, dist = 1e9;
  for (const [, hex] of CORES_APP) { const [r2, g2, b2] = rgbHex(hex); const dd = Math.abs(r - r2) + Math.abs(g - g2) + Math.abs(b - b2); if (dd < dist) { dist = dd; melhor = hex; } }
  return dist <= 24 ? melhor : null;
}

const maisPe = () => `<p class="foot"><b>GerencIA</b><br>v${VERSAO}${DEMO ? ' · prévia: as alterações ficam só nesta tela' : ''}</p>`;
function telaMais() {
  const tela = maisTela();
  if (!tela) return menuMais();
  const d = S.d;
  let status = ['', `GerencIA ${VERSAO}`], corpo;
  if (tela === 'bancos') {
    const cs = d.bancos.flatMap(b => b.contas || []);
    status = ['', d.bancos.length ? `${plural(d.bancos.length, 'banco', 'bancos')} · ${plural(cs.length, 'conta', 'contas')} · ${plural(cs.filter(c => c.cartao).length, 'cartão', 'cartões')}` : 'Nenhum banco ainda'];
    corpo = `<div class="mais-painel">${maisBancos()}</div>`;
  } else if (tela === 'caixa') {
    const n = fixosAtivos().length;
    status = ['', `${n ? plural(n, 'fixo', 'fixos') : 'Nenhum fixo ainda'} · ${plural(d.categorias.length, 'categoria', 'categorias')}`];
    corpo = `<div class="mais-painel">${maisCaixa()}</div>`;
  } else if (tela === 'invest') {
    status = syncInfo();
    corpo = `<div class="mais-painel">${maisInvest()}</div>`;
  } else if (tela === 'sobre') { // a versão já está em "Este app": sem a linha embaixo do título nem o rodapé
    return `${cabecalho('Sobre', '', false, true)}<div class="mais-painel sb-pagina">${maisSobre()}</div>`;
  } else {
    const aba = maisAba();
    if (aba === 'integracoes') status = !iaOn() ? ['manual', 'IA desligada'] : DEMO ? ['', 'IA simulada na prévia'] : !S.ia ? ['manual', 'Verificando a IA…'] : S.ia.pronta ? ['', 'IA do Home Assistant pronta'] : ['erro', S.ia.motivo || 'IA não está pronta'];
    const painel = { integracoes: maisIntegracoes, dados: maisDados, aparencia: maisAparencia, opcoes: maisOpcoes }[aba]();
    corpo = `<div class="mais-abas" role="tablist" aria-label="Seções de Configurações">${CONFIG_ABAS.map(([k, n, i]) =>
        `<button role="tab" class="${aba === k ? 'on' : ''}" aria-selected="${aba === k}" data-a="mais-aba" data-v="${k}">${ic(i, 'ic-s')}<span>${n}</span></button>`).join('')}</div>
      <div class="mais-painel abas" role="tabpanel" aria-label="${CONFIG_ABAS.find(([k]) => k === aba)[1]}">${painel}</div>`;
  }
  return `${cabecalho(MAIS_TELAS[tela], '', status, true)}${corpo}${maisPe()}`;
}

/* --------- o menu: uma linha por função (o ícone no quadradinho dos títulos das seções), Configurações e Sobre por último */
function menuMais() {
  const linhas = [
    ['bancos', 'bank', 'Bancos', 'Quem tem conta e os cartões.'],
    ['caixa', 'fluxo', 'Caixa', 'Fixos, categorias e dicas de economia.'],
    ['invest', 'trend', 'Invest', cardPerdaBens() ? 'Índices de mercado e perda de valor dos bens.' : 'Índices de mercado: CDI, Selic, IPCA e TR.'],
    ['', 'file', 'Relatório de patrimônio', 'Para imprimir ou salvar em PDF.'],
    ['config', 'sliders', 'Configurações', 'Integrações, dados, aparência e opções.'],
    ['sobre', 'info', 'Sobre', 'CorrerIA Code, os apps e o GitHub.'],
  ];
  return `${cabecalho('Mais', '', false)}
    <nav aria-label="Mais"><ul class="menu-list">${linhas.map(([k, i, t, s]) => `<li><button class="menu-row" ${k ? `data-a="mais-tela" data-v="${k}"` : 'data-a="relatorio"'}>
      <span class="mais-ic" aria-hidden="true">${ic(i)}</span><span class="mb"><b>${t}</b><span>${s}</span></span>${ic('chev', 'chev')}</button></li>`).join('')}</ul></nav>
    ${maisPe()}`;
}

/* --------- Sobre: quem faz os apps (CorrerIA Code), os apps da família, cada um com a sua linha e o link para o
   GitHub, e Meu GitHub. A mesma página nos apps da família (como no about.js do CronologIA): só muda qual é "Este app". */
const GITHUB = 'https://github.com/diegozapella63';
// os apps, na ordem: [nome, repositório, ícone, a linha sobre ele]
const PRODUTOS = [
  ['CronologIA', 'cronologia-ha', 'calendar-days', 'Agenda da família, remédios, rotinas e placar.'],
  ['ResolvIA', 'resolvia-ha', 'list-checks', 'Listas de tarefas com prazos, pontos e repetição.'],
  ['GerencIA', 'gerencia-ha', 'wallet', 'Finanças da casa: caixa, cartões e investimentos.'],
  ['InventarIA', 'inventario-ha', 'package', 'Inventário da casa: cômodos, itens e valores.'],
  ['EconomIA', 'economia-ha', 'receipt', 'Lista de compras com o melhor preço perto de casa.'],
  ['MemorIA', 'memoria-ha', 'book-open', 'Cadernos de anotação que abrem na hora certa.'],
];
// "GerencIA" com o "IA" na cor de destaque, numa peça só (o nome não quebra)
const marcaNome = n => `<span class="sb-wm">${n.slice(0, -2)}<span>${n.slice(-2)}</span></span>`;
const linkFora = (href, corpo, cls) => `<a class="${cls}" href="${href}" target="_blank" rel="noopener">${corpo}</a>`;
function maisSobre() {
  const app = r => r === 'gerencia-ha';
  return `<div class="sobre-topo">
      <span class="sb-raio" aria-hidden="true">${ic('zap')}</span>
      <h2 class="sb-nome">Correr<span>IA</span> Code</h2>
      <p class="sb-oque">desenvolvimento de softwares</p>
      <p class="sb-lema">Feito na correria, rodado pela IA.</p>
    </div>
    <section class="card" id="por-que">${maisCab('hourglass', 'Por que CorrerIA?')}
      <p class="sb-txt">Porque eu sou um programador sem tempo: vivo na correria. Então eu uso a IA para rodar tudo isso aqui. Ela escreve, testa e publica; eu dou as ideias e reclamo dos botões tortos.</p></section>
    <section class="card" id="os-apps">${maisCab('layers', 'Os apps')}
      <ul class="sb-apps" aria-label="Os apps">${PRODUTOS.map(([n, repo, i, linha]) => `<li>${linkFora(`${GITHUB}/${repo}`,
        `<span class="mais-ic" aria-hidden="true">${ic(i)}</span><span class="mb"><b>${marcaNome(n)}${app(repo) ? `<em class="sb-aqui">Este app · v${VERSAO}</em>` : ''}</b><span>${linha}</span></span>${ic('external-link', 'sb-ext')}`,
        `sb-app${app(repo) ? ' aqui' : ''}`)}</li>`).join('')}</ul></section>
    ${linkFora(GITHUB, `${ic('external-link', 'ic-s')}Meu GitHub`, 'btn pri larga sb-github')}`;
}

/* --------- Bancos */
function maisBancos() {
  const d = S.d;
  // a tela já se chama Bancos: o quadro vai sem título, como as telas de uma coisa só do InventarIA
  let h = `<section class="card" id="bancos">${maisLead('Quem tem conta em cada banco e os cartões, com fechamento e vencimento.')}`;
  for (const b of d.bancos) {
    const l = d.investimentos.filter(i => i.banco === b.id);
    const v = l.reduce((s, i) => s + valorHoje(i), 0);
    h += `<button class="banco-row" data-a="banco" data-id="${b.id}"><span class="ini" style="--c:${corOk(b.cor) || '#B8B0B0'}">${esc((b.nome || '?').slice(0, 1).toUpperCase())}</span>
      <div class="op-t"><b>${esc(b.nome)}</b><span>${esc(resumoContas(b))}${l.length ? ` · ${plural(l.length, 'investimento', 'investimentos')} · ${brl(v, 0)}` : ''}</span></div>${ic('chev', 'chev')}</button>`;
  }
  h += `<button class="btn out larga" data-a="banco" style="margin-top:14px">${ic('plus')}Cadastrar banco</button>`;
  const sug = BANCOS_COMUNS.filter(n => !d.bancos.some(b => (b.nome || '').toLowerCase() === n.toLowerCase())).slice(0, 10);
  if (sug.length) h += `<div class="ctrl"><div class="lbl">Toque para cadastrar</div><div class="chips">${sug.map(n => `<button class="chip" data-a="banco-sug" data-v="${esc(n)}">+ ${esc(n)}</button>`).join('')}</div></div>`;
  return h + `</section>`;
}

/* --------- Caixa: fixos, categorias e dicas */
function maisCaixa() {
  const fixos = cardFixos();
  return (fixos || `<section class="card" id="fixos">${maisCab('repeat', 'Fixos')}${maisLead('Ao lançar, escolha Repetir: Todo mês ou Todo ano.')}
    <button class="btn out" data-a="lanc-novo" data-v="despesa">${ic('plus')}Lançar um fixo</button></section>`) + cardCategorias() + cardDicasMais();
}

/* --------- Invest: índices de mercado */
function maisInvest() {
  const I = S.d.indices;
  const quando = I.atualizado_em ? new Date(I.atualizado_em) : null;
  const st = I.erro ? ['erro', `${esc(I.erro)}. Usando os últimos valores.`]
    : I.fonte === 'manual' ? ['manual', `Valores digitados à mão${quando ? ' em ' + fData(quando) : ''}.`]
      : I.fonte === 'bcb' && quando ? ['', `Atualizado pelo Banco Central em ${fData(quando)} às ${quando.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}.`]
        : ['manual', 'Valores de partida (outubro de 2026).'];
  return `<section class="card" id="indices">${maisCab('trend', 'Índices de mercado')}
    ${maisLead('Toque num valor para mudar à mão.')}
    ${[['cdi', 'CDI', 'Taxa DI, ao ano'], ['selic', 'Selic', 'Meta do Copom, ao ano'], ['ipca', 'IPCA', 'Inflação dos últimos 12 meses'], ['tr', 'TR', 'Taxa referencial, ao mês (poupança)']].map(([k, n, s]) =>
      `<button class="idx-row" data-a="indice" data-v="${k}"><div><b>${n}</b><span>${s}</span></div><span class="vl">${pct(+I[k] || 0)}%</span>${ic('chev', 'chev')}</button>`).join('')}
    <div class="status ${st[0]}">${st[1]}</div>
    ${linhaChaveIdx(I)}
    <button class="btn out" data-a="indices-atualizar" style="margin-top:6px">${ic('refresh')}Atualizar agora</button></section>${cardPerdaBens()}`;
}
// perda de valor por ano, por categoria: vale para os bens do InventarIA e para os investimentos do tipo Bens (de terceiros, um carro…)
function cardPerdaBens() {
  const catsInv = i => i.partes && i.partes.length ? i.partes.map(p => p.categoria) : [i.categoria_bem || 'outros'];
  const usadas = new Set([...S.d.investimentos.filter(i => i.tipo === 'bens').flatMap(catsInv),
    ...(bensOn() ? S.bens.categorias.map(c => c.id) : [])]);
  if (!usadas.size) return '';
  const valor = k => S.d.investimentos.filter(i => i.tipo === 'bens').reduce((a, i) => a + (i.partes && i.partes.length
      ? partesHoje(i).filter(p => p.categoria === k).reduce((x, p) => x + p.v, 0) : (i.categoria_bem || 'outros') === k ? valorHoje(i) : 0), 0)
    + (bensOn() ? (S.bens.categorias.find(c => c.id === k)?.hoje || 0) : 0);
  const cats = [...usadas].sort((a, b) => valor(b) - valor(a));
  // cada categoria perde ou valoriza (um imóvel, por exemplo) uma % por ano; gravado com sinal: negativa é valorizar
  const dir = (k, v, t) => { const on = v < 0 ? t < 0 : t >= 0; return `<button type="button" class="${on ? 'on' : ''}" data-a="bens-dir" data-k="${esc(k)}" data-v="${v}" aria-pressed="${on}">${v < 0 ? 'Valoriza' : 'Perde'}</button>`; };
  return `<section class="card" id="perda-bens">${maisCab('sofa', 'Valor dos bens por ano')}
    ${maisLead('Quanto cada categoria perde ou valoriza por ano.')}
    <div class="bens-taxas">${cats.map(k => { const t = taxaBem(k), n = esc(nomeCatBem(k)); return `<div class="bens-tx"><span>${n}<small>${brl(valor(k), 0)}</small></span>
      <span class="bens-ctl"><span class="seg tx-dir" role="group" aria-label="${n}: perde ou valoriza">${dir(k, 1, t)}${dir(k, -1, t)}</span>
      <span class="pref mini"><input data-bens-taxa="${esc(k)}" inputmode="decimal" value="${String(Math.abs(t)).replace('.', ',')}" aria-label="${t < 0 ? 'Valorização' : 'Perda'} por ano de ${n}, em %"><span>%</span></span></span></div>`; }).join('')}</div></section>`;
}
const linhaChaveIdx = I => `<div class="linha-sw" style="margin-bottom:12px"><div><b>Atualizar sozinho</b><span>Busca no Banco Central a cada 12 horas.</span></div>
  <button class="sw${I.auto ? ' on' : ''}" data-a="indices-auto" role="switch" aria-checked="${!!I.auto}" aria-label="Atualizar sozinho"></button></div>`;

/* --------- Integrações: outros apps, IA, uso da IA e sensores */
function maisIntegracoes() {
  const a = S.d.ajustes, sens = a.sensores === true;
  // só os sensores que o servidor cria: o da IA com Usar IA ligado; o dos bens com o InventarIA respondendo
  const lista = ['_meu', '_terceiros', '_rendimento_mensal', '_saldo_caixa', '_entradas_mes', '_saidas_mes',
    ...(iaOn() ? ['_ia_hoje'] : []), ...(a.bens !== false && S.bens && S.bens.ok ? ['_bens'] : [])].map(s => `<code>${s}</code>`);
  return cardOutrosApps(a) + cardBens(a) + cardIA() + (iaOn() ? cardSenhas() + cardEmail() + cardUsoIA() : '') + `
    <section class="card" id="sensores">${maisCab('chart-column', 'Sensores no Home Assistant')}
      ${maisLead('Para painéis e automações.')}
      ${linhaChave('sensores', sens, 'Criar os sensores', sens
        ? `Ligado: <code>sensor.gerencia_patrimonio</code>, ${lista.slice(0, -1).join(', ')} e ${lista[lista.length - 1]}. Atualizam a cada mudança e a cada 15 minutos.`
        : 'Desligado: nenhum sensor no Home Assistant.')}
      ${sens && iaOn() ? `<p class="nota" style="margin:12px 0 0"><code>sensor.gerencia_ia_hoje</code>: chamadas de IA de hoje, com erros, cota e tokens.</p>` : ''}
    </section>`;
}

/* --------- Uso da IA (igual ao do InventarIA): hoje, 7 dias e o mês, gráfico por dia e as últimas chamadas */
const USO_TIPO = { caixa: 'Ler lançamentos', invest: 'Ler investimentos', holerite: 'Ler recibo de pagamento', precos: 'Conferir preço de assinatura', fala: 'Falar', ler: 'Ler com IA', saldos: 'Atualizar saldos', chat: 'Conversa' };
const USO_RES = { ok: '', cota: 'cota excedida', erro: 'erro' };
const DIA_SEM = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'];
const milTokens = n => { n = +n || 0; return n >= 1e6 ? `${(n / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi` : n >= 1000 ? `${Math.round(n / 1000)} mil` : String(Math.round(n)); };
function quandoCurto(isoTxt) {
  const dt = new Date(isoTxt);
  if (isNaN(dt)) return '';
  const hm = dt.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  const k = iso(dt), hj = iso(hoje()), on = iso(new Date(hoje().getTime() - 864e5));
  return k === hj ? `hoje ${hm}` : k === on ? `ontem ${hm}` : `${k.slice(8, 10)}/${k.slice(5, 7)} ${hm}`;
}
function nomeIA(id) {
  if (!id || id === 'padrão do Home Assistant') return 'Padrão do Home Assistant';
  const e = ((S.ia && S.ia.entidades) || []).find(x => x.id === id);
  return e ? e.nome : id === 'ai_task.simulada' ? 'IA simulada (teste)' : id.replace(/^[a-z_]+\./, '').replace(/_/g, ' ');
}
function cardUsoIA() {
  const u = S.uso;
  let corpo;
  if (!u) corpo = `<div class="status manual">Carregando…</div>`;
  else if (!u.today || !(u.days || []).length) corpo = `<div class="status manual">Sem dados de uso ainda.</div>`;
  else {
    const hojeK = u.days[u.days.length - 1].day;
    if (!S.usoSel || !u.days.some(x => x.day === S.usoSel)) S.usoSel = hojeK;
    const diaSem = k => DIA_SEM[new Date(k + 'T12:00:00').getDay()];
    const diaLongo = k => k === hojeK ? 'Hoje' : `${maiuscula(diaSem(k))}, ${k.slice(8, 10)}/${k.slice(5, 7)}`;
    const sub = t => t.quota ? `<span class="s alerta">${t.quota} ${t.quota > 1 ? 'vezes' : 'vez'} sem cota</span>` : t.errors ? `<span class="s alerta">${t.errors} com erro</span>` : `<span class="s">≈ ${milTokens(t.tokens)} tokens</span>`;
    const tile = (k, t) => `<div class="uso-tile"><span class="uk">${k}</span><span class="v">${t.calls || 0}</span>${sub(t)}</div>`;
    const max = Math.max(1, ...u.days.map(x => x.calls || 0));
    const barras = u.days.map(x => {
      const h = x.calls ? Math.max(4, Math.round(x.calls / max * 100)) : 0;
      const lab = `${diaLongo(x.day)}: ${plural(x.calls || 0, 'chamada', 'chamadas')}${x.errors ? `, ${x.errors} com erro` : ''}${x.quota ? `, ${x.quota} sem cota` : ''}`;
      return `<button class="uso-bar" data-a="uso-dia" data-v="${esc(x.day)}" aria-pressed="${x.day === S.usoSel}" aria-label="${esc(lab)}" title="${esc(lab)}"><i style="height:${h}%"></i></button>`;
    }).join('');
    const sel = u.days.find(x => x.day === S.usoSel);
    const tipos = Object.entries(u.week.kinds || {}).sort((a, b) => b[1] - a[1]);
    const recentes = (u.recent || []).map(c => {
      const res = USO_RES[c.result] ?? c.result;
      return `<li><b>${esc(USO_TIPO[c.kind] || c.kind)}</b><span>${esc(nomeIA(c.entity))}</span>${res ? `<span class="r-erro">${esc(res)}</span>` : ''}
        <span class="t">${esc(String(c.seconds).replace('.', ','))} s · ≈ ${milTokens(c.tokens)} tokens${c.images ? ` · ${plural(c.images, 'anexo', 'anexos')}` : ''} · ${esc(quandoCurto(c.at))}</span></li>`;
    }).join('');
    corpo = `<div class="uso-tiles">${tile('Hoje', u.today)}${tile('7 dias', u.week)}${tile('Este mês', u.month)}</div>
      <div class="uso-chart" role="group" aria-label="Chamadas de IA nos últimos 7 dias">${barras}</div>
      <div class="uso-dias" aria-hidden="true">${u.days.map(x => `<span>${x.day === hojeK ? 'hoje' : diaSem(x.day)}</span>`).join('')}</div>
      <p class="uso-cap" aria-live="polite">${diaLongo(sel.day)}: <b>${plural(sel.calls || 0, 'chamada', 'chamadas')}</b>${sel.errors ? `, ${sel.errors} com erro` : ''}${sel.quota ? `, ${sel.quota} sem cota` : ''}.</p>
      ${tipos.length ? `<ul class="uso-tipos" aria-label="Nos últimos 7 dias">${tipos.map(([k, n]) => `<li>${esc(USO_TIPO[k] || k)} <b>${n}</b></li>`).join('')}</ul>` : ''}
      <details class="uso-ult"><summary>${ic('chev', 'ic-s')}Últimas chamadas</summary><ul>${recentes || '<li>Nenhuma chamada ainda.</li>'}</ul></details>
      <p class="nota">Tokens estimados pelo texto. Custo e limites exatos ficam no painel do provedor.</p>`;
  }
  return `<section class="card" id="uso-ia">${maisCab('chart-column', 'Uso da IA')}
    ${maisLead('Chamadas do app à IA do Home Assistant.')}
    ${corpo}</section>`;
}

/* --------- Dados */
function maisDados() {
  // Exportar como no InventarIA, no ResolvIA e no CronologIA: uma linha por arquivo, o que ele tem e o botão
  const exp = (fmt, titulo, texto, rotulo) => `<li><div class="ot"><b>${titulo}</b><span>${texto}</span></div>${DEMO
    ? `<button class="btn peq" data-a="demo-arq">${ic('download', 'ic-s')}${rotulo}</button>`
    : `<a class="btn peq" href="api/export/${fmt}" download>${ic('download', 'ic-s')}${rotulo}</a>`}</li>`;
  const bks = S.backups;
  const listaBk = !DEMO && bks == null ? `<div class="status manual">Carregando backups…</div>`
    : (bks || []).length ? `<div class="bk-lista">${bks.slice(0, 5).map(b => {
      const dt = new Date(b.quando);
      return `<div class="bk-row"><div><b>${fData(dt)} às ${dt.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</b><span>${tamanhoTxt(b.tamanho)} · ${esc(b.nome)}</span></div>
        <button class="btn peq" data-a="bk-restaurar" data-v="${esc(b.nome)}">${ic('archive-restore', 'ic-s')}Restaurar</button></div>`;
    }).join('')}</div>` : `<p class="nota" style="margin:12px 0 0">Nenhum backup na pasta ainda.</p>`;
  return `<section class="card" id="exportar">${maisCab('download', 'Exportar')}
            <ul class="opts">
        ${exp('lancamentos', 'Lançamentos (CSV)', 'Um lançamento por linha, para Excel ou Google Planilhas.', 'Baixar CSV')}
        ${exp('csv', 'Investimentos (CSV)', 'Um investimento por linha.', 'Baixar CSV')}
        ${exp('json', 'Dados completos (JSON)', 'Todos os campos.', 'Baixar JSON')}
        ${exp('zip', 'Tudo (ZIP)', 'Dados, planilhas e imagens. É o que o Importar traz de volta.', 'Baixar ZIP')}
      </ul></section>
    <section class="card" id="backup">${maisCab('archive', 'Backup na pasta share')}
      ${maisLead('Cópia completa em <code>share/gerencia</code>. O backup do Home Assistant também inclui o app.')}
      <button class="btn pri" data-a="backup">${ic('archive')}Criar backup</button>${listaBk}</section>
    <section class="card" id="importar">${maisCab('upload', 'Importar')}
      ${maisLead('Um .zip ou .json exportado pelo GerencIA. Antes, o app guarda uma cópia do que existe.')}
      <button class="btn" data-a="importar">${ic('upload')}Escolher arquivo</button></section>
    <section class="card" id="versoes">${maisCab('clock', 'Versões anteriores')}
      ${maisLead('Uma cópia a cada 10 minutos de uso e antes de importar ou restaurar. Ficam as 3 mais recentes.')}
      <button class="btn" data-a="versoes">${ic('clock')}Ver versões</button></section>
    <section class="card" id="onde">${maisCab('database', 'Onde ficam os dados')}
      ${maisLead('<code>/data/gerencia.json</code> e as imagens em <code>/data/fotos</code>, no backup do Home Assistant. Sem internet, só os índices, a IA e as dicas param.')}</section>
    <section class="card" id="zerar">${maisCab('trash', 'Começar do zero')}
      ${maisLead('Apaga lançamentos, fixos, investimentos e bancos. Índices, categorias e preferências continuam. Uma cópia fica em Versões anteriores.')}
      <button class="btn perigo" data-a="apagar-tudo">${ic('trash')}Apagar tudo</button></section>`;
}
const tamanhoTxt = n => n >= 1048576 ? `${(n / 1048576).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} MB` : `${Math.max(1, Math.round(n / 1024))} KB`;

/* --------- Aparência */
function maisAparencia() {
  const a = S.d.ajustes, cor = corAppAtual();
  return `<section class="card" id="tema">${maisCab('contrast', 'Tema')}
      ${maisLead('Automático segue o Home Assistant.')}
      <div class="seg temas" role="radiogroup" aria-label="Tema">${[['auto', 'Automático', 'smartphone'], ['claro', 'Claro', 'sun'], ['escuro', 'Escuro', 'moon']].map(([k, n, i]) =>
        `<button role="radio" aria-checked="${a.tema === k}" class="${a.tema === k ? 'on' : ''}" data-a="tema" data-v="${k}">${ic(i)}<span>${n}</span></button>`).join('')}</div></section>
    <section class="card" id="cor">${maisCab('palette', 'Cor do app')}
      ${linhaChave('cor_dia', corDiaOn(), 'Cor do dia', 'Muda a cor do app todo dia.')}
      <div class="tag-cores" role="radiogroup" aria-label="Cor do app">${CORES_APP.map(([n, hex]) =>
        `<button class="tsw${cor === hex ? ' on' : ''}" role="radio" aria-checked="${cor === hex}" style="--a:${hex}" data-a="cor" data-v="${hex}">
          <svg viewBox="-5 -5 40 30" aria-hidden="true"><path class="sw-ring" d="${TAG_SW}"/><path class="sw-gap" d="${TAG_SW}"/><path class="sw-fill" d="${TAG_SW}${FURO_SW}"/><path class="sw-check" d="m14.6 10.3 3.2 3.2 6.5-6.9"/></svg>
          <span>${n}</span></button>`).join('')}</div></section>`;
}

/* --------- Opções: o jeito de o app funcionar, para a casa toda */
function maisOpcoes() {
  const a = S.d.ajustes;
  return `<section class="card" id="op-inicio">${maisCab('home', 'Início')}
      ${linhaChave('dicas', a.dicas !== false, 'Dicas de economia', a.dicas === false
        ? 'Desligado: sem dicas.'
        : iaOn() ? 'Ligado: no Início, planos anuais mais baratos e categorias acima da média.'
          : 'Ligado: no Início, categorias acima da média. Planos anuais precisam da IA.')}</section>
    ${opcoesDicas()}
    ${opcoesEmail()}
    <section class="card" id="op-caixa">${maisCab('fluxo', 'Fluxo de caixa')}
      ${linhaChave('prever_dia', a.prever_dia !== false, 'Prever o dia a dia', a.prever_dia !== false
        ? `Ligado: os próximos meses somam a média do dia a dia, ${brl(mediaVariaveis(), 0)} por mês.`
        : 'Desligado: só fixos, parcelas e faturas.')}</section>
    <section class="card" id="op-invest">${maisCab('wallet', 'Investimentos')}
      ${linhaChave('corrigir', a.corrigir !== false, 'Corrigir valores pelo rendimento', 'Estima o valor de hoje desde o último informado. Renda variável não muda.')}</section>`;
}

/* Dicas de economia: conferir sozinho (todo dia, no horário) e avisar no celular, como o aviso de prazos do ResolvIA:
   o aviso vai para as pessoas escolhidas, nos celulares ligados a elas no Home Assistant (Configurações › Pessoas).
   Os planos anuais são conferidos pela IA: sem ela (ou com as dicas desligadas), a seção some. */
function opcoesDicas() {
  const a = S.d.ajustes;
  if (a.dicas === false || !iaOn()) return '';
  const auto = a.dicas_auto !== false, aviso = a.dicas_aviso === true, freq = DICAS_FREQ[a.dicas_freq] ? a.dicas_freq : 'mes';
  let h = `<section class="card" id="op-dicas">${maisCab('percent', 'Dicas de economia')}
    ${linhaChave('dicas_auto', auto, 'Conferir sozinho', auto ? 'Ligado: uma assinatura nova é conferida logo.' : 'Desligado: só no Conferir agora.')}`;
  // de quanto em quanto tempo, como as escolhas do ResolvIA (a assinatura nova é conferida logo)
  if (auto) h += `<div class="seg mini op-freq" role="radiogroup" aria-label="De quanto em quanto tempo">${Object.entries(DICAS_FREQ).map(([k, [n]]) =>
    `<button class="${k === freq ? 'on' : ''}" role="radio" aria-checked="${k === freq}" data-a="dicas-freq" data-v="${k}">${n}</button>`).join('')}</div>`;
  h += linhaChave('dicas_aviso', aviso, 'Avisar no celular', aviso ? 'Ligado: quando aparece uma dica nova.' : 'Desligado.');
  if (aviso) h += quemRecebe();
  return h + '</section>';
}
// Faturas por e-mail: o aviso no celular quando uma fatura fica pronta para conferir (como o das dicas)
function opcoesEmail() {
  if (!emailOn()) return '';
  const aviso = S.d.ajustes.email_aviso === true;
  return `<section class="card" id="op-email">${maisCab('mail', 'Faturas por e-mail')}
    ${linhaChave('email_aviso', aviso, 'Avisar no celular', aviso ? 'Ligado: quando uma fatura do e-mail fica pronta para conferir.' : 'Desligado.')}
    ${aviso ? quemRecebe('email_para', false) : ''}</section>`;
}
const DICAS_FREQ = { semana: ['Toda semana'], quinzena: ['A cada 15 dias'], mes: ['Todo mês'] };
function quemRecebe(chave = 'dicas_para', testar = true) {
  const P = S.avisoPessoas;
  if (P === undefined) carregarPessoasAviso();
  const para = new Set(S.d.ajustes[chave] || []);
  const eu = P && P.pessoas ? P.pessoas.find(p => p.eu) : null;
  const porque = !P || !P.pessoas ? (P && P.erro) || '' : !eu ? 'Você não é uma pessoa da casa no Home Assistant.' : !eu.celular ? 'Sem celular ligado a você no Home Assistant.' : '';
  let h = `<div class="campo"><label>Quem recebe</label>`;
  if (P === undefined) h += `<p class="nota">Procurando as pessoas da casa…</p>`;
  else if (!P || !P.pessoas) h += `<p class="nota">${esc((P && P.erro) || 'Não consegui ver as pessoas da casa.')}</p>`;
  else if (!P.pessoas.length) h += `<p class="nota">Nenhuma pessoa da casa no Home Assistant.</p>`;
  else {
    h += `<div class="quem">${P.pessoas.map(p => `<button class="quem-p${para.has(p.id) ? ' on' : ''}${p.celular ? '' : ' sem'}" data-a="aviso-pessoa" data-k="${chave}" data-v="${esc(p.id)}" aria-pressed="${para.has(p.id)}">${ic('user', 'ic-s')}<b>${esc(p.nome)}</b>${p.celular ? '' : '<span>sem celular</span>'}</button>`).join('')}</div>`;
    const sem = P.pessoas.filter(p => para.has(p.id) && !p.celular).map(p => p.nome);
    if (sem.length) h += `<p class="nota">Sem celular para ${esc(juntarE(sem))}: ligue o celular à pessoa no Home Assistant.</p>`;
    else if (!para.size) h += `<p class="nota">Escolha quem recebe.</p>`;
  }
  return h + '</div>' + (testar ? `<button class="btn out op-testar" data-a="aviso-testar"${eu && eu.celular ? '' : ' disabled'}${porque ? ` title="${esc(porque)}"` : ''}>${ic('send')}Testar no meu celular</button>` : '');
}
function carregarPessoasAviso() {
  if (S.avisoPedido) return S.avisoPedido;
  S.avisoPedido = api.avisoPessoas().then(r => r, () => ({ pessoas: null }))
    .then(r => { S.avisoPessoas = r; S.avisoPedido = null; if (S.ui.maisTela === 'config') render(); return r; });
  return S.avisoPedido;
}

/* ------------------------------------------------------------------ folhas (bottom sheets) */
// Cada folha (e a câmera) ocupa um nível no histórico: o Voltar do celular fecha só o de cima.
// Uma folha aberta "por cima" (Fatura, print ou foto a partir da Nova despesa) volta para a de baixo ao fechar.
let FOLHA = null, PILHA = [];
const nivelHist = () => { try { return (history.state && history.state.g) || 0; } catch (e) { return 0; } };
const nivel = () => (CAM ? CAM.h : FOLHA ? FOLHA.h : 0);
// O Voltar que o app pede (history.go) chega depois, num popstate. Uma folha aberta antes disso (salvou uma e já abriu
// outra) marcaria o histórico na entrada velha e o popstate a fecharia: ela espera o Voltar chegar para marcar a dela.
let VOLTA = null, MARCAR = null, VOLTA_T = 0;
const nivelAgora = () => (VOLTA !== null ? VOLTA : nivelHist());
function voltarHist(h) {
  if (MARCAR !== null && h < MARCAR) MARCAR = null;  // a folha que esperava já fechou: nada a marcar
  const g = nivelAgora();
  if (g <= h) return;
  try { history.go(h - g); } catch (e) { return; }
  VOLTA = h;
  clearTimeout(VOLTA_T);
  VOLTA_T = setTimeout(chegouVolta, 1000);  // se o popstate não vier
}
function chegouVolta() {
  clearTimeout(VOLTA_T);
  VOLTA = null;
  const m = MARCAR;
  MARCAR = null;
  if (m !== null && nivel() >= m) marcarHist(m);
  return m !== null;
}
function marcarHist(h) {
  if (VOLTA !== null) { MARCAR = h; return; }
  // a entrada de agora já é desse nível (a câmera acabou de fechar e a folha entra no lugar dela): só troca
  try { if (nivelHist() >= h) history.replaceState({ folha: 1, g: h }, ''); else history.pushState({ folha: 1, g: h }, ''); } catch (e) { /* ok */ }
}
function abrirFolha(montar, aoFechar, sobre) {
  const root = $('#folhas');
  if (sobre && FOLHA) {
    const c = $('.folha-corpo', root);
    FOLHA.scroll = c ? c.scrollTop : 0;
    PILHA.push(FOLHA);
    FOLHA = { montar, aoFechar, h: FOLHA.h + 1 };
    pintarFolha(0);
    marcarHist(FOLHA.h);
    return;
  }
  fecharFolha(true);
  root.innerHTML = `<div class="veu" data-a="fechar"></div><section class="folha" role="dialog" aria-modal="true"></section>`;
  FOLHA = { montar, aoFechar, h: Math.max(1, nivelAgora()) };
  pintarFolha();
  requestAnimationFrame(() => { $('.veu', root).classList.add('on'); $('.folha', root).classList.add('on'); });
  marcarHist(FOLHA.h);
}
function pintarFolha(scrollPara) {
  if (!FOLHA) return;
  const el = $('#folhas .folha');
  const corpoAnt = $('.folha-corpo', el);
  const scroll = typeof scrollPara === 'number' ? scrollPara : corpoAnt ? corpoAnt.scrollTop : 0;
  const f = FOLHA.montar();
  el.innerHTML = `<div class="folha-cab"><h2>${f.titulo}</h2>${f.cab || ''}<button class="icbtn" data-a="fechar" aria-label="Fechar">${ic('x')}</button></div>
    <div class="folha-corpo">${f.corpo}</div>${f.pe ? `<div class="folha-pe">${f.pe}</div>` : ''}`;
  $('.folha-corpo', el).scrollTop = scroll;
  if (f.depois) f.depois(el);
}
// umNivel: o X, o Cancelar, o fundo escuro e o Voltar fecham só a folha de cima; o resto (salvou, trocou de tela) fecha todas
function fecharFolha(semHistorico, umNivel) {
  if (!FOLHA) return;
  if (umNivel && PILHA.length) {
    const cb = FOLHA.aoFechar;
    FOLHA = PILHA.pop();
    pintarFolha(FOLHA.scroll || 0);
    if (!semHistorico) voltarHist(FOLHA.h);
    if (cb) cb();
    return;
  }
  const root = $('#folhas');
  const veu = $('.veu', root), fo = $('.folha', root);
  const cbs = [FOLHA, ...PILHA.slice().reverse()].map(f => f.aoFechar).filter(Boolean);
  FOLHA = null; PILHA = [];
  if (veu) veu.classList.remove('on');
  if (fo) fo.classList.remove('on');
  setTimeout(() => { if (!FOLHA) root.innerHTML = ''; }, 240);
  if (!semHistorico) voltarHist(nivel());
  cbs.forEach(cb => cb());
}
window.addEventListener('popstate', () => {
  // o Voltar que o app pediu chegou; uma folha aberta enquanto isso marca a entrada dela agora
  if (VOLTA !== null && chegouVolta()) return;
  const alvo = nivelHist();
  if (CAM && CAM.h > alvo) fecharCamera(true);
  while (FOLHA && FOLHA.h > alvo) fecharFolha(true, true);
  if (nivel() < alvo) voltarHist(nivel()); // entradas que sobraram de folhas já fechadas
  // as telas de Mais (marcarTela): saiu da entrada da tela aberta, volta para onde se estava;
  // caiu na entrada de uma tela que já não está aberta (sobrou), volta mais uma
  if (alvo || FOLHA || CAM || !S.d) return;
  const t = histTela(), agora = maisTela();
  if (t && t !== agora) { try { history.back(); } catch (e) { /* ok */ } }
  else if (!t && agora) {
    const de = TELA_DE;
    TELA_DE = null;
    TELA_VISTA = '';
    S.ui.maisTela = '';
    if (de) S.ui.tab = de;
    salvarUI();
    render();
    window.scrollTo(0, 0);
  }
});

// como escolher: de dentro de outra janela, fica por cima dela e o Cancelar volta para ela
function confirmar({ titulo, texto, botao, perigo, acao }) {
  abrirFolha(() => ({
    titulo,
    corpo: `<p style="margin:0;font-size:17px;color:var(--text-2)">${texto}</p>`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn ${perigo ? 'perigo' : 'pri'}" data-a="confirmar">${botao}</button>`,
  }), null, !!FOLHA);
  FOLHA.confirmar = acao;
}

/* --------- investimento */
let F = null;
function novoForm(base) {
  const t = tipoDe(base?.tipo || 'cdb');
  return Object.assign({
    id: null, nome: '', banco: S.d.bancos[0]?.id || '', tipo: t.id, valor: 0, data_valor: iso(hoje()),
    indexador: t.p.indexador, taxa: t.p.taxa, liquidez: t.p.liquidez, vencimento: '', titular: 'meu', terceiro: '', obs: '',
    obsAberta: false, idxEditado: false, dataEditada: false, bancosNovos: [], novoBanco: null, erros: {}, original: null, fotos: [], categoria_bem: 'outros',
  }, base || {});
}

function abrirInvestimento(id, preset) {
  const inv = id && S.d.investimentos.find(i => i.id === id);
  if (inv) {
    F = novoForm(Object.assign(clone(inv), { original: inv, obsAberta: !!inv.obs, idxEditado: true, dataEditada: true, bancosNovos: [], erros: {}, vencimento: inv.vencimento || '' }));
    if (inv.partes && inv.partes.length) Object.assign(F, { dividir: true, partes: Object.fromEntries(inv.partes.map(p => [p.categoria, +p.valor || 0])) });
  } else {
    F = novoForm(preset);
  }
  abrirFolha(montarFormInv);
}

// Aplicar num investimento já cadastrado: soma ao valor de hoje e, se quiser, lança no caixa como aporte
// (dando baixa no aporte do mês, quando houver um a aplicar, ou como um aporte à parte).
let AP = null;
function aportesPendentes() {
  const h = iso(hoje());
  // o aporte deste mês (ou o do mês passado, se ficou para trás) ainda a aplicar; o do mês que vem não
  return lancamentosEntre(addYm(ymHoje(), -1), ymHoje()).filter(l => ehAporte(l) && !l.pago && (l.competencia || ymDe(l.data)) <= ymHoje())
    .sort((a, b) => Math.abs(diasEntre(pData(a.data), pData(h))) - Math.abs(diasEntre(pData(b.data), pData(h))));
}
function abrirAplicar(invId) {
  const inv = S.d.investimentos.find(i => i.id === invId);
  if (!inv) return;
  const pend = inv.titular === 'terceiros' ? [] : aportesPendentes();
  const conta = (contas().find(c => c.id === ultimaConta('despesa').conta && !c.cartao) || contas().find(c => !c.cartao) || contas()[0])?.id || '';
  AP = { inv: invId, modo: 'aplicou', valor: 0, total: 0, data: iso(hoje()), destino: pend[0] ? pend[0].id : inv.titular === 'terceiros' ? 'nenhum' : 'novo', conta, erro: '' };
  abrirFolha(montarAplicar, null, !!FOLHA); // aberto do investimento: Cancelar, X e Voltar voltam para ele
  requestAnimationFrame(() => { const v = $('#ap-v'); if (v) v.focus(); });
}
function montarAplicar() {
  const a = AP, inv = S.d.investimentos.find(i => i.id === a.inv);
  if (!inv) return { titulo: 'Aplicar', corpo: '' };
  const pend = inv.titular === 'terceiros' ? [] : aportesPendentes();
  const atual = valorHoje(inv);
  const chip = (v, txt) => `<button class="chip${a.destino === v ? ' on' : ''}" data-a="ap-destino" data-v="${esc(v)}">${txt}</button>`;
  const pl = pend.find(l => l.id === a.destino);
  return {
    titulo: `Aplicar em ${esc(inv.nome)}`,
    // às vezes só se sabe o total novo (o app do banco mostra o saldo): o aporte é a diferença para o valor de hoje
    corpo: `<div class="seg ap-modo" style="margin-bottom:14px"><button class="${a.modo !== 'total' ? 'on' : ''}" data-a="ap-modo" data-v="aplicou">Quanto apliquei</button>
        <button class="${a.modo === 'total' ? 'on' : ''}" data-a="ap-modo" data-v="total">Quanto tem agora</button></div>
      <div class="campo"><label for="ap-v">${a.modo === 'total' ? 'Quanto tem agora, no total' : 'Quanto você aplicou'}</label><div class="pref grande${a.erro ? ' erro' : ''}"><span>R$</span><input id="ap-v" data-ap="${a.modo === 'total' ? 'total' : 'valor'}" inputmode="numeric" value="${a.modo === 'total' ? (a.total ? NF2.format(a.total) : '') : (a.valor ? NF2.format(a.valor) : '')}" placeholder="0,00"></div>
        ${a.erro ? `<div class="msg-erro">${esc(a.erro)}</div>` : ''}
        <div class="ajuda" id="ap-ajuda">${aplicarAjuda(atual)}</div></div>
      <div class="campo"><label for="ap-data">Data</label><input id="ap-data" class="inp" type="date" data-ap="data" value="${esc(a.data)}" max="${iso(hoje())}"></div>
      <div class="campo"><div class="lbl">No caixa</div><div class="chips" style="margin:0">
        ${pend.map(l => chip(l.id, `Baixa no ${esc(l.descricao.toLowerCase().startsWith('aporte') ? 'aporte' : l.descricao)} de ${MESES_LONGOS[+String(l.competencia || l.data).slice(5, 7) - 1]} (${brl(+l.valor || 0, 0)})`)).join('')}
        ${chip('novo', pend.length ? 'Lançar à parte' : 'Lançar como aporte')}${chip('nenhum', 'Não lançar')}</div>
        ${pl ? `<div class="ajuda">Sai de ${esc(nomeConta(contaDe(pl.conta)) || 'sem conta')}.</div>` : inv.titular === 'terceiros' && a.destino === 'nenhum' ? '<div class="ajuda">Dinheiro de terceiros não mexe no caixa.</div>' : ''}
        ${a.destino === 'novo' ? `<div class="chips" style="margin:10px 0 0">${contas().map(k => `<button class="chip${a.conta === k.id ? ' on' : ''}" data-a="ap-conta" data-v="${k.id}" style="--c:${corOk(k.cor) || '#B8B0B0'}"><span class="bol"></span>${esc(nomeConta(k))}</button>`).join('')}</div>` : ''}</div>`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="ap-ok">Aplicar${a.valor ? ' ' + brl(a.valor, 0) : ''}</button>`,
  };
}
const l2mes = l => `de ${MESES_LONGOS[+String(l.competencia || l.data).slice(5, 7) - 1]}`;
function aplicarAjuda(atual) {
  if (AP.modo === 'total') {
    if (!(AP.total > 0)) return `Hoje: ${brl(atual)}. O aporte é a diferença.`;
    return AP.total > atual + 0.005 ? `Aporte de <b>${brl(AP.total - atual)}</b>: de ${brl(atual)} para ${brl(AP.total)}.`
      : `É menos que os ${brl(atual)} de hoje. Para corrigir o valor, edite o investimento.`;
  }
  return AP.valor > 0 ? `${brl(atual)} → <b>${brl(atual + AP.valor)}</b>.` : `Hoje: ${brl(atual)}.`;
}
function confirmarAplicar() {
  const a = AP, inv0 = S.d.investimentos.find(i => i.id === a.inv);
  if (!inv0) return;
  if (a.modo === 'total' && a.total > 0 && !(a.valor > 0)) { a.erro = `O total precisa ser maior que os ${brl(valorHoje(inv0))} de hoje.`; pintarFolha(); return; }
  if (!(a.valor > 0)) { a.erro = a.modo === 'total' ? 'Coloque o total.' : 'Coloque o valor.'; pintarFolha(); return; }
  const novoValor = a.modo === 'total' ? round2(a.total) : round2(valorHoje(inv0) + a.valor);
  const pl = aportesPendentes().find(l => l.id === a.destino);
  const hj = iso(hoje());
  persistir(d => {
    const inv = d.investimentos.find(i => i.id === a.inv);
    if (!inv) return;
    definirValor(inv, novoValor, hj);
    if (pl) {
      if (pl.virtual) d.lancamentos.push(materializar(pl, { valor: round2(a.valor), pago: true, investimento: inv.id }));
      else { const x = d.lancamentos.find(y => y.id === pl.id); if (x) Object.assign(x, { valor: round2(a.valor), pago: true, investimento: inv.id }); }
      const r = pl.recorrencia && d.recorrencias.find(x => x.id === pl.recorrencia);
      if (r && !r.investimento) r.investimento = inv.id;
    } else if (a.destino === 'novo') {
      if (!d.categorias.some(c => c.id === 'c-investimentos')) d.categorias.push(clone(CATEGORIAS_PADRAO.find(c => c.id === 'c-investimentos')));
      d.lancamentos.push({ id: uid(), tipo: 'despesa', aporte: true, descricao: `Aporte: ${inv.nome}`, valor: round2(a.valor), categoria: 'c-investimentos',
        conta: a.conta || '', cartao: false, data: a.data || hj, pago: (a.data || hj) <= hj, obs: '', investimento: inv.id });
    }
  }, `Aplicado ${brl(a.valor, 0)} em ${inv0.nome}`).then(ok => { if (ok) { AP = null; fecharFolha(); } });
}

// O novo valor de hoje de um investimento. Num bem separado por categoria, o valor de hoje é a soma das partes: elas
// mudam na mesma proporção (senão Aplicar e Transferir não mudariam nada nele, ou o dinheiro sumiria).
function definirValor(inv, novo, data) {
  novo = round2(novo);
  const ps = inv.tipo === 'bens' && Array.isArray(inv.partes) && inv.partes.length ? partesHoje(inv) : null;
  if (ps) {
    const tot = ps.reduce((a, p) => a + p.v, 0);
    let resto = novo;
    inv.partes = inv.partes.map((p, k) => {
      const v = k === ps.length - 1 ? resto : tot > 0 ? round2(ps[k].v * novo / tot) : 0;
      resto = round2(resto - v);
      return Object.assign({}, p, { valor: v });
    });
  }
  Object.assign(inv, { valor: novo, data_valor: data || iso(hoje()), atualizado_em: new Date().toISOString() });
}
// Transferir de um investimento para outro: sai do valor de hoje de um e soma no do outro. O caixa não muda.
let TR = null;
function abrirTransferir(invId) {
  const inv = S.d.investimentos.find(i => i.id === invId);
  if (!inv) return;
  TR = { de: invId, para: '', valor: 0, apagar: false, erro: '' };
  abrirFolha(montarTransferir, () => { TR = null; }, !!FOLHA);
  requestAnimationFrame(() => { const v = $('#tr-v'); if (v) v.focus(); });
}
function transferirAjuda() {
  const de = S.d.investimentos.find(i => i.id === TR.de), para = S.d.investimentos.find(i => i.id === TR.para);
  if (!de) return '';
  const a = valorHoje(de);
  if (!(TR.valor > 0)) return `Hoje: ${brl(a)}.`;
  return `${esc(de.nome)} fica com <b>${brl(Math.max(0, a - TR.valor))}</b>${para ? ` e ${esc(para.nome)} passa de ${brl(valorHoje(para))} para <b>${brl(valorHoje(para) + TR.valor)}</b>` : ''}.`;
}
function montarTransferir() {
  const t = TR, de = S.d.investimentos.find(i => i.id === t.de);
  if (!de) return { titulo: 'Transferir', corpo: '' };
  const atual = round2(valorHoje(de)), tudo = t.valor > 0 && Math.abs(t.valor - atual) < 0.005;
  // os do mesmo dono primeiro
  const outros = S.d.investimentos.filter(i => i.id !== de.id)
    .sort((a, b) => ((a.titular === 'terceiros') !== (de.titular === 'terceiros')) - ((b.titular === 'terceiros') !== (de.titular === 'terceiros')) || a.nome.localeCompare(b.nome, 'pt-BR'));
  const para = outros.find(i => i.id === t.para);
  const dono = i => i.titular === 'terceiros' ? (i.terceiro || 'terceiros') : '';
  return {
    titulo: `Transferir de ${esc(de.nome)}`,
    corpo: `<div class="campo"><label for="tr-v">Quanto</label><div class="pref grande${t.erro === 'valor' ? ' erro' : ''}"><span>R$</span><input id="tr-v" data-tr="valor" inputmode="numeric" value="${t.valor ? NF2.format(t.valor) : ''}" placeholder="0,00"></div>
        ${t.erro === 'valor' ? `<div class="msg-erro">${t.valor > atual ? `Passa do valor de hoje (${brl(atual)}).` : 'Coloque o valor.'}</div>` : ''}
        <div class="chips c3" style="margin:10px 0 0"><button class="chip${tudo ? ' on' : ''}" data-a="tr-tudo">Tudo (${brl(atual, 0)})</button></div>
        <div class="ajuda" id="tr-ajuda">${transferirAjuda()}</div></div>
      <div class="campo"><div class="lbl">Para qual investimento</div>
        <div class="chips tr-para${t.erro === 'para' ? ' erro' : ''}" style="margin:0">${outros.map(i => { const b = bancoDe(i.banco);
          return `<button class="chip${t.para === i.id ? ' on' : ''}" data-a="tr-para" data-v="${esc(i.id)}" style="--c:${corOk(b?.cor) || '#B8B0B0'}"><span class="bol"></span><span>${esc(i.nome)}${dono(i) ? ` <small>· ${esc(dono(i))}</small>` : ''}</span></button>`; }).join('')}</div>
        ${t.erro === 'para' ? '<div class="msg-erro">Escolha para onde vai o dinheiro.</div>' : ''}
        ${para && (para.titular === 'terceiros') !== (de.titular === 'terceiros') ? `<div class="ajuda">${de.titular === 'terceiros' ? 'Sai de um dinheiro de terceiros e entra num seu.' : 'Sai de um dinheiro seu e entra num de terceiros.'} </div>` : ''}</div>
      ${tudo ? `<div class="campo"><div class="lbl">${esc(de.nome)} fica zerado</div><div class="chips c2" style="margin:0">
        <button class="chip${!t.apagar ? ' on' : ''}" data-a="tr-apagar" data-v="">Manter na carteira</button>
        <button class="chip${t.apagar ? ' on' : ''}" data-a="tr-apagar" data-v="1">Tirar da carteira</button></div>
        ${t.apagar ? '<div class="ajuda">Uma cópia fica em Mais › Configurações › Dados › Versões anteriores.</div>' : ''}</div>` : ''}
      <p class="nota" style="margin:4px 0 0">Não mexe no caixa.</p>`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="tr-ok">Transferir${t.valor ? ' ' + brl(t.valor, 0) : ''}</button>`,
  };
}
function confirmarTransferir() {
  const t = TR, de0 = S.d.investimentos.find(i => i.id === t.de), para0 = S.d.investimentos.find(i => i.id === t.para);
  if (!de0) return;
  const atual = round2(valorHoje(de0));
  if (!(t.valor > 0) || t.valor > atual + 0.005) { t.erro = 'valor'; pintarFolha(); return; }
  if (!para0) { t.erro = 'para'; pintarFolha(); return; }
  const tudo = Math.abs(t.valor - atual) < 0.005, apagar = tudo && t.apagar;
  const vDe = tudo ? 0 : round2(atual - t.valor), vPara = round2(valorHoje(para0) + t.valor);
  const hj = iso(hoje()), agora = new Date().toISOString();
  persistir(d => {
    const de = d.investimentos.find(i => i.id === t.de), para = d.investimentos.find(i => i.id === t.para);
    if (!de || !para) return;
    definirValor(para, vPara, hj);
    if (apagar) d.investimentos = d.investimentos.filter(i => i.id !== de.id);
    else definirValor(de, vDe, hj);
  }, `Transferido ${brl(t.valor, 0)} de ${de0.nome} para ${para0.nome}`).then(ok => { if (ok) { TR = null; F = null; fecharFolha(); } });
}

// Bens: uma categoria para o total, ou (se quiser) o valor separado pelas categorias do InventarIA, cada uma com a sua perda por ano
const varAno = v => v > 0.5 ? `perdem ≈ ${brl(v, 0)}/ano` : v < -0.5 ? `valorizam ≈ ${brl(-v, 0)}/ano` : 'mantêm o valor';
const rotPerda = t => t > 0 ? `Perde ${pct(t)}% por ano` : t < 0 ? `Valoriza ${pct(-t)}% por ano` : 'Mantém o valor';
function camposBens(f) {
  if (f.dividir) {
    const soma = Object.values(f.partes || {}).reduce((a, v) => a + (+v || 0), 0);
    return `<div class="campo"><div class="lbl">Valor por categoria</div><div class="bens-partes">${catsBens().map(([k, n]) =>
      `<label class="bens-tx"><span>${esc(n)}<small>${rotPerda(taxaBem(k))}</small></span><span class="pref mini larga"><span>R$</span><input data-fparte="${k}" inputmode="numeric" value="${f.partes && f.partes[k] ? NF2.format(f.partes[k]) : ''}" placeholder="0,00" aria-label="Valor em ${esc(n)}"></span></label>`).join('')}</div>
      <div class="ajuda" id="partes-soma">Total: <b>${brl(soma)}</b>. As taxas ficam em Mais › Invest.</div>
      <button type="button" class="link" data-a="f-dividir" data-v="">Usar uma categoria só</button></div>`;
  }
  const cs = catsBens(), extra = f.categoria_bem && !cs.some(c => c[0] === f.categoria_bem) ? [[f.categoria_bem, nomeCatBem(f.categoria_bem)]] : [];
  return `<div class="campo"><div class="lbl">Categoria</div><div class="chips" style="margin:0">${[...cs, ...extra].map(([k, n]) =>
      `<button class="chip${(f.categoria_bem || 'outros') === k ? ' on' : ''}" data-a="f-set" data-k="categoria_bem" data-v="${k}">${n}</button>`).join('')}</div>
      <div class="ajuda">${rotPerda(taxaBem(f.categoria_bem || 'outros'))}. As taxas ficam em Mais › Invest.</div>
      <button type="button" class="link" data-a="f-dividir" data-v="1">Separar o valor por categoria</button></div>`;
}

function montarFormInv() {
  const f = F;
  const ix = idxDe(f.indexador);
  const bancos = [...S.d.bancos, ...f.bancosNovos];
  const ps = pessoas();
  const err = k => f.erros[k] ? ' erro' : '';
  const msg = k => f.erros[k] ? `<div class="msg-erro">${f.erros[k]}</div>` : '';
  const titulo = f.id ? 'Editar investimento' : f.duplicando ? 'Duplicar investimento' : 'Novo investimento';
  const aplicar = f.id ? `<div class="inv-aplicar"><div class="inv-acoes"><button class="btn out" data-a="inv-aplicar" data-v="${esc(f.id)}">${ic('plus', 'ic-s')}Aplicar mais</button>
    ${S.d.investimentos.length > 1 ? `<button class="btn out" data-a="inv-transferir" data-v="${esc(f.id)}">${ic('swap', 'ic-s')}Transferir</button>` : ''}</div>
</div>` : '';
  let c = `${aplicar}${!f.id && !f.duplicando && !f.daIA ? tilesIA('invest') : ''}<div class="campo"><div class="lbl">De quem é este dinheiro?</div>
    <div class="seg dono-seg" style="margin-bottom:10px">
      <button class="${f.titular !== 'terceiros' ? 'on' : ''}" data-a="f-set" data-k="titular" data-v="meu">${ic('user', 'ic-s')}Meu</button>
      <button class="${f.titular === 'terceiros' ? 'on terc' : ''}" data-a="f-set" data-k="titular" data-v="terceiros">${ic('users', 'ic-s')}De terceiros</button></div>`;
  if (f.titular === 'terceiros') {
    c += `<input class="inp${err('terceiro')}" data-f="terceiro" value="${esc(f.terceiro)}" placeholder="De quem? Ex.: Mãe, Pedro, condomínio" autocomplete="off">${msg('terceiro')}`;
    if (ps.length) c += `<div class="chips" style="margin:10px 0 0">${ps.map(p => `<button class="chip${f.terceiro === p ? ' on' : ''}" data-a="f-set" data-k="terceiro" data-v="${esc(p)}">${esc(p)}</button>`).join('')}</div>`;
  }
  // dinheiro em espécie e bens: sem banco, sem rendimento, sem vencimento (bens perdem a taxa da categoria)
  const especie = f.tipo === 'dinheiro' || f.tipo === 'bens', oculto = especie ? ' hidden' : '';
  c += `</div>
    <div class="campo"><label for="f-nome">Nome</label><input id="f-nome" class="inp" data-f="nome" value="${esc(f.nome)}" placeholder="${f.tipo === 'bens' ? 'Ex.: Carro da mãe' : especie ? 'Ex.: Dinheiro em casa' : 'Ex.: CDB Inter 2028'}" autocomplete="off"></div>
    <div class="campo"${oculto}><div class="lbl">Banco</div><div class="chips" style="margin:0">
      ${bancos.map(b => `<button class="chip${f.banco === b.id ? ' on' : ''}" data-a="f-set" data-k="banco" data-v="${b.id}" style="--c:${corOk(b.cor) || '#B8B0B0'}"><span class="bol"></span>${esc(b.nome)}</button>`).join('')}
      <button class="chip add" data-a="f-nb">${ic('plus', 'ic-s')}Banco</button></div>`;
  if (f.novoBanco) {
    c += `<div style="margin-top:12px;padding:14px;border:1px dashed var(--line-2);border-radius:16px">
      <input class="inp${err('nb')}" data-f="nb-nome" value="${esc(f.novoBanco.nome)}" placeholder="Nome do banco ou corretora" list="dl-bancos" autocomplete="off">${msg('nb')}
      <datalist id="dl-bancos">${BANCOS_COMUNS.map(n => `<option value="${esc(n)}">`).join('')}</datalist>
      <div class="cores p" style="margin:12px 0">${PALETA.map(cr => `<button class="cor${f.novoBanco.cor === cr ? ' on' : ''}" style="--c:${cr}" data-a="f-nbcor" data-v="${cr}" aria-label="Cor ${cr}"></button>`).join('')}</div>
      <button class="btn out" data-a="f-nbok">Usar este banco</button></div>`;
  }
  c += `</div>
    <div class="campo"><div class="lbl">Tipo</div><div class="chips" style="margin:0">${TIPOS.map(t =>
      `<button class="chip${f.tipo === t.id ? ' on' : ''}" data-a="f-tipo" data-v="${t.id}">${t.nome}</button>`).join('')}</div></div>
    <div class="duo"><div class="campo" style="margin-bottom:6px"><label for="f-valor">Valor atual</label>
        <div class="pref${err('valor')}"><span>R$</span><input id="f-valor" data-f="valor" inputmode="numeric" value="${f.valor ? NF2.format(f.valor) : ''}" placeholder="0,00"${f.tipo === 'bens' && f.dividir ? ' readonly aria-readonly="true" title="A soma das categorias"' : ''}></div></div>
      <div class="campo" style="margin-bottom:6px"><label for="f-data">Valor em</label><input id="f-data" class="inp" type="date" data-f="data_valor" value="${esc(f.data_valor)}" max="${iso(hoje())}"></div></div>
    ${msg('valor')}<div class="ajuda" id="aj-valor" style="color:var(--muted);font-size:14.5px;margin-bottom:20px"></div>
    ${f.tipo === 'bens' ? camposBens(f) : ''}
    <div class="campo"${oculto}><div class="lbl">Rendimento</div><div class="chips">${IDX.filter(x => !x.oculto || x.id === f.indexador).map(x =>
      `<button class="chip${f.indexador === x.id ? ' on' : ''}" data-a="f-idx" data-v="${x.id}">${x.nome}</button>`).join('')}</div>
      ${ix.taxa ? `<div class="pref${err('taxa')}">${ix.pre ? `<span>${ix.pre}</span>` : ''}<input data-f="taxa" inputmode="decimal" value="${f.taxa === '' || f.taxa == null ? '' : String(f.taxa).replace('.', ',')}" placeholder="${ix.ph}"><span>${ix.suf}</span></div>` : ''}
      ${msg('taxa')}<div class="ajuda" id="aj-taxa"></div></div>
    <div class="campo"${oculto}><div class="lbl">Liquidez</div><div class="seg" style="margin:0">
      <button class="${f.liquidez === 'diaria' ? 'on' : ''}" data-a="f-set" data-k="liquidez" data-v="diaria">Diária</button>
      <button class="${f.liquidez !== 'diaria' ? 'on' : ''}" data-a="f-set" data-k="liquidez" data-v="vencimento">No vencimento</button></div></div>
    <div class="campo"${oculto}><label for="f-venc">Vencimento <span style="color:var(--muted);font-weight:400">(opcional)</span></label>
      <input id="f-venc" class="inp" type="date" data-f="vencimento" value="${esc(f.vencimento || '')}"></div>
    ${fotosFormHTML()}
    <div class="campo"><button class="abre${f.obsAberta ? ' on' : ''}" data-a="f-obs">${ic('chev', 'ic-s')}Observação</button>
      ${f.obsAberta ? `<textarea class="inp" data-f="obs" rows="3" style="margin-top:10px;resize:vertical" placeholder="Algo para lembrar sobre este investimento">${esc(f.obs)}</textarea>` : ''}</div>`;
  const cab = f.id ? `<button class="icbtn" data-a="f-excluir" aria-label="Excluir" style="color:var(--danger)">${ic('trash')}</button>` : '';
  const pe = f.id
    ? `<button class="btn" data-a="f-duplicar">${ic('copy', 'ic-s')}Duplicar</button><button class="btn pri" data-a="f-salvar">Salvar</button>`
    : `<button class="btn" data-a="f-salvar" data-mais="1">Salvar e adicionar outro</button><button class="btn pri" data-a="f-salvar">Salvar</button>`;
  return { titulo, corpo: c, pe, cab, depois: ajudasForm };
}

function ajudasForm() {
  if (!F) return;
  const I = S.d.indices;
  const inv = { indexador: F.indexador, taxa: F.taxa };
  const r = taxaAnual(inv);
  const ix = idxDe(F.indexador);
  const aj = $('#aj-taxa');
  if (aj) {
    let t = '';
    const ok = !ix.taxa || (F.taxa !== '' && !isNaN(F.taxa));
    if (F.indexador === 'parado') t = 'O valor fica parado, sem render.';
    else if (F.indexador === 'estimado') t = ok ? `Estimativa sua, ≈ <b>${pct(r * 100)}% a.a.</b> Entra na projeção, mas o valor de hoje não é corrigido sozinho.` : 'Quanto você espera que renda por ano.';
    else if (ok) {
      const base = { cdi_pct: `CDI de ${pct(I.cdi)}%`, cdi_mais: `CDI de ${pct(I.cdi)}%`, ipca_mais: `IPCA de ${pct(I.ipca)}%`, selic_mais: `Selic de ${pct(I.selic)}%`, poupanca: `Selic de ${pct(I.selic)}% e TR de ${pct(I.tr)}% a.m.`, pre: 'taxa fixa' }[F.indexador];
      t = `≈ <b>${pct(r * 100)}% ao ano</b> hoje, com ${base}`;
    }
    if (ok && r > 0 && F.valor > 0) t += ` · rende ≈ <b>${brl(rendeMes(F.valor, r))}</b> por mês`;
    aj.innerHTML = t;
  }
  const av = $('#aj-valor');
  if (av) {
    let t = '';
    const o = F.original;
    if (o && corrige(F) && S.d.ajustes.corrigir !== false && F.data_valor && F.data_valor < iso(hoje())) {
      const est = valorHoje({ valor: F.valor, data_valor: F.data_valor, indexador: F.indexador, taxa: F.taxa });
      if (est - F.valor >= 0.01) t = `Hoje: ≈ <b>${brl(est)}</b>, corrigido desde ${fData(pData(F.data_valor))}. <button class="link" data-a="f-usar-est">Usar este valor</button>`;
    } else if (F.tipo === 'bens' && F.dividir) t = 'A soma das categorias abaixo.';
    // com Corrigir valores pelo rendimento desligado, o valor de hoje não muda sozinho
    else if (!o && F.tipo === 'bens') t = S.d.ajustes.corrigir !== false ? 'O valor de hoje; a taxa da categoria conta daqui para a frente.' : 'O valor de hoje.';
    else if (!o && corrige(F)) t = S.d.ajustes.corrigir !== false ? 'O saldo de hoje; o rendimento conta daqui para a frente.' : 'O saldo de hoje.';
    av.innerHTML = t;
  }
}

function salvarInvestimento(eOutro) {
  const f = F;
  f.erros = {};
  if (f.tipo === 'bens' && f.dividir) f.valor = round2(Object.values(f.partes || {}).reduce((a, v) => a + (+v || 0), 0));
  const ix = idxDe(f.indexador);
  if (!(f.valor > 0)) f.erros.valor = 'Coloque o valor.';
  if (ix.taxa && (f.taxa === '' || f.taxa == null || isNaN(f.taxa))) f.erros.taxa = 'Coloque a taxa.';
  if (f.titular === 'terceiros' && !String(f.terceiro || '').trim()) f.erros.terceiro = 'Diga de quem é.';
  if (Object.keys(f.erros).length) { pintarFolha(); toast('Falta preencher ' + Object.keys(f.erros).length + (Object.keys(f.erros).length === 1 ? ' campo' : ' campos')); return; }
  const bancos = [...S.d.bancos, ...f.bancosNovos];
  const nomeBanco = bancos.find(b => b.id === f.banco)?.nome || '';
  const inv = {
    id: f.id || uid(),
    nome: (f.nome || '').trim() || `${tipoDe(f.tipo).nome}${nomeBanco && f.tipo !== 'dinheiro' && f.tipo !== 'bens' ? ' ' + nomeBanco : ''}`,
    banco: f.tipo === 'dinheiro' || f.tipo === 'bens' ? '' : f.banco || '', tipo: f.tipo, valor: Math.round(f.valor * 100) / 100, data_valor: f.data_valor || iso(hoje()),
    indexador: f.indexador, taxa: ix.taxa ? +f.taxa : 0, liquidez: f.liquidez, vencimento: f.vencimento || null,
    // bens: a taxa vem da tabela de perda por categoria (Mais › Invest)
    ...(f.tipo === 'bens' ? { indexador: 'deprecia', taxa: taxaBem(f.categoria_bem || 'outros'), categoria_bem: f.categoria_bem || 'outros', liquidez: 'diaria', vencimento: null } : {}),
    ...(f.tipo === 'bens' && f.dividir ? (() => {
      const partes = Object.keys(f.partes || {}).filter(k => +f.partes[k] > 0).map(k => ({ categoria: k, valor: round2(+f.partes[k]), taxa: taxaBem(k) }));
      return partes.length ? { partes, valor: round2(partes.reduce((a, p) => a + p.valor, 0)), taxa: taxaPartes(partes), categoria_bem: partes.length === 1 ? partes[0].categoria : 'varias' } : {};
    })() : { partes: undefined }),
    titular: f.titular === 'terceiros' ? 'terceiros' : 'meu', terceiro: f.titular === 'terceiros' ? String(f.terceiro).trim() : '',
    obs: (f.obs || '').trim(), fotos: (f.fotos || []).slice(), criado_em: f.original?.criado_em || new Date().toISOString(), atualizado_em: new Date().toISOString(),
  };
  const novosBancos = f.bancosNovos.filter(b => b.id === inv.banco || S.d.investimentos.some(i => i.banco === b.id));
  const editando = !!f.id;
  persistir(d => {
    d.bancos.push(...novosBancos.map(({ id, nome, cor }) => ({ id, nome, cor, obs: '' })));
    const k = d.investimentos.findIndex(i => i.id === inv.id);
    if (k >= 0) d.investimentos[k] = inv; else d.investimentos.push(inv);
  }, editando ? 'Investimento salvo' : (eOutro ? 'Salvo. Pode cadastrar o próximo.' : 'Investimento cadastrado')).then(ok => {
    if (!ok) return;
    if (eOutro) {
      F = novoForm({ banco: inv.banco, tipo: inv.tipo, titular: inv.titular, terceiro: inv.terceiro, indexador: inv.indexador, taxa: inv.taxa, liquidez: inv.liquidez });
      pintarFolha();
      const n = $('#f-nome'); if (n) n.focus();
    } else fecharFolha();
  });
}

/* --------- índice */
function abrirIndice(k) {
  const nomes = { cdi: ['CDI', '% a.a.'], selic: ['Selic', '% a.a.'], ipca: ['IPCA em 12 meses', '%'], tr: ['TR', '% a.m.'] };
  const [n, suf] = nomes[k];
  abrirFolha(() => ({
    titulo: n,
    corpo: `<div class="campo"><label for="i-v">Valor</label><div class="pref"><input id="i-v" inputmode="decimal" value="${String(S.d.indices[k]).replace('.', ',')}"><span>${suf}</span></div>
      <div class="ajuda" style="color:var(--muted);font-size:14.5px;margin-top:8px">Mudar à mão desliga a atualização pelo Banco Central.</div></div>`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="i-salvar" data-v="${k}">Salvar</button>`,
  }));
}

/* --------- versões */
function abrirVersoes() {
  let lista = null, erro = null;
  abrirFolha(() => ({
    titulo: 'Versões anteriores',
    corpo: erro ? `<p class="msg-erro">${esc(erro)}</p>` : lista == null ? '<p style="color:var(--muted)">Carregando…</p>'
      : !lista.length ? '<p style="color:var(--muted)">Nenhuma versão anterior ainda.</p>'
        : lista.map(v => {
          const q = v.quando ? new Date(v.quando) : null;
          const motivo = { 'antes-de-importar': 'antes de importar', 'antes-de-restaurar': 'antes de restaurar' }[v.motivo] || 'automática';
          return `<div class="versao-row"><div><b>${q ? fData(q) + ' às ' + q.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : esc(v.nome)}</b>
            <span>${plural(v.investimentos, 'investimento', 'investimentos')} · ${brl(v.total, 0)} · ${motivo}</span></div>
            <button class="btn peq" data-a="restaurar" data-v="${esc(v.nome)}">Restaurar</button></div>`;
        }).join(''),
  }));
  api.versoes().then(l => { lista = l; pintarFolha(); }).catch(e => { erro = e.message; pintarFolha(); });
}

/* ------------------------------------------------------------------ render */
const ABAS = [
  ['inicio', 'Início', 'home'], ['caixa', 'Caixa', 'fluxo'], ['add', 'Adicionar', 'plus'],
  ['investimentos', 'Invest', 'wallet'], ['mais', 'Mais', 'dots'],
];
function pintarNav() {
  $('#nav .in').innerHTML = ABAS.map(([k, n, i]) => k === 'add'
    ? `<button class="add" data-a="novo" aria-label="Adicionar"><span class="pill">${ic('plus')}</span>${n}</button>`
    : `<button class="${S.ui.tab === k ? 'on' : ''}" data-a="tab" data-v="${k}" ${S.ui.tab === k ? 'aria-current="page"' : ''}>${ic(i)}${n}</button>`).join('');
}

// Computador (1000 px ou mais): barra lateral no lugar das abas de baixo, como no ResolvIA, no CronologIA e no InventarIA.
// Seções, Buscar (tecla /), os bancos e as pessoas com dinheiro aqui; cada um abre a Carteira já filtrada.
function irBuscar() {
  // como o Buscar dos outros apps: procura em todos os investimentos
  Object.assign(S.ui, { tab: 'investimentos', invModo: 'carteira', filtro: 'todos', pessoa: null, banco: null });
  salvarUI(); render(); window.scrollTo(0, 0);
  const q = $('#q'); if (q) q.focus();
}
function pintarLado() {
  let el = $('#lado');
  if (!el) { el = document.createElement('aside'); el.id = 'lado'; el.setAttribute('aria-label', 'Menu'); document.body.prepend(el); }
  const d = S.d, u = S.ui, tab = u.tab;
  // com um banco ou uma pessoa aberta, só ele fica marcado (como a lista aberta no ResolvIA)
  const naCarteira = tab === 'investimentos' && u.invModo === 'carteira';
  const itemAberto = naCarteira && ((u.banco && u.filtro === 'todos') || (u.filtro === 'terc' && u.pessoa && !u.banco));
  const link = (k, n, i, extra = '') => `<button class="side-link" data-a="tab" data-v="${k}"${tab === k && !(k === 'investimentos' && itemAberto) ? ' aria-current="page"' : ''}>${ic(i)}<span>${n}</span>${extra}</button>`;
  const nAtr = temCaixa() ? memo('nAtr', () => { avisosCaixa(hoje()); return S.nAtrasadas || 0; }) : 0;
  let h = `<div class="side-brand">${iconeApp()}Gerenc<span>IA</span></div><nav class="side-nav" aria-label="Seções">
    ${link('inicio', 'Início', 'home')}
    ${d.investimentos.length ? `<button class="side-link" data-a="buscar">${ic('search')}<span>Buscar</span><kbd aria-hidden="true">/</kbd></button>` : ''}
    ${link('caixa', 'Caixa', 'fluxo', nAtr ? `<span class="side-badge" title="${plural(nAtr, 'conta atrasada', 'contas atrasadas')}">${nAtr}</span>` : '')}
    ${link('investimentos', 'Investimentos', 'wallet')}
    ${link('mais', 'Mais', 'dots')}</nav>`;
  const pb = new Map();
  for (const i of d.investimentos) pb.set(i.banco || '', (pb.get(i.banco || '') || 0) + valorHoje(i));
  const bancos = [...pb].sort((a, b) => b[1] - a[1]);
  if (bancos.length) {
    h += `<div class="side-h"><span>Bancos</span><small>${bancos.length}</small></div><div class="side-lista">${bancos.map(([id, v]) => {
      const b = bancoDe(id), on = naCarteira && u.banco === (id || '-') && u.filtro === 'todos';
      return `<button class="side-item" data-a="lado-banco" data-v="${esc(id || '-')}"${on ? ' aria-current="page"' : ''}><span class="side-tile" style="--c:${corOk(b?.cor) || 'var(--c0)'}">${esc((b?.nome || '?').slice(0, 1).toUpperCase())}</span><span class="sl-nome">${esc(b?.nome || 'Sem banco')}</span><span class="sl-num">${compacto(v)}</span></button>`;
    }).join('')}</div>`;
  }
  const ps = pessoas();
  if (ps.length) {
    h += `<div class="side-h"><span>De terceiros</span><small>${ps.length}</small></div><div class="side-lista">${ps.map(p => {
      const v = d.investimentos.filter(i => i.titular === 'terceiros' && dono(i) === p).reduce((s2, i) => s2 + valorHoje(i), 0);
      const on = naCarteira && u.filtro === 'terc' && u.pessoa === p && !u.banco;
      return `<button class="side-item" data-a="pessoa" data-v="${esc(p)}"${on ? ' aria-current="page"' : ''}><span class="side-tile terc">${esc(p.slice(0, 1).toUpperCase())}</span><span class="sl-nome">${esc(p)}</span><span class="sl-num">${compacto(v)}</span></button>`;
    }).join('')}</div>`;
  }
  h += `<p class="side-foot">GerencIA ${VERSAO}${DEMO ? ' · prévia' : ''}</p>`;
  el.innerHTML = h;
}

// Números grandes que não cabem diminuem até caber. Pela proporção (largura que cabe ÷ largura do texto), em até 4 passos:
// funciona também quando o celular aumenta as letras (fonte grande no Android), em que o tamanho medido não é o aplicado.
function ajustarTextos() {
  const els = $$('.stat-duo b, .inv-valor, .hl-n');
  els.forEach(el => { el.style.fontSize = ''; });
  for (const el of els) {
    for (let n = 0; n < 4 && el.scrollWidth > el.clientWidth + 1; n++) {
      const atual = parseFloat(el.style.fontSize) || parseFloat(getComputedStyle(el).fontSize);
      el.style.fontSize = Math.max(12, atual * (el.clientWidth / el.scrollWidth) * 0.97).toFixed(2) + 'px';
    }
  }
  // os dois números de cada par ficam do mesmo tamanho (o menor dos dois)
  $$('.stat-duo').forEach(duo => {
    const bs = $$('b', duo).filter(b => b.parentElement.parentElement === duo && b.style.fontSize);
    if (!bs.length) return;
    const fs = Math.min(...bs.map(b => parseFloat(b.style.fontSize)));
    $$('b', duo).filter(b => b.parentElement.parentElement === duo).forEach(b => { b.style.fontSize = fs + 'px'; });
  });
}
function desenharGraficos() {
  if (S.ui.tab === 'investimentos' && S.ui.invModo === 'evolucao') desenharEvolucao();
  if (S.ui.tab === 'caixa' && S.ui.cxModo === 'fluxo') { desenharFluxo(); desenharSaldo(); }
}
try { document.fonts.ready.then(() => { ajustarTextos(); desenharGraficos(); }); } catch (e) { /* ok */ }

function render() {
  if (!S.d) return;
  aplicarTema();
  const telas = { inicio: telaInicio, caixa: telaCaixa, investimentos: telaInvest, mais: telaMais };
  const foco = document.activeElement && document.activeElement.dataset && document.activeElement.dataset.ui;
  const pos = foco ? document.activeElement.selectionStart : null;
  $('#app').innerHTML = (telas[S.ui.tab] || telaInicio)();
  pintarNav();
  pintarLado();
  marcarTela();
  desenharGraficos();
  { const t = $('.mais-abas'), on = t && $('button.on', t); if (on) { const l = on.offsetLeft - 8, r = on.offsetLeft + on.offsetWidth + 8; if (l < t.scrollLeft) t.scrollLeft = l; else if (r > t.scrollLeft + t.clientWidth) t.scrollLeft = r - t.clientWidth; } }
  ajustarTextos();
  requestAnimationFrame(ajustarTextos);
  // um pedido de cada vez: enquanto a resposta não chega, redesenhar Mais não pede de novo
  if (S.ui.tab === 'mais' && !S.ia && !S.iaPedido && !DEMO && iaOn()) {
    S.iaPedido = true;
    api.iaStatus().then(st => { S.ia = st; if (S.ui.tab === 'mais') render(); }).catch(() => {}).finally(() => { S.iaPedido = false; });
  }
  if (maisTela() === 'config' && maisAba() === 'integracoes' && iaOn() && !S.usoPedido && (!S.uso || Date.now() - (S.usoEm || 0) > 30000)) {
    S.usoPedido = true;
    api.iaUso().then(u => { S.uso = u; }).catch(() => { if (!S.uso) S.uso = { today: null, days: [] }; })
      .finally(() => { S.usoPedido = false; S.usoEm = Date.now(); if (S.ui.tab === 'mais') render(); });
  }
  if (maisTela() === 'config' && maisAba() === 'dados' && S.backups == null && !S.bkPedido) {
    S.bkPedido = true;
    api.backups().then(b => { S.backups = b; }).catch(() => { S.backups = []; }).finally(() => { S.bkPedido = false; if (S.ui.tab === 'mais') render(); });
  }
  if (foco) { const el = $(`[data-ui="${foco}"]`); if (el) { el.focus(); try { el.setSelectionRange(pos, pos); } catch (e) { /* ok */ } } }
  if (FOLHA) pintarFolha();
}

// Uma tela de Mais ocupa uma entrada no histórico ({ tela }): o Voltar do celular (ou do navegador) volta para onde
// se estava, o menu (ou a aba do atalho que abriu a tela). Saindo da tela de outro jeito (‹ Mais, a barra de baixo,
// arrastar), a entrada dela é desfeita, para o Voltar seguinte não cair nela. As janelas (folhas) ficam por cima.
let TELA_VISTA = '', TELA_DE = null;
const histTela = () => { try { return (history.state && history.state.tela) || ''; } catch (e) { return ''; } };
function marcarTela() {
  if (FOLHA || CAM) return;
  const agora = maisTela(), antes = TELA_VISTA;
  TELA_VISTA = agora;
  if (agora === antes) return;
  try {
    if (agora) { if (histTela()) history.replaceState({ tela: agora }, ''); else history.pushState({ tela: agora }, ''); }
    else if (histTela() === antes) history.back();
  } catch (e) { /* ok */ }
}
// um atalho para um quadro de Mais (Índices, Dicas...) abre a tela (e a aba de Configurações) onde ele está
const MAIS_ANCORA = { indices: ['invest'], 'perda-bens': ['invest'], dicas: ['caixa'], fixos: ['caixa'], ia: ['config', 'integracoes'], bens: ['config', 'integracoes'] };
function irPara(tab, ancora, tela = '') {
  const de = S.ui.tab, antes = maisTela();
  S.ui.tab = tab;
  S.ui.maisTela = tab === 'mais' && Object.keys(MAIS_TELAS).includes(tela) ? tela : '';
  const agora = maisTela();
  if (!agora) TELA_DE = null;
  else if (agora !== antes) TELA_DE = (antes || de === 'mais') ? null : de; // do menu (ou de outra tela de Mais), o Voltar vai ao menu
  salvarUI();
  render();
  if (entraDe) { // arrastou para o lado: a tela nova entra pelo lado para onde o dedo foi
    const d = entraDe;
    entraDe = 0;
    const app = $('#app');
    if (app.animate && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      app.animate([{ opacity: 0, transform: `translateX(${d > 0 ? 40 : -40}px)` }, { opacity: 1, transform: 'none' }], { duration: 280, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' });
    }
  }
  if (ancora) { const el = document.getElementById(ancora); if (el) { el.scrollIntoView({ block: 'start' }); return; } }
  window.scrollTo(0, 0);
}

/* ------------------------------------------------------------------ eventos */
document.addEventListener('click', ev => {
  const el = ev.target.closest('[data-a]');
  if (!el) return;
  const a = el.dataset.a, v = el.dataset.v, id = el.dataset.id;
  switch (a) {
    case 'tab': { // a barra de baixo (Mais abre o menu) ou um atalho para um quadro de Mais
      const al = v === 'mais' && MAIS_ANCORA[el.dataset.ancora];
      if (al && al[1]) S.ui.maisAba = al[1];
      irPara(v, el.dataset.ancora, al ? al[0] : '');
      break;
    }
    case 'mais-tela': irPara('mais', null, v); break;
    case 'mais-volta': irPara('mais'); break;
    case 'novo':
      if (S.ui.tab === 'investimentos') abrirInvestimento(null, S.ui.filtro === 'terc' && S.ui.pessoa ? { titular: 'terceiros', terceiro: S.ui.pessoa } : null);
      else if (S.ui.tab === 'caixa') abrirLancamento(null, { tipo: S.ui.cxFiltro === 'entradas' ? 'receita' : 'despesa' });
      else abrirEscolhaNovo();
      break;
    case 'novo-inv': abrirInvestimento(null); break;
    case 'lanc-novo': abrirLancamento(null, { tipo: v === 'receita' ? 'receita' : 'despesa' }); break;
    case 'lanc': abrirLancamento(id); break;
    case 'lanc-pagar': {
      const l = acharLanc(id);
      if (l && ehRec(l) && (temPartes(l) || temDescontos(l))) { abrirLancamento(id); Object.assign(LF, { pago: true, pagoMexido: true, descAberto: true, confirmando: true }); pintarFolha(); }
      else abrirPagar(id);
      break;
    }
    case 'pg-ok': confirmarPagar(); break;
    case 'inv-aplicar': abrirAplicar(v); break;
    case 'inv-transferir': abrirTransferir(v); break;
    case 'tr-para': TR.para = v; if (TR.erro === 'para') TR.erro = ''; pintarFolha(); break;
    case 'tr-tudo': { const de = S.d.investimentos.find(i => i.id === TR.de); if (de) { TR.valor = round2(valorHoje(de)); TR.erro = ''; } pintarFolha(); break; }
    case 'tr-apagar': TR.apagar = !!v; pintarFolha(); break;
    case 'tr-ok': confirmarTransferir(); break;
    case 'ap-destino': AP.destino = v; pintarFolha(); break;
    case 'ap-modo': if (AP.modo !== v) { Object.assign(AP, { modo: v, valor: 0, total: 0, erro: '' }); pintarFolha(); requestAnimationFrame(() => { const x = $('#ap-v'); if (x) x.focus(); }); } break;
    case 'ap-conta': AP.conta = v; pintarFolha(); break;
    case 'ap-ok': confirmarAplicar(); break;
    case 'pg-inv': PG.inv = v; PG.erroInv = ''; pintarFolha(); break;
    case 'lf-inv': LF.investimento = v; LF.erroInv = ''; delete LF.erros.investimento; pintarFolha(); break;
    case 'fatura-abrir': S.ui.faturaAberta = S.ui.faturaAberta === v ? null : v; render(); break;
    case 'fatura-pagar': pagarFatura(v); break;
    case 'cx-ajuste': abrirAjuste(); break;
    case 'aj-ok': confirmarAjuste(); break;
    case 'aj-sinal': if (AJ) { AJ.neg = v === '-'; pintarFolha(); } break;
    case 'cx-modo': S.ui.cxModo = v; S.ui.cxSel = null; salvarUI(); render(); break;
    case 'cx-mes': S.ui.cxMes = +v === 0 ? null : addYm(mesCaixa(), +v); S.ui.faturaAberta = null; S.ui.cxSel = null; render(); break;
    case 'cx-filtro': S.ui.cxFiltro = v; salvarUI(); render(); break;
    case 'cx-periodo': if (v === 'outro') abrirPeriodo(); else { S.ui.cxPeriodo = v; salvarUI(); render(); } break;
    case 'cx-per-pre': aplicarPeriodo(...v.split(',')); break;
    case 'cx-per-ok': aplicarPeriodo($('#per-atras').value, $('#per-frente').value); break;
    case 'g-anos-outro': abrirHorizonte(); break;
    case 'g-anos-pre': aplicarHorizonte(v); break;
    case 'g-anos-ok': aplicarHorizonte($('#hz-anos').value); break;
    case 'mais-aba': S.ui.maisAba = v; salvarUI(); render(); { const t = $('.mais-abas'); if (t && t.getBoundingClientRect().top < 0) t.scrollIntoView({ block: 'start' }); } break;
    case 'uso-dia': S.usoSel = v; render(); break;
    case 'bk-restaurar':
      confirmar({ titulo: 'Restaurar backup?', texto: `Os dados de agora são trocados pelos do backup <b>${esc(v)}</b>. Antes, o app guarda uma cópia do que existe hoje em Versões anteriores.`, botao: 'Restaurar',
        acao: () => api.restaurarBackup(v).then(d => { S.d = normalizar(d); render(); toast('Backup restaurado'); }).catch(e => toast('Não consegui restaurar. ' + e.message)) });
      break;
    case 'cx-cat-tipo': S.ui.cxCatTipo = v; S.ui.cxSel = null; salvarUI(); render(); break;
    case 'cx-sel': S.ui.cxSel = S.ui.cxSel === v ? null : v; render(); break;
    case 'cx-ir': S.ui.cxModo = 'lista'; S.ui.cxMes = null; S.ui.cxFiltro = v || 'tudo'; irPara('caixa'); break;
    case 'inv-modo': S.ui.invModo = v; salvarUI(); if (S.ui.tab !== 'investimentos') irPara('investimentos'); else render(); break;
    case 'escolha': { const o = FOLHA && FOLHA.opcoes && FOLHA.opcoes[+v]; fecharFolha(); if (o) o.acao(); break; }
    case 'fixo': { const r = S.d.recorrencias.find(x => x.id === id); if (r) abrirLancamento(`v:${r.id}:${proximaYm(r)}`); break; }
    case 'dica-anual': abrirDicaAnual(v); break;
    case 'aporte-ajustar': { const fx = aportesFixos(); if (fx.length === 1) abrirLancamento(`v:${fx[0].id}:${proximaYm(fx[0])}`); else irPara('mais', 'fixos', 'caixa'); break; }
    case 'aporte-novo': novoAporte(); break;
    case 'dica-fora': persistir(d => { d.ajustes.dicas_fora = [...new Set([...(d.ajustes.dicas_fora || []), v])].slice(-200); }, 'Dica dispensada'); break;
    case 'dica-cat': S.ui.cxModo = 'categorias'; S.ui.cxCatTipo = 'despesa'; S.ui.cxMes = v; salvarUI(); irPara('caixa'); break;
    case 'dicas-conferir': if (S.dicas) S.dicas.conferindo = true; render(); carregarDicas(true); break;
    case 'dicas-voltar': persistir(d => { d.ajustes.dicas_fora = []; }, 'Dicas de volta'); break;
    case 'dicas-freq': persistir(d => { d.ajustes.dicas_freq = v; }); break;
    case 'aviso-pessoa': { const k = el.dataset.k === 'email_para' ? 'email_para' : 'dicas_para'; persistir(d => { const p = new Set(d.ajustes[k] || []); if (p.has(v)) p.delete(v); else p.add(v); d.ajustes[k] = [...p]; }); break; }
    case 'email-abrir': abrirEmail(v); break;
    case 'email-ignorar': { const id = IAS && IAS.email; fecharFolha(); if (id) emailAcao('ignorar', id, 'Fatura ignorada'); break; }
    case 'email-ler': emailAcao('ler', v, 'Lendo com IA'); break;
    case 'email-de-add': emailDeAdicionar(); break;
    case 'email-de-rm': persistir(d => { d.ajustes.email_de = (d.ajustes.email_de || []).filter(x => x !== v); }); break;
    case 'aviso-testar': el.disabled = true; api.avisoTestar().then(() => toast('Aviso enviado para o seu celular.'), e => toast(e.message)).finally(() => { el.disabled = false; }); break;
    case 'da-ok': confirmarDicaAnual(); break;
    case 'categoria': abrirCategoria(id); break;
    case 'categoria-nova': abrirCategoria(null, v); break;
    case 'cat-tipo': FC.tipo = v; pintarFolha(); break;
    case 'cat-cor': FC.cor = v; pintarFolha(); break;
    case 'cat-salvar': {
      const nome = (FC.nome || '').trim();
      if (!nome) { FC.erro = 'Dê um nome.'; pintarFolha(); break; }
      const c = { id: FC.id || 'c-' + uid(), nome, tipo: FC.tipo, cor: FC.cor };
      persistir(d => { const k = d.categorias.findIndex(x => x.id === c.id); if (k >= 0) d.categorias[k] = c; else d.categorias.push(c); }, FC.id ? 'Categoria salva' : 'Categoria criada')
        .then(ok => { if (ok) fecharFolha(); });
      break;
    }
    case 'cat-excluir': {
      const alvo = FC.id;
      confirmar({ titulo: 'Apagar categoria?', texto: 'Os lançamentos dela ficam sem categoria.', botao: 'Apagar', perigo: true,
        acao: () => persistir(d => { d.categorias = d.categorias.filter(c => c.id !== alvo); for (const l of [...d.lancamentos, ...d.recorrencias]) if (l.categoria === alvo) l.categoria = ''; }, 'Categoria apagada') });
      break;
    }
    // formulário de lançamento
    case 'lf-tipo': {
      const apo = v === 'aporte', tipo = v === 'receita' ? 'receita' : 'despesa';
      LF.tipo = tipo; LF.categoria = apo ? 'c-investimentos' : ''; LF.pagoMexido = false; Object.assign(LF, ultimaConta(tipo));
      if (apo && !LF.aporte && LF.repete === 'nao') LF.repete = 'mensal';
      if (!apo && LF.aporte && LF.repete === 'mensal') LF.repete = 'nao';
      LF.aporte = apo;
      if (tipo === 'receita' || apo) { LF.cartao = false; LF.vinculo = ''; }
      pintarFolha(); break;
    }
    case 'lf-set': LF[el.dataset.k] = v; pintarFolha(); break;
    case 'lf-pago': LF.pago = !!v; LF.pagoMexido = true; pintarFolha(); break;
    case 'lf-conta': LF.conta = v; if (!contaDe(v)?.cartao) LF.cartao = false; LF.pagoMexido = LF.id ? LF.pagoMexido : false; pintarFolha(); break;
    case 'lf-cartao': LF.cartao = !!v; if (!LF.id) LF.pagoMexido = false; pintarFolha(); break;
    case 'lf-obs': LF.obsAberta = !LF.obsAberta; pintarFolha(); break;
    case 'lf-desc-abrir': LF.descAberto = true; pintarFolha(); break;
    case 'lf-desc-add': addDesconto(+v); break;
    case 'lf-desc-rm': LF.descontos.splice(+v, 1); pintarFolha(); break;
    case 'lf-desc-modo': trocarModoDesc(+el.dataset.i, v); break;
    case 'lf-ler-recibo': lerRecibo(); break;
    case 'desc-abrir': S.ui.descAberto = S.ui.descAberto === v ? null : v; render(); break;
    case 'lf-cat-nova': LF.novaCat = LF.novaCat ? null : { nome: '', cor: CORES_BANCO.find(c => !S.d.categorias.some(x => x.cor === c)) || CORES_BANCO[0] }; pintarFolha(); break;
    case 'lf-cat-cor': LF.novaCat.cor = v; pintarFolha(); break;
    case 'lf-cat-ok': {
      const nome = (LF.novaCat?.nome || '').trim();
      if (!nome) { toast('Dê um nome para a categoria.'); break; }
      const c = { id: 'c-' + uid(), nome, tipo: LF.tipo, cor: LF.novaCat.cor };
      LF.catsNovas.push(c); LF.categoria = c.id; LF.novaCat = null; pintarFolha(); break;
    }
    case 'lf-salvar': salvarLanc(v, !!el.dataset.mais); break;
    case 'lf-duplicar': LF = Object.assign({}, LF, { id: null, virtual: false, recorrencia: null, competencia: null, grupo: null, parcela: null, repete: 'nao', pagoMexido: false }); pintarFolha(); break;
    case 'lf-excluir': excluirLanc(); break;
    // imagens e IA
    case 'falar': if (!vozPronta()) break; abrirIA(S.ui.tab === 'investimentos' ? 'invest' : 'caixa', 'voz'); break;
    case 'ia-falar': comecarFala(); break;
    case 'fala-mic': if (IAS && IAS.rec === 'on') terminarFala(); else comecarFala(); break;
    case 'chat': if (chatPronto()) abrirChat(); break;
    case 'ch-enviar': if (CH) enviarChat(CH.texto); break;
    case 'ch-sug': if (CH) enviarChat(v); break;
    case 'ch-mic': if (CH && CH.rec === 'on') terminarDitado(); else comecarDitado(); break;
    case 'ch-ok': confirmarAcaoChat(id, el.dataset.g); break;
    case 'ch-editar': editarAcaoChat(id, el.dataset.g); break;
    case 'ch-limpar': if (CH) { CH.limpar = true; pintarFolha(); } break;
    case 'ch-limpar-nao': if (CH) { CH.limpar = false; pintarFolha(); } break;
    case 'ch-limpar-sim':
      if (CH) api.chatLimpar().then(r => { if (CH) { Object.assign(CH, { msgs: r.mensagens || [], limpar: false, erro: '' }); pintarFolha(); } }).catch(e => toast('Não consegui apagar. ' + (e.message || '')));
      break;
    case 'fala-ok': terminarFala(); break;
    case 'ia': if (!iaOn()) { toast('A IA está desligada. Para usar, ligue em Mais › Configurações › Integrações.'); break; } abrirIA(v); break;
    case 'ia-saldos': if (!iaOn()) { toast('A IA está desligada. Para usar, ligue em Mais › Configurações › Integrações.'); break; } abrirIA('invest', null, { saldos: true, pessoa: v || '', sobre: !!el.dataset.sobre }); break;
    case 'ias-pessoa': IAS.pessoa = v; pintarFolha(); break;
    case 'ia-de': {
      if (!iaOn()) break;
      const ini = el.dataset.ini, o = { soInvest: v === 'invest', sobre: true };
      if (ini === 'voz' && !vozPronta()) break;
      // a galeria abre direto, sem trocar a janela: se desistir, continua na Nova despesa
      if (ini === 'arquivo') { escolherArquivo('image/*,application/pdf').then(f => { if (!f || !FOLHA) return; abrirIA(v, 'colado', o); iaPegarArquivo(f); }); break; }
      if (ini === 'camera') { abrirCamera(fotos => { abrirIA(v, 'camera', o); iaUsarFotos(fotos); }); break; }
      abrirIA(v, ini, o); break;
    }
    case 'ia-cam': abrirCamera(iaUsarFotos); break;
    case 'cam-fechar': fecharCamera(); break;
    case 'cam-foto': camFoto(); break;
    case 'cam-pronto': camPronto(); break;
    case 'cam-luz': camLuz(); break;
    case 'cam-galeria': camGaleria(); break;
    case 'ia-arq': escolherArquivo('image/*,application/pdf').then(iaPegarArquivo); break;
    case 'ia-arq-rm': IAS.arquivo = null; IAS.pedeSenha = false; IAS.senha = ''; IAS.erro = ''; pintarFolha(); break;
    case 'ias-guardar': IAS.guardarSenha = IAS.guardarSenha === false; pintarFolha(); break;
    case 'senha-nova': abrirSenhaNova(); break;
    case 'senha-salvar': salvarSenhaNova(); break;
    case 'senha-apagar': api.senhaApagar(v).then(r => { S.senhas = r.senhas; render(); toast('Senha apagada'); }, e => toast(e.message)); break;
    case 'ia-ler': iaLer(); break;
    case 'ia-voltar': IAS.etapa = 'entrada'; pintarFolha(); break;
    case 'ia-marca': { const it = IAS.itens[+el.dataset.i]; it.marcado = !it.marcado; pintarFolha(); break; }
    case 'ia-marca-inv': { const it = IAS.invs[+el.dataset.i]; it.marcado = !it.marcado; pintarFolha(); break; }
    case 'ia-salvar': salvarIA(); break;
    case 'iac-conta': IAS.conta = v; if (!contaDe(v)?.cartao) IAS.cartao = false;
      for (const it of IAS.itens) { it.conta = v; it.noCartao = it.tipo === 'despesa' && IAS.cartao && !!contaDe(v)?.cartao && it.cartao !== false; }
      pintarFolha(); break;
    case 'iac-cartao': IAS.cartao = !!v; for (const it of IAS.itens) it.noCartao = it.tipo === 'despesa' && !!v && !!contaDe(it.conta)?.cartao; pintarFolha(); break;
    case 'iac-sit': IAS.situacao = v; pintarFolha(); break;
    case 'iac-futuras': IAS.futuras = !IAS.futuras; pintarFolha(); break;

    case 'iai-revisar': revisarItemInvest(+el.dataset.i); break;
    case 'iae-liq': IAS.edit.r.liquidez = v; pintarFolha(); break;
    case 'iae-voltar': IAS.edit = null; IAS.etapa = 'revisao'; pintarFolha(); break;
    case 'iae-ok': { const r = IAS.edit.r; if (!(r.valor > 0)) { toast('Coloque o valor.'); break; }
      r.nome = String(r.nome || '').trim() || r.banco || 'Investimento'; r.taxa = Number(String(r.taxa ?? '').replace(',', '.')) || 0;
      IAS.invs[IAS.edit.k] = Object.assign(r, { marcado: true, confianca: 'alta' }); IAS.edit = null; IAS.etapa = 'revisao'; pintarFolha(); break; }
    case 'ia-verificar': S.ia = null; carregarVoz(); render(); api.iaStatus().then(st => { S.ia = st; render(); toast(st.pronta ? 'IA pronta' : (st.motivo || 'IA não está pronta')); }).catch(e => toast(e.message)); break;
    case 'f-foto-add':
      escolherArquivo('image/*').then(async file => {
        if (!file) return;
        try { const n = await enviarFoto(file); F.fotos = [...(F.fotos || []), n]; pintarFolha(); } catch (e) { toast('Não consegui enviar a imagem. ' + e.message); }
      });
      break;
    case 'f-foto-rm': F.fotos = (F.fotos || []).filter(n => n !== v); pintarFolha(); break;
    case 'foto-ver': verFoto(v); break;
    case 'inv': abrirInvestimento(id); break;
    case 'olho': S.oculto = !S.oculto; store.set('oculto', S.oculto); render(); break;
    case 'busca-limpar': S.ui.busca = ''; render(); { const q = $('#q'); if (q) q.focus(); } break;
    case 'filtro': S.ui.filtro = v; S.ui.pessoa = null; salvarUI(); render(); break;
    case 'pessoa-f': S.ui.pessoa = v || null; render(); break;
    case 'banco-f': S.ui.banco = v || null; render(); break;
    case 'buscar': irBuscar(); break;
    case 'lado-banco': Object.assign(S.ui, { invModo: 'carteira', filtro: 'todos', pessoa: null, banco: v, busca: '' }); irPara('investimentos'); break;
    case 'pessoa': S.ui.filtro = 'terc'; S.ui.pessoa = v; S.ui.banco = null; S.ui.invModo = 'carteira'; irPara('investimentos'); break;
    case 'graf-comp': S.ui.invModo = 'divisao'; S.ui.gAgrup = v; S.ui.gEscopo = 'tudo'; salvarUI(); irPara('investimentos'); break;
    case 'g': {
      const k = el.dataset.k;
      if (k === 'gAnos') S.ui.gAnos = +v;
      else if (k === 'gIR') S.ui.gIR = !!v;
      else if (k === 'gSemBens') S.ui.gSemBens = !!v;
      else if (k === 'gSel') S.ui.gSel = S.ui.gSel === v ? null : v;
      else if (k === 'gModo') S.ui.invModo = v === 'composicao' ? 'divisao' : 'evolucao';
      else { S.ui[k] = v; if (k === 'gAgrup') S.ui.gSel = null; }
      salvarUI(); render(); break;
    }
    case 'carregar-exemplo': {
      const ex = gerarExemplo();
      persistir(d => { d.bancos = ex.bancos; d.investimentos = ex.investimentos; d.lancamentos = ex.lancamentos; d.recorrencias = ex.recorrencias; d.categorias = ex.categorias; d.exemplo = true; d._hist = ex.historico; }, 'Exemplo carregado');
      break;
    }
    case 'apagar-exemplo':
      confirmar({ titulo: 'Apagar exemplo?', texto: 'Os dados de demonstração saem.', botao: 'Apagar exemplo', perigo: true,
        acao: () => persistir(d => { d.bancos = []; d.investimentos = []; d.lancamentos = []; d.recorrencias = []; d.categorias = clone(CATEGORIAS_PADRAO); d.exemplo = false; d._hist = []; }, 'Exemplo apagado') });
      break;
    case 'apagar-tudo':
      confirmar({ titulo: 'Apagar tudo?', texto: `Saem ${plural(S.d.investimentos.length, 'investimento', 'investimentos')} e ${plural(S.d.bancos.length, 'banco', 'bancos')}. Uma cópia fica em Versões anteriores.`, botao: 'Apagar tudo', perigo: true,
        acao: () => persistir(d => { d.bancos = []; d.investimentos = []; d.lancamentos = []; d.recorrencias = []; d.exemplo = false; d._hist = []; }, 'Tudo apagado') });
      break;
    case 'tema': S.d.ajustes.tema = v; aplicarTema(); render(); persistir(d => { d.ajustes.tema = v; }); break;
    // escolher uma cor desliga a Cor do dia e fica com ela
    case 'cor': Object.assign(S.d.ajustes, { cor: v, cor_dia: false }); aplicarTema(); render(); persistir(d => { Object.assign(d.ajustes, { cor: v, cor_dia: false }); }); break;
    case 'ajuste': {
      // as chaves vêm ligadas por padrão; as de DESLIGADAS_PADRAO (o aviso no celular), desligadas
      const k = el.dataset.k; const nv = DESLIGADAS_PADRAO.has(k) ? S.d.ajustes[k] !== true : S.d.ajustes[k] === false;
      persistir(d => { d.ajustes[k] = nv; }).then(ok => {
        if (!ok) return;
        if (k === 'ia') { S.ia = null; S.uso = null; S.emails = undefined; carregarVoz(); render(); }
        if (k === 'dicas') carregarDicas();
        if (k === 'email') { S.emails = undefined; carregarEmails(true); }
        // ligou o aviso sem ninguém escolhido: começa com quem está usando o app
        const para = { dicas_aviso: 'dicas_para', email_aviso: 'email_para' }[k];
        if (para && nv && !(S.d.ajustes[para] || []).length) carregarPessoasAviso().then(r => {
          const eu = r && r.pessoas && r.pessoas.find(p => p.eu);
          if (eu && !(S.d.ajustes[para] || []).length) persistir(d => { d.ajustes[para] = [eu.id]; });
        });
        if (k === 'bens') carregarBens();
      });
      break;
    }
    case 'banco': abrirBanco(id); break;
    case 'bens': abrirFolha(montarBens); break;
    case 'bens-evolucao': fecharFolha(); Object.assign(S.ui, { tab: 'investimentos', invModo: 'evolucao', gEscopo: S.ui.gEscopo === 'terc' ? 'meu' : S.ui.gEscopo }); salvarUI(); render(); window.scrollTo(0, 0); break;
    case 'bens-atualizar': S.bens = null; render(); if (FOLHA) pintarFolha(); carregarBens(true); break;
    case 'bens-dir': { const t = taxaBem(el.dataset.k), v = Math.abs(t) * +el.dataset.v; if (v !== t && Math.abs(t)) salvarTaxaBem(el.dataset.k, v); else if (!Math.abs(t)) { el.parentNode.querySelectorAll('button').forEach(x => { x.classList.toggle('on', x === el); x.setAttribute('aria-pressed', x === el); }); } break; }
    case 'banco-sug': abrirBanco(null, v); break;
    case 'indice': abrirIndice(v); break;
    case 'indices-auto': api.indices({ auto: !S.d.indices.auto }).then(d => { S.d = normalizar(d); render(); }).catch(e => toast(e.message)); break;
    case 'indices-atualizar':
      el.disabled = true; el.innerHTML = `${ic('refresh')}Buscando…`;
      api.atualizarIndices().then(d => { S.d = normalizar(d); render(); toast(S.d.indices.erro ? 'Banco Central não respondeu. Mantive os valores.' : 'Índices atualizados'); })
        .catch(e => { toast('Não consegui atualizar. ' + e.message); render(); });
      break;
    case 'relatorio': if (DEMO) toast('Na prévia o relatório não abre.'); else location.href = urlRelatorio(); break;
    case 'demo-arq': toast('Na prévia os arquivos não são baixados.'); break;
    case 'backup': api.backup().then(r => { toast(`Backup salvo em ${r.pasta}/${r.arquivo}`); S.backups = null; render(); }).catch(e => toast('Não consegui criar o backup. ' + e.message)); break;
    case 'importar': $('#arquivo').click(); break;
    case 'versoes': abrirVersoes(); break;
    case 'restaurar':
      confirmar({ titulo: 'Restaurar esta versão?', texto: 'Os dados de agora são trocados por essa versão. Uma cópia de hoje fica guardada.', botao: 'Restaurar',
        acao: () => api.restaurar(v).then(d => { S.d = normalizar(d); render(); toast('Versão restaurada'); }).catch(e => toast(e.message)) });
      break;
    case 'fechar': fecharFolha(false, true); break;
    case 'confirmar': { const fn = FOLHA && FOLHA.confirmar; fecharFolha(); if (fn) fn(); break; }

    // formulário de investimento
    case 'f-set':
      F[el.dataset.k] = v;
      if (el.dataset.k === 'titular' && v === 'terceiros') setTimeout(() => { const i = $('[data-f="terceiro"]'); if (i && !i.value) i.focus(); }, 30);
      pintarFolha(); break;
    case 'f-dividir': F.dividir = !!v; if (v && !F.partes) F.partes = F.valor ? { [F.categoria_bem || 'outros']: F.valor } : {}; pintarFolha(); break;
    case 'f-tipo': {
      F.tipo = v;
      const p = tipoDe(v).p;
      if (!F.id) { F.liquidez = p.liquidez; if (!F.idxEditado) { F.indexador = p.indexador; F.taxa = p.taxa; } }
      // dinheiro e bens têm rendimento próprio; saindo deles, volta o de costume do tipo
      if (v === 'bens' || v === 'dinheiro' || ['deprecia', 'parado'].includes(F.indexador)) Object.assign(F, { indexador: p.indexador, taxa: p.taxa, liquidez: p.liquidez });
      pintarFolha(); break;
    }
    case 'f-idx': {
      if (F.indexador !== v) {
        F.indexador = v; F.idxEditado = true;
        const ix = idxDe(v);
        F.taxa = ix.taxa ? (v === 'cdi_pct' ? 100 : v === 'selic_mais' ? 0 : '') : 0;
        delete F.erros.taxa;
      }
      pintarFolha();
      const t = $('[data-f="taxa"]'); if (t && t.value === '') t.focus();
      break;
    }
    case 'f-obs': F.obsAberta = !F.obsAberta; pintarFolha(); break;
    case 'f-nb': F.novoBanco = F.novoBanco ? null : { nome: '', cor: CORES_BANCO.find(c => ![...S.d.bancos, ...F.bancosNovos].some(b => b.cor === c)) || CORES_BANCO[0] }; pintarFolha(); if (F.novoBanco) $('[data-f="nb-nome"]').focus(); break;
    case 'f-nbcor': F.novoBanco.cor = v; pintarFolha(); break;
    case 'f-nbok': {
      const nome = (F.novoBanco.nome || '').trim();
      if (!nome) { F.erros.nb = 'Dê um nome.'; pintarFolha(); break; }
      const existe = S.d.bancos.find(b => b.nome.toLowerCase() === nome.toLowerCase());
      if (existe) F.banco = existe.id;
      else { const nb = { id: 'b-' + uid(), nome, cor: F.novoBanco.cor }; F.bancosNovos.push(nb); F.banco = nb.id; }
      F.novoBanco = null; delete F.erros.nb; pintarFolha(); break;
    }
    case 'f-usar-est': {
      F.valor = Math.round(valorHoje({ valor: F.valor, data_valor: F.data_valor, indexador: F.indexador, taxa: F.taxa }) * 100) / 100;
      F.data_valor = iso(hoje()); pintarFolha(); break;
    }
    case 'f-salvar': salvarInvestimento(!!el.dataset.mais); break;
    case 'f-duplicar':
      F = Object.assign(F, { id: null, original: null, duplicando: true, nome: F.nome ? F.nome + ' (cópia)' : '' });
      pintarFolha(); break;
    case 'f-excluir': {
      const alvo = F.id, nome = F.nome;
      confirmar({ titulo: 'Excluir investimento?', texto: `<b>${esc(nome)}</b> sai da lista e dos gráficos. Uma cópia fica em Versões anteriores.`, botao: 'Excluir', perigo: true,
        acao: () => persistir(d => { d.investimentos = d.investimentos.filter(i => i.id !== alvo); }, 'Investimento excluído') });
      break;
    }

    // banco
    case 'b-cor': FB.cor = v; pintarFolha(); break;
    case 'b-salvar': salvarBanco(); break;
    case 'bc-add': FB.contas.push({ id: 'k-' + uid(), pessoa: '', cartao: false, fechamento: '', vencimento: '' }); pintarFolha(); break;
    case 'bc-rm': FB.contas.splice(+el.dataset.i, 1); pintarFolha(); break;
    case 'bc-cartao': { const c = FB.contas[+el.dataset.i]; c.cartao = !c.cartao; pintarFolha(); break; }
    case 'b-excluir': {
      const alvo = FB.id, n = S.d.investimentos.filter(i => i.banco === alvo).length;
      confirmar({ titulo: 'Excluir banco?', texto: n ? `${plural(n, 'investimento fica', 'investimentos ficam')} sem banco. Dá para escolher outro depois.` : 'O banco sai da lista.', botao: 'Excluir', perigo: true,
        acao: () => persistir(d => {
          const ks = new Set((d.bancos.find(b => b.id === alvo)?.contas || []).map(c => c.id));
          d.bancos = d.bancos.filter(b => b.id !== alvo);
          d.investimentos.forEach(i => { if (i.banco === alvo) i.banco = ''; });
          for (const l of [...d.lancamentos, ...d.recorrencias]) if (ks.has(l.conta)) { l.conta = ''; l.cartao = false; }
        }, 'Banco excluído') });
      break;
    }

    // índice
    case 'i-salvar': {
      const val = parseNum($('#i-v').value);
      if (isNaN(val)) { toast('Valor inválido'); break; }
      api.indices({ [v]: val }).then(d => { S.d = normalizar(d); fecharFolha(); render(); toast('Índice atualizado'); }).catch(e => toast(e.message));
      break;
    }
    default: break;
  }
});

document.addEventListener('input', ev => {
  const el = ev.target;
  if (el.dataset.ch === 'texto' && CH) {
    CH.texto = el.value;
    ajustarAlturaChat(el);
    const b = $('.ch-env'); if (b) b.disabled = CH.enviando || !CH.texto.trim();
    return;
  }
  if (el.dataset.fparte && F) {
    const dig = el.value.replace(/\D/g, '').slice(0, 13), v = dig ? parseInt(dig, 10) / 100 : 0;
    F.partes = Object.assign({}, F.partes, { [el.dataset.fparte]: v });
    el.value = dig ? NF2.format(v) : '';
    F.valor = round2(Object.values(F.partes).reduce((a, x) => a + (+x || 0), 0)); delete F.erros.valor;
    const vi = $('[data-f="valor"]'); if (vi) vi.value = F.valor ? NF2.format(F.valor) : '';
    const ps = $('#partes-soma'); if (ps) ps.innerHTML = `Total: <b>${brl(F.valor)}</b>. As taxas ficam em Mais › Invest.`;
    return;
  }
  if (el.dataset.f && F) {
    const k = el.dataset.f;
    if (k === 'valor') {
      const dig = el.value.replace(/\D/g, '').slice(0, 13);
      F.valor = dig ? parseInt(dig, 10) / 100 : 0;
      el.value = dig ? NF2.format(F.valor) : '';
      if (F.original && !F.dataEditadaAgora) { F.data_valor = iso(hoje()); $('[data-f="data_valor"]').value = F.data_valor; }
      delete F.erros.valor;
    } else if (k === 'taxa') { const n = parseNum(el.value); F.taxa = isNaN(n) ? '' : n; }
    else if (k === 'nb-nome') F.novoBanco.nome = el.value;
    else if (k === 'data_valor') { F.data_valor = el.value; F.dataEditadaAgora = true; }
    else F[k] = el.value;
    ajudasForm();
    return;
  }
  if (el.dataset.fb && FB) { FB[el.dataset.fb] = el.value; return; }
  if (el.dataset.fbc && FB) { FB.contas[+el.dataset.i][el.dataset.fbc] = el.dataset.fbc === 'pessoa' ? el.value : el.value.replace(/\D/g, '').slice(0, 2); if (el.dataset.fbc !== 'pessoa') el.value = FB.contas[+el.dataset.i][el.dataset.fbc]; return; }
  if (el.dataset.fc && FC) { FC[el.dataset.fc] = el.value; return; }
  if (el.dataset.fs && FS) {
    FS[el.dataset.fs] = el.value;
    // ao digitar, o aviso de antes sai (sem repintar, para não perder o cursor)
    if (FS.erro) { FS.erro = ''; $('.folha .msg-erro')?.remove(); $('#sn-senha')?.classList.remove('erro'); }
    return;
  }
  if (el.dataset.ias === 'senha' && IAS && IAS.erro) { IAS.erro = ''; $('.folha .msg-erro')?.remove(); }  // digitando a senha, o aviso de antes sai
  if (el.dataset.ias && IAS) { IAS[el.dataset.ias] = el.value; const b = $('[data-a="ia-ler"]'); if (b) b.disabled = !IAS.arquivo && !IAS.texto.trim(); return; }
  if (el.dataset.iai === 'contasel' && IAS) { const it = IAS.itens[+el.dataset.i], [c, cart] = el.value.split('|'); it.conta = c; it.noCartao = cart === 'c'; pintarFolha(); return; }
  if (el.dataset.iai && IAS) { IAS.itens[+el.dataset.i][el.dataset.iai] = el.value; return; }
  if (el.dataset.iav && IAS) { IAS.invs[+el.dataset.i][el.dataset.iav] = el.value; pintarFolha(); return; }
  if (el.dataset.iae && IAS && IAS.edit) {
    const r = IAS.edit.r, k = el.dataset.iae;
    if (k === 'valor') { const dig = el.value.replace(/\D/g, '').slice(0, 13); r.valor = dig ? parseInt(dig, 10) / 100 : 0; el.value = dig ? NF2.format(r.valor) : ''; return; }
    r[k] = el.value;
    // trocar o tipo traz o rendimento e a liquidez de costume; trocar o rendimento mostra ou esconde a taxa
    if (k === 'tipo') Object.assign(r, tipoDe(el.value).p);
    if (k === 'tipo' || k === 'indexador') pintarFolha();
    return;
  }
  if (el.dataset.tr && TR) {
    const dig = el.value.replace(/\D/g, '').slice(0, 13);
    const antes = TR.valor;
    TR.valor = dig ? parseInt(dig, 10) / 100 : 0; if (TR.erro === 'valor') TR.erro = '';
    el.value = dig ? NF2.format(TR.valor) : '';
    const de = S.d.investimentos.find(i => i.id === TR.de), aj = $('#tr-ajuda'), b = $('[data-a="tr-ok"]');
    const atual = de ? round2(valorHoje(de)) : 0, era = Math.abs(antes - atual) < 0.005, e = Math.abs(TR.valor - atual) < 0.005;
    if (era !== e) { pintarFolha(); const v = $('#tr-v'); if (v) { v.focus(); v.setSelectionRange(v.value.length, v.value.length); } return; }
    if (aj) aj.innerHTML = transferirAjuda();
    if (b) b.textContent = 'Transferir' + (TR.valor ? ' ' + brl(TR.valor, 0) : '');
    return;
  }
  if (el.dataset.ap && AP) {
    if (el.dataset.ap === 'valor' || el.dataset.ap === 'total') {
      const dig = el.value.replace(/\D/g, '').slice(0, 13), n = dig ? parseInt(dig, 10) / 100 : 0;
      const inv = S.d.investimentos.find(i => i.id === AP.inv), aj = $('#ap-ajuda'), b = $('[data-a="ap-ok"]');
      if (el.dataset.ap === 'total') { AP.total = n; AP.valor = inv ? Math.max(0, round2(n - valorHoje(inv))) : 0; } else AP.valor = n;
      AP.erro = '';
      el.value = dig ? NF2.format(n) : '';
      if (inv && aj) aj.innerHTML = aplicarAjuda(valorHoje(inv));
      if (b) b.textContent = 'Aplicar' + (AP.valor ? ' ' + brl(AP.valor, 0) : '');
    } else AP.data = el.value;
    return;
  }
  if (el.dataset.aj && AJ) {
    // um "-" digitado deixa negativo; apagar o "-" (com números no campo) deixa positivo; campo vazio mantém o sinal
    const dig = el.value.replace(/\D/g, '').slice(0, 13);
    if (/[-−]/.test(el.value)) AJ.neg = true; else if (dig && AJ.neg && !el.value.startsWith('-')) AJ.neg = false;
    AJ.abs = dig ? parseInt(dig, 10) / 100 : 0;
    el.value = dig ? ajTexto() : (AJ.neg ? '-' : '');
    document.querySelectorAll('[data-a="aj-sinal"]').forEach(b => b.classList.toggle('on', (b.dataset.v === '-') === AJ.neg));
    return;
  }
  if (el.dataset.pg && PG) {
    const alvo = PG;
    const dig = el.value.replace(/\D/g, '').slice(0, 13);
    alvo.valor = dig ? parseInt(dig, 10) / 100 : 0;
    el.value = dig ? NF2.format(alvo.valor) : '';
    return;
  }
  if (el.dataset.da && DA) {
    if (el.dataset.da === 'valor') {
      const dig = el.value.replace(/\D/g, '').slice(0, 11);
      DA.valor = dig ? parseInt(dig, 10) / 100 : 0;
      el.value = dig ? NF2.format(DA.valor) : '';
    } else DA.data = el.value;
    DA.erro = '';
    const e = $('#da-eco'); if (e) e.innerHTML = ecoDA();
    return;
  }
  if (el.dataset.lfp && LF) {
    const p = LF.partes[+el.dataset.i]; if (!p) return;
    if (el.dataset.lfp === 'valor') { const dig = el.value.replace(/\D/g, '').slice(0, 13); p.valor = dig ? parseInt(dig, 10) / 100 : 0; el.value = dig ? NF2.format(p.valor) : ''; }
    else p.descricao = el.value;
    atualizarDescontosVivo(); return;
  }
  if (el.dataset.lfd && LF) {
    const x = LF.descontos[+el.dataset.i]; if (!x) return;
    if (el.dataset.lfd === 'valor') {
      if (x.modo === 'pct') { const n = parseNum(el.value); x.valor = isNaN(n) ? 0 : Math.min(100, Math.max(0, n)); }
      else { const dig = el.value.replace(/\D/g, '').slice(0, 11); x.valor = dig ? parseInt(dig, 10) / 100 : 0; el.value = dig ? NF2.format(x.valor) : ''; }
    } else x.descricao = el.value;
    atualizarDescontosVivo(); return;
  }
  if (el.dataset.lfv && LF) { LF.vinculo = el.value; pintarFolha(); return; }
  if (el.dataset.lfn != null && LF && el.type === 'checkbox') { const n = (LF.ligadosNovos || [])[+el.dataset.lfn]; if (n) n.sel = el.checked; atualizarDescontosVivo(); return; }
  if (el.dataset.lfds && LF) {
    const x = LF.descontos[+el.dataset.i]; if (!x) return;
    x[el.dataset.lfds] = el.value;
    atualizarDescontosVivo(); return;
  }
  if (el.dataset.lf && LF) {
    const k = el.dataset.lf;
    if (k === 'valor') {
      const dig = el.value.replace(/\D/g, '').slice(0, 13);
      LF.valor = dig ? parseInt(dig, 10) / 100 : 0;
      el.value = dig ? NF2.format(LF.valor) : '';
      delete LF.erros.valor;
      if (LF.descontos.length) atualizarDescontosVivo();
      if (LF.repete === 'parcelado') pintarFolhaDepois();
    } else if (k === 'vezes') { LF.vezes = el.value.replace(/\D/g, '').slice(0, 3); el.value = LF.vezes; pintarFolhaDepois(); }
    else if (k === 'novaCat') LF.novaCat.nome = el.value;
    else if (k === 'descricao') {
      LF.descricao = el.value;
      if (!LF.id && !LF.categoria) {
        const igual = S.d.lancamentos.filter(l => l.tipo === LF.tipo && semAcento(l.descricao) === semAcento(el.value)).pop();
        if (igual) { LF.categoria = igual.categoria; LF.conta = igual.conta; LF.cartao = !!igual.cartao; pintarFolhaDepois(); }
      }
    } else if (k === 'data') { LF.data = el.value; if (!LF.id || !LF.pagoMexido) LF.pagoMexido = false; pintarFolhaDepois(); }
    else LF[k] = el.value;
    return;
  }
  if (el.dataset.ui === 'busca') { S.ui.busca = el.value; if (S.ui.invModo !== 'carteira' && el.value) { S.ui.invModo = 'carteira'; salvarUI(); } render(); return; }
});

// Arrastar para o lado troca de aba no celular, como no ResolvIA, no CronologIA e no InventarIA: Início ⇄ Caixa ⇄ Invest ⇄ Mais
// (numa tela de Mais, para a direita volta ao menu).
// Não vale começando na borda da tela (é o Voltar do celular), num campo, num gráfico (lá o dedo mostra os valores),
// numa fileira que rola para o lado, com uma janela aberta ou no computador (lá há a barra lateral).
const ABAS_ARRASTE = ['inicio', 'caixa', 'investimentos', 'mais'];
let arraste = null, entraDe = 0;
document.addEventListener('touchstart', ev => {
  arraste = null;
  if (!S.d || FOLHA || !ev.touches || ev.touches.length !== 1 || matchMedia('(min-width: 1000px)').matches) return;
  const t = ev.touches[0];
  if (t.clientX < 24 || t.clientX > window.innerWidth - 24) return;
  for (let el = ev.target instanceof Element ? ev.target : ev.target.parentElement; el && el !== document.body; el = el.parentElement) {
    if (el.matches('input, textarea, select, [contenteditable], [data-noswipe], .chart, #nav')) return;
    const st = getComputedStyle(el);
    if ((st.overflowX === 'auto' || st.overflowX === 'scroll') && el.scrollWidth > el.clientWidth + 2) return;
  }
  arraste = { x: t.clientX, y: t.clientY, at: Date.now() };
}, { passive: true });
document.addEventListener('touchend', ev => {
  const s = arraste;
  arraste = null;
  if (!s || FOLHA || !ev.changedTouches || !ev.changedTouches.length) return;
  const t = ev.changedTouches[0], dx = t.clientX - s.x, dy = t.clientY - s.y;
  if (Math.abs(dx) < 70 || Math.abs(dx) < Math.abs(dy) * 2 || Date.now() - s.at > 800) return;
  const d = dx < 0 ? 1 : -1; // dedo para a esquerda: a próxima aba
  // numa tela de Mais (Bancos, Configurações...), arrastar para a direita volta para o menu
  if (maisTela()) { if (d < 0) { entraDe = d; irPara('mais'); } return; }
  const i = ABAS_ARRASTE.indexOf(S.ui.tab), j = i + d;
  if (i < 0 || j < 0 || j >= ABAS_ARRASTE.length) return;
  entraDe = d;
  irPara(ABAS_ARRASTE[j]);
}, { passive: true });
document.addEventListener('touchcancel', () => { arraste = null; }, { passive: true });

document.addEventListener('keydown', ev => {
  if (ev.key === 'Escape' && CAM) fecharCamera();
  else if (ev.key === 'Escape' && FOLHA) fecharFolha(false, true);
  if (ev.key === '/' && !FOLHA && !ev.ctrlKey && !ev.metaKey && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || '')) {
    const q = $('#q'); if (q) { ev.preventDefault(); q.focus(); } else if (S.d && S.d.investimentos.length) { ev.preventDefault(); irBuscar(); }
  }
  if (ev.key === 'Escape' && document.activeElement?.id === 'q' && S.ui.busca) { S.ui.busca = ''; render(); }
  if ((ev.key === 'Enter' || ev.key === ' ') && ev.target.matches && ev.target.matches('div[role="button"][data-a]')) { ev.preventDefault(); ev.target.click(); }
  if (ev.key === 'Enter' && !ev.shiftKey && !ev.isComposing && ev.target.id === 'ch-txt' && CH) { ev.preventDefault(); enviarChat(CH.texto); }
  if (ev.key === 'Enter' && ev.target.id === 'email-de') { ev.preventDefault(); emailDeAdicionar(); }
  if (ev.key === 'Enter' && ev.target.matches && ev.target.matches('#per-atras, #per-frente, #hz-anos')) { ev.preventDefault(); const ok = $('.folha-pe .btn.pri'); if (ok) ok.click(); }
});
document.addEventListener('change', ev => {
  const el = ev.target;
  if (el.dataset.bensTaxa) {
    // a % vai com o Perde ou Valoriza escolhido ao lado; digitar um número negativo também vira Valoriza
    const k = el.dataset.bensTaxa, n = Number(String(el.value).replace(',', '.').replace('−', '-')) || 0;
    const val = el.closest('.bens-tx')?.querySelector('[data-a="bens-dir"][data-v="-1"]')?.classList.contains('on');
    salvarTaxaBem(k, n < 0 ? n : val ? -n : n);
    return;
  }
  if (el.dataset.ajusteSel) {
    const k = el.dataset.ajusteSel, v = el.value, fala = k === 'voz_motor';
    persistir(d => { d.ajustes[k] = v; }, fala ? 'Fala para texto escolhida' : 'IA escolhida').then(() => { if (fala) carregarVoz(); else S.ia = null; render(); });
  }
});
// a % por ano de uma categoria de bens (negativa: valoriza, como um imóvel); vale também para os bens cadastrados aqui
function salvarTaxaBem(k, v) {
  v = Math.max(-50, Math.min(100, Math.round((+v || 0) * 100) / 100));
  persistir(d => {
    d.ajustes.bens_taxas = Object.assign({}, d.ajustes.bens_taxas, { [k]: v });
    for (const i of d.investimentos) {
      if (i.tipo !== 'bens') continue;
      if (i.partes && i.partes.length) { let mud = false; for (const p of i.partes) if (p.categoria === k) { p.taxa = v; mud = true; } if (mud) i.taxa = taxaPartes(i.partes); }
      else if ((i.categoria_bem || 'outros') === k) i.taxa = v;
    }
  }, v < 0 ? `Valoriza ${pct(-v)}% por ano` : v > 0 ? `Perde ${pct(v)}% por ano` : 'Mantém o valor').then(ok => { if (ok) { carregarBens(); render(); } });
}
let pfT;
function pintarFolhaDepois() {
  clearTimeout(pfT);
  pfT = setTimeout(() => {
    const ativo = document.activeElement, sel = ativo && ativo.dataset && (ativo.dataset.lf ? `[data-lf="${ativo.dataset.lf}"]` : null);
    const pos = ativo && ativo.selectionStart;
    pintarFolha();
    if (sel) { const e = $(sel); if (e) { e.focus(); try { e.setSelectionRange(pos, pos); } catch (x) { /* ok */ } } }
  }, 450);
}

$('#arquivo').addEventListener('change', ev => {
  const f = ev.target.files && ev.target.files[0];
  ev.target.value = '';
  if (!f) return;
  confirmar({
    titulo: 'Importar arquivo?', texto: `Os dados de agora são trocados pelos de <b>${esc(f.name)}</b>. Antes, o app guarda uma cópia do que existe hoje.`, botao: 'Importar',
    acao: () => api.importar(f).then(d => { S.d = normalizar(d); irPara('inicio'); toast('Dados importados'); }).catch(e => toast('Não consegui importar. ' + e.message)),
  });
});

document.addEventListener('visibilitychange', () => {
  if (!document.hidden && !FOLHA && !DEMO) api.state().then(d => { S.d = normalizar(d); render(); }).catch(() => {});
});
let rz;
window.addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { desenharGraficos(); ajustarTextos(); }, 150); });

/* ------------------------------------------------------------------ outros apps */
/* --------- bens da casa, do InventarIA: somam no patrimônio e perdem valor por categoria */
const bensOn = () => S.d.ajustes.bens !== false && !!(S.bens && S.bens.ok && S.bens.n);
function carregarBens(forcar) {
  if (S.d.ajustes.bens === false) { S.bens = null; return; }
  (forcar ? api.bensAtualizar() : api.bens()).then(r => { S.bens = r; if (!FOLHA || FOLHA.montar === montarBens) { if (FOLHA) pintarFolha(); render(); } })
    .catch(e => { S.bens = { ok: false, motivo: e.message }; });
}
function cardBens(a) {
  const b = S.bens, on = a.bens !== false;
  let h = `<section class="card" id="bens">${maisCab('sofa', 'Bens no InventarIA')}
    ${maisLead('Os valores dos itens do InventarIA, somados no patrimônio.')}
    ${linhaChave('bens', on, 'Somar os bens', on ? (b && b.ok ? `Ligado: ${brl(b.hoje, 0)} em ${plural(b.n, 'item', 'itens')}.` : 'Ligado.') : 'Desligado: o patrimônio fica só com os investimentos.')}`;
  if (!on) return h + '</section>';
  if (!b) return h + `<div class="status manual">Procurando o InventarIA…</div></section>`;
  if (!b.ok) return h + `<div class="status manual">${esc(b.motivo || 'O InventarIA não respondeu.')}</div>
    <button class="btn out" data-a="bens-atualizar">${ic('refresh')}Tentar de novo</button></section>`;
  // sem itens com valor no InventarIA, Mais › Invest não tem as categorias dele
  h += `${bensOn() ? '<p class="nota" style="margin:0 0 12px">Quanto cada categoria perde ou valoriza por ano fica em Mais › Invest.</p>' : ''}
    <button class="btn out" data-a="bens-atualizar">${ic('refresh')}Atualizar do InventarIA</button></section>`;
  return h;
}
function montarBens() {
  const b = S.bens;
  if (!b || !b.ok) return { titulo: 'Bens da casa', corpo: `<div class="status manual">${esc((b && b.motivo) || 'Procurando o InventarIA…')}</div>` };
  const linha = (n, sub, v) => `<div class="bens-l"><span><b>${esc(n)}</b><small>${sub}</small></span><b>${brl(v, 0)}</b></div>`;
  return {
    titulo: 'Bens da casa',
    corpo: `<div class="stat-duo" style="margin:0 0 14px"><div><span>Hoje</span><b>${brl(b.hoje, 0)}</b><small>registrado ${brl(b.registrado, 0)}</small></div>
        <div><span>${b.perde_ano < 0 ? 'Valorizam por ano' : 'Perdem por ano'}</span><b>${brl(Math.abs(b.perde_ano), 0)}</b></div></div>
      <div class="bens-evo">${[1, 5, 10].map(a => `<div><span>Em ${a === 1 ? '1 ano' : a + ' anos'}</span><b>${brl(bensEm(a * 12), 0)}</b></div>`).join('')}</div>
      <button class="link" data-a="bens-evolucao" style="margin:0 0 6px">${ic('chart', 'ic-s')}Ver na Evolução</button>
      <h3 class="ia-sec">Por categoria</h3>${b.categorias.map(c => linha(c.nome, `${plural(c.n, 'item', 'itens')} · ${c.taxa > 0 ? `−${pct(c.taxa)}% ao ano` : c.taxa < 0 ? `+${pct(-c.taxa)}% ao ano` : 'mantém o valor'}`, c.hoje)).join('')}
      <h3 class="ia-sec">Por cômodo</h3>${b.comodos.map(c => linha(c.nome, plural(c.n, 'item', 'itens'), c.hoje)).join('')}
      <p class="nota">Pelo valor de cada item no InventarIA, com o que a categoria perde ou valoriza por ano desde a data desse valor. As taxas ficam em Mais › Invest.</p>`,
    pe: `<button class="btn" data-a="fechar">Fechar</button><button class="btn pri" data-a="bens-atualizar">${ic('refresh', 'ic-s')}Atualizar</button>`,
  };
}
// prévia: bens inventados (nenhum dado real)
function bensDemo() {
  const cats = [['eletronicos', 'Eletrônicos', 20, 14200, 6], ['moveis', 'Móveis', 10, 18600, 9], ['cozinha', 'Cozinha e bar', 10, 5400, 12], ['decoracao', 'Decoração e arte', 5, 3900, 7]];
  const tx = S.d.ajustes.bens_taxas || {};
  const categorias = cats.map(([id, nome, t, v, n]) => { const taxa = tx[id] != null ? +tx[id] : t; return { id, nome, taxa, registrado: v, hoje: round2(v * Math.pow(1 - taxa / 100, 1.4)), n }; });
  const hojeT = categorias.reduce((a, c) => a + c.hoje, 0);
  return { ok: true, hoje: round2(hojeT), registrado: cats.reduce((a, c) => a + c[3], 0), perde_ano: round2(categorias.reduce((a, c) => a + c.hoje * c.taxa / 100, 0)), n: cats.reduce((a, c) => a + c[4], 0),
    categorias, comodos: [{ id: 'sala', nome: 'Sala', hoje: round2(hojeT * 0.45), n: 14 }, { id: 'cozinha', nome: 'Cozinha', hoje: round2(hojeT * 0.25), n: 12 }, { id: 'quarto', nome: 'Quarto', hoje: round2(hojeT * 0.3), n: 8 }], versao: '1.16.0' };
}

function cardOutrosApps(a) {
  const lig = a.integracao !== false, u = S.integracaoUltimo;
  let quando = '';
  if (u && u.em) {
    const dt = new Date(u.em), hj = iso(hoje()) === iso(dt);
    quando = `${esc(u.app)} usou ${hj ? 'hoje' : 'em ' + fData(dt)} às ${dt.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}.`;
  }
  return `<section class="card" id="outros-apps">${maisCab('calendar', 'Contas no CronologIA')}
    ${maisLead('O CronologIA mostra as contas a pagar e as faturas na agenda e dá baixa com o Paguei.')}
    ${linhaChave('integracao', lig, 'Usar a integração', lig ? 'Ligado: o CronologIA lê e dá baixa nas contas daqui.' : 'Desligado: o CronologIA não vê as contas do GerencIA.')}
    ${lig ? `<div class="status${quando ? '' : ' manual'}">${quando || 'Nenhum app conectou ainda.'}</div>` : ''}</section>`;
}
// Mudanças feitas por outro app (Paguei no CronologIA) aparecem sem precisar recarregar.
if (!DEMO) setInterval(() => {
  if (document.hidden || FOLHA || !S.d) return;
  fetch('api/rev', { cache: 'no-store' }).then(jsonOk).then(r => {
    S.integracaoUltimo = r.integracao_ultimo || null;
    if (emailOn() && r.emails !== S.emailsCarimbo) { S.emailsCarimbo = r.emails; carregarEmails(); }  // chegou ou mudou e-mail
    if (r.rev !== S.d.rev && !FOLHA) return api.state().then(d => { S.d = normalizar(d); render(); });
  }).catch(() => {});
}, 20000);

/* ------------------------------------------------------------------ início */
async function iniciar() {
  pintarNav();
  try {
    const st = await api.state();
    S.usuario = st.usuario || null;
    S.integracaoUltimo = st.integracao_ultimo || null;
    S.d = normalizar(st);
  } catch (e) {
    $('#app').innerHTML = `<div class="vazio">Não consegui abrir os dados.<br>${esc(e.message)}<br><br><button class="btn" onclick="location.reload()">Tentar de novo</button></div>`;
    return;
  }
  if (S.ui.tab === 'graficos') { S.ui.tab = 'investimentos'; S.ui.invModo = 'evolucao'; }
  if (!['inicio', 'caixa', 'investimentos', 'mais'].includes(S.ui.tab)) S.ui.tab = 'inicio';
  if (!['carteira', 'evolucao', 'divisao'].includes(S.ui.invModo)) S.ui.invModo = 'carteira';
  S.ui.cxMes = null; S.ui.faturaAberta = null; S.ui.cxSel = null;
  S.ui.busca = ''; S.ui.buscaAberta = false; S.ui.gSel = null;
  render();
  carregarDicas();
  carregarVoz();
  carregarBens();
  carregarEmails();
}
// Só nos testes (tests/test_tela*.py abrem a página com window.GERENCIA_TESTE = true): qualquer função ou variável
// daqui de dentro pelo nome (GERENCIA_TESTE.totais, GERENCIA_TESTE.S, GERENCIA_TESTE.IAS = ...). No app, nada disso existe.
if (window.GERENCIA_TESTE === true) {
  const ler = nome => { try { return eval(nome); } catch (e) { return undefined; } }; // eslint-disable-line no-eval
  window.GERENCIA_TESTE = new Proxy({}, {
    get: (_, k) => typeof k === 'string' && /^[A-Za-z_$][\w$]*$/.test(k) && k !== 'then' ? ler(k) : undefined,
    set: (_, k, v) => { if (/^[A-Za-z_$][\w$]*$/.test(k)) eval(`${k} = v`); return true; }, // eslint-disable-line no-eval
  });
}
iniciar();
})();
