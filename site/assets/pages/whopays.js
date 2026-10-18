/* Who pays: HMRC income tax liabilities and taxpayers by income band (Table 2.5 and 2.5a, from 2015-16). */
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
  const headHost = $('#head'); const groupHost = $('#groups'); const liabHost = $('#liab'); const payHost = $('#payers'); const rateHost = $('#rates');

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

  const pt2 = (v) => (v == null ? 'Not published' : (v < 1 ? v.toFixed(1) : String(Math.round(v))));
  function render() {
    U.clear(headHost); U.clear(groupHost); U.clear(liabHost); U.clear(payHost); U.clear(rateHost);
    const tlVf = U.variantFor(tl);
    const tlPt = U.pointFor(tl, tlVf.variant, year);
    const tpPt = data[TP] && U.pointFor(data[TP], 'nominal', year);
    const isFc = tlPt && tlPt.status === 'forecast';
    /* Five plain groups made by adding the tax office's own bands (never re-banded inside a band). */
    const GROUPS = [['Under £20,000', 0, 20000], ['£20,000 to £50,000', 20000, 50000], ['£50,000 to £100,000', 50000, 100000], ['£100,000 to £200,000', 100000, 200000], ['£200,000 and over', 200000, Infinity]];
    const totL = U.pointFor(tl, 'nominal', year); const totP = data[TP] && U.pointFor(data[TP], 'nominal', year);
    const sumFor = (ids, lo, hi) => {
      const pts = ids.filter((id) => bandOf(id) >= lo && bandOf(id) < hi).map((id) => data[id] && U.pointFor(data[id], 'nominal', year));
      if (!pts.length || pts.some((x) => !x)) return null;
      return { value: pts.reduce((a, x) => a + x.value, 0), pts };
    };
    const shareSpec = (title, s, tot, ids) => ({ title, text: 'The tax office bands added together, divided by the total, ' + year + '.', formula: 'Sum of bands ÷ total × 100',
      inputs: s.pts.map((x, k) => ({ label: 'Band ' + (k + 1), id: x.provenance_id, value: U.fmt(x.value, x.unit) })).concat([{ label: 'Total ' + year, id: tot.provenance_id, value: U.fmt(tot.value, tot.unit) }]) });
    const groups = (totL && totP) ? GROUPS.map(([label, lo, hi]) => {
      const l = sumFor(liabIds, lo, hi); const pp = sumFor(payIds, lo, hi);
      return { label, lo, liab: l && (l.value / totL.value) * 100, pay: pp && (pp.value / totP.value) * 100, l, pp };
    }) : [];
    const top = groups.filter((g) => g.lo >= 100000);
    const topPay = top.every((g) => g.pay != null) ? top.reduce((a, g) => a + g.pay, 0) : null;
    const topLiab = top.every((g) => g.liab != null) ? top.reduce((a, g) => a + g.liab, 0) : null;
    if (topPay != null && topLiab != null) {
      const ppl = Math.round(topPay); const pnd = Math.round(topLiab);
      const pplText = ppl < 1 ? 'fewer than 1' : 'about ' + ppl;
      headHost.appendChild(h('p', { class: 'hero-says' }, 'People earning over £100,000 a year are ', h('strong', null, pplText + ' in every 100'), ' taxpayers. Together they owe ', h('strong', null, 'about £' + pnd + ' of every £100'), ' of income tax.'));
      headHost.appendChild(h('div', { class: 'pair' },
        U.peopleGrid({ on: ppl, title: 'Taxpayers earning over £100,000: ' + pplText + ' in every 100', scope: U.scopeChip(year, 'UK', isFc ? 'forecast' : 'actual'),
          caption: 'Every 100 taxpayers', keyOn: 'Earn over £100,000 (' + ppl + ')', keyOff: 'Earn less (' + (100 - ppl) + ')' }),
        U.squares({ on: pnd, bracket: '£' + pnd, size: 'lg', title: 'Income tax owed by people earning over £100,000: about £' + pnd + ' of every £100', scope: U.scopeChip(year, 'UK', isFc ? 'forecast' : 'actual'),
          caption: 'Every £100 of income tax', keyOn: 'Owed by people earning over £100,000 (£' + pnd + ')', keyOff: 'Owed by everyone else (£' + (100 - pnd) + ')' })));
    }
    if (groups.length) {
      const list = h('div', { class: 'card' });
      groups.forEach((g) => {
        const bar = (pct, cls) => { const seg = h('span', { class: 'strip-seg ' + cls }); seg.style.flexGrow = String(Math.max(0, pct || 0)); const base = h('span', { class: 'strip-seg base' }); base.style.flexGrow = String(Math.max(0, 100 - (pct || 0))); return h('div', { class: 'strip', 'aria-hidden': 'true' }, seg, base); };
        const pt = (v) => (v == null ? 'not published' : (v < 1 ? v.toFixed(1) : Math.round(v)) + ' in 100');
        list.appendChild(h('div', { class: 'strip-row' }, h('span', { class: 'who' }, g.label),
          h('div', { class: 'strip-pair' },
            h('span', { class: 'lbl' }, h('span', null, 'Share of taxpayers'), g.pp ? U.derivedNum(pt(g.pay), shareSpec('Share of taxpayers: ' + g.label, g.pp, totP)) : h('span', null, 'not published')), bar(g.pay, 'tone-4'),
            h('span', { class: 'lbl' }, h('span', null, 'Share of income tax'), g.l ? U.derivedNum(g.liab == null ? '' : '£' + (g.liab < 1 ? g.liab.toFixed(1) : Math.round(g.liab)) + ' of £100', shareSpec('Share of income tax: ' + g.label, g.l, totL)) : h('span', null, 'not published')), bar(g.liab, 'tone-1'))));
      });
      groupHost.appendChild(h('figure', { class: 'chart-fig' }, h('figcaption', null, U.scopeChip(year, 'UK', isFc ? 'forecast' : 'actual'),
        h('p', { class: 'caption-text' }, 'For each income group: how many of the taxpayers they are, and how much of the income tax they owe.')), list,
        U.tableView('Share of taxpayers and of income tax by income group, ' + year, ['Income group', 'Taxpayers (in 100)', 'Income tax (£ of £100)'],
          groups.map((g) => [g.label, pt2(g.pay), pt2(g.liab)]))));
      groupHost.appendChild(h('p', { class: 'small muted' }, 'People earning less than £12,570 a year usually pay no income tax, so they are not in these figures.'));
    } else {
      U.state(groupHost, 'We can’t show the income groups for ' + year + ': the totals are not published.');
    }
    headHost.appendChild(h('div', { class: 'grid grid-2' },
      h('div', { class: 'card tile' }, h('p', { class: 'label' }, 'Income tax owed, ' + year), h('div', { class: 'hero-num' }, U.num(tlPt, { label: 'Total income tax owed ' + year, badge: false })),
        tlVf.fallback ? h('p', { class: 'small muted' }, tlVf.fallback) : null),
      h('div', { class: 'card tile' }, h('p', { class: 'label' }, 'People who pay income tax, ' + year), h('div', { class: 'hero-num' }, U.num(tpPt, { label: 'People who pay income tax ' + year, badge: false })))));
    U.setSummary([isFc ? 'The tax office expects ' : 'In ' + year + ', ', tpPt ? U.num(tpPt, { label: 'People who pay income tax ' + year, check: false, badge: false }) : 'an unpublished number of people',
      isFc ? ' people to owe about ' : ' people owed about ', U.num(tlPt, { label: 'Total income tax owed ' + year, check: false, badge: false }), ' in income tax' + (isFc ? ' in ' + year + '.' : '.')],
      (isFc ? 'Forecast figures' : 'Actual figures') + ' · ' + U.basisShort(tlVf.variant) + ' · last updated ' + U.updatedText(ix), tlPt);
    if (isFc) headHost.appendChild(U.note('warn', h('strong', null, year + ' is a projection. '), 'The tax office projects amounts for years after its latest survey. These are marked Forecast.'));

    const L = shareRows(liabIds, tl, 'money', (id) => bandLabel(bandOf(id)));
    if (L.fallback) liabHost.appendChild(U.note('warn', L.fallback));
    liabHost.appendChild(U.barList(L.rows));
    const P = shareRows(payIds, data[TP], 'people', (id) => bandLabel(bandOf(id)));
    payHost.appendChild(U.barList(P.rows));

    const RL = shareRows(rateLiab, tl, 'money', (id) => rateLabel[id.split('.').pop()] || id);
    const RP = shareRows(ratePay, data[TP], 'people', (id) => rateLabel[id.split('.').pop()] || id);
    rateHost.appendChild(h('div', { class: 'grid grid-2' },
      h('div', { class: 'card' }, h('h3', null, 'Income tax owed, by rate'), U.barList(RL.rows)),
      h('div', { class: 'card' }, h('h3', null, 'People, by rate'), U.barList(RP.rows))));
  }
  render();
  U.onBasis(render);
  U.mountCheckers({
    figures: [{ label: 'Income tax owed, ' + year, point: U.pointFor(tl, 'nominal', year) }, { label: 'People who pay income tax, ' + year, point: data[TP] && U.pointFor(data[TP], 'nominal', year) }],
    recon: [],
    method: ['Source: HM Revenue and Customs, Income tax liabilities statistics, Table 2.5. Bands are as the tax office publishes them. We do not re-band.', 'Amounts owed (liabilities) are not the same as cash collected, which is on the revenue page.', 'Years run from 6 April to 5 April. Counts of people are never adjusted for prices.'],
  });
});
