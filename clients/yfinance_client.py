"""yfinance 클라이언트. 해외(US) 기업 재무·R&D 데이터 수집. API키 불필요."""
import yfinance as yf
from graph.state import Candidate


def find_ticker(name: str) -> list[Candidate]:
    """티커/회사명으로 yfinance 기업 정보 검증."""
    ticker = yf.Ticker(name.upper())
    info = ticker.info
    if info.get("symbol"):
        return [
            Candidate(
                name=info.get("longName", name),
                identifier=info["symbol"],
                country="US",
                score=1.0,
            )
        ]
    return []


def get_financials(ticker: str, years: int = 5) -> dict:
    """yfinance 손익계산서에서 매출·R&D비 연도별 추출."""
    t = yf.Ticker(ticker)
    income = t.financials  # columns = 회계연도 (최신순)

    cols = list(income.columns)[:years]

    revenue, rnd, year_list = [], [], []
    for col in cols:
        rev = income.loc["Total Revenue", col] if "Total Revenue" in income.index else 0.0
        rnd_val = income.loc["Research And Development", col] if "Research And Development" in income.index else 0.0
        revenue.append(float(rev) if rev == rev else 0.0)  # NaN 방어
        rnd.append(float(rnd_val) if rnd_val == rnd_val else 0.0)
        year_list.append(col.year)

    return {"years": year_list, "revenue": revenue, "rnd_expense": rnd, "currency": "USD"}
