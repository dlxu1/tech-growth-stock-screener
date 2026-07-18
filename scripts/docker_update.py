"""Docker/NAS data update entry point."""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_PY = ROOT / "scripts" / "run.py"


def run_step(args: list[str]) -> None:
    command = [sys.executable, str(RUN_PY), *args]
    print(f"[docker-update] {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    today = date.today().isoformat()
    run_step(["sync", "--dataset", "spot", "--source", "auto"])
    run_step(["sync", "--dataset", "financials", "--report-date", "auto", "--source", "auto"])
    run_step(["sync", "--dataset", "index_constituents", "--index-symbol", "000300", "--source", "auto"])
    run_step(
        [
            "sync",
            "--dataset",
            "daily_prices",
            "--from-index",
            "--index-symbol",
            "000300",
            "--start",
            "2026-01-01",
            "--end",
            today,
            "--adjust",
            "qfq",
            "--source",
            "auto",
        ]
    )
    run_step(["validate-dashboard", "--source", "cache"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
