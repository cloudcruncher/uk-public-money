"""HMRC tax and NICs receipts: annual receipts by tax (NS_Table.ods).

Sheets used: `Receipts_Annually` (Table 2, receipts by financial year, GBP million, cash basis).
Sheets skipped: `Cover_Sheet`, `Table_Notes` (text only), `Receipts_Monthly`, `Expenditure_Monthly`,
`Expenditure_Annually` (HMRC-administered payments, not receipts) and `Annual_Contribution_by_Tax`
(a different cut of the same receipts; not needed for the first slice).

Layout: the header row is found by the label "Table 2 HMRC Receipts by financial year" in column A.
Each column to its right is one tax; each row below is a financial year written "2024 to 2025".
Blank cells give no row. Only years from 2015-16 are emitted. Every row is outturn (cash received).
Registry verdict is USABLE; 2015-16 onward is confirmed by the year labels in column A.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..provenance import Provenance, Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError, normalise_fiscal_year

SHEET = "Receipts_Annually"
ANCHOR = "Table 2 HMRC Receipts by financial year"
FIRST_YEAR = "2015-16"
_YEAR_RE = re.compile(r"^\s*\d{4} to \d{4}\s*$")

# Header text -> series slug. Headers not listed fall back to a slug of the full header text.
_SLUGS = {
    "Total Paid Over": "total_paid_over",
    "Total HMRC Receipts": "total",
    "Income Tax": "income_tax",
    "Pay As You Earn Income Tax (included within Income Tax)": "income_tax_paye",
    "Self-Assessment Income Tax (included within Income Tax)": "income_tax_self_assessment",
    "National Insurance Contributions": "nics",
    "Value Added Tax": "vat",
    "Offshore (included within Corporation Tax)": "corporation_tax_offshore",
}

SERIES = {
    "hmrc_receipts.total": {
        "title": "Total HMRC receipts",
        "unit": "gbp_m",
        "period_type": "fiscal_year",
        "monetary": True,
        "description": "Table 2, Total HMRC Receipts. Cash basis. Other columns are "
        "hmrc_receipts.<tax> (one series per Receipts_Annually column).",
    },
}


def _slug(header: str) -> str:
    if header in _SLUGS:
        return _SLUGS[header]
    return re.sub(r"[^a-z0-9]+", "_", header.casefold()).strip("_")


def _num(v: object) -> float | None:
    return float(v) if isinstance(v, int | float) and not isinstance(v, bool) else None


def parse(path: Path, meta: FileMeta) -> list[Row]:
    book = open_book(path)
    try:
        hr, hc = book.find(SHEET, ANCHOR)
    except (KeyError, LookupError) as e:
        raise LayoutError(meta.file.key, f"{SHEET}!{ANCHOR}") from e
    grid = book.rows(SHEET)
    cols: list[tuple[int, str]] = []
    seen: set[str] = set()
    for c, h in enumerate(grid[hr]):
        if c <= hc or not isinstance(h, str) or not h.strip():
            continue
        slug = _slug(h.strip())
        if slug in seen:
            raise LayoutError(meta.file.key, f"{SHEET}: duplicate series for header {h!r}")
        seen.add(slug)
        cols.append((c, slug))
    if not any(s == "total" for _, s in cols):
        raise LayoutError(meta.file.key, f"{SHEET}!Total HMRC Receipts")

    out: list[Row] = []
    for r in range(hr + 1, len(grid)):
        label = grid[r][hc] if len(grid[r]) > hc else None
        if not (isinstance(label, str) and _YEAR_RE.match(label)):
            continue
        fy = normalise_fiscal_year(label.replace(" to ", "-"))
        if fy < FIRST_YEAR:
            continue
        for c, slug in cols:
            v = _num(grid[r][c]) if c < len(grid[r]) else None
            if v is None:
                continue
            prov = Provenance(
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
                status="outturn",
                vintage=meta.file.edition,
                retrieved_at=meta.fetched_at,
            )
            out.append(Row(f"hmrc_receipts.{slug}", fy, "fiscal_year", v, "gbp_m", "UK", prov))
    return out
