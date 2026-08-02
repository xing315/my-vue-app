import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from fastapi import FastAPI
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
