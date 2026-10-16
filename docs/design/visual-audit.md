# Visual audit and homepage scroll-story spec

Status: audit of the `feat/layman-and-sources` working tree on 2026-10-15, plus a spec for the next builder. Read with `positioning.md` (voice) and `layman-ux.md` (IA, components). Where this file disagrees with `layman-ux.md` on visuals, this file is newer; where it disagrees with `positioning.md`, positioning wins.

**Method.** `python3 -m http.server` on `site/`, Playwright Chromium, full-page and first-screen captures at 1280×800 and 390×844, light and dark. 14 pages, plus `benefit.html?b=universal-credit`, `benefit.html?b=carers-allowance`, a real `check.html#p=…` and the number popover. No console errors on any page. API data was mid-edit by other agents, so figures quoted below are what the build showed at the time. The spec uses `{placeholders}` for figures.

**The test for every page:** a first-time visitor, given 10 seconds, can say the page's one finding back in their own words ("about £41 of every £100 goes on pensions and benefits"). Today, only **Carer's Allowance** (the benefit page) passes. The homepage nearly does, but its best visual is broken on desktop.

---

## 1. Fixes ranked by impact

Each fix gets a priority, a scope (which pages it affects) and an effort guess. Do P0 before anything else. Each one either breaks the first screen or makes two numbers on one screen look like they contradict each other.

| # | P | Fix | Where | Effort |
| --- | --- | --- | --- | --- |
| 1 | P0 | **Phones scroll sideways.** At 390px wide, `scrollWidth` is 537px on 13 of 14 pages. The cause is the basis toggle: `.controls fieldset.basis .seg` does not wrap, and "Share of the economy" sits off-screen. `benefits.html` also has a table 608px wide outside `.table-wrap`. Fix: let `.seg` wrap, or turn it into a 3-row stacked radio below 480px. Wrap every `<table>` in `.table-wrap`. | All | S |
| 2 | P0 | **Phones: the H1 starts at y≈520 of 844.** The offline banner, an 8-link two-row nav, the toggle and the cross-check badges take up 60% of the first screen. Fix: below 720px, collapse the nav into a `<details class="nav-menu">` with a "Menu" button (no JS needed). Hide the cross-check badges in the controls bar on layman pages (keep them on `reconciliation.html` and inside For checkers). Shorten the banner to one line: "Test build: some years are missing." Target: the H1 sits above y=200 on a 390×844 screen. | All | M |
| 3 | P0 | **The first coloured thing a visitor sees is a red "✕ 17 failing".** It is in the controls bar on every page. To a layperson it reads as "this site's numbers are wrong". Fix: remove the badge strip from the global controls bar. Show cross-check status only in For checkers and on Why totals differ, with a plain line first: "We compare official totals with each other. Most agree; where they don't, we show both." | All | S |
| 4 | P0 | **The basis label contradicts itself.** The toggle says "Adjusted for rising prices", but the summary meta on Home, Where your money goes and Benefits explained says "as spent at the time". On Carer's Allowance, three tiles say "adjusted" and the cost-per-person tile says "as spent at the time". The Benefits list shows Carer's Allowance at £4.2 billion and its own page shows £4.4 billion. Fix: one basis per page view. Every figure on the screen follows the toggle, and the meta line is generated from the same state. If a figure cannot follow the toggle (for example a £-out-of-£100 share), its meta says "a share, so the same either way". | Home, Spending, Benefits, Benefit | M |
| 5 | P0 | **Desktop: the homepage 100-squares are crushed.** In "The three biggest parts", the three squares cards sit in a grid only about 100px wide each. The caption breaks one word per line ("Pensions / and / benefits: / £41…") and the grid is 50px. On phones the same block renders well. Fix: give the squares row the full content width (`grid-template-columns: repeat(3, minmax(220px, 1fr))`, no side text column). Or follow the scroll-story spec in section 3, which gives each category its own band. | Home | S |
| 6 | P0 | **The welfare section undercuts its own message.** The heading says "several totals… each can be right", but all three cards show **£334 billion** for 2025-26. A visitor concludes the totals are the same. Fix: show the cards only when their values differ. Order them smallest to largest, with a horizontal "stacked ruler" (section 3, band 8) that makes the gaps visible. Use the Benefits page's £289 billion (GB, DWP benefits, 2024-25) and the UK welfare figure for the same year, not a mix of years. Remove "(AME)" and "(DWP tab)" from card titles. | Home | M |
| 7 | P1 | **Mixed years and areas on one screen.** The homepage hero is 2025-26 UK. The £100 split directly under it is 2024-25 England only. Spending's summary is England 2024-25. A visitor reads them as one picture. Fix: put the year and area in a **scope chip** above every chart: `2024-25 · England · actual`. Use a full sentence when they differ from the hero: "This split only covers public services in England, and the latest year is 2024-25." Put the chip in the figcaption, not in muted small print below. | Home, Spending | S |
| 8 | P1 | **One hero number, not three.** "The year in three numbers" gives £1.4 trillion, £1.2 trillion and £334 billion equal weight. The third is a forecast in a different family. Fix: one hero, which is the spending total plus a plain unit translation (section 3, band 1). Income and borrowing become band 7. Welfare becomes band 8. | Home | M |
| 9 | P1 | **"Check this number" link noise.** On Benefits explained, 20 cards × 4 figures gives 80 underlined links. On the homepage bar lists, every row has one. It turns a chart into a form. The number is already a button (dotted underline, opens the source popover). Fix: in lists, charts and cards, drop the trailing "Check this number" text link and keep the `.num-val` button. Keep one visible "Check this number" link per hero or summary figure only. Add a single key line under each chart: "Click any amount to see where it came from." | All | S |
| 10 | P1 | **Benefits explained has no picture.** It is a 2×10 wall of identical cards, and the State Pension (£137 billion) looks the same size as Severe Disablement Allowance (£54 million). Fix: lead with one ranked `.bars` chart of all benefits by cost, in £ out of every £100 of benefit spending. Annotate State Pension: "Almost half of all benefit spending goes on the State Pension." Each row links to its page. Move the cards into `details.table-view` or into a compact table below. | Benefits | M |
| 11 | P1 | **Who pays tax hides its story.** The bars are about 25px long at most. The percentages wrap onto 4 lines ("0.22% / of all / income / tax"). The page never states the finding. Fix: a paired "people vs tax" chart (section 4.4). Lead with the sentence it supports: "About 4 in every 100 taxpayers earn over £100,000. Together they pay about £45 of every £100 of income tax." Use £-out-of-£100 and "in every 100" framing instead of 2-decimal percentages. | Who pays | M |
| 12 | P1 | **Charts are not annotated.** The time series on Spending and Revenue are plain columns. The 2020-21 spike has no label, and the reader is left to guess. Fix: one or two plain callouts drawn on the chart (section 4.2): "2020-21: COVID support", and at the actual/forecast boundary, "Forecast by the OBR". Never more than two per chart. | Spending, Revenue, Benefit | M |
| 13 | P1 | **Phone charts are shrunk desktop charts.** On Carer's Allowance at 390px, the 640-wide SVG scales to about 300px, and tick labels render near 6px. `layman-ux.md` section 5.2 asks for a 360×240 viewBox on phones. That is not done. Fix: pick the viewBox by container width at render time. Keep tick labels at 12px or more in rendered size. Show at most 5 x-labels on phones (first, last and evenly spaced). | Benefit, Spending, Revenue | M |
| 14 | P1 | **Jargon still visible in body copy.** "Hydrocarbon oil fuel duties", "Stamp duty land tax", "PESA 2026 10.1 ends at 2024-25 outturn" (Spending's missing-years note), "no ONS mid-year estimate…" (repeated 6 times on Revenue), "Total expenditure on services, England", "DWP benefit spending (AME)", the Claims list ("Public sector current receipts", "Total managed expenditure" with mono IDs), Methodology ("Outturn and forecast", "PESA Table 10.1… TES… UK TME… COFOG"). Fix: plain labels map in the page script ("Fuel duty", "Stamp duty on property"). Gap notes collapse to one sentence per series ("Years after 2025-26 are not shown: there is no official population figure for them yet."). Move Methodology's technical paragraphs into its For checkers. | Revenue, Spending, Claims, Methodology, Home | S |
| 15 | P2 | **"Everything else" is not last** in the homepage income list. It sits 4th, between VAT and Corporation tax. `layman-ux.md` section 5.1 puts it last regardless of size. It also gets the same blue as real categories: use `.bar-fill.rest` (`--axis`) so it reads as a remainder. | Home, Revenue | S |
| 16 | P2 | **Benefit page tiles are 3 + 1 orphan on desktop.** "Share of benefit spending" wraps alone. Fix: 4 across from 960px, 2×2 from 480px to 959px, 1 column below 480px. Section 4 of `layman-ux.md` also asks for a "Compared with other benefits" `.bars` with this benefit highlighted. It is missing. Add it. It is the context a layperson needs ("is £4.4 billion a lot?"). | Benefit | S |
| 17 | P2 | **Chart legend does not match the marks.** On benefit line charts the legend swatch for "Forecast (dashed)" is a hatched square, but the line is dashed. The "People getting it" axis title says "Thousand people" while ticks read "1.5 million". Fix: draw legend swatches as a 24×0 line segment (solid and dashed) for line charts. Make the axis title "People" and keep tick units in the labels. | Benefit | S |
| 18 | P2 | **Words explained is unstyled.** The A to Z is a vertical bulleted list of 15 single letters (about 320px tall). Terms are 16px sans and look smaller than the bold definition under them. Fix: horizontal wrapping letter strip (`display:flex; flex-wrap:wrap; gap:4px`, 36px square targets). `dt` in `var(--serif)` 1.25rem. The definition's first line at normal weight. "Also called" and "See also" on one muted line. Keep the `:target` highlight. | Glossary | S |
| 19 | P2 | **Why totals differ is 14,000px (desktop) / 32,000px (phone) of pink rows.** Each rule lists every year in full with raw `|delta|` text. Fix: per rule, one plain sentence ("DWP's benefit total is about £1 to £2 billion more than its listed benefits add up to, every year. We don't know why yet.") and a **year strip**: 16 small cells, one per year, each ✓ or ✕ with the word in the tooltip/table. The full rows go into `details.table-view`. Use the `--bad-soft` row tint only on the strip, not on whole tables. | Reconciliation | M |
| 20 | P2 | **The check page has opaque links and no plain lead.** "Check the other inputs" lists `obr.529baa637cdd`. Step 4 says "GDP deflator, OBR databank Sep 2026, 2025-26=100". Fix: name the input ("Price adjuster for 2025-26 (OBR, September 2026)") with the ID in mono after it. Put one sentence first: "£1.4 trillion is all government spending in 2025-26. Here is how to find it in the publisher's own spreadsheet in 4 steps." The no-ID state should show 3 example numbers to try, not just a sentence. | Check | S |
| 21 | P2 | **Empty space and empty states.** Claims opens with an empty "No claims have been checked yet" box above the useful lookup. The lookup's right column says "Pick a series to see its official figure." beside 400px of blank space. Fix: lookup first. Put the empty-claims note below it as one muted line. The right pane shows the top suggestion pre-selected. | Claims | S |
| 22 | P3 | **Spending squares card floats alone** under the 10-row bar list, left-aligned and 240px wide in a 1088px column. Fix: put it beside the bar list from 960px (bars 2fr, squares 1fr, top-aligned). Or drop it: the bar list already shows the split, and the squares belong on the homepage. | Spending, Revenue | S |
| 23 | P3 | **Defence shows as "less than £1"** in the England-only split. That is correct for that table, but most readers will think it is wrong. Fix: annotate the row: "Defence is mostly paid for UK-wide, so little of it shows up in England's services." Also link to the UK-wide total. | Spending | S |
| 24 | P3 | Orphan punctuation: "The gap is called the deficit ." wraps the full stop onto its own line on phones. The `.term` button is followed by a text node starting with ".". Fix: put the full stop inside a no-break span with the button, or use `white-space: nowrap` on `.term + text`. | Home | S |

**Dark mode** renders correctly (checked on Home). Tokens hold, and the bars and badges have enough contrast. No dark-specific fixes are needed.

---

## 2. Page by page: what a visitor gets in 10 seconds

### Home (`index.html`)
- **Gets:** "The government spent about £1.4 trillion in 2025-26." The serif H1 and summary card are strong.
- **Confused by:** a red "17 failing" before the H1; three equal hero numbers with long meta lines; a "2024-25 England" split under a "2025-26 UK" hero; broken squares on desktop; three welfare cards that all say £334 billion; "Everything else" mid-list; a "What about interest on debt?" section that is only an empty box.
- **Visual fixes:** replace with the scroll story in section 3. Until data arrives, the debt-interest band is removed, not shown empty. A one-line note in band 6 says it is coming.

### Where your money goes (`spending.html`)
- **Gets:** "£41 of every £100 went on pensions and benefits." The bar list is clear and well-spaced.
- **Confused by:** "Read this first" box (right instinct, but it is a wall of text). Defence "less than £1". A total column chart whose 2020-21 jump has no explanation. The second chart's title is "Total expenditure on services, England". The missing-year note says "PESA 2026 10.1 ends at 2024-25 outturn".
- **Visual fixes:** scope chip on the bar list (fix 7). Annotate 2020-21 and the forecast start on the total chart (fix 12). Rename the second chart's default to "All areas together, England". Defence note (fix 23). Squares beside bars (fix 22).

### Where the money comes from (`revenue.html`)
- **Gets:** "£35 of every £100 the tax office collected came from income tax."
- **Confused by:** "Two different totals" (HMRC vs OBR) is explained in text, but then the two charts sit side by side at different scales (1,000 vs 1,500), which makes them look the same size. "Missing years" box has 6 near-duplicate lines about ONS population on a tax page. Tax names are official ("Hydrocarbon oil fuel duties").
- **Visual fixes:** draw the two totals on **one** chart: OBR all-income as a pale `--bar-soft` column with an `--bar` outline, and HMRC tax as a solid column inside it, with a callout on the latest year: "The OBR total is bigger because it also counts council tax and business rates." Collapse the gap note to one line. Plain tax names (fix 14).

### Benefits explained (`benefits.html`)
- **Gets:** "Benefits in Great Britain cost about £289 billion, and the biggest was the State Pension." Only from the summary.
- **Confused by:** 20 same-size cards with 80 "Check this number" links. No sense of scale. The phone table overflows.
- **Visual fixes:** ranked bar chart first (fix 10). Add a 100-squares figure: "£47 of every £100 spent on benefits goes on the State Pension". Cards go behind a "Show details for every benefit" disclosure.

### One benefit (`benefit.html?b=…`)
- **Gets:** "About 950,000 people got Carer's Allowance; it cost about £4.4 billion." **Best page on the site.** It has a clear template, a good line chart with a shaded forecast band, and end labels.
- **Confused by:** basis mismatch between tiles (fix 4). Tile orphan (fix 16). No "compared with other benefits". Phone chart text too small (fix 13). Legend swatch (fix 17).
- **Visual fixes:** as listed. Add one callout per chart at the latest actual year ("2024-25: £4.4 billion").

### Who pays tax (`who-pays.html`)
- **Gets:** "37 million people owed about £295 billion in income tax." Nothing about *who*.
- **Confused by:** two parallel lists of 11 bands with tiny bars and 4-line percentages. Bands start at £12,570 with no explanation ("people earning below the tax-free amount pay no income tax" is missing).
- **Visual fixes:** paired chart (section 4.4) and a headline sentence. Put the bands into 5 readable groups for the picture (under £20,000; £20,000 to £50,000; £50,000 to £100,000; £100,000 to £200,000; over £200,000). Keep all 11 in the table.

### Check a number (`claims.html`)
- **Gets:** "I can search for a figure." Only after reading.
- **Confused by:** empty claims box first. Series names in official language with mono IDs as the main labels.
- **Visual fixes:** fix 21. Show plain names with the official name as muted second line, and drop the mono ID to For checkers.

### Where this number comes from (`check.html`)
- **Gets (with an id):** the numbered stepper is the clearest proof-of-source design I have seen on a civic site. Keep it.
- **Confused by:** no plain lead sentence. Opaque input IDs. "Value in the file 1365.598 (GBP_bn)" with no "this is £1.4 trillion, rounded" bridge.
- **Visual fixes:** fix 20. Add a bridge line under step 3: "1,365.598 £ billion in the file → shown on the site as about £1.4 trillion."

### Words explained (`glossary.html`)
- **Gets:** "It's a dictionary." Clear words. The page is unstyled (fix 18).

### Why totals differ (`reconciliation.html`)
- **Gets:** "78 agree, 17 do not, 16 differ for known reasons." The 4 count tiles are good.
- **Confused by:** everything below the tiles is a debug log ("R7", "table_1a_lines", "|delta| 1.078262 vs tolerance 0.029000 GBP bn"). Red tint everywhere reads as alarm.
- **Visual fixes:** fix 19. Lead each rule with its plain question as an H3 ("Do DWP's benefit lines add up to its own total?").

### How we work it out (`methodology.html`) / About (`about.html`) / Corrections
- Fine as text pages for the secondary audience. Methodology body uses banned jargon (fix 14). About's sources table is useful, but its "Editions used" column is unreadable at 1280px (one long run-on cell). Fix: show the latest edition only, and put the rest in `details`.

---

## 3. Homepage scroll story: visual spec

H1 stays **"£1 of your tax: where it goes"**. The story uses **every £100 the government spends** as the unit (see `layman-ux.md` 3.1). Every `{figure}` is a `.num` with provenance. All £-out-of-£100 values use the largest-remainder rounding already in place, so the squares and bars agree.

**Layout.** Each band is `section.story-band` with an H2, at most 3 sentences, and one graphic. Text max 34ch on desktop. Graphic column 1fr. Bands are separated by 96px (desktop) / 64px (phone) of empty `--bg`, with no rules or cards around the text. On ≥960px: two columns, text left (sticky at `top: 24px` within its band, so the words stay beside the picture as it scrolls), graphic right. On <720px: text first, graphic full width. No scroll-driven animation (`layman-ux.md` 8.4).

**Scope chip.** Every graphic starts with a scope chip (`.scope`): `{year} · {area} · {Actual|Forecast}`. It is 12px uppercase-free sans, `--surface-2` pill, `--muted` text. It is the first child of the `<figcaption>`.

### Band 1: The hero
- **H2 (visually hidden):** "The total"
- **Graphic:** one huge number. `.hero-figure` serif, `clamp(3rem, 9vw, 6rem)`, weight 700, `--ink`. Beneath it, a **unit ladder**, three short lines at 1.1rem that translate the number into a scale people know:
  - "£{1.4 trillion} spent by the UK government in {2025-26} (April to March)"
  - "That is about £{20,500} for every person in the UK, including children." (only if the ONS population series is in the registry; it now appears to be: `ons_population.uk`)
  - "Or about £{3.8 billion} every day."
- **Copy (exact):** "In {2025-26}, the UK government spent about {£1.4 trillion}. Here is where each £100 went, and how it was paid for."
- **Meta:** "Actual figures · adjusted for rising prices · updated {15 October 2026}"
- No cards, no tiles, no badges in this band.

### Band 2: The whole £100
- **H2:** "Out of every £100 the government spends"
- **Graphic:** **one 10×10 squares grid, partitioned** into the top 6 areas plus "Everything else". This is the one place where a multi-category grid is allowed. Each block is a contiguous run of squares in reading order, separated by a 3px gap. Colour is **one blue** at stepped lightness (see 4.1 `--seq-1…--seq-4`) **plus a direct label** printed on the grid's right edge with a 1px leader line to each block's first square. The legend is the labels; there is no separate key. The text column carries the ranked `.bars` list (the accessible, exact version).
- **Caption (exact):** "{Pensions and benefits} is the biggest part: about £{41} of every £100."
- **Body (exact):** "Each square is £1. The squares are grouped by what the money was spent on. The amounts are rounded so they add up to £100."
- **Scope chip:** `{2024-25} · England · Actual`. **If** the scope differs from band 1, add this line under the caption: "This split only covers public services in England. It is the most detailed split published."

### Bands 3 to 5: The three biggest parts (one band each, data-ranked)
- **H2 (exact pattern):** "£{41} goes on {pensions and benefits}"
- **Graphic:** single-category 10×10 squares (`layman-ux.md` 5.3), 260px on desktop, 70% width on phone, on a `--surface` card. **Annotation drawn on the grid:** a bracket on the right edge spanning the filled rows, labelled "£{41}" in 1.5rem serif. One pictogram line under it (see 4.3) when a count exists: "That pays for about {13 million} State Pensions." Only use it when both numbers are traced (DWP caseload).
- **Body copy:**
  - Pensions and benefits: "This includes the State Pension, Universal Credit and disability benefits. The State Pension is the largest single payment." Link: "Benefits explained →"
  - Health: "This is mostly the NHS: hospitals, GPs and medicines."
  - Schools and education: "This covers schools, colleges and universities, and student support."
- **Per person line** (`.small.muted`), only with a population series: "That is about £{5,320} for every person in England, including children."

### Band 6: The rest
- **H2:** "The rest: transport, police, housing and more"
- **Graphic:** compact `.bars` of the remaining categories, with "Everything else" last and in `--axis` grey.
- **Body:** "These areas share the remaining £{20} of every £100."
- **If debt interest is not yet traced:** one `.small.muted` line here: "We don't show interest on government debt yet: the official figures aren't published in a form we can trace." Remove the empty box band.
- **When debt interest arrives:** it becomes its own band after band 5, with a 10-year line chart (fix 12 annotations: "2022-23: interest rates and inflation rose"). Caption: "£{X} of every £100 went on interest on government debt. This is the cost of past borrowing, not paying the debt back."

### Band 7: How the £100 was paid for
- **H2:** "How the £100 was paid for"
- **Graphic:** 10×10 squares in two parts: `.sq.on` for tax and other income (£{90}) and `.sq.hatch` for borrowing (£{10}). The hatched block is last (bottom-right). A bracket on the right labels it "£{10} borrowed". A second bracket on the left labels "£{90} from taxes and other income". Below it, the top 3 taxes as a single 100% **stacked strip** (one bar, 3 labelled segments plus "other", 28px tall, labels above with leader ticks): "Income tax £{35} · National Insurance £{21} · VAT £{19} · Other £{25}". The strip is per £100 of *tax collected*. Label it as such.
- **Caption (exact):** "Taxes and other income covered about £{90} of every £100. The other £{10} was borrowed."
- **Body (exact):** "Borrowing in one year adds to the government's total debt. Officials call the yearly gap the deficit."
- **Legend for the hatch:** "Hatched squares: borrowed". Do not reuse the word "Forecast" here.

### Band 8: The tension
- **H2 (exact):** "“Welfare costs £{X}.” Which welfare?"
- **Graphic:** a **definition ruler**. Horizontal bars on one shared £ scale, one per official total, sorted smallest to largest, each 20px tall. The bar's included parts are a solid `--bar`. When one total contains another, the shared part is drawn as the same left-aligned length, so the extra visibly sticks out. Each bar has a right-hand label "£{289} billion" and a left label in plain words:
  1. "Benefits paid by DWP, Great Britain"
  2. "UK welfare, all departments"
  3. "Spending on support for people (international definition)"
- **Annotation:** a bracket between bars 1 and 2: "£{X} billion more: adds Northern Ireland and benefits paid by other departments."
- **Body (exact):** "You may hear several totals for welfare. They count different things, so each can be right. The longest bar includes the most."
- **Rule:** all bars share one year and one basis. If they don't, don't draw the band: fall back to the cards with a scope chip on each.
- **Link:** "See every total and what it includes →" (`benefits.html#totals`)

### Band 9: Trust
- **H2 (exact):** "Check any number yourself"
- **Graphic:** a **worked example**, drawn as 3 linked boxes left to right (stacked on phone), connected by `→` arrows drawn as SVG paths: [ **£1.4 trillion** (a real `.num`) ] → [ "OBR Public finances databank, September 2026" ] → [ "Sheet *Aggregates (£bn)*, cell **D87**: 1,365.598" ]. The middle and right boxes use `--surface-2` and `--mono` for the cell reference only.
- **Body (exact):** "Every number on this site is a button. Click it to see the publisher's file, the sheet and the cell it came from."
- **Link:** "Try it on a number you have heard →" (`claims.html`)

### Band 10: Next steps
The existing `.grid-3` cards (Where your money goes, Benefits explained, Words explained). Then For checkers, closed.

---

## 4. Shared component rules

### 4.1 Colour tokens

No new hues. One blue carries all data. Add only lightness steps of that blue, plus roles that name existing values. Add to `:root` and both dark blocks.

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--bar` (existing) | `#2a78d6` | `#3987e5` | The highlighted or only series. Actual data. |
| `--seq-1` | `#1c5cab` (= `--accent`) | `#86b6ef` | Partitioned grid, 1st block |
| `--seq-2` | `#2a78d6` (= `--bar`) | `#3987e5` | 2nd block |
| `--seq-3` | `#6aa3e6` | `#2a6bbf` | 3rd block |
| `--seq-4` | `#a9cbf2` | `#1f4f8f` | 4th to 6th blocks (alternate with `--seq-3`, separated by gaps and labels) |
| `--rest` | `var(--axis)` | `var(--axis)` | "Everything else", remainders, unhighlighted rows in a context chart |
| `--anno` | `var(--ink)` | `var(--ink)` | Callout text, leader lines, brackets |
| `--empty` | `var(--surface-2)` | `var(--surface-2)` | Empty squares (with `--axis` stroke) |

Meaning rules:
- **Blue = money in the data. Grey = the rest or context. Hatched = forecast, or borrowed in band 7 (the legend says which).** Nothing else gets colour.
- Status colours (`--good`, `--bad`, `--warn`) are **only** for reconciliation, and only in For checkers and on Why totals differ. They never appear in the global header.
- Every colour meaning is also given in words: a direct label, a legend word or a badge. The partitioned grid in band 2 must have direct labels. Never rely on telling `--seq-3` from `--seq-4`.
- `--seq-3`/`--seq-4` on `--surface` must have a 1px `--bar` stroke to reach 3:1 against the card (they are below 3:1 on their own). Check this with a contrast tool before merging.

### 4.2 Annotated charts (the callout pattern)

Every time-series chart gets **1 or 2 callouts, never more**, drawn inside the SVG:

```html
<g class="anno" aria-hidden="true">
  <line class="anno-leader" x1="…" y1="…" x2="…" y2="…"/>
  <circle class="anno-dot" cx="…" cy="…" r="3.5"/>
  <text class="anno-text" x="…" y="…">2020-21: COVID support</text>
</g>
```

- `.anno-text`: `fill: var(--anno); font: 600 13px/1.2 var(--sans)`. Max 28 characters per line; use a second `<tspan>` line if needed. Never rotate.
- `.anno-leader`: `stroke: var(--anno); stroke-width: 1`. It runs from the text to the point, ending 4px short.
- `.anno-dot`: `fill: var(--surface); stroke: var(--anno); stroke-width: 1.5`.
- Placement: put the text in the emptiest quadrant above the line. On phones (360 viewBox), put callouts above the plot area in a reserved 28px strip with a vertical leader down to the point.
- The callout text must also appear in the figcaption or the `<desc>` (the SVG group is `aria-hidden`).
- Callouts state facts from the data or a named event. They never give opinions ("soared", "too high").
- **Standard callouts:** the first actual year and the last actual year, each with a value label (`.dlabel`). The forecast start: "Forecast by the OBR →" at the band's top-left (replaces the small "Forecast ▸"). Named shocks (2020-21) only where the data jump is more than 10%.
- **Brackets** (squares and stacked strips): `path.anno-bracket` with `fill: none; stroke: var(--anno); stroke-width: 1.5`, a 6px cap at each end and a label at the midpoint, 1.25rem serif.

### 4.3 Pictograms ("in every 100 people")

For counts of people (Who pays tax, caseloads), use a 10×10 grid of person glyphs instead of squares.
- The glyph is one `<symbol id="person">` (a 10×14 path: circle head and rounded body), placed with `<use href="#person" class="pp">`, with a pitch of 16px horizontal and 20px vertical.
- `.pp { fill: var(--empty); stroke: var(--axis); stroke-width: .75 }` and `.pp.on { fill: var(--bar); stroke: var(--bar) }`.
- Fill row by row from the top-left, as with squares. Under 1 in 100: fill none, and the caption says "fewer than 1 in every 100".
- Use people only for people counts. Use squares only for £. Never mix them in one figure.

### 4.4 Paired comparison ("share of people vs share of tax")

Who pays tax, main graphic. Two 100% horizontal stacked strips, one above the other, on the same width, each 32px tall:
- Top: **"Taxpayers"**, segmented by income group (5 groups).
- Bottom: **"Income tax paid"**, the same 5 groups in the same order.
- Use the same `--seq-*` step per group in both strips. Draw thin polygons (`.link`, `fill: var(--bar-soft); opacity: .6`) joining each group's top segment to its bottom segment, so the widening is visible.
- Highlight one group (over £100,000) in `--bar`; the others in `--rest`/`--seq-4`. Bracket and callout: "About {4} in every 100 taxpayers · about £{45} of every £100 of income tax".
- Caption (exact pattern): "People earning over £100,000 are about {4} in every 100 taxpayers. They pay about £{45} of every £100 of income tax."
- Under the strips: "People earning less than £12,570 a year usually pay no income tax, so they are not shown."

### 4.5 Type scale and spacing

| Role | Spec |
| --- | --- |
| Hero figure | serif 700, `clamp(3rem, 9vw, 6rem)`, line-height 1, `font-variant-numeric: lining-nums tabular-nums` |
| H1 | serif 700, `clamp(2rem, 5vw, 3rem)` (as now) |
| Band H2 | serif 700, `clamp(1.5rem, 3.5vw, 2rem)`. The £ amount in the H2 is in `--bar`'s text-safe partner `--accent` |
| Body | sans 1.0625rem/1.55, max 60ch (34ch in story bands) |
| Caption (figcaption) | sans 600 1rem, `--ink`. It is the finding, so it is not muted |
| Chart ticks | 12px rendered minimum, `--muted` |
| Callouts | 13px 600 `--ink` |
| Source line | 0.8125rem `--muted` |

Spacing: 8px base. Inside a card: 16/24. Between H2 and its graphic: 16. Between bands: 96 desktop / 64 phone. Never put a card inside a card.

### 4.6 Bars (`.bars`)

- Row height at least 44px on phones. Label left, value right, bar under the label on phones and beside it from 720px (as now).
- Bar track: show a faint `--grid` track at 100% width behind each fill, so short bars still read as part of the same whole.
- The value is a `.num-val` button. No trailing "Check this number" link (fix 9).
- "Everything else" and remainder rows: `.bar-fill.rest` (`--rest`), always last.
- A highlighted row (benefit context chart): `--bar` plus bold label plus `aria-current="true"`. Other rows: `--rest`.

### 4.7 Lines and columns

- Prefer **lines** for 10-year trends of one series (benefit pages). Use **columns** only for the total-spending chart, where the forecast hatch on columns is already understood.
- Forecasts: dashed line or hatched column **and** the shaded `.fc-band` **and** the words "Forecast by the OBR". Legend swatches match the mark type (fix 17).
- The y-axis starts at zero for money. 4 or 5 gridlines. Axis title above the plot, left-aligned, in plain words: "£ billion, adjusted for rising prices".

### 4.8 Mobile rules (390px reference)

- No horizontal page scroll at 320px wide. Test with `document.documentElement.scrollWidth <= innerWidth` in the Playwright smoke test for every page. This would have caught fix 1.
- The H1 must be visible in the first 844px screen with at least 300px of content below it (fix 2).
- SVG charts switch to the 360-wide viewBox below 480px (fix 13). Squares grids are at most 70% of width and centred. Pictogram grids are 100%.
- Two-column story bands and tile rows collapse to one column below 720px, text first.

### 4.9 States

- **Loading:** reserve the graphic's final height (an `aspect-ratio` box in `--surface-2`) with "Loading…" centred, so the page does not jump.
- **Error:** `.state.error` inside the same box, in the copy from `layman-ux.md` 1.3.
- **Gap:** never an empty box as a whole band. Use one muted sentence inside the nearest related band.

---

## 5. Verification for the builder

1. Playwright: for each page at 390 and 1280, assert `scrollWidth <= innerWidth`, and assert the H1's `getBoundingClientRect().top < 300` at 390.
2. Grep that no page's controls bar contains `.badge-fail` outside `reconciliation.html`.
3. Screenshot the homepage at 1280: each squares grid is at least 200px wide.
4. On Home, Spending, Benefits and Benefit, toggle the basis. Every meta line and tile on screen must change wording together.
5. Contrast-check `--seq-3`/`--seq-4` against `--surface` in light and dark.
6. Existing checks: no `style=` or inline `<script>`, the banned-jargon grep, and axe on Home, one benefit page and Words explained.
