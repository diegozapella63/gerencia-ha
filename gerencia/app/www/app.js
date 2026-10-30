/* GerencIA · controle de investimentos dentro do Home Assistant */
(() => {
'use strict';

const DEMO = !!window.GERENCIA_DEMO;
const VERSAO = '1.15.0';

const PALETA = ['#FF5A4E', '#FF8A65', '#FF77A8', '#E04B8A', '#FFA23A', '#F2C14E', '#B79BFF', '#56AEFF', '#4CD3A5', '#B8B0B0'];
// ordem para sugerir cor a um banco novo
const CORES_BANCO = ['#56AEFF', '#B79BFF', '#4CD3A5', '#FFA23A', '#FF77A8', '#F2C14E', '#FF8A65', '#E04B8A', '#FF5A4E', '#B8B0B0'];
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
];

const INDICES_PADRAO = { cdi: 13.65, selic: 13.75, ipca: 4.58, tr: 0.17, auto: true, fonte: 'padrao', atualizado_em: null, datas: {}, erro: null };
const AJUSTES_PADRAO = { tema: 'auto', cor: '#56AEFF', corrigir: true, sensores: false, sensores_v: 2, ia_entidade: '', dicas_fora: [], integracao: true, ia: true, dicas: true, prever_dia: true };

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
  alert: '<path d="M12 4 2.5 20h19L12 4Z"/><path d="M12 10v4M12 17h.01"/>',
  trend: '<path d="m3 17 6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
  calendar: '<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
  percent: '<path d="M19 5 5 19"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
  edit: '<path d="M4 20h4L19 9l-4-4L4 16v4Z"/>',
  fluxo: '<path d="M7 20V5M3 9l4-4 4 4"/><path d="M17 4v15M13 15l4 4 4-4"/>',
  card: '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M3 10h18M7 15h4"/>',
  camera: '<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
  ia: '<path d="M12 3l1.8 4.7 4.7 1.8-4.7 1.8L12 16l-1.8-4.7-4.7-1.8 4.7-1.8z"/><path d="M19 15l.8 2.2 2.2.8-2.2.8L19 21l-.8-2.2-2.2-.8 2.2-.8z"/>',
  repeat: '<path d="M17 2l3 3-3 3"/><path d="M4 11V9a4 4 0 0 1 4-4h12"/><path d="M7 22l-3-3 3-3"/><path d="M20 13v2a4 4 0 0 1-4 4H4"/>',
  minus: '<path d="M5 12h14"/>',
  chevL: '<path d="m15 6-6 6 6 6"/>',
};
const ic = (n, c = 'ic') => `<svg class="${c}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[n] || ''}</svg>`;

/* ------------------------------------------------------------------ estado */
const S = {
  d: null,
  usuario: null,
  oculto: store.get('oculto', false),
  ui: Object.assign({
    tab: 'inicio', filtro: 'todos', pessoa: null, banco: null, busca: '', buscaAberta: false,
    invModo: 'carteira', gEscopo: 'tudo', gAnos: 5, gIR: false, gAgrup: 'banco', gSel: null,
    cxModo: 'lista', cxMes: null, cxFiltro: 'tudo', cxPeriodo: 'meio', cxCatTipo: 'despesa', cxSel: null, faturaAberta: null, maisAba: 'bancos',
  }, store.get('ui', {})),
  ia: null,
  dicas: null,
};
const salvarUI = () => {
  const { tab, filtro, invModo, gEscopo, gAnos, gIR, gAgrup, cxModo, cxFiltro, cxPeriodo, cxCatTipo, maisAba } = S.ui;
  store.set('ui', { tab, filtro, invModo, gEscopo, gAnos, gIR, gAgrup, cxModo, cxFiltro, cxPeriodo, cxCatTipo, maisAba });
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
    default: return 0;
  }
}
const corrige = inv => !['estimado', 'parado'].includes(inv.indexador);
function valorHoje(inv, h = hoje(), d = S.d) {
  const v = +inv.valor || 0;
  if (d.ajustes.corrigir === false || !corrige(inv)) return v;
  const d0 = pData(inv.data_valor) || h;
  return v * Math.pow(1 + taxaAnual(inv, d.indices), diasUteis(d0, h) / 252);
}
const rendeMes = (v, r) => v * (Math.pow(1 + r, 1 / 12) - 1);
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
  const base = lista.map(i => ({
    v: valorHoje(i, h), r: taxaAnual(i), ir: tipoDe(i.tipo).ir,
    idade: Math.max(0, diasEntre(pData(i.data_valor) || h, h)),
  }));
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
    b('b-nu', 'Nubank', '#B79BFF'), b('b-inter', 'Inter', '#FFA23A'), b('b-itau', 'Itaú', '#FF8A65'),
    b('b-xp', 'XP', '#B8B0B0'), b('b-caixa', 'Caixa', '#56AEFF'), b('b-sicredi', 'Sicredi', '#4CD3A5'),
  ];
  const inv = (o) => Object.assign({ id: uid(), obs: '', vencimento: null, terceiro: '', titular: 'meu', criado_em: dia(200) }, o);
  const investimentos = [
    inv({ nome: 'Reserva de emergência', banco: 'b-nu', tipo: 'caixinha', valor: 24380.52, data_valor: dia(17), indexador: 'cdi_pct', taxa: 100, liquidez: 'diaria' }),
    inv({ nome: 'CDB Inter 2028', banco: 'b-inter', tipo: 'cdb', valor: 15000, data_valor: dia(46), indexador: 'cdi_pct', taxa: 112, liquidez: 'vencimento', vencimento: futuro(17, 13) }),
    inv({ nome: 'LCI Itaú', banco: 'b-itau', tipo: 'lci', valor: 20000, data_valor: dia(95), indexador: 'cdi_pct', taxa: 94, liquidez: 'vencimento', vencimento: iso(new Date(h.getTime() + 24 * 86400000)) }),
    inv({ nome: 'Tesouro IPCA+ 2035', banco: 'b-xp', tipo: 'tesouro', valor: 18640.1, data_valor: dia(30), indexador: 'ipca_mais', taxa: 7.1, liquidez: 'vencimento', vencimento: '2035-05-15' }),
    inv({ nome: 'Tesouro Selic 2029', banco: 'b-xp', tipo: 'tesouro', valor: 8200, data_valor: dia(30), indexador: 'selic_mais', taxa: 0.05, liquidez: 'diaria', vencimento: '2029-03-01' }),
    inv({ nome: 'Ações e FIIs', banco: 'b-xp', tipo: 'acoes', valor: 12450, data_valor: dia(9), indexador: 'estimado', taxa: 10, liquidez: 'diaria' }),
    inv({ nome: 'Poupança da mãe', banco: 'b-caixa', tipo: 'poupanca', valor: 9870.35, data_valor: dia(18), indexador: 'poupanca', taxa: 0, liquidez: 'diaria', titular: 'terceiros', terceiro: 'Mãe' }),
    inv({ nome: 'CDB do Pedro', banco: 'b-sicredi', tipo: 'cdb', valor: 5300, data_valor: dia(73), indexador: 'cdi_pct', taxa: 105, liquidez: 'vencimento', vencimento: futuro(26, 2), titular: 'terceiros', terceiro: 'Pedro' }),
    inv({ nome: 'Vaquinha da viagem', banco: 'b-nu', tipo: 'caixinha', valor: 2150, data_valor: dia(5), indexador: 'cdi_pct', taxa: 100, liquidez: 'diaria', titular: 'terceiros', terceiro: 'Família' }),
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
  let msg = `Erro ${r.status}`;
  try { const j = await r.json(); msg = j.erro || msg; } catch (e) { /* sem corpo */ }
  throw new Error(msg);
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
  iaUso: () => fetch('api/ia/uso', { cache: 'no-store' }).then(jsonOk),
  vozStatus: () => fetch('api/voz/status', { cache: 'no-store' }).then(jsonOk),
  vozTexto: pcm => fetch('api/voz', { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: pcm }).then(jsonOk),
  backups: () => fetch('api/backups', { cache: 'no-store' }).then(jsonOk),
  restaurarBackup: nome => fetch('api/backups/restaurar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nome }) }).then(jsonOk),
  dicasConferir: () => fetch('api/dicas/conferir', { method: 'POST' }).then(jsonOk),
};
function apiDemo() {
  let d = null;
  const espera = ms => new Promise(r => setTimeout(r, ms));
  return {
    async state() { d = d || gerarExemplo(); return Object.assign(clone(d), { usuario: 'Diego' }); },
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
    async vozStatus() { return { pronta: true, nome: 'Home Assistant Cloud' }; },
    async vozTexto() { await espera(900); return { texto: 'Gastei 45 reais no mercado hoje no cartão do Nubank e recebi 150 do João pelo Pix', nome: 'Home Assistant Cloud' }; },
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
      const hj = iso(hoje()), ont = iso(new Date(hoje().getTime() - 86400000));
      const t = (c.texto || '').toLowerCase();
      // na prévia, a IA "lê" pelo texto: palavras de investimento trazem investimentos, de gasto trazem lançamentos
      let inv = /cdb|tesouro|\blc[ia]\b|invest|apliquei|aplica[çc]|% do cdi|caixinha|rende/.test(t), cx = /gast|receb|pagu|pagar|compr|fatura|pix|mercado|boleto|conta de|sal[áa]rio/.test(t);
      if (!inv && !cx) { inv = c.dica === 'invest'; cx = !inv; }
      const lanc = !cx ? [] : /mercado/.test(t) && /jo[aã]o/.test(t) ? [
        { tipo: 'despesa', descricao: 'Mercado', valor: 45, data: hj, categoria: 'c-mercado', parcela_atual: 0, parcelas_total: 0, cartao: true, banco: 'Nubank', situacao: 'feito', confianca: 'alta' },
        { tipo: 'receita', descricao: 'Pix do João', valor: 150, data: hj, categoria: 'c-reembolso', parcela_atual: 0, parcelas_total: 0, cartao: false, banco: '', situacao: 'feito', confianca: 'alta' },
      ] : [
        { tipo: 'despesa', descricao: 'iFood', valor: 64.9, data: ont, categoria: 'c-restaurantes', parcela_atual: 0, parcelas_total: 0, cartao: true, banco: 'Nubank', situacao: 'feito', confianca: 'alta' },
        { tipo: 'despesa', descricao: 'Posto Shell', valor: 210, data: ont, categoria: 'c-transporte', parcela_atual: 0, parcelas_total: 0, cartao: true, banco: 'Nubank', situacao: 'feito', confianca: 'alta' },
        { tipo: 'despesa', descricao: 'Magazine Luiza', valor: 189.9, data: iso(addMeses(hoje(), -1)), categoria: 'c-compras', parcela_atual: 2, parcelas_total: 6, cartao: true, banco: 'Nubank', situacao: '', confianca: 'media' },
        { tipo: 'despesa', descricao: 'IPVA', valor: 1480, data: iso(addMeses(hoje(), 1)), categoria: 'c-impostos', parcela_atual: 0, parcelas_total: 0, cartao: false, banco: '', situacao: 'pendente', confianca: 'alta' },
        { tipo: 'receita', descricao: 'Pix do João', valor: 150, data: hj, categoria: 'c-reembolso', parcela_atual: 0, parcelas_total: 0, cartao: false, banco: '', situacao: 'feito', confianca: 'alta' },
      ];
      const cdb = d.investimentos.find(i => i.tipo === 'cdb');
      const invs = !inv ? [] : [
        { nome: 'CDB Inter 2028', banco: 'Inter', tipo: 'cdb', valor: 15412.37, aplicado: 15000, data_valor: hj, indexador: 'cdi_pct', taxa: 112, vencimento: '2028-03-13', liquidez: 'vencimento', existente: cdb ? cdb.id : '', confianca: 'alta' },
        { nome: 'LCA Banco do Brasil 2027', banco: 'Banco do Brasil', tipo: 'lci', valor: 10250, aplicado: 10000, data_valor: hj, indexador: 'cdi_pct', taxa: 93, vencimento: '2027-09-20', liquidez: 'vencimento', existente: '', confianca: 'media' },
      ];
      if (c.modo === 'invest') return { itens: invs.length ? invs : [{ nome: 'CDB Inter 2028', banco: 'Inter', tipo: 'cdb', valor: 15412.37, aplicado: 15000, data_valor: hj, indexador: 'cdi_pct', taxa: 112, vencimento: '2028-03-13', liquidez: 'vencimento', existente: cdb ? cdb.id : '', confianca: 'alta' }], entidade: 'simulada' };
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
  const cor = corOk(a.cor) || AJUSTES_PADRAO.cor;
  root.style.setProperty('--accent', cor);
  root.dataset.ia = a.ia === false ? 'off' : 'on';
  const meta = $('meta[name="theme-color"]');
  if (meta) meta.content = getComputedStyle(root).getPropertyValue('--bg').trim() || '#0f1318';
}
if (!DEMO) setInterval(() => { if (S.d && S.d.ajustes.tema === 'auto') aplicarTema(); }, 2000);
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
  return ['manual', DEMO ? 'Exemplo com os índices de outubro de 2026' : 'Esperando os índices do Banco Central'];
}
// O ícone do app ao lado do nome (no alto e na barra lateral), na cor escolhida em Aparência, como no ResolvIA e no CronologIA:
// as duas plaquinhas "R$" do placar.
const iconeApp = () => `<svg class="app-ic" viewBox="0 0 32 32" aria-hidden="true">
  <rect x="2" y="5" width="13.2" height="22" rx="3.2" fill="var(--accent)"/><rect x="16.8" y="5" width="13.2" height="22" rx="3.2" fill="var(--accent)"/>
  <rect x="2" y="5" width="28" height="11" rx="3.2" fill="#fff" fill-opacity=".16"/>
  <path d="M2 16h2.4M12.8 16h2.4M16.8 16h2.4M27.6 16h2.4" stroke="var(--bg)" stroke-width="1.6"/>
  <text x="8.6" y="23.2" text-anchor="middle" font-family="Barlow Condensed, Arial Narrow, sans-serif" font-weight="700" font-size="18.5" fill="var(--on-accent)">R</text>
  <text x="23.4" y="23.2" text-anchor="middle" font-family="Barlow Condensed, Arial Narrow, sans-serif" font-weight="700" font-size="18.5" fill="var(--on-accent)">$</text></svg>`;
function cabecalho(titulo, acoes = '', status = null) {
  const [cls, txt] = status || syncInfo();
  return `<header class="cab"><div class="cab-topo"><p class="eyebrow"><span class="brand">${iconeApp()}Gerenc<span>IA</span></span>${S.usuario ? `<span class="eb-sep"> · </span>Olá, ${esc(S.usuario.split(' ')[0])}` : ''}</p>${botaoFalar()}</div>
    <div class="cab-linha"><h1>${titulo}</h1>${acoes}</div>${acoesTopo(acoes)}</header>
    <p class="sync ${cls}"><span class="dot" aria-hidden="true"></span><span>${txt}</span></p>`;
}

// No computador, as ações ficam no alto à direita, como no ResolvIA e no CronologIA: Falar, esconder valores, Ler com IA e Adicionar.
function acoesTopo(acoes) {
  const olho = /data-a="olho"/.test(acoes)
    ? `<button class="icbtn" data-a="olho" aria-label="${S.oculto ? 'Mostrar' : 'Esconder'} valores" title="${S.oculto ? 'Mostrar' : 'Esconder'} valores">${ic(S.oculto ? 'eyeOff' : 'eye')}</button>` : '';
  const v = S.ui.tab === 'investimentos' ? 'invest' : 'caixa';
  return `<div class="top-acts">${botaoFalar()}${olho}<button class="btn" data-a="ia" data-v="${v}">${ic('ia', 'ic-s')}Ler com IA</button>
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
  const nBancos = new Set(d.investimentos.map(i => i.banco).filter(Boolean)).size;
  const olho = `<button class="icbtn" data-a="olho" aria-label="${S.oculto ? 'Mostrar' : 'Esconder'} valores">${ic(S.oculto ? 'eyeOff' : 'eye')}</button>`;
  let html = cabecalho('Início', olho);
  if (d.exemplo) html += avisoExemplo();
  if (!d.investimentos.length) {
    const r = resumoMes(ymHoje());
    html += placar({ cab: 'Saldo em caixa', data: fData(h), valor: numf(saldoCaixa(), 0), rotulo: `Saldo em caixa de ${brl(saldoCaixa(), 0)}`,
      cols: [['Entrou', brl(r.entrou, 0), 'ent'], ['Saiu', brl(r.saiu, 0), 'sai'], ['Sobrou', brl(r.sobra, 0), true]] });
    return html.replace('<section class="placar', '<div class="ini-g so-caixa"><section class="placar') + `<div class="ini-ga">${cardDicas()}</div><div class="ini-gb">${avisosInicio(h)}</div></div>`;
  }

  html += '<div class="ini-g">' + placar({
    cab: 'Patrimônio', data: fData(h), valor: numf(t.total, 0), rotulo: `Patrimônio de ${brl(t.total, 0)}`,
    cols: [
      ['Seu', brl(t.meu, 0), 'meu'],
      t.terc > 0 ? ['Terceiros', brl(t.terc, 0), 'terc'] : ['Bancos', String(nBancos)],
      ['Por mês', (S.oculto ? '' : '+') + brl(t.mes, 0), true],
    ],
  });

  html += `<div class="ini-ga">${temCaixa() ? cardCaixaInicio() + cardDicas() : ''}</div>`;
  // destaques
  const rows = [];
  rows.push(`<button class="hl-row" data-a="inv-modo" data-v="evolucao"><div><div class="hl-k">Rende por mês</div>
    <div class="hl-v">Média de ${pct(t.rMed * 100)}% a.a.</div></div><div class="hl-n">${brl(t.mes, 0)}<small>antes do IR</small></div></button>`);
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
  const pb = {};
  for (const i of d.investimentos) pb[i.banco || ''] = (pb[i.banco || ''] || 0) + valorHoje(i);
  const [bId, bVal] = Object.entries(pb).sort((a, b) => b[1] - a[1])[0] || [];
  if (bVal) {
    rows.push(`<button class="hl-row" data-a="graf-comp" data-v="banco"><div><div class="hl-k">Maior banco</div>
      <div class="hl-v">${esc(bancoDe(bId)?.nome || 'Sem banco')}</div></div><div class="hl-n">${pct(Math.round(bVal / t.total * 100))}%<small>${brl(bVal, 0)}</small></div></button>`);
  }
  const meus = porEscopo('meu');
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
  const av = [];
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
    <p>Comece pelo que entra e sai todo mês e pelos seus investimentos. Já tem um backup? Importe o arquivo .zip e tudo volta.</p>
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
  if (u.banco) l = l.filter(i => (i.banco || '') === u.banco);
  const q = u.busca.trim().toLowerCase();
  if (q) l = l.filter(i => [i.nome, bancoDe(i.banco)?.nome, tipoDe(i.tipo).nome, dono(i), i.obs].join(' ').toLowerCase().includes(q));
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
  let html = cabecalho('Investimentos');
  html += `<div class="seg">${[['carteira', 'Carteira'], ['evolucao', 'Evolução'], ['divisao', 'Divisão']].map(([k, n]) =>
    `<button class="${u.invModo === k ? 'on' : ''}" data-a="inv-modo" data-v="${k}">${n}</button>`).join('')}</div>`;
  if (u.invModo !== 'carteira') return html + invGraficos();
  // Buscar sempre à mostra, como no ResolvIA; no computador, a tecla / põe o cursor nele
  html += `<div class="inv-filtros"><div class="busca">${ic('search', 'ic-s')}<input id="q" type="search" data-ui="busca" value="${esc(u.busca)}" placeholder="Buscar por nome, banco ou pessoa" autocomplete="off" enterkeyhint="search" aria-label="Buscar investimentos">
    ${u.busca ? `<button class="icbtn mini" data-a="busca-limpar" aria-label="Limpar busca">${ic('x', 'ic-s')}</button>` : '<kbd aria-hidden="true">/</kbd>'}</div>`;
  html += `<div class="seg">
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
      ${usados.map(id => { const b = bancoDe(id); return `<button class="chip${u.banco === id ? ' on' : ''}" data-a="banco-f" data-v="${esc(id)}" style="--c:${corOk(b?.cor) || 'var(--c0)'}"><span class="bol"></span>${esc(b?.nome || 'Sem banco')}</button>`; }).join('')}</div>`;
  }
  const l = listaFiltrada();
  const soma = l.reduce((s, x) => s + x.v, 0);
  const mes = l.reduce((s, x) => s + rendeMes(x.v, taxaAnual(x.i)), 0);
  html += `<div class="resumo-lista"><span>${plural(l.length, 'investimento', 'investimentos')} · rende ≈ ${brl(mes, 0)}/mês</span><b>${brl(soma, 0)}</b></div>`;
  html += l.length ? `<div class="inv-lista">${l.map(x => cardInv(x.i, x.v)).join('')}</div>` : '<div class="vazio">Nenhum investimento com esse filtro.</div>';
  return html;
}

function cardInv(i, v) {
  const h = hoje();
  const b = bancoDe(i.banco);
  const venc = pData(i.vencimento);
  const dv = pData(i.data_valor);
  let liq;
  if (venc && venc < h) liq = `<span class="tag alerta">${ic('alert')}Venceu ${fData(venc)}</span>`;
  else if (i.liquidez === 'diaria') liq = `<span class="tag">Liquidez diária</span>`;
  else liq = `<span class="tag">${ic('calendar')}${venc ? 'Vence ' + fData(venc) : 'No vencimento'}</span>`;
  const r = taxaAnual(i);
  const velho = dv && diasEntre(dv, h) > 60 && i.indexador !== 'parado';
  return `<button class="inv" data-a="inv" data-id="${i.id}" style="--c:${corOk(b?.cor) || 'var(--line-2)'}">
    <div class="inv-top"><div class="inv-nome">${esc(i.nome)}</div><div class="inv-valor">${brl(v)}</div></div>
    <div class="inv-meta"><i></i>${esc(b?.nome || 'Sem banco')} · ${esc(tipoDe(i.tipo).nome)}</div>
    <div class="tags"><span class="tag taxa">${esc(rotuloTaxa(i))}</span>${tagDono(i)}${liq}</div>
    <div class="inv-pe"><span>${r > 0 ? `≈ ${brl(rendeMes(v, r))} por mês` : 'Não rende'}</span>
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
  const lista = porEscopo(u.gEscopo);
  if (!lista.length) return html + '<div class="vazio">Nada nesse filtro.</div>';
  return html + (u.invModo === 'divisao' ? grafComposicao(lista) : grafEvolucao(lista));
}

let CACHE = {};
function grafEvolucao(lista) {
  const u = S.ui;
  const ap = u.gEscopo === 'terc' ? 0 : aporteMensal();
  const pj = projetar(lista, u.gAnos, ap, u.gIR);
  CACHE.proj = pj;
  const fim = pj.pts[pj.pts.length - 1];
  const campo = u.gEscopo === 'meu' ? 'meu' : u.gEscopo === 'terc' ? 'terceiros' : 'total';
  CACHE.hist = S.d.historico.filter(h => h.d < iso(hoje())).map(h => ({ t: pData(h.d).getTime(), v: +h[campo] || 0 }));
  const anosTxt = u.gAnos === 1 ? '1 ano' : `${u.gAnos} anos`;
  let html = `<div class="graf-card">
    <div class="stat-duo"><div><span>Hoje</span><b>${brl(pj.pts[0].valor, 0)}</b></div>
      <div><span>Em ${anosTxt}${u.gIR ? ', líquido' : ''}</span><b>${brl(fim.valor, 0)}</b><small>+${brl(fim.valor - fim.aplicado, 0)} de rendimento</small></div></div>
    <div class="chart" id="ch-evo" role="img" aria-label="Evolução do dinheiro: registrado até hoje e projetado para ${anosTxt}"></div>
    <div class="leg">
      ${CACHE.hist.length ? `<span><i class="k" style="--kc:var(--accent)"></i>Registrado</span>` : ''}
      <span><i class="k tr" style="--kc:var(--accent)"></i>Projetado</span>
      <span><i class="k" style="--kc:var(--c0)"></i>${ap ? 'Investido + aportes' : 'Valor investido'}</span>
      <span><i class="k" style="--kc:var(--c2)"></i>Em dinheiro de hoje</span>
    </div></div>`;
  html += `<div class="ctrl"><div class="lbl">Horizonte</div><div class="chips c4">${[1, 2, 5, 10].map(a =>
    `<button class="chip${u.gAnos === a ? ' on' : ''}" data-a="g" data-k="gAnos" data-v="${a}">${a === 1 ? '1 ano' : a + ' anos'}</button>`).join('')}</div>
    ${u.gEscopo === 'terc' ? `<div class="lbl">Aporte por mês</div><p class="ajuda" style="margin:0">Os aportes entram só nos seus investimentos. Veja em Tudo ou Só o meu.</p>` : aporteInfo(ap)}
    <div class="sep" style="margin:18px 0"></div>
    <div class="linha-sw"><div><b>Descontar imposto de renda</b><span>Tabela regressiva na renda fixa e 15% em ações. LCI, LCA e poupança são isentas.</span></div>
      <button class="sw${u.gIR ? ' on' : ''}" data-a="g" data-k="gIR" data-v="${u.gIR ? '' : '1'}" aria-label="Descontar IR"></button></div>
  </div>
  <p class="nota">A projeção usa os índices de hoje (CDI ${pct(S.d.indices.cdi)}%, IPCA ${pct(S.d.indices.ipca)}%) mantidos no período, com rendimento médio de ${pct(pj.rMed * 100)}% a.a. "Em dinheiro de hoje" desconta a inflação. É uma estimativa, não uma promessa.</p>
  <details class="card" style="margin-top:16px"><summary style="cursor:pointer;font-weight:600">Ver tabela por ano</summary>
  <table class="tabela"><thead><tr><th>Quando</th><th class="n">Projetado</th><th class="n">Rendeu</th><th class="n">Em dinheiro de hoje</th></tr></thead><tbody>
  ${Array.from({ length: u.gAnos }, (_, k) => pj.pts[(k + 1) * 12]).map(p =>
    `<tr><td>${fMesAno(new Date(p.t))}</td><td class="n">${brl(p.valor, 0)}</td><td class="n">${brl(p.valor - p.aplicado, 0)}</td><td class="n">${brl(p.real, 0)}</td></tr>`).join('')}
  </tbody></table></details>`;
  return html;
}

// O aporte por mês não se digita aqui: vem das contas a pagar do tipo Aporte (o compromisso de aplicar).
function aporteInfo(ap) {
  const fx = aportesFixos();
  if (!fx.length) {
    return `<div class="lbl">Aporte por mês nos seus investimentos</div>
      <p class="ajuda" style="margin:0 0 10px">Nenhum. Para a projeção contar com um aporte, cadastre o compromisso no Caixa: uma conta a pagar do tipo <b>Aporte</b>, todo mês.</p>
      <button class="btn out peq" data-a="aporte-novo">${ic('plus', 'ic-s')}Cadastrar aporte</button>`;
  }
  const r = fx[0], conta = r.conta ? contaDe(r.conta) : null;
  const quando = fx.length > 1 ? `${fx.length} aportes fixos nas contas a pagar` : `${r.freq === 'anual' ? `todo ano em ${MESES_LONGOS[+String(r.inicio).slice(5, 7) - 1]}, dividido por 12` : `todo dia ${r.dia}`}${conta ? `, saindo de ${esc(nomeConta(conta))}` : ''}`;
  return `<div class="lbl">Aporte por mês nos seus investimentos</div>
    <div class="aporte-info"><b>${brl(ap)}</b><span>Das contas a pagar do tipo Aporte: ${quando}.</span></div>
    <div class="btns" style="margin-top:10px"><button class="btn peq" data-a="aporte-ajustar">${ic('edit', 'ic-s')}${fx.length > 1 ? 'Ver os aportes' : 'Mudar o aporte'}</button>
      <button class="btn peq" data-a="aporte-novo">${ic('plus', 'ic-s')}Outro aporte</button></div>`;
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
  const vals = [...proj.flatMap(p => [p.valor, p.aplicado, p.real]), ...histC.map(p => p.v)];
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
    const passoA = span > 7 ? 2 : 1;
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
  const area = linha(proj, p => p.valor) + proj.slice().reverse().map(p => `L${X(p.t).toFixed(1)},${Y(p.aplicado).toFixed(1)}`).join('') + 'Z';
  g += `<path class="a-proj" d="${area}"/>`;
  g += `<path class="l-apl" d="${linha(proj, p => p.aplicado)}"/>`;
  g += `<path class="l-real" d="${linha(proj, p => p.real)}"/>`;
  if (histC.length) g += `<path class="l-hist" d="${linha(histC, p => p.v)}"/>`;
  g += `<path class="l-proj" d="${linha(proj, p => p.valor)}"/>`;
  const ult = proj[proj.length - 1];
  g += `<circle class="pt" cx="${X(ult.t).toFixed(1)}" cy="${Y(ult.valor).toFixed(1)}" r="4.5" fill="var(--accent)"/>`;
  g += `<circle class="pt" cx="${xh}" cy="${Y(proj[0].valor).toFixed(1)}" r="4.5" fill="var(--accent)"/>`;
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
    const pontos = q.p ? [[q.p.valor, 'var(--accent)'], [q.p.aplicado, 'var(--c0)'], [q.p.real, 'var(--c2)']] : [[q.hist, 'var(--accent)']];
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
      ? [[q.p.valor, 'Projetado', 'var(--accent)', true], [q.p.aplicado, 'Valor investido', 'var(--c0)'], [q.p.real, 'Em dinheiro de hoje', 'var(--c2)']]
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
    const g = m.get(k) || { k, nome, cor, v: 0, n: 0, mes: 0 };
    const v = valorHoje(i);
    g.v += v; g.n++; g.mes += rendeMes(v, taxaAnual(i));
    m.set(k, g);
  }
  return [...m.values()].sort((a, b) => b.v - a.v);
}

function grafComposicao(lista) {
  const u = S.ui;
  const gs = grupos(lista, u.gAgrup);
  const total = gs.reduce((s, g) => s + g.v, 0) || 1;
  const sel = gs.find(g => g.k === u.gSel);
  const opts = [['banco', 'Banco'], ['dono', 'De quem'], ['tipo', 'Tipo'], ['liq', 'Liquidez']];
  let html = `<div class="chips c4">${opts.map(([k, n]) => `<button class="chip${u.gAgrup === k ? ' on' : ''}" data-a="g" data-k="gAgrup" data-v="${k}">${n}</button>`).join('')}</div>`;
  html += `<div class="graf-card" style="padding:18px 18px 8px">
    <div class="stat-duo" style="margin:0 0 10px"><div><span>Total</span><b>${brl(total, 0)}</b></div><div><span>Rende por mês</span><b>${brl(gs.reduce((s, g) => s + g.mes, 0), 0)}</b></div></div>
    <div class="pilha-cap">${sel ? `<b>${esc(sel.nome)}</b> · ${brl(sel.v, 0)} · ${pct(sel.v / total * 100)}%` : 'Toque numa parte para ver o valor'}</div>
    <div class="pilha" role="img" aria-label="Divisão do dinheiro por ${opts.find(o => o[0] === u.gAgrup)[1].toLowerCase()}">
      ${gs.map(g => `<i data-a="g" data-k="gSel" data-v="${esc(g.k)}" style="--c:${g.cor};flex:${g.v / total} 1 0"></i>`).join('')}</div>
    <div style="margin-top:8px">${gs.map(g => `<div class="comp${u.gSel === g.k ? ' on' : ''}" data-a="g" data-k="gSel" data-v="${esc(g.k)}" style="--c:${g.cor}">
      <span class="sq"></span><div class="nm"><b>${esc(g.nome)}</b><span class="sub">${plural(g.n, 'investimento', 'investimentos')} · ≈ ${brl(g.mes, 0)}/mês</span>
      <div class="barra"><i style="width:${(g.v / gs[0].v * 100).toFixed(1)}%"></i></div></div>
      <div class="vl">${brl(g.v, 0)}<small>${pct(g.v / total * 100)}%</small></div></div>`).join('')}</div>
  </div>`;
  return html;
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
    'b-nu': [c('k-nu-diego', 'Diego', true, 3, 10), c('k-nu-dessa', 'Dessa', true, 28, 5)],
    'b-inter': [c('k-inter-diego', 'Diego', true, 25, 2)],
    'b-itau': [c('k-itau-diego', 'Diego', false, 1, 10)],
    'b-xp': [c('k-xp-diego', 'Diego', false, 1, 10)],
    'b-caixa': [c('k-caixa-mae', 'Mãe', false, 1, 10)],
    'b-sicredi': [c('k-sicredi-dessa', 'Dessa', false, 1, 10)],
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
    R({ id: 'r-sal', tipo: 'receita', descricao: 'Salário', valor: 11800, dia: 5, categoria: 'c-salario', conta: 'k-itau-diego',
      descontos: [{ id: 'd-inss', descricao: 'INSS', modo: 'pct', valor: 7, base: '', categoria: 'c-impostos' },
        { id: 'd-taxa', descricao: 'Taxa administrativa', modo: 'pct', valor: 4.5, base: '', categoria: 'c-impostos' }] }),
    R({ id: 'r-plano', tipo: 'despesa', descricao: 'Plano de saúde', valor: 698.46, dia: 5, categoria: 'c-saude', conta: 'k-itau-diego', vinculo: 'r-sal' }),
    R({ id: 'r-alug', tipo: 'despesa', descricao: 'Aluguel', valor: 2300, dia: 10, categoria: 'c-moradia', conta: 'k-itau-diego' }),
    R({ id: 'r-cond', tipo: 'despesa', descricao: 'Condomínio', valor: 680, dia: 10, categoria: 'c-moradia', conta: 'k-itau-diego' }),
    R({ id: 'r-luz', tipo: 'despesa', descricao: 'Conta de luz', valor: 260, dia: 21, categoria: 'c-contas', conta: 'k-itau-diego' }),
    R({ id: 'r-net', tipo: 'despesa', descricao: 'Internet', valor: 119.9, dia: 18, categoria: 'c-contas', conta: 'k-itau-diego' }),
    R({ id: 'r-ingles', tipo: 'despesa', descricao: 'Inglês', valor: 420, dia: 8, categoria: 'c-educacao', conta: 'k-nu-dessa', cartao: true }),
    R({ id: 'r-acad', tipo: 'despesa', descricao: 'Academia', valor: 129, dia: 3, categoria: 'c-saude', conta: 'k-nu-diego', cartao: true }),
    R({ id: 'r-stream', tipo: 'despesa', descricao: 'Streaming', valor: 55.9, dia: 15, categoria: 'c-assinaturas', conta: 'k-nu-diego', cartao: true }),
    R({ id: 'r-musica', tipo: 'despesa', descricao: 'Spotify', valor: 23.9, dia: 22, categoria: 'c-assinaturas', conta: 'k-nu-dessa', cartao: true }),
    R({ id: 'r-nabu', tipo: 'despesa', descricao: 'Nabu Casa', valor: 34.9, dia: 9, categoria: 'c-assinaturas', conta: 'k-nu-diego', cartao: true }),
    R({ id: 'r-aporte', tipo: 'despesa', descricao: 'Aporte nos investimentos', valor: 800, dia: 6, categoria: 'c-investimentos', conta: 'k-itau-diego', aporte: true }),
    R({ id: 'r-cel', tipo: 'despesa', descricao: 'Celular', valor: 59.99, dia: 14, categoria: 'c-contas', conta: 'k-inter-diego', cartao: true }),
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
      [2, 'Mercado', 'c-mercado', 180, 520, 'k-itau-diego', false], [9, 'Mercado', 'c-mercado', 150, 480, 'k-nu-diego', true],
      [16, 'Mercado', 'c-mercado', 160, 430, 'k-itau-diego', false], [26, 'Hortifruti', 'c-mercado', 60, 140, 'k-nu-dessa', true],
      [6, 'iFood', 'c-restaurantes', 45, 120, 'k-nu-diego', true], [13, 'Restaurante', 'c-restaurantes', 90, 220, 'k-nu-dessa', true],
      [24, 'Padaria', 'c-restaurantes', 25, 60, 'k-itau-diego', false], [7, 'Combustível', 'c-transporte', 180, 260, 'k-inter-diego', true],
      [20, 'Combustível', 'c-transporte', 170, 250, 'k-inter-diego', true], [11, 'Uber', 'c-transporte', 18, 46, 'k-nu-diego', true],
      [17, 'Cinema', 'c-lazer', 60, 140, 'k-nu-dessa', true], [23, 'Pet shop', 'c-pets', 120, 220, 'k-nu-dessa', true],
      [19, 'Farmácia', 'c-saude', 35, 160, 'k-nu-diego', true],
    ];
    for (const [d, desc, cat, a, b, conta, cartao] of gastos) {
      const data = dia(d);
      if (data > hj) continue;
      const o = { tipo: 'despesa', descricao: desc, valor: entre(a, b), categoria: cat, conta, cartao, data };
      L(o);
    }
  }
  // freelances e reembolsos pontuais
  [[-5, 20, 1800], [-3, 22, 2400], [-1, 19, 1200]].forEach(([k, d, v]) => L({ tipo: 'receita', descricao: 'Freelance', valor: v, categoria: 'c-freelance', conta: 'k-inter-diego', data: dataNoMes(addYm(ymAtual, k), d), pago: true }));
  L({ tipo: 'receita', descricao: 'Reembolso médico', valor: 340, categoria: 'c-reembolso', conta: 'k-itau-diego', data: dataNoMes(addYm(ymAtual, -2), 9), pago: true });
  // geladeira em 10x no cartão da Dessa: as parcelas futuras aparecem nas próximas faturas
  const g = 'g-geladeira';
  for (let k = 0; k < 10; k++) {
    L({ tipo: 'despesa', descricao: 'Geladeira', valor: 389.9, categoria: 'c-compras', conta: 'k-nu-dessa', cartao: true, data: dataNoMes(addYm(ymAtual, -4 + k), 14), parcela: `${k + 1}/10`, grupo: g, pago: false });
  }
  // seguro do carro: fixo anual
  R({ id: 'r-seguro', tipo: 'despesa', descricao: 'Seguro do carro', valor: 2380, dia: 12, categoria: 'c-transporte', conta: 'k-itau-diego', inicio: addYm(ymAtual, 3), freq: 'anual' });
  // IPTU atrasado (para mostrar o aviso)
  const atras = iso(new Date(hoje().getTime() - 3 * 86400000));
  L({ tipo: 'despesa', descricao: 'IPTU', valor: 212.4, categoria: 'c-impostos', conta: 'k-itau-diego', data: atras, pago: false, parcela: '8/10' });
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
    return html + `<div class="vazio"><b>Comece pelo que entra e sai todo mês.</b><br>Cadastre o salário e os gastos fixos uma vez só; eles aparecem sozinhos nos próximos meses.<br><br>
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
  if (u.cxFiltro === 'pendentes') lista = lista.filter(l => !l.pago);
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
  return `<div class="lanc${dentroFatura ? ' sub' : ''}" data-a="lanc" data-id="${esc(l.id)}" role="button" tabindex="0">
    <span class="ini${apo ? ' apo' : ''}" style="--c:${corCat(l)}">${apo ? ic('wallet') : esc((l.descricao || '?').slice(0, 1).toUpperCase())}</span>
    <span class="lanc-t"><b>${esc(l.descricao)}</b><span>${esc([nomeCat, conta, ...extras].filter(Boolean).join(' · '))}</span></span>
    <span class="lanc-d"><b class="${rec ? 'ent' : 'sai'}">${rec ? '+' : '−'} ${brl(+l.valor || 0)}</b>${estado}
      ${!l.pago && !dentroFatura && !l.desconto && !l.vinculo ? `<button class="pagar" data-a="lanc-pagar" data-id="${esc(l.id)}">${rec ? 'Recebi' : apo ? 'Apliquei' : 'Paguei'}</button>` : ''}</span>
  </div>`;
}

function linhaFatura(f) {
  const c = contaDe(f.conta);
  const aberta = S.ui.faturaAberta === f.k;
  const atras = !f.pago && f.dc < iso(hoje());
  const itens = f.itens.slice().sort((a, b) => a.data < b.data ? -1 : 1);
  return `<div class="lanc fatura${aberta ? ' aberta' : ''}" data-a="fatura-abrir" data-v="${esc(f.k)}" role="button" tabindex="0" aria-expanded="${aberta}">
    <span class="ini" style="--c:${corOk(bancoDe(c?.banco)?.cor) || '#B8B0B0'}">${ic('card', 'ic-s')}</span>
    <span class="lanc-t"><b>Fatura ${esc(nomeConta(c))}</b><span>${plural(f.itens.length, 'compra', 'compras')} · vence ${fDataC(pData(f.dc))} · ${aberta ? 'toque para fechar' : 'toque para ver'}</span></span>
    <span class="lanc-d"><b class="sai">− ${brl(f.total)}</b>${f.pago ? '<span class="tag">Paga</span>' : `<span class="tag ${atras ? 'alerta' : 'pend'}">${atras ? 'Atrasada' : 'Aberta'}</span>`}
      ${!f.pago ? `<button class="pagar" data-a="fatura-pagar" data-v="${esc(f.k)}">Paguei</button>` : ''}</span>
  </div>${aberta ? `<div class="fatura-itens">${itens.map(l => linhaLanc(l, true)).join('')}</div>` : ''}`;
}

/* --------- fluxo de caixa */
function periodoFluxo() {
  const p = S.ui.cxPeriodo, a = ymHoje();
  if (p === 'passado') return [addYm(a, -11), a];
  if (p === 'futuro') return [a, addYm(a, 11)];
  return [addYm(a, -5), addYm(a, 6)];
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
  const passado = serie.filter(m => !m.prev), futuro = serie.filter(m => m.prev);
  const soma = (l, k) => l.reduce((s, m) => s + m[k], 0);
  let html = `<div class="chips c3">${[['passado', '12 meses atrás'], ['meio', '6 + 6'], ['futuro', '12 à frente']].map(([k, n]) =>
    `<button class="chip${u.cxPeriodo === k ? ' on' : ''}" data-a="cx-periodo" data-v="${k}">${n}</button>`).join('')}</div>`;
  html += `<div class="graf-card"><h3 class="g-tit">${rotIc('chart')}<span>Fluxo de caixa mensal</span></h3>
    <div class="stat-duo">${passado.length ? `<div><span>Sobrou por mês, em média</span><b>${brlS(soma(passado, 'net') / passado.length, 0)}</b><small>${nomeMes(passado[0].ym, true)} a ${nomeMes(passado[passado.length - 1].ym, true)}</small></div>` : ''}
      ${futuro.length ? `<div><span>Deve sobrar à frente</span><b>${brlS(soma(futuro, 'net'), 0)}</b><small>${S.d.ajustes.prever_dia !== false ? 'fixos, parcelas, faturas e dia a dia' : 'fixos, parcelas e faturas já lançados'}</small></div>` : ''}</div>
    <div class="chart" id="ch-fluxo" role="img" aria-label="Entradas e saídas por mês"></div>
    <div class="leg"><span><i class="sw-q" style="--kc:var(--entra)"></i>Entradas</span><span><i class="sw-q" style="--kc:var(--sai)"></i>Saídas</span>
      ${serie.some(m => m.apo > 0) ? '<span><i class="sw-q" style="--kc:var(--apo)"></i>Aportes</span>' : ''}
      ${S.d.ajustes.prever_dia !== false ? '<span><i class="sw-q est"></i>Dia a dia (média)</span>' : ''}<span><i class="pt-q"></i>Sobrou</span><span><i class="sw-q prev"></i>Previsto</span></div>
    <div class="sep" style="margin:14px 6px"></div>
    <div class="linha-sw" style="margin:0 6px"><div><b>Prever o dia a dia</b><span>Soma nos próximos meses a média dos gastos que não são fixos nem parcelas (mercado, restaurante, combustível): ${brl(mediaVariaveis(), 0)} por mês.</span></div>
      ${chave('prever_dia', S.d.ajustes.prever_dia !== false, 'Prever o dia a dia')}</div></div>`;
  html += `<div class="graf-card"><h3 class="g-tit">${rotIc('wallet', 'bom')}<span>Saldo em caixa</span></h3>
    <div class="stat-duo"><div><span>Hoje</span><b>${brl(saldoCaixa(), 0)}</b></div>
      <div><span>Em ${nomeMes(serie[serie.length - 1].ym, true)}</span><b>${brl(serie[serie.length - 1].saldo, 0)}</b></div></div>
    <div class="chart" id="ch-saldo" role="img" aria-label="Saldo em caixa no fim de cada mês"></div>
    <div class="leg"><span><i class="k" style="--kc:var(--accent)"></i>Fechado</span><span><i class="k tr" style="--kc:var(--accent)"></i>Previsto</span></div></div>`;
  html += `<p class="nota">Compras no cartão entram no mês em que a fatura vence. Fixos aparecem nos meses em que acontecem (todo mês ou todo ano) com o valor padrão, até você confirmar o valor real.</p>
  <details class="card" style="margin-top:16px"><summary>Ver tabela por mês</summary>
  <table class="tabela"><thead><tr><th>Mês</th><th class="n">Entrou</th><th class="n">Saiu</th><th class="n">Sobrou</th><th class="n">Saldo</th></tr></thead><tbody>
  ${serie.map(m => `<tr><td>${nomeMes(m.ym, true)}${m.prev ? ' *' : ''}</td><td class="n">${brl(m.ent, 0)}</td><td class="n">${brl(m.sai, 0)}</td><td class="n">${brl(m.net, 0)}</td><td class="n">${brl(m.saldo, 0)}</td></tr>`).join('')}
  </tbody></table><p class="nota">* previsto</p></details>`;
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
  let g = '';
  for (let v = -top; v <= top + 1; v += step) {
    const y = Y(v).toFixed(1);
    g += `<line class="grid${v === 0 ? ' zero' : ''}" x1="${pl}" x2="${W - pr}" y1="${y}" y2="${y}"/><text x="${pl - 8}" y="${(+y + 4).toFixed(1)}" text-anchor="end">${v < 0 ? '−' : ''}${compacto(Math.abs(v))}</text>`;
  }
  const r = 4;
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
    g += `<circle class="pt-net" cx="${cx.toFixed(1)}" cy="${Y(m.net).toFixed(1)}" r="4"/>`;
    if (serie.length <= 7 || i % 2 === 0 || m.atual) g += `<text x="${cx.toFixed(1)}" y="${H - 6}" text-anchor="middle"${m.atual ? ' class="hoje-t"' : ''}>${MESES[+m.ym.slice(5) - 1]}</text>`;
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
    <div class="pilha-cap">${sel ? `<b>${esc(nome(sel))}</b> · ${brl(sel.v, 0)} · ${pct(sel.v / total * 100)}%` : 'Toque numa parte para ver o valor'}</div>
    <div class="pilha" role="img" aria-label="Divisão por categoria">${gs.map(g => `<i data-a="cx-sel" data-v="${esc(g.k)}" style="--c:${cor(g)};flex:${g.v / total} 1 0"></i>`).join('')}</div>
    <div class="comps">${gs.map(g => {
      const media = g.k === '_outras' ? null : ant.reduce((s, m) => s + (m.get(g.k)?.v || 0), 0) / 3;
      const dif = media ? (g.v - media) / media * 100 : null;
      return `<div class="comp${u.cxSel === g.k ? ' on' : ''}" data-a="cx-sel" data-v="${esc(g.k)}" style="--c:${cor(g)}">
        <span class="sq"></span><div class="nm"><b>${esc(nome(g))}</b><span class="sub">${plural(g.n, 'lançamento', 'lançamentos')}${media ? ` · média ${brl(media, 0)}` : ''}</span>
        <div class="barra"><i style="width:${(g.v / gs[0].v * 100).toFixed(1)}%"></i></div></div>
        <div class="vl">${brl(g.v, 0)}<small>${pct(g.v / total * 100)}%${dif != null && Math.abs(dif) >= 10 ? ` · ${dif > 0 ? '▲' : '▼'} ${pct(Math.round(Math.abs(dif)))}%` : ''}</small></div></div>`;
    }).join('')}</div></div>
    <p class="nota">Pela data da compra. Fixos entram com o valor padrão até você confirmar o valor do mês.</p>`;
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

function escolher({ titulo, texto, opcoes }) {
  abrirFolha(() => ({
    titulo,
    corpo: `<p style="margin:0 0 4px;color:var(--text-2)">${texto}</p>`,
    pe: `<div class="pe-col">${opcoes.map((o, i) => `<button class="btn${o.perigo ? ' perigo' : o.pri ? ' pri' : ''}" data-a="escolha" data-v="${i}">${o.rotulo}</button>`).join('')}
      <button class="btn" data-a="fechar">Cancelar</button></div>`,
  }));
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
  if (!lista.length) return `<div class="campo"><div class="lbl">Em qual investimento</div><p class="ajuda" style="margin:0">Cadastre o investimento em Invest para o valor do aporte somar a ele.</p></div>`;
  if (!o.investimento && lista.length === 1) o.investimento = lista[0].id;
  const sel = lista.find(i => i.id === o.investimento);
  return `<div class="campo"><div class="lbl">Em qual investimento</div><div class="chips" style="margin:0">
    ${lista.map(i => `<button class="chip${o.investimento === i.id ? ' on' : ''}" data-a="${chave}" data-v="${esc(i.id)}" style="--c:${corOk(bancoDe(i.banco)?.cor) || 'var(--c0)'}"><span class="bol"></span>${esc(i.nome)}</button>`).join('')}</div>
    ${o.erroInv ? `<div class="msg-erro">${esc(o.erroInv)}</div>` : ''}
    <div class="ajuda">${sel ? `O valor soma a ${esc(sel.nome)}: ${brl(valorHoje(sel))} → ${brl(valorHoje(sel) + (+o.valor || 0))}.` : 'Escolha para onde foi o dinheiro: o valor soma ao investimento.'} É um investimento novo? Cadastre em Invest e volte aqui.</div></div>`;
}

// Adicionar › Nova despesa e Novo investimento: trazer de mensagem, arquivo ou fala, em quadrinhos tracejados
// no alto da janela, como no ResolvIA e no CronologIA (Ler com IA mora aqui, não no cabeçalho).
function tilesIA(modo) {
  if (!iaOn()) return '';
  const caixa = modo === 'caixa', voz = vozPronta();
  const t = (inicio, icone, txt) => `<button type="button" class="imp-tile" data-a="ia-de" data-v="${modo}" data-ini="${inicio}">${ic(icone)}<span>${txt}</span></button>`;
  return `<div class="campo imp-campo"><div class="lbl">Trazer de mensagem ou imagem</div>
    <div class="imp-tiles${voz ? '' : ' dois'}">${t('texto', 'clipboard-paste', 'Colar mensagem')}${t('arquivo', caixa ? 'receipt' : 'camera', caixa ? 'Fatura, print ou foto' : 'Imagem ou print')}${voz ? t('voz', 'mic', 'Falar') : ''}</div>
    <p class="imp-ajuda">${caixa
      ? 'Cole a mensagem do WhatsApp ou mande a fatura, o print ou a foto do papel (dá para colar a imagem direto aqui). A IA separa cada gasto e recebimento e você confere antes de lançar.'
      : 'Cole a mensagem do WhatsApp ou do e-mail, ou mande a imagem do app do banco (dá para colar a imagem direto aqui). A IA acha cada investimento e você confere antes de salvar.'}</p></div>`;
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
    if (apo) c += `<div class="aviso-fixo">${ic('wallet', 'ic-s')}<span>Um compromisso de aplicar nos seus investimentos, como uma conta a pagar. ${f.repete === 'mensal' || f.repete === 'anual' ? 'Fixo, ele soma o aporte por mês da projeção na aba Invest.' : 'Uma vez só, ele não entra no aporte por mês da projeção; para isso, escolha Todo mês.'}</span></div>`;
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
      ${vinc ? `<div class="ajuda">A baixa acontece junto com ${esc(vinc.descricao)}: quando ele for confirmado, este gasto fica pago no mesmo dia e na mesma conta. Se o valor mudar num mês, edite só aquele mês.</div>` : ''}</div>`;
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
    if (f.repete === 'mensal') c += `<div class="ajuda">Fica fixo: aparece todo dia ${+f.data.slice(8, 10)} a partir de ${MESES_LONGOS[+f.data.slice(5, 7) - 1]}, inclusive nos gráficos dos próximos meses. O valor acima é o padrão; quando ${rec ? 'receber' : apo ? 'aplicar' : 'pagar'}, você confirma o valor real do mês.</div>`;
    if (f.repete === 'anual') c += `<div class="ajuda">Fica fixo: aparece todo ano em ${MESES_LONGOS[+f.data.slice(5, 7) - 1]}, dia ${+f.data.slice(8, 10)}, inclusive nos gráficos. Serve para anuidade, IPVA, seguro e planos anuais.</div>`;
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
      } else d.lancamentos.push(Object.assign({ id: uid() }, base));
      if (rec && ridRec && recFinal) { criarLigados(d, f, ridRec, recFinal); baixaVinculados(d, recFinal); }
      return;
    }
    if (f.recorrencia && alcance === 'todos') {
      const r = d.recorrencias.find(x => x.id === f.recorrencia);
      if (r) semDesc(Object.assign(r, { descricao: base.descricao, valor: base.valor, categoria: base.categoria, conta: base.conta, cartao: base.cartao, obs: base.obs, dia: +f.data.slice(8, 10) },
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
function abrirPagar(id) {
  const l = acharLanc(id);
  if (!l) return;
  const r = l.recorrencia ? S.d.recorrencias.find(x => x.id === l.recorrencia) : null;
  PG = { l, valor: +l.valor || 0, inv: l.investimento || r?.investimento || '' };
  if (PG.inv && !S.d.investimentos.some(i => i.id === PG.inv)) PG.inv = '';
  abrirFolha(() => ({
    titulo: ehRec(l) ? 'Confirmar recebimento' : ehAporte(l) ? 'Confirmar aporte' : 'Confirmar pagamento',
    corpo: `<p style="margin:0 0 16px;color:var(--text-2)"><b style="color:var(--text)">${esc(l.descricao)}</b> · ${fData(pData(l.dc || l.data))}${r ? ` · fixo, padrão ${brl(r.valor)}` : ''}</p>
      <div class="campo"><label for="pg-v">Quanto ${ehRec(l) ? 'entrou' : ehAporte(l) ? 'você aplicou' : 'saiu'}</label><div class="pref grande"><span>R$</span><input id="pg-v" data-pg="valor" inputmode="numeric" value="${NF2.format(PG.valor)}"></div>
      ${r ? `<div class="ajuda">Foi diferente este mês? Corrija aqui. O valor padrão continua ${brl(r.valor)} nos próximos meses.</div>` : ''}</div>
      ${ehAporte(l) ? campoInvestimentoAporte({ get investimento() { return PG.inv; }, set investimento(x) { PG.inv = x; }, valor: PG.valor, erroInv: PG.erroInv }, 'pg-inv') : ''}`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="pg-ok">${ehRec(l) ? 'Recebi' : ehAporte(l) ? 'Apliquei' : 'Paguei'}</button>`,
  }));
}
function confirmarPagar() {
  const { l, valor } = PG;
  if (!(valor > 0)) { toast('Coloque o valor.'); return; }
  const apo = ehAporte(l), inv0 = apo && PG.inv ? S.d.investimentos.find(i => i.id === PG.inv) : null;
  if (apo && !inv0 && invsDoAporte().length) { PG.erroInv = 'Escolha em qual investimento o aporte foi aplicado.'; pintarFolha(); return; }
  const novoValor = inv0 ? round2(valorHoje(inv0) + valor) : 0;
  persistir(d => {
    let x;
    const extra = inv0 ? { investimento: inv0.id } : {};
    if (l.virtual) d.lancamentos.push(x = materializar(l, Object.assign({ valor: round2(valor), pago: true }, extra)));
    else { x = d.lancamentos.find(y => y.id === l.id); if (x) Object.assign(x, { pago: true, valor: round2(valor) }, extra); }
    baixaVinculados(d, x);
    if (inv0) {
      const inv = d.investimentos.find(i => i.id === inv0.id);
      if (inv) Object.assign(inv, { valor: novoValor, data_valor: iso(hoje()), atualizado_em: new Date().toISOString() });
      const r = l.recorrencia && d.recorrencias.find(y => y.id === l.recorrencia);
      if (r) r.investimento = inv0.id;
    }
  }, ehRec(l) ? 'Recebimento confirmado' : inv0 ? `Aplicado em ${inv0.nome}` : apo ? 'Aporte confirmado' : 'Pagamento confirmado').then(ok => { if (ok) fecharFolha(); });
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
function abrirAjuste() {
  AJ = { valor: round2(saldoCaixa()) };
  abrirFolha(() => ({
    titulo: 'Ajustar saldo',
    corpo: `<div class="campo"><label for="aj-v">Quanto você tem em conta hoje, somando tudo</label><div class="pref grande"><span>R$</span><input id="aj-v" data-aj="valor" inputmode="numeric" value="${NF2.format(Math.abs(AJ.valor))}"></div>
      <div class="ajuda">O app lança a diferença como "Ajuste de saldo". Ele muda o saldo, mas não entra nas entradas, saídas nem nos gráficos de categoria.</div></div>`,
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
function escolherArquivo(accept) {
  return new Promise(res => {
    const inp = document.createElement('input');
    inp.type = 'file'; inp.accept = accept; inp.style.display = 'none';
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
// Imagens guardadas com o investimento. No investimento novo, quem lê com IA são os quadrinhos do alto
// (Colar mensagem, Imagem ou print): aqui é só para guardar, sem o Ler, para não ter duas leituras na mesma janela.
function fotosFormHTML() {
  const fotos = F.fotos || [];
  const comLer = iaOn() && !!F.id;
  return `<div class="campo"><div class="lbl">Imagens guardadas</div><div class="fotos">
    ${fotos.map(n => `<div class="foto"><img src="${fotoSrc(n)}" alt="Imagem do investimento" data-a="foto-ver" data-v="${esc(n)}">
      <button class="foto-x" data-a="f-foto-rm" data-v="${esc(n)}" aria-label="Remover imagem">${ic('x', 'ic-s')}</button>
      ${comLer ? `<button class="foto-ia" data-a="f-foto-ia" data-v="${esc(n)}">${ic('ia', 'ic-s')}Ler</button>` : ''}</div>`).join('')}
    <button class="foto add" data-a="f-foto-add">${ic('camera')}<span>Guardar</span></button></div>
    <div class="ajuda">${comLer ? 'Comprovante, print ou extrato guardado com o investimento. Toque em <b>Ler</b> para a IA atualizar os campos com uma imagem nova.'
      : 'Comprovante, print ou extrato para guardar junto com o investimento.'}</div></div>`;
}
function verFoto(n) {
  abrirFolha(() => ({ titulo: 'Imagem', corpo: `<img class="foto-grande" src="${fotoSrc(n)}" alt="Imagem do investimento">` }), null, true);
}
async function lerFotoNoForm(n) {
  toast('Lendo com a IA… pode levar até um minuto.');
  try {
    const r = await api.iaLer({ modo: 'invest', foto: n });
    const it = r.itens[0];
    if (!it) { toast('A IA não encontrou investimento nessa imagem.'); return; }
    preencherForm(it);
    pintarFolha();
    toast(r.itens.length > 1 ? `Achei ${r.itens.length} investimentos; preenchi com o primeiro. Para os outros, use Ler com IA no Invest.` : 'Campos preenchidos pela IA. Confira antes de salvar.');
  } catch (e) { toast('Não consegui ler. ' + e.message); }
}
function bancoPorNome(nome, d = S.d) {
  const n = semAcento(nome);
  if (!n) return null;
  return d.bancos.find(b => semAcento(b.nome) === n) || d.bancos.find(b => semAcento(b.nome).includes(n) || n.includes(semAcento(b.nome)));
}
const semAcento = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
function preencherForm(it) {
  Object.assign(F, { nome: it.nome || F.nome, tipo: it.tipo || F.tipo, valor: it.valor || F.valor, indexador: it.indexador || F.indexador,
    taxa: it.indexador === 'poupanca' || it.indexador === 'parado' ? 0 : it.taxa, liquidez: it.liquidez || F.liquidez,
    vencimento: it.vencimento || F.vencimento, data_valor: it.data_valor || iso(hoje()), idxEditado: true });
  const b = bancoPorNome(it.banco);
  if (b) F.banco = b.id;
  else if (it.banco) { const nb = { id: 'b-' + uid(), nome: it.banco, cor: CORES_BANCO.find(c => !S.d.bancos.some(x => x.cor === c)) || CORES_BANCO[0] }; F.bancosNovos.push(nb); F.banco = nb.id; }
  if (it.aplicado && !F.obs) { F.obs = `Valor aplicado: ${brl(it.aplicado)}`; F.obsAberta = true; }
}

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
      <p class="nota" style="text-align:center">O Home Assistant transcreve${v.nome && !/^home assistant$/i.test(v.nome) ? ` (${esc(v.nome)})` : ''} e a IA separa sozinha os gastos, os recebimentos, as contas a pagar e a receber e os investimentos. Você confere antes de lançar.</p>`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="fala-ok"${on ? '' : ' disabled'}>${ic('ia', 'ic-s')}Pronto</button>`,
  };
}
const ouvidoHTML = s => s.ouvido ? `<div class="ouvido">${ic('mic', 'ic-s')}<span>“${esc(s.ouvido)}”</span></div>` : '';

function abrirIA(modo, inicio) {
  // a IA separa sozinha lançamentos (gastos, recebimentos, a pagar e a receber) e investimentos: não se escolhe antes
  IAS = { dica: modo === 'invest' ? 'invest' : 'caixa', etapa: inicio === 'voz' ? 'voz' : 'entrada', rec: inicio === 'voz' ? 'starting' : 'off', arquivo: null, texto: '', itens: [], invs: [], erro: '', conta: '', cartao: false,
    situacao: 'auto', futuras: true, ouvido: '' };
  if (!S.ia && !DEMO) api.iaStatus().then(s => { S.ia = s; if (IAS && FOLHA) pintarFolha(); }).catch(() => {});
  abrirFolha(montarIA, () => { pararFala(); IAS = null; });
  if (inicio === 'voz') comecarFala();
  if (inicio === 'arquivo') escolherArquivo('image/*,application/pdf').then(iaPegarArquivo);
  if (inicio === 'texto') requestAnimationFrame(() => { const t = $('#ia-txt'); if (t) t.focus(); });
}
function montarIA() {
  const s = IAS;
  if (s.etapa === 'voz') return telaFala();
  if (s.etapa === 'transcrevendo') return { titulo: 'Falar', corpo: `<div class="ia-lendo"><span class="giro"></span><p>Transcrevendo o que você disse…</p></div>` };
  if (s.etapa === 'revisao' && s.ouvido) { const r = revisaoIA(); r.corpo = ouvidoHTML(s) + r.corpo; return r; }
  if (s.etapa === 'lendo') return { titulo: 'Lendo com IA', corpo: `<div class="ia-lendo"><span class="giro"></span><p>Lendo ${s.arquivo ? (s.arquivo.pdf ? 'o PDF' : 'a imagem') : 'o texto'} com a IA do Home Assistant…<br>Pode levar até um minuto.</p></div>` };
  if (s.etapa === 'revisao') return revisaoIA();
  const aviso = S.ia && S.ia.pronta === false ? `<div class="aviso-fixo alerta">${ic('alert', 'ic-s')}<span>${esc(S.ia.motivo || 'A IA não está pronta.')} Veja em Mais &gt; Leitura por IA.</span></div>` : '';
  const arq = s.arquivo;
  return {
    titulo: 'Ler com IA',
    corpo: `${aviso}<div class="ia-arq">${arq ? `<div class="ia-prev">${arq.pdf ? `<span class="ia-pdf">${ic('file')}</span>` : `<img src="${arq.dataUrl}" alt="">`}
          <span><b>${esc(arq.nome)}</b><small>${arq.pdf ? 'PDF' : 'Imagem'}</small></span><button class="icbtn" data-a="ia-arq-rm" aria-label="Tirar arquivo">${ic('x')}</button></div>`
        : `<button class="btn larga" data-a="ia-arq">${ic('camera')}Fatura, print, foto ou PDF</button>`}
        ${!arq && vozPronta() ? `<button class="btn larga" data-a="ia-falar" style="margin-top:8px">${ic('mic')}Falar</button>` : ''}</div>
      <div class="campo"><label for="ia-txt">Ou cole o texto</label>
        <textarea id="ia-txt" class="inp" data-ias="texto" rows="6" placeholder="Ex.: mensagens do WhatsApp (“gastei 45 no mercado”, “recebi 300 do João”, “boleto do IPVA vence dia 10”, “apliquei 2 mil no CDB do Inter”), fatura, extrato ou e-mail do banco">${esc(s.texto)}</textarea>
        <div class="ajuda">Você também pode colar um print aqui. Não precisa dizer o que é: a IA separa os gastos, os recebimentos, as contas a pagar e a receber e os investimentos, e você confere antes de salvar.</div></div>
      ${s.erro ? `<div class="msg-erro">${esc(s.erro)}</div>` : ''}`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="ia-ler"${!arq && !s.texto.trim() ? ' disabled' : ''}>${ic('ia', 'ic-s')}Ler com IA</button>`,
  };
}
async function iaPegarArquivo(file) {
  if (!file) return;
  const pdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name);
  if (!pdf && !/^image\//.test(file.type)) { toast('Envie uma imagem ou um PDF.'); return; }
  if (file.size > 15 * 1024 * 1024) { toast('Arquivo grande demais (máximo 15 MB).'); return; }
  try {
    const dataUrl = pdf ? await lerArquivo(file) : await imagemJPG(file);
    IAS.arquivo = { nome: file.name || (pdf ? 'arquivo.pdf' : 'imagem.jpg'), pdf, dataUrl, foto: null };
    IAS.erro = '';
    pintarFolha();
  } catch (e) { toast(e.message); }
}
async function iaLer() {
  const s = IAS;
  s.erro = ''; s.etapa = 'lendo'; pintarFolha();
  try {
    const corpo = { modo: 'auto', dica: s.dica, texto: s.texto };
    if (s.ouvido && !s.arquivo) corpo.fala = true;
    if (s.arquivo) corpo.anexo = { b64: s.arquivo.dataUrl };
    const r = await api.iaLer(corpo);
    if (!IAS) return;
    const lanc = r.lancamentos || [], invs = r.investimentos || [];
    if (!lanc.length && !invs.length) { s.etapa = 'entrada'; s.erro = 'A IA não encontrou gasto, recebimento, conta nem investimento. Tente outra imagem ou cole o texto.'; pintarFolha(); return; }
    s.itens = lanc.map(it => Object.assign({ marcado: true }, it));
    s.invs = invs.map(it => Object.assign({ marcado: true }, it));
    if (s.itens.length) prepararRevisaoCaixa();
    s.etapa = 'revisao';
    pintarFolha();
  } catch (e) {
    if (!IAS) return;
    s.etapa = 'entrada'; s.erro = 'Não consegui ler. ' + e.message; pintarFolha();
  }
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
  let corpo = `<p style="margin:0 0 14px;color:var(--text-2)">Achei <b style="color:var(--text)">${achou}</b>. Confira e desmarque o que não quiser.</p>`;
  if (nl) corpo += `${ni ? `<h3 class="ia-sec">${ic('fluxo', 'ic-s')}Lançamentos</h3>` : ''}${revisaoCaixa()}`;
  if (ni) corpo += `${nl ? `<h3 class="ia-sec">${ic('wallet', 'ic-s')}Investimentos</h3>` : ''}${revisaoInvest()}`;
  const total = ml.reduce((a, i) => a + (i.tipo === 'receita' ? i.valor : -i.valor), 0);
  const n = ml.length + mi.length;
  const rot = ni && !nl ? `Salvar ${n}` : nl && !ni ? `Lançar ${n} · ${total < 0 ? '−' : ''}${brl(Math.abs(total), 0)}` : `Salvar ${n}`;
  return { titulo: nl && ni ? 'Conferir o que a IA leu' : nl ? 'Conferir lançamentos' : 'Conferir investimentos', corpo,
    pe: `<button class="btn" data-a="ia-voltar">Voltar</button><button class="btn pri" data-a="ia-salvar"${n ? '' : ' disabled'}>${rot}</button>` };
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
  return dataCaixa({ data, conta: s.conta, cartao }) <= iso(hoje());
}
// no cartão: o que a IA leu como compra no cartão; se você escolher Cartão de crédito ou Débito, vale para todos
function iaNoCartao(it) {
  const s = IAS;
  return it.tipo === 'despesa' && !!s.cartao && !!contaDe(s.conta)?.cartao && (s.cartaoMexido || it.cartao !== false);
}
function revisaoCaixa() {
  const s = IAS;
  const conta = contaDe(s.conta);
  const temParc = s.itens.some(i => i.parcelas_total > i.parcela_atual);
  return `<div class="campo"><div class="lbl">Lançar em</div><div class="chips" style="margin:0">
      <button class="chip${!s.conta ? ' on' : ''}" data-a="iac-conta" data-v="">Sem conta</button>
      ${contas().map(k => `<button class="chip${s.conta === k.id ? ' on' : ''}" data-a="iac-conta" data-v="${k.id}" style="--c:${corOk(k.cor) || '#B8B0B0'}"><span class="bol"></span>${esc(nomeConta(k))}</button>`).join('')}</div>
      ${conta?.cartao ? `<div class="seg mini" style="margin:10px 0 0"><button class="${!s.cartao ? 'on' : ''}" data-a="iac-cartao" data-v="">Débito ou Pix</button><button class="${s.cartao ? 'on' : ''}" data-a="iac-cartao" data-v="1">${ic('card', 'ic-s')}Cartão de crédito</button></div>` : ''}</div>
    <div class="campo"><div class="lbl">Situação</div><div class="seg mini" style="margin:0">
      <button class="${s.situacao === 'auto' ? 'on' : ''}" data-a="iac-sit" data-v="auto">Automática</button>
      <button class="${s.situacao === 'pago' ? 'on' : ''}" data-a="iac-sit" data-v="pago">Tudo pago</button>
      <button class="${s.situacao === 'apagar' ? 'on' : ''}" data-a="iac-sit" data-v="apagar">Tudo pendente</button></div>
      ${s.situacao === 'auto' ? `<div class="ajuda">O que a IA viu como conta a pagar ou valor a receber fica pendente; o resto, pela data.${s.cartao ? ' Compras no cartão seguem a fatura.' : ''}</div>` : ''}</div>
    ${temParc ? `<div class="linha-sw" style="margin-bottom:16px"><div><b>Lançar as próximas parcelas</b><span>Aparecem nas faturas dos próximos meses.</span></div><button class="sw${s.futuras ? ' on' : ''}" data-a="iac-futuras" aria-label="Lançar parcelas futuras"></button></div>` : ''}
    <div class="ia-itens">${s.itens.map((it, k) => {
      const cats = S.d.categorias.filter(c => c.tipo === it.tipo);
      return `<div class="ia-item${it.marcado ? '' : ' off'}">
        <button class="ia-check${it.marcado ? ' on' : ''}" data-a="ia-marca" data-i="${k}" aria-label="${it.marcado ? 'Desmarcar' : 'Marcar'}">${it.marcado ? ic('check', 'ic-s') : ''}</button>
        <div class="ia-item-t"><b>${esc(it.descricao)}</b>
          <span>${fDataC(pData(it.data))}${it.parcelas_total ? ` · parcela ${it.parcela_atual}/${it.parcelas_total}` : ''}${iaNoCartao(it) || iaPago(it, it.data) ? '' : ` · <b class="ia-pend">${it.tipo === 'receita' ? 'a receber' : 'a pagar'}</b>`}${it.dup ? ' · <em>parece já lançado</em>' : ''}${it.confianca === 'baixa' ? ' · <em>confira</em>' : ''}</span>
          <select class="ia-cat" data-iai="categoria" data-i="${k}" aria-label="Categoria">${cats.map(c => `<option value="${c.id}"${c.id === it.categoria ? ' selected' : ''}>${esc(c.nome)}</option>`).join('')}</select></div>
        <b class="${it.tipo === 'receita' ? 'ent' : 'sai'}">${it.tipo === 'receita' ? '+' : '−'} ${brl(it.valor)}</b></div>`;
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
  const msg = [ml.length ? plural(ml.length, 'lançamento', 'lançamentos') : '', mi.length ? plural(mi.length, 'investimento', 'investimentos') : ''].filter(Boolean).join(' e ');
  persistir(d => {
    if (ml.length) aplicarIACaixa(d, ml);
    if (mi.length) aplicarIAInvest(d, mi);
  }, `${msg} pela IA`).then(ok => {
    if (!ok) return;
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
      const base = { tipo: it.tipo, descricao: it.descricao, valor: it.valor, categoria: it.categoria, conta: s.conta, cartao, obs: '' };
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
function revisaoInvest() {
  const s = IAS;
  return `<p class="ajuda" style="margin:0 0 10px">Os investimentos que já existem têm o valor atualizado.</p>
    <div class="ia-itens">${s.invs.map((it, k) => {
      const ex = it.existente && S.d.investimentos.find(i => i.id === it.existente);
      return `<div class="ia-item${it.marcado ? '' : ' off'}">
        <button class="ia-check${it.marcado ? ' on' : ''}" data-a="ia-marca-inv" data-i="${k}" aria-label="${it.marcado ? 'Desmarcar' : 'Marcar'}">${it.marcado ? ic('check', 'ic-s') : ''}</button>
        <div class="ia-item-t"><b>${esc(it.nome)}</b>
          <span>${esc([it.banco, tipoDe(it.tipo).nome, rotuloTaxa(it), it.vencimento ? 'vence ' + fData(pData(it.vencimento)) : ''].filter(Boolean).join(' · '))}</span>
          ${ex ? (it.aporte > 0 && !(it.valor > 0) ? `<span class="ia-atualiza">Aplica ${brl(it.aporte)} em ${esc(ex.nome)}: ${brl(valorHoje(ex))} → ${brl(valorHoje(ex) + it.aporte)}</span>`
            : `<span class="ia-atualiza">Atualiza ${esc(ex.nome)}: ${brl(valorHoje(ex))} → ${brl(it.valor)}</span>`) : '<span class="ia-atualiza novo">Novo investimento</span>'}
          ${it.confianca === 'baixa' ? '<span><em>Confira os números</em></span>' : ''}
          <button class="link" data-a="iai-revisar" data-i="${k}">Revisar antes</button></div>
        <b>${brl(it.aporte > 0 && !(it.valor > 0) ? it.aporte : it.valor)}</b></div>`;
    }).join('')}</div>`;
}
function aplicarIAInvest(d, itens) {
  const s = IAS, hj = iso(hoje());
  const foto = s.arquivo?.foto;
  {
    for (const it of itens) {
      const ex = it.existente && d.investimentos.find(i => i.id === it.existente);
      if (ex) {
        // "apliquei 3 mil no CDB": a IA manda o aporte sem o saldo, e ele soma ao valor de hoje
        const valor = it.aporte > 0 && !(it.valor > 0) ? round2(valorHoje(ex) + it.aporte) : it.valor;
        Object.assign(ex, { valor, data_valor: it.aporte > 0 && !(it.valor > 0) ? hj : it.data_valor || hj, atualizado_em: new Date().toISOString() });
        if (!ex.vencimento && it.vencimento) ex.vencimento = it.vencimento;
        if (foto) ex.fotos = [...(ex.fotos || []), foto];
        continue;
      }
      let b = bancoPorNome(it.banco, d);
      if (!b && it.banco) { b = { id: 'b-' + uid(), nome: it.banco, cor: CORES_BANCO.find(c => !d.bancos.some(x => x.cor === c)) || CORES_BANCO[0], obs: '', contas: [] }; d.bancos.push(b); }
      d.investimentos.push({ id: uid(), nome: it.nome, banco: b?.id || '', tipo: it.tipo, valor: it.valor, data_valor: it.data_valor || hj,
        indexador: it.indexador, taxa: ['poupanca', 'parado'].includes(it.indexador) ? 0 : it.taxa, liquidez: it.liquidez, vencimento: it.vencimento || null,
        titular: 'meu', terceiro: '', obs: it.aplicado ? `Valor aplicado: ${brl(it.aplicado)}` : '', fotos: foto ? [foto] : [],
        criado_em: new Date().toISOString(), atualizado_em: new Date().toISOString() });
    }
  }
}
function revisarItemInvest(k) {
  const it = IAS.invs[k], foto = IAS.arquivo?.foto;
  const ex = it.existente && S.d.investimentos.find(i => i.id === it.existente);
  if (ex) { abrirInvestimento(ex.id); preencherForm(it); if (foto) F.fotos = [...(F.fotos || []), foto]; pintarFolha(); return; }
  abrirInvestimento(null, { fotos: foto ? [foto] : [], daIA: true });
  preencherForm(it);
  pintarFolha();
}
document.addEventListener('paste', ev => {
  if (!iaOn()) return;
  const f = [...(ev.clipboardData?.files || [])].find(x => /^image\//.test(x.type) || x.type === 'application/pdf');
  if (!f) return;
  if (IAS && IAS.etapa === 'entrada') { ev.preventDefault(); iaPegarArquivo(f); return; }
  // com a Nova despesa ou o Novo investimento aberto, colar uma imagem já abre a leitura por IA com ela
  if (!IAS && FOLHA && $('#folhas .imp-campo')) {
    ev.preventDefault();
    abrirIA(FOLHA.montar === montarFormInv ? 'invest' : 'caixa');
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
  if (!IAS) abrirIA(FOLHA.montar === montarFormInv ? 'invest' : 'caixa');
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
  const subs = ((S.dicas && S.dicas.dicas) || []).filter(x => !fora.has(x.id) && realDe(x).real >= 10)
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
  const conferindo = S.dicas && S.dicas.conferindo && (S.dicas.assinaturas || []).some(a => a.status === 'conferindo');
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
    ${maisLead(`O app procura assinaturas nos seus fixos e faturas e confere o preço do plano anual na página oficial de cada serviço, lida pela IA do Home Assistant. A dica só aparece quando o valor que você paga bate com um plano e o preço está escrito na página. Reconhece ${esc(juntarE(catalogo))}.`)}`;
  if (S.d.ajustes.dicas === false) return h + `<div class="status manual">Desligadas em Mais › Opções.</div></section>`;
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
  h += `<div class="dica-btns"><button class="btn out" data-a="dicas-conferir"${st && st.conferindo ? ' disabled' : ''}>${ic('refresh')}${st && st.conferindo ? 'Conferindo…' : 'Conferir agora'}</button>
    ${fora ? `<button class="btn" data-a="dicas-voltar">Mostrar dispensadas (${fora})</button>` : ''}</div>`;
  if (st && st.dolar && st.dolar.valor) h += `<p class="nota" style="margin:12px 0 0">Planos em dólar são comparados com o dólar do Banco Central (${brl(st.dolar.valor)} em ${esc(st.dolar.data || '')}) mais IOF e câmbio do cartão. A economia em reais é estimada pelo que você paga hoje.</p>`;
  return h + `</section>`;
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
  const corpo = `<p class="da-intro">Primeiro troque para o plano anual em <a href="${esc(x.fonte)}" target="_blank" rel="noopener">${esc(x.dominio)}</a>. Depois confirme aqui para o GerencIA ajustar o seu fluxo: ${x.origem === 'fixo' ? 'o fixo mensal para e entra um fixo anual.' : 'entra um fixo anual, que aparece todo ano.'}</p>
    <div class="cmp-anual"><div><span>Hoje</span><b>${brl(x.valor)}</b><small>por mês · ${brl(12 * x.valor, 0)} por ano</small></div>
      <div><span>No anual</span><b>${fmtPreco(x.anual, x.moeda)}</b><small>por ano, na página oficial</small></div></div>
    <div class="campo"><label for="da-valor">Valor da cobrança anual</label><div class="pref grande${DA.erro ? ' erro' : ''}"><span>R$</span><input id="da-valor" data-da="valor" inputmode="numeric" value="${DA.valor ? NF2.format(DA.valor) : ''}"></div>
      <div class="ajuda">${x.estimado ? `Estimado: ${fmtPreco(x.anual, x.moeda)} no câmbio que o seu cartão cobra hoje. Ajuste quando vier a cobrança.` : `Preço da página oficial.`}</div>${DA.erro ? `<div class="msg-erro">${DA.erro}</div>` : ''}</div>
    <div class="campo"><label for="da-data">Primeira cobrança anual</label><input id="da-data" class="inp" type="date" data-da="data" value="${esc(DA.data)}">
      <div class="ajuda">${x.origem === 'fixo' ? `O fixo mensal vai até o mês anterior. ` : ''}Depois, a cobrança entra todo ano em ${mes}${x.cartao ? ', na fatura do cartão' : ''}.</div></div>
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
    <div class="pref"><input data-lfd="valor" data-i="${i}" inputmode="decimal" value="${x.valor ? NFP4.format(x.valor) : ''}" placeholder="0" aria-label="Porcentagem do bruto"><span>%</span></div>
    <button class="icbtn" data-a="lf-desc-rm" data-v="${i}" aria-label="Tirar imposto">${ic('x')}</button>
    <b class="desc-v" id="lfd-v-${i}">− ${brl(valorDesc(l, x))}</b></div>`).join('');
  h += `<div class="chips" style="margin:6px 0 0">${DESC_RAPIDOS.map(([n], k) => [n, k]).filter(([n]) => n === 'Outro imposto' || !f.descontos.some(x => semAcento(x.descricao) === semAcento(n))).map(([n, k]) =>
    `<button class="chip add" data-a="lf-desc-add" data-v="${k}">${ic('plus', 'ic-s')}${n}</button>`).join('')}</div>`;
  h += `<div class="ajuda">Porcentagem do bruto. O imposto sai do caixa junto com o recebimento, já pago, na categoria Impostos e taxas.</div>`;
  h += `<div class="sub-lbl">Outros descontos ligados</div>`;
  if (lig.length) {
    h += lig.map(o => `<div class="lig-l">${o.existe ? ic('repeat', 'ic-s') : `<input type="checkbox" data-lfn="${o.i}"${o.sel ? ' checked' : ''} aria-label="Criar ${esc(o.descricao)}">`}
      <span>${esc(o.descricao)}${o.existe ? (o.atualiza ? ' · valor do recibo neste mês' : '') : ' · nova despesa fixa ligada'}</span><b>− ${brl(o.valor)}</b></div>`).join('');
  }
  h += `<div class="ajuda">${f.recorrencia || f.repete === 'mensal'
    ? 'Plano de saúde e outros: cadastre a despesa e, em "Como é pago", escolha este recebimento. A baixa dela acontece junto com a dele.'
    : 'Para ligar o plano de saúde e outros descontos, o recebimento precisa ser fixo (Repetir: Todo mês).'}</div>`;
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
      if (m) m.valor = n.valor;
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
    ${maisLead('Para onde vai e de onde vem o dinheiro. Toque numa categoria para mudar o nome ou a cor.')}
    <h3>Gastos</h3><div class="chips">${grupo('despesa')}<button class="chip add" data-a="categoria-nova" data-v="despesa">${ic('plus', 'ic-s')}Nova</button></div>
    <h3>Recebimentos</h3><div class="chips" style="margin:0">${grupo('receita')}<button class="chip add" data-a="categoria-nova" data-v="receita">${ic('plus', 'ic-s')}Nova</button></div></section>`;
}
function cardFixos() {
  const ym = ymHoje();
  // só os que ainda vão acontecer (um fixo parado some da lista; o que ele já lançou continua no caixa)
  const ativos = S.d.recorrencias.filter(r => { for (let k = 1; k <= 12; k++) if (ativaEm(r, addYm(ym, k))) return true; return false; });
  if (!ativos.length) return '';
  const quando = r => (r.freq === 'anual' ? `Todo ano, ${r.dia} de ${MESES_LONGOS[+String(r.inicio).slice(5) - 1]}` : `Todo dia ${r.dia}`) + (r.fim ? ` · até ${nomeMes(r.fim, true)}` : '');
  const linha = r => `<button class="banco-row" data-a="fixo" data-id="${esc(r.id)}"><span class="ini" style="--c:${corCat(r)}">${esc((r.descricao || '?').slice(0, 1).toUpperCase())}</span>
    <div class="op-t"><b>${esc(r.descricao)}</b><span>${quando(r)}${r.conta ? ' · ' + esc(nomeConta(contaDe(r.conta))) + (r.cartao ? ' · cartão' : '') : ''}</span></div>
    <span class="op-n ${r.tipo === 'receita' ? 'ent' : 'sai'}">${brl(r.valor, 0)}<small>${r.freq === 'anual' ? 'por ano' : temDescontos(r) ? 'líquido ' + brl(liquidoDe(r), 0) : 'padrão'}</small></span>${ic('chev', 'chev')}</button>`;
  const mensais = ativos.filter(r => r.freq !== 'anual'), anuais = ativos.filter(r => r.freq === 'anual');
  const rec = mensais.filter(r => r.tipo === 'receita'), des = mensais.filter(r => r.tipo !== 'receita');
  const soma = l => l.reduce((s, r) => s + (+r.valor || 0), 0);
  return `<section class="card" id="fixos">${maisCab('repeat', 'Fixos', brl(soma(rec) - soma(des), 0) + ' por mês')}
    ${maisLead('Entram sozinhos nos próximos meses, com o valor padrão. Toque para mudar o padrão ou parar.')}
    ${rec.length ? `<h3>Recebimentos · ${brl(soma(rec), 0)}</h3>${rec.map(linha).join('')}` : ''}
    ${des.length ? `<h3 style="margin-top:14px">Gastos · ${brl(soma(des), 0)}</h3>${des.map(linha).join('')}` : ''}
    ${anuais.length ? `<h3 style="margin-top:14px">Uma vez por ano</h3>${anuais.map(linha).join('')}` : ''}</section>`;
}
function cardIA() {
  const on = iaOn();
  const chaveIA = linhaChave('ia', on, 'Usar IA', on
    ? 'Ligado: aparecem Ler com IA (fatura, print, foto de papel e WhatsApp), Ler recibo no salário e Ler nas imagens; as dicas de economia conferem preços com a IA.'
    : 'Desligado: os botões de IA somem e as dicas não conferem preços. Vale para todos os aparelhos; nada do que já foi lançado muda.');
  const cab = `<section class="card" id="ia">${maisCab('ia', 'Leitura por IA')}
    ${maisLead('Lê faturas em PDF, prints, fotos de papel, textos do WhatsApp e recibos de pagamento, e prints do banco para cadastrar investimentos. Usa a integração de IA configurada no Home Assistant (Anthropic Claude, OpenAI, Google Gemini ou um modelo local); o app não guarda nenhuma chave.')}
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
  const fala = DEMO ? ['', 'Falar: na prévia, a fala é simulada.'] : !v ? ['manual', 'Falar: verificando o assistente de voz…']
    : v.pronta ? ['', `Falar: pronto, com ${esc(v.nome || 'a fala para texto do Home Assistant')}. O microfone fica no alto de cada tela.`] : ['manual', `Falar: ${esc(v.motivo || 'não está pronto.')}`];
  return cab + `<div class="status ${st[0]}">${st[1]}</div><div class="status ${fala[0]}" style="margin-top:-6px">${fala[1]}</div>
    <div class="campo"><label class="lbl" for="ia-ent">IA usada pelo app</label><select id="ia-ent" class="inp" data-ajuste-sel="ia_entidade">
      <option value="">Padrão do Home Assistant</option>${ents.map(e => `<option value="${esc(e.id)}"${e.id === S.d.ajustes.ia_entidade ? ' selected' : ''}>${esc(e.nome)}${e.imagens ? '' : ' (só texto)'}</option>`).join('')}</select></div>
    <button class="btn out" data-a="ia-verificar">${ic('refresh')}Verificar de novo</button>
    <p class="nota" style="margin:12px 0 0">Para ler imagem e PDF, a IA precisa aceitar anexos; Google Gemini, OpenAI e Anthropic aceitam. Se a IA não aceitar PDF, o app manda só o texto do arquivo.</p></section>`;
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
            <div class="conta-l"><input class="inp" data-fbc="pessoa" data-i="${i}" value="${esc(c.pessoa || '')}" placeholder="Nome, ex.: Diego" list="dl-pessoas" autocomplete="off" aria-label="Nome da pessoa">
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

/* ------------------------------------------------------------------ Mais */
/* ------------------------------------------------------------------ Mais: abas no alto, como no ResolvIA, no CronologIA e no InventarIA */
const MAIS_ABAS = [
  ['bancos', 'Bancos', 'bank'], ['caixa', 'Caixa', 'fluxo'], ['invest', 'Invest', 'trend'], ['integracoes', 'Integrações', 'blocks'],
  ['dados', 'Dados', 'archive'], ['aparencia', 'Aparência', 'palette'], ['opcoes', 'Opções', 'toggle-right'],
];
const maisAba = () => MAIS_ABAS.some(([k]) => k === S.ui.maisAba) ? S.ui.maisAba : 'bancos';
const iaOn = () => S.d.ajustes.ia !== false;
// cabeçalho de seção: o ícone num quadradinho no tom da cor do app e o título grande
// the header of a card: an icon tile (like the CronologIA and the ResolvIA), the title and, on the right, a number
const rotIc = (icone, tom = '') => `<span class="rot-ic ${tom}" aria-hidden="true">${ic(icone)}</span>`;
const maisCab = (icone, titulo, aside = '') => `<div class="mais-head"><span class="mais-ic" aria-hidden="true">${ic(icone)}</span><h2>${titulo}</h2>${aside ? `<b class="mais-aside">${aside}</b>` : ''}</div>`;
const maisLead = t => `<p class="painel-lead">${t}</p>`;
const chave = (k, on, rotulo) => `<button class="sw${on ? ' on' : ''}" data-a="ajuste" data-k="${k}" role="switch" aria-checked="${on}" aria-label="${esc(rotulo)}"></button>`;
const linhaChave = (k, on, titulo, texto) => `<div class="linha-sw"><div><b>${titulo}</b><span>${texto}</span></div>${chave(k, on, titulo)}</div>`;
// cores do app com nome, em forma de etiqueta (as mesmas do CronologIA e do ResolvIA; o azul é o do GerencIA)
const CORES_APP = [
  ['Vermelho', '#FF5A4F'], ['Coral', '#FF8A65'], ['Laranja', '#FFA23E'], ['Ouro', '#F2C14E'], ['Verde', '#8BD45F'], ['Menta', '#4ED3A6'],
  ['Turquesa', '#3CCBDA'], ['Azul', '#56AEFF'], ['Índigo', '#8F9BFF'], ['Lilás', '#B99BFF'], ['Rosa', '#FF77A9'], ['Grafite', '#B5B9C2'],
];
const TAG_SW = 'M8 0h20a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H8L0 13V7z', FURO_SW = 'M9.7 10a2.7 2.7 0 1 0-5.4 0a2.7 2.7 0 1 0 5.4 0z';
function corAppAtual() {
  const c = (corOk(S.d.ajustes.cor) || AJUSTES_PADRAO.cor).toUpperCase();
  const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const [r, g, b] = rgb(c);
  let melhor = null, dist = 1e9;
  for (const [, hex] of CORES_APP) { const [r2, g2, b2] = rgb(hex); const dd = Math.abs(r - r2) + Math.abs(g - g2) + Math.abs(b - b2); if (dd < dist) { dist = dd; melhor = hex; } }
  return dist <= 24 ? melhor : null;
}

function telaMais() {
  const aba = maisAba();
  const d = S.d;
  let status = ['', `GerencIA ${VERSAO}`];
  if (aba === 'bancos') {
    const cs = d.bancos.flatMap(b => b.contas || []);
    status = ['', d.bancos.length ? `${plural(d.bancos.length, 'banco', 'bancos')} · ${plural(cs.length, 'conta', 'contas')} · ${plural(cs.filter(c => c.cartao).length, 'cartão', 'cartões')}` : 'Nenhum banco ainda'];
  } else if (aba === 'invest') status = syncInfo();
  else if (aba === 'integracoes') status = !iaOn() ? ['manual', 'IA desligada'] : DEMO ? ['', 'IA simulada na prévia'] : !S.ia ? ['manual', 'Verificando a IA…'] : S.ia.pronta ? ['', 'IA do Home Assistant pronta'] : ['erro', S.ia.motivo || 'IA não está pronta'];
  const corpo = { bancos: maisBancos, caixa: maisCaixa, invest: maisInvest, integracoes: maisIntegracoes, dados: maisDados, aparencia: maisAparencia, opcoes: maisOpcoes }[aba]();
  return `${cabecalho('Mais', '', status)}
    <div class="mais-abas" role="tablist" aria-label="Seções de Mais">${MAIS_ABAS.map(([k, n, i]) =>
      `<button role="tab" class="${aba === k ? 'on' : ''}" aria-selected="${aba === k}" data-a="mais-aba" data-v="${k}">${ic(i, 'ic-s')}<span>${n}</span></button>`).join('')}</div>
    <div class="mais-painel" role="tabpanel" aria-label="${MAIS_ABAS.find(([k]) => k === aba)[1]}">${corpo}</div>
    <p class="foot"><b>GerencIA</b><br>v${VERSAO} · ${DEMO ? 'prévia do app do Home Assistant: as alterações ficam só nesta tela.' : 'seus dados ficam em arquivos abertos (JSON) dentro do Home Assistant.'}</p>`;
}

/* --------- Bancos */
function maisBancos() {
  const d = S.d;
  let h = `<section class="card" id="bancos">${maisCab('bank', 'Bancos e contas')}
    ${maisLead('Os bancos e corretoras, quem tem conta em cada um e quem tem cartão de crédito, com o dia em que a fatura fecha e vence. Cada banco ganha uma cor para as listas e os gráficos.')}`;
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
  return (fixos || `<section class="card" id="fixos">${maisCab('repeat', 'Fixos')}${maisLead('Salário, aluguel, assinaturas e o que mais se repete. Ao lançar, escolha Repetir: Todo mês ou Todo ano, e eles aparecem sozinhos nos próximos meses.')}
    <button class="btn out" data-a="lanc-novo" data-v="despesa">${ic('plus')}Lançar um fixo</button></section>`) + cardCategorias() + cardDicasMais();
}

/* --------- Invest: índices de mercado */
function maisInvest() {
  const I = S.d.indices;
  const quando = I.atualizado_em ? new Date(I.atualizado_em) : null;
  const st = I.erro ? ['erro', `${esc(I.erro)}. Usando os últimos valores.`]
    : I.fonte === 'manual' ? ['manual', `Valores digitados à mão${quando ? ' em ' + fData(quando) : ''}.`]
      : I.fonte === 'bcb' && quando ? ['', `Atualizado pelo Banco Central em ${fData(quando)} às ${quando.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}.`]
        : ['manual', 'Valores de partida (outubro de 2026). Toque em atualizar para buscar os de hoje.'];
  return `<section class="card" id="indices">${maisCab('trend', 'Índices de mercado')}
    ${maisLead('Usados para calcular quanto cada investimento rende. Toque num valor para mudar à mão.')}
    ${[['cdi', 'CDI', 'Taxa DI, ao ano'], ['selic', 'Selic', 'Meta do Copom, ao ano'], ['ipca', 'IPCA', 'Inflação dos últimos 12 meses'], ['tr', 'TR', 'Taxa referencial, ao mês (poupança)']].map(([k, n, s]) =>
      `<button class="idx-row" data-a="indice" data-v="${k}"><div><b>${n}</b><span>${s}</span></div><span class="vl">${pct(+I[k] || 0)}%</span>${ic('chev', 'chev')}</button>`).join('')}
    <div class="status ${st[0]}">${st[1]}</div>
    ${linhaChaveIdx(I)}
    <button class="btn out" data-a="indices-atualizar" style="margin-top:6px">${ic('refresh')}Atualizar agora</button></section>`;
}
const linhaChaveIdx = I => `<div class="linha-sw" style="margin-bottom:12px"><div><b>Atualizar sozinho</b><span>Busca no Banco Central a cada 12 horas.</span></div>
  <button class="sw${I.auto ? ' on' : ''}" data-a="indices-auto" role="switch" aria-checked="${!!I.auto}" aria-label="Atualizar sozinho"></button></div>`;

/* --------- Integrações: outros apps, IA, uso da IA e sensores */
function maisIntegracoes() {
  const a = S.d.ajustes;
  return cardOutrosApps(a) + cardIA() + (iaOn() ? cardUsoIA() : '') + `
    <section class="card" id="sensores">${maisCab('chart-column', 'Sensores no Home Assistant')}
      ${maisLead('Para painéis e automações: patrimônio, seu dinheiro, de terceiros, rendimento por mês, saldo em caixa, entradas e saídas do mês e as chamadas de IA de hoje.')}
      ${linhaChave('sensores', a.sensores === true, 'Criar os sensores', a.sensores === true
        ? 'Ligado: <code>sensor.gerencia_patrimonio</code>, <code>_meu</code>, <code>_terceiros</code>, <code>_rendimento_mensal</code>, <code>_saldo_caixa</code>, <code>_entradas_mes</code>, <code>_saidas_mes</code> e <code>_ia_hoje</code>. Atualizam a cada mudança e a cada 15 minutos.'
        : 'Desligado: o app não cria sensores no Home Assistant, e apaga os que tinha criado.')}
    </section>`;
}

/* --------- Uso da IA (igual ao do InventarIA): hoje, 7 dias e o mês, gráfico por dia e as últimas chamadas */
const USO_TIPO = { caixa: 'Ler lançamentos', invest: 'Ler investimentos', holerite: 'Ler recibo de pagamento', precos: 'Conferir preço de assinatura', fala: 'Falar', ler: 'Ler com IA' };
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
    const idsIA = [...Object.keys(u.month.entities || {}), ...Object.keys(u.week.entities || {}), S.d.ajustes.ia_entidade || ''];
    let ids = [...idsIA, ...idsIA.filter(Boolean).map(nomeIA)].join(' ').toLowerCase();
    if (!/google|gemini|openai|gpt|anthropic|claude/.test(ids)) {
      // sem chamada ainda: se todas as IAs do Home Assistant são do mesmo provedor, usa ele
      const ps = new Set(((S.ia && S.ia.entidades) || []).map(e => (`${e.id} ${e.nome}`.toLowerCase().match(/google|gemini|openai|gpt|anthropic|claude/) || [''])[0].replace('gemini', 'google').replace('gpt', 'openai').replace('claude', 'anthropic')).filter(Boolean));
      if (ps.size === 1) ids = [...ps][0];
    }
    const link = (href, t) => `<a href="${href}" target="_blank" rel="noopener noreferrer">${t}</a>`;
    const prov = /google|gemini/.test(ids) ? `Consumo exato do Gemini: no ${link('https://console.cloud.google.com/apis/dashboard', 'Google Cloud Console')}, abra APIs e serviços ativados e depois Generative Language API; o gráfico de tráfego mostra os pedidos e os erros 429 de cota. Os limites do plano grátis estão no ${link('https://aistudio.google.com/', 'Google AI Studio')}. A cota diária volta à meia-noite do horário do Pacífico, de madrugada no Brasil (4h ou 5h).`
      : /openai|gpt/.test(ids) ? `Consumo exato e custo da OpenAI: ${link('https://platform.openai.com/usage', 'platform.openai.com/usage')}.`
        : /anthropic|claude/.test(ids) ? `Consumo exato e custo da Anthropic: ${link('https://platform.claude.com/usage', 'Claude Console, Usage')}.`
          : 'O consumo exato e o custo ficam no painel do provedor da sua IA (Google, OpenAI, Anthropic...).';
    corpo = `<div class="uso-tiles">${tile('Hoje', u.today)}${tile('7 dias', u.week)}${tile('Este mês', u.month)}</div>
      <div class="uso-chart" role="group" aria-label="Chamadas de IA nos últimos 7 dias">${barras}</div>
      <div class="uso-dias" aria-hidden="true">${u.days.map(x => `<span>${x.day === hojeK ? 'hoje' : diaSem(x.day)}</span>`).join('')}</div>
      <p class="uso-cap" aria-live="polite">${diaLongo(sel.day)}: <b>${plural(sel.calls || 0, 'chamada', 'chamadas')}</b>${sel.errors ? `, ${sel.errors} com erro` : ''}${sel.quota ? `, ${sel.quota} sem cota` : ''}.</p>
      ${tipos.length ? `<ul class="uso-tipos" aria-label="Nos últimos 7 dias">${tipos.map(([k, n]) => `<li>${esc(USO_TIPO[k] || k)} <b>${n}</b></li>`).join('')}</ul>` : ''}
      <details class="uso-ult"><summary>${ic('chev', 'ic-s')}Últimas chamadas</summary><ul>${recentes || '<li>Nenhuma chamada ainda.</li>'}</ul></details>
      <p class="nota">${prov} A estimativa de tokens daqui conta só o texto; anexos (PDF e imagem) somam mais.</p>
      <p class="nota">${S.d.ajustes.sensores === true
        ? `No Home Assistant, o sensor <code>${esc(u.sensor || 'sensor.gerencia_ia_hoje')}</code> traz as chamadas de hoje, com erros, cota e tokens estimados, para pôr num painel ou numa automação (por exemplo, avisar quando passar de 50 no dia).`
        : `Para ter o sensor <code>${esc(u.sensor || 'sensor.gerencia_ia_hoje')}</code> no Home Assistant (as chamadas de hoje, com erros, cota e tokens), ligue <b>Sensores no Home Assistant</b>, logo abaixo.`}</p>`;
  }
  return `<section class="card" id="uso-ia">${maisCab('chart-column', 'Uso da IA')}
    ${maisLead('Cada leitura de fatura, print ou recibo, cada fala e cada conferência de preço é uma chamada para a IA do Home Assistant. O Home Assistant não informa tokens nem custo, então o GerencIA conta as chamadas e estima os tokens pelo tamanho do texto.')}
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
      ${maisLead('Baixe para guardar ou levar para outro programa. Os arquivos são abertos e legíveis.')}
      <ul class="opts">
        ${exp('lancamentos', 'Lançamentos (CSV)', 'Abre no Excel e no Google Planilhas, com um lançamento por linha: data, data no caixa, categoria, conta, valor e se está pago. Traz também os fixos e os descontos do salário.', 'Baixar CSV')}
        ${exp('csv', 'Investimentos (CSV)', 'Um investimento por linha, com banco, de quem é, rendimento, valor de hoje, quanto rende por mês e liquidez.', 'Baixar CSV')}
        ${exp('json', 'Dados completos (JSON)', 'Todos os campos, para backup ou para outro sistema.', 'Baixar JSON')}
        ${exp('zip', 'Tudo (ZIP)', 'Os dados completos, as duas planilhas e as imagens dos lançamentos e investimentos num arquivo só. É o arquivo que o Importar traz de volta.', 'Baixar ZIP')}
        <li id="relatorio"><div class="ot"><b>Relatório de patrimônio</b><span>Os investimentos por dono e por banco, com os totais, pronto para imprimir ou salvar em PDF.</span></div><button class="btn peq" data-a="relatorio">${ic('file', 'ic-s')}Abrir relatório</button></li>
      </ul></section>
    <section class="card" id="backup">${maisCab('archive', 'Backup na pasta share')}
      ${maisLead('Cria uma cópia completa em <code>share/gerencia</code>, que você acessa pela rede do Home Assistant. Os backups do próprio Home Assistant também incluem o GerencIA.')}
      <button class="btn pri" data-a="backup">${ic('archive')}Criar backup</button>${listaBk}</section>
    <section class="card" id="importar">${maisCab('upload', 'Importar')}
      ${maisLead('Traz os dados de um .zip ou .json exportado pelo GerencIA: lançamentos, fixos, investimentos, bancos e imagens. Antes de importar, o app guarda uma cópia do que existe hoje.')}
      <button class="btn" data-a="importar">${ic('upload')}Escolher arquivo</button></section>
    <section class="card" id="versoes">${maisCab('clock', 'Versões anteriores')}
      ${maisLead('O app guarda sozinho uma cópia dos dados a cada 10 minutos de uso e antes de importar ou restaurar, e fica com as 3 mais recentes. Se algo sair errado, volte para uma delas.')}
      <button class="btn" data-a="versoes">${ic('clock')}Ver versões</button></section>
    <section class="card" id="onde">${maisCab('database', 'Onde ficam os dados')}
      ${maisLead('Tudo fica em <code>/data/gerencia.json</code> e as imagens em <code>/data/fotos</code>, dentro do app, e entra no backup do Home Assistant. O app funciona sem internet: só os índices do Banco Central, a leitura por IA e as dicas de economia precisam dela. Valores e projeções são estimativas.')}</section>
    <section class="card" id="zerar">${maisCab('trash', 'Começar do zero')}
      ${maisLead('Apaga lançamentos, fixos, investimentos e bancos. Índices, categorias e preferências continuam. Uma cópia fica em Versões anteriores.')}
      <button class="btn perigo" data-a="apagar-tudo">${ic('trash')}Apagar tudo</button></section>`;
}
const tamanhoTxt = n => n >= 1048576 ? `${(n / 1048576).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} MB` : `${Math.max(1, Math.round(n / 1024))} KB`;

/* --------- Aparência */
function maisAparencia() {
  const a = S.d.ajustes, cor = corAppAtual();
  return `<section class="card" id="tema">${maisCab('contrast', 'Tema')}
      ${maisLead('Automático segue o modo claro ou escuro do Home Assistant. Vale para todos os aparelhos.')}
      <div class="seg temas" role="radiogroup" aria-label="Tema">${[['auto', 'Automático', 'smartphone'], ['claro', 'Claro', 'sun'], ['escuro', 'Escuro', 'moon']].map(([k, n, i]) =>
        `<button role="radio" aria-checked="${a.tema === k}" class="${a.tema === k ? 'on' : ''}" data-a="tema" data-v="${k}">${ic(i)}<span>${n}</span></button>`).join('')}</div></section>
    <section class="card" id="cor">${maisCab('palette', 'Cor do app')}
      ${maisLead('Muda os botões principais, a aba escolhida e os destaques. Vale para todos os aparelhos.')}
      <div class="tag-cores" role="radiogroup" aria-label="Cor do app">${CORES_APP.map(([n, hex]) =>
        `<button class="tsw${cor === hex ? ' on' : ''}" role="radio" aria-checked="${cor === hex}" style="--a:${hex}" data-a="cor" data-v="${hex}">
          <svg viewBox="-5 -5 40 30" aria-hidden="true"><path class="sw-ring" d="${TAG_SW}"/><path class="sw-gap" d="${TAG_SW}"/><path class="sw-fill" d="${TAG_SW}${FURO_SW}"/><path class="sw-check" d="m14.6 10.3 3.2 3.2 6.5-6.9"/></svg>
          <span>${n}</span></button>`).join('')}</div></section>`;
}

/* --------- Opções: o jeito de o app funcionar, para a casa toda */
function maisOpcoes() {
  const a = S.d.ajustes;
  return `<section class="card" id="op-inicio">${maisCab('home', 'Início')}
      ${linhaChave('dicas', a.dicas !== false, 'Dicas de economia', a.dicas !== false
        ? 'Ligado: o Início mostra quando uma assinatura tem plano anual mais barato e quando uma categoria passa da média. O preço é conferido na página oficial, com a IA.'
        : 'Desligado: o Início não mostra dicas e o app não confere preços de assinaturas.')}</section>
    <section class="card" id="op-caixa">${maisCab('fluxo', 'Fluxo de caixa')}
      ${linhaChave('prever_dia', a.prever_dia !== false, 'Prever o dia a dia', a.prever_dia !== false
        ? `Ligado: os próximos meses somam a média dos gastos que não são fixos nem parcelas (mercado, restaurante, combustível): ${brl(mediaVariaveis(), 0)} por mês.`
        : 'Desligado: os próximos meses mostram só fixos, parcelas e faturas já lançados.')}</section>
    <section class="card" id="op-invest">${maisCab('wallet', 'Investimentos')}
      ${linhaChave('corrigir', a.corrigir !== false, 'Corrigir valores pelo rendimento', 'Estima o valor de hoje a partir do último valor informado, contando dias úteis. Renda variável e dinheiro parado não mudam.')}</section>`;
}

/* ------------------------------------------------------------------ folhas (bottom sheets) */
let FOLHA = null;
function abrirFolha(montar, aoFechar) {
  fecharFolha(true);
  const root = $('#folhas');
  root.innerHTML = `<div class="veu" data-a="fechar"></div><section class="folha" role="dialog" aria-modal="true"></section>`;
  FOLHA = { montar, aoFechar };
  pintarFolha();
  requestAnimationFrame(() => { $('.veu', root).classList.add('on'); $('.folha', root).classList.add('on'); });
  try { history.pushState({ folha: 1 }, ''); } catch (e) { /* ok */ }
}
function pintarFolha() {
  if (!FOLHA) return;
  const el = $('#folhas .folha');
  const corpoAnt = $('.folha-corpo', el);
  const scroll = corpoAnt ? corpoAnt.scrollTop : 0;
  const f = FOLHA.montar();
  el.innerHTML = `<div class="folha-cab"><h2>${f.titulo}</h2>${f.cab || ''}<button class="icbtn" data-a="fechar" aria-label="Fechar">${ic('x')}</button></div>
    <div class="folha-corpo">${f.corpo}</div>${f.pe ? `<div class="folha-pe">${f.pe}</div>` : ''}`;
  $('.folha-corpo', el).scrollTop = scroll;
  if (f.depois) f.depois(el);
}
function fecharFolha(semHistorico) {
  if (!FOLHA) return;
  const root = $('#folhas');
  const veu = $('.veu', root), fo = $('.folha', root);
  const cb = FOLHA.aoFechar;
  FOLHA = null;
  if (veu) veu.classList.remove('on');
  if (fo) fo.classList.remove('on');
  setTimeout(() => { if (!FOLHA) root.innerHTML = ''; }, 240);
  if (!semHistorico) { try { if (history.state && history.state.folha) history.back(); } catch (e) { /* ok */ } }
  if (cb) cb();
}
window.addEventListener('popstate', () => { if (FOLHA) fecharFolha(true); });

function confirmar({ titulo, texto, botao, perigo, acao }) {
  abrirFolha(() => ({
    titulo,
    corpo: `<p style="margin:0;font-size:17px;color:var(--text-2)">${texto}</p>`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn ${perigo ? 'perigo' : 'pri'}" data-a="confirmar">${botao}</button>`,
  }));
  FOLHA.confirmar = acao;
}

/* --------- investimento */
let F = null;
function novoForm(base) {
  const t = tipoDe(base?.tipo || 'cdb');
  return Object.assign({
    id: null, nome: '', banco: S.d.bancos[0]?.id || '', tipo: t.id, valor: 0, data_valor: iso(hoje()),
    indexador: t.p.indexador, taxa: t.p.taxa, liquidez: t.p.liquidez, vencimento: '', titular: 'meu', terceiro: '', obs: '',
    obsAberta: false, idxEditado: false, dataEditada: false, bancosNovos: [], novoBanco: null, erros: {}, original: null, fotos: [],
  }, base || {});
}

function abrirInvestimento(id, preset) {
  const inv = id && S.d.investimentos.find(i => i.id === id);
  if (inv) {
    F = novoForm(Object.assign(clone(inv), { original: inv, obsAberta: !!inv.obs, idxEditado: true, dataEditada: true, bancosNovos: [], erros: {}, vencimento: inv.vencimento || '' }));
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
  AP = { inv: invId, valor: 0, data: iso(hoje()), destino: pend[0] ? pend[0].id : inv.titular === 'terceiros' ? 'nenhum' : 'novo', conta, erro: '' };
  abrirFolha(montarAplicar);
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
    corpo: `<div class="campo"><label for="ap-v">Quanto você aplicou</label><div class="pref grande${a.erro ? ' erro' : ''}"><span>R$</span><input id="ap-v" data-ap="valor" inputmode="numeric" value="${a.valor ? NF2.format(a.valor) : ''}" placeholder="0,00"></div>
        ${a.erro ? `<div class="msg-erro">${esc(a.erro)}</div>` : ''}
        <div class="ajuda" id="ap-ajuda">${aplicarAjuda(atual)}</div></div>
      <div class="campo"><label for="ap-data">Data</label><input id="ap-data" class="inp" type="date" data-ap="data" value="${esc(a.data)}" max="${iso(hoje())}"></div>
      <div class="campo"><div class="lbl">No caixa</div><div class="chips" style="margin:0">
        ${pend.map(l => chip(l.id, `Baixa no ${esc(l.descricao.toLowerCase().startsWith('aporte') ? 'aporte' : l.descricao)} de ${MESES_LONGOS[+String(l.competencia || l.data).slice(5, 7) - 1]} (${brl(+l.valor || 0, 0)})`)).join('')}
        ${chip('novo', pend.length ? 'Lançar à parte' : 'Lançar como aporte')}${chip('nenhum', 'Não lançar')}</div>
        <div class="ajuda">${pl ? `O aporte ${l2mes(pl)} fica aplicado com este valor, saindo de ${esc(nomeConta(contaDe(pl.conta)) || 'sem conta')}.`
          : a.destino === 'novo' ? 'Entra no caixa como uma saída do tipo Aporte, já aplicada.' : inv.titular === 'terceiros' ? 'Dinheiro de terceiros: não mexe no seu caixa.' : 'Só o valor do investimento muda; o caixa fica como está.'}</div>
        ${a.destino === 'novo' ? `<div class="chips" style="margin:10px 0 0">${contas().map(k => `<button class="chip${a.conta === k.id ? ' on' : ''}" data-a="ap-conta" data-v="${k.id}" style="--c:${corOk(k.cor) || '#B8B0B0'}"><span class="bol"></span>${esc(nomeConta(k))}</button>`).join('')}</div>` : ''}</div>`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="ap-ok">Aplicar${a.valor ? ' ' + brl(a.valor, 0) : ''}</button>`,
  };
}
const l2mes = l => `de ${MESES_LONGOS[+String(l.competencia || l.data).slice(5, 7) - 1]}`;
function aplicarAjuda(atual) {
  return AP.valor > 0 ? `O investimento passa de <b>${brl(atual)}</b> para <b>${brl(atual + AP.valor)}</b>.` : `Hoje ele está em ${brl(atual)}. O valor aplicado soma a isso.`;
}
function confirmarAplicar() {
  const a = AP, inv0 = S.d.investimentos.find(i => i.id === a.inv);
  if (!inv0) return;
  if (!(a.valor > 0)) { a.erro = 'Coloque o valor.'; pintarFolha(); return; }
  const novoValor = round2(valorHoje(inv0) + a.valor);
  const pl = aportesPendentes().find(l => l.id === a.destino);
  const hj = iso(hoje());
  persistir(d => {
    const inv = d.investimentos.find(i => i.id === a.inv);
    if (!inv) return;
    Object.assign(inv, { valor: novoValor, data_valor: hj, atualizado_em: new Date().toISOString() });
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

function montarFormInv() {
  const f = F;
  const ix = idxDe(f.indexador);
  const bancos = [...S.d.bancos, ...f.bancosNovos];
  const ps = pessoas();
  const err = k => f.erros[k] ? ' erro' : '';
  const msg = k => f.erros[k] ? `<div class="msg-erro">${f.erros[k]}</div>` : '';
  const titulo = f.id ? 'Editar investimento' : f.duplicando ? 'Duplicar investimento' : 'Novo investimento';
  const aplicar = f.id ? `<div class="inv-aplicar"><button class="btn out" data-a="inv-aplicar" data-v="${esc(f.id)}">${ic('plus', 'ic-s')}Aplicar mais</button>
    <span>Fez um aporte? Diga quanto: soma ao valor de hoje e, se quiser, entra no caixa.</span></div>` : '';
  let c = `${aplicar}${!f.id && !f.duplicando && !f.daIA ? tilesIA('invest') : ''}<div class="campo"><div class="lbl">De quem é este dinheiro?</div>
    <div class="seg dono-seg" style="margin-bottom:10px">
      <button class="${f.titular !== 'terceiros' ? 'on' : ''}" data-a="f-set" data-k="titular" data-v="meu">${ic('user', 'ic-s')}Meu</button>
      <button class="${f.titular === 'terceiros' ? 'on terc' : ''}" data-a="f-set" data-k="titular" data-v="terceiros">${ic('users', 'ic-s')}De terceiros</button></div>`;
  if (f.titular === 'terceiros') {
    c += `<input class="inp${err('terceiro')}" data-f="terceiro" value="${esc(f.terceiro)}" placeholder="De quem? Ex.: Mãe, Pedro, condomínio" autocomplete="off">${msg('terceiro')}`;
    if (ps.length) c += `<div class="chips" style="margin:10px 0 0">${ps.map(p => `<button class="chip${f.terceiro === p ? ' on' : ''}" data-a="f-set" data-k="terceiro" data-v="${esc(p)}">${esc(p)}</button>`).join('')}</div>`;
  }
  c += `</div>
    <div class="campo"><label for="f-nome">Nome</label><input id="f-nome" class="inp" data-f="nome" value="${esc(f.nome)}" placeholder="Ex.: CDB Inter 2028" autocomplete="off"></div>
    <div class="campo"><div class="lbl">Banco</div><div class="chips" style="margin:0">
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
        <div class="pref${err('valor')}"><span>R$</span><input id="f-valor" data-f="valor" inputmode="numeric" value="${f.valor ? NF2.format(f.valor) : ''}" placeholder="0,00"></div></div>
      <div class="campo" style="margin-bottom:6px"><label for="f-data">Valor em</label><input id="f-data" class="inp" type="date" data-f="data_valor" value="${esc(f.data_valor)}" max="${iso(hoje())}"></div></div>
    ${msg('valor')}<div class="ajuda" id="aj-valor" style="color:var(--muted);font-size:14.5px;margin-bottom:20px"></div>
    <div class="campo"><div class="lbl">Rendimento</div><div class="chips">${IDX.map(x =>
      `<button class="chip${f.indexador === x.id ? ' on' : ''}" data-a="f-idx" data-v="${x.id}">${x.nome}</button>`).join('')}</div>
      ${ix.taxa ? `<div class="pref${err('taxa')}">${ix.pre ? `<span>${ix.pre}</span>` : ''}<input data-f="taxa" inputmode="decimal" value="${f.taxa === '' || f.taxa == null ? '' : String(f.taxa).replace('.', ',')}" placeholder="${ix.ph}"><span>${ix.suf}</span></div>` : ''}
      ${msg('taxa')}<div class="ajuda" id="aj-taxa"></div></div>
    <div class="campo"><div class="lbl">Liquidez</div><div class="seg" style="margin:0">
      <button class="${f.liquidez === 'diaria' ? 'on' : ''}" data-a="f-set" data-k="liquidez" data-v="diaria">Diária</button>
      <button class="${f.liquidez !== 'diaria' ? 'on' : ''}" data-a="f-set" data-k="liquidez" data-v="vencimento">No vencimento</button></div></div>
    <div class="campo"><label for="f-venc">Vencimento <span style="color:var(--muted);font-weight:400">(opcional)</span></label>
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
    } else if (!o) t = 'Coloque o saldo de hoje; o app calcula o rendimento daqui para a frente.';
    av.innerHTML = t;
  }
}

function salvarInvestimento(eOutro) {
  const f = F;
  f.erros = {};
  const ix = idxDe(f.indexador);
  if (!(f.valor > 0)) f.erros.valor = 'Coloque o valor.';
  if (ix.taxa && (f.taxa === '' || f.taxa == null || isNaN(f.taxa))) f.erros.taxa = 'Coloque a taxa.';
  if (f.titular === 'terceiros' && !String(f.terceiro || '').trim()) f.erros.terceiro = 'Diga de quem é.';
  if (Object.keys(f.erros).length) { pintarFolha(); toast('Falta preencher ' + Object.keys(f.erros).length + (Object.keys(f.erros).length === 1 ? ' campo' : ' campos')); return; }
  const bancos = [...S.d.bancos, ...f.bancosNovos];
  const nomeBanco = bancos.find(b => b.id === f.banco)?.nome || '';
  const inv = {
    id: f.id || uid(),
    nome: (f.nome || '').trim() || `${tipoDe(f.tipo).nome}${nomeBanco ? ' ' + nomeBanco : ''}`,
    banco: f.banco || '', tipo: f.tipo, valor: Math.round(f.valor * 100) / 100, data_valor: f.data_valor || iso(hoje()),
    indexador: f.indexador, taxa: ix.taxa ? +f.taxa : 0, liquidez: f.liquidez, vencimento: f.vencimento || null,
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
      <div class="ajuda" style="color:var(--muted);font-size:14.5px;margin-top:8px">Ao mudar à mão, a atualização automática pelo Banco Central é desligada. Dá para religar em Mais.</div></div>`,
    pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="i-salvar" data-v="${k}">Salvar</button>`,
  }));
}

/* --------- versões */
function abrirVersoes() {
  let lista = null, erro = null;
  abrirFolha(() => ({
    titulo: 'Versões anteriores',
    corpo: erro ? `<p class="msg-erro">${esc(erro)}</p>` : lista == null ? '<p style="color:var(--muted)">Carregando…</p>'
      : !lista.length ? '<p style="color:var(--muted)">Ainda não há versões anteriores. Elas aparecem depois das primeiras alterações.</p>'
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
  ['investimentos', 'Invest', 'wallet'], ['mais', 'Mais', 'sliders'],
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
    ${link('mais', 'Mais', 'sliders')}</nav>`;
  const pb = new Map();
  for (const i of d.investimentos) pb.set(i.banco || '', (pb.get(i.banco || '') || 0) + valorHoje(i));
  const bancos = [...pb].sort((a, b) => b[1] - a[1]);
  if (bancos.length) {
    h += `<div class="side-h"><span>Bancos</span><small>${bancos.length}</small></div><div class="side-lista">${bancos.map(([id, v]) => {
      const b = bancoDe(id), on = naCarteira && u.banco === id && u.filtro === 'todos';
      return `<button class="side-item" data-a="lado-banco" data-v="${esc(id)}"${on ? ' aria-current="page"' : ''}><span class="side-tile" style="--c:${corOk(b?.cor) || 'var(--c0)'}">${esc((b?.nome || '?').slice(0, 1).toUpperCase())}</span><span class="sl-nome">${esc(b?.nome || 'Sem banco')}</span><span class="sl-num">${compacto(v)}</span></button>`;
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

function ajustarTextos() {
  $$('.stat-duo b, .inv-valor, .hl-n').forEach(el => {
    el.style.fontSize = '';
    let fs = parseFloat(getComputedStyle(el).fontSize), n = 0;
    while (el.scrollWidth > el.clientWidth + 1 && fs > 14 && n++ < 40) { fs -= 1.5; el.style.fontSize = fs + 'px'; }
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
  desenharGraficos();
  { const t = $('.mais-abas'), on = t && $('button.on', t); if (on) { const l = on.offsetLeft - 8, r = on.offsetLeft + on.offsetWidth + 8; if (l < t.scrollLeft) t.scrollLeft = l; else if (r > t.scrollLeft + t.clientWidth) t.scrollLeft = r - t.clientWidth; } }
  ajustarTextos();
  if (S.ui.tab === 'mais' && !S.ia && !DEMO && iaOn()) api.iaStatus().then(st => { S.ia = st; if (S.ui.tab === 'mais') render(); }).catch(() => {});
  if (S.ui.tab === 'mais' && maisAba() === 'integracoes' && iaOn() && !S.usoPedido && (!S.uso || Date.now() - (S.usoEm || 0) > 30000)) {
    S.usoPedido = true;
    api.iaUso().then(u => { S.uso = u; }).catch(() => { if (!S.uso) S.uso = { today: null, days: [] }; })
      .finally(() => { S.usoPedido = false; S.usoEm = Date.now(); if (S.ui.tab === 'mais') render(); });
  }
  if (S.ui.tab === 'mais' && maisAba() === 'dados' && S.backups == null && !S.bkPedido) {
    S.bkPedido = true;
    api.backups().then(b => { S.backups = b; }).catch(() => { S.backups = []; }).finally(() => { S.bkPedido = false; if (S.ui.tab === 'mais') render(); });
  }
  if (foco) { const el = $(`[data-ui="${foco}"]`); if (el) { el.focus(); try { el.setSelectionRange(pos, pos); } catch (e) { /* ok */ } } }
  if (FOLHA) pintarFolha();
}

function irPara(tab, ancora) {
  S.ui.tab = tab;
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
    case 'tab': irPara(v, el.dataset.ancora); break;
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
    case 'ap-destino': AP.destino = v; pintarFolha(); break;
    case 'ap-conta': AP.conta = v; pintarFolha(); break;
    case 'ap-ok': confirmarAplicar(); break;
    case 'pg-inv': PG.inv = v; PG.erroInv = ''; pintarFolha(); break;
    case 'lf-inv': LF.investimento = v; LF.erroInv = ''; delete LF.erros.investimento; pintarFolha(); break;
    case 'fatura-abrir': S.ui.faturaAberta = S.ui.faturaAberta === v ? null : v; render(); break;
    case 'fatura-pagar': pagarFatura(v); break;
    case 'cx-ajuste': abrirAjuste(); break;
    case 'aj-ok': confirmarAjuste(); break;
    case 'cx-modo': S.ui.cxModo = v; S.ui.cxSel = null; salvarUI(); render(); break;
    case 'cx-mes': S.ui.cxMes = +v === 0 ? null : addYm(mesCaixa(), +v); S.ui.faturaAberta = null; S.ui.cxSel = null; render(); break;
    case 'cx-filtro': S.ui.cxFiltro = v; salvarUI(); render(); break;
    case 'cx-periodo': S.ui.cxPeriodo = v; salvarUI(); render(); break;
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
    case 'aporte-ajustar': { const fx = aportesFixos(); if (fx.length === 1) abrirLancamento(`v:${fx[0].id}:${proximaYm(fx[0])}`); else { S.ui.maisAba = 'caixa'; irPara('mais', 'fixos'); } break; }
    case 'aporte-novo': novoAporte(); break;
    case 'dica-fora': persistir(d => { d.ajustes.dicas_fora = [...new Set([...(d.ajustes.dicas_fora || []), v])].slice(-200); }, 'Dica dispensada'); break;
    case 'dica-cat': S.ui.cxModo = 'categorias'; S.ui.cxCatTipo = 'despesa'; S.ui.cxMes = v; salvarUI(); irPara('caixa'); break;
    case 'dicas-conferir': if (S.dicas) S.dicas.conferindo = true; render(); carregarDicas(true); break;
    case 'dicas-voltar': persistir(d => { d.ajustes.dicas_fora = []; }, 'Dicas de volta'); break;
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
    case 'fala-ok': terminarFala(); break;
    case 'ia': if (!iaOn()) { toast('A IA está desligada. Para usar, ligue em Mais › Integrações.'); break; } abrirIA(v); break;
    case 'ia-de': if (!iaOn()) break; if (el.dataset.ini === 'voz' && !vozPronta()) break; abrirIA(v, el.dataset.ini); break;
    case 'ia-arq': escolherArquivo('image/*,application/pdf').then(iaPegarArquivo); break;
    case 'ia-arq-rm': IAS.arquivo = null; pintarFolha(); break;
    case 'ia-ler': iaLer(); break;
    case 'ia-voltar': IAS.etapa = 'entrada'; pintarFolha(); break;
    case 'ia-marca': { const it = IAS.itens[+el.dataset.i]; it.marcado = !it.marcado; pintarFolha(); break; }
    case 'ia-marca-inv': { const it = IAS.invs[+el.dataset.i]; it.marcado = !it.marcado; pintarFolha(); break; }
    case 'ia-salvar': salvarIA(); break;
    case 'iac-conta': IAS.conta = v; if (!contaDe(v)?.cartao) IAS.cartao = false; pintarFolha(); break;
    case 'iac-cartao': IAS.cartao = !!v; IAS.cartaoMexido = true; pintarFolha(); break;
    case 'iac-sit': IAS.situacao = v; pintarFolha(); break;
    case 'iac-futuras': IAS.futuras = !IAS.futuras; pintarFolha(); break;

    case 'iai-revisar': revisarItemInvest(+el.dataset.i); break;
    case 'ia-verificar': S.ia = null; render(); api.iaStatus().then(st => { S.ia = st; render(); toast(st.pronta ? 'IA pronta' : (st.motivo || 'IA não está pronta')); }).catch(e => toast(e.message)); break;
    case 'f-foto-add':
      escolherArquivo('image/*').then(async file => {
        if (!file) return;
        try { const n = await enviarFoto(file); F.fotos = [...(F.fotos || []), n]; pintarFolha(); } catch (e) { toast('Não consegui enviar a imagem. ' + e.message); }
      });
      break;
    case 'f-foto-rm': F.fotos = (F.fotos || []).filter(n => n !== v); pintarFolha(); break;
    case 'f-foto-ia': lerFotoNoForm(v); break;
    case 'foto-ver': verFoto(v); break;
    case 'inv': abrirInvestimento(id); break;
    case 'olho': S.oculto = !S.oculto; store.set('oculto', S.oculto); render(); break;
    case 'buscar':
      S.ui.tab = 'investimentos'; S.ui.invModo = 'carteira'; render(); window.scrollTo(0, 0);
      { const q = $('#q'); if (q) q.focus(); }
      break;
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
      confirmar({ titulo: 'Apagar exemplo?', texto: 'Os investimentos e bancos de demonstração saem. Depois é só cadastrar os seus.', botao: 'Apagar exemplo', perigo: true,
        acao: () => persistir(d => { d.bancos = []; d.investimentos = []; d.lancamentos = []; d.recorrencias = []; d.categorias = clone(CATEGORIAS_PADRAO); d.exemplo = false; d._hist = []; }, 'Exemplo apagado') });
      break;
    case 'apagar-tudo':
      confirmar({ titulo: 'Apagar tudo?', texto: `Saem ${plural(S.d.investimentos.length, 'investimento', 'investimentos')} e ${plural(S.d.bancos.length, 'banco', 'bancos')}. Uma cópia fica em Versões anteriores.`, botao: 'Apagar tudo', perigo: true,
        acao: () => persistir(d => { d.bancos = []; d.investimentos = []; d.lancamentos = []; d.recorrencias = []; d.exemplo = false; d._hist = []; }, 'Tudo apagado') });
      break;
    case 'tema': S.d.ajustes.tema = v; aplicarTema(); render(); persistir(d => { d.ajustes.tema = v; }); break;
    case 'cor': S.d.ajustes.cor = v; aplicarTema(); render(); persistir(d => { d.ajustes.cor = v; }); break;
    case 'ajuste': {
      const k = el.dataset.k; const nv = S.d.ajustes[k] === false;
      persistir(d => { d.ajustes[k] = nv; }).then(ok => {
        if (!ok) return;
        if (k === 'ia') { S.ia = null; S.uso = null; carregarVoz(); render(); }
        if (k === 'dicas') carregarDicas();
      });
      break;
    }
    case 'banco': abrirBanco(id); break;
    case 'banco-sug': abrirBanco(null, v); break;
    case 'indice': abrirIndice(v); break;
    case 'indices-auto': api.indices({ auto: !S.d.indices.auto }).then(d => { S.d = normalizar(d); render(); }).catch(e => toast(e.message)); break;
    case 'indices-atualizar':
      el.disabled = true; el.innerHTML = `${ic('refresh')}Buscando…`;
      api.atualizarIndices().then(d => { S.d = normalizar(d); render(); toast(S.d.indices.erro ? 'Banco Central não respondeu. Mantive os valores.' : 'Índices atualizados'); })
        .catch(e => { toast('Não consegui atualizar. ' + e.message); render(); });
      break;
    case 'relatorio': if (DEMO) toast('Na prévia o relatório não abre. No app, ele abre pronto para imprimir.'); else location.href = 'relatorio'; break;
    case 'demo-arq': toast('Na prévia os arquivos não são baixados.'); break;
    case 'backup': api.backup().then(r => { toast(`Backup salvo em ${r.pasta}/${r.arquivo}`); S.backups = null; render(); }).catch(e => toast('Não consegui criar o backup. ' + e.message)); break;
    case 'importar': $('#arquivo').click(); break;
    case 'versoes': abrirVersoes(); break;
    case 'restaurar':
      confirmar({ titulo: 'Restaurar esta versão?', texto: 'Os dados de agora são trocados por essa versão. Antes, o app guarda uma cópia do que existe hoje.', botao: 'Restaurar',
        acao: () => api.restaurar(v).then(d => { S.d = normalizar(d); render(); toast('Versão restaurada'); }).catch(e => toast(e.message)) });
      break;
    case 'fechar': fecharFolha(); break;
    case 'confirmar': { const fn = FOLHA && FOLHA.confirmar; fecharFolha(); if (fn) fn(); break; }

    // formulário de investimento
    case 'f-set':
      F[el.dataset.k] = v;
      if (el.dataset.k === 'titular' && v === 'terceiros') setTimeout(() => { const i = $('[data-f="terceiro"]'); if (i && !i.value) i.focus(); }, 30);
      pintarFolha(); break;
    case 'f-tipo': {
      F.tipo = v;
      const p = tipoDe(v).p;
      if (!F.id) { F.liquidez = p.liquidez; if (!F.idxEditado) { F.indexador = p.indexador; F.taxa = p.taxa; } }
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
  if (el.dataset.ias && IAS) { IAS[el.dataset.ias] = el.value; const b = $('[data-a="ia-ler"]'); if (b) b.disabled = !IAS.arquivo && !IAS.texto.trim(); return; }
  if (el.dataset.iai && IAS) { IAS.itens[+el.dataset.i][el.dataset.iai] = el.value; return; }
  if (el.dataset.ap && AP) {
    if (el.dataset.ap === 'valor') {
      const dig = el.value.replace(/\D/g, '').slice(0, 13);
      AP.valor = dig ? parseInt(dig, 10) / 100 : 0; AP.erro = '';
      el.value = dig ? NF2.format(AP.valor) : '';
      const inv = S.d.investimentos.find(i => i.id === AP.inv), aj = $('#ap-ajuda'), b = $('[data-a="ap-ok"]');
      if (inv && aj) aj.innerHTML = aplicarAjuda(valorHoje(inv));
      if (b) b.textContent = 'Aplicar' + (AP.valor ? ' ' + brl(AP.valor, 0) : '');
    } else AP.data = el.value;
    return;
  }
  if ((el.dataset.pg && PG) || (el.dataset.aj && AJ)) {
    const alvo = el.dataset.pg ? PG : AJ;
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
  if (el.dataset.ui === 'busca') { S.ui.busca = el.value; render(); return; }
});

// Arrastar para o lado troca de aba no celular, como no ResolvIA, no CronologIA e no InventarIA: Início ⇄ Caixa ⇄ Invest ⇄ Mais.
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
  const i = ABAS_ARRASTE.indexOf(S.ui.tab), j = i + d;
  if (i < 0 || j < 0 || j >= ABAS_ARRASTE.length) return;
  entraDe = d;
  irPara(ABAS_ARRASTE[j]);
}, { passive: true });
document.addEventListener('touchcancel', () => { arraste = null; }, { passive: true });

document.addEventListener('keydown', ev => {
  if (ev.key === 'Escape' && FOLHA) fecharFolha();
  if (ev.key === '/' && !FOLHA && !ev.ctrlKey && !ev.metaKey && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || '')) {
    const q = $('#q'); if (q) { ev.preventDefault(); q.focus(); } else if (S.d && S.d.investimentos.length) { ev.preventDefault(); irBuscar(); }
  }
  if (ev.key === 'Escape' && document.activeElement?.id === 'q' && S.ui.busca) { S.ui.busca = ''; render(); }
  if ((ev.key === 'Enter' || ev.key === ' ') && ev.target.matches && ev.target.matches('div[role="button"][data-a]')) { ev.preventDefault(); ev.target.click(); }
});
document.addEventListener('change', ev => {
  const el = ev.target;
  if (el.dataset.ajusteSel) { const k = el.dataset.ajusteSel, v = el.value; persistir(d => { d.ajustes[k] = v; }, 'IA escolhida').then(() => { S.ia = null; render(); }); }
});
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
window.addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(desenharGraficos, 150); });

/* ------------------------------------------------------------------ outros apps */
function cardOutrosApps(a) {
  const lig = a.integracao !== false, u = S.integracaoUltimo;
  let quando = '';
  if (u && u.em) {
    const dt = new Date(u.em), hj = iso(hoje()) === iso(dt);
    quando = `${esc(u.app)} usou ${hj ? 'hoje' : 'em ' + fData(dt)} às ${dt.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}.`;
  }
  return `<section class="card" id="outros-apps">${maisCab('calendar', 'Contas no CronologIA')}
    ${maisLead('O CronologIA, no mesmo Home Assistant, mostra as contas a pagar e as faturas na agenda, dá baixa com o Paguei e cria contas novas. A ligação é automática, pela pasta <code>share/gerencia</code>.')}
    ${linhaChave('integracao', lig, 'Usar a integração', lig ? 'Ligado: o CronologIA lê e dá baixa nas contas daqui.' : 'Desligado: o CronologIA não vê as contas do GerencIA.')}
    ${lig ? `<div class="status${quando ? '' : ' manual'}">${quando || 'Nenhum app conectou ainda.'}</div>` : ''}</section>`;
}
// Mudanças feitas por outro app (Paguei no CronologIA) aparecem sem precisar recarregar.
if (!DEMO) setInterval(() => {
  if (document.hidden || FOLHA || !S.d) return;
  fetch('api/rev', { cache: 'no-store' }).then(jsonOk).then(r => {
    S.integracaoUltimo = r.integracao_ultimo || null;
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
}
iniciar();
})();
