.PHONY: install test lint demo backfill train predict api dashboard clean help

help:
	@echo "Pearls AQI Predictor - Available Commands"
	@echo "=========================================="
	@echo "make install     - Install dependencies"
	@echo "make test        - Run all tests"
	@echo "make lint        - Run linting and type checking"
	@echo "make demo        - Run complete demo workflow"
	@echo "make backfill    - Generate demo historical data"
	@echo "make train       - Train models"
	@echo "make predict     - Generate forecast"
	@echo "make api         - Start FastAPI server"
	@echo "make dashboard   - Start Streamlit dashboard"
	@echo "make clean       - Clean generated files"

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

test:
	pytest -v --cov=src/pearls_aqi --cov-report=html --cov-report=term

test-quick:
	pytest -q

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-smoke:
	pytest tests/smoke/ -v

lint:
	black --check src/ tests/
	isort --check-only src/ tests/
	flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503

format:
	black src/ tests/ scripts/ dashboard/
	isort src/ tests/ scripts/ dashboard/

demo:
	@echo "Running complete demo workflow..."
	python scripts/backfill.py --demo --start 2025-01-01 --end 2025-02-01
	python scripts/train.py --demo
	python scripts/predict.py --city Delhi --demo
	@echo "Demo complete! Run 'make dashboard' to view results."

backfill:
	python scripts/backfill.py --demo --start 2025-01-01 --end 2025-02-01

train:
	python scripts/train.py --demo

predict:
	python scripts/predict.py --city Delhi --demo

api:
	python -m uvicorn src.pearls_aqi.api.app:app --reload --host 0.0.0.0 --port 8000

dashboard:
	streamlit run dashboard/streamlit_app.py

fetch:
	python scripts/fetch_current.py --demo

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
	rm -rf build/ dist/ 2>/dev/null || true

clean-data:
	rm -rf data/raw/* data/processed/* data/features/* data/models/* data/reports/*
	@echo "Data directories cleaned (keeping .gitkeep files)"
