"""리포트 생성 노드: 3챕터 작성 + executive summary + HTML 조립."""
import os
from datetime import date
from jinja2 import Environment, FileSystemLoader
from clients import llm
from graph.state import IntelState
import config

_env = Environment(loader=FileSystemLoader("templates"))


def chapter_writer(state: IntelState) -> dict:
    company = state["confirmed_company"]["name"]
    chapters = {
        "overview": _write_overview(company, state["finance"]),
        "industry": _write_industry(company, state["news"], state["cross_validation"]),
        "tech_eval": _write_tech_eval(company, state["patents"], state["cross_validation"]),
    }
    return {"chapters": chapters}


def executive_summary(state: IntelState) -> dict:
    company = state["confirmed_company"]["name"]
    chapters = state["chapters"]

    prompt = f"""{company} 경쟁사 분석 3개 챕터의 핵심을 통합 요약하세요.

[기업 개요]
{chapters['overview'][:600]}

[산업 동향]
{chapters['industry'][:600]}

[기술 평가]
{chapters['tech_eval'][:600]}

경영진 브리핑 수준의 요약 4-5문장. 수치 근거를 반드시 포함하세요."""

    summary = llm.chat(prompt)

    template = _env.get_template("report.html.j2")
    html = template.render(
        company=company,
        report_date=date.today().isoformat(),
        chapters=chapters,
        executive_summary=summary,
        cross_validation=state["cross_validation"],
        top_patents=state["patents"][:5],
        finance=state["finance"],
    )

    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    path = f"{config.REPORTS_DIR}/{company}_{date.today().isoformat()}.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    return {"final_report_html": html}


# --- 챕터별 작성 ---

def _write_overview(company: str, finance: dict) -> str:
    prompt = f"""{company} 기업 개요 챕터를 작성하세요.
재무 데이터: {finance}
포함 내용: 사업 영역, 재무 건전성, R&D 투자 기조. 300자 내외."""
    return llm.chat(prompt)


def _write_industry(company: str, news: list, cross: dict) -> str:
    news_lines = "\n".join(f"- {n['summary']}" for n in news[:5])
    prompt = f"""{company} 산업 동향 챕터를 작성하세요.
주요 뉴스:
{news_lines}
교차분석 인사이트: {cross.get('news_patent_alignment', '')}
포함 내용: 시장 동향, 경쟁 이슈, 규제 환경. 300자 내외."""
    return llm.chat(prompt)


def _write_tech_eval(company: str, patents: list, cross: dict) -> str:
    patent_lines = "\n".join(
        f"- [TRL {p['trl']}/CRL {p['crl']}] {p['title']}: {p['analysis_4d'].get('differentiation', '')}"
        for p in patents[:3]
    )
    prompt = f"""{company} 기술 평가 챕터를 작성하세요.
핵심 특허:
{patent_lines}
상용화 시그널: {cross.get('commercialization_signal', '')}
포함 내용: 기술 포트폴리오, TRL/CRL 분포, 경쟁 차별화 포인트. 300자 내외."""
    return llm.chat(prompt)
