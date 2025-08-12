include .env
export $(shell sed 's/=.*//' .env)

.PHONY: setup up down logs restart
setup:
	uv sync

up:
	docker compose -f docker/compose.dev.yaml up -d

down:
	docker compose -f docker/compose.dev.yaml down

logs:
	docker compose -f docker/compose.dev.yaml logs -f api worker

restart: down up


.PHONY: migrate makemigrations db-shell
migrate:
	uv run alembic upgrade head

makemigrations:
	uv run alembic revision --autogenerate -m "$(message)"

db-shell:
	docker compose -f docker/compose.dev.yaml exec db psql -U $(DB_USER) -d $(DB_NAME)


.PHONY: lint typecheck test
lint:
	ruff check .

typecheck:
	mypy .

test:
	uv run pytest -v --asyncio-mode=auto --cov=src --cov-report=term-missing

.PHONY: run-api run-worker
run-api:
	uv run fastapi dev apps/api/main.py

run-worker:
	uv run apps/worker/main.py


.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
