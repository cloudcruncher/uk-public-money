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

Each derived value has its own provenance record listing its inputs. A derived value is `forecast` if any input is.
If the deflator cannot be confirmed, no real-terms variant is published and `index.json` says so.

## Forecast and outturn

Forecast and projection values carry `status: forecast`, with the original wording in `status_note`. Tax years and
fiscal years are labelled and never silently aligned.

## Reconciliation

Rules R1 to R7 are published in `reconciliation.json` and shown on the site. A failure does not fail the build.

| Rule | Check | Status now |
|---|---|---|
| R1 | PESA 10.1: COFOG functions sum to the table total (same edition) | Implemented |
| R2 | PESA 10.1 total vs TME (4.1); TES-to-TME gap shown as `info` if the label is TES | Implemented |
| R3 | PESA TME vs OBR TME, per outturn year (rel tolerance 1.0%) | Implemented |
| R4 | PESA TME vs ONS PSF TME | `not_run` (ONS PSF is a stub) |
| R5 | Our real-terms TME vs the databank real-terms sheet | `not_run` |
| R6 | HMRC receipts vs OBR current receipts (`info` for definitional gaps) | Implemented |
| R7 | DWP UK welfare total vs sum of Table 1a benefit lines | Implemented; **currently fails on real data** |

Statuses are `pass`, `fail`, `info`, and `not_run`.

## Known limits

- **ONS Public Sector Finances:** a stub. No verified URL or hash, so it is disabled.
- **COFOG (PESA 10.1):** covers 2015-16 to 2024-25. 2025-26 has aggregates only.
- **PESA 10.1:** England-only TES (total expenditure on services), not TME.
- **HMRC income tax (Table 2.5):** current edition starts 2023-24. Earlier years need the historic tables, not yet sourced.
- **DWP Table 1a:** GB geography. Values from 2025-26 onward are forecasts.
- **Stat-Xplore, ONS labour market, PAYE RTI:** deferred.
- **R7** currently fails on real data; the cause is not yet resolved.
- **Claims:** `data/claims.yml` ships empty, so no claims are shown.
