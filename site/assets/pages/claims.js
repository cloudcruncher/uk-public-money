/* Claim checker: curated claims (claims.json) plus a lookup of any official number with its provenance. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const [ix, cj] = await Promise.all([U.index(), U.getJSON('claims.json')]);

  /* --- curated claims --- */
  const ch = $('#claims');
  U.clear(ch);
  const claims = cj.claims || [];
  const VERDICT = {
    consistent: ['pass', 'Consistent with the official figure'], differs: ['fail', 'Differs from the official figure'],
    not_comparable: ['not_run', 'Not comparable (different definition)'], no_official_figure: ['not_run', 'No official figure'],
  };
  if (!claims.length) {
    ch.appendChild(h('div', { class: 'empty' },
      h('p', null, h('strong', null, 'No claims have been checked yet.')),
      h('p', null, 'Claims are added only with a link to where they were said. We never invent example quotes. Until then, use the lookup below to find the official figure for any series.')));
  } else {
    const list = h('div', { class: 'grid' });
    claims.forEach((c) => {
      const v = VERDICT[c.verdict] || ['not_run', c.verdict || 'Unknown'];
      const off = c.official || null;
      list.appendChild(h('article', { class: 'card' },
        h('p', null, U.badge(v[0], v[1])),
        h('blockquote', null, h('p', null, '“' + (c.text || '') + '”')),
        h('p', { class: 'small muted' }, c.said_by ? c.said_by + ', ' : '', c.said_date || '', ' · ', U.ext(c.said_url, 'where it was said')),
        c.claimed ? h('p', null, 'Claimed: ', h('strong', null, String(c.claimed.value) + ' ' + (c.claimed.unit || '')), ' for ', c.claimed.fiscal_year || '?', ' (', c.claimed.price_basis || 'basis not stated', ')') : null,
        off ? h('p', null, 'Official: ', U.num(off, { label: 'Official figure for this claim' }), off.vintage ? h('span', { class: 'small muted' }, ' ' + off.vintage) : null) : null,
        c.delta_pct != null ? h('p', { class: 'small' }, 'Difference: ' + Number(c.delta_pct).toFixed(1) + '%') : null));
    });
    ch.appendChild(list);
  }

  /* --- lookup --- */
  const all = ix.series.slice().sort((a, b) => a.title.localeCompare(b.title));
  const q = $('#q'); const res = $('#results'); const out = $('#lookup'); const count = $('#count');
  let selected = null; let year = null;

  function readHash() {
    const p = new URLSearchParams(location.hash.replace(/^#/, ''));
    const sid = p.get('s');
    if (sid && U.SERIES_RE.test(sid) && all.some((x) => x.id === sid)) { selected = sid; year = p.get('y'); }
  }
  function writeHash() {
    if (!selected) return;
    const p = new URLSearchParams(); p.set('s', selected); if (year) p.set('y', year);
    history.replaceState(null, '', '#' + p.toString());
  }
  function matches(term) {
    const words = term.toLowerCase().split(/\s+/).filter(Boolean);
    if (!words.length) return all.filter((x) => x.headline);
    return all.filter((x) => { const hay = (x.title + ' ' + x.id + ' ' + (x.geography || '')).toLowerCase(); return words.every((w) => hay.includes(w)); });
  }
  function renderResults() {
    const found = matches(q.value);
    U.clear(res);
    count.textContent = q.value.trim() ? found.length + ' matching series' : 'Headline series (type to search all ' + all.length + ')';
    found.slice(0, 60).forEach((x) => {
      res.appendChild(h('li', null, h('button', {
        type: 'button', 'aria-pressed': String(x.id === selected),
        onclick: () => { selected = x.id; year = null; renderResults(); renderLookup(true); },
      }, x.title, h('span', { class: 'sid' }, x.id + ' · ' + (x.geography || '') + ' · ' + (x.years || []).join(' to ')))));
    });
    if (found.length > 60) res.appendChild(h('li', { class: 'small muted' }, h('span', { class: 'state' }, 'Showing 60 of ' + found.length + '. Narrow the search.')));
    if (!found.length) res.appendChild(h('li', null, h('p', { class: 'state' }, 'No series match. Try “health”, “VAT” or “welfare”.')));
  }
  q.addEventListener('input', renderResults);

  async function renderLookup(focus) {
    if (!selected) { U.clear(out).appendChild(h('p', { class: 'muted' }, 'Pick a series to see its official figure.')); return; }
    U.state(out, 'Loading…');
    let ser;
    try { ser = await U.series(selected); } catch (e) { U.state(out, 'Could not load the series: ' + e.message, 'error'); return; }
    const vf = U.variantFor(ser);
    const yrs = vf.points.map((p) => p.fiscal_year);
    if (!year || !yrs.includes(year)) {
      const lo = ix.fiscal_years && ix.fiscal_years.latest_outturn;
      const outt = vf.points.filter((p) => p.status !== 'forecast').map((p) => p.fiscal_year);
      year = yrs.includes(lo) ? lo : (outt[outt.length - 1] || yrs[yrs.length - 1]);
    }
    writeHash();
    U.clear(out);
    const title = h('h3', { tabindex: '-1' }, ser.title);
    out.appendChild(title);
    if (ser.description) out.appendChild(h('p', { class: 'small muted' }, ser.description));
    const tools = h('div', { class: 'toolbar' }, U.yearSelect('Year', yrs, year, (y) => { year = y; renderLookup(false); }));
    out.appendChild(tools);
    if (vf.fallback) out.appendChild(U.note('warn', vf.fallback));
    const pt = U.pointFor(ser, vf.variant, year);
    if (!pt) { out.appendChild(h('p', { class: 'state' }, 'No figure for ' + year + '.')); return; }
    out.appendChild(h('div', { class: 'hero-num' }, U.num(pt, { label: ser.title + ' ' + year })));
    out.appendChild(h('p', { class: 'small muted' }, year, ' · ', U.basisCaption(vf.variant, ix), ' · ', U.badge(pt.status), ' · ', pt.vintage, ' · geography: ', ser.geography || 'not stated'));
    (ser.notes || []).length && out.appendChild(h('ul', { class: 'notes-list' }, ser.notes.map((n) => h('li', null, n))));
    const provBox = h('div', { class: 'card' }, h('p', { class: 'state', role: 'status' }, 'Loading the source record…'));
    out.appendChild(h('h3', null, 'Where it comes from'));
    out.appendChild(provBox);
    if (focus) title.focus();
    try {
      const rec = await U.prov(pt.provenance_id);
      U.clear(provBox);
      U.renderProvSummary(provBox, rec, { point: pt, label: ser.title + ' ' + year });
    } catch (e) { U.state(provBox, 'Could not load provenance: ' + e.message, 'error'); }
  }

  readHash();
  if (selected) { const t = all.find((x) => x.id === selected); if (t) q.value = ''; }
  renderResults();
  renderLookup(false);
  U.onBasis(() => renderLookup(false));
});
