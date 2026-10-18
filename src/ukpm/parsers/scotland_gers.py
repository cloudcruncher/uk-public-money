"""Scottish Government GERS 2025-26 tables (xlsx): Scotland revenue, spending and net fiscal
balance, GBP million, financial years 1998-99 to 2025-26.

Sheets read (all other sheets are ignored):

* ``Table_1.1``  Total Revenue, rows ``Scotland (£ million)`` (revenue **including** a
  geographical share of North Sea revenue) and ``Scotland - excluding North Sea (£ million)``.
* ``Table_3.1``  Total Public Sector Expenditure, row ``Scotland  (£ millions)``. Whole pounds
  million as published. Spending has one basis only (there is no North Sea split).
* ``Table_5.1``  Net Fiscal Balance, rows ``Scotland (£ million)`` (with the North Sea share) and
  ``Scotland - Excluding North Sea (£ million)``. Negative = deficit.
* ``Table_3.3``  Total Expenditure: Scotland 2025-26 by function, GBP million, one year only
  (the year is read from the sheet title). Lines are kept as published (COFOG level 1, with the
  published sub-lines for general public services and economic affairs).

Checks (``LayoutError`` on failure): each sheet title; the year header (first column of years is
``1998-99``, consecutive fiscal years, the same on all three time-series sheets); the row labels;
unit text in the label; every value numeric; for every year, revenue minus expenditure equals the
published net fiscal balance (within ``BALANCE_TOLERANCE`` GBP m, because Table 3.1 is rounded to
whole millions), on both North Sea bases; Table 3.3 lines sum to its ``Total Expenditure``, which
agrees with Table 3.1 for the same year within the same tolerance.

Percent and share rows are NOT parsed (several are stored as fractions under a ``%`` label).
Earlier years are restated each August; the edition is GERS 2025-26 (published 2026-08-12).
"""

from __future__ import annotations

import re
from pathlib import Path

from ..provenance import Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError, normalise_fiscal_year
from ._w2 import num, prov, text

BALANCE_TOLERANCE = 0.6  # GBP m: Table 3.1 is whole millions (+/-0.5) plus 2dp rounding

REV, EXP, BAL, FUNC = "Table_1.1", "Table_3.1", "Table_5.1", "Table_3.3"
_TITLES = {
    REV: "Table 1.1: Total Revenue: 1998-99 to 2025-26",
    EXP: "Table 3.1: Total Public Sector Expenditure: 1998-99 to 2025-26",
    BAL: "Table 5.1: Net Fiscal Balance: Scotland and UK 1998-99 to 2025-26",
}
_FUNC_TITLE = re.compile(r"^Table 3\.3: Total Expenditure: Scotland (\d{4}-\d{2})$")

# slug -> (sheet, exact label, title, what it is)
_TS = {
    "revenue": (
        REV, "Scotland (£ million)", "Total revenue, including a geographical share of North Sea",
        "all UK taxes and other revenue raised in Scotland, with a geographical share of North "
        "Sea oil and gas revenue added (GERS headline basis)",
    ),
    "revenue_excl_north_sea": (
        REV, "Scotland - excluding North Sea (£ million)", "Total revenue, excluding North Sea",
        "the same revenue with no North Sea oil and gas revenue counted",
    ),
    "expenditure": (
        EXP, "Scotland (£ millions)", "Total public sector expenditure",
        "spending on Scotland by the Scottish Government, local government and UK Government "
        "bodies, plus accounting adjustments (one basis: there is no North Sea split for "
        "spending); published as whole millions",
    ),
    "net_balance": (
        BAL, "Scotland (£ million)", "Net fiscal balance, including North Sea share",
        "revenue minus expenditure, with a geographical share of North Sea revenue; negative "
        "means a deficit",
    ),
    "net_balance_excl_north_sea": (
        BAL, "Scotland - Excluding North Sea (£ million)",
        "Net fiscal balance, excluding North Sea",
        "revenue minus expenditure with no North Sea revenue counted; negative means a deficit",
    ),
}  # fmt: skip

# exact published label -> (slug, title)
_FUNCS = {
    "General public services - Public and common services": (
        "gps_public_common", "General public services: public and common services"),
    "General public services - International services": (
        "gps_international", "General public services: international services"),
    "General public services - Reserved public sector debt interest": (
        "gps_debt_interest", "General public services: reserved public sector debt interest"),
    "General public services - Local government pension fund interest expenditure": (
        "gps_lg_pension_interest",
        "General public services: local government pension fund interest"),
    "Defence": ("defence", "Defence"),
    "Public order and safety": ("public_order_and_safety", "Public order and safety"),
    "Economic affairs - Enterprise and economic development": (
        "ea_enterprise", "Economic affairs: enterprise and economic development"),
    "Economic affairs - Science and technology": (
        "ea_science", "Economic affairs: science and technology"),
    "Economic affairs - Employment policies": (
        "ea_employment", "Economic affairs: employment policies"),
    "Economic affairs - Agriculture, forestry and fisheries": (
        "ea_agriculture", "Economic affairs: agriculture, forestry and fisheries"),
    "Economic affairs - Transport": ("ea_transport", "Economic affairs: transport"),
    "Environment protection": ("environment_protection", "Environment protection"),
    "Housing and community amenities": (
        "housing_and_community_amenities", "Housing and community amenities"),
    "Health": ("health", "Health"),
    "Recreation, culture and religion": (
        "recreation_culture_religion", "Recreation, culture and religion"),
    "Education and training": ("education", "Education and training"),
    "Social protection": ("social_protection", "Social protection"),
    "EU transactions": ("eu_transactions", "EU transactions"),
    "Accounting adjustments": ("accounting_adjustments", "Accounting adjustments"),
}  # fmt: skip
_TOTAL_LABEL = "Total Expenditure"

_CAVEAT = (
    "Scottish Government GERS 2025-26 tables (Official Statistics, published 12 August 2026), "
    "financial years (April to March), GBP million, nominal. Earlier years are restated in each "
    "August edition."
)
SERIES = {
    f"scotland_gers.{slug}": {
        "title": f"Scotland: {title} (GERS)",
        "unit": "gbp_m",
        "period_type": "fiscal_year",
        "monetary": True,
        "description": f"{title[0].upper()}{title[1:]}: {what}. {_CAVEAT}",
    }
    for slug, (_sh, _lab, title, what) in _TS.items()
} | {
    f"scotland_gers.fn_{slug}": {
        "title": f"Scotland: spending on {title.lower()} (GERS 2025-26)",
        "unit": "gbp_m",
        "period_type": "fiscal_year",
        "monetary": True,
        "description": f"Scottish public sector spending on {title.lower()}, 2025-26 only (GERS "
        f"Table 3.3, one row per published function line). {_CAVEAT}",
    }
    for slug, title in _FUNCS.values()
}
SERIES["scotland_gers.fn_total_expenditure"] = {
    "title": "Scotland: total expenditure by function table (GERS 2025-26)",
    "unit": "gbp_m",
    "period_type": "fiscal_year",
    "monetary": True,
    "description": "Total of the function lines in GERS Table 3.3, 2025-26 only, to two decimal "
    f"places (Table 3.1 gives the same total rounded to whole millions). {_CAVEAT}",
}


def _norm(s: object) -> str:
    return " ".join(str(s).split()).casefold() if isinstance(s, str) else ""


def _sheet(book, key: str, name: str):
    try:
        return book.rows(name)
    except KeyError as e:
        raise LayoutError(key, f"sheet {name}") from e


def _series_sheet(grid, key: str, name: str):
    """Check the title and the year header; return {column: fiscal year}."""
    if text(grid[0][0] if grid and grid[0] else "") != _TITLES[name]:
        raise LayoutError(key, f"{name}!A1 title {_TITLES[name]!r}")
    if len(grid) < 3:
        raise LayoutError(key, f"{name}: header row")
    cols: dict[int, str] = {}
    for c, v in enumerate(grid[1]):
        if c == 0:
            if text(v) != "":
                raise LayoutError(key, f"{name}!A2 blank corner")
            continue
        if text(v) == "":
            continue
        try:
            cols[c] = normalise_fiscal_year(text(v))
        except ValueError as e:
            raise LayoutError(key, f"{name}!{a1(1, c)} fiscal year header") from e
    years = list(cols.values())
    if not years or years[0] != "1998-99" or years[-1] != "2025-26" or len(years) != 28:
        raise LayoutError(key, f"{name}: header runs 1998-99 to 2025-26 (28 years)")
    for a, b in zip(years, years[1:], strict=False):
        if int(a[:4]) + 1 != int(b[:4]):
            raise LayoutError(key, f"{name}: consecutive years ({a} then {b})")
    return cols


def _find_row(grid, key: str, name: str, label: str) -> int:
    hits = [r for r, row in enumerate(grid) if row and _norm(row[0]) == _norm(label)]
    if len(hits) != 1:
        raise LayoutError(key, f"{name}!{label!r} ({len(hits)} matches)")
    return hits[0]


def parse(path: Path, meta: FileMeta) -> list[Row]:
    key = meta.file.key
    book = open_book(path)
    out: list[Row] = []
    vals: dict[tuple[str, str], float] = {}
    colmap: dict[str, dict[int, str]] = {}
    grids = {}
    for name in (REV, EXP, BAL):
        grids[name] = _sheet(book, key, name)
        colmap[name] = _series_sheet(grids[name], key, name)
    if not (colmap[REV] == colmap[EXP] == colmap[BAL]):
        raise LayoutError(key, "year columns differ between Table 1.1, 3.1 and 5.1")

    for slug, (name, label, _t, _w) in _TS.items():
        grid, cols = grids[name], colmap[name]
        r = _find_row(grid, key, name, label)
        for c, fy in cols.items():
            v = num(grid[r][c]) if c < len(grid[r]) else None
            if v is None:
                raise LayoutError(key, f"{name}!{a1(r, c)} numeric value")
            vals[(slug, fy)] = v
            out.append(
                Row(f"scotland_gers.{slug}", fy, "fiscal_year", v, "gbp_m", "Scotland",
                    prov(meta, name, a1(r, c), "outturn", "GERS 2025-26"))
            )  # fmt: skip

    for fy in colmap[REV].values():
        exp = vals[("expenditure", fy)]
        for rev, bal in (("revenue", "net_balance"),
                         ("revenue_excl_north_sea", "net_balance_excl_north_sea")):  # fmt: skip
            if abs(vals[(rev, fy)] - exp - vals[(bal, fy)]) > BALANCE_TOLERANCE:
                raise LayoutError(key, f"revenue - expenditure != {bal} for {fy}")

    # ---- Table 3.3: spending by function, one year ----
    grid = _sheet(book, key, FUNC)
    m = _FUNC_TITLE.match(text(grid[0][0]) if grid and grid[0] else "")
    if not m:
        raise LayoutError(key, f"{FUNC}!A1 title 'Table 3.3: Total Expenditure: Scotland <year>'")
    fy = normalise_fiscal_year(m.group(1))
    if fy != "2025-26":
        raise LayoutError(key, f"{FUNC}: year is {fy}, expected 2025-26")
    if len(grid) < 3 or text(grid[1][1]) != "£ million":
        raise LayoutError(key, f"{FUNC}!B2 unit '£ million'")
    parts = 0.0
    for lab, (slug, _t) in _FUNCS.items():
        r = _find_row(grid, key, FUNC, lab)
        v = num(grid[r][1])
        if v is None:
            raise LayoutError(key, f"{FUNC}!{a1(r, 1)} numeric value")
        parts += v
        out.append(
            Row(f"scotland_gers.fn_{slug}", fy, "fiscal_year", v, "gbp_m", "Scotland",
                prov(meta, FUNC, a1(r, 1), "outturn", "GERS 2025-26"))
        )  # fmt: skip
    # no unexpected extra data rows between the header and the total
    r = _find_row(grid, key, FUNC, _TOTAL_LABEL)
    body = [_norm(row[0]) for row in grid[2:r] if row and _norm(row[0])]
    if sorted(body) != sorted(_norm(k) for k in _FUNCS):
        raise LayoutError(key, f"{FUNC}: function lines changed")
    total = num(grid[r][1])
    if total is None:
        raise LayoutError(key, f"{FUNC}!{a1(r, 1)} numeric value")
    if abs(parts - total) > BALANCE_TOLERANCE or abs(total - vals[("expenditure", fy)]) > 0.6:
        raise LayoutError(key, f"{FUNC}: lines do not add to Total Expenditure / Table 3.1")
    out.append(
        Row("scotland_gers.fn_total_expenditure", fy, "fiscal_year", total, "gbp_m", "Scotland",
            prov(meta, FUNC, a1(r, 1), "outturn", "GERS 2025-26"))
    )  # fmt: skip
    return out
