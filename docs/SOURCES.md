# Sources index

Verified 2026-10-15/16 by the scouts; detail and hashes in `docs/sources/` (`spend.md`, `revenue-welfare.md`, `new-sources*.md`). The machine-readable register is `data/sources.yml` (only USABLE/PARTIAL sources can be enabled).

| source_id | Publisher / dataset | Verdict | Enabled | Notes |
|---|---|---|---|---|
| `pesa` | HMT PESA: Table 10.1 COFOG, Table 4.1 aggregates | USABLE | yes | COFOG 2015-16 to 2024-25; 4.1 to 2025-26 outturn. OGL v3 |
| `obr` | OBR Public Finances Databank, Sept 2026 | USABLE | yes | OGL v3 (version inferred from an unversioned link on the OBR copyright page). Needs a browser User-Agent |
| `hmrc_receipts` | HMRC tax and NICs receipts, `NS_Table.ods` | USABLE | yes | Year headers of `Receipts_Annually` still to be confirmed by the parser |
| `hmrc_income_tax` | HMRC Income Tax Tables 2.5 and 2.1 | PARTIAL | yes | 2023-24 onward only; 2015-16 to 2022-23 need historic Table 2.5a |
| `dwp_benefits` | DWP outturn and forecast tables, Spring Forecast 2026 | USABLE | yes | Table 1a (spend), 1c (caseload); UK and GB welfare tabs |
| `ons_psf` | ONS Public Sector Finances (central government TME, debt interest) | USABLE | yes | Followed from the bulletin to the dataset file. Re-issued monthly; URL is `/current/` (see Known gaps) |
| `ons_population` | ONS mid-year population estimates, UK | USABLE | yes | Basis for per-person figures. OGL v3.0 verified |
| `ons_households` | ONS families and households, UK 2025 (sheet 5) | USABLE | yes | Basis for per-household figures. Private households only, LFS sample estimate |
| `ons_gdp` | ONS GDP at current market prices (YBHA) | USABLE | yes | Used for % of GDP cross-checks. Generator CSV endpoint, no versioned link |
| `obr_efo` | OBR Economic and fiscal outlook, March 2026, sheet 4.9 welfare cap | PARTIAL | yes | Only welfare-cap rows parsed |
| `obr_efo_receipts` | OBR EFO sheet 3.8, current receipts (cash basis) | PARTIAL | yes | Policy tables and other receipts sheets not parsed |
| `pesa_uk` | HMT PESA 2026 chapter 5, table 5.2 (UK-wide COFOG) | USABLE | yes | Replaces England-only table 10.1 for the out-of-every-£100 view |
| `cabinet_office_spend` | Cabinet Office spend over £25,000, monthly CSV | USABLE | yes | Aggregated by month, expense type and the 20 largest suppliers; no row-level data published |
| `ons_lms` | ONS labour market, series MGRZ | PARTIAL (MGRZ usable) | no | Out of first slice; MGSX unverified |
| `ons_taxes_benefits` | ONS effects of taxes and benefits | PARTIAL | no | File hashed; years and sheet definitions open; publication date not recorded |
| `dwp_stat_xplore` | DWP Stat-Xplore API | PARTIAL | no | Needs API key; licence unverified |
| `hmrc_paye_rti` | HMRC PAYE RTI | PARTIAL | no | No data file hashed |
| `obr_other` | OBR EFO tables, historical PF database, revisions DB, July 2025 annexes | PARTIAL | no | Downloaded, not inspected |

UNUSABLE: OBR historical official forecasts database (the URL returns an access page, not a workbook).

## Known gaps

- PESA COFOG 10.1 stops at 2024-25; 2025-26 has aggregates only.
- HMRC income tax 2015-16 to 2022-23 not yet sourced.
- ONS URLs are not stable. `ons_psf` and `ons_households` use `/current/` links and `ons_gdp` a generator CSV. ONS moves a release to `/previous/vNNN` only after the next one, and none of those versioned links matched our pinned sha256 (checked 2026-10-16). `refresh.yml` restores the pinned file from the `raw-cache` GitHub release; if ONS replaces a file before it is first cached, `ukpm fetch` fails with a sha256 mismatch and the pin must be re-verified from `landing_url`.
- Universal Credit, ESA, JSA, Pension Credit and Housing Benefit caseloads count cases or claims, not necessarily people (DWP Table 1c says only "individuals" and has no household note for UC). ESA and JSA include credits-only cases that are paid nothing.
- OBR EFO and DWP disagree by 1.09% for Universal Credit in 2024-25 (rule R8, tolerance 1%). Both are outturn; neither file gives a reason.
- No household count means per-household figures exist only where ONS households cover the year (2011 onward).
- Not parseable or not found, so shown as gaps with no figure: PSF expenditure series beyond those listed; Scotland GERS, MHCLG council spend and OBR fiscal-risks tables T3.1/T5.1 (scouted, not finished: `docs/sources/new-sources-2-pub.md`); any official total for tax paid or benefits received by migrants or asylum seekers (`docs/sources/new-sources-3-immigration.md`).
- Detail and hashes for the newer sources: `docs/sources/new-sources.md`, `new-sources-2-ons.md`, `new-sources-2-pub.md`.
- Several files carry restatements between editions; the latest edition covering a year is used and recorded.
