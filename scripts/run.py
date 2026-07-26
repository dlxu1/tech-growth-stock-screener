#!/usr/bin/env python3
"""Layered entry point for data sync, screening, planning, and reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from common import DEFAULT_KEYWORDS, cache_dir
from data.sources import sync_dataset
from infra.network import apply_network_policy
from reports.coarse_markdown import render_coarse
from reports.combo_markdown import render_combo
from reports.coarse_html import render_coarse_html, render_combo_html
from reports.fine_html import render_fine_html
from reports.fine_markdown import render_fine
from reports.index_constituents_html import render_index_constituents_html
from reports.markdown import render_screen
from reports.operation_backtest_markdown import render_operation_backtest
from reports.repository import load_index_constituents as load_report_index_constituents
from reports.allocation_markdown import render_allocation_plan
from reports.dashboard_html import render_dashboard_html
from reports.dashboard_v2_html import render_dashboard_v2_html
from reports.sector_screen_markdown import render_sector_screen
from reports.signal_backtest_markdown import render_signal_backtest
from reports.signal_validation_markdown import render_signal_validation
from reports.trade_plan_markdown import render_trade_plan
from dashboard.health import audit_dashboard_model, render_health_markdown
from infra.cache import read_index_constituents
from strategies.coarse.registry import STRATEGIES as COARSE_STRATEGIES
from strategies.coarse.registry import run as run_coarse
from strategies.coarse.registry import run_combo
from strategies.fine.technical import run as run_fine
from strategies import tech_growth
from strategies import sector_screen
from dashboard.pipeline import run_dashboard
from dashboard.server import serve_dashboard
from allocation.personal_plan import run_allocation_plan
from backtest.operation_backtest import run_operation_backtest
from backtest.signal_backtest import run_signal_backtest, run_signal_validation
from plan.trade_plan import run_trade_plan
from infra.preflight import POLICIES, apply_update_policy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"


def _command_example(*args: str) -> str:
    script = Path(__file__).resolve()
    return " ".join([str(PROJECT_PYTHON), str(script), *args])


def add_common_screen_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--industry-rank", type=int, default=10)
    parser.add_argument("--min-revenue-yoy", type=float, default=0.0)
    parser.add_argument("--min-profit-yoy", type=float, default=0.0)
    parser.add_argument("--universe", choices=["tech", "csi300"], default="tech", help="Candidate universe: tech keyword pool or cached CSI 300 constituents.")
    parser.add_argument("--universe-index-symbol", default="000300", help="Index symbol used when --universe csi300.")
    parser.add_argument("--sector", default="", help="Comma-separated sector terms matched against board_name after the base universe is built.")
    parser.add_argument("--stock-type-config", default="", help="JSON config path for dashboard stock-type classification rules.")
    parser.add_argument("--stock-types", default="", help="Comma-separated stock types allowed to enter downstream dashboard stages, e.g. 科技股,周期股.")
    parser.add_argument("--as-of-date", default="", help="Historical dashboard cutoff date, e.g. 2026-06-30. Daily quotes after this date are ignored.")
    parser.add_argument("--report-date", default="auto")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--no-proxy", action="store_true")
    parser.add_argument("--proxy", help="Explicit proxy URL, e.g. http://127.0.0.1:7890. Overrides TECH_GROWTH_PROXY.")
    parser.add_argument("--source", choices=["auto", "cache", "sina", "efinance", "akshare", "baostock"], default="auto")
    parser.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS))
    parser.add_argument("--update-policy", choices=POLICIES, default="none", help="Pre-run data update policy: none keeps current behavior; cache forces offline cache; auto updates stale/missing data and continues on failures; strict stops on update failure; refresh forces relevant updates.")
    parser.add_argument("--update-start", help="Start date for pre-run daily price updates. Defaults to --update-end minus --update-daily-window-days.")
    parser.add_argument("--update-end", help="End date for pre-run daily price updates. Defaults to today.")
    parser.add_argument("--update-daily-window-days", type=int, default=180, help="Default daily price lookback window for pre-run updates.")
    parser.add_argument("--update-adjust", choices=["", "qfq", "hfq"], default="qfq", help="Adjustment mode for pre-run daily price updates.")
    parser.add_argument("--update-spot-max-age-days", type=int, default=1, help="Maximum accepted spot quote cache age before pre-run update.")
    parser.add_argument("--update-index-max-age-days", type=int, default=7, help="Maximum accepted index constituent cache age before pre-run update.")
    parser.add_argument("--no-persist-results", action="store_true", help="Do not persist this command's layer outputs into SQLite.")


def add_backtest_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--backtest-date", default="", help="Signal date used for fixed-horizon backtests. Defaults to --as-of-date.")
    parser.add_argument("--backtest-top", type=int, default=10, help="Top ranked stocks selected for each signal strategy.")
    parser.add_argument("--holding-days", default="7,14,21", help="Comma-separated holding horizons in trading days.")


def add_operation_backtest_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--operation-profit-target", type=float, default=0.05, help="Profit target for operation backtests, e.g. 0.05 means sell at +5%%.")


def add_dashboard_cache_args(parser: argparse.ArgumentParser) -> None:
    cache_group = parser.add_mutually_exclusive_group()
    cache_group.add_argument("--dashboard-cache", dest="dashboard_cache", action="store_true", default=True, help="Reuse and save complete dashboard model snapshots when request parameters and source-data fingerprints match.")
    cache_group.add_argument("--no-dashboard-cache", dest="dashboard_cache", action="store_false", help="Disable complete dashboard model snapshot reuse for this run.")
    parser.add_argument("--rebuild-dashboard-cache", action="store_true", help="Ignore any matching dashboard snapshot, rerun the pipeline, and replace the cached model.")


def add_recent_high_good_hits_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--with-recent-high-good-hits", dest="recent_high_good_hits", action="store_true", default=True, help="Enable the 30-day high-potential and good-timing hit-count annotation.")
    group.add_argument("--no-recent-high-good-hits", dest="recent_high_good_hits", action="store_false", help="Disable the 30-day high-potential and good-timing hit-count annotation.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sync = sub.add_parser(
        "sync",
        help="Sync source data into the SQLite cache.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "示例:\n"
            f"  {_command_example('sync', '--dataset', 'daily_prices', '--codes', '001309,688525,688498,301666,688766,300475,300857,688110', '--start', '2026-01-01', '--end', '2026-07-10', '--adjust', 'qfq', '--source', 'auto', '--no-proxy')}"
        ),
    )
    sync.add_argument("--dataset", choices=["spot", "financials", "industry_boards", "index_constituents", "daily_prices"], default="spot")
    sync.add_argument("--report-date", default="auto")
    sync.add_argument("--refresh", action="store_true")
    sync.add_argument("--no-proxy", action="store_true")
    sync.add_argument("--proxy", help="Explicit proxy URL, e.g. http://127.0.0.1:7890. Overrides TECH_GROWTH_PROXY.")
    sync.add_argument("--source", choices=["auto", "cache", "sina", "efinance", "akshare", "baostock"], default="auto")
    sync.add_argument("--codes", default="", help="Comma-separated stock codes for daily_prices sync.")
    sync.add_argument("--index-symbol", default="000300", help="Index symbol for index_constituents sync, e.g. 000300 for CSI 300.")
    sync.add_argument("--start", help="Start date for daily_prices, e.g. 2024-01-01.")
    sync.add_argument("--end", help="End date for daily_prices, e.g. 2026-07-08.")
    sync.add_argument("--adjust", choices=["", "qfq", "hfq"], default="qfq")
    sync.add_argument("--from-strategy", action="store_true", help="Use strategy output as daily_prices symbols.")
    sync.add_argument("--from-index", action="store_true", help="Use cached index constituents as daily_prices symbols.")
    sync.add_argument("--skip-existing", dest="skip_existing", action="store_true", default=True, help="For daily_prices, skip or shrink symbols that already cover the requested date range in SQLite. Enabled by default.")
    sync.add_argument("--no-skip-existing", dest="skip_existing", action="store_false", help="For daily_prices, force the full requested date range instead of incremental gap sync.")
    sync.add_argument("--strategy", choices=["tech_growth"], default="tech_growth")
    sync.add_argument("--top", type=int, default=10)
    sync.add_argument("--industry-rank", type=int, default=10)
    sync.add_argument("--min-revenue-yoy", type=float, default=0.0)
    sync.add_argument("--min-profit-yoy", type=float, default=0.0)
    sync.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS))

    screen = sub.add_parser("screen", help="Run a stock-selection strategy.")
    screen.add_argument("--strategy", choices=["tech_growth"], default="tech_growth")
    screen.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown")
    add_common_screen_args(screen)

    sector = sub.add_parser("sector-screen", help="Run a unified sector screen from a selected base universe.")
    sector.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown")
    add_common_screen_args(sector)
    sector.set_defaults(top=100)

    coarse = sub.add_parser("coarse", help="Run coarse stock-screening strategies.")
    coarse.add_argument("--strategy", choices=["all", *COARSE_STRATEGIES.keys()], default="all")
    coarse.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown")
    add_common_screen_args(coarse)
    coarse.set_defaults(top=5)

    combo = sub.add_parser("combo", help="Run potential-stock combo scoring across selected coarse strategies.")
    combo.add_argument("--combo-strategy-top", type=int, default=20, help="Candidates retained from each component strategy before aggregation.")
    combo.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown")
    add_common_screen_args(combo)
    combo.set_defaults(top=20)

    fine = sub.add_parser("fine", help="Run technical fine screening after coarse screening.")
    fine.add_argument("--coarse-strategy", choices=["all", *COARSE_STRATEGIES.keys()], default="all")
    fine.add_argument("--coarse-top", type=int, default=5)
    fine.add_argument("--min-amount", type=float, default=20000000.0, help="Minimum 20-day average turnover for liquidity scoring.")
    fine.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown")
    add_common_screen_args(fine)
    fine.set_defaults(top=10)

    plan = sub.add_parser("plan", help="Generate next-session trade plans for fine-screened stocks.")
    plan.add_argument("--coarse-strategy", choices=["all", *COARSE_STRATEGIES.keys()], default="all")
    plan.add_argument("--coarse-top", type=int, default=5)
    plan.add_argument("--min-amount", type=float, default=20000000.0, help="Minimum 20-day average turnover for liquidity scoring.")
    plan.add_argument("--breakout-buffer", type=float, default=0.003, help="Breakout trigger buffer above recent high.")
    plan.add_argument("--volume-multiplier", type=float, default=1.2, help="Turnover multiple required for volume confirmation.")
    plan.add_argument("--stop-pct", type=float, default=0.05, help="Fixed stop percentage below planned entry.")
    plan.add_argument("--atr-stop-multiplier", type=float, default=1.5, help="ATR multiple for stop placement.")
    plan.add_argument("--max-gap-up", type=float, default=0.05, help="Cancel chasing if next open gaps above latest close by this amount.")
    plan.add_argument("--move-stop-profit", type=float, default=0.05, help="Profit threshold for moving stop to cost.")
    plan.add_argument("--trailing-profit", type=float, default=0.08, help="Profit threshold for enabling trailing stop.")
    plan.add_argument("--trailing-drawdown", type=float, default=0.06, help="Drawdown from highest close for trailing stop.")
    plan.add_argument("--max-position", type=float, default=0.25, help="Maximum single-stock position cap.")
    plan.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown")
    add_common_screen_args(plan)
    plan.set_defaults(top=5)

    allocation = sub.add_parser("allocation", help="Generate a personal ETF/core plus stock/satellite allocation plan.")
    allocation.add_argument("--coarse-strategy", choices=["all", *COARSE_STRATEGIES.keys()], default="all")
    allocation.add_argument("--coarse-top", type=int, default=5)
    allocation.add_argument("--min-amount", type=float, default=20000000.0, help="Minimum 20-day average turnover for liquidity scoring.")
    allocation.add_argument("--breakout-buffer", type=float, default=0.003, help="Breakout trigger buffer above recent high.")
    allocation.add_argument("--volume-multiplier", type=float, default=1.2, help="Turnover multiple required for volume confirmation.")
    allocation.add_argument("--stop-pct", type=float, default=0.05, help="Fixed stop percentage below planned entry.")
    allocation.add_argument("--atr-stop-multiplier", type=float, default=1.5, help="ATR multiple for stop placement.")
    allocation.add_argument("--max-gap-up", type=float, default=0.05, help="Cancel chasing if next open gaps above latest close by this amount.")
    allocation.add_argument("--move-stop-profit", type=float, default=0.05, help="Profit threshold for moving stop to cost.")
    allocation.add_argument("--trailing-profit", type=float, default=0.08, help="Profit threshold for enabling trailing stop.")
    allocation.add_argument("--trailing-drawdown", type=float, default=0.06, help="Drawdown from highest close for trailing stop.")
    allocation.add_argument("--max-position", type=float, default=0.25, help="Maximum plan-layer single-stock position cap.")
    allocation.add_argument("--capital", type=float, default=15000.0, help="Personal account capital in CNY.")
    allocation.add_argument("--target-return", type=float, default=0.10, help="Annual target return used for planning context.")
    allocation.add_argument("--core-etf-pct", type=float, default=0.60, help="Capital share reserved for technology ETF core position.")
    allocation.add_argument("--satellite-stock-pct", type=float, default=0.20, help="Capital share reserved for individual technology stocks.")
    allocation.add_argument("--cash-pct", type=float, default=0.20, help="Capital share kept as cash reserve.")
    allocation.add_argument("--etf-tranches", type=int, default=3, help="Number of ETF buying tranches.")
    allocation.add_argument("--initial-single-stock-pct", type=float, default=0.12, help="First-buy budget cap for one stock.")
    allocation.add_argument("--max-single-stock-pct", type=float, default=0.20, help="Maximum personal-account cap for one stock.")
    allocation.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown")
    add_common_screen_args(allocation)
    allocation.set_defaults(top=5)

    dashboard = sub.add_parser(
        "dashboard",
        help="Generate one interactive HTML report for all pipeline stages.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "示例:\n"
            f"  {_command_example('dashboard', '--source', 'cache', '--output', str(Path(__file__).resolve().parents[1] / '.cache' / 'reports' / 'dashboard_latest.html'))}"
        ),
    )
    dashboard.add_argument("--strategy", choices=["tech_growth"], default="tech_growth")
    dashboard.add_argument("--coarse-strategy", choices=["all", *COARSE_STRATEGIES.keys()], default="all")
    dashboard.add_argument("--coarse-top", type=int, default=5)
    dashboard.add_argument("--combo-strategy-top", type=int, default=20, help="Candidates retained from each combo component strategy before aggregation.")
    dashboard.add_argument("--min-amount", type=float, default=20000000.0, help="Minimum 20-day average turnover for liquidity scoring.")
    dashboard.add_argument("--breakout-buffer", type=float, default=0.003, help="Breakout trigger buffer above recent high.")
    dashboard.add_argument("--volume-multiplier", type=float, default=1.2, help="Turnover multiple required for volume confirmation.")
    dashboard.add_argument("--stop-pct", type=float, default=0.05, help="Fixed stop percentage below planned entry.")
    dashboard.add_argument("--atr-stop-multiplier", type=float, default=1.5, help="ATR multiple for stop placement.")
    dashboard.add_argument("--max-gap-up", type=float, default=0.05, help="Cancel chasing if next open gaps above latest close by this amount.")
    dashboard.add_argument("--move-stop-profit", type=float, default=0.05, help="Profit threshold for moving stop to cost.")
    dashboard.add_argument("--trailing-profit", type=float, default=0.08, help="Profit threshold for enabling trailing stop.")
    dashboard.add_argument("--trailing-drawdown", type=float, default=0.06, help="Drawdown from highest close for trailing stop.")
    dashboard.add_argument("--max-position", type=float, default=0.25, help="Maximum plan-layer single-stock position cap.")
    dashboard.add_argument("--sector-top", type=int, default=100, help="Maximum rows retained in the dashboard sector-screen stage.")
    dashboard.add_argument("--combo-top", type=int, default=100, help="Maximum rows retained in the dashboard macro coarse stage.")
    dashboard.add_argument("--format", choices=["html"], default="html")
    dashboard.add_argument("--output", help="HTML output path. Defaults to .cache/reports/dashboard_latest.html.")
    add_backtest_args(dashboard)
    add_operation_backtest_args(dashboard)
    add_common_screen_args(dashboard)
    add_dashboard_cache_args(dashboard)
    add_recent_high_good_hits_args(dashboard)
    dashboard.set_defaults(top=5, universe="csi300", dashboard_variant="v1")

    dashboardv2 = sub.add_parser(
        "dashboardv2",
        help="Generate the industry-thesis dashboard v2 HTML report.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "示例:\n"
            f"  {_command_example('dashboardv2', '--source', 'cache', '--output', str(Path(__file__).resolve().parents[1] / '.cache' / 'reports' / 'dashboard_v2_latest.html'))}"
        ),
    )
    dashboardv2.add_argument("--strategy", choices=["tech_growth"], default="tech_growth")
    dashboardv2.add_argument("--coarse-strategy", choices=["all", *COARSE_STRATEGIES.keys()], default="all")
    dashboardv2.add_argument("--coarse-top", type=int, default=5)
    dashboardv2.add_argument("--combo-strategy-top", type=int, default=20, help="Candidates retained from each combo component strategy before aggregation.")
    dashboardv2.add_argument("--min-amount", type=float, default=20000000.0, help="Minimum 20-day average turnover for liquidity scoring.")
    dashboardv2.add_argument("--breakout-buffer", type=float, default=0.003, help="Breakout trigger buffer above recent high.")
    dashboardv2.add_argument("--volume-multiplier", type=float, default=1.2, help="Turnover multiple required for volume confirmation.")
    dashboardv2.add_argument("--stop-pct", type=float, default=0.05, help="Fixed stop percentage below planned entry.")
    dashboardv2.add_argument("--atr-stop-multiplier", type=float, default=1.5, help="ATR multiple for stop placement.")
    dashboardv2.add_argument("--max-gap-up", type=float, default=0.05, help="Cancel chasing if next open gaps above latest close by this amount.")
    dashboardv2.add_argument("--move-stop-profit", type=float, default=0.05, help="Profit threshold for moving stop to cost.")
    dashboardv2.add_argument("--trailing-profit", type=float, default=0.08, help="Profit threshold for enabling trailing stop.")
    dashboardv2.add_argument("--trailing-drawdown", type=float, default=0.06, help="Drawdown from highest close for trailing stop.")
    dashboardv2.add_argument("--max-position", type=float, default=0.25, help="Maximum plan-layer single-stock position cap.")
    dashboardv2.add_argument("--sector-top", type=int, default=100, help="Maximum rows retained in the dashboard sector-screen stage.")
    dashboardv2.add_argument("--combo-top", type=int, default=100, help="Maximum rows retained in the dashboard macro coarse stage.")
    dashboardv2.add_argument("--format", choices=["html"], default="html")
    dashboardv2.add_argument("--output", help="HTML output path. Defaults to .cache/reports/dashboard_v2_latest.html.")
    add_backtest_args(dashboardv2)
    add_operation_backtest_args(dashboardv2)
    add_common_screen_args(dashboardv2)
    add_dashboard_cache_args(dashboardv2)
    add_recent_high_good_hits_args(dashboardv2)
    dashboardv2.set_defaults(top=5, universe="csi300", dashboard_variant="v2")

    dashboard_server = sub.add_parser(
        "dashboard-server",
        help="Serve the interactive dashboard locally and recalculate it when the as-of date changes.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "示例:\n"
            f"  {_command_example('dashboard-server', '--source', 'cache', '--host', '127.0.0.1', '--port', '5001')}"
        ),
    )
    dashboard_server.add_argument("--strategy", choices=["tech_growth"], default="tech_growth")
    dashboard_server.add_argument("--coarse-strategy", choices=["all", *COARSE_STRATEGIES.keys()], default="all")
    dashboard_server.add_argument("--coarse-top", type=int, default=5)
    dashboard_server.add_argument("--combo-strategy-top", type=int, default=20, help="Candidates retained from each combo component strategy before aggregation.")
    dashboard_server.add_argument("--min-amount", type=float, default=20000000.0, help="Minimum 20-day average turnover for liquidity scoring.")
    dashboard_server.add_argument("--breakout-buffer", type=float, default=0.003, help="Breakout trigger buffer above recent high.")
    dashboard_server.add_argument("--volume-multiplier", type=float, default=1.2, help="Turnover multiple required for volume confirmation.")
    dashboard_server.add_argument("--stop-pct", type=float, default=0.05, help="Fixed stop percentage below planned entry.")
    dashboard_server.add_argument("--atr-stop-multiplier", type=float, default=1.5, help="ATR multiple for stop placement.")
    dashboard_server.add_argument("--max-gap-up", type=float, default=0.05, help="Cancel chasing if next open gaps above latest close by this amount.")
    dashboard_server.add_argument("--move-stop-profit", type=float, default=0.05, help="Profit threshold for moving stop to cost.")
    dashboard_server.add_argument("--trailing-profit", type=float, default=0.08, help="Profit threshold for enabling trailing stop.")
    dashboard_server.add_argument("--trailing-drawdown", type=float, default=0.06, help="Drawdown from highest close for trailing stop.")
    dashboard_server.add_argument("--max-position", type=float, default=0.25, help="Maximum plan-layer single-stock position cap.")
    dashboard_server.add_argument("--sector-top", type=int, default=100, help="Maximum rows retained in the dashboard sector-screen stage.")
    dashboard_server.add_argument("--combo-top", type=int, default=100, help="Maximum rows retained in the dashboard macro coarse stage.")
    dashboard_server.add_argument("--host", default="127.0.0.1", help="Local host address for the dashboard server.")
    dashboard_server.add_argument("--port", type=int, default=5001, help="Local port for the dashboard server.")
    add_backtest_args(dashboard_server)
    add_operation_backtest_args(dashboard_server)
    add_common_screen_args(dashboard_server)
    add_dashboard_cache_args(dashboard_server)
    add_recent_high_good_hits_args(dashboard_server)
    dashboard_server.set_defaults(top=5, universe="csi300")

    validate_dashboard = sub.add_parser(
        "validate-dashboard",
        help="Run data-health checks for the dashboard pipeline.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "示例:\n"
            f"  {_command_example('validate-dashboard', '--source', 'cache', '--expected-latest-trade-date', '2026-07-10')}"
        ),
    )
    validate_dashboard.add_argument("--strategy", choices=["tech_growth"], default="tech_growth")
    validate_dashboard.add_argument("--coarse-strategy", choices=["all", *COARSE_STRATEGIES.keys()], default="all")
    validate_dashboard.add_argument("--coarse-top", type=int, default=5)
    validate_dashboard.add_argument("--combo-strategy-top", type=int, default=20, help="Candidates retained from each combo component strategy before aggregation.")
    validate_dashboard.add_argument("--min-amount", type=float, default=20000000.0, help="Minimum 20-day average turnover for liquidity scoring.")
    validate_dashboard.add_argument("--breakout-buffer", type=float, default=0.003, help="Breakout trigger buffer above recent high.")
    validate_dashboard.add_argument("--volume-multiplier", type=float, default=1.2, help="Turnover multiple required for volume confirmation.")
    validate_dashboard.add_argument("--stop-pct", type=float, default=0.05, help="Fixed stop percentage below planned entry.")
    validate_dashboard.add_argument("--atr-stop-multiplier", type=float, default=1.5, help="ATR multiple for stop placement.")
    validate_dashboard.add_argument("--max-gap-up", type=float, default=0.05, help="Cancel chasing if next open gaps above latest close by this amount.")
    validate_dashboard.add_argument("--move-stop-profit", type=float, default=0.05, help="Profit threshold for moving stop to cost.")
    validate_dashboard.add_argument("--trailing-profit", type=float, default=0.08, help="Profit threshold for enabling trailing stop.")
    validate_dashboard.add_argument("--trailing-drawdown", type=float, default=0.06, help="Drawdown from highest close for trailing stop.")
    validate_dashboard.add_argument("--max-position", type=float, default=0.25, help="Maximum plan-layer single-stock position cap.")
    validate_dashboard.add_argument("--sector-top", type=int, default=100, help="Maximum rows retained in the dashboard sector-screen stage.")
    validate_dashboard.add_argument("--combo-top", type=int, default=100, help="Maximum rows retained in the dashboard macro coarse stage.")
    validate_dashboard.add_argument("--expected-latest-trade-date", help="Expected latest trade date, e.g. 2026-07-10.")
    validate_dashboard.add_argument("--format", choices=["markdown", "json"], default="markdown")
    add_common_screen_args(validate_dashboard)
    add_dashboard_cache_args(validate_dashboard)
    add_recent_high_good_hits_args(validate_dashboard)
    validate_dashboard.set_defaults(top=5, universe="csi300")

    signal_backtest = sub.add_parser(
        "signal-backtest",
        help="Backtest single-date dashboard score signals over fixed holding horizons.",
    )
    signal_backtest.add_argument("--strategy", choices=["tech_growth"], default="tech_growth")
    signal_backtest.add_argument("--coarse-strategy", choices=["all", *COARSE_STRATEGIES.keys()], default="all")
    signal_backtest.add_argument("--coarse-top", type=int, default=5)
    signal_backtest.add_argument("--combo-strategy-top", type=int, default=20)
    signal_backtest.add_argument("--min-amount", type=float, default=20000000.0)
    signal_backtest.add_argument("--breakout-buffer", type=float, default=0.003)
    signal_backtest.add_argument("--volume-multiplier", type=float, default=1.2)
    signal_backtest.add_argument("--stop-pct", type=float, default=0.05)
    signal_backtest.add_argument("--atr-stop-multiplier", type=float, default=1.5)
    signal_backtest.add_argument("--max-gap-up", type=float, default=0.05)
    signal_backtest.add_argument("--move-stop-profit", type=float, default=0.05)
    signal_backtest.add_argument("--trailing-profit", type=float, default=0.08)
    signal_backtest.add_argument("--trailing-drawdown", type=float, default=0.06)
    signal_backtest.add_argument("--max-position", type=float, default=0.25)
    signal_backtest.add_argument("--sector-top", type=int, default=100)
    signal_backtest.add_argument("--combo-top", type=int, default=100)
    add_backtest_args(signal_backtest)
    signal_backtest.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown")
    add_common_screen_args(signal_backtest)
    signal_backtest.set_defaults(top=5, universe="csi300")

    signal_validate = sub.add_parser(
        "signal-validate",
        help="Validate dashboard score signals by matrix quadrant and attention-score buckets.",
    )
    signal_validate.add_argument("--strategy", choices=["tech_growth"], default="tech_growth")
    signal_validate.add_argument("--coarse-strategy", choices=["all", *COARSE_STRATEGIES.keys()], default="all")
    signal_validate.add_argument("--coarse-top", type=int, default=5)
    signal_validate.add_argument("--combo-strategy-top", type=int, default=20)
    signal_validate.add_argument("--min-amount", type=float, default=20000000.0)
    signal_validate.add_argument("--breakout-buffer", type=float, default=0.003)
    signal_validate.add_argument("--volume-multiplier", type=float, default=1.2)
    signal_validate.add_argument("--stop-pct", type=float, default=0.05)
    signal_validate.add_argument("--atr-stop-multiplier", type=float, default=1.5)
    signal_validate.add_argument("--max-gap-up", type=float, default=0.05)
    signal_validate.add_argument("--move-stop-profit", type=float, default=0.05)
    signal_validate.add_argument("--trailing-profit", type=float, default=0.08)
    signal_validate.add_argument("--trailing-drawdown", type=float, default=0.06)
    signal_validate.add_argument("--max-position", type=float, default=0.25)
    signal_validate.add_argument("--sector-top", type=int, default=100)
    signal_validate.add_argument("--combo-top", type=int, default=100)
    signal_validate.add_argument("--validation-start", default="", help="First signal date for batch validation, e.g. 2026-01-01.")
    signal_validate.add_argument("--validation-end", default="", help="Last signal date for batch validation, e.g. 2026-06-30.")
    signal_validate.add_argument("--validation-step-days", type=int, default=20, help="Calendar-day spacing between sampled signal dates.")
    signal_validate.add_argument("--bucket-size", type=int, default=10, help="Number of stocks per attention-score bucket.")
    add_backtest_args(signal_validate)
    signal_validate.add_argument("--format", choices=["markdown", "json"], default="markdown")
    add_common_screen_args(signal_validate)
    signal_validate.set_defaults(top=5, universe="csi300")

    operation_backtest = sub.add_parser(
        "operation-backtest",
        help="Backtest high-potential good-timing dashboard operation plans using trigger, stop, and profit-target rules.",
    )
    operation_backtest.add_argument("--strategy", choices=["tech_growth"], default="tech_growth")
    operation_backtest.add_argument("--coarse-strategy", choices=["all", *COARSE_STRATEGIES.keys()], default="all")
    operation_backtest.add_argument("--coarse-top", type=int, default=5)
    operation_backtest.add_argument("--combo-strategy-top", type=int, default=20)
    operation_backtest.add_argument("--min-amount", type=float, default=20000000.0)
    operation_backtest.add_argument("--breakout-buffer", type=float, default=0.003)
    operation_backtest.add_argument("--volume-multiplier", type=float, default=1.2)
    operation_backtest.add_argument("--stop-pct", type=float, default=0.05)
    operation_backtest.add_argument("--atr-stop-multiplier", type=float, default=1.5)
    operation_backtest.add_argument("--max-gap-up", type=float, default=0.05)
    operation_backtest.add_argument("--move-stop-profit", type=float, default=0.05)
    operation_backtest.add_argument("--trailing-profit", type=float, default=0.08)
    operation_backtest.add_argument("--trailing-drawdown", type=float, default=0.06)
    operation_backtest.add_argument("--max-position", type=float, default=0.25)
    operation_backtest.add_argument("--sector-top", type=int, default=100)
    operation_backtest.add_argument("--combo-top", type=int, default=100)
    add_backtest_args(operation_backtest)
    add_operation_backtest_args(operation_backtest)
    operation_backtest.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown")
    add_common_screen_args(operation_backtest)
    operation_backtest.set_defaults(top=5, universe="csi300")

    visualize = sub.add_parser("visualize", help="Generate local visual reports from the SQLite cache.")
    visualize.add_argument("--dataset", choices=["index_constituents", "coarse", "combo", "fine"], default="index_constituents")
    visualize.add_argument("--index-symbol", default="000300")
    visualize.add_argument("--constituent-date", default="latest")
    visualize.add_argument("--strategy", choices=["all", *COARSE_STRATEGIES.keys()], default="all")
    visualize.add_argument("--coarse-strategy", choices=["all", *COARSE_STRATEGIES.keys()], default="all")
    visualize.add_argument("--coarse-top", type=int, default=5)
    visualize.add_argument("--min-amount", type=float, default=20000000.0, help="Minimum 20-day average turnover for fine scoring.")
    visualize.add_argument("--combo-strategy-top", type=int, default=20)
    add_common_screen_args(visualize)
    visualize.add_argument("--output", help="HTML output path. Defaults to .cache/reports/index_constituents_<symbol>.html.")

    return parser.parse_args()


def render_result(df, stats, output_format: str) -> None:
    if output_format == "json":
        clean = df.astype(object).where(pd.notna(df), None)
        print(json.dumps({"stats": stats.__dict__, "data": clean.to_dict(orient="records")}, ensure_ascii=False, indent=2))
    elif output_format == "csv":
        df.to_csv(sys.stdout, index=False)
    else:
        print(render_screen(df, stats))


def main() -> int:
    args = parse_args()
    apply_network_policy(getattr(args, "no_proxy", False), getattr(args, "proxy", None))
    try:
        if args.command == "sync":
            codes = [code.strip() for code in getattr(args, "codes", "").split(",") if code.strip()]
            if args.dataset == "daily_prices" and args.from_strategy:
                candidates, _ = tech_growth.run(args)
                codes = candidates.head(args.top)["code"].astype(str).tolist()
            if args.dataset == "daily_prices" and args.from_index:
                members = read_index_constituents(getattr(args, "index_symbol", "000300"))
                if members.empty:
                    raise RuntimeError("No cached index constituents found. Run sync --dataset index_constituents first.")
                codes = members["code"].astype(str).str.zfill(6).tolist()
            result = sync_dataset(
                args.dataset,
                args.report_date,
                args.refresh,
                args.no_proxy,
                args.source,
                codes=codes,
                start=getattr(args, "start", None),
                end=getattr(args, "end", None),
                adjust=getattr(args, "adjust", "qfq"),
                index_symbol=getattr(args, "index_symbol", "000300"),
                skip_existing=getattr(args, "skip_existing", False),
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        apply_update_policy(args)
        if args.command == "screen":
            result, stats = tech_growth.run(args)
            render_result(result, stats, args.format)
            return 0
        if args.command == "sector-screen":
            result, meta = sector_screen.run(args)
            if args.format == "json":
                clean = result.astype(object).where(pd.notna(result), None)
                print(json.dumps({"meta": meta, "data": clean.to_dict(orient="records")}, ensure_ascii=False, indent=2))
            elif args.format == "csv":
                result.to_csv(sys.stdout, index=False)
            else:
                print(render_sector_screen(result, meta))
            return 0
        if args.command == "coarse":
            result, meta = run_coarse(args)
            if args.format == "json":
                clean = result.astype(object).where(pd.notna(result), None)
                print(json.dumps({"meta": meta, "data": clean.to_dict(orient="records")}, ensure_ascii=False, indent=2))
            elif args.format == "csv":
                result.to_csv(sys.stdout, index=False)
            else:
                print(render_coarse(result, meta))
            return 0
        if args.command == "combo":
            result, meta = run_combo(args)
            if args.format == "json":
                clean = result.astype(object).where(pd.notna(result), None)
                print(json.dumps({"meta": meta, "data": clean.to_dict(orient="records")}, ensure_ascii=False, indent=2))
            elif args.format == "csv":
                result.to_csv(sys.stdout, index=False)
            else:
                print(render_combo(result, meta))
            return 0
        if args.command == "fine":
            result, meta = run_fine(args)
            if args.format == "json":
                clean = result.astype(object).where(pd.notna(result), None)
                print(json.dumps({"meta": meta, "data": clean.to_dict(orient="records")}, ensure_ascii=False, indent=2))
            elif args.format == "csv":
                result.to_csv(sys.stdout, index=False)
            else:
                print(render_fine(result, meta))
            return 0
        if args.command == "plan":
            result, meta = run_trade_plan(args)
            if args.format == "json":
                clean = result.astype(object).where(pd.notna(result), None)
                print(json.dumps({"meta": meta, "data": clean.to_dict(orient="records")}, ensure_ascii=False, indent=2))
            elif args.format == "csv":
                result.to_csv(sys.stdout, index=False)
            else:
                print(render_trade_plan(result, meta))
            return 0
        if args.command == "allocation":
            result, meta = run_allocation_plan(args)
            if args.format == "json":
                clean = result.astype(object).where(pd.notna(result), None)
                print(json.dumps({"meta": meta, "data": clean.to_dict(orient="records")}, ensure_ascii=False, indent=2))
            elif args.format == "csv":
                result.to_csv(sys.stdout, index=False)
            else:
                print(render_allocation_plan(result, meta))
            return 0
        if args.command == "dashboard":
            model = run_dashboard(args)
            output = Path(args.output) if args.output else cache_dir() / "reports" / "dashboard_latest.html"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(render_dashboard_html(model), encoding="utf-8")
            print(json.dumps({"output": str(output.resolve()), "stages": len(model.get("stages", []))}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "dashboardv2":
            model = run_dashboard(args)
            output = Path(args.output) if args.output else cache_dir() / "reports" / "dashboard_v2_latest.html"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(render_dashboard_v2_html(model), encoding="utf-8")
            print(json.dumps({"output": str(output.resolve()), "stages": len(model.get("stages", [])), "variant": "v2"}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "dashboard-server":
            serve_dashboard(args)
            return 0
        if args.command == "validate-dashboard":
            model = run_dashboard(args)
            audit = audit_dashboard_model(model, expected_latest_trade_date=getattr(args, "expected_latest_trade_date", None))
            if args.format == "json":
                print(json.dumps(audit, ensure_ascii=False, indent=2))
            else:
                print(render_health_markdown(audit))
            return 0
        if args.command == "signal-backtest":
            model = run_signal_backtest(args)
            if args.format == "json":
                print(json.dumps(model, ensure_ascii=False, indent=2))
            elif args.format == "csv":
                frames = []
                for strategy in model.get("strategies", []):
                    frame = pd.DataFrame(strategy.get("rows", []))
                    if not frame.empty:
                        frame.insert(0, "strategy_title", strategy.get("title", ""))
                        frames.append(frame)
                result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
                result.to_csv(sys.stdout, index=False)
            else:
                print(render_signal_backtest(model))
            return 0
        if args.command == "signal-validate":
            model = run_signal_validation(args)
            if args.format == "json":
                print(json.dumps(model, ensure_ascii=False, indent=2))
            else:
                print(render_signal_validation(model))
            return 0
        if args.command == "operation-backtest":
            model = run_operation_backtest(args)
            if args.format == "json":
                print(json.dumps(model, ensure_ascii=False, indent=2))
            elif args.format == "csv":
                pd.DataFrame(model.get("rows", [])).to_csv(sys.stdout, index=False)
            else:
                print(render_operation_backtest(model))
            return 0
        if args.command == "visualize":
            if args.dataset == "index_constituents":
                df, meta = load_report_index_constituents(args.index_symbol, args.constituent_date)
                output = Path(args.output) if args.output else cache_dir() / "reports" / f"index_constituents_{args.index_symbol}.html"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(render_index_constituents_html(df, meta), encoding="utf-8")
                print(json.dumps({"dataset": args.dataset, "rows": len(df), "output": str(output.resolve()), **meta}, ensure_ascii=False, indent=2))
                return 0
            if args.dataset == "coarse":
                result, meta = run_coarse(args)
                output = Path(args.output) if args.output else cache_dir() / "reports" / "coarse_all.html"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(render_coarse_html(result, meta), encoding="utf-8")
                print(json.dumps({"dataset": args.dataset, "rows": len(result), "output": str(output.resolve()), **meta}, ensure_ascii=False, indent=2))
                return 0
            if args.dataset == "combo":
                result, meta = run_combo(args)
                output = Path(args.output) if args.output else cache_dir() / "reports" / "combo.html"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(render_combo_html(result, meta), encoding="utf-8")
                print(json.dumps({"dataset": args.dataset, "rows": len(result), "output": str(output.resolve()), **meta}, ensure_ascii=False, indent=2))
                return 0
            if args.dataset == "fine":
                result, meta = run_fine(args)
                output = Path(args.output) if args.output else cache_dir() / "reports" / "fine.html"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(render_fine_html(result, meta), encoding="utf-8")
                print(json.dumps({"dataset": args.dataset, "rows": len(result), "output": str(output.resolve()), **meta}, ensure_ascii=False, indent=2))
                return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
