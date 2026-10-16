"""ONS Families and households in the UK, 2025 (xlsx): number of households.

Sheet ``5`` ("Table 5: Households by size, United Kingdom, 1996 to 2025"), thousands. The header
row is the first row whose cells include ``<year> Estimate``; each year is a triplet
(Estimate, CV, CI+/-) and only the Estimate column is read. The row is found by the label
``All households`` in column A. Years from 2011 are emitted: the household definition changed
between 2010 and 2011 (Notes, note 9: 1996-2010 'share one main meal a day or share living
accommodation'; 2011 onwards 'share cooking facilities and share a living room or sitting room or
dining area'), so pre-2011 values are not comparable and are not emitted.

Series ``ons_households.uk`` (unit ``thousands``): the Labour Force Survey April-June quarter of
calendar year YYYY, mapped to the fiscal year YYYY-(YY+1) in which it falls (2025 -> 2025-26).
It is a sample survey estimate (2025: 29,003 +/- 155), not a census count, and covers private
households only (no communal establishments). The estimate is outturn.

The workbook cover sheet row 2 must read ``Date published: ...`` or LayoutError is raised.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..provenance import Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError
from ._w2 import num, prov, text

SHEET = "5"
FIRST_YEAR = 2011
_EST = re.compile(r"^(\d{4}) Estimate$")
_NOTE = (
    "Definition change in 2011: 1996-2010 households share one main meal a day or living "
    "accommodation; 2011 onwards they share cooking facilities and a living/sitting/dining "
    "room (Notes, note 9). Only 2011 onwards is emitted. LFS sample estimate, April-June "
    "quarter, private households only."
)

SERIES = {
    "ons_households.uk": {
        "title": "Households in the UK (ONS, Labour Force Survey)",
        "unit": "thousands",
        "period_type": "fiscal_year",
        "monetary": False,
        "description": f"ONS Families and households, table 5, All households. {_NOTE}",
    }
}


def parse(path: Path, meta: FileMeta) -> list[Row]:
    key = meta.file.key
    book = open_book(path)
    try:
        cover = book.rows("Cover sheet")
        grid = book.rows(SHEET)
    except KeyError as e:
        raise LayoutError(key, str(e.args[0])) from e
    if not any(text(v).startswith("Date published:") for row in cover[:6] for v in row):
        raise LayoutError(key, "Cover sheet: 'Date published:'")
    hdr = None
    for r, row in enumerate(grid):
        cols = {int(m.group(1)): c for c, v in enumerate(row) if (m := _EST.match(text(v)))}
        if len(cols) >= 3:
            hdr = (r, cols)
            break
    if hdr is None:
        raise LayoutError(key, f"{SHEET}: '<year> Estimate' header row")
    hr, cols = hdr
    hits = [r for r in range(hr + 1, len(grid)) if text(grid[r][0]) == "All households"]
    if len(hits) != 1:
        raise LayoutError(key, f"{SHEET}!All households (found {len(hits)} times)")
    r = hits[0]
    out: list[Row] = []
    for year, c in sorted(cols.items()):
        v = num(grid[r][c])
        if year < FIRST_YEAR or v is None:
            continue
        out.append(
            Row(
                "ons_households.uk",
                f"{year}-{(year + 1) % 100:02d}",
                "apr_jun_quarter",
                v,
                "thousands",
                "UK",
                prov(meta, SHEET, a1(r, c), "outturn"),
            )
        )
    if not out:
        raise LayoutError(key, f"{SHEET}!All households: no values from {FIRST_YEAR}")
    return out
