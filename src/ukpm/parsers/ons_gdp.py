"""ONS UK nominal GDP, series YBHA (UKEA dataset), annual, CSV from the ONS generator endpoint.

File layout (verified on the 30-09-2026 release): lines 1-8 are metadata (``"Title"``,
``"CDID"``, ``"Source dataset ID"``, ``"PreUnit"``, ``"Unit"``, ``"Release date"``,
``"Next release"``, ``"Important notes"``), then ``"year","value"`` rows with four-digit years;
quarterly rows (``"2026 Q2"``) follow and are ignored. CDID must be ``YBHA`` and Unit ``m`` (GBP
million, current prices), else LayoutError. The release date (``DD-MM-YYYY``) is stored as the
vintage because nominal GDP is revised every quarter (2025 moved +10,728m between two vintages).

Series ``ons_gdp.nominal`` (gbp_m) is CALENDAR-year GDP: the label in ``fiscal_year`` is the bare
calendar year (``2025``) with period basis ``calendar_year``. It is deliberately not relabelled as
a fiscal year. It is not the PSF % GDP denominator (a 12-month centred total). Years from 2015.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

from ..provenance import Row
from . import FileMeta, LayoutError
from ._w2 import prov

SERIES_CDID = "YBHA"
FIRST_YEAR = 2015
_YEAR = re.compile(r"^\d{4}$")

SERIES = {
    "ons_gdp.nominal": {
        "title": "UK nominal GDP at market prices, calendar year (ONS YBHA)",
        "unit": "gbp_m",
        "period_type": "calendar_year",
        "monetary": True,
        "description": "ONS YBHA: Gross Domestic Product at market prices, current price, "
        "seasonally adjusted, GBP million, calendar year, UK Economic Accounts. Revised each "
        "quarter; the release date is the vintage.",
    }
}


def parse(path: Path, meta: FileMeta) -> list[Row]:
    key = meta.file.key
    lines = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))
    head = {r[0]: (r[1] if len(r) > 1 else "") for r in lines[:8] if r}
    if head.get("CDID") != SERIES_CDID:
        raise LayoutError(key, f"CDID {SERIES_CDID}")
    if head.get("Unit") != "m" or head.get("PreUnit") != "£":
        raise LayoutError(key, "Unit '£m'")
    try:
        released = datetime.strptime(head["Release date"], "%d-%m-%Y").date().isoformat()
    except (KeyError, ValueError) as e:
        raise LayoutError(key, "Release date DD-MM-YYYY") from e
    vintage = f"ONS UKEA release {released}"
    query = (
        "ons.gov.uk/generator?format=csv&uri=/economy/grossdomesticproductgdp/timeseries/ybha/ukea"
    )
    out: list[Row] = []
    for i, r in enumerate(lines[8:], start=9):
        if len(r) < 2 or not _YEAR.match(r[0]) or int(r[0]) < FIRST_YEAR:
            continue
        try:
            value = float(r[1])
        except ValueError as e:
            raise LayoutError(key, f"line {i}: value {r[1]!r} is not a number") from e
        out.append(
            Row(
                "ons_gdp.nominal",
                r[0],
                "calendar_year",
                value,
                "gbp_m",
                "UK",
                prov(meta, path.name, f"line {i}", "outturn", vintage, query),
            )
        )
    if not out:
        raise LayoutError(key, f"annual rows from {FIRST_YEAR}")
    return out
