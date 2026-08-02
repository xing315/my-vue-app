from app.recommendations import select_top_stocks


def stock(code: str, score: int, industry: str, confidence: int = 80, flags=None):
    return {"code": code, "score": score, "industry": industry, "confidence": confidence,
            "quality": 20, "risk": 8, "position": [3, 5], "flags": flags or []}


def test_top_stocks_enforces_industry_cap():
    stocks = [stock(f"600{i:03d}", 90 - i, "银行") for i in range(8)]
    stocks += [stock(f"000{i:03d}", 80 - i, "医药") for i in range(5)]
    selected = select_top_stocks(stocks, limit=8, industry_cap=4)
    assert len(selected) == 8
    assert sum(item["industry"] == "银行" for item in selected) == 4
    assert sum(item["industry"] == "医药" for item in selected) == 4


def test_top_stocks_rejects_low_confidence_and_hard_filters():
    stocks = [stock("600001", 90, "银行", confidence=60), stock("600002", 89, "银行", flags=["ST"]),
              stock("600003", 70, "银行")]
    assert [item["code"] for item in select_top_stocks(stocks)] == ["600003"]
