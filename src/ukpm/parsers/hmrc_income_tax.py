"""HMRC Income Tax statistics: liabilities by income range and number of payers.

The current Table 2.5 edition covers tax years 2023-24 to 2026-27 (2023-24 is outturn from the
Survey of Personal Incomes; 2024-25 onward are provisional projections, emitted as status
"forecast"). The 2015-16 to 2022-23 years come from the historic Table 2.5a (`hmrc_table_2_5a`,
sheets `2_5a_IT_liability_by_IT_YY-YY`, same columns, header label has an "in £" suffix; its
1999-00 to 2014-15 sheets are deliberately not read). Values stored as text (e.g. "0",
"[no estimate]") give no row.
Table 2.1 covers payer numbers by marginal rate from 2015-16 (emitted from 2015-16 onward).

Files and sheets used:
- `hmrc_table_2_5` (Table 2.5, sheets `2_5_IT_Liabilities_YYYY-YY`): per income band,
  total number of payers (thousand persons) and total liability (GBP million); on the "All Ranges"
  row, total liability, total income and liability by marginal rate.
- `hmrc_table_2_1` (`2_1_IT_payers_by_demographic`): all payers and payers by marginal rate
  (thousand persons). Sex and age columns are skipped (not needed for "who pays").
Sheets skipped: `Contents`, `2_5_Footnotes`, `2_1_Footnotes` (text only).
Skipped columns in 2.5: average rate and average amount (derived), per-band-by-rate cells.

Cells holding text such as "[no estimate]" or "[not applicable]" give no row. Series ids:
hmrc_income_tax.{payers,liabilities}.band.from_<lower limit GBP>, hmrc_income_tax.liabilities_total,
hmrc_income_tax.liabilities.rate.<rate>, hmrc_income_tax.total_income,
hmrc_income_tax.payers.all, hmrc_income_tax.payers.rate.<rate>.
Everything is UK, on a tax-year basis, income tax only (no NICs).
"""

from __future__ import annotations

import re
from pathlib import Path

from ..provenance import Provenance, Row
from ..sheets import a1, open_book
from . import FileMeta, LayoutError, normalise_fiscal_year

LAST_OUTTURN = "2023-24"
FIRST_YEAR_21 = "2015-16"
_SHEET_25 = re.compile(r"^2_5_IT_Liabilities_(\d{4}-\d{2})$")
_YEAR_21 = re.compile(r"^\s*(\d{4}) to (\d{4})")
_RATES = ("savers", "basic", "higher", "additional")
HISTORIC_YEARS = tuple(f"{y}-{str(y + 1)[2:]}" for y in range(2015, 2023))  # 2015-16 .. 2022-23
_SHEET_25A = re.compile(r"^2_5a_IT_liability_by_IT_(\d{2})-(\d{2})$", re.IGNORECASE)
_TITLE_25A = re.compile(
    r"^\s*Table 2\.5a Income Tax liabilities,? by Income Range, (\d{4}) to (\d{4})\s*$"
)
_LOWER_LIMIT_25A = "Range of total income (lower limit)"
_UNITS_25A = "Numbers are in thousands. Amounts are in £ million"

SERIES = {
    "hmrc_income_tax.liabilities_total": {
        "title": "Total income tax liability",
        "unit": "gbp_m",
        "period_type": "tax_year",
        "monetary": True,
        "description": "Table 2.5 / 2.5a All Ranges, Total Income Tax liability.",
    },
    "hmrc_income_tax.total_income": {
        "title": "Total income of income tax payers",
        "unit": "gbp_m",
        "period_type": "tax_year",
        "monetary": True,
        "description": "Table 2.5 / 2.5a All Ranges, Total income.",
    },
    "hmrc_income_tax.payers.all": {
        "title": "All income tax payers",
        "unit": "thousand_persons",
        "period_type": "tax_year",
        "monetary": False,
        "description": "Table 2.1, All Income Tax payers.",
    },
}


def _num(v: object) -> float | None:
    return float(v) if isinstance(v, int | float) and not isinstance(v, bool) else None


def _status(fy: str) -> str:
    return "outturn" if fy <= LAST_OUTTURN else "forecast"


def _prov(meta: FileMeta, sheet: str, cell: str, fy: str) -> Provenance:
    return Provenance(
        publisher=meta.source.publisher,
        dataset=meta.source.dataset,
        edition=meta.file.edition,
        publication_date=meta.file.publication_date,
        source_url=meta.file.file_url,
        landing_url=meta.file.landing_url,
        file_sha256=meta.sha256,
        sheet=sheet,
        cell_or_range=cell,
        api_query=None,
        licence=meta.source.licence,
        transformations=(),
        status=_status(fy),
        vintage=meta.file.edition,
        retrieved_at=meta.fetched_at,
    )


def _cols(header: list, wanted: dict[str, str], meta: FileMeta, where: str) -> dict[str, int]:
    """Map header text (startswith match, so '[note n]' suffixes are fine) to column index."""
    out: dict[str, int] = {}
    for key, text in wanted.items():
        for c, h in enumerate(header):
            if isinstance(h, str) and h.strip().startswith(text):
                out[key] = c
                break
        else:
            raise LayoutError(meta.file.key, f"{where}!{text}")
    return out


_WANTED_25 = {
    "payers": "Total number of Income Tax payers",
    "liab": "Total Income Tax liability",
    "income": "Total income",
    **{f"liab_{r}": f"Income Tax liability for {r} rate Income Tax payers" for r in _RATES},
}


def _emit_25(grid: list[list], hr: int, hc: int, sheet: str, fy: str, meta: FileMeta) -> list[Row]:
    """Rows of one Table 2.5 / 2.5a year sheet below its header row `hr` (label column `hc`)."""
    out: list[Row] = []
    cols = _cols(grid[hr], _WANTED_25, meta, sheet)
    for r in range(hr + 1, len(grid)):
        lab = grid[r][hc]
        if isinstance(lab, str) and lab.strip().casefold() == "all ranges":
            items = [
                ("hmrc_income_tax.liabilities_total", "liab", "gbp_m"),
                ("hmrc_income_tax.total_income", "income", "gbp_m"),
                *[(f"hmrc_income_tax.liabilities.rate.{x}", f"liab_{x}", "gbp_m") for x in _RATES],
            ]
        else:
            if isinstance(lab, int | float) and not isinstance(lab, bool):
                digits = str(int(lab))
            elif isinstance(lab, str) and re.search(r"\d", lab):
                digits = re.sub(r"\D", "", lab)
            else:
                continue
            items = [
                (f"hmrc_income_tax.payers.band.from_{digits}", "payers", "thousand_persons"),
                (f"hmrc_income_tax.liabilities.band.from_{digits}", "liab", "gbp_m"),
            ]
        for sid, key, unit in items:
            v = _num(grid[r][cols[key]])
            if v is None:
                continue
            prov = _prov(meta, sheet, a1(r, cols[key]), fy)
            out.append(Row(sid, fy, "tax_year", v, unit, "UK", prov))
    return out


def _parse_25(book, meta: FileMeta) -> list[Row]:
    out: list[Row] = []
    sheets = [(n, m.group(1)) for n in book.sheet_names if (m := _SHEET_25.match(n))]
    if not sheets:
        raise LayoutError(meta.file.key, "2_5_IT_Liabilities_<year> sheets")
    for sheet, fy in sheets:
        try:
            normalise_fiscal_year(fy)
            hr, hc = book.find(sheet, "Range of total income (lower limit)")
        except LookupError as e:
            raise LayoutError(meta.file.key, f"{sheet}!Range of total income (lower limit)") from e
        out += _emit_25(book.rows(sheet), hr, hc, sheet, fy, meta)
    return out


def _parse_25a(book, meta: FileMeta) -> list[Row]:
    """Historic Table 2.5a: one sheet per year, same columns as 2.5 but a different header label.

    Only HISTORIC_YEARS are read (earlier sheets have starting-rate columns and are out of scope).
    Each sheet must carry the expected title and units line, or the parse fails.
    """
    out: list[Row] = []
    found: dict[str, str] = {}
    for n in book.sheet_names:
        if m := _SHEET_25A.match(n):
            found[f"20{m.group(1)}-{m.group(2)}"] = n
    for fy in HISTORIC_YEARS:
        sheet = found.get(fy)
        if sheet is None:
            raise LayoutError(meta.file.key, f"2_5a_IT_liability_by_IT_{fy[2:]} sheet")
        grid = book.rows(sheet)
        title = grid[0][0] if grid and grid[0] else None
        t = _TITLE_25A.match(title) if isinstance(title, str) else None
        if not t or normalise_fiscal_year(f"{t.group(1)}-{t.group(2)}") != fy:
            raise LayoutError(meta.file.key, f"{sheet}!A1 title for {fy}")
        hr = next(
            (
                i
                for i, row in enumerate(grid)
                if row and isinstance(row[0], str) and row[0].strip().startswith(_LOWER_LIMIT_25A)
            ),
            None,
        )
        if hr is None:
            raise LayoutError(meta.file.key, f"{sheet}!{_LOWER_LIMIT_25A}")
        if not any(isinstance(c, str) and _UNITS_25A in c for row in grid[:hr] for c in row if c):
            raise LayoutError(meta.file.key, f"{sheet}!units line '{_UNITS_25A}'")
        out += _emit_25(grid, hr, 0, sheet, fy, meta)
    return out


def _parse_21(book, meta: FileMeta) -> list[Row]:
    sheet = "2_1_IT_payers_by_demographic"
    try:
        hr, hc = book.find(sheet, "Tax year")
    except (KeyError, LookupError) as e:
        raise LayoutError(meta.file.key, f"{sheet}!Tax year") from e
    grid = book.rows(sheet)
    wanted = {
        "all": "All Income Tax payers",
        **{r: f"{r.capitalize()} rate" for r in _RATES},
    }
    cols = _cols(grid[hr], wanted, meta, sheet)
    out: list[Row] = []
    for r in range(hr + 1, len(grid)):
        lab = grid[r][hc]
        m = _YEAR_21.match(lab) if isinstance(lab, str) else None
        if not m:
            continue
        fy = normalise_fiscal_year(f"{m.group(1)}-{m.group(2)}")
        if fy < FIRST_YEAR_21:
            continue
        for key, c in cols.items():
            v = _num(grid[r][c])
            if v is None:
                continue
            sid = (
                "hmrc_income_tax.payers.all"
                if key == "all"
                else f"hmrc_income_tax.payers.rate.{key}"
            )
            out.append(
                Row(
                    sid,
                    fy,
                    "tax_year",
                    v,
                    "thousand_persons",
                    "UK",
                    _prov(meta, sheet, a1(r, c), fy),
                )
            )
    return out


def parse(path: Path, meta: FileMeta) -> list[Row]:
    book = open_book(path)
    if meta.file.key == "hmrc_table_2_5":
        return _parse_25(book, meta)
    if meta.file.key == "hmrc_table_2_5a":
        return _parse_25a(book, meta)
    if meta.file.key == "hmrc_table_2_1":
        return _parse_21(book, meta)
    raise LayoutError(meta.file.key, "unknown file key for hmrc_income_tax")
