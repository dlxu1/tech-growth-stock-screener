from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from backtest.operation_backtest import build_operation_backtest_model


class OperationBacktestTest(unittest.TestCase):
    def test_uses_passed_dynamic_thresholds_when_selecting_candidates(self) -> None:
        plans = pd.DataFrame(
            [
                {
                    "code": "000004",
                    "name": "四号",
                    "action": "等待放量确认",
                    "primary_strategy": "volume_confirm_buy",
                    "coarse_score": 76.0,
                    "technical_score": 60.0,
                    "planned_entry": 10.0,
                    "initial_stop": 9.5,
                    "volume_confirm_amount": 1000.0,
                    "usable_for_plan": True,
                }
            ]
        )
        quotes = pd.DataFrame(
            [
                {"code": "000004", "trade_date": "2026-07-02", "open": 9.8, "high": 10.1, "low": 9.7, "close": 10.0, "amount": 2000},
            ]
        )

        model = build_operation_backtest_model(
            plans,
            quotes,
            signal_date="2026-07-01",
            macro_threshold=75.0,
            tech_threshold=52.0,
        )

        self.assertEqual(model["summary"]["candidate_count"], 1)
        self.assertEqual(model["summary"]["row_count"], 1)

    def test_buys_executable_high_potential_good_timing_plan_and_sells_at_five_percent_profit(self) -> None:
        plans = pd.DataFrame(
            [
                {
                    "code": "000001",
                    "name": "一号",
                    "action": "允许条件买入",
                    "primary_strategy": "breakout_buy",
                    "coarse_score": 88.0,
                    "technical_score": 82.0,
                    "planned_entry": 10.0,
                    "initial_stop": 9.5,
                    "volume_confirm_amount": 1000.0,
                    "usable_for_plan": True,
                }
            ]
        )
        quotes = pd.DataFrame(
            [
                {"code": "000001", "trade_date": "2026-07-02", "open": 9.8, "high": 10.1, "low": 9.7, "close": 10.0, "amount": 2000},
                {"code": "000001", "trade_date": "2026-07-03", "open": 10.1, "high": 10.4, "low": 10.0, "close": 10.3, "amount": 2000},
                {"code": "000001", "trade_date": "2026-07-06", "open": 10.4, "high": 10.6, "low": 10.2, "close": 10.5, "amount": 2000},
            ]
        )

        model = build_operation_backtest_model(plans, quotes, signal_date="2026-07-01", profit_target_pct=0.05)

        row = model["rows"][0]
        self.assertEqual(row["status"], "take_profit")
        self.assertEqual(row["buy_date"], "2026-07-02")
        self.assertEqual(row["sell_date"], "2026-07-06")
        self.assertAlmostEqual(row["return_pct"], 0.05)
        self.assertEqual(model["summary"]["trade_count"], 1)
        self.assertEqual(model["summary"]["take_profit_count"], 1)
        self.assertAlmostEqual(model["summary"]["realized_avg_return_pct"], 0.05)

    def test_keeps_untriggered_plan_out_of_trade_return_summary(self) -> None:
        plans = pd.DataFrame(
            [
                {
                    "code": "000002",
                    "name": "二号",
                    "action": "等待回踩买入",
                    "primary_strategy": "pullback_ma_buy",
                    "coarse_score": 90.0,
                    "technical_score": 80.0,
                    "planned_entry": 10.0,
                    "initial_stop": 9.5,
                    "volume_confirm_amount": 1000.0,
                    "usable_for_plan": True,
                }
            ]
        )
        quotes = pd.DataFrame(
            [
                {"code": "000002", "trade_date": "2026-07-02", "open": 11.0, "high": 11.2, "low": 10.8, "close": 11.1, "amount": 2000},
                {"code": "000002", "trade_date": "2026-07-03", "open": 11.1, "high": 11.3, "low": 10.9, "close": 11.2, "amount": 2000},
            ]
        )

        model = build_operation_backtest_model(plans, quotes, signal_date="2026-07-01", profit_target_pct=0.05)

        self.assertEqual(model["rows"][0]["status"], "not_triggered")
        self.assertEqual(model["summary"]["trade_count"], 0)
        self.assertEqual(model["summary"]["untriggered_count"], 1)
        self.assertIsNone(model["summary"]["realized_avg_return_pct"])

    def test_does_not_sell_on_buy_date_because_a_share_trades_are_t_plus_one(self) -> None:
        plans = pd.DataFrame(
            [
                {
                    "code": "000003",
                    "name": "三号",
                    "action": "等待回踩买入",
                    "primary_strategy": "pullback_ma_buy",
                    "coarse_score": 90.0,
                    "technical_score": 80.0,
                    "planned_entry": 10.0,
                    "initial_stop": 9.5,
                    "usable_for_plan": True,
                }
            ]
        )
        quotes = pd.DataFrame(
            [
                {"code": "000003", "trade_date": "2026-06-12", "open": 10.1, "high": 10.6, "low": 9.8, "close": 10.2, "amount": 2000},
                {"code": "000003", "trade_date": "2026-06-15", "open": 10.2, "high": 10.4, "low": 9.8, "close": 10.3, "amount": 2000},
            ]
        )

        model = build_operation_backtest_model(plans, quotes, signal_date="2026-06-11", profit_target_pct=0.05)

        row = model["rows"][0]
        self.assertEqual(row["buy_date"], "2026-06-12")
        self.assertEqual(row["sell_date"], "2026-06-15")
        self.assertEqual(row["status"], "hold_to_end")
        self.assertAlmostEqual(row["return_pct"], 0.03)
        self.assertEqual(model["summary"]["take_profit_count"], 0)
        self.assertEqual(model["summary"]["hold_count"], 1)


if __name__ == "__main__":
    unittest.main()
