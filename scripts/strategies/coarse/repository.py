"""Cache-facing data assembly for coarse screening."""

from __future__ import annotations

import pandas as pd

from common import find_col, to_number
from infra.cache import read_price_metrics
from data.sources import load_board_constituents, load_financial_report, load_industry_boards, load_spot, normalize_financials
from strategies.coarse.network import fetch_coarse_source_bundle


OPTIONAL_COLUMN_ALIASES = {
    "pe": [["市盈率-动态"], ["动态市盈率"], ["市盈率"], ["pe"]],
    "pb": [["市净率"], ["pb"]],
    "revenue": [["营业总收入-营业总收入"], ["营业总收入"], ["营业收入"], ["revenue"]],
    "profit": [["净利润-净利润"], ["净利润"], ["profit"]],
    "roe": [["净资产收益率"], ["ROE"], ["roe"]],
    "gross_margin": [["销售毛利率"], ["毛利率"], ["gross_margin"]],
    "rd_expense": [["研发费用"], ["研发支出"], ["rd_expense"]],
}


def _positive(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0) > 0


def _find_alias(columns: pd.Index, aliases: list[list[str]]) -> str | None:
    for alias in aliases:
        if len(alias) == 1:
            col = find_col(columns, [alias[0]])
        else:
            col = find_col(columns, [], contains_all=alias)
        if col:
            return col
    return None


def _is_absolute_metric_column(metric: str, col: str) -> bool:
    if metric not in {"revenue", "profit"}:
        return True
    bad_parts = ["同比", "环比", "增长", "季度", "率"]
    return not any(part in str(col) for part in bad_parts)


def _extract_optional_metrics(raw_frames: list[pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for raw in raw_frames:
        code_col = find_col(raw.columns, ["股票代码", "代码", "code"], contains_all=["代码"])
        if not code_col:
            continue
        out = pd.DataFrame({"code": raw[code_col].astype(str).str.zfill(6)})
        for metric, aliases in OPTIONAL_COLUMN_ALIASES.items():
            col = _find_alias(raw.columns, aliases)
            if col and _is_absolute_metric_column(metric, col):
                out[metric] = raw[col].map(to_number)
        frames.append(out)
    if not frames:
        return pd.DataFrame(columns=["code"])
    metrics = frames[0]
    for frame in frames[1:]:
        metrics = metrics.merge(frame, on="code", how="outer", suffixes=("", "_new"))
        for col in list(metrics.columns):
            if col.endswith("_new"):
                base = col[:-4]
                if base in metrics.columns:
                    metrics[base] = metrics[base].combine_first(metrics[col])
                    metrics = metrics.drop(columns=[col])
                else:
                    metrics = metrics.rename(columns={col: base})
    return metrics


def _build_selected_industry_universe(args, selected_industry: str) -> tuple[pd.DataFrame, dict]:
    report_raw, report_date, financial_source = load_financial_report(args.report_date, args.refresh, args.source, args.no_proxy)
    fin = normalize_financials(report_raw)
    spot, spot_source = load_spot(args.refresh, args.no_proxy, args.source)
    boards = load_industry_boards(args.refresh, args.no_proxy, args.source)
    selected = boards[boards["board_name"].astype(str) == selected_industry].copy()
    if selected.empty:
        selected = boards[boards["board_name"].astype(str).str.contains(str(selected_industry), na=False)].copy()
    if selected.empty:
        raise RuntimeError(f"Cannot find industry board for {selected_industry}")
    board_row = selected.iloc[0]
    board_name = str(board_row.get("board_name") or selected_industry)
    board_code = str(board_row.get("board_code") or "")
    constituents = load_board_constituents(board_name, board_code, args.refresh, args.no_proxy, args.source)
    base = constituents.merge(spot, on="code", how="left", suffixes=("", "_spot"))
    if "name_spot" in base.columns:
        if "name" in base.columns:
            base["name"] = base["name"].fillna(base["name_spot"])
        else:
            base["name"] = base["name_spot"]
        base = base.drop(columns=["name_spot"])
    if not fin.empty:
        base = base.merge(fin, on="code", how="left", suffixes=("", "_financial"))
        if "financial_name" in base.columns and "name" in base.columns:
            base["name"] = base["name"].fillna(base["financial_name"])
    optional = _extract_optional_metrics([report_raw, spot])
    if not optional.empty:
        base = base.merge(optional, on="code", how="left")
    if "revenue" in base.columns and "rd_expense" in base.columns:
        base["rd_intensity"] = pd.to_numeric(base["rd_expense"], errors="coerce") / pd.to_numeric(base["revenue"], errors="coerce")
    price_metrics = read_price_metrics(base["code"].astype(str).tolist(), as_of_date=getattr(args, "as_of_date", None))
    if not price_metrics.empty:
        base = base.merge(price_metrics, on="code", how="left")
    growth_flags = base.assign(_growth_positive=_positive(base["revenue_yoy"]) & _positive(base["profit_yoy"]))
    base["industry_growth_breadth"] = growth_flags.groupby("board_name")["_growth_positive"].transform("sum")
    meta = {
        "report_date": report_date,
        "financial_source": financial_source,
        "universe_source": "industry-board constituents",
        "quote_source": spot_source,
        "tech_boards": int(base["board_name"].nunique()) if "board_name" in base.columns else 0,
        "tech_universe": len(base),
        "selected_industry": board_name,
        "selected_industry_code": board_code,
        "selected_industry_pool_label": "行业全成分股",
        "selected_industry_pool_kind": "full",
        "selected_industry_pool_source": "industry_members",
    }
    return base, meta


def filter_by_sector(base: pd.DataFrame, sector_text: str | None) -> tuple[pd.DataFrame, dict]:
    """Filter a base universe by comma-separated sector terms in board_name."""

    terms = [term.strip() for term in str(sector_text or "").split(",") if term.strip()]
    meta = {
        "sector_terms": terms,
        "sector_filter_mode": "board_name_contains",
        "sector_input_size": len(base),
        "sector_filtered": len(base),
    }
    if not terms or base.empty:
        return base.copy(), meta
    board = base.get("board_name", pd.Series("", index=base.index)).fillna("").astype(str)
    mask = board.map(lambda value: any(term in value for term in terms))
    filtered = base[mask].copy()
    meta["sector_filtered"] = len(filtered)
    return filtered, meta


def build_base_universe(args) -> tuple[pd.DataFrame, dict]:
    selected_industry = str(getattr(args, "selected_industry", "") or "").strip()
    if selected_industry:
        try:
            base, meta = _build_selected_industry_universe(args, selected_industry)
            sector_text = getattr(args, "sector", "") or selected_industry
            if sector_text:
                base, sector_meta = filter_by_sector(base, sector_text)
                if not base.empty:
                    meta.update(sector_meta)
                    meta["selected_industry_pool_kind"] = "full"
                    meta["selected_industry_pool_label"] = "行业全成分股"
                    return base, meta
            return base, meta
        except Exception as exc:
            fallback_note = str(exc)
            report_raw, financials, universe, meta = fetch_coarse_source_bundle(args)
            spot = meta.pop("spot")
            base = universe.merge(financials, on="code", how="left")
            optional = _extract_optional_metrics([report_raw, spot])
            if not optional.empty:
                base = base.merge(optional, on="code", how="left")
            if "revenue" in base.columns and "rd_expense" in base.columns:
                base["rd_intensity"] = pd.to_numeric(base["rd_expense"], errors="coerce") / pd.to_numeric(base["revenue"], errors="coerce")
            price_metrics = read_price_metrics(base["code"].astype(str).tolist(), as_of_date=getattr(args, "as_of_date", None))
            if not price_metrics.empty:
                base = base.merge(price_metrics, on="code", how="left")
            growth_flags = base.assign(_growth_positive=_positive(base["revenue_yoy"]) & _positive(base["profit_yoy"]))
            base["industry_growth_breadth"] = growth_flags.groupby("board_name")["_growth_positive"].transform("sum")
            sector_text = selected_industry or getattr(args, "sector", "")
            if sector_text:
                base, sector_meta = filter_by_sector(base, sector_text)
                meta.update(sector_meta)
            meta.update(
                {
                    "selected_industry": selected_industry,
                    "selected_industry_pool_label": "缓存样本代理",
                    "selected_industry_pool_kind": "sample",
                    "selected_industry_pool_source": str(meta.get("universe_source") or "sample"),
                    "selected_industry_fallback_note": fallback_note,
                }
            )
            return base, meta
    report_raw, financials, universe, meta = fetch_coarse_source_bundle(args)
    spot = meta.pop("spot")
    base = universe.merge(financials, on="code", how="left")
    optional = _extract_optional_metrics([report_raw, spot])
    if not optional.empty:
        base = base.merge(optional, on="code", how="left")
    if "revenue" in base.columns and "rd_expense" in base.columns:
        base["rd_intensity"] = pd.to_numeric(base["rd_expense"], errors="coerce") / pd.to_numeric(base["revenue"], errors="coerce")
    price_metrics = read_price_metrics(base["code"].astype(str).tolist(), as_of_date=getattr(args, "as_of_date", None))
    if not price_metrics.empty:
        base = base.merge(price_metrics, on="code", how="left")
    growth_flags = base.assign(_growth_positive=_positive(base["revenue_yoy"]) & _positive(base["profit_yoy"]))
    base["industry_growth_breadth"] = growth_flags.groupby("board_name")["_growth_positive"].transform("sum")
    sector_text = getattr(args, "sector", "")
    if sector_text:
        base, sector_meta = filter_by_sector(base, sector_text)
        meta.update(sector_meta)
    return base, meta
