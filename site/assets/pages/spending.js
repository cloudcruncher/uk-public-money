/* Where £1 goes: PESA Table 10.1 (COFOG, England-only TES) plus total spending over time. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const ix = await U.index();
  const funcIds = ix.series.filter((x) => x.id.startsWith('pesa.cofog.') && x.id !== 'pesa.cofog.total_services').map((x) => x.id);
  const TOTAL = 'pesa.cofog.total_services';
  const data = await U.seriesMany([...funcIds, TOTAL, 'obr.psf.tme', 'pesa.tme']);
  const total = data[TOTAL];
  if (!total) throw new Error('PESA Table 10.1 total is missing from this build');
  const short = (ser) => (ser.title || ser.id).split(':')[0];
  const years = total.variants.nominal.map((p) => p.fiscal_year);
  let year = years[years.length - 1];
  let func = TOTAL;

  /* --- Where £1 goes --- */
  const poundHost = $('#pound');
  const poundTools = $('#pound-tools');
  poundTools.appendChild(U.yearSelect('Year', years, year, (y) => { year = y; renderPound(); }));

  function renderPound() {
    U.clear(poundHost);
    const tot = U.pointFor(total, 'nominal', year);
    if (!tot) { U.state(poundHost, 'No Table 10.1 total for ' + year + '.'); return; }
    let fallback = null;
    const rows = funcIds.map((id) => data[id]).filter(Boolean).map((ser) => {
      const nom = U.pointFor(ser, 'nominal', year);
      const vf = U.variantFor(ser);
      if (vf.fallback) fallback = vf.fallback;
      const shown = U.pointFor(ser, vf.variant, year);
      const label = short(ser);
      if (!nom) return { label, sub: (U.gapFor(ser, year) || {}).reason || 'No figure', barValue: 0, point: null };
      const pence = (nom.value / tot.value) * 100;
      return {
        label, fullLabel: label + ', ' + year, point: shown, barValue: pence, forecast: nom.status === 'forecast',
        share: {
          text: pence.toFixed(1) + 'p',
          spec: {
            title: 'Pence in every £1: ' + label,
            text: label + ' was ' + pence.toFixed(2) + 'p of every £1 of identifiable spending on services in England in ' + year + '.',
            formula: label + ' ÷ total expenditure on services (England), cash, ' + year + ' × 100',
            inputs: [
              { label: label + ' ' + year + ' (cash)', id: nom.provenance_id, value: U.fmt(nom.value, nom.unit) },
              { label: 'Total expenditure on services ' + year + ' (cash)', id: tot.provenance_id, value: U.fmt(tot.value, tot.unit) },
            ],
          },
        },
      };
    }).sort((a, b) => b.barValue - a.barValue);
    const totShown = U.pointFor(total, U.variantFor(total).variant, year);
    poundHost.appendChild(h('p', null, 'Of every £1 of identifiable spending on services in England in ', h('strong', null, year), ' (total ',
      U.num(totShown, { label: 'Total expenditure on services, England, ' + year }), '):'));
    if (fallback) poundHost.appendChild(U.note('warn', fallback));
    poundHost.appendChild(U.barList(rows, { max: Math.max(...rows.map((r) => r.barValue)) }));
    poundHost.appendChild(h('p', { class: 'small muted' }, 'Pence are computed from cash figures, so they do not change with the money toggle. Bars show pence per £1; the figure on the right follows the toggle.'));
  }

  /* --- Total spending over time --- */
  const tmeHost = $('#tme');
  function renderTme() {
    U.clear(tmeHost);
    const ser = data['obr.psf.tme'];
    if (!ser) { U.state(tmeHost, 'OBR total managed expenditure is not in this build.', 'error'); return; }
    const vf = U.variantFor(ser);
    if (vf.fallback) tmeHost.appendChild(U.note('warn', vf.fallback));
    tmeHost.appendChild(U.columnChart(ser, vf.points, { heading: 'Total managed expenditure, UK', sub: U.basisCaption(vf.variant, ix) + '. Source: OBR Public Finances Databank.' }));
    tmeHost.appendChild(U.seriesTable(ser, vf.points, 'Total managed expenditure (' + U.basisCaption(vf.variant, ix) + ')'));
  }

  /* --- One function over time --- */
  const fnHost = $('#func');
  const fnTools = $('#func-tools');
  const opts = [[TOTAL, 'All functions (total on services)'], ...funcIds.filter((id) => data[id]).map((id) => [id, short(data[id])])];
  fnTools.appendChild(U.selectField('Function', opts, func, (v) => { func = v; renderFunc(); }));
  function renderFunc() {
    U.clear(fnHost);
    const ser = data[func];
    if (!ser) { U.state(fnHost, 'Series not available.', 'error'); return; }
    const vf = U.variantFor(ser);
    if (vf.fallback) fnHost.appendChild(U.note('warn', vf.fallback));
    fnHost.appendChild(U.columnChart(ser, vf.points, { heading: short(ser) + ', England', sub: U.basisCaption(vf.variant, ix) + '. Source: HM Treasury PESA Table 10.1, newest edition per year.' }));
    const gn = U.gapsNote(ser); if (gn) fnHost.appendChild(gn);
    fnHost.appendChild(U.seriesTable(ser, vf.points, short(ser) + ' (' + U.basisCaption(vf.variant, ix) + ')'));
  }

  renderPound(); renderTme(); renderFunc();
  U.onBasis(() => { renderPound(); renderTme(); renderFunc(); });
});
