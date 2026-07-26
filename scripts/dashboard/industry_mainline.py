"""Shared industry mainline evidence ranking helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _rows_to_df(rows: list[dict] | pd.DataFrame | None) -> pd.DataFrame:
    if rows is None:
        return pd.DataFrame()
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _numeric_group(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def _merge_row_context(row: dict, fine_map: dict[str, dict], plan_map: dict[str, dict]) -> dict:
    code = str(row.get("code") or "").zfill(6)
    merged = {**row, **fine_map.get(code, {}), **plan_map.get(code, {})}
    merged["code"] = code
    return merged


def _leader_reason(row: dict) -> str:
    reasons: list[str] = []
    if pd.notna(row.get("market_cap")) and float(row.get("market_cap") or 0) > 0:
        reasons.append("市值靠前")
    if pd.notna(row.get("return_60d")) and float(row.get("return_60d") or 0) > 0:
        reasons.append("近60日强势")
    if pd.notna(row.get("amount_20d")) and float(row.get("amount_20d") or 0) > 0:
        reasons.append("成交额有承接")
    rev = float(row.get("revenue_yoy") or 0) if pd.notna(row.get("revenue_yoy")) else 0.0
    prof = float(row.get("profit_yoy") or 0) if pd.notna(row.get("profit_yoy")) else 0.0
    if rev > 0 and prof > 0:
        reasons.append("营收利润双增")
    if pd.notna(row.get("max_drawdown_252d")) and float(row.get("max_drawdown_252d") or 0) > -0.2:
        reasons.append("回撤可控")
    return "、".join(reasons) if reasons else "作为主线内候选观察"


def _mainline_reason(row: pd.Series) -> str:
    reasons = [
        f"近60日涨幅 {_pct(row.get('avg_return_60d'))}",
        f"上涨家数占比 {_pct(row.get('positive_ratio'))}",
        f"成交额 {_yi(row.get('avg_amount_20d'))}",
    ]
    if pd.notna(row.get("avg_revenue_yoy")) or pd.notna(row.get("avg_profit_yoy")):
        reasons.append(f"营收/利润均值 {_pct(row.get('avg_revenue_yoy'))} / {_pct(row.get('avg_profit_yoy'))}")
    return "；".join(reasons)


def _leader_score_frame(group: pd.DataFrame) -> pd.DataFrame:
    frame = _numeric_group(
        group,
        ["market_cap", "return_60d", "amount_20d", "revenue_yoy", "profit_yoy", "max_drawdown_252d"],
    ).copy()
    if frame.empty:
        return frame
    market_rank = frame["market_cap"].rank(pct=True, ascending=True).fillna(0.5)
    return_rank = frame["return_60d"].rank(pct=True, ascending=True).fillna(0.5)
    amount_rank = frame["amount_20d"].rank(pct=True, ascending=True).fillna(0.5)
    growth_signal = (frame["revenue_yoy"].clip(lower=0).fillna(0) + frame["profit_yoy"].clip(lower=0).fillna(0)) / 2
    growth_rank = growth_signal.rank(pct=True, ascending=True).fillna(0.5)
    risk_rank = (-frame["max_drawdown_252d"].abs().fillna(0)).rank(pct=True, ascending=True).fillna(0.5)
    frame["leader_score"] = (
        market_rank * 0.30
        + return_rank * 0.25
        + amount_rank * 0.20
        + growth_rank * 0.15
        + risk_rank * 0.10
    )
    return frame


def _pct(value: Any, digits: int = 2) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        number = float(value)
        if abs(number) <= 1:
            number *= 100
        return f"{number:.{digits}f}%"
    except Exception:
        return "N/A"


def _yi(value: Any, digits: int = 1) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value) / 100000000:.{digits}f} 亿"
    except Exception:
        return "N/A"


def build_industry_mainlines(
    pool_rows: list[dict] | pd.DataFrame,
    fine_rows: list[dict] | pd.DataFrame | None = None,
    plan_rows: list[dict] | pd.DataFrame | None = None,
    *,
    pool_source_label: str = "",
    pool_source_note: str = "",
) -> list[dict]:
    """Rank industries from a candidate stock pool using the v2 evidence skeleton."""

    pool_df = _rows_to_df(pool_rows)
    if pool_df.empty:
        return []
    pool_df = _numeric_group(
        pool_df,
        ["market_cap", "revenue_yoy", "profit_yoy", "amount_20d", "return_60d", "max_drawdown_252d"],
    )
    if "board_name" not in pool_df.columns:
        pool_df["board_name"] = "未分类"
    pool_df["board_name"] = pool_df["board_name"].fillna("未分类").astype(str)
    pool_df = pool_df[pool_df["board_name"].astype(str).str.strip() != ""].copy()
    if pool_df.empty:
        return []

    fine_map = {str(row.get("code") or "").zfill(6): row for row in _rows_to_df(fine_rows).to_dict(orient="records")}
    plan_map = {str(row.get("code") or "").zfill(6): row for row in _rows_to_df(plan_rows).to_dict(orient="records")}

    groups: list[dict] = []
    for board_name, group in pool_df.groupby("board_name", dropna=False):
        group = group.copy()
        if group.empty:
            continue
        group = _leader_score_frame(group)
        if "leader_score" not in group.columns:
            group["leader_score"] = 0.5
        group = group.sort_values(["leader_score", "market_cap"], ascending=[False, False])
        stock_count = int(len(group))
        avg_return_60d = group["return_60d"].mean()
        avg_amount_20d = group["amount_20d"].mean()
        avg_revenue_yoy = group["revenue_yoy"].mean()
        avg_profit_yoy = group["profit_yoy"].mean()
        avg_max_drawdown_252d = group["max_drawdown_252d"].mean()
        positive_ratio = float((group["return_60d"].fillna(0) > 0).mean()) if stock_count else 0.0
        growth_signal = ((group["revenue_yoy"].clip(lower=0).fillna(0) + group["profit_yoy"].clip(lower=0).fillna(0)) / 2).mean()
        pool = []
        for row in group.head(12).to_dict(orient="records"):
            merged = _merge_row_context(row, fine_map, plan_map)
            merged["leader_reason"] = _leader_reason(merged)
            pool.append(merged)
        leaders = pool[:3]
        groups.append(
            {
                "board_name": str(board_name),
                "board_code": str(group.iloc[0].get("board_code") or "") if "board_code" in group.columns and not group.empty else "",
                "stock_count": stock_count,
                "avg_return_60d": avg_return_60d,
                "avg_amount_20d": avg_amount_20d,
                "avg_revenue_yoy": avg_revenue_yoy,
                "avg_profit_yoy": avg_profit_yoy,
                "avg_max_drawdown_252d": avg_max_drawdown_252d,
                "positive_ratio": positive_ratio,
                "mainline_score": 0.0,
                "_growth_signal": growth_signal,
                "_risk_signal": -(abs(avg_max_drawdown_252d) if pd.notna(avg_max_drawdown_252d) else 0.0),
                "mainline_reason": _mainline_reason(
                    pd.Series(
                        {
                            "avg_return_60d": avg_return_60d,
                            "positive_ratio": positive_ratio,
                            "avg_amount_20d": avg_amount_20d,
                            "avg_revenue_yoy": avg_revenue_yoy,
                            "avg_profit_yoy": avg_profit_yoy,
                        }
                    )
                ),
                "stock_pool": pool,
                "leaders": leaders,
                "daily_review": leaders,
                "pool_source_label": pool_source_label or "样本代理",
                "pool_source_note": pool_source_note or "",
            }
        )

    if groups:
        score_frame = pd.DataFrame(groups)
        return_rank = pd.to_numeric(score_frame["avg_return_60d"], errors="coerce").rank(pct=True, ascending=True).fillna(0.5)
        amount_rank = pd.to_numeric(score_frame["avg_amount_20d"], errors="coerce").rank(pct=True, ascending=True).fillna(0.5)
        growth_rank = pd.to_numeric(score_frame["_growth_signal"], errors="coerce").rank(pct=True, ascending=True).fillna(0.5)
        risk_rank = pd.to_numeric(score_frame["_risk_signal"], errors="coerce").rank(pct=True, ascending=True).fillna(0.5)
        for idx, group in enumerate(groups):
            group["mainline_score"] = float(
                return_rank.iloc[idx] * 0.35
                + float(group.get("positive_ratio") or 0.0) * 0.20
                + amount_rank.iloc[idx] * 0.15
                + growth_rank.iloc[idx] * 0.20
                + risk_rank.iloc[idx] * 0.10
            )
            group.pop("_growth_signal", None)
            group.pop("_risk_signal", None)

    groups.sort(key=lambda item: (float(item.get("mainline_score") or 0), float(item.get("avg_return_60d") or 0)), reverse=True)
    for index, group in enumerate(groups, start=1):
        group["rank"] = index
    return groups

