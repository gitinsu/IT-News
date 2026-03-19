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
</style>
""", unsafe_allow_html=True)


# 🔥 시간 변환 (몇분 전)
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
            hours = minutes // 60
            return f"{hours}시간 전"
    except:
        return ""


# 🔥 카테고리 분류
def detect_cat(title):
    t = title.lower()

    # AI (반도체 포함)
    if re.search(r"""
        ai|gpt|llm|인공지능|딥러닝|머신러닝|
        반도체|hbm|dram|낸드|칩|파운드리|
        엔비디아|amd|인텔|tsmc|하이닉스
    """, t, re.VERBOSE):
        return "AI"

    # 암호화폐
    if re.search(r"비트코인|이더리움|코인|암호화폐|블록체인", t):
        return "암호화폐"

    # 증시
    if re.search(r"""
        증시|주식|코스피|코스닥|환율|경제|
        골드만삭스|나스닥|다우|s&p|
        급등|시장|금리|연준
    """, t, re.VERBOSE):
        return "증시"

    return "기타"


# 🔥 뉴스 가져오기
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


# 🔥 UI
st.title("📰 IT PULSE")
st.caption("실시간 IT 뉴스 (RSS 기반)")

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