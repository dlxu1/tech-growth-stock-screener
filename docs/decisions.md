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
