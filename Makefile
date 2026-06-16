.PHONY: dev test lint typecheck migrate up down models

dev:        ## run API locally
	cd backend && uvicorn app.main:app --reload --port 8000

test:       ## run test suite
	cd backend && python -m pytest tests -q

lint:
	ruff check backend

typecheck:
	mypy backend/app

up:         ## start full stack
	docker compose up --build

down:
	docker compose down

models:     ## pull local LLM + embeddings
	bash scripts/pull_models.sh
