"""PESA parser tests against the trimmed real-file fixtures in this directory (see MANIFEST.yml)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ukpm.fetch import fetch_source
from ukpm.parsers import FileMeta, LayoutError, pesa
from ukpm.provenance import validate
from ukpm.registry import load

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def src():
    return next(s for s in load(ROOT / "data/sources.yml") if s.id == "pesa")


@pytest.fixture(scope="module")
def rows(src, tmp_path_factory):
    import os

    cwd = os.getcwd()
    os.chdir(ROOT)  # fixture_dir in sources.yml is relative to the repo root
    try:
        fetched = fetch_source(src, offline=True, work=tmp_path_factory.mktemp("work"))
    finally:
        os.chdir(cwd)
    by_key = {f.key: f for f in src.files}
    out = []
    for ff in fetched:
        meta = FileMeta(src, by_key[ff.file_key], ff.sha256, ff.url, ff.fetched_at, ff.path)
        out.extend(pesa.parse(ff.path, meta))
    return out, fetched


def _get(rs, series, year, vintage):
    (r,) = [
        x
        for x in rs
        if x.series_id == series and x.fiscal_year == year and x.prov.vintage == vintage
    ]
    return r


def test_all_rows_have_complete_provenance_and_original_hash(rows, src):
    rs, fetched = rows
    assert all(f.from_fixture for f in fetched)
    originals = {f.sha256 for f in src.files}
    for r in rs:
        validate(r.prov)
        assert r.prov.file_sha256 in originals


def test_known_cells_by_label(rows):
    rs, _ = rows
    r = _get(rs, "pesa.cofog.general_public_services", "2015-16", "PESA 2021")
    assert (r.value, r.prov.sheet, r.prov.cell_or_range, r.geography) == (
        4330.0,
        "10.1",
        "B12",
        "England",
    )
    r = _get(rs, "pesa.cofog.general_public_services", "2024-25", "PESA 2026")
    assert (r.value, r.prov.cell_or_range) == (9049.0, "F12")
    r = _get(rs, "pesa.tme", "2025-26", "PESA 2026")
    assert (r.value, r.prov.sheet, r.prov.cell_or_range, r.unit, r.prov.status) == (
        1360.1,
        "4_1",
        "M46",
        "gbp_bn",
        "outturn",
    )
    assert _get(rs, "pesa.tme", "2026-27", "PESA 2026").prov.status == "forecast"


def test_combine_keeps_newest_edition(rows):
    rs, _ = rows
    merged = pesa.combine(rs)
    cof = [r for r in merged if r.series_id == "pesa.cofog.health"]
    assert [r.fiscal_year for r in cof] == [f"{y}-{str(y + 1)[2:]}" for y in range(2015, 2025)]
    vint = {r.fiscal_year: r.prov.vintage for r in cof}
    assert (
        vint["2015-16"] == "PESA 2021"
        and vint["2019-20"] == "PESA 2025"
        and vint["2024-25"] == "PESA 2026"
    )
    assert len({(r.series_id, r.fiscal_year) for r in merged}) == len(merged)


def test_changed_label_raises_layout_error(src, tmp_path):
    import openpyxl

    path = ROOT / "tests/fixtures/spend/pesa_2026_ch10.trim.xlsx"
    wb = openpyxl.load_workbook(path)
    wb["10.1"]["A76"] = "Total wellbeing"
    bad = tmp_path / "bad.xlsx"
    wb.save(bad)
    f = next(x for x in src.files if x.key == "pesa_2026_ch10")
    meta = FileMeta(src, replace(f), f.sha256, f.file_url, "2026-10-15T00:00:00Z", bad)
    with pytest.raises(LayoutError, match="Total health"):
        pesa.parse(bad, meta)
