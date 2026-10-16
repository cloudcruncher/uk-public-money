# New sources 2: PESA, HMRC, OBR, devolved and local (verification log)

Checked 2026-10-15. Every file below was fetched with curl (browser User-Agent, retry on 429/5xx) into a fresh scratchpad directory (`.../scratchpad/pub2/`, not the repo) and read with `python3 -I` in a venv (openpyxl, pandas+odfpy). Only URLs that returned HTTP 200 are listed. Licence lines are quoted from the landing page. Figures quoted are copied from cells I read; none are estimated. "Smallest fixture" means the least a parser test needs (header rows plus the key rows, other cells blanked or dropped).

Format and earlier findings: see `docs/sources/new-sources.md` and `docs/sources/spend.md`.

## Verdict summary

| # | Target | Verdict |
|---|---|---|
| 1 | PESA 2026 UK-wide spending by function (Chapter 5 table 5.2 / 5.4; Chapter 9 CRA) | **USABLE** (Ch5 5.2 is UK-wide, to 2025-26 outturn; replaces England-only 10.1) |
| 2a | HMRC tax and NICs receipts (NS_Table.ods) | **USABLE** (annual 2006-07 to 2025-26, monthly to Aug 2026) |
| 2b | HMRC Income Tax liabilities statistics 2.1 to 2.6 | **USABLE** for who-pays shares and bands; 2024-25 on is projected |
| 2c | HMRC Personal Incomes Statistics 3.1 to 3.15a (2023-24) | **USABLE** (latest outturn is 2023-24; ODS only) |
| 3a | OBR EFO March 2026 receipts (table 3.8) | **USABLE** |
| 3b | OBR EFO March 2026 policy tables | **PARTIAL** (policy-measure scorecard, not a series) |
| 3c | OBR FRS July 2026 annexes and chapter workbooks | **USABLE (found)**: xlsx exist on assets.publishing; the no-access page is bypassed. Annex chart sheets hold only charts; data tables are in chapter workbooks |
| 4a | Scotland GERS 2025-26 tables | **USABLE** |
| 4b | MHCLG LA revenue outturn (RS, first release tables, multi-year CSV) | **USABLE** (England only) |

Licence note for all gov.uk / gov.scot files: the page footer reads "All content is available under the Open Government Licence v3.0, except where otherwise stated" (gov.uk) and "All content is available under the Open Government Licence v3.0, except for graphic assets and where otherwise stated" (gov.scot). OGL v3: YES. OBR: the copyright page https://obr.uk/legal-pages/copyright/ (HTTP 200) reads "You may use and re-use the information featured on this website (not including logos) free of charge in any format or medium, under the terms of the Open Government Licence". OGL: YES (this resolves the earlier "UNVERIFIED" for OBR).

---

## 1. HM Treasury PESA 2026 (UK-wide by function)

- Landing: https://www.gov.uk/government/statistics/public-expenditure-statistical-analyses-2026 (HTTP 200, text/html). Content API: https://www.gov.uk/api/content/government/statistics/public-expenditure-statistical-analyses-2026 (HTTP 200).
- Publication date: first published and last updated 2026-07-16.
- Licence: "Open Government Licence v3.0" (page footer).
- Finding: **Chapter 5 is UK-wide public sector expenditure on services by function.** Chapter 10 tables 10.1 to 10.10 are per country/region (10.1 = England only, as already known). Chapter 9 is the Country and Regional Analysis (CRA) summary.

### 1a. Chapter 5 tables (best for "out of every £100", UK-wide)

- Direct file: https://assets.publishing.service.gov.uk/media/6a5772f59e63154454413701/PESA_2026_CP_Chapter_5_tables.xlsx
- HTTP 200, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, 72078 bytes, sha256 `ccb4539bb837c2b6a7f9509da49bd409eb9e5a910f3332311b494291fbd33107` (matches spend.md).
- Sheets: 5_1, 5_1a, 5_1b (2025-26 by department group and function, current/capital), 5_2, 5_3, 5_4, 5_5, 5_6, 5_3_checks.
- Sheet `5_2` "Table 5.2 Public sector expenditure on services by sub-function, 2021-22 to 2025-26", £ million, "Accredited Official Statistics". Header: row 5 = years in C:G (`2021-22`, `2022-23`, `2023-24`, `2024-25`, `2025-26`), row 6 = `outturn` in each. Labels in column B. All five years are outturn, so **2025-26 is covered**.
- Key rows (column G = 2025-26, £ million; column C = 2021-22):

| Row | Label (col B) | 2021-22 (C) | 2025-26 (G) |
|---|---|---|---|
| 20 | Total general public services | 109222 | 165504 |
| 14 | 1.7 Public debt transactions | 72703 | 130305 |
| 27 | Total defence | 48681 | 65418 |
| 37 | Total public order and safety | 39756 | 55720 |
| 56 | Total economic affairs | 97734 | 93959 |
| 64 | Total environment protection | 13785 | 19157 |
| 74 | Total housing and community amenities | 15273 | 22470 |
| 79 | Total health | 216237 | 257542 |
| 87 | Total recreation, culture and religion | 12762 | 15053 |
| 99 | Total education | 100148 | 125721 |
| 121 | Total social protection | 300292 | 407270 |
| 130 | Total EU transactions | -1946 | -166 |
| 131 | Public sector expenditure on services | 951945 | 1227648 |
| 132 | Accounting adjustments | 88943 | 132474 |
| 133 | Total Managed Expenditure (11) | 1040888 | 1360122 |

  Check: the ten function totals for 2025-26 sum to 1,227,814; plus EU transactions (-166) gives 1,227,648 = row 131. Row 133 TME 1,360,122 agrees with Chapter 4 table 4.1 (1360.1, £bn). Social protection sub-rows: 10.2 Old age row 105 (G 172180; "of which: pensions" row 107 = 154858); 10.1 Sickness and disability row 102 (84330); 10.7 Social exclusion n.e.c. row 116 (86773; includes Universal Credit and tax credits, "of which: family benefits, income support, Universal Credit and tax credits" row 118 = 84272). Sub-function labels in the file contain `of which:` indents with irregular spacing; strip and match by row label, not position.
- Sheet `5_4`: public sector current and capital expenditure by function, £ million, same year header (rows 5-6, C:G). Row 27 "Total public sector current expenditure on services" G = 1084664; row 48 capital G = 142984; row 51 total G = 1227648; row 53 TME G = 1360122. Current rows 8-26 by function; capital rows 30-47.
- Revision: 2025-26 is the first outturn in this edition; earlier years are restated edition to edition (see spend.md for the 2015-16 example). Record the edition (PESA 2026, July 2026).
- Verdict: **USABLE**. Reason: UK-wide, five outturn years to 2025-26, internally consistent with 4.1. Caveat: the function list is COFOG level 1 plus HMT sub-functions; "Economic affairs" fell from 124545 (2022-23) to 94408 (2023-24) because energy support schemes ended (footnote 5 says 2022-23 was affected by cost of living measures).
- Smallest fixture: sheet `5_2` rows 1-6 (title, unit, header years) plus rows 14, 20, 27, 37, 56, 64, 74, 79, 87, 99, 121, 130, 131, 133 (columns B:G only).

### 1b. Chapter 9 (CRA summary, per region/country)

- Direct file: https://assets.publishing.service.gov.uk/media/6a5773582cbe5d1c179a6549/PESA_2026_CP_Chapter_9_tables.xlsx
- HTTP 200, spreadsheetml, 296894 bytes, sha256 `3d3512975f49996ceb1fda90639d1d3d557c23cf5f651214910df2d2ed375ce0`.
- Sheets 9.1a to 9.21. Years: 2020-21 to 2024-25 (outturn; one year behind Chapter 5). Sheet `9.1a` rows 4-20: header row 4 (B:F = 2020-21..2024-25 £ million; G:K = per cent), rows 5-13 English regions, row 14 Total England, rows 15-17 Scotland, Wales, Northern Ireland, row 18 "UK identifiable expenditure", row 19 "Outside UK", row 20 "Total identifiable expenditure"; rows 25-29: Identifiable, Non-identifiable, Public sector expenditure on services, Accounting adjustments, Total Managed Expenditure. 2024-25 values: UK identifiable 935588 (B..F, F = 2024-25), England 769898, Scotland 86328, Wales 48293, NI 31069, TME 1288053.
- Function tables: 9.5 general public services, 9.6 defence, 9.7 public order, 9.8 economic affairs, 9.9 environment, 9.10 housing, 9.11 health, 9.12 recreation, 9.13 education, 9.14 social protection; 9.15 per head by function (UK).
- Verdict: **USABLE for regional splits only**. Uses "identifiable" expenditure, so it is not a total of public spending; do not use as the national "£100" split (use 1a).
- Smallest fixture: sheet `9.1a` rows 1-20 and 24-29.

### 1c. Chapter 10 tables 10.1 to 10.10

- Already inspected (spend.md). 10.1 = England only, 10.2 Scotland, 10.3 Wales, 10.4 Northern Ireland (each "Total identifiable expenditure on services in X by sub-function (1), 2020-21 to 2024-25", £ million), 10.5-10.8 per head, 10.9-10.10 English regions for 2024-25. Not UK-wide. Superseded by 1a for the national split.

---

## 2. HMRC

### 2a. HMRC tax receipts and National Insurance contributions for the UK (NS_Table)

- Landing: https://www.gov.uk/government/statistics/hmrc-tax-and-nics-receipts-for-the-uk (HTTP 200, text/html).
- Direct file: https://assets.publishing.service.gov.uk/media/6aa923f20420ac660805f7f2/NS_Table.ods
- HTTP 200, `application/vnd.oasis.opendocument.spreadsheet`, 65933 bytes, sha256 `2cadbec4c57e8626dae26c9f46975375eb2d0c07e40a94070a3c6ccc64403cab`. (No xlsx offered; ODS only.)
- Publication date: first published 2013-10-03; last updated 2026-09-22 (content API). Monthly series runs to August 2026.
- Licence: "Open Government Licence v3.0" (footer).
- Sheets: Cover_Sheet, Table_Notes, Receipts_Monthly, Receipts_Annually, Expenditure_Monthly, Expenditure_Annually, Annual_Contribution_by_Tax.
- `Receipts_Annually` (Table 2, £ million, cash basis): header at spreadsheet row 6 (column A "Table 2 HMRC Receipts by financial year"), data rows 7-26 = `2006 to 2007` .. `2025 to 2026`, row 27 "End of worksheet". Columns: B Total Paid Over, C Total HMRC Receipts, D Income Tax, E PAYE, F Self-Assessment, G Capital Gains Tax, H Apprenticeship Levy, I National Insurance Contributions, J PAYE NIC1 employer, K PAYE NIC1 employee, L SA NIC2&4, M Value Added Tax, N Corporation Tax, Z Hydrocarbon Oil (fuel duties), AA Inheritance Tax, AC Stamp Duty Land Tax, AE Tobacco, AK Air Passenger Duty, AT Customs Duties, and others to AU Penalties (47 columns). Suppressed cells appear as `[X]`.
- 2025 to 2026 row (row 26): Total Paid Over 919111; Total HMRC Receipts 937763; Income Tax 326932; PAYE 278237; SA 54071; CGT 24310; NICs 200829 (employer 143903, employee 49404); VAT 179861; Corporation Tax 95105; Fuel duties 24558; IHT 8467; SDLT 15159.
- Cross-check: OBR EFO March 2026 table 3.8 forecast for 2025-26 has income tax 329.3, NICs 200.08, VAT 180.17, CT 95.51, Total HMRC 936.88 (£bn); HMRC outturn is close but not identical (different vintage and basis).
- `Receipts_Monthly`: header at row 6, monthly rows, last data row `August 2026` (Total Paid Over 66216; Total HMRC Receipts 68886).
- Revision behaviour (Table_Notes): NICs "subject to revision"; Corporation Tax "subject to change, due to a lag in return data"; tax credits provisional. Latest year is first-release and gets restated.
- Verdict: **USABLE** for tax by type 2006-07 to 2025-26 (HMRC receipts; not the same as OBR "current receipts", which add business rates, council tax etc.).
- Smallest fixture: `Receipts_Annually` rows 6 (header), 25-26 (two years), columns A:N plus Z, AA, AC. Plus `Table_Notes` is not needed.

### 2b. Income Tax liabilities statistics (who pays income tax)

- Landing: https://www.gov.uk/government/statistics/income-tax-liabilities-statistics-tax-year-2023-to-2024-to-tax-year-2026-to-2027 (HTTP 200).
- Direct file: https://assets.publishing.service.gov.uk/media/6a5a49b47eb057103bd946a4/Collated_Income_Tax_liabilities_statistics_tables_-_2.1_to_2.6.ods
- HTTP 200, ODS, 93036 bytes, sha256 `40e1c7bb75d484132e8329fcac75f16e1a96305302fc422ee446a688d52bdbc2`.
- Publication date: 2026-07-15 (09:30). "Next publication date: May/June 2027." (Contents sheet).
- Licence: "Open Government Licence v3.0" (footer).
- Years: 1999-00 to 2026-27. Contents: "All years to the 2023 to 2024 tax year are outturn data, tax years 2024 to 2025 through to 2026 to 2027 are projected estimates, projected from the 2023 to 2024 SPI. SPI years are final outturns and projection years are provisional and will be revised until they become superceded by the S[PI]..."
- Source: Survey of Personal Incomes 2023-24.
- Sheets (selected): `2_1_IT_payers_by_demographic` (number of payers by marginal rate, sex, age); `2_2_Taxpayers_by_demographic_*` (EN, NE, NW, YH, EM, WM, EE, LD, SE, SW, WA, SC, NI); `2_4_Taxpayer_share_inc_pretax`, `2_4_Taxpayer_share_inc_posttax`, `2_4_Taxpayer_share_tax`, `2_4_Taxpayer_inc_quantiles`; `2_5_IT_Liabilities_2023-24 / 2024-25 / 2025-26 / 2026-27` (liability by income range, thousands of payers and £ million); `2_6_IT_by_income_source_*`.
- `2_4_Taxpayer_share_tax`: header at spreadsheet row 2: A Tax year, B Bottom 1%, C Bottom 5%, D Bottom 10%, E Bottom 25%, F Bottom 50%, G Top 50%, H Top 25%, I Top 10%, J Top 5%, K Top 1%, L "Total Income Tax for all Income Tax payers in £ billion". Last rows: `2024 to 2025` top 10% = 47.5, top 1% = 27.2, total £304bn; `2025 to 2026` top 10% = 47.1, top 1% = 26.8, total £329bn; `2026 to 2027` top 10% = 46.9, top 1% = 26.6, total £347bn. Percent shares (not fractions).
- `2_5_IT_Liabilities_2025-26`: header row 3 (Range of total income lower limit; number and liability for savers, basic, higher, additional rate payers, ...). Row for lower limit 12570 shows 48 savers-rate payers (thousands) with liability 4 (£m); last row "All Ranges" shows 437 savers-rate payers, liability 558, basic rate payers 30900 (thousands). Some cells read `[no estimate]`.
- Verdict: **USABLE** for "who pays" shares by income group (2.4) and by income band (2.5) up to 2023-24 outturn; later years are projections and must be labelled as such.
- Smallest fixture: sheet `2_4_Taxpayer_share_tax` rows 1-3 and the last 3 data rows; sheet `2_5_IT_Liabilities_2025-26` rows 1-5 and the "All Ranges" row.

### 2c. Personal Incomes Statistics (SPI) 2023-24

- Landing: https://www.gov.uk/government/statistics/personal-incomes-statistics-for-the-tax-year-2023-to-2024 (HTTP 200).
- Publication date: 2026-04-29 (09:30).
- Licence: "Open Government Licence v3.0" (footer).
- Files (HTTP 200, ODS):
  - Tables 3.1 to 3.11: https://assets.publishing.service.gov.uk/media/69f1f12d2fae53a03709682f/Collated_Tables_3_1_to_3_11_2324.ods, 166693 bytes, sha256 `ad063b06b2bdeef8600dbbb09d48153337a4966f8c7eea50df7a2e0304ebd73e`.
  - Tables 3.12 to 3.15a: https://assets.publishing.service.gov.uk/media/69f1f17cc42061e837e3ac3b/Collated_Tables_3_12_to_3_15a_2324.ods, 926081 bytes, sha256 `f70e210eb2931d9a6da5f8b6fa184b902b51ef9e2c9fb3588323907647d7672c` (not inspected beyond download).
  - Table 3.1a percentile points: https://assets.publishing.service.gov.uk/media/69f2082f0bb62e692c5d6e35/Table_3.1a_2324.ods, 42290 bytes, sha256 `00e534504deaee38b4435ca83b8c3e32c698b29c4d2bac5686f53e1d8d6da193`. (Landing: https://www.gov.uk/government/statistics/percentile-points-from-1-to-99-for-total-income-before-and-after-tax, HTTP 200.)
- Years: Table 3.1a 1999-00 to 2023-24 (2008-09 not available per Notes_3_1a); other tables are single-year 2023-24.
- `Table_3_1a_before_tax`: header at spreadsheet row 5 (A "Percentile point for total income before tax", B.. = `1999 to 2000` ...), rows 6-104 = percentile points 1 to 99 in £. First row (percentile 1, 1999 to 2000) = 4600; percentile 97 = 56600. Based on UK taxpayers only.
- `Table_3_11` (income and tax by gender, region and country): header row 5 (A Region or country, B Population, C Range of total income lower limit, D.. income-source number/amount pairs); rows from 6 (`United Kingdom`, `All`, lower limit 12570 ...). Region sizes should be treated as indicative (Notes_3_11).
- Verdict: **USABLE** for income percentiles and the taxpayer income distribution (outturn to 2023-24). Latest outturn is 2023-24, so 2.4 projections in 2b are the only later years.
- Smallest fixture: `Table_3_1a_before_tax` rows 1-8 plus the last 3 data rows (A:D and last two columns).

---

## 3. OBR

Browser User-Agent required (bare curl gets 403). Licence: OGL (see top).

### 3a. EFO March 2026 detailed forecast tables, receipts

- Landing: https://obr.uk/efo/economic-and-fiscal-outlook-march-2026/ (HTTP 200).
- Direct file: https://obr.uk/docs/d055fbf02d5b3g6jq8l2/efo-march-2026-detailed-forecast-tables-receipts.xlsx
- HTTP 200, spreadsheetml, 187899 bytes, sha256 `f65b6cb7f96931d4abd85940794eb60f6f65afca8bbf16c74a4548bf92766a28` (same as in new-sources.md; now inspected).
- Publication date: March 2026 (title: "March 2026 Economic and fiscal outlook – detailed forecast tables: receipts"; exact day not read).
- Sheets: Contents, 3.1 Other HMRC taxes, 3.2 Other taxes, 3.3 Other receipts, 3.4 Income tax and NICs forecast (detailed), 3.5, 3.6 Onshore CT, 3.7 Property transactions taxes, **3.8 Current receipts (on a cash basis)**, 3.9 to 3.22 (APD, betting, tobacco, alcohol, IHT, oil and gas, VAT gap, personal tax measures yield, threshold freezes, thresholds, fiscally neutral receipts).
- Sheet `3.8`, £ billion. Year header row 5: D = `2024-25` (row 4 label "Outturn"), E = `2025-26` (row 4 "Forecast", applies to E:J), F `2026-27`, G `2027-28`, H `2028-29`, I `2029-30`, J `2030-31`. Labels in B (or C for "of which").
- Key rows (D 2024-25 outturn / E 2025-26 / J 2030-31):

| Row | Series | D | E | J |
|---|---|---|---|---|
| 7 | Income tax (gross of tax credits) | 302.8 | 329.3 | 428.77 |
| 9 | of which PAYE (col C label) | 259.76 | 278.23 | 358.05 |
| 10 | of which Self assessment | 48.16 | 55.87 | 76.98 |
| 12 | National insurance contributions | 172.52 | 200.08 | 244.33 |
| 13 | Value added tax | 170.99 | 180.17 | 222.2 |
| 14 | Corporation tax | 90.92 | 95.51 | 121.12 |
| 21 | Fuel duties | 24.36 | 24.24 | 25.74 |
| 22 | Capital gains tax | 13.69 | 21.8 | 34.9 |
| 23 | Inheritance tax | 8.29 | 8.66 | 14.71 |
| 24 | Stamp duty land tax | 13.88 | 15.41 | 26.16 |
| 51 | Total HMRC | 858.62 | 936.88 | 1188.09 |
| 52 | Vehicle excise duties | 8.21 | 9.4 | 13.34 |
| 53 | Business rates | 32.38 | 34.05 | 42.46 |
| 54 | Council tax | 46.6 | 50.06 | 66.44 |
| 64 | Current receipts | 1139.04 | 1235.25 | 1551.48 |

  Note: "All tax lines prior to accruals adjustments on tax line are on a cash basis rather than an accrued basis." Labels for sub-lines sit in column C; labels for top lines in column B.
- Revision: restated each Budget/EFO; keep the "March 2026" release label.
- Verdict: **USABLE** (receipts by tax, 2024-25 outturn plus forecast to 2030-31).
- Smallest fixture: sheet `3.8` rows 3-14, 21-24, 51-54, 64 (columns B:J).

### 3b. EFO March 2026 detailed forecast tables, policy

- Direct file: https://obr.uk/docs/d055fbf02d5b3g6jq8l2/efo-march-2026-detailed-forecast-tables-policy.xlsx
- HTTP 200, spreadsheetml, 64437 bytes, sha256 `5263b901827d887bc87b9f49f627780c789a594e48897d194d90463e61def763`.
- Sheets: Contents (a long sheet of 1956 rows by 26 columns in the file), `1.1` "Table 1.1: Breakdown of policy decisions since November 2025" (£ million).
- `1.1` layout: year header at row 5, I:N = `2025-26` .. `2030-31` (row 4 "Forecast", row 3 "£ million"); G = Head (for example "Current DEL"), H = Category (for example "PSCE in RDEL"); measure number in C, name in D; each measure is followed by a `Total` row. Example: measure 1 "Additional funding for SEND" row 8, 2028-29 = -4111.
- Verdict: **PARTIAL**. A list of individual policy measures with annual costs, not a series; only useful for a "recent policy changes" note. Years/sheets were read only for sheet 1.1.

### 3c. Fiscal Risks and Sustainability (FRS) July 2026 charts and tables

- Landing: https://obr.uk/frs/fiscal-risks-and-sustainability-july-2026/ (HTTP 200, text/html).
- Finding: the earlier session landed on the `obr.uk/no-access/download-id/24953/` access page; the cause was not established. In this session, fetching **`https://obr.uk/download/<slug>/` without the `?tmstv=` query** with the browser UA redirects (HTTP 200 after redirects) straight to the xlsx on assets.publishing.service.gov.uk. That is the real file; no browser tools were needed.
- Files (all HTTP 200, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`):

| Workbook | Redirected file URL | Size (bytes) | sha256 |
|---|---|---|---|
| Annexes (B to D) | https://assets.publishing.service.gov.uk/media/6a4cb54cc5aa1b17abab40d7/7._Fiscal_risks_and_sustainability_July_2026_charts_and_tables_-_Annexes.xlsx (via https://obr.uk/download/july-2026-fiscal-risks-and-sustainability-charts-and-tables-annexes/) | 418445 | `03441907650a7a251e403f048ce5ae0577b186d14e3609f27e755353d3dcea71` |
| Chapter 2 | https://assets.publishing.service.gov.uk/media/6a4cb54dc5aa1b17abab40d8/3._Fiscal_risks_and_sustainability_July_2026_charts_and_tables_-_Chapter_2.xlsx | 1185180 | `aa30ff1f70825bf6d39aa85fdf22514669544430bce41d42296d946a77e580d3` |
| Chapter 3 | https://assets.publishing.service.gov.uk/media/6a4cb54db7203c4c023fd29a/4._Fiscal_risks_and_sustainability_July_2026_charts_and_tables_-_Chapter_3.xlsx | 1639964 | `7ae2183f3f7a3eeee1a1447c73e3fac206722b0bf757c9773b5f30120b015c2b` |
| Chapter 4 | https://assets.publishing.service.gov.uk/media/6a4cb54dd200ca05e289e65b/5._Fiscal_risks_and_sustainability_July_2026_charts_and_tables_-_Chapter_4.xlsx | 947052 | `2be91e5624a0e795b767a5d429d043c7ca765d081bff40413c4ca67483757159` |
| Chapter 5 | https://assets.publishing.service.gov.uk/media/6a4cb54d4889d85e75ab40e1/6._Fiscal_risks_and_sustainability_July_2026_charts_and_tables_-_Chapter_5.xlsx | 394872 | `ea9f27a43f91967d2a28d2e4beb843061b8f88bb5ad7502e64c587eb7b043639` |

  Executive summary and Introduction workbook links exist on the landing page but were not fetched. Redirecting slugs: `july-2026-fiscal-risks-and-sustainability-charts-and-tables-chapter-2` .. `-chapter-5`.
- Publication date: July 2026 (report PDF already recorded in new-sources.md).
- Contents:
  - Annexes workbook sheets: Contents, Annex, TB.1/TB.2 (baseline policy assumptions), CC.1-CC.4 (age profiles), TD.1 and CD.1 (debt assumptions). The CC and CD chart sheets that I opened (CC.3) have a title only and no cell data (the data is probably in the chart objects); TB.1, TB.2 and TD.1 are text/number tables.
  - Chapter 3 sheet `T3.1` "Baseline primary spending scenario", per cent of GDP; header row 6: C = `2025-26`, D = `2030-31`, F = `2035-36`, G = `2045-46`, H = `2055-56`, I = `2065-66`, J = `2075-76`. Row 7 Health: 8.35, 8.36, 8.96, 10.07, 11.16, 12.21, 13.46. Row 8 Adult social care 1.24 (2025-26); row 9 Education 4.48; row 10 State pension 4.79 → 8.61 (2075-76); row 11 Other welfare benefits 6.11.
  - Chapter 5 sheet `T5.1` "Baseline scenario: fiscal aggregates", per cent of GDP, same header row 6: row 7 Public sector current receipts 40.44 (2025-26) → 42.66 (2075-76); row 8 TME 44.79 → 62.19; row 10 PSND 94.31 → 300.41; row 14 net interest 2.95 → 12.2.
  - Chapter 4 sheets C4.1..C4.4 are chart sheets (C4.1 "Public sector current receipts as a share of GDP" held no cells in rows 1-8 when read).
  - Chapter 2 sheet `T2.1` "Summary of key long-term demographic and economic variables".
- Revision: the FRS projections are rebuilt each edition; "Estimates are consistent with the March 2026 Economic and fiscal outlook".
- Verdict: **PARTIAL to USABLE**. Table sheets (T2.1, T3.1, T5.1, TB.x, TD.1) are parseable; chart sheets are not reliably data. The long-term projection tables are only needed for a "long-run" page.
- Smallest fixture: `T3.1` rows 1-12 and `T5.1` rows 1-14 (columns B:J).

### 3d. Devolved tax and spending forecasts (found while checking)

- URL: https://obr.uk/download/march-2026-devolved-tax-and-spending-forecasts/ → https://obr.uk/docs/d055fbf02d5b3g6jq8l2/efo-march-2026-devolved-tax-and-spending.pdf, HTTP 200, `application/pdf`, 388806 bytes, sha256 `ccabd6af2d5f11fb675b04130a6fa18209e717a0c1b74ddfb8358544a048babc`. PDF (43 pages), not inspected. **UNUSABLE** as data until tables are extracted (PDF).

---

## 4. Devolved and local

### 4a. Scottish Government GERS 2025-26

- Landing: https://www.gov.scot/publications/government-expenditure-revenue-scotland-2025-26/ (HTTP 200, text/html). Supporting documents page: https://www.gov.scot/publications/government-expenditure-revenue-scotland-2025-26/documents/ (HTTP 200).
- Publication date: "Published 12 August 2026" (page); the tables cover sheet says "originally published at 09:30 on 12 August 2026".
- Licence: "All content is available under the Open Government Licence v3.0, except for graphic assets and where otherwise stated".
- Files (HTTP 200, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=UTF-8`):
  - Tables: https://www.gov.scot/binaries/content/documents/govscot/publications/statistics/2026/08/government-expenditure-revenue-scotland-2025-26/documents/gers-2025-26-tables/gers-2025-26-tables/govscot%3Adocument/gers-2025-26-tables.xlsx, 477241 bytes, sha256 `61e2e8f64b280a57c61423d523c09c9252aa2f002aab7f638c129e57dcd55d9f`.
  - Supplementary expenditure database: same path with `gers-2025-26-supplementary-data-expenditure-database/.../gers-2025-26-supplementary-data-expenditure-database.xlsx`, 2398794 bytes, sha256 `42cb4889c9d39a261186334f3e8871c5d83956c65fe1950a4cba0c5ec208afe3` (not inspected).
  - Main report PDF listed on the documents page (not fetched).
- Years: 1998-99 to 2025-26.
- Sheets (tables workbook): Cover_page, Table_of_contents, Notes, Figures 1-3, Chart_1.1, Table_1.1 to 1.7 (revenue), Chart_2.1, Table_2.1 to 2.3 (North Sea), Chart_3.1, Table_3.1 to 3.12 (expenditure), Chart_4.1/4.2, Table_4.1 to 4.4 (devolved taxes/social security).
- Key series:
  - `Table_1.1` "Total Revenue": header in row 2 (B.. = `1998-99` .. `2025-26`, last column = 2025-26). Row 3 "Scotland (£ million)": 2023-24 90543.58, 2024-25 91945.29, 2025-26 98261.89. Row 4 Scotland excluding North Sea: 86173.72, 88377.24, 95108.94.
  - `Table_3.1` "Total Public Sector Expenditure": header row 2; row 3 "Scotland (£ millions)": 2023-24 112340, 2024-25 117887, 2025-26 123566; row 4 Share of UK (%) ≈ 0.091 (fraction, not percent).
  - `Table_3.3` "Total Expenditure: Scotland 2025-26": col B £ million, col C share; rows by COFOG function, e.g. Health 21120.07 (17.1 per cent), Social protection 36502.23 (29.5 per cent), Education and training 11976.17, Defence 5234.08, Total Expenditure 123565.53.
  - `Table_1.3` "Revenue: Scotland and UK 2025-26": Income tax (gross of tax credits) Scotland 22071.78, UK 330250 (Scotland 6.7 per cent of UK).
  - Fractions are stored as decimals in several tables (0.091 = 9.1 per cent) while headers say "%"; test the ranges.
- Revision: GERS restates earlier years each August (and the UK tax and spending bases follow PESA/OBR vintages). Record the 2025-26 edition.
- Verdict: **USABLE** for Scotland totals and function split; it complements PESA CRA 2024-25.
- Smallest fixture: `Table_3.1` rows 2-3 (first and last three columns) and `Table_3.3` rows 1-21. Note openpyxl `read_only` mode misreports dimensions on these sheets; load without `read_only`.

### 4b. MHCLG local authority revenue outturn (England)

- Collection: https://www.gov.uk/government/collections/local-authority-revenue-expenditure-and-financing (HTTP 200, content API).
- First release page: https://www.gov.uk/government/statistics/local-authority-revenue-expenditure-and-financing-england-2025-to-2026-first-release (HTTP 200), published 2026-09-17.
- Licence: "Open Government Licence v3.0" (footer).
- Files (HTTP 200):
  - First-release Table 1a/1b: https://assets.publishing.service.gov.uk/media/6aa91ca70420ac660805f7d9/RO_2025-26_Table_1a_1b.ods, ODS, 9293 bytes, sha256 `2807508a4030dedffd0c3377e89dd829b40aada18739ba2cf245a12288b23488`. Sheet `Table_1a` "Service expenditure net of sales, fees and charges and of other income, 2021-22 to 2025-26 (cash terms)", £ million; header row 6 (A Service Category, B:F = `2021-22` .. `2025-26`). Row 19 "Total Service Expenditure": 107050.069, 113480.231, 123752.58, 134233.179, 144434.26 (2025-26, F). Rows: Education 49402.61; Social care 44375.10; Highways and transport 5650.69; Police 17823.60; Fire & rescue 2991.18; Central services 3794.38. `Table_1b` is the real-terms version (2025-26 prices).
  - Table 5 (financing 2021-22 onward): https://assets.publishing.service.gov.uk/media/6aa91d7a0420ac660805f7e4/RO_2025-26_Table_5.ods, ODS, 6016 bytes, sha256 `58c9b36f1eb650882bde20bace8b25fe430862645f46df2520d86f0188cc7ad9` (downloaded, contents not read).
  - Revenue Outturn Summary (RS) 2025-26 by local authority: https://assets.publishing.service.gov.uk/media/6ab26f5dfe72ed1e2b02ee72/RS_LA_Data_2025-26_data_by_LA.ods, ODS, 389549 bytes, sha256 `941c2fbd2dbafc4365cb535639a3c7504a0f54706833c6677e0c2f5ce380fc4a`. Sheets: Front_Page, Notes, LA_drop-down, `RS_LA_Data_202526` (434 rows by 162 columns, £ thousand; header row 7: E-code, ONS Code, Local authority, Notes, Class, Detailed Class, Certification, then "Service Expenditure - Education services", "Highways and transport services", "Children Social Care", "Adult Social Care [note 2]", ...). Notes sheet: "RO return not received in time for publication. England totals have been estimated by also drawing on grant allocations ...". 36 authorities "not submitted" in the time series for 202603.
  - Multi-year time series CSV (updated 2026-09-28): https://assets.publishing.service.gov.uk/media/6ab26ffffe72ed1e2b02ee74/Revenue_Outturn_time_series_data_v4.csv, `text/csv`, 24337741 bytes, sha256 `7cd3a815b3bcb2717be0ce241f22ff01b7b3f8ba85595233248d462e33198657`. 3,930 data rows, 2,586 columns. Columns: year_ending (e.g. 201803 .. 202603, YYYYMM), ONS_code, LA_LGF_code, LA_name, status (`submitted`, `not submitted`, `total`), LA_class, LA_subclass, then `RS_*`, `RG_*` etc. fields (for example `RS_edu_net_exp`, `RS_asc_net_exp`). Aggregate rows have status `total` per class (13 for 2026). Metadata: https://assets.publishing.service.gov.uk/media/6ac3c069241ecad55a9793ae/Revenue_Outturn_metadata.ods (listed in the API, not fetched).
- Years: first release 2021-22 to 2025-26; CSV from 201803 (2017-18) to 202603.
- Coverage: England only (devolved nations publish separately). Local government is in PESA 5_2 already; this adds service detail by council.
- Revision behaviour: "first release" (Sept 2026) is followed by later releases (the 2024-25 series reached its "third release" by 2026-06-11); figures are provisional until then.
- Verdict: **USABLE** (England). Prefer the CSV for a parser (flat, one row per authority-year). The ODS tables are for a quick England total. Beware that 2,586 columns make the CSV heavy; read with `usecols`.
- Smallest fixture: `Table_1a` rows 6 and 19 and a few service rows; or the CSV header plus 2-3 rows (class `total`, year_ending 202503 and 202603) restricted to `year_ending, LA_name, status, RS_edu_net_exp, RS_asc_net_exp` columns.

---

## Not done / caveats

- No ONS or HMRC percentile cross-check against PESA beyond the receipts comparison above.
- HMRC "Statistics on tax receipts" other tables (for example NIC receipts in the NI Fund, "Income tax receipts statistics to tax year 2019 to 2020") were seen in search results (https://www.gov.uk/government/statistics/income-tax-receipts-statistics-to-tax-year-2019-to-2020) but not fetched. Not needed given 2a and 2b.
- Annex chart sheets in the FRS workbooks (CC.x, CD.x, C4.x) appear to hold chart objects without cell data; I read only CC.3, C4.1, T3.1, T5.1.
- Scotland supplementary expenditure database and MHCLG Table 5, RO1-RO6 files were downloaded or listed but not read.
