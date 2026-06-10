import requests
from datetime import datetime, timedelta

def get_10day_price(stock_code):
    """
    네이버 금융 API로 최근 10영업일 주가 조회 (로그인 불필요)
    """
    try:
        url = "https://api.finance.naver.com/siseJson.naver"
        params = {
            "symbol": stock_code,
            "requestType": "1",
            "startTime": (datetime.today() - timedelta(days=30)).strftime("%Y%m%d"),
            "endTime": datetime.today().strftime("%Y%m%d"),
            "timeframe": "day",
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://finance.naver.com/",
        }
        res = requests.get(url, params=params, headers=headers, timeout=10)
        raw = res.text.strip()

        # 응답 파싱 (CSV 형태)
        lines = [l.strip() for l in raw.replace("'", "").split("\n") if l.strip()]
        result = []
        for line in lines[1:]:  # 첫 줄은 헤더
            parts = line.split(",")
            if len(parts) < 5:
                continue
            date_str = parts[0].strip().replace("'", "")
            close    = parts[4].strip().replace("'", "")
            open_p   = parts[1].strip().replace("'", "")
            if not close or not date_str or len(date_str) < 8:
                continue
            close_int = int(close)
            open_int  = int(open_p) if open_p else close_int
            chg_pct   = round((close_int - open_int) / open_int * 100, 2) if open_int else 0
            result.append({
                "date":       f"{date_str[4:6]}/{date_str[6:8]}",
                "close":      close_int,
                "change_pct": chg_pct,
            })

        return result[-10:] if len(result) >= 10 else result
    except Exception as e:
        print(f"[Naver] 주가 조회 실패 ({stock_code}): {e}")
        return []


def get_stock_code_from_dart(corp_name, dart_api_key):
    """DART API로 기업명 → 종목코드 조회"""
    try:
        url = "https://opendart.fss.or.kr/api/list.json"
        params = {
            "crtfc_key": dart_api_key,
            "corp_name":  corp_name,
            "page_no":    "1",
            "page_count": "5",
        }
        res  = requests.get(url, params=params, timeout=10)
        data = res.json()
        items = data.get("list", [])
        for item in items:
            code = item.get("stock_code", "").strip()
            name = item.get("corp_name", "").strip()
            if name == corp_name and code:
                print(f"  [DART] {corp_name} → {code}")
                return code
    except Exception as e:
        print(f"  [DART] 종목코드 조회 실패 ({corp_name}): {e}")

    # DART 실패 시 네이버 검색으로 폴백
    return get_stock_code_from_naver(corp_name)


def get_stock_code_from_naver(corp_name):
    """네이버 금융 검색으로 종목코드 조회"""
    try:
        url = "https://ac.finance.naver.com/ac"
        params = {
            "q": corp_name,
            "q_enc": "UTF-8",
            "st": "111",
            "frm": "stock",
            "res_format": "json",
        }
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}
        res  = requests.get(url, params=params, headers=headers, timeout=10)
        data = res.json()
        items = data.get("items", [[]])
        for group in items:
            for item in group:
                name = item[0] if len(item) > 0 else ""
                code = item[1] if len(item) > 1 else ""
                if name == corp_name and code:
                    print(f"  [Naver] {corp_name} → {code}")
                    return code
    except Exception as e:
        print(f"  [Naver] 종목코드 검색 실패 ({corp_name}): {e}")
    return ""
