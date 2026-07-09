"""Pre-run cache freshness checks and optional data updates."""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from common import db_path, report_date_candidates
from data.sources import sync_dataset


POLICIES = ("none", "cache", "auto", "strict", "refresh")
DAILY_COMMANDS = {"combo", "fine", "plan"}
COARSE_COMMANDS = {"screen", "coarse", "combo", "fine", "plan"}


@dataclass
class PreflightStep:
    dataset: str
    status: str
    detail: str
    rows: int | None = None


def _log(message: str) -> None:
    print(f"[preflight] {message}", file=sys.stderr, flush=True)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _today() -> date:
    return date.today()


def _default_update_end(args: Any) -> str:
    explicit = getattr(args, "update_end", None)
    if explicit:
        return explicit
    return _today().isoformat()


def _default_update_start(args: Any, end: str) -> str:
    explicit = getattr(args, "update_start", None)
    if explicit:
        return explicit
    end_date = _parse_date(end) or _today()
    window_days = int(getattr(args, "update_daily_window_days", 180) or 180)
    return (end_date - timedelta(days=window_days)).isoformat()


def _connect_readonly() -> sqlite3.Connection:
    return sqlite3.connect(db_path())


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (table,),
    ).fetchone()
    return row is not None


def _cache_meta(conn: sqlite3.Connection, table_key: str) -> dict[str, Any] | None:
    if not _table_exists(conn, "cache_meta"):
        return None
    row = conn.execute(
        """
        select table_key, source, fetched_at, row_count, status, error
        from cache_meta
        where table_key=?
        """,
        (table_key,),
    ).fetchone()
    if not row:
        return None
    return {
        "table_key": row[0],
        "source": row[1],
        "fetched_at": row[2],
        "row_count": row[3],
        "status": row[4],
        "error": row[5],
    }


def _age_days(fetched_at: str | None) -> int | None:
    if not fetched_at:
        return None
    try:
        fetched = datetime.fromisoformat(str(fetched_at)).date()
    except ValueError:
        return None
    return (_today() - fetched).days


def _meta_fresh(conn: sqlite3.Connection, table_key: str, max_age_days: int) -> tuple[bool, str]:
    meta = _cache_meta(conn, table_key)
    if not meta or meta.get("status") != "ok":
        return False, "missing cache_meta"
    age = _age_days(meta.get("fetched_at"))
    if age is None:
        return False, "invalid fetched_at"
    if age > max_age_days:
        return False, f"stale {age}d > {max_age_days}d"
    return True, f"fresh {age}d, rows={meta.get('row_count')}"


def _financial_fresh(conn: sqlite3.Connection, report_date: str, max_age_days: int = 120) -> tuple[bool, str]:
    candidates = report_date_candidates() if report_date == "auto" else [report_date]
    for rd in candidates:
        fresh, detail = _meta_fresh(conn, f"stock_yjbb_{rd}", max_age_days)
        if fresh:
            return True, f"{rd}: {detail}"
    return False, "no fresh financial report cache"


def _index_fresh(conn: sqlite3.Connection, index_symbol: str, max_age_days: int) -> tuple[bool, str, list[str]]:
    if not _table_exists(conn, "index_constituents"):
        return False, "missing index_constituents table", []
    row = conn.execute(
        """
        select max(constituent_date), max(updated_at), count(distinct code)
        from index_constituents
        where index_symbol=?
        """,
        (index_symbol,),
    ).fetchone()
    if not row or not row[0] or not row[2]:
        return False, f"no cached index constituents for {index_symbol}", []
    constituent_date, updated_at, count = row
    age = _age_days(updated_at)
    if age is None or age > max_age_days:
        return False, f"{index_symbol} stale by updated_at={updated_at}, constituent_date={constituent_date}, members={count}", []
    codes = [
        str(item[0]).zfill(6)
        for item in conn.execute(
            """
            select distinct code
            from index_constituents
            where index_symbol=? and constituent_date=?
            order by code
            """,
            (index_symbol, constituent_date),
        ).fetchall()
    ]
    return True, f"{index_symbol} constituent_date={constituent_date}, members={count}, updated {age}d ago", codes


def _index_codes(conn: sqlite3.Connection, index_symbol: str) -> list[str]:
    if not _table_exists(conn, "index_constituents"):
        return []
    row = conn.execute(
        "select max(constituent_date) from index_constituents where index_symbol=?",
        (index_symbol,),
    ).fetchone()
    if not row or not row[0]:
        return []
    return [
        str(item[0]).zfill(6)
        for item in conn.execute(
            """
            select distinct code
            from index_constituents
            where index_symbol=? and constituent_date=?
            order by code
            """,
            (index_symbol, row[0]),
        ).fetchall()
    ]


def _daily_fresh(conn: sqlite3.Connection, codes: list[str], start: str, end: str) -> tuple[bool, str]:
    if not codes:
        return False, "no symbols available for daily price check"
    if not _table_exists(conn, "quotes_daily"):
        return False, "missing quotes_daily table"
    placeholders = ",".join("?" for _ in codes)
    rows = conn.execute(
        f"""
        select code, min(trade_date), max(trade_date), count(distinct trade_date)
        from quotes_daily
        where code in ({placeholders})
        group by code
        """,
        codes,
    ).fetchall()
    coverage = {str(row[0]).zfill(6): row for row in rows}
    covered = 0
    stale = []
    for code in codes:
        row = coverage.get(code)
        if not row:
            stale.append(code)
            continue
        first_date, last_date = row[1], row[2]
        if first_date and last_date and first_date <= start and last_date >= end:
            covered += 1
        else:
            stale.append(code)
    if covered == len(codes):
        return True, f"daily prices cover {covered}/{len(codes)} symbols for {start}..{end}"
    sample = ",".join(stale[:5])
    return False, f"daily prices cover {covered}/{len(codes)} symbols for {start}..{end}; missing/stale sample={sample}"


def _needs_daily(args: Any) -> bool:
    if args.command in DAILY_COMMANDS:
        return True
    if args.command == "visualize" and getattr(args, "dataset", "") in DAILY_COMMANDS:
        return True
    return False


def _needs_coarse_bundle(args: Any) -> bool:
    if args.command in COARSE_COMMANDS:
        return True
    if args.command == "visualize" and getattr(args, "dataset", "") in {"coarse", "combo", "fine"}:
        return True
    return False


def _needs_index_constituents_report(args: Any) -> bool:
    return args.command == "visualize" and getattr(args, "dataset", "") == "index_constituents"


def _resolve_index_symbol(args: Any) -> str:
    if _needs_index_constituents_report(args):
        return getattr(args, "index_symbol", "000300")
    return getattr(args, "universe_index_symbol", getattr(args, "index_symbol", "000300"))


def _run_sync(args: Any, dataset: str, *, refresh: bool, codes: list[str] | None = None, start: str | None = None, end: str | None = None) -> dict:
    return sync_dataset(
        dataset,
        getattr(args, "report_date", "auto"),
        refresh,
        getattr(args, "no_proxy", False),
        getattr(args, "source", "auto"),
        codes=codes,
        start=start,
        end=end,
        adjust=getattr(args, "update_adjust", "qfq"),
        index_symbol=_resolve_index_symbol(args),
        skip_existing=True,
    )


def _sync_or_handle(args: Any, steps: list[PreflightStep], dataset: str, detail: str, *, refresh: bool, strict: bool, **kwargs) -> None:
    _log(f"{dataset}: updating ({detail})")
    try:
        result = _run_sync(args, dataset, refresh=refresh, **kwargs)
        rows = int(result.get("rows", 0) or 0)
        steps.append(PreflightStep(dataset, "updated", detail, rows))
        _log(f"{dataset}: updated rows={rows}")
    except Exception as exc:
        steps.append(PreflightStep(dataset, "error", str(exc)))
        _log(f"{dataset}: update failed: {exc}")
        if strict:
            raise


def apply_update_policy(args: Any) -> list[PreflightStep]:
    """Apply the requested update policy before a non-sync command runs."""

    policy = getattr(args, "update_policy", "none")
    if policy not in POLICIES:
        raise RuntimeError(f"Unsupported update policy: {policy}")
    if policy == "none" or getattr(args, "command", "") == "sync":
        return []
    steps: list[PreflightStep] = []
    if policy == "cache":
        setattr(args, "source", "cache")
        steps.append(PreflightStep("all", "cache", "offline cache mode; no preflight network updates"))
        _log("cache mode enabled; no network updates will be attempted")
        return steps

    strict = policy in {"strict", "refresh"}
    force_refresh = policy == "refresh" or bool(getattr(args, "refresh", False))
    index_symbol = _resolve_index_symbol(args)
    universe = getattr(args, "universe", "tech")
    update_end = _default_update_end(args)
    update_start = _default_update_start(args, update_end)

    conn = _connect_readonly()
    try:
        if _needs_coarse_bundle(args):
            spot_max_age = int(getattr(args, "update_spot_max_age_days", 1) or 1)
            fresh, detail = _meta_fresh(conn, "stock_zh_a_spot", spot_max_age)
            if force_refresh or not fresh:
                _sync_or_handle(args, steps, "spot", detail, refresh=force_refresh or not fresh, strict=strict)
            else:
                steps.append(PreflightStep("spot", "fresh", detail))
                _log(f"spot: {detail}")

            fresh, detail = _financial_fresh(conn, getattr(args, "report_date", "auto"))
            if force_refresh or not fresh:
                _sync_or_handle(args, steps, "financials", detail, refresh=force_refresh or not fresh, strict=strict)
            else:
                steps.append(PreflightStep("financials", "fresh", detail))
                _log(f"financials: {detail}")

            if universe == "csi300":
                index_max_age = int(getattr(args, "update_index_max_age_days", 7) or 7)
                fresh, detail, _ = _index_fresh(conn, index_symbol, index_max_age)
                if force_refresh or not fresh:
                    _sync_or_handle(args, steps, "index_constituents", detail, refresh=force_refresh or not fresh, strict=strict)
                else:
                    steps.append(PreflightStep("index_constituents", "fresh", detail))
                    _log(f"index_constituents: {detail}")
            else:
                fresh, detail = _meta_fresh(conn, "stock_board_industry_name", 30)
                if force_refresh or not fresh:
                    _sync_or_handle(args, steps, "industry_boards", detail, refresh=force_refresh or not fresh, strict=strict)
                else:
                    steps.append(PreflightStep("industry_boards", "fresh", detail))
                    _log(f"industry_boards: {detail}")

        if _needs_index_constituents_report(args):
            index_max_age = int(getattr(args, "update_index_max_age_days", 7) or 7)
            fresh, detail, _ = _index_fresh(conn, index_symbol, index_max_age)
            if force_refresh or not fresh:
                _sync_or_handle(args, steps, "index_constituents", detail, refresh=force_refresh or not fresh, strict=strict)
            else:
                steps.append(PreflightStep("index_constituents", "fresh", detail))
                _log(f"index_constituents: {detail}")

        if _needs_daily(args):
            if universe != "csi300":
                detail = "daily auto-update currently requires --universe csi300; strategy will use cached quotes and report missing data"
                steps.append(PreflightStep("daily_prices", "skipped", detail))
                _log(f"daily_prices: skipped ({detail})")
            else:
                codes = _index_codes(conn, index_symbol)
                fresh, detail = _daily_fresh(conn, codes, update_start, update_end)
                if force_refresh or not fresh:
                    _sync_or_handle(
                        args,
                        steps,
                        "daily_prices",
                        detail,
                        refresh=force_refresh,
                        strict=strict,
                        codes=codes,
                        start=update_start,
                        end=update_end,
                    )
                else:
                    steps.append(PreflightStep("daily_prices", "fresh", detail))
                    _log(f"daily_prices: {detail}")
    finally:
        conn.close()
    return steps


__all__ = ["POLICIES", "PreflightStep", "apply_update_policy"]
