"""Playwright fixtures. SMOKE_URL tests a deployed site; otherwise site/ is served locally."""

from __future__ import annotations

import functools
import http.server
import os
import threading
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[2] / "site"


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        pass


@pytest.fixture(scope="session")
def base_url():
    env = os.environ.get("SMOKE_URL")
    if env:
        yield env.rstrip("/") + "/"
        return
    if not (SITE / "api" / "v1" / "index.json").exists():
        pytest.skip("site/api/v1 missing: run `python -m ukpm build --offline` first")
    handler = functools.partial(_Quiet, directory=str(SITE))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    errors: list[str] = []
    pg.errors = errors
    pg.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.on(
        "response",
        lambda r: errors.append(f"http {r.status}: {r.url}") if r.status >= 400 else None,
    )
    yield pg
    ctx.close()
