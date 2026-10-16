"""Load and validate data/sources.yml."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from .provenance import HOST_ALLOWLIST, LICENCE_ALLOWLIST

VERDICTS = frozenset({"USABLE", "PARTIAL", "UNVERIFIED", "UNUSABLE"})
FORMATS = frozenset({"xlsx", "ods", "csv", "zip"})
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_REQUIRED = (
    "id",
    "publisher",
    "dataset",
    "landing_url",
    "licence",
    "verdict",
    "enabled",
    "files",
)
_FILE_REQUIRED = ("key", "edition", "publication_date", "file_url", "landing_url", "format", "role")


class RegistryError(ValueError):
    pass


@dataclass(frozen=True)
class FileEntry:
    key: str
    edition: str
    publication_date: str
    file_url: str | None
    landing_url: str
    format: str
    sha256: str | None
    role: str


@dataclass(frozen=True)
class Source:
    id: str
    publisher: str
    dataset: str
    landing_url: str
    licence: str
    licence_evidence: str | None
    cadence: str | None
    coverage: dict[str, Any]
    verdict: str
    enabled: bool
    fixture_dir: str | None
    user_agent: str | None
    files: tuple[FileEntry, ...]
    gaps: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    notes: str | None = None
    verdict_reason: str | None = None


def _check_url(url: str, where: str, enforce_host: bool = True) -> None:
    p = urlparse(url)
    if p.scheme != "https":
        raise RegistryError(f"{where}: URL not https: {url}")
    if enforce_host and p.hostname not in HOST_ALLOWLIST:
        raise RegistryError(f"{where}: host {p.hostname!r} not allowlisted")


def _file(raw: dict[str, Any], src_id: str, enabled: bool) -> FileEntry:
    where = f"{src_id}.{raw.get('key', '?')}"
    for k in _FILE_REQUIRED:
        if k not in raw:
            raise RegistryError(f"{where}: missing {k}")
    if raw["format"] not in FORMATS:
        raise RegistryError(f"{where}: bad format {raw['format']!r}")
    pd = raw["publication_date"]
    if isinstance(pd, date):
        pd = pd.isoformat()
    try:
        date.fromisoformat(str(pd))
    except ValueError as e:
        raise RegistryError(f"{where}: publication_date not ISO") from e
    url = raw["file_url"]
    if url is None:
        if enabled:
            raise RegistryError(f"{where}: enabled source has no file_url")
    else:
        _check_url(url, where, enabled)
    _check_url(raw["landing_url"], where, enabled)
    sha = raw.get("sha256")
    if enabled and not sha:
        raise RegistryError(f"{where}: enabled source file has no sha256")
    if sha is not None and not _SHA_RE.match(str(sha)):
        raise RegistryError(f"{where}: sha256 not 64 lowercase hex")
    return FileEntry(
        raw["key"],
        raw["edition"],
        str(pd),
        url,
        raw["landing_url"],
        raw["format"],
        sha,
        raw["role"],
    )


def _source(raw: dict[str, Any]) -> Source:
    sid = raw.get("id", "?")
    for k in _SOURCE_REQUIRED:
        if k not in raw:
            raise RegistryError(f"{sid}: missing {k}")
    if raw["verdict"] not in VERDICTS:
        raise RegistryError(f"{sid}: bad verdict {raw['verdict']!r}")
    enabled = bool(raw["enabled"])
    if enabled and raw["verdict"] not in ("USABLE", "PARTIAL"):
        raise RegistryError(f"{sid}: enabled with verdict {raw['verdict']}")
    if enabled and raw["licence"] not in LICENCE_ALLOWLIST:
        raise RegistryError(f"{sid}: enabled with licence {raw['licence']!r} outside allowlist")
    _check_url(raw["landing_url"], sid, enabled)
    files = tuple(_file(f, sid, enabled) for f in raw["files"] or [])
    keys = [f.key for f in files]
    if len(set(keys)) != len(keys):
        raise RegistryError(f"{sid}: duplicate file key")
    if enabled and not files:
        raise RegistryError(f"{sid}: enabled with no files")
    return Source(
        id=raw["id"],
        publisher=raw["publisher"],
        dataset=raw["dataset"],
        landing_url=raw["landing_url"],
        licence=raw["licence"],
        licence_evidence=raw.get("licence_evidence"),
        cadence=raw.get("cadence"),
        coverage=raw.get("coverage") or {},
        verdict=raw["verdict"],
        enabled=enabled,
        fixture_dir=raw.get("fixture_dir"),
        user_agent=raw.get("user_agent"),
        files=files,
        gaps=tuple(raw.get("gaps") or ()),
        notes=raw.get("notes"),
        verdict_reason=raw.get("verdict_reason"),
    )


def load(path: str | Path) -> list[Source]:
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, list):
        raise RegistryError("sources.yml must be a list")
    sources = [_source(r) for r in data]
    ids = [s.id for s in sources]
    if len(set(ids)) != len(ids):
        raise RegistryError("duplicate source id")
    return sources
