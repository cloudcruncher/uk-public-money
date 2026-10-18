"""MHCLG local authority revenue outturn, England, first release 2025-26: sheet ``Table_1a``.

"Service expenditure net of sales, fees and charges and of other income, 2021-22 to 2025-26
(cash terms)", GBP million (the sheet says so in its preamble and the parser asserts it), by
service category, England only, financial years. Header: the row whose first cell is
``Service Category``; year columns are ``YYYY-YY`` and must be consecutive. Rows are matched by
label (the ``[note N]`` marks are ignored); each must occur exactly once, else LayoutError. The
ten top-level categories must add up to ``Total Service Expenditure`` (tolerance 0.5 GBP m).
The Children's Social Care row (``of which`` Social care) is parsed and must sit directly under
Social care. The Greater London Authority ``of which`` row, the year-on-year rows, the
"excluding" totals and ``Revenue Expenditure`` are not parsed.

Series ``mhclg_la_outturn.<slug>`` (gbp_m, fiscal_year, England). Caveats in every description:
net of income (including NHS money such as the Better Care Fund, so adult social care is not
shown on its own); education is not comparable between years because schools becoming academies
leave council budgets; the first release is provisional and revised in later releases.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..provenance import Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError, normalise_fiscal_year
from ._w2 import num, prov, text

SHEET = "Table_1a"
TOLERANCE = 0.5  # GBP m; the published categories are rounded to thousands of pounds
_TITLE = (
    "Table 1a: Service expenditure net of sales, fees and charges and of other income "
    "[note 1], 2021-22 to 2025-26 (cash terms)"
)
_UNIT = "Figures are reported in £ millions."
_NOTE = re.compile(r"\s*\[note \d+\]\s*")
_CHILD = "of which: Children's Social Care"
_CAVEATS = (
    "England only (the devolved nations publish separately). Cash terms, not adjusted for "
    "inflation. Net of sales, fees and charges and of other income, including NHS money such as "
    "the Better Care Fund. Financial year (April to March). The first release is provisional "
    "and is revised in later releases."
)

# label as published (notes removed) -> (slug, short name, extra caveat)
_LINES = {
    "Education": (
        "education",
        "education",
        " Not comparable between years: schools becoming academies are funded centrally.",
    ),
    "Highways and transport": (
        "highways_transport",
        "highways and transport",
        " Includes the Greater London Authority (Transport for London grants were high in "
        "2021-22).",
    ),
    "Social care": (
        "social_care",
        "social care (adult and children's)",
        " Adult social care is not shown separately because spending paid for by the NHS is "
        "left out.",
    ),
    _CHILD: ("childrens_social_care", "children's social care (part of social care)", ""),
    "Public Health": ("public_health", "public health", ""),
    "Housing (excluding Housing Revenue Account)": (
        "housing",
        "housing (excluding the Housing Revenue Account)",
        "",
    ),
    "Cultural, environmental and planning": (
        "cultural_environmental_planning",
        "cultural, environmental and planning services",
        "",
    ),
    "Police": ("police", "police", ""),
    "Fire & rescue": ("fire_rescue", "fire and rescue", ""),
    "Central services": ("central_services", "central services", ""),
    "Other Services": ("other", "other services", ""),
    "Total Service Expenditure": ("total", "all services", ""),
}
_PARTS = [
    "education", "highways_transport", "social_care", "public_health", "housing",
    "cultural_environmental_planning", "police", "fire_rescue", "central_services", "other",
]  # fmt: skip

SERIES = {
    f"mhclg_la_outturn.{slug}": {
        "title": f"Council spending in England on {name} (net, financial year)",
        "unit": "gbp_m",
        "period_type": "fiscal_year",
        "monetary": True,
        "description": f"MHCLG local authority revenue outturn, first release 2025-26, Table 1a, "
        f"{name}, GBP million. {_CAVEATS}{extra}",
    }
    for slug, name, extra in _LINES.values()
}


def _label(v: object) -> str:
    return _NOTE.sub(" ", text(v)).strip()


def parse(path: Path, meta: FileMeta) -> list[Row]:
    key = meta.file.key
    book = open_book(path)
    try:
        grid = book.rows(SHEET)
    except KeyError as e:
        raise LayoutError(key, f"sheet {SHEET}") from e
    if not grid or not grid[0] or text(grid[0][0]) != _TITLE:
        raise LayoutError(key, f"{SHEET}!A1 title {_TITLE!r}")
    pre = [text(r[0]) if r else "" for r in grid[1:6]]
    if _UNIT not in pre:
        raise LayoutError(key, f"{SHEET}: unit line {_UNIT!r}")
    hr = next((r for r, row in enumerate(grid) if row and text(row[0]) == "Service Category"), -1)
    if hr < 0:
        raise LayoutError(key, f"{SHEET}: header row starting 'Service Category'")
    cols: list[tuple[int, str]] = []
    for c, v in enumerate(grid[hr][1:], start=1):
        if text(v):
            try:
                cols.append((c, normalise_fiscal_year(text(v))))
            except ValueError as e:
                raise LayoutError(key, f"{SHEET}!{a1(hr, c)} financial year") from e
    if len(cols) < 3:
        raise LayoutError(key, f"{SHEET}: financial-year columns")
    starts = [int(y[:4]) for _c, y in cols]
    if starts != list(range(starts[0], starts[0] + len(starts))):
        raise LayoutError(key, f"{SHEET}: financial years not consecutive")
    where: dict[str, int] = {}
    for r in range(hr + 1, len(grid)):
        lab = _label(grid[r][0]) if grid[r] else ""
        if lab in _LINES:
            if lab in where:
                raise LayoutError(key, f"{SHEET}!{lab} (found twice)")
            where[lab] = r
    for lab in _LINES:
        if lab not in where:
            raise LayoutError(key, f"{SHEET}!{lab}")
    if where[_CHILD] != where["Social care"] + 1:
        raise LayoutError(key, f"{SHEET}: Children's Social Care row not under Social care")

    out: list[Row] = []
    vals: dict[tuple[str, str], float] = {}
    for lab, (slug, _name, _extra) in _LINES.items():
        r = where[lab]
        for c, year in cols:
            v = num(grid[r][c]) if c < len(grid[r]) else None
            if v is None:
                raise LayoutError(key, f"{SHEET}!{a1(r, c)} number for {lab}")
            vals[(slug, year)] = v
            out.append(
                Row(f"mhclg_la_outturn.{slug}", year, "fiscal_year", v, "gbp_m", "England",
                    prov(meta, SHEET, a1(r, c), "outturn", meta.file.edition))
            )  # fmt: skip
    for _c, year in cols:
        if abs(sum(vals[(s, year)] for s in _PARTS) - vals[("total", year)]) > TOLERANCE:
            raise LayoutError(key, f"{SHEET}: categories do not add up to the total for {year}")
        if vals[("childrens_social_care", year)] > vals[("social_care", year)]:
            raise LayoutError(key, f"{SHEET}: children's social care exceeds social care {year}")
    return out
