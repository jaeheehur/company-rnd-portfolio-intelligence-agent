"""교차검증 노드: 특허·재무·뉴스 시계열을 LLM으로 교차 분석."""
import json
from clients import llm
from graph.state import IntelState


def cross_validator(state: IntelState) -> dict:
    company = state["confirmed_company"]["name"]
    finance = state["finance"]
    patents = state["patents"]
    news = state["news"]

    # 연도별 특허 출원 수 집계
    patent_by_year: dict[int, int] = {}
    for p in patents:
        patent_by_year[p["filing_year"]] = patent_by_year.get(p["filing_year"], 0) + 1

    top_news = [f"- {n['summary']}" for n in news[:5]]

    prompt = f"""{company}의 다중 소스 데이터를 교차 분석하여 전략적 인사이트를 도출하세요.

[재무 추세]
{finance['interpretation']}

[연도별 특허 출원 수]
{json.dumps(patent_by_year)}

[연도별 R&D 투자액({finance['currency']})]
{dict(zip(finance['years'], finance['rnd_expense']))}

[최근 주요 뉴스]
{chr(10).join(top_news)}

분석 포인트:
1. R&D 증가 → 특허 급증 간 시차(lag) 분석
2. 특허 IPC 집중 분야와 매출 연계
3. 뉴스 이벤트(M&A, 출시, 제휴)와 특허/재무 패턴 정합성
4. 향후 18개월 기술 상용화 가능성 시그널

JSON으로 반환:
{{
  "patent_rnd_lag": "...",
  "tech_revenue_link": "...",
  "news_patent_alignment": "...",
  "commercialization_signal": "...",
  "summary": "3-4문장 종합 요약"
}}"""

    cross_validation = llm.structured(prompt, dict)
    return {"cross_validation": cross_validation}
