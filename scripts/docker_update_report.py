"""Docker/NAS data update entry point that also writes an email digest."""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import DEFAULT_KEYWORDS, cache_dir
from dashboard.pipeline import run_dashboard
from docker_update import main as update_main
from reports.email_digest import build_daily_email_digest


def _dashboard_args() -> Namespace:
    return Namespace(
        command="dashboard",
        strategy="tech_growth",
        coarse_strategy="all",
        coarse_top=5,
        combo_strategy_top=20,
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
        sector_top=100,
        combo_top=100,
        format="html",
        output="",
        backtest_date="",
        backtest_top=10,
        holding_days="7,14,21",
        operation_profit_target=0.05,
        top=5,
        industry_rank=10,
        min_revenue_yoy=0.0,
        min_profit_yoy=0.0,
        universe="csi300",
        universe_index_symbol="000300",
        sector="",
        stock_type_config="",
        stock_types="",
        as_of_date="",
        report_date="auto",
        refresh=False,
        no_proxy=False,
        proxy=None,
        source="cache",
        keywords=",".join(DEFAULT_KEYWORDS),
        update_policy="none",
        update_start=None,
        update_end=None,
        update_daily_window_days=180,
        update_adjust="qfq",
        update_spot_max_age_days=1,
        update_index_max_age_days=7,
        no_persist_results=False,
        dashboard_cache=True,
        rebuild_dashboard_cache=True,
        recent_high_good_hits=False,
        _skip_backtest=True,
        _skip_signal_validation=True,
        _skip_operation_backtest=True,
        _skip_recent_high_good_hits=True,
        _signal_inputs=None,
    )


def _write_digest_files(digest) -> None:
    reports_dir = cache_dir() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "daily_email_latest.txt").write_text(digest.body + "\n", encoding="utf-8")
    (reports_dir / "daily_email_subject.txt").write_text(digest.subject + "\n", encoding="utf-8")
    (reports_dir / "daily_email_latest.json").write_text(json.dumps(digest.payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[docker-update-report] wrote {reports_dir / 'daily_email_latest.txt'}", flush=True)


def main() -> int:
    update_status = update_main()
    if update_status != 0:
        return update_status
    model = run_dashboard(_dashboard_args())
    digest = build_daily_email_digest(model, max_candidates=10)
    _write_digest_files(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
