from app.signals import build_signal_events


def stock(code="600036", score=68, flags=None):
    return {"code": code, "score": score, "flags": flags or []}


def snapshot(day, stocks, top=None):
    return {"updatedAt": f"{day}T16:45:00+08:00", "stocks": stocks,
            "recommendations": [{"code": code} for code in (top or [])]}


def test_score_threshold_change_and_top30_entry():
    old = snapshot("2026-08-05", [stock(score=68)])
    new = snapshot("2026-08-06", [stock(score=74)], ["600036"])
    events = build_signal_events(new, old)
    assert {event["signal_type"] for event in events} == {"score_above_70", "score_change", "top30_change"}
    assert all(event["trade_date"] == "2026-08-06" for event in events)


def test_downgrade_and_new_risk_label():
    old = snapshot("2026-08-05", [stock(score=82)], ["600036"])
    new = snapshot("2026-08-06", [stock(score=69, flags=["高波动"])])
    events = build_signal_events(new, old)
    types = {event["signal_type"] for event in events}
    assert {"score_below_80", "score_below_70", "score_change", "top30_change", "risk_change"} <= types
    assert next(event for event in events if event["signal_type"] == "risk_change")["severity"] == "risk"


def test_first_snapshot_has_no_false_changes():
    assert build_signal_events(snapshot("2026-08-06", [stock()])) == []
