"""IP 에이전트: Text2SQL → BigQuery → 출원인 정규화 → cosine re-rank → TRL/CRL/4D 분석.

흐름:
  1. LLM이 키워드 + 출원인 조건으로 BigQuery SQL 생성 (SCHEMA_HINT 주입)
  2. bigquery_client.run_sql()로 실행 (SELECT 전용 + LIMIT 강제)
  3. LLM few-shot으로 출원인명 변형 통합 (assignee_harmonized 보완)
  4. Gemini 임베딩 cosine similarity re-rank → Top 20
  5. 특허별 TRL + CRL + 4-Dimension 분석
"""
import numpy as np
from clients import llm, bigquery_client
from graph.state import IntelState, Patent


def ip_agent(state: IntelState) -> dict:
    company = state["confirmed_company"]["name"]
    keywords = state["keywords"]

    # 1. Text2SQL
    sql = _generate_sql(company, keywords)

    # 2. BigQuery 실행
    try:
        rows = bigquery_client.run_sql(sql)
    except Exception as e:
        return {"patents": [], "errors": [f"IP Agent BigQuery 오류: {e}"]}

    if not rows:
        return {"patents": [], "errors": [f"IP Agent: '{company}' 특허 검색 결과 없음"]}

    # 3. 출원인명 정규화
    rows = _normalize_assignees(rows, company)

    # 4. Cosine re-rank → Top 20
    query_text = f"{company} {' '.join(keywords[:5])}"
    rows = _rerank(rows, query_text)[:20]

    # 5. TRL/CRL/4D 분석
    patents = [_analyze_patent(row) for row in rows]

    return {"patents": patents}


def _generate_sql(company: str, keywords: list[str]) -> str:
    kw_conditions = " OR ".join(
        f"LOWER(t.text) LIKE '%{k.lower()}%'" for k in keywords[:8]
    )
    prompt = f"""Google Patents BigQuery 공개셋에서 특허를 검색하는 SQL을 작성하세요.

스키마 및 규칙:
{bigquery_client.SCHEMA_HINT}

검색 조건:
- 출원인: "{company}" 관련 (assignee_harmonized의 name 필드)
- 키워드: title 또는 abstract에 다음 중 하나 포함: {keywords[:8]}
- 출원일: 최근 10년 이내

SELECT 컬럼 (아래 형식 그대로):
  publication_number,
  (SELECT t.text FROM UNNEST(title_localized) t WHERE t.language = 'en' LIMIT 1) AS title_en,
  (SELECT a.text FROM UNNEST(abstract_localized) a WHERE a.language = 'en' LIMIT 1) AS abstract_en,
  (SELECT ag.name FROM UNNEST(assignee_harmonized) ag LIMIT 1) AS assignee,
  filing_date,
  (SELECT i.code FROM UNNEST(ipc) i LIMIT 1) AS ipc_primary,
  country_code

SQL만 반환하세요. 설명 없이."""
    return llm.chat(prompt)


def _normalize_assignees(rows: list[dict], target: str) -> list[dict]:
    """LLM few-shot으로 출원인명 변형(약칭·영문·한글)을 통합."""
    unique_assignees = list({r.get("assignee", "") for r in rows if r.get("assignee")})
    if len(unique_assignees) <= 1:
        return rows

    prompt = f"""다음 특허 출원인 이름들 중 '{target}'와 동일한 법인으로 판단되는 것을 고르세요.
예시: "LG Chem" = "LG화학" = "LG CHEM LTD" = "엘지화학"

출원인 목록: {unique_assignees}

JSON으로 반환: {{"same_entity": ["출원인A", "출원인B", ...]}}"""

    result = llm.structured(prompt, dict)
    same_set = set(result.get("same_entity", []))
    if not same_set:
        return rows
    return [r for r in rows if r.get("assignee", "") in same_set]


def _rerank(rows: list[dict], query_text: str) -> list[dict]:
    """Gemini 임베딩 기반 cosine similarity re-rank."""
    query_emb = np.array(llm.embed(query_text))

    scored = []
    for row in rows:
        doc_text = f"{row.get('title_en', '')} {row.get('abstract_en', '')[:300]}"
        doc_emb = np.array(llm.embed(doc_text))
        norm = np.linalg.norm(query_emb) * np.linalg.norm(doc_emb)
        score = float(np.dot(query_emb, doc_emb) / (norm + 1e-9))
        scored.append({**row, "_similarity": score})

    return sorted(scored, key=lambda x: x["_similarity"], reverse=True)


def _analyze_patent(row: dict) -> Patent:
    """특허 1건 TRL, CRL, 4-Dimension 분석."""
    prompt = f"""다음 특허를 분석하세요.
제목: {row.get('title_en', '')}
초록: {row.get('abstract_en', '')[:600]}
IPC: {row.get('ipc_primary', '')}

JSON으로 반환:
{{
  "trl": 1-9,
  "crl": 1-9,
  "analysis_4d": {{
    "problem": "해결하는 문제",
    "approach": "기술적 접근방법",
    "impact": "기대 효과",
    "differentiation": "경쟁 차별성"
  }}
}}"""
    analysis = llm.structured(prompt, dict)

    return Patent(
        publication_number=row.get("publication_number", ""),
        title=row.get("title_en", ""),
        abstract=row.get("abstract_en", ""),
        applicant=row.get("assignee", ""),
        filing_year=int(str(row.get("filing_date", "20000101"))[:4]),
        ipc_codes=[row.get("ipc_primary", "")] if row.get("ipc_primary") else [],
        trl=int(analysis.get("trl", 0)),
        crl=int(analysis.get("crl", 0)),
        analysis_4d=analysis.get("analysis_4d", {}),
        similarity_score=row.get("_similarity", 0.0),
    )
