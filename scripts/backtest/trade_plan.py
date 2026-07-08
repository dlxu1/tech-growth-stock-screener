"""Next-session trading plan rules for fine-screened candidates.

This module consumes strategy outputs and cached quotes_daily rows only. It
does not fetch remote data directly.
"""

from __future__ import annotations

import sqlite3

import pandas as pd

from common import db_path
from backtest.plan import repository as plan_repository
from strategies.fine.technical import run as run_fine


OUTPUT_COLUMNS = [
    "code",
    "name",
    "board_name",
    "action",
    "primary_strategy",
    "technical_score",
    "technical_reasons",
    "basis_trade_date",
    "latest_close",
    "breakout_trigger",
    "pullback_low",
    "pullback_high",
    "volume_confirm_amount",
    "planned_entry",
    "initial_stop",
    "risk_pct",
    "take_profit_1r",
    "take_profit_2r",
    "trailing_stop_rule",
    "position_cap",
    "cancel_conditions",
    "stop_conditions",
    "data_status",
    "missing_data_reason",
    "missing_data_impact",
    "usable_for_plan",
    "plan_note",
]


def _to_float(value) -> float:
    try:
        if pd.isna(value):
            return float("nan")
        return float(value)
    except Exception:
        return float("nan")


def _last(series: pd.Series) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return float("nan")
    return float(clean.iloc[-1])


def _load_quotes(codes: list[str]) -> pd.DataFrame:
    if not codes:
        return pd.DataFrame(columns=["code", "trade_date", "open", "high", "low", "close", "volume", "amount"])
    conn = sqlite3.connect(db_path())
    placeholders = ",".join("?" for _ in codes)
    try:
        prices = pd.read_sql_query(
            f"""
            select code, trade_date, open, high, low, close, volume, amount, source, updated_at
            from quotes_daily
            where code in ({placeholders})
            order by code, trade_date, updated_at
            """,
            conn,
            params=codes,
        )
    except Exception:
        return pd.DataFrame(columns=["code", "trade_date", "open", "high", "low", "close", "volume", "amount"])
    if prices.empty:
        return prices
    prices["code"] = prices["code"].astype(str).str.zfill(6)
    prices["trade_date"] = pd.to_datetime(prices["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    prices = prices.dropna(subset=["trade_date", "close"])
    return prices.drop_duplicates(["code", "trade_date"], keep="last")


def _atr(group: pd.DataFrame, window: int = 14) -> float:
    high = pd.to_numeric(group["high"], errors="coerce")
    low = pd.to_numeric(group["low"], errors="coerce")
    close = pd.to_numeric(group["close"], errors="coerce")
    prev_close = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return _last(tr.rolling(window, min_periods=1).mean())


def _score_position_cap(score: float, max_position: float) -> float:
    if pd.isna(score) or score < 60:
        return 0.0
    if score >= 85:
        return max_position
    if score >= 75:
        return min(max_position, 0.20)
    return min(max_position, 0.12)


def _strategy_for(row, latest_close: float) -> tuple[str, str]:
    score = _to_float(row.technical_score)
    reasons = str(row.technical_reasons)
    if pd.isna(latest_close) or score < 60:
        return "暂不交易", "no_trade"
    if score >= 80 and "放量突破" in reasons:
        return "允许条件买入", "breakout_buy"
    if score >= 70 and "趋势强" in reasons:
        return "等待回踩买入", "pullback_ma_buy"
    if score >= 60 and ("量能改善" in reasons or "动量较好" in reasons):
        return "等待放量确认", "volume_confirm_buy"
    return "观察", "watch"


def _plan_one(row, group: pd.DataFrame, args) -> dict:
    if group.empty or pd.isna(row.latest_trade_date):
        return {
            "code": row.code,
            "name": row.name,
            "board_name": row.board_name,
            "action": "暂不交易",
            "primary_strategy": "no_data",
            "technical_score": _to_float(row.technical_score),
            "technical_reasons": row.technical_reasons,
            "data_status": "missing_quotes",
            "missing_data_reason": "quotes_daily 缺少该股票日线记录，通常是未同步 daily_prices、上游源失败，或股票代码不在本地缓存中。",
            "missing_data_impact": "无法计算突破价、回踩区间、ATR止损、成交额确认和移动止损；技术评分被降为0，操作计划置为暂不交易。",
            "usable_for_plan": False,
            "plan_note": "缺少 quotes_daily，无法生成明日买入和止损价位；先同步 daily_prices。",
        }

    group = group.sort_values("trade_date").copy()
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        group[col] = pd.to_numeric(group[col], errors="coerce")
    latest = group.iloc[-1]
    close = group["close"]
    high = group["high"]
    low = group["low"]
    amount = group["amount"]

    latest_close = _to_float(latest["close"])
    latest_high = _to_float(latest["high"])
    ma5 = _last(close.rolling(5, min_periods=1).mean())
    ma10 = _last(close.rolling(10, min_periods=1).mean())
    ma20 = _last(close.rolling(20, min_periods=1).mean())
    high20_prior = _last(high.shift(1).rolling(20, min_periods=1).max())
    recent_low = _last(low.rolling(10, min_periods=1).min())
    atr14 = _atr(group)
    amount20 = _last(amount.rolling(20, min_periods=1).mean())

    action, strategy = _strategy_for(row, latest_close)
    breakout_base = max(value for value in [latest_high, high20_prior, latest_close] if pd.notna(value))
    breakout_trigger = breakout_base * (1 + args.breakout_buffer)
    pullback_low = min(value for value in [ma10, ma20, latest_close] if pd.notna(value)) * 0.995
    pullback_high = max(value for value in [ma5, ma10, latest_close] if pd.notna(value)) * 1.005
    volume_confirm_amount = amount20 * args.volume_multiplier if pd.notna(amount20) else float("nan")

    if strategy == "breakout_buy":
        planned_entry = breakout_trigger
    elif strategy == "pullback_ma_buy":
        planned_entry = (pullback_low + pullback_high) / 2
    elif strategy == "volume_confirm_buy":
        planned_entry = latest_close * (1 + args.breakout_buffer)
    else:
        planned_entry = float("nan")

    fixed_stop = planned_entry * (1 - args.stop_pct) if pd.notna(planned_entry) else float("nan")
    atr_stop = planned_entry - args.atr_stop_multiplier * atr14 if pd.notna(planned_entry) and pd.notna(atr14) else float("nan")
    ma_stop = ma20 * 0.99 if pd.notna(ma20) else float("nan")
    low_stop = recent_low * 0.995 if pd.notna(recent_low) else float("nan")
    stop_candidates = [v for v in [fixed_stop, atr_stop, ma_stop, low_stop] if pd.notna(v) and pd.notna(planned_entry) and v < planned_entry]
    initial_stop = max(stop_candidates) if stop_candidates else fixed_stop
    risk = planned_entry - initial_stop if pd.notna(planned_entry) and pd.notna(initial_stop) else float("nan")
    risk_pct = risk / planned_entry if pd.notna(risk) and pd.notna(planned_entry) and planned_entry else float("nan")
    take_profit_1r = planned_entry + risk if pd.notna(risk) else float("nan")
    take_profit_2r = planned_entry + 2 * risk if pd.notna(risk) else float("nan")

    cancel_conditions = [
        f"明日高开超过今日收盘 {args.max_gap_up:.1%} 不追",
        "开盘直接跌破初始止损价则取消买入",
        "未触发入场价且成交额不足确认阈值则不买",
    ]
    if strategy == "pullback_ma_buy":
        cancel_conditions.append("回踩跌破 MA20 后不能快速收回则不买")
    if strategy == "breakout_buy":
        cancel_conditions.append("突破后跌回突破价下方且放量转弱则撤单")

    stop_conditions = [
        "买入后跌破初始止损价立即止损",
        "收盘跌破 MA20 且 MACD/量能同步转弱则退出",
        f"盈利超过 {args.move_stop_profit:.1%} 后止损抬到成本价",
    ]
    trailing_stop_rule = f"盈利超过 {args.trailing_profit:.1%} 后，用最高收盘价回撤 {args.trailing_drawdown:.1%} 或跌破 MA10 作为移动止损"
    position_cap = _score_position_cap(_to_float(row.technical_score), args.max_position)
    note = "规则计划，需用明日实际开盘、成交额和盘中价触发；不是保证成交价。"
    data_status = "complete"
    missing_data_reason = "无关键数据缺失。"
    missing_data_impact = "可生成完整入场、止损、止盈和仓位规则。"
    if len(group) < 20:
        data_status = "degraded_short_history"
        missing_data_reason = f"quotes_daily 仅有 {len(group)} 个交易日，少于20日指标窗口。"
        missing_data_impact = "MA20、20日高点、20日成交额均值、20日回撤等指标使用短样本替代，计划可用但可靠性下降。"
        note = f"日线样本不足20日，仅有{len(group)}日，计划已降级；" + note

    return {
        "code": row.code,
        "name": row.name,
        "board_name": row.board_name,
        "action": action,
        "primary_strategy": strategy,
        "technical_score": _to_float(row.technical_score),
        "technical_reasons": row.technical_reasons,
        "basis_trade_date": latest["trade_date"],
        "latest_close": latest_close,
        "breakout_trigger": breakout_trigger,
        "pullback_low": pullback_low,
        "pullback_high": pullback_high,
        "volume_confirm_amount": volume_confirm_amount,
        "planned_entry": planned_entry,
        "initial_stop": initial_stop,
        "risk_pct": risk_pct,
        "take_profit_1r": take_profit_1r,
        "take_profit_2r": take_profit_2r,
        "trailing_stop_rule": trailing_stop_rule,
        "position_cap": position_cap,
        "cancel_conditions": "；".join(cancel_conditions),
        "stop_conditions": "；".join(stop_conditions),
        "data_status": data_status,
        "missing_data_reason": missing_data_reason,
        "missing_data_impact": missing_data_impact,
        "usable_for_plan": bool(strategy not in {"no_trade"} and pd.notna(planned_entry)),
        "plan_note": note,
    }


def run_trade_plan(args) -> tuple[pd.DataFrame, dict]:
    fine, fine_meta = run_fine(args)
    meta = {
        **fine_meta,
        "plan": "next_session_trade_plan",
        "selected": len(fine),
        "breakout_buffer": args.breakout_buffer,
        "volume_multiplier": args.volume_multiplier,
        "stop_pct": args.stop_pct,
        "max_gap_up": args.max_gap_up,
        "db_path": str(db_path()),
    }
    if fine.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS), meta
    codes = fine["code"].astype(str).str.zfill(6).tolist()
    quotes = plan_repository.load_quotes(codes)
    rows = []
    for row in fine.itertuples(index=False):
        code = str(row.code).zfill(6)
        group = quotes[quotes["code"] == code] if not quotes.empty else pd.DataFrame()
        rows.append(_plan_one(row, group, args))
    result = pd.DataFrame(rows)
    for col in OUTPUT_COLUMNS:
        if col not in result.columns:
            result[col] = pd.NA
    meta["data_quality"] = {
        "complete": int((result["data_status"] == "complete").sum()) if "data_status" in result else 0,
        "degraded": int(result["data_status"].astype(str).str.startswith("degraded").sum()) if "data_status" in result else 0,
        "missing": int(result["data_status"].astype(str).str.startswith("missing").sum()) if "data_status" in result else 0,
        "usable_for_plan": int(result["usable_for_plan"].fillna(False).astype(bool).sum()) if "usable_for_plan" in result else 0,
    }
    result = result[OUTPUT_COLUMNS].sort_values(["technical_score", "position_cap"], ascending=[False, False])
    return result, meta
