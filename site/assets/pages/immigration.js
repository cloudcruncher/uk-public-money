/* Immigration and public money: only series that exist in the API are shown, each with its year and scope.
   Gaps are named plainly; nothing is estimated. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const ix = await U.index();
  const figs = [];
  const track = (label, p) => { if (p) figs.push({ label, point: p }); };
  const nom = (s, y) => U.pointFor(s, 'nominal', y);
  const latest = (s) => { const pts = s.variants.nominal.filter((p) => p.status === 'outturn'); return pts.length ? pts[pts.length - 1] : null; };
  const money = (p, label) => U.num(p, { label, badge: false });
  const people = (p, label) => U.num(p, { label, badge: false });
  const input = (label, p) => ({ label, id: p.provenance_id, value: U.fmt(p.value, p.unit) });
  const pct = (v) => (v < 10 ? v.toFixed(1) : String(Math.round(v))) + '%';
  async function tryLoad(ids) {
    const out = {};
    await Promise.all(ids.map(async (id) => { try { out[id] = await U.series(id); } catch (e) { out[id] = null; } }));
    return out;
  }
  const missing = (host) => U.state(host, 'We don’t show this yet: the official figures aren’t published in a form we can trace.');

  /* ---- 1. Home Office asylum cost ---- */
  const costHost = $('#cost');
  let headline = null;
  try {
    const d = await tryLoad(['home_office_spend.resource_del.asylum_support_resettlement_accommodation', 'pesa_uk.tme']);
    const a = d['home_office_spend.resource_del.asylum_support_resettlement_accommodation']; const tme = d['pesa_uk.tme'];
    if (!a) throw new Error('missing');
    const pts = a.variants.nominal.filter((p) => p.status === 'outturn');
    const now = pts[pts.length - 1]; const y = now.fiscal_year;
    headline = now; track('Asylum support, resettlement and accommodation, ' + y, now);
    const tp = tme && nom(tme, y);
    const rows = pts.map((p) => ({ label: p.fiscal_year, barValue: p.value, valueNode: money(p, 'Asylum support, resettlement and accommodation, ' + p.fiscal_year) }));
    U.clear(costHost);
    costHost.appendChild(h('p', { class: 'faq-answer' }, 'In ' + y + ', the Home Office spent about ', money(now, 'Asylum support, resettlement and accommodation, ' + y),
      ' on asylum support, resettlement and accommodation.',
      tp ? [' That is about ', U.derivedNum(U.per100Text((now.value / tp.value) * 100),
        U.shareSpec('Asylum support, resettlement and accommodation', y, now, tp, 'total government spending')), ' in every £100 the government spent.'] : null));
    costHost.appendChild(U.barList(rows, { unitHead: 'Cost each year, as spent at the time (April to March)' }));
    costHost.appendChild(h('p', { class: 'small muted' }, h('strong', null, 'What this counts: '), 'the Home Office’s own spending on housing and supporting people who claim asylum, and on resettlement schemes. It does not include costs in other departments, such as health and schools. The source file is marked “draft” by the Home Office.'));
  } catch (e) { missing(costHost); }

  /* ---- 1b. Fee income (Home Office accounts) ---- */
  const incomeHost = $('#income');
  try {
    const rowsDef = [['visa_income', 'Visa and immigration fees'], ['ihs_retained', 'Immigration Health Surcharge'], ['immigration_skills_charge', 'Immigration Skills Charge'], ['civil_penalties', 'Fines and civil penalties']];
    const d = await tryLoad(rowsDef.map(([k]) => 'home_office_ara.' + k));
    const have = rowsDef.filter(([k]) => d['home_office_ara.' + k]);
    if (!have.length) throw new Error('missing');
    const first = d['home_office_ara.' + have[0][0]];
    const y = latest(first).fiscal_year;
    const rows = have.map(([k, label]) => ({ label, p: nom(d['home_office_ara.' + k], y) })).filter((r) => r.p).sort((a, b) => b.p.value - a.p.value);
    rows.forEach((r) => track(r.label + ', ' + y, r.p));
    const visa = rows.find((r) => r.label.startsWith('Visa'));
    U.clear(incomeHost);
    incomeHost.appendChild(h('p', { class: 'faq-answer' }, 'In ' + y + ', ', visa ? ['the Home Office recorded about ', money(visa.p, 'Visa and immigration fees, ' + y), ' of income from visa and immigration fees. '] : '',
      'Other charges and fines under the immigration system are below.'));
    incomeHost.appendChild(U.barList(rows.map((r) => ({ label: r.label, barValue: r.p.value, valueNode: money(r.p, r.label + ', ' + y) })), { unitHead: 'Income recorded in ' + y + ' (April to March), in pounds of the time' }));
    incomeHost.appendChild(h('p', { class: 'small muted' }, h('strong', null, 'What this counts: '), 'money paid to the Home Office or the Treasury in immigration fees, charges and fines, from its audited accounts. Fines are shown before money that is never paid is taken off, and much of it is never paid. The health surcharge is passed on to health services, and the skills charge goes to the Treasury. It is not tax paid by migrants, and it is not the same as the cost of the asylum system, so do not subtract one from the other. Terms: ',
      U.term('immigration-health-surcharge', 'Immigration Health Surcharge'), ' and ', U.term('immigration-skills-charge', 'Immigration Skills Charge'), '.'));
  } catch (e) { missing(incomeHost); }

  /* ---- 2. People in asylum support and hotels ---- */
  const peopleHost = $('#people');
  try {
    const d = await tryLoad(['home_office_asylum.support', 'home_office_asylum.support_hotels', 'home_office_asylum.claims']);
    const sup = d['home_office_asylum.support']; const hot = d['home_office_asylum.support_hotels']; const cl = d['home_office_asylum.claims'];
    if (!sup || !hot) throw new Error('missing');
    const ls = latest(sup); const y = ls.fiscal_year; const hp = nom(hot, y);
    track('People in asylum support, end of ' + y, ls); track('People in hotels, end of ' + y, hp);
    U.clear(peopleHost);
    peopleHost.appendChild(h('p', { class: 'faq-answer' }, 'At the end of ' + y + ', about ', people(ls, 'People in asylum support, end of ' + y), ' people were getting asylum support',
      hp ? [', and about ', people(hp, 'People in hotels, end of ' + y), ' of them were in hotels.'] : '.'));
    const hy = hot.variants.nominal.filter((p) => p.status === 'outturn');
    peopleHost.appendChild(U.barList(hy.map((p) => ({ label: 'In hotels, end of ' + p.fiscal_year, barValue: p.value, valueNode: people(p, 'People in hotels, end of ' + p.fiscal_year) })),
      { unitHead: 'People in asylum hotels at the end of each year' }));
    const clp = cl && latest(cl);
    if (clp) {
      track('Asylum claims, ' + clp.fiscal_year, clp);
      peopleHost.appendChild(h('p', { class: 'small' }, 'During ' + clp.fiscal_year + ', about ', people(clp, 'Asylum claims, ' + clp.fiscal_year), ' people claimed asylum, counting family members included in a claim. A claim is a request, not a decision.'));
    }
    peopleHost.appendChild(h('p', { class: 'small muted' }, h('strong', null, 'What this counts: '), 'people, not pounds. People in support and in hotels are counted on 31 December; claims are for the whole year. Some people stay in support for a long time and some leave quickly, so these numbers are not the same as the number of new arrivals. Terms: ',
      U.term('asylum-seeker', 'asylum seeker'), ' and ', U.term('refugee', 'refugee'), '.'));
  } catch (e) { missing(peopleHost); }

  /* ---- 3. FCDO in-donor refugee costs ---- */
  const idrcHost = $('#idrc');
  try {
    const depts = [['home_office', 'Home Office'], ['dhsc', 'Health (DHSC)'], ['dfe', 'Education (DfE)'], ['mhclg', 'Housing and communities (MHCLG)'], ['dwp', 'Work and Pensions (DWP)'], ['hmrc', 'HMRC'], ['other', 'Other, including devolved health and education']];
    const d = await tryLoad(['fcdo_oda.idrc.total', ...depts.map(([k]) => 'fcdo_oda.idrc.' + k)]);
    const tot = d['fcdo_oda.idrc.total'];
    if (!tot) throw new Error('missing');
    const lt = latest(tot); const y = lt.fiscal_year; track('Refugee costs in the UK, all departments, ' + y, lt);
    const rows = depts.map(([k, label]) => ({ k, label, p: d['fcdo_oda.idrc.' + k] && nom(d['fcdo_oda.idrc.' + k], y) })).filter((r) => r.p)
      .sort((a, b) => b.p.value - a.p.value).map((r) => ({ label: r.label, barValue: r.p.value, valueNode: money(r.p, r.label + ', ' + y) }));
    U.clear(idrcHost);
    idrcHost.appendChild(h('p', { class: 'faq-answer' }, 'Across all government departments, support for asylum seekers and refugees in their first year in the UK cost about ', money(lt, 'Refugee costs in the UK, ' + y),
      ' in calendar year ' + y + '. This is the only official total that spans several departments. It is smaller than the Home Office figure above because it counts only the first 12 months, only people from countries that can receive UK aid, and calendar years.'));
    idrcHost.appendChild(U.barList(rows, { unitHead: 'By department, calendar year ' + y + ' (first estimate, likely to be revised)' }));
    idrcHost.appendChild(h('p', { class: 'small muted' }, h('strong', null, 'What this counts: '), 'costs in the first 12 months of a person’s stay, for people from countries that can receive UK aid, as defined by the international aid rules (',
      U.term('in-donor-refugee-costs', 'in-donor refugee costs'), '). It is for a calendar year, not April to March, and is provisional. Costs after the first year are not in it. These costs are reported as part of the UK aid total.'));
  } catch (e) { missing(idrcHost); }

  /* ---- 4. Universal Credit by immigration status ---- */
  const ucHost = $('#uc');
  try {
    const parts = [['cta', 'British, Irish or right of abode'], ['eu_settlement_scheme', 'EU Settlement Scheme'], ['indefinite_leave_to_remain', 'Indefinite leave to remain'], ['refugee', 'Refugee'],
      ['limited_leave_to_remain', 'Limited leave to remain, including family reunion'], ['humanitarian', 'Humanitarian schemes (for example Ukraine, Hong Kong BN(O), Afghan resettlement)'], ['other', 'Other'], ['no_status_recorded', 'No status recorded']];
    const d = await tryLoad(parts.map(([k]) => 'dwp_uc_status.people.' + k));
    const have = parts.filter(([k]) => d['dwp_uc_status.people.' + k]);
    if (have.length < 3 || !d['dwp_uc_status.people.cta']) throw new Error('missing');
    const y = latest(d['dwp_uc_status.people.' + have[0][0]]).fiscal_year;
    const pts = have.map(([k, label]) => ({ label, p: nom(d['dwp_uc_status.people.' + k], y) })).filter((r) => r.p);
    const total = pts.reduce((a, r) => a + r.p.value, 0);
    pts.forEach((r) => track(r.label + ', May ' + y, r.p));
    const shareSpec = (r) => ({
      title: 'Share of people on Universal Credit: ' + r.label,
      text: 'This group divided by everyone on Universal Credit in May ' + y + ' (all the groups added together), times 100.',
      formula: r.label + ' ÷ all groups added together, May ' + y + ', × 100',
      inputs: [input(r.label, r.p), ...pts.filter((o) => o !== r).map((o) => input(o.label, o.p))],
    });
    const rows = pts.sort((a, b) => b.p.value - a.p.value).map((r) => ({
      label: r.label, barValue: r.p.value, valueNode: people(r.p, r.label + ', May ' + y),
      share: { text: pct((r.p.value / total) * 100), spec: shareSpec(r) },
    }));
    U.clear(ucHost);
    ucHost.appendChild(h('p', { class: 'faq-answer' }, 'In May ' + y + ', about ', U.derivedNum(pct((pts.find((r) => r.label.startsWith('British')).p.value / total) * 100), shareSpec(pts.find((r) => r.label.startsWith('British')))),
      ' of the people on Universal Credit in Great Britain were British or Irish citizens, or had the right of abode (the latest three months are provisional). The rest are in the groups below.'));
    ucHost.appendChild(U.barList(rows, { unitHead: 'People on Universal Credit in May ' + y + ', by immigration status' }));
    ucHost.appendChild(h('p', { class: 'small muted' }, h('strong', null, 'What this counts: '), 'people, not pounds, in Great Britain, and Universal Credit only. It says nothing about other benefits. Status comes from the claimant’s residence checks; the latest three months are provisional; some people who became British may still be counted under their old status if DWP was not told. Terms: ',
      U.term('leave-to-remain', 'leave to remain'), '.'));
  } catch (e) { missing(ucHost); }

  /* ---- gaps ---- */
  $('#gaps').appendChild(h('ul', { class: 'method-list' },
    h('li', null, h('strong', null, 'Tax paid by migrants. '), 'HMRC’s breakdown by nationality stops in 2018-19. One independent expert body has published a model-based estimate, which we do not show because it is a model, not a count.'),
    h('li', null, h('strong', null, 'The cost of asylum hotels in pounds. '), 'Official statistics count the people in hotels but do not publish one pounds total for them.'),
    h('li', null, h('strong', null, 'Money paid to, or by, people who are in the country without permission. '), 'No official figure exists.'),
    h('li', null, 'Where we skip a number, ', U.ext('https://github.com/cloudcruncher/uk-public-money/blob/main/docs/SOURCES.md', 'docs/SOURCES.md'), ' says why.')));

  U.setSummary(['We show what officials have published on the cost of the asylum system, immigration fee income, the people in the system and Universal Credit claims by status. Some figures, such as tax paid by migrants, are not published in a usable form.'],
    'Last updated ' + U.updatedText(ix), headline);

  U.mountCheckers({
    figures: figs,
    method: ['Fee income is from the Home Office Annual Report and Accounts 2025-26 (audited accounts, read from fixed pages). Home Office spending is “resource DEL” (day-to-day budget) from the Home Office Core Data Tables, 2026; plans years are not shown.',
      'Asylum counts are from Home Office asylum statistics at 31 December each year. Refugee costs are from the FCDO provisional UK aid statistics (calendar years). Universal Credit counts are from DWP, Great Britain, May of each year.',
      'These sources use different years (financial, calendar or a single month), so we do not add them together.'],
  });
});
