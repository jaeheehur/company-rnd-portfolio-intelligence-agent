"""기업 해석 노드: 동명이의 후보 생성 + 사용자 확정(interrupt)."""
import json
from langgraph.types import interrupt
from clients import llm, dart_client, yfinance_client
from graph.state import IntelState, Candidate


def company_resolver(state: IntelState) -> dict:
    """한글 포함 여부로 국내/해외 1차 판별 후 LLM이 관련성 기준으로 재랭킹."""
    query = state["query_name"]
    field = state["business_field"]

    is_korean = any("가" <= c <= "힣" for c in query)

    if is_korean:
        candidates = dart_client.find_corp(query)
    else:
        candidates = yfinance_client.find_ticker(query)

    if len(candidates) > 1:
        prompt = f"""다음 기업 후보들을 '{field}' 사업분야와의 관련성 기준으로 재랭킹하세요.
후보: {json.dumps(candidates, ensure_ascii=False)}
JSON 배열로 반환. score 필드(0.0-1.0)를 관련성에 맞게 조정. 상위 5개만."""
        candidates = llm.structured(prompt, list[Candidate])[:5]

    return {"company_candidates": candidates}


def human_confirm(state: IntelState) -> dict:
    """사용자가 기업 후보 중 하나를 선택하는 interrupt 노드.
    Streamlit에서 Command(resume=chosen_candidate)로 재개.
    """
    chosen: Candidate = interrupt({
        "type": "select_company",
        "candidates": state["company_candidates"],
        "message": "분석할 기업을 선택하세요.",
    })
    return {"confirmed_company": chosen}
