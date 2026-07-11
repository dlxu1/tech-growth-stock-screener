"""Run the full selection pipeline and build dashboard data."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from allocation.personal_plan import run_allocation_plan
from dashboard.view_model import build_dashboard_view_model
from plan.trade_plan import run_trade_plan
from strategies import sector_screen
from strategies.coarse.registry import run_combo
from strategies.fine.technical import run as run_fine


def run_dashboard(args) -> dict:
    """Run each existing stage and return a dashboard view model."""

    sector_args = SimpleNamespace(**vars(args))
    sector_args.top = getattr(args, "sector_top", 100)
    combo_args = SimpleNamespace(**vars(args))
    combo_args.top = getattr(args, "combo_top", 10)

    sector_result, sector_meta = sector_screen.run(sector_args)
    combo, combo_meta = run_combo(combo_args, candidates=sector_result)
    fine, fine_meta = run_fine(args, candidates=combo)
    plan, plan_meta = run_trade_plan(args)
    allocation, allocation_meta = run_allocation_plan(args)

    stages: dict[str, pd.DataFrame] = {
        "sector_screen": sector_result,
        "combo": combo,
        "fine": fine,
        "plan": plan,
        "allocation": allocation,
    }
    metas = {
        "sector_screen": sector_meta,
        "combo": combo_meta,
        "fine": fine_meta,
        "plan": plan_meta,
        "allocation": allocation_meta,
    }
    return build_dashboard_view_model(stages, metas)
