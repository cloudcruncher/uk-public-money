# UK Public Money

A static, open-data view of UK public spending and revenue, with a provenance record behind every published number.
Each figure links to a "Check this number" page that gives the publisher's file, sheet, cell, and SHA-256 so a reader
can find the same value in the original download.

**Status:** first slice in development. The live site URL is not yet known. Nothing here is deployed by this README.

## What it covers (first slice)

- Spending by function (COFOG) from HM Treasury PESA, and total managed expenditure (TME).
- Macro aggregates and the GDP deflator from the OBR Public Finances Databank (used for real-terms and % of GDP).
- HMRC tax and NICs receipts, and income tax liabilities by income range.
- DWP benefit expenditure and caseloads.
- A reconciliation page (rules R1 to R7) and a corrections log.

Out of scope for now: spend over £25k, Contracts Finder, Stat-Xplore, ONS labour market, PAYE RTI, ONS household
incidence, and debt stocks. The ONS Public Sector Finances parser is a stub (see [docs/SOURCES.md](docs/SOURCES.md)).

## Quick start

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
PYTHONPATH=src uv run python -m ukpm fetch          # download and parse enabled sources (needs network)
PYTHONPATH=src uv run python -m ukpm build          # write site/api/v1 (use --offline for cached or fixture files)
PYTHONPATH=src uv run python -m ukpm check-api site/api/v1
uv run pytest -q
uv run ruff check .
```

## Documentation

- [docs/METHODOLOGY.md](docs/METHODOLOGY.md): how numbers are sourced, converted, stitched, and reconciled.
- [docs/CORRECTIONS.md](docs/CORRECTIONS.md): how corrections are logged and published.
- [docs/API.md](docs/API.md): the static JSON and Parquet files under `site/api/v1`.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): design and module layout.
- [docs/SOURCES.md](docs/SOURCES.md): source register with verdicts and known gaps.
