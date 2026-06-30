# 🕵️ Company R&D Portfolio Intelligence Agent

> 타겟 기업의 **특허 · 재무 · 뉴스**를 자동 수집·분석하고, 3개 챕터 + Executive Summary로 구성된 통합 경쟁사 분석 리포트를 자동 생성하는 Multi-Agent 시스템

## 📌 개요

기존에 2주 이상 소요되던 경쟁사 R&D 리서치를 **10분 이내**로 단축합니다.  
사업 담당자가 기업명과 사업 분야를 입력하면, LangGraph 기반 Multi-Agent 파이프라인이 국내외 공개 데이터를 병렬로 수집하고, LLM이 교차 분석하여 경영진 브리핑 수준의 HTML 리포트를 자동 생성합니다.

---

## 🏗️ 시스템 아키텍처

```
사용자 입력 (기업명 + 사업분야)
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│                   LangGraph Orchestrator                 │
│                                                         │
│  [1] resolver ──→ human_confirm (interrupt)             │
│                         │                               │
│  [2]            keyword_generator                       │
│                         │                               │
│              ┌──────────┼──────────┐                    │
│  [3]     news_agent  ip_agent  finance_agent  (병렬)   │
│              └──────────┼──────────┘                    │
│                         │                               │
│  [4]            cross_validator                         │
│                         │                               │
│  [5]  chapter_writer → review loop (PASS/FAIL retry)   │
│       ch1 → ch2 → ch3                                   │
│                         │                               │
│  [6]   executive_summary → build_refs → HTML 리포트     │
└─────────────────────────────────────────────────────────┘
        │
        ▼
   Flask Web App (결과 확인 / HTML 다운로드)
```

---

## 🤖 Agent 구성

| Agent | 역할 | 데이터 소스 |
|---|---|---|
| **Company Resolver** | 기업명 해석 → 국내/해외 판별 → 후보 LLM 재랭킹 | DART API, yfinance |
| **Keyword Generator** | 기업·사업분야 기반 검색 키워드 15~20개 생성 (한/영 혼합) | Gemini LLM |
| **News Agent** | Tavily 검색 → 중복 제거 → 임팩트 점수 산정 → 요약 | Tavily Search API |
| **IP Agent** | Text2SQL → BigQuery 특허 검색 → Cosine re-rank → TRL/CRL/4D 분석 | Google Patents (BigQuery Public Dataset) |
| **Finance Agent** | 국적 분기(KR/US) → 최근 5개년 재무 데이터 → LLM 타임라인 해석 | DART OpenAPI, yfinance |
| **Cross Validator** | 특허·재무·뉴스 시계열 교차 분석 → 전략적 인사이트 도출 | 위 3개 Agent 결과 통합 |
| **Chapter Writer** | 3개 챕터(기업개요/산업동향/기술평가) 작성 + PASS/FAIL 리뷰 루프 | 전체 수집 데이터 |
| **Executive Summary** | 3개 챕터 핵심 통합 요약 (경영진 브리핑 수준) | 챕터 결과 |

---

## ⚙️ 주요 기술 특징

### Multi-Agent Orchestration (LangGraph)
- `StateGraph` 기반으로 노드 간 상태 전파
- `MemorySaver` checkpoint로 interrupt/resume 지원
- News / IP / Finance 에이전트 **병렬 실행**으로 처리 시간 최소화

### Human-in-the-Loop
- 동명이의 기업 존재 시 **자동 interrupt** → 사용자가 후보 중 선택 후 분석 재개

### IP 분석 (Text2SQL + BigQuery)
- LLM이 스키마 힌트를 참조하여 BigQuery SQL 자동 생성
- SELECT 전용 + LIMIT 강제로 안전성 확보
- **Gemini 임베딩** 기반 cosine similarity re-rank → Top 20 특허 선별
- 특허별 **TRL / CRL / 4-Dimension** (문제·접근법·임팩트·차별성) 분석

### 재무 분석 (이중 소스)
- 국내 기업: **DART OpenAPI** (사업보고서 기반)
- 해외 기업: **yfinance** (증권 데이터)
- 최근 5개년 매출 / R&D 투자액 트렌드 자동 해석

### LLM Review Loop
- 각 챕터 생성 후 **LLM Self-Review** (PASS/FAIL 판정)
- FAIL 시 피드백과 함께 자동 재생성 (최대 1회 retry)

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|---|---|
| **LLM** | Google Gemini API |
| **Embedding** | Gemini Embedding (cosine re-rank) |
| **Agent Framework** | LangGraph |
| **Web Framework** | Flask |
| **특허 DB** | Google BigQuery Public Dataset (Google Patents) |
| **재무 (국내)** | DART OpenAPI |
| **재무 (해외)** | yfinance |
| **뉴스 검색** | Tavily Search API |
| **템플릿** | Jinja2 |

---

## 📁 프로젝트 구조

```
company-rnd-portfolio-intelligence-agent/
├── app.py                          # Flask 진입점 (라우터)
├── config.py                       # 환경변수 로드 및 설정
├── .env.example                    # 환경변수 예시
│
├── graph/
│   ├── orchestrator.py             # LangGraph StateGraph 정의 및 엣지 연결
│   ├── state.py                    # 공유 상태 스키마 (IntelState, Candidate, Patent 등)
│   └── nodes/
│       ├── resolver.py             # 기업 해석 + human confirm (interrupt)
│       ├── keywords.py             # 검색 키워드 생성
│       ├── news_agent.py           # 뉴스 수집 및 요약
│       ├── ip_agent.py             # 특허 검색 및 분석
│       ├── finance_agent.py        # 재무 데이터 수집 및 해석
│       ├── cross_validate.py       # 다중 소스 교차 분석
│       └── reporter.py             # 챕터 작성 + Executive Summary + HTML 조립
│
├── clients/
│   ├── __init__.py
│   ├── bigquery_client.py          # BigQuery Google Patents 클라이언트 (Text2SQL)
│   ├── dart_client.py              # DART OpenAPI 클라이언트
│   ├── yfinance_client.py          # yfinance 클라이언트
│   └── tavily_client.py            # Tavily Search 클라이언트
│
└── templates/
    ├── index.html                  # 입력 폼
    ├── confirm.html                # 기업 후보 선택 화면
    ├── result.html                 # 최종 리포트 표시
    └── report.html.j2              # 다운로드용 HTML 리포트 템플릿
```

---

## 🚀 시작하기

### 1. 환경 설정

```bash
git clone https://github.com/jaeheehur/company-rnd-portfolio-intelligence-agent.git
cd company-rnd-portfolio-intelligence-agent

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env.example`을 복사하여 `.env`를 만들고 값을 채워주세요.

```bash
cp .env.example .env
```

```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_CLOUD_PROJECT=your_gcp_project_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
DART_API_KEY=your_dart_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
FLASK_SECRET_KEY=your_flask_secret_key
```

### 3. GCP 설정

BigQuery를 사용하려면 GCP 서비스 계정에 다음 권한이 필요합니다:
- `BigQuery Data Viewer`
- `BigQuery Job User`

### 4. 실행

```bash
python app.py
```

브라우저에서 `http://localhost:5000` 으로 접속합니다.

---

## 📊 사용 흐름

```
1. 기업명 + 사업분야 입력
        ↓
2. (동명이의 기업 존재 시) 후보 목록에서 분석 대상 선택
        ↓
3. 병렬 데이터 수집 (뉴스 / 특허 / 재무) — 약 2~5분
        ↓
4. 교차 분석 → 3개 챕터 작성 → Executive Summary 생성
        ↓
5. 브라우저에서 리포트 확인 / HTML 파일 다운로드
```

---

## 🌐 Flask API Endpoints

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/` | 입력 폼 |
| `POST` | `/analyze` | 분석 실행 (그래프 시작) |
| `GET` | `/confirm` | 기업 후보 선택 화면 |
| `POST` | `/confirm` | 기업 선택 → 분석 재개 |
| `GET` | `/result` | 최종 리포트 표시 |
| `GET` | `/download` | HTML 리포트 다운로드 |
| `GET` | `/reset` | 세션 초기화 |

---

## 📋 리포트 구성

생성되는 분석 리포트는 다음 4개 섹션으로 구성됩니다:

1. **Executive Summary** — 핵심 인사이트 4~5문장 (수치 근거 포함)
2. **Chapter 1: 기업 개요** — 재무 현황, R&D 투자 트렌드, 사업 구조
3. **Chapter 2: 산업 동향** — 최근 뉴스 기반 시장 동향 및 전략 분석
4. **Chapter 3: 기술 평가** — 특허 포트폴리오, TRL/CRL 분석, 기술 차별성

---

## ⚠️ 주의사항

- BigQuery Google Patents 공개셋 쿼리 비용이 발생할 수 있습니다 (첫 1TB/월 무료).
- DART API는 국내 상장·등록 기업만 지원합니다.
- LLM API 호출 비용은 기업 복잡도에 따라 달라집니다.
- 생성된 리포트는 공개 데이터 기반이므로, 비공개 정보는 포함되지 않습니다.

---

## 👤 Author

**Jaehee Hur** · [Portfolio](https://jaeheehur.github.io/portfolio)
