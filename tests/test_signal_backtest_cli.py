from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SignalBacktestCliTest(unittest.TestCase):
    def test_signal_backtest_command_is_registered(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run.py", "signal-backtest", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--as-of-date", result.stdout)
        self.assertIn("--backtest-date", result.stdout)
        self.assertIn("--backtest-top", result.stdout)
        self.assertIn("--holding-days", result.stdout)
        self.assertIn("--format", result.stdout)

    def test_signal_validate_command_is_registered(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run.py", "signal-validate", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--validation-start", result.stdout)
        self.assertIn("--validation-end", result.stdout)
        self.assertIn("--validation-step-days", result.stdout)
        self.assertIn("--bucket-size", result.stdout)
        self.assertIn("--holding-days", result.stdout)

    def test_operation_backtest_command_is_registered(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run.py", "operation-backtest", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--backtest-date", result.stdout)
        self.assertIn("--operation-profit-target", result.stdout)
        self.assertIn("--format", result.stdout)


if __name__ == "__main__":
    unittest.main()
