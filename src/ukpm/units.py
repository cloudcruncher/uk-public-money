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
