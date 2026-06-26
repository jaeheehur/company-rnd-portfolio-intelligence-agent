"""BigQuery Google Patents 공개셋 클라이언트.
Text2SQL이 생성한 SQL을 검증 후 실행. SELECT 전용 + LIMIT 강제.
"""
import re
from google.cloud import bigquery
import config

TABLE = config.BIGQUERY_PATENTS_TABLE

SCHEMA_HINT = f"""
TABLE `{TABLE}`:
  publication_number  STRING        -- 특허 공개번호 (고유 ID)
  title_localized     ARRAY<STRUCT<text STRING, language STRING>>
  abstract_localized  ARRAY<STRUCT<text STRING, language STRING>>
  assignee_harmonized ARRAY<STRUCT<name STRING, country_code STRING>>
  filing_date         INT64         -- YYYYMMDD 형식 (예: 20200315)
  ipc                 ARRAY<STRUCT<code STRING>>
  country_code        STRING        -- 출원 국가 (KR, US, JP, ...)

쿼리 작성 규칙:
- title/abstract 추출: (SELECT t.text FROM UNNEST(title_localized) t WHERE t.language = 'en' LIMIT 1)
- 출원일 필터 예시: filing_date BETWEEN 20150101 AND 20241231
- 출원인 검색: EXISTS(SELECT 1 FROM UNNEST(assignee_harmonized) a WHERE LOWER(a.name) LIKE '%keyword%')
- 반드시 LIMIT 50 이하 포함
- SELECT 문만 사용 (DML 금지)
"""

_SAFE_SQL = re.compile(r"^\s*SELECT\b", re.IGNORECASE)
_DANGEROUS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|CREATE|ALTER|MERGE|EXECUTE)\b",
    re.IGNORECASE,
)

_client = bigquery.Client(project=config.GOOGLE_CLOUD_PROJECT)


def _validate(sql: str) -> None:
    if not _SAFE_SQL.match(sql):
        raise ValueError("Text2SQL 보안: SELECT 문만 허용됩니다.")
    if _DANGEROUS.search(sql):
        raise ValueError("Text2SQL 보안: 위험한 SQL 키워드가 포함되어 있습니다.")


def _inject_limit(sql: str, max_rows: int = 50) -> str:
    sql = sql.rstrip().rstrip(";")
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql += f"\nLIMIT {max_rows}"
    return sql


def run_sql(sql: str) -> list[dict]:
    _validate(sql)
    sql = _inject_limit(sql)
    job = _client.query(sql)
    return [dict(row) for row in job.result()]
