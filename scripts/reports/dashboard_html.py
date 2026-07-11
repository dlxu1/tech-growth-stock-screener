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
    "coarse_strategy": "粗筛策略",
    "coarse_strategy_title": "策略名称",
    "coarse_score": "粗筛分",
    "coarse_reason": "入选逻辑",
    "technical_score": "技术分",
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
    "entry_price": "计划买入价",
    "stop_price": "止损价",
    "target_price": "目标价",
    "position_size": "建议仓位",
    "portfolio_action": "组合动作",
    "budget_status": "预算状态",
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
            "技术分 = 趋势分 × 30 + 动量分 × 20 + 量能分 × 20 + 突破分 × 15 + "
            "风险分 × 10 + 流动性分 × 5。趋势看均线多头和20日均线上行；动量看20日涨幅、MACD和RSI；"
            "量能看成交额放大、当日上涨和20日成交额门槛；突破看20日新高附近和收盘位置；风险看20日回撤和ATR。"
        ),
        "coarse_score": "粗筛分 = 进入技术细筛前的宏观/粗筛阶段得分，用作技术分相同或接近时的次级排序依据。",
    },
}


def render_dashboard_html(model: dict) -> str:
    """Render a self-contained dashboard document."""

    summary = model.get("summary", {})
    stage_counts = summary.get("stage_counts", {})
    action_counts = summary.get("action_counts", {})
    stages = model.get("stages", [])
    total_rows = sum(int(value or 0) for value in stage_counts.values())
    tabs = "\n".join(
        f'<button type="button" class="tab{" active" if i == 0 else ""}" data-stage-key="{escape(stage["key"])}">{escape(stage["title"])} <span>{int(stage.get("row_count") or 0)}</span></button>'
        for i, stage in enumerate(stages)
    )
    action_bits = "；".join(f"{key} {value}" for key, value in action_counts.items()) or "暂无最终动作"
    data_json = _json_script(model)
    column_labels_json = _json_script(COLUMN_LABELS)
    score_help_json = _json_script(SCORE_HELP)
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
      padding: 24px 0 44px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: flex-end;
      margin-bottom: 16px;
    }}
    h1, h2 {{ margin: 0; letter-spacing: 0; }}
    h1 {{ font-size: 28px; }}
    h2 {{ font-size: 18px; }}
    .muted {{ color: var(--muted); }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin: 14px 0;
    }}
    .metric, section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .metric {{ padding: 12px 14px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 13px; }}
    .metric strong {{ display: block; margin-top: 4px; font-size: 20px; font-weight: 500; }}
    .toolbar {{
      display: flex;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
      margin: 16px 0 12px;
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
      header {{ display: block; }}
      h1 {{ font-size: 23px; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .stage-grid {{ grid-template-columns: 1fr; }}
      .toolbar {{ align-items: stretch; }}
      input[type="search"] {{ width: 100%; }}
    }}
    @media (max-width: 520px) {{
      .metrics {{ grid-template-columns: 1fr; }}
      th, td {{ max-width: 150px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>选股流程交互仪表盘</h1>
        <div class="muted">一次运行串联板块筛选、宏观粗筛、技术细筛、操作计划和个人配置。</div>
      </div>
      <div class="muted">离线 HTML 快照</div>
    </header>
    <div class="metrics">
      {_stat("总资金", _money(summary.get("capital")))}
      {_stat("ETF 核心仓", _money(summary.get("core_etf_budget")))}
      {_stat("个股卫星仓", _money(summary.get("satellite_stock_budget")))}
      {_stat("总阶段行数", f"{total_rows} 条")}
    </div>
    <div class="metrics">
      {_stat("现金预留", _money(summary.get("cash_reserve")))}
      {_stat("最终动作", escape(action_bits))}
      {_stat("阶段数量", f"{len(stages)} 个")}
      {_stat("可追踪股票", f"{len(model.get("traces", {}))} 只")}
    </div>
    <div class="toolbar">
      <div class="tabs">{tabs}</div>
      <input id="globalSearch" type="search" placeholder="搜索代码、名称、行业、动作">
    </div>
    <section>
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
    const sectorVisibleColumns = ["code","name","board_name","market_cap","revenue_yoy","profit_yoy","amount_20d","return_60d","max_drawdown_252d","risk_flags","data_note"];
    const percentColumns = ["revenue_yoy","profit_yoy","return_60d","max_drawdown_252d"];
    const fineHiddenColumns = ["coarse_strategies"];
    const finePercentColumns = ["change_pct","return_20d","return_60d","max_drawdown_20d"];
    const fineNumberColumns = ["coarse_score","technical_score","close","amount_ratio","ma5","ma10","ma20","macd_hist","rsi14"];
    const data = window.DASHBOARD_DATA;
    const search = document.getElementById("globalSearch");
    const tableHost = document.getElementById("tableHost");
    const traceHost = document.getElementById("traceHost");
    const stageTitle = document.getElementById("stageTitle");
    const visibleCount = document.getElementById("visibleCount");
    const scoreTooltip = document.getElementById("scoreTooltip");
    let activeStage = data.stages[0]?.key || "";
    let sortState = {{ column: "", dir: 1 }};

    function text(value) {{
      if (value === null || value === undefined || value === "") return "N/A";
      return String(value);
    }}

    function escapeHtml(value) {{
      return text(value).replace(/[&<>"']/g, (ch) => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[ch]));
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

    function visibleColumns(stage) {{
      const raw = stage.columns || [];
      if (stage.key === "sector_screen") {{
        return sectorVisibleColumns.filter((col) => raw.includes(col)).slice(0, 12);
      }}
      if (stage.key === "fine") {{
        return raw.filter((col) => !fineHiddenColumns.includes(col)).slice(0, 12);
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
      if (stage.key === "combo" && typeof value === "number") return formatNumber(value, 2);
      return text(value);
    }}

    function cellTitle(stage, col, row, display) {{
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

    renderStage();
  </script>
</body>
</html>
"""
