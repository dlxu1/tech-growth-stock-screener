# dashboard Specification

## Purpose

保留现有 dashboard 研究视图，同时新增 `dashboardv2` 行业主线模式。v1 继续服务于通用筛选和排序，v2 以“行业主线 -> 主线股票池 -> 龙头收敛 -> 技术确认 -> 每日复盘”为主线，降低黑盒感和短线盯盘压力。

## Requirements

### Requirement: 保留现有 dashboard
系统 SHALL 保留当前 dashboard 的交互、阶段顺序、数据健康栏和现有展示口径，不因新增 `dashboardv2` 而改变 v1 的默认行为。

#### Scenario: v1 仍按原流程运行
- **WHEN** 用户打开现有 `dashboard`
- **THEN** 系统 SHALL 继续使用现有的串行流程与现有展示结构
- **AND** 系统 SHALL 不把行业主线层强制插入 v1

### Requirement: 新增 dashboardv2 行业主线模式
系统 SHALL 提供一个与 v1 并存的 `dashboardv2` 入口，展示行业主线驱动的研究链路。

#### Scenario: v2 主流程
- **WHEN** 用户打开 `dashboardv2`
- **THEN** 系统 SHALL 展示以下链路：
  `行业主线 -> 主线股票池 -> 龙头收敛 -> 技术确认 -> 每日复盘`
- **AND** 页面 SHALL 明确表达行业主线优先于个股技术面的研究顺序

### Requirement: 行业主线数据接入
系统 SHALL 为 dashboardv2 接入行业板块涨幅、行业历史走势和行业成分股数据，并用于解释行业为什么成为主线。

#### Scenario: 行业主线榜
- **WHEN** 系统计算行业主线榜
- **THEN** 系统 SHALL 展示近一个月行业涨幅、上涨家数、成交额变化和主线强度
- **AND** 行业解释 SHALL 优先来自公开行业板块数据、资金/新闻摘要或可复用缓存
- **AND** 若解释数据不足，系统 SHALL 保守提示，不得编造上涨原因

#### Scenario: 第一阶段缓存降级
- **WHEN** 行业指数历史、资金流或新闻催化数据尚未稳定接入
- **THEN** 系统 MAY 使用现有股票池中的板块样本涨幅、上涨家数占比、成交额、财报和回撤字段估算行业主线
- **AND** 系统 SHALL 明确标注这是缓存样本估算
- **AND** 系统 SHALL 不把估算结果包装成完整行业指数或新闻催化结论

### Requirement: 主线股票池以行业为方向过滤
系统 SHALL 在 dashboardv2 中把行业主线作为方向过滤器，在现有基础池之上收敛出主线股票池。

#### Scenario: 基础池保留
- **WHEN** 系统生成 dashboardv2 主线股票池
- **THEN** 系统 SHALL 默认以现有 CSI 300 基础池作为稳定底座
- **AND** 再按选中的行业主线过滤出主线股票池
- **AND** 主线股票池 SHALL 只用于 v2，不得覆盖 v1 的基础池语义

#### Scenario: 龙头扩展
- **WHEN** 某行业存在明显龙头但不在基础池内
- **THEN** 系统 MAY 以观察标记展示该股票
- **AND** SHALL 保持与基础池结果可区分

### Requirement: 龙头收敛重定位高潜力
系统 SHALL 将既有“高潜力”分析重定位为 dashboardv2 的龙头收敛层，用于在主线行业中筛出少数核心候选股。

#### Scenario: 龙头排序
- **WHEN** 系统在主线股票池内排序
- **THEN** 系统 SHALL 优先结合市值、财报、相对强弱、资金承接和行业地位
- **AND** 结果 SHALL 收敛到少量龙头，而不是输出大量候选

### Requirement: 技术确认重定位好时机
系统 SHALL 将既有“好时机”分析重定位为 dashboardv2 的技术确认层，只对少数龙头输出能不能下手的结论。

#### Scenario: 技术确认面板
- **WHEN** 用户查看某只龙头股票
- **THEN** 系统 SHALL 展示结论、关键价位、趋势证据、量能证据和风险提醒
- **AND** 系统 SHALL 以“观察、等待回踩、等待放量确认、提醒触发、放弃”等保守结论表达
- **AND** 系统 SHALL 不把技术分本身作为主叙事

### Requirement: 每日复盘只跟踪少数主线与龙头
系统 SHALL 在 dashboardv2 中将每日复盘范围限制为少数主线和少数龙头股票。

#### Scenario: 复盘队列
- **WHEN** 系统生成每日复盘队列
- **THEN** 系统 SHALL 默认只保留 1-3 只龙头作为重点复盘对象
- **AND** 系统 SHALL 展示行业是否延续、龙头是否变化和技术确认是否仍成立
- **AND** 系统 SHALL 不要求用户对大量短线候选全天盯盘

### Requirement: v1 与 v2 共享数据底座但快照隔离
系统 SHALL 让 v1 和 v2 共享现有缓存与基础数据，但 SHALL 对入口、页面语义和快照版本进行隔离。

#### Scenario: 缓存复用
- **WHEN** 系统生成 v1 或 v2 页面
- **THEN** 系统 MAY 复用同一套 SQLite 缓存、财报、日线行情和成分股数据
- **AND** 系统 SHALL 让 v1 和 v2 的快照和渲染版本可区分
- **AND** 新增行业主线数据后 SHALL 尽量不破坏现有缓存行为

### Requirement: 行业数据缺失时保守降级
系统 SHALL 在行业板块数据缺失、成分股缺失或解释信息不足时保守降级，不得把 v2 退化成无约束的全市场黑盒筛选。

#### Scenario: 行业数据不可用
- **WHEN** 行业板块历史、成分股或解释数据不可用
- **THEN** 系统 SHALL 在 v2 中展示可读的降级提示
- **AND** 系统 SHALL 允许 v1 继续正常运行
- **AND** 系统 SHALL 不自动扩展为全市场推荐
