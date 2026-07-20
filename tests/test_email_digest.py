import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reports.email_digest import build_daily_email_digest


def _stage(key, rows):
    return {"key": key, "title": key, "rows": rows, "row_count": len(rows)}


class EmailDigestTest(unittest.TestCase):
    def test_renders_health_and_top_ten_high_good_plan_rows(self) -> None:
        combo_rows = []
        fine_rows = []
        plan_rows = []
        for idx in range(12):
            code = f"600{idx:03d}"
            combo_score = 95 - idx
            technical_score = 90 - idx
            combo_rows.append({"code": code, "name": f"第一象限{idx}", "combo_score": combo_score})
            fine_rows.append({"code": code, "name": f"第一象限{idx}", "technical_score": technical_score})
            plan_rows.append(
                {
                    "code": code,
                    "name": f"第一象限{idx}",
                    "technical_score": technical_score,
                    "action": "条件买入",
                    "latest_close": 10 + idx,
                    "planned_entry": 10.5 + idx,
                    "initial_stop": 9.8 + idx,
                    "risk_pct": 0.035,
                    "take_profit_1r": 11 + idx,
                    "take_profit_2r": 12 + idx,
                    "plan_note": "等待明日触发条件。",
                    "attention_score": combo_score * 0.65 + technical_score * 0.35,
                    "usable_for_plan": True,
                    "horizon_tags": ["中线", "短线"],
                    "primary_horizon": "短线",
                    "horizon_reason": "宏观潜力与技术时机共振，且已有可执行操作计划。",
                    "horizon_data_note": "",
                }
            )
        combo_rows.append({"code": "000001", "name": "非第一象限", "combo_score": 70})
        fine_rows.append({"code": "000001", "name": "非第一象限", "technical_score": 96})
        plan_rows.append({"code": "000001", "name": "非第一象限", "action": "观察", "attention_score": 79.1})
        model = {
            "summary": {
                "as_of_date": "2026-07-17",
                "adaptive_thresholds": {"macro_potential_threshold": 80, "technical_timing_threshold": 75},
                "health": {
                    "health_score": 96,
                    "freshness": {"latest_trade_date": "2026-07-17", "lag_days": 0},
                    "coverage": {
                        "sector_rows": 100,
                        "sector_quote_metric_missing": 0,
                        "combo_rows": 100,
                        "combo_score_missing": 0,
                        "plan_rows": 100,
                        "plan_usable": 18,
                        "plan_missing_quotes": 1,
                    },
                    "serial": {"ok": True},
                    "issues": ["操作建议缺日线行情：1/100"],
                },
            },
            "stages": [_stage("combo", combo_rows), _stage("fine", fine_rows), _stage("plan", plan_rows)],
        }

        digest = build_daily_email_digest(model, max_candidates=10)

        self.assertEqual("股票数据更新日报 - 2026-07-17", digest.subject)
        self.assertIn("数据健康度：96/100", digest.body)
        self.assertIn("最新行情日：2026-07-17", digest.body)
        self.assertIn("阶段串行关系：通过", digest.body)
        self.assertIn("主要问题：", digest.body)
        self.assertIn("- 操作建议缺日线行情：1/100", digest.body)
        self.assertIn("1. 600000 第一象限0", digest.body)
        self.assertIn("10. 600009 第一象限9", digest.body)
        self.assertIn("操作建议：条件买入", digest.body)
        self.assertIn("计划入场：10.50", digest.body)
        self.assertIn("风险比例：3.50%", digest.body)
        self.assertIn("适合周期：中线 / 短线", digest.body)
        self.assertIn("优先关注：短线", digest.body)
        self.assertIn("周期说明：宏观潜力与技术时机共振，且已有可执行操作计划。", digest.body)
        self.assertNotIn("600010 第一象限10", digest.body)
        self.assertNotIn("000001 非第一象限", digest.body)
        self.assertNotIn("预算", digest.body)
        self.assertEqual(10, len(digest.payload["candidates"]))
        self.assertEqual(12, digest.payload["candidate_total"])
        self.assertEqual(["中线", "短线"], digest.payload["candidates"][0]["horizon_tags"])
        self.assertEqual("短线", digest.payload["candidates"][0]["primary_horizon"])

    def test_renders_empty_candidate_message(self) -> None:
        model = {
            "summary": {
                "as_of_date": "2026-07-17",
                "health": {"health_score": 100, "freshness": {"latest_trade_date": "2026-07-17"}, "coverage": {}, "serial": {"ok": True}},
            },
            "stages": [
                _stage("combo", [{"code": "000001", "name": "平安银行", "combo_score": 60}]),
                _stage("fine", [{"code": "000001", "name": "平安银行", "technical_score": 60}]),
                _stage("plan", [{"code": "000001", "name": "平安银行", "action": "观察"}]),
            ],
        }

        digest = build_daily_email_digest(model, max_candidates=10)

        self.assertIn("暂无符合条件股票。", digest.body)
        self.assertEqual(0, digest.payload["candidate_total"])


if __name__ == "__main__":
    unittest.main()
