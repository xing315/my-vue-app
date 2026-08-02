from __future__ import annotations

import gzip
import json
import math
from pathlib import Path

import pandas as pd


SHARD_COUNT = 64
BAR_LIMIT = 250


def shard_number(symbol: str) -> int:
    return int(symbol) % SHARD_COUNT


def _number(value):
    if value is None or pd.isna(value):
        return None
    try:
        number = float(value)
        return round(number, 4) if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _financial_map(data_root: Path) -> dict[str, dict]:
    path = data_root / "raw" / "financial.parquet"
    if not path.exists():
        return {}
    frame = pd.read_parquet(path)
    if frame.empty or "code" not in frame:
        return {}
    frame["code"] = frame["code"].astype(str).str.zfill(6)
    sort_column = "report_date" if "report_date" in frame else "publish_date"
    if sort_column in frame:
        frame = frame.sort_values(sort_column, ascending=False)
    frame = frame.drop_duplicates("code", keep="first")
    result = {}
    for row in frame.to_dict("records"):
        result[row["code"]] = {
            "reportDate": str(row.get("report_date") or ""),
            "publishDate": str(row.get("publish_date") or ""),
            "revenue": _number(row.get("revenue")), "revenueGrowth": _number(row.get("revenue_growth")),
            "profit": _number(row.get("profit")), "profitGrowth": _number(row.get("profit_growth")),
            "eps": _number(row.get("eps")), "bps": _number(row.get("bps")), "roe": _number(row.get("roe")),
            "grossMargin": _number(row.get("gross_margin")),
            "cashflowPerShare": _number(row.get("cashflow_ps")),
        }
    return result


def build_chart_shards(data_root: Path, bar_limit: int = BAR_LIMIT) -> dict[int, bytes]:
    """Build compact gzip objects for online charts without publishing raw history."""
    histories = data_root / "raw" / "history"
    financials = _financial_map(data_root)
    shards: list[dict] = [{} for _ in range(SHARD_COUNT)]
    for path in sorted(histories.glob("*.parquet")):
        symbol = path.stem
        if len(symbol) != 6 or not symbol.isdigit():
            continue
        frame = pd.read_parquet(path)
        required = {"date", "open", "high", "low", "close"}
        if frame.empty or not required.issubset(frame.columns):
            continue
        if "tradestatus" in frame:
            frame = frame[frame["tradestatus"].astype(str) == "1"]
        frame = frame.tail(bar_limit).copy()
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.dropna(subset=["date", "close"])
        bars = []
        for row in frame.itertuples(index=False):
            bars.append([row.date.date().isoformat(), _number(row.open), _number(row.high), _number(row.low),
                         _number(row.close), _number(getattr(row, "volume", None)), _number(getattr(row, "amount", None))])
        if bars:
            shards[shard_number(symbol)][symbol] = {"b": bars, "f": financials.get(symbol),
                                                    "scope": f"线上近 {len(bars)} 个有效交易日"}
    result = {}
    for index, shard in enumerate(shards):
        raw = json.dumps({"version": 1, "barLimit": bar_limit, "stocks": shard},
                         ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        result[index] = gzip.compress(raw, compresslevel=6, mtime=0)
    return result
