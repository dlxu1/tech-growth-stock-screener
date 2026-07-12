from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dashboard.server import _args_for_request


class DashboardServerTest(unittest.TestCase):
    def test_request_query_can_override_dashboard_universe(self) -> None:
        args = _args_for_request(
            Namespace(command="dashboard-server", universe="tech", universe_index_symbol="000300", as_of_date=""),
            {"as_of_date": ["2026-06-30"], "universe": ["csi300"], "universe_index_symbol": ["000300"]},
        )

        self.assertEqual(args.command, "dashboard")
        self.assertEqual(args.as_of_date, "2026-06-30")
        self.assertEqual(args.universe, "csi300")
        self.assertEqual(args.universe_index_symbol, "000300")

    def test_request_query_can_override_backtest_date(self) -> None:
        args = _args_for_request(
            Namespace(command="dashboard-server", universe="csi300", universe_index_symbol="000300", as_of_date="2026-07-10", backtest_date=""),
            {"backtest_date": ["2026-06-30"]},
        )

        self.assertEqual(args.command, "dashboard")
        self.assertEqual(args.as_of_date, "2026-07-10")
        self.assertEqual(args.backtest_date, "2026-06-30")


if __name__ == "__main__":
    unittest.main()
