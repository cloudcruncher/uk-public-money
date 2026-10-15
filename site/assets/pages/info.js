/* About, Methodology and Corrections: small data-driven parts of mostly static pages. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const ix = await U.index();

  const fill = (sel, text) => { const n = $(sel); if (n) n.textContent = text; };
  fill('[data-fill="real_base_year"]', ix.real_base_year || 'not published');
  fill('[data-fill="deflator_vintage"]', (ix.deflator && ix.deflator.vintage) || 'not published');
  fill('[data-fill="latest_outturn"]', (ix.fiscal_years && ix.fiscal_years.latest_outturn) || '?');
  fill('[data-fill="from_year"]', (ix.fiscal_years && ix.fiscal_years.from) || '?');

  const srcHost = $('#sources');
  if (srcHost) {
    U.clear(srcHost);
    const tb = h('tbody');
    (ix.sources || []).forEach((x) => {
      const files = (x.files || []).map((f) => f.edition + ' (' + f.publication_date + ', ' + f.retrieval + ')').join('; ');
      tb.appendChild(h('tr', null,
        h('th', { scope: 'row' }, x.publisher || x.id, h('div', { class: 'small muted' }, x.dataset || '')),
        h('td', null, x.enabled ? U.badge('pass', 'In use') : U.badge('not_run', 'Not used')),
        h('td', null, x.verdict || ''),
        h('td', null, x.licence || ''),
        h('td', { class: 'small' }, files || (x.notes || (x.deferred && x.deferred.reason) || '')),
        h('td', { class: 'small' }, x.stale_since ? 'Cached copy since ' + x.stale_since : (x.enabled ? 'Current' : ''))));
    });
    srcHost.appendChild(h('div', { class: 'table-wrap' }, h('table', null, h('caption', null, 'Every source in the register, including the ones not used yet.'),
      h('thead', null, h('tr', null, ['Source', 'Status', 'Verdict', 'Licence', 'Editions used / notes', 'Freshness'].map((t) => h('th', { scope: 'col' }, t)))), tb)));
  }

  const corrHost = $('#corrections');
  if (corrHost) {
    let cj;
    try { cj = await U.getJSON('corrections.json'); } catch (e) { U.state(corrHost, 'Could not load the corrections log: ' + e.message, 'error'); return; }
    const list = (cj.corrections || []).slice().sort((a, b) => String(b.date).localeCompare(String(a.date)));
    U.clear(corrHost);
    if (!list.length) {
      corrHost.appendChild(h('div', { class: 'empty' }, h('p', null, h('strong', null, 'No corrections so far.')),
        h('p', null, 'When we publish a wrong number, the fix is logged here with the old and new value. Entries are never removed.')));
      return;
    }
    const tb = h('tbody');
    list.forEach((c) => {
      tb.appendChild(h('tr', null,
        h('th', { scope: 'row' }, c.date || ''),
        h('td', null, h('code', null, c.series_id || ''), h('div', { class: 'small muted' }, c.fiscal_year || '')),
        h('td', null, c.what_was_wrong || ''),
        h('td', null, c.what_changed || ''),
        h('td', { class: 'r' }, c.old_value == null ? '' : String(c.old_value)),
        h('td', { class: 'r' }, c.new_value == null ? '' : String(c.new_value), U.checkHref(c.provenance_id) ? h('div', null, h('a', { href: U.checkHref(c.provenance_id) }, 'Check this number')) : null)));
    });
    corrHost.appendChild(h('div', { class: 'table-wrap' }, h('table', null, h('caption', null, 'Newest first.'),
      h('thead', null, h('tr', null, ['Date', 'Series', 'What was wrong', 'What changed', 'Old', 'New'].map((t, i) => h('th', { scope: 'col', class: i >= 4 ? 'r' : null }, t)))), tb)));
  }
});
