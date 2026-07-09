"""Markdown rendering for coarse strategy outputs."""

from __future__ import annotations

import pandas as pd


def _fmt_yi(value) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value) / 100000000:.1f} 亿"
    except Exception:
        return "N/A"


def _fmt_pct(value) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.2f}%"
    except Exception:
        return "N/A"


def _fmt_num(value) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.2f}"
    except Exception:
        return "N/A"


def render_coarse(df: pd.DataFrame, meta: dict) -> str:
    lines = [
        "# 粗筛策略结果",
        "",
        f"- 策略：{meta.get('strategy', '')}",
        f"- 每个策略保留：{meta.get('top', 5)} 支",
        f"- 财报口径：{meta.get('report_date', '')}",
        f"- 候选池来源：{meta.get('universe_source', '')}",
        f"- 行情/市值来源：{meta.get('quote_source', '')}",
        "",
    ]
    if df.empty:
        lines.append("没有粗筛候选。")
        return "\n".join(lines)
    grouped = df.groupby("coarse_strategy", sort=False)
    for strategy, group in grouped:
        title = group["coarse_strategy_title"].iloc[0]
        lines += [f"## {title}（{strategy}）", ""]
        for i, row in enumerate(group.itertuples(index=False), start=1):
            lines += [
                f"{i}. {row.name}（{row.code}）",
                f"   行业：{row.board_name}；总市值：{_fmt_yi(row.market_cap)}；PE：{_fmt_num(row.pe)}；PB：{_fmt_num(row.pb)}。",
                f"   增长：营收同比 {_fmt_pct(row.revenue_yoy)}；净利润同比 {_fmt_pct(row.profit_yoy)}；粗筛分：{_fmt_num(row.coarse_score)}。",
                f"   说明：{row.coarse_reason}；{row.data_note}。",
                "",
            ]
    return "\n".join(lines)
