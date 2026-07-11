from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == "__main__":
    unittest.main()
