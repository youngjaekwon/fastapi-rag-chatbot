fastapi-rag-chatbot 서비스 레포 구조 (MSA 표준형)

⸻

Top-level 개요

fastapi-rag-chatbot-service/
├─ apps/ # 실행 단위(프로세스) 별 앱
│ ├─ api/ # FastAPI(REST + WebSocket)
│ └─ worker/ # 비동기 작업(ingest, outbox dispatcher 등)
│
├─ src/ # 공통/도메인 코드 (src-layout)
│ ├─ core/ # 도메인·애플리케이션 계층(헥사고날/클린)
│ │ ├─ domain/ # 엔티티, 값 객체, 도메인 이벤트
│ │ ├─ application/ # 유스케이스(서비스), 포트 인터페이스
│ │ └─ common/ # 에러, 결과 타입, 설정 인터페이스
│ ├─ adapters/ # 어댑터(인프라: DB/Kafka/LLM/Embedding/Cache)
│ │ ├─ db/ # SQLAlchemy, 리포지토리, 쿼리
│ │ ├─ embeddings/ # OpenAI/e5 임베딩 공급자
│ │ ├─ llm/ # LLM 클라이언트(스트리밍 지원)
│ │ ├─ search/ # pgvector 검색, MMR, rerank 연동
│ │ ├─ messaging/ # Kafka(producer/consumer), AsyncAPI 계약
│ │ ├─ cache/ # Redis(선택)
│ │ ├─ telemetry/ # OpenTelemetry, metrics, logging
│ │ └─ security/ # JWT/인증, 권한, 레이트 리미트
│ └─ rag/ # RAG 그래프/체인 정의
│ ├─ graph/ # LangGraph 노드/엣지 구성
│ ├─ prompts/ # 시스템/컨텍스트 템플릿
│ └─ pipeline/ # retrieve→augment→generate→record
│
├─ contracts/ # API/이벤트 계약(명세 우선)
│ ├─ openapi/ # REST(OpenAPI yaml/json)
│ ├─ asyncapi/ # Kafka 이벤트(AsyncAPI yaml)
│ └─ schemas/ # JSON Schema(요청/응답/이벤트 페이로드)
│
├─ migrations/ # Alembic 마이그레이션
│ ├─ env.py
│ └─ versions/
│
├─ deployments/ # 배포 아티팩트(K8s/Helm/Kustomize)
│ ├─ helm/fastapi-rag-chatbot-service/ # Helm 차트(템플릿/values)
│ ├─ k8s/
│ │ ├─ base/ # Deployment/Service/HPA/PDB/NP/SM
│ │ └─ overlays/
│ │ ├─ dev/
│ │ ├─ staging/
│ │ └─ prod/
│ ├─ otel/ # OTEL Collector 설정
│ ├─ prometheus/ # Rule/Alert (SLO/SLI)
│ └─ grafana/ # 대시보드 JSON
│
├─ infra/ # IaC(Terraform) — 선택
│ ├─ modules/
│ │ ├─ postgres_pgvector/
│ │ ├─ msks_kafka/
│ │ ├─ ecr/
│ │ └─ vpc/
│ └─ envs/
│ ├─ dev/
│ ├─ staging/
│ └─ prod/
│
├─ docker/ # 멀티스테이지 Dockerfile & Compose
│ ├─ api.Dockerfile
│ ├─ worker.Dockerfile
│ ├─ compose.dev.yaml # 로컬(dev)
│ └─ compose.obs.yaml # 로컬 observability(otel/prom/graf)
│
├─ client/ # 간단 WebSocket 데모(내부 검증용)
│ └─ index.html
│
├─ tests/
│ ├─ unit/ # 단위 테스트
│ ├─ integration/ # DB/Kafka 통합
│ ├─ e2e/ # ingest→chat 스트리밍 시나리오
│ └─ resources/ # 샘플 PDF/텍스트
│
├─ scripts/ # 개발/운영 스크립트(마이그레이터 등)
│ ├─ init_db.sh
│ ├─ make_sample_data.py
│ └─ load_test_locustfile.py
│
├─ docs/ # 아키텍처/운영 문서
│ ├─ adr/ # ADR(의사결정 기록)
│ ├─ architecture.md # 컨텍스트/컨테이너/컴포넌트 다이어그램
│ ├─ runbook.md # 온콜/장애 대응 절차
│ ├─ security.md # 위협모델/JWT/권한/시크릿 전략
│ └─ slo.md # SLO/에러버짓/알람 기준
│
├─ .github/workflows/ # CI/CD 파이프라인
│ ├─ ci.yaml # lint/test/build/scan
│ ├─ release.yaml # tag→이미지→Helm 패키징
│ └─ trivy.yaml # 이미지/코드 보안 스캔
│
├─ .devcontainer/ # VS Code Dev Containers (선택)
│ └─ devcontainer.json
│
├─ pyproject.toml # poetry/ruff/mypy/pytest 설정
├─ mypy.ini
├─ pytest.ini
├─ .pre-commit-config.yaml
├─ Makefile # make run/api/worker/test/lint/migrate
├─ Taskfile.yml # (또는 justfile) 로컬 작업 자동화
├─ CODEOWNERS
├─ CONTRIBUTING.md
├─ CHANGELOG.md
└─ README.md

⸻

계층/모듈 설계 가이드
• 헥사고날(Ports & Adapters)
• core.application: 유스케이스(포트)와 DTO, 트랜잭션 경계
• core.domain: 엔티티/도메인 서비스, 도메인 이벤트
• adapters.\*: 인프라 구현체(DB/Kafka/LLM/Cache/Telemetry/Security)
• apps/api: 프리젠테이션 계층(HTTP/WebSocket), OpenAPI 스펙 준수
• apps/worker: 비동기 잡(문서 파이프라인, outbox dispatcher)
• CQRS/이벤트 (선택)
• 쓰기 모델: 업로드/청킹/임베딩/색인(트랜잭션)
• 읽기 모델: chunks + pgvector를 통한 검색
• Outbox 패턴: DB 트랜잭션과 함께 outbox_events 테이블에 기록 → worker가 Kafka로 내보냄

⸻

데이터베이스 스키마(요지)
• documents(id, collection, source, metadata, created_at)
• chunks(id, document_id, content, embedding[vector], metadata, created_at)
• sessions(id, user_id, metadata, created_at)
• messages(id, session_id, role, content, usage_prompt, usage_completion, created_at)
• citations(id, message_id, chunk_id, score, extra)
• outbox_events(id, aggregate_id, type, payload, created_at, published_at)

Alembic으로 관리하며 migrations/versions에 버전별 스크립트 배치.

⸻

API/프로토콜
• REST (OpenAPI): /ingest, /chat/session, /healthz, /metrics
• WebSocket: /ws/chat?session_id=... (토큰 스트리밍)
• Kafka 이벤트(옵션): document.ingested, embedding.created, chat.message.created 등(AsyncAPI로 계약)

contracts/openapi와 contracts/asyncapi에서 **소비자 주도 계약(CDC)**를 가능하게 유지.

⸻

Observability & 운영
• OpenTelemetry 트레이스: retrieve/augment/llm/stream 스팬 구분
• Prometheus 지표: 요청 p95, 첫 토큰 지연, 검색 hit-rate, 스코어 분포
• Grafana 대시보드 샘플 JSON 제공(deployments/grafana)
• SLO: Availability(99.9%), Latency p95 < 2s(첫 토큰), 에러율 알람 규칙 포함

⸻

보안/시크릿/정책
• JWT 베어러(예: Cognito JWK 검증) → security/
• External Secrets(Sealed/Cloud Secret Manager)로 시크릿 주입(K8s)
• 네트워크 폴리시/PodSecurity, 이미지 서명(선택: Cosign)
• PR 단계에서 SAST/Dependency Scan(Trivy/Snyk)

⸻

로컬 개발 흐름

make setup # venv, pre-commit 설치
make up # docker compose(dev)로 db/otel/kafka(optional) 기동
make migrate # Alembic 업/다운
make run-api # FastAPI 앱 실행(핫리로드)
make run-worker # Ingestion/outbox 워커 실행
make test # unit + integration

⸻

CI/CD 파이프라인(요지) 1. CI: ruff + mypy + pytest + coverage → Trivy scan → 컨테이너 빌드/푸시(ECR/GHCR) 2. 릴리스: git tag(version) → Helm 패키징/차트 리포 업데이트 → overlays/\*에 이미지 태그 자동 치환(또는 ArgoCD)

⸻

부록 A: apps/api 디렉토리 예시

apps/api/
├─ main.py # FastAPI 앱 팩토리, 라우팅, 미들웨어
├─ routes/
│ ├─ ingest.py
│ ├─ chat.py # REST 세션 생성
│ └─ health.py
├─ ws/
│ └─ chat_ws.py # WebSocket 핸들러(스트리밍 중계)
├─ deps/
│ └─ containers.py # DI 컨테이너(설정/서비스 바인딩)
└─ settings.py

부록 B: apps/worker 디렉토리 예시

apps/worker/
├─ main.py # 워커 엔트리
├─ jobs/
│ ├─ ingest_file.py # 업로드→청킹→임베딩→pgvector
│ ├─ create_embeddings.py
│ └─ outbox_dispatch.py # outbox→Kafka
└─ settings.py

부록 C: Helm values 핵심 키

image:
repository: ghcr.io/org/fastapi-rag-chatbot-service
tag: "1.0.0"
resources:
requests: { cpu: "200m", memory: "512Mi" }
limits: { cpu: "1", memory: "1Gi" }
postgres:
host: postgresql.fastapi-rag-chatbot.svc
db: fastapi-rag-chatbot
userSecretRef: fastapi-rag-chatbot-db-credentials
otel:
endpoint: http://otel-collector:4317
replicaCount: 2
hpa:
enabled: true
targetCPUUtilizationPercentage: 70

⸻

체크리스트
• OpenAPI/AsyncAPI 계약서 초안 작성 및 리뷰
• Alembic 초기 마이그레이션 생성 및 CI 적용
• OTEL/Prometheus/Grafana 로컬 관측 스택 실행 확인
• 보안 스캔 파이프라인(Trivy) 통과
• Outbox→Kafka 이벤트 흐름 통합 테스트
• README/Runbook 최신화
