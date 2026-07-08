# Fine Strategies

Use this reference when changing technical fine-screening inputs, indicators, score weights, reason labels, missing-data behavior, or the handoff to the plan layer.

## Layer Boundary

Fine screening is the second business-selection layer. It consumes coarse-screen outputs and cached `quotes_daily` rows, then ranks candidates by technical condition.

The layer is split into:

- `scripts/strategies/fine/network.py`: optional daily-price refresh hook.
- `scripts/strategies/fine/repository.py`: loads coarse candidates and cached daily quotes.
- `scripts/strategies/fine/technical.py`: computes indicators, scores candidates, and assigns reason labels.

Fine strategies must not fetch remote data directly. They should read from `quotes_daily` through the repository/cache boundary.

## Input Data

The default fine strategy starts by running coarse screening.

Default flow:

1. Run coarse screening using `--coarse-strategy`.
2. Keep `--coarse-top 5` names per coarse strategy.
3. Deduplicate stock codes.
4. Preserve the highest coarse score per stock.
5. Read OHLCV bars from `quotes_daily`.
6. Compute technical indicators from the latest available trade date.
7. Sort by `technical_score` descending, then `coarse_score` descending.

`quotes_daily` must provide:

- `code`
- `trade_date`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`

If no daily bars exist for a stock, the stock stays visible but receives score 0 and a missing-data note.

## Cache Behavior

Fine screening does not persist its own historical scoring results today.

- Historical OHLCV bars are retained in `quotes_daily`.
- Technical indicators are recomputed on each run.
- `technical_score`, `technical_reasons`, and the fine-ranked stock list are not currently written to SQLite.

If fine-score history is needed, add:

- `fine_runs`: one row per fine-screen execution.
- `fine_results`: one row per stock per run, including indicator values, score, reason labels, data status, and coarse-source metadata.

## Indicator Set

The current technical score uses:

- moving averages: `ma5`, `ma10`, `ma20`;
- moving-average slope: MA20 latest value versus recent prior value;
- returns: `return_20d`, `return_60d`;
- MACD histogram: EMA12, EMA26, DEA9, then `(DIF - DEA) * 2`;
- RSI: `rsi14`;
- turnover expansion: latest amount divided by recent average amount;
- 20-day average amount;
- breakout position: prior 20-day high and current 20-day high;
- candle close position inside the latest high-low range;
- drawdown: `max_drawdown_20d`;
- ATR percentage: ATR14 divided by latest close.

## Score Weights

Total score is 100 points:

- Trend: 30 points
- Momentum: 20 points
- Volume/price confirmation: 20 points
- Breakout: 15 points
- Drawdown/volatility risk: 10 points
- Liquidity: 5 points

Each component is capped before contributing to the total score.

## Component Logic

Trend component:

- latest close above MA20 contributes 35% of trend score;
- MA5 >= MA10 >= MA20 contributes 35%;
- MA20 rising contributes 30%.

Momentum component:

- positive 20-day return contributes 40%;
- MACD histogram above 0 contributes 35%;
- RSI14 between 50 and 75 contributes 25%;
- RSI14 between 45 and 50 contributes a smaller partial score.

Volume/price component:

- latest amount at least 1.2x recent average contributes 55%;
- latest daily change positive contributes 35%;
- 20-day average amount above `--min-amount` contributes 10%.

Breakout component:

- latest close above the prior 20-day high contributes 55%;
- latest close within 98% of the 20-day high contributes 25%;
- latest close in the upper part of the daily range contributes 20%.

Risk component:

- 20-day drawdown no worse than -8% contributes 60%;
- 20-day drawdown between -15% and -8% contributes partial score;
- ATR percentage no higher than 6% contributes 40%;
- ATR percentage between 6% and 10% contributes partial score.

Liquidity component:

- 20-day average amount above `--min-amount` contributes the full liquidity score.

## Reason Labels

Reason labels are generated from component strength:

- `趋势强`: trend component is strong.
- `放量突破`: volume and breakout components are both strong.
- `量能改善`: volume improves but breakout is weaker.
- `回撤可控`: drawdown and ATR risk are controlled.
- `动量较好`: momentum component is strong.
- `流动性达标`: 20-day average turnover is above the configured threshold.
- `技术面一般`: no stronger label applies.

These labels are used by the plan layer to decide whether the candidate is a breakout, pullback, volume-confirmation, watch, or no-trade candidate.

## Missing Data Behavior

No daily bars:

```text
technical_score = 0
technical_reasons = 缺少日线数据
technical_note = quotes_daily 无该股票数据，需先同步 daily_prices
```

Fewer than 20 daily bars:

The strategy remains runnable and computes indicators with the available short sample. `technical_note` must say the daily sample is below 20 rows and the calculation is degraded.

## Output Columns

Fine output includes:

- identity: `code`, `name`, `board_name`;
- coarse context: `coarse_strategies`, `coarse_score`;
- latest state: `latest_trade_date`, `close`, `change_pct`;
- indicators: `return_20d`, `return_60d`, `amount_ratio`, `ma5`, `ma10`, `ma20`, `macd_hist`, `rsi14`, `max_drawdown_20d`;
- ranking: `technical_score`;
- explanation: `technical_reasons`, `technical_note`.

## Maintenance Checklist

When adding or changing a fine indicator:

1. Add the indicator calculation in `technical.py`.
2. Add the output column if users or the plan layer need to see it.
3. Decide whether it affects component scores or only report display.
4. Update score weights and reason-label thresholds carefully.
5. Keep missing-data behavior explicit.
6. If the indicator needs new cached data, add it behind repository/cache boundaries.
7. Update this reference.
8. Validate with `--source cache` and with a run where at least one stock has missing `quotes_daily`.

## Commands

Run fine screening after all coarse strategies:

```bash
python scripts/run.py fine --coarse-strategy all --coarse-top 5 --top 10
```

Run fine screening after one coarse strategy:

```bash
python scripts/run.py fine --coarse-strategy market_cap_reasonable_pe --coarse-top 5 --top 5
```

Run strictly from existing cache:

```bash
python scripts/run.py fine --coarse-strategy all --coarse-top 5 --top 10 --source cache
```
