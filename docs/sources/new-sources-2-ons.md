# New sources 2: ONS gap closure (PSF, households, GDP)

Checked 2026-10-15. Files fetched with curl (browser User-Agent, retry on 5xx/429) into a scratch directory outside the repo and read with `python3 -I` / openpyxl (read-only, no macros). Only URLs that returned HTTP 200 and were fetched are listed. Format follows `new-sources.md`.

Licence line, quoted from each ONS dataset landing page: "Open Government Licence v3.0" (link to nationalarchives.gov.uk/doc/open-government-licence/version/3/). The households workbook cover sheet also says: "You may re-use this document/publication (not including logos) free of charge in any format or medium, under the terms of the Open Government Licence v3.0." OGL v3: YES for all three.

Note for earlier work: the legacy ONS `.../bulletins/<name>/latest/data` endpoint is dead (HTTP 404, body "This legacy endpoint was decommissioned on 02/02/2026 and is no longer available."). Use dataset page `/current/data` (JSON listing), `/file?uri=...` (xlsx) and time series `/data` instead. The ONS developer API `https://api.beta.ons.gov.uk/v1/datasets?limit=1000` returned 200 application/json (471131 bytes, 338 datasets) but contains only Census 2021, regional GDP, tax-benefit and similar datasets; it has no PSF and no Families and households dataset, so it is not the route for these targets.

## 1. ONS Public Sector Finances

### Chain of links followed (all HTTP 200)

1. Bulletin: https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/publicsectorfinance/bulletins/publicsectorfinances/latest (text/html, 179188 bytes). Resolves to "Public sector finances, UK: August 2026", Release date 22 September 2026, Next release 21 October 2026.
2. The bulletin links to the dataset page (found in its HTML): https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/publicsectorfinance/datasets/publicsectorfinancesappendixatables110 (text/html, 42805 bytes), "Public sector finances tables 1 to 10: Appendix A", Release date 22 September 2026, xlsx 1.6 MB.
3. Dataset JSON: https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/publicsectorfinance/datasets/publicsectorfinancesappendixatables110/current/data (application/json, 39839 bytes). Lists download `publicsectorfinancessummarytablesappendixafinal.xlsx`, a supplementary `datdataset1appendixaafinal.xls`, and 144 earlier versions (latest three dated 2026-07-21, 2026-08-21, 2026-09-22).
4. File (the dataset page's own link).

### File

- Direct URL: https://www.ons.gov.uk/file?uri=/economy/governmentpublicsectorandtaxes/publicsectorfinance/datasets/publicsectorfinancesappendixatables110/current/publicsectorfinancessummarytablesappendixafinal.xlsx
- HTTP 200; Content-Type `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=utf-8`; 1717948 bytes; sha256 `4cc5dded99d4bf06b8df9c3d9ef4e09a903c96208ba54626e6db507a07129b7e`.
- Publication date: cover sheet row 5, "This spreadsheet was published at 7.00am 22 September 2026"; next "7.00am 21 October 2026". Data run to August 2026 (cover title "Appendix A, Public Sector Finances, August ...").
- Workbook: 70 sheets. Cover Sheet, Table of Contents, Notes (note text in column B, key in column A as "note 17" etc.), then PSA1 ... PSA10, REC1-3, PSNFL1-3, PSA1R, PSA2R, PSA6BR_1/2.
- Layout (common to the long sheets): row 5 = column headers (with unit and note refs), row 6 = "Dataset identifier code" (4-letter CDID, some with a leading space, e.g. " NMFX", " -NMFJ"), then data from row 7. Column A is the period label. Rows are in blocks: calendar years "1998" to "2025" (rows 7-34), financial years "Apr 1997 to Mar 1998" ... "Apr 2025 to Mar 2026" (rows 35-63; the label is truncated to "Apr 1997 t" in my print only), quarters "Apr to Jun ..." from row 64, then months "1998 Jan" ... "2026 Aug" (last row 533). Values are numeric strings of £ million unless stated.

### Key series (sheet / columns / rows), values read from this file

| Need | Sheet | Column (CDID) | Row(s) | Values read |
|---|---|---|---|---|
| Central government total managed expenditure ("Memo item: Total expenditure", note 21 = total current expenditure + depreciation + net investment) | PSA6B_2 | K (header "Memo item: Total expenditure (£ million)", no CDID shown) | 7-34 calendar years, 35-63 FY | 2024: 1175025; 2025: 1235538; FY 2024/25 (row 62): 1187834; FY 2025/26 (row 63): 1250068 |
| Same, via sub-sector TME table | PSA6L | B Central government (CDID ECOD); H Public sector excl. banks (KX5Q); K/L memo % GDP (FZM3/FZM4) | same row blocks | FY 2025/26 row 63: central gov 1250068, public sector excl. banks 1365598, 46.4 % GDP; FY 2024/25 row 62: 1187834, 1290348, 44.0 % |
| Central government total revenue | PSA6C_3 | B (MF6R) | same | FY 2025/26: 1175063; FY 2024/25: 1090205; calendar 2025: 1144522 |
| Central government total expenditure (gross-capital basis, note 26 = current + capital) | PSA6C_3 | C (MF6U), D current (MF6S), E capital (MF6T) | same | FY 2025/26: 1301598 (current 1147100, capital 154498); FY 2024/25: 1240238 |
| Central government net borrowing | PSA6C_3 / PSA6B_2 | F (-NMFJ) / J | same | FY 2025/26: 126535; FY 2024/25: 150033; calendar 2025: 143545 |
| Debt interest (central gov current expenditure, interest) | PSA6B_2 | B (NMFX), note 17: "Includes investment income attributable to insurance policy holders" | same | calendar 2025: 97643; FY 2025/26: 96839; FY 2024/25: 85261 |
| Net social benefits (central gov) | PSA6B_2 | C (GZSJ) | same | FY 2025/26: 326332 |
| Public sector net borrowing excl. banks | PSA1 | D (-J5II) | 7-34 cal, 35-63 FY | FY 2025/26 (row 63): 134286; FY 2024/25: 149769 |
| Public sector net debt, £bn and % GDP | PSA1 | E CPPH and F CPOA (excl. public sector banks and Bank of England); G HF6W and H HF6X (excl. public sector banks); N RUTN / O RUTO incl. banks | monthly rows to 533 | Aug 2026 (row 533): CPPH 2870.1, CPOA 90.2, HF6W 2985.5, HF6X 93.8 |
| Net debt monthly matrix | PSA4_1 | columns = FY labels "Apr 2012 to Mar 2013" ... "Apr 2026 to Mar 2027" (£bn); rows = months | rows 6-17 | e.g. April row: 1260.7 (FY2012/13) |
| Fiscal indicators % GDP | PSA5A, PSA5B | not opened in detail | | |

Net debt mapping: values and CDIDs were matched by position on rows 5 and 6 of PSA1 (E=CPPH, F=CPOA, G=HF6W, H=HF6X). A parser should key off the row 6 CDIDs (which may have leading spaces) rather than column letters. The four column-header texts were read truncated; confirm full wording before labelling in the UI.

Reconciliation observation (verified from the file): PSA6C_3 "Total expenditure" (FY 2025/26: 1301598) and PSA6B_2/PSA6L "Total expenditure/TME" (1250068) are different definitions (difference 51530). Both give identical net borrowing (126535). The PSA6B_2 identity (note 21: K = E + G + I) was checked for calendar 2025: 1085255 + 43778 + 106505 = 1235538. For a "total managed expenditure" series, use PSA6L (it is titled "Total Managed Expenditure by sub-sector"); do not mix with PSA6C_3.

### Revision behaviour

The dataset is re-issued every month (144 versions; latest three 2026-07-21, 2026-08-21, 2026-09-22). Each release restates history (cover sheet row 9-10 warn on comparing changes; PSA1R, PSA2R, PSA6BR_* sheets and the separate "revisions analysis" dataset appendix P exist for this). I did not download an earlier vintage to diff values. Record the release month with every stored series.

### Verdict: **USABLE**

Reason: official chain of links bulletin -> dataset page -> file, 200, OGL, annual calendar-year, financial-year, quarterly and monthly data back to 1997/98, and the exact series wanted (central government expenditure/TME, receipts, net borrowing, debt interest, public sector net debt). Caveats: net debt row mapping noted above; two total-expenditure definitions; values are £ million (debt in £ billion on PSA1 G, PSA4_1).

### Smallest fixture slice for a parser test

Sheet PSA6B_2 rows 1-9 plus rows 33-34 (calendar 2024, 2025) and rows 62-63 (FY 2024/25, 2025/26) and the last row, columns A-K, to prove the row-5/row-6 header and the calendar vs financial-year label blocks. Add sheet PSA6L with the same rows (columns A-L) for TME and % GDP. Optionally sheet PSA1 rows 5-9 plus rows 62-63 columns A-H. Include the "Cover Sheet" row 5 text for the vintage. Keep sheet names exactly (some contain a trailing space in the sheet list, e.g. "PSA6C_2 ").

## 2. ONS families and households (count of UK households)

### Chain of links followed (all HTTP 200)

1. Bulletin: https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/families/bulletins/familiesandhouseholds/latest (text/html, 91246 bytes). "Families and households in the UK: 2025", Release date 17 April 2026, Next release "To be announced". Main points: "In 2025, there were 29.0 million households in the UK, 66.8% of which contained one family ..." and "Around 8.6 million people (29.5% of all households) lived alone".
2. Dataset page: https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/families/datasets/familiesandhouseholdsfamiliesandhouseholds (text/html, 42652 bytes), "Families and households", Release date 17 April 2026, xlsx 204.2 KB.
3. Dataset JSON: .../datasets/familiesandhouseholdsfamiliesandhouseholds/current/data (application/json, 3758 bytes): lists `familiesandhouseholdsuk2025.xlsx` and earlier versions from 2016-11-04.

### File

- Direct URL: https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/birthsdeathsandmarriages/families/datasets/familiesandhouseholdsfamiliesandhouseholds/current/familiesandhouseholdsuk2025.xlsx
- HTTP 200; Content-Type `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=utf-8`; 209085 bytes; sha256 `a89eaa3d7f519bfa949c7cfa12f531b8c7a86c704adcb70e81f49567ae724a91`.
- Publication date: cover sheet "Date published: 17 April 2026."
- Sheets: Cover sheet, Notes, Statistical robustness, Covid-19 and LFS, then "1" to "9" (Table 1 families by type; 5 households by size; 6 people living alone; 7 households by type; 8 people in households; 9 married couple families).
- Years covered: 1996 to 2025, 30 years (Labour Force Survey household dataset, April to June quarter each year).
- Key series: sheet "5" ("Table 5: Households by size, United Kingdom, 1996 to 2025"), header row 12 with a triplet per year: "<year> Estimate", "<year> CV", "<year> CI+/-", newest year first (B = 2025). Row 21, "All households" (thousands): 2025 29003; 2024 28609; 2023 28358; 2022 28243; 2021 28119; 2020 27893; 2019 27824; 2018 27576; 2017 27226; 2016 27109; 2015 27046; 2014 26734; 2013 26663; 2012 26620; 2011 26409; 2010 26240; 2009 26042; 2008 25875; 2007 25609; 2006 25379; 2005 25217; 2004 24993; 2003 24917; 2002 24792; 2001 24535; 2000 24396; 1999 24209; 1998 24036; 1997 23865; 1996 23738. Row 22 average household size 2025 = 2.36. Row 36 of sheet "1" "All families" 2025 = 19880 (thousands), 2024 = 19688, 2023 = 19477, 2022 = 19410, 2021 = 19312.
- Definition break: Notes row 12 (note 9): "For 1996 to 2010, a household is defined as a person living alone, or a group of people living at the same address who have the address as their only or main residence and either share one main meal a day or share living accommodation (or both). For 2011 onwards it is defined as one person living alone, or a group of people ... who share cooking facilities and share a living room or sitting room or dining area."
- Coverage note (cover sheet row 22): private households, NHS accommodation and students in halls whose parents live in the UK; excludes communal establishments. Row 28: LFS-based estimates for Northern Ireland are no longer published separately (the UK total table is still present).
- Revision behaviour: annual re-issue (one workbook per year since 2016); LFS-based, sample estimates with CV and 95 % CI per cell (2025 all households 29003 with CI +/- 155). Earlier years may be restated when LFS weights change; I did not diff against a prior edition.
- Verdict: **USABLE** for the UK number of households and families 1996-2025 (use the 2011-2025 span to avoid the definition break). Caveat: sample survey, not a census count.
- Smallest fixture slice: sheet "5" rows 1, 12 and 21-22 (header and "All households"/average size) with columns A-M (2025 to 2022 triplets); sheet "1" rows 12 and 36; sheet "Cover sheet" rows 1-2 for the vintage.

## 3. ONS UK GDP (current prices, annual)

### Chain of links followed (all HTTP 200)

1. Time series page: https://www.ons.gov.uk/economy/grossdomesticproductgdp/timeseries/ybha/ukea (text/html, 137806 bytes); the page carries the OGL v3.0 line.
2. JSON: https://www.ons.gov.uk/economy/grossdomesticproductgdp/timeseries/ybha/ukea/data (application/json;charset=utf-8, 63857 bytes, sha256 `feae68ca4ed2c9b709c2bc41a53f6769507d3afe2eccaec0ea39900844c06864`).
3. CSV: https://www.ons.gov.uk/generator?format=csv&uri=/economy/grossdomesticproductgdp/timeseries/ybha/ukea (Content-Type `application/octet-stream;charset=utf-8`, 6752 bytes, sha256 `080b6afad67e567c2f27c1afea720cdf49832b7158de0487fc4a3681c0485bf4`).

### Series

- YBHA = "Gross Domestic Product at market prices: Current price: Seasonally adjusted £m" (so nominal GDP; ABMI is the chained-volume series and was not used). Source dataset UKEA ("UK Economic Accounts"). Contact sector.accounts@ons.gov.uk.
- Release date 30-09-2026 (CSV header "Release date"; JSON `releaseDate` 2026-09-29T23:00:00Z, i.e. 30 September BST); next release 22 December 2026.
- CSV layout: lines 1-8 metadata (Title, CDID, Source dataset ID, PreUnit, Unit, Release date, Next release, Important notes), then `"year","value"` rows with annual data from "1948" (line 9) to "2025" (line 86), then quarters ("2026 Q2" last, value 787197). JSON has 78 annual points (`years`), 286 quarterly (`quarters`), no monthly.
- Annual values (£ million): 2018 2178105; 2019 2263433; 2020 2131729; 2021 2332847; 2022 2590757; 2023 2766446; 2024 2904950; 2025 3044594; 1948 11383.
- Revision behaviour (verified by comparing two vintages fetched from the same URL pattern): the same series from the earlier dataset edition `/timeseries/ybha/pn2/data` (release 2026-08-12, "PN2" = quarterly national accounts first edition) gives 2023 2752164; 2024 2890254; 2025 3033866, versus the UKEA edition (30 Sep 2026) 2766446; 2024 2904950; 2025 3044594. So a one-quarter vintage change moved 2025 nominal GDP by +10728 (+0.35 %). Always store the release date with the series.
- Note on denominators: the ONS PSF workbook uses its own 12-month-centred GDP for its "% GDP" columns (PSA1 note 2: "12 month centred moving total of GDP"), so a ratio built from YBHA calendar-year GDP will not equal the PSF percentage.
- Verdict: **USABLE** (annual 1948 to 2025). Caveat: provisional recent years, revised each quarter.
- Smallest fixture slice: the 8 CSV metadata lines plus data rows 1948, 2023, 2024, 2025 and the first quarter row, verbatim (about 15 lines).

## Summary table

| Target | Verdict | Direct file | sha256 |
|---|---|---|---|
| Public Sector Finances Appendix A tables 1-10 (Aug 2026) | USABLE | https://www.ons.gov.uk/file?uri=/economy/governmentpublicsectorandtaxes/publicsectorfinance/datasets/publicsectorfinancesappendixatables110/current/publicsectorfinancessummarytablesappendixafinal.xlsx | 4cc5dded99d4bf06b8df9c3d9ef4e09a903c96208ba54626e6db507a07129b7e |
| Families and households 2025 | USABLE | https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/birthsdeathsandmarriages/families/datasets/familiesandhouseholdsfamiliesandhouseholds/current/familiesandhouseholdsuk2025.xlsx | a89eaa3d7f519bfa949c7cfa12f531b8c7a86c704adcb70e81f49567ae724a91 |
| GDP current prices YBHA (UKEA) | USABLE | https://www.ons.gov.uk/generator?format=csv&uri=/economy/grossdomesticproductgdp/timeseries/ybha/ukea (or `/data` JSON) | CSV 080b6afad67e567c2f27c1afea720cdf49832b7158de0487fc4a3681c0485bf4; JSON feae68ca4ed2c9b709c2bc41a53f6769507d3afe2eccaec0ea39900844c06864 |
