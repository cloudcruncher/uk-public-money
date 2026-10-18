/* Scotland and your council: Scottish Government GERS (Scotland) and MHCLG council outturn (England).
   Cash terms only. Each section loads on its own so one missing series does not blank the page. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const ix = await U.index();
  const figs = [];
  const track = (label, p) => { if (p) figs.push({ label, point: p }); };
  const nom = (s, y) => U.pointFor(s, 'nominal', y);
  const money = (p, label) => U.num(p, { label, badge: false });
  const missing = (host) => U.state(host, 'We don’t show this yet: the official figures aren’t published in a form we can trace.');
  const years = (s) => s.variants.nominal.map((p) => p.fiscal_year);
  let headline = null;
  let scotNow = null; let councilNow = null;

  /* Bars that add up to £100, each with its source amount and a "out of every £100" share. */
  function splitRows(items, year, whatTotal, totalPt) {
    const rows = U.splitOf100(items.map((i) => ({ label: i.label, fullLabel: i.label + ', ' + year, value: i.value, point: i.point })));
    return rows.map((r) => ({
      label: r.label, barValue: r.barValue,
      valueNode: money(r.point, r.fullLabel),
      share: { text: '£' + r.int, spec: U.shareSpec(r.label, year, r.point, totalPt, whatTotal) },
    }));
  }

  /* ---- 1. Scotland over time ---- */
  const timeHost = $('#scot-time');
  try {
    const ids = ['revenue', 'expenditure', 'net_balance', 'revenue_excl_north_sea', 'net_balance_excl_north_sea'];
    const d = await U.seriesMany(ids.map((k) => 'scotland_gers.' + k));
    const S = (k) => d['scotland_gers.' + k];
    if (ids.some((k) => !S(k))) throw new Error('missing');
    const ys = years(S('expenditure'));
    const y = ys[ys.length - 1];
    const rev = nom(S('revenue'), y); const exp = nom(S('expenditure'), y); const net = nom(S('net_balance'), y);
    const revX = nom(S('revenue_excl_north_sea'), y); const netX = nom(S('net_balance_excl_north_sea'), y);
    if (!rev || !exp || !net || !revX || !netX) throw new Error('missing');
    scotNow = { y, exp }; headline = headline || exp;
    track('Scotland: total public sector spending, ' + y, exp);
    track('Scotland: revenue including a share of North Sea, ' + y, rev);
    track('Scotland: net balance including a share of North Sea, ' + y, net);
    track('Scotland: revenue excluding North Sea, ' + y, revX);
    track('Scotland: net balance excluding North Sea, ' + y, netX);
    U.clear(timeHost);
    timeHost.appendChild(h('p', { class: 'faq-answer' }, 'In ' + y + ', the Scottish Government’s official estimate is that about ', money(rev, 'Scotland revenue including a share of North Sea, ' + y),
      ' was raised in Scotland, and about ', money(exp, 'Scotland total public sector spending, ' + y), ' was spent for Scotland. Figures are rounded, so they may not add up exactly. That leaves a balance of about ', money(net, 'Scotland net balance including a share of North Sea, ' + y),
      ' (a minus sign means spending was more than revenue). Without any North Sea oil and gas revenue, the balance for the same year is about ', money(netX, 'Scotland net balance excluding North Sea, ' + y), '.'));
    timeHost.appendChild(h('p', { class: 'small' }, h('strong', null, 'What the North Sea changes: '),
      'oil and gas are taken from the sea around Scotland, and the figures give Scotland a share based on where the fields are (a “geographical share”). That share is added to the revenue and so makes the balance better. The spending figure is the same either way. We show both versions so you can see the difference. ',
      U.derivedNum(U.moneyWords(rev.value - revX.value), {
        title: 'North Sea revenue counted in ' + y,
        text: 'Revenue with the geographical share of North Sea oil and gas, minus revenue without it, ' + y + '.',
        formula: 'Revenue including North Sea − revenue excluding North Sea, ' + y,
        inputs: [{ label: 'Revenue including a share of North Sea, ' + y, id: rev.provenance_id, value: U.fmt(rev.value, rev.unit) },
          { label: 'Revenue excluding North Sea, ' + y, id: revX.provenance_id, value: U.fmt(revX.value, revX.unit) }],
      }), ' of the ' + y + ' revenue is North Sea oil and gas.'));

    const recent = ys.slice(-11).reverse();
    const cell = (k, yr, label) => { const p = nom(S(k), yr); return h('td', { class: 'r' }, p ? money(p, label + ', ' + yr) : h('span', { class: 'muted' }, 'Not published yet')); };
    const head = ['Year', 'Revenue (with a North Sea share)', 'Revenue (no North Sea)', 'Spending', 'Balance (with a North Sea share)', 'Balance (no North Sea)'];
    const tbl = h('table', null,
      h('caption', null, 'Scotland: revenue, spending and balance each year, in cash terms (pounds of each year, not adjusted for prices), as restated in the 2025-26 edition (April to March). A minus balance is a shortfall.'),
      h('thead', null, h('tr', null, head.map((t, i) => h('th', { scope: 'col', class: i ? 'r' : null }, t)))),
      h('tbody', null, recent.map((yr) => h('tr', null, h('th', { scope: 'row' }, yr),
        cell('revenue', yr, 'Scotland revenue with a North Sea share'), cell('revenue_excl_north_sea', yr, 'Scotland revenue without North Sea'),
        cell('expenditure', yr, 'Scotland spending'), cell('net_balance', yr, 'Scotland balance with a North Sea share'),
        cell('net_balance_excl_north_sea', yr, 'Scotland balance without North Sea')))));
    timeHost.appendChild(h('details', { class: 'table-view', open: true }, h('summary', null, 'Last ' + recent.length + ' years, in a table'), h('div', { class: 'table-wrap' }, tbl)));
    timeHost.appendChild(h('p', { class: 'small muted' }, h('strong', null, 'What this counts: '),
      'these are estimates from the Scottish Government’s yearly “Government Expenditure and Revenue Scotland” (GERS) report, which is built from UK government and Scottish data. They are in cash terms, not adjusted for rising prices, and earlier years are restated each August. They cover spending by all levels of government for Scotland, including a share of UK-wide costs such as defence and debt interest, not just the Scottish Government’s own budget. Figures are rounded, so they may not add up exactly. They are not directly comparable with the UK-wide spending totals from the Treasury on the “Where your money goes” page, which are counted differently.'));
  } catch (e) { missing(timeHost); }

  /* ---- 2. Scotland spending by function ---- */
  const splitHost = $('#scot-split');
  try {
    const fn = ['health', 'social_protection', 'education', 'gps_debt_interest', 'defence', 'public_order_and_safety', 'ea_transport', 'gps_public_common', 'housing_and_community_amenities',
      'ea_enterprise', 'gps_lg_pension_interest', 'environment_protection', 'recreation_culture_religion', 'ea_science', 'ea_agriculture', 'gps_international', 'ea_employment', 'accounting_adjustments'];
    const d = await U.seriesMany(['scotland_gers.fn_total_expenditure', 'scotland_gers.fn_eu_transactions', ...fn.map((k) => 'scotland_gers.fn_' + k)]);
    const tot = d['scotland_gers.fn_total_expenditure'];
    if (!tot) throw new Error('missing');
    const y = years(tot)[years(tot).length - 1];
    const totPt = nom(tot, y);
    const short = (s) => U.cap1(s.title.replace(/^Scotland: spending on /, '').replace(/ \(GERS[^)]*\)$/, ''));
    const parts = fn.map((k) => d['scotland_gers.fn_' + k]).filter(Boolean).map((s) => ({ s, p: nom(s, y) })).filter((r) => r.p && r.p.value > 0);
    if (!totPt || !parts.length) throw new Error('missing');
    const euS = d['scotland_gers.fn_eu_transactions']; const euP = euS && nom(euS, y);
    const euText = euP ? 'A small item for EU transactions (' + U.moneyWords(euP.value) + ') is left out of the bars.' : 'EU transactions are not shown.';
    const sum = parts.reduce((a, r) => a + r.p.value, 0);
    const items = parts.map((r) => ({ label: short(r.s), value: (r.p.value / sum) * 100, point: r.p })).sort((a, b) => b.value - a.value);
    track('Scotland: total spending by function, ' + y, totPt);
    U.clear(splitHost);
    const srows = U.splitOf100(items.map((i) => ({ label: i.label, value: i.value, point: i.point })));
    splitHost.appendChild(h('p', { class: 'faq-answer' }, 'Of the ', money(totPt, 'Scotland total spending by function, ' + y), ' spent for Scotland in ' + y + ', the biggest share went on ',
      items[0].label.toLowerCase(), ' (about £' + srows[0].int + ' of every £100). Here is where each £100 went:'));
    splitHost.appendChild(U.scopeChip(y, 'Scotland', 'actual'));
    splitHost.appendChild(U.barList(splitRows(items, y, 'Scotland’s spending by function', totPt), { unitHead: 'Out of every £100 spent for Scotland in ' + y }));
    splitHost.appendChild(h('p', { class: 'small muted' }, h('strong', null, 'What this counts: '),
      'spending by all levels of government for Scotland (the Scottish Government, local councils and UK government bodies, including a share of UK-wide costs such as defence and debt interest), as estimated in GERS for ' + y + ' only. We show whole pounds that add up to £100. “Accounting adjustments” are bookkeeping items that are not spending on one service. ' + euText + ' These are Scottish estimates, so do not compare them line by line with the UK-wide split on the “Where your money goes” page.'));
  } catch (e) { missing(splitHost); }

  /* ---- 3 and 4. Councils in England ---- */
  const SVC = [['social_care', 'Social care (adults and children)'], ['education', 'Education'], ['housing', 'Housing'], ['highways_transport', 'Roads and transport'],
    ['police', 'Police'], ['fire_rescue', 'Fire and rescue'], ['public_health', 'Public health'], ['cultural_environmental_planning', 'Culture, environment and planning (parks, bins, planning)'],
    ['central_services', 'Central services (running the council)'], ['other', 'Other services']];
  const totHost = $('#council-total'); const splHost = $('#council-split');
  const councilNote = (kids) => h('p', { class: 'small muted' }, h('strong', null, 'What this counts: '), kids);
  let cd = null;
  try {
    cd = await U.seriesMany(['mhclg_la_outturn.total', 'mhclg_la_outturn.childrens_social_care', ...SVC.map(([k]) => 'mhclg_la_outturn.' + k)]);
    if (!cd['mhclg_la_outturn.total']) throw new Error('missing');
  } catch (e) { cd = null; }
  if (!cd) { missing(totHost); missing(splHost); } else {
    const C = (k) => cd['mhclg_la_outturn.' + k];
    const total = C('total'); const ys = years(total); const latestY = ys[ys.length - 1];
    try {
      const pts = total.variants.nominal;
      const now = pts[pts.length - 1]; const first = pts[0];
      councilNow = now; headline = headline || now;
      track('Councils in England: spending on all services, ' + now.fiscal_year, now);
      U.clear(totHost);
      totHost.appendChild(h('p', { class: 'faq-answer' }, 'In ' + now.fiscal_year + ', councils in England spent about ', money(now, 'Councils in England: spending on all services, ' + now.fiscal_year),
        ' running local services' + (first !== now ? ', up from about ' : '.'), first !== now ? [money(first, 'Councils in England: spending on all services, ' + first.fiscal_year), ' in ' + first.fiscal_year + ' (the first year in this release). These are cash amounts, so part of the rise is rising prices.'] : null));
      totHost.appendChild(U.barList(pts.map((p) => ({ label: p.fiscal_year, barValue: p.value, valueNode: money(p, 'Councils in England: spending on all services, ' + p.fiscal_year) })),
        { unitHead: 'Council spending in England each year (April to March), in pounds of the time' }));
      totHost.appendChild(councilNote('England only: Scotland, Wales and Northern Ireland publish their own council figures separately. Amounts are in cash terms, not adjusted for inflation. They are net of fees, charges and other income, including NHS money such as the Better Care Fund. The latest year is a first release, so it is provisional and is revised in later releases. Councils that had not reported in time are estimated in the provisional release. Years before 2021-22 are in a different MHCLG file that we do not read yet.'));
    } catch (e) { missing(totHost); }

    try {
      let year = latestY;
      const tools = h('div', { class: 'tools' }, U.yearSelect('Year', ys, year, (v) => { year = v; render(); }));
      const out = h('div');
      splHost.replaceChildren(tools, out);
      const render = () => {
        U.clear(out);
        const totPt = nom(total, year);
        const parts = SVC.map(([k, label]) => ({ k, label, s: C(k), p: C(k) && nom(C(k), year) })).filter((r) => r.p && r.p.value > 0);
        if (!totPt || !parts.length) { U.state(out, 'We don’t show a split for ' + year + ' yet.'); return; }
        const sum = parts.reduce((a, r) => a + r.p.value, 0);
        const items = parts.map((r) => ({ label: r.label, value: (r.p.value / sum) * 100, point: r.p })).sort((a, b) => b.value - a.value);
        const crow = U.splitOf100(items.map((i) => ({ label: i.label, value: i.value, point: i.point })));
        const provisional = year === latestY;
        parts.forEach((r) => track('Councils in England: ' + r.label + ', ' + year, r.p));
        const kids = C('childrens_social_care') && nom(C('childrens_social_care'), year);
        const sc = parts.find((r) => r.k === 'social_care');
        out.appendChild(h('p', null, 'In ', h('strong', null, year), ', councils in England spent ', money(totPt, 'Councils in England: spending on all services, ' + year),
          '. The biggest service was ', items[0].label.toLowerCase().replace(/ \(.*\)/, ''), ' (about £' + crow[0].int + ' of every £100). Here is where each £100 went:'));
        out.appendChild(provisional ? h('span', { class: 'scope' }, year + ' · England · Provisional first release') : U.scopeChip(year, 'England', 'actual'));
        out.appendChild(U.barList(splitRows(items, year, 'council spending in England', totPt), { unitHead: 'Out of every £100 councils in England spent in ' + year }));
        if (kids && sc) {
          out.appendChild(h('p', { class: 'small' }, 'Children’s social care is already inside the social care bar. In ' + year + ' it was about ', money(kids, 'Councils in England: children’s social care, ' + year),
            ', part of the ', money(sc.p, 'Councils in England: social care, ' + year), '. Do not add the two together.'));
          track('Councils in England: children’s social care, ' + year, kids);
        }
        const prov = nom(total, year) && nom(total, year).status === 'outturn' && year === latestY ? ' The ' + year + ' figures are the first release and are provisional.' : '';
        out.appendChild(councilNote('England only, in cash terms (not adjusted for inflation), net of fees, charges and other income.' + prov + ' Education is not comparable across years because schools that become academies leave council budgets. Police and fire here are the authorities counted as local government. Housing leaves out the Housing Revenue Account (council house rents and costs). Councils that had not reported in time are estimated in the provisional release. Services are grouped as MHCLG publishes them. The ten groups add up to the total, and we show whole pounds adding up to £100.'));
      };
      render();
    } catch (e) { missing(splHost); }
  }

  U.setSummary(['Scotland’s own official estimate is that ' + (scotNow ? 'about ' + U.moneyWords(scotNow.exp.value) + ' was spent for Scotland in ' + scotNow.y + ', counting all public spending for Scotland including UK-wide costs' : 'its revenue and spending are published separately') + '. Councils in England ' +
    (councilNow ? 'spent about ' + U.moneyWords(councilNow.value) + ' on local services in ' + councilNow.fiscal_year + ', which is councils only' : 'publish their own spending') + '. The two cannot be compared with each other.'],
    'Last updated ' + U.updatedText(ix), headline);

  U.mountCheckers({
    figures: figs,
    method: ['Scotland: the Scottish Government’s “Government Expenditure and Revenue Scotland” (GERS) 2025-26 tables, an Official Statistics release. They are estimates built from UK and Scottish data, in cash terms, and earlier years are restated each August. Revenue is shown with and without a geographical share of North Sea oil and gas. The split of spending by function is for 2025-26 only.',
      'Councils in England: the MHCLG (Ministry of Housing, Communities and Local Government) “Local authority revenue expenditure and financing, England” 2025-26 first release, Table 1a, 2021-22 to 2025-26. Cash terms, net of income, England only. The first release is provisional and is revised later. Children’s social care is part of social care.',
      'Scottish GERS estimates are not directly comparable with the UK-wide totals from HM Treasury (PESA) used on other pages, so we do not add or subtract them.'],
  });
});
