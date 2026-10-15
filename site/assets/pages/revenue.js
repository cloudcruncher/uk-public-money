/* Where £1 comes from: HMRC receipts by tax (cash, UK) plus receipts over time. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const ix = await U.index();
  // Sub-lines and memo columns that are already inside a top-level line (adding them would double count).
  const SUBLINES = new Set(['total', 'total_paid_over', 'income_tax_paye', 'income_tax_self_assessment',
    'paye_nic1_emp_ee', 'paye_nic1_emp_er', 'sa_nic2_4', 'corporation_tax_offshore']);
  const lineIds = ix.series.filter((x) => x.id.startsWith('hmrc_receipts.') && !SUBLINES.has(x.id.slice('hmrc_receipts.'.length))).map((x) => x.id);
  const TOTAL = 'hmrc_receipts.total';
  const data = await U.seriesMany([...lineIds, TOTAL, 'obr.psf.receipts', 'hmrc_receipts.income_tax_paye', 'hmrc_receipts.income_tax_self_assessment']);
  const total = data[TOTAL];
  if (!total) throw new Error('HMRC total receipts are missing from this build');
  const nice = (ser) => {
    const t = (ser.title || ser.id).replace(/^HMRC tax and NICs receipts for the UK:\s*/, '');
    const fixed = { nics: 'National Insurance contributions', vat: 'VAT' }[t];
    return fixed || (t.charAt(0).toUpperCase() + t.slice(1));
  };
  const years = total.variants.nominal.map((p) => p.fiscal_year);
  let year = years[years.length - 1];
  let showAll = false;
  let tax = 'hmrc_receipts.income_tax';

  const poundHost = $('#pound');
  $('#pound-tools').appendChild(U.yearSelect('Year', years, year, (y) => { year = y; renderPound(); }));

  function renderPound() {
    U.clear(poundHost);
    const tot = U.pointFor(total, 'nominal', year);
    if (!tot) { U.state(poundHost, 'No HMRC total for ' + year + '.'); return; }
    let fallback = null; let itemised = 0;
    const rows = [];
    lineIds.map((id) => data[id]).filter(Boolean).forEach((ser) => {
      const nom = U.pointFor(ser, 'nominal', year);
      if (!nom) return;
      itemised += nom.value;
      const vf = U.variantFor(ser);
      if (vf.fallback) fallback = vf.fallback;
      const label = nice(ser);
      const pence = (nom.value / tot.value) * 100;
      rows.push({
        label, fullLabel: label + ', ' + year, point: U.pointFor(ser, vf.variant, year), barValue: pence, forecast: nom.status === 'forecast',
        share: {
          text: (pence < 0.1 ? pence.toFixed(2) : pence.toFixed(1)) + 'p',
          spec: {
            title: 'Pence in every £1: ' + label,
            formula: label + ' ÷ total HMRC receipts, cash, ' + year + ' × 100',
            inputs: [
              { label: label + ' ' + year, id: nom.provenance_id, value: U.fmt(nom.value, nom.unit) },
              { label: 'Total HMRC receipts ' + year, id: tot.provenance_id, value: U.fmt(tot.value, tot.unit) },
            ],
          },
        },
      });
    });
    rows.sort((a, b) => b.barValue - a.barValue);
    const totShown = U.pointFor(total, U.variantFor(total).variant, year);
    poundHost.appendChild(h('p', null, 'Of every £1 HMRC collected in ', h('strong', null, year), ' (total ', U.num(totShown, { label: 'Total HMRC receipts ' + year }), '):'));
    if (fallback) poundHost.appendChild(U.note('warn', fallback));
    const max = Math.max(...rows.map((r) => r.barValue));
    const visible = showAll ? rows : rows.slice(0, 10);
    poundHost.appendChild(U.barList(visible, { max }));
    const diff = tot.value - itemised;
    if (Math.abs(diff) >= 0.05) {
      poundHost.appendChild(U.note('warn', h('strong', null, 'Lines do not add up exactly. '),
        'The taxes listed sum to ' + U.fmt(itemised, 'GBP_bn') + ', the published total is ' + U.fmt(tot.value, 'GBP_bn') + ' (difference ' + U.fmt(diff, 'GBP_bn') + '). We show the difference rather than adjust anything.'));
    }
    if (rows.length > 10) {
      poundHost.appendChild(h('p', { class: 'more' }, h('button', {
        type: 'button', class: 'btn', 'aria-expanded': String(showAll),
        onclick: () => { showAll = !showAll; renderPound(); },
      }, showAll ? 'Show the top 10 only' : 'Show all ' + rows.length + ' taxes')));
    }
  }

  const overHost = $('#over');
  function renderOver() {
    U.clear(overHost);
    const grid = h('div', { class: 'grid grid-2' });
    [[TOTAL, 'HMRC tax and NICs receipts (cash)', 'HMRC receipts: taxes HMRC collects, cash basis.'],
      ['obr.psf.receipts', 'Public sector current receipts (accrued)', 'OBR databank: all public sector receipts, including council tax and business rates.']].forEach(([id, head, sub]) => {
      const ser = data[id];
      const cell = h('div');
      if (!ser) { U.state(cell, head + ' is not in this build.', 'error'); grid.appendChild(cell); return; }
      const vf = U.variantFor(ser);
      if (vf.fallback) cell.appendChild(U.note('warn', vf.fallback));
      cell.appendChild(U.columnChart(ser, vf.points, { heading: head, sub: sub + ' ' + U.basisCaption(vf.variant, ix) + '.' }));
      const gn = U.gapsNote(ser); if (gn) cell.appendChild(gn);
      cell.appendChild(U.seriesTable(ser, vf.points, head));
      grid.appendChild(cell);
    });
    overHost.appendChild(grid);
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
    taxHost.appendChild(U.columnChart(ser, vf.points, { heading: nice(ser), sub: U.basisCaption(vf.variant, ix) + '. Source: HMRC receipts, cash basis.' }));
    const gn = U.gapsNote(ser); if (gn) taxHost.appendChild(gn);
    taxHost.appendChild(U.seriesTable(ser, vf.points, nice(ser)));
  }

  renderPound(); renderOver(); renderTax();
  U.onBasis(() => { renderPound(); renderOver(); renderTax(); });
});
