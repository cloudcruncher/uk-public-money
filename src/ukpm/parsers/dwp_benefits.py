"""DWP benefit expenditure and caseload tables, Spring Forecast 2026 (xlsx).

Sheets used:
- `Table 1a` (expenditure by benefit, GBP million, nominal terms). Geography is Great Britain
  (Northern Ireland benefits are devolved), so series are `dwp_benefits.exp.<benefit>` with
  geography "GB". "of which" rows are named `<parent>.<child>`. Rows stop at the "Reconciliation
  with OBR ..." block, which restates AME totals on the OBR basis and is skipped.
- `UK welfare ` (note the trailing space in the sheet name): the nominal GBP billion block only,
  geography "UK" (DWP Social Security (GB) + Northern Ireland + other departments). Series are
  `dwp_benefits.uk_welfare.<line>`; the "Total" row is `dwp_benefits.total_uk_welfare`.
Sheets skipped: Contents, Notes, GB welfare (GB view of the same lines), Benefit summary table,
Table 1b (real terms, deflator-dependent), Table 1c and 2a to 4 (caseloads and breakdowns, not in
the first slice), Non-DWP Welfare, and the per-benefit sheets.

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
}


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
    return _table_1a(book, meta) + _uk_welfare(book, meta)
