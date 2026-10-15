"""HM Treasury PESA (Public Expenditure Statistical Analyses).

Sheets used
-----------
* ``10.1`` (role ``cofog_10_1``), every edition: "Table 10.1 Total identifiable expenditure on
  services in England by sub-function", GBP million. Only the ten COFOG function total rows and the
  "Total Expenditure on Services in England" row are read; sub-function rows are skipped. The scope
  is **England**, not the UK, and the total is expenditure on services (TES), not TME.
* ``4_1`` (role ``aggregates_4_1``), PESA 2026: "Table 4.1 Public expenditure aggregates", GBP
  billion nominal, UK. Current expenditure, depreciation, net investment and TME are read. The
  real-terms and per-cent-of-GDP columns are skipped (derivable with ``ukpm.units``).

Skipped: every other sheet (10.2 to 10.10, Metadata, 2.5, 4_2 to 4_4) and every other chapter file.

Layout rules: cells are found by label, never by fixed address. The year columns come from the
header cells ("2015-16\\noutturn"). An expected label that is missing or duplicated raises
``LayoutError``.
Cells holding ``-``, ``..``, ``x`` or nothing give no row. Editions overlap and are restated, so
``combine`` keeps the newest edition for each (series, year); the vintage records which one.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..provenance import Provenance, Row
from ..sheets import Book, a1, open_book
from . import FileMeta, LayoutError, normalise_fiscal_year

SOURCE = "pesa"
COFOG_SHEET = "10.1"
AGG_SHEET = "4_1"
FIRST_YEAR = "2015-16"  # registry coverage start; Table 4.1 itself runs from 1985-86
_BLANKS = frozenset({"", "-", "..", "x", "X"})
_HEADER_RE = re.compile(r"^\s*(\d{4}-\d{2})\s+(\w+)\s*$")
_OUTTURN_UPTO_RE = re.compile(r"Outturn data in this table up to (\d{4}-\d{2})")

# Label in Table 10.1 -> series id suffix.
COFOG_TOTALS: dict[str, str] = {
    "Total general public services": "general_public_services",
    "Total defence": "defence",
    "Total public order and safety": "public_order_safety",
    "Total economic affairs": "economic_affairs",
    "Total environment protection": "environment_protection",
    "Total housing and community amenities": "housing_community_amenities",
    "Total health": "health",
    "Total recreation, culture and religion": "recreation_culture_religion",
    "Total education": "education",
    "Total social protection": "social_protection",
    "Total Expenditure on Services in England": "total_services",
}
_COFOG_TITLES = {
    "general_public_services": "General public services",
    "defence": "Defence",
    "public_order_safety": "Public order and safety",
    "economic_affairs": "Economic affairs",
    "environment_protection": "Environment protection",
    "housing_community_amenities": "Housing and community amenities",
    "health": "Health",
    "recreation_culture_religion": "Recreation, culture and religion",
    "education": "Education",
    "social_protection": "Social protection",
    "total_services": "Total expenditure on services",
}
# Group header text (prefix) in Table 4.1 -> series id.
AGGREGATES: dict[str, str] = {
    "Public sector current expenditure": "pesa.current_expenditure",
    "Depreciation": "pesa.depreciation",
    "Public sector net investment": "pesa.net_investment",
    "Total Managed Expenditure": "pesa.tme",
}

SERIES: dict[str, dict] = {
    **{
        f"pesa.cofog.{k}": {
            "title": f"{_COFOG_TITLES[k]}: identifiable expenditure on services in England",
            "unit": "gbp_m",
            "period_type": "fiscal_year",
            "monetary": True,
            "description": (
                f"PESA Table 10.1 row 'Total {_COFOG_TITLES[k].lower()}' (England only, nominal "
                "GBP million, outturn). Not UK-wide and not TME."
                if k != "total_services"
                else "PESA Table 10.1 'Total Expenditure on Services in England' (England only, "
                "nominal GBP million). This is TES, not TME."
            ),
        }
        for k in COFOG_TOTALS.values()
    },
    "pesa.tme": {
        "title": "Total Managed Expenditure (UK)",
        "unit": "gbp_bn",
        "period_type": "fiscal_year",
        "monetary": True,
        "description": "PESA Table 4.1 TME, nominal GBP billion; years after the outturn cut-off "
        "stated in the sheet are forecast.",
    },
    "pesa.current_expenditure": {
        "title": "Public sector current expenditure (UK)",
        "unit": "gbp_bn",
        "period_type": "fiscal_year",
        "monetary": True,
        "description": "PESA Table 4.1, nominal GBP billion.",
    },
    "pesa.depreciation": {
        "title": "Depreciation (UK)",
        "unit": "gbp_bn",
        "period_type": "fiscal_year",
        "monetary": True,
        "description": "PESA Table 4.1, nominal GBP billion.",
    },
    "pesa.net_investment": {
        "title": "Public sector net investment (UK)",
        "unit": "gbp_bn",
        "period_type": "fiscal_year",
        "monetary": True,
        "description": "PESA Table 4.1, nominal GBP billion.",
    },
}


def _num(v: object, key: str, sheet: str, addr: str) -> float | None:
    if isinstance(v, bool):
        raise LayoutError(key, f"{sheet}!{addr}: boolean in a value cell")
    if isinstance(v, (int, float)):
        return float(v)
    if v is None or (isinstance(v, str) and v.strip() in _BLANKS):
        return None
    raise LayoutError(key, f"{sheet}!{addr}: non-numeric value {v!r}")


def _prov(meta: FileMeta, sheet: str, cell: str, status: str) -> Provenance:
    return Provenance(
        publisher=meta.source.publisher,
        dataset=meta.source.dataset,
        edition=meta.file.edition,
        publication_date=meta.file.publication_date,
        source_url=meta.file.file_url or meta.url,
        landing_url=meta.file.landing_url,
        file_sha256=meta.sha256,
        sheet=sheet,
        cell_or_range=cell,
        api_query=None,
        licence=meta.source.licence,
        transformations=(),
        status=status,
        vintage=meta.file.edition,
        retrieved_at=meta.fetched_at,
    )


def _sheet(book: Book, name: str, key: str) -> list[list]:
    if name not in book.sheet_names:
        raise LayoutError(key, f"sheet {name!r}")
    return book.rows(name)


def _parse_cofog(book: Book, meta: FileMeta) -> list[Row]:
    key = meta.file.key
    rows = _sheet(book, COFOG_SHEET, key)
    if not any(str(c).strip() == "£ million" for r in rows[:6] for c in r):
        raise LayoutError(key, f"{COFOG_SHEET}: unit '£ million'")
    cols: dict[int, tuple[str, str]] = {}  # column -> (fiscal year, status)
    out: list[Row] = []
    seen: set[str] = set()
    for ri, row in enumerate(rows):
        head = {
            ci: m
            for ci, c in enumerate(row[1:], 1)
            if (m := _HEADER_RE.match(str(c).replace("\n", " ")))
        }
        if head and not str(row[0]).strip():
            cols = {
                ci: (
                    normalise_fiscal_year(m.group(1)),
                    "outturn" if m.group(2) == "outturn" else "forecast",
                )
                for ci, m in head.items()
            }
            continue
        label = str(row[0]).strip()
        if label not in COFOG_TOTALS:
            continue
        if label in seen:
            raise LayoutError(key, f"{COFOG_SHEET}: duplicate label {label!r}")
        seen.add(label)
        if not cols:
            raise LayoutError(key, f"{COFOG_SHEET}: year header above {label!r}")
        for ci, (fy, status) in cols.items():
            cell = a1(ri, ci)
            val = _num(row[ci] if ci < len(row) else None, key, COFOG_SHEET, cell)
            if val is None:
                continue
            out.append(
                Row(
                    f"pesa.cofog.{COFOG_TOTALS[label]}",
                    fy,
                    "fiscal_year",
                    val,
                    "gbp_m",
                    "England",
                    _prov(meta, COFOG_SHEET, cell, status),
                )
            )
    for label in COFOG_TOTALS:
        if label not in seen:
            raise LayoutError(key, f"{COFOG_SHEET}: label {label!r}")
    return out


def _parse_aggregates(book: Book, meta: FileMeta) -> list[Row]:
    key = meta.file.key
    rows = _sheet(book, AGG_SHEET, key)
    cutoff = None
    for r in rows[:8]:
        for c in r:
            if m := _OUTTURN_UPTO_RE.search(str(c)):
                cutoff = normalise_fiscal_year(m.group(1))
    if cutoff is None:
        raise LayoutError(key, f"{AGG_SHEET}: 'Outturn data in this table up to <year>'")
    # Group header row: the row holding the TME group label; the nominal column is first in a group.
    group_row = next(
        (
            i
            for i, r in enumerate(rows[:10])
            if any(str(c).strip().casefold().startswith("total managed expenditure") for c in r)
        ),
        None,
    )
    if group_row is None:
        raise LayoutError(key, f"{AGG_SHEET}: 'Total Managed Expenditure' header")
    unit_row = rows[group_row + 1]
    group_cols: dict[str, int] = {}
    for sid_label in AGGREGATES:
        for ci, c in enumerate(rows[group_row]):
            if str(c).strip().casefold().startswith(sid_label.casefold()):
                group_cols[sid_label] = ci
                break
        else:
            raise LayoutError(key, f"{AGG_SHEET}: header {sid_label!r}")
        u = str(unit_row[group_cols[sid_label]]).replace("\n", " ")
        if not (u.startswith("Nominal") and "£ billion" in u):
            raise LayoutError(key, f"{AGG_SHEET}: {sid_label!r} column is not 'Nominal £ billion'")
    out: list[Row] = []
    for ri in range(group_row + 2, len(rows)):
        try:
            fy = normalise_fiscal_year(rows[ri][1])
        except ValueError:
            continue
        if fy < FIRST_YEAR:
            continue
        status = "outturn" if fy <= cutoff else "forecast"
        for lab, ci in group_cols.items():
            cell = a1(ri, ci)
            val = _num(rows[ri][ci], key, AGG_SHEET, cell)
            if val is None:
                continue
            out.append(
                Row(
                    AGGREGATES[lab],
                    fy,
                    "fiscal_year",
                    val,
                    "gbp_bn",
                    "UK",
                    _prov(meta, AGG_SHEET, cell, status),
                )
            )
    if not out:
        raise LayoutError(key, f"{AGG_SHEET}: no fiscal-year rows")
    return out


def parse(path: Path, meta: FileMeta) -> list[Row]:
    book = open_book(path)
    role = meta.file.role
    if role == "cofog_10_1":
        return _parse_cofog(book, meta)
    if role == "aggregates_4_1":
        return _parse_aggregates(book, meta)
    raise LayoutError(meta.file.key, f"unsupported role {role!r}")


def combine(rows: list[Row]) -> list[Row]:
    """Keep the newest edition for each (series, fiscal year); order by series then year."""
    best: dict[tuple[str, str], Row] = {}
    for r in rows:
        k = (r.series_id, r.fiscal_year)
        if k not in best or r.prov.publication_date > best[k].prov.publication_date:
            best[k] = r
    return [best[k] for k in sorted(best)]
