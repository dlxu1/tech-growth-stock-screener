"""SQLite cache helpers shared by screening, planning, and reports."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from common import db_path
from data.db import connect, read_cached_source, write_quotes_daily, write_source_table


def database_path() -> Path:
    return db_path()


def read_quotes_daily(codes: list[str], columns: list[str] | None = None) -> pd.DataFrame:
    base_columns = ["code", "trade_date", "open", "high", "low", "close", "volume", "amount", "source", "updated_at"]
    selected = columns or base_columns
    if not codes:
        return pd.DataFrame(columns=selected)
    normalized_codes = [str(code).zfill(6) for code in codes if str(code).strip()]
    if not normalized_codes:
        return pd.DataFrame(columns=selected)
    placeholders = ",".join("?" for _ in normalized_codes)
    safe_columns = ", ".join(selected)
    conn = sqlite3.connect(db_path())
    try:
        prices = pd.read_sql_query(
            f"""
            select {safe_columns}
            from quotes_daily
            where code in ({placeholders})
            order by code, trade_date, updated_at
            """,
            conn,
            params=normalized_codes,
        )
    except Exception:
        return pd.DataFrame(columns=selected)
    if prices.empty:
        return prices
    prices["code"] = prices["code"].astype(str).str.zfill(6)
    prices["trade_date"] = pd.to_datetime(prices["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    prices = prices.dropna(subset=["trade_date", "close"])
    return prices.drop_duplicates(["code", "trade_date"], keep="last")


def read_price_metrics(codes: list[str]) -> pd.DataFrame:
    prices = read_quotes_daily(codes, ["code", "trade_date", "close", "amount", "updated_at"])
    if prices.empty:
        return pd.DataFrame(columns=["code"])
    rows = []
    for code, group in prices.groupby("code"):
        group = group.sort_values("trade_date")
        close = pd.to_numeric(group["close"], errors="coerce")
        amount = pd.to_numeric(group["amount"], errors="coerce")
        if close.dropna().empty:
            continue
        return_60d = float(close.iloc[-1] / close.iloc[max(0, len(close) - 60)] - 1) if len(close) > 1 else float("nan")
        drawdown = close / close.cummax() - 1
        rows.append(
            {
                "code": str(code).zfill(6),
                "amount_20d": float(amount.tail(20).mean()) if amount.notna().any() else float("nan"),
                "return_60d": return_60d,
                "max_drawdown_252d": float(drawdown.tail(252).min()) if drawdown.notna().any() else float("nan"),
            }
        )
    return pd.DataFrame(rows)


__all__ = [
    "connect",
    "database_path",
    "read_cached_source",
    "read_price_metrics",
    "read_quotes_daily",
    "write_quotes_daily",
    "write_source_table",
]

