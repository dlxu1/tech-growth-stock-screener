"""Renderer for the dashboardv2 industry-thesis view.

The goal is to reuse the existing dashboard data model while recasting the UI
around:

    行业主线 -> 主线股票池 -> 龙头收敛 -> 技术确认 -> 每日复盘

This module intentionally keeps the model transformation lightweight and local
to the renderer so the v1 dashboard pipeline remains unchanged.
"""

from __future__ import annotations

import json
from html import escape
from typing import Any

import pandas as pd

from dashboard.industry_mainline import build_industry_mainlines


def _num(value: Any, digits: int = 2) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.{digits}f}"
    except Exception:
        return "N/A"


def _pct(value: Any, digits: int = 2) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        number = float(value)
        if abs(number) <= 1:
            number *= 100
        return f"{number:.{digits}f}%"
    except Exception:
        return "N/A"


def _yi(value: Any, digits: int = 1) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value) / 100000000:.{digits}f} 亿"
    except Exception:
        return "N/A"


def _rows_to_df(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _stage_rows(model: dict, key: str) -> list[dict]:
    for stage in model.get("stages", []):
        if stage.get("key") == key:
            return list(stage.get("rows") or [])
    return []


def _numeric_group(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def _merge_row_context(row: dict, fine_map: dict[str, dict], plan_map: dict[str, dict]) -> dict:
    code = str(row.get("code") or "").zfill(6)
    merged = {**row, **fine_map.get(code, {}), **plan_map.get(code, {})}
    merged["code"] = code
    return merged


def _leader_reason(row: dict) -> str:
    reasons: list[str] = []
    if pd.notna(row.get("market_cap")) and float(row.get("market_cap") or 0) > 0:
        reasons.append("市值靠前")
    if pd.notna(row.get("return_60d")) and float(row.get("return_60d") or 0) > 0:
        reasons.append("近60日强势")
    if pd.notna(row.get("amount_20d")) and float(row.get("amount_20d") or 0) > 0:
        reasons.append("成交额有承接")
    rev = float(row.get("revenue_yoy") or 0) if pd.notna(row.get("revenue_yoy")) else 0.0
    prof = float(row.get("profit_yoy") or 0) if pd.notna(row.get("profit_yoy")) else 0.0
    if rev > 0 and prof > 0:
        reasons.append("营收利润双增")
    if pd.notna(row.get("max_drawdown_252d")) and float(row.get("max_drawdown_252d") or 0) > -0.2:
        reasons.append("回撤可控")
    return "、".join(reasons) if reasons else "作为主线内候选观察"


def _mainline_reason(row: pd.Series) -> str:
    reasons = [
        f"缓存样本涨幅 {_pct(row.get('avg_return_60d'))}",
        f"上涨家数占比 {_pct(row.get('positive_ratio'))}",
        f"成交额 {_yi(row.get('avg_amount_20d'))}",
    ]
    if pd.notna(row.get("avg_revenue_yoy")) or pd.notna(row.get("avg_profit_yoy")):
        reasons.append(
            f"营收/利润均值 {_pct(row.get('avg_revenue_yoy'))} / {_pct(row.get('avg_profit_yoy'))}"
        )
    return "；".join(reasons)


def _leader_score_frame(group: pd.DataFrame) -> pd.DataFrame:
    frame = _numeric_group(
        group,
        ["market_cap", "return_60d", "amount_20d", "revenue_yoy", "profit_yoy", "max_drawdown_252d"],
    ).copy()
    if frame.empty:
        return frame
    market_rank = frame["market_cap"].rank(pct=True, ascending=True).fillna(0.5)
    return_rank = frame["return_60d"].rank(pct=True, ascending=True).fillna(0.5)
    amount_rank = frame["amount_20d"].rank(pct=True, ascending=True).fillna(0.5)
    growth_signal = (frame["revenue_yoy"].clip(lower=0).fillna(0) + frame["profit_yoy"].clip(lower=0).fillna(0)) / 2
    growth_rank = growth_signal.rank(pct=True, ascending=True).fillna(0.5)
    risk_rank = (-frame["max_drawdown_252d"].abs().fillna(0)).rank(pct=True, ascending=True).fillna(0.5)
    frame["leader_score"] = (
        market_rank * 0.30
        + return_rank * 0.25
        + amount_rank * 0.20
        + growth_rank * 0.15
        + risk_rank * 0.10
    )
    return frame


def _build_mainline_objects(model: dict) -> list[dict]:
    summary = model.get("summary") or {}
    sector_rows = _stage_rows(model, "sector_screen")
    fine_rows = _stage_rows(model, "fine")
    plan_rows = _stage_rows(model, "plan")
    sector_df = _rows_to_df(sector_rows)
    if sector_df.empty:
        return []
    pool_source_label = str((summary.get("industry_pool") or {}).get("source_label") or summary.get("industry_mainline_source_label") or "缓存样本代理")
    pool_source_note = str((summary.get("industry_pool") or {}).get("note") or summary.get("selected_industry_note") or "")
    return build_industry_mainlines(sector_df, fine_rows, plan_rows, pool_source_label=pool_source_label, pool_source_note=pool_source_note)


def _build_context(model: dict) -> dict[str, Any]:
    summary = dict(model.get("summary") or {})
    health = summary.get("health") or {}
    mainlines = _build_mainline_objects(model)
    selected = mainlines[0]["board_name"] if mainlines else ""
    summary["dashboard_variant"] = "v2"
    summary["selected_industry"] = selected
    summary["industry_mainline_count"] = len(mainlines)
    summary["industry_mainlines"] = mainlines
    summary["v2_note"] = "行业主线数据基于当前缓存可得的板块样本和成分股表现估算；若行业指数、资金流或新闻催化缺失，展示会保守降级，不编造上涨原因。"
    return {
        "summary": summary,
        "health": health,
        "stages": model.get("stages", []),
        "industry_mainlines": mainlines,
        "selected_industry": selected,
    }


def _json_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str).replace("</", "<\\/")


def render_dashboard_v2_html(model: dict) -> str:
    """Render the dashboardv2 industry-thesis page."""

    context = _build_context(model)
    summary = context["summary"]
    mainlines = context["industry_mainlines"]
    selected = context["selected_industry"]
    health = context["health"] or {}
    data_json = _json_script(context)
    strategy_title = summary.get("strategy_title") or "潜力股组合评分"
    weight_version = summary.get("weight_version") or ""
    if not weight_version:
        weight_version = "牛市动量版"
    latest_trade_date = ((health.get("freshness") or {}).get("latest_trade_date")) or summary.get("as_of_date") or "N/A"
    health_score = health.get("health_score", "N/A")
    variant_note = summary.get("v2_note") or ""

    cards = []
    for index, item in enumerate(mainlines):
        active = " active" if index == 0 else ""
        cards.append(
            f"""
            <button class="industry-card{active}" data-index="{index}" type="button">
              <div class="industry-head">
                <strong>{escape(str(item.get('board_name') or '未分类'))}</strong>
                <span>{_pct(item.get('avg_return_60d'))}</span>
              </div>
              <div class="industry-meta">
                {escape(str(item.get('stock_count') or 0))} 只 · 成交额 {_yi(item.get('avg_amount_20d'))} ·
                上涨家数占比 {_pct(item.get('positive_ratio'))} · {escape(str(item.get('pool_source_label') or '样本代理'))}
              </div>
              <div class="industry-reason">{escape(str(item.get('mainline_reason') or ''))}</div>
            </button>
            """
        )
    cards_html = "\n".join(cards) if cards else '<div class="empty">暂无可展示行业主线。</div>'

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>dashboardv2 - 行业主线选股</title>
  <style>
    :root {{
      --bg: #f4f6f8;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #667085;
      --line: #dde3ea;
      --soft: #fbfcfd;
      --green: #127a57;
      --blue: #1d4ed8;
      --amber: #a16207;
      --red: #b42318;
      --shadow: 0 14px 34px rgba(23, 32, 51, 0.08);
    }}

    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); color: var(--ink); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .shell {{ min-height: 100vh; }}
    main {{ padding: 22px; min-width: 0; max-width: 1600px; margin: 0 auto; }}
    .top {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 16px; align-items: start; margin-bottom: 16px; }}
    h1 {{ margin: 0 0 6px; font-size: 24px; line-height: 1.2; letter-spacing: 0; }}
    .sub {{ margin: 0; color: var(--muted); font-size: 14px; line-height: 1.55; }}
    .chips {{ display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }}
    .chip {{ display: inline-flex; align-items: center; gap: 6px; padding: 8px 10px; border-radius: 6px; border: 1px solid var(--line); background: var(--panel); color: #344054; font-size: 13px; white-space: nowrap; }}
    .chip.blue {{ color: var(--blue); }}
    .chip.green {{ color: var(--green); }}
    .chip.amber {{ color: var(--amber); }}
    .pipeline {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 16px; }}
    .step {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 13px; box-shadow: 0 8px 22px rgba(23, 32, 51, 0.05); }}
    .step.active {{ border-color: #8fb4ff; background: #f1f6ff; }}
    .step strong {{ display: block; font-size: 14px; margin-bottom: 4px; }}
    .step span {{ display: block; color: var(--muted); font-size: 12px; line-height: 1.45; }}
    .workspace {{ display: grid; grid-template-columns: minmax(280px, 0.86fr) minmax(390px, 1fr) minmax(360px, 0.92fr); gap: 16px; align-items: start; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; box-shadow: var(--shadow); overflow: hidden; }}
    .panel-head {{ padding: 15px 16px 12px; border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; gap: 12px; align-items: center; }}
    .title {{ font-weight: 760; font-size: 16px; }}
    .note {{ color: var(--muted); font-size: 12px; margin-top: 3px; line-height: 1.45; }}
    .body {{ padding: 16px; }}
    .industry-list {{ display: grid; gap: 10px; max-height: 780px; overflow: auto; padding-right: 4px; }}
    .industry-card {{ width: 100%; text-align: left; border: 1px solid var(--line); border-radius: 8px; background: #fbfcfd; padding: 12px; cursor: pointer; }}
    .industry-card.active {{ border-color: #8fb4ff; background: #f1f6ff; }}
    .industry-head {{ display: flex; justify-content: space-between; gap: 10px; align-items: baseline; }}
    .industry-head strong {{ font-size: 15px; }}
    .industry-head span {{ font-size: 20px; font-weight: 760; color: var(--red); }}
    .industry-meta {{ font-size: 12px; color: var(--muted); margin-top: 5px; line-height: 1.45; }}
    .industry-reason {{ font-size: 12px; color: #344054; margin-top: 8px; line-height: 1.5; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-bottom: 14px; }}
    .summary-box {{ border: 1px solid var(--line); border-radius: 8px; padding: 10px; background: #fff; }}
    .summary-box strong {{ display: block; font-size: 18px; margin-bottom: 3px; }}
    .summary-box span {{ color: var(--muted); font-size: 12px; }}
    .table-wrap {{ border: 1px solid var(--line); border-radius: 8px; overflow: hidden; background: #fff; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 10px 11px; border-bottom: 1px solid #eef1f4; text-align: left; vertical-align: middle; }}
    th {{ color: var(--muted); background: #fbfcfd; font-size: 12px; font-weight: 650; }}
    tr:last-child td {{ border-bottom: none; }}
    .tag {{ display: inline-flex; align-items: center; padding: 4px 6px; border-radius: 5px; border: 1px solid var(--line); background: #fafafa; font-size: 12px; white-space: nowrap; }}
    .tag.blue {{ color: var(--blue); border-color: #b9cffc; background: #eef4ff; }}
    .tag.green {{ color: var(--green); border-color: #a8d8c8; background: #eefaf5; }}
    .tag.amber {{ color: var(--amber); border-color: #efcf8a; background: #fff7e6; }}
    .tag.red {{ color: var(--red); border-color: #f4b8b2; background: #fff0ee; }}
    .stack {{ display: grid; gap: 10px; }}
    .stack-card {{ border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: var(--soft); }}
    .stack-card h3 {{ margin: 0 0 8px; font-size: 14px; }}
    .stack-card p {{ margin: 0; color: #344054; font-size: 13px; line-height: 1.55; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }}
    .metric {{ border: 1px solid var(--line); border-radius: 8px; padding: 10px; background: #fff; }}
    .metric strong {{ display: block; font-size: 18px; margin-bottom: 3px; }}
    .metric span {{ color: var(--muted); font-size: 12px; line-height: 1.45; }}
    .review {{ margin-top: 14px; border-top: 1px solid var(--line); padding-top: 14px; }}
    .review-row {{ display: grid; grid-template-columns: 92px 1fr auto; gap: 12px; padding: 10px 0; border-bottom: 1px solid #eef1f4; align-items: center; }}
    .review-row:last-child {{ border-bottom: none; }}
    .time {{ color: var(--muted); font-size: 12px; }}
    .action {{ font-size: 13px; color: #344054; line-height: 1.45; }}
    .foot {{ margin-top: 16px; padding: 14px 16px; background: #eef4ff; border: 1px solid #b9cffc; border-radius: 8px; color: #12346f; font-size: 14px; line-height: 1.55; }}
    .empty {{ color: var(--muted); padding: 14px; }}
    @media (max-width: 1280px) {{
      .workspace {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 760px) {{
      main {{ padding: 14px; }}
      .top {{ grid-template-columns: 1fr; }}
      .chips {{ justify-content: flex-start; }}
      .pipeline {{ grid-template-columns: 1fr 1fr; }}
      .summary-grid, .metric-grid {{ grid-template-columns: 1fr; }}
      .review-row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <main>
      <div class="top">
          <div>
            <h1>把沪深300当基准池，把行业主线当方向盘</h1>
            <p class="sub">v2 只强调少数主线和少数龙头。行业排序复用当前缓存可得的板块样本，技术面只做最后确认。</p>
          </div>
          <div class="chips">
            <div class="chip green">数据健康 {escape(str(health_score))}/100</div>
            <div class="chip blue">{escape(str(strategy_title))}</div>
            <div class="chip amber">{escape(str(weight_version))}</div>
            <div class="chip">最新行情日 {escape(str(latest_trade_date))}</div>
            <div class="chip">暂停更新</div>
          </div>
      </div>

      <div class="pipeline">
        <div class="step active"><strong>1. 行业先行</strong><span>先看行业是否成立，再决定研究方向。</span></div>
        <div class="step active"><strong>2. 主线股票池</strong><span>只保留当前主线行业里的少数候选。</span></div>
        <div class="step active"><strong>3. 龙头收敛</strong><span>把高潜力重定位为龙头排序，不回到黑盒分数。</span></div>
        <div class="step active"><strong>4. 技术确认</strong><span>只对龙头看能不能下手。</span></div>
        <div class="step"><strong>5. 每日复盘</strong><span>每天只跟踪 1-3 只核心股票。</span></div>
      </div>

      <div class="workspace">
        <section class="panel">
          <div class="panel-head">
            <div>
              <div class="title">行业主线榜</div>
              <div class="note">按缓存样本涨幅、扩散度与成交额估算行业主线强度。</div>
            </div>
            <span class="chip">基于缓存样本</span>
          </div>
          <div class="body">
            <div class="industry-list" id="industryList">
              {cards_html}
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div>
              <div class="title" id="selectedTitle">{escape(selected or '暂无主线')}</div>
              <div class="note" id="selectedNote">{escape(variant_note)}</div>
            </div>
            <span class="tag green" id="selectedRank">{escape('主线 #1' if mainlines else '无数据')}</span>
          </div>
          <div class="body">
            <div class="summary-grid" id="selectedSummary"></div>

            <div class="stack">
              <div class="stack-card">
                <h3>上涨原因</h3>
                <p id="selectedReason">点击左侧行业查看原因。</p>
              </div>
              <div class="stack-card">
                <h3>主线股票池</h3>
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>股票</th>
                        <th>主线理由</th>
                        <th>技术确认</th>
                      </tr>
                    </thead>
                    <tbody id="stockPoolBody"></tbody>
                  </table>
                </div>
              </div>
              <div class="stack-card">
                <h3>龙头证据卡</h3>
                <div class="metric-grid" id="leaderMetrics"></div>
              </div>
              <div class="stack-card">
                <h3>技术确认</h3>
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>股票</th>
                        <th>结论</th>
                        <th>关键价位</th>
                        <th>风险提醒</th>
                      </tr>
                    </thead>
                    <tbody id="technicalBody"></tbody>
                  </table>
                </div>
              </div>
              <div class="stack-card">
                <h3>每日复盘</h3>
                <div class="review" id="reviewBody"></div>
              </div>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div>
              <div class="title">复盘节奏</div>
              <div class="note">v2 只保留少数主线与龙头，减少全天盯盘感。</div>
            </div>
          </div>
          <div class="body">
            <div class="stack">
              <div class="stack-card">
                <h3>行业层</h3>
                <p>看近30日主线是否继续跑赢、上涨家数是否仍在扩散、成交额是否维持。</p>
              </div>
              <div class="stack-card">
                <h3>龙头层</h3>
                <p>只跟踪 1-3 只龙头，优先看市值、业绩、资金承接和相对强弱。</p>
              </div>
              <div class="stack-card">
                <h3>技术层</h3>
                <p>只判断：观察、等待回踩、等待放量确认、提醒触发、放弃。</p>
              </div>
              <div class="stack-card">
                <h3>数据口径</h3>
                <p>这版 UI 复用当前缓存和现有技术分析结果；如果板块历史数据缺失，会保守降级。</p>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div class="foot">{escape(variant_note)}</div>
    </main>
  </div>

  <script id="dashboardV2Data" type="application/json">{data_json}</script>
  <script>
    const payload = JSON.parse(document.getElementById("dashboardV2Data").textContent);
    const mainlines = payload.industry_mainlines || [];
    const fineRows = new Map((payload.stages || []).find(stage => stage.key === "fine")?.rows?.map(row => [String(row.code || "").padStart(6, "0"), row]) || []);
    const planRows = new Map((payload.stages || []).find(stage => stage.key === "plan")?.rows?.map(row => [String(row.code || "").padStart(6, "0"), row]) || []);
    const list = document.getElementById("industryList");
    const title = document.getElementById("selectedTitle");
    const note = document.getElementById("selectedNote");
    const rank = document.getElementById("selectedRank");
    const reason = document.getElementById("selectedReason");
    const summary = document.getElementById("selectedSummary");
    const stockPoolBody = document.getElementById("stockPoolBody");
    const leaderMetrics = document.getElementById("leaderMetrics");
    const technicalBody = document.getElementById("technicalBody");
    const reviewBody = document.getElementById("reviewBody");

    function fmtPct(value, digits = 2) {{
      const n = Number(value);
      if (!Number.isFinite(n)) return "N/A";
      const scaled = Math.abs(n) <= 1 ? n * 100 : n;
      return `${{scaled.toFixed(digits)}}%`;
    }}

    function fmtYi(value) {{
      const n = Number(value);
      if (!Number.isFinite(n)) return "N/A";
      return `${{(n / 100000000).toFixed(1)}} 亿`;
    }}

    function byCodeMap(rows) {{
      const out = new Map();
      (rows || []).forEach(row => out.set(String(row.code || "").padStart(6, "0"), row));
      return out;
    }}

    function mergeRow(row) {{
      const code = String(row.code || "").padStart(6, "0");
      return {{ ...row, ...fineRows.get(code), ...planRows.get(code), code }};
    }}

    function render(index) {{
      const item = mainlines[index];
      if (!item) return;
      [...document.querySelectorAll(".industry-card")].forEach((el, idx) => el.classList.toggle("active", idx === index));
      title.textContent = item.board_name || "未分类";
      note.textContent = item.mainline_reason || payload.summary?.v2_note || "";
      rank.textContent = `主线 #${{item.rank || index + 1}}`;
      reason.textContent = item.mainline_reason || "暂无原因";
      summary.innerHTML = `
        <div class="summary-box"><strong>${{item.stock_count || 0}}</strong><span>股票数量</span></div>
        <div class="summary-box"><strong>${{fmtPct(item.avg_return_60d)}} </strong><span>缓存样本涨幅</span></div>
        <div class="summary-box"><strong>${{fmtYi(item.avg_amount_20d)}}</strong><span>平均成交额</span></div>
      `;

      stockPoolBody.innerHTML = (item.stock_pool || []).slice(0, 8).map(row => {{
        const merged = mergeRow(row);
        return `
          <tr>
            <td><strong>${{merged.name || merged.code}}</strong><br><span class="note">${{merged.code || ""}}</span></td>
            <td>${{merged.leader_reason || "主线内候选"}}</td>
            <td>${{merged.action || merged.technical_reasons || "待确认"}}</td>
          </tr>
        `;
      }}).join("") || '<tr><td colspan="3" class="empty">暂无主线股票池。</td></tr>';

      const leaders = (item.leaders || []).slice(0, 3).map(row => mergeRow(row));
      leaderMetrics.innerHTML = leaders.map(row => `
        <div class="metric">
          <strong>${{row.name || row.code}}</strong>
          <span>${{row.leader_reason || "主线龙头"}}<br>技术：${{row.action || row.technical_reasons || "待确认"}}</span>
        </div>
      `).join("") || '<div class="empty">暂无龙头数据。</div>';

      technicalBody.innerHTML = leaders.map(row => {{
        const plan = row.action || row.primary_horizon || "观察";
        const price = [row.planned_entry, row.initial_stop].filter(v => v !== undefined && v !== null && v !== "").length
          ? `买点 ${{row.planned_entry ?? "N/A"}} / 止损 ${{row.initial_stop ?? "N/A"}}`
          : "计划待补充";
        const risk = row.horizon_data_note || row.technical_note || row.risk_flags || "证据不足，需人工复核";
        return `
          <tr>
            <td><strong>${{row.name || row.code}}</strong><br><span class="note">${{row.code || ""}}</span></td>
            <td>${{plan}}</td>
            <td>${{price}}</td>
            <td>${{risk}}</td>
          </tr>
        `;
      }}).join("") || '<tr><td colspan="4" class="empty">暂无技术确认数据。</td></tr>';

      reviewBody.innerHTML = leaders.map((row, idx) => `
        <div class="review-row">
          <div class="time">第 ${{idx + 1}} 只</div>
          <div class="action">${{row.name || row.code}}：${{row.action || row.primary_horizon || "观察"}}；${{row.horizon_reason || row.technical_reasons || "等待技术确认"}}</div>
          <span class="tag ${{row.action ? 'green' : 'amber'}}">${{row.action || '观察'}}</span>
        </div>
      `).join("") || '<div class="empty">暂无每日复盘队列。</div>';
    }}

    [...document.querySelectorAll(".industry-card")].forEach((el, idx) => {{
      el.addEventListener("click", () => render(idx));
    }});

    if (mainlines.length) {{
      render(0);
    }}
  </script>
</body>
</html>
"""
