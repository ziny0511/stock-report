import schedule
import time
import os
import webbrowser
from datetime import datetime
from dart_fetcher import fetch_all
from config import REPORT_OUTPUT_DIR, REPORT_TIME


def build_html(disc):
    """공시 데이터를 HTML 리포트로 변환"""
    today = datetime.today().strftime("%Y년 %m월 %d일")

    def row(item, badge_class, badge_text):
        dt = item["rcept_dt"]
        date_str = f"{dt[4:6]}/{dt[6:]}"
        return f"""
        <div class="disc-row">
          <span class="pill {badge_class}">{badge_text}</span>
          <span class="disc-name">{item['report_nm']}</span>
          <span class="disc-corp">{item['corp_name']}</span>
          <span class="disc-date">{date_str}</span>
        </div>"""

    warn_rows     = "".join(row(d, "pill-warn", "희석위험") for d in disc["warn"])     or "<div class='empty'>해당 없음</div>"
    good_rows     = "".join(row(d, "pill-safe", "긍정공시") for d in disc["good"])     or "<div class='empty'>해당 없음</div>"
    earn_rows     = "".join(row(d, "pill-info", "잠정실적") for d in disc["earnings"]) or "<div class='empty'>해당 없음</div>"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>주식 리포트 {today}</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; }}
  h1 {{ font-size: 20px; font-weight: 500; margin-bottom: 4px; }}
  .meta {{ font-size: 13px; color: #888; margin-bottom: 28px; }}
  h2 {{ font-size: 13px; font-weight: 500; color: #888; letter-spacing: 0.05em; text-transform: uppercase; margin: 24px 0 10px; }}
  .card {{ border: 0.5px solid #e5e5e5; border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; }}
  .disc-row {{ display: grid; grid-template-columns: 72px 1fr 100px 50px; gap: 8px; align-items: center; padding: 6px 0; border-bottom: 0.5px solid #f0f0f0; font-size: 13px; }}
  .disc-row:last-child {{ border-bottom: none; }}
  .disc-name {{ color: #1a1a1a; }}
  .disc-corp {{ color: #888; text-align: right; font-size: 12px; }}
  .disc-date {{ color: #aaa; text-align: right; font-size: 12px; }}
  .pill {{ display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 99px; font-weight: 500; }}
  .pill-warn {{ background: #FCEBEB; color: #791F1F; }}
  .pill-safe {{ background: #EAF3DE; color: #27500A; }}
  .pill-info {{ background: #E6F1FB; color: #0C447C; }}
  .empty {{ font-size: 13px; color: #bbb; padding: 6px 0; }}
  .footer {{ font-size: 11px; color: #ccc; text-align: center; margin-top: 40px; }}
</style>
</head>
<body>
  <h1>국내주식 일일 리포트</h1>
  <div class="meta">생성: {today} {datetime.now().strftime('%H:%M')} &nbsp;|&nbsp; KOSPI + KOSDAQ</div>

  <h2>주가 희석 위험 공시</h2>
  <div class="card">{warn_rows}</div>

  <h2>긍정적 공시 (자사주·수주·대형계약)</h2>
  <div class="card">{good_rows}</div>

  <h2>잠정실적 공시</h2>
  <div class="card">{earn_rows}</div>

  <div class="footer">DART Open API 기반 자동 생성 리포트</div>
</body>
</html>"""


def run_report():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 리포트 생성 시작...")
    disc = fetch_all(days=1)
    html = build_html(disc)

    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
    filename = datetime.today().strftime("%Y%m%d") + "_report.html"
    path = os.path.join(REPORT_OUTPUT_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    abs_path = os.path.abspath(path)
    print(f"리포트 저장: {abs_path}")
    webbrowser.open(f"file://{abs_path}")


schedule.every().day.at(REPORT_TIME).do(run_report)

if __name__ == "__main__":
    print(f"스케줄러 시작 — 매일 {REPORT_TIME} 자동 실행")
    run_report()       # 즉시 1회 실행
    while True:
        schedule.run_pending()
        time.sleep(30)
