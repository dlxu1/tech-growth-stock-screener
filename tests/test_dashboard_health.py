from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dashboard.health import audit_dashboard_model, render_health_markdown


class DashboardHealthTest(unittest.TestCase):
    def test_audit_flags_missing_quotes_and_serial_breaks(self) -> None:
        model = {
            "summary": {"stage_counts": {"sector_screen": 2, "combo": 2, "fine": 2, "plan": 2}},
            "stages": [
                {
                    "key": "sector_screen",
                    "rows": [
                        {"code": "000001", "amount_20d": 1, "return_60d": 0.1, "max_drawdown_252d": -0.1},
                        {"code": "000002", "amount_20d": None, "return_60d": None, "max_drawdown_252d": None},
                    ],
                },
                {
                    "key": "combo",
                    "rows": [
                        {"code": "000001", "combo_score": 88},
                        {"code": "000003", "combo_score": None},
                    ],
                },
                {
                    "key": "fine",
                    "rows": [
                        {"code": "000001", "technical_score": 70, "latest_trade_date": "2026-07-09"},
                        {"code": "000003", "technical_score": -1, "latest_trade_date": None},
                    ],
                },
                {
                    "key": "plan",
                    "rows": [
                        {"code": "000001", "data_status": "complete", "usable_for_plan": True, "planned_entry": 10, "initial_stop": 9},
                        {"code": "000004", "data_status": "missing_quotes", "usable_for_plan": False},
                    ],
                },
            ],
        }

        audit = audit_dashboard_model(model, expected_latest_trade_date="2026-07-10")

        self.assertLess(audit["health_score"], 100)
        self.assertEqual(audit["stage_counts"]["plan"], 2)
        self.assertEqual(audit["coverage"]["sector_quote_metric_missing"], 1)
        self.assertEqual(audit["coverage"]["plan_missing_quotes"], 1)
        self.assertEqual(audit["coverage"]["plan_usable"], 1)
        self.assertEqual(audit["freshness"]["latest_trade_date"], "2026-07-09")
        self.assertEqual(audit["freshness"]["lag_days"], 1)
        self.assertIn("000003", audit["serial"]["combo_not_in_sector"])
        self.assertIn("000004", audit["serial"]["plan_not_in_fine"])
        self.assertEqual(audit["coverage"]["combo_score_missing"], 1)
        self.assertIn("宏观粗筛分缺失：1/2", audit["issues"])
        self.assertTrue(audit["issues"])

    def test_render_health_markdown_is_readable(self) -> None:
        audit = {
            "health_score": 72,
            "freshness": {"latest_trade_date": "2026-07-09", "expected_latest_trade_date": "2026-07-10", "lag_days": 1},
            "coverage": {
                "sector_rows": 100,
                "sector_quote_metric_missing": 46,
                "plan_rows": 20,
                "plan_usable": 4,
                "plan_missing_quotes": 8,
            },
            "serial": {"ok": True},
            "issues": ["操作建议缺日线行情：8/20"],
            "missing_quotes": [{"code": "688110", "name": "东芯股份"}],
        }

        markdown = render_health_markdown(audit)

        self.assertIn("数据健康度：72/100", markdown)
        self.assertIn("最新行情日：2026-07-09", markdown)
        self.assertIn("操作建议缺日线行情：8/20", markdown)
        self.assertIn("东芯股份", markdown)


if __name__ == "__main__":
    unittest.main()
