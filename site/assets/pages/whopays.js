/* Who pays: HMRC income tax liabilities and taxpayers by income band (Table 2.5, from 2023-24). */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const ix = await U.index();
  const bandOf = (id) => { const m = /\.band\.from_(\d+)$/.exec(id); return m ? +m[1] : null; };
  const liabIds = ix.series.filter((x) => x.id.startsWith('hmrc_income_tax.liabilities.band.')).map((x) => x.id).sort((a, b) => bandOf(a) - bandOf(b));
  const payIds = ix.series.filter((x) => x.id.startsWith('hmrc_income_tax.payers.band.')).map((x) => x.id).sort((a, b) => bandOf(a) - bandOf(b));
  const RATES = ['savers', 'basic', 'higher', 'additional'];
  const rateLiab = RATES.map((r) => 'hmrc_income_tax.liabilities.rate.' + r);
  const ratePay = RATES.map((r) => 'hmrc_income_tax.payers.rate.' + r);
  const TL = 'hmrc_income_tax.liabilities_total'; const TP = 'hmrc_income_tax.payers.all';
  const data = await U.seriesMany([...liabIds, ...payIds, ...rateLiab, ...ratePay, TL, TP]);
  const tl = data[TL];
  if (!tl) throw new Error('Total income tax liabilities are missing from this build');
  const years = tl.variants.nominal.map((p) => p.fiscal_year);
  const latest = ix.fiscal_years && ix.fiscal_years.latest_outturn;
  const outturnYears = tl.variants.nominal.filter((p) => p.status === 'outturn').map((p) => p.fiscal_year);
  let year = outturnYears.length ? outturnYears[outturnYears.length - 1] : (years.includes(latest) ? latest : years[years.length - 1]);

  const pounds = (n) => '£' + n.toLocaleString('en-GB');
  const bounds = liabIds.map(bandOf);
  const bandLabel = (lo) => { const i = bounds.indexOf(lo); const hi = bounds[i + 1]; return hi ? pounds(lo) + ' to ' + pounds(hi) : pounds(lo) + ' and over'; };
  const rateLabel = { savers: 'Starting rate for savings', basic: 'Basic rate', higher: 'Higher rate', additional: 'Additional rate' };

  $('#tools').appendChild(U.yearSelect('Tax year', years, year, (y) => { year = y; render(); }));
  const headHost = $('#head'); const liabHost = $('#liab'); const payHost = $('#payers'); const rateHost = $('#rates');

  function shareRows(ids, totalSer, kind, labelFn) {
    const totNom = U.pointFor(totalSer, 'nominal', year);
    let fallback = null;
    const rows = ids.map((id) => data[id]).filter(Boolean).map((ser) => {
      const nom = U.pointFor(ser, 'nominal', year);
      const vf = U.variantFor(ser);
      if (vf.fallback && kind === 'money') fallback = vf.fallback;
      const label = labelFn(ser.id);
      if (!nom) return { label, sub: (U.gapFor(ser, year) || {}).reason || 'No figure', barValue: 0, point: null };
      const share = totNom ? (nom.value / totNom.value) * 100 : null;
      const what = kind === 'money' ? 'of all income tax' : 'of all taxpayers';
      return {
        label, fullLabel: label + ', ' + year, point: U.pointFor(ser, vf.variant, year), barValue: nom.value, forecast: nom.status === 'forecast',
        share: share == null ? null : {
          text: (share < 1 ? share.toFixed(2) : share.toFixed(1)) + '% ' + what,
          spec: {
            title: 'Share ' + what + ': ' + label,
            formula: label + ' ÷ total, ' + year + ' × 100',
            inputs: [
              { label: label + ' ' + year, id: nom.provenance_id, value: U.fmt(nom.value, nom.unit) },
              { label: 'Total ' + year, id: totNom.provenance_id, value: U.fmt(totNom.value, totNom.unit) },
            ],
          },
        },
      };
    });
    return { rows, fallback };
  }

  function render() {
    U.clear(headHost); U.clear(liabHost); U.clear(payHost); U.clear(rateHost);
    const tlVf = U.variantFor(tl);
    const tlPt = U.pointFor(tl, tlVf.variant, year);
    const tpPt = data[TP] && U.pointFor(data[TP], 'nominal', year);
    const isFc = tlPt && tlPt.status === 'forecast';
    headHost.appendChild(h('div', { class: 'grid grid-2' },
      h('div', { class: 'card tile' }, h('p', { class: 'label' }, 'Income tax liabilities, ' + year), h('div', { class: 'hero-num' }, U.num(tlPt, { label: 'Total income tax liabilities ' + year })),
        tlVf.fallback ? h('p', { class: 'small muted' }, tlVf.fallback) : null),
      h('div', { class: 'card tile' }, h('p', { class: 'label' }, 'Income tax payers, ' + year), h('div', { class: 'hero-num' }, U.num(tpPt, { label: 'Income tax payers ' + year })))));
    if (isFc) headHost.appendChild(U.note('warn', h('strong', null, year + ' is a projection. '), 'HMRC projects liabilities for years after the latest Survey of Personal Incomes. These are marked Forecast.'));

    const L = shareRows(liabIds, tl, 'money', (id) => bandLabel(bandOf(id)));
    if (L.fallback) liabHost.appendChild(U.note('warn', L.fallback));
    liabHost.appendChild(U.barList(L.rows));
    const P = shareRows(payIds, data[TP], 'people', (id) => bandLabel(bandOf(id)));
    payHost.appendChild(U.barList(P.rows));

    const RL = shareRows(rateLiab, tl, 'money', (id) => rateLabel[id.split('.').pop()] || id);
    const RP = shareRows(ratePay, data[TP], 'people', (id) => rateLabel[id.split('.').pop()] || id);
    rateHost.appendChild(h('div', { class: 'grid grid-2' },
      h('div', { class: 'card' }, h('h3', null, 'Income tax by marginal rate'), U.barList(RL.rows)),
      h('div', { class: 'card' }, h('h3', null, 'Taxpayers by marginal rate'), U.barList(RP.rows))));
  }
  render();
  U.onBasis(render);
});
