"""SQLite cache helpers shared by screening, planning, and reports."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from common import db_path
from data.db import connect, read_cached_source, write_quotes_daily, write_source_table


def database_path() -> Path:
    return db_path()


def read_quotes_daily(codes: list[str], columns: list[str] | None = None, as_of_date: str | None = None) -> pd.DataFrame:
    base_columns = ["code", "trade_date", "open", "high", "low", "close", "volume", "amount", "source", "updated_at"]
    selected = columns or base_columns
    if not codes:
        return pd.DataFrame(columns=selected)
    normalized_codes = [str(code).zfill(6) for code in codes if str(code).strip()]
    if not normalized_codes:
        return pd.DataFrame(columns=selected)
    placeholders = ",".join("?" for _ in normalized_codes)
    date_filter = " and trade_date<=?" if as_of_date else ""
    params = [*normalized_codes, as_of_date] if as_of_date else normalized_codes
    safe_columns = ", ".join(selected)
    conn = sqlite3.connect(db_path())
    try:
        prices = pd.read_sql_query(
            f"""
            select {safe_columns}
            from quotes_daily
            where code in ({placeholders})
            {date_filter}
            order by code, trade_date, updated_at
            """,
            conn,
            params=params,
        )
    except Exception:
        return pd.DataFrame(columns=selected)
    finally:
        conn.close()
    if prices.empty:
        return prices
    prices["code"] = prices["code"].astype(str).str.zfill(6)
    prices["trade_date"] = pd.to_datetime(prices["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    prices = prices.dropna(subset=["trade_date", "close"])
    return prices.drop_duplicates(["code", "trade_date"], keep="last")


def read_price_metrics(codes: list[str], as_of_date: str | None = None) -> pd.DataFrame:
    prices = read_quotes_daily(codes, ["code", "trade_date", "close", "amount", "updated_at"], as_of_date=as_of_date)
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


def read_index_constituents(index_symbol: str = "000300", constituent_date: str = "latest", as_of_date: str | None = None) -> pd.DataFrame:
    conn = sqlite3.connect(db_path())
    try:
        index_symbol = str(index_symbol).strip() or "000300"
        if constituent_date == "latest":
            if as_of_date:
                row = conn.execute(
                    "select max(constituent_date) from index_constituents where index_symbol=? and constituent_date<=?",
                    (index_symbol, as_of_date),
                ).fetchone()
                if not row or not row[0]:
                    row = conn.execute(
                        "select max(constituent_date) from index_constituents where index_symbol=?",
                        (index_symbol,),
                    ).fetchone()
            else:
                row = conn.execute(
                    "select max(constituent_date) from index_constituents where index_symbol=?",
                    (index_symbol,),
                ).fetchone()
            constituent_date = row[0] if row and row[0] else ""
        if not constituent_date:
            return pd.DataFrame(columns=["index_symbol", "index_name", "constituent_date", "code", "name", "exchange", "weight", "weight_date"])
        df = pd.read_sql_query(
            """
            select index_symbol, index_name, constituent_date, code, name, exchange, weight, weight_date, source, updated_at
            from index_constituents
            where index_symbol=? and constituent_date=?
            order by code
            """,
            conn,
            params=(index_symbol, constituent_date),
        )
    except Exception:
        return pd.DataFrame(columns=["index_symbol", "index_name", "constituent_date", "code", "name", "exchange", "weight", "weight_date"])
    finally:
        conn.close()
    if not df.empty:
        df["code"] = df["code"].astype(str).str.zfill(6)
    return df


__all__ = [
    "connect",
    "database_path",
    "read_cached_source",
    "read_index_constituents",
    "read_price_metrics",
    "read_quotes_daily",
    "write_quotes_daily",
    "write_source_table",
]
