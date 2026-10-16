# Layman framing and new sources: design

Inputs: `docs/sources/new-sources.md` (scout log, 2026-10-15), `docs/ARCHITECTURE.md` sections 4 to 10 and 14,
`docs/design/positioning.md`, the current `src/ukpm/{build,units,provenance,check_api,reconcile}.py`,
`src/ukpm/parsers/{__init__,dwp_benefits,ons_psf}.py`, and the cached DWP Spring Forecast 2026 workbook
(`work/raw/dwp_benefits/11a591e4...xlsx`), which the architect read to settle the Table 1a/1c pairing (section 4).

The core rule does not change: **no number reaches `site/api/v1` without a complete provenance record**. Every new
value, including every derived value (per person, per £100, cost per claimant, share of welfare, Cabinet Office
sums), goes through `provenance.problems()` before it is written. A value that fails is dropped, logged to
`work/rejected.jsonl` and counted in `index.json.build.rejected`. Its slot becomes a published gap. It is never
filled in.

---

## 1. Decisions in one screen

| Topic | Decision |
|---|---|
| New enabled sources | `ons_population` (USABLE), `obr_efo` (PARTIAL: expenditure tables only), `cabinet_office_spend` (USABLE). |
| `ons_psf` | Stays a stub. Verdict changes from UNVERIFIED to **UNUSABLE**, `enabled: false`. R4 stays `not_run` with the new reason. |
| Per person | New variants `per_person` (cash) and `per_person_real` on an allowlist of series. Divisor: the ONS mid-year population for the same geography, with mid-YYYY mapped to fiscal year YYYY-(YY+1). Recorded as a `per_person` transformation whose `inputs` holds the population provenance id. |
| Per household | **Gap.** No ONS household count was verified. `index.json.per_household = {available: false, reason}`. The site shows no household figure. |
| Out of every £100 | New variant `per_100` on parts of two fixed sets: England spending by function (PESA 10.1) and HMRC receipts by tax. Same edition and year only. A computed "everything else" remainder makes each set add up to 100. Also written as `shares.json`. |
| Per benefit | DWP Table 1c caseloads are parsed (new series `dwp_benefits.caseload.*`). 16 benefits are paired with their Table 1a spend. Build derives cost per claimant and share of welfare and writes `benefits/index.json` plus `benefits/<slug>.json`. |
| Cabinet Office | Aggregates only: monthly total, transaction count, by expense type (top 10 plus "other"), and top suppliers over 12 months (at most 20, each at least £1m, redaction markers excluded). No row-level data, refs, transaction numbers, days or expense areas. Hard size caps, which `check-api` enforces. |
| Reconciliation | New R8 (OBR EFO Universal Credit vs DWP), R9 (OBR EFO NI social security vs DWP UK welfare tab), R10 (Cabinet Office sanity bounds). `RULE_IDS` becomes R1 to R10. |
| Glossary | `data/glossary.yml` becomes `glossary.json`. The build validates it and fails if any entry contains a figure. |

---

## 2. Source register: `data/sources.yml` (owner: integrate)

Add these entries. URLs and sha256 values are copied from `docs/sources/new-sources.md`. Enter only URLs that the
scout recorded as HTTP 200.

```yaml
- id: ons_population
  publisher: Office for National Statistics
  dataset: Population estimates for the UK, England, Wales, Scotland and Northern Ireland
  landing_url: https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/populationestimatesforukenglandandwalesscotlandandnorthernireland
  licence: OGL-UK-3.0        # ONLY after integrate verifies it (see below); else UNVERIFIED + enabled: false
  licence_evidence: "<verbatim OGL line from the landing page, with the date checked>"
  cadence: annual (mid-year estimates; prior years revised)
  coverage: {from: 2015-16, to: 2025-26, note: "mid-YYYY estimate mapped to fiscal year YYYY-(YY+1)"}
  verdict: USABLE
  enabled: true
  fixture_dir: tests/fixtures/ons
  user_agent: "Mozilla/5.0 (compatible; ukpm/0.1)"
  files:
    - key: ons_mye_2025
      edition: ONS mid-2025 population estimates
      publication_date: 2026-10-01          # cover sheet: "originally published at 9.30am 1 October 2026"
      file_url: https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/populationestimatesforukenglandandwalesscotlandandnorthernireland/mid2025/mye25tablesuk.xlsx
      landing_url: <dataset landing above>
      format: xlsx
      sha256: 8ae244e3341257ecccaee55f4973fe12f46afe6656ead6c1a9ed3f4f8585e40f
      role: mye_summary

- id: obr_efo
  publisher: Office for Budget Responsibility
  dataset: Economic and fiscal outlook, detailed forecast tables (expenditure)
  landing_url: https://obr.uk/efo/economic-and-fiscal-outlook-march-2026/
  licence: OGL-UK-3.0
  licence_evidence: <copy the obr entry's licence_evidence (same obr.uk/copyright page)>
  cadence: twice yearly with each forecast
  coverage: {note: "forecast publication; year range read from the sheet header"}
  verdict: PARTIAL
  verdict_reason: "Only sheet 4.9 welfare cap rows are parsed. Receipts and policy tables were not inspected."
  enabled: true
  fixture_dir: tests/fixtures/obr_efo
  user_agent: "Mozilla/5.0 (compatible; ukpm/0.1)"   # obr.uk returns 403 to bare curl
  files:
    - key: obr_efo_mar2026_expenditure
      edition: OBR EFO March 2026
      publication_date: 2026-03-03   # DWP Notes: "Spring Forecast on the 3rd of March 2026"; integrate confirms on the EFO landing page
      file_url: https://obr.uk/docs/d055fbf02d5b3g6jq8l2/efo-march-2026-detailed-forecast-tables-expenditure.xlsx
      landing_url: https://obr.uk/efo/economic-and-fiscal-outlook-march-2026/
      format: xlsx
      sha256: 700bfd700c872794e5fe8cf164086cd38a63850db26427b9d4b2e363d177d9a1
      role: efo_expenditure

- id: cabinet_office_spend
  publisher: Cabinet Office
  dataset: Cabinet Office spend over £25,000
  landing_url: https://www.gov.uk/government/publications/cabinet-office-spend-data
  licence: OGL-UK-3.0
  licence_evidence: "gov.uk footer: 'All content is available under the Open Government Licence v3.0, except where otherwise stated' (checked 2026-10-15)"
  cadence: monthly
  coverage: {from: 2025-09, to: 2026-08, note: "Cabinet Office core; amounts as published, VAT basis unverified"}
  verdict: USABLE
  enabled: true
  fixture_dir: tests/fixtures/cabinet_office
  user_agent: null
  files:                        # 12 entries, one per row of the scout table (rows 1 to 12)
    - key: co_2025_09           # co_<YYYY>_<MM>
      edition: "2025-09"        # the month; the parser uses it as the aggregation month
      publication_date: <see below>
      file_url: https://assets.publishing.service.gov.uk/media/69009a5a84b816d72cb9aa48/Expenditure_Over_25000_-_September_2025__Cabinet_Office_Core___1___2_.csv
      landing_url: https://www.gov.uk/government/publications/cabinet-office-spend-data
      format: csv
      sha256: 587b8fcba37848d8cb4081d8cfb0af1872cca67bdd0d8d68604a2a0940b5555b
      role: monthly_spend
    # ... co_2025_10 to co_2026_08, same pattern
```

- **ONS licence**: the scout recorded it as UNVERIFIED. Integrate must fetch the landing page (www.ons.gov.uk is
  already on the host allowlist), find the OGL line and paste it verbatim into `licence_evidence`. If no OGL line is
  found, set `licence: UNVERIFIED` and `enabled: false`. All per-person output then becomes gaps. It is not an error.
- **Cabinet Office `publication_date`**: take each attachment's date from
  `https://www.gov.uk/api/content/government/publications/cabinet-office-spend-data`. If the content API gives no
  per-file date, use `2026-09-24` (the page's last-updated date) and say so in a `notes:` line. Never invent one.
- `ons_psf`: set `verdict: UNUSABLE` and set `notes` to the new-sources.md reason ("no link followed from an official
  page to a PSF dataset file; bulletin URL 502"). The file entry is unchanged and stays disabled.
- **Not entered** (each is a documented gap, see section 11): OBR EFO receipts and policy xlsx (not inspected), OBR
  Welfare Trends workbook, OBR FRS report PDF, OBR FRS annexes (gated), ONS long-run population file (not inspected),
  ONS households.

---

## 3. Parsers (contract: ARCHITECTURE section 6 and `parsers/__init__.py`)

Every parser exposes `SERIES` and `parse(path, meta) -> list[Row]`. It locates cells by label and raises
`LayoutError` on any missing anchor. It records the real A1 address, never rounds, and gives no row for a blank,
`..`, `-` or `x` cell. Fixtures follow the existing `MANIFEST.yml` format (`source_id, original_sha256,
original_url, fixture, fixture_sha256`, plus a trim comment). A trimmed fixture keeps every kept cell at its
original sheet and A1 address.

### 3.1 `ukpm.parsers.ons_population` (owner: parsers-ons)

- Sheet `MYE4` ("Summary for the UK, mid-2011 to mid-2025"). Header row 8 holds `Mid-YYYY` labels (D = Mid-2025,
  then descending). Find every `Mid-YYYY` column by text, keeping YYYY ≥ 2015. The scout did not read Mid-2015 and
  Mid-2016 cell by cell. If a column is missing, its year simply has no row and becomes a gap.
- Row 9 = United Kingdom (assert the label text you find). Also emit Great Britain and England **only if** MYE4
  has rows with those labels. Assert the exact text and document the result in the module docstring.
- Cross-check: `MYE1` row 9 "All Persons", column B (United Kingdom) must equal the MYE4 UK Mid-2025 cell
  (69483939). Raise `LayoutError` if they differ. This adds no extra series.
- Rows: `series_id` = `ons_population.uk`, `ons_population.gb` or `ons_population.england`. `fiscal_year` is the
  fiscal year that contains 30 June of YYYY (Mid-2024 → `2024-25`). `period_basis: "mid_year"`, `unit: "persons"`,
  `status: "outturn"`, vintage `ONS mid-2025 population estimates`. Geography is `UK`, `GB` or `England`.
- `SERIES` metadata: `monetary: False`. The description must state the mid-year-to-fiscal-year mapping.
- Fixture `tests/fixtures/ons/mye25tablesuk.trimmed.xlsx` (the original is 1,026,940 bytes, over the 1 MB rule).
  Keep MYE4 rows 1 to 20 with all columns, and MYE1 rows 7 to 9.
- Tests in `tests/test_parsers_ons.py`. Assert UK 2025-26 = 69483939 (D9), 2024-25 = 69256274 (E9) and
  2023-24 = 68588048 (F9). Also assert the cell addresses, that provenance is complete
  (`problems() == []`), and that the MYE1 mismatch raises.

### 3.2 `ukpm.parsers.ons_psf` (owner: parsers-ons)

Unchanged stub. Update only the docstring: verdict UNUSABLE, the reason from new-sources.md, and the next step. It
must keep raising `NotImplementedError`.

### 3.3 `ukpm.parsers.dwp_benefits`: add Table 1c (owner: parsers-ons, plan amendment, see section 10)

- Parse `Table 1c` ("Table 1c: Caseloads by benefit,", unit text `thousands*`) with the same year and status logic
  as 1a (`_year_cols`). Stop at the footnote row that starts with "* Summing the rows of caseloads". Quote that
  footnote in `SERIES` (individual caseloads overlap, so there is **no total caseload**, and none may be computed).
- `series_id` = `dwp_benefits.caseload.<slug>`. "of which" rows become `<parent>.<child>` exactly as in 1a (so
  "of which in payment" becomes `.in_payment`). `unit: "thousand_cases"`, geography `GB`. Blank cells give no row.
- Add the constant `BENEFIT_PAIRS`. The build imports it, so all label knowledge stays in the parser. The pairs
  below were verified against the cached original (Spring Forecast 2026; row numbers are sheet rows):

| slug | name | spend series (1a row) | caseload series (1c row) | basis |
|---|---|---|---|---|
| attendance-allowance | Attendance Allowance | exp.attendance_allowance (7) | caseload.attendance_allowance.in_payment (8) | in payment |
| bereavement-benefits | Bereavement benefits | exp.bereavement_related_benefits (8) | caseload.bereavement_related_benefits (10) | all cases |
| carers-allowance | Carer's Allowance | exp.carer_s_allowance (9) | caseload.carer_s_allowance.in_payment (12) | in payment |
| disability-living-allowance | Disability Living Allowance | exp.disability_living_allowance (18) | caseload.disability_living_allowance.in_payment (21) | in payment |
| employment-and-support-allowance | Employment and Support Allowance | exp.employment_and_support_allowance (22) | caseload.employment_and_support_allowance (24) | all cases (includes credits only) |
| housing-benefit | Housing Benefit | exp.housing_benefits_exc_universal_credit (29) | caseload.housing_benefits_exc_universal_credit (30) | all cases |
| industrial-injuries | Industrial Injuries benefits | exp.industrial_injuries_benefits_in_ame (37) | caseload.industrial_injuries_benefits (37) | all cases (labels differ: note it) |
| jobseekers-allowance | Jobseeker's Allowance | exp.jobseeker_s_allowance (41) | caseload.jobseeker_s_allowance (41) | all cases (includes credits only) |
| maternity-allowance | Maternity Allowance | exp.maternity_allowance (44) | caseload.maternity_allowance (46) | all cases |
| pension-credit | Pension Credit | exp.pension_credit (54) | caseload.pension_credit (50) | all cases |
| personal-independence-payment | Personal Independence Payment | exp.personal_independence_payment (55) | caseload.personal_independence_payment.in_payment (52) | in payment |
| severe-disablement-allowance | Severe Disablement Allowance | exp.severe_disablement_allowance (59) | caseload.severe_disablement_allowance (54) | all cases |
| state-pension | State Pension | exp.state_pension (63) | caseload.state_pension_includes_contributory_and_non_contributory (55) | all cases |
| statutory-maternity-pay | Statutory Maternity Pay | exp.statutory_maternity_pay (67) | caseload.statutory_maternity_pay (56) | all cases |
| universal-credit | Universal Credit | exp.universal_credit (72) | caseload.universal_credit (58) | all cases |
| winter-fuel-payments | Winter Fuel Payments | exp.winter_fuel_payments (77) | caseload.winter_fuel_payments (62) | all cases |

  (All ids carry the `dwp_benefits.` prefix.) The rule for the denominator is: use "of which in payment" when 1c
  publishes it, otherwise the top-line row. Each pair entry also holds `notes`: verbatim sentences from the
  workbook's `Notes` sheet that apply to it. These are the Scotland devolution sentences for Carer's Allowance (from
  3 Sep 2018), for DLA/PIP/AA/SDA/Industrial Injuries (from 1 Apr 2020) and for Winter Fuel (from Apr 2024), plus
  "Caseload figures represent an average over the full financial year" and "rounded to the nearest 1,000". Notes are
  quoted, never paraphrased into new facts.
- **Not paired** (published in `benefits/index.json.gaps`): Child Benefit (Table 1a shows 0 and Table 1c is blank
  in this edition). Also Income Support and Incapacity Benefit, whose caseload in payment is 0 in recent years, so a
  cost per claimant is undefined. Small lines with no matching 1c row are not paired.
- Re-trim `tests/fixtures/dwp/spring_forecast_2026.trimmed.xlsx` to **add `Table 1c`** (paired rows, the in-payment
  child rows, the header/status rows and the footnote), using the same four year columns at their original
  addresses. Update `SOURCE.txt` (fixture sha). Existing 1a tests must still pass unchanged. New tests go in
  `tests/test_parsers_dwp_caseload.py`: Carer's Allowance in payment 2025-26 = 1018.0 (thousand), PIP in payment
  2025-26 = 3836.0, every `BENEFIT_PAIRS` series exists in the parsed rows, and provenance is complete.

### 3.4 `ukpm.parsers.obr_efo` (owner: parsers-obr-co)

- File: the EFO March 2026 expenditure workbook. **Read the year header row first.** In sheet `4.9`, find the
  header row above the data. It is the first row with three or more cells that `normalise_fiscal_year` accepts
  (also try `2024-25` and `2024/25` text). Raise `LayoutError` if it is not found. Map columns by that text only.
  Read the unit from the title rows (expect "£ billion"; if it is absent, raise `LayoutError`).
- Status: if the sheet has an explicit Outturn/Forecast marker (a row, or a header suffix), use it. If it has none,
  set **every value to `forecast`** (it is a forecast publication) and add a line to the series description: "as
  published in the March 2026 forecast; earlier years may be outturn estimates". Vintage: `OBR EFO March 2026`.
- Series (locate by label; the scout's rows are only expectations):

| series_id | sheet / label (scout row) | geography |
|---|---|---|
| `obr_efo.welfare_cap.universal_credit` | 4.9 "Universal credit" (18) | GB |
| `obr_efo.welfare_cap.other_dwp` | 4.9 "Other DWP in welfare cap" (19) | GB |
| `obr_efo.welfare_cap.ni_social_security` | 4.9 "NI social security in welfare cap" (34) | Northern Ireland |

  Sheet 4.2 (TME % GDP) and sheet 4.11 are not parsed in this slice. List them in the docstring as skipped.
- Fixture: the original file is 236,965 bytes (≤ 1 MB), so commit it **unmodified** as
  `tests/fixtures/obr_efo/efo-march-2026-detailed-forecast-tables-expenditure.xlsx`, with `MANIFEST.yml`
  (`fixture_sha256 == original_sha256`). Tests in `tests/test_parsers_obr_efo.py` assert the header row, the cell
  addresses and values for at least two years per series, the status rule, and complete provenance.

### 3.5 `ukpm.parsers.cabinet_office_spend` (owner: parsers-obr-co)

- Decoding: try `utf-8-sig`, then `cp1252`. Use the `csv` module (CRLF). Find the header row by text: `Ref,
  Departmental Family, Entity, Date, Expense Type, Expense Area, Supplier, Transaction number, Amount`. Find columns
  by header name. Missing headers raise `LayoutError`.
- Fully blank rows are skipped and not counted. For a non-blank row, the Amount (comma-thousands, may be negative)
  must parse, or the parser raises `LayoutError` with the row number. **Nothing is dropped silently.**
- Month = `files[].edition` (`YYYY-MM`). The fiscal year is the April-to-March year that contains it
  (2025-09 → `2025-26`). `period_basis: "month"`, `status: "outturn"`, vintage
  `Cabinet Office spend over £25,000, <Month YYYY>`, geography `UK`, unit `gbp` (pounds as published).
- Provenance for a CSV: `sheet: "CSV"`. `cell_or_range` is the Amount column's contiguous data range, plus a filter
  for subtotals. The filter is part of the provenance, so ids stay unique:
  - total: `I2:I500`
  - by expense type: `I2:I500 where E="Professional Services"`
  - by supplier: `I2:I500 where G="Acme Ltd"`

  Use the real column letters and last row. Double any `"` inside the text. Export `label_of(row) -> str | None`,
  which returns the quoted filter text; the build uses it for display names.
- Rows per file (`MM` = `YYYY_MM`):
  - `cabinet_office_spend.total.<MM>`
  - `cabinet_office_spend.transactions.<MM>`: count of rows summed (unit `count`, range `A2:A500`)
  - `cabinet_office_spend.expense_type.<MM>.<slug>`: one per distinct Expense Type
  - `cabinet_office_spend.supplier.<MM>.<slug>`: one per distinct Supplier. These go to `work/parsed` only; the
    build decides what is published (section 6.4).

  Slug collisions get `_2`, `_3` and so on, in order of first appearance. Never publish `Ref`, `Transaction number`,
  `Date` (day), `Expense Area` or row-level amounts.
- Internal assertion: the sum of the expense-type rows equals the total to within £0.01. Otherwise raise
  `LayoutError` (this is a parser bug guard).
- Fixtures `tests/fixtures/cabinet_office/`: all 12 months, **trimmed for privacy**. Every row stays at its original
  line number. Blank the `Ref` and `Transaction number` cells, and replace every Supplier whose 12-month total is
  below £1,000,000 with `WITHHELD (fixture)`. Amount, Date and Expense Type stay unchanged, so totals still match
  the publisher. Keep each file's original encoding and blank trailing rows (co_12 has 130). `MANIFEST.yml` records
  the original url/sha and describes the trim. Tests in `tests/test_parsers_cabinet_office.py` assert, for at least
  three months, the scout's row counts and totals to the penny (Sep 2025: 499 rows, 112227426.43; Mar 2026: 869,
  261904761.53; Aug 2026: 476, 110279506.39). They also cover the cp1252 decode, blank-row skipping, the
  `LayoutError` on a bad Amount, and complete provenance.

---

## 4. Derived values (owner: integrate; `units.py` + `build.py`)

### 4.1 New `units.py` functions

Each returns a new `Row` with one appended `Transformation`, as the existing ones do, and sets status to `forecast`
if any input is a forecast. `MissingDenominator` is raised when an input is missing or zero.

```python
def per_person(row: Row, pop_rows: list[Row]) -> Row
    # value_gbp_bn * 1e9 / persons, same fiscal_year; unit "gbp_per_person"
    # Transformation("per_person", "x 1e9 / <geo> population, ONS mid-<YYYY> estimate (<vintage>)", (pid(pop),))
def share(part: Row, total: Row, op: str = "per_100") -> Row
    # 100 * part / total; requires same fiscal_year, unit and prov.edition (else ValueError "mixed editions")
    # unit "gbp_per_100" for op per_100, "pct" for op share_of_total; inputs (pid(total),)
def per_claimant(spend: Row, caseload: Row) -> Row
    # spend_gbp_bn * 1e9 / (thousand_cases * 1000); same fiscal_year and edition; unit "gbp_per_claimant"
def remainder(total: Row, parts: list[Row], label: str) -> Row
    # total - sum(parts); location copied from total; inputs = pids of all parts; op "remainder"
def sum_rows(primary: Row, others: list[Row], op: str, detail: str) -> Row
    # primary + sum(others); inputs = pids of others; used for Cabinet Office 12-month sums
```

`per_person` requires unit `gbp_bn`, so it can also be applied to an already deflated row to give
`per_person_real`, with the chain recorded.

### 4.2 Per person

- Population map: `{"UK": "ons_population.uk", "GB": "ons_population.gb", "England": "ons_population.england"}`.
  No other geography gets per-person figures (for example Northern Ireland). Tax-year series are excluded.
- Allowlist `PER_PERSON` in build.py: the `HEADLINE` series, `pesa.cofog.*` (England), the HMRC `per_100` parts,
  and every spend series in `BENEFIT_PAIRS` (GB). Other series do not get the variant, which keeps provenance files
  small.
- Variants `per_person` (unit label `GBP_per_person`) and `per_person_real` (`GBP_per_person_<base>`, from the real
  row). A year with no population becomes a gap `{fiscal_year, variant, reason: "no ONS mid-year estimate for this
  year; projections are not used"}`. This covers every forecast year after 2025-26.

### 4.3 Out of every £100

`PER_100_SETS` in build.py:

```python
PER_100_SETS = {
  "spending_england": {"title": "Spending on services in England", "total": "pesa.cofog.total_services",
                       "parts": [the ten pesa.cofog.<function> ids]},
  "revenue_hmrc": {"title": "Tax collected by HMRC", "total": "hmrc_receipts.total",
                   "parts": ["hmrc_receipts.income_tax", "hmrc_receipts.nics", "hmrc_receipts.vat",
                             "hmrc_receipts.corporation_tax", "hmrc_receipts.hydrocarbon_oil_fuel_duties",
                             "hmrc_receipts.stamp_duty_land_tax"]},
}
```

- Integrate must confirm that each HMRC part is a top-level column. Its header must not contain "included within";
  `corporation_tax` already includes offshore. If a part is not top-level, the build fails.
- Shares use the **same edition** as the total. Each point is a `per_100` variant on the part series. Per set and
  year, `other = remainder(total, parts)` is shared as well and labelled "everything else (and rounding)", so the
  parts add up to exactly 100.
- The scope is said plainly: PESA 10.1 covers **England only** (identifiable spending on services, not total
  government spending). UK-wide spending by function needs PESA chapter 5, which has not been fetched. That is a
  gap (section 11).

### 4.4 Per benefit

For each `BENEFIT_PAIRS` entry and each year in both series (same edition):

- `cost_per_claimant = per_claimant(spend, caseload)`.
- `share_of_welfare = share(spend, dwp_benefits.exp.total_benefit_expenditure, op="share_of_total")`. The
  denominator is the GB Table 1a total, so the scope matches. It is never the UK welfare tab.
- Headline year: the latest year where all four values exist with status `outturn`. If there is none, the latest
  year with all four values, flagged as a forecast.

### 4.5 One write path

Every value written anywhere (series, shares, benefits, Cabinet Office) goes through one helper:
`_emit(row, primary, unit_label) -> point | None`. It runs `problems(row.prov)`. On failure it appends to `rejected`
and returns None, and the caller records a gap. On success it calls `records.add(row, primary)` and returns the
point dict (`POINT_KEYS`). **No writer builds a point from a bare number.**

---

## 5. Reconciliation (owner: integrate; `reconcile.py`)

| id | rule | tolerance / status |
|---|---|---|
| R4 | (unchanged) PESA TME vs ONS PSF | `not_run`, reason: "ONS PSF has no verifiable file (docs/sources/new-sources.md)" |
| R8 | OBR EFO `welfare_cap.universal_credit` vs DWP `exp.universal_credit.within_welfare_cap`, per overlapping year | rel ≤ 1.0% pass, else fail. Run only for the vintage pair (`OBR EFO March 2026`, `DWP Spring Forecast 2026`), which are the same forecast round. Any other pair gives `info` with "different forecast rounds". `not_run` if either side is missing. |
| R9 | OBR EFO `welfare_cap.ni_social_security` vs DWP `uk_welfare.northern_ireland_social_security.within_the_welfare_cap` | as R8 |
| R10 | Cabinet Office sanity bounds. One result per month: £10m ≤ total ≤ £1bn. One result for the window: the latest 12 consecutive months total between £0.5bn and £5bn | pass/fail. The window is `not_run` if fewer than 12 consecutive months are present. Description: "wide plausibility bounds, not an official total; the 12 scout files sum to £1,896,163,621.03". |

`reconcile.run` gains a `co_rows` argument, because Cabinet Office rows are not in `nominal` (see 6.4). Results
reference only published provenance ids (the month totals and the derived window total). `check_api.RULE_IDS`
becomes R1 to R10.

---

## 6. API additions under `site/api/v1` (owner: integrate)

All files are UTF-8 with `sort_keys`. Values are as computed, with no rounding. A "point" is
`{fiscal_year, value, unit, status, vintage, provenance_id}`.

### 6.1 `index.json` (additions)

```json
{"population": {"series": {"UK": "ons_population.uk", "GB": "ons_population.gb", "England": "ons_population.england"},
                "vintage": "ONS mid-2025 population estimates",
                "mapping": "mid-year (30 June) estimate inside each April-March year"},
 "per_household": {"available": false, "reason": "No ONS household count file was verified (docs/sources/new-sources.md)."},
 "files": {"...existing...": "...", "glossary": "glossary.json", "shares": "shares.json",
           "benefits": "benefits/index.json", "cabinet_office": "cabinet_office/summary.json"}}
```

`population.series` lists only geographies that were built. `index.series[].variants` may now include
`per_person`, `per_person_real` and `per_100`. Population, caseload and EFO series appear as ordinary series
(`series/<id>.json`; non-monetary ones have `nominal` only).

### 6.2 `shares.json`

```json
{"generated_at": "...",
 "sets": [{"id": "spending_england", "title": "Spending on services in England", "scope": "England",
           "total_series_id": "pesa.cofog.total_services", "fiscal_year": "2024-25", "edition": "PESA 2026",
           "parts": [{"series_id": "pesa.cofog.health", "title": "...", "per_100": {point, "unit": "GBP_per_100"},
                      "per_person": {point} | null}],
           "other": {point} | null}]}
```

`fiscal_year` is the latest outturn year in which every part and the total exist in one edition. The parts plus
`other` add up to 100 (within 1e-9).

### 6.3 `benefits/index.json` and `benefits/<slug>.json`

```json
// benefits/index.json
{"generated_at": "...", "edition": "DWP Spring Forecast 2026", "geography": "GB",
 "total_series_id": "dwp_benefits.exp.total_benefit_expenditure",
 "benefits": [{"slug": "carers-allowance", "name": "Carer's Allowance", "path": "benefits/carers-allowance.json",
               "headline": {"fiscal_year": "2024-25", "status": "outturn", "spend": {point},
                            "claimants": {point}, "cost_per_claimant": {point}, "share_of_welfare": {point}}}],
 "gaps": [{"name": "Child Benefit", "reason": "Table 1a shows 0 and Table 1c is blank in this edition."}]}

// benefits/<slug>.json
{"slug": "...", "name": "...", "geography": "GB", "edition": "...",
 "spend_series_id": "...", "caseload_series_id": "...",
 "caseload_basis": "in_payment" | "all_cases", "headline_year": "2024-25",
 "spend": [points GBP_bn], "spend_real": [points GBP_bn_<base>], "spend_per_person": [points GBP_per_person],
 "claimants": [points thousand_cases], "cost_per_claimant": [points GBP_per_claimant],
 "share_of_welfare": [points percent],
 "gaps": [{"fiscal_year": "...", "field": "cost_per_claimant", "reason": "..."}],
 "notes": ["<verbatim DWP Notes sentences from BENEFIT_PAIRS>", "Claimant numbers are yearly averages, rounded to the nearest 1,000."]}
```

The slug matches `^[a-z0-9-]+$`. Years run from 2015-16 to the last year in the edition, with forecasts flagged per
point.

### 6.4 `cabinet_office/summary.json`

Cabinet Office rows are **excluded** from `nominal`, stitching, `build_series`, `observations*.parquet` and the
"register every vintage" loop. That loop would otherwise publish a record for every supplier. They are handled only
by `build_cabinet_office(co_rows, parser)`:

```json
{"source_id": "cabinet_office_spend", "entity": "Cabinet Office (core)", "threshold_gbp": 25000,
 "vat_basis": "unverified", "available": true,
 "window": {"from": "2025-09", "to": "2026-08", "months": 12, "complete": true, "total": {point, "unit": "GBP"}},
 "months": [{"month": "2025-09", "fiscal_year": "2025-26", "total": {point}, "transactions": {point, "unit": "count"},
             "expense_types": [{"name": "...", "point": {point}}], "other_expense_types": {point} | null}],
 "top_suppliers": [{"name": "...", "point": {point}, "months_present": 12}],
 "other_suppliers": {point},
 "caps": {"months": 24, "expense_types_per_month": 10, "suppliers": 20, "supplier_floor_gbp": 1000000,
          "max_bytes": 262144, "max_provenance_bytes": 1048576},
 "notes": ["Amounts as published; the files do not say whether VAT is included.",
           "Only suppliers paid at least £1 million over the 12 months are named; everyone else is grouped."]}
```

- `months` is the newest 24 months at most, newest first. `expense_types` holds the top 10 by value, and
  `other_expense_types = remainder(total, top10)`.
- `top_suppliers`: per supplier, the window total = `sum_rows` of that supplier's monthly rows (each monthly row's
  record is published as an input). A supplier is named only if **all** of these hold: it is in the top 20 by
  window total; its total is at least £1,000,000; its name is not blank; and its name does not match
  `(?i)redact|withheld|personal|individual|employee|private|name not|^n/?a$`. `other_suppliers =
  remainder(window total, named suppliers)`.
- If the source is disabled or not built: `{"source_id": ..., "available": false, "reason": "..."}`.

### 6.5 `glossary.json`

`{"generated_at": "...", "terms": [{"id", "term", "aliases", "plain", "long", "see_also", "source_id",
"checker_only"}]}`, sorted by `term.casefold()`.

### 6.6 Check block for CSV records

In `Records._check`, when `sheet == "CSV"`, the instructions read: "Download the CSV and open it. Add up column
<col> (Amount) for rows <a> to <b>[ where column <c> is "<text>"]. To confirm you have the same file: shasum -a 256
<file> should print <sha>." It keeps `kind: "spreadsheet"`, so `check.js` needs no new kind.

---

## 7. `data/glossary.yml` schema (content: glossary-copy; validation: integrate)

```yaml
- id: real-terms                 # optional; default slug(term); ^[a-z0-9-]+$; unique; anchor glossary.html#<id>
  term: Real terms               # required
  aliases: [adjusted for rising prices]   # optional; other phrases a tooltip may attach to
  plain: One sentence, reading age about 12, under 25 words.   # required
  long: Two to four sentences of explanation.                  # required
  see_also: [inflation, gdp-deflator]     # optional; ids that must exist
  source_id: obr                 # optional; must be an id in data/sources.yml
  checker_only: false            # optional; true = jargon that appears only in "For checkers" sections
```

The build fails, naming the entry, if: `term`, `plain` or `long` is missing; an id is duplicated; a `see_also`
entry does not resolve; a `source_id` is unknown; or `plain`/`long` contains a figure (regex `£\s?\d|\d\s?%|\d[\d,]*\s?(million|billion|bn|m)\b`).
Figures belong in the API with provenance, never in copy.

---

## 8. `check_api.py` contract changes (owner: integrate)

1. `REQUIRED_FILES` adds `glossary.json`, `shares.json`, `benefits/index.json` and `cabinet_office/summary.json`.
2. `RULE_IDS` = R1 to R10.
3. Allowed variant names: `nominal, real, pct_gdp, per_person, per_person_real, per_100`. Records for
   `per_person*` must list an input starting with `ons_population.`. Records for `per_100` must list the set's
   total series input.
4. **Generic value walker** over shares, benefits and Cabinet Office JSON: every dict that has a `value` key must
   have a `provenance_id` that resolves to a complete record (the same gate). Any other numeric leaf named `value`
   is a violation.
5. Benefits: every `index.benefits[].path` exists. `cost_per_claimant` records have an input with the prefix
   `dwp_benefits.` that resolves to a caseload record. Slugs are valid.
6. Shares: per set, the parts plus `other` add up to 100 within 1e-9.
7. Glossary: shape, unique ids, `see_also` resolves, and the figure regex finds nothing.
8. Cabinet Office (privacy and size):
   - `summary.json` ≤ 262144 bytes and `provenance/cabinet_office_spend.json` ≤ 1048576 bytes.
   - The list lengths respect `caps`, and every named supplier is ≥ the floor.
   - No key named `ref`, `transaction_number`, `date` or `expense_area` appears anywhere.
   - **No orphan supplier records**: every record whose `cell_or_range` filters on the Supplier column is referenced
     from `summary.json`, directly or as an input of a referenced record.

Tests: extend `tests/test_contract_api.py` (one negative case per new rule above) and `tests/test_reconcile.py` (R8
to R10, including `not_run`). Add `tests/test_build_layman.py`, which checks:

- per_person equals nominal × 1e9 / population for a known year (UK TME 2024-25), and its record's inputs list
  both the population id and the deflator ids for the real variant;
- every `BENEFIT_PAIRS` slug has a file;
- Carer's Allowance cost per claimant equals spend ÷ caseload from the fixture cells;
- the shares add up to 100;
- no supplier below the floor appears.

---

## 9. Edge cases

- **Mixed editions**: `share`/`per_claimant` raise on different editions. The build uses each pair's edition
  values (`_edition_year`), not the stitched mix.
- **Zero or missing denominators** (a 0.0 caseload, a missing population year) give a gap with a reason, never 0 or
  infinity.
- **Negative values** (Cost of Living Payments −42.9 in 2025-26, credit notes in Cabinet Office files) are allowed
  as published. Shares with negative parts are not in any set.
- **Population revisions**: mid-2022 to mid-2024 were revised in October 2026. Only the latest edition is used, and
  its vintage is shown.
- **Scotland devolution** breaks benefit trends (Carer's Allowance 2018, disability benefits 2020, Winter Fuel
  2024). This is stated in the notes; nothing is adjusted.
- **Caseload overlap**: there is no total-claimants figure anywhere (DWP footnote).
- **Cabinet Office re-published months**: a corrected file is a new `files[]` entry with a new sha, and the newest
  `publication_date` for that month wins. The old one stays in the register.
- **Offline builds**: every new source has fixtures, so `build --offline` is complete and R10's window runs.

---

## 10. Ownership (matches `.swarm/plan.json`, with one amendment)

| task | owns (exclusive) |
|---|---|
| parsers-ons | `src/ukpm/parsers/ons_population.py`, `src/ukpm/parsers/ons_psf.py` (docstring only), `tests/fixtures/ons/**`, `tests/test_parsers_ons.py`; **amendment:** `src/ukpm/parsers/dwp_benefits.py` (Table 1c, `BENEFIT_PAIRS`), `tests/fixtures/dwp/**`, `tests/test_parsers_dwp_caseload.py` |
| parsers-obr-co | `src/ukpm/parsers/obr_efo.py`, `src/ukpm/parsers/cabinet_office_spend.py`, `tests/fixtures/obr_efo/**`, `tests/fixtures/cabinet_office/**`, `tests/test_parsers_obr_efo.py`, `tests/test_parsers_cabinet_office.py` |
| glossary-copy | `data/glossary.yml`, `data/definitions.yml` (`short` fields only), `site/glossary.html`, `site/assets/pages/glossary.js` |
| integrate | `data/sources.yml`, `data/fetched.json`, `src/ukpm/{build,units,reconcile,check_api,registry}.py`, `src/ukpm/parsers/__init__.py`, `tests/{test_contract_api,test_reconcile,test_core,test_build_layman}.py`, `site/api/v1/**` |
| site-core | site shell and pages listed in the plan. It reads `shares.json`, the `per_person*` variants, `glossary.json` and `index.json.per_household` (shows no household figure while it is unavailable) |
| site-benefits | `site/benefits.html`, `site/benefit.html`, `site/assets/pages/{benefits,benefit}.js`. Reads `benefits/index.json` and `benefits/<slug>.json` only |

**Amendment for the lead:** add the three DWP paths to the `parsers-ons` `files` list in `.swarm/plan.json`. No other
task owns `dwp_benefits.py`, and Table 1c is needed for the per-benefit pages. Parser tasks must not touch
`data/sources.yml` or `build.py`. For offline tests they build `FileMeta` from a local `Source`/`FileEntry`, as the
existing parser tests do.

Order: parsers-ons ∥ parsers-obr-co ∥ glossary-copy → integrate → site-core → site-benefits.

---

## 11. Documented gaps and out of scope (scribe copies these into docs/SOURCES.md)

| Gap | Why | Next step |
|---|---|---|
| ONS Public Sector Finances | UNUSABLE: no link from an official page to a PSF file; bulletin 502; earlier guesses 404/429 | Find a PSF xlsx linked from an ONS/HMT page; fetch and hash it |
| Per-household figures | No ONS household or family count file was verified | Scout a household estimates file; add `ons_households` |
| OBR EFO receipts and policy tables | Downloaded, not inspected | Inspect sheets; add series to `obr_efo` |
| OBR EFO sheets 4.2 (TME % GDP) and 4.11 (UC elements) | Located, not needed in this slice | Optional R-rule vs the databank |
| OBR Welfare Trends June 2026 workbook | A fraud-and-error workbook with no spend or caseload table | Possible future "fraud and error" page |
| OBR Fiscal Risks and Sustainability 2026 | The report is a PDF; the annexes are gated (`obr.uk/no-access`) | None |
| ONS long-run population 1838 to 2025 | Not inspected | Only needed for pre-2015 years |
| UK-wide spending by function | PESA 10.1 is England only; chapter 5 not fetched | Scout PESA chapter 5 (Table 5.2) |
| Child Benefit page | Not in DWP Table 1a/1c in this edition | HMRC Child Benefit statistics |
| Cabinet Office VAT basis; other departments | Not stated in the files; only Cabinet Office core was scouted | Ask the publisher; scout other departments' £25k files |

Out of scope: forecasts of population, interpolation of any missing year, a total claimant count, any per-transaction
Cabinet Office view, Stat-Xplore and new hosts on the allowlist.

## 12. Risks

- **ONS licence not yet quoted**: this blocks all per-person output. Integrate resolves it first (section 2).
- **EFO status split may be absent**: values are then labelled forecast throughout. That is conservative and stated
  in the description.
- **Supplier privacy relies on the floor, top-N and denylist**, not on a list of individuals. The reviewer should
  read the published supplier names once per refresh. `check-api` blocks orphan supplier records.
- **Provenance file growth** from per-person variants: the `PER_PERSON` allowlist limits it. Watch
  `provenance/*.json` sizes in review.
