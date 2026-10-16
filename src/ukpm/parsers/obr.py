"""OBR Public Finances Databank parser (`PSF_aggregates_databank_*.xlsx`).

Licence evidence (fetched 2026-10-15, https://obr.uk/copyright/, HTTP 200). Verbatim quote:

    "You may use and re-use the information featured on this website (not including logos) free
    of charge in any format or medium, under the terms of the Open Government Licence."

The page links the unversioned Open Government Licence URL on nationalarchives.gov.uk and does
not print "v3.0", so the version is inferred (v3 is the current OGL). Logos are excluded.

Sheets used (names exact; columns and rows are found by label, never by address):
  - "Aggregates (£bn)": receipts, TME, current expenditure, net/gross investment, depreciation,
    national accounts taxes (£bn, nominal).
  - "Receipts (£bn)": receipts by tax (£bn, nominal). The two total columns are skipped because
    "Aggregates (£bn)" already supplies them.
  - "Aggregates (per cent of GDP)": column "Nominal GDP (£ billion)" -> obr.gdp_nominal.
  - "Aggregates (2025-26 prices)": column "GDP Deflator (2025-26=100)" -> obr.gdp_deflator.
    Its "£ billion (2024-25 prices)" title disagrees with the sheet name; only the deflator
    column is read, and its base year is read from its own header.
  - Same sheet, column "Total managed expenditure" -> obr.psf.tme_real (OBR's own real-terms
    TME, kept as published for the R5 cross-check only). The sheet title says "2024-25 prices"
    while the deflator header says 2025-26=100; the base is settled by R5 against the data.
Skipped: "Changes since last (OLD)" and "Spending and receipts" (no data), "Public finances since
1900" (long history, out of scope), "Glossary", and every other column of the sheets above.

Status: each sheet carries the note "Forecast years from 2026-27 are consistent with the OBR
Economic and fiscal outlook forecast published March 2026". Years before that year are
`outturn`, the rest `forecast`. Rows start at 2015-16 (FIRST_YEAR). Blank and "-" cells give no
row. Values are published in £bn and are not rounded or scaled. Vintage is "OBR databank <Mon
YYYY>" taken from the registry edition; the forecast years themselves are the March 2026 EFO.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..provenance import Provenance, Row
from ..sheets import Book, a1, open_book
from . import FileMeta, LayoutError, normalise_fiscal_year

FIRST_YEAR = 2015
AGG = "Aggregates (£bn)"
REC = "Receipts (£bn)"
PCT = "Aggregates (per cent of GDP)"
REAL = "Aggregates (2025-26 prices)"

# header label (case-folded) -> (series_id, title)
_AGG_COLS = {
    "public sector current receipts": ("obr.psf.receipts", "Public sector current receipts"),
    "total managed expenditure": ("obr.psf.tme", "Total managed expenditure"),
    "public sector current expenditure": (
        "obr.psf.current_expenditure",
        "Public sector current expenditure",
    ),
    "public sector net investment": ("obr.psf.net_investment", "Public sector net investment"),
    "depreciation": ("obr.psf.depreciation", "Depreciation"),
    "public sector gross investment": (
        "obr.psf.gross_investment",
        "Public sector gross investment",
    ),
    "national account taxes": ("obr.psf.national_accounts_taxes", "National accounts taxes"),
}
_RECEIPT_SKIP = {"public sector current receipts", "national accounts taxes"}
_RECEIPT_ANCHOR = "VAT (net of VAT refunds)"
_SLUG_OVERRIDES = {
    "pay as your earn income tax": "paye_income_tax",
    "self assessed income tax": "sa_income_tax",
    "national insurance contributions": "nics",
    "public sector gross operating surplus": "gross_operating_surplus",
}

SERIES: dict[str, dict[str, Any]] = {
    sid: {"title": t, "unit": "gbp_bn", "period_type": "fiscal_year", "monetary": True}
    for sid, t in _AGG_COLS.values()
}
SERIES["obr.gdp_nominal"] = {
    "title": "Nominal GDP (fiscal year)",
    "unit": "gbp_bn",
    "period_type": "fiscal_year",
    "monetary": False,
}
SERIES["obr.gdp_deflator"] = {
    "title": "GDP deflator at market prices (base year = 100)",
    "unit": "index",
    "period_type": "fiscal_year",
    "monetary": False,
}
SERIES["obr.psf.tme_real"] = {
    "title": "Total managed expenditure, databank real terms (as published)",
    "unit": "gbp_bn",
    "period_type": "fiscal_year",
    "monetary": False,
}
# obr.receipts.<tax> series are registered dynamically by parse() (labels come from the file).

_FORECAST_RE = re.compile(r"Forecast years from (\d{4}-\d{2})")
_FOOTNOTE_RE = re.compile(r"(?<=[A-Za-z)])\d+$")


def _slug(label: str) -> str:
    base = re.sub(r"\(.*?\)", " ", _FOOTNOTE_RE.sub("", label.strip()).lower())
    clean = re.sub(r"[^a-z0-9 ]+", "", base)
    clean = re.sub(r"\s+", " ", clean).strip()
    return _SLUG_OVERRIDES.get(clean, re.sub(r" ", "_", clean)[:60].rstrip("_"))


def _header_row(book: Book, sheet: str, file_key: str, anchor: str) -> int:
    try:
        return book.find(sheet, anchor)[0]
    except LookupError as e:
        raise LayoutError(file_key, f"{sheet}!{anchor}") from e


def _regex_col(book: Book, sheet: str, file_key: str, pattern: str) -> tuple[int, int, str]:
    rx = re.compile(pattern, re.I)
    for r, row in enumerate(book.rows(sheet)[:15]):
        for c, v in enumerate(row):
            if isinstance(v, str) and rx.search(v.strip()):
                return r, c, v.strip()
    raise LayoutError(file_key, f"{sheet}!/{pattern}/")


def _forecast_start(book: Book, sheet: str, file_key: str) -> int:
    for row in book.rows(sheet):
        for v in row:
            if isinstance(v, str) and (m := _FORECAST_RE.search(v)):
                return int(m.group(1)[:4])
    raise LayoutError(file_key, f"{sheet}!'Forecast years from YYYY-YY' note")


def _year_rows(book: Book, sheet: str, after: int) -> list[tuple[int, str]]:
    out = []
    for r, row in enumerate(book.rows(sheet)):
        if r <= after or len(row) < 2:
            continue
        try:
            fy = normalise_fiscal_year(row[1])
        except ValueError:
            continue
        if int(fy[:4]) >= FIRST_YEAR:
            out.append((r, fy))
    return out


def _vintage(edition: str) -> str:
    m = re.search(r"([A-Z][a-z]{2})[a-z]* (\d{4})\s*$", edition)
    if not m:
        raise ValueError(f"cannot derive vintage from edition {edition!r}")
    return f"OBR databank {m.group(1)} {m.group(2)}"


def _num(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


def parse(path: Path, meta: FileMeta) -> list[Row]:
    book = open_book(path)
    key = meta.file.key
    vintage = _vintage(meta.file.edition)
    rows: list[Row] = []

    def emit(sheet: str, header_row: int, col: int, series: str, unit: str, fstart: int) -> None:
        for r, fy in _year_rows(book, sheet, header_row):
            raw = book.rows(sheet)[r]
            val = _num(raw[col]) if col < len(raw) else None
            if val is None:
                continue
            prov = Provenance(
                publisher=meta.source.publisher,
                dataset=meta.source.dataset,
                edition=meta.file.edition,
                publication_date=meta.file.publication_date,
                source_url=meta.url,
                landing_url=meta.file.landing_url,
                file_sha256=meta.sha256,
                sheet=sheet,
                cell_or_range=a1(r, col),
                api_query=None,
                licence=meta.source.licence,
                transformations=(),
                status="outturn" if int(fy[:4]) < fstart else "forecast",
                vintage=vintage,
                retrieved_at=meta.fetched_at,
            )
            rows.append(Row(series, fy, "fiscal_year", val, unit, "UK", prov))

    # Aggregates (£bn)
    hr = _header_row(book, AGG, key, "Total managed expenditure")
    fstart = _forecast_start(book, AGG, key)
    header = book.rows(AGG)[hr]
    found = {
        v.strip().casefold(): c
        for c, v in enumerate(header)
        if isinstance(v, str) and v.strip().casefold() in _AGG_COLS
    }
    for label, (sid, _t) in _AGG_COLS.items():
        if label not in found:
            raise LayoutError(key, f"{AGG}!{label}")
        emit(AGG, hr, found[label], sid, "gbp_bn", fstart)

    # Receipts by tax
    hr = _header_row(book, REC, key, _RECEIPT_ANCHOR)
    fstart = _forecast_start(book, REC, key)
    seen: set[str] = set()
    for c, v in enumerate(book.rows(REC)[hr]):
        if c < 2 or not isinstance(v, str) or not v.strip():
            continue
        if v.strip().casefold() in _RECEIPT_SKIP:
            continue
        slug = _slug(v)
        if slug in seen:
            raise LayoutError(key, f"{REC}!duplicate receipts header {v!r}")
        seen.add(slug)
        sid = f"obr.receipts.{slug}"
        SERIES[sid] = {
            "title": _FOOTNOTE_RE.sub("", v.strip()),
            "unit": "gbp_bn",
            "period_type": "fiscal_year",
            "monetary": True,
        }
        emit(REC, hr, c, sid, "gbp_bn", fstart)

    # Nominal GDP
    hr, col, _ = _regex_col(book, PCT, key, r"^Nominal GDP \(£ ?billion\)$")
    emit(PCT, hr, col, "obr.gdp_nominal", "gbp_bn", _forecast_start(book, PCT, key))

    # GDP deflator
    hr, col, _ = _regex_col(book, REAL, key, r"^GDP Deflator \(\d{4}-\d{2}=100\)$")
    emit(REAL, hr, col, "obr.gdp_deflator", "index", _forecast_start(book, REAL, key))

    # Real-terms TME as published by OBR (cross-check only, R5; never re-deflated)
    hr = _header_row(book, REAL, key, "Total managed expenditure")
    col = next(
        (
            c
            for c, v in enumerate(book.rows(REAL)[hr])
            if isinstance(v, str) and v.strip().casefold() == "total managed expenditure"
        ),
        None,
    )
    if col is None:
        raise LayoutError(key, f"{REAL}!Total managed expenditure")
    emit(REAL, hr, col, "obr.psf.tme_real", "gbp_bn", _forecast_start(book, REAL, key))

    if not rows:
        raise LayoutError(key, "no data rows")
    return rows
