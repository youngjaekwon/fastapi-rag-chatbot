## [Unreleased] - 2025-08-12

### Added

- 프로젝트 구조 초기화: 서비스의 기본 디렉터리 구조를 설정
- Makefile 추가: 개발, 데이터베이스, 린트/테스트 실행을 위한 명령어 포함
- pre-commit 설정: ruff, mypy, 문서 린팅/포매팅, 타입체크를 위한 훅 구성
- 개발용 Docker compose 스택 추가: postgres + pgvector, api, worker 서비스 포함
- .gitignore 업데이트: env 파일 및 데이터베이스 데이터 파일 제외
- 임시 FastAPI 앱 및 Worker 엔트리포인트 추가
- ruff/mypy/pytest 설정을 `pyproject.toml`에 추가
- 초기 smoke 테스트 파일(`tests/unit/test_smoke.py`) 추가
- Github Actions CI 워크플로우 추가: main, staging, dev 브랜치에서 push 및 PR 시 lint, typecheck, test 실행
