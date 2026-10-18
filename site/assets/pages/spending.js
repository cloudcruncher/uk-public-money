/* Where £1 goes: PESA Table 5.2 (COFOG, UK-wide) plus total spending over time. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const ix = await U.index();
  let shares = null;
  try { shares = await U.getJSON('shares.json'); } catch (e) { shares = null; }
  const set = shares && (shares.sets || []).find((x) => x.id === 'spending_uk' && x.available);
  if (!set) throw new Error('The UK-wide spending split is missing from this build');
  const funcIds = set.parts.map((p) => p.series_id);
  const TOTAL = set.total_series_id || 'pesa_uk.services';
  const otherLabel = set.other_label || 'EU transactions and rounding';
  const data = await U.seriesMany([...funcIds, TOTAL, 'obr.psf.tme', 'pesa_uk.public_debt_transactions']);
  const total = data[TOTAL];
  if (!total) throw new Error('PESA total spending on services is missing from this build');
  const short = (ser) => (ser.title || ser.id).split(',')[0];
  const years = total.variants.nominal.map((p) => p.fiscal_year);
  let year = years[years.length - 1];
  let func = TOTAL;

  /* --- Where £1 goes --- */
  const poundHost = $('#pound');
  const poundTools = $('#pound-tools');
  poundTools.appendChild(U.yearSelect('Year', years, year, (y) => { year = y; renderPound(); }));

  function headLine(ser, fy) {
    const out = [];
    const pp = U.perHead(ser, 'per_person', fy); const ph = U.perHead(ser, 'per_household', fy);
    if (pp) out.push(U.perPersonNote(pp, 'the UK', 'Spending on services per person ' + fy));
    out.push(U.perHouseholdNote(ph, 'Spending on services per household ' + fy,
      'We do not show an amount per household for ' + fy + ': household counts only cover ' + U.perHousehold(ix).first + ' to ' + U.perHousehold(ix).last + '.'));
    return out;
  }

  function renderPound() {
    U.clear(poundHost);
    const tot = U.pointFor(total, 'nominal', year);
    if (!tot) { U.state(poundHost, 'We don’t show a total for ' + year + ' yet.'); return; }
    const items = [];
    let sum = 0;
    funcIds.map((id) => data[id]).filter(Boolean).forEach((ser) => {
      const pt = U.pointFor(ser, 'per_100', year);
      if (!pt) return;
      sum += pt.value;
      const label = U.cap1(U.areaName(ser.id, short(ser)));
      items.push({ sid: ser.id, label, fullLabel: label + ', ' + year, value: pt.value, point: pt, forecast: pt.status === 'forecast' });
    });
    items.sort((a, b) => b.value - a.value);
    const rest = 100 - sum;
    let restNote = '';
    if (rest >= 0.05) {
      items.push({ label: U.cap1(otherLabel), value: rest, spec: { title: 'Out of every £100: ' + otherLabel, text: 'What is left after the ten areas are added up.', formula: '100 − the ten areas, ' + year, inputs: [] } });
    } else {
      restNote = ' EU transactions and rounding are too small to show here (' + (Math.abs(rest) < 0.005 ? 'under 1p' : 'about ' + U.per100Text(Math.abs(rest))) + ' out of every £100).';
    }
    const rows = U.splitOf100(items);
    const top = rows[0];
    poundHost.appendChild(h('p', null, 'In ', h('strong', null, year), ', the UK government spent ',
      U.num(U.pointFor(total, U.variantFor(total).variant, year), { label: 'Spending on services, UK, ' + year }),
      ' on public services across the UK. Out of every £100, here is where it went:'));
    /* Bridge to the home-page headline (total managed expenditure), so the two totals do not look like a mismatch. */
    const tmeP = data['obr.psf.tme'] && U.pointFor(data['obr.psf.tme'], 'nominal', year);
    const debtP = data['pesa_uk.public_debt_transactions'] && U.pointFor(data['pesa_uk.public_debt_transactions'], 'nominal', year);
    const svcP = U.pointFor(total, 'nominal', year);
    if (tmeP && svcP && tmeP.value > svcP.value) {
      poundHost.appendChild(h('p', { class: 'small' }, 'Why is this less than the ', U.num(tmeP, { label: 'All government spending, ' + year }),
        ' of all government spending on the home page? That headline is total managed expenditure, which also counts interest on government debt' +
        (debtP && debtP.value > 0 ? ' (' + U.fmt(debtP.value, debtP.unit) + ')' : '') + ' and some accounting items. This page splits spending on services only. The two come from different publications, so a small gap can also come from different forecast dates.'));
    }
    const status = items.some((i) => i.point && i.point.status === 'forecast') ? 'mixed' : 'actual';
    const left = h('div', null, U.scopeChip(year, 'UK', status),
      U.barList(rows, { max: Math.max(...rows.map((r) => r.barValue)), unitHead: 'Out of every £100' }),
      h('p', { class: 'small muted' }, 'Whole pounds, adding up to £100.' + (restNote || ' EU transactions and rounding are shown as “' + otherLabel.toLowerCase() + '”.')));
    const right = h('div');
    if (top) {
      right.appendChild(U.squares({ on: top.int, bracket: top.int >= 1 ? top.text : null, title: top.label + ': ' + top.text + ' out of every £100',
        caption: top.int >= 1 ? top.label + ': ' + top.text + ' of every £100' : 'Less than £1 out of every £100', keyOn: top.label, keyOff: 'Everything else',
        source: 'Source: HM Treasury, Public Expenditure Statistical Analyses, ' + year + '.' }));
    }
    headLine(total, year).forEach((n) => { if (n) right.appendChild(n); });
    poundHost.appendChild(h('div', { class: 'side' }, left, right));
    U.setSummary(['In ' + year + ', about ', top && items[0].point ? U.num(items[0].point, { label: items[0].fullLabel, text: top.text, check: false, badge: false }) : (top ? top.text : ''),
      ' of every £100 spent on public services across the UK went on ' + U.areaName(items[0].sid, items[0].label) + '.'],
      'Actual figures · shares of each year’s spending, so the same whichever way amounts are shown · last updated ' + U.updatedText(ix), items[0].point);
  }

  /* --- Total spending over time --- */
  const tmeHost = $('#tme');
  function renderTme() {
    U.clear(tmeHost);
    const ser = data['obr.psf.tme'];
    if (!ser) { U.state(tmeHost, 'OBR total managed expenditure is not in this build.', 'error'); return; }
    const vf = U.variantFor(ser);
    if (vf.fallback) tmeHost.appendChild(U.note('warn', vf.fallback));
    /* Plain callout on the biggest jump between two actual years, if it is large. 2020-21 is the pandemic year. */
    const pts = vf.points;
    let jump = null;
    for (let i = 1; i < pts.length; i += 1) {
      const a = pts[i - 1]; const b = pts[i];
      if (b.status !== 'forecast' && a.value > 0 && (b.value - a.value) / a.value > 0.1 && (!jump || (b.value - a.value) / a.value > jump.r)) jump = { y: b.fiscal_year, r: (b.value - a.value) / a.value };
    }
    const annotations = jump ? [{ year: jump.y, text: jump.y === '2020-21' ? 'Covid-19 support' : 'Biggest one-year rise' }] : [];
    const st = pts.some((p) => p.status === 'forecast') ? 'mixed' : 'actual';
    tmeHost.appendChild(U.columnChart(ser, pts, { heading: 'All government spending, UK', annotations, fcLabel: 'Forecast by the OBR',
      scope: U.scopeChip(pts.length ? pts[0].fiscal_year + ' to ' + pts[pts.length - 1].fiscal_year : '', 'UK', st),
      caption: 'Total government spending each year. ' + U.basisCaption(vf.variant, ix) + '.', sub: 'Source: Office for Budget Responsibility. Includes interest on debt.' }));
    tmeHost.appendChild(U.seriesTable(ser, vf.points, 'All government spending (' + U.basisCaption(vf.variant, ix) + ')'));
  }

  /* --- One function over time --- */
  const fnHost = $('#func');
  const fnTools = $('#func-tools');
  const opts = [[TOTAL, 'All areas together'], ...funcIds.filter((id) => data[id]).map((id) => [id, U.cap1(U.areaName(id, short(data[id])))])];
  fnTools.appendChild(U.selectField('Area', opts, func, (v) => { func = v; renderFunc(); }));
  function renderFunc() {
    U.clear(fnHost);
    const ser = data[func];
    if (!ser) { U.state(fnHost, 'Series not available.', 'error'); return; }
    const vf = U.variantFor(ser);
    if (vf.fallback) fnHost.appendChild(U.note('warn', vf.fallback));
    fnHost.appendChild(U.columnChart(ser, vf.points, { heading: func === TOTAL ? 'All areas together, UK' : U.cap1(U.areaName(ser.id, short(ser))) + ', UK', caption: U.basisCaption(vf.variant, ix) + '.', sub: 'Source: HM Treasury, Public Expenditure Statistical Analyses.' }));
    const gn = U.gapsNote(ser); if (gn) fnHost.appendChild(gn);
    fnHost.appendChild(U.seriesTable(ser, vf.points, short(ser) + ' (' + U.basisCaption(vf.variant, ix) + ')'));
  }

  renderPound(); renderTme(); renderFunc();
  U.onBasis(() => { renderPound(); renderTme(); renderFunc(); });
  const tmeS = data['obr.psf.tme'];
  const tmeP = tmeS && U.pointFor(tmeS, 'nominal', ix.fiscal_years.latest_outturn);
  U.mountCheckers({
    figures: [
      { label: 'Spending on services, UK, ' + year, point: U.pointFor(total, 'nominal', year) },
      tmeP ? { label: 'All government spending, ' + tmeP.fiscal_year, point: tmeP } : null,
    ].filter(Boolean),
    recon: ['R1', 'R2'],
    method: ['The split by area is Table 5.2 of HM Treasury’s Public Expenditure Statistical Analyses (PESA), grouped by the international COFOG classification. It covers public sector spending on services across the whole UK.',
      'The ten areas do not quite add up to the total: EU transactions and rounding make up the rest, and are shown as “' + otherLabel.toLowerCase() + '” when large enough.',
      'All government spending over time is total managed expenditure (TME) from the OBR Public Finances Databank, UK-wide. It is larger than spending on services because it also counts debt interest and other items.',
      'Each part out of £100 is that area divided by the total, for the same year and edition. Whole pounds use the largest-remainder method so they add up to exactly £100. Per-person amounts use the ONS population; per-household amounts use the ONS household count, which covers ' + U.perHousehold(ix).first + ' to ' + U.perHousehold(ix).last + ' only.'],
  });
});
