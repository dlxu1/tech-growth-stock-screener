# Handoff

Use this file as the first stop when a new thread needs to continue work.

## Current Known State

- The project has a CodeGraph index at `.codegraph/`.
- The dashboard flow is serial: `sector_screen -> combo -> fine -> plan`,
  displayed as `股票池 -> 宏观粗筛 -> 技术分析 -> 操作建议`.
- Latest dashboard output path:

```text
.cache/reports/dashboard_latest.html
```

- Current visible dashboard refinements:
  - `组合评分` wording has been changed to `宏观粗筛`.
  - `板块筛选` is displayed as `股票池`; the table includes `股票类型`, and hover
    text shows the matched keyword and board-name classification basis.
  - Stock-type classification is configurable through `configs/stock_type_rules.json`
    or `--stock-type-config`. `--stock-types` filters which classified types
    enter downstream dashboard stages while keeping the full stock pool visible.
  - Macro coarse table uses Chinese headers and score help hover buttons.
  - Dashboard macro coarse keeps up to 100 stocks from the stock pool.
  - Macro coarse table formats market cap as `xx.xx亿`.
  - Macro coarse `策略命中` shows only hit count; specific strategies appear on hover.
  - Sector screen removes `匹配理由` from the main table and keeps detailed `数据说明`.
  - Technical fine screen is displayed as `技术分析`, receives all macro coarse
    rows, formats ratio fields as percentages, numeric fields to two decimals,
    and hides `coarse_strategies`.
  - Operation advice shows next-session plan fields only, has no budget/allocation
    fields, and now generates plan data for the full technical-analysis result.
    The matrix uses point size for combined attention and does not add a top-5
    black-ring highlight.
  - Dashboard landing view now emphasizes `宏观潜力 × 技术时机`: a large
    potential-timing matrix fills the left side, and a selected-stock
    explanation panel sits on the right. The matrix includes macro coarse plus
    technical analysis stocks, point size reflects combined attention score,
    includes a local stock search box and stock-type filter chips, and clicking
    a point updates the right-side stock introduction. The quadrant lines match
    the color thresholds: macro potential `>= 80` and technical timing `>= 75`.
  - Dashboard models now include `summary.health`, and the HTML shows a compact
    data-health strip above the matrix. Use `validate-dashboard` to print the
    same audit from the CLI.
  - The separate candidate-priority list has been removed from the current UI.

## Standard Verification

Run these after code changes:

```bash
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest discover -s tests
git diff --check
codegraph sync
```

Run this after dashboard renderer or pipeline changes:

```bash
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python /Users/xudoulei/work/tech-growth-stock-screener/scripts/run.py dashboard --source cache --output /Users/xudoulei/work/tech-growth-stock-screener/.cache/reports/dashboard_latest.html
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python /Users/xudoulei/work/tech-growth-stock-screener/scripts/run.py validate-dashboard --source cache
```

Focused dashboard checks:

```bash
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest tests.test_dashboard_html
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest tests.test_dashboard_pipeline
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest tests.test_dashboard_view_model
```

## New Thread Prompt

To resume this project in a fresh thread, use:

```text
继续 tech-growth-stock-screener 项目。请先读 AGENTS.md、docs/project-context.md、docs/data-rules.md、docs/decisions.md、docs/handoff.md，并用 CodeGraph 理解相关代码后再操作。
```

## Maintenance Rule

When a new durable decision is made, update:

- `docs/decisions.md` for the decision and reason.
- `docs/data-rules.md` if data contracts, scores, units, or formatting changed.
- `docs/handoff.md` if the next thread should know the latest state or command.
