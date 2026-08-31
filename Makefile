.PHONY: sync lint check check-local migrations test compose-config compose-build compose-up compose-down load-test-accounts load-test-accounts-local smoke

sync:
	uv sync --all-extras --dev --frozen

lint:
	uv run ruff check apps config tests

check:
	uv run python manage.py check --settings=config.settings.test

check-local:
	uv run python manage.py check --settings=config.settings.local

migrations:
	uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test

test:
	uv run pytest

conf:
	docker compose config --quiet

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

#load_test_accounts
load:
	docker compose exec -e ALLOW_TEST_ACCOUNT_SEED=true web python manage.py load_test_accounts

#load_test_accounts
load-local:
	ALLOW_TEST_ACCOUNT_SEED=true uv run python manage.py load_test_accounts --settings=config.settings.local

smoke:
	curl --fail --silent --show-error http://localhost:8000/api/health/
	curl --fail --silent --show-error --output /dev/null http://localhost:8000/api/schema/
	curl --fail --silent --show-error --output /dev/null http://localhost:8000/api/docs/
	docker compose exec db pg_isready -U ravid -d ravid
	docker compose exec redis redis-cli ping
	docker compose exec chroma curl --fail --silent http://localhost:8000/api/v2/heartbeat
	docker compose exec celery celery -A config inspect ping
	curl --fail --silent --show-error --output /dev/null --user ravid:change-me http://localhost:5555/api/workers
