from datetime import date

import pandas as pd

from app.pipeline import append_spot_bar


def test_append_spot_bar_adds_only_one_new_day(tmp_path):
    path=tmp_path/"000001.parquet"
    pd.DataFrame([{"date":pd.Timestamp("2026-08-05"),"close":10.0,"amount":1000}]).to_parquet(path,index=False)
    row=type("Spot",(),{"price":10.5,"change":5.0,"amount":2000,"volume":100,
                         "open":10.1,"high":10.6,"low":10.0,"turnover":1.2})()

    assert append_spot_bar(path,row,date(2026,8,6))
    assert append_spot_bar(path,row,date(2026,8,6))

    saved=pd.read_parquet(path)
    assert list(pd.to_datetime(saved.date).dt.strftime("%Y-%m-%d")) == ["2026-08-05","2026-08-06"]
    assert saved.iloc[-1].close == 10.5


def test_append_spot_bar_rejects_suspended_or_empty_quote(tmp_path):
    path=tmp_path/"000001.parquet"
    pd.DataFrame([{"date":pd.Timestamp("2026-08-05"),"close":10.0}]).to_parquet(path,index=False)
    row=type("Spot",(),{"price":10.0,"amount":0})()

    assert not append_spot_bar(path,row,date(2026,8,6))
    assert len(pd.read_parquet(path)) == 1
