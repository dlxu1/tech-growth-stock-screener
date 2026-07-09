"""Markdown rendering for next-session trade plans."""

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


def _fmt_yi(value) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value) / 100000000:.2f} 亿"
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


def render_trade_plan(df: pd.DataFrame, meta: dict) -> str:
    quality = meta.get("data_quality") or {}
    lines = [
        "# 明日操作计划",
        "",
        f"- 粗筛策略：{meta.get('coarse_strategy', '')}",
        f"- 每个粗筛策略保留：{meta.get('coarse_top', 5)} 支",
        f"- 细筛/计划输出：{meta.get('selected', 0)} 支",
        f"- 数据质量：完整 {quality.get('complete', 0)} 支；降级 {quality.get('degraded', 0)} 支；缺失 {quality.get('missing', 0)} 支；可生成计划 {quality.get('usable_for_plan', 0)} 支",
        f"- 买入突破缓冲：{float(meta.get('breakout_buffer', 0)):.2%}",
        f"- 放量确认倍数：{float(meta.get('volume_multiplier', 0)):.2f}x",
        f"- 固定止损参考：{float(meta.get('stop_pct', 0)):.2%}",
        f"- 日线缓存：{meta.get('db_path', '')}",
        "",
        "说明：这是规则化交易计划，不是收益保证。实际成交价会受跳空、流动性和滑点影响。",
        "",
    ]
    if df.empty:
        lines.append("没有可生成计划的候选。")
        return "\n".join(lines)
    for i, row in enumerate(df.itertuples(index=False), start=1):
        lines += [
            f"{i}. {row.name}（{row.code}）",
            f"   动作：{_fmt_text(row.action)}；主策略：{_fmt_text(row.primary_strategy)}；技术评分：{_fmt_num(row.technical_score)}；原因：{_fmt_text(row.technical_reasons)}。",
            f"   依据交易日：{_fmt_text(row.basis_trade_date)}；最新收盘：{_fmt_num(row.latest_close)}。",
            f"   买入：突破触发价 {_fmt_num(row.breakout_trigger)}；回踩买入区间 {_fmt_num(row.pullback_low)} - {_fmt_num(row.pullback_high)}；放量确认成交额 >= {_fmt_yi(row.volume_confirm_amount)}。",
            f"   风控：计划入场价 {_fmt_num(row.planned_entry)}；初始止损 {_fmt_num(row.initial_stop)}；单笔价格风险 {_fmt_pct(row.risk_pct)}；仓位上限 {_fmt_pct(row.position_cap)}。",
            f"   止盈/移动止损：1R {_fmt_num(row.take_profit_1r)}；2R {_fmt_num(row.take_profit_2r)}；{_fmt_text(row.trailing_stop_rule)}。",
            f"   不买/撤单：{_fmt_text(row.cancel_conditions)}。",
            f"   及时止损：{_fmt_text(row.stop_conditions)}。",
            f"   数据诊断：状态={_fmt_text(row.data_status)}；可用于计划={_fmt_text(row.usable_for_plan)}。",
            f"   缺失原因：{_fmt_text(row.missing_data_reason)}",
            f"   评测影响：{_fmt_text(row.missing_data_impact)}",
            f"   备注：{_fmt_text(row.plan_note)}",
            "",
        ]
    return "\n".join(lines)
