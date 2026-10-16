"""Home Office Core Data Tables 2026 (xlsx), sheet ``Total_departmental_spending``.

GBP thousand in the file; each value is scaled to GBP million by a recorded transformation
(``scale``, x 0.001) and the build scales on to GBP billion. The file name contains "draft"
("Core_Data_Tables_2026_Home_Office__draft__based_on_ARA_model_shared_29th_June__-_FINAL__FRT_");
the publisher says the numbers are based on the Annual Report and Accounts model.

Layout: a header row whose cells read ``2021-22`` ... (found by text), the next row holds
``OUTTURN`` or ``PLANS`` per column, the next the unit ``£'000``. Only the **Resource DEL**
block is read (from the ``Resource DEL`` row to the ``Total Resource DEL`` row), because the same
group names recur in the Capital DEL block. Columns marked PLANS are skipped (no plans are
published); only OUTTURN columns (2021-22 to 2025-26) are read. Blank cells give no row.

Lines (``home_office_spend.resource_del.<slug>``): customer services (visas and passports),
which is NET of fee income so is negative from 2022-23; asylum support, resettlement and
accommodation (from 2023-24; before that the function sat in 'Asylum & Protection', which is
not parsed because its cells are placeholders around a reorganisation); immigration enforcement
and border force (from 2023-24; the 0 cells for earlier years belong to a former structure and
are not published as zero); and total resource DEL. Group names change from year to year, so a
line is published only for the years the file shows it under that name.
"""

from __future__ import annotations

import re
from pathlib import Path

from .. import units
from ..provenance import Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError, normalise_fiscal_year
from ._w2 import num, prov, text

SHEET = "Total_departmental_spending"
_FY = re.compile(r"^\d{4}-\d{2}$")

# label -> (slug, title, first year published or None for all outturn years, note)
_LINES = {
    "Customer Services (Visas & Passports)": (
        "customer_services_visas_passports",
        "Customer Services (visas and passports), net of fee income",
        None,
    ),
    "Asylum Support, Resettlement and Accommodation": (
        "asylum_support_resettlement_accommodation",
        "Asylum support, resettlement and accommodation",
        "2023-24",
    ),
    "Immigration Enforcement": ("immigration_enforcement", "Immigration Enforcement", "2023-24"),
    "Border Force": ("border_force", "Border Force", "2023-24"),
    "Total Resource DEL": ("total", "Total resource spending (DEL)", None),
}
_STOP = "Total Resource DEL"
_DRAFT = (
    "The file is labelled 'draft' in its name and is based on the Home Office accounts model; "
    "check against the Annual Report and Accounts. Resource DEL only (day-to-day spending, not "
    "capital)."
)

SERIES = {
    f"home_office_spend.resource_del.{slug}": {
        "title": f"Home Office: {title} (resource DEL)",
        "unit": "gbp_m",
        "period_type": "fiscal_year",
        "monetary": True,
        "description": f"Home Office Core Data Tables 2026, resource DEL, {title}, outturn. "
        + _DRAFT
        + (
            " Negative because fee income is netted off the cost."
            if slug.startswith("customer_services")
            else ""
        ),
    }
    for slug, title, _first in _LINES.values()
}


def parse(path: Path, meta: FileMeta) -> list[Row]:
    key = meta.file.key
    book = open_book(path)
    try:
        grid = book.rows(SHEET)
    except KeyError as e:
        raise LayoutError(key, f"sheet {SHEET}") from e
    hr = next(
        (r for r, row in enumerate(grid) if sum(bool(_FY.match(text(v))) for v in row) >= 5), -1
    )
    if hr < 0 or hr + 2 >= len(grid):
        raise LayoutError(key, f"{SHEET}: fiscal-year header row")
    cols = []
    for c, v in enumerate(grid[hr]):
        if not _FY.match(text(v)):
            continue
        mark = text(grid[hr + 1][c]).upper() if c < len(grid[hr + 1]) else ""
        if mark not in ("OUTTURN", "PLANS", "PLANS (CAPITAL ONLY)"):
            raise LayoutError(key, f"{SHEET}!{a1(hr + 1, c)} OUTTURN/PLANS marker")
        if mark == "OUTTURN":
            if "£'000" not in text(grid[hr + 2][c]):
                raise LayoutError(key, f"{SHEET}!{a1(hr + 2, c)} unit £'000")
            cols.append((c, normalise_fiscal_year(text(v))))
    if not cols:
        raise LayoutError(key, f"{SHEET}: OUTTURN columns")
    start = next((r for r in range(hr + 3, len(grid)) if text(grid[r][0]) == "Resource DEL"), -1)
    stop = next((r for r in range(start + 1, len(grid)) if text(grid[r][0]) == _STOP), -1)
    if start < 0 or stop < 0:
        raise LayoutError(key, f"{SHEET}: 'Resource DEL' block")
    where: dict[str, int] = {}
    for r in range(start + 1, stop + 1):
        lab = text(grid[r][0])
        if lab in _LINES:
            if lab in where:
                raise LayoutError(key, f"{SHEET}!{lab} (found twice in Resource DEL)")
            where[lab] = r
    for lab in _LINES:
        if lab not in where:
            raise LayoutError(key, f"{SHEET}!{lab}")

    out: list[Row] = []
    for lab, (slug, _title, first) in _LINES.items():
        r = where[lab]
        for c, fy in cols:
            v = num(grid[r][c]) if c < len(grid[r]) else None
            if v is None or (first and fy < first):
                continue
            row = Row(f"home_office_spend.resource_del.{slug}", fy, "fiscal_year", v, "gbp_k", "UK",
                      prov(meta, SHEET, a1(r, c), "outturn", meta.file.edition))  # fmt: skip
            out.append(units.scale(row, 0.001, "GBP thousand to GBP million (x 0.001)", "gbp_m"))
    return out
