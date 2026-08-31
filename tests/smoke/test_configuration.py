import importlib
import sys

import pytest
from celery import current_app
from django.conf import settings


def import_fresh_settings(module_name: str):
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_domain_apps_are_registered():
    assert "apps.accounts" in settings.INSTALLED_APPS
    assert "apps.common" in settings.INSTALLED_APPS
    assert "apps.documents" in settings.INSTALLED_APPS
    assert "apps.rag" in settings.INSTALLED_APPS


def test_default_api_permission_is_authenticated():
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAuthenticated"
    ]


def test_test_settings_do_not_require_external_services():
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
    assert settings.CELERY_TASK_ALWAYS_EAGER is True
    assert settings.OPENROUTER_API_KEY == ""


def test_rag_defaults_use_free_router_and_bounded_requests():
    assert settings.OPENROUTER_MODEL == "openrouter/free"
    assert settings.DEFAULT_DAILY_TOKEN_LIMIT == 20_000
    assert settings.RAG_RETRIEVAL_K == 4
    assert settings.RAG_RETRIEVAL_SEARCH_TYPE == "similarity_score_threshold"
    assert settings.RAG_RETRIEVAL_SCORE_THRESHOLD == 0.2
    assert settings.RAG_RETRIEVAL_FETCH_K == 20
    assert settings.RAG_MAX_CONTEXT_CHARS == 6_000
    assert settings.RAG_MAX_OUTPUT_TOKENS == 800
    assert settings.RAG_HYDE_MAX_OUTPUT_TOKENS == 256
    assert settings.RAG_HYDE_MAX_OUTPUT_CHARS == 2_000
    assert settings.RAG_HYDE_TIMEOUT_MS == 3_000
    assert settings.RAG_CHAT_OVERHEAD_TOKENS == 256
    assert settings.RAG_TEMPERATURE == 0
    assert settings.RAG_PROVIDER_TIMEOUT_MS == 10_000
    assert settings.RAG_PROVIDER_MAX_RETRIES == 0


def test_celery_uses_django_settings_namespace():
    assert current_app.main == "ravid"
    assert settings.CELERY_BROKER_URL == "memory://"
    assert settings.CELERY_TASK_IGNORE_RESULT is True


def test_ingestion_defaults_are_bounded_and_coherent():
    assert settings.INGESTION_MAX_PDF_PAGES == 200
    assert settings.INGESTION_MAX_EXTRACTED_CHARS == 2_000_000
    assert settings.INGESTION_MAX_CHUNKS == 2_500
    assert settings.INGESTION_MAX_RECOVERY_ATTEMPTS == 3
    assert settings.INGESTION_OUTBOX_MAX_ATTEMPTS == 5
    assert settings.INGESTION_CLEANUP_MAX_ATTEMPTS == 5
    assert settings.INGESTION_CLEANUP_BACKOFF_SECONDS == 300
    assert settings.INGESTION_STALE_PROCESSING_SECONDS >= (
        settings.CELERY_TASK_TIME_LIMIT + settings.INGESTION_LEASE_SAFETY_SECONDS
    )
    assert "publish-ingestion-dispatches" in settings.CELERY_BEAT_SCHEDULE
    assert "recover-ingestion-work" in settings.CELERY_BEAT_SCHEDULE


def test_production_settings_require_secret_key(monkeypatch):
    for key in ("SECRET_KEY", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(Exception, match="SECRET_KEY is required"):
        import_fresh_settings("config.settings.production")


def test_production_settings_use_postgresql(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-production-secret")
    monkeypatch.setenv("POSTGRES_DB", "ravid")
    monkeypatch.setenv("POSTGRES_USER", "ravid")
    monkeypatch.setenv("POSTGRES_PASSWORD", "ravid")

    production = import_fresh_settings("config.settings.production")

    assert production.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
    assert production.DATABASES["default"]["HOST"] == "db"
