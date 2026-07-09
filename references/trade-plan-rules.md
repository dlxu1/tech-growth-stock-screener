# Trade Plan Rules

Use this reference when changing next-session operation plans, entry rules, stop-loss rules, take-profit rules, position sizing, missing-data diagnostics, or plan output fields.

## Layer Boundary

The plan layer turns fine-screened candidates into next-session rule plans. It does not select the initial universe and does not fetch remote market data directly.

The layer is split into:

- `scripts/plan/network.py`: optional refresh hook for data needed by plans.
- `scripts/plan/repository.py`: reads cached daily quotes from `quotes_daily`.
- `scripts/plan/trade_plan.py`: computes actions, entry levels, stop levels, take-profit levels, position caps, and data-quality diagnostics.
- `scripts/reports/trade_plan_markdown.py`: renders plan output and diagnostics.

The plan is a ruleset for the next trading session, not a guaranteed execution instruction.

## Input Data

The plan layer starts by running fine screening with `--top 5` by default. It then reads cached OHLCV bars for those stocks from `quotes_daily`.

Required daily fields:

- `trade_date`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`

Required fine-screen fields:

- `technical_score`
- `technical_reasons`
- `latest_trade_date`
- stock identity and board fields

## Cache Behavior

The plan layer consumes historical daily bars from `quotes_daily`.

Plan outputs are persisted to `layer_runs` and `layer_results`.

- Entry levels, stop levels, action labels, and data diagnostics are stored as historical snapshots.
- `layer_results.row_json` stores the complete plan row, including entry, stop, take-profit, position cap, action, strategy label, and data-quality fields.

## Action Selection

The plan first converts technical score and reason labels into an action and primary strategy.

Rules:

- missing latest close or technical score below 60: `暂不交易`, `no_trade`;
- score at least 80 and reason contains `放量突破`: `允许条件买入`, `breakout_buy`;
- score at least 70 and reason contains `趋势强`: `等待回踩买入`, `pullback_ma_buy`;
- score at least 60 and reason contains `量能改善` or `动量较好`: `等待放量确认`, `volume_confirm_buy`;
- otherwise: `观察`, `watch`.

Strategy labels:

- `breakout_buy`: buy only after price breaks latest high or recent high with a configurable buffer.
- `pullback_ma_buy`: buy only if price pulls back into the MA5/MA10/MA20 support zone and stabilizes.
- `volume_confirm_buy`: buy only if price action is positive and turnover reaches the confirmation threshold.
- `watch`: keep on watchlist but do not open by default.
- `no_trade`: no trade because score or data quality is insufficient.
- `no_data`: no trade because cached daily quotes are missing.

## Entry Metrics

The plan computes:

- `latest_close`: latest cached close.
- `breakout_trigger`: max of latest high, prior 20-day high, and latest close, multiplied by `1 + --breakout-buffer`.
- `pullback_low`: low side of the MA/price support zone, with a small buffer.
- `pullback_high`: high side of the MA/price support zone, with a small buffer.
- `volume_confirm_amount`: recent average amount multiplied by `--volume-multiplier`.
- `planned_entry`: the reference entry used for risk calculations.

Planned-entry rules:

- `breakout_buy`: `planned_entry = breakout_trigger`.
- `pullback_ma_buy`: `planned_entry = midpoint(pullback_low, pullback_high)`.
- `volume_confirm_buy`: `planned_entry = latest_close * (1 + breakout_buffer)`.
- `watch`, `no_trade`, `no_data`: no planned entry.

## Stop-Loss Metrics

The plan computes an initial stop from multiple candidates:

- fixed-percent stop: `planned_entry * (1 - --stop-pct)`;
- ATR stop: `planned_entry - --atr-stop-multiplier * ATR14`;
- MA20 stop: `MA20 * 0.99`;
- recent-low stop: recent 10-day low * 0.995.

Only stop candidates below `planned_entry` are valid. The selected `initial_stop` is the highest valid stop candidate, so the risk level stays close to the entry while remaining below it.

Derived risk metric:

- `risk_pct = (planned_entry - initial_stop) / planned_entry`.

## Take-Profit and Trailing Stop Metrics

The plan computes:

- `take_profit_1r = planned_entry + 1 * risk`;
- `take_profit_2r = planned_entry + 2 * risk`;
- `trailing_stop_rule`: text rule for post-entry trailing stops.

Default trailing rules:

- after profit reaches `--move-stop-profit`, lift stop to cost;
- after profit reaches `--trailing-profit`, use highest close drawdown by `--trailing-drawdown` or MA10 break as trailing stop.

## Position Sizing

Position cap is score-based:

- score below 60 or missing: 0%;
- score 60 to 75: up to 12%;
- score 75 to 85: up to 20%;
- score at least 85: up to `--max-position`, default 25%.

This is a maximum single-stock cap. It does not compute whole-portfolio exposure or cash allocation.

## Cancel Conditions

Common no-buy/cancel conditions:

- next-session open gaps above latest close by more than `--max-gap-up`;
- price opens below the initial stop;
- entry price is not triggered and amount does not reach confirmation threshold.

Additional pullback condition:

- if price pulls below MA20 and cannot recover quickly, do not buy.

Additional breakout condition:

- if price breaks out then falls back below trigger with weakening volume, cancel the order.

## Stop Conditions

Common exit/risk conditions:

- after buying, price breaks the initial stop;
- close breaks MA20 while MACD and volume also weaken;
- after profit reaches `--move-stop-profit`, move stop to cost.

These are rules for risk control. They should be rendered as conditional rules, not as guaranteed execution outcomes.

## Missing Data Diagnostics

Every plan row should explain data quality:

- `complete`: enough cached daily bars for the current rule set.
- `degraded_short_history`: fewer than 20 daily bars. The plan may still run, but MA20, 20-day high, turnover average, and drawdown use a short sample.
- `missing_quotes`: no cached daily bars. Entry, stop, take-profit, and volume-confirmation levels cannot be computed; the stock must be marked `暂不交易`.

Diagnostic fields:

- `data_status`
- `missing_data_reason`
- `missing_data_impact`
- `usable_for_plan`
- `plan_note`

Reports must show both the reason for missing data and the impact on scoring, risk controls, and whether the stock is usable for a next-session plan.

## Output Columns

Plan output includes:

- identity: `code`, `name`, `board_name`;
- decision: `action`, `primary_strategy`;
- fine context: `technical_score`, `technical_reasons`;
- latest state: `basis_trade_date`, `latest_close`;
- entry: `breakout_trigger`, `pullback_low`, `pullback_high`, `volume_confirm_amount`, `planned_entry`;
- risk: `initial_stop`, `risk_pct`, `position_cap`;
- profit/risk management: `take_profit_1r`, `take_profit_2r`, `trailing_stop_rule`;
- rule text: `cancel_conditions`, `stop_conditions`;
- data diagnostics: `data_status`, `missing_data_reason`, `missing_data_impact`, `usable_for_plan`, `plan_note`.

## Maintenance Checklist

When changing plan logic:

1. Keep action selection tied to fine-screen score and reason labels.
2. Keep all entry/stop/profit levels derived from cached `quotes_daily`.
3. Add new output fields to `OUTPUT_COLUMNS`.
4. Update the Markdown renderer if users need to see the new field.
5. Keep missing-data behavior explicit and non-blocking.
6. Avoid wording that implies guaranteed profit or guaranteed execution.
7. Update this reference.
8. Validate with complete data, short-history data, and missing-quotes data.

## Command

```bash
python scripts/run.py plan --coarse-strategy all --coarse-top 5 --top 5
```

Run from existing cache only:

```bash
python scripts/run.py plan --coarse-strategy all --coarse-top 5 --top 5 --source cache
```
