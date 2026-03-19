import streamlit as st
import requests
import re
import time
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

st.set_page_config(page_title="IT PULSE", layout="wide")

# ── 자동 새로고침 (10초) ──────────────────────────────────────────────
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=10_000, limit=None, key="ticker_refresh")
except:
    pass

# 🎨 스타일
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

# ── 시간 표시 (한국시간 KST 기준) ────────────────────────────────────
def time_ago(pub_date):
    try:
        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
        now_kst = datetime.now(KST)
        diff = now_kst - dt.astimezone(KST)
        m = int(diff.total_seconds() / 60)
        return "방금 전" if m < 1 else f"{m}분 전" if m < 60 else f"{m//60}시간 전"
    except:
        return ""

# ── 한국 지수 (현재가 + 등락률) ──────────────────────────────────────
def fetch_korea_index():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://finance.yahoo.com/",
    }
    def get(symbol):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
            res = requests.get(url, headers=headers, timeout=5).json()
            result = res["chart"]["result"][0]
            closes = result["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None]
            if len(closes) < 2:
                return 0, 0
            curr = closes[-1]
            prev = closes[-2]
            pct  = ((curr - prev) / prev) * 100
            return curr, pct
        except:
            return 0, 0
    return get("^KS11"), get("^KQ11")

# ── 미국 지수 (실시간 regularMarketPrice 사용) ────────────────────────
def fetch_us_index():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://finance.yahoo.com/",
    }
    def get(symbol):
        try:
            # v8 chart 1d 분봉 → 실시간에 가까운 데이터
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=5m"
            res = requests.get(url, headers=headers, timeout=5).json()
            result = res["chart"]["result"][0]
            meta  = result.get("meta", {})
            curr  = meta.get("regularMarketPrice", 0)
            prev  = meta.get("chartPreviousClose", 0) or meta.get("previousClose", 0)
            if not curr or not prev:
                return 0, 0
            pct = ((curr - prev) / prev) * 100
            return curr, pct
        except:
            return 0, 0

    sp_val,      sp_pct      = get("^GSPC")
    nasdaq_val,  nasdaq_pct  = get("^IXIC")
    russell_val, russell_pct = get("^RUT")
    return (sp_val, sp_pct), (nasdaq_val, nasdaq_pct), (russell_val, russell_pct)

# ── 환율 (실시간 fallback) ────────────────────────────────────────────
def fetch_usd():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://finance.yahoo.com/",
    }
    try:
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

# ── 통합 캐시 ─────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def fetch_indices():
    kospi, kosdaq           = fetch_korea_index()
    sp, nasdaq, russell     = fetch_us_index()
    usd                     = fetch_usd()
    kospi_val,   kospi_pct  = kospi
    kosdaq_val,  kosdaq_pct = kosdaq
    sp_val,      sp_pct     = sp
    nasdaq_val,  nasdaq_pct = nasdaq
    russell_val, russell_pct= russell
    return {
        "KOSPI":   ("both", kospi_pct,    kospi_val),
        "KOSDAQ":  ("both", kosdaq_pct,   kosdaq_val),
        "S&P500":  ("both", sp_pct,       sp_val),
        "NASDAQ":  ("both", nasdaq_pct,   nasdaq_val),
        "RUSSELL": ("both", russell_pct,  russell_val),
        "USD/KRW": ("fx",   usd,          None),
    }

# ── 카테고리 ──────────────────────────────────────────────────────────
def detect_cat(title):
    t = title.lower()

    # AI·반도체: AI 기술 + 반도체 기업
    if re.search(r"ai|gpt|llm|인공지능|반도체|엔비디아|nvidia|amd|인텔|intel|tsmc|hbm|낸드|dram|칩|파운드리|챗봇|딥러닝|gtc|머신러닝|생성형", t):
        return "AI·반도체"

    # 빅테크: 국내 TOP5 + 해외 M7
    if re.search(
        r"삼성전자|sk하이닉스|하이닉스|현대차|lg전자|카카오|네이버|"  # 국내 TOP5
        r"애플|apple|구글|google|메타|meta|아마존|amazon|마이크로소프트|microsoft|ms|"  # 해외 M7
        r"테슬라|tesla|알파벳|alphabet|엔비디아|nvidia|"
        r"빅테크|틱톡|tiktok|유튜브|youtube|페이스북|facebook|클라우드|aws|애저",
        t
    ):
        return "빅테크"

    # 암호화폐·에너지: 코인 + 유가
    if re.search(r"비트코인|bitcoin|이더리움|ethereum|코인|암호화폐|블록체인|crypto|"
                 r"유가|원유|wti|브렌트|brent|석유|오일|천연가스|lng|에너지", t):
        return "코인·에너지"

    return None  # IT 무관 → 표시 안 함

# ── 뉴스 ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def fetch_news():
    urls = [
        "https://kr.investing.com/rss/news_25.rss",
        "https://kr.investing.com/rss/news_285.rss",
        "https://kr.investing.com/rss/news_1.rss",
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

            cat = detect_cat(title)
            if cat is None:
                continue  # IT 무관 뉴스 제외

            data.append({
                "title":    title,
                "url":      link,
                "category": cat,
                "time":     time_ago(d.group(1) if d else "")
            })

    return data

# ── 사이드바 ──────────────────────────────────────────────────────────
st.sidebar.title("📊 주요 지수")
st.sidebar.caption(f"🕐 {datetime.now(KST).strftime('%H:%M:%S')} KST 기준")

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

tab1, tab2, tab3, tab4 = st.tabs(["전체", "AI·반도체", "빅테크", "코인·에너지"])

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
    render("코인·에너지")

# ── 뉴스 자동 새로고침 ────────────────────────────────────────────────
if refresh != "없음":
    wait = {"1분": 60, "3분": 180, "5분": 300}[refresh]
    time.sleep(wait)
    st.cache_data.clear()
    st.rerun()
