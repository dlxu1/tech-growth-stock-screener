"""Run the full selection pipeline and build dashboard data."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from dashboard.health import audit_dashboard_model
from dashboard.stock_types import annotate_stock_types, filter_by_stock_types, load_stock_type_rules, parse_stock_types
from dashboard.market_state import compute_dynamic_thresholds, detect
from dashboard.view_model import build_dashboard_view_model
from plan.trade_plan import run_trade_plan
from strategies import sector_screen
from strategies.coarse.registry import run_combo
from strategies.fine.technical import run as run_fine


def _attention_ranked_candidates(fine: pd.DataFrame) -> pd.DataFrame:
    """Rank fine rows by macro potential first and technical timing second."""

    if fine.empty:
        return fine.copy()
    ranked = fine.copy()
    macro_source = ranked["combo_score"] if "combo_score" in ranked.columns else ranked.get("coarse_score", 0)
    if not isinstance(macro_source, pd.Series):
        macro_source = pd.Series([macro_source] * len(ranked), index=ranked.index)
    technical_source = ranked.get("technical_score", 0)
    if not isinstance(technical_source, pd.Series):
        technical_source = pd.Series([technical_source] * len(ranked), index=ranked.index)
    macro = pd.to_numeric(macro_source, errors="coerce").fillna(0)
    technical = pd.to_numeric(technical_source, errors="coerce").fillna(0)
    if "coarse_score" not in ranked.columns:
        ranked["coarse_score"] = macro
    if "technical_score" not in ranked.columns:
        ranked["technical_score"] = technical
    ranked["attention_score"] = macro * 0.65 + technical * 0.35
    return ranked.sort_values(["attention_score", "coarse_score", "technical_score"], ascending=[False, False, False]).copy()


def _build_backtest_model(model: dict, args) -> dict | None:
    if getattr(args, "_skip_backtest", False):
        return None
    signal_inputs = _build_signal_inputs(model, args)
    if signal_inputs is None:
        return None
    signal_date, candidates, quotes, _signal_model = signal_inputs

    from backtest.signal_backtest import build_signal_backtest_model, parse_holding_days

    return build_signal_backtest_model(
        candidates,
        quotes,
        signal_date=signal_date,
        top=int(getattr(args, "backtest_top", 10) or 10),
        holding_days=parse_holding_days(getattr(args, "holding_days", "")),
    )


def _build_signal_validation_model(model: dict, args) -> dict | None:
    if getattr(args, "_skip_signal_validation", False):
        return None
    signal_inputs = _build_signal_inputs(model, args)
    if signal_inputs is None:
        return None
    signal_date, candidates, quotes, _signal_model = signal_inputs

    from backtest.signal_backtest import build_signal_validation_model, parse_holding_days

    return build_signal_validation_model(
        candidates,
        quotes,
        signal_date=signal_date,
        holding_days=parse_holding_days(getattr(args, "holding_days", "")),
        bucket_size=int(getattr(args, "bucket_size", 10) or 10),
        macro_threshold=getattr(args, "macro_potential_threshold", None),
        tech_threshold=getattr(args, "technical_timing_threshold", None),
    )


def _build_operation_backtest_model(model: dict, args) -> dict | None:
    if getattr(args, "_skip_operation_backtest", False):
        return None
    signal_inputs = _build_signal_inputs(model, args)
    if signal_inputs is None:
        return None
    signal_date, _candidates, quotes, signal_model = signal_inputs

    from backtest.operation_backtest import DEFAULT_PROFIT_TARGET_PCT, build_operation_backtest_model, plans_from_dashboard_model

    plans = plans_from_dashboard_model(signal_model)
    return build_operation_backtest_model(
        plans,
        quotes,
        signal_date=signal_date,
        profit_target_pct=float(getattr(args, "operation_profit_target", DEFAULT_PROFIT_TARGET_PCT) or DEFAULT_PROFIT_TARGET_PCT),
        macro_threshold=getattr(args, "macro_potential_threshold", None),
        tech_threshold=getattr(args, "technical_timing_threshold", None),
    )


def _build_signal_inputs(model: dict, args) -> tuple[str, pd.DataFrame, pd.DataFrame, dict] | None:
    if getattr(args, "_signal_inputs", None) is not None:
        return getattr(args, "_signal_inputs")
    signal_date = str(getattr(args, "backtest_date", "") or getattr(args, "as_of_date", "") or "").strip()
    if not signal_date:
        return None

    from backtest.repository import load_forward_quotes
    from backtest.signal_backtest import candidates_from_dashboard_model

    signal_model = model
    matrix_date = str(getattr(args, "as_of_date", "") or "").strip()
    if signal_date != matrix_date:
        signal_args = SimpleNamespace(**vars(args))
        signal_args.as_of_date = signal_date
        signal_args.backtest_date = ""
        signal_args._skip_backtest = True
        signal_args._skip_signal_validation = True
        signal_model = run_dashboard(signal_args)

    candidates = candidates_from_dashboard_model(signal_model)
    codes = candidates["code"].astype(str).str.zfill(6).dropna().unique().tolist() if "code" in candidates.columns else []
    quotes = load_forward_quotes(codes, after_date=signal_date)
    result = (signal_date, candidates, quotes, signal_model)
    setattr(args, "_signal_inputs", result)
    return result


def run_dashboard(args) -> dict:
    """Run each existing stage and return a dashboard view model."""

    stock_type_rules = load_stock_type_rules(getattr(args, "stock_type_config", None))
    selected_stock_types = parse_stock_types(getattr(args, "stock_types", ""))
    sector_args = SimpleNamespace(**vars(args))
    sector_args.top = getattr(args, "sector_top", 100)
    combo_args = SimpleNamespace(**vars(args))
    combo_args.top = getattr(args, "combo_top", 100)
    fine_args = SimpleNamespace(**vars(args))

    sector_result, sector_meta = sector_screen.run(sector_args)
    sector_result = annotate_stock_types(sector_result, stock_type_rules)
    combo_candidates = filter_by_stock_types(sector_result, selected_stock_types)
    combo, combo_meta = run_combo(combo_args, candidates=combo_candidates)
    fine_args.top = len(combo) if not combo.empty else getattr(args, "top", 20)
    fine, fine_meta = run_fine(fine_args, candidates=combo)
    if not combo.empty and not fine.empty and "combo_score" in combo.columns and "combo_score" not in fine.columns:
        combo_scores = combo[["code", "combo_score"]].copy()
        fine = fine.merge(combo_scores, on="code", how="left")
    market_state = detect(
        fine["code"].astype(str).str.zfill(6).tolist() if not fine.empty else [],
        as_of_date=getattr(args, "as_of_date", None) or None,
    )
    # 市场状态影响仓位上限：防御模式下 max_position 打折
    if market_state.label == "defensive":
        original_max = getattr(args, "max_position", 0.25) or 0.25
        setattr(args, "max_position", round(original_max * market_state.position_multiplier, 4))
    # 动态阈值：根据当前候选股分数分布自适应象限线
    adaptive_thresholds = compute_dynamic_thresholds(
        combo_scores=pd.to_numeric(fine.get("combo_score", pd.Series(dtype=float)), errors="coerce").dropna().tolist() if not fine.empty else [],
        technical_scores=pd.to_numeric(fine.get("technical_score", pd.Series(dtype=float)), errors="coerce").dropna().tolist() if not fine.empty else [],
    )
    plan_candidates = _attention_ranked_candidates(fine)
    plan, plan_meta = run_trade_plan(args, candidates=plan_candidates)
    if not plan.empty and not plan_candidates.empty:
        enrich_cols = [col for col in ["code", "attention_score", "coarse_score"] if col in plan_candidates.columns]
        if len(enrich_cols) > 1:
            plan = plan.merge(plan_candidates[enrich_cols], on="code", how="left")
        if "attention_score" in plan.columns:
            sort_cols = [col for col in ["attention_score", "technical_score"] if col in plan.columns]
            plan = plan.sort_values(sort_cols, ascending=[False] * len(sort_cols))
    plan_meta = {**plan_meta, "selected": len(plan)}

    stages: dict[str, pd.DataFrame] = {
        "sector_screen": sector_result,
        "combo": combo,
        "fine": fine,
        "plan": plan,
    }
    metas = {
        "sector_screen": sector_meta,
        "combo": combo_meta,
        "fine": fine_meta,
        "plan": plan_meta,
    }
    model = build_dashboard_view_model(stages, metas, stock_type_rules=stock_type_rules)
    model["summary"]["stock_type_filter"] = {
        "selected_types": selected_stock_types,
        "before_count": len(sector_result),
        "after_count": len(combo_candidates),
        "config_path": stock_type_rules.source_path,
    }
    model["summary"]["as_of_date"] = getattr(args, "as_of_date", "") or ""
    model["summary"]["backtest_date"] = getattr(args, "backtest_date", "") or getattr(args, "as_of_date", "") or ""
    model["summary"]["universe"] = getattr(args, "universe", "") or ""
    model["summary"]["universe_index_symbol"] = getattr(args, "universe_index_symbol", "") or ""
    model["summary"]["sector"] = getattr(args, "sector", "") or ""
    model["summary"]["market_state"] = {
        "label": market_state.label,
        "median_close_vs_ma20": market_state.median_close_vs_ma20 if pd.notna(market_state.median_close_vs_ma20) else None,
        "median_ma20_slope": market_state.median_ma20_slope if pd.notna(market_state.median_ma20_slope) else None,
        "sample_count": market_state.sample_count,
        "position_multiplier": market_state.position_multiplier,
        "note": market_state.note,
    }
    model["summary"]["adaptive_thresholds"] = adaptive_thresholds
    setattr(args, "macro_potential_threshold", adaptive_thresholds.get("macro_potential_threshold"))
    setattr(args, "technical_timing_threshold", adaptive_thresholds.get("technical_timing_threshold"))
    model["summary"]["health"] = audit_dashboard_model(model)
    backtest = _build_backtest_model(model, args)
    if backtest is not None:
        model["backtest"] = backtest
    signal_validation = _build_signal_validation_model(model, args)
    if signal_validation is not None:
        model["signal_validation"] = signal_validation
    operation_backtest = _build_operation_backtest_model(model, args)
    if operation_backtest is not None:
        model["operation_backtest"] = operation_backtest
    return model
