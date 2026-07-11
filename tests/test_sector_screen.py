from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from strategies.sector_screen import MAX_SECTOR_TOP, filter_by_sector, run


class SectorScreenTest(unittest.TestCase):
    def test_filter_by_sector_matches_board_name_terms(self) -> None:
        base = pd.DataFrame(
            [
                {"code": "688981", "name": "中芯国际", "board_name": "半导体"},
                {"code": "300308", "name": "中际旭创", "board_name": "通信设备"},
                {"code": "601939", "name": "建设银行", "board_name": "银行Ⅱ"},
            ]
        )

        filtered, meta = filter_by_sector(base, "半导体,光模块")

        self.assertEqual(filtered["code"].tolist(), ["688981"])
        self.assertEqual(meta["sector_terms"], ["半导体", "光模块"])
        self.assertEqual(meta["sector_filtered"], 1)

    def test_run_caps_top_at_100_without_strategy_score(self) -> None:
        rows = []
        for idx in range(120):
            rows.append(
                {
                    "code": f"{idx:06d}",
                    "name": f"股票{idx}",
                    "board_name": "半导体",
                    "market_cap": 1000 + idx,
                    "revenue_yoy": idx,
                    "profit_yoy": idx * 2,
                    "amount_20d": None if idx == 119 else 1000000 + idx,
                    "return_60d": idx / 1000,
                    "max_drawdown_252d": -0.1,
                }
            )
        args = Namespace(top=150, sector="半导体")

        with patch("strategies.sector_screen.coarse_repository.build_base_universe", return_value=(pd.DataFrame(rows), {"universe": "csi300"})):
            result, meta = run(args)

        self.assertEqual(MAX_SECTOR_TOP, 100)
        self.assertEqual(len(result), 100)
        self.assertEqual(meta["requested_top"], 150)
        self.assertEqual(meta["capped_top"], 100)
        self.assertNotIn("sector_score", result.columns)
        self.assertNotIn("score_reason", result.columns)
        self.assertIn("match_reason", result.columns)
        self.assertEqual(result.iloc[0]["code"], "000119")
        self.assertEqual(result.iloc[-1]["code"], "000020")
        self.assertEqual(result.iloc[0]["match_reason"], "board_name 命中：半导体")
        self.assertIn("字段缺失", result.iloc[0]["data_note"])
        self.assertIn("20日成交额", result.iloc[0]["data_note"])
        self.assertIn("N/A", result.iloc[0]["data_note"])
        self.assertIn("市值、营收同比、净利同比、20日成交额、60日涨幅、年内最大回撤", result.iloc[0]["data_note"])
        self.assertIn("按市值降序", result.iloc[0]["data_note"])


if __name__ == "__main__":
    unittest.main()
