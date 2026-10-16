/* One benefit, from benefits/<slug>.json, chosen by ?b=<slug>. Same block order for every benefit. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;

  /* Plain-English words only. No figures here: every number comes from the data. */
  const INFO = {
    'attendance-allowance': { what: 'A payment to help with extra costs of illness or disability for people over State Pension age. It is not means-tested.', who: ['People over State Pension age', 'People with a long-term illness or disability who need help with personal care or supervision'], gov: 'https://www.gov.uk/attendance-allowance' },
    'bereavement-benefits': { what: 'Payments to people whose husband, wife or civil partner has died. Newer claims are paid as Bereavement Support Payment. The older benefits are paid to fewer people each year.', who: ['People whose husband, wife or civil partner has died', 'Based on National Insurance contributions made by the person who died'], gov: null },
    'carers-allowance': { what: 'A weekly payment for people who spend a lot of time caring for someone with a disability. It is not means-tested, but there is a limit on how much a carer can earn.', who: ['People who care for someone for at least 35 hours a week', 'The person cared for must get a qualifying disability benefit', 'People whose earnings are under a set weekly limit'], gov: 'https://www.gov.uk/carers-allowance' },
    'disability-living-allowance': { what: 'A payment towards the extra costs of disability. It is being replaced by Personal Independence Payment for most adults, so it now goes mainly to children and some older claimants. It is not means-tested.', who: ['Children with care or mobility needs', 'Some adults who were already claiming before Personal Independence Payment began'], gov: 'https://www.gov.uk/disability-living-allowance-benefit' },
    'employment-and-support-allowance': { what: 'Money for people who cannot work, or can only work a little, because of illness or disability. Some people get it based on National Insurance contributions and others get it because of low income.', who: ['People of working age with an illness or disability that limits work', 'Some people must meet a National Insurance contributions test, and others a low-income test'], gov: 'https://www.gov.uk/employment-support-allowance' },
    'housing-benefit': { what: 'Help with rent for people on low incomes. It is means-tested. Most working-age people now get this help through Universal Credit instead.', who: ['People on a low income who pay rent', 'Mostly people over State Pension age, and some people in supported housing'], gov: 'https://www.gov.uk/housing-benefit' },
    'industrial-injuries': { what: 'Payments to people who were disabled by an accident or illness caused by their work. It is not means-tested.', who: ['People disabled by an accident at work', 'People with a disease caused by the work they did'], gov: 'https://www.gov.uk/industrial-injuries-disablement-benefit' },
    'jobseekers-allowance': { what: 'Money for people who are out of work and looking for a job. Most new claims now go to Universal Credit, so fewer people get this each year.', who: ['People who are out of work and looking for a job', 'Some must have paid enough National Insurance, and others must have a low income'], gov: 'https://www.gov.uk/jobseekers-allowance' },
    'maternity-allowance': { what: 'A payment for working mothers who cannot get Statutory Maternity Pay, for example because they are self-employed.', who: ['Mothers-to-be who have worked recently but do not qualify for Statutory Maternity Pay', 'Some self-employed women'], gov: 'https://www.gov.uk/maternity-allowance' },
    'pension-credit': { what: 'Extra money for people over State Pension age who have a low income. It is means-tested.', who: ['People over State Pension age', 'People whose income is below a set level'], gov: 'https://www.gov.uk/pension-credit' },
    'personal-independence-payment': { what: 'A payment towards the extra costs of a long-term illness or disability for people of working age. It is not means-tested.', who: ['Adults with a long-term illness or disability', 'People who need help with daily living, with getting around, or both'], gov: 'https://www.gov.uk/pip' },
    'severe-disablement-allowance': { what: 'An older benefit for people who had been unable to work for a long time because of disability. It closed to new claims in 2001, so the number of people getting it falls each year.', who: ['People who were already claiming when it closed to new claims', 'No new claims are taken'], gov: null },
    'state-pension': { what: 'A regular payment from the government to people who have reached State Pension age. How much you get depends on your National Insurance record.', who: ['People who have reached State Pension age', 'Paid by how many years of National Insurance contributions or credits a person has'], gov: 'https://www.gov.uk/state-pension' },
    'statutory-maternity-pay': { what: 'Pay from an employer to an employee who is off work to have a baby. Employers get most of the cost back from the government.', who: ['Employees who are having a baby', 'People who have worked for their employer long enough and earn above a set level'], gov: 'https://www.gov.uk/maternity-pay-leave' },
    'universal-credit': { what: 'A monthly payment for people on a low income or out of work. It replaced six older benefits. It is means-tested.', who: ['People of working age who are out of work or on a low income', 'People with some savings under a set limit'], gov: 'https://www.gov.uk/universal-credit' },
    'winter-fuel-payments': { what: 'A yearly payment to help older people with heating bills in winter. Rules have changed in recent years, and it is now paid by different governments in different parts of the UK.', who: ['People over a set age, based on State Pension age', 'Rules differ by year and by where you live'], gov: 'https://www.gov.uk/winter-fuel-payment' },
  };

  const slug = (new URLSearchParams(location.search).get('b') || '').toLowerCase();
  const bx = await U.getJSON('benefits/index.json');
  const entry = (bx.benefits || []).find((b) => b.slug === slug);
  const body = $('#body');
  if (!entry) {
    $('#bname').textContent = 'Benefit not found';
    U.summaryState('We could not find that benefit.', 'error');
    body.appendChild(h('p', null, 'Please choose one from ', h('a', { href: 'benefits.html' }, 'the list of benefits'), '.'));
    return;
  }
  const [ix, d, total] = await Promise.all([U.index(), U.getJSON('benefits/' + slug + '.json'), U.series(bx.total_series_id).catch(() => null)]);
  const name = d.name;
  document.title = name + ' explained · UK Public Money';
  $('#bname').textContent = name;
  const info = INFO[slug] || null;
  const year = d.headline_year;
  const where = d.geography === 'GB' ? 'Great Britain' : 'the UK';
  /* Table 1c counts people only for "in payment" lines; the others count claims (cases), some of them credits-only. */
  const people = d.caseload_basis === 'in_payment';
  const creditsOnly = (d.notes || []).some((t) => /credits only/i.test(t));
  const at = (arr) => (arr || []).find((p) => p.fiscal_year === year) || null;
  const NOT_YET = 'Not published yet. See the sources in “For checkers”.';
  /* Other benefits, for the comparison bars (same year, same basis). */
  const others = (bx.benefits || []).filter((b) => b.headline && b.headline.spend).map((b) => (b.slug === slug ? d : U.benefitSlim(b)));

  /* ---- static blocks (do not depend on the price basis) ---- */
  const sumHost = $('#summary-body');
  const sections = {
    what: h('section', { 'aria-labelledby': 'what-h' }, h('h2', { id: 'what-h' }, 'What it is')),
    who: h('section', { 'aria-labelledby': 'who-h' }, h('h2', { id: 'who-h' }, 'Who gets it')),
    nums: h('section', { 'aria-labelledby': 'nums-h' }, h('h2', { id: 'nums-h' }, 'The numbers')),
    person: h('section', { 'aria-labelledby': 'person-h' }, h('h2', { id: 'person-h' }, 'What it means for each person')),
    trend: h('section', { 'aria-labelledby': 'trend-h' }, h('h2', { id: 'trend-h' }, 'How it has changed over ten years')),
    compare: h('section', { 'aria-labelledby': 'cmp-h' }, h('h2', { id: 'cmp-h' }, 'Compared with other benefits')),
  };
  Object.values(sections).forEach((s) => body.appendChild(s));

  if (info) {
    sections.what.appendChild(h('p', null, info.what));
    sections.what.appendChild(h('p', null, 'These figures cover ' + where + '. ', info.gov ? ['Official advice: ', U.ext(info.gov, 'GOV.UK page for ' + name), '.'] : null));
    sections.who.appendChild(h('ul', null, info.who.map((t) => h('li', null, t))));
  } else {
    sections.what.appendChild(U.gapBox('We have not written a plain-English description of this benefit yet.'));
    sections.who.appendChild(U.gapBox('We have not written a plain-English description of who gets this benefit yet.'));
  }

  /* ---- numbers that depend on the price basis ---- */
  const numsHost = h('div'); sections.nums.appendChild(numsHost);
  const personHost = h('div'); sections.person.appendChild(personHost);
  const trendHost = h('div'); sections.trend.appendChild(trendHost);
  const cmpHost = h('div'); sections.compare.appendChild(cmpHost);

  function tile(label, node, has, meta, status) {
    const t = h('div', { class: 'card tile' }, h('p', { class: 'label' }, label));
    t.appendChild(h('div', { class: 'hero-num' }, has ? node : h('span', { class: 'muted' }, 'Not published yet')));
    t.appendChild(h('p', { class: 'meta' }, has ? [meta, status === 'forecast' ? ' ' : null, status === 'forecast' ? U.badge('forecast') : null] : NOT_YET));
    return t;
  }
  function gapLines(field) {
    return (d.gaps || []).filter((g) => g.field === field);
  }

  function render() {
    const v = U.benefitView(d, year);
    const sp = v.spend; const claimants = v.claimants; const share = v.share;
    const real = () => v.mode === 'real';
    const when = year + (sp && sp.status === 'forecast' ? ' (forecast)' : '');
    /* summary */
    const nodes = [];
    if (claimants && sp) {
      nodes.push('In ' + year + ', about ', U.num(claimants, { label: 'People getting ' + name, badge: false }), (people ? ' people got ' + name : ' claims for ' + name + ' were open on average') + (creditsOnly ? ' (this includes cases that get National Insurance credits only)' : '') + '. It cost about ', U.num(sp, { label: name + ' cost', badge: false }), real() ? ', adjusted for rising prices.' : '.');
    } else if (sp) {
      nodes.push('In ' + year + ', ' + name + ' cost about ', U.num(sp, { label: name + ' cost', badge: false }), '. We don’t show how many ' + (people ? 'people' : 'claims') + ' there were.');
    } else {
      nodes.push('We don’t show the cost of ' + name + ' yet: the official figures aren’t published in a form we can trace.');
    }
    U.setSummary(nodes, U.metaLine(sp, ix, v.mode), sp);

    /* four headline numbers, all on the same basis */
    U.clear(numsHost);
    if (v.pctNote) numsHost.appendChild(U.note('warn', v.pctNote));
    const tiles = h('div', { class: 'btiles' });
    tiles.appendChild(tile('Total cost', v.spendNode, !!sp, 'In ' + when + ', ' + v.basisWords, sp && sp.status));
    tiles.appendChild(tile(people ? 'People getting it' : 'Claims', claimants ? U.num(claimants, { label: name + ': people getting it, ' + year, badge: false }) : null, !!claimants,
      'Yearly average in ' + when + (people ? ', people being paid' : ', all cases' + (creditsOnly ? ', including credits-only cases' : '')), claimants && claimants.status));
    tiles.appendChild(tile('Cost for each person getting it', v.perClaimant.node, !!v.perClaimant.point, 'A year, in ' + when + ', ' + v.basisWords, v.perClaimant.point && v.perClaimant.point.status));
    tiles.appendChild(tile('Share of benefit spending', share ? U.num(share, { text: U.per100Text(share.value), label: name + ': share of benefit spending, ' + year, badge: false }) : null, !!share,
      'Out of every £100 of DWP benefit spending in ' + where + ', ' + when + ' (the same however amounts are shown)', share && share.status));
    numsHost.appendChild(tiles);
    const missing = ['cost_per_claimant', 'share_of_welfare'].flatMap(gapLines);
    if (missing.length) numsHost.appendChild(h('details', { class: 'gaps-note small' }, h('summary', null, 'Some figures are missing. Why?'), h('ul', { class: 'notes-list' }, missing.map((g) => h('li', null, g.fiscal_year + ': ' + g.reason)))));
    numsHost.appendChild(h('p', { class: 'small muted' }, (people ? 'The number of people getting a benefit' : 'The number of claims') + ' is called the ', U.term('caseload', 'caseload'), '.'));

    /* per-person framing */
    U.clear(personHost);
    const lines = [];
    if (v.perClaimant.point) lines.push(h('p', null, 'In ' + year + ', the cost was about ', U.benefitView(d, year).perClaimant.node, (people ? ' a year for each person getting it.' : ' a year for each claim.')));
    if (v.perPerson.point) lines.push(h('p', null, 'Spread across everyone living in ' + where + ', that is about ', U.benefitView(d, year).perPerson.node, ' for each person in the country, whether or not they get it.'));
    if (!lines.length) lines.push(U.gapBox('We don’t show a per-person figure for this benefit yet: the official figures aren’t published in a form we can trace.'));
    lines.forEach((l) => personHost.appendChild(l));

    /* compared with other benefits: the biggest 8, plus this one if it is not among them */
    U.clear(cmpHost);
    const vs = others.map((o) => ({ o, w: U.benefitView(o, year) })).filter((x) => x.w.spend).sort((a, b) => b.w.spend.value - a.w.spend.value);
    let shown = vs.slice(0, 8);
    if (!shown.some((x) => x.o.slug === slug)) { const me = vs.find((x) => x.o.slug === slug); if (me) shown = shown.concat([me]); }
    if (shown.length > 1) {
      cmpHost.appendChild(U.scopeChip(year, 'Great Britain', shown.some((x) => x.w.spend.status === 'forecast') ? 'mixed' : 'actual'));
      cmpHost.appendChild(U.barList(shown.map((x) => ({ label: x.o.name, href: x.o.slug === slug ? null : 'benefit.html?b=' + encodeURIComponent(x.o.slug), current: x.o.slug === slug,
        barValue: x.w.spend.value, forecast: x.w.spend.status === 'forecast', muted: x.o.slug !== slug, valueNode: x.w.spendNode })), { unitHead: 'Total cost in ' + year + ', ' + v.basisWords }));
      cmpHost.appendChild(h('p', { class: 'small' }, h('a', { href: 'benefits.html' }, 'See every benefit')));
    }

    /* ten-year trend */
    U.clear(trendHost);
    const all = real() && d.spend_real && d.spend_real.length ? d.spend_real : d.spend;
    const lastActual = [...(all || [])].reverse().find((p) => p.status !== 'forecast' && p.fiscal_year <= year);
    const startIdx = Math.max(0, all.findIndex((p) => p.fiscal_year === year) - 9);
    const pts = (all || []).slice(startIdx);
    const outturn = pts.filter((p) => p.status !== 'forecast');
    if (pts.length < 2) {
      trendHost.appendChild(U.gapBox());
    } else {
      const f = outturn[0] || pts[0]; const l = outturn[outturn.length - 1] || pts[pts.length - 1];
      const diff = l.value - f.value;
      const verb = Math.abs(diff) < 0.05 * Math.max(Math.abs(f.value), 1e-9) ? 'stayed about the same, at about ' + U.moneyWords(l.value)
        : (diff > 0 ? 'risen from about ' + U.moneyWords(f.value) + ' in ' + f.fiscal_year + ' to about ' + U.moneyWords(l.value) : 'fallen from about ' + U.moneyWords(f.value) + ' in ' + f.fiscal_year + ' to about ' + U.moneyWords(l.value));
      const cap = 'The cost of ' + name + ' has ' + verb + (verb.startsWith('stayed') ? ' in ' + l.fiscal_year : ' in ' + l.fiscal_year) + (real() ? ', after adjusting for rising prices.' : ', as spent at the time.') + (pts.some((p) => p.status === 'forecast') ? ' Dashed years are forecasts.' : '');
      const sg = (d.gaps || []).filter((g) => g.field === 'spend' || g.field === 'spend_real');
      trendHost.appendChild(U.lineChart({
        title: name + ': total cost each year', heading: 'Total cost each year', caption: cap, fcLabel: 'Forecast by DWP',
        annotations: lastActual ? [{ year: lastActual.fiscal_year, text: U.moneyWords(lastActual.value) + ' in ' + lastActual.fiscal_year }] : [],
        sub: 'Source: Department for Work and Pensions, ' + d.edition + '.', points: pts, gaps: sg,
        ser: { id: d.spend_series_id, title: name + ' total cost', gaps: sg }, tableCaption: name + ': total cost each year',
      }));
      const cl = (d.claimants || []).slice(Math.max(0, d.claimants.findIndex((p) => p.fiscal_year === year) - 9));
      if (cl.length >= 2) {
        trendHost.appendChild(U.lineChart({
          title: name + ': people getting it each year', heading: 'People getting it each year',
          caption: 'The yearly average number of people getting ' + name + ', from ' + cl[0].fiscal_year + ' to ' + cl[cl.length - 1].fiscal_year + '.',
          sub: 'Source: Department for Work and Pensions, ' + d.edition + '.', points: cl, gaps: (d.gaps || []).filter((g) => g.field === 'claimants'),
          ser: { id: d.caseload_series_id, title: name + ' people getting it', gaps: [] }, tableCaption: name + ': people getting it each year', axisTitle: 'People (thousands)', fcLabel: 'Forecast by DWP',
        }));
      }
    }
  }
  render();
  U.onBasis(render);

  /* ---- For checkers ---- */
  const shareOf = at(d.share_of_welfare) && total ? U.pointFor(total, 'nominal', year) : null;
  U.mountCheckers({
    figures: [
      { label: name + ' total cost, ' + year + ' (as spent at the time)', point: at(d.spend) },
      { label: name + ' total cost, ' + year + ' (adjusted for rising prices)', point: at(d.spend_real) },
      { label: name + ' people getting it, ' + year, point: at(d.claimants) },
      { label: name + ' cost per claimant, ' + year, point: at(d.cost_per_claimant) },
      { label: name + ' share of benefit spending, ' + year, point: at(d.share_of_welfare) },
      { label: name + ' cost for each person living in ' + where + ', ' + year, point: at(d.spend_per_person) },
      shareOf ? { label: 'All DWP benefit spending, ' + year, point: shareOf } : null,
    ].filter(Boolean),
    method: [
      'Spending is from DWP Benefit expenditure and caseload tables, Table 1a (' + d.edition + '), series ' + d.spend_series_id + '. It covers ' + where + '.',
      'The number of people getting the benefit (the caseload) is from Table 1c, series ' + d.caseload_series_id + ', counted as “' + (d.caseload_basis === 'in_payment' ? 'in payment' : 'all cases') + '”.',
      'Cost per claimant is spending divided by the average caseload for the same year and release. The caseload is a yearly average, rounded to the nearest 1,000. DWP publishes it as spent at the time; adjusted for rising prices, we scale it by this benefit’s real ÷ cash ratio for the same year.',
      'Share of benefit spending is this benefit’s cost divided by the Table 1a total, shown out of every £100.',
      'Cost for each person in the country is spending divided by the ONS mid-year population for the same area and year.',
    ].concat(d.notes || []),
  });
});
