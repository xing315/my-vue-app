from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

import duckdb


SCHEMA_SQL = """
create table if not exists instruments (
  symbol varchar primary key, name varchar not null, industry varchar,
  status varchar not null default 'active', updated_at timestamptz not null
);
create table if not exists daily_scores (
  trade_date date, symbol varchar, model_version varchar, release_mode varchar,
  score smallint, confidence smallint, rating varchar,
  quality_score smallint, growth_score smallint, valuation_score smallint,
  trend_score smallint, risk_score smallint, liquidity_score smallint,
  excluded boolean, detail json, created_at timestamptz,
  primary key (trade_date, symbol, model_version)
);
create table if not exists sync_runs (
  id varchar primary key, started_at timestamptz, completed_at timestamptz,
  status varchar, trade_date date, expected_count integer, collected_count integer,
  failed_count integer, coverage double, sources json, error_message varchar
);
create table if not exists risk_events (
  symbol varchar, event_date date, event_type varchar, title varchar,
  source varchar, active boolean, detail json,
  primary key (symbol, event_date, event_type)
);
create table if not exists backtest_runs (
  id varchar primary key, strategy_name varchar, model_version varchar,
  started_at timestamptz, completed_at timestamptz, parameters json,
  annual_return double, max_drawdown double, win_rate double, result json
);
create table if not exists daily_recommendations (
  trade_date date, rank smallint, symbol varchar, model_version varchar,
  previous_rank smallint, rank_change smallint, score smallint, confidence smallint,
  industry varchar, explanation json, experimental boolean, created_at timestamptz,
  primary key (trade_date, rank, model_version)
);
"""


def _sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def connect_database(data_root: Path) -> duckdb.DuckDBPyConnection:
    data_root.mkdir(parents=True, exist_ok=True)
    db = duckdb.connect(str(data_root / "quant.duckdb"))
    db.execute(SCHEMA_SQL)
    history_glob = _sql_path(data_root / "raw" / "history" / "*.parquet")
    spot_path = _sql_path(data_root / "raw" / "spot.parquet")
    financial_path = _sql_path(data_root / "raw" / "financial.parquet")
    if list((data_root / "raw" / "history").glob("*.parquet")):
        db.execute(f"create or replace view daily_bars as select * from read_parquet('{history_glob}', union_by_name=true, filename=true)")
    if (data_root / "raw" / "spot.parquet").exists():
        db.execute(f"create or replace view latest_spot as select * from read_parquet('{spot_path}', union_by_name=true)")
    if (data_root / "raw" / "financial.parquet").exists():
        db.execute(f"create or replace view latest_financial as select * from read_parquet('{financial_path}', union_by_name=true)")
    db.execute("create or replace view latest_scores as select * exclude(rn) from (select *, row_number() over(partition by symbol order by trade_date desc, created_at desc) rn from daily_scores) where rn=1")
    return db


def update_database(data_root: Path, payload: dict, collection_meta: dict) -> dict:
    db = connect_database(data_root)
    updated_at = payload["updatedAt"]
    trade_date = updated_at[:10]
    stocks = payload.get("stocks", [])
    run_id = str(uuid.uuid4())
    failures = collection_meta.get("failures", [])
    try:
        db.execute("begin")
        for stock in stocks:
            db.execute("""insert or replace into instruments(symbol,name,industry,status,updated_at)
                values (?,?,?,?,?)""", [stock["code"],stock["name"],stock.get("industry") or "未分类",
                "excluded" if stock.get("flags") else "active",updated_at])
            db.execute("""insert or replace into daily_scores values
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", [trade_date,stock["code"],payload["modelVersion"],payload.get("mode","preview"),
                stock["score"],stock["confidence"],_rating(stock["score"]),stock.get("quality",0),stock.get("growth",0),
                stock.get("valuation",0),stock.get("trend",0),stock.get("risk",0),stock.get("liquidity",0),
                bool(stock.get("flags")),json.dumps(stock,ensure_ascii=False),updated_at])
        for item in payload.get("recommendations", []):
            db.execute("""insert or replace into daily_recommendations values
                (?,?,?,?,?,?,?,?,?,?,?,?)""", [trade_date,item["rank"],item["code"],payload["modelVersion"],
                item.get("previousRank"),item.get("rankChange"),item["score"],item["confidence"],item["industry"],
                json.dumps(item.get("explanation",{}),ensure_ascii=False),True,updated_at])
        expected = int(collection_meta.get("symbols", len(stocks)))
        coverage = (expected-len(failures))/expected if expected else 0
        db.execute("""insert into sync_runs values (?,?,?,?,?,?,?,?,?,?,?)""", [run_id,
            collection_meta.get("collectedAt",updated_at),updated_at,"success",trade_date,expected,len(stocks),
            len(failures),coverage,json.dumps(payload.get("sources",[]),ensure_ascii=False),None])
        db.execute("commit")
        counts=db.execute("select (select count(*) from daily_bars),(select count(*) from instruments),(select count(*) from daily_scores)").fetchone()
        return {"daily_bars":counts[0],"instruments":counts[1],"daily_scores":counts[2],"run_id":run_id}
    except Exception:
        db.execute("rollback")
        raise
    finally:
        db.close()


def _rating(score: int) -> str:
    if score>=80:return "重点研究"
    if score>=70:return "值得关注"
    if score>=55:return "中性观察"
    if score>=40:return "谨慎"
    return "回避"
