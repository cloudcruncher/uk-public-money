"""Stitching across editions and reconciliation rules R1-R7.

Results are data, never exceptions: a mismatch is recorded with its delta. Statuses are
`pass`, `fail`, `info` (known definitional difference) and `not_run` (an input is missing, with
the reason). Every rule appears in the output even when it cannot run.

All values compared here are the nominal GBP billion rows built by `ukpm.build` (a row published
in GBP million has already been scaled by a recorded transformation). Rules never compare
across editions, except R3 and R6, which use the newest edition of each side and say so.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from .provenance import Row

PidFn = Callable[[Row], str]

TES = "pesa.cofog.total_services"
TME = "pesa.tme"
COFOG_PREFIX = "pesa.cofog."
OBR_TME = "obr.psf.tme"
OBR_RECEIPTS = "obr.psf.receipts"
HMRC_TOTAL = "hmrc_receipts.total"
DWP_GB_TOTAL = "dwp_benefits.exp.total_benefit_expenditure"
DWP_UK_TOTAL = "dwp_benefits.total_uk_welfare"
DWP_LINE = "dwp_benefits.exp."
DWP_UK_LINE = "dwp_benefits.uk_welfare."

GBP_M_IN_BN = 0.001  # the rounding unit of tables published in GBP million, in GBP billion

RULES: list[dict[str, Any]] = [
    {
        "id": "R1",
        "title": "PESA 10.1: COFOG functions sum to the table total",
        "description": "Within one PESA edition and year, the ten COFOG function rows should "
        "sum to the table's own total row (Total Expenditure on Services, England).",
        "tolerance": {"abs": 0.5, "rel": None, "unit": "table unit per function row (GBP m)"},
    },
    {
        "id": "R2",
        "title": "PESA 10.1 total vs PESA TME (Table 4.1)",
        "description": "Same edition. Chapter 10 totals Total Expenditure on Services (TES) in "
        "England, not TME, so the gap is reported as information, not pass/fail.",
        "tolerance": {"abs": None, "rel": 0.001, "unit": "only applied if the label says TME"},
    },
    {
        "id": "R3",
        "title": "PESA TME vs OBR databank TME",
        "description": "Newest edition of each source, outturn years in both.",
        "tolerance": {"abs": None, "rel": 0.01, "unit": "relative"},
    },
    {
        "id": "R4",
        "title": "PESA TME vs ONS PSF TME",
        "description": "Needs the ONS Public Sector Finances source, which is disabled.",
        "tolerance": {"abs": None, "rel": 0.01, "unit": "relative"},
    },
    {
        "id": "R5",
        "title": "Our real-terms TME vs the OBR databank real-terms sheet",
        "description": "Compares our deflated TME with the databank's own real-terms TME.",
        "tolerance": {"abs": None, "rel": 0.005, "unit": "relative"},
    },
    {
        "id": "R6",
        "title": "HMRC total receipts vs OBR public sector current receipts",
        "description": "Information only (cash vs accrued; HMRC-only vs all public sector "
        "receipts such as council tax and business rates). Fails only if HMRC exceeds OBR.",
        "tolerance": {"abs": None, "rel": None, "unit": "fail only if HMRC > OBR"},
    },
    {
        "id": "R7",
        "title": "DWP welfare totals vs the sum of their benefit lines",
        "description": "Same edition and year. (a) Table 1a total benefit expenditure (GB) vs the "
        "sum of its top-level benefit lines. (b) UK welfare tab total vs the sum of its "
        "component lines.",
        "tolerance": {
            "abs": 0.5,
            "rel": None,
            "unit": "table unit per line (Table 1a GBP m; UK tab 0.5 x GBP 1m per line)",
        },
    },
]


def stitch(rows: list[Row]) -> tuple[dict[tuple[str, str], Row], list[Row]]:
    """Newest publication date wins per (series, fiscal year); outturn beats forecast on a tie.

    Returns (chosen, superseded). Nothing is interpolated or carried forward.
    """
    groups: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for r in rows:
        groups[(r.series_id, r.fiscal_year)].append(r)
    chosen: dict[tuple[str, str], Row] = {}
    superseded: list[Row] = []
    for k, rs in groups.items():
        rs = sorted(rs, key=lambda r: (r.prov.publication_date, r.prov.status == "outturn"))
        chosen[k] = rs[-1]
        superseded.extend(rs[:-1])
    return chosen, superseded


def _side(series_id: str, value: float, rows: list[Row], pid: PidFn) -> dict[str, Any]:
    pids = [pid(r) for r in rows]
    return {
        "series_id": series_id,
        "value": value,
        "unit": "GBP_bn",
        "provenance_id": pids[0] if len(pids) == 1 else None,
        "provenance_ids": pids,
    }


def _result(
    fy: str,
    edition: str | None,
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
    status: str,
    reason: str,
    **extra: Any,
) -> dict[str, Any]:
    delta = delta_pct = None
    if left is not None and right is not None:
        delta = left["value"] - right["value"]
        delta_pct = delta / right["value"] * 100 if right["value"] else None
    return {
        "fiscal_year": fy,
        "edition": edition,
        "left": left,
        "right": right,
        "delta": delta,
        "delta_pct": delta_pct,
        "status": status,
        "reason": reason,
        **extra,
    }


def _not_run(reason: str) -> list[dict[str, Any]]:
    return [_result("", None, None, None, "not_run", reason)]


def _by_series(rows: list[Row]) -> dict[str, list[Row]]:
    out: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        out[r.series_id].append(r)
    return out


def _edition_year(rows: list[Row]) -> dict[tuple[str, str], Row]:
    return {(r.prov.edition, r.fiscal_year): r for r in rows}


def _r1(by: dict[str, list[Row]], pid: PidFn) -> list[dict[str, Any]]:
    funcs = {
        s: _edition_year(rs) for s, rs in by.items() if s.startswith(COFOG_PREFIX) and s != TES
    }
    totals = _edition_year(by.get(TES, []))
    out = []
    for (ed, fy), tot in sorted(totals.items()):
        parts = [(s, m[(ed, fy)]) for s, m in sorted(funcs.items()) if (ed, fy) in m]
        if not parts:
            continue
        n = len(parts)
        tol = 0.5 * n * GBP_M_IN_BN
        total = sum(r.value for _, r in parts)
        left = _side("sum of pesa.cofog.* functions", total, [r for _, r in parts], pid)
        right = _side(TES, tot.value, [tot], pid)
        gap = abs(total - tot.value)
        ok = gap <= tol + 1e-12
        reason = f"{n} function rows; |delta| {gap:.6f} vs tolerance {tol:.6f} GBP bn"
        if n != len(funcs):
            reason += f"; only {n} of {len(funcs)} function series have a value in this edition"
        out.append(
            _result(fy, ed, left, right, "pass" if ok else "fail", reason, tolerance_abs=tol)
        )
    return out or _not_run("no PESA Table 10.1 edition with a total row and function rows")


def _r2(by: dict[str, list[Row]], pid: PidFn, titles: dict[str, str]) -> list[dict[str, Any]]:
    tes, tme = _edition_year(by.get(TES, [])), _edition_year(by.get(TME, []))
    label = titles.get(TES, "")
    says_tme = "managed expenditure" in label.lower()
    out = []
    for key in sorted(set(tes) & set(tme)):
        ed, fy = key
        left, right = (
            _side(TES, tes[key].value, [tes[key]], pid),
            _side(TME, tme[key].value, [tme[key]], pid),
        )
        if says_tme:
            rel = abs(left["value"] - right["value"]) / right["value"] if right["value"] else 1
            out.append(
                _result(
                    fy,
                    ed,
                    left,
                    right,
                    "pass" if rel <= 0.001 else "fail",
                    f"table total labelled as TME; relative gap {rel:.4%}",
                    tolerance_rel=0.001,
                )
            )
        else:
            gap = right["value"] - left["value"]
            out.append(
                _result(
                    fy,
                    ed,
                    left,
                    right,
                    "info",
                    f"Table 10.1 total is '{label}' (TES, England only), not TME (UK, Table 4.1). "
                    f"TME - TES = {gap:.3f} GBP bn: geography (England vs UK), non-identifiable "
                    "spending and accounting adjustments.",
                )
            )
    return out or _not_run("no edition publishes both Table 10.1 and Table 4.1")


def _outturn_compare(
    a_rows: list[Row],
    b_rows: list[Row],
    a_id: str,
    b_id: str,
    pid: PidFn,
    rel_tol: float,
    note: str,
) -> list[dict[str, Any]]:
    a, _ = stitch(a_rows)
    b, _ = stitch(b_rows)
    out = []
    for fy in sorted({k[1] for k in a} & {k[1] for k in b}):
        ra, rb = a[(a_id, fy)], b[(b_id, fy)]
        if ra.prov.status != "outturn" or rb.prov.status != "outturn":
            continue
        left, right = _side(a_id, ra.value, [ra], pid), _side(b_id, rb.value, [rb], pid)
        rel = abs(left["value"] - right["value"]) / right["value"] if right["value"] else 1
        out.append(
            _result(
                fy,
                f"{ra.prov.vintage} vs {rb.prov.vintage}",
                left,
                right,
                "pass" if rel <= rel_tol else "fail",
                f"{note}; relative gap {rel:.4%} vs tolerance {rel_tol:.2%}",
                tolerance_rel=rel_tol,
            )
        )
    return out


def _r6(by: dict[str, list[Row]], pid: PidFn) -> list[dict[str, Any]]:
    h, _ = stitch(by.get(HMRC_TOTAL, []))
    o, _ = stitch(by.get(OBR_RECEIPTS, []))
    out = []
    for fy in sorted({k[1] for k in h} & {k[1] for k in o}):
        rh, ro = h[(HMRC_TOTAL, fy)], o[(OBR_RECEIPTS, fy)]
        left, right = (
            _side(HMRC_TOTAL, rh.value, [rh], pid),
            _side(OBR_RECEIPTS, ro.value, [ro], pid),
        )
        bad = left["value"] > right["value"]
        out.append(
            _result(
                fy,
                f"{rh.prov.vintage} vs {ro.prov.vintage}",
                left,
                right,
                "fail" if bad else "info",
                "HMRC receipts exceed all public sector current receipts, which should not happen"
                if bad
                else "HMRC cash receipts are narrower than OBR accrued public sector current "
                "receipts (excludes council tax, business rates and other non-HMRC receipts)",
            )
        )
    return out or _not_run("HMRC receipts and OBR current receipts share no fiscal year")


def _r7(by: dict[str, list[Row]], pid: PidFn, trimmed: bool) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def check(total_id: str, line_ids: list[str], tol_per_line: float, comparison: str) -> None:
        totals = _edition_year(by.get(total_id, []))
        lines = {s: _edition_year(by[s]) for s in line_ids}
        for (ed, fy), tot in sorted(totals.items()):
            parts = [(s, m[(ed, fy)]) for s, m in sorted(lines.items()) if (ed, fy) in m]
            if not parts:
                continue
            total = sum(r.value for _, r in parts)
            tol = tol_per_line * len(parts)
            left = _side(f"sum of {comparison} lines", total, [r for _, r in parts], pid)
            right = _side(total_id, tot.value, [tot], pid)
            gap = abs(total - tot.value)
            reason = (
                f"{comparison}: {len(parts)} lines summed; |delta| {gap:.6f} vs tolerance "
                f"{tol:.6f} GBP bn; scope {'GB' if total_id == DWP_GB_TOTAL else 'UK'}"
            )
            out.append(
                _result(
                    fy,
                    ed,
                    left,
                    right,
                    "pass" if gap <= tol + 1e-12 else "fail",
                    reason,
                    comparison=comparison,
                    tolerance_abs=tol,
                )
            )

    top_1a = sorted(
        s
        for s in by
        if s.startswith(DWP_LINE)
        and "." not in s[len(DWP_LINE) :]
        and not s[len(DWP_LINE) :].startswith("total")
    )
    check(DWP_GB_TOTAL, top_1a, 0.5 * GBP_M_IN_BN, "table_1a_lines")
    top_uk = sorted(
        s
        for s in by
        if s.startswith(DWP_UK_LINE)
        and "." not in s[len(DWP_UK_LINE) :]
        and not s[len(DWP_UK_LINE) :].startswith("total")
    )
    check(DWP_UK_TOTAL, top_uk, 0.5 * GBP_M_IN_BN, "uk_welfare_tab_lines")
    return out or _not_run("DWP totals or benefit lines not available")


def run(
    rows: list[Row],
    pid: PidFn,
    titles: dict[str, str],
    sources: dict[str, dict[str, Any]],
    trimmed_sources: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Run R1-R7 over nominal GBP bn rows (all vintages). `sources[id]` has enabled/verdict."""
    by = _by_series(rows)
    psf = sources.get("ons_psf", {})
    results: dict[str, list[dict[str, Any]]] = {
        "R1": _r1(by, pid),
        "R2": _r2(by, pid, titles),
        "R3": _outturn_compare(
            by.get(TME, []),
            by.get(OBR_TME, []),
            TME,
            OBR_TME,
            pid,
            0.01,
            "newest PESA edition vs OBR databank",
        )
        or _not_run("PESA TME and OBR TME share no outturn year"),
        "R4": _not_run(
            "ONS Public Sector Finances is "
            f"{'enabled but has no rows' if psf.get('enabled') else 'disabled'} "
            f"(verdict {psf.get('verdict', 'unknown')}; no verified URL, parser is a stub)"
        ),
        "R5": _not_run(
            "the databank's real-terms TME column is not extracted by the OBR parser "
            "(only its GDP deflator is), so there is nothing to compare our deflated TME with"
        ),
        "R6": _r6(by, pid),
        "R7": _r7(by, pid, "dwp_benefits" in trimmed_sources),
    }
    counts = {"pass": 0, "fail": 0, "info": 0, "not_run": 0}
    rules = []
    for meta in RULES:
        res = results[meta["id"]]
        for r in res:
            counts[r["status"]] += 1
        rules.append({**meta, "results": res})
    return {"summary": counts, "rules": rules}
