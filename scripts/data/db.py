"""SQLite cache for source tables and normalized stock data."""

from __future__ import annotations

import json
import math
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

        create table if not exists index_constituents (
            index_symbol text not null,
            index_name text,
            constituent_date text not null,
            code text not null,
            name text,
            exchange text,
            weight real,
            weight_date text,
            source text,
            updated_at text,
            primary key (index_symbol, constituent_date, code, source)
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

        create table if not exists layer_runs (
            id integer primary key autoincrement,
            layer text not null,
            command text,
            strategy text,
            universe text,
            report_date text,
            run_at text not null,
            row_count integer not null,
            selected_count integer,
            status text not null,
            params_json text,
            meta_json text
        );

        create table if not exists layer_results (
            id integer primary key autoincrement,
            run_id integer not null references layer_runs(id) on delete cascade,
            layer text not null,
            rank integer not null,
            code text,
            name text,
            trade_date text,
            score real,
            action text,
            strategy text,
            row_json text not null,
            created_at text not null
        );

        create index if not exists idx_layer_runs_layer_run_at on layer_runs(layer, run_at);
        create index if not exists idx_layer_results_run_id on layer_results(run_id);
        create index if not exists idx_layer_results_code on layer_results(code);
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


def _json_clean(value):
    if isinstance(value, dict):
        return {str(k): _json_clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_clean(v) for v in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):
        try:
            return _json_clean(value.item())
        except Exception:
            pass
    return value


def _json_dumps(value) -> str:
    return json.dumps(_json_clean(value), ensure_ascii=False, sort_keys=True)


def _first_present(row: dict, names: list[str]):
    for name in names:
        value = row.get(name)
        if value is not None:
            try:
                if pd.isna(value):
                    continue
            except Exception:
                pass
            return value
    return None


def _as_float(value) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def write_layer_results(
    conn: sqlite3.Connection,
    layer: str,
    command: str,
    params: dict,
    meta: dict,
    df: pd.DataFrame,
    status: str = "ok",
) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    clean_df = df.astype(object).where(pd.notna(df), None) if df is not None else pd.DataFrame()
    rows = clean_df.to_dict(orient="records")
    strategy = str(_first_present(meta, ["plan", "strategy", "coarse_strategy"]) or "")
    universe = str(_first_present(meta, ["universe"]) or params.get("universe") or "")
    report_date = str(_first_present(meta, ["report_date"]) or params.get("report_date") or "")
    selected_count = meta.get("selected")
    try:
        selected_count = int(selected_count) if selected_count is not None else None
    except Exception:
        selected_count = None
    cur = conn.execute(
        """
        insert into layer_runs(
            layer, command, strategy, universe, report_date, run_at,
            row_count, selected_count, status, params_json, meta_json
        )
        values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            layer,
            command,
            strategy,
            universe,
            report_date,
            now,
            len(rows),
            selected_count,
            status,
            _json_dumps(params),
            _json_dumps(meta),
        ),
    )
    run_id = int(cur.lastrowid)
    result_rows = []
    for rank, row in enumerate(rows, start=1):
        code = _first_present(row, ["code"])
        trade_date = _first_present(row, ["latest_trade_date", "basis_trade_date", "trade_date"])
        score = _as_float(_first_present(row, ["technical_score", "combo_score", "coarse_score", "score"]))
        result_rows.append(
            (
                run_id,
                layer,
                rank,
                str(code).zfill(6) if code is not None else None,
                _first_present(row, ["name"]),
                str(trade_date) if trade_date is not None else None,
                score,
                _first_present(row, ["action"]),
                _first_present(row, ["primary_strategy", "coarse_strategy", "strategy"]),
                _json_dumps(row),
                now,
            )
        )
    conn.executemany(
        """
        insert into layer_results(
            run_id, layer, rank, code, name, trade_date, score, action,
            strategy, row_json, created_at
        )
        values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        result_rows,
    )
    conn.commit()
    return run_id


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


def write_index_constituents(conn: sqlite3.Connection, df: pd.DataFrame, source: str) -> int:
    if df.empty:
        return 0
    required = ["index_symbol", "constituent_date", "code"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise RuntimeError(f"index_constituents missing columns: {missing}")
    now = datetime.now().isoformat(timespec="seconds")
    optional_defaults = {
        "index_name": "",
        "name": "",
        "exchange": "",
        "weight": None,
        "weight_date": "",
    }
    def clean_text(value, default: str = "") -> str:
        if value is None or pd.isna(value):
            return default
        return str(value)

    rows = []
    for row in df.to_dict(orient="records"):
        rows.append(
            (
                clean_text(row["index_symbol"]),
                clean_text(row.get("index_name"), optional_defaults["index_name"]),
                clean_text(row["constituent_date"]),
                str(row["code"]).zfill(6),
                clean_text(row.get("name"), optional_defaults["name"]),
                clean_text(row.get("exchange"), optional_defaults["exchange"]),
                float(row["weight"]) if pd.notna(row.get("weight")) else None,
                clean_text(row.get("weight_date"), optional_defaults["weight_date"]),
                source,
                now,
            )
        )
    conn.executemany(
        """
        insert into index_constituents(
            index_symbol, index_name, constituent_date, code, name, exchange,
            weight, weight_date, source, updated_at
        )
        values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(index_symbol, constituent_date, code, source) do update set
            index_name=excluded.index_name,
            name=excluded.name,
            exchange=excluded.exchange,
            weight=excluded.weight,
            weight_date=excluded.weight_date,
            updated_at=excluded.updated_at
        """,
        rows,
    )
    conn.commit()
    return len(rows)
