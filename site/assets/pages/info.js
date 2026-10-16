/* About, Methodology and Corrections: small data-driven parts of mostly static pages. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const ix = await U.index();

  const fill = (sel, text) => { const n = $(sel); if (n) n.textContent = text; };
  fill('[data-fill="real_base_year"]', ix.real_base_year || 'not published');
  fill('[data-fill="deflator_vintage"]', (ix.deflator && ix.deflator.vintage) || 'not published');
  fill('[data-fill="latest_outturn"]', (ix.fiscal_years && ix.fiscal_years.latest_outturn) || '?');
  fill('[data-fill="from_year"]', (ix.fiscal_years && ix.fiscal_years.from) || '?');

  let ruleRange = 'the rules';
  try {
    const ids = ((await U.getJSON('reconciliation.json')).rules || []).map((r) => r.id);
    if (ids.length) ruleRange = ids[0] + ' to ' + ids[ids.length - 1];
  } catch (e) { /* keep the generic wording */ }
  fill('[data-fill="rule_range"]', ruleRange);

  const here = location.pathname.split('/').pop();
  if (here === 'about.html') {
    U.setSummary(['This site shows where UK public money comes from and where it goes. It uses only official figures, and every number can be checked.'], 'Last updated ' + U.updatedText(ix));
    U.mountCheckers({ method: ['Every number has a record of the publisher, file, SHA-256 hash, sheet, cell and each step we applied.', 'Source data is under the Open Government Licence v3.0.'] });
  } else if (here === 'methodology.html') {
    U.setSummary(['We show each official number as published, then label whether it is actual or forecast, and whether prices are adjusted.'], 'Last updated ' + U.updatedText(ix));
    U.mountCheckers({ method: ['Real-terms figures use the OBR GDP deflator at market prices. Percent of GDP uses nominal GDP from the same OBR edition.', 'Cross-check rules (' + ruleRange + ') are listed on the reconciliation page.'] });
  } else if (here === 'corrections.html') {
    let n = null;
    try { n = ((await U.getJSON('corrections.json')).corrections || []).length; } catch (e) { n = null; }
    U.setSummary([n == null ? 'We could not load the corrections log just now.' : (n === 0 ? 'We have not had to correct a number so far.' : 'We have corrected ' + n + (n === 1 ? ' number' : ' numbers') + ' so far. Each fix says what was wrong.')], 'Last updated ' + U.updatedText(ix));
    U.mountCheckers({ method: ['Corrections are appended to api/v1/corrections.json. Entries are never removed.'] });
  }

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
