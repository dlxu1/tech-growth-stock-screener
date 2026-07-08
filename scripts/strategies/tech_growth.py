"""Technology leadership plus real-growth stock screen."""

from __future__ import annotations

import pandas as pd

from common import SourceStats, db_path
from data.sources import (
    load_board_constituents,
    load_financial_report,
    load_industry_boards,
    load_spot,
    normalize_financials,
)


def build_report_industry_universe(spot: pd.DataFrame, fin: pd.DataFrame, keywords: list[str]) -> tuple[pd.DataFrame, int]:
    if "report_industry" not in fin.columns:
        raise RuntimeError("financial report has no industry column")
    tech_fin = fin[
        fin["report_industry"].fillna("").map(lambda b: any(k in str(b) for k in keywords))
    ].copy()
    if tech_fin.empty:
        raise RuntimeError("no technology rows found from financial-report industry")
    merged = tech_fin.merge(spot, on="code", how="inner", suffixes=("_financial", ""))
    if "financial_name" in merged.columns:
        merged["name"] = merged["name"].fillna(merged["financial_name"])
    merged["board_name"] = merged["report_industry"]
    merged["industry_rank"] = merged.groupby("board_name")["market_cap"].rank(method="first", ascending=False).astype(int)
    merged = merged.sort_values(["code", "industry_rank"]).drop_duplicates("code", keep="first")
    return merged[["code", "name", "market_cap", "board_name", "industry_rank"]], merged["board_name"].nunique()


def build_board_universe(
    spot: pd.DataFrame,
    refresh: bool,
    keywords: list[str],
    no_proxy: bool,
    source: str,
) -> tuple[pd.DataFrame, int]:
    boards = load_industry_boards(refresh, no_proxy, source)
    tech_board_rows = boards[boards["board_name"].map(lambda b: any(k in str(b) for k in keywords))]
    frames = []
    failures = []
    for row in tech_board_rows.itertuples(index=False):
        board = str(row.board_name)
        board_code = str(getattr(row, "board_code", "") or "")
        try:
            cons = load_board_constituents(board, board_code, refresh, no_proxy, source)
            merged = cons.merge(spot, on="code", how="inner")
            merged["industry_rank"] = merged["market_cap"].rank(method="first", ascending=False).astype(int)
            frames.append(merged)
        except Exception as exc:
            failures.append(f"{board}: {exc}")
    if not frames:
        detail = "; ".join(failures[:5])
        raise RuntimeError(f"No technology board constituents fetched. {detail}")
    universe = pd.concat(frames, ignore_index=True)
    universe = universe.sort_values(["code", "industry_rank"]).drop_duplicates("code", keep="first")
    return universe, len(tech_board_rows)


def build_tech_universe(
    refresh: bool,
    keywords: list[str],
    no_proxy: bool,
    source: str,
    fin: pd.DataFrame,
) -> tuple[pd.DataFrame, int, str, str]:
    spot, quote_source = load_spot(refresh, no_proxy, source)
    failures = []
    if source != "efinance":
        try:
            universe, tech_board_count = build_board_universe(spot, refresh, keywords, no_proxy, source)
            return universe, tech_board_count, "industry-board constituents", quote_source
        except Exception as exc:
            failures.append(str(exc))
    try:
        universe, tech_group_count = build_report_industry_universe(spot, fin, keywords)
        return universe, tech_group_count, "financial-report industry", quote_source
    except Exception as exc:
        failures.append(str(exc))
    raise RuntimeError("No technology universe available. " + "; ".join(failures[:5]))


def run(args) -> tuple[pd.DataFrame, SourceStats]:
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    report_raw, report_date, financial_source = load_financial_report(args.report_date, args.refresh, args.source, args.no_proxy)
    fin = normalize_financials(report_raw)
    universe, tech_board_count, universe_source, quote_source = build_tech_universe(
        args.refresh, keywords, args.no_proxy, args.source, fin
    )
    ranked = universe[universe["industry_rank"] <= args.industry_rank].copy()
    joined = ranked.merge(fin, on="code", how="left")
    passed = joined[
        (joined["revenue_yoy"] >= args.min_revenue_yoy)
        & (joined["profit_yoy"] >= args.min_profit_yoy)
    ].copy()
    passed["growth_score"] = passed["revenue_yoy"].clip(lower=0) * 0.35 + passed["profit_yoy"].clip(lower=0) * 0.65
    passed["leadership_score"] = (args.industry_rank + 1 - passed["industry_rank"]).clip(lower=0) * 10
    passed["score"] = passed["leadership_score"] + passed["growth_score"]
    passed = passed.sort_values(
        ["industry_rank", "profit_yoy", "revenue_yoy", "market_cap"],
        ascending=[True, False, False, False],
    )
    cols = ["code", "name", "board_name", "industry_rank", "market_cap", "revenue_yoy", "profit_yoy", "score"]
    stats = SourceStats(
        report_date=report_date,
        universe_source=universe_source,
        quote_source=quote_source,
        financial_source=financial_source,
        db_path=str(db_path()),
        tech_boards=tech_board_count,
        tech_universe=len(universe),
        after_rank_gate=len(ranked),
        after_growth_gate=len(passed),
    )
    return passed[cols].head(args.top), stats

