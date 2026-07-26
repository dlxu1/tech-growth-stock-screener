# 任务

## 1. 规格确认

- [ ] Review 本 OpenSpec change，确认两个优化目标：行业成分同步落库、dashboard 全成分优先。
- [ ] 确认 `行业全成分股` 优先来自 `industry_members`，样本代理只作为降级口径。
- [ ] 确认不改变行业主线、宏观粗筛、技术分析和操作建议评分公式。

## 2. 行业成分同步

- [ ] 扩展 `sync --dataset industry_boards` 或新增等价同步入口，支持同步行业板块列表和行业成分股。
- [ ] 复用 `load_industry_boards` 和 `load_board_constituents` 获取行业与成分股数据。
- [ ] 将行业成分规范化写入 `industry_members`，包含 `board_name`、`board_code`、`code`、`name`、`source`、`updated_at`。
- [ ] 支持单行业失败不中断整体同步，并在返回 summary 中记录失败行业和错误原因。
- [ ] 保持 cache/offline 行为；普通本地检查优先使用 cache，不强制远程刷新。

## 3. Dashboard 全成分优先

- [ ] 在选中行业股票池构建路径中优先读取 `industry_members`。
- [ ] 当 `industry_members` 中选中行业有成员时，使用全成分股构建 `股票池`。
- [ ] 合并 spot、financial、日线派生指标，保持现有字段契约和展示格式。
- [ ] 当完整行业成分不可用时，保留当前基础池样本降级路径。
- [ ] 在 summary/meta 中输出 `selected_industry_pool_kind`、`selected_industry_pool_label`、`selected_industry_pool_source` 和降级原因。

## 4. 快照与缓存

- [ ] 将 `industry_members` 的行数、更新时间或聚合 hash 纳入 dashboard 数据指纹。
- [ ] 确保行业成分同步后，dashboard-server 不继续复用旧样本代理响应。
- [ ] 检查 dashboard snapshot scope/key 是否区分选中行业和股票池来源。

## 5. 页面与文档

- [ ] 在行业主线证据板中明确显示 `行业全成分股`、`指数样本代理` 或 `缓存样本代理`。
- [ ] 样本代理时展示“仅代表当前样本，不代表完整行业”的提示。
- [ ] 更新 `docs/data-rules.md`，记录 `industry_members` 表契约、同步策略和降级规则。
- [ ] 更新 `docs/decisions.md`，记录行业数据口径优化决策。
- [ ] 更新 `docs/handoff.md`，记录最新状态、验证命令和注意事项。
- [ ] 必要时更新 `README.md` 的同步和 dashboard 使用说明。

## 6. 测试与验证

- [ ] 增加行业成分同步单元测试或聚焦集成测试。
- [ ] 增加 dashboard pipeline 测试：全成分可用时下游只消费该行业成分股。
- [ ] 增加 dashboard pipeline 测试：成分缺失时降级为样本代理并标注原因。
- [ ] 增加 snapshot/data fingerprint 测试，覆盖 `industry_members` 变化。
- [ ] 增加 HTML 渲染测试，覆盖全成分和样本代理文案。
- [ ] 运行 `/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest tests.test_dashboard_pipeline`。
- [ ] 运行 `/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest tests.test_dashboard_html`。
- [ ] 运行完整测试：`/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest discover -s tests`。
- [ ] 重新生成 `.cache/reports/dashboard_latest.html`。
- [ ] 运行 `git diff --check` 和 `codegraph sync`。
