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

- `stock_type`: classify by `board_name`, such as `科技股`, `周期股`, `金融股`,
  `消费/防御`, or `未分类`; hover title uses `stock_type_note` to show the
  matched board-name basis.
- `market_cap`: divide by `100000000`, keep two decimals, append `亿`.
- `amount_20d`: divide by `100000000`, keep two decimals, append `亿`.
- `revenue_yoy`, `profit_yoy`, `return_60d`, `max_drawdown_252d`: keep two decimals and append `%`.
- Hide `match_reason` from the main dashboard table.
- Keep `data_note` detailed enough to explain missing fields and data limitations.

### 宏观粗筛

Purpose: rank the previous stage's stocks with a multi-strategy coarse score.
It must not pull from the full base universe when the dashboard flow is serial.
The dashboard keeps up to 100 rows for the next stage.

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
