"""Browser smoke tests for the static site (Playwright, chromium)."""

from __future__ import annotations

import re

import pytest

PAGES = [
    "index",
    "spending",
    "revenue",
    "benefits",
    "who-pays",
    "claims",
    "check",
    "reconciliation",
    "about",
    "methodology",
    "corrections",
]
DATA_PAGES = ["index", "spending", "revenue", "benefits", "who-pays"]
T = 20_000


def goto(page, base_url, path):
    page.goto(base_url + path, wait_until="networkidle")


def wait_loaded(page):
    page.wait_for_function(
        "() => !document.querySelector('#build-host')?.textContent.startsWith('Loading')",
        timeout=T,
    )


def hero_values(page):
    return page.locator(".hero-num button.num-val").all_inner_texts()


@pytest.mark.parametrize("name", PAGES)
def test_page_loads_without_errors(page, base_url, name):
    goto(page, base_url, f"{name}.html")
    wait_loaded(page)
    assert page.locator("h1").first.inner_text().strip()
    assert page.locator("[role=alert]").count() == 0, "page shows an error alert"
    assert page.errors == []


@pytest.mark.parametrize("name", DATA_PAGES)
def test_data_pages_render_figures(page, base_url, name):
    goto(page, base_url, f"{name}.html")
    page.locator("button.num-val").first.wait_for(timeout=T)
    assert page.locator("p.state.error").count() == 0


def tme_first_row(page):
    return page.locator("#tme details.table-view tbody tr").first.text_content()


def test_basis_toggle_changes_values(page, base_url):
    """Real equals cash in the price-base year, so compare the earliest year."""
    goto(page, base_url, "spending.html")
    page.locator("#tme details.table-view tbody tr").first.wait_for(state="attached", timeout=T)
    nominal = tme_first_row(page)
    caption = page.locator("#tme figcaption").inner_text()
    seen = {}
    for basis in ("real", "pct_gdp"):
        page.locator(f"label[for=basis-{basis}]").click()
        assert page.locator(f"#basis-{basis}").is_checked()
        page.wait_for_function(
            "(b) => new URL(location.href).searchParams.get('basis') === b", arg=basis
        )
        page.wait_for_function(
            "(c) => document.querySelector('#tme figcaption').innerText !== c", arg=caption
        )
        seen[basis] = tme_first_row(page)
        assert seen[basis] != nominal, f"{basis} first row identical to nominal: {nominal}"
        caption = page.locator("#tme figcaption").inner_text()
    assert seen["real"] != seen["pct_gdp"]
    assert "%" in seen["pct_gdp"]
    page.locator("label[for=basis-nominal]").click()
    page.wait_for_function(
        "(c) => document.querySelector('#tme figcaption').innerText !== c", arg=caption
    )
    assert tme_first_row(page) == nominal


def test_home_tiles_follow_basis_toggle(page, base_url):
    goto(page, base_url, "index.html")
    page.locator(".hero-num button.num-val").first.wait_for(timeout=T)
    nominal_meta = page.locator("#tiles .meta").all_inner_texts()
    nominal = hero_values(page)
    page.locator("label[for=basis-pct_gdp]").click()
    page.wait_for_function(
        "() => document.querySelector('#tiles').innerText.includes('%')", timeout=T
    )
    assert hero_values(page) != nominal
    page.locator("label[for=basis-real]").click()
    page.wait_for_function(
        "() => !document.querySelector('#tiles').innerText.includes('%')", timeout=T
    )
    # latest outturn is the price-base year: figure may match cash, caption must not
    assert page.locator("#tiles .meta").all_inner_texts() != nominal_meta


def test_basis_from_query_string(page, base_url):
    goto(page, base_url, "index.html?basis=pct_gdp")
    page.locator(".hero-num button.num-val").first.wait_for(timeout=T)
    assert page.locator("#basis-pct_gdp").is_checked()


@pytest.mark.parametrize("name", DATA_PAGES)
def test_check_links_are_wellformed(page, base_url, name):
    goto(page, base_url, f"{name}.html")
    page.locator("a:has-text('Check this number')").first.wait_for(timeout=T)
    hrefs = page.locator("a:has-text('Check this number')").evaluate_all(
        "els => els.map(e => e.getAttribute('href'))"
    )
    assert hrefs
    for href in hrefs:
        assert re.fullmatch(r"check\.html#p=[a-z][a-z0-9_]*\.[0-9a-f]{6,64}", href), href


def test_check_link_leads_to_https_official_source(page, base_url):
    goto(page, base_url, "spending.html")
    page.locator("a.num-check").first.wait_for(timeout=T)
    href = page.locator("a.num-check").first.get_attribute("href")
    goto(page, base_url, href)
    page.locator("ol.steps").wait_for(timeout=T)
    url = page.locator("ol.steps a[rel~=external]").first.get_attribute("href")
    assert url.startswith("https://"), url
    sha = page.locator("ol.steps code").filter(has_text=re.compile(r"^[0-9a-f]{64}$"))
    assert sha.count() >= 1
    assert page.errors == []


def test_every_home_tile_check_link_resolves_to_official_https(page, base_url):
    goto(page, base_url, "index.html")
    links = page.locator("#tiles a:has-text('Check this number')")
    links.first.wait_for(timeout=T)
    hrefs = links.evaluate_all("els => els.map(e => e.getAttribute('href'))")
    assert len(hrefs) == 3
    for href in hrefs:
        goto(page, base_url, href)
        page.locator("ol.steps").wait_for(timeout=T)
        urls = page.locator("ol.steps a[rel~=external]").evaluate_all("els => els.map(e => e.href)")
        assert urls
        assert all(u.startswith("https://") for u in urls), (href, urls)


def test_check_page_states(page, base_url):
    goto(page, base_url, "check.html")
    assert "No number selected" in page.locator("#check").inner_text()
    goto(page, base_url, "check.html#p=not-valid")
    page.reload(wait_until="networkidle")
    assert "valid provenance id" in page.locator("#check").inner_text()
    goto(page, base_url, "check.html#p=obr_psf.deadbeef00")
    page.reload(wait_until="networkidle")
    page.wait_for_function(
        "() => document.querySelector('#check').innerText.includes('Could not find')", timeout=T
    )


def test_figure_popover_shows_source(page, base_url):
    goto(page, base_url, "index.html")
    page.locator(".hero-num button.num-val").first.click()
    pop = page.locator("div.pop[role=dialog]")
    pop.wait_for(state="visible", timeout=T)
    pop.locator("a.cta").wait_for(timeout=T)
    assert "check.html#p=" in pop.locator("a.cta").get_attribute("href")


def test_reconciliation_panel_on_home(page, base_url):
    goto(page, base_url, "index.html")
    page.locator("#recon-panel table tbody tr").first.wait_for(timeout=T)
    assert page.locator("#recon-panel .recon-summary .rs").count() == 4
    page.locator("#recon-host a").wait_for(timeout=T)
    assert "Cross-checks" in page.locator("#recon-host").inner_text()


def test_reconciliation_page_renders_and_filters(page, base_url):
    goto(page, base_url, "reconciliation.html")
    page.locator("#recon section.rule").first.wait_for(timeout=T)
    rows = page.locator("#recon section.rule tbody tr")
    total = rows.count()
    assert total > 0
    assert page.locator("#summary .rs").count() == 4
    page.locator("#filters button", has_text="Failing").click()
    failing = rows.count()
    assert 0 < failing < total
    assert page.locator("#recon tr.row-fail").count() == failing
    page.locator("#filters button", has_text="All results").click()
    assert rows.count() == total


def test_reconciliation_failures_listed_first(page, base_url):
    goto(page, base_url, "reconciliation.html")
    page.locator("#recon section.rule").first.wait_for(timeout=T)
    assert page.locator("#recon section.rule").first.locator("tr.row-fail").count() > 0


def test_forecast_labels_visible(page, base_url):
    goto(page, base_url, "spending.html")
    page.locator("#tme figure.card").wait_for(timeout=T)
    assert "Forecast" in page.locator("#tme .chart-legend").inner_text()
    assert page.locator("#tme svg .fc-label").first.text_content().startswith("Forecast")
    page.locator("#tme details.table-view summary").click()
    assert "Forecast" in page.locator("#tme details.table-view").inner_text()


def test_forecast_labels_on_revenue(page, base_url):
    goto(page, base_url, "revenue.html")
    page.locator("figure.card").first.wait_for(timeout=T)
    assert "Forecast" in page.locator("main").inner_text()


def test_claims_page_empty_state_is_explicit(page, base_url):
    """data/claims.yml is empty: the page must say so rather than invent claims."""
    goto(page, base_url, "claims.html")
    page.locator("#claims .empty").wait_for(timeout=T)
    assert "No claims have been checked yet" in page.locator("#claims").inner_text()
    assert page.locator("#claims article").count() == 0


def test_claim_lookup_returns_sourced_result(page, base_url):
    """Scaffold: no curated claims; a series lookup gives the official figure and source."""
    goto(page, base_url, "claims.html")
    page.locator("#results li button").first.wait_for(timeout=T)
    page.locator("#q").fill("total managed")
    page.locator("#results li button").first.click()
    out = page.locator("#lookup")
    out.locator("button.num-val").wait_for(timeout=T)
    out.locator("dl").wait_for(timeout=T)
    text = out.inner_text()
    for needle in ("Publisher", "Dataset", "Licence"):
        assert needle in text
    assert out.locator("a.cta").get_attribute("href").startswith("check.html#p=")
    assert out.locator("dl a[rel~=external]").first.get_attribute("href").startswith("https://")


def test_claim_lookup_no_match_state(page, base_url):
    goto(page, base_url, "claims.html")
    page.locator("#results li").first.wait_for(timeout=T)
    page.locator("#q").fill("zzzzqqqq")
    assert "No series match" in page.locator("#results").inner_text()
    assert page.locator("#count").inner_text().startswith("0 matching")


def test_claim_lookup_deep_link(page, base_url):
    goto(page, base_url, "claims.html")
    page.locator("#results li button").first.wait_for(timeout=T)
    page.locator("#results li button").first.click()
    page.locator("#lookup button.num-val").wait_for(timeout=T)
    assert page.url.split("#", 1)[1].startswith("s=")
    page.reload(wait_until="networkidle")
    page.locator("#lookup button.num-val").wait_for(timeout=T)
    assert page.errors == []


def test_nav_links_resolve(page, base_url):
    goto(page, base_url, "index.html")
    hrefs = sorted(
        set(page.locator("nav.nav a").evaluate_all("els => els.map(e => e.getAttribute('href'))"))
    )
    assert len(hrefs) == 10
    for href in hrefs:
        assert page.request.get(base_url + href).ok, href
