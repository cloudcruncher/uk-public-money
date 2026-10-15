from __future__ import annotations

from pathlib import Path

import pytest

from ukpm.provenance import Provenance, Row, Transformation

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def prov() -> Provenance:
    return Provenance(
        publisher="HM Treasury",
        dataset="PESA",
        edition="PESA 2026",
        publication_date="2026-07-16",
        source_url="https://assets.publishing.service.gov.uk/media/x/PESA.xlsx",
        landing_url="https://www.gov.uk/government/statistics/public-expenditure-statistical-analyses-2026",
        file_sha256="a" * 64,
        sheet="10.1",
        cell_or_range="F20",
        api_query=None,
        licence="OGL-UK-3.0",
        transformations=(Transformation("scale", "£m -> £bn (x 0.001)"),),
        status="outturn",
        vintage="PESA 2026",
        retrieved_at="2026-10-15T10:00:00Z",
    )


@pytest.fixture
def make_row(prov):
    def _make(series="pesa.tme", year="2024-25", value=100.0, unit="gbp_bn", **changes):
        from dataclasses import replace

        return Row(series, year, "fiscal_year", value, unit, "UK", replace(prov, **changes))

    return _make
