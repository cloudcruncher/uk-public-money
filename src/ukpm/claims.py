"""Claim checker: data/claims.yml curated claims -> claims.json with computed verdicts.

A curator supplies the claim text, who said it, where, and the figure claimed. The official
figure, the verdict, the delta and the check URL are always computed from published points;
any `official`/`verdict` keys in the YAML are ignored.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

# multiplier from the claimed unit to GBP billion
MONEY_TO_BN = {"GBP_m": 0.001, "GBP_bn": 1.0, "GBP_tn": 1000.0}
PRICE_BASES = ("nominal", "real", "pct_gdp")

# lookup(series_id, price_basis, fiscal_year) -> (point, series_title) or None
Lookup = Callable[[str, str, str], "tuple[dict[str, Any], str] | None"]


def load_claims(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text())
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError(f"{p}: claims file must be a list")
    return data


def _problems(c: dict[str, Any]) -> list[str]:
    out = []
    for k in ("id", "text", "said_url", "claimed", "maps_to"):
        if not c.get(k):
            out.append(f"missing {k}")
    if c.get("said_url") and not str(c["said_url"]).startswith("https://"):
        out.append("said_url not https")
    cl, mp = c.get("claimed") or {}, c.get("maps_to") or {}
    for k in ("value", "unit", "fiscal_year", "price_basis"):
        if cl.get(k) is None:
            out.append(f"claimed.{k} missing")
    if cl.get("price_basis") not in (None, *PRICE_BASES):
        out.append("claimed.price_basis must be nominal, real or pct_gdp")
    if not mp.get("series_id"):
        out.append("maps_to.series_id missing")
    return out


def evaluate(
    claims: list[dict[str, Any]],
    lookup: Lookup,
    definitions_by_series: dict[str, set[str]],
) -> dict[str, Any]:
    out, rejected = [], []
    for c in claims:
        bad = _problems(c) if isinstance(c, dict) else ["not a mapping"]
        if bad:
            rejected.append({"id": c.get("id") if isinstance(c, dict) else None, "problems": bad})
            continue
        cl, mp = c["claimed"], c["maps_to"]
        sid, fy, basis = mp["series_id"], str(cl["fiscal_year"]), cl["price_basis"]
        tol = float(c.get("tolerance_rel", 0.02))
        entry: dict[str, Any] = {
            "id": c["id"],
            "text": c["text"],
            "said_by": c.get("said_by"),
            "said_url": c["said_url"],
            "said_date": str(c["said_date"]) if c.get("said_date") else None,
            "claimed": {**cl, "fiscal_year": fy},
            "maps_to": {"series_id": sid, "definition_id": mp.get("definition_id")},
            "tolerance_rel": tol,
            "series_title": None,
            "official": None,
            "verdict": "no_official_figure",
            "delta_pct": None,
            "check_url": None,
        }
        found = lookup(sid, basis, fy)
        if found is not None:
            point, title = found
            entry["series_title"] = title
            entry["official"] = {
                k: point[k] for k in ("value", "unit", "status", "vintage", "provenance_id")
            }
            entry["check_url"] = f"check.html#p={point['provenance_id']}"
            entry["verdict"], entry["delta_pct"] = _verdict(
                cl, point, tol, mp.get("definition_id"), definitions_by_series.get(sid, set())
            )
        out.append(entry)
    return {"claims": out, "rejected": rejected}


def _verdict(
    claimed: dict[str, Any],
    point: dict[str, Any],
    tol: float,
    definition_id: str | None,
    series_defs: set[str],
) -> tuple[str, float | None]:
    if definition_id and definition_id not in series_defs:
        return "not_comparable", None
    unit, off_unit = claimed["unit"], point["unit"]
    if unit == "percent":
        if off_unit != "percent":
            return "not_comparable", None
        official = point["value"]
    elif unit in MONEY_TO_BN and off_unit.startswith("GBP_bn"):
        official = point["value"] / MONEY_TO_BN[unit]
    else:
        return "not_comparable", None
    if not official:
        return "not_comparable", None
    delta = (float(claimed["value"]) - official) / abs(official)
    return ("consistent" if abs(delta) <= tol else "differs"), delta * 100
