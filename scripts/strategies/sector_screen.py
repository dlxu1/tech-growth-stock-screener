"""Unified sector screening for a selected base universe."""

from __future__ import annotations

import pandas as pd

from infra.persistence import persist_layer_result
from strategies.coarse import repository as coarse_repository


MAX_SECTOR_TOP = 100

OUTPUT_COLUMNS = [
    "code",
    "name",
    "board_name",
    "market_cap",
    "revenue_yoy",
    "profit_yoy",
    "amount_20d",
    "return_60d",
    "max_drawdown_252d",
    "match_reason",
    "risk_flags",
    "data_note",
]


def _match_reason(row, terms: list[str]) -> str:
    board_name = str(getattr(row, "board_name", "") or "")
    matched = [term for term in terms if term and term in board_name]
    if matched:
        return "board_name 命中：" + "、".join(matched)
    if terms:
        return "已进入板块股票池，需复核板块字段"
    return "未指定板块，来自基础股票池"


def _risk_flags(row) -> str:
    flags = []
    if pd.notna(row.revenue_yoy) and row.revenue_yoy < 0:
        flags.append("营收同比为负")
    if pd.notna(row.profit_yoy) and row.profit_yoy < 0:
        flags.append("净利润同比为负")
    if pd.notna(row.max_drawdown_252d) and row.max_drawdown_252d < -0.35:
        flags.append("历史回撤较大")
    return "；".join(flags) if flags else "未触发主要风险标记"


def _data_note(row) -> str:
    labels = {
        "market_cap": "市值",
        "revenue_yoy": "营收同比",
        "profit_yoy": "净利同比",
        "amount_20d": "20日成交额",
        "return_60d": "60日涨幅",
        "max_drawdown_252d": "年内最大回撤",
    }
    missing = []
    for col in labels:
        value = getattr(row, col, pd.NA)
        if pd.isna(value):
            missing.append(col)
    field_text = "、".join(labels.values())
    if not missing:
        return f"字段完整：{field_text}均有可用数据；板块筛选按市值降序展示，用于研究池观察，不构成买入建议。"
    missing_text = "、".join(labels[col] for col in missing)
    return (
        f"检查字段：{field_text}；字段缺失：{missing_text}暂无可用数据，缺失项在看板中显示为 N/A；"
        "板块筛选仍按市值降序展示，缺失市值时该行排序可信度需复核；用于研究池观察，不构成买入建议。"
    )


def filter_by_sector(base: pd.DataFrame, sector_text: str | None) -> tuple[pd.DataFrame, dict]:
    return coarse_repository.filter_by_sector(base, sector_text)


def run(args) -> tuple[pd.DataFrame, dict]:
    base, meta = coarse_repository.build_base_universe(args)
    requested_top = int(getattr(args, "top", MAX_SECTOR_TOP) or MAX_SECTOR_TOP)
    selected_industry = str(getattr(args, "selected_industry", "") or "").strip()
    sector_text = str(getattr(args, "sector", "") or "").strip()
    sector_terms = [term.strip() for term in sector_text.split(",") if term.strip()]
    if selected_industry and selected_industry not in sector_terms:
        sector_terms = [selected_industry]
    capped_top = len(base) if selected_industry else min(requested_top, MAX_SECTOR_TOP)
    if base.empty:
        result = pd.DataFrame(columns=OUTPUT_COLUMNS)
        meta.update(
            {
                "strategy": "sector_screen",
                "requested_top": requested_top,
                "capped_top": capped_top,
                "selected": 0,
                "selected_industry": selected_industry,
                "selected_industry_pool_label": meta.get("selected_industry_pool_label")
                or ("行业全成分股" if meta.get("selected_industry_pool_kind") == "full" else "缓存样本代理"),
                "selected_industry_pool_kind": meta.get("selected_industry_pool_kind") or ("full" if selected_industry else "sample"),
                "selected_industry_pool_source": meta.get("selected_industry_pool_source") or meta.get("universe_source") or "",
            }
        )
        persist_layer_result("sector_screen", args, result, meta)
        return result, meta

    selected_pool = base.copy()
    for col in ["market_cap", "revenue_yoy", "profit_yoy", "amount_20d", "return_60d", "max_drawdown_252d"]:
        if col not in selected_pool.columns:
            selected_pool[col] = pd.NA
    selected_pool["selected_industry"] = selected_industry
    selected_pool["pool_source_label"] = meta.get("selected_industry_pool_label") or ("行业全成分股" if meta.get("selected_industry_pool_kind") == "full" else "缓存样本代理")
    selected_pool["pool_source_kind"] = meta.get("selected_industry_pool_kind") or ("full" if selected_industry else "sample")
    selected_pool["pool_source_note"] = meta.get("selected_industry_fallback_note") or meta.get("selected_industry_pool_source") or meta.get("universe_source") or ""
    selected_pool["match_reason"] = selected_pool.apply(lambda row: _match_reason(row, sector_terms), axis=1)
    selected_pool["risk_flags"] = selected_pool.apply(_risk_flags, axis=1)
    selected_pool["data_note"] = selected_pool.apply(_data_note, axis=1)
    selected = selected_pool.sort_values(["market_cap", "code"], ascending=[False, True]).head(capped_top).copy()
    for col in OUTPUT_COLUMNS:
        if col not in selected.columns:
            selected[col] = pd.NA
    result = selected[OUTPUT_COLUMNS]
    meta.update(
        {
            "strategy": "sector_screen",
            "requested_top": requested_top,
            "capped_top": capped_top,
            "selected": len(result),
            "max_top": MAX_SECTOR_TOP,
            "selected_industry": selected_industry,
            "selected_industry_pool_label": selected_pool["pool_source_label"].iloc[0] if not selected_pool.empty else meta.get("selected_industry_pool_label"),
            "selected_industry_pool_kind": selected_pool["pool_source_kind"].iloc[0] if not selected_pool.empty else meta.get("selected_industry_pool_kind"),
            "selected_industry_pool_source": selected_pool["pool_source_note"].iloc[0] if not selected_pool.empty else meta.get("selected_industry_pool_source"),
        }
    )
    persist_layer_result("sector_screen", args, result, meta)
    return result, meta
