from pykrx import stock
from datetime import datetime, timedelta

def get_10day_price(stock_code):
    """
    pykrx로 최근 10영업일 주가 조회
    반환: [{"date": "06/01", "close": 82600, "change_pct": +3.2}, ...]
    """
    try:
        end_dt   = datetime.today().strftime("%Y%m%d")
        start_dt = (datetime.today() - timedelta(days=30)).strftime("%Y%m%d")
        df = stock.get_market_ohlcv(start_dt, end_dt, stock_code)
        if df is None or df.empty:
            return []
        df = df.tail(10)
        result = []
        for date, row in df.iterrows():
            close     = int(row["종가"])
            prev      = int(row["시가"]) if int(row["시가"]) > 0 else close
            chg_pct   = round((close - prev) / prev * 100, 2) if prev else 0
            result.append({
                "date":       date.strftime("%m/%d"),
                "close":      close,
                "change_pct": chg_pct,
            })
        return result
    except Exception as e:
        print(f"[pykrx] 주가 조회 실패 ({stock_code}): {e}")
        return []

def get_corp_code_from_name(corp_name):
    """기업명 → 종목코드"""
    try:
        tickers = stock.get_market_ticker_list(market="ALL")
        for ticker in tickers:
            name = stock.get_market_ticker_name(ticker)
            if name == corp_name:
                return ticker
    except Exception as e:
        print(f"[pykrx] 종목코드 조회 실패 ({corp_name}): {e}")
    return ""
