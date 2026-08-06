from __future__ import annotations

from typing import Iterable


def _event(stock: dict, trade_date: str, signal_type: str, severity: str, title: str,
           reason: str, previous=None, current=None, evidence=None) -> dict:
    return {"trade_date": trade_date, "symbol": stock["code"], "signal_type": signal_type,
            "severity": severity, "title": title, "reason": reason,
            "previous_value": previous, "current_value": current,
            "evidence": evidence or {}, "source": "盘后量化流水线"}


def build_signal_events(payload: dict, previous_payload: dict | None = None) -> list[dict]:
    """Create deterministic, explainable daily signals from two audited snapshots."""
    trade_date = payload["updatedAt"][:10]
    previous_payload = previous_payload or {}
    prior = {item["code"]: item for item in previous_payload.get("stocks", [])}
    current_top = {item["code"] for item in payload.get("recommendations", [])}
    prior_top = {item["code"] for item in previous_payload.get("recommendations", [])}
    events: list[dict] = []
    for stock in payload.get("stocks", []):
        old = prior.get(stock["code"])
        if not old:
            continue
        score, old_score = int(stock.get("score", 0)), int(old.get("score", 0))
        for threshold in (70, 80):
            if old_score < threshold <= score:
                events.append(_event(stock, trade_date, f"score_above_{threshold}", "attention",
                    f"评分升至 {threshold} 分以上", f"综合评分由 {old_score} 升至 {score}",
                    {"score": old_score}, {"score": score}, {"threshold": threshold}))
            elif old_score >= threshold > score:
                events.append(_event(stock, trade_date, f"score_below_{threshold}", "risk",
                    f"评分跌破 {threshold} 分", f"综合评分由 {old_score} 降至 {score}",
                    {"score": old_score}, {"score": score}, {"threshold": threshold}))
        if abs(score - old_score) >= 5:
            direction = "上升" if score > old_score else "下降"
            events.append(_event(stock, trade_date, "score_change", "attention" if score > old_score else "risk",
                f"评分显著{direction}", f"综合评分单日{direction} {abs(score-old_score)} 分",
                {"score": old_score}, {"score": score}))
        was_top, is_top = stock["code"] in prior_top, stock["code"] in current_top
        if was_top != is_top:
            events.append(_event(stock, trade_date, "top30_change", "attention" if is_top else "risk",
                "进入今日 Top 30" if is_top else "退出今日 Top 30",
                "盘后规则排名发生变化", {"inTop30": was_top}, {"inTop30": is_top}))
        old_flags, flags = set(old.get("flags") or []), set(stock.get("flags") or [])
        added = sorted(flags - old_flags)
        if added:
            events.append(_event(stock, trade_date, "risk_change", "risk", "新增风险标签",
                "；".join(added), {"flags": sorted(old_flags)}, {"flags": sorted(flags)}))
        old_metrics, metrics = old.get("metrics") or {}, stock.get("metrics") or {}
        for days in (20, 60):
            key = f"ma{days}Ratio"
            before, now = old_metrics.get(key), metrics.get(key)
            if before is not None and now is not None and before >= 0 > now:
                events.append(_event(stock, trade_date, f"ma{days}_break", "risk", f"跌破 MA{days}",
                    f"收盘价相对 MA{days} 由 {before*100:.2f}% 降至 {now*100:.2f}%",
                    {key: before}, {key: now}, {"movingAverage": days}))
        old_rating = "回避" if old_score < 40 else "谨慎" if old_score < 55 else "中性观察" if old_score < 70 else "值得关注" if old_score < 80 else "重点研究"
        rating = "回避" if score < 40 else "谨慎" if score < 55 else "中性观察" if score < 70 else "值得关注" if score < 80 else "重点研究"
        if old_score >= 55 > score:
            events.append(_event(stock, trade_date, "rating_downgrade", "risk", "模型评级降至谨慎/回避",
                f"评级由{old_rating}降至{rating}", {"rating": old_rating}, {"rating": rating}))
        old_vol, vol = old_metrics.get("volatility"), metrics.get("volatility")
        old_dd, dd = old_metrics.get("maxDrawdown"), metrics.get("maxDrawdown")
        if ((old_vol is not None and vol is not None and vol-old_vol >= .05) or
                (old_dd is not None and dd is not None and dd-old_dd <= -.05)):
            events.append(_event(stock, trade_date, "risk_metrics_worse", "risk", "波动或回撤风险恶化",
                "历史风险指标较上一快照明显恶化", {"volatility": old_vol, "maxDrawdown": old_dd},
                {"volatility": vol, "maxDrawdown": dd}))
    return events


def signal_symbols(events: Iterable[dict]) -> set[str]:
    return {event["symbol"] for event in events}
