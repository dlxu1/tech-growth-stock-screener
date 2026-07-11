"""Build JSON-serializable data for the interactive dashboard."""

from __future__ import annotations

from typing import Any

import pandas as pd

from dashboard.stock_types import StockTypeRules, classify_stock_type


STAGE_TITLES = {
    "sector_screen": "股票池",
    "combo": "宏观粗筛",
    "fine": "技术分析",
    "plan": "操作建议",
}

STAGE_ORDER = ["sector_screen", "combo", "fine", "plan"]


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
    for key in ["action", "technical_score", "coarse_score", "combo_score", "name"]:
        value = row.get(key)
        if value not in {None, ""}:
            return str(value)
    return "出现"


def _annotate_stage_rows(key: str, rows: list[dict], stock_type_rules: StockTypeRules | None = None) -> list[dict]:
    if key != "sector_screen":
        return rows
    annotated = []
    for row in rows:
        if row.get("stock_type") and row.get("stock_type_note"):
            annotated.append(row)
            continue
        stock_type, note = classify_stock_type(row, stock_type_rules)
        next_row = {**row, "stock_type": stock_type, "stock_type_note": note}
        annotated.append(next_row)
    return annotated


def _stock_type_counts(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        stock_type = str(row.get("stock_type") or "未分类")
        counts[stock_type] = counts.get(stock_type, 0) + 1
    return counts


def build_dashboard_view_model(
    stages: dict[str, pd.DataFrame],
    metas: dict[str, dict],
    stock_type_rules: StockTypeRules | None = None,
) -> dict:
    """Normalize stage outputs into one dashboard model."""

    stage_models = []
    traces: dict[str, list[dict]] = {}
    stage_counts = {}
    action_counts = {}

    for key in STAGE_ORDER:
        df = stages.get(key, pd.DataFrame())
        meta = _meta_dict(metas.get(key, {}))
        rows = _annotate_stage_rows(key, _records(df), stock_type_rules)
        stage_counts[key] = len(rows)
        columns = list(df.columns) if not df.empty else []
        if key == "sector_screen" and rows:
            columns = [*columns, *[col for col in ["stock_type", "stock_type_note"] if col not in columns]]
        stage_models.append(
            {
                "key": key,
                "title": STAGE_TITLES.get(key, key),
                "row_count": len(rows),
                "meta": meta,
                "columns": columns,
                "rows": rows,
            }
        )
        if key == "plan":
            for row in rows:
                action = row.get("action")
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

    sector_rows = next((stage["rows"] for stage in stage_models if stage["key"] == "sector_screen"), [])
    return {
        "summary": {
            "stage_counts": stage_counts,
            "action_counts": action_counts,
            "stock_type_counts": _stock_type_counts(sector_rows),
        },
        "stages": stage_models,
        "traces": traces,
    }
