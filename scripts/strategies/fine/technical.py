"""Technical fine screening built on coarse candidates and quotes_daily."""

from __future__ import annotations

import sqlite3

import pandas as pd

from common import db_path
from infra.persistence import persist_layer_result
from strategies.fine import repository as fine_repository


OUTPUT_COLUMNS = [
    "code",
    "name",
    "board_name",
    "coarse_strategies",
    "coarse_score",
    "latest_trade_date",
    "close",
    "change_pct",
    "return_20d",
    "return_60d",
    "amount_ratio",
    "ma5",
    "ma10",
    "ma20",
    "macd_hist",
    "rsi14",
    "max_drawdown_20d",
    "technical_score",
    "technical_reasons",
    "technical_note",
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


def _pct_change(close: pd.Series, periods: int) -> float:
    clean = pd.to_numeric(close, errors="coerce").dropna()
    if len(clean) < 2:
        return float("nan")
    start_pos = max(0, len(clean) - periods - 1)
    start = clean.iloc[start_pos]
    end = clean.iloc[-1]
    if pd.isna(start) or start == 0:
        return float("nan")
    return float(end / start - 1)


def _max_drawdown(close: pd.Series, window: int) -> float:
    clean = pd.to_numeric(close, errors="coerce").dropna().tail(window)
    if clean.empty:
        return float("nan")
    drawdown = clean / clean.cummax() - 1
    return float(drawdown.min())


def _rsi(close: pd.Series, window: int = 14) -> float:
    clean = pd.to_numeric(close, errors="coerce")
    if clean.notna().sum() < 2:
        return float("nan")
    delta = clean.diff()
    gain = delta.clip(lower=0).rolling(window, min_periods=1).mean()
    loss = (-delta.clip(upper=0)).rolling(window, min_periods=1).mean()
    rs = gain / loss.replace(0, pd.NA)
    rsi = 100 - 100 / (1 + rs)
    if pd.isna(rsi.iloc[-1]) and gain.iloc[-1] > 0 and loss.iloc[-1] == 0:
        return 100.0
    return _last(rsi)


def _macd_hist(close: pd.Series) -> float:
    clean = pd.to_numeric(close, errors="coerce")
    if clean.notna().sum() < 2:
        return float("nan")
    ema12 = clean.ewm(span=12, adjust=False, min_periods=1).mean()
    ema26 = clean.ewm(span=26, adjust=False, min_periods=1).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False, min_periods=1).mean()
    return _last((dif - dea) * 2)


def _atr_pct(group: pd.DataFrame) -> float:
    high = pd.to_numeric(group["high"], errors="coerce")
    low = pd.to_numeric(group["low"], errors="coerce")
    close = pd.to_numeric(group["close"], errors="coerce")
    prev_close = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=1).mean()
    latest_close = _last(close)
    if pd.isna(latest_close) or latest_close == 0:
        return float("nan")
    return float(_last(atr) / latest_close)


def _score_component(condition: bool, value: float) -> float:
    return value if condition else 0.0


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


def _coarse_candidates(args) -> tuple[pd.DataFrame, dict]:
    coarse_args = SimpleNamespace(**vars(args))
    coarse_args.strategy = args.coarse_strategy
    coarse_args.top = args.coarse_top
    coarse, meta = run_coarse(coarse_args)
    if coarse.empty:
        return coarse, meta
    grouped = (
        coarse.groupby("code", as_index=False)
        .agg(
            name=("name", "first"),
            board_name=("board_name", "first"),
            coarse_strategies=("coarse_strategy", lambda values: ",".join(dict.fromkeys(values.astype(str)))),
            coarse_score=("coarse_score", "max"),
        )
    )
    return grouped, meta


def _score_one(candidate: pd.Series, group: pd.DataFrame, min_amount: float) -> dict:
    if group.empty:
        return {
            "code": candidate.code,
            "name": candidate.name,
            "board_name": candidate.board_name,
            "coarse_strategies": candidate.coarse_strategies,
            "coarse_score": _to_float(candidate.coarse_score),
            "technical_score": 0.0,
            "technical_reasons": "缺少日线数据",
            "technical_note": "quotes_daily 无该股票数据，需先同步 daily_prices",
        }

    group = group.sort_values("trade_date").copy()
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        group[col] = pd.to_numeric(group[col], errors="coerce")
    close = group["close"]
    amount = group["amount"]
    latest = group.iloc[-1]
    prior_close = close.dropna().iloc[-2] if close.notna().sum() >= 2 else float("nan")
    latest_close = _to_float(latest["close"])
    change_pct = latest_close / prior_close - 1 if pd.notna(prior_close) and prior_close else float("nan")

    ma5 = _last(close.rolling(5, min_periods=1).mean())
    ma10 = _last(close.rolling(10, min_periods=1).mean())
    ma20 = _last(close.rolling(20, min_periods=1).mean())
    ma20_series = close.rolling(20, min_periods=1).mean()
    ma20_slope_up = len(ma20_series.dropna()) >= 2 and ma20_series.dropna().iloc[-1] > ma20_series.dropna().iloc[max(0, len(ma20_series.dropna()) - 6)]
    return_20d = _pct_change(close, 20)
    return_60d = _pct_change(close, 60)
    macd_hist = _macd_hist(close)
    rsi14 = _rsi(close)
    drawdown_20d = _max_drawdown(close, 20)
    atr_pct = _atr_pct(group)

    amount_ref = amount.shift(1).tail(20).mean()
    if pd.isna(amount_ref) or amount_ref == 0:
        amount_ref = amount.tail(20).mean()
    amount_ratio = _to_float(latest["amount"]) / amount_ref if pd.notna(amount_ref) and amount_ref else float("nan")
    amount_20d = amount.tail(20).mean()

    prev_high20 = group["high"].shift(1).tail(20).max()
    high20 = group["high"].tail(20).max()
    day_range = _to_float(latest["high"]) - _to_float(latest["low"])
    close_position = (latest_close - _to_float(latest["low"])) / day_range if day_range and day_range > 0 else float("nan")

    trend_score = (
        _score_component(pd.notna(ma20) and latest_close > ma20, 0.35)
        + _score_component(pd.notna(ma5) and pd.notna(ma10) and pd.notna(ma20) and ma5 >= ma10 >= ma20, 0.35)
        + _score_component(ma20_slope_up, 0.30)
    )
    momentum_score = (
        _score_component(pd.notna(return_20d) and return_20d > 0, 0.40)
        + _score_component(pd.notna(macd_hist) and macd_hist > 0, 0.35)
        + _score_component(pd.notna(rsi14) and 50 <= rsi14 <= 75, 0.25)
        + _score_component(pd.notna(rsi14) and 45 <= rsi14 < 50, 0.12)
    )
    volume_score = (
        _score_component(pd.notna(amount_ratio) and amount_ratio >= 1.2, 0.55)
        + _score_component(pd.notna(change_pct) and change_pct > 0, 0.35)
        + _score_component(pd.notna(amount_20d) and amount_20d >= min_amount, 0.10)
    )
    breakout_score = (
        _score_component(pd.notna(prev_high20) and latest_close >= prev_high20, 0.55)
        + _score_component(pd.notna(high20) and high20 > 0 and latest_close / high20 >= 0.98, 0.25)
        + _score_component(pd.notna(close_position) and close_position >= 0.65, 0.20)
    )
    risk_score = (
        _score_component(pd.notna(drawdown_20d) and drawdown_20d >= -0.08, 0.60)
        + _score_component(pd.notna(drawdown_20d) and -0.15 <= drawdown_20d < -0.08, 0.35)
        + _score_component(pd.notna(atr_pct) and atr_pct <= 0.06, 0.40)
        + _score_component(pd.notna(atr_pct) and 0.06 < atr_pct <= 0.10, 0.20)
    )
    liquidity_score = _score_component(pd.notna(amount_20d) and amount_20d >= min_amount, 1.0)

    technical_score = (
        trend_score * 30
        + min(momentum_score, 1.0) * 20
        + min(volume_score, 1.0) * 20
        + min(breakout_score, 1.0) * 15
        + min(risk_score, 1.0) * 10
        + liquidity_score * 5
    )

    reasons = []
    if trend_score >= 0.65:
        reasons.append("趋势强")
    if volume_score >= 0.70 and breakout_score >= 0.55:
        reasons.append("放量突破")
    elif volume_score >= 0.55:
        reasons.append("量能改善")
    if risk_score >= 0.80:
        reasons.append("回撤可控")
    if momentum_score >= 0.70:
        reasons.append("动量较好")
    if liquidity_score >= 1.0:
        reasons.append("流动性达标")
    if not reasons:
        reasons.append("技术面一般")
    note = "完整日线指标" if len(group) >= 20 else f"日线样本不足20日，仅有{len(group)}日，已降级计算"

    return {
        "code": candidate.code,
        "name": candidate.name,
        "board_name": candidate.board_name,
        "coarse_strategies": candidate.coarse_strategies,
        "coarse_score": _to_float(candidate.coarse_score),
        "latest_trade_date": latest["trade_date"],
        "close": latest_close,
        "change_pct": change_pct,
        "return_20d": return_20d,
        "return_60d": return_60d,
        "amount_ratio": amount_ratio,
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "macd_hist": macd_hist,
        "rsi14": rsi14,
        "max_drawdown_20d": drawdown_20d,
        "technical_score": technical_score,
        "technical_reasons": "、".join(reasons),
        "technical_note": note,
    }


def _candidates_from_previous_stage(candidates: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty or "code" not in candidates.columns:
        return pd.DataFrame(columns=["code", "name", "board_name", "coarse_strategies", "coarse_score"])
    out = candidates.copy()
    for col in ["name", "board_name"]:
        if col not in out.columns:
            out[col] = ""
    if "coarse_strategies" not in out.columns:
        out["coarse_strategies"] = out["matched_strategies"] if "matched_strategies" in out.columns else ""
    if "coarse_score" not in out.columns:
        out["coarse_score"] = out["combo_score"] if "combo_score" in out.columns else 0.0
    grouped = (
        out.groupby("code", as_index=False)
        .agg(
            name=("name", "first"),
            board_name=("board_name", "first"),
            coarse_strategies=("coarse_strategies", lambda values: ",".join(dict.fromkeys(values.astype(str)))),
            coarse_score=("coarse_score", "max"),
        )
    )
    return grouped


def run(args, candidates: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    if candidates is None:
        coarse, coarse_meta = fine_repository.coarse_candidates(args)
    else:
        coarse = _candidates_from_previous_stage(candidates)
        coarse_meta = {"upstream_stage": "combo", "upstream_candidates": len(candidates)}
    meta = {
        **coarse_meta,
        "strategy": "technical",
        "coarse_strategy": args.coarse_strategy,
        "coarse_top": args.coarse_top,
        "top": args.top,
        "min_amount": args.min_amount,
    }
    if coarse.empty:
        result = pd.DataFrame(columns=OUTPUT_COLUMNS)
        persist_layer_result("fine", args, result, meta)
        return result, meta
    codes = coarse["code"].astype(str).str.zfill(6).tolist()
    quotes = fine_repository.load_quotes(codes, as_of_date=getattr(args, "as_of_date", None))
    rows = []
    for candidate in coarse.itertuples(index=False):
        code = str(candidate.code).zfill(6)
        group = quotes[quotes["code"] == code] if not quotes.empty else pd.DataFrame()
        rows.append(_score_one(candidate, group, args.min_amount))
    result = pd.DataFrame(rows)
    for col in OUTPUT_COLUMNS:
        if col not in result.columns:
            result[col] = pd.NA
    result = result[OUTPUT_COLUMNS].sort_values(["technical_score", "coarse_score"], ascending=[False, False])
    selected = result.head(args.top).copy()
    meta.update({"coarse_candidates": len(coarse), "selected": len(selected), "db_path": str(db_path())})
    persist_layer_result("fine", args, selected, meta)
    return selected, meta
