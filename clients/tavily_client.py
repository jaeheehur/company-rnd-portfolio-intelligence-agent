"""Tavily 뉴스 검색 클라이언트. 월 1,000건 무료 티어."""
from tavily import TavilyClient
import config

_client = TavilyClient(api_key=config.TAVILY_API_KEY)


def search(query: str, max_results: int = 5) -> list[dict]:
    """키워드 검색 → [{title, url, content, published_date, score}] 반환."""
    response = _client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced",
        include_answer=False,
    )
    return response.get("results", [])
