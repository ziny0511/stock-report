import os, json
from datetime import datetime
from dart_fetcher import fetch_all
from krx_fetcher import get_stock_code_from_name, get_10day_price
from krx_market  import get_market_data, find_consecutive_surge, find_consecutive_decline, get_top10_fluctuation
from config import DART_API_KEY

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]

def fmt_date(rcept_dt):
    return f"{rcept_dt[4:6]}/{rcept_dt[6:]}"

def fmt_krx(d):
    """20260616 → 06/16(월)"""
    from datetime import datetime
    try:
        dt  = datetime.strptime(d, "%Y%m%d")
        day = WEEKDAY_KR[dt.weekday()]
        return f"{d[4:6]}/{d[6:]}({day})"
    except:
        return f"{d[4:6]}/{d[6:]}"

def naver_stock_url(code):
    return f"https://finance.naver.com/item/main.naver?code={code}"

def dart_url(rcept_no):
    return f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

def vol_fmt(v):
    if v >= 100000000:
        return f"{v//100000000:,}억"
    elif v >= 10000:
        return f"{v//10000:,}만"
    return f"{v:,}"

# ── 미니 차트 (공시용) ──────────────────────────────────
def make_chart_html(corp_name, prices, chart_id, color):
    if not prices:
        return '<div class="chart-ph">주가 데이터 없음</div>'
    labels    = json.dumps([p["date"] for p in prices], ensure_ascii=False)
    values    = json.dumps([p["close"] for p in prices])
    last      = prices[-1]
    chg       = last["change_pct"]
    chg_color = "#3B6D11" if chg >= 0 else "#A32D2D"
    chg_sign  = "+" if chg >= 0 else ""
    return f"""
    <div class="chart-wrap">
      <div class="chart-header">
        <span class="chart-corp">{corp_name}&nbsp;<span style="font-weight:400;color:#888">{last['close']:,}원</span></span>
        <span style="font-size:11px;font-weight:500;color:{chg_color}">{chg_sign}{chg:.1f}%</span>
      </div>
      <canvas id="{chart_id}" height="60"></canvas>
    </div>
    <script>(function(){{
      new Chart(document.getElementById('{chart_id}').getContext('2d'),{{
        type:'line',
        data:{{labels:{labels},datasets:[{{data:{values},borderColor:'{color}',borderWidth:1.5,
          pointRadius:2,pointBackgroundColor:'{color}',fill:true,
          backgroundColor:'{color}18',tension:0.3}}]}},
        options:{{responsive:true,plugins:{{legend:{{display:false}},
          tooltip:{{callbacks:{{label:function(c){{return c.parsed.y.toLocaleString()+'원';}}}}}}  }},
          scales:{{x:{{grid:{{display:false}},ticks:{{font:{{size:9}},color:'#aaa'}}}},
            y:{{grid:{{color:'#f5f5f5'}},ticks:{{font:{{size:9}},color:'#aaa',
              callback:function(v){{return v.toLocaleString();}}}}}}}}}}
      }});
    }})();</script>"""

# ── ① 연속 상승 컬럼 ────────────────────────────────────
def col_surge(surge_list):
    if not surge_list:
        return "<div class='empty'>해당 종목 없음</div>"
    html = ""
    for s in surge_list[:8]:
        last_close = s.get("last_close", 0)
        last_chg   = s.get("last_chg", 0)
        pills = " ".join([f'<span class="pill pill-up">{i+1}구간 {sk["days"]}일</span>'
                          for i, sk in enumerate(s["streaks"])])
        streaks_html = ""
        for si, sk in enumerate(s["streaks"]):
            if si > 0:
                streaks_html += '<div class="gap-row"><div class="gap-line"></div><div class="gap-text">조정 구간</div><div class="gap-line"></div></div>'
            streaks_html += f'<div class="streak-head"><span class="streak-label-up">{si+1}구간 {fmt_krx(sk["start"])}–{fmt_krx(sk["end"])}</span></div>'
            for di in range(sk["days"]):
                streaks_html += f"""<div class="day-row">
                  <span class="dot-up"></span>
                  <span class="day-label">{fmt_krx(sk["dates"][di])}</span>
                  <span class="pct-up">+{sk["pcts"][di]:.1f}%</span>
                  <span class="dprice">{sk["closes"][di]:,}원</span>
                </div>"""
        html += f"""
        <div class="stock-item">
          <div class="stock-row">
            <div>
              <a class="stock-link" href="{naver_stock_url(s['code'])}" target="_blank" rel="noopener">
                <span class="stock-name">{s['name']}</span><span class="stock-code">{s['code']}</span>
              </a>
            </div>
            <div style="display:flex;gap:3px;flex-wrap:wrap;justify-content:flex-end">{pills}</div>
          </div>
          <div class="stock-row">
            <span class="stock-vol">거래대금 {vol_fmt(s['last_volume'])}</span>
            <span class="stock-price">{last_close:,}원</span>
            <span class="stock-chg" style="font-size:10px;font-weight:500;color:{"#3B6D11" if last_chg>=0 else "#A32D2D"}">{("+" if last_chg>=0 else "")}{last_chg:.1f}%</span>
          </div>
          <div class="streak-wrap">{streaks_html}</div>
        </div>"""
    return html

# ── ② 연속 하락 컬럼 ────────────────────────────────────
def col_decline(decline_list):
    if not decline_list:
        return "<div class='empty'>해당 종목 없음</div>"
    html = ""
    for s in decline_list[:8]:
        last_close = s.get("last_close", 0)
        last_chg   = s.get("last_chg", 0)
        pills = " ".join([f'<span class="pill pill-down">{i+1}구간 {sk["days"]}일</span>'
                          for i, sk in enumerate(s["streaks"])])
        streaks_html = ""
        for si, sk in enumerate(s["streaks"]):
            if si > 0:
                streaks_html += '<div class="gap-row"><div class="gap-line"></div><div class="gap-text">반등 구간</div><div class="gap-line"></div></div>'
            streaks_html += f'<div class="streak-head"><span class="streak-label-down">{si+1}구간 {fmt_krx(sk["start"])}–{fmt_krx(sk["end"])}</span></div>'
            for di in range(sk["days"]):
                streaks_html += f"""<div class="day-row">
                  <span class="dot-down"></span>
                  <span class="day-label">{fmt_krx(sk["dates"][di])}</span>
                  <span class="pct-down">{sk["pcts"][di]:.1f}%</span>
                  <span class="dprice">{sk["closes"][di]:,}원</span>
                </div>"""
        html += f"""
        <div class="stock-item">
          <div class="stock-row">
            <div>
              <a class="stock-link" href="{naver_stock_url(s['code'])}" target="_blank" rel="noopener">
                <span class="stock-name">{s['name']}</span><span class="stock-code">{s['code']}</span>
              </a>
            </div>
            <div style="display:flex;gap:3px;flex-wrap:wrap;justify-content:flex-end">{pills}</div>
          </div>
          <div class="stock-row">
            <span class="stock-vol">거래대금 {vol_fmt(s['last_volume'])}</span>
            <span class="stock-price">{last_close:,}원</span>
            <span class="stock-chg" style="font-size:10px;font-weight:500;color:{"#3B6D11" if last_chg>=0 else "#A32D2D"}">{("+" if last_chg>=0 else "")}{last_chg:.1f}%</span>
          </div>
          <div class="streak-wrap">{streaks_html}</div>
        </div>"""
    return html

# ── ③ TOP10 컬럼 ────────────────────────────────────────
def col_top10(top_up, top_down):
    def rows(items, pct_class):
        h = ""
        for i, d in enumerate(items):
            sign = "+" if d["chg_pct"] > 0 else ""
            h += f"""<div class="t-row">
              <span class="t-rank">{i+1}</span>
              <a class="stock-link t-name" href="{naver_stock_url(d['code'])}" target="_blank" rel="noopener">{d['name']}</a>
              <span class="{pct_class}">{sign}{d['chg_pct']:.1f}%</span>
              <span class="t-price">{d['close']:,}원</span>
            </div>"""
        return h
    return f"""
    <div class="top10-block">
      <div class="top10-head" style="color:#3B6D11">▲ 상승 TOP 10</div>
      <div class="t-col-head"><span></span><span>종목</span><span style="text-align:right">등락</span><span style="text-align:right">종가</span></div>
      {rows(top_up, 't-pct-up')}
    </div>
    <div style="border-top:0.5px solid #f0f0f0;margin:8px 0;"></div>
    <div class="top10-block">
      <div class="top10-head" style="color:#A32D2D">▼ 하락 TOP 10</div>
      <div class="t-col-head"><span></span><span>종목</span><span style="text-align:right">등락</span><span style="text-align:right">종가</span></div>
      {rows(top_down, 't-pct-down')}
    </div>"""

# ── ④ 공시 섹션 (하단 풀와이드 3열) ────────────────────
def disc_card(items, badge_class, badge_text, color, title):
    if not items:
        return f'<div class="disc-card"><div class="disc-title" style="color:{color}">{title}</div><div class="empty">해당 공시 없음</div></div>'
    inner = ""
    for i, d in enumerate(items):
        url       = dart_url(d['rcept_no'])
        chart_id  = f"chart_{badge_text}_{i}"
        code, mkt = get_stock_code_from_name(d['corp_name'])
        prices    = get_10day_price(code, mkt, d['corp_name']) if code else []
        inner += f"""
        <div class="disc-item">
          <div class="disc-row">
            <span class="pill {badge_class}">{badge_text}</span>
            <a class="disc-name" href="{url}" target="_blank" rel="noopener">
              {d['report_nm']} <i class="li">↗</i></a>
            <span class="disc-corp">{d['corp_name']}</span>
            <span class="disc-date">{fmt_date(d['rcept_dt'])}</span>
          </div>
          {make_chart_html(d['corp_name'], prices, chart_id, color)}
        </div>"""
    return f'<div class="disc-card"><div class="disc-title" style="color:{color}">{title}</div>{inner}</div>'

# ── 메인 빌드 ────────────────────────────────────────────
def build():
    today     = datetime.today()
    today_str = today.strftime("%Y년 %m월 %d일")
    time_str  = today.strftime("%H:%M")

    print("=== 시장 데이터 수집 ===")
    stocks = get_market_data(n_days=20)

    print("=== 분석 ===")
    surge_list       = find_consecutive_surge(stocks, min_days=3, min_pct=10.0)
    decline_list     = find_consecutive_decline(stocks, min_days=5)
    top_up, top_down = get_top10_fluctuation(stocks)

    print("=== 공시 수집 ===")
    disc = fetch_all(days=1)

    surge_html   = col_surge(surge_list)
    decline_html = col_decline(decline_list)
    top10_html   = col_top10(top_up, top_down)
    warn_card    = disc_card(disc["warn"],     "pill-warn", "희석위험", "#E24B4A", "⚠ 희석 위험 공시")
    good_card    = disc_card(disc["good"],     "pill-safe", "긍정공시", "#639922", "👍 긍정적 공시")
    earn_card    = disc_card(disc["earnings"], "pill-info", "잠정실적", "#185FA5", "📊 잠정실적 공시")

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
        background:#f5f5f3;color:#1a1a1a;padding:20px 16px;}}
  .wrap{{max-width:1200px;margin:0 auto;}}
  .report-header{{margin-bottom:16px;padding-bottom:12px;border-bottom:0.5px solid #e0e0e0;}}
  .report-title{{font-size:18px;font-weight:500;margin-bottom:3px;}}
  .report-meta{{font-size:12px;color:#888;}}
  .s-label{{font-size:11px;font-weight:500;color:#888;letter-spacing:.05em;
            text-transform:uppercase;margin-bottom:8px;}}

  /* 3분할 */
  .three-col{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;
              margin-bottom:20px;align-items:start;}}
  .col-panel{{background:#fff;border:0.5px solid #e5e5e5;border-radius:12px;padding:12px 14px;}}
  .col-title{{font-size:12px;font-weight:500;margin-bottom:10px;padding-bottom:8px;
              border-bottom:0.5px solid #f0f0f0;}}

  /* 종목 아이템 */
  .stock-item{{border-bottom:0.5px solid #f5f5f5;padding:8px 0;}}
  .stock-item:last-child{{border-bottom:none;padding-bottom:0;}}
  .stock-row{{display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;}}
  .stock-name{{font-size:12px;font-weight:500;color:#1a1a1a;}}
  .stock-code{{font-size:10px;color:#aaa;margin-left:3px;}}
  .stock-link{{text-decoration:none;color:inherit;}}
  .stock-link:hover .stock-name{{color:#185FA5;text-decoration:underline;}}
  .stock-link:hover{{color:#185FA5;}}
  .stock-price{{font-size:11px;font-weight:500;color:#1a1a1a;}}
  .stock-vol{{font-size:10px;color:#888;}}
  .streak-wrap{{margin-top:4px;}}
  .streak-head{{margin-bottom:3px;}}
  .streak-label-up{{font-size:10px;font-weight:500;color:#27500A;background:#EAF3DE;
    padding:2px 6px;border-left:2px solid #639922;display:inline-block;}}
  .streak-label-down{{font-size:10px;font-weight:500;color:#791F1F;background:#FCEBEB;
    padding:2px 6px;border-left:2px solid #E24B4A;display:inline-block;}}
  .gap-row{{display:flex;align-items:center;gap:5px;margin:3px 0;}}
  .gap-line{{flex:1;border-top:0.5px dashed #e0e0e0;}}
  .gap-text{{font-size:9px;color:#aaa;white-space:nowrap;}}
  .day-row{{display:flex;align-items:center;gap:4px;padding:1px 0;font-size:10px;}}
  .day-label{{color:#888;min-width:58px;}}
  .pct-up{{color:#3B6D11;font-weight:500;min-width:40px;}}
  .pct-down{{color:#A32D2D;font-weight:500;min-width:40px;}}
  .dprice{{font-size:10px;color:#aaa;}}
  .dot-up{{width:4px;height:4px;border-radius:50%;background:#639922;flex-shrink:0;}}
  .dot-down{{width:4px;height:4px;border-radius:50%;background:#E24B4A;flex-shrink:0;}}

  /* TOP10 */
  .top10-block{{margin-bottom:8px;}}
  .top10-head{{font-size:11px;font-weight:500;margin-bottom:5px;}}
  .t-col-head{{display:grid;grid-template-columns:14px 1fr 38px 58px;gap:3px;
               padding:0 0 4px;border-bottom:0.5px solid #e5e5e5;margin-bottom:2px;
               font-size:9px;color:#aaa;}}
  .t-row{{display:grid;grid-template-columns:14px 1fr 38px 58px;gap:3px;
          align-items:center;padding:3px 0;border-bottom:0.5px solid #f5f5f5;font-size:10px;}}
  .t-row:last-child{{border-bottom:none;}}
  .t-rank{{color:#aaa;}}
  .t-name{{color:#1a1a1a;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
  .t-pct-up{{color:#3B6D11;font-weight:500;text-align:right;}}
  .t-pct-down{{color:#A32D2D;font-weight:500;text-align:right;}}
  .t-price{{color:#1a1a1a;font-weight:500;text-align:right;}}

  /* 공시 */
  .disc-section{{border-top:0.5px solid #e0e0e0;padding-top:16px;}}
  .disc-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;}}
  .disc-card{{background:#fff;border:0.5px solid #e5e5e5;border-radius:12px;padding:12px 14px;}}
  .disc-title{{font-size:12px;font-weight:500;margin-bottom:10px;}}
  .disc-item{{border-bottom:0.5px solid #f5f5f5;padding:8px 0;}}
  .disc-item:last-child{{border-bottom:none;padding-bottom:0;}}
  .disc-row{{display:grid;grid-template-columns:52px minmax(0,1fr) 64px 32px;
             gap:4px;align-items:center;margin-bottom:6px;}}
  a.disc-name{{color:#1a1a1a;text-decoration:none;font-size:11px;line-height:1.4;
               display:flex;align-items:center;gap:3px;}}
  a.disc-name:hover{{color:#185FA5;}}
  a.disc-name:hover .li{{opacity:1;}}
  .li{{font-style:normal;font-size:10px;color:#185FA5;opacity:0;transition:opacity .15s;}}
  .disc-corp{{color:#888;text-align:right;font-size:10px;}}
  .disc-date{{color:#aaa;text-align:right;font-size:10px;}}
  .chart-wrap{{background:#fafafa;border-radius:8px;padding:8px 10px;}}
  .chart-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;}}
  .chart-corp{{font-size:11px;font-weight:500;color:#555;}}
  .chart-ph{{background:#fafafa;border-radius:8px;height:50px;display:flex;
             align-items:center;justify-content:center;font-size:10px;color:#bbb;}}

  /* 공통 */
  .pill{{display:inline-block;font-size:10px;padding:1px 6px;border-radius:99px;font-weight:500;white-space:nowrap;}}
  .pill-up{{background:#EAF3DE;color:#3B6D11;}}
  .pill-down{{background:#FCEBEB;color:#A32D2D;}}
  .pill-warn{{background:#FCEBEB;color:#791F1F;}}
  .pill-safe{{background:#EAF3DE;color:#27500A;}}
  .pill-info{{background:#E6F1FB;color:#0C447C;}}
  .empty{{font-size:12px;color:#bbb;padding:6px 0;}}
  .footer{{font-size:11px;color:#ccc;text-align:center;margin-top:24px;
           padding-top:12px;border-top:0.5px solid #e0e0e0;}}

  @media(max-width:900px){{
    .three-col,.disc-grid{{grid-template-columns:1fr;}}
  }}
</style>
</head>
<body>
<div class="wrap">
  <div class="report-header">
    <div class="report-title">국내주식 일일 리포트</div>
    <div class="report-meta">{today_str} {time_str} 기준 &nbsp;|&nbsp; KOSPI + KOSDAQ &nbsp;|&nbsp; DART + KRX 자동 수집</div>
  </div>

  <div class="three-col">
    <div class="col-panel">
      <div class="col-title" style="color:#3B6D11">
        <i>▲</i> ① 3영업일 이상 연속 10% 상승
      </div>
      {surge_html}
    </div>
    <div class="col-panel">
      <div class="col-title" style="color:#A32D2D">
        <i>▼</i> ② 5영업일 이상 연속 하락
      </div>
      {decline_html}
    </div>
    <div class="col-panel">
      <div class="col-title" style="color:#1a1a1a">
        ③ 전일 상승 / 하락 TOP 10
      </div>
      {top10_html}
    </div>
  </div>

  <div class="disc-section">
    <div class="s-label">④ 전일 주요 공시 — 최근 10영업일 주가 포함</div>
    <div class="disc-grid">
      {warn_card}
      {good_card}
      {earn_card}
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
