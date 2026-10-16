"""ONS mid-year population estimates for the UK, England, Wales, Scotland and Northern Ireland.

File: ``mye25tablesuk.xlsx`` (mid-2025 estimates, published 1 October 2026).

Sheet ``MYE4`` ("Summary for the UK, mid-2011 to mid-2025"): the header row is the first row with
three or more ``Mid-YYYY`` cells; columns are found by that text and years before 2015 are
skipped. Geography rows are found by the exact text in the ``Name`` column (verified on the
mid-2025 file): ``UNITED KINGDOM`` (row 9, required), ``GREAT BRITAIN`` (row 10) and ``ENGLAND``
(row 12). ``ENGLAND AND WALES`` is a different row and is not used. A geography row that is absent
is simply not emitted (GB and England are optional); a missing UK row raises ``LayoutError``.

Cross-check: ``MYE1`` "All Persons" in the United Kingdom column must equal the MYE4 UK mid-2025
cell, otherwise ``LayoutError``. It adds no series.

Mid-year to fiscal year: the estimate is for 30 June YYYY, which falls in the April-March fiscal
year YYYY-(YY+1), so Mid-2024 is ``2024-25``. A year whose column is missing has no row (a gap).
Blank, ``..``, ``-`` and ``x`` cells give no row. Values are never rounded. The licence is taken
from the registry entry (``meta.source.licence``); this module does not assert it.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..provenance import Provenance, Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError

SOURCE = "ons_population"
MYE4 = "MYE4"
MYE1 = "MYE1"
FIRST_YEAR = 2015
_MID = re.compile(r"^Mid-(\d{4})$")
_MAPPING = (
    "Mid-year (30 June) estimate; mid-YYYY is mapped to the April-March fiscal year "
    "YYYY-(YY+1) that contains 30 June (Mid-2024 is 2024-25)."
)

# MYE4 'Name' text -> (series id, geography)
GEOGRAPHIES = {
    "UNITED KINGDOM": ("ons_population.uk", "UK"),
    "GREAT BRITAIN": ("ons_population.gb", "GB"),
    "ENGLAND": ("ons_population.england", "England"),
}

SERIES = {
    sid: {
        "title": f"Population, {geo} (ONS mid-year estimate)",
        "unit": "persons",
        "period_type": "fiscal_year",
        "monetary": False,
        "description": f"ONS MYE4, {name.title()}, all persons. {_MAPPING}",
    }
    for name, (sid, geo) in GEOGRAPHIES.items()
}


def _fy(year: int) -> str:
    return f"{year}-{(year + 1) % 100:02d}"


def _num(v: object) -> float | None:
    return float(v) if isinstance(v, int | float) and not isinstance(v, bool) else None


def _prov(meta: FileMeta, sheet: str, cell: str) -> Provenance:
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
        status="outturn",
        vintage=meta.file.edition,
        retrieved_at=meta.fetched_at,
    )


def _text(v: object) -> str:
    return " ".join(v.split()) if isinstance(v, str) else ""


def _header(grid: list[list], meta: FileMeta) -> tuple[int, int, dict[int, int]]:
    """(header row, Name column, {column: year}) for MYE4."""
    for r, row in enumerate(grid):
        years = {c: int(m.group(1)) for c, v in enumerate(row) if (m := _MID.match(_text(v)))}
        if len(years) >= 3:
            name_cols = [c for c, v in enumerate(row) if _text(v) == "Name"]
            if not name_cols:
                raise LayoutError(meta.file.key, f"{MYE4}!Name")
            return r, name_cols[0], years
    raise LayoutError(meta.file.key, f"{MYE4}!Mid-YYYY header row")


def _check_mye1(book, meta: FileMeta, uk_latest: float) -> None:
    try:
        grid = book.rows(MYE1)
    except KeyError as e:
        raise LayoutError(meta.file.key, MYE1) from e
    hdr = next(
        (
            (r, c)
            for r, row in enumerate(grid)
            for c, v in enumerate(row)
            if _text(v) == "United Kingdom"
        ),
        None,
    )
    if hdr is None:
        raise LayoutError(meta.file.key, f"{MYE1}!United Kingdom")
    hr, uc = hdr
    for r in range(hr + 1, len(grid)):
        if _text(grid[r][0]) == "All Persons":
            v = _num(grid[r][uc])
            if v != uk_latest:
                raise LayoutError(
                    meta.file.key,
                    f"{MYE1}!{a1(r, uc)} ({v}) differs from {MYE4} UK latest ({uk_latest})",
                )
            return
    raise LayoutError(meta.file.key, f"{MYE1}!All Persons")


def parse(path: Path, meta: FileMeta) -> list[Row]:
    book = open_book(path)
    try:
        grid = book.rows(MYE4)
    except KeyError as e:
        raise LayoutError(meta.file.key, MYE4) from e
    hr, nc, years = _header(grid, meta)
    cols = sorted(((c, y) for c, y in years.items() if y >= FIRST_YEAR), key=lambda t: t[1])
    if not cols:
        raise LayoutError(meta.file.key, f"{MYE4}!Mid-YYYY columns from {FIRST_YEAR}")
    out: list[Row] = []
    uk_row = -1
    found: set[str] = set()
    for r in range(hr + 1, len(grid)):
        name = _text(grid[r][nc]).upper() if nc < len(grid[r]) else ""
        if name not in GEOGRAPHIES or name in found:
            continue
        found.add(name)
        sid, geo = GEOGRAPHIES[name]
        if name == "UNITED KINGDOM":
            uk_row = r
        for c, y in cols:
            v = _num(grid[r][c]) if c < len(grid[r]) else None
            if v is not None:
                prov = _prov(meta, MYE4, a1(r, c))
                out.append(Row(sid, _fy(y), "mid_year", v, "persons", geo, prov))
    if uk_row < 0:
        raise LayoutError(meta.file.key, f"{MYE4}!UNITED KINGDOM")
    latest_c = max(years, key=years.__getitem__)
    uk_latest = _num(grid[uk_row][latest_c])
    if uk_latest is None:
        raise LayoutError(meta.file.key, f"{MYE4}!{a1(uk_row, latest_c)}")
    _check_mye1(book, meta, uk_latest)
    return out
