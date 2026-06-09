import os
from datetime import datetime
from dart_fetcher import fetch_all

def fmt_date(rcept_dt):
    return f"{rcept_dt[4:6]}/{rcept_dt[6:]}"

def dart_url(rcept_no):
    return f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

def disc_rows(items, badge_class, badge_text):
    if not items:
        return "<div class='empty'>해당 공시 없음</div>"
    rows = ""
    for d in items:
        url = dart_url(d['rcept_no'])
        rows += f"""
        <div class="disc-row">
          <span class="pill {badge_class}">{badge_text}</span>
          <a class="disc-name" href="{url}" target="_blank" rel="noopener">
            {d['report_nm']}
            <i class="link-icon">↗</i>
          </a>
          <span class="disc-corp">{d['corp_name']}</span>
          <span class="disc-date">{fmt_date(d['rcept_dt'])}</span>
        </div>"""
    return rows

def build():
    today     = datetime.today()
    today_str = today.strftime("%Y년 %m월 %d일")
    time_str  = today.strftime("%H:%M")

    disc = fetch_all(days=1)
    warn_html     = disc_rows(disc["warn"],     "pill-warn", "희석위험")
    good_html     = disc_rows(disc["good"],     "pill-safe", "긍정공시")
    earnings_html = disc_rows(disc["earnings"], "pill-info", "잠정실적")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>국내주식 일일 리포트 — {today_str}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background: #f5f5f3; color: #1a1a1a; padding: 24px 16px; }}
  .wrap {{ max-width: 900px; margin: 0 auto; }}
  .report-header {{ margin-bottom: 24px; padding-bottom: 16px;
                    border-bottom: 0.5px solid #e0e0e0; }}
  .report-title {{ font-size: 20px; font-weight: 500; margin-bottom: 4px; }}
  .report-meta  {{ font-size: 13px; color: #888; }}
  .section {{ margin-bottom: 24px; }}
  .s-label {{ font-size: 11px; font-weight: 500; color: #888;
              letter-spacing: 0.05em; text-transform: uppercase;
              margin-bottom: 10px; }}
  .card {{ background: #fff; border: 0.5px solid #e5e5e5;
           border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; }}
  .sub-head {{ font-size: 13px; font-weight: 500; margin-bottom: 10px; }}
  .disc-row {{ display: grid;
               grid-template-columns: 68px minmax(0,1fr) 90px 44px;
               gap: 6px; align-items: center; padding: 7px 0;
               border-bottom: 0.5px solid #f0f0f0; }}
  .disc-row:last-of-type {{ border-bottom: none; }}
  a.disc-name {{
    color: #1a1a1a;
    text-decoration: none;
    font-size: 13px;
    line-height: 1.4;
    display: flex;
    align-items: center;
    gap: 4px;
    transition: color 0.15s;
  }}
  a.disc-name:hover {{ color: #185FA5; }}
  a.disc-name:hover .link-icon {{ opacity: 1; }}
  .link-icon {{
    font-style: normal;
    font-size: 11px;
    color: #185FA5;
    opacity: 0;
    transition: opacity 0.15s;
    flex-shrink: 0;
  }}
  .disc-corp {{ color: #888; text-align: right; font-size: 12px; }}
  .disc-date {{ color: #aaa; text-align: right; font-size: 12px; }}
  .pill {{ display: inline-block; font-size: 11px; padding: 2px 8px;
           border-radius: 99px; font-weight: 500; white-space: nowrap; }}
  .pill-warn {{ background: #FCEBEB; color: #791F1F; }}
  .pill-safe {{ background: #EAF3DE; color: #27500A; }}
  .pill-info {{ background: #E6F1FB; color: #0C447C; }}
  .empty {{ font-size: 13px; color: #bbb; padding: 6px 0; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .footer {{ font-size: 11px; color: #ccc; text-align: center;
             margin-top: 40px; padding-top: 16px;
             border-top: 0.5px solid #e0e0e0; }}
  @media (max-width: 600px) {{
    .two-col {{ grid-template-columns: 1fr; }}
    .disc-row {{ grid-template-columns: 60px 1fr 70px; }}
    .disc-date {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="wrap">

  <div class="report-header">
    <div class="report-title">국내주식 일일 리포트</div>
    <div class="report-meta">{today_str} {time_str} 기준 &nbsp;|&nbsp; KOSPI + KOSDAQ &nbsp;|&nbsp; DART 자동 수집</div>
  </div>

  <div class="section">
    <div class="s-label">④ 전일 주요 공시</div>
    <div class="two-col">
      <div class="card">
        <div class="sub-head" style="color:#791F1F">⚠ 희석 위험 공시</div>
        {warn_html}
      </div>
      <div class="card">
        <div class="sub-head" style="color:#27500A">👍 긍정적 공시</div>
        {good_html}
      </div>
    </div>
    <div class="card">
      <div class="sub-head" style="color:#0C447C">📊 잠정실적 공시</div>
      {earnings_html}
    </div>
  </div>

  <div class="footer">
    DART Open API 기반 자동 생성 &nbsp;|&nbsp; ziny0511.github.io/stock-report
  </div>
</div>
</body>
</html>"""

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[완료] docs/index.html 생성 — {today_str} {time_str}")

if __name__ == "__main__":
    build()
