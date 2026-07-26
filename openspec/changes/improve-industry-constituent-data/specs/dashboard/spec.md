## ADDED Requirements

### Requirement: 行业成分股同步落库
系统 SHALL 提供可重复运行的行业成分股同步能力，将行业板块下的股票成分规范化写入 `industry_members`。

#### Scenario: 同步行业成分股
- **WHEN** 用户运行行业板块/行业成分同步命令
- **THEN** 系统 SHALL 读取行业板块列表
- **AND** 系统 SHALL 为每个可用行业板块读取成分股
- **AND** 系统 SHALL 将成分股写入 `industry_members`
- **AND** `code` SHALL 标准化为 6 位 A 股代码

#### Scenario: 单行业同步失败
- **WHEN** 某个行业成分股源不可用或解析失败
- **THEN** 系统 SHALL 记录该行业失败原因
- **AND** 系统 SHOULD 继续同步其他行业
- **AND** 系统 SHALL 在同步结果中暴露失败行业数量或明细

### Requirement: dashboard 优先使用行业全成分股
系统 SHALL 在选中行业后优先使用 `industry_members` 中的行业全成分股构建 dashboard 股票池。

#### Scenario: 行业全成分股可用
- **WHEN** dashboard 已确定当前选中行业
- **AND** `industry_members` 中存在该行业的可用成分股
- **THEN** `股票池` SHALL 使用该行业成分股构建
- **AND** `宏观粗筛` SHALL 只消费该行业股票池
- **AND** `技术分析` SHALL 只消费 `宏观粗筛` 输出
- **AND** `操作建议` SHALL 只消费 `技术分析` 输出
- **AND** 页面 SHALL 标注当前股票池为 `行业全成分股`

#### Scenario: 行业全成分股不可用
- **WHEN** dashboard 已确定当前选中行业
- **AND** `industry_members` 中没有该行业可用成分股
- **THEN** 系统 MAY 降级为当前基础池内的行业样本
- **AND** 页面 SHALL 标注为 `指数样本代理` 或 `缓存样本代理`
- **AND** 页面 SHALL 展示降级原因
- **AND** 系统 SHALL NOT 将样本代理结果包装成完整行业结论

### Requirement: 行业数据口径透明
系统 SHALL 在 dashboard model 和 HTML 中透明展示行业股票池来源、数量和可信口径。

#### Scenario: 展示股票池来源
- **WHEN** dashboard 展示行业主线证据板
- **THEN** 系统 SHALL 展示当前选中行业
- **AND** 系统 SHALL 展示当前股票池数量
- **AND** 系统 SHALL 展示股票池来源标签
- **AND** 若为样本代理，系统 SHALL 提示该结果仅代表当前样本

#### Scenario: 样本过小
- **WHEN** 当前行业股票池为样本代理且样本数量很少
- **THEN** 系统 SHOULD 保守展示涨幅、上涨家数占比和成交额指标
- **AND** 系统 SHALL 保留样本代理说明，避免用户误解为全行业统计

### Requirement: 行业成分数据参与 dashboard 缓存指纹
系统 SHALL 将行业成分股数据状态纳入 dashboard 数据指纹，避免成分数据更新后复用旧 dashboard 结果。

#### Scenario: 行业成分股变化
- **WHEN** `industry_members` 行数、更新时间或成员摘要发生变化
- **THEN** dashboard snapshot/response cache SHALL 视为数据指纹变化
- **AND** 系统 SHALL 重新计算 dashboard 结果或跳过旧快照
