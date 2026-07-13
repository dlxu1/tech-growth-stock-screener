"""Market state detection for dashboard pipeline risk control.

Determines whether the current market environment is NORMAL (uptrend,
supportive for breakout/pullback strategies) or DEFENSIVE (downtrend or
choppy, where position sizing and momentum weights should be reduced).

Uses the median of all fine-stage candidates' daily price data:
- close vs MA20 position
- MA20 slope over the last 5-6 trading days

Both conditions must be true for NORMAL; otherwise DEFENSIVE.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from infra.cache import read_quotes_daily


@dataclass(frozen=True)
class MarketState:
    label: str  # "normal" | "defensive"
    median_close_vs_ma20: float  # ratio, >1 means above MA20
    median_ma20_slope: float  # positive means upward
    sample_count: int
    position_multiplier: float  # 1.0 for normal, ≤1.0 for defensive
    note: str


NORMAL = "normal"
DEFENSIVE = "defensive"

DEFAULT_DEFENSIVE_POSITION_MULTIPLIER = 0.60


def _safe_float(series: pd.Series) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return float("nan")
    return float(clean.median())


def detect(codes: list[str], as_of_date: str | None = None) -> MarketState:
    """Detect market state from fine-stage candidate daily quotes.

    Args:
        codes: Normalized 6-digit stock codes from the fine stage result.
        as_of_date: Optional cutoff date for historical replay.

    Returns:
        MarketState with label, key metrics, and position_multiplier.
    """
    if not codes:
        return MarketState(
            label=NORMAL,
            median_close_vs_ma20=float("nan"),
            median_ma20_slope=float("nan"),
            sample_count=0,
            position_multiplier=1.0,
            note="无候选股，默认正常模式",
        )

    quotes = read_quotes_daily(codes, as_of_date=as_of_date)
    if quotes.empty:
        return MarketState(
            label=NORMAL,
            median_close_vs_ma20=float("nan"),
            median_ma20_slope=float("nan"),
            sample_count=0,
            position_multiplier=1.0,
            note="缺少日线数据，默认正常模式",
        )

    for col in ["close", "trade_date"]:
        if col not in quotes.columns:
            return MarketState(
                label=NORMAL,
                median_close_vs_ma20=float("nan"),
                median_ma20_slope=float("nan"),
                sample_count=0,
                position_multiplier=1.0,
                note=f"日线数据缺少{col}字段，默认正常模式",
            )

    quotes["trade_date"] = pd.to_datetime(quotes["trade_date"], errors="coerce")
    quotes["close"] = pd.to_numeric(quotes["close"], errors="coerce")
    quotes = quotes.dropna(subset=["code", "trade_date", "close"]).sort_values(["code", "trade_date"])

    ratios = []
    slopes = []
    for _code, group in quotes.groupby("code"):
        group = group.sort_values("trade_date")
        close = group["close"]
        if len(close) < 20:
            continue
        ma20 = close.rolling(20, min_periods=20).mean().dropna()
        if len(ma20) < 2:
            continue
        latest_close = float(close.iloc[-1])
        latest_ma20 = float(ma20.iloc[-1])
        if latest_ma20 and latest_ma20 > 0:
            ratios.append(latest_close / latest_ma20)
        if len(ma20) >= 6:
            slope = float(ma20.iloc[-1] - ma20.iloc[-6])
            slopes.append(slope)

    if not ratios or not slopes:
        return MarketState(
            label=NORMAL,
            median_close_vs_ma20=float("nan"),
            median_ma20_slope=float("nan"),
            sample_count=len(ratios),
            position_multiplier=1.0,
            note="有效样本不足，默认正常模式",
        )

    median_ratio = float(pd.Series(ratios).median())
    median_slope = float(pd.Series(slopes).median())
    is_normal = median_ratio > 1.0 and median_slope > 0
    label = NORMAL if is_normal else DEFENSIVE
    position_multiplier = 1.0 if is_normal else DEFAULT_DEFENSIVE_POSITION_MULTIPLIER

    note_parts = []
    if median_ratio <= 1.0:
        note_parts.append(f"中位收盘/MA20={median_ratio:.3f}≤1，多数股票在均线下方")
    if median_slope <= 0:
        note_parts.append(f"中位MA20斜率={median_slope:.2f}≤0，均线走平或下行")

    return MarketState(
        label=label,
        median_close_vs_ma20=median_ratio,
        median_ma20_slope=median_slope,
        sample_count=len(ratios),
        position_multiplier=position_multiplier,
        note="；".join(note_parts) if note_parts else "中位收盘在MA20上方且MA20上行",
    )


def compute_dynamic_thresholds(
    combo_scores: list[float],
    technical_scores: list[float],
    macro_percentile: float = 70.0,
    technical_percentile: float = 65.0,
) -> dict:
    """Compute adaptive matrix quadrant thresholds from current score distributions.

    Args:
        combo_scores: Macro coarse scores of fine-stage candidates.
        technical_scores: Technical scores of fine-stage candidates.
        macro_percentile: Percentile for the macro potential threshold (default 70).
        technical_percentile: Percentile for the technical timing threshold (default 65).

    Returns:
        Dict with macro_potential_threshold, technical_timing_threshold, and metadata.
    """
    combo = pd.Series([float(v) for v in combo_scores if v is not None and pd.notna(v)])
    tech = pd.Series([float(v) for v in technical_scores if v is not None and pd.notna(v)])

    macro_threshold = 80.0
    tech_threshold = 75.0
    note = "使用默认固定阈值（样本不足）"

    if len(combo) >= 15:
        macro_threshold = round(float(combo.quantile(macro_percentile / 100.0)), 1)
    if len(tech) >= 15:
        tech_threshold = round(float(tech.quantile(technical_percentile / 100.0)), 1)

    if len(combo) >= 15 and len(tech) >= 15:
        note = (
            f"动态阈值：宏观分{macro_percentile:.0f}分位={macro_threshold}，"
            f"技术分{technical_percentile:.0f}分位={tech_threshold}。"
            f"好时机+高潜力约占总样本的{(len(combo[combo >= macro_threshold]) / len(combo) * len(tech[tech >= tech_threshold]) / len(tech) * 100):.0f}%"
        )

    return {
        "macro_potential_threshold": macro_threshold,
        "technical_timing_threshold": tech_threshold,
        "macro_percentile": macro_percentile,
        "technical_percentile": technical_percentile,
        "combo_sample_count": len(combo),
        "technical_sample_count": len(tech),
        "note": note,
    }
