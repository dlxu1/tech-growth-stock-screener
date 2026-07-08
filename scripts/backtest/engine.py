"""Minimal equal-weight backtest scaffold.

This layer intentionally consumes strategy outputs and database price data. It
does not fetch remote data directly.
"""

from __future__ import annotations

import sqlite3

import pandas as pd

from common import db_path


def run_equal_weight(candidates: pd.DataFrame, start: str, end: str, top: int) -> dict:
    symbols = candidates.head(top)["code"].astype(str).tolist()
    if not symbols:
        return {"status": "empty", "message": "策略没有返回候选股票。"}
    conn = sqlite3.connect(db_path())
    placeholders = ",".join("?" for _ in symbols)
    prices = pd.read_sql_query(
        f"""
        select code, trade_date, close, updated_at
        from quotes_daily
        where code in ({placeholders})
          and trade_date >= ?
          and trade_date <= ?
        order by trade_date, code
        """,
        conn,
        params=[*symbols, start, end],
    )
    if prices.empty:
        return {
            "status": "missing-data",
            "message": "数据库 quotes_daily 暂无可用于回测的日行情；先运行数据层同步历史行情后再回测。",
            "symbols": symbols,
        }
    prices = prices.sort_values(["code", "trade_date", "updated_at"]).drop_duplicates(["code", "trade_date"], keep="last")
    pivot = prices.pivot(index="trade_date", columns="code", values="close").sort_index()
    returns = pivot.pct_change().dropna(how="all")
    portfolio = returns.mean(axis=1)
    equity = (1 + portfolio.fillna(0)).cumprod()
    if equity.empty:
        return {"status": "insufficient-data", "symbols": symbols}
    drawdown = equity / equity.cummax() - 1
    return {
        "status": "ok",
        "symbols": symbols,
        "start": str(equity.index[0]),
        "end": str(equity.index[-1]),
        "total_return": float(equity.iloc[-1] - 1),
        "max_drawdown": float(drawdown.min()),
        "days": int(len(equity)),
    }
