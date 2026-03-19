import streamlit as st
import requests
import re
import time
from datetime import datetime, timezone

st.set_page_config(page_title="IT PULSE", layout="wide")

# 🎨 스타일
st.markdown("""
<style>
.card {
    padding: 12px;
    border-radius: 10px;
    border: 1px solid #2a2a2a;
    margin-bottom: 10px;
}
.title {
    font-size: 14px;
    font-weight: 500;
}
.meta {
    font-size: 11px;
    color: gray;
}

.up {
    color: #ff4d4f;
    font-weight: bold;
    animation: blink 1s infinite;
}

.down {
    color: #4da6ff;
    font-weight: bold;
    animation: blink 1s infinite;
}

@keyframes blink {
    50% { opacity: 0.3; }
}
</style>
""", unsafe_allow_html=True)


# 🔥 시간 표시
def time_ago(pub_date):
    try:
        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
        now = datetime.now(timezone.utc)
        diff = now - dt
        minutes = int(diff.total_seconds() / 60)

        if minutes < 1:
            return "방금 전"
        elif minutes < 60:
            return f"{minutes}분 전"
        else:
            return f"{minutes//60}시간 전"
    except:
        return ""


# 🔥 🇰🇷 네이버 금융 (코스피/코스닥 해결)
def fetch_korea_index():
    headers = {"User-Agent": "Mozilla/5.0"}

    kospi = 0
    kosdaq = 0

    try:
        url = "https://polling.finance.naver.com/api/realtime"
        res = requests.get(url, headers=headers).json()

        for item in res["result"]["areas"][0]["datas"]:
            if item["code"] == "KOSPI":
                kospi = float(item["nv"]) - float(item["cv"])
                kospi = (kospi / float(item["cv"])) * 100

            elif item["code"] == "KOSDAQ":
                kosdaq = float(item["nv"]) - float(item["cv"])
                kosdaq = (kosdaq / float(item["cv"])) * 100

    except Exception as e:
        print("네이버 오류:", e)

    return kospi, kosdaq


# 🔥 🌍 해외 (Yahoo)
def fetch_global_index(symbol):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
        res = requests.get(url, headers=headers).json()

        result = res["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]

        prev = closes[-2]
        current = closes[-1]

        return ((current - prev) / prev) * 100

    except:
        return 0


# 🔥 지수 통합 (완전 안정)
def fetch_indices():
    kospi, kosdaq = fetch_korea_index()

    return {
        "KOSPI": kospi,
        "KOSDAQ": kosdaq,
        "S&P500": fetch_global_index("^GSPC"),
        "RUSSELL": fetch_global_index("^RUT")
    }


# 🔥 카테고리
def detect_cat(title):
    t = title.lower()

    if re.search(r"ai|gpt|llm|인공지능|반도체|hbm|dram|칩|엔비디아|amd|인텔|하이닉스", t):
        return "AI"

    if re.search(r"비트코인|이더리움|코인|암호화폐|블록체인", t):
        return "암호화폐"

    if re.search(r"코스피|코스닥|환율|경제|나스닥|다우|s&p|시장|금리|급등", t):
        return "증시"

    return "기타"


# 🔥 뉴스
def fetch_news():
    urls = [
        "https://kr.investing.com/rss/news_25.rss",
        "https://kr.investing.com/rss/news_285.rss",
        "https://kr.investing.com/rss/news_1.rss"
    ]

    all_articles = []
    seen = set()

    for url in urls:
        res = requests.get(url)
        xml = res.text

        items = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)

        for item in items:
            title_match = re.search(r"<title>(.*?)</title>", item)
            link_match = re.search(r"<link>(.*?)</link>", item)
            date_match = re.search(r"<pubDate>(.*?)</pubDate>", item)

            if not title_match or not link_match:
                continue

            title = re.sub(r"<!\[CDATA\[|\]\]>", "", title_match.group(1)).strip()
            link = link_match.group(1)
            pub_date = date_match.group(1) if date_match else ""

            if link in seen:
                continue
            seen.add(link)

            all_articles.append({
                "title": title,
                "url": link,
                "category": detect_cat(title),
                "time": time_ago(pub_date)
            })

            if len(all_articles) >= 60:
                break

    return all_articles


# 🔥 사이드바
st.sidebar.title("📊 주요 지수")

indices = fetch_indices()

for name, val in indices.items():
    cls = "up" if val >= 0 else "down"
    st.sidebar.markdown(
        f"<div class='{cls}'>{name} {val:.2f}%</div>",
        unsafe_allow_html=True
    )


# 🔥 메인
st.title("📰 IT PULSE")

col1, col2 = st.columns([1,1])

with col1:
    refresh = st.selectbox("자동 새로고침", ["없음", "1분", "3분", "5분"])

with col2:
    if st.button("🔄 새로고침"):
        st.session_state["refresh_now"] = True


# 🔥 데이터 로드
if "data" not in st.session_state or st.session_state.get("refresh_now"):
    with st.spinner("뉴스 가져오는 중..."):
        st.session_state["data"] = fetch_news()
        st.session_state["refresh_now"] = False

data = st.session_state["data"]


# 🔥 탭
tab1, tab2, tab3 = st.tabs(["전체", "AI", "증시"])


def render_news(filter_name=None):
    for a in data:
        if filter_name and a["category"] != filter_name:
            continue

        st.markdown(f"""
        <div class="card">
            <div class="title">
                <a href="{a['url']}" target="_blank">{a['title']}</a>
            </div>
            <div class="meta">{a['category']} · {a['time']}</div>
        </div>
        """, unsafe_allow_html=True)


with tab1:
    render_news()

with tab2:
    render_news("AI")

with tab3:
    render_news("증시")


# 🔥 자동 새로고침
if refresh != "없음":
    sec = {"1분":60, "3분":180, "5분":300}[refresh]
    time.sleep(sec)
    st.rerun()