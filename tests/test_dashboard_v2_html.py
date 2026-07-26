import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reports.dashboard_v2_html import _build_mainline_objects, render_dashboard_v2_html


class DashboardV2HtmlTest(unittest.TestCase):
    def sample_model(self) -> dict:
        return {
            "summary": {
                "as_of_date": "2026-07-10",
                "strategy_title": "潜力股组合评分",
                "weight_version": "震荡防御版",
                "health": {
                    "health_score": 88,
                    "freshness": {"latest_trade_date": "2026-07-10"},
                },
            },
            "stages": [
                {
                    "key": "sector_screen",
                    "title": "股票池",
                    "rows": [
                        {
                            "code": "688981",
                            "name": "中芯国际",
                            "board_name": "半导体",
                            "market_cap": 500000000000,
                            "revenue_yoy": 12.0,
                            "profit_yoy": 8.0,
                            "amount_20d": 1200000000,
                            "return_60d": 9.0,
                            "max_drawdown_252d": -12.0,
                        },
                        {
                            "code": "002371",
                            "name": "北方华创",
                            "board_name": "半导体",
                            "market_cap": 200000000000,
                            "revenue_yoy": 20.0,
                            "profit_yoy": 18.0,
                            "amount_20d": 800000000,
                            "return_60d": 7.0,
                            "max_drawdown_252d": -16.0,
                        },
                        {
                            "code": "000001",
                            "name": "平安银行",
                            "board_name": "银行",
                            "market_cap": 300000000000,
                            "revenue_yoy": 2.0,
                            "profit_yoy": 1.0,
                            "amount_20d": 400000000,
                            "return_60d": -2.0,
                            "max_drawdown_252d": -20.0,
                        },
                    ],
                },
                {
                    "key": "fine",
                    "title": "技术分析",
                    "rows": [
                        {
                            "code": "688981",
                            "technical_score": 78.5,
                            "technical_reasons": "趋势强，量能改善",
                        }
                    ],
                },
                {
                    "key": "plan",
                    "title": "操作建议",
                    "rows": [
                        {
                            "code": "688981",
                            "name": "中芯国际",
                            "action": "等待回踩买入",
                            "planned_entry": 76.5,
                            "initial_stop": 72.8,
                            "primary_horizon": "中线",
                            "horizon_reason": "主线龙头，技术确认接近触发。",
                            "horizon_data_note": "等待回踩确认。",
                        }
                    ],
                },
            ],
        }

    def test_renders_industry_thesis_flow(self) -> None:
        html = render_dashboard_v2_html(self.sample_model())

        self.assertIn("<!doctype html>", html)
        self.assertIn("dashboardv2 - 行业主线选股", html)
        self.assertIn("行业主线", html)
        self.assertNotIn("dashboard v1", html)
        self.assertNotIn("链路", html)
        self.assertIn("主线股票池", html)
        self.assertIn("龙头收敛", html)
        self.assertIn("技术确认", html)
        self.assertIn("每日复盘", html)
        self.assertIn("半导体", html)
        self.assertIn("中芯国际", html)
        self.assertIn("等待回踩买入", html)
        self.assertIn("缓存样本涨幅", html)
        self.assertIn("不编造上涨原因", html)
        self.assertIn('id="dashboardV2Data"', html)

    def test_mainline_objects_limit_daily_review_to_top_leaders(self) -> None:
        mainlines = _build_mainline_objects(self.sample_model())

        self.assertGreaterEqual(len(mainlines), 2)
        self.assertEqual(mainlines[0]["board_name"], "半导体")
        self.assertLessEqual(len(mainlines[0]["daily_review"]), 3)
        self.assertEqual(mainlines[0]["leaders"][0]["code"], "688981")

    def test_renders_conservative_empty_state(self) -> None:
        html = render_dashboard_v2_html({"summary": {}, "stages": []})

        self.assertIn("暂无可展示行业主线", html)
        self.assertIn("行业指数、资金流或新闻催化缺失", html)


if __name__ == "__main__":
    unittest.main()
