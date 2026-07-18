from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run


class DashboardCliTest(unittest.TestCase):
    def test_dashboard_command_is_registered(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run.py", "dashboard", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--output", result.stdout)
        self.assertIn("--combo-top", result.stdout)
        self.assertIn("--as-of-date", result.stdout)
        self.assertIn("--backtest-date", result.stdout)
        self.assertIn("--stock-type-config", result.stdout)
        self.assertIn("--stock-types", result.stdout)
        self.assertNotIn("--capital", result.stdout)
        self.assertNotIn("--target-return", result.stdout)
        self.assertNotIn("--core-etf-pct", result.stdout)
        self.assertNotIn("--cash-pct", result.stdout)

    def test_validate_dashboard_command_is_registered(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run.py", "validate-dashboard", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--expected-latest-trade-date", result.stdout)
        self.assertIn("--format", result.stdout)
        self.assertIn(str(ROOT / ".venv" / "bin" / "python"), result.stdout)
        self.assertIn(str(ROOT / "scripts" / "run.py"), result.stdout)

    def test_dashboard_server_command_is_registered(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run.py", "dashboard-server", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--host", result.stdout)
        self.assertIn("--port", result.stdout)
        self.assertIn("--as-of-date", result.stdout)
        self.assertIn("--backtest-date", result.stdout)

    def test_dashboard_server_defaults_to_csi300_universe(self) -> None:
        old_argv = sys.argv[:]
        try:
            sys.argv = ["run.py", "dashboard-server"]
            args = run.parse_args()
        finally:
            sys.argv = old_argv

        self.assertEqual(args.universe, "csi300")
        self.assertTrue(args.recent_high_good_hits)

    def test_dashboard_server_can_disable_recent_high_good_hits(self) -> None:
        old_argv = sys.argv[:]
        try:
            sys.argv = ["run.py", "dashboard-server", "--no-recent-high-good-hits"]
            args = run.parse_args()
        finally:
            sys.argv = old_argv

        self.assertFalse(args.recent_high_good_hits)

    def test_sync_daily_prices_defaults_to_incremental_skip_existing(self) -> None:
        old_argv = sys.argv[:]
        try:
            sys.argv = ["run.py", "sync", "--dataset", "daily_prices", "--codes", "000001", "--start", "2026-01-01", "--end", "2026-07-16"]
            args = run.parse_args()
        finally:
            sys.argv = old_argv

        self.assertTrue(args.skip_existing)

    def test_sync_daily_prices_can_force_full_range(self) -> None:
        old_argv = sys.argv[:]
        try:
            sys.argv = [
                "run.py",
                "sync",
                "--dataset",
                "daily_prices",
                "--codes",
                "000001",
                "--start",
                "2026-01-01",
                "--end",
                "2026-07-16",
                "--no-skip-existing",
            ]
            args = run.parse_args()
        finally:
            sys.argv = old_argv

        self.assertFalse(args.skip_existing)


if __name__ == "__main__":
    unittest.main()
