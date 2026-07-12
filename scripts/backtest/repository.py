"""Cache reads for signal backtests."""

from __future__ import annotations

import sqlite3

import pandas as pd

from common import db_path


def load_forward_quotes(codes: list[str], after_date: str) -> pd.DataFrame:
    """Load cached daily quotes strictly after the signal date."""

    normalized = [str(code).zfill(6) for code in codes if str(code).strip()]
    columns = ["code", "trade_date", "open", "high", "low", "close", "volume", "amount", "source", "updated_at"]
    if not normalized:
        return pd.DataFrame(columns=columns)
    placeholders = ",".join("?" for _ in normalized)
    conn = sqlite3.connect(db_path())
    try:
        quotes = pd.read_sql_query(
            f"""
            select code, trade_date, open, high, low, close, volume, amount, source, updated_at
            from quotes_daily
            where code in ({placeholders}) and trade_date>?
            order by code, trade_date, updated_at
            """,
            conn,
            params=[*normalized, after_date],
        )
    except Exception:
        return pd.DataFrame(columns=columns)
    finally:
        conn.close()
    if quotes.empty:
        return quotes
    quotes["code"] = quotes["code"].astype(str).str.zfill(6)
    quotes["trade_date"] = pd.to_datetime(quotes["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    quotes = quotes.dropna(subset=["trade_date", "close", "open"])
    return quotes.drop_duplicates(["code", "trade_date"], keep="last")
