from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from data.db import connect, write_index_constituents, write_quotes_daily
from infra.cache import read_index_constituents, read_price_metrics, read_quotes_daily


class CacheAsOfTest(unittest.TestCase):
    def test_read_quotes_daily_filters_rows_after_as_of_date(self) -> None:
        old_db = os.environ.get("TECH_GROWTH_DB")
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["TECH_GROWTH_DB"] = str(Path(tmpdir) / "stock_data.sqlite")
            conn = connect()
            try:
                write_quotes_daily(
                    conn,
                    pd.DataFrame(
                        [
                            {"code": "000001", "trade_date": "2026-06-01", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1, "amount": 100},
                            {"code": "000001", "trade_date": "2026-06-02", "open": 11, "high": 12, "low": 10, "close": 11, "volume": 1, "amount": 200},
                        ]
                    ),
                    "unit-test",
                )
            finally:
                conn.close()

            prices = read_quotes_daily(["1"], ["code", "trade_date", "close"], as_of_date="2026-06-01")
            metrics = read_price_metrics(["000001"], as_of_date="2026-06-01")

        if old_db is None:
            os.environ.pop("TECH_GROWTH_DB", None)
        else:
            os.environ["TECH_GROWTH_DB"] = old_db

        self.assertEqual(prices["trade_date"].tolist(), ["2026-06-01"])
        self.assertEqual(prices["close"].tolist(), [10.0])
        self.assertEqual(metrics["amount_20d"].tolist(), [100.0])

    def test_read_index_constituents_falls_back_to_latest_cached_snapshot(self) -> None:
        old_db = os.environ.get("TECH_GROWTH_DB")
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["TECH_GROWTH_DB"] = str(Path(tmpdir) / "stock_data.sqlite")
            conn = connect()
            try:
                write_index_constituents(
                    conn,
                    pd.DataFrame(
                        [
                            {
                                "index_symbol": "000300",
                                "index_name": "沪深300",
                                "constituent_date": "2026-07-09",
                                "code": "000001",
                                "name": "平安银行",
                            }
                        ]
                    ),
                    "unit-test",
                )
            finally:
                conn.close()

            members = read_index_constituents("000300", as_of_date="2026-06-30")

        if old_db is None:
            os.environ.pop("TECH_GROWTH_DB", None)
        else:
            os.environ["TECH_GROWTH_DB"] = old_db

        self.assertEqual(members["code"].tolist(), ["000001"])
        self.assertEqual(members["constituent_date"].tolist(), ["2026-07-09"])


if __name__ == "__main__":
    unittest.main()
