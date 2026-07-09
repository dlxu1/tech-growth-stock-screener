"""Display-layer data helpers."""

from __future__ import annotations

import sqlite3

import pandas as pd

from common import db_path


def normalize_report_meta(meta: dict | None) -> dict:
    return dict(meta or {})


def load_index_constituents(index_symbol: str = "000300", constituent_date: str = "latest") -> tuple[pd.DataFrame, dict]:
    conn = sqlite3.connect(db_path())
    index_symbol = str(index_symbol).strip() or "000300"
    if constituent_date == "latest":
        row = conn.execute(
            "select max(constituent_date) from index_constituents where index_symbol=?",
            (index_symbol,),
        ).fetchone()
        constituent_date = row[0] if row and row[0] else ""
    if not constituent_date:
        return (
            pd.DataFrame(columns=["code", "name", "exchange", "weight", "weight_date"]),
            {"index_symbol": index_symbol, "constituent_date": "", "db_path": str(db_path())},
        )
    df = pd.read_sql_query(
        """
        select index_symbol, index_name, constituent_date, code, name, exchange, weight, weight_date, source, updated_at
        from index_constituents
        where index_symbol=? and constituent_date=?
        order by coalesce(weight, -1) desc, code
        """,
        conn,
        params=(index_symbol, constituent_date),
    )
    meta = {
        "index_symbol": index_symbol,
        "index_name": "" if df.empty else str(df["index_name"].dropna().iloc[0]),
        "constituent_date": constituent_date,
        "weight_date": "" if df.empty else str(df["weight_date"].dropna().max()),
        "rows": len(df),
        "db_path": str(db_path()),
    }
    return df, meta
