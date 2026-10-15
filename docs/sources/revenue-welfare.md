# Revenue, taxpayer, welfare and labour sources

Status: scout pass, 2026-10-15. Files were downloaded to scratchpad `rev-dl/` and `rev-misc/` (not committed). Only URLs that returned HTTP 200 are recorded as fetched. Entries marked "unverified" were located on gov.uk or the ONS API but not downloaded.

Licence: the gov.uk and ONS pages are under the Open Government Licence v3.0 (https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/, fetched 200). I did not extract a verbatim quote from the page, so the quote is left blank rather than guessed.

## HMRC: tax receipts and NICs

- Landing: https://www.gov.uk/government/statistics/hmrc-tax-and-nics-receipts-for-the-uk (content API 200, updated 2026-09-22, first published 2013-10-03)
- Direct file: https://assets.publishing.service.gov.uk/media/6aa923f20420ac660805f7f2/NS_Table.ods (HTTP 200, 65,933 bytes, ODS)
- sha256: 2cadbec4c57e8626dae26c9f46975375eb2d0c07e40a94070a3c6ccc64403cab
- Sheets: Receipts_Monthly, Receipts_Annually, Expenditure_Monthly, Expenditure_Annually, Annual_Contribution_by_Tax
- Coverage: the annual sheets include years from the 1990s to 2026, so 2015-16 onward is covered (year tokens 1999 to 2026 found; not every sheet checked).
- Definitions: receipts only, not welfare. Use for revenue totals.
- Verdict: USABLE

## HMRC: income tax statistics (taxpayers and liabilities)

- Landing (collection): https://www.gov.uk/government/collections/income-tax-statistics-and-distributions (content API 200, updated 2026-07-15)
- Table 2.1, number of individual taxpayers: https://assets.publishing.service.gov.uk/media/6a54e2a9a4890e65cce64dd3/Table_2.1_Number_of_individual_Income_Tax_Payers.ods (HTTP 200, 13,000 bytes, ODS), sha256 caca39aca5c041081a56cf685a438769a6fbcbfe5b3f8ec8d498ec0afc2c9ed1. Sheet 2_1_IT_payers_by_demographic. Year tokens 1990 to 2027 appear in the file, but the time series per sheet is not yet checked. PARTIAL until checked.
- Table 2.5, liabilities by income range: https://assets.publishing.service.gov.uk/media/6a5a4b987eb057103bd946a5/Table_2.5_Income_Tax_liabilites_by_income_range.ods (HTTP 200, 14,575 bytes), sha256 d7e9b36cb585824bf69a3a60b32099b4a2fe213e53ea538401ae3acfaf5fb68c. Sheets are per year: 2_5_IT_Liabilities_2023-24 through 2026-27. The current edition covers only 2023-24 onward, so the 2015-16 to 2022-23 years must come from historic Table 2.5a: https://www.gov.uk/government/statistics/income-tax-liabilities-by-income-range--2 (landing, not downloaded).
- Collated Tables 2.1 to 2.6: https://assets.publishing.service.gov.uk/media/6a5a49b47eb057103bd946a4/Collated_Income_Tax_liabilities_statistics_tables_-_2.1_to_2.6.ods (HTTP 200, 93,036 bytes), sha256 40e1c7bb75d484132e8329fcac75f16e1a96305302fc422ee446a688d52bdbc2.
- Publication: "Income Tax liabilities statistics: tax year 2023 to 2024 to tax year 2026 to 2027", first published 2026-07-15.
- Definitions: liabilities are income tax only, not NICs or welfare.
- Verdict: PARTIAL (the historic 2015-16 to 2022-23 years are not yet downloaded from Table 2.5a)

## DWP: benefit expenditure and caseload tables

- Landing: https://www.gov.uk/government/publications/benefit-expenditure-and-caseload-tables-2026 (content API 200, first published 2026-04-14)
- Spring Forecast 2026 XLSX: https://assets.publishing.service.gov.uk/media/69dcdc8c6b695d635c34dcc4/outturn-and-forecast-tables-spring-forecast-2026.xlsx (HTTP 200, 1,707,003 bytes), sha256 11a591e4a2144ed6a686be6a9ded4e5d5b3b8d4887bd57c1ff0632bd251009de
- Spring Forecast 2026 ODS: https://assets.publishing.service.gov.uk/media/69dcdc56d3e08b8871b66628/outturn-and-forecast-tables-spring-forecast-2026.ods (HTTP 200, 1,646,400 bytes), sha256 705fb8fb5ace47e37eafe0b3817d5a6de538ce8fb2a67746e8f92d15ecd616e6
- Autumn Budget 2025 XLSX: https://assets.publishing.service.gov.uk/media/694931be888ddc41b48a546f/outturn-and-forecast-tables-autumn-budget-2025.xlsx (HTTP 200, 1,660,482 bytes), sha256 780167f86852bb0e0d5fc7f08564a9410a1515259e97135b7234e523b4e9123e
- Spring Statement 2025 XLSX: https://assets.publishing.service.gov.uk/media/68f8923724fc2bb7eed11ac8/outturn-and-forecast-tables-spring-statement-2025.xlsx (HTTP 200, 1,633,514 bytes), sha256 ad1294ea619098f9e80a33b8bb65f374460b580a6a20337d80db9d2852587874
- Sheets (Spring 2026): Contents, Notes, UK welfare, GB welfare, Benefit summary table, Table 1a (nominal expenditure by benefit, 1948/49 to 2029/30), Table 1b (real terms), Table 1c (caseloads), Tables 2a to 2c (by age), 3a to 3c (income-related), 4, 4(i), 4(ii) (disability and health), Non-DWP Welfare, plus per-benefit sheets.
- Coverage: 1948/49 to 2029/30, so 2015-16 onward is covered and includes forecasts.
- Definitions: the "UK welfare" tab covers the broader welfare total. The Welfare Cap applies to DWP AME excluding State Pension and most cyclical elements (JSA and the UC equivalent), plus some other departments' spend and Northern Ireland. COFOG social protection is not in these tables. Use the Welfare Cap column for fiscal-rule purposes and DWP AME for expenditure totals.
- Verdict: USABLE (Table 1a, Spring 2026 XLSX)

## DWP: Stat-Xplore (API)

- Docs: https://stat-xplore.dwp.gov.uk/webapi/online-help/Open-Data-API.html (HTTP 200, 15,215 bytes), sha256 09063b7f... (full hash: 9ad858d837f9b3cb5365b6fafe61d001981f71537cc8dc1775c78217d4aec640)
- Home: https://stat-xplore.dwp.gov.uk/ (HTTP 200), sha256 58d8090982a28b80244a16d9309475889ac90d5d4b16f963ddbfc615951bebea
- Key requirement: the docs say "In order to use the API, you must first obtain an API key. This is used for authorisation and must be submitted in an APIKey header in every request you make to the API." Registration is needed. The docs also mention rate limits.
- Licence: the Stat-Xplore data is not verified. The home page did not show an explicit OGL line in the text I pulled. Treat as unverified until the terms page is fetched.
- Verdict: PARTIAL (API is usable with a key; licence and rate limits are not verified)

## ONS: labour market (LMS)

- Series MGRZ (employment, 16+, seasonally adjusted, 000s): https://www.ons.gov.uk/generator?format=csv&uri=/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/timeseries/mgrz/lms (HTTP 200, 17,690 bytes, CSV), sha256 400b6004f2c9190c1f3f9a37ce64c43922e1757c3abec39a992f08dc72d2d49d. Release date 15-09-2026, next release 20 October 2026. Series runs from 1971 to 2026 APR/MAY/JUN.
- MGSX (unemployment rate): the ONS generator returned 429 (rate limited) on the path I tried. Unverified.
- Verdict: USABLE for MGRZ. MGSX PARTIAL until fetched.

## HMRC: PAYE RTI

- The gov.uk search found "Earnings and employment from Pay As You Earn Real Time Information, UK" monthly releases (for example, June 2026 published 2026-06-18, August 2026 published 2026-08-18). Example landing: https://www.gov.uk/government/statistics/earnings-and-employment-from-pay-as-you-earn-real-time-information-uk-june-2026 (unverified, not downloaded).
- Verdict: PARTIAL (landing pages located, data not fetched)

## ONS: effects of taxes and benefits on household income

- ONS API dataset: https://api.beta.ons.gov.uk/v1/datasets/tax-benefits-statistics (HTTP 200, sha256 2a1254ec8cac5b9c7d1606421c3d3f2bb613d1032e03f72a109e88334389bf1b)
- Latest version in the API is v3, released 2022-09-09 (https://api.beta.ons.gov.uk/v1/datasets/tax-benefits-statistics/editions/time-series/versions/3, HTTP 200, sha256 627f8ae355977d816f38ee011262ed73436f4e1be30bc9dbd3b7469a38e81336). This is stale.
- The newer bulletin on ONS.gov.uk was rate limited (429) and not fetched.
- Verdict: PARTIAL (API version is stale; newer bulletin not verified)

## Summary of verdicts

| Source | Verdict |
|---|---|
| HMRC receipts (NS_Table.ods) | USABLE |
| HMRC income tax Table 2.5, 2.1 | PARTIAL |
| DWP benefit expenditure (Spring 2026 XLSX) | USABLE |
| DWP Stat-Xplore API | PARTIAL |
| ONS LMS MGRZ | USABLE |
| ONS LMS MGSX | PARTIAL (unverified) |
| HMRC PAYE RTI | PARTIAL (unverified) |
| ONS taxes and benefits | PARTIAL (stale API v3) |

## Updates (later checks, same day)

### Licence wording
- gov.uk pages (HMRC receipts, DWP benefit tables 2026, PAYE RTI May 2026, HMRC income tax liabilities): footer reads "Open Government Licence v3.0".
- ONS dataset page (householddisposableincomeandinequality): "Open Government Licence v3.0".
- Stat-Xplore: no licence text found on https://stat-xplore.dwp.gov.uk/. Still open.

### HMRC receipts (coverage and update)
- Workbook last published 22 September 2026; next update per the workbook is due in October 2026.
- Coverage: the ODS was not parsed for year headers. The 10-year check is still open. It is PARTIAL until confirmed.

### PAYE RTI (update)
- Edition page: https://www.gov.uk/government/statistics/earnings-and-employment-from-pay-as-you-earn-real-time-information-uk-may-2026 (published 2026-05-19). The gov.uk content API showed no spreadsheet attachment.
- Verdict: PARTIAL. No data file hashed yet.

### ONS effects of taxes and benefits (update)
- Landing: https://www.ons.gov.uk/peoplepopulationandcommunity/personalandhouseholdfinances/incomeandwealth/bulletins/theeffectsoftaxesandbenefitsonhouseholdincome/latest (200)
- Dataset page: https://www.ons.gov.uk/peoplepopulationandcommunity/personalandhouseholdfinances/incomeandwealth/datasets/householddisposableincomeandinequality (200)
- File: https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/personalandhouseholdfinances/incomeandwealth/datasets/householddisposableincomeandinequality/financialyearending2025/hdiifye2025.xlsx (200)
  - sha256: 6438e9fbce43497bbf9a346a6d4a589ede1c552140dbaae34ab7c18f04856e83
  - Sheets include Cover Sheet, Index, Notes, Table 1 to Table 9 and more.
- Verdict: PARTIAL. Usable for household income by tax and benefit. Years and sheet definitions for the historical series are still open.

### ONS labour market (update)
- Still UNUSABLE through the legacy API (retired 25/11/2024). Beta catalogue at https://api.beta.ons.gov.uk/v1/datasets returned 200, but no "lms" dataset id was found. Verdict PARTIAL until a dataset id and file are hashed.

### Summary of verdicts
- HMRC receipts: PARTIAL. HMRC income tax stats: PARTIAL. DWP benefit expenditure: USABLE. Stat-Xplore: PARTIAL (free key). ONS labour market: PARTIAL (legacy API UNUSABLE). PAYE RTI: PARTIAL. ONS effects of taxes and benefits: PARTIAL.
