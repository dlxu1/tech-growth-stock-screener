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

## Pre-Run Update Policy

Non-sync commands can use `--update-policy` to refresh required cache data before running:

- `none`: default; no pre-run update.
- `cache`: force offline cache mode by setting the command source to cache.
- `auto`: update missing or stale required data and continue on recoverable update failures.
- `strict`: update missing or stale required data and stop if an update fails.
- `refresh`: force-refresh required data and stop if an update fails.

Preflight checks are implemented in `scripts/infra/preflight.py` and call `sync_dataset()` for actual writes. This keeps remote source persistence inside `scripts/data/` and prevents strategy, plan, or report code from calling upstream APIs directly.

Default freshness expectations:

- `stock_zh_a_spot`: max 1 day old.
- financial reports: any cached selected report period within the latest report-date candidates is acceptable unless forced.
- `index_constituents`: max 7 days old by `updated_at`.
- `quotes_daily`: must cover the requested pre-run range for all checked symbols.

For CSI 300 workflows, `combo`, `fine`, and `plan` can preflight `quotes_daily` for cached index members. The default pre-run daily range is the latest 180 days ending at today, unless `--update-start` or `--update-end` is supplied.

## Core Tables

- `cache_meta`: maps logical source keys to raw SQLite tables.
- `source_runs`: records sync attempts and errors.
- `stocks`: normalized stock identity and industry metadata.
- `market_cap_snapshot`: stock market-cap snapshots by date and source.
- `financial_reports`: normalized financial report fields.
- `industry_members`: industry or board constituents.
- `index_constituents`: index member pools such as CSI 300, including constituent date, stock identity, exchange, optional latest weight, and weight date.
- `quotes_daily`: daily OHLCV bars for fine screening, trade plans, and price-derived metrics.
- `layer_runs`: one row per persisted screen, coarse, combo, fine, or plan execution, including command parameters and layer metadata as JSON.
- `layer_results`: one row per persisted layer output row. The complete row is stored in `row_json`; common lookup fields such as `code`, `name`, `rank`, `score`, `action`, `strategy`, and `trade_date` are also stored as columns.

## Layer Result Persistence

Strategy-layer outputs are persisted by default:

- `screen`: strict technology-growth screen output.
- `coarse`: coarse strategy output, including `--strategy all` expanded rows.
- `combo`: potential-stock combo scoring output.
- `fine`: technical fine-screening output.
- `plan`: next-session operation-plan output.

When `plan` runs, the internal coarse and fine outputs are also persisted because each layer owns its own persistence. Use `--no-persist-results` on a command to skip persistence for that command and its internal layer calls.

`layer_results.row_json` is the durable complete payload for future analysis. The extracted columns are intentionally small and query-oriented, so adding new output fields does not require schema migration.

## Daily Price Sync

Use `scripts/run.py sync --dataset daily_prices` to fill `quotes_daily`.

Supported inputs:

- `--codes 600584,000021`: sync explicit symbols.
- `--from-strategy --top 10`: run the configured strategy and sync its top symbols.
- `--from-index --index-symbol 000300`: read cached index constituents, such as CSI 300, and sync those symbols.
- `--start YYYY-MM-DD --end YYYY-MM-DD`: required date range.
- `--adjust qfq`: default front-adjusted prices; use `--adjust ""` for unadjusted prices.
- `--source auto`: for daily prices, tries `efinance`, `akshare`, `sina`, then `baostock`.
- `--skip-existing`: skip a symbol when existing `quotes_daily` rows already cover the requested date range.

The data layer writes raw upstream tables into `raw_*` and normalized rows into `quotes_daily`.
For offline tests, `--source cache` reads `daily_prices_<code>.csv` from the active cache directory.

Example CSI 300 daily sync with resumability:

```bash
python scripts/run.py sync --dataset daily_prices --from-index --index-symbol 000300 --start 2026-01-09 --end 2026-07-09 --adjust qfq --source auto --no-proxy --skip-existing
```

## Index Constituents Sync

Use `scripts/run.py sync --dataset index_constituents --index-symbol 000300` to persist an index member pool before running `--universe csi300` or `--from-index`.

Normalized rows are written to `index_constituents` with:

- `index_symbol`
- `index_name`
- `constituent_date`
- `code`
- `name`
- `exchange`
- `weight`
- `weight_date`
- `source`
- `updated_at`

The cache key includes `index_symbol`, `constituent_date`, `code`, and `source`, so repeated constituent snapshots can coexist when the upstream date changes.

## Source Table Naming

Raw upstream responses should be stored as `raw_*` tables and registered in `cache_meta`.

Examples:

- `stock_zh_a_spot` -> `raw_stock_zh_a_spot`
- `stock_yjbb_20260331` -> `raw_stock_yjbb_20260331`
- `industry_cons_半导体` -> a sanitized `raw_*` table
- `index_cons_000300` / `index_cons_weight_000300` -> CSI 300 raw member and weight source tables
