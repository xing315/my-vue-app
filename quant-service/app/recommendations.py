from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

import httpx


DIMENSIONS = {
    "quality": ("财务质量", 25), "growth": ("成长能力", 20), "valuation": ("估值水平", 20),
    "trend": ("中期趋势", 15), "risk": ("风险稳定", 10), "liquidity": ("流动性", 10),
}


def _rule_explanation(stock: dict) -> dict:
    ranked = sorted(DIMENSIONS, key=lambda key: stock.get(key, 0) / DIMENSIONS[key][1], reverse=True)
    strongest, second = ranked[:2]
    weakest = ranked[-1]
    positives = [f"{DIMENSIONS[strongest][0]}得分 {stock.get(strongest, 0)}/{DIMENSIONS[strongest][1]}",
                 f"{DIMENSIONS[second][0]}得分 {stock.get(second, 0)}/{DIMENSIONS[second][1]}"]
    metrics = stock.get("metrics") or {}
    if metrics.get("roe") is not None:
        positives.append(f"最新可用 ROE 为 {metrics['roe']:.2f}%")
    negatives = [f"主要短板是{DIMENSIONS[weakest][0]}，得分 {stock.get(weakest, 0)}/{DIMENSIONS[weakest][1]}"]
    if metrics.get("maxDrawdown") is not None and metrics["maxDrawdown"] < -0.2:
        negatives.append(f"样本期最大回撤为 {metrics['maxDrawdown'] * 100:.2f}%")
    invalidation = ["后续正式财报导致盈利质量或成长得分明显下降", "触发 ST、停牌、重大调查或流动性硬性过滤"]
    if strongest == "trend": invalidation.append("中期趋势跌破模型有效区间")
    return {"summary": stock.get("reason") or f"综合得分 {stock['score']}，进入今日重点研究名单",
            "positiveEvidence": positives[:3], "negativeEvidence": negatives[:2],
            "invalidationConditions": invalidation[:3],
            "positionReason": f"根据得分、置信度与历史波动，建议研究仓位区间为 {stock['position'][0]}–{stock['position'][1]}%",
            "dataLimitations": ["当前财务数据历史深度有限", "尚未完成正式滚动窗口回测"],
            "source": "rules"}


def _previous_ranks(data_root: Path, trade_date: str) -> dict[str, int]:
    directory = data_root / "recommendations"
    if not directory.exists(): return {}
    candidates = sorted((p for p in directory.glob("*.json") if p.stem < trade_date), reverse=True)
    if not candidates: return {}
    try:
        payload = json.loads(candidates[0].read_text(encoding="utf-8"))
        return {item["code"]: int(item["rank"]) for item in payload.get("recommendations", [])}
    except (OSError, ValueError, KeyError): return {}


def select_top_stocks(stocks: list[dict], limit: int = 30, industry_cap: int = 4) -> list[dict]:
    candidates = [stock for stock in stocks if not stock.get("flags") and stock.get("confidence", 0) >= 70
                  and stock.get("score", 0) >= 55 and (stock.get("position") or [0, 0])[1] > 0]
    candidates.sort(key=lambda stock: (stock["score"], stock["confidence"], stock.get("quality", 0),
                                       stock.get("risk", 0)), reverse=True)
    selected, counts = [], Counter()
    for stock in candidates:
        industry = stock.get("industry") or "未分类"
        if counts[industry] >= industry_cap: continue
        selected.append(stock); counts[industry] += 1
        if len(selected) == limit: break
    return selected


def _ai_explanations(items: list[dict]) -> dict[str, dict]:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key or not items: return {}
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    output = {}
    client = httpx.Client(timeout=120)
    system = """你是A股量化研究解释器。排名已由规则模型确定，你不得修改排名、评分或仓位。
只能引用输入JSON中的事实和数字，不得编造新闻、公告、行业地位或未来收益。输出JSON对象，格式为
{"items":[{"code":"股票代码","summary":"一句话","positiveEvidence":["证据"],"negativeEvidence":["反证"],
"invalidationConditions":["失效条件"],"positionReason":"仓位原因","dataLimitations":["局限"]}]}。"""
    for start in range(0, len(items), 10):
        batch = items[start:start + 10]
        safe = [{k: item.get(k) for k in ("code", "name", "industry", "score", "confidence", "quality", "growth",
                                            "valuation", "trend", "risk", "liquidity", "position", "metrics")} for item in batch]
        try:
            response = client.post("https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "system", "content": system},
                      {"role": "user", "content": "请根据以下JSON生成可核验解释：" + json.dumps(safe, ensure_ascii=False)}],
                      "thinking": {"type": "disabled"}, "response_format": {"type": "json_object"},
                      "temperature": 0.1, "max_tokens": 5000})
            response.raise_for_status()
            parsed = json.loads(response.json()["choices"][0]["message"]["content"])
            allowed = {item["code"] for item in batch}
            for explanation in parsed.get("items", []):
                code = explanation.get("code")
                required = ("summary", "positiveEvidence", "negativeEvidence", "invalidationConditions", "dataLimitations")
                if code in allowed and all(key in explanation for key in required):
                    explanation["source"] = "deepseek"; output[code] = explanation
        except Exception as exc:
            print(f"DeepSeek 推荐解释批次失败，使用规则解释: {type(exc).__name__}", flush=True)
    return output


def build_recommendations(data_root: Path, payload: dict, limit: int = 30) -> list[dict]:
    trade_date = payload["updatedAt"][:10]
    selected = select_top_stocks(payload.get("stocks", []), limit=limit)
    previous = _previous_ranks(data_root, trade_date)
    ai = _ai_explanations(selected)
    recommendations = []
    for rank, stock in enumerate(selected, 1):
        prior = previous.get(stock["code"])
        recommendation={"rank": rank, "previousRank": prior, "rankChange": prior - rank if prior else None,
            "code": stock["code"], "name": stock["name"], "industry": stock.get("industry") or "未分类",
            "score": stock["score"], "confidence": stock["confidence"], "price": stock.get("price"),
            "change": stock.get("change"), "position": stock.get("position"), "explanation": ai.get(stock["code"], _rule_explanation(stock))}
        recommendations.append(recommendation)
        # Keep the current recommendation inside latest_scores.detail as an
        # online fallback when the history-table migration has not run yet.
        stock["recommendation"] = recommendation
    directory = data_root / "recommendations"; directory.mkdir(parents=True, exist_ok=True)
    result = {"tradeDate": trade_date, "modelVersion": payload["modelVersion"], "experimental": True,
              "recommendations": recommendations}
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    (directory / f"{trade_date}.json").write_text(encoded, encoding="utf-8")
    (data_root / "latest-recommendations.json").write_text(encoded, encoding="utf-8")
    return recommendations
