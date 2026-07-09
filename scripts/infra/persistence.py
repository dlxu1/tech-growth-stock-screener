"""Persistence helpers for strategy-layer outputs."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

import pandas as pd

from data.db import connect, write_layer_results


def _args_to_params(args: Any) -> dict:
    try:
        raw = vars(args)
    except TypeError:
        return {}
    out = {}
    for key, value in raw.items():
        if key.startswith("_"):
            continue
        if callable(value):
            continue
        out[key] = value
    return out


def _meta_to_dict(meta: Any) -> dict:
    if meta is None:
        return {}
    if isinstance(meta, dict):
        return dict(meta)
    if is_dataclass(meta):
        return asdict(meta)
    try:
        return dict(meta)
    except Exception:
        return {"value": str(meta)}


def should_persist(args: Any) -> bool:
    if getattr(args, "no_persist_results", False):
        return False
    if getattr(args, "command", "") == "sync":
        return False
    return True


def persist_layer_result(layer: str, args: Any, df: pd.DataFrame, meta: Any) -> int | None:
    if not should_persist(args):
        return None
    meta_dict = _meta_to_dict(meta)
    params = _args_to_params(args)
    conn = connect()
    try:
        run_id = write_layer_results(
            conn,
            layer=layer,
            command=str(getattr(args, "command", "")),
            params=params,
            meta=meta_dict,
            df=df,
        )
    finally:
        conn.close()
    meta_dict[f"{layer}_run_id"] = run_id
    if isinstance(meta, dict):
        meta[f"{layer}_run_id"] = run_id
    elif is_dataclass(meta) and hasattr(meta, "__dict__"):
        setattr(meta, f"{layer}_run_id", run_id)
    return run_id


__all__ = ["persist_layer_result", "should_persist"]
