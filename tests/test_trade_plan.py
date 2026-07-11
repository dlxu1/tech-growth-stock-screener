from __future__ import annotations

import math
import sys
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from plan.trade_plan import _plan_one


def _args() -> Namespace:
    return Namespace(
        breakout_buffer=0.003,
        volume_multiplier=1.5,
        stop_pct=0.05,
        max_gap_up=0.03,
        atr_stop_multiplier=2.0,
        move_stop_profit=0.05,
        trailing_profit=0.10,
        trailing_drawdown=0.06,
        max_position=0.25,
    )


def _quotes(code: str = "300308") -> pd.DataFrame:
    rows = []
    for day in range(1, 26):
        close = 100 + day
        rows.append(
            {
                "code": code,
                "trade_date": f"2026-06-{day:02d}",
                "open": close - 1,
                "high": close + 2,
                "low": close - 3,
                "close": close,
                "volume": 1000000 + day,
                "amount": 100000000 + day,
            }
        )
    return pd.DataFrame(rows)


class TradePlanTest(unittest.TestCase):
    def test_no_trade_with_quotes_still_gets_observation_price_plan(self) -> None:
        row = SimpleNamespace(
            code="300308",
            name="中际旭创",
            board_name="通信设备",
            technical_score=27.0,
            technical_reasons="趋势转弱",
            latest_trade_date="2026-06-25",
        )

        plan = _plan_one(row, _quotes(), _args())

        self.assertEqual(plan["action"], "暂不交易")
        self.assertEqual(plan["primary_strategy"], "no_trade")
        self.assertFalse(plan["usable_for_plan"])
        self.assertFalse(math.isnan(plan["planned_entry"]))
        self.assertFalse(math.isnan(plan["initial_stop"]))
        self.assertFalse(math.isnan(plan["risk_pct"]))
        self.assertIn("观察参考价", plan["plan_note"])
        self.assertIn("不构成买入指令", plan["plan_note"])

    def test_missing_quotes_keep_price_plan_empty(self) -> None:
        row = SimpleNamespace(
            code="688110",
            name="东芯股份",
            board_name="半导体",
            technical_score=0.0,
            technical_reasons="缺少日线数据",
            latest_trade_date=None,
        )

        plan = _plan_one(row, pd.DataFrame(), _args())

        self.assertEqual(plan["primary_strategy"], "no_data")
        self.assertFalse(plan["usable_for_plan"])
        self.assertNotIn("planned_entry", plan)
        self.assertIn("quotes_daily", plan["missing_data_reason"])


if __name__ == "__main__":
    unittest.main()
