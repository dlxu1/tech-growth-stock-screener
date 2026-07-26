import sys
import unittest
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dashboard.snapshot import snapshot_key


class DashboardSnapshotTest(unittest.TestCase):
    def base_args(self) -> Namespace:
        return Namespace(
            source="cache",
            strategy="tech_growth",
            coarse_strategy="all",
            universe="csi300",
            universe_index_symbol="000300",
            sector="",
            stock_types="",
            stock_type_config="",
            report_date="auto",
            as_of_date="2026-07-10",
            backtest_date="",
            top=5,
            sector_top=100,
            combo_top=100,
            combo_strategy_top=20,
            coarse_top=5,
            min_amount=20000000.0,
            breakout_buffer=0.003,
            volume_multiplier=1.2,
            stop_pct=0.05,
            atr_stop_multiplier=1.5,
            max_gap_up=0.05,
            move_stop_profit=0.05,
            trailing_profit=0.08,
            trailing_drawdown=0.06,
            max_position=0.25,
            backtest_top=10,
            holding_days="7,14,21",
            operation_profit_target=0.05,
            recent_high_good_hits=True,
            _skip_backtest=True,
            _skip_signal_validation=True,
            _skip_operation_backtest=True,
            _skip_recent_high_good_hits=True,
        )

    def test_v1_snapshot_key_stays_compatible_with_missing_variant(self) -> None:
        fingerprint = {"tables": {"quotes_daily": {"count": 1}}}
        args = self.base_args()
        key_without_variant, _params, _fingerprint = snapshot_key(args, fingerprint)

        args.dashboard_variant = "v1"
        key_with_v1_variant, _params, _fingerprint = snapshot_key(args, fingerprint)

        self.assertEqual(key_without_variant, key_with_v1_variant)

    def test_v2_snapshot_key_is_separate_from_v1(self) -> None:
        fingerprint = {"tables": {"quotes_daily": {"count": 1}}}
        args = self.base_args()
        v1_key, _params, _fingerprint = snapshot_key(args, fingerprint)

        args.dashboard_variant = "v2"
        v2_key, _params, _fingerprint = snapshot_key(args, fingerprint)

        self.assertNotEqual(v1_key, v2_key)


if __name__ == "__main__":
    unittest.main()
