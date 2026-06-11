import os, json
from datetime import datetime
from dart_fetcher import fetch_all
from krx_fetcher import get_stock_code_from_name, get_10day_price
from krx_market  import get_market_data, find_consecutive_surge, find_consecutive_decline, get_top10_fluctuation
from config import DART_API_KEY

# ─── 유틸 ───────────────────────────────────────────────
def fmt_date(rcept_dt):
    return f"{rcept_dt[4:6]}/{rcept_dt[6:]}"

def fmt_krx_date(d):   # "20260611" → "06/11"
    return f"{d[4:6]}/{d[6:]}"

def dart_url(rcept_no):
    return f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

# ─── 미니 차트 (공시용) ──────────────────────────────────
def make_chart_html(corp_name, prices, chart_id, color):
    if not prices:
        return '<div class="no-chart">주가 데이터 없음</div>'
    labels    = json.dumps([p["date"] for p in prices], ensure_ascii=False)
    values    = json.dumps([p["close"] for p in prices])
    last      = prices[-1]
    chg       = last["change_pct"]
    chg_color = "#3B6D11" if chg >= 0 else "#A32D2D"
    chg_sign  = "+" if chg >= 0 else ""
    return f"""
    <div class="chart-wrap">
      <div class="chart-header">
        <span class="chart-corp">{corp_name}&nbsp;
          <span style="font-weight:400;color:#888">{last['close']:,}원</span></span>
        <span class="chart-chg" style="color:{chg_color}">{chg_sign}{chg:.1f}%</span>
      </div>
      <canvas id="{chart_id}" height="70"></canvas>
    </div>
    <script>(function(){{
      new Chart(document.getElementById('{chart_id}').getContext('2d'),{{
        type:'line',
        data:{{labels:{labels},datasets:[{{data:{values},borderColor:'{color}',borderWidth:1.5,
          pointRadius:2.5,pointBackgroundColor:'{color}',fill:true,
          backgroundColor:'{color}18',tension:0.3}}]}},
        options:{{responsive:true,plugins:{{legend:{{display:false}},
          tooltip:{{callbacks:{{label:function(c){{return c.parsed.y.toLocaleString()+'원';}} }} }} }},
          scales:{{x:{{grid:{{display:false}},ticks:{{font:{{size:10}},color:'#aaa'}}}},
            y:{{grid:{{color:'#f5f5f5'}},ticks:{{font:{{size:10}},color:'#aaa',
              callback:function(v){{return v.toLocaleString();}} }} }} }} }} }});
    }})();</script>"""

# ─── 공시 섹션 ───────────────────────────────────────────
def disc_rows_with_chart(items, badge_class, badge_text, color):
    if not items:
        return "<div class='empty'>해당 공시 없음</div>"
    rows = ""
    for i, d in enumerate(items):
        url        = dart_url(d['rcept_no'])
        chart_id   = f"chart_{badge_text}_{i}"
        code, mkt  = get_stock_code_from_name(d['corp_name'])
        prices     = get_10day_price(code, mkt, d['corp_name']) if code else []
        rows += f"""
        <div class="disc-card">
          <div class="disc-row">
            <span class="pill {badge_class}">{badge_text}</span>
            <a class="disc-name" href="{url}" target="_blank" rel="noopener">
              {d['report_nm']} <i class="link-icon">↗</i></a>
            <span class="disc-corp">{d['corp_name']}</span>
            <span class="disc-date">{fmt_date(d['rcept_dt'])}</span>
          </div>
          {make_chart_html(d['corp_name'], prices, chart_id, color)}
        </div>"""
    return rows

# ─── ① 연속 상승 섹션 ────────────────────────────────────
def surge_section(surge_list):
    if not surge_list:
        return "<div class='empty'>해당 종목 없음</div>"
    rows = ""
    for s in surge_list[:10]:
        streaks_html = ""
        for si, streak in enumerate(s["streaks"]):
            days_label = f"{streak['days']}일 연속"
            date_range = f"{fmt_krx_date(streak['start'])} – {fmt_krx_date(streak['end'])}"
            day_rows = ""
            for di in range(streak["days"]):
                pct   = streak["pcts"][di]
                close = streak["closes"][di]
                date  = fmt_krx_date(streak["dates"][di])
                day_rows += f"""
                <div class="day-row">
                  <span class="dot-up"></span>
                  <span class="day-label">{date}</span>
                  <span class="pct-up">+{pct:.1f}%</span>
                  <span class="price">{close:,}원</span>
                </div>"""
            if si > 0:
                streaks_html += '<div class="gap-row"><div class="gap-line"></div><div class="gap-text">조정 구간</div><div class="gap-line"></div></div>'
            streaks_html += f"""
            <div class="streak-grid">
              <div class="days-col">{day_rows}</div>
              <div class="label-col">
                <div class="streak-label-up">{si+1}구간<br>{date_range}<br>{days_label}</div>
              </div>
            </div>"""

        pill_html = " ".join([f'<span class="pill pill-up">{si+1}구간 {s["streaks"][si]["days"]}일</span>'
                               for si in range(len(s["streaks"]))])
        vol_fmt = f"{s['last_volume']//100000000:,}억" if s['last_volume'] >= 100000000 else f"{s['last_volume']:,}"
        rows += f"""
        <div class="card">
          <div class="stock-header">
            <div><span class="stock-name">{s['name']}</span>
                 <span class="stock-code">{s['code']}</span></div>
            <div style="display:flex;gap:5px;align-items:center">{pill_html}</div>
          </div>
          <div class="meta-row">
            <span class="vol-text">거래대금 {vol_fmt}</span>
          </div>
          <div class="divider"></div>
          {streaks_html}
        </div>"""
    return rows

# ─── ② 연속 하락 섹션 ────────────────────────────────────
def decline_section(decline_list):
    if not decline_list:
        return "<div class='empty'>해당 종목 없음</div>"
    rows = ""
    for s in decline_list[:10]:
        streaks_html = ""
        for si, streak in enumerate(s["streaks"]):
            days_label = f"{streak['days']}일 연속 하락"
            date_range = f"{fmt_krx_date(streak['start'])} – {fmt_krx_date(streak['end'])}"
            day_rows = ""
            for di in range(streak["days"]):
                pct   = streak["pcts"][di]
                close = streak["closes"][di]
                date  = fmt_krx_date(streak["dates"][di])
                day_rows += f"""
                <div class="day-row">
                  <span class="dot-down"></span>
                  <span class="day-label">{date}</span>
                  <span class="pct-down">{pct:.1f}%</span>
                  <span class="price">{close:,}원</span>
                </div>"""
            if si > 0:
                streaks_html += '<div class="gap-row"><div class="gap-line"></div><div class="gap-text">반등 구간</div><div class="gap-line"></div></div>'
            streaks_html += f"""
            <div class="streak-grid">
              <div class="days-col">{day_rows}</div>
              <div class="label-col">
                <div class="streak-label-down">{si+1}구간<br>{date_range}<br>{days_label}</div>
              </div>
            </div>"""

        pill_html = " ".join([f'<span class="pill pill-down">{si+1}구간 {s["streaks"][si]["days"]}일</span>'
                               for si in range(len(s["streaks"]))])
        vol_fmt = f"{s['last_volume']//100000000:,}억" if s['last_volume'] >= 100000000 else f"{s['last_volume']:,}"
        rows += f"""
        <div class="card">
          <div class="stock-header">
            <div><span class="stock-name">{s['name']}</span>
                 <span class="stock-code">{s['code']}</span></div>
            <div style="display:flex;gap:5px;align-items:center">{pill_html}</div>
          </div>
          <div class="meta-row">
            <span class="vol-text">거래대금 {vol_fmt}</span>
          </div>
          <div class="divider"></div>
          {streaks_html}
        </div>"""
    return rows

# ─── ③ TOP10 섹션 ────────────────────────────────────────
def top10_section(top_up, top_down):
    def rows(items, pct_class):
        html = ""
        for i, d in enumerate(items):
            sign = "+" if d["chg_pct"] > 0 else ""
            vol  = f"{d['volume']//100000000:,}억" if d['volume'] >= 100000000 else f"{d['volume']:,}"
            html += f"""
            <div class="top10-row">
              <span class="rank">{i+1}</span>
              <span class="t-name">{d['name']}</span>
              <span class="{pct_class}">{sign}{d['chg_pct']:.1f}%</span>
              <span class="t-vol">{vol}</span>
            </div>"""
        return html

    return f"""
    <div class="top10-grid">
      <div class="card" style="margin-bottom:0">
        <div style="font-size:12px;font-weight:500;color:#3B6D11;margin-bottom:8px">▲ 상승 TOP 10</div>
        <div class="col-head"><span></span><span>종목</span>
          <span style="text-align:right">등락률</span><span style="text-align:right">거래대금</span></div>
        {rows(top_up, 'pct-up')}
      </div>
      <div class="card" style="margin-bottom:0">
        <div style="font-size:12px;font-weight:500;color:#A32D2D;margin-bottom:8px">▼ 하락 TOP 10</div>
        <div class="col-head"><span></span><span>종목</span>
          <span style="text-align:right">등락률</span><span style="text-align:right">거래대금</span></div>
        {rows(top_down, 'pct-down')}
      </div>
    </div>"""

# ─── 메인 빌드 ───────────────────────────────────────────
def build():
    today     = datetime.today()
    today_str = today.strftime("%Y년 %m월 %d일")
    time_str  = today.strftime("%H:%M")

    print("=== 전체 시장 데이터 수집 시작 ===")
    stocks = get_market_data(n_days=20)

    print("=== 분석 시작 ===")
    surge_list   = find_consecutive_surge(stocks, min_days=3, min_pct=10.0)
    decline_list = find_consecutive_decline(stocks, min_days=5)
    top_up, top_down = get_top10_fluctuation(stocks)

    print("=== 공시 데이터 수집 ===")
    disc          = fetch_all(days=1)
    warn_html     = disc_rows_with_chart(disc["warn"],     "pill-warn", "희석위험", "#E24B4A")
    good_html     = disc_rows_with_chart(disc["good"],     "pill-safe", "긍정공시", "#639922")
    earnings_html = disc_rows_with_chart(disc["earnings"], "pill-info", "잠정실적", "#185FA5")

    surge_html   = surge_section(surge_list)
    decline_html = decline_section(decline_list)
    top10_html   = top10_section(top_up, top_down)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>국내주식 일일 리포트 — {today_str}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
        background:#f5f5f3;color:#1a1a1a;padding:24px 16px;}}
  .wrap{{max-width:960px;margin:0 auto;}}
  .report-header{{margin-bottom:24px;padding-bottom:16px;border-bottom:0.5px solid #e0e0e0;}}
  .report-title{{font-size:20px;font-weight:500;margin-bottom:4px;}}
  .report-meta{{font-size:13px;color:#888;}}
  .section{{margin-bottom:28px;}}
  .s-label{{font-size:11px;font-weight:500;color:#888;letter-spacing:.05em;
            text-transform:uppercase;margin-bottom:10px;}}
  .card{{background:#fff;border:0.5px solid #e5e5e5;border-radius:12px;
         padding:14px 18px;margin-bottom:10px;}}
  .stock-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;}}
  .stock-name{{font-size:14px;font-weight:500;}}
  .stock-code{{font-size:11px;color:#888;margin-left:5px;}}
  .meta-row{{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap;}}
  .vol-text{{font-size:11px;color:#888;}}
  .divider{{border:none;border-top:0.5px solid #f0f0f0;margin:8px 0;}}
  .streak-grid{{display:grid;grid-template-columns:1fr auto;gap:0 16px;align-items:start;}}
  .days-col{{min-width:0;}}
  .label-col{{display:flex;flex-direction:column;}}
  .streak-label-up{{font-size:11px;font-weight:500;color:#27500A;background:#EAF3DE;
    padding:5px 10px;white-space:nowrap;border-left:2px solid #639922;line-height:1.4;}}
  .streak-label-down{{font-size:11px;font-weight:500;color:#791F1F;background:#FCEBEB;
    padding:5px 10px;white-space:nowrap;border-left:2px solid #E24B4A;line-height:1.4;}}
  .gap-row{{grid-column:1/-1;display:flex;align-items:center;gap:8px;margin:6px 0;}}
  .gap-line{{flex:1;border-top:0.5px dashed #e0e0e0;}}
  .gap-text{{font-size:11px;color:#aaa;white-space:nowrap;}}
  .day-row{{display:flex;align-items:center;gap:6px;padding:3px 0;font-size:12px;}}
  .day-label{{color:#888;min-width:52px;}}
  .pct-up{{color:#3B6D11;font-weight:500;min-width:48px;}}
  .pct-down{{color:#A32D2D;font-weight:500;min-width:48px;}}
  .price{{font-size:11px;color:#888;}}
  .dot-up{{width:6px;height:6px;border-radius:50%;background:#639922;flex-shrink:0;}}
  .dot-down{{width:6px;height:6px;border-radius:50%;background:#E24B4A;flex-shrink:0;}}
  .pill{{display:inline-block;font-size:11px;padding:2px 8px;border-radius:99px;font-weight:500;white-space:nowrap;}}
  .pill-up{{background:#EAF3DE;color:#3B6D11;}}
  .pill-down{{background:#FCEBEB;color:#A32D2D;}}
  .pill-warn{{background:#FCEBEB;color:#791F1F;}}
  .pill-safe{{background:#EAF3DE;color:#27500A;}}
  .pill-info{{background:#E6F1FB;color:#0C447C;}}
  .top10-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;}}
  .col-head{{display:grid;grid-template-columns:18px 1fr 50px 58px;gap:4px;
             padding:0 0 6px;border-bottom:0.5px solid #e5e5e5;margin-bottom:4px;
             font-size:11px;color:#888;}}
  .top10-row{{display:grid;grid-template-columns:18px 1fr 50px 58px;gap:4px;
              align-items:center;padding:5px 0;border-bottom:0.5px solid #f5f5f5;font-size:12px;}}
  .top10-row:last-child{{border-bottom:none;}}
  .rank{{font-size:11px;color:#aaa;}}
  .t-name{{color:#1a1a1a;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
  .t-vol{{font-size:11px;color:#888;text-align:right;}}
  .disc-card{{border-bottom:0.5px solid #f0f0f0;padding:10px 0;}}
  .disc-card:last-child{{border-bottom:none;padding-bottom:0;}}
  .disc-row{{display:grid;grid-template-columns:68px minmax(0,1fr) 90px 44px;
             gap:6px;align-items:center;margin-bottom:8px;}}
  a.disc-name{{color:#1a1a1a;text-decoration:none;font-size:13px;line-height:1.4;
               display:flex;align-items:center;gap:4px;}}
  a.disc-name:hover{{color:#185FA5;}}
  a.disc-name:hover .link-icon{{opacity:1;}}
  .link-icon{{font-style:normal;font-size:11px;color:#185FA5;opacity:0;transition:opacity .15s;flex-shrink:0;}}
  .disc-corp{{color:#888;text-align:right;font-size:12px;}}
  .disc-date{{color:#aaa;text-align:right;font-size:12px;}}
  .chart-wrap{{background:#fafafa;border-radius:8px;padding:10px 12px;}}
  .chart-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;}}
  .chart-corp{{font-size:12px;font-weight:500;color:#555;}}
  .chart-chg{{font-size:12px;font-weight:500;}}
  .no-chart{{font-size:12px;color:#bbb;padding:8px 0;text-align:center;background:#fafafa;border-radius:8px;}}
  .sub-head{{font-size:13px;font-weight:500;margin-bottom:12px;}}
  .two-col{{display:grid;grid-template-columns:1fr 1fr;gap:10px;}}
  .empty{{font-size:13px;color:#bbb;padding:6px 0;}}
  .footer{{font-size:11px;color:#ccc;text-align:center;margin-top:40px;padding-top:16px;
           border-top:0.5px solid #e0e0e0;}}
  @media(max-width:640px){{
    .two-col,.top10-grid{{grid-template-columns:1fr;}}
    .disc-corp,.disc-date{{display:none;}}
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
    <div class="s-label">① 3영업일 이상 연속 10% 상승 종목</div>
    {surge_html}
  </div>

  <div class="section">
    <div class="s-label">② 5영업일 이상 연속 하락 종목</div>
    {decline_html}
  </div>

  <div class="section">
    <div class="s-label">③ 전일 상승 / 하락 TOP 10</div>
    {top10_html}
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

  <div class="footer">DART + KRX Open API 기반 자동 생성 &nbsp;|&nbsp; ziny0511.github.io/stock-report</div>
</div>
</body>
</html>"""

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[완료] docs/index.html 생성 — {today_str} {time_str}")

if __name__ == "__main__":
    build()
