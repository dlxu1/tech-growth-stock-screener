"""Industry-neutral ranking helpers for coarse scoring.

Converts global percentile-rank calculations to within-industry ranks
so that low-volatility sectors (finance, consumer staples) do not
systematically dominate quality and risk-control scores.
"""

from __future__ import annotations

import pandas as pd


def _rank_high_within_group(series: pd.Series, groups: pd.Series) -> pd.Series:
    """Percentile rank within each group, higher = better. Falls back to global rank."""
    clean = pd.to_numeric(series, errors="coerce")
    result = pd.Series(0.5, index=series.index)
    if clean.notna().sum() == 0:
        return result
    for group_name, mask in groups.groupby(groups).groups.items():
        subset = clean.loc[mask]
        if subset.notna().sum() == 0:
            result.loc[mask] = 0.5
        else:
            result.loc[mask] = subset.rank(pct=True, ascending=True).fillna(0.5)
    return result


def _rank_low_within_group(series: pd.Series, groups: pd.Series) -> pd.Series:
    """Percentile rank within each group, lower = better. Falls back to global rank."""
    clean = pd.to_numeric(series, errors="coerce")
    result = pd.Series(0.5, index=series.index)
    if clean.notna().sum() == 0:
        return result
    for group_name, mask in groups.groupby(groups).groups.items():
        subset = clean.loc[mask]
        if subset.notna().sum() == 0:
            result.loc[mask] = 0.5
        else:
            result.loc[mask] = subset.rank(pct=True, ascending=False).fillna(0.5)
    return result


def safe_group_column(df: pd.DataFrame) -> pd.Series:
    """Return a group column for industry neutralization.

    Uses 'board_name' if available; falls back to a single global group.
    Groups with fewer than 5 members are merged into '其他'.
    """
    if "board_name" not in df.columns or df.empty:
        return pd.Series("global", index=df.index)
    groups = df["board_name"].fillna("未知").astype(str)
    counts = groups.value_counts()
    small = counts[counts < 5].index.tolist()
    if small:
        groups = groups.map(lambda g: "其他" if g in small else g)
    return groups
