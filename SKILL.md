---
name: tech-growth-stock-screener
description: "Screen A-share technology stocks for industry leadership and real earnings growth. Use when Codex needs to find, rank, or explain technology stock candidates that satisfy: tech-sector exposure, market capitalization ranking in the top 10 of their industry/board, and positive real one-year operating growth from public financial-report data."
---

# Tech Growth Stock Screener

Use this skill to screen A-share technology stocks with three required gates:

1. Technology exposure.
2. Market capitalization rank in the top 10 within the matched technology industry board.
3. Real one-year performance growth, defined by public financial-report revenue YoY and net-profit YoY both being positive.

This skill is a research filter, not a buy/sell engine. Keep the final wording as a ranked research list with risks and validation notes.

## Quick Start

Run the layered screener:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" screen --top 30 --format markdown
```

The old wrapper is still supported:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/screen.py" --top 30 --format markdown
```

If `$SKILL` is not set, use the installed skill directory:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python /Users/xudoulei/.codex/skills/tech-growth-stock-screener/scripts/screen.py --top 30 --format markdown
```

The scripts use AKShare, Sina, efinance, pandas, and SQLite from the project virtual environment. All fetched source tables and normalized daily quotes are cached under `$SKILL/.cache/stock_data.sqlite` and reused unless `--refresh` is passed.

Use `--no-proxy` when the machine has a system proxy configured but Eastmoney/AKShare should be reached directly.

Use `--source auto` by default. It reads cache first, then tries Sina for realtime market-cap quotes, `efinance`, and AKShare/Eastmoney-compatible financial tables. Use `--source cache` for a strictly offline run from existing CSV cache.

## Workflow

1. Run `scripts/run.py sync` only when fresh source data is needed.
2. Run `scripts/run.py screen --strategy tech_growth` for the current screen.
3. Run `scripts/run.py backtest --strategy tech_growth` only after daily prices exist in `quotes_daily`.
4. If industry-board constituents cannot be fetched, allow the strategy fallback that ranks by financial-report industry plus total market capitalization.
5. If network or upstream APIs fail, report the exact failing source and suggest rerunning with `--source cache` or `--refresh` later.
6. Present candidates as a ranked research list, including:
   - stock code and name;
   - matched technology industry board;
   - market cap rank within that board;
   - revenue YoY and net-profit YoY from the selected report date;
   - why it passed;
   - what would make the candidate weaker.
7. Present Markdown results as direct numbered items, not a table.
8. Do not recommend a trade solely from this screen. For specific buy/sell timing, run a separate technical diagnosis.

## Layered Architecture

- Infrastructure layer: `scripts/infra/`; shared SQLite cache access, network fallback helpers, proxy policy, and logging.
- Coarse layer: `scripts/strategies/coarse/`; split into `network.py` for realtime source fetch, `repository.py` for cache-backed data assembly, and `registry.py` for coarse strategy logic.
- Fine layer: `scripts/strategies/fine/`; split into `network.py` for daily-price refresh hooks, `repository.py` for cached quote reads and coarse-candidate assembly, and `technical.py` for technical scoring logic.
- Plan layer: `scripts/backtest/plan/` plus `scripts/backtest/trade_plan.py`; split into realtime refresh hooks, cached quote reads, and next-session trade-plan rules.
- Display layer: `scripts/reports/`; render Markdown, JSON, or CSV output. Reports do not fetch remote data.
- Compatibility layer: `scripts/data/` still exists as a backward-compatible source adapter while the new layer structure is being iterated. New shared cache/network capabilities should go into `scripts/infra/`.

Read `references/data-schema.md` before changing cache schema, source persistence, or cross-layer data contracts.
Read `references/architecture.md` before changing layer boundaries, command flow, or cross-layer responsibilities.
Read `references/coarse-strategies.md` before changing coarse strategy names, weights, or missing-field fallback behavior.
Read `references/fine-strategies.md` before changing technical indicators, score weights, or reason labels.
Read `references/backtest-rules.md` before changing backtest assumptions.
Read `references/trade-plan-rules.md` before changing next-session entry, stop-loss, take-profit, or position rules.

## Screening Rules

Read `references/screening-rules.md` before changing thresholds, explaining why a stock passed, or relaxing any of the three required gates.

Default thresholds:

- `--industry-rank 10`
- `--min-revenue-yoy 0`
- `--min-profit-yoy 0`

Prefer keeping the default gates strict. If the user asks for a broader watchlist, widen only one gate at a time and clearly label the result as a relaxed screen.

## Useful Commands

Markdown output:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" screen --top 30 --format markdown
```

JSON output:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" screen --top 50 --format json
```

Run all coarse strategies, keeping five names per strategy:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" coarse --strategy all --top 5 --format markdown
```

Run one coarse strategy:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" coarse --strategy market_cap_reasonable_pe --top 5
```

Run technical fine screening after all coarse strategies:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" fine --coarse-strategy all --coarse-top 5 --top 10 --format markdown
```

Run technical fine screening after one coarse strategy:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" fine --coarse-strategy market_cap_reasonable_pe --coarse-top 5 --top 5
```

Generate next-session trade plans from the five fine-screened stocks:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" plan --coarse-strategy all --coarse-top 5 --top 5 --format markdown
```

Force fresh upstream data:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" screen --refresh --top 30
```

Force direct connection without proxies:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" screen --no-proxy --top 30
```

Strictly offline from existing cache:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" screen --source cache --top 30
```

Use a fixed financial report date:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" screen --report-date 20260331
```

Sync source data into SQLite:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" sync --dataset spot
```

Sync daily prices for explicit symbols:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" sync --dataset daily_prices --codes 600584,000021 --start 2024-01-01 --end 2026-07-08
```

Sync daily prices for strategy-selected symbols:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" sync --dataset daily_prices --from-strategy --top 10 --start 2024-01-01 --end 2026-07-08
```

Run the initial backtest scaffold:

```bash
/Users/xudoulei/Documents/Codex/2026-06-28/new-chat/venv/bin/python "$SKILL/scripts/run.py" backtest --start 2024-01-01 --end 2026-07-08 --top 10
```

## Output Rules

- Use Chinese for A-share results.
- State the selected financial report date.
- State that data comes from public third-party sources and may lag.
- For `--format markdown`, use a direct numbered list instead of a Markdown table.
- If proxy issues appear, retry with `--no-proxy`.
- If fewer than the requested count pass, do not pad the list with failures.
- Include excluded-count diagnostics when available.
- Avoid guaranteed-return or direct order language.
