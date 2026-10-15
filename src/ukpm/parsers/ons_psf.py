"""ONS Public Sector Finances: documented stub, not implemented.

The source is disabled in data/sources.yml (verdict UNVERIFIED). No ONS file URL has been
verified to return a data file: guessed bulletin and dataset URLs returned 404 or 429
(docs/sources/spend.md), and the landing page (HTTP 200) is HTML, not data. So there is no file to
pin, hash or build a fixture from.

To implement: find the real PSF time-series CSV/XLSX URL, record its sha256 and licence in
data/sources.yml, add a verified file entry, then write ``parse`` (TME, current receipts, net
borrowing) by label per docs/ARCHITECTURE.md section 6, with a trimmed fixture under
tests/fixtures/spend/.
"""

from __future__ import annotations

from pathlib import Path

from ..provenance import Row
from . import FileMeta

SOURCE = "ons_psf"
SERIES: dict[str, dict] = {}


def parse(path: Path, meta: FileMeta) -> list[Row]:
    raise NotImplementedError("ons_psf has no verified source file; see the module docstring")
