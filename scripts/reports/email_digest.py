"""Render daily NAS email digests from dashboard models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class EmailDigest:
    subject: str
    body: str
    payload: dict[str, Any]


def _stage_rows(model: dict, key: str) -> list[dict]:
    for stage in model.get("stages", []):
        if stage.get("key") == key:
            return list(stage.get("rows") or [])
    return []


def _code(value: Any) -> str:
    text = str(value or "").strip()
    return text.zfill(6) if text else ""


def _text(value: Any, default: str = "-") -> str:
    if value is None or value == "":
        return default
    return str(value)


def _number(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: Any) -> str:
    number = _number(value)
    return f"{number:.2f}" if number is not None else "-"


def _format_pct(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "-"
    if abs(number) <= 1:
        number *= 100
    return f"{number:.2f}%"


def _horizon_tags(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.replace("、", "/").split("/") if item.strip()]
    return []


def _format_horizon_tags(value: Any) -> str:
    tags = _horizon_tags(value)
    return " / ".join(tags) if tags else "证据不足，需人工复核"


def _health_date(health: dict) -> str:
    freshness = health.get("freshness") or {}
    return str(freshness.get("latest_trade_date") or date.today().isoformat())


def _health_lines(health: dict) -> list[str]:
    freshness = health.get("freshness") or {}
    coverage = health.get("coverage") or {}
    serial = health.get("serial") or {}
    lines = [
        f"数据健康度：{health.get('health_score', 0)}/100",
        f"最新行情日：{freshness.get('latest_trade_date') or 'N/A'}",
    ]
    if freshness.get("expected_latest_trade_date"):
        lines.append(f"预期行情日：{freshness.get('expected_latest_trade_date')}")
    if freshness.get("lag_days") is not None:
        lines.append(f"行情滞后：{freshness.get('lag_days')} 天")
    lines.extend(
        [
            f"股票池行情指标缺失：{coverage.get('sector_quote_metric_missing', 0)}/{coverage.get('sector_rows', 0)}",
            f"宏观粗筛分缺失：{coverage.get('combo_score_missing', 0)}/{coverage.get('combo_rows', 0)}",
            f"操作建议可执行：{coverage.get('plan_usable', 0)}/{coverage.get('plan_rows', 0)}",
            f"操作建议缺日线行情：{coverage.get('plan_missing_quotes', 0)}/{coverage.get('plan_rows', 0)}",
            f"阶段串行关系：{'通过' if serial.get('ok') else '异常'}",
        ]
    )
    issues = health.get("issues") or []
    if issues:
        lines.append("")
        lines.append("主要问题：")
        lines.extend(f"- {issue}" for issue in issues)
    return lines


def _candidate_rows(model: dict) -> list[dict]:
    summary = model.get("summary") or {}
    thresholds = summary.get("adaptive_thresholds") or {}
    macro_threshold = float(thresholds.get("macro_potential_threshold") or 80)
    technical_threshold = float(thresholds.get("technical_timing_threshold") or 75)
    combo_by_code = {_code(row.get("code")): row for row in _stage_rows(model, "combo")}
    fine_by_code = {_code(row.get("code")): row for row in _stage_rows(model, "fine")}
    rows = []
    for plan in _stage_rows(model, "plan"):
        code = _code(plan.get("code"))
        if not code:
            continue
        combo = combo_by_code.get(code, {})
        fine = fine_by_code.get(code, {})
        macro_score = _number(combo.get("combo_score"))
        if macro_score is None:
            macro_score = _number(combo.get("coarse_score"))
            if macro_score is not None and macro_score <= 1:
                macro_score *= 100
        technical_score = _number(fine.get("technical_score"))
        if technical_score is None:
            technical_score = _number(plan.get("technical_score"))
        macro_score = macro_score or 0.0
        technical_score = technical_score or 0.0
        if macro_score < macro_threshold or technical_score < technical_threshold:
            continue
        attention_score = _number(plan.get("attention_score"))
        if attention_score is None:
            attention_score = macro_score * 0.65 + technical_score * 0.35
        rows.append(
            {
                "code": code,
                "name": _text(plan.get("name") or fine.get("name") or combo.get("name"), ""),
                "macro_score": macro_score,
                "technical_score": technical_score,
                "attention_score": attention_score,
                "action": _text(plan.get("action")),
                "latest_close": plan.get("latest_close"),
                "planned_entry": plan.get("planned_entry"),
                "initial_stop": plan.get("initial_stop"),
                "risk_pct": plan.get("risk_pct"),
                "horizon_tags": _horizon_tags(plan.get("horizon_tags")),
                "primary_horizon": plan.get("primary_horizon"),
                "horizon_reason": _text(plan.get("horizon_reason"), ""),
                "horizon_data_note": _text(plan.get("horizon_data_note"), ""),
                "take_profit_1r": plan.get("take_profit_1r"),
                "take_profit_2r": plan.get("take_profit_2r"),
                "plan_note": _text(plan.get("plan_note")),
            }
        )
    return sorted(rows, key=lambda row: (row.get("attention_score") or 0, row.get("code") or ""), reverse=True)


def _candidate_lines(candidates: list[dict], total: int) -> list[str]:
    if not candidates:
        return ["暂无符合条件股票。"]
    lines = [f"共命中 {total} 只，本邮件按综合关注分展示前 {len(candidates)} 只。"]
    for idx, item in enumerate(candidates, start=1):
        lines.extend(
            [
                "",
                f"{idx}. {item['code']} {item['name']}",
                f"   宏观潜力：{_format_number(item.get('macro_score'))}",
                f"   技术时机：{_format_number(item.get('technical_score'))}",
                f"   综合关注：{_format_number(item.get('attention_score'))}",
                f"   操作建议：{item.get('action')}",
                f"   适合周期：{_format_horizon_tags(item.get('horizon_tags'))}",
                f"   优先关注：{_text(item.get('primary_horizon'), '证据不足')}",
                f"   周期说明：{_text(item.get('horizon_reason') or item.get('horizon_data_note'), '需人工复核')}",
                f"   最新价：{_format_number(item.get('latest_close'))}",
                f"   计划入场：{_format_number(item.get('planned_entry'))}",
                f"   初始止损：{_format_number(item.get('initial_stop'))}",
                f"   风险比例：{_format_pct(item.get('risk_pct'))}",
                f"   止盈参考：1R {_format_number(item.get('take_profit_1r'))} / 2R {_format_number(item.get('take_profit_2r'))}",
                f"   说明：{item.get('plan_note')}",
            ]
        )
    return lines


def build_daily_email_digest(model: dict, max_candidates: int = 10) -> EmailDigest:
    health = (model.get("summary") or {}).get("health") or {}
    report_date = _health_date(health)
    all_candidates = _candidate_rows(model)
    candidates = all_candidates[:max_candidates]
    lines = [
        f"股票数据更新日报 - {report_date}",
        "",
        "一、数据健康度",
        *_health_lines(health),
        "",
        f"二、好时机+高潜力，最多 {max_candidates} 个",
        *_candidate_lines(candidates, len(all_candidates)),
        "",
        "三、风险提示",
        "本邮件基于公开第三方数据和规则化模型生成，仅用于研究和辅助决策，不构成投资建议。",
    ]
    payload = {
        "report_date": report_date,
        "health": health,
        "candidate_total": len(all_candidates),
        "candidates": candidates,
    }
    return EmailDigest(subject=f"股票数据更新日报 - {report_date}", body="\n".join(lines), payload=payload)
