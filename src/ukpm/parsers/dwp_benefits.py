"""DWP benefit expenditure and caseload tables, Spring Forecast 2026 (xlsx).

Sheets used:
- `Table 1a` (expenditure by benefit, GBP million, nominal terms). Geography is Great Britain
  (Northern Ireland benefits are devolved), so series are `dwp_benefits.exp.<benefit>` with
  geography "GB". "of which" rows are named `<parent>.<child>`. Rows stop at the "Reconciliation
  with OBR ..." block, which restates AME totals on the OBR basis and is skipped.
- `UK welfare ` (note the trailing space in the sheet name): the nominal GBP billion block only,
  geography "UK" (DWP Social Security (GB) + Northern Ireland + other departments). Series are
  `dwp_benefits.uk_welfare.<line>`; the "Total" row is `dwp_benefits.total_uk_welfare`.
- `Table 1c` (caseloads by benefit, unit text "thousands*"), same year and status logic as 1a.
  Series are `dwp_benefits.caseload.<benefit>` with "of which" rows as `<parent>.<child>`, unit
  `thousand_cases`, geography "GB". Rows stop at the footnote starting "* Summing the rows of
  caseloads". Caseloads overlap (a person can claim several benefits), so there is NO total
  caseload and none may be computed. `BENEFIT_PAIRS` pairs 16 Table 1a spend series with a
  Table 1c caseload series for the per-benefit pages.
Sheets skipped: Contents, Notes, GB welfare (GB view of the same lines), Benefit summary table,
Table 1b (real terms, deflator-dependent), Tables 2a to 4 (breakdowns, not in the first slice),
Non-DWP Welfare, and the per-benefit sheets.

Status comes from the "Outturn" / "Forecast" row under each year heading. Only years from 2015-16
are emitted. Welfare Cap lines ("of which within/outside the Welfare Cap") are different scopes from
totals: do not add them to the total. Blank cells give no row. Skipped: Stat-Xplore API
(registry verdict PARTIAL, needs a key, licence unverified; source `dwp_stat_xplore` is disabled).
"""

from __future__ import annotations

import re
from pathlib import Path

from ..provenance import Provenance, Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError, normalise_fiscal_year

T1A = "Table 1a"
T1A_ANCHOR = "Table 1a: Expenditure by benefit,"
T1A_STOP = "reconciliation with obr"
T1C = "Table 1c"
T1C_ANCHOR = "Table 1c: Caseloads by benefit,"
T1C_STOP = "* summing the rows of caseloads"
UKW = "UK welfare "
UKW_START = "united kingdom welfare spending, \n£ billion, nominal terms"
UKW_STOP = "united kingdom welfare spending including"
FIRST_YEAR = "2015-16"
_FY = re.compile(r"^\d{4}/\d{2}$")

SERIES = {
    "dwp_benefits.exp.total_benefit_expenditure": {
        "title": "Total benefit expenditure (Great Britain)",
        "unit": "gbp_m",
        "period_type": "fiscal_year",
        "monetary": True,
        "description": "Table 1a, Total benefit expenditure, nominal. GB. One series per Table 1a "
        "row: dwp_benefits.exp.<benefit>.",
    },
    "dwp_benefits.total_uk_welfare": {
        "title": "UK welfare spending, total",
        "unit": "gbp_bn",
        "period_type": "fiscal_year",
        "monetary": True,
        "description": "UK welfare tab, nominal Total (DWP, Northern Ireland, other departments).",
    },
    "dwp_benefits.caseload.universal_credit": {
        "title": "Universal Credit caseload (Great Britain), thousands",
        "unit": "thousand_cases",
        "period_type": "fiscal_year",
        "monetary": False,
        "description": "Table 1c, caseloads by benefit, thousands, yearly average. GB. One series "
        "per Table 1c row: dwp_benefits.caseload.<benefit>. Table 1c footnote: 'Summing the rows "
        "of caseloads for individual benefits to create a total caseload is not possible due to "
        "the overlap of individuals who are in receipt of more than one benefit.' There is no "
        "total caseload.",
    },
}

# Verbatim sentences from the workbook's Notes sheet (Spring Forecast 2026).
_N_ROUND = (
    "Caseloads stated in these tables are rounded to the nearest 1,000, as such totals may not "
    "sum due to this rounding."
)
_N_AVG = (
    "Caseload figures represent an average over the full financial year; caseloads for benefits "
    "which commenced or ended during a financial year still reflect an average over the full "
    "year. Forecasts may use different sources to those on Stat-Xplore, and so may differ "
    "slightly."
)
_N_CA = (
    "Executive competence for Carer’s Allowance in Scotland was transferred to the Scottish "
    "Government on 3rd September 2018. From this point, Scottish caseload and expenditure are no "
    "longer included in our tables."
)
_N_DIS = (
    "Executive competence for Disability Living Allowance, Personal Independence Payment, "
    "Attendance Allowance, Severe Disablement Allowance and Industrial Injuries Disablement "
    "Benefit in Scotland was transferred to the Scottish Government on 1st April 2020. From this "
    "point, Scottish caseload and expenditure are no longer included in our tables."
)
_N_WFP = (
    "Winter Fuel Payments are devolved from April 2024. From this point, Scottish caseload and "
    "expenditure are no longer included in our tables."
)
_BASE = (_N_AVG, _N_ROUND)


def _pair(slug, name, spend, caseload, basis, extra=(), note=None):
    return {
        "slug": slug,
        "name": name,
        "spend": f"dwp_benefits.exp.{spend}",
        "caseload": f"dwp_benefits.caseload.{caseload}",
        "basis": basis,  # "in_payment" or "all_cases"
        "basis_note": note,
        "notes": extra + _BASE,
    }


# Verified against the Spring Forecast 2026 original. Denominator rule: "of which in payment" when
# Table 1c publishes it, otherwise the top-line row.
BENEFIT_PAIRS = [
    _pair(
        "attendance-allowance",
        "Attendance Allowance",
        "attendance_allowance",
        "attendance_allowance.in_payment",
        "in_payment",
        (_N_DIS,),
    ),
    _pair(
        "bereavement-benefits",
        "Bereavement benefits",
        "bereavement_related_benefits",
        "bereavement_related_benefits",
        "all_cases",
    ),
    _pair(
        "carers-allowance",
        "Carer's Allowance",
        "carer_s_allowance",
        "carer_s_allowance.in_payment",
        "in_payment",
        (_N_CA,),
    ),
    _pair(
        "disability-living-allowance",
        "Disability Living Allowance",
        "disability_living_allowance",
        "disability_living_allowance.in_payment",
        "in_payment",
        (_N_DIS,),
    ),
    _pair(
        "employment-and-support-allowance",
        "Employment and Support Allowance",
        "employment_and_support_allowance",
        "employment_and_support_allowance",
        "all_cases",
        note="Includes cases receiving credits only.",
    ),
    _pair(
        "housing-benefit",
        "Housing Benefit",
        "housing_benefits_exc_universal_credit",
        "housing_benefits_exc_universal_credit",
        "all_cases",
    ),
    _pair(
        "industrial-injuries",
        "Industrial Injuries benefits",
        "industrial_injuries_benefits_in_ame",
        "industrial_injuries_benefits",
        "all_cases",
        (_N_DIS,),
        note="Table 1a and Table 1c label this line differently.",
    ),
    _pair(
        "jobseekers-allowance",
        "Jobseeker's Allowance",
        "jobseeker_s_allowance",
        "jobseeker_s_allowance",
        "all_cases",
        note="Includes cases receiving credits only.",
    ),
    _pair(
        "maternity-allowance",
        "Maternity Allowance",
        "maternity_allowance",
        "maternity_allowance",
        "all_cases",
    ),
    _pair("pension-credit", "Pension Credit", "pension_credit", "pension_credit", "all_cases"),
    _pair(
        "personal-independence-payment",
        "Personal Independence Payment",
        "personal_independence_payment",
        "personal_independence_payment.in_payment",
        "in_payment",
        (_N_DIS,),
    ),
    _pair(
        "severe-disablement-allowance",
        "Severe Disablement Allowance",
        "severe_disablement_allowance",
        "severe_disablement_allowance",
        "all_cases",
        (_N_DIS,),
    ),
    _pair(
        "state-pension",
        "State Pension",
        "state_pension",
        "state_pension_includes_contributory_and_non_contributory",
        "all_cases",
    ),
    _pair(
        "statutory-maternity-pay",
        "Statutory Maternity Pay",
        "statutory_maternity_pay",
        "statutory_maternity_pay",
        "all_cases",
    ),
    _pair(
        "universal-credit", "Universal Credit", "universal_credit", "universal_credit", "all_cases"
    ),
    _pair(
        "winter-fuel-payments",
        "Winter Fuel Payments",
        "winter_fuel_payments",
        "winter_fuel_payments",
        "all_cases",
        (_N_WFP,),
    ),
]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")


def _num(v: object) -> float | None:
    return float(v) if isinstance(v, int | float) and not isinstance(v, bool) else None


def _year_cols(
    row: list, status_row: list, meta: FileMeta, where: str
) -> list[tuple[int, str, str]]:
    cols = []
    for c, h in enumerate(row):
        if not (isinstance(h, str) and _FY.match(h.strip())):
            continue
        fy = normalise_fiscal_year(h.strip())
        st = status_row[c].strip().casefold() if c < len(status_row) and status_row[c] else ""
        if st not in ("outturn", "forecast"):
            raise LayoutError(meta.file.key, f"{where}: status under {h!r} is {st!r}")
        if fy >= FIRST_YEAR:
            cols.append((c, fy, st))
    if not cols:
        raise LayoutError(meta.file.key, f"{where}: year headings")
    return cols


def _prov(meta: FileMeta, sheet: str, cell: str, status: str) -> Provenance:
    return Provenance(
        publisher=meta.source.publisher,
        dataset=meta.source.dataset,
        edition=meta.file.edition,
        publication_date=meta.file.publication_date,
        source_url=meta.file.file_url,
        landing_url=meta.file.landing_url,
        file_sha256=meta.sha256,
        sheet=sheet,
        cell_or_range=cell,
        api_query=None,
        licence=meta.source.licence,
        transformations=(),
        status=status,
        vintage=meta.file.edition,
        retrieved_at=meta.fetched_at,
    )


def _label(grid: list[list], r: int, c: int) -> str:
    v = grid[r][c] if c < len(grid[r]) else None
    return v.strip() if isinstance(v, str) else ""


def _table_1a(book, meta: FileMeta) -> list[Row]:
    try:
        hr, lc = book.find(T1A, T1A_ANCHOR)
    except (KeyError, LookupError) as e:
        raise LayoutError(meta.file.key, f"{T1A}!{T1A_ANCHOR}") from e
    grid = book.rows(T1A)
    cols = _year_cols(grid[hr], grid[hr + 1], meta, T1A)
    out: list[Row] = []
    seen: set[str] = set()
    parent = ""
    for r in range(hr + 2, len(grid)):
        lab = _label(grid, r, lc)
        if not lab:
            continue
        if lab.casefold().startswith(T1A_STOP):
            break
        if lab.casefold().startswith("of which "):
            slug = f"{parent}.{_slug(lab[len('of which ') :])}"
        else:
            slug = parent = _slug(lab)
        if slug in seen:
            raise LayoutError(meta.file.key, f"{T1A}: duplicate series {slug} at row {r + 1}")
        seen.add(slug)
        for c, fy, st in cols:
            v = _num(grid[r][c]) if c < len(grid[r]) else None
            if v is not None:
                out.append(
                    Row(
                        f"dwp_benefits.exp.{slug}",
                        fy,
                        "fiscal_year",
                        v,
                        "gbp_m",
                        "GB",
                        _prov(meta, T1A, a1(r, c), st),
                    )
                )
    if not out:
        raise LayoutError(meta.file.key, f"{T1A}: no values")
    return out


def _table_1c(book, meta: FileMeta) -> list[Row]:
    try:
        hr, lc = book.find(T1C, T1C_ANCHOR)
    except (KeyError, LookupError) as e:
        raise LayoutError(meta.file.key, f"{T1C}!{T1C_ANCHOR}") from e
    grid = book.rows(T1C)
    cols = _year_cols(grid[hr], grid[hr + 1], meta, T1C)
    out: list[Row] = []
    seen: set[str] = set()
    parent = ""
    stopped = False
    for r in range(hr + 2, len(grid)):
        lab = _label(grid, r, lc)
        if not lab:
            continue
        if lab.casefold().startswith(T1C_STOP):
            stopped = True
            break
        if lab.casefold().startswith("of which "):
            slug = f"{parent}.{_slug(lab[len('of which ') :])}"
        else:
            slug = parent = _slug(lab)
        if slug in seen:
            raise LayoutError(meta.file.key, f"{T1C}: duplicate series {slug} at row {r + 1}")
        seen.add(slug)
        for c, fy, st in cols:
            v = _num(grid[r][c]) if c < len(grid[r]) else None
            if v is not None:
                prov = _prov(meta, T1C, a1(r, c), st)
                out.append(
                    Row(
                        f"dwp_benefits.caseload.{slug}",
                        fy,
                        "fiscal_year",
                        v,
                        "thousand_cases",
                        "GB",
                        prov,
                    )
                )
    if not stopped:
        raise LayoutError(meta.file.key, f"{T1C}!{T1C_STOP}")
    if not out:
        raise LayoutError(meta.file.key, f"{T1C}: no values")
    return out


def _uk_welfare(book, meta: FileMeta) -> list[Row]:
    try:
        hr, lc = book.find(UKW, "Summary table: UK welfare,")
    except (KeyError, LookupError) as e:
        raise LayoutError(meta.file.key, f"{UKW}!Summary table: UK welfare,") from e
    grid = book.rows(UKW)
    cols = _year_cols(grid[hr], grid[hr + 1], meta, UKW)
    start = next(
        (
            r
            for r in range(hr + 2, len(grid))
            if _label(grid, r, lc).casefold() == UKW_START.strip()
        ),
        None,
    )
    if start is None:
        raise LayoutError(
            meta.file.key, f"{UKW}!United Kingdom welfare spending, GBP billion, nominal"
        )
    out: list[Row] = []
    seen: set[str] = set()
    parent = ""
    for r in range(start + 1, len(grid)):
        lab = _label(grid, r, lc)
        if not lab:
            continue
        if lab.casefold().startswith(UKW_STOP):
            break
        if lab.casefold().startswith("total ("):  # OBR-consistent total: a different definition
            slug = "total_obr_definition"
        elif lab.casefold().startswith("of which "):
            slug = f"{parent}.{_slug(lab[len('of which ') :])}"
        else:
            slug = parent = _slug(lab)
        if slug in seen:
            raise LayoutError(meta.file.key, f"{UKW}: duplicate series {slug} at row {r + 1}")
        seen.add(slug)
        sid = (
            "dwp_benefits.total_uk_welfare"
            if slug == "total"
            else f"dwp_benefits.uk_welfare.{slug}"
        )
        for c, fy, st in cols:
            v = _num(grid[r][c]) if c < len(grid[r]) else None
            if v is not None:
                out.append(
                    Row(sid, fy, "fiscal_year", v, "gbp_bn", "UK", _prov(meta, UKW, a1(r, c), st))
                )
    if not any(x.series_id == "dwp_benefits.total_uk_welfare" for x in out):
        raise LayoutError(meta.file.key, f"{UKW}!Total")
    return out


def parse(path: Path, meta: FileMeta) -> list[Row]:
    book = open_book(path)
    return _table_1a(book, meta) + _table_1c(book, meta) + _uk_welfare(book, meta)
