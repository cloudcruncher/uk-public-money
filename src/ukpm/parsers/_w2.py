"""Small helpers shared by the wave-2 parsers (ons_psf, ons_households, ons_gdp, pesa_uk,
obr_efo_receipts). Not a source module."""

from __future__ import annotations

from ..provenance import Provenance
from . import FileMeta


def num(v: object) -> float | None:
    return float(v) if isinstance(v, int | float) and not isinstance(v, bool) else None


def text(v: object) -> str:
    return " ".join(v.split()) if isinstance(v, str) else ""


def prov(
    meta: FileMeta,
    sheet: str | None,
    cell: str | None,
    status: str = "outturn",
    vintage: str | None = None,
    api_query: str | None = None,
) -> Provenance:
    return Provenance(
        publisher=meta.source.publisher,
        dataset=meta.source.dataset,
        edition=meta.file.edition,
        publication_date=meta.file.publication_date,
        source_url=meta.file.file_url,
        landing_url=meta.file.landing_url,
        file_sha256=meta.sha256,
        sheet=sheet,
        cell_or_range=cell,
        api_query=api_query,
        licence=meta.source.licence,
        transformations=(),
        status=status,
        vintage=vintage or meta.file.edition,
        retrieved_at=meta.fetched_at,
    )
