"""Static HTML rendering for index constituent pools."""

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


def _weight(value) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.3f}%"
    except Exception:
        return "N/A"


def _num(value) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _metric(label: str, value: str) -> str:
    return f"""
      <div class="metric">
        <span>{escape(label)}</span>
        <strong>{escape(value)}</strong>
      </div>
    """


def _exchange_bars(df: pd.DataFrame) -> str:
    if df.empty or "exchange" not in df.columns:
        return "<p class=\"muted\">暂无交易所分布数据。</p>"
    counts = df["exchange"].fillna("未知").replace("", "未知").value_counts()
    total = max(int(counts.sum()), 1)
    rows = []
    for exchange, count in counts.items():
        pct = count / total * 100
        rows.append(
            f"""
            <div class="bar-row">
              <div class="bar-label">{_text(exchange)}</div>
              <div class="bar-track"><div class="bar-fill" style="width:{pct:.2f}%"></div></div>
              <div class="bar-value">{int(count)} 只</div>
            </div>
            """
        )
    return "\n".join(rows)


def _top_weights(df: pd.DataFrame, top_n: int = 10) -> str:
    if df.empty or "weight" not in df.columns:
        return "<p class=\"muted\">暂无权重数据。</p>"
    top = df.sort_values("weight", ascending=False).head(top_n)
    max_weight = max((_num(value) for value in top["weight"]), default=0.0) or 1.0
    rows = []
    for row in top.itertuples(index=False):
        width = _num(row.weight) / max_weight * 100
        rows.append(
            f"""
            <tr>
              <td class="mono">{_text(row.code)}</td>
              <td>{_text(row.name)}</td>
              <td>
                <div class="weight-cell">
                  <div class="bar-track"><div class="bar-fill accent" style="width:{width:.2f}%"></div></div>
                  <span>{_weight(row.weight)}</span>
                </div>
              </td>
            </tr>
            """
        )
    return f"""
      <table>
        <thead><tr><th>代码</th><th>名称</th><th>权重</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    """


def _constituent_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "<p class=\"muted\">当前数据库里没有该指数的成分股。</p>"
    rows = []
    ordered = df.sort_values(["exchange", "code"], ascending=[True, True])
    for row in ordered.itertuples(index=False):
        rows.append(
            f"""
            <tr>
              <td class="mono">{_text(row.code)}</td>
              <td>{_text(row.name)}</td>
              <td>{_text(row.exchange)}</td>
              <td>{_weight(row.weight)}</td>
            </tr>
            """
        )
    return f"""
      <div class="table-tools">
        <input id="filterInput" type="search" placeholder="搜索代码、名称或交易所" aria-label="搜索成分股">
        <span id="rowCount">{len(df)} 只</span>
      </div>
      <table id="constituentTable">
        <thead><tr><th>代码</th><th>名称</th><th>交易所</th><th>权重</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    """


def render_index_constituents_html(df: pd.DataFrame, meta: dict) -> str:
    index_name = meta.get("index_name") or meta.get("index_symbol") or "指数"
    title = f"{index_name} 成分股"
    total_weight = df["weight"].dropna().sum() if "weight" in df.columns and not df.empty else 0.0
    metrics = [
        _metric("成分数量", f"{len(df)} 只"),
        _metric("成分日期", str(meta.get("constituent_date") or "N/A")),
        _metric("权重日期", str(meta.get("weight_date") or "N/A")),
        _metric("权重合计", f"{total_weight:.2f}%"),
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
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #172033;
      --muted: #687386;
      --line: #dbe1ea;
      --accent: #1f8a70;
      --accent-2: #cf5c36;
      --track: #e8edf3;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    main {{
      width: min(1180px, calc(100% - 32px));
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
    h1, h2 {{
      margin: 0;
      letter-spacing: 0;
    }}
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
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 13px;
    }}
    .metric strong {{
      display: block;
      margin-top: 4px;
      font-size: 22px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1.25fr;
      gap: 14px;
      margin-bottom: 14px;
    }}
    section {{ padding: 18px; overflow: hidden; }}
    .bar-row {{
      display: grid;
      grid-template-columns: 130px minmax(120px, 1fr) 64px;
      gap: 10px;
      align-items: center;
      margin: 10px 0;
    }}
    .bar-label, .bar-value {{ color: var(--muted); font-size: 13px; }}
    .bar-track {{
      height: 10px;
      background: var(--track);
      border-radius: 999px;
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      background: var(--accent);
      border-radius: inherit;
    }}
    .bar-fill.accent {{ background: var(--accent-2); }}
    .weight-cell {{
      display: grid;
      grid-template-columns: minmax(70px, 1fr) 64px;
      gap: 10px;
      align-items: center;
    }}
    .table-tools {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 12px;
    }}
    input[type="search"] {{
      width: min(420px, 100%);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 11px;
      font-size: 14px;
      background: #fff;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: middle;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
      background: #fafbfc;
      position: sticky;
      top: 0;
    }}
    tbody tr:hover {{ background: #f8fafb; }}
    .source {{
      margin-top: 14px;
      font-size: 12px;
      color: var(--muted);
    }}
    @media (max-width: 820px) {{
      header {{ display: block; }}
      .metrics, .grid {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 104px minmax(90px, 1fr) 58px; }}
      main {{ width: min(100% - 20px, 1180px); padding-top: 18px; }}
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
        <div class="muted">指数代码：{escape(str(meta.get("index_symbol") or ""))}</div>
      </div>
      <div class="muted">本地 SQLite 可视化</div>
    </header>

    <div class="metrics">{"".join(metrics)}</div>

    <div class="grid">
      <section>
        <h2>交易所分布</h2>
        {_exchange_bars(df)}
      </section>
      <section>
        <h2>前十大权重</h2>
        {_top_weights(df)}
      </section>
    </div>

    <section>
      <h2>完整成分股</h2>
      {_constituent_table(df)}
    </section>

    <div class="source">数据库：{escape(str(meta.get("db_path") or ""))}</div>
  </main>
  <script>
    const input = document.getElementById("filterInput");
    const table = document.getElementById("constituentTable");
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
        rowCount.textContent = `${{visible}} 只`;
      }});
    }}
  </script>
</body>
</html>
"""
