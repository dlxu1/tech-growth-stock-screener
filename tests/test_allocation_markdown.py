from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reports.allocation_markdown import render_allocation_plan


class AllocationMarkdownTest(unittest.TestCase):
    def test_renders_capital_buckets_and_candidate_actions(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "code": "000725",
                    "name": "京东方A",
                    "portfolio_action": "可条件买入",
                    "source_action": "允许条件买入",
                    "budget_status": "预算内",
                    "latest_close": 4.25,
                    "lot_cost": 425,
                    "initial_buy_budget": 1800,
                    "max_position_amount": 3000,
                    "planned_entry": 4.30,
                    "initial_stop": 4.05,
                    "risk_pct": 0.058,
                    "position_cap": 0.20,
                    "allocation_note": "一手成本约 425 元；单股仓位上限约 3000 元。",
                }
            ]
        )
        meta = {
            "capital": 15000,
            "target_return": 0.10,
            "annual_target_profit": 1500,
            "core_etf_budget": 9000,
            "satellite_stock_budget": 3000,
            "cash_reserve": 3000,
            "etf_tranches": 3,
            "etf_tranche_amount": 3000,
        }

        markdown = render_allocation_plan(df, meta)

        self.assertIn("# 个人科技股配置计划", markdown)
        self.assertIn("总资金：15000 元", markdown)
        self.assertIn("科技 ETF 核心仓：9000 元，分 3 笔，每笔约 3000 元", markdown)
        self.assertIn("京东方A（000725）", markdown)
        self.assertIn("组合动作：可条件买入", markdown)
        self.assertIn("一手成本：425 元", markdown)


if __name__ == "__main__":
    unittest.main()
