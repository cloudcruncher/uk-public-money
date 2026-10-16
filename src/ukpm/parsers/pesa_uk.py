"""HM Treasury PESA 2026, Chapter 5 table 5.2 (xlsx): UK-wide public sector expenditure on
services by function, GBP million, 2021-22 to 2025-26.

Sheet ``5_2``. Header: the first row with three or more fiscal-year cells (row 5, columns C:G);
the next row holds ``outturn``/``forecast`` per year (all outturn in this edition). Labels sit in
column B and are matched by text (the trailing footnote markers ``(2), (3)`` and ``(11)`` are
stripped; leading numbers on sub-function labels are kept). Each label must occur exactly once.
Unit must read ``£ million``. Dash cells (``-``) give no row.

Series (``pesa_uk.<slug>``): the ten function totals, ``public_debt_transactions`` (row '1.7'),
``eu_transactions``, ``services`` (Public sector expenditure on services),
``accounting_adjustments`` and ``tme`` (Total Managed Expenditure). The ten function totals plus
EU transactions sum to ``services`` to within rounding (1m in 2021-22 and 2023-24);
``services`` plus ``accounting_adjustments`` equals ``tme`` exactly. Both are asserted, else
LayoutError. Economic affairs fell in 2023-24 as energy support ended. Edition is PESA 2026
(July 2026); earlier years are restated edition to edition.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..provenance import Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError, normalise_fiscal_year
from ._w2 import num, prov, text

SHEET = "5_2"
ROUNDING = 1.5  # tolerance (GBP m) when summing rounded published function totals; also rule R12
_FOOT = re.compile(r"\s*(\(\d+\)[,\s]*)+$")

# label -> (slug, title)
_LINES = {
    "1.7 Public debt transactions": ("public_debt_transactions", "Public debt transactions"),
    "Total general public services": ("general_public_services", "General public services"),
    "Total defence": ("defence", "Defence"),
    "Total public order and safety": ("public_order_and_safety", "Public order and safety"),
    "Total economic affairs": ("economic_affairs", "Economic affairs"),
    "Total environment protection": ("environment_protection", "Environment protection"),
    "Total housing and community amenities": (
        "housing_and_community_amenities",
        "Housing and community amenities",
    ),
    "Total health": ("health", "Health"),
    "Total recreation, culture and religion": (
        "recreation_culture_religion",
        "Recreation, culture and religion",
    ),
    "Total education": ("education", "Education"),
    "Total social protection": ("social_protection", "Social protection"),
    "Total EU transactions": ("eu_transactions", "EU transactions"),
    "Public sector expenditure on services": ("services", "Public sector expenditure on services"),
    "Accounting adjustments": ("accounting_adjustments", "Accounting adjustments"),
    "Total Managed Expenditure": ("tme", "Total Managed Expenditure"),
}
_FUNCTIONS = [
    "general_public_services", "defence", "public_order_and_safety", "economic_affairs",
    "environment_protection", "housing_and_community_amenities", "health",
    "recreation_culture_religion", "education", "social_protection", "eu_transactions",
]  # fmt: skip

SERIES = {
    f"pesa_uk.{slug}": {
        "title": f"{title}, UK public spending (PESA 2026 table 5.2)",
        "unit": "gbp_m",
        "period_type": "fiscal_year",
        "monetary": True,
        "description": "HMT PESA 2026 chapter 5 table 5.2, UK-wide public sector expenditure on "
        "services by function, GBP million, nominal. COFOG level 1 plus HMT sub-functions.",
    }
    for slug, title in _LINES.values()
}


def parse(path: Path, meta: FileMeta) -> list[Row]:
    key = meta.file.key
    book = open_book(path)
    try:
        grid = book.rows(SHEET)
    except KeyError as e:
        raise LayoutError(key, f"sheet {SHEET}") from e
    hr, cols = -1, []
    for r, row in enumerate(grid):
        found = []
        for c, v in enumerate(row):
            try:
                found.append((c, normalise_fiscal_year(text(v))))
            except ValueError:
                pass
        if len(found) >= 3:
            hr, cols = r, found
            break
    if hr < 0:
        raise LayoutError(key, f"{SHEET}: fiscal-year header row")
    if not any("£ million" in text(v) for row in grid[:hr] for v in row):
        raise LayoutError(key, f"{SHEET}: unit '£ million' above the header")
    marks = grid[hr + 1] if hr + 1 < len(grid) else []
    status = {}
    for c, _fy in cols:
        s = text(marks[c]).casefold() if c < len(marks) else ""
        if s not in ("outturn", "forecast"):
            raise LayoutError(key, f"{SHEET}!{a1(hr + 1, c)} outturn/forecast marker")
        status[c] = s

    where: dict[str, int] = {}
    for r in range(hr + 2, len(grid)):
        lab = _FOOT.sub("", text(grid[r][1])) if len(grid[r]) > 1 else ""
        if lab in _LINES:
            if lab in where:
                raise LayoutError(key, f"{SHEET}!{lab} (found twice)")
            where[lab] = r
    for lab in _LINES:
        if lab not in where:
            raise LayoutError(key, f"{SHEET}!{lab}")

    out: list[Row] = []
    vals: dict[tuple[str, str], float] = {}
    for lab, (slug, _t) in _LINES.items():
        r = where[lab]
        for c, fy in cols:
            v = num(grid[r][c]) if c < len(grid[r]) else None
            if v is None:
                continue
            vals[(slug, fy)] = v
            out.append(
                Row(f"pesa_uk.{slug}", fy, "fiscal_year", v, "gbp_m", "UK",
                    prov(meta, SHEET, a1(r, c), status[c], "PESA 2026"))
            )  # fmt: skip
    for _c, fy in cols:
        parts = [vals.get((s, fy)) for s in _FUNCTIONS]
        svc, adj, tme = (vals.get((s, fy)) for s in ("services", "accounting_adjustments", "tme"))
        if None in parts or svc is None or adj is None or tme is None:
            continue
        # published parts may be off by 1 from rounding (2021-22, 2023-24); more than ROUNDING is
        # a layout error
        if abs(sum(parts) - svc) > ROUNDING or svc + adj != tme:  # type: ignore[arg-type]
            raise LayoutError(key, f"{SHEET}: totals do not add up for {fy}")
    return out
