"""Home Office Annual Report and Accounts 2025-26 (HC 440, PDF): income lines.

Deterministic extraction: fixed PDF pages, ``pypdf`` text, regex on exact row labels, strict
numeric parsing, hard layout assertions. No OCR, no model. Every page is checked for its title,
the printed page number, the unit (GBP thousand) and the year header (2025-26 then 2024-25)
before any number is read; every wanted row must match exactly once or ``LayoutError`` is raised.

Pages (1-based PDF page, printed page in brackets):

* 283 (278)  Note 3 Income: visa and immigration income, Immigration Health Surcharge (retained).
* 284 (279)  Note 3 continued: Immigration Health Surcharge payable to the Consolidated Fund.
* 228 (223)  Fees and Charges table: Customer Service (UKVI), in-country and overseas.
* 351 (346)  Trust Statement, Statement of Revenue, Other Income and Expenditure.
* 339 (334)  Trust Statement "Our Performance" text, used only to cross-check the totals above
  (it quotes them in GBP million to one decimal place).

All amounts are GBP thousand in the PDF; each is scaled to GBP million by a recorded
transformation (the build scales on to GBP billion). A dash ("–") in a money column is the
accounts' way of writing nil; it is read as 0 and the transformation list says so. Note 3 values
come from the *Departmental Group* column; the parser checks they equal the *Core Department and
Agencies* column for these rows.

Sanity checks (LayoutError on failure): income - full cost = surplus and the published recovery
percentage, for UKVI; the Trust Statement parts add up to their totals (penalty types to total
penalties; ISC + penalties + other income to total revenue); the Trust Statement thousands agree
with the GBP million quoted in the narrative; UKVI fee income agrees with Note 3 visa income to
within 0.1 per cent (they are different cuts of the same fee income).
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from .. import units
from ..provenance import Row, Transformation
from . import FileMeta, LayoutError
from ._w2 import prov

YEARS = ("2025-26", "2024-25")
NOTE3, NOTE3B, FEES, TRUST, TRUST_TEXT = 283, 284, 228, 351, 339
PRINTED = {NOTE3: 278, NOTE3B: 279, FEES: 223, TRUST: 346, TRUST_TEXT: 334}

_NUM = r"(?:\(\d{1,3}(?:,\d{3})*\)|\d{1,3}(?:,\d{3})*|[–-])(?![\d,.%])"
_PCT = r"\d{1,3}%"
_DEFAULT = "accounts figure, GBP thousand, published as a whole number"

# slug -> (title, what it is)
_DEFS = {
    "visa_income": (
        "Visa and immigration income",
        "fees for visas and other immigration applications, kept by the Home Office (Note 3)",
    ),
    "ihs_retained": (
        "Immigration Health Surcharge, retained",
        "the part of the surcharge the Home Office keeps in its accounts before passing it on "
        "to health services (Note 3, other operating income)",
    ),
    "ihs_payable_consolidated_fund": (
        "Immigration Health Surcharge, payable to the Consolidated Fund",
        "surcharge income that goes straight to the government's main account (Note 3); "
        "nil in 2025-26 (the accounts show a dash)",
    ),
    "ukvi_fee_income": (
        "UK Visas and Immigration fee income (fees and charges table)",
        "income of the Customer Service (UKVI) segment, in-country and overseas",
    ),
    "ukvi_full_cost": (
        "UK Visas and Immigration full cost (fees and charges table)",
        "the full cost of the same segment as measured for Treasury fees-and-charges rules",
    ),
    "ukvi_surplus": (
        "UK Visas and Immigration surplus (fees and charges table)",
        "fee income minus full cost for the same segment",
    ),
    "immigration_skills_charge": (
        "Immigration Skills Charge",
        "charge paid by employers who sponsor skilled workers from abroad, paid into the "
        "Consolidated Fund (Trust Statement)",
    ),
    "civil_penalties": (
        "Civil penalties (Trust Statement)",
        "fines on illegal-worker employers, hauliers, carriers and landlords, paid into the "
        "Consolidated Fund (Trust Statement, total fines and penalties)",
    ),
    "trust_total_revenue": (
        "Trust Statement gross revenue and other income",
        "all revenue collected for the Consolidated Fund by the Home Office before costs of "
        "collection and credit losses: Immigration Skills Charge, civil penalties and duties and "
        "fees (mainly passport consular fees)",
    ),
}
_CAVEAT = (
    "Home Office Annual Report and Accounts 2025-26, audited outturn, financial year (April to "
    "March), GBP thousand in the PDF. The 2024-25 figures are comparatives printed in the 2025-26 "
    "report and may be restated or reclassified there (the Trust Statement says 2024-25 is "
    "'Reclassified' because of a change in discounts policy)."
)
SERIES = {
    f"home_office_ara.{slug}": {
        "title": f"Home Office: {title}",
        "unit": "gbp_m",
        "period_type": "fiscal_year",
        "monetary": True,
        "description": f"{title[0].upper()}{title[1:]}: {what}. {_CAVEAT}",
    }
    for slug, (title, what) in _DEFS.items()
}


def _squash(s: str) -> str:
    return re.sub(r"\s+", "", s).replace("’", "'").lower()


def _lab(label: str) -> str:
    """Regex for a label that tolerates any line breaks or stray spaces between characters
    (the PDF text has 'Consolidate d' and '20 25')."""
    return r"\s*".join(re.escape(c) for c in label if not c.isspace())


def _value(tok: str) -> tuple[float, bool]:
    """'3,574,088' -> 3574088.0; '(201,622)' -> -201622.0; a dash -> (0.0, True) for nil."""
    if tok in ("–", "-"):
        return 0.0, True
    neg = tok.startswith("(")
    v = float(tok.strip("()").replace(",", ""))
    return (-v if neg else v), False


class _Doc:
    """Page text with the layout checks. Everything raises LayoutError(file_key, anchor)."""

    def __init__(self, path: Path, key: str):
        from pypdf import PdfReader

        self.key = key
        try:
            self._reader = PdfReader(str(path))
            self._n = len(self._reader.pages)
        except Exception as e:  # pypdf raises many types on bad input
            raise LayoutError(key, f"readable PDF ({type(e).__name__})") from e
        self._cache: dict[int, str] = {}

    def fail(self, page: int, what: str) -> LayoutError:
        return LayoutError(self.key, f"PDF p{page}: {what}")

    def page(self, n: int) -> str:
        if n not in self._cache:
            if n > self._n:
                raise self.fail(n, f"page exists (file has {self._n} pages)")
            try:
                self._cache[n] = self._reader.pages[n - 1].extract_text() or ""
            except Exception as e:  # pypdf raises many types on malformed content
                raise self.fail(n, f"extractable text ({type(e).__name__})") from e
        return self._cache[n]

    def check(self, n: int, *, title: str, headers: tuple[str, ...], years: bool = True) -> str:
        text = self.page(n)
        sq = _squash(text)
        if _squash(title) not in sq:
            raise self.fail(n, f"title {title!r}")
        if not re.search(rf"(?m)^\s*{PRINTED[n]}\s*$", text):
            raise self.fail(n, f"printed page number {PRINTED[n]}")
        if years and not re.search(r"2025-26\s*2024-25", text):
            raise self.fail(n, "year header '2025-26' then '2024-25'")
        for h in headers:
            if _squash(h) not in sq:
                raise self.fail(n, f"column header {h!r}")
        return text

    def row(self, n: int, text: str, label: str, tail: str) -> re.Match[str]:
        """The one match of ``label`` followed by ``tail`` (a regex); not found or twice raises."""
        ms = list(re.finditer(rf"(?<![A-Za-z]){_lab(label)}\s+{tail}", text))
        if len(ms) != 1:
            raise self.fail(n, f"row {label!r} (matched {len(ms)} times, need exactly 1)")
        return ms[0]


def _close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def parse(path: Path, meta: FileMeta) -> list[Row]:
    key = meta.file.key
    doc = _Doc(path, key)
    edition = meta.file.edition
    # (slug, year) -> (value in GBP thousand, pdf page, row label, column note, nil)
    got: dict[tuple[str, str], tuple[float, int, str, str, bool]] = {}

    # ---- Note 3 (p283, p284): Core Dept 2025-26, Group 2025-26, Core 2024-25, Group 2024-25
    note_hdr = ("Core Department and Agencies", "Departmental Group", "£'000")
    t283 = doc.check(NOTE3, title="3. Income", headers=note_hdr)
    t284 = doc.check(NOTE3B, title="payable to Consolidated Fund", headers=note_hdr)
    four = rf"({_NUM})\s+({_NUM})\s+({_NUM})\s+({_NUM})"
    for page, text, label, slug in (
        (NOTE3, t283, "Visa and immigration income", "visa_income"),
        (NOTE3, t283, "Immigration Health Surcharge", "ihs_retained"),
        (NOTE3B, t284, "Immigration Health Surcharge", "ihs_payable_consolidated_fund"),
    ):
        m = doc.row(page, text, label, four)
        vals = [_value(g) for g in m.groups()]
        for (core, _), (grp, nil), yr in (
            (vals[0], vals[1], YEARS[0]),
            (vals[2], vals[3], YEARS[1]),
        ):
            if core != grp:
                raise doc.fail(page, f"row {label!r} {yr}: Core Department != Departmental Group")
            got[(slug, yr)] = (grp, page, label, f"{yr}, Departmental Group", nil)
    # the retained IHS row must come before the 'payable' heading on the first page only
    if not re.search(
        rf"{_lab('Other operating income')}\s+{_lab('Immigration Health Surcharge')}", t283
    ):
        raise doc.fail(NOTE3, "Immigration Health Surcharge under 'Other operating income'")
    if not re.search(
        rf"{_lab('Other operating income')}\s*[–-]\s*{_lab('payable to Consolidated Fund')}", t284
    ):
        raise doc.fail(NOTE3B, "'Other operating income - payable to Consolidated Fund' heading")

    # ---- Fees and Charges (p228)
    t228 = doc.check(
        FEES,
        title="Fee recovery",
        headers=("Income", "Full Cost", "Surplus/", "Fee recovery actual", "Fee recovery target",
                 "£'000"),
    )  # fmt: skip
    seg = "Customer Service (UKVI) In-Country and Overseas"
    fm = doc.row(
        FEES, t228, seg,
        rf"({_NUM})\s+({_NUM})\s+({_NUM})\s+({_PCT})\s+({_PCT})\s+"
        rf"({_NUM})\s+({_NUM})\s+({_NUM})\s+({_PCT})\s+({_PCT})",
    )  # fmt: skip
    g = fm.groups()
    fee_cols = {YEARS[0]: g[0:5], YEARS[1]: g[5:10]}
    for yr, (inc, cost, sur, rec, _target) in fee_cols.items():
        i, c, s = _value(inc)[0], _value(cost)[0], _value(sur)[0]
        if c <= 0:
            raise doc.fail(FEES, f"{yr}: full cost is not positive")
        if i - c != s:
            raise doc.fail(FEES, f"{yr}: income - full cost != surplus")
        if not _close(100 * i / c, float(rec.rstrip("%")), 0.5):
            raise doc.fail(FEES, f"{yr}: fee recovery % does not equal income / full cost")
        for slug, v in (("ukvi_fee_income", i), ("ukvi_full_cost", c), ("ukvi_surplus", s)):
            col = {"ukvi_fee_income": "Income", "ukvi_full_cost": "Full Cost",
                   "ukvi_surplus": "Surplus/(deficit)"}[slug]  # fmt: skip
            got[(slug, yr)] = (v, FEES, seg, f"{yr}, {col}", False)
    for yr in YEARS:
        a, b = got[("ukvi_fee_income", yr)][0], got[("visa_income", yr)][0]
        if not _close(a, b, 0.001 * b):
            raise doc.fail(FEES, f"{yr}: UKVI fee income differs from Note 3 visa income by >0.1%")

    # ---- Trust Statement (p351)
    t351 = doc.check(
        TRUST,
        title="Statement of Revenue, Other Income and Expenditure",
        headers=("Levies and Similar Revenue", "£'000"),
    )
    if not re.search(r"2024-25\s*\(Reclassified\)", t351):
        raise doc.fail(TRUST, "2024-25 column marked '(Reclassified)'")
    ts: dict[str, tuple[float, float, str]] = {}
    for label, with_note in (
        ("Immigration Skills Charge", True),
        ("Illegal Workers Civil Penalties", True),
        ("Hauliers Civil Penalties", True),
        ("Carriers Civil Penalties", True),
        ("Landlords Civil Penalties", True),
        ("Total Fines and Penalties", False),
        ("Duties and Fees", True),
        ("Total Revenue and Other Income", False),
    ):
        tail = rf"(?:\d\.\d\s+)?({_NUM})\s+({_NUM})" if with_note else rf"({_NUM})\s+({_NUM})"
        m = doc.row(TRUST, t351, label, tail)
        ts[label] = (_value(m.group(1))[0], _value(m.group(2))[0], label)
    for idx, yr in enumerate(YEARS):
        parts = [ts[k][idx] for k in ts if k.endswith("Civil Penalties")]
        if sum(parts) != ts["Total Fines and Penalties"][idx]:
            raise doc.fail(TRUST, f"{yr}: civil penalty types do not add to total fines")
        total = (
            ts["Immigration Skills Charge"][idx]
            + ts["Total Fines and Penalties"][idx]
            + ts["Duties and Fees"][idx]
        )
        if total != ts["Total Revenue and Other Income"][idx]:
            raise doc.fail(TRUST, f"{yr}: ISC + penalties + duties and fees != total revenue")
        for slug, label in (
            ("immigration_skills_charge", "Immigration Skills Charge"),
            ("civil_penalties", "Total Fines and Penalties"),
            ("trust_total_revenue", "Total Revenue and Other Income"),
        ):
            got[(slug, yr)] = (ts[label][idx], TRUST, label, f"{yr}", False)

    # ---- cross-check against the narrative in GBP million (p339)
    t339 = doc.check(
        TRUST_TEXT, title="Our Performance", headers=("Consolidated Fund",), years=False
    )
    flat = re.sub(r"(?<=\d)\s+(?=\d)", "", re.sub(r"\s+", " ", t339))  # '2024-2 5' -> '2024-25'
    for slug, yr, pattern in (
        ("trust_total_revenue", YEARS[0], r"\(restated\) to £(\d+\.\d) million in 2025-26"),
        ("trust_total_revenue", YEARS[1], r"from £(\d+\.\d) million in 2024-25 \(restated\)"),
        (
            "immigration_skills_charge",
            YEARS[1],
            r"Immigration Skills Charge, which increased from £(\d+\.\d) million to",
        ),
        (
            "immigration_skills_charge",
            YEARS[0],
            r"Immigration Skills Charge, which increased from £\d+\.\d million to £(\d+\.\d)",
        ),
        ("civil_penalties", YEARS[1], r"reduced from £(\d+\.\d) million \(restated\)"),
        (
            "civil_penalties",
            YEARS[0],
            r"reduced from £\d+\.\d million \(restated\) to £(\d+\.\d) million",
        ),
    ):
        ms = re.findall(pattern, flat)
        if len(ms) != 1:
            raise doc.fail(TRUST_TEXT, f"narrative figure for {slug} {yr}")
        if not _close(got[(slug, yr)][0] / 1000, float(ms[0]), 0.051):
            raise doc.fail(TRUST_TEXT, f"narrative {ms[0]}m disagrees with table for {slug} {yr}")

    # ---- build rows
    out: list[Row] = []
    for (slug, yr), (v, page, label, col, nil) in sorted(got.items()):
        cell = f"row '{label}', column {col}"
        steps = [
            Transformation(
                "pdf_text",
                f"pypdf text of PDF page {page}; row label matched exactly once; "
                f"thousands separators removed; {_DEFAULT}",
            )
        ]
        if nil:
            steps.append(
                Transformation("nil", "the accounts print a dash for this cell, read as nil (0)")
            )
        p = prov(meta, f"PDF p{page} (printed p{PRINTED[page]})", cell, "outturn", edition)
        p = replace(p, transformations=tuple(steps))
        row = Row(f"home_office_ara.{slug}", yr, "fiscal_year", v, "gbp_k", "UK", p)
        out.append(units.scale(row, 0.001, "GBP thousand to GBP million (x 0.001)", "gbp_m"))
    return out
