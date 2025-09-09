.PHONY: up down install fmt lint test precommit clean build

# Development
up:
	docker compose -f docker-compose.dev.yml up -d

down:
	docker compose -f docker-compose.dev.yml down -v

install:
	pipx run pre-commit install

# Code quality
fmt:
	ruff format .
	isort .

lint:
	ruff check .
	import-linter lint

test:
	pytest -q

precommit:
	pre-commit run --all-files

# Build
build:
	docker compose -f docker-compose.dev.yml build

# Cleanup
clean:
	docker compose -f docker-compose.dev.yml down -v
	docker system prune -f

# Database migrations
migrate-pg:
	cd apps/userprofiles-service && python scripts/run_pg_migrations.py

migrate-ddb:
	cd apps/usersettings-service && python scripts/run_dynamodb_migrations.py

# Health checks
health:
	@echo "Checking service health..."
	@curl -f http://localhost:8080/health || echo "BFF: DOWN"
	@curl -f http://localhost:8081/health || echo "UserProfiles: DOWN"
	@curl -f http://localhost:8082/health || echo "UserSettings: DOWN"
	@curl -f http://localhost:8083/health || echo "Auth: DOWN"