"""Persistence helpers for complete dashboard model snapshots."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from typing import Any

import pandas as pd

from common import db_path
from data.db import connect


SNAPSHOT_VERSION = 1

SNAPSHOT_ARG_KEYS = [
    "source",
    "strategy",
    "coarse_strategy",
    "universe",
    "universe_index_symbol",
    "sector",
    "stock_types",
    "stock_type_config",
    "report_date",
    "as_of_date",
    "backtest_date",
    "top",
    "sector_top",
    "combo_top",
    "combo_strategy_top",
    "coarse_top",
    "min_amount",
    "breakout_buffer",
    "volume_multiplier",
    "stop_pct",
    "atr_stop_multiplier",
    "max_gap_up",
    "move_stop_profit",
    "trailing_profit",
    "trailing_drawdown",
    "max_position",
    "backtest_top",
    "holding_days",
    "operation_profit_target",
    "recent_high_good_hits",
    "_skip_backtest",
    "_skip_signal_validation",
    "_skip_operation_backtest",
    "_skip_recent_high_good_hits",
]


def _json_clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_clean(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return _json_clean(value.item())
        except Exception:
            pass
    return value


def _json_dumps(value: Any) -> str:
    return json.dumps(_json_clean(value), ensure_ascii=False, sort_keys=True)


def _arg_value(args: Any, key: str) -> Any:
    value = getattr(args, key, "")
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return str(value)


def snapshot_params(args: Any) -> dict[str, Any]:
    return {key: _arg_value(args, key) for key in SNAPSHOT_ARG_KEYS}


def dashboard_data_fingerprint() -> dict:
    path = db_path()
    if not path.exists():
        return {"db_path": str(path), "missing": True}
    tables = {
        "cache_meta": ["fetched_at"],
        "quotes_daily": ["trade_date", "updated_at"],
        "financial_reports": ["report_date", "updated_at"],
        "market_cap_snapshot": ["as_of_date", "updated_at"],
        "index_constituents": ["constituent_date", "weight_date", "updated_at"],
        "industry_members": ["updated_at"],
        "stocks": ["updated_at"],
    }
    conn = sqlite3.connect(path)
    try:
        fingerprint: dict[str, Any] = {"db_path": str(path), "tables": {}}
        existing_tables = {
            str(row[0])
            for row in conn.execute("select name from sqlite_master where type='table'").fetchall()
        }
        for table, date_columns in tables.items():
            if table not in existing_tables:
                fingerprint["tables"][table] = {"missing": True}
                continue
            columns = {str(row[1]) for row in conn.execute(f"pragma table_info({table})").fetchall()}
            selected_columns = [column for column in date_columns if column in columns]
            expressions = ["count(*)", *[f"max({column})" for column in selected_columns]]
            row = conn.execute(f"select {', '.join(expressions)} from {table}").fetchone()
            table_fingerprint: dict[str, Any] = {"count": int(row[0] or 0)}
            for index, column in enumerate(selected_columns, start=1):
                table_fingerprint[f"max_{column}"] = row[index]
            fingerprint["tables"][table] = table_fingerprint
        return fingerprint
    except Exception:
        return {"db_path": str(path), "unavailable": True}
    finally:
        conn.close()


def snapshot_key(args: Any, data_fingerprint: dict | None = None) -> tuple[str, dict, dict]:
    params = snapshot_params(args)
    fingerprint = data_fingerprint or dashboard_data_fingerprint()
    identity = {
        "version": SNAPSHOT_VERSION,
        "params": params,
        "data": fingerprint,
    }
    raw = _json_dumps(identity)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest(), params, fingerprint


def dashboard_snapshot_enabled(args: Any) -> bool:
    if not bool(getattr(args, "dashboard_cache", False)):
        return False
    if bool(getattr(args, "refresh", False)):
        return False
    if str(getattr(args, "update_policy", "none") or "none") == "refresh":
        return False
    return True


def should_read_dashboard_snapshot(args: Any) -> bool:
    return dashboard_snapshot_enabled(args) and not bool(getattr(args, "rebuild_dashboard_cache", False))


def load_dashboard_snapshot(args: Any) -> dict | None:
    if not should_read_dashboard_snapshot(args):
        return None
    key, _params, _fingerprint = snapshot_key(args)
    conn = connect()
    try:
        row = conn.execute(
            """
            select model_json, created_at
            from dashboard_snapshots
            where snapshot_key=?
            """,
            (key,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    try:
        model = json.loads(row[0])
    except json.JSONDecodeError:
        return None
    model.setdefault("summary", {})["dashboard_snapshot"] = {
        "cache_status": "hit",
        "snapshot_key": key,
        "created_at": row[1],
    }
    return model


def save_dashboard_snapshot(args: Any, model: dict, html_path: str | None = None) -> str | None:
    if not dashboard_snapshot_enabled(args):
        return None
    key, params, fingerprint = snapshot_key(args)
    now = datetime.now().isoformat(timespec="seconds")
    summary = model.setdefault("summary", {})
    summary["dashboard_snapshot"] = {
        "cache_status": "saved",
        "snapshot_key": key,
        "created_at": now,
    }
    conn = connect()
    try:
        conn.execute(
            """
            insert into dashboard_snapshots(
                snapshot_key, as_of_date, backtest_date, universe, universe_index_symbol,
                sector, stock_types, report_date, source, created_at,
                data_fingerprint_json, params_json, model_json, html_path
            )
            values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(snapshot_key) do update set
                as_of_date=excluded.as_of_date,
                backtest_date=excluded.backtest_date,
                universe=excluded.universe,
                universe_index_symbol=excluded.universe_index_symbol,
                sector=excluded.sector,
                stock_types=excluded.stock_types,
                report_date=excluded.report_date,
                source=excluded.source,
                created_at=excluded.created_at,
                data_fingerprint_json=excluded.data_fingerprint_json,
                params_json=excluded.params_json,
                model_json=excluded.model_json,
                html_path=excluded.html_path
            """,
            (
                key,
                str(getattr(args, "as_of_date", "") or ""),
                str(getattr(args, "backtest_date", "") or getattr(args, "as_of_date", "") or ""),
                str(getattr(args, "universe", "") or ""),
                str(getattr(args, "universe_index_symbol", "") or ""),
                str(getattr(args, "sector", "") or ""),
                str(getattr(args, "stock_types", "") or ""),
                str(getattr(args, "report_date", "") or ""),
                str(getattr(args, "source", "") or ""),
                now,
                _json_dumps(fingerprint),
                _json_dumps(params),
                _json_dumps(model),
                html_path,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return key


__all__ = [
    "dashboard_data_fingerprint",
    "dashboard_snapshot_enabled",
    "load_dashboard_snapshot",
    "save_dashboard_snapshot",
    "should_read_dashboard_snapshot",
    "snapshot_key",
]
