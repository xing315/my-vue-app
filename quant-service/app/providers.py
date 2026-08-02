from __future__ import annotations

import time
import socket
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Iterable

import pandas as pd
import numpy as np


def _rename(frame: pd.DataFrame, aliases: dict[str, list[str]]) -> pd.DataFrame:
    """Normalize changing upstream Chinese column names without silently inventing data."""
    mapping = {}
    for target, candidates in aliases.items():
        found = next((name for name in candidates if name in frame.columns), None)
        if found:
            mapping[found] = target
    return frame.rename(columns=mapping)


class AkshareProvider:
    def spot_sina(self) -> pd.DataFrame:
        import akshare as ak
        frame = ak.stock_zh_a_spot()
        frame = _rename(frame, {"code":["代码"],"name":["名称"],"price":["最新价"],
            "change":["涨跌幅"],"volume":["成交量"],"amount":["成交额"],"high":["最高"],"low":["最低"]})
        if not {"code","name","price","amount"}.issubset(frame.columns):
            raise ValueError("新浪行情字段不完整")
        frame["code"] = frame["code"].astype(str).str.extract(r"(\d{6})$",expand=False)
        frame = frame[frame.code.str.match(r"^[036]\d{5}$",na=False)]
        for col in ["price","change","volume","amount","high","low"]:
            if col in frame: frame[col]=pd.to_numeric(frame[col],errors="coerce")
        for col in ["turnover","pe","pb","market_cap"]: frame[col]=np.nan
        return frame

    def spot(self) -> pd.DataFrame:
        import akshare as ak
        frame = ak.stock_zh_a_spot_em()
        frame = _rename(frame, {
            "code": ["代码"], "name": ["名称"], "price": ["最新价"],
            "change": ["涨跌幅"], "volume": ["成交量"], "amount": ["成交额"],
            "turnover": ["换手率"], "pe": ["市盈率-动态", "市盈率"],
            "pb": ["市净率"], "market_cap": ["总市值"],
            "float_cap": ["流通市值"], "high": ["最高"], "low": ["最低"],
        })
        required = {"code", "name", "price", "amount", "turnover"}
        if not required.issubset(frame.columns):
            raise ValueError(f"AKShare 行情字段不完整: {sorted(required - set(frame.columns))}")
        frame["code"] = frame["code"].astype(str).str.zfill(6)
        for col in set(frame.columns) & {"price","change","volume","amount","turnover","pe","pb","market_cap","float_cap","high","low"}:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
        return frame

    def financial_report(self, report_date: str) -> pd.DataFrame:
        import akshare as ak
        frame = ak.stock_yjbb_em(date=report_date)
        frame = _rename(frame, {
            "code": ["股票代码", "代码"], "name": ["股票简称", "名称"],
            "roe": ["净资产收益率", "净资产收益率(%)"],
            "revenue": ["营业总收入-营业总收入", "营业总收入", "营业收入"],
            "revenue_growth": ["营业总收入-同比增长", "营业总收入同比增长", "营业收入同比增长"],
            "profit": ["净利润-净利润", "净利润"], "profit_growth": ["净利润-同比增长", "净利润同比增长"],
            "eps": ["每股收益"], "bps": ["每股净资产"],
            "cashflow_ps": ["每股经营现金流量", "每股经营现金流"],
            "gross_margin": ["销售毛利率", "毛利率"],
            "publish_date": ["最新公告日期", "公告日期"],
            "industry": ["所处行业", "行业"],
        })
        if "code" not in frame.columns:
            raise ValueError("AKShare 业绩报表缺少股票代码")
        frame["code"] = frame["code"].astype(str).str.zfill(6)
        for col in set(frame.columns) & {"roe","revenue","revenue_growth","profit","profit_growth","eps","bps","cashflow_ps","gross_margin"}:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
        frame["report_date"] = report_date
        return frame

    def history_many(self, symbols: Iterable[str], start: date, end: date,
                     delay: float = 0.15) -> Iterable[tuple[str, pd.DataFrame, str | None]]:
        """Eastmoney history fallback when BaoStock's socket service is unavailable."""
        import akshare as ak
        for symbol in symbols:
            try:
                frame = ak.stock_zh_a_hist(
                    symbol=symbol, period="daily",
                    start_date=start.strftime("%Y%m%d"), end_date=end.strftime("%Y%m%d"),
                    adjust="qfq")
                frame = _rename(frame, {
                    "date":["日期"], "open":["开盘"], "high":["最高"], "low":["最低"],
                    "close":["收盘"], "volume":["成交量"], "amount":["成交额"],
                    "turn":["换手率"], "pctChg":["涨跌幅"]})
                required = {"date", "close", "amount"}
                if frame.empty or not required.issubset(frame.columns):
                    yield symbol, pd.DataFrame(), "empty_or_missing_fields"
                    continue
                for col in ["open","high","low","close","volume","amount","turn","pctChg"]:
                    if col in frame: frame[col] = pd.to_numeric(frame[col], errors="coerce")
                frame["tradestatus"] = "1"; frame["isST"] = "0"
                yield symbol, frame, None
            except Exception as exc:
                yield symbol, pd.DataFrame(), type(exc).__name__
            time.sleep(delay)

    def history_many_sina(self, symbols: Iterable[str], start: date, end: date,
                          delay: float = 0.12) -> Iterable[tuple[str, pd.DataFrame, str | None]]:
        import akshare as ak
        for symbol in symbols:
            try:
                prefix = "sh" if symbol.startswith(("5","6","9")) else "sz"
                frame = ak.stock_zh_a_daily(symbol=prefix+symbol,
                    start_date=start.strftime("%Y%m%d"),end_date=end.strftime("%Y%m%d"),adjust="qfq")
                if frame.empty: yield symbol,pd.DataFrame(),"empty"; continue
                frame=frame.reset_index(); frame["tradestatus"]="1"; frame["isST"]="0"
                if "turnover" in frame: frame["turn"]=pd.to_numeric(frame["turnover"],errors="coerce")*100
                yield symbol,frame,None
            except Exception as exc: yield symbol,pd.DataFrame(),type(exc).__name__
            time.sleep(delay)

    def financial_many_sina(self, symbols: Iterable[str], start_year: int,
                            delay: float = 0.12) -> pd.DataFrame:
        import akshare as ak
        rows=[]
        for idx,symbol in enumerate(symbols,1):
            try:
                frame=ak.stock_financial_analysis_indicator(symbol=symbol,start_year=str(start_year))
                if frame.empty: continue
                row=frame.sort_values("日期").iloc[-1]
                rows.append({"code":symbol,"report_date":str(row.get("日期","")),
                    "roe":pd.to_numeric(row.get("净资产收益率(%)"),errors="coerce"),
                    "gross_margin":pd.to_numeric(row.get("销售毛利率(%)"),errors="coerce"),
                    "revenue_growth":pd.to_numeric(row.get("主营业务收入增长率(%)"),errors="coerce"),
                    "profit_growth":pd.to_numeric(row.get("净利润增长率(%)"),errors="coerce"),
                    "cashflow_ps":pd.to_numeric(row.get("每股经营性现金流(元)"),errors="coerce")})
            except Exception: pass
            if idx%100==0: print(f"Sina financial {idx}/{len(symbols)}",flush=True)
            time.sleep(delay)
        return pd.DataFrame(rows)


class BaoStockProvider:
    @contextmanager
    def session(self):
        import baostock as bs
        previous_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(20)
        logged_in = False
        try:
            result = bs.login()
            if result.error_code != "0":
                raise ConnectionError(f"BaoStock 登录失败: {result.error_msg}")
            logged_in = True
            yield bs
        finally:
            if logged_in:
                bs.logout()
            socket.setdefaulttimeout(previous_timeout)

    @staticmethod
    def exchange_code(symbol: str) -> str:
        return ("sh." if symbol.startswith(("5", "6", "9")) else "sz.") + symbol

    def history_many(self, symbols: Iterable[str], start: date, end: date,
                     delay: float = 0.08) -> Iterable[tuple[str, pd.DataFrame, str | None]]:
        fields = "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,isST"
        with self.session() as bs:
            for symbol in symbols:
                try:
                    rs = bs.query_history_k_data_plus(
                        self.exchange_code(symbol), fields,
                        start_date=start.isoformat(), end_date=end.isoformat(),
                        frequency="d", adjustflag="2")  # forward-adjusted
                    if rs.error_code != "0":
                        yield symbol, pd.DataFrame(), rs.error_msg
                        continue
                    rows = []
                    while rs.error_code == "0" and rs.next():
                        rows.append(rs.get_row_data())
                    frame = pd.DataFrame(rows, columns=rs.fields)
                    for col in ["open","high","low","close","preclose","volume","amount","turn","pctChg","peTTM","pbMRQ"]:
                        if col in frame: frame[col] = pd.to_numeric(frame[col], errors="coerce")
                    yield symbol, frame, None
                except Exception as exc:
                    yield symbol, pd.DataFrame(), type(exc).__name__
                time.sleep(delay)

    def universe(self, day: date | None = None) -> pd.DataFrame:
        """Fallback universe when public realtime quote endpoints are unavailable."""
        day = day or date.today()
        with self.session() as bs:
            for offset in range(10):
                rs = bs.query_all_stock((day - timedelta(days=offset)).isoformat())
                rows = []
                while rs.error_code == "0" and rs.next(): rows.append(rs.get_row_data())
                if rows:
                    frame = pd.DataFrame(rows, columns=rs.fields)
                    frame["code"] = frame["code"].str.split(".").str[-1]
                    frame = frame.rename(columns={"code_name":"name", "tradeStatus":"trade_status"})
                    frame = frame[frame.code.str.match(r"^[036]\d{5}$")]
                    for col in ["price","change","amount","turnover","pe","pb","market_cap"]:
                        frame[col] = np.nan
                    return frame
        raise ConnectionError("BaoStock 无法取得最近交易日证券列表")


def latest_expected_report_day(today: date) -> str:
    """Choose the latest broadly disclosed quarter; never select a future filing."""
    if today >= date(today.year, 10, 31): return f"{today.year}0930"
    if today >= date(today.year, 8, 31): return f"{today.year}0630"
    if today >= date(today.year, 4, 30): return f"{today.year}0331"
    return f"{today.year - 1}1231"
