# Data Rules

## Data Sources And Cache

The project uses public third-party A-share data sources through the existing
source adapters and caches normalized data in SQLite.

Default cache path is described in `README.md`. The important tables include:

- `cache_meta`
- `source_runs`
- `stocks`
- `market_cap_snapshot`
- `financial_reports`
- `industry_members`
- `index_constituents`
- `quotes_daily`
- `layer_runs`
- `layer_results`
- `dashboard_snapshots`
- `dashboard_matrix_signals`

Prefer cache-backed commands for local iteration:

```bash
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python /Users/xudoulei/work/tech-growth-stock-screener/scripts/run.py dashboard --source cache --output /Users/xudoulei/work/tech-growth-stock-screener/.cache/reports/dashboard_latest.html
```

Historical dashboard replay uses `--as-of-date YYYY-MM-DD`. When this parameter
is present, daily quote reads for macro price metrics, technical analysis, and
operation advice only use `quotes_daily.trade_date <= as_of_date`. With
`--report-date auto`, financial-report candidates are also capped to quarter
dates not later than `as_of_date`. This is a signal snapshot for research
review. The optional signal backtest described below is the only step that may
read daily quotes after `as_of_date`, and it does so only to calculate fixed
forward holding returns for the selected signal date.

## Data Update Policy

Data updates should be incremental by default. Do not force full remote refreshes
unless the user explicitly asks for a rebuild or passes the force-refresh flags.

- `sync --dataset daily_prices` defaults to `--skip-existing`. For each symbol,
  if `quotes_daily` already covers the requested date range, the symbol is
  skipped. If the cache covers the beginning of the requested range but is
  missing the tail, only dates after the cached max `trade_date` are fetched and
  upserted into `quotes_daily`.
- Use `--no-skip-existing` only when deliberately re-fetching the full requested
  daily-price range.
- `--refresh` and `--update-policy refresh` are force-refresh controls. Ordinary
  "更新数据" requests should avoid them unless a full rebuild is requested.
- `sync --dataset financials --report-date auto` should avoid selecting a newly
  published but obviously incomplete quarter. Auto selection prefers the latest
  cached/fetched `stock_yjbb_YYYYMMDD` report whose row count is at least
  `FINANCIAL_AUTO_MIN_ROWS`; if no complete candidate exists, it may fall back
  to the first available incomplete candidate with visible row counts.

Source table behavior remains table-specific:

- `quotes_daily` and `index_constituents` are normalized upsert tables.
- Raw daily-price source snapshots are stored as range-specific
  `daily_prices_<code>_<start>_<end>_<adjust>` tables.
- Spot quotes, industry boards, industry constituents, and financial-report
  raw tables are source snapshots and may be replaced when their own sync is
  explicitly run.
- `dashboard_snapshots` stores complete dashboard model JSON after the plan
  stage and downstream dashboard model enrichment are complete. Snapshot reuse
  is keyed by dashboard parameters plus source-data fingerprints, not by
  `layer_results`.
- `dashboard_matrix_signals` stores lightweight per-date matrix membership
  derived from dashboard models so repeated `好时机+高潜力` hit counts can be
  queried without recursively rebuilding every historical dashboard.

## Dashboard Snapshot Cache

Dashboard-oriented commands can reuse complete dashboard data snapshots when
`--dashboard-cache` is enabled. This is the default for `dashboard`,
`dashboard-server`, and `validate-dashboard`.

The snapshot node runs after:

```text
股票池 -> 宏观粗筛 -> 技术分析 -> 操作建议
```

It stores the final dashboard model in `dashboard_snapshots.model_json`. Later
requests with the same dashboard parameters and unchanged source-data
fingerprint can load that model directly instead of recalculating all four
business stages.
When a dashboard model is calculated or loaded from a snapshot, the matrix
membership is also materialized into `dashboard_matrix_signals` when dashboard
cache is enabled. This derived table is used to aggregate repeated
`好时机+高潜力` hits across historical signal dates without rebuilding every
dashboard model in the lookback window.

Snapshot reuse is skipped when:

- `--no-dashboard-cache` is passed;
- `--rebuild-dashboard-cache` is passed;
- `--refresh` is passed;
- `--update-policy refresh` is passed.

`--rebuild-dashboard-cache` reruns the full pipeline and replaces the matching
snapshot. Historical snapshots should be treated as research replay artifacts:
they preserve the model produced under the source data fingerprint available at
the time, and are not direct trade instructions.

## Dashboard v1 行业主线证据板

`dashboard` v1 现在在数据健康条下方插入行业主线证据板，并把选中的
行业作为后续 `股票池 -> 宏观粗筛 -> 技术分析 -> 操作建议` 的上游作用域。
主线榜和选中行业的口径如下：

- 行业主线强度优先复用 `board_name`、`return_60d`、`amount_20d`、
  `revenue_yoy`、`profit_yoy`、`market_cap` 和 `max_drawdown_252d` 的证据排序骨架。
- `industry_members` 可用时，行业股票池优先使用该行业全成分股。
- 行业全成分股不可用时，降级为当前基础池内的行业样本，并明确标注样本代理或指数内样本。
- 行业证据板和 `summary.industry_pool` 需要展示当前股票池来源、池内数量和降级说明。
- 默认未显式指定行业时，选中行业主线榜排名第一且有可用股票池的行业。

## Dashboardv2 兼容视图

`dashboardv2` 现在只保留兼容入口和暂停更新提示，不再承接新的交互需求。
历史上它的展示链路曾是：

```text
行业主线 -> 主线股票池 -> 龙头收敛 -> 技术确认 -> 每日复盘
```

若旧入口仍可访问，页面必须保守显示暂停更新说明，不得把它继续包装成新的主入口。

## Stage Contracts

### 股票池

Purpose: create the first research universe from a base universe and optional
sector text. The current stage is a pure board/universe selection step, not a
scoring strategy.

Expected display fields include:

- `code`
- `name`
- `stock_type`
- `board_name`
- `market_cap`
- `revenue_yoy`
- `profit_yoy`
- `amount_20d`
- `return_60d`
- `max_drawdown_252d`
- `risk_flags`
- `data_note`

Presentation rules:

- `stock_type`: classify by `board_name` using `configs/stock_type_rules.json`
  unless `--stock-type-config` points to another JSON file. The default config
  includes `科技股`, `周期股`, `金融股`, `消费/防御`, and `未分类`. Hover title
  uses `stock_type_note` to show the matched keyword and board-name basis.
- `--stock-types` can select one or more stock types, such as `科技股,周期股`,
  for the downstream dashboard flow. The stock-pool stage still displays the
  full classified pool; only the candidates passed to `宏观粗筛` are filtered.
- Dashboard, dashboard-server, and validate-dashboard default to
  `--universe csi300` so the interactive matrix starts from the cached CSI 300
  pool unless another universe is explicitly selected. When the dashboard
  selects an industry mainline, the stock-pool stage may expand to that
  industry's full constituents and carry `selected_industry` / pool-source
  metadata forward for downstream stages.
- `market_cap`: divide by `100000000`, keep two decimals, append `亿`.
- `amount_20d`: divide by `100000000`, keep two decimals, append `亿`.
- `revenue_yoy`, `profit_yoy`, `return_60d`, `max_drawdown_252d`: keep two decimals and append `%`.
- Hide `match_reason` from the main dashboard table.
- Keep `data_note` detailed enough to explain missing fields and data limitations.

### 宏观粗筛

Purpose: rank the previous stage's stocks with a multi-strategy coarse score.
It must not pull from the full base universe when the dashboard flow is serial.
The dashboard keeps up to 100 rows for the next stage. If `--stock-types` is
provided, this stage receives only stock-pool rows whose configured
`stock_type` is selected.

Main score:

```text
基础宏观粗筛分 =
  多策略共振分 * 30%
  + 成长分 * 22%
  + 质量分 * 20%
  + 风控分 * 13%
  + 流动性分 * 7%
  + 动量分 * 8%
```

Component meanings:

- `overlap_score`: matched strategy weight / total strategy weight * 100.
- `growth_score`: percentile rank of positive revenue YoY plus positive profit YoY.
- `quality_score`: ROE within-industry rank * 40% + gross margin within-industry rank * 25% + PEG score * 35%.
- `risk_control_score`: |max_drawdown_252d| within-industry rank * 70% + amount_20d global rank * 30%.
- `liquidity_score`: 20-day amount percentile rank * 100.
- `momentum_score`: return_60d rank * 55% + mean_reversion_score * 45%.
- The final `combo_score` is recomputed by market regime:
  - `bull`: overlap 30%, growth 20%, quality 15%, risk 10%, liquidity 5%, momentum 20%; momentum = trend 70% + reversion 30%.
  - `transition`: overlap 30%, growth 23%, quality 24.8%, risk 14.8%, liquidity 7%, momentum 3.2%; momentum = trend 30% + reversion 70%.
  - `bear`: overlap 25%, growth 22%, quality 30%, risk 18%, liquidity 5%, momentum 0%; displayed momentum uses reversion only but does not affect total score.

Dashboard presentation:

- Main columns: `code`, `name`, `market_cap`, `combo_score`, `growth_score`,
  `quality_score`, `risk_control_score`, `strategy_summary`.
- `strategy_summary` shows only the number of hit strategies.
- Hover title for `strategy_summary` shows the specific matched strategies.
- Scores and numeric values should keep two decimals.

### 技术分析

技术分 =
  趋势分 \* 28
  + 动量分 \* 22
  + 量能分 \* 22
  + 突破分 \* 15
  + 风险分 \* 8
  + 流动性分 \* 5


Purpose: rank the previous macro coarse result with daily-price technical
signals.
The dashboard technical stage runs on all macro coarse rows and keeps up to 100
rows.

Main score:

```text
技术分 =
  趋势分 * 30
  + 动量分 * 20
  + 量能分 * 20
  + 突破分 * 15
  + 风险分 * 10
  + 流动性分 * 5
```

The technical stage uses moving averages, 20-day return, MACD, RSI, amount
expansion, 20-day high/breakout position, 20-day drawdown, ATR, and liquidity
checks.

Dashboard presentation:

- Hide `coarse_strategies` from the technical fine-screen table.
- Ratio fields `change_pct`, `return_20d`, `return_60d`, `max_drawdown_20d`
  are stored as ratios and must be multiplied by 100 for display.
- Numeric fields such as `coarse_score`, `technical_score`, `close`,
  `amount_ratio`, `ma5`, `ma10`, `ma20`, `macd_hist`, and `rsi14` should keep
  two decimals.

### 操作建议

The dashboard operation-advice stage is a rule-based next-session plan, not a
command to trade. It must be generated for the full technical fine-screen result,
which itself comes from all macro coarse rows. The dashboard computes a combined
attention score for ranking and matrix point size: macro potential (`combo_score`,
falling back to normalized `coarse_score`) * 65% plus technical timing
(`technical_score`) * 35%. The displayed table shows plan fields only. It must
not include personal budget/allocation fields such as ETF core budget, stock
satellite budget, cash reserve, one-lot affordability, or budget status.

Expected display fields include:

- `code`
- `name`
- `technical_score`
- `action`
- `horizon_tags`
- `primary_horizon`
- `horizon_reason`
- `horizon_data_note`
- `latest_close`
- `planned_entry`
- `initial_stop`
- `risk_pct`
- `take_profit_1r`
- `take_profit_2r`
- `plan_note`

Keep language conservative: use `观察`, `条件买入`, `等待回踩`, `等待放量确认`,
or `暂不交易`, and include risk/data limitations when relevant.

Investment horizon annotations are display-only research notes generated from
the merged macro, technical, and operation-plan context. They must not change
scores, thresholds, stage membership, sorting, operation-plan rules, dashboard
snapshot identity, or backtest samples.

- `horizon_tags`: list of applicable labels, displayed as `适合周期`. The fixed
  order is `长线`, `中线`, `短线`.
- `primary_horizon`: the current priority label, displayed as `优先关注`.
- `horizon_reason`: short Chinese explanation for assigned labels.
- `horizon_data_note`: conservative data-quality note, usually
  `证据不足，需人工复核` when no label is assigned.

Current horizon rules:

- `长线`: requires `quality_score >= 75`, `risk_control_score >= 65`,
  `growth_score >= 60`, and at least one quality/value/growth strategy hint
  such as `高 ROE + 合理估值`, `高毛利率 + 营收增长`, `市值前排 + 营收净利双增长`,
  `低 PE + 正增长`, `低 PB + 正盈利`, or `回撤较小 + 正增长`.
- `中线`: requires macro potential and technical timing共振, currently
  `combo_score >= 80` and `technical_score >= 75`.
- `短线`: requires an executable plan: `usable_for_plan` true,
  `primary_strategy` in `breakout_buy`, `pullback_ma_buy`,
  `volume_confirm_buy`, valid positive `planned_entry` and `initial_stop`, and
  `0 < risk_pct <= 0.12`.

The dashboard operation-advice table may show `horizon_tags` as `适合周期`.
The selected-stock detail panel should show `适合周期` and `优先关注` inside the
stock detail area, not as top-level global dashboard facts.

Daily email summaries must consume these dashboard model fields for
`好时机+高潜力` candidates. The email body shows `适合周期`, `优先关注`, and
`周期说明`; the JSON payload keeps `horizon_tags`, `primary_horizon`,
`horizon_reason`, and `horizon_data_note`. If fields are missing, email output
falls back to `适合周期：证据不足，需人工复核` and keeps the existing research-risk
disclaimer.

### 潜力-时机矩阵

The dashboard matrix includes both macro coarse and technical-analysis rows.
The x-axis is macro potential, the y-axis is technical timing, and point size is
the combined attention score. The visual quadrant split must use the same
thresholds as color classification: macro potential `>= 80` is high potential,
and technical timing `>= 75` is good timing. Do not add a separate outline or
black-ring highlight for the top operation-advice rows; point size already
reflects combined attention. Point hover text should explain the threshold
comparison so red/blue/green status is not confused with the background zone.
The matrix has local stock-type chips that filter the currently displayed
matrix candidates by their configured `stock_type`.

The matrix can be recalculated for a historical date through the local
dashboard server or a static dashboard generated with `--as-of-date`. Changing
the date may reuse a matching `dashboard_snapshots` model; otherwise it reruns
the serial dashboard flow and rebuilds all matrix scores from the selected
date's available cached data.
The repeated `好时机+高潜力` hit-count diagnostic is enabled by default. Pass
`--no-recent-high-good-hits` only when temporarily disabling the annotation for
debugging. The dashboard tracks how often current `好时机+高潜力` stocks appeared
in the same quadrant during the previous 30 calendar days. Each historical
signal date uses that date's own adaptive matrix thresholds, not today's
thresholds. The count is exposed on fine/plan rows as
`recent_high_good_hits` with `count`, `dates`, `window_start`, `window_end`, and
`highlight`. `highlight=true` starts at 4 hits, and the HTML matrix renders a
special ring/badge plus hover dates for those repeated strong signals. This is
display-only diagnostic context and must not change scores, thresholds, stage
membership, or operation advice. Each dashboard model also materializes
per-date matrix signals into `dashboard_matrix_signals`; the repeated-hit
annotation first aggregates that table, then hydrates missing signal dates from
existing `dashboard_snapshots`, and only falls back to recalculating missing
historical dates. The computed repeated-signal result is still cached under
`.cache/recent_high_good_hits.json` by dashboard date, signal-date window,
current high-potential+good-timing codes, relevant dashboard parameters, cache
version, and key SQLite table freshness/count fingerprints.
When the CSI 300 constituent cache has no snapshot at or before the selected
date, historical replay falls back to the latest cached constituent snapshot and
still applies the selected date cutoff to quotes and financial-report dates.
In strict cache mode, if the requested historical report period is not cached,
the dashboard falls back to the latest cached financial-report table so the
page can still render with an explicit data-health warning rather than failing.

### 数据回测

Purpose: evaluate how the selected date's dashboard scores would have behaved
under simple fixed holding periods. This is a research replay module, not a
position-sizing, execution, or investment-advice engine.

Signal date:

- The dashboard backtest can use `--backtest-date YYYY-MM-DD`. If it is omitted,
  it falls back to `--as-of-date`.
- The standalone CLI `signal-backtest` requires either `--backtest-date` or
  `--as-of-date`.
- If `backtest_date` differs from the matrix `as_of_date`, the backtest reruns
  the serial dashboard signal flow for `backtest_date` before reading any future
  quote rows. The main matrix can remain on the current or another selected
  date.

Selectors:

- `宏观潜力 Top10`: top 10 by `combo_score`.
- `技术分 Top10`: top 10 by `technical_score`.
- `综合关注 Top10`: top 10 by `attention_score`, where `attention_score =
  combo_score * 65% + technical_score * 35%`.

Return rule:

- Buy price: next available trading day's `open` after the signal date.
- Sell price: the N-th future trading day's `close`.
- Default holding horizons: 7, 14, and 21 trading days. CLI parameter
  `--holding-days` can override this comma-separated list.
- If future quote rows are absent or shorter than the required horizon, mark
  the row as `missing_future_quotes` or `insufficient_future_quotes`; do not
  fill, forward-fill, or synthesize prices.
- Summary returns use only complete rows.

Dashboard presentation:

- Show one `数据回测` section under the potential-timing matrix when backtest
  data exists.
- For each selector, display complete sample count, average return, and win
  rate for each holding period, plus default 7-day detail rows.
- Keep the text conservative and label it as research verification.

### 操作回测

Purpose: evaluate whether the rule-based `操作建议` entries for high-potential
good-timing stocks would have produced positive returns under simple execution
rules. This is still research verification, not investment advice.

Command:

```bash
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python /Users/xudoulei/work/tech-growth-stock-screener/scripts/run.py operation-backtest --source cache --backtest-date 2026-05-25
```

Selection rules:

- The signal date uses `--backtest-date`, falling back to `--as-of-date`.
- The dashboard signal flow reruns for the signal date before future quotes are
  read.
- Only `操作建议` rows with macro potential `>= 80`, technical timing `>= 75`,
  `usable_for_plan=True`, and executable plan strategies are simulated.
- Executable strategies are `breakout_buy`, `pullback_ma_buy`, and
  `volume_confirm_buy`. `观察` and `暂不交易` rows are not bought.

Execution rules:

- Buy checks start on the first trading day after the signal date.
- `breakout_buy`: buy at `planned_entry` if the day's high reaches that price.
- `pullback_ma_buy`: buy at `planned_entry` if the day's low/high range touches
  that price.
- `volume_confirm_buy`: buy at `planned_entry` if the day's high reaches that
  price and amount meets `volume_confirm_amount` when that threshold exists.
- A-share T+1 is enforced: after a buy is triggered, target/stop checks start
  on the next trading day. The buy date itself is never used as an exit date.
- Profit target defaults to `5%`, configurable by `--operation-profit-target`.
- Stop loss uses `initial_stop`.
- If stop and target are both touched on the same day, the simulation treats the
  stop as hit first to avoid overstating returns without intraday order data.
  This same-day collision rule applies only on sell-eligible trading days after
  the T+1 holding constraint is satisfied.
- If neither target nor stop is touched before the latest cached quote, the row
  exits at the latest close with status `持有至截止日`.
- If no buy trigger occurs, the row is `未触发` and is not included in traded
  return averages.

Dashboard presentation:

- Show one `操作回测` section below fixed-horizon `数据回测` when operation
  backtest data exists.
- Show operation sample count, successful buys, untriggered rows, take-profit
  exits, stop-loss exits, open holds, traded win rate, realized average return,
  and average return including open holds.
- The detail table shows each row's action, buy/sell dates and prices, exit
  reason, return, and status.
- Clicking or hovering a row shows the operation path with planned entry,
  initial stop, 5% target, and daily high/low/close points used by the
  simulation.

### 信号有效性验证

Purpose: diagnose whether the scoring signal itself has predictive value before
changing score formulas or operation-advice rules.

Command:

```bash
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python /Users/xudoulei/work/tech-growth-stock-screener/scripts/run.py signal-validate --source cache --backtest-date 2026-05-01
```

For multiple sampled signal dates, use `--validation-start`, `--validation-end`,
and `--validation-step-days`.

Validation rules:

- Each signal date reruns the serial dashboard flow using only data available
  at that date.
- All dashboard candidates are classified into matrix quadrants using the same
  thresholds as the dashboard: macro potential `>= 80` and technical timing
  `>= 75`.
- All candidates are also sorted by `attention_score` and grouped into
  rank buckets such as `Top 1-10`, `Top 11-20`, and so on. `--bucket-size`
  controls bucket width.
- Return rules match fixed-horizon signal backtests: next trading day's open
  to the N-th future trading day's close.
- Statistics aggregate complete rows only and include sample count, average
  return, median return, win rate, max return, and min return.

This command validates scoring signal quality. It does not simulate
operation-advice triggers such as planned entry, stop loss, or take-profit
execution.

Dashboard presentation:

- When the dashboard model contains `signal_validation`, show one
  `信号验证与预警` section under `数据回测`.
- The section has holding-period tabs using the validation `holding_days`.
- The overview shows sample count, `好时机+高潜力` average return, excess return
  versus `其他象限`, and `象限失效预警`.
- `象限失效预警` must treat small samples conservatively. If the
  `好时机+高潜力` complete sample count is below 5 for the selected holding
  period, show `样本不足` and do not mark the quadrant as failed.
- `排序有效性预警` is separate from quadrant validation. It compares
  `Top 1-10` against `Top 11-20`; if either bucket has fewer than 5 complete
  samples, show `样本不足`, otherwise trigger only when `Top 1-10` does not
  outperform `Top 11-20`.
- Failure warnings require at least 3 sampled signal dates. If the selected
  validation model has fewer than 3 signal dates, underperformance is shown as
  `单日观察` with warning styling instead of red `触发`.
- The quadrant heatmap shows sample count, average return, median return, and
  win rate for each matrix quadrant.
- The attention-score bucket bars show average return and win rate for buckets
  such as `Top 1-10`, `Top 11-20`.
- A warning is visual only. It must not change score formulas, candidate order,
  or operation-advice rules.

### 数据健康审计

The dashboard model includes `summary.health`, and the CLI exposes the same
audit through `validate-dashboard`.

The audit checks:

- Stage counts for `股票池 -> 宏观粗筛 -> 技术分析 -> 操作建议`.
- Serial-stage integrity: combo rows must come from stock pool, fine rows from
  combo, and plan rows from fine.
- Stock-pool quote metric coverage for `amount_20d`, `return_60d`, and
  `max_drawdown_252d`.
- Operation-advice daily-quote coverage, usable plan count, and complete rows
  missing `planned_entry` or `initial_stop`.
- Latest trade date from technical and plan rows; `validate-dashboard` can also
  compare it with `--expected-latest-trade-date`.
- Score ranges for known 0-100 score fields.

The dashboard health strip displays the audit summary only. It must not alter
screening scores, candidate order, or operation-advice rules.

The same strip also displays global strategy context for the whole dashboard
run, not for the currently selected stock:

- `策略口径`: `summary.strategy_title`, currently `潜力股组合评分`.
- `权重版本`: `summary.weight_version`, derived from market regime.
- `权重版本` hover title: `summary.weight_version_note`.

Weight-version labels:

- `牛市动量版`: 更重视动量和价格强势。
- `震荡防御版`: 更重视质量、风控、反转，弱化动量。
- `熊市防御版`: 质量和风控权重最高，动量不参与总分。

## When Rules Change

If a calculation, display unit, stage dependency, or stage field contract
changes, update this file in the same change and add a short note to
`docs/decisions.md`.

## 2026-07-13: 市场状态过滤器

### 市场状态判定

Dashboard pipeline 在 stock-pool 阶段完成后、combo 阶段前运行 `dashboard.market_state.detect()`：

- 输入：股票池候选股的全部 6 位代码 + 可选的 `as_of_date` 截断日期
- 输出：`MarketState` 数据类，包含 label/regime（`bull`、`transition`、`bear`）、中位指标、市场宽度、投票数、仓位乘数、说明文字

判定逻辑：对每只股票取最近 20/30 个交易日均线，计算 close/MA20、close/MA30、MA20 近 6 日斜率，并取有效股票样本的中位数。

- 样本中位 close/MA30 > 1.0 → 1 张牛市票
- 样本宽度（close/MA20 > 1 的股票占比）> 60% → 1 张牛市票
- 样本中位 MA20 斜率 > 0 → 1 张牛市票
- 3/3 → **牛市**（bull）
- 1/3 或 2/3 → **震荡市**（transition）
- 0/3 → **熊市**（bear）
- 无候选股、缺少日线或有效样本不足时，默认 bull，以避免离线缓存不完整时误触发防御。

### 不同市场状态下的行为

市场状态会传入 combo 阶段重新计算动量和 `combo_score`：

- `bull`：提高趋势动量权重，`momentum_score = trend 70% + reversion 30%`，总分中 momentum 权重 20%。
- `transition`：降低动量总权重，偏向质量和反转，`momentum_score = trend 30% + reversion 70%`，总分中 momentum 权重 3.2%。
- `bear`：动量展示为反转分，但总分 momentum 权重为 0；质量和风控权重提高。

非 bull 状态还会修改 `args.max_position`：
- `transition` 且 2 张牛市票：原始 max_position × 0.85
- `transition` 且 1 张牛市票：原始 max_position × 0.60
- `bear`：原始 max_position × 0.60

`_score_position_cap()` 读取的是修改后的仓位上限。操作建议字段本身不新增个人预算/配置类字段。

### 看板展示

`model["summary"]["market_state"]` 字段包含：
- `label`/`regime`：`"bull"`、`"transition"` 或 `"bear"`
- `median_close_vs_ma20`：中位比率（可能为 null）
- `median_ma20_slope`：中位斜率（可能为 null）
- `breadth_pct`：样本宽度（close/MA20 > 1 的股票占比，可能为 null）
- `bull_votes`：牛市投票数（0-3）
- `sample_count`：有效样本数
- `position_multiplier`：仓位乘数
- `note`：人类可读的说明

Dashboard summary also exposes the scoring context used by the health strip:

- `strategy_title`: `潜力股组合评分`
- `strategy_key`: `combo`
- `combo_strategies`: configured coarse strategy labels
- `weight_version`: `牛市动量版`, `震荡防御版`, or `熊市防御版`
- `weight_version_note`: hover explanation for the selected version

## 2026-07-13: 行业中性化

quality_score 和 risk_control_score 的 rank 操作从全局改为行业内：

```
quality_score = (
    within_industry_rank(ROE) × 0.45
  + within_industry_rank(gross_margin) × 0.30
  + PE_合理度(全局) × 0.25
) × 100

risk_control_score = (
    within_industry_rank(|max_drawdown_252d|, ascending=False) × 0.70
  + rank_high(amount_20d, 全局) × 0.30
) × 100
```

行业分组：按 `board_name` 分组，每组 < 5 只股票合并为「其他」组。

其他评分（growth、liquidity、momentum、overlap）保持全局 rank 不变。

## 2026-07-13: 动态矩阵阈值

矩阵象限阈值从固定值改为自适应：

- `macro_potential_threshold`：combo_score 的 70 分位（样本 ≥ 15），否则默认 80
- `technical_timing_threshold`：technical_score 的 65 分位（样本 ≥ 15），否则默认 75

阈值通过 `model["summary"]["adaptive_thresholds"]` 暴露。前端、signal_backtest、operation_backtest 均使用动态阈值。未传入时降级到模块级默认常量。

## 2026-07-15: PEG 因子与动量/反转拆分（濮元恺《量化投资技术分析实战》优化）

### quality_score PEG 计算

`revenue_yoy`/`profit_yoy` 在不同源中可能是 `20.0` 这种百分数，也可能是 `0.20` 这种小数比例。PEG 计算先取两者正值均值；若均值 `<= 1.0`，按小数比例乘以 100，否则按百分数原样使用。

PEG = PE / max(growth_pct, 1)。得分映射：
- PEG < 0.5 → 深度低估 → 1.0
- PEG 0.5-1.0 → 合理偏低估 → 0.85~1.0
- PEG 1.0-2.0 → 合理偏贵 → 0.40~0.85
- PEG > 2.0 或 PE ≤ 0 → 0.0~0.40

### momentum_score 反转信号

mean_reversion_score 仅在 revenue_yoy > 0 且 profit_yoy > 0 时激活，并由年内回撤分乘以 60 日收益因子：
- |max_drawdown_252d| > 25% → 1.0
- 15%-25% → 0.5~0.8
- 10%-15% → 0.2~0.5
- < 10% → 0.0

60 日收益因子用于避免把已经大幅反弹的股票误当成反转候选：
- return_60d <= 0：因子 0.6~1.0，跌幅越深越接近 1.0
- return_60d > 0：因子 0.2~0.5，涨幅越大惩罚越强

### technical_score 技术分调整

技术分 =
  趋势分 * 28
  + 动量分 * 22
  + 量能分 * 22
  + 突破分 * 15
  + 风险分 * 8
  + 流动性分 * 5

量能分细化：
- 放量阳线（量比≥1.2 且收阳）：35%
- 显著放量阳线（量比≥1.5 且收阳）：20%
- 当日上涨：25%
- 量价配合（量比>1, 涨, 收盘上半区）：10%
- 流动性达标：10%

MACD 信号细化：
- MACD 柱正值且在加速扩大：20%
- MACD 柱正值但在缩小：8%
- MACD 金叉（柱值从非正转正）：7%

突破分筹码集中度：
- 近 5 日量 / 近 20 日量 ≥ 35%：1.0
- 25%-35%：0.5
- < 25%：0.0

风险分换手率稳定性：
- turnover_stability = 1 - CV(20日换手率)，CV 越小越稳定
- ≥ 0.7：稳健机构持仓特征 → 0.30
- 0.4-0.7：中等 → 0.15
