.PHONY: help install test test-fast test-cov eval eval-quick run-api run-ui run-both docker-build clean format lint

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install runtime + dev deps
	pip install -e ".[dev]"

test:  ## Run all tests
	pytest tests/ -v

test-fast:  ## Run only fast tests (no integration)
	pytest tests/ -v -m "not integration"

test-cov:  ## Run tests with coverage report
	pytest tests/ --cov=app --cov-report=term-missing --cov-report=html

eval:  ## Run full eval (30 questions, ~15 min)
	python scripts/run_eval.py

eval-quick:  ## Run eval on 5 questions (smoke, ~3 min)
	python scripts/run_eval.py --qids Q01,Q05,Q10,Q20,Q25

run-api:  ## Run FastAPI backend
	uvicorn app.main:app --reload --port 8000

run-ui:  ## Run Streamlit UI
	streamlit run ui/streamlit_app.py

run-both:  ## Run API + UI in two terminals (use a tmux/separate shell for UI)
	uvicorn app.main:app --reload --port 8000 & streamlit run ui/streamlit_app.py

docker-build:  ## Build the local Docker image
	docker build -t text-to-sql-agent .

clean:  ## Clean caches + logs
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	rm -rf logs/*.log
	rm -rf data/db/sessions.db
	rm -rf mlruns

format:  ## Format code with ruff (if installed)
	ruff format app/ tests/ scripts/ ui/

lint:  ## Lint with ruff (if installed)
	ruff check app/ tests/ scripts/ ui/
