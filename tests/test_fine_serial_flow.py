from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from strategies.fine.technical import _score_one, run


class FineSerialFlowTest(unittest.TestCase):
    def test_run_fine_uses_combo_candidates_when_provided(self) -> None:
        candidates = pd.DataFrame(
            [
                {
                    "code": "000001",
                    "name": "宏观入选",
                    "board_name": "半导体",
                    "matched_strategies": "多策略共振",
                    "combo_score": 88.5,
                }
            ]
        )
        args = Namespace(coarse_strategy="all", coarse_top=50, top=5, min_amount=20000000)

        with (
            patch("strategies.fine.technical.fine_repository.coarse_candidates") as coarse_candidates,
            patch("strategies.fine.technical.fine_repository.load_quotes", return_value=pd.DataFrame()),
            patch("strategies.fine.technical.persist_layer_result"),
        ):
            result, meta = run(args, candidates=candidates)

        coarse_candidates.assert_not_called()
        self.assertEqual(result["code"].tolist(), ["000001"])
        self.assertEqual(result.iloc[0]["coarse_score"], 88.5)
        self.assertEqual(meta["upstream_stage"], "combo")
        self.assertEqual(meta["upstream_candidates"], 1)

    def test_run_fine_loads_quotes_at_as_of_date(self) -> None:
        candidates = pd.DataFrame(
            [
                {
                    "code": "000001",
                    "name": "宏观入选",
                    "board_name": "半导体",
                    "matched_strategies": "多策略共振",
                    "combo_score": 88.5,
                }
            ]
        )
        args = Namespace(coarse_strategy="all", coarse_top=50, top=5, min_amount=20000000, as_of_date="2026-06-28")

        with (
            patch("strategies.fine.technical.fine_repository.load_quotes", return_value=pd.DataFrame()) as load_quotes,
            patch("strategies.fine.technical.persist_layer_result"),
        ):
            run(args, candidates=candidates)

        load_quotes.assert_called_once_with(["000001"], as_of_date="2026-06-28")

    def test_volume_concentration_strength_changes_technical_score(self) -> None:
        candidate = pd.Series(
            {
                "code": "000001",
                "name": "宏观入选",
                "board_name": "半导体",
                "coarse_strategies": "多策略共振",
                "coarse_score": 88.5,
            }
        )
        base = pd.DataFrame(
            {
                "trade_date": pd.date_range("2026-01-01", periods=20).strftime("%Y-%m-%d"),
                "open": [10 + i for i in range(20)],
                "high": [10.5 + i for i in range(20)],
                "low": [9.5 + i for i in range(20)],
                "close": [10.2 + i for i in range(20)],
                "amount": [100000000] * 20,
            }
        )
        moderate_volume = [70 / 15] * 15 + [6] * 5
        strong_volume = [50 / 15] * 15 + [10] * 5

        moderate = _score_one(candidate, base.assign(volume=moderate_volume), min_amount=20000000)
        strong = _score_one(candidate, base.assign(volume=strong_volume), min_amount=20000000)

        self.assertGreater(strong["technical_score"], moderate["technical_score"])


if __name__ == "__main__":
    unittest.main()
