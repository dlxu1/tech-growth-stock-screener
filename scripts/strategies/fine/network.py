"""Realtime fetch hooks for fine screening."""

from __future__ import annotations

from data.sources import sync_daily_prices


def refresh_daily_prices(codes: list[str], start: str, end: str, args) -> dict:
    return sync_daily_prices(codes, start, end, args.refresh, args.no_proxy, args.source, getattr(args, "adjust", "qfq"))

