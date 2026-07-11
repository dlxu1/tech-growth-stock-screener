"""Configurable stock-type classification for dashboard stock pools."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "stock_type_rules.json"


@dataclass(frozen=True)
class StockTypeRule:
    name: str
    keywords: tuple[str, ...]
    exclude_keywords: tuple[str, ...] = ()
    color: str = ""


@dataclass(frozen=True)
class StockTypeRules:
    default_type: str
    rules: tuple[StockTypeRule, ...]
    source_path: str

    @property
    def names(self) -> list[str]:
        names = [rule.name for rule in self.rules]
        if self.default_type not in names:
            names.append(self.default_type)
        return names


def _as_text_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _fallback_rules() -> StockTypeRules:
    return StockTypeRules(
        default_type="未分类",
        source_path="built-in",
        rules=(
            StockTypeRule("科技股", ("半导体", "通信", "软件", "计算机", "消费电子", "光学光电子", "元件", "电子", "自动化设备", "IT服务"), color="#315f9f"),
            StockTypeRule("周期股", ("煤炭", "有色", "钢铁", "化工", "电力", "航运", "石油", "采掘"), color="#a8642a"),
            StockTypeRule("金融股", ("银行", "保险", "证券", "多元金融"), color="#247c6d"),
            StockTypeRule("消费/防御", ("食品", "饮料", "医药", "家电", "农林牧渔", "公用事业"), color="#6b7280"),
        ),
    )


def load_stock_type_rules(config_path: str | None = None) -> StockTypeRules:
    """Load stock-type rules from JSON, falling back to the project default."""

    path = Path(config_path).expanduser() if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        return _fallback_rules()
    data = json.loads(path.read_text(encoding="utf-8"))
    rules = []
    for item in data.get("types", []):
        if not item.get("enabled", True):
            continue
        name = str(item.get("name") or "").strip()
        keywords = _as_text_list(item.get("keywords"))
        if not name or not keywords:
            continue
        rules.append(
            StockTypeRule(
                name=name,
                keywords=keywords,
                exclude_keywords=_as_text_list(item.get("exclude_keywords")),
                color=str(item.get("color") or "").strip(),
            )
        )
    default_type = str(data.get("default_type") or "未分类").strip() or "未分类"
    return StockTypeRules(default_type=default_type, rules=tuple(rules), source_path=str(path))


def parse_stock_types(value: str | None) -> list[str]:
    """Parse comma-separated stock-type names from CLI args."""

    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def classify_stock_type(row: dict, rules: StockTypeRules | None = None) -> tuple[str, str]:
    """Return stock type and traceable note for one stock-pool row."""

    rules = rules or load_stock_type_rules(None)
    board_name = str(row.get("board_name") or "")
    for rule in rules.rules:
        if rule.exclude_keywords and any(keyword in board_name for keyword in rule.exclude_keywords):
            continue
        hit = next((keyword for keyword in rule.keywords if keyword in board_name), "")
        if hit:
            return rule.name, f"股票类型：{rule.name}；命中关键词：{hit}；识别依据：board_name={board_name}"
    return rules.default_type, f"股票类型：{rules.default_type}；识别依据：board_name={board_name or 'N/A'}"


def annotate_stock_types(df: pd.DataFrame, rules: StockTypeRules | None = None) -> pd.DataFrame:
    """Add stock_type and stock_type_note columns to a stock-pool DataFrame."""

    if df.empty:
        return df.copy()
    annotated = df.copy()
    stock_types = []
    notes = []
    for row in annotated.astype(object).where(pd.notna(annotated), None).to_dict(orient="records"):
        stock_type, note = classify_stock_type(row, rules)
        stock_types.append(stock_type)
        notes.append(note)
    annotated["stock_type"] = stock_types
    annotated["stock_type_note"] = notes
    return annotated


def filter_by_stock_types(df: pd.DataFrame, selected_types: list[str]) -> pd.DataFrame:
    """Keep rows whose configured stock type is selected."""

    if df.empty or not selected_types or "stock_type" not in df.columns:
        return df
    selected = set(selected_types)
    return df[df["stock_type"].isin(selected)].copy()
