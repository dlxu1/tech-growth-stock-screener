from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from strategies.coarse.registry import run_combo


class ComboSerialFlowTest(unittest.TestCase):
    def test_run_combo_only_scores_upstream_candidates(self) -> None:
        base = pd.DataFrame(
            [
                {
                    "code": "000001",
                    "name": "上游股票",
                    "board_name": "半导体",
                    "market_cap": 1000,
                    "revenue_yoy": 20,
                    "profit_yoy": 30,
                    "roe": 12,
                    "gross_margin": 35,
                    "pe": 20,
                    "amount_20d": 100000000,
                    "return_60d": 0.2,
                    "max_drawdown_252d": -0.1,
                },
                {
                    "code": "000002",
                    "name": "非上游股票",
                    "board_name": "半导体",
                    "market_cap": 2000,
                    "revenue_yoy": 50,
                    "profit_yoy": 60,
                    "roe": 20,
                    "gross_margin": 45,
                    "pe": 18,
                    "amount_20d": 200000000,
                    "return_60d": 0.4,
                    "max_drawdown_252d": -0.05,
                },
            ]
        )
        candidates = pd.DataFrame([{"code": "000001"}])
        args = Namespace(top=5, combo_strategy_top=20)

        with (
            patch("strategies.coarse.registry.coarse_repository.build_base_universe", return_value=(base, {"stage": "base"})),
            patch("strategies.coarse.registry.persist_layer_result"),
        ):
            result, meta = run_combo(args, candidates=candidates)

        self.assertEqual(result["code"].tolist(), ["000001"])
        self.assertEqual(meta["upstream_stage"], "sector_screen")
        self.assertEqual(meta["upstream_candidates"], 1)


if __name__ == "__main__":
    unittest.main()
