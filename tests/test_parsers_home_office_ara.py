"""Home Office Annual Report and Accounts 2025-26 (PDF): deterministic page-text parser.

The fixture is the real five pages (others blank), so PDF page numbers are the real ones. Layout
failures are simulated by changing the extracted text of one page.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from ukpm.parsers import FileMeta, LayoutError, home_office_ara
from ukpm.provenance import problems
from ukpm.registry import FileEntry, Source

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests/fixtures/home_office_ara/ara_2025_26.trimmed.pdf"
SHA = "c8cda7ee5f28700b4a2174b3889cb203c410503c60222e6a03102d92642c1350"
URL = (
    "https://assets.publishing.service.gov.uk/media/6a58e9953ae256c99b702f50/"
    "36.54_HO_ARA_25-26_WEB.pdf"
)
LANDING = (
    "https://www.gov.uk/government/publications/home-office-annual-report-and-accounts-2025-to-2026"
)


def meta_for(path: Path = FIXTURE) -> FileMeta:
    f = FileEntry(
        "ho_ara_2025_26", "HO ARA 2025-26", "2026-07-14", URL, LANDING, "pdf", SHA, "main"
    )
    s = Source(
        id="home_office_ara", publisher="Home Office", dataset="ARA", landing_url=LANDING,
        licence="OGL-UK-3.0", licence_evidence=None, cadence=None, coverage={},
        verdict="USABLE", enabled=True, fixture_dir=None, user_agent=None, files=(f,),
    )  # fmt: skip
    return FileMeta(s, f, SHA, URL, "2026-10-15T00:00:00Z", path)


def run(path: Path = FIXTURE):
    return home_office_ara.parse(path, meta_for(path))


@pytest.fixture(scope="module")
def rows():
    return run()


def one(rows, slug, fy):
    (r,) = [x for x in rows if x.series_id == f"home_office_ara.{slug}" and x.fiscal_year == fy]
    return r


@pytest.fixture
def edit_page(monkeypatch):
    """Apply fn(text) to the extracted text of one PDF page."""

    def _edit(page: int, fn):
        orig = home_office_ara._Doc.page

        def patched(self, n):
            t = orig(self, n)
            return fn(t) if n == page else t

        monkeypatch.setattr(home_office_ara._Doc, "page", patched)

    return _edit


# (slug, year, published GBP thousand, pdf page, printed page)
EXPECTED = [
    ("visa_income", "2025-26", 3574088, 283, 278),
    ("visa_income", "2024-25", 2978355, 283, 278),
    ("ihs_retained", "2025-26", 2318923, 283, 278),
    ("ihs_retained", "2024-25", 2420109, 283, 278),
    ("ihs_payable_consolidated_fund", "2025-26", 0, 284, 279),
    ("ihs_payable_consolidated_fund", "2024-25", 200769, 284, 279),
    ("ukvi_fee_income", "2025-26", 3574081, 228, 223),
    ("ukvi_fee_income", "2024-25", 2978356, 228, 223),
    ("ukvi_full_cost", "2025-26", 1067639, 228, 223),
    ("ukvi_full_cost", "2024-25", 1164523, 228, 223),
    ("ukvi_surplus", "2025-26", 2506442, 228, 223),
    ("ukvi_surplus", "2024-25", 1813833, 228, 223),
    ("immigration_skills_charge", "2025-26", 594309, 351, 346),
    ("immigration_skills_charge", "2024-25", 559727, 351, 346),
    ("civil_penalties", "2025-26", 111337, 351, 346),
    ("civil_penalties", "2024-25", 122890, 351, 346),
    ("trust_total_revenue", "2025-26", 814739, 351, 346),
    ("trust_total_revenue", "2024-25", 786835, 351, 346),
]


@pytest.mark.parametrize(("slug", "year", "k", "page", "printed"), EXPECTED)
def test_values_pages_and_unit_scaling(rows, slug, year, k, page, printed):
    r = one(rows, slug, year)
    assert r.unit == "gbp_m" and r.value == pytest.approx(k / 1000)
    assert r.prov.sheet == f"PDF p{page} (printed p{printed})"
    assert r.prov.cell_or_range.startswith("row '") and year in r.prov.cell_or_range
    assert r.prov.file_sha256 == SHA and r.prov.status == "outturn"
    ops = [t.op for t in r.prov.transformations]
    assert ops[0] == "pdf_text" and ops[-1] == "scale"
    assert "x 0.001" in r.prov.transformations[-1].detail
    assert not problems(r.prov)


def test_all_series_two_years_and_declared(rows):
    assert len(rows) == 18 == len(EXPECTED)
    assert {r.series_id for r in rows} == set(home_office_ara.SERIES)
    assert {r.fiscal_year for r in rows} == {"2025-26", "2024-25"}
    assert all(r.period_basis == "fiscal_year" and r.geography == "UK" for r in rows)


def test_nil_dash_is_recorded_as_a_transformation(rows):
    ops = [t.op for t in one(rows, "ihs_payable_consolidated_fund", "2025-26").prov.transformations]
    assert ops == ["pdf_text", "nil", "scale"]
    assert "nil" not in [t.op for t in one(rows, "ihs_retained", "2025-26").prov.transformations]


def test_scout_figures_in_millions(rows):
    # 594.3m / 559.7m (Trust Statement narrative, one decimal) agree with the table in thousands
    assert round(one(rows, "immigration_skills_charge", "2025-26").value, 1) == 594.3
    assert round(one(rows, "immigration_skills_charge", "2024-25").value, 1) == 559.7
    assert round(one(rows, "trust_total_revenue", "2025-26").value, 1) == 814.7


def test_descriptions_carry_the_restatement_caveat():
    for s in home_office_ara.SERIES.values():
        assert "Reclassified" in s["description"] and "restated" in s["description"]


# ---------- layout failures ----------


def test_missing_row_is_layout_error(edit_page):
    edit_page(283, lambda t: t.replace("Visa and immigration", "Visa and something"))
    with pytest.raises(LayoutError, match="Visa and immigration income"):
        run()


def test_duplicated_row_is_layout_error(edit_page):
    row = "Immigration Skills Charge 2.1 594,309 559,727\n"
    edit_page(351, lambda t: t.replace(row, row + row))
    with pytest.raises(LayoutError, match="matched 2 times"):
        run()


def test_wrong_title_is_layout_error(edit_page):
    edit_page(351, lambda t: t.replace("Statement of Revenue", "Statement of Costs"))
    with pytest.raises(LayoutError, match="title"):
        run()


def test_changed_year_header_is_layout_error(edit_page):
    edit_page(283, lambda t: t.replace("2025-26 2024-25", "2026-27 2025-26", 1))
    with pytest.raises(LayoutError, match="year header"):
        run()


def test_changed_printed_page_is_layout_error(edit_page):
    edit_page(228, lambda t: re.sub(r"(?m)^223$", "224", t))
    with pytest.raises(LayoutError, match="printed page number 223"):
        run()


def test_changed_unit_header_is_layout_error(edit_page):
    edit_page(283, lambda t: t.replace("£’000", "£m"))
    with pytest.raises(LayoutError, match="column header"):
        run()


def test_malformed_number_is_layout_error(edit_page):
    edit_page(283, lambda t: t.replace("3,574,088", "3,574, 088", 1))
    with pytest.raises(LayoutError, match="Visa and immigration income"):
        run()


def test_core_and_group_columns_must_agree(edit_page):
    edit_page(283, lambda t: t.replace("2,318,923 2,318,923", "2,318,900 2,318,923", 1))
    with pytest.raises(LayoutError, match="Core Department != Departmental Group"):
        run()


def test_trust_parts_must_add_to_total(edit_page):
    edit_page(351, lambda t: t.replace("96,594", "96,595", 1))
    with pytest.raises(LayoutError, match="civil penalty types"):
        run()


def test_trust_total_must_add_up(edit_page):
    edit_page(351, lambda t: t.replace("814,739", "814,740", 1))
    with pytest.raises(LayoutError, match="total revenue"):
        run()


def test_fee_surplus_check(edit_page):
    edit_page(228, lambda t: t.replace("2,506,442", "2,506,443", 1))
    with pytest.raises(LayoutError, match="income - full cost != surplus"):
        run()


def test_value_parses_brackets_dash_and_plain():
    assert home_office_ara._value("(8,276)") == (-8276.0, False)
    assert home_office_ara._value("3,574,088") == (3574088.0, False)
    assert home_office_ara._value("–") == (0.0, True)


def test_num_pattern_rejects_unseparated_digits():
    pat = re.compile(home_office_ara._NUM)
    assert pat.fullmatch("(8,276)") and pat.fullmatch("594,309")
    assert not pat.fullmatch("594309") and not pat.fullmatch("12.5")


def test_fee_recovery_percentage_check(edit_page):
    edit_page(228, lambda t: re.sub(r"\b(\d{2,3})%", "7%", t, count=1))
    with pytest.raises(LayoutError):
        run()


def test_narrative_must_agree_with_table(edit_page):
    edit_page(339, lambda t: t.replace("£594.3 million", "£599.3 million"))
    with pytest.raises(LayoutError, match="disagrees"):
        run()


def test_not_a_pdf_is_layout_error(tmp_path):
    bad = tmp_path / "x.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(LayoutError, match="readable PDF"):
        run(bad)


def test_too_few_pages_is_layout_error(tmp_path):
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(100, 100)
    p = tmp_path / "short.pdf"
    with p.open("wb") as fh:
        w.write(fh)
    with pytest.raises(LayoutError, match="page exists"):
        run(p)


@pytest.mark.skipif(not os.environ.get("UKPM_ARA_PDF"), reason="set UKPM_ARA_PDF to the real PDF")
def test_real_pdf_matches_fixture(rows):
    real = run(Path(os.environ["UKPM_ARA_PDF"]))
    key = lambda r: (r.series_id, r.fiscal_year)  # noqa: E731
    assert [
        (key(r), r.value, r.prov.sheet, r.prov.cell_or_range) for r in sorted(real, key=key)
    ] == [(key(r), r.value, r.prov.sheet, r.prov.cell_or_range) for r in sorted(rows, key=key)]
