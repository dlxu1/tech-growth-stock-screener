"""Operation-plan backtests for dashboard trade advice."""

from __future__ import annotations

from typing import Iterable
from types import SimpleNamespace

import pandas as pd


MACRO_POTENTIAL_THRESHOLD = 80.0
TECHNICAL_TIMING_THRESHOLD = 75.0
DEFAULT_PROFIT_TARGET_PCT = 0.05
EXECUTABLE_STRATEGIES = {"breakout_buy", "pullback_ma_buy", "volume_confirm_buy"}


def _num(value) -> float | None:
    try:
        if pd.isna(value):
            return None
        number = float(value)
    except Exception:
        return None
    return number if pd.notna(number) else None


def _text(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)


def _clean_quotes(quotes: pd.DataFrame) -> pd.DataFrame:
    columns = ["code", "trade_date", "open", "high", "low", "close", "amount"]
    if quotes.empty:
        return pd.DataFrame(columns=columns)
    prices = quotes.copy()
    for column in columns:
        if column not in prices.columns:
            prices[column] = pd.NA
    prices["code"] = prices["code"].astype(str).str.zfill(6)
    prices["trade_date"] = pd.to_datetime(prices["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    for column in ["open", "high", "low", "close", "amount"]:
        prices[column] = pd.to_numeric(prices[column], errors="coerce")
    return prices.dropna(subset=["code", "trade_date", "open", "high", "low", "close"]).sort_values(["code", "trade_date"])


def _macro_score(row: pd.Series) -> float:
    for column in ["combo_score", "coarse_score", "macro_score"]:
        value = _num(row.get(column))
        if value is not None:
            return value * 100 if column == "coarse_score" and value <= 1 else value
    return 0.0


def _is_candidate(row: pd.Series, macro_threshold: float | None = None, tech_threshold: float | None = None) -> bool:
    macro = _macro_score(row)
    technical = _num(row.get("technical_score")) or 0.0
    usable = bool(row.get("usable_for_plan", False))
    strategy = _text(row.get("primary_strategy"))
    mt = macro_threshold if macro_threshold is not None else MACRO_POTENTIAL_THRESHOLD
    tt = tech_threshold if tech_threshold is not None else TECHNICAL_TIMING_THRESHOLD
    return macro >= mt and technical >= tt and usable and strategy in EXECUTABLE_STRATEGIES


def _empty_row(row: pd.Series, signal_date: str, status: str, reason: str) -> dict:
    return {
        "code": str(row.get("code", "")).zfill(6),
        "name": row.get("name", ""),
        "signal_date": signal_date,
        "action": row.get("action", ""),
        "primary_strategy": row.get("primary_strategy", ""),
        "macro_score": _macro_score(row),
        "technical_score": _num(row.get("technical_score")),
        "planned_entry": _num(row.get("planned_entry")),
        "initial_stop": _num(row.get("initial_stop")),
        "profit_target_price": None,
        "buy_date": None,
        "buy_price": None,
        "sell_date": None,
        "sell_price": None,
        "exit_reason": "",
        "return_pct": None,
        "holding_days": 0,
        "status": status,
        "data_status": status,
        "path": [],
        "note": reason,
    }


def _buy_triggered(strategy: str, row: pd.Series, entry: float, quote: pd.Series) -> bool:
    high = _num(quote.get("high"))
    low = _num(quote.get("low"))
    amount = _num(quote.get("amount"))
    if high is None or low is None:
        return False
    if strategy == "breakout_buy":
        return high >= entry
    if strategy == "pullback_ma_buy":
        return low <= entry <= high
    if strategy == "volume_confirm_buy":
        threshold = _num(row.get("volume_confirm_amount"))
        return high >= entry and (threshold is None or (amount is not None and amount >= threshold))
    return False


def _simulate_one(row: pd.Series, quotes: pd.DataFrame, signal_date: str, profit_target_pct: float) -> dict:
    code = str(row.get("code", "")).zfill(6)
    entry = _num(row.get("planned_entry"))
    stop = _num(row.get("initial_stop"))
    strategy = _text(row.get("primary_strategy"))
    if entry is None or entry <= 0:
        return _empty_row(row, signal_date, "invalid_plan", "缺少有效计划入场价。")
    if stop is None or stop <= 0:
        return _empty_row(row, signal_date, "invalid_plan", "缺少有效初始止损价。")
    group = quotes[(quotes["code"] == code) & (quotes["trade_date"] > signal_date)].copy()
    if group.empty:
        return _empty_row(row, signal_date, "missing_future_quotes", "缺少信号日后的日线行情。")

    buy_date = None
    buy_price = None
    target = entry * (1 + profit_target_pct)
    path = []
    for _, quote in group.iterrows():
        item = {
            "trade_date": quote["trade_date"],
            "open": float(quote["open"]),
            "high": float(quote["high"]),
            "low": float(quote["low"]),
            "close": float(quote["close"]),
        }
        if buy_date is None:
            if not _buy_triggered(strategy, row, entry, quote):
                continue
            buy_date = quote["trade_date"]
            buy_price = entry
            item["event"] = "buy"
            path.append(item)
            continue
        else:
            path.append(item)

        low = float(quote["low"])
        high = float(quote["high"])
        if low <= stop:
            return _trade_row(row, signal_date, buy_date, buy_price, quote["trade_date"], stop, "stop_loss", stop / buy_price - 1, path, target)
        if high >= target:
            return _trade_row(row, signal_date, buy_date, buy_price, quote["trade_date"], target, "take_profit", profit_target_pct, path, target)

    if buy_date is None:
        return _empty_row(row, signal_date, "not_triggered", "信号日至截止日未触发操作建议入场条件。")
    last = group.iloc[-1]
    close = float(last["close"])
    return _trade_row(row, signal_date, buy_date, buy_price, last["trade_date"], close, "hold_to_end", close / buy_price - 1, path, target)


def _trade_row(
    row: pd.Series,
    signal_date: str,
    buy_date: str,
    buy_price: float,
    sell_date: str,
    sell_price: float,
    status: str,
    return_pct: float,
    path: list[dict],
    target: float,
) -> dict:
    return {
        "code": str(row.get("code", "")).zfill(6),
        "name": row.get("name", ""),
        "signal_date": signal_date,
        "action": row.get("action", ""),
        "primary_strategy": row.get("primary_strategy", ""),
        "macro_score": _macro_score(row),
        "technical_score": _num(row.get("technical_score")),
        "planned_entry": _num(row.get("planned_entry")),
        "initial_stop": _num(row.get("initial_stop")),
        "profit_target_price": target,
        "buy_date": buy_date,
        "buy_price": buy_price,
        "sell_date": sell_date,
        "sell_price": sell_price,
        "exit_reason": status,
        "return_pct": return_pct,
        "holding_days": len(path),
        "status": status,
        "data_status": "complete",
        "path": path,
        "note": "按操作建议触发买入后，遵循A股T+1，从下一交易日起以止盈、初始止损或截止日收盘退出。",
    }


def _avg(values: Iterable[float]) -> float | None:
    items = [float(value) for value in values if value is not None and pd.notna(value)]
    return sum(items) / len(items) if items else None


def _summary(rows: list[dict], signal_date: str, profit_target_pct: float, candidate_count: int) -> dict:
    trade_rows = [row for row in rows if row.get("buy_date")]
    realized = [row for row in trade_rows if row.get("status") in {"take_profit", "stop_loss"}]
    returns = [row.get("return_pct") for row in trade_rows]
    realized_returns = [row.get("return_pct") for row in realized]
    return {
        "signal_date": signal_date,
        "profit_target_pct": profit_target_pct,
        "candidate_count": candidate_count,
        "row_count": len(rows),
        "trade_count": len(trade_rows),
        "untriggered_count": sum(1 for row in rows if row.get("status") == "not_triggered"),
        "take_profit_count": sum(1 for row in rows if row.get("status") == "take_profit"),
        "stop_loss_count": sum(1 for row in rows if row.get("status") == "stop_loss"),
        "hold_count": sum(1 for row in rows if row.get("status") == "hold_to_end"),
        "win_rate": _avg([1.0 if (row.get("return_pct") or 0) > 0 else 0.0 for row in trade_rows]),
        "realized_avg_return_pct": _avg(realized_returns),
        "total_avg_return_pct": _avg(returns),
        "max_return_pct": max(returns) if returns else None,
        "min_return_pct": min(returns) if returns else None,
    }


def build_operation_backtest_model(
    plans: pd.DataFrame,
    quotes: pd.DataFrame,
    signal_date: str,
    profit_target_pct: float = DEFAULT_PROFIT_TARGET_PCT,
    macro_threshold: float | None = None,
    tech_threshold: float | None = None,
) -> dict:
    """Simulate operation-plan triggers for high-potential good-timing stocks."""

    if plans.empty:
        return {
            "summary": _summary([], signal_date, profit_target_pct, 0),
            "rows": [],
        }
    frame = plans.copy()
    if "code" in frame.columns:
        frame["code"] = frame["code"].astype(str).str.zfill(6)
    candidates = frame[
        frame.apply(
            lambda row: _is_candidate(row, macro_threshold=macro_threshold, tech_threshold=tech_threshold),
            axis=1,
        )
    ].copy()
    prices = _clean_quotes(quotes)
    rows = [_simulate_one(row, prices, signal_date, profit_target_pct) for _, row in candidates.iterrows()]
    return {
        "summary": _summary(rows, signal_date, profit_target_pct, len(candidates)),
        "rows": rows,
    }


def plans_from_dashboard_model(model: dict) -> pd.DataFrame:
    """Extract dashboard operation-plan rows for operation backtests."""

    stages = {stage.get("key"): stage for stage in model.get("stages", [])}
    plan = pd.DataFrame((stages.get("plan") or {}).get("rows", []))
    if plan.empty:
        return pd.DataFrame()
    if "code" in plan.columns:
        plan["code"] = plan["code"].astype(str).str.zfill(6)
    return plan


def run_operation_backtest(args) -> dict:
    """Run the dashboard signal snapshot and simulate operation-plan execution."""

    signal_date = str(getattr(args, "backtest_date", "") or getattr(args, "as_of_date", "") or "").strip()
    if not signal_date:
        raise RuntimeError("operation-backtest requires --as-of-date or --backtest-date so the signal date is explicit.")
    from backtest.repository import load_forward_quotes
    from dashboard.pipeline import run_dashboard

    dashboard_args = SimpleNamespace(**vars(args))
    if not str(getattr(dashboard_args, "as_of_date", "") or "").strip():
        dashboard_args.as_of_date = signal_date
    dashboard_args.backtest_date = signal_date
    dashboard_args._skip_backtest = True
    dashboard_args._skip_signal_validation = True
    dashboard_args._skip_operation_backtest = True
    dashboard_model = run_dashboard(dashboard_args)
    plans = plans_from_dashboard_model(dashboard_model)
    codes = plans["code"].astype(str).str.zfill(6).dropna().unique().tolist() if "code" in plans.columns else []
    quotes = load_forward_quotes(codes, after_date=signal_date)
    model = build_operation_backtest_model(
        plans,
        quotes,
        signal_date=signal_date,
        profit_target_pct=float(getattr(args, "operation_profit_target", DEFAULT_PROFIT_TARGET_PCT) or DEFAULT_PROFIT_TARGET_PCT),
    )
    model["summary"]["dashboard_health"] = (dashboard_model.get("summary") or {}).get("health", {})
    model["summary"]["universe"] = (dashboard_model.get("summary") or {}).get("universe", "")
    model["summary"]["universe_index_symbol"] = (dashboard_model.get("summary") or {}).get("universe_index_symbol", "")
    return model
