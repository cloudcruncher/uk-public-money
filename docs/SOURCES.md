# Sources index

Verified 2026-10-15 by the scouts; detail and hashes in `docs/sources/spend.md` and `docs/sources/revenue-welfare.md`. The machine-readable register is `data/sources.yml` (only USABLE/PARTIAL sources can be enabled).

| source_id | Publisher / dataset | Verdict | Enabled | Notes |
|---|---|---|---|---|
| `pesa` | HMT PESA: Table 10.1 COFOG, Table 4.1 aggregates | USABLE | yes | COFOG 2015-16 to 2024-25; 4.1 to 2025-26 outturn. OGL v3 |
| `obr` | OBR Public Finances Databank, Sept 2026 | USABLE | yes | OGL v3 (version inferred from an unversioned link on the OBR copyright page). Needs a browser User-Agent |
| `hmrc_receipts` | HMRC tax and NICs receipts, `NS_Table.ods` | USABLE | yes | Year headers of `Receipts_Annually` still to be confirmed by the parser |
| `hmrc_income_tax` | HMRC Income Tax Tables 2.5 and 2.1 | PARTIAL | yes | 2023-24 onward only; 2015-16 to 2022-23 need historic Table 2.5a |
| `dwp_benefits` | DWP outturn and forecast tables, Spring Forecast 2026 | USABLE | yes | Table 1a (spend), 1c (caseload); UK and GB welfare tabs |
| `ons_psf` | ONS Public Sector Finances | UNVERIFIED | no | Guessed URLs returned 404/429; nothing downloaded |
| `ons_lms` | ONS labour market, series MGRZ | PARTIAL (MGRZ usable) | no | Out of first slice; MGSX unverified |
| `ons_taxes_benefits` | ONS effects of taxes and benefits | PARTIAL | no | File hashed; years and sheet definitions open; publication date not recorded |
| `dwp_stat_xplore` | DWP Stat-Xplore API | PARTIAL | no | Needs API key; licence unverified |
| `hmrc_paye_rti` | HMRC PAYE RTI | PARTIAL | no | No data file hashed |
| `obr_other` | OBR EFO tables, historical PF database, revisions DB, July 2025 annexes | PARTIAL | no | Downloaded, not inspected |

UNUSABLE: OBR historical official forecasts database (the URL returns an access page, not a workbook).

## Known gaps

- PESA COFOG 10.1 stops at 2024-25; 2025-26 has aggregates only.
- HMRC income tax 2015-16 to 2022-23 not yet sourced.
- No ONS cross-check until a real PSF URL is verified.
- Several files carry restatements between editions; the latest edition covering a year is used and recorded.
