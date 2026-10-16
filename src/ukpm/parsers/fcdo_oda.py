"""FCDO provisional UK ODA spend 2025 (ods): in-donor refugee costs (IDRC), sheet ``Fig3``.

Figure 3, "Total UK In-donor Refugee Costs (IDRC) incurred in the UK: by Department", GBP million,
CALENDAR years (2021 to 2025). Header: the row whose first cell is ``Department``; year columns
are found by text (``2021 [note 3]`` and so on; the note marks and the ``£ million`` line are
ignored) and every year header must say ``£ million``. Departments are matched by label text;
each must occur exactly once, else LayoutError. The ``Total`` row is checked against the sum of
the department rows (the table notes that rounding can make them differ, so a tolerance of 1.5
GBP m is allowed). The ``Percentage of total ODA`` row and the change columns are not parsed.

Series ``fcdo_oda.idrc.<slug>`` (gbp_m, calendar_year, UK). The year goes in ``fiscal_year`` as a
bare calendar year, as ``ons_gdp.nominal`` does. The figures are provisional (the final 2025
release is due in autumn 2026) and cover only the first 12 months of a person's stay.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..provenance import Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError
from ._w2 import num, prov, text

SHEET = "Fig3"
ROUNDING = 1.5  # GBP m; the table says figures may not sum to totals due to rounding
_YEAR = re.compile(r"^(20\d{2})\b")
_DEFINITION = (
    "OECD in-donor refugee costs (IDRC): money spent in the UK on supporting asylum seekers and "
    "refugees from developing countries during the first 12 months of their stay, counted as UK "
    "aid (ODA) under OECD rules. Calendar year. Provisional. Spending after the first 12 months "
    "is not included."
)

# label as published -> (slug, short name)
_LINES = {
    "Home Office": ("home_office", "Home Office"),
    "Department for Health and Social Care": ("dhsc", "Department of Health and Social Care"),
    "Department for Education": ("dfe", "Department for Education"),
    "Ministry of Housing, Communities and Local Government": (
        "mhclg",
        "Ministry of Housing, Communities and Local Government",
    ),
    "Department for Work and Pensions": ("dwp", "Department for Work and Pensions"),
    "Other In-Donor Refugee Costs": (
        "other",
        "other bodies (including estimated devolved health and education)",
    ),
    "HM Revenue and Customs": ("hmrc", "HM Revenue and Customs"),
    "Total in-donor refugee costs in the UK": ("total", "all departments"),
}
_PARTS = [s for s, _ in list(_LINES.values())[:-1]]
_NOTE = re.compile(r"\s*\[note \d+\]\s*$")

SERIES = {
    f"fcdo_oda.idrc.{slug}": {
        "title": f"In-donor refugee costs, {name} (calendar year, provisional)",
        "unit": "gbp_m",
        "period_type": "calendar_year",
        "monetary": True,
        "description": f"FCDO provisional UK ODA spend 2025, Figure 3, {name}, GBP million, "
        f"calendar year. {_DEFINITION}",
    }
    for slug, name in _LINES.values()
}


def _label(v: object) -> str:
    return _NOTE.sub("", text(v))


def parse(path: Path, meta: FileMeta) -> list[Row]:
    key = meta.file.key
    book = open_book(path)
    try:
        grid = book.rows(SHEET)
    except KeyError as e:
        raise LayoutError(key, f"sheet {SHEET}") from e
    hr = next((r for r, row in enumerate(grid) if row and text(row[0]) == "Department"), -1)
    if hr < 0:
        raise LayoutError(key, f"{SHEET}: header row starting 'Department'")
    cols: list[tuple[int, str]] = []
    for c, v in enumerate(grid[hr]):
        m = _YEAR.match(text(v))
        if m:
            if "£ million" not in text(v):
                raise LayoutError(key, f"{SHEET}!{a1(hr, c)} unit '£ million'")
            cols.append((c, m.group(1)))
    if len(cols) < 3:
        raise LayoutError(key, f"{SHEET}: calendar-year columns")
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

    out: list[Row] = []
    vals: dict[tuple[str, str], float] = {}
    for lab, (slug, _name) in _LINES.items():
        r = where[lab]
        for c, year in cols:
            v = num(grid[r][c]) if c < len(grid[r]) else None
            if v is None:
                continue
            vals[(slug, year)] = v
            out.append(
                Row(f"fcdo_oda.idrc.{slug}", year, "calendar_year", v, "gbp_m", "UK",
                    prov(meta, SHEET, a1(r, c), "outturn", meta.file.edition))
            )  # fmt: skip
    for _c, year in cols:
        parts = [vals.get((s, year)) for s in _PARTS]
        total = vals.get(("total", year))
        if None in parts or total is None:
            continue
        if abs(sum(parts) - total) > ROUNDING:  # type: ignore[arg-type]
            raise LayoutError(key, f"{SHEET}: departments do not add up to the total for {year}")
    return out
