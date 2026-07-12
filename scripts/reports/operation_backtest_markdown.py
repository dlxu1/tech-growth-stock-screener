"""Markdown rendering for operation-plan backtests."""

from __future__ import annotations


def _pct(value) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value) * 100:.2f}%"
    except Exception:
        return "N/A"


def _num(value) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.2f}"
    except Exception:
        return "N/A"


def _status(value: str) -> str:
    return {
        "take_profit": "已止盈",
        "stop_loss": "已止损",
        "hold_to_end": "持有至截止日",
        "not_triggered": "未触发",
        "missing_future_quotes": "缺未来行情",
        "invalid_plan": "计划无效",
    }.get(str(value), str(value or "N/A"))


def render_operation_backtest(model: dict) -> str:
    summary = model.get("summary", {})
    lines = [
        "# 操作回测",
        "",
        f"- 信号日期：{summary.get('signal_date', 'N/A')}",
        f"- 股票范围：高潜力+好时机且操作建议可执行",
        f"- 止盈规则：遵循 A 股 T+1，买入后下一交易日起达到 {_pct(summary.get('profit_target_pct'))} 卖出",
        "- 止损规则：遵循 A 股 T+1，买入后下一交易日起触达操作建议初始止损价卖出",
        "- 说明：结果仅用于规则复核，不构成投资建议。",
        "",
        "## 汇总",
        "",
        f"- 操作样本：{summary.get('candidate_count', 0)}",
        f"- 成功买入：{summary.get('trade_count', 0)}",
        f"- 未触发：{summary.get('untriggered_count', 0)}",
        f"- 已止盈：{summary.get('take_profit_count', 0)}",
        f"- 已止损：{summary.get('stop_loss_count', 0)}",
        f"- 仍持有：{summary.get('hold_count', 0)}",
        f"- 实际成交胜率：{_pct(summary.get('win_rate'))}",
        f"- 平均已实现收益：{_pct(summary.get('realized_avg_return_pct'))}",
        f"- 平均含浮动收益：{_pct(summary.get('total_avg_return_pct'))}",
        "",
    ]
    rows = model.get("rows") or []
    if not rows:
        lines.append("暂无可回测的操作样本。")
        return "\n".join(lines).rstrip() + "\n"
    lines.extend(
        [
            "## 明细",
            "",
            "| 代码 | 名称 | 动作 | 买入日 | 买入价 | 卖出日 | 卖出价 | 状态 | 收益 |",
            "|---|---|---|---|---:|---|---:|---|---:|",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            f"{row.get('code')} | "
            f"{row.get('name')} | "
            f"{row.get('action')} | "
            f"{row.get('buy_date') or 'N/A'} | "
            f"{_num(row.get('buy_price'))} | "
            f"{row.get('sell_date') or 'N/A'} | "
            f"{_num(row.get('sell_price'))} | "
            f"{_status(row.get('status'))} | "
            f"{_pct(row.get('return_pct'))} |"
        )
    return "\n".join(lines).rstrip() + "\n"
