"""Stitching across editions and reconciliation rules R1-R14.

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

from . import units
from .parsers.pesa_uk import ROUNDING as PESA_UK_ROUNDING_GBP_M
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

EFO_UC = "obr_efo.welfare_cap.universal_credit"
DWP_UC = "dwp_benefits.exp.universal_credit.within_welfare_cap"
EFO_NI = "obr_efo.welfare_cap.ni_social_security"
DWP_NI = "dwp_benefits.uk_welfare.northern_ireland_social_security.within_the_welfare_cap"
EFO_VINTAGE = "OBR EFO March 2026"
DWP_VINTAGE = "DWP Spring Forecast 2026"
CO_TOTAL = "cabinet_office_spend.total."
CO_MONTH_BOUNDS = (10e6, 1e9)  # GBP
CO_WINDOW_BOUNDS = (0.5e9, 5e9)
CO_WINDOW_MONTHS = 12

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
        "title": "ONS PSF central government TME vs PESA / OBR public sector TME",
        "description": "ONS PSF cg_tme is CENTRAL GOVERNMENT total managed expenditure; PESA and "
        "OBR TME are PUBLIC SECTOR (they also include local government and public corporations, "
        "net of transfers). The definitions differ, so a gap is expected and shown as information "
        "with the delta. It fails only if central government exceeds the public sector total, "
        "which cannot happen. Outturn years only.",
        "tolerance": {
            "abs": None,
            "rel": None,
            "unit": "fail only if central govt > public sector",
        },
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
    {
        "id": "R8",
        "title": "OBR EFO Universal Credit vs DWP Universal Credit (welfare cap)",
        "description": "OBR EFO March 2026 sheet 4.9 Universal credit vs the DWP Spring Forecast "
        "2026 Universal Credit line within the welfare cap, per overlapping year. Run only for "
        "the pair of editions that share a forecast round; other pairs are information. Known "
        "result: 2024-25 is outturn in both files yet differs by about 1.1% (OBR 52.83, DWP 53.42 "
        "GBP bn); the forecast years agree within 0.2%. Neither file says why, so the cause is "
        "unconfirmed (possibly a different outturn vintage or scope); the failure stays visible.",
        "tolerance": {"abs": None, "rel": 0.01, "unit": "relative"},
    },
    {
        "id": "R9",
        "title": "OBR EFO Northern Ireland social security vs DWP UK welfare tab",
        "description": "OBR EFO March 2026 sheet 4.9 NI social security in the welfare cap vs the "
        "DWP Spring Forecast 2026 UK welfare tab Northern Ireland social security within the "
        "welfare cap, per overlapping year. Same forecast-round rule as R8.",
        "tolerance": {"abs": None, "rel": 0.01, "unit": "relative"},
    },
    {
        "id": "R10",
        "title": "Cabinet Office spend: sanity bounds",
        "description": "Wide plausibility bounds, not an official total. Each month's total of "
        "payments over GBP 25,000 should be between GBP 10m and GBP 1bn, and the latest 12 "
        "consecutive months should total between GBP 0.5bn and GBP 5bn.",
        "tolerance": {"abs": None, "rel": None, "unit": "bounds in GBP, see description"},
    },
    {
        "id": "R11",
        "title": "PESA UK Table 5.2 TME vs PESA Table 4.1 TME",
        "description": "Same PESA edition, two tables: the UK COFOG table (5.2) total managed "
        "expenditure against the headline TME in Table 4.1. Both are UK public sector TME.",
        "tolerance": {"abs": None, "rel": 0.001, "unit": "relative"},
    },
    {
        "id": "R12",
        "title": "PESA UK Table 5.2 internal sums",
        "description": "(a) The ten COFOG functions plus EU transactions equal Total Expenditure "
        "on Services. (b) Total Expenditure on Services plus accounting adjustments equals TME.",
        "tolerance": {
            "abs": PESA_UK_ROUNDING_GBP_M * GBP_M_IN_BN,
            "rel": None,
            "unit": "GBP bn (rounding of 11 lines at GBP 1m)",
        },
    },
    {
        "id": "R13",
        "title": "HMRC receipts vs OBR EFO receipts (total, income tax, NICs, VAT, corp tax)",
        "description": "Both are on a cash basis. Where both are outturn, the HMRC tax receipts "
        "and the OBR EFO table 3.8 are the same series and must agree within 1%. Where HMRC has "
        "outturn but the OBR EFO still holds a forecast for that year, the gap is forecast error, "
        "shown as information.",
        "tolerance": {"abs": None, "rel": 0.01, "unit": "relative"},
    },
    {
        "id": "R14",
        "title": "ONS PSF central government identities and definitions",
        "description": "(a) Gross expenditure minus receipts equals net borrowing. (b) cg_tme and "
        "cg_total_expenditure_gross are different definitions (TME is net of some receipts and "
        "adds capital items); the gap is shown as information and the two are never mixed.",
        "tolerance": {"abs": 0.001, "rel": None, "unit": "GBP bn (a); (b) information only"},
    },
]

# Table 1a rows printed below "Total benefit expenditure" that restate spending already counted
# in the lines above it (by funder), so adding them to the lines double-counts.
R7_MEMO_LINES = frozenset(
    {
        "expenditure_covered_by_departmental_expenditure_limit",
        "benefits_funded_by_local_authorities",
    }
)


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


PSF_TME = "ons_psf.cg_tme"
PSF_GROSS = "ons_psf.cg_total_expenditure_gross"
PSF_RECEIPTS = "ons_psf.cg_receipts"
PSF_BORROW = "ons_psf.cg_net_borrowing"
UK_TME = "pesa_uk.tme"
UK_SERVICES = "pesa_uk.services"
UK_ADJ = "pesa_uk.accounting_adjustments"
UK_FUNCS = (
    "general_public_services defence public_order_and_safety economic_affairs "
    "environment_protection housing_and_community_amenities health recreation_culture_religion "
    "education social_protection eu_transactions"
).split()
RECEIPT_LINES = ("total", "income_tax", "nics", "vat", "corporation_tax")


def _latest(rows: list[Row], sid: str) -> dict[str, Row]:
    st, _ = stitch(rows)
    return {fy: r for (s, fy), r in st.items() if s == sid}


def _r4(by: dict[str, list[Row]], pid: PidFn) -> list[dict[str, Any]]:
    cg = _latest(by.get(PSF_TME, []), PSF_TME)
    out = []
    for other_id in (TME, OBR_TME):
        ot = _latest(by.get(other_id, []), other_id)
        for fy in sorted(set(cg) & set(ot)):
            a, b = cg[fy], ot[fy]
            if a.prov.status != "outturn" or b.prov.status != "outturn":
                continue
            left, right = _side(PSF_TME, a.value, [a], pid), _side(other_id, b.value, [b], pid)
            bad = left["value"] > right["value"]
            out.append(
                _result(
                    fy,
                    f"{a.prov.vintage} vs {b.prov.vintage}",
                    left,
                    right,
                    "fail" if bad else "info",
                    "central government TME exceeds public sector TME, which should not happen"
                    if bad
                    else "ONS PSF cg_tme is central government only; "
                    f"{other_id} is public sector TME (adds local government and public "
                    "corporations), so the gap is a definition difference, not an error",
                )
            )
    return out or _not_run("ONS PSF cg_tme and PESA/OBR TME share no outturn year")


def _r11(by: dict[str, list[Row]], pid: PidFn) -> list[dict[str, Any]]:
    return _outturn_compare(
        by.get(UK_TME, []),
        by.get(TME, []),
        UK_TME,
        TME,
        pid,
        0.001,
        "PESA Table 5.2 TME vs Table 4.1 TME",
    ) or _not_run("PESA UK TME and PESA TME share no outturn year")


def _r12(by: dict[str, list[Row]], pid: PidFn) -> list[dict[str, Any]]:
    funcs = {f: _latest(by.get(f"pesa_uk.{f}", []), f"pesa_uk.{f}") for f in UK_FUNCS}
    svc = _latest(by.get(UK_SERVICES, []), UK_SERVICES)
    adj = _latest(by.get(UK_ADJ, []), UK_ADJ)
    tme = _latest(by.get(UK_TME, []), UK_TME)
    tol = PESA_UK_ROUNDING_GBP_M * GBP_M_IN_BN
    out = []
    for fy in sorted(svc):
        if all(fy in f for f in funcs.values()):
            rs = [f[fy] for f in funcs.values()]
            total = sum(r.value for r in rs)
            left = _side("sum(pesa_uk functions + eu_transactions)", total, rs, pid)
            right = _side(UK_SERVICES, svc[fy].value, [svc[fy]], pid)
            gap = abs(total - svc[fy].value)
            out.append(
                _result(
                    fy,
                    svc[fy].prov.vintage,
                    left,
                    right,
                    "pass" if gap <= tol else "fail",
                    f"ten functions + EU transactions vs services; gap {gap:.4f} bn vs {tol} bn",
                )
            )
        if fy in adj and fy in tme:
            rs = [svc[fy], adj[fy]]
            total = svc[fy].value + adj[fy].value
            left = _side("pesa_uk.services + pesa_uk.accounting_adjustments", total, rs, pid)
            right = _side(UK_TME, tme[fy].value, [tme[fy]], pid)
            gap = abs(total - tme[fy].value)
            out.append(
                _result(
                    fy,
                    tme[fy].prov.vintage,
                    left,
                    right,
                    "pass" if gap <= tol else "fail",
                    f"services + accounting adjustments vs TME; gap {gap:.4f} bn vs {tol} bn",
                )
            )
    return out or _not_run("PESA Table 5.2 rows not available")


def _r13(by: dict[str, list[Row]], pid: PidFn) -> list[dict[str, Any]]:
    out = []
    for line in RECEIPT_LINES:
        h_id = f"hmrc_receipts.{line}"
        o_id = "obr_efo_receipts.total_hmrc" if line == "total" else f"obr_efo_receipts.{line}"
        h, o = _latest(by.get(h_id, []), h_id), _latest(by.get(o_id, []), o_id)
        for fy in sorted(set(h) & set(o)):
            rh, ro = h[fy], o[fy]
            left, right = _side(h_id, rh.value, [rh], pid), _side(o_id, ro.value, [ro], pid)
            rel = abs(rh.value - ro.value) / ro.value if ro.value else 1
            ed = f"{rh.prov.vintage} vs {ro.prov.vintage}"
            if rh.prov.status == "outturn" and ro.prov.status == "outturn":
                out.append(
                    _result(
                        fy,
                        ed,
                        left,
                        right,
                        "pass" if rel <= 0.01 else "fail",
                        f"both outturn; relative gap {rel:.4%} vs tolerance 1.00%",
                        tolerance_rel=0.01,
                    )
                )
            elif rh.prov.status == "outturn":
                out.append(
                    _result(
                        fy,
                        ed,
                        left,
                        right,
                        "info",
                        f"HMRC outturn vs OBR EFO forecast for the same year; relative gap "
                        f"{rel:.4%} is forecast error, not a data mismatch",
                    )
                )
    return out or _not_run("HMRC receipts and OBR EFO receipts share no fiscal year")


def _r14(by: dict[str, list[Row]], pid: PidFn) -> list[dict[str, Any]]:
    g, rc, nb = (
        _latest(by.get(PSF_GROSS, []), PSF_GROSS),
        _latest(by.get(PSF_RECEIPTS, []), PSF_RECEIPTS),
        _latest(by.get(PSF_BORROW, []), PSF_BORROW),
    )
    tme = _latest(by.get(PSF_TME, []), PSF_TME)
    out = []
    tol = 0.001
    for fy in sorted(set(g) & set(rc) & set(nb)):
        diff = g[fy].value - rc[fy].value
        left = _side("cg_total_expenditure_gross - cg_receipts", diff, [g[fy], rc[fy]], pid)
        right = _side(PSF_BORROW, nb[fy].value, [nb[fy]], pid)
        gap = abs(diff - nb[fy].value)
        out.append(
            _result(
                fy,
                g[fy].prov.vintage,
                left,
                right,
                "pass" if gap <= tol else "fail",
                f"gross expenditure minus receipts vs net borrowing; gap {gap:.4f} bn vs {tol} bn",
            )
        )
    for fy in sorted(set(g) & set(tme)):
        out.append(
            _result(
                fy,
                g[fy].prov.vintage,
                _side(PSF_TME, tme[fy].value, [tme[fy]], pid),
                _side(PSF_GROSS, g[fy].value, [g[fy]], pid),
                "info",
                "cg_tme and cg_total_expenditure_gross are different ONS definitions; "
                "the gap is shown, and the two are never mixed in one series",
            )
        )
    return out or _not_run("ONS PSF central government rows not available")


def _r7(by: dict[str, list[Row]], pid: PidFn) -> list[dict[str, Any]]:
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
        and s[len(DWP_LINE) :] not in R7_MEMO_LINES
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


def _efo_vs_dwp(
    by: dict[str, list[Row]], pid: PidFn, efo_id: str, dwp_id: str
) -> list[dict[str, Any]]:
    efo, dwp = by.get(efo_id, []), by.get(dwp_id, [])
    if not efo or not dwp:
        return _not_run(
            f"{efo_id if not efo else dwp_id} has no rows (source disabled or not built)"
        )
    out = []
    for e in sorted(efo, key=lambda r: r.fiscal_year):
        for d in dwp:
            if d.fiscal_year != e.fiscal_year:
                continue
            left, right = _side(efo_id, e.value, [e], pid), _side(dwp_id, d.value, [d], pid)
            edition = f"{e.prov.vintage} vs {d.prov.vintage}"
            if (e.prov.vintage, d.prov.vintage) != (EFO_VINTAGE, DWP_VINTAGE):
                out.append(
                    _result(
                        e.fiscal_year,
                        edition,
                        left,
                        right,
                        "info",
                        "different forecast rounds; not compared",
                    )
                )
                continue
            rel = abs(left["value"] - right["value"]) / right["value"] if right["value"] else 1
            out.append(
                _result(
                    e.fiscal_year,
                    edition,
                    left,
                    right,
                    "pass" if rel <= 0.01 else "fail",
                    f"same forecast round; relative gap {rel:.4%} vs tolerance 1.00%",
                    tolerance_rel=0.01,
                )
            )
    return out or _not_run("OBR EFO and DWP share no fiscal year for this line")


def _co_month(r: Row) -> str:
    return r.series_id[len(CO_TOTAL) :]  # 'YYYY_MM'


def _consecutive(months: list[str]) -> bool:
    idx = sorted(int(m[:4]) * 12 + int(m[5:7]) for m in months)
    return all(b - a == 1 for a, b in zip(idx, idx[1:], strict=False))


def co_window(co_rows: list[Row]) -> tuple[Row, list[Row]] | None:
    """The sum of the latest 12 consecutive monthly totals: (derived row, the 12 month rows).

    The derived row is built by `units.sum_rows` on the oldest month, so its provenance id is the
    same wherever it is computed. None if fewer than 12 consecutive months are present.
    """
    totals = sorted(
        (r for r in co_rows if r.series_id.startswith(CO_TOTAL)), key=lambda r: _co_month(r)
    )
    if len(totals) < CO_WINDOW_MONTHS:
        return None
    last = totals[-CO_WINDOW_MONTHS:]
    if not _consecutive([_co_month(r) for r in last]):
        return None
    first, rest = last[0], last[1:]
    row = units.sum_rows(
        first,
        rest,
        "sum_months",
        f"sum of 12 monthly totals, {_co_month(first).replace('_', '-')} to "
        f"{_co_month(last[-1]).replace('_', '-')}; this record's own range is the first month, "
        "the other 11 months are its inputs",
    )
    return row, last


def _co_side(series_id: str, value: float, rows: list[Row], pid: PidFn) -> dict[str, Any]:
    pids = [pid(r) for r in rows]
    return {
        "series_id": series_id,
        "value": value,
        "unit": "GBP",
        "provenance_id": pids[0] if len(pids) == 1 else None,
        "provenance_ids": pids,
    }


def _r10(co_rows: list[Row], pid: PidFn) -> list[dict[str, Any]]:
    totals = sorted(
        (r for r in co_rows if r.series_id.startswith(CO_TOTAL)), key=lambda r: _co_month(r)
    )
    if not totals:
        return _not_run("Cabinet Office spend is disabled or has no rows")
    lo, hi = CO_MONTH_BOUNDS
    out = []
    for r in totals:
        ok = lo <= r.value <= hi
        out.append(
            _result(
                r.fiscal_year,
                r.prov.edition,
                _co_side(r.series_id, r.value, [r], pid),
                None,
                "pass" if ok else "fail",
                f"month {_co_month(r).replace('_', '-')}: total GBP {r.value:,.2f} "
                f"{'inside' if ok else 'outside'} the bounds GBP {lo:,.0f} to {hi:,.0f}",
            )
        )
    win = co_window(totals)
    if win is None:
        out.append(
            _result(
                "",
                None,
                None,
                None,
                "not_run",
                f"fewer than {CO_WINDOW_MONTHS} consecutive months are present, so the "
                "12-month window cannot be checked",
            )
        )
    else:
        row, months = win
        wlo, whi = CO_WINDOW_BOUNDS
        ok = wlo <= row.value <= whi
        out.append(
            _result(
                row.fiscal_year,
                f"{_co_month(months[0]).replace('_', '-')} to "
                f"{_co_month(months[-1]).replace('_', '-')}",
                _co_side("cabinet_office_spend.window", row.value, [row], pid),
                None,
                "pass" if ok else "fail",
                f"12-month total GBP {row.value:,.2f} {'inside' if ok else 'outside'} the "
                f"bounds GBP {wlo:,.0f} to {whi:,.0f}",
            )
        )
    return out


def run(
    rows: list[Row],
    pid: PidFn,
    titles: dict[str, str],
    sources: dict[str, dict[str, Any]],
    trimmed_sources: frozenset[str] = frozenset(),
    co_rows: list[Row] | None = None,
) -> dict[str, Any]:
    """Run R1-R14 over nominal GBP bn rows (all vintages). `sources[id]` has enabled/verdict.

    `co_rows` are the published Cabinet Office monthly total rows (pounds, not in `rows`).
    """
    by = _by_series(rows)
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
        "R4": _r4(by, pid),
        "R5": _not_run(
            "the databank's real-terms TME column is not extracted by the OBR parser "
            "(only its GDP deflator is), so there is nothing to compare our deflated TME with"
        ),
        "R6": _r6(by, pid),
        "R7": _r7(by, pid),
        "R8": _efo_vs_dwp(by, pid, EFO_UC, DWP_UC),
        "R9": _efo_vs_dwp(by, pid, EFO_NI, DWP_NI),
        "R10": _r10(co_rows or [], pid),
        "R11": _r11(by, pid),
        "R12": _r12(by, pid),
        "R13": _r13(by, pid),
        "R14": _r14(by, pid),
    }
    counts = {"pass": 0, "fail": 0, "info": 0, "not_run": 0}
    rules = []
    for meta in RULES:
        res = results[meta["id"]]
        for r in res:
            counts[r["status"]] += 1
        rules.append({**meta, "results": res})
    return {"summary": counts, "rules": rules}
