from __future__ import annotations

from dataclasses import dataclass
from math import floor

WEIGHTS = {"quality": 25, "growth": 20, "valuation": 20, "trend": 15, "risk": 10, "liquidity": 10}

@dataclass(frozen=True)
class ScoreResult:
    score: int
    rating: str
    confidence: int
    excluded: bool

def rating_for(score: int) -> str:
    if score >= 80: return "重点研究"
    if score >= 70: return "值得关注"
    if score >= 55: return "中性观察"
    if score >= 40: return "谨慎"
    return "回避"

def score_stock(dimensions: dict[str, float], completeness: float = 1.0,
                exclusion_reasons: list[str] | None = None) -> ScoreResult:
    missing = set(WEIGHTS) - set(dimensions)
    completeness = max(0.0, min(1.0, completeness - len(missing) * 0.1))
    raw = sum(max(0.0, min(1.0, dimensions.get(k, 0))) * w for k, w in WEIGHTS.items())
    excluded = bool(exclusion_reasons)
    score = min(39, round(raw)) if excluded else round(raw)
    confidence = round(completeness * 100)
    if confidence < 60: score = min(score, 54)
    return ScoreResult(score, rating_for(score), confidence, excluded)

def suggested_position(score: int, confidence: int, volatility: float,
                       excluded: bool = False) -> tuple[int, int]:
    if excluded or score < 55 or confidence < 60: return (0, 0)
    upper = 8 if score >= 80 and confidence >= 80 else 5 if score >= 70 else 3
    if volatility >= 0.40: upper = max(2, upper - 2)
    elif volatility >= 0.30: upper = max(2, upper - 1)
    return (max(2, upper - 2), upper)

def board_lot_quantity(budget: float, price: float, position: tuple[int, int]) -> int:
    if budget <= 0 or price <= 0 or position[1] == 0: return 0
    return floor((budget * (sum(position) / 2 / 100) / price) / 100) * 100
