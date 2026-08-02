from app.scoring import board_lot_quantity, rating_for, score_stock, suggested_position

def test_rating_boundaries():
    assert [rating_for(x) for x in (80,70,55,40,39)] == ["重点研究","值得关注","中性观察","谨慎","回避"]

def test_hard_exclusion_overrides_high_score():
    result = score_stock({k:1 for k in ("quality","growth","valuation","trend","risk","liquidity")}, exclusion_reasons=["ST"])
    assert result.excluded and result.score == 39 and result.rating == "回避"

def test_incomplete_data_cannot_recommend():
    assert score_stock({"quality":1,"growth":1}, completeness=.5).score <= 54

def test_position_limits_and_board_lot():
    assert suggested_position(85,90,.2) == (6,8)
    assert suggested_position(85,90,.45) == (4,6)
    assert suggested_position(50,90,.2) == (0,0)
    assert board_lot_quantity(100_000,20,(3,5)) == 200
