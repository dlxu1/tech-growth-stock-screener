# Decisions

This file records durable project decisions so a new thread can continue the
work without replaying the whole conversation.

## 2026-07-11: Dashboard Flow Is Serial

Decision: the dashboard stage flow is:

```text
股票池 -> 宏观粗筛 -> 技术分析 -> 操作建议
```

Reason: each later stage should refine the previous stage's result, not restart
from the full universe. This keeps the displayed workflow aligned with the
user's mental model and makes counts/data easier to audit.

Implication: when modifying `scripts/dashboard/pipeline.py` or coarse/fine/plan
entry points, verify that downstream stages receive upstream candidates.

## 2026-07-11: 操作建议 Is Plan-Only In Dashboard

Decision: the dashboard shows one `操作建议` stage instead of separate `操作计划`
and `个人配置` tabs, and this stage is generated from the technical fine-screen
result as a rule-based next-session plan only. It does not include personal
budget or allocation fields.

Reason: the user wants the action recommendation for the stocks that survived
technical fine screening, and currently wants to focus on stock-screening logic
instead of account-budget configuration.

Implication: the dashboard plan stage must consume the current fine-screen
result. Do not display or derive `portfolio_action`, `budget_status`,
`lot_cost`, `allocation_note`, or other budget-related fields in the dashboard.

## 2026-07-11: 股票池 Is Pure Universe Selection

Decision: `sector-screen` is displayed as `股票池` and should not invent a board
score. It filters and annotates a matched universe, with market cap used as a
stable display order when capping results. The dashboard adds a `股票类型` label
from `board_name`, with hover text explaining the classification basis.

Reason: the first stage is meant to show "which stocks are in the chosen board
or tech universe", not rank investability.

Implication: prefer `match_reason`, `risk_flags`, and detailed `data_note` over
score fields in the first dashboard table.

## 2026-07-11: 股票类型规则配置化

Decision: dashboard stock-type classification is loaded from
`configs/stock_type_rules.json` by default, with `--stock-type-config` available
for custom JSON rules. `--stock-types` filters which classified stock types enter
the downstream dashboard stages. The original stock-pool stage remains visible
as the full classified universe.

Reason: the user needs to freely configure stock-pool types such as technology,
cyclical, finance, defensive, or custom groups without changing Python code.
Keeping the full classified stock pool visible preserves auditability while
allowing the research flow to narrow the candidates passed to macro screening.

Implication: stock-type matching should remain a traceable board-name keyword
rule with `stock_type_note` explaining the matched keyword. Do not silently
change score formulas when changing type rules.

## 2026-07-11: 宏观粗筛 Defaults To Top 100 In Dashboard

Decision: dashboard macro coarse output should show up to the top 100 ranked
stocks, selected from the stock-pool result.

Reason: the user wants the full first-stage stock pool to remain available for
macro comparison, technical analysis, and operation-advice generation.

Implication: tests should protect the expected count and the subset
relationship from sector screen to macro coarse.

## 2026-07-11: 技术分析 Runs On All Macro Coarse Rows

Decision: the dashboard technical stage is displayed as `技术分析` and receives
all macro coarse rows, up to 100. Operation advice then generates rule-based
plans for the full technical-analysis result. The matrix uses point size for
combined attention and does not add a separate top-5 outline highlight.

Reason: macro screening answers whether a stock is worth following; technical
analysis answers whether the current timing is usable. The user wants every
macro-selected stock to receive an operation-advice data row, while the UI can
still emphasize the highest-priority names.

Implication: do not cap technical analysis or dashboard operation-advice data to
five rows. Keep any five-name cap in visual emphasis only, not in the plan data
contract.

## 2026-07-11: Table Formatting Happens In Dashboard Renderer

Decision: display-only formatting such as `亿`, two decimals, and `%` is handled
in `scripts/reports/dashboard_html.py`.

Reason: the dashboard should preserve raw JSON values for sorting/debugging
while presenting human-readable table cells.

Implication: avoid changing calculation functions just to alter display units.

## 2026-07-11: Strategy Hits Are Compact In 宏观粗筛

Decision: macro coarse table shows only the number of hit strategies in the
visible `策略命中` column. The specific strategy names are shown on hover.

Reason: showing both count and names as separate columns was redundant and made
the table harder to scan.

Implication: keep `matched_strategies` in row data for title/trace/debug use,
but do not make it a main visible macro coarse column.

## 2026-07-11: 技术细筛 Hides Coarse Strategy Names

Decision: the dashboard technical fine-screen table hides `coarse_strategies`.

Reason: the fine-screen page should focus on technical metrics after the macro
stage has already selected candidates.

Implication: do not remove the underlying field unless the data contract changes;
only hide it from the dashboard table.

## 2026-07-11: Dashboard Landing View Uses 潜力-时机 Matrix

Decision: the dashboard landing view should lead with a large `宏观潜力 × 技术时机`
matrix and a selected-stock explanation panel. The separate candidate-priority
list is removed from the current UI. The complete stage tables remain in the
HTML but are hidden by default.

Reason: "潜力大" should primarily come from macro/coarse screening, while
technical fine screening should explain timing and risk-control quality. This
separates "is it worth tracking" from "is the current window suitable".

Implication: keep `combo_score`/macro components visible in candidate
explanations and matrix x-axis, keep `technical_score`/technical signals on the
y-axis and timing explanation, and avoid presenting technical strength alone as
long-term potential.

## 2026-07-11: Matrix Shows Coarse And Technical Universe

Decision: the `潜力-时机矩阵` includes both macro coarse and technical-analysis
stocks. Point size reflects combined attention score, without an extra black
ring or outline for operation-advice picks. The matrix quadrant lines use the
same thresholds as point colors: macro potential `>= 80` and technical timing
`>= 75`.

Reason: the user wants to see both the macro-selected universe and the technical
analysis outcome in one decision surface, not only the final five advice rows.

Implication: the frontend should merge rows by code across stock pool, macro
coarse, technical analysis, and operation advice before drawing the matrix.
Clicking a matrix point should update the right-side stock detail panel. Do not
use 50/50 visual quadrant lines unless the color-classification thresholds also
change.

## 2026-07-11: Dashboard Carries Data Health Audit

Decision: the dashboard model includes a `summary.health` audit, and
`scripts/run.py validate-dashboard` exposes the same checks as Markdown or JSON.
The HTML dashboard shows a compact data-health strip above the matrix.

Reason: the user needs to know whether the current output is trustworthy before
reasoning about stock candidates. A separate audit keeps data-quality concerns
visible without changing screening formulas.

Implication: data-health checks must remain diagnostic only. They may report
missing quote coverage, stale trade dates, score-range errors, and serial-stage
breaks, but must not silently change candidate selection or operation plans.

## 2026-07-12: Matrix Supports Historical Date Replay

Decision: the dashboard accepts `--as-of-date` and the local dashboard server
can recalculate `/dashboard?as_of_date=YYYY-MM-DD`. The potential-timing matrix
date selector is a research replay control: it reruns the full serial dashboard
flow using daily quotes no later than the selected date.

Reason: the next analysis need is to inspect how a few matrix stocks' macro
potential, technical timing, and attention scores changed at historical points,
without introducing a full trade simulator.

Implication: historical replay must keep the existing stage order and scoring
formulas. Do not treat it as realized P&L backtesting, and do not use daily
quotes after the selected date in macro price metrics, technical analysis, or
operation advice.

## 2026-07-12: Dashboard Defaults To CSI 300

Decision: dashboard-oriented commands (`dashboard`, `dashboard-server`, and
`validate-dashboard`) default to `--universe csi300`. The historical date form
preserves the current universe, index symbol, sector, and stock-type filters
when submitting a new date.

Reason: the interactive matrix is currently used as a CSI 300 research surface,
and date switching should not silently fall back to the technology keyword pool.

Implication: broad screen commands can still use their own defaults, but the
dashboard path must keep the selected stock pool stable across historical
recalculations.

## 2026-07-12: CSI 300 Replay Falls Back To Cached Constituents

Decision: if `--as-of-date` is earlier than every cached CSI 300 constituent
snapshot, historical replay uses the latest cached constituent snapshot instead
of failing.

Reason: the local cache may only contain the latest CSI 300 constituent table,
while the user still needs to replay quote and score signals on earlier dates.

Implication: this fallback is a constituent-universe approximation. Quote reads
and financial-report date selection must still respect `as_of_date`.

## 2026-07-12: Cache Replay Falls Back To Cached Financial Reports

Decision: when `--source cache` historical replay cannot find a cached
financial-report table for the requested auto report candidates, it falls back
to the latest cached `stock_yjbb_YYYYMMDD` source table.

Reason: the local dashboard should render and expose data-health degradation
instead of returning HTTP 500 when older report periods were never cached.

Implication: the fallback report date must be visible in stage metadata. Missing
daily quotes before the cached quote range should remain a health warning rather
than being hidden or forward-filled.

## 2026-07-12: Signal Warnings Require Multi-Date Confirmation

Decision: `信号验证与预警` keeps the 5-complete-sample guard and adds a
3-signal-date guard before showing red `触发`. When a single-date or two-date
validation sample underperforms, the dashboard shows yellow `单日观察` instead.

Reason: a single signal date can be noisy even when complete sample counts pass
the minimum. The warning should still surface weak evidence, but red failure
should require a broader validation window.

Implication: do not silence underperformance. Prefer `signal-validate` with
`--validation-start`, `--validation-end`, and `--validation-step-days` when
deciding whether a scoring signal is genuinely failing.

## 2026-07-12: 数据回测 Uses Single-Date Fixed Holding Signals

Decision: the new signal backtest module selects the top 10 stocks from the
selected backtest signal date by three selectors: macro potential (`combo_score`),
technical timing (`technical_score`), and combined attention
(`combo_score * 65% + technical_score * 35%`). It buys at the next trading day's
open and sells at the 7th, 14th, and 21st future trading day's close.

Reason: the user's immediate need is to compare how matrix scores ranked stocks
at historical points and what those simple signal groups did afterwards. A full
portfolio simulator with rebalancing, capital allocation, transaction costs, or
stop/take-profit execution would add complexity before the score signal itself
has been validated.

Implication: keep `scripts/backtest/signal_backtest.py` focused on fixed-horizon
signal groups. Do not use it to silently tune score formulas or operation-plan
triggers. Do not mix in personal allocation fields, dynamic rebalancing, or
operation-plan trigger execution unless a later decision expands the backtest
scope. The dashboard may keep the matrix date and backtest signal date
independent so a current matrix can be compared with an older signal date that
has enough future quote data.

## 2026-07-12: Dashboard Shows Signal Validation As Warnings

Decision: when `signal_validation` exists in the dashboard model, the HTML
dashboard shows a `信号验证与预警` section. The first version visualizes the
selected signal date's quadrant and attention-bucket performance by holding
horizon, and flags whether `好时机+高潜力` is failing versus `其他象限`.

Reason: the user needs a persistent dashboard surface to diagnose whether the
current score signal itself is valid before changing factor weights or operation
advice rules.

Implication: this module is diagnostic only. It must not mutate screening
scores, candidate ordering, operation advice, or future quote availability.

## 2026-07-12: Signal Warnings Need Minimum Sample Guard

Decision: dashboard signal warnings use a minimum complete-sample guard of 5.
When `好时机+高潜力` has fewer than 5 complete rows for the selected holding
period, the quadrant warning shows `样本不足` instead of `触发`. Ranking
validation is shown separately as `排序有效性预警`, comparing `Top 1-10` with
`Top 11-20` only when both buckets have at least 5 complete rows.

Reason: a two-stock or similarly tiny quadrant can look like frequent failure
even when the result is mostly sampling noise. Separating quadrant validity from
rank-bucket validity makes the dashboard diagnostic less jumpy.

Implication: a warning state is not a score-formula change. Use it to decide
what to investigate next, not to automatically alter thresholds or candidate
selection.

## 2026-07-12: Signal Validation Separates Scoring From Execution

Decision: `signal-validate` diagnoses score-signal quality separately from
operation-advice execution. It reruns historical dashboard signal dates, then
aggregates fixed-horizon returns by matrix quadrant and attention-score bucket.

Reason: low win rate can come from two different places: weak scoring signals
or poor buy/sell execution. The first validation step should isolate whether
`好时机+高潜力` and high `attention_score` groups actually outperform other
groups before changing formulas or adding trigger-based trading rules.

Implication: `signal-validate` should not simulate `planned_entry`,
`initial_stop`, `take_profit_1r`, or `take_profit_2r`. Trigger-based operation
advice backtesting should be a separate module so results can be compared with
the fixed next-open baseline.

## 2026-07-12: 操作回测 Simulates Plan Execution Separately

Decision: add `operation-backtest` and a dashboard `操作回测` section that
simulate executable `操作建议` rows for high-potential good-timing stocks. The
first version buys when the plan trigger is reached, sells at a configurable
profit target defaulting to 5%, stops at `initial_stop`, and marks untouched
positions as held to the latest cached quote.

Reason: fixed-horizon signal backtests answer whether scores rank well, while
the user also needs to know whether the operation-plan trigger/stop/target rules
would have produced positive returns.

Implication: keep this separate from signal validation. Do not use operation
backtest results to silently change factor scores, matrix thresholds, or plan
rules. Same-day stop and target collisions should remain conservative unless
intraday data is added.

## 2026-07-12: 操作回测 Enforces A-share T+1

Decision: operation backtests must enforce the A-share T+1 rule. A triggered
buy can only be exited from the next trading day onward; the buy date itself is
never eligible for take-profit or stop-loss exits.

Reason: A-share cash equity positions bought today cannot be sold on the same
trading day. Allowing same-day exits overstated execution quality when the buy
date's high/low touched target or stop after the planned entry.

Implication: the operation path can record the buy-day price range for audit,
but target/stop checks start on the following trading day. Conservative same-day
stop-before-target collision handling still applies on later sell-eligible
trading days when intraday sequencing is unknown.
