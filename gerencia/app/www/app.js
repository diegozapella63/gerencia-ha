/* GerencIA · controle de investimentos dentro do Home Assistant */
(() => {
'use strict';

const DEMO = !!window.GERENCIA_DEMO;
const VERSAO = '1.0.0';

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
const AJUSTES_PADRAO = { tema: 'auto', cor: '#56AEFF', corrigir: true, sensores: true };

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
const compacto = v => S.oculto ? '•••' : NFC.format(v);
const parseNum = t => { const s = String(t ?? '').trim().replace(/\s/g, ''); if (!s) return NaN; return parseFloat(s.includes(',') ? s.replace(/\./g, '').replace(',', '.') : s); };
const plural = (n, s, p) => `${n} ${n === 1 ? s : p}`;

/* ------------------------------------------------------------------ ícones */
const P = {
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
};
const ic = (n, c = 'ic') => `<svg class="${c}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[n] || ''}</svg>`;

/* ------------------------------------------------------------------ estado */
const S = {
  d: null,
  usuario: null,
  oculto: store.get('oculto', false),
  ui: Object.assign({
    tab: 'inicio', filtro: 'todos', pessoa: null, banco: null, busca: '', buscaAberta: false,
    gModo: 'evolucao', gEscopo: 'tudo', gAnos: 5, gAporte: 0, gIR: false, gAgrup: 'banco', gSel: null,
  }, store.get('ui', {})),
};
const salvarUI = () => {
  const { tab, filtro, gModo, gEscopo, gAnos, gAporte, gIR, gAgrup } = S.ui;
  store.set('ui', { tab, filtro, gModo, gEscopo, gAnos, gAporte, gIR, gAgrup });
};

function normalizar(d) {
  d = d || {};
  return {
    schema: 1, rev: d.rev || 0, exemplo: !!d.exemplo,
    bancos: Array.isArray(d.bancos) ? d.bancos : [],
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
  const d = normalizar({ exemplo: true, bancos, investimentos });
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
};
function apiDemo() {
  let d = null;
  const espera = ms => new Promise(r => setTimeout(r, ms));
  return {
    async state() { d = d || gerarExemplo(); return Object.assign(clone(d), { usuario: 'Diego' }); },
    async save(c) {
      if (c.rev !== d.rev) { const e = new Error('conflito'); e.conflito = true; e.d = clone(d); throw e; }
      for (const k of ['bancos', 'investimentos', 'ajustes', 'exemplo']) if (k in c) d[k] = c[k];
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
  };
}
const api = DEMO ? apiDemo() : apiServidor;

let fila = Promise.resolve();
function persistir(mut, ok) {
  fila = fila.then(async () => {
    const novo = clone(S.d);
    mut(novo);
    const corpo = { rev: novo.rev, bancos: novo.bancos, investimentos: novo.investimentos, ajustes: novo.ajustes, exemplo: novo.exemplo };
    if (novo._hist) { corpo.substituir_historico = true; corpo.historico = novo._hist; }
    try {
      S.d = normalizar(await api.save(corpo));
      render();
      if (ok) toast(ok);
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
function cabecalho(titulo, acoes = '') {
  const [cls, txt] = syncInfo();
  return `<header class="cab"><div class="cab-l"><p class="eyebrow"><span class="brand">Gerenc<span>IA</span></span>${S.usuario ? ' · Olá, ' + esc(S.usuario.split(' ')[0]) : ''}</p>
    <h1>${titulo}</h1></div>${acoes}</header>
    <p class="sync ${cls}"><span class="dot" aria-hidden="true"></span><span>${txt}</span></p>`;
}

// Código de autenticação do comprovante, como nos recibos de banco (muda com o total e o dia).
const autenticacao = v => (Math.round(v * 100) * 31 + +iso(hoje()).replace(/-/g, '')).toString(16).toUpperCase().slice(-6).padStart(6, '0');

// Comprovante saindo da fenda do caixa eletrônico: o destaque principal do Início.
function comprovante({ topo, data, val, palavra, linhas, texto, rodape }) {
  return `<div class="cpv-wrap"><div class="cpv-fenda" aria-hidden="true"></div><div class="cpv-papel"><div class="cpv">
    <div class="cpv-topo"><span>${topo}</span><span>${data}</span></div>
    <div class="cpv-val${palavra ? ' palavra' : ''}">${val}</div>
    <div class="cpv-linhas">${texto ? `<p class="cpv-texto">${texto}</p>` : linhas.map(([k, v]) => `<div class="cpv-linha"><span>${k}</span><b>${v}</b></div>`).join('')}</div>
    ${rodape ? `<div class="cpv-rodape"><span>${rodape[0]}</span><span>${rodape[1] || ''}</span></div>` : ''}
  </div></div></div>`;
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
  if (!d.investimentos.length) return telaBoasVindas();
  const h = hoje();
  const t = totais();
  const nBancos = new Set(d.investimentos.map(i => i.banco).filter(Boolean)).size;
  const olho = `<button class="icbtn" data-a="olho" aria-label="${S.oculto ? 'Mostrar' : 'Esconder'} valores">${ic(S.oculto ? 'eyeOff' : 'eye')}</button>`;
  let html = cabecalho('Início', `${olho}<button class="icbtn" data-a="buscar" aria-label="Buscar">${ic('search')}</button>`);
  if (d.exemplo) html += avisoExemplo();

  const linhas = [['Seu dinheiro', brl(t.meu, 0)]];
  if (t.terc > 0) linhas.push(['De terceiros', brl(t.terc, 0)]);
  linhas.push(['Rende por mês', brl(t.mes, 0)]);
  html += comprovante({
    topo: 'Patrimônio', data: fData(h), val: `<small>R$</small>${numf(t.total, 0)}`, linhas,
    rodape: [`${plural(d.investimentos.length, 'investimento', 'investimentos')} · ${plural(nBancos, 'banco', 'bancos')}`, 'AUT ' + autenticacao(t.total)],
  });

  // destaques
  const rows = [];
  rows.push(`<button class="hl-row" data-a="tab" data-v="graficos"><div><div class="hl-k">Rende por mês</div>
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
  const pr = projetar(alvo, 1, 0, false).pts;
  const ganho = pr[12].valor - pr[0].valor;
  rows.push(`<button class="hl-row" data-a="tab" data-v="graficos"><div><div class="hl-k">${meus.length ? 'Seu dinheiro em 1 ano' : 'Em 1 ano'}</div>
    <div class="hl-v">Sem novos aportes</div></div><div class="hl-n">${brl(pr[12].valor, 0)}<small>+${brl(ganho, 0)}</small></div></button>`);
  html += `<div class="hl">${rows.join('')}</div>`;

  // terceiros
  const ps = pessoas();
  if (ps.length) {
    html += `<div class="card flush"><div class="rot">Dinheiro de terceiros <b>${brl(t.terc, 0)}</b></div>`;
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
  const av = [];
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
  html += `<div class="card flush"><div class="rot">Avisos</div>${av.join('')}</div>`;
  return html;
}

function avisoExemplo() {
  return `<div class="exemplo"><b>Exemplo.</b> Estes valores são de demonstração. Quando quiser usar com os seus, apague o exemplo e comece a cadastrar.
    <div><button class="btn out peq" data-a="apagar-exemplo">Apagar exemplo</button></div></div>`;
}

function telaBoasVindas() {
  return `${cabecalho('Início')}
    ${comprovante({ topo: 'Bem-vindo', data: fData(hoje()), val: 'Gerenc<span style="opacity:.6">IA</span>', palavra: true, texto: 'Seu dinheiro, seus investimentos e quanto eles vão render.', rodape: ['Comprovante nº 0001', ''] })}
    <div class="comeco"><h2>Vamos começar</h2>
    <p>Cadastre o primeiro investimento com o valor de hoje e quanto ele rende. Já tem um backup? Importe o arquivo .zip e tudo volta.</p>
    <div class="btns">
      <button class="btn pri" data-a="novo">${ic('plus')}Cadastrar investimento</button>
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
      <button class="btn pri" data-a="novo">${ic('plus')}Cadastrar investimento</button></div>`;
  }
  const nMeu = porEscopo('meu').length, nTerc = porEscopo('terc').length;
  let html = cabecalho('Investimentos', `<button class="icbtn" data-a="buscar" aria-label="Buscar">${ic(u.buscaAberta ? 'x' : 'search')}</button>`);
  if (u.buscaAberta) html += `<div class="busca">${ic('search', 'ic-s')}<input id="q" data-ui="busca" value="${esc(u.busca)}" placeholder="Buscar por nome, banco ou pessoa" autocomplete="off"></div>`;
  html += `<div class="seg">
    <button class="${u.filtro === 'todos' ? 'on' : ''}" data-a="filtro" data-v="todos">Todos <small>${d.investimentos.length}</small></button>
    <button class="${u.filtro === 'meus' ? 'on' : ''}" data-a="filtro" data-v="meus">Meus <small>${nMeu}</small></button>
    <button class="${u.filtro === 'terc' ? 'on' : ''}" data-a="filtro" data-v="terc">Terceiros <small>${nTerc}</small></button></div>`;
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
  html += l.length ? l.map(x => cardInv(x.i, x.v)).join('') : '<div class="vazio">Nenhum investimento com esse filtro.</div>';
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

/* ------------------------------------------------------------------ Gráficos */
function telaGraf() {
  const u = S.ui, d = S.d;
  let html = cabecalho('Gráficos', S.oculto ? `<button class="icbtn" data-a="olho" aria-label="Mostrar valores">${ic('eyeOff')}</button>` : '');
  if (!d.investimentos.length) return html + '<div class="vazio">Cadastre um investimento para ver os gráficos.</div>';
  html += `<div class="seg"><button class="${u.gModo === 'evolucao' ? 'on' : ''}" data-a="g" data-k="gModo" data-v="evolucao">${ic('trend', 'ic-s')}Evolução</button>
    <button class="${u.gModo === 'composicao' ? 'on' : ''}" data-a="g" data-k="gModo" data-v="composicao">${ic('wallet', 'ic-s')}Dinheiro atual</button></div>`;
  const temTerc = porEscopo('terc').length > 0;
  if (temTerc) {
    html += `<div class="chips">${[['tudo', 'Tudo'], ['meu', 'Só o meu'], ['terc', 'De terceiros']].map(([k, n]) =>
      `<button class="chip${u.gEscopo === k ? ' on' : ''}" data-a="g" data-k="gEscopo" data-v="${k}">${n}</button>`).join('')}</div>`;
  } else if (u.gEscopo !== 'tudo') u.gEscopo = 'tudo';
  const lista = porEscopo(u.gEscopo);
  if (!lista.length) return html + '<div class="vazio">Nada nesse filtro.</div>';
  return html + (u.gModo === 'composicao' ? grafComposicao(lista) : grafEvolucao(lista));
}

let CACHE = {};
function grafEvolucao(lista) {
  const u = S.ui;
  const pj = projetar(lista, u.gAnos, +u.gAporte || 0, u.gIR);
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
      <span><i class="k" style="--kc:var(--c0)"></i>${+u.gAporte ? 'Investido + aportes' : 'Valor investido'}</span>
      <span><i class="k" style="--kc:var(--c2)"></i>Em dinheiro de hoje</span>
    </div></div>`;
  html += `<div class="ctrl"><div class="lbl">Horizonte</div><div class="chips">${[1, 2, 5, 10].map(a =>
    `<button class="chip${u.gAnos === a ? ' on' : ''}" data-a="g" data-k="gAnos" data-v="${a}">${a === 1 ? '1 ano' : a + ' anos'}</button>`).join('')}</div>
    <div class="lbl">Aporte por mês</div>
    <div class="pref" style="max-width:260px"><span>R$</span><input id="aporte" data-ui="gAporte" inputmode="numeric" value="${+u.gAporte ? NF2.format(+u.gAporte) : ''}" placeholder="0,00"></div>
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
    const x = ev.clientX - r.left;
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
  let html = `<div class="chips">${opts.map(([k, n]) => `<button class="chip${u.gAgrup === k ? ' on' : ''}" data-a="g" data-k="gAgrup" data-v="${k}">${n}</button>`).join('')}</div>`;
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

/* ------------------------------------------------------------------ Mais */
function telaMais() {
  const d = S.d, a = d.ajustes, I = d.indices;
  let html = cabecalho('Mais');
  const temaDesc = { auto: 'Segue o modo claro/escuro do Home Assistant.', claro: 'Sempre claro.', escuro: 'Sempre escuro.' }[a.tema] || '';
  html += `<div class="card"><div class="rot">Aparência</div><h3>Tema</h3>
    <div class="seg">${[['auto', 'Automático', 'auto'], ['claro', 'Claro', 'sun'], ['escuro', 'Escuro', 'moon']].map(([k, n, i]) =>
      `<button class="${a.tema === k ? 'on' : ''}" data-a="tema" data-v="${k}">${ic(i, 'ic-s')}${n}</button>`).join('')}</div>
    <p class="desc">${temaDesc}</p><div class="sep"></div><h3>Cor do app</h3>
    <div class="cores">${PALETA.map(c => `<button class="cor${(a.cor || '').toUpperCase() === c ? ' on' : ''}" style="--c:${c}" data-a="cor" data-v="${c}" aria-label="Cor ${c}">${(a.cor || '').toUpperCase() === c ? ic('check') : ''}</button>`).join('')}</div></div>`;

  // bancos
  html += `<div class="card" id="bancos"><div class="rot">Bancos</div>`;
  if (d.bancos.length) {
    for (const b of d.bancos) {
      const l = d.investimentos.filter(i => i.banco === b.id);
      const v = l.reduce((s, i) => s + valorHoje(i), 0);
      html += `<button class="banco-row" data-a="banco" data-id="${b.id}"><span class="ini" style="--c:${corOk(b.cor) || '#B8B0B0'}">${esc((b.nome || '?').slice(0, 1).toUpperCase())}</span>
        <div class="op-t"><b>${esc(b.nome)}</b><span>${l.length ? `${plural(l.length, 'investimento', 'investimentos')} · ${brl(v, 0)}` : 'Nenhum investimento'}${b.obs ? ' · ' + esc(b.obs) : ''}</span></div>${ic('chev', 'chev')}</button>`;
    }
  } else {
    html += `<p class="desc">Cadastre os bancos e corretoras onde o dinheiro está. Cada um ganha uma cor para aparecer nas listas e nos gráficos.</p>`;
  }
  html += `<button class="btn out larga" data-a="banco" style="margin-top:14px">${ic('plus')}Cadastrar banco</button>`;
  const sug = BANCOS_COMUNS.filter(n => !d.bancos.some(b => (b.nome || '').toLowerCase() === n.toLowerCase())).slice(0, 10);
  if (sug.length) html += `<div class="ctrl"><div class="lbl">Toque para cadastrar</div><div class="chips">${sug.map(n => `<button class="chip" data-a="banco-sug" data-v="${esc(n)}">+ ${esc(n)}</button>`).join('')}</div></div>`;
  html += `</div>`;

  // índices
  const quando = I.atualizado_em ? new Date(I.atualizado_em) : null;
  const st = I.erro ? ['erro', `${esc(I.erro)}. Usando os últimos valores.`]
    : I.fonte === 'manual' ? ['manual', `Valores digitados à mão${quando ? ' em ' + fData(quando) : ''}.`]
      : I.fonte === 'bcb' && quando ? ['', `Atualizado pelo Banco Central em ${fData(quando)} às ${quando.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}.`]
        : ['manual', 'Valores de partida (outubro de 2026). Toque em atualizar para buscar os de hoje.'];
  html += `<div class="card" id="indices"><div class="rot">Índices de mercado</div>
    <p class="desc">Usados para calcular quanto cada investimento rende. Toque num valor para mudar à mão.</p>
    ${[['cdi', 'CDI', 'Taxa DI, ao ano', '% a.a.'], ['selic', 'Selic', 'Meta do Copom, ao ano', '% a.a.'], ['ipca', 'IPCA', 'Inflação dos últimos 12 meses', '%'], ['tr', 'TR', 'Taxa referencial, ao mês (poupança)', '% a.m.']].map(([k, n, s]) =>
      `<button class="idx-row" data-a="indice" data-v="${k}"><div><b>${n}</b><span>${s}</span></div><span class="vl">${pct(+I[k] || 0)}%</span>${ic('chev', 'chev')}</button>`).join('')}
    <div class="status ${st[0]}">${st[1]}</div>
    <div class="linha-sw" style="margin-bottom:16px"><div><b>Atualizar sozinho</b><span>Busca no Banco Central a cada 12 horas.</span></div>
      <button class="sw${I.auto ? ' on' : ''}" data-a="indices-auto" aria-label="Atualizar sozinho"></button></div>
    <button class="btn out" data-a="indices-atualizar">${ic('refresh')}Atualizar agora</button></div>`;

  // ajustes
  html += `<div class="card"><div class="rot">Cálculos</div>
    <div class="linha-sw"><div><b>Corrigir valores pelo rendimento</b><span>Estima o valor de hoje a partir do último valor informado. Renda variável e dinheiro parado não mudam.</span></div>
      <button class="sw${a.corrigir !== false ? ' on' : ''}" data-a="ajuste" data-k="corrigir" aria-label="Corrigir valores"></button></div>
    <div class="sep"></div>
    <div class="linha-sw"><div><b>Sensores no Home Assistant</b><span><code>sensor.gerencia_patrimonio</code>, <code>_meu</code>, <code>_terceiros</code> e <code>_rendimento_mensal</code>, para painéis e automações.</span></div>
      <button class="sw${a.sensores !== false ? ' on' : ''}" data-a="ajuste" data-k="sensores" aria-label="Sensores"></button></div></div>`;

  // dados
  const exp = (fmt, nome) => DEMO
    ? `<button class="btn" data-a="demo-arq">${ic('download')}${nome}</button>`
    : `<a class="btn" href="api/export/${fmt}" download>${ic('download')}${nome}</a>`;
  html += `<div class="card"><div class="rot">Dados</div>
    <div class="dado"><h4>Exportar</h4><p>Baixe para abrir no Excel, guardar ou levar para outro programa. Os arquivos são abertos e legíveis.</p>
      <div class="btns">${exp('csv', 'Planilha (CSV)')}${exp('json', 'JSON')}${exp('zip', 'Tudo (ZIP)')}</div></div>
    <div class="dado"><h4>Relatório de patrimônio</h4><p>Lista por dono e por banco, pronta para imprimir ou salvar em PDF.</p>
      <button class="btn" data-a="relatorio">${ic('file')}Abrir relatório</button></div>
    <div class="dado"><h4>Backup na pasta share</h4><p>Cria uma cópia completa em <code>share/gerencia</code>, que você acessa pela rede do Home Assistant. Os backups do próprio Home Assistant também incluem o GerencIA.</p>
      <button class="btn pri" data-a="backup">${ic('archive')}Criar backup</button></div>
    <div class="dado"><h4>Importar backup ou JSON</h4><p>Traz os dados de um .zip ou .json exportado pelo app. Antes de importar, o app guarda uma cópia do que existe hoje.</p>
      <button class="btn" data-a="importar">${ic('upload')}Escolher arquivo</button></div>
    <div class="dado"><h4>Versões anteriores</h4><p>O app guarda sozinho uma cópia a cada 10 minutos de uso. Se algo sair errado, volte para uma versão anterior.</p>
      <button class="btn" data-a="versoes">${ic('clock')}Ver versões</button></div>
    <div class="dado"><h4>Começar do zero</h4><p>Apaga investimentos e bancos. Índices e preferências continuam.</p>
      <button class="btn perigo" data-a="apagar-tudo">${ic('trash')}Apagar tudo</button></div></div>`;

  html += `<div class="card"><div class="rot">Sobre</div><p class="sobre"><b>GerencIA ${VERSAO}.</b> Os dados ficam em <code>gerencia.json</code>, dentro do app.
    Funciona sem internet; só a atualização dos índices usa a internet, direto do Banco Central. Valores e projeções são estimativas, antes do imposto de renda quando não indicado.</p></div>`;
  return html;
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
    obsAberta: false, idxEditado: false, dataEditada: false, bancosNovos: [], novoBanco: null, erros: {}, original: null,
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

function montarFormInv() {
  const f = F;
  const ix = idxDe(f.indexador);
  const bancos = [...S.d.bancos, ...f.bancosNovos];
  const ps = pessoas();
  const err = k => f.erros[k] ? ' erro' : '';
  const msg = k => f.erros[k] ? `<div class="msg-erro">${f.erros[k]}</div>` : '';
  const titulo = f.id ? 'Editar investimento' : f.duplicando ? 'Duplicar investimento' : 'Novo investimento';
  let c = `<div class="campo"><div class="lbl">De quem é este dinheiro?</div>
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
    obs: (f.obs || '').trim(), criado_em: f.original?.criado_em || new Date().toISOString(), atualizado_em: new Date().toISOString(),
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

/* --------- banco */
let FB = null;
function abrirBanco(id, nome) {
  const b = id && S.d.bancos.find(x => x.id === id);
  const usadas = S.d.bancos.map(x => x.cor);
  FB = b ? clone(b) : { id: null, nome: nome || '', cor: CORES_BANCO.find(c => !usadas.includes(c)) || CORES_BANCO[0], obs: '' };
  FB.erro = '';
  abrirFolha(() => {
    const n = FB.id ? S.d.investimentos.filter(i => i.banco === FB.id).length : 0;
    return {
      titulo: FB.id ? 'Editar banco' : 'Novo banco',
      cab: FB.id ? `<button class="icbtn" data-a="b-excluir" aria-label="Excluir" style="color:var(--danger)">${ic('trash')}</button>` : '',
      corpo: `<div class="campo"><label for="b-nome">Nome</label><input id="b-nome" class="inp${FB.erro ? ' erro' : ''}" data-fb="nome" value="${esc(FB.nome)}" placeholder="Ex.: Nubank, XP, Sicredi" list="dl-b" autocomplete="off">
        <datalist id="dl-b">${BANCOS_COMUNS.map(x => `<option value="${esc(x)}">`).join('')}</datalist>${FB.erro ? `<div class="msg-erro">${FB.erro}</div>` : ''}</div>
        <div class="campo"><div class="lbl">Cor</div><div class="cores p">${PALETA.map(c => `<button class="cor${FB.cor === c ? ' on' : ''}" style="--c:${c}" data-a="b-cor" data-v="${c}" aria-label="Cor ${c}">${FB.cor === c ? ic('check', 'ic-s') : ''}</button>`).join('')}</div></div>
        <div class="campo"><label for="b-obs">Observação <span style="color:var(--muted);font-weight:400">(opcional)</span></label>
          <input id="b-obs" class="inp" data-fb="obs" value="${esc(FB.obs || '')}" placeholder="Agência, conta, gerente…" autocomplete="off"></div>
        ${n ? `<p style="color:var(--muted);margin:0">${plural(n, 'investimento usa', 'investimentos usam')} este banco.</p>` : ''}`,
      pe: `<button class="btn" data-a="fechar">Cancelar</button><button class="btn pri" data-a="b-salvar">Salvar</button>`,
    };
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
  ['inicio', 'Início', 'home'], ['investimentos', 'Investimentos', 'wallet'], ['add', 'Adicionar', 'plus'],
  ['graficos', 'Gráficos', 'chart'], ['mais', 'Mais', 'sliders'],
];
function pintarNav() {
  $('#nav .in').innerHTML = ABAS.map(([k, n, i]) => k === 'add'
    ? `<button class="add" data-a="novo" aria-label="Adicionar investimento"><span class="pill">${ic('plus')}</span>${n}</button>`
    : `<button class="${S.ui.tab === k ? 'on' : ''}" data-a="tab" data-v="${k}" ${S.ui.tab === k ? 'aria-current="page"' : ''}>${ic(i)}${n}</button>`).join('');
}

function ajustarTextos() {
  $$('.cpv-val, .stat-duo b, .inv-valor, .hl-n').forEach(el => {
    el.style.fontSize = '';
    let fs = parseFloat(getComputedStyle(el).fontSize), n = 0;
    while (el.scrollWidth > el.clientWidth + 1 && fs > 14 && n++ < 40) { fs -= 1.5; el.style.fontSize = fs + 'px'; }
  });
}
try { document.fonts.ready.then(() => { ajustarTextos(); if (S.ui.tab === 'graficos') desenharEvolucao(); }); } catch (e) { /* ok */ }

function render() {
  if (!S.d) return;
  aplicarTema();
  const telas = { inicio: telaInicio, investimentos: telaInvest, graficos: telaGraf, mais: telaMais };
  const foco = document.activeElement && document.activeElement.dataset && document.activeElement.dataset.ui;
  const pos = foco ? document.activeElement.selectionStart : null;
  $('#app').innerHTML = (telas[S.ui.tab] || telaInicio)();
  pintarNav();
  if (S.ui.tab === 'graficos' && S.ui.gModo !== 'composicao') desenharEvolucao();
  ajustarTextos();
  if (foco) { const el = $(`[data-ui="${foco}"]`); if (el) { el.focus(); try { el.setSelectionRange(pos, pos); } catch (e) { /* ok */ } } }
  if (FOLHA) pintarFolha();
}

function irPara(tab, ancora) {
  S.ui.tab = tab;
  salvarUI();
  render();
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
    case 'novo': abrirInvestimento(null, S.ui.tab === 'investimentos' && S.ui.filtro === 'terc' && S.ui.pessoa ? { titular: 'terceiros', terceiro: S.ui.pessoa } : null); break;
    case 'inv': abrirInvestimento(id); break;
    case 'olho': S.oculto = !S.oculto; store.set('oculto', S.oculto); render(); break;
    case 'buscar':
      if (S.ui.tab !== 'investimentos') { S.ui.tab = 'investimentos'; S.ui.buscaAberta = true; }
      else { S.ui.buscaAberta = !S.ui.buscaAberta; if (!S.ui.buscaAberta) S.ui.busca = ''; }
      render(); window.scrollTo(0, 0);
      if (S.ui.buscaAberta) { const q = $('#q'); if (q) q.focus(); }
      break;
    case 'filtro': S.ui.filtro = v; S.ui.pessoa = null; salvarUI(); render(); break;
    case 'pessoa-f': S.ui.pessoa = v || null; render(); break;
    case 'banco-f': S.ui.banco = v || null; render(); break;
    case 'pessoa': S.ui.filtro = 'terc'; S.ui.pessoa = v; S.ui.banco = null; irPara('investimentos'); break;
    case 'graf-comp': S.ui.gModo = 'composicao'; S.ui.gAgrup = v; S.ui.gEscopo = 'tudo'; irPara('graficos'); break;
    case 'g': {
      const k = el.dataset.k;
      if (k === 'gAnos') S.ui.gAnos = +v;
      else if (k === 'gIR') S.ui.gIR = !!v;
      else if (k === 'gSel') S.ui.gSel = S.ui.gSel === v ? null : v;
      else { S.ui[k] = v; if (k === 'gAgrup') S.ui.gSel = null; }
      salvarUI(); render(); break;
    }
    case 'carregar-exemplo': {
      const ex = gerarExemplo();
      persistir(d => { d.bancos = ex.bancos; d.investimentos = ex.investimentos; d.exemplo = true; d._hist = ex.historico; }, 'Exemplo carregado');
      break;
    }
    case 'apagar-exemplo':
      confirmar({ titulo: 'Apagar exemplo?', texto: 'Os investimentos e bancos de demonstração saem. Depois é só cadastrar os seus.', botao: 'Apagar exemplo', perigo: true,
        acao: () => persistir(d => { d.bancos = []; d.investimentos = []; d.exemplo = false; d._hist = []; }, 'Exemplo apagado') });
      break;
    case 'apagar-tudo':
      confirmar({ titulo: 'Apagar tudo?', texto: `Saem ${plural(S.d.investimentos.length, 'investimento', 'investimentos')} e ${plural(S.d.bancos.length, 'banco', 'bancos')}. Uma cópia fica em Versões anteriores.`, botao: 'Apagar tudo', perigo: true,
        acao: () => persistir(d => { d.bancos = []; d.investimentos = []; d.exemplo = false; d._hist = []; }, 'Tudo apagado') });
      break;
    case 'tema': S.d.ajustes.tema = v; aplicarTema(); render(); persistir(d => { d.ajustes.tema = v; }); break;
    case 'cor': S.d.ajustes.cor = v; aplicarTema(); render(); persistir(d => { d.ajustes.cor = v; }); break;
    case 'ajuste': { const k = el.dataset.k; const nv = S.d.ajustes[k] === false; persistir(d => { d.ajustes[k] = nv; }); break; }
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
    case 'backup': api.backup().then(r => toast(`Backup salvo em ${r.pasta}/${r.arquivo}`)).catch(e => toast('Não consegui criar o backup. ' + e.message)); break;
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
    case 'b-salvar': {
      const nome = (FB.nome || '').trim();
      if (!nome) { FB.erro = 'Dê um nome ao banco.'; pintarFolha(); break; }
      if (S.d.bancos.some(b => b.id !== FB.id && b.nome.toLowerCase() === nome.toLowerCase())) { FB.erro = 'Já existe um banco com esse nome.'; pintarFolha(); break; }
      const b = { id: FB.id || 'b-' + uid(), nome, cor: FB.cor, obs: (FB.obs || '').trim() };
      persistir(d => { const k = d.bancos.findIndex(x => x.id === b.id); if (k >= 0) d.bancos[k] = b; else d.bancos.push(b); }, FB.id ? 'Banco salvo' : 'Banco cadastrado')
        .then(ok => { if (ok) fecharFolha(); });
      break;
    }
    case 'b-excluir': {
      const alvo = FB.id, n = S.d.investimentos.filter(i => i.banco === alvo).length;
      confirmar({ titulo: 'Excluir banco?', texto: n ? `${plural(n, 'investimento fica', 'investimentos ficam')} sem banco. Dá para escolher outro depois.` : 'O banco sai da lista.', botao: 'Excluir', perigo: true,
        acao: () => persistir(d => { d.bancos = d.bancos.filter(b => b.id !== alvo); d.investimentos.forEach(i => { if (i.banco === alvo) i.banco = ''; }); }, 'Banco excluído') });
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
  if (el.dataset.ui === 'busca') { S.ui.busca = el.value; render(); return; }
  if (el.dataset.ui === 'gAporte') {
    const dig = el.value.replace(/\D/g, '').slice(0, 11);
    S.ui.gAporte = dig ? parseInt(dig, 10) / 100 : 0;
    el.value = dig ? NF2.format(S.ui.gAporte) : '';
    clearTimeout(window.__ap); window.__ap = setTimeout(() => { salvarUI(); render(); }, 350);
  }
});

document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && FOLHA) fecharFolha(); });

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
window.addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { if (S.ui.tab === 'graficos') desenharEvolucao(); }, 150); });

/* ------------------------------------------------------------------ início */
async function iniciar() {
  pintarNav();
  try {
    const st = await api.state();
    S.usuario = st.usuario || null;
    S.d = normalizar(st);
  } catch (e) {
    $('#app').innerHTML = `<div class="vazio">Não consegui abrir os dados.<br>${esc(e.message)}<br><br><button class="btn" onclick="location.reload()">Tentar de novo</button></div>`;
    return;
  }
  if (!['inicio', 'investimentos', 'graficos', 'mais'].includes(S.ui.tab)) S.ui.tab = 'inicio';
  S.ui.busca = ''; S.ui.buscaAberta = false; S.ui.gSel = null;
  render();
}
iniciar();
})();
