"""Reconciliation rules R1-R7 and stitching: results are data, a mismatch is never an exception."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import openpyxl
import pytest
import yaml

from ukpm import reconcile
from ukpm.parsers import FileMeta, obr, pesa
from ukpm.registry import load

ROOT = Path(__file__).resolve().parent.parent
SPEND = ROOT / "tests/fixtures/spend"
FUNCS = list(pesa.COFOG_TOTALS.values())[:-1]
RULE_IDS = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]


def pid(r):
    return f"{r.series_id}@{r.prov.edition}/{r.fiscal_year}"


def _run(rows, titles=None, sources=None):
    return reconcile.run(rows, pid, titles or {}, sources or {})


def _rule(out, rid):
    return next(r for r in out["rules"] if r["id"] == rid)["results"]


def _bn(rows):
    """What ukpm.build hands to reconcile: GBP million rows scaled to GBP billion."""
    return [
        replace(r, value=r.value / 1000, unit="gbp_bn") if r.unit == "gbp_m" else r for r in rows
    ]


# ---- R1 on synthetic data ------------------------------------------------------------------


@pytest.fixture
def cofog(make_row):
    def build(total_delta_bn=0.0, drop=0, edition="PESA 2026", year="2024-25"):
        kw = {"edition": edition, "vintage": edition, "publication_date": "2026-07-16"}
        rows = [
            make_row(f"pesa.cofog.{f}", year, 10.0 + i, **kw)
            for i, f in enumerate(FUNCS)
            if i >= drop
        ]
        total = sum(r.value for r in rows) + total_delta_bn
        rows.append(make_row(reconcile.TES, year, total, **kw))
        return rows

    return build


def test_r1_passes_when_functions_sum_to_total(cofog):
    (res,) = _rule(_run(cofog()), "R1")
    assert res["status"] == "pass" and res["fiscal_year"] == "2024-25"
    assert res["edition"] == "PESA 2026"
    assert res["delta"] == pytest.approx(0.0, abs=1e-9)
    assert res["left"]["value"] == pytest.approx(sum(10.0 + i for i in range(10)))
    assert len(res["left"]["provenance_ids"]) == 10 and res["right"]["provenance_id"]


def test_r1_rounding_tolerance_boundary(cofog):
    tol = 0.5 * 10 * reconcile.GBP_M_IN_BN  # GBP 5m across ten rows
    (ok,) = _rule(_run(cofog(total_delta_bn=tol * 0.99)), "R1")
    (bad,) = _rule(_run(cofog(total_delta_bn=tol * 1.5)), "R1")
    assert ok["status"] == "pass"
    assert bad["status"] == "fail"
    assert bad["tolerance_abs"] == pytest.approx(tol)


def test_deliberately_broken_total_is_a_visible_fail_with_delta(cofog):
    out = _run(cofog(total_delta_bn=2.5))
    (res,) = _rule(out, "R1")
    assert res["status"] == "fail"
    assert res["delta"] == pytest.approx(-2.5)
    assert res["delta_pct"] == pytest.approx(-2.5 / res["right"]["value"] * 100)
    assert "delta" in res["reason"] and "tolerance" in res["reason"]
    assert out["summary"]["fail"] >= 1


def test_missing_function_row_is_reported_not_dropped(cofog, make_row):
    full = cofog(edition="PESA 2025", year="2023-24")  # makes all ten function series known
    kw = {"edition": "PESA 2026", "vintage": "PESA 2026", "publication_date": "2026-07-16"}
    partial = [make_row(f"pesa.cofog.{f}", "2024-25", 10.0 + i, **kw) for i, f in enumerate(FUNCS)]
    total = sum(r.value for r in partial)
    rows = full + partial[1:] + [make_row(reconcile.TES, "2024-25", total, **kw)]
    res = {r["edition"]: r for r in _rule(_run(rows), "R1")}
    assert res["PESA 2025"]["status"] == "pass"
    r = res["PESA 2026"]
    assert r["status"] == "fail" and r["delta"] == pytest.approx(-10.0)
    assert "9 function rows" in r["reason"] and "only 9 of 10" in r["reason"]


def test_r1_checks_each_edition_year_separately(cofog):
    rows = cofog(edition="PESA 2026") + cofog(
        total_delta_bn=9.0, edition="PESA 2025", year="2023-24"
    )
    res = {(r["edition"], r["fiscal_year"]): r["status"] for r in _rule(_run(rows), "R1")}
    assert res == {("PESA 2026", "2024-25"): "pass", ("PESA 2025", "2023-24"): "fail"}


def test_r1_total_without_functions_does_not_raise(make_row):
    rows = [make_row(reconcile.TES, "2024-25", 100.0)]
    (res,) = _rule(_run(rows), "R1")
    assert res["status"] == "not_run" and res["reason"]


# ---- shape guarantees ----------------------------------------------------------------------


def test_every_rule_always_present_even_with_no_rows():
    out = _run([])
    assert [r["id"] for r in out["rules"]] == RULE_IDS
    for r in out["rules"]:
        assert r["title"] and r["description"] and r["tolerance"]
        assert r["results"] and all(x["status"] == "not_run" and x["reason"] for x in r["results"])
    assert out["summary"] == {"pass": 0, "fail": 0, "info": 0, "not_run": 7}


def test_summary_counts_match_result_statuses(cofog):
    out = _run(cofog(total_delta_bn=1.0))
    counts = {"pass": 0, "fail": 0, "info": 0, "not_run": 0}
    for rule in out["rules"]:
        for r in rule["results"]:
            counts[r["status"]] += 1
    assert out["summary"] == counts


def test_r4_reason_reflects_disabled_or_enabled_psf():
    off = _rule(_run([], sources={"ons_psf": {"enabled": False, "verdict": "BLOCKED"}}), "R4")
    on = _rule(_run([], sources={"ons_psf": {"enabled": True, "verdict": "USABLE"}}), "R4")
    assert "disabled" in off[0]["reason"] and "BLOCKED" in off[0]["reason"]
    assert "enabled but has no rows" in on[0]["reason"]


# ---- R2 / R3 / R6 / R7 --------------------------------------------------------------------


def test_r2_is_information_not_failure_for_tes_vs_tme(make_row):
    kw = {"edition": "PESA 2026", "publication_date": "2026-07-16"}
    rows = [
        make_row(reconcile.TES, "2024-25", 770.0, **kw),
        make_row("pesa.tme", "2024-25", 1290.0, **kw),
    ]
    (res,) = _rule(_run(rows, {reconcile.TES: "Total expenditure on services"}), "R2")
    assert res["status"] == "info" and "TES" in res["reason"]
    assert res["delta"] == pytest.approx(770.0 - 1290.0)


def test_r2_fails_if_total_is_labelled_tme_and_differs(make_row):
    rows = [make_row(reconcile.TES, "2024-25", 770.0), make_row("pesa.tme", "2024-25", 1290.0)]
    (res,) = _rule(_run(rows, {reconcile.TES: "Total Managed Expenditure"}), "R2")
    assert res["status"] == "fail"


def test_r3_within_and_outside_tolerance_and_skips_forecast(make_row):
    p = lambda y, v, **k: make_row("pesa.tme", y, v, publication_date="2026-07-16", **k)  # noqa: E731
    o = lambda y, v, **k: make_row("obr.psf.tme", y, v, publication_date="2026-09-01", **k)  # noqa: E731
    rows = [
        p("2023-24", 1000.0),
        o("2023-24", 1005.0),  # 0.5% pass
        p("2024-25", 1000.0),
        o("2024-25", 1100.0),  # 10% fail
        p("2026-27", 1000.0, status="forecast"),
        o("2026-27", 1000.0, status="forecast"),
    ]
    res = {r["fiscal_year"]: r for r in _rule(_run(rows), "R3")}
    assert set(res) == {"2023-24", "2024-25"}
    assert res["2023-24"]["status"] == "pass"
    assert res["2024-25"]["status"] == "fail"
    assert res["2024-25"]["delta"] == pytest.approx(-100.0)


def test_r3_not_run_without_shared_outturn_year(make_row):
    rows = [make_row("pesa.tme", "2023-24", 1.0), make_row("obr.psf.tme", "2020-21", 1.0)]
    (res,) = _rule(_run(rows), "R3")
    assert res["status"] == "not_run"


def test_r6_info_normally_fail_if_hmrc_exceeds_obr(make_row):
    ok = [
        make_row("hmrc_receipts.total", "2024-25", 858.0),
        make_row("obr.psf.receipts", "2024-25", 1140.0),
    ]
    (res,) = _rule(_run(ok), "R6")
    assert res["status"] == "info"
    bad = [
        make_row("hmrc_receipts.total", "2024-25", 1200.0),
        make_row("obr.psf.receipts", "2024-25", 1140.0),
    ]
    (res,) = _rule(_run(bad), "R6")
    assert res["status"] == "fail" and res["delta"] == pytest.approx(60.0)


def _dwp(make_row, total_gb, lines, uk_total=None, uk_lines=()):
    rows = [
        make_row(
            f"dwp_benefits.exp.{n}", "2023-24", v, edition="DWP", publication_date="2026-04-01"
        )
        for n, v in lines.items()
    ]
    rows.append(
        make_row(
            reconcile.DWP_GB_TOTAL,
            "2023-24",
            total_gb,
            edition="DWP",
            publication_date="2026-04-01",
        )
    )
    for n, v in uk_lines:
        rows.append(
            make_row(
                f"dwp_benefits.uk_welfare.{n}",
                "2023-24",
                v,
                edition="DWP",
                publication_date="2026-04-01",
            )
        )
    if uk_total is not None:
        rows.append(
            make_row(
                reconcile.DWP_UK_TOTAL,
                "2023-24",
                uk_total,
                edition="DWP",
                publication_date="2026-04-01",
            )
        )
    return rows


def test_r7_sums_top_level_lines_only(make_row):
    rows = _dwp(
        make_row,
        total_gb=300.0,
        lines={
            "state_pension": 150.0,
            "universal_credit": 100.0,
            "state_pension.contributory": 149.0,
            "child_benefit": 50.0,
        },
        uk_total=10.0,
        uk_lines=[
            ("dwp_social_security_gb", 6.0),
            ("northern_ireland_social_security", 4.0),
            ("dwp_social_security_gb.within_the_welfare_cap", 5.0),
        ],
    )
    res = {r["comparison"]: r for r in _rule(_run(rows), "R7")}
    assert res["table_1a_lines"]["status"] == "pass"  # children are not double counted
    assert res["table_1a_lines"]["left"]["value"] == pytest.approx(300.0)
    assert res["uk_welfare_tab_lines"]["status"] == "pass"


def test_r7_broken_total_fails_with_delta(make_row):
    rows = _dwp(
        make_row,
        total_gb=310.0,
        lines={"state_pension": 150.0, "universal_credit": 100.0, "child_benefit": 50.0},
    )
    (res,) = _rule(_run(rows), "R7")
    assert res["status"] == "fail" and res["delta"] == pytest.approx(-10.0)


# ---- stitch --------------------------------------------------------------------------------


def test_stitch_newest_publication_wins_and_old_is_superseded(make_row):
    old = make_row("pesa.tme", "2023-24", 1.0, publication_date="2024-07-30", edition="PESA 2024")
    new = make_row("pesa.tme", "2023-24", 2.0, publication_date="2025-07-17", edition="PESA 2025")
    other = make_row("pesa.tme", "2022-23", 3.0, publication_date="2024-07-30")
    chosen, sup = reconcile.stitch([new, old, other])
    assert chosen[("pesa.tme", "2023-24")] is new and sup == [old]
    assert set(chosen) == {("pesa.tme", "2023-24"), ("pesa.tme", "2022-23")}  # no interpolation


def test_stitch_tie_prefers_outturn(make_row):
    f = make_row("x.y", "2024-25", 1.0, status="forecast", publication_date="2026-01-01")
    o = make_row("x.y", "2024-25", 2.0, status="outturn", publication_date="2026-01-01")
    chosen, _ = reconcile.stitch([o, f])
    assert chosen[("x.y", "2024-25")] is o
    chosen, _ = reconcile.stitch([f, o])
    assert chosen[("x.y", "2024-25")] is o


# ---- on real fixture data ------------------------------------------------------------------


@pytest.fixture(scope="module")
def pesa_rows():
    src = next(s for s in load(ROOT / "data/sources.yml") if s.id == "pesa")
    manifest = yaml.safe_load((SPEND / "MANIFEST.yml").read_text())
    by_sha = {e["original_sha256"]: SPEND / e["fixture"] for e in manifest}
    out = []
    for f in src.files:
        p = by_sha[f.sha256]
        out += pesa.parse(p, FileMeta(src, f, f.sha256, f.file_url, "2026-10-15T00:00:00Z", p))
    return src, out, by_sha


def test_r1_cofog_sum_matches_tes_on_every_fixture_edition_year(pesa_rows):
    _, rows, _ = pesa_rows
    results = _rule(_run(_bn(rows)), "R1")
    assert len(results) == 25  # five editions x five years
    for r in results:
        assert r["status"] == "pass", r
        assert len(r["left"]["provenance_ids"]) == 10
        assert abs(r["delta"]) <= r["tolerance_abs"]


def test_r2_and_r3_on_fixture_data(pesa_rows):
    _, rows, _ = pesa_rows
    out = _run(_bn(rows), {reconcile.TES: "Total expenditure on services"})
    r2 = _rule(out, "R2")
    assert r2 and {r["status"] for r in r2} == {"info"}
    # TES (England) is well below TME (UK)
    assert all(r["delta"] < 0 for r in r2)


def test_pesa_vs_obr_tme_agree_within_one_percent_on_fixtures(pesa_rows):
    _, prows, _ = pesa_rows
    osrc = next(s for s in load(ROOT / "data/sources.yml") if s.id == "obr")
    f = osrc.files[0]
    p = ROOT / "tests/fixtures/obr/PSF_aggregates_databank_Sep-3.trimmed.xlsx"
    orows = obr.parse(p, FileMeta(osrc, f, f.sha256, f.file_url, "2026-10-15T00:00:00Z", p))
    results = _rule(_run(_bn(prows + orows)), "R3")
    assert {r["fiscal_year"] for r in results} >= {"2020-21", "2021-22", "2024-25", "2025-26"}
    assert all(r["status"] == "pass" for r in results), [
        r for r in results if r["status"] != "pass"
    ]
    assert all(r["left"]["provenance_id"] and r["right"]["provenance_id"] for r in results)


def test_broken_pesa_fixture_produces_fail_record_with_delta(pesa_rows, tmp_path):
    src, _, by_sha = pesa_rows
    f = next(x for x in src.files if x.key == "pesa_2026_ch10")
    wb = openpyxl.load_workbook(by_sha[f.sha256])
    ws = wb["10.1"]
    assert ws["F124"].value == 769898.0
    ws["F124"] = 769898.0 + 1000.0  # inflate the 2024-25 total by GBP 1bn
    bad = tmp_path / "broken.xlsx"
    wb.save(bad)
    rows = pesa.parse(bad, FileMeta(src, f, f.sha256, f.file_url, "2026-10-15T00:00:00Z", bad))
    results = _rule(_run(_bn(rows)), "R1")  # must not raise
    by_year = {r["fiscal_year"]: r for r in results}
    assert len(by_year) == 5
    broken = by_year["2024-25"]
    assert broken["status"] == "fail"
    assert broken["delta"] == pytest.approx(-1.0, abs=0.01)
    assert broken["right"]["provenance_id"] == "pesa.cofog.total_services@PESA 2026/2024-25"
    assert all(r["status"] == "pass" for fy, r in by_year.items() if fy != "2024-25")
