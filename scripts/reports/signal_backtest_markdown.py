"""Markdown rendering for signal backtests."""

from __future__ import annotations


def _pct(value) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value) * 100:.2f}%"
    except Exception:
        return "N/A"


def render_signal_backtest(model: dict) -> str:
    summary = model.get("summary", {})
    lines = [
        "# 数据回测",
        "",
        f"- 信号日期：{summary.get('signal_date', 'N/A')}",
        f"- 选股数量：Top {summary.get('top', 'N/A')}",
        "- 买入规则：信号日后下一交易日开盘价",
        "- 卖出规则：持有期第 N 个交易日收盘价",
        "- 说明：结果仅用于历史信号复盘，不构成投资建议。",
        "",
    ]
    for strategy in model.get("strategies", []):
        lines.append(f"## {strategy.get('title', strategy.get('key', ''))}")
        lines.append("")
        lines.append("| 持有期 | 完整样本 | 平均收益 | 中位收益 | 胜率 | 最大收益 | 最大亏损 |")
        lines.append("|---:|---:|---:|---:|---:|---:|---:|")
        for horizon in sorted((strategy.get("horizons") or {}), key=lambda value: int(value)):
            data = strategy["horizons"][horizon]
            lines.append(
                "| "
                f"{data.get('holding_days')} | "
                f"{data.get('complete_count')} | "
                f"{_pct(data.get('avg_return_pct'))} | "
                f"{_pct(data.get('median_return_pct'))} | "
                f"{_pct(data.get('win_rate'))} | "
                f"{_pct(data.get('max_return_pct'))} | "
                f"{_pct(data.get('min_return_pct'))} |"
            )
        lines.append("")
        rows = [row for row in strategy.get("rows", []) if row.get("holding_days") == 7][:10]
        if rows:
            lines.append("7日明细：")
            for row in rows:
                lines.append(
                    f"- {row.get('code')} {row.get('name')}："
                    f"分数 {float(row.get('score') or 0):.2f}，"
                    f"{row.get('buy_date') or 'N/A'} -> {row.get('sell_date') or 'N/A'}，"
                    f"收益 {_pct(row.get('return_pct'))}，状态 {row.get('data_status')}"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
