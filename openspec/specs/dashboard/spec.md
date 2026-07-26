# dashboard Specification

## Purpose

定义交互式 dashboard 的展示契约、数据注释字段和邮件摘要复用口径。Dashboard 仍是研究和辅助决策工具，不构成投资建议。

## Requirements

### Requirement: dashboard v1 展示行业主线证据板
系统 SHALL 在 `dashboard` v1 的数据健康条下方、矩阵/决策区上方展示行业主线证据板，并将其作为后续分析的方向确认层。

#### Scenario: 默认行业选择
- **WHEN** 用户打开 `dashboard` 且未显式指定行业
- **THEN** 系统 SHALL 先计算行业主线榜
- **AND** 系统 SHALL 默认选中排名第一且有可用股票池的行业

#### Scenario: 行业股票池驱动下游阶段
- **WHEN** 系统已确定当前选中行业
- **THEN** `股票池` SHALL 输出该行业的股票池
- **AND** `宏观粗筛`、`技术分析`、`操作建议` SHALL 只消费该行业股票池的下游结果

#### Scenario: 股票池来源透明展示
- **WHEN** dashboard 展示行业主线证据板
- **THEN** 系统 SHALL 显示当前股票池来源、池内数量和降级状态
- **AND** 若行业全成分股可用，系统 SHALL 标注为行业全成分股
- **AND** 若只能使用缓存样本或指数内样本，系统 SHALL 明确标注样本代理口径

### Requirement: dashboardv2 暂停更新
系统 SHALL 保留 `dashboardv2` 兼容入口，但不再把新的交互需求投放到该页面。

#### Scenario: 访问旧入口
- **WHEN** 用户访问 `dashboardv2`
- **THEN** 系统 MAY 保留兼容响应以避免历史链接失效
- **AND** 系统 SHOULD 标注 `dashboardv2` 已暂停更新，主入口回到 `dashboard`

### Requirement: 高潜力好时机股票周期标记
系统 SHALL 为 dashboard 操作建议行生成展示用投资周期字段：`horizon_tags`、`primary_horizon`、`horizon_reason` 和 `horizon_data_note`，并在交互界面中以 `适合周期` 和 `优先关注` 展示。

#### Scenario: 多周期证据同时成立
- **WHEN** 某只股票同时满足长线、中线或短线中的多个证据规则
- **THEN** `horizon_tags` SHALL 按 `长线`、`中线`、`短线` 的固定顺序输出多个标签
- **AND** `primary_horizon` SHALL 输出当前优先关注周期
- **AND** 标记 SHALL 仅作为研究注释，不改变评分、阈值、阶段成员、排序、操作建议或回测样本

#### Scenario: 证据不足
- **WHEN** 宏观、技术、策略命中或操作计划字段不足以支持任何周期标签
- **THEN** 系统 SHALL 不强行打标
- **AND** `horizon_data_note` SHALL 提示 `证据不足，需人工复核`

### Requirement: 周期标记分类口径
系统 SHALL 使用现有 dashboard 行字段生成周期标记，不新增独立选股策略或投资建议口径。

#### Scenario: 长线证据成立
- **WHEN** `quality_score >= 75`、`risk_control_score >= 65`、`growth_score >= 60`
- **AND** 策略命中信息包含价值、质量、成长或回撤控制类证据
- **THEN** 系统 SHALL 添加 `长线` 标记

#### Scenario: 中线证据成立
- **WHEN** `combo_score >= 80`
- **AND** `technical_score >= 75`
- **THEN** 系统 SHALL 添加 `中线` 标记

#### Scenario: 短线证据成立
- **WHEN** `usable_for_plan` 为真
- **AND** `primary_strategy` 为 `breakout_buy`、`pullback_ma_buy` 或 `volume_confirm_buy`
- **AND** `planned_entry`、`initial_stop` 是有效正数
- **AND** `risk_pct` 存在且不高于保守上限
- **THEN** 系统 SHALL 添加 `短线` 标记

### Requirement: 数据健康栏展示全局策略状态
系统 SHALL 在 dashboard 数据健康栏展示全局 `策略口径` 和 `权重版本`，并为 `权重版本` 提供 hover 说明。

#### Scenario: 展示权重版本说明
- **WHEN** 用户将鼠标悬停在 `权重版本` 上
- **THEN** 系统 SHALL 展示当前版本说明
- **AND** `牛市动量版` SHALL 说明更重视动量和价格强势
- **AND** `震荡防御版` SHALL 说明更重视质量、风控、反转，弱化动量
- **AND** `熊市防御版` SHALL 说明质量和风控权重最高，动量不参与总分

### Requirement: 邮件摘要包含周期字段
系统 SHALL 在每日邮件的 `好时机+高潜力` 候选股明细和 JSON payload 中包含 dashboard model 已生成的周期字段。

#### Scenario: 邮件消费 dashboard 周期字段
- **WHEN** 邮件摘要生成 `好时机+高潜力` 候选股
- **THEN** 每只候选股 SHALL 包含 `适合周期`、`优先关注` 和 `周期说明`
- **AND** JSON payload SHALL 包含 `horizon_tags`、`primary_horizon`、`horizon_reason` 和 `horizon_data_note`
- **AND** 邮件 SHALL 不重新计算另一套周期规则

#### Scenario: 邮件周期字段缺失
- **WHEN** dashboard model 中候选股缺少周期字段
- **THEN** 邮件 SHALL 展示 `适合周期：证据不足，需人工复核`
- **AND** 保留原风险提示
