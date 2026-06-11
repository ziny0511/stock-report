import requests
import os
from datetime import datetime, timedelta

KRX_API_KEY = os.environ.get("KRX_API_KEY", "")
API_BASE = "https://data-dbg.krx.co.kr/svc/apis/sto"

ENDPOINTS = {
    "KOSPI": {
        "daily": "/stk_bydd_trd",
        "info":  "/stk_isu_base_info",
    },
    "KOSDAQ": {
        "daily": "/ksq_bydd_trd",
        "info":  "/ksq_isu_base_info",
    },
}

def _get(endpoint, base_date):
    """KRX Open API GET 호출 — params 방식"""
    url = API_BASE + endpoint
    headers = {
        "AUTH_KEY": KRX_API_KEY.strip(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    params = {"basDd": base_date}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=15)
        if res.status_code != 200:
            print(f"  [KRX] {endpoint} {base_date} HTTP {res.status_code}")
            return []
        return res.json().get("OutBlock_1", [])
    except Exception as e:
        print(f"  [KRX] {endpoint} 오류: {e}")
        return []


def _last_biz_date(days_ago=1):
    """최근 영업일 반환 (주말 제외)"""
    dt = datetime.today() - timedelta(days=days_ago)
    while dt.weekday() >= 5:  # 토=5, 일=6
        dt -= timedelta(days=1)
    return dt.strftime("%Y%m%d")


def get_stock_code_from_name(corp_name):
    """기업명 → 종목코드 + 시장 구분"""
    base_date = _last_biz_date(1)

    for market in ["KOSPI", "KOSDAQ"]:
        items = _get(ENDPOINTS[market]["info"], base_date)
        for item in items:
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

    daily_prices = []
    days_ago = 1

    while len(daily_prices) < 10 and days_ago <= 30:
        base_date = _last_biz_date(days_ago)
        items = _get(ENDPOINTS[market]["daily"], base_date)

        for item in items:
            code = item.get("ISU_SRT_CD", "").strip()
            if code == stock_code:
                try:
                    close   = int(item.get("TDD_CLSPRC", "0").replace(",", ""))
                    chg_pct = float(item.get("FLUC_RT", "0").replace(",", ""))
                    if close > 0:
                        daily_prices.append({
                            "date":       f"{base_date[4:6]}/{base_date[6:]}",
                            "close":      close,
                            "change_pct": chg_pct,
                        })
                except:
                    pass
                break
        days_ago += 1

    result = list(reversed(daily_prices[:10]))
    print(f"  [KRX] {corp_name}({stock_code}) 주가 {len(result)}건")
    return result
