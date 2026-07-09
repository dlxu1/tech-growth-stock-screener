"""Markdown rendering for screener outputs."""

from __future__ import annotations

import pandas as pd

from common import SourceStats


def render_screen(df: pd.DataFrame, stats: SourceStats) -> str:
    lines = [
        "# 科技成长股筛选结果",
        "",
        f"- 财报口径：{stats.report_date}",
        f"- 候选池来源：{stats.universe_source}",
        f"- 行情/市值来源：{stats.quote_source}",
        f"- 财报来源：{stats.financial_source}",
        f"- 数据库缓存：{stats.db_path}",
        f"- 科技行业板块数：{stats.tech_boards}",
        f"- 科技候选池：{stats.tech_universe} 只",
        f"- 行业市值前十后：{stats.after_rank_gate} 只",
        f"- 营收与净利润同比为正后：{stats.after_growth_gate} 只",
        "",
    ]
    if df.empty:
        lines.append("没有股票同时通过三道门槛。")
        return "\n".join(lines)
    for i, row in enumerate(df.itertuples(index=False), start=1):
        market_cap_yi = row.market_cap / 100000000
        lines += [
            f"{i}. {row.name}（{row.code}）",
            f"   行业板块：{row.board_name}；行业市值排名：第 {int(row.industry_rank)}；总市值约 {market_cap_yi:.1f} 亿。",
            f"   业绩增长：营收同比 {row.revenue_yoy:.2f}%，净利润同比 {row.profit_yoy:.2f}%。",
            "   入选原因：属于科技板块，市值进入行业前十，且近一年营收与净利润均为正增长。",
            "   下一步核对：确认增长是否来自主营业务，并检查现金流、应收和存货是否同步健康。",
            "",
        ]
    lines += [
        "这是优先研究名单，不构成投资建议。下一步应核对最新财报附注、现金流、应收、存货和估值分位。",
    ]
    return "\n".join(lines)

