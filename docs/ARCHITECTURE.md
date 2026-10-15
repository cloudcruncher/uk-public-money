# UK Public Money: architecture

A trust-first static data product built on the london-pulse pattern: uv, DuckDB, Parquet, a static JSON/Parquet API
under `site/api/v1`, scheduled GitHub Actions refresh, contract and Playwright smoke tests, GitHub Pages hosting. No
server, no database to run.

The rule: **no number is published without a complete provenance record**, and every published number has a
"Check this number" link that lets a reader find the same value in the publisher's own file.

Inputs to this design: `docs/sources/spend.md` and `docs/sources/revenue-welfare.md` (scout logs, 2026-10-15).
Section 2 lists what those logs found, and the design follows from it.

---

## 1. Flow

```
data/sources.yml ──> fetch (download, sha256, manifest) ──> parsers.<id>.parse() ──> work/parsed/<id>.parquet
                                                                                   │
            tests/fixtures/** (--offline) ─────────────────────────────────────────┘
                                                                                   ▼
                     build: DuckDB load → provenance gate → stitch editions → unit conversions
                            → reconciliation → definitions → claims → write site/api/v1
                                                                                   ▼
                     check-api site/api/v1 → pytest → Pages deploy → smoke.yml (live)
```

---

## 2. Scout findings and what the design does about them

| # | Finding (scout log) | Design response |
|---|---|---|
| 1 | **ONS PSF UNVERIFIED**: guessed URLs gave 404, then 429; nothing was fetched, so there is no sha256, licence or coverage. | The **OBR Public Finances Databank** (`PSF_aggregates_databank_Sep-3.xlsx`, USABLE, 2015-16 to 2025-26 outturn) is the primary source for annual aggregates (TME, receipts, borrowing). `ons_psf` is in `sources.yml` with `verdict: UNVERIFIED`, `optional: true`, `enabled: false`. Its parser module may exist, but any fetch failure is non-fatal. The reconciliation rules that need it publish `status: not_run` with the reason, so they are never silently dropped. It can be turned on once a URL returns 200 and is hashed. |
| 2 | **OBR gated file.** The scout log shows the *historical official forecasts database* redirects to `obr.uk/no-access/...` (HTTP 200, but HTML, not a workbook). The EFO March 2026 detailed-tables zip did download (200), but its members are PARTIAL (not inspected cell by cell). Note: the brief calls this the "EFO aggregates file". In the log, the gated file is the historical forecasts database, and the EFO aggregates member came from a zip that downloaded fine. | (a) The fetch layer **sniffs content**: a file declared xlsx/ods/zip must start with the `PK\x03\x04` magic and must not be `text/html`. Otherwise the fetch fails for that file (`gated_or_not_a_file`) and nothing is parsed. (b) Forecast rows come from the databank's own forecast years and from PESA/DWP forecast columns. The EFO zip is `optional: true`, used only for GDP and the deflator if the databank lacks them (see 7). (c) The historical forecasts database is `verdict: UNUSABLE` and is not fetched. (d) OBR returns 403 to bare curl, so sources can set `headers` (User-Agent) in `sources.yml`. (e) **OBR licence is UNVERIFIED.** `licence` is a mandatory provenance field and `UNVERIFIED` fails the gate, so `parse-obr` must fetch the OBR copyright/licence page and record the licence id and a verbatim quote in `sources.yml` before any OBR value can be published. If it is not OGL-compatible, stop and escalate; do not publish. |
| 3 | **HMRC files do not span 10 years in one file.** Income tax Table 2.5 (current edition) has 2023-24 to 2026-27 only; 2015-16 to 2022-23 is in the historic Table 2.5a editions (landing found, not downloaded). The 10-year coverage of HMRC receipts `NS_Table.ods` is not yet confirmed. | A source has a **list of files (editions)**. Each file is fetched, hashed and parsed separately and gets its own provenance. **Stitching** (build, section 6): for each `(series_id, fiscal_year)`, take the value from the newest edition that covers that year. Superseded values stay in `observations_all_vintages.parquet`. Years that no edition covers become entries in the series' `gaps` list with a reason. **Never interpolate, carry forward or back-cast.** HMRC liabilities for years after the latest SPI outturn year are HMRC *projections* and get `status: forecast` with vintage `"SPI projection <edition>"`. Income bands are published per year as HMRC gives them; there is no re-banding across years. |
| 4 | **Stat-Xplore needs a free API key** (docs quote: "you must first obtain an API key"), and its licence is not verified. **The ONS legacy LMS time-series API was retired 25/11/2024**, and no beta dataset id was found. PAYE RTI pages have no spreadsheet attachment. The ONS effects of taxes and benefits API (v3, 2022) is stale. | These are **out of the first slice** and are listed in `sources.yml` with `enabled: false` and a `deferred` block (reason and replacement). See the table below. No secret is introduced in slice 1. |
| 5 | **PESA layout changes between editions**: sheet `10.1` vs `Table_10_1`/`4_1`; year columns move (2017 ed: F = 2015-16; 2021 ed: B = 2015-16); xlsx vs ods (2018); values are restated (2015-16 general public services is 4880 in the 2017 ed and 4330 in the 2021 ed). | **Per-edition parsing.** `ukpm.parsers.pesa` holds a `LAYOUTS: dict[edition, Layout]` (sheet name, header row, label column, unit) and finds year columns by **header text** (`"2015-16"`, including `"2015-16 outturn"` variants), never by fixed letters. An edition without a layout raises `UnknownLayout`; it is never guessed. The recorded `cell_or_range` is the real cell address in that edition's file. Revisions are expected: stitching takes the newest edition per year and records `vintage = "PESA <edition>"`. COFOG 2025-26 is absent from the 2026 edition (only 4.1 aggregates), so it is a published **gap**, not filled in from another source. |

Deferred sources (slice 1):

| Source | Why deferred | Replacement in slice 1 / next step |
|---|---|---|
| DWP Stat-Xplore | Needs a free API key (401 without one); licence not verified | Caseloads come from DWP benefit expenditure and caseload tables, Table 1c (USABLE). Next: register a key, store it as an Actions secret, verify the licence. |
| ONS labour market (LMS) | Legacy API retired; no beta dataset id | None in slice 1. The MGRZ CSV via `ons.gov.uk/generator` returned 200 and could be used later. |
| HMRC PAYE RTI | No data attachment found via the content API | None in slice 1. |
| ONS effects of taxes and benefits (ETB) | API v3 is stale (2022); `hdiifye2025.xlsx` is PARTIAL | "Who pays" uses HMRC income tax liabilities by income range. Next: inspect `hdiifye2025.xlsx` sheets. |

Slice-1 enabled sources: `pesa`, `obr` (databank; EFO zip optional), `hmrc_receipts`, `hmrc_income_tax`,
`dwp_benefits`. `ons_psf` is optional and off by default.

---

## 3. Repo layout

```
pyproject.toml          [tool.uv] package = false; [tool.pytest.ini_options] pythonpath = ["src"]; ruff config
uv.lock
data/
  sources.yml           source register (section 4)
  fetched.json          committed fetch manifest: last good file per (source, file key) (section 5)
  definitions.yml       side-by-side definitions (section 9)
  claims.yml            curated claims for the claim checker (section 11)
  corrections.yml       public corrections log (append-only)
src/ukpm/
  __init__.py
  __main__.py           CLI (section 12)
  fetch.py              download, sniff, sha256, manifest, raw cache, offline resolution
  sheets.py             safe workbook reader for xlsx/ods (cell values plus A1 addresses)
  provenance.py         Provenance dataclass, REQUIRED_FIELDS, validate() raises IncompleteProvenance
  registry.py           load and validate data/sources.yml
  units.py              nominal/real/%GDP conversions that append transformations
  parsers/__init__.py   Row type, helpers, load_parser(id) -> importlib("ukpm.parsers." + id)
  parsers/pesa.py  parsers/obr.py  parsers/ons_psf.py
  parsers/hmrc_receipts.py  parsers/hmrc_income_tax.py  parsers/dwp_benefits.py
  build.py  reconcile.py  claims.py  check_api.py
site/                   static HTML/CSS/JS, no build step; reads only site/api/v1
  api/v1/               generated (section 10)
tests/                  test_core, test_parsers_*, test_reconcile, test_contract, test_build, smoke/
  fixtures/{spend,obr,revenue,dwp}/   real files or trimmed copies plus fixtures.json
work/                   gitignored: raw/, parsed/, ukpm.duckdb
.github/workflows/      refresh.yml, ci.yml, smoke.yml
scripts/serve.sh
```

All commands run as `PYTHONPATH=src uv run python -m ukpm ...`.
Dependencies: `duckdb`, `pyyaml`, `python-calamine` (one reader for both xlsx and ods; reads cached values only, never
evaluates formulas or macros). `openpyxl` is optional, for writing trimmed xlsx fixtures. Stdlib `urllib` (or `httpx`).
Dev: `pytest`, `ruff`, `playwright`.

---

## 4. `data/sources.yml` schema

```yaml
- id: pesa                       # [a-z_]+, equal to the parser module name
  publisher: HM Treasury
  dataset: Public Expenditure Statistical Analyses
  landing_url: https://www.gov.uk/government/collections/public-expenditure-statistical-analyses-pesa
  licence: {id: OGL-3.0, url: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/,
            evidence: 'gov.uk footer: "Open Government Licence v3.0"'}
  cadence: annual (July), occasional December update
  coverage: {from: 2011-12, to: 2024-25, notes: "COFOG 10.1 chained across editions; 4.1 to 2025-26 outturn"}
  verdict: USABLE                # USABLE | PARTIAL | UNVERIFIED | UNUSABLE  (copied from docs/sources/*.md)
  verdict_reason: "..."
  enabled: true                  # fetch and build it
  optional: false                # true: a fetch/parse failure warns instead of failing the run
  headers: {}                    # e.g. obr: {User-Agent: "Mozilla/5.0 (compatible; uk-public-money; +repo url)"}
  deferred: null                 # or {reason: ..., replacement: ...}
  files:                         # one entry per edition/file; file_url lives here
    - key: pesa_2026_ch10        # unique within the source
      edition: "2026"            # selects the parser layout and gives the vintage label
      file_url: https://assets.publishing.service.gov.uk/media/6a57736c6d6d5c7e2845c9d6/PESA_2026_CP_Chapter_10_tables.xlsx
      format: xlsx               # xlsx | ods | zip | csv | json
      zip_member: null           # for zip files: the member to parse
      publication_date: 2026-07-16
      covers: {from: 2020-21, to: 2024-25}
      scout_sha256: baaa63b9...  # sha256 recorded by the scout; a change on fetch is logged, not an error
```

`registry.load()` validates: unique ids; `file_url` and `landing_url` are https; verdict is in the enum;
`enabled: true` is refused for `UNUSABLE`; `licence.id` is set (`UNVERIFIED` is allowed in the register but blocked
at the provenance gate). Only URLs that returned 200 in the scout logs may be entered, with a scout or parser task
recording the check.

---

## 5. Fetch layer (`ukpm.fetch`)

- `fetch(source, file) -> FetchedFile(path, sha256, size, content_type, retrieved_at, url_final)`.
- Downloads to a temp file, then moves it to `work/raw/<source_id>/<sha256>/<original_filename>` (content-addressed,
  so re-downloading the same bytes is a no-op).
- **Safety**: 60 MB size cap while streaming; zip magic check for xlsx/ods/zip; reject `text/html` (gated pages);
  zip-bomb guard (total uncompressed size ≤ 300 MB, at most 200 members); no macro or formula evaluation. Downloaded
  files are untrusted data: parsers only read cells.
- **Manifest**: `data/fetched.json` (committed, small) maps `"<source>/<key>"` to
  `{url, url_final, sha256, size, retrieved_at, publication_date}`. It is rewritten only for files that fetched
  successfully. A changed sha256 is logged as `source changed` and shows in the commit diff.
- **Raw cache in CI**: raw files are kept as assets on a GitHub release `raw-cache`, named
  `<source>__<key>__<sha256>.<ext>`. `refresh.yml` restores the assets listed in `fetched.json` before fetching. If a
  live fetch fails (429, 5xx, gated), the build uses the **last good cached file**. Its provenance stays exact (same
  url, sha256, older `retrieved_at`), and `index.json.sources[].stale_since` is set so the site can say so.
- **`--offline`**: no network. Resolution order per file: (1) `work/raw/...` matching the sha256 in `fetched.json`;
  (2) a committed fixture listed in `tests/fixtures/*/fixtures.json`.
  `fixtures.json` entries look like:
  `{source_id, key, path, original_url, original_sha256, fixture_sha256, publication_date, trimmed: bool, trim_note}`.
  **Fixture rule**: commit the original file unmodified when it is 1 MB or smaller (then `fixture_sha256 ==
  original_sha256`). Larger files (DWP 1.7 MB) are trimmed to the needed sheets and rows, written as xlsx with **every
  kept cell at its original sheet name and A1 address**, so the recorded `sheet`/`cell_or_range` stay true for the
  original file. Provenance always carries the **original** url and sha256, plus `retrieval: live|cache|fixture`.

---

## 6. Parser contract (`ukpm.parsers.<id>`)

```python
SERIES: dict[str, SeriesMeta]   # series_id -> {title, unit, period_type, monetary: bool, definition_id?, description}
def parse(path: Path, meta: FileMeta) -> list[Row]: ...
# FileMeta: source (registry entry), file (files[] entry), sha256, url_final, retrieved_at, retrieval
```

Each `Row` (a dict or dataclass; written to `work/parsed/<source_id>.parquet`) has:

| field | type | rule |
|---|---|---|
| series_id | str | `<source>.<concept>[.<sub>]`, e.g. `pesa.cofog.health`, `obr.psf.tme`, `hmrc.receipts.vat`, `dwp.exp.uk_welfare`, `hmrc_it.liabilities.band.<slug>` |
| fiscal_year | str | `YYYY-YY` (`2015-16`). Tax years use the same format, with `period_type: tax_year` in SERIES |
| value | float | exactly as in the cell (no rounding); a blank, `..`, `-` or `x` cell gives **no row** |
| unit | str | `GBP_m`, `GBP_bn`, `thousand_persons`, `persons`, `percent`, `index` |
| publisher, dataset, licence | str | from the registry |
| publication_date | date | from `files[].publication_date` |
| source_url | str | https `file_url` (the publisher's direct file) |
| file_sha256 | str | 64 hex chars, of the **original** file |
| sheet | str | sheet name exactly as in the file |
| cell_or_range | str or null | A1 address of the value cell, e.g. `F12`. Exactly one of `cell_or_range` and `api_query` is set |
| api_query | str or null | full https request URL, for API sources |
| row_label, column_label | str | the text of the row and column headers that located the value (shown in the check view) |
| transformations | list | parser-level steps, e.g. `[{op:"scale", from:"GBP_m", to:"GBP_bn", factor:0.001}]`; `[]` if none |
| status | str | `outturn` or `forecast`. Plans, projections and forecasts are all `forecast`; the original wording goes in `status_note` |
| vintage | str | e.g. `PESA 2026`, `OBR databank Sep 2026`, `DWP Spring Forecast 2026`, `HMRC IT liabilities 2026` |
| retrieval | str | `live`, `cache` or `fixture` |

Rules: locate cells by label text and assert the label you expected (raise `LayoutChanged` with sheet and cell, never
guess); per-edition layouts as described in section 2 (#5); parsers never combine sources; units are kept as published
(scaling only in recorded transformations). Every module docstring lists the sheets used and any skipped (with reason).

---

## 7. Canonical store (DuckDB `work/ukpm.duckdb`, exported as Parquet)

```sql
provenance(provenance_id TEXT PRIMARY KEY, source_id, publisher, dataset, publication_date DATE, source_url,
           file_sha256, sheet, cell_or_range, api_query, row_label, column_label, licence, licence_url,
           transformations JSON, status, status_note, vintage, retrieval, retrieved_at TIMESTAMP,
           inputs JSON)          -- provenance_ids of other values used to derive this one (derived values only)
observations(series_id, fiscal_year, value DOUBLE, unit, price_basis, status, provenance_id)   -- one row per published value
observations_all_vintages(...same + edition, superseded BOOL)
gaps(series_id, fiscal_year, reason)
```

- `price_basis`: `nominal`, `real_<base>` (e.g. `real_2025-26`), or `pct_gdp`.
- `provenance_id = "<source_id>." + sha256(file_sha256|sheet|cell_or_range|api_query|canonical_json(transformations))[:16]`.
  It is deterministic, so ids stay the same across rebuilds of the same file. The prefix tells the client which
  provenance file to load.
- **Provenance gate** (`provenance.validate`, called by the build writer and again by `check-api`). A record is
  complete only if: all of publisher, dataset, publication_date, source_url (https), file_sha256 (64 hex), sheet,
  exactly one of cell_or_range/api_query, licence (not `UNVERIFIED`, in the allowed list: `OGL-3.0` for now),
  transformations (a list, possibly empty), status in {outturn, forecast}, vintage, and retrieval are present. The
  writer **refuses** to emit a value whose record is incomplete. Such values are dropped, logged to
  `work/rejected.jsonl` and counted in `index.json.build.rejected` (published, not hidden). For live builds, `check-api`
  fails when `rejected > 0` for an enabled non-optional source.
- **Stitching** (build): only across editions of one source. Newest `publication_date` wins per
  `(series_id, fiscal_year)`. Within one edition, outturn beats forecast. Missing years in 2015-16..latest become
  `gaps` rows: reason `"not published in any fetched edition"` or `"source unavailable: <error>"`.

## 8. Unit conversions (`ukpm.units`) as recorded transformations

Applied only to series with `monetary: true` (never counts or percentages). Every derived value gets its own provenance
record. It copies the primary input's location fields, appends a transformation, and lists `inputs`.

- **Nominal**: the published value, scaled to `GBP_bn` (`{op:"scale"}`).
- **Real**: `real = nominal × D[base] / D[y]`, where D is the **OBR GDP deflator at market prices, fiscal-year basis**
  from the same databank vintage as the aggregates. `base` = the latest outturn year of that vintage (2025-26 for the
  Sep 2026 databank), published as `index.json.real_base_year`.
  Transformation: `{op:"deflate", deflator_series:"obr.gdp_deflator", base_year, deflator_vintage, d_base, d_year}`,
  with `inputs` = provenance ids of both deflator cells.
  Source of D: the databank, if the parser finds a deflator column by header. Otherwise the EFO March 2026 economy
  member (optional; not inspected by the scout, so `parse-obr` must confirm the row and record its cell). If neither
  can be confirmed, no real-terms variant is published, and `index.json` says so.
- **% of GDP**: `value / nominal GDP (fiscal year, same OBR vintage) × 100`; `{op:"ratio_gdp", gdp_series:"obr.gdp_nominal"}`.
  This is not GDP centred end-March (that measure is for debt stocks, which are out of slice 1).
- A derived value is `forecast` if any input is forecast. Fiscal-year deflators are applied to tax-year series with
  `status_note: "tax-year series deflated with fiscal-year deflator"`.
- Cross-check: our real-terms TME is compared with the databank's "Aggregates (2025-26 prices)" sheet (rule R5).

---

## 9. Reconciliation (`ukpm.reconcile`) and definitions

Results are always published in `reconciliation.json` and shown on the site. Failures **do not fail the build**. They
are the honest output. Statuses: `pass`, `fail`, `info` (a known definitional difference, delta shown with an
explanation), `not_run` (an input is missing; reason given).

| id | rule | tolerance |
|---|---|---|
| R1 | PESA 10.1: sum of COFOG function rows = the table's own total row, **same edition**, per year | abs ≤ 0.5 × number of rows (in the table's unit; rounding), else fail |
| R2 | PESA 10.1 total vs PESA TME (4.1), same edition. **Builder must read the total row label**: chapter 10 totals are usually *total expenditure on services* (TES), not TME. If so, publish the TME−TES gap as `info` ("accounting adjustments"). Compare as pass/fail only if the label says TME | `info`, or rel ≤ 0.1% |
| R3 | PESA TME (latest edition) vs OBR databank TME, per outturn year | rel ≤ 1.0% pass; above that, `fail` with both vintages shown |
| R4 | PESA TME vs ONS PSF TME | as R3; `not_run` while `ons_psf` is disabled |
| R5 | Our real-terms TME vs the databank's real-terms sheet | rel ≤ 0.5% |
| R6 | HMRC total receipts vs OBR current receipts | `info`: cash vs accrued, HMRC-only vs all receipts (council tax, business rates and so on). `fail` only if HMRC > OBR |
| R7 | DWP UK welfare total vs the sum of its benefit lines in Table 1a, same edition | abs ≤ 0.5 × rows |

Each result records `left`, `right`, `delta`, `delta_pct`, both provenance ids and the tolerance. Rules never
compare across editions (except R3/R4, which say so).

**Definitions registry** (`data/definitions.yml` → `definitions.json`): groups of definitions shown side by side, each
tied to a real series, so a reader can see why the "welfare" figures differ:

```yaml
- group: welfare
  title: What counts as "welfare"?
  definitions:
    - id: dwp_uk_welfare        # DWP benefit expenditure, "UK welfare" tab: all benefits incl. State Pension
      label: ...; publisher: DWP; series_id: dwp.exp.uk_welfare
      includes: [...]; excludes: [...]; scope: UK; notes: ...
    - id: welfare_cap           # benefits within the Welfare Cap: excludes State Pension and cyclical JSA/UC elements
    - id: dwp_ame_ex_pensions
    - id: cofog_social_protection   # PESA 10.1 function 10 (includes non-DWP spending, e.g. some local authority and public service pensions)
```

A definition whose series has no data is published with `series_id: null` and `status: "not available in slice 1"`.
It is never filled in.

---

## 10. Static API contract: `site/api/v1`

All JSON is UTF-8, `sort_keys`, with numbers as published (no rounding in the API; the site rounds for display).

**index.json**
```json
{"api_version":"v1","generated_at":"ISO8601","build":{"mode":"live|offline","git_sha":"...","rejected":0},
 "fiscal_years":{"from":"2015-16","latest_outturn":"2025-26"},
 "real_base_year":"2025-26","deflator":{"series_id":"obr.gdp_deflator","vintage":"OBR databank Sep 2026"},
 "sources":[{"id":"pesa","publisher":"HM Treasury","dataset":"...","verdict":"USABLE","licence":"OGL-3.0",
             "enabled":true,"stale_since":null,"deferred":null}],
 "series":[{"id":"pesa.cofog.health","title":"...","unit":"GBP_bn","source_id":"pesa","period_type":"fiscal_year",
            "monetary":true,"definition_id":null,"path":"series/pesa.cofog.health.json","years":["2015-16","2024-25"]}],
 "files":{"observations":"observations.parquet","provenance":"provenance.parquet",
          "all_vintages":"observations_all_vintages.parquet","reconciliation":"reconciliation.parquet"}}
```

**series/<series_id>.json**
```json
{"id":"...","title":"...","description":"...","source_id":"pesa","period_type":"fiscal_year","definition_id":null,
 "variants":{
   "nominal":[{"fiscal_year":"2015-16","value":4.33,"unit":"GBP_bn","status":"outturn","vintage":"PESA 2021",
               "provenance_id":"pesa.ab12cd34ef56ab78"}],
   "real":[...same shape, "unit":"GBP_bn_2025-26"...],
   "pct_gdp":[...same shape, "unit":"percent"...]},
 "gaps":[{"fiscal_year":"2025-26","reason":"COFOG not published in PESA 2026 (aggregates only)"}],
 "notes":["..."]}
```
Non-monetary series have only `nominal`. Every point has a `provenance_id`, with no exceptions.

**provenance/<source_id>.json**: `{"source_id":"pesa","records":{"<provenance_id>":{...all fields from section 7...,
"check":{...}}}}`. The `check` block:
```json
{"kind":"spreadsheet","download_url":"https://assets.publishing.service.gov.uk/...xlsx","landing_url":"https://www.gov.uk/...",
 "sheet":"10.1","cell":"B12","row_label":"Total general public services","column_label":"2015-16",
 "sha256":"4be4da7b...","published_value":4330,"published_unit":"GBP_m",
 "instructions":"Download the file, open sheet '10.1', go to cell B12 (row 'Total general public services', column '2015-16'). To confirm you have the same file: shasum -a 256 <file> should print 4be4da7b...",
 "derived_from":[...provenance ids, for derived values...]}
```
For API sources: `{"kind":"api","query_url":"https://...","json_path":"..."}`. xlsx and ods files cannot be
deep-linked to a cell, so the check is **file URL + sheet + cell + the labels + sha256**, and the reader can verify
their own download.

**"Check this number" link**: `check.html#p=<provenance_id>` (relative to the site root). `check.html` takes the
prefix before the first `.` as `source_id`, fetches `api/v1/provenance/<source_id>.json`, and renders the check block
with `textContent`. For derived values, it renders the transformation chain and links each input's own check.

**reconciliation.json**: `{"generated_at":...,"summary":{"pass":n,"fail":n,"info":n,"not_run":n},
"rules":[{"id":"R1","title":...,"description":...,"tolerance":{"abs":..,"rel":..,"unit":..},
"results":[{"fiscal_year":..,"edition":..,"left":{"series_id":..,"value":..,"provenance_id":..},
"right":{...},"delta":..,"delta_pct":..,"status":"pass|fail|info|not_run","reason":..}]}]}`

**definitions.json**: `{"groups":[{"id","title","definitions":[{"id","label","publisher","series_id","scope","includes","excludes","notes","status"}]}]}`

**claims.json**: see section 11. **corrections.json**: `{"corrections":[{"id","date","series_id","fiscal_year",
"what_was_wrong","what_changed","old_value","new_value","provenance_id"}]}` (from `data/corrections.yml`; an empty
list is valid).

**Parquet**: `observations.parquet`, `observations_all_vintages.parquet`, `provenance.parquet`,
`reconciliation.parquet` (same columns as the tables in section 7).

`check-api DIR [--live]` validates: every file above exists and parses; shapes match this section; every point's
`provenance_id` resolves to a complete record (gate in section 7) with an https `source_url` and a 64-hex sha256;
monetary headline series have all three variants; forecast points carry `status: forecast`; every rule R1 to R7
appears in reconciliation.json (including `not_run`); every claim resolves to a real point. `--live` also fails on any
`retrieval: fixture` record (refresh deploys live builds only).

---

## 11. Claim checker (`ukpm.claims`, `data/claims.yml` → `claims.json`)

```yaml
- id: c-0001
  text: "<claim exactly as stated>"
  said_by: "<person or organisation>"          # optional
  said_url: https://...                        # required: where the claim was made (https)
  said_date: 2026-..
  claimed: {value: 1.2, unit: GBP_tn, fiscal_year: "2024-25", price_basis: nominal}
  maps_to: {series_id: pesa.tme, definition_id: null}
  tolerance_rel: 0.02
```
The build computes, and never takes from the YAML: `official: {value, unit, status, vintage, provenance_id}`,
`verdict` ∈ `consistent | differs | not_comparable | no_official_figure`, `delta_pct`, and `check_url`. If the
claim's definition does not match the series definition, the verdict is `not_comparable`. A curator never types the
official figure or the verdict. `claims.yml` may ship **empty**. Example claims live only in test fixtures, so
the site never shows invented quotes. The site's search lists claims and also lets a reader pick a series and year to
see the official number with its check link.

---

## 12. CLI (`python -m ukpm`)

- `fetch [ids...]`: for each enabled source (or the given ids): download every file (section 5), update
  `data/fetched.json`, then run its parser and write `work/parsed/<id>.parquet`. Exit code is non-zero if a
  non-optional source fails and there is no cached file.
- `build [--offline]`: (offline: parse from the cache or fixtures first) → load `work/parsed/*.parquet` into DuckDB
  → provenance gate → stitch → conversions → reconcile → definitions → claims → write `site/api/v1` (writes to a temp
  dir, then swaps it in atomically).
- `check-api DIR [--live]`: section 10. Exit code 1 with a list of violations.

Parsers are found by `importlib.import_module(f"ukpm.parsers.{id}")`, so adding a source needs no change in core.

---

## 13. CI (`.github/workflows`)

All actions are **pinned by full commit SHA** (reuse the london-pulse pins: checkout `11d5960...` v4, setup-uv
`d0cc045...` v6, configure-pages `983d773...` v5, upload-pages-artifact `7b1f4a7...` v4, deploy-pages `d6db901...` v4).
Top-level `permissions: {}`, and each job declares only what it needs. No `${{ github.event.* }}` or
`inputs` is interpolated into `run:`. There are no secrets in slice 1.

- **refresh.yml**: `schedule: "23 5 * * *"` (daily, off the :00 mark) plus `workflow_dispatch`; `concurrency: ukpm-refresh`,
  no cancel. Job `update` (`contents: write`, `pages: write`): checkout → setup-uv → `uv sync --locked` → restore the
  raw cache from release `raw-cache` → `ukpm fetch` → `ukpm build` → `ukpm check-api site/api/v1 --live` → `pytest -q`
  (contract plus local smoke against `python -m http.server`) → upload new raw files to `raw-cache` → commit
  `data/fetched.json` and `site/api` only if they changed (rebase-retry loop as in london-pulse) → configure-pages →
  upload-pages-artifact `site`. Job `deploy` (`needs: update`; `pages: write`, `id-token: write`; environment
  `github-pages`) → deploy-pages. Any failed gate stops the run before commit and deploy, and the previous site stays live.
- **ci.yml**: push and pull_request; `contents: read`; `ruff check .`, `pytest -q`, `build --offline`,
  `check-api site/api/v1` (without `--live`). No network is needed.
- **smoke.yml**: `workflow_run` of refresh (only on `conclusion == success`) plus dispatch; `contents: read`;
  Playwright against the live Pages URL (`SMOKE_URL`).

---

## 14. Module ownership (matches `.swarm/plan.json`)

| task | owns |
|---|---|
| core | pyproject.toml, uv.lock, .gitignore, `src/ukpm/{__init__,__main__,fetch,provenance,registry,units}.py`, **`src/ukpm/sheets.py` (added by this design)**, `parsers/__init__.py`, `data/sources.yml`, `data/definitions.yml`, `data/corrections.yml`, `data/fetched.json` (initial), docs/SOURCES.md, tests/conftest.py, tests/test_core.py |
| parse-spend | `parsers/pesa.py` (per-edition LAYOUTS), `parsers/ons_psf.py` (optional; it must tolerate the source being disabled), tests/fixtures/spend/** |
| parse-obr | `parsers/obr.py` (databank aggregates, receipts, GDP, deflator; EFO economy member as optional fallback); **must verify and record the OBR licence**; tests/fixtures/obr/** |
| parse-revenue-welfare | `parsers/hmrc_receipts.py`, `parsers/hmrc_income_tax.py` (current plus historic 2.5a editions, stitched), `parsers/dwp_benefits.py` (Table 1a/1c, UK vs GB scope), tests/fixtures/{revenue,dwp}/** |
| build-api | `build.py`, `reconcile.py`, `claims.py`, `check_api.py`, site/api/**, **`data/claims.yml` (added)** |
| test-parsers | tests/test_parsers_{spend,obr,revenue_welfare}.py, tests/test_reconcile.py |
| test-contract | tests/test_contract.py, tests/test_build.py |
| site | site/*.html (including `check.html`), site/assets/**, site/config.js |
| ci | .github/workflows/**, scripts/** |
| test-smoke | tests/smoke/** |
| docs | README.md, docs/METHODOLOGY.md, docs/CORRECTIONS.md, docs/API.md |

---

## 15. Risks and edge cases

- **OBR licence not verified**: this blocks every OBR value, including the deflator and GDP, so the real and % GDP
  toggles depend on it. It is the first thing `parse-obr` must resolve.
- **Mixed vintages**: a stitched series mixes editions (PESA 2021 for 2015-16, PESA 2026 for 2024-25). The vintage is
  shown per point and the site states it. Arithmetic checks stay within a single edition.
- **Upstream URL churn**: gov.uk asset URLs change on every edition. A new edition means a new `files[]` entry (a
  reviewed PR), never auto-discovery in slice 1. The daily refresh detects changed bytes at known URLs.
- **Rate limits (ONS 429, OBR 403)**: retries with backoff (max 3), the cached last-good file, and `stale_since`.
- **Label drift inside an edition update** (for example the PESA December update): the parser raises `LayoutChanged`,
  and the cached previous file is used for publishing until the parser is fixed.
- **Tax year vs fiscal year, UK vs GB scope, cash vs accrued**: these are labelled in SERIES and definitions and
  never silently aligned.

## 16. Out of scope (slice 1)

Spend over £25k, Contracts Finder, Stat-Xplore, ONS LMS/labour, PAYE RTI, ETB household incidence, debt stocks and
GDP centred end-March, departmental budgets beyond PESA chapter 5 totals, auto-discovery of new editions, any
interpolation or nowcasting, and any server-side component.
