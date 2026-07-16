"""Run the full selection pipeline and build dashboard data."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pandas as pd

from common import cache_dir, db_path
from dashboard.health import audit_dashboard_model
from dashboard.stock_types import annotate_stock_types, filter_by_stock_types, load_stock_type_rules, parse_stock_types
from dashboard.market_state import compute_dynamic_thresholds, detect
from dashboard.view_model import build_dashboard_view_model
from plan.trade_plan import run_trade_plan
from strategies import sector_screen
from strategies.coarse.registry import run_combo
from strategies.fine.technical import run as run_fine


RECENT_HIGH_GOOD_WINDOW_DAYS = 30
RECENT_HIGH_GOOD_HIGHLIGHT_MIN_COUNT = 4
RECENT_HIGH_GOOD_CACHE_VERSION = 1


def _recent_hits_cache_path():
    return cache_dir() / "recent_high_good_hits.json"


def _dashboard_data_fingerprint() -> dict:
    path = db_path()
    if not path.exists():
        return {"db_path": str(path), "missing": True}
    tables = {
        "quotes_daily": ["trade_date", "updated_at"],
        "financial_reports": ["report_date", "updated_at"],
        "market_cap_snapshot": ["as_of_date", "updated_at"],
        "index_constituents": ["constituent_date", "weight_date", "updated_at"],
        "industry_members": ["updated_at"],
        "stocks": ["updated_at"],
    }
    conn = sqlite3.connect(path)
    try:
        fingerprint = {"db_path": str(path), "tables": {}}
        existing_tables = {
            str(row[0])
            for row in conn.execute("select name from sqlite_master where type='table'").fetchall()
        }
        for table, date_columns in tables.items():
            if table not in existing_tables:
                fingerprint["tables"][table] = {"missing": True}
                continue
            columns = {str(row[1]) for row in conn.execute(f"pragma table_info({table})").fetchall()}
            selected_columns = [column for column in date_columns if column in columns]
            expressions = ["count(*)", *[f"max({column})" for column in selected_columns]]
            row = conn.execute(f"select {', '.join(expressions)} from {table}").fetchone()
            table_fingerprint = {"count": int(row[0] or 0)}
            for index, column in enumerate(selected_columns, start=1):
                table_fingerprint[f"max_{column}"] = row[index]
            fingerprint["tables"][table] = table_fingerprint
        return fingerprint
    except Exception:
        return {"db_path": str(path), "unavailable": True}
    finally:
        conn.close()


def _cache_arg_value(args, key: str):
    value = getattr(args, key, "")
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return str(value)


def _recent_hits_cache_key(model: dict, args, as_of_date: str, signal_dates: list[str], current_codes: set[str]) -> str:
    summary = model.get("summary") or {}
    identity = {
        "version": RECENT_HIGH_GOOD_CACHE_VERSION,
        "window_days": RECENT_HIGH_GOOD_WINDOW_DAYS,
        "highlight_min_count": RECENT_HIGH_GOOD_HIGHLIGHT_MIN_COUNT,
        "as_of_date": as_of_date,
        "signal_dates": signal_dates,
        "current_codes": sorted(current_codes),
        "adaptive_thresholds": summary.get("adaptive_thresholds") or {},
        "data": _dashboard_data_fingerprint(),
        "args": {
            key: _cache_arg_value(args, key)
            for key in [
                "source",
                "strategy",
                "coarse_strategy",
                "universe",
                "universe_index_symbol",
                "sector",
                "stock_types",
                "stock_type_config",
                "report_date",
                "top",
                "sector_top",
                "combo_top",
            ]
        },
    }
    raw = json.dumps(identity, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_recent_hits_cache(key: str, current_codes: set[str]) -> tuple[bool, dict[str, dict]]:
    path = _recent_hits_cache_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, {}
    entry = payload.get(key) if isinstance(payload, dict) else None
    if not isinstance(entry, dict):
        return False, {}
    hits = entry.get("hits")
    if not isinstance(hits, dict):
        return True, {}
    filtered: dict[str, dict] = {}
    for raw_code, raw_info in hits.items():
        code = str(raw_code).zfill(6)
        if code not in current_codes or not isinstance(raw_info, dict):
            continue
        dates = [str(item) for item in raw_info.get("dates", []) if item]
        count = int(raw_info.get("count", len(dates)) or 0)
        filtered[code] = {
            "count": count,
            "dates": dates,
            "window_start": str(raw_info.get("window_start") or ""),
            "window_end": str(raw_info.get("window_end") or ""),
            "highlight": bool(raw_info.get("highlight", count >= RECENT_HIGH_GOOD_HIGHLIGHT_MIN_COUNT)),
        }
    return True, filtered


def _save_recent_hits_cache(key: str, hits: dict[str, dict]) -> None:
    path = _recent_hits_cache_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload[key] = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hits": hits,
    }
    if len(payload) > 100:
        ordered = sorted(payload.items(), key=lambda item: str((item[1] or {}).get("created_at") or ""))
        payload = dict(ordered[-100:])
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def _attention_ranked_candidates(fine: pd.DataFrame) -> pd.DataFrame:
    """Rank fine rows by macro potential first and technical timing second."""

    if fine.empty:
        return fine.copy()
    ranked = fine.copy()
    macro_source = ranked["combo_score"] if "combo_score" in ranked.columns else ranked.get("coarse_score", 0)
    if not isinstance(macro_source, pd.Series):
        macro_source = pd.Series([macro_source] * len(ranked), index=ranked.index)
    technical_source = ranked.get("technical_score", 0)
    if not isinstance(technical_source, pd.Series):
        technical_source = pd.Series([technical_source] * len(ranked), index=ranked.index)
    macro = pd.to_numeric(macro_source, errors="coerce").fillna(0)
    technical = pd.to_numeric(technical_source, errors="coerce").fillna(0)
    if "coarse_score" not in ranked.columns:
        ranked["coarse_score"] = macro
    if "technical_score" not in ranked.columns:
        ranked["technical_score"] = technical
    ranked["attention_score"] = macro * 0.65 + technical * 0.35
    return ranked.sort_values(["attention_score", "coarse_score", "technical_score"], ascending=[False, False, False]).copy()


def _build_backtest_model(model: dict, args) -> dict | None:
    if getattr(args, "_skip_backtest", False):
        return None
    signal_inputs = _build_signal_inputs(model, args)
    if signal_inputs is None:
        return None
    signal_date, candidates, quotes, _signal_model = signal_inputs

    from backtest.signal_backtest import build_signal_backtest_model, parse_holding_days

    return build_signal_backtest_model(
        candidates,
        quotes,
        signal_date=signal_date,
        top=int(getattr(args, "backtest_top", 10) or 10),
        holding_days=parse_holding_days(getattr(args, "holding_days", "")),
    )


def _build_signal_validation_model(model: dict, args) -> dict | None:
    if getattr(args, "_skip_signal_validation", False):
        return None
    signal_inputs = _build_signal_inputs(model, args)
    if signal_inputs is None:
        return None
    signal_date, candidates, quotes, _signal_model = signal_inputs

    from backtest.signal_backtest import build_signal_validation_model, parse_holding_days

    return build_signal_validation_model(
        candidates,
        quotes,
        signal_date=signal_date,
        holding_days=parse_holding_days(getattr(args, "holding_days", "")),
        bucket_size=int(getattr(args, "bucket_size", 10) or 10),
        macro_threshold=getattr(args, "macro_potential_threshold", None),
        tech_threshold=getattr(args, "technical_timing_threshold", None),
    )


def _build_operation_backtest_model(model: dict, args) -> dict | None:
    if getattr(args, "_skip_operation_backtest", False):
        return None
    signal_inputs = _build_signal_inputs(model, args)
    if signal_inputs is None:
        return None
    signal_date, _candidates, quotes, signal_model = signal_inputs

    from backtest.operation_backtest import DEFAULT_PROFIT_TARGET_PCT, build_operation_backtest_model, plans_from_dashboard_model

    plans = plans_from_dashboard_model(signal_model)
    return build_operation_backtest_model(
        plans,
        quotes,
        signal_date=signal_date,
        profit_target_pct=float(getattr(args, "operation_profit_target", DEFAULT_PROFIT_TARGET_PCT) or DEFAULT_PROFIT_TARGET_PCT),
        macro_threshold=getattr(args, "macro_potential_threshold", None),
        tech_threshold=getattr(args, "technical_timing_threshold", None),
    )


def _build_signal_inputs(model: dict, args) -> tuple[str, pd.DataFrame, pd.DataFrame, dict] | None:
    if getattr(args, "_signal_inputs", None) is not None:
        return getattr(args, "_signal_inputs")
    signal_date = str(getattr(args, "backtest_date", "") or getattr(args, "as_of_date", "") or "").strip()
    if not signal_date:
        return None

    from backtest.repository import load_forward_quotes
    from backtest.signal_backtest import candidates_from_dashboard_model

    signal_model = model
    matrix_date = str(getattr(args, "as_of_date", "") or "").strip()
    if signal_date != matrix_date:
        signal_args = SimpleNamespace(**vars(args))
        signal_args.as_of_date = signal_date
        signal_args.backtest_date = ""
        signal_args._skip_backtest = True
        signal_args._skip_signal_validation = True
        signal_args._skip_operation_backtest = True
        signal_args._skip_recent_high_good_hits = True
        signal_args._signal_inputs = None
        signal_model = run_dashboard(signal_args)

    candidates = candidates_from_dashboard_model(signal_model)
    codes = candidates["code"].astype(str).str.zfill(6).dropna().unique().tolist() if "code" in candidates.columns else []
    quotes = load_forward_quotes(codes, after_date=signal_date)
    result = (signal_date, candidates, quotes, signal_model)
    setattr(args, "_signal_inputs", result)
    return result


def _recent_hit_bounds(as_of_date: str) -> tuple[str, str]:
    end = datetime.strptime(as_of_date, "%Y-%m-%d").date()
    start = end - timedelta(days=RECENT_HIGH_GOOD_WINDOW_DAYS)
    return start.isoformat(), end.isoformat()


def _latest_trade_date_from_model(model: dict) -> str:
    dates = []
    for stage in model.get("stages", []):
        for row in stage.get("rows", []):
            value = row.get("latest_trade_date")
            if value:
                dates.append(str(value))
    return max(dates) if dates else ""


def _recent_hit_end_date(model: dict, args) -> str:
    explicit = str(getattr(args, "as_of_date", "") or "").strip()
    if explicit:
        return explicit
    summary_date = str((model.get("summary") or {}).get("as_of_date") or "").strip()
    if summary_date:
        return summary_date
    return _latest_trade_date_from_model(model)


def _recent_signal_dates(as_of_date: str, window_days: int = RECENT_HIGH_GOOD_WINDOW_DAYS) -> list[str]:
    try:
        end = datetime.strptime(as_of_date, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return []
    start = end - timedelta(days=window_days)
    conn = sqlite3.connect(db_path())
    try:
        rows = conn.execute(
            """
            select distinct trade_date
            from quotes_daily
            where trade_date>=? and trade_date<=?
            order by trade_date
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    except Exception:
        return []
    finally:
        conn.close()
    return [str(row[0]) for row in rows if row and row[0]]


def _score_column(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce")
    return pd.Series(float("nan"), index=df.index)


def _high_good_codes_from_model(model: dict) -> set[str]:
    from backtest.signal_backtest import candidates_from_dashboard_model

    candidates = candidates_from_dashboard_model(model)
    if candidates.empty or "code" not in candidates.columns:
        return set()
    thresholds = (model.get("summary") or {}).get("adaptive_thresholds") or {}
    macro_threshold = float(thresholds.get("macro_potential_threshold") or 80)
    tech_threshold = float(thresholds.get("technical_timing_threshold") or 75)
    macro = _score_column(candidates, "combo_score").fillna(_score_column(candidates, "coarse_score")).fillna(0)
    macro = macro.where(macro > 1, macro * 100)
    technical = _score_column(candidates, "technical_score").fillna(0)
    codes = candidates["code"].astype(str).str.zfill(6)
    matched = candidates[(macro >= macro_threshold) & (technical >= tech_threshold)].copy()
    if matched.empty:
        return set()
    return set(codes.loc[matched.index].tolist())


def _collect_recent_high_good_hits(model: dict, args) -> dict[str, dict]:
    if getattr(args, "_skip_recent_high_good_hits", False):
        return {}
    as_of_date = _recent_hit_end_date(model, args)
    if not as_of_date:
        return {}
    current_codes = _high_good_codes_from_model(model)
    if not current_codes:
        return {}
    signal_dates = _recent_signal_dates(as_of_date)
    if not signal_dates:
        return {}
    cache_key = _recent_hits_cache_key(model, args, as_of_date, signal_dates, current_codes)
    cache_hit, cached_hits = _load_recent_hits_cache(cache_key, current_codes)
    if cache_hit:
        return cached_hits

    hit_dates_by_code = {code: [] for code in current_codes}
    for signal_date in signal_dates:
        if signal_date == as_of_date:
            signal_model = model
        else:
            signal_args = SimpleNamespace(**vars(args))
            signal_args.as_of_date = signal_date
            signal_args.backtest_date = ""
            signal_args._skip_backtest = True
            signal_args._skip_signal_validation = True
            signal_args._skip_operation_backtest = True
            signal_args._skip_recent_high_good_hits = True
            signal_args._signal_inputs = None
            signal_model = run_dashboard(signal_args)
        for code in _high_good_codes_from_model(signal_model) & current_codes:
            hit_dates_by_code.setdefault(code, []).append(signal_date)

    window_start, window_end = _recent_hit_bounds(as_of_date)
    hits = {
        code: {
            "count": len(dates),
            "dates": dates,
            "window_start": window_start,
            "window_end": window_end,
            "highlight": len(dates) >= RECENT_HIGH_GOOD_HIGHLIGHT_MIN_COUNT,
        }
        for code, dates in hit_dates_by_code.items()
        if dates
    }
    _save_recent_hits_cache(cache_key, hits)
    return hits


def _empty_recent_hit_info(window_start: str, window_end: str) -> dict:
    return {
        "count": 0,
        "dates": [],
        "window_start": window_start,
        "window_end": window_end,
        "highlight": False,
    }


def _annotate_recent_high_good_hits(model: dict, hits_by_code: dict[str, dict], args) -> None:
    as_of_date = _recent_hit_end_date(model, args)
    if as_of_date:
        try:
            window_start, window_end = _recent_hit_bounds(as_of_date)
        except (TypeError, ValueError):
            window_start, window_end = "", as_of_date
    else:
        window_start, window_end = "", ""
    model.setdefault("summary", {})["recent_high_good_hits"] = {
        "window_start": window_start,
        "window_end": window_end,
        "window_days": RECENT_HIGH_GOOD_WINDOW_DAYS,
        "highlight_min_count": RECENT_HIGH_GOOD_HIGHLIGHT_MIN_COUNT,
    }
    for stage in model.get("stages", []):
        if stage.get("key") not in {"fine", "plan"}:
            continue
        columns = stage.setdefault("columns", [])
        if "recent_high_good_hits" not in columns:
            columns.append("recent_high_good_hits")
        for row in stage.get("rows", []):
            code = str(row.get("code") or "").zfill(6)
            row["recent_high_good_hits"] = hits_by_code.get(code) or _empty_recent_hit_info(window_start, window_end)


def run_dashboard(args) -> dict:
    """Run each existing stage and return a dashboard view model."""

    stock_type_rules = load_stock_type_rules(getattr(args, "stock_type_config", None))
    selected_stock_types = parse_stock_types(getattr(args, "stock_types", ""))
    sector_args = SimpleNamespace(**vars(args))
    sector_args.top = getattr(args, "sector_top", 100)
    combo_args = SimpleNamespace(**vars(args))
    combo_args.top = getattr(args, "combo_top", 100)
    fine_args = SimpleNamespace(**vars(args))

    sector_result, sector_meta = sector_screen.run(sector_args)
    sector_result = annotate_stock_types(sector_result, stock_type_rules)
    combo_candidates = filter_by_stock_types(sector_result, selected_stock_types)
    # 提前检测市场状态，传入粗筛阶段做动量防御调整
    market_state = detect(
        sector_result["code"].astype(str).str.zfill(6).tolist() if not sector_result.empty else [],
        as_of_date=getattr(args, "as_of_date", None) or None,
    )
    combo, combo_meta = run_combo(combo_args, candidates=combo_candidates, market_state=market_state.regime)
    fine_args.top = len(combo) if not combo.empty else getattr(args, "top", 20)
    fine, fine_meta = run_fine(fine_args, candidates=combo)
    if not combo.empty and not fine.empty and "combo_score" in combo.columns and "combo_score" not in fine.columns:
        combo_scores = combo[["code", "combo_score"]].copy()
        fine = fine.merge(combo_scores, on="code", how="left")
    # 防御模式下仓位上限打折
    if market_state.regime != "bull":
        original_max = getattr(args, "max_position", 0.25) or 0.25
        setattr(args, "max_position", round(original_max * market_state.position_multiplier, 4))
    # 动态阈值：根据当前候选股分数分布自适应象限线
    adaptive_thresholds = compute_dynamic_thresholds(
        combo_scores=pd.to_numeric(fine.get("combo_score", pd.Series(dtype=float)), errors="coerce").dropna().tolist() if not fine.empty else [],
        technical_scores=pd.to_numeric(fine.get("technical_score", pd.Series(dtype=float)), errors="coerce").dropna().tolist() if not fine.empty else [],
    )
    plan_candidates = _attention_ranked_candidates(fine)
    plan, plan_meta = run_trade_plan(args, candidates=plan_candidates)
    if not plan.empty and not plan_candidates.empty:
        enrich_cols = [col for col in ["code", "attention_score", "coarse_score"] if col in plan_candidates.columns]
        if len(enrich_cols) > 1:
            plan = plan.merge(plan_candidates[enrich_cols], on="code", how="left")
        if "attention_score" in plan.columns:
            sort_cols = [col for col in ["attention_score", "technical_score"] if col in plan.columns]
            plan = plan.sort_values(sort_cols, ascending=[False] * len(sort_cols))
    plan_meta = {**plan_meta, "selected": len(plan)}

    stages: dict[str, pd.DataFrame] = {
        "sector_screen": sector_result,
        "combo": combo,
        "fine": fine,
        "plan": plan,
    }
    metas = {
        "sector_screen": sector_meta,
        "combo": combo_meta,
        "fine": fine_meta,
        "plan": plan_meta,
    }
    model = build_dashboard_view_model(stages, metas, stock_type_rules=stock_type_rules)
    model["summary"]["stock_type_filter"] = {
        "selected_types": selected_stock_types,
        "before_count": len(sector_result),
        "after_count": len(combo_candidates),
        "config_path": stock_type_rules.source_path,
    }
    model["summary"]["as_of_date"] = getattr(args, "as_of_date", "") or ""
    model["summary"]["backtest_date"] = getattr(args, "backtest_date", "") or getattr(args, "as_of_date", "") or ""
    model["summary"]["universe"] = getattr(args, "universe", "") or ""
    model["summary"]["universe_index_symbol"] = getattr(args, "universe_index_symbol", "") or ""
    model["summary"]["sector"] = getattr(args, "sector", "") or ""
    model["summary"]["market_state"] = {
        "label": market_state.label,
        "regime": market_state.regime,
        "median_close_vs_ma20": market_state.median_close_vs_ma20 if pd.notna(market_state.median_close_vs_ma20) else None,
        "median_ma20_slope": market_state.median_ma20_slope if pd.notna(market_state.median_ma20_slope) else None,
        "breadth_pct": market_state.breadth_pct if pd.notna(market_state.breadth_pct) else None,
        "bull_votes": market_state.bull_votes,
        "sample_count": market_state.sample_count,
        "position_multiplier": market_state.position_multiplier,
        "note": market_state.note,
    }
    model["summary"]["adaptive_thresholds"] = adaptive_thresholds
    setattr(args, "macro_potential_threshold", adaptive_thresholds.get("macro_potential_threshold"))
    setattr(args, "technical_timing_threshold", adaptive_thresholds.get("technical_timing_threshold"))
    recent_hits = _collect_recent_high_good_hits(model, args)
    _annotate_recent_high_good_hits(model, recent_hits, args)
    model["summary"]["health"] = audit_dashboard_model(model)
    backtest = _build_backtest_model(model, args)
    if backtest is not None:
        model["backtest"] = backtest
    signal_validation = _build_signal_validation_model(model, args)
    if signal_validation is not None:
        model["signal_validation"] = signal_validation
    operation_backtest = _build_operation_backtest_model(model, args)
    if operation_backtest is not None:
        model["operation_backtest"] = operation_backtest
    return model
