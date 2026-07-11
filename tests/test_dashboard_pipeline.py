from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dashboard.pipeline import run_dashboard


class DashboardPipelineTest(unittest.TestCase):
    def test_runs_all_stages_and_builds_view_model(self) -> None:
        args = Namespace(strategy="tech_growth", coarse_strategy="all", top=5, sector_top=100, coarse_top=5, sector="半导体")
        one_row = pd.DataFrame([{"code": "000725", "name": "京东方A"}])

        with (
            patch("dashboard.pipeline.sector_screen.run", return_value=(one_row, {"stage": "sector_screen"})) as sector_run,
            patch("dashboard.pipeline.run_combo", return_value=(one_row, {"stage": "combo"})) as combo_run,
            patch("dashboard.pipeline.run_fine", return_value=(one_row, {"stage": "fine"})) as fine_run,
            patch("dashboard.pipeline.run_trade_plan", return_value=(one_row, {"stage": "plan"})),
            patch("dashboard.pipeline.run_allocation_plan", return_value=(one_row, {"stage": "allocation", "capital": 15000})),
        ):
            model = run_dashboard(args)

        self.assertEqual(sector_run.call_args.args[0].top, 100)
        self.assertEqual(sector_run.call_args.args[0].sector, "半导体")
        self.assertEqual(combo_run.call_args.args[0].top, 10)
        self.assertEqual(fine_run.call_args.args[0].top, 5)
        self.assertIs(combo_run.call_args.kwargs["candidates"], one_row)
        self.assertIs(fine_run.call_args.kwargs["candidates"], one_row)
        keys = [stage["key"] for stage in model["stages"]]
        self.assertEqual(keys, ["sector_screen", "combo", "fine", "plan", "allocation"])
        self.assertEqual(model["summary"]["stage_counts"]["plan"], 1)
        self.assertIn("000725", model["traces"])


if __name__ == "__main__":
    unittest.main()
