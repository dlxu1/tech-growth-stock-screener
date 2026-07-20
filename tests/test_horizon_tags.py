from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dashboard.horizon_tags import annotate_horizon


class HorizonTagsTest(unittest.TestCase):
    def test_marks_long_and_medium_when_quality_and_matrix_evidence_are_present(self) -> None:
        row = annotate_horizon(
            {
                "combo_score": 86,
                "technical_score": 78,
                "quality_score": 82,
                "risk_control_score": 71,
                "growth_score": 66,
                "matched_strategies": "高 ROE + 合理估值、高毛利率 + 营收增长",
            }
        )

        self.assertEqual(row["horizon_tags"], ["长线", "中线"])
        self.assertEqual(row["primary_horizon"], "中线")
        self.assertIn("基本面质量", row["horizon_reason"])
        self.assertIn("宏观潜力与技术时机共振", row["horizon_reason"])

    def test_marks_short_only_when_operation_plan_is_executable(self) -> None:
        row = annotate_horizon(
            {
                "combo_score": 83,
                "technical_score": 80,
                "quality_score": 62,
                "risk_control_score": 60,
                "growth_score": 58,
                "usable_for_plan": True,
                "primary_strategy": "breakout_buy",
                "planned_entry": 10.5,
                "initial_stop": 9.9,
                "risk_pct": 0.057,
            }
        )

        self.assertEqual(row["horizon_tags"], ["中线", "短线"])
        self.assertEqual(row["primary_horizon"], "短线")
        self.assertIn("可执行", row["horizon_reason"])

    def test_missing_scores_do_not_force_a_tag(self) -> None:
        row = annotate_horizon({"code": "000001", "name": "样本"})

        self.assertEqual(row["horizon_tags"], [])
        self.assertIsNone(row["primary_horizon"])
        self.assertEqual(row["horizon_data_note"], "证据不足，需人工复核")


if __name__ == "__main__":
    unittest.main()
