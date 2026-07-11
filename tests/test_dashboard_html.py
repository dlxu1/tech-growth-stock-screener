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
        self.assertIn("macroPotentialThreshold = 80", html)
        self.assertIn("technicalTimingThreshold = 75", html)
        self.assertIn("--macro-threshold: 80%", html)
        self.assertIn("--timing-threshold-top: 25%", html)
        self.assertIn("宏观潜力分，80 为高潜力线", html)
        self.assertIn("技术时机分，75 为好时机线", html)
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
