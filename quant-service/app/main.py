import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .scoring import rating_for

app = FastAPI(title="A股中长线量化研究服务", version="1.0.0")
app.add_middleware(CORSMiddleware,
    allow_origins=os.getenv("QUANT_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["GET"], allow_headers=["*"])
DATA_ROOT = Path(os.getenv("QUANT_DATA_ROOT", "data"))

def _now(): return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()

def _live_quotes() -> list[dict]:
    import akshare as ak
    frame = ak.stock_zh_a_spot_em()
    wanted = frame[frame["代码"].isin(["600036", "000333", "600519", "300750", "002594"])]
    return [{"code": str(r["代码"]), "price": float(r["最新价"]),
             "change": float(r["涨跌幅"]), "quoteAt": _now()} for _, r in wanted.iterrows()]

@app.get("/health")
def health(): return {"status": "ok", "time": _now()}

@app.get("/api/quant/dashboard")
def dashboard():
    """Serve an audited daily snapshot, enriching only intraday quote fields."""
    snapshot = DATA_ROOT / "latest-dashboard.json"
    if not snapshot.exists():
        return {"mode":"unavailable","updatedAt":_now(),"modelVersion":"cn-equity-v1.0",
          "market":{"indices":[],"breadth":0,"valuation":0,"risk":"数据不足"},"stocks":[],
          "validation":{"annualReturn":0,"maxDrawdown":0,"winRate":0,"excessReturn":0,"period":"尚未完成滚动回测"},
          "sources":[{"name":"分析快照","state":"offline","detail":"尚未生成盘后评分"}]}
    payload = json.loads(snapshot.read_text(encoding="utf-8")); payload["mode"] = "live"
    try:
        quotes = {q["code"]: q for q in _live_quotes()}
        for stock in payload.get("stocks", []):
            if stock["code"] in quotes: stock.update(quotes[stock["code"]])
    except Exception as exc:
        payload.setdefault("sources", []).append({"name":"AKShare盘中行情","state":"offline","detail":type(exc).__name__})
    for stock in payload.get("stocks", []): stock["rating"] = rating_for(int(stock["score"]))
    return payload

def _number(value):
    """Return JSON-safe numeric values from pandas/numpy scalars."""
    import pandas as pd
    if value is None or pd.isna(value):
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None

@app.get("/api/quant/stocks/{symbol}")
def stock_detail(symbol: str):
    """Serve one stock's locally-audited price and financial detail."""
    import math
    import pandas as pd

    if not re.fullmatch(r"[036]\d{5}", symbol):
        raise HTTPException(status_code=400, detail="股票代码格式错误")
    history_path = DATA_ROOT / "raw" / "history" / f"{symbol}.parquet"
    if not history_path.exists():
        raise HTTPException(status_code=404, detail="该股票暂无历史行情")

    history = pd.read_parquet(history_path).copy()
    history["date"] = pd.to_datetime(history["date"], errors="coerce")
    for column in ("open", "high", "low", "close", "volume", "amount", "turnover", "turn"):
        if column in history:
            history[column] = pd.to_numeric(history[column], errors="coerce")
    history = history.dropna(subset=["date", "close"]).sort_values("date")
    if "tradestatus" in history:
        history = history[history["tradestatus"].astype(str) == "1"]
    if history.empty:
        raise HTTPException(status_code=404, detail="该股票暂无有效交易记录")

    close = history["close"]
    for days in (5, 20, 60, 120, 250):
        history[f"ma{days}"] = close.rolling(days).mean()
    returns = close.pct_change().dropna()
    drawdown = close / close.cummax() - 1
    first, last = history.iloc[0], history.iloc[-1]

    bars = []
    for row in history.tail(900).itertuples(index=False):
        bars.append({
            "date": row.date.date().isoformat(), "open": _number(getattr(row, "open", None)),
            "high": _number(getattr(row, "high", None)), "low": _number(getattr(row, "low", None)),
            "close": _number(row.close), "volume": _number(getattr(row, "volume", None)),
            "amount": _number(getattr(row, "amount", None)),
            "turnover": _number(getattr(row, "turn", getattr(row, "turnover", None))),
            **{f"ma{days}": _number(getattr(row, f"ma{days}", None)) for days in (5, 20, 60, 120, 250)},
        })

    financial_rows = []
    financial_path = DATA_ROOT / "raw" / "financial.parquet"
    if financial_path.exists():
        financial = pd.read_parquet(financial_path)
        financial = financial[financial["code"].astype(str).str.zfill(6) == symbol]
        sort_column = "report_date" if "report_date" in financial else "publish_date"
        if sort_column in financial:
            financial = financial.sort_values(sort_column, ascending=False)
        for row in financial.head(12).to_dict("records"):
            financial_rows.append({
                "reportDate": str(row.get("report_date") or ""), "publishDate": str(row.get("publish_date") or ""),
                "revenue": _number(row.get("revenue")), "revenueGrowth": _number(row.get("revenue_growth")),
                "profit": _number(row.get("profit")), "profitGrowth": _number(row.get("profit_growth")),
                "eps": _number(row.get("eps")), "bps": _number(row.get("bps")), "roe": _number(row.get("roe")),
                "grossMargin": _number(row.get("gross_margin")), "cashflowPerShare": _number(row.get("cashflow_ps")),
            })

    stock = None
    snapshot = DATA_ROOT / "latest-dashboard.json"
    if snapshot.exists():
        payload = json.loads(snapshot.read_text(encoding="utf-8"))
        stock = next((item for item in payload.get("stocks", []) if item.get("code") == symbol), None)
    stats = {
        "startDate": first.date.date().isoformat(), "endDate": last.date.date().isoformat(),
        "tradingDays": len(history), "periodReturn": _number(last.close / first.close - 1),
        "return1y": _number(last.close / close.iloc[-min(240, len(close))] - 1),
        "maxDrawdown": _number(drawdown.min()),
        "annualVolatility": _number(returns.tail(250).std() * math.sqrt(250)) if len(returns) else None,
        "high": _number(history["high"].max() if "high" in history else close.max()),
        "low": _number(history["low"].min() if "low" in history else close.min()),
        "averageAmount20": _number(history["amount"].tail(20).mean()) if "amount" in history else None,
    }
    return {"symbol": symbol, "stock": stock, "stats": stats, "bars": bars,
            "financials": financial_rows, "dataScope": "本地已下载行情，最多近 900 个交易日；不代表上市以来"}
