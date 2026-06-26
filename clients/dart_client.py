"""DART OpenAPI 클라이언트. 국내(KR) 기업 재무·R&D 데이터 수집."""
import io
import zipfile
import xml.etree.ElementTree as ET
import datetime
from functools import lru_cache

import requests
import config
from graph.state import Candidate

DART_BASE = "https://opendart.fss.or.kr/api"


@lru_cache(maxsize=1)
def _load_corp_codes() -> dict[str, str]:
    """DART corp_code XML 캐싱 로드 (첫 호출 시 1회만 실행)."""
    url = f"{DART_BASE}/corpCode.xml?crtfc_key={config.DART_API_KEY}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        with z.open("CORPCODE.xml") as f:
            tree = ET.parse(f)
    return {
        corp.findtext("corp_name", ""): corp.findtext("corp_code", "")
        for corp in tree.getroot().findall("list")
        if corp.findtext("stock_code")  # 상장사만
    }


def find_corp(name: str) -> list[Candidate]:
    """기업명 부분 일치로 DART 후보 반환."""
    codes = _load_corp_codes()
    matches = [(n, c) for n, c in codes.items() if name in n][:5]
    return [
        Candidate(
            name=n,
            identifier=c,
            country="KR",
            score=1.0 if n == name else 0.7,
        )
        for n, c in matches
    ]


def get_financials(corp_code: str, years: int = 5) -> dict:
    """DART 단일회사 재무제표 API. 매출액·R&D비 5개년 조회."""
    current_year = datetime.date.today().year
    revenue, rnd, year_list = [], [], []

    for y in range(current_year - years, current_year):
        params = {
            "crtfc_key": config.DART_API_KEY,
            "corp_code": corp_code,
            "bsns_year": str(y),
            "reprt_code": "11011",  # 사업보고서
            "fs_div": "CFS",        # 연결재무제표
        }
        resp = requests.get(f"{DART_BASE}/fnlttSinglAcnt.json", params=params, timeout=10)
        data = resp.json().get("list", [])

        rev = next(
            (float(d["thstrm_amount"].replace(",", "")) for d in data if d.get("account_nm") == "매출액"),
            0.0,
        )
        rnd_val = next(
            (float(d["thstrm_amount"].replace(",", "")) for d in data if "연구개발" in d.get("account_nm", "")),
            0.0,
        )
        year_list.append(y)
        revenue.append(rev)
        rnd.append(rnd_val)

    return {"years": year_list, "revenue": revenue, "rnd_expense": rnd, "currency": "KRW"}
