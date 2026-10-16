"""Cabinet Office spend over GBP 25,000: one monthly CSV per file.

Aggregates only. For each file (month = `files[].edition`, `YYYY-MM`) the parser emits, in
pounds as published (VAT basis unverified): - `cabinet_office_spend.total.<YYYY_MM>`
sum of Amount - `cabinet_office_spend.transactions.<YYYY_MM>`           number of rows summed
(unit `count`) - `cabinet_office_spend.expense_type.<YYYY_MM>.<slug>`    sum by Expense Type -
`cabinet_office_spend.supplier.<YYYY_MM>.<slug>`        sum by Supplier (work/parsed only; the
build decides what is published) Never emitted: Ref, Transaction number, Date (day), Expense
Area, or any row-level amount.

Reading: bytes decode as utf-8-sig, then cp1252 (most files are cp1252); anything else raises
LayoutError. The header row is found by text and columns are found by header name. Amounts are
comma-thousands strings, summed as Decimal (so totals match the publisher to the penny); `(x)`
and a leading `-` are negative; an unparseable Amount raises LayoutError with the row number.

Nothing is dropped silently. Rows with every cell blank are skipped as padding. Rows with no
Date, Expense Type, Expense Area, Supplier, Transaction number or Amount (only Ref/Family/Entity
filled, as in the May 2026 file at row 149) are skipped as placeholders. Both kinds are counted
and listed by `scan(...).skipped`; `skipped_rows(path)` is the convenience call. Spreadsheet row
= record number (header is row 1), so the summed range is `<col>2:<col><last counted row>`;
skipped rows inside it hold no amount and do not change the sum.

Provenance: sheet "CSV"; `cell_or_range` is the Amount column range, plus a filter for
subtotals, e.g. `I2:I500 where E="Professional Services"` (embedded `"` doubled).
`label_of(row)` returns the filter text. Fiscal year is the April-March year containing the
month."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..provenance import Provenance, Row
from ..sheets import a1
from . import FileMeta, LayoutError

HEADERS = (
    "Ref",
    "Departmental Family",
    "Entity",
    "Date",
    "Expense Type",
    "Expense Area",
    "Supplier",
    "Transaction number",
    "Amount",
)
PREFIX = "cabinet_office_spend"
_MONTHS = (
    "January February March April May June July August September October November December"
).split()
_EDITION = re.compile(r"^(\d{4})-(\d{2})$")
_FILTER = re.compile(r' where [A-Z]+="((?:[^"]|"")*)"$')
_CONTENT = ("Date", "Expense Type", "Expense Area", "Supplier", "Transaction number", "Amount")

_DESC = (
    "Cabinet Office (core) spend over GBP 25,000, pounds as published; the files do not say "
    "whether VAT is included. Monthly aggregate of the Amount column."
)
SERIES = {
    f"{PREFIX}.total": {
        "title": "Cabinet Office spend over 25,000 pounds, monthly total",
        "unit": "gbp",
        "period_type": "month",
        "monetary": True,
        "description": _DESC + " Series ids end in the month, YYYY_MM.",
    },
    f"{PREFIX}.transactions": {
        "title": "Cabinet Office spend over 25,000 pounds, transactions in the month",
        "unit": "count",
        "period_type": "month",
        "monetary": False,
        "description": "Number of rows summed in the month's file. Ids end in YYYY_MM.",
    },
    f"{PREFIX}.expense_type": {
        "title": "Cabinet Office spend over 25,000 pounds, by expense type",
        "unit": "gbp",
        "period_type": "month",
        "monetary": True,
        "description": _DESC + " Ids are expense_type.<YYYY_MM>.<slug>.",
    },
    f"{PREFIX}.supplier": {
        "title": "Cabinet Office spend over 25,000 pounds, by supplier",
        "unit": "gbp",
        "period_type": "month",
        "monetary": True,
        "description": _DESC + " Ids are supplier.<YYYY_MM>.<slug>. Parsed only; the build "
        "publishes a capped, filtered subset.",
    },
}


@dataclass(frozen=True)
class Skipped:
    row: int  # spreadsheet row number (header is row 1)
    reason: str  # "blank" or "placeholder"


@dataclass(frozen=True)
class Scan:
    rows: list[Row]
    skipped: list[Skipped]
    transactions: int


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_") or "unnamed"


def _decode(path: Path, key: str) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise LayoutError(key, "text encoding (neither utf-8 nor cp1252)")


def _amount(text: str, row: int, key: str) -> Decimal:
    t = text.strip().replace("£", "").replace(",", "").replace(" ", "")
    neg = t.startswith("(") and t.endswith(")")
    if neg:
        t = t[1:-1]
    try:
        v = Decimal(t)
    except InvalidOperation:
        raise LayoutError(key, f"Amount at row {row} is not a number: {text!r}") from None
    if not v.is_finite():
        raise LayoutError(key, f"Amount at row {row} is not a number: {text!r}")
    return -v if neg else v


def label_of(row: Row) -> str | None:
    """The quoted filter text of a subtotal row's range, or None for a total/transactions row."""
    m = _FILTER.search(row.prov.cell_or_range or "")
    return m.group(1).replace('""', '"') if m else None


def _filter(col: str, text: str) -> str:
    return f' where {col}="{text.replace(chr(34), chr(34) * 2)}"'


def scan(path: Path, meta: FileMeta) -> Scan:
    key = meta.file.key
    m = _EDITION.match(meta.file.edition)
    if not m or not 1 <= int(m.group(2)) <= 12:
        raise LayoutError(key, f"edition {meta.file.edition!r} is not YYYY-MM")
    year, month = int(m.group(1)), int(m.group(2))
    start = year if month >= 4 else year - 1
    fy = f"{start}-{(start + 1) % 100:02d}"
    mm = f"{year}_{month:02d}"
    vintage = f"Cabinet Office spend over £25,000, {_MONTHS[month - 1]} {year}"

    records = list(csv.reader(io.StringIO(_decode(path, key), newline="")))
    norm = [tuple(c.strip().casefold() for c in r) for r in records]
    want = tuple(h.casefold() for h in HEADERS)
    hdr = next((i for i, r in enumerate(norm) if set(want) <= set(r)), None)
    if hdr is None:
        raise LayoutError(key, "header row: " + ", ".join(HEADERS))
    idx = {h: norm[hdr].index(h.casefold()) for h in HEADERS}
    col = {h: a1(0, idx[h])[:-1] for h in HEADERS}

    counted: list[tuple[int, str, str, Decimal]] = []  # row, expense type, supplier, amount
    skipped: list[Skipped] = []
    for i in range(hdr + 1, len(records)):
        r = records[i]
        rownum = i + 1
        if not any(c.strip() for c in r):
            skipped.append(Skipped(rownum, "blank"))
            continue

        def cell(h: str, r: list[str] = r) -> str:
            j = idx[h]
            return r[j].strip() if j < len(r) else ""

        if not any(cell(h) for h in _CONTENT):
            skipped.append(Skipped(rownum, "placeholder"))
            continue
        counted.append(
            (rownum, cell("Expense Type"), cell("Supplier"), _amount(cell("Amount"), rownum, key))
        )
    if not counted:
        raise LayoutError(key, "no data rows")

    last = counted[-1][0]
    first = hdr + 2
    amt = f"{col['Amount']}{first}:{col['Amount']}{last}"

    def prov(rng: str, status: str = "outturn") -> Provenance:
        return Provenance(
            publisher=meta.source.publisher,
            dataset=meta.source.dataset,
            edition=meta.file.edition,
            publication_date=meta.file.publication_date,
            source_url=meta.file.file_url,
            landing_url=meta.file.landing_url,
            file_sha256=meta.sha256,
            sheet="CSV",
            cell_or_range=rng,
            api_query=None,
            licence=meta.source.licence,
            transformations=(),
            status=status,
            vintage=vintage,
            retrieved_at=meta.fetched_at,
        )

    def row(sid: str, value: Decimal | int, unit: str, rng: str) -> Row:
        return Row(sid, fy, "month", float(value), unit, "UK", prov(rng))

    total = sum((c[3] for c in counted), Decimal(0))
    by_type: dict[str, Decimal] = {}
    by_sup: dict[str, Decimal] = {}
    for _n, et, sup, a in counted:
        by_type[et] = by_type.get(et, Decimal(0)) + a
        by_sup[sup] = by_sup.get(sup, Decimal(0)) + a
    if abs(sum(by_type.values(), Decimal(0)) - total) > Decimal("0.01"):
        raise LayoutError(key, "expense-type subtotals do not add up to the total")

    out = [
        row(f"{PREFIX}.total.{mm}", total, "gbp", amt),
        row(
            f"{PREFIX}.transactions.{mm}",
            len(counted),
            "count",
            f"{col['Ref']}{first}:{col['Ref']}{last}",
        ),
    ]
    for kind, header, groups in (
        ("expense_type", "Expense Type", by_type),
        ("supplier", "Supplier", by_sup),
    ):
        used: set[str] = set()
        for name, v in groups.items():
            base = _slug(name)
            slug, n = base, 1
            while slug in used:
                n += 1
                slug = f"{base}_{n}"
            used.add(slug)
            out.append(
                row(f"{PREFIX}.{kind}.{mm}.{slug}", v, "gbp", amt + _filter(col[header], name))
            )
    return Scan(out, skipped, len(counted))


def parse(path: Path, meta: FileMeta) -> list[Row]:
    return scan(path, meta).rows


def skipped_rows(path: Path, meta: FileMeta) -> list[Skipped]:
    return scan(path, meta).skipped
