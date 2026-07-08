"""SQLite cache for source tables and normalized stock data."""

from __future__ import annotations

import re
import sqlite3
from hashlib import sha1
from datetime import datetime
from pathlib import Path

import pandas as pd

from common import db_path


def connect(path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or db_path(), timeout=30)
    conn.execute("pragma journal_mode=wal")
    conn.execute("pragma foreign_keys=on")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        create table if not exists cache_meta (
            table_key text primary key,
            table_name text not null,
            source text not null,
            fetched_at text not null,
            row_count integer not null,
            status text not null,
            error text
        );

        create table if not exists source_runs (
            id integer primary key autoincrement,
            source text not null,
            dataset text not null,
            started_at text not null,
            finished_at text,
            status text not null,
            rows integer,
            error text
        );

        create table if not exists stocks (
            code text primary key,
            name text,
            market text,
            industry text,
            updated_at text
        );

        create table if not exists market_cap_snapshot (
            code text not null,
            as_of_date text not null,
            name text,
            market_cap real,
            source text,
            updated_at text,
            primary key (code, as_of_date, source)
        );

        create table if not exists financial_reports (
            code text not null,
            report_date text not null,
            name text,
            industry text,
            revenue_yoy real,
            profit_yoy real,
            source text,
            updated_at text,
            primary key (code, report_date, source)
        );

        create table if not exists industry_members (
            board_name text not null,
            board_code text,
            code text not null,
            name text,
            source text,
            updated_at text,
            primary key (board_name, code, source)
        );

        create table if not exists quotes_daily (
            code text not null,
            trade_date text not null,
            open real,
            high real,
            low real,
            close real,
            volume real,
            amount real,
            source text,
            updated_at text,
            primary key (code, trade_date, source)
        );
        """
    )
    conn.commit()


def safe_table_name(key: str) -> str:
    safe = re.sub(r"[^0-9a-zA-Z_]+", "_", key).strip("_").lower()
    if not safe:
        safe = "table"
    if safe[0].isdigit():
        safe = f"t_{safe}"
    digest = sha1(key.encode("utf-8")).hexdigest()[:8]
    return f"raw_{safe}_{digest}"


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def read_table(conn: sqlite3.Connection, table_name: str) -> pd.DataFrame:
    return pd.read_sql_query(f'select * from "{table_name}"', conn)


def write_source_table(conn: sqlite3.Connection, table_key: str, source: str, df: pd.DataFrame) -> str:
    table_name = safe_table_name(table_key)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.execute(
        """
        insert into cache_meta(table_key, table_name, source, fetched_at, row_count, status, error)
        values(?, ?, ?, ?, ?, 'ok', null)
        on conflict(table_key) do update set
            table_name=excluded.table_name,
            source=excluded.source,
            fetched_at=excluded.fetched_at,
            row_count=excluded.row_count,
            status='ok',
            error=null
        """,
        (table_key, table_name, source, datetime.now().isoformat(timespec="seconds"), len(df)),
    )
    conn.commit()
    return table_name


def read_cached_source(conn: sqlite3.Connection, table_key: str) -> pd.DataFrame | None:
    row = conn.execute("select table_name from cache_meta where table_key=? and status='ok'", (table_key,)).fetchone()
    if not row:
        return None
    table_name = row[0]
    if not table_exists(conn, table_name):
        return None
    return read_table(conn, table_name)


def write_quotes_daily(conn: sqlite3.Connection, df: pd.DataFrame, source: str) -> int:
    if df.empty:
        return 0
    required = ["code", "trade_date", "open", "high", "low", "close", "volume", "amount"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise RuntimeError(f"quotes_daily missing columns: {missing}")
    now = datetime.now().isoformat(timespec="seconds")
    rows = []
    for row in df[required].itertuples(index=False):
        rows.append(
            (
                str(row.code),
                str(row.trade_date),
                float(row.open) if pd.notna(row.open) else None,
                float(row.high) if pd.notna(row.high) else None,
                float(row.low) if pd.notna(row.low) else None,
                float(row.close) if pd.notna(row.close) else None,
                float(row.volume) if pd.notna(row.volume) else None,
                float(row.amount) if pd.notna(row.amount) else None,
                source,
                now,
            )
        )
    conn.executemany(
        """
        insert into quotes_daily(code, trade_date, open, high, low, close, volume, amount, source, updated_at)
        values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(code, trade_date, source) do update set
            open=excluded.open,
            high=excluded.high,
            low=excluded.low,
            close=excluded.close,
            volume=excluded.volume,
            amount=excluded.amount,
            updated_at=excluded.updated_at
        """,
        rows,
    )
    conn.commit()
    return len(rows)
