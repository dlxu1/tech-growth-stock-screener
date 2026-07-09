"""Static HTML rendering for fine technical screening outputs."""

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
        return f"{float(value) * 100:.2f}%"
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
        _metric("细筛输出", f"{row_count} 支"),
        _metric("粗筛候选", f"{meta.get('coarse_candidates', 'N/A')} 支"),
        _metric("粗筛策略", str(meta.get("coarse_strategy") or "N/A")),
        _metric("日期缓存", "已读取"),
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
      --risk: #bf5b30;
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
    h1, h2 {{ margin: 0; letter-spacing: 0; }}
    h1 {{ font-size: 30px; }}
    h2 {{ font-size: 18px; margin-bottom: 14px; }}
    .muted {{ color: var(--muted); }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 18px 0;
    }}
    .metric, section {{
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
    .bar-row {{
      display: grid;
      grid-template-columns: 132px minmax(140px, 1fr) 70px;
      gap: 10px;
      align-items: center;
      margin: 10px 0;
    }}
    .bar-label, .bar-value {{
      color: var(--muted);
      font-size: 13px;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .bar-track {{ height: 10px; background: var(--track); border-radius: 999px; overflow: hidden; }}
    .bar-fill {{ height: 100%; background: var(--accent); border-radius: inherit; }}
    .bar-fill.risk {{ background: var(--risk); }}
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
      .metrics, .grid {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 112px minmax(90px, 1fr) 54px; }}
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
        <div class="muted">日线缓存：{escape(str(meta.get("db_path") or ""))}</div>
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


def _score_bars(df: pd.DataFrame) -> str:
    if df.empty:
        return "<section><h2>技术分</h2><p class=\"muted\">暂无数据。</p></section>"
    top = df.sort_values("technical_score", ascending=False).head(12)
    max_score = max(top["technical_score"].max(), 1)
    rows = []
    for row in top.itertuples(index=False):
        width = float(row.technical_score) / max_score * 100
        rows.append(
            f"""
            <div class="bar-row">
              <div class="bar-label">{_text(row.name)}</div>
              <div class="bar-track"><div class="bar-fill" style="width:{width:.2f}%"></div></div>
              <div class="bar-value">{_num(row.technical_score)}</div>
            </div>
            """
        )
    return f"<section><h2>技术分 Top 12</h2>{''.join(rows)}</section>"


def _risk_bars(df: pd.DataFrame) -> str:
    if df.empty or "max_drawdown_20d" not in df.columns:
        return ""
    top = df.sort_values("technical_score", ascending=False).head(12)
    rows = []
    for row in top.itertuples(index=False):
        drawdown = abs(float(row.max_drawdown_20d)) if pd.notna(row.max_drawdown_20d) else 0.0
        width = min(drawdown / 0.30, 1.0) * 100
        rows.append(
            f"""
            <div class="bar-row">
              <div class="bar-label">{_text(row.name)}</div>
              <div class="bar-track"><div class="bar-fill risk" style="width:{width:.2f}%"></div></div>
              <div class="bar-value">{_pct(row.max_drawdown_20d)}</div>
            </div>
            """
        )
    return f"<section><h2>20日最大回撤</h2>{''.join(rows)}</section>"


def _fine_table(df: pd.DataFrame) -> str:
    rows = []
    for row in df.itertuples(index=False):
        tags = "".join(f"<span class=\"tag\">{_text(item)}</span>" for item in str(row.technical_reasons).split("、") if item)
        rows.append(
            f"""
            <tr>
              <td>{_num(row.technical_score)}</td>
              <td class="mono">{_text(row.code)}</td>
              <td>{_text(row.name)}</td>
              <td>{_text(row.board_name)}</td>
              <td>{_text(row.latest_trade_date)}</td>
              <td>{_num(row.close, 2)}</td>
              <td>{_pct(row.change_pct)}</td>
              <td>{_pct(row.return_20d)}</td>
              <td>{_num(row.amount_ratio, 2)}</td>
              <td>{_num(row.rsi14, 1)}</td>
              <td>{_pct(row.max_drawdown_20d)}</td>
              <td>{tags}</td>
              <td>{_text(row.coarse_strategies)}</td>
            </tr>
            """
        )
    return f"""
      <section>
        <h2>细筛明细</h2>
        <div class="table-tools">
          <input id="filterInput" type="search" placeholder="搜索代码、名称、行业或标签" aria-label="搜索细筛结果">
          <span id="rowCount">{len(df)} 条</span>
        </div>
        <table id="screenTable">
          <thead><tr><th>技术分</th><th>代码</th><th>名称</th><th>行业</th><th>日期</th><th>收盘</th><th>日涨跌</th><th>20日涨幅</th><th>量能</th><th>RSI</th><th>回撤</th><th>标签</th><th>粗筛来源</th></tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </section>
    """


def render_fine_html(df: pd.DataFrame, meta: dict) -> str:
    body = f"""
      <div class="grid">
        {_score_bars(df)}
        {_risk_bars(df)}
      </div>
      {_fine_table(df)}
    """
    return _page("细筛技术面结果", meta, body, len(df))
