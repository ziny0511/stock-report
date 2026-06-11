import requests
import os
from datetime import datetime, timedelta

KRX_API_KEY = os.environ.get("KRX_API_KEY", "")
BASE = "https://openapi.krx.co.kr/contents/OPP/USES/service/OPPUSES002_S2.cmd"

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "AUTH_KEY": KRX_API_KEY,
}

def get_stock_code_from_name(corp_name):
    """기업명 → 종목코드 (KRX Open API 종목 검색)"""
    try:
        url = "https://openapi.krx.co.kr/contents/OPP/USES/service/OPPUSES002_S2.cmd"
        data = {
            "bld":        "dbms/comm/finder/finder_stkisu",
            "mktsel":     "ALL",
            "searchText": corp_name,
        }
        headers = {"AUTH_KEY": KRX_API_KEY, "Content-Type": "application/x-www-form-urlencoded"}
        res   = requests.post(url, headers=headers, data=data, timeout=10)
        items = res.json().get("block1", [])
        for item in items:
            name = item.get("isu_abbrv", "").strip()
            code = item.get("short_code", "").strip()
            if name == corp_name and code:
                print(f"  [KRX] {corp_name} → {code}")
                return code
        # 완전 일치 없으면 첫 번째 결과 사용
        if items:
            code = items[0].get("short_code", "").strip()
            name = items[0].get("isu_abbrv", "").strip()
            print(f"  [KRX] {corp_name} → {code} ({name}, 유사검색)")
            return code
    except Exception as e:
        print(f"  [KRX] 종목코드 조회 실패 ({corp_name}): {e}")
    return ""


def get_isin(stock_code):
    """종목코드 → ISIN 코드"""
    try:
        url = "https://openapi.krx.co.kr/contents/OPP/USES/service/OPPUSES002_S2.cmd"
        data = {
            "bld":        "dbms/comm/finder/finder_stkisu",
            "mktsel":     "ALL",
            "searchText": stock_code,
        }
        headers = {"AUTH_KEY": KRX_API_KEY, "Content-Type": "application/x-www-form-urlencoded"}
        res   = requests.post(url, headers=headers, data=data, timeout=10)
        items = res.json().get("block1", [])
        for item in items:
            if item.get("short_code", "").strip() == stock_code:
                return item.get("isu_cd", "").strip()
    except Exception as e:
        print(f"  [KRX] ISIN 조회 실패 ({stock_code}): {e}")
    return ""


def get_10day_price(stock_code, corp_name=""):
    """최근 10영업일 주가 조회 (KRX Open API)"""
    try:
        isin = get_isin(stock_code)
        if not isin:
            print(f"  [KRX] ISIN 없음 ({stock_code})")
            return []

        end_dt   = datetime.today()
        start_dt = end_dt - timedelta(days=30)
        url  = "https://openapi.krx.co.kr/contents/OPP/USES/service/OPPUSES002_S2.cmd"
        data = {
            "bld":             "dbms/MDC/STAT/standard/MDCSTAT01701",
            "isuCd":           isin,
            "strtDd":          start_dt.strftime("%Y%m%d"),
            "endDd":           end_dt.strftime("%Y%m%d"),
            "adjStkPrc_check": "Y",
            "adjStkPrc":       "2",
        }
        headers = {"AUTH_KEY": KRX_API_KEY, "Content-Type": "application/x-www-form-urlencoded"}
        res   = requests.post(url, headers=headers, data=data, timeout=10)
        items = res.json().get("output", [])

        if not items:
            print(f"  [KRX] 주가 데이터 없음 ({stock_code})")
            return []

        result = []
        for item in sorted(items, key=lambda x: x["TRD_DD"])[-10:]:
            date_raw = item["TRD_DD"].replace("/", "")
            close    = int(item["TDD_CLSPRC"].replace(",", ""))
            chg_pct  = float(item["FLUC_RT"].replace(",", ""))
            result.append({
                "date":       f"{date_raw[4:6]}/{date_raw[6:]}",
                "close":      close,
                "change_pct": chg_pct,
            })

        print(f"  [KRX] {corp_name}({stock_code}) 주가 {len(result)}건 수집 완료")
        return result

    except Exception as e:
        print(f"  [KRX] 주가 조회 실패 ({stock_code}): {e}")
        return []
