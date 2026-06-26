"""Streamlit 진입점.

흐름:
  입력 폼 → graph.stream() → interrupt(기업 확정) → Command(resume) → 진행상황 표시 → 리포트
"""
import uuid
import streamlit as st
from langgraph.types import Command
from graph.orchestrator import graph
from graph.state import IntelState

st.set_page_config(page_title="Competitor Intelligence Agent", layout="wide")
st.title("Competitor Intelligence Agent")

# --- Session state 초기화 ---
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "stage" not in st.session_state:
    st.session_state.stage = "input"     # input | confirm | done
if "candidates" not in st.session_state:
    st.session_state.candidates = []

_config = {"configurable": {"thread_id": st.session_state.thread_id}}

# ============================
# Stage 1: 입력 폼
# ============================
if st.session_state.stage == "input":
    with st.form("intel_form"):
        query_name = st.text_input("기업/기술명", placeholder="예: LG화학, NVIDIA")
        business_field = st.text_input("사업분야", placeholder="예: 배터리소재, AI반도체")
        submitted = st.form_submit_button("분석 시작")

    if submitted and query_name:
        initial_state = IntelState(
            business_field=business_field,
            query_name=query_name,
            company_candidates=[],
            confirmed_company=None,
            keywords=[],
            news=[],
            patents=[],
            finance={},
            cross_validation={},
            chapters={},
            final_report_html="",
            errors=[],
        )
        with st.spinner("기업 후보 검색 중..."):
            for event in graph.stream(initial_state, _config, stream_mode="updates"):
                if "__interrupt__" in event:
                    interrupt_data = event["__interrupt__"][0].value
                    st.session_state.candidates = interrupt_data["candidates"]
                    st.session_state.stage = "confirm"
                    break
        st.rerun()

# ============================
# Stage 2: 기업 확정 (interrupt resume)
# ============================
elif st.session_state.stage == "confirm":
    st.subheader("분석 기업 확정")
    candidates = st.session_state.candidates

    if not candidates:
        st.error("후보 기업을 찾지 못했습니다. 다시 입력해주세요.")
        if st.button("처음으로"):
            st.session_state.stage = "input"
            st.rerun()
    else:
        options = {
            f"{c['name']}  ({c['country']})  — 관련도 {c['score']:.2f}": c
            for c in candidates
        }
        chosen_label = st.radio("후보 기업 선택", list(options.keys()))

        if st.button("확정 후 분석 시작", type="primary"):
            chosen = options[chosen_label]
            progress = st.progress(0, text="분석 시작...")
            steps = ["keywords", "news", "ip", "finance", "cross", "report", "summary"]
            completed: list[str] = []

            for event in graph.stream(Command(resume=chosen), _config, stream_mode="updates"):
                node = next(iter(event.keys()), "")
                if node in steps:
                    completed.append(node)
                    pct = int(len(completed) / len(steps) * 100)
                    label_map = {
                        "keywords": "키워드 생성", "news": "뉴스 수집",
                        "ip": "특허 분석 (Text2SQL)", "finance": "재무 조회",
                        "cross": "교차검증", "report": "챕터 작성", "summary": "최종 요약",
                    }
                    progress.progress(pct, text=f"{label_map.get(node, node)} 완료...")
                    # 에러 표시
                    node_state = event.get(node, {})
                    for err in node_state.get("errors", []):
                        st.warning(err)

            progress.progress(100, text="분석 완료!")
            st.session_state.stage = "done"
            st.rerun()

# ============================
# Stage 3: 결과 표시
# ============================
elif st.session_state.stage == "done":
    final = graph.get_state(_config).values

    company_name = final.get("confirmed_company", {}).get("name", "")
    st.success(f"**{company_name}** 분석 완료")

    col1, col2, col3 = st.columns(3)
    col1.metric("수집 뉴스", len(final.get("news", [])))
    col2.metric("분석 특허", len(final.get("patents", [])))
    col3.metric("재무 데이터 연도", len(final.get("finance", {}).get("years", [])))

    st.subheader("Executive Summary")
    cross = final.get("cross_validation", {})
    st.info(cross.get("summary", ""))

    st.subheader("최종 리포트")
    html = final.get("final_report_html", "")
    if html:
        st.components.v1.html(html, height=900, scrolling=True)
        st.download_button(
            "리포트 다운로드 (.html)",
            data=html,
            file_name=f"intel_{company_name}.html",
            mime="text/html",
        )

    if st.button("새 분석 시작"):
        for key in ["thread_id", "stage", "candidates"]:
            st.session_state.pop(key, None)
        st.rerun()
