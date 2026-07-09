"""Realtime source access for coarse screening.

This layer owns upstream fetch fallback for the coarse screen. It returns raw
source frames; repository code is responsible for cache reads/writes and
normalization boundaries.
"""

from __future__ import annotations

import pandas as pd

from data.sources import load_financial_report, load_spot, normalize_financials
from infra.cache import read_index_constituents
from strategies.tech_growth import build_tech_universe


def build_index_universe(index_symbol: str, spot: pd.DataFrame, financials: pd.DataFrame) -> pd.DataFrame:
    members = read_index_constituents(index_symbol)
    if members.empty:
        raise RuntimeError(f"No cached index constituents for {index_symbol}. Run sync --dataset index_constituents first.")
    index_cols = ["code", "name", "index_name", "constituent_date", "weight"]
    universe = members[[col for col in index_cols if col in members.columns]].copy()
    universe = universe.rename(columns={"name": "index_member_name"})
    universe["code"] = universe["code"].astype(str).str.zfill(6)
    universe = universe.merge(spot, on="code", how="left")
    fin_cols = [col for col in ["code", "financial_name", "report_industry"] if col in financials.columns]
    if fin_cols:
        universe = universe.merge(financials[fin_cols], on="code", how="left")
    if "name" not in universe.columns:
        universe["name"] = pd.NA
    universe["name"] = universe["name"].fillna(universe.get("index_member_name", pd.Series(index=universe.index, dtype=object)))
    if "financial_name" in universe.columns:
        universe["name"] = universe["name"].fillna(universe["financial_name"])
    universe["board_name"] = universe.get("report_industry", pd.Series(index=universe.index, dtype=object)).fillna("")
    fallback_name = universe["index_name"].dropna().iloc[0] if "index_name" in universe.columns and universe["index_name"].notna().any() else f"指数{index_symbol}"
    universe["board_name"] = universe["board_name"].replace("", pd.NA).fillna(fallback_name)
    universe["market_cap"] = pd.to_numeric(universe["market_cap"], errors="coerce")
    universe["industry_rank"] = universe.groupby("board_name")["market_cap"].rank(method="first", ascending=False).fillna(9999).astype(int)
    return universe[["code", "name", "market_cap", "board_name", "industry_rank"]].drop_duplicates("code")


def fetch_coarse_source_bundle(args) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    report_raw, report_date, financial_source = load_financial_report(args.report_date, args.refresh, args.source, args.no_proxy)
    financials = normalize_financials(report_raw)
    spot, spot_source = load_spot(args.refresh, args.no_proxy, args.source)
    universe_name = getattr(args, "universe", "tech")
    if universe_name == "csi300":
        index_symbol = getattr(args, "universe_index_symbol", "000300")
        universe = build_index_universe(index_symbol, spot, financials)
        universe_source = f"index_constituents:{index_symbol}"
        quote_source = spot_source
        tech_board_count = universe["board_name"].nunique()
    else:
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
        universe, tech_board_count, universe_source, quote_source = build_tech_universe(
            args.refresh, keywords, args.no_proxy, args.source, financials
        )
    meta = {
        "report_date": report_date,
        "financial_source": financial_source,
        "universe_source": universe_source,
        "quote_source": quote_source,
        "spot_source": spot_source,
        "tech_boards": tech_board_count,
        "tech_universe": len(universe),
        "universe": universe_name,
    }
    return report_raw, financials, universe, meta | {"spot": spot}
