/* UK Public Money: shared site code. No dependencies, no build step.
   Rules: data is rendered with textContent only (never innerHTML); external links must be https;
   every displayed number links to its provenance record (popover + check.html).
   Strict CSP: no inline script or style. Geometry uses SVG attributes; colour comes from classes in app.css. */
(function () {
  'use strict';

  const CFG = Object.assign({ apiBase: 'api/v1', checkHosts: [] }, window.UKPM_CONFIG || {});
  const API = String(CFG.apiBase).replace(/\/+$/, '');
  const SVGNS = 'http://www.w3.org/2000/svg';
  const PROV_RE = /^([a-z][a-z0-9_]*)\.([0-9a-f]{6,64})$/;
  const SERIES_RE = /^[a-z0-9_]+(\.[a-z0-9_]+)+$/;
  const BASES = ['real', 'nominal', 'pct_gdp'];

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
      else if (k === 'href') { const hh = safeHref(v); if (hh) n.setAttribute('href', hh); }
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

  /* ---------- data (lazy: nothing is fetched until a page asks) ---------- */
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
  function latestOutturn(ix) { return ix && ix.fiscal_years && ix.fiscal_years.latest_outturn; }

  /* ---------- basis toggle ---------- */
  const BASIS_LABEL = { real: 'Adjusted for rising prices', nominal: 'As spent at the time', pct_gdp: 'Share of the economy' };
  let basis = 'real';
  try {
    const q = new URLSearchParams(location.search).get('basis');
    const stored = localStorage.getItem('ukpm.basis');
    basis = BASES.includes(q) ? q : (BASES.includes(stored) ? stored : 'real');
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
      reason = n || 'We do not show this as a share of the economy yet.';
    } else if (b === 'real') {
      reason = ser && ser.monetary === false ? 'Counts of people are not adjusted for prices.' : 'We do not show this adjusted for rising prices yet.';
    }
    return { variant: 'nominal', points: pts, fallback: reason ? 'Showing amounts as spent at the time. ' + reason : null };
  }

  /* ---------- formatting (plain English: words, not bn/m/k) ---------- */
  function nf(v, dp) { return v.toLocaleString('en-GB', { minimumFractionDigits: dp, maximumFractionDigits: dp }); }
  function sig(v, n) {
    if (!v) return 0;
    const mag = Math.pow(10, Math.floor(Math.log10(Math.abs(v))) - n + 1);
    return Math.round(v / mag) * mag;
  }
  /* bn is a value in £ billion */
  function moneyWords(bn) {
    if (bn === 0) return '£0';
    const a = Math.abs(bn); const sign = bn < 0 ? '−' : '';
    if (a >= 1000) return sign + '£' + nf(a / 1000, 1) + ' trillion';
    if (a >= 10) return sign + '£' + nf(Math.round(a), 0) + ' billion';
    if (a >= 1) return sign + '£' + nf(a, 1) + ' billion';
    const m = a * 1000;
    if (m >= 10) return sign + '£' + nf(Math.round(m), 0) + ' million';
    if (m >= 1) return sign + '£' + nf(m, 1) + ' million';
    return sign + '£' + nf(Math.round(m * 1000), 0) + ' thousand';
  }
  /* Per person: nearest £10, or nearest £100 from £10,000 up. */
  function perPersonText(v) {
    const a = Math.abs(v);
    const r = a >= 10000 ? Math.round(a / 100) * 100 : (a >= 100 ? Math.round(a / 10) * 10 : Math.round(a));
    return (v < 0 ? '−' : '') + '£' + nf(r, 0);
  }
  /* Out of every £100: whole pounds; pence under £1. */
  function per100Text(v) {
    if (v >= 0.995) return '£' + nf(Math.round(v), 0);
    const p = Math.round(v * 100);
    return p <= 0 ? 'less than 1p' : p + 'p';
  }
  function per100Int(n) { return n >= 1 ? '£' + nf(n, 0) : 'less than £1'; }
  /* Counts of people: 2 significant figures, unit as a word. */
  function peopleText(p) {
    const a = Math.abs(p);
    if (a >= 1e6) { const m = a / 1e6; return nf(m >= 9.95 ? Math.round(m) : Math.round(m * 10) / 10, m >= 9.95 ? 0 : 1) + ' million'; }
    return nf(sig(a, 2), 0);
  }
  /* Split values that should sum to 100 into whole pounds that sum to exactly 100. */
  function largestRemainder(values, target) {
    target = target == null ? 100 : target;
    const floors = values.map((v) => Math.max(0, Math.floor(v + 1e-9)));
    let left = target - floors.reduce((a, b) => a + b, 0);
    const order = values.map((v, i) => [v - Math.floor(v + 1e-9), i]).sort((a, b) => b[0] - a[0]);
    for (let k = 0; left > 0 && order.length; k += 1, left -= 1) floors[order[k % order.length][1]] += 1;
    return floors;
  }
  function fmt(v, unit) {
    if (v == null || !isFinite(v)) return '–';
    unit = unit || '';
    if (unit === 'GBP_bn' || unit.startsWith('GBP_bn_')) return moneyWords(v);
    if (unit === 'GBP_m') return moneyWords(v / 1000);
    if (unit === 'GBP_per_100') return per100Text(v);
    if (unit === 'GBP_per_person' || unit.startsWith('GBP_per_person_') || unit === 'GBP_per_household' || unit.startsWith('GBP_per_household_')) return perPersonText(v);
    if (unit === 'GBP_per_claimant') return perPersonText(v);
    if (unit === 'percent') return nf(v, Math.abs(v) < 10 ? 1 : 0) + '%';
    if (unit === 'thousand_persons' || unit === 'thousand_cases') return peopleText(v * 1000);
    if (unit === 'persons') return peopleText(v);
    if (unit === 'index') return nf(v, 1);
    return nf(v, 2);
  }
  /* Chart labels and ticks: plain numbers; the axis title carries the unit. */
  function fmtShort(v, unit) {
    if (v == null || !isFinite(v)) return '';
    if (v === 0) return '0';
    unit = unit || '';
    if (unit === 'GBP_bn' || unit.startsWith('GBP_bn_')) {
      const a = Math.abs(v);
      return (v < 0 ? '−' : '') + nf(a, a >= 10 ? 0 : 1);
    }
    if (unit === 'percent') return nf(v, Math.abs(v) < 10 ? 1 : 0) + '%';
    if (unit === 'thousand_persons' || unit === 'thousand_cases') return v >= 1000 ? nf(v / 1000, 1) + ' million' : nf(v, 0) + ' thousand';
    return nf(v, Math.abs(v) < 10 && v % 1 ? 1 : 0);
  }
  function unitNote(unit) {
    if (!unit) return '';
    if (unit === 'GBP_bn') return 'as spent at the time';
    const m = /^GBP_bn_(\d{4}-\d{2})$/.exec(unit);
    if (m) return 'adjusted for rising prices (' + m[1] + ' prices)';
    if (unit === 'percent') return 'share of the economy';
    if (unit === 'thousand_persons' || unit === 'thousand_cases') return 'people';
    if (unit === 'GBP_per_100') return 'out of every £100';
    if (unit === 'GBP_per_person') return 'per person, as spent at the time';
    if (/^GBP_per_person_/.test(unit)) return 'per person, adjusted for rising prices';
    if (unit === 'GBP_per_household') return 'per household, as spent at the time';
    if (/^GBP_per_household_/.test(unit)) return 'per household, adjusted for rising prices';
    if (unit === 'GBP_per_claimant') return 'a year for each person getting it';
    return '';
  }
  function axisTitle(unit) {
    unit = unit || '';
    if (unit === 'GBP_bn') return '£ billion, as spent at the time';
    const m = /^GBP_bn_(\d{4}-\d{2})$/.exec(unit);
    if (m) return '£ billion, adjusted for rising prices (' + m[1] + ' prices)';
    if (unit === 'percent') return 'Per cent of everything the UK produces (GDP)';
    if (unit === 'thousand_persons' || unit === 'thousand_cases') return 'Thousand people';
    return '';
  }
  function basisCaption(b, ix) {
    if (b === 'real') return 'Adjusted for rising prices, in ' + ((ix && ix.real_base_year) || 'latest year') + ' prices';
    if (b === 'pct_gdp') return 'Share of everything the UK produces in a year (GDP)';
    return 'As spent at the time, not adjusted for rising prices';
  }
  function basisShort(b) {
    return b === 'real' ? 'adjusted for rising prices' : (b === 'pct_gdp' ? 'share of the economy' : 'as spent at the time');
  }
  function updatedText(ix) {
    const d = ix && ix.generated_at ? new Date(ix.generated_at) : null;
    return d && !isNaN(d) ? d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) : 'date not recorded';
  }
  /* Per household: the API only has it for years with an ONS household count (UK-wide series, recent years). */
  function perHousehold(ix) {
    const ph = ix && ix.per_household;
    if (ph && ph.available === true) {
      const yrs = ph.years || [];
      return { available: true, first: yrs[0], last: yrs[yrs.length - 1],
        note: 'Amounts per household are shown only for ' + (yrs.length > 1 ? yrs[0] + ' to ' + yrs[yrs.length - 1] : (yrs[0] || 'recent years')) + ', because the household count starts in 2011 and only recent years are traced.' };
    }
    return { available: false, note: 'We do not show amounts per household yet: the official household counts are not published in a form we can trace.' };
  }
  /* Per-person or per-household point of a series for a year, following the price basis (real when asked and available). */
  function perHead(ser, kind, fy, b) {
    b = b || basis;
    const order = b === 'real' ? [kind + '_real', kind] : [kind];
    for (const v of order) {
      const pt = pointFor(ser, v, fy);
      if (pt) return pt;
    }
    return null;
  }
  function perHouseholdNote(point, label, missing) {
    if (!point) return missing ? h('p', { class: 'small muted' }, missing) : null;
    return h('p', { class: 'small muted' }, 'That is about ', num(point, { label: label || 'Amount per household', badge: false }),
      ' for every household in ' + point.fiscal_year + ' (' + (unitNote(point.unit) || 'per household') + ').');
  }
  function perPersonNote(point, where, label) {
    if (!point) return null;
    return h('p', { class: 'small muted' }, 'That is about ', num(point, { label: label || 'Amount per person', badge: false }),
      ' for every person in ' + (where || 'the UK') + ', including children.');
  }

  /* Plain names for the ten spending areas (series id suffix). */
  const AREA_NAMES = {
    social_protection: 'pensions and benefits', health: 'health', education: 'schools and education',
    economic_affairs: 'transport, business and the economy', public_order_safety: 'police, courts and prisons', public_order_and_safety: 'police, courts and prisons',
    housing_community_amenities: 'housing and local services', housing_and_community_amenities: 'housing and local services', general_public_services: 'general public services',
    environment_protection: 'the environment', recreation_culture_religion: 'culture, sport and religion', defence: 'defence',
  };
  const AREA_BLURB = {
    social_protection: 'This is help for people who are older, ill, disabled, out of work or on low incomes.',
    health: 'This covers hospitals, GPs and other health services.',
    education: 'This covers schools, colleges and universities.',
    economic_affairs: 'This covers things like transport, support for business and help to find work.',
    public_order_and_safety: 'This covers the police, courts, prisons and fire services.',
    public_order_safety: 'This covers the police, courts, prisons and fire services.',
  };
  function areaName(seriesId, fallback) {
    const k = String(seriesId || '').split('.').pop();
    return AREA_NAMES[k] || (fallback ? String(fallback).split(':')[0].toLowerCase() : k.replace(/_/g, ' '));
  }
  const cap1 = (t) => t.charAt(0).toUpperCase() + t.slice(1);

  /* ---------- badges ---------- */
  const STATUS = {
    pass: ['✓', 'Pass'], fail: ['✕', 'Fail'], info: ['i', 'Info'], not_run: ['–', 'Not run'],
    forecast: ['▸', 'Forecast'], outturn: ['●', 'Actual'], plan: ['▸', 'Plan'],
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
      return h('span', { class: 'num muted' }, opts.missing || 'Not published yet');
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
    /* The value itself is the button that opens the source. A visible "Check this number" link is shown
       only where a page asks for it (one per hero or summary figure), so lists and charts stay readable. */
    const ch = checkHref(point.provenance_id);
    if (ch && opts.check === true) {
      parts.push(h('a', { class: 'num-check', href: ch, 'aria-label': 'Check this number' + (label ? ': ' + label : '') }, 'Check this number'));
    }
    return h('span', { class: 'num' + (opts.class ? ' ' + opts.class : '') }, parts);
  }
  /* A value computed on the page from published numbers (e.g. out of every £100). */
  function derivedNum(text, spec) {
    const btn = h('button', {
      type: 'button', class: 'num-val', 'aria-haspopup': 'dialog', 'aria-expanded': 'false',
      'aria-label': text + '. Show how this was worked out',
      onclick: (e) => openPop(e.currentTarget, Object.assign({ kind: 'derived' }, spec)),
    }, text);
    return h('span', { class: 'num' }, btn);
  }
  /* Spec for "part out of every £100 of total". */
  function shareSpec(label, year, part, total, whatTotal) {
    const pct = (part.value / total.value) * 100;
    return {
      title: 'Out of every £100: ' + label,
      text: label + ' was ' + nf(pct, 2) + ' out of every £100 of ' + whatTotal + ' in ' + year + '. The page rounds the parts so they add up to exactly £100.',
      formula: label + ' ÷ ' + whatTotal + ', ' + year + ', × 100',
      inputs: [
        { label: label + ' ' + year, id: part.provenance_id, value: fmt(part.value, part.unit) },
        { label: cap1(whatTotal) + ' ' + year, id: total.provenance_id, value: fmt(total.value, total.unit) },
      ],
    };
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
    popShell(spec.kind === 'derived' ? (spec.title || 'How this was worked out') : 'Where this number comes from');
    pop.hidden = false;
    if (spec.kind === 'derived') {
      renderDerived(pop, spec);
    } else {
      const st = h('p', { class: 'state', role: 'status' }, 'Loading the source…');
      pop.appendChild(st);
      placePop(); pop.focus();
      try {
        const rec = await prov(spec.id);
        if (popTrigger !== trigger) return;
        st.remove();
        renderProvSummary(pop, rec, spec);
      } catch (e) {
        st.textContent = 'Could not load the source: ' + e.message;
        st.classList.add('error');
      }
    }
    placePop(); pop.focus();
  }
  function renderDerived(host, spec) {
    if (spec.text) host.appendChild(h('p', { class: 'small' }, spec.text));
    if (spec.formula) host.appendChild(h('p', { class: 'small' }, h('strong', null, 'Sum: '), spec.formula));
    host.appendChild(h('p', { class: 'small muted' }, 'Worked out in your browser from the published numbers below. It is not itself a published figure. Each input has its own check.'));
    const ul = h('ul', { class: 'notes-list' });
    (spec.inputs || []).forEach((inp) => {
      const ch = checkHref(inp.id);
      ul.appendChild(h('li', null, inp.label + (inp.value != null ? ' = ' + inp.value : '') + ' ', ch ? h('a', { href: ch }, 'Check this number') : h('span', { class: 'muted' }, '(no source id)')));
    });
    host.appendChild(ul);
  }
  function renderProvSummary(host, rec, spec) {
    const c = rec.check || {};
    const dl = h('dl');
    const row = (k, v) => { if (v != null && v !== '') append(dl, [h('dt', null, k), h('dd', null, v)]); };
    if (spec.label) row('Figure', spec.label);
    if (spec.point) {
      row('Value shown', fmt(spec.point.value, spec.point.unit) + (unitNote(spec.point.unit) ? ' (' + unitNote(spec.point.unit) + ')' : ''));
      if (/^GBP_per_/.test(spec.point.unit || '')) row('Exact value', nf(spec.point.value, 3));
    }
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
    row('What we did to it', steps.length ? steps.join('; ') : 'nothing: shown as published');
    row('Licence', rec.licence_url ? ext(rec.licence_url, rec.licence) : rec.licence);
    if (rec.retrieval === 'fixture') row('Retrieved', 'from a committed test fixture (offline build)');
    host.appendChild(dl);
    const ch = checkHref(rec.provenance_id);
    if (ch) host.appendChild(h('a', { class: 'cta', href: ch }, 'Check this number →'));
  }

  /* ---------- glossary terms: accessible tooltips (Popover API, no inline script or style) ---------- */
  let glossaryP = null;
  function loadGlossary() {
    if (!glossaryP) glossaryP = getJSON('glossary.json').catch(() => null);
    return glossaryP;
  }
  let termSeq = 0;
  /* A word that will become a tooltip button once the glossary has loaded. Until then (or without
     JavaScript) it is plain text. */
  function term(id, text) { return h('span', { 'data-term': id }, text); }
  async function enhanceTerms(root) {
    const nodes = [...(root || document).querySelectorAll('[data-term]')];
    if (!nodes.length) return;
    const g = await loadGlossary();
    if (!g) return;
    const byId = new Map((g.terms || []).map((t) => [t.id, t]));
    nodes.forEach((n) => {
      if (!n.isConnected) return;
      const id = n.getAttribute('data-term');
      const t = byId.get(id);
      const plainText = () => { n.replaceWith(document.createTextNode(n.textContent)); };
      if (!t || n.closest('h1,h2,h3,h4,h5,h6,button,.num,nav,svg,summary,.term-tip')) { plainText(); return; }
      if (document.querySelector('button.term[data-term-id="' + id + '"]')) { plainText(); return; }
      const tipId = 'tt-' + id + '-' + (++termSeq);
      const btn = h('button', { type: 'button', class: 'term', popovertarget: tipId, 'data-term-id': id }, n.textContent);
      const tip = h('span', { id: tipId, class: 'term-tip', popover: true, role: 'note' },
        t.plain, ' ', h('a', { href: 'glossary.html#g-' + encodeURIComponent(id) }, 'More in Words explained'));
      n.replaceWith(btn, tip);
    });
  }
  let termQueued = false;
  function watchTerms() {
    if (!('MutationObserver' in window)) return;
    new MutationObserver(() => {
      if (termQueued || !document.querySelector('[data-term]')) return;
      termQueued = true;
      requestAnimationFrame(() => { termQueued = false; enhanceTerms(); });
    }).observe(document.body, { childList: true, subtree: true });
  }

  /* ---------- shared UI pieces ---------- */
  function state(host, text, kind) {
    clear(host).appendChild(h('p', { class: 'state' + (kind ? ' ' + kind : ''), role: kind === 'error' ? 'alert' : 'status' }, text));
  }
  function note(kind, ...kids) { return h('div', { class: 'note' + (kind ? ' ' + kind : '') }, h('p', null, kids)); }
  function gapBox(text) {
    return h('div', { class: 'empty' }, h('p', null, text || 'We don’t show this yet: the official figures aren’t published in a form we can trace.'));
  }
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
    const n = (ser.gaps || []).length;
    return h('details', { class: 'gaps-note small' },
      h('summary', null, n + (n === 1 ? ' year is' : ' years are') + ' not published yet. Why?'),
      h('p', null, 'We never fill gaps with estimates.'),
      h('ul', { class: 'notes-list' }, r.map((g) => h('li', null, (g.from === g.to ? g.from : g.from + ' to ' + g.to) + ': ' + g.reason))));
  }

  /* ---------- summary block (one sentence that answers the page's question) ---------- */
  /* checkPoint: the point whose source the visible "Check this number" link opens (one per page summary). */
  function setSummary(nodes, meta, checkPoint) {
    const host = $('#summary-body');
    if (!host) return;
    clear(host);
    host.appendChild(h('p', { class: 'summary-text' }, nodes));
    const ch = checkPoint && checkHref(checkPoint.provenance_id);
    if (meta || ch) {
      host.appendChild(h('p', { class: 'summary-meta small muted' }, meta || null,
        ch ? [meta ? ' · ' : null, h('a', { class: 'num-check', href: ch }, 'Check this number')] : null));
    }
  }
  /* Scope chip: year · area · actual/forecast, first thing in a figure caption. */
  function scopeChip(year, area, status) {
    const st = status === 'forecast' ? 'Forecast' : (status === 'mixed' ? 'Actual and forecast' : (status === 'share' ? 'Share, not affected by prices' : 'Actual'));
    return h('span', { class: 'scope' }, [year, area, st].filter(Boolean).join(' · '));
  }
  function summaryState(text, kind) {
    const host = $('#summary-body');
    if (host) state(host, text, kind);
  }
  function metaLine(point, ix, b) {
    const parts = [point ? (point.status === 'forecast' ? 'Forecast figures' : 'Actual figures') : 'Figures'];
    parts.push(basisShort(b || basis));
    parts.push('last updated ' + updatedText(ix));
    return parts.join(' · ');
  }

  /* Horizontal bar list. rows: {label, sub, point, share:{text,spec}, barValue, forecast, valueNode} */
  function barList(rows, opts) {
    opts = opts || {};
    const max = opts.max || Math.max(...rows.map((r) => Math.abs(r.barValue || 0)), 0) || 1;
    const ul = h('ul', { class: 'bars' });
    rows.forEach((r) => {
      const pct = Math.max(0, Math.min(100, (Math.abs(r.barValue || 0) / max) * 100));
      const fill = h('span', { class: 'bar-fill' + (r.forecast ? ' forecast' : '') + (r.rest ? ' rest' : '') + (r.muted ? ' context' : ''), 'aria-hidden': 'true' });
      fill.style.width = pct.toFixed(2) + '%';
      const track = h('div', { class: 'bar-track' }, h('span', { class: 'bar-bg', 'aria-hidden': 'true' }, fill),
        r.share ? h('span', { class: 'bar-share' }, derivedNum(r.share.text, r.share.spec)) : null);
      const li = h('li', { class: 'bar-row' + (r.current ? ' is-current' : '') + (r.rest ? ' is-rest' : '') },
        h('div', { class: 'bar-label' }, r.href ? h('a', { href: r.href }, r.label) : r.label, r.sub ? h('span', { class: 'sub' }, r.sub) : null),
        track,
        h('div', { class: 'bar-value' }, r.valueNode || num(r.point, { label: r.fullLabel || r.label })));
      if (r.current) li.setAttribute('aria-current', 'true');
      ul.appendChild(li);
    });
    return opts.unitHead ? h('div', null, h('p', { class: 'bars-head small muted' }, opts.unitHead), ul) : ul;
  }
  /* Build bar rows for parts of £100. items: {label, value (float), point?, spec?, forecast?, sub?, fullLabel?, last?}
     Whole-pound amounts are chosen by the largest-remainder method so the shown amounts add up to £100. */
  function splitOf100(items) {
    const ints = largestRemainder(items.map((i) => i.value), 100);
    return items.map((it, k) => {
      const text = per100Int(ints[k]);
      return {
        label: it.label, sub: it.sub, fullLabel: it.fullLabel || it.label, barValue: it.value, forecast: it.forecast, int: ints[k], text, rest: it.rest, sid: it.sid, part: it.part, point: it.point, spec: it.spec,
        valueNode: it.point ? num(it.point, { label: it.fullLabel || it.label, text, badge: false }) : derivedNum(text, it.spec || { title: it.label, inputs: [] }),
      };
    });
  }

  /* Generic data table fallback for a chart. rows: arrays whose first cell is the row header. */
  function tableView(caption, headers, rows, summaryText) {
    const tb = h('tbody');
    rows.forEach((r) => {
      tb.appendChild(h('tr', null, r.map((c, i) => (i === 0 ? h('th', { scope: 'row' }, c) : h('td', { class: i === 1 ? 'r' : null }, c)))));
    });
    return h('details', { class: 'table-view' }, h('summary', null, summaryText || 'Show these numbers as a table'),
      h('div', { class: 'table-wrap' }, h('table', null, h('caption', null, caption),
        h('thead', null, h('tr', null, headers.map((t, i) => h('th', { scope: 'col', class: i === 1 ? 'r' : null }, t)))), tb)));
  }
  /* Table view of a series variant: every value with its check link. */
  function seriesTable(ser, points, caption, summaryText) {
    const tb = h('tbody');
    const years = new Set(points.map((p) => p.fiscal_year));
    (ser.gaps || []).forEach((g) => years.add(g.fiscal_year));
    [...years].sort().forEach((y) => {
      const p = points.find((x) => x.fiscal_year === y);
      const g = gapFor(ser, y);
      tb.appendChild(h('tr', null,
        h('th', { scope: 'row' }, y),
        h('td', { class: 'r' }, p ? num(p, { label: ser.title + ' ' + y, badge: false }) : h('span', { class: 'muted' }, 'Not published yet')),
        h('td', null, p ? badge(p.status) : (g ? g.reason : '')),
        h('td', null, p ? p.vintage : '')));
    });
    return h('details', { class: 'table-view' }, h('summary', null, summaryText || 'Show these numbers as a table'),
      h('div', { class: 'table-wrap' }, h('table', null, h('caption', null, caption),
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Year'), h('th', { scope: 'col', class: 'r' }, 'Amount'), h('th', { scope: 'col' }, 'Status'), h('th', { scope: 'col' }, 'Edition'))),
        tb)));
  }

  /* ---------- charts ---------- */
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
  function describeChart(svg, uid, title, desc) {
    svg.insertBefore(s('desc', { id: uid + 'd' }, desc), svg.firstChild);
    svg.insertBefore(s('title', { id: uid + 't' }, title), svg.firstChild);
    svg.setAttribute('aria-labelledby', uid + 't ' + uid + 'd');
  }
  /* Year labels on the x axis: all of them when they fit, otherwise first, last and evenly spaced. */
  function pickLabels(n, max) {
    const out = new Set();
    if (n <= max) { for (let i = 0; i < n; i += 1) out.add(i); return out; }
    const step = Math.ceil((n - 1) / Math.max(1, max - 1));
    let last = 0;
    for (let i = 0; i < n; i += step) { out.add(i); last = i; }
    if (last !== n - 1) { if (n - 1 - last < step * 0.6) out.delete(last); out.add(n - 1); }
    return out;
  }
  /* Split callout text into lines of at most 28 characters. */
  function annoLines(text) {
    const words = String(text).split(/\s+/); const lines = []; let cur = '';
    words.forEach((w) => { if ((cur + ' ' + w).trim().length > 28 && cur) { lines.push(cur); cur = w; } else cur = (cur + ' ' + w).trim(); });
    if (cur) lines.push(cur);
    return lines.slice(0, 2);
  }
  /* A plain callout drawn on the chart: text in a reserved strip above the plot, a leader down to the point.
     The same text is also given in the figure caption (the group is aria-hidden). */
  function drawAnno(svg, ax, ay, text, textY, W) {
    const lines = annoLines(text);
    const anchor = ax < W * 0.22 ? 'start' : (ax > W * 0.78 ? 'end' : 'middle');
    const tx = anchor === 'start' ? Math.max(2, ax - 8) : (anchor === 'end' ? Math.min(W - 2, ax + 8) : ax);
    const g = s('g', { class: 'anno', 'aria-hidden': 'true' });
    const lastY = textY + 15 * (lines.length - 1);
    if (ay - 6 > lastY + 6) g.appendChild(s('line', { class: 'anno-leader', x1: ax, x2: ax, y1: lastY + 6, y2: ay - 6 }));
    g.appendChild(s('circle', { class: 'anno-dot', cx: ax, cy: ay, r: 3.5 }));
    const t = s('text', { class: 'anno-text', x: tx, y: textY, 'text-anchor': anchor });
    lines.forEach((ln, k) => t.appendChild(s('tspan', { x: tx, dy: k ? 15 : 0 }, ln)));
    g.appendChild(t);
    svg.appendChild(g);
  }
  function hatchDefs(uid) {
    return s('defs', null, s('pattern', { id: uid + 'h', width: 6, height: 6, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' },
      s('rect', { width: 6, height: 6, class: 'hatch-bg' }), s('rect', { width: 2.5, height: 6, class: 'hatch-fg' })));
  }
  function colPath(x0, top, bot, bw, up) {
    const hgt = Math.max(1, bot - top); const r = Math.min(4, bw / 2, hgt);
    return up
      ? `M${x0},${bot}V${top + r}Q${x0},${top} ${x0 + r},${top}H${x0 + bw - r}Q${x0 + bw},${top} ${x0 + bw},${top + r}V${bot}Z`
      : `M${x0},${top}V${bot - r}Q${x0},${bot} ${x0 + r},${bot}H${x0 + bw - r}Q${x0 + bw},${bot} ${x0 + bw},${bot - r}V${top}Z`;
  }
  function legendLine(dashed) {
    return h('span', { class: 'sw line' + (dashed ? ' dashed' : ''), 'aria-hidden': 'true' });
  }

  /* One series over time as columns. Keeps keyboard arrows + click-for-source on every column.
     opts: {heading, caption, sub, scope, fcLabel, annotations:[{year,text}], behind:{points,label,legend}} */
  function columnChart(ser, points, opts) {
    opts = opts || {};
    const wrap = h('div', { class: 'chart' });
    const tip = h('div', { class: 'tip', hidden: true, role: 'presentation' });
    const uid = 'c' + (++chartSeq);
    const behind = opts.behind && opts.behind.points && opts.behind.points.length ? opts.behind : null;
    const years = new Set(points.map((p) => p.fiscal_year));
    (ser.gaps || []).forEach((g) => years.add(g.fiscal_year));
    if (behind) behind.points.forEach((p) => years.add(p.fiscal_year));
    const yrs = [...years].sort();
    const hasFc = points.some((p) => p.status === 'forecast');
    const hasGap = (ser.gaps || []).length > 0;
    const unit = points[0] ? points[0].unit : '';
    const heading = opts.title || opts.heading || ser.title;
    const fcText = opts.fcLabel || 'Forecast';
    const annos = (opts.annotations || []).filter((a) => a && yrs.includes(a.year)).slice(0, 2);

    function draw() {
      const W = Math.max(280, wrap.clientWidth || 640);
      const narrow = W < 520;
      const H0 = narrow ? 220 : 260;
      let top = 22; let annoY = 0; let fcY = 0;
      if (annos.length) { annoY = top + 14; top += Math.max(...annos.map((a) => annoLines(a.text).length)) * 15 + 14; }
      if (hasFc) { fcY = top + 14; top += 22; }
      const m = { l: 46, r: 8, t: top + 6, b: 30 };
      const H = H0 + m.t - 24;
      const iw = W - m.l - m.r; const ih = H - m.t - m.b;
      const vals = points.map((p) => p.value).concat(behind ? behind.points.map((p) => p.value) : []);
      const lo = Math.min(0, ...vals); const hi = Math.max(0, ...vals);
      const ticks = niceTicks(lo, hi, narrow ? 3 : 4);
      const d0 = ticks[0]; const d1 = ticks[ticks.length - 1];
      const y = (v) => m.t + ih - ((v - d0) / (d1 - d0 || 1)) * ih;
      const band = iw / Math.max(1, yrs.length);
      const bw = Math.max(4, Math.min(band - 4, band * 0.72, 44));
      const x = (i) => m.l + band * i + (band - bw) / 2;
      const svg = s('svg', { viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'group' });
      describeChart(svg, uid, heading + ', ' + yrs[0] + ' to ' + yrs[yrs.length - 1],
        (opts.caption ? opts.caption + ' ' : '') + annos.map((a) => a.text + '.').join(' ') + ' Use the arrow keys to move between years. The same numbers are in the table below.');
      svg.setAttribute('aria-label', heading + ', ' + yrs[0] + ' to ' + yrs[yrs.length - 1] + '. Use arrow keys to move between years.');
      svg.appendChild(hatchDefs(uid));
      const at = opts.axisTitle || axisTitle(unit);
      if (at) svg.appendChild(s('text', { class: 'axis-title', x: 0, y: 13 }, at));
      const fcIdx = yrs.map((yy, i) => (points.find((p) => p.fiscal_year === yy && p.status === 'forecast') ? i : -1)).filter((i) => i >= 0);
      if (fcIdx.length) {
        const fx = m.l + band * fcIdx[0];
        svg.appendChild(s('rect', { class: 'fc-band', x: fx, y: fcY - 16, width: band * fcIdx.length, height: m.t + ih - (fcY - 16) }));
        const right = fx > W * 0.6;
        svg.appendChild(s('text', { class: 'fc-label', x: right ? Math.min(W - 4, fx + band * fcIdx.length - 4) : fx + 6, y: fcY, 'text-anchor': right ? 'end' : 'start' }, fcText + ' →'));
      }
      ticks.forEach((t) => {
        svg.appendChild(s('line', { class: t === 0 ? 'zero' : 'grid-line', x1: m.l, x2: W - m.r, y1: y(t), y2: y(t) }));
        svg.appendChild(s('text', { class: 'tick', x: m.l - 6, y: y(t) + 4, 'text-anchor': 'end' }, fmtShort(t, unit)));
      });
      const show = pickLabels(yrs.length, narrow ? 5 : Math.max(2, Math.floor(iw / 64)));
      yrs.forEach((yy, i) => {
        if (show.has(i)) svg.appendChild(s('text', { class: 'tick', x: m.l + band * i + band / 2, y: H - 10, 'text-anchor': 'middle' }, narrow ? yy.slice(2) : yy));
      });
      const lastOut = [...points].reverse().find((p) => p.status !== 'forecast');
      const lastAll = points[points.length - 1];
      const annoYears = new Set(annos.map((a) => a.year));
      const groups = [];
      yrs.forEach((yy, i) => {
        const p = points.find((q) => q.fiscal_year === yy);
        const bp = behind ? behind.points.find((q) => q.fiscal_year === yy) : null;
        const g = s('g', { class: 'pt', tabindex: '-1', role: 'button' });
        if (bp) {
          const top0 = y(Math.max(0, bp.value)); const bot0 = y(Math.min(0, bp.value));
          g.appendChild(s('path', { class: 'col back', d: colPath(x(i), top0, bot0, bw, bp.value >= 0) }));
        }
        if (p) {
          const top0 = y(Math.max(0, p.value)); const bot0 = y(Math.min(0, p.value));
          const up = p.value >= 0;
          const iwc = behind ? bw * 0.56 : bw; const x0 = x(i) + (bw - iwc) / 2;
          const fc = p.status === 'forecast';
          const col = s('path', { class: 'col' + (fc ? ' forecast' : ''), d: colPath(x0, top0, bot0, iwc, up) });
          if (fc) col.style.setProperty('fill', 'url(#' + uid + 'h)');
          g.appendChild(col);
          if (!annoYears.has(yy) && (p === lastOut || (p === lastAll && p !== lastOut) || (!narrow && i === 0))) {
            const lt = bp && bp.value > p.value ? y(bp.value) : top0;
            g.appendChild(s('text', { class: 'dlabel', x: x(i) + bw / 2, y: (up ? lt : bot0 + 12) - 5, 'text-anchor': 'middle' }, fmtShort(p.value, p.unit)));
          }
          g.setAttribute('aria-label', yy + ': ' + fmt(p.value, p.unit) + (fc ? ', forecast' : ', actual') + (bp ? '; ' + (behind.label || 'other total') + ' ' + fmt(bp.value, bp.unit) : '') + '. Press Enter for the source.');
        } else {
          g.appendChild(s('line', { class: 'gap-mark', x1: x(i), x2: x(i) + bw, y1: y(0) - 2, y2: y(0) - 2 }));
          const gg = gapFor(ser, yy);
          g.setAttribute('aria-label', yy + ': not published yet. ' + (gg ? gg.reason : ''));
        }
        g.appendChild(s('rect', { class: 'hit', x: m.l + band * i, y: m.t, width: band, height: ih }));
        const showTip = () => {
          clear(tip);
          append(tip, [h('strong', null, yy)]);
          if (p) append(tip, [fmt(p.value, p.unit), ' ', unitNote(p.unit), h('br'), p.status === 'forecast' ? 'Forecast' : 'Actual', ' · ', p.vintage]);
          else { const gg = gapFor(ser, yy); append(tip, ['Not published yet', h('br'), gg ? gg.reason : '']); }
          if (bp) append(tip, [h('br'), (behind.label || 'Other total') + ': ' + fmt(bp.value, bp.unit)]);
          if (p) append(tip, [h('br'), 'Click or press Enter for the source']);
          tip.hidden = false;
          const sc = wrap.clientWidth / W;
          const cx = (m.l + band * i + band / 2) * sc;
          const tw = tip.offsetWidth;
          tip.style.left = Math.max(0, Math.min(cx - tw / 2, wrap.clientWidth - tw)) + 'px';
          const topV = Math.max(p ? p.value : 0, bp ? bp.value : 0, 0);
          tip.style.top = Math.max(0, (y(topV) * sc) - tip.offsetHeight - 10) + 'px';
        };
        const hide = () => { tip.hidden = true; };
        const activate = () => { if (p) openPop(g, { kind: 'point', id: p.provenance_id, point: p, label: heading + ' ' + yy }); };
        g.addEventListener('pointerenter', showTip); g.addEventListener('pointerleave', hide);
        g.addEventListener('focus', showTip); g.addEventListener('blur', hide);
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
      annos.forEach((a) => {
        const i = yrs.indexOf(a.year); const p = points.find((q) => q.fiscal_year === a.year);
        if (i < 0 || !p) return;
        drawAnno(svg, x(i) + bw / 2, y(Math.max(0, p.value)), a.text, annoY, W);
      });
      const start = groups.length ? (lastOut ? yrs.indexOf(lastOut.fiscal_year) : groups.length - 1) : -1;
      if (start >= 0) groups[start].setAttribute('tabindex', '0');
      const old = wrap.querySelector('svg');
      if (old) old.replaceWith(svg); else wrap.insertBefore(svg, tip);
    }
    wrap.appendChild(tip);
    const legend = h('p', { class: 'chart-legend' },
      h('span', null, h('span', { class: 'sw', 'aria-hidden': 'true' }), behind ? (opts.mainLegend || 'Actual') : 'Actual'),
      behind ? h('span', null, h('span', { class: 'sw back', 'aria-hidden': 'true' }), behind.legend || behind.label) : null,
      hasFc ? h('span', null, h('span', { class: 'sw fc', 'aria-hidden': 'true' }), fcText + ' (hatched)') : null,
      hasGap ? h('span', null, h('span', { class: 'sw gap', 'aria-hidden': 'true' }), 'Not published yet (see note)') : null);
    const out = h('figure', { class: 'card chart-fig' },
      opts.heading || opts.caption || opts.sub || opts.scope ? h('figcaption', null,
        opts.scope || null,
        opts.heading ? h('h3', null, opts.heading) : null,
        opts.caption ? h('p', { class: 'caption-text' }, opts.caption) : null,
        opts.sub ? h('p', { class: 'small muted' }, opts.sub) : null) : null,
      wrap, legend, h('p', { class: 'chart-key small muted' }, 'Click any column to see where the number came from.'));
    draw();
    requestAnimationFrame(draw);
    let lastW = 0;
    if ('ResizeObserver' in window) {
      new ResizeObserver(() => { const w = wrap.clientWidth; if (w && Math.abs(w - lastW) > 8) { lastW = w; draw(); } }).observe(wrap);
    }
    return out;
  }

  /* Ten-year line. Actual years are solid, forecast years dashed over a labelled band. Drawn at the
     container's real width so labels stay readable on phones.
     spec: {title, heading, caption, sub, scope, points (sorted), gaps, source, tableCaption, ser, axisTitle, annotations, fcLabel} */
  function lineChart(spec) {
    const points = (spec.points || []).slice().sort((a, b) => a.fiscal_year.localeCompare(b.fiscal_year));
    const gaps = spec.gaps || [];
    const uid = 'l' + (++chartSeq);
    const wrap = h('div', { class: 'chart' });
    const yrs = [...new Set([...points.map((p) => p.fiscal_year), ...gaps.map((g) => g.fiscal_year)])].sort();
    const unit = points[0] ? points[0].unit : '';
    const hasFc = points.some((p) => p.status === 'forecast');
    const fcText = spec.fcLabel || 'Forecast';
    const annos = (spec.annotations || []).filter((a) => a && yrs.includes(a.year)).slice(0, 2);
    const desc = (spec.caption || (spec.title + ', ' + yrs[0] + ' to ' + yrs[yrs.length - 1] + '.')) + (annos.length ? ' ' + annos.map((a) => a.text + '.').join(' ') : '');

    function draw() {
      const W = Math.max(280, wrap.clientWidth || 640);
      const narrow = W < 480;
      let top = 22; let annoY = 0; let fcY = 0;
      if (annos.length) { annoY = top + 14; top += Math.max(...annos.map((a) => annoLines(a.text).length)) * 15 + 14; }
      if (hasFc) { fcY = top + 14; top += 22; }
      const vals = points.map((p) => p.value);
      const ticks = niceTicks(Math.min(0, ...vals), Math.max(0, ...vals), narrow ? 3 : 4);
      /* left margin fits the longest tick label (12px text, ~6.6px a character) */
      const tickW = Math.max(...ticks.map((t) => String(fmtShort(t, unit)).length)) * 6.6;
      const m = { l: Math.max(48, Math.ceil(tickW) + 12), r: narrow ? 26 : 34, t: top + 10, b: 30 };
      const H = (narrow ? 230 : 270) + m.t - 28;
      const iw = W - m.l - m.r; const ih = H - m.t - m.b;
      const d0 = ticks[0]; const d1 = ticks[ticks.length - 1];
      const y = (v) => m.t + ih - ((v - d0) / (d1 - d0 || 1)) * ih;
      const step = iw / Math.max(1, yrs.length - 1);
      const x = (i) => m.l + step * i;
      const svg = s('svg', { viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img' });
      describeChart(svg, uid, spec.title, desc);
      const at = spec.axisTitle || axisTitle(unit);
      if (at) svg.appendChild(s('text', { class: 'axis-title', x: 0, y: 13 }, at));
      const fcIdx = yrs.map((yy, i) => (points.find((p) => p.fiscal_year === yy && p.status === 'forecast') ? i : -1)).filter((i) => i >= 0);
      if (fcIdx.length) {
        const fx = Math.max(m.l, x(fcIdx[0]) - step / 2);
        const fw = Math.min(W - m.r, x(fcIdx[fcIdx.length - 1]) + step / 2) - fx;
        svg.appendChild(s('rect', { class: 'fc-band', x: fx, y: fcY - 16, width: fw, height: m.t + ih - (fcY - 16) }));
        const right = fx > W * 0.55;
        svg.appendChild(s('text', { class: 'fc-label', x: right ? fx + fw - 4 : fx + 6, y: fcY, 'text-anchor': right ? 'end' : 'start' }, fcText + ' →'));
      }
      ticks.forEach((t) => {
        svg.appendChild(s('line', { class: t === 0 ? 'zero' : 'grid-line', x1: m.l, x2: W - m.r, y1: y(t), y2: y(t) }));
        svg.appendChild(s('text', { class: 'tick', x: m.l - 6, y: y(t) + 4, 'text-anchor': 'end' }, fmtShort(t, unit)));
      });
      const show = pickLabels(yrs.length, narrow ? 5 : Math.max(2, Math.floor(iw / 64)));
      yrs.forEach((yy, i) => {
        if (show.has(i)) svg.appendChild(s('text', { class: 'tick', x: x(i), y: H - 10, 'text-anchor': 'middle' }, narrow ? yy.slice(2) : yy));
      });
      const byYear = new Map(points.map((p) => [p.fiscal_year, p]));
      let cur = null;
      const segs = [];
      for (let i = 0; i < yrs.length - 1; i += 1) {
        const a = byYear.get(yrs[i]); const b = byYear.get(yrs[i + 1]);
        if (!a || !b) { cur = null; continue; }
        const cls = 'line' + (b.status === 'forecast' ? ' forecast' : '');
        if (cur && cur.cls === cls) cur.d += 'L' + x(i + 1) + ',' + y(b.value);
        else { cur = { cls, d: 'M' + x(i) + ',' + y(a.value) + 'L' + x(i + 1) + ',' + y(b.value) }; segs.push(cur); }
      }
      segs.forEach((sg) => svg.appendChild(s('path', { class: sg.cls, d: sg.d, fill: 'none' })));
      yrs.forEach((yy, i) => {
        if (!byYear.has(yy)) svg.appendChild(s('line', { class: 'gap-mark', x1: x(i) - 6, x2: x(i) + 6, y1: y(0) - 3, y2: y(0) - 3 }));
      });
      const annoYears = new Set(annos.map((a) => a.year));
      const first = points[0]; const last = points[points.length - 1];
      [first, last].filter((p, k, arr) => p && arr.indexOf(p) === k).forEach((p) => {
        const i = yrs.indexOf(p.fiscal_year);
        svg.appendChild(s('circle', { class: 'dot', cx: x(i), cy: y(p.value), r: 3.5 }));
        if (annoYears.has(p.fiscal_year)) return;
        const anchor = p === first ? 'start' : 'end';
        svg.appendChild(s('text', { class: 'dlabel', x: x(i) + (p === first ? -2 : 2), y: y(p.value) - 9, 'text-anchor': anchor }, fmtShort(p.value, p.unit)));
      });
      annos.forEach((a) => {
        const i = yrs.indexOf(a.year); const p = byYear.get(a.year);
        if (i < 0 || !p) return;
        drawAnno(svg, x(i), y(p.value), a.text, annoY, W);
      });
      const old = wrap.querySelector('svg');
      if (old) old.replaceWith(svg); else wrap.appendChild(svg);
    }
    draw();
    requestAnimationFrame(draw);
    let lastW = 0;
    if ('ResizeObserver' in window) {
      new ResizeObserver(() => { const w = wrap.clientWidth; if (w && Math.abs(w - lastW) > 8) { lastW = w; draw(); } }).observe(wrap);
    }
    const legend = h('p', { class: 'chart-legend' },
      h('span', null, legendLine(false), 'Actual'),
      hasFc ? h('span', null, legendLine(true), fcText + ' (dashed)') : null,
      gaps.length ? h('span', null, h('span', { class: 'sw gap', 'aria-hidden': 'true' }), 'Not published yet') : null);
    return h('figure', { class: 'card chart-fig' },
      h('figcaption', null, spec.scope || null, spec.heading ? h('h3', null, spec.heading) : null, spec.caption ? h('p', { class: 'caption-text' }, spec.caption) : null, spec.sub ? h('p', { class: 'small muted' }, spec.sub) : null),
      wrap, legend,
      spec.source ? h('p', { class: 'small muted' }, spec.source) : null,
      spec.table || (spec.ser ? seriesTable(spec.ser, points, spec.tableCaption || spec.title) : null));
  }

  /* 100 squares: each square is £1 out of every £100. One highlighted category per grid.
     spec: {on, hatch, title, caption, keyOn, keyHatch, keyOff, source, table, bracket (label for the filled part),
            bracketHatch (label for the hatched part), size: 'lg'} */
  function squares(spec) {
    const on = Math.max(0, Math.min(100, spec.on || 0));
    const hatch = Math.max(0, Math.min(100 - on, spec.hatch || 0));
    const uid = 'q' + (++chartSeq);
    const brk = spec.bracket && on > 0;
    const brkH = spec.bracketHatch && hatch > 0;
    const vbW = 218 + (brk || brkH ? 78 : 0);
    const svg = s('svg', { viewBox: '0 0 ' + vbW + ' 218', role: 'img', class: brk || brkH ? 'has-bracket' : null });
    describeChart(svg, uid, spec.title, on + ' of 100 squares are filled' + (hatch ? ' and ' + hatch + ' are hatched' : '') + '.');
    if (hatch) svg.appendChild(hatchDefs(uid));
    for (let i = 0; i < 100; i += 1) {
      const filled = i < on; const hatched = !filled && i < on + hatch;
      const r = s('rect', { class: 'sq' + (filled ? ' on' : '') + (hatched ? ' hatch' : ''), x: (i % 10) * 22, y: Math.floor(i / 10) * 22, width: 20, height: 20, rx: 3 });
      if (hatched) r.style.setProperty('fill', 'url(#' + uid + 'h)');
      svg.appendChild(r);
    }
    /* Brackets on the right edge: one spanning the filled rows, one spanning the hatched rows. */
    const bracket = (r0, r1, label) => {
      const y0 = r0 * 22 + 1; const y1 = r1 * 22 - 3; const bx = 226;
      const g = s('g', { class: 'anno', 'aria-hidden': 'true' });
      g.appendChild(s('path', { class: 'anno-bracket', d: `M${bx - 4},${y0}H${bx}V${y1}H${bx - 4}M${bx},${(y0 + y1) / 2}H${bx + 6}` }));
      g.appendChild(s('text', { class: 'anno-big', x: bx + 10, y: (y0 + y1) / 2 + 7 }, label));
      svg.appendChild(g);
    };
    if (brk) bracket(0, Math.max(1, Math.ceil(on / 10)), spec.bracket);
    if (brkH) bracket(Math.floor(on / 10) + (on % 10 && Math.ceil((on + hatch) / 10) - Math.floor(on / 10) > 1 ? 1 : 0), Math.ceil((on + hatch) / 10), spec.bracketHatch);
    const key = h('p', { class: 'squares-key small' },
      h('span', null, h('span', { class: 'sw on', 'aria-hidden': 'true' }), spec.keyOn || (per100Int(on) + ' filled')),
      hatch ? h('span', null, h('span', { class: 'sw hatch', 'aria-hidden': 'true' }), spec.keyHatch || (per100Int(hatch) + ' hatched')) : null,
      spec.keyOff === false ? null : h('span', null, h('span', { class: 'sw', 'aria-hidden': 'true' }), spec.keyOff || (per100Int(100 - on - hatch) + ' everything else')));
    return h('figure', { class: 'card chart squares' + (spec.size === 'lg' ? ' lg' : '') },
      h('figcaption', null, spec.scope || null, h('span', { class: 'sq-cap' }, spec.caption)), svg, key,
      spec.source ? h('p', { class: 'small muted' }, spec.source) : null, spec.table || null);
  }

  /* One 10×10 grid split into several blocks (the whole £100). Blocks are runs of squares in reading
     order, in stepped blues, each with a direct label (no colour-only key).
     blocks: [{label, n, tone: 1..4 | 'rest'}] */
  function partitionGrid(spec) {
    const blocks = spec.blocks.filter((b) => b.n > 0);
    const uid = 'pg' + (++chartSeq);
    const wrap = h('div', { class: 'chart pgrid' });
    const keyList = h('ol', { class: 'pgrid-key' }, blocks.map((b) => h('li', null,
      h('span', { class: 'sw tone-' + b.tone, 'aria-hidden': 'true' }), h('strong', null, '£' + b.n), ' ', b.label)));
    function draw() {
      const W = Math.max(260, wrap.clientWidth || 600);
      const wide = W >= 520;
      const G = wide ? Math.min(300, W * 0.5) : Math.min(300, W * 0.82);
      const pitch = G / 10; const sz = pitch - 3;
      const LW = wide ? W - G - 24 : 0;
      const Wsvg = wide ? G + 24 + LW : G;
      const svg = s('svg', { viewBox: '0 0 ' + Wsvg + ' ' + G, width: Wsvg, height: G, role: 'img' });
      describeChart(svg, uid, spec.title, blocks.map((b) => b.label + ': ' + b.n + ' squares').join('; ') + '.');
      let i = 0;
      const starts = [];
      blocks.forEach((b) => {
        starts.push(i);
        for (let k = 0; k < b.n && i < 100; k += 1, i += 1) {
          svg.appendChild(s('rect', { class: 'sq tone-' + b.tone, x: (i % 10) * pitch, y: Math.floor(i / 10) * pitch, width: sz, height: sz, rx: 2.5 }));
        }
      });
      for (; i < 100; i += 1) svg.appendChild(s('rect', { class: 'sq', x: (i % 10) * pitch, y: Math.floor(i / 10) * pitch, width: sz, height: sz, rx: 2.5 }));
      if (wide) {
        /* labels at each block's middle row, pushed apart so they never overlap */
        const want = blocks.map((b, k) => {
          const r0 = Math.floor(starts[k] / 10); const r1 = Math.floor((starts[k] + b.n - 1) / 10);
          return { y: ((r0 + r1 + 1) / 2) * pitch - 1.5, r0, k };
        });
        const gap = 34; const ys = want.map((w) => w.y);
        for (let k = 1; k < ys.length; k += 1) ys[k] = Math.max(ys[k], ys[k - 1] + gap);
        const over = ys[ys.length - 1] - (G - 10);
        if (over > 0) { for (let k = ys.length - 1; k >= 0; k -= 1) { ys[k] -= over; if (k && ys[k - 1] > ys[k] - gap) ys[k - 1] = ys[k] - gap; } }
        blocks.forEach((b, k) => {
          const g = s('g', { class: 'anno', 'aria-hidden': 'true' });
          const ly = Math.max(12, ys[k]);
          g.appendChild(s('path', { class: 'anno-leader', d: `M${G + 2},${want[k].y}L${G + 14},${ly}H${G + 20}` }));
          const t = s('text', { class: 'pg-label', x: G + 24, y: ly + 5 });
          t.appendChild(s('tspan', { class: 'pg-amt' }, '£' + b.n + ' '));
          t.appendChild(s('tspan', null, b.short || b.label));
          g.appendChild(t);
          svg.appendChild(g);
        });
      }
      keyList.hidden = wide;
      const old = wrap.querySelector('svg');
      if (old) old.replaceWith(svg); else wrap.insertBefore(svg, keyList);
    }
    wrap.appendChild(keyList);
    const fig = h('figure', { class: 'card chart-fig' },
      h('figcaption', null, spec.scope || null, spec.caption ? h('p', { class: 'caption-text' }, spec.caption) : null), wrap,
      spec.note ? h('p', { class: 'small muted' }, spec.note) : null, spec.source ? h('p', { class: 'small muted' }, spec.source) : null, spec.table || null);
    draw(); requestAnimationFrame(draw);
    let lastW = 0;
    if ('ResizeObserver' in window) new ResizeObserver(() => { const w = wrap.clientWidth; if (w && Math.abs(w - lastW) > 8) { lastW = w; draw(); } }).observe(wrap);
    return fig;
  }

  /* People pictogram: 100 person glyphs, the first n filled ("n in every 100 people"). */
  function peopleGrid(spec) {
    const n = Math.max(0, Math.min(100, spec.on || 0));
    const uid = 'pp' + (++chartSeq);
    const svg = s('svg', { viewBox: '0 0 200 250', role: 'img', class: 'people' });
    describeChart(svg, uid, spec.title, n < 1 ? 'Fewer than 1 in every 100.' : n + ' of 100 people are filled.');
    const sym = s('symbol', { id: uid + 'p', viewBox: '0 0 12 18' },
      s('circle', { cx: 6, cy: 3.6, r: 3.3 }), s('path', { d: 'M1,17.5V11.5Q1,8 4.5,8H7.5Q11,8 11,11.5V17.5Z' }));
    svg.appendChild(s('defs', null, sym));
    for (let i = 0; i < 100; i += 1) {
      svg.appendChild(s('use', { href: '#' + uid + 'p', class: 'pp' + (i < n ? ' on' : ''), x: (i % 10) * 20 + 2, y: Math.floor(i / 10) * 25 + 1, width: 16, height: 23 }));
    }
    return h('figure', { class: 'card chart squares people-fig' },
      h('figcaption', null, spec.scope || null, h('span', { class: 'sq-cap' }, spec.caption)), svg,
      h('p', { class: 'squares-key small' }, h('span', null, h('span', { class: 'sw on', 'aria-hidden': 'true' }), spec.keyOn),
        h('span', null, h('span', { class: 'sw', 'aria-hidden': 'true' }), spec.keyOff)),
      spec.source ? h('p', { class: 'small muted' }, spec.source) : null);
  }

  /* A single 100% strip (parts of £100), labels above each segment. parts: [{label, n, tone, node}] */
  function stackStrip(spec) {
    const strip = h('div', { class: 'strip', role: 'img', 'aria-label': spec.title + ': ' + spec.parts.map((p) => p.label + ' £' + p.n).join(', ') });
    const labels = h('div', { class: 'strip-labels', 'aria-hidden': 'true' });
    spec.parts.forEach((p) => {
      const seg = h('span', { class: 'strip-seg tone-' + p.tone }); seg.style.flexGrow = String(p.n);
      strip.appendChild(seg);
      const lab = h('span', { class: 'strip-lab' }, h('strong', null, '£' + p.n), h('span', null, p.label)); lab.style.flexGrow = String(p.n);
      labels.appendChild(lab);
    });
    return h('div', { class: 'strip-fig' }, spec.head ? h('p', { class: 'strip-head small' }, spec.head) : null, labels, strip,
      h('p', { class: 'visually-hidden' }, spec.parts.map((p) => p.label + ': £' + p.n + ' out of every £100').join('. ') + '.'));
  }

  /* Several totals on one shared £ scale, smallest first: shows that bigger totals count more things.
     rows: [{label, point, note}], all for the same year and basis. */
  function ruler(spec) {
    const rows = spec.rows.slice().sort((a, b) => a.point.value - b.point.value);
    const max = rows[rows.length - 1].point.value || 1;
    const list = h('ol', { class: 'ruler' });
    rows.forEach((r, k) => {
      const pct = Math.max(0.5, (r.point.value / max) * 100);
      const prev = k ? rows[k - 1] : null;
      const fill = h('span', { class: 'ruler-fill' }); fill.style.width = pct.toFixed(2) + '%';
      let shared = null;
      if (prev) { shared = h('span', { class: 'ruler-shared' }); shared.style.width = ((prev.point.value / max) * 100).toFixed(2) + '%'; }
      const extra = prev ? r.point.value - prev.point.value : null;
      list.appendChild(h('li', { class: 'ruler-row' },
        h('div', { class: 'ruler-top' }, h('span', { class: 'ruler-label' }, r.label), h('span', { class: 'ruler-val' }, num(r.point, { label: r.label + ', ' + r.point.fiscal_year, badge: false }))),
        h('div', { class: 'ruler-track', 'aria-hidden': 'true' }, fill, shared),
        extra != null && extra > 0 ? h('p', { class: 'ruler-extra small' }, h('span', { 'aria-hidden': 'true' }, '+ '),
          derivedNum(moneyWords(extra), { title: 'Difference between two totals', text: r.label + ' minus ' + prev.label + ', ' + r.point.fiscal_year + '.', formula: r.label + ' − ' + prev.label,
            inputs: [{ label: r.label, id: r.point.provenance_id, value: fmt(r.point.value, r.point.unit) }, { label: prev.label, id: prev.point.provenance_id, value: fmt(prev.point.value, prev.point.unit) }] }),
          ' more than the line above' + (r.note ? ': ' + r.note : '.')) : (r.note ? h('p', { class: 'ruler-extra small' }, r.note) : null)));
    });
    return h('figure', { class: 'card chart-fig ruler-fig' },
      h('figcaption', null, spec.scope || null, spec.caption ? h('p', { class: 'caption-text' }, spec.caption) : null),
      list, h('p', { class: 'chart-legend' }, h('span', null, h('span', { class: 'sw', 'aria-hidden': 'true' }), 'What the total counts'),
        h('span', null, h('span', { class: 'sw shared', 'aria-hidden': 'true' }), 'Already counted in the line above')),
      spec.table || null);
  }

  /* One benefit's figures for a year, all on the same price basis, so the overview and the explainer agree.
     DWP publishes total cost in both cash and real terms, but cost per claimant and per person only in cash.
     In real terms we scale those by the benefit's own real ÷ cash ratio and say so in the popover.
     Benefit figures have no "share of the economy" version, so that view falls back to cash with a note. */
  /* A small stand-in for a benefit's own file, built from its benefits/index.json entry (headline year only),
     so the list and comparison bars do not download every benefit file. */
  function benefitSlim(entry) {
    const hd = entry.headline || {};
    const one = (p) => (p ? [p] : []);
    return { slug: entry.slug, name: entry.name, in_payment: entry.caseload_basis === 'in_payment', spend: one(hd.spend), spend_real: one(hd.spend_real), claimants: one(hd.claimants),
      cost_per_claimant: one(hd.cost_per_claimant), share_of_welfare: one(hd.share_of_welfare) };
  }
  function benefitView(d, year) {
    const at = (arr) => (arr || []).find((p) => p.fiscal_year === year) || null;
    const spendN = at(d.spend); const spendR = at(d.spend_real);
    const mode = basis === 'real' && spendR ? 'real' : 'nominal';
    const factor = spendR && spendN && spendN.value ? spendR.value / spendN.value : null;
    const name = d.name;
    function scaled(pt, label, suffix) {
      if (!pt) return { value: null, node: num(null), point: null };
      if (mode === 'nominal' || !factor) return { value: pt.value, point: pt, node: num(pt, { label: name + ': ' + label + ', ' + year, badge: false }) };
      const v = pt.value * factor;
      return { value: v, point: pt, node: derivedNum(fmt(v, pt.unit) + (suffix || ''), {
        title: name + ': ' + label + ', adjusted for rising prices', text: 'DWP publishes this only as spent at the time. We adjust it by the same amount as the benefit’s total cost (' + year + ').',
        formula: 'Amount × (cost adjusted for prices ÷ cost as spent)',
        inputs: [{ label: label + ', as spent', id: pt.provenance_id, value: fmt(pt.value, pt.unit) }, { label: 'Total cost, adjusted for prices', id: spendR.provenance_id, value: fmt(spendR.value, spendR.unit) },
          { label: 'Total cost, as spent', id: spendN.provenance_id, value: fmt(spendN.value, spendN.unit) }] }) };
    }
    const spend = mode === 'real' ? spendR : spendN;
    return {
      mode, year, spend, spendN, spendR,
      spendNode: spend ? num(spend, { label: name + ': total cost, ' + year, badge: false }) : num(null),
      claimants: at(d.claimants), share: at(d.share_of_welfare),
      perClaimant: scaled(at(d.cost_per_claimant), 'cost for each person getting it'),
      perPerson: scaled(at(d.spend_per_person), 'cost for each person in the country'),
      basisWords: mode === 'real' ? 'adjusted for rising prices, in ' + (spendR && /\d{4}-\d{2}$/.test(spendR.unit) ? spendR.unit.slice(-7) : 'today’s') + ' prices' : 'as spent at the time',
      pctNote: basis === 'pct_gdp' ? 'Benefit figures are not published as a share of the economy, so they are shown as spent at the time.' : null,
    };
  }

  /* "Welfare costs…" Which welfare? Three published totals for the same year on one scale, smallest first,
     each bigger one counting more things. Shared by the home page and benefits.html#totals. */
  const WELFARE_RULER = [
    { id: 'dwp_benefits.exp.total_benefit_expenditure', label: 'DWP benefits, Great Britain', note: 'benefits paid by the Department for Work and Pensions in England, Scotland and Wales.' },
    { id: 'dwp_benefits.total_uk_welfare', label: 'All UK welfare', note: 'adds Northern Ireland and welfare paid by other departments.' },
    { id: 'pesa_uk.social_protection', label: 'Social protection, all UK public spending', note: 'the international definition, which also counts things like social care and public service pensions.' },
  ];
  async function welfareRuler(year) {
    const data = await seriesMany(WELFARE_RULER.map((r) => r.id));
    const ok = WELFARE_RULER.filter((r) => data[r.id]);
    if (ok.length < 2) return gapBox('We can’t show the welfare totals side by side yet: they are not all in this build.');
    // One basis for every row, so the lengths compare like with like.
    const want = basis === 'real' ? 'real' : 'nominal';
    const v = ok.every((r) => pointFor(data[r.id], want, year)) ? want : 'nominal';
    const rows = ok.map((r) => ({ label: r.label, note: r.note, point: pointFor(data[r.id], v, year) })).filter((r) => r.point);
    if (rows.length < 2) return gapBox('We can’t show the welfare totals side by side for ' + year + ': not every total is published for that year.');
    const fell = basis === 'pct_gdp' || (basis === 'real' && v !== 'real');
    const tb = rows.slice().sort((a, b) => a.point.value - b.point.value).map((r) => [r.label, num(r.point, { label: r.label + ', ' + year, badge: false }), r.point.vintage]);
    return ruler({
      rows,
      scope: scopeChip(year, 'UK and Great Britain', rows.some((r) => r.point.status === 'forecast') ? 'mixed' : 'actual'),
      caption: 'Three totals for welfare in ' + year + ', ' + basisShort(v) + '. Each bigger total counts more things.' + (fell ? ' Shown as spent at the time, because not every total has the other measures.' : ''),
      table: tableView('Welfare totals, ' + year, ['Total', 'Amount', 'Edition'], tb),
    });
  }

  /* ---------- "For checkers": sources, exact cells, cross-checks and method, closed by default ---------- */
  function reconPanel(r, ids, full) {
    const sm = r.summary || {};
    const wrapEl = h('div', { id: full ? 'recon-panel' : null });
    if (full) {
      const tiles = h('div', { class: 'recon-summary' });
      [['fail', 'Failing'], ['pass', 'Passing'], ['info', 'Known differences'], ['not_run', 'Not run']].forEach(([k, label]) => {
        tiles.appendChild(h('div', { class: 'rs ' + k }, badge(k, label), h('span', { class: 'n' }, String(sm[k] || 0))));
      });
      wrapEl.appendChild(tiles);
    }
    const tb = h('tbody');
    (r.rules || []).filter((rule) => full || !ids || ids.includes(rule.id)).forEach((rule) => {
      const c = { pass: 0, fail: 0, info: 0, not_run: 0 };
      (rule.results || []).forEach((x) => { c[x.status] = (c[x.status] || 0) + 1; });
      const worst = c.fail ? 'fail' : c.not_run && !c.pass && !c.info ? 'not_run' : c.info && !c.pass ? 'info' : 'pass';
      tb.appendChild(h('tr', { class: c.fail ? 'row-fail' : null },
        h('th', { scope: 'row' }, rule.id),
        h('td', null, h('a', { href: 'reconciliation.html#' + rule.id }, rule.title)),
        h('td', null, badge(worst, worst === 'fail' ? c.fail + ' of ' + rule.results.length + ' fail' : null))));
    });
    wrapEl.appendChild(h('div', { class: 'table-wrap' }, h('table', null,
      h('caption', null, 'Cross-checks run on every build. Failures are published, not hidden.'),
      h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Rule'), h('th', { scope: 'col' }, 'What is compared'), h('th', { scope: 'col' }, 'Result'))), tb)));
    return wrapEl;
  }
  async function loadSourceDetails(figures, host) {
    state(host, 'Loading the file details…');
    const ids = [...new Set(figures.map((f) => f.point && f.point.provenance_id).filter(Boolean))];
    const recs = [];
    const files = {};
    await Promise.all([...new Set(ids.map((i) => (PROV_RE.exec(i) || [])[1]).filter(Boolean))].map(async (src) => {
      try { files[src] = await getJSON('provenance/' + src + '.json'); } catch (e) { files[src] = null; }
    }));
    ids.forEach((id) => {
      const m = PROV_RE.exec(id); const f = m && files[m[1]];
      if (f && f.records && f.records[id]) recs.push(f.records[id]);
    });
    clear(host);
    if (!recs.length) { host.appendChild(gapBox('We could not load the file details just now.')); return; }
    const groups = new Map();
    recs.forEach((rec) => {
      const c = rec.check || {};
      const key = [rec.publisher, rec.dataset, rec.vintage || rec.edition, c.download_url || rec.source_url, c.sheet || rec.sheet].join('|');
      if (!groups.has(key)) groups.set(key, { rec, cells: [] });
      groups.get(key).cells.push(c.cell || rec.cell_or_range);
    });
    groups.forEach(({ rec, cells }) => {
      const c = rec.check || {};
      const dl = h('dl', { class: 'kv' });
      const kv = (k, v) => { if (v != null && v !== '') append(dl, [h('dt', null, k), h('dd', null, v)]); };
      kv('Publisher', rec.publisher);
      kv('Dataset', rec.dataset);
      kv('Edition', rec.vintage || rec.edition);
      kv('Published', rec.publication_date);
      kv('File', c.kind === 'api' ? ext(c.query_url, 'API request') : ext(c.download_url || rec.source_url, 'Download the file'));
      kv('Sheet', c.sheet || rec.sheet);
      kv('Cells', [...new Set(cells)].filter(Boolean).slice(0, 12).join(', ') + (new Set(cells).size > 12 ? ' and more' : ''));
      kv('SHA-256', c.sha256 || rec.file_sha256 ? h('code', null, c.sha256 || rec.file_sha256) : null);
      kv('Fetched', rec.retrieved_at ? rec.retrieved_at + ' (' + (rec.retrieval || '?') + ')' : null);
      host.appendChild(h('div', { class: 'card' }, dl));
    });
  }
  /* spec: {figures:[{label, point}], recon: 'all' | [rule ids], method: [string|Node], intro} */
  function checkers(spec) {
    spec = spec || {};
    const det = h('details', { class: 'checkers', id: 'for-checkers' });
    det.appendChild(h('summary', null, h('span', { class: 'checkers-h' }, 'For checkers'),
      h('span', { class: 'small muted' }, 'Sources, exact cells and how the numbers fit together')));
    const body = h('div', { class: 'checkers-body' });
    if (spec.intro) body.appendChild(h('p', { class: 'small' }, spec.intro));
    const figures = (spec.figures || []).filter((f) => f && f.point);
    if (figures.length) {
      body.appendChild(h('h3', null, 'Check these numbers'));
      body.appendChild(h('ul', { class: 'check-list' }, figures.map((f) => {
        const ch = checkHref(f.point.provenance_id);
        return h('li', null, f.label + ': ', h('strong', null, f.text || fmt(f.point.value, f.point.unit)), ' ',
          f.point.status === 'forecast' ? badge('forecast') : null, ' ', ch ? h('a', { href: ch }, 'Check this number') : null);
      })));
      body.appendChild(h('h3', null, 'Where they come from'));
      const srcHost = h('div', { class: 'src-host' });
      const heavy = figures.some((f) => /^dwp_benefits\./.test(f.point.provenance_id || ''));
      body.appendChild(h('p', { class: 'small muted' }, 'Publisher, file, sheet, cell and SHA-256 for each source.' + (heavy ? ' The benefits file is large (about 10 MB), so it loads only when you ask.' : '')));
      const btn = h('button', { type: 'button', class: 'btn', onclick: () => { btn.remove(); loadSourceDetails(figures, srcHost); } }, 'Show the file details');
      body.appendChild(btn);
      body.appendChild(srcHost);
    }
    let reconHost = null;
    if (spec.recon) {
      body.appendChild(h('h3', null, 'Do the sources agree?'));
      reconHost = h('div', null, h('p', { class: 'state', role: 'status' }, 'Loading the cross-checks…'));
      body.appendChild(reconHost);
    }
    if (spec.method && spec.method.length) {
      body.appendChild(h('h3', null, 'Definitions and method'));
      body.appendChild(h('ul', { class: 'method-list' }, spec.method.map((m) => h('li', null, m))));
    }
    det.appendChild(body);
    let done = false;
    det.addEventListener('toggle', async () => {
      if (!det.open || done || !reconHost) return;
      done = true;
      try {
        const r = await getJSON('reconciliation.json');
        clear(reconHost).appendChild(reconPanel(r, spec.recon === 'all' ? null : spec.recon, spec.recon === 'all'));
      } catch (e) { state(reconHost, 'Could not load the cross-checks: ' + e.message, 'error'); }
    });
    return det;
  }
  function mountCheckers(spec) {
    const host = $('#checkers');
    if (!host) return null;
    const det = checkers(spec);
    clear(host).appendChild(det);
    openCheckersFromHash();
    return det;
  }
  function openCheckersFromHash() {
    if (location.hash === '#for-checkers') {
      const d = $('details.checkers');
      if (d) { d.open = true; d.scrollIntoView(); }
    }
  }

  /* ---------- chrome: nav, basis toggle, reconciliation strip, build banner, footer ---------- */
  const NAV_MAIN = [['index.html', 'Home'], ['spending.html', 'Where your money goes'], ['revenue.html', 'Where the money comes from'],
    ['benefits.html', 'Benefits explained'], ['who-pays.html', 'Who pays tax'], ['claims.html', 'Check a number']];
  const NAV_SEC = [['glossary.html', 'Words explained'], ['reconciliation.html', 'Why totals differ'], ['methodology.html', 'How we work it out'],
    ['corrections.html', 'Corrections'], ['about.html', 'About us']];
  function navList(items, cls, current) {
    return h('ul', { class: cls || null }, items.map(([href, label]) =>
      h('li', null, h('a', { href, 'aria-current': current === href ? 'page' : null }, label))));
  }
  function mountNav() {
    let cur = location.pathname.split('/').pop() || 'index.html';
    if (/^benefit(-|\.html)/.test(cur)) cur = 'benefits.html';
    const nav = $('nav.nav');
    if (nav) {
      /* On phones the links fold behind a Menu button so the page heading is near the top. */
      const lists = h('div', { class: 'nav-lists', id: 'nav-lists' }, navList(NAV_MAIN, null, cur), navList(NAV_SEC, 'secondary', cur));
      const btn = h('button', { type: 'button', class: 'nav-toggle', 'aria-expanded': 'false', 'aria-controls': 'nav-lists' },
        h('span', { class: 'nav-toggle-icon', 'aria-hidden': 'true' }), 'Menu');
      btn.addEventListener('click', () => {
        const open = btn.getAttribute('aria-expanded') !== 'true';
        btn.setAttribute('aria-expanded', String(open));
        nav.classList.toggle('open', open);
      });
      nav.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && nav.classList.contains('open')) { btn.setAttribute('aria-expanded', 'false'); nav.classList.remove('open'); btn.focus(); }
      });
      clear(nav).append(btn, lists);
    }
    const foot = $('.site-foot .foot-inner ul');
    if (foot) clear(foot).append(...[...NAV_MAIN, ...NAV_SEC].map(([href, label]) => h('li', null, h('a', { href }, label))));
  }
  function mountBasis() {
    const host = $('#basis-host');
    if (!host) return;
    const fs = h('fieldset', { class: 'basis' }, h('legend', null, 'Show amounts:'));
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
  /* A calm, honest line: how many cross-checks agree and how many we have not explained yet. No alarm colours:
     a difference between two official totals is usually a definition, and the page explains each one. */
  async function mountReconStrip() {
    const host = $('#recon-host');
    if (!host) return;
    try {
      const r = await getJSON('reconciliation.json');
      const sm = r.summary || {};
      const agree = (sm.pass || 0) + (sm.info || 0);
      const open = sm.fail || 0;
      clear(host);
      host.appendChild(h('a', { href: 'reconciliation.html', class: 'recon-link' },
        h('span', { class: 'recon-dot', 'aria-hidden': 'true' }),
        'Cross-checks: ', h('span', { class: 'long' }, agree + ' agree or are explained'), h('span', { class: 'short' }, agree + ' agree'),
        open ? [', ', h('span', { class: 'long' }, open + ' not explained yet'), h('span', { class: 'short' }, open + ' open')] : ', none open'));
    } catch (e) {
      host.textContent = 'Cross-checks unavailable just now.';
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
        if (offline) {
          const fixtures = (ix.sources || []).some((x) => (x.files || []).some((f) => f.retrieval === 'fixture'));
          msg.push(fixtures ? 'Test build: some years are missing.' : 'Built from saved copies of the source files.');
        }
        if (stale.length) msg.push('Some sources are from a saved copy (' + stale.map((x) => x.publisher + ' since ' + x.stale_since).join('; ') + ').');
        const b = h('div', { class: 'build-banner', role: 'note' }, h('div', null, msg.join(' '), ' ', h('a', { href: 'methodology.html' }, 'How we build this')));
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
    mountNav();
    mountBasis();
    mountReconStrip();
    mountFooter();
    watchTerms();
    window.addEventListener('beforeprint', () => document.querySelectorAll('details.checkers').forEach((d) => { d.open = true; }));
    window.addEventListener('hashchange', openCheckersFromHash);
    const main = $('#main');
    if (pageFn) {
      try { await pageFn({ main }); } catch (e) {
        console.error(e);
        const host = $('[data-page-root]') || main;
        host.appendChild(h('p', { class: 'state error', role: 'alert' }, 'Something went wrong loading the data: ' + e.message));
      }
    }
    openCheckersFromHash();
    enhanceTerms();
  }
  // Deferred scripts run while readyState is 'interactive', before the page script registers; wait for DOMContentLoaded.
  if (document.readyState === 'complete') setTimeout(boot, 0); else document.addEventListener('DOMContentLoaded', boot);

  window.UKPM = {
    h, s, ext, clear, $, append, safeHref, getJSON, index, series, seriesMany, prov, checkHref, pointFor, gapFor, latestOutturn,
    get basis() { return basis; }, setBasis, onBasis, variantFor, fmt, fmtShort, unitNote, axisTitle, basisCaption, basisShort, updatedText,
    moneyWords, perPersonText, per100Text, per100Int, peopleText, largestRemainder, perHousehold, perHead, perHouseholdNote, perPersonNote, areaName, AREA_BLURB, cap1,
    badge, num, derivedNum, shareSpec, openPop, closePop, renderProvSummary, state, note, gapBox, yearSelect, selectField, gapsNote, gapRanges,
    barList, splitOf100, tableView, seriesTable, columnChart, lineChart, squares, partitionGrid, peopleGrid, stackStrip, ruler, welfareRuler, benefitView, benefitSlim, scopeChip, setSummary, summaryState, metaLine,
    term, enhanceTerms, checkers, mountCheckers, reconPanel, page, PROV_RE, SERIES_RE,
  };
})();
