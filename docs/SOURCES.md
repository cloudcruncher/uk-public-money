# Sources index

Verified 2026-10-15/16 by the scouts; detail and hashes in `docs/sources/` (`spend.md`, `revenue-welfare.md`, `new-sources*.md`). The machine-readable register is `data/sources.yml` (only USABLE/PARTIAL sources can be enabled).

| source_id | Publisher / dataset | Verdict | Enabled | Notes |
|---|---|---|---|---|
| `pesa` | HMT PESA: Table 10.1 COFOG, Table 4.1 aggregates | USABLE | yes | COFOG 2015-16 to 2024-25; 4.1 to 2025-26 outturn. OGL v3 |
| `obr` | OBR Public Finances Databank, Sept 2026 | USABLE | yes | OGL v3 (version inferred from an unversioned link on the OBR copyright page). Needs a browser User-Agent |
| `hmrc_receipts` | HMRC tax and NICs receipts, `NS_Table.ods` | USABLE | yes | Year headers of `Receipts_Annually` still to be confirmed by the parser |
| `hmrc_income_tax` | HMRC Income Tax Tables 2.5 and 2.1 | PARTIAL | yes | 2015-16 to 2026-27 (2015-16 to 2022-23 from historic Table 2.5a) |
| `dwp_benefits` | DWP outturn and forecast tables, Spring Forecast 2026 | USABLE | yes | Table 1a (spend), 1c (caseload); UK and GB welfare tabs |
| `ons_psf` | ONS Public Sector Finances (central government TME, debt interest) | USABLE | yes | Followed from the bulletin to the dataset file. Re-issued monthly; URL is `/current/` (see Known gaps) |
| `ons_population` | ONS mid-year population estimates, UK | USABLE | yes | Basis for per-person figures. OGL v3.0 verified |
| `ons_households` | ONS families and households, UK 2025 (sheet 5) | USABLE | yes | Basis for per-household figures. Private households only, LFS sample estimate |
| `ons_gdp` | ONS GDP at current market prices (YBHA) | USABLE | yes | Used for % of GDP cross-checks. Generator CSV endpoint, no versioned link |
| `obr_efo` | OBR Economic and fiscal outlook, March 2026, sheet 4.9 welfare cap | PARTIAL | yes | Only welfare-cap rows parsed |
| `obr_efo_receipts` | OBR EFO sheet 3.8, current receipts (cash basis) | PARTIAL | yes | Policy tables and other receipts sheets not parsed |
| `pesa_uk` | HMT PESA 2026 chapter 5, table 5.2 (UK-wide COFOG) | USABLE | yes | Replaces England-only table 10.1 for the out-of-every-£100 view |
| `cabinet_office_spend` | Cabinet Office spend over £25,000, monthly CSV | USABLE | yes | Aggregated by month, expense type and the 20 largest suppliers; no row-level data published |
| `fcdo_oda` | FCDO provisional UK ODA spend 2025, Fig3: in-donor refugee costs by department | PARTIAL | yes | Calendar years 2021-2025, provisional, first 12 months of a stay only. OGL v3 |
| `dwp_uc_status` | DWP Universal Credit by immigration status, Table_1 | PARTIAL | yes | People (not GBP), Great Britain, May of each year 2022-2026; last three months provisional. OGL v3 |
| `home_office_spend` | Home Office Core Data Tables 2026, Total_departmental_spending (resource DEL) | PARTIAL | yes | Outturn 2021-22 to 2025-26; file name says "draft"; visas and passports line is net of fee income. OGL v3 |
| `home_office_ara` | Home Office Annual Report and Accounts 2025-26 (PDF): visa income, IHS, UKVI fees and charges, Immigration Skills Charge, civil penalties, Trust Statement total | USABLE | yes | Outturn 2025-26 with 2024-25 comparatives (reclassified/restated there). PDF read with `pypdf` from fixed pages. OGL v3 |
| `home_office_asylum` | Home Office immigration system statistics, Asy_00a | USABLE | yes | Counts of people, calendar years 2015-2025 (hotels from 2022). OGL v3 |
| `scotland_gers` | Scottish Government GERS 2025-26, Tables 1.1, 3.1, 5.1 (all years) and 3.3 (2025-26 by function) | USABLE | yes | Scotland, GBP million, 1998-99 to 2025-26; revenue and balance shown with and without the North Sea geographical share. `www.gov.scot` added to the host allowlist. OGL v3 |
| `mhclg_la_outturn` | MHCLG local authority revenue outturn 2025-26, England Table 1a | USABLE | yes | England only, GBP million, 2021-22 to 2025-26 by service; first release provisional; social care excludes NHS-funded spend; education not comparable across years (academies) |
| `mac_fiscal_impact` | MAC fiscal impact of immigration, Table 9, Figure 10, Table 23 | PARTIAL | no | Deliberately not parsed: modelled estimates for a single 2022/23 cohort, and the data model only has outturn and forecast. Needs an `estimate` status in provenance, build and check_api first |
| `ons_lms` | ONS labour market, series MGRZ | PARTIAL (MGRZ usable) | no | Out of first slice; MGSX unverified |
| `ons_taxes_benefits` | ONS effects of taxes and benefits | PARTIAL | no | File hashed; years and sheet definitions open; publication date not recorded |
| `dwp_stat_xplore` | DWP Stat-Xplore API | PARTIAL | no | Needs API key; licence unverified |
| `hmrc_paye_rti` | HMRC PAYE RTI | PARTIAL | no | No data file hashed |
| `obr_other` | OBR EFO tables, historical PF database, revisions DB, July 2025 annexes | PARTIAL | no | Downloaded, not inspected |

UNUSABLE: OBR historical official forecasts database (the URL returns an access page, not a workbook).

## Known gaps

- PESA COFOG 10.1 stops at 2024-25; 2025-26 has aggregates only.
- ONS URLs are not stable. `ons_psf` and `ons_households` use `/current/` links and `ons_gdp` a generator CSV. ONS moves a release to `/previous/vNNN` only after the next one, and none of those versioned links matched our pinned sha256 (checked 2026-10-16). `refresh.yml` restores the pinned file from the `raw-cache` GitHub release; if ONS replaces a file before it is first cached, `ukpm fetch` fails with a sha256 mismatch and the pin must be re-verified from `landing_url`.
- Universal Credit, ESA, JSA, Pension Credit and Housing Benefit caseloads count cases or claims, not necessarily people (DWP Table 1c says only "individuals" and has no household note for UC). ESA and JSA include credits-only cases that are paid nothing.
- OBR EFO and DWP disagree by 1.09% for Universal Credit in 2024-25 (rule R8, tolerance 1%). Both are outturn. DWP Notes say its figures differ from the EFO through different spending definitions and reassignment across benefits, and Table 1a's OBR reconciliation shows a net +1.2 GBP bn bridge for 2024-25 (not itemised by benefit). The line and scope compared are the same; forecast years agree exactly.
- No household count means per-household figures exist only where ONS households cover the year (2011 onward).
- Not parseable or not found, so shown as gaps with no figure: PSF expenditure series beyond those listed; Scotland GERS, MHCLG council spend and OBR fiscal-risks tables T3.1/T5.1 (scouted, not finished: `docs/sources/new-sources-2-pub.md`); any official total for tax paid or benefits received by migrants or asylum seekers (`docs/sources/new-sources-3-immigration.md`).
- Detail and hashes for the newer sources: `docs/sources/new-sources.md`, `new-sources-2-ons.md`, `new-sources-2-pub.md`.
- Several files carry restatements between editions; the latest edition covering a year is used and recorded.
- Immigration income now comes from the Home Office Annual Report and Accounts 2025-26 PDF (`home_office_ara`; HC 440, sha256 `c8cda7ee5f28700b4a2174b3889cb203c410503c60222e6a03102d92642c1350`). It is read deterministically (no OCR, no model): `pypdf` text of fixed PDF pages 283/284 (Note 3, printed 278/279), 228 (fees and charges, printed 223), 351 (Trust Statement revenue statement, printed 346) and 339 (narrative cross-check, printed 334). Each page's title, printed page number, GBP thousand unit and the year header (2025-26 then 2024-25) are asserted, every row must match exactly once, and totals are cross-checked, otherwise `LayoutError`. Provenance puts the PDF page in `sheet` and the row label and column in `cell_or_range`. The Trust Statement figures are read from the thousands table on p351 rather than the millions in the narrative on p339 (the scout's source), which is used only as a cross-check. Not parsed: passport fees, total fees-and-charges income (the segment rows do not add to it, because small categories are excluded), income by visa route (not published). IHS payable to the Consolidated Fund is a dash (nil) in 2025-26, stored as 0 with a recorded `nil` transformation. Only 2025-26 is parsed; older reports have other layouts.
- Why `pypdf`: it is pure Python, has no required dependencies and gives page-by-page text, which is all this needs. `pdfplumber` pulls in `pdfminer.six` and `pypdfium2` (a compiled binary) for table geometry we do not use. The PDF is 18.7 MB (under the 25 MB fetch cap) and is not committed: the fixture `tests/fixtures/home_office_ara/` keeps the five real pages and blanks the rest so page numbers stay true.
- Home Office spending, other gaps: no separate pounds figure for asylum hotels in the accounts (NAO HC 874 gives a partial-year contract estimate only, not parsed); NHS cost of care for migrants has no official aggregate; tax paid or benefits received by status or nationality: HMRC stops at 2018-19 (nationality, not status); MAC fiscal-impact tables, OBR net-migration assumption (EFO sheet C2.6) and Home Office asylum tables other than `Asy_00a` (support type, route of entry, small boats, safe routes) are scouted but not parsed.
- Immigration series use different time bases and are not directly comparable: FCDO and Home Office asylum counts are calendar years, DWP counts are May of each year, Home Office spending is April to March. The latest asylum month (year ending June 2026) is not published (different period basis).

## New-edition watch

The daily refresh only re-downloads the files pinned in `data/sources.yml`, so a new publication is not picked up by itself. `python -m ukpm watch` (weekly via `.github/workflows/watch.yml`) reads each landing page and reports data-file links that are not pinned or listed in `data/watch_baseline.json`, and any pinned file whose live bytes no longer match its sha256. A report opens or updates a `source-watch` issue. Adding the new edition is still a PR: verify the file, add a pin, check the parser. After reviewing, run `python -m ukpm watch --accept` to record the current links as seen. Rate-limited or unreachable pages are warnings, not findings.
