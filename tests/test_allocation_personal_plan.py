from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from allocation.personal_plan import build_allocation_plan


class PersonalAllocationPlanTest(unittest.TestCase):
    def test_splits_capital_into_core_satellite_cash_and_target_profit(self) -> None:
        trade_plan = pd.DataFrame()

        result, meta = build_allocation_plan(trade_plan, capital=15000)

        self.assertTrue(result.empty)
        self.assertEqual(meta["capital"], 15000)
        self.assertEqual(meta["target_return"], 0.10)
        self.assertEqual(meta["annual_target_profit"], 1500)
        self.assertEqual(meta["core_etf_budget"], 9000)
        self.assertEqual(meta["satellite_stock_budget"], 3000)
        self.assertEqual(meta["cash_reserve"], 3000)
        self.assertEqual(meta["etf_tranches"], 3)
        self.assertEqual(meta["etf_tranche_amount"], 3000)

    def test_marks_one_lot_as_unaffordable_when_it_exceeds_single_stock_cap(self) -> None:
        trade_plan = pd.DataFrame(
            [
                {
                    "code": "688012",
                    "name": "中微公司",
                    "action": "等待放量确认",
                    "usable_for_plan": True,
                    "latest_close": 471.59,
                    "planned_entry": 473.00,
                    "initial_stop": 449.35,
                    "risk_pct": 0.05,
                    "position_cap": 0.12,
                }
            ]
        )

        result, _ = build_allocation_plan(trade_plan, capital=15000)

        row = result.iloc[0]
        self.assertEqual(row["code"], "688012")
        self.assertEqual(row["lot_cost"], 47159)
        self.assertEqual(row["max_position_amount"], 1800)
        self.assertEqual(row["budget_status"], "一手超过单股仓位上限")
        self.assertEqual(row["portfolio_action"], "只做风向标")

    def test_keeps_budget_friendly_triggered_candidates_actionable(self) -> None:
        trade_plan = pd.DataFrame(
            [
                {
                    "code": "000725",
                    "name": "京东方A",
                    "action": "允许条件买入",
                    "usable_for_plan": True,
                    "latest_close": 4.25,
                    "planned_entry": 4.30,
                    "initial_stop": 4.05,
                    "risk_pct": 0.058,
                    "position_cap": 0.20,
                }
            ]
        )

        result, _ = build_allocation_plan(trade_plan, capital=15000)

        row = result.iloc[0]
        self.assertEqual(row["lot_cost"], 425)
        self.assertEqual(row["budget_status"], "预算内")
        self.assertEqual(row["portfolio_action"], "可条件买入")
        self.assertEqual(row["initial_buy_budget"], 1800)


if __name__ == "__main__":
    unittest.main()
