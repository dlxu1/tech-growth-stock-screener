from __future__ import annotations

import sys
import os
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from data.db import connect, write_source_table
from data.sources import financial_report_candidates, load_financial_report


class DataSourcesAsOfTest(unittest.TestCase):
    def test_auto_financial_report_candidates_respect_as_of_date(self) -> None:
        candidates = financial_report_candidates("auto", as_of_date="2026-04-15")

        self.assertEqual(candidates[0], "20260331")
        self.assertNotIn("20260630", candidates[:4])

    def test_cache_financial_report_falls_back_to_available_cached_report(self) -> None:
        old_db = os.environ.get("TECH_GROWTH_DB")
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["TECH_GROWTH_DB"] = str(Path(tmpdir) / "stock_data.sqlite")
            conn = connect()
            try:
                write_source_table(
                    conn,
                    "stock_yjbb_20260331",
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
            finally:
                conn.close()

            df, report_date, source = load_financial_report("auto", False, "cache", True, as_of_date="2025-12-31")

        if old_db is None:
            os.environ.pop("TECH_GROWTH_DB", None)
        else:
            os.environ["TECH_GROWTH_DB"] = old_db

        self.assertEqual(report_date, "20260331")
        self.assertEqual(source, "db:stock_yjbb_20260331")
        self.assertEqual(df["股票代码"].tolist(), ["000001"])


if __name__ == "__main__":
    unittest.main()
