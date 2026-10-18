"""Download pinned files, verify sha256, keep a manifest, resolve offline fixtures."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml

from .provenance import HOST_ALLOWLIST
from .registry import FileEntry, Source

WORK = Path("work")
MAX_BYTES = 25 * 1024 * 1024
DEFAULT_UA = "ukpm/0.1 (+https://github.com/; open-data pipeline)"


class FetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class FetchedFile:
    source_id: str
    file_key: str
    path: Path
    sha256: str
    url: str
    final_url: str
    fetched_at: str
    size: int
    content_type: str
    from_fixture: bool


class _AllowlistRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p = urlparse(newurl)
        if p.scheme != "https" or p.hostname not in HOST_ALLOWLIST:
            raise FetchError(f"redirect to non-allowlisted target: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _manifest_path(work: Path) -> Path:
    return work / "raw" / "manifest.json"


def _load_manifest(work: Path) -> dict:
    p = _manifest_path(work)
    return json.loads(p.read_text()) if p.exists() else {}


def _save_manifest(work: Path, m: dict) -> None:
    p = _manifest_path(work)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(m, indent=2, sort_keys=True))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _cache_path(work: Path, src: Source, f: FileEntry) -> Path:
    return work / "raw" / src.id / f"{f.sha256}.{f.format}"


def _download(src: Source, f: FileEntry, dest: Path) -> tuple[str, str, str, int]:
    opener = urllib.request.build_opener(_AllowlistRedirect)
    req = urllib.request.Request(f.file_url, headers={"User-Agent": src.user_agent or DEFAULT_UA})
    last: Exception | None = None
    for attempt in range(3):
        try:
            with opener.open(req, timeout=60) as r:
                h, size = hashlib.sha256(), 0
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(".part")
                with tmp.open("wb") as out:
                    while chunk := r.read(1 << 16):
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise FetchError(f"{f.key}: larger than {MAX_BYTES} bytes")
                        h.update(chunk)
                        out.write(chunk)
                digest = h.hexdigest()
                if size == 0:
                    # A 200 with no body is a dropped connection: retry it.
                    tmp.unlink(missing_ok=True)
                    raise OSError("empty response body")
                if digest != f.sha256:
                    tmp.unlink(missing_ok=True)
                    raise FetchError(
                        f"{src.id}/{f.key}: sha256 mismatch (got {digest}); publisher replaced "
                        "file in place; re-verify and update sources.yml"
                    )
                tmp.replace(dest)
                return digest, r.geturl(), r.headers.get("Content-Type", ""), size
        except FetchError:
            dest.with_suffix(".part").unlink(missing_ok=True)
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            time.sleep(2**attempt)
    raise FetchError(f"{src.id}/{f.key}: download failed: {last}")


def _fixture(src: Source, f: FileEntry) -> Path | None:
    if not src.fixture_dir:
        return None
    manifest = Path(src.fixture_dir) / "MANIFEST.yml"
    if not manifest.exists():
        return None
    for e in yaml.safe_load(manifest.read_text()) or []:
        if e.get("source_id") == src.id and e.get("original_sha256") == f.sha256:
            p = manifest.parent / e["fixture"]
            if p.exists():
                return p
    return None


def fetch_source(src: Source, *, offline: bool, work: Path = WORK) -> list[FetchedFile]:
    """Return local copies of every file of an enabled source. Offline gaps raise FetchError."""
    manifest = _load_manifest(work)
    out: list[FetchedFile] = []
    for f in src.files:
        cached = _cache_path(work, src, f)
        fixture = None
        if cached.exists() and sha256_file(cached) == f.sha256:
            path, from_fix = cached, False
        elif offline:
            fixture = _fixture(src, f)
            if fixture is None:
                raise FetchError(f"{src.id}/{f.key}: skipped (no offline copy)")
            path, from_fix = fixture, True
        else:
            digest, final, ctype, size = _download(src, f, cached)
            manifest[digest] = {
                "source_id": src.id,
                "file_key": f.key,
                "url": f.file_url,
                "final_url": final,
                "fetched_at": _now(),
                "size": size,
                "content_type": ctype,
            }
            _save_manifest(work, manifest)
            path, from_fix = cached, False
        info = manifest.get(f.sha256, {})
        out.append(
            FetchedFile(
                source_id=src.id,
                file_key=f.key,
                path=path,
                sha256=f.sha256,
                url=f.file_url,
                final_url=info.get("final_url", f.file_url),
                fetched_at=info.get("fetched_at", _now()),
                size=path.stat().st_size,
                content_type=info.get("content_type", ""),
                from_fixture=from_fix,
            )
        )
    return out
