/* Reconciliation: every rule and every result. Failures are listed first and never filtered out by default. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const r = await U.getJSON('reconciliation.json');
  const host = $('#recon');
  const sumHost = $('#summary');
  const sm = r.summary || {};
  U.clear(sumHost);
  const tiles = h('div', { class: 'recon-summary' });
  [['fail', 'Failing'], ['pass', 'Passing'], ['info', 'Known differences'], ['not_run', 'Not run']].forEach(([k, label]) => {
    tiles.appendChild(h('div', { class: 'rs ' + k }, U.badge(k, label), h('span', { class: 'n' }, String(sm[k] || 0))));
  });
  sumHost.appendChild(tiles);
  sumHost.appendChild(h('p', { class: 'small muted' }, 'Results generated ', r.generated_at || '?', '. A failing check does not stop the site being published: it is the honest output, shown here.'));

  let filter = 'all';
  const fHost = $('#filters');
  const FILTERS = [['all', 'All results'], ['fail', 'Failing'], ['info', 'Known differences'], ['not_run', 'Not run'], ['pass', 'Passing']];
  function renderFilters() {
    U.clear(fHost);
    FILTERS.forEach(([k, t]) => fHost.appendChild(h('button', { type: 'button', class: 'btn', 'aria-pressed': String(filter === k), onclick: () => { filter = k; renderFilters(); render(); } }, t)));
  }

  const ORDER = { fail: 0, not_run: 1, info: 2, pass: 3 };
  function side(x, label) {
    if (!x) return h('span', { class: 'muted' }, '–');
    const pt = { value: x.value, unit: x.unit, provenance_id: x.provenance_id, status: null };
    const name = h('span', { class: 'small muted' }, h('code', null, x.series_id || ''));
    if (x.provenance_id) return h('div', null, U.num(pt, { label }), h('br'), name);
    const ids = x.provenance_ids || [];
    return h('div', null, U.derivedNum(U.fmt(x.value, x.unit), {
      title: label, formula: 'Sum of ' + ids.length + ' published values', inputs: ids.map((id, i) => ({ label: 'Input ' + (i + 1), id })),
    }), h('br'), name);
  }
  function tolText(t) {
    if (!t) return '';
    const parts = [];
    if (t.abs != null) parts.push('absolute ' + t.abs);
    if (t.rel != null) parts.push('relative ' + (t.rel * 100).toFixed(2) + '%');
    return 'Tolerance: ' + (parts.join(', ') || 'none') + (t.unit ? ' (' + t.unit + ')' : '');
  }

  function render() {
    U.clear(host);
    const rules = (r.rules || []).slice().sort((a, b) => {
      const fa = (a.results || []).some((x) => x.status === 'fail') ? 0 : 1;
      const fb = (b.results || []).some((x) => x.status === 'fail') ? 0 : 1;
      return fa - fb || a.id.localeCompare(b.id, undefined, { numeric: true });
    });
    let shown = 0;
    rules.forEach((rule) => {
      const results = (rule.results || []).filter((x) => filter === 'all' || x.status === filter)
        .sort((a, b) => (ORDER[a.status] - ORDER[b.status]) || String(a.fiscal_year).localeCompare(String(b.fiscal_year)));
      if (!results.length) return;
      shown += results.length;
      const counts = {};
      (rule.results || []).forEach((x) => { counts[x.status] = (counts[x.status] || 0) + 1; });
      const sec = h('section', { class: 'rule', id: rule.id, 'aria-labelledby': rule.id + '-h' });
      sec.appendChild(h('h3', { id: rule.id + '-h' }, h('span', null, rule.id + ': ' + rule.title),
        Object.keys(ORDER).filter((k) => counts[k]).map((k) => U.badge(k, counts[k] + ' ' + ({ fail: 'fail', pass: 'pass', info: 'info', not_run: 'not run' })[k]))));
      if (rule.description) sec.appendChild(h('p', null, rule.description));
      sec.appendChild(h('p', { class: 'tol' }, tolText(rule.tolerance)));
      const tb = h('tbody');
      results.forEach((x) => {
        tb.appendChild(h('tr', { class: x.status === 'fail' ? 'row-fail' : null },
          h('td', null, U.badge(x.status)),
          h('th', { scope: 'row' }, x.fiscal_year || '–', x.edition ? h('div', { class: 'small muted' }, x.edition) : null),
          h('td', null, side(x.left, rule.id + ' ' + (x.fiscal_year || '') + ' left side')),
          h('td', null, side(x.right, rule.id + ' ' + (x.fiscal_year || '') + ' right side')),
          h('td', { class: 'r' }, x.delta == null ? '–' : U.fmt(x.delta, (x.left && x.left.unit) || 'GBP_bn'), x.delta_pct == null ? null : h('div', { class: 'small muted' }, x.delta_pct.toFixed(2) + '%')),
          h('td', { class: 'small' }, x.reason || '')));
      });
      sec.appendChild(h('div', { class: 'table-wrap' }, h('table', null,
        h('caption', null, rule.id + ' results' + (filter !== 'all' ? ' (filtered: ' + filter + ')' : '')),
        h('thead', null, h('tr', null, ['Result', 'Year', 'Left', 'Right', 'Difference', 'Why'].map((t, i) => h('th', { scope: 'col', class: i === 4 ? 'r' : null }, t)))),
        tb)));
      host.appendChild(sec);
    });
    if (!shown) host.appendChild(h('div', { class: 'empty' }, 'No results with this status.'));
  }
  renderFilters();
  render();
  if (location.hash) { const t = document.getElementById(location.hash.slice(1)); if (t) t.scrollIntoView(); }
});
