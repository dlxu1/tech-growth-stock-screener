#!/usr/bin/env python3
"""Backward-compatible wrapper for the tech-growth screen command."""

from __future__ import annotations

import argparse
import json
import sys

from common import DEFAULT_KEYWORDS, apply_network_policy
from reports.markdown import render_screen
from strategies.tech_growth import run as run_tech_growth


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=30, help="Number of passing candidates to show.")
    parser.add_argument("--industry-rank", type=int, default=10, help="Required max market-cap rank inside each tech board.")
    parser.add_argument("--min-revenue-yoy", type=float, default=0.0, help="Minimum revenue YoY growth percentage.")
    parser.add_argument("--min-profit-yoy", type=float, default=0.0, help="Minimum net-profit YoY growth percentage.")
    parser.add_argument("--report-date", default="auto", help="Financial report date, e.g. 20260331, or auto.")
    parser.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown")
    parser.add_argument("--refresh", action="store_true", help="Ignore cached source tables.")
    parser.add_argument("--no-proxy", action="store_true", help="Force direct requests and bypass system/env proxies.")
    parser.add_argument("--proxy", help="Explicit proxy URL, e.g. http://127.0.0.1:7890. Overrides TECH_GROWTH_PROXY.")
    parser.add_argument(
        "--source",
        choices=["auto", "cache", "sina", "efinance", "akshare"],
        default="auto",
        help="Preferred remote source after cache lookup. auto tries Sina quotes, then efinance, then AKShare/Eastmoney.",
    )
    parser.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS), help="Comma-separated technology board keywords.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    apply_network_policy(args.no_proxy, args.proxy)
    try:
        result, stats = run_tech_growth(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps({"stats": stats.__dict__, "data": result.to_dict(orient="records")}, ensure_ascii=False, indent=2))
    elif args.format == "csv":
        result.to_csv(sys.stdout, index=False)
    else:
        print(render_screen(result, stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
