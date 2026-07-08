"""Cache-facing data assembly for next-session plans."""

from __future__ import annotations

import pandas as pd

from infra.cache import read_quotes_daily


def load_quotes(codes: list[str]) -> pd.DataFrame:
    return read_quotes_daily(codes)

