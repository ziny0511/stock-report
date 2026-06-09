import requests
import json
from datetime import datetime, timedelta

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "http://data.krx.co.kr/",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}
BASE = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"


def get_isin(stock_code):
    """종목코드 → ISIN 코드 변환"""
    data = {
        "bld": "dbms/comm/finder/finder_stkisu",
        "mktsel": "ALL",
        "searchText": stock_code,
        "pagePath": "/contents/MDC/STAT/standard/MDCSTAT01901.jsp",
    }
    try:
        res = requests.post(BASE, headers=HEADERS, data=data, timeout=10)
        items = res.json().get("block1", [])
        for item in items:
            if item.get("short_code") == stock_code:
                return item.get("isu_cd", "")
    except Exception as e:
        print(f"[KRX] ISIN 조회 실패 ({stock_code}): {e}")
    return ""


def get_10day_price(stock_code):
    """
    종목코드로 최근 10영업일 주가 조회
    반환: [{"date": "06/01", "close": 82600, "change_pct": +3.2}, ...]
    """
    isin = get_isin(stock_code)
    if not isin:
        return []

    end_dt   = datetime.today()
    start_dt = end_dt - timedelta(days=20)  # 영업일 10일 확보를 위해 20일치 요청
    data = {
        "bld": "dbms/MDC/STAT/standard/MDCSTAT01701",
        "isuCd": isin,
        "strtDd": start_dt.strftime("%Y%m%d"),
        "endDd":  end_dt.strftime("%Y%m%d"),
        "adjStkPrc_check": "Y",
        "adjStkPrc": "2",
        "outputFileType": "json",
    }
    try:
        res = requests.post(BASE, headers=HEADERS, data=data, timeout=10)
        items = res.json().get("output", [])
        result = []
        for item in sorted(items, key=lambda x: x["TRD_DD"])[-10:]:
            date_str = item["TRD_DD"].replace("/", "")
            close    = int(item["TDD_CLSPRC"].replace(",", ""))
            chg_pct  = float(item["FLUC_RT"].replace(",", ""))
            result.append({
                "date":       f"{date_str[4:6]}/{date_str[6:]}",
                "close":      close,
                "change_pct": chg_pct,
            })
        return result
    except Exception as e:
        print(f"[KRX] 주가 조회 실패 ({stock_code}): {e}")
        return []


def get_corp_code_from_dart(corp_name, dart_api_key):
    """DART 기업명 → 종목코드 조회"""
    url = "https://opendart.fss.or.kr/api/company.json"
    params = {
        "crtfc_key": dart_api_key,
        "corp_name": corp_name,
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        items = res.json().get("list", [])
        for item in items:
            if item.get("corp_name") == corp_name and item.get("stock_code"):
                return item["stock_code"]
    except Exception as e:
        print(f"[DART] 종목코드 조회 실패 ({corp_name}): {e}")
    return ""
