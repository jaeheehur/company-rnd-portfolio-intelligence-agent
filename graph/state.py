from typing import TypedDict, Literal, Optional, Annotated
from operator import add


class Candidate(TypedDict):
    name: str
    identifier: str       # DART corp_code 또는 주식 티커
    country: Literal["KR", "US", "OTHER"]
    score: float


class Patent(TypedDict):
    publication_number: str
    title: str
    abstract: str
    applicant: str
    filing_year: int
    ipc_codes: list[str]
    trl: int              # Technology Readiness Level 1-9
    crl: int              # Commercial Readiness Level 1-9
    analysis_4d: dict     # {problem, approach, impact, differentiation}
    similarity_score: float


class NewsItem(TypedDict):
    title: str
    url: str
    date: str
    summary: str
    impact_score: float


class FinanceData(TypedDict):
    years: list[int]
    revenue: list[float]
    rnd_expense: list[float]
    currency: str
    interpretation: str


class IntelState(TypedDict):
    # 입력
    business_field: str
    query_name: str
    # 기업 해석
    company_candidates: list[Candidate]
    confirmed_company: Optional[Candidate]
    keywords: list[str]
    # 병렬 수집 (에이전트별 독립 키 → reducer 충돌 없음)
    news: list[NewsItem]
    patents: list[Patent]
    finance: FinanceData
    # 산출
    cross_validation: dict
    chapters: dict         # {overview: str, industry: str, tech_eval: str}
    final_report_html: str
    # 메타
    errors: Annotated[list[str], add]   # 여러 노드에서 누적 가능
