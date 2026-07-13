from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reports.dashboard_html import render_dashboard_html


class DashboardHtmlTest(unittest.TestCase):
    def test_renders_interactive_dashboard_shell(self) -> None:
        model = {
            "summary": {
                "stage_counts": {"sector_screen": 2, "plan": 1},
                "action_counts": {"等待回踩买入": 1},
                "stock_type_filter": {
                    "selected_types": ["科技股"],
                    "before_count": 2,
                    "after_count": 1,
                },
                "as_of_date": "2026-07-10",
                "universe": "csi300",
                "universe_index_symbol": "000300",
                "health": {
                    "health_score": 70,
                    "freshness": {"latest_trade_date": "2026-07-09", "lag_days": 1},
                    "coverage": {
                        "sector_rows": 100,
                        "sector_quote_metric_missing": 46,
                        "plan_rows": 20,
                        "plan_usable": 4,
                        "plan_missing_quotes": 8,
                    },
                    "serial": {"ok": True},
                    "issues": ["操作建议缺日线行情：8/20"],
                },
            },
            "stages": [
                {
                    "key": "sector_screen",
                    "title": "股票池",
                    "row_count": 1,
                    "columns": [
                        "code",
                        "name",
                        "board_name",
                        "market_cap",
                        "revenue_yoy",
                        "profit_yoy",
                        "amount_20d",
                        "return_60d",
                        "max_drawdown_252d",
                        "match_reason",
                        "risk_flags",
                        "stock_type",
                        "stock_type_note",
                        "data_note",
                    ],
                    "rows": [
                        {
                            "code": "688981",
                            "name": "中芯国际",
                            "board_name": "半导体",
                            "market_cap": 500000000000,
                            "revenue_yoy": 12.345,
                            "profit_yoy": -4.321,
                            "amount_20d": 1234567890,
                            "return_60d": 8.765,
                            "max_drawdown_252d": -18.9,
                            "match_reason": "board_name 命中：半导体",
                            "risk_flags": "净利润同比为负",
                            "stock_type": "科技股",
                            "stock_type_note": "股票类型：科技股；命中关键词：半导体；识别依据：board_name=半导体",
                            "data_note": "字段完整：市值、营收同比、净利同比、20日成交额、60日涨幅、年内最大回撤均有可用数据。",
                        }
                    ],
                },
                {
                    "key": "combo",
                    "title": "宏观粗筛",
                    "row_count": 1,
                    "columns": [
                        "code",
                        "name",
                        "market_cap",
                        "combo_score",
                        "overlap_score",
                        "quality_score",
                        "growth_score",
                        "risk_control_score",
                        "liquidity_score",
                        "momentum_score",
                        "strategy_hits",
                        "matched_strategies",
                    ],
                    "rows": [
                        {
                            "code": "000725",
                            "name": "京东方A",
                            "market_cap": 10045000000,
                            "combo_score": 88.6,
                            "overlap_score": 92.0,
                            "quality_score": 81.5,
                            "growth_score": 76.2,
                            "risk_control_score": 70.0,
                            "liquidity_score": 98.0,
                            "momentum_score": 66.0,
                            "strategy_hits": 3,
                            "matched_strategies": "多策略共振",
                        }
                    ],
                },
                {
                    "key": "fine",
                    "title": "技术细筛",
                    "row_count": 1,
                    "columns": [
                        "code",
                        "name",
                        "board_name",
                        "coarse_strategies",
                        "coarse_score",
                        "latest_trade_date",
                        "close",
                        "change_pct",
                        "return_20d",
                        "return_60d",
                        "amount_ratio",
                        "ma5",
                        "ma10",
                        "ma20",
                        "max_drawdown_20d",
                        "technical_score",
                        "technical_reasons",
                    ],
                    "rows": [
                        {
                            "code": "000725",
                            "name": "京东方A",
                            "board_name": "光学光电子",
                            "coarse_strategies": "多策略共振",
                            "technical_score": 77.5,
                            "coarse_score": 0.86,
                            "latest_trade_date": "2026-07-10",
                            "close": 4.236,
                            "change_pct": 0.0123,
                            "return_20d": 0.08,
                            "return_60d": 0.1567,
                            "amount_ratio": 1.234,
                            "ma5": 4.111,
                            "ma10": 4.222,
                            "ma20": 4.333,
                            "max_drawdown_20d": -0.0456,
                            "technical_reasons": "趋势强",
                        }
                    ],
                },
                {
                    "key": "plan",
                    "title": "操作建议",
                    "row_count": 1,
                    "columns": [
                        "code",
                        "name",
                        "technical_score",
                        "action",
                        "latest_close",
                        "planned_entry",
                        "initial_stop",
                        "risk_pct",
                        "take_profit_1r",
                        "take_profit_2r",
                        "plan_note",
                    ],
                    "rows": [
                        {
                            "code": "000725",
                            "name": "京东方A",
                            "technical_score": 77.5,
                            "action": "等待回踩买入",
                            "latest_close": 4.23,
                            "planned_entry": 4.18,
                            "initial_stop": 3.98,
                            "risk_pct": 0.0478,
                            "take_profit_1r": 4.38,
                            "take_profit_2r": 4.58,
                            "plan_note": "规则计划，需用明日实际开盘、成交额和盘中价触发。",
                        }
                    ],
                },
            ],
            "traces": {
                "000725": [{"stage": "sector_screen", "title": "板块筛选", "label": "京东方A", "row": {}}]
            },
            "backtest": {
                "summary": {"signal_date": "2026-07-10", "top": 10, "holding_days": [7, 14, 21]},
                "strategies": [
                    {
                        "key": "macro",
                        "title": "宏观潜力 Top10",
                        "horizons": {
                            7: {"holding_days": 7, "complete_count": 10, "avg_return_pct": 0.0123, "win_rate": 0.6},
                            14: {"holding_days": 14, "complete_count": 10, "avg_return_pct": 0.0234, "win_rate": 0.7},
                            21: {"holding_days": 21, "complete_count": 8, "avg_return_pct": -0.01, "win_rate": 0.4},
                        },
                        "rows": [
                            {
                                "code": "000725",
                                "name": "京东方A",
                                "score": 88.6,
                                "holding_days": 7,
                                "buy_date": "2026-07-13",
                                "sell_date": "2026-07-21",
                                "return_pct": 0.0123,
                                "data_status": "complete",
                            }
                        ],
                    }
                ],
            },
            "operation_backtest": {
                "summary": {
                    "signal_date": "2026-07-10",
                    "profit_target_pct": 0.05,
                    "candidate_count": 2,
                    "trade_count": 1,
                    "untriggered_count": 1,
                    "take_profit_count": 1,
                    "stop_loss_count": 0,
                    "hold_count": 0,
                    "win_rate": 1.0,
                    "realized_avg_return_pct": 0.05,
                    "total_avg_return_pct": 0.05,
                },
                "rows": [
                    {
                        "code": "000725",
                        "name": "京东方A",
                        "signal_date": "2026-07-10",
                        "action": "等待回踩买入",
                        "planned_entry": 4.18,
                        "initial_stop": 3.98,
                        "profit_target_price": 4.39,
                        "buy_date": "2026-07-13",
                        "buy_price": 4.18,
                        "sell_date": "2026-07-21",
                        "sell_price": 4.39,
                        "exit_reason": "take_profit",
                        "return_pct": 0.05,
                        "holding_days": 7,
                        "status": "take_profit",
                        "path": [
                            {"trade_date": "2026-07-13", "open": 4.2, "high": 4.25, "low": 4.1, "close": 4.18},
                            {"trade_date": "2026-07-21", "open": 4.35, "high": 4.4, "low": 4.3, "close": 4.39},
                        ],
                    },
                    {
                        "code": "000001",
                        "name": "平安银行",
                        "signal_date": "2026-07-10",
                        "action": "等待回踩买入",
                        "planned_entry": 10.0,
                        "initial_stop": 9.5,
                        "profit_target_price": None,
                        "buy_date": None,
                        "buy_price": None,
                        "sell_date": None,
                        "sell_price": None,
                        "exit_reason": "",
                        "return_pct": None,
                        "holding_days": 0,
                        "status": "not_triggered",
                        "path": [],
                    },
                ],
            },
            "signal_validation": {
                "summary": {
                    "signal_dates": ["2026-05-13"],
                    "signal_date_count": 1,
                    "candidate_count": 100,
                    "holding_days": [7, 14, 21],
                    "bucket_size": 10,
                },
                "quadrants": {
                    "好时机+高潜力": {
                        7: {"holding_days": 7, "complete_count": 4, "avg_return_pct": 0.1436, "median_return_pct": 0.0672, "win_rate": 1.0},
                        14: {"holding_days": 14, "complete_count": 4, "avg_return_pct": 0.3974, "median_return_pct": 0.4261, "win_rate": 1.0},
                    },
                    "其他象限": {
                        7: {"holding_days": 7, "complete_count": 57, "avg_return_pct": 0.0011, "median_return_pct": -0.0079, "win_rate": 0.4737},
                        14: {"holding_days": 14, "complete_count": 57, "avg_return_pct": 0.0087, "median_return_pct": -0.0279, "win_rate": 0.2632},
                    },
                },
                "attention_buckets": {
                    "Top 1-10": {
                        7: {"holding_days": 7, "complete_count": 10, "avg_return_pct": 0.0521, "median_return_pct": 0.0321, "win_rate": 0.7},
                        14: {"holding_days": 14, "complete_count": 10, "avg_return_pct": 0.2466, "median_return_pct": 0.2356, "win_rate": 0.8},
                    },
                    "Top 11-20": {
                        7: {"holding_days": 7, "complete_count": 10, "avg_return_pct": 0.0792, "median_return_pct": 0.0392, "win_rate": 0.6},
                        14: {"holding_days": 14, "complete_count": 10, "avg_return_pct": 0.0978, "median_return_pct": 0.0672, "win_rate": 0.6},
                    },
                },
            },
        }

        html = render_dashboard_html(model)

        self.assertIn("<!doctype html>", html)
        self.assertIn("选股流程交互仪表盘", html)
        self.assertIn("数据健康", html)
        self.assertIn("70/100", html)
        self.assertIn("最新行情日", html)
        self.assertIn("2026-07-09", html)
        self.assertIn("操作建议缺日线", html)
        self.assertIn("8/20", html)
        self.assertIn("类型过滤", html)
        self.assertIn("科技股 1/2", html)
        self.assertIn("潜力看宏观，时机看技术", html)
        self.assertIn("潜力-时机矩阵", html)
        self.assertIn('id="asOfDate"', html)
        self.assertIn('value="2026-07-10"', html)
        self.assertIn('name="universe" value="csi300"', html)
        self.assertIn('name="universe_index_symbol" value="000300"', html)
        self.assertIn('action="/dashboard"', html)
        self.assertIn("历史日期重算", html)
        self.assertIn("数据回测", html)
        self.assertIn("宏观潜力 Top10", html)
        self.assertIn("平均收益", html)
        self.assertIn("7日明细", html)
        self.assertIn('id="backtestStrategyTabs"', html)
        self.assertIn('id="backtestHorizonTabs"', html)
        self.assertIn('id="backtestMatrixSummary"', html)
        self.assertIn('id="backtestTableBody"', html)
        self.assertIn('id="backtestChart"', html)
        self.assertIn("好时机+高潜力", html)
        self.assertIn("backtest-row-label", html)
        self.assertIn("matrixCandidateByCode", html)
        self.assertIn("isHighPotentialGoodTiming", html)
        self.assertIn("renderBacktestMatrixSummary", html)
        self.assertIn("renderBacktestTable", html)
        self.assertIn("renderBacktestChart", html)
        self.assertIn('backtestTableBody?.addEventListener("mouseover"', html)
        self.assertIn("data-backtest-row", html)
        self.assertIn("操作回测", html)
        self.assertIn("5%止盈", html)
        self.assertIn('id="operationBacktestSummary"', html)
        self.assertIn('id="operationBacktestTableBody"', html)
        self.assertIn('id="operationBacktestPath"', html)
        self.assertIn("renderOperationBacktestPanel", html)
        self.assertIn("operation-row-active", html)
        self.assertIn("data-operation-row", html)
        self.assertIn("信号验证与预警", html)
        self.assertIn('id="validationHorizonTabs"', html)
        self.assertIn('id="validationOverview"', html)
        self.assertIn('id="validationQuadrants"', html)
        self.assertIn('id="validationBuckets"', html)
        self.assertIn("renderSignalValidationPanel", html)
        self.assertIn("validation-heatmap", html)
        self.assertIn("validation-bucket-bars", html)
        self.assertIn("象限失效预警", html)
        self.assertIn("validationMinCompleteSamples = 5", html)
        self.assertIn("样本不足", html)
        self.assertIn("排序有效性预警", html)
        self.assertIn("validationMinSignalDatesForFailure = 3", html)
        self.assertIn("单日观察", html)
        self.assertIn("信号日少于 ${validationMinSignalDatesForFailure} 个", html)
        self.assertIn("Top 1-10 未跑赢 Top 11-20", html)
        self.assertIn("验证口径：以下统计来自信号日 2026-05-13", html)
        self.assertIn("当前矩阵日为 2026-07-10", html)
        self.assertIn("象限数量不会等于当前矩阵内可见股票数", html)
        self.assertNotIn("backtest-list", html)
        self.assertNotIn("backtest-strategy", html)
        self.assertIn("回测信号日", html)
        self.assertIn('name="backtest_date"', html)
        self.assertIn('value="2026-07-10"', html)
        self.assertIn('name="as_of_date" value="2026-07-10"', html)
        self.assertNotIn("候选优先级", html)
        self.assertIn("股票池", html)
        self.assertIn("技术分析", html)
        self.assertIn("股票类型", html)
        self.assertIn("stock_type_note", html)
        self.assertIn("股票类型：科技股；命中关键词：半导体；识别依据：board_name=半导体", html)
        self.assertIn("matrixUniverse", html)
        self.assertIn('id="matrixSearch"', html)
        self.assertIn('id="matrixMatchCount"', html)
        self.assertIn('id="stockTypeFilters"', html)
        self.assertIn("stock-type-filter", html)
        self.assertIn("activeStockType", html)
        self.assertIn("renderStockTypeFilters", html)
        self.assertIn("stockTypeOptions", html)
        self.assertIn("selectFirstVisibleCandidate", html)
        self.assertIn('stockTypeFilters?.addEventListener("click"', html)
        self.assertIn("filterMatrixCandidates", html)
        self.assertIn("matrixSearchText", html)
        self.assertIn("selectFirstMatrixMatch", html)
        self.assertIn('matrixSearch?.addEventListener("input"', html)
        self.assertIn("没有匹配的矩阵股票", html)
        self.assertIn("attention_score", html)
        self.assertIn("pointSize", html)
        self.assertIn("resolveMatrixPositions", html)
        self.assertIn("quadrantBounds", html)
        self.assertIn("clampToQuadrant", html)
        self.assertIn("selected", html)
        self.assertIn("z-index", html)
        self.assertIn("var(--point-size, 24px)", html)
        self.assertIn("macroPotentialThreshold", html)
        self.assertIn("technicalTimingThreshold", html)
        self.assertIn("--macro-threshold: 80%", html)
        self.assertIn("--timing-threshold-top: 25%", html)
        self.assertIn("宏观潜力分", html)
        self.assertIn("技术时机分", html)
        self.assertIn("classificationReason", html)
        self.assertIn('class="legend" hidden', html)
        self.assertIn("candidateMetricHelp", html)
        self.assertIn("helpLabel", html)
        self.assertIn("formatTechnicalReasonText", html)
        self.assertIn("renderTechnicalReason", html)
        self.assertNotIn("技术状态", html)
        self.assertNotIn("流动性满足细筛门槛", html)
        self.assertIn("技术理由", html)
        self.assertNotIn('${escapeHtml(fine.technical_reasons || fine.technical_note || "暂无技术理由")}', html)
        self.assertIn("data-score-help", html)
        self.assertIn('detailHost.addEventListener("mouseover"', html)
        self.assertIn('detailHost.addEventListener("focusin"', html)
        self.assertIn('closest("[data-score-help]")', html)
        self.assertIn("宏观潜力分 = 宏观粗筛分", html)
        self.assertIn("技术时机分 = 技术细筛分", html)
        self.assertIn("综合关注分 = 宏观潜力分 × 65% + 技术时机分 × 35%", html)
        self.assertIn("多策略共振：宏观粗筛中策略命中的强度", html)
        self.assertIn("计划入场：规则计算出的观察入场价", html)
        self.assertIn("宏观", html)
        self.assertIn("技术", html)
        self.assertNotIn("planFocusCodes", html)
        self.assertNotIn("matrix-point plan-pick", html)
        self.assertNotIn("point-label", html)
        self.assertIn("宏观潜力", html)
        self.assertIn("技术时机", html)
        self.assertNotIn("<h3>为什么说有潜力</h3>", html)
        self.assertNotIn("<h3>为什么说时机接近</h3>", html)
        self.assertIn("macroCommentary", html)
        self.assertIn("technicalCommentary", html)
        self.assertIn('class="module-commentary"', html)
        self.assertIn(".module-commentary {\n      margin-top: 12px;", html)
        self.assertIn("font-size: 14px;", html)
        self.assertIn("border-left: 4px solid var(--accent);", html)
        self.assertIn("renderActionPlan", html)
        self.assertIn("planPriceText", html)
        self.assertIn("planStatusInfo", html)
        self.assertIn("action-plan", html)
        self.assertIn("触发条件", html)
        self.assertIn("价格计划", html)
        self.assertIn("风险提示", html)
        self.assertIn("待生成", html)
        self.assertIn('class="decision-note" hidden', html)
        self.assertIn("宏观分说明“为什么值得跟踪”", html)
        self.assertNotIn('detailMetricHeader("最新收盘"', html)
        self.assertNotIn('id="candidateList"', html)
        self.assertNotIn("renderCandidateList", html)
        self.assertNotIn("candidateSortMode", html)
        self.assertIn('class="decision-shell matrix-focus-shell"', html)
        self.assertIn(".matrix-focus-shell {\n      grid-template-columns: 1fr;", html)
        self.assertIn('class="detail-layout"', html)
        self.assertIn('class="detail-summary"', html)
        self.assertIn('class="detail-summary-main"', html)
        self.assertIn('class="detail-status chip ${item.priority.tone}"', html)
        self.assertIn('class="detail-modules"', html)
        self.assertIn('</div>\n            <div class="detail-modules">', html)
        self.assertIn(".detail-modules {\n      display: grid;", html)
        self.assertIn('class="detail-card explain-block"', html)
        self.assertIn('class="decision-panel matrix-panel"', html)
        self.assertIn('id="potentialMatrix"', html)
        self.assertIn('id="detailHost"', html)
        self.assertIn('id="stageTableSection"', html)
        self.assertIn('id="stageTableSection" class="stage-table-section" hidden', html)
        self.assertIn("buildCandidateModels", html)
        self.assertIn("renderPotentialTiming", html)
        self.assertIn("renderCandidateDetail", html)
        self.assertIn('id="globalSearch"', html)
        self.assertNotIn("<h1>选股流程交互仪表盘</h1>", html)
        self.assertNotIn('class="metrics"', html)
        self.assertNotIn("总资金", html)
        self.assertNotIn("ETF 核心仓", html)
        self.assertNotIn("个股卫星仓", html)
        self.assertNotIn("现金预留", html)
        self.assertNotIn("离线 HTML 快照", html)
        self.assertNotIn("预算状态", html)
        self.assertNotIn("组合动作", html)
        self.assertNotIn("一手成本", html)
        self.assertNotIn("配置说明", html)
        self.assertNotIn("budget_status", html)
        self.assertNotIn("portfolio_action", html)
        self.assertNotIn("lot_cost", html)
        self.assertNotIn("allocation_note", html)
        self.assertIn("宏观粗筛", html)
        self.assertIn("操作建议", html)
        self.assertNotIn("个人配置", html)
        self.assertIn("宏观粗筛分", html)
        self.assertIn("多策略共振分", html)
        self.assertIn("质量分", html)
        self.assertIn("成长分", html)
        self.assertIn("风控分", html)
        self.assertIn("流动性分", html)
        self.assertIn("动量分", html)
        self.assertIn("细筛分", html)
        self.assertIn("粗筛分", html)
        self.assertIn("策略命中", html)
        self.assertIn("strategy_summary", html)
        self.assertIn("strategySummary", html)
        self.assertIn("formatCell", html)
        self.assertIn("formatNumber", html)
        self.assertIn("formatMarketCap", html)
        self.assertIn("formatPercent", html)
        self.assertIn("formatAmountYi", html)
        self.assertIn("formatFineNumber", html)
        self.assertIn("formatFinePercent", html)
        self.assertIn("cellTitle", html)
        self.assertIn("/ 100000000", html)
        self.assertIn("亿", html)
        self.assertIn(
            'const comboVisibleColumns = ["code","name","market_cap","combo_score","growth_score","quality_score","risk_control_score","strategy_summary"];',
            html,
        )
        self.assertIn(
            'const sectorVisibleColumns = ["code","name","stock_type","board_name","market_cap","revenue_yoy","profit_yoy","amount_20d","return_60d","max_drawdown_252d","risk_flags","data_note"];',
            html,
        )
        self.assertIn(
            'const fineHiddenColumns = ["coarse_strategies"];',
            html,
        )
        self.assertIn(
            'const fineVisibleColumns = ["code","name","technical_score","coarse_score","latest_trade_date","close","change_pct","return_20d","amount_ratio","rsi14","max_drawdown_20d","technical_reasons"];',
            html,
        )
        self.assertIn(
            'const planVisibleColumns = ["code","name","technical_score","action","latest_close","planned_entry","initial_stop","risk_pct","take_profit_1r","take_profit_2r","plan_note"];',
            html,
        )
        self.assertNotIn(
            'const fineHiddenColumns = [];',
            html,
        )
        self.assertNotIn('"match_reason","risk_flags","data_note"];', html)
        self.assertIn("score-info", html)
        self.assertIn('id="scoreTooltip"', html)
        self.assertIn("data-score-help", html)
        self.assertIn("宏观粗筛分 = 多策略共振分 × 35%", html)
        self.assertIn("细筛分 = 趋势分 × 30", html)
        self.assertIn("京东方A", html)
        self.assertIn("window.DASHBOARD_DATA", html)


if __name__ == "__main__":
    unittest.main()
