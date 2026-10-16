"""ONS Public Sector Finances, Appendix A tables 1 to 10 (xlsx): central government aggregates.

Sheets used (names exact): PSA6L, PSA6B_2, PSA6C_3, PSA1. Layout read from the real August 2026
file (sha256 4cc5dded...): row 5 holds the column headings (with unit), row 6 the dataset
identifier codes (CDIDs, sometimes with a leading space or a sign prefix such as ' -NMFJ'), and
column A the period label. Columns are found by CDID in row 6, then checked against a keyword in
the row 5 heading and the unit in that heading; a mismatch raises LayoutError. Only financial-year
rows (label 'Apr 2025 to Mar 2026') from 2015-16 are emitted; calendar-year, quarterly and
monthly rows are skipped. All values are outturn (provisional for the latest year and restated
every month; the vintage is the release edition, e.g. 'ONS Public sector finances, August 2026').

TWO EXPENDITURE DEFINITIONS, NEVER MIXED (docs/sources/new-sources-2-ons.md):
- ons_psf.cg_tme: central government total managed expenditure (PSA6L, CDID ECOD; PSF note 21 =
  current expenditure + depreciation + net investment). FY2025-26 = 1,250,068.
- ons_psf.cg_total_expenditure_gross: central government total expenditure, revenue and
  expenditure account basis (PSA6C_3, CDID MF6U; note 26 = current + capital).
  FY2025-26 = 1,301,598.
They differ by 51,530 in FY2025-26 and both give the same net borrowing. The PSA6B_2 memo item
'Total expenditure' (DU3N) is the same quantity as ECOD, so it is not emitted twice: it is
asserted equal to ECOD and net borrowing (PSA6B_2 vs PSA6C_3) is asserted equal, else LayoutError.

Other series: cg_receipts (PSA6C_3 MF6R), cg_net_borrowing (PSA6C_3 -NMFJ), cg_debt_interest
(PSA6B_2 NMFX, includes investment income attributable to insurance policy holders, note 17),
ps_net_borrowing_ex_banks (PSA1 -J5II), ps_net_debt_gbp_bn and ps_net_debt_pct_gdp (PSA1 HF6W /
HF6X, excluding public sector banks; end-of-period stock; the % uses ONS's 12-month centred GDP,
not calendar-year YBHA GDP).
"""

from __future__ import annotations

import re
from pathlib import Path

from ..provenance import Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError
from ._w2 import num, prov, text

SOURCE = "ons_psf"
FIRST_YEAR = 2015
_FY = re.compile(r"^Apr (\d{4}) to Mar (\d{4})$")

# series suffix -> (sheet, CDID, heading keyword, unit key, unit, title, description)
_M, _BN, _PCT = "(£ million)", "(£ billion)", "%"
_LINES = {
    "cg_tme": (
        "PSA6L",
        "ECOD",
        "central government",
        _M,
        "gbp_m",
        "Central government total managed expenditure (PSF)",
        "PSF PSA6L Total Managed Expenditure by sub-sector, central government (CDID ECOD). "
        "Note 21 definition: current expenditure + depreciation + net investment. Not the same "
        "as cg_total_expenditure_gross.",
    ),
    "cg_total_expenditure_gross": (
        "PSA6C_3",
        "MF6U",
        "total expenditure",
        _M,
        "gbp_m",
        "Central government total expenditure, current + capital (PSF account basis)",
        "PSF PSA6C_3 Total expenditure (CDID MF6U), note 26: current plus capital expenditure. "
        "A different definition from cg_tme (51,530m higher in 2025-26); never combine the two.",
    ),
    "cg_receipts": (
        "PSA6C_3",
        "MF6R",
        "total revenue",
        _M,
        "gbp_m",
        "Central government total revenue (PSF)",
        "PSF PSA6C_3 Total revenue (CDID MF6R).",
    ),
    "cg_net_borrowing": (
        "PSA6C_3",
        "NMFJ",
        "net borrowing",
        _M,
        "gbp_m",
        "Central government net borrowing (PSF)",
        "PSF PSA6C_3 Net borrowing (CDID -NMFJ). Positive is borrowing.",
    ),
    "cg_debt_interest": (
        "PSA6B_2",
        "NMFX",
        "interest",
        _M,
        "gbp_m",
        "Central government debt interest (PSF)",
        "PSF PSA6B_2 current expenditure, of which interest (CDID NMFX), note 17: includes "
        "investment income attributable to insurance policy holders.",
    ),
    "ps_net_borrowing_ex_banks": (
        "PSA1",
        "J5II",
        "net borrowing excluding public sector banks",
        _M,
        "gbp_m",
        "Public sector net borrowing excluding public sector banks (PSF)",
        "PSF PSA1 public sector net borrowing excluding public sector banks (CDID -J5II).",
    ),
    "ps_net_debt_gbp_bn": (
        "PSA1",
        "HF6W",
        "net debt excluding public sector banks",
        _BN,
        "gbp_bn",
        "Public sector net debt excluding public sector banks, GBP bn (PSF)",
        "PSF PSA1 (CDID HF6W). End-of-period stock at 31 March of the financial year.",
    ),
    "ps_net_debt_pct_gdp": (
        "PSA1",
        "HF6X",
        "as a % gdp",
        "percentage points",
        "pct_gdp",
        "Public sector net debt excluding public sector banks, % of GDP (PSF)",
        "PSF PSA1 (CDID HF6X). Denominator is ONS's 12-month centred GDP (PSA1 note 2), so it "
        "will not equal a ratio built on calendar-year YBHA GDP.",
    ),
}

SERIES = {
    f"ons_psf.{k}": {
        "title": v[5],
        "unit": v[4],
        "period_type": "fiscal_year",
        "monetary": v[4] != "pct_gdp",
        "description": v[6],
    }
    for k, v in _LINES.items()
}


def _cdid(v: object) -> str:
    return text(v).lstrip("-").strip().upper()


def _vintage(book, meta: FileMeta) -> str:
    """'ONS Public sector finances, <release month year>' from the cover sheet text."""
    try:
        grid = book.rows("Cover Sheet")
    except KeyError as e:
        raise LayoutError(meta.file.key, "Cover Sheet") from e
    for row in grid[:12]:
        for v in row:
            m = re.match(
                r"This spreadsheet was published at [\d.]+[ap]m (\d{1,2}) (\w+) (\d{4})", text(v)
            )
            if m:
                d, mo, y = m.groups()
                return f"ONS Public sector finances, published {d} {mo} {y}"
    raise LayoutError(meta.file.key, "Cover Sheet: 'published at ... <date>'")


def _sheet_cols(book, sheet: str, key: str) -> tuple[list[list], dict[str, int]]:
    try:
        grid = book.rows(sheet)
    except KeyError as e:
        raise LayoutError(key, sheet) from e
    if len(grid) < 8 or text(grid[5][0]) != "Dataset identifier code":
        raise LayoutError(key, f"{sheet}!A6 'Dataset identifier code'")
    cols: dict[str, int] = {}
    for c, v in enumerate(grid[5]):
        cd = _cdid(v)
        if not cd:
            continue
        if cd in cols:
            raise LayoutError(key, f"{sheet}: CDID {cd} appears in more than one column")
        cols[cd] = c
    return grid, cols


def parse(path: Path, meta: FileMeta) -> list[Row]:
    key = meta.file.key
    book = open_book(path)
    vintage = _vintage(book, meta)
    sheets: dict[str, tuple[list[list], dict[str, int]]] = {}
    out: list[Row] = []
    located: dict[str, dict[str, tuple[int, int]]] = {}  # suffix -> {fy: (row, col)}
    for suffix, (sheet, cdid, kw, unit_kw, unit, _t, _d) in _LINES.items():
        if sheet not in sheets:
            sheets[sheet] = _sheet_cols(book, sheet, key)
        grid, cols = sheets[sheet]
        if cdid not in cols:
            raise LayoutError(key, f"{sheet}!row 6 CDID {cdid}")
        c = cols[cdid]
        head = text(grid[4][c]).casefold()
        if kw.casefold() not in head or unit_kw.casefold() not in head:
            raise LayoutError(key, f"{sheet}!{a1(4, c)} heading {head!r} lacks {kw!r}/{unit_kw!r}")
        for r in range(6, len(grid)):
            m = _FY.match(text(grid[r][0]))
            if not m:
                continue
            y0, y1 = int(m.group(1)), int(m.group(2))
            if y1 != y0 + 1:
                raise LayoutError(key, f"{sheet}!{a1(r, 0)} not a financial year: {grid[r][0]!r}")
            if y0 < FIRST_YEAR:
                continue
            v = num(grid[r][c])
            if v is None:
                continue
            fy = f"{y0}-{y1 % 100:02d}"
            located.setdefault(suffix, {})[fy] = (r, c)
            out.append(
                Row(
                    f"ons_psf.{suffix}",
                    fy,
                    "fiscal_year",
                    v,
                    unit,
                    "UK",
                    prov(meta, sheet, a1(r, c), "outturn", vintage),
                )
            )
        if suffix not in located:
            raise LayoutError(key, f"{sheet}!{cdid}: no financial-year values from {FIRST_YEAR}")

    _cross_checks(book, sheets, out, meta, vintage)
    return out


def _cross_checks(book, sheets, out: list[Row], meta: FileMeta, vintage: str) -> None:
    """ECOD must equal the PSA6B_2 memo total expenditure (DU3N) and the two net borrowing
    columns (PSA6C_3 -NMFJ, PSA6B_2 -NMFJ) must agree, per financial year."""
    key = meta.file.key
    by = {(x.series_id, x.fiscal_year): x.value for x in out}
    grid, cols = sheets.get("PSA6B_2") or _sheet_cols(book, "PSA6B_2", key)
    pairs = {"DU3N": "ons_psf.cg_tme", "NMFJ": "ons_psf.cg_net_borrowing"}
    for cdid, sid in pairs.items():
        if cdid not in cols:
            raise LayoutError(key, f"PSA6B_2!row 6 CDID {cdid}")
        for r in range(6, len(grid)):
            m = _FY.match(text(grid[r][0]))
            if not m or int(m.group(1)) < FIRST_YEAR:
                continue
            fy = f"{m.group(1)}-{int(m.group(2)) % 100:02d}"
            v, want = num(grid[r][cols[cdid]]), by.get((sid, fy))
            if v is not None and want is not None and v != want:
                raise LayoutError(
                    key, f"PSA6B_2!{a1(r, cols[cdid])} ({v}) disagrees with {sid} {fy} ({want})"
                )
