import hashlib
import io
from types import SimpleNamespace

import pytest

from ukpm import fetch

GOOD = b"workbook bytes"


class _Resp(io.BytesIO):
    headers = {"Content-Type": "application/octet-stream"}

    def __enter__(self):
        return self

    def geturl(self):
        return "https://www.gov.uk/x.xlsx"


def _entry(sha):
    return SimpleNamespace(key="k", file_url="https://www.gov.uk/x.xlsx", sha256=sha)


def _patch(monkeypatch, bodies):
    it = iter(bodies)
    opener = SimpleNamespace(open=lambda req, timeout: _Resp(next(it)))
    monkeypatch.setattr(fetch.urllib.request, "build_opener", lambda *a: opener)
    monkeypatch.setattr(fetch.time, "sleep", lambda s: None)


def test_empty_body_is_retried_not_called_a_replaced_file(monkeypatch, tmp_path):
    _patch(monkeypatch, [b"", GOOD])
    sha = hashlib.sha256(GOOD).hexdigest()
    src = SimpleNamespace(id="s", user_agent=None)
    digest, *_ = fetch._download(src, _entry(sha), tmp_path / "f.xlsx")
    assert digest == sha


def test_changed_file_still_reports_mismatch(monkeypatch, tmp_path):
    _patch(monkeypatch, [b"something else"])
    src = SimpleNamespace(id="s", user_agent=None)
    with pytest.raises(fetch.FetchError, match="sha256 mismatch"):
        fetch._download(src, _entry(hashlib.sha256(GOOD).hexdigest()), tmp_path / "f.xlsx")
