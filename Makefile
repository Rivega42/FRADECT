.PHONY: help install run test lint format clean docker-build docker-up docker-down migrate

# Variables
PYTHON := python3
PIP := pip3
PROJECT_NAME := fradect
DOCKER_COMPOSE := docker-compose
BLACK := black
ISORT := isort
FLAKE8 := flake8
PYTEST := pytest

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo '${GREEN}FRADECT Makefile${NC}'
	@echo ''
	@echo 'Usage:'
	@echo '  ${YELLOW}make${NC} ${GREEN}<target>${NC}'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  ${YELLOW}%-15s${NC} %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	@echo '${GREEN}Installing dependencies...${NC}'
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo '${GREEN}Dependencies installed!${NC}'

install-dev: ## Install development dependencies
	@echo '${GREEN}Installing dev dependencies...${NC}'
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	pre-commit install
	@echo '${GREEN}Dev dependencies installed!${NC}'

run: ## Run the application locally
	@echo '${GREEN}Starting FRADECT API...${NC}'
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Run the application in production mode
	@echo '${GREEN}Starting FRADECT API in production mode...${NC}'
	gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

test: ## Run tests
	@echo '${GREEN}Running tests...${NC}'
	$(PYTEST) tests/ -v --cov=src --cov-report=term-missing --cov-report=html

test-unit: ## Run unit tests only
	@echo '${GREEN}Running unit tests...${NC}'
	$(PYTEST) tests/unit/ -v

test-integration: ## Run integration tests
	@echo '${GREEN}Running integration tests...${NC}'
	$(PYTEST) tests/integration/ -v

test-e2e: ## Run end-to-end tests
	@echo '${GREEN}Running E2E tests...${NC}'
	$(PYTEST) tests/e2e/ -v

lint: ## Run linters
	@echo '${GREEN}Running linters...${NC}'
	$(BLACK) --check src/ tests/
	$(ISORT) --check-only src/ tests/
	$(FLAKE8) src/ tests/ --max-line-length=100
	mypy src/ --ignore-missing-imports

format: ## Format code
	@echo '${GREEN}Formatting code...${NC}'
	$(BLACK) src/ tests/
	$(ISORT) src/ tests/
	@echo '${GREEN}Code formatted!${NC}'

clean: ## Clean temporary files
	@echo '${GREEN}Cleaning up...${NC}'
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '.pytest_cache' -delete
	find . -type d -name '.mypy_cache' -delete
	rm -rf htmlcov/
	rm -f .coverage
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	@echo '${GREEN}Cleaned!${NC}'

# Docker commands
docker-build: ## Build Docker images
	@echo '${GREEN}Building Docker images...${NC}'
	$(DOCKER_COMPOSE) build

docker-up: ## Start Docker containers
	@echo '${GREEN}Starting Docker containers...${NC}'
	$(DOCKER_COMPOSE) up -d
	@echo '${GREEN}Containers started!${NC}'
	@echo 'API: http://localhost:8000'
	@echo 'Docs: http://localhost:8000/docs'
	@echo 'Grafana: http://localhost:3000 (admin/admin)'
	@echo 'MLflow: http://localhost:5000'
	@echo 'Prometheus: http://localhost:9090'

docker-down: ## Stop Docker containers
	@echo '${GREEN}Stopping Docker containers...${NC}'
	$(DOCKER_COMPOSE) down

docker-logs: ## Show Docker logs
	$(DOCKER_COMPOSE) logs -f

docker-clean: ## Clean Docker resources
	@echo '${RED}Cleaning Docker resources...${NC}'
	$(DOCKER_COMPOSE) down -v
	docker system prune -f

# Database commands
db-migrate: ## Run database migrations
	@echo '${GREEN}Running migrations...${NC}'
	alembic upgrade head

db-rollback: ## Rollback last migration
	@echo '${YELLOW}Rolling back migration...${NC}'
	alembic downgrade -1

db-reset: ## Reset database
	@echo '${RED}Resetting database...${NC}'
	alembic downgrade base
	alembic upgrade head
	@echo '${GREEN}Database reset complete!${NC}'

db-seed: ## Seed database with test data
	@echo '${GREEN}Seeding database...${NC}'
	$(PYTHON) scripts/seed_db.py

# ML commands
ml-train: ## Train ML models
	@echo '${GREEN}Training ML models...${NC}'
	$(PYTHON) scripts/train_models.py

ml-evaluate: ## Evaluate ML models
	@echo '${GREEN}Evaluating ML models...${NC}'
	$(PYTHON) scripts/evaluate_models.py

ml-deploy: ## Deploy ML models
	@echo '${GREEN}Deploying ML models...${NC}'
	$(PYTHON) scripts/deploy_models.py

# Monitoring commands
monitor-start: ## Start monitoring stack
	@echo '${GREEN}Starting monitoring...${NC}'
	docker-compose -f docker-compose.monitoring.yml up -d

monitor-stop: ## Stop monitoring stack
	@echo '${GREEN}Stopping monitoring...${NC}'
	docker-compose -f docker-compose.monitoring.yml down

# Security commands
security-check: ## Run security checks
	@echo '${GREEN}Running security checks...${NC}'
	safety check --json
	bandit -r src/
	trivy image $(PROJECT_NAME):latest

# Performance commands
perf-test: ## Run performance tests
	@echo '${GREEN}Running performance tests...${NC}'
	locust -f tests/performance/locustfile.py --host=http://localhost:8000

profile: ## Profile the application
	@echo '${GREEN}Profiling application...${NC}'
	python -m cProfile -o profile.stats src/main.py
	python -m pstats profile.stats

# Documentation
docs-build: ## Build documentation
	@echo '${GREEN}Building documentation...${NC}'
	mkdocs build

docs-serve: ## Serve documentation locally
	@echo '${GREEN}Serving documentation...${NC}'
	mkdocs serve

# Deployment
deploy-staging: ## Deploy to staging
	@echo '${GREEN}Deploying to staging...${NC}'
	./scripts/deploy.sh staging

deploy-production: ## Deploy to production
	@echo '${RED}Deploying to PRODUCTION...${NC}'
	@echo '${YELLOW}Are you sure? [y/N]${NC}'
	@read ans && [ $${ans:-N} = y ]
	./scripts/deploy.sh production

# Kubernetes
k8s-deploy: ## Deploy to Kubernetes
	@echo '${GREEN}Deploying to Kubernetes...${NC}'
	kubectl apply -f k8s/

k8s-delete: ## Delete from Kubernetes
	@echo '${RED}Deleting from Kubernetes...${NC}'
	kubectl delete -f k8s/

k8s-logs: ## Show Kubernetes logs
	kubectl logs -f deployment/fradect-api

# Utilities
version: ## Show version
	@echo '${GREEN}FRADECT Version:${NC}'
	@cat VERSION

changelog: ## Generate changelog
	@echo '${GREEN}Generating changelog...${NC}'
	git-changelog -o CHANGELOG.md

backup: ## Backup database
	@echo '${GREEN}Backing up database...${NC}'
	pg_dump $(DATABASE_URL) > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore: ## Restore database from backup
	@echo '${YELLOW}Restoring database...${NC}'
	psql $(DATABASE_URL) < $(BACKUP_FILE)
