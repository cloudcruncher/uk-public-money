# Corrections

Corrections are recorded in `data/corrections.yml` and published as `site/api/v1/corrections.json`. The file is
append-only. It ships empty, so no corrections have been published yet.

## Entry fields

| Field | Meaning |
|---|---|
| `id` | Unique identifier |
| `date` | ISO date of the correction |
| `series_id` | Affected series |
| `fiscal_year` | Affected year |
| `price_basis` | `nominal`, `real`, `pct_gdp`, or `none` |
| `old_value`, `new_value` | Value before and after |
| `old_provenance_id`, `new_provenance_id` | Provenance of each value |
| `reason` | Why the value changed |
| `reported_by` | Optional, public only |
| `status` | `open` or `fixed` |

Each published correction is shown with its old and new values and provenance links.

## Process

Append an entry to `data/corrections.yml` with both provenance ids, a reason, and a status, then rebuild. The build
publishes the list as `corrections.json`. The reason and status are curated by hand; the build does not detect corrections.

Restatements between PESA or OBR editions are handled by stitching (newest edition wins). Those changes are visible in
`observations_all_vintages` and are not, by themselves, logged as corrections.
