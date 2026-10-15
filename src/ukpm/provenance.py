"""Provenance, Row and Transformation records plus the completeness gate."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from urllib.parse import urlparse

LICENCE_ALLOWLIST = frozenset({"OGL-UK-3.0"})
STATUSES = frozenset({"outturn", "forecast"})
HOST_ALLOWLIST = frozenset(
    {
        "assets.publishing.service.gov.uk",
        "www.gov.uk",
        "obr.uk",
        "www.ons.gov.uk",
        "api.beta.ons.gov.uk",
    }
)
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class ProvenanceError(ValueError):
    """Raised when a provenance record is incomplete or invalid."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("; ".join(problems))


@dataclass(frozen=True)
class Transformation:
    op: str
    detail: str
    inputs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Provenance:
    publisher: str
    dataset: str
    edition: str
    publication_date: str
    source_url: str
    landing_url: str
    file_sha256: str
    sheet: str | None
    cell_or_range: str | None
    api_query: str | None
    licence: str
    transformations: tuple[Transformation, ...]
    status: str
    vintage: str
    retrieved_at: str


@dataclass(frozen=True)
class Row:
    series_id: str
    fiscal_year: str
    period_basis: str
    value: float
    unit: str
    geography: str
    prov: Provenance


def _blank(v: object) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def https_allowed(url: str) -> bool:
    p = urlparse(url)
    return p.scheme == "https" and p.hostname in HOST_ALLOWLIST


def _iso_date(s: object) -> bool:
    try:
        date.fromisoformat(s)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return True


def _iso_dt(s: object) -> bool:
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        return False
    return True


def problems(p: Provenance) -> list[str]:
    """Return every reason the record is incomplete or invalid (empty if fine)."""
    out: list[str] = []
    for f in ("publisher", "dataset", "edition", "vintage", "licence", "status"):
        if _blank(getattr(p, f)):
            out.append(f"missing {f}")
    if not _iso_date(p.publication_date):
        out.append("publication_date missing or not ISO date")
    if not _iso_dt(p.retrieved_at):
        out.append("retrieved_at missing or not ISO datetime")
    for f in ("source_url", "landing_url"):
        v = getattr(p, f)
        if _blank(v):
            out.append(f"missing {f}")
        elif not https_allowed(v):
            out.append(f"{f} not https on an allowlisted host")
    if not isinstance(p.file_sha256, str) or not _SHA_RE.match(p.file_sha256):
        out.append("file_sha256 missing or not 64 lowercase hex")
    if not _blank(p.licence) and p.licence not in LICENCE_ALLOWLIST:
        out.append(f"licence {p.licence!r} not in allowlist")
    if not _blank(p.status) and p.status not in STATUSES:
        out.append(f"status {p.status!r} not outturn/forecast")
    if _blank(p.sheet) and _blank(p.api_query):
        out.append("need sheet+cell_or_range or api_query")
    if not _blank(p.sheet) and _blank(p.cell_or_range):
        out.append("cell_or_range required when sheet is set")
    if p.transformations is None:
        out.append("transformations missing (use an empty tuple for none)")
    return out


def validate(p: Provenance) -> Provenance:
    """Raise ProvenanceError unless the record is complete; return it otherwise."""
    found = problems(p)
    if found:
        raise ProvenanceError(found)
    return p


def to_dict(p: Provenance) -> dict:
    return asdict(p)


def provenance_id(source_id: str, p: Provenance) -> str:
    """Stable id '<source_id>-<12 hex>' from the full record content."""
    blob = json.dumps(to_dict(p), sort_keys=True, default=str).encode()
    return f"{source_id}-{hashlib.sha256(blob).hexdigest()[:12]}"
