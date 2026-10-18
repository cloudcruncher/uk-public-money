"""Report new editions: compare publisher landing pages with the files pinned in sources.yml.

The daily refresh only re-downloads pinned files, so a new publication is invisible to it.
This reads each landing page, lists data-file links on allowlisted hosts that are not pinned,
and for every pinned URL checks the live bytes still match the pinned sha256. It never edits
sources.yml: a new edition still needs a parser check and a verified pin (a PR).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from http.client import HTTPException
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

from .fetch import DEFAULT_UA, FetchError, _AllowlistRedirect
from .provenance import HOST_ALLOWLIST
from .registry import Source, load

SOURCES = Path("data/sources.yml")
BASELINE = Path("data/watch_baseline.json")
_DATA_EXT = (".xlsx", ".xls", ".ods", ".csv", ".zip", ".pdf")
_HREF = re.compile(r"""href=["']([^"']+)["']""", re.I)
MAX_BYTES = 25 * 1024 * 1024


_OPENER = urllib.request.build_opener(_AllowlistRedirect)
_NET_ERRORS = (urllib.error.URLError, TimeoutError, OSError, HTTPException, FetchError)


def _get(url: str, ua: str) -> tuple[bytes, str]:
    """GET with pacing and backoff; returns (body, final url). ONS answers 429 in bursts."""
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    wait = 0
    for _ in range(3):
        time.sleep(wait + 1)
        try:
            with _OPENER.open(req, timeout=60) as r:
                return r.read(MAX_BYTES + 1), r.geturl()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                raise
            try:
                wait = max(0, min(int(e.headers.get("Retry-After", 10)), 120))
            except ValueError:
                wait = 10
            e.close()
    raise urllib.error.URLError("still rate limited after retries")


def data_links(html: str, base: str) -> set[str]:
    out = set()
    for href in _HREF.findall(html):
        try:
            url = urljoin(base, href.replace("&amp;", "&"))
            p = urlparse(url)
            _ = p.hostname
        except ValueError:
            continue
        if p.scheme != "https" or p.hostname not in HOST_ALLOWLIST:
            continue
        # ONS serves files as /file?uri=...xlsx; gov.uk and OBR as plain paths.
        target = p.path.lower()
        if target.endswith("/file"):
            target = unquote(p.query).lower().split("&")[0]
        if target.endswith(_DATA_EXT):
            out.add(url)
    return out


def _gone(e: Exception) -> bool:
    """A 4xx other than 429 means the page or file was removed or moved: a finding."""
    return isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500 and e.code != 429


def check_source(
    src: Source, baseline: set[str], ua: str | None = None
) -> tuple[list[str], set[str]]:
    ua = src.user_agent or ua or DEFAULT_UA
    notes: list[str] = []
    pinned = {f.file_url for f in src.files if f.file_url} | baseline
    pages = {src.landing_url} | {f.landing_url for f in src.files}
    seen: set[str] = set()
    for page in sorted(pages):
        try:
            body, final = _get(page, ua)
            seen |= data_links(body.decode("utf-8", "replace"), final)
        except _NET_ERRORS as e:
            if _gone(e) or isinstance(e, FetchError):
                notes.append(f"landing page gone or redirected off-allowlist: {page} ({e})")
                continue
            print(f"warning: landing page unreachable: {page} ({e})", file=sys.stderr)
    for url in sorted(seen - pinned):
        notes.append(f"unpinned data file on landing page: {url}")
    for f in src.files:
        if not (f.file_url and f.sha256):
            continue
        try:
            body, _ = _get(f.file_url, ua)
        except _NET_ERRORS as e:
            if _gone(e) or isinstance(e, FetchError):
                notes.append(f"{f.key}: pinned file gone or redirected off-allowlist ({e})")
                continue
            print(f"warning: {f.key}: pinned file unreachable ({e})", file=sys.stderr)
            continue
        if len(body) > MAX_BYTES:
            notes.append(f"{f.key}: larger than {MAX_BYTES} bytes, not hashed")
        elif hashlib.sha256(body).hexdigest() != f.sha256:
            notes.append(
                f"{f.key}: live file differs from pinned sha256 (publisher replaced it in place)"
            )
    return notes, seen


def main(argv: list[str] | None = None) -> int:
    """`watch [ids]` reports; `watch --accept [ids]` records today's links as already seen."""
    args = list(argv or [])
    accept = "--accept" in args
    ids = {a for a in args if a != "--accept"}
    base = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
    findings = {}
    for src in load(SOURCES):
        if not src.enabled or (ids and src.id not in ids):
            continue
        notes, seen = check_source(src, set(base.get(src.id, [])))
        if accept:
            base[src.id] = sorted(set(base.get(src.id, [])) | seen)
        elif notes:
            findings[src.id] = notes
    if accept:
        BASELINE.write_text(json.dumps(base, indent=1, sort_keys=True) + "\n")
        print(f"watch: baseline written for {len(base)} sources")
        return 0
    if not findings:
        print("watch: no new links and every pinned file matches its sha256")
        return 0
    print("# Source watch: possible new or changed editions\n")
    for sid, notes in findings.items():
        print(f"## {sid}")
        for n in notes:
            print(f"- {n}")
        print()
    return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
