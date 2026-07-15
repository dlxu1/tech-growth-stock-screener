from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from strategies.coarse.registry import _mean_reversion_score, _peg_score, run_combo


class ComboSerialFlowTest(unittest.TestCase):
    def test_peg_score_accepts_percent_and_ratio_growth_units(self) -> None:
        pe = pd.Series([20.0, 20.0])
        revenue_yoy = pd.Series([20.0, 0.20])
        profit_yoy = pd.Series([30.0, 0.30])

        score = _peg_score(pe, revenue_yoy, profit_yoy)

        self.assertAlmostEqual(score.iloc[0], score.iloc[1], places=6)
        self.assertLess(score.iloc[0], 1.0)

    def test_mean_reversion_requires_negative_recent_momentum(self) -> None:
        return_60d = pd.Series([-0.20, 0.20])
        drawdown = pd.Series([-0.30, -0.30])
        revenue_yoy = pd.Series([20.0, 20.0])
        profit_yoy = pd.Series([30.0, 30.0])

        score = _mean_reversion_score(return_60d, drawdown, revenue_yoy, profit_yoy)

        self.assertGreater(score.iloc[0], score.iloc[1])
        self.assertLess(score.iloc[1], 0.5)

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

    def test_run_combo_keeps_scores_after_market_regime_merge(self) -> None:
        base = pd.DataFrame(
            [
                {
                    "code": "000001",
                    "name": "一号",
                    "board_name": "半导体",
                    "market_cap": 1000,
                    "revenue": 100,
                    "profit": 10,
                    "revenue_yoy": 0.20,
                    "profit_yoy": 0.30,
                    "roe": 12,
                    "gross_margin": 35,
                    "pe": 20,
                    "amount_20d": 100000000,
                    "return_60d": 0.20,
                    "max_drawdown_252d": -0.10,
                },
                {
                    "code": "000002",
                    "name": "二号",
                    "board_name": "半导体",
                    "market_cap": 2000,
                    "revenue": 200,
                    "profit": 30,
                    "revenue_yoy": 0.50,
                    "profit_yoy": 0.60,
                    "roe": 20,
                    "gross_margin": 45,
                    "pe": 18,
                    "amount_20d": 200000000,
                    "return_60d": 0.40,
                    "max_drawdown_252d": -0.05,
                },
                {
                    "code": "000003",
                    "name": "三号",
                    "board_name": "半导体",
                    "market_cap": 1500,
                    "revenue": 150,
                    "profit": 20,
                    "revenue_yoy": 0.10,
                    "profit_yoy": 0.12,
                    "roe": 16,
                    "gross_margin": 40,
                    "pe": 22,
                    "amount_20d": 150000000,
                    "return_60d": -0.05,
                    "max_drawdown_252d": -0.20,
                },
            ],
            index=[10, 20, 30],
        )
        candidates = pd.DataFrame([{"code": "000001"}, {"code": "000002"}, {"code": "000003"}])
        args = Namespace(top=3, combo_strategy_top=3)

        for regime in ["bull", "transition", "bear"]:
            with self.subTest(regime=regime):
                with (
                    patch("strategies.coarse.registry.coarse_repository.build_base_universe", return_value=(base, {"stage": "base"})),
                    patch("strategies.coarse.registry.persist_layer_result"),
                ):
                    result, _meta = run_combo(args, candidates=candidates, market_state=regime)

                self.assertEqual(len(result), 3)
                self.assertFalse(result["combo_score"].isna().any())
                self.assertFalse(result["momentum_score"].isna().any())


if __name__ == "__main__":
    unittest.main()
