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

- 新增 dashboardv2 输出路径：

```text
.cache/reports/dashboard_v2_latest.html
```

- Current visible dashboard refinements:
  - Dashboard-oriented commands now default to the cached CSI 300 universe. The
    historical date form preserves universe, index symbol, sector, and
    stock-type filters when recalculating.
  - `dashboard` v1 已合并行业主线证据板：页面先显示数据健康，再显示行业
    主线证据，然后进入原有 `宏观潜力 × 技术时机`、详情、回测和验证交互。
    未显式指定行业时，pipeline 会先计算行业主线榜并默认选中排名第一的行业；
    下方 `股票池 -> 宏观粗筛 -> 技术分析 -> 操作建议` 使用该行业股票池。
    行业全成分股优先来自 `industry_members`，不可用时透明降级为缓存样本代理。
  - `dashboardv2` 保留兼容入口和暂停更新提示，不再承接新增交互需求。v2
    快照仍通过 `dashboard_variant="v2"` 与 v1 隔离，v1 缺省快照 key 保持兼容。
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
  - NAS 部署文件已加入仓库：`Dockerfile`、`docker-compose.yml`、
    `.dockerignore`、`requirements.txt` 和 `docs/nas-docker-deploy.md`。
    推荐常驻运行 `dashboard-server --source cache --host 0.0.0.0 --port 5001`，
    通过 `nas-cache:/app/.cache` 持久化 SQLite 缓存、dashboard 快照和报表。
    NAS 浏览器入口为 `http://NAS_IP:5001/dashboard`。
  - `docs/nas-docker-deploy.md` 已补充 NAS cron 定时更新说明：如何判断
    cron 是否可用、查看/编辑当前用户和 root 的定时任务、配置工作日 17:00
    执行 `docker compose run --rm update`、理解 `update.log` 重定向，以及
    `/app/.cache/stock_data.sqlite` 到 NAS 主机 `nas-cache/stock_data.sqlite`
    的 Docker volume 映射关系。
  - 新增每日邮件日报流水线：`docker compose run --rm update-report` 会增量
    更新数据、重跑 dashboard、生成 `nas-cache/reports/daily_email_latest.txt`
    和主题/JSON 文件；`scripts/nas_update_and_mail.sh` 在 NAS 主机上调用
    `mail/msmtp` 发信，成功时发送健康度与最多 10 只 `好时机+高潜力` 股票的
    操作指南，失败时发送 `update.log` 最后 200 行。推荐 cron：
    `0 17 * * 1-5 MAIL_TO="your_email@example.com,team@example.com" /vol1/docker/tech-growth-stock-screener/scripts/nas_update_and_mail.sh`。
    `MAIL_TO` 支持逗号、空格或分号分隔多个邮箱；脚本会逐个发送，任一失败会
    记录日志并返回非零。
  - `好时机+高潜力` 候选股现在带有展示用投资周期字段：
    `horizon_tags`、`primary_horizon`、`horizon_reason` 和
    `horizon_data_note`。UI 文案为 `适合周期` 和 `优先关注`，显示在选中股票
    详情和操作建议表内，不放在顶部全局栏。分类规则只消费现有宏观、技术和
    操作计划字段，不改变评分、阈值、阶段成员或回测样本。
  - 顶部数据健康栏现在展示全局 `策略口径` 和 `权重版本`。`权重版本` hover
    会解释 `牛市动量版`、`震荡防御版` 或 `熊市防御版` 对应的权重含义。
  - 每日邮件中每只 `好时机+高潜力` 候选股现在包含 `适合周期`、`优先关注`
    和 `周期说明`，JSON payload 同步包含 horizon 字段；邮件不重新计算周期
    规则，只消费 dashboard model。
  - OpenSpec change `add-horizon-tags-to-high-potential-good-timing` 已创建，
    并已同步主 spec 到 `openspec/specs/dashboard/spec.md`。

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
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest tests.test_horizon_tags
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest tests.test_email_digest
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
