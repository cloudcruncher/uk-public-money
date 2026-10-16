"""check-api: validate a built static API directory against the ARCHITECTURE.md contract.

Usage: python -m ukpm check-api DIR [--live]. Exit 1 with a list of violations.
Every point must reference a complete provenance record (the same gate the builder uses), with an
https source_url on an allowlisted host. `--live` also rejects fixture-based records.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import duckdb

from .provenance import Provenance, Transformation, problems

REQUIRED_FILES = (
    "index.json",
    "reconciliation.json",
    "definitions.json",
    "claims.json",
    "corrections.json",
    "observations.parquet",
    "observations_all_vintages.parquet",
    "provenance.parquet",
    "reconciliation.parquet",
    "glossary.json",
    "shares.json",
    "benefits/index.json",
    "cabinet_office/summary.json",
)
RULE_IDS = [f"R{i}" for i in range(1, 15)]
VARIANTS = {
    "nominal",
    "real",
    "pct_gdp",
    "per_person",
    "per_person_real",
    "per_household",
    "per_household_real",
    "per_100",
}
SLUG_RE = re.compile(r"^[a-z0-9-]+$")
FIGURE_RE = re.compile(r"£\s?\d|\d\s?%|\d[\d,]*\s?(million|billion|bn|m)\b")
PER_100_TOTALS = {
    "pesa.cofog.total_services",
    "pesa_uk.services",
    "hmrc_receipts.total",
    "ons_psf.cg_receipts",
}
FORBIDDEN_CO_KEYS = {"ref", "transaction_number", "date", "expense_area"}
CO_MAX_BYTES = 262144
CO_MAX_PROVENANCE_BYTES = 1048576
STATUSES = {"pass", "fail", "info", "not_run"}
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
INDEX_KEYS = ("api_version", "generated_at", "build", "fiscal_years", "sources", "series", "files")
SERIES_KEYS = ("id", "title", "source_id", "period_type", "variants", "gaps", "notes")
POINT_KEYS = ("fiscal_year", "value", "unit", "status", "vintage", "provenance_id")
PROV_FIELDS = (
    "publisher",
    "dataset",
    "edition",
    "publication_date",
    "source_url",
    "landing_url",
    "file_sha256",
    "sheet",
    "cell_or_range",
    "api_query",
    "licence",
    "transformations",
    "status",
    "vintage",
    "retrieved_at",
)


def _load(path: Path, errs: list[str]) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as e:
        errs.append(f"{path.name}: cannot read as JSON ({e})")
        return None


def _as_prov(rec: dict[str, Any]) -> Provenance:
    trans = tuple(
        Transformation(t["op"], t["detail"], tuple(t.get("inputs", [])))
        for t in rec.get("transformations") or []
    )
    return Provenance(**{**{k: rec.get(k) for k in PROV_FIELDS}, "transformations": trans})


def _walk_values(obj: Any, where: str, records: dict[str, dict[str, Any]], errs: list[str]) -> None:
    """Every dict with a `value` key must resolve to a complete provenance record."""
    if isinstance(obj, dict):
        if "value" in obj:
            pid = obj.get("provenance_id")
            rec = records.get(pid) if isinstance(pid, str) else None
            v = obj["value"]
            if rec is None:
                errs.append(f"{where}: value has no resolvable provenance_id")
            elif not isinstance(v, int | float) or isinstance(v, bool) or not math.isfinite(v):
                errs.append(f"{where}: value not a finite number")
            elif rec.get("status") != obj.get("status"):
                errs.append(f"{where}: status differs from its provenance record")
        for k, v in obj.items():
            if k != "value":
                _walk_values(v, f"{where}.{k}", records, errs)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_values(v, f"{where}[{i}]", records, errs)


def _keys(obj: Any):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


def _pids(obj: Any):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "provenance_id" and isinstance(v, str):
                yield v
            else:
                yield from _pids(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _pids(v)


def _input_series(rec: dict[str, Any], records: dict[str, dict[str, Any]]) -> list[str]:
    return [str(records[i].get("series_id") or "") for i in rec.get("inputs") or [] if i in records]


def _check_layman(root: Path, records: dict[str, dict[str, Any]], errs: list[str]) -> None:
    # shares
    shares = _load(root / "shares.json", errs)
    if isinstance(shares, dict) and isinstance(shares.get("sets"), list):
        _walk_values(shares, "shares.json", records, errs)
        for st in shares["sets"]:
            if st.get("available") is False:
                continue
            tot = sum(p["per_100"]["value"] for p in st.get("parts", []))
            tot += (st.get("other") or {}).get("value", 0.0)
            if abs(tot - 100) > 1e-9 or not st.get("other"):
                errs.append(f"shares.json: set {st.get('id')} adds up to {tot}, not 100")
            if st.get("role") not in ("primary", "fallback"):
                errs.append(f"shares.json: set {st.get('id')} has no role (primary or fallback)")
            if st.get("role") == "fallback" and not st.get("superseded_by"):
                errs.append(
                    f"shares.json: fallback set {st.get('id')} says nothing about its successor"
                )
            for part in st.get("parts", []):
                ph = part.get("per_household")
                rec = records.get((ph or {}).get("provenance_id", "")) if ph else None
                if ph and (rec is None or "ons_households.uk" not in _input_series(rec, records)):
                    errs.append(
                        f"shares.json: {part.get('series_id')} per_household lacks household input"
                    )
    else:
        errs.append("shares.json: bad shape")
    # index blocks that describe the denominators
    idx = _load(root / "index.json", errs)
    if isinstance(idx, dict):
        ids = {e["id"] for e in idx.get("series", [])}
        phb = idx.get("per_household")
        if not isinstance(phb, dict) or not isinstance(phb.get("available"), bool):
            errs.append("index.json: per_household block is missing or has no 'available'")
        elif phb["available"] and phb.get("series_id") not in ids:
            errs.append("index.json: per_household.series_id is not a published series")
        gdpb = idx.get("gdp")
        if not isinstance(gdpb, dict) or not {"fiscal_year", "calendar_year"} <= set(gdpb):
            errs.append("index.json: gdp block must describe fiscal_year and calendar_year GDP")
        elif (gdpb["calendar_year"] or {}).get("used_for") is not None:
            errs.append("index.json: calendar-year GDP must not be used as a divisor")
        dib = idx.get("debt_interest")
        if not isinstance(dib, dict) or not isinstance(dib.get("available"), bool):
            errs.append("index.json: debt_interest block is missing or has no 'available'")
        elif dib["available"] and dib.get("series_id") not in ids:
            errs.append("index.json: debt_interest.series_id is not a published series")
    # benefits
    ben = _load(root / "benefits" / "index.json", errs)
    if isinstance(ben, dict) and isinstance(ben.get("benefits"), list):
        _walk_values(ben, "benefits/index.json", records, errs)
        for b in ben["benefits"]:
            slug = str(b.get("slug", ""))
            path = root / str(b.get("path", ""))
            if not SLUG_RE.match(slug):
                errs.append(f"benefits/index.json: bad slug {slug!r}")
            if not path.is_file():
                errs.append(f"benefits/index.json: {b.get('path')} does not exist")
                continue
            data = _load(path, errs)
            if isinstance(data, dict):
                _walk_values(data, f"benefits/{slug}.json", records, errs)
                for p in data.get("cost_per_claimant", []):
                    rec = records.get(p.get("provenance_id", ""))
                    if rec is not None and not any(
                        x.startswith("dwp_benefits.caseload.") for x in _input_series(rec, records)
                    ):
                        errs.append(
                            f"benefits/{slug}.json: cost_per_claimant lacks a caseload input"
                        )
    else:
        errs.append("benefits/index.json: bad shape")
    # glossary
    g = _load(root / "glossary.json", errs)
    if isinstance(g, dict) and isinstance(g.get("terms"), list):
        ids = [t.get("id") for t in g["terms"]]
        if len(set(ids)) != len(ids):
            errs.append("glossary.json: duplicate ids")
        for t in g["terms"]:
            for k in (
                "id",
                "term",
                "aliases",
                "plain",
                "long",
                "see_also",
                "source_id",
                "checker_only",
            ):
                if k not in t:
                    errs.append(f"glossary.json: {t.get('id')} missing {k}")
            for ref in t.get("see_also") or []:
                if ref not in ids:
                    errs.append(f"glossary.json: {t.get('id')} see_also {ref} does not exist")
            for k in ("plain", "long"):
                if FIGURE_RE.search(str(t.get(k, ""))):
                    errs.append(f"glossary.json: {t.get('id')} {k} contains a figure")
    else:
        errs.append("glossary.json: bad shape")
    # Cabinet Office
    cp = root / "cabinet_office" / "summary.json"
    co = _load(cp, errs)
    if not isinstance(co, dict):
        return
    if cp.stat().st_size > CO_MAX_BYTES:
        errs.append(
            f"cabinet_office/summary.json: {cp.stat().st_size} bytes exceeds {CO_MAX_BYTES}"
        )
    pp = root / "provenance" / "cabinet_office_spend.json"
    if pp.exists() and pp.stat().st_size > CO_MAX_PROVENANCE_BYTES:
        errs.append(f"provenance/cabinet_office_spend.json exceeds {CO_MAX_PROVENANCE_BYTES} bytes")
    bad_keys = {str(k).lower() for k in _keys(co)} & FORBIDDEN_CO_KEYS
    if bad_keys:
        errs.append(f"cabinet_office/summary.json: forbidden keys {sorted(bad_keys)}")
    if co.get("available") is False:
        return
    _walk_values(co, "cabinet_office/summary.json", records, errs)
    caps = co.get("caps") or {}
    if len(co.get("months", [])) > caps.get("months", 24):
        errs.append("cabinet_office/summary.json: too many months")
    for m in co.get("months", []):
        if len(m.get("expense_types", [])) > caps.get("expense_types_per_month", 10):
            errs.append(f"cabinet_office/summary.json: too many expense types in {m.get('month')}")
    sup = co.get("top_suppliers", [])
    if len(sup) > caps.get("suppliers", 20):
        errs.append("cabinet_office/summary.json: too many suppliers")
    for x in sup:
        if (x.get("point") or {}).get("value", 0) < caps.get("supplier_floor_gbp", 1_000_000):
            errs.append(f"cabinet_office/summary.json: supplier {x.get('name')} is below the floor")
    # no orphan supplier records
    referenced = set(_pids(co))
    reach = set(referenced)
    for pid in referenced:
        reach.update((records.get(pid) or {}).get("inputs") or [])
    for pid, rec in records.items():
        if rec.get("source_id") != "cabinet_office_spend":
            continue
        parts = str(rec.get("series_id", "")).split(".")
        if len(parts) > 1 and parts[1] == "supplier" and pid not in reach:
            errs.append(f"{pid}: orphan supplier record (not referenced by summary.json)")


def check(root: Path, live: bool = False) -> list[str]:
    errs: list[str] = []
    for f in REQUIRED_FILES:
        p = root / f
        if not p.is_file() or p.stat().st_size == 0:
            errs.append(f"{f}: missing or empty")
    if errs:
        return errs
    for f in REQUIRED_FILES:
        if f.endswith(".parquet"):
            try:
                duckdb.connect().execute(
                    f"SELECT count(*) FROM read_parquet('{root / f}')"
                ).fetchone()
            except duckdb.Error as e:
                errs.append(f"{f}: unreadable parquet ({e})")

    index = _load(root / "index.json", errs)
    recon = _load(root / "reconciliation.json", errs)
    defs = _load(root / "definitions.json", errs)
    claims = _load(root / "claims.json", errs)
    corr = _load(root / "corrections.json", errs)
    if not isinstance(index, dict):
        return errs
    for k in INDEX_KEYS:
        if k not in index:
            errs.append(f"index.json: missing {k}")
    if errs:
        return errs

    build = index["build"]
    if build.get("rejected", 0) and (live or build.get("mode") == "live"):
        errs.append(f"index.json: {build['rejected']} values rejected by the provenance gate")
    if live and build.get("mode") != "live":
        errs.append("index.json: --live requires a live build")

    # provenance records
    records: dict[str, dict[str, Any]] = {}
    for src in {s["id"] for s in index["sources"]}:
        p = root / "provenance" / f"{src}.json"
        if not p.exists():
            continue
        data = _load(p, errs)
        if not isinstance(data, dict) or "records" not in data:
            errs.append(f"provenance/{src}.json: bad shape")
            continue
        for pid, rec in data["records"].items():
            records[pid] = rec
            if rec.get("provenance_id") != pid or not pid.startswith(f"{src}."):
                errs.append(f"{pid}: id does not match file or key")
            try:
                bad = problems(_as_prov(rec))
            except (TypeError, KeyError) as e:
                bad = [f"malformed record ({e})"]
            if bad:
                errs.append(f"{pid}: incomplete provenance: {'; '.join(bad)}")
            if not str(rec.get("source_url", "")).startswith("https://"):
                errs.append(f"{pid}: source_url not https")
            if not SHA_RE.match(str(rec.get("file_sha256", ""))):
                errs.append(f"{pid}: file_sha256 not 64 hex")
            if not isinstance(rec.get("check"), dict) or "kind" not in rec["check"]:
                errs.append(f"{pid}: missing check block")
            for i in rec.get("inputs") or []:
                if (
                    i not in records
                    and not (root / "provenance" / f"{i.split('.')[0]}.json").exists()
                ):
                    errs.append(f"{pid}: input {i} has no provenance file")
            if live and rec.get("retrieval") == "fixture":
                errs.append(f"{pid}: retrieval is fixture in a --live check")

    for pid, rec in records.items():
        for i in rec.get("inputs") or []:
            if i not in records:
                errs.append(f"{pid}: derived input {i} does not resolve")

    # series files
    points: dict[tuple[str, str, str], dict[str, Any]] = {}
    ids_in_index = set()
    for entry in index["series"]:
        sid = entry["id"]
        ids_in_index.add(sid)
        s = _load(root / entry["path"], errs) if (root / entry["path"]).exists() else None
        if s is None:
            errs.append(f"{sid}: series file missing at {entry['path']}")
            continue
        for k in SERIES_KEYS:
            if k not in s:
                errs.append(f"{sid}: series file missing {k}")
        variants = s.get("variants", {})
        if "nominal" not in variants:
            errs.append(f"{sid}: no nominal variant")
        if entry.get("headline") and entry.get("monetary"):
            need = {"nominal", "pct_gdp"} | ({"real"} if index.get("real_base_year") else set())
            for v in sorted(need - set(variants)):
                errs.append(f"{sid}: headline series lacks the {v} variant")
        if s.get("period_type") in ("calendar_year", "may_snapshot") and set(variants) != {
            "nominal"
        }:
            errs.append(f"{sid}: calendar-year series must be nominal only, not converted")
        for v, pts in variants.items():
            if v not in VARIANTS:
                errs.append(f"{sid}: unknown variant {v}")
            if v != "nominal" and not s.get("monetary"):
                errs.append(f"{sid}: non-monetary series has a {v} variant")
            for p in pts:
                for k in POINT_KEYS:
                    if k not in p:
                        errs.append(f"{sid}/{v}/{p.get('fiscal_year')}: point missing {k}")
                if not isinstance(p.get("value"), int | float) or not math.isfinite(p["value"]):
                    errs.append(f"{sid}/{v}/{p.get('fiscal_year')}: value not a finite number")
                rec = records.get(p.get("provenance_id", ""))
                if rec is None:
                    errs.append(f"{sid}/{v}/{p.get('fiscal_year')}: provenance_id does not resolve")
                    continue
                if rec["status"] != p.get("status"):
                    errs.append(f"{sid}/{v}/{p['fiscal_year']}: point status differs from record")
                if rec["status"] == "forecast" and p.get("status") != "forecast":
                    errs.append(f"{sid}/{v}/{p['fiscal_year']}: forecast not marked forecast")
                if v != "nominal" and not rec.get("inputs"):
                    errs.append(f"{sid}/{v}/{p['fiscal_year']}: derived value lists no inputs")
                if v.startswith("per_person") and not any(
                    x.startswith("ons_population.") for x in _input_series(rec, records)
                ):
                    errs.append(
                        f"{sid}/{v}/{p['fiscal_year']}: per-person value lacks a population input"
                    )
                if v.startswith("per_household") and not any(
                    x == "ons_households.uk" for x in _input_series(rec, records)
                ):
                    errs.append(
                        f"{sid}/{v}/{p['fiscal_year']}: per-household value lacks a household input"
                    )
                if v == "per_100" and not any(
                    x in PER_100_TOTALS for x in _input_series(rec, records)
                ):
                    errs.append(
                        f"{sid}/{v}/{p['fiscal_year']}: per_100 value lacks its total as input"
                    )
                points[(sid, v, p["fiscal_year"])] = p

    # reconciliation
    if not isinstance(recon, dict) or "rules" not in recon or "summary" not in recon:
        errs.append("reconciliation.json: bad shape")
    else:
        got = [r.get("id") for r in recon["rules"]]
        for rid in RULE_IDS:
            if rid not in got:
                errs.append(f"reconciliation.json: rule {rid} missing")
        for rule in recon["rules"]:
            if not rule.get("results"):
                errs.append(f"reconciliation.json: {rule.get('id')} has no results")
            for r in rule.get("results", []):
                if r.get("status") not in STATUSES:
                    errs.append(f"reconciliation.json: {rule['id']} bad status {r.get('status')}")
                if r.get("status") == "not_run" and not r.get("reason"):
                    errs.append(f"reconciliation.json: {rule['id']} not_run without a reason")
                for side in ("left", "right"):
                    for pid in (r.get(side) or {}).get("provenance_ids", []):
                        if pid not in records:
                            errs.append(f"reconciliation.json: {rule['id']} {pid} does not resolve")

    if not isinstance(defs, dict) or "groups" not in defs:
        errs.append("definitions.json: bad shape")
    else:
        for g in defs["groups"]:
            for d in g.get("definitions", []):
                if d.get("series_id") and d["series_id"] not in ids_in_index:
                    errs.append(f"definitions.json: {d['id']} points at unknown series")

    if not isinstance(corr, dict) or not isinstance(corr.get("corrections"), list):
        errs.append("corrections.json: bad shape")

    if not isinstance(claims, dict) or not isinstance(claims.get("claims"), list):
        errs.append("claims.json: bad shape")
    else:
        for c in claims["claims"]:
            if c.get("verdict") == "no_official_figure":
                continue
            off = c.get("official") or {}
            sid, fy, basis = (
                c["maps_to"]["series_id"],
                c["claimed"]["fiscal_year"],
                c["claimed"]["price_basis"],
            )
            p = points.get((sid, basis, fy))
            if (
                not p
                or p["provenance_id"] != off.get("provenance_id")
                or p["value"] != off.get("value")
            ):
                errs.append(f"claims.json: {c['id']} does not resolve to a real point")
            if not str(c.get("said_url", "")).startswith("https://"):
                errs.append(f"claims.json: {c['id']} said_url not https")
    _check_layman(root, records, errs)
    return errs


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="ukpm check-api")
    ap.add_argument("dir", nargs="?", default="site/api/v1")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args(argv)
    errs = check(Path(args.dir), live=args.live)
    if errs:
        print(f"check-api: {len(errs)} violation(s)", file=sys.stderr)
        for e in errs[:200]:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"check-api: {args.dir} ok")
    return 0
