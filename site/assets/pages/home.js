/* Home: three headline numbers and the reconciliation panel. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const ix = await U.index();
  const latest = ix.fiscal_years && ix.fiscal_years.latest_outturn;
  const TILES = [
    { id: 'obr.psf.tme', label: 'Total public spending (TME)', href: 'spending.html', more: 'Where £1 goes' },
    { id: 'obr.psf.receipts', label: 'Public sector current receipts', href: 'revenue.html', more: 'Where £1 comes from' },
    { id: 'dwp_benefits.total_uk_welfare', label: 'UK welfare spending (DWP tables)', href: 'benefits.html', more: 'Benefits, and why totals differ' },
  ];
  const data = await U.seriesMany(TILES.map((t) => t.id));
  const host = $('#tiles');

  function render() {
    U.clear(host);
    const cap = $('#tiles-caption');
    if (cap) cap.textContent = U.basisCaption(U.basis, ix);
    TILES.forEach((t) => {
      const ser = data[t.id];
      const card = h('div', { class: 'card tile' });
      card.appendChild(h('p', { class: 'label' }, t.label));
      if (!ser) {
        card.appendChild(h('p', { class: 'state error' }, 'Series not available in this build.'));
      } else {
        const vf = U.variantFor(ser);
        const outturn = vf.points.filter((p) => p.status !== 'forecast');
        const pt = vf.points.find((p) => p.fiscal_year === latest) || outturn[outturn.length - 1] || vf.points[vf.points.length - 1];
        card.appendChild(h('div', { class: 'hero-num' }, U.num(pt, { label: t.label + ' ' + (pt ? pt.fiscal_year : ''), check: false, badge: false })));
        if (pt) {
          card.appendChild(h('p', { class: 'meta' }, pt.fiscal_year, ' · ', U.unitNote(pt.unit) || 'cash', ' · ', U.badge(pt.status), ' · ', pt.vintage));
          const ch = U.checkHref(pt.provenance_id);
          if (ch) card.appendChild(h('p', { class: 'small' }, h('a', { href: ch }, 'Check this number')));
        }
        if (vf.fallback) card.appendChild(h('p', { class: 'small muted' }, vf.fallback));
      }
      card.appendChild(h('p', { class: 'small' }, h('a', { href: t.href }, t.more + ' →')));
      host.appendChild(card);
    });
  }
  render();
  U.onBasis(render);

  // Reconciliation panel: every rule, failures listed first and in full.
  const rh = $('#recon-panel');
  try {
    const r = await U.getJSON('reconciliation.json');
    U.clear(rh);
    const sm = r.summary || {};
    const tiles = h('div', { class: 'recon-summary' });
    [['fail', 'Failing'], ['pass', 'Passing'], ['info', 'Known differences'], ['not_run', 'Not run']].forEach(([k, label]) => {
      tiles.appendChild(h('div', { class: 'rs ' + k }, U.badge(k, label), h('span', { class: 'n' }, String(sm[k] || 0))));
    });
    rh.appendChild(tiles);
    const tb = h('tbody');
    (r.rules || []).forEach((rule) => {
      const c = { pass: 0, fail: 0, info: 0, not_run: 0 };
      (rule.results || []).forEach((x) => { c[x.status] = (c[x.status] || 0) + 1; });
      const worst = c.fail ? 'fail' : c.not_run && !c.pass && !c.info ? 'not_run' : c.info && !c.pass ? 'info' : 'pass';
      tb.appendChild(h('tr', { class: c.fail ? 'row-fail' : null },
        h('th', { scope: 'row' }, rule.id),
        h('td', null, h('a', { href: 'reconciliation.html#' + rule.id }, rule.title)),
        h('td', null, U.badge(worst, worst === 'fail' ? c.fail + ' of ' + rule.results.length + ' fail' : null)),
      ));
    });
    rh.appendChild(h('div', { class: 'table-wrap' }, h('table', null,
      h('caption', null, 'Every cross-check the build ran. Failures are published, not hidden.'),
      h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Rule'), h('th', { scope: 'col' }, 'What is compared'), h('th', { scope: 'col' }, 'Result'))), tb)));
  } catch (e) {
    U.state(rh, 'Could not load reconciliation results: ' + e.message, 'error');
  }
});
