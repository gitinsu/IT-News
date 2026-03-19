import streamlit as st
import requests
import re
import time

st.set_page_config(page_title="IT PULSE", layout="wide")

# 🔥 스타일 (글씨 줄이고 카드 느낌)
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

            if not title_match or not link_match:
                continue

            title = re.sub(r"<!\[CDATA\[|\]\]>", "", title_match.group(1)).strip()
            link = link_match.group(1)

            if link in seen:
                continue
            seen.add(link)

            category = detect_cat(title)

            all_articles.append({
                "title": title,
                "url": link,
                "category": category
            })

            if len(all_articles) >= 60:
                break

    return all_articles


# 🔥 카테고리 분류
def detect_cat(title):
    t = title.lower()

    if re.search(r"ai|gpt|llm|인공지능", t):
        return "AI"
    if re.search(r"반도체|hbm|dram|낸드|칩|엔비디아|amd|인텔|하이닉스", t):
        return "반도체"
    if re.search(r"비트코인|이더리움|코인|암호화폐|블록체인", t):
        return "암호화폐"
    if re.search(r"증시|주식|나스닥|다우|s&p|금리", t):
        return "증시"

    return "기타"


# 🔥 UI 상단
st.title("📰 IT PULSE")
st.caption("실시간 IT 뉴스")

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

# 🔥 탭 UI
tab1, tab2, tab3, tab4 = st.tabs(["전체", "반도체", "암호화폐", "증시"])

def render_news(filter_name=None):
    for a in data:
        if filter_name and a["category"] != filter_name:
            continue

        st.markdown(f"""
        <div class="card">
            <div class="title"><a href="{a['url']}" target="_blank">{a['title']}</a></div>
            <div class="meta">{a['category']}</div>
        </div>
        """, unsafe_allow_html=True)


with tab1:
    render_news()

with tab2:
    render_news("반도체")

with tab3:
    render_news("암호화폐")

with tab4:
    render_news("증시")


# 🔥 자동 새로고침
if refresh != "없음":
    sec = {"1분":60, "3분":180, "5분":300}[refresh]
    time.sleep(sec)
    st.rerun()