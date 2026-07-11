"""Markdown rendering for sector screening outputs."""

from __future__ import annotations

import pandas as pd


def _num(value, digits: int = 2) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.{digits}f}"
    except Exception:
        return "N/A"


def _yi(value) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value) / 100000000:.1f} 亿"
    except Exception:
        return "N/A"


def render_sector_screen(df: pd.DataFrame, meta: dict) -> str:
    lines = [
        "# 板块筛选结果",
        "",
        f"- 基础股票池：{meta.get('universe', '')}",
        f"- 候选池来源：{meta.get('universe_source', '')}",
        f"- 板块过滤：{','.join(meta.get('sector_terms', [])) or '未指定'}",
        f"- 过滤方式：{meta.get('sector_filter_mode', '')}",
        f"- 过滤前：{meta.get('sector_input_size', meta.get('tech_universe', 'N/A'))} 只",
        f"- 过滤后：{meta.get('sector_filtered', len(df))} 只",
        f"- 输出上限：{meta.get('capped_top', len(df))} 只",
        f"- 财报口径：{meta.get('report_date', '')}",
        "",
        "说明：这是板块研究池，不是买入建议；细分概念如光模块、先进封装需要概念成分数据支持才可精确过滤。",
        "",
    ]
    if df.empty:
        lines.append("没有符合条件的股票。")
        return "\n".join(lines)
    for i, row in enumerate(df.itertuples(index=False), start=1):
        lines += [
            f"{i}. {row.name}（{row.code}）",
            f"   板块：{row.board_name}；总市值：{_yi(row.market_cap)}。",
            f"   成长：营收同比 {_num(row.revenue_yoy)}%，净利润同比 {_num(row.profit_yoy)}%。",
            f"   命中：{row.match_reason}。",
            f"   风险：{row.risk_flags}。",
            "",
        ]
    return "\n".join(lines)
