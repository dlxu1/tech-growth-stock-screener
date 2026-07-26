## ADDED Requirements

### Requirement: dashboard v1 展示行业主线证据板
系统 SHALL 在现有 `dashboard` v1 中展示行业主线证据板，并将其作为高潜力与好时机分析之前的方向确认层。

#### Scenario: 行业证据板位置
- **WHEN** 用户打开 `dashboard`
- **THEN** 系统 SHALL 先展示现有数据健康模块
- **AND** 系统 SHALL 在数据健康模块下方展示行业主线证据板
- **AND** 系统 SHALL 在行业主线证据板下方展示现有高潜力与好时机决策区

#### Scenario: 保留 v1 现有交互
- **WHEN** 行业主线证据板加入 v1
- **THEN** 系统 SHALL 保留现有 `宏观潜力 × 技术时机` 矩阵、股票详情、阶段表、数据回测、操作回测和信号验证交互
- **AND** 系统 SHALL 不把独立 `dashboardv2` 页面作为新增交互的主承载入口

### Requirement: 默认选中行业排名第一
系统 SHALL 在未显式指定行业时，默认选中行业主线榜排名第一的行业。

#### Scenario: 默认行业选择
- **WHEN** 用户打开 `dashboard` 且没有传入选中行业参数
- **THEN** 系统 SHALL 根据当前可用数据计算行业主线榜
- **AND** 系统 SHALL 默认选择排名第一且有可用股票池的行业
- **AND** 页面 SHALL 标注该行业为当前选中行业

#### Scenario: 第一行业不可用
- **WHEN** 行业主线排名第一的行业缺少可用股票池
- **THEN** 系统 MAY 选择下一条有可用股票池的行业
- **AND** 系统 SHALL 在页面或 summary 中记录降级原因

### Requirement: 下游分析使用选中行业股票池
系统 SHALL 让高潜力与好时机相关分析基于当前选中行业股票池运行，而不是默认沪深 300 全池。

#### Scenario: 行业股票池作为上游
- **WHEN** 系统已经确定当前选中行业
- **THEN** `股票池` 阶段 SHALL 输出该行业的股票池
- **AND** `宏观粗筛` SHALL 只消费该行业股票池
- **AND** `技术分析` SHALL 只消费 `宏观粗筛` 输出
- **AND** `操作建议` SHALL 只消费 `技术分析` 输出

#### Scenario: 页面说明股票池来源
- **WHEN** dashboard 展示高潜力与好时机模块
- **THEN** 页面 SHALL 显示当前股票池来源
- **AND** 若使用行业全成分股，页面 SHALL 标注为行业全成分股
- **AND** 若只能使用沪深 300 内行业样本或缓存样本，页面 SHALL 明确标注样本范围和降级原因

### Requirement: 行业全成分股优先，样本降级透明
系统 SHALL 优先使用选中行业的全成分股作为股票池；当全成分股不可用时，系统 SHALL 透明降级为可用缓存样本。

#### Scenario: 行业全成分股可用
- **WHEN** `industry_members` 或等价缓存中存在选中行业的完整成分股
- **THEN** 系统 SHALL 使用该行业成分股构建 dashboard 股票池
- **AND** 后续宏观、技术和操作建议 SHALL 基于该股票池运行

#### Scenario: 行业全成分股不可用
- **WHEN** 选中行业缺少完整成分股数据
- **THEN** 系统 MAY 使用当前基础池内 `board_name` 命中的行业样本
- **AND** 系统 SHALL 明确提示这是缓存样本或指数内样本
- **AND** 系统 SHALL 不自动退回全市场或沪深 300 全池继续生成不带行业约束的结果

### Requirement: 行业主线排序可复用既有证据排序
系统 SHOULD 复用既有行业主线证据排序骨架来计算行业主线榜，并将其作为行业证据排序而不是完整行业指数排序。

#### Scenario: 复用既有排序公式
- **WHEN** 系统计算行业主线榜
- **THEN** 系统 SHOULD 复用既有实现中按 `board_name` 分组、结合涨幅、上涨家数占比、成交额、成长和回撤的证据排序逻辑
- **AND** 系统 SHALL 允许在输入池切换为当前选中行业股票池后继续使用相同的排序骨架
- **AND** 系统 SHALL 将该结果标注为“证据排序”或“主线强度排序”，避免包装成完整行业指数结论

#### Scenario: 排序口径保持可解释
- **WHEN** 页面展示行业主线榜
- **THEN** 系统 SHALL 同时展示排序依据和数据口径
- **AND** 若仍处于缓存样本代理口径，系统 SHALL 明确标注“样本代理”或等价提示
- **AND** 若已能使用完整行业成分股，系统 SHALL 明确标注“行业成分股”

### Requirement: dashboardv2 暂停更新
系统 SHALL 暂停独立 `dashboardv2` 页面的后续功能更新，并将新交互需求集中到 `dashboard` v1。

#### Scenario: 保留兼容入口
- **WHEN** 用户访问既有 `dashboardv2` 入口
- **THEN** 系统 MAY 保留当前兼容响应，避免历史链接失效
- **AND** 系统 SHOULD 标注 `dashboardv2` 已暂停更新，主入口回到 `dashboard`

#### Scenario: 新需求归入 v1
- **WHEN** 后续需求涉及行业主线、行业股票池、高潜力或好时机交互
- **THEN** 系统 SHALL 优先更新 `dashboard` v1
- **AND** 系统 SHALL 不继续扩展独立 `dashboardv2` 的交互能力
