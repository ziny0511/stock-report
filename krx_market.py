import requests
import os
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

KRX_API_KEY = os.environ.get("KRX_API_KEY", "")
API_BASE    = "https://data-dbg.krx.co.kr/svc/apis/sto"

WINDOW_DAYS = {"1m": 22, "2m": 44, "6m": 130, "12m": 260}
WINDOW_LABELS = {"1m": "1개월", "2m": "2개월", "6m": "6개월", "12m": "12개월"}

CACHE_PATH = "docs/data/raw"  # 날짜별 원시 데이터 캐시 폴더
MAX_WORKERS = 8               # 병렬 API 호출 수

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

def _last_biz_dates(n=260):
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

# ── 캐시 로드/저장 ──────────────────────────────────────────
def _cache_file(date):
    return os.path.join(CACHE_PATH, f"{date}.json")

def _load_cache(date):
    path = _cache_file(date)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return None

def _save_cache(date, data):
    os.makedirs(CACHE_PATH, exist_ok=True)
    with open(_cache_file(date), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

# ── 하루치 데이터 fetch (캐시 우선) ─────────────────────────
def _fetch_day(date):
    cached = _load_cache(date)
    if cached is not None:
        return date, cached

    day_stocks = {}
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
            day_stocks[code] = {
                "name":    name,
                "market":  market,
                "close":   close,
                "chg_pct": chg,
                "volume":  volume,
            }

    if day_stocks:
        _save_cache(date, day_stocks)
    return date, day_stocks

# ── 메인 수집 함수 (병렬 + 캐시) ────────────────────────────
def get_market_data(n_days=260):
    biz_dates = _last_biz_dates(n_days)
    today_str = biz_dates[0]  # 가장 최근 날짜 = 캐시 저장 안 함(당일만 제외)

    cached_count = sum(1 for d in biz_dates if os.path.exists(_cache_file(d)))
    fetch_count  = len(biz_dates) - cached_count
    print(f"[KRX] 캐시 {cached_count}일 / API 호출 {fetch_count}일 (병렬 {MAX_WORKERS}workers)")

    results = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(_fetch_day, d): d for d in biz_dates}
        done = 0
        for fut in as_completed(futures):
            date, day_data = fut.result()
            results[date] = day_data
            done += 1
            if done % 20 == 0:
                print(f"  ... {done}/{len(biz_dates)} 완료")

    # stocks 딕셔너리 조립
    stocks = {}
    for date in sorted(results.keys()):
        for code, info in results[date].items():
            if code not in stocks:
                stocks[code] = {"name": info["name"], "market": info["market"], "prices": []}
            stocks[code]["prices"].append({
                "date":    date,
                "close":   info["close"],
                "chg_pct": info["chg_pct"],
                "volume":  info["volume"],
            })

    print(f"[KRX] 전체 종목 {len(stocks)}개 / {n_days}영업일 수집 완료")
    return stocks


def _calc_extra(prices):
    last = prices[-1]

    recent_vols = [p["volume"] for p in prices[:-1] if p["volume"] > 0]
    if len(recent_vols) >= 5:
        avg_vol = sum(recent_vols[-20:]) / len(recent_vols[-20:])
        vol_ratio = round(last["volume"] / avg_vol, 1) if avg_vol > 0 else 0.0
    else:
        vol_ratio = 0.0

    if len(prices) >= 5:
        base_close = prices[-5]["close"]
        cum_pct = round((last["close"] - base_close) / base_close * 100, 1) if base_close > 0 else 0.0
    else:
        cum_pct = 0.0

    highs = [p["close"] for p in prices]
    is_52w_high = last["close"] >= max(highs) if highs else False
    high_pct = round((last["close"] - max(highs[:-1])) / max(highs[:-1]) * 100, 1) if len(highs) > 1 else 0.0

    return vol_ratio, cum_pct, is_52w_high, high_pct


def find_consecutive_surge(stocks, min_days=3, min_pct=10.0, window_days=22):
    result = []
    for code, info in stocks.items():
        prices  = info["prices"][-window_days:] if window_days else info["prices"]
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
            last_price = prices[-1]
            vol_ratio, cum_pct, is_52w_high, high_pct = _calc_extra(prices)
            result.append({
                "code":        code,
                "name":        info["name"],
                "market":      info["market"],
                "streaks":     streaks,
                "last_volume": last_price["volume"],
                "last_close":  last_price["close"],
                "last_chg":    last_price["chg_pct"],
                "vol_ratio":   vol_ratio,
                "cum_pct":     cum_pct,
                "is_52w_high": is_52w_high,
                "high_pct":    high_pct,
            })

    result.sort(key=lambda x: x["last_volume"], reverse=True)
    print(f"[분석] 연속 상승({window_days}일) {len(result)}개 발견")
    return result


def find_consecutive_decline(stocks, min_days=5, window_days=22):
    result = []
    for code, info in stocks.items():
        prices  = info["prices"][-window_days:] if window_days else info["prices"]
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
            last_price = prices[-1]
            vol_ratio, cum_pct, is_52w_high, high_pct = _calc_extra(prices)
            result.append({
                "code":        code,
                "name":        info["name"],
                "market":      info["market"],
                "streaks":     streaks,
                "last_volume": last_price["volume"],
                "last_close":  last_price["close"],
                "last_chg":    last_price["chg_pct"],
                "vol_ratio":   vol_ratio,
                "cum_pct":     cum_pct,
                "is_52w_high": is_52w_high,
                "high_pct":    high_pct,
            })

    result.sort(key=lambda x: x["last_volume"], reverse=True)
    print(f"[분석] 연속 하락({window_days}일) {len(result)}개 발견")
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
