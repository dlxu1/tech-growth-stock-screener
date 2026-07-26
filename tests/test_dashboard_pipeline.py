from __future__ import annotations

import os
import json
import sqlite3
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dashboard.pipeline import (
    _collect_recent_high_good_hits,
    _matrix_data_fingerprint_key,
    _matrix_signal_scope_key,
    run_dashboard,
)
from dashboard.market_state import MarketState
from data.db import connect


class DashboardPipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self._probe_base = pd.DataFrame([{"code": "000001", "name": "样本", "board_name": "半导体", "market_cap": 1}])
        self._probe_mainlines = [
            {
                "board_name": "半导体",
                "rank": 1,
                "mainline_score": 0.91,
                "stock_count": 1,
                "avg_return_60d": 0.48,
                "avg_amount_20d": 100000000.0,
                "avg_revenue_yoy": 0.12,
                "avg_profit_yoy": 0.08,
                "avg_max_drawdown_252d": -0.18,
                "positive_ratio": 1.0,
                "mainline_reason": "近60日涨幅 48.00%；上涨家数占比 100.00%；成交额 1.0 亿",
                "pool_source_label": "指数样本代理",
                "pool_source_note": "测试样本",
                "leaders": [{"code": "000001", "name": "样本", "leader_reason": "市值靠前"}],
                "stock_pool": [{"code": "000001", "name": "样本", "leader_reason": "市值靠前"}],
            }
        ]
        self._probe_base_patcher = patch("dashboard.pipeline.coarse_repository.build_base_universe", return_value=(self._probe_base, {"universe_source": "index_constituents:000300"}))
        self._probe_mainline_patcher = patch("dashboard.pipeline.build_industry_mainlines", return_value=self._probe_mainlines)
        self._probe_base_patcher.start()
        self._probe_mainline_patcher.start()
        self.addCleanup(self._probe_base_patcher.stop)
        self.addCleanup(self._probe_mainline_patcher.stop)

    def test_recent_high_good_hits_are_disabled_by_default(self) -> None:
        args = Namespace(
            strategy="tech_growth",
            coarse_strategy="all",
            top=5,
            sector_top=100,
            combo_top=100,
            coarse_top=5,
            sector="",
            stock_types="",
            stock_type_config="",
            as_of_date="2026-07-14",
            backtest_date="",
            universe="csi300",
            universe_index_symbol="000300",
            report_date="auto",
            source="cache",
            refresh=False,
            update_policy="none",
            dashboard_cache=False,
            _skip_backtest=True,
            _skip_signal_validation=True,
            _skip_operation_backtest=True,
        )
        one_row = pd.DataFrame([{"code": "000001", "name": "样本", "board_name": "半导体"}])

        with (
            patch("dashboard.pipeline.sector_screen.run", return_value=(one_row, {"stage": "sector_screen"})),
            patch("dashboard.pipeline.run_combo", return_value=(one_row.assign(combo_score=88.0), {"stage": "combo"})),
            patch("dashboard.pipeline.run_fine", return_value=(one_row.assign(combo_score=88.0, technical_score=76.0), {"stage": "fine"})),
            patch("dashboard.pipeline.run_trade_plan", return_value=(one_row.assign(action="观察"), {"stage": "plan"})),
            patch("dashboard.pipeline._collect_recent_high_good_hits", side_effect=AssertionError("recent hits should be skipped")),
        ):
            model = run_dashboard(args)

        self.assertNotIn("recent_high_good_hits", model["summary"])
        for stage in model["stages"]:
            self.assertNotIn("recent_high_good_hits", stage["columns"])
            for row in stage["rows"]:
                self.assertNotIn("recent_high_good_hits", row)

    def test_dashboard_snapshot_is_saved_and_reused_for_same_request(self) -> None:
        old_db = os.environ.get("TECH_GROWTH_DB")
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ["TECH_GROWTH_DB"] = str(Path(tmpdir) / "stock_data.sqlite")
                conn = connect()
                conn.close()
                args = Namespace(
                    strategy="tech_growth",
                    coarse_strategy="all",
                    top=5,
                    sector_top=100,
                    combo_top=100,
                    coarse_top=5,
                    sector="",
                    stock_types="",
                    stock_type_config="",
                    as_of_date="2026-07-14",
                    backtest_date="",
                    universe="csi300",
                    universe_index_symbol="000300",
                    report_date="auto",
                    source="cache",
                    refresh=False,
                    update_policy="none",
                    dashboard_cache=True,
                    rebuild_dashboard_cache=False,
                    _skip_backtest=True,
                    _skip_signal_validation=True,
                    _skip_operation_backtest=True,
                    _skip_recent_high_good_hits=True,
                )
                one_row = pd.DataFrame([{"code": "000001", "name": "样本", "board_name": "半导体"}])
                combo_rows = one_row.assign(combo_score=88.0)
                fine_rows = one_row.assign(combo_score=88.0, technical_score=76.0)
                plan_rows = one_row.assign(action="观察")

                with (
                    patch("dashboard.pipeline.sector_screen.run", return_value=(one_row, {"stage": "sector_screen"})) as sector_run,
                    patch("dashboard.pipeline.run_combo", return_value=(combo_rows, {"stage": "combo"})) as combo_run,
                    patch("dashboard.pipeline.run_fine", return_value=(fine_rows, {"stage": "fine"})) as fine_run,
                    patch("dashboard.pipeline.run_trade_plan", return_value=(plan_rows, {"stage": "plan"})) as plan_run,
                ):
                    first = run_dashboard(args)

                self.assertEqual(first["summary"]["dashboard_snapshot"]["cache_status"], "saved")
                with sqlite3.connect(os.environ["TECH_GROWTH_DB"]) as conn:
                    count = conn.execute("select count(*) from dashboard_snapshots").fetchone()[0]
                    model_json = conn.execute("select model_json from dashboard_snapshots").fetchone()[0]
                self.assertEqual(count, 1)
                self.assertEqual(json.loads(model_json)["summary"]["as_of_date"], "2026-07-14")
                self.assertEqual(sector_run.call_count, 1)
                self.assertEqual(combo_run.call_count, 1)
                self.assertEqual(fine_run.call_count, 1)
                self.assertEqual(plan_run.call_count, 1)

                with (
                    patch("dashboard.pipeline.sector_screen.run", side_effect=AssertionError("sector should not rerun")),
                    patch("dashboard.pipeline.run_combo", side_effect=AssertionError("combo should not rerun")),
                    patch("dashboard.pipeline.run_fine", side_effect=AssertionError("fine should not rerun")),
                    patch("dashboard.pipeline.run_trade_plan", side_effect=AssertionError("plan should not rerun")),
                ):
                    cached = run_dashboard(args)

                self.assertEqual(cached["summary"]["dashboard_snapshot"]["cache_status"], "hit")
                self.assertEqual(cached["summary"]["stage_counts"], first["summary"]["stage_counts"])
                self.assertEqual(cached["stages"][-1]["rows"][0]["action"], "观察")
        finally:
            if old_db is None:
                os.environ.pop("TECH_GROWTH_DB", None)
            else:
                os.environ["TECH_GROWTH_DB"] = old_db

    def test_rebuild_dashboard_cache_ignores_existing_snapshot(self) -> None:
        old_db = os.environ.get("TECH_GROWTH_DB")
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ["TECH_GROWTH_DB"] = str(Path(tmpdir) / "stock_data.sqlite")
                args = Namespace(
                    strategy="tech_growth",
                    coarse_strategy="all",
                    top=5,
                    sector_top=100,
                    combo_top=100,
                    coarse_top=5,
                    sector="",
                    stock_types="",
                    stock_type_config="",
                    as_of_date="2026-07-14",
                    backtest_date="",
                    universe="csi300",
                    universe_index_symbol="000300",
                    report_date="auto",
                    source="cache",
                    refresh=False,
                    update_policy="none",
                    dashboard_cache=True,
                    rebuild_dashboard_cache=False,
                    _skip_backtest=True,
                    _skip_signal_validation=True,
                    _skip_operation_backtest=True,
                    _skip_recent_high_good_hits=True,
                )
                one_row = pd.DataFrame([{"code": "000001", "name": "样本", "board_name": "半导体"}])

                with (
                    patch("dashboard.pipeline.sector_screen.run", return_value=(one_row, {"stage": "sector_screen"})),
                    patch("dashboard.pipeline.run_combo", return_value=(one_row.assign(combo_score=80), {"stage": "combo"})),
                    patch("dashboard.pipeline.run_fine", return_value=(one_row.assign(combo_score=80, technical_score=70), {"stage": "fine"})),
                    patch("dashboard.pipeline.run_trade_plan", return_value=(one_row.assign(action="观察"), {"stage": "plan"})),
                ):
                    run_dashboard(args)

                args.rebuild_dashboard_cache = True
                refreshed_plan = one_row.assign(action="等待回踩买入")
                with (
                    patch("dashboard.pipeline.sector_screen.run", return_value=(one_row, {"stage": "sector_screen"})) as sector_run,
                    patch("dashboard.pipeline.run_combo", return_value=(one_row.assign(combo_score=90), {"stage": "combo"})),
                    patch("dashboard.pipeline.run_fine", return_value=(one_row.assign(combo_score=90, technical_score=82), {"stage": "fine"})),
                    patch("dashboard.pipeline.run_trade_plan", return_value=(refreshed_plan, {"stage": "plan"})),
                ):
                    rebuilt = run_dashboard(args)

                self.assertEqual(sector_run.call_count, 1)
                self.assertEqual(rebuilt["summary"]["dashboard_snapshot"]["cache_status"], "saved")
                self.assertEqual(rebuilt["stages"][-1]["rows"][0]["action"], "等待回踩买入")
        finally:
            if old_db is None:
                os.environ.pop("TECH_GROWTH_DB", None)
            else:
                os.environ["TECH_GROWTH_DB"] = old_db

    def test_dashboard_snapshot_reuses_original_request_params_after_position_adjustment(self) -> None:
        old_db = os.environ.get("TECH_GROWTH_DB")
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ["TECH_GROWTH_DB"] = str(Path(tmpdir) / "stock_data.sqlite")

                def make_args() -> Namespace:
                    return Namespace(
                        strategy="tech_growth",
                        coarse_strategy="all",
                        top=5,
                        sector_top=100,
                        combo_top=100,
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
                        backtest_top=10,
                        holding_days="7,14,21",
                        operation_profit_target=0.05,
                        sector="",
                        stock_types="",
                        stock_type_config="",
                        as_of_date="2026-07-09",
                        backtest_date="2026-07-14",
                        universe="csi300",
                        universe_index_symbol="000300",
                        report_date="auto",
                        source="cache",
                        refresh=False,
                        update_policy="none",
                        dashboard_cache=True,
                        rebuild_dashboard_cache=False,
                        recent_high_good_hits=False,
                        _skip_backtest=True,
                        _skip_signal_validation=True,
                        _skip_operation_backtest=True,
                        _skip_recent_high_good_hits=True,
                    )

                one_row = pd.DataFrame([{"code": "000001", "name": "样本", "board_name": "半导体"}])
                defensive_state = MarketState(
                    label="bear",
                    regime="bear",
                    median_close_vs_ma20=0.9,
                    median_ma20_slope=-0.1,
                    breadth_pct=20.0,
                    bull_votes=0,
                    sample_count=1,
                    position_multiplier=0.6,
                    note="测试防御模式",
                )

                with (
                    patch("dashboard.pipeline.sector_screen.run", return_value=(one_row, {"stage": "sector_screen"})),
                    patch("dashboard.pipeline.detect", return_value=defensive_state),
                    patch("dashboard.pipeline.run_combo", return_value=(one_row.assign(combo_score=88.0), {"stage": "combo"})),
                    patch("dashboard.pipeline.run_fine", return_value=(one_row.assign(combo_score=88.0, technical_score=76.0), {"stage": "fine"})),
                    patch("dashboard.pipeline.run_trade_plan", return_value=(one_row.assign(action="观察"), {"stage": "plan"})),
                ):
                    first = run_dashboard(make_args())

                self.assertEqual(first["summary"]["dashboard_snapshot"]["cache_status"], "saved")

                with (
                    patch("dashboard.pipeline.sector_screen.run", side_effect=AssertionError("sector should not rerun")),
                    patch("dashboard.pipeline.detect", side_effect=AssertionError("detect should not rerun")),
                    patch("dashboard.pipeline.run_combo", side_effect=AssertionError("combo should not rerun")),
                    patch("dashboard.pipeline.run_fine", side_effect=AssertionError("fine should not rerun")),
                    patch("dashboard.pipeline.run_trade_plan", side_effect=AssertionError("plan should not rerun")),
                ):
                    cached = run_dashboard(make_args())

                self.assertEqual(cached["summary"]["dashboard_snapshot"]["cache_status"], "hit")
        finally:
            if old_db is None:
                os.environ.pop("TECH_GROWTH_DB", None)
            else:
                os.environ["TECH_GROWTH_DB"] = old_db

    def test_runs_all_stages_and_builds_view_model(self) -> None:
        args = Namespace(strategy="tech_growth", coarse_strategy="all", top=5, sector_top=100, coarse_top=5, sector="半导体")
        one_row = pd.DataFrame([{"code": "000725", "name": "京东方A"}])
        combo_rows = pd.DataFrame(
            [
                {"code": f"{i:06d}", "name": f"股票{i}", "combo_score": 100 - i}
                for i in range(1, 112)
            ]
        )
        combo_top100 = combo_rows.head(100)
        fine_rows = combo_rows.assign(technical_score=[50 + i for i in range(1, 112)])
        fine_top100 = fine_rows.head(100)
        plan_rows = pd.DataFrame([{"code": f"{i:06d}", "name": f"股票{i}", "action": "等待回踩买入"} for i in range(1, 101)])

        with (
            patch("dashboard.pipeline.sector_screen.run", return_value=(one_row, {"stage": "sector_screen"})) as sector_run,
            patch("dashboard.pipeline.run_combo", return_value=(combo_top100, {"stage": "combo"})) as combo_run,
            patch("dashboard.pipeline.run_fine", return_value=(fine_top100, {"stage": "fine"})) as fine_run,
            patch("dashboard.pipeline.run_trade_plan", return_value=(plan_rows, {"stage": "plan"})) as plan_run,
        ):
            model = run_dashboard(args)

        self.assertEqual(sector_run.call_args.args[0].top, 100)
        self.assertEqual(sector_run.call_args.args[0].sector, "半导体")
        self.assertEqual(sector_run.call_args.args[0].selected_industry, "半导体")
        self.assertEqual(combo_run.call_args.args[0].top, 100)
        self.assertEqual(fine_run.call_args.args[0].top, 100)
        combo_candidates = combo_run.call_args.kwargs["candidates"]
        self.assertEqual(combo_candidates["code"].tolist(), one_row["code"].tolist())
        self.assertIn("stock_type", combo_candidates.columns)
        self.assertIs(fine_run.call_args.kwargs["candidates"], combo_top100)
        self.assertEqual(len(plan_run.call_args.kwargs["candidates"]), 100)
        self.assertIn("attention_score", plan_run.call_args.kwargs["candidates"].columns)
        keys = [stage["key"] for stage in model["stages"]]
        self.assertEqual(keys, ["sector_screen", "combo", "fine", "plan"])
        self.assertEqual(model["stages"][-1]["title"], "操作建议")
        self.assertEqual(model["summary"]["stage_counts"]["combo"], 100)
        self.assertEqual(model["summary"]["stage_counts"]["fine"], 100)
        self.assertEqual(model["summary"]["stage_counts"]["plan"], 100)
        self.assertEqual(model["summary"]["selected_industry"], "半导体")
        self.assertEqual(model["summary"]["industry_pool"]["count"], 1)
        self.assertIn("health", model["summary"])
        self.assertIn("health_score", model["summary"]["health"])
        self.assertEqual(model["stages"][-1]["rows"][0]["action"], "等待回踩买入")
        self.assertNotIn("budget_status", model["stages"][-1]["rows"][0])
        self.assertIn("000001", model["traces"])

    def test_filters_downstream_candidates_by_stock_type(self) -> None:
        args = Namespace(
            strategy="tech_growth",
            coarse_strategy="all",
            top=5,
            sector_top=100,
            coarse_top=5,
            sector="",
            stock_types="科技股",
            stock_type_config="",
        )
        sector_rows = pd.DataFrame(
            [
                {"code": "000001", "name": "科技样本", "board_name": "半导体"},
                {"code": "000002", "name": "周期样本", "board_name": "煤炭开采"},
            ]
        )
        combo_rows = pd.DataFrame([{"code": "000001", "name": "科技样本", "combo_score": 90}])
        fine_rows = pd.DataFrame([{"code": "000001", "name": "科技样本", "technical_score": 80, "combo_score": 90}])
        plan_rows = pd.DataFrame([{"code": "000001", "name": "科技样本", "action": "观察"}])

        with (
            patch("dashboard.pipeline.sector_screen.run", return_value=(sector_rows, {"stage": "sector_screen"})),
            patch("dashboard.pipeline.run_combo", return_value=(combo_rows, {"stage": "combo"})) as combo_run,
            patch("dashboard.pipeline.run_fine", return_value=(fine_rows, {"stage": "fine"})),
            patch("dashboard.pipeline.run_trade_plan", return_value=(plan_rows, {"stage": "plan"})),
        ):
            model = run_dashboard(args)

        downstream_candidates = combo_run.call_args.kwargs["candidates"]
        self.assertEqual(downstream_candidates["code"].tolist(), ["000001"])
        self.assertEqual(downstream_candidates["stock_type"].tolist(), ["科技股"])
        self.assertEqual(model["summary"]["stock_type_filter"]["selected_types"], ["科技股"])
        self.assertEqual(model["summary"]["stock_type_filter"]["before_count"], 2)
        self.assertEqual(model["summary"]["stock_type_filter"]["after_count"], 1)

    def test_as_of_date_is_passed_to_all_dashboard_stages(self) -> None:
        args = Namespace(
            strategy="tech_growth",
            coarse_strategy="all",
            top=5,
            sector_top=100,
            coarse_top=5,
            sector="",
            stock_types="",
            stock_type_config="",
            as_of_date="2026-06-28",
        )
        one_row = pd.DataFrame([{"code": "000001", "name": "样本", "board_name": "半导体"}])

        with (
            patch("dashboard.pipeline.sector_screen.run", return_value=(one_row, {"stage": "sector_screen"})) as sector_run,
            patch("dashboard.pipeline.run_combo", return_value=(one_row.assign(combo_score=80), {"stage": "combo"})) as combo_run,
            patch("dashboard.pipeline.run_fine", return_value=(one_row.assign(technical_score=70, combo_score=80), {"stage": "fine"})) as fine_run,
            patch("dashboard.pipeline.run_trade_plan", return_value=(one_row.assign(action="观察"), {"stage": "plan"})) as plan_run,
            patch("backtest.repository.load_forward_quotes", return_value=pd.DataFrame()) as quote_loader,
        ):
            model = run_dashboard(args)

        self.assertEqual(sector_run.call_args.args[0].as_of_date, "2026-06-28")
        self.assertEqual(combo_run.call_args.args[0].as_of_date, "2026-06-28")
        self.assertEqual(fine_run.call_args.args[0].as_of_date, "2026-06-28")
        self.assertEqual(plan_run.call_args.args[0].as_of_date, "2026-06-28")
        self.assertEqual(model["summary"]["as_of_date"], "2026-06-28")
        quote_loader.assert_called_once()
        self.assertEqual(model["backtest"]["summary"]["signal_date"], "2026-06-28")
        self.assertIn("signal_validation", model)
        self.assertIn("operation_backtest", model)
        self.assertEqual(model["signal_validation"]["summary"]["signal_dates"], ["2026-06-28"])
        self.assertEqual(model["operation_backtest"]["summary"]["signal_date"], "2026-06-28")
        self.assertEqual([item["title"] for item in model["backtest"]["strategies"]], ["宏观潜力 Top10", "技术分 Top10", "综合关注 Top10"])

    def test_backtest_date_can_differ_from_matrix_date(self) -> None:
        args = Namespace(
            strategy="tech_growth",
            coarse_strategy="all",
            top=5,
            sector_top=100,
            coarse_top=5,
            sector="",
            stock_types="",
            stock_type_config="",
            as_of_date="2026-07-10",
            backtest_date="2026-06-30",
        )
        one_row = pd.DataFrame([{"code": "000001", "name": "样本", "board_name": "半导体"}])

        with (
            patch("dashboard.pipeline.sector_screen.run", return_value=(one_row, {"stage": "sector_screen"})) as sector_run,
            patch("dashboard.pipeline.run_combo", return_value=(one_row.assign(combo_score=80), {"stage": "combo"})),
            patch("dashboard.pipeline.run_fine", return_value=(one_row.assign(technical_score=70, combo_score=80), {"stage": "fine"})),
            patch("dashboard.pipeline.run_trade_plan", return_value=(one_row.assign(action="观察"), {"stage": "plan"})),
            patch("backtest.repository.load_forward_quotes", return_value=pd.DataFrame()) as quote_loader,
        ):
            model = run_dashboard(args)

        self.assertEqual(model["summary"]["as_of_date"], "2026-07-10")
        self.assertEqual(model["summary"]["backtest_date"], "2026-06-30")
        self.assertEqual(model["backtest"]["summary"]["signal_date"], "2026-06-30")
        self.assertEqual(model["signal_validation"]["summary"]["signal_dates"], ["2026-06-30"])
        self.assertEqual(model["operation_backtest"]["summary"]["signal_date"], "2026-06-30")
        self.assertEqual(quote_loader.call_args.kwargs["after_date"], "2026-06-30")
        self.assertIn("2026-06-30", [call.args[0].as_of_date for call in sector_run.call_args_list])

    def test_annotates_current_high_good_candidates_with_recent_hits(self) -> None:
        args = Namespace(
            strategy="tech_growth",
            coarse_strategy="all",
            top=5,
            sector_top=100,
            coarse_top=5,
            sector="",
            stock_types="",
            stock_type_config="",
            as_of_date="2026-07-16",
            recent_high_good_hits=True,
            _skip_backtest=True,
            _skip_signal_validation=True,
            _skip_operation_backtest=True,
        )
        sector_rows = pd.DataFrame(
            [
                {"code": "000001", "name": "重复命中", "board_name": "半导体"},
                {"code": "000002", "name": "普通命中", "board_name": "半导体"},
            ]
        )
        combo_rows = pd.DataFrame(
            [
                {"code": "000001", "name": "重复命中", "combo_score": 91.0},
                {"code": "000002", "name": "普通命中", "combo_score": 89.0},
            ]
        )
        fine_rows = pd.DataFrame(
            [
                {"code": "000001", "name": "重复命中", "combo_score": 91.0, "technical_score": 82.0},
                {"code": "000002", "name": "普通命中", "combo_score": 89.0, "technical_score": 79.0},
            ]
        )
        plan_rows = pd.DataFrame([{"code": "000001", "name": "重复命中", "action": "观察"}])
        recent_hits = {
            "000001": {
                "count": 4,
                "dates": ["2026-06-26", "2026-07-02", "2026-07-10", "2026-07-16"],
                "window_start": "2026-06-16",
                "window_end": "2026-07-16",
                "highlight": True,
            },
        }

        with (
            patch("dashboard.pipeline.sector_screen.run", return_value=(sector_rows, {"stage": "sector_screen"})),
            patch("dashboard.pipeline.run_combo", return_value=(combo_rows, {"stage": "combo"})),
            patch("dashboard.pipeline.run_fine", return_value=(fine_rows, {"stage": "fine"})),
            patch("dashboard.pipeline.run_trade_plan", return_value=(plan_rows, {"stage": "plan"})),
            patch("dashboard.pipeline._collect_recent_high_good_hits", return_value=recent_hits, create=True) as collect_hits,
        ):
            model = run_dashboard(args)

        collect_hits.assert_called_once()
        fine_stage = next(stage for stage in model["stages"] if stage["key"] == "fine")
        rows_by_code = {row["code"]: row for row in fine_stage["rows"]}
        self.assertEqual(rows_by_code["000001"]["recent_high_good_hits"]["count"], 4)
        self.assertTrue(rows_by_code["000001"]["recent_high_good_hits"]["highlight"])
        self.assertEqual(rows_by_code["000002"]["recent_high_good_hits"]["count"], 0)
        self.assertEqual(model["summary"]["recent_high_good_hits"]["highlight_min_count"], 4)

    def test_recent_hit_collection_uses_each_signal_dates_dynamic_thresholds(self) -> None:
        args = Namespace(as_of_date="2026-07-16")
        current_model = {
            "summary": {
                "as_of_date": "2026-07-16",
                "adaptive_thresholds": {"macro_potential_threshold": 80, "technical_timing_threshold": 75},
            },
            "stages": [
                {"key": "combo", "rows": [{"code": "000001", "name": "样本", "combo_score": 90.0}]},
                {"key": "fine", "rows": [{"code": "000001", "name": "样本", "combo_score": 90.0, "technical_score": 80.0}]},
            ],
        }
        historical_hit_model = {
            "summary": {
                "as_of_date": "2026-07-01",
                "adaptive_thresholds": {"macro_potential_threshold": 80, "technical_timing_threshold": 75},
            },
            "stages": [
                {"key": "combo", "rows": [{"code": "000001", "name": "样本", "combo_score": 90.0}]},
                {"key": "fine", "rows": [{"code": "000001", "name": "样本", "combo_score": 90.0, "technical_score": 80.0}]},
            ],
        }
        historical_miss_model = {
            "summary": {
                "as_of_date": "2026-07-02",
                "adaptive_thresholds": {"macro_potential_threshold": 95, "technical_timing_threshold": 90},
            },
            "stages": [
                {"key": "combo", "rows": [{"code": "000001", "name": "样本", "combo_score": 90.0}]},
                {"key": "fine", "rows": [{"code": "000001", "name": "样本", "combo_score": 90.0, "technical_score": 80.0}]},
            ],
        }

        with (
            patch("dashboard.pipeline._recent_signal_dates", return_value=["2026-07-01", "2026-07-02", "2026-07-16"]),
            patch("dashboard.pipeline.run_dashboard", side_effect=[historical_hit_model, historical_miss_model]),
        ):
            hits = _collect_recent_high_good_hits(current_model, args)

        self.assertEqual(hits["000001"]["count"], 2)
        self.assertEqual(hits["000001"]["dates"], ["2026-07-01", "2026-07-16"])

    def test_recent_hit_collection_uses_matrix_signal_snapshots_without_rerunning_dashboard(self) -> None:
        old_db = os.environ.get("TECH_GROWTH_DB")
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ["TECH_GROWTH_DB"] = str(Path(tmpdir) / "stock_data.sqlite")
                args = Namespace(
                    as_of_date="2026-07-16",
                    source="cache",
                    strategy="tech_growth",
                    coarse_strategy="all",
                    universe="csi300",
                    universe_index_symbol="000300",
                    sector="",
                    stock_types="",
                    stock_type_config="",
                    report_date="auto",
                    top=5,
                    sector_top=100,
                    combo_top=100,
                    combo_strategy_top=20,
                    coarse_top=5,
                    min_amount=20000000.0,
                )
                current_model = {
                    "summary": {
                        "as_of_date": "2026-07-16",
                        "adaptive_thresholds": {"macro_potential_threshold": 80, "technical_timing_threshold": 75},
                    },
                    "stages": [
                        {"key": "fine", "rows": [{"code": "000001", "name": "样本", "combo_score": 90.0, "technical_score": 80.0}]},
                    ],
                }
                conn = connect()
                try:
                    scope_key, params_json = _matrix_signal_scope_key(args)
                    fingerprint_key, fingerprint_json = _matrix_data_fingerprint_key()
                    rows = [
                        ("2026-07-01", "000001", "样本", 90.0, 80.0, 80.0, 75.0, 1),
                        ("2026-07-02", "000001", "样本", 90.0, 80.0, 95.0, 90.0, 0),
                        ("2026-07-16", "000001", "样本", 90.0, 80.0, 80.0, 75.0, 1),
                    ]
                    conn.executemany(
                        """
                        insert into dashboard_matrix_signals(
                            scope_key, data_fingerprint_key, as_of_date, code, name,
                            macro_score, technical_score, macro_threshold, technical_threshold,
                            is_high_good, created_at, params_json, data_fingerprint_json
                        )
                        values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '2026-07-18T00:00:00', ?, ?)
                        """,
                        [
                            (scope_key, fingerprint_key, *row, params_json, fingerprint_json)
                            for row in rows
                        ],
                    )
                    conn.commit()
                finally:
                    conn.close()

                with (
                    patch("dashboard.pipeline._recent_signal_dates", return_value=["2026-07-01", "2026-07-02", "2026-07-16"]),
                    patch("dashboard.pipeline.run_dashboard", side_effect=AssertionError("historical dashboard should not rerun")),
                ):
                    hits = _collect_recent_high_good_hits(current_model, args)

                self.assertEqual(hits["000001"]["count"], 2)
                self.assertEqual(hits["000001"]["dates"], ["2026-07-01", "2026-07-16"])
        finally:
            if old_db is None:
                os.environ.pop("TECH_GROWTH_DB", None)
            else:
                os.environ["TECH_GROWTH_DB"] = old_db

    def test_recent_hit_collection_reuses_persistent_cache_for_same_identity(self) -> None:
        args = Namespace(as_of_date="2026-07-16", universe="csi300", universe_index_symbol="000300", stock_types="")
        current_model = {
            "summary": {
                "as_of_date": "2026-07-16",
                "adaptive_thresholds": {"macro_potential_threshold": 80, "technical_timing_threshold": 75},
            },
            "stages": [
                {"key": "fine", "rows": [{"code": "000001", "name": "样本", "combo_score": 90.0, "technical_score": 80.0}]},
            ],
        }
        historical_hit_model = {
            "summary": {
                "as_of_date": "2026-07-01",
                "adaptive_thresholds": {"macro_potential_threshold": 80, "technical_timing_threshold": 75},
            },
            "stages": [
                {"key": "fine", "rows": [{"code": "000001", "name": "样本", "combo_score": 90.0, "technical_score": 80.0}]},
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            old_cache = os.environ.get("TECH_GROWTH_SCREENER_CACHE")
            old_db = os.environ.get("TECH_GROWTH_DB")
            os.environ["TECH_GROWTH_SCREENER_CACHE"] = tmp
            os.environ["TECH_GROWTH_DB"] = str(Path(tmp) / "stock_data.sqlite")
            conn = connect()
            conn.close()
            try:
                with (
                    patch("dashboard.pipeline._recent_signal_dates", return_value=["2026-07-01", "2026-07-16"]),
                    patch("dashboard.pipeline.run_dashboard", return_value=historical_hit_model) as dashboard_run,
                ):
                    first = _collect_recent_high_good_hits(current_model, args)
                    second = _collect_recent_high_good_hits(current_model, args)
            finally:
                if old_cache is None:
                    os.environ.pop("TECH_GROWTH_SCREENER_CACHE", None)
                else:
                    os.environ["TECH_GROWTH_SCREENER_CACHE"] = old_cache
                if old_db is None:
                    os.environ.pop("TECH_GROWTH_DB", None)
                else:
                    os.environ["TECH_GROWTH_DB"] = old_db

        self.assertEqual(first, second)
        self.assertEqual(first["000001"]["dates"], ["2026-07-01", "2026-07-16"])
        dashboard_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
