"""뉴스 수집 에이전트: Tavily 검색 → 중복 제거 → 임팩트 점수 → LLM 요약."""
from clients import llm, tavily_client
from graph.state import IntelState, NewsItem


def news_agent(state: IntelState) -> dict:
    keywords = state["keywords"][:5]

    raw_articles: list[dict] = []
    seen_urls: set[str] = set()

    for kw in keywords:
        for article in tavily_client.search(kw, max_results=5):
            if article["url"] not in seen_urls:
                seen_urls.add(article["url"])
                raw_articles.append(article)

    news_items: list[NewsItem] = []
    for article in raw_articles[:20]:
        prompt = f"""다음 뉴스 기사를 경쟁사 분석 관점에서 평가하세요.
제목: {article['title']}
내용: {article.get('content', '')[:500]}

JSON으로 반환:
{{
  "summary": "1-2줄 핵심 인사이트",
  "impact_score": 0.0-1.0
}}"""
        analysis = llm.structured(prompt, dict)
        news_items.append(NewsItem(
            title=article["title"],
            url=article["url"],
            date=article.get("published_date", ""),
            summary=analysis.get("summary", ""),
            impact_score=float(analysis.get("impact_score", 0.5)),
        ))

    news_items.sort(key=lambda x: x["impact_score"], reverse=True)
    return {"news": news_items[:10]}
