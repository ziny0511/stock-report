import requests
import os
from datetime import datetime, timedelta

KRX_API_KEY = os.environ.get("KRX_API_KEY", "")
API_BASE = "https://data-dbg.krx.co.kr/svc/apis/sto"

ENDPOINTS = {
    "KOSPI":  { "daily": "/stk_bydd_trd", "info": "/stk_isu_base_info" },
    "KOSDAQ": { "daily": "/ksq_bydd_trd", "info": "/ksq_isu_base_info" },
}

def _get(endpoint, base_date):
    url     = API_BASE + endpoint
    headers = {
        "AUTH_KEY":     KRX_API_KEY.strip(),
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }
    try:
        res = requests.get(url, headers=headers, params={"basDd": base_date}, timeout=20)
        if res.status_code != 200:
            print(f"  [KRX] HTTP {res.status_code} ({endpoint} {base_date})")
            return []
        return res.json().get("OutBlock_1", [])
    except Exception as e:
        print(f"  [KRX] 오류 ({endpoint}): {e}")
        return []

def _last_biz_dates(n=15):
    """최근 n개 영업일 날짜 리스트 반환 (최신순)"""
    dates = []
    dt = datetime.today() - timedelta(days=1)
    while len(dates) < n:
        if dt.weekday() < 5:  # 평일만
            dates.append(dt.strftime("%Y%m%d"))
        dt -= timedelta(days=1)
    return dates

def get_stock_code_from_name(corp_name):
    """기업명 → 종목코드 + 시장"""
    # 종목기본정보는 최근 영업일 1개만 조회해도 충분
    for days_ago in range(1, 6):
        dt = datetime.today() - timedelta(days=days_ago)
        if dt.weekday() >= 5:
            continue
        base_date = dt.strftime("%Y%m%d")

        for market in ["KOSPI", "KOSDAQ"]:
            items = _get(ENDPOINTS[market]["info"], base_date)
            if not items:
                continue
            for item in items:
                name = item.get("ISU_ABBRV", "").strip()
                code = item.get("ISU_SRT_CD", "").strip()
                if name == corp_name and code:
                    print(f"  [KRX] {corp_name} → {code} ({market})")
                    return code, market
        # KOSPI+KOSDAQ 모두 데이터 있으면 충분
        if items:
            break

    print(f"  [KRX] {corp_name} 종목코드 없음")
    return "", ""

def get_10day_price(stock_code, market, corp_name=""):
    """
    최근 10영업일 주가 — 날짜별 루프 대신
    15영업일치 날짜를 한꺼번에 조회해서 필터링
    """
    if not stock_code or not market:
        return []

    biz_dates = _last_biz_dates(15)   # 최신순 15일
    result    = []

    for base_date in biz_dates:
        items = _get(ENDPOINTS[market]["daily"], base_date)
        for item in items:
            if item.get("ISU_SRT_CD", "").strip() != stock_code:
                continue
            try:
                close   = int(item.get("TDD_CLSPRC", "0").replace(",", ""))
                chg_pct = float(item.get("FLUC_RT",   "0").replace(",", ""))
                if close > 0:
                    result.append({
                        "date":       f"{base_date[4:6]}/{base_date[6:]}",
                        "close":      close,
                        "change_pct": chg_pct,
                    })
            except:
                pass
            break
        if len(result) >= 10:
            break

    result = list(reversed(result[:10]))   # 오래된 순으로 정렬
    print(f"  [KRX] {corp_name}({stock_code}) 주가 {len(result)}건")
    return result
