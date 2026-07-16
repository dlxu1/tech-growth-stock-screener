from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dashboard.server import _args_for_request, _build_dashboard_response


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

    def test_dashboard_response_cache_reuses_same_url(self) -> None:
        server = SimpleNamespace(
            base_args=Namespace(
                command="dashboard-server",
                universe="csi300",
                universe_index_symbol="000300",
                as_of_date="",
                backtest_date="",
                source="cache",
            ),
            response_cache={},
        )

        with (
            patch("dashboard.server.run_dashboard", return_value={"summary": {"as_of_date": "2026-07-16"}, "stages": []}) as dashboard_run,
            patch("dashboard.server.render_dashboard_html", return_value="<html>ok</html>") as renderer,
        ):
            first = _build_dashboard_response(server, "/dashboard", {"as_of_date": ["2026-07-16"]})
            second = _build_dashboard_response(server, "/dashboard", {"as_of_date": ["2026-07-16"]})

        self.assertEqual(first, second)
        dashboard_run.assert_called_once()
        renderer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
