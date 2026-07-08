# Infrastructure Cache Schema

Use this reference when changing source persistence, database cache behavior, or cross-layer data contracts.

## Rule

There is no standalone business data layer. The active business layers are coarse screening, fine screening, plan generation, and display. Shared cache, network policy, and logging live in `scripts/infra/`.

Each business layer should keep three boundaries:

- `network.py`: realtime source fetch and source fallback.
- `repository.py`: database cache reads/writes and normalized data assembly.
- logic module: scoring, ranking, planning, or rendering rules.

Remote source data must be persisted into SQLite before being consumed by strategy or plan logic. Strategies and plans should read normalized dataframes from repositories or SQLite-backed helpers, not call AKShare, Sina, Eastmoney, efinance, or other upstream APIs directly.

## Cache

Default database:

`$SKILL/.cache/stock_data.sqlite`

Override with:

`TECH_GROWTH_DB=/path/to/stock_data.sqlite`

Legacy CSV caches from `$SKILL/.cache/` or `TECH_GROWTH_SCREENER_CACHE` are imported into SQLite on first read. New remote fetches should be written to SQLite source tables through the infrastructure cache boundary.

## Core Tables

- `cache_meta`: maps logical source keys to raw SQLite tables.
- `source_runs`: records sync attempts and errors.
- `stocks`: normalized stock identity and industry metadata.
- `market_cap_snapshot`: stock market-cap snapshots by date and source.
- `financial_reports`: normalized financial report fields.
- `industry_members`: industry or board constituents.
- `quotes_daily`: daily OHLCV bars for backtests.

## Daily Price Sync

Use `scripts/run.py sync --dataset daily_prices` to fill `quotes_daily`.

Supported inputs:

- `--codes 600584,000021`: sync explicit symbols.
- `--from-strategy --top 10`: run the configured strategy and sync its top symbols.
- `--start YYYY-MM-DD --end YYYY-MM-DD`: required date range.
- `--adjust qfq`: default front-adjusted prices; use `--adjust ""` for unadjusted prices.

The data layer writes raw upstream tables into `raw_*` and normalized rows into `quotes_daily`.
For offline tests, `--source cache` reads `daily_prices_<code>.csv` from the active cache directory.

## Source Table Naming

Raw upstream responses should be stored as `raw_*` tables and registered in `cache_meta`.

Examples:

- `stock_zh_a_spot` -> `raw_stock_zh_a_spot`
- `stock_yjbb_20260331` -> `raw_stock_yjbb_20260331`
- `industry_cons_半导体` -> a sanitized `raw_*` table
