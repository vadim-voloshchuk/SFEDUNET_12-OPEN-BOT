.PHONY: help install test lint format clean docker-build docker-run docker-stop

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	python -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt

test: ## Run tests
	./venv/bin/pytest tests/ -v --cov=bot --cov-report=term-missing

test-coverage: ## Run tests with coverage report
	./venv/bin/pytest tests/ -v --cov=bot --cov-report=html --cov-report=term-missing

lint: ## Run code linting
	./venv/bin/flake8 bot.py tests/
	./venv/bin/mypy bot.py --ignore-missing-imports

format: ## Format code with black
	./venv/bin/black bot.py tests/

security: ## Run security checks
	./venv/bin/bandit -r .
	./venv/bin/safety check

clean: ## Clean up temporary files
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf venv/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

docker-build: ## Build Docker image
	docker build -t sfedunet-bot:latest .

docker-run: ## Run bot in Docker container
	docker-compose up -d

docker-stop: ## Stop Docker container
	docker-compose down

docker-logs: ## Show Docker container logs
	docker-compose logs -f

run: ## Run bot locally
	./venv/bin/python bot.py

dev: install lint test ## Set up development environment

check: lint test security ## Run all checks

all: clean install check docker-build ## Run everything