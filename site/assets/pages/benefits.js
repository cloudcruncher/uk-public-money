/* Benefits explained: what each DWP benefit costs (Great Britain), ranked, following the price basis.
   The same figures as each benefit's own page (both use UKPM.benefitView). */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const [ix, bx] = await Promise.all([U.index(), U.getJSON('benefits/index.json')]);
  const entries = (bx.benefits || []).filter((b) => b.headline && b.headline.spend);
  const host = $('#list');
  if (!entries.length) {
    U.clear(host).appendChild(U.gapBox('We don’t show the benefits yet: the official figures aren’t published in a form we can trace.'));
    U.summaryState('We don’t show benefit costs yet: the official figures aren’t published in a form we can trace.');
    return;
  }
  const year = entries[0].headline.fiscal_year;
  const docs = entries.map(U.benefitSlim);
  let total = null;
  try { total = await U.series(bx.total_series_id); } catch (e) { total = null; }
  const href = (d) => 'benefit.html?b=' + encodeURIComponent(d.slug);

  function render() {
    const views = docs.map((d) => ({ d, v: U.benefitView(d, year) })).filter((x) => x.v.spend).sort((a, b) => b.v.spend.value - a.v.spend.value);
    if (!views.length) { U.state(host, 'We don’t show benefit costs for ' + year + ' yet.'); return; }
    const mode = views[0].v.mode;
    const totalPoint = total && (U.pointFor(total, mode, year) || U.pointFor(total, 'nominal', year));
    const top = views[0];
    const status = views.some((x) => x.v.spend.status === 'forecast') ? 'mixed' : 'actual';

    /* summary */
    const sentence = [];
    if (totalPoint) {
      sentence.push('In ' + year + ', benefits in Great Britain cost about ', U.num(totalPoint, { label: 'All DWP benefit spending, ' + year, badge: false }),
        '. The biggest was ' + top.d.name + ', at about ', U.num(top.v.spend, { label: top.d.name + ' cost, ' + year, badge: false }), '.');
    } else {
      sentence.push('In ' + year + ', ' + top.d.name + ' was the biggest benefit, at about ', U.num(top.v.spend, { label: top.d.name + ' cost, ' + year, badge: false }), '.');
    }
    U.setSummary(sentence, (status === 'actual' ? 'Actual figures' : 'Actual and forecast figures') + ' · ' + top.v.basisWords + ' · last updated ' + U.updatedText(ix), totalPoint || top.v.spend);

    U.clear(host);
    if (top.v.pctNote) host.appendChild(U.note('warn', top.v.pctNote));
    /* ranked bars: the cost of each benefit, with how many people get it */
    const rows = views.map((x, k) => ({
      label: x.d.name, href: href(x.d), barValue: x.v.spend.value, forecast: x.v.spend.status === 'forecast',
      sub: [x.v.claimants ? U.peopleText(x.v.claimants.value * (x.v.claimants.unit === 'thousand_cases' ? 1000 : 1)) + (x.d.in_payment ? ' people' : ' claims') : null,
        k === 0 && x.v.share ? 'about ' + U.per100Text(x.v.share.value) + ' of every £100 of benefit spending' : null].filter(Boolean).join(' · ') || null,
      /* a fresh node: v.spendNode is appended to the detail card below, and a DOM node can only live in one place */
      valueNode: U.num(x.v.spend, { label: x.d.name + ' cost, ' + year, badge: false }),
    }));
    const left = h('div', null, U.scopeChip(year, 'Great Britain', status),
      U.barList(rows, { unitHead: 'Total cost in ' + year + ', ' + top.v.basisWords }));
    const right = h('div');
    if (top.v.share) {
      const n = Math.round(top.v.share.value);
      right.appendChild(U.squares({ on: n, bracket: '£' + n, title: top.d.name + ': about £' + n + ' of every £100 of benefit spending',
        caption: top.d.name + ': £' + n + ' of every £100 spent on benefits', keyOn: top.d.name, keyOff: 'All other benefits',
        source: 'Source: Department for Work and Pensions, ' + (top.d.edition || '') + '.' }));
    }
    host.appendChild(h('div', { class: 'side' }, left, right));

    /* every benefit's details, folded away */
    const grid = h('div', { class: 'grid grid-2' });
    views.forEach(({ d, v }) => {
      const card = h('article', { class: 'card', 'aria-labelledby': 'b-' + d.slug });
      card.appendChild(h('h3', { id: 'b-' + d.slug }, h('a', { href: href(d) }, d.name)));
      const kv = h('dl', { class: 'kv' });
      const row = (label, node) => { kv.appendChild(h('dt', null, label)); kv.appendChild(h('dd', null, node)); };
      row('Total cost', v.spendNode);
      row('People getting it', v.claimants ? U.num(v.claimants, { label: 'People getting ' + d.name + ', ' + year, badge: false }) : U.num(null));
      row('Cost for each person getting it', v.perClaimant.point ? h('span', null, v.perClaimant.node, ' a year') : U.num(null));
      row('Out of every £100 of benefit spending', v.share ? U.num(v.share, { text: U.per100Text(v.share.value), label: d.name + ' share of benefit spending, ' + year, badge: false }) : U.num(null));
      card.appendChild(kv);
      card.appendChild(h('p', { class: 'small' }, h('a', { class: 'go', href: href(d) }, 'What is ' + d.name + '? →')));
      grid.appendChild(card);
    });
    host.appendChild(h('details', { class: 'more-detail' }, h('summary', null, 'Show details for every benefit'), h('p', { class: 'small muted' }, 'All amounts ' + top.v.basisWords + ', ' + year + '.'), grid));
    host.appendChild(U.tableView('Benefits in Great Britain, ' + year + ', ' + top.v.basisWords,
      ['Benefit', 'Total cost', 'People getting it', 'Cost for each person (a year)', 'Out of every £100 of benefit spending'],
      views.map(({ d, v }) => [h('a', { href: href(d) }, d.name), U.num(v.spend, { label: d.name + ' cost', badge: false }),
        v.claimants ? U.num(v.claimants, { label: d.name + ' people', badge: false }) : 'Not published yet',
        v.perClaimant.point ? U.benefitView(d, year).perClaimant.node : 'Not published yet',
        v.share ? U.num(v.share, { text: U.per100Text(v.share.value), label: d.name + ' share', badge: false }) : 'Not published yet'])));
  }
  render();
  U.onBasis(render);

  const gaps = bx.gaps || [];
  if (gaps.length) {
    $('#gaps').appendChild(h('details', { class: 'gaps-note small' },
      h('summary', null, 'Not shown: ' + gaps.map((g) => g.name).join(', ') + '. Why?'),
      h('ul', { class: 'notes-list' }, gaps.map((g) => h('li', null, g.name + ': ' + g.reason)))));
  }

  /* why welfare has more than one total */
  const tHost = $('#totals-host');
  async function renderTotals() { const node = await U.welfareRuler(year); U.clear(tHost).appendChild(node); }
  await renderTotals();
  U.onBasis(renderTotals);

  const topD = docs.slice().sort((a, b) => (((b.spend || []).find((p) => p.fiscal_year === year) || {}).value || 0) - (((a.spend || []).find((p) => p.fiscal_year === year) || {}).value || 0)).slice(0, 3);
  const at = (arr) => (arr || []).find((p) => p.fiscal_year === year) || null;
  U.mountCheckers({
    figures: topD.flatMap((d) => [
      { label: d.name + ' cost, ' + year, point: at(d.spend) },
      { label: d.name + ' cost per claimant, ' + year, point: at(d.cost_per_claimant) },
    ]).concat(total && U.pointFor(total, 'nominal', year) ? [{ label: 'All DWP benefit spending, ' + year, point: U.pointFor(total, 'nominal', year) }] : []),
    recon: ['R7', 'R8', 'R9'],
    method: [
      'Spending is from DWP Benefit expenditure and caseload tables, Table 1a. It covers Great Britain.',
      'The number of people getting a benefit (the caseload) is from Table 1c. It is a yearly average, rounded to the nearest 1,000.',
      'Cost per claimant is the spending divided by the caseload, for the same year and the same release. DWP publishes it as spent at the time; adjusted for rising prices, we scale it by the benefit’s own real ÷ cash ratio.',
      'Share of benefit spending is the benefit’s cost divided by the Table 1a total, shown out of every £100.',
      'The three welfare totals are DWP total benefit expenditure (Great Britain), the UK welfare total in the DWP tables, and social protection in HM Treasury’s PESA. All are for ' + year + '.',
    ],
  });
});
