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
            print(f"  [KRX] HTTP {res.status_code} ({endpoint} {base_date}): {res.text[:200]}")
            return []
        data  = res.json()
        items = data.get("OutBlock_1", [])
        # 첫 번째 항목 키/값 샘플 출력 (디버그)
        if items and endpoint.endswith("_trd"):
            sample = items[0]
            print(f"  [KRX DEBUG] {base_date} 첫번째 항목: {dict(list(sample.items())[:6])}")
        return items
    except Exception as e:
        print(f"  [KRX] 오류 ({endpoint} {base_date}): {e}")
        return []

def _last_biz_dates(n=15):
    dates = []
    dt = datetime.today() - timedelta(days=1)
    while len(dates) < n:
        if dt.weekday() < 5:
            dates.append(dt.strftime("%Y%m%d"))
        dt -= timedelta(days=1)
    return dates

def get_stock_code_from_name(corp_name):
    for days_ago in range(1, 6):
        dt = datetime.today() - timedelta(days=days_ago)
        if dt.weekday() >= 5:
            continue
        base_date = dt.strftime("%Y%m%d")
        for market in ["KOSPI", "KOSDAQ"]:
            items = _get(ENDPOINTS[market]["info"], base_date)
            for item in items:
                name = item.get("ISU_ABBRV", "").strip()
                code = item.get("ISU_SRT_CD", "").strip()
                if name == corp_name and code:
                    print(f"  [KRX] {corp_name} → {code} ({market})")
                    return code, market
        if items:
            break
    print(f"  [KRX] {corp_name} 종목코드 없음")
    return "", ""

def get_10day_price(stock_code, market, corp_name=""):
    if not stock_code or not market:
        return []

    biz_dates = _last_biz_dates(15)
    result    = []

    for base_date in biz_dates:
        items = _get(ENDPOINTS[market]["daily"], base_date)
        matched = False
        for item in items:
            code = item.get("ISU_SRT_CD", "").strip()
            # 첫 번째 종목의 코드 출력 (디버그)
            if not matched and items:
                print(f"  [KRX DEBUG] {base_date} 종목코드 샘플: {items[0].get('ISU_SRT_CD','?')} (찾는코드:{stock_code})")
            if code == stock_code:
                try:
                    close   = int(item.get("TDD_CLSPRC", "0").replace(",", ""))
                    chg_pct = float(item.get("FLUC_RT",   "0").replace(",", ""))
                    if close > 0:
                        result.append({
                            "date":       f"{base_date[4:6]}/{base_date[6:]}",
                            "close":      close,
                            "change_pct": chg_pct,
                        })
                        matched = True
                except Exception as e:
                    print(f"  [KRX] 파싱 오류: {e} / {item}")
                break
        if len(result) >= 10:
            break

    result = list(reversed(result[:10]))
    print(f"  [KRX] {corp_name}({stock_code}) 주가 {len(result)}건")
    return result
