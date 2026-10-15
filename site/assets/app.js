/* UK Public Money: shared site code. No dependencies, no build step.
   Rules: data is rendered with textContent only (never innerHTML); external links must be https;
   every displayed number links to its provenance record (popover + check.html). */
(function () {
  'use strict';

  const CFG = Object.assign({ apiBase: 'api/v1', checkHosts: [] }, window.UKPM_CONFIG || {});
  const API = String(CFG.apiBase).replace(/\/+$/, '');
  const SVGNS = 'http://www.w3.org/2000/svg';
  const PROV_RE = /^([a-z][a-z0-9_]*)\.([0-9a-f]{6,64})$/;
  const SERIES_RE = /^[a-z0-9_]+(\.[a-z0-9_]+)+$/;
  const BASES = ['nominal', 'real', 'pct_gdp'];

  /* ---------- safe DOM helpers ---------- */
  function safeHref(v) {
    if (v == null) return null;
    const s = String(v).trim();
    if (s === '' || /[\x00-\x20]/.test(s)) return null;
    if (/^[a-z][a-z0-9+.-]*:/i.test(s) || s.startsWith('//')) {
      let u;
      try { u = new URL(s); } catch (e) { return null; }
      if (u.protocol !== 'https:') return null;
      if (CFG.checkHosts.length && !CFG.checkHosts.includes(u.hostname)) return null;
      return u.href;
    }
    return s; // relative, same origin
  }
  function append(n, kids) {
    for (const k of kids.flat(Infinity)) {
      if (k == null || k === false) continue;
      n.appendChild(k instanceof Node ? k : document.createTextNode(String(k)));
    }
    return n;
  }
  function setAttrs(n, props) {
    if (!props) return;
    for (const [k, v] of Object.entries(props)) {
      if (v == null || v === false) continue;
      if (k === 'text') n.textContent = String(v);
      else if (k === 'class') n.setAttribute('class', v);
      else if (k === 'dataset') Object.assign(n.dataset, v);
      else if (k.startsWith('on') && typeof v === 'function') n.addEventListener(k.slice(2), v);
      else if (k === 'href') { const h = safeHref(v); if (h) n.setAttribute('href', h); }
      else n.setAttribute(k, v === true ? '' : String(v));
    }
  }
  function h(tag, props, ...kids) { const n = document.createElement(tag); setAttrs(n, props); return append(n, kids); }
  function s(tag, props, ...kids) { const n = document.createElementNS(SVGNS, tag); setAttrs(n, props); return append(n, kids); }
  function ext(href, text, props) {
    const safe = safeHref(href);
    if (!safe || !/^https:/.test(safe)) return h('span', { class: 'mono' }, text || String(href || ''));
    return h('a', Object.assign({ href: safe, rel: 'noopener noreferrer external' }, props || {}), text || safe);
  }
  function clear(n) { n.replaceChildren(); return n; }
  const $ = (sel, root) => (root || document).querySelector(sel);

  /* ---------- data ---------- */
  const cache = new Map();
  function getJSON(path) {
    if (!cache.has(path)) {
      cache.set(path, fetch(API + '/' + path, { credentials: 'same-origin' }).then((r) => {
        if (!r.ok) throw new Error(path + ': HTTP ' + r.status);
        return r.json();
      }).catch((e) => { cache.delete(path); throw e; }));
    }
    return cache.get(path);
  }
  const index = () => getJSON('index.json');
  function series(id) {
    if (!SERIES_RE.test(id)) return Promise.reject(new Error('bad series id: ' + id));
    return getJSON('series/' + id + '.json');
  }
  async function seriesMany(ids) {
    const out = {};
    await Promise.all(ids.map(async (id) => { try { out[id] = await series(id); } catch (e) { out[id] = null; } }));
    return out;
  }
  async function prov(id) {
    const m = PROV_RE.exec(String(id || ''));
    if (!m) throw new Error('Not a valid provenance id');
    const file = await getJSON('provenance/' + m[1] + '.json');
    const rec = file.records && file.records[id];
    if (!rec) throw new Error('No provenance record ' + id);
    return rec;
  }
  function checkHref(id) { return PROV_RE.test(String(id || '')) ? 'check.html#p=' + encodeURIComponent(id) : null; }
  function pointFor(ser, variant, fy) {
    const pts = (ser && ser.variants && ser.variants[variant]) || [];
    return pts.find((p) => p.fiscal_year === fy) || null;
  }
  function gapFor(ser, fy) { return ((ser && ser.gaps) || []).find((g) => g.fiscal_year === fy) || null; }

  /* ---------- basis toggle (nominal / real / % GDP) ---------- */
  const BASIS_LABEL = { nominal: 'Cash', real: 'Real terms', pct_gdp: '% of GDP' };
  let basis = 'nominal';
  try {
    const q = new URLSearchParams(location.search).get('basis');
    const stored = localStorage.getItem('ukpm.basis');
    basis = BASES.includes(q) ? q : (BASES.includes(stored) ? stored : 'nominal');
  } catch (e) { /* storage blocked: default */ }
  const basisSubs = [];
  function setBasis(b) {
    if (!BASES.includes(b) || b === basis) return;
    basis = b;
    try { localStorage.setItem('ukpm.basis', b); } catch (e) { /* ignore */ }
    try {
      const u = new URL(location.href); u.searchParams.set('basis', b); history.replaceState(null, '', u);
    } catch (e) { /* ignore */ }
    document.querySelectorAll('input[name="basis"]').forEach((i) => { i.checked = i.value === b; });
    basisSubs.forEach((fn) => { try { fn(b); } catch (e) { console.error(e); } });
  }
  function onBasis(fn) { basisSubs.push(fn); }

  /* Pick the variant to show for the global basis; fall back to cash with a stated reason. */
  function variantFor(ser, b) {
    b = b || basis;
    const v = ser && ser.variants && ser.variants[b];
    if (v && v.length) return { variant: b, points: v, fallback: null };
    const pts = (ser && ser.variants && ser.variants.nominal) || [];
    let reason;
    if (b === 'pct_gdp') {
      const n = ((ser && ser.notes) || []).find((x) => /GDP/i.test(x));
      reason = n || 'No % of GDP figure is published for this series.';
    } else if (b === 'real') {
      reason = ser && ser.monetary === false ? 'Counts of people are not adjusted for prices.' : 'No real-terms figure is published for this series.';
    }
    return { variant: 'nominal', points: pts, fallback: reason ? 'Showing cash terms. ' + reason : null };
  }

  /* ---------- formatting ---------- */
  function nf(v, dp) { return v.toLocaleString('en-GB', { minimumFractionDigits: dp, maximumFractionDigits: dp }); }
  function money(v) {
    const a = Math.abs(v); const dp = a >= 10 ? 1 : 2;
    return (v < 0 ? '−' : '') + '£' + nf(a, dp) + 'bn';
  }
  function fmt(v, unit) {
    if (v == null || !isFinite(v)) return '–';
    unit = unit || '';
    if (unit === 'GBP_bn' || unit.startsWith('GBP_bn_')) return money(v);
    if (unit === 'GBP_m') return money(v / 1000);
    if (unit === 'percent') return nf(v, Math.abs(v) < 10 ? 2 : 1) + '%';
    if (unit === 'thousand_persons' || unit === 'persons') {
      const p = unit === 'persons' ? v : v * 1000;
      return p >= 1e6 ? nf(p / 1e6, 2) + ' million' : nf(Math.round(p), 0);
    }
    if (unit === 'index') return nf(v, 1);
    return nf(v, 2);
  }
  function fmtShort(v, unit) {
    if (v == null || !isFinite(v)) return '';
    if (v === 0) return '0';
    if (unit === 'GBP_bn' || (unit || '').startsWith('GBP_bn_')) {
      const a = Math.abs(v);
      return (v < 0 ? '−' : '') + '£' + (a >= 1000 ? nf(a / 1000, a >= 10000 ? 0 : 1) + 'tn' : nf(a, a >= 10 ? 0 : 1) + 'bn');
    }
    if (unit === 'percent') return nf(v, 0) + '%';
    if (unit === 'thousand_persons') return v >= 1000 ? nf(v / 1000, 1) + 'm' : nf(v, 0) + 'k';
    return nf(v, 0);
  }
  function unitNote(unit) {
    if (!unit) return '';
    if (unit === 'GBP_bn') return 'cash';
    const m = /^GBP_bn_(\d{4}-\d{2})$/.exec(unit);
    if (m) return m[1] + ' prices';
    if (unit === 'percent') return 'of GDP';
    if (unit === 'thousand_persons') return 'people';
    return '';
  }
  function basisCaption(b, ix) {
    if (b === 'real') return 'Real terms, in ' + ((ix && ix.real_base_year) || 'latest year') + ' prices (OBR GDP deflator)';
    if (b === 'pct_gdp') return 'Per cent of nominal GDP (same OBR vintage)';
    return 'Cash terms (nominal £, as published)';
  }

  /* ---------- badges ---------- */
  const STATUS = {
    pass: ['✓', 'Pass'], fail: ['✕', 'Fail'], info: ['i', 'Info'], not_run: ['–', 'Not run'],
    forecast: ['▸', 'Forecast'], outturn: ['●', 'Outturn'],
  };
  function badge(status, text) {
    const st = STATUS[status] || ['', status];
    return h('span', { class: 'badge badge-' + status }, h('span', { 'aria-hidden': 'true' }, st[0]), text || st[1]);
  }

  /* ---------- number with popover + check link ---------- */
  let numSeq = 0;
  function num(point, opts) {
    opts = opts || {};
    if (!point) {
      return h('span', { class: 'num muted' }, opts.missing || 'No figure');
    }
    const label = opts.label || '';
    const valText = opts.text || fmt(point.value, point.unit);
    const id = 'n' + (++numSeq);
    const btn = h('button', {
      type: 'button', class: 'num-val', id, 'aria-haspopup': 'dialog', 'aria-expanded': 'false',
      'aria-label': valText + (label ? ', ' + label : '') + '. Show source',
      onclick: (e) => openPop(e.currentTarget, { kind: 'point', id: point.provenance_id, point, label }),
    }, valText);
    const parts = [btn];
    if (opts.unitNote !== false) {
      const un = unitNote(point.unit);
      if (un && opts.showUnit) parts.push(h('span', { class: 'num-unit' }, un));
    }
    if (point.status === 'forecast' && opts.badge !== false) parts.push(badge('forecast'));
    const ch = checkHref(point.provenance_id);
    if (ch && opts.check !== false) {
      parts.push(h('a', { class: 'num-check', href: ch, 'aria-label': 'Check this number' + (label ? ': ' + label : '') }, 'Check this number'));
    }
    return h('span', { class: 'num' + (opts.class ? ' ' + opts.class : '') }, parts);
  }
  /* A value computed on the page from published numbers (e.g. pence per pound). */
  function derivedNum(text, spec) {
    const btn = h('button', {
      type: 'button', class: 'num-val', 'aria-haspopup': 'dialog', 'aria-expanded': 'false',
      'aria-label': text + '. Show how this was computed',
      onclick: (e) => openPop(e.currentTarget, Object.assign({ kind: 'derived' }, spec)),
    }, text);
    return h('span', { class: 'num' }, btn);
  }

  /* ---------- popover ---------- */
  let pop = null; let popTrigger = null;
  function ensurePop() {
    if (pop) return pop;
    pop = h('div', { class: 'pop', role: 'dialog', 'aria-modal': 'false', 'aria-labelledby': 'pop-title', hidden: true, tabindex: '-1' });
    document.body.appendChild(pop);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !pop.hidden) { e.preventDefault(); closePop(true); } });
    document.addEventListener('pointerdown', (e) => {
      if (!pop.hidden && !pop.contains(e.target) && e.target !== popTrigger && !(popTrigger && popTrigger.contains(e.target))) closePop(false);
    });
    window.addEventListener('resize', () => { if (!pop.hidden) placePop(); });
    return pop;
  }
  function placePop() {
    if (!popTrigger) return;
    if (window.matchMedia('(max-width: 639px)').matches) return; // bottom sheet via CSS
    const r = popTrigger.getBoundingClientRect();
    const w = pop.offsetWidth;
    let left = r.left + window.scrollX;
    left = Math.max(16 + window.scrollX, Math.min(left, window.scrollX + document.documentElement.clientWidth - w - 16));
    let top = r.bottom + window.scrollY + 8;
    const ph = pop.offsetHeight;
    if (r.bottom + ph + 16 > window.innerHeight && r.top - ph - 8 > 0) top = r.top + window.scrollY - ph - 8;
    pop.style.left = left + 'px';
    pop.style.top = top + 'px';
  }
  function closePop(returnFocus) {
    if (!pop || pop.hidden) return;
    pop.hidden = true;
    if (popTrigger) {
      popTrigger.setAttribute('aria-expanded', 'false');
      if (returnFocus && popTrigger.isConnected) popTrigger.focus();
    }
    popTrigger = null;
  }
  function popShell(title) {
    clear(pop);
    append(pop, [
      h('button', { type: 'button', class: 'x', 'aria-label': 'Close', onclick: () => closePop(true) }, '×'),
      h('h2', { id: 'pop-title' }, title),
    ]);
  }
  async function openPop(trigger, spec) {
    ensurePop();
    if (popTrigger === trigger && !pop.hidden) { closePop(true); return; }
    closePop(false);
    popTrigger = trigger;
    trigger.setAttribute('aria-expanded', 'true');
    popShell(spec.kind === 'derived' ? (spec.title || 'How this was computed') : 'Where this number comes from');
    pop.hidden = false;
    if (spec.kind === 'derived') {
      renderDerived(pop, spec);
    } else {
      const st = h('p', { class: 'state', role: 'status' }, 'Loading provenance…');
      pop.appendChild(st);
      placePop(); pop.focus();
      try {
        const rec = await prov(spec.id);
        if (popTrigger !== trigger) return;
        st.remove();
        renderProvSummary(pop, rec, spec);
      } catch (e) {
        st.textContent = 'Could not load provenance: ' + e.message;
        st.classList.add('error');
      }
    }
    placePop(); pop.focus();
  }
  function renderDerived(host, spec) {
    if (spec.text) host.appendChild(h('p', { class: 'small' }, spec.text));
    if (spec.formula) host.appendChild(h('p', { class: 'small' }, h('strong', null, 'Formula: '), spec.formula));
    host.appendChild(h('p', { class: 'small muted' }, 'Computed in your browser from the published numbers below. It is not itself a published figure; each input has its own check.'));
    const ul = h('ul', { class: 'notes-list' });
    (spec.inputs || []).forEach((inp) => {
      const ch = checkHref(inp.id);
      ul.appendChild(h('li', null, inp.label + (inp.value != null ? ' = ' + inp.value : '') + ' ', ch ? h('a', { href: ch }, 'Check this number') : h('span', { class: 'muted' }, '(no provenance id)')));
    });
    host.appendChild(ul);
  }
  function renderProvSummary(host, rec, spec) {
    const c = rec.check || {};
    const dl = h('dl');
    const row = (k, v) => { if (v != null && v !== '') append(dl, [h('dt', null, k), h('dd', null, v)]); };
    if (spec.label) row('Figure', spec.label);
    if (spec.point) row('Value shown', fmt(spec.point.value, spec.point.unit) + (unitNote(spec.point.unit) ? ' (' + unitNote(spec.point.unit) + ')' : ''));
    row('Status', h('span', null, badge(rec.status), rec.status_note ? ' ' + rec.status_note : ''));
    row('Publisher', rec.publisher);
    row('Dataset', rec.dataset);
    row('Edition', rec.vintage || rec.edition);
    row('Published', rec.publication_date);
    if (c.kind === 'api') row('Query', ext(c.query_url, 'API request'));
    else {
      row('File', ext(c.download_url || rec.source_url, 'Download the file'));
      row('Sheet', c.sheet || rec.sheet);
      row('Cell', c.cell || rec.cell_or_range);
      if (c.row_label) row('Row', c.row_label);
      if (c.column_label) row('Column', c.column_label);
      if (c.published_value != null) row('In the file', String(c.published_value) + (c.published_unit ? ' ' + c.published_unit : ''));
    }
    const steps = (rec.transformations || []).map((t) => t.detail || t.op).filter(Boolean);
    row('Our steps', steps.length ? steps.join('; ') : 'none: value as published');
    row('Licence', rec.licence_url ? ext(rec.licence_url, rec.licence) : rec.licence);
    if (rec.retrieval === 'fixture') row('Retrieved', 'from a committed test fixture (offline build)');
    host.appendChild(dl);
    const ch = checkHref(rec.provenance_id);
    if (ch) host.appendChild(h('a', { class: 'cta', href: ch }, 'Check this number →'));
  }

  /* ---------- shared UI pieces ---------- */
  function state(host, text, kind) {
    clear(host).appendChild(h('p', { class: 'state' + (kind ? ' ' + kind : ''), role: kind === 'error' ? 'alert' : 'status' }, text));
  }
  function note(kind, ...kids) { return h('div', { class: 'note' + (kind ? ' ' + kind : '') }, h('p', null, kids)); }
  function yearSelect(labelText, years, value, onChange) {
    const id = 'sel' + (++numSeq);
    const sel = h('select', { id, onchange: (e) => onChange(e.target.value) });
    years.forEach((y) => { const o = h('option', { value: y }, y); if (y === value) o.selected = true; sel.appendChild(o); });
    return h('div', { class: 'field' }, h('label', { for: id }, labelText), sel);
  }
  function selectField(labelText, options, value, onChange) {
    const id = 'sel' + (++numSeq);
    const sel = h('select', { id, onchange: (e) => onChange(e.target.value) });
    options.forEach(([v, t]) => { const o = h('option', { value: v }, t); if (v === value) o.selected = true; sel.appendChild(o); });
    return h('div', { class: 'field' }, h('label', { for: id }, labelText), sel);
  }
  function gapRanges(gaps) {
    const sorted = (gaps || []).slice().sort((a, b) => a.fiscal_year.localeCompare(b.fiscal_year));
    const out = [];
    sorted.forEach((g) => {
      const last = out[out.length - 1];
      const prevYear = last && last.to;
      const consecutive = prevYear && (parseInt(prevYear, 10) + 1 === parseInt(g.fiscal_year, 10));
      if (last && consecutive && last.reason === g.reason) last.to = g.fiscal_year;
      else out.push({ from: g.fiscal_year, to: g.fiscal_year, reason: g.reason });
    });
    return out;
  }
  function gapsNote(ser) {
    const r = gapRanges(ser && ser.gaps);
    if (!r.length) return null;
    return h('div', { class: 'note warn' },
      h('p', null, h('strong', null, 'Missing years. '), 'We never fill gaps by estimating.'),
      h('ul', { class: 'notes-list' }, r.map((g) => h('li', null, (g.from === g.to ? g.from : g.from + ' to ' + g.to) + ': ' + g.reason))));
  }

  /* Horizontal bar list. rows: {label, sub, point, share:{value,text,spec}, barValue, forecast} */
  function barList(rows, opts) {
    opts = opts || {};
    const max = opts.max || Math.max(...rows.map((r) => Math.abs(r.barValue || 0)), 0) || 1;
    const ul = h('ul', { class: 'bars' });
    rows.forEach((r) => {
      const pct = Math.max(0, Math.min(100, (Math.abs(r.barValue || 0) / max) * 100));
      const fill = h('span', { class: 'bar-fill' + (r.forecast ? ' forecast' : ''), 'aria-hidden': 'true' });
      fill.style.width = pct.toFixed(2) + '%';
      const track = h('div', { class: 'bar-track' }, fill, r.share ? h('span', { class: 'bar-share' }, derivedNum(r.share.text, r.share.spec)) : null);
      ul.appendChild(h('li', { class: 'bar-row' },
        h('div', { class: 'bar-label' }, r.label, r.sub ? h('span', { class: 'sub' }, r.sub) : null),
        track,
        h('div', { class: 'bar-value' }, r.valueNode || num(r.point, { label: r.fullLabel || r.label }))));
    });
    return ul;
  }

  /* Table view of a series variant: every value with its check link. */
  function seriesTable(ser, points, caption) {
    const tb = h('tbody');
    const years = new Set(points.map((p) => p.fiscal_year));
    (ser.gaps || []).forEach((g) => years.add(g.fiscal_year));
    [...years].sort().forEach((y) => {
      const p = points.find((x) => x.fiscal_year === y);
      const g = gapFor(ser, y);
      tb.appendChild(h('tr', null,
        h('th', { scope: 'row' }, y),
        h('td', { class: 'r' }, p ? num(p, { label: ser.title + ' ' + y, badge: false }) : h('span', { class: 'muted' }, 'No data')),
        h('td', null, p ? badge(p.status) : (g ? g.reason : '')),
        h('td', null, p ? p.vintage : '')));
    });
    return h('details', { class: 'table-view' }, h('summary', null, 'Show the numbers as a table'),
      h('div', { class: 'table-wrap' }, h('table', null, h('caption', null, caption),
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Year'), h('th', { scope: 'col', class: 'r' }, 'Value'), h('th', { scope: 'col' }, 'Status'), h('th', { scope: 'col' }, 'Edition'))),
        tb)));
  }

  /* ---------- column chart (one series over time) ---------- */
  function niceTicks(min, max, count) {
    const span = max - min || Math.abs(max) || 1;
    const step0 = span / count;
    const mag = Math.pow(10, Math.floor(Math.log10(step0)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((m) => span / m <= count) || 10 * mag;
    const lo = Math.floor(min / step) * step; const hi = Math.ceil(max / step) * step;
    const out = []; for (let v = lo; v <= hi + step / 2; v += step) out.push(+v.toFixed(10));
    return out;
  }
  let chartSeq = 0;
  function columnChart(ser, points, opts) {
    opts = opts || {};
    const wrap = h('div', { class: 'chart' });
    const tip = h('div', { class: 'tip', hidden: true, role: 'presentation' });
    const uid = 'c' + (++chartSeq);
    const years = new Set(points.map((p) => p.fiscal_year));
    (ser.gaps || []).forEach((g) => years.add(g.fiscal_year));
    const yrs = [...years].sort();
    const hasFc = points.some((p) => p.status === 'forecast');
    const hasGap = (ser.gaps || []).length > 0;
    const unit = points[0] ? points[0].unit : '';

    function draw() {
      const W = Math.max(280, wrap.clientWidth || 640);
      const narrow = W < 520;
      const H = narrow ? 220 : 260;
      const m = { l: 46, r: 8, t: hasFc ? 26 : 16, b: 30 };
      const iw = W - m.l - m.r; const ih = H - m.t - m.b;
      const vals = points.map((p) => p.value);
      const lo = Math.min(0, ...vals); const hi = Math.max(0, ...vals);
      const ticks = niceTicks(lo, hi, narrow ? 3 : 4);
      const d0 = ticks[0]; const d1 = ticks[ticks.length - 1];
      const y = (v) => m.t + ih - ((v - d0) / (d1 - d0 || 1)) * ih;
      const band = iw / Math.max(1, yrs.length);
      const bw = Math.max(4, Math.min(band - 4, band * 0.72, 44));
      const x = (i) => m.l + band * i + (band - bw) / 2;
      const svg = s('svg', { viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'group', 'aria-label': (opts.title || ser.title) + ', ' + yrs[0] + ' to ' + yrs[yrs.length - 1] + '. Use arrow keys to move between years.' });
      const defs = s('defs', null, s('pattern', { id: uid + 'h', width: 6, height: 6, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' },
        s('rect', { width: 6, height: 6, class: 'hatch-bg' }), s('rect', { width: 2.5, height: 6, class: 'hatch-fg' })));
      svg.appendChild(defs);
      // forecast band
      const fcIdx = yrs.map((yy, i) => (points.find((p) => p.fiscal_year === yy && p.status === 'forecast') ? i : -1)).filter((i) => i >= 0);
      if (fcIdx.length) {
        const fx = m.l + band * fcIdx[0];
        svg.appendChild(s('rect', { class: 'fc-band', x: fx, y: 4, width: band * fcIdx.length, height: m.t + ih - 4 }));
        svg.appendChild(s('text', { class: 'fc-label', x: fx + 6, y: 17 }, 'Forecast ▸'));
      }
      ticks.forEach((t) => {
        svg.appendChild(s('line', { class: t === 0 ? 'zero' : 'grid-line', x1: m.l, x2: W - m.r, y1: y(t), y2: y(t) }));
        svg.appendChild(s('text', { class: 'tick', x: m.l - 6, y: y(t) + 4, 'text-anchor': 'end' }, fmtShort(t, unit)));
      });
      const labelEvery = Math.max(1, Math.ceil((narrow ? 46 : 52) / band));
      yrs.forEach((yy, i) => {
        if ((yrs.length - 1 - i) % labelEvery === 0) {
          svg.appendChild(s('text', { class: 'tick', x: m.l + band * i + band / 2, y: H - 10, 'text-anchor': 'middle' }, narrow ? yy.slice(2) : yy));
        }
      });
      const lastOut = [...points].reverse().find((p) => p.status !== 'forecast');
      const lastAll = points[points.length - 1];
      const groups = [];
      yrs.forEach((yy, i) => {
        const p = points.find((q) => q.fiscal_year === yy);
        const g = s('g', { class: 'pt', tabindex: '-1', role: 'button' });
        if (p) {
          const top = y(Math.max(0, p.value)); const bot = y(Math.min(0, p.value));
          const hgt = Math.max(1, bot - top); const r = Math.min(4, bw / 2, hgt);
          const x0 = x(i); const up = p.value >= 0;
          const dpath = up
            ? `M${x0},${bot}V${top + r}Q${x0},${top} ${x0 + r},${top}H${x0 + bw - r}Q${x0 + bw},${top} ${x0 + bw},${top + r}V${bot}Z`
            : `M${x0},${top}V${bot - r}Q${x0},${bot} ${x0 + r},${bot}H${x0 + bw - r}Q${x0 + bw},${bot} ${x0 + bw},${bot - r}V${top}Z`;
          const fc = p.status === 'forecast';
          const col = s('path', { class: 'col' + (fc ? ' forecast' : ''), d: dpath });
          if (fc) col.style.setProperty('fill', 'url(#' + uid + 'h)');
          g.appendChild(col);
          if (p === lastOut || (p === lastAll && p !== lastOut) || (!narrow && i === 0)) {
            g.appendChild(s('text', { class: 'dlabel', x: x0 + bw / 2, y: (up ? top : bot + 12) - 5, 'text-anchor': 'middle' }, fmtShort(p.value, p.unit)));
          }
          g.setAttribute('aria-label', yy + ': ' + fmt(p.value, p.unit) + (fc ? ', forecast' : ', outturn') + '. Press Enter for source.');
        } else {
          g.appendChild(s('line', { class: 'gap-mark', x1: x(i), x2: x(i) + bw, y1: y(0) - 2, y2: y(0) - 2 }));
          const gg = gapFor(ser, yy);
          g.setAttribute('aria-label', yy + ': no data. ' + (gg ? gg.reason : ''));
        }
        g.appendChild(s('rect', { class: 'hit', x: m.l + band * i, y: m.t, width: band, height: ih }));
        const show = () => {
          clear(tip);
          append(tip, [h('strong', null, yy)]);
          if (p) append(tip, [fmt(p.value, p.unit), ' ', unitNote(p.unit), h('br'), p.status === 'forecast' ? 'Forecast' : 'Outturn', ' · ', p.vintage, h('br'), 'Click or press Enter for the source']);
          else { const gg = gapFor(ser, yy); append(tip, ['No data', h('br'), gg ? gg.reason : '']); }
          tip.hidden = false;
          const cx = (m.l + band * i + band / 2) * (wrap.clientWidth / W);
          const tw = tip.offsetWidth;
          tip.style.left = Math.max(0, Math.min(cx - tw / 2, wrap.clientWidth - tw)) + 'px';
          tip.style.top = Math.max(0, (y(p ? Math.max(0, p.value) : 0) * (wrap.clientWidth / W)) - tip.offsetHeight - 10) + 'px';
        };
        const hide = () => { tip.hidden = true; };
        const activate = () => { if (p) openPop(g, { kind: 'point', id: p.provenance_id, point: p, label: (opts.title || ser.title) + ' ' + yy }); };
        g.addEventListener('pointerenter', show); g.addEventListener('pointerleave', hide);
        g.addEventListener('focus', show); g.addEventListener('blur', hide);
        g.addEventListener('click', activate);
        g.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(); }
          else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft' || e.key === 'Home' || e.key === 'End') {
            e.preventDefault();
            const j = e.key === 'Home' ? 0 : e.key === 'End' ? groups.length - 1 : Math.max(0, Math.min(groups.length - 1, i + (e.key === 'ArrowRight' ? 1 : -1)));
            groups[i].setAttribute('tabindex', '-1'); groups[j].setAttribute('tabindex', '0'); groups[j].focus();
          }
        });
        groups.push(g);
        svg.appendChild(g);
      });
      const start = groups.length ? (lastOut ? yrs.indexOf(lastOut.fiscal_year) : groups.length - 1) : -1;
      if (start >= 0) groups[start].setAttribute('tabindex', '0');
      const old = wrap.querySelector('svg');
      if (old) old.replaceWith(svg); else wrap.insertBefore(svg, tip);
    }
    wrap.appendChild(tip);
    const legend = h('p', { class: 'chart-legend' },
      h('span', null, h('span', { class: 'sw', 'aria-hidden': 'true' }), 'Outturn'),
      hasFc ? h('span', null, h('span', { class: 'sw fc', 'aria-hidden': 'true' }), 'Forecast (hatched)') : null,
      hasGap ? h('span', null, h('span', { class: 'sw gap', 'aria-hidden': 'true' }), 'No data (see note)') : null);
    const out = h('figure', { class: 'card', style: null },
      opts.heading ? h('figcaption', null, h('h3', null, opts.heading), opts.sub ? h('p', { class: 'small muted' }, opts.sub) : null) : null,
      wrap, legend);
    draw(); // drawn at a default width now (scales via viewBox), redrawn at the real width once attached
    requestAnimationFrame(draw);
    let lastW = 0;
    if ('ResizeObserver' in window) {
      new ResizeObserver(() => { const w = wrap.clientWidth; if (w && Math.abs(w - lastW) > 8) { lastW = w; draw(); } }).observe(wrap);
    }
    return out;
  }

  /* ---------- chrome: basis toggle, reconciliation strip, build banner, footer ---------- */
  function mountBasis() {
    const host = $('#basis-host');
    if (!host) return;
    const fs = h('fieldset', { class: 'basis' }, h('legend', null, 'Show money as'));
    const seg = h('div', { class: 'seg' });
    BASES.forEach((b) => {
      const id = 'basis-' + b;
      const inp = h('input', { type: 'radio', name: 'basis', id, value: b, onchange: (e) => setBasis(e.target.value) });
      inp.checked = b === basis;
      append(seg, [inp, h('label', { for: id }, BASIS_LABEL[b])]);
    });
    fs.appendChild(seg);
    clear(host).appendChild(fs);
  }
  async function mountReconStrip() {
    const host = $('#recon-host');
    if (!host) return;
    try {
      const r = await getJSON('reconciliation.json');
      const sm = r.summary || {};
      clear(host);
      append(host, [
        h('span', { class: 'muted' }, 'Cross-checks:'),
        (sm.fail || 0) > 0 ? badge('fail', (sm.fail) + ' failing') : badge('pass', 'none failing'),
        badge('pass', String(sm.pass || 0) + ' pass'),
        badge('info', String(sm.info || 0) + ' info'),
        (sm.not_run || 0) ? badge('not_run', sm.not_run + ' not run') : null,
        h('a', { href: 'reconciliation.html' }, 'See every check'),
      ]);
    } catch (e) {
      host.textContent = 'Cross-checks unavailable (' + e.message + ')';
    }
  }
  async function mountFooter() {
    const host = $('#build-host');
    try {
      const ix = await index();
      if (host) {
        clear(host);
        append(host, ['Data built ', ix.generated_at || '?', ' · commit ', h('code', null, (ix.build && ix.build.git_sha || '').slice(0, 7) || '?'),
          ' · ', String((ix.series || []).length), ' series · rejected values: ', String((ix.build && ix.build.rejected) || 0)]);
      }
      const stale = (ix.sources || []).filter((x) => x.stale_since);
      const offline = ix.build && ix.build.mode === 'offline';
      if (offline || stale.length) {
        const msg = [];
        if (offline) msg.push('This is an offline build from committed test fixtures, so some years are missing. Each number’s source shows how it was retrieved.');
        stale.forEach((x) => msg.push(x.publisher + ' data is from a cached copy since ' + x.stale_since + ' (the live download failed).'));
        const b = h('div', { class: 'build-banner', role: 'note' }, h('div', null, msg.join(' ')));
        document.body.insertBefore(b, document.body.firstElementChild.nextElementSibling);
      }
    } catch (e) {
      if (host) host.textContent = 'Build information unavailable.';
    }
  }

  /* ---------- boot ---------- */
  let pageFn = null;
  function page(fn) { pageFn = fn; }
  async function boot() {
    mountBasis();
    mountReconStrip();
    mountFooter();
    const main = $('#main');
    if (pageFn) {
      try { await pageFn({ main }); } catch (e) {
        console.error(e);
        const host = $('[data-page-root]') || main;
        host.appendChild(h('p', { class: 'state error', role: 'alert' }, 'Something went wrong loading the data: ' + e.message));
      }
    }
  }
  // Deferred scripts run while readyState is 'interactive', before the page script registers; wait for DOMContentLoaded.
  if (document.readyState === 'complete') setTimeout(boot, 0); else document.addEventListener('DOMContentLoaded', boot);

  window.UKPM = {
    h, s, ext, clear, $, append, safeHref, getJSON, index, series, seriesMany, prov, checkHref, pointFor, gapFor,
    get basis() { return basis; }, setBasis, onBasis, variantFor, fmt, fmtShort, unitNote, basisCaption, badge, num, derivedNum,
    openPop, closePop, renderProvSummary, state, note, yearSelect, selectField, gapsNote, gapRanges, barList, seriesTable, columnChart, page,
    PROV_RE, SERIES_RE,
  };
})();
