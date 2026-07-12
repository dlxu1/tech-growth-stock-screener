"""Local HTTP server for recalculating dashboard snapshots by date."""

from __future__ import annotations

import json
from argparse import Namespace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pandas as pd

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
        args = _args_for_request(self.server.base_args, query)
        try:
            model = run_dashboard(args)
            if parsed.path == "/api/dashboard":
                self._send_json(200, model)
            else:
                self._send_text(200, render_dashboard_html(model), "text/html")
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def log_message(self, format: str, *args) -> None:
        return


class DashboardServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_class, base_args: Namespace) -> None:
        super().__init__(server_address, handler_class)
        self.base_args = base_args


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
