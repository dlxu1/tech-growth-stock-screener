"""Market state detection for dashboard pipeline risk control.

Three-dimension market regime classifier:
1. Sample position: candidate median close vs MA30
2. Market breadth: % of stocks with close > MA20
3. Trend persistence: median MA20 slope direction

Voting: 3/3 bull → BULL, 2-1 → TRANSITION, 0/3 → BEAR.
Bull mode uses momentum-weighted strategy, bear mode uses quality-defense.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from infra.cache import read_quotes_daily


@dataclass(frozen=True)
class MarketState:
    label: str  # "bull" | "transition" | "bear"
    regime: str  # alias for label
    median_close_vs_ma20: float
    median_ma20_slope: float
    breadth_pct: float  # % of stocks above MA20
    bull_votes: int  # 0-3
    sample_count: int
    position_multiplier: float
    note: str


BULL = "bull"
TRANSITION = "transition"
BEAR = "bear"
NORMAL = BULL  # backward compat
DEFENSIVE = BEAR  # backward compat

DEFAULT_DEFENSIVE_POSITION_MULTIPLIER = 0.60


def detect(codes: list[str], as_of_date: str | None = None) -> MarketState:
    """Three-dimension market regime classifier.

    Returns MarketState with regime (bull/transition/bear) and position_multiplier.
    """
    if not codes:
        return MarketState(label=BULL, regime=BULL, median_close_vs_ma20=float("nan"),
                           median_ma20_slope=float("nan"), breadth_pct=float("nan"),
                           bull_votes=3, sample_count=0, position_multiplier=1.0,
                           note="无候选股，默认牛市模式")

    quotes = read_quotes_daily(codes, as_of_date=as_of_date)
    if quotes.empty or "close" not in quotes.columns or "trade_date" not in quotes.columns:
        return MarketState(label=BULL, regime=BULL, median_close_vs_ma20=float("nan"),
                           median_ma20_slope=float("nan"), breadth_pct=float("nan"),
                           bull_votes=3, sample_count=0, position_multiplier=1.0,
                           note="缺少日线数据，默认牛市模式")

    quotes["trade_date"] = pd.to_datetime(quotes["trade_date"], errors="coerce")
    quotes["close"] = pd.to_numeric(quotes["close"], errors="coerce")
    quotes = quotes.dropna(subset=["code", "trade_date", "close"]).sort_values(["code", "trade_date"])

    ratios = []
    slopes = []
    ma30_ratios = []
    for _code, group in quotes.groupby("code"):
        group = group.sort_values("trade_date")
        close = group["close"]
        if len(close) < 30:
            continue
        ma20 = close.rolling(20, min_periods=20).mean().dropna()
        ma30 = close.rolling(30, min_periods=30).mean().dropna()
        if len(ma20) < 2 or len(ma30) < 1:
            continue
        latest_close = float(close.iloc[-1])
        latest_ma20 = float(ma20.iloc[-1])
        if latest_ma20 and latest_ma20 > 0:
            ratios.append(latest_close / latest_ma20)
        if len(ma20) >= 6:
            slopes.append(float(ma20.iloc[-1] - ma20.iloc[-6]))
        latest_ma30 = float(ma30.iloc[-1])
        if latest_ma30 and latest_ma30 > 0:
            ma30_ratios.append(latest_close / latest_ma30)

    if not ratios or not slopes or not ma30_ratios:
        return MarketState(label=BULL, regime=BULL, median_close_vs_ma20=float("nan"),
                           median_ma20_slope=float("nan"), breadth_pct=float("nan"),
                           bull_votes=3, sample_count=len(ratios), position_multiplier=1.0,
                           note="有效样本不足，默认牛市模式")

    median_ratio = float(pd.Series(ratios).median())
    median_slope = float(pd.Series(slopes).median())
    median_ma30_ratio = float(pd.Series(ma30_ratios).median())
    breadth_pct = sum(1 for r in ratios if r > 1.0) / len(ratios) * 100

    dim1_bull = median_ma30_ratio > 1.0
    dim2_bull = breadth_pct > 60.0
    dim3_bull = median_slope > 0
    bull_votes = sum([dim1_bull, dim2_bull, dim3_bull])

    if bull_votes == 3:
        regime = BULL
        position_multiplier = 1.0
    elif bull_votes == 0:
        regime = BEAR
        position_multiplier = DEFAULT_DEFENSIVE_POSITION_MULTIPLIER
    else:
        regime = TRANSITION
        position_multiplier = DEFAULT_DEFENSIVE_POSITION_MULTIPLIER if bull_votes == 1 else 0.85

    note_parts = []
    note_parts.append(f"样本MA30: {median_ma30_ratio:.3f} {'>1' if dim1_bull else '≤1'}")
    note_parts.append(f"宽度: {breadth_pct:.0f}% {'>60%' if dim2_bull else '≤60%'}")
    note_parts.append(f"趋势: slope={median_slope:.2f} {'>0' if dim3_bull else '≤0'}")
    note_parts.append(f"投票: {bull_votes}/3 → {regime}")

    return MarketState(
        label=regime, regime=regime,
        median_close_vs_ma20=median_ratio,
        median_ma20_slope=median_slope,
        breadth_pct=breadth_pct,
        bull_votes=bull_votes,
        sample_count=len(ratios),
        position_multiplier=position_multiplier,
        note="；".join(note_parts),
    )


def compute_dynamic_thresholds(
    combo_scores: list[float],
    technical_scores: list[float],
    macro_percentile: float = 70.0,
    technical_percentile: float = 65.0,
) -> dict:
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
        note = (f"动态阈值：宏观分{macro_percentile:.0f}分位={macro_threshold}，"
                f"技术分{technical_percentile:.0f}分位={tech_threshold}")
    return {
        "macro_potential_threshold": macro_threshold,
        "technical_timing_threshold": tech_threshold,
        "macro_percentile": macro_percentile,
        "technical_percentile": technical_percentile,
        "combo_sample_count": len(combo),
        "technical_sample_count": len(tech),
        "note": note,
    }
