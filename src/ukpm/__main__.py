"""CLI: python -m ukpm fetch | build | check-api."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

import duckdb

from . import fetch as fetch_mod
from .parsers import FileMeta, LayoutError
from .provenance import ProvenanceError, Row, validate
from .registry import Source, load

SOURCES = Path("data/sources.yml")
PARSED = Path("work/parsed")


def _rows_to_parquet(rows: list[Row], dest: Path) -> None:
    flat = []
    for r in rows:
        d = asdict(r)
        prov = d.pop("prov")
        prov["transformations"] = json.dumps(prov["transformations"])
        flat.append({**d, **prov})
    dest.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    cols = list(flat[0]) if flat else []
    if not flat:
        raise RuntimeError("parser returned no rows")
    con.execute(
        "CREATE TABLE t ("
        + ", ".join(f'"{c}" {"DOUBLE" if c == "value" else "VARCHAR"}' for c in cols)
        + ")"
    )
    con.executemany(
        f"INSERT INTO t VALUES ({', '.join('?' * len(cols))})", [[x[c] for c in cols] for x in flat]
    )
    con.execute(f"COPY t TO '{dest}' (FORMAT PARQUET)")
    con.close()


def fetch_and_parse(src: Source, *, offline: bool) -> list[Row]:
    fetched = fetch_mod.fetch_source(src, offline=offline)
    parser = importlib.import_module(f"ukpm.parsers.{src.id}")
    by_key = {f.key: f for f in src.files}
    rows: list[Row] = []
    for ff in fetched:
        meta = FileMeta(src, by_key[ff.file_key], ff.sha256, ff.url, ff.fetched_at, ff.path)
        rows.extend(parser.parse(ff.path, meta))
    if hasattr(parser, "combine"):
        rows = parser.combine(rows)
    for r in rows:
        validate(r.prov)
    return rows


def cmd_fetch(args: argparse.Namespace) -> int:
    sources = {s.id: s for s in load(SOURCES)}
    ids = args.sources or [i for i, s in sources.items() if s.enabled]
    rc = 0
    for sid in ids:
        src = sources.get(sid)
        if src is None:
            print(f"skipped: {sid}: unknown source")
            continue
        if not src.enabled:
            print(f"skipped: {sid}: disabled ({src.verdict})")
            continue
        try:
            rows = fetch_and_parse(src, offline=args.offline)
            _rows_to_parquet(rows, PARSED / f"{sid}.parquet")
            print(f"ok: {sid}: {len(rows)} rows")
        except fetch_mod.FetchError as e:
            if "no offline copy" in str(e):
                print(f"skipped: {e}")
            else:
                print(f"error: {e}", file=sys.stderr)
                rc = 1
        except ModuleNotFoundError as e:
            if e.name == f"ukpm.parsers.{sid}":
                print(f"skipped: {sid}: no parser module yet")
            else:
                raise
        except (LayoutError, ProvenanceError, RuntimeError) as e:
            print(f"error: {sid}: {e}", file=sys.stderr)
            rc = 1
    return rc


def _delegate(module: str, argv: list[str]) -> int:
    try:
        mod = importlib.import_module(f"ukpm.{module}")
    except ModuleNotFoundError as e:
        if e.name == f"ukpm.{module}":
            print(f"error: ukpm.{module} is not implemented yet", file=sys.stderr)
            return 2
        raise
    return int(mod.main(argv) or 0)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ukpm")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pf = sub.add_parser("fetch")
    pf.add_argument("sources", nargs="*")
    pf.add_argument("--offline", action="store_true")
    pb = sub.add_parser("build")
    pb.add_argument("--offline", action="store_true")
    pb.add_argument("--out", default="site/api/v1")
    pc = sub.add_parser("check-api")
    pc.add_argument("dir", nargs="?", default="site/api/v1")
    pc.add_argument("--live", action="store_true")
    pw = sub.add_parser("watch")
    pw.add_argument("sources", nargs="*")
    pw.add_argument("--accept", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "watch":
        return _delegate("watch", args.sources + (["--accept"] if args.accept else []))
    if args.cmd == "fetch":
        return cmd_fetch(args)
    if args.cmd == "build":
        return _delegate("build", ["--out", args.out] + (["--offline"] if args.offline else []))
    return _delegate("check_api", [args.dir] + (["--live"] if args.live else []))


if __name__ == "__main__":
    sys.exit(main())
