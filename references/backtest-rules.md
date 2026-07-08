# Backtest Rules

Use this reference when changing or explaining the backtest layer.

## Boundaries

Backtests must not fetch market data from remote sources. They consume:

- strategy output from `scripts/strategies/`;
- historical prices from `quotes_daily`;
- costs and portfolio rules from `scripts/backtest/`.

If `quotes_daily` is empty, run:

```bash
python scripts/run.py sync --dataset daily_prices --from-strategy --top 10 --start 2024-01-01 --end 2026-07-08
```

## Initial Assumptions

The first backtest engine is intentionally simple:

- portfolio: equal weight;
- candidates: top N from the selected strategy;
- prices: `quotes_daily.close`;
- metrics: total return, max drawdown, covered days;
- missing daily prices: return a clear `missing-data` status rather than guessing.

## Next Extensions

Add these only after daily price sync exists:

- rebalance frequency;
- transaction costs and slippage;
- benchmark comparison;
- annualized return and volatility;
- rolling drawdown and win rate.
