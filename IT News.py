import streamlit as st
import requests
import re
import time
from datetime import datetime, timezone

st.set_page_config(page_title="IT PULSE", layout="wide")

# 🎨 스타일
st.markdown("""
<style>
.card { padding:12px; border-radius:10px; border:1px solid #2a2a2a; margin-bottom:10px; }
.title { font-size:14px; font-weight:500; }
.meta { font-size:11px; color:gray; }
.up { color:#ff4d4f; font-weight:bold; animation: blink 1s infinite; }
.down { color:#4da6ff; font-weight:bold; animation: blink 1s infinite; }
@keyframes blink { 50% { opacity:0.3; } }
</style>
""", unsafe_allow_html=True)

# 🔥 시간 표시
def time_ago(pub_date):
    try:
        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
        diff = datetime.now(timezone.utc) - dt
        m = int(diff.total_seconds()/60)
        return "방금 전" if m<1 else f"{m}분 전" if m<60 else f"{m//60}시간 전"
    except:
        return ""

# 🔥 한국 지수 (chart API - 안정)
def fetch_korea_index():
    try:
        headers = {"User-Agent":"Mozilla/5.0"}

        def get(symbol):
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
            res = requests.get(url, headers=headers).json()

            closes = res["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c]

            if len(closes) < 2:
                return 0

            return ((closes[-1] - closes[-2]) / closes[-2]) * 100

        return get("^KS11"), get("^KQ11")

    except:
        return 0, 0

# 🔥 미국 지수 (quote API)
def fetch_us_index():
    try:
        url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=^GSPC,^RUT"
        res = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}).json()

        data = res["quoteResponse"]["result"]

        sp = russell = 0

        for i in data:
            if i["symbol"] == "^GSPC":
                sp = i.get("regularMarketChangePercent", 0)
            elif i["symbol"] == "^RUT":
                russell = i.get("regularMarketChangePercent", 0)

        return sp, russell

    except:
        return 0, 0

# 🔥 환율 (유지)
def fetch_usd():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD").json()
        return res["rates"]["KRW"]
    except:
        return 0

# 🔥 통합
def fetch_indices():
    kospi, kosdaq = fetch_korea_index()
    sp, russell = fetch_us_index()
    usd = fetch_usd()

    return {
        "KOSPI": kospi,
        "KOSDAQ": kosdaq,
        "USD/KRW": usd,
        "S&P500": sp,
        "RUSSELL": russell
    }

# 🔥 뉴스
def fetch_news():
    urls = [
        "https://kr.investing.com/rss/news_25.rss",
        "https://kr.investing.com/rss/news_285.rss",
        "https://kr.investing.com/rss/news_1.rss"
    ]

    data, seen = [], set()

    for u in urls:
        xml = requests.get(u).text
        items = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)

        for it in items:
            t = re.search(r"<title>(.*?)</title>", it)
            l = re.search(r"<link>(.*?)</link>", it)
            d = re.search(r"<pubDate>(.*?)</pubDate>", it)

            if not t or not l:
                continue

            title = re.sub(r"<!\[CDATA\[|\]\]>", "", t.group(1))
            link = l.group(1)

            if link in seen:
                continue
            seen.add(link)

            data.append({
                "title": title,
                "url": link,
                "time": time_ago(d.group(1) if d else "")
            })

    return data

# 🔥 UI
st.sidebar.title("📊 주요 지수")

indices = fetch_indices()

for k,v in indices.items():
    if k == "USD/KRW":
        st.sidebar.write(f"{k}: {v:,.2f}")
    else:
        color = "🔴" if v >= 0 else "🔵"
        st.sidebar.write(f"{color} {k}: {v:.2f}%")

st.title("📰 IT PULSE")

data = fetch_news()

for a in data[:20]:
    st.markdown(f"**[{a['title']}]({a['url']})**  \n{a['time']}")
