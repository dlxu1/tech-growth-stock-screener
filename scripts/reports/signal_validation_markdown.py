"""Markdown rendering for signal validation diagnostics."""

from __future__ import annotations


def _pct(value) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value) * 100:.2f}%"
    except Exception:
        return "N/A"


def _section(title: str, groups: dict) -> list[str]:
    lines = [f"## {title}", ""]
    if not groups:
        return [*lines, "暂无可统计样本。", ""]
    lines.extend(
        [
            "| 分组 | 持有期 | 完整样本 | 平均收益 | 中位收益 | 胜率 | 最大收益 | 最大亏损 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for label, horizons in groups.items():
        for horizon in sorted(horizons, key=lambda value: int(value)):
            data = horizons[horizon]
            lines.append(
                "| "
                f"{label} | "
                f"{data.get('holding_days')} | "
                f"{data.get('complete_count')} | "
                f"{_pct(data.get('avg_return_pct'))} | "
                f"{_pct(data.get('median_return_pct'))} | "
                f"{_pct(data.get('win_rate'))} | "
                f"{_pct(data.get('max_return_pct'))} | "
                f"{_pct(data.get('min_return_pct'))} |"
            )
    lines.append("")
    return lines


def render_signal_validation(model: dict) -> str:
    summary = model.get("summary", {})
    dates = summary.get("signal_dates") or []
    date_text = "、".join(dates[:8])
    if len(dates) > 8:
        date_text += f" 等 {len(dates)} 个信号日"
    lines = [
        "# 信号有效性验证",
        "",
        f"- 信号日期：{date_text or 'N/A'}",
        f"- 信号日数量：{summary.get('signal_date_count', len(dates))}",
        f"- 候选样本数：{summary.get('candidate_count', 0)}",
        f"- 综合分分桶：每 {summary.get('bucket_size', 'N/A')} 只一组",
        "- 买入规则：信号日后下一交易日开盘价",
        "- 卖出规则：持有期第 N 个交易日收盘价",
        "- 说明：该验证用于判断评分信号是否有预测力，不代表操作建议触发式回测。",
        "",
    ]
    lines.extend(_section("矩阵象限表现", model.get("quadrants") or {}))
    lines.extend(_section("综合关注分分桶表现", model.get("attention_buckets") or {}))
    return "\n".join(lines).rstrip() + "\n"
