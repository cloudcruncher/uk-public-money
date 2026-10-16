"""Layman layer: per-person, shares, benefits, Cabinet Office and glossary built from fixtures."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from ukpm import build
from ukpm.__main__ import main as cli_main
from ukpm.parsers.dwp_benefits import BENEFIT_PAIRS

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def api(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("api") / "v1"
    cwd = os.getcwd()
    os.chdir(ROOT)
    mp = pytest.MonkeyPatch()
    mp.setattr(build, "WORK", tmp_path_factory.mktemp("work"))
    try:
        assert cli_main(["build", "--offline", "--out", str(out)]) == 0
    finally:
        mp.undo()
        os.chdir(cwd)
    return out


def J(p: Path):
    return json.loads(p.read_text())


@pytest.fixture(scope="module")
def records(api):
    recs = {}
    for f in (api / "provenance").glob("*.json"):
        recs.update(J(f)["records"])
    return recs


def _values(obj):
    if isinstance(obj, dict):
        if "value" in obj and "provenance_id" in obj:
            yield obj
        for v in obj.values():
            yield from _values(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _values(v)


def _input_ids(rec, records):
    return set(rec.get("inputs") or []) | {
        i for t in rec.get("transformations", []) for i in t.get("inputs", [])
    }


def test_per_person_equals_nominal_over_population(api, records):
    nom = next(
        p
        for p in J(api / "series/pesa.tme.json")["variants"]["nominal"]
        if p["fiscal_year"] == "2024-25"
    )
    per = next(
        p
        for p in J(api / "series/pesa.tme.json")["variants"]["per_person"]
        if p["fiscal_year"] == "2024-25"
    )
    pop = next(
        p
        for p in J(api / "series/ons_population.uk.json")["variants"]["nominal"]
        if p["fiscal_year"] == "2024-25"
    )
    assert per["value"] == pytest.approx(nom["value"] * 1e9 / pop["value"])
    assert pop["provenance_id"] in _input_ids(records[per["provenance_id"]], records)


def test_per_person_real_cites_population_and_deflator(api, records):
    pr = J(api / "series/pesa.tme.json")["variants"]["per_person_real"][0]
    ins = _input_ids(records[pr["provenance_id"]], records)
    series = {records[i]["series_id"] for i in ins if i in records}
    assert any(s.startswith("ons_population.") for s in series)
    assert "obr.gdp_deflator" in series


def test_every_benefit_pair_has_a_file(api):
    idx = J(api / "benefits/index.json")
    slugs = {b["slug"] for b in idx["benefits"]}
    assert slugs
    assert len(slugs) == len(BENEFIT_PAIRS)
    for s in slugs:
        assert (api / "benefits" / f"{s}.json").is_file()


def test_carers_allowance_cost_per_claimant_is_spend_over_caseload(api, records):
    d = J(api / "benefits/carers-allowance.json")
    cpc = d["cost_per_claimant"][-1]
    spend = {p["fiscal_year"]: p for p in d["spend"]}[cpc["fiscal_year"]]
    cases = {p["fiscal_year"]: p for p in d["claimants"]}[cpc["fiscal_year"]]
    assert cpc["value"] == pytest.approx(spend["value"] * 1e9 / (cases["value"] * 1000))
    assert cases["provenance_id"] in _input_ids(records[cpc["provenance_id"]], records)


def test_shares_sum_to_100(api):
    for st in J(api / "shares.json")["sets"]:
        if st.get("available") is False:
            assert st.get("reason")
            continue
        tot = sum(p["per_100"]["value"] for p in st["parts"]) + st["other"]["value"]
        assert tot == pytest.approx(100.0, abs=1e-9)


def test_cabinet_office_summary_is_aggregate_only_and_capped(api):
    p = api / "cabinet_office/summary.json"
    d = J(p)
    assert p.stat().st_size <= d["caps"]["max_bytes"]
    text = p.read_text().lower()
    for k in ("transaction_number", "ref", "expense_area", "date"):
        assert f'"{k}"' not in text
    floor = d["caps"]["supplier_floor_gbp"]
    assert len(d["top_suppliers"]) <= d["caps"]["suppliers"]
    assert all(s["point"]["value"] >= floor for s in d["top_suppliers"])


def test_every_derived_value_cites_its_inputs(api, records):
    derived = 0
    for f in ("shares.json", "benefits/carers-allowance.json"):
        for v in _values(J(api / f)):
            rec = records[v["provenance_id"]]
            tr = rec.get("transformations") or []
            if any(
                t["op"] in ("per_person", "per_claimant", "share_of_total", "per_100") for t in tr
            ):
                derived += 1
                assert _input_ids(rec, records), (f, v["provenance_id"])
                assert all(i in records for i in _input_ids(rec, records))
    assert derived


def _glossary(tmp_path, **over):
    e = {"id": "x", "term": "X", "aliases": [], "plain": "A plain line.", "long": "A longer line."}
    e.update(over)
    p = tmp_path / "g.yml"
    p.write_text(yaml.safe_dump([e]))
    return p


def test_glossary_accepts_clean_entry(tmp_path):
    out = build.build_glossary(set(), "2026-10-15T00:00:00Z", _glossary(tmp_path))
    assert out["terms"][0]["id"] == "x"


def test_glossary_build_fails_when_entry_contains_a_figure(tmp_path):
    with pytest.raises(build.GlossaryError):
        build.build_glossary(
            set(), "2026-10-15T00:00:00Z", _glossary(tmp_path, plain="It cost 12.5 billion.")
        )


# ---- wave 2: households, GDP, UK shares, debt interest ----------------------------------------


def _pt(api, sid, variant, fy):
    return next(
        p for p in J(api / f"series/{sid}.json")["variants"][variant] if p["fiscal_year"] == fy
    )


def test_per_household_is_spend_over_households_and_cites_both(api, records):
    nom = _pt(api, "pesa_uk.tme", "nominal", "2025-26")
    per = _pt(api, "pesa_uk.tme", "per_household", "2025-26")
    hh = _pt(api, "ons_households.uk", "nominal", "2025-26")
    assert hh["value"] == 29003.0
    assert per["unit"] == "GBP_per_household"
    assert per["value"] == pytest.approx(nom["value"] * 1e9 / (hh["value"] * 1000))
    rec = records[per["provenance_id"]]
    ops = [t for t in rec["transformations"] if t["op"] == "per_household"]
    assert ops and hh["provenance_id"] in ops[0]["inputs"]
    # the spend side is the record itself (same file, sheet and cell as the nominal point)
    nrec = records[nom["provenance_id"]]
    assert (rec["file_sha256"], rec["sheet"], rec["cell_or_range"]) == (
        nrec["file_sha256"],
        nrec["sheet"],
        nrec["cell_or_range"],
    )
    assert "April-June" in ops[0]["detail"]


def test_spending_uk_is_primary_and_england_is_labelled_fallback(api):
    sets = {s["id"]: s for s in J(api / "shares.json")["sets"]}
    assert sets["spending_uk"]["role"] == "primary"
    assert sets["spending_england"]["role"] == "fallback"
    assert sets["spending_england"]["superseded_by"] == "spending_uk"
    uk = sets["spending_uk"]
    assert uk["other_label"]
    assert all("per_household" in p for p in uk["parts"])
    tot = sum(p["per_100"]["value"] for p in uk["parts"]) + uk["other"]["value"]
    assert tot == pytest.approx(100.0, abs=1e-9)


def test_calendar_and_stock_series_have_only_nominal(api):
    for sid in ("ons_gdp.nominal", "ons_psf.ps_net_debt_gbp_bn"):
        assert set(J(api / f"series/{sid}.json")["variants"]) == {"nominal"}


def test_debt_interest_has_per_100_of_receipts(api, records):
    v = J(api / "series/ons_psf.cg_debt_interest.json")["variants"]
    assert "per_100" in v and v["per_100"]
    rec = records[v["per_100"][0]["provenance_id"]]
    series = {records[i]["series_id"] for i in _input_ids(rec, records) if i in records}
    assert "ons_psf.cg_receipts" in series
    idx = J(api / "index.json")
    assert idx["debt_interest"] and idx["per_household"] and idx["gdp"]


def test_debt_interest_variants_come_from_the_series(api):
    idx = J(api / "index.json")
    series = J(api / "series/ons_psf.cg_debt_interest.json")
    assert idx["debt_interest"]["variants"] == sorted(series["variants"])


def test_spreadsheet_check_block_keeps_v1_aliases(records):
    rec = next(r for r in records.values() if r["check"]["kind"] == "spreadsheet")
    c = rec["check"]
    assert c["download_url"] == rec["source_url"] and c["sha256"] == rec["file_sha256"]
    assert c["sheet"] == rec["sheet"] and c["cell"] == rec["cell_or_range"]
    assert c["landing_url"] == rec["landing_url"] and c["derived_from"] == rec["inputs"]


def test_benefits_index_headline_has_spend_and_basis(api):
    bx = J(api / "benefits/index.json")
    for b in bx["benefits"]:
        assert b["caseload_basis"] in ("in_payment", "all_cases")
        if b["headline"]:
            assert b["headline"]["spend"]["fiscal_year"] == b["headline"]["fiscal_year"]
            assert "spend_real" in b["headline"]


def test_clean_supplier_strips_vendor_number():
    assert build.clean_supplier("1234567 Acme Ltd") == "Acme Ltd"
    assert build.clean_supplier("  0012345678   Acme Ltd ") == "Acme Ltd"
    assert build.clean_supplier("12345 Acme Ltd") == "12345 Acme Ltd"  # fewer than 6 digits
    assert build.clean_supplier("Acme 1234567 Ltd") == "Acme 1234567 Ltd"


def test_gdp_calendar_year_is_not_used_for_pct_gdp(api):
    assert J(api / "index.json")["gdp"]["calendar_year"]["used_for"] is None
