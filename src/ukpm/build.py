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
from .parsers.cabinet_office_spend import label_of
from .parsers.dwp_benefits import BENEFIT_PAIRS
from .provenance import Row, problems, provenance_id
from .registry import FileEntry, Source, load

SOURCES = Path("data/sources.yml")
DEFINITIONS = Path("data/definitions.yml")
CLAIMS = Path("data/claims.yml")
CORRECTIONS = Path("data/corrections.yml")
GLOSSARY = Path("data/glossary.yml")
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
    "gbp": "GBP",
    "thousand_persons": "thousand_persons",
    "thousand_cases": "thousand_cases",
    "persons": "persons",
    "count": "count",
    "index": "index",
    "percent": "percent",
    "pct": "percent",
    "thousands": "thousands",
    "pct_gdp": "percent",
    "gbp_per_person": "GBP_per_person",
    "gbp_per_household": "GBP_per_household",
    "gbp_per_100": "GBP_per_100",
    "gbp_per_claimant": "GBP_per_claimant",
}
CO_PREFIX = "cabinet_office_spend."
POP_SERIES = {
    "UK": "ons_population.uk",
    "GB": "ons_population.gb",
    "England": "ons_population.england",
}
HH_SERIES = "ons_households.uk"
GDP_FISCAL = "obr.gdp_nominal"
GDP_CALENDAR = "ons_gdp.nominal"
# Stocks at 31 March: no real, % of GDP (ONS publishes its own ratio, ons_psf.ps_net_debt_pct_gdp,
# on a 12-month centred GDP) or per-head variants, because a stock is not a flow for the year.
STOCK_SERIES = frozenset({"ons_psf.ps_net_debt_gbp_bn"})
# Derived variants are built only for series labelled by fiscal year. Calendar-year and
# quarter-based series (ons_gdp.nominal) are published as they come.
DERIVED_BASES = frozenset({"fiscal_year"})
# One part out of every GBP 100 of a total, outside the fixed sets: part -> total.
EXTRA_PER_100 = {"ons_psf.cg_debt_interest": "ons_psf.cg_receipts"}
PER_UNIT_EXTRA = frozenset(
    {
        "ons_psf.cg_debt_interest",
        "ons_psf.cg_receipts",
        "ons_psf.cg_tme",
        "pesa_uk.services",
        "pesa_uk.tme",
        "pesa_uk.public_debt_transactions",
    }
)
_COFOG = (
    "general_public_services",
    "defence",
    "public_order_safety",
    "economic_affairs",
    "environment_protection",
    "housing_community_amenities",
    "health",
    "recreation_culture_religion",
    "education",
    "social_protection",
)
_COFOG_UK = (
    "general_public_services",
    "defence",
    "public_order_and_safety",
    "economic_affairs",
    "environment_protection",
    "housing_and_community_amenities",
    "health",
    "recreation_culture_religion",
    "education",
    "social_protection",
)
PER_100_SETS = {
    "spending_uk": {
        "title": "Public spending on services, UK",
        "scope": "UK",
        "role": "primary",
        "note": "PESA 2026 table 5.2, UK-wide public sector expenditure on services by function. "
        "The ten functions sum to the total except for EU transactions and rounding, which "
        "make up the remainder.",
        "other_label": "EU transactions and rounding",
        "total": "pesa_uk.services",
        "parts": [f"pesa_uk.{f}" for f in _COFOG_UK],
    },
    "spending_england": {
        "title": "Spending on services in England",
        "scope": "England",
        "role": "fallback",
        "note": "England only (PESA chapter 10, table 10.1). Superseded by spending_uk; kept so "
        "that older pages keep working.",
        "superseded_by": "spending_uk",
        "other_label": "everything else (and rounding)",
        "total": "pesa.cofog.total_services",
        "parts": [f"pesa.cofog.{f}" for f in _COFOG],
    },
    "revenue_hmrc": {
        "title": "Tax collected by HMRC",
        "scope": "UK",
        "role": "primary",
        "note": "HMRC cash receipts by tax (NS_Table, table 2).",
        "other_label": "everything else (and rounding)",
        "total": "hmrc_receipts.total",
        "parts": [
            "hmrc_receipts.income_tax",
            "hmrc_receipts.nics",
            "hmrc_receipts.vat",
            "hmrc_receipts.corporation_tax",
            "hmrc_receipts.hydrocarbon_oil_fuel_duties",
            "hmrc_receipts.stamp_duty_land_tax",
        ],
    },
}
BENEFIT_SPEND_IDS = {p["spend"] for p in BENEFIT_PAIRS}
BENEFIT_GAPS = [
    {
        "name": "Child Benefit",
        "reason": "Table 1a shows 0 and Table 1c is blank in this edition.",
    },
    {
        "name": "Income Support",
        "reason": "Caseload in payment is 0 in recent years, so a cost per claimant is undefined.",
    },
    {
        "name": "Incapacity Benefit",
        "reason": "Caseload in payment is 0 in recent years, so a cost per claimant is undefined.",
    },
]
CO_CAPS = {
    "months": 24,
    "expense_types_per_month": 10,
    "suppliers": 20,
    "supplier_floor_gbp": 1_000_000,
    "max_bytes": 262_144,
    "max_provenance_bytes": 1_048_576,
}
_VENDOR_NUMBER = re.compile(r"^\d{6,}\s+")


def clean_supplier(name: str) -> str:
    """Drop a leading vendor number ('1234567 Acme Ltd' -> 'Acme Ltd') so a supplier groups once."""
    return _VENDOR_NUMBER.sub("", name.strip())


_SUPPLIER_DENY = re.compile(
    r"(?i)redact|withheld|personal|individual|employee|private|name not|^n/?a$"
)
_FIGURE = re.compile(r"£\s?\d|\d\s?%|\d[\d,]*\s?(million|billion|bn|m)\b")
_SLUG_RE = re.compile(r"^[a-z0-9-]+$")
_CSV_RANGE = re.compile(r'^([A-Z]+)(\d+):([A-Z]+)(\d+)(?: where ([A-Z]+)="((?:[^"]|"")*)")?$')
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


def _manifest_fixture(src: Source, f: FileEntry) -> Path | None:
    """MANIFEST.yml is a list of entries, or a mapping with them under 'fixtures'."""
    if not src.fixture_dir:
        return None
    manifest = Path(src.fixture_dir) / "MANIFEST.yml"
    if not manifest.exists():
        return None
    data = yaml.safe_load(manifest.read_text()) or []
    entries = data.get("fixtures", []) if isinstance(data, dict) else data
    for e in entries:
        if (
            isinstance(e, dict)
            and e.get("source_id") == src.id
            and e.get("original_sha256") == f.sha256
        ):
            p = manifest.parent / e["fixture"]
            if p.exists():
                return p
    return None


def _fixture_path(src: Source, f: FileEntry) -> Path | None:
    hit = _manifest_fixture(src, f)
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
            "series_id": row.series_id,
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
        csv_m = _CSV_RANGE.match(d["cell_or_range"] or "") if d["sheet"] == "CSV" else None
        if csv_m:
            col, a, last, fcol, ftext = csv_m.group(1, 2, 4, 5, 6)
            if raw_unit == "count":
                what = (
                    f"Count the data rows from row {a} to row {last} (rows with no Amount are "
                    "padding and are not counted)"
                )
            else:
                what = f"Add up column {col} (Amount) for rows {a} to {last}"
            if fcol:
                what += f' where column {fcol} is "{ftext.replace(chr(34) * 2, chr(34))}"'
            text = (
                f"Download the CSV and open it. {what}. To confirm you have the same file: "
                f"shasum -a 256 <file> should print {d['file_sha256']}."
            )
        else:
            text = (
                f"Download the file, open sheet '{d['sheet']}' and go to cell "
                f"{d['cell_or_range']}. To confirm you have the same file: shasum -a 256 <file> "
                f"should print {d['file_sha256']}."
            )
        if steps:
            text += f" The published figure is then derived: {steps}."
        # Aliases of the record fields, kept so the v1 check block stays complete. row_label and
        # column_label are not emitted: no parser records header text, so they were always null.
        return {
            "kind": "spreadsheet",
            "download_url": d["source_url"],
            "landing_url": d["landing_url"],
            "sheet": d["sheet"],
            "cell": d["cell_or_range"],
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


def _emit(
    records: Records,
    rejected: list[dict[str, Any]],
    row: Row,
    primary: Row,
    unit_label: str,
    **ctx: Any,
) -> dict[str, Any] | None:
    """The one write path: gate the row, register its record, return its point (or None)."""
    why = problems(row.prov)
    if not isinstance(row.value, int | float) or not math.isfinite(row.value):
        why.append("value missing or not finite")
    if why:
        rejected.append(
            {"series_id": row.series_id, "fiscal_year": row.fiscal_year, **ctx, "problems": why}
        )
        return None
    return _point(row, unit_label, records.add(row, primary))


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
    nom_by: dict[str, list[Row]],
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
        # calendar-year and other non-fiscal bases, and stocks, get no derived variants
        plain = first.period_basis not in ("fiscal_year", "tax_year") or sid in STOCK_SERIES
        monetary_derive = monetary and not plain
        variants: dict[str, list[dict[str, Any]]] = {
            "nominal": [
                pt
                for r in rs
                if (pt := _emit(records, rejected, r, r, UNIT_LABEL.get(r.unit, r.unit)))
            ]
        }
        gaps: list[dict[str, Any]] = []
        notes: list[str] = []
        real_rows: list[tuple[Row, Row]] = []
        if monetary_derive and base:
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
                if pt := _emit(records, rejected, dr, r, f"GBP_bn_{base}", variant="real"):
                    real.append(pt)
                    real_rows.append((r, dr))
            if real:
                variants["real"] = real
        if monetary_derive and first.geography == "UK" and not tax_year and gdp:
            pct = []
            for r in rs:
                try:
                    pr = units.pct_gdp(r, gdp)
                except units.MissingDenominator as e:
                    gaps.append(
                        {"fiscal_year": r.fiscal_year, "variant": "pct_gdp", "reason": str(e)}
                    )
                    continue
                if pt := _emit(records, rejected, pr, r, "percent", variant="pct_gdp"):
                    pct.append(pt)
            if pct:
                variants["pct_gdp"] = pct
        pop = by.get(POP_SERIES.get(first.geography, ""), [])
        if monetary_derive and not tax_year and pop and _per_person_ok(sid):
            for variant, pairs, label in (
                ("per_person", [(r, r) for r in rs], "GBP_per_person"),
                ("per_person_real", real_rows, f"GBP_per_person_{base}"),
            ):
                pts = []
                for primary, r in pairs:
                    try:
                        pp = units.per_person(r, pop)
                    except units.MissingDenominator:
                        gaps.append(
                            {
                                "fiscal_year": r.fiscal_year,
                                "variant": variant,
                                "reason": "no ONS mid-year estimate for this year; "
                                "projections are not used",
                            }
                        )
                        continue
                    if pt := _emit(records, rejected, pp, primary, label, variant=variant):
                        pts.append(pt)
                if pts:
                    variants[variant] = pts
        hh = by.get(HH_SERIES, [])
        if (
            monetary_derive
            and not tax_year
            and first.geography == "UK"
            and hh
            and _per_person_ok(sid)
        ):
            hh_years = sorted(r.fiscal_year for r in hh)
            for variant, pairs, label in (
                ("per_household", [(r, r) for r in rs], "GBP_per_household"),
                ("per_household_real", real_rows, f"GBP_per_household_{base}"),
            ):
                pts = []
                for primary, r in pairs:
                    try:
                        ph = units.per_household(r, hh)
                    except units.MissingDenominator:
                        if hh_years[0] <= r.fiscal_year <= hh_years[-1]:
                            gaps.append(
                                {
                                    "fiscal_year": r.fiscal_year,
                                    "variant": variant,
                                    "reason": "no ONS household estimate for this year",
                                }
                            )
                        continue
                    if pt := _emit(records, rejected, ph, primary, label, variant=variant):
                        pts.append(pt)
                if pts:
                    variants[variant] = pts
            if "per_household" in variants:
                notes.append(
                    f"Per-household values exist for fiscal years {hh_years[0]} to {hh_years[-1]} "
                    "only (the ONS household count; spend over the fiscal year divided by the "
                    "April-June household count of its first quarter)."
                )
        total_id = _per100_total(sid)
        if total_id and not plain:
            pts = []
            totals = _edition_index(nom_by.get(total_id, []))
            for r in rs:
                tot = totals.get((r.prov.edition, r.fiscal_year))
                if tot is None:
                    gaps.append(
                        {
                            "fiscal_year": r.fiscal_year,
                            "variant": "per_100",
                            "reason": "the total is not published in the same edition",
                        }
                    )
                    continue
                try:
                    sr = units.share(r, tot)
                except units.MissingDenominator as e:
                    gaps.append(
                        {"fiscal_year": r.fiscal_year, "variant": "per_100", "reason": str(e)}
                    )
                    continue
                if pt := _emit(records, rejected, sr, r, "GBP_per_100", variant="per_100"):
                    pts.append(pt)
            if pts:
                variants["per_100"] = pts
        if first.geography != "UK":
            notes.append(f"Scope: {first.geography} only, not UK-wide.")
            if monetary:
                notes.append("No % of GDP variant: the numerator is not UK-wide but GDP is.")
        if first.period_basis == "calendar_year":
            notes.append(
                "Calendar-year series: the label is the calendar year, not a fiscal year. It gets "
                "no real-terms, % of GDP or per-head variant, because a fiscal year (April to "
                "March) and a calendar year do not line up. Fiscal-year series use the OBR "
                "fiscal-year GDP for their % of GDP."
            )
        if sid in STOCK_SERIES:
            notes.append(
                "A stock at 31 March, not a flow over the year: nominal only. The ratio to GDP "
                "is published by the ONS as ons_psf.ps_net_debt_pct_gdp."
            )
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


def _per_person_ok(sid: str) -> bool:
    return (
        sid in HEADLINE
        or sid.startswith("pesa.cofog.")
        or sid in BENEFIT_SPEND_IDS
        or sid in PER_UNIT_EXTRA
        or _share_set_of(sid) is not None
    )


def _share_set_of(sid: str) -> str | None:
    return next((k for k, v in PER_100_SETS.items() if sid in v["parts"]), None)


def _per100_total(sid: str) -> str | None:
    """The total a series is expressed against for its per_100 variant, if it has one."""
    if sid in EXTRA_PER_100:
        return EXTRA_PER_100[sid]
    st = _share_set_of(sid)
    return PER_100_SETS[st]["total"] if st else None


def _edition_index(rows: list[Row]) -> dict[tuple[str, str], Row]:
    return {(r.prov.edition, r.fiscal_year): r for r in rows}


def _first_year(src: Source) -> str:
    """First fiscal year a source claims to cover, but never earlier than FIRST_YEAR."""
    claimed = str(src.coverage.get("from", ""))
    return claimed if re.fullmatch(r"\d{4}-\d{2}", claimed) and claimed > FIRST_YEAR else FIRST_YEAR


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
    if rs[0].period_basis == "calendar_year":
        span = {str(y) for y in range(int(FIRST_YEAR[:4]), int(max(have)) + 1)} | set(declared)
    else:
        span = set(_fy_range(_first_year(src), max(have))) | set(declared)
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


# --------------------------------------------------------------------------- shares


def _check_hmrc_parts() -> None:
    """Every HMRC part must be a top-level column, never one 'included within' another."""
    from .parsers import hmrc_receipts

    nested = {slug for h, slug in hmrc_receipts._SLUGS.items() if "included within" in h.lower()}
    for part in PER_100_SETS["revenue_hmrc"]["parts"]:
        slug = part.split(".", 1)[1]
        if slug in nested or "included_within" in slug:
            raise RuntimeError(f"{part} is not a top-level HMRC column; it cannot be a share part")


def build_shares(
    series: dict[str, dict[str, Any]],
    nom_by: dict[str, list[Row]],
    chosen_by: dict[str, list[Row]],
    records: Records,
    rejected: list[dict[str, Any]],
    generated: str,
) -> dict[str, Any]:
    _check_hmrc_parts()
    sets = []
    for set_id, spec in PER_100_SETS.items():
        entry: dict[str, Any] = {
            "id": set_id,
            "title": spec["title"],
            "scope": spec["scope"],
            "role": spec["role"],
            "note": spec["note"],
            "total_series_id": spec["total"],
            **({"superseded_by": spec["superseded_by"]} if "superseded_by" in spec else {}),
        }
        totals = _edition_index(nom_by.get(spec["total"], []))
        part_idx = {p: _edition_index(nom_by.get(p, [])) for p in spec["parts"]}
        cands = [
            k
            for k, t in totals.items()
            if t.prov.status == "outturn"
            and all(k in m and m[k].prov.status == "outturn" for m in part_idx.values())
        ]
        if not cands:
            sets.append(
                {
                    **entry,
                    "available": False,
                    "reason": "no year has the total and every "
                    "part, as actual figures, in one edition",
                }
            )
            continue
        edition, fy = max(cands, key=lambda k: (k[1], totals[k].prov.publication_date))
        total = totals[(edition, fy)]
        pop_id = POP_SERIES.get(total.geography)
        pop = chosen_by.get(pop_id, []) if pop_id else []
        hh = chosen_by.get(HH_SERIES, []) if total.geography == "UK" else []
        parts_out, part_rows, failed = [], [], False
        for pid_ in spec["parts"]:
            row = part_idx[pid_][(edition, fy)]
            part_rows.append(row)
            try:
                sr = units.share(row, total)
            except units.MissingDenominator:
                failed = True
                continue
            p100 = _emit(records, rejected, sr, row, "GBP_per_100", variant="per_100")
            pp = None
            if pop and row.unit == "gbp_bn":
                try:
                    pp = _emit(
                        records,
                        rejected,
                        units.per_person(row, pop),
                        row,
                        "GBP_per_person",
                        variant="per_person",
                    )
                except units.MissingDenominator:
                    pp = None
            phh = None
            if hh and row.unit == "gbp_bn":
                try:
                    phh = _emit(
                        records,
                        rejected,
                        units.per_household(row, hh),
                        row,
                        "GBP_per_household",
                        variant="per_household",
                    )
                except units.MissingDenominator:
                    phh = None
            if p100 is None:
                failed = True
                continue
            parts_out.append(
                {
                    "series_id": pid_,
                    "title": series[pid_]["title"] if pid_ in series else pid_,
                    "per_100": p100,
                    "per_person": pp,
                    "per_household": phh,
                }
            )
        other = None
        if not failed:
            orow = units.remainder(total, part_rows, spec["other_label"])
            try:
                other = _emit(
                    records,
                    rejected,
                    units.share(orow, total),
                    total,
                    "GBP_per_100",
                    variant="per_100",
                )
            except units.MissingDenominator:
                other = None
        if failed or other is None:
            sets.append({**entry, "available": False, "reason": "a share could not be derived"})
            continue
        sets.append(
            {
                **entry,
                "available": True,
                "fiscal_year": fy,
                "edition": edition,
                "other_label": spec["other_label"],
                "parts": parts_out,
                "other": other,
            }
        )
    return {"generated_at": generated, "sets": sets}


# --------------------------------------------------------------------------- benefits

CLAIMANT_NOTE = "Claimant numbers are yearly averages, rounded to the nearest 1,000."


def build_benefits(
    series: dict[str, dict[str, Any]],
    nom_by: dict[str, list[Row]],
    chosen_by: dict[str, list[Row]],
    records: Records,
    rejected: list[dict[str, Any]],
    generated: str,
) -> dict[str, dict[str, Any]]:
    """Return {relative path: JSON object} for benefits/index.json and benefits/<slug>.json."""
    total_id = "dwp_benefits.exp.total_benefit_expenditure"
    totals = _edition_index(nom_by.get(total_id, []))
    files: dict[str, dict[str, Any]] = {}
    index_entries: list[dict[str, Any]] = []
    gaps = [dict(g) for g in BENEFIT_GAPS]
    edition = None
    for pair in BENEFIT_PAIRS:
        slug = pair["slug"]
        if not _SLUG_RE.match(slug):
            raise RuntimeError(f"bad benefit slug {slug!r}")
        sid, cid = pair["spend"], pair["caseload"]
        if sid not in series or cid not in series:
            gaps.append(
                {
                    "name": pair["name"],
                    "reason": "the spend or caseload series is not in this build",
                }
            )
            continue
        caseloads = _edition_index(nom_by.get(cid, []))
        cpc_pts, share_pts, fgaps = [], [], []
        for r in chosen_by[sid]:
            edition = edition or r.prov.edition
            c = caseloads.get((r.prov.edition, r.fiscal_year))
            if c is None:
                fgaps.append(
                    {
                        "fiscal_year": r.fiscal_year,
                        "field": "cost_per_claimant",
                        "reason": "no caseload published for this year",
                    }
                )
            else:
                try:
                    pt = _emit(
                        records,
                        rejected,
                        units.per_claimant(r, c),
                        r,
                        "GBP_per_claimant",
                        variant="cost_per_claimant",
                    )
                    if pt:
                        cpc_pts.append(pt)
                except units.MissingDenominator as e:
                    fgaps.append(
                        {
                            "fiscal_year": r.fiscal_year,
                            "field": "cost_per_claimant",
                            "reason": str(e),
                        }
                    )
            t = totals.get((r.prov.edition, r.fiscal_year))
            if t is None:
                fgaps.append(
                    {
                        "fiscal_year": r.fiscal_year,
                        "field": "share_of_welfare",
                        "reason": "the welfare total is not published in the same edition",
                    }
                )
            else:
                try:
                    pt = _emit(
                        records,
                        rejected,
                        units.share(r, t, op="share_of_total"),
                        r,
                        "percent",
                        variant="share_of_welfare",
                    )
                    if pt:
                        share_pts.append(pt)
                except units.MissingDenominator as e:
                    fgaps.append(
                        {
                            "fiscal_year": r.fiscal_year,
                            "field": "share_of_welfare",
                            "reason": str(e),
                        }
                    )
        spend_pts = series[sid]["variants"]["nominal"]
        claim_pts = series[cid]["variants"]["nominal"]
        have = [
            {p["fiscal_year"] for p in pts} for pts in (spend_pts, claim_pts, cpc_pts, share_pts)
        ]
        full = sorted(set.intersection(*have))
        by_fy = [
            {p["fiscal_year"]: p for p in pts} for pts in (spend_pts, claim_pts, cpc_pts, share_pts)
        ]
        outturn = [fy for fy in full if all(m[fy]["status"] == "outturn" for m in by_fy)]
        head_fy = outturn[-1] if outturn else (full[-1] if full else None)
        headline = None
        if head_fy:
            sp, cl, cp, sh = (m[head_fy] for m in by_fy)
            real_pt = next(
                (p for p in series[sid]["variants"].get("real", []) if p["fiscal_year"] == head_fy),
                None,
            )
            headline = {
                "fiscal_year": head_fy,
                "status": "outturn" if head_fy in outturn else "forecast",
                "spend": sp,
                "spend_real": real_pt,
                "claimants": cl,
                "cost_per_claimant": cp,
                "share_of_welfare": sh,
            }
        notes = list(pair["notes"])
        if pair.get("basis_note"):
            notes.append(pair["basis_note"])
        notes.append(CLAIMANT_NOTE)
        files[f"benefits/{slug}.json"] = {
            "slug": slug,
            "name": pair["name"],
            "geography": "GB",
            "edition": edition,
            "spend_series_id": sid,
            "caseload_series_id": cid,
            "caseload_basis": pair["basis"],
            "headline_year": head_fy,
            "spend": spend_pts,
            "spend_real": series[sid]["variants"].get("real", []),
            "spend_per_person": series[sid]["variants"].get("per_person", []),
            "claimants": claim_pts,
            "cost_per_claimant": cpc_pts,
            "share_of_welfare": share_pts,
            "gaps": sorted(fgaps, key=lambda g: (g["fiscal_year"], g["field"])),
            "notes": notes,
        }
        index_entries.append(
            {
                "slug": slug,
                "name": pair["name"],
                "path": f"benefits/{slug}.json",
                "caseload_basis": pair["basis"],
                "headline": headline,
            }
        )
    files["benefits/index.json"] = {
        "generated_at": generated,
        "edition": edition,
        "geography": "GB",
        "total_series_id": total_id,
        "benefits": index_entries,
        "gaps": gaps,
    }
    return files


# --------------------------------------------------------------------------- Cabinet Office


def _co_parts(sid: str) -> tuple[str, str]:
    """('total'|'transactions'|'expense_type'|'supplier', 'YYYY_MM') from a series id."""
    kind, mm = sid[len(CO_PREFIX) :].split(".")[:2]
    return kind, mm


def _month_label(mm: str) -> str:
    return mm.replace("_", "-")


def build_cabinet_office(
    co_rows: list[Row],
    enabled: bool,
    records: Records,
    rejected: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[Row]]:
    """Aggregates only. Returns (summary.json object, month total rows that were published)."""
    base = {"source_id": "cabinet_office_spend", "entity": "Cabinet Office (core)"}
    if not enabled or not co_rows:
        return (
            {
                **base,
                "available": False,
                "reason": "the source is disabled or produced no rows in this build",
            },
            [],
        )
    by_month: dict[str, dict[str, list[Row]]] = defaultdict(lambda: defaultdict(list))
    for r in co_rows:
        kind, mm = _co_parts(r.series_id)
        by_month[mm][kind].append(r)
    keep = sorted(by_month, reverse=True)[: CO_CAPS["months"]]
    months_out, total_rows = [], []
    for mm in keep:  # newest first
        kinds = by_month[mm]
        total = kinds["total"][0]
        tp = _emit(records, rejected, total, total, "GBP")
        if tp is None:
            continue
        total_rows.append(total)
        tx = kinds["transactions"][0] if kinds["transactions"] else None
        txp = _emit(records, rejected, tx, tx, "count") if tx else None
        ets = sorted(kinds["expense_type"], key=lambda r: -r.value)
        top = ets[: CO_CAPS["expense_types_per_month"]]
        et_out, top_ok = [], []
        for r in top:
            name = label_of(r)
            pt = _emit(records, rejected, r, r, "GBP")
            if pt and name:
                et_out.append({"name": name, "point": pt})
                top_ok.append(r)
        other = None
        if len(ets) > len(top) and len(top_ok) == len(top):
            orow = units.remainder(total, top_ok, "other expense types")
            other = _emit(records, rejected, orow, total, "GBP")
        months_out.append(
            {
                "month": _month_label(mm),
                "fiscal_year": total.fiscal_year,
                "total": tp,
                "transactions": txp,
                "expense_types": et_out,
                "other_expense_types": other,
            }
        )
    window_out: dict[str, Any] = {
        "from": None,
        "to": None,
        "months": 0,
        "complete": False,
        "total": None,
    }
    top_suppliers: list[dict[str, Any]] = []
    other_suppliers = None
    win = reconcile.co_window(total_rows)
    if win is not None:
        wrow, wmonths = win
        wp = _emit(records, rejected, wrow, wmonths[0], "GBP")
        # a window total that fails the gate leaves the window unavailable
        if wp:
            for m in wmonths[1:]:
                records.add(m, m)
            window_out = {
                "from": _month_label(_co_parts(wmonths[0].series_id)[1]),
                "to": _month_label(_co_parts(wmonths[-1].series_id)[1]),
                "months": len(wmonths),
                "complete": True,
                "total": wp,
            }
            wm = [_co_parts(m.series_id)[1] for m in wmonths]
            # rows are grouped by cleaned name, so one supplier written with and without a vendor
            # number (or twice in a month) is one supplier; each input row keeps its own record
            sup_months: dict[str, dict[str, list[Row]]] = defaultdict(lambda: defaultdict(list))
            for mm in wm:
                for r in by_month[mm]["supplier"]:
                    name = label_of(r)
                    if name is not None:
                        sup_months[clean_supplier(name)][mm].append(r)
            sup_total = {
                n: sum(r.value for rs in d.values() for r in rs) for n, d in sup_months.items()
            }
            ranked = sorted(sup_total, key=lambda n: (-sup_total[n], n))[: CO_CAPS["suppliers"]]
            named_rows = []
            for name in ranked:
                if (
                    not name.strip()
                    or _SUPPLIER_DENY.search(name)
                    or sup_total[name] < CO_CAPS["supplier_floor_gbp"]
                ):
                    continue
                months = [r for mm in wm for r in sup_months[name].get(mm, [])]
                first, rest = months[0], months[1:]
                n_months = len(sup_months[name])
                srow = units.sum_rows(
                    first,
                    rest,
                    "sum_months",
                    f"sum of this supplier's monthly totals, {n_months} month(s) between "
                    f"{window_out['from']} and {window_out['to']}; this record's own range is "
                    "the first of those months, the other months are its inputs",
                )
                pt = _emit(records, rejected, srow, first, "GBP")
                if pt is None:
                    continue
                for m in rest:
                    records.add(m, m)
                named_rows.append(srow)
                top_suppliers.append({"name": name, "point": pt, "months_present": n_months})
            if named_rows:
                orow = units.remainder(
                    wrow, named_rows, "suppliers not named individually", strict=False
                )
                other_suppliers = _emit(records, rejected, orow, wmonths[0], "GBP")
    summary = {
        **base,
        "threshold_gbp": 25000,
        "vat_basis": "unverified",
        "available": True,
        "window": window_out,
        "months": months_out,
        "top_suppliers": top_suppliers,
        "other_suppliers": other_suppliers,
        "caps": dict(CO_CAPS),
        "notes": [
            "Amounts as published; the files do not say whether VAT is included.",
            "The 20 largest suppliers paid at least £1 million over the 12 months are named; "
            "everyone else is grouped.",
        ],
    }
    return summary, total_rows


# --------------------------------------------------------------------------- glossary


class GlossaryError(ValueError):
    pass


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")


def build_glossary(source_ids: set[str], generated: str, path: Path = GLOSSARY) -> dict[str, Any]:
    """Validate data/glossary.yml and return glossary.json. No figures are allowed in copy."""
    raw = yaml.safe_load(path.read_text()) if path.exists() else None
    if not isinstance(raw, list) or not raw:
        raise GlossaryError(f"{path}: must be a non-empty list")
    terms: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, e in enumerate(raw):
        if not isinstance(e, dict):
            raise GlossaryError(f"{path}: entry {i} is not a mapping")
        name = e.get("id") or e.get("term") or f"#{i}"
        for k in ("term", "plain", "long"):
            if not isinstance(e.get(k), str) or not e[k].strip():
                raise GlossaryError(f"glossary entry {name!r}: missing {k}")
        gid = e.get("id") or _slugify(e["term"])
        if not _SLUG_RE.match(gid):
            raise GlossaryError(f"glossary entry {name!r}: bad id {gid!r}")
        if gid in seen:
            raise GlossaryError(f"glossary entry {name!r}: duplicate id {gid!r}")
        seen.add(gid)
        for k in ("plain", "long"):
            m = _FIGURE.search(e[k])
            if m:
                raise GlossaryError(
                    f"glossary entry {gid!r}: {k} contains a figure ({m.group(0)!r}); figures "
                    "belong in the API with provenance"
                )
        if e.get("source_id") is not None and e["source_id"] not in source_ids:
            raise GlossaryError(f"glossary entry {gid!r}: unknown source_id {e['source_id']!r}")
        terms.append(
            {
                "id": gid,
                "term": e["term"].strip(),
                "aliases": list(e.get("aliases") or []),
                "plain": e["plain"].strip(),
                "long": e["long"].strip(),
                "see_also": list(e.get("see_also") or []),
                "source_id": e.get("source_id"),
                "checker_only": bool(e.get("checker_only", False)),
            }
        )
    for t in terms:
        for ref in t["see_also"]:
            if ref not in seen:
                raise GlossaryError(f"glossary entry {t['id']!r}: see_also {ref!r} does not exist")
    terms.sort(key=lambda t: t["term"].casefold())
    return {"generated_at": generated, "terms": terms}


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


def _per_household_block(chosen_by: dict[str, list[Row]]) -> dict[str, Any]:
    rows = chosen_by.get(HH_SERIES)
    if not rows:
        return {
            "available": False,
            "reason": "the ONS household count is disabled or produced no rows in this build",
        }
    return {
        "available": True,
        "series_id": HH_SERIES,
        "unit": "thousands",
        "vintage": rows[-1].prov.vintage,
        "years": [rows[0].fiscal_year, rows[-1].fiscal_year],
        "variants": ["per_household", "per_household_real"],
        "period_basis": "apr_jun_quarter",
        "mapping": "Labour Force Survey April-June quarter of calendar year YYYY, labelled with "
        "the fiscal year YYYY-(YY+1) that contains it; spend of that whole fiscal year is "
        "divided by it",
        "note": "A sample survey of private households, 2011 onwards (the definition changed "
        "in 2011). Only UK-wide series have a per-household variant.",
    }


def _gdp_block(chosen_by: dict[str, list[Row]]) -> dict[str, Any]:
    fiscal = chosen_by.get(GDP_FISCAL, [])
    cal = chosen_by.get(GDP_CALENDAR, [])
    return {
        "fiscal_year": {
            "series_id": GDP_FISCAL,
            "vintage": fiscal[-1].prov.vintage if fiscal else None,
            "used_for": "the pct_gdp variant of every UK fiscal-year monetary series: value of "
            "fiscal year Y divided by nominal GDP of fiscal year Y",
        },
        "calendar_year": {
            "series_id": GDP_CALENDAR if cal else None,
            "vintage": cal[-1].prov.vintage if cal else None,
            "years": [cal[0].fiscal_year, cal[-1].fiscal_year] if cal else None,
            "used_for": None,
            "note": "ONS calendar-year GDP is published for reference and cross-checks only. It "
            "is not a divisor: an April-March fiscal year and a calendar year do not line up, "
            "and the ONS public sector finances use their own 12-month centred GDP.",
        },
    }


def _debt_interest_block(chosen_by: dict[str, list[Row]], series: dict[str, Any]) -> dict[str, Any]:
    sid, total = "ons_psf.cg_debt_interest", EXTRA_PER_100["ons_psf.cg_debt_interest"]
    rows = [r for r in chosen_by.get(sid, []) if r.prov.status == "outturn"]
    if not rows:
        return {
            "available": False,
            "reason": "the ONS public sector finances are not in this build",
        }
    return {
        "available": True,
        "series_id": sid,
        "variants": sorted(series[sid]["variants"]) if sid in series else [],
        "per_100_total_series_id": total,
        "latest_outturn": rows[-1].fiscal_year,
        "note": "Central government interest on its debt (includes investment income "
        "attributable to insurance policy holders). per_100 is out of every GBP 100 of central "
        "government revenue.",
    }


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
    # Cabinet Office rows never enter stitching, series, observations or the vintage loop
    co_rows = [r for r in rows if r.series_id.startswith(CO_PREFIX)]
    rows = [r for r in rows if not r.series_id.startswith(CO_PREFIX)]

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
    nom_by: dict[str, list[Row]] = defaultdict(list)
    for r in nominal:
        nom_by[r.series_id].append(r)
    chosen_by: dict[str, list[Row]] = defaultdict(list)
    for (sid_, _), r in sorted(chosen.items()):
        chosen_by[sid_].append(r)
    series, base = build_series(
        chosen, parser_series, src_by_id, records, rejected, retrieval, definition_of, nom_by
    )
    titles = {sid: s["title"] for sid, s in series.items()}
    for r in nominal:  # every vintage keeps its provenance record
        records.add(r, r)

    shares = build_shares(series, nom_by, chosen_by, records, rejected, generated)
    benefit_files = build_benefits(series, nom_by, chosen_by, records, rejected, generated)
    co_summary, co_month_totals = build_cabinet_office(
        co_rows, src_by_id["cabinet_office_spend"].enabled, records, rejected
    )
    try:
        glossary = build_glossary(set(src_by_id), generated)
    except GlossaryError as e:
        print(f"build failed: {e}", file=sys.stderr)
        return 1

    recon = reconcile.run(
        nominal,
        pub_id,
        titles,
        {s.id: {"enabled": s.enabled, "verdict": s.verdict} for s in sources},
        frozenset(
            s.id for s in sources if any(f["retrieval"] == "fixture" for f in status[s.id]["files"])
        ),
        co_month_totals,
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
                "verdict_reason": s.verdict_reason,
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
        "population": {
            "series": {g: sid for g, sid in POP_SERIES.items() if sid in series},
            "vintage": next(
                (r.prov.vintage for (sid, _), r in chosen.items() if sid.startswith("ons_pop")),
                None,
            ),
            "mapping": "mid-year (30 June) estimate inside each April-March year",
        },
        "per_household": _per_household_block(chosen_by),
        "gdp": _gdp_block(chosen_by),
        "debt_interest": _debt_interest_block(chosen_by, series),
        "files": {
            "observations": "observations.parquet",
            "provenance": "provenance.parquet",
            "all_vintages": "observations_all_vintages.parquet",
            "reconciliation": "reconciliation.parquet",
            "glossary": "glossary.json",
            "shares": "shares.json",
            "benefits": "benefits/index.json",
            "cabinet_office": "cabinet_office/summary.json",
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
    _dump(tmp / "glossary.json", glossary)
    _dump(tmp / "shares.json", shares)
    for rel, obj in benefit_files.items():
        _dump(tmp / rel, obj)
    _dump(tmp / "cabinet_office" / "summary.json", co_summary)

    obs, vint = [], []
    for sid, s in series.items():
        for v, pts in s["variants"].items():
            basis = {
                "nominal": "nominal",
                "pct_gdp": "pct_gdp",
                "per_person": "per_person",
                "per_person_real": f"per_person_real_{base}",
                "per_household": "per_household",
                "per_household_real": f"per_household_real_{base}",
                "per_100": "per_100",
            }.get(v, f"real_{base}")
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
