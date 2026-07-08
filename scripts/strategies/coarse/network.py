"""Realtime source access for coarse screening.

This layer owns upstream fetch fallback for the coarse screen. It returns raw
source frames; repository code is responsible for cache reads/writes and
normalization boundaries.
"""

from __future__ import annotations

import pandas as pd

from data.sources import load_financial_report, load_spot, normalize_financials
from strategies.tech_growth import build_tech_universe


def fetch_coarse_source_bundle(args) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    report_raw, report_date, financial_source = load_financial_report(args.report_date, args.refresh, args.source, args.no_proxy)
    financials = normalize_financials(report_raw)
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    universe, tech_board_count, universe_source, quote_source = build_tech_universe(
        args.refresh, keywords, args.no_proxy, args.source, financials
    )
    spot, spot_source = load_spot(args.refresh, args.no_proxy, args.source)
    meta = {
        "report_date": report_date,
        "financial_source": financial_source,
        "universe_source": universe_source,
        "quote_source": quote_source,
        "spot_source": spot_source,
        "tech_boards": tech_board_count,
        "tech_universe": len(universe),
    }
    return report_raw, financials, universe, meta | {"spot": spot}

