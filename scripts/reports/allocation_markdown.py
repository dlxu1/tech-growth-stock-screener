"""Markdown rendering for personal technology allocation plans."""

from __future__ import annotations

import pandas as pd


def _fmt_money(value) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.0f} 元"
    except Exception:
        return "N/A"


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


def render_allocation_plan(df: pd.DataFrame, meta: dict) -> str:
    """Render a small-account ETF/core plus stock/satellite allocation plan."""

    lines = [
        "# 个人科技股配置计划",
        "",
        f"- 总资金：{_fmt_money(meta.get('capital'))}",
        f"- 年化目标：{_fmt_pct(meta.get('target_return'))}，对应目标收益约 {_fmt_money(meta.get('annual_target_profit'))}",
        f"- 科技 ETF 核心仓：{_fmt_money(meta.get('core_etf_budget'))}，分 {meta.get('etf_tranches', 0)} 笔，每笔约 {_fmt_money(meta.get('etf_tranche_amount'))}",
        f"- 个股卫星仓：{_fmt_money(meta.get('satellite_stock_budget'))}",
        f"- 现金预留：{_fmt_money(meta.get('cash_reserve'))}",
        "",
        "说明：这是规则化研究计划，不是收益保证。实际买卖由你自己决定。",
        "",
        "## 执行顺序",
        "",
        "1. 先用 ETF 承接科技方向长期仓位，避免小资金押错单只股票。",
        "2. 个股只在计划层触发且一手成本符合仓位约束时执行。",
        "3. 一手成本超过单股仓位上限的高价龙头只作为板块风向标。",
        "4. 保留现金，等待回调、突破确认或止损后的重新评估。",
        "",
    ]
    if df.empty:
        lines.append("## 个股候选")
        lines.append("")
        lines.append("当前没有可用于个人配置计划的个股候选。")
        return "\n".join(lines)

    lines += ["## 个股候选", ""]
    for i, row in enumerate(df.itertuples(index=False), start=1):
        lines += [
            f"{i}. {row.name}（{row.code}）",
            f"   组合动作：{_fmt_text(row.portfolio_action)}；计划层动作：{_fmt_text(row.source_action)}；预算状态：{_fmt_text(row.budget_status)}。",
            f"   价格/预算：最新收盘 {_fmt_num(row.latest_close)}；一手成本：{_fmt_money(row.lot_cost)}；首次买入预算 {_fmt_money(row.initial_buy_budget)}；单股上限 {_fmt_money(row.max_position_amount)}。",
            f"   买入/风控：计划入场 {_fmt_num(row.planned_entry)}；初始止损 {_fmt_num(row.initial_stop)}；单笔价格风险 {_fmt_pct(row.risk_pct)}；仓位上限 {_fmt_pct(row.position_cap)}。",
            f"   备注：{_fmt_text(row.allocation_note)}",
            "",
        ]
    return "\n".join(lines)
