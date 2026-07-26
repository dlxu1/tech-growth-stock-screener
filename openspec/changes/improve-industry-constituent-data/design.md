# 设计

## 概览

本变更解决行业主线模块的数据可信度问题。核心思路是把行业数据分成两个层次：

1. 行业板块列表：有哪些行业板块，包含 `board_name` 和 `board_code`。
2. 行业成分股：每个行业板块下有哪些股票，规范化写入 `industry_members`。

dashboard 行业主线证据板继续作为方向确认层，但其输入口径必须可审计：

```text
行业全成分股 -> 更可信，可作为当前行业股票池
指数样本代理 / 缓存样本代理 -> 只能作为样本热度提示
```

本次不改变评分公式。优化重点是数据覆盖、缓存复用和展示口径。

## 数据同步

### 行业成分同步入口

扩展现有同步能力，推荐首期在 `sync --dataset industry_boards` 中增加行业成分同步，或新增等价参数/数据集来完成以下动作：

- 读取行业板块列表。
- 对每个行业板块调用已有 `load_board_constituents(board_name, board_code, ...)`。
- 将结果规范化为 `industry_members`。
- 对单个行业失败做记录，不让少数行业失败导致整体同步完全不可用。

推荐输出 summary：

```text
dataset: industry_boards
boards: 76
member_rows: 5000+
member_boards: 76
failed_boards: [...]
db_path: .cache/stock_data.sqlite
```

如果考虑运行时间，可以支持后续增强参数：

- `--sector 半导体`：只同步指定行业。
- `--refresh`：强制刷新板块列表和成分股。
- 默认 cache/auto 行为继续遵守项目现有缓存策略。

### `industry_members` 契约

`industry_members` 应至少包含：

- `board_name`
- `board_code`
- `code`
- `name`
- `source`
- `updated_at`

写入策略：

- 对同一 `board_name + code + source` 或等价主键做 upsert。
- 每次同步某行业成功后，可以替换该行业对应 source 的旧成员，避免陈旧成分残留。
- `code` 必须标准化为 6 位 A 股代码。
- `name` 优先来自行业成分接口，缺失时可后续由 spot/financial 数据补齐。

### 失败与降级

行业成分同步可能受远程源、代理、缓存缺失影响。失败处理要求：

- 单行业失败应写入 sync summary 或 source run error，不中断其他行业。
- dashboard 不得因为完整成分缺失而静默退回全市场结果。
- dashboard 可以降级为当前基础池中 `board_name` 命中的样本，但必须标明降级原因。

## Dashboard 数据流

### 行业主线榜

行业主线榜可以继续基于当前可用基础池计算证据排序，但必须在 summary 中标注输入口径：

- `industry_mainline_source_label`
- `industry_pool.source_kind`
- `industry_pool.source_label`
- `industry_pool.count`
- `industry_pool.note`

当全行业成分可用时，行业主线证据可在后续实现中扩展为使用更完整的行业成员及其行情/财报指标。首期至少要求选中行业的下游股票池使用全成分股。

### 选中行业股票池

当用户打开 dashboard 或点击行业卡片时：

1. 服务端根据请求参数或默认主线确定 `selected_industry`。
2. 系统尝试从 `industry_members` 读取该行业完整成分。
3. 如果读取成功且成分非空，合并 spot、financial、daily quote 派生指标，生成 `股票池`。
4. 如果读取失败或为空，降级为当前基础池样本，并在 summary/page 中记录降级原因。
5. 下游 `宏观粗筛`、`技术分析`、`操作建议` 只消费该股票池。

全成分股路径的 meta 应输出：

```text
selected_industry_pool_kind: full
selected_industry_pool_label: 行业全成分股
selected_industry_pool_source: industry_members
```

样本降级路径的 meta 应输出：

```text
selected_industry_pool_kind: sample
selected_industry_pool_label: 指数样本代理 或 缓存样本代理
selected_industry_fallback_note: <具体原因>
```

## 快照与缓存

dashboard 快照和 dashboard-server 响应缓存必须感知行业成分数据变化。数据指纹应包含：

- `industry_members` 行数。
- 最近 `updated_at`。
- 可选：按 `board_name` 聚合的成员数量摘要或 hash。

否则用户同步行业成分后，页面可能继续复用旧的样本代理快照。

## 展示

行业主线证据板继续显示：

- 行业名称、排名、主线强度。
- 样本数量或成分股数量。
- 近 60 日涨幅、上涨家数占比、成交额、回撤。
- 当前选中行业的主线股票池。

但展示必须明确区分口径：

- `行业全成分股 87 只`
- `沪深300指数样本代理 20 只`
- `缓存样本代理 2 只`

样本代理时，页面文案应提示该数据不代表完整行业，仅用于样本热度观察。

## 测试

需要覆盖：

- 行业成分同步把多个行业写入 `industry_members`。
- 单个行业同步失败时，其他行业仍可写入，并在 summary 中体现失败。
- `industry_members` 有数据时，选中行业使用全成分股路径。
- `industry_members` 为空时，dashboard 明确降级为样本代理。
- dashboard HTML 显示正确的 pool source label、数量和降级 note。
- dashboard 数据指纹包含行业成员变化，避免旧快照复用。
- 现有 dashboard pipeline 串行关系保持不变。

## 待确认点

- 首期是否把行业成分同步并入 `sync --dataset industry_boards`，还是新增独立 `industry_members` dataset。建议并入现有命令，并在 README 中明确其会同步板块列表和成员。
- 是否默认同步所有行业，还是先支持指定行业后再扩展为全量。建议默认全量，保留未来按行业过滤的扩展空间。
