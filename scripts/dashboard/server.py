"""Local HTTP server for recalculating dashboard snapshots by date."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from argparse import Namespace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pandas as pd

from common import db_path
from dashboard.pipeline import run_dashboard
from reports.dashboard_html import render_dashboard_html


def _clean_for_json(value):
    if isinstance(value, dict):
        return {str(key): _clean_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_for_json(item) for item in value]
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def _args_for_request(base_args: Namespace, query: dict[str, list[str]]) -> SimpleNamespace:
    data = vars(base_args).copy()
    as_of_values = query.get("as_of_date") or query.get("asOfDate") or [data.get("as_of_date", "")]
    data["as_of_date"] = str(as_of_values[0] or "").strip()
    backtest_values = query.get("backtest_date") or query.get("backtestDate") or [data.get("backtest_date", "")]
    data["backtest_date"] = str(backtest_values[0] or "").strip()
    for key in ["universe", "universe_index_symbol", "sector", "stock_types"]:
        values = query.get(key)
        if values:
            data[key] = str(values[0] or "").strip()
    data["command"] = "dashboard"
    return SimpleNamespace(**data)


def _dashboard_data_fingerprint() -> dict:
    path = db_path()
    if not path.exists():
        return {"db_path": str(path), "missing": True}
    tables = {
        "quotes_daily": ["trade_date", "updated_at"],
        "financial_reports": ["report_date", "updated_at"],
        "market_cap_snapshot": ["as_of_date", "updated_at"],
        "index_constituents": ["constituent_date", "weight_date", "updated_at"],
        "industry_members": ["updated_at"],
        "stocks": ["updated_at"],
    }
    conn = sqlite3.connect(path)
    try:
        fingerprint = {"db_path": str(path), "tables": {}}
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
            table_fingerprint = {"count": int(row[0] or 0)}
            for index, column in enumerate(selected_columns, start=1):
                table_fingerprint[f"max_{column}"] = row[index]
            fingerprint["tables"][table] = table_fingerprint
        return fingerprint
    except Exception:
        return {"db_path": str(path), "unavailable": True}
    finally:
        conn.close()


def _response_cache_key(path: str, args: SimpleNamespace) -> str:
    args_payload = {}
    for key, value in sorted(vars(args).items()):
        if key.startswith("_"):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            args_payload[key] = value
        elif isinstance(value, (list, tuple)):
            args_payload[key] = [str(item) for item in value]
        else:
            args_payload[key] = str(value)
    identity = {"path": path, "args": args_payload, "data": _dashboard_data_fingerprint()}
    raw = json.dumps(identity, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _build_dashboard_response(server, path: str, query: dict[str, list[str]]) -> tuple[int, str, str]:
    args = _args_for_request(server.base_args, query)
    cache = getattr(server, "response_cache", None)
    if cache is None:
        cache = {}
        server.response_cache = cache
    key = _response_cache_key(path, args)
    cached = cache.get(key)
    if cached is not None:
        return cached

    model = run_dashboard(args)
    if path == "/api/dashboard":
        response = (200, json.dumps(_clean_for_json(model), ensure_ascii=False), "application/json")
    else:
        response = (200, render_dashboard_html(model), "text/html")
    cache[key] = response
    if len(cache) > 20:
        oldest_key = next(iter(cache))
        cache.pop(oldest_key, None)
    return response


class DashboardRequestHandler(BaseHTTPRequestHandler):
    server_version = "TechGrowthDashboard/1.0"

    def _send_text(self, status: int, body: str, content_type: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, status: int, body: dict) -> None:
        self._send_text(status, json.dumps(_clean_for_json(body), ensure_ascii=False), "application/json")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path not in {"/", "/dashboard", "/api/dashboard"}:
            self._send_text(404, "Not found", "text/plain")
            return
        try:
            status, body, content_type = _build_dashboard_response(self.server, parsed.path, query)
            self._send_text(status, body, content_type)
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def log_message(self, format: str, *args) -> None:
        return


class DashboardServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_class, base_args: Namespace) -> None:
        super().__init__(server_address, handler_class)
        self.base_args = base_args
        self.response_cache = {}


def serve_dashboard(args: Namespace) -> None:
    host = getattr(args, "host", "127.0.0.1")
    port = int(getattr(args, "port", 5001))
    server = DashboardServer((host, port), DashboardRequestHandler, args)
    print(f"Dashboard server running at http://{host}:{port}/dashboard", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
