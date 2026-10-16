/* Is it true? Common questions answered from the published series. Nothing is typed in by hand:
   every figure is read from the API, and every comparison word ("more", "less") is worked out from the numbers. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const ix = await U.index();
  const checkFigures = [];

  const nom = (ser, y) => U.pointFor(ser, 'nominal', y);
  /* Latest year in which every series has an actual (outturn) figure. */
  function commonYear(sers) {
    const sets = sers.map((s) => new Set(s.variants.nominal.filter((p) => p.status === 'outturn').map((p) => p.fiscal_year)));
    const ys = [...sets[0]].filter((y) => sets.every((s) => s.has(y))).sort();
    return ys.length ? ys[ys.length - 1] : null;
  }
  const prior = (y, n) => { const a = +y.slice(0, 4) - n; return a + '-' + String((a + 1) % 100).padStart(2, '0'); };
  const pct1 = (v) => (v < 10 ? v.toFixed(1) : String(Math.round(v)));
  const input = (label, p) => ({ label, id: p.provenance_id, value: U.fmt(p.value, p.unit) });
  const track = (label, p) => { if (p) checkFigures.push({ label, point: p }); };
  /* "part out of every £100 of total" as a clickable number that shows its working. */
  const per100 = (label, y, part, total, whatTotal) =>
    U.derivedNum(U.per100Text((part.value / total.value) * 100), U.shareSpec(label, y, part, total, whatTotal));
  const money = (p, label) => U.num(p, { label, badge: false });
  const link = (href, text) => h('a', { href }, text);

  async function load(ids) { return U.seriesMany(ids); }

  /* Each question returns { q, answer: [nodes], know: [nodes], more: [href, text] } or throws if data is missing. */
  const QUESTIONS = [
    {
      id: 'welfare-vs-nhs', q: 'Does the government spend more on social protection (mostly pensions and benefits) than on health?',
      async build() {
        const d = await load(['pesa_uk.social_protection', 'pesa_uk.health', 'pesa_uk.tme']);
        const sp = d['pesa_uk.social_protection']; const he = d['pesa_uk.health']; const tme = d['pesa_uk.tme'];
        const y = commonYear([sp, he, tme]);
        const a = nom(sp, y); const b = nom(he, y); const t = nom(tme, y);
        track('Social protection, ' + y, a); track('Health, ' + y, b);
        const more = a.value > b.value;
        let pensions = null;
        try {
          const bx = await U.getJSON('benefits/index.json');
          const sPen = (bx.benefits || []).find((x) => x.slug === 'state-pension');
          pensions = sPen && sPen.headline && sPen.headline.share_of_welfare;
        } catch (e) { pensions = null; }
        return {
          answer: [more ? 'Yes, on this measure. ' : 'No, on this measure. ', 'In ' + y + ', support such as pensions and benefits (“social protection”) cost about ', money(a, 'Social protection, ' + y),
            ' and health cost about ', money(b, 'Health, ' + y), '. Out of every £100 the government spent, about ', per100('Social protection', y, a, t, 'total government spending'),
            ' went on social protection and ', per100('Health', y, b, t, 'total government spending'), ' on health.'],
          know: [pensions ? ['The State Pension alone is about ', U.num(pensions, { label: 'State Pension share of welfare, ' + pensions.fiscal_year, badge: false }), ' of UK welfare spending (' + pensions.fiscal_year + '). That is why a welfare total that includes pensions looks so much bigger than one that leaves them out.'] : 'Social protection includes pensions, not only working-age benefits.',
            ' Social protection also includes social care, and health covers more than the NHS. “Welfare” has more than one official total; ', link('reconciliation.html', 'see why they differ'), '.'],
          more: ['benefits.html', 'See what each benefit costs'],
        };
      },
    },
    {
      id: 'debt-interest', q: 'How much of our money goes on interest on the debt?',
      async build() {
        const d = await load(['ons_psf.cg_debt_interest', 'ons_psf.cg_tme']);
        const i = d['ons_psf.cg_debt_interest']; const t = d['ons_psf.cg_tme'];
        const y = commonYear([i, t]);
        const a = nom(i, y); const b = nom(t, y);
        track('Central government debt interest, ' + y, a);
        return {
          answer: ['In ' + y + ', central government spent about ', money(a, 'Debt interest, ' + y), ' on interest on money it has borrowed. That is about ',
            per100('Debt interest', y, a, b, 'central government spending'), ' of every £100 it spent.'],
          know: ['This is a cost of past borrowing, not a payment for a service. It changes with how much is owed and with interest rates, so it can move quickly. It is paid to those who hold UK government debt, such as pension funds, banks, savers and overseas investors.'],
          more: ['spending.html', 'See where all the money goes'],
        };
      },
    },
    {
      id: 'spend-vs-collect', q: 'Does the government spend more than it collects?',
      async build() {
        const d = await load(['ons_psf.cg_receipts', 'ons_psf.cg_tme', 'ons_psf.ps_net_borrowing_ex_banks']);
        const r = d['ons_psf.cg_receipts']; const s = d['ons_psf.cg_tme']; const bo = d['ons_psf.ps_net_borrowing_ex_banks'];
        const y = commonYear([r, s, bo]);
        const rp = nom(r, y); const sp = nom(s, y); const bp = nom(bo, y);
        track('Central government spending, ' + y, sp); track('Central government income, ' + y, rp); track('Public sector net borrowing, ' + y, bp);
        const gap = sp.value > rp.value;
        return {
          answer: [gap ? 'Yes. ' : 'No. ', 'In ' + y + ', central government spent about ', money(sp, 'Spending, ' + y), ' and collected about ', money(rp, 'Money collected, ' + y),
            '. ', gap ? 'The gap is covered by borrowing. ' : '', 'The whole public sector borrowed about ', money(bp, 'Net borrowing, ' + y), ' that year.'],
          know: ['Borrowing adds to the national debt each year. The yearly gap (the deficit) and the total owed (the debt) are different numbers. Borrowing here is for the whole public sector, so it will not match spending minus income exactly.'],
          more: ['reconciliation.html', 'Why official totals differ'],
        };
      },
    },
    {
      id: 'debt-size', q: 'How big is the national debt?',
      async build() {
        const d = await load(['ons_psf.ps_net_debt_pct_gdp', 'ons_psf.ps_net_debt_gbp_bn']);
        const p = d['ons_psf.ps_net_debt_pct_gdp']; const g = d['ons_psf.ps_net_debt_gbp_bn'];
        const y = commonYear([p, g]); const y0 = prior(y, 10);
        const now = nom(p, y); const then = nom(p, y0); const gb = nom(g, y);
        if (!then) throw new Error('missing comparison year');
        track('Public sector net debt, ' + y, gb); track('Net debt as a share of the economy, ' + y, now);
        const dir = now.value > then.value ? 'up from' : (now.value < then.value ? 'down from' : 'the same as');
        return {
          answer: ['At the end of ' + y + ', the public sector owed about ', money(gb, 'Net debt, ' + y), ' after taking off some of what it holds in cash and similar assets. That is about ',
            U.num(now, { label: 'Net debt as a share of the economy, ' + y, badge: false }), ' of a whole year’s national income, ' + dir + ' ',
            U.num(then, { label: 'Net debt as a share of the economy, ' + y0, badge: false }), ' in ' + y0 + '.'],
          know: ['Experts compare debt with the size of the economy because a bigger economy can carry bigger debts, much as a higher earner can carry a bigger mortgage. A number in pounds on its own can sound larger than it is.'],
          more: ['spending.html', 'See the numbers over time'],
        };
      },
    },
    {
      id: 'state-size', q: 'Is the government getting bigger?',
      async build() {
        const d = await load(['obr.psf.tme', 'obr.gdp_nominal']);
        const t = d['obr.psf.tme']; const g = d['obr.gdp_nominal'];
        const y = commonYear([t, g]);
        const years = t.variants.nominal.filter((p) => p.status === 'outturn' && nom(g, p.fiscal_year)).map((p) => p.fiscal_year);
        const y0 = years[0];
        const share = (yr) => (nom(t, yr).value / nom(g, yr).value) * 100;
        const now = share(y); const then = share(y0);
        let peak = years[0];
        years.forEach((yr) => { if (share(yr) > share(peak)) peak = yr; });
        const spec = (yr) => ({
          title: 'Government spending as a share of the economy, ' + yr,
          text: 'Total government spending divided by the size of the economy that year, times 100.',
          formula: 'Total government spending ÷ size of the economy, ' + yr + ', × 100',
          inputs: [input('Total government spending ' + yr, nom(t, yr)), input('Size of the economy ' + yr, nom(g, yr))],
        });
        track('Total government spending, ' + y, nom(t, y)); track('Size of the economy, ' + y, nom(g, y));
        const dir = now > then ? 'higher' : (now < then ? 'lower' : 'the same');
        return {
          answer: ['Measured against the size of the economy, total government spending was ', U.derivedNum(pct1(now) + '%', spec(y)), ' in ' + y + ', which is ' + dir + ' than ', U.derivedNum(pct1(then) + '%', spec(y0)), ' in ' + y0 + '.'],
          know: [peak !== y && peak !== y0 ? 'It peaked at ' + pct1(share(peak)) + '% in ' + peak + (peak === '2020-21' ? ', when the economy shrank and the government spent heavily to respond to Covid' : '') + '. ' : '',
            'Comparing with the economy is fairer than comparing pounds, because prices and wages rise every year. We do not say whether this is too high or too low.'],
          more: ['spending.html?basis=pct_gdp', 'See spending as a share of the economy'],
        };
      },
    },
    {
      id: 'who-pays-tax', q: 'What share of income tax do high earners pay?',
      async build() {
        const bandOf = (id) => { const m = /\.band\.from_(\d+)$/.exec(id); return m ? +m[1] : null; };
        const liab = ix.series.map((x) => x.id).filter((id) => id.startsWith('hmrc_income_tax.liabilities.band.') && bandOf(id) >= 150000);
        const pay = ix.series.map((x) => x.id).filter((id) => id.startsWith('hmrc_income_tax.payers.band.') && bandOf(id) >= 150000);
        const TL = 'hmrc_income_tax.liabilities_total'; const TP = 'hmrc_income_tax.payers.all';
        if (!liab.length || liab.length !== pay.length) throw new Error('bands missing');
        const d = await load([...liab, ...pay, TL, TP]);
        const y = commonYear([d[TL], d[TP], ...liab.map((i) => d[i]), ...pay.map((i) => d[i])]);
        const sum = (ids) => ids.map((i) => nom(d[i], y));
        const lp = sum(liab); const pp = sum(pay);
        const lt = nom(d[TL], y); const pt = nom(d[TP], y);
        const lShare = (lp.reduce((a, p) => a + p.value, 0) / lt.value) * 100;
        const pShare = (pp.reduce((a, p) => a + p.value, 0) / pt.value) * 100;
        const spec = (title, parts, total, what) => ({
          title, text: 'Adds up everyone with income of £150,000 or more, then divides by all ' + what + ' that year.',
          formula: 'Sum of the bands from £150,000 ÷ total, ' + y + ', × 100',
          inputs: [...parts.map((p, k) => input('Income band ' + (k + 1) + ' of ' + parts.length + ' (from £150,000 up)', p)), input('Total ' + y, total)],
        });
        track('Total income tax, ' + y, lt); track('All income tax payers, ' + y, pt);
        return {
          answer: ['In ' + y + ', people with incomes of £150,000 or more were about ', U.derivedNum(pct1(pShare) + '%', spec('Share of taxpayers with incomes of £150,000 or more', pp, pt, 'taxpayers')),
            ' of income tax payers. They paid about ', U.derivedNum(pct1(lShare) + '%', spec('Share of income tax paid by people with incomes of £150,000 or more', lp, lt, 'income tax')), ' of all income tax.'],
          know: ['This is income tax only. National Insurance and VAT are separate, and VAT is paid by everyone who buys things. HMRC rounds these figures, so treat the shares as approximate.'],
          more: ['who-pays.html', 'See who pays income tax, band by band'],
        };
      },
    },
    {
      id: 'tax-sources', q: 'Where does the tax money come from?',
      async build() {
        const ids = ['hmrc_receipts.total', 'hmrc_receipts.income_tax', 'hmrc_receipts.nics', 'hmrc_receipts.vat', 'hmrc_receipts.corporation_tax'];
        const d = await load(ids);
        const y = commonYear(ids.map((i) => d[i]));
        const t = nom(d[ids[0]], y);
        const part = (i, label) => ({ label, p: nom(d[i], y) });
        const items = [part(ids[1], 'income tax'), part(ids[2], 'National Insurance'), part(ids[3], 'VAT'), part(ids[4], 'company profits tax (corporation tax)')];
        items.forEach((it) => track(it.label + ', ' + y, it.p));
        const list = [];
        items.forEach((it, k) => { list.push(per100(cap(it.label), y, it.p, t, 'tax collected by HMRC'), ' from ' + it.label + (k < items.length - 2 ? ', ' : (k === items.length - 2 ? ' and ' : '.'))); });
        return {
          answer: ['In ' + y + ', HMRC collected about ', money(t, 'Tax collected by HMRC, ' + y), '. Out of every £100: about ', ...list],
          know: ['The rest comes from many smaller taxes, such as fuel and alcohol duties and stamp duty. These are taxes HMRC collects; council tax and business rates are collected by councils, so they are not in these figures.'],
          more: ['revenue.html', 'See every tax'],
        };
      },
    },
    {
      id: 'asylum-cost', q: 'How much does the asylum system cost?',
      async build() {
        const d = await load(['home_office_spend.resource_del.asylum_support_resettlement_accommodation', 'pesa_uk.tme']);
        const a = d['home_office_spend.resource_del.asylum_support_resettlement_accommodation']; const t = d['pesa_uk.tme'];
        const y = commonYear([a, t]);
        const ap = nom(a, y); const tp = nom(t, y);
        track('Asylum support, resettlement and accommodation, ' + y, ap);
        return {
          answer: ['In ' + y + ', the Home Office spent about ', money(ap, 'Asylum support, resettlement and accommodation, ' + y), ' on asylum support, resettlement and accommodation. That is about ',
            per100('Asylum support, resettlement and accommodation', y, ap, tp, 'total government spending'), ' of every £100 the government spent.'],
          know: ['This is the Home Office only. Other departments have costs too, and there is no single official total that covers everything. Money collected from visa fees is a separate figure that we do not show yet. The asylum page has the people, the other departments and the gaps.'],
          more: ['immigration.html', 'See the full picture on immigration and money'],
        };
      },
    },
    {
      id: 'biggest-benefits', q: 'Which benefits cost the most?',
      async build() {
        const bx = await U.getJSON('benefits/index.json');
        const rows = (bx.benefits || []).filter((b) => b.headline && b.headline.spend && b.headline.share_of_welfare)
          .sort((a, b) => b.headline.spend.value - a.headline.spend.value).slice(0, 3);
        if (rows.length < 3) throw new Error('not enough benefits');
        const y = rows[0].headline.fiscal_year;
        rows.forEach((r) => track(r.name + ', ' + y, r.headline.spend));
        const list = [];
        rows.forEach((r, k) => {
          list.push(r.name + ' (about ', money(r.headline.spend, r.name + ' cost, ' + y), ', ', U.num(r.headline.share_of_welfare, { label: r.name + ' share of welfare, ' + y, badge: false }), ' of all welfare)', k < rows.length - 2 ? ', ' : (k === rows.length - 2 ? ' and ' : '.'));
        });
        return {
          answer: ['In ' + y + ', the three biggest were ', ...list],
          know: ['Costs are for the whole year, for the whole country, and include everyone who gets the benefit. A benefit that costs a lot can be a small payment to a very large number of people. Each benefit page shows both.'],
          more: ['benefits.html', 'See every benefit'],
        };
      },
    },
  ];

  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

  const host = $('#questions');
  U.clear(host);
  const built = [];
  for (const spec of QUESTIONS) {
    let out = null;
    try { out = await spec.build(); } catch (e) { out = null; }
    if (!out) continue;
    built.push(spec.id);
    const know = [].concat(...out.know.map((k) => (Array.isArray(k) ? k : [k])));
    host.appendChild(h('article', { class: 'card faq', id: spec.id },
      h('h3', null, spec.q),
      h('p', { class: 'faq-answer' }, out.answer),
      h('p', { class: 'faq-know small' }, h('strong', null, 'Worth knowing: '), know),
      h('p', { class: 'small' }, h('a', { href: out.more[0] }, out.more[1] + ' →'))));
  }
  if (!built.length) host.appendChild(U.gapBox('We don’t show these answers yet: the official figures aren’t published in a form we can trace.'));

  U.setSummary(['People share numbers about public money without the year, the area or what is counted. These answers use only official figures, and every number opens its source.'],
    'Last updated ' + U.updatedText(ix), checkFigures.length ? checkFigures[0].point : null);

  /* ---------- how big is that number ---------- */
  const scaleHost = $('#scale');
  try {
    const d = await load(['pesa_uk.tme', 'ons_population.uk']);
    const y = commonYear([d['pesa_uk.tme'], d['ons_population.uk']].map((s) => ({ variants: { nominal: s.variants.nominal } })));
    const tme = nom(d['pesa_uk.tme'], y); const pop = nom(d['ons_population.uk'], y);
    track('Total government spending, ' + y, tme); track('Population of the UK, ' + y, pop);
    const out = h('div', { class: 'card' });
    const amount = h('input', { id: 'amt', type: 'number', min: '0', step: 'any', inputmode: 'decimal', value: '100' });
    const unit = h('select', { id: 'amt-unit' }, h('option', { value: '1e6' }, 'million'), h('option', { value: '1e9' }, 'billion'));
    function render() {
      const mult = +unit.value; const n = parseFloat(amount.value);
      U.clear(out);
      if (!isFinite(n) || n < 0) { out.appendChild(h('p', { class: 'small muted' }, 'Type an amount to compare.')); return; }
      const pounds = n * mult;
      const perPerson = pounds / pop.value;
      const of100 = (pounds / (tme.value * 1e9)) * 100;
      if (of100 > 100) { out.appendChild(h('p', { class: 'small muted' }, 'That is more than a whole year of government spending.')); return; }
      const pp = perPerson >= 10 ? U.perPersonText(perPerson) : '£' + perPerson.toFixed(2);
      const shareText = of100 >= 0.995 ? 'about ' + U.per100Text(of100) + ' in every £100' : (of100 * 100 >= 1 ? 'about ' + (of100 * 100).toFixed(of100 * 100 < 10 ? 1 : 0) + 'p in every £100' : 'less than 1p in every £100');
      out.appendChild(h('p', { class: 'faq-answer' }, '£' + n.toLocaleString('en-GB') + ' ' + (mult === 1e6 ? 'million' : 'billion') + ' is about ',
        h('strong', null, pp), ' for each person in the UK. That is ', h('strong', null, shareText), ' of what the government spends in a year.'));
      out.appendChild(h('p', { class: 'small muted' }, 'Worked out from the UK population in ' + y + ' (', U.num(pop, { label: 'UK population, ' + y, badge: false }),
        ') and total government spending in ' + y + ' (', U.num(tme, { label: 'Total government spending, ' + y, badge: false }), '). A one-off amount is compared with one year of spending.'));
    }
    amount.addEventListener('input', render); unit.addEventListener('change', render);
    U.clear(scaleHost).appendChild(h('div', { class: 'grid grid-2' },
      h('div', { class: 'card' }, h('div', { class: 'field' }, h('label', { for: 'amt' }, 'Amount in the post (£)'), amount),
        h('div', { class: 'field' }, h('label', { for: 'amt-unit' }, 'In'), unit)), out));
    render();
  } catch (e) {
    U.state(scaleHost, 'We don’t show this comparison yet: the official figures aren’t available.');
  }

  /* ---------- five questions ---------- */
  const TIPS = [
    ['Which year is it?', 'A number from 2019 and one from 2025 are not the same thing. Posts often leave the year out.'],
    ['Is it for one year or several?', 'A bill added up over five years sounds five times bigger than the yearly cost.'],
    ['Who is it for?', 'Pounds for the whole country, for each person and for each household are very different sizes.'],
    ['What is counted?', 'A total can include pensions or leave them out, and can cover the UK, Great Britain or only England.'],
    ['Is it spent, or only planned?', 'Forecasts and plans are guesses about the future. Actual figures are what happened.'],
  ];
  const tips = $('#tips');
  TIPS.forEach(([t, d]) => tips.appendChild(h('li', null, h('strong', null, t), ' ', d)));
  tips.insertAdjacentElement('afterend', h('p', { class: 'small' }, 'Still unsure? ', link('claims.html', 'Look up the official number'), ' or ', link('reconciliation.html', 'see why totals differ'), '.'));

  U.mountCheckers({
    figures: checkFigures.filter((f, k, a) => a.findIndex((g) => g.point.provenance_id === f.point.provenance_id) === k),
    recon: 'all',
    method: ['Every answer is built from the published series in api/v1. The words “more” and “less” are chosen by the page from the numbers, so they follow the data when it is revised.',
      'Shares and “out of every £100” figures are worked out on the page from two published numbers; tap one to see both inputs.',
      'Where two official totals for the same thing exist (for example welfare), the page names the one it uses and links to the comparison.'],
  });
});
