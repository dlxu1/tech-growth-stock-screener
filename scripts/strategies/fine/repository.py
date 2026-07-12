"""Cache-facing data assembly for technical fine screening."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from infra.cache import read_quotes_daily
from strategies.coarse.registry import run as run_coarse


def load_quotes(codes: list[str], as_of_date: str | None = None) -> pd.DataFrame:
    return read_quotes_daily(codes, as_of_date=as_of_date)


def coarse_candidates(args) -> tuple[pd.DataFrame, dict]:
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
