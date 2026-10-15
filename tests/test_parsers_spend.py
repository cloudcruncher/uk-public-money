"""PESA parser: per-year known values re-checked against the fixture cell named in provenance."""

from __future__ import annotations

from dataclasses import replace
from functools import cache
from pathlib import Path

import openpyxl
import pytest
import yaml

from ukpm.parsers import FileMeta, LayoutError, normalise_fiscal_year, pesa
from ukpm.provenance import validate
from ukpm.registry import load

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests/fixtures/spend"
FETCHED = "2026-10-15T00:00:00Z"
YEARS = [f"{y}-{str(y + 1)[2:]}" for y in range(2015, 2029)]


@pytest.fixture(scope="module")
def src():
    return next(s for s in load(ROOT / "data/sources.yml") if s.id == "pesa")


@pytest.fixture(scope="module")
def paths(src):
    manifest = yaml.safe_load((FIXTURES / "MANIFEST.yml").read_text())
    by_sha = {e["original_sha256"]: FIXTURES / e["fixture"] for e in manifest}
    return {f.key: by_sha[f.sha256] for f in src.files}


def _meta(src, key, path):
    f = next(x for x in src.files if x.key == key)
    return FileMeta(src, f, f.sha256, f.file_url, FETCHED, path)


@pytest.fixture(scope="module")
def rows(src, paths):
    out = []
    for key, p in paths.items():
        out.extend(pesa.parse(p, _meta(src, key, p)))
    return out


@cache
def _wb(path: Path):
    return openpyxl.load_workbook(path, data_only=True)


def _get(rows, series, year, vintage):
    (r,) = [
        x
        for x in rows
        if x.series_id == series and x.fiscal_year == year and x.prov.vintage == vintage
    ]
    return r


def test_every_row_complete_provenance_and_value_matches_recorded_cell(rows, src, paths):
    by_sha = {f.sha256: paths[f.key] for f in src.files}
    assert rows
    for r in rows:
        validate(r.prov)
        assert r.prov.file_sha256 in by_sha
        assert r.prov.licence == "OGL-UK-3.0"
        assert r.prov.transformations == ()
        cell = _wb(by_sha[r.prov.file_sha256])[r.prov.sheet][r.prov.cell_or_range].value
        assert cell == r.value, (r.series_id, r.fiscal_year, r.prov.vintage, r.prov.cell_or_range)


# Known values (GBP bn) for pesa.tme from Table 4.1, PESA 2026 (sheet 4_1, column M).
TME = {
    "2015-16": (793.7, "M36", "outturn"),
    "2016-17": (811.4, "M37", "outturn"),
    "2017-18": (838.8, "M38", "outturn"),
    "2018-19": (856.1, "M39", "outturn"),
    "2019-20": (884.9, "M40", "outturn"),
    "2020-21": (1102.9, "M41", "outturn"),
    "2021-22": (1040.9, "M42", "outturn"),
    "2022-23": (1160.7, "M43", "outturn"),
    "2023-24": (1230.8, "M44", "outturn"),
    "2024-25": (1290.0, "M45", "outturn"),
    "2025-26": (1360.1, "M46", "outturn"),
    "2026-27": (1419.3, "M47", "forecast"),
    "2027-28": (1471.9, "M48", "forecast"),
    "2028-29": (1513.5, "M49", "forecast"),
}


@pytest.mark.parametrize("fy", sorted(TME))
def test_tme_per_year_value_cell_status(rows, paths, fy):
    value, cell, status = TME[fy]
    r = _get(rows, "pesa.tme", fy, "PESA 2026")
    assert (r.value, r.prov.sheet, r.prov.cell_or_range, r.prov.status) == (
        value,
        "4_1",
        cell,
        status,
    )
    assert (r.unit, r.geography, r.period_basis) == ("gbp_bn", "UK", "fiscal_year")
    assert _wb(paths["pesa_2026_ch4"])["4_1"][cell].value == value


def test_aggregates_cover_all_four_series_for_every_year(rows):
    for sid in ("pesa.tme", "pesa.current_expenditure", "pesa.depreciation", "pesa.net_investment"):
        got = sorted(r.fiscal_year for r in rows if r.series_id == sid)
        assert got == YEARS[:14], sid


def test_forecast_starts_exactly_after_stated_outturn_cutoff(rows, paths):
    sheet = _wb(paths["pesa_2026_ch4"])["4_1"]
    note = next(
        c.value
        for row in sheet.iter_rows(max_row=8)
        for c in row
        if isinstance(c.value, str) and "Outturn data in this table up to" in c.value
    )
    assert "2025-26" in note
    agg = [r for r in rows if r.prov.sheet == "4_1"]
    assert {r.fiscal_year for r in agg if r.prov.status == "outturn"} == set(YEARS[:11])
    assert {r.fiscal_year for r in agg if r.prov.status == "forecast"} == set(YEARS[11:])


# Table 10.1 layout differs per edition: the first year column is B but the first year moves.
EDITION_LAYOUT = {
    "PESA 2021": ("2015-16", "2019-20"),
    "PESA 2023": ("2017-18", "2021-22"),
    "PESA 2024": ("2018-19", "2022-23"),
    "PESA 2025": ("2019-20", "2023-24"),
    "PESA 2026": ("2020-21", "2024-25"),
}
# (edition, year) -> (value GBP m, cell) for Total Expenditure on Services in England (row 124).
TES = {
    ("PESA 2021", "2015-16"): (483676.0, "B124"),
    ("PESA 2021", "2019-20"): (540585.0, "F124"),
    ("PESA 2023", "2017-18"): (502996.0, "B124"),
    ("PESA 2023", "2020-21"): (740298.0, "E124"),
    ("PESA 2024", "2018-19"): (520836.0, "B124"),
    ("PESA 2024", "2022-23"): (698215.0, "F124"),
    ("PESA 2025", "2019-20"): (542600.0, "B124"),
    ("PESA 2025", "2023-24"): (728359.0, "F124"),
    ("PESA 2026", "2020-21"): (737515.0, "B124"),
    ("PESA 2026", "2024-25"): (769898.0, "F124"),
}


@pytest.mark.parametrize(("edition", "fy"), sorted(TES))
def test_total_services_per_edition_year(rows, paths, edition, fy):
    value, cell = TES[(edition, fy)]
    r = _get(rows, "pesa.cofog.total_services", fy, edition)
    assert (r.value, r.prov.cell_or_range, r.prov.sheet) == (value, cell, "10.1")
    assert (r.unit, r.geography, r.prov.status) == ("gbp_m", "England", "outturn")


@pytest.mark.parametrize("edition", sorted(EDITION_LAYOUT))
def test_edition_year_window_and_row_counts(rows, edition):
    first, last = EDITION_LAYOUT[edition]
    cof = [r for r in rows if r.series_id.startswith("pesa.cofog.") and r.prov.vintage == edition]
    assert {r.fiscal_year for r in cof} == set(YEARS[YEARS.index(first) : YEARS.index(last) + 1])
    assert len(cof) == 11 * 5  # ten functions plus total, five years
    assert {r.prov.status for r in cof} == {"outturn"}
    assert {r.prov.edition for r in cof} == {edition}
    # first year always sits in column B whatever the edition
    assert {r.prov.cell_or_range[0] for r in cof if r.fiscal_year == first} == {"B"}


def test_restated_value_differs_between_editions_but_each_matches_its_cell(rows):
    old = _get(rows, "pesa.cofog.general_public_services", "2019-20", "PESA 2021")
    new = _get(rows, "pesa.cofog.general_public_services", "2019-20", "PESA 2025")
    assert (old.value, old.prov.cell_or_range) == (5991.0, "F12")
    assert (new.value, new.prov.cell_or_range) == (5880.0, "B12")


def test_combine_picks_newest_edition_and_is_unique(rows):
    merged = pesa.combine(rows)
    keys = [(r.series_id, r.fiscal_year) for r in merged]
    assert len(keys) == len(set(keys)) and keys == sorted(keys)
    r = next(
        x
        for x in merged
        if x.series_id == "pesa.cofog.total_services" and x.fiscal_year == "2020-21"
    )
    assert (r.prov.vintage, r.value) == ("PESA 2026", 737515.0)
    r = next(
        x
        for x in merged
        if x.series_id == "pesa.cofog.total_services" and x.fiscal_year == "2015-16"
    )
    assert r.prov.vintage == "PESA 2021"


def test_combine_empty_and_single():
    assert pesa.combine([]) == []


# ---- layout / failure handling -------------------------------------------------------------


def _edited(paths, key, tmp_path, sheet, edits):
    wb = openpyxl.load_workbook(paths[key])
    for addr, v in edits.items():
        wb[sheet][addr] = v
    out = tmp_path / "edited.xlsx"
    wb.save(out)
    return out


def test_missing_sheet_raises_layout_error(src, paths, tmp_path):
    wb = openpyxl.load_workbook(paths["pesa_2026_ch10"])
    wb["10.1"].title = "renamed"
    bad = tmp_path / "b.xlsx"
    wb.save(bad)
    with pytest.raises(LayoutError, match="10.1"):
        pesa.parse(bad, _meta(src, "pesa_2026_ch10", bad))


def test_unknown_role_raises_layout_error(src, paths):
    p = paths["pesa_2026_ch10"]
    meta = _meta(src, "pesa_2026_ch10", p)
    meta = replace(meta, file=replace(meta.file, role="mystery"))
    with pytest.raises(LayoutError, match="unsupported role"):
        pesa.parse(p, meta)


def test_non_numeric_value_cell_raises_layout_error_naming_cell(src, paths, tmp_path):
    bad = _edited(paths, "pesa_2026_ch10", tmp_path, "10.1", {"B12": "see note"})
    with pytest.raises(LayoutError, match="B12"):
        pesa.parse(bad, _meta(src, "pesa_2026_ch10", bad))


@pytest.mark.parametrize("marker", ["-", "..", "x", None])
def test_blank_markers_give_no_row_not_zero(src, paths, tmp_path, marker):
    bad = _edited(paths, "pesa_2026_ch10", tmp_path, "10.1", {"B12": marker})
    out = pesa.parse(bad, _meta(src, "pesa_2026_ch10", bad))
    gps = [
        r
        for r in out
        if r.series_id == "pesa.cofog.general_public_services" and r.fiscal_year == "2020-21"
    ]
    assert gps == []
    assert len(out) == 55 - 1


def test_missing_outturn_cutoff_note_raises(src, paths, tmp_path):
    wb = openpyxl.load_workbook(paths["pesa_2026_ch4"])
    ws = wb["4_1"]
    for row in ws.iter_rows(max_row=8):
        for c in row:
            if isinstance(c.value, str) and "Outturn data in this table" in c.value:
                c.value = "Data"
    bad = tmp_path / "b.xlsx"
    wb.save(bad)
    with pytest.raises(LayoutError, match="Outturn data"):
        pesa.parse(bad, _meta(src, "pesa_2026_ch4", bad))


def test_duplicate_total_label_raises(src, paths, tmp_path):
    ws = openpyxl.load_workbook(paths["pesa_2026_ch10"])["10.1"]
    label = next(
        c
        for row in ws.iter_rows()
        for c in row
        if c.value == "Total Expenditure on Services in England"
    )
    bad = _edited(paths, "pesa_2026_ch10", tmp_path, "10.1", {f"A{label.row - 1}": label.value})
    with pytest.raises(LayoutError, match="duplicate"):
        pesa.parse(bad, _meta(src, "pesa_2026_ch10", bad))


def test_wrong_unit_header_raises(src, paths, tmp_path):
    wb = openpyxl.load_workbook(paths["pesa_2026_ch10"])
    for row in wb["10.1"].iter_rows(max_row=6):
        for c in row:
            if str(c.value).strip() == "£ million":
                c.value = "£ billion"
    bad = tmp_path / "b.xlsx"
    wb.save(bad)
    with pytest.raises(LayoutError, match="million"):
        pesa.parse(bad, _meta(src, "pesa_2026_ch10", bad))


@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("2015/16", "2015-16"),
        ("2015-2016", "2015-16"),
        (" 1999-00 ", "1999-00"),
        ("2099/00", "2099-00"),
    ],
)
def test_normalise_fiscal_year(text, want):
    assert normalise_fiscal_year(text) == want


@pytest.mark.parametrize("text", ["2015-17", "2015", "abc", "2015/15", ""])
def test_normalise_fiscal_year_rejects(text):
    with pytest.raises(ValueError):
        normalise_fiscal_year(text)
