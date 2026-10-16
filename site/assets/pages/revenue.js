/* Where £1 comes from: HMRC receipts by tax (cash, UK) plus receipts over time. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const ix = await U.index();
  // Sub-lines and memo columns that are already inside a top-level line (adding them would double count).
  const SUBLINES = new Set(['total', 'total_paid_over', 'income_tax_paye', 'income_tax_self_assessment',
    'paye_nic1_emp_ee', 'paye_nic1_emp_er', 'sa_nic2_4', 'corporation_tax_offshore']);
  const lineIds = ix.series.filter((x) => x.id.startsWith('hmrc_receipts.') && !SUBLINES.has(x.id.slice('hmrc_receipts.'.length))).map((x) => x.id);
  const TOTAL = 'hmrc_receipts.total';
  const EFO = ix.series.filter((x) => x.id.startsWith('obr_efo_receipts.')).map((x) => x.id);
  const data = await U.seriesMany([...lineIds, ...EFO, TOTAL, 'obr.psf.receipts', 'hmrc_receipts.income_tax_paye', 'hmrc_receipts.income_tax_self_assessment']);
  const total = data[TOTAL];
  if (!total) throw new Error('HMRC total receipts are missing from this build');
  const nice = (ser) => {
    const t = (ser.title || ser.id).replace(/^HMRC tax and NICs receipts for the UK:\s*/, '');
    const fixed = { nics: 'National Insurance', vat: 'VAT', 'hydrocarbon oil fuel duties': 'Fuel duty', 'stamp duty land tax': 'Stamp duty on property', sdlt: 'Stamp duty on property',
      'betting gaming': 'Betting and gaming duties', 'income tax paye': 'Income tax: PAYE', 'income tax self assessment': 'Income tax: self assessment',
      'stamp duty shares': 'Stamp duty on shares', 'tobacco duties': 'Tobacco duty', 'spirits duties': 'Spirits duty', 'wine duties': 'Wine duty', 'beer duties': 'Beer duty', 'cider duties': 'Cider duty' }[t.toLowerCase()];
    return fixed || (t.charAt(0).toUpperCase() + t.slice(1));
  };
  const years = total.variants.nominal.map((p) => p.fiscal_year);
  let year = years[years.length - 1];
  let showAll = false;
  let tax = 'hmrc_receipts.income_tax';

  const poundHost = $('#pound');
  $('#pound-tools').appendChild(U.yearSelect('Year', years, year, (y) => { year = y; renderPound(); }));

  let setSummaryFor = null;
  function renderPound() {
    U.clear(poundHost);
    const tot = U.pointFor(total, 'nominal', year);
    if (!tot) { U.state(poundHost, 'We don’t show a total for ' + year + ' yet.'); return; }
    let itemised = 0;
    const items = [];
    lineIds.map((id) => data[id]).filter(Boolean).forEach((ser) => {
      const nom = U.pointFor(ser, 'nominal', year);
      if (!nom) return;
      itemised += nom.value;
      const label = nice(ser);
      items.push({ label, src: nom, fullLabel: label + ', ' + year, value: (nom.value / tot.value) * 100, forecast: nom.status === 'forecast', spec: U.shareSpec(label, year, nom, tot, 'tax collected by HMRC') });
    });
    items.sort((a, b) => b.value - a.value);
    const diff = tot.value - itemised;
    if (diff / tot.value > 0.0005) {
      items.push({ label: 'Everything else', rest: true, value: (diff / tot.value) * 100, spec: { title: 'Everything else', text: 'The published total minus the taxes listed.', formula: 'Total − listed taxes, ' + year, inputs: [{ label: 'Total ' + year, id: tot.provenance_id, value: U.fmt(tot.value, tot.unit) }] } });
    }
    const rows = U.splitOf100(items);
    poundHost.appendChild(h('p', null, 'In ', h('strong', null, year), ', the tax office (HMRC) collected ',
      U.num(U.pointFor(total, U.variantFor(total).variant, year), { label: 'Total HMRC receipts ' + year, badge: false }), '. Out of every £100, here is where it came from:'));
    const max = Math.max(...rows.map((r) => r.barValue));
    /* Short view: the biggest 7 taxes, then everything else in one grey row (always last). */
    let visible = rows;
    const named = rows.filter((r) => !r.rest);
    if (!showAll && named.length > 7) {
      const shown = named.slice(0, 7);
      const others = rows.filter((r) => !shown.includes(r));
      const n = others.reduce((a, r) => a + r.int, 0);
      const bv = others.reduce((a, r) => a + r.barValue, 0);
      visible = shown.concat([{ label: 'Everything else', rest: true, barValue: bv, int: n, text: U.per100Int(n),
        valueNode: U.derivedNum(U.per100Int(n), { title: 'Out of every £100: everything else', text: 'The ' + others.length + ' smaller taxes added together, ' + year + '.', formula: others.map((r) => r.label).join(' + '), inputs: [] }) }]);
    }
    const st = items.some((i) => i.forecast) ? 'mixed' : 'actual';
    const left = h('div', null, U.scopeChip(year, 'UK', st), U.barList(visible, { max, unitHead: 'Out of every £100' }),
      h('p', { class: 'small muted' }, 'Whole pounds, adding up to £100.'));
    const right = h('div');
    const pp = U.perHead(total, 'per_person', year); const ph = U.perHead(total, 'per_household', year);
    const sideHost = h('div', { class: 'side' }, left, right);
    poundHost.appendChild(sideHost);
    if (pp) right.appendChild(U.perPersonNote(pp, 'the UK', 'Tax collected per person ' + year));
    const phn = U.perHouseholdNote(ph, 'Tax collected per household ' + year,
      'We do not show tax collected per household for ' + year + ': household counts only cover ' + U.perHousehold(ix).first + ' to ' + U.perHousehold(ix).last + '.');
    if (phn) right.appendChild(phn);
    if (named.length > 7) {
      poundHost.appendChild(h('p', { class: 'more' }, h('button', {
        type: 'button', class: 'btn', 'aria-expanded': String(showAll),
        onclick: () => { showAll = !showAll; renderPound(); },
      }, showAll ? 'Show the biggest taxes only' : 'Show all ' + named.length + ' taxes')));
    }
    if (rows[0]) {
      right.insertBefore(U.squares({ on: rows[0].int, bracket: rows[0].text, title: rows[0].label + ': ' + rows[0].text + ' out of every £100',
        caption: rows[0].label + ': ' + rows[0].text + ' of every £100', keyOn: rows[0].label, keyOff: 'Everything else', source: 'Source: HM Revenue and Customs, ' + year + '.' }), right.firstChild);
    }
    if (setSummaryFor) setSummaryFor(rows, items);
  }

  const overHost = $('#over');
  /* One chart: tax collected by HMRC, drawn inside all government income (OBR). The pale part is income
     that HMRC does not collect, such as council tax and business rates. */
  function renderOver() {
    U.clear(overHost);
    const obr = data['obr.psf.receipts'];
    const vf = U.variantFor(total);
    if (vf.fallback) overHost.appendChild(U.note('warn', vf.fallback));
    let behind = null;
    if (obr) {
      const bp = (obr.variants[vf.variant] || []);
      const yrs = new Set(vf.points.map((p) => p.fiscal_year));
      const pts = bp.filter((p) => yrs.has(p.fiscal_year));
      if (pts.length) behind = { points: pts, label: 'All government income', legend: 'All government income (OBR)' };
    }
    const common = behind ? vf.points.filter((p) => behind.points.some((q) => q.fiscal_year === p.fiscal_year && q.value > p.value)) : [];
    const ay = common.length ? common[common.length - 1].fiscal_year : null;
    overHost.appendChild(U.columnChart(total, vf.points, {
      heading: 'Tax collected by HMRC, inside all government income', behind, mainLegend: 'Tax collected by HMRC',
      annotations: ay ? [{ year: ay, text: 'Pale part: income HMRC does not collect' }] : [],
      scope: U.scopeChip(vf.points.length ? vf.points[0].fiscal_year + ' to ' + vf.points[vf.points.length - 1].fiscal_year : '', 'UK', vf.points.some((p) => p.status === 'forecast') ? 'mixed' : 'actual'),
      caption: U.basisCaption(vf.variant, ix) + '.',
      sub: 'Sources: HM Revenue and Customs (cash collected); Office for Budget Responsibility (all income, including council tax and business rates).' }));
    const gn = U.gapsNote(total); if (gn) overHost.appendChild(gn);
    overHost.appendChild(U.seriesTable(total, vf.points, 'Tax collected by HMRC (' + U.basisCaption(vf.variant, ix) + ')', 'Show tax collected by HMRC as a table'));
    if (obr) {
      const ov = U.variantFor(obr);
      overHost.appendChild(U.seriesTable(obr, ov.points, 'All government income, OBR (' + U.basisCaption(ov.variant, ix) + ')', 'Show all government income as a table'));
    } else overHost.appendChild(U.gapBox('All government income (OBR) is not in this build.'));
  }

  const taxHost = $('#tax');
  const taxOpts = lineIds.filter((id) => data[id]).map((id) => [id, nice(data[id])]).sort((a, b) => a[1].localeCompare(b[1]));
  taxOpts.push(['hmrc_receipts.income_tax_paye', 'Income tax: PAYE (part of income tax)'], ['hmrc_receipts.income_tax_self_assessment', 'Income tax: self assessment (part of income tax)']);
  $('#tax-tools').appendChild(U.selectField('Tax', taxOpts.filter(([id]) => data[id]), tax, (v) => { tax = v; renderTax(); }));
  function renderTax() {
    U.clear(taxHost);
    const ser = data[tax];
    if (!ser) { U.state(taxHost, 'Series not available.', 'error'); return; }
    const vf = U.variantFor(ser);
    if (vf.fallback) taxHost.appendChild(U.note('warn', vf.fallback));
    taxHost.appendChild(U.columnChart(ser, vf.points, { heading: nice(ser), caption: U.basisCaption(vf.variant, ix) + '.', sub: 'Source: HM Revenue and Customs. Cash collected.' }));
    const gn = U.gapsNote(ser); if (gn) taxHost.appendChild(gn);
    taxHost.appendChild(U.seriesTable(ser, vf.points, nice(ser)));
  }

  /* OBR forecast of receipts: every point is a forecast; % of GDP only if the API has the variant. */
  const efoHost = $('#efo');
  let efo = EFO.find((id) => id === 'obr_efo_receipts.current_receipts') || EFO[0];
  const efoName = (ser) => (ser.title || ser.id).replace(/\s*\(OBR EFO[^)]*\)\s*$/, '');
  function renderEfo() {
    U.clear(efoHost);
    const ser = data[efo];
    if (!ser) { U.state(efoHost, 'The OBR forecasts are not in this build.'); return; }
    const vf = U.variantFor(ser);
    efoHost.appendChild(U.note('warn', h('strong', null, 'These are forecasts. '), 'The Office for Budget Responsibility expects these amounts. They are not what was collected.'));
    if (vf.fallback) efoHost.appendChild(U.note('warn', vf.fallback));
    efoHost.appendChild(U.columnChart(ser, vf.points, { heading: efoName(ser) + ' (forecast)', caption: 'Forecast. ' + U.basisCaption(vf.variant, ix) + '.', sub: 'Source: Office for Budget Responsibility, Economic and fiscal outlook.' }));
    const gn = U.gapsNote(ser); if (gn) efoHost.appendChild(gn);
    efoHost.appendChild(U.seriesTable(ser, vf.points, efoName(ser) + ', forecast (' + U.basisCaption(vf.variant, ix) + ')'));
  }
  if (EFO.length && efoHost) {
    $('#efo-tools').appendChild(U.selectField('Forecast of', EFO.filter((id) => data[id]).map((id) => [id, U.cap1(efoName(data[id]).toLowerCase())]), efo, (v) => { efo = v; renderEfo(); }));
  } else if (efoHost) {
    U.state(efoHost, 'We do not have the OBR forecasts in this build.');
  }

  setSummaryFor = (rows, items) => {
    const top = rows[0];
    if (!top) return;
    U.setSummary(['In ' + year + ', about ', U.derivedNum(top.text, items[0].spec), ' of every £100 the tax office collected came from ' + (/^(VAT|National)/.test(top.label) ? top.label : top.label.toLowerCase()) + '.'],
      'Actual figures · shares of each year’s tax, so the same whichever way amounts are shown · last updated ' + U.updatedText(ix), items[0].src);
  };
  renderPound(); renderOver(); renderTax(); if (EFO.length) renderEfo();
  U.onBasis(() => { renderOver(); renderTax(); if (EFO.length) renderEfo(); });
  U.mountCheckers({
    figures: [
      { label: 'Tax collected by HMRC, ' + year, point: U.pointFor(total, 'nominal', year) },
      { label: 'All government income, ' + ix.fiscal_years.latest_outturn, point: data['obr.psf.receipts'] && U.pointFor(data['obr.psf.receipts'], 'nominal', ix.fiscal_years.latest_outturn) },
    ],
    recon: ['R6'],
    method: ['Tax collected is the HMRC receipts table, in cash. All government income is “public sector current receipts” from the OBR databank, which is on an accruals basis and also covers council tax and business rates.', 'Forecasts are from the OBR Economic and fiscal outlook and are marked as forecasts everywhere. Percent of GDP is shown only where the data has it. Per-person amounts use the ONS population; per-household amounts use the ONS household count, which only covers ' + U.perHousehold(ix).first + ' to ' + U.perHousehold(ix).last + '.', 'Each part out of £100 is that tax divided by the HMRC total for the same year, in cash terms. Whole pounds use the largest-remainder method so they add up to exactly £100.'],
  });
});
