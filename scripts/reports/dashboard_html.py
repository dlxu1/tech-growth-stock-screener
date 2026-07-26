"""Interactive offline HTML dashboard for full screening runs."""

from __future__ import annotations

import json
from html import escape
from urllib.parse import urlencode


def _json_script(model: dict) -> str:
    return json.dumps(model, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _money(value) -> str:
    try:
        if value is None:
            return "N/A"
        return f"{float(value):.0f} 元"
    except Exception:
        return "N/A"


def _number(value, digits: int = 1) -> str:
    try:
        if value is None:
            return "N/A"
        return f"{float(value):.{digits}f}"
    except Exception:
        return "N/A"


def _percent(value) -> str:
    try:
        if value is None:
            return "N/A"
        return f"{float(value) * 100:.2f}%"
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
    "horizon_tags": "适合周期",
    "primary_horizon": "优先关注",
    "horizon_reason": "周期说明",
    "horizon_data_note": "周期数据说明",
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
            "宏观粗筛分会随市场状态切换权重。基础权重为多策略共振分 × 30% + 成长分 × 22% + "
            "质量分 × 20% + 风控分 × 13% + 流动性分 × 7% + 动量分 × 8%。"
            "牛市提高动量权重；震荡市偏向质量和反转；熊市动量不参与总分。"
        ),
        "overlap_score": "多策略共振分 = 命中策略权重 / 总策略权重 × 100。命中越多高权重粗筛策略，分数越高。",
        "growth_score": "成长分 = 营收同比和净利润同比正值相加后做百分位排名，再 × 100。",
        "quality_score": "质量分 = 行业内 ROE 排名 × 40% + 行业内毛利率排名 × 25% + PEG 评分 × 35%，再 × 100。",
        "risk_control_score": "风控分 = 最大回撤绝对值低排名 × 70% + 20日成交额排名 × 30%，再 × 100。",
        "liquidity_score": "流动性分 = 20日成交额在基础股票池中的百分位排名 × 100。",
        "momentum_score": "动量分 = 60日趋势动量排名与均值反转分的组合；反转分要求基本面正增长，并会惩罚已明显反弹的股票。",
        "strategy_summary": "策略命中 = 该股票进入了多少个宏观粗筛子策略。命中策略数越多，说明多维度共振越强；命中策略的权重会进一步换算为多策略共振分。",
    },
    "fine": {
        "technical_score": (
            "细筛分 = 趋势分 × 28 + 动量分 × 22 + 量能分 × 22 + 突破分 × 15 + "
            "风险分 × 8 + 流动性分 × 5。趋势看均线多头和20日均线上行；动量看20日涨幅、MACD和RSI；"
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
    combo_missing = coverage.get("combo_score_missing", 0)
    combo_rows = coverage.get("combo_rows", 0)
    plan_missing = coverage.get("plan_missing_quotes", 0)
    plan_rows = coverage.get("plan_rows", 0)
    plan_usable = coverage.get("plan_usable", 0)
    serial_text = "通过" if serial.get("ok") else "异常"
    stock_type_filter = summary.get("stock_type_filter") or {}
    selected_types = stock_type_filter.get("selected_types") or []
    stock_type_text = "全部" if not selected_types else ",".join(str(item) for item in selected_types)
    stock_type_count = f"{stock_type_filter.get('after_count', sector_rows)}/{stock_type_filter.get('before_count', sector_rows)}"
    market = summary.get("market_state") or {}
    market_label = market.get("label", "bull")
    market_regime = market.get("regime", market_label)
    market_bull_votes = market.get("bull_votes", 0)
    market_breadth = market.get("breadth_pct")
    market_note = str(market.get("note", ""))
    strategy_title = summary.get("strategy_title") or "潜力股组合评分"
    weight_version = summary.get("weight_version") or ""
    if not weight_version:
        weight_version = "牛市动量版" if market_regime == "bull" else ("熊市防御版" if market_regime == "bear" else "震荡防御版")
    weight_version_note = summary.get("weight_version_note") or {
        "牛市动量版": "牛市动量版：更重视动量和价格强势。由市场状态投票自动切换。",
        "震荡防御版": "震荡防御版：更重视质量、风控、反转，弱化动量。由市场状态投票自动切换。",
        "熊市防御版": "熊市防御版：质量和风控权重最高，动量不参与总分。由市场状态投票自动切换。",
    }.get(str(weight_version), "由市场状态投票自动切换。")
    # 构建三票维度详情
    dim_details = ""
    if market_note:
        parts = market_note.split("；")
        dim_items = []
        for p in parts:
            if "→" in p:
                dim_items.append(f'<span class="dim-chip">{p.strip()}</span>')
        if dim_items:
            dim_details = "".join(dim_items)
    # 市场研判 chip
    if market_regime == "bull":
        regime_html = '<span class="chip green">🟢 牛市</span>'
    elif market_regime == "bear":
        regime_html = '<span class="chip danger">🔴 熊市</span>'
    elif market_regime == "transition":
        regime_html = '<span class="chip warn">🟡 震荡</span>'
    else:
        regime_html = '<span class="chip muted">? 未知</span>'
    regime_title = f"投票 {market_bull_votes}/3 → {market_regime}。" + market_note
    # 市场状态 chip (简化为仓位提示)
    if market_regime != "bull":
        market_html = '<span class="chip danger">🔻 防御模式</span>'
        market_title = f"仓位上限降至{market.get('position_multiplier', 0.6):.0%}。" + str(market.get("note", ""))
    else:
        market_html = '<span class="chip green">✓ 正常模式</span>'
        market_title = str(market.get("note", "多数股票在均线上方且趋势上行"))
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
        <div title="{escape(regime_title)}"><span>市场研判</span><strong>{regime_html}</strong></div>
        <div title="{escape(market_title)}"><span>仓位管理</span><strong>{market_html}</strong></div>
        <div title="本次宏观粗筛使用的策略包"><span>策略口径</span><strong>{escape(str(strategy_title))}</strong></div>
        <div title="{escape(str(weight_version_note))}"><span>权重版本</span><strong>{escape(str(weight_version))}</strong></div>
        <div><span>最新行情日</span><strong>{escape(str(latest))}</strong></div>
        <div><span>股票池缺指标</span><strong>{escape(str(sector_missing))}/{escape(str(sector_rows))}</strong></div>
        <div><span>宏观分缺失</span><strong>{escape(str(combo_missing))}/{escape(str(combo_rows))}</strong></div>
        <div><span>操作建议缺日线</span><strong>{escape(str(plan_missing))}/{escape(str(plan_rows))}</strong></div>
        <div><span>操作建议可执行</span><strong>{escape(str(plan_usable))}/{escape(str(plan_rows))}</strong></div>
        <div><span>阶段串行</span><strong>{escape(serial_text)}</strong></div>
        <div><span>类型过滤</span><strong>{escape(stock_type_text)} {escape(stock_type_count)}</strong></div>
      </div>
    </section>
    """


def _backtest_html(backtest: dict | None, page_summary: dict | None = None) -> str:
    if not backtest:
        return ""
    strategies = backtest.get("strategies") or []
    if not strategies:
        return ""
    summary = backtest.get("summary") or {}
    page_summary = page_summary or {}
    signal_date = summary.get("signal_date") or "N/A"
    top = summary.get("top") or 10
    holding_days = summary.get("holding_days") or [7, 14, 21]
    preferred_detail_days = int(holding_days[0]) if holding_days else 7
    matrix_date = str(page_summary.get("as_of_date") or "")
    universe = str(page_summary.get("universe") or "")
    universe_index_symbol = str(page_summary.get("universe_index_symbol") or "")
    sector = str(page_summary.get("sector") or "")
    stock_types = ",".join((page_summary.get("stock_type_filter") or {}).get("selected_types") or [])
    return f"""
    <section class="backtest-section">
      <div class="section-title">
        <h2>数据回测</h2>
        <span class="chip">信号日 {escape(str(signal_date))}</span>
      </div>
      <div class="muted">按回测信号日的评分结果分别选取前三类 Top{escape(str(top))}，以下一交易日开盘买入，并按第 N 个交易日收盘计算持有收益，仅用于研究复核。</div>
      <form class="as-of-form backtest-date-form" action="/dashboard" method="get">
        <label for="backtestDate">回测信号日</label>
        <input type="hidden" name="as_of_date" value="{escape(matrix_date)}">
        <input type="hidden" name="universe" value="{escape(universe)}">
        <input type="hidden" name="universe_index_symbol" value="{escape(universe_index_symbol)}">
        <input type="hidden" name="sector" value="{escape(sector)}">
        <input type="hidden" name="stock_types" value="{escape(stock_types)}">
        <input id="backtestDate" name="backtest_date" type="date" value="{escape(str(signal_date))}" aria-label="选择回测信号日">
        <button type="submit">重算回测</button>
        <span class="muted">矩阵日期保持不变，仅用该信号日重跑评分并读取未来行情</span>
      </form>
      <div class="backtest-panel">
        <div class="backtest-controls">
          <div class="backtest-control-group">
            <span class="muted">评分口径</span>
            <div class="backtest-tabs" id="backtestStrategyTabs" role="tablist" aria-label="选择回测评分口径"></div>
          </div>
          <div class="backtest-control-group">
            <span class="muted">持有期：7日明细 / 14日明细 / 21日明细</span>
            <div class="backtest-tabs" id="backtestHorizonTabs" role="tablist" aria-label="选择回测持有期"></div>
          </div>
          <div class="backtest-summary-group">
            <div class="backtest-matrix-summary" id="backtestMatrixSummary"></div>
            <div class="backtest-summary" id="backtestSummary"></div>
          </div>
        </div>
        <div class="backtest-content">
          <div class="table-wrap">
            <table>
              <thead><tr><th>代码</th><th>名称</th><th>评分</th><th>买入日</th><th>买入价</th><th>卖出日</th><th>卖出价</th><th>收益</th><th>状态</th></tr></thead>
              <tbody id="backtestTableBody"></tbody>
            </table>
          </div>
          <div class="backtest-chart" id="backtestChart">
            <div class="empty">悬停表格股票查看买入到卖出区间的股价变化。</div>
          </div>
        </div>
      </div>
    </section>
    """


def _operation_backtest_html(operation_backtest: dict | None) -> str:
    if not operation_backtest:
        return ""
    rows = operation_backtest.get("rows") or []
    summary = operation_backtest.get("summary") or {}
    signal_date = summary.get("signal_date") or "N/A"
    profit_target = summary.get("profit_target_pct", 0.05)
    try:
        profit_target_text = f"{float(profit_target) * 100:.0f}%"
    except (TypeError, ValueError):
        profit_target_text = "5%"
    return f"""
    <section class="operation-backtest-section">
      <div class="section-title">
        <h2>操作回测</h2>
        <span class="chip">信号日 {escape(str(signal_date))}</span>
      </div>
      <div class="muted">按高潜力+好时机股票的操作建议模拟触发买入，并遵循 A 股 T+1：买入后下一交易日起才检查 {escape(profit_target_text)}止盈或初始止损，未退出则按截止日收盘计算。</div>
      <div class="operation-summary" id="operationBacktestSummary"></div>
      <div class="backtest-content">
        <div class="table-wrap">
          <table>
            <thead><tr><th>代码</th><th>名称</th><th>动作</th><th>买入日</th><th>买入价</th><th>卖出日</th><th>卖出价</th><th>状态</th><th>收益</th></tr></thead>
            <tbody id="operationBacktestTableBody"></tbody>
          </table>
        </div>
        <div class="operation-path" id="operationBacktestPath">
          <div class="empty">点击或悬停交易明细查看买入、止盈、止损路径。</div>
        </div>
      </div>
      <div class="muted">操作样本 {escape(str(summary.get("candidate_count", len(rows))))} 只；成功买入 {escape(str(summary.get("trade_count", 0)))} 只；仅用于规则复核。</div>
    </section>
    """


def _signal_validation_html(signal_validation: dict | None, page_summary: dict | None = None) -> str:
    if not signal_validation:
        return ""
    summary = signal_validation.get("summary") or {}
    page_summary = page_summary or {}
    holding_days = summary.get("holding_days") or [7, 14, 21]
    if not holding_days:
        return ""
    signal_dates = summary.get("signal_dates") or []
    if len(signal_dates) == 1:
        signal_date_text = str(signal_dates[0])
    elif len(signal_dates) > 1:
        signal_date_text = f"{signal_dates[0]} 至 {signal_dates[-1]}"
    else:
        signal_date_text = "N/A"
    matrix_date = str(page_summary.get("as_of_date") or "").strip()
    date_scope_note = f"验证口径：以下统计来自信号日 {signal_date_text} 的完整候选样本。"
    if matrix_date and matrix_date != signal_date_text:
        date_scope_note = (
            f"验证口径：以下统计来自信号日 {signal_date_text} 的完整候选样本；"
            f"当前矩阵日为 {matrix_date}。两者不同时，象限数量不会等于当前矩阵内可见股票数。"
        )
    return f"""
    <section class="validation-section">
      <div class="section-title">
        <h2>信号验证与预警</h2>
        <span class="chip">信号日 {escape(signal_date_text)}</span>
      </div>
      <div class="muted">验证信号日评分在未来持有期里的收益、胜率和排序有效性，用于后续预警规则复核。</div>
      <div class="validation-scope-note">{escape(date_scope_note)}</div>
      <div class="validation-panel">
        <div class="validation-controls">
          <div class="backtest-control-group">
            <span class="muted">持有期验证</span>
            <div class="validation-tabs" id="validationHorizonTabs" role="tablist" aria-label="选择信号验证持有期"></div>
          </div>
        </div>
        <div class="validation-overview" id="validationOverview"></div>
        <div class="validation-grid">
          <div class="validation-block">
            <h3>矩阵象限表现</h3>
            <div class="validation-heatmap" id="validationQuadrants"></div>
          </div>
          <div class="validation-block">
            <h3>综合关注分分桶</h3>
            <div class="validation-bucket-bars" id="validationBuckets"></div>
          </div>
        </div>
      </div>
    </section>
    """


def _industry_mainline_html(
    summary: dict,
    as_of_date: str,
    backtest_date: str,
    universe: str,
    universe_index_symbol: str,
    stock_types: str,
) -> str:
    mainlines = summary.get("industry_mainlines") or []
    if not mainlines:
        return """
        <section class="industry-mainline-band">
          <div class="section-title">
            <h2>行业主线证据板</h2>
            <span class="chip">暂无行业主线数据</span>
          </div>
          <div class="muted">当前没有可用行业主线，下面的高潜力和好时机仍按原始数据口径展示。</div>
        </section>
        """

    selected_name = str(summary.get("selected_industry") or mainlines[0].get("board_name") or "")
    selected = next((item for item in mainlines if str(item.get("board_name") or "") == selected_name), mainlines[0])
    selected_rank = int(summary.get("selected_industry_rank") or selected.get("rank") or 1)
    pool = summary.get("industry_pool") or {}
    pool_count = int(pool.get("count") or selected.get("stock_count") or 0)
    pool_label = str(pool.get("source_label") or selected.get("pool_source_label") or "样本代理")
    pool_kind = str(pool.get("source_kind") or "sample")
    pool_kind_label = "行业全成分股" if pool_kind == "full" else "缓存样本代理"
    pool_source = str(pool.get("source") or selected.get("pool_source_note") or "")
    pool_note = str(pool.get("note") or selected.get("pool_source_note") or "")
    source_label = str(summary.get("industry_mainline_source_label") or selected.get("pool_source_label") or "缓存样本代理")
    source_note = str(summary.get("selected_industry_note") or summary.get("selected_industry_reason") or "")

    def _nav_href(board_name: str) -> str:
        query = urlencode(
            {
                "as_of_date": as_of_date,
                "backtest_date": backtest_date,
                "universe": universe,
                "universe_index_symbol": universe_index_symbol,
                "stock_types": stock_types,
                "sector": board_name,
            }
        )
        return f"/dashboard?{query}"

    cards = []
    for item in mainlines[:8]:
        board_name = str(item.get("board_name") or "未分类")
        active = " active" if board_name == selected_name else ""
        cards.append(
            f"""
            <a class="industry-card{active}" href="{escape(_nav_href(board_name))}">
              <div class="industry-card-head">
                <strong>#{escape(str(item.get('rank') or 0))} {escape(board_name)}</strong>
                <span>{_number(item.get('mainline_score'), 2)}</span>
              </div>
              <div class="industry-card-meta">
                {escape(str(item.get('stock_count') or 0))} 只 · 近60日 {_percent(item.get('avg_return_60d'))} ·
                上涨家数 {_percent(item.get('positive_ratio'))}
              </div>
              <div class="industry-card-meta muted">
                成交额 {_money(item.get('avg_amount_20d'))} · 回撤 {_percent(item.get('avg_max_drawdown_252d'))}
              </div>
            </a>
            """
        )
    cards_html = "\n".join(cards)

    leaders = selected.get("leaders") or selected.get("stock_pool") or []
    leader_html = []
    for row in leaders[:5]:
        leader_html.append(
            f"""
            <div class="industry-stock-item">
              <div>
                <strong>{escape(str(row.get('name') or row.get('board_stock_name') or 'N/A'))}</strong>
                <span>{escape(str(row.get('leader_reason') or row.get('match_reason') or ''))}</span>
              </div>
              <span class="chip">{escape(str(row.get('code') or ''))}</span>
            </div>
            """
        )
    leader_html = "\n".join(leader_html) or '<div class="empty">暂无主线股票池。</div>'

    evidence_html = f"""
      <div class="industry-stat-grid">
        <div class="industry-stat"><strong>{_number(selected.get('mainline_score'), 2)}</strong><span>主线强度</span></div>
        <div class="industry-stat"><strong>{_percent(selected.get('avg_return_60d'))}</strong><span>近60日涨幅</span></div>
        <div class="industry-stat"><strong>{_percent(selected.get('positive_ratio'))}</strong><span>上涨家数占比</span></div>
        <div class="industry-stat"><strong>{_money(selected.get('avg_amount_20d'))}</strong><span>平均成交额</span></div>
        <div class="industry-stat"><strong>{_percent(selected.get('avg_revenue_yoy'))}</strong><span>营收均值</span></div>
        <div class="industry-stat"><strong>{_percent(selected.get('avg_profit_yoy'))}</strong><span>净利均值</span></div>
      </div>
      <div class="industry-reason">{escape(str(selected.get('mainline_reason') or ''))}</div>
    """

    return f"""
    <section class="industry-mainline-band">
      <div class="section-title">
        <h2>行业主线证据板</h2>
        <div class="industry-badges">
          <span class="chip green">当前选中 {escape(selected_name)}</span>
          <span class="chip">排名 #{escape(str(selected_rank))}</span>
          <span class="chip">{escape(source_label)}</span>
          <span class="chip">{escape(pool_label)} {escape(str(pool_count))} 只</span>
        </div>
      </div>
      <div class="muted">点击行业后服务端重算，下面的高潜力与好时机模块会跟着切到该行业股票池。{escape(source_note)}</div>
      <div class="industry-mainline-grid">
        <div class="industry-list">
          {cards_html}
        </div>
        <div class="industry-focus">
          <div class="industry-focus-head">
            <div>
              <strong>{escape(selected_name)}</strong>
              <span>证据排序 / 主线强度排序</span>
            </div>
            <div class="industry-focus-meta">
              <span class="chip">{escape(pool_label)}</span>
              <span class="chip">{escape(pool_kind_label)}</span>
              <span class="chip">{escape(pool_source or 'N/A')}</span>
            </div>
          </div>
          {evidence_html}
          <div class="industry-note">{escape(pool_note or '页面会优先用行业全成分股；若不可用则透明降级为样本代理。')}</div>
        </div>
        <div class="industry-pool">
          <div class="industry-pool-head">
            <strong>主线股票池</strong>
            <span class="muted">{escape(str(pool_count))} 只 · 只跟踪这一条主线</span>
          </div>
          <div class="industry-stock-list">
            {leader_html}
          </div>
        </div>
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
    summary = model.get("summary") or {}
    as_of_date = str(summary.get("as_of_date") or "")
    backtest_date = str(summary.get("backtest_date") or "")
    universe = str(summary.get("universe") or "")
    universe_index_symbol = str(summary.get("universe_index_symbol") or "")
    sector = str(summary.get("sector") or "")
    stock_types = ",".join((summary.get("stock_type_filter") or {}).get("selected_types") or [])
    health_html = _health_html(summary)
    industry_mainline_html = _industry_mainline_html(summary, as_of_date, backtest_date, universe, universe_index_symbol, stock_types)
    backtest_html = _backtest_html(model.get("backtest"), summary)
    operation_backtest_html = _operation_backtest_html(model.get("operation_backtest"))
    signal_validation_html = _signal_validation_html(model.get("signal_validation"), summary)
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
    .industry-mainline-band {{
      padding: 12px;
      margin-bottom: 12px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .industry-badges {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    .industry-mainline-grid {{
      display: grid;
      grid-template-columns: minmax(260px, 0.9fr) minmax(320px, 1.1fr) minmax(240px, 0.8fr);
      gap: 12px;
      margin-top: 10px;
      align-items: start;
    }}
    .industry-list {{
      display: grid;
      gap: 8px;
      max-height: 420px;
      overflow: auto;
      padding-right: 4px;
    }}
    .industry-card {{
      display: grid;
      gap: 4px;
      text-decoration: none;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfb;
      color: inherit;
      cursor: pointer;
    }}
    .industry-card.active {{
      border-color: var(--accent);
      background: var(--accent-soft);
    }}
    .industry-card-head {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: baseline;
    }}
    .industry-card-head strong {{
      font-size: 14px;
    }}
    .industry-card-head span {{
      font-size: 16px;
      font-weight: 700;
      color: var(--warn);
    }}
    .industry-card-meta {{
      color: var(--text);
      font-size: 12px;
      line-height: 1.45;
    }}
    .industry-focus,
    .industry-pool {{
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfb;
    }}
    .industry-focus-head,
    .industry-pool-head {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      margin-bottom: 10px;
    }}
    .industry-focus-head strong,
    .industry-pool-head strong {{
      display: block;
      font-size: 16px;
    }}
    .industry-focus-head span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-top: 2px;
    }}
    .industry-focus-meta {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    .industry-stat-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 10px;
    }}
    .industry-stat {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px;
      background: var(--panel);
      min-width: 0;
    }}
    .industry-stat strong {{
      display: block;
      font-size: 16px;
      line-height: 1.15;
    }}
    .industry-stat span {{
      display: block;
      color: var(--muted);
      font-size: 11px;
      margin-top: 2px;
    }}
    .industry-reason {{
      color: var(--text);
      font-size: 12px;
      line-height: 1.55;
    }}
    .industry-note {{
      margin-top: 10px;
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }}
    .industry-stock-list {{
      display: grid;
      gap: 8px;
    }}
    .industry-stock-item {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px;
      background: var(--panel);
    }}
    .industry-stock-item strong {{
      display: block;
      font-size: 13px;
      line-height: 1.3;
    }}
    .industry-stock-item span {{
      display: block;
      color: var(--muted);
      font-size: 11px;
      line-height: 1.35;
      margin-top: 2px;
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
    .as-of-form {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 10px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfb;
    }}
    .as-of-form label {{
      color: var(--muted);
      font-size: 13px;
    }}
    .as-of-form input[type="date"] {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 7px 9px;
      font: inherit;
      background: var(--panel);
      color: var(--text);
    }}
    .as-of-form button {{
      border: 1px solid var(--accent);
      border-radius: 8px;
      padding: 7px 10px;
      background: var(--accent-soft);
      color: var(--accent);
      font: inherit;
      cursor: pointer;
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
    .matrix-point.repeat-hit {{
      border-color: #f6d56b;
      box-shadow: 0 0 0 3px rgba(246, 213, 107, 0.52), 0 10px 28px rgba(36, 124, 109, 0.30);
    }}
    .hit-badge {{
      position: absolute;
      right: -11px;
      top: -11px;
      min-width: 22px;
      height: 18px;
      padding: 0 4px;
      border: 1px solid #f6d56b;
      border-radius: 999px;
      background: #fff8dc;
      color: #8a5a00;
      font-size: 10px;
      line-height: 16px;
      font-weight: 700;
      pointer-events: none;
      box-shadow: 0 4px 10px rgba(24, 33, 47, 0.18);
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
    .backtest-section {{ margin-top: 12px; }}
    .backtest-section h3 {{
      margin: 0;
      font-size: 15px;
      letter-spacing: 0;
    }}
    .backtest-panel {{
      display: grid;
      gap: 12px;
      margin-top: 12px;
    }}
    .backtest-controls {{
      display: flex;
      gap: 12px;
      align-items: flex-end;
      justify-content: space-between;
      flex-wrap: wrap;
    }}
    .backtest-control-group {{
      display: grid;
      gap: 6px;
    }}
    .backtest-tabs {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .backtest-tab {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 7px 10px;
      background: var(--panel);
      color: var(--text);
      font: inherit;
      cursor: pointer;
    }}
    .backtest-tab.active {{
      background: var(--accent-soft);
      border-color: var(--accent);
      color: var(--accent);
      font-weight: 600;
    }}
    .backtest-summary {{
      color: var(--muted);
      font-size: 13px;
      min-width: 260px;
      text-align: right;
    }}
    .backtest-summary-group {{
      display: grid;
      gap: 4px;
      min-width: 280px;
      text-align: right;
    }}
    .backtest-matrix-summary {{
      color: var(--accent);
      font-size: 13px;
      font-weight: 600;
    }}
    .backtest-row-label {{
      margin-left: 6px;
      vertical-align: middle;
    }}
    .backtest-content {{
      display: grid;
      grid-template-columns: minmax(280px, 0.72fr) minmax(0, 1.28fr);
      gap: 12px;
      align-items: start;
    }}
    .backtest-chart {{
      min-height: 300px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfb;
      padding: 12px;
    }}
    .backtest-chart svg {{
      width: 100%;
      height: auto;
      display: block;
    }}
    .backtest-chart-title {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 8px;
      font-size: 13px;
      color: var(--muted);
    }}
    tr.backtest-row-active {{ background: #f3f7f5; }}
    .operation-backtest-section {{ margin-top: 12px; }}
    .operation-summary {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 8px;
      margin: 12px 0;
    }}
    .operation-kpi {{
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfb;
    }}
    .operation-kpi span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
    }}
    .operation-kpi strong {{
      display: block;
      margin-top: 4px;
      font-size: 18px;
    }}
    .operation-path {{
      min-height: 260px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfb;
      padding: 12px;
    }}
    .operation-path-list {{
      display: grid;
      gap: 8px;
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
    }}
    .operation-path-item {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px;
      background: var(--panel);
    }}
    tr.operation-row-active {{ background: #f3f7f5; }}
    .validation-section {{ margin-top: 12px; }}
    .validation-section h3 {{
      margin: 0 0 10px;
      font-size: 15px;
      letter-spacing: 0;
    }}
    .validation-panel {{
      display: grid;
      gap: 12px;
      margin-top: 12px;
    }}
    .validation-scope-note {{
      margin-top: 10px;
      padding: 9px 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfb;
      color: var(--muted);
      font-size: 13px;
    }}
    .validation-controls {{
      display: flex;
      gap: 12px;
      align-items: flex-end;
      justify-content: space-between;
      flex-wrap: wrap;
    }}
    .validation-tabs {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .validation-tab {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 7px 10px;
      background: var(--panel);
      color: var(--text);
      font: inherit;
      cursor: pointer;
    }}
    .validation-tab.active {{
      background: var(--accent-soft);
      border-color: var(--accent);
      color: var(--accent);
      font-weight: 600;
    }}
    .validation-overview {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
    }}
    .validation-kpi {{
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfb;
    }}
    .validation-kpi strong {{
      display: block;
      margin-top: 4px;
      font-size: 20px;
      line-height: 1.1;
    }}
    .validation-kpi span {{
      color: var(--muted);
      font-size: 12px;
    }}
    .validation-kpi.green {{ border-color: var(--accent); background: var(--accent-soft); }}
    .validation-kpi.warn {{ border-color: var(--warn); background: #f5ecd9; }}
    .validation-kpi.danger {{ border-color: var(--danger); background: #f5e3e1; }}
    .validation-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 12px;
    }}
    .validation-block {{
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fbfcfb;
    }}
    .validation-heatmap {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }}
    .validation-tile {{
      min-width: 0;
      border: 1px solid var(--line);
      border-left-width: 5px;
      border-radius: 8px;
      padding: 10px;
      background: var(--panel);
    }}
    .validation-tile.green {{ border-left-color: var(--accent); }}
    .validation-tile.warn {{ border-left-color: var(--warn); }}
    .validation-tile.danger {{ border-left-color: var(--danger); }}
    .validation-tile-head {{
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: center;
      margin-bottom: 7px;
    }}
    .validation-tile-title {{
      font-weight: 600;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .validation-tile-metrics {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 6px;
      font-size: 12px;
    }}
    .validation-tile-metrics span {{
      color: var(--muted);
      display: block;
    }}
    .validation-bucket-bars {{
      display: grid;
      gap: 9px;
    }}
    .validation-bar-row {{
      display: grid;
      grid-template-columns: 92px minmax(0, 1fr) 112px;
      gap: 8px;
      align-items: center;
      font-size: 12px;
    }}
    .validation-bar-track {{
      height: 10px;
      border-radius: 999px;
      background: var(--track);
      overflow: hidden;
    }}
    .validation-bar-fill {{
      height: 100%;
      min-width: 4px;
      border-radius: 999px;
      background: var(--accent);
    }}
    .validation-bar-fill.negative {{ background: var(--danger); }}
    .validation-bar-value {{
      text-align: right;
      color: var(--muted);
      white-space: nowrap;
    }}
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
      .industry-mainline-grid,
      .industry-stat-grid,
      .decision-shell,
      .matrix-focus-shell,
      .detail-layout,
      .detail-summary,
      .detail-summary-main,
      .detail-modules,
      .backtest-content,
      .operation-summary,
      .validation-overview,
      .validation-grid,
      .validation-heatmap,
      .legend {{ grid-template-columns: 1fr; }}
      .industry-badges,
      .industry-focus-meta,
      .industry-focus-head,
      .industry-pool-head,
      .industry-stock-item {{
        justify-content: flex-start;
      }}
      .backtest-summary {{ text-align: left; }}
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
    {industry_mainline_html}
    <div class="decision-shell matrix-focus-shell">
      <section class="decision-panel matrix-panel">
        <div class="section-title">
          <h2>潜力-时机矩阵</h2>
          <span class="chip">宏观 × 技术</span>
        </div>
        <div class="muted">横轴是宏观粗筛分，纵轴是技术细筛分。右上角才是优先研究对象。</div>
        <form class="as-of-form" action="/dashboard" method="get">
          <label for="asOfDate">历史日期重算</label>
          <input type="hidden" name="universe" value="{escape(universe)}">
          <input type="hidden" name="universe_index_symbol" value="{escape(universe_index_symbol)}">
          <input type="hidden" name="sector" value="{escape(sector)}">
          <input type="hidden" name="stock_types" value="{escape(stock_types)}">
          <input type="hidden" name="backtest_date" value="{escape(backtest_date)}">
          <input id="asOfDate" name="as_of_date" type="date" value="{escape(as_of_date)}" aria-label="选择历史重算日期">
          <button type="submit">重算矩阵</button>
          <span class="muted">按所选日期截断日线行情并重跑完整筛选流程</span>
        </form>
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
    {backtest_html}
    {operation_backtest_html}
    {signal_validation_html}
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
    const planVisibleColumns = ["code","name","technical_score","action","horizon_tags","latest_close","planned_entry","initial_stop","risk_pct","take_profit_1r","take_profit_2r","plan_note"];
    const percentColumns = ["revenue_yoy","profit_yoy","return_60d","max_drawdown_252d"];
    const fineHiddenColumns = ["coarse_strategies"];
    const finePercentColumns = ["change_pct","return_20d","return_60d","max_drawdown_20d"];
    const fineNumberColumns = ["coarse_score","technical_score","close","amount_ratio","ma5","ma10","ma20","macd_hist","rsi14"];
    const planPercentColumns = ["risk_pct","position_cap"];
    const planNumberColumns = ["technical_score","latest_close","planned_entry","initial_stop","take_profit_1r","take_profit_2r"];
    const validationMinCompleteSamples = 5;
    const validationMinSignalDatesForFailure = 3;
    const data = window.DASHBOARD_DATA;
    const adaptiveThresholds = data.summary.adaptive_thresholds || {{}};
    const macroPotentialThreshold = adaptiveThresholds.macro_potential_threshold || 80;
    const technicalTimingThreshold = adaptiveThresholds.technical_timing_threshold || 75;
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
    const backtestStrategyTabs = document.getElementById("backtestStrategyTabs");
    const backtestHorizonTabs = document.getElementById("backtestHorizonTabs");
    const backtestMatrixSummary = document.getElementById("backtestMatrixSummary");
    const backtestSummary = document.getElementById("backtestSummary");
    const backtestTableBody = document.getElementById("backtestTableBody");
    const backtestChart = document.getElementById("backtestChart");
    const operationBacktestSummary = document.getElementById("operationBacktestSummary");
    const operationBacktestTableBody = document.getElementById("operationBacktestTableBody");
    const operationBacktestPath = document.getElementById("operationBacktestPath");
    const validationHorizonTabs = document.getElementById("validationHorizonTabs");
    const validationOverview = document.getElementById("validationOverview");
    const validationQuadrants = document.getElementById("validationQuadrants");
    const validationBuckets = document.getElementById("validationBuckets");
    let activeStage = data.stages[0]?.key || "";
    let sortState = {{ column: "", dir: 1 }};
    let selectedCandidateCode = "";
    let activeStockType = "全部";
    let activeBacktestStrategy = data.backtest?.strategies?.[0]?.key || "";
    let activeBacktestHorizon = data.backtest?.summary?.holding_days?.[0] || 7;
    let activeValidationHorizon = data.signal_validation?.summary?.holding_days?.[0] || 7;
    let activeBacktestRows = [];
    let activeOperationRows = data.operation_backtest?.rows || [];

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

    function recentHighGoodHits(plan, fine) {{
      return plan?.recent_high_good_hits || fine?.recent_high_good_hits || null;
    }}

    function recentHitCount(item) {{
      const count = Number(item?.recentHighGoodHits?.count || 0);
      return Number.isFinite(count) ? count : 0;
    }}

    function recentHitDates(item) {{
      const dates = item?.recentHighGoodHits?.dates;
      return Array.isArray(dates) ? dates.map(text).filter((value) => value !== "N/A") : [];
    }}

    function isRepeatHighGoodHit(item) {{
      return item?.priority?.label === "高潜力 + 好时机" && item?.recentHighGoodHits?.highlight === true && recentHitCount(item) > 3;
    }}

    function recentHitTitle(item) {{
      const count = recentHitCount(item);
      if (!count) return "";
      const dates = recentHitDates(item);
      const dateText = dates.length ? `：${{dates.join("、")}}` : "";
      return `近1月命中 ${{count}} 次${{dateText}}`;
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
          horizonTags: Array.isArray(plan.horizon_tags) ? plan.horizon_tags : [],
          primaryHorizon: plan.primary_horizon || "",
          horizonReason: plan.horizon_reason || "",
          horizonDataNote: plan.horizon_data_note || "",
          recentHighGoodHits: recentHighGoodHits(plan, fine),
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
        item.horizonTags?.join(" "),
        item.primaryHorizon,
        item.horizonReason,
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
      potentialMatrix.style.setProperty('--macro-threshold', macroPotentialThreshold + '%');
      potentialMatrix.style.setProperty('--timing-threshold-top', (100 - technicalTimingThreshold) + '%');
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
        const repeat = isRepeatHighGoodHit(item);
        const repeatClass = repeat ? " repeat-hit" : "";
        const repeatTitle = recentHitTitle(item);
        const title = `${{item.name}}｜${{classificationReason(item)}}｜综合关注分 ${{scoreText(item.attention_score)}}${{repeatTitle ? "｜" + repeatTitle : ""}}`;
        const count = recentHitCount(item);
        const badge = repeat ? `<span class="hit-badge">${{count}}x</span>` : "";
        return `
          <button type="button" class="matrix-point ${{item.priority.tone}}${{repeatClass}}${{selected}}" data-code="${{escapeHtml(item.code)}}" title="${{escapeHtml(title)}}" style="left:${{item.matrixX.toFixed(1)}}%;top:${{item.matrixY.toFixed(1)}}%;--point-size:${{item.pointSize.toFixed(0)}}px;z-index:${{item.zIndex}}">${{escapeHtml(initial)}}${{badge}}</button>
        `;
      }}).join("");
      potentialMatrix.innerHTML = `
        <div class="quad q1"><strong>高潜力 + 好时机</strong><br>优先研究</div>
        <div class="quad q2"><strong>低潜力 + 好时机</strong><br>短线强，需复核</div>
        <div class="quad q3"><strong>低潜力 + 差时机</strong><br>暂不关注</div>
        <div class="quad q4"><strong>高潜力 + 差时机</strong><br>加入观察池</div>
        <div class="axis-x">宏观潜力分，${{macroPotentialThreshold}} 为高潜力线 →</div>
        <div class="axis-y">技术时机分，${{technicalTimingThreshold}} 为好时机线 →</div>
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

    function horizonText(tags) {{
      return Array.isArray(tags) && tags.length ? tags.join(" / ") : "证据不足，需人工复核";
    }}

    function renderHorizonSummary(item) {{
      const tags = horizonText(item.horizonTags);
      const primary = item.primaryHorizon || "证据不足";
      const reason = item.horizonReason || item.horizonDataNote || "需结合基本面、技术时机和操作计划继续人工复核。";
      return `
        <div class="action-plan horizon-summary">
          <div class="action-plan-head">
            <div>
              <h3>周期标记</h3>
              <div class="action-copy">适合周期：${{escapeHtml(tags)}}</div>
              <div class="action-copy">优先关注：${{escapeHtml(primary)}}</div>
            </div>
            <span class="chip">研究注释</span>
          </div>
          <div class="risk-note">${{escapeHtml(reason)}}</div>
        </div>
      `;
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
                ${{renderHorizonSummary(item)}}
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
      if (col === "horizon_tags") return horizonText(value);
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
      if (col === "horizon_tags") return text(row.horizon_reason || row.horizon_data_note || display);
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

    function backtestStrategy() {{
      return (data.backtest?.strategies || []).find((item) => item.key === activeBacktestStrategy) || data.backtest?.strategies?.[0] || null;
    }}

    function backtestHorizonSummary(strategy, horizon) {{
      return strategy?.horizons?.[horizon] || strategy?.horizons?.[String(horizon)] || {{}};
    }}

    function backtestStatusLabel(status) {{
      if (status === "complete") return "完整";
      if (status === "missing_future_quotes") return "缺未来行情";
      if (status === "insufficient_future_quotes") return "样本不足";
      return text(status);
    }}

    function matrixCandidateByCode(code) {{
      const key = text(code || "").padStart(6, "0");
      return buildCandidateModels().find((item) => item.code === key) || null;
    }}

    function isHighPotentialGoodTiming(row) {{
      if (row?.is_high_potential_good_timing === true) return true;
      if (row?.matrix_label === "好时机+高潜力") return true;
      const macro = numberValue(row?.macro_score);
      const technical = numberValue(row?.technical_score);
      if (macro !== null && technical !== null) return macro >= macroPotentialThreshold && technical >= technicalTimingThreshold;
      const candidate = matrixCandidateByCode(row?.code);
      return candidate?.priority?.label === "高潜力 + 好时机";
    }}

    function renderBacktestMatrixLabel(row) {{
      if (!isHighPotentialGoodTiming(row)) return "";
      const macro = numberValue(row?.macro_score);
      const technical = numberValue(row?.technical_score);
      const title = macro !== null && technical !== null
        ? `宏观 ${{macro.toFixed(1)}}，技术 ${{technical.toFixed(1)}}`
        : "落在好时机+高潜力矩阵";
      return `<span class="backtest-row-label chip green" title="${{escapeHtml(title)}}">好时机+高潜力</span>`;
    }}

    function average(values) {{
      if (!values.length) return null;
      return values.reduce((sum, value) => sum + value, 0) / values.length;
    }}

    function renderBacktestMatrixSummary(horizon) {{
      if (!backtestMatrixSummary) return;
      const matrixRows = activeBacktestRows.filter(isHighPotentialGoodTiming);
      const returns = matrixRows
        .map((row) => numberValue(row.return_pct))
        .filter((value) => value !== null);
      if (!matrixRows.length) {{
        backtestMatrixSummary.textContent = `${{horizon}}日好时机+高潜力：暂无命中样本`;
        return;
      }}
      const avgReturn = average(returns);
      const winRate = returns.length ? returns.filter((value) => value > 0).length / returns.length : null;
      backtestMatrixSummary.textContent = `${{horizon}}日好时机+高潜力：完整样本 ${{returns.length}}/${{matrixRows.length}}，拼股收益 ${{formatBacktestReturn(avgReturn)}}，胜率 ${{formatBacktestReturn(winRate)}}`;
    }}

    function renderBacktestTabs() {{
      if (!backtestStrategyTabs || !backtestHorizonTabs || !data.backtest) return;
      const strategies = data.backtest.strategies || [];
      if (!activeBacktestStrategy && strategies.length) activeBacktestStrategy = strategies[0].key;
      backtestStrategyTabs.innerHTML = strategies.map((strategy) => `
        <button type="button" class="backtest-tab${{strategy.key === activeBacktestStrategy ? " active" : ""}}" data-bt-strategy="${{escapeHtml(strategy.key)}}">${{escapeHtml(strategy.title || strategy.key)}} <span>${{Number(strategy.selected_count || 0)}}只</span></button>
      `).join("");
      const horizons = data.backtest.summary?.holding_days || [7, 14, 21];
      if (!horizons.includes(Number(activeBacktestHorizon))) activeBacktestHorizon = horizons[0] || 7;
      backtestHorizonTabs.innerHTML = horizons.map((horizon) => `
        <button type="button" class="backtest-tab${{Number(horizon) === Number(activeBacktestHorizon) ? " active" : ""}}" data-backtest-horizon="${{Number(horizon)}}">${{Number(horizon)}}日明细</button>
      `).join("");
    }}

    function formatBacktestReturn(value) {{
      const number = numberValue(value);
      return number === null ? "N/A" : `${{(number * 100).toFixed(2)}}%`;
    }}

    function formatBacktestPrice(value) {{
      const number = numberValue(value);
      return number === null ? "N/A" : number.toFixed(2);
    }}

    function renderBacktestTable() {{
      if (!backtestTableBody || !data.backtest) return;
      const strategy = backtestStrategy();
      const horizon = Number(activeBacktestHorizon);
      activeBacktestRows = (strategy?.rows || []).filter((row) => Number(row.holding_days) === horizon);
      const summary = backtestHorizonSummary(strategy, horizon);
      renderBacktestMatrixSummary(horizon);
      if (backtestSummary) {{
        backtestSummary.textContent = `${{horizon}}日：完整样本 ${{summary.complete_count || 0}}/${{summary.rows || activeBacktestRows.length}}，平均收益 ${{formatBacktestReturn(summary.avg_return_pct)}}，胜率 ${{formatBacktestReturn(summary.win_rate)}}`;
      }}
      if (!activeBacktestRows.length) {{
        backtestTableBody.innerHTML = '<tr><td colspan="9" class="empty">暂无该持有期明细。</td></tr>';
        renderBacktestChart(null);
        return;
      }}
      backtestTableBody.innerHTML = activeBacktestRows.map((row, index) => `
        <tr data-backtest-row="${{index}}">
          <td class="mono">${{escapeHtml(row.code)}}</td>
          <td>${{escapeHtml(row.name)}}${{renderBacktestMatrixLabel(row)}}</td>
          <td>${{escapeHtml(scoreText(row.score))}}</td>
          <td>${{escapeHtml(row.buy_date || "N/A")}}</td>
          <td>${{escapeHtml(formatBacktestPrice(row.buy_price))}}</td>
          <td>${{escapeHtml(row.sell_date || "N/A")}}</td>
          <td>${{escapeHtml(formatBacktestPrice(row.sell_price))}}</td>
          <td>${{escapeHtml(formatBacktestReturn(row.return_pct))}}</td>
          <td><span class="chip">${{escapeHtml(backtestStatusLabel(row.data_status))}}</span></td>
        </tr>
      `).join("");
      renderBacktestChart(activeBacktestRows.find((row) => row.data_status === "complete") || activeBacktestRows[0]);
    }}

    function renderBacktestChart(row) {{
      if (!backtestChart) return;
      if (!row || !Array.isArray(row.price_points) || !row.price_points.length) {{
        backtestChart.innerHTML = '<div class="empty">该股票暂无可绘制的完整价格序列。</div>';
        return;
      }}
      const points = row.price_points
        .map((item) => ({{ trade_date: text(item.trade_date), close: numberValue(item.close) }}))
        .filter((item) => item.close !== null);
      if (!points.length) {{
        backtestChart.innerHTML = '<div class="empty">该股票暂无可绘制的完整价格序列。</div>';
        return;
      }}
      const width = 640;
      const height = 260;
      const pad = {{ left: 44, right: 22, top: 22, bottom: 34 }};
      const closes = points.map((item) => item.close);
      const minClose = Math.min(...closes);
      const maxClose = Math.max(...closes);
      const spread = maxClose - minClose || Math.max(maxClose * 0.02, 1);
      const xFor = (index) => pad.left + (points.length === 1 ? 0 : index / (points.length - 1)) * (width - pad.left - pad.right);
      const yFor = (close) => pad.top + (maxClose - close) / spread * (height - pad.top - pad.bottom);
      const path = points.map((item, index) => `${{index === 0 ? "M" : "L"}}${{xFor(index).toFixed(1)}} ${{yFor(item.close).toFixed(1)}}`).join(" ");
      const buyIndex = points.findIndex((item) => item.trade_date === row.buy_date);
      const sellIndex = points.findIndex((item) => item.trade_date === row.sell_date);
      const marker = (index, label, color) => {{
        if (index < 0) return "";
        const point = points[index];
        const x = xFor(index);
        const y = yFor(point.close);
        return `<g><line x1="${{x.toFixed(1)}}" y1="${{pad.top}}" x2="${{x.toFixed(1)}}" y2="${{height - pad.bottom}}" stroke="${{color}}" stroke-dasharray="4 4"/><circle cx="${{x.toFixed(1)}}" cy="${{y.toFixed(1)}}" r="4.5" fill="${{color}}"/><text x="${{x.toFixed(1)}}" y="${{Math.max(14, y - 8).toFixed(1)}}" text-anchor="middle" fill="${{color}}" font-size="12">${{label}}</text></g>`;
      }};
      const first = points[0];
      const last = points[points.length - 1];
      backtestChart.innerHTML = `
        <div class="backtest-chart-title">
          <strong>${{escapeHtml(row.name)}} <span class="mono">${{escapeHtml(row.code)}}</span></strong>
          <span>${{escapeHtml(row.buy_date)}} -> ${{escapeHtml(row.sell_date)}}，收益 ${{escapeHtml(formatBacktestReturn(row.return_pct))}}</span>
        </div>
        <svg viewBox="0 0 ${{width}} ${{height}}" role="img" aria-label="${{escapeHtml(row.name)}} 回测区间股价变化">
          <rect x="0" y="0" width="${{width}}" height="${{height}}" fill="#fbfcfb"/>
          <line x1="${{pad.left}}" y1="${{pad.top}}" x2="${{pad.left}}" y2="${{height - pad.bottom}}" stroke="#d9e0e6"/>
          <line x1="${{pad.left}}" y1="${{height - pad.bottom}}" x2="${{width - pad.right}}" y2="${{height - pad.bottom}}" stroke="#d9e0e6"/>
          <text x="${{pad.left - 8}}" y="${{pad.top + 4}}" text-anchor="end" fill="#667284" font-size="12">${{maxClose.toFixed(2)}}</text>
          <text x="${{pad.left - 8}}" y="${{height - pad.bottom}}" text-anchor="end" fill="#667284" font-size="12">${{minClose.toFixed(2)}}</text>
          <path d="${{path}}" fill="none" stroke="#247c6d" stroke-width="2.5"/>
          ${{marker(buyIndex, "买入", "#315f9f")}}
          ${{marker(sellIndex, "卖出", "#b94a48")}}
          <text x="${{pad.left}}" y="${{height - 10}}" fill="#667284" font-size="12">${{escapeHtml(first.trade_date)}}</text>
          <text x="${{width - pad.right}}" y="${{height - 10}}" text-anchor="end" fill="#667284" font-size="12">${{escapeHtml(last.trade_date)}}</text>
        </svg>
      `;
    }}

    function renderBacktestPanel() {{
      if (!data.backtest) return;
      renderBacktestTabs();
      renderBacktestTable();
    }}

    function operationStatusLabel(status) {{
      const labels = {{
        take_profit: "已止盈",
        stop_loss: "已止损",
        hold_to_end: "持有至截止日",
        not_triggered: "未触发",
        missing_future_quotes: "缺未来行情",
        invalid_plan: "计划无效",
      }};
      return labels[status] || text(status);
    }}

    function renderOperationBacktestSummary() {{
      if (!operationBacktestSummary || !data.operation_backtest) return;
      const summary = data.operation_backtest.summary || {{}};
      const items = [
        ["操作样本", summary.candidate_count || 0],
        ["成功买入", summary.trade_count || 0],
        ["未触发", summary.untriggered_count || 0],
        ["已止盈", summary.take_profit_count || 0],
        ["已止损", summary.stop_loss_count || 0],
        ["仍持有", summary.hold_count || 0],
        ["实际成交胜率", formatBacktestReturn(summary.win_rate)],
        ["平均已实现收益", formatBacktestReturn(summary.realized_avg_return_pct)],
        ["平均含浮动收益", formatBacktestReturn(summary.total_avg_return_pct)],
      ];
      operationBacktestSummary.innerHTML = items.map(([label, value]) => `
        <div class="operation-kpi"><span>${{escapeHtml(label)}}</span><strong>${{escapeHtml(value)}}</strong></div>
      `).join("");
    }}

    function renderOperationBacktestTable() {{
      if (!operationBacktestTableBody || !data.operation_backtest) return;
      activeOperationRows = data.operation_backtest.rows || [];
      if (!activeOperationRows.length) {{
        operationBacktestTableBody.innerHTML = '<tr><td colspan="9" class="empty">暂无可回测的操作样本。</td></tr>';
        renderOperationBacktestPath(null);
        return;
      }}
      operationBacktestTableBody.innerHTML = activeOperationRows.map((row, index) => `
        <tr tabindex="0" data-operation-row="${{index}}">
          <td class="mono">${{escapeHtml(row.code)}}</td>
          <td>${{escapeHtml(row.name)}}</td>
          <td>${{escapeHtml(row.action)}}</td>
          <td>${{escapeHtml(row.buy_date || "N/A")}}</td>
          <td>${{escapeHtml(formatBacktestPrice(row.buy_price))}}</td>
          <td>${{escapeHtml(row.sell_date || "N/A")}}</td>
          <td>${{escapeHtml(formatBacktestPrice(row.sell_price))}}</td>
          <td><span class="chip">${{escapeHtml(operationStatusLabel(row.status))}}</span></td>
          <td>${{escapeHtml(formatBacktestReturn(row.return_pct))}}</td>
        </tr>
      `).join("");
      renderOperationBacktestPath(activeOperationRows[0]);
    }}

    function renderOperationBacktestPath(row) {{
      if (!operationBacktestPath) return;
      if (!row) {{
        operationBacktestPath.innerHTML = '<div class="empty">暂无可展示的操作路径。</div>';
        return;
      }}
      const path = Array.isArray(row.path) ? row.path : [];
      const pathItems = path.length ? path.map((item) => `
        <div class="operation-path-item">
          <span>${{escapeHtml(item.trade_date)}} ${{item.event === "buy" ? "触发买入" : "持有观察"}}</span>
          <strong>高 ${{escapeHtml(formatBacktestPrice(item.high))}} / 低 ${{escapeHtml(formatBacktestPrice(item.low))}} / 收 ${{escapeHtml(formatBacktestPrice(item.close))}}</strong>
        </div>
      `).join("") : '<div class="empty">该股票未触发买入或缺少路径数据。</div>';
      operationBacktestPath.innerHTML = `
        <div class="backtest-chart-title">
          <strong>${{escapeHtml(row.name)}} <span class="mono">${{escapeHtml(row.code)}}</span></strong>
          <span>${{escapeHtml(operationStatusLabel(row.status))}}，收益 ${{escapeHtml(formatBacktestReturn(row.return_pct))}}</span>
        </div>
        <div class="operation-path-list">
          <div class="operation-path-item"><span>计划入场</span><strong>${{escapeHtml(formatBacktestPrice(row.planned_entry))}}</strong></div>
          <div class="operation-path-item"><span>初始止损</span><strong>${{escapeHtml(formatBacktestPrice(row.initial_stop))}}</strong></div>
          <div class="operation-path-item"><span>5%止盈价</span><strong>${{escapeHtml(formatBacktestPrice(row.profit_target_price))}}</strong></div>
          ${{pathItems}}
        </div>
      `;
    }}

    function renderOperationBacktestPanel() {{
      if (!data.operation_backtest) return;
      renderOperationBacktestSummary();
      renderOperationBacktestTable();
    }}

    function validationHorizonSummary(group, horizon) {{
      return group?.[horizon] || group?.[String(horizon)] || {{}};
    }}

    function validationStat(collection, name, horizon) {{
      return validationHorizonSummary(collection?.[name], horizon);
    }}

    function validationCompleteCount(stats) {{
      const count = Number(stats?.complete_count || 0);
      return Number.isFinite(count) ? count : 0;
    }}

    function validationHasEnoughSamples(stats) {{
      return validationCompleteCount(stats) >= validationMinCompleteSamples;
    }}

    function validationSignalDateCount() {{
      const summary = data.signal_validation?.summary || {{}};
      const summaryCount = Number(summary.signal_date_count || 0);
      const dateCount = Array.isArray(summary.signal_dates) ? summary.signal_dates.length : 0;
      const count = Math.max(summaryCount, dateCount);
      return Number.isFinite(count) ? count : 0;
    }}

    function validationCanTriggerFailure() {{
      return validationSignalDateCount() >= validationMinSignalDatesForFailure;
    }}

    function validationTone(stats, peerStats = null) {{
      const avg = numberValue(stats?.avg_return_pct);
      const winRate = numberValue(stats?.win_rate);
      const peerAvg = numberValue(peerStats?.avg_return_pct);
      if (!validationHasEnoughSamples(stats)) return "warn";
      if (avg === null && winRate === null) return "danger";
      if ((winRate !== null && winRate < 0.5) || (peerAvg !== null && avg !== null && avg <= peerAvg)) return "danger";
      if ((winRate !== null && winRate < 0.6) || (peerAvg !== null && avg !== null && avg - peerAvg < 0.02)) return "warn";
      return "green";
    }}

    function validationAlert(goodStats, otherStats) {{
      const completeCount = validationCompleteCount(goodStats);
      const avg = numberValue(goodStats?.avg_return_pct);
      const otherAvg = numberValue(otherStats?.avg_return_pct);
      const winRate = numberValue(goodStats?.win_rate);
      const excess = avg !== null && otherAvg !== null ? avg - otherAvg : null;
      if (!validationHasEnoughSamples(goodStats)) {{
        return {{
          tone: "warn",
          label: "象限失效预警",
          value: "样本不足",
          detail: `完整样本 ${{completeCount}} 只，低于 ${{validationMinCompleteSamples}} 只，暂不判定失效`,
        }};
      }}
      const tone = validationTone(goodStats, otherStats);
      if (tone === "green") {{
        return {{
          tone,
          label: "象限失效预警",
          value: "稳定",
          detail: `胜率 ${{formatBacktestReturn(winRate)}}，相对其他象限 ${{formatBacktestReturn(excess)}}`,
        }};
      }}
      if (tone === "warn") {{
        return {{
          tone,
          label: "象限失效预警",
          value: "观察",
          detail: `胜率 ${{formatBacktestReturn(winRate)}}，相对其他象限 ${{formatBacktestReturn(excess)}}`,
        }};
      }}
      if (!validationCanTriggerFailure()) {{
        return {{
          tone: "warn",
          label: "象限失效预警",
          value: "单日观察",
          detail: `信号日少于 ${{validationMinSignalDatesForFailure}} 个，先按观察处理；胜率 ${{formatBacktestReturn(winRate)}}，相对其他象限 ${{formatBacktestReturn(excess)}}`,
        }};
      }}
      return {{
        tone,
        label: "象限失效预警",
        value: "触发",
        detail: `胜率 ${{formatBacktestReturn(winRate)}}，相对其他象限 ${{formatBacktestReturn(excess)}}`,
      }};
    }}

    function validationBucketStat(name, horizon) {{
      return validationStat(data.signal_validation?.attention_buckets || {{}}, name, horizon);
    }}

    function validationRankingAlert(horizon) {{
      const top10 = validationBucketStat("Top 1-10", horizon);
      const top20 = validationBucketStat("Top 11-20", horizon);
      const top10Avg = numberValue(top10.avg_return_pct);
      const top20Avg = numberValue(top20.avg_return_pct);
      const diff = top10Avg !== null && top20Avg !== null ? top10Avg - top20Avg : null;
      if (!validationHasEnoughSamples(top10) || !validationHasEnoughSamples(top20)) {{
        return {{
          tone: "warn",
          label: "排序有效性预警",
          value: "样本不足",
          detail: `Top 分桶完整样本低于 ${{validationMinCompleteSamples}} 只，暂不判定排序失效`,
        }};
      }}
      if (diff !== null && diff >= 0) {{
        return {{
          tone: "green",
          label: "排序有效性预警",
          value: "稳定",
          detail: `Top 1-10 跑赢 Top 11-20，差额 ${{formatBacktestReturn(diff)}}`,
        }};
      }}
      if (!validationCanTriggerFailure()) {{
        return {{
          tone: "warn",
          label: "排序有效性预警",
          value: "单日观察",
          detail: `信号日少于 ${{validationMinSignalDatesForFailure}} 个，Top 1-10 未跑赢 Top 11-20，差额 ${{formatBacktestReturn(diff)}}`,
        }};
      }}
      return {{
        tone: "danger",
        label: "排序有效性预警",
        value: "触发",
        detail: `Top 1-10 未跑赢 Top 11-20，差额 ${{formatBacktestReturn(diff)}}`,
      }};
    }}

    function renderValidationTabs() {{
      if (!validationHorizonTabs || !data.signal_validation) return;
      const horizons = data.signal_validation.summary?.holding_days || [7, 14, 21];
      if (!horizons.includes(Number(activeValidationHorizon))) activeValidationHorizon = horizons[0] || 7;
      validationHorizonTabs.innerHTML = horizons.map((horizon) => `
        <button type="button" class="validation-tab${{Number(horizon) === Number(activeValidationHorizon) ? " active" : ""}}" data-validation-horizon="${{Number(horizon)}}">${{Number(horizon)}}日</button>
      `).join("");
    }}

    function renderValidationOverview(horizon) {{
      if (!validationOverview || !data.signal_validation) return;
      const quadrants = data.signal_validation.quadrants || {{}};
      const goodStats = validationStat(quadrants, "好时机+高潜力", horizon);
      const otherStats = validationStat(quadrants, "其他象限", horizon);
      const alert = validationAlert(goodStats, otherStats);
      const rankingAlert = validationRankingAlert(horizon);
      const avg = numberValue(goodStats.avg_return_pct);
      const otherAvg = numberValue(otherStats.avg_return_pct);
      const excess = avg !== null && otherAvg !== null ? avg - otherAvg : null;
      const summary = data.signal_validation.summary || {{}};
      validationOverview.innerHTML = `
        <div class="validation-kpi">
          <span>验证样本</span>
          <strong>${{escapeHtml(summary.candidate_count || 0)}}</strong>
          <span>${{escapeHtml((summary.signal_dates || []).join("、") || "N/A")}}</span>
        </div>
        <div class="validation-kpi">
          <span>好时机+高潜力平均收益</span>
          <strong>${{escapeHtml(formatBacktestReturn(goodStats.avg_return_pct))}}</strong>
          <span>完整样本 ${{escapeHtml(goodStats.complete_count || 0)}} 只</span>
        </div>
        <div class="validation-kpi">
          <span>相对其他象限超额</span>
          <strong>${{escapeHtml(formatBacktestReturn(excess))}}</strong>
          <span>其他象限 ${{escapeHtml(formatBacktestReturn(otherStats.avg_return_pct))}}</span>
        </div>
        <div class="validation-kpi ${{alert.tone}}">
          <span>${{escapeHtml(alert.label)}}</span>
          <strong>${{escapeHtml(alert.value)}}</strong>
          <span>${{escapeHtml(alert.detail)}}</span>
        </div>
        <div class="validation-kpi ${{rankingAlert.tone}}">
          <span>${{escapeHtml(rankingAlert.label)}}</span>
          <strong>${{escapeHtml(rankingAlert.value)}}</strong>
          <span>${{escapeHtml(rankingAlert.detail)}}</span>
        </div>
      `;
    }}

        function quadrantOrder(name) {{
          const order = ["好时机+高潜力", "高潜力+等时机", "好时机+低潜力", "其他象限"];
          const index = order.indexOf(name);
          return index >= 0 ? index : order.length;
        }}

        function renderValidationQuadrants(horizon) {{
          if (!validationQuadrants || !data.signal_validation) return;
          const quadrants = data.signal_validation.quadrants || {{}};
          const otherStats = validationStat(quadrants, "其他象限", horizon);
          const entries = Object.entries(quadrants).sort(([a], [b]) => quadrantOrder(a) - quadrantOrder(b) || a.localeCompare(b, "zh-Hans-CN"));
          if (!entries.length) {{
            validationQuadrants.innerHTML = '<div class="empty">暂无象限验证数据。</div>';
            return;
          }}
          validationQuadrants.innerHTML = entries.map(([name, group]) => {{
            const stats = validationHorizonSummary(group, horizon);
            const tone = validationTone(stats, name === "其他象限" ? null : otherStats);
            return `
              <div class="validation-tile ${{tone}}">
                <div class="validation-tile-head">
                  <div class="validation-tile-title" title="${{escapeHtml(name)}}">${{escapeHtml(name)}}</div>
                  <span class="chip ${{tone}}">${{escapeHtml(stats.complete_count || 0)}}只</span>
                </div>
                <div class="validation-tile-metrics">
                  <div><span>平均收益</span><strong>${{escapeHtml(formatBacktestReturn(stats.avg_return_pct))}}</strong></div>
                  <div><span>胜率</span><strong>${{escapeHtml(formatBacktestReturn(stats.win_rate))}}</strong></div>
                  <div><span>中位收益</span><strong>${{escapeHtml(formatBacktestReturn(stats.median_return_pct))}}</strong></div>
                </div>
              </div>
            `;
          }}).join("");
        }}

        function bucketOrder(label) {{
          const match = text(label).match(/Top\\s+(\\d+)/i);
          return match ? Number(match[1]) : 9999;
        }}

        function renderValidationBuckets(horizon) {{
          if (!validationBuckets || !data.signal_validation) return;
          const buckets = data.signal_validation.attention_buckets || {{}};
          const entries = Object.entries(buckets).sort(([a], [b]) => bucketOrder(a) - bucketOrder(b) || a.localeCompare(b, "zh-Hans-CN"));
          if (!entries.length) {{
            validationBuckets.innerHTML = '<div class="empty">暂无综合关注分分桶数据。</div>';
            return;
          }}
          const returns = entries
            .map(([, group]) => numberValue(validationHorizonSummary(group, horizon).avg_return_pct))
            .filter((value) => value !== null);
          const maxAbs = Math.max(0.01, ...returns.map((value) => Math.abs(value)));
          validationBuckets.innerHTML = entries.map(([label, group]) => {{
            const stats = validationHorizonSummary(group, horizon);
            const avg = numberValue(stats.avg_return_pct);
            const width = avg === null ? 0 : Math.max(4, Math.min(100, Math.abs(avg) / maxAbs * 100));
            const negative = avg !== null && avg < 0;
            return `
              <div class="validation-bar-row">
                <strong>${{escapeHtml(label)}}</strong>
                <div class="validation-bar-track" title="平均收益 ${{escapeHtml(formatBacktestReturn(avg))}}">
                  <div class="validation-bar-fill${{negative ? " negative" : ""}}" style="width: ${{width.toFixed(1)}}%"></div>
                </div>
                <div class="validation-bar-value">${{escapeHtml(formatBacktestReturn(stats.avg_return_pct))}} / ${{escapeHtml(formatBacktestReturn(stats.win_rate))}}</div>
              </div>
            `;
          }}).join("");
        }}

        function renderSignalValidationPanel() {{
          if (!data.signal_validation) return;
          const horizon = Number(activeValidationHorizon);
          renderValidationTabs();
          renderValidationOverview(horizon);
          renderValidationQuadrants(horizon);
          renderValidationBuckets(horizon);
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
    backtestStrategyTabs?.addEventListener("click", (event) => {{
      const button = event.target.closest("[data-bt-strategy]");
      if (!button) return;
      activeBacktestStrategy = button.dataset.btStrategy;
      renderBacktestPanel();
    }});
        backtestHorizonTabs?.addEventListener("click", (event) => {{
          const button = event.target.closest("[data-backtest-horizon]");
          if (!button) return;
          activeBacktestHorizon = Number(button.dataset.backtestHorizon);
          renderBacktestPanel();
        }});
        validationHorizonTabs?.addEventListener("click", (event) => {{
          const button = event.target.closest("[data-validation-horizon]");
          if (!button) return;
          activeValidationHorizon = Number(button.dataset.validationHorizon);
          renderSignalValidationPanel();
        }});
        backtestTableBody?.addEventListener("mouseover", (event) => {{
      const row = event.target.closest("[data-backtest-row]");
      if (!row) return;
      backtestTableBody.querySelectorAll("tr").forEach((item) => item.classList.remove("backtest-row-active"));
      row.classList.add("backtest-row-active");
      renderBacktestChart(activeBacktestRows[Number(row.dataset.backtestRow)]);
    }});
        backtestTableBody?.addEventListener("focusin", (event) => {{
      const row = event.target.closest("[data-backtest-row]");
      if (!row) return;
      renderBacktestChart(activeBacktestRows[Number(row.dataset.backtestRow)]);
    }});
    operationBacktestTableBody?.addEventListener("mouseover", (event) => {{
      const row = event.target.closest("[data-operation-row]");
      if (!row) return;
      operationBacktestTableBody.querySelectorAll("tr").forEach((item) => item.classList.remove("operation-row-active"));
      row.classList.add("operation-row-active");
      renderOperationBacktestPath(activeOperationRows[Number(row.dataset.operationRow)]);
    }});
    operationBacktestTableBody?.addEventListener("focusin", (event) => {{
      const row = event.target.closest("[data-operation-row]");
      if (!row) return;
      renderOperationBacktestPath(activeOperationRows[Number(row.dataset.operationRow)]);
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
        renderBacktestPanel();
        renderOperationBacktestPanel();
        renderSignalValidationPanel();
        renderStage();
  </script>
</body>
</html>
"""
