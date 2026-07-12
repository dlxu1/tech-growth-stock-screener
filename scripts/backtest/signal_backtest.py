"""Single-date signal backtests for dashboard scores."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from typing import Iterable

import pandas as pd

from backtest.repository import load_forward_quotes


STRATEGY_CONFIGS = {
    "macro": {"title": "宏观潜力 Top10", "score_column": "combo_score"},
    "technical": {"title": "技术分 Top10", "score_column": "technical_score"},
    "attention": {"title": "综合关注 Top10", "score_column": "attention_score"},
}
MACRO_POTENTIAL_THRESHOLD = 80.0
TECHNICAL_TIMING_THRESHOLD = 75.0


def parse_holding_days(value: str | None) -> list[int]:
    if not value:
        return [7, 14, 21]
    days = []
    for item in str(value).split(","):
        text = item.strip()
        if not text:
            continue
        days.append(int(text))
    return days or [7, 14, 21]


def candidates_from_dashboard_model(model: dict) -> pd.DataFrame:
    """Merge dashboard combo and fine rows into signal-backtest candidates."""

    stages = {stage.get("key"): stage for stage in model.get("stages", [])}
    combo = pd.DataFrame((stages.get("combo") or {}).get("rows", []))
    fine = pd.DataFrame((stages.get("fine") or {}).get("rows", []))
    if combo.empty and fine.empty:
        return pd.DataFrame(columns=["code", "name", "combo_score", "technical_score", "attention_score"])
    if combo.empty:
        merged = fine.copy()
    elif fine.empty:
        merged = combo.copy()
    else:
        combo_cols = [col for col in ["code", "name", "board_name", "combo_score", "coarse_score"] if col in combo.columns]
        fine_cols = [col for col in ["code", "name", "board_name", "technical_score", "latest_trade_date", "close"] if col in fine.columns]
        merged = combo[combo_cols].merge(fine[fine_cols], on="code", how="outer", suffixes=("", "_fine"))
        for col in ["name", "board_name"]:
            fine_col = f"{col}_fine"
            if fine_col in merged.columns:
                if col in merged.columns:
                    merged[col] = merged[col].combine_first(merged[fine_col])
                    merged = merged.drop(columns=[fine_col])
                else:
                    merged = merged.rename(columns={fine_col: col})
    if "code" in merged.columns:
        merged["code"] = merged["code"].astype(str).str.zfill(6)
    return _with_attention_score(merged)


def _score_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce")
    return pd.Series(float("nan"), index=df.index)


def _with_attention_score(candidates: pd.DataFrame) -> pd.DataFrame:
    scored = candidates.copy()
    macro = _score_series(scored, "combo_score").fillna(_score_series(scored, "coarse_score")).fillna(0)
    technical = _score_series(scored, "technical_score").fillna(0)
    scored["attention_score"] = macro * 0.65 + technical * 0.35
    return scored


def _matrix_label(macro_score: float, technical_score: float) -> str:
    macro_high = macro_score >= MACRO_POTENTIAL_THRESHOLD
    technical_high = technical_score >= TECHNICAL_TIMING_THRESHOLD
    if macro_high and technical_high:
        return "好时机+高潜力"
    if macro_high:
        return "高潜力+等时机"
    if technical_high:
        return "好时机+待复核"
    return "其他象限"


def _with_matrix_classification(candidates: pd.DataFrame) -> pd.DataFrame:
    scored = candidates.copy()
    macro = _score_series(scored, "combo_score").fillna(_score_series(scored, "coarse_score")).fillna(0)
    macro = macro.where(macro > 1, macro * 100)
    technical = _score_series(scored, "technical_score").fillna(0)
    scored["macro_score"] = macro
    scored["technical_score"] = technical
    scored["matrix_label"] = [
        _matrix_label(float(macro_value), float(technical_value))
        for macro_value, technical_value in zip(macro, technical, strict=False)
    ]
    scored["is_high_potential_good_timing"] = scored["matrix_label"] == "好时机+高潜力"
    return scored


def select_signal_candidates(candidates: pd.DataFrame, top: int = 10) -> dict[str, pd.DataFrame]:
    """Select top candidates for macro, technical, and attention score backtests."""

    if candidates.empty:
        return {key: pd.DataFrame() for key in STRATEGY_CONFIGS}
    scored = _with_matrix_classification(_with_attention_score(candidates))
    selections: dict[str, pd.DataFrame] = {}
    for key, config in STRATEGY_CONFIGS.items():
        score_column = config["score_column"]
        frame = scored.copy()
        frame["score"] = _score_series(frame, score_column)
        frame = frame.dropna(subset=["score"])
        sort_columns = ["score", "code"]
        selected = frame.sort_values(sort_columns, ascending=[False, True]).head(top).copy()
        selected["strategy"] = key
        selections[key] = selected
    return selections


def _empty_return_row(row: pd.Series, signal_date: str, holding_days: int, status: str) -> dict:
    return {
        "strategy": row.get("strategy", ""),
        "code": str(row.get("code", "")).zfill(6),
        "name": row.get("name", ""),
        "score": row.get("score"),
        "signal_date": signal_date,
        "buy_date": None,
        "buy_price": None,
        "sell_date": None,
        "sell_price": None,
        "holding_days": holding_days,
        "return_pct": None,
        "macro_score": row.get("macro_score"),
        "technical_score": row.get("technical_score"),
        "matrix_label": row.get("matrix_label", ""),
        "is_high_potential_good_timing": bool(row.get("is_high_potential_good_timing", False)),
        "price_points": [],
        "data_status": status,
    }


def compute_forward_returns(
    selections: pd.DataFrame,
    quotes: pd.DataFrame,
    signal_date: str,
    holding_days: Iterable[int],
) -> pd.DataFrame:
    """Compute next-open to horizon-close returns for selected stocks."""

    rows = []
    horizons = [int(value) for value in holding_days]
    if selections.empty:
        return pd.DataFrame(
            columns=[
                "strategy",
                "code",
                "name",
                "score",
                "signal_date",
                "buy_date",
                "buy_price",
                "sell_date",
                "sell_price",
                "holding_days",
                "return_pct",
                "macro_score",
                "technical_score",
                "matrix_label",
                "is_high_potential_good_timing",
                "price_points",
                "data_status",
            ]
        )
    prices = quotes.copy()
    if not prices.empty:
        prices["code"] = prices["code"].astype(str).str.zfill(6)
        prices["trade_date"] = pd.to_datetime(prices["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        for column in ["open", "close"]:
            prices[column] = pd.to_numeric(prices[column], errors="coerce")
        prices = prices.dropna(subset=["trade_date", "open", "close"]).sort_values(["code", "trade_date"])

    for _, row in selections.iterrows():
        code = str(row.get("code", "")).zfill(6)
        group = prices[(prices["code"] == code) & (prices["trade_date"] > signal_date)].copy() if not prices.empty else pd.DataFrame()
        for horizon in horizons:
            if group.empty:
                rows.append(_empty_return_row(row, signal_date, horizon, "missing_future_quotes"))
                continue
            if len(group) < horizon:
                rows.append(_empty_return_row(row, signal_date, horizon, "insufficient_future_quotes"))
                continue
            buy = group.iloc[0]
            sell = group.iloc[horizon - 1]
            buy_price = float(buy["open"])
            sell_price = float(sell["close"])
            return_pct = sell_price / buy_price - 1 if buy_price else None
            price_points = [
                {
                    "trade_date": item["trade_date"],
                    "open": float(item["open"]),
                    "close": float(item["close"]),
                }
                for _, item in group.iloc[:horizon].iterrows()
            ]
            rows.append(
                {
                    "strategy": row.get("strategy", ""),
                    "code": code,
                    "name": row.get("name", ""),
                    "score": row.get("score"),
                    "signal_date": signal_date,
                    "buy_date": buy["trade_date"],
                    "buy_price": buy_price,
                    "sell_date": sell["trade_date"],
                    "sell_price": sell_price,
                    "holding_days": horizon,
                    "return_pct": return_pct,
                    "macro_score": row.get("macro_score"),
                    "technical_score": row.get("technical_score"),
                    "matrix_label": row.get("matrix_label", ""),
                    "is_high_potential_good_timing": bool(row.get("is_high_potential_good_timing", False)),
                    "price_points": price_points,
                    "data_status": "complete",
                }
            )
    return pd.DataFrame(rows)


def _horizon_summary(rows: pd.DataFrame) -> dict[int, dict]:
    summaries: dict[int, dict] = {}
    if rows.empty:
        return summaries
    for horizon, group in rows.groupby("holding_days"):
        returns = pd.to_numeric(group["return_pct"], errors="coerce").dropna()
        summaries[int(horizon)] = {
            "holding_days": int(horizon),
            "rows": int(len(group)),
            "complete_count": int(len(returns)),
            "avg_return_pct": float(returns.mean()) if not returns.empty else None,
            "median_return_pct": float(returns.median()) if not returns.empty else None,
            "win_rate": float((returns > 0).mean()) if not returns.empty else None,
            "max_return_pct": float(returns.max()) if not returns.empty else None,
            "min_return_pct": float(returns.min()) if not returns.empty else None,
        }
    return summaries


def _summary_by_group(rows: pd.DataFrame, group_column: str) -> dict[str, dict[int, dict]]:
    if rows.empty or group_column not in rows.columns:
        return {}
    grouped: dict[str, dict[int, dict]] = {}
    for label, group in rows.groupby(group_column, sort=False):
        grouped[str(label)] = _horizon_summary(group)
    return grouped


def _with_attention_buckets(candidates: pd.DataFrame, bucket_size: int) -> pd.DataFrame:
    bucketed = candidates.sort_values(["attention_score", "code"], ascending=[False, True]).copy()
    size = max(int(bucket_size), 1)
    labels = []
    for index in range(len(bucketed)):
        start = index // size * size + 1
        end = min(start + size - 1, len(bucketed))
        labels.append(f"Top {start}-{end}")
    bucketed["attention_bucket"] = labels
    return bucketed


def build_signal_validation_model(
    candidates: pd.DataFrame,
    quotes: pd.DataFrame,
    signal_date: str,
    holding_days: Iterable[int] = (7, 14, 21),
    bucket_size: int = 10,
) -> dict:
    """Validate all dashboard candidates by matrix quadrant and attention-score buckets."""

    if candidates.empty:
        return {
            "summary": {
                "signal_dates": [signal_date],
                "candidate_count": 0,
                "holding_days": [int(value) for value in holding_days],
                "bucket_size": int(bucket_size),
                "buy_rule": "next_trade_open",
                "sell_rule": "nth_trade_close",
            },
            "quadrants": {},
            "attention_buckets": {},
            "rows": [],
        }
    scored = _with_attention_buckets(_with_matrix_classification(_with_attention_score(candidates)), bucket_size)
    scored["strategy"] = "validation"
    scored["score"] = _score_series(scored, "attention_score")
    returns = compute_forward_returns(scored, quotes, signal_date=signal_date, holding_days=holding_days)
    bucket_lookup = scored.set_index("code")["attention_bucket"].to_dict()
    if not returns.empty:
        returns["attention_bucket"] = returns["code"].map(bucket_lookup).fillna("未分桶")
    clean_returns = returns.astype(object).where(pd.notna(returns), None)
    return {
        "summary": {
            "signal_dates": [signal_date],
            "candidate_count": int(len(scored)),
            "holding_days": [int(value) for value in holding_days],
            "bucket_size": int(bucket_size),
            "buy_rule": "next_trade_open",
            "sell_rule": "nth_trade_close",
        },
        "quadrants": _summary_by_group(returns, "matrix_label"),
        "attention_buckets": _summary_by_group(returns, "attention_bucket"),
        "rows": clean_returns.to_dict(orient="records"),
    }


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def validation_signal_dates(args) -> list[str]:
    """Resolve signal dates for validation runs."""

    start = str(getattr(args, "validation_start", "") or "").strip()
    end = str(getattr(args, "validation_end", "") or "").strip()
    if start or end:
        if not start or not end:
            raise RuntimeError("signal-validate requires both --validation-start and --validation-end when using a date range.")
        step_days = max(int(getattr(args, "validation_step_days", 20) or 20), 1)
        current = _parse_date(start)
        final = _parse_date(end)
        if current > final:
            raise RuntimeError("--validation-start must be earlier than or equal to --validation-end.")
        dates = []
        while current <= final:
            dates.append(current.isoformat())
            current += timedelta(days=step_days)
        return dates
    signal_date = str(getattr(args, "backtest_date", "") or getattr(args, "as_of_date", "") or "").strip()
    if not signal_date:
        raise RuntimeError("signal-validate requires --backtest-date, --as-of-date, or --validation-start/--validation-end.")
    return [signal_date]


def aggregate_validation_models(models: list[dict], bucket_size: int, holding_days: Iterable[int]) -> dict:
    """Aggregate validation rows from multiple signal-date models."""

    frames = []
    signal_dates = []
    candidate_count = 0
    for model in models:
        summary = model.get("summary") or {}
        signal_dates.extend(str(item) for item in summary.get("signal_dates", []) if item)
        candidate_count += int(summary.get("candidate_count") or 0)
        rows = model.get("rows") or []
        if rows:
            frames.append(pd.DataFrame(rows))
    returns = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return {
        "summary": {
            "signal_dates": signal_dates,
            "signal_date_count": len(signal_dates),
            "candidate_count": candidate_count,
            "holding_days": [int(value) for value in holding_days],
            "bucket_size": int(bucket_size),
            "buy_rule": "next_trade_open",
            "sell_rule": "nth_trade_close",
        },
        "quadrants": _summary_by_group(returns, "matrix_label"),
        "attention_buckets": _summary_by_group(returns, "attention_bucket"),
        "rows": returns.astype(object).where(pd.notna(returns), None).to_dict(orient="records") if not returns.empty else [],
        "per_date": models,
    }


def build_signal_backtest_model(
    candidates: pd.DataFrame,
    quotes: pd.DataFrame,
    signal_date: str,
    top: int = 10,
    holding_days: Iterable[int] = (7, 14, 21),
) -> dict:
    """Build a serializable signal-backtest model for all three score selectors."""

    selections = select_signal_candidates(candidates, top=top)
    strategies = []
    for key, selected in selections.items():
        returns = compute_forward_returns(selected, quotes, signal_date=signal_date, holding_days=holding_days)
        clean_returns = returns.astype(object).where(pd.notna(returns), None)
        strategies.append(
            {
                "key": key,
                "title": STRATEGY_CONFIGS[key]["title"],
                "score_column": STRATEGY_CONFIGS[key]["score_column"],
                "selected_count": int(len(selected)),
                "horizons": _horizon_summary(returns),
                "rows": clean_returns.to_dict(orient="records"),
            }
        )
    return {
        "summary": {
            "signal_date": signal_date,
            "top": int(top),
            "holding_days": [int(value) for value in holding_days],
            "buy_rule": "next_trade_open",
            "sell_rule": "nth_trade_close",
        },
        "strategies": strategies,
    }


def run_signal_backtest(args) -> dict:
    """Run the dashboard signal snapshot and compute forward returns."""

    signal_date = str(getattr(args, "backtest_date", "") or getattr(args, "as_of_date", "") or "").strip()
    if not signal_date:
        raise RuntimeError("signal-backtest requires --as-of-date or --backtest-date so the signal date is explicit.")
    from dashboard.pipeline import run_dashboard

    dashboard_args = SimpleNamespace(**vars(args))
    if not str(getattr(dashboard_args, "as_of_date", "") or "").strip():
        dashboard_args.as_of_date = signal_date
    dashboard_args.backtest_date = signal_date
    dashboard_model = run_dashboard(dashboard_args)
    model = dashboard_model.get("backtest")
    if not model:
        candidates = candidates_from_dashboard_model(dashboard_model)
        codes = candidates["code"].astype(str).str.zfill(6).dropna().unique().tolist() if "code" in candidates.columns else []
        quotes = load_forward_quotes(codes, after_date=signal_date)
        model = build_signal_backtest_model(
            candidates,
            quotes,
            signal_date=signal_date,
            top=int(getattr(args, "backtest_top", 10) or 10),
            holding_days=parse_holding_days(getattr(args, "holding_days", "")),
        )
    model["summary"]["dashboard_health"] = (dashboard_model.get("summary") or {}).get("health", {})
    model["summary"]["universe"] = (dashboard_model.get("summary") or {}).get("universe", "")
    model["summary"]["universe_index_symbol"] = (dashboard_model.get("summary") or {}).get("universe_index_symbol", "")
    return model


def run_signal_validation(args) -> dict:
    """Run dashboard signal validation across one or more historical signal dates."""

    from dashboard.pipeline import run_dashboard

    signal_dates = validation_signal_dates(args)
    holding_days = parse_holding_days(getattr(args, "holding_days", ""))
    bucket_size = int(getattr(args, "bucket_size", 10) or 10)
    models = []
    for signal_date in signal_dates:
        dashboard_args = SimpleNamespace(**vars(args))
        dashboard_args.as_of_date = signal_date
        dashboard_args.backtest_date = signal_date
        dashboard_model = run_dashboard(dashboard_args)
        candidates = candidates_from_dashboard_model(dashboard_model)
        codes = candidates["code"].astype(str).str.zfill(6).dropna().unique().tolist() if "code" in candidates.columns else []
        quotes = load_forward_quotes(codes, after_date=signal_date)
        model = build_signal_validation_model(
            candidates,
            quotes,
            signal_date=signal_date,
            holding_days=holding_days,
            bucket_size=bucket_size,
        )
        model["summary"]["dashboard_health"] = (dashboard_model.get("summary") or {}).get("health", {})
        model["summary"]["universe"] = (dashboard_model.get("summary") or {}).get("universe", "")
        model["summary"]["universe_index_symbol"] = (dashboard_model.get("summary") or {}).get("universe_index_symbol", "")
        models.append(model)
    aggregate = aggregate_validation_models(models, bucket_size=bucket_size, holding_days=holding_days)
    aggregate["summary"]["universe"] = getattr(args, "universe", "")
    aggregate["summary"]["universe_index_symbol"] = getattr(args, "universe_index_symbol", "")
    return aggregate
