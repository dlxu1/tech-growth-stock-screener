# Interactive Dashboard HTML Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `dashboard` CLI command that runs the existing stock-selection stages and writes one interactive offline HTML report showing every stage result.

**Architecture:** Reuse the existing CLI stage functions instead of reimplementing selection logic. Add a dashboard pipeline to collect stage DataFrames and metadata, a view-model layer to normalize rows for HTML, and a report renderer that emits a single self-contained file with tabs, global search, sortable tables, and per-stock stage traces.

**Tech Stack:** Python standard library, pandas, existing project CLI modules, static HTML/CSS/JavaScript.

---

### Task 1: Dashboard View Model

**Files:**
- Create: `scripts/dashboard/view_model.py`
- Test: `tests/test_dashboard_view_model.py`

- [ ] Write a failing `unittest` that passes staged DataFrames into `build_dashboard_view_model` and expects stage counts, allocation action counts, and per-code traces.
- [ ] Implement `build_dashboard_view_model(stages, metas)` to return a JSON-serializable dict with `stages`, `summary`, and `traces`.
- [ ] Run `python -m unittest tests/test_dashboard_view_model.py -v` and confirm it passes.

### Task 2: Dashboard HTML Renderer

**Files:**
- Create: `scripts/reports/dashboard_html.py`
- Test: `tests/test_dashboard_html.py`

- [ ] Write a failing `unittest` that calls `render_dashboard_html(view_model)` and expects a full HTML document with stage tabs, search input, embedded JSON, and stage tables.
- [ ] Implement the renderer as a single offline HTML document with inline CSS and JavaScript.
- [ ] Run `python -m unittest tests/test_dashboard_html.py -v` and confirm it passes.

### Task 3: Pipeline and CLI

**Files:**
- Create: `scripts/dashboard/pipeline.py`
- Modify: `scripts/run.py`
- Test: `tests/test_dashboard_cli.py`

- [ ] Write a failing CLI test for `python scripts/run.py dashboard --help`, expecting `--output` and `--capital`.
- [ ] Implement `run_dashboard(args)` to call `tech_growth.run`, `run_coarse`, `run_combo`, `run_fine`, `run_trade_plan`, and `run_allocation_plan`.
- [ ] Add `dashboard` to `scripts/run.py`; write the rendered HTML to `--output` or `.cache/reports/dashboard_latest.html`.
- [ ] Run `python -m unittest tests/test_dashboard_cli.py -v` and confirm it passes.

### Task 4: Documentation and Verification

**Files:**
- Modify: `README.md`

- [ ] Document `python scripts/run.py dashboard --capital 15000 --source cache`.
- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run `python scripts/run.py dashboard --capital 15000 --source cache --output .cache/reports/dashboard_latest.html`.
- [ ] Run `git diff --check`.
