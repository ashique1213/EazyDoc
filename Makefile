.PHONY: help build up down restart logs backend-shell test-backend test-frontend lint check

help:
	@echo "EazyDoc Developer Commands:"
	@echo "  make up            - Start all services using Docker Compose"
	@echo "  make down          - Stop all Docker Compose services"
	@echo "  make build         - Build/rebuild Docker containers"
	@echo "  make logs          - Tail logs of all containers"
	@echo "  make migrate       - Run Django database migrations"
	@echo "  make makemigrations- Create new Django migrations"
	@echo "  make test-backend  - Run backend unit tests"
	@echo "  make test-frontend - Run frontend tests/build"
	@echo "  make lint          - Lint backend and frontend code"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

migrate:
	docker compose exec backend python manage.py migrate

makemigrations:
	docker compose exec backend python manage.py makemigrations

backend-shell:
	docker compose exec backend python manage.py shell

test-backend:
	cd backend && python manage.py test

test-frontend:
	cd frontend && npm run build

lint:
	cd frontend && npm run lint

check:
	cd backend && python manage.py check
