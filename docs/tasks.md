Fastapi-rag-chatbot Task List

대상: fastapi-rag-chatbot (FastAPI + PostgreSQL(pgvector) + LangGraph/LangChain + WebSocket) — 엔터프라이즈 MSA의 단일 서비스로 가정
형식: 태스크 ID / 설명 / 산출물 / 예상시간 / 담당 / 선행조건 / DoD(완료기준)

⸻

Day 0 (선택) — 사전 준비
• T0.1 리포 이름/브랜치 전략 확정
• 산출물: fastapi-rag-chatbot 리포 생성, 브랜치 전략 문서(docs/branching.md)
• 시간: 0.5h / 담당: TL
• 선행: 없음
• DoD: 기본 브랜치 보호, PR 템플릿/Codeowners 반영
• T0.2 CI 러너/레지스트리 접근성 확인
• 산출물: GHCR(or ECR) push 권한, 워크플로우 시크릿 세팅
• 시간: 0.5h / 담당: DevOps
• DoD: ghcr.io/... 접속/토큰 검증 로그 기록

⸻

Day 1 — 데이터 경로 완성 (총 8h)

1. 리포 셋업: FastAPI + Docker + Compose + 기본 품질 게이트 (2h)
   • T1.1 베이스 프로젝트 스캐폴드
   • 설명: apps/api, apps/worker, src/, migrations/, deployments/, docker/ 등 디렉토리 생성
   • 산출물: 기본 코드/빈 파일, pyproject.toml, Makefile, .pre-commit-config.yaml
   • 시간: 0.5h / 담당: BE
   • DoD: make setup 후 pre-commit 훅 동작
   • T1.2 Docker/Compose 스택 구성
   • 설명: postgres:16 + pgvector, api, worker 서비스 정의(개발용)
   • 산출물: docker/api.Dockerfile, docker/worker.Dockerfile, docker/compose.dev.yaml
   • 시간: 0.5h / 담당: BE/DevOps
   • DoD: docker compose -f docker/compose.dev.yaml up -d로 기동, API 8000 응답 확인
   • T1.3 품질/정적분석/테스트 베이스
   • 설명: ruff/mypy/pytest 설정, 샘플 테스트
   • 산출물: pytest.ini, mypy.ini, tests/unit/test_smoke.py
   • 시간: 0.5h / 담당: BE
   • DoD: make test 통과, CI에서 lint/test 성공
   • T1.4 Alembic 초기화 & pgvector 확장
   • 설명: DB 연결 설정, CREATE EXTENSION vector; 포함한 초기 마이그레이션
   • 산출물: migrations/versions/<ts>\_init.py
   • 시간: 0.5h / 담당: BE/DBA
   • 선행: DB 기동
   • DoD: make migrate로 스키마 적용

2. /ingest 구현: 업로드→청킹→임베딩→pgvector 저장 (3h)
   • T1.5 파일 업로드 API 스켈레톤
   • 설명: 입력 검증(확장자/크기), 비동기 저장 디렉토리
   • 산출물: apps/api/routes/ingest.py
   • 시간: 0.5h / 담당: BE
   • DoD: 10MB 이하 파일 업로드 200 응답
   • T1.6 파서/청킹 파이프라인
   • 설명: PDF/TXT 파싱 → 토큰/헤더 기반 청킹, 중복방지 해시
   • 산출물: adapters/embeddings/parser.py, rag/pipeline/chunking.py
   • 시간: 1h / 담당: BE
   • DoD: 샘플 PDF 3개에서 청크 생성 로그 확인
   • T1.7 임베딩 & 저장
   • 설명: OpenAI(또는 대체) 임베딩 호출, chunks(embedding vector) 저장
   • 산출물: adapters/embeddings/provider_openai.py, adapters/db/repository.py
   • 시간: 1h / 담당: BE
   • 선행: API key
   • DoD: 1분 내(10MB 기준) 저장 완료
   • T1.8 에러/리트라이/로그
   • 설명: HTTP/임베딩 실패 재시도, 구조적 로깅, 예외 매핑
   • 산출물: 공통 예외/로깅 미들웨어
   • 시간: 0.5h / 담당: BE
   • DoD: 실패 케이스에서 적절한 4xx/5xx 반환

3. 검색 쿼리, 인덱스 튜닝 (2h)
   • T1.9 벡터 인덱스 구성
   • 설명: ivfflat(lists 파라미터), 코사인 연산자 설정
   • 산출물: 마이그레이션 스크립트(인덱스 추가)
   • 시간: 0.5h / 담당: DBA
   • DoD: EXPLAIN에서 인덱스 사용 확인
   • T1.10 검색 모듈/파라미터화
   • 설명: top_k, min_score, MMR 옵션화
   • 산출물: adapters/search/vector_store.py
   • 시간: 1h / 담당: BE
   • DoD: 단위테스트로 다양한 파라미터 조합 검증
   • T1.11 쿼리 성능 검증
   • 설명: p95 검색시간 측정, VACUUM/ANALYZE 가이드 추가
   • 산출물: 성능 메모(docs/search_tuning.md)
   • 시간: 0.5h / 담당: BE/DBA
   • DoD: p95 < 100ms(로컬 기준) 목표 메모 기록

4. 헬스체크/메트릭/JWT (1h)
   • T1.12 헬스/메트릭 엔드포인트
   • 설명: /healthz, /metrics
   • 산출물: apps/api/routes/health.py
   • 시간: 0.5h / 담당: BE
   • DoD: 200 응답 및 기본 메트릭 노출
   • T1.13 JWT 베어러 미들웨어(기본)
   • 설명: JWK 검증 스텁 or 테스트 키
   • 산출물: adapters/security/jwt.py
   • 시간: 0.5h / 담당: BE
   • DoD: 보호 라우트에서 401/200 동작 구분

⸻

Day 2 — 대화 & 스트리밍 (총 8h)

5. LangGraph 그래프 (3h)
   • T2.1 그래프 상태/노드 정의
   • 설명: retrieve, rerank(optional), augment, llm, record
   • 산출물: rag/graph/graph.py
   • 시간: 1h / 담당: BE
   • 선행: 검색/임베딩
   • DoD: 단위테스트로 노드별 입력/출력 계약 통과
   • T2.2 프롬프트/컨텍스트 빌더
   • 설명: 컨텍스트 패킹(토큰 가드), 시스템/유저 템플릿
   • 산출물: rag/prompts/\*.jinja
   • 시간: 1h / 담당: BE/UXW
   • DoD: 상위 n 청크 삽입, 길이 제한 준수
   • T2.3 지식부족 분기/리커버리
   • 설명: min_score 미달 시 fallback 응답
   • 산출물: 그래프 조건 노드
   • 시간: 1h / 담당: BE
   • DoD: 테스트로 분기 경로 검증

6. WebSocket 스트리밍 + 데모 클라이언트 (3h)
   • T2.4 WS 프로토콜 확정/핸들러
   • 설명: start/user_message/token/final/error 타입 스키마
   • 산출물: apps/api/ws/chat_ws.py, 스키마 정의
   • 시간: 1h / 담당: BE
   • DoD: 2초 내 첫 토큰 도달(외부 LLM 기준)
   • T2.5 백프레셔/핑퐁/에러 처리
   • 설명: 연결 유지, 클라이언트 분리, 타임아웃
   • 산출물: 연결 관리 유틸
   • 시간: 1h / 담당: BE
   • DoD: 비정상 종료 시 자원 정리 확인
   • T2.6 HTML/JS 데모 클라
   • 설명: 토큰 로그/최종 응답/citation 출력
   • 산출물: client/index.html
   • 시간: 1h / 담당: FE
   • DoD: 로컬에서 질문→스트림 표시

7. 저장/템플릿 정리 (2h)
   • T2.7 세션/메시지/인용 모델링 & 저장
   • 설명: DB 테이블/ORM 모델/리포지토리
   • 산출물: Alembic 마이그레이션 + 리포지토리 코드
   • 시간: 1h / 담당: BE/DBA
   • DoD: 대화 1세션 CRUD 통과
   • T2.8 프롬프트/응답 표준 포맷 정리
   • 설명: 응답 구조/메타데이터/usage
   • 산출물: contracts/openapi/chat.yaml 업데이트
   • 시간: 1h / 담당: BE
   • DoD: OpenAPI 검증 통과

⸻

Day 3 — 품질/운영/테스트 (총 8h)

8. 가드레일 & 레이트리미트 (2h)
   • T3.1 품질 가드레일
   • 설명: min_score 문턱, 응답 내 citation 최소 2개, 금칙어/모더레이션(옵션)
   • 산출물: 설정값(.env), 검증 유닛테스트
   • 시간: 1h / 담당: BE
   • DoD: 조건 미충족 시 표준 에러/대체 응답 반환
   • T3.2 레이트리미트
   • 설명: IP/토큰 기반 기본 한도
   • 산출물: starlette-limiter 적용
   • 시간: 1h / 담당: BE
   • DoD: 초과 시 429 반환, 메트릭 기록

9. 관측성: 메트릭 & 트레이스 (2h)
   • T3.3 Prometheus 메트릭
   • 설명: 요청 카운터/지연(p95), 첫 토큰 지연, 검색 스코어 분포
   • 산출물: prometheus-client 계측 코드
   • 시간: 1h / 담당: BE/SRE
   • DoD: /metrics에 커스텀 지표 노출, 대시보드 임포트 가능
   • T3.4 OpenTelemetry 트레이스
   • 설명: retrieve/augment/llm/stream 스팬과 속성
   • 산출물: OTLP 내보내기 설정
   • 시간: 1h / 담당: BE/SRE
   • DoD: 로컬 OTEL Collector로 스팬 수집 확인

10. 테스트 & 검증 (2h)
    • T3.5 E2E 테스트
    • 설명: 업로드→검색→WS 스트리밍→인용 확인
    • 산출물: tests/e2e/test_chat_flow.py
    • 시간: 1h / 담당: QA/BE
    • DoD: 시나리오 그린패스 통과
    • T3.6 부하/성능 측정
    • 설명: Locust로 동시 20세션, p95 첫 토큰 < 2s
    • 산출물: 부하 리포트
    • 시간: 1h / 담당: QA/SRE
    • DoD: 기준 충족/개선안 기록

11. 문서화 & 데모 (2h)
    • T3.7 운영/개발 문서
    • 설명: README, runbook, 아키텍처/시퀀스 다이어그램, .env 템플릿
    • 산출물: README.md, docs/runbook.md, docs/architecture.md
    • 시간: 1h / 담당: BE/TL
    • DoD: 신규 인원이 README만 보고 로컬 실행 성공
    • T3.8 데모 스크립트/레코딩
    • 설명: 시연 순서와 스크린샷/녹화
    • 산출물: docs/demo.md, /docs/assets/\*
    • 시간: 1h / 담당: BE/PM
    • DoD: 5분 이내 데모 진행 가능

⸻

공통 체크리스트
• 모든 환경변수는 .env.example에 설명 포함
• 예외는 표준 에러 포맷(JSON)으로 반환
• 로그는 JSON 구조(레벨/트레이스ID/요청ID 포함)
• DB 트랜잭션/리트라이 정책 문서화
• 보안(권한/시크릿/업로드 화이트리스트) 점검

⸻

수락기준(요약)
• docker compose up 후 5분 내 전체 기동, /healthz 200
• /ingest 10MB 문서 1분 내 처리, /ws/chat 2초 내 첫 토큰
• 최종 응답에 citation ≥ 2, /metrics에서 커스텀 지표 확인
• E2E/부하 기준 충족, README만으로 신규 환경 재현 가능
