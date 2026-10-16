"""OBR Economic and fiscal outlook, March 2026, detailed forecast tables: receipts (xlsx).

Sheet used: ``3.8`` ("Current receipts (on a cash basis)", unit ``£ billion``). Layout read from
the real file (sha256 f65b6cb7...): the year headings (``2024-25`` ... ``2030-31``) are the first
row with three or more fiscal-year cells (row 5), the row above holds the status markers
(``Outturn`` over 2024-25, ``Forecast`` over 2025-26 onward; a marker applies from its column to
the next marker). Labels are in column B (top lines) or C (``of which`` lines) and are matched by
text after removing a trailing footnote digit (``Income tax (gross of tax credits)1``); each label
must occur exactly once or LayoutError is raised. The unit must read ``£ billion``.

Series (``obr_efo_receipts.<slug>``, gbp_bn, cash basis): ``income_tax`` (row 7), ``nics`` (12),
``vat`` (13), ``corporation_tax`` (14), ``total_hmrc`` (51) and ``current_receipts`` (64, includes
non-HMRC receipts such as business rates and council tax). Vintage ``OBR EFO March 2026``.
Same cash basis as the HMRC receipts (hmrc_receipts), so the HMRC lines agree for outturn years
(rule R13); only ``current_receipts`` is broader, because it adds non-HMRC receipts.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..provenance import Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError, normalise_fiscal_year
from ._w2 import num, prov, text

SHEET = "3.8"
VINTAGE = "OBR EFO March 2026"
UNIT = "gbp_bn"
_FOOT = re.compile(r"(?<=[a-z)])\d+$")

# label -> (slug, title)
_LINES = {
    "Income tax (gross of tax credits)": ("income_tax", "Income tax (gross of tax credits)"),
    "National insurance contributions": ("nics", "National insurance contributions"),
    "Value added tax": ("vat", "Value added tax"),
    "Corporation tax": ("corporation_tax", "Corporation tax"),
    "Total HMRC": ("total_hmrc", "Total HMRC receipts"),
    "Current receipts": ("current_receipts", "Total current receipts"),
}

SERIES = {
    f"obr_efo_receipts.{slug}": {
        "title": f"{title} (OBR EFO March 2026)",
        "unit": UNIT,
        "period_type": "fiscal_year",
        "monetary": True,
        "description": "OBR EFO March 2026 detailed forecast tables, receipts, table 3.8, GBP "
        "billion, cash basis. 2024-25 is outturn, later years are forecast.",
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
    if hr < 1:
        raise LayoutError(key, f"{SHEET}: fiscal-year header row")
    if not any(text(v) == "£ billion" for row in grid[:hr] for v in row):
        raise LayoutError(key, f"{SHEET}: unit '£ billion' above the header")
    marks = {
        c: text(v).casefold()
        for c, v in enumerate(grid[hr - 1])
        if text(v).casefold() in ("outturn", "forecast")
    }
    status: dict[int, str] = {}
    for c, _fy in cols:
        prior = [m for m in marks if m <= c]
        if not prior:
            raise LayoutError(key, f"{SHEET}: status marker for {a1(hr - 1, c)}")
        status[c] = marks[max(prior)]

    where: dict[str, int] = {}
    for r in range(hr + 1, len(grid)):
        for v in grid[r][:3]:
            lab = _FOOT.sub("", text(v))
            if lab in _LINES:
                if lab in where:
                    raise LayoutError(key, f"{SHEET}!{lab} (found twice)")
                where[lab] = r
    out: list[Row] = []
    for lab, (slug, _t) in _LINES.items():
        if lab not in where:
            raise LayoutError(key, f"{SHEET}!{lab}")
        r = where[lab]
        for c, fy in cols:
            v = num(grid[r][c]) if c < len(grid[r]) else None
            if v is not None:
                out.append(
                    Row(f"obr_efo_receipts.{slug}", fy, "fiscal_year", v, UNIT, "UK",
                        prov(meta, SHEET, a1(r, c), status[c], VINTAGE))
                )  # fmt: skip
        if not any(x.series_id == f"obr_efo_receipts.{slug}" for x in out):
            raise LayoutError(key, f"{SHEET}!{lab}: no values")
    return out
