from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dashboard.view_model import build_dashboard_view_model


class DashboardViewModelTest(unittest.TestCase):
    def test_builds_stage_counts_action_counts_and_code_traces(self) -> None:
        stages = {
            "sector_screen": pd.DataFrame(
                [
                    {"code": "000725", "name": "京东方A", "board_name": "光学光电子"},
                    {"code": "688981", "name": "中芯国际", "board_name": "半导体"},
                ]
            ),
            "combo": pd.DataFrame(
                [
                    {
                        "code": "000725",
                        "name": "京东方A",
                        "combo_score": 88.6,
                    }
                ]
            ),
            "allocation": pd.DataFrame(
                [
                    {
                        "code": "000725",
                        "name": "京东方A",
                        "portfolio_action": "可条件买入",
                        "budget_status": "预算内",
                    },
                    {
                        "code": "688981",
                        "name": "中芯国际",
                        "portfolio_action": "只做风向标",
                        "budget_status": "一手超过单股仓位上限",
                    },
                ]
            ),
        }
        metas = {
            "sector_screen": {"report_date": "20260331"},
            "allocation": {"capital": 15000, "core_etf_budget": 9000},
        }

        model = build_dashboard_view_model(stages, metas)

        self.assertEqual(model["summary"]["stage_counts"]["sector_screen"], 2)
        self.assertEqual(model["summary"]["stage_counts"]["allocation"], 2)
        self.assertEqual(model["summary"]["action_counts"]["可条件买入"], 1)
        self.assertEqual(model["summary"]["action_counts"]["只做风向标"], 1)
        self.assertEqual(model["stages"][0]["key"], "sector_screen")
        self.assertEqual(model["stages"][0]["title"], "板块筛选")
        self.assertEqual(model["stages"][1]["key"], "combo")
        self.assertEqual(model["stages"][1]["title"], "宏观粗筛")
        self.assertEqual(model["stages"][0]["rows"][0]["code"], "000725")
        self.assertIn("000725", model["traces"])
        self.assertEqual(model["traces"]["000725"][0]["stage"], "sector_screen")
        self.assertEqual(model["traces"]["000725"][1]["stage"], "combo")
        self.assertEqual(model["traces"]["000725"][2]["stage"], "allocation")


if __name__ == "__main__":
    unittest.main()
