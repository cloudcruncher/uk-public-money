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
| `reconciliation.json` | Rules R1 to R7 with their results and a summary |
| `definitions.json` | Definition groups shown side by side |
| `claims.json` | Claim checks (empty while `data/claims.yml` is empty) |
| `corrections.json` | Corrections log |
| `observations.parquet`, `observations_all_vintages.parquet`, `provenance.parquet`, `reconciliation.parquet` | Same data in tabular form |

## Key shapes

- **Series point:** `fiscal_year`, `value`, `unit`, `status` (`outturn` or `forecast`), `vintage`, `provenance_id`.
  Every point has a `provenance_id`. Non-monetary series have only `nominal`.
- **Provenance `check` block:** download URL, landing URL, sheet, cell, row and column labels, SHA-256, published
  value and unit, and plain-language instructions for finding the value. Derived values list `derived_from`.
- **Provenance id:** `<source_id>.<16 hex chars>`. The prefix before the first dot names the provenance file.

## Check links

The site links each value to `check.html#p=<provenance_id>`, which loads `provenance/<source_id>.json`. xlsx and ods
files cannot be linked to a cell, so the check is the file URL plus sheet, cell, labels, and SHA-256.

`api_version` is `v1` in `index.json`.
