"""Unit conversions. Each returns a new Row with one Transformation appended."""

from __future__ import annotations

from dataclasses import replace

from .provenance import Row, Transformation, provenance_id


class MissingDenominator(LookupError):
    """A year has no deflator/GDP value; the variant is not produced."""


def _derive(row: Row, t: Transformation, value: float, unit: str, status: str) -> Row:
    prov = replace(row.prov, transformations=(*row.prov.transformations, t), status=status)
    return replace(row, prov=prov, value=value, unit=unit)


def _pid(row: Row) -> str:
    return provenance_id(row.series_id.split(".")[0], row.prov)


def _by_year(rows: list[Row]) -> dict[str, Row]:
    return {r.fiscal_year: r for r in rows}


def _need_gbp(row: Row) -> None:
    if row.unit != "gbp_bn":
        raise ValueError("real/pct_gdp variants only for unit gbp_bn")


def _status(a: str, b: str) -> str:
    return "forecast" if "forecast" in (a, b) else "outturn"


def scale(row: Row, factor: float, detail: str, unit: str | None = None) -> Row:
    t = Transformation("scale", detail)
    return _derive(row, t, row.value * factor, unit or row.unit, row.prov.status)


def deflate(row: Row, deflator_rows: list[Row], base_year: str, detail: str | None = None) -> Row:
    """real = nominal * D[base] / D[year]; unit stays gbp_bn."""
    _need_gbp(row)
    d = _by_year(deflator_rows)
    if row.fiscal_year not in d or base_year not in d or not d[row.fiscal_year].value:
        raise MissingDenominator(f"deflator missing for {row.fiscal_year} or {base_year}")
    dy, db = d[row.fiscal_year], d[base_year]
    t = Transformation(
        "deflate",
        detail or f"GDP deflator, {dy.prov.vintage}, {base_year}=100",
        (_pid(dy), _pid(db)),
    )
    return _derive(
        row, t, row.value * db.value / dy.value, "gbp_bn", _status(row.prov.status, dy.prov.status)
    )


def pct_gdp(row: Row, gdp_rows: list[Row]) -> Row:
    """100 * value / nominal GDP for the same fiscal-year label."""
    _need_gbp(row)
    g = _by_year(gdp_rows).get(row.fiscal_year)
    if g is None or not g.value:
        raise MissingDenominator(f"GDP missing for {row.fiscal_year}")
    t = Transformation("pct_gdp", f"100 x value / nominal GDP ({g.prov.vintage})", (_pid(g),))
    return _derive(
        row, t, 100 * row.value / g.value, "pct", _status(row.prov.status, g.prov.status)
    )


def _pop_pid_detail(pop: Row) -> str:
    return (
        f"{pop.geography} population, ONS mid-{pop.fiscal_year[:4]} estimate ({pop.prov.vintage})"
    )


def per_person(row: Row, pop_rows: list[Row]) -> Row:
    """value x 1e9 / persons, same fiscal-year label; unit gbp_per_person."""
    _need_gbp(row)
    p = _by_year(pop_rows).get(row.fiscal_year)
    if p is None or not p.value:
        raise MissingDenominator(f"no ONS mid-year estimate for {row.fiscal_year}")
    t = Transformation("per_person", f"x 1e9 / {_pop_pid_detail(p)}", (_pid(p),))
    return _derive(
        row,
        t,
        row.value * 1e9 / p.value,
        "gbp_per_person",
        _status(row.prov.status, p.prov.status),
    )


def per_household(row: Row, hh_rows: list[Row]) -> Row:
    """value x 1e9 / (households x 1000); unit gbp_per_household.

    The ONS household count (`ons_households.uk`, thousands) is the Labour Force Survey estimate
    for the April-June quarter of calendar year YYYY and carries the fiscal-year label
    YYYY-(YY+1) that contains it. It is matched to the spend of that whole fiscal year: the
    spend runs April to March, the count is a point-in-time estimate taken at its start. The
    alignment is written into the transformation detail.
    """
    _need_gbp(row)
    h = _by_year(hh_rows).get(row.fiscal_year)
    if h is None or not h.value:
        raise MissingDenominator(f"no ONS household estimate for {row.fiscal_year}")
    if h.unit != "thousands":
        raise ValueError("household count must be in thousands")
    t = Transformation(
        "per_household",
        f"x 1e9 / (households x 1000); households: ONS Labour Force Survey, April-June "
        f"{h.fiscal_year[:4]} quarter ({h.prov.vintage}), matched to the fiscal year "
        f"{h.fiscal_year} that contains it; the spend covers the whole fiscal year, the count is "
        "one quarter at its start",
        (_pid(h),),
    )
    return _derive(
        row,
        t,
        row.value * 1e9 / (h.value * 1000),
        "gbp_per_household",
        _status(row.prov.status, h.prov.status),
    )


def share(part: Row, total: Row, op: str = "per_100") -> Row:
    """100 x part / total; same fiscal year, unit and edition. per_100 -> gbp_per_100."""
    if op not in ("per_100", "share_of_total"):
        raise ValueError(f"unknown share op {op!r}")
    if (part.fiscal_year, part.unit, part.prov.edition) != (
        total.fiscal_year,
        total.unit,
        total.prov.edition,
    ):
        raise ValueError("mixed editions, years or units")
    if not total.value:
        raise MissingDenominator(f"zero or missing total for {total.fiscal_year}")
    word = "out of every GBP 100" if op == "per_100" else "share of the total"
    t = Transformation(
        op, f"100 x part / total ({total.series_id}, {total.prov.edition}): {word}", (_pid(total),)
    )
    return _derive(
        part,
        t,
        100 * part.value / total.value,
        "gbp_per_100" if op == "per_100" else "pct",
        _status(part.prov.status, total.prov.status),
    )


def per_claimant(spend: Row, caseload: Row) -> Row:
    """spend (GBP bn) x 1e9 / (caseload in thousands x 1000); same year and edition."""
    _need_gbp(spend)
    if caseload.unit != "thousand_cases":
        raise ValueError("caseload must be thousand_cases")
    if (spend.fiscal_year, spend.prov.edition) != (caseload.fiscal_year, caseload.prov.edition):
        raise ValueError("mixed editions or years")
    if not caseload.value:
        raise MissingDenominator(f"caseload is zero or missing for {caseload.fiscal_year}")
    t = Transformation(
        "per_claimant",
        f"x 1e9 / (caseload x 1000), {caseload.series_id}, {caseload.prov.edition}",
        (_pid(caseload),),
    )
    return _derive(
        spend,
        t,
        spend.value * 1e9 / (caseload.value * 1000),
        "gbp_per_claimant",
        _status(spend.prov.status, caseload.prov.status),
    )


def remainder(total: Row, parts: list[Row], label: str, strict: bool = True) -> Row:
    """total - sum(parts); the location is the total's.

    Strict (default): parts must match the total's year, unit and edition. Non-strict (windows
    that span several monthly files): only the unit must match.
    """
    for p in parts:
        same = (p.fiscal_year, p.prov.edition) == (total.fiscal_year, total.prov.edition)
        if p.unit != total.unit or (strict and not same):
            raise ValueError("mixed editions, years or units")
    status = "forecast" if any(p.prov.status == "forecast" for p in parts) else total.prov.status
    t = Transformation(
        "remainder",
        f"{label}: {total.series_id} minus the listed parts",
        tuple(_pid(p) for p in parts),
    )
    return _derive(total, t, total.value - sum(p.value for p in parts), total.unit, status)


def sum_rows(primary: Row, others: list[Row], op: str, detail: str) -> Row:
    """primary + sum(others); inputs are the others' ids (the primary is the row's own cell)."""
    t = Transformation(op, detail, tuple(_pid(o) for o in others))
    status = (
        "forecast"
        if "forecast" in {r.prov.status for r in (primary, *others)}
        else primary.prov.status
    )
    return _derive(primary, t, primary.value + sum(o.value for o in others), primary.unit, status)
