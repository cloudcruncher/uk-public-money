"""build: parse -> provenance gate -> stitch -> conversions -> reconcile -> write site/api/v1.

Every published value comes from a parsed row with a complete provenance record. Rows that fail
the gate are dropped, logged to work/rejected.jsonl and counted in index.json (build.rejected).
`--offline` resolves files from work/raw (matching sha256) or the committed fixtures under
tests/fixtures and never touches the network. The API directory is written to a temporary
sibling and swapped in at the end.
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib
import json
import math
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import yaml

from . import claims as claims_mod
from . import fetch as fetch_mod
from . import reconcile, units
from .parsers import FileMeta, LayoutError
from .provenance import Row, problems, provenance_id
from .registry import FileEntry, Source, load

SOURCES = Path("data/sources.yml")
DEFINITIONS = Path("data/definitions.yml")
CLAIMS = Path("data/claims.yml")
CORRECTIONS = Path("data/corrections.yml")
WORK = Path("work")
FIRST_YEAR = "2015-16"
# Fixtures are trimmed copies of files fetched on this date (see tests/fixtures/*/SOURCE.txt).
FIXTURE_RETRIEVED_AT = "2026-10-15T00:00:00Z"
LICENCE_URLS = {
    "OGL-UK-3.0": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
}
UNIT_LABEL = {
    "gbp_m": "GBP_m",
    "gbp_bn": "GBP_bn",
    "thousand_persons": "thousand_persons",
    "persons": "persons",
    "index": "index",
    "percent": "percent",
}
HEADLINE = (
    "pesa.tme",
    "obr.psf.tme",
    "obr.psf.receipts",
    "hmrc_receipts.total",
    "dwp_benefits.total_uk_welfare",
)
GROUP_BY_SOURCE = {
    "dwp_benefits": ("welfare", "Welfare"),
    "pesa": ("spending", "Public spending"),
    "obr": ("receipts", "Receipts and the public finances"),
    "hmrc_receipts": ("receipts", "Receipts and the public finances"),
    "hmrc_income_tax": ("receipts", "Receipts and the public finances"),
}

_SHA_LINE = re.compile(r"original sha256\s+([0-9a-f]{64})")
_FILE_LINE = re.compile(r"^(\S+\.(?:xlsx|ods|csv))\b")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def pub_id(row: Row) -> str:
    """Published provenance id '<source_id>.<12 hex>' (core ids use '-' as the separator)."""
    return _pub(provenance_id(row.series_id.split(".")[0], row.prov))


def _pub(core_id: str) -> str:
    return core_id.replace("-", ".", 1)


# --------------------------------------------------------------------------- file resolution


def _fixture_path(src: Source, f: FileEntry) -> Path | None:
    hit = fetch_mod._fixture(src, f)
    if hit is not None:
        return hit
    if not src.fixture_dir:
        return None
    note = Path(src.fixture_dir) / "SOURCE.txt"
    if not note.exists():
        return None
    current = None
    for line in note.read_text().splitlines():
        m = _FILE_LINE.match(line)
        if m:
            current = m.group(1)
        s = _SHA_LINE.search(line)
        if s and current and s.group(1) == f.sha256:
            p = note.parent / current
            return p if p.exists() else None
    return None


def _resolve_files(
    src: Source, offline: bool
) -> tuple[list[tuple[FileEntry, Path, str, str]], list[str]]:
    """Return ([(file, path, retrieval, retrieved_at)], problems) for one source."""
    out, bad = [], []
    if offline:
        for f in src.files:
            cached = fetch_mod._cache_path(WORK, src, f)
            if cached.exists() and fetch_mod.sha256_file(cached) == f.sha256:
                info = fetch_mod._load_manifest(WORK).get(f.sha256, {})
                out.append((f, cached, "cache", info.get("fetched_at") or _now()))
                continue
            fx = _fixture_path(src, f)
            if fx is None:
                bad.append(f"{f.key}: no offline copy (no cache, no fixture)")
            else:
                out.append((f, fx, "fixture", FIXTURE_RETRIEVED_AT))
        return out, bad
    had = {f.key: fetch_mod._cache_path(WORK, src, f).exists() for f in src.files}
    try:
        fetched = fetch_mod.fetch_source(src, offline=False)
    except fetch_mod.FetchError as e:
        return [], [str(e)]
    by_key = {f.key: f for f in src.files}
    for ff in fetched:
        out.append(
            (by_key[ff.file_key], ff.path, "cache" if had[ff.file_key] else "live", ff.fetched_at)
        )
    return out, bad


def collect(
    sources: list[Source], offline: bool
) -> tuple[list[Row], dict[str, str], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Parse enabled sources. Returns (rows, retrieval by sha, parser SERIES, source status)."""
    rows: list[Row] = []
    retrieval: dict[str, str] = {}
    parser_series: dict[str, dict[str, Any]] = {}
    status: dict[str, dict[str, Any]] = {}
    for src in sources:
        st = {"state": "disabled", "rows": 0, "errors": [], "files": []}
        status[src.id] = st
        if not src.enabled:
            continue
        files, bad = _resolve_files(src, offline)
        st["errors"].extend(bad)
        try:
            parser = importlib.import_module(f"ukpm.parsers.{src.id}")
        except ModuleNotFoundError:
            st["errors"].append("no parser module")
            files = []
        for f, path, how, when in files:
            meta = FileMeta(src, f, f.sha256, f.file_url, when, path)
            try:
                parsed = parser.parse(path, meta)
            except NotImplementedError as e:
                st["errors"].append(f"{f.key}: parser not implemented ({e})")
                continue
            except LayoutError as e:
                st["errors"].append(f"{f.key}: {e}")
                continue
            retrieval[f.sha256] = how
            rows.extend(parsed)
            st["rows"] += len(parsed)
            st["files"].append(
                {
                    "key": f.key,
                    "edition": f.edition,
                    "publication_date": f.publication_date,
                    "retrieval": how,
                    "rows": len(parsed),
                }
            )
        parser_series.update(getattr(sys.modules.get(f"ukpm.parsers.{src.id}"), "SERIES", {}))
        st["state"] = "built" if st["rows"] else ("skipped" if offline else "error")
    return rows, retrieval, parser_series, status


# --------------------------------------------------------------------------- gate and records


def gate(rows: list[Row]) -> tuple[list[Row], list[dict[str, Any]]]:
    ok, rejected = [], []
    for r in rows:
        why = problems(r.prov)
        if not isinstance(r.value, int | float) or not math.isfinite(r.value):
            why.append("value missing or not finite")
        if why:
            rejected.append(
                {"series_id": r.series_id, "fiscal_year": r.fiscal_year, "problems": why}
            )
        else:
            ok.append(r)
    return ok, rejected


class Records:
    """Provenance records keyed by published id, with the 'Check this number' block."""

    def __init__(self, retrieval: dict[str, str]):
        self.retrieval = retrieval
        self.by_id: dict[str, dict[str, Any]] = {}
        self.raw: dict[str, tuple[float, str]] = {}

    def note_raw(self, nominal: Row, raw: Row) -> None:
        self.raw[pub_id(nominal)] = (raw.value, raw.unit)

    def add(self, row: Row, primary: Row) -> str:
        """Register `row`'s record; `primary` is the nominal row it derives from (or itself)."""
        pid = pub_id(row)
        if pid in self.by_id:
            return pid
        source_id = pid.split(".")[0]
        d = asdict(row.prov)
        trans = [
            {"op": t["op"], "detail": t["detail"], "inputs": [_pub(i) for i in t["inputs"]]}
            for t in d["transformations"]
        ]
        inputs = sorted({i for t in trans for i in t["inputs"]})
        raw_value, raw_unit = self.raw.get(pub_id(primary), (primary.value, primary.unit))
        rec = {
            **d,
            "provenance_id": pid,
            "source_id": source_id,
            "transformations": trans,
            "licence_url": LICENCE_URLS.get(row.prov.licence),
            "retrieval": self.retrieval.get(row.prov.file_sha256, "live"),
            "status_note": None,
            "inputs": inputs,
            "check": self._check(d, trans, inputs, raw_value, raw_unit),
        }
        self.by_id[pid] = rec
        return pid

    @staticmethod
    def _check(d, trans, inputs, raw_value, raw_unit) -> dict[str, Any]:
        steps = "; ".join(t["detail"] for t in trans)
        if d["api_query"]:
            return {
                "kind": "api",
                "query_url": d["api_query"],
                "json_path": d["cell_or_range"],
                "landing_url": d["landing_url"],
                "published_value": raw_value,
                "published_unit": UNIT_LABEL.get(raw_unit, raw_unit),
                "derived_from": inputs,
            }
        text = (
            f"Download the file, open sheet '{d['sheet']}' and go to cell {d['cell_or_range']}. "
            f"To confirm you have the same file: shasum -a 256 <file> should print "
            f"{d['file_sha256']}."
        )
        if steps:
            text += f" The published figure is then derived: {steps}."
        return {
            "kind": "spreadsheet",
            "download_url": d["source_url"],
            "landing_url": d["landing_url"],
            "sheet": d["sheet"],
            "cell": d["cell_or_range"],
            "row_label": None,
            "column_label": None,
            "sha256": d["file_sha256"],
            "published_value": raw_value,
            "published_unit": UNIT_LABEL.get(raw_unit, raw_unit),
            "instructions": text,
            "derived_from": inputs,
        }


# --------------------------------------------------------------------------- series building


def _fy_range(first: str, last: str) -> list[str]:
    a, b = int(first[:4]), int(last[:4])
    return [f"{y}-{(y + 1) % 100:02d}" for y in range(a, b + 1)]


def _point(row: Row, unit: str, pid: str) -> dict[str, Any]:
    return {
        "fiscal_year": row.fiscal_year,
        "value": row.value,
        "unit": unit,
        "status": row.prov.status,
        "vintage": row.prov.vintage,
        "provenance_id": pid,
    }


def _title(sid: str, src: Source, meta: dict[str, Any]) -> str:
    if meta.get("title"):
        return meta["title"]
    tail = sid.split(".", 1)[1].replace("_", " ").replace(".", " / ")
    return f"{src.dataset}: {tail}"


def build_series(
    chosen: dict[tuple[str, str], Row],
    parser_series: dict[str, dict[str, Any]],
    sources: dict[str, Source],
    records: Records,
    rejected: list[dict[str, Any]],
    retrieval: dict[str, str],
    definition_of: dict[str, str],
) -> tuple[dict[str, dict[str, Any]], str | None]:
    by: dict[str, list[Row]] = defaultdict(list)
    for (sid, _), r in sorted(chosen.items()):
        by[sid].append(r)
    for rs in by.values():
        rs.sort(key=lambda r: r.fiscal_year)

    defl = by.get("obr.gdp_deflator", [])
    gdp = by.get("obr.gdp_nominal", [])
    outturn_defl = [r.fiscal_year for r in defl if r.prov.status == "outturn"]
    base = max(outturn_defl) if outturn_defl else None

    series: dict[str, dict[str, Any]] = {}
    for sid, rs in sorted(by.items()):
        src = sources[sid.split(".")[0]]
        meta = parser_series.get(sid, {})
        first = rs[0]
        monetary = bool(meta.get("monetary", first.unit in ("gbp_m", "gbp_bn")))
        monetary = monetary and first.unit == "gbp_bn"
        tax_year = first.period_basis == "tax_year"
        variants: dict[str, list[dict[str, Any]]] = {
            "nominal": [_point(r, UNIT_LABEL.get(r.unit, r.unit), records.add(r, r)) for r in rs]
        }
        gaps: list[dict[str, Any]] = []
        notes: list[str] = []
        if monetary and base:
            real = []
            for r in rs:
                try:
                    dr = units.deflate(
                        r,
                        defl,
                        base,
                        f"GDP deflator, {defl[0].prov.vintage}, {base}=100"
                        + (
                            "; tax-year series deflated with fiscal-year deflator"
                            if tax_year
                            else ""
                        ),
                    )
                except units.MissingDenominator as e:
                    gaps.append({"fiscal_year": r.fiscal_year, "variant": "real", "reason": str(e)})
                    continue
                if problems(dr.prov):
                    rejected.append(
                        {
                            "series_id": sid,
                            "fiscal_year": r.fiscal_year,
                            "variant": "real",
                            "problems": problems(dr.prov),
                        }
                    )
                    continue
                real.append(_point(dr, f"GBP_bn_{base}", records.add(dr, r)))
            if real:
                variants["real"] = real
        if monetary and first.geography == "UK" and not tax_year and gdp:
            pct = []
            for r in rs:
                try:
                    pr = units.pct_gdp(r, gdp)
                except units.MissingDenominator as e:
                    gaps.append(
                        {"fiscal_year": r.fiscal_year, "variant": "pct_gdp", "reason": str(e)}
                    )
                    continue
                if problems(pr.prov):
                    rejected.append(
                        {
                            "series_id": sid,
                            "fiscal_year": r.fiscal_year,
                            "variant": "pct_gdp",
                            "problems": problems(pr.prov),
                        }
                    )
                    continue
                pct.append(_point(pr, "percent", records.add(pr, r)))
            if pct:
                variants["pct_gdp"] = pct
        if first.geography != "UK":
            notes.append(f"Scope: {first.geography} only, not UK-wide.")
            if monetary:
                notes.append("No % of GDP variant: the numerator is not UK-wide but GDP is.")
        if tax_year:
            notes.append(
                "Tax-year series. Real terms use the fiscal-year deflator; "
                "no % of GDP variant is published."
            )
        if any(r.prov.status == "forecast" for r in rs):
            notes.append("Points with status 'forecast' are the publisher's projections.")
        series[sid] = {
            "id": sid,
            "title": _title(sid, src, meta),
            "description": meta.get("description")
            or f"{src.publisher}, {src.dataset}. Geography: {first.geography}. As published.",
            "source_id": src.id,
            "period_type": meta.get("period_type", first.period_basis),
            "geography": first.geography,
            "monetary": monetary,
            "definition_id": definition_of.get(sid),
            "variants": variants,
            "gaps": _gaps(sid, rs, src, retrieval),
            "notes": notes,
            "_gaps_variant": gaps,
        }
    for s in series.values():
        s["gaps"] = sorted(
            s["gaps"] + s.pop("_gaps_variant"),
            key=lambda g: (g["fiscal_year"], g.get("variant", "")),
        )
    return series, base


def _gaps(sid: str, rs: list[Row], src: Source, retrieval: dict[str, str]) -> list[dict[str, Any]]:
    have = {r.fiscal_year for r in rs}
    declared: dict[str, str] = {}
    for g in src.gaps:
        if fnmatch.fnmatch(sid, g["series"]):
            for y in g["years"]:
                declared[str(y)] = g["reason"]
    default = "not published in any fetched edition"
    if any(retrieval.get(f.sha256) == "fixture" for f in src.files):
        default += " (offline build from trimmed fixtures)"
    span = set(_fy_range(FIRST_YEAR, max(have))) | set(declared)
    return [{"fiscal_year": y, "reason": declared.get(y, default)} for y in sorted(span - have)]


# --------------------------------------------------------------------------- definitions


def build_definitions(
    published: set[str], geography: dict[str, str]
) -> tuple[dict, dict[str, str], dict[str, set[str]]]:
    raw = yaml.safe_load(DEFINITIONS.read_text()) if DEFINITIONS.exists() else []
    groups: dict[str, dict[str, Any]] = {}
    definition_of: dict[str, str] = {}
    defs_by_series: dict[str, set[str]] = defaultdict(set)
    for d in raw or []:
        gid, gtitle = d.get("group") or GROUP_BY_SOURCE.get(d.get("source_id"), ("other", "Other"))
        avail = [s for s in d.get("series_ids") or [] if s in published]
        sid = avail[0] if avail else None
        for s in avail:
            defs_by_series[s].add(d["id"])
            definition_of.setdefault(s, d["id"])
        g = groups.setdefault(gid, {"id": gid, "title": gtitle, "definitions": []})
        g["definitions"].append(
            {
                "id": d["id"],
                "label": d.get("label"),
                "short": d.get("short"),
                "publisher": d.get("publisher"),
                "source_id": d.get("source_id"),
                "series_id": sid,
                "series_ids": avail,
                "scope": geography.get(sid) if sid else None,
                "includes": d.get("includes") or [],
                "excludes": d.get("excludes") or [],
                "notes": d.get("notes"),
                "status": "available" if sid else "not available in slice 1",
            }
        )
    return {"groups": list(groups.values())}, definition_of, defs_by_series


# --------------------------------------------------------------------------- writing


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def _table(
    con: duckdb.DuckDBPyConnection, name: str, schema: dict[str, str], rows: list[dict]
) -> None:
    con.execute(f"DROP TABLE IF EXISTS {name}")
    con.execute(f"CREATE TABLE {name} (" + ", ".join(f'"{c}" {t}' for c, t in schema.items()) + ")")
    if rows:
        con.executemany(
            f"INSERT INTO {name} VALUES ({', '.join('?' * len(schema))})",
            [[r.get(c) for c in schema] for r in rows],
        )


def _git_sha() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _flatten_recon(recon: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for rule in recon["rules"]:
        for r in rule["results"]:
            l_, r_ = r["left"] or {}, r["right"] or {}
            out.append(
                {
                    "rule_id": rule["id"],
                    "fiscal_year": r["fiscal_year"],
                    "edition": r["edition"],
                    "status": r["status"],
                    "left_series_id": l_.get("series_id"),
                    "left_value": l_.get("value"),
                    "left_provenance_ids": json.dumps(l_.get("provenance_ids", [])),
                    "right_series_id": r_.get("series_id"),
                    "right_value": r_.get("value"),
                    "right_provenance_ids": json.dumps(r_.get("provenance_ids", [])),
                    "delta": r["delta"],
                    "delta_pct": r["delta_pct"],
                    "reason": r["reason"],
                }
            )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ukpm build")
    ap.add_argument("--out", default="site/api/v1")
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args(argv)
    out = Path(args.out)
    generated = _now()

    sources = load(SOURCES)
    src_by_id = {s.id: s for s in sources}
    rows, retrieval, parser_series, status = collect(sources, args.offline)
    rows, rejected = gate(rows)

    # nominal GBP bn rows for every vintage; raw values stay in the check block
    records = Records(retrieval)
    nominal: list[Row] = []
    for r in rows:
        n = (
            units.scale(r, 0.001, "GBP million to GBP billion (x 0.001)", unit="gbp_bn")
            if r.unit == "gbp_m"
            else r
        )
        if n is not r:
            records.note_raw(n, r)
        if problems(n.prov):
            rejected.append(
                {
                    "series_id": r.series_id,
                    "fiscal_year": r.fiscal_year,
                    "problems": problems(n.prov),
                }
            )
            continue
        nominal.append(n)

    chosen, superseded = reconcile.stitch(nominal)
    published = {sid for sid, _ in chosen}
    geography = {r.series_id: r.geography for r in nominal}
    definitions, definition_of, defs_by_series = build_definitions(published, geography)
    series, base = build_series(
        chosen, parser_series, src_by_id, records, rejected, retrieval, definition_of
    )
    titles = {sid: s["title"] for sid, s in series.items()}
    for r in nominal:  # every vintage keeps its provenance record
        records.add(r, r)

    recon = reconcile.run(
        nominal,
        pub_id,
        titles,
        {s.id: {"enabled": s.enabled, "verdict": s.verdict} for s in sources},
        frozenset(
            s.id for s in sources if any(f["retrieval"] == "fixture" for f in status[s.id]["files"])
        ),
    )
    recon["generated_at"] = generated

    points = {
        (sid, v): {p["fiscal_year"]: p for p in pts}
        for sid, s in series.items()
        for v, pts in s["variants"].items()
    }

    def lookup(sid: str, basis: str, fy: str):
        p = points.get((sid, basis), {}).get(fy)
        return (p, series[sid]["title"]) if p else None

    claim_out = claims_mod.evaluate(claims_mod.load_claims(CLAIMS), lookup, defs_by_series)
    claim_out["generated_at"] = generated
    corrections = yaml.safe_load(CORRECTIONS.read_text()) if CORRECTIONS.exists() else []
    corrections = corrections or []

    tme = [
        r for (sid, _), r in chosen.items() if sid == "obr.psf.tme" and r.prov.status == "outturn"
    ]
    latest_outturn = max((r.fiscal_year for r in tme), default=None) or max(
        (fy for _, fy in chosen), default=None
    )
    defl_row = next((r for (sid, _), r in chosen.items() if sid == "obr.gdp_deflator"), None)
    errors = [{"source_id": s, "error": e} for s, st in status.items() for e in st["errors"]]
    mode = "offline" if args.offline else "live"

    index = {
        "api_version": "v1",
        "generated_at": generated,
        "build": {
            "mode": mode,
            "git_sha": _git_sha(),
            "rejected": len(rejected),
            "errors": errors,
        },
        "fiscal_years": {"from": FIRST_YEAR, "latest_outturn": latest_outturn},
        "real_base_year": base,
        "deflator": {"series_id": "obr.gdp_deflator", "vintage": defl_row.prov.vintage}
        if base and defl_row
        else None,
        "sources": [
            {
                "id": s.id,
                "publisher": s.publisher,
                "dataset": s.dataset,
                "verdict": s.verdict,
                "licence": s.licence,
                "enabled": s.enabled,
                "status": status[s.id]["state"],
                "rows": status[s.id]["rows"],
                "files": status[s.id]["files"],
                "stale_since": None,
                "deferred": None,
                "notes": s.notes,
            }
            for s in sources
        ],
        "series": [
            {
                "id": sid,
                "title": s["title"],
                "unit": s["variants"]["nominal"][0]["unit"],
                "source_id": s["source_id"],
                "period_type": s["period_type"],
                "geography": s["geography"],
                "monetary": s["monetary"],
                "headline": sid in HEADLINE,
                "definition_id": s["definition_id"],
                "variants": sorted(s["variants"]),
                "path": f"series/{sid}.json",
                "years": [
                    s["variants"]["nominal"][0]["fiscal_year"],
                    s["variants"]["nominal"][-1]["fiscal_year"],
                ],
            }
            for sid, s in sorted(series.items())
        ],
        "files": {
            "observations": "observations.parquet",
            "provenance": "provenance.parquet",
            "all_vintages": "observations_all_vintages.parquet",
            "reconciliation": "reconciliation.parquet",
        },
    }

    tmp = out.parent / f".{out.name}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    _dump(tmp / "index.json", index)
    for sid, s in series.items():
        _dump(tmp / "series" / f"{sid}.json", s)
    per_source: dict[str, dict[str, Any]] = defaultdict(dict)
    for pid, rec in records.by_id.items():
        per_source[rec["source_id"]][pid] = rec
    for source_id, recs in per_source.items():
        _dump(tmp / "provenance" / f"{source_id}.json", {"source_id": source_id, "records": recs})
    _dump(tmp / "reconciliation.json", recon)
    _dump(tmp / "definitions.json", definitions)
    _dump(tmp / "claims.json", claim_out)
    _dump(tmp / "corrections.json", {"corrections": corrections})

    obs, vint = [], []
    for sid, s in series.items():
        for v, pts in s["variants"].items():
            basis = (
                "nominal" if v == "nominal" else ("pct_gdp" if v == "pct_gdp" else f"real_{base}")
            )
            obs += [
                {
                    "series_id": sid,
                    "price_basis": basis,
                    **{
                        k: p[k] for k in ("fiscal_year", "value", "unit", "status", "provenance_id")
                    },
                }
                for p in pts
            ]
    sup_ids = {id(r) for r in superseded}
    for r in nominal:
        vint.append(
            {
                "series_id": r.series_id,
                "fiscal_year": r.fiscal_year,
                "value": r.value,
                "unit": UNIT_LABEL.get(r.unit, r.unit),
                "price_basis": "nominal",
                "status": r.prov.status,
                "provenance_id": pub_id(r),
                "edition": r.prov.edition,
                "vintage": r.prov.vintage,
                "superseded": id(r) in sup_ids,
            }
        )
    prov_rows = [
        {
            **{k: v for k, v in rec.items() if k not in ("check", "transformations", "inputs")},
            "transformations": json.dumps(rec["transformations"]),
            "inputs": json.dumps(rec["inputs"]),
            "published_value": rec["check"].get("published_value"),
            "published_unit": rec["check"].get("published_unit"),
        }
        for rec in records.by_id.values()
    ]
    obs_schema = {
        "series_id": "VARCHAR",
        "fiscal_year": "VARCHAR",
        "value": "DOUBLE",
        "unit": "VARCHAR",
        "price_basis": "VARCHAR",
        "status": "VARCHAR",
        "provenance_id": "VARCHAR",
    }
    WORK.mkdir(exist_ok=True)
    con = duckdb.connect(str(WORK / "ukpm.duckdb"))
    _table(con, "observations", obs_schema, obs)
    _table(
        con,
        "observations_all_vintages",
        {**obs_schema, "edition": "VARCHAR", "vintage": "VARCHAR", "superseded": "BOOLEAN"},
        vint,
    )
    _table(
        con,
        "provenance",
        {
            "provenance_id": "VARCHAR",
            "source_id": "VARCHAR",
            "publisher": "VARCHAR",
            "dataset": "VARCHAR",
            "edition": "VARCHAR",
            "publication_date": "DATE",
            "source_url": "VARCHAR",
            "landing_url": "VARCHAR",
            "file_sha256": "VARCHAR",
            "sheet": "VARCHAR",
            "cell_or_range": "VARCHAR",
            "api_query": "VARCHAR",
            "licence": "VARCHAR",
            "licence_url": "VARCHAR",
            "transformations": "VARCHAR",
            "status": "VARCHAR",
            "status_note": "VARCHAR",
            "vintage": "VARCHAR",
            "retrieval": "VARCHAR",
            "retrieved_at": "VARCHAR",
            "inputs": "VARCHAR",
            "published_value": "DOUBLE",
            "published_unit": "VARCHAR",
        },
        prov_rows,
    )
    _table(
        con,
        "reconciliation",
        {
            "rule_id": "VARCHAR",
            "fiscal_year": "VARCHAR",
            "edition": "VARCHAR",
            "status": "VARCHAR",
            "left_series_id": "VARCHAR",
            "left_value": "DOUBLE",
            "left_provenance_ids": "VARCHAR",
            "right_series_id": "VARCHAR",
            "right_value": "DOUBLE",
            "right_provenance_ids": "VARCHAR",
            "delta": "DOUBLE",
            "delta_pct": "DOUBLE",
            "reason": "VARCHAR",
        },
        _flatten_recon(recon),
    )
    for name, fname in (
        ("observations", "observations"),
        ("observations_all_vintages", "observations_all_vintages"),
        ("provenance", "provenance"),
        ("reconciliation", "reconciliation"),
    ):
        con.execute(f"COPY {name} TO '{tmp / (fname + '.parquet')}' (FORMAT PARQUET)")
    con.close()

    WORK.mkdir(exist_ok=True)
    with (WORK / "rejected.jsonl").open("w") as fh:
        for r in rejected:
            fh.write(json.dumps(r, sort_keys=True) + "\n")

    old = out.parent / f".{out.name}.old"
    shutil.rmtree(old, ignore_errors=True)
    if out.exists():
        out.rename(old)
    tmp.rename(out)
    shutil.rmtree(old, ignore_errors=True)

    s = recon["summary"]
    print(
        f"built {out}: {len(series)} series, {len(obs)} observations, {len(vint)} vintage rows, "
        f"{len(records.by_id)} provenance records, rejected {len(rejected)}"
    )
    print(f"reconciliation: {s}; claims: {len(claim_out['claims'])}")
    for e in errors:
        print(f"warning: {e['source_id']}: {e['error']}", file=sys.stderr)
    failed = [s_.id for s_ in sources if s_.enabled and status[s_.id]["state"] == "error"]
    return 1 if failed else 0
