"""Data-health checks for dashboard outputs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _stage_rows(model: dict, key: str) -> list[dict]:
    for stage in model.get("stages", []):
        if stage.get("key") == key:
            return list(stage.get("rows") or [])
    return []


def _code_set(rows: list[dict]) -> set[str]:
    codes = set()
    for row in rows:
        code = str(row.get("code") or "").zfill(6)
        if code and code != "000000":
            codes.add(code)
    return codes


def _missing(value: Any) -> bool:
    return value is None or value == ""


def _as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _date_value(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _latest_trade_date(fine_rows: list[dict], plan_rows: list[dict]) -> str | None:
    dates = []
    for row in [*fine_rows, *plan_rows]:
        for key in ["latest_trade_date", "basis_trade_date"]:
            parsed = _date_value(row.get(key))
            if parsed:
                dates.append(parsed)
    return max(dates).isoformat() if dates else None


def _score_range_issues(rows: list[dict], stage: str, columns: list[str]) -> dict[str, list[str]]:
    issues: dict[str, list[str]] = {}
    for col in columns:
        bad = []
        for row in rows:
            value = _as_float(row.get(col))
            if value is not None and (value < 0 or value > 100):
                bad.append(str(row.get("code") or ""))
        if bad:
            issues[f"{stage}.{col}"] = bad
    return issues


def _health_score(issue_count: int, coverage: dict, serial_ok: bool, freshness: dict) -> int:
    score = 100
    if not serial_ok:
        score -= 25
    score -= min(25, int(coverage["sector_quote_metric_missing_ratio"] * 25))
    score -= min(25, int(coverage["plan_missing_quotes_ratio"] * 35))
    if freshness.get("lag_days") is not None:
        score -= min(15, max(0, int(freshness["lag_days"])) * 5)
    score -= min(20, issue_count * 5)
    return max(0, min(100, score))


def audit_dashboard_model(model: dict, expected_latest_trade_date: str | None = None) -> dict:
    """Return a JSON-serializable health report for a dashboard view model."""

    sector_rows = _stage_rows(model, "sector_screen")
    combo_rows = _stage_rows(model, "combo")
    fine_rows = _stage_rows(model, "fine")
    plan_rows = _stage_rows(model, "plan")

    sector_codes = _code_set(sector_rows)
    combo_codes = _code_set(combo_rows)
    fine_codes = _code_set(fine_rows)
    plan_codes = _code_set(plan_rows)

    serial = {
        "combo_not_in_sector": sorted(combo_codes - sector_codes),
        "fine_not_in_combo": sorted(fine_codes - combo_codes),
        "plan_not_in_fine": sorted(plan_codes - fine_codes),
    }
    serial["ok"] = not serial["combo_not_in_sector"] and not serial["fine_not_in_combo"] and not serial["plan_not_in_fine"]

    sector_quote_metric_missing = sum(
        1
        for row in sector_rows
        if any(_missing(row.get(col)) for col in ["amount_20d", "return_60d", "max_drawdown_252d"])
    )
    plan_missing_quotes = sum(1 for row in plan_rows if row.get("data_status") == "missing_quotes")
    plan_usable = sum(1 for row in plan_rows if bool(row.get("usable_for_plan")))
    plan_complete_price_missing = sum(
        1
        for row in plan_rows
        if row.get("data_status") == "complete" and (_missing(row.get("planned_entry")) or _missing(row.get("initial_stop")))
    )
    coverage = {
        "sector_rows": len(sector_rows),
        "sector_quote_metric_missing": sector_quote_metric_missing,
        "sector_quote_metric_missing_ratio": sector_quote_metric_missing / len(sector_rows) if sector_rows else 0,
        "plan_rows": len(plan_rows),
        "plan_usable": plan_usable,
        "plan_usable_ratio": plan_usable / len(plan_rows) if plan_rows else 0,
        "plan_missing_quotes": plan_missing_quotes,
        "plan_missing_quotes_ratio": plan_missing_quotes / len(plan_rows) if plan_rows else 0,
        "plan_complete_price_missing": plan_complete_price_missing,
    }

    latest = _latest_trade_date(fine_rows, plan_rows)
    expected_date = expected_latest_trade_date
    latest_date = _date_value(latest)
    expected = _date_value(expected_date)
    freshness = {
        "latest_trade_date": latest,
        "expected_latest_trade_date": expected_date,
        "lag_days": (expected - latest_date).days if expected and latest_date else None,
    }

    score_ranges = {}
    score_ranges.update(_score_range_issues(combo_rows, "combo", ["combo_score", "growth_score", "quality_score", "risk_control_score"]))
    score_ranges.update(_score_range_issues(fine_rows, "fine", ["technical_score", "coarse_score"]))
    score_ranges.update(_score_range_issues(plan_rows, "plan", ["technical_score", "attention_score"]))

    missing_quotes = [
        {"code": str(row.get("code") or "").zfill(6), "name": row.get("name", "")}
        for row in plan_rows
        if row.get("data_status") == "missing_quotes"
    ]

    issues = []
    if not serial["ok"]:
        issues.append("阶段串行关系异常：存在下游股票不在上游结果中")
    if coverage["sector_quote_metric_missing"]:
        issues.append(f"股票池行情指标缺失：{coverage['sector_quote_metric_missing']}/{coverage['sector_rows']}")
    if coverage["plan_missing_quotes"]:
        issues.append(f"操作建议缺日线行情：{coverage['plan_missing_quotes']}/{coverage['plan_rows']}")
    if coverage["plan_complete_price_missing"]:
        issues.append(f"完整行情计划缺少价格字段：{coverage['plan_complete_price_missing']}/{coverage['plan_rows']}")
    if freshness["lag_days"] is not None and freshness["lag_days"] > 0:
        issues.append(f"行情日期落后：{freshness['lag_days']} 天")
    if score_ranges:
        issues.append("存在分数超出 0-100 范围")

    health_score = _health_score(len(score_ranges), coverage, bool(serial["ok"]), freshness)
    return {
        "health_score": health_score,
        "stage_counts": model.get("summary", {}).get("stage_counts", {}),
        "freshness": freshness,
        "coverage": coverage,
        "serial": serial,
        "score_ranges": score_ranges,
        "missing_quotes": missing_quotes,
        "issues": issues,
    }


def render_health_markdown(audit: dict) -> str:
    freshness = audit.get("freshness", {})
    coverage = audit.get("coverage", {})
    lines = [
        f"数据健康度：{audit.get('health_score', 0)}/100",
        f"最新行情日：{freshness.get('latest_trade_date') or 'N/A'}",
    ]
    if freshness.get("expected_latest_trade_date"):
        lines.append(f"预期行情日：{freshness.get('expected_latest_trade_date')}")
    if freshness.get("lag_days") is not None:
        lines.append(f"行情滞后：{freshness.get('lag_days')} 天")
    lines.extend(
        [
            f"股票池行情指标缺失：{coverage.get('sector_quote_metric_missing', 0)}/{coverage.get('sector_rows', 0)}",
            f"操作建议可执行：{coverage.get('plan_usable', 0)}/{coverage.get('plan_rows', 0)}",
            f"操作建议缺日线行情：{coverage.get('plan_missing_quotes', 0)}/{coverage.get('plan_rows', 0)}",
            f"阶段串行关系：{'通过' if audit.get('serial', {}).get('ok') else '异常'}",
        ]
    )
    issues = audit.get("issues") or []
    if issues:
        lines.append("")
        lines.append("主要问题：")
        lines.extend(f"- {issue}" for issue in issues)
    missing = audit.get("missing_quotes") or []
    if missing:
        lines.append("")
        lines.append("缺日线股票：")
        lines.extend(f"- {item.get('code')} {item.get('name')}" for item in missing[:20])
    return "\n".join(lines)
