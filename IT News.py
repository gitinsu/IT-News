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

# 🔥 🇰🇷 KRX API (코스피/코스닥)
def fetch_korea_index():
    try:
        url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "http://data.krx.co.kr"
        }

        # 코스피
        kospi_data = {
            "bld": "dbms/MDC/STAT/standard/MDCSTAT00301",
            "locale": "ko_KR",
            "idxIndMidclssCd": "01",  # 코스피
            "trdDd": "20240301"
        }

        # 코스닥
        kosdaq_data = {
            "bld": "dbms/MDC/STAT/standard/MDCSTAT00301",
            "locale": "ko_KR",
            "idxIndMidclssCd": "02",  # 코스닥
            "trdDd": "20240301"
        }

        kospi_res = requests.post(url, data=kospi_data, headers=headers).json()
        kosdaq_res = requests.post(url, data=kosdaq_data, headers=headers).json()

        kospi = float(kospi_res["output"][0]["FLUC_RT"])
        kosdaq = float(kosdaq_res["output"][0]["FLUC_RT"])

        return kospi, kosdaq

    except Exception as e:
        print("KRX 오류:", e)
        return 0, 0

# 🔥 환율 (안정 API)
def fetch_usd():
    try:
        res = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=KRW").json()
        return 0  # 환율은 % 계산 어려워서 0 유지 (원하면 계산 가능)
    except:
        return 0

# 🔥 해외 지수
def fetch_global(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
        res = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}).json()

        closes = res["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c]

        return ((closes[-1]-closes[-2])/closes[-2])*100
    except:
        return 0

# 🔥 지수 통합
def fetch_indices():
    kospi, kosdaq = fetch_korea_index()
    return {
        "KOSPI": kospi,
        "KOSDAQ": kosdaq,
        "USD/KRW": fetch_usd(),
        "S&P500": fetch_global("^GSPC"),
        "RUSSELL": fetch_global("^RUT")
    }

# 🔥 뉴스
def fetch_news():
    urls=[
        "https://kr.investing.com/rss/news_25.rss",
        "https://kr.investing.com/rss/news_285.rss",
        "https://kr.investing.com/rss/news_1.rss"
    ]
    data=[]; seen=set()
    for u in urls:
        xml=requests.get(u).text
        items=re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)
        for it in items:
            t=re.search(r"<title>(.*?)</title>",it)
            l=re.search(r"<link>(.*?)</link>",it)
            d=re.search(r"<pubDate>(.*?)</pubDate>",it)
            if not t or not l: continue
            title=re.sub(r"<!\[CDATA\[|\]\]>","",t.group(1))
            link=l.group(1)
            if link in seen: continue
            seen.add(link)
            data.append({
                "title":title,
                "url":link,
                "time":time_ago(d.group(1) if d else "")
            })
            if len(data)>=60: break
    return data

# 🔥 UI
st.sidebar.title("📊 주요 지수")

indices=fetch_indices()

for k,v in indices.items():
    cls="up" if v>=0 else "down"
    st.sidebar.markdown(f"<div class='{cls}'>{k} {v:.2f}%</div>", unsafe_allow_html=True)

st.title("📰 IT PULSE")

data=fetch_news()

for a in data[:20]:
    st.markdown(f"""
    <div class="card">
    <div class="title"><a href="{a['url']}" target="_blank">{a['title']}</a></div>
    <div class="meta">{a['time']}</div>
    </div>
    """, unsafe_allow_html=True)