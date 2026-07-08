"""Backward-compatible source adapters.

New architecture keeps shared cache/network utilities in ``scripts/infra`` and
uses layer repositories as the bridge between realtime fetches and SQLite.
This module remains as a compatibility adapter for existing fetch functions.
"""

from __future__ import annotations

import math
import time
from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd
import requests

from common import cache_dir, db_path, find_col, normalize_code, report_date_candidates, source_chain, to_number
from data.db import connect, read_cached_source, write_quotes_daily, write_source_table


def run_fetchers(label: str, fetchers: list[tuple[str, Callable[[], pd.DataFrame]]]) -> tuple[pd.DataFrame, str]:
    errors = []
    for name, fetcher in fetchers:
        try:
            df = fetcher()
            if df is not None and not df.empty:
                return df, name
            errors.append(f"{name}: empty")
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    raise RuntimeError(f"No {label} source available. " + "; ".join(errors[:5]))


def cached_source_table(table_key: str, legacy_csv: str, refresh: bool, fetcher: Callable[[], tuple[pd.DataFrame, str]]) -> tuple[pd.DataFrame, str]:
    conn = connect()
    if not refresh:
        cached = read_cached_source(conn, table_key)
        if cached is not None:
            return cached, f"db:{table_key}"
        legacy_path = cache_dir() / legacy_csv
        if legacy_path.exists():
            df = pd.read_csv(legacy_path, dtype={"代码": str, "code": str, "股票代码": str})
            write_source_table(conn, table_key, f"legacy-csv:{legacy_csv}", df)
            return df, f"db:{table_key}"
    df, source = fetcher()
    write_source_table(conn, table_key, source, df)
    return df, source


def disable_efinance_proxy(no_proxy: bool) -> None:
    if not no_proxy:
        return
    try:
        from efinance import shared

        shared.session.trust_env = False
    except Exception:
        pass


def eastmoney_get(session: requests.Session, url: str, params: dict[str, str], headers: dict[str, str], timeout: int):
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = session.get(url, params=params, timeout=timeout, headers=headers)
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            time.sleep(0.4 * attempt)
    raise RuntimeError(f"Eastmoney request failed after 3 tries: {last_error}")


def eastmoney_paginated(url: str, params: dict[str, str], no_proxy: bool, timeout: int = 15) -> pd.DataFrame:
    session = requests.Session()
    session.trust_env = not no_proxy
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html",
        "Connection": "close",
    }
    response = eastmoney_get(session, url, params.copy(), headers, timeout)
    data = response.json()["data"]
    diff = data.get("diff") or []
    if not diff:
        return pd.DataFrame()
    page_size = len(diff)
    total = int(data.get("total") or page_size)
    total_pages = math.ceil(total / page_size)
    frames = [pd.DataFrame(diff)]
    for page in range(2, total_pages + 1):
        page_params = params.copy()
        page_params["pn"] = str(page)
        time.sleep(0.15)
        response = eastmoney_get(session, url, page_params, headers, timeout)
        page_diff = (response.json().get("data") or {}).get("diff") or []
        if page_diff:
            frames.append(pd.DataFrame(page_diff))
    return pd.concat(frames, ignore_index=True)


def fetch_spot_direct(no_proxy: bool) -> pd.DataFrame:
    url = "https://82.push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": "100",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f12",
        "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
        "fields": "f12,f14,f20",
    }
    raw = eastmoney_paginated(url, params, no_proxy)
    if raw.empty:
        return pd.DataFrame(columns=["代码", "名称", "总市值"])
    return raw.rename(columns={"f12": "代码", "f14": "名称", "f20": "总市值"})[["代码", "名称", "总市值"]]


def fetch_spot_efinance(no_proxy: bool) -> pd.DataFrame:
    disable_efinance_proxy(no_proxy)
    import efinance as ef

    df = ef.stock.get_realtime_quotes("沪深京A股")
    return df[["代码", "名称", "总市值"]]


def fetch_spot_sina(no_proxy: bool) -> pd.DataFrame:
    from akshare.stock.cons import zh_sina_a_stock_count_url, zh_sina_a_stock_payload, zh_sina_a_stock_url
    from akshare.utils import demjson

    session = requests.Session()
    session.trust_env = not no_proxy
    count_response = session.get(zh_sina_a_stock_count_url, timeout=15)
    count_response.raise_for_status()
    total = int("".join(ch for ch in count_response.text if ch.isdigit()))
    page_size = 80
    pages = math.ceil(total / page_size)
    payload = zh_sina_a_stock_payload.copy()
    payload.update({"num": str(page_size)})
    frames = []
    for page in range(1, pages + 1):
        page_payload = payload.copy()
        page_payload["page"] = str(page)
        response = session.get(zh_sina_a_stock_url, params=page_payload, timeout=15)
        response.raise_for_status()
        rows = demjson.decode(response.text)
        if rows:
            frames.append(pd.DataFrame(rows))
        time.sleep(0.05)
    if not frames:
        return pd.DataFrame(columns=["代码", "名称", "总市值"])
    raw = pd.concat(frames, ignore_index=True)
    out = raw[["code", "name", "mktcap"]].copy()
    out.columns = ["代码", "名称", "总市值"]
    out["总市值"] = out["总市值"].map(to_number) * 10000
    return out


def load_spot(refresh: bool, no_proxy: bool, source: str) -> tuple[pd.DataFrame, str]:
    import akshare as ak

    def _fetch() -> tuple[pd.DataFrame, str]:
        fetchers: list[tuple[str, Callable[[], pd.DataFrame]]] = []
        for name in source_chain(source, ["sina", "efinance", "akshare"]):
            if name == "sina":
                fetchers.append(("sina", lambda: fetch_spot_sina(no_proxy)))
            elif name == "efinance":
                fetchers.append(("efinance", lambda: fetch_spot_efinance(no_proxy)))
            elif name == "akshare":
                fetchers.append(("akshare", lambda: ak.stock_zh_a_spot_em()))
                fetchers.append(("eastmoney-direct", lambda: fetch_spot_direct(no_proxy)))
        return run_fetchers("spot quote", fetchers)

    spot, chosen_source = cached_source_table("stock_zh_a_spot", "stock_zh_a_spot_em.csv", refresh, _fetch)
    code_col = find_col(spot.columns, ["代码", "code"])
    name_col = find_col(spot.columns, ["名称", "name"])
    mcap_col = find_col(spot.columns, ["总市值", "market_cap"], contains_all=["总市值"])
    if not code_col or not name_col or not mcap_col:
        raise RuntimeError(f"Cannot find required spot columns in: {list(spot.columns)}")
    out = spot[[code_col, name_col, mcap_col]].copy()
    out.columns = ["code", "name", "market_cap"]
    out["code"] = out["code"].map(normalize_code)
    out["market_cap"] = out["market_cap"].map(to_number)
    return out.dropna(subset=["market_cap"]), chosen_source


def fetch_industry_boards_direct(no_proxy: bool) -> pd.DataFrame:
    url = "https://17.push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": "100",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": "m:90 t:2 f:!50",
        "fields": "f12,f14",
    }
    raw = eastmoney_paginated(url, params, no_proxy)
    if raw.empty:
        return pd.DataFrame(columns=["板块代码", "板块名称"])
    return raw.rename(columns={"f12": "板块代码", "f14": "板块名称"})[["板块代码", "板块名称"]]


def load_industry_boards(refresh: bool, no_proxy: bool, source: str) -> pd.DataFrame:
    import akshare as ak

    def _fetch() -> tuple[pd.DataFrame, str]:
        if source == "cache":
            raise RuntimeError("cache miss: stock_board_industry_name_em.csv")
        try:
            return ak.stock_board_industry_name_em(), "akshare"
        except Exception:
            return fetch_industry_boards_direct(no_proxy), "eastmoney-direct"

    boards, _ = cached_source_table("stock_board_industry_name", "stock_board_industry_name_em.csv", refresh, _fetch)
    name_col = find_col(boards.columns, ["板块名称", "名称", "name"], contains_all=["名称"])
    code_col = find_col(boards.columns, ["板块代码", "代码", "code"], contains_all=["代码"])
    if not name_col:
        raise RuntimeError(f"Cannot find industry-board name column in: {list(boards.columns)}")
    out = boards.copy()
    out["board_name"] = out[name_col].astype(str)
    out["board_code"] = out[code_col].astype(str) if code_col else ""
    return out


def fetch_board_cons_direct(board_code: str, no_proxy: bool) -> pd.DataFrame:
    if not board_code:
        raise RuntimeError("missing Eastmoney board code for direct constituent fallback")
    url = "https://29.push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": "100",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": f"b:{board_code} f:!50",
        "fields": "f12,f14",
    }
    raw = eastmoney_paginated(url, params, no_proxy)
    if raw.empty:
        return pd.DataFrame(columns=["代码", "名称"])
    return raw.rename(columns={"f12": "代码", "f14": "名称"})[["代码", "名称"]]


def load_board_constituents(board_name: str, board_code: str, refresh: bool, no_proxy: bool, source: str) -> pd.DataFrame:
    import akshare as ak

    safe = "".join(ch if ch.isalnum() else "_" for ch in board_name)

    def _fetch() -> tuple[pd.DataFrame, str]:
        if source == "cache":
            raise RuntimeError(f"cache miss: industry_cons_{safe}.csv")
        try:
            return ak.stock_board_industry_cons_em(symbol=board_name), "akshare"
        except Exception:
            return fetch_board_cons_direct(board_code, no_proxy), "eastmoney-direct"

    cons, _ = cached_source_table(f"industry_cons_{safe}", f"industry_cons_{safe}.csv", refresh, _fetch)
    code_col = find_col(cons.columns, ["代码", "code"])
    name_col = find_col(cons.columns, ["名称", "name"])
    if not code_col:
        raise RuntimeError(f"Cannot find code column for board {board_name}: {list(cons.columns)}")
    out = cons[[code_col] + ([name_col] if name_col else [])].copy()
    out.columns = ["code"] + (["board_stock_name"] if name_col else [])
    out["code"] = out["code"].map(normalize_code)
    out["board_name"] = board_name
    return out


def fetch_financial_report_efinance(report_date: str, no_proxy: bool) -> pd.DataFrame:
    disable_efinance_proxy(no_proxy)
    import efinance as ef

    rd = f"{report_date[:4]}-{report_date[4:6]}-{report_date[6:]}"
    return ef.stock.get_all_company_performance(rd)


def load_financial_report(report_date: str, refresh: bool, source: str, no_proxy: bool) -> tuple[pd.DataFrame, str, str]:
    import akshare as ak

    candidates = report_date_candidates() if report_date == "auto" else [report_date]
    errors = []
    for rd in candidates:
        try:
            def _fetch(rd=rd) -> tuple[pd.DataFrame, str]:
                fetchers: list[tuple[str, Callable[[], pd.DataFrame]]] = []
                for name in source_chain(source, ["akshare", "efinance"]):
                    if name == "akshare":
                        fetchers.append(("akshare", lambda rd=rd: ak.stock_yjbb_em(date=rd)))
                    elif name == "efinance":
                        fetchers.append(("efinance", lambda rd=rd: fetch_financial_report_efinance(rd, no_proxy)))
                return run_fetchers("financial report", fetchers)

            df, chosen_source = cached_source_table(f"stock_yjbb_{rd}", f"stock_yjbb_em_{rd}.csv", refresh, _fetch)
            if not df.empty:
                return df, rd, chosen_source
        except Exception as exc:
            errors.append(f"{rd}: {exc}")
    raise RuntimeError("No financial report table available. " + "; ".join(errors[:5]))


def normalize_financials(df: pd.DataFrame) -> pd.DataFrame:
    code_col = find_col(df.columns, ["股票代码", "代码", "code"], contains_all=["代码"])
    name_col = find_col(df.columns, ["股票简称", "股票名称", "名称", "name"])
    industry_col = find_col(df.columns, ["所处行业", "行业", "industry"], contains_all=["行业"])
    rev_yoy_col = (
        find_col(df.columns, ["营业总收入-同比增长", "营业收入-同比增长", "营业收入同比增长", "营收同比增长", "营收同比"])
        or find_col(df.columns, [], contains_all=["营业总收入", "同比"])
        or find_col(df.columns, [], contains_all=["营业收入", "同比"])
        or find_col(df.columns, [], contains_all=["营收", "同比"])
    )
    profit_yoy_col = (
        find_col(df.columns, ["净利润-同比增长", "净利润同比增长", "归母净利润同比增长", "归母净利润同比"])
        or find_col(df.columns, [], contains_all=["净利润", "同比"])
    )
    if not code_col or not rev_yoy_col or not profit_yoy_col:
        raise RuntimeError(
            "Cannot find required financial columns. "
            f"code={code_col}, revenue_yoy={rev_yoy_col}, profit_yoy={profit_yoy_col}, columns={list(df.columns)}"
        )
    optional_cols = [col for col in [name_col, industry_col] if col]
    out = df[[code_col, rev_yoy_col, profit_yoy_col] + optional_cols].copy()
    out.columns = ["code", "revenue_yoy", "profit_yoy"] + [
        "financial_name" if col == name_col else "report_industry" for col in optional_cols
    ]
    out["code"] = out["code"].map(normalize_code)
    out["revenue_yoy"] = out["revenue_yoy"].map(to_number)
    out["profit_yoy"] = out["profit_yoy"].map(to_number)
    if "report_industry" not in out.columns:
        out["report_industry"] = ""
    if "financial_name" not in out.columns:
        out["financial_name"] = ""
    return out


def market_symbol(code: str) -> str:
    code = normalize_code(code)
    if code.startswith(("6", "9")):
        return f"sh{code}"
    if code.startswith(("0", "2", "3")):
        return f"sz{code}"
    if code.startswith(("4", "8")):
        return f"bj{code}"
    return code


def compact_date(value: str) -> str:
    return value.replace("-", "")


def normalize_daily_prices(raw: pd.DataFrame, code: str, source: str) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=["code", "trade_date", "open", "high", "low", "close", "volume", "amount"])
    date_col = find_col(raw.columns, ["日期", "date", "trade_date"])
    open_col = find_col(raw.columns, ["开盘", "open"])
    high_col = find_col(raw.columns, ["最高", "high"])
    low_col = find_col(raw.columns, ["最低", "low"])
    close_col = find_col(raw.columns, ["收盘", "close"])
    volume_col = find_col(raw.columns, ["成交量", "volume"])
    amount_col = find_col(raw.columns, ["成交额", "amount"])
    missing = {
        "date": date_col,
        "open": open_col,
        "high": high_col,
        "low": low_col,
        "close": close_col,
        "volume": volume_col,
        "amount": amount_col,
    }
    if any(v is None for v in missing.values()):
        raise RuntimeError(f"Cannot normalize daily prices from {source} for {code}: {missing}, columns={list(raw.columns)}")
    out = raw[[date_col, open_col, high_col, low_col, close_col, volume_col, amount_col]].copy()
    out.columns = ["trade_date", "open", "high", "low", "close", "volume", "amount"]
    out.insert(0, "code", normalize_code(code))
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        out[col] = out[col].map(to_number)
    return out.dropna(subset=["trade_date", "close"])


def fetch_daily_prices_sina(code: str, start: str, end: str, adjust: str, no_proxy: bool) -> pd.DataFrame:
    import akshare as ak

    if market_symbol(code).startswith("bj"):
        raise RuntimeError("Sina daily source does not support Beijing-board symbols reliably")
    # AKShare's Sina daily endpoint uses global requests; proxy control is handled
    # at the process environment level by --no-proxy.
    return ak.stock_zh_a_daily(
        symbol=market_symbol(code),
        start_date=compact_date(start),
        end_date=compact_date(end),
        adjust=adjust,
    )


def fetch_daily_prices_akshare(code: str, start: str, end: str, adjust: str, no_proxy: bool) -> pd.DataFrame:
    import akshare as ak

    return ak.stock_zh_a_hist(
        symbol=normalize_code(code),
        period="daily",
        start_date=compact_date(start),
        end_date=compact_date(end),
        adjust=adjust,
    )


def fetch_daily_prices_efinance(code: str, start: str, end: str, adjust: str, no_proxy: bool) -> pd.DataFrame:
    disable_efinance_proxy(no_proxy)
    import efinance as ef

    fqt = {"": 0, "qfq": 1, "hfq": 2}.get(adjust, 1)
    return ef.stock.get_quote_history(normalize_code(code), beg=compact_date(start), end=compact_date(end), klt=101, fqt=fqt)


def sync_daily_prices(codes: list[str], start: str, end: str, refresh: bool, no_proxy: bool, source: str, adjust: str) -> dict:
    if not codes:
        raise RuntimeError("daily_prices sync requires at least one code")
    conn = connect()
    normalized_frames = []
    per_symbol = []
    for code in [normalize_code(c) for c in codes if str(c).strip()]:
        fetchers: list[tuple[str, Callable[[], pd.DataFrame]]] = []
        if source == "cache":
            legacy_path = cache_dir() / f"daily_prices_{code}.csv"
            if legacy_path.exists():
                fetchers.append((f"legacy-csv:daily_prices_{code}.csv", lambda legacy_path=legacy_path: pd.read_csv(legacy_path, dtype={"code": str})))
        for name in source_chain(source, ["sina", "akshare", "efinance"]):
            if name == "sina":
                fetchers.append(("sina-daily", lambda code=code: fetch_daily_prices_sina(code, start, end, adjust, no_proxy)))
            elif name == "akshare":
                fetchers.append(("akshare-hist", lambda code=code: fetch_daily_prices_akshare(code, start, end, adjust, no_proxy)))
            elif name == "efinance":
                fetchers.append(("efinance-history", lambda code=code: fetch_daily_prices_efinance(code, start, end, adjust, no_proxy)))
        try:
            raw, used_source = run_fetchers(f"daily prices for {code}", fetchers)
            raw_key = f"daily_prices_{code}_{start}_{end}_{adjust or 'none'}"
            write_source_table(conn, raw_key, used_source, raw)
            normalized = normalize_daily_prices(raw, code, used_source)
            normalized = normalized[(normalized["trade_date"] >= start) & (normalized["trade_date"] <= end)].copy()
            rows = write_quotes_daily(conn, normalized, used_source)
            normalized_frames.append(normalized)
            per_symbol.append({"code": code, "source": used_source, "rows": rows, "status": "ok"})
        except Exception as exc:
            per_symbol.append({"code": code, "rows": 0, "status": "error", "error": str(exc)})
            if refresh:
                raise
    total_rows = int(sum(item["rows"] for item in per_symbol))
    return {
        "dataset": "daily_prices",
        "start": start,
        "end": end,
        "adjust": adjust,
        "symbols": len(per_symbol),
        "rows": total_rows,
        "db_path": str(db_path()),
        "details": per_symbol,
    }


def sync_dataset(
    dataset: str,
    report_date: str,
    refresh: bool,
    no_proxy: bool,
    source: str,
    codes: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    adjust: str = "qfq",
) -> dict:
    if dataset == "spot":
        df, used_source = load_spot(refresh, no_proxy, source)
        return {"dataset": dataset, "source": used_source, "rows": len(df), "db_path": str(db_path())}
    if dataset == "financials":
        raw, rd, used_source = load_financial_report(report_date, refresh, source, no_proxy)
        return {"dataset": dataset, "source": used_source, "report_date": rd, "rows": len(raw), "db_path": str(db_path())}
    if dataset == "industry_boards":
        df = load_industry_boards(refresh, no_proxy, source)
        return {"dataset": dataset, "rows": len(df), "db_path": str(db_path())}
    if dataset == "daily_prices":
        if not start or not end:
            raise RuntimeError("daily_prices sync requires --start and --end")
        return sync_daily_prices(codes or [], start, end, refresh, no_proxy, source, adjust)
    raise RuntimeError(f"Unsupported dataset: {dataset}")
