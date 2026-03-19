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

# 🔥 🔥 핵심: Daum API
def fetch_daum_market():
    try:
        url = "https://finance.daum.net/api/market_index"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://finance.daum.net/domestic"
        }

        res = requests.get(url, headers=headers).json()

        kospi = kosdaq = usd = 0

        for item in res["data"]:
            name = item["name"]

            if name == "코스피":
                kospi = float(item["changeRate"])

            elif name == "코스닥":
                kosdaq = float(item["changeRate"])

            elif "USD/KRW" in name:
                usd = float(item["tradePrice"])

        return kospi, kosdaq, usd

    except Exception as e:
        print("Daum 오류:", e)
        return 0, 0, 0

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
    kospi, kosdaq, usd = fetch_daum_market()

    return {
        "KOSPI": kospi,
        "KOSDAQ": kosdaq,
        "USD/KRW": usd,
        "S&P500": fetch_global("^GSPC"),
        "RUSSELL": fetch_global("^RUT")
    }

# 🔥 카테고리
def detect_cat(title):
    t = title.lower()

    if re.search(r"ai|gpt|llm|반도체|칩|엔비디아|하이닉스", t):
        return "AI"

    if re.search(r"비트코인|코인|암호화폐", t):
        return "암호화폐"

    if re.search(r"코스피|코스닥|환율|경제|나스닥|금리|시장", t):
        return "증시"

    return "기타"

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
                "category":detect_cat(title),
                "time":time_ago(d.group(1) if d else "")
            })

            if len(data)>=60: break

    return data

# 🔥 사이드바
st.sidebar.title("📊 주요 지수")

indices = fetch_indices()

for k,v in indices.items():
    if k == "USD/KRW":
        st.sidebar.markdown(
            f"<div class='meta'>{k} {v:,.2f}</div>",
            unsafe_allow_html=True
        )
    else:
        cls="up" if v>=0 else "down"
        st.sidebar.markdown(
            f"<div class='{cls}'>{k} {v:.2f}%</div>",
            unsafe_allow_html=True
        )

# 🔥 메인 UI
st.title("📰 IT PULSE")

col1,col2=st.columns([1,1])

with col1:
    refresh=st.selectbox("자동 새로고침",["없음","1분","3분","5분"])

with col2:
    if st.button("🔄 새로고침"):
        st.session_state["r"]=True

# 🔥 데이터 로드
if "data" not in st.session_state or st.session_state.get("r"):
    st.session_state["data"]=fetch_news()
    st.session_state["r"]=False

data=st.session_state["data"]

# 🔥 탭
tab1,tab2,tab3=st.tabs(["전체","AI","증시"])

def render(cat=None):
    for a in data:
        if cat and a["category"]!=cat: continue

        st.markdown(f"""
        <div class="card">
        <div class="title"><a href="{a['url']}" target="_blank">{a['title']}</a></div>
        <div class="meta">{a['category']} · {a['time']}</div>
        </div>
        """, unsafe_allow_html=True)

with tab1: render()
with tab2: render("AI")
with tab3: render("증시")

# 🔥 자동 새로고침
if refresh!="없음":
    time.sleep({"1분":60,"3분":180,"5분":300}[refresh])
    st.rerun()