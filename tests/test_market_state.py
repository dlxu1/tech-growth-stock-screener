from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dashboard import market_state


class MarketStateTest(unittest.TestCase):
    def test_detect_note_uses_sample_not_index_label(self) -> None:
        dates = pd.date_range("2026-05-01", periods=35, freq="D")
        quotes = pd.DataFrame(
            [
                {
                    "code": "000001",
                    "trade_date": day.strftime("%Y-%m-%d"),
                    "close": 10 + idx * 0.1,
                }
                for idx, day in enumerate(dates)
            ]
        )

        with patch("dashboard.market_state.read_quotes_daily", return_value=quotes):
            state = market_state.detect(["000001"])

        self.assertIn("样本MA30", state.note)
        self.assertNotIn("指数MA30", state.note)


if __name__ == "__main__":
    unittest.main()
