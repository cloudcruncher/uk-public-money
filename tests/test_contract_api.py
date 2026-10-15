"""Contract tests for the static API (docs/ARCHITECTURE.md section 10).

An offline build is made once per session into a tmp dir, then inspected and tampered with.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from ukpm import build, check_api
from ukpm.__main__ import main as cli_main

ROOT = Path(__file__).resolve().parent.parent
SHA = re.compile(r"^[0-9a-f]{64}$")
PROV_KEYS = (
    "provenance_id",
    "publisher",
    "dataset",
    "publication_date",
    "source_url",
    "file_sha256",
    "licence",
    "status",
    "vintage",
    "check",
)


@pytest.fixture(scope="session")
def api(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("api") / "v1"
    import os

    cwd = os.getcwd()
    os.chdir(ROOT)  # build reads data/*.yml relative to the repo root
    mp = pytest.MonkeyPatch()
    mp.setattr(build, "WORK", tmp_path_factory.mktemp("work"))  # ignore any real work/raw
    try:
        rc = cli_main(["build", "--offline", "--out", str(out)])
    finally:
        mp.undo()
        os.chdir(cwd)
    assert rc == 0
    return out


def J(p: Path):
    return json.loads(p.read_text())


@pytest.fixture(scope="session")
def index(api):
    return J(api / "index.json")


@pytest.fixture(scope="session")
def records(api, index):
    recs = {}
    for s in index["sources"]:
        f = api / "provenance" / f"{s['id']}.json"
        if f.exists():
            d = J(f)
            assert d["source_id"] == s["id"]
            recs.update(d["records"])
    return recs


@pytest.fixture(scope="session")
def series(api, index):
    return {e["id"]: J(api / e["path"]) for e in index["series"]}


@pytest.fixture
def tampered(api, tmp_path):
    dst = tmp_path / "v1"
    shutil.copytree(api, dst)
    return dst


# ---- shapes ----------------------------------------------------------------------------------


def test_check_api_passes_on_clean_build(api):
    assert check_api.check(api) == []
    assert cli_main(["check-api", str(api)]) == 0


def test_index_shape(index):
    assert index["api_version"] == "v1"
    for k in ("generated_at", "build", "fiscal_years", "sources", "series", "files"):
        assert k in index
    assert index["build"]["mode"] == "offline"
    assert index["build"]["rejected"] == 0
    assert index["real_base_year"]
    assert index["deflator"]["series_id"] == "obr.gdp_deflator"
    assert index["series"] and index["sources"]
    for e in index["series"]:
        for k in ("id", "title", "unit", "source_id", "period_type", "monetary", "path"):
            assert k in e


def test_series_file_shape(api, index, series):
    for e in index["series"]:
        s = series[e["id"]]
        assert s["id"] == e["id"]
        for k in ("title", "source_id", "period_type", "variants", "gaps", "notes"):
            assert k in s
        assert "nominal" in s["variants"]
        assert set(s["variants"]) <= {"nominal", "real", "pct_gdp"}
        for pts in s["variants"].values():
            for p in pts:
                for k in ("fiscal_year", "value", "unit", "status", "vintage", "provenance_id"):
                    assert k in p
                assert re.match(r"^\d{4}-\d{2}$", p["fiscal_year"])
                assert p["status"] in ("outturn", "forecast")


def test_non_monetary_series_have_only_nominal(series):
    for s in series.values():
        if not s["monetary"]:
            assert set(s["variants"]) == {"nominal"}, s["id"]


def test_auxiliary_files(api):
    d = J(api / "definitions.json")
    assert isinstance(d["groups"], list)
    c = J(api / "corrections.json")
    assert isinstance(c["corrections"], list)
    cl = J(api / "claims.json")
    assert isinstance(cl["claims"], list)
    for f in (
        "observations.parquet",
        "observations_all_vintages.parquet",
        "provenance.parquet",
        "reconciliation.parquet",
    ):
        assert (api / f).stat().st_size > 0


# ---- provenance ------------------------------------------------------------------------------


def test_every_observation_resolves_to_complete_provenance(series, records):
    n = 0
    for s in series.values():
        for pts in s["variants"].values():
            for p in pts:
                rec = records.get(p["provenance_id"])
                assert rec is not None, (s["id"], p)
                assert p["provenance_id"].split(".")[0] == s["source_id"] or rec.get("inputs")
                for k in PROV_KEYS:
                    assert rec.get(k) not in (None, ""), (p["provenance_id"], k)
                assert rec["source_url"].startswith("https://")
                assert SHA.match(rec["file_sha256"])
                assert rec["status"] == p["status"]
                assert rec["check"].get("kind") in ("spreadsheet", "api", "derived")
                n += 1
    assert n > 1000


def test_all_records_are_https_and_sha256(records):
    assert records
    for pid, rec in records.items():
        assert rec["provenance_id"] == pid
        assert rec["source_url"].startswith("https://"), pid
        assert SHA.match(rec["file_sha256"]), pid


def test_derived_values_list_inputs_that_resolve(series, records):
    seen = 0
    for s in series.values():
        for v, pts in s["variants"].items():
            if v == "nominal":
                continue
            for p in pts:
                inputs = records[p["provenance_id"]].get("inputs")
                assert inputs, (s["id"], v, p["fiscal_year"])
                for i in inputs:
                    assert i in records
                seen += 1
    assert seen > 0


# ---- variants and forecasts ------------------------------------------------------------------


def test_headline_series_have_nominal_real_and_pct_gdp(index, series):
    headline = [e for e in index["series"] if e.get("headline")]
    assert {e["id"] for e in headline} >= {"pesa.tme", "obr.psf.tme", "obr.psf.receipts"}
    for e in headline:
        if e["monetary"]:
            assert {"nominal", "real", "pct_gdp"} <= set(series[e["id"]]["variants"]), e["id"]


def test_variant_units(series):
    for sid in ("pesa.tme", "obr.psf.tme"):
        v = series[sid]["variants"]
        assert all(p["unit"] == "GBP_bn" for p in v["nominal"])
        assert all(p["unit"].startswith("GBP_bn_") for p in v["real"])
        assert all(p["unit"] == "percent" for p in v["pct_gdp"])


def test_real_equals_nominal_in_base_year(index, series):
    base = index["real_base_year"]
    v = series["obr.psf.tme"]["variants"]
    nom = {p["fiscal_year"]: p["value"] for p in v["nominal"]}
    real = {p["fiscal_year"]: p["value"] for p in v["real"]}
    assert base in real
    assert real[base] == pytest.approx(nom[base], rel=1e-6)


def test_forecast_rows_are_labelled(series, records):
    forecasts = [
        (s["id"], p)
        for s in series.values()
        for pts in s["variants"].values()
        for p in pts
        if p["status"] == "forecast"
    ]
    assert forecasts, "OBR/DWP forecast years expected in the offline build"
    for _, p in forecasts:
        assert records[p["provenance_id"]]["status"] == "forecast"
    for s in series.values():
        for pts in s["variants"].values():
            for p in pts:
                if records[p["provenance_id"]]["status"] == "forecast":
                    assert p["status"] == "forecast"


def test_obr_series_forecast_years_come_after_outturn(series):
    pts = series["obr.psf.tme"]["variants"]["nominal"]
    seen_forecast = False
    for p in sorted(pts, key=lambda x: x["fiscal_year"]):
        if p["status"] == "forecast":
            seen_forecast = True
        else:
            assert not seen_forecast, "outturn after forecast"


# ---- reconciliation --------------------------------------------------------------------------


def test_reconciliation_lists_all_rules_including_failures(api):
    r = J(api / "reconciliation.json")
    ids = [x["id"] for x in r["rules"]]
    # ARCHITECTURE.md section 10 and check_api.RULE_IDS define R1..R7
    assert ids == [f"R{i}" for i in range(1, 8)]
    statuses = [res["status"] for x in r["rules"] for res in x["results"]]
    assert set(statuses) <= {"pass", "fail", "info", "not_run"}
    assert "fail" in statuses, "failures must be published, not hidden"
    assert "pass" in statuses
    for k in ("pass", "fail", "info", "not_run"):
        assert r["summary"][k] == statuses.count(k)
    for x in r["rules"]:
        for k in ("title", "description", "tolerance"):
            assert k in x
        assert x["results"], x["id"]
        for res in x["results"]:
            assert "fiscal_year" in res and "left" in res and "right" in res
            if res["status"] == "not_run":
                assert res["reason"]


def test_reconciliation_provenance_resolves(api, records):
    r = J(api / "reconciliation.json")
    for x in r["rules"]:
        for res in x["results"]:
            for side in ("left", "right"):
                ids = list((res[side] or {}).get("provenance_ids") or [])
                pid = (res[side] or {}).get("provenance_id")
                if pid:
                    ids.append(pid)
                for i in ids:
                    assert i in records


# ---- claims ----------------------------------------------------------------------------------


def test_claims_resolve_to_real_series_values(api, series):
    for c in J(api / "claims.json")["claims"]:
        if c["verdict"] == "no_official_figure":
            continue
        pts = series[c["maps_to"]["series_id"]]["variants"][c["claimed"]["price_basis"]]
        match = [p for p in pts if p["fiscal_year"] == c["claimed"]["fiscal_year"]]
        assert match
        assert match[0]["value"] == c["official"]["value"]
        assert match[0]["provenance_id"] == c["official"]["provenance_id"]
        assert c["check_url"] == f"check.html#p={c['official']['provenance_id']}"


def test_claims_evaluate_resolves_against_built_point(series):
    from ukpm import claims

    pt = series["obr.psf.tme"]["variants"]["nominal"][0]

    def lookup(sid, basis, fy):
        if (sid, basis, fy) == ("obr.psf.tme", "nominal", pt["fiscal_year"]):
            return pt, "TME"
        return None

    base = {
        "id": "c1",
        "text": "t",
        "said_url": "https://example.org/x",
        "claimed": {
            "value": pt["value"],
            "unit": "GBP_bn",
            "fiscal_year": pt["fiscal_year"],
            "price_basis": "nominal",
        },
        "maps_to": {"series_id": "obr.psf.tme"},
    }
    bad_url = {**base, "id": "c2", "said_url": "http://insecure"}
    out = claims.evaluate([base, bad_url], lookup, {})
    assert out["claims"][0]["verdict"] == "consistent"
    assert out["claims"][0]["official"]["provenance_id"] == pt["provenance_id"]
    assert out["claims"][0]["check_url"] == f"check.html#p={pt['provenance_id']}"
    assert [r["id"] for r in out["rejected"]] == ["c2"]


# ---- gate and tamper detection ---------------------------------------------------------------


def test_gate_drops_values_with_missing_provenance(make_row):
    good = make_row()
    no_sha = make_row(file_sha256="")
    http = make_row(source_url="http://assets.publishing.service.gov.uk/x.xlsx")
    nan = replace(make_row(), value=float("nan"))
    ok, rejected = build.gate([good, no_sha, http, nan])
    assert ok == [good]
    assert len(rejected) == 3


def test_injected_bad_row_is_rejected_by_full_build(api, tmp_path, monkeypatch, make_row):
    real_collect = build.collect

    def collect(*a, **kw):
        rows, *rest = real_collect(*a, **kw)
        bad = make_row(series="bogus.series", file_sha256="")
        return (rows + [bad], *rest)

    monkeypatch.setattr(build, "collect", collect)
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(build, "WORK", tmp_path / "work")
    out = tmp_path / "v1"
    assert build.main(["--offline", "--out", str(out)]) == 0
    idx = J(out / "index.json")
    assert idx["build"]["rejected"] >= 1
    assert "bogus.series" not in {e["id"] for e in idx["series"]}
    assert not (out / "series" / "bogus.series.json").exists()


def test_check_api_fails_on_removed_provenance_record(tampered, records):
    f = next(tampered.glob("provenance/pesa.json"))
    d = J(f)
    pid = next(iter(d["records"]))
    del d["records"][pid]
    f.write_text(json.dumps(d))
    errs = check_api.check(tampered)
    assert any("does not resolve" in e for e in errs)
    assert cli_main(["check-api", str(tampered)]) == 1


def test_check_api_fails_on_bad_sha_and_http_url(tampered):
    f = tampered / "provenance" / "pesa.json"
    d = J(f)
    pids = list(d["records"])
    d["records"][pids[0]]["file_sha256"] = "abc"
    d["records"][pids[1]]["source_url"] = "http://assets.publishing.service.gov.uk/x.xlsx"
    f.write_text(json.dumps(d))
    errs = check_api.check(tampered)
    assert any("64 hex" in e for e in errs)
    assert any("not https" in e for e in errs)


def test_check_api_fails_on_point_with_unknown_provenance_id(tampered):
    f = tampered / "series" / "pesa.tme.json"
    s = J(f)
    s["variants"]["nominal"][0]["provenance_id"] = "pesa.0000000000000000"
    f.write_text(json.dumps(s))
    assert any("does not resolve" in e for e in check_api.check(tampered))


def test_check_api_fails_when_forecast_unlabelled(tampered):
    f = tampered / "series" / "obr.psf.tme.json"
    s = J(f)
    p = next(p for p in s["variants"]["nominal"] if p["status"] == "forecast")
    p["status"] = "outturn"
    f.write_text(json.dumps(s))
    assert any("status differs" in e for e in check_api.check(tampered))


def test_check_api_fails_when_headline_variant_missing(tampered):
    f = tampered / "series" / "pesa.tme.json"
    s = J(f)
    del s["variants"]["real"]
    f.write_text(json.dumps(s))
    assert any("lacks the real variant" in e for e in check_api.check(tampered))


def test_check_api_fails_when_rule_missing(tampered):
    f = tampered / "reconciliation.json"
    r = J(f)
    r["rules"] = [x for x in r["rules"] if x["id"] != "R3"]
    f.write_text(json.dumps(r))
    assert any("rule R3 missing" in e for e in check_api.check(tampered))


def test_check_api_fails_on_claim_that_does_not_resolve(tampered):
    f = tampered / "claims.json"
    f.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "id": "x",
                        "verdict": "consistent",
                        "said_url": "https://example.org",
                        "maps_to": {"series_id": "pesa.tme"},
                        "claimed": {"fiscal_year": "2015-16", "price_basis": "nominal"},
                        "official": {"provenance_id": "pesa.nope", "value": 1},
                    }
                ]
            }
        )
    )
    assert any("does not resolve to a real point" in e for e in check_api.check(tampered))


def test_check_api_fails_on_missing_file(tampered):
    (tampered / "claims.json").unlink()
    assert any("claims.json: missing" in e for e in check_api.check(tampered))


def test_check_api_live_rejects_fixture_offline_build(api):
    errs = check_api.check(api, live=True)
    assert any("--live requires a live build" in e for e in errs)
    assert any("fixture" in e for e in errs)


def test_cli_check_api_live_flag_on_offline_build(api, capsys):
    assert cli_main(["check-api", str(api), "--live"]) == 1
    assert "requires a live build" in capsys.readouterr().err
