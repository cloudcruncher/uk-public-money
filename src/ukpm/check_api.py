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
)
RULE_IDS = [f"R{i}" for i in range(1, 8)]
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
        for v, pts in variants.items():
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
