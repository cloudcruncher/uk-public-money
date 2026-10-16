# Static API (v1)

The build writes a static API to `site/api/v1`. It is JSON (UTF-8, sorted keys) plus Parquet, with no server. Numbers
are as published, with no rounding; the site rounds for display. `python -m ukpm check-api site/api/v1` validates the
shapes below, and `--live` also rejects fixture-sourced records.

## Files

| Path | Contents |
|---|---|
| `index.json` | Build mode and time, fiscal-year range, real base year, deflator, sources, series list, file list |
| `series/<series_id>.json` | One series with `nominal`, `real`, and `pct_gdp` variants, gaps, and notes |
| `provenance/<source_id>.json` | Provenance records keyed by `provenance_id`, each with a `check` block |
| `reconciliation.json` | Rules R1 to R14 with their results and a summary |
| `definitions.json` | Definition groups shown side by side |
| `benefits/index.json`, `benefits/<slug>.json` | Per-benefit explainers: `caseload_basis`, `headline` (`spend`, `spend_real`, `claimants`, `cost_per_claimant`, `share_of_welfare`, each with `value`, `unit`, `fiscal_year`, `status`, `vintage`, `provenance_id`) and a trend. `index.json` carries every benefit's headline so pages need not load all 16 files |
| `shares.json` | "Out of every £100" shares for spending, with provenance |
| `glossary.json` | Plain-English terms built from `data/glossary.yml`; entries may not contain figures |
| `cabinet_office/summary.json` | Monthly totals of payments over £25k, expense-type totals and the 20 largest suppliers paid at least £1m. No dates, references, expense areas or row-level amounts |
| `claims.json` | Claim checks (empty while `data/claims.yml` is empty) |
| `corrections.json` | Corrections log |
| `observations.parquet`, `observations_all_vintages.parquet`, `provenance.parquet`, `reconciliation.parquet` | Same data in tabular form |

## Key shapes

- **Derived variants:** series may also carry `per_person`, `per_household` (from ONS households, 2011 onward), `per_100` and cost-per-claimant variants. Each has a provenance record naming both inputs. Calendar-year and stock series get no derived variants.
- **Series point:** `fiscal_year`, `value`, `unit`, `status` (`outturn` or `forecast`), `vintage`, `provenance_id`.
  Every point has a `provenance_id`. Non-monetary series have only `nominal`.
- **Provenance `check` block:** `download_url`, `landing_url`, `sheet`, `cell`, `sha256` (aliases of the record fields), published
  value and unit, and plain-language instructions for finding the value. Derived values list `derived_from`. `row_label` and `column_label` are not emitted (no parser sets them).
- **Provenance id:** `<source_id>.<16 hex chars>`. The prefix before the first dot names the provenance file.

## Check links

The site links each value to `check.html#p=<provenance_id>`, which loads `provenance/<source_id>.json`. xlsx and ods
files cannot be linked to a cell, so the check is the file URL plus sheet, cell, labels, and SHA-256.

`api_version` is `v1` in `index.json`.
