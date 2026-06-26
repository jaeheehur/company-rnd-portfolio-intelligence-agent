"""키워드 생성 노드: 확정 기업·사업분야로부터 검색 키워드 ~20개 생성."""
from clients import llm
from graph.state import IntelState


def keyword_generator(state: IntelState) -> dict:
    company = state["confirmed_company"]["name"]
    field = state["business_field"]

    prompt = f"""경쟁사 인텔리전스 조사를 위한 검색 키워드를 생성하세요.

기업명: {company}
사업분야: {field}

요구사항:
- 한국어와 영어 키워드 혼합
- 기업명 변형(약칭·영문·한글), 주요 기술명, 제품명, 파이프라인 키워드 포함
- 15~20개
- JSON 문자열 배열로 반환"""

    keywords: list[str] = llm.structured(prompt, list[str])
    return {"keywords": keywords}
