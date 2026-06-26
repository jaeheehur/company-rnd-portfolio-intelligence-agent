"""재무 에이전트: 국적에 따라 DART(KR) / yfinance(US) 분기 후 LLM 타임라인 해석."""
from clients import llm, dart_client, yfinance_client
from graph.state import IntelState, FinanceData


def finance_agent(state: IntelState) -> dict:
    company = state["confirmed_company"]
    country = company["country"]
    identifier = company["identifier"]

    if country == "KR":
        raw = dart_client.get_financials(identifier, years=5)
    else:
        raw = yfinance_client.get_financials(identifier, years=5)

    interpretation = _interpret(company["name"], raw)

    finance = FinanceData(
        years=raw["years"],
        revenue=raw["revenue"],
        rnd_expense=raw["rnd_expense"],
        currency=raw["currency"],
        interpretation=interpretation,
    )
    return {"finance": finance}


def _interpret(company_name: str, raw: dict) -> str:
    prompt = f"""{company_name}의 5개년 재무 데이터를 분석하세요.

연도: {raw['years']}
매출액({raw['currency']}): {raw['revenue']}
R&D 비용({raw['currency']}): {raw['rnd_expense']}

분석 관점:
1. 매출 성장 추세 (CAGR 포함)
2. R&D 집약도 변화 (R&D/매출 비율)
3. 주요 변곡점과 전략적 의미
4. 기술 투자 방향성 시그널

3-4문장으로 간결하게 서술하세요."""
    return llm.chat(prompt)
