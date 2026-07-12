from __future__ import annotations

import sys
import os
import unittest
from datetime import date, timedelta
from pathlib import Path
import tempfile

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from backtest.signal_backtest import (
    build_signal_backtest_model,
    build_signal_validation_model,
    candidates_from_dashboard_model,
    compute_forward_returns,
    parse_holding_days,
    select_signal_candidates,
)
from data.db import connect, write_quotes_daily
from backtest.repository import load_forward_quotes


def _quote_rows(code: str, base_open: float) -> list[dict]:
    rows = []
    start = date(2026, 7, 1)
    for offset in range(21):
        trade_date = start + timedelta(days=offset)
        rows.append(
            {
                "code": code,
                "trade_date": trade_date.isoformat(),
                "open": base_open,
                "high": base_open + offset + 1,
                "low": base_open - 1,
                "close": base_open + offset + 1,
                "volume": 1000,
                "amount": 100000,
            }
        )
    return rows


class SignalBacktestTest(unittest.TestCase):
    def test_load_forward_quotes_reads_rows_after_signal_date(self) -> None:
        old_db = os.environ.get("TECH_GROWTH_DB")
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["TECH_GROWTH_DB"] = str(Path(tmpdir) / "stock_data.sqlite")
            conn = connect()
            try:
                write_quotes_daily(
                    conn,
                    pd.DataFrame(
                        [
                            {"code": "000001", "trade_date": "2026-06-30", "open": 9, "high": 10, "low": 8, "close": 9, "volume": 1, "amount": 9},
                            {"code": "000001", "trade_date": "2026-07-01", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1, "amount": 10},
                        ]
                    ),
                    "unit-test",
                )
            finally:
                conn.close()

            quotes = load_forward_quotes(["1"], after_date="2026-06-30")

        if old_db is None:
            os.environ.pop("TECH_GROWTH_DB", None)
        else:
            os.environ["TECH_GROWTH_DB"] = old_db

        self.assertEqual(quotes["trade_date"].tolist(), ["2026-07-01"])
        self.assertEqual(quotes["open"].tolist(), [10.0])

    def test_parse_holding_days_accepts_comma_separated_values(self) -> None:
        self.assertEqual(parse_holding_days("7,14,21"), [7, 14, 21])
        self.assertEqual(parse_holding_days(""), [7, 14, 21])

    def test_candidates_from_dashboard_model_merges_combo_and_fine_rows(self) -> None:
        model = {
            "stages": [
                {
                    "key": "combo",
                    "rows": [
                        {"code": "000001", "name": "一号", "combo_score": 90.0, "board_name": "银行"},
                        {"code": "000002", "name": "二号", "combo_score": 80.0, "board_name": "电子"},
                    ],
                },
                {
                    "key": "fine",
                    "rows": [
                        {"code": "000001", "name": "一号", "technical_score": 70.0, "latest_trade_date": "2026-06-30"},
                        {"code": "000002", "name": "二号", "technical_score": 95.0, "latest_trade_date": "2026-06-30"},
                    ],
                },
            ]
        }

        candidates = candidates_from_dashboard_model(model)

        self.assertEqual(candidates["code"].tolist(), ["000001", "000002"])
        self.assertIn("combo_score", candidates.columns)
        self.assertIn("technical_score", candidates.columns)
        self.assertAlmostEqual(candidates.loc[candidates["code"] == "000001", "attention_score"].iloc[0], 83.0)

    def test_selects_top_ten_for_macro_technical_and_attention_scores(self) -> None:
        rows = [
            {"code": f"000{i:03d}", "name": f"股票{i}", "combo_score": float(i), "technical_score": float(20 - i)}
            for i in range(1, 13)
        ]
        candidates = pd.DataFrame(rows)

        selections = select_signal_candidates(candidates, top=10)

        self.assertEqual(selections["macro"].iloc[0]["code"], "000012")
        self.assertEqual(len(selections["macro"]), 10)
        self.assertEqual(selections["technical"].iloc[0]["code"], "000001")
        self.assertEqual(len(selections["technical"]), 10)
        self.assertIn("attention_score", selections["attention"].columns)
        self.assertIn("matrix_label", selections["attention"].columns)
        self.assertEqual(len(selections["attention"]), 10)

    def test_forward_returns_use_next_trade_open_and_horizon_close(self) -> None:
        selections = pd.DataFrame(
            [
                {"strategy": "macro", "code": "000001", "name": "一号", "score": 90.0},
                {"strategy": "macro", "code": "000002", "name": "二号", "score": 80.0},
            ]
        )
        quotes = pd.DataFrame([*_quote_rows("000001", 100.0), *_quote_rows("000002", 50.0)[:10]])

        result = compute_forward_returns(
            selections,
            quotes,
            signal_date="2026-06-30",
            holding_days=[7, 14, 21],
        )

        complete_7d = result[(result["code"] == "000001") & (result["holding_days"] == 7)].iloc[0]
        self.assertEqual(complete_7d["buy_date"], "2026-07-01")
        self.assertEqual(complete_7d["sell_date"], "2026-07-07")
        self.assertAlmostEqual(complete_7d["return_pct"], 0.07)
        self.assertEqual(complete_7d["price_points"][0]["trade_date"], "2026-07-01")
        self.assertEqual(complete_7d["price_points"][-1]["trade_date"], "2026-07-07")
        self.assertEqual(complete_7d["price_points"][0]["close"], 101.0)
        complete_21d = result[(result["code"] == "000001") & (result["holding_days"] == 21)].iloc[0]
        self.assertAlmostEqual(complete_21d["return_pct"], 0.21)
        missing_21d = result[(result["code"] == "000002") & (result["holding_days"] == 21)].iloc[0]
        self.assertEqual(missing_21d["data_status"], "insufficient_future_quotes")

    def test_forward_returns_carry_matrix_classification(self) -> None:
        selections = pd.DataFrame(
            [
                {
                    "strategy": "macro",
                    "code": "000001",
                    "name": "一号",
                    "score": 90.0,
                    "macro_score": 88.0,
                    "technical_score": 82.0,
                    "matrix_label": "好时机+高潜力",
                    "is_high_potential_good_timing": True,
                },
                {
                    "strategy": "macro",
                    "code": "000002",
                    "name": "二号",
                    "score": 80.0,
                    "macro_score": 78.0,
                    "technical_score": 82.0,
                    "matrix_label": "其他象限",
                    "is_high_potential_good_timing": False,
                },
            ]
        )
        quotes = pd.DataFrame([*_quote_rows("000001", 100.0), *_quote_rows("000002", 50.0)])

        result = compute_forward_returns(selections, quotes, signal_date="2026-06-30", holding_days=[7])

        tagged = result[result["code"] == "000001"].iloc[0]
        untagged = result[result["code"] == "000002"].iloc[0]
        self.assertTrue(tagged["is_high_potential_good_timing"])
        self.assertEqual(tagged["matrix_label"], "好时机+高潜力")
        self.assertFalse(untagged["is_high_potential_good_timing"])

    def test_builds_summary_for_three_signal_strategies(self) -> None:
        candidates = pd.DataFrame(
            [
                {"code": "000001", "name": "一号", "combo_score": 90.0, "technical_score": 70.0},
                {"code": "000002", "name": "二号", "combo_score": 80.0, "technical_score": 95.0},
            ]
        )
        quotes = pd.DataFrame([*_quote_rows("000001", 100.0), *_quote_rows("000002", 50.0)])

        model = build_signal_backtest_model(
            candidates,
            quotes,
            signal_date="2026-06-30",
            top=10,
            holding_days=[7, 14, 21],
        )

        self.assertEqual(model["summary"]["signal_date"], "2026-06-30")
        self.assertEqual([item["key"] for item in model["strategies"]], ["macro", "technical", "attention"])
        macro = model["strategies"][0]
        self.assertEqual(macro["title"], "宏观潜力 Top10")
        self.assertEqual(macro["horizons"][7]["complete_count"], 2)
        self.assertGreater(macro["horizons"][7]["avg_return_pct"], 0)

    def test_builds_validation_model_for_matrix_quadrants_and_attention_buckets(self) -> None:
        candidates = pd.DataFrame(
            [
                {"code": "000001", "name": "一号", "combo_score": 90.0, "technical_score": 80.0},
                {"code": "000002", "name": "二号", "combo_score": 85.0, "technical_score": 60.0},
                {"code": "000003", "name": "三号", "combo_score": 60.0, "technical_score": 82.0},
                {"code": "000004", "name": "四号", "combo_score": 55.0, "technical_score": 50.0},
            ]
        )
        quotes = pd.DataFrame(
            [
                *_quote_rows("000001", 100.0),
                *_quote_rows("000002", 100.0),
                *_quote_rows("000003", 100.0),
                *_quote_rows("000004", 100.0),
            ]
        )

        model = build_signal_validation_model(
            candidates,
            quotes,
            signal_date="2026-06-30",
            holding_days=[7],
            bucket_size=2,
        )

        self.assertEqual(model["summary"]["signal_dates"], ["2026-06-30"])
        self.assertEqual(model["summary"]["candidate_count"], 4)
        quadrant = model["quadrants"]["好时机+高潜力"][7]
        self.assertEqual(quadrant["complete_count"], 1)
        self.assertAlmostEqual(quadrant["avg_return_pct"], 0.07)
        self.assertIn("Top 1-2", model["attention_buckets"])
        self.assertEqual(model["attention_buckets"]["Top 1-2"][7]["complete_count"], 2)


if __name__ == "__main__":
    unittest.main()
