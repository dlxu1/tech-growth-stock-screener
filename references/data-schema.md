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
- `dashboard_snapshots`: one row per reusable dashboard model snapshot, keyed by dashboard parameters plus source-data fingerprints. The complete dashboard data model is stored in `model_json`.
- `dashboard_matrix_signals`: one lightweight row per dashboard matrix candidate per signal date, keyed by dashboard matrix scope, source-data fingerprint, date, and code. It stores macro score, technical score, that date's adaptive thresholds, and whether the stock belongs to `好时机+高潜力`.

## Layer Result Persistence

Strategy-layer outputs are persisted by default:

- `screen`: strict technology-growth screen output.
- `coarse`: coarse strategy output, including `--strategy all` expanded rows.
- `combo`: potential-stock combo scoring output.
- `fine`: technical fine-screening output.
- `plan`: next-session operation-plan output.

When `plan` runs, the internal coarse and fine outputs are also persisted because each layer owns its own persistence. Use `--no-persist-results` on a command to skip persistence for that command and its internal layer calls.

`layer_results.row_json` is the durable complete payload for future analysis. The extracted columns are intentionally small and query-oriented, so adding new output fields does not require schema migration.

## Dashboard Snapshot Persistence

After the dashboard pipeline completes the plan stage and builds the final
dashboard data model, it stores a reusable snapshot in `dashboard_snapshots`.
The table stores:

- `snapshot_key`: SHA-256 key derived from snapshot version, dashboard command
  parameters, and source-data fingerprint.
- `as_of_date`, `backtest_date`, `universe`, `universe_index_symbol`, `sector`,
  `stock_types`, `report_date`, and `source`: query-oriented snapshot
  dimensions.
- `data_fingerprint_json`: counts and latest update/date markers for source
  tables such as `cache_meta`, `quotes_daily`, `index_constituents`, and
  normalized source tables.
- `params_json`: normalized dashboard parameters used in the key.
- `model_json`: the complete JSON-serializable dashboard model consumed by HTML
  rendering, API responses, and validation.
- `html_path`: optional static HTML path when a caller records one.

`dashboard_snapshots` is separate from `layer_results`. Stage outputs still
persist individually for audit and row-level analysis, while the snapshot table
answers "have we already built this full dashboard model?".

Snapshot reuse is enabled by default for `dashboard`, `dashboard-server`, and
`validate-dashboard`, and can be disabled with `--no-dashboard-cache`. Passing
`--rebuild-dashboard-cache`, `--refresh`, or `--update-policy refresh` forces a
recalculation rather than reusing an old snapshot.

## Dashboard Matrix Signal Persistence

Every cache-enabled dashboard model materializes its matrix membership into
`dashboard_matrix_signals`. The table stores:

- `scope_key`: SHA-256 key derived from matrix-affecting dashboard parameters
  such as source, strategy, universe, sector, stock-type filter, report date,
  and top-count settings.
- `data_fingerprint_key`: SHA-256 key derived from the same source-data
  fingerprint used by dashboard snapshots.
- `as_of_date`, `code`, `name`: signal date and stock identity.
- `macro_score`, `technical_score`: the values used on the dashboard matrix.
- `macro_threshold`, `technical_threshold`: that signal date's adaptive
  thresholds.
- `is_high_good`: 1 when the row is classified as `好时机+高潜力`.
- `params_json` and `data_fingerprint_json`: full identity payloads for audit.

The repeated `好时机+高潜力` hit-count annotation should aggregate
`dashboard_matrix_signals` first. If a date is missing, it may hydrate the
matrix signal rows from an existing matching `dashboard_snapshots.model_json`
before falling back to recalculating that missing date.

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
