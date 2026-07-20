# 任务

## 1. 模型与分类器

- [x] 在 dashboard view-model 附近增加聚焦的投资周期分类器模块或 helper。
- [x] 定义 `horizon_tags`、`primary_horizon`、`horizon_reason` 和 `horizon_data_note` 字段；UI 中将 `primary_horizon` 展示为 `优先关注`。
- [x] 基于质量、成长、风控和宏观策略命中，实现长线证据规则。
- [x] 基于宏观潜力、技术时机和趋势/动量上下文，实现中线证据规则。
- [x] 基于可执行操作计划策略和完整风险字段，实现短线证据规则。
- [x] 保持分类器仅用于展示：不得改变分数、阈值、阶段成员或操作计划。

## 2. Dashboard 数据流

- [x] 将投资周期注释附加到合并后的矩阵行。
- [x] 在行上下文可用时，将投资周期注释附加到操作建议行。
- [x] 将 `策略口径` 和 `权重版本` 作为全局状态附加到 dashboard summary，供数据健康栏展示。
- [x] 保持串行阶段契约：下游行仍必须来自上一个阶段。
- [x] 确保静态 dashboard 快照包含新的注释字段。

## 3. HTML 展示

- [x] 在选中股票详情面板中增加紧凑的 `长线` / `中线` / `短线` 标签。
- [x] 在现有数据健康栏中展示 `策略口径` 和 `权重版本`，不把个股周期标签放在顶部。
- [x] 为数据健康栏的 `权重版本` 增加 hover tooltip：牛市动量版说明动量/价格强势，震荡防御版说明质量/风控/反转，熊市防御版说明质量/风控主导且动量不参与总分。
- [x] 在不挤占现有计划字段的前提下，在操作建议表或行详情中展示投资周期。
- [x] 将周期文本纳入矩阵搜索，使用户可以按 `长线`、`中线` 或 `短线` 检索。
- [x] 增加帮助文案，说明投资周期标签只是研究注释，不构成投资建议。

## 4. 邮件摘要

- [x] 更新 `scripts/reports/email_digest.py`，让 `好时机+高潜力` 候选股邮件明细包含 `适合周期`、`优先关注` 和 `周期说明`。
- [x] 确保邮件 JSON payload 中每只候选股包含 `horizon_tags`、`primary_horizon`、`horizon_reason` 和 `horizon_data_note`。
- [x] 邮件摘要不得重新计算另一套周期规则；应消费 dashboard model 中已经生成的周期字段。
- [x] 当周期字段缺失时，邮件展示 `适合周期：证据不足，需人工复核`，并保留原风险提示。

## 5. 文档

- [x] 更新 `docs/data-rules.md`，记录周期字段定义和分类规则。
- [x] 更新 `docs/decisions.md`，记录周期标签仅用于展示的决策。
- [x] 更新 `docs/handoff.md`，记录最新行为和验证命令。

## 6. 验证

- [x] 增加分类器规则和数据缺失行为的单元测试。
- [x] 增加或更新 dashboard view-model 测试，覆盖输出字段。
- [x] 增加或更新 dashboard HTML 测试，覆盖标签渲染。
- [x] 增加或更新 dashboard HTML 测试，覆盖 `权重版本` hover 文案。
- [x] 增加或更新 `tests/test_email_digest.py`，覆盖邮件正文和 payload 中的周期字段。
- [x] 运行 `/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest discover -s tests`。
- [x] 渲染器变更后重新生成 `.cache/reports/dashboard_latest.html`。
- [x] 运行 `git diff --check`。
- [x] 代码编辑后运行 `codegraph sync`。
