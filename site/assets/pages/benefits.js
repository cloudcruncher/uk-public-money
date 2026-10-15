/* Benefits: welfare definitions side by side, DWP spending by benefit, UK welfare over time. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const [ix, defs] = await Promise.all([U.index(), U.getJSON('definitions.json')]);
  const groups = defs.groups || [];
  const welfare = (groups.find((g) => g.id === 'welfare') || { definitions: [] }).definitions.slice();
  groups.forEach((g) => (g.definitions || []).forEach((d) => { if (d.id === 'cofog_social_protection') welfare.push(d); }));
  const lineIds = ix.series.filter((x) => /^dwp_benefits\.exp\.[a-z_]+$/.test(x.id) && !x.id.startsWith('dwp_benefits.exp.total')).map((x) => x.id);
  const TOTAL_1A = 'dwp_benefits.exp.total_benefit_expenditure';
  const UK_TOTAL = 'dwp_benefits.total_uk_welfare';
  const defSeries = welfare.map((d) => d.series_id).filter(Boolean);
  const data = await U.seriesMany([...new Set([...defSeries, ...lineIds, TOTAL_1A, UK_TOTAL])]);
  const caseloads = ix.series.filter((x) => x.source_id === 'dwp_benefits' && /persons/.test(x.unit));
  const yearSet = new Set();
  defSeries.forEach((id) => { const ser = data[id]; if (ser) (ser.variants.nominal || []).forEach((p) => yearSet.add(p.fiscal_year)); });
  const years = [...yearSet].sort();
  const latest = ix.fiscal_years && ix.fiscal_years.latest_outturn;
  let year = years.includes(latest) ? latest : years[years.length - 1];
  const humanTitle = (ser) => (ser.title || ser.id).replace(/^Benefit expenditure and caseload tables \(outturn and forecast\):\s*exp\s*\/\s*/, '').replace(/^./, (c) => c.toUpperCase());

  /* --- definitions side by side --- */
  const defHost = $('#defs');
  $('#defs-tools').appendChild(U.yearSelect('Year', years, year, (y) => { year = y; renderDefs(); renderLines(); }));
  function list(title, items) {
    if (!items || !items.length) return null;
    return [h('p', { class: 'inc-h' }, title), h('ul', null, items.map((x) => h('li', null, x)))];
  }
  function renderDefs() {
    U.clear(defHost);
    const firstUse = {};
    welfare.forEach((d) => { if (d.series_id && !firstUse[d.series_id]) firstUse[d.series_id] = d; });
    const grid = h('div', { class: 'defs' });
    welfare.forEach((d) => {
      const card = h('article', { class: 'card def', 'aria-labelledby': 'def-' + d.id });
      card.appendChild(h('h3', { id: 'def-' + d.id }, d.label));
      if (d.short) card.appendChild(h('p', { class: 'short' }, d.short));
      card.appendChild(h('p', null, U.badge('scope', 'Scope: ' + (d.scope || 'not stated'))));
      const ser = d.series_id ? data[d.series_id] : null;
      if (!d.series_id || d.status !== 'available') {
        card.appendChild(h('p', { class: 'state' }, 'No figure: ' + (d.status || 'not available') + '.'));
      } else if (!ser) {
        card.appendChild(h('p', { class: 'state error' }, 'Series ' + d.series_id + ' could not be loaded.'));
      } else {
        const vf = U.variantFor(ser);
        const pt = U.pointFor(ser, vf.variant, year);
        if (pt) {
          card.appendChild(h('div', { class: 'hero-num' }, U.num(pt, { label: d.label + ' ' + year })));
          card.appendChild(h('p', { class: 'small muted' }, year, ' · ', U.unitNote(pt.unit) || '', ' · ', pt.vintage));
        } else {
          const g = U.gapFor(ser, year);
          card.appendChild(h('p', { class: 'state' }, 'No figure for ' + year + (g ? ': ' + g.reason : '.')));
        }
        if (vf.fallback) card.appendChild(h('p', { class: 'small muted' }, vf.fallback));
        const owner = firstUse[d.series_id];
        if (owner && owner.id !== d.id) {
          card.appendChild(U.note('warn', h('strong', null, 'Same series as “' + owner.label + '”. '),
            'This build has no separate series for this definition yet, so the figure above is not a distinct ' + d.label + ' total.'));
        }
        card.appendChild(h('p', { class: 'small muted' }, 'Series: ', h('code', null, d.series_id)));
      }
      append(card, list('Includes', d.includes));
      append(card, list('Excludes', d.excludes));
      if (d.notes) card.appendChild(h('p', { class: 'small' }, d.notes));
      grid.appendChild(card);
    });
    defHost.appendChild(grid);
  }
  function append(n, kids) { if (kids) U.append(n, [kids]); }

  /* --- by benefit (Table 1a, GB) --- */
  const linesHost = $('#lines');
  function renderLines() {
    U.clear(linesHost);
    const totSer = data[TOTAL_1A];
    const totNom = totSer && U.pointFor(totSer, 'nominal', year);
    if (!totNom) { U.state(linesHost, 'No Table 1a total for ' + year + (totSer && U.gapFor(totSer, year) ? ': ' + U.gapFor(totSer, year).reason : '.')); return; }
    const totVf = U.variantFor(totSer);
    linesHost.appendChild(h('p', null, 'Total benefit expenditure, Great Britain, ', h('strong', null, year), ': ',
      U.num(U.pointFor(totSer, totVf.variant, year), { label: 'Total benefit expenditure GB ' + year })));
    if (totVf.fallback) linesHost.appendChild(U.note('warn', totVf.fallback));
    let sum = 0;
    const rows = lineIds.map((id) => data[id]).filter(Boolean).map((ser) => {
      const nom = U.pointFor(ser, 'nominal', year);
      const vf = U.variantFor(ser);
      if (nom) sum += nom.value;
      return { label: humanTitle(ser), fullLabel: humanTitle(ser) + ', GB, ' + year, point: U.pointFor(ser, vf.variant, year), barValue: nom ? nom.value : 0, forecast: nom && nom.status === 'forecast', sub: nom ? null : 'No figure for ' + year };
    }).sort((a, b) => b.barValue - a.barValue);
    const rest = totNom.value - sum;
    if (rest > 0.0005) {
      rows.push({
        label: 'Not in the lines above', sub: 'Total minus the lines in this build',
        barValue: rest,
        valueNode: U.derivedNum(U.fmt(rest, 'GBP_bn') + ' (cash)', {
          title: 'Spending not covered by the lines shown',
          formula: 'Total benefit expenditure − sum of the ' + lineIds.length + ' benefit lines, cash, ' + year,
          text: 'Reconciliation rule R7 flags this: the build’s benefit lines do not add up to the table total.',
          inputs: [{ label: 'Total benefit expenditure ' + year, id: totNom.provenance_id, value: U.fmt(totNom.value, totNom.unit) }]
            .concat(lineIds.map((id) => data[id]).filter(Boolean).map((ser) => { const p = U.pointFor(ser, 'nominal', year); return p ? { label: humanTitle(ser), id: p.provenance_id, value: U.fmt(p.value, p.unit) } : null; }).filter(Boolean)),
        }),
      });
    }
    linesHost.appendChild(U.barList(rows, { max: totNom.value }));
    linesHost.appendChild(h('p', { class: 'small muted' }, 'Bars are drawn against the GB total (cash), so a full-width bar would be all benefit spending.'));
    if (rest > 0.0005) {
      linesHost.appendChild(U.note('bad', h('strong', null, 'These lines do not add up to the total. '),
        'The build reads only some Table 1a lines. See rule R7 on the ', h('a', { href: 'reconciliation.html#R7' }, 'reconciliation page'), '.'));
    }
  }

  /* --- UK welfare over time --- */
  const overHost = $('#over');
  function renderOver() {
    U.clear(overHost);
    const ser = data[UK_TOTAL];
    if (!ser) { U.state(overHost, 'UK welfare total is not in this build.', 'error'); return; }
    const vf = U.variantFor(ser);
    if (vf.fallback) overHost.appendChild(U.note('warn', vf.fallback));
    overHost.appendChild(U.columnChart(ser, vf.points, { heading: 'UK welfare spending', sub: U.basisCaption(vf.variant, ix) + '. Source: DWP benefit expenditure tables, UK welfare tab.' }));
    const gn = U.gapsNote(ser); if (gn) overHost.appendChild(gn);
    overHost.appendChild(U.seriesTable(ser, vf.points, 'UK welfare spending'));
  }

  const cl = $('#caseloads');
  U.clear(cl);
  if (caseloads.length) {
    cl.appendChild(h('ul', null, caseloads.map((x) => h('li', null, x.title))));
  } else {
    cl.appendChild(h('p', { class: 'muted' }, 'This build has no caseload series (how many people receive each benefit). They are not shown until a published table is parsed; we do not estimate them.'));
  }

  renderDefs(); renderLines(); renderOver();
  U.onBasis(() => { renderDefs(); renderLines(); renderOver(); });
});
