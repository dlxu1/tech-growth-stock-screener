"""Personal portfolio allocation layer for small technology-stock accounts."""

from __future__ import annotations

from typing import Any

import pandas as pd

from plan.trade_plan import run_trade_plan


OUTPUT_COLUMNS = [
    "code",
    "name",
    "portfolio_action",
    "source_action",
    "budget_status",
    "latest_close",
    "lot_cost",
    "initial_buy_budget",
    "max_position_amount",
    "planned_entry",
    "initial_stop",
    "risk_pct",
    "position_cap",
    "allocation_note",
]


def _to_float(value: Any) -> float:
    try:
        if pd.isna(value):
            return float("nan")
        return float(value)
    except Exception:
        return float("nan")


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _money(value: float) -> int:
    if pd.isna(value):
        return 0
    return int(round(value))


def _budget_status(lot_cost: int, max_position_amount: int, satellite_budget: int) -> str:
    if lot_cost <= 0:
        return "缺少价格"
    if lot_cost > max_position_amount:
        return "一手超过单股仓位上限"
    if lot_cost > satellite_budget:
        return "一手超过个股卫星仓"
    return "预算内"


def _portfolio_action(source_action: str, usable: bool, budget_status: str) -> str:
    if not usable:
        return "暂不交易"
    if budget_status != "预算内":
        return "只做风向标"
    if "允许" in source_action:
        return "可条件买入"
    if "等待" in source_action:
        return "等待触发"
    return "观察"


def build_allocation_plan(
    trade_plan: pd.DataFrame,
    *,
    capital: float = 15000,
    target_return: float = 0.10,
    core_etf_pct: float = 0.60,
    satellite_stock_pct: float = 0.20,
    cash_pct: float = 0.20,
    etf_tranches: int = 3,
    lot_size: int = 100,
    initial_single_stock_pct: float = 0.12,
    max_single_stock_pct: float = 0.20,
) -> tuple[pd.DataFrame, dict]:
    """Convert trade-plan rows into a capital-aware personal allocation plan."""

    capital_amount = _money(capital)
    core_etf_budget = _money(capital_amount * core_etf_pct)
    satellite_budget = _money(capital_amount * satellite_stock_pct)
    cash_reserve = _money(capital_amount * cash_pct)
    initial_buy_budget = _money(capital_amount * initial_single_stock_pct)
    meta = {
        "plan": "personal_tech_allocation",
        "capital": capital_amount,
        "target_return": target_return,
        "annual_target_profit": _money(capital_amount * target_return),
        "core_etf_pct": core_etf_pct,
        "satellite_stock_pct": satellite_stock_pct,
        "cash_pct": cash_pct,
        "core_etf_budget": core_etf_budget,
        "satellite_stock_budget": satellite_budget,
        "cash_reserve": cash_reserve,
        "etf_tranches": etf_tranches,
        "etf_tranche_amount": _money(core_etf_budget / etf_tranches) if etf_tranches else 0,
        "lot_size": lot_size,
        "initial_single_stock_pct": initial_single_stock_pct,
        "max_single_stock_pct": max_single_stock_pct,
    }

    if trade_plan.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS), meta

    rows = []
    for row in trade_plan.itertuples(index=False):
        data = row._asdict()
        latest_close = _to_float(data.get("latest_close"))
        source_action = str(data.get("action", "观察"))
        usable = _to_bool(data.get("usable_for_plan"))
        position_cap = _to_float(data.get("position_cap"))
        if pd.isna(position_cap) or position_cap <= 0:
            position_cap = max_single_stock_pct
        effective_position_cap = min(position_cap, max_single_stock_pct)
        max_position_amount = _money(capital_amount * effective_position_cap)
        lot_cost = _money(latest_close * lot_size) if pd.notna(latest_close) else 0
        budget_status = _budget_status(lot_cost, max_position_amount, satellite_budget)
        portfolio_action = _portfolio_action(source_action, usable, budget_status)
        note = (
            f"一手成本约 {lot_cost} 元；单股仓位上限约 {max_position_amount} 元。"
            if lot_cost
            else "缺少最新收盘价，无法做一手预算检查。"
        )
        if budget_status != "预算内":
            note += f" 对 {capital_amount} 元账户不适合作为直接买入标的，可作为科技板块风向标。"
        rows.append(
            {
                "code": str(data.get("code", "")).zfill(6),
                "name": data.get("name", ""),
                "portfolio_action": portfolio_action,
                "source_action": source_action,
                "budget_status": budget_status,
                "latest_close": latest_close,
                "lot_cost": lot_cost,
                "initial_buy_budget": min(initial_buy_budget, max_position_amount),
                "max_position_amount": max_position_amount,
                "planned_entry": _to_float(data.get("planned_entry")),
                "initial_stop": _to_float(data.get("initial_stop")),
                "risk_pct": _to_float(data.get("risk_pct")),
                "position_cap": effective_position_cap,
                "allocation_note": note,
            }
        )

    result = pd.DataFrame(rows)
    for col in OUTPUT_COLUMNS:
        if col not in result.columns:
            result[col] = pd.NA
    action_rank = {"可条件买入": 0, "等待触发": 1, "观察": 2, "只做风向标": 3, "暂不交易": 4}
    result["_rank"] = result["portfolio_action"].map(action_rank).fillna(9)
    result = result.sort_values(["_rank", "position_cap"], ascending=[True, False]).drop(columns=["_rank"])
    return result[OUTPUT_COLUMNS], meta


def run_allocation_plan(args) -> tuple[pd.DataFrame, dict]:
    """Run the existing trade plan, then apply personal account constraints."""

    trade_plan, trade_meta = run_trade_plan(args)
    result, meta = build_allocation_plan(
        trade_plan,
        capital=args.capital,
        target_return=args.target_return,
        core_etf_pct=args.core_etf_pct,
        satellite_stock_pct=args.satellite_stock_pct,
        cash_pct=args.cash_pct,
        etf_tranches=args.etf_tranches,
        initial_single_stock_pct=args.initial_single_stock_pct,
        max_single_stock_pct=args.max_single_stock_pct,
    )
    meta.update(
        {
            "trade_plan": trade_meta,
            "selected": len(result),
            "action_counts": result["portfolio_action"].value_counts().to_dict() if not result.empty else {},
        }
    )
    return result, meta
