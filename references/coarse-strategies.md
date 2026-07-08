# Coarse Strategies

Use this reference when changing coarse-screening data assembly, strategy names, score weights, missing-field fallback behavior, or per-strategy output size.

## Layer Boundary

Coarse screening is the first business-selection layer. It narrows the technology universe to `--top 5` names per strategy by default. It is not a final buy list and does not produce entry or stop-loss rules.

The layer is split into:

- `scripts/strategies/coarse/network.py`: fetches the source bundle needed by coarse screening.
- `scripts/strategies/coarse/repository.py`: assembles cached/source data into the base universe consumed by strategies.
- `scripts/strategies/coarse/registry.py`: defines strategy metadata, score functions, positive filters, and top-N selection.

Remote fetches must be cached through the source/cache boundary before strategy logic consumes them. Strategy logic should operate on dataframes, not direct upstream API calls.

## Input Data

The coarse layer builds a technology stock universe from:

- realtime A-share spot quote data, mainly stock code, name, and market cap;
- financial report data, mainly revenue YoY, profit YoY, report industry, and optional valuation/fundamental fields;
- industry-board names and industry-board constituents;
- cached daily quote metrics from `quotes_daily`, currently `amount_20d`, `return_60d`, and `max_drawdown_252d`.

Primary path:

1. Fetch all A-share market-cap data.
2. Fetch the selected financial report table.
3. Fetch industry-board names.
4. Select technology boards by configured keywords.
5. Fetch full constituents for matched technology boards.
6. Merge constituents with market-cap and financial data.

Fallback path:

If board constituents cannot be fetched, the coarse layer falls back to financial-report industry names. It selects rows whose report industry matches technology keywords and then ranks those stocks by market cap inside that report industry.

## Cache Behavior

The coarse layer relies on SQLite cache tables managed by the infrastructure/source adapters.

- Financial reports are keyed by report date, for example `stock_yjbb_20260331`, so multiple report periods can coexist.
- Spot quote, board list, and board-constituent raw source tables are cached by logical source key. Re-fetching with the same key refreshes the current raw snapshot.
- Daily quote metrics are derived from `quotes_daily`, which keeps historical bars by stock code and trade date.
- Coarse screen outputs are not currently persisted as historical runs.

If coarse result history is needed, add `coarse_runs` and `coarse_results` tables instead of overloading raw source tables.

## Base Universe Assembly

`repository.build_base_universe(args)` returns `(base, meta)`.

`base` contains:

- stock identity: `code`, `name`, `board_name`;
- size: `market_cap`;
- growth: `revenue_yoy`, `profit_yoy`;
- optional valuation/fundamental metrics: `pe`, `pb`, `revenue`, `profit`, `roe`, `gross_margin`, `rd_expense`, `rd_intensity`;
- optional price-derived metrics: `amount_20d`, `return_60d`, `max_drawdown_252d`;
- industry breadth: `industry_growth_breadth`.

`meta` contains the report date, chosen source labels, technology-board count, and technology-universe size.

Optional metric extraction is tolerant. If a metric cannot be found, the strategy still runs and emits a degraded `data_note`.

## Implemented Strategies

Each strategy is registered as a `CoarseStrategy` with:

- `name`: stable command-line id;
- `title`: Chinese display title;
- `description`: explanation used in report output;
- `ranker`: score function returning a comparable series;
- `required_metrics`: fields expected for full-quality scoring;
- `positive_filters`: metrics that should be positive when available.

Implemented strategies:

- `market_cap_low_pe`: 市值龙头 + 低市盈率
- `market_cap_reasonable_pe`: 市值龙头 + 合理市盈率
- `market_cap_revenue_scale`: 高市值 + 高营收规模
- `market_cap_profit_scale`: 高市值 + 高净利润规模
- `market_cap_revenue_growth`: 市值前排 + 营收同比为正
- `market_cap_profit_growth`: 市值前排 + 净利润同比为正
- `market_cap_revenue_profit_growth`: 市值前排 + 营收净利双增长
- `low_pe_positive_growth`: 低 PE + 正增长
- `low_pb_positive_profit`: 低 PB + 正盈利
- `high_roe_reasonable_pe`: 高 ROE + 合理估值
- `high_gross_margin_revenue_growth`: 高毛利率 + 营收增长
- `high_rd_intensity_revenue_growth`: 高研发强度 + 营收增长
- `active_amount_solid_fundamentals`: 成交额活跃 + 基本面不差
- `price_strength_market_cap`: 价格强势 + 市值前排
- `low_drawdown_positive_growth`: 回撤较小 + 正增长
- `industry_breadth_leaders`: 行业景气扩散粗筛

## Ranking Rules

Ranking uses percentile-style helper functions:

- `_rank_high`: larger values receive higher scores.
- `_rank_low`: smaller values receive higher scores.
- `_reasonable_pe_score`: PE closer to the available median receives a higher score.

Score examples:

- `market_cap_low_pe`: `market_cap` 65% + low `pe` 35%.
- `market_cap_reasonable_pe`: `market_cap` 65% + reasonable `pe` 35%.
- `market_cap_revenue_profit_growth`: `market_cap` 45% + `revenue_yoy` 25% + `profit_yoy` 30%.
- `active_amount_solid_fundamentals`: `amount_20d` 55% + positive growth composite 45%.
- `price_strength_market_cap`: `return_60d` 55% + `market_cap` 45%.
- `low_drawdown_positive_growth`: low absolute drawdown 55% + positive growth composite 45%.

After scoring, results are sorted by:

1. `coarse_score` descending;
2. `market_cap` descending.

Then each strategy keeps `args.top`, defaulting to 5 for the `coarse` command.

## Missing Data Behavior

If a required metric is completely missing, the strategy still runs. Missing metrics are neutralized by rank helpers or skipped by filters, and `data_note` is set to:

```text
缺少字段，已降级: metric_name
```

If a positive filter would empty the result set, the strategy falls back to the unfiltered base universe to avoid producing no output solely due to sparse optional fields.

## Output Columns

Coarse output includes:

- strategy fields: `coarse_strategy`, `coarse_strategy_title`, `coarse_score`, `coarse_reason`;
- stock fields: `code`, `name`, `board_name`;
- fundamental fields: `market_cap`, `pe`, `pb`, `revenue_yoy`, `profit_yoy`;
- price-derived fields: `amount_20d`, `return_60d`, `max_drawdown_252d`;
- data diagnostics: `data_note`.

## Maintenance Checklist

When adding or changing a coarse strategy:

1. Add or update a score function in `registry.py`.
2. Register it in `STRATEGIES`.
3. Declare all required metrics and positive filters.
4. If the strategy needs a new metric, add extraction or assembly in `repository.py`.
5. If the metric comes from a new upstream source, add fetch logic behind the network/source boundary and persist it to SQLite.
6. Update this reference.
7. Validate with one single strategy and with `--strategy all`.

## Commands

Run all coarse strategies:

```bash
python scripts/run.py coarse --strategy all --top 5
```

Run one strategy:

```bash
python scripts/run.py coarse --strategy market_cap_reasonable_pe --top 5
```

Run from existing cache only:

```bash
python scripts/run.py coarse --strategy all --top 5 --source cache
```
