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

# ── JSON 저장 ─────────────────────────────────────────────
def save_json(report_data, date_key):
    os.makedirs("docs/data", exist_ok=True)
    # 날짜별 데이터 저장
    with open(f"docs/data/{date_key}.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    # index.json 업데이트
    index_path = "docs/data/index.json"
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
    else:
        index = {"dates": []}
    if date_key not in index["dates"]:
        index["dates"].insert(0, date_key)
        index["dates"] = sorted(index["dates"], reverse=True)[:90]  # 최근 90일치 유지
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
    print(f"[완료] docs/data/{date_key}.json 저장 ({len(index['dates'])}개 날짜)")

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

# ── ① 연속 상승 컬럼 ────────────────────────────────────────
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

# ── ② 연속 하락 컬럼 ────────────────────────────────────────
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

# ── ③ TOP10 컬럼 ────────────────────────────────────────────
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

# ── ④ 공시 섹션 ─────────────────────────────────────────────
def disc_card(items, badge_class, badge_text, color, title):
    if not items:
        return f'<div class="disc-card"><div class="disc-title" style="color:{color}">{title}</div><div class="empty">해당 공시 없음</div></div>'
    inner = ""
    for i, d in enumerate(items):
        url       = dart_url(d['rcept_no'])
        chart_id  = f"chart_{badge_text}_{i}"
        code, mkt = get_stock_code_from_name(d['corp_name'])
        prices    = get_10day_price(code, mkt, d['corp_name']) if code else []
        d['_prices'] = prices  # JSON 저장용
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

# ── 메인 빌드 ────────────────────────────────────────────────
def build():
    today     = datetime.today()
    today_str = today.strftime("%Y년 %m월 %d일")
    time_str  = today.strftime("%H:%M")
    date_key  = today.strftime("%Y-%m-%d")

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

    # ── JSON 데이터 저장 ───────────────────────────────────
    def safe_disc(items):
        result = []
        for d in items:
            result.append({
                "corp_name": d.get("corp_name",""),
                "report_nm": d.get("report_nm",""),
                "rcept_no":  d.get("rcept_no",""),
                "rcept_dt":  d.get("rcept_dt",""),
                "prices":    d.get("_prices", [])
            })
        return result

    report_data = {
        "date":         date_key,
        "date_str":     today_str,
        "time_str":     time_str,
        "surge_list":   surge_list,
        "decline_list": decline_list,
        "top_up":       top_up,
        "top_down":     top_down,
        "disc": {
            "warn":     safe_disc(disc["warn"]),
            "good":     safe_disc(disc["good"]),
            "earnings": safe_disc(disc["earnings"])
        }
    }
    save_json(report_data, date_key)

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
  .report-header{{margin-bottom:16px;padding-bottom:12px;border-bottom:0.5px solid #e0e0e0;
                  display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:8px;}}
  .report-title{{font-size:18px;font-weight:500;margin-bottom:3px;}}
  .report-meta{{font-size:12px;color:#888;}}
  .s-label{{font-size:11px;font-weight:500;color:#888;letter-spacing:.05em;
            text-transform:uppercase;margin-bottom:8px;}}

  /* 날짜 선택기 */
  .date-picker-wrap{{display:flex;align-items:center;gap:8px;}}
  .date-label{{font-size:11px;color:#aaa;}}
  #date-select{{font-size:12px;border:0.5px solid #ddd;border-radius:8px;
               padding:5px 10px;background:#fff;color:#1a1a1a;cursor:pointer;outline:none;}}
  #date-select:focus{{border-color:#185FA5;}}
  .today-btn{{font-size:11px;color:#185FA5;cursor:pointer;padding:5px 8px;
              border:0.5px solid #185FA5;border-radius:8px;background:#fff;}}
  .today-btn:hover{{background:#E6F1FB;}}
  #history-badge{{display:none;font-size:11px;background:#FFF3CD;color:#856404;
                  padding:4px 10px;border-radius:99px;margin-bottom:12px;}}

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
  .loading{{font-size:12px;color:#aaa;padding:20px;text-align:center;}}
  .footer{{font-size:11px;color:#ccc;text-align:center;margin-top:24px;
           padding-top:12px;border-top:0.5px solid #e0e0e0;}}

  @media(max-width:900px){{
    .three-col,.disc-grid{{grid-template-columns:1fr;}}
    .report-header{{flex-direction:column;align-items:flex-start;}}
  }}
</style>
</head>
<body>
<div class="wrap">
  <div class="report-header">
    <div>
      <div class="report-title">국내주식 일일 리포트</div>
      <div class="report-meta" id="report-meta">{today_str} {time_str} 기준 &nbsp;|&nbsp; KOSPI + KOSDAQ &nbsp;|&nbsp; DART + KRX 자동 수집</div>
    </div>
    <div class="date-picker-wrap">
      <span class="date-label">날짜 선택</span>
      <select id="date-select"><option value="{date_key}">{today_str}</option></select>
      <button class="today-btn" onclick="goToday()">오늘</button>
    </div>
  </div>

  <div id="history-badge">📅 과거 리포트 조회 중</div>

  <div id="main-content">
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
  </div>

  <div class="footer">DART + KRX Open API 기반 자동 생성 &nbsp;|&nbsp; ziny0511.github.io/stock-report</div>
</div>

<script>
const BASE = location.origin + '/stock-report';
const TODAY_KEY = '{date_key}';
let todayContent = document.getElementById('main-content').innerHTML;
let chartInstances = [];

// 날짜 목록 로드
async function loadDateIndex() {{
  try {{
    const r = await fetch(BASE + '/data/index.json?t=' + Date.now());
    const data = await r.json();
    const sel = document.getElementById('date-select');
    sel.innerHTML = '';
    data.dates.forEach(d => {{
      const opt = document.createElement('option');
      opt.value = d;
      opt.textContent = formatDateLabel(d);
      if (d === TODAY_KEY) opt.textContent += ' (오늘)';
      sel.appendChild(opt);
    }});
    sel.value = TODAY_KEY;
  }} catch(e) {{ console.log('index.json 없음, 오늘만 표시'); }}
}}

function formatDateLabel(d) {{
  const [y,m,day] = d.split('-');
  const days = ['일','월','화','수','목','금','토'];
  const dow = days[new Date(d).getDay()];
  return `${{y}}년 ${{m}}월 ${{day}}일(${{dow}})`;
}}

function destroyCharts() {{
  Chart.helpers && Chart.instances && Object.values(Chart.instances).forEach(c => c.destroy());
}}

async function loadDate(dateKey) {{
  if (dateKey === TODAY_KEY) {{
    goToday();
    return;
  }}
  const content = document.getElementById('main-content');
  const badge = document.getElementById('history-badge');
  content.innerHTML = '<div class="loading">불러오는 중...</div>';
  badge.style.display = 'block';
  try {{
    const r = await fetch(BASE + '/data/' + dateKey + '.json?t=' + Date.now());
    if (!r.ok) throw new Error('파일 없음');
    const d = await r.json();
    document.getElementById('report-meta').innerHTML =
      d.date_str + ' ' + d.time_str + ' 기준 &nbsp;|&nbsp; KOSPI + KOSDAQ &nbsp;|&nbsp; DART + KRX 자동 수집';
    content.innerHTML = renderData(d);
    // 차트 렌더링
    renderHistoryCharts(d);
  }} catch(e) {{
    content.innerHTML = '<div class="loading">해당 날짜 데이터를 불러올 수 없습니다.</div>';
  }}
}}

function goToday() {{
  destroyCharts();
  document.getElementById('main-content').innerHTML = todayContent;
  document.getElementById('history-badge').style.display = 'none';
  document.getElementById('date-select').value = TODAY_KEY;
  document.getElementById('report-meta').innerHTML =
    '{today_str} {time_str} 기준 &nbsp;|&nbsp; KOSPI + KOSDAQ &nbsp;|&nbsp; DART + KRX 자동 수집';
}}

function volFmt(v) {{
  if (v >= 100000000) return Math.floor(v/100000000).toLocaleString() + '억';
  if (v >= 10000) return Math.floor(v/10000).toLocaleString() + '만';
  return v.toLocaleString();
}}

function fmtKrx(d) {{
  if (!d) return '';
  const days = ['일','월','화','수','목','금','토'];
  try {{
    const dt = new Date(d.slice(0,4)+'-'+d.slice(4,6)+'-'+d.slice(6,8));
    return d.slice(4,6)+'/'+d.slice(6,8)+'('+days[dt.getDay()]+')';
  }} catch(e) {{ return d.slice(4,6)+'/'+d.slice(6,8); }}
}}

function renderSurge(list) {{
  if (!list || !list.length) return "<div class='empty'>해당 종목 없음</div>";
  return list.slice(0,8).map(s => {{
    const pills = s.streaks.map((sk,i) => `<span class="pill pill-up">${{i+1}}구간 ${{sk.days}}일</span>`).join(' ');
    let streaks = '';
    s.streaks.forEach((sk, si) => {{
      if (si > 0) streaks += '<div class="gap-row"><div class="gap-line"></div><div class="gap-text">조정 구간</div><div class="gap-line"></div></div>';
      streaks += `<div class="streak-head"><span class="streak-label-up">${{si+1}}구간 ${{fmtKrx(sk.start)}}–${{fmtKrx(sk.end)}}</span></div>`;
      for (let di=0; di<sk.days; di++) {{
        streaks += `<div class="day-row"><span class="dot-up"></span><span class="day-label">${{fmtKrx(sk.dates[di])}}</span><span class="pct-up">+${{sk.pcts[di].toFixed(1)}}%</span><span class="dprice">${{sk.closes[di].toLocaleString()}}원</span></div>`;
      }}
    }});
    const chgColor = s.last_chg >= 0 ? '#3B6D11' : '#A32D2D';
    const chgSign = s.last_chg >= 0 ? '+' : '';
    return `<div class="stock-item">
      <div class="stock-row"><div><a class="stock-link" href="https://finance.naver.com/item/main.naver?code=${{s.code}}" target="_blank"><span class="stock-name">${{s.name}}</span><span class="stock-code">${{s.code}}</span></a></div>
      <div style="display:flex;gap:3px;flex-wrap:wrap;justify-content:flex-end">${{pills}}</div></div>
      <div class="stock-row"><span class="stock-vol">거래대금 ${{volFmt(s.last_volume)}}</span><span class="stock-price">${{s.last_close.toLocaleString()}}원</span><span class="stock-chg" style="font-size:10px;font-weight:500;color:${{chgColor}}">${{chgSign}}${{s.last_chg.toFixed(1)}}%</span></div>
      <div class="streak-wrap">${{streaks}}</div></div>`;
  }}).join('');
}}

function renderDecline(list) {{
  if (!list || !list.length) return "<div class='empty'>해당 종목 없음</div>";
  return list.slice(0,8).map(s => {{
    const pills = s.streaks.map((sk,i) => `<span class="pill pill-down">${{i+1}}구간 ${{sk.days}}일</span>`).join(' ');
    let streaks = '';
    s.streaks.forEach((sk, si) => {{
      if (si > 0) streaks += '<div class="gap-row"><div class="gap-line"></div><div class="gap-text">반등 구간</div><div class="gap-line"></div></div>';
      streaks += `<div class="streak-head"><span class="streak-label-down">${{si+1}}구간 ${{fmtKrx(sk.start)}}–${{fmtKrx(sk.end)}}</span></div>`;
      for (let di=0; di<sk.days; di++) {{
        streaks += `<div class="day-row"><span class="dot-down"></span><span class="day-label">${{fmtKrx(sk.dates[di])}}</span><span class="pct-down">${{sk.pcts[di].toFixed(1)}}%</span><span class="dprice">${{sk.closes[di].toLocaleString()}}원</span></div>`;
      }}
    }});
    const chgColor = s.last_chg >= 0 ? '#3B6D11' : '#A32D2D';
    const chgSign = s.last_chg >= 0 ? '+' : '';
    return `<div class="stock-item">
      <div class="stock-row"><div><a class="stock-link" href="https://finance.naver.com/item/main.naver?code=${{s.code}}" target="_blank"><span class="stock-name">${{s.name}}</span><span class="stock-code">${{s.code}}</span></a></div>
      <div style="display:flex;gap:3px;flex-wrap:wrap;justify-content:flex-end">${{pills}}</div></div>
      <div class="stock-row"><span class="stock-vol">거래대금 ${{volFmt(s.last_volume)}}</span><span class="stock-price">${{s.last_close.toLocaleString()}}원</span><span class="stock-chg" style="font-size:10px;font-weight:500;color:${{chgColor}}">${{chgSign}}${{s.last_chg.toFixed(1)}}%</span></div>
      <div class="streak-wrap">${{streaks}}</div></div>`;
  }}).join('');
}}

function renderTop10(top_up, top_down) {{
  const rows = (items, cls) => items.map((d,i) => {{
    const sign = d.chg_pct > 0 ? '+' : '';
    return `<div class="t-row"><span class="t-rank">${{i+1}}</span><a class="stock-link t-name" href="https://finance.naver.com/item/main.naver?code=${{d.code}}" target="_blank">${{d.name}}</a><span class="${{cls}}">${{sign}}${{d.chg_pct.toFixed(1)}}%</span><span class="t-price">${{d.close.toLocaleString()}}원</span></div>`;
  }}).join('');
  return `<div class="top10-block"><div class="top10-head" style="color:#3B6D11">▲ 상승 TOP 10</div>
    <div class="t-col-head"><span></span><span>종목</span><span style="text-align:right">등락</span><span style="text-align:right">종가</span></div>${{rows(top_up,'t-pct-up')}}</div>
    <div style="border-top:0.5px solid #f0f0f0;margin:8px 0;"></div>
    <div class="top10-block"><div class="top10-head" style="color:#A32D2D">▼ 하락 TOP 10</div>
    <div class="t-col-head"><span></span><span>종목</span><span style="text-align:right">등락</span><span style="text-align:right">종가</span></div>${{rows(top_down,'t-pct-down')}}</div>`;
}}

function renderDiscCard(items, badgeClass, badgeText, color, title, dateKey) {{
  if (!items || !items.length) return `<div class="disc-card"><div class="disc-title" style="color:${{color}}">${{title}}</div><div class="empty">해당 공시 없음</div></div>`;
  const inner = items.map((d,i) => {{
    const url = `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${{d.rcept_no}}`;
    const dateStr = d.rcept_dt ? d.rcept_dt.slice(4,6)+'/'+d.rcept_dt.slice(6,8) : '';
    const chartId = `hchart_${{dateKey}}_${{badgeText}}_${{i}}`;
    const chartHtml = (d.prices && d.prices.length) ?
      `<div class="chart-wrap"><div class="chart-header"><span class="chart-corp">${{d.corp_name}}&nbsp;<span style="font-weight:400;color:#888">${{d.prices[d.prices.length-1].close.toLocaleString()}}원</span></span></div><canvas id="${{chartId}}" height="60"></canvas></div>` :
      '<div class="chart-ph">주가 데이터 없음</div>';
    return `<div class="disc-item" data-chart-id="${{chartId}}" data-prices='${{JSON.stringify(d.prices||[])}}' data-color="${{color}}">
      <div class="disc-row">
        <span class="pill ${{badgeClass}}">${{badgeText}}</span>
        <a class="disc-name" href="${{url}}" target="_blank">${{d.report_nm}} <i class="li">↗</i></a>
        <span class="disc-corp">${{d.corp_name}}</span>
        <span class="disc-date">${{dateStr}}</span>
      </div>${{chartHtml}}</div>`;
  }}).join('');
  return `<div class="disc-card"><div class="disc-title" style="color:${{color}}">${{title}}</div>${{inner}}</div>`;
}}

function renderHistoryCharts(d) {{
  document.querySelectorAll('[data-chart-id]').forEach(el => {{
    const chartId = el.getAttribute('data-chart-id');
    const prices = JSON.parse(el.getAttribute('data-prices') || '[]');
    const color = el.getAttribute('data-color');
    if (!prices.length) return;
    const canvas = document.getElementById(chartId);
    if (!canvas) return;
    new Chart(canvas.getContext('2d'), {{
      type: 'line',
      data: {{
        labels: prices.map(p => p.date),
        datasets: [{{ data: prices.map(p => p.close), borderColor: color, borderWidth: 1.5,
          pointRadius: 2, pointBackgroundColor: color, fill: true,
          backgroundColor: color + '18', tension: 0.3 }}]
      }},
      options: {{ responsive: true, plugins: {{ legend: {{ display: false }},
        tooltip: {{ callbacks: {{ label: c => c.parsed.y.toLocaleString() + '원' }} }} }},
        scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 9 }}, color: '#aaa' }} }},
          y: {{ grid: {{ color: '#f5f5f5' }}, ticks: {{ font: {{ size: 9 }}, color: '#aaa',
            callback: v => v.toLocaleString() }} }} }} }}
    }});
  }});
}}

function renderData(d) {{
  return `
    <div class="three-col">
      <div class="col-panel"><div class="col-title" style="color:#3B6D11"><i>▲</i> ① 3영업일 이상 연속 10% 상승</div>${{renderSurge(d.surge_list)}}</div>
      <div class="col-panel"><div class="col-title" style="color:#A32D2D"><i>▼</i> ② 5영업일 이상 연속 하락</div>${{renderDecline(d.decline_list)}}</div>
      <div class="col-panel"><div class="col-title" style="color:#1a1a1a">③ 전일 상승 / 하락 TOP 10</div>${{renderTop10(d.top_up, d.top_down)}}</div>
    </div>
    <div class="disc-section">
      <div class="s-label">④ 전일 주요 공시 — 최근 10영업일 주가 포함</div>
      <div class="disc-grid">
        ${{renderDiscCard(d.disc.warn,     'pill-warn', '희석위험', '#E24B4A', '⚠ 희석 위험 공시',     d.date)}}
        ${{renderDiscCard(d.disc.good,     'pill-safe', '긍정공시', '#639922', '👍 긍정적 공시',        d.date)}}
        ${{renderDiscCard(d.disc.earnings, 'pill-info', '잠정실적', '#185FA5', '📊 잠정실적 공시',      d.date)}}
      </div>
    </div>`;
}}

document.getElementById('date-select').addEventListener('change', e => loadDate(e.target.value));
loadDateIndex();
</script>
</body>
</html>"""

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[완료] docs/index.html 생성 — {today_str} {time_str}")

if __name__ == "__main__":
    build()
