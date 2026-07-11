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

## Key Modules

- `scripts/run.py`: CLI entry point.
- `scripts/dashboard/pipeline.py`: orchestrates the dashboard stage sequence.
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
- The stock-pool table shows a `股票类型` column, with hover text explaining
  the board-name rule used for classification.
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
  the currently displayed matrix stocks by code, name, board, action, or reason.
  Full stage tables remain available below the candidate overview.
- Table headers should use Chinese labels where known.
- Score headers should include an `i` help button when calculation help exists.
- The dashboard is a static local HTML file. After renderer changes, regenerate it.

## User Preferences Captured In This Project

- Prefer direct implementation over abstract proposals when the request is clear.
- Keep explanations concise and in Chinese.
- For UI/dashboard work, polish the actual current HTML output, not a landing page.
- Data tables should be readable: currency in `亿`, percentages with `%`, scores/numbers usually two decimals.
