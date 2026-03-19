import streamlit as st
import requests
import re
import time
from datetime import datetime, timezone

st.set_page_config(page_title="IT PULSE", layout="wide")

# ── 자동 새로고침 (10초) ──────────────────────────────────────────────
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=10_000, limit=None, key="ticker_refresh")
except ImportError:
    st.warning("pip install streamlit-autorefresh 를 실행하면 10초 자동 새로고침이 활성화됩니다.")

# 🎨 스타일 + 화살표 애니메이션
st.markdown("""
<style>
.card { padding:12px; border-radius:10px; border:1px solid #2a2a2a; margin-bottom:10px; }
.title { font-size:14px; font-weight:500; }
.meta { font-size:11px; color:gray; }

/* 상승 - 빨강 + 위 화살표 bounce */
.up   { color:#ff4d4f; font-weight:bold; }
.up   .arrow { display:inline-block; animation: bounceUp 0.8s ease infinite; }

/* 하락 - 파랑 + 아래 화살표 bounce */
.down { color:#4da6ff; font-weight:bold; }
.down .arrow { display:inline-block; animation: bounceDown 0.8s ease infinite; }

@keyframes bounceUp {
    0%   { transform: translateY(0); opacity:1; }
    50%  { transform: translateY(-5px); opacity:0.6; }
    100% { transform: translateY(0); opacity:1; }
}
@keyframes bounceDown {
    0%   { transform: translateY(0); opacity:1; }
    50%  { transform: translateY(5px); opacity:0.6; }
    100% { transform: translateY(0); opacity:1; }
}

.index-row { padding: 6px 0; border-bottom: 1px solid #1e1e1e; font-size:13px; }
</style>
""", unsafe_allow_html=True)

# ── 시간 표시 ─────────────────────────────────────────────────────────
def time_ago(pub_date):
    try:
        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
        diff = datetime.now(timezone.utc) - dt
        m = int(diff.total_seconds() / 60)
        return "방금 전" if m < 1 else f"{m}분 전" if m < 60 else f"{m//60}시간 전"
    except:
        return ""

# ── 한국 지수 ─────────────────────────────────────────────────────────
def fetch_korea_index():
    headers = {"User-Agent": "Mozilla/5.0"}

    def get(symbol):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
            res = requests.get(url, headers=headers, timeout=5).json()
            closes = res["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c]
            if len(closes) < 2:
                return 0
            return ((closes[-1] - closes[-2]) / closes[-2]) * 100
        except:
            return 0

    return get("^KS11"), get("^KQ11")

# ── 미국 지수 (S&P500 + NASDAQ + RUSSELL) ────────────────────────────
def fetch_us_index():
    try:
        symbols = "^GSPC,^IXIC,^RUT"
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
        data = res["quoteResponse"]["result"]

        sp = nasdaq = russell = 0
        for item in data:
            pct = item.get("regularMarketChangePercent", 0) or 0
            if item["symbol"] == "^GSPC":
                sp = pct
            elif item["symbol"] == "^IXIC":
                nasdaq = pct
            elif item["symbol"] == "^RUT":
                russell = pct

        return sp, nasdaq, russell
    except:
        return 0, 0, 0

# ── 환율 ─────────────────────────────────────────────────────────────
def fetch_usd():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5).json()
        return res["rates"]["KRW"]
    except:
        return 0

# ── 통합 (ttl=10초로 단축) ────────────────────────────────────────────
@st.cache_data(ttl=10)
def fetch_indices():
    kospi, kosdaq = fetch_korea_index()
    sp, nasdaq, russell = fetch_us_index()
    usd = fetch_usd()

    return {
        "KOSPI":    ("pct", kospi),
        "KOSDAQ":   ("pct", kosdaq),
        "S&P500":   ("pct", sp),
        "NASDAQ":   ("pct", nasdaq),
        "RUSSELL":  ("pct", russell),
        "USD/KRW":  ("fx",  usd),
    }

# ── 카테고리 ──────────────────────────────────────────────────────────
def detect_cat(title):
    t = title.lower()
    if re.search(r"ai|gpt|반도체|엔비디아|삼성|하이닉스", t):
        return "AI"
    if re.search(r"코스피|코스닥|환율|금리|시장|증시|나스닥", t):
        return "증시"
    return "기타"

# ── 뉴스 ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def fetch_news():
    urls = [
        "https://kr.investing.com/rss/news_25.rss",
        "https://kr.investing.com/rss/news_285.rss",
        "https://kr.investing.com/rss/news_1.rss"
    ]
    data, seen = [], set()

    for u in urls:
        try:
            xml = requests.get(u, timeout=5).text
        except:
            continue
        items = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)

        for it in items:
            t = re.search(r"<title>(.*?)</title>", it)
            l = re.search(r"<link>(.*?)</link>", it)
            d = re.search(r"<pubDate>(.*?)</pubDate>", it)

            if not t or not l:
                continue

            title = re.sub(r"<!\[CDATA\[|\]\]>", "", t.group(1))
            link  = l.group(1)

            if link in seen:
                continue
            seen.add(link)

            data.append({
                "title":    title,
                "url":      link,
                "category": detect_cat(title),
                "time":     time_ago(d.group(1) if d else "")
            })

    return data

# ═══════════════════════════════════════════════════════════════════════
# 사이드바
# ═══════════════════════════════════════════════════════════════════════
st.sidebar.title("📊 주요 지수")
st.sidebar.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} 기준")

indices = fetch_indices()

for name, (kind, val) in indices.items():
    if kind == "fx":
        st.sidebar.markdown(
            f"<div class='index-row meta'>{name} &nbsp;<b>{val:,.2f}</b></div>",
            unsafe_allow_html=True
        )
    else:
        cls   = "up" if val >= 0 else "down"
        arrow = "▲" if val >= 0 else "▼"
        sign  = "+" if val >= 0 else ""
        st.sidebar.markdown(
            f"""<div class='index-row {cls}'>
                  {name} &nbsp;
                  <span class='arrow'>{arrow}</span>
                  {sign}{val:.2f}%
                </div>""",
            unsafe_allow_html=True
        )

# ═══════════════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════════════
st.title("📰 IT PULSE")

col1, col2 = st.columns([1, 1])
with col1:
    refresh = st.selectbox("자동 새로고침 (뉴스)", ["없음", "1분", "3분", "5분"])
with col2:
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

data = fetch_news()

tab1, tab2, tab3 = st.tabs(["전체", "AI", "증시"])

def render(cat=None):
    for a in data:
        if cat and a["category"] != cat:
            continue
        st.markdown(f"""
        <div class="card">
          <div class="title"><a href="{a['url']}" target="_blank">{a['title']}</a></div>
          <div class="meta">{a['category']} · {a['time']}</div>
        </div>
        """, unsafe_allow_html=True)

with tab1:
    render()
with tab2:
    render("AI")
with tab3:
    render("증시")

# ── 뉴스 자동 새로고침 ────────────────────────────────────────────────
if refresh != "없음":
    wait = {"1분": 60, "3분": 180, "5분": 300}[refresh]
    time.sleep(wait)
    st.cache_data.clear()
    st.rerun()
