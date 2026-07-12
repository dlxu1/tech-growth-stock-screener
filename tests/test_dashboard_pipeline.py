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
        combo_rows = pd.DataFrame(
            [
                {"code": f"{i:06d}", "name": f"股票{i}", "combo_score": 100 - i}
                for i in range(1, 112)
            ]
        )
        combo_top100 = combo_rows.head(100)
        fine_rows = combo_rows.assign(technical_score=[50 + i for i in range(1, 112)])
        fine_top100 = fine_rows.head(100)
        plan_rows = pd.DataFrame([{"code": f"{i:06d}", "name": f"股票{i}", "action": "等待回踩买入"} for i in range(1, 101)])

        with (
            patch("dashboard.pipeline.sector_screen.run", return_value=(one_row, {"stage": "sector_screen"})) as sector_run,
            patch("dashboard.pipeline.run_combo", return_value=(combo_top100, {"stage": "combo"})) as combo_run,
            patch("dashboard.pipeline.run_fine", return_value=(fine_top100, {"stage": "fine"})) as fine_run,
            patch("dashboard.pipeline.run_trade_plan", return_value=(plan_rows, {"stage": "plan"})) as plan_run,
        ):
            model = run_dashboard(args)

        self.assertEqual(sector_run.call_args.args[0].top, 100)
        self.assertEqual(sector_run.call_args.args[0].sector, "半导体")
        self.assertEqual(combo_run.call_args.args[0].top, 100)
        self.assertEqual(fine_run.call_args.args[0].top, 100)
        combo_candidates = combo_run.call_args.kwargs["candidates"]
        self.assertEqual(combo_candidates["code"].tolist(), one_row["code"].tolist())
        self.assertIn("stock_type", combo_candidates.columns)
        self.assertIs(fine_run.call_args.kwargs["candidates"], combo_top100)
        self.assertEqual(len(plan_run.call_args.kwargs["candidates"]), 100)
        self.assertIn("attention_score", plan_run.call_args.kwargs["candidates"].columns)
        keys = [stage["key"] for stage in model["stages"]]
        self.assertEqual(keys, ["sector_screen", "combo", "fine", "plan"])
        self.assertEqual(model["stages"][-1]["title"], "操作建议")
        self.assertEqual(model["summary"]["stage_counts"]["combo"], 100)
        self.assertEqual(model["summary"]["stage_counts"]["fine"], 100)
        self.assertEqual(model["summary"]["stage_counts"]["plan"], 100)
        self.assertIn("health", model["summary"])
        self.assertIn("health_score", model["summary"]["health"])
        self.assertEqual(model["stages"][-1]["rows"][0]["action"], "等待回踩买入")
        self.assertNotIn("budget_status", model["stages"][-1]["rows"][0])
        self.assertIn("000001", model["traces"])

    def test_filters_downstream_candidates_by_stock_type(self) -> None:
        args = Namespace(
            strategy="tech_growth",
            coarse_strategy="all",
            top=5,
            sector_top=100,
            coarse_top=5,
            sector="",
            stock_types="科技股",
            stock_type_config="",
        )
        sector_rows = pd.DataFrame(
            [
                {"code": "000001", "name": "科技样本", "board_name": "半导体"},
                {"code": "000002", "name": "周期样本", "board_name": "煤炭开采"},
            ]
        )
        combo_rows = pd.DataFrame([{"code": "000001", "name": "科技样本", "combo_score": 90}])
        fine_rows = pd.DataFrame([{"code": "000001", "name": "科技样本", "technical_score": 80, "combo_score": 90}])
        plan_rows = pd.DataFrame([{"code": "000001", "name": "科技样本", "action": "观察"}])

        with (
            patch("dashboard.pipeline.sector_screen.run", return_value=(sector_rows, {"stage": "sector_screen"})),
            patch("dashboard.pipeline.run_combo", return_value=(combo_rows, {"stage": "combo"})) as combo_run,
            patch("dashboard.pipeline.run_fine", return_value=(fine_rows, {"stage": "fine"})),
            patch("dashboard.pipeline.run_trade_plan", return_value=(plan_rows, {"stage": "plan"})),
        ):
            model = run_dashboard(args)

        downstream_candidates = combo_run.call_args.kwargs["candidates"]
        self.assertEqual(downstream_candidates["code"].tolist(), ["000001"])
        self.assertEqual(downstream_candidates["stock_type"].tolist(), ["科技股"])
        self.assertEqual(model["summary"]["stock_type_filter"]["selected_types"], ["科技股"])
        self.assertEqual(model["summary"]["stock_type_filter"]["before_count"], 2)
        self.assertEqual(model["summary"]["stock_type_filter"]["after_count"], 1)

    def test_as_of_date_is_passed_to_all_dashboard_stages(self) -> None:
        args = Namespace(
            strategy="tech_growth",
            coarse_strategy="all",
            top=5,
            sector_top=100,
            coarse_top=5,
            sector="",
            stock_types="",
            stock_type_config="",
            as_of_date="2026-06-28",
        )
        one_row = pd.DataFrame([{"code": "000001", "name": "样本", "board_name": "半导体"}])

        with (
            patch("dashboard.pipeline.sector_screen.run", return_value=(one_row, {"stage": "sector_screen"})) as sector_run,
            patch("dashboard.pipeline.run_combo", return_value=(one_row.assign(combo_score=80), {"stage": "combo"})) as combo_run,
            patch("dashboard.pipeline.run_fine", return_value=(one_row.assign(technical_score=70, combo_score=80), {"stage": "fine"})) as fine_run,
            patch("dashboard.pipeline.run_trade_plan", return_value=(one_row.assign(action="观察"), {"stage": "plan"})) as plan_run,
            patch("backtest.repository.load_forward_quotes", return_value=pd.DataFrame()) as quote_loader,
        ):
            model = run_dashboard(args)

        self.assertEqual(sector_run.call_args.args[0].as_of_date, "2026-06-28")
        self.assertEqual(combo_run.call_args.args[0].as_of_date, "2026-06-28")
        self.assertEqual(fine_run.call_args.args[0].as_of_date, "2026-06-28")
        self.assertEqual(plan_run.call_args.args[0].as_of_date, "2026-06-28")
        self.assertEqual(model["summary"]["as_of_date"], "2026-06-28")
        quote_loader.assert_called_once()
        self.assertEqual(model["backtest"]["summary"]["signal_date"], "2026-06-28")
        self.assertIn("signal_validation", model)
        self.assertIn("operation_backtest", model)
        self.assertEqual(model["signal_validation"]["summary"]["signal_dates"], ["2026-06-28"])
        self.assertEqual(model["operation_backtest"]["summary"]["signal_date"], "2026-06-28")
        self.assertEqual([item["title"] for item in model["backtest"]["strategies"]], ["宏观潜力 Top10", "技术分 Top10", "综合关注 Top10"])

    def test_backtest_date_can_differ_from_matrix_date(self) -> None:
        args = Namespace(
            strategy="tech_growth",
            coarse_strategy="all",
            top=5,
            sector_top=100,
            coarse_top=5,
            sector="",
            stock_types="",
            stock_type_config="",
            as_of_date="2026-07-10",
            backtest_date="2026-06-30",
        )
        one_row = pd.DataFrame([{"code": "000001", "name": "样本", "board_name": "半导体"}])

        with (
            patch("dashboard.pipeline.sector_screen.run", return_value=(one_row, {"stage": "sector_screen"})) as sector_run,
            patch("dashboard.pipeline.run_combo", return_value=(one_row.assign(combo_score=80), {"stage": "combo"})),
            patch("dashboard.pipeline.run_fine", return_value=(one_row.assign(technical_score=70, combo_score=80), {"stage": "fine"})),
            patch("dashboard.pipeline.run_trade_plan", return_value=(one_row.assign(action="观察"), {"stage": "plan"})),
            patch("backtest.repository.load_forward_quotes", return_value=pd.DataFrame()) as quote_loader,
        ):
            model = run_dashboard(args)

        self.assertEqual(model["summary"]["as_of_date"], "2026-07-10")
        self.assertEqual(model["summary"]["backtest_date"], "2026-06-30")
        self.assertEqual(model["backtest"]["summary"]["signal_date"], "2026-06-30")
        self.assertEqual(model["signal_validation"]["summary"]["signal_dates"], ["2026-06-30"])
        self.assertEqual(model["operation_backtest"]["summary"]["signal_date"], "2026-06-30")
        self.assertEqual(quote_loader.call_args.kwargs["after_date"], "2026-06-30")
        self.assertIn("2026-06-30", [call.args[0].as_of_date for call in sector_run.call_args_list])


if __name__ == "__main__":
    unittest.main()
