"""ONS mid-year population parser against the trimmed mid-2025 file."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from ukpm.parsers import FileMeta, LayoutError, ons_population
from ukpm.provenance import problems
from ukpm.registry import FileEntry, Source

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "tests/fixtures/ons/mye25tablesuk.trimmed.xlsx"
ORIG_SHA = "8ae244e3341257ecccaee55f4973fe12f46afe6656ead6c1a9ed3f4f8585e40f"
URL = (
    "https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/"
    "populationestimates/datasets/populationestimatesforukenglandandwalesscotlandandnorthernireland/"
    "mid2025/mye25tablesuk.xlsx"
)
LANDING = (
    "https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/"
    "populationestimates/datasets/populationestimatesforukenglandandwalesscotlandandnorthernireland"
)
EDITION = "ONS mid-2025 population estimates"


def _meta(path: Path = PATH) -> FileMeta:
    f = FileEntry(
        "ons_mye_2025", EDITION, "2026-10-01", URL, LANDING, "xlsx", ORIG_SHA, "mye_summary"
    )
    s = Source(
        id="ons_population",
        publisher="Office for National Statistics",
        dataset="Population estimates for the UK, England, Wales, Scotland and Northern Ireland",
        landing_url=LANDING,
        licence="OGL-UK-3.0",
        licence_evidence=None,
        cadence=None,
        coverage={},
        verdict="USABLE",
        enabled=True,
        fixture_dir="tests/fixtures/ons",
        user_agent=None,
        files=(f,),
    )
    return FileMeta(s, f, ORIG_SHA, URL, "2026-10-15T00:00:00Z", path)


@pytest.fixture(scope="module")
def rows():
    return ons_population.parse(PATH, _meta())


def _one(rows, sid, fy):
    (r,) = [x for x in rows if x.series_id == sid and x.fiscal_year == fy]
    return r


@pytest.mark.parametrize(
    ("fy", "value", "cell"),
    [
        ("2025-26", 69483939.0, "D9"),
        ("2024-25", 69256274.0, "E9"),
        ("2023-24", 68588048.0, "F9"),
        ("2015-16", 65086958.0, "N9"),
    ],
)
def test_uk_values_and_cells(rows, fy, value, cell):
    r = _one(rows, "ons_population.uk", fy)
    assert (r.value, r.prov.cell_or_range, r.prov.sheet) == (value, cell, "MYE4")
    assert (r.unit, r.geography, r.period_basis) == ("persons", "UK", "mid_year")
    assert (r.prov.status, r.prov.vintage, r.prov.edition) == ("outturn", EDITION, EDITION)
    assert openpyxl.load_workbook(PATH, data_only=True)["MYE4"][cell].value == value


def test_gb_and_england_rows(rows):
    g = _one(rows, "ons_population.gb", "2025-26")
    e = _one(rows, "ons_population.england", "2025-26")
    assert (g.value, g.prov.cell_or_range, g.geography) == (67555493.0, "D10", "GB")
    assert (e.value, e.prov.cell_or_range, e.geography) == (58834812.0, "D12", "England")


def test_years_from_2015_16_to_2025_26_only(rows):
    years = sorted({r.fiscal_year for r in rows})
    assert years[0] == "2015-16" and years[-1] == "2025-26" and len(years) == 11
    assert {r.series_id for r in rows} == set(ons_population.SERIES)


def test_provenance_complete(rows):
    for r in rows:
        assert problems(r.prov) == []
        assert r.prov.file_sha256 == ORIG_SHA and r.prov.licence == "OGL-UK-3.0"
        assert r.prov.source_url == URL and r.prov.transformations == ()


def test_series_metadata():
    for meta in ons_population.SERIES.values():
        assert meta["monetary"] is False and meta["unit"] == "persons"
        assert "30 June" in meta["description"] and "2024-25" in meta["description"]


def _edited(tmp_path, fn):
    wb = openpyxl.load_workbook(PATH)
    fn(wb)
    p = tmp_path / "x.xlsx"
    wb.save(p)
    return p


def test_mye1_mismatch_raises(tmp_path):
    p = _edited(tmp_path, lambda w: w["MYE1"].__setitem__("B9", 69483938.0))
    with pytest.raises(LayoutError):
        ons_population.parse(p, _meta(p))


def test_missing_uk_row_raises(tmp_path):
    p = _edited(tmp_path, lambda w: w["MYE4"].__setitem__("B9", "SOMEWHERE"))
    with pytest.raises(LayoutError):
        ons_population.parse(p, _meta(p))


def test_missing_sheet_raises(tmp_path):
    p = _edited(tmp_path, lambda w: w["MYE4"].__setattr__("title", "gone"))
    with pytest.raises(LayoutError):
        ons_population.parse(p, _meta(p))


def test_missing_year_column_is_a_gap_not_a_guess(tmp_path):
    p = _edited(tmp_path, lambda w: w["MYE4"].__setitem__("N8", "Mid-2015x"))
    out = ons_population.parse(p, _meta(p))
    assert not [r for r in out if r.fiscal_year == "2015-16"]
    assert [r for r in out if r.fiscal_year == "2016-17"]


def test_blank_cell_gives_no_row(tmp_path):
    p = _edited(tmp_path, lambda w: w["MYE4"].__setitem__("F10", ".."))
    out = ons_population.parse(p, _meta(p))
    assert not [r for r in out if r.series_id == "ons_population.gb" and r.fiscal_year == "2023-24"]
