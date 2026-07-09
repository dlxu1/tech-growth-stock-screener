"""Markdown rendering for potential-stock combo scoring."""

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


def _fmt_score(value) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.1f}"
    except Exception:
        return "N/A"


def _fmt_text(value) -> str:
    try:
        if pd.isna(value):
            return "N/A"
    except Exception:
        pass
    text = str(value)
    return "N/A" if text.lower() in {"nan", "none", "<na>", ""} else text


def render_combo(df: pd.DataFrame, meta: dict) -> str:
    lines = [
        "# 潜力股组合评分",
        "",
        f"- 输出数量：{meta.get('selected', 0)} 支",
        f"- 单策略候选深度：{meta.get('combo_strategy_top', '')} 支",
        f"- 财报口径：{meta.get('report_date', '')}",
        f"- 候选池来源：{meta.get('universe_source', '')}",
        f"- 行情/市值来源：{meta.get('quote_source', '')}",
        "- 评分权重：策略共振 35%，成长 20%，质量 18%，风控 15%，流动性 7%，动量 5%。",
        "",
    ]
    if df.empty:
        lines.append("没有组合评分候选。")
        return "\n".join(lines)
    for i, row in enumerate(df.itertuples(index=False), start=1):
        lines += [
            f"{i}. {row.name}（{row.code}）",
            f"   组合分：{_fmt_score(row.combo_score)}；策略命中：{int(row.strategy_hits)}；策略共振分：{_fmt_score(row.overlap_score)}。",
            f"   行业：{row.board_name}；总市值：{_fmt_yi(row.market_cap)}；PE：{_fmt_score(row.pe)}；PB：{_fmt_score(row.pb)}。",
            f"   基本面：营收同比 {_fmt_pct(row.revenue_yoy)}；净利润同比 {_fmt_pct(row.profit_yoy)}；ROE：{_fmt_pct(row.roe)}；毛利率：{_fmt_pct(row.gross_margin)}。",
            f"   技术/风险：60日涨幅 {_fmt_pct(row.return_60d * 100 if pd.notna(row.return_60d) else row.return_60d)}；252日最大回撤 {_fmt_pct(row.max_drawdown_252d * 100 if pd.notna(row.max_drawdown_252d) else row.max_drawdown_252d)}；20日成交额：{_fmt_yi(row.amount_20d)}。",
            f"   入选理由：{_fmt_text(row.combo_reason)}。",
            f"   风险提示：{_fmt_text(row.risk_flags)}。",
            f"   命中策略：{_fmt_text(row.matched_strategies)}。",
            f"   数据说明：{_fmt_text(row.data_note)}。",
            "",
        ]
    lines.append("这是研究候选清单，不构成投资建议。组合分越高只代表当前缓存数据下的多维匹配度越高。")
    return "\n".join(lines)
