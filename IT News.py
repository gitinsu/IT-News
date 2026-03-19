import streamlit as st
import requests
import re
import time
from datetime import datetime, timezone

st.set_page_config(page_title="IT PULSE", layout="wide")

# ── 자동 새로고침 (10초) ──────────────────────────────────────────────
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=10_000, limit=None, key="ticker_refresh")

# 🎨 스타일 + 화살표 애니메이션
st.markdown("""
<style>
.card { padding:12px; border-radius:10px; border:1px solid #2a2a2a; margin-bottom:10px; }
.title { font-size:14px; font-weight:500; }
.meta { font-size:11px; color:gray; }
.up   { color:#ff4d4f; font-weight:bold; }
.up   .arrow { display:inline-block; animation: bounceUp 0.8s ease infinite; }
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

def time_ago(pub_date):
    try:
        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
        diff = datetime.now(timezone.utc) - dt
        m = int(diff.total_seconds() / 60)
        return "방금 전" if m < 1 else f"{m}분 전" if m < 60 else f"{m//60}시간 전"
    except:
        return ""

def fetch_korea_index():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
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

def fetch_us_index():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://finance.yahoo.com/",
    }
    def get(symbol):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2d&interval=1d"
            res = requests.get(url, headers=headers, timeout=5).json()
            result = res["chart"]["result"][0]
            closes = result["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None]
            if len(closes) < 2:
                return 0, 0
            prev = closes[-2]
            curr = closes[-1]
            pct = ((curr - prev) / prev) * 100
            return curr, pct
        except:
            return 0, 0
    sp_val,      sp_pct      = get("^GSPC")
    nasdaq_val,  nasdaq_pct  = get("^IXIC")
    russell_val, russell_pct = get("^RUT")
    return (sp_val, sp_pct), (nasdaq_val, nasdaq_pct), (russell_val, russell_pct)

def fetch_usd():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://finance.yahoo.com/",
        }
        url = "https://query1.finance.yahoo.com/v8/finance/chart/USDKRW=X?range=1d&interval=1m"
        res = requests.get(url, headers=headers, timeout=5).json()
        closes = res["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        if closes:
            return closes[-1]
    except:
        pass
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5).json()
        return res["rates"]["KRW"]
    except:
        pass
    try:
        res = requests.get("https://api.frankfurter.app/latest?from=USD&to=KRW", timeout=5).json()
        return res["rates"]["KRW"]
    except:
        return 0

@st.cache_data(ttl=10)
def fetch_indices():
    kospi, kosdaq = fetch_korea_index()
    sp, nasdaq, russell = fetch_us_index()
    usd = fetch_usd()
    sp_val,      sp_pct      = sp
    nasdaq_val,  nasdaq_pct  = nasdaq
    russell_val, russell_pct = russell
    return {
        "KOSPI":   ("pct",  kospi,        None),
        "KOSDAQ":  ("pct",  kosdaq,       None),
        "S&P500":  ("both", sp_pct,       sp_val),
        "NASDAQ":  ("both", nasdaq_pct,   nasdaq_val),
        "RUSSELL": ("both", russell_pct,  russell_val),
        "USD/KRW": ("fx",   usd,          None),
    }

def detect_cat(title):
    t = title.lower()
    if re.search(r"ai|gpt|llm|인공지능|반도체|엔비디아|삼성전자|하이닉스|챗봇|딥러닝|gtc", t):
        return "AI·반도체"
    if re.search(r"애플|구글|메타|아마존|마이크로소프트|테슬라|빅테크|틱톡|로봇|자율주행", t):
        return "빅테크"
    if re.search(r"코스피|코스닥|환율|금리|시장|증시|나스닥|s&p|다우", t):
        return "증시"
    if re.search(r"게임|엔씨|넥슨|크래프톤|카카오게임", t):
        return "게임"
    if re.search(r"핀테크|카카오뱅크|토스|블록체인|비트코인|코인", t):
        return "핀테크"
    return "기타IT"

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
            xml = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).text
        except:
            continue
        items = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)
        for it in items:
            t = re.search(r"<title>(.*?)</title>", it)
            l = re.search(r"<link>(.*?)</link>", it)
            d = re.search(r"<pubDate>(.*?)</pubDate>", it)
            if not t or not l:
                continue
            title = re.sub(r"<!\[CDATA\[|\]\]>", "", t.group(1)).strip()
            link  = l.group(1).strip()
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

# ── 사이드바 ──────────────────────────────────────────────────────────
st.sidebar.title("📊 주요 지수")
st.sidebar.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} 기준")

indices = fetch_indices()

for name, info in indices.items():
    kind  = info[0]
    val   = info[1]
    extra = info[2]
    if kind == "fx":
        st.sidebar.markdown(
            f"<div class='index-row meta'>{name} &nbsp;<b>{val:,.2f}</b></div>",
            unsafe_allow_html=True
        )
    elif kind == "both":
        cls   = "up" if val >= 0 else "down"
        arrow = "▲" if val >= 0 else "▼"
        sign  = "+" if val >= 0 else ""
        price_str = f"<span style='font-size:11px;color:gray'>{extra:,.2f}</span> &nbsp;" if extra else ""
        st.sidebar.markdown(
            f"""<div class='index-row {cls}'>
                  {name} &nbsp;{price_str}
                  <span class='arrow'>{arrow}</span>
                  {sign}{val:.2f}%
                </div>""",
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

# ── 메인 ──────────────────────────────────────────────────────────────
st.title("📰 IT PULSE")

col1, col2 = st.columns([1, 1])
with col1:
    refresh = st.selectbox("자동 새로고침 (뉴스)", ["없음", "1분", "3분", "5분"])
with col2:
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

data = fetch_news()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["전체", "AI·반도체", "빅테크", "게임", "핀테크"])

def render(cat=None):
    items = [a for a in data if not cat or a["category"] == cat]
    if not items:
        st.caption("뉴스가 없습니다.")
        return
    for a in items:
        st.markdown(f"""
        <div class="card">
          <div class="title"><a href="{a['url']}" target="_blank">{a['title']}</a></div>
          <div class="meta">{a['category']} · {a['time']}</div>
        </div>
        """, unsafe_allow_html=True)

with tab1:
    render()
with tab2:
    render("AI·반도체")
with tab3:
    render("빅테크")
with tab4:
    render("게임")
with tab5:
    render("핀테크")

if refresh != "없음":
    wait = {"1분": 60, "3분": 180, "5분": 300}[refresh]
    time.sleep(wait)
    st.cache_data.clear()
    st.rerun()