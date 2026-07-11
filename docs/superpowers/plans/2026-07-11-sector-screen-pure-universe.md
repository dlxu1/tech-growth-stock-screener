# Sector Screen Pure Universe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `sector-screen` a pure board/universe selection stage instead of a scoring strategy.

**Architecture:** Keep board filtering in `strategies/coarse/repository.py`, because all downstream stages already build from that normalized base universe. Change `strategies/sector_screen.py` so it only formats, annotates, and caps the matched universe, with market-cap ordering used only as a stable display truncation rule when more than 100 rows match.

**Tech Stack:** Python, pandas, unittest, existing CLI/report/dashboard pipeline.

---

### Task 1: Pin Pure Board Selection Behavior

**Files:**
- Modify: `tests/test_sector_screen.py`

- [ ] **Step 1: Write the failing test**

Replace the score-order assertion with assertions that `sector_score` is absent, `match_reason` is present, and the capped result is ordered by `market_cap` for display truncation.

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python -m unittest tests.test_sector_screen -v`

Expected: FAIL because current `sector-screen` still returns `sector_score` and `score_reason`.

### Task 2: Remove Sector Scoring From Implementation

**Files:**
- Modify: `scripts/strategies/sector_screen.py`

- [ ] **Step 1: Remove score helpers and score output**

Delete sector score ranking logic and replace `score_reason` with `match_reason`.

- [ ] **Step 2: Cap by stable display order**

Sort by `market_cap` descending before applying the 100-row cap, without calling it a scoring strategy.

- [ ] **Step 3: Run the targeted test to verify it passes**

Run: `/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python -m unittest tests.test_sector_screen -v`

Expected: PASS.

### Task 3: Update Report Wording And Verify Dashboard

**Files:**
- Modify: `scripts/reports/sector_screen_markdown.py`

- [ ] **Step 1: Replace board score wording**

Render `match_reason` and remove “板块分”.

- [ ] **Step 2: Run all tests**

Run: `/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python -m unittest discover -s tests -v`

Expected: PASS.

- [ ] **Step 3: Regenerate latest dashboard**

Run: `/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python scripts/run.py dashboard --universe csi300 --sector 半导体 --capital 15000 --source cache --output .cache/reports/dashboard_latest.html`

Expected: `.cache/reports/dashboard_latest.html` is updated with the pure board selection result.
