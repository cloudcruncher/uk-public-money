"""Immigration-related parsers against trimmed real fixtures: FCDO in-donor refugee costs,
DWP Universal Credit by immigration status, Home Office Core Data Tables (resource DEL)."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from ukpm.parsers import (
    FileMeta,
    LayoutError,
    dwp_uc_status,
    fcdo_oda,
    home_office_asylum,
    home_office_spend,
)
from ukpm.provenance import problems
from ukpm.registry import FileEntry, Source

ROOT = Path(__file__).resolve().parent.parent
FX = ROOT / "tests/fixtures"
GOV = "https://assets.publishing.service.gov.uk/media/"

CASES = {
    "fcdo": (
        fcdo_oda, "fcdo_oda", FX / "fcdo_oda/fig3.trimmed.xlsx",
        "cb1363b7c2fa914e81b0864052e5fb85051aaaadd496749f2a262fbece81a8fa",
        GOV + "69d4cb4d826d774e7b263e3c/Tables-Statistics-on-International-Development-"
        "provisional-UK-ODA-spend-2025.ods",
        "2026-04-09",
    ),
    "uc": (
        dwp_uc_status, "dwp_uc_status", FX / "dwp_uc_status/uc_status_to_may_2026.trimmed.xlsx",
        "22c9f2f3aa448af7f5ea4458cb2286e494a79f69ac31a7fa0b7381e86d2f29e4",
        GOV + "6a82c17492ec93e1e0329a46/"
        "uc-immigration-status-nationality-statistics-to-may-2026.ods",
        "2026-08-18",
    ),
    "ho": (
        home_office_spend, "home_office_spend",
        FX / "home_office_spend/core_data_tables_2026.trimmed.xlsx",
        "8860a2fe3e2b1d1d41e4c7264fc313d2a7cf8d7becf9f9e78456083e51bcda29",
        GOV + "6a5651389e63154454413675/Core_Data_Tables_2026_Home_Office__draft__based_on_ARA_"
        "model_shared_29th_June__-_FINAL__FRT_.xlsx",
        "2026-07-14",
    ),
    "asy": (
        home_office_asylum, "home_office_asylum", FX / "home_office_asylum/asy_00a.trimmed.xlsx",
        "f935782ab90190deb04a1a86f7b6ba7515f32e238c14b96c55993f4793096d14",
        GOV + "6a85c315b0504df9f2c89800/asylum-summary-jun-2026-tables.ods",
        "2026-08-27",
    ),
}  # fmt: skip


def meta_for(name: str, path: Path | None = None) -> FileMeta:
    mod, sid, fixture, sha, url, pub = CASES[name]
    landing = "https://www.gov.uk/government/statistics/x"
    f = FileEntry(f"{sid}_k", f"{sid} edition", pub, url, landing, "xlsx", sha, "main")
    s = Source(
        id=sid, publisher="Test publisher", dataset=f"{sid} dataset", landing_url=landing,
        licence="OGL-UK-3.0", licence_evidence=None, cadence=None, coverage={},
        verdict="PARTIAL", enabled=True, fixture_dir=None, user_agent=None, files=(f,),
    )  # fmt: skip
    return FileMeta(s, f, sha, url, "2026-10-15T00:00:00Z", path or fixture)


def run(name: str, path: Path | None = None):
    return CASES[name][0].parse(path or CASES[name][2], meta_for(name, path))


@pytest.fixture(scope="module")
def all_rows():
    return {n: run(n) for n in CASES}


def one(rows, sid, fy):
    (r,) = [x for x in rows if x.series_id == sid and x.fiscal_year == fy]
    return r


def edited(tmp_path, name, fn):
    wb = openpyxl.load_workbook(CASES[name][2])
    fn(wb)
    p = tmp_path / "x.xlsx"
    wb.save(p)
    return p


@pytest.mark.parametrize("name", list(CASES))
def test_provenance_complete_and_series_declared(all_rows, name):
    rows = all_rows[name]
    mod, _sid, _fx, sha, url, pub = CASES[name]
    assert rows
    for r in rows:
        assert problems(r.prov) == [], (r.series_id, r.fiscal_year)
        assert (r.prov.file_sha256, r.prov.source_url, r.prov.publication_date) == (sha, url, pub)
        assert r.prov.licence == "OGL-UK-3.0" and r.prov.status == "outturn"
        assert r.series_id in mod.SERIES
    assert {r.series_id for r in rows} == set(mod.SERIES)
    for s in mod.SERIES.values():
        assert {"title", "unit", "period_type", "monetary", "description"} <= set(s)


@pytest.mark.parametrize("name", list(CASES))
def test_cell_matches_workbook(all_rows, name):
    wb = openpyxl.load_workbook(CASES[name][2], data_only=True)
    for r in all_rows[name]:
        cell = wb[r.prov.sheet][r.prov.cell_or_range].value
        raw = r.value / 0.001 if name == "ho" else r.value
        assert cell == pytest.approx(raw), r.series_id


# ---------- FCDO ----------


@pytest.mark.parametrize(
    ("slug", "year", "cell", "value"),
    [
        ("home_office", "2021", "B4", 996.362578),
        ("home_office", "2025", "F4", 2050.172),
        ("dwp", "2023", "D8", 249.394476),
        ("hmrc", "2022", "C10", 20.9022089986667),
        ("total", "2022", "C11", 3690.42677186196),
        ("total", "2025", "F11", 2394.70381492376),
    ],
)
def test_fcdo_values(all_rows, slug, year, cell, value):
    r = one(all_rows["fcdo"], f"fcdo_oda.idrc.{slug}", year)
    assert (r.prov.sheet, r.prov.cell_or_range, r.unit) == ("Fig3", cell, "gbp_m")
    assert r.value == value
    assert (r.period_basis, r.geography) == ("calendar_year", "UK")


def test_fcdo_definition_caveats_in_every_description():
    for s in fcdo_oda.SERIES.values():
        assert "first 12 months" in s["description"] and "Provisional" in s["description"]
        assert s["period_type"] == "calendar_year"


def test_fcdo_total_mismatch_is_layout_error(tmp_path):
    def f(wb):
        wb["Fig3"]["C11"] = 9999

    with pytest.raises(LayoutError, match="do not add up"):
        run("fcdo", edited(tmp_path, "fcdo", f))


def test_fcdo_missing_department_is_layout_error(tmp_path):
    def f(wb):
        wb["Fig3"]["A4"] = "Cabinet Office"

    with pytest.raises(LayoutError, match="Home Office"):
        run("fcdo", edited(tmp_path, "fcdo", f))


def test_fcdo_unit_change_is_layout_error(tmp_path):
    def f(wb):
        wb["Fig3"]["B3"] = "2021 [note 3]\n\n£ billion"

    with pytest.raises(LayoutError, match="unit"):
        run("fcdo", edited(tmp_path, "fcdo", f))


# ---------- DWP UC by status ----------


@pytest.mark.parametrize(
    ("slug", "year", "cell", "value"),
    [
        ("cta", "2026", "D10", 7065665.0),
        ("refugee", "2026", "D13", 130618.0),
        ("humanitarian", "2026", "D12", 52499.0),
        ("no_status_recorded", "2026", "D17", 23343.0),
    ],
)
def test_uc_latest_may_values(all_rows, slug, year, cell, value):
    r = one(all_rows["uc"], f"dwp_uc_status.people.{slug}", year)
    assert (r.prov.sheet, r.prov.cell_or_range, r.unit) == ("Table_1", cell, "persons")
    assert (r.value, r.geography, r.period_basis) == (value, "GB", "may_snapshot")


def test_uc_one_point_per_may_and_provisional_flag(all_rows):
    cta = sorted(r.fiscal_year for r in all_rows["uc"] if r.series_id.endswith(".cta"))
    assert cta == ["2022", "2023", "2024", "2025", "2026"]
    assert "provisional" in one(all_rows["uc"], "dwp_uc_status.people.cta", "2026").prov.vintage
    assert "provisional" not in one(all_rows["uc"], "dwp_uc_status.people.cta", "2025").prov.vintage
    assert len(all_rows["uc"]) == 8 * 5


def test_uc_description_carries_guidance_caveats():
    d = dwp_uc_status.SERIES["dwp_uc_status.people.no_status_recorded"]["description"]
    for phrase in ("provisional", "not pounds", "data category", "cannot claim"):
        assert phrase in d
    assert dwp_uc_status.SERIES["dwp_uc_status.people.cta"]["unit"] == "persons"


def test_uc_missing_status_row_is_layout_error(tmp_path):
    def f(wb):
        wb["Table_1"]["B13"] = "Something else"

    with pytest.raises(LayoutError, match="Refugee"):
        run("uc", edited(tmp_path, "uc", f))


def test_uc_wrong_title_is_layout_error(tmp_path):
    def f(wb):
        for c in ("B4", "B5", "B6"):
            wb["Table_1"][c] = "Something else"

    with pytest.raises(LayoutError, match="Universal Credit"):
        run("uc", edited(tmp_path, "uc", f))


# ---------- Home Office ----------


@pytest.mark.parametrize(
    ("slug", "year", "cell", "published_k"),
    [
        ("customer_services_visas_passports", "2025-26", "F17", -4934927.0),
        ("customer_services_visas_passports", "2022-23", "C17", -3166254.0),
        ("asylum_support_resettlement_accommodation", "2025-26", "F20", 4181193.0),
        ("asylum_support_resettlement_accommodation", "2023-24", "D20", 5424708.0),
        ("total", "2025-26", "F35", 17919340.0),
    ],
)
def test_ho_values_scaled_from_thousands(all_rows, slug, year, cell, published_k):
    r = one(all_rows["ho"], f"home_office_spend.resource_del.{slug}", year)
    assert (r.prov.sheet, r.prov.cell_or_range, r.unit) == (
        "Total_departmental_spending",
        cell,
        "gbp_m",
    )
    assert r.value == pytest.approx(published_k / 1000)
    (t,) = r.prov.transformations
    assert t.op == "scale" and "thousand" in t.detail


def test_ho_outturn_only_and_resource_block_only(all_rows):
    rows = all_rows["ho"]
    years = {r.fiscal_year for r in rows}
    assert years == {"2021-22", "2022-23", "2023-24", "2024-25", "2025-26"}
    assert all(int(r.prov.cell_or_range[1:]) < 63 for r in rows)  # not the Capital DEL block
    asy = {r.fiscal_year for r in rows if "asylum_support" in r.series_id}
    assert asy == {"2023-24", "2024-25", "2025-26"}  # earlier years sit under another name
    # placeholder zeros from the earlier structure are not published as zero
    assert {r.fiscal_year for r in rows if r.series_id.endswith("border_force")} == asy


def test_ho_draft_caveat_in_description():
    for s in home_office_spend.SERIES.values():
        assert "draft" in s["description"]
    assert (
        "fee income"
        in home_office_spend.SERIES[
            "home_office_spend.resource_del.customer_services_visas_passports"
        ]["description"]
    )


def test_ho_plans_column_relabelled_outturn_is_refused(tmp_path):
    def f(wb):
        wb["Total_departmental_spending"]["F5"] = "SOMETHING"

    with pytest.raises(LayoutError, match="OUTTURN/PLANS"):
        run("ho", edited(tmp_path, "ho", f))


def test_ho_unit_change_is_layout_error(tmp_path):
    def f(wb):
        wb["Total_departmental_spending"]["C6"] = "£m"

    with pytest.raises(LayoutError, match="unit"):
        run("ho", edited(tmp_path, "ho", f))


# ---------- Home Office asylum summary ----------


@pytest.mark.parametrize(
    ("slug", "year", "cell", "value"),
    [
        ("claims", "2025", "Q7", 101911.0),
        ("claims", "2015", "G7", 39968.0),
        ("support", "2025", "Q18", 107003.0),
        ("support_hotels", "2022", "N19", 45753.0),
        ("support_hotels", "2025", "Q19", 30657.0),
        ("awaiting_decision", "2015", "G13", 22147.0),
    ],
)
def test_asylum_values(all_rows, slug, year, cell, value):
    r = one(all_rows["asy"], f"home_office_asylum.{slug}", year)
    assert (r.prov.sheet, r.prov.cell_or_range, r.unit) == ("Asy_00a", cell, "persons")
    assert (r.value, r.period_basis) == (value, "calendar_year")


def test_asylum_markers_and_june_columns_give_no_rows(all_rows):
    rows = all_rows["asy"]
    hotels = {r.fiscal_year for r in rows if r.series_id.endswith("support_hotels")}
    assert hotels == {"2022", "2023", "2024", "2025"}  # 'z' and ':' cells are not values
    assert not any("June" in r.fiscal_year or r.fiscal_year > "2025" for r in rows)


def test_asylum_missing_row_is_layout_error(tmp_path):
    def f(wb):
        wb["Asy_00a"]["A19"] = "Of which in something else"

    with pytest.raises(LayoutError, match="hotels"):
        run("asy", edited(tmp_path, "asy", f))
