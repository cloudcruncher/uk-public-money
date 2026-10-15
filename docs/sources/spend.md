# Spending and macro sources: verification log

Checked 2026-10-15. Files were fetched with curl into scratchpad `spend-dl` (not committed). Hashes are sha256 of the files as fetched today. "UNVERIFIED" means not fetched, or fetched but not inspected.

## HMT Public Expenditure Statistical Analyses (PESA)

- Landing: https://www.gov.uk/government/collections/public-expenditure-statistical-analyses-pesa (HTTP 200, text/html)
- Edition API used: https://www.gov.uk/api/content/government/statistics/public-expenditure-statistical-analyses-{2016..2026} (all HTTP 200, application/json)
- Licence: the gov.uk page footer reads "Open Government Licence v3.0". OGL v3: YES.
- Editions: 2016 (first published 2016-07-21, updated 2016-09-14) through 2026 (first published 2026-07-16). The 2025 edition has a December 2025 update.

| File (direct URL, HTTP 200) | Format | Content-Type | Size (bytes) | sha256 | Sheets / coverage |
|---|---|---|---|---|---|
| assets.publishing.service.gov.uk/media/5a75b2f4ed915d6faf2b5027/PESA_2016_Chapter_1_Tables.xlsx | xlsx | spreadsheetml | 164600 | 16289df818e9093f23aee17f454d76c96a97b4f0c3749c75d27e90a639d34b45 | Table 1.1 to 1.15 (TME, 2011-12 to 2015-16 outturn) |
| .../5a80cbd1ed915d74e33fc74c/PESA_2016_Chapter_4_tables.xlsx | xlsx | spreadsheetml | 49899 | 2b33020454354fec32cb20685ecb9a8e1e503e80b8197e6b818d8d4102ecde07 | 4.1 to 4.4; 4.1 row 45 = 2015-16 |
| .../5a7f5c21e5274a2e87db561f/PESA_2016_Chapter_5_tables.xlsx | xlsx | spreadsheetml | 67665 | c6bccdbbfc704229e6c7e4656c278f69999bbbc669789f9ebc2196a287966621 | 5.1 to 5.6 (departmental) |
| .../5a815e6ae5274a2e87dbd414/PESA_2016_Chapter_10_Tables.xlsx | xlsx | spreadsheetml | 125234 | fda553ba0083e96add2d54852a76c4f31dcdc6e51a05e055be81978e7f8de642 | 10.1 COFOG, 2010-11 to 2014-15 outturn (F = 2014-15) |
| .../5a81cd7ee5274a2e8ab55e82/PESA_2017_Chapter_10_Tables.xlsx | xlsx | spreadsheetml | 122270 | 1597b5732ab7fba9bc4987310cf19d35307c68c4ce2f79d7d6f9929d930543df | 10.1 COFOG, 2011-12 to 2015-16 outturn (F4 = 2015-16 outturn; "Total general public services" F12 = 4880) |
| .../5b4f4172ed915d43718e1bcd/PESA_2018_Chapter_10_tables.ods | ods | opendocument.spreadsheet | 106006 | 9415808a492d83016308ce5365d336c79f36bd42711232a75d46f950eb34bb91 | 10.x COFOG (ODS, not inspected) |
| .../60f57459d3bf7f56801f3d84/PESA_2021_CP_Chapter_10.xlsx | xlsx | spreadsheetml | 127656 | 4be4da7b9a800152f30ae2516472aeb1ab199feb86583f477df0b7b61c11cb5d | 10.1 COFOG, 2015-16 to 2019-20 outturn (B = 2015-16; "Total general public services" B12 = 4330, a revision from 4880 in the 2017 edition) |
| .../64b67a9d71749c001389ed6e/PESA_2023_CP_Chapter_10_tables.xlsx | xlsx | spreadsheetml | 189304 | e4d97184d529831819e5b5f850a303eec6d1f9fe003b351c8562064e08efe9ba | 10.1 COFOG, 2017-18 to 2021-22 outturn |
| .../66a8dec0a3c2a28abb50d9b9/PESA_2024_CP_Chapter_10_tables.xlsx | xlsx | spreadsheetml | 189731 | 42c87f10010283c577e77e8d58b366de77d800f2fcefbefd0fd76b4831df84e5 | 10.1 COFOG, 2018-19 to 2022-23 outturn |
| .../6874fa8f92691289bdb7d394/PESA_2025_CP_Chapter_1_tables.xlsx | xlsx | spreadsheetml | 128761 | ec4a7aa9313ee676bb5ebf357edeb1f5c4d1a0b534819fe59c4092ca61fc92e4 | Table_1_1 to Table_1_17 (sheet names with underscores) |
| .../6874fe33b1b4ebc2c2e46574/PESA_2025_CP_Chapter_4_tables.xlsx | xlsx | spreadsheetml | 68548 | bc275bc1efed362ba3ed15fb27db010692caa879d201897dc5d64c46bc942570 | 4_1 to 4_4 |
| .../6874fe4582370235232f9343/PESA_2025_CP_Chapter_5_tables.xlsx | xlsx | spreadsheetml | 72454 | 81f2f5db1fd0f0f57d7772be55aeec45ae1f02da551b71e6cf1db2f1d17b9207 | 5_1 to 5_6 |
| .../6874fea182370235232f9345/PESA_2025_CP_Chapter_10_tables.xlsx | xlsx | spreadsheetml | 183247 | b898a1dc0d2d87ee6a8e5a9273cf3fd2bab9b3ef45d9e3a3f6de2c91ed72d2a7 | Metadata, 10.1 COFOG to 10.10 |
| .../6942790ed8156a816c41934f/PESA_2025_Dec_Chapter_1_tables___Chapter_2_tables.xlsx | xlsx | spreadsheetml | 97925 | e8fd09d55db92b0416b076161d909336c4a141bc7c8034f14137c1ae9bfbff60 | Notes; Table_1_3 to Table_1_11; Table_2_1 (a/b/c) (December 2025 update) |
| .../6a57728b822fbe6b8245c9a1/PESA_2026_CP_Chapter_1_tables.xlsx | xlsx | spreadsheetml | 119498 | 0e88d4904e747460fbf254c358b0922f74898b8dd3d4364e0ca1ebe35e12e454 | Table_1_1 to Table_1_14 |
| .../6a5772e09e63154454413700/PESA_2026_CP_Chapter_4_tables.xlsx | xlsx | spreadsheetml | 69092 | 50ae80d95c4e542c34a17dfa8bc302858ca6508b6753e27bb31920cec9bb75c4 | 4_1 Public expenditure aggregates: B46 = 2025-26 outturn (M = 1360.1 TME, £bn), B47 = 2026-27 forecast (M = 1419.3). Header: "Outturn data in this table up to 2025-26" |
| .../6a5772f59e63154454413701/PESA_2026_CP_Chapter_5_tables.xlsx | xlsx | spreadsheetml | 72078 | ccb4539bb837c2b6a7f9509da49bd409eb9e5a910f3332311b494291fbd33107 | 5_1 to 5_6 |
| .../6a57736c6d6d5c7e2845c9d6/PESA_2026_CP_Chapter_10_tables.xlsx | xlsx | spreadsheetml | 185050 | baaa63b96fc3ba066d20d90add268c98f871718ccadf15b75babf922e006d934 | 10.1 COFOG, 2020-21 to 2024-25 outturn (F = 2024-25); "Total general public services" F12 = 9049 |

- Years covered: chaining 10.1 across editions (2017 ed. 2011-12 to 2015-16; 2021 ed. 2015-16 to 2019-20; 2023 ed. 2017-18 to 2021-22; 2024 ed. 2018-19 to 2022-23; 2026 ed. 2020-21 to 2024-25) gives COFOG outturn from 2011-12 to 2024-25. 2015-16 is covered. Table 4.1 (aggregates) runs from 1985-86 to 2026-27 forecast.
- Revision / vintage behaviour: COFOG figures for the same year are restated between editions. Example: "Total general public services" for 2015-16 is 4880 in the 2017 edition and 4330 in the 2021 edition. Use the latest edition that covers a year, and record the edition used.
- Verdict: **USABLE** for 2015-16 to 2024-25 COFOG (10.1) and aggregates (4.1). Reason: all files returned 200 and were inspected; OGL v3. Caveats: no 2025-26 COFOG in the 2026 edition (only 4.1 aggregates); the 2018 ODS and the 2024 ed. were not inspected cell by cell.

## OBR (Office for Budget Responsibility)

- Landing: https://obr.uk/data/ (HTTP 200 with a browser User-Agent; HTTP 403 with a bare curl User-Agent). Use a browser User-Agent for OBR.
- Licence: UNVERIFIED. The OBR licence page was not fetched.

| File (URL as fetched, redirects followed) | Format | Content-Type | Size (bytes) | sha256 | Notes |
|---|---|---|---|---|---|
| https://obr.uk/download/public-finances-databank-september-2026/ -> obr.uk/docs/dlm_uploads/PSF_aggregates_databank_Sep-3.xlsx | xlsx | spreadsheetml | 513789 | 9f3c513a6940e6f75dbcc768bc95cdb5dec78fe6d49fdf3662a019645d1a88ed | Sheets: Changes since last (OLD), Spending and receipts, Aggregates (£bn), Aggregates (per cent of GDP), Aggregates (2025-26 prices), Receipts (£bn), Public finances since 1900, Glossary. "Aggregates (£bn)" row 77 = 2015-16 (C = receipts 714.264, D = TME 794.365); row 87 = 2025-26 (D = TME 1365.598). |
| https://obr.uk/download/historical-public-finances-database/ -> obr.uk/docs/dlm_uploads/Historical-public-finances-database.xlsx | xlsx | spreadsheetml | 2316523 | df154a4774807de330ad3b356db085c1d7adf4b1a4f7bcd13484ad9374f0e3f8 | Sheets: Contents, References, Receipts (£m), Receipts (per cent of GDP), Spending (£m), Spending (per cent of GDP), Aggregates (£m), Aggregates (per cent of GDP). Long history. Year range not checked cell by cell. |
| https://obr.uk/download/march-2026-economic-and-fiscal-outlook-detailed-forecast-tables-zip-file/ -> obr.uk/docs/d055fbf02d5b3g6jq8l2/efo-march-2026-detailed-forecast-tables-zipfile.zip | zip (6 xlsx: aggregates, debt-interest, economy, expenditure, policy, receipts) | application/zip | 1226333 | de72d04940ea7e4013a1b6cce230f7144a05ad734cdd3e72306f34f6c4eb24cd | Members extracted to scratchpad only. Individual member sha256: aggregates f88536f2d9d497ffe307688a8497cb6228d4efac4bf984773db971d037d70a5e; economy fde1de4bc5424dcf16c7b5c42eb75a35198e347f54db47690e95ede7541db510; expenditure 700bfd700c872794e5fe8cf164086cd38a63850db26427b9d4b2e363d177d9a1; receipts a2c16ef1697e4e67f8dd20123595f3f7609b6a6d5ada20cb24ddbe8a758c9368. Economy sheet (GDP and deflator) not inspected cell by cell. |
| https://obr.uk/download/march-2026-economic-and-fiscal-outlook-charts-and-tables/ -> obr.uk/docs/d055fbf02d5b3g6jq8l2/efo-march-2026-charts-and-tables-zipfile.zip | zip (7 xlsx) | application/zip | 4083562 | fb899257ef17c7407eed4e17559b2a037becccd4924366a49f7e6dac5d596aa4 | Charts and tables workbook set. Not inspected. |
| https://obr.uk/download/forecast-revisions-database-march-2025/ -> obr.uk/docs/dlm_uploads/Fiscal_forecast_revisions_database_March_2026.xlsx | xlsx | spreadsheetml | 187094 | a0b03000470a2fffb9b8e05408b8fb7a45c17cac2333c2f05e2ca151fdf4b3b8 | Sheets: Contents, Revisions (Per cent of GDP), Revisions (£ billion), Classifications and one-offs. The slug says March 2025 but the file is March 2026. |
| https://obr.uk/download/july-2025-forecast-evaluation-report-annex-b-supplementary-fiscal-tables/ -> obr.uk/docs/dlm_uploads/Forecast-evaluation-report-%E2%80%93-July-2025-annex-B-%E2%80%93-supplementary-fiscal-tables.xlsx | xlsx | spreadsheetml | 72265 | 450f8c6dee5b93d7cd3d109c313494cf7986c328460a48f8888cf18cfc708fc7 | Contents, Annex B, TB.1 to TB.8 |
| https://obr.uk/download/july-2025-forecast-evaluation-report-annex-a-supplementary-economy-tables/ -> obr.uk/docs/dlm_uploads/Forecast-evaluation-report-%E2%80%93-July-2025-annex-A-%E2%80%93-supplementary-economy-tables.xlsx | xlsx | spreadsheetml | 63478 | 1171feb176c6f95bbda0c5156f3f154880c1a55c36580a94c4c43dd184af63b2 | Contents, Annex A, Methodology notes, TA.1 to TA.11 |
| https://obr.uk/download/historical-official-forecasts-database/ -> https://obr.uk/no-access/download-id/23772/ | HTML (not a data file) | text/html; charset=UTF-8 | 88639 | 963961b486e79e47abe5951559e65e1cba99be2d2a4946968eab0b7967996b93 | HTTP 200, but it is an access page, not the workbook. |

- Years covered: the databank 2015-16 to 2025-26 outturn is confirmed in "Aggregates (£bn)". The historical database covers the long run. Forecast vs outturn: the forecast revisions database (xlsx) is the vintage source. The historical official forecasts database could not be downloaded.
- Vintage behaviour: each EFO and databank release restates history. Keep the release name with each series.
- Verdicts:
  - Public Finances Databank (Sept 2026): **USABLE** for receipts, TME, and aggregates 2015-16 to 2025-26 (inspected, row/col recorded above). Licence UNVERIFIED.
  - Historical Public Finances Database: **PARTIAL** (downloaded, sheets listed, years and series not checked).
  - EFO March 2026 detailed tables (GDP and deflator): **PARTIAL** (downloaded and extracted; the economy sheet was not inspected for the GDP deflator row).
  - EFO charts and tables zip: **PARTIAL** (downloaded, not inspected).
  - Forecast revisions database: **PARTIAL** (downloaded, not inspected; the vintage source for forecast vs outturn).
  - July 2025 Annex A and Annex B: **PARTIAL** (downloaded, not inspected).
  - Historical official forecasts database: **UNUSABLE** as a file (the URL returns an access page, not data).

## ONS Public Sector Finances (PSF)

- Not verified. The guessed bulletin and dataset URLs (…/publicsectorfinances/latest and …/datasets/publicsectorfinancesfinancialtransactions) returned HTTP 404. A later request returned HTTP 429 (rate limited). The ONS time-series API probe (api.ons.gov.uk/timeseries/ANNX/dataset/PSF/time-series-data) returned HTTP 404. No ONS file was downloaded, so no sha256, licence, or coverage was confirmed.
- Licence: UNVERIFIED (ONS normally publishes under OGL v3, but this is not confirmed here).
- Verdict: **UNVERIFIED / PARTIAL**. Next step: find the current PSF bulletin URL from the ONS site, wait for the rate limit to clear, and fetch the time-series CSV or XLSX for the PSF dataset. Confirm 2015-16 to 2025-26 coverage and the licence.

## Summary

| Source | Verdict |
|---|---|
| PESA COFOG 10.1 and aggregates 4.1 (2015-16 to 2024-25 COFOG; 2025-26 aggregates) | USABLE |
| OBR Public Finances Databank Sept 2026 (aggregates, 2015-16 to 2025-26) | USABLE (licence UNVERIFIED) |
| OBR historical PF database, EFO detailed tables, EFO charts, forecast revisions, July 2025 annexes | PARTIAL |
| OBR historical official forecasts database | UNUSABLE (access page) |
| ONS Public Sector Finances | UNVERIFIED / PARTIAL (URLs 404 or 429; nothing fetched) |
