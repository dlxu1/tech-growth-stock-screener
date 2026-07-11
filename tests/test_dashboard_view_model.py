from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dashboard.stock_types import load_stock_type_rules
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
            "plan": pd.DataFrame(
                [
                    {
                        "code": "000725",
                        "name": "京东方A",
                        "action": "等待回踩买入",
                    },
                    {
                        "code": "688981",
                        "name": "中芯国际",
                        "action": "暂不交易",
                    },
                ]
            ),
        }
        metas = {
            "sector_screen": {"report_date": "20260331"},
            "plan": {},
        }

        model = build_dashboard_view_model(stages, metas)

        self.assertEqual(model["summary"]["stage_counts"]["sector_screen"], 2)
        self.assertEqual(model["summary"]["stage_counts"]["plan"], 2)
        self.assertEqual(model["summary"]["action_counts"]["等待回踩买入"], 1)
        self.assertEqual(model["summary"]["action_counts"]["暂不交易"], 1)
        self.assertNotIn("capital", model["summary"])
        self.assertEqual(model["stages"][0]["key"], "sector_screen")
        self.assertEqual(model["stages"][0]["title"], "股票池")
        self.assertEqual(model["stages"][0]["rows"][0]["stock_type"], "科技股")
        self.assertIn("board_name=光学光电子", model["stages"][0]["rows"][0]["stock_type_note"])
        self.assertEqual(model["stages"][1]["key"], "combo")
        self.assertEqual(model["stages"][1]["title"], "宏观粗筛")
        self.assertEqual(model["stages"][2]["key"], "fine")
        self.assertEqual(model["stages"][2]["title"], "技术分析")
        self.assertEqual(model["stages"][3]["key"], "plan")
        self.assertEqual(model["stages"][3]["title"], "操作建议")
        self.assertEqual(model["stages"][0]["rows"][0]["code"], "000725")
        self.assertIn("000725", model["traces"])
        self.assertEqual(model["traces"]["000725"][0]["stage"], "sector_screen")
        self.assertEqual(model["traces"]["000725"][1]["stage"], "combo")
        self.assertEqual(model["traces"]["000725"][2]["stage"], "plan")

    def test_uses_configured_stock_type_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Path(tmpdir) / "stock_type_rules.json"
            config.write_text(
                """
                {
                  "default_type": "其他",
                  "types": [
                    {
                      "name": "AI算力",
                      "enabled": true,
                      "keywords": ["算力", "服务器"],
                      "exclude_keywords": []
                    }
                  ]
                }
                """,
                encoding="utf-8",
            )
            rules = load_stock_type_rules(str(config))

        model = build_dashboard_view_model(
            {
                "sector_screen": pd.DataFrame(
                    [
                        {"code": "000001", "name": "算力样本", "board_name": "AI算力服务器"},
                        {"code": "000002", "name": "普通样本", "board_name": "地产开发"},
                    ]
                )
            },
            {"sector_screen": {}},
            stock_type_rules=rules,
        )

        rows = model["stages"][0]["rows"]
        self.assertEqual(rows[0]["stock_type"], "AI算力")
        self.assertIn("命中关键词：算力", rows[0]["stock_type_note"])
        self.assertEqual(rows[1]["stock_type"], "其他")


if __name__ == "__main__":
    unittest.main()
