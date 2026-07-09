"""Markdown rendering for fine technical screening outputs."""

from __future__ import annotations

import pandas as pd


def _fmt_num(value, digits: int = 2) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.{digits}f}"
    except Exception:
        return "N/A"


def _fmt_pct(value) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value) * 100:.2f}%"
    except Exception:
        return "N/A"


def _fmt_text(value) -> str:
    try:
        if pd.isna(value):
            return "N/A"
    except Exception:
        pass
    text = str(value)
    return "N/A" if text.lower() in {"nan", "none", "<na>"} else text


def render_fine(df: pd.DataFrame, meta: dict) -> str:
    lines = [
        "# 细筛技术面结果",
        "",
        f"- 粗筛策略：{meta.get('coarse_strategy', '')}",
        f"- 每个粗筛策略保留：{meta.get('coarse_top', 5)} 支",
        f"- 细筛输出：{meta.get('selected', 0)} 支",
        f"- 粗筛去重候选：{meta.get('coarse_candidates', 0)} 支",
        f"- 日线缓存：{meta.get('db_path', '')}",
        "",
    ]
    if df.empty:
        lines.append("没有可细筛的候选。")
        return "\n".join(lines)
    for i, row in enumerate(df.itertuples(index=False), start=1):
        lines += [
            f"{i}. {row.name}（{row.code}）",
            f"   技术评分：{_fmt_num(row.technical_score)}；原因：{row.technical_reasons}。",
            f"   最新交易日：{_fmt_text(row.latest_trade_date)}；收盘：{_fmt_num(row.close)}；当日涨跌：{_fmt_pct(row.change_pct)}。",
            f"   趋势：MA5={_fmt_num(row.ma5)}，MA10={_fmt_num(row.ma10)}，MA20={_fmt_num(row.ma20)}；MACD柱={_fmt_num(row.macd_hist, 4)}；RSI14={_fmt_num(row.rsi14)}。",
            f"   量价/风险：成交额放大倍数={_fmt_num(row.amount_ratio)}；20日涨幅={_fmt_pct(row.return_20d)}；20日最大回撤={_fmt_pct(row.max_drawdown_20d)}。",
            f"   粗筛来源：{row.coarse_strategies}；粗筛分：{_fmt_num(row.coarse_score)}；说明：{row.technical_note}。",
            "",
        ]
    return "\n".join(lines)
