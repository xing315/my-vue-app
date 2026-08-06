from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from collections import defaultdict

from .indicators import dimension_scores, history_features
from .providers import AkshareProvider, BaoStockProvider, latest_expected_report_day
from .scoring import score_stock, suggested_position

TZ = ZoneInfo("Asia/Shanghai")
MODEL_VERSION = "cn-equity-v1.1"

def configure_network():
    """Public data endpoints often fail through a macOS HTTP proxy.

    Default to direct connections. Set QUANT_USE_SYSTEM_PROXY=1 when the local
    network genuinely requires its configured proxy.
    """
    if os.getenv("QUANT_USE_SYSTEM_PROXY") == "1": return
    for key in ("HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"):
        os.environ.pop(key, None)
    os.environ["NO_PROXY"] = "*"; os.environ["no_proxy"] = "*"

def finite(value, default=None):
    try:
        number = float(value)
        return number if np.isfinite(number) else default
    except (TypeError, ValueError): return default

def reasons(row) -> tuple[str, str]:
    positives, risks = [], []
    if row.quality_n >= .7: positives.append("盈利质量位于全市场较高分位")
    if row.growth_n >= .7: positives.append("营收与利润增速相对突出")
    if row.valuation_n >= .7: positives.append("估值处于相对有利分位")
    if row.trend_n >= .7: positives.append("半年至一年中期趋势较强")
    if row.risk_n < .35: risks.append("历史波动或回撤偏高")
    if row.valuation_n < .35: risks.append("估值安全边际不足")
    if row.growth_n < .35: risks.append("增长指标弱于市场中位数")
    return ("；".join(positives[:3]) or "当前指标未形成明显的中长线优势",
            "；".join(risks[:3]) or "若盈利趋势或行业景气转弱，当前结论可能失效")

def append_spot_bar(path: Path, row, trading_day: date) -> bool:
    """Append today's already-fetched quote instead of requesting history again."""
    close=finite(getattr(row,"price",None))
    amount=finite(getattr(row,"amount",None))
    if close is None or amount is None or amount <= 0: return False
    change=finite(getattr(row,"change",None))
    preclose=finite(getattr(row,"preclose",None))
    if preclose is None and change is not None and change != -100:
        preclose=close/(1+change/100)
    bar=pd.DataFrame([{"date":pd.Timestamp(trading_day),"open":finite(getattr(row,"open",None),close),
      "high":finite(getattr(row,"high",None),close),"low":finite(getattr(row,"low",None),close),
      "close":close,"preclose":preclose,"volume":finite(getattr(row,"volume",None)),"amount":amount,
      "turn":finite(getattr(row,"turnover",None)),"pctChg":change,"tradestatus":"1","isST":"0"}])
    old=pd.read_parquet(path)
    old["date"]=pd.to_datetime(old["date"],errors="coerce")
    combined=pd.concat([old,bar],ignore_index=True,sort=False).dropna(subset=["date"])
    combined=combined.drop_duplicates("date",keep="last").sort_values("date")
    combined.to_parquet(path,index=False)
    return True

def collect(data_root: Path, limit: int | None = None) -> Path:
    configure_network()
    raw = data_root / "raw"; history_dir = raw / "history"
    raw.mkdir(parents=True, exist_ok=True); history_dir.mkdir(parents=True, exist_ok=True)
    ak = AkshareProvider(); provider = BaoStockProvider()
    try:
        spot = ak.spot(); spot_source = "AKShare"
    except Exception as exc:
        print(f"东方财富行情不可用，切换新浪: {type(exc).__name__}", flush=True)
        try:
            spot = ak.spot_sina(); spot_source = "Sina"
        except Exception as sina_exc:
            print(f"新浪行情不可用，切换 BaoStock: {type(sina_exc).__name__}",flush=True)
            spot = provider.universe(); spot_source = "BaoStock"
    spot = spot[spot.code.str.match(r"^[036]\d{5}$")].drop_duplicates("code")
    if limit: spot = spot.head(limit)
    report_day = latest_expected_report_day(date.today())
    try:
        financial = ak.financial_report(report_day); financial_source = "AKShare"
    except Exception as exc:
        print(f"东方财富财务不可用，切换新浪: {type(exc).__name__}", flush=True)
        financial = ak.financial_many_sina(spot.code.tolist(),date.today().year-3)
        financial_source = "Sina" if not financial.empty else "unavailable"
    spot.to_parquet(raw / "spot.parquet", index=False)
    financial.to_parquet(raw / "financial.parquet", index=False)
    symbols = spot.code.tolist(); today=date.today()
    try:
        days=[day for day in ak.trading_days() if day <= today]
        end=max(days)
        if end == today and datetime.now(TZ).time() < datetime.strptime("15:05","%H:%M").time():
            end=max(day for day in days if day < today)
    except Exception as exc:
        end=today
        print(f"交易日历不可用，按当天检查: {type(exc).__name__}",flush=True)
    previous=max((day for day in days if day < end),default=None) if 'days' in locals() else None
    default_start = end - timedelta(days=900)
    groups=defaultdict(list); cached_count=0; cache_errors=0
    spot_appended=0; spot_rows={row.code:row for row in spot.itertuples()}
    for symbol in symbols:
        path=history_dir/f"{symbol}.parquet"; symbol_start=default_start
        if path.exists():
            try:
                cached=pd.read_parquet(path,columns=["date"])
                if "date" in cached.columns:
                    # 尝试多种日期格式兼容
                    last=pd.to_datetime(cached["date"],errors="coerce").max()
                    if pd.notna(last) and last.year > 2000:
                        symbol_start=last.date()+timedelta(days=1)
                        # 盘后 spot 已包含今日 OHLC，常规日更无需再逐只请求历史接口。
                        if end == today and last.date() == previous:
                            if symbol in spot_rows and append_spot_bar(path,spot_rows[symbol],end):
                                symbol_start=end+timedelta(days=1); spot_appended+=1
                    else:
                        cache_errors+=1
                else:
                    cache_errors+=1
            except Exception:
                cache_errors+=1
        if symbol_start<=end: groups[symbol_start].append(symbol)
        else: cached_count+=1
    if cache_errors>0: print(f"缓存检查: {cache_errors} 只股票缓存异常，将全量拉取", flush=True)
    print(f"缓存检查: {cached_count} 只本地已就绪(其中 {spot_appended} 只追加当日行情), {sum(len(v) for v in groups.values())} 只需补历史", flush=True)
    def grouped(iterator_factory):
        for group_start,group_symbols in groups.items():
            yield from iterator_factory(group_symbols,group_start,end)
    def save_histories(iterator, source):
        failed=[]; succeeded=cached_count
        for idx, (symbol, frame, error) in enumerate(iterator, 1):
            if error or frame.empty: failed.append({"code":symbol,"error":error or "empty"})
            else:
                path=history_dir/f"{symbol}.parquet"
                # 统一date列为Timestamp类型，避免datetime.date与Timestamp混排报错
                if "date" in frame.columns:
                    frame["date"]=pd.to_datetime(frame["date"],errors="coerce")
                if path.exists():
                    old=pd.read_parquet(path)
                    if "date" in old.columns:
                        old["date"]=pd.to_datetime(old["date"],errors="coerce")
                    combined=pd.concat([old,frame],ignore_index=True,sort=False)
                    if "date" in combined.columns:
                        combined=combined.dropna(subset=["date"])
                        combined=combined.drop_duplicates("date",keep="last").sort_values("date")
                    frame=combined
                frame.to_parquet(path,index=False); succeeded += 1
            if idx % 100 == 0 or idx == sum(map(len,groups.values())): print(f"{source} history {idx}/{sum(map(len,groups.values()))} (+{cached_count} cached)", flush=True)
        return succeeded, failed
    if not groups:
        history_source="local-cache"; succeeded=cached_count; failures=[]
    else:
        try:
            history_source = "BaoStock"
            succeeded, failures = save_histories(grouped(provider.history_many), history_source)
        except Exception as exc:
            print(f"BaoStock 历史行情不可用，切换新浪: {type(exc).__name__}", flush=True)
            history_source = "Sina"
            succeeded, failures = save_histories(grouped(ak.history_many_sina), history_source)
    if succeeded == 0:
        raise ConnectionError("两个历史行情源均不可用，未发布评分快照")
    (raw / "collection-meta.json").write_text(json.dumps({"collectedAt":datetime.now(TZ).isoformat(),"reportDate":report_day,"symbols":len(symbols),"failures":failures,"spotSource":spot_source,"financialSource":financial_source,"historySource":history_source},ensure_ascii=False,indent=2),encoding="utf-8")
    return raw

def build(data_root: Path, min_coverage: float = .75) -> Path:
    raw=data_root/"raw"; history_dir=raw/"history"
    spot=pd.read_parquet(raw/"spot.parquet"); financial=pd.read_parquet(raw/"financial.parquet")
    meta=json.loads((raw/"collection-meta.json").read_text(encoding="utf-8"))
    features=[]
    for symbol in spot.code:
        path=history_dir/f"{symbol}.parquet"
        if path.exists(): features.append({"code":symbol,**history_features(pd.read_parquet(path))})
    history=pd.DataFrame(features)
    coverage=len(history)/max(1,len(spot))
    if coverage < min_coverage: raise RuntimeError(f"历史数据覆盖率 {coverage:.1%} 低于发布阈值 {min_coverage:.1%}")
    merged=spot.merge(financial,on="code",how="left",suffixes=("","_fin")).merge(history,on="code",how="left")
    for target, fallback in [("price","history_price"),("change","history_change"),("turnover","history_turnover"),("pe","history_pe"),("pb","history_pb")]:
        if fallback in merged:
            merged[target] = pd.to_numeric(merged.get(target),errors="coerce").fillna(merged[fallback])
    scored=dimension_scores(merged)
    published=[]
    for row in scored.itertuples():
        exclusions=[]; name=str(row.name)
        if "ST" in name.upper() or "退" in name: exclusions.append("ST或退市风险")
        if getattr(row,"history_days",0)<240: exclusions.append("上市或有效历史不足一年")
        if finite(getattr(row,"avg_amount_20",None),0)<20_000_000: exclusions.append("流动性过低")
        if not getattr(row,"trading",True): exclusions.append("当前停牌")
        dims={k:finite(getattr(row,f"{k}_n",None),0) for k in ("quality","growth","valuation","trend","risk","liquidity")}
        completeness=sum(finite(getattr(row,c,None)) is not None for c in ("roe","revenue_growth","profit_growth","pe","pb","return_1y","volatility","avg_amount_20"))/8
        result=score_stock(dims,completeness,exclusions)
        pos=suggested_position(result.score,result.confidence,finite(getattr(row,"volatility",None),1),result.excluded)
        reason,counter=reasons(row)
        industry=getattr(row,"industry",None)
        if not isinstance(industry,str) or not industry.strip(): industry="未分类"
        metrics={"roe":finite(getattr(row,"roe",None)),"grossMargin":finite(getattr(row,"gross_margin",None)),
          "revenueGrowth":finite(getattr(row,"revenue_growth",None)),"profitGrowth":finite(getattr(row,"profit_growth",None)),
          "cashflowPerShare":finite(getattr(row,"cashflow_ps",None)),"return1y":finite(getattr(row,"return_1y",None)),
          "maxDrawdown":finite(getattr(row,"max_drawdown",None)),"volatility":finite(getattr(row,"volatility",None)),
          "ma20Ratio":finite(getattr(row,"ma20_ratio",None)),"ma60Ratio":finite(getattr(row,"ma60_ratio",None)),
          "averageAmount20":finite(getattr(row,"avg_amount_20",None))}
        published.append({"code":row.code,"name":name,"industry":industry,"price":finite(row.price,0),"change":finite(getattr(row,"change",0),0),"score":result.score,"confidence":result.confidence,
          "quality":round(dims["quality"]*25),"growth":round(dims["growth"]*20),"valuation":round(dims["valuation"]*20),"trend":round(dims["trend"]*15),"risk":round(dims["risk"]*10),"liquidity":round(dims["liquidity"]*10),"position":list(pos),"pe":finite(getattr(row,"pe",None)),"pb":finite(getattr(row,"pb",None)),"reportDate":str(getattr(row,"report_date","")),"reason":reason,"counter":counter,"flags":exclusions})
        published[-1]["metrics"] = metrics
    published.sort(key=lambda x:(x["score"],x["confidence"]),reverse=True)
    eligible=[s for s in published if not s["flags"]]
    changes=pd.to_numeric(spot.change,errors="coerce")
    pe_rank=pd.to_numeric(spot.get("pe"),errors="coerce").rank(pct=True).median()
    valuation=round(float(pe_rank*100)) if pd.notna(pe_rank) else 0
    release_mode="live" if len(spot)>=1000 else "preview"
    payload={"mode":release_mode,"updatedAt":datetime.now(TZ).isoformat(),"modelVersion":MODEL_VERSION,
      "market":{"indices":[],"breadth":round(float((changes>0).mean()*100)),"valuation":valuation,"risk":"中性"},
      "stocks":published,
      "validation":{"annualReturn":0,"maxDrawdown":0,"winRate":0,"excessReturn":0,"period":"滚动回测待生成"},
      "sources":[{"name":meta.get("historySource","历史行情"),"state":"ready","detail":f"复权日线覆盖 {coverage:.1%}"},{"name":meta.get("financialSource","财务数据"),"state":"ready","detail":f"行情来源 {meta.get('spotSource','unknown')}"},{"name":"数据质量","state":"ready","detail":f"已评分 {len(published)} 只"}]}
    target=data_root/"latest-dashboard.json"
    previous_payload=None
    if target.exists():
        try: previous_payload=json.loads(target.read_text(encoding="utf-8"))
        except (OSError,ValueError): previous_payload=None
    from .recommendations import build_recommendations
    payload["recommendations"] = build_recommendations(data_root, payload)
    from .signals import build_signal_events
    payload["signals"] = build_signal_events(payload, previous_payload)
    temp=data_root/"latest-dashboard.json.tmp"
    temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8"); os.replace(temp,target)
    from .local_db import update_database
    try:
        db_result=update_database(data_root,payload,meta)
    except Exception as exc:
        if "Conflicting lock" not in str(exc): raise
        db_result={"status":"skipped","reason":"DuckDB 正被 DBeaver 占用"}
        print("DuckDB 正被 DBeaver 占用，本次跳过本地表写入；JSON 与线上发布继续",flush=True)
    print(f"published {target}: {len(published)} scored, {len(eligible)} eligible")
    print(f"DuckDB updated: {db_result}",flush=True)
    return target

def main():
    parser=argparse.ArgumentParser(description="A股盘后数据与评分流水线")
    parser.add_argument("command",choices=["collect","build","db-init","publish","all"]); parser.add_argument("--data-root",default="data")
    parser.add_argument("--limit",type=int); parser.add_argument("--min-coverage",type=float,default=.75)
    args=parser.parse_args(); root=Path(args.data_root)
    if args.command in ("collect","all"): collect(root,args.limit)
    if args.command in ("build","all"): build(root,args.min_coverage)
    if args.command == "db-init":
        from .local_db import connect_database
        db=connect_database(root)
        print(db.execute("select count(*) from daily_bars").fetchone()[0] if "daily_bars" in [r[0] for r in db.execute("show tables").fetchall()] else 0)
        db.close()
    if args.command in ("publish","all"):
        if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
            from .publisher import publish_file
            print(publish_file(root/"latest-dashboard.json"), flush=True)
        elif args.command == "publish":
            raise RuntimeError("发布需要 SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY")
        elif os.getenv("QUANT_REQUIRE_SUPABASE_PUBLISH") == "1":
            raise RuntimeError("本次同步要求自动发布，但缺少 SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY")
        else:
            print("未配置 Supabase service_role，跳过线上发布", flush=True)

if __name__ == "__main__": main()
