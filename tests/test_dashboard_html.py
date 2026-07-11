from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reports.dashboard_html import render_dashboard_html


class DashboardHtmlTest(unittest.TestCase):
    def test_renders_interactive_dashboard_shell(self) -> None:
        model = {
            "summary": {
                "stage_counts": {"sector_screen": 2, "allocation": 1},
                "action_counts": {"只做风向标": 1},
                "capital": 15000,
                "core_etf_budget": 9000,
                "satellite_stock_budget": 3000,
                "cash_reserve": 3000,
            },
            "stages": [
                {
                    "key": "sector_screen",
                    "title": "板块筛选",
                    "row_count": 1,
                    "columns": [
                        "code",
                        "name",
                        "board_name",
                        "market_cap",
                        "revenue_yoy",
                        "profit_yoy",
                        "amount_20d",
                        "return_60d",
                        "max_drawdown_252d",
                        "match_reason",
                        "risk_flags",
                        "data_note",
                    ],
                    "rows": [
                        {
                            "code": "688981",
                            "name": "中芯国际",
                            "board_name": "半导体",
                            "market_cap": 500000000000,
                            "revenue_yoy": 12.345,
                            "profit_yoy": -4.321,
                            "amount_20d": 1234567890,
                            "return_60d": 8.765,
                            "max_drawdown_252d": -18.9,
                            "match_reason": "board_name 命中：半导体",
                            "risk_flags": "净利润同比为负",
                            "data_note": "字段完整：市值、营收同比、净利同比、20日成交额、60日涨幅、年内最大回撤均有可用数据。",
                        }
                    ],
                },
                {
                    "key": "combo",
                    "title": "宏观粗筛",
                    "row_count": 1,
                    "columns": [
                        "code",
                        "name",
                        "market_cap",
                        "combo_score",
                        "overlap_score",
                        "quality_score",
                        "growth_score",
                        "risk_control_score",
                        "liquidity_score",
                        "momentum_score",
                        "strategy_hits",
                        "matched_strategies",
                    ],
                    "rows": [
                        {
                            "code": "000725",
                            "name": "京东方A",
                            "market_cap": 10045000000,
                            "combo_score": 88.6,
                            "overlap_score": 92.0,
                            "quality_score": 81.5,
                            "growth_score": 76.2,
                            "risk_control_score": 70.0,
                            "liquidity_score": 98.0,
                            "momentum_score": 66.0,
                            "strategy_hits": 3,
                            "matched_strategies": "多策略共振",
                        }
                    ],
                },
                {
                    "key": "fine",
                    "title": "技术细筛",
                    "row_count": 1,
                    "columns": [
                        "code",
                        "name",
                        "board_name",
                        "coarse_strategies",
                        "coarse_score",
                        "latest_trade_date",
                        "close",
                        "change_pct",
                        "return_20d",
                        "return_60d",
                        "amount_ratio",
                        "ma5",
                        "ma10",
                        "ma20",
                        "max_drawdown_20d",
                        "technical_score",
                        "technical_reasons",
                    ],
                    "rows": [
                        {
                            "code": "000725",
                            "name": "京东方A",
                            "board_name": "光学光电子",
                            "coarse_strategies": "多策略共振",
                            "technical_score": 77.5,
                            "coarse_score": 0.86,
                            "latest_trade_date": "2026-07-10",
                            "close": 4.236,
                            "change_pct": 0.0123,
                            "return_20d": 0.08,
                            "return_60d": 0.1567,
                            "amount_ratio": 1.234,
                            "ma5": 4.111,
                            "ma10": 4.222,
                            "ma20": 4.333,
                            "max_drawdown_20d": -0.0456,
                            "technical_reasons": "趋势强",
                        }
                    ],
                }
            ],
            "traces": {
                "000725": [{"stage": "sector_screen", "title": "板块筛选", "label": "京东方A", "row": {}}]
            },
        }

        html = render_dashboard_html(model)

        self.assertIn("<!doctype html>", html)
        self.assertIn("选股流程交互仪表盘", html)
        self.assertIn('id="globalSearch"', html)
        self.assertIn("宏观粗筛", html)
        self.assertIn("宏观粗筛分", html)
        self.assertIn("多策略共振分", html)
        self.assertIn("质量分", html)
        self.assertIn("成长分", html)
        self.assertIn("风控分", html)
        self.assertIn("流动性分", html)
        self.assertIn("动量分", html)
        self.assertIn("技术分", html)
        self.assertIn("粗筛分", html)
        self.assertIn("策略命中", html)
        self.assertIn("strategy_summary", html)
        self.assertIn("strategySummary", html)
        self.assertIn("formatCell", html)
        self.assertIn("formatNumber", html)
        self.assertIn("formatMarketCap", html)
        self.assertIn("formatPercent", html)
        self.assertIn("formatAmountYi", html)
        self.assertIn("formatFineNumber", html)
        self.assertIn("formatFinePercent", html)
        self.assertIn("cellTitle", html)
        self.assertIn("/ 100000000", html)
        self.assertIn("亿", html)
        self.assertIn(
            'const comboVisibleColumns = ["code","name","market_cap","combo_score","growth_score","quality_score","risk_control_score","strategy_summary"];',
            html,
        )
        self.assertIn(
            'const sectorVisibleColumns = ["code","name","board_name","market_cap","revenue_yoy","profit_yoy","amount_20d","return_60d","max_drawdown_252d","risk_flags","data_note"];',
            html,
        )
        self.assertIn(
            'const fineHiddenColumns = ["coarse_strategies"];',
            html,
        )
        self.assertNotIn(
            'const fineHiddenColumns = [];',
            html,
        )
        self.assertNotIn('"match_reason","risk_flags","data_note"];', html)
        self.assertIn("score-info", html)
        self.assertIn('id="scoreTooltip"', html)
        self.assertIn("data-score-help", html)
        self.assertIn("宏观粗筛分 = 多策略共振分 × 35%", html)
        self.assertIn("技术分 = 趋势分 × 30", html)
        self.assertIn("京东方A", html)
        self.assertIn("window.DASHBOARD_DATA", html)


if __name__ == "__main__":
    unittest.main()
