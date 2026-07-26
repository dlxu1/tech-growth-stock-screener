# Project Context

## Purpose

This project screens A-share technology stocks through a layered research flow,
then renders the result as Markdown/JSON/CSV or an offline interactive HTML
dashboard. It is used for research and辅助决策 only; it must not present output
as guaranteed returns or direct trading instructions.

## Current Main Workflow

The dashboard workflow is serial:

```text
股票池 -> 宏观粗筛 -> 技术分析 -> 操作建议
```

The important invariant is that each downstream stage must only operate on the
stocks selected by the immediately previous stage.

Current default dashboard output:

```text
.cache/reports/dashboard_latest.html
```

Dashboard-oriented commands default to the cached CSI 300 universe. Use
`--universe tech` only when the technology keyword pool is explicitly needed.
The v1 dashboard now inserts an industry-mainline evidence board between data
health and the existing decision surface, and uses the selected industry pool
for downstream macro/technical analysis when available. `dashboardv2` is kept
only as a paused compatibility entry.

## Key Modules

- `scripts/run.py`: CLI entry point.
- `scripts/dashboard/pipeline.py`: orchestrates the dashboard stage sequence.
- `scripts/dashboard/snapshot.py`: reads and writes complete dashboard model snapshots.
- `scripts/dashboard/stock_types.py`: loads configurable stock-type rules and annotates stock-pool rows.
- `scripts/dashboard/view_model.py`: normalizes stage DataFrames into JSON for the dashboard.
- `scripts/reports/dashboard_html.py`: renders the interactive offline dashboard.
- `scripts/strategies/sector_screen.py`: first-stage board/universe selection.
- `scripts/strategies/coarse/registry.py`: coarse strategies and combo scoring.
- `scripts/strategies/fine/technical.py`: technical fine-screen scoring.
- `scripts/allocation/personal_plan.py`: personal capital allocation overlay.

## Current Dashboard Expectations

- Stage titles should be Chinese:
  - `sector_screen`: `股票池`
  - `combo`: `宏观粗筛`
  - `fine`: `技术分析`
  - `plan`: `操作建议`
- The stock-pool table shows a `股票类型` column. Classification is loaded from
  `configs/stock_type_rules.json` by default or from `--stock-type-config`, and
  hover text explains the matched keyword and board-name basis.
- `--stock-types` can limit which classified stock types enter downstream
  dashboard stages. The full classified stock pool remains visible for audit.
- The macro coarse screen shows up to 100 fundamentally stronger stocks from the
  stock-pool result.
- The technical analysis screen runs on all macro coarse stocks, up to 100 rows.
- The operation advice screen is generated for the full technical fine-screen
  result, which covers all macro coarse stocks, and shows next-session
  rule-based plan fields only. Dashboard operation advice does not include
  personal budget or allocation fields.
- The dashboard landing view focuses on a large `宏观潜力 × 技术时机` matrix and a
  right-side stock detail panel. Macro/coarse scores explain why a stock is
  worth tracking, technical scores explain whether the current window is close.
  The matrix includes both macro coarse and technical analysis stocks, point
  size reflects the combined attention score, and clicking a point updates the
  right-side stock introduction. The separate candidate-priority list is hidden
  from the current UI. The matrix has its own search box for quickly filtering
  the currently displayed matrix stocks by code, name, board, action, reason, or
  stock type. It also has local stock-type chips for quickly filtering the matrix
  without rerunning the pipeline. Full stage tables remain available below the
  candidate overview.
- The v1 dashboard now places an `行业主线证据板` under the data-health strip
  and above the main matrix. The board defaults to the top-ranked industry and
  clearly labels the current pool as industry full constituents or a degraded
  sample pool. When a selected industry is available, downstream stages use
  that industry's stock pool instead of the default CSI 300-only pool.
- The matrix includes a historical date selector. In `dashboard-server` mode,
  changing the date reloads the dashboard with `as_of_date`. A matching
  `dashboard_snapshots` entry may be reused directly; otherwise the full serial
  flow reruns using cached daily quotes up to that date while preserving the
  current universe/filter parameters. Static HTML can also be generated for a
  fixed historical date with `--as-of-date`.
- `recent_high_good_hits` is displayed by default for current `好时机+高潜力`
  stocks. It counts how many available signal dates in the previous 30 calendar
  days also landed in `好时机+高潜力`, using each historical date's own adaptive
  matrix thresholds. The calculation is display-only and must not change scores,
  thresholds, stage membership, backtest samples, or operation advice. To keep
  historical date switching fast, dashboard models materialize lightweight
  matrix rows into `dashboard_matrix_signals`; the repeated-hit annotation first
  aggregates that table, then hydrates missing dates from matching
  `dashboard_snapshots`, and only recalculates dates still missing from both.
  Use `--no-recent-high-good-hits` only as a temporary diagnostic bypass.
- When signal-validation data is present, the dashboard shows a `信号验证与预警`
  section under `数据回测`. It visualizes the selected signal date's matrix
  quadrant performance and attention-score bucket performance across holding
  horizons, and flags whether `好时机+高潜力` is underperforming `其他象限`.
- When operation-backtest data is present, the dashboard shows an `操作回测`
  section below fixed-horizon `数据回测`. It simulates executable operation
  plans for `好时机+高潜力` stocks with planned-entry triggers, A-share T+1
  sell eligibility, a default 5% profit target, initial-stop exits, and
  held-to-latest-close fallback.
- Table headers should use Chinese labels where known.
- Score headers should include an `i` help button when calculation help exists.
- The dashboard is a static local HTML file. After renderer changes, regenerate it.

## User Preferences Captured In This Project

- Prefer direct implementation over abstract proposals when the request is clear.
- Keep explanations concise and in Chinese.
- For UI/dashboard work, polish the actual current HTML output, not a landing page.
- Data tables should be readable: currency in `亿`, percentages with `%`, scores/numbers usually two decimals.
