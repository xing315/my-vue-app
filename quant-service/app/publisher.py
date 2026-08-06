from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

import httpx

from .scoring import rating_for


class SupabasePublisher:
    def __init__(self, url: str, service_key: str):
        self.origin = url.rstrip("/")
        self.base = self.origin + "/rest/v1"
        headers = {
            "apikey": service_key,
            "Content-Type": "application/json",
        }
        # New sb_secret keys authenticate via apikey. Legacy service_role JWTs
        # also require the bearer header to assume the service_role database role.
        if not service_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {service_key}"
        self.client = httpx.Client(timeout=60, headers=headers, trust_env=False)

    def _upload(self, bucket: str, object_path: str, content: bytes):
        last_error = None
        for attempt in range(3):
            try:
                response = self.client.post(
                    f"{self.origin}/storage/v1/object/{bucket}/{object_path}",
                    headers={"Content-Type": "application/gzip", "x-upsert": "true"}, content=content,
                )
                response.raise_for_status()
                return
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt < 2: time.sleep(attempt + 1)
        raise last_error

    def _ensure_chart_bucket(self):
        body = {"id": "quant-stock-charts", "name": "quant-stock-charts", "public": True,
                "file_size_limit": 5 * 1024 * 1024, "allowed_mime_types": ["application/gzip"]}
        response = self.client.post(f"{self.origin}/storage/v1/bucket", json=body)
        if response.status_code in (400, 409):
            response = self.client.put(f"{self.origin}/storage/v1/bucket/quant-stock-charts", json=body)
        response.raise_for_status()

    def _upsert(self, table: str, rows: list[dict], conflict: str):
        response = self.client.post(
            f"{self.base}/{table}", params={"on_conflict": conflict},
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            content=json.dumps(rows, ensure_ascii=False),
        )
        response.raise_for_status()

    def _select(self, table: str, params: dict) -> list[dict]:
        response = self.client.get(f"{self.base}/{table}", params=params)
        response.raise_for_status()
        return response.json()

    def publish(self, payload: dict, batch_size: int = 200, data_root: Path | None = None) -> dict:
        if payload.get("mode") != "live":
            raise ValueError("只允许发布通过全市场安全门的 live 快照")
        updated_at = payload["updatedAt"]
        trade_date = updated_at[:10]
        stocks = payload.get("stocks", [])
        if len(stocks) < 1000:
            raise ValueError(f"覆盖数 {len(stocks)} 低于发布门槛")
        rows = []
        for stock in stocks:
            position = stock.get("position") or [0, 0]
            rows.append({
                "symbol": stock["code"], "name": stock["name"],
                "industry": stock.get("industry") or "未分类",
                "score": stock["score"], "confidence": stock["confidence"],
                "rating": rating_for(int(stock["score"])),
                "price": stock.get("price"), "change_percent": stock.get("change"),
                "position_min": position[0], "position_max": position[1],
                "excluded": bool(stock.get("flags")), "detail": stock,
                "trade_date": trade_date, "updated_at": updated_at,
                "model_version": payload["modelVersion"],
            })
        for start in range(0, len(rows), batch_size):
            self._upsert("quant_latest_scores", rows[start:start + batch_size], "symbol")
            print(f"Supabase scores {min(start + batch_size, len(rows))}/{len(rows)}", flush=True)
        eligible = sum(not row["excluded"] for row in rows)
        self._upsert("quant_market_snapshots", [{
            "trade_date": trade_date, "updated_at": updated_at,
            "model_version": payload["modelVersion"], "coverage_count": len(rows),
            "eligible_count": eligible, "market": payload.get("market", {}),
            "validation": payload.get("validation", {}), "sources": payload.get("sources", []),
        }], "trade_date")
        recommendations = []
        for item in payload.get("recommendations", []):
            position = item.get("position") or [0, 0]
            recommendations.append({"trade_date": trade_date, "rank": item["rank"], "symbol": item["code"],
                "name": item["name"], "industry": item.get("industry") or "未分类", "score": item["score"],
                "confidence": item["confidence"], "previous_rank": item.get("previousRank"),
                "rank_change": item.get("rankChange"), "price": item.get("price"),
                "change_percent": item.get("change"), "position_min": position[0], "position_max": position[1],
                "explanation": item.get("explanation") or {}, "model_version": payload["modelVersion"],
                "experimental": True})
        if recommendations:
            try:
                self._upsert("quant_daily_recommendations", recommendations, "trade_date,rank,model_version")
                print(f"Supabase recommendations {len(recommendations)}/{len(recommendations)}", flush=True)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 404: raise
                print("Supabase 推荐历史表尚未迁移，最新推荐已随 scores.detail 发布", flush=True)
        signals = payload.get("signals") or []
        if signals:
            try:
                self._upsert("quant_signal_events", signals, "trade_date,symbol,signal_type")
                symbols = sorted({item["symbol"] for item in signals})
                symbol_filter = "(" + ",".join(symbols) + ")"
                owners: dict[str, set[str]] = {}
                for table in ("quant_watchlist", "quant_holdings"):
                    for row in self._select(table, {"select": "user_id,symbol", "symbol": f"in.{symbol_filter}"}):
                        owners.setdefault(row["symbol"], set()).add(row["user_id"])
                published_signals = self._select("quant_signal_events", {
                    "select": "id,symbol", "trade_date": f"eq.{trade_date}", "symbol": f"in.{symbol_filter}"})
                inbox = [{"user_id": user_id, "signal_id": event["id"]}
                         for event in published_signals for user_id in owners.get(event["symbol"], set())]
                if inbox: self._upsert("quant_user_alerts", inbox, "user_id,signal_id")
                print(f"Supabase signals {len(signals)}, inbox {len(inbox)}", flush=True)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 404: raise
                print("Supabase 投研驾驶舱表尚未迁移，跳过盘后信号发布", flush=True)
        chart_bytes = 0
        if data_root is not None:
            from .chart_shards import build_chart_shards
            self._ensure_chart_bucket()
            shards = build_chart_shards(data_root)
            for index, content in shards.items():
                self._upload("quant-stock-charts", f"v1/shard-{index:02d}.json.gz", content)
                chart_bytes += len(content)
                print(f"Supabase chart shards {index + 1}/{len(shards)}", flush=True)
        return {"trade_date": trade_date, "published": len(rows), "eligible": eligible,
                "chart_bytes": chart_bytes}


def publish_file(path: Path) -> dict:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("缺少 SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SupabasePublisher(url, key).publish(payload, data_root=path.parent)
