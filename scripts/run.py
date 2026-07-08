#!/usr/bin/env python3
"""Layered entry point for data sync, screening, and backtesting."""

from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from common import DEFAULT_KEYWORDS
from data.sources import sync_dataset
from infra.network import apply_network_policy
from reports.coarse_markdown import render_coarse
from reports.fine_markdown import render_fine
from reports.markdown import render_screen
from reports.trade_plan_markdown import render_trade_plan
from strategies.coarse.registry import STRATEGIES as COARSE_STRATEGIES
from strategies.coarse.registry import run as run_coarse
from strategies.fine.technical import run as run_fine
from strategies import tech_growth
from backtest.engine import run_equal_weight
from backtest.trade_plan import run_trade_plan


def add_common_screen_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--industry-rank", type=int, default=10)
    parser.add_argument("--min-revenue-yoy", type=float, default=0.0)
    parser.add_argument("--min-profit-yoy", type=float, default=0.0)
    parser.add_argument("--report-date", default="auto")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--no-proxy", action="store_true")
    parser.add_argument("--proxy", help="Explicit proxy URL, e.g. http://127.0.0.1:7890. Overrides TECH_GROWTH_PROXY.")
    parser.add_argument("--source", choices=["auto", "cache", "sina", "efinance", "akshare"], default="auto")
    parser.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sync = sub.add_parser("sync", help="Sync source data into the SQLite cache.")
    sync.add_argument("--dataset", choices=["spot", "financials", "industry_boards", "daily_prices"], default="spot")
    sync.add_argument("--report-date", default="auto")
    sync.add_argument("--refresh", action="store_true")
    sync.add_argument("--no-proxy", action="store_true")
    sync.add_argument("--proxy", help="Explicit proxy URL, e.g. http://127.0.0.1:7890. Overrides TECH_GROWTH_PROXY.")
    sync.add_argument("--source", choices=["auto", "cache", "sina", "efinance", "akshare"], default="auto")
    sync.add_argument("--codes", default="", help="Comma-separated stock codes for daily_prices sync.")
    sync.add_argument("--start", help="Start date for daily_prices, e.g. 2024-01-01.")
    sync.add_argument("--end", help="End date for daily_prices, e.g. 2026-07-08.")
    sync.add_argument("--adjust", choices=["", "qfq", "hfq"], default="qfq")
    sync.add_argument("--from-strategy", action="store_true", help="Use strategy output as daily_prices symbols.")
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

    coarse = sub.add_parser("coarse", help="Run coarse stock-screening strategies.")
    coarse.add_argument("--strategy", choices=["all", *COARSE_STRATEGIES.keys()], default="all")
    coarse.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown")
    add_common_screen_args(coarse)
    coarse.set_defaults(top=5)

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

    backtest = sub.add_parser("backtest", help="Backtest a strategy using cached daily prices.")
    backtest.add_argument("--strategy", choices=["tech_growth"], default="tech_growth")
    backtest.add_argument("--start", required=True)
    backtest.add_argument("--end", required=True)
    add_common_screen_args(backtest)

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
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "screen":
            result, stats = tech_growth.run(args)
            render_result(result, stats, args.format)
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
        if args.command == "backtest":
            result, stats = tech_growth.run(args)
            backtest_result = run_equal_weight(result, args.start, args.end, args.top)
            print(json.dumps({"screen_stats": stats.__dict__, "backtest": backtest_result}, ensure_ascii=False, indent=2))
            return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
