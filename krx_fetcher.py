import requests
import os
from datetime import datetime, timedelta

KRX_API_KEY = os.environ.get("KRX_API_KEY", "")

# KRX Open API 공식 엔드포인트
API_BASE = "https://data-dbg.krx.co.kr/svc/apis/sto"
ENDPOINTS = {
    "KOSPI": {
        "daily": "/stk_bydd_trd",       # 유가증권 일별매매정보
        "info":  "/stk_isu_base_info",  # 유가증권 종목기본정보
    },
    "KOSDAQ": {
        "daily": "/ksq_bydd_trd",       # 코스닥 일별매매정보
        "info":  "/ksq_isu_base_info",  # 코스닥 종목기본정보
    },
}

def _post(endpoint, payload):
    """KRX Open API POST 공통 호출"""
    url = API_BASE + endpoint
    headers = {
        "AUTH_KEY":     KRX_API_KEY.strip(),
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }
    res = requests.post(url, headers=headers, json=payload, timeout=15)
    if res.status_code != 200:
        print(f"  [KRX] HTTP {res.status_code}: {res.text[:200]}")
        return {}
    return res.json()


def get_stock_market(stock_code):
    """종목코드가 KOSPI인지 KOSDAQ인지 판별 (기본정보 조회)"""
    today = datetime.today().strftime("%Y%m%d")

    # KOSPI 먼저 시도
    data = _post(ENDPOINTS["KOSPI"]["info"], {"basDd": today})
    for item in data.get("OutBlock_1", []):
        if item.get("ISU_SRT_CD", "") == stock_code:
            return "KOSPI"

    # KOSDAQ 시도
    data = _post(ENDPOINTS["KOSDAQ"]["info"], {"basDd": today})
    for item in data.get("OutBlock_1", []):
        if item.get("ISU_SRT_CD", "") == stock_code:
            return "KOSDAQ"

    return ""


def get_stock_code_from_name(corp_name):
    """기업명 → 종목코드 조회"""
    today = datetime.today().strftime("%Y%m%d")

    for market in ["KOSPI", "KOSDAQ"]:
        data = _post(ENDPOINTS[market]["info"], {"basDd": today})
        for item in data.get("OutBlock_1", []):
            name = item.get("ISU_ABBRV", "").strip()
            code = item.get("ISU_SRT_CD", "").strip()
            if name == corp_name and code:
                print(f"  [KRX] {corp_name} → {code} ({market})")
                return code, market

    print(f"  [KRX] {corp_name} 종목코드 없음")
    return "", ""


def get_10day_price(stock_code, market, corp_name=""):
    """최근 10영업일 주가 조회"""
    if not stock_code or not market:
        return []

    result = []
    end_dt   = datetime.today()
    start_dt = end_dt - timedelta(days=20)

    # 날짜 범위 내 영업일별로 조회
    current = start_dt
    daily_prices = []
    while current <= end_dt:
        date_str = current.strftime("%Y%m%d")
        data = _post(ENDPOINTS[market]["daily"], {"basDd": date_str})
        items = data.get("OutBlock_1", [])
        for item in items:
            if item.get("ISU_SRT_CD", "") == stock_code:
                try:
                    close   = int(item.get("TDD_CLSPRC", "0").replace(",", ""))
                    chg_pct = float(item.get("FLUC_RT", "0").replace(",", ""))
                    if close > 0:
                        daily_prices.append({
                            "date":       f"{date_str[4:6]}/{date_str[6:]}",
                            "close":      close,
                            "change_pct": chg_pct,
                        })
                except:
                    pass
                break
        current += timedelta(days=1)

    result = daily_prices[-10:]
    print(f"  [KRX] {corp_name}({stock_code}) 주가 {len(result)}건 수집")
    return result
