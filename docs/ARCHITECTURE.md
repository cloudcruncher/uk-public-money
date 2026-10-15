# UK Public Money: architecture

A static site on GitHub Pages that shows UK government spending and revenue from 2015-16 to the latest outturn year. It uses official open data only. It follows the london-pulse pattern: uv, DuckDB and Parquet, a static versioned API under `site/api/v1`, a scheduled GitHub Actions refresh, contract tests, and Playwright smoke tests. There are no servers.

**Trust rule:** no number is published unless it has a complete provenance record (publisher, dataset, publication date, source URL, file sha256, sheet and cell or API query, licence, transformations). The API writer enforces this rule, and `check-api` checks it again. Reconciliation results are published, including failures.

Inputs to this design: `docs/sources/spend.md` and `docs/sources/revenue-welfare.md` (scout verdicts, 2026-10-15).

---

## 1. Source decisions (first slice)

| source_id | What it supplies | Verdict | Used for |
|---|---|---|---|
| `pesa` | HMT PESA: Table 10.1 COFOG (TES by function, £m) and Table 4.1 aggregates (TME, £bn) | USABLE | COFOG split for 2015-16 to 2024-25. TME 4.1 to 2025-26 outturn, plus the 2026-27 forecast |
| `obr` | OBR Public Finances Databank, Sept 2026 (`PSF_aggregates_databank_Sep-3.xlsx`) | USABLE (licence UNVERIFIED, see risk R1) | Headline TME, current receipts, net borrowing, nominal GDP, GDP deflator, 2015-16 to 2025-26 outturn plus forecast years |
| `hmrc_receipts` | HMRC tax and NICs receipts `NS_Table.ods`, sheet `Receipts_Annually` | USABLE | Receipts by tax ("Where £1 comes from") |
| `hmrc_income_tax` | HMRC Table 2.5 (liabilities by income range), Table 2.1 (taxpayer numbers) | PARTIAL | "Who pays" from 2023-24 onward only (see gaps) |
| `dwp_benefits` | DWP outturn and forecast tables, Spring Forecast 2026 xlsx: Table 1a (nominal spend by benefit), 1c (caseloads), "UK welfare" / "GB welfare" tabs | USABLE | Benefits page, welfare definitions |
| `ons_psf` | ONS Public Sector Finances | **UNVERIFIED** | Optional cross-check only. Disabled (`enabled: false`) until a URL returns 200 |

### Known gaps and what replaces each one

These go into `data/sources.yml` and are also published in `index.json.coverage_gaps`, so the site shows them.

1. **ONS PSF is UNVERIFIED.** The guessed bulletin, dataset and time-series URLs returned 404, and later 429. Nothing was downloaded. **Replacement:** TME, current receipts and net borrowing come from the **OBR Public Finances Databank (Sept 2026)**. PESA Table 4.1 aggregates serve as a second, independent TME. `src/ukpm/parsers/ons_psf.py` is written as an optional cross-check parser for the ONS generator CSV format (the same format as the verified LMS MGRZ CSV: metadata rows first, then `"YYYY"` / `"YYYY Qn"` / `"YYYY MMM"` rows). It stays disabled until someone records a real ONS URL that returned 200, with its sha256. Never invent the URL. While it is disabled, its reconciliation rules report `not_run`.
2. **OBR historical official forecasts database is UNUSABLE.** The URL returns an access page, not a workbook. **Replacement:** each source's own outturn/forecast labelling. The PESA 4.1 header says "Outturn data in this table up to 2025-26". The OBR databank and the DWP tables mark forecast years. The OBR forecast revisions database (PARTIAL) is out of the first slice.
3. **PESA COFOG 10.1 stops at 2024-25.** The 2026 edition has 2020-21 to 2024-25, and only Table 4.1 aggregates for 2025-26. **Handling:** COFOG series end at 2024-25. "Where £1 goes" defaults to 2024-25 and says so. Aggregate series (TME) run to 2025-26. A gap is recorded: `pesa.cofog.*`, missing `2025-26`, "not yet published in PESA 10.1".
4. **HMRC income tax Table 2.5: the current edition covers 2023-24 onward (PARTIAL).** 2015-16 to 2022-23 need archive editions (historic Table 2.5a, landing page https://www.gov.uk/government/statistics/income-tax-liabilities-by-income-range--2, not yet downloaded). **Handling:** publish 2023-24 onward. Label 2023-24 as outturn (Survey of Personal Incomes based) and later years as `projection` (`status: forecast`). A gap is recorded for 2015-16 to 2022-23. `parse-revenue-welfare` may add archive editions only after their file URLs have returned 200 and been recorded with sha256 in `sources.yml`.
5. **DWP Stat-Xplore needs an API key (PARTIAL), and its licence is unverified.** It is out of the first slice. **Replacement:** DWP Spring Forecast 2026 xlsx, Table 1a for spend and Table 1c for caseloads.
6. Out of the first slice (PARTIAL, not used): ONS LMS, HMRC PAYE RTI, ONS effects of taxes and benefits, OBR EFO detail and charts zips, OBR historical PF database, OBR July 2025 annexes. They stay in `sources.yml` with `enabled: false` so the register is complete.

---

## 2. Repo layout

```
pyproject.toml            # [tool.uv] package = false; [tool.pytest.ini_options] pythonpath = ["src"]
uv.lock
data/
  sources.yml             # source register (schema in section 3)
  definitions.yml         # side-by-side definitions (section 9)
  corrections.yml         # corrections log (section 10)
src/ukpm/
  __init__.py
  __main__.py             # CLI: fetch | build | check-api
  registry.py             # load and validate sources.yml
  fetch.py                # download, sha256, manifest, offline fixture resolution
  sheets.py               # one spreadsheet reader for xlsx and ods (python-calamine)
  provenance.py           # Provenance, Row, Transformation dataclasses; validate(); provenance_id()
  units.py                # scale, deflate, pct_gdp (each appends a Transformation)
  parsers/__init__.py     # parser contract docs plus helpers (fiscal year normalisation, A1 addressing)
  parsers/{pesa,obr,ons_psf,hmrc_receipts,hmrc_income_tax,dwp_benefits}.py
  build.py                # DuckDB load, conversions, provenance gate, API writer
  reconcile.py            # rules, plus reconciliation.json
  claims.py               # claims index
  check_api.py            # independent validator of site/api/v1
site/                     # plain HTML/CSS/JS, no build step; reads only site/api/v1
  api/v1/...              # generated (section 7), committed by the refresh workflow
tests/
  fixtures/{spend,obr,revenue,dwp}/  # trimmed real files plus MANIFEST.yml
  smoke/                  # Playwright
work/                     # gitignored: raw/, parsed/, ukpm.duckdb
scripts/serve.sh
.github/workflows/{ci,refresh,smoke}.yml
```

Dependencies: `duckdb`, `python-calamine` (reads xlsx and ods, with no macro execution and no XML entity expansion), `openpyxl` (only for writing trimmed xlsx fixtures and in tests), `pyyaml`. Fetching uses stdlib `urllib`. Dev dependencies: `pytest`, `ruff`, `playwright`. Run everything with `PYTHONPATH=src uv run ...`.

`sheets.py` (owned by `core`): `open_book(path) -> Book`, with `Book.sheet_names` and `Book.rows(sheet) -> list[list[Any]]`, where row 0 is spreadsheet row 1 and column 0 is A. Call `to_python(skip_empty_area=False)` so indices map to real A1 addresses. Also `a1(row_idx, col_idx) -> "B46"` and `find(sheet, text) -> (r, c)` for label anchoring. A test must check that the A1 mapping matches openpyxl on an xlsx fixture.

---

## 3. `data/sources.yml`

The file has one entry per source, and each source lists its files. Every file URL is pinned. A new edition means a PR that adds a file entry after it has been verified (HTTP 200 and a recorded sha256). This keeps every published number traceable to bytes someone has inspected.

```yaml
- id: pesa                         # also the parser module name: ukpm.parsers.pesa
  publisher: HM Treasury
  dataset: Public Expenditure Statistical Analyses (PESA)
  landing_url: https://www.gov.uk/government/collections/public-expenditure-statistical-analyses-pesa
  licence: OGL-UK-3.0              # allowlist: OGL-UK-3.0 only, for now
  licence_evidence: "gov.uk footer: Open Government Licence v3.0 (checked 2026-10-15)"
  cadence: annual (July), occasional December update
  coverage: {from: 2015-16, to: 2024-25, note: "COFOG 10.1; 4.1 aggregates to 2025-26 outturn"}
  verdict: USABLE                  # USABLE | PARTIAL | UNVERIFIED | UNUSABLE
  enabled: true                    # fetch/build skip disabled sources (exit 0, logged)
  fixture_dir: tests/fixtures/spend
  user_agent: null                 # obr needs a browser UA (bare curl gets 403)
  files:
    - key: pesa_2026_ch10          # unique within the source
      edition: PESA 2026
      publication_date: 2026-07-16
      file_url: https://assets.publishing.service.gov.uk/media/6a57736c6d6d5c7e2845c9d6/PESA_2026_CP_Chapter_10_tables.xlsx
      landing_url: https://www.gov.uk/government/statistics/public-expenditure-statistical-analyses-2026
      format: xlsx                 # xlsx | ods | csv | zip
      sha256: baaa63b96fc3ba066d20d90add268c98f871718ccadf15b75babf922e006d934
      role: cofog_10_1             # tells the parser which layout to expect
  gaps:
    - {series: "pesa.cofog.*", years: ["2025-26"], reason: "PESA 2026 10.1 ends at 2024-25 outturn"}
```

Validation in `registry.load(path) -> list[Source]` raises on: a missing key; a duplicate id or file key; a non-https URL; a host outside the allowlist (`assets.publishing.service.gov.uk`, `www.gov.uk`, `obr.uk`, `www.ons.gov.uk`, `api.beta.ons.gov.uk`); `enabled: true` with a verdict other than USABLE/PARTIAL; `enabled: true` with a file that has no `sha256`; a licence outside the allowlist on an enabled source; a non-ISO `publication_date`. Disabled sources may have `file_url: null` (ons_psf, stat_xplore).

The first-slice `files:` entries use the URLs and sha256 values recorded by the scouts. For `pesa`: the chapter 10 files for the 2021, 2023, 2024, 2025 and 2026 editions, and the chapter 4 file for 2026. For `obr`: the Sept 2026 databank. For `hmrc_receipts`: `NS_Table.ods`. For `hmrc_income_tax`: Tables 2.5 and 2.1. For `dwp_benefits`: Spring Forecast 2026 xlsx. The 2025 edition chapter 10 is listed in the notes and should cover 2019-20. Confirm that against the file.

---

## 4. Fetch layer (`fetch.py`)

```python
@dataclass(frozen=True)
class FetchedFile:
    source_id: str; file_key: str; path: Path
    sha256: str            # sha256 of the ORIGINAL published file (always)
    url: str; final_url: str; fetched_at: str  # ISO UTC
    size: int; content_type: str
    from_fixture: bool

def fetch_source(src: Source, *, offline: bool) -> list[FetchedFile]
```

- **Online:** GET `file_url`, following redirects to allowlisted hosts only, with a 60 s timeout and 3 retries with backoff. Reject anything larger than 25 MB (streamed count). Hash while streaming. Write to `work/raw/<source_id>/<sha256>.<ext>`, where the filename comes from the hash, never from the URL or a header. If the hash differs from the pinned `sha256`, **fail** for that source with "publisher replaced file in place; re-verify and update sources.yml". The refresh then fails and yesterday's site stays live.
- **Cache:** `work/raw/manifest.json` maps `sha256 -> {source_id, file_key, url, final_url, fetched_at, size, content_type}`. If a file with the pinned sha256 already exists, it is not downloaded again.
- **Offline** (`--offline`): no network. The file is resolved by pinned sha256 from (1) the `work/raw` cache, then (2) `<fixture_dir>/MANIFEST.yml`. If neither has it, the source is reported as `skipped (no offline copy)`. That is not an error, but the build records it in `index.json.skipped_sources`.
- **Zip** (OBR EFO, later): read members in memory. Reject absolute or `..` names, more than 50 members, or more than 200 MB uncompressed in total.
- `fetch` also parses. After download, `ukpm fetch <ids>` calls the parser and writes `work/parsed/<source_id>.parquet` (the done-criteria of the parse tasks depend on this).

### Fixtures (offline CI)

`tests/fixtures/<area>/MANIFEST.yml`:

```yaml
- source_id: pesa
  file_key: pesa_2026_ch10
  fixture: pesa_2026_ch10.xlsx
  original_sha256: baaa63b9...      # equals sources.yml sha256
  original_url: https://assets.publishing.service.gov.uk/...
  fixture_sha256: <sha of the trimmed file>
  kept_sheets: ["10.1"]
```

Trimming rule: keep only the sheets the parser reads. Inside them, keep every cell the parser reads, including label/anchor cells, **at the same address**. Other cells may be blanked. ODS originals may be saved as xlsx. With this rule, an offline parse produces the same values and cell references as an online parse, and `file_sha256` in provenance is always `original_sha256`. Each fixture must be 300 KB or less. Fixtures are made by a throwaway script in the scratchpad, not by repo code.

---

## 5. Parser contract

Each module `ukpm.parsers.<source_id>` exposes:

```python
def parse(path: Path, meta: FileMeta) -> list[Row]           # required; one call per file
def combine(rows: list[Row]) -> list[Row]                    # optional; across files of the source (default identity)
```

`FileMeta` is the source entry, the file entry and the `FetchedFile`. The CLI imports parsers with `importlib.import_module(f"ukpm.parsers.{source_id}")`, so adding a parser needs no change to core.

```python
@dataclass(frozen=True)
class Transformation:
    op: str        # scale | sign | select_edition | label_map | sum | deflate | pct_gdp | rebase
    detail: str    # human-readable, e.g. "£m -> £bn (x 0.001)"
    inputs: tuple[str, ...] = ()   # provenance_ids used (derived values only)

@dataclass(frozen=True)
class Provenance:
    publisher: str; dataset: str; edition: str
    publication_date: str          # ISO date
    source_url: str                # direct file URL (https)
    landing_url: str               # human page for the edition (https)
    file_sha256: str               # 64 hex, original file
    sheet: str | None
    cell_or_range: str | None      # "M46" or "B12:F12"; required if sheet set
    api_query: str | None          # required when sheet is None
    licence: str                   # in allowlist
    transformations: tuple[Transformation, ...]
    status: str                    # outturn | forecast
    vintage: str                   # e.g. "PESA 2026", "OBR PFD Sep 2026", "DWP Spring Forecast 2026"
    retrieved_at: str              # ISO UTC from FetchedFile

@dataclass(frozen=True)
class Row:
    series_id: str                 # "<source_id>.<measure>[.<breakdown>]"
    fiscal_year: str               # "2015-16" (normalised from 2015/16, 2015-2016, etc.)
    period_basis: str              # fiscal_year (1 Apr) | tax_year (6 Apr)
    value: float                   # as published after recorded scaling only
    unit: str                      # gbp_bn | count_thousands | count | pct
    geography: str                 # UK | GB | England ... as stated in the table title
    prov: Provenance
```

Parser rules:

- **Find cells by label, never by hard-coded address.** For example, find the row whose column-A text is "Total expenditure on services" and the header row containing "2024-25", then record the resolved A1 address. If an anchor text is missing, raise `LayoutError(file_key, anchor)`. Do not guess.
- Money is normalised to `gbp_bn`. PESA 10.1 £m becomes £bn with a `scale` transformation. Values are never rounded.
- `status` comes from the source's own marking: the PESA header "Outturn data ... up to YYYY-YY", forecast columns in OBR and DWP, and HMRC projections. If the status cannot be determined, raise.
- `pesa.combine`: for each `(series_id, fiscal_year)`, keep the row from the **latest edition** that covers the year. Append `select_edition` with the detail "PESA 2026 used; also in PESA 2024, 2025 (restated)". The scouts recorded a restatement: 2015-16 general public services was 4880 in the 2017 edition and 4330 in the 2021 edition.
- `geography` comes from the table title (DWP has both UK and GB tabs; record which one Table 1a is).
- `fetch` writes rows to `work/parsed/<id>.parquet` flattened: the Row columns plus every Provenance field as a column, with `transformations` as a JSON string. `file_sha256`, `source_url` and `status` must be columns.

Series ids (first slice):

| series_id | Source cells | Unit |
|---|---|---|
| `pesa.tes`, `pesa.cofog.<fn>` (`general_public_services`, `defence`, `public_order_safety`, `economic_affairs`, `environment_protection`, `housing_community`, `health`, `recreation_culture_religion`, `education`, `social_protection`), plus `pesa.cofog.eu_transactions` where present | 10.1 | gbp_bn |
| `pesa.tme` | 4.1 | gbp_bn |
| `obr.tme`, `obr.receipts` (public sector current receipts), `obr.psnb`, `obr.gdp_nominal` | Databank "Aggregates (£bn)" | gbp_bn |
| `obr.gdp_deflator` | Databank (column located by header). If it is absent, fall back to the EFO March 2026 economy table, which is PARTIAL and must be inspected and verified first | index |
| `obr.tme_real_published`, `obr.tme_pct_gdp_published` | "Aggregates (2025-26 prices)", "Aggregates (per cent of GDP)": used only for reconciliation | gbp_bn / pct |
| `hmrc_receipts.total`, `hmrc_receipts.<tax>` (income_tax, nics, vat, corporation_tax, fuel_duties, ...) | `Receipts_Annually` | gbp_bn |
| `hmrc_income_tax.taxpayers.<band>`, `hmrc_income_tax.liability.<band>`, `.total` | 2.5 per-year sheets, 2.1 | count_thousands / gbp_bn (`period_basis: tax_year`) |
| `dwp_benefits.<benefit>`, `dwp_benefits.total_uk_welfare`, `dwp_benefits.welfare_cap`, `dwp_benefits.caseload.<benefit>` | Table 1a, 1c, "UK welfare" | gbp_bn / count_thousands |
| `ons_psf.tme`, `ons_psf.receipts`, `ons_psf.psnb` | disabled | gbp_bn |

---

## 6. Canonical store (DuckDB / Parquet)

`build.py` loads every `work/parsed/*.parquet` into `work/ukpm.duckdb` and produces two tables.

```sql
CREATE TABLE provenance (
  provenance_id TEXT PRIMARY KEY,   -- "<source_id>-<first 12 hex of sha256(canonical JSON of record)>"
  kind TEXT,                        -- source | derived
  publisher TEXT, dataset TEXT, edition TEXT, publication_date DATE,
  source_url TEXT, landing_url TEXT, file_sha256 TEXT,
  sheet TEXT, cell_or_range TEXT, api_query TEXT, licence TEXT,
  transformations JSON, status TEXT, vintage TEXT, retrieved_at TIMESTAMP
);
CREATE TABLE values_long (
  series_id TEXT, fiscal_year TEXT, period_basis TEXT,
  value DOUBLE, unit TEXT,
  price_basis TEXT,                 -- nominal | real | pct_gdp | none (counts, indices)
  status TEXT, geography TEXT,
  provenance_id TEXT REFERENCES provenance,
  PRIMARY KEY (series_id, fiscal_year, price_basis)
);
```

A derived record (real, % of GDP, sums) has `kind: derived`. It copies `source_url`, `file_sha256`, `sheet` and `cell_or_range` from its primary input, and its `transformations` carry the full chain plus the `inputs` provenance_ids, which must all be complete. Its `status` is `forecast` if any input is a forecast. The canonical JSON used for hashing has sorted keys and excludes `retrieved_at`, so ids stay stable between runs.

### Provenance gate

`provenance.validate(p) -> list[str]` returns the missing or invalid fields. A record is incomplete if any of the following holds:

- a required field is empty
- a URL is not https or its host is outside the allowlist
- `file_sha256` is not 64 hex characters
- the licence is outside the allowlist (so `UNVERIFIED` fails)
- neither `sheet` + `cell_or_range` nor `api_query` is present
- `status` is not in {outturn, forecast}
- a derived record has an unresolvable input

`build.write_api` calls the gate for every value. A failing value is **dropped**, never published. It is logged and listed in `index.json.rejected` as `{series_id, fiscal_year, price_basis, missing: [...]}`. The writer has no code path that emits a value without a `provenance_id` that resolves to a complete record.

## 7. Unit conversions (`units.py`)

Every function returns a new Row/Provenance pair with one Transformation appended:

- `scale(row, factor, detail)`: for example, £m to £bn.
- `deflate(row, deflator_rows, base_year)`: `real = nominal × D[base] / D[year]`. The deflator is the GDP deflator `obr.gdp_deflator` from the same OBR vintage. **Base year = the latest outturn year in the OBR databank (2025-26)**, so the result is "2025-26 prices", which matches OBR's own "Aggregates (2025-26 prices)" sheet and lets reconciliation rule R5 check it. The detail reads, for example, "GDP deflator, OBR PFD Sep 2026, 2025-26=100". The base year is published in `index.json.price_base`.
- `pct_gdp(row, gdp_rows)`: `100 × value / obr.gdp_nominal[year]`. The status is forecast if the GDP figure is a forecast.
- Real and % of GDP versions are produced only for `unit == gbp_bn`. Counts get `price_basis: none`. If a denominator for a year is missing, that variant is not produced and the build records `variant_missing` in index.json. Nothing is extrapolated.
- **Tax years:** HMRC income tax values are on a tax-year basis. They are deflated and divided by GDP using the fiscal year with the same label, and the Transformation detail says so. The site labels them "tax year".

---

## 8. Reconciliation (`reconcile.py`)

Rules are defined in code as a list of `Rule(id, title, kind, lhs, rhs, tolerance, explanation)`. Every rule is evaluated for every fiscal year where it applies, and every result is written out. A failure never stops the build and is never hidden.

| id | Check | kind | Tolerance |
|---|---|---|---|
| R1 `cofog_sum_tes` | Sum of `pesa.cofog.*` (incl. EU transactions) = `pesa.tes`, same edition and year | equality | abs 0.05 £bn (rounding in £m tables) |
| R2 `tes_vs_tme` | `pesa.tes` vs `pesa.tme`. COFOG tables are **TES, not TME**. TME = TES + accounting adjustments | bounded_gap | gap within ±5% of TME. The site explains that the gap is expected |
| R3 `pesa_tme_vs_obr_tme` | `pesa.tme` vs `obr.tme` | equality | rel 1% (PESA July and OBR Sept vintages differ) |
| R4 `hmrc_vs_obr_receipts` | `hmrc_receipts.total` vs `obr.receipts` | bounded_gap | HMRC/OBR ratio in [0.80, 0.98]. HMRC excludes council tax, business rates and other non-HMRC receipts |
| R5 `real_tme_vs_obr` | Our `obr.tme` real (2025-26 prices) vs `obr.tme_real_published` | equality | rel 0.5% |
| R6 `pct_gdp_vs_obr` | Our `obr.tme` pct_gdp vs `obr.tme_pct_gdp_published` | equality | abs 0.1 pp |
| R7 `dwp_vs_cofog_sp` | `dwp_benefits.total_uk_welfare` vs `pesa.cofog.social_protection` | bounded_gap | DWP/COFOG ratio in [0.6, 1.0]. The scopes differ, and the site shows both definitions side by side |
| R8 `psf_vs_obr` | `ons_psf.tme`, `ons_psf.receipts` vs OBR | equality | rel 1%. `not_run` while ons_psf is disabled |

Each result has a status: `pass`, `fail`, or `not_run` (with the reason, such as a missing input or a disabled source). The tolerances above are starting values. A builder who changes one must give the reason in the rule's `explanation`, never just to make a check pass.

---

## 9. Definitions registry (`data/definitions.yml`)

```yaml
- id: welfare_dwp_ame
  label: DWP benefit spending (AME)
  short: "Benefits paid by DWP, demand-led budget"
  includes: [State Pension, Universal Credit, PIP, Housing Benefit, ...]
  excludes: [Tax credits (HMRC, pre-UC), departmental admin]
  source_id: dwp_benefits
  series_ids: [dwp_benefits.total_uk_welfare]
  notes: "Table 1a. Geography as stated in the table."
```

The minimum set is: `welfare_dwp_ame`, `welfare_cap` (excludes State Pension and the most cyclical benefits, includes some non-DWP spending and Northern Ireland), `uk_welfare_total` (the DWP "UK welfare" tab), `cofog_social_protection` (PESA function 10), `tme`, `tes`, `public_sector_current_receipts`, `hmrc_receipts`, `income_tax_liabilities` (tax-year basis, income tax only, no NICs). Each definition used on the site must list at least one `series_id`, and `check-api` verifies that the id exists.

## 10. Corrections (`data/corrections.yml`)

`[]` to start. Each entry has: `{id, date, series_id, fiscal_year, price_basis, old_value, new_value, old_provenance_id, new_provenance_id, reason, reported_by (optional, public), status: open|fixed}`. The file is copied as-is to `corrections.json`.

---

## 11. Static API contract: `site/api/v1`

All files are UTF-8 JSON. Every file has `"api_version": 1`. Paths are relative to `site/api/v1`. Numbers are JSON numbers and are never rounded.

**`index.json`**
```json
{"api_version":1,"generated_at":"2026-10-15T05:23:00Z","build":{"git_sha":"...","offline":false},
 "price_base":"2025-26","latest_outturn":{"aggregates":"2025-26","cofog":"2024-25"},
 "series":[{"id":"pesa.cofog.health","title":"Health (COFOG)","unit":"gbp_bn","bases":["nominal","real","pct_gdp"],
            "years":["2015-16","2024-25"],"definition_id":"cofog_health","file":"series/pesa.cofog.health.json"}],
 "headlines":{"spend_total":"obr.tme","receipts_total":"obr.receipts","borrowing":"obr.psnb","spend_by_function":"pesa.cofog.*"},
 "sources":[{"id":"pesa","publisher":"HM Treasury","verdict":"USABLE","enabled":true,"licence":"OGL-UK-3.0"}],
 "coverage_gaps":[{"series":"hmrc_income_tax.*","years":["2015-16","2022-23"],"reason":"..."}],
 "skipped_sources":[{"id":"ons_psf","reason":"verdict UNVERIFIED; no verified URL"}],
 "rejected":[], "variant_missing":[],
 "files":{"reconciliation":"reconciliation.json","definitions":"definitions.json","claims":"claims.json",
          "corrections":"corrections.json","parquet":["values.parquet","provenance.parquet"]}}
```

**`series/<series_id>.json`**
```json
{"api_version":1,"id":"pesa.cofog.health","title":"Health (COFOG)","unit":"gbp_bn","period_basis":"fiscal_year",
 "geography":"UK","definition_id":"cofog_health","source_id":"pesa",
 "points":[{"fiscal_year":"2024-25","status":"outturn","vintage":"PESA 2026",
            "values":{"nominal":{"v":220.1,"p":"pesa-1a2b3c4d5e6f"},
                      "real":{"v":226.4,"p":"pesa-..."},
                      "pct_gdp":{"v":7.6,"p":"pesa-..."}}}]}
```
(The values shown are placeholders for the shape only.)

**`provenance/<source_id>.json`**: sharded by the id prefix, so the client fetches one shard per source.
```json
{"api_version":1,"source_id":"pesa","records":{"pesa-1a2b3c4d5e6f":{
  "kind":"source","publisher":"HM Treasury","dataset":"PESA","edition":"PESA 2026","publication_date":"2026-07-16",
  "source_url":"https://assets.publishing.service.gov.uk/.../PESA_2026_CP_Chapter_10_tables.xlsx",
  "landing_url":"https://www.gov.uk/...","file_sha256":"baaa63b9...","sheet":"10.1","cell_or_range":"F20",
  "api_query":null,"licence":"OGL-UK-3.0","status":"outturn","vintage":"PESA 2026","retrieved_at":"...",
  "transformations":[{"op":"scale","detail":"£m -> £bn (x 0.001)","inputs":[]}],
  "check_url":"https://assets.publishing.service.gov.uk/.../PESA_2026_CP_Chapter_10_tables.xlsx",
  "check_hint":"Open sheet 10.1, cell F20 (£ million)"}}}
```

**`reconciliation.json`**
```json
{"api_version":1,"summary":{"pass":0,"fail":0,"not_run":0},
 "rules":[{"id":"R1","name":"cofog_sum_tes","title":"...","kind":"equality","tolerance":{"abs":0.05},
   "explanation":"...","results":[{"fiscal_year":"2024-25","status":"pass","lhs":1.0,"rhs":1.0,"delta":0.0,
   "delta_pct":0.0,"lhs_p":["pesa-..."],"rhs_p":["pesa-..."],"reason":null}]}]}
```

**`definitions.json`**: `{"api_version":1,"definitions":[...definitions.yml entries...]}`.
**`claims.json`**: `{"api_version":1,"claims":[{"id":"pesa.cofog.health:2024-25:nominal","text":"Health spending in 2024-25","keywords":["health","nhs","spending"],"series_id":"...","fiscal_year":"...","price_basis":"nominal","value":0,"unit":"gbp_bn","status":"outturn","provenance_id":"...","check_url":"https://..."}]}`. This is generated from the series in `index.json.headlines` and from every `pesa.cofog.*`, `hmrc_receipts.*` and `dwp_benefits.*` (non-caseload) series × year × basis. In the claim-checker scaffold, the user's text is matched to entries by keywords and year. No free-text number extraction is done in the first slice.
**`corrections.json`**: `{"api_version":1,"corrections":[...]}`.
**`values.parquet`, `provenance.parquet`**: exports of the two DuckDB tables, for analysts.

### "Check this number" link

For a value `{v, p}`, the site loads `provenance/<p.split("-")[0]>.json` and renders `<a href=record.check_url>Check this number</a>` with `record.check_hint` next to it, plus a popover with every provenance field and the transformation chain. `check_url` is the direct file URL (`source_url`). The hint tells the user which sheet and cell to open. For derived values, the popover lists the inputs, each with its own link. The site only renders hrefs whose scheme is `https:` and whose host is in the allowlist, and it uses `textContent` only.

### `check-api DIR` (`check_api.py`) fails (exit 1, with a list of problems) on any of these

- a JSON file missing or failing to parse, or missing `api_version: 1`
- a series file listed in index.json that does not exist
- any point value whose `p` does not resolve to a record in its shard
- any provenance record that fails `provenance.validate`
- a `source_url`, `landing_url` or `check_url` that is not https or not on an allowlisted host
- a value where `v` is non-finite
- a `status` outside {outturn, forecast}
- a headline money series missing a `nominal`, `real` or `pct_gdp` variant for a year where the denominators exist
- a reconciliation rule in code that is absent from the file
- a claim that does not match the series value
- a definition series_id that does not exist

Total size of `site/api/v1` must be 20 MB or less.

---

## 12. CLI (`python -m ukpm`)

| Command | Behaviour |
|---|---|
| `fetch [SOURCE ...] [--offline]` | No ids means all enabled sources. Downloads (or resolves the offline copy), verifies sha256, parses, and writes `work/parsed/<id>.parquet`. Disabled or unknown-offline sources print `skipped: <reason>` and exit 0. A sha mismatch, `LayoutError` or provenance gap exits 1 |
| `build [--offline] [--out site/api/v1]` | Runs `fetch` for all enabled sources (same offline flag), then loads DuckDB, converts units, applies the gate, reconciles, builds claims, writes the API, and runs `check-api` on the output. Exits 1 if `check-api` fails |
| `check-api DIR` | Standalone validator (section 11) |

Because fixtures keep the original cells, `build --offline` from fixtures gives the same values as an online build with the pinned files. Only `generated_at`, `build` and `retrieved_at` differ. Developers can therefore run the gates locally without changing the published numbers.

---

## 13. CI workflows

All actions are pinned by commit SHA (reuse the london-pulse pins: `actions/checkout@11d5960a…`, `astral-sh/setup-uv@d0cc045d…`, `actions/configure-pages@983d7736…`, `actions/upload-pages-artifact@7b1f4a76…`, `actions/deploy-pages@d6db9016…`). Top level: `permissions: {}`. Each job declares only what it needs. Never interpolate `${{ github.event.* }}` into `run:`.

- **`ci.yml`**: on push and pull_request, `contents: read`. Steps: `uv sync --locked`, `uv run ruff check .`, `uv run pytest -q --ignore=tests/smoke`, `PYTHONPATH=src uv run python -m ukpm build --offline`, `check-api site/api/v1`, then a local Playwright smoke run against `python3 -m http.server` on `site/`.
- **`refresh.yml`**: `schedule: cron "23 5 * * *"` (off the :00 mark) and `workflow_dispatch`, with `concurrency: {group: ukpm-refresh, cancel-in-progress: false}`.
  - Job `update` (`contents: write`): sync, `build` (online), `check-api`, pytest, local Playwright smoke. If any step fails, nothing is committed or deployed. Then commit `site/api` only if it changed (bot identity, pull --rebase retry loop as in london-pulse), `configure-pages`, `upload-pages-artifact` (path `site`).
  - Job `deploy` (`needs: update`; `pages: write`, `id-token: write`; environment `github-pages`): `deploy-pages`.
  - Cache `work/raw` with `actions/cache` (pinned SHA) keyed on `hashFiles('data/sources.yml')`.
- **`smoke.yml`**: on `workflow_run` of refresh (completed, conclusion success) and `workflow_dispatch`, `contents: read`. Runs the Playwright tests against `SMOKE_URL=https://<owner>.github.io/uk-public-money/`.
- **`scripts/serve.sh`**: `python3 -m http.server` on `site/` (no secrets to inject).

---

## 14. Site (summary for the designer)

Pages: `index.html` (Where £1 goes, COFOG shares of TES for the selected year, default 2024-25), `comes-from.html` (receipts by tax), `benefits.html` (DWP spend and caseload, with the welfare definitions side by side and R7 shown), `who-pays.html` (income tax by band, 2023-24 onward, with the gap note), `check.html` (claim checker, plus provenance lookup by `#p=<id>`), `about.html`, `methodology.html`, `corrections.html`.

Shared rules:

- A global toggle for nominal, real (2025-26 prices) and % of GDP, persisted in the URL hash.
- Forecast years are shown with a hatched or dashed style **and** a text label ("forecast"), so colour is never the only signal.
- A reconciliation status panel on every page, showing a fail count and linking to details.
- Coverage gaps are shown where they apply.
- No third-party scripts. A CSP meta tag with `default-src 'self'`.

---

## 15. Module ownership (matches `.swarm/plan.json`)

| Task | Owns |
|---|---|
| core | pyproject.toml, uv.lock, .gitignore, `src/ukpm/{__init__,__main__,fetch,provenance,registry,units}.py`, **`src/ukpm/sheets.py`** (added by this design; core owns it), `parsers/__init__.py`, `data/{sources,definitions,corrections}.yml`, docs/SOURCES.md, tests/{conftest,test_core}.py |
| parse-spend | `parsers/{pesa,ons_psf}.py`, tests/fixtures/spend/** |
| parse-obr | `parsers/obr.py`, tests/fixtures/obr/**. Must also fetch the OBR copyright/licence page and give core the quote for `licence_evidence` (risk R1) |
| parse-revenue-welfare | `parsers/{hmrc_receipts,hmrc_income_tax,dwp_benefits}.py`, tests/fixtures/{revenue,dwp}/** |
| build-api | `src/ukpm/{build,reconcile,claims,check_api}.py`, site/api/** |
| test-parsers / test-contract | tests listed in the plan |
| site | site/*.html, site/assets/**, site/config.js |
| ci | .github/workflows/**, scripts/** |
| docs | README.md, docs/{METHODOLOGY,CORRECTIONS,API}.md |

Interfaces between tasks are frozen at the dataclasses in section 5, the tables in section 6, and the JSON shapes in section 11. Changing one needs an update to this file first.

---

## 16. Risks

- **R1 OBR licence UNVERIFIED.** The licence allowlist would block every OBR value, which includes the deflator and GDP, so no real or % of GDP figures could be published. parse-obr must fetch the OBR licence/copyright page (with a browser UA) and record a verbatim quote. If it is not OGL v3, stop and escalate. Do not weaken the gate.
- **Layout drift between PESA editions** (sheet names `10.1` vs `Table_1_1`, column shifts). Label anchoring and `LayoutError` handle this. The 2018 ODS edition is not needed, because later editions cover those years.
- **Mixed vintages in the COFOG series** (different editions for different years). Every point carries `vintage`, and the site notes the restatements.
- **DWP geography** (GB vs UK) and the welfare scope. Record them from the table titles, and never mix them within one series.
- **Tax year vs fiscal year.** Labelled through `period_basis`. Never summed with fiscal-year series.
- **A publisher replaces a file in place.** The sha mismatch fails the refresh, and the previous site stays live.
- **ONS rate limiting (429).** It only affects the disabled ons_psf source.

## 17. Out of scope (first slice)

Spend over £25k and Contracts Finder; Stat-Xplore; ONS LMS, PAYE RTI, ONS effects of taxes and benefits; OBR historical official forecasts (UNUSABLE) and the forecast revisions database; automatic discovery of new editions (new editions arrive as reviewed PRs to `sources.yml`); department-level PESA chapter 5 pages; free-text number extraction in the claim checker; regional (CRA/ITL) breakdowns.
