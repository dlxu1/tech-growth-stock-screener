"""Shared helpers for the tech growth stock screener."""

from __future__ import annotations

import math
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


DEFAULT_KEYWORDS = [
    "半导体",
    "电子",
    "元件",
    "光学光电子",
    "消费电子",
    "通信设备",
    "通信服务",
    "软件开发",
    "计算机设备",
    "互联网服务",
    "IT服务",
    "人工智能",
    "自动化设备",
]

PROXY_ENV_KEYS = ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]


@dataclass
class SourceStats:
    report_date: str
    universe_source: str
    quote_source: str
    financial_source: str
    db_path: str
    tech_boards: int
    tech_universe: int
    after_rank_gate: int
    after_growth_gate: int


def skill_root() -> Path:
    return Path(os.environ.get("SKILL", Path(__file__).resolve().parents[1]))


def cache_dir() -> Path:
    path = Path(os.environ.get("TECH_GROWTH_SCREENER_CACHE", skill_root() / ".cache"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    path = Path(os.environ.get("TECH_GROWTH_DB", cache_dir() / "stock_data.sqlite"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _proxy_env_exists() -> bool:
    return any(os.environ.get(key) for key in PROXY_ENV_KEYS)


def _set_proxy_env(proxy: str) -> None:
    if not proxy:
        return
    if "://" not in proxy:
        proxy = f"http://{proxy}"
    os.environ["HTTP_PROXY"] = proxy
    os.environ["HTTPS_PROXY"] = proxy
    os.environ["http_proxy"] = proxy
    os.environ["https_proxy"] = proxy


def _macos_system_proxy() -> str | None:
    try:
        output = subprocess.check_output(["scutil", "--proxy"], text=True, timeout=3)
    except Exception:
        return None
    enabled = re.search(r"HTTPSEnable\s*:\s*1", output) or re.search(r"HTTPEnable\s*:\s*1", output)
    host_match = re.search(r"HTTPSProxy\s*:\s*(\S+)", output) or re.search(r"HTTPProxy\s*:\s*(\S+)", output)
    port_match = re.search(r"HTTPSPort\s*:\s*(\d+)", output) or re.search(r"HTTPPort\s*:\s*(\d+)", output)
    if not enabled or not host_match or not port_match:
        return None
    return f"http://{host_match.group(1)}:{port_match.group(1)}"


def apply_network_policy(no_proxy: bool, proxy: str | None = None) -> None:
    if not no_proxy:
        explicit_proxy = proxy or os.environ.get("TECH_GROWTH_PROXY")
        if explicit_proxy:
            _set_proxy_env(explicit_proxy)
        elif not _proxy_env_exists():
            system_proxy = _macos_system_proxy()
            if system_proxy:
                _set_proxy_env(system_proxy)
        return
    for key in PROXY_ENV_KEYS:
        os.environ.pop(key, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


def source_chain(source: str, names: list[str]) -> list[str]:
    if source == "cache":
        return []
    if source == "auto":
        return names
    return [name for name in names if name == source]


def normalize_code(value) -> str:
    try:
        import pandas as pd

        if pd.isna(value):
            return ""
    except Exception:
        if value is None:
            return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(6) if text.isdigit() and len(text) <= 6 else text


def find_col(columns: Iterable[str], candidates: Iterable[str], contains_all: Iterable[str] | None = None) -> str | None:
    cols = [str(c) for c in columns]
    for wanted in candidates:
        for col in cols:
            if col == wanted:
                return col
    if contains_all:
        parts = list(contains_all)
        for col in cols:
            if all(part in col for part in parts):
                return col
    return None


def to_number(value) -> float:
    try:
        import pandas as pd

        if pd.isna(value):
            return math.nan
    except Exception:
        if value is None:
            return math.nan
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if text in {"", "-", "--", "None", "nan"}:
        return math.nan
    try:
        return float(text)
    except ValueError:
        return math.nan


def report_date_candidates(today: date | None = None) -> list[str]:
    today = today or date.today()
    quarters = ["0331", "0630", "0930", "1231"]
    out: list[str] = []
    for year in range(today.year, today.year - 4, -1):
        for q in reversed(quarters):
            candidate = f"{year}{q}"
            if candidate <= today.strftime("%Y%m%d"):
                out.append(candidate)
    return out
