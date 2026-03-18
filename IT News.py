import streamlit as st
import requests
import re

st.set_page_config(page_title="IT PULSE", layout="wide")

# 🔥 RSS 가져오기
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

            all_articles.append({
                "title": title,
                "url": link,
                "category": detect_cat(title)
            })

            if len(all_articles) >= 60:
                break

    return all_articles


# 🔥 IT 필터
def is_it(title):
    t = title.lower()
    keywords = [
        "ai","인공지능","gpt","llm",
        "반도체","hbm","dram","칩",
        "엔비디아","amd","인텔",
        "애플","구글","마이크로소프트",
        "삼성","하이닉스","현대",
        "테슬라","클라우드","aws"
    ]
    return any(k in t for k in keywords)


# 🔥 카테고리
def detect_cat(title):
    t = title.lower()

    if re.search(r"ai|gpt|llm|인공지능", t):
        return "AI·인공지능"
    if re.search(r"반도체|칩|하이닉스|hbm|dram", t):
        return "반도체·하드웨어"
    if re.search(r"애플|구글|마이크로소프트|삼성|현대|테슬라", t):
        return "빅테크·플랫폼"

    return "기타IT"


# 🔥 UI 시작
st.title("📰 IT PULSE (Streamlit)")
st.caption("Investing RSS 기반 IT 뉴스")

if st.button("🔄 뉴스 가져오기"):
    with st.spinner("뉴스 가져오는 중..."):
        articles = fetch_news()

        it_articles = [a for a in articles if is_it(a["title"])]

        final = it_articles[:20] if len(it_articles) >= 10 else (it_articles + articles)[:20]

        st.success(f"{len(final)}개 뉴스 로드 완료")

        # 🔥 카드 UI
        for a in final:
            with st.container():
                st.markdown(f"""
                ### [{a['title']}]({a['url']})
                **{a['category']}**
                ---
                """)