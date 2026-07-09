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
from reports.repository import load_index_constituents as load_report_index_constituents
from reports.trade_plan_markdown import render_trade_plan
from infra.cache import read_index_constituents
from strategies.coarse.registry import STRATEGIES as COARSE_STRATEGIES
from strategies.coarse.registry import run as run_coarse
from strategies.coarse.registry import run_combo
from strategies.fine.technical import run as run_fine
from strategies import tech_growth
from plan.trade_plan import run_trade_plan
from infra.preflight import POLICIES, apply_update_policy


def add_common_screen_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--industry-rank", type=int, default=10)
    parser.add_argument("--min-revenue-yoy", type=float, default=0.0)
    parser.add_argument("--min-profit-yoy", type=float, default=0.0)
    parser.add_argument("--universe", choices=["tech", "csi300"], default="tech", help="Candidate universe: tech keyword pool or cached CSI 300 constituents.")
    parser.add_argument("--universe-index-symbol", default="000300", help="Index symbol used when --universe csi300.")
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sync = sub.add_parser("sync", help="Sync source data into the SQLite cache.")
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
    sync.add_argument("--skip-existing", action="store_true", help="For daily_prices, skip symbols that already cover the requested date range in SQLite.")
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
