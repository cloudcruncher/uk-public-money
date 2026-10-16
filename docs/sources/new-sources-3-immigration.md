# New sources 3: immigration income, outgoings and status classification

Checked 2026-10-15. Files fetched with curl into a scratchpad directory outside the repo and read with `python3 -I` (treated as untrusted). Browser UA used (Mozilla/5.0 Macintosh, Chrome/124); OBR and some gov.uk hosts return 403 to a bare curl UA. Licence lines are those standard on the landing page or site footer: gov.uk pages carry "All content is available under the Open Government Licence v3.0, except where otherwise stated"; where not checked the line is marked UNVERIFIED. Only URLs that returned HTTP 200 are recorded. Landing pages marked "content API 200" were resolved through the gov.uk content API (https://www.gov.uk/api/content/...) rather than fetched as HTML. Neutral wording throughout: this file records what official sources publish, not what they imply.

## 1. Summary answer

| Question | Official figure exists? | Best source | Verdict |
|---|---|---|---|
| Income: visa and immigration fees | Yes, audited outturn | Home Office ARA 2025-26, Note 3 and Fees and Charges table | USABLE |
| Income: Immigration Health Surcharge (IHS) | Yes, total only | Home Office ARA 2025-26, Note 3 | USABLE |
| Income: Immigration Skills Charge (ISC) | Yes, total only | Home Office ARA 2025-26, Trust Statement | USABLE |
| Income: tax paid by migrants | Partly: by nationality, up to 2018-19 only; modelled for Skilled Worker cohort | HMRC non-UK nationals series; MAC Dec 2025 | PARTIAL |
| Outgoings: asylum support, resettlement, accommodation (total) | Yes, departmental outturn (resource DEL) | Home Office Core Data Tables 2026 | USABLE |
| Outgoings: asylum hotels in GBP | Counts yes; GBP total not in ARA; contract-level estimate from NAO | Home Office stats (counts); NAO HC 874 | PARTIAL |
| Outgoings: refugee/asylum costs across departments | Yes, provisional calendar-year series (OECD in-donor refugee cost definition) | FCDO provisional ODA spend 2025 | PARTIAL |
| Outgoings: benefits by nationality or status | Universal Credit people counts by status only (GB); no GBP; no other benefits | DWP UC immigration status and nationality statistics | PARTIAL |
| Outgoings: NHS | No aggregate found | none (IHS income only) | gap |
| Classification by status/route | Yes, counts | Home Office immigration system statistics YE Jun 2026 | USABLE (counts) |
| OBR net-migration assumption | Yes, forecast | OBR EFO March 2026 | USABLE |
| Official fiscal-impact estimates | Yes, narrow scope | MAC Dec 2025; two Home Office indicative notes | PARTIAL |
| Tax paid / benefits received by irregular migrants | No official figure found | n/a | gap |

## 2. Income

### 2.1 Home Office Annual Report and Accounts 2025-26 (HC 440)

- Publisher: Home Office. Published 2026-07-14. Licence: OGL v3.0 (gov.uk standard line).
- Landing: https://www.gov.uk/government/publications/home-office-annual-report-and-accounts-2025-to-2026 (content API 200).
- Outturn (audited accounts). Years: 2025-26 with 2024-25 comparatives. Financial years (April to March).

| File | Content-Type | Size | sha256 |
|---|---|---|---|
| https://assets.publishing.service.gov.uk/media/6a58e9953ae256c99b702f50/36.54_HO_ARA_25-26_WEB.pdf (200) | application/pdf | 18,763,104 B (370 pp) | c8cda7ee5f28700b4a2174b3889cb203c410503c60222e6a03102d92642c1350 |

Figures (GBP thousands unless stated):

| Location | Line | 2025-26 | 2024-25 |
|---|---|---|---|
| Note 3 Income (PDF p283, printed p278) | Visa and immigration income | 3,574,088 | 2,978,355 |
| Note 3 | Immigration Health Surcharge (retained, other operating income) | 2,318,923 | 2,420,109 |
| Note 3 | IHS payable to Consolidated Fund | nil | 200,769 |
| Note 3 | Passport fees | 549,532 | not recorded here |
| Fees and Charges table (PDF p228, printed p223) | Customer Service (UKVI) in-country and overseas: income / full cost / surplus / recovery | 3,574,081 / 1,067,639 / 2,506,442 / 335% (target 335%) | 2,978,356 / 1,164,523 / 1,813,833 / 256% (target 241%) |
| Same table | Total fees-and-charges income | 4,789,762 | not recorded here |
| Trust Statement (PDF p339, printed p334) | Gross revenue to Consolidated Fund | 814.7m | 786.8m (restated) |
| Trust Statement | Immigration Skills Charge | 594.3m | 559.7m |
| Trust Statement | Civil penalties | 111.3m | 122.9m (restated) |

- Notes in the report: ISC rates from 16 Dec 2025 are 480 (small/charity, previously 364) and 1,320 (medium/large, previously 1,000) per worker per year. IHS is passed on to DHSC and devolved governments via Barnett; IHS income is recognised on approval, deferred income uses an average IHS fee (an estimate); an IHS reimbursement scheme error of about 18.7m is recognised as a reduction in IHS income. The rise in visa income is attributed mainly to fee increases.
- Includes: fee income by UKVI total, IHS retained, ISC and civil penalties. Does NOT include: tax paid by migrants, net fiscal effect, income split by visa route, any hotel GBP figure (searched; none found).
- Revision behaviour: prior years are restated in places (Trust Statement marks "restated"); groupings and line names change between years.
- Verdict: USABLE (outturn).
- Smallest fixture: Note 3 rows for visa income and IHS (both years) and the Trust Statement ISC row, transcribed as a small CSV with page references.

### 2.2 Home Office Core Data Tables 2026 (companion to the ARA)

- Publisher: Home Office. Licence: OGL v3.0 (UNVERIFIED on the attachment page; standard gov.uk footer).
- File: https://assets.publishing.service.gov.uk/media/6a5651389e63154454413675/Core_Data_Tables_2026_Home_Office__draft__based_on_ARA_model_shared_29th_June__-_FINAL__FRT_.xlsx (200), 1,571,233 B, sha256 8860a2fe3e2b1d1d41e4c7264fc313d2a7cf8d7becf9f9e78456083e51bcda29. The file name contains "draft"; treat the numbers as to be reconciled against the ARA PDF.
- Sheets Total_departmental_spending and Administration_Spending. GBP thousands. Columns 2021-22 to 2025-26 are OUTTURN; 2026-27 to 2028-29 are PLANS.
- Rows (sheet Total_departmental_spending, resource DEL): row 17 "Customer Services (Visas & Passports)": 2022-23 -3,166,254; 2023-24 -3,344,985; 2024-25 -4,319,505; 2025-26 -4,934,927 (negative = net of fee income). Row 20 "Asylum Support, Resettlement and Accommodation": 2023-24 5,424,708; 2024-25 4,512,567; 2025-26 4,181,193. Row 19 "Asylum & Protection" 2022-23 4,498,823. Row 21 "Asylum Group" plans 4,116,034 / 3,795,700 / 3,621,700. Row 39 income from sales of goods and services: -1,860,975 (2021-22) to -4,096,750 (2025-26). Row 76 capital for the same group: 195,032 / 22,685 / 33,151.
- Cross-check in the ARA performance report: Asylum Support, Resettlement and Accommodation budget 4.33bn vs actual 4.18bn. Afghan resettlement Home Office costs 222.1m in 2025-26 (205m in 2024-25).
- Includes: Home Office spending only. Does NOT include: other departments' costs (DWP, DHSC, DfE, local authorities).
- Verdict: USABLE (outturn), with the draft-filename caveat and group renaming year to year.
- Smallest fixture: rows 17, 19, 20 and header rows 4-6 of Total_departmental_spending.

## 3. Outgoings

### 3.1 Asylum support and hotels (Home Office statistics, ARA, NAO)

- Counts of people (Home Office asylum summary tables, section 5.1 below): in receipt of support 93,293 in June 2026 (107,003 at end December 2025, matching the ARA); of which in hotels 16,021 (June 2026) vs 32,041 (June 2025). ARA: 30,657 in hotels end December 2025 (38,054 December 2024; peak 56,018 September 2023).
- GBP: the ARA reports Asylum Support, Resettlement and Accommodation outturn of 4.18bn (section 2.2), but no separate hotel GBP figure was found in the ARA text.
- NAO report: "The Home Office's asylum accommodation contracts", HC 874, 7 May 2025, with correction note. File https://www.nao.org.uk/wp-content/uploads/2025/05/home-offices-asylum-accommodation-contracts.pdf (200), application/pdf, 543,037 B, sha256 5c6dad774c52ab2cc4efecebc26e16d9b16c9e21a0984001bf97615ad2d7648a. Publisher: National Audit Office (independent of government; not gov.uk). Licence: UNVERIFIED. Content: in the first seven months of 2024-25 the Home Office spent an estimated 1.7bn on the asylum accommodation and support contracts (AASC); current estimate of total 10-year spend (2019-29) 15.3bn; hotels about 35% of people in asylum accommodation and about 76% of contract cost (1.3bn of 1.7bn, first seven months 2024-25). Estimate, partial year, contracts only.
- Verdict: PARTIAL.

### 3.2 FCDO provisional UK ODA spend 2025 (in-donor refugee costs)

- Publisher: FCDO. Accredited Official Statistics, 2026-04-09; next (final 2025) due Autumn 2026. Licence: OGL v3.0 (gov.uk standard line).
- Landing: https://www.gov.uk/government/statistics/statistics-on-international-development-provisional-uk-official-development-assistance-spend-2025 (content API 200).

| File | Content-Type | Size | sha256 |
|---|---|---|---|
| https://assets.publishing.service.gov.uk/media/69d4cb4d826d774e7b263e3c/Tables-Statistics-on-International-Development-provisional-UK-ODA-spend-2025.ods (200) | ODS | 29,053 B | cb1363b7c2fa914e81b0864052e5fb85051aaaadd496749f2a262fbece81a8fa |
| https://assets.publishing.service.gov.uk/media/69d77ee00c6c0aacee394b2b/Statistics-on-International-Development-Provisional-UK-ODA-Spend-2025.pdf (200) | application/pdf | 1,443,503 B | 9f5bb660751b0d552d9e52b0d25f3948e9f3e8cc1acdb6d6399e37330658776d |

- Sheet Fig3, "Total UK In-donor Refugee Costs (IDRC) incurred in the UK: by Department", GBP million, calendar years 2021-2025:

| Department | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| Home Office | 996 | 2,382 | 2,936 | 2,374 | 2,050 |
| DHSC | 26 | 274 | 318 | 132 | 103 |
| DfE | 21 | 218 | 169 | 91 | 74 |
| MHCLG | 0 | 524 | 466 | 98 | 69 |
| DWP | 4 | 163 | 249 | 85 | 62 |
| Other (incl. estimated devolved health/education) | 4 | 109 | 106 | 41 | 30 |
| HMRC | 0 | 21 | 28 | 6 | 6 |
| Total | 1,052 | 3,690 | 4,273 | 2,827 | 2,395 |
| % of total ODA | 9.2 | 28.9 | 27.9 | 20.1 | 18.3 |

- Definition (PDF p11): OECD DAC in-donor refugee costs are costs incurred in a donor country for support to asylum seekers and refugees from developing countries during the first 12 months of their stay (transport, temporary sustenance: food, shelter, training). 2025 total 2,395m, a decrease of 432m (15.3%) on 2024.
- Includes: the only cross-department GBP series on refugee/asylum costs found. Does NOT include: costs beyond the first 12 months, nationals of non-eligible countries, or non-ODA-eligible spend; calendar year, not financial year.
- Provisional; revised in the final release. A final 2024 release exists (https://www.gov.uk/government/statistics/statistics-on-international-development-final-uk-oda-spend-2024; not downloaded).
- Verdict: PARTIAL (usable as a labelled series with the definition caveat).
- Smallest fixture: sheet Fig3 as a 8-row by 5-column CSV.

### 3.3 DWP Universal Credit by immigration status and nationality

- Publisher: DWP. Official Statistics, published 2026-08-18; quarterly; next 2026-11-17. Coverage: Great Britain. Licence: OGL v3.0 (gov.uk standard line).
- Landing: https://www.gov.uk/government/statistics/universal-credit-quarterly-statistics-29-april-2013-to-14-may-2026 (content API 200).

| File | Content-Type | Size | sha256 |
|---|---|---|---|
| https://assets.publishing.service.gov.uk/media/6a82c17492ec93e1e0329a46/uc-immigration-status-nationality-statistics-to-may-2026.ods (200) | ODS | 61,736 B | 22c9f2f3aa448af7f5ea4458cb2286e494a79f69ac31a7fa0b7381e86d2f29e4 |

- Sheets: Contents, Guidance, Table_1 (people on UC by immigration status, monthly April 2022 to May 2026, header row 8, 53 monthly columns, latest first), Table_2 (status by nationality by employment; header says Apr-26, which is inconsistent with the file title).
- Table_1 May 2026 (people): Citizen/Right of Abode/Irish (CTA) 7,065,665; EU Settlement Scheme 744,679; Humanitarian 52,499; Refugee 130,618; Indefinite Leave to Remain 233,217; Limited Leave to Remain incl. Family Reunion 75,512; Other 34,209; No immigration status recorded 23,343. CTA April 2022 (earliest) 4,612,021.
- Notes from the Guidance sheet: unit is number of people, not GBP; nationality is the latest declared by the claimant; status comes from Habitual Residence Test data; the last three months are provisional and HRT revisions apply retrospectively; dual nationals with CTA are recorded as CTA; naturalised citizens fall in CTA; disclosure control/perturbation applies; "Humanitarian" covers Ukraine, BN(O), resettlement schemes, ARAP and ACRS, with "Refugee" shown separately. "No immigration status recorded" is a data-recording category, not a measure of irregular status. People subject to no recourse to public funds, and asylum seekers, cannot claim UC.
- Includes: counts of UC claimants by status. Does NOT include: GBP expenditure, other benefits (PIP, Housing Benefit, Pension Credit, Child Benefit and others), Northern Ireland.
- Another earlier-vintage copy (nationality_april_2022_to_january_2026.ods) is referenced by third parties; not fetched. Stat-Xplore (https://stat-xplore.dwp.gov.uk) is named as a data source; not fetched.
- Verdict: USABLE for UC counts by status; PARTIAL as an answer to "benefits claimed".
- Smallest fixture: Table_1 header row plus rows 8-17 for the latest 4 month columns, and Guidance rows 12-14.
- Related, not downloaded (content API only): DWP "National Insurance number allocations to adult overseas nationals", quarterly, latest to March 2026, published 2026-05-21. Counts new NINo registrations, not benefit receipt or spend.

## 4. Classification by status or route

### 4.1 Home Office immigration system statistics, year ending June 2026

- Publisher: Home Office. Published 2026-08-27; next 2026-11-26. Crown copyright; Licence: OGL v3.0 (gov.uk standard line, UNVERIFIED on this dataset page).
- Landing: https://www.gov.uk/government/statistical-data-sets/immigration-system-statistics-data-tables (content API 200).

| File | Size | sha256 |
|---|---|---|
| https://assets.publishing.service.gov.uk/media/6a85c315b0504df9f2c89800/asylum-summary-jun-2026-tables.ods (200) | 121,209 B | f935782ab90190deb04a1a86f7b6ba7515f32e238c14b96c55993f4793096d14 |
| https://assets.publishing.service.gov.uk/media/6a8c11c3a8f84a582b84281a/illegal-entry-routes-to-the-uk-summary-jun-2026-tables.ods (200) | 33,607 B | 247cdb26e11953ce73a88589c9edc9ade531328a5f97b75c56abf612217c293f |
| https://assets.publishing.service.gov.uk/media/6a85c59054bcee010d514573/safe-legal-routes-summary-tables-jun-2026.ods (200) | about 62 kB | 087938fe4954166d39d9c46e04fb3a353fc557448e06c9929db92029261e11af |

All ODS (application/vnd.oasis.opendocument.spreadsheet). Figures, year ending June 2026 (YE Jun 2025 in brackets):

- Asy_00a: people claiming asylum 85,891 (108,585); initial decisions 115,872; grants 42,394 (53,480); refusals 73,478; grant rate 38% (48%); awaiting initial decision 40,168 (90,812); in receipt of support 93,293 (106,075); of which in hotels 16,021 (32,041); asylum-related returns 12,568.
- Asy_09a (June 2026) by support type: Section 95 85,998; Section 4 4,987; Section 98 2,308. Asy_09b: total in support 93,293 (single applicants 51,947; family members 41,346; families 12,345).
- Asy_01c asylum claims by route of prior entry: Illegal Entry Routes 44,297 (small boat 33,949; clandestine 6,999; entered without relevant documentation 3,349); Visas and Other Leave 34,999 (study 9,442; work 14,151; visitor 6,392; other leave 5,014). These are by claim date and differ from arrival-date counts in the illegal entry routes tables.
- IER_01: small boat arrivals 33,374 (43,309); inadequately documented air arrivals 2,492; recorded detections in the UK 1,962; at ports 258.
- Hum_01 (safe and legal routes): resettlement arrivals 3,840; BN(O) visa grants 13,969; Ukraine visa grants 94,233; Refugee Family Reunion grants 12,888; total 124,930 (142,418).
- Other attachments listed on the page, not downloaded: asylum seekers in receipt of support datasets, resettlement datasets, returns. Migrant journey 2025 report: https://www.gov.uk/government/statistics/migrant-journey-2025-report (2026-05-21; status outcomes of cohorts, not fiscal).
- Includes: counts by route and support type, the official status/route classification. Does NOT include: GBP, tax, benefits or any fiscal impact.
- Revision behaviour: restated quarterly; some cells carry suppression markers.
- Verdict: USABLE (counts only).
- Smallest fixture: Asy_00a and Asy_09a as CSV; IER_01 first four rows.

## 5. OBR assumptions

### 5.1 Economic and fiscal outlook, March 2026

- Publisher: Office for Budget Responsibility. Licence: UNVERIFIED (landing page not re-fetched for licence text). Landing: https://obr.uk/efo/economic-and-fiscal-outlook-march-2026/ (200 per earlier check; browser UA required).

| File | Content-Type | Size | sha256 |
|---|---|---|---|
| https://assets.publishing.service.gov.uk/media/69a6d7b62e1f4fbda4252208/economic-and-fiscal-outlook-march-2026-web-accessible.pdf (200) | application/pdf | 1,112,521 B | e1d08a66afdda02789a087b79ddbb3398a4e9414254aed8c5de0fc74577f8be6 |
| https://obr.uk/docs/d055fbf02d5b3g6jq8l2/efo-march-2026-charts-and-tables-zipfile.zip (200) | application/zip | 4,083,562 B | fb899257ef17c7407eed4e17559b2a037becccd4924366a49f7e6dac5d596aa4 |
| member efo-march-2026-charts-and-tables-chapter-2.xlsx (extracted) | xlsx | n/a | d1ba09340a85c2a4034edd3a60a18354befe3f88cb2fa588d011d5817a7b8734 |
| https://obr.uk/docs/.../efo-march-2026-detailed-forecast-tables-zipfile.zip (via https://obr.uk/download/march-2026-economic-and-fiscal-outlook-detailed-forecast-tables-zip-file/) (200) | application/zip | 1,226,333 B | de72d04940ea7e4013a1b6cce230f7144a05ad734cdd3e72306f34f6c4eb24cd |

- Text, paras 2.11-2.14 (PDF p26-27): central forecast has net inward migration "to rise to around 290,000 in 2030, mainly non-EU nationals". ONS revised down recent net migration on 18 Nov 2025 (British nationals 2021-24 average -92,000 a year vs -6,500 before); the OBR lowered its central net inward migration forecast by about 60,000 people (50,000 adults) a year on average; adult population is about 200,000 lower by 2030. Policy changes on indefinite leave to remain and asylum are not in the forecast. ONS long-term international migration is badged "official statistics in development". Box 2.1 (p28) cites the March 2024 EFO scenarios (plus or minus 200,000 net migration moves real GDP by 1-2% after five years).
- Data, chapter 2 workbook, sheet C2.6 rows 25-44, columns F-H, overall net migration, thousands, mid-year, November 2025 forecast vs March 2026 forecast: 2022 634/681; 2023 906/924; 2024 739/649; 2025 291/204; 2026 262/200; 2027 258/203; 2028 290/235; 2029 327/254; 2030 340/281; 2031 340/290.
- Discrepancy to flag: the text says "around 290,000 in 2030" but the sheet shows 281 in 2030 and 290 in 2031. Check which year convention applies before using either.
- The detailed forecast tables workbook (economy.xlsx, sha256 fde1de4bc5424dcf16c7b5c42eb75a35198e347f54db47690e95ede7541db510) has no net-migration table. The EFO does not publish fiscal impact by migrant group.
- Forecast; revised at every EFO (next: Autumn 2026).
- Verdict: USABLE for the net-migration assumption; not a fiscal-impact source.
- Smallest fixture: C2.6 rows 25-44, columns A and F-H.

### 5.2 Fiscal risks and sustainability, July 2026

- File: https://assets.publishing.service.gov.uk/media/6a4cb4c74889d85e75ab40e0/E03599617_OBR_FRS_2026_Accessible.pdf (200), application/pdf, 1,375,079 B, sha256 3274a2d1373e6093ebd3a14298f873b9efead3d659d2878b64121941c80ea2b3. Licence UNVERIFIED.
- PDF p33 (printed p28): long-run demographics use the ONS projection assuming 230,000 net arrivals a year from 2031; net migration contributes nearly 12 million additional people across the projection; described as highly uncertain; population about 81 million by 2075 in the unchanged-net-migration scenario. It refers to earlier FRS editions (2022, 2024) with migration scenarios; those were not fetched and are pointers only.
- Related: OBR article "Forecasting net migration", https://articles.obr.uk/forecasting-net-migration/index.html (200, text/html, 553,924 B, sha256 e7b08547de30c3a962905d55dcc8275357ec6e129c88cbad8fe57dff661f5fbc); not read in detail.
- A figure of "20bn borrowing per 200,000 net migration" (March 2024) was seen only second-hand via an IFS write-up; UNVERIFIED, not stated here as an OBR figure.
- Verdict: PARTIAL (projection assumption, not a fiscal-by-status estimate).

### 5.3 Other pointers (not downloaded or not read for figures)

- MAC "Report on net migration" (May 2025): https://www.gov.uk/government/publications/migration-advisory-committee-report-on-net-migration; data tables ODS https://assets.publishing.service.gov.uk/media/681b2be0155568d3da1d2968/Net+Migration+data+tables.ods (200 when fetched; 144,244 B; sha256 2e090379f5af24fba5adabd3537865243d3703540df8e9e5be8980724f55c480). Migration volumes, not fiscal. Not inspected in detail.
- Home Office page "MEDP with Rwanda and the Illegal Migration Act associated costs" (2024-12-02), https://www.gov.uk/government/publications/medp-with-rwanda-and-the-illegal-migration-act-associated-costs (content API only; not read for figures).
- Home Office migration analysis collection (impact assessments): https://www.gov.uk/government/collections/migration-analysis-at-the-home-office (not examined).

## 6. Official fiscal-impact estimates

### 6.1 MAC, "The Fiscal Impact of Immigration: Static and Dynamic Estimates for the UK" (December 2025)

- Publisher: Migration Advisory Committee. First published 2025-12-11, updated 2026-03-18. Licence: OGL v3.0 (gov.uk standard line). Landing: https://www.gov.uk/government/publications/the-fiscal-impact-of-immigration-in-the-uk (content API 200).

| File | Content-Type | Size | sha256 |
|---|---|---|---|
| https://assets.publishing.service.gov.uk/media/6938108633c7ace9c4a41e42/The_Fiscal_Impact_of_Immigration_Final__1_.pdf (200) | application/pdf | 1,609,074 B (64 pp) | 58d41c126b0300444d3129f551f0beaaff91a59a24af20f9b426f93e638d0518 |
| https://assets.publishing.service.gov.uk/media/69ba8a09530e305110e7f5e1/fiscal_report_ods_tables.checked.ods (200) | ODS | 328,098 B | ab431dbcd7d3eb40e611d2e208968124803f78a0b5dbf041ace642a53a22c608 |

- ODS sheets: Table_4, Figure_5, Figure_6, Figure_7, Table_9, Figure_10, Table_11, Table_14, Fig 15-21, Table_22, Table_23.
- Table_9, annualised visa fee revenue per person (2022/23 GBP): Skilled Worker excluding Health and Care, main applicant: application fee 298, IHS 618, ISC 729, certificate of sponsorship 75, total 1,720. Health and Care main applicant total 933 (IHS not applicable). Adult dependants 880 / 120; child 732 / 119 (as recorded in the sheet).
- Figure_10, net static fiscal impact including visa fees, 2022/23 per person per year: Skilled Worker main applicant +21,800 (excluding Health and Care +40,300; Health and Care main applicant +9,200); adult dependant +2,000; UK resident adult +3,400; UK child -14,900.
- Table_23, lifetime totals, GBP million, 2022/23 arrival cohort (329,200 arrivals): Skilled Worker excluding H&C main: tax 72,100, visa fees 600, expenditure 25,100, net +47,700; H&C main net +5,500; H&C adult dependants -3,300; H&C children -2,000; all groups: tax 140,300, visa fees 1,300, expenditure 94,500, net +47,100.
- Scope: Skilled Worker (including Health and Care) visa cohort entering in 2022/23 and their dependants only. The report states that family, other work, humanitarian and asylum routes are future work; they are not covered.
- Estimate (model with discounting and assumptions); not outturn. Revision: report updated 2026-03-18; future cohorts to be added.
- Verdict: PARTIAL (USABLE for the Skilled Worker and Health and Care routes only).
- Smallest fixture: Table_9 and Figure_10 as CSV; Table_23 totals row.

### 6.2 Home Office indicative fiscal notes

Publisher: Home Office. Licence: OGL v3.0 (stated on the page for Article 8). Both are indicative derived estimates without data tables.

| Page | Published | Size | sha256 |
|---|---|---|---|
| https://www.gov.uk/government/publications/estimated-lifetime-net-fiscal-impact-of-article-8-main-applicants/estimated-lifetime-net-fiscal-impact-of-article-8-main-applicants (200, text/html) | 2026-06-26 | 95,350 B | 10cbb9be4eb2923eafb20a9ff40769a85458efbb59c6df7c54e0f33494ecf22c |
| https://www.gov.uk/government/publications/estimated-lifetime-net-fiscal-costs-for-care-workers-and-their-adult-dependants/estimated-lifetime-net-fiscal-costs-for-care-workers-and-their-adult-dependants (200, text/html) | 2026-03-05 | 83,196 B | eccf6446491fea451eb0ac905b1ebe5f39ccc9911d1ccafdbef3a71c69d00949 |

- Article 8 note: uses the MAC model; excludes visa fee income and IHS; family partner (out of country) -112,000 per grantee; family and private life (in country) -141,000 (used as a proxy); first-time in-country Article 8 main applicant grantees in 2025 about 4.9bn net lifetime cost.
- Care worker note: applies MAC per-person estimates (care worker main applicant -36,000; adult dependant -67,000) to the Home Office settlement forecast 2026-2030 (117,000 care workers giving 4.2bn; 79,000 adult dependants giving 5.3bn; total 9.5bn, "10bn to the nearest billion"). Uses 2022/23 cohort per-person values for 2026-30; forecast-based.
- Verdict: PARTIAL (indicative, narrow scope, depend on MAC assumptions).

### 6.3 HMRC, Income Tax, NICs, Tax Credits and Child Benefit statistics for non-UK nationals

- Publisher: HMRC. Official Statistics. Latest edition found: tax year 2018-19, released 2022-01-26. Licence: OGL v3.0 (gov.uk standard line). Landing: https://www.gov.uk/government/statistics/income-tax-national-insurance-contributions-tax-credits-and-child-benefit-statistics-for-non-uk-nationals-2018-to-2019 (content API 200).

| File | Content-Type | Size | sha256 |
|---|---|---|---|
| https://assets.publishing.service.gov.uk/media/61ee67fc8fa8f505893f1dfa/Income_Tax__NICs__Tax_Credits_and_Child_Benefit_Statistics_for_Non-UK_Nationals_in_the_2018_to_2019_Tax_Year.ods (200) | ODS | 47,057 B | 38e0592bece94855f5bb8540bebb5caeb7ab52c6399767bc6b8f8353b3e242ee |
| https://assets.publishing.service.gov.uk/media/61eab60de90e07037794ff7f/Income_Tax__NICs__tax_credits_and_Child_Benefit_statistics_for_non-UK_nationals_2017_to_2018_.ods (200, 2017-18 edition, released 2020-08-27) | ODS | 46,992 B | 4755b72a496059701cd3b338cb4395599f7a3ad88a518dc932d6e143d784c37b |

- 2018-19 values: Table B1 row 33 "Total EEA and Switzerland": income tax 2,251k individuals, 13,889m; NICs 3,132k, 11,515m; tax credits 482k, 1,916m; Child Benefit 680k, 1,045m. Table B5 row 67 "Total non-EEA": income tax 1,572k, 14,127m; NICs 1,950k, 9,910m; tax credits 659k, 2,980m; Child Benefit 620k, 1,060m. Tables C5/C6: EEA and Swiss income before tax 77.5bn, income tax 13.9bn; non-EEA 69.3bn, 14.1bn. Table D1 taxpayers EEA 2,209k, non-EEA 1,549k. "Recently arrived" means arrival between 6 April 2015 and 5 April 2019.
- Sources: Survey of Personal Incomes, HMRC tax credit and Child Benefit records, Migrant Worker Scan.
- Includes: gross income tax, NICs, tax credits and Child Benefit by nationality group. Does NOT include: indirect taxes, corporation tax, public service use, net fiscal position, immigration status (nationality only). Tax credits have since been replaced by Universal Credit.
- No edition for 2019-20 onward found (content API returned 404 for 2019-to-2020, 2020-to-2021, 2021-to-2022).
- Verdict: PARTIAL (dated; nationality, not status).
- Smallest fixture: Table B1 row 33 and Table B5 row 67 with headers.

## 7. Gaps, with evidence

1. Tax paid or benefits received by irregular migrants or by asylum seekers: no official figure found. Evidence: ONS FOI-2025-2887 (17 June 2025; https://cy.ons.gov.uk/aboutus/transparencyandgovernance/ukbenefitclaimbyimmigrationstatus, 200, text/html, 32,185 B, sha256 767d9bc7e0484a75c3f99376aad2b1d0f531061e96eca34ec3f3102629ea9623) states ONS does not hold benefit claimants by citizenship or immigration status, nor those without legal immigration status, and points to DWP Stat-Xplore. DWP UC statistics have no irregular-status category (asylum seekers and no-recourse-to-public-funds cases cannot claim UC; "no immigration status recorded" is a recording category). HMRC publishes by nationality, not status. Asylum seekers' right to work is governed by Home Office rules not examined here.
2. DWP nationality breakdown beyond UC: ICO decision notice IC-510838-x8x0 (1 September 2026; 200, text/html, 30,042 B, sha256 0d543b336dc16065c281bc6fae7c31d984517878172957c3e15f03bc8304ca2b) upheld DWP's reliance on the future-publication exemption (s22) for a UC nationality breakdown. No GBP benefit spend by nationality or status found for any benefit.
3. Asylum hotels GBP: no official total in the ARA; NAO gives a contract-level partial-year estimate only (section 3.1).
4. NHS: no official aggregate cost of NHS care for migrants or overseas visitor charging income found in this search; only IHS income (Home Office accounts). An older NAO overseas-visitor report exists but was not fetched.
5. IHS by visa category or status: not published in the ARA; MAC gives per-person IHS for Skilled Worker routes only.
6. Fee income by route: the ARA reports UKVI totals only.
7. Lifetime fiscal impact of refugee, asylum and irregular-route arrivals: not estimated by MAC (stated as future work); no Home Office note found for these groups.
8. Local authority and devolved costs: only partly captured in the FCDO series (for example MHCLG 69m in 2025); no complete official cost of the Ukraine schemes found.
9. HMRC nationality series stops at 2018-19.

## 8. Unofficial estimates (NOT official; not relied on; seen in search results only, not fetched or verified here)

- asylumstats.co.uk (independent site): reports asylum hotel costs of about 2.1bn in 2025-26 and about 5.77m per day in 2024/25. Method: its own analysis built on departmental accounts. Not verified against the ARA, which has no hotel GBP line.
- Migration Observatory, University of Oxford: IHS income "over 2.4bn" in 2024/25 (academic summary; consistent with the Home Office accounts line of 2.42bn retained).
- House of Commons Library briefings (parliamentary research, secondary): CBP-7274 on IHS (over 1.7bn in 2023/24; 6.9bn cumulative since 2015); CBP-9663 on UK aid and refugees; CBP-7445 on migrants and benefits. Not fetched.
- Full Fact: non-British/non-Irish share of UC claimants about 15.5% (January 2026), derived by Full Fact from the DWP file.
- Institute for Fiscal Studies (independent think tank), Green Budget chapter September 2026, "Migration and the public finance forecast": says lower net migration reduced the OBR 2030 tax revenue forecast by about 5bn, and that the ONS long-run projection fell from 340k to 230k. Method: IFS calculation from OBR/ONS publications.
- Oxford Economics 2018 study of EU migrants' fiscal contribution: older commissioned report, not fetched.
- Media and campaign figures on foreign nationals on UC: not official, not used.

## 9. Cross-source caveats

- Time bases differ: Home Office accounts are financial years (April-March); FCDO ODA series and Home Office immigration statistics use calendar years or years ending June; HMRC uses tax years; OBR migration is mid-year.
- Units differ: DWP and Home Office statistics are counts of people; accounts and ODA tables are GBP; MAC is per-person GBP and lifetime totals in 2022/23 prices with discounting.
- Gross vs net: Home Office DEL lines for Customer Services are net of fee income (negative); the Fees and Charges table is gross income vs full cost. HMRC amounts are gross taxes paid, not net contributions. Home Office Article 8 note excludes fees and IHS; MAC Figure_10 includes them.
- Outturn vs estimate vs forecast: ARA and Core Data Tables are outturn (plans flagged); FCDO is provisional; NAO, MAC and Home Office notes are estimates; OBR is a forecast.
- IHS is retained by the Home Office and passed to health bodies, so it is income of the Home Office accounts, not a measure of NHS cost.
- Status vocabularies differ: DWP "Humanitarian"/"Refugee"/"ILR"/"CTA"; Home Office "Illegal Entry Routes"/"Visas and Other Leave"/safe and legal routes; none maps one-to-one to another.
- Asylum claims by prior route (by claim date) and illegal-entry-route arrivals (by arrival date) are not directly comparable.

## 10. Suggested fixtures (smallest slices)

1. Home Office ARA 2025-26: Note 3 rows (visa income, IHS) and Trust Statement ISC row, as hand-keyed CSV with page refs (PDF is 18.7 MB; do not commit it).
2. Core Data Tables: rows 17, 19, 20 plus header rows from Total_departmental_spending.
3. DWP UC Table_1: header row and rows 8-17 for four recent months.
4. Home Office Asy_00a and Asy_09a.
5. FCDO Fig3.
6. MAC Table_9 and Figure_10.
7. OBR C2.6 rows 25-44 (columns A, F-H).
8. HMRC Table B1 row 33 and Table B5 row 67.
