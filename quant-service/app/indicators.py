from __future__ import annotations

import math
from typing import Iterable
import numpy as np
import pandas as pd


def percentile(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    rank = values.rank(pct=True, method="average")
    return rank if higher_is_better else 1 - rank


def history_features(frame: pd.DataFrame) -> dict:
    valid = frame.copy()
    if "tradestatus" in valid:
        valid = valid[valid["tradestatus"].astype(str) == "1"]
    close = pd.to_numeric(valid.get("close"), errors="coerce").dropna()
    amount = pd.to_numeric(valid.get("amount"), errors="coerce").dropna()
    if len(close) < 120:
        return {"history_days": len(close)}
    returns = close.pct_change().dropna()
    peak = close.cummax()
    drawdown = close / peak - 1
    last = float(close.iloc[-1])
    result = {
        "history_days": len(close), "return_6m": float(last / close.iloc[-min(120,len(close))] - 1),
        "return_1y": float(last / close.iloc[-min(240,len(close))] - 1),
        "volatility": float(returns.tail(240).std() * math.sqrt(250)),
        "max_drawdown": float(drawdown.tail(500).min()),
        "avg_amount_20": float(amount.tail(20).mean()) if len(amount) else np.nan,
        "ma20_ratio": float(last / close.tail(20).mean() - 1),
        "ma60_ratio": float(last / close.tail(60).mean() - 1),
        "ma120_ratio": float(last / close.tail(120).mean() - 1),
        "history_price": last,
    }
    for source, target in [("pctChg","history_change"),("turn","history_turnover"),("peTTM","history_pe"),("pbMRQ","history_pb")]:
        values = pd.to_numeric(valid[source], errors="coerce").dropna() if source in valid else pd.Series(dtype=float)
        if len(values): result[target] = float(values.iloc[-1])
    if "isST" in valid and len(valid): result["is_st_history"] = str(valid["isST"].iloc[-1]) == "1"
    if "tradestatus" in frame and len(frame): result["trading"] = str(frame["tradestatus"].iloc[-1]) == "1"
    return result


def dimension_scores(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    cash_quality = np.where((out.get("profit", 0) > 0), out.get("cashflow_ps", np.nan), np.nan)
    out["quality_n"] = pd.concat([
        percentile(out.get("roe", pd.Series(index=out.index,dtype=float))),
        percentile(out.get("gross_margin", pd.Series(index=out.index,dtype=float))),
        percentile(pd.Series(cash_quality,index=out.index)),
    ],axis=1).mean(axis=1)
    out["growth_n"] = pd.concat([
        percentile(out.get("revenue_growth", pd.Series(index=out.index,dtype=float))),
        percentile(out.get("profit_growth", pd.Series(index=out.index,dtype=float))),
    ],axis=1).mean(axis=1)
    pe = out.get("pe", pd.Series(index=out.index,dtype=float)).where(lambda x: x > 0)
    pb = out.get("pb", pd.Series(index=out.index,dtype=float)).where(lambda x: x > 0)
    out["valuation_n"] = pd.concat([percentile(pe,False),percentile(pb,False)],axis=1).mean(axis=1)
    out["trend_n"] = pd.concat([
        percentile(out.get("return_6m", pd.Series(index=out.index,dtype=float))),
        percentile(out.get("return_1y", pd.Series(index=out.index,dtype=float))),
        percentile(out.get("ma120_ratio", pd.Series(index=out.index,dtype=float))),
    ],axis=1).mean(axis=1)
    out["risk_n"] = pd.concat([
        percentile(out.get("volatility", pd.Series(index=out.index,dtype=float)),False),
        percentile(out.get("max_drawdown", pd.Series(index=out.index,dtype=float))),
    ],axis=1).mean(axis=1)
    out["liquidity_n"] = pd.concat([
        percentile(out.get("avg_amount_20", pd.Series(index=out.index,dtype=float))),
        percentile(out.get("turnover", pd.Series(index=out.index,dtype=float))),
    ],axis=1).mean(axis=1)
    return out
