# New sources: verification log

Checked 2026-10-15. Files fetched with curl into a scratchpad download directory (not committed). Browser User-Agent used for gov.uk and obr.uk. "Licence" lines are quoted from the landing page. Only URLs that returned HTTP 200 are recorded.

## Cabinet Office spend over £25,000 (Cabinet Office)

- Landing: https://www.gov.uk/government/publications/cabinet-office-spend-data (HTTP 200, text/html). Collection: https://www.gov.uk/government/collections/cabinet-office-spend-data (HTTP 200).
- Publication date: first published 2013-07-05; last updated 2026-09-24 (from the gov.uk content API).
- Licence: the gov.uk footer reads "All content is available under the Open Government Licence v3.0, except where otherwise stated". OGL v3: YES.
- Years covered: the latest 12 files cover Sep 2025 to Aug 2026. The page itself covers spend since 1 April 2010.
- Headers (all 12 files, identical): Ref, Departmental Family, Entity, Date, Expense Type, Expense Area, Supplier, Transaction number, Amount. Date format is DD-Mon-YY. Amount is a comma-thousands string such as "528,677.90".
- Encoding: UTF-8 with BOM for most files; 11 of 12 files are not valid UTF-8 and decode as cp1252 (for example "AtkinsRéalis" has byte 0xE9). Line endings are CRLF. Parsers should try UTF-8-sig, then cp1252.
- Gross or VAT: the header has no VAT column, and the page text found no VAT statement. Treat amounts as published, with VAT status UNVERIFIED.
- Blank rows: co_09 has 1 blank row and co_12 has 130 blank rows (trailing). Skip empty rows.
- Verdict: **USABLE** for spend totals by month and entity. The file is a flat CSV with no sheet structure. Caveat: VAT basis unknown; sum counts are as published.

| # | File (URL, HTTP 200, text/csv) | Size (bytes) | Month | Data rows | Sum of Amount (£) | sha256 |
|---|---|---|---|---|---|---|
| 1 | https://assets.publishing.service.gov.uk/media/69009a5a84b816d72cb9aa48/Expenditure_Over_25000_-_September_2025__Cabinet_Office_Core___1___2_.csv | 77093 | September 2025 | 499 | 112227426.43 | 587b8fcba37848d8cb4081d8cfb0af1872cca67bdd0d8d68604a2a0940b5555b |
| 2 | https://assets.publishing.service.gov.uk/media/692439c3367485ea116a5601/Expenditure_Over_25000_-_October_2025__Cabinet_Office_Core___1___2___1_.csv | 81533 | October 2025 | 524 | 115830260.96 | 37b8277b11f45f9e709ce477161759bb0d5586f5579bb584ba85690763d97192 |
| 3 | https://assets.publishing.service.gov.uk/media/693bf0cc5cc812f50aa420c3/Expenditure_Over_25000_-_November_2025__Cabinet_Office_Core.csv | 83420 | November 2025 | 534 | 119181958.69 | fb7a8d642751d8f914a55932a8be3ea3627a776f9f8b0554efd08f81a4f88ce0 |
| 4 | https://assets.publishing.service.gov.uk/media/69774ec94883520241b796df/Expenditure_Over_25000_-_December_2025__Cabinet_Office_Core.csv | 95305 | December 2025 | 614 | 196480768.72 | b1dfbcb6bab221435b0705ccf0bfeb3bd28a052b7a1545e4bc72235d60c450bb |
| 5 | https://assets.publishing.service.gov.uk/media/699c82d2e1c6bad1576fbbfd/Expenditure_Over_25000_-_January_2026__Cabinet_Office_Core.csv | 86016 | January 2026 | 560 | 123607773.56 | 15a47ac9a23079dc83a8e20006e7cf459c93dcb71c18432f46eac16abfe4c00b |
| 6 | https://assets.publishing.service.gov.uk/media/69c15f18bb0dfe55b83e4bc1/Expenditure_Over_25000_-_February_2026__Cabinet_Office_Core__1_.csv | 95161 | February 2026 | 604 | 138317293.25 | 1e96da3fbf166e943bcd110330e575428a39ad8fa5abcec87d9422e922389cad |
| 7 | https://assets.publishing.service.gov.uk/media/69ef6596ed93f72cf816343c/Expenditure_Over_25000_-_March_2026__Cabinet_Office_Core.csv | 142572 | March 2026 | 869 | 261904761.53 | fda534025b47e80a45e41a0bbfc5b6fb3d868dccb045ac1b88718608891866eb |
| 8 | https://assets.publishing.service.gov.uk/media/6a18061ec7335e2ca6daac44/Expenditure_Over_25000_-April_2026__Cabinet_Office_Core.csv | 81666 | April 2026 | 503 | 114211764.83 | 27888083577226475e8069fd9ed1d274d8660fd60e066e227bf00ab6bed6a934 |
| 9 | https://assets.publishing.service.gov.uk/media/6a3919a225c5199bda1178e2/Expenditure_Over_25000_-May_2026__Cabinet_Office_Core.csv | 90697 | May 2026 | 562 | 282202688.85 | 00b06342cd07278a775f47b8b5d5aaddeed2d7d08d338659a68183b0d2001dab |
| 10 | https://assets.publishing.service.gov.uk/media/6a69c721f23ff62c51c1a7eb/Expenditure_Over_25000_-June_2026__Cabinet_Office_Core.csv | 102726 | June 2026 | 637 | 147840701.52 | 9bceed0988394baa46c41a5eac8fd0a0bcb84e99459c92b7eb40727e98d5d3ba |
| 11 | https://assets.publishing.service.gov.uk/media/6a842891c9205b515d421e07/Expenditure_Over_25000_-July_2026__Cabinet_Office_Core.csv | 98896 | July 2026 | 606 | 174078716.30 | 52b4287984158cf874ef361c455d59f1ba38364bdadbce46d3c1f82718d283d7 |
| 12 | https://assets.publishing.service.gov.uk/media/6aad022a44ec1aa417346c6d/Expenditure_Over_25000_-Aug_2026__Cabinet_Office_Core__1_.csv | 76491 | Aug 2026 | 476 | 110279506.39 | 6b44468c316b6831245af143b1995f4aadda131a41791159e939beb1032dba27 |

- Monthly totals are sums of the Amount column over data rows, as published. They are not reconciled to any Cabinet Office headline figure.
- Revision behaviour: each monthly file is a fixed publication. The gov.uk page notes re-published months (for example "Updated document for January 2025", which says GPA data "was previously missing").

## OBR (OBR)

- Landing pages (HTTP 200, browser UA): https://obr.uk/data/ (text/html); https://obr.uk/efo/economic-and-fiscal-outlook-march-2026/; https://obr.uk/wtr/welfare-trends-report-june-2026/; https://obr.uk/frs/fiscal-risks-and-sustainability-july-2026/.
- Licence: UNVERIFIED. The OBR licence page was not fetched.
- Bare curl user agents get HTTP 403 on obr.uk; a browser UA is required.

| Source | Final URL (HTTP 200) | Content-Type | Size (bytes) | sha256 | Years / sheets / key series | Verdict |
|---|---|---|---|---|---|---|
| EFO March 2026 detailed tables, expenditure | https://obr.uk/docs/d055fbf02d5b3g6jq8l2/efo-march-2026-detailed-forecast-tables-expenditure.xlsx | spreadsheetml | 236965 | 700bfd700c872794e5fe8cf164086cd38a63850db26427b9d4b2e363d177d9a1 | Sheets 4.1 to 4.20 + Contents. Sheet 4.2 row 6 = Total managed expenditure (% GDP). Sheet 4.9 row 18 = Universal credit; row 19 = Other DWP in welfare cap; row 34 = NI social security in welfare cap. Sheet 4.11 row 8 = UC standard allowance and health element. Year header row not yet read. | **PARTIAL**: welfare and TME rows located; year header not read. |
| EFO March 2026 detailed tables, receipts | https://obr.uk/docs/d055fbf02d5b3g6jq8l2/efo-march-2026-detailed-forecast-tables-receipts.xlsx | spreadsheetml | 187899 | f65b6cb7f96931d4abd85940794eb60f6f65afca8bbf16c74a4548bf92766a28 | Not inspected. | **PARTIAL** |
| EFO March 2026 detailed tables, policy | https://obr.uk/docs/d055fbf02d5b3g6jq8l2/efo-march-2026-detailed-forecast-tables-policy.xlsx | spreadsheetml | 64437 | 5263b901827d887bc87b9f49f627780c789a594e48897d194d90463e61def763 | Not inspected. | **PARTIAL** |
| Welfare Trends Report June 2026, charts and tables | https://assets.publishing.service.gov.uk/media/6a3a579e25c5199bda1179d1/Welfare-trends-report-June-2026-charts-and-tables.xlsx (linked from https://obr.uk/download/june-2026-welfare-trends-report-charts-and-tables/) | spreadsheetml | 1889979 | 31bca7e55cacdbce212d42a023db2e263cca352174fbc6a342427e378cc6f84f | Sheets: Contents, Executive summary, C1.1 to C3.5, T2.1, T2.2, T3.1. Mainly fraud and error (UC rates, C2.x, C3.x, T3.1 recoveries). No spend-by-benefit or caseload table seen in the sheet list. | **PARTIAL**: fraud-and-error workbook, not a spend or caseload source. |
| Fiscal Risks and Sustainability July 2026, report | https://assets.publishing.service.gov.uk/media/6a4cb4c74889d85e75ab40e0/E03599617_OBR_FRS_2026_Accessible.pdf | application/pdf | 1375079 | 3274a2d1373e6093ebd3a14298f873b9efead3d659d2878b64121941c80ea2b3 | PDF report, not a workbook. | **PARTIAL** (report only) |
| FRS July 2026, charts and tables annexes | https://obr.uk/no-access/download-id/24953/ (reached via obr.uk/download/july-2026-fiscal-risks-and-sustainability-charts-and-tables-annexes/) | text/html; charset=UTF-8 | 88639 | de09d68d020ee1a3dfcaefe12e3166c444a5f07689ff709597104ee2ed8b4aec | Access page, not data. | **UNUSABLE** (access page) |

- Revision behaviour: each EFO and welfare release restates history. Keep the release name with each series.
- Other OBR files from the earlier session (Public Finances Databank Sept 2026, Historical PF database, July 2025 annexes, forecast revisions database) are recorded in docs/sources/spend.md, not repeated here.

## ONS mid-year population estimates (population)

- Dataset landing: https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/populationestimatesforukenglandandwalesscotlandandnorthernireland (HTTP 200, text/html, browser UA).
- Latest file: https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/populationestimatesforukenglandandwalesscotlandandnorthernireland/mid2025/mye25tablesuk.xlsx (HTTP 200, spreadsheetml, 1026940 bytes, sha256 8ae244e3341257ecccaee55f4973fe12f46afe6656ead6c1a9ed3f4f8585e40f). Cover sheet: "originally published at 9.30am 1 October 2026".
- Long run file: https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/populationestimatesforukenglandandwalesscotlandandnorthernireland/ukpopulationestimates1838to2025/ukpopulationestimates18382025.xlsx (HTTP 200, spreadsheetml, 992614 bytes, sha256 5f2b92d0c9191198f5fd0d9515928f8d48c13aba1b52d8e7399c82cc2dd25bb0). Not inspected.
- Licence: UNVERIFIED on the ONS page. The landing page licence line was not extracted in this pass.
- Years covered: MYE4 "Summary for the UK, mid-2011 to mid-2025" (sheet MYE4, header row 8: D = Mid-2025 ... L = Mid-2017; mid-2015 and mid-2016 are in columns further right and were not read cell by cell).
- Key series: sheet MYE1 (row 9, "All Persons", column B = United Kingdom = 69483939 for mid-2025). Sheet MYE4 row 9 = UK series (D = Mid-2025 = 69483939; E = Mid-2024 = 69256274; F = Mid-2023 = 68588048). Sheet MYE2 - Persons row 9 = by single year of age (column D = All ages).
- Revision behaviour: Notes row 12 says mid-2022, mid-2023 and mid-2024 UK estimates were revised in October 2026 (international migration for England and Wales and Scotland). Series are restated each year; record the release vintage.
- Verdict: **USABLE** for UK total population 2015 to 2025 (MYE4 row 9, sheet MYE4 columns for mid-2015 onward). Caveat: the mid-2015 and mid-2016 columns need one cell check before a fixture is cut. Licence still UNVERIFIED.
- Smallest fixture slice for a parser test: sheets MYE4 (rows 1 to 9, all columns) and MYE1 (rows 7 to 9), trimmed to the UK row.

## Households and families count

- Not checked in this pass. Verdict: **PARTIAL** (not attempted). The population dataset page lists zip and xlsx files, but no households or families file was opened or confirmed.

## ONS Public Sector Finances (Public Sector Finances)

- Status: NOT VERIFIED. The gov.uk national statistics release collection (https://www.gov.uk/government/collections/national-statistics-release, HTTP 200) contains no link to a PSF bulletin or dataset. The ONS PSF bulletin URL returned HTTP 502 this session. The previously guessed URLs in docs/SOURCES.md returned 404 and 429.
- Verdict: **UNUSABLE** for now (no verifiable file). Reason: no link followed from an official page to a PSF dataset file. Next step: find a PSF link from an official page (for example the HMT or ONS statistics page) and fetch its xlsx.
