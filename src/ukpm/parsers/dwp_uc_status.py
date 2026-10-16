"""DWP Universal Credit statistics by immigration status and nationality (ods), sheet ``Table_1``.

Table_1: people on Universal Credit by immigration status, monthly, Great Britain. Counts of
people (not GBP, not households). Layout: the header row is the row whose column-B cell reads
``Immigration status``; month columns hold real dates (first of the month), latest first. The
status labels are matched by text and each must occur exactly once. The sheet's own text must
say it is about Universal Credit and people. Blank cells give no row. There is no total row
(the notes say disclosure control means totals need not equal the sum of the cells), so none is
made.

Period model: one series per status, ``dwp_uc_status.people.<slug>``, with one point per year
for the **May** count (the 2nd Thursday of May; the table runs from April 2022, so May 2022 to
May 2026). The point label is the bare year of that May (period basis ``may_snapshot``). The
latest month in this release is May 2026; other months are not published here, to keep the API
small. The last three months of the file are provisional (guidance sheet) and are marked so in
the vintage text.

Skipped: sheet ``Table_2`` (status by nationality by employment; its header says Apr-26, which
does not match the file title) and the Guidance sheet (read by people, quoted in definitions).
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ..provenance import Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError
from ._w2 import num, prov, text

SHEET = "Table_1"
MONTH = 5
PROVISIONAL_MONTHS = 3
BASIS = "may_snapshot"

# label as published (stripped) -> (slug, plain name)
_LINES = {
    "CTA - UK, Ireland, Right of Abode": ("cta", "British, Irish or right of abode (CTA)"),
    "EU Settlement Scheme": ("eu_settlement_scheme", "EU Settlement Scheme"),
    "Humanitarian": ("humanitarian", "Humanitarian routes"),
    "Refugee": ("refugee", "Refugee"),
    "Indefinite Leave to Remain": ("indefinite_leave_to_remain", "Indefinite leave to remain"),
    "Limited Leave to Remain including Family Reunion": (
        "limited_leave_to_remain",
        "Limited leave to remain (including family reunion)",
    ),
    "Other": ("other", "Other"),
    "No immigration status recorded on digital systems": (
        "no_status_recorded",
        "No immigration status recorded on digital systems",
    ),
}
_CAVEAT = (
    "Number of people on Universal Credit in Great Britain, by immigration status, in May of "
    "the year shown (the second Thursday of the month). Counts of people, not pounds, and not "
    "all benefits. Status comes from the Habitual Residence Test record and is the latest held. "
    "The last three months of each release are provisional and may be revised. 'No immigration "
    "status recorded' is a data category, not a measure of irregular status. Asylum seekers and "
    "people with no recourse to public funds cannot claim Universal Credit."
)

SERIES = {
    f"dwp_uc_status.people.{slug}": {
        "title": f"People on Universal Credit, {name}, May of each year (Great Britain)",
        "unit": "persons",
        "period_type": BASIS,
        "monetary": False,
        "description": _CAVEAT,
    }
    for slug, name in _LINES.values()
}


def _month(v: object) -> tuple[int, int] | None:
    if isinstance(v, datetime | date):
        return v.year, v.month
    return None


def parse(path: Path, meta: FileMeta) -> list[Row]:
    key = meta.file.key
    book = open_book(path)
    try:
        grid = book.rows(SHEET)
    except KeyError as e:
        raise LayoutError(key, f"sheet {SHEET}") from e
    blob = " ".join(text(v) for row in grid[:8] for v in row).casefold()
    if "universal credit" not in blob or "immigration status" not in blob:
        raise LayoutError(key, f"{SHEET}: title 'Universal Credit ... Immigration status'")
    hr = next(
        (r for r, row in enumerate(grid) if len(row) > 1 and text(row[1]) == "Immigration status"),
        -1,
    )
    if hr < 0:
        raise LayoutError(key, f"{SHEET}: header cell 'Immigration status'")
    months = [(c, ym) for c, v in enumerate(grid[hr]) if (ym := _month(v))]
    if len(months) < 12:
        raise LayoutError(key, f"{SHEET}: monthly date headers")
    order = [ym for _c, ym in months]
    if order != sorted(order, reverse=True):
        raise LayoutError(key, f"{SHEET}: months not latest-first")
    wanted = [(c, ym, i) for i, (c, ym) in enumerate(months) if ym[1] == MONTH]
    if not wanted:
        raise LayoutError(key, f"{SHEET}: a May column")

    where: dict[str, int] = {}
    for r in range(hr + 1, len(grid)):
        lab = text(grid[r][1]) if len(grid[r]) > 1 else ""
        if lab in _LINES:
            if lab in where:
                raise LayoutError(key, f"{SHEET}!{lab} (found twice)")
            where[lab] = r
    for lab in _LINES:
        if lab not in where:
            raise LayoutError(key, f"{SHEET}!{lab}")

    out: list[Row] = []
    for lab, (slug, _name) in _LINES.items():
        r = where[lab]
        for c, (year, _m), idx in wanted:
            v = num(grid[r][c]) if c < len(grid[r]) else None
            if v is None:
                continue
            vintage = f"{meta.file.edition}; May {year}"
            if idx < PROVISIONAL_MONTHS:
                vintage += " (provisional: latest three months)"
            out.append(
                Row(f"dwp_uc_status.people.{slug}", str(year), BASIS, v, "persons", "GB",
                    prov(meta, SHEET, a1(r, c), "outturn", vintage))
            )  # fmt: skip
    return out
