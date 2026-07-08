"""Shared network policy and fallback helpers."""

from __future__ import annotations

from typing import Callable

import pandas as pd

from common import apply_network_policy, source_chain


def run_fetchers(label: str, fetchers: list[tuple[str, Callable[[], pd.DataFrame]]]) -> tuple[pd.DataFrame, str]:
    errors = []
    for name, fetcher in fetchers:
        try:
            df = fetcher()
            if df is not None and not df.empty:
                return df, name
            errors.append(f"{name}: empty")
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    raise RuntimeError(f"No {label} source available. " + "; ".join(errors[:5]))


__all__ = ["apply_network_policy", "run_fetchers", "source_chain"]

