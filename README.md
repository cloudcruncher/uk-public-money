# UK Public Money

A static, open-data view of UK public spending and revenue, with a provenance record behind every published number.
Each figure links to a "Check this number" page that gives the publisher's file, sheet, cell, and SHA-256 so a reader
can find the same value in the original download.

**Live site:** https://cloudcruncher.github.io/uk-public-money/ (rebuilt daily). The idea: heard a number about UK public money? See what it means in plain English, then check it yourself.

## What it covers

- Spending by function (COFOG) from HM Treasury PESA, and total managed expenditure (TME).
- Macro aggregates and the GDP deflator from the OBR Public Finances Databank (used for real-terms and % of GDP).
- HMRC tax and NICs receipts, and income tax liabilities by income range.
- DWP benefit expenditure and caseloads.
- Plain-English story homepage ("out of every £100", per person, per household), benefits explained one by one (cost, claimants, cost per claimant), and a glossary.
- ONS population, households, GDP and Public Sector Finances; OBR outlook tables; Cabinet Office spend over £25k (aggregated).
- A reconciliation page (rules R1 to R14) and a corrections log.

Out of scope for now: Contracts Finder, Stat-Xplore, ONS labour market, PAYE RTI and debt stocks. Known gaps are in [docs/SOURCES.md](docs/SOURCES.md).

## Quick start

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
PYTHONPATH=src uv run --no-active python -m ukpm fetch          # download and parse enabled sources (needs network)
PYTHONPATH=src uv run --no-active python -m ukpm build          # write site/api/v1 (use --offline for cached or fixture files)
PYTHONPATH=src uv run --no-active python -m ukpm check-api site/api/v1
uv run --no-active pytest -q
uv run --no-active ruff check .
```

## Documentation

- [docs/METHODOLOGY.md](docs/METHODOLOGY.md): how numbers are sourced, converted, stitched, and reconciled.
- [docs/CORRECTIONS.md](docs/CORRECTIONS.md): how corrections are logged and published.
- [docs/API.md](docs/API.md): the static JSON and Parquet files under `site/api/v1`.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): design and module layout.
- [docs/SOURCES.md](docs/SOURCES.md): source register with verdicts and known gaps.
