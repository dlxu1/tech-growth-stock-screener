"""Display-only horizon annotations for dashboard candidates."""

from __future__ import annotations

from typing import Any


HORIZON_ORDER = ["长线", "中线", "短线"]
LONG_STRATEGY_HINTS = (
    "高 ROE + 合理估值",
    "高毛利率 + 营收增长",
    "市值前排 + 营收净利双增长",
    "低 PE + 正增长",
    "低 PB + 正盈利",
    "回撤较小 + 正增长",
)
SHORT_STRATEGIES = {"breakout_buy", "pullback_ma_buy", "volume_confirm_buy"}


def _number(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _strategy_text(row: dict) -> str:
    return "、".join(
        str(row.get(key) or "")
        for key in ["matched_strategies", "coarse_strategies", "coarse_strategy_title"]
    )


def _has_long_strategy(row: dict) -> bool:
    text = _strategy_text(row)
    return any(hint in text for hint in LONG_STRATEGY_HINTS)


def annotate_horizon(row: dict) -> dict:
    """Return a copy of row with horizon fields added.

    The annotation is intentionally conservative and display-only. It does not
    change scores, thresholds, selection, or operation rules.
    """

    out = dict(row)
    combo = _number(out.get("combo_score") if out.get("combo_score") is not None else out.get("coarse_score"))
    if combo is not None and combo <= 1:
        combo *= 100
    technical = _number(out.get("technical_score"))
    quality = _number(out.get("quality_score"))
    risk = _number(out.get("risk_control_score"))
    growth = _number(out.get("growth_score"))
    tags: list[str] = []
    reasons: list[str] = []

    long_ok = (
        quality is not None
        and risk is not None
        and growth is not None
        and quality >= 75
        and risk >= 65
        and growth >= 60
        and _has_long_strategy(out)
    )
    if long_ok:
        tags.append("长线")
        reasons.append("基本面质量、成长和回撤控制证据较强")

    medium_ok = combo is not None and technical is not None and combo >= 80 and technical >= 75
    if medium_ok:
        tags.append("中线")
        reasons.append("宏观潜力与技术时机共振")

    entry = _number(out.get("planned_entry"))
    stop = _number(out.get("initial_stop"))
    risk_pct = _number(out.get("risk_pct"))
    short_ok = (
        _bool(out.get("usable_for_plan"))
        and str(out.get("primary_strategy") or "") in SHORT_STRATEGIES
        and entry is not None
        and entry > 0
        and stop is not None
        and stop > 0
        and risk_pct is not None
        and 0 < risk_pct <= 0.12
    )
    if short_ok:
        tags.append("短线")
        reasons.append("已有可执行入场、止损和风险计划")

    out["horizon_tags"] = [tag for tag in HORIZON_ORDER if tag in tags]
    if "短线" in tags:
        primary = "短线"
    elif "中线" in tags:
        primary = "中线"
    elif "长线" in tags:
        primary = "长线"
    else:
        primary = None
    out["primary_horizon"] = primary
    out["horizon_reason"] = "，且".join(reasons) + "。" if reasons else ""
    out["horizon_data_note"] = "" if tags else "证据不足，需人工复核"
    return out
