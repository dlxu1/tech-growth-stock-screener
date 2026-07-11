# New Thread Prompt

Copy this into a new Codex thread when the current conversation is too long:

```text
继续 /Users/xudoulei/work/tech-growth-stock-screener 项目。

请先恢复上下文：
1. 读 AGENTS.md。
2. 读 docs/project-context.md。
3. 读 docs/data-rules.md。
4. 读 docs/decisions.md。
5. 读 docs/handoff.md。
6. 因为仓库有 .codegraph/，请先用 CodeGraph 定位相关代码，再读文件或修改。

当前目标：继续维护 A 股科技股分层筛选仪表盘。核心流程必须保持串行：
板块筛选 -> 宏观粗筛 -> 技术细筛 -> 操作计划 -> 个人配置。

除非我特别要求刷新远程数据，否则优先使用 --source cache。
修改 dashboard 后，请重新生成：
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python scripts/run.py dashboard --source cache --output .cache/reports/dashboard_latest.html
```

