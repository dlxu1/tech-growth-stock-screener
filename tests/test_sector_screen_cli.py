from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SectorScreenCliTest(unittest.TestCase):
    def test_sector_screen_command_is_registered(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run.py", "sector-screen", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--sector", result.stdout)
        self.assertIn("--universe", result.stdout)
        self.assertIn("--top", result.stdout)


if __name__ == "__main__":
    unittest.main()
