exports.handler = async () => {
  try {
    const urls = [
      "https://kr.investing.com/rss/news_25.rss",
      "https://kr.investing.com/rss/news_285.rss",
      "https://kr.investing.com/rss/news_1.rss"
    ];

    let allArticles = [];
    const seen = new Set();

    for (let feedUrl of urls) {
      const res = await fetch(feedUrl);
      const xml = await res.text();

      const items = [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)];

      for (let i = 0; i < items.length; i++) {
        const item = items[i][1];

        const titleMatch = item.match(/<title>(.*?)<\/title>/);
        const linkMatch = item.match(/<link>(.*?)<\/link>/);

        if (!titleMatch || !linkMatch) continue;

        const title = titleMatch[1]
          .replace(/<!\[CDATA\[|\]\]>/g, '')
          .trim();

        const url = linkMatch[1];

        // 🔥 중복 제거
        if (seen.has(url)) continue;
        seen.add(url);

        allArticles.push({
          title,
          url,
          category: detectCat(title),
          source: "Investing"
        });

        if (allArticles.length >= 60) break; // 넉넉하게 확보
      }
    }

    // 🔥 IT 필터
    const itArticles = allArticles.filter(a => isIT(a.title));

    // 🔥 부족하면 채우기
    const finalArticles = itArticles.length >= 10
      ? itArticles.slice(0, 20)
      : [...itArticles, ...allArticles].slice(0, 20);

    return {
      statusCode: 200,
      body: JSON.stringify({
        articles: finalArticles,
        total: allArticles.length,
        itCount: itArticles.length
      })
    };

  } catch (e) {
    return {
      statusCode: 500,
      body: JSON.stringify({
        error: e.message,
        articles: []
      })
    };
  }
};


// 🔥 IT 필터
function isIT(title) {
  const t = title.toLowerCase();

  return [
    "ai","인공지능","gpt","llm",
    "반도체","hbm","dram","낸드","칩",
    "엔비디아","amd","인텔",
    "애플","구글","메타","아마존","마이크로소프트",
    "삼성","삼성전자","하이닉스","sk하이닉스",
    "테슬라","현대","현대차",
    "클라우드","aws"
  ].some(k => t.includes(k));
}


// 🔥 카테고리 분류 (최종)
function detectCat(title) {
  const t = title.toLowerCase();

  // 1️⃣ AI
  if (/ai|gpt|llm|인공지능|딥러닝|머신러닝/.test(t)) {
    return "AI·인공지능";
  }

  // 2️⃣ 반도체
  if (/반도체|hbm|dram|낸드|칩|파운드리|엔비디아|amd|인텔|tsmc|하이닉스|sk하이닉스/.test(t)) {
    return "반도체·하드웨어";
  }

  // 3️⃣ 빅테크 (🔥 한국 기업 포함)
  if (/애플|구글|메타|아마존|마이크로소프트|알파벳|테슬라|넷플릭스|카카오|네이버|삼성|삼성전자|현대|현대차/.test(t)) {
    return "빅테크·플랫폼";
  }

  return "기타IT";
}