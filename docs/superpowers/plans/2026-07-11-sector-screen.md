# Sector Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dashboard's confusing `screen + coarse` first two stages with one `sector-screen` stage that can filter a chosen base universe, such as CSI 300, by sector terms and keep at most 100 stocks.

**Architecture:** Add a sector filter helper in the coarse repository so every downstream stage shares the same filtered base universe. Add `strategies/sector_screen.py` for a single first-stage ranked list, then update dashboard pipeline/view model to show `sector-screen -> combo -> fine -> plan -> allocation`.

**Tech Stack:** Python standard library, pandas, existing SQLite/cache-backed data assembly, unittest.

---

### Task 1: Sector Filter and Sector Screen Core

**Files:**
- Create: `scripts/strategies/sector_screen.py`
- Modify: `scripts/strategies/coarse/repository.py`
- Test: `tests/test_sector_screen.py`

- [ ] Write failing tests for comma-separated sector filtering and top cap at 100.
- [ ] Implement `filter_by_sector(base, sector_text)` using `board_name` text contains matching.
- [ ] Implement `sector_screen.run(args)` with unified `sector_score`, `score_reason`, `risk_flags`, and `data_note`.
- [ ] Run `python -m unittest tests/test_sector_screen.py -v`.

### Task 2: CLI and Markdown Report

**Files:**
- Modify: `scripts/run.py`
- Create: `scripts/reports/sector_screen_markdown.py`
- Test: `tests/test_sector_screen_cli.py`

- [ ] Write a failing CLI test for `sector-screen --help`.
- [ ] Register `sector-screen` with `--universe`, `--sector`, `--top`, and existing source/cache args.
- [ ] Render Markdown/JSON/CSV outputs.
- [ ] Run `python -m unittest tests/test_sector_screen_cli.py -v`.

### Task 3: Dashboard Replacement

**Files:**
- Modify: `scripts/dashboard/pipeline.py`
- Modify: `scripts/dashboard/view_model.py`
- Test: `tests/test_dashboard_pipeline.py`
- Test: `tests/test_dashboard_view_model.py`

- [ ] Update dashboard tests to expect `sector_screen` and not `screen/coarse`.
- [ ] Make dashboard run `sector_screen`, then existing `combo/fine/plan/allocation` with the same `--sector` filter applied through the base repository.
- [ ] Run dashboard tests.

### Task 4: Docs and Verification

**Files:**
- Modify: `README.md`

- [ ] Document `sector-screen --universe csi300 --sector 半导体 --top 100`.
- [ ] Run all tests.
- [ ] Run `python scripts/run.py sector-screen --universe csi300 --sector 半导体 --source cache --top 100`.
- [ ] Run `python scripts/run.py dashboard --universe csi300 --sector 半导体 --capital 15000 --source cache --output .cache/reports/dashboard_latest.html`.
- [ ] Run `git diff --check`.
