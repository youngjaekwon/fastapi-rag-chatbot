RAG 챗봇 PRD (FastAPI + PostgreSQL pgvector + LangGraph/LangChain + WebSocket)

⸻

1. 목표 및 범위
   • 사용자 가치: 사내 문서를 업로드하여 질문-답변을 빠르게 얻고, 근거(출처)와 함께 스트리밍으로 답변을 확인.
   • 범위(In Scope)
   • 문서 업로드(API) → 청킹/임베딩 → pgvector 저장 → 검색 → RAG 답변 → WebSocket 스트리밍.
   • 세션/대화 로그 저장, 인용(citation) 노출.
   • 최소 권한 인증(토큰 기반)과 기본 레이트 리미트.
   • Docker Compose로 로컬 1명~수명 사용 가능한 배포.
   • 비범위(Out of Scope)
   • 정교한 UI(Web): 이번 스프린트는 간단한 HTML/JS 예제 클라이언트만.
   • 멀티 테넌시, 다국어 번역, 복잡한 권한 모델.

⸻

2. 성공 기준 (Acceptance Criteria)
   • docker compose up -d만으로 API/DB 구동.
   • POST /ingest로 PDF/TXT 업로드 시 자동 청킹·임베딩·저장, 1분 내 처리(10MB 이하 기준).
   • ws://.../ws/chat 접속 후 사용자 질문을 보내면 2초 내 첫 토큰 스트리밍 시작, 최종 응답에 출처 2건 이상 포함(top-k=4, 필터링 결과에 따라 다를 수 있음).
   • GET /healthz, GET /metrics 제공.
   • 대화/세션/검색 로그가 PostgreSQL에 남고 재현 가능.

⸻

3. 주요 사용자 시나리오
   1. 지식 업로드: 운영자가 PDF 3개 업로드 → 자동 청킹/임베딩 → 색인 완료.
   2. 질의응답: 사용자가 “반환 정책 요약?” 질문 → 토큰 스트리밍 → 최종 답변 + 출처 링크.
   3. 검색 실패: 답변 자신감 낮음(스코어 낮음) → “지식 부족” 가드레일 메시지.
   4. 세션 유지: 같은 세션에서 후속 질문 시 직전 문맥(요약) 반영.

⸻

4. 시스템 아키텍처 (개요)
   • FastAPI: REST(업로드/상태/메트릭) + WebSocket(채팅 스트리밍)
   • PostgreSQL + pgvector: 문서 청킹 및 임베딩 저장/검색
   • LangGraph(권장) / LangChain: 그래프형 RAG 파이프라인
   • 임베딩/LLM: 기본은 OpenAI/Azure OpenAI API 사용(대체: 로컬 vLLM)
   • 옵저버빌리티: OpenTelemetry + Prometheus + Sentry(선택)

요청 흐름

Client → WebSocket(user_message)
→ RAG Graph: Retrieve(벡터검색) → (선택)Rerank → Augment → LLM Call → Stream Tokens
→ Server → WebSocket(token|final|citations)

⸻

5. 기술 스택

필수
• Python 3.11, FastAPI, Uvicorn
• PostgreSQL 16 + pgvector
• LangGraph(권장) 또는 LangChain
• OpenAI(또는 Azure OpenAI) SDK
• WebSocket (FastAPI 내장) + 간단한 HTML/JS 데모 클라이언트
• Docker, Docker Compose

LLM 서빙 실전에서 함께 배워야 하는 스택(권장)
• 서빙 엔진: vLLM(로컬/자가호스팅), TGI(Alternatives)
• 관측/성능: OpenTelemetry 트레이싱, Prometheus/Grafana 메트릭, Sentry(에러)
• 성능 최적화: 토큰/요청 캐싱(서버·프롬프트 캐시), rate limiting(slowapi/Redis), 병렬 검색/MMR
• 보안: JWT 인증(예: AWS Cognito 연동), Secrets 관리(.env, Doppler 등), CORS/CSRF 기본
• 데이터 파이프라인: Unstructured/PyPDF 로더, Chunking 전략(
by tokens/headers), 메타데이터 추출
• 품질/가드레일: Moderation, PII 마스킹(Presidio), Hallucination 체크(스코어 문턱)
• 테스트/CI: pytest, ruff, mypy, pre-commit, GitHub Actions
• 배포: Nginx/Traefik(리버스 프록시), 컨테이너 베스트 프랙티스

⸻

6. API & 프로토콜 설계

REST
• POST /ingest
• Form-Data: file (pdf/txt/md)
• Query: collection(기본값 default), chunk_size(기본 800 토큰)
• 응답: {document_id, chunks, elapsed_ms}
• POST /chat/session
• Body: {user_id?, metadata?} → {session_id}
• GET /healthz / GET /metrics

WebSocket (/ws/chat?session_id=...)

Client → Server

{"type":"start","model":"gpt-4o-mini","stream":true}
{"type":"user_message","text":"반환 정책 요약해줘"}

Server → Client

{"type":"token","delta":"반환"}
{"type":"token","delta":" 정책은..."}
{"type":"citations","items":[{"chunk_id":123,"source":"filename.pdf#p3","score":0.82}]}
{"type":"final","message_id":456,"usage":{"prompt":523,"completion":211}}

에러: { "type":"error", "message":"..." }

⸻

7. 데이터 모델 (PostgreSQL + pgvector)

확장 및 스키마

CREATE EXTENSION IF NOT EXISTS vector;

-- 문서 원본
CREATE TABLE documents (
id BIGSERIAL PRIMARY KEY,
collection TEXT NOT NULL DEFAULT 'default',
source TEXT, -- 파일명/URL
metadata JSONB,
created_at TIMESTAMPTZ DEFAULT now()
);

-- 청크 + 임베딩 (임베딩 차원은 사용 모델에 맞게 수정: 1536/3072 등)
CREATE TABLE chunks (
id BIGSERIAL PRIMARY KEY,
document_id BIGINT REFERENCES documents(id) ON DELETE CASCADE,
content TEXT NOT NULL,
embedding VECTOR(1536) NOT NULL,
metadata JSONB,
created_at TIMESTAMPTZ DEFAULT now()
);

-- 벡터 인덱스 (코사인 유사도)
CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists=100);
CREATE INDEX ON chunks (document_id);
CREATE INDEX ON chunks USING gin ((metadata));

-- 세션/메시지/인용
CREATE TABLE sessions (
id UUID PRIMARY KEY,
user_id TEXT,
metadata JSONB,
created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE messages (
id BIGSERIAL PRIMARY KEY,
session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
role TEXT CHECK (role IN ('user','assistant','system')),
content TEXT NOT NULL,
usage_prompt INT,
usage_completion INT,
created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE citations (
id BIGSERIAL PRIMARY KEY,
message_id BIGINT REFERENCES messages(id) ON DELETE CASCADE,
chunk_id BIGINT REFERENCES chunks(id) ON DELETE SET NULL,
score REAL,
extra JSONB
);

⸻

8. 검색·RAG 설계
   • 임베딩 모델: 기본 text-embedding-3-small(1536차원) 또는 -large(3072). 대안: e5-large(로컬)
   • 검색: cosine similarity, top_k=4, min_score=0.75 문턱
   • MMR: 다양성 확보(선택)
   • 메타 필터: collection, doc_type, timestamp, tags 등
   • 컨텍스트 구성: 상위 n개 청크를 템플릿에 삽입, 토큰 가드(최대 context)
   • 가드레일: 스코어 낮으면 “정보 부족” 응답 + 업로드 유도

⸻

9. LangGraph(권장) 그래프 설계

노드 1. retrieve: 쿼리 임베딩 → pgvector 유사도 검색 → 상위 k 청크 반환 2. rerank(optional): (있다면) Cross-Encoder 또는 스코어 재정렬 3. augment: 청크 → 컨텍스트 패킹 + 시스템 프롬프트 구성 4. llm: 스트리밍 호출(WS로 토큰 중계) 5. record: messages, citations 저장

조건분기
• 검색 결과 스코어 < 문턱 → insufficient_knowledge 경로로 이동

오케스트레이션
• 세션 요약(길이 초과 시) 노드 추가 가능

⸻

10. 비기능 요구사항
    • 성능: 단일 노드에서 동시 20세션, p95 첫 토큰 < 2s(외부 LLM 기준)
    • 신뢰성: DB 트랜잭션/리트라이, 임베딩 배치 실패 재시도
    • 보안: JWT 베어러, CORS 허용 도메인 제한, 업로드 파일 확장자 화이트리스트
    • 관측성: /metrics(Prometheus), 트레이스(Otel), 구조적 로깅(JSON)

⸻

11. 테스트 전략
    • 단위: 청킹, 임베딩 호출 모킹, 검색 쿼리 빌더, 프롬프트 템플릿
    • 통합: 로컬 Postgres 컨테이너로 임베딩 더미 벡터 저장/검색
    • E2E: 업로드→질의→스트리밍→인용까지 시나리오 테스트
    • 부하: Locust로 동시 20세션, 응답/첫 토큰 지표 확인

⸻

12. 확장 과제(Stretch)
    • Reranker: bge-reranker-large, Cohere rerank 등
    • 세션 요약: 긴 대화에서 대화 요약 노드 추가
    • 도구 호출: 캘린더/DB/사내 API 호출 에이전트화
    • SSE 지원: WebSocket 병행/대체
    • 로컬 서빙: vLLM + Llama 3.1 8B/70B 로컬 파이프라인

⸻

13. 리스크 & 차선책
    • 외부 LLM 속도/가용성 → 첫 토큰 지연 발생 가능 → 프롬프트/컨텍스트 최소화, 타임아웃/리트라이 도입
    • 임베딩 비용 → 배치 처리 & 중복 방지 해시
    • PDF 파싱 품질 편차 → 헤더/섹션 기반 청킹으로 개선

⸻

14. 빠른 시작 체크리스트
    1.  Docker Desktop 실행 → docker compose up -d
    2.  POST /ingest로 샘플 PDF 업로드
    3.  /chat/session으로 세션 생성, /ws/chat 접속 후 질문
    4.  메트릭/로그로 성능 확인
