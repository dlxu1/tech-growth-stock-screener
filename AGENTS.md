# AGENTS.md

This repository is a long-running A-share technology stock screening project.
When a new Codex thread starts here, first restore project context from the
files below before changing code or explaining behavior.

## Startup Reading Order

1. `docs/project-context.md` for the current product goal, stage flow, and key modules.
2. `docs/data-rules.md` for data sources, scoring formulas, display formatting, and stage contracts.
3. `docs/decisions.md` for durable design decisions and why they were made.
4. `docs/handoff.md` for the latest known state, verification commands, and suggested next checks.
5. `README.md` for user-facing command examples and broader usage notes.

## CodeGraph

In this repository, a `.codegraph/` directory exists at the repo root. Use
CodeGraph before grep/find/manual file reading when locating or understanding
code:

- Prefer MCP `codegraph_explore` when available.
- Otherwise run `codegraph explore "<question or symbol names>"`.
- After editing code, run `codegraph sync` so future threads see the updated index.

## Project Rules

- Answer the user in Chinese unless they ask otherwise.
- Treat this as a research and decision-support tool, not an investment advice engine.
- Keep the dashboard screening flow serial: `板块筛选 -> 宏观粗筛 -> 技术细筛 -> 操作建议`.
- The `操作建议` dashboard stage shows next-session plan fields only; do not include personal budget/allocation fields.
- A downstream stage must only use stocks from the previous stage.
- Preserve existing cache/offline behavior. Prefer `--source cache` for local checks unless fresh data is explicitly needed.
- Do not relax screening thresholds or scoring formulas silently. If a rule changes, update `docs/data-rules.md` and `docs/decisions.md`.
- When changing dashboard presentation, regenerate `.cache/reports/dashboard_latest.html`.

## Common Commands

Use the project virtual environment for tests and dashboard generation:

```bash
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest discover -s tests
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python /Users/xudoulei/work/tech-growth-stock-screener/scripts/run.py dashboard --source cache --output /Users/xudoulei/work/tech-growth-stock-screener/.cache/reports/dashboard_latest.html
```

Useful focused checks:

```bash
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest tests.test_dashboard_html
/Users/xudoulei/work/tech-growth-stock-screener/.venv/bin/python -m unittest tests.test_dashboard_pipeline
git diff --check
```
