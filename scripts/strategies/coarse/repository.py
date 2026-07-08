"""Cache-facing data assembly for coarse screening."""

from __future__ import annotations

import pandas as pd

from common import find_col, to_number
from infra.cache import read_price_metrics
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


def build_base_universe(args) -> tuple[pd.DataFrame, dict]:
    report_raw, financials, universe, meta = fetch_coarse_source_bundle(args)
    spot = meta.pop("spot")
    base = universe.merge(financials, on="code", how="left")
    optional = _extract_optional_metrics([report_raw, spot])
    if not optional.empty:
        base = base.merge(optional, on="code", how="left")
    if "revenue" in base.columns and "rd_expense" in base.columns:
        base["rd_intensity"] = pd.to_numeric(base["rd_expense"], errors="coerce") / pd.to_numeric(base["revenue"], errors="coerce")
    price_metrics = read_price_metrics(base["code"].astype(str).tolist())
    if not price_metrics.empty:
        base = base.merge(price_metrics, on="code", how="left")
    growth_flags = base.assign(_growth_positive=_positive(base["revenue_yoy"]) & _positive(base["profit_yoy"]))
    base["industry_growth_breadth"] = growth_flags.groupby("board_name")["_growth_positive"].transform("sum")
    return base, meta

