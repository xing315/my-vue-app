from __future__ import annotations

import json
import os
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
        self.client = httpx.Client(timeout=60, headers=headers)

    def _upload(self, bucket: str, object_path: str, content: bytes):
        response = self.client.post(
            f"{self.origin}/storage/v1/object/{bucket}/{object_path}",
            headers={"Content-Type": "application/gzip", "x-upsert": "true"}, content=content,
        )
        response.raise_for_status()

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
