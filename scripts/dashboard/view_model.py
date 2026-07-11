"""Build JSON-serializable data for the interactive dashboard."""

from __future__ import annotations

from typing import Any

import pandas as pd


STAGE_TITLES = {
    "sector_screen": "板块筛选",
    "combo": "宏观粗筛",
    "fine": "技术细筛",
    "plan": "操作计划",
    "allocation": "个人配置",
}

STAGE_ORDER = ["sector_screen", "combo", "fine", "plan", "allocation"]


def _json_value(value: Any) -> Any:
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _records(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    clean = df.astype(object).where(pd.notna(df), None)
    records = []
    for row in clean.to_dict(orient="records"):
        records.append({str(key): _json_value(value) for key, value in row.items()})
    return records


def _meta_dict(meta: Any) -> dict:
    if meta is None:
        return {}
    if isinstance(meta, dict):
        items = meta.items()
    elif hasattr(meta, "__dict__"):
        items = vars(meta).items()
    else:
        return {"value": _json_value(meta)}
    return {str(key): _json_value(value) for key, value in items}


def _trace_label(row: dict) -> str:
    for key in ["portfolio_action", "action", "technical_score", "coarse_score", "combo_score", "name"]:
        value = row.get(key)
        if value not in {None, ""}:
            return str(value)
    return "出现"


def build_dashboard_view_model(stages: dict[str, pd.DataFrame], metas: dict[str, dict]) -> dict:
    """Normalize stage outputs into one dashboard model."""

    stage_models = []
    traces: dict[str, list[dict]] = {}
    stage_counts = {}
    action_counts = {}

    for key in STAGE_ORDER:
        df = stages.get(key, pd.DataFrame())
        meta = _meta_dict(metas.get(key, {}))
        rows = _records(df)
        stage_counts[key] = len(rows)
        stage_models.append(
            {
                "key": key,
                "title": STAGE_TITLES.get(key, key),
                "row_count": len(rows),
                "meta": meta,
                "columns": list(df.columns) if not df.empty else [],
                "rows": rows,
            }
        )
        if key == "allocation":
            for row in rows:
                action = row.get("portfolio_action")
                if action:
                    action_counts[action] = action_counts.get(action, 0) + 1
        for row in rows:
            code = str(row.get("code") or "").zfill(6)
            if not code or code == "000000":
                continue
            traces.setdefault(code, []).append(
                {
                    "stage": key,
                    "title": STAGE_TITLES.get(key, key),
                    "name": row.get("name", ""),
                    "label": _trace_label(row),
                    "row": row,
                }
            )

    allocation_meta = metas.get("allocation", {})
    return {
        "summary": {
            "stage_counts": stage_counts,
            "action_counts": action_counts,
            "capital": allocation_meta.get("capital"),
            "core_etf_budget": allocation_meta.get("core_etf_budget"),
            "satellite_stock_budget": allocation_meta.get("satellite_stock_budget"),
            "cash_reserve": allocation_meta.get("cash_reserve"),
        },
        "stages": stage_models,
        "traces": traces,
    }
