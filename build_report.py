import os, json
from datetime import datetime
from dart_fetcher import fetch_all
from krx_fetcher import get_stock_code_from_name, get_10day_price
from config import DART_API_KEY

def fmt_date(rcept_dt):
    return f"{rcept_dt[4:6]}/{rcept_dt[6:]}"

def dart_url(rcept_no):
    return f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

def make_chart_html(corp_name, prices, chart_id, color):
    if not prices:
        return '<div class="no-chart">주가 데이터 없음</div>'

    labels    = json.dumps([p["date"] for p in prices], ensure_ascii=False)
    values    = json.dumps([p["close"] for p in prices])
    last      = prices[-1]
    chg       = last["change_pct"]
    chg_color = "#3B6D11" if chg >= 0 else "#A32D2D"
    chg_sign  = "+" if chg >= 0 else ""
    close_fmt = f"{last['close']:,}"

    return f"""
    <div class="chart-wrap">
      <div class="chart-header">
        <span class="chart-corp">{corp_name}&nbsp;
          <span style="font-weight:400;color:#888">{close_fmt}원</span>
        </span>
        <span class="chart-chg" style="color:{chg_color}">{chg_sign}{chg:.1f}%</span>
      </div>
      <canvas id="{chart_id}" height="70"></canvas>
    </div>
    <script>
    (function() {{
      var ctx = document.getElementById('{chart_id}').getContext('2d');
      new Chart(ctx, {{
        type: 'line',
        data: {{
          labels: {labels},
          datasets: [{{
            data: {values},
            borderColor: '{color}',
            borderWidth: 1.5,
            pointRadius: 2.5,
            pointBackgroundColor: '{color}',
            fill: true,
            backgroundColor: '{color}18',
            tension: 0.3,
          }}]
        }},
        options: {{
          responsive: true,
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{ callbacks: {{
              label: function(c) {{ return c.parsed.y.toLocaleString() + '원'; }}
            }} }}
          }},
          scales: {{
            x: {{ grid: {{ display: false }},
                  ticks: {{ font: {{ size: 10 }}, color: '#aaa' }} }},
            y: {{ grid: {{ color: '#f5f5f5' }},
                  ticks: {{ font: {{ size: 10 }}, color: '#aaa',
                    callback: function(v) {{ return v.toLocaleString(); }}
                  }} }}
          }}
        }}
      }});
    }})();
    </script>"""

def disc_rows_with_chart(items, badge_class, badge_text, color):
    if not items:
        return "<div class='empty'>해당 공시 없음</div>"
    rows = ""
    for i, d in enumerate(items):
        url        = dart_url(d['rcept_no'])
        chart_id   = f"chart_{badge_text}_{i}"
        code, market = get_stock_code_from_name(d['corp_name'])
        prices     = get_10day_price(code, market, d['corp_name']) if code else []
        chart_html = make_chart_html(d['corp_name'], prices, chart_id, color)
        rows += f"""
        <div class="disc-card">
          <div class="disc-row">
            <span class="pill {badge_class}">{badge_text}</span>
            <a class="disc-name" href="{url}" target="_blank" rel="noopener">
              {d['report_nm']} <i class="link-icon">↗</i>
            </a>
            <span class="disc-corp">{d['corp_name']}</span>
            <span class="disc-date">{fmt_date(d['rcept_dt'])}</span>
          </div>
          {chart_html}
        </div>"""
    return rows

def build():
    today     = datetime.today()
    today_str = today.strftime("%Y년 %m월 %d일")
    time_str  = today.strftime("%H:%M")

    disc          = fetch_all(days=1)
    warn_html     = disc_rows_with_chart(disc["warn"],     "pill-warn", "희석위험", "#E24B4A")
    good_html     = disc_rows_with_chart(disc["good"],     "pill-safe", "긍정공시", "#639922")
    earnings_html = disc_rows_with_chart(disc["earnings"], "pill-info", "잠정실적", "#185FA5")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>국내주식 일일 리포트 — {today_str}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background: #f5f5f3; color: #1a1a1a; padding: 24px 16px; }}
  .wrap {{ max-width: 960px; margin: 0 auto; }}
  .report-header {{ margin-bottom: 24px; padding-bottom: 16px;
                    border-bottom: 0.5px solid #e0e0e0; }}
  .report-title {{ font-size: 20px; font-weight: 500; margin-bottom: 4px; }}
  .report-meta  {{ font-size: 13px; color: #888; }}
  .section {{ margin-bottom: 24px; }}
  .s-label {{ font-size: 11px; font-weight: 500; color: #888;
              letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 10px; }}
  .card {{ background: #fff; border: 0.5px solid #e5e5e5;
           border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; }}
  .sub-head {{ font-size: 13px; font-weight: 500; margin-bottom: 12px; }}
  .disc-card {{ border-bottom: 0.5px solid #f0f0f0; padding: 10px 0; }}
  .disc-card:last-child {{ border-bottom: none; padding-bottom: 0; }}
  .disc-row {{ display: grid; grid-template-columns: 68px minmax(0,1fr) 90px 44px;
               gap: 6px; align-items: center; margin-bottom: 8px; }}
  a.disc-name {{ color: #1a1a1a; text-decoration: none; font-size: 13px;
                 line-height: 1.4; display: flex; align-items: center; gap: 4px; }}
  a.disc-name:hover {{ color: #185FA5; }}
  a.disc-name:hover .link-icon {{ opacity: 1; }}
  .link-icon {{ font-style: normal; font-size: 11px; color: #185FA5;
                opacity: 0; transition: opacity 0.15s; flex-shrink: 0; }}
  .disc-corp {{ color: #888; text-align: right; font-size: 12px; }}
  .disc-date {{ color: #aaa; text-align: right; font-size: 12px; }}
  .chart-wrap {{ background: #fafafa; border-radius: 8px; padding: 10px 12px; }}
  .chart-header {{ display: flex; justify-content: space-between;
                   align-items: center; margin-bottom: 6px; }}
  .chart-corp {{ font-size: 12px; font-weight: 500; color: #555; }}
  .chart-chg  {{ font-size: 12px; font-weight: 500; }}
  .no-chart {{ font-size: 12px; color: #bbb; padding: 8px 0;
               text-align: center; background: #fafafa; border-radius: 8px; }}
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
  @media (max-width: 640px) {{
    .two-col {{ grid-template-columns: 1fr; }}
    .disc-row {{ grid-template-columns: 60px 1fr; }}
    .disc-corp, .disc-date {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <div class="report-header">
    <div class="report-title">국내주식 일일 리포트</div>
    <div class="report-meta">{today_str} {time_str} 기준 &nbsp;|&nbsp; KOSPI + KOSDAQ &nbsp;|&nbsp; DART + KRX 자동 수집</div>
  </div>
  <div class="section">
    <div class="s-label">④ 전일 주요 공시 — 최근 10영업일 주가 포함</div>
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
    DART + KRX Open API 기반 자동 생성 &nbsp;|&nbsp; ziny0511.github.io/stock-report
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
