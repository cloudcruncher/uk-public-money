"""Home Office immigration system statistics, asylum summary tables, YE June 2026 (ods), sheet
``Asy_00a`` ("Asylum claims, initial decisions, awaiting an initial decision, appeals, support
and returns, by date of event").

Counts of people. Header: the row whose first cell reads ``Date / As at the end of...``; the
calendar-year columns are found by text (a bare four-digit year, 2015 onward). The two
``Year ending June`` columns and the change columns are not parsed (a different period basis;
documented as a gap). Row labels are matched by text and each must occur exactly once. Cells
that hold ``z`` (not applicable) or ``:`` (not available) give no row.

Series (``home_office_asylum.<slug>``, persons, calendar_year, UK): ``claims`` (people claiming
asylum in the year), ``awaiting_decision`` (people awaiting an initial decision, as at the end
of the year), ``support`` (asylum seekers in receipt of support, as at the end of the year) and
``support_hotels`` (of which accommodated in hotels, as at the end of the year; published from
2022). Counts only: the file has no pounds.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..provenance import Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError
from ._w2 import num, prov, text

SHEET = "Asy_00a"
FIRST_YEAR = 2015
_YEAR = re.compile(r"^(\d{4})$")
_HEAD = "Date / As at the end of..."

# label -> (slug, title, how it is counted)
_LINES = {
    "People claiming asylum": ("claims", "People claiming asylum", "in the calendar year"),
    "People awaiting an initial decision": (
        "awaiting_decision",
        "People awaiting an initial decision on an asylum claim",
        "as at the end of the year",
    ),
    "Asylum seekers in receipt of support": (
        "support",
        "Asylum seekers in receipt of Home Office support",
        "as at the end of the year",
    ),
    "Of which accommodated in hotels": (
        "support_hotels",
        "Asylum seekers in receipt of support who are accommodated in hotels",
        "as at the end of the year",
    ),
}

SERIES = {
    f"home_office_asylum.{slug}": {
        "title": f"{title} (calendar year)",
        "unit": "persons",
        "period_type": "calendar_year",
        "monetary": False,
        "description": f"Home Office immigration system statistics, table Asy_00a: {title}, "
        f"{how}. Counts of people, not pounds. Calendar years; the 'year ending June' columns "
        "are not included here. Figures are restated each quarter.",
    }
    for slug, title, how in _LINES.values()
}


def parse(path: Path, meta: FileMeta) -> list[Row]:
    key = meta.file.key
    book = open_book(path)
    try:
        grid = book.rows(SHEET)
    except KeyError as e:
        raise LayoutError(key, f"sheet {SHEET}") from e
    if not grid or not text(grid[0][0]).startswith("Asy_00a:"):
        raise LayoutError(key, f"{SHEET}!A1 title 'Asy_00a:'")
    hr = next((r for r, row in enumerate(grid) if row and text(row[0]) == _HEAD), -1)
    if hr < 0:
        raise LayoutError(key, f"{SHEET}: header cell {_HEAD!r}")
    cols = [
        (c, int(m.group(1)))
        for c, v in enumerate(grid[hr])
        if (m := _YEAR.match(text(v))) and int(m.group(1)) >= FIRST_YEAR
    ]
    if len(cols) < 5:
        raise LayoutError(key, f"{SHEET}: calendar-year columns")
    where: dict[str, int] = {}
    for r in range(hr + 1, len(grid)):
        lab = text(grid[r][0]) if grid[r] else ""
        if lab in _LINES:
            if lab in where:
                raise LayoutError(key, f"{SHEET}!{lab} (found twice)")
            where[lab] = r
    for lab in _LINES:
        if lab not in where:
            raise LayoutError(key, f"{SHEET}!{lab}")
    out: list[Row] = []
    for lab, (slug, _t, _h) in _LINES.items():
        r = where[lab]
        for c, year in cols:
            v = num(grid[r][c]) if c < len(grid[r]) else None
            if v is None:
                continue
            out.append(
                Row(f"home_office_asylum.{slug}", str(year), "calendar_year", v, "persons", "UK",
                    prov(meta, SHEET, a1(r, c), "outturn", meta.file.edition))
            )  # fmt: skip
    return out
