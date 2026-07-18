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
  - Dashboard-oriented commands now default to the cached CSI 300 universe. The
    historical date form preserves universe, index symbol, sector, and
    stock-type filters when recalculating.
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
  - The potential-timing matrix includes a `历史日期重算` date selector. It is
    useful through `dashboard-server`; choosing a date reloads
    `/dashboard?as_of_date=YYYY-MM-DD`. A matching `dashboard_snapshots` model
    can be reused directly; otherwise the full serial flow reruns using cached
    daily quotes up to that date.
  - `recent_high_good_hits` is enabled by default again. Current `好时机+高潜力`
    matrix stocks count how many available signal dates in the previous 30
    calendar days also landed in `好时机+高潜力`. Each historical date uses its
    own adaptive thresholds. Counts of 4 or more show a special matrix
    ring/badge and hover dates, plus a note in the right-side stock detail
    panel. The expensive repeated-hit path now first aggregates
    `dashboard_matrix_signals`, then hydrates missing dates from matching
    `dashboard_snapshots`, and only recalculates still-missing dates. Use
    `--no-recent-high-good-hits` to temporarily disable the annotation. The
    dashboard server also keeps identical URL responses in
    memory while that database fingerprint is unchanged, so refreshing the same
    date should avoid the 20+ historical reruns.
  - If the requested historical date is earlier than every cached CSI 300
    constituent snapshot, replay falls back to the latest cached constituent
    snapshot while still cutting off quotes/report dates by `as_of_date`.
  - In cache mode, if the selected historical date points to report periods that
    are not cached, replay falls back to the latest cached financial-report
    source table and lets the data-health strip report any quote coverage gaps.
  - When `--as-of-date` is present, dashboard models also include a `数据回测`
    section. It tests three single-date signal groups: `宏观潜力 Top10`,
    `技术分 Top10`, and `综合关注 Top10`, using next-trading-day open to 7/14/21
    trading-day close returns. `--backtest-date` and the page-level回测信号日
    selector can choose a backtest signal date independently from the matrix
    `as_of_date`.
  - Dashboard models now include `operation_backtest` when a signal date is
    available. The HTML shows `操作回测` below fixed-horizon `数据回测`, simulating
    high-potential+good-timing executable `操作建议` rows with planned-entry
    triggers, A-share T+1 exits, 5% default profit target, initial-stop exits,
    and held-to-latest close fallback. Buy-day target/stop touches are ignored
    for exits; selling starts on the next trading day.
  - `signal-validate` validates score-signal quality across one or more
    historical signal dates. It aggregates all candidates by matrix quadrant
    and attention-score rank buckets using the same fixed next-open to
    N-day-close return rule. It intentionally does not simulate operation-plan
    triggers yet.
  - When dashboard models include signal validation, the HTML dashboard shows
    `信号验证与预警` below `数据回测`, with holding-period tabs, quadrant
    heatmap, attention-score bucket bars, and an `象限失效预警` status comparing
    `好时机+高潜力` against `其他象限`.
  - Signal warnings now have a small-sample guard: fewer than 5 complete
    `好时机+高潜力` rows shows `样本不足` instead of a failure trigger. Ranking
    validation is a separate `排序有效性预警` comparing `Top 1-10` with
    `Top 11-20`. Red `触发` now also requires at least 3 sampled signal dates;
    underperformance from one or two signal dates is shown as yellow
    `单日观察`.
  - The separate candidate-priority list has been removed from the current UI.
  - Data updates now default to incremental daily-price sync. `sync --dataset
    daily_prices` and internal `sync_dataset(..., dataset="daily_prices")` pass
    `skip_existing=True` unless explicitly overridden, so cached symbols are
    skipped and partially cached symbols fetch only the missing tail. Use
    `--no-skip-existing`, `--refresh`, or `--update-policy refresh` only for an
    intentional full repair/rebuild.
  - Financial-report `--report-date auto` now prefers the latest complete-looking
    cached/fetched `stock_yjbb_YYYYMMDD` table and avoids using an obviously
    incomplete fresh quarter when an older complete report is available.
  - Dashboard now has a fifth data-generation node after `操作建议`: the complete
    dashboard model is persisted to `dashboard_snapshots`. `dashboard`,
    `dashboard-server`, and `validate-dashboard` default to `--dashboard-cache`
    and can reuse a matching snapshot when dashboard parameters and source-data
    fingerprints are unchanged. Use `--no-dashboard-cache` to bypass reuse or
    `--rebuild-dashboard-cache` to rerun and replace the matching snapshot.
  - A derived matrix-signal cache now lives in `dashboard_matrix_signals`.
    Cache-enabled dashboard runs materialize one row per matrix candidate per
    signal date. `recent_high_good_hits` is enabled by default and aggregates
    this table first, hydrates missing signal dates from `dashboard_snapshots`,
    and only recalculates dates still missing from both caches. The measured
    2026-07-09 case dropped from about 113 seconds on first repeated-hit
    calculation to about 13 seconds when forcing the current date rebuild, and
    about 1 second when the full dashboard snapshot is reused.

## Standard Verification

Run these after code changes:

```bash
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest discover -s tests
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest tests.test_incremental_sync
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest tests.test_dashboard_pipeline
git diff --check
codegraph sync
```

Run this after dashboard renderer or pipeline changes:

```bash
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python /Users/xudoulei/work/tech-growth-stock-screener/scripts/run.py dashboard --source cache --output /Users/xudoulei/work/tech-growth-stock-screener/.cache/reports/dashboard_latest.html
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python /Users/xudoulei/work/tech-growth-stock-screener/scripts/run.py validate-dashboard --source cache
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python /Users/xudoulei/work/tech-growth-stock-screener/scripts/run.py signal-backtest --source cache --backtest-date 2026-06-30 --format markdown
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python /Users/xudoulei/work/tech-growth-stock-screener/scripts/run.py operation-backtest --source cache --backtest-date 2026-05-25 --format markdown
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python /Users/xudoulei/work/tech-growth-stock-screener/scripts/run.py signal-validate --source cache --backtest-date 2026-05-01 --format markdown
```

Run the local historical matrix dashboard:

```bash
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python /Users/xudoulei/work/tech-growth-stock-screener/scripts/run.py dashboard-server --source cache --host 127.0.0.1 --port 5001
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

## 2026-07-13: 策略分析文档沉淀

- 新增 `docs/strategy-analysis.md`：完整梳理了 combo_score、technical_score、attention_score 的计算公式、各子分判定规则、操作建议生成规则、信号验证与预警机制，以及「好时机+高潜力是否安全」的核心判断和局限性分析。
- Dashboard server 在 `http://127.0.0.1:5001/dashboard?as_of_date=2026-06-30&backtest_date=2026-06-30` 运行中，四个模块（数据回测、操作回测、信号验证与预警、宏观潜力×技术时机矩阵）均正常展示。
- 数据健康度 100/100，最新行情日 2026-06-30。

## 2026-07-13 (续): 策略优化分析

- 基于 2025-12-31 至 2026-06-30 共 6 个信号日回测数据，发现：
  1. 评分信号在 7 日窗口单调性弱，14-21 日窗口显著增强
  2. 「高潜力+等时机」(纯宏观高分) 在 2026-03-31 大幅跑赢所有其他象限
  3. 2026-06-30 评分完全反向——高分股在科技股回调中跌幅最大
  4. 固定阈值 80/75 在不同市场状态下表现差异极大
- `docs/strategy-analysis.md` 新增第九章「基于历史回测数据的优化建议」，含 5 条具体优化方案和 4 阶段迭代路线图。
- 最高优先级建议：市场状态过滤器（防御/正常两档，影响仓位上限），改动量小、风险可控。
