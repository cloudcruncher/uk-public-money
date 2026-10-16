# Layman UX: information architecture and page templates

Status: design spec for the `feat/layman-and-sources` work. Builders implement from this; it does not change data rules.

Read with `docs/design/positioning.md` (voice, homepage arc, banned jargon). Where this file and positioning disagree, positioning wins.

## 0. Constraints this design works inside

- **Static site, no build step for CSS.** One stylesheet (`site/assets/app.css`), page scripts in `site/assets/pages/*.js`.
- **Strict CSP on every page:** `script-src 'self'; style-src 'self'`. So:
  - No `<script>` blocks, no `onclick=` attributes.
  - No `style="..."` attributes in HTML or in SVG markup, and no `setAttribute('style', ...)`. Setting `el.style.width` from `app.js` through the CSSOM is allowed (the bars already do this).
  - SVG geometry uses presentation attributes (`x`, `y`, `width`, `height`, `d`, `points`). Colour comes only from classes in `app.css`.
- **Reuse the existing design language:** paper `--bg`, ink text, serif headings, one data blue (`--bar`), forecast hatching, `.note`, `.badge-forecast`, `.num-val` (click a number to see its source), `details.table-view`. Add no new colours. Status colours stay reserved for reconciliation.
- **No number without a traced source.** Every figure on a layman page is rendered by the existing `.num` component, so it keeps its "check this number" link.
- **Reading age:** aim for 9 to 11 (as in positioning). The hard ceiling is 12. Check every page with a readability tool before merging.

## 1. Information architecture

### 1.1 Page list, titles and nav labels

The nav label is what appears in the header. The H1 is the page title. The `<title>` is `{H1} · UK Public Money`.

| File | Nav label | H1 (page title) | Replaces / notes |
| --- | --- | --- | --- |
| `index.html` | Home | £1 of your tax: where it goes | Story homepage (section 3). Replaces "Overview". |
| `spending.html` | Where your money goes | Where your money goes | Was "Where £1 goes". |
| `revenue.html` | Where the money comes from | Where the money comes from | Was "Where £1 comes from". |
| `benefits.html` | Benefits explained | Benefits explained | Index of benefits, plus the "which welfare total?" comparison. |
| `benefit-<slug>.html` | (none, linked from Benefits explained) | e.g. Carer's Allowance | One page per benefit (section 4). Flat file names keep the relative `assets/` paths working. |
| `who-pays.html` | Who pays tax | Who pays income tax | Was "Who pays". |
| `claims.html` | Check a number | Check a number you have heard | Was "Check a claim". |
| `check.html` | (none) | Where this number comes from | Reached from any number. |
| `glossary.html` | Words explained | Words explained | New page (section 6). |
| `reconciliation.html` | Why totals differ | Why official totals differ | Secondary nav. |
| `methodology.html` | How we work it out | How we work out the numbers | Secondary nav. |
| `corrections.html` | Corrections | Corrections | Secondary nav. |
| `about.html` | About us | About this site | Secondary nav. |

Primary nav order: Home, Where your money goes, Where the money comes from, Benefits explained, Who pays tax, Check a number.
Secondary nav order: Words explained, Why totals differ, How we work it out, Corrections, About us.
The footer repeats both lists in the same order.

Labels use the reader's words: "your money", "explained", "check". They do not use publisher or method words. Do not put acronyms in the nav.

### 1.2 Page anatomy (every page, top to bottom)

1. Skip link, header, nav (as now).
2. Controls bar (as now). On layman pages the basis toggle is labelled **"Show amounts: Adjusted for rising prices | As spent at the time"**, and the first option is the default. The reconciliation strip stays.
3. `<main>`:
   1. **H1**
   2. **Summary block** (1.3)
   3. Page sections. Each one is an H2 with one idea, one chart at most, and 1 to 4 short paragraphs.
   4. **For checkers** disclosure (section 7). It is always last before the footer and always closed by default.
4. Footer.

Heading order is strict: one H1, then H2s, then H3s inside them. Never skip a level. A card title inside an H2 section is an H3.

### 1.3 The one-sentence summary block

Every page opens with one sentence that answers the page's question, with its year and basis.

```html
<section class="summary" aria-labelledby="summary-h">
  <h2 id="summary-h" class="visually-hidden">In one sentence</h2>
  <p class="summary-text">In 2024-25 (April to March), the government spent about
    <span class="num">…£X billion…</span> on Carer's Allowance, which is about
    <span class="num">…£Y…</span> out of every £100 spent on benefits.</p>
  <p class="summary-meta small muted">Actual figures · adjusted for rising prices · last updated 3 October 2026</p>
</section>
```

Rules:
- The sentence is 30 words or fewer. It leads with the answer. It has at most two numbers, and each is a `.num` with a source link.
- The meta line states three things: actual figures or forecast, the price basis, and the date of the last data refresh.
- The summary must never say more than the data allows. If the main figure is missing, the sentence says so: "We don't show the total cost yet: the official figures aren't published in a form we can trace."
- Visual: `.summary` is a `--surface` card with a 4px `--accent` left border. `.summary-text` uses `var(--serif)` at 1.25rem/1.45 with a max width of 60ch. It sits directly under the H1 and replaces `.lede` on layman pages.
- Loading state: the sentence frame renders with a "Loading…" `.state` in its place. Error state: `.state.error` says "We couldn't load this figure. Try again, or see the source files on the Methodology page."

## 2. Copy rules

### 2.1 Sentences and words

- Keep sentences under 20 words, with one idea each. Paragraphs are 3 sentences at most.
- Use the active voice and say who acted: "The government spent", not "Expenditure was incurred".
- **No jargon without a glossary term.** Body copy uses the plain phrase. When a technical term has to appear, wrap it in the tooltip pattern (section 6.2) on its first use on each page. The words banned in positioning (TME, PSCE, AME, DEL, COFOG, outturn, receipts and others) appear only in For checkers and on the glossary page.
- Spell out publishers on first use on a page: "the Office for Budget Responsibility (OBR)". After that, "the OBR" is fine.
- Neutral verbs only: spent, collected, paid, claimed, expected. Never "splurged", "ballooned", "soared" or "only".
- No exclamation marks, no rhetorical questions, and no "you might be surprised".

### 2.2 Numbers

| Kind | Rule | Example |
| --- | --- | --- |
| Large money | Write the unit as a word. Use whole billions from £10 billion up. Use one decimal place below that. | £1.3 trillion · £312 billion · £4.2 billion |
| Millions | Write "million". Use whole numbers from 10 million up. | £850 million · 1.4 million people |
| Out of every £100 | Use whole pounds. If the amount is under £1, write it in pence or as "less than £1". The parts shown must add up to £100 (see below). | £21 out of every £100 · 40p out of every £100 |
| Per person | Round to the nearest £10, or to the nearest £100 from £10,000 up. | about £4,600 per person |
| Percentages | Avoid them in body copy. Prefer "out of every £100". When a percentage cannot be avoided (for example a share of GDP), use whole numbers and add a plain gloss. | about 4% of everything the UK produces in a year |
| Counts of people | Round to 2 significant figures and write the unit as a word. | about 1.4 million people |
| Years | Write the financial year with its months on first use. After that, the short form is fine. | 2024-25 (April to March), then 2024-25 |

- **Never use "bn", "m", "k" or "£bn" in body copy.** Chart axes may use "£ billion" in the axis title. Tick labels show plain numbers.
- Say "about" whenever a figure is rounded. Never write "roughly" or "around" without a number.
- **Making the parts add up to £100:** round with the largest-remainder method so the categories shown sum to exactly £100. Explain this in For checkers.
- Every figure states its year and whether it is adjusted for rising prices. The unadjusted basis is "as spent at the time".

### 2.3 Forecast, actual and provisional wording

| Data status | Verb tense and wording | Visual |
| --- | --- | --- |
| Actual figures (outturn) | Past tense. "The government spent £X billion." | Solid bar or line. No badge, or `.badge-outturn` "Actual". |
| Provisional or first estimate | "First estimate, likely to be revised: about £X billion." | Solid, with a `.badge-info` badge reading "First estimate". |
| Forecast (OBR) | Future tense, with the forecaster named. "The OBR expects spending to be about £X billion in 2027-28." Never "will be". | Hatched bar or dashed line, with a `.badge-forecast` badge reading "Forecast". |
| Plan (department budgets) | "The government plans to spend…" | As forecast, with the badge reading "Plan". |

Never write a sentence that mixes actual and forecast years without naming both: "Spending rose from £X billion in 2019-20 (actual) to an expected £Y billion in 2027-28 (forecast)."

### 2.4 Gaps and disagreements

- Gap: "We don't show this yet: the official figures aren't published in a form we can trace." Render it in an `.empty` box. Never fill a gap with an estimate.
- Disagreement: "These two totals differ by about £X billion because one includes the State Pension." Never call a figure "wrong" or "misleading".

## 3. Story homepage: "£1 of your tax: where it goes"

### 3.1 Honesty note built into the copy

The title says "your tax", but the government spends more than it collects in tax. So the story splits **every £100 the government spends** and gives borrowing its own section. The summary sentence says this up front.

> Summary: "In 2024-25 (April to March), the government spent about £1.3 trillion. Here is where each £100 went, and how it was paid for."

### 3.2 Unit choice: per person vs per household

- **Per person** is used only if a UK population figure (ONS mid-year estimate) is in the source registry and traced to a cell for the same year. At the time of writing, no population series is in `src/ukpm/registry.py`. Until one is added, the per-person lines are hidden, and the story uses "out of every £100" only.
- **Typical household:** show a household figure only if a verified household count (ONS Families and Households) is in the registry and traced to a cell. Otherwise do not show one. Never derive a household number by dividing by an assumed household size.
- Per-person copy: "That is about £X for every person in the UK, including children." The words "including children" must be there, because the figure is not a per-taxpayer amount.

### 3.3 Section sequence

Each section is an H2 band. It holds one statement, one chart, two to three sentences, and an optional "Read more" link. On wide screens the chart and text sit side by side (text left, chart right, `grid-template-columns: 1fr 1fr` from 720px up). On phones they stack, with the text first.

| # | H2 (plain) | Content | Chart |
| --- | --- | --- | --- |
| 1 | Out of every £100 the government spends | The six biggest areas, with the rest grouped as "Everything else". Year labelled. | Ranked bar list (`.bars`) in £ out of £100. |
| 2 | £X goes on pensions and benefits | The biggest area first. One sentence on what it includes. | 100-squares with £X of squares filled. |
| 3 | £X goes on health | Same pattern. | 100-squares. |
| 4 | £X goes on schools and education | Same pattern. | 100-squares. |
| 5 | £X goes on interest on government debt | "This is the cost of past borrowing, not paying the debt back." | 100-squares, plus a 10-year line (adjusted for rising prices). |
| 6 | The rest: defence, police, roads and more | Short list with £ out of £100 for each. | Compact `.bars`. |
| 7 | How the £100 was paid for | "£X came from taxes and other income. £Y was borrowed." Uses spending as the denominator so the parts add up to £100. | 100-squares in two parts: filled for tax and income, hatched for borrowing (hatching is the existing forecast pattern, here relabelled in the legend). |
| 8 | "Welfare costs £X." Which welfare? | The tension from positioning: several honest totals exist. | None. Lead into section 9. |
| 9 | Four official welfare totals, side by side | The existing `.defs` cards, each with an "includes / leaves out" list. | None (cards). Links to Benefits explained. |
| 10 | Check any number yourself | "Click any number on this site to see the exact file and cell it came from." Shows one example `.num`. | None. Links to Check a number. |

After section 10: a three-card `.grid-3` of next steps (Where your money goes, Benefits explained, Words explained), then For checkers.

- Sections 2 to 5 pick their categories from the data, in ranked order. They are not hard-coded. If the ranking changes, the copy changes with it.
- Every £-out-of-£100 figure is a `.num` whose provenance is the share calculation: the numerator cell, the denominator cell and the formula. Its source popover shows all three.
- When the per-person line is enabled (3.2), it goes under each section's main statement as `.small.muted`.

## 4. Benefit explainer page template

Modelled on wheredoesitallgo.org/welfare/carers-allowance. Ours adds traced sources, actual vs forecast labels and the For checkers block.

URL: `benefit-<slug>.html` (for example `benefit-carers-allowance.html`). Generate these from one HTML template, either through `ukpm build` writing out the files or through one page script reading a `data-benefit` attribute on `<main>`. Every benefit page must have the same block order.

| # | Block | H2 | Content rules |
| --- | --- | --- | --- |
| 0 | H1 | (H1) The benefit name, e.g. "Carer's Allowance" | Use the official name. Add no adjectives. |
| 1 | Summary | (hidden H2 "In one sentence") | "In 2024-25, about 1.0 million people got Carer's Allowance. It cost about £4.2 billion, adjusted for rising prices." |
| 2 | What it is | What it is | Two to three sentences in plain words. Say whether it is means-tested, whether it counts towards the welfare cap, and whether it covers Great Britain or the UK. Link to the GOV.UK page for the benefit. |
| 3 | Who gets it | Who gets it | Eligibility in one short bulleted list of 3 to 5 items, in plain words. Write "people who…", not "claimants who…". |
| 4 | Key numbers | The numbers | Four stat tiles (`.grid` of `.tile`, 2 by 2 on phones, 4 across from 720px): **Total cost**, **People getting it**, **Cost per person getting it**, **Share of benefit spending**. Each tile has a label, a `.hero-num` and a meta line (year, actual or forecast). |
| 5 | Over ten years | How it has changed over ten years | Line chart (5.2) of cost, adjusted for rising prices. A second small line chart shows the number of people. Forecast years are dashed and labelled. One sentence of plain change: "Cost has risen from about £X billion to about £Y billion since 2015-16, after adjusting for rising prices." |
| 6 | In context | Compared with other benefits | A `.bars` list of the 8 largest benefits with this benefit highlighted (the row gets `aria-current="true"` and bold text). Links to each benefit's page. |
| 7 | Check this | (inside For checkers) | Section 7. |

Rules for the key numbers:
- **Cost per person getting it** = total cost ÷ average number of people getting it in the same year, both from the same DWP table release. Write it as "about £X a year for each person getting it". The divisor is the average over the year, and For checkers says so. If the two figures come from different releases or years, do not show the tile. Show the gap message instead.
- **Share of benefit spending** must name its denominator in the tile meta, for example "of all DWP benefit spending in Great Britain". It links to Benefits explained, where the other totals are shown. Show it as £ out of £100 ("£2 out of every £100 spent on benefits"), not as a percentage.
- **People getting it** is the caseload. The glossary tooltip on "people getting it" says: "Officials call this the caseload."

## 5. Chart patterns (inline SVG, CSP-safe)

All charts share these rules:

- Wrap each chart in `<figure class="chart">`. The `<svg>` has `role="img"` and `aria-labelledby` pointing to its own `<title>` (the chart's question) and `<desc>` (the plain caption sentence).
- Put a **plain caption** in `<figcaption>` above the chart. It is a sentence that states the finding, not a label. Good: "Health got about £21 out of every £100 in 2024-25." Bad: "Fig. 2: COFOG 07 share."
- A source line goes under the chart in `.small.muted`: "Source: HM Treasury, Public Spending Statistics, July 2026. Click any number to check it."
- **Data-table fallback:** every chart is followed by `<details class="table-view"><summary>Show these numbers as a table</summary>`, holding a real `<table>` with a `<caption>`, `<th scope="col">` and `<th scope="row">`, right-aligned numbers (`td.r`) and `.num` links. The table is the accessible source of truth. The SVG shows the same data in picture form.
- Draw only with classes. Allowed classes: `.col`, `.grid-line`, `.zero`, `.tick`, `.dlabel`, `.hatch-*`, `.fc-band`, `.fc-label`, `.gap-mark`, plus the new ones below. Do not use `fill=` colours in markup, so dark mode and forced colours keep working.
- Wrap the SVG in `.table-wrap`-style horizontal scrolling only if it truly cannot fit. Prefer reflowing to a narrower viewBox on phones, below 480px.
- Make interactive points (`g.pt`) focusable only when they add something beyond the table. Never make them the only way to reach a value.

### 5.1 Bar (ranked list)

Reuse the HTML/CSS `.bars` and `.bar-row` pattern, not SVG. It wraps text, reflows on phones and is read in order. Sort from largest to smallest and put "Everything else" last whatever its size. Show the value as "£21" with "out of every £100" in the column header or the first row's sub-label only, to avoid repeating it.

### 5.2 Line (ten-year trend)

- The viewBox is 640×280 on desktop and 360×240 on phones (the page script picks one by container width at render).
- Only the y-axis gridlines are drawn, 4 to 5 of them, starting at zero. Never truncate the axis on money charts.
- Actual years are a solid 2.5px line in `--bar` (new class `.line`). Forecast years are a dashed line (new class `.line.forecast`, `stroke-dasharray: 6 4`) over the existing `.fc-band` background, with the `.fc-label` "Forecast" placed at the band's top-left.
- Label the first and last points with values (`.dlabel`). Do not label every point.
- Show a missing year as a gap in the line (`.gap-mark`), not by joining across it.
- The axis title is "£ billion, adjusted for rising prices (2024-25 prices)".

### 5.3 100 squares ("out of £100")

A 10×10 grid where each square is £1 out of £100. Use one highlighted category per grid. Several colours in one grid fail colour-only distinction and break the one-blue language.

```html
<figure class="chart squares">
  <figcaption>Health got about £21 out of every £100 the government spent in 2024-25.</figcaption>
  <svg viewBox="0 0 218 218" role="img" aria-labelledby="sq1-t sq1-d">
    <title id="sq1-t">Out of £100 of spending, how much went on health</title>
    <desc id="sq1-d">21 of 100 squares are filled.</desc>
    <rect class="sq on" x="0" y="0" width="20" height="20" rx="3"/>
    <!-- … 100 rects at 22px pitch, filled row by row from top-left … -->
    <rect class="sq" x="198" y="198" width="20" height="20" rx="3"/>
  </svg>
  <p class="squares-key small"><span class="sw on" aria-hidden="true"></span>£21 on health
     <span class="sw" aria-hidden="true"></span>£79 on everything else</p>
</figure>
```

- New CSS: `.chart .sq { fill: var(--surface); stroke: var(--axis); stroke-width: 1; }` and `.chart .sq.on { fill: var(--bar); stroke: var(--bar); }`. For the borrowing split in homepage section 7, add `.chart .sq.hatch { fill: url(#hatch) }`, which uses the existing hatch pattern defined in the SVG `<defs>`.
- Fill row by row from the top-left, so a count reads like a progress bar.
- If the amount is under £1, fill no squares and change the caption: "Less than £1 out of every £100." Never draw fractional squares.
- The grid is 218px square and centred. On phones it is at most 70% of the container width.
- Rounding uses the same largest-remainder values as the ranked list, so each grid and the list agree.

## 6. Glossary page and inline tooltip

### 6.1 Glossary page (`glossary.html`)

- H1 "Words explained". Summary: "What the words on this site mean, in plain English."
- A-to-Z jump links (`<nav aria-label="Jump to letter">`) show only letters that have terms.
- The body is one `<dl class="glossary">`. Each term is a `<dt id="g-<slug>">` and each definition a `<dd>`. The `<dd>` holds:
  1. The plain one-line definition (the same text as the tooltip).
  2. Optional "Also called" with synonyms and the official acronym.
  3. Optional "Example" with one real figure as a `.num`.
  4. Optional "See also" links to other terms.
- Store the terms in `data/glossary.yml` (slug, term, plain, also_called, see_also). The page and the tooltips are built from it, so there is one source of truth.
- Every `<dt>` has a `:target` style: `--accent-soft` background, kept on screen, with no animation.

### 6.2 Inline tooltip pattern (no inline script or style)

Use the HTML **Popover API** with a `<button>` invoker. It needs no JavaScript at all and no `style` attributes, so it passes `script-src 'self'; style-src 'self'`. Escape and light dismiss are native. It opens on click or Enter, not on hover, so WCAG 1.4.13 (content on hover or focus) does not apply.

```html
<p>Amounts are
  <button type="button" class="term" popovertarget="tt-real-terms">adjusted for rising prices</button><span
    id="tt-real-terms" class="term-tip" popover role="note">Changed so that £1 in an older year buys the same
    as £1 today. Officials call this <em>real terms</em>.
    <a href="glossary.html#g-real-terms">More in Words explained</a></span>
  so years can be compared fairly.</p>
```

- **Element choice:** `<button>` gives keyboard focus and Enter/Space activation. Browsers that support `popovertarget` expose `aria-expanded` on it automatically. The popover is a `<span>`, so it is valid inside `<p>`. It sits straight after the button in the DOM, so screen readers reach it next in reading order when it opens.
- **Use the plain phrase as the button text.** The technical term goes inside the tip ("Officials call this…"). This keeps jargon out of body copy while still teaching it.
- **Visual:** `.term` looks like text with a 1px dotted `--accent` underline (`border-bottom: 1px dotted var(--accent)`), on a transparent background, inheriting the font. It is not a pill. Hover and open states thicken the underline to 2px solid. Focus uses the global `:focus-visible` ring.
- **Tip styles:** `.term-tip` has a `--surface` background, a 1px `--line` border, `--radius-sm` and `var(--shadow)`, 12px 14px padding, `max-width: min(320px, calc(100vw - 32px))`, 0.9rem/1.45 text and `--ink` colour.
- **Positioning:** the default is a bottom sheet on all screens (`position: fixed; inset: auto 16px 16px 16px; margin: 0`), which always works. Inside `@supports (position-area: block-end)`, anchor it to its invoker (`position-area: block-end span-inline-end; margin-top: 6px; position-try-fallbacks: flip-block`). Browsers link an implicit anchor between a `popovertarget` invoker and its popover, so no `anchor-name` per term is needed.
- **Fallback:** older browsers without popover support render the `<span>` inline. Under `@supports not selector(:popover-open)`, style `.term-tip` as an inline muted parenthetical (`display: inline; font-size: .9em; color: var(--muted)`, with `::before { content: " (" }` and `::after { content: ")" }`) and make `.term` look like plain text. Nothing is lost.
- **Frequency:** use it on the first use of a term per page only, and on no more than about 5 terms per screen. Never use it inside headings, nav, buttons, chart SVG or `.num` values.
- **No JS-built tooltips** (`title=` attributes, hover-only `.tip` divs) for definitions. `title` is not keyboard or touch accessible. The existing chart `.tip` stays for chart data points only.

### 6.3 Initial glossary terms (32)

| Term (slug) | Plain one-line definition |
| --- | --- |
| Actual figures / outturn (`outturn`) | What was really spent or collected, counted after the year ended. |
| Forecast (`forecast`) | What the Office for Budget Responsibility expects to happen in future years; it can change. |
| First estimate / provisional (`provisional`) | An early count that is likely to be revised as more data comes in. |
| Plan (`plan`) | What the government intends to spend, set out in budgets before the money is spent. |
| Financial year (`financial-year`) | The government's year, which runs from 6 April to 5 April for tax and from 1 April to 31 March for spending. |
| Total government spending / TME (`tme`) | Everything the UK public sector spends in a year, including benefits, services, investment and debt interest. Officials call it Total Managed Expenditure (TME). |
| Day-to-day spending / PSCE (`psce`) | Spending on running services and paying benefits, leaving out investment in things like roads and buildings. Officials call it Public Sector Current Expenditure (PSCE). |
| Department budgets / DEL (`del`) | Spending that government departments plan and control within a fixed limit. Officials call it Departmental Expenditure Limits (DEL). |
| Demand-led spending / AME (`ame`) | Spending that depends on need, such as benefits and pensions, so it is managed year by year rather than capped. Officials call it Annually Managed Expenditure (AME). |
| Spending by purpose / COFOG (`cofog`) | An international way of grouping spending by what it is for, such as health, education or defence. |
| PESA (`pesa`) | HM Treasury's yearly tables of public spending, called Public Expenditure Statistical Analyses. |
| Tax collected / receipts (`receipts`) | Money the government takes in from taxes and other sources in a year. |
| Income tax (`income-tax`) | Tax on what people earn from jobs, pensions, savings and some benefits. |
| National Insurance / NICs (`nics`) | A tax on earnings paid by workers and employers that helps pay for the State Pension and some benefits. |
| VAT (`vat`) | Value Added Tax, a tax added to the price of most things people buy. |
| Borrowing / deficit (`deficit`) | The gap in a year when the government spends more than it takes in, which it fills by borrowing. |
| Government debt (`debt`) | The total the government owes from all its past borrowing that has not yet been paid back. |
| Debt interest (`debt-interest`) | The yearly cost of interest on government debt; it does not pay off the debt itself. |
| Adjusted for rising prices / real terms (`real-terms`) | Amounts changed so that £1 in an older year buys the same as £1 today, which lets years be compared fairly. |
| As spent at the time / cash terms (`cash-terms`) | Amounts as they were paid in that year, not adjusted for rising prices. |
| Inflation (`inflation`) | How fast prices are rising. |
| Price adjuster / GDP deflator (`gdp-deflator`) | The measure of rising prices across the whole economy that we use to adjust amounts. |
| GDP (`gdp`) | The total value of everything the UK produces in a year. |
| Share of GDP / % of GDP (`percent-of-gdp`) | A figure shown as a share of everything the UK produces in a year, so it can be compared across years and countries. |
| Welfare (`welfare`) | Money paid to people to support them, such as benefits and the State Pension; different reports include different things. |
| Social protection (`social-protection`) | The international spending group for pensions, benefits and other support for people; it is wider than DWP benefits. |
| State Pension (`state-pension`) | A regular payment from the government to people who have reached State Pension age. |
| Universal Credit (`universal-credit`) | A monthly payment for people on low incomes or out of work that replaced six older benefits. |
| Means-tested (`means-tested`) | Only paid if your income and savings are below a set level. |
| People getting it / caseload (`caseload`) | The number of people getting a benefit, usually the average across the year. |
| Cost per person getting it (`cost-per-claimant`) | The total cost of a benefit divided by the number of people getting it in the same year. |
| Why totals differ / reconciliation (`reconciliation`) | Our check that figures from different official sources agree, and our explanation when they don't. |

Publishers (HM Treasury, OBR, ONS, HMRC, DWP) get short entries on the About page, not in the glossary. If needed later, they can go in a separate "Who publishes the figures" list.

## 7. "For checkers" disclosure

This is the last block on every page. It is closed by default, so the plain answer always comes first.

```html
<details class="checkers" id="for-checkers">
  <summary><span class="checkers-h">For checkers</span>
    <span class="small muted">Sources, exact cells and how the numbers fit together</span></summary>
  <div class="checkers-body">
    <h3>Check these numbers</h3>       <!-- list: each figure on the page → check.html?id=… -->
    <h3>Where they come from</h3>      <!-- kv list: publisher, file, release date, sheet, cell, SHA-256, fetched at -->
    <h3>Do the sources agree?</h3>     <!-- reconciliation rules for this page's figures, with pass/fail badges -->
    <h3>Definitions and method</h3>    <!-- technical names (TME, AME, COFOG 10…), rounding, deflator, caseload averaging -->
  </div>
</details>
```

- **Native `<details>`/`<summary>`:** keyboard and screen-reader support is built in, and it needs no script. The H3s inside sit under the page's last H2, which is the visually hidden "For checkers" `<h2>` placed just before the `<details>`. This keeps the heading outline correct.
- **Content:**
  - **Check these numbers:** a list with one row per figure on the page. Each row has the plain label, the value and a "Check this number" link to `check.html?id=<series_id>&period=<year>`.
  - **Provenance:** for each source, the publisher, file title and link, release date, sheet, cell or range, SHA-256 and fetch time. Reuse the `.kv` styles.
  - **Reconciliation:** the rules that touch this page's figures, each with a status badge (`.badge-pass`, `.badge-fail`, `.badge-not_run`) and a one-line plain explanation. A failure is stated neutrally, as in positioning.
  - **Definitions and method:** the technical names that were kept out of the body copy, the rounding method (largest remainder for £100 splits), the price basis and base year, and how cost per person is calculated.
- **Visual:** `--surface-2` background, 1px `--line` border, `--radius`. The summary row is at least 44px tall. Its "For checkers" label uses the serif at 1.1rem. A `::marker` replacement chevron rotates 90° when open (the rotation is wrapped in `prefers-reduced-motion: no-preference`).
- **Deep link:** `#for-checkers` opens it. `app.js` sets `open` when the hash matches; that is an external script, so CSP allows it.
- **Print:** in print, show it open (`details.checkers > *` displayed). That needs a small `beforeprint` handler in `app.js` that sets `open`.

## 8. Accessibility (WCAG 2.2 AA)

### 8.1 Contrast (measured on the existing tokens)

| Pair | Light | Dark | Use |
| --- | --- | --- | --- |
| `--muted` on `--bg` | 6.42:1 | 9.02:1 | Meta text, captions: passes 4.5:1. |
| `--accent` on `--bg` | 6.13:1 | 8.88:1 | Links, `.term` underline, focus ring. |
| `--warn` on `--bg` | 6.12:1 | 10.82:1 | Forecast badge text. |
| `--bar` on `--surface` | 4.42:1 | 4.79:1 | Filled squares, bars, lines: passes 3:1 for graphics. |
| `--axis` on `--surface` | 3.25:1 | 5.11:1 | Empty square outlines: passes 3:1. |
| `--axis` on `--bg` | 3.00:1 | 5.50:1 | Borderline in light mode. **Put 100-squares grids on a `--surface` card**, not on bare `--bg`. |
| `--bar-soft` on `--bg` | 1.22:1 | (n/a) | Never use it alone to carry meaning. It only appears inside hatching with a `--bar` outline (3.34:1 against it). |

- Never encode meaning with colour alone. Forecasts are hatched or dashed **and** carry a "Forecast" badge or label. Highlighted rows are also bold and have `aria-current`.
- Keep `@media (forced-colors: active)`. Add `.chart .sq.on { fill: CanvasText }` and `.chart .sq { stroke: CanvasText }`, and make `.term` use a `LinkText` underline.

### 8.2 Focus and keyboard

- The global `:focus-visible` ring (3px `--accent`, 2px offset) applies everywhere, including `.term`, `summary` and the `.num-val` buttons.
- **WCAG 2.2 Focus Not Obscured (2.4.11):** the sticky `.controls` bar can cover focused items. Add `html { scroll-padding-top: 64px }`, or match the bar height, so focused elements and `:target` anchors scroll clear of it.
- **Target size (2.5.8):** interactive targets are at least 24×24 CSS px. `.term` buttons inside text are exempt as inline targets, but give them `padding-block: 2px`. The `summary` and nav links meet 44px.
- Tab order follows reading order. No positive `tabindex`.

### 8.3 Structure

- One H1 per page, with no skipped levels (see 1.2). Landmarks: `header`, `nav[aria-label="Main"]`, `main`, `footer`. The summary is a labelled `section`.
- `lang="en-GB"` (already set). The page `<title>` names the page first.
- Live regions are only for loading and error `.state` messages (`role="status"`). Never put `aria-live` on numbers that update when the basis toggle is used. The toggle's own label change is enough.

### 8.4 Motion

- The only animations are the bar width transition (existing) and the chevron rotation. Both sit inside `@media (prefers-reduced-motion: no-preference)`.
- No scroll-driven animation in the story homepage. Sections are static. Do not use `scroll-behavior: smooth` unless it is wrapped in the same media query.

### 8.5 Responsive

- Use a 16px side gutter and avoid horizontal page scroll at 320px wide (WCAG 1.4.10 reflow). Only data tables may scroll sideways, inside `.table-wrap`.
- Story sections are single-column below 720px, text first. Stat tiles are 2×2 below 720px.

## 9. New CSS classes to add (summary for builders)

Add to `site/assets/app.css`. All use the existing tokens, so no new colours are needed.

- `.summary`, `.summary-text`, `.summary-meta`: summary block (1.3).
- `.story-section`: grid layout for the homepage bands (3.3).
- `.chart .line`, `.chart .line.forecast`: line chart (5.2).
- `.chart .sq`, `.chart .sq.on`, `.chart .sq.hatch`, `.squares-key`, `.squares-key .sw`, `.squares-key .sw.on`: 100 squares (5.3).
- `.glossary`, `.glossary dt:target`: glossary page (6.1).
- `.term`, `.term-tip`, plus the `@supports` blocks: tooltip (6.2).
- `.checkers`, `.checkers-h`, `.checkers-body`: For checkers (7).
- `html { scroll-padding-top }` and the forced-colors additions (8.1, 8.2).

## 10. Done criteria for builders

- Every page has an H1, a summary block and a For checkers disclosure, in that order.
- No `style=` attribute and no inline `<script>` in any HTML or generated SVG. Check with `grep -rn 'style=\|<script>' site/*.html` (it should find nothing). The browser console shows no CSP violations.
- Every number on a layman page is a `.num` that has a working "Check this number" link.
- Every chart has a figcaption sentence, `<title>`/`<desc>` and a `details.table-view` table.
- £100 splits add up to exactly £100 on the page.
- There is no per-person or household figure unless its population or household count is in the source registry.
- Banned jargon from positioning does not appear in body copy outside For checkers and the glossary. Check with a grep for `\b(TME|PSCE|AME|DEL|COFOG|outturn|receipts)\b` against the text outside `details.checkers`.
- axe or Lighthouse accessibility checks show no violations on the homepage, one benefit page and the glossary, in light and dark mode.
