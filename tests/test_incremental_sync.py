from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from data.db import connect, write_quotes_daily, write_source_table
from data.sources import load_financial_report, sync_daily_prices, sync_dataset


class IncrementalSyncTest(unittest.TestCase):
    def test_sync_dataset_defaults_daily_prices_to_incremental(self) -> None:
        with patch("data.sources.sync_daily_prices", return_value={"dataset": "daily_prices"}) as mocked:
            sync_dataset(
                "daily_prices",
                report_date="auto",
                refresh=False,
                no_proxy=True,
                source="efinance",
                codes=["000001"],
                start="2026-07-14",
                end="2026-07-16",
            )

        self.assertEqual(mocked.call_args.args[-1], True)

    def test_daily_prices_skip_existing_fetches_only_missing_tail(self) -> None:
        old_db = os.environ.get("TECH_GROWTH_DB")
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["TECH_GROWTH_DB"] = str(Path(tmpdir) / "stock_data.sqlite")
            conn = connect()
            try:
                write_quotes_daily(
                    conn,
                    pd.DataFrame(
                        [
                            {
                                "code": "000001",
                                "trade_date": "2026-07-14",
                                "open": 10,
                                "high": 11,
                                "low": 9,
                                "close": 10,
                                "volume": 1,
                                "amount": 100,
                            },
                            {
                                "code": "000001",
                                "trade_date": "2026-07-15",
                                "open": 10,
                                "high": 11,
                                "low": 9,
                                "close": 10,
                                "volume": 1,
                                "amount": 100,
                            },
                        ]
                    ),
                    "unit-test",
                )
            finally:
                conn.close()

            calls: list[tuple[str, str]] = []

            def fake_fetch(_code: str, start: str, end: str, _adjust: str, _no_proxy: bool) -> pd.DataFrame:
                calls.append((start, end))
                return pd.DataFrame(
                    [
                        {
                            "日期": "2026-07-16",
                            "开盘": 10,
                            "最高": 11,
                            "最低": 9,
                            "收盘": 10.5,
                            "成交量": 2,
                            "成交额": 200,
                        }
                    ]
                )

            with patch("data.sources.fetch_daily_prices_efinance", side_effect=fake_fetch):
                result = sync_daily_prices(
                    ["000001"],
                    "2026-07-14",
                    "2026-07-16",
                    refresh=False,
                    no_proxy=True,
                    source="efinance",
                    adjust="qfq",
                    skip_existing=True,
                )

        if old_db is None:
            os.environ.pop("TECH_GROWTH_DB", None)
        else:
            os.environ["TECH_GROWTH_DB"] = old_db

        self.assertEqual(calls, [("2026-07-16", "2026-07-16")])
        self.assertEqual(result["rows"], 1)
        self.assertEqual(result["details"][0]["fetch_start"], "2026-07-16")
        self.assertEqual(result["details"][0]["incremental"], True)

    def test_daily_prices_refresh_forces_full_requested_range(self) -> None:
        old_db = os.environ.get("TECH_GROWTH_DB")
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["TECH_GROWTH_DB"] = str(Path(tmpdir) / "stock_data.sqlite")
            conn = connect()
            try:
                write_quotes_daily(
                    conn,
                    pd.DataFrame(
                        [
                            {
                                "code": "000001",
                                "trade_date": "2026-07-14",
                                "open": 10,
                                "high": 11,
                                "low": 9,
                                "close": 10,
                                "volume": 1,
                                "amount": 100,
                            },
                        ]
                    ),
                    "unit-test",
                )
            finally:
                conn.close()

            calls: list[tuple[str, str]] = []

            def fake_fetch(_code: str, start: str, end: str, _adjust: str, _no_proxy: bool) -> pd.DataFrame:
                calls.append((start, end))
                return pd.DataFrame(
                    [
                        {
                            "日期": "2026-07-14",
                            "开盘": 10,
                            "最高": 11,
                            "最低": 9,
                            "收盘": 10,
                            "成交量": 1,
                            "成交额": 100,
                        },
                        {
                            "日期": "2026-07-15",
                            "开盘": 10,
                            "最高": 11,
                            "最低": 9,
                            "收盘": 10.5,
                            "成交量": 2,
                            "成交额": 200,
                        },
                    ]
                )

            with patch("data.sources.fetch_daily_prices_efinance", side_effect=fake_fetch):
                result = sync_daily_prices(
                    ["000001"],
                    "2026-07-14",
                    "2026-07-15",
                    refresh=True,
                    no_proxy=True,
                    source="efinance",
                    adjust="qfq",
                )

        if old_db is None:
            os.environ.pop("TECH_GROWTH_DB", None)
        else:
            os.environ["TECH_GROWTH_DB"] = old_db

        self.assertEqual(calls, [("2026-07-14", "2026-07-15")])
        self.assertEqual(result["rows"], 2)

    def test_auto_financial_report_uses_latest_complete_cached_report(self) -> None:
        old_db = os.environ.get("TECH_GROWTH_DB")
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["TECH_GROWTH_DB"] = str(Path(tmpdir) / "stock_data.sqlite")
            conn = connect()
            try:
                write_source_table(
                    conn,
                    "stock_yjbb_20260630",
                    "unit-test",
                    pd.DataFrame(
                        [
                            {
                                "股票代码": "000001",
                                "股票简称": "平安银行",
                                "所处行业": "银行",
                                "营业总收入-同比增长": 1.0,
                                "净利润-同比增长": 2.0,
                            }
                        ]
                    ),
                )
                write_source_table(
                    conn,
                    "stock_yjbb_20260331",
                    "unit-test",
                    pd.DataFrame(
                        [
                            {
                                "股票代码": f"{idx:06d}",
                                "股票简称": f"样本{idx}",
                                "所处行业": "样本行业",
                                "营业总收入-同比增长": 1.0,
                                "净利润-同比增长": 2.0,
                            }
                            for idx in range(1, 5)
                        ]
                    ),
                )
            finally:
                conn.close()

            with patch("data.sources.FINANCIAL_AUTO_MIN_ROWS", 3):
                df, report_date, source = load_financial_report("auto", False, "cache", True)

        if old_db is None:
            os.environ.pop("TECH_GROWTH_DB", None)
        else:
            os.environ["TECH_GROWTH_DB"] = old_db

        self.assertEqual(report_date, "20260331")
        self.assertEqual(source, "db:stock_yjbb_20260331")
        self.assertEqual(len(df), 4)


if __name__ == "__main__":
    unittest.main()
