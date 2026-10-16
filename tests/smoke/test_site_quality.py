"""Readability, glossary-link, benefit-page and basic accessibility checks (Playwright)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from .test_site_smoke import PAGES, T, goto, wait_loaded

ROOT = Path(__file__).resolve().parents[2]
GLOSSARY_IDS = {t["id"] for t in yaml.safe_load((ROOT / "data" / "glossary.yml").read_text())}
BENEFIT_SLUGS = ["universal-credit", "attendance-allowance", "housing-benefit"]
MAX_GRADE = 10.0

PROSE_JS = """() => {
  const skip = 'table, details, figcaption, nav, footer, .meta, .state, .term-tip, .badge, '
    + '.controls, .note, button, svg, [aria-hidden=true]';
  const out = [];
  document.querySelectorAll('main p, main li').forEach((el) => {
    if (el.closest(skip)) return;
    const t = el.textContent.replace(/\\s+/g, ' ').trim();
    if (t.split(' ').length >= 5) out.push(t);
  });
  return out;
}"""


def _syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and not w.endswith(("le", "ee")) and n > 1:
        n -= 1
    return max(n, 1)


def fk_grade(text: str) -> float:
    sentences = [s for s in re.split(r"[.!?]+(?:\s|$)", text) if re.search(r"[A-Za-z]", s)]
    words = re.findall(r"[A-Za-z][A-Za-z'’-]*", text)
    if not sentences or not words:
        return 0.0
    syl = sum(_syllables(w) for w in words)
    return 0.39 * len(words) / len(sentences) + 11.8 * syl / len(words) - 15.59


def test_fk_grade_helper_sanity():
    assert fk_grade("The cat sat on the mat. The dog ran to the park.") < 3
    hard = (
        "Notwithstanding considerable methodological complications, intergovernmental "
        "reconciliation necessitates comprehensive epidemiological reinterpretation."
    )
    assert fk_grade(hard) > 15


def _prose(page):
    return " ".join(s if re.search(r"[.!?]$", s) else s + "." for s in page.evaluate(PROSE_JS))


@pytest.mark.parametrize("path", ["index.html"] + [f"benefit.html?b={s}" for s in BENEFIT_SLUGS])
def test_main_prose_is_readable(page, base_url, path):
    goto(page, base_url, path)
    wait_loaded(page)
    page.locator("main h1").first.wait_for(timeout=T)
    text = _prose(page)
    assert len(text.split()) > 40, f"too little prose to judge: {text[:200]!r}"
    grade = fk_grade(text)
    assert grade <= MAX_GRADE, f"{path}: Flesch-Kincaid grade {grade:.1f} > {MAX_GRADE}"


def test_glossary_yaml_ids_unique():
    ids = [t["id"] for t in yaml.safe_load((ROOT / "data" / "glossary.yml").read_text())]
    assert len(ids) == len(set(ids)) and ids


@pytest.mark.parametrize(
    "path",
    [
        "index.html",
        "spending.html",
        "revenue.html",
        "benefits.html",
        "who-pays.html",
        "benefit.html?b=universal-credit",
    ],
)
def test_glossary_links_point_to_real_ids(page, base_url, path):
    goto(page, base_url, path)
    wait_loaded(page)
    page.locator("button.num-val").first.wait_for(timeout=T)
    hrefs = page.eval_on_selector_all(
        "a[href*='glossary.html#']", "els => els.map(e => e.getAttribute('href'))"
    )
    for href in hrefs:
        assert re.fullmatch(r"glossary\.html#g-[a-z0-9_-]+", href), href
        assert href.split("#g-")[1] in GLOSSARY_IDS, f"unknown glossary id in {href}"
    for tid in page.eval_on_selector_all("button.term", "els => els.map(e => e.dataset.termId)"):
        assert tid in GLOSSARY_IDS, tid
    assert page.errors == []


def test_term_tooltip_opens_and_links_to_glossary_entry(page, base_url):
    goto(page, base_url, "index.html")
    wait_loaded(page)
    btn = page.locator("button.term").first
    btn.wait_for(timeout=T)
    btn.click()
    tip = page.locator(f"#{btn.get_attribute('popovertarget')}")
    assert tip.is_visible()
    link = tip.locator("a[href^='glossary.html#g-']")
    href = link.get_attribute("href")
    link.click()
    page.wait_for_url(re.compile(re.escape(href) + "$"))
    page.locator("dl.glossary dt").first.wait_for(timeout=T)
    assert page.locator("#" + href.split("#")[1]).count() == 1


def test_glossary_page_has_every_term(page, base_url):
    goto(page, base_url, "glossary.html")
    page.locator("dl.glossary dt").first.wait_for(timeout=T)
    ids = set(page.eval_on_selector_all("dl.glossary dt", "els => els.map(e => e.id)"))
    visible = {i for i in GLOSSARY_IDS if f"g-{i}" in ids}
    assert visible, "no glossary terms rendered"
    assert all(i.startswith("g-") and i[2:] in GLOSSARY_IDS for i in ids)


@pytest.mark.parametrize("slug", BENEFIT_SLUGS)
def test_benefit_page_shows_figure_and_source(page, base_url, slug):
    goto(page, base_url, f"benefit.html?b={slug}")
    wait_loaded(page)
    page.locator("button.num-val").first.wait_for(timeout=T)
    assert page.locator("#bname").inner_text().strip() not in ("", "Benefit", "Benefit not found")
    assert re.search(r"\d", page.locator("button.num-val").first.inner_text())
    assert page.locator("[role=alert]").count() == 0
    srcs = page.locator("main a[href^='https://']")
    assert srcs.count() > 0, "no external source link on benefit page"
    assert page.errors == []


def test_unknown_benefit_is_explicit(page, base_url):
    goto(page, base_url, "benefit.html?b=does-not-exist")
    page.locator("#bname", has_text="Benefit not found").wait_for(timeout=T)
    assert page.locator("a[href='benefits.html']").count() >= 1


@pytest.mark.parametrize("name", PAGES + ["glossary", "benefit"])
def test_basic_accessibility(page, base_url, name):
    path = f"{name}.html" + ("?b=universal-credit" if name == "benefit" else "")
    goto(page, base_url, path)
    wait_loaded(page)
    assert page.locator("html").get_attribute("lang"), "missing lang attribute"
    assert page.locator("h1:visible").count() == 1, "expected exactly one h1"
    assert page.locator("img:not([alt])").count() == 0, "image without alt"
    bad = page.eval_on_selector_all(
        "a[href]",
        """els => els.filter(e => !(e.textContent.trim() || e.getAttribute('aria-label')
            || e.getAttribute('aria-labelledby') || e.querySelector('img[alt]:not([alt=""])')
            || e.getAttribute('title'))).map(e => e.outerHTML.slice(0, 120))""",
    )
    assert bad == [], f"links without text: {bad}"


def test_glossary_links_exist_somewhere(page, base_url):
    """Guards against the glossary checks passing vacuously."""
    goto(page, base_url, "index.html")
    wait_loaded(page)
    page.locator("button.term").first.wait_for(timeout=T)
    assert page.locator("a[href*='glossary.html#g-']").count() > 0
