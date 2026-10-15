"""Parser contract and shared helpers.

Each module `ukpm.parsers.<source_id>` exposes:

    parse(path: Path, meta: FileMeta) -> list[Row]     # required; one call per file
    combine(rows: list[Row]) -> list[Row]              # optional; across files of the source

Rules: find cells by label (never a hard-coded address), record the resolved A1 address in
provenance, raise LayoutError(file_key, anchor) if an anchor is missing, never round values.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..registry import FileEntry, Source
from ..sheets import a1 as a1  # re-exported for parsers

__all__ = ["FileMeta", "LayoutError", "a1", "normalise_fiscal_year"]


class LayoutError(RuntimeError):
    def __init__(self, file_key: str, anchor: str):
        self.file_key, self.anchor = file_key, anchor
        super().__init__(f"layout changed in {file_key}: anchor {anchor!r} not found")


@dataclass(frozen=True)
class FileMeta:
    source: Source
    file: FileEntry
    sha256: str
    url: str
    fetched_at: str
    path: Path


_FY_RE = re.compile(r"^\s*(\d{4})\s*[-/–]\s*(\d{2}|\d{4})\s*$")


def normalise_fiscal_year(text: object) -> str:
    """'2015/16', '2015-2016', '2015-16' -> '2015-16'."""
    m = _FY_RE.match(str(text))
    if not m:
        raise ValueError(f"not a fiscal year: {text!r}")
    start, end = int(m.group(1)), m.group(2)
    if len(end) == 4:
        end = end[2:]
    if int(end) != (start + 1) % 100:
        raise ValueError(f"fiscal year does not span consecutive years: {text!r}")
    return f"{start}-{end}"
