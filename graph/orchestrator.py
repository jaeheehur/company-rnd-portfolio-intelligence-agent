"""LangGraph 기반 경쟁사 분석 보고서 오케스트레이션.

실행흐름:
  resolver → confirm (interrupt) → keywords
  keywords → [news ∥ ip ∥ finance]
  [news, ip, finance] → cross
  cross → generate_ch1 → review_ch1 -[PASS]→ generate_ch2 → review_ch2 -[PASS]→ generate_ch3 → review_ch3 -[PASS]→ exec_summary → build_refs → END
                        └[FAIL]→ generate_ch1(재생성)             └[FAIL]→ ...
"""

from typing import TypedDict, List, Optional, Annotated
from operator import add
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.nodes.resolver import company_resolver, human_confirm
from graph.nodes.keywords import keyword_generator
from graph.nodes.news_agent import news_agent
from graph.nodes.ip_agent import ip_agent
from graph.nodes.finance_agent import finance_agent
from graph.nodes.cross_validate import cross_validator
from graph.nodes.reporter import chapter_writer, executive_summary, build_refs

MAX_RETRIES = 1  # 챕터당 최대 재시도 횟수


# ── State 정의 ────────────────────────────────────────────────────────────────
class AnalysisState(TypedDict):
    # 입력
    business_field: str
    query_name: str
    technology: str
    # 기업 해석
    company_candidates: list
    confirmed_company: Optional[dict]
    keywords: list
    # 병렬 수집
    news: list
    patents: list
    finance: dict
    # 교차 검증
    cross_validation: dict
    # 오케스트레이터 상태
    data_source: str
    fmp_data: dict
    tavily_news: list
    patent_records: list
    is_subsidiary: bool
    parent_company_kr: str
    # 챕터 생성
    ch1: str
    ch2: str
    ch3: str
    exec_summary: str
    # 리뷰 루프
    ch1_feedback: str
    ch1_ok: bool
    ch1_retries: int
    ch2_feedback: str
    ch2_ok: bool
    ch2_retries: int
    ch3_feedback: str
    ch3_ok: bool
    ch3_retries: int
    # 최종
    all_refs: str
    final_report_html: str
    # 메타
    errors: Annotated[list, add]
    log_callback: object   # callable
    check_cancel: object   # callable


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────
def _extract_feedback(llm_output: str) -> tuple[bool, str]:
    """LLM 출력에서 PASS/FAIL 판정 및 피드백 추출."""
    upper = llm_output.upper()
    is_pass = upper.startswith("PASS") or "PASS" in upper[:30]
    feedback = "" if is_pass else llm_output.strip()
    return is_pass, feedback


def _log(state: AnalysisState, msg: str):
    cb = state.get("log_callback")
    if callable(cb):
        cb(msg)
    else:
        print(msg)


def _check_cancel(state: AnalysisState):
    cc = state.get("check_cancel")
    if callable(cc):
        cc()


# ── 전처리 노드 (LangGraph 진입 전 수행되는 단계를 그래프 내 래핑) ────────────
def node_data_collection(state: AnalysisState) -> dict:
    """keywords → [news ∥ ip ∥ finance] fan-out 이후 fan-in 결과를 하나로 모은다."""
    _check_cancel(state)
    _log(state, "[Orchestrator] 멀티소스 데이터 수집 완료 — 오케스트레이션 시작")
    return {}


# ── Chapter 1 노드 ────────────────────────────────────────────────────────────
def node_generate_ch1(state: AnalysisState) -> dict:
    from graph.nodes.reporter import generate_chapter1
    _check_cancel(state)
    retries = state.get("ch1_retries", 0)
    feedback = state.get("ch1_feedback", "") if retries > 0 else ""
    label = "수정안" if retries > 0 else "초안"
    _log(state, f"[Orchestrator] Chapter 1 (기업·재무 개요) {label} 생성 중…")

    ch1 = generate_chapter1(
        company=state.get("confirmed_company", {}).get("name", state["query_name"]),
        fmp_data=state.get("fmp_data", {}),
        finance=state.get("finance", {}),
        news=state.get("news", []),
        data_source=state.get("data_source", "FMP"),
        is_subsidiary=state.get("is_subsidiary", False),
        parent_company_kr=state.get("parent_company_kr", ""),
        feedback=feedback,
    )
    return {"ch1": ch1}


def node_review_ch1(state: AnalysisState) -> dict:
    from graph.nodes.reporter import review_chapter
    _check_cancel(state)
    _log(state, "[Orchestrator] Chapter 1 품질 검토 중…")
    retries = state.get("ch1_retries", 0)
    if retries >= MAX_RETRIES:
        _log(state, "[Orchestrator] Chapter 1 통과")
        return {"ch1_ok": True, "ch1_feedback": "최대 재시도 도달, 통과", "ch1_retries": retries + 1}

    raw = review_chapter(
        chapter_num=1,
        company=state.get("confirmed_company", {}).get("name", state["query_name"]),
        technology=state.get("technology", ""),
        content=state["ch1"],
        fmp_data=state.get("fmp_data", {}),
        finance=state.get("finance", {}),
        data_source=state.get("data_source", "FMP"),
    )
    is_pass, feedback = _extract_feedback(raw)
    if is_pass:
        _log(state, "[Orchestrator] Chapter 1 통과")
    else:
        _log(state, f"[Orchestrator] Chapter 1 불통 — 재생성")
    return {"ch1_ok": is_pass, "ch1_feedback": feedback, "ch1_retries": retries + 1}


def _route_ch1(state: AnalysisState) -> str:
    return "generate_ch2" if state.get("ch1_ok") else "generate_ch1"


# ── Chapter 2 노드 ────────────────────────────────────────────────────────────
def node_generate_ch2(state: AnalysisState) -> dict:
    from graph.nodes.reporter import generate_chapter2
    _check_cancel(state)
    retries = state.get("ch2_retries", 0)
    feedback = state.get("ch2_feedback", "") if retries > 0 else ""
    label = "수정안" if retries > 0 else "초안"
    _log(state, f"[Orchestrator] Chapter 2 (산업 동향) {label} 생성 중…")

    ch2 = generate_chapter2(
        company=state.get("confirmed_company", {}).get("name", state["query_name"]),
        business_field=state.get("business_field", ""),
        technology=state.get("technology", ""),
        fmp_data=state.get("fmp_data", {}),
        finance=state.get("finance", {}),
        news=state.get("news", []),
        ch1=state.get("ch1", ""),
        cross_validation=state.get("cross_validation", {}),
        data_source=state.get("data_source", "FMP"),
        feedback=feedback,
    )
    return {"ch2": ch2}


def node_review_ch2(state: AnalysisState) -> dict:
    from graph.nodes.reporter import review_chapter
    _check_cancel(state)
    _log(state, "[Orchestrator] Chapter 2 품질 검토 중…")
    retries = state.get("ch2_retries", 0)
    if retries >= MAX_RETRIES:
        _log(state, "[Orchestrator] Chapter 2 통과")
        return {"ch2_ok": True, "ch2_feedback": "최대 재시도 도달, 통과", "ch2_retries": retries + 1}

    raw = review_chapter(
        chapter_num=2,
        company=state.get("confirmed_company", {}).get("name", state["query_name"]),
        technology=state.get("technology", ""),
        content=state["ch2"],
        fmp_data=state.get("fmp_data", {}),
        finance=state.get("finance", {}),
        data_source=state.get("data_source", "FMP"),
        ch1=state.get("ch1", ""),
    )
    is_pass, feedback = _extract_feedback(raw)
    if is_pass:
        _log(state, "[Orchestrator] Chapter 2 통과")
    else:
        _log(state, f"[Orchestrator] Chapter 2 불통 — 재생성")
    return {"ch2_ok": is_pass, "ch2_feedback": feedback, "ch2_retries": retries + 1}


def _route_ch2(state: AnalysisState) -> str:
    return "generate_ch3" if state.get("ch2_ok") else "generate_ch2"


# ── Chapter 3 노드 ────────────────────────────────────────────────────────────
def node_generate_ch3(state: AnalysisState) -> dict:
    from graph.nodes.reporter import generate_chapter3
    _check_cancel(state)
    retries = state.get("ch3_retries", 0)
    feedback = state.get("ch3_feedback", "") if retries > 0 else ""
    label = "수정안" if retries > 0 else "초안"
    _log(state, f"[Orchestrator] Chapter 3 (기술·특허 평가) {label} 생성 중…")

    ch3 = generate_chapter3(
        company=state.get("confirmed_company", {}).get("name", state["query_name"]),
        business_field=state.get("business_field", ""),
        technology=state.get("technology", ""),
        fmp_data=state.get("fmp_data", {}),
        finance=state.get("finance", {}),
        ch1=state.get("ch1", ""),
        ch2=state.get("ch2", ""),
        patents=state.get("patents", []),
        patent_records=state.get("patent_records", []),
        cross_validation=state.get("cross_validation", {}),
        data_source=state.get("data_source", "FMP"),
        feedback=feedback,
    )
    return {"ch3": ch3}


def node_review_ch3(state: AnalysisState) -> dict:
    from graph.nodes.reporter import review_chapter
    _check_cancel(state)
    _log(state, "[Orchestrator] Chapter 3 품질 검토 중…")
    retries = state.get("ch3_retries", 0)
    if retries >= MAX_RETRIES:
        _log(state, "[Orchestrator] Chapter 3 통과")
        return {"ch3_ok": True, "ch3_feedback": "최대 재시도 도달, 통과", "ch3_retries": retries + 1}

    raw = review_chapter(
        chapter_num=3,
        company=state.get("confirmed_company", {}).get("name", state["query_name"]),
        technology=state.get("technology", ""),
        content=state["ch3"],
        fmp_data=state.get("fmp_data", {}),
        finance=state.get("finance", {}),
        data_source=state.get("data_source", "FMP"),
        ch1=state.get("ch1", ""),
        ch2=state.get("ch2", ""),
        patents=state.get("patents", []),
    )
    is_pass, feedback = _extract_feedback(raw)
    if is_pass:
        _log(state, "[Orchestrator] Chapter 3 통과")
    else:
        _log(state, f"[Orchestrator] Chapter 3 불통 — 재생성")
    return {"ch3_ok": is_pass, "ch3_feedback": feedback, "ch3_retries": retries + 1}


def _route_ch3(state: AnalysisState) -> str:
    return "generate_exec_summary" if state.get("ch3_ok") else "generate_ch3"


# ── Executive Summary 노드 ────────────────────────────────────────────────────
def node_generate_exec_summary(state: AnalysisState) -> dict:
    _check_cancel(state)
    _log(state, "[Orchestrator] Executive Summary 생성 중…")
    exec_sum = executive_summary(state)
    return {"exec_summary": exec_sum.get("exec_summary", "")}


# ── 레퍼런스 빌드 노드 ───────────────────────────────────────────────────────
def node_build_refs(state: AnalysisState) -> dict:
    _check_cancel(state)
    _log(state, "[Orchestrator] 최종 레퍼런스 통합 중…")
    result = build_refs(state)
    return result


# ── 그래프 구성 ───────────────────────────────────────────────────────────────
def build_graph() -> StateGraph:
    g = StateGraph(AnalysisState)

    # 전처리 & 데이터 수집 (기존 노드 재사용)
    g.add_node("resolver", company_resolver)
    g.add_node("confirm", human_confirm)
    g.add_node("keywords", keyword_generator)
    g.add_node("news", news_agent)
    g.add_node("ip", ip_agent)
    g.add_node("finance", finance_agent)
    g.add_node("cross", cross_validator)
    g.add_node("data_collected", node_data_collection)

    # 리포트 생성 루프 노드
    g.add_node("generate_ch1", node_generate_ch1)
    g.add_node("review_ch1",   node_review_ch1)
    g.add_node("generate_ch2", node_generate_ch2)
    g.add_node("review_ch2",   node_review_ch2)
    g.add_node("generate_ch3", node_generate_ch3)
    g.add_node("review_ch3",   node_review_ch3)
    g.add_node("generate_exec_summary", node_generate_exec_summary)
    g.add_node("build_refs",   node_build_refs)

    # 전처리 엣지
    g.set_entry_point("resolver")
    g.add_edge("resolver", "confirm")
    g.add_edge("confirm", "keywords")

    # fan-out: keywords → 3 에이전트 병렬
    g.add_edge("keywords", "news")
    g.add_edge("keywords", "ip")
    g.add_edge("keywords", "finance")

    # fan-in → cross → data_collected → 리포트 루프 진입
    g.add_edge(["news", "ip", "finance"], "cross")
    g.add_edge("cross", "data_collected")
    g.add_edge("data_collected", "generate_ch1")

    # Ch1 리뷰 루프
    g.add_edge("generate_ch1", "review_ch1")
    g.add_conditional_edges("review_ch1", _route_ch1, {
        "generate_ch2": "generate_ch2",
        "generate_ch1": "generate_ch1",
    })

    # Ch2 리뷰 루프
    g.add_edge("generate_ch2", "review_ch2")
    g.add_conditional_edges("review_ch2", _route_ch2, {
        "generate_ch3": "generate_ch3",
        "generate_ch2": "generate_ch2",
    })

    # Ch3 리뷰 루프
    g.add_edge("generate_ch3", "review_ch3")
    g.add_conditional_edges("review_ch3", _route_ch3, {
        "generate_exec_summary": "generate_exec_summary",
        "generate_ch3": "generate_ch3",
    })

    g.add_edge("generate_exec_summary", "build_refs")
    g.add_edge("build_refs", END)

    return g.compile(checkpointer=MemorySaver())


graph = build_graph()
