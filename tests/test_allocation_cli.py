from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AllocationCliTest(unittest.TestCase):
    def test_allocation_command_is_registered(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run.py", "allocation", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--capital", result.stdout)
        self.assertIn("--target-return", result.stdout)


if __name__ == "__main__":
    unittest.main()
