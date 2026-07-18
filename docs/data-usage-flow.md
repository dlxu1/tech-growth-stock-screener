# 数据存储与使用流程

> 生成日期：2026-07-18

本文档基于 `docs/project-context.md`、`docs/data-rules.md`、`docs/decisions.md` 以及 `scripts/` 下的核心代码分析整理。

---

## 一、数据存储三层架构

```
┌──────────────────────────────────────────────────────────┐
│ Layer 0: raw_* 原始快照层（不可变）                         │
│   每次从数据源拉取的原始数据直接落盘，不做任何改写              │
│   raw_daily_prices_{code}_{start}_{end}_{adjust}_{hash}     │
│   raw_index_cons_000300, raw_stock_yjbb_20260331, ...       │
├──────────────────────────────────────────────────────────┤
│ Layer 1: 归一化业务表（可增量更新，upsert）                   │
│   quotes_daily         日线行情，PK=(code, trade_date, src)  │
│   index_constituents   指数成分股，PK=(symbol,date,code,src) │
│   financial_reports    财务数据（目前空表）                   │
│   industry_members     行业归属（目前空表）                   │
├──────────────────────────────────────────────────────────┤
│ Layer 2: 计算结果层（append-only）                          │
│   layer_runs           每次运行的元信息                      │
│   layer_results        每只股票每个阶段的详细结果（JSON）      │
└──────────────────────────────────────────────────────────┘
```

### 数据库文件位置

```
.cache/stock_data.sqlite
```

由 `common.py` 中的 `db_path()` 生成，可通过环境变量 `TECH_GROWTH_DB` 自定义。

---

## 二、数据源与同步流程

### 当前使用的数据源（按优先级排列）

| 数据源 | 用途 | 接口方式 |
|--------|------|----------|
| **sina** (新浪财经) | 日线行情、A股实时快照 | HTTP API |
| **efinance** (东方财富) | 日线行情 | Python 库 |
| **akshare** | 指数成分股、权重、财务数据 | Python 库 |
| **baostock** (证券宝) | 日线行情（兜底） | Python 库 |
| **eastmoney-direct** | 行业板块列表 | HTTP API |

### 日线行情同步（核心流程）

```bash
# 入口命令
.venv/bin/python scripts/run.py sync --dataset daily_prices \
    --start 2026-01-01 --end 2026-07-17 --codes 000001,000002,... --adjust qfq
```

**执行流程**（`scripts/data/sources.py:657 sync_daily_prices()`）：

```
1. 遍历 codes 列表
2. 对每只股票：
   a. skip_existing 检查：该股票在 quotes_daily 中是否已覆盖 [start, end]
      - 已覆盖 → 跳过
      - 部分覆盖 → 只拉取缺失的尾部日期
   b. 按优先级尝试数据源：efinance → akshare → sina → baostock
   c. 拉取成功 → 写入 raw_daily_prices_{code}_{start}_{end}_{adjust} 表（不可变）
   d. 归一化为统一格式 → upsert 写入 quotes_daily
3. 返回同步统计
```

### 指数成分股同步

```bash
.venv/bin/python scripts/run.py sync --dataset index_constituents --index-symbol 000300
```

- 通过 akshare 拉取中证指数官网
- 同时拉取成分股名单 + 权重
- upsert 到 `index_constituents` 表

### 财务数据同步

```bash
.venv/bin/python scripts/run.py sync --dataset financials --report-date auto
```

- 默认 `report_date=auto` 选择最新的完整财报（行数 >= 3000）
- 写入 `raw_stock_yjbb_YYYYMMDD` 表
- 注意：`financial_reports` 归一化表目前为空，财务数据直接从 raw 表读取

---

## 三、Dashboard 流水线（核心使用路径）

入口命令：
```bash
.venv/bin/python scripts/run.py dashboard --source cache \
    --universe csi300 --output .cache/reports/dashboard_latest.html
```

核心函数：`scripts/dashboard/pipeline.py:437 run_dashboard()`

### 阶段 0：市场状态检测

在进入股票池之前，先对整个指数做市场状态检测（`scripts/dashboard/market_state.py`）：

```python
# 读取 quotes_daily，计算指数成分股的整体状态
market_state = detect(codes, as_of_date=as_of_date)
```

返回三个市场状态之一：
- `bull`（牛市）— 仓位乘数 1.0
- `bear`（熊市）— 仓位乘数减半
- `neutral`（中性）— 仓位乘数 1.0

检测维度：
- 收盘价与 MA20 的位置关系
- MA20 斜率方向（上涨/下跌）
- 站上 MA20 的股票占比（市场宽度）

### 阶段 1：`sector_screen`（股票池）

```
输入：指数成分股列表（index_constituents）+ 实盘快照（stock_zh_a_spot）
输出：最多 100 只股票的基础画像

数据来源：
  1. index_constituents → 沪深300 成分股代码清单
  2. stock_zh_a_spot（raw） → 市值、行业
  3. stock_yjbb_YYYYMMDD（raw） → 营收同比、利润同比、行业
  4. quotes_daily → 计算 amount_20d, return_60d, max_drawdown_252d

产物字段：
  code, name, board_name, market_cap, revenue_yoy, profit_yoy,
  amount_20d, return_60d, max_drawdown_252d, match_reason, risk_flags, data_note
```

关键步骤（`scripts/strategies/sector_screen.py:76 run()`）：
1. `build_base_universe(args)` → 从 `index_constituents` 读取成分股
2. 合并 `financials`（营业收入、利润）和 `spot`（市值、行业）
3. `read_price_metrics()` → 从 `quotes_daily` 计算 20 日均成交额、60 日涨幅、252 日最大回撤
4. 按市值降序排列，取前 100 只
5. 生成 `match_reason`、`risk_flags`、`data_note`
6. **股票类型分类**：`annotate_stock_types()` 根据 `board_name` 匹配 `configs/stock_type_rules.json` 中的关键词，分为 `科技股`、`周期股`、`金融股`、`消费/防御`、`未分类`
7. `persist_layer_result("sector_screen", args, df)` → 写入 `layer_runs` + `layer_results`

### 阶段 2：`combo`（宏观粗筛）

```
输入：sector_screen 输出（阶段 1 选出的 100 只股票）
输出：最多 100 只股票的多策略综合评分

数据来源：
  1. quotes_daily → 计算股票价格动量、波动率
  2. financials（raw data） → ROE、毛利率、PE、PB
  3. spot → 市值

评分体系（多策略并行打分后取组合分）：
  - growth_score：  营收 + 利润增速（百分位排名）
  - quality_score：  ROE + 毛利率（百分位排名）
  - momentum_score： 60 日涨幅排名
  - liquidity_score：20 日均成交额排名
  - risk_control_score：252 日最大回撤倒数排名
  - overlap_score： 多策略共振度（同时命中多个策略加分）

combo_score = 加权聚合上述 6 个分项得分

产物字段（row_json）：
  combo_score, growth_score, quality_score, momentum_score,
  liquidity_score, risk_control_score, overlap_score,
  revenue_yoy, profit_yoy, roe, gross_margin, pe, pb,
  strategy_hits, matched_strategies, combo_reason
```

市场状态影响（`scripts/strategies/coarse/registry.py`）：
- `bear` 熊市下，动量因子自动防御性降权
- 防御模式下仓位上限自动打折

### 阶段 3：`fine`（技术分析）

```
输入：combo 输出（阶段 2 选出的最多 100 只股票）
输出：每只股票的技术面打分

数据来源：
  quotes_daily → 每只股票的完整日线数据

技术指标计算（`scripts/strategies/fine/technical.py`）：
  - MA5 / MA10 / MA20     移动均线
  - MACD Histogram          趋势强度
  - RSI14                   超买超卖
  - return_20d / return_60d  短期/中期收益
  - max_drawdown_20d         20 日最大回撤
  - amount_ratio             量能倍数（当前成交量 vs 20日均量）

评分规则：
  趋势强 + 放量突破 + 回撤可控 + 动量较好 + 流动性达标 → 高分

产物字段（row_json）：
  technical_score, close, ma5, ma10, ma20, macd_hist, rsi14,
  return_20d, return_60d, change_pct, amount_ratio,
  max_drawdown_20d, technical_reasons, technical_note
```

### 阶段 4：`plan`（操作建议）

```
输入：fine 输出（阶段 3 选出的股票）
输出：基于规则的下一个交易日操作计划

数据来源：
  quotes_daily → 日线数据（用于计算入场/止损/止盈价格）

操作策略（`scripts/plan/trade_plan.py`）：
  - breakout_buy：  突破买入 → 突破近期高点时入场
  - pullback_ma_buy：回踩买入 → 回踩 MA 支撑时入场
  - "暂不交易"：    不满足技术条件，不给买入建议

产物字段（row_json）：
  action, primary_strategy,
  planned_entry, initial_stop, risk_pct,
  take_profit_1r, take_profit_2r,
  breakout_trigger, pullback_high, pullback_low,
  volume_confirm_amount, position_cap,
  stop_conditions, cancel_conditions, trailing_stop_rule,
  data_status, usable_for_plan
```

### 阶段 5：动态阈值计算

```python
# scripts/dashboard/market_state.py
adaptive_thresholds = compute_dynamic_thresholds(
    combo_scores=[...],      # 所有候选股的宏观粗筛分
    technical_scores=[...]   # 所有候选股的技术分析分
)
```

自动计算象限分界线（用于 Dashboard 上的 `宏观潜力 × 技术时机` 矩阵）：
- `macro_potential_threshold`：默认 80，但如果分数分布集中则自动调整
- `technical_timing_threshold`：默认 75，同理自适应

---

## 四、Dashboard 可视化渲染

`run_dashboard()` 返回的 dict → `build_dashboard_view_model()` → `render_dashboard_html()`

### 输出的 HTML 包含：

| 组件 | 数据来源 |
|------|----------|
| 数据健康检查条 | `quotes_daily`, `index_constituents` 的最新日期/行数 |
| 宏观潜力 × 技术时机 矩阵图 | `combo_score` × `technical_score` 散点图 |
| 股票详情面板 | 点击矩阵中的点，展示该股票的四阶段完整数据 |
| 股票类型筛选芯片 | `stock_type_rules.json` 分类结果 |
| 历史日期选择器 | 触发 `--as-of-date` 重算 |
| 数据回测（固定持有期） | signal_backtest，读取 `quotes_daily` 前向收益 |
| 信号验证与预警 | 多日期批量验证，矩阵象限表现对比 |
| 操作回测 | operation_backtest，模拟入场/止损/止盈执行 |

### 综合关注度排序

```python
attention_score = combo_score * 0.65 + technical_score * 0.35
```
矩阵中的点大小反映该值。

---

## 五、数据回测与信号验证

### 固定持有期回测（signal_backtest）

```
输入：指定 as_of_date 的 dashboard 结果
操作：计算 Top N 股票在 7/14/21 个交易日后的收益
规则：从 as_of_date 的下一个交易日开盘价买入，持有至 N 个交易日收盘
```

### 批量信号验证（signal_validate）

```
输入：validation_start ~ validation_end 的多个信号日期
      每个日期间隔 validation_step_days（默认 20 天）
操作：对每个信号日期：
  1. 重跑该日期的 dashboard
  2. 按矩阵象限（好时机+高潜力 / 好时机+低潜力 / ...）分组
  3. 计算每组在 7/14/21 个交易日的平均收益
输出：象限热力图、注意力分桶柱状图、预警状态
```

### 操作回测（operation_backtest）

```
输入：好时机+高潜力 象限内的股票的操作计划
操作：模拟执行操作建议中的入场触发条件
  - 突破买入：开盘价 >= breakout_trigger 则入场
  - 回踩买入：盘中触及 Pullback Low 且 成交额确认 则入场
  - A股 T+1 卖出：入场次日才能卖
  - 止盈：5% 默认目标
  - 止损：initial_stop 触发立即退出
  - 未触发：持有至最新收盘价
```

---

## 六、关键代码文件索引

### 数据层

| 文件 | 职责 |
|------|------|
| `scripts/common.py` | `db_path()`, `cache_dir()`, `normalize_code()`, 通用工具 |
| `scripts/data/db.py` | SQLite 建表、`write_quotes_daily()`, `write_index_constituents()`, `write_layer_results()` |
| `scripts/data/sources.py` | 数据源适配器、`sync_daily_prices()`, `sync_dataset()`, `load_spot()`, `load_financial_report()` |
| `scripts/infra/cache.py` | `read_quotes_daily()`, `read_price_metrics()`, `read_index_constituents()` |
| `scripts/infra/persistence.py` | `persist_layer_result()` — 计算结果写入 `layer_runs` + `layer_results` |
| `scripts/infra/preflight.py` | 数据健康检查、更新策略 |
| `scripts/infra/network.py` | 网络代理策略 |

### 策略层

| 文件 | 职责 |
|------|------|
| `scripts/strategies/sector_screen.py` | 阶段 1：股票池构建 |
| `scripts/strategies/coarse/network.py` | 粗筛数据源组装、`build_index_universe()` |
| `scripts/strategies/coarse/repository.py` | 粗筛数据整合（合并财务+行情） |
| `scripts/strategies/coarse/registry.py` | 多策略打分注册、`run_combo()` |
| `scripts/strategies/fine/technical.py` | 阶段 3：技术分析（MA/MACD/RSI） |
| `scripts/strategies/fine/repository.py` | 技术分析数据读取 |
| `scripts/plan/trade_plan.py` | 阶段 4：操作建议生成 |
| `scripts/plan/repository.py` | 操作建议数据读取 |

### 仪表盘层

| 文件 | 职责 |
|------|------|
| `scripts/dashboard/pipeline.py` | `run_dashboard()` — 编排四个阶段 + 回测 |
| `scripts/dashboard/view_model.py` | `build_dashboard_view_model()` — DataFrame → 纯 dict |
| `scripts/dashboard/health.py` | 数据健康审计 |
| `scripts/dashboard/market_state.py` | 市场状态检测 + 动态阈值计算 |
| `scripts/dashboard/stock_types.py` | 股票类型分类（从 `configs/stock_type_rules.json` 加载） |
| `scripts/dashboard/server.py` | HTTP Server（支持动态日期切换） |
| `scripts/reports/dashboard_html.py` | 交互式 HTML 渲染 |

### 回测层

| 文件 | 职责 |
|------|------|
| `scripts/backtest/signal_backtest.py` | 固定持有期回测 + 批量信号验证 |
| `scripts/backtest/operation_backtest.py` | 操作计划模拟回测 |
| `scripts/backtest/repository.py` | 回测数据读取（前向行情） |

---

## 七、数据读写模式总结

| 表 | 写模式 | 读模式 | 使用方 |
|----|--------|--------|--------|
| `cache_meta` + `raw_*` | 每次拉取 append（新表） | `read_cached_source()` 按 table_key 读取 | `sources.py` |
| `quotes_daily` | `INSERT ... ON CONFLICT DO UPDATE`（upsert） | `read_quotes_daily(codes, as_of_date)` 批量按股票+日期读取 | 所有策略层 + plan + backtest |
| `index_constituents` | upsert | `read_index_constituents(symbol, date)` | `sector_screen`, `dashboard/pipeline.py` |
| `layer_runs` | 每次 pipeline 运行 INSERT 1 条 | 历史回溯查询 | `dashboard/pipeline.py` |
| `layer_results` | 每次 pipeline 运行 INSERT N 条（N = 股票数） | `row_json` 字段反序列化 | `view_model.py`, `reports/` |
