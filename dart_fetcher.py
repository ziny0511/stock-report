import requests
from datetime import datetime, timedelta
from config import DART_API_KEY

BASE = "https://opendart.fss.or.kr/api"

KEY_TYPES = {
    "유상증자결정":       "warn",
    "전환사채권발행결정":  "warn",
    "신주인수권부사채":    "warn",
    "자기주식취득결정":   "good",
    "단일판매공급계약":   "good",
    "잠정실적":          "earnings",
    "영업(잠정)실적":    "earnings",
}

def get_recent_disclosures(days=1, corp_cls="Y"):
    end   = datetime.today().strftime("%Y%m%d")
    start = (datetime.today() - timedelta(days=days)).strftime("%Y%m%d")
    params = {
        "crtfc_key":  DART_API_KEY,
        "bgn_de":     start,
        "end_de":     end,
        "corp_cls":   corp_cls,
        "page_no":    "1",
        "page_count": "100",
    }
    try:
        res = requests.get(f"{BASE}/list.json", params=params, timeout=10)
        data = res.json()
        if data.get("status") != "000":
            print(f"[DART] 오류: {data.get('message')}")
            return []
        return data.get("list", [])
    except Exception as e:
        print(f"[DART] 요청 실패: {e}")
        return []

def filter_key_disclosures(disc_list):
    warn, good, earnings = [], [], []
    for d in disc_list:
        report = d.get("report_nm", "")
        for keyword, impact in KEY_TYPES.items():
            if keyword in report:
                item = {
                    "corp_name": d["corp_name"],
                    "report_nm": report,
                    "rcept_dt":  d["rcept_dt"],
                    "impact":    impact,
                    "rcept_no":  d["rcept_no"],
                }
                if impact == "warn":     warn.append(item)
                elif impact == "good":   good.append(item)
                else:                    earnings.append(item)
                break
    return {"warn": warn, "good": good, "earnings": earnings}

def fetch_all(days=1):
    kospi  = get_recent_disclosures(days=days, corp_cls="Y")
    kosdaq = get_recent_disclosures(days=days, corp_cls="K")
    return filter_key_disclosures(kospi + kosdaq)
