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


def test_celery_uses_django_settings_namespace():
    assert current_app.main == "ravid"
    assert settings.CELERY_BROKER_URL == "memory://"


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
