"""Run the full selection pipeline and build dashboard data."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from dashboard.health import audit_dashboard_model
from dashboard.stock_types import annotate_stock_types, filter_by_stock_types, load_stock_type_rules, parse_stock_types
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
    model["summary"]["health"] = audit_dashboard_model(model)
    return model
