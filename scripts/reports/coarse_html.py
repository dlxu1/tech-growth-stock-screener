"""Static HTML rendering for coarse and combo screening outputs."""

from __future__ import annotations

from html import escape

import pandas as pd


def _text(value) -> str:
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return escape(str(value))


def _num(value, digits: int = 1) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.{digits}f}"
    except Exception:
        return "N/A"


def _pct(value) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.2f}%"
    except Exception:
        return "N/A"


def _yi(value) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value) / 100000000:.1f} 亿"
    except Exception:
        return "N/A"


def _metric(label: str, value: str) -> str:
    return f"""
      <div class="metric">
        <span>{escape(label)}</span>
        <strong>{escape(value)}</strong>
      </div>
    """


def _page(title: str, meta: dict, body: str, row_count: int) -> str:
    metrics = [
        _metric("输出股票", f"{row_count} 条"),
        _metric("财报口径", str(meta.get("report_date") or "N/A")),
        _metric("候选池", f"{meta.get('tech_universe', 'N/A')} 只"),
        _metric("板块数", f"{meta.get('tech_boards', 'N/A')}"),
    ]
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f7f8;
      --panel: #fff;
      --text: #172033;
      --muted: #687386;
      --line: #dce3ea;
      --accent: #1f8a70;
      --warn: #bf5b30;
      --track: #e8edf2;
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
      width: min(1280px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 44px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 20px;
      margin-bottom: 18px;
    }}
    h1, h2, h3 {{ margin: 0; letter-spacing: 0; }}
    h1 {{ font-size: 30px; }}
    h2 {{ font-size: 18px; margin-bottom: 14px; }}
    h3 {{ font-size: 15px; margin-bottom: 8px; }}
    .muted {{ color: var(--muted); }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 18px 0;
    }}
    .metric, section, .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .metric {{ padding: 14px 16px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 13px; }}
    .metric strong {{ display: block; margin-top: 4px; font-size: 22px; }}
    section {{ padding: 18px; margin-bottom: 14px; overflow: hidden; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 14px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }}
    .card {{ padding: 12px; }}
    .card strong {{ display: block; font-size: 18px; margin-top: 4px; }}
    .bar-row {{
      display: grid;
      grid-template-columns: 150px minmax(140px, 1fr) 64px;
      gap: 10px;
      align-items: center;
      margin: 10px 0;
    }}
    .bar-label, .bar-value {{ color: var(--muted); font-size: 13px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .bar-track {{ height: 10px; background: var(--track); border-radius: 999px; overflow: hidden; }}
    .bar-fill {{ height: 100%; background: var(--accent); border-radius: inherit; }}
    .bar-fill.warn {{ background: var(--warn); }}
    .table-tools {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 12px;
    }}
    input[type="search"] {{
      width: min(460px, 100%);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 11px;
      font-size: 14px;
      background: #fff;
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 9px 8px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; background: #fafbfc; position: sticky; top: 0; }}
    tbody tr:hover {{ background: #f8fafb; }}
    .tag {{
      display: inline-block;
      margin: 0 4px 4px 0;
      padding: 2px 6px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }}
    @media (max-width: 920px) {{
      header {{ display: block; }}
      .metrics, .grid, .cards {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 116px minmax(90px, 1fr) 54px; }}
      main {{ width: min(100% - 20px, 1280px); padding-top: 18px; }}
      h1 {{ font-size: 24px; }}
      section {{ padding: 14px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>{escape(title)}</h1>
        <div class="muted">来源：{escape(str(meta.get("universe_source") or ""))}；行情：{escape(str(meta.get("quote_source") or ""))}</div>
      </div>
      <div class="muted">本地 SQLite 可视化</div>
    </header>
    <div class="metrics">{"".join(metrics)}</div>
    {body}
  </main>
  <script>
    const input = document.getElementById("filterInput");
    const table = document.getElementById("screenTable");
    const rowCount = document.getElementById("rowCount");
    if (input && table && rowCount) {{
      const rows = Array.from(table.querySelectorAll("tbody tr"));
      input.addEventListener("input", () => {{
        const query = input.value.trim().toLowerCase();
        let visible = 0;
        for (const row of rows) {{
          const matched = row.innerText.toLowerCase().includes(query);
          row.style.display = matched ? "" : "none";
          if (matched) visible += 1;
        }}
        rowCount.textContent = `${{visible}} 条`;
      }});
    }}
  </script>
</body>
</html>
"""


def _strategy_cards(df: pd.DataFrame) -> str:
    if df.empty or "coarse_strategy_title" not in df.columns:
        return ""
    cards = []
    for strategy, group in df.groupby("coarse_strategy", sort=False):
        title = group["coarse_strategy_title"].iloc[0]
        names = "、".join(group["name"].astype(str).head(3))
        cards.append(
            f"""
            <div class="card">
              <div class="muted">{_text(strategy)}</div>
              <strong>{_text(title)}</strong>
              <div class="muted">{len(group)} 条；{_text(names)}</div>
            </div>
            """
        )
    return f"<section><h2>策略分组</h2><div class=\"cards\">{''.join(cards)}</div></section>"


def _overlap_bars(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    counts = df.groupby(["code", "name"], as_index=False).size().sort_values(["size", "code"], ascending=[False, True]).head(12)
    max_count = max(counts["size"].max(), 1)
    rows = []
    for row in counts.itertuples(index=False):
        width = row.size / max_count * 100
        rows.append(
            f"""
            <div class="bar-row">
              <div class="bar-label mono">{_text(row.code)}</div>
              <div class="bar-track"><div class="bar-fill" style="width:{width:.2f}%"></div></div>
              <div class="bar-value">{int(row.size)} 次</div>
            </div>
            <div class="muted" style="margin:-7px 0 7px 160px">{_text(row.name)}</div>
            """
        )
    return f"<section><h2>多策略重复出现</h2>{''.join(rows)}</section>"


def _coarse_table(df: pd.DataFrame) -> str:
    rows = []
    for row in df.itertuples(index=False):
        rows.append(
            f"""
            <tr>
              <td>{_text(row.coarse_strategy_title)}</td>
              <td class="mono">{_text(row.code)}</td>
              <td>{_text(row.name)}</td>
              <td>{_text(row.board_name)}</td>
              <td>{_yi(row.market_cap)}</td>
              <td>{_pct(row.revenue_yoy)}</td>
              <td>{_pct(row.profit_yoy)}</td>
              <td>{_num(row.coarse_score, 3)}</td>
              <td>{_text(row.data_note)}</td>
            </tr>
            """
        )
    return f"""
      <section>
        <h2>粗筛明细</h2>
        <div class="table-tools">
          <input id="filterInput" type="search" placeholder="搜索代码、名称、行业或策略" aria-label="搜索粗筛结果">
          <span id="rowCount">{len(df)} 条</span>
        </div>
        <table id="screenTable">
          <thead><tr><th>策略</th><th>代码</th><th>名称</th><th>行业</th><th>市值</th><th>营收同比</th><th>净利同比</th><th>分数</th><th>数据说明</th></tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </section>
    """


def render_coarse_html(df: pd.DataFrame, meta: dict) -> str:
    body = f"""
      <div class="grid">
        {_overlap_bars(df)}
        {_strategy_cards(df)}
      </div>
      {_coarse_table(df)}
    """
    return _page("粗筛策略结果", meta, body, len(df))


def _combo_bars(df: pd.DataFrame) -> str:
    if df.empty:
        return "<section><h2>组合分</h2><p class=\"muted\">暂无数据。</p></section>"
    top = df.sort_values("combo_score", ascending=False).head(12)
    max_score = max(top["combo_score"].max(), 1)
    rows = []
    for row in top.itertuples(index=False):
        width = float(row.combo_score) / max_score * 100
        rows.append(
            f"""
            <div class="bar-row">
              <div class="bar-label">{_text(row.name)}</div>
              <div class="bar-track"><div class="bar-fill" style="width:{width:.2f}%"></div></div>
              <div class="bar-value">{_num(row.combo_score)}</div>
            </div>
            """
        )
    return f"<section><h2>组合分 Top 12</h2>{''.join(rows)}</section>"


def _hit_bars(df: pd.DataFrame) -> str:
    if df.empty or "strategy_hits" not in df.columns:
        return ""
    top = df.sort_values(["strategy_hits", "combo_score"], ascending=[False, False]).head(12)
    max_hits = max(top["strategy_hits"].max(), 1)
    rows = []
    for row in top.itertuples(index=False):
        width = int(row.strategy_hits) / max_hits * 100
        rows.append(
            f"""
            <div class="bar-row">
              <div class="bar-label">{_text(row.name)}</div>
              <div class="bar-track"><div class="bar-fill warn" style="width:{width:.2f}%"></div></div>
              <div class="bar-value">{int(row.strategy_hits)} 个</div>
            </div>
            """
        )
    return f"<section><h2>策略命中数</h2>{''.join(rows)}</section>"


def _combo_table(df: pd.DataFrame) -> str:
    rows = []
    for row in df.itertuples(index=False):
        rows.append(
            f"""
            <tr>
              <td>{_num(row.combo_score)}</td>
              <td class="mono">{_text(row.code)}</td>
              <td>{_text(row.name)}</td>
              <td>{_text(row.board_name)}</td>
              <td>{int(row.strategy_hits)}</td>
              <td>{_pct(row.revenue_yoy)}</td>
              <td>{_pct(row.profit_yoy)}</td>
              <td>{_num(row.quality_score)}</td>
              <td>{_text(row.combo_reason)}</td>
              <td>{_text(row.risk_flags)}</td>
            </tr>
            """
        )
    return f"""
      <section>
        <h2>组合评分明细</h2>
        <div class="table-tools">
          <input id="filterInput" type="search" placeholder="搜索代码、名称、行业或理由" aria-label="搜索组合评分">
          <span id="rowCount">{len(df)} 条</span>
        </div>
        <table id="screenTable">
          <thead><tr><th>组合分</th><th>代码</th><th>名称</th><th>行业</th><th>命中</th><th>营收同比</th><th>净利同比</th><th>质量分</th><th>理由</th><th>风险</th></tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </section>
    """


def render_combo_html(df: pd.DataFrame, meta: dict) -> str:
    body = f"""
      <div class="grid">
        {_combo_bars(df)}
        {_hit_bars(df)}
      </div>
      {_combo_table(df)}
    """
    return _page("潜力股组合评分", meta, body, len(df))
