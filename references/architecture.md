# Tech Growth Stock Screener Architecture

本文档用于帮助维护者快速理解 `tech-growth-stock-screener` 的代码结构、数据流、缓存边界和后续扩展方式。

## 1. 项目定位

`tech-growth-stock-screener` 是一个 A 股科技股筛选 skill。它的目标不是直接给出确定性买卖结论，而是把公开数据转化为一套可迭代的研究流程：

1. 从公开数据源获取股票、行业、财报、日线行情。
2. 将数据缓存到 SQLite。
3. 以科技关键词池或缓存指数成分池（如沪深 300）构建候选。
4. 细筛技术面强弱。
5. 生成下一交易日的规则化操作计划。
6. 用 Markdown、JSON、CSV 或本地 HTML 展示结果。

核心原则：

- 外部数据必须缓存到数据库后再被策略使用。
- 策略层不直接调用远程数据源。
- 每一层尽量拆成 `network.py`、`repository.py`、逻辑模块。
- 输出必须保留数据缺失原因和评测影响。
- 结果是研究和规则计划，不是收益保证。

## 2. 总体架构图

```mermaid
flowchart TD
  User["用户 / Codex"] --> CLI["scripts/run.py CLI 入口"]

  CLI --> Preflight["infra/preflight.py 按需更新"]
  CLI --> Sync["sync 命令"]
  CLI --> Screen["screen 命令"]
  CLI --> Coarse["coarse 命令"]
  CLI --> Combo["combo 命令"]
  CLI --> Fine["fine 命令"]
  CLI --> Plan["plan 命令"]
  CLI --> Visualize["visualize 命令"]

  Preflight --> Sync
  Sync --> SourceAdapter["scripts/data 兼容源适配器"]
  SourceAdapter --> InfraNet["scripts/infra/network.py"]
  SourceAdapter --> InfraCache["scripts/infra/cache.py / data/db.py"]
  InfraCache --> DB[("SQLite stock_data.sqlite")]

  Coarse --> CoarseLayer["粗筛层 strategies/coarse"]
  Combo --> CoarseLayer
  Fine --> FineLayer["细筛层 strategies/fine"]
  Plan --> PlanLayer["计划层 plan/trade_plan.py"]
  Visualize --> Reports["展示层 scripts/reports"]

  CoarseLayer --> DB
  FineLayer --> DB
  PlanLayer --> DB

  Screen --> StrictScreen["strict screen strategies/tech_growth.py"]
  StrictScreen --> DB

  CoarseLayer --> Reports
  FineLayer --> Reports
  PlanLayer --> Reports
  StrictScreen --> Reports
```

## 3. 分层职责

```mermaid
flowchart LR
  Infra["基建层 infra"] --> Coarse["粗筛层 coarse"]
  Infra --> Fine["细筛层 fine"]
  Infra --> Plan["计划层 plan"]
  Infra --> Reports["展示层 reports"]

  Coarse --> Fine
  Fine --> Plan
  Plan --> Reports

  Compat["兼容适配层 data"] --> Infra
  Compat --> Coarse
```

### 3.1 基建层

位置：`scripts/infra/`

职责：

- 封装 SQLite 缓存读写入口。
- 封装通用网络降级辅助。
- 封装代理策略。
- 封装命令运行前的数据新鲜度检查和按需更新编排。
- 封装日志能力。

主要文件：

- `infra/cache.py`: 统一读取 `quotes_daily`、读取派生日线指标、复用底层 SQLite helper。
- `infra/network.py`: 暴露 `apply_network_policy`、`run_fetchers`、`source_chain`。
- `infra/preflight.py`: 为 `screen/coarse/combo/fine/plan/visualize` 提供 `--update-policy`，检查并同步命令依赖的数据。
- `infra/logging.py`: 简单日志 helper。

### 3.2 兼容源适配层

位置：`scripts/data/`

这是历史遗留的数据适配层，目前保留为兼容入口。它仍然承担大量远程源拉取和标准化逻辑，但从架构上应视为“源适配器”，而不是业务数据层。

主要文件：

- `data/db.py`: SQLite schema、raw source table 写入、`index_constituents` 和 `quotes_daily` 写入。
- `data/sources.py`: AKShare、Sina、efinance、baostock、Eastmoney direct、CSV cache 的兼容适配。

日线同步的 `--source auto` 默认按 `efinance -> akshare -> sina -> baostock` 依次尝试，适配 Eastmoney/AKShare 连接不稳定的场景。`--skip-existing` 用于断点续跑，若某只股票在 `quotes_daily` 中已覆盖请求日期区间，则跳过该股票而不再联网请求。

后续演进方向：

- 通用缓存能力逐步沉到 `infra/cache.py`。
- 业务层专属数据组装放在各层 `repository.py`。
- 新增数据源时仍可先放在 `data/sources.py`，但必须保证写入 SQLite 后再被策略消费。

### 3.3 粗筛层

位置：`scripts/strategies/coarse/`

职责：

- 构建科技关键词候选池，或读取缓存指数成分池（`--universe csi300`）。
- 合并市值、财报、估值、行业、日线派生指标。
- 按 16 个粗筛策略打分。
- 每个策略默认保留 5 支股票。
- 通过 `combo` 命令聚合常用潜力股粗筛策略，形成组合评分。

主要文件：

- `coarse/network.py`: 拉取粗筛需要的源数据包。
- `coarse/repository.py`: 组装粗筛基础股票池。
- `coarse/registry.py`: 策略注册、评分函数、组合评分、排序和输出字段。

粗筛不是从数据源直接拉“排名靠前股票”。它先构建候选池，再在本地按策略评分排序。候选池可以来自科技行业关键词，也可以来自已同步的指数成分股，例如 `index_constituents` 中的沪深 300。

### 3.4 细筛层

位置：`scripts/strategies/fine/`

职责：

- 接收粗筛结果。
- 按股票代码去重。
- 读取 `quotes_daily` 历史日线。
- 计算技术指标和技术评分。
- 输出评分、原因标签和数据质量说明。
- 将本层输出写入 `layer_runs` / `layer_results`。

主要文件：

- `fine/network.py`: 日线刷新 hook。
- `fine/repository.py`: 加载粗筛候选和缓存日线。
- `fine/technical.py`: 技术指标、评分权重、原因标签。

细筛层每次运行会保存本次输出结果；日线历史数据仍来自 `quotes_daily`。

### 3.5 计划层

位置：`scripts/plan/`

职责：

- 接收细筛前 5 支股票。
- 读取缓存日线。
- 根据技术评分和原因标签生成下一交易日计划。
- 输出入场价、突破价、回踩区间、放量阈值、止损、止盈、移动止损、仓位上限和数据诊断。
- 将本层输出写入 `layer_runs` / `layer_results`。

主要文件：

- `plan/network.py`: 计划层数据刷新 hook。
- `plan/repository.py`: 加载缓存日线。
- `plan/trade_plan.py`: 操作计划核心规则。

计划层不重新选股，也不直接拉远程数据。

### 3.6 展示层

位置：`scripts/reports/`

职责：

- 将 screen、coarse、fine、plan 的结果渲染成 Markdown。
- JSON 和 CSV 输出由 `run.py` 统一处理。
- 将指数成分股、粗筛、组合评分、细筛结果渲染成本地静态 HTML。
- 展示层不拉远程数据，不改变策略结果。

主要文件：

- `reports/markdown.py`: strict screen Markdown。
- `reports/coarse_markdown.py`: 粗筛 Markdown。
- `reports/combo_markdown.py`: 组合评分 Markdown。
- `reports/fine_markdown.py`: 细筛 Markdown。
- `reports/trade_plan_markdown.py`: 计划 Markdown。
- `reports/index_constituents_html.py`: 指数成分股 HTML。
- `reports/coarse_html.py`: 粗筛和组合评分 HTML。
- `reports/fine_html.py`: 细筛技术面 HTML。
- `reports/repository.py`: 展示层数据辅助。
- `reports/network.py`: 保留展示层边界；展示层不做网络访问。

## 4. 数据流

```mermaid
sequenceDiagram
  participant U as User
  participant CLI as run.py
  participant C as Coarse Layer
  participant F as Fine Layer
  participant P as Plan Layer
  participant R as Reports
  participant DB as SQLite
  participant S as Upstream Sources

  U->>CLI: plan --coarse-strategy all --top 5 --universe csi300
  CLI->>DB: preflight check spot/financials/index/quotes
  alt cache stale or missing and update-policy enabled
    CLI->>S: sync required datasets through data sources
    S-->>DB: persist raw and normalized data
  end
  CLI->>C: run coarse strategies
  C->>DB: read cached index_constituents/spot/financials/industry/quotes
  C-->>S: fetch missing or refreshed source data
  S-->>DB: persist raw source tables
  C->>C: score candidates, keep top N per strategy
  C-->>F: coarse candidates
  F->>DB: read quotes_daily
  F->>F: compute technical indicators and score
  F-->>P: fine top candidates
  P->>DB: read latest quotes_daily bars
  P->>P: compute entry/stop/take-profit/position rules
  P-->>R: plan dataframe + metadata
  R-->>U: Markdown / JSON / CSV / HTML output
```

## 5. 命令入口

统一入口：`scripts/run.py`

支持命令：

- `sync`: 同步数据到 SQLite。
- `screen`: 运行原始 strict tech-growth 策略。
- `coarse`: 运行粗筛策略。
- `combo`: 运行潜力股组合评分。
- `fine`: 运行粗筛后的技术细筛。
- `plan`: 运行细筛后的下一交易日计划。
- `visualize`: 从 SQLite 和策略结果生成本地 HTML 报表。

除 `sync` 外，筛选和展示命令支持运行前按需更新：

- `--update-policy none`：默认值，不改变旧行为。
- `--update-policy cache`：强制离线缓存模式，不联网。
- `--update-policy auto`：检查缺失或过期数据并增量同步；失败时继续用缓存，错误写入 stderr。
- `--update-policy strict`：和 `auto` 一样检查和同步，但必要更新失败会中止命令。
- `--update-policy refresh`：强制刷新当前命令依赖的数据。

依赖关系：

- `screen/coarse`：spot、财报业绩；科技池还需要行业板块，沪深 300 池还需要 `index_constituents`。
- `combo`：粗筛依赖，加 `quotes_daily` 派生的动量、流动性和回撤指标。
- `fine/plan`：粗筛依赖，加 `quotes_daily` 历史日线。
- `visualize`：按 `--dataset` 复用对应命令的数据依赖。

`infra/preflight.py` 只做缓存检查和 `sync_dataset()` 编排；它不直接实现远程数据源，也不改变策略评分和展示排序。

常用命令：

```bash
python scripts/run.py coarse --strategy all --top 5
python scripts/run.py coarse --strategy all --top 5 --universe csi300 --source cache
python scripts/run.py combo --top 20 --combo-strategy-top 20 --universe csi300 --source cache
python scripts/run.py combo --top 20 --combo-strategy-top 20 --universe csi300 --update-policy auto
python scripts/run.py fine --coarse-strategy all --coarse-top 5 --top 20 --universe csi300 --source cache
python scripts/run.py fine --coarse-strategy all --coarse-top 5 --top 20 --universe csi300 --update-policy auto
python scripts/run.py plan --coarse-strategy all --coarse-top 5 --top 5 --universe csi300 --source cache
python scripts/run.py plan --coarse-strategy all --coarse-top 5 --top 5 --universe csi300 --update-policy auto
python scripts/run.py visualize --dataset fine --coarse-strategy all --coarse-top 5 --top 20 --universe csi300 --source cache --output .cache/reports/fine_csi300.html
python scripts/run.py sync --dataset index_constituents --index-symbol 000300
python scripts/run.py sync --dataset daily_prices --codes 600584,000021 --start 2024-01-01 --end 2026-07-08
python scripts/run.py sync --dataset daily_prices --from-index --index-symbol 000300 --start 2026-01-09 --end 2026-07-09 --adjust qfq --source auto --no-proxy --skip-existing
```

离线缓存运行：

```bash
python scripts/run.py plan --coarse-strategy all --coarse-top 5 --top 5 --source cache
```

## 6. 数据库和缓存

默认数据库：

```text
$SKILL/.cache/stock_data.sqlite
```

可通过环境变量覆盖：

```text
TECH_GROWTH_DB=/path/to/stock_data.sqlite
TECH_GROWTH_SCREENER_CACHE=/path/to/cache
```

核心表：

- `cache_meta`: 记录 logical source key 和 raw SQLite table 的映射。
- `source_runs`: 记录同步任务和错误。
- `stocks`: 标准化股票身份信息。
- `market_cap_snapshot`: 市值快照。
- `financial_reports`: 标准化财报字段。
- `industry_members`: 行业或板块成分。
- `index_constituents`: 指数成分股池，例如沪深 300，包含成分日期、名称、交易所、权重和权重日期。
- `quotes_daily`: 日线 OHLCV，供细筛、计划和价格派生指标使用。
- `layer_runs`: 保存 screen、coarse、combo、fine、plan 每次运行的参数和元信息。
- `layer_results`: 保存每层输出的完整逐行 JSON，同时冗余 code、name、rank、score、action 等查询字段。

缓存策略：

- 财报数据按报告期保留。
- 指数成分股按 `index_symbol + constituent_date + code + source` 保留，可支撑历史基座池对比。
- `quotes_daily` 按 `code + trade_date + source` 保留历史。
- `--update-policy auto` 会按命令依赖检查缓存：粗筛需要 spot、财报和候选池；沪深 300 池需要 `index_constituents`；组合评分、细筛和计划需要 `quotes_daily`。
- 日线同步支持 `--skip-existing`，用于断网后续跑：只要本地已覆盖请求日期区间，就跳过该股票。
- spot、行业板块、板块成分股 raw table 偏当前快照。
- 策略层结果默认沉淀到 `layer_runs` / `layer_results`；临时运行可用 `--no-persist-results` 跳过。

## 7. 策略数据流图

```mermaid
flowchart TD
  Spot["全市场行情 / 市值"] --> Base["粗筛基础股票池"]
  Financials["财报业绩 / 行业 / 增长"] --> Base
  Boards["科技板块 / 成分股"] --> Base
  IndexMembers["指数成分股 / 沪深300"] --> Base
  DailyMetrics["quotes_daily 派生指标"] --> Base

  Base --> C1["16 个粗筛策略"]
  C1 --> Combo["潜力股组合评分"]
  C1 --> C2["每个策略 Top 5"]
  C2 --> Dedup["按 code 去重"]
  Dedup --> Quotes["读取 quotes_daily"]
  Quotes --> TScore["技术指标评分"]
  TScore --> FTop["细筛 Top N"]
  FTop --> Plan["下一交易日计划"]
  Combo --> Output["Markdown / JSON / CSV / HTML"]
  Plan --> Output
```

## 8. 目录结构

```text
tech-growth-stock-screener/
  SKILL.md
  agents/
    openai.yaml
  references/
    architecture.md
    data-schema.md
    coarse-strategies.md
    fine-strategies.md
    trade-plan-rules.md
    screening-rules.md
  scripts/
    run.py
    screen.py
    common.py
    infra/
      cache.py
      network.py
      preflight.py
      logging.py
    data/
      db.py
      sources.py
    strategies/
      tech_growth.py
      coarse/
        network.py
        repository.py
        registry.py
      fine/
        network.py
        repository.py
        technical.py
    plan/
      trade_plan.py
      network.py
      repository.py
    reports/
      markdown.py
      coarse_markdown.py
      combo_markdown.py
      fine_markdown.py
      trade_plan_markdown.py
      index_constituents_html.py
      coarse_html.py
      fine_html.py
      repository.py
      network.py
```

## 9. 扩展指南

### 9.1 新增数据源

优先位置：

- 通用源适配：`scripts/data/sources.py`
- 通用网络能力：`scripts/infra/network.py`
- 通用缓存能力：`scripts/infra/cache.py`

要求：

1. 远程数据先写 SQLite raw source table。
2. 标准化数据再写核心表，如 `quotes_daily`。
3. 策略层只读 repository/cache 输出。
4. 文档同步更新 `references/data-schema.md`。

日线数据源新增时，还应确认 `--source auto` 的回退顺序是否合理，并验证 `--skip-existing` 不会重复拉取已覆盖完整日期区间的股票。

### 9.2 新增粗筛策略

修改：

- `scripts/strategies/coarse/registry.py`
- 必要时 `scripts/strategies/coarse/repository.py`
- `references/coarse-strategies.md`

步骤：

1. 添加 score function。
2. 注册到 `STRATEGIES`。
3. 声明 `required_metrics` 和 `positive_filters`。
4. 验证单策略和 `--strategy all`。

### 9.3 新增细筛指标

修改：

- `scripts/strategies/fine/technical.py`
- 必要时 `scripts/strategies/fine/repository.py`
- `references/fine-strategies.md`

步骤：

1. 添加指标计算。
2. 决定是否进入 `OUTPUT_COLUMNS`。
3. 调整 component score 或 reason label。
4. 保留缺失数据降级说明。

### 9.4 新增计划规则

修改：

- `scripts/plan/trade_plan.py`
- `scripts/reports/trade_plan_markdown.py`
- `references/trade-plan-rules.md`

步骤：

1. 保持动作选择依赖细筛评分和标签。
2. 所有价位规则从缓存日线计算。
3. 新字段加入 `OUTPUT_COLUMNS`。
4. 展示层同步渲染。
5. 明确数据缺失时的影响。

### 9.5 新增展示格式

修改：

- `scripts/run.py`
- `scripts/reports/`

注意：

- 展示层只渲染结果，不改变结果。
- 不在展示层补拉数据。
- 新格式应保留数据质量和缺失影响说明。

当前 `visualize` 支持 `index_constituents`、`coarse`、`combo`、`fine`。HTML 报表应保持静态文件输出，默认写入 `.cache/reports/`，并且只从 SQLite 或策略返回结果渲染。

## 10. 维护约束

- 不要让策略直接访问 AKShare、Sina、Eastmoney、efinance。
- 不要让展示层改变排序、评分或交易规则。
- 不要把缺失数据静默忽略。
- 不要把粗筛结果当作买入清单。
- 不要把计划层输出写成保证成交或保证收益。
- 改 schema 时同步 `data-schema.md`。
- 改粗筛逻辑时同步 `coarse-strategies.md`。
- 改细筛逻辑时同步 `fine-strategies.md`。
- 改计划逻辑时同步 `trade-plan-rules.md`。

## 11. 当前已知演进方向

建议后续分阶段完善：

1. 将 `scripts/data/` 中的通用缓存和网络能力继续下沉到 `scripts/infra/`。
2. 增加粗筛、细筛、计划的历史运行表。
3. 如未来确实需要历史验证能力，应另起独立模块，并先定义清楚调仓、成本、基准和样本外验证规则。
4. 为计划层增加组合级仓位控制。
5. 增加数据源健康检查和 source quality score，区分 efinance、AKShare、Sina、baostock 的可用性。
6. 增加更完整的离线测试样本。
7. 为 `index_constituents` 增加更多指数池和历史成分对比视图。
