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
        items = res.json().get("OutBlock_1", [])
        # 첫 번째 항목 전체 키 출력 (1회만)
        if items and not hasattr(_get, '_printed'):
            print(f"  [KRX DEBUG] 전체 키: {list(items[0].keys())}")
            print(f"  [KRX DEBUG] 샘플값: {dict(list(items[0].items())[:8])}")
            _get._printed = True
        return items
    except Exception as e:
        print(f"  [KRX] 오류: {e}")
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
                # ISU_ABBRV(약명) 또는 ISU_NM(정식명) 으로 매칭
                name1 = item.get("ISU_ABBRV", "").strip()
                name2 = item.get("ISU_NM", "").strip()
                # 단축코드(ISU_SRT_CD) 없으면 ISU_CD 앞 6자리 사용
                code  = (item.get("ISU_SRT_CD") or item.get("ISU_CD", "")[:6]).strip()
                if (name1 == corp_name or name2 == corp_name) and code:
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
        for item in items:
            # 일별매매정보의 종목코드 필드: ISU_SRT_CD 또는 ISU_CD 앞 6자리
            code = (item.get("ISU_SRT_CD") or item.get("ISU_CD", "")[:6]).strip()
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
                except Exception as e:
                    print(f"  [KRX] 파싱 오류: {e}")
                break
        if len(result) >= 10:
            break

    result = list(reversed(result[:10]))
    print(f"  [KRX] {corp_name}({stock_code}) 주가 {len(result)}건")
    return result
