"""Coarse screening registry.

Coarse strategies narrow the investable universe to five names per strategy.
They should be fast, tolerant of partial data, and explicit about degraded
ranking when optional fields are missing.
"""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Callable

import pandas as pd

from common import db_path, find_col, to_number
from data.sources import load_financial_report, load_spot, normalize_financials
from infra.persistence import persist_layer_result
from strategies.coarse import repository as coarse_repository
from strategies.tech_growth import build_tech_universe


@dataclass(frozen=True)
class CoarseStrategy:
    name: str
    title: str
    description: str
    ranker: Callable[[pd.DataFrame], pd.Series]
    required_metrics: tuple[str, ...]
    positive_filters: tuple[str, ...] = ()


def _rank_high(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce")
    if clean.notna().sum() == 0:
        return pd.Series(0.5, index=series.index)
    return clean.rank(pct=True, ascending=True).fillna(0.5)


def _rank_low(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce")
    if clean.notna().sum() == 0:
        return pd.Series(0.5, index=series.index)
    return clean.rank(pct=True, ascending=False).fillna(0.5)


def _reasonable_pe_score(series: pd.Series) -> pd.Series:
    pe = pd.to_numeric(series, errors="coerce")
    if pe.notna().sum() == 0:
        return pd.Series(0.5, index=series.index)
    valid = pe.where(pe > 0)
    median = valid.median()
    if pd.isna(median) or median <= 0:
        return pd.Series(0.5, index=series.index)
    distance = ((valid - median).abs() / median).clip(upper=2)
    return (1 - distance / 2).fillna(0.5)


def _positive(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0) > 0


def _metric(df: pd.DataFrame, name: str) -> pd.Series:
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce")
    return pd.Series(float("nan"), index=df.index)


def _score_market_cap_low_pe(df: pd.DataFrame) -> pd.Series:
    return _rank_high(_metric(df, "market_cap")) * 0.65 + _rank_low(_metric(df, "pe")) * 0.35


def _score_market_cap_reasonable_pe(df: pd.DataFrame) -> pd.Series:
    return _rank_high(_metric(df, "market_cap")) * 0.65 + _reasonable_pe_score(_metric(df, "pe")) * 0.35


def _score_market_cap_revenue_scale(df: pd.DataFrame) -> pd.Series:
    return _rank_high(_metric(df, "market_cap")) * 0.55 + _rank_high(_metric(df, "revenue")) * 0.45


def _score_market_cap_profit_scale(df: pd.DataFrame) -> pd.Series:
    return _rank_high(_metric(df, "market_cap")) * 0.55 + _rank_high(_metric(df, "profit")) * 0.45


def _score_market_cap_revenue_growth(df: pd.DataFrame) -> pd.Series:
    return _rank_high(_metric(df, "market_cap")) * 0.55 + _rank_high(_metric(df, "revenue_yoy")) * 0.45


def _score_market_cap_profit_growth(df: pd.DataFrame) -> pd.Series:
    return _rank_high(_metric(df, "market_cap")) * 0.55 + _rank_high(_metric(df, "profit_yoy")) * 0.45


def _score_market_cap_revenue_profit_growth(df: pd.DataFrame) -> pd.Series:
    return (
        _rank_high(_metric(df, "market_cap")) * 0.45
        + _rank_high(_metric(df, "revenue_yoy")) * 0.25
        + _rank_high(_metric(df, "profit_yoy")) * 0.30
    )


def _score_low_pe_positive_growth(df: pd.DataFrame) -> pd.Series:
    growth = _rank_high(_metric(df, "revenue_yoy").clip(lower=0) + _metric(df, "profit_yoy").clip(lower=0))
    return _rank_low(_metric(df, "pe")) * 0.55 + growth * 0.45


def _score_low_pb_positive_profit(df: pd.DataFrame) -> pd.Series:
    return _rank_low(_metric(df, "pb")) * 0.55 + _rank_high(_metric(df, "profit")) * 0.45


def _score_high_roe_reasonable_pe(df: pd.DataFrame) -> pd.Series:
    return _rank_high(_metric(df, "roe")) * 0.6 + _reasonable_pe_score(_metric(df, "pe")) * 0.4


def _score_high_gross_margin_revenue_growth(df: pd.DataFrame) -> pd.Series:
    return _rank_high(_metric(df, "gross_margin")) * 0.55 + _rank_high(_metric(df, "revenue_yoy")) * 0.45


def _score_high_rd_intensity_revenue_growth(df: pd.DataFrame) -> pd.Series:
    return _rank_high(_metric(df, "rd_intensity")) * 0.55 + _rank_high(_metric(df, "revenue_yoy")) * 0.45


def _score_active_amount_solid_fundamentals(df: pd.DataFrame) -> pd.Series:
    fundamentals = _rank_high(_metric(df, "revenue_yoy").clip(lower=0) + _metric(df, "profit_yoy").clip(lower=0))
    return _rank_high(_metric(df, "amount_20d")) * 0.55 + fundamentals * 0.45


def _score_price_strength_market_cap(df: pd.DataFrame) -> pd.Series:
    return _rank_high(_metric(df, "return_60d")) * 0.55 + _rank_high(_metric(df, "market_cap")) * 0.45


def _score_low_drawdown_positive_growth(df: pd.DataFrame) -> pd.Series:
    growth = _rank_high(_metric(df, "revenue_yoy").clip(lower=0) + _metric(df, "profit_yoy").clip(lower=0))
    return _rank_low(_metric(df, "max_drawdown_252d").abs()) * 0.55 + growth * 0.45


def _score_industry_breadth_leaders(df: pd.DataFrame) -> pd.Series:
    breadth = _rank_high(_metric(df, "industry_growth_breadth"))
    return breadth * 0.55 + _rank_high(_metric(df, "market_cap")) * 0.45


STRATEGIES: dict[str, CoarseStrategy] = {
    "market_cap_low_pe": CoarseStrategy("market_cap_low_pe", "市值龙头 + 低市盈率", "行业内市值靠前，同时 PE 越低越靠前。", _score_market_cap_low_pe, ("market_cap", "pe")),
    "market_cap_reasonable_pe": CoarseStrategy("market_cap_reasonable_pe", "市值龙头 + 合理市盈率", "行业内市值靠前，PE 越接近行业中枢越靠前。", _score_market_cap_reasonable_pe, ("market_cap", "pe")),
    "market_cap_revenue_scale": CoarseStrategy("market_cap_revenue_scale", "高市值 + 高营收规模", "市值和营业收入规模共同排序。", _score_market_cap_revenue_scale, ("market_cap", "revenue")),
    "market_cap_profit_scale": CoarseStrategy("market_cap_profit_scale", "高市值 + 高净利润规模", "市值和净利润规模共同排序。", _score_market_cap_profit_scale, ("market_cap", "profit")),
    "market_cap_revenue_growth": CoarseStrategy("market_cap_revenue_growth", "市值前排 + 营收同比为正", "市值靠前，优先营收同比增长更高者。", _score_market_cap_revenue_growth, ("market_cap", "revenue_yoy"), ("revenue_yoy",)),
    "market_cap_profit_growth": CoarseStrategy("market_cap_profit_growth", "市值前排 + 净利润同比为正", "市值靠前，优先净利润同比增长更高者。", _score_market_cap_profit_growth, ("market_cap", "profit_yoy"), ("profit_yoy",)),
    "market_cap_revenue_profit_growth": CoarseStrategy("market_cap_revenue_profit_growth", "市值前排 + 营收净利双增长", "市值、营收同比、净利润同比综合排序。", _score_market_cap_revenue_profit_growth, ("market_cap", "revenue_yoy", "profit_yoy"), ("revenue_yoy", "profit_yoy")),
    "low_pe_positive_growth": CoarseStrategy("low_pe_positive_growth", "低 PE + 正增长", "PE 越低越好，同时要求增长为正。", _score_low_pe_positive_growth, ("pe", "revenue_yoy", "profit_yoy")),
    "low_pb_positive_profit": CoarseStrategy("low_pb_positive_profit", "低 PB + 正盈利", "PB 越低越好，同时盈利规模越高越好。", _score_low_pb_positive_profit, ("pb", "profit")),
    "high_roe_reasonable_pe": CoarseStrategy("high_roe_reasonable_pe", "高 ROE + 合理估值", "ROE 靠前，PE 接近行业中枢。", _score_high_roe_reasonable_pe, ("roe", "pe")),
    "high_gross_margin_revenue_growth": CoarseStrategy("high_gross_margin_revenue_growth", "高毛利率 + 营收增长", "毛利率和营收同比综合排序。", _score_high_gross_margin_revenue_growth, ("gross_margin", "revenue_yoy"), ("revenue_yoy",)),
    "high_rd_intensity_revenue_growth": CoarseStrategy("high_rd_intensity_revenue_growth", "高研发强度 + 营收增长", "研发费用率和营收同比综合排序。", _score_high_rd_intensity_revenue_growth, ("rd_intensity", "revenue_yoy"), ("revenue_yoy",)),
    "active_amount_solid_fundamentals": CoarseStrategy("active_amount_solid_fundamentals", "成交额活跃 + 基本面不差", "近 20 日成交额和增长指标综合排序。", _score_active_amount_solid_fundamentals, ("amount_20d", "revenue_yoy", "profit_yoy")),
    "price_strength_market_cap": CoarseStrategy("price_strength_market_cap", "价格强势 + 市值前排", "近 60 日涨幅和市值综合排序。", _score_price_strength_market_cap, ("return_60d", "market_cap")),
    "low_drawdown_positive_growth": CoarseStrategy("low_drawdown_positive_growth", "回撤较小 + 正增长", "最大回撤越小越好，同时增长为正。", _score_low_drawdown_positive_growth, ("max_drawdown_252d", "revenue_yoy", "profit_yoy")),
    "industry_breadth_leaders": CoarseStrategy("industry_breadth_leaders", "行业景气扩散粗筛", "行业内增长为正的公司越多越好，再选市值龙头。", _score_industry_breadth_leaders, ("industry_growth_breadth", "market_cap")),
}


POTENTIAL_COMBO_STRATEGY_WEIGHTS = {
    "market_cap_revenue_profit_growth": 1.25,
    "high_roe_reasonable_pe": 1.15,
    "high_gross_margin_revenue_growth": 1.00,
    "low_drawdown_positive_growth": 1.15,
    "active_amount_solid_fundamentals": 1.00,
    "price_strength_market_cap": 0.75,
}


COMBO_OUTPUT_COLUMNS = [
    "code",
    "name",
    "board_name",
    "combo_score",
    "overlap_score",
    "quality_score",
    "growth_score",
    "risk_control_score",
    "liquidity_score",
    "momentum_score",
    "strategy_hits",
    "matched_strategies",
    "market_cap",
    "pe",
    "pb",
    "revenue_yoy",
    "profit_yoy",
    "roe",
    "gross_margin",
    "amount_20d",
    "return_60d",
    "max_drawdown_252d",
    "combo_reason",
    "risk_flags",
    "data_note",
]


OPTIONAL_COLUMN_ALIASES = {
    "pe": [["市盈率-动态"], ["动态市盈率"], ["市盈率"], ["pe"]],
    "pb": [["市净率"], ["pb"]],
    "revenue": [["营业总收入-营业总收入"], ["营业总收入"], ["营业收入"], ["revenue"]],
    "profit": [["净利润-净利润"], ["净利润"], ["profit"]],
    "roe": [["净资产收益率"], ["ROE"], ["roe"]],
    "gross_margin": [["销售毛利率"], ["毛利率"], ["gross_margin"]],
    "rd_expense": [["研发费用"], ["研发支出"], ["rd_expense"]],
}


def list_strategy_names() -> list[str]:
    return list(STRATEGIES)


def _find_alias(columns: pd.Index, aliases: list[list[str]]) -> str | None:
    for alias in aliases:
        if len(alias) == 1:
            col = find_col(columns, [alias[0]])
        else:
            col = find_col(columns, [], contains_all=alias)
        if col:
            return col
    return None


def _is_absolute_metric_column(metric: str, col: str) -> bool:
    if metric not in {"revenue", "profit"}:
        return True
    bad_parts = ["同比", "环比", "增长", "季度", "率"]
    return not any(part in str(col) for part in bad_parts)


def _extract_optional_metrics(raw_frames: list[pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for raw in raw_frames:
        code_col = find_col(raw.columns, ["股票代码", "代码", "code"], contains_all=["代码"])
        if not code_col:
            continue
        out = pd.DataFrame({"code": raw[code_col].astype(str).str.zfill(6)})
        for metric, aliases in OPTIONAL_COLUMN_ALIASES.items():
            col = _find_alias(raw.columns, aliases)
            if col and _is_absolute_metric_column(metric, col):
                out[metric] = raw[col].map(to_number)
        frames.append(out)
    if not frames:
        return pd.DataFrame(columns=["code"])
    metrics = frames[0]
    for frame in frames[1:]:
        metrics = metrics.merge(frame, on="code", how="outer", suffixes=("", "_new"))
        for col in list(metrics.columns):
            if col.endswith("_new"):
                base = col[:-4]
                if base in metrics.columns:
                    metrics[base] = metrics[base].combine_first(metrics[col])
                    metrics = metrics.drop(columns=[col])
                else:
                    metrics = metrics.rename(columns={col: base})
    return metrics


def _load_price_metrics(codes: list[str]) -> pd.DataFrame:
    conn = sqlite3.connect(db_path())
    if not codes:
        return pd.DataFrame(columns=["code"])
    placeholders = ",".join("?" for _ in codes)
    try:
        prices = pd.read_sql_query(
            f"""
            select code, trade_date, close, amount, updated_at
            from quotes_daily
            where code in ({placeholders})
            order by code, trade_date, updated_at
            """,
            conn,
            params=codes,
        )
    except Exception:
        return pd.DataFrame(columns=["code"])
    if prices.empty:
        return pd.DataFrame(columns=["code"])
    prices = prices.drop_duplicates(["code", "trade_date"], keep="last")
    rows = []
    for code, group in prices.groupby("code"):
        group = group.sort_values("trade_date")
        last_close = pd.to_numeric(group["close"], errors="coerce").dropna()
        if last_close.empty:
            continue
        close = pd.to_numeric(group["close"], errors="coerce")
        amount = pd.to_numeric(group["amount"], errors="coerce")
        return_60d = float(close.iloc[-1] / close.iloc[max(0, len(close) - 60)] - 1) if len(close) > 1 else float("nan")
        rolling_high = close.cummax()
        drawdown = close / rolling_high - 1
        rows.append(
            {
                "code": str(code).zfill(6),
                "amount_20d": float(amount.tail(20).mean()) if amount.notna().any() else float("nan"),
                "return_60d": return_60d,
                "max_drawdown_252d": float(drawdown.tail(252).min()) if drawdown.notna().any() else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def build_base_universe(args) -> tuple[pd.DataFrame, dict]:
    report_raw, report_date, financial_source = load_financial_report(args.report_date, args.refresh, args.source, args.no_proxy)
    fin = normalize_financials(report_raw)
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    universe, tech_board_count, universe_source, quote_source = build_tech_universe(
        args.refresh, keywords, args.no_proxy, args.source, fin
    )
    base = universe.merge(fin, on="code", how="left")
    spot, _ = load_spot(args.refresh, args.no_proxy, args.source)
    optional = _extract_optional_metrics([report_raw, spot])
    if not optional.empty:
        base = base.merge(optional, on="code", how="left")
    if "revenue" in base.columns and "rd_expense" in base.columns:
        base["rd_intensity"] = pd.to_numeric(base["rd_expense"], errors="coerce") / pd.to_numeric(base["revenue"], errors="coerce")
    price_metrics = _load_price_metrics(base["code"].astype(str).tolist())
    if not price_metrics.empty:
        base = base.merge(price_metrics, on="code", how="left")
    growth_flags = base.assign(_growth_positive=_positive(base["revenue_yoy"]) & _positive(base["profit_yoy"]))
    breadth = growth_flags.groupby("board_name")["_growth_positive"].transform("sum")
    base["industry_growth_breadth"] = breadth
    meta = {
        "report_date": report_date,
        "financial_source": financial_source,
        "universe_source": universe_source,
        "quote_source": quote_source,
        "tech_boards": tech_board_count,
        "tech_universe": len(universe),
    }
    return base, meta


def _apply_positive_filters(df: pd.DataFrame, strategy: CoarseStrategy) -> pd.DataFrame:
    out = df.copy()
    for metric in strategy.positive_filters:
        if metric in out.columns and pd.to_numeric(out[metric], errors="coerce").notna().any():
            out = out[_positive(out[metric])]
    return out


def _missing_required_metrics(df: pd.DataFrame, strategy: CoarseStrategy) -> list[str]:
    return [
        metric
        for metric in strategy.required_metrics
        if metric not in df.columns or pd.to_numeric(df[metric], errors="coerce").notna().sum() == 0
    ]


def _select_strategy_from_base(base: pd.DataFrame, args, strategy_name: str, top: int) -> tuple[pd.DataFrame, list[str]]:
    strategy = STRATEGIES[strategy_name]
    filtered = _apply_positive_filters(base, strategy)
    if filtered.empty:
        filtered = base.copy()
    selected = filtered.copy()
    selected["coarse_score"] = strategy.ranker(selected)
    selected["coarse_strategy"] = strategy.name
    selected["coarse_strategy_title"] = strategy.title
    selected["coarse_reason"] = strategy.description
    missing = _missing_required_metrics(selected, strategy)
    selected["data_note"] = "完整字段" if not missing else "缺少字段，已降级: " + ",".join(missing)
    return selected.sort_values(["coarse_score", "market_cap"], ascending=[False, False]).head(top).copy(), missing


def _fmt_flag(condition: bool, text: str) -> str | None:
    return text if condition else None


def _row_risk_flags(row) -> str:
    revenue_yoy = row.get("revenue_yoy", pd.NA)
    profit_yoy = row.get("profit_yoy", pd.NA)
    max_drawdown_252d = row.get("max_drawdown_252d", pd.NA)
    return_60d = row.get("return_60d", pd.NA)
    pe = row.get("pe", pd.NA)
    amount_20d = row.get("amount_20d", pd.NA)
    flags = [
        _fmt_flag(pd.notna(revenue_yoy) and revenue_yoy <= 0, "营收未正增长"),
        _fmt_flag(pd.notna(profit_yoy) and profit_yoy <= 0, "净利未正增长"),
        _fmt_flag(pd.notna(max_drawdown_252d) and max_drawdown_252d < -0.35, "年内回撤偏大"),
        _fmt_flag(pd.notna(return_60d) and return_60d < -0.15, "60日走势偏弱"),
        _fmt_flag(pd.notna(pe) and (pe <= 0 or pe > 100), "PE异常或偏高"),
        _fmt_flag(pd.notna(amount_20d) and amount_20d < 20000000, "成交额偏低"),
    ]
    clean = [flag for flag in flags if flag]
    return "、".join(clean) if clean else "暂无明显粗筛风险"


def _combo_reason(row) -> str:
    revenue_yoy = row.get("revenue_yoy", pd.NA)
    profit_yoy = row.get("profit_yoy", pd.NA)
    roe = row.get("roe", pd.NA)
    max_drawdown_252d = row.get("max_drawdown_252d", pd.NA)
    amount_20d = row.get("amount_20d", pd.NA)
    reasons = []
    if row.get("strategy_hits", 0) >= 3:
        reasons.append("多策略共振")
    if pd.notna(revenue_yoy) and pd.notna(profit_yoy) and revenue_yoy > 0 and profit_yoy > 0:
        reasons.append("营收净利双增长")
    if pd.notna(roe) and roe > 10:
        reasons.append("ROE较好")
    if pd.notna(max_drawdown_252d) and max_drawdown_252d >= -0.25:
        reasons.append("回撤相对可控")
    if pd.notna(amount_20d) and amount_20d >= 20000000:
        reasons.append("流动性达标")
    return "、".join(reasons) if reasons else "组合分靠前，需人工复核基本面与风险"


def run_one(args, strategy_name: str) -> tuple[pd.DataFrame, dict]:
    if strategy_name not in STRATEGIES:
        raise RuntimeError(f"Unknown coarse strategy: {strategy_name}")
    strategy = STRATEGIES[strategy_name]
    base, meta = coarse_repository.build_base_universe(args)
    selected, missing = _select_strategy_from_base(base, args, strategy_name, args.top)
    cols = [
        "coarse_strategy",
        "coarse_strategy_title",
        "code",
        "name",
        "board_name",
        "market_cap",
        "pe",
        "pb",
        "revenue_yoy",
        "profit_yoy",
        "amount_20d",
        "return_60d",
        "max_drawdown_252d",
        "coarse_score",
        "data_note",
        "coarse_reason",
    ]
    for col in cols:
        if col not in selected.columns:
            selected[col] = pd.NA
    meta.update({"strategy": strategy.name, "strategy_title": strategy.title, "top": args.top, "selected": len(selected)})
    return selected[cols], meta


def _base_for_combo(args, candidates: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    base, meta = coarse_repository.build_base_universe(args)
    if candidates is None:
        return base, meta
    if candidates.empty or "code" not in candidates.columns:
        return base.iloc[0:0].copy(), {**meta, "upstream_candidates": 0}
    codes = candidates["code"].astype(str).str.zfill(6).dropna().unique().tolist()
    filtered = base[base["code"].astype(str).str.zfill(6).isin(codes)].copy()
    meta.update({"upstream_stage": "sector_screen", "upstream_candidates": len(codes)})
    return filtered, meta


def run_combo(args, candidates: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    base, meta = _base_for_combo(args, candidates)
    if base.empty:
        meta.update({"strategy": "potential_combo", "top": args.top, "selected": 0})
        result = pd.DataFrame(columns=COMBO_OUTPUT_COLUMNS)
        persist_layer_result("combo", args, result, meta)
        return result, meta

    strategy_top = max(args.top, getattr(args, "combo_strategy_top", 20))
    strategy_frames = []
    missing_by_strategy = {}
    for name in POTENTIAL_COMBO_STRATEGY_WEIGHTS:
        selected, missing = _select_strategy_from_base(base, args, name, strategy_top)
        selected["strategy_weight"] = POTENTIAL_COMBO_STRATEGY_WEIGHTS[name]
        strategy_frames.append(selected)
        if missing:
            missing_by_strategy[name] = missing

    hits = pd.concat(strategy_frames, ignore_index=True) if strategy_frames else pd.DataFrame()
    base_scored = base.copy()
    base_scored["growth_score"] = _rank_high(_metric(base_scored, "revenue_yoy").clip(lower=0) + _metric(base_scored, "profit_yoy").clip(lower=0)) * 100
    base_scored["quality_score"] = (
        _rank_high(_metric(base_scored, "roe")) * 0.45
        + _rank_high(_metric(base_scored, "gross_margin")) * 0.30
        + _reasonable_pe_score(_metric(base_scored, "pe")) * 0.25
    ) * 100
    base_scored["risk_control_score"] = (
        _rank_low(_metric(base_scored, "max_drawdown_252d").abs()) * 0.70
        + _rank_high(_metric(base_scored, "amount_20d")) * 0.30
    ) * 100
    base_scored["liquidity_score"] = _rank_high(_metric(base_scored, "amount_20d")) * 100
    base_scored["momentum_score"] = _rank_high(_metric(base_scored, "return_60d")) * 100

    total_weight = sum(POTENTIAL_COMBO_STRATEGY_WEIGHTS.values())
    if hits.empty:
        base_scored["strategy_hits"] = 0
        base_scored["matched_strategies"] = ""
        base_scored["overlap_score"] = 0.0
    else:
        hit_summary = (
            hits.groupby("code", as_index=False)
            .agg(
                strategy_hits=("coarse_strategy", "nunique"),
                matched_strategies=("coarse_strategy_title", lambda values: "、".join(dict.fromkeys(values.astype(str)))),
                matched_weight=("strategy_weight", "sum"),
            )
        )
        hit_summary["overlap_score"] = hit_summary["matched_weight"] / total_weight * 100
        base_scored = base_scored.merge(hit_summary[["code", "strategy_hits", "matched_strategies", "overlap_score"]], on="code", how="left")
        base_scored["strategy_hits"] = base_scored["strategy_hits"].fillna(0).astype(int)
        base_scored["matched_strategies"] = base_scored["matched_strategies"].fillna("")
        base_scored["overlap_score"] = base_scored["overlap_score"].fillna(0.0)

    base_scored["combo_score"] = (
        base_scored["overlap_score"] * 0.35
        + base_scored["growth_score"] * 0.20
        + base_scored["quality_score"] * 0.18
        + base_scored["risk_control_score"] * 0.15
        + base_scored["liquidity_score"] * 0.07
        + base_scored["momentum_score"] * 0.05
    )
    base_scored["risk_flags"] = base_scored.apply(_row_risk_flags, axis=1)
    base_scored["combo_reason"] = base_scored.apply(_combo_reason, axis=1)
    data_notes = []
    if missing_by_strategy:
        for name, missing in missing_by_strategy.items():
            data_notes.append(f"{name}:缺少{','.join(missing)}")
    base_scored["data_note"] = "完整字段" if not data_notes else "部分策略降级；" + "；".join(data_notes)

    selected = base_scored.sort_values(["combo_score", "overlap_score", "market_cap"], ascending=[False, False, False]).head(args.top).copy()
    for col in COMBO_OUTPUT_COLUMNS:
        if col not in selected.columns:
            selected[col] = pd.NA
    meta.update(
        {
            "strategy": "potential_combo",
            "strategy_title": "潜力股组合评分",
            "top": args.top,
            "combo_strategy_top": strategy_top,
            "selected": len(selected),
            "combo_strategies": list(POTENTIAL_COMBO_STRATEGY_WEIGHTS),
        }
    )
    result = selected[COMBO_OUTPUT_COLUMNS]
    persist_layer_result("combo", args, result, meta)
    return result, meta


def run(args) -> tuple[pd.DataFrame, dict]:
    if args.strategy == "all":
        frames = []
        meta = {"strategy": "all", "top": args.top}
        for name in STRATEGIES:
            df, one_meta = run_one(args, name)
            frames.append(df)
            meta.update({k: v for k, v in one_meta.items() if k not in {"strategy", "strategy_title", "selected"}})
        result = pd.concat(frames, ignore_index=True)
        persist_layer_result("coarse", args, result, meta)
        return result, meta
    result, meta = run_one(args, args.strategy)
    persist_layer_result("coarse", args, result, meta)
    return result, meta
