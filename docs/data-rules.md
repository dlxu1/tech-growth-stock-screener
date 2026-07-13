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
  pool unless another universe is explicitly selected.
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
宏观粗筛分 =
  多策略共振分 * 35%
  + 成长分 * 20%
  + 质量分 * 18%
  + 风控分 * 15%
  + 流动性分 * 7%
  + 动量分 * 5%
```

Component meanings:

- `overlap_score`: matched strategy weight / total strategy weight * 100.
- `growth_score`: percentile rank of positive revenue YoY plus positive profit YoY.
- `quality_score`: ROE rank * 45% + gross margin rank * 30% + PE reasonableness * 25%.
- `risk_control_score`: low absolute max drawdown rank * 70% + amount rank * 30%.
- `liquidity_score`: 20-day amount percentile rank * 100.
- `momentum_score`: 60-day return percentile rank * 100.

Dashboard presentation:

- Main columns: `code`, `name`, `market_cap`, `combo_score`, `growth_score`,
  `quality_score`, `risk_control_score`, `strategy_summary`.
- `strategy_summary` shows only the number of hit strategies.
- Hover title for `strategy_summary` shows the specific matched strategies.
- Scores and numeric values should keep two decimals.

### 技术分析

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
- `latest_close`
- `planned_entry`
- `initial_stop`
- `risk_pct`
- `take_profit_1r`
- `take_profit_2r`
- `plan_note`

Keep language conservative: use `观察`, `条件买入`, `等待回踩`, `等待放量确认`,
or `暂不交易`, and include risk/data limitations when relevant.

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
the date must rerun the serial dashboard flow and rebuild all matrix scores from
the selected date's available cached data.
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

## When Rules Change

If a calculation, display unit, stage dependency, or stage field contract
changes, update this file in the same change and add a short note to
`docs/decisions.md`.

## 2026-07-13: 市场状态过滤器

### 市场状态判定

Dashboard pipeline 在 fine 阶段完成后自动运行 `detect_market_state()`：

- 输入：fine 候选股的全部 6 位代码 + 可选的 `as_of_date` 截断日期
- 输出：`MarketState` 数据类，包含 label（normal/defensive）、中位指标、仓位乘数（1.0 或 0.60）、说明文字

判定逻辑：对每只股票取最近 20 个交易日的 MA20，计算 close/MA20 比率和 MA20 近 6 日斜率。取所有有效股票的中位数。

- 中位 close/MA20 > 1.0 且中位 MA20 斜率 > 0 → **正常模式**（NORMAL）
- 任一条件不满足 → **防御模式**（DEFENSIVE）
- 有效样本不足（< 1 只股票有完整 20 日数据）→ 默认正常模式

### 防御模式下的行为

防御模式通过修改 `args.max_position` 生效：
- 原始 max_position（默认 0.25）× 0.60 = 0.15
- `_score_position_cap()` 读取的是修改后的值，因此：
  - 技术分 ≥ 85：仓位上限从 25% 降至 15%
  - 技术分 ≥ 75：仓位上限从 min(25%, 20%) 降至 min(15%, 20%) = 15%
  - 技术分 ≥ 60：仓位上限从 min(25%, 12%) 降至 min(15%, 12%) = 12%

不修改评分公式、不改变候选股排序、不改变操作建议的策略分派逻辑。

### 看板展示

`model["summary"]["market_state"]` 字段包含：
- `label`：`"normal"` 或 `"defensive"`
- `median_close_vs_ma20`：中位比率（可能为 null）
- `median_ma20_slope`：中位斜率（可能为 null）
- `sample_count`：有效样本数
- `position_multiplier`：仓位乘数
- `note`：人类可读的说明

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
