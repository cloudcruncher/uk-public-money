# Methodology

## Provenance rule

No number is published without a complete provenance record. A record needs: publisher, dataset, publication date,
source URL (https), file SHA-256, sheet, exactly one of cell or API query, licence, transformations, status
(`outturn` or `forecast`), vintage, and retrieval mode. The build drops any value whose record is incomplete, logs it
to `work/rejected.jsonl`, and counts it in `index.json`. Dropped values are counted, not hidden.

## Sources and licences

Sources are listed in `data/sources.yml`, with verdicts from [SOURCES.md](SOURCES.md). Only USABLE or PARTIAL
sources can be enabled. Licence for the enabled sources is Open Government Licence v3.0 (`OGL-UK-3.0`), checked
against the gov.uk footer or ONS and OBR pages. The OBR licence is recorded as OGL v3 with the version inferred from
an unversioned OGL link.

## Parsing

Each source has one parser module. Cells are located by header and row text, never by fixed column letters. A
PESA edition needs an entry in its layout table; an unknown edition raises an error rather than being guessed. Values
are kept as published, with no rounding. Blank or non-numeric cells produce no row.

## Stitching across editions

For each series and fiscal year, the newest edition that covers the year is used, and the edition is recorded as its
vintage. Older values remain in `observations_all_vintages`. Years no edition covers are listed as gaps with a reason.
Values are never interpolated, carried forward, or back-cast.

## Units and derived values

- **Nominal:** published value, scaled to £bn with a recorded transformation.
- **Real terms:** deflated with the OBR GDP deflator (fiscal-year basis, same databank vintage) to the base year
  stated in `index.json`.
- **% of GDP:** value divided by OBR nominal GDP for the same fiscal year.
- **Per person:** value divided by the ONS UK mid-year population estimate, mapped to the fiscal year it falls in. Never projected beyond published estimates.
- **Per household:** value divided by the ONS count of private households (Labour Force Survey, April to June quarter; a sample estimate). Published from 2011 only.
- **Out of every £100:** a function's share of total managed expenditure multiplied by 100, from `shares.json`. The revenue page computes its shares in the browser.
- **Cost per claimant:** DWP Table 1a spend divided by Table 1c caseload for the same benefit and year. Caseloads count cases or claims, so for benefits with credits-only cases (ESA, JSA) the figure understates what a paid claimant receives.
- Calendar-year and stock series (for example debt) get no per-person, per-household or share variants.

Each derived value has its own provenance record listing its inputs. A derived value is `forecast` if any input is.
If the deflator cannot be confirmed, no real-terms variant is published and `index.json` says so.

## Forecast and outturn

Forecast and projection values carry `status: forecast`, with the original wording in `status_note`. Tax years and
fiscal years are labelled and never silently aligned.

## Reconciliation

Rules R1 to R14 are published in `reconciliation.json` and shown on the site. A failure does not fail the build.

| Rule | Check | Status now |
|---|---|---|
| R1 | PESA 10.1: COFOG functions sum to the table total (same edition) | Implemented |
| R2 | PESA 10.1 total vs TME (4.1); TES-to-TME gap shown as `info` if the label is TES | Implemented |
| R3 | PESA TME vs OBR TME, per outturn year (rel tolerance 1.0%) | Implemented |
| R4 | ONS PSF central government TME vs PESA/OBR public sector TME (different scope, stated) | Implemented |
| R5 | Our deflated TME (nominal x D[base]/D[year], base = the year the deflator equals 100) vs the databank real-terms TME, same file, 0.5% | Implemented; all years agree |
| R6 | HMRC receipts vs OBR current receipts (`info`) | Implemented |
| R7 | DWP total benefit expenditure vs sum of Table 1a lines (memo rows below the total excluded) | Implemented |
| R8 | OBR EFO Universal Credit vs DWP Spring Forecast, 1% tolerance | 2024-25 fails at 1.09%; cause traced to the DWP outturn basis, see Known limits |
| R9 | OBR EFO welfare cap vs DWP UK welfare total | Implemented |
| R10 | Cabinet Office monthly payments within plausibility bounds | Implemented |
| R11 | PESA UK COFOG 5.2 total vs headline TME | Implemented |
| R12 | PESA 5.2 functions plus EU transactions vs TES, rounding 1.5 | Implemented |
| R13 | HMRC receipts vs OBR EFO 3.8, both cash basis | Implemented |
| R14 | PSF gross expenditure minus receipts equals net borrowing | Implemented |

Statuses are `pass`, `fail`, `info`, and `not_run`.

## Known limits

- **ONS URLs:** PSF, households and GDP files are replaced in place by ONS; see SOURCES.md for how the pin is kept.
- **COFOG (PESA 10.1):** covers 2015-16 to 2024-25. 2025-26 has aggregates only.
- **PESA 10.1:** England-only TES; the UK-wide view uses PESA 5.2.
- **HMRC income tax (Table 2.5):** current edition starts 2023-24. Earlier years need the historic tables, not yet sourced.
- **DWP Table 1a:** GB geography. Values from 2025-26 onward are forecasts.
- **Stat-Xplore, ONS labour market, PAYE RTI:** deferred.
- **R8** fails for 2024-25 (1.09%: OBR 52.835, DWP 53.418 GBP bn) and is left failing on purpose. It is the right line and scope on both sides (the "within the Welfare Cap" Universal Credit line; forecast years 2026-27 to 2030-31 agree to 1e-14). DWP's Notes tab says its tables "do not exactly match those in the EFO" because of "different definitions of spending, and additional analysis leading to reassignment of spending across benefits", and Table 1a's own OBR reconciliation block shows 2024-25 outturn needs +1.41 (removal of accounting adjustments), -0.20 and +0.004 GBP bn to reach the OBR total (OBR DWP social security 289.143 = that reconciled total exactly). The adjustments are not itemised by benefit, so the UC share cannot be derived: DWP UC total is 66.74 vs OBR 66.36 and the within/outside split also differs by 0.20. The tolerance is not loosened.
- **R7** failed 16 times on live data (about 0.6% in 2015-16) before the memo rows were excluded. Cause: the "Expenditure covered by Departmental Expenditure Limit" and "Benefits funded by local authorities" rows printed under the total restate spending already in the lines above (2015-16: 407.4 + 670.8 = 1,078.3 of 171,893 GBP m = 0.63%). With them excluded, Table 1a lines sum to the total in all 16 years and the UK welfare tab also sums, checked against the real file (sha256 11a591e4...).
- **Claims:** `data/claims.yml` ships empty, so no claims are shown.
