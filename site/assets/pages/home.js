/* Home: "£1 of your tax: where it goes". A story in bands: one big number, where each £100 goes,
   the biggest parts, debt interest, how it is paid for, which "welfare", and how to check any number.
   Every figure comes from the API; anything we compute on the page says how it was worked out. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const ix = await U.index();
  const latest = ix.fiscal_years && ix.fiscal_years.latest_outturn;
  const data = await U.seriesMany(['obr.psf.tme', 'obr.psf.receipts']);
  const tmeS = data['obr.psf.tme']; const recS = data['obr.psf.receipts'];
  const tmeP = tmeS && U.pointFor(tmeS, 'nominal', latest);
  const recP = recS && U.pointFor(recS, 'nominal', latest);
  let covered = null;
  if (tmeP && recP && tmeP.vintage === recP.vintage && tmeP.value > 0) covered = (recP.value / tmeP.value) * 100;
  const coveredSpec = covered == null ? null : {
    title: 'Income compared with spending', text: 'All government income divided by all government spending, ' + latest + ', as spent at the time.', formula: 'Income ÷ spending × 100',
    inputs: [{ label: 'All government income ' + latest, id: recP.provenance_id, value: U.fmt(recP.value, recP.unit) }, { label: 'All government spending ' + latest, id: tmeP.provenance_id, value: U.fmt(tmeP.value, tmeP.unit) }],
  };

  /* --- summary + hero: one big number that follows the "Show amounts" toggle --- */
  const hero = $('#tiles');
  function renderHero() {
    U.clear(hero);
    if (!tmeS) { U.state(hero, 'We don’t show total government spending yet: the official figures aren’t published in a form we can trace.'); return; }
    const vf = U.variantFor(tmeS);
    const pt = U.pointFor(tmeS, vf.variant, latest);
    if (!pt) { U.state(hero, 'We don’t show total government spending for ' + latest + ' yet.'); return; }
    const pct = vf.variant === 'pct_gdp';
    hero.appendChild(h('p', { class: 'hero-kicker' }, 'In ' + latest + ' (April to March), the UK government spent'));
    hero.appendChild(h('div', { class: 'hero-num' }, U.num(pt, { label: 'All government spending ' + latest, badge: false })));
    if (pct) hero.appendChild(h('p', { class: 'hero-says' }, 'of everything the UK produces in a year (', U.term('gdp', 'GDP'), ').'));
    hero.appendChild(h('p', { class: 'meta' }, latest, ' · UK · ', pt.status === 'forecast' ? 'Forecast' : 'Actual', ' · ', U.basisShort(vf.variant), ' · ', pt.vintage, ' · ',
      h('a', { class: 'num-check', href: U.checkHref(pt.provenance_id) }, 'Check this number')));
    if (vf.fallback) hero.appendChild(h('p', { class: 'small muted' }, vf.fallback));
    const ladder = h('ul', { class: 'ladder' });
    const pp = U.perHead(tmeS, 'per_person', latest);
    if (pp) {
      ladder.appendChild(h('li', null, h('span', { class: 'lab' }, 'For every person in the UK'),
        h('span', { class: 'big' }, U.num(pp, { label: 'All government spending per person ' + latest, badge: false })),
        h('a', { class: 'num-check', href: U.checkHref(pp.provenance_id) }, 'Check this number')));
    }
    const cash = pct ? tmeP : pt;
    if (cash && /^GBP_bn/.test(cash.unit)) {
      ladder.appendChild(h('li', null, h('span', { class: 'lab' }, 'Every day of the year'),
        h('span', { class: 'big' }, U.derivedNum(U.moneyWords(cash.value / 365), { title: 'Spending per day', text: 'The year’s total divided by 365 days' + (pct ? ', as spent at the time.' : '.'), formula: 'Total ÷ 365',
          inputs: [{ label: 'All government spending ' + latest, id: cash.provenance_id, value: U.fmt(cash.value, cash.unit) }] }))));
    }
    if (recS) {
      const rv = U.pointFor(recS, vf.variant, latest) || recP;
      if (rv) {
        ladder.appendChild(h('li', null, h('span', { class: 'lab' }, 'Money it took in (all income)'),
          h('span', { class: 'big' }, U.num(rv, { label: 'All government income ' + latest, badge: false })),
          h('a', { class: 'num-check', href: U.checkHref(rv.provenance_id) }, 'Check this number')));
      }
    }
    hero.appendChild(ladder);
  }
  function renderSummary() {
    if (!tmeS || !tmeP) { U.setSummary(['We don’t show total government spending yet: the official figures aren’t published in a form we can trace.'], 'Last updated ' + U.updatedText(ix)); return; }
    const parts = ['The government spent more than it took in. '];
    if (covered != null) parts.push('Income covered about ', U.derivedNum('£' + Math.round(covered), coveredSpec), ' of every £100 it spent in ' + latest + '; the rest was borrowed.');
    U.setSummary(parts, U.metaLine(tmeP, ix, U.basis));
  }
  renderHero(); renderSummary();
  U.onBasis(() => { renderHero(); renderSummary(); });

  /* --- the story bands --- */
  const story = $('#story');
  U.clear(story);
  let shares = null;
  try { shares = await U.getJSON('shares.json'); } catch (e) { shares = null; }
  const setOf = (id) => shares && (shares.sets || []).find((x) => x.id === id && x.available);
  const sp = setOf('spending_uk');
  const rv = setOf('revenue_hmrc');
  const band = (id, kicker, title, text, visual, cls) => h('section', { class: 'band' + (cls ? ' ' + cls : ''), 'aria-labelledby': id },
    h('div', { class: 'band-text' }, kicker ? h('p', { class: 'kicker' }, kicker) : null, h('h2', { id }, title), text),
    visual ? h('div', { class: 'band-visual' }, visual) : null);

  /* Band 2: where each £100 goes (one grid, the whole £100) */
  if (sp) {
    const items = sp.parts.map((p) => ({ sid: p.series_id, label: U.cap1(U.areaName(p.series_id, p.title)), fullLabel: U.cap1(U.areaName(p.series_id, p.title)) + ', ' + sp.fiscal_year, value: p.per_100.value, point: p.per_100, part: p }));
    if (sp.other && sp.other.value >= 0.05) items.push({ label: U.cap1(sp.other_label || 'other'), value: sp.other.value, point: sp.other, rest: true });
    items.sort((a, b) => (Number(!!a.rest) - Number(!!b.rest)) || (b.value - a.value));
    const split = U.splitOf100(items);
    const top = split.slice(0, 4);
    const restSum = 100 - top.reduce((a, r) => a + r.int, 0);
    const status = items.some((i) => i.point && i.point.status === 'forecast') ? 'mixed' : 'actual';
    const blocks = top.map((r, k) => ({ label: r.label, short: r.label.length > 26 ? r.label.split(/,| and /)[0] : r.label, n: r.int, tone: k + 1 }));
    blocks.push({ label: 'Everything else', n: restSum, tone: 'rest' });
    const tb = split.map((r) => [r.label, r.valueNode]);
    const grid = U.partitionGrid({
      title: 'Where each £100 of spending on public services went, ' + sp.fiscal_year, blocks,
      scope: U.scopeChip(sp.fiscal_year, 'UK', status),
      caption: 'Each square is £1 of every £100 spent on public services.',
      source: 'Source: HM Treasury, ' + (sp.edition || 'Public Expenditure Statistical Analyses') + '. Whole pounds, adding up to £100.',
      table: U.tableView('Out of every £100 spent on public services, ' + sp.fiscal_year, ['Area', 'Out of every £100'], tb),
    });
    const first = top[0];
    story.appendChild(band('b-where', 'Where it goes', 'Out of every £100, where does it go?', [
      h('p', null, 'Out of every £100 spent on public services across the UK in ' + sp.fiscal_year + ', ',
        first ? [h('strong', null, first.text), ' went on ' + first.label.toLowerCase() + ' – the biggest part by far.'] : ''),
      h('p', { class: 'small muted' }, 'This is spending on services. Interest on debt is shown further down. ', h('a', { href: 'spending.html' }, 'See every area and every year'), '.')], grid));

    /* Band 3: the three biggest parts, as 100 squares with a bracket */
    const trio = h('div', { class: 'trio' });
    split.filter((r) => r.part).slice(0, 3).forEach((r) => {
      const key = String(r.sid || '').split('.').pop();
      const pp = r.part.per_person;
      trio.appendChild(h('div', null,
        U.squares({ on: r.int, bracket: r.text, size: 'lg', title: r.label + ': ' + r.text + ' out of every £100', caption: r.label, keyOn: r.text + ' of every £100', keyOff: false }),
        U.AREA_BLURB[key] ? h('p', { class: 'blurb' }, U.AREA_BLURB[key]) : null,
        pp ? h('p', { class: 'small muted' }, 'About ', U.num(pp, { label: r.label + ' per person ' + sp.fiscal_year, badge: false }), ' for every person, as spent at the time.') : null,
        key === 'social_protection' ? h('p', { class: 'small' }, h('a', { href: 'benefits.html' }, 'Benefits explained →')) : null));
    });
    story.appendChild(band('b-big', 'The biggest parts', 'The three biggest parts', [
      h('p', null, 'Each grid is £100. The filled squares are the part that went on each area.')], trio, 'wide'));

    /* Band 4: the rest, as bars (smaller areas, then everything else in grey) */
    const rest = split.slice(3);
    if (rest.length) {
      const rows = rest.map((r) => Object.assign({}, r, { label: r.label }));
      story.appendChild(band('b-rest', null, 'And the rest', [h('p', null, 'The other areas, out of every £100. Click any amount to see where it came from.')],
        U.barList(rows, { max: Math.max(...split.map((r) => r.barValue)), unitHead: 'Out of every £100' })));
    }
  } else {
    story.appendChild(band('b-where', null, 'Out of every £100, where does it go?', h('p', null, 'We don’t show this yet: the official figures aren’t published in a form we can trace.'), U.gapBox()));
  }

  /* Band 5: interest on debt (ONS, central government) */
  const DEBT = 'ons_psf.cg_debt_interest';
  const debt = (await U.seriesMany([DEBT]))[DEBT];
  const debtVisual = h('div');
  const debtText = h('div');
  function renderDebt() {
    U.clear(debtVisual); U.clear(debtText);
    if (!debt) { debtVisual.appendChild(U.gapBox('We don’t show interest on debt yet: the official figures aren’t published in a form we can trace.')); return; }
    const dy = (ix.debt_interest && ix.debt_interest.latest_outturn) || latest;
    const vf = U.variantFor(debt);
    const pt = U.pointFor(debt, vf.variant, dy);
    const p100 = U.pointFor(debt, 'per_100', dy);
    const pp = U.perHead(debt, 'per_person', dy);
    debtText.appendChild(h('p', null, 'The government has borrowed over many years. Like any borrower, it pays ', U.term('debt-interest', 'interest'), '. In ' + dy + ' that was ',
      U.num(pt, { label: 'Interest on government debt ' + dy, missing: 'not published', badge: false }), '.'));
    if (p100) debtText.appendChild(h('p', null, 'Out of every £100 the central government took in, about ', h('strong', null, U.num(p100, { label: 'Debt interest out of every £100 of income ' + dy, badge: false })), ' went on interest.'));
    if (pp) debtText.appendChild(h('p', { class: 'small muted' }, 'About ', U.num(pp, { label: 'Debt interest per person ' + dy, badge: false }), ' for every person in the UK.'));
    debtText.appendChild(h('p', { class: 'small muted' }, 'Central government only, as the Office for National Statistics counts it.'));
    if (vf.fallback) debtText.appendChild(h('p', { class: 'small muted' }, vf.fallback));
    const pts = vf.points.slice().sort((a, b) => a.fiscal_year.localeCompare(b.fiscal_year));
    if (pts.length > 1) {
      /* Callout on the biggest one-year rise, only if it is large (over 10%). */
      let best = null;
      for (let i = 1; i < pts.length; i += 1) {
        const a = pts[i - 1]; const b = pts[i];
        if (a.value > 0 && b.status !== 'forecast' && (b.value - a.value) / a.value > 0.1 && (!best || b.value - a.value > best.d)) best = { y: b.fiscal_year, d: b.value - a.value, a, b };
      }
      const annotations = [];
      if (best && vf.variant !== 'pct_gdp') annotations.push({ year: best.y, text: 'Up ' + U.moneyWords(best.d) + ' in one year' });
      else if (best) annotations.push({ year: best.y, text: 'Biggest one-year rise' });
      debtVisual.appendChild(U.lineChart({
        title: 'Interest on government debt', points: pts, gaps: debt.gaps, annotations,
        scope: U.scopeChip(pts[0].fiscal_year + ' to ' + pts[pts.length - 1].fiscal_year, 'UK central government', pts.some((p) => p.status === 'forecast') ? 'mixed' : 'actual'),
        caption: 'Interest paid each year. ' + U.basisCaption(vf.variant, ix) + '.',
        source: 'Source: Office for National Statistics, public sector finances.', ser: debt,
        tableCaption: 'Interest on government debt (' + U.basisCaption(vf.variant, ix) + ')',
      }));
    }
  }
  renderDebt();
  U.onBasis(renderDebt);
  story.appendChild(band('b-debt', 'Interest', 'What about interest on debt?', debtText, debtVisual));

  /* Band 6: how it is paid for — borrowing squares, then where tax comes from */
  const payVisual = h('div', { class: 'band-visual' });
  if (covered != null) {
    const on = Math.round(covered); const bor = 100 - on;
    payVisual.appendChild(U.squares({ on, hatch: bor, size: 'lg', bracket: '£' + on, bracketHatch: bor > 0 ? '£' + bor : null,
      title: 'Of every £100 spent in ' + latest + ', about £' + on + ' was covered by income and £' + bor + ' was borrowed',
      scope: U.scopeChip(latest, 'UK', tmeP.status === 'forecast' ? 'forecast' : 'actual'),
      caption: 'Every £100 the government spent in ' + latest,
      keyOn: 'Paid for by income (£' + on + ')', keyHatch: 'Hatched squares: borrowed (£' + bor + ')', keyOff: false,
      source: 'Source: Office for Budget Responsibility, Public Finances Databank.' }));
  }
  if (rv) {
    const items = rv.parts.map((p) => {
      let label = U.cap1(U.areaName(p.series_id, p.title.replace(/^HMRC tax and NICs receipts for the UK:\s*/, '')));
      label = label.replace(/^Nics$/i, 'National Insurance').replace(/^Vat$/i, 'VAT').replace(/^Sdlt$/i, 'Stamp duty on property');
      return { label, value: p.per_100.value, point: p.per_100 };
    });
    items.sort((a, b) => b.value - a.value);
    if (rv.other) items.push({ label: 'Everything else', value: rv.other.value, point: rv.other, rest: true });
    const split = U.splitOf100(items);
    const top = split.filter((r) => !r.rest).slice(0, 4);
    const restN = 100 - top.reduce((a, r) => a + r.int, 0);
    const parts = top.map((r, k) => ({ label: r.label, n: r.int, tone: k + 1 })).concat([{ label: 'Everything else', n: restN, tone: 'rest' }]);
    payVisual.appendChild(h('figure', { class: 'card chart-fig' },
      h('figcaption', null, U.scopeChip(rv.fiscal_year, 'UK', 'actual'), h('p', { class: 'caption-text' }, 'Where each £100 of tax collected by HMRC came from')),
      U.stackStrip({ title: 'Where each £100 of tax collected by HMRC came from, ' + rv.fiscal_year, parts }),
      h('p', { class: 'small muted' }, 'Source: HM Revenue and Customs. ', h('a', { href: 'revenue.html' }, 'See every tax'), '.'),
      U.tableView('Out of every £100 of tax collected by HMRC, ' + rv.fiscal_year, ['Tax', 'Out of every £100'], split.map((r) => [r.label, r.valueNode]))));
  }
  story.appendChild(band('b-pay', 'Paying for it', 'How is it paid for?', [
    covered != null ? h('p', null, 'Most of it is paid for by taxes and other income. In ' + latest + ', income covered about ', U.derivedNum('£' + Math.round(covered), coveredSpec),
      ' of every £100 spent. The rest was borrowed – this gap is called the ', U.term('deficit', 'deficit'), '.') : h('p', null, 'We can’t compare income with spending for ' + latest + ' yet.'),
    rv ? h('p', null, 'Most tax comes from income tax, National Insurance and VAT.') : null], payVisual));

  /* Band 7: which welfare? Three real totals on one scale. */
  const wHost = h('div');
  const WY = '2024-25';
  async function renderWelfare() { const node = await U.welfareRuler(WY); U.clear(wHost).appendChild(node); }
  await renderWelfare();
  U.onBasis(renderWelfare);
  story.appendChild(band('b-welfare', 'Welfare', '“Welfare costs…” Which welfare?', [
    h('p', null, 'You may hear very different totals for ', U.term('welfare', 'welfare'), '. They count different things, so each can be right. The bigger the total, the more it includes.'),
    h('p', { class: 'small' }, h('a', { href: 'benefits.html#totals' }, 'Why the welfare totals differ'), ' · ', h('a', { href: 'reconciliation.html' }, 'How the sources compare'))], wHost));

  /* Band 8: worked example — one number traced to its file, sheet and cell */
  const traceHost = h('div', null, h('p', { class: 'state', role: 'status' }, 'Loading the example…'));
  story.appendChild(band('b-check', 'Check it yourself', 'Check any number', [
    h('p', null, 'Every number here is a button. Click one to see where it came from, then follow the link to the exact file, sheet and cell.'),
    tmeP ? h('p', null, 'Try it: ', U.num(tmeP, { label: 'All government spending ' + latest, badge: false })) : null], traceHost));
  async function renderTrace() {
    try {
      const rec = await U.prov(tmeP.provenance_id);
      const c = rec.check || {};
      const box = (k1, v1, k2, v2, extra) => h('li', { class: 'card' }, h('span', { class: 'k' }, k1), h('span', { class: 'v' }, v1), k2 ? [h('span', { class: 'k' }, k2), h('span', { class: 'v' }, v2)] : null, extra || null);
      U.clear(traceHost).appendChild(h('ol', { class: 'trace' },
        box('Who published it', rec.publisher, 'Which file', (rec.dataset || '') + (rec.vintage ? ', ' + rec.vintage : '')),
        box('Where in the file', 'Sheet “' + (c.sheet || rec.sheet || '?') + '”', 'Cell', c.cell || rec.cell_or_range || '?'),
        box('What it says there', c.published_value != null ? c.published_value.toLocaleString('en-GB') + (/^GBP_bn/.test(c.published_unit || '') ? ' (£ billion)' : '') : U.fmt(tmeP.value, tmeP.unit), 'What we show', U.fmt(tmeP.value, tmeP.unit),
          h('a', { href: U.checkHref(tmeP.provenance_id) }, 'Follow the steps'))));
    } catch (e) {
      U.clear(traceHost).appendChild(U.gapBox('We could not load the example just now.'));
    }
  }
  /* The provenance file is large (about 2 MB): fetch it only when the example scrolls near the screen. */
  if (!tmeP) U.clear(traceHost);
  else if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { io.disconnect(); renderTrace(); } }, { rootMargin: '400px' });
    io.observe(traceHost);
  } else renderTrace();

  U.mountCheckers({
    intro: 'Cross-checks, sources and exact cells for the numbers on this page.',
    figures: [
      { label: 'All government spending, ' + latest, point: tmeP },
      { label: 'All government income, ' + latest, point: recP },
    ],
    recon: 'all',
    method: ['All government spending is total managed expenditure (TME) and all government income is public sector current receipts, both from the OBR Public Finances Databank. “Every day” is the year’s total divided by 365.',
      'The split of £100 uses Table 5.2 of HM Treasury’s PESA (UK-wide, by COFOG function) and the HMRC receipts table. Whole pounds use the largest-remainder method so they add up to exactly £100.',
      'Debt interest is central government interest from the ONS public sector finances. “Out of every £100” for debt interest is out of the central government’s income that year.',
      'The three welfare totals are DWP total benefit expenditure (Great Britain), the UK welfare total from the DWP tables, and social protection from PESA. They are all for ' + WY + '.',
      'Per-person amounts divide by the ONS population estimate for the same year. Per-household amounts divide by the ONS household count, which only covers ' + U.perHousehold(ix).first + ' to ' + U.perHousehold(ix).last + '.'],
  });
});
