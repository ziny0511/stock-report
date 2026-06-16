import requests
import os
from datetime import datetime, timedelta

KRX_API_KEY = os.environ.get("KRX_API_KEY", "")
API_BASE    = "https://data-dbg.krx.co.kr/svc/apis/sto"

ENDPOINTS = {
    "KOSPI":  { "daily": "/stk_bydd_trd", "info": "/stk_isu_base_info" },
    "KOSDAQ": { "daily": "/ksq_bydd_trd", "info": "/ksq_isu_base_info" },
}

def _get(endpoint, base_date):
    headers = {
        "AUTH_KEY":     KRX_API_KEY.strip(),
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }
    try:
        res = requests.get(
            API_BASE + endpoint,
            headers=headers,
            params={"basDd": base_date},
            timeout=20
        )
        if res.status_code != 200:
            return []
        return res.json().get("OutBlock_1", [])
    except:
        return []

def _last_biz_dates(n=20):
    dates, dt = [], datetime.today() - timedelta(days=1)
    while len(dates) < n:
        if dt.weekday() < 5:
            dates.append(dt.strftime("%Y%m%d"))
        dt -= timedelta(days=1)
    return dates

def _parse_code(item):
    return (item.get("ISU_SRT_CD") or item.get("ISU_CD", "")[:6]).strip()

def _parse_close(item):
    try:
        return int(item.get("TDD_CLSPRC", "0").replace(",", ""))
    except:
        return 0

def _parse_chg(item):
    try:
        return float(item.get("FLUC_RT", "0").replace(",", ""))
    except:
        return 0.0

def _parse_volume(item):
    try:
        return int(item.get("ACC_TRDVAL", "0").replace(",", ""))
    except:
        return 0

def get_market_data(n_days=20):
    biz_dates = _last_biz_dates(n_days)
    stocks = {}

    for date in biz_dates:
        for market in ["KOSPI", "KOSDAQ"]:
            items = _get(ENDPOINTS[market]["daily"], date)
            for item in items:
                code   = _parse_code(item)
                name   = item.get("ISU_ABBRV", item.get("ISU_NM", code)).strip()
                close  = _parse_close(item)
                chg    = _parse_chg(item)
                volume = _parse_volume(item)
                if not code or close <= 0:
                    continue
                if code not in stocks:
                    stocks[code] = {"name": name, "market": market, "prices": []}
                stocks[code]["prices"].append({
                    "date":    date,
                    "close":   close,
                    "chg_pct": chg,
                    "volume":  volume,
                })

    for code in stocks:
        stocks[code]["prices"].sort(key=lambda x: x["date"])

    print(f"[KRX] 전체 종목 {len(stocks)}개 / {n_days}영업일 수집 완료")
    return stocks


def find_consecutive_surge(stocks, min_days=3, min_pct=10.0):
    result = []
    for code, info in stocks.items():
        prices  = info["prices"]
        streaks = []
        i = 0
        while i < len(prices):
            if prices[i]["chg_pct"] >= min_pct:
                j = i
                while j < len(prices) and prices[j]["chg_pct"] >= min_pct:
                    j += 1
                if j - i >= min_days:
                    sp = prices[i:j]
                    streaks.append({
                        "start":  sp[0]["date"],
                        "end":    sp[-1]["date"],
                        "days":   j - i,
                        "pcts":   [p["chg_pct"] for p in sp],
                        "closes": [p["close"]   for p in sp],
                        "dates":  [p["date"]    for p in sp],
                    })
                i = j
            else:
                i += 1

        if streaks:
            last_price  = prices[-1]
            result.append({
                "code":        code,
                "name":        info["name"],
                "market":      info["market"],
                "streaks":     streaks,
                "last_volume": last_price["volume"],
                "last_close":  last_price["close"],   # ← 전일 종가 추가
                "last_chg":    last_price["chg_pct"], # ← 전일 등락률 추가
            })

    result.sort(key=lambda x: x["last_volume"], reverse=True)
    print(f"[분석] 연속 상승 종목 {len(result)}개 발견")
    return result


def find_consecutive_decline(stocks, min_days=5):
    result = []
    for code, info in stocks.items():
        prices  = info["prices"]
        streaks = []
        i = 0
        while i < len(prices):
            if prices[i]["chg_pct"] < 0:
                j = i
                while j < len(prices) and prices[j]["chg_pct"] < 0:
                    j += 1
                if j - i >= min_days:
                    sp = prices[i:j]
                    streaks.append({
                        "start":  sp[0]["date"],
                        "end":    sp[-1]["date"],
                        "days":   j - i,
                        "pcts":   [p["chg_pct"] for p in sp],
                        "closes": [p["close"]   for p in sp],
                        "dates":  [p["date"]    for p in sp],
                    })
                i = j
            else:
                i += 1

        if streaks:
            last_price  = prices[-1]
            result.append({
                "code":        code,
                "name":        info["name"],
                "market":      info["market"],
                "streaks":     streaks,
                "last_volume": last_price["volume"],
                "last_close":  last_price["close"],   # ← 전일 종가 추가
                "last_chg":    last_price["chg_pct"], # ← 전일 등락률 추가
            })

    result.sort(key=lambda x: x["last_volume"], reverse=True)
    print(f"[분석] 연속 하락 종목 {len(result)}개 발견")
    return result


def get_top10_fluctuation(stocks):
    yesterday = _last_biz_dates(1)[0]
    day_data  = []

    for code, info in stocks.items():
        for p in info["prices"]:
            if p["date"] == yesterday:
                day_data.append({
                    "code":    code,
                    "name":    info["name"],
                    "market":  info["market"],
                    "chg_pct": p["chg_pct"],
                    "close":   p["close"],
                    "volume":  p["volume"],
                })
                break

    top_up   = sorted([d for d in day_data if d["chg_pct"] > 0],
                      key=lambda x: x["chg_pct"], reverse=True)[:10]
    top_down = sorted([d for d in day_data if d["chg_pct"] < 0],
                      key=lambda x: x["chg_pct"])[:10]

    print(f"[분석] 전일 상승 {len(top_up)}개 / 하락 {len(top_down)}개")
    return top_up, top_down
