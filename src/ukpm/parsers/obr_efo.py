"""OBR Economic and fiscal outlook (EFO), March 2026, detailed forecast tables: expenditure (xlsx).

Sheet used: `4.9` ("Post measures breakdown of welfare spending", unit "£ billion"). Layout read
from the real file (sha256 700bfd70...): row 3 holds the unit, row 4 the status markers
(`Outturn` over the first year column, `Forecast` over the rest; the markers sit in the first
cell of a merged span, so a marker applies from its column to the next marker), row 5 the year
headings as text (`2024-25` ... `2030-31`), column B the labels. Year columns are found by text
on the first row with three or more fiscal-year headings; the unit must be "£ billion" or the
parser raises LayoutError.

Status: read from the Outturn/Forecast marker row. If a sheet has no marker at all, every value is
`forecast` (this is a forecast publication). Vintage is `OBR EFO March 2026`.

Series (located by label inside the "Welfare cap" block, i.e. between the rows "Welfare cap" and
"Total welfare cap"; "Universal credit" repeats in the block outside the cap and is not used. Each
label must occur exactly once in the block):
- `obr_efo.welfare_cap.universal_credit`   "Universal credit"                      GB
- `obr_efo.welfare_cap.other_dwp`          "Other DWP in welfare cap"              GB
- `obr_efo.welfare_cap.ni_social_security` "NI social security in welfare cap"     Northern Ireland

Cells holding `*` (less than £0.1bn) or blanks give no row. Skipped in this slice: sheet 4.2
(total managed expenditure, % GDP), sheet 4.11 (Universal Credit elements) and all other sheets;
the EFO receipts and policy workbooks were not inspected."""

from __future__ import annotations

from pathlib import Path

from ..provenance import Provenance, Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError, normalise_fiscal_year

SHEET = "4.9"
VINTAGE = "OBR EFO March 2026"
UNIT = "gbp_bn"
_DESC = (
    "OBR EFO March 2026, sheet 4.9, GBP billion, nominal. Status is read from the sheet's "
    "Outturn/Forecast row; if a sheet had none, every value would be labelled forecast, as "
    "published in the March 2026 forecast, and earlier years may be outturn estimates."
)

# series_id -> (label on sheet 4.9, geography, title)
_LINES = {
    "obr_efo.welfare_cap.universal_credit": (
        "Universal credit",
        "GB",
        "Universal Credit within the welfare cap (OBR forecast)",
    ),
    "obr_efo.welfare_cap.other_dwp": (
        "Other DWP in welfare cap",
        "GB",
        "Other DWP social security within the welfare cap (OBR forecast)",
    ),
    "obr_efo.welfare_cap.ni_social_security": (
        "NI social security in welfare cap",
        "Northern Ireland",
        "Northern Ireland social security within the welfare cap (OBR forecast)",
    ),
}

SERIES = {
    sid: {
        "title": title,
        "unit": UNIT,
        "period_type": "fiscal_year",
        "monetary": True,
        "description": _DESC,
    }
    for sid, (_label, _geo, title) in _LINES.items()
}


def _year(v: object) -> str | None:
    if not isinstance(v, str):
        return None
    try:
        return normalise_fiscal_year(v)
    except ValueError:
        return None


def _header(grid: list[list], key: str) -> tuple[int, list[tuple[int, str]]]:
    for r, row in enumerate(grid):
        cols = [(c, fy) for c, v in enumerate(row) if (fy := _year(v))]
        if len(cols) >= 3:
            return r, cols
    raise LayoutError(key, f"{SHEET}: year heading row")


def _statuses(grid: list[list], hr: int, cols: list[tuple[int, str]]) -> dict[int, str]:
    marks: dict[int, str] = {}
    for r in (hr - 1, hr + 1):
        if r < 0 or r >= len(grid):
            continue
        for c, v in enumerate(grid[r]):
            t = v.strip().casefold() if isinstance(v, str) else ""
            if t in ("outturn", "forecast"):
                marks[c] = t
    if not marks:
        return {c: "forecast" for c, _ in cols}
    out: dict[int, str] = {}
    for c, _fy in cols:
        prior = [m for m in marks if m <= c]
        if not prior:
            raise LayoutError("obr_efo", f"{SHEET}: status marker for column {a1(0, c)}")
        out[c] = marks[max(prior)]
    return out


def _section(grid: list[list], hr: int, key: str) -> tuple[int, int]:
    """Row span of the 'Welfare cap' block. 'Universal credit' also appears under the block
    'Welfare spending outside the welfare cap', so labels are only looked up inside this span."""

    def find(text: str) -> int:
        want = text.casefold()
        for r in range(hr + 1, len(grid)):
            if any(isinstance(v, str) and v.strip().casefold() == want for v in grid[r]):
                return r
        raise LayoutError(key, f"{SHEET}!{text}")

    lo, hi = find("Welfare cap"), find("Total welfare cap")
    if hi <= lo:
        raise LayoutError(key, f"{SHEET}: 'Total welfare cap' before 'Welfare cap'")
    return lo + 1, hi


def parse(path: Path, meta: FileMeta) -> list[Row]:
    key = meta.file.key
    book = open_book(path)
    if SHEET not in book.sheet_names:
        raise LayoutError(key, f"sheet {SHEET}")
    grid = book.rows(SHEET)
    hr, cols = _header(grid, key)
    if not any(
        isinstance(v, str) and "£ billion" in v.casefold() for row in grid[:hr] for v in row
    ):
        raise LayoutError(key, f"{SHEET}: unit '£ billion' above the year headings")
    status = _statuses(grid, hr, cols)

    lo, hi = _section(grid, hr, key)
    out: list[Row] = []
    for sid, (label, geo, _title) in _LINES.items():
        want = label.casefold()
        hits = [
            (r, c)
            for r in range(lo, hi)
            for c, v in enumerate(grid[r])
            if isinstance(v, str) and v.strip().casefold() == want
        ]
        if len(hits) != 1:
            raise LayoutError(key, f"{SHEET}!{label} (found {len(hits)} times)")
        r = hits[0][0]
        for c, fy in cols:
            v = grid[r][c] if c < len(grid[r]) else None
            if isinstance(v, int | float) and not isinstance(v, bool):
                out.append(
                    Row(
                        sid,
                        fy,
                        "fiscal_year",
                        float(v),
                        UNIT,
                        geo,
                        Provenance(
                            publisher=meta.source.publisher,
                            dataset=meta.source.dataset,
                            edition=meta.file.edition,
                            publication_date=meta.file.publication_date,
                            source_url=meta.file.file_url,
                            landing_url=meta.file.landing_url,
                            file_sha256=meta.sha256,
                            sheet=SHEET,
                            cell_or_range=a1(r, c),
                            api_query=None,
                            licence=meta.source.licence,
                            transformations=(),
                            status=status[c],
                            vintage=VINTAGE,
                            retrieved_at=meta.fetched_at,
                        ),
                    )
                )
        if not any(x.series_id == sid for x in out):
            raise LayoutError(key, f"{SHEET}!{label}: no values")
    return out
