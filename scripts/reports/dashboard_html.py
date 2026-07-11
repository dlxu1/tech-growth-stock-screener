"""Interactive offline HTML dashboard for full screening runs."""

from __future__ import annotations

import json
from html import escape


def _json_script(model: dict) -> str:
    return json.dumps(model, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _money(value) -> str:
    try:
        if value is None:
            return "N/A"
        return f"{float(value):.0f} 元"
    except Exception:
        return "N/A"


def _stat(label: str, value: str) -> str:
    return f"""
      <div class="metric">
        <span>{escape(label)}</span>
        <strong>{escape(value)}</strong>
      </div>
    """


COLUMN_LABELS = {
    "code": "代码",
    "name": "名称",
    "board_name": "行业/板块",
    "market_cap": "市值",
    "pe": "市盈率",
    "pb": "市净率",
    "revenue": "营业收入",
    "profit": "净利润",
    "revenue_yoy": "营收同比",
    "profit_yoy": "净利同比",
    "roe": "ROE",
    "gross_margin": "毛利率",
    "rd_intensity": "研发强度",
    "amount_20d": "20日成交额",
    "return_60d": "60日涨幅",
    "max_drawdown_252d": "年内最大回撤",
    "industry_rank": "行业排名",
    "score": "综合分",
    "combo_score": "宏观粗筛分",
    "overlap_score": "多策略共振分",
    "quality_score": "质量分",
    "growth_score": "成长分",
    "risk_control_score": "风控分",
    "liquidity_score": "流动性分",
    "momentum_score": "动量分",
    "strategy_hits": "命中策略数",
    "matched_strategies": "命中策略",
    "strategy_summary": "策略命中",
    "stock_type": "股票类型",
    "stock_type_note": "类型说明",
    "coarse_strategy": "粗筛策略",
    "coarse_strategy_title": "策略名称",
    "coarse_score": "粗筛分",
    "attention_score": "综合关注分",
    "coarse_reason": "入选逻辑",
    "technical_score": "细筛分",
    "technical_reasons": "技术理由",
    "technical_note": "技术说明",
    "return_20d": "20日涨幅",
    "latest_trade_date": "最新交易日",
    "close": "收盘价",
    "change_pct": "当日涨跌幅",
    "amount_ratio": "量能倍数",
    "ma5": "5日均线",
    "ma10": "10日均线",
    "ma20": "20日均线",
    "macd_hist": "MACD柱",
    "rsi14": "RSI14",
    "max_drawdown_20d": "20日最大回撤",
    "action": "操作动作",
    "latest_close": "最新收盘",
    "planned_entry": "计划入场",
    "initial_stop": "初始止损",
    "risk_pct": "价格风险",
    "take_profit_1r": "一倍风险目标",
    "take_profit_2r": "两倍风险目标",
    "plan_note": "计划说明",
    "entry_price": "计划买入价",
    "stop_price": "止损价",
    "target_price": "目标价",
    "position_size": "建议仓位",
    "match_reason": "匹配理由",
    "risk_flags": "风险提示",
    "data_note": "数据说明",
}


SCORE_HELP = {
    "*": {
        "score": "综合分 = 领导力分 + 成长分。领导力分来自行业内市值排名，成长分来自营收同比和净利润同比。",
        "coarse_score": "粗筛分 = 当前粗筛策略的排名分。不同策略会组合市值、估值、营收增长、净利增长、ROE、毛利率、回撤、成交额等指标。",
    },
    "combo": {
        "combo_score": (
            "宏观粗筛分 = 多策略共振分 × 35% + 成长分 × 20% + 质量分 × 18% + "
            "风控分 × 15% + 流动性分 × 7% + 动量分 × 5%。多策略共振分 = "
            "命中策略权重 / 总策略权重 × 100；成长分来自营收同比和净利润同比的正向排名；"
            "质量分来自 ROE、毛利率和 PE 合理度；风控分来自最大回撤和成交额。"
        ),
        "overlap_score": "多策略共振分 = 命中策略权重 / 总策略权重 × 100。命中越多高权重粗筛策略，分数越高。",
        "growth_score": "成长分 = 营收同比和净利润同比正值相加后做百分位排名，再 × 100。",
        "quality_score": "质量分 = ROE排名 × 45% + 毛利率排名 × 30% + PE合理度 × 25%，再 × 100。",
        "risk_control_score": "风控分 = 最大回撤绝对值低排名 × 70% + 20日成交额排名 × 30%，再 × 100。",
        "liquidity_score": "流动性分 = 20日成交额在基础股票池中的百分位排名 × 100。",
        "momentum_score": "动量分 = 60日涨幅在基础股票池中的百分位排名 × 100。",
        "strategy_summary": "策略命中 = 该股票进入了多少个宏观粗筛子策略。命中策略数越多，说明多维度共振越强；命中策略的权重会进一步换算为多策略共振分。",
    },
    "fine": {
        "technical_score": (
            "细筛分 = 趋势分 × 30 + 动量分 × 20 + 量能分 × 20 + 突破分 × 15 + "
            "风险分 × 10 + 流动性分 × 5。趋势看均线多头和20日均线上行；动量看20日涨幅、MACD和RSI；"
            "量能看成交额放大、当日上涨和20日成交额门槛；突破看20日新高附近和收盘位置；风险看20日回撤和ATR。"
        ),
        "coarse_score": "粗筛分 = 进入技术细筛前的宏观/粗筛阶段得分，用作技术分相同或接近时的次级排序依据。",
    },
}


def _health_html(summary: dict) -> str:
    health = summary.get("health") or {}
    if not health:
        return ""
    score = health.get("health_score", 0)
    try:
        score_number = int(score)
    except (TypeError, ValueError):
        score_number = 0
    tone = "green" if score_number >= 85 else ("warn" if score_number >= 70 else "danger")
    freshness = health.get("freshness") or {}
    coverage = health.get("coverage") or {}
    serial = health.get("serial") or {}
    latest = freshness.get("latest_trade_date") or "N/A"
    sector_missing = coverage.get("sector_quote_metric_missing", 0)
    sector_rows = coverage.get("sector_rows", 0)
    plan_missing = coverage.get("plan_missing_quotes", 0)
    plan_rows = coverage.get("plan_rows", 0)
    plan_usable = coverage.get("plan_usable", 0)
    serial_text = "通过" if serial.get("ok") else "异常"
    stock_type_filter = summary.get("stock_type_filter") or {}
    selected_types = stock_type_filter.get("selected_types") or []
    stock_type_text = "全部" if not selected_types else ",".join(str(item) for item in selected_types)
    stock_type_count = f"{stock_type_filter.get('after_count', sector_rows)}/{stock_type_filter.get('before_count', sector_rows)}"
    issues = health.get("issues") or []
    issue_text = "；".join(str(issue) for issue in issues[:3]) or "当前未发现关键数据问题"
    return f"""
    <section class="health-strip" title="{escape(issue_text)}">
      <div class="health-main">
        <span class="chip {tone}">数据健康</span>
        <strong>{score_number}/100</strong>
        <span class="muted">用于判断本次结果能否直接用于研究复核</span>
      </div>
      <div class="health-metrics">
        <div><span>最新行情日</span><strong>{escape(str(latest))}</strong></div>
        <div><span>股票池缺指标</span><strong>{escape(str(sector_missing))}/{escape(str(sector_rows))}</strong></div>
        <div><span>操作建议缺日线</span><strong>{escape(str(plan_missing))}/{escape(str(plan_rows))}</strong></div>
        <div><span>操作建议可执行</span><strong>{escape(str(plan_usable))}/{escape(str(plan_rows))}</strong></div>
        <div><span>阶段串行</span><strong>{escape(serial_text)}</strong></div>
        <div><span>类型过滤</span><strong>{escape(stock_type_text)} {escape(stock_type_count)}</strong></div>
      </div>
    </section>
    """


def render_dashboard_html(model: dict) -> str:
    """Render a self-contained dashboard document."""

    stages = model.get("stages", [])
    tabs = "\n".join(
        f'<button type="button" class="tab{" active" if i == 0 else ""}" data-stage-key="{escape(stage["key"])}">{escape(stage["title"])} <span>{int(stage.get("row_count") or 0)}</span></button>'
        for i, stage in enumerate(stages)
    )
    data_json = _json_script(model)
    column_labels_json = _json_script(COLUMN_LABELS)
    score_help_json = _json_script(SCORE_HELP)
    health_html = _health_html(model.get("summary", {}))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>选股流程交互仪表盘</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f4;
      --panel: #ffffff;
      --text: #18212f;
      --muted: #667284;
      --line: #d9e0e6;
      --accent: #247c6d;
      --accent-soft: #e5f2ee;
      --warn: #a8642a;
      --danger: #b94a48;
      --track: #e9edf0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    main {{
      width: min(1440px, calc(100% - 32px));
      margin: 0 auto;
      padding: 16px 0 44px;
    }}
    h2 {{ margin: 0; letter-spacing: 0; }}
    h2 {{ font-size: 18px; }}
    .muted {{ color: var(--muted); }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .toolbar {{
      display: flex;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
      margin: 0 0 12px;
      flex-wrap: wrap;
    }}
    .tabs {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    button.tab {{
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--text);
      border-radius: 8px;
      padding: 8px 10px;
      cursor: pointer;
      font: inherit;
    }}
    button.tab.active {{
      background: var(--accent-soft);
      border-color: var(--accent);
    }}
    button.tab span {{ color: var(--muted); margin-left: 4px; }}
    input[type="search"] {{
      width: min(420px, 100%);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 11px;
      font-size: 14px;
      background: var(--panel);
      color: var(--text);
    }}
    .dashboard-hero {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 16px;
      margin-bottom: 12px;
    }}
    h1 {{
      margin: 0;
      font-size: 23px;
      font-weight: 600;
      letter-spacing: 0;
    }}
    .hero-copy {{
      margin-top: 5px;
      max-width: 780px;
      color: var(--muted);
    }}
    .stage-funnel {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 12px;
    }}
    .funnel-card {{
      padding: 10px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .funnel-top {{
      display: flex;
      justify-content: space-between;
      gap: 8px;
      font-size: 13px;
      font-weight: 500;
    }}
    .funnel-count {{ color: var(--muted); }}
    .funnel-bar {{
      height: 7px;
      border-radius: 999px;
      background: var(--track);
      overflow: hidden;
      margin: 8px 0 5px;
    }}
    .funnel-bar span {{
      display: block;
      height: 100%;
      background: var(--accent);
    }}
    .health-strip {{
      display: grid;
      grid-template-columns: minmax(260px, 0.85fr) minmax(0, 1.6fr);
      gap: 12px;
      align-items: center;
      padding: 12px;
      margin: -2px 0 12px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .health-main {{
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
      flex-wrap: wrap;
    }}
    .health-main strong {{
      font-size: 22px;
      line-height: 1;
    }}
    .health-metrics {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 8px;
    }}
    .health-metrics div {{
      min-width: 0;
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfb;
    }}
    .health-metrics span {{
      display: block;
      color: var(--muted);
      font-size: 11px;
      white-space: nowrap;
    }}
    .health-metrics strong {{
      display: block;
      margin-top: 2px;
      font-size: 14px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .decision-shell {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
      align-items: start;
      margin-bottom: 12px;
    }}
    .matrix-focus-shell {{
      grid-template-columns: 1fr;
    }}
    .decision-panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      overflow: hidden;
    }}
    .section-title {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      margin-bottom: 4px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      padding: 3px 8px;
      background: #eef1f3;
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }}
    .chip.green {{ background: var(--accent-soft); color: var(--accent); }}
    .chip.blue {{ background: #e8eef7; color: #315f9f; }}
    .chip.warn {{ background: #f5ecd9; color: var(--warn); }}
    .chip.danger {{ background: #f5e3e1; color: var(--danger); }}
    .code {{ color: var(--muted); font-size: 12px; margin-left: 4px; }}
    .matrix {{
      --macro-threshold: 80%;
      --timing-threshold-top: 25%;
      position: relative;
      min-height: 486px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background:
        linear-gradient(90deg, rgba(185, 74, 72, 0.06) 0 var(--macro-threshold), rgba(36, 124, 109, 0.10) var(--macro-threshold) 100%),
        linear-gradient(180deg, rgba(36, 124, 109, 0.08) 0 var(--timing-threshold-top), rgba(185, 74, 72, 0.06) var(--timing-threshold-top) 100%);
      overflow: hidden;
      margin-top: 10px;
    }}
    .matrix-panel .matrix {{
      min-height: 650px;
    }}
    .matrix-tools {{
      display: flex;
      gap: 10px;
      align-items: center;
      margin-top: 10px;
    }}
    .matrix-tools input[type="search"] {{
      flex: 1;
      min-width: 220px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 11px;
      font-size: 14px;
      background: #fff;
    }}
    .matrix-count {{
      min-width: 76px;
      text-align: right;
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }}
    .stock-type-filters {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 10px;
    }}
    .stock-type-filter {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 5px 9px;
      background: var(--panel);
      color: var(--text);
      font: inherit;
      font-size: 12px;
      cursor: pointer;
    }}
    .stock-type-filter.active {{
      background: var(--accent-soft);
      border-color: var(--accent);
      color: var(--accent);
      font-weight: 600;
    }}
    .matrix::before,
    .matrix::after {{
      content: "";
      position: absolute;
      background: rgba(24, 33, 47, 0.18);
    }}
    .matrix::before {{ left: var(--macro-threshold); top: 0; width: 1px; height: 100%; }}
    .matrix::after {{ left: 0; top: var(--timing-threshold-top); height: 1px; width: 100%; }}
    .quad {{
      position: absolute;
      padding: 10px;
      color: var(--muted);
      font-size: 12px;
    }}
    .q1 {{ right: 0; top: 0; text-align: right; }}
    .q2 {{ left: 0; top: 0; }}
    .q3 {{ left: 0; bottom: 0; }}
    .q4 {{ right: 0; bottom: 0; text-align: right; }}
    .axis-x,
    .axis-y {{
      position: absolute;
      font-size: 12px;
      color: var(--muted);
    }}
    .axis-x {{ left: 50%; bottom: 8px; transform: translateX(-50%); }}
    .axis-y {{ left: 8px; top: 50%; transform: translateY(-50%) rotate(-90deg); transform-origin: left center; }}
    .matrix-point {{
      position: absolute;
      transform: translate(-50%, -50%);
      width: var(--point-size, 24px);
      height: var(--point-size, 24px);
      border-radius: 50%;
      border: 2px solid var(--panel);
      box-shadow: 0 6px 18px rgba(24, 33, 47, 0.18);
      color: #fff;
      font-weight: 600;
      font-size: 12px;
      cursor: pointer;
      z-index: 2;
      transition: transform 0.12s ease, box-shadow 0.12s ease;
    }}
    .matrix-point:hover,
    .matrix-point:focus-visible,
    .matrix-point.selected {{
      transform: translate(-50%, -50%) scale(1.16);
      box-shadow: 0 10px 24px rgba(24, 33, 47, 0.24);
      z-index: 8;
    }}
    .matrix-point.green {{ background: var(--accent); }}
    .matrix-point.blue {{ background: #315f9f; }}
    .matrix-point.warn {{ background: var(--warn); }}
    .matrix-point.danger {{ background: var(--danger); }}
    .legend {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      margin-top: 10px;
    }}
    .legend[hidden] {{ display: none; }}
    .legend-item {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px;
      background: var(--panel);
    }}
    #detailHost {{
      padding: 0;
      border: 0;
      background: transparent;
      overflow: visible;
    }}
    .detail-layout {{
      display: grid;
      gap: 12px;
    }}
    .detail-summary {{
      display: grid;
      gap: 14px;
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: var(--panel);
    }}
    .detail-summary-main {{
      display: grid;
      grid-template-columns: minmax(260px, 0.75fr) minmax(0, 1.25fr);
      gap: 14px;
      align-items: center;
    }}
    .detail-modules {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      align-items: stretch;
    }}
    .detail-card {{
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: var(--panel);
    }}
    .detail-head {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
      margin-bottom: 10px;
    }}
    .detail-summary .detail-head {{
      margin-bottom: 0;
    }}
    .detail-title {{
      min-width: 0;
    }}
    .detail-status {{
      margin-bottom: 8px;
      width: fit-content;
    }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-bottom: 10px;
    }}
    .detail-summary .kpis {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
      margin-bottom: 0;
    }}
    .kpi {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px;
      background: #fbfcfb;
    }}
    .kpi strong {{ display: block; font-size: 18px; }}
    .kpi span {{ font-size: 11px; color: var(--muted); }}
    .kpi[data-score-help],
    .help-label {{
      cursor: help;
    }}
    .help-label {{
      border-bottom: 1px dotted var(--muted);
      text-underline-offset: 2px;
    }}
    .explain-block {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: var(--panel);
      margin-top: 9px;
    }}
    .detail-card.explain-block {{
      margin-top: 0;
      padding: 12px;
    }}
    .detail-card h3 {{
      margin: 0 0 10px;
      font-size: 16px;
    }}
    .mini-bars {{ display: grid; gap: 7px; margin-top: 9px; }}
    .mini {{
      display: grid;
      grid-template-columns: 82px 1fr 44px;
      gap: 8px;
      align-items: center;
      font-size: 12px;
    }}
    .mini-track {{
      height: 7px;
      border-radius: 999px;
      background: var(--track);
      overflow: hidden;
    }}
    .mini-track span {{ display: block; height: 100%; background: var(--accent); }}
    .technical-reason {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }}
    .module-commentary {{
      margin-top: 12px;
      border-left: 4px solid var(--accent);
      border-radius: 8px;
      padding: 10px 12px;
      background: var(--accent-soft);
      color: var(--text);
      font-size: 14px;
      font-weight: 600;
      line-height: 1.62;
    }}
    .action-plan {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfb;
      margin-top: 9px;
    }}
    .action-plan-head {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
      margin-bottom: 8px;
    }}
    .action-title {{
      font-size: 16px;
      font-weight: 600;
    }}
    .action-copy {{
      margin-top: 4px;
      color: var(--text);
      font-weight: 500;
    }}
    .action-plan h3 {{
      margin: 10px 0 6px;
      font-size: 13px;
    }}
    .detail-modules .action-plan {{
      margin-top: 0;
      min-width: 0;
    }}
    .trigger-list {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 6px 8px;
      margin: 8px 0 10px;
      color: var(--muted);
      font-size: 12px;
    }}
    .trigger-item {{
      display: flex;
      align-items: center;
      gap: 6px;
      min-width: 0;
    }}
    .trigger-dot {{
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--accent);
      flex: 0 0 auto;
    }}
    .plan-price-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    .plan-price {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding: 8px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      font-size: 13px;
    }}
    .plan-price:nth-last-child(-n+2) {{ border-bottom: 0; }}
    .plan-price:nth-child(odd) {{ border-right: 1px solid var(--line); }}
    .plan-price strong {{ font-weight: 600; }}
    .risk-note {{
      margin-top: 9px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px;
      color: var(--muted);
      background: var(--panel);
      font-size: 12px;
    }}
    .risk-note.green {{ border-color: var(--accent); background: var(--accent-soft); color: var(--accent); }}
    .risk-note.warn {{ border-color: var(--warn); background: #f5ecd9; color: var(--warn); }}
    .risk-note.danger {{ border-color: var(--danger); background: #f5e3e1; color: var(--danger); }}
    .decision-note {{
      margin-top: 12px;
      border: 1px solid var(--accent);
      background: var(--accent-soft);
      color: var(--accent);
      border-radius: 8px;
      padding: 10px;
      font-size: 13px;
    }}
    .decision-note[hidden] {{ display: none; }}
    .stage-table-section {{ margin-top: 12px; }}
    section {{ padding: 16px; overflow: hidden; }}
    .stage-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }}
    .stage-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 320px;
      gap: 14px;
      align-items: start;
    }}
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; background: var(--panel); }}
    th, td {{
      padding: 8px 9px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      white-space: nowrap;
      max-width: 220px;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    th {{
      color: var(--muted);
      font-weight: 500;
      background: #fafbf9;
      cursor: pointer;
      position: sticky;
      top: 0;
    }}
    .th-content {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }}
    .score-info {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 16px;
      height: 16px;
      border: 1px solid var(--accent);
      border-radius: 50%;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 11px;
      line-height: 1;
      font-weight: 700;
      cursor: help;
    }}
    .score-tooltip {{
      position: fixed;
      z-index: 20;
      width: min(360px, 72vw);
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      color: var(--text);
      box-shadow: 0 10px 24px rgba(24, 33, 47, 0.14);
      font-size: 12px;
      font-weight: 400;
      line-height: 1.5;
      white-space: normal;
      text-align: left;
      visibility: hidden;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.12s ease;
    }}
    .score-tooltip.visible {{
      visibility: visible;
      opacity: 1;
    }}
    tbody tr {{ cursor: pointer; }}
    tbody tr:hover {{ background: #f3f7f5; }}
    .trace {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: var(--panel);
    }}
    .trace h2 {{ font-size: 16px; margin-bottom: 10px; }}
    .trace-step {{
      display: grid;
      grid-template-columns: 86px minmax(0, 1fr);
      gap: 8px;
      padding: 8px 0;
      border-bottom: 1px solid var(--line);
    }}
    .trace-step:last-child {{ border-bottom: 0; }}
    .badge {{
      display: inline-block;
      padding: 2px 6px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
    }}
    .empty {{ padding: 24px; color: var(--muted); text-align: center; }}
    @media (max-width: 960px) {{
      main {{ width: min(100% - 20px, 1440px); padding-top: 16px; }}
      .dashboard-hero {{ display: block; }}
      .stage-funnel,
      .health-strip,
      .health-metrics,
      .decision-shell,
      .matrix-focus-shell,
      .detail-layout,
      .detail-summary,
      .detail-summary-main,
      .detail-modules,
      .legend {{ grid-template-columns: 1fr; }}
      .stage-grid {{ grid-template-columns: 1fr; }}
      .toolbar {{ align-items: stretch; }}
      input[type="search"] {{ width: 100%; }}
    }}
    @media (min-width: 961px) and (max-width: 1280px) {{
      .detail-modules {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}
    @media (max-width: 520px) {{
      th, td {{ max-width: 150px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header class="dashboard-hero">
      <div>
        <h1>新版交互：潜力看宏观，时机看技术</h1>
        <div class="hero-copy">首页先看宏观粗筛和技术分析后的候选股票，并用宏观粗筛分判断潜力底座、用细筛分判断当前时机质量。操作建议只作为下一交易日观察规则。</div>
      </div>
      <span class="chip green">研究和辅助决策</span>
    </header>
    <div class="stage-funnel" id="stageFunnel"></div>
    {health_html}
    <div class="decision-shell matrix-focus-shell">
      <section class="decision-panel matrix-panel">
        <div class="section-title">
          <h2>潜力-时机矩阵</h2>
          <span class="chip">宏观 × 技术</span>
        </div>
        <div class="muted">横轴是宏观粗筛分，纵轴是技术细筛分。右上角才是优先研究对象。</div>
        <div class="matrix-tools">
          <input id="matrixSearch" type="search" placeholder="检索矩阵股票：代码、名称、行业、动作" aria-label="检索潜力时机矩阵股票">
          <span id="matrixMatchCount" class="matrix-count"></span>
        </div>
        <div class="stock-type-filters" id="stockTypeFilters" aria-label="按股票类型筛选矩阵股票"></div>
        <div class="matrix" id="potentialMatrix"></div>
        <div class="legend" hidden>
          <div class="legend-item"><span class="chip green">优先研究</span><div class="muted">宏观高、技术高</div></div>
          <div class="legend-item"><span class="chip blue">等待时机</span><div class="muted">宏观高、技术未确认</div></div>
          <div class="legend-item"><span class="chip warn">谨慎复核</span><div class="muted">技术强、宏观一般</div></div>
          <div class="legend-item"><span class="chip danger">暂不关注</span><div class="muted">两项都弱</div></div>
        </div>
      </section>
      <section class="decision-panel" id="detailHost"></section>
    </div>
    <section id="stageTableSection" class="stage-table-section" hidden>
      <div class="toolbar">
        <div class="tabs">{tabs}</div>
        <input id="globalSearch" type="search" placeholder="搜索代码、名称、行业、动作">
      </div>
      <div class="stage-head">
        <h2 id="stageTitle"></h2>
        <div id="visibleCount" class="muted"></div>
      </div>
      <div class="stage-grid">
        <div class="table-wrap" id="tableHost"></div>
        <aside class="trace" id="traceHost">
          <h2>阶段轨迹</h2>
          <div class="muted">点击任意股票行查看它在各阶段的出现记录。</div>
        </aside>
      </div>
    </section>
  </main>
  <div id="scoreTooltip" class="score-tooltip" role="tooltip"></div>
  <script>
    window.DASHBOARD_DATA = {data_json};
    const columnLabels = {column_labels_json};
    const scoreHelp = {score_help_json};
    const comboVisibleColumns = ["code","name","market_cap","combo_score","growth_score","quality_score","risk_control_score","strategy_summary"];
    const sectorVisibleColumns = ["code","name","stock_type","board_name","market_cap","revenue_yoy","profit_yoy","amount_20d","return_60d","max_drawdown_252d","risk_flags","data_note"];
    const fineVisibleColumns = ["code","name","technical_score","coarse_score","latest_trade_date","close","change_pct","return_20d","amount_ratio","rsi14","max_drawdown_20d","technical_reasons"];
    const planVisibleColumns = ["code","name","technical_score","action","latest_close","planned_entry","initial_stop","risk_pct","take_profit_1r","take_profit_2r","plan_note"];
    const percentColumns = ["revenue_yoy","profit_yoy","return_60d","max_drawdown_252d"];
    const fineHiddenColumns = ["coarse_strategies"];
    const finePercentColumns = ["change_pct","return_20d","return_60d","max_drawdown_20d"];
    const fineNumberColumns = ["coarse_score","technical_score","close","amount_ratio","ma5","ma10","ma20","macd_hist","rsi14"];
    const planPercentColumns = ["risk_pct","position_cap"];
    const planNumberColumns = ["technical_score","latest_close","planned_entry","initial_stop","take_profit_1r","take_profit_2r"];
    const macroPotentialThreshold = 80;
    const technicalTimingThreshold = 75;
    const data = window.DASHBOARD_DATA;
    const stageFunnel = document.getElementById("stageFunnel");
    const potentialMatrix = document.getElementById("potentialMatrix");
    const matrixSearch = document.getElementById("matrixSearch");
    const matrixMatchCount = document.getElementById("matrixMatchCount");
    const stockTypeFilters = document.getElementById("stockTypeFilters");
    const detailHost = document.getElementById("detailHost");
    const search = document.getElementById("globalSearch");
    const tableHost = document.getElementById("tableHost");
    const traceHost = document.getElementById("traceHost");
    const stageTitle = document.getElementById("stageTitle");
    const visibleCount = document.getElementById("visibleCount");
    const scoreTooltip = document.getElementById("scoreTooltip");
    let activeStage = data.stages[0]?.key || "";
    let sortState = {{ column: "", dir: 1 }};
    let selectedCandidateCode = "";
    let activeStockType = "全部";

    function text(value) {{
      if (value === null || value === undefined || value === "") return "N/A";
      return String(value);
    }}

    function escapeHtml(value) {{
      return text(value).replace(/[&<>"']/g, (ch) => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[ch]));
    }}

    function numberValue(value) {{
      const number = Number(value);
      return Number.isFinite(number) ? number : null;
    }}

    function percentWidth(value) {{
      const number = numberValue(value);
      if (number === null) return 0;
      return Math.max(4, Math.min(100, number));
    }}

    function stageByKey(key) {{
      return data.stages.find((stage) => stage.key === key) || {{ rows: [], row_count: 0, title: key }};
    }}

    function rowsByCode(stageKey) {{
      const result = {{}};
      for (const row of stageByKey(stageKey).rows || []) {{
        const code = codeKey(row);
        if (code && code !== "000000") result[code] = row;
      }}
      return result;
    }}

    function codeKey(row) {{
      return text(row?.code || "").padStart(6, "0");
    }}

    function scoreText(value) {{
      const number = numberValue(value);
      return number === null ? "N/A" : number.toFixed(1);
    }}

    const candidateMetricHelp = {{
      macroScore: "宏观潜力分 = 宏观粗筛分。用于判断这只股票是否有足够好的基本面、行业地位、成长质量和风险控制底座。",
      technicalScore: "技术时机分 = 技术细筛分。趋势、动量、量能、突破、回撤和流动性共同决定当前是否接近观察窗口。",
      attention_score: "综合关注分 = 宏观潜力分 × 65% + 技术时机分 × 35%。它决定矩阵点位大小，用来表达研究优先级。",
      "多策略共振": "多策略共振：宏观粗筛中策略命中的强度。命中策略越多、质量越高，说明基本面候选理由越稳定。",
      "成长": "成长：主要看营收、利润等成长指标，判断公司是否真的在扩张，而不是只靠题材或估值变化。",
      "质量": "质量：关注盈利质量、财务稳定性和经营效率，避免只看增长速度忽略增长含金量。",
      "风控": "风控：关注回撤、估值压力、财务异常和风险提示，用来降低高分但风险过大的候选权重。",
      "20日涨幅": "20日涨幅：近20个交易日价格表现，反映短期动量，但过热时也需要结合回撤和量能复核。",
      "量能倍数": "量能倍数：当前成交活跃度相对近期均值的放大程度，用于判断资金关注度是否提升。",
      "RSI14": "RSI14：14日相对强弱指标，衡量短期强弱和过热程度，过高时需要警惕追高风险。",
      "回撤控制": "回撤控制：近20日最大回撤越小，说明走势越稳；回撤过大时即使反弹也要谨慎。",
      latest_close: "最新收盘：最近一个交易日的收盘价，是后续入场、止损和目标价计算的参考基准。",
      planned_entry: "计划入场：规则计算出的观察入场价，不是立即买入指令，需要结合下一交易日实际走势确认。",
      initial_stop: "初始止损：如果入场后走势不符合预期，用来控制单笔价格风险的参考价。",
      risk_pct: "价格风险：计划入场价到初始止损价之间的跌幅比例，用来衡量这笔观察计划的风险厚度。",
      take_profit_1r: "1R 目标：以入场到止损的风险距离计算出的第一档目标价。",
      take_profit_2r: "2R 目标：以入场到止损的风险距离计算出的第二档目标价。",
    }};

    function metricHelp(key) {{
      return candidateMetricHelp[key] || "该指标用于辅助解释单只股票的筛选结果。";
    }}

    function helpLabel(label, key = label) {{
      return `<span class="help-label" data-score-help="${{escapeHtml(metricHelp(key))}}" tabindex="0">${{escapeHtml(label)}}</span>`;
    }}

    function detailMetricHeader(label, key) {{
      return `<th data-score-help="${{escapeHtml(metricHelp(key))}}">${{helpLabel(label, key)}}</th>`;
    }}

    function hasPositiveNumber(value) {{
      const number = numberValue(value);
      return number !== null && number > 0;
    }}

    function planPriceText(value) {{
      const number = numberValue(value);
      if (number === null || number <= 0) return "待生成";
      return number.toFixed(2);
    }}

    function planRiskText(value) {{
      const number = numberValue(value);
      if (number === null || number <= 0) return "待生成";
      return `${{(number * 100).toFixed(2)}}%`;
    }}

    function planStatusInfo(plan, item) {{
      const hasPricePlan = hasPositiveNumber(plan.planned_entry) && hasPositiveNumber(plan.initial_stop);
      const risk = numberValue(plan.risk_pct);
      if (!hasPricePlan) return {{ label: "暂无价格计划", tone: "danger", action: "观察，暂无价格计划" }};
      if (risk !== null && risk >= 0.08) return {{ label: "风险偏高", tone: "warn", action: plan.action || item.action || "观察" }};
      if ((plan.action || item.action || "").includes("等待")) return {{ label: "等确认", tone: "blue", action: plan.action || item.action }};
      return {{ label: "可观察", tone: "green", action: plan.action || item.action || "观察" }};
    }}

    function planMetric(label, key, value, formatter = planPriceText) {{
      return `
        <div class="plan-price">
          <span>${{helpLabel(label, key)}}</span>
          <strong>${{escapeHtml(formatter(value))}}</strong>
        </div>
      `;
    }}

    function renderActionPlan(plan, item, fine) {{
      const status = planStatusInfo(plan, item);
      const hasPricePlan = hasPositiveNumber(plan.planned_entry) && hasPositiveNumber(plan.initial_stop);
      const risk = numberValue(plan.risk_pct);
      const riskTone = status.tone === "danger" ? "danger" : (risk !== null && risk >= 0.08 ? "warn" : "green");
      const riskText = status.tone === "danger"
        ? "风险提示：价格计划待生成，先只做观察，不把 0.00 当成真实入场或止损。"
        : `风险提示：当前价格风险为 ${{planRiskText(plan.risk_pct)}}，需等待触发条件同时满足。`;
      const technicalText = scoreText(item.technicalScore);
      const entryTrigger = hasPricePlan ? "接近计划入场价" : "等待生成计划入场价";
      const stopTrigger = hasPricePlan ? "未跌破初始止损区" : "暂无止损价前不执行";
      return `
        <div class="action-plan">
          <div class="action-plan-head">
            <div>
              <div class="action-title">操作建议</div>
              <div class="action-copy">${{escapeHtml(status.action)}}</div>
            </div>
            <span class="chip ${{status.tone}}">${{escapeHtml(status.label)}}</span>
          </div>
          <h3>触发条件</h3>
          <div class="trigger-list">
            <div class="trigger-item"><span class="trigger-dot"></span><span>${{escapeHtml(entryTrigger)}}</span></div>
            <div class="trigger-item"><span class="trigger-dot"></span><span>量能不明显缩量</span></div>
            <div class="trigger-item"><span class="trigger-dot"></span><span>技术分维持在 ${{technicalText}}</span></div>
            <div class="trigger-item"><span class="trigger-dot"></span><span>${{escapeHtml(stopTrigger)}}</span></div>
          </div>
          <h3>价格计划</h3>
          <div class="plan-price-grid">
            ${{planMetric("最新收盘", "latest_close", plan.latest_close)}}
            ${{planMetric("计划入场", "planned_entry", plan.planned_entry)}}
            ${{planMetric("初始止损", "initial_stop", plan.initial_stop)}}
            ${{planMetric("价格风险", "risk_pct", plan.risk_pct, planRiskText)}}
            ${{planMetric("1R 目标", "take_profit_1r", plan.take_profit_1r)}}
            ${{planMetric("2R 目标", "take_profit_2r", plan.take_profit_2r)}}
          </div>
          <div class="risk-note ${{riskTone}}">风险提示：${{escapeHtml(riskText.replace(/^风险提示：/, ""))}}</div>
        </div>
      `;
    }}

    function priorityInfo(macroScore, technicalScore) {{
      const macroHigh = numberValue(macroScore) !== null && Number(macroScore) >= macroPotentialThreshold;
      const techHigh = numberValue(technicalScore) !== null && Number(technicalScore) >= technicalTimingThreshold;
      if (macroHigh && techHigh) return {{ rank: "A", label: "高潜力 + 好时机", tone: "green", order: 0 }};
      if (macroHigh) return {{ rank: "B", label: "高潜力 + 等时机", tone: "blue", order: 1 }};
      if (techHigh) return {{ rank: "C", label: "趋势强 + 需复核", tone: "warn", order: 2 }};
      return {{ rank: "D", label: "暂不关注", tone: "danger", order: 3 }};
    }}

    function thresholdText(value, threshold) {{
      const number = numberValue(value);
      if (number === null) return `N/A < ${{threshold}}`;
      return `${{number.toFixed(1)}} ${{number >= threshold ? "≥" : "<"}} ${{threshold}}`;
    }}

    function classificationReason(item) {{
      return `宏观 ${{thresholdText(item.macroScore, macroPotentialThreshold)}}，技术 ${{thresholdText(item.technicalScore, technicalTimingThreshold)}}，分类：${{item.priority.label}}`;
    }}

    function normalizedMacroScore(combo, fine) {{
      const comboScore = numberValue(combo.combo_score ?? fine.combo_score);
      if (comboScore !== null) return comboScore;
      const coarseScore = numberValue(fine.coarse_score ?? combo.coarse_score);
      if (coarseScore === null) return null;
      return coarseScore <= 1 ? coarseScore * 100 : coarseScore;
    }}

    function attentionScore(row, combo, fine) {{
      const explicit = numberValue(row.attention_score ?? fine.attention_score ?? combo.attention_score);
      if (explicit !== null) return explicit;
      const macro = normalizedMacroScore(combo, fine);
      const technical = numberValue(row.technical_score ?? fine.technical_score);
      if (macro === null && technical === null) return null;
      return (macro ?? 0) * 0.65 + (technical ?? 0) * 0.35;
    }}

    function pointSize(attention_score) {{
      const score = numberValue(attention_score);
      if (score === null) return 28;
      const clamped = Math.max(0, Math.min(100, score));
      return 24 + (clamped / 100) * 20;
    }}

    function quadrantBounds(macro, top) {{
      const timingTop = 100 - technicalTimingThreshold;
      const macroHigh = macro >= macroPotentialThreshold;
      const timingHigh = top <= timingTop;
      return {{
        left: macroHigh ? macroPotentialThreshold + 3 : 4,
        right: macroHigh ? 96 : macroPotentialThreshold - 3,
        top: timingHigh ? 4 : timingTop + 3,
        bottom: timingHigh ? timingTop - 3 : 96,
      }};
    }}

    function clampToQuadrant(point, bounds) {{
      return {{
        x: Math.max(bounds.left, Math.min(bounds.right, point.x)),
        y: Math.max(bounds.top, Math.min(bounds.bottom, point.y)),
      }};
    }}

    function resolveMatrixPositions(candidates) {{
      const placed = [];
      const minGap = 5.4;
      const offsets = [
        [0, 0],
        [3.2, 0], [-3.2, 0], [0, 3.2], [0, -3.2],
        [2.6, 2.6], [-2.6, 2.6], [2.6, -2.6], [-2.6, -2.6],
        [5.4, 0], [-5.4, 0], [0, 5.4], [0, -5.4],
        [4.6, 4.6], [-4.6, 4.6], [4.6, -4.6], [-4.6, -4.6],
      ];
      return candidates.map((item, index) => {{
        const macro = Math.max(4, Math.min(96, item.macroScore ?? 0));
        const tech = Math.max(4, Math.min(96, item.technicalScore ?? 0));
        const top = 100 - tech;
        const bounds = quadrantBounds(macro, top);
        let chosen = clampToQuadrant({{ x: macro, y: top }}, bounds);
        for (const [dx, dy] of offsets) {{
          const candidate = clampToQuadrant({{ x: macro + dx, y: top + dy }}, bounds);
          const overlaps = placed.some((point) => Math.hypot(candidate.x - point.x, candidate.y - point.y) < minGap);
          if (!overlaps) {{
            chosen = candidate;
            break;
          }}
        }}
        placed.push(chosen);
        return {{
          ...item,
          matrixX: chosen.x,
          matrixY: chosen.y,
          rawMacro: macro,
          rawTop: top,
          pointSize: pointSize(item.attention_score),
          zIndex: 2 + index,
        }};
      }});
    }}

    function matrixUniverse() {{
      const sectorRows = rowsByCode("sector_screen");
      const comboRows = rowsByCode("combo");
      const fineRows = rowsByCode("fine");
      const planRows = rowsByCode("plan");
      let codes = [...new Set([...Object.keys(comboRows), ...Object.keys(fineRows)])];
      if (!codes.length) codes = [...new Set([...Object.keys(planRows), ...Object.keys(sectorRows)])];
      return codes.map((code) => {{
        const row = planRows[code] || fineRows[code] || comboRows[code] || sectorRows[code] || {{}};
        const combo = comboRows[code] || {{}};
        const fine = fineRows[code] || {{}};
        const plan = planRows[code] || {{}};
        const sector = sectorRows[code] || {{}};
        const macroScore = normalizedMacroScore(combo, fine);
        const technicalScore = numberValue(plan.technical_score ?? fine.technical_score);
        const attention_score = attentionScore(plan, combo, fine);
        const priority = priorityInfo(macroScore, technicalScore);
        return {{
          code,
          name: plan.name || fine.name || combo.name || sector.name || row.name || code,
          board: fine.board_name || sector.board_name || combo.board_name || "",
          stockType: sector.stock_type || "未分类",
          macroScore,
          technicalScore,
          attention_score,
          priority,
          action: plan.action || "观察",
          plan,
          combo,
          fine,
          sector,
        }};
      }}).filter((item) => item.code && item.code !== "000000");
    }}

    function buildCandidateModels() {{
      const candidates = matrixUniverse();
      candidates.sort((a, b) => a.priority.order - b.priority.order || (b.macroScore ?? -1) - (a.macroScore ?? -1) || (b.technicalScore ?? -1) - (a.technicalScore ?? -1));
      return candidates;
    }}

    function matrixQuery() {{
      return (matrixSearch?.value || "").trim().toLowerCase();
    }}

    function matrixSearchText(item) {{
      return [
        item.code,
        item.name,
        item.board,
        item.stockType,
        item.action,
        item.priority?.label,
        item.plan?.primary_strategy,
        item.fine?.technical_reasons,
        item.combo?.matched_strategies,
      ].map(text).join(" ").toLowerCase();
    }}

    function filterMatrixCandidates(candidates) {{
      const query = matrixQuery();
      return candidates.filter((item) => {{
        const typeMatched = activeStockType === "全部" || item.stockType === activeStockType;
        const queryMatched = !query || matrixSearchText(item).includes(query);
        return typeMatched && queryMatched;
      }});
    }}

    function updateMatrixMatchCount(visible, total) {{
      if (!matrixMatchCount) return;
      matrixMatchCount.textContent = `${{visible}} / ${{total}}`;
    }}

    function selectFirstMatrixMatch() {{
      const allCandidates = buildCandidateModels();
      const matches = filterMatrixCandidates(allCandidates);
      if (matrixQuery() && matches.length) selectedCandidateCode = matches[0].code;
      renderPotentialTiming();
      renderCandidateDetail();
    }}

    function stockTypeOptions(candidates) {{
      const counts = {{}};
      for (const item of candidates) {{
        const stockType = item.stockType || "未分类";
        counts[stockType] = (counts[stockType] || 0) + 1;
      }}
      return Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "zh-Hans-CN"));
    }}

    function renderStockTypeFilters() {{
      if (!stockTypeFilters) return;
      const candidates = buildCandidateModels();
      const options = stockTypeOptions(candidates);
      const total = candidates.length;
      const buttons = [["全部", total], ...options].map(([label, count]) => {{
        const active = label === activeStockType ? " active" : "";
        return `<button type="button" class="stock-type-filter${{active}}" data-stock-type="${{escapeHtml(label)}}">${{escapeHtml(label)}} <span>${{count}}</span></button>`;
      }}).join("");
      stockTypeFilters.innerHTML = buttons;
    }}

    function selectFirstVisibleCandidate() {{
      const matches = filterMatrixCandidates(buildCandidateModels());
      selectedCandidateCode = matches[0]?.code || "";
    }}

    function renderStageFunnel() {{
      const counts = data.summary?.stage_counts || {{}};
      const maxCount = Math.max(1, ...data.stages.map((stage) => Number(counts[stage.key] ?? stage.row_count ?? 0)));
      const notes = {{
        sector_screen: "研究池，不做潜力判断",
        combo: "判断潜力底座",
        fine: "判断时机质量",
        plan: "规则计划，不是交易指令",
      }};
      stageFunnel.innerHTML = data.stages.map((stage) => {{
        const count = Number(counts[stage.key] ?? stage.row_count ?? 0);
        const width = Math.max(6, (count / maxCount) * 100);
        return `
          <div class="funnel-card">
            <div class="funnel-top"><span>${{escapeHtml(stage.title)}}</span><span class="funnel-count">${{count}}</span></div>
            <div class="funnel-bar"><span style="width:${{width.toFixed(1)}}%"></span></div>
            <div class="muted">${{escapeHtml(notes[stage.key] || "")}}</div>
          </div>
        `;
      }}).join("");
    }}

    function renderPotentialTiming() {{
      const allCandidates = buildCandidateModels();
      const candidates = filterMatrixCandidates(allCandidates);
      if (selectedCandidateCode && !candidates.some((item) => item.code === selectedCandidateCode)) {{
        selectedCandidateCode = candidates[0]?.code || "";
      }}
      updateMatrixMatchCount(candidates.length, allCandidates.length);
      const positioned = resolveMatrixPositions(candidates);
      const points = positioned.map((item) => {{
        const initial = text(item.name).slice(0, 1);
        const selected = item.code === selectedCandidateCode ? " selected" : "";
        return `
          <button type="button" class="matrix-point ${{item.priority.tone}}${{selected}}" data-code="${{escapeHtml(item.code)}}" title="${{escapeHtml(item.name)}}｜${{escapeHtml(classificationReason(item))}}｜综合关注分 ${{scoreText(item.attention_score)}}" style="left:${{item.matrixX.toFixed(1)}}%;top:${{item.matrixY.toFixed(1)}}%;--point-size:${{item.pointSize.toFixed(0)}}px;z-index:${{item.zIndex}}">${{escapeHtml(initial)}}</button>
        `;
      }}).join("");
      potentialMatrix.innerHTML = `
        <div class="quad q1"><strong>高潜力 + 好时机</strong><br>优先研究</div>
        <div class="quad q2"><strong>低潜力 + 好时机</strong><br>短线强，需复核</div>
        <div class="quad q3"><strong>低潜力 + 差时机</strong><br>暂不关注</div>
        <div class="quad q4"><strong>高潜力 + 差时机</strong><br>加入观察池</div>
        <div class="axis-x">宏观潜力分，80 为高潜力线 →</div>
        <div class="axis-y">技术时机分，75 为好时机线 →</div>
        ${{points || '<div class="empty">没有匹配的矩阵股票。</div>'}}
      `;
    }}

    function miniBar(label, value) {{
      return `
        <div class="mini">
          <span>${{helpLabel(label)}}</span>
          <div class="mini-track"><span style="width:${{percentWidth(value)}}%"></span></div>
          <strong>${{scoreText(value)}}</strong>
        </div>
      `;
    }}

    function formatTechnicalReasonText(fine) {{
      const raw = text(fine.technical_reasons || fine.technical_note || "");
      if (raw === "N/A") return "";
      const reasons = raw
        .split(/[、,，/]/)
        .map((item) => item.trim())
        .filter((item) => item && item !== "流动性达标");
      if (!reasons.length) return "";
      return `技术理由：${{reasons.join(" / ")}}`;
    }}

    function renderTechnicalReason(fine) {{
      const reasonText = formatTechnicalReasonText(fine);
      return reasonText ? `<div class="technical-reason">${{escapeHtml(reasonText)}}</div>` : "";
    }}

    function macroCommentary(combo) {{
      const overlap = numberValue(combo.overlap_score);
      const growth = numberValue(combo.growth_score);
      const quality = numberValue(combo.quality_score);
      const risk = numberValue(combo.risk_control_score);
      const strong = [
        ["多策略共振", overlap],
        ["成长", growth],
        ["质量", quality],
        ["风控", risk],
      ].filter(([, value]) => value !== null && value >= 80).map(([label]) => label);
      const weak = [
        ["多策略共振", overlap],
        ["成长", growth],
        ["质量", quality],
        ["风控", risk],
      ].filter(([, value]) => value !== null && value < 70).map(([label]) => label);
      if (strong.length && weak.length) return `宏观层面${{strong.join("、")}}较强，${{weak.join("、")}}仍需复核，适合继续跟踪基本面兑现度。`;
      if (strong.length) return `宏观层面${{strong.join("、")}}支撑较明显，当前更像具备跟踪价值的候选。`;
      if (weak.length) return `宏观层面${{weak.join("、")}}偏弱，潜力判断需要等待更多基本面或策略共振确认。`;
      return "宏观分项整体较均衡，暂未出现单一指标主导，适合结合行业景气继续观察。";
    }}

    function technicalCommentary(fine) {{
      const return20d = numberValue(fine.return_20d);
      const amountRatio = numberValue(fine.amount_ratio);
      const rsi = numberValue(fine.rsi14);
      const drawdown = numberValue(fine.max_drawdown_20d);
      const notes = [];
      if (return20d !== null) notes.push(return20d >= 0.08 ? "短期涨幅较强" : "短期涨幅尚未充分展开");
      if (amountRatio !== null) notes.push(amountRatio >= 1.2 ? "量能有放大迹象" : "量能仍偏温和");
      if (rsi !== null) notes.push(rsi >= 70 ? "RSI偏热" : rsi <= 35 ? "RSI偏低" : "RSI处于中性区间");
      if (drawdown !== null) notes.push(drawdown > -0.06 ? "回撤控制尚可" : "回撤压力需要留意");
      return notes.length ? `技术层面${{notes.join("，")}}，时机判断仍需结合下一交易日价格和成交额确认。` : "技术指标数据不足，当前时机判断以观察为主。";
    }}

    function renderCandidateDetail() {{
      const candidates = buildCandidateModels();
      const item = candidates.find((candidate) => candidate.code === selectedCandidateCode) || candidates[0];
      if (!item) {{
        detailHost.innerHTML = '<h2>单股解释</h2><div class="muted">暂无技术细筛候选。</div>';
        return;
      }}
      const plan = item.plan || {{}};
      const combo = item.combo || {{}};
      const fine = item.fine || {{}};
      detailHost.innerHTML = `
        <div class="detail-layout">
          <div class="detail-summary">
            <div class="detail-summary-main">
              <div class="detail-title">
                <span class="detail-status chip ${{item.priority.tone}}">${{escapeHtml(item.action)}}</span>
                <h2>${{escapeHtml(item.name)}} <span class="code">${{escapeHtml(item.code)}}</span></h2>
                <div class="muted">${{escapeHtml(item.board || "细筛结果股票")}} · ${{escapeHtml(item.stockType || "未分类")}}</div>
              </div>
              <div class="kpis">
                <div class="kpi" data-score-help="${{escapeHtml(metricHelp("macroScore"))}}"><strong>${{scoreText(item.macroScore)}}</strong><span>${{helpLabel("宏观潜力", "macroScore")}}</span></div>
                <div class="kpi" data-score-help="${{escapeHtml(metricHelp("technicalScore"))}}"><strong>${{scoreText(item.technicalScore)}}</strong><span>${{helpLabel("技术时机", "technicalScore")}}</span></div>
                <div class="kpi" data-score-help="${{escapeHtml(metricHelp("attention_score"))}}"><strong>${{scoreText(item.attention_score)}}</strong><span>${{helpLabel("综合关注", "attention_score")}}</span></div>
              </div>
            </div>
            <div class="detail-modules">
              <div class="detail-card explain-block">
                <h3>宏观潜力</h3>
                <div class="mini-bars">
                  ${{miniBar("多策略共振", combo.overlap_score)}}
                  ${{miniBar("成长", combo.growth_score)}}
                  ${{miniBar("质量", combo.quality_score)}}
                  ${{miniBar("风控", combo.risk_control_score)}}
                </div>
                <div class="module-commentary">${{escapeHtml(macroCommentary(combo))}}</div>
              </div>
              <div class="detail-card explain-block">
                <h3>技术时机</h3>
                <div class="mini-bars">
                  ${{miniBar("20日涨幅", numberValue(fine.return_20d) === null ? null : Number(fine.return_20d) * 100)}}
                  ${{miniBar("量能倍数", numberValue(fine.amount_ratio) === null ? null : Math.min(Number(fine.amount_ratio) * 50, 100))}}
                  ${{miniBar("RSI14", fine.rsi14)}}
                  ${{miniBar("回撤控制", numberValue(fine.max_drawdown_20d) === null ? null : Math.max(0, 100 + Number(fine.max_drawdown_20d) * 100))}}
                </div>
                <div class="module-commentary">${{escapeHtml(technicalCommentary(fine))}}</div>
                ${{renderTechnicalReason(fine)}}
              </div>
              ${{renderActionPlan(plan, item, fine)}}
            </div>
          </div>
        </div>
        <div class="decision-note" hidden>宏观分说明“为什么值得跟踪”，技术分说明“现在是否接近窗口”，操作建议只给下一交易日观察规则。</div>
      `;
    }}

    function renderPotentialTimingDashboard() {{
      renderStageFunnel();
      renderStockTypeFilters();
      renderPotentialTiming();
      renderCandidateDetail();
    }}

    function columnLabel(col) {{
      return columnLabels[col] || col;
    }}

    function columnHelp(stageKey, col) {{
      return scoreHelp[stageKey]?.[col] || scoreHelp["*"]?.[col] || "";
    }}

    function renderHeaderCell(stage, col) {{
      const help = columnHelp(stage.key, col);
      const sortMark = sortState.column === col ? (sortState.dir > 0 ? " ↑" : " ↓") : "";
      const info = help
        ? `<button type="button" class="score-info" aria-label="${{escapeHtml(columnLabel(col))}}计算规则" data-score-help="${{escapeHtml(help)}}">i</button>`
        : "";
      return `<th data-column="${{escapeHtml(col)}}"><span class="th-content"><span>${{escapeHtml(columnLabel(col))}}${{sortMark}}</span>${{info}}</span></th>`;
    }}

    function showScoreTooltip(button) {{
      const help = button.dataset.scoreHelp || "";
      if (!help) return;
      scoreTooltip.textContent = help;
      scoreTooltip.classList.add("visible");
      const rect = button.getBoundingClientRect();
      const tooltipRect = scoreTooltip.getBoundingClientRect();
      const margin = 10;
      let left = rect.left + rect.width / 2 - tooltipRect.width / 2;
      left = Math.max(margin, Math.min(left, window.innerWidth - tooltipRect.width - margin));
      let top = rect.bottom + 8;
      if (top + tooltipRect.height > window.innerHeight - margin) {{
        top = Math.max(margin, rect.top - tooltipRect.height - 8);
      }}
      scoreTooltip.style.left = `${{left}}px`;
      scoreTooltip.style.top = `${{top}}px`;
    }}

    function hideScoreTooltip() {{
      scoreTooltip.classList.remove("visible");
    }}

    function showDetailHelp(event) {{
      const target = event.target.closest("[data-score-help]");
      if (target && detailHost.contains(target)) showScoreTooltip(target);
    }}

    function hideDetailHelp(event) {{
      if (event.target.closest("[data-score-help]")) hideScoreTooltip();
    }}

    function visibleColumns(stage) {{
      const raw = stage.columns || [];
      if (stage.key === "sector_screen") {{
        return sectorVisibleColumns.filter((col) => raw.includes(col)).slice(0, 12);
      }}
      if (stage.key === "fine") {{
        return fineVisibleColumns.filter((col) => raw.includes(col));
      }}
      if (stage.key === "plan") {{
        return planVisibleColumns.filter((col) => raw.includes(col));
      }}
      if (stage.key !== "combo") return raw.slice(0, 12);
      const hasStrategyData = raw.includes("strategy_hits") || raw.includes("matched_strategies");
      return comboVisibleColumns
        .filter((col) => raw.includes(col) || (col === "strategy_summary" && hasStrategyData))
        .slice(0, 12);
    }}

    function formatNumber(value, digits = 2) {{
      const number = Number(value);
      if (!Number.isFinite(number)) return text(value);
      return number.toFixed(digits);
    }}

    function formatMarketCap(value) {{
      const number = Number(value);
      if (!Number.isFinite(number)) return text(value);
      return `${{(number / 100000000).toFixed(2)}}亿`;
    }}

    function formatAmountYi(value) {{
      const number = Number(value);
      if (!Number.isFinite(number)) return text(value);
      return `${{(number / 100000000).toFixed(2)}}亿`;
    }}

    function formatPercent(value) {{
      const number = Number(value);
      if (!Number.isFinite(number)) return text(value);
      return `${{number.toFixed(2)}}%`;
    }}

    function formatFineNumber(value) {{
      const number = Number(value);
      if (!Number.isFinite(number)) return text(value);
      return number.toFixed(2);
    }}

    function formatFinePercent(value) {{
      const number = Number(value);
      if (!Number.isFinite(number)) return text(value);
      return `${{(number * 100).toFixed(2)}}%`;
    }}

    function strategySummary(row) {{
      const hitsValue = row.strategy_hits;
      const hitsNumber = Number(hitsValue);
      return Number.isFinite(hitsNumber) ? String(Math.trunc(hitsNumber)) : text(hitsValue);
    }}

    function formatCell(stage, col, row) {{
      if (stage.key === "combo" && col === "strategy_summary") return strategySummary(row);
      const value = row[col];
      if (col === "market_cap") return formatMarketCap(value);
      if (col === "amount_20d") return formatAmountYi(value);
      if (stage.key === "sector_screen" && percentColumns.includes(col)) return formatPercent(value);
      if (stage.key === "fine" && finePercentColumns.includes(col)) return formatFinePercent(value);
      if (stage.key === "fine" && fineNumberColumns.includes(col)) return formatFineNumber(value);
      if (stage.key === "plan" && planPercentColumns.includes(col)) return formatFinePercent(value);
      if (stage.key === "plan" && planNumberColumns.includes(col)) return formatFineNumber(value);
      if (stage.key === "combo" && typeof value === "number") return formatNumber(value, 2);
      return text(value);
    }}

    function cellTitle(stage, col, row, display) {{
      if (stage.key === "sector_screen" && col === "stock_type") return text(row.stock_type_note);
      if (stage.key === "combo" && col === "strategy_summary") return text(row.matched_strategies);
      return display;
    }}

    function sortValue(row, col) {{
      if (col === "strategy_summary") return row.strategy_hits;
      return row[col];
    }}

    function currentStage() {{
      return data.stages.find((stage) => stage.key === activeStage) || data.stages[0];
    }}

    function filteredRows(stage) {{
      const query = search.value.trim().toLowerCase();
      let rows = [...(stage?.rows || [])];
      if (query) {{
        rows = rows.filter((row) => Object.values(row).join(" ").toLowerCase().includes(query));
      }}
      if (sortState.column) {{
        const col = sortState.column;
        const dir = sortState.dir;
        rows.sort((a, b) => {{
          const av = sortValue(a, col);
          const bv = sortValue(b, col);
          const an = Number(av);
          const bn = Number(bv);
          if (!Number.isNaN(an) && !Number.isNaN(bn)) return (an - bn) * dir;
          return text(av).localeCompare(text(bv), "zh-Hans-CN") * dir;
        }});
      }}
      return rows;
    }}

    function renderStage() {{
      const stage = currentStage();
      if (!stage) return;
      stageTitle.textContent = stage.title;
      const rows = filteredRows(stage);
      visibleCount.textContent = `${{rows.length}} / ${{stage.row_count}} 条`;
      if (!stage.columns.length || !rows.length) {{
        tableHost.innerHTML = '<div class="empty">当前阶段没有匹配数据。</div>';
        return;
      }}
      const columns = visibleColumns(stage);
      const header = columns.map((col) => renderHeaderCell(stage, col)).join("");
      const body = rows.map((row) => {{
        const code = text(row.code || "");
        const cells = columns.map((col) => {{
          const display = formatCell(stage, col, row);
          const title = cellTitle(stage, col, row, display);
          return `<td title="${{escapeHtml(title)}}">${{escapeHtml(display)}}</td>`;
        }}).join("");
        return `<tr data-code="${{escapeHtml(code)}}">${{cells}}</tr>`;
      }}).join("");
      tableHost.innerHTML = `<table><thead><tr>${{header}}</tr></thead><tbody>${{body}}</tbody></table>`;
    }}

    function renderTrace(code) {{
      const steps = data.traces[code] || [];
      if (!steps.length) {{
        traceHost.innerHTML = '<h2>阶段轨迹</h2><div class="muted">该股票没有跨阶段轨迹。</div>';
        return;
      }}
      const name = steps.find((step) => step.name)?.name || code;
      const html = steps.map((step) => `
        <div class="trace-step">
          <div><span class="badge">${{escapeHtml(step.title)}}</span></div>
          <div>
            <strong>${{escapeHtml(step.label)}}</strong>
            <div class="muted mono">${{escapeHtml(code)}}</div>
          </div>
        </div>
      `).join("");
      traceHost.innerHTML = `<h2>${{escapeHtml(name)}} 的阶段轨迹</h2>${{html}}`;
    }}

    document.querySelectorAll(".tab").forEach((btn) => {{
      btn.addEventListener("click", () => {{
        document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
        btn.classList.add("active");
        activeStage = btn.dataset.stageKey;
        sortState = {{ column: "", dir: 1 }};
        renderStage();
      }});
    }});

    potentialMatrix.addEventListener("click", (event) => {{
      const point = event.target.closest(".matrix-point[data-code]");
      if (!point) return;
      selectedCandidateCode = point.dataset.code;
      renderPotentialTiming();
      renderCandidateDetail();
    }});

    matrixSearch?.addEventListener("input", selectFirstMatrixMatch);
    stockTypeFilters?.addEventListener("click", (event) => {{
      const button = event.target.closest(".stock-type-filter[data-stock-type]");
      if (!button) return;
      activeStockType = button.dataset.stockType || "全部";
      selectFirstVisibleCandidate();
      renderStockTypeFilters();
      renderPotentialTiming();
      renderCandidateDetail();
    }});
    search.addEventListener("input", renderStage);
    tableHost.addEventListener("mouseover", (event) => {{
      const btn = event.target.closest(".score-info");
      if (btn) showScoreTooltip(btn);
    }});
    tableHost.addEventListener("mouseout", (event) => {{
      if (event.target.closest(".score-info")) hideScoreTooltip();
    }});
    tableHost.addEventListener("focusin", (event) => {{
      const btn = event.target.closest(".score-info");
      if (btn) showScoreTooltip(btn);
    }});
    tableHost.addEventListener("focusout", (event) => {{
      if (event.target.closest(".score-info")) hideScoreTooltip();
    }});
    detailHost.addEventListener("mouseover", showDetailHelp);
    detailHost.addEventListener("mouseout", hideDetailHelp);
    detailHost.addEventListener("focusin", showDetailHelp);
    detailHost.addEventListener("focusout", hideDetailHelp);
    window.addEventListener("scroll", hideScoreTooltip, true);
    window.addEventListener("resize", hideScoreTooltip);
    tableHost.addEventListener("click", (event) => {{
      if (event.target.closest(".score-info")) return;
      const th = event.target.closest("th");
      if (th) {{
        const column = th.dataset.column;
        if (sortState.column === column) sortState.dir *= -1;
        else sortState = {{ column, dir: 1 }};
        renderStage();
        return;
      }}
      const tr = event.target.closest("tr[data-code]");
      if (tr) renderTrace(tr.dataset.code);
    }});

    renderPotentialTimingDashboard();
    renderStage();
  </script>
</body>
</html>
"""
