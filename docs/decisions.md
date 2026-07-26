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

## 2026-07-18: Dashboard Model Has A Snapshot Node

Decision: after the dashboard pipeline completes `操作建议`, it builds the full
dashboard model and persists it to a dedicated `dashboard_snapshots` SQLite
table. Snapshot reuse is keyed by dashboard parameters plus source-data
fingerprints, and is enabled by default for dashboard-oriented commands.

Reason: historical dashboard dates are often revisited. Reusing the complete
model avoids rerunning `股票池 -> 宏观粗筛 -> 技术分析 -> 操作建议` when the same
parameters and unchanged source data have already produced a model.

Implication: `layer_runs` and `layer_results` remain row-level audit trails for
individual stages. `dashboard_snapshots` is the complete dashboard-data cache.
Use `--no-dashboard-cache` to force no reuse, `--rebuild-dashboard-cache` to
recalculate and replace a matching snapshot, and `--refresh` or
`--update-policy refresh` for source-data refresh flows.

## 2026-07-25: Dashboardv2 Is A Parallel Industry-Thesis View

Decision: keep the existing `dashboard` v1 interaction unchanged and add
`dashboardv2` as a separate entry. v2 reuses the current dashboard data model
but renders it as `行业主线 -> 主线股票池 -> 龙头收敛 -> 技术确认 -> 每日复盘`.
The first implementation uses available board-name, quote, turnover, financial
and plan fields from the existing model to estimate industry mainlines.

Reason: the user needs a less black-box research flow where industry direction
comes before individual-stock technical timing, while still preserving the
current CSI 300 dashboard as a familiar research surface.

Implication: do not insert industry-mainline UI into v1 by default. Keep v2
snapshot identity separate with `dashboard_variant="v2"` while preserving v1
snapshot-key compatibility. If industry index history,资金流 or news catalysts
are missing, v2 must show a conservative degradation note instead of inventing
reasons or broadening back to an unconstrained whole-market recommendation.

## 2026-07-17: Repeated Strong-Signal Stats Are Cached

Superseded on 2026-07-18 by `近 1 月重复强信号改为矩阵信号物化`. The JSON cache
remains as a final computed-result cache, but SQLite `dashboard_matrix_signals`
is now the primary acceleration path.

Decision: the `近 1 月重复强信号` calculation keeps its existing semantics but is
cached. The persistent cache stores computed `recent_high_good_hits` by
dashboard date, signal-date list, current high-potential+good-timing codes,
relevant dashboard parameters, cache version, and SQLite data-file fingerprint.
The live dashboard server also caches rendered responses in memory for identical
URLs while the key SQLite table freshness/count fingerprint is unchanged.

Reason: computing repeated strong signals by rerunning roughly one month of
historical dashboard snapshots added about 70 seconds to each page load. Cache
reuse keeps the first uncached calculation correct and makes refreshes or
service restarts reuse the same result when the source data has not changed.

Implication: do not change repeated-hit formulas, adaptive-threshold behavior,
or key parameters without bumping the cache version in
`scripts/dashboard/pipeline.py`.

## 2026-07-18: NAS Deployment Uses Dashboard Server Container

Decision: NAS/Docker deployment runs the live `dashboard-server` instead of
serving only the static `dashboard_latest.html`. The container listens on
`0.0.0.0:5001`, maps the NAS port to `5001`, and persists `/app/.cache` through
the host `nas-cache` directory.

Reason: the current dashboard depends on server-side recalculation for
historical dates, `/api/dashboard`, dashboard snapshots, and matrix-signal
cache reuse. A static HTML-only deployment would lose those interactive
research workflows.

Implication: keep Docker entrypoints aligned with
`scripts/run.py dashboard-server --source cache --host 0.0.0.0 --port 5001`.
Do not bake `.cache` into the image; copy or mount `stock_data.sqlite` through
the persistent `nas-cache` volume.

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

## 2026-07-16: Data Updates Default To Incremental

Decision: daily-price sync defaults to incremental `skip_existing` behavior at
both the CLI and data-source function layers. A normal "更新数据" operation should
fill only missing daily-price tails and should not pass `--refresh` or
`--no-skip-existing` unless a full rebuild is explicitly requested. Financial
report `auto` selection prefers the latest complete-looking report table and
skips obviously incomplete fresh quarters when a complete cached/fetched
candidate is available.

Reason: repeated full-universe daily-price refreshes are slow, unnecessary, and
increase the chance of upstream throttling or partial overwrites. Incomplete
new financial quarters can distort stock-pool and macro scores by silently
shrinking the financial universe.

Implication: future data-update commands should rely on default incremental
daily-price sync and cache freshness checks. Use `--no-skip-existing`,
`--refresh`, or `--update-policy refresh` only for deliberate data repair or
full rebuild tasks.

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

## 2026-07-13: 市场状态过滤器

Decision: 在 dashboard pipeline 中新增市场状态检测模块 `scripts/dashboard/market_state.py`。当前实现是在股票池阶段完成后、combo 阶段前，用候选样本的日线中位数和宽度判定当前市场处于 bull、transition 还是 bear。

判定规则：
- 样本中位 close/MA30 > 1.0 → 1 张牛市票
- 样本宽度（close/MA20 > 1 的股票占比）> 60% → 1 张牛市票
- 样本中位 MA20 斜率 > 0 → 1 张牛市票
- 3/3 → bull；1/3 或 2/3 → transition；0/3 → bear

非 bull 状态下的影响：
- `max_position`（仓位上限）按状态乘以 0.85 或 0.60
- 通过 `setattr(args, "max_position", ...)` 传递，不修改 trade_plan 代码
- market regime 传入 `run_combo()`，直接改变 `momentum_score` 组成和 `combo_score` 权重

市场状态信息通过 `model["summary"]["market_state"]` 暴露给看板和 API。

Reason: 2026-06-30 回测数据表明，在市场整体下跌期间（中位股票在 MA20 下方且 MA20 下行），当前评分体系选出的高分股（前期涨幅大的科技股）反而跌幅最大。在市场下行期自动降仓位可以保护本金，这是最轻量的防御性改动。

Implication:
- 市场状态现在会影响 combo_score；复盘分布时必须按 bull/transition/bear 分开看
- technical_score 的计算不受市场状态影响
- 市场状态通过已有的 args 对象传递，trade_plan 无需感知
- 无候选股、缺少日线或有效样本不足时仍默认 bull，避免离线缓存不完整时误触发防御

## 2026-07-13: 行业中性化

Decision: combo_score 中的 quality_score（ROE 排序 + 毛利率排序）和 risk_control_score（最大回撤排序）从全局 percentile rank 改为行业内 percentile rank。通过 `board_name` 分组，每组内独立排名后映射到 0-1。

小行业（< 5 只股票）合并为「其他」组，避免噪声。

Reason: CSI 300 中金融和消费行业天然 ROE 高、毛利率稳、回撤小，在全局排名中系统性霸榜。行业中性化确保各行业内最优秀的公司都能被发现，而非集中在少数低波动行业。

Implication:
- growth_score、liquidity_score、momentum_score 保持全局 rank——这些指标跨行业可比性好
- PE 合理度保持全局（行业 PE 中位数已隐含行业基准）
- overlap_score 不受影响（策略排名仍基于全局 rank）
- 代码改动集中在 `scripts/strategies/coarse/registry.py` 的 `run_combo` 和新增的 `scripts/strategies/coarse/neutralizer.py`

## 2026-07-13: 矩阵象限阈值自适应

Decision: 矩阵象限线（宏观潜力 ≥ 80、技术时机 ≥ 75）从固定值改为基于当前候选股分数分布的动态分位数。宏观潜力阈值取 combo_score 的 70 分位，技术时机阈值取 technical_score 的 65 分位。样本不足 15 时降级到固定默认值。

阈值通过 `model["summary"]["adaptive_thresholds"]` 传递给前端和后端回测模块。`signal_backtest.py` 和 `operation_backtest.py` 的函数签名增加了可选 `macro_threshold` 和 `tech_threshold` 参数，未传入时使用模块级常量作为 fallback。

Reason: 固定阈值在牛市（分数普遍膨胀）和熊市（分数普遍收缩）中表现不一致。70/65 分位确保「好时机+高潜力」始终是当前市场中最优秀的约 10-15% 的股票。

Implication:
- 历史回测中的 `signal-validate` 和 `operation-backtest` 也受益于动态阈值
- HTML 轴标签动态显示当前阈值
- 阈值的分位数参数（70/65）可通过 `compute_dynamic_thresholds` 的参数调整

## 2026-07-15: PEG 因子 + 动量/反转 + 技术面信号精细化（濮元恺《量化投资技术分析实战》）

### 宏观粗筛改动

1. **PEG 因子替换 PE 合理度**：`quality_score` 中 PE 合理度（25%）替换为 PEG 评分（35%），权重调整为 ROE(40%) + gross_margin(25%) + PEG(35%)。PEG = PE / max(growth_pct, 1)，其中 growth_pct 对 `20.0` 百分数单位和 `0.20` 小数比例单位自适应，映射到 0-1 分。

2. **动量分解为趋势动量 + 均值反转**：`momentum_score` 从单一 return_60d rank 改为 return_60d_rank(55%) + mean_reversion_score(45%)。反转信号仅在 revenue_yoy>0 且 profit_yoy>0 时生效，回撤越深反转分越高；同时用 return_60d 因子惩罚已经明显反弹的股票，避免把“已完成反转”误计成高反转潜力。

3. **combo_score 权重调整**：overlap 35→30, growth 20→22, quality 18→20, risk_control 15→13, liquidity 7→7, momentum 5→8。

### 技术细筛改动

4. **量价配合确认**：`volume_score` 从简单的量比+涨跌改为放量阳线(35%) + 显著放量阳线(20%) + 上涨(25%) + 量价配合(10%) + 流动性(10%)。

5. **MACD 信号精细化**：MACD 柱加速扩大→20%、MACD 柱缩小→8%、金叉→7%，替代原来笼统的 hist>0 给 35%。

6. **筹码集中度**：`breakout_score` 加入 volume_concentration 因子（近 5 日量/近 20 日量），≥35% 为强筹码堆积。

7. **换手率稳定性**：`risk_score` 加入 turnover_stability（1-CV(20日换手率)），低 CV=机构持仓特征。换手率通过 volume × close / market_cap 近似计算。

8. **technical_score 权重调整**：trend 30→28, momentum 20→22, volume 20→22, breakout 15→15, risk 10→8, liquidity 5→5。

### 数据支撑

- PEG/动量/反转/MACD/量价/筹码集中度：现有 quotes_daily 数据足够
- 换手率稳定性：通过 volume × close / market_cap 推导 total_shares，在 fine 阶段计算
- `fine/repository.py` 和 `_candidates_from_previous_stage` 新增 market_cap 穿透

### 依据

- 4.3 PEG 价值选股模型（彼得·林奇路径）
- 4.5 动量效应和反转效应
- 4.6 换手率和资金流模型（主力和筹码盘根错节）
- 4.8 聪明钱因子模型（低 CV 换手率近似机构行为）
- 4.4 技术指标测试平台（多指标验证、MACD 发散检测）

## 2026-07-16: 矩阵标记近 1 月重复强信号

Decision: 对当前矩阵中属于 `好时机+高潜力` 的股票，统计过去 30 个自然日内它们在可用交易日上再次落入 `好时机+高潜力` 的次数。每个历史信号日使用该日期重算后的动态阈值，不套用当前日期阈值。命中次数从 4 次起在矩阵点上显示外圈和次数 badge，hover 展示具体命中日期；右侧详情不再重复展示这段日期说明。

Reason: 单日落入高潜力+好时机可能是偶然分布位置；连续多次落入同一象限说明这只股票在近期多次同时满足宏观潜力和技术时机，有必要在矩阵上显式提醒，但不能因此直接改变评分公式或操作建议。

Implication: `recent_high_good_hits` 是展示和诊断字段，出现在技术分析/操作建议行中。它不得改变 `combo_score`、`technical_score`、动态阈值、阶段样本、回测样本或操作计划。历史统计递归重跑 dashboard 时必须跳过回测和重复统计，避免递归放大耗时。

## 2026-07-18: 近 1 月重复强信号改为矩阵信号物化

Decision: `recent_high_good_hits` 默认恢复展示，但不再优先递归重跑历史 dashboard。每个 cache-enabled dashboard model 会把矩阵候选的 `combo_score/coarse_score`、`technical_score`、当日动态阈值和 `is_high_good` 写入 `dashboard_matrix_signals`。近 1 月命中次数优先用这张表 SQL 聚合，缺失日期先从已有 `dashboard_snapshots.model_json` 水化，最后才回退重算缺失日期。需要临时关闭展示时传 `--no-recent-high-good-hits`。

Reason: 原实现切换历史日期时需要回看 30 个自然日内多个交易日，并对每个历史信号日重跑 dashboard。2026-07-09 实测首次开启耗时约 113 秒，命中完整缓存后约 1 秒。物化矩阵信号把核心统计从 O(交易日数 × dashboard 四阶段) 改为优先 O(一次 SQL 聚合)。

Implication: `recent_high_good_hits` 仍然只是展示/诊断字段，不改变评分、阈值、样本或操作建议。`dashboard_matrix_signals` 是 dashboard snapshot 的派生加速表，使用矩阵 scope key 和 source-data fingerprint 防止跨参数或跨数据版本复用。

## 2026-07-20: 高潜力好时机股票增加投资周期研究注释

Decision: dashboard 操作建议行新增 `horizon_tags`、`primary_horizon`、`horizon_reason` 和 `horizon_data_note`，在 UI 中展示为 `适合周期`、`优先关注` 和周期说明。标签只用于研究解释，可同时出现 `长线`、`中线`、`短线`，但不参与筛选、排序、评分、阈值、操作计划或回测样本。

Reason: `好时机+高潜力` 只说明当前宏观潜力和技术时机共振，但不同股票的证据来源不同。质量/成长/风控证据更适合长期跟踪，宏观潜力和技术时机共振更偏中线观察，可执行入场和止损字段更偏短线计划。把这些差异显式展示，可以减少用户在交互层自行猜测。

Implication:
- 周期分类器必须消费现有 dashboard 行字段，不新增独立选股策略。
- `策略口径` 和 `权重版本` 是全局 dashboard 状态，放在数据健康栏；个股周期标签放在选中股票详情和操作建议行内。
- `权重版本` hover 解释当前市场状态对应的权重口径：牛市动量版、震荡防御版或熊市防御版。
- 每日邮件摘要必须消费 dashboard model 中已有周期字段，不在邮件层重新计算另一套规则；字段缺失时展示 `证据不足，需人工复核`。
