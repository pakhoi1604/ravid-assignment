import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


def env_list(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-local-development-secret-key")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.accounts",
    "apps.common",
    "apps.documents",
    "apps.rag",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=env_int("JWT_ACCESS_TOKEN_LIFETIME_DAYS", 7)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", 30)),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "RAVID API",
    "DESCRIPTION": "Document RAG backend foundation.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = env_int("CELERY_TASK_TIME_LIMIT", 30 * 60)
CELERY_TASK_IGNORE_RESULT = True
CELERY_BROKER_CONNECTION_TIMEOUT = env_int("CELERY_BROKER_CONNECTION_TIMEOUT", 3)
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "socket_connect_timeout": CELERY_BROKER_CONNECTION_TIMEOUT,
    "socket_timeout": CELERY_BROKER_CONNECTION_TIMEOUT,
}
CELERY_BEAT_SCHEDULE = {
    "publish-ingestion-dispatches": {
        "task": "apps.documents.tasks.publish_ingestion_dispatches",
        "schedule": env_int("INGESTION_OUTBOX_PUBLISH_INTERVAL_SECONDS", 10),
    },
    "recover-ingestion-work": {
        "task": "apps.documents.tasks.recover_ingestion_work",
        "schedule": env_int("INGESTION_RECOVERY_INTERVAL_SECONDS", 60),
    },
}

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = env_int("CHROMA_PORT", 8000)
CHROMA_URL = f"http://{CHROMA_HOST}:{CHROMA_PORT}"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_APP_TITLE = os.getenv("OPENROUTER_APP_TITLE", "RAVID Backend")
OPENROUTER_APP_URL = os.getenv("OPENROUTER_APP_URL", "")

DEFAULT_DAILY_TOKEN_LIMIT = env_int("DEFAULT_DAILY_TOKEN_LIMIT", 20_000)
RAG_RETRIEVAL_K = env_int("RAG_RETRIEVAL_K", 4)
RAG_RETRIEVAL_SEARCH_TYPE = os.getenv("RAG_RETRIEVAL_SEARCH_TYPE", "similarity_score_threshold")
RAG_RETRIEVAL_SCORE_THRESHOLD = float(os.getenv("RAG_RETRIEVAL_SCORE_THRESHOLD", "0.2"))
RAG_RETRIEVAL_FETCH_K = env_int("RAG_RETRIEVAL_FETCH_K", 20)
RAG_MAX_CONTEXT_CHARS = env_int("RAG_MAX_CONTEXT_CHARS", 6_000)
RAG_MAX_OUTPUT_TOKENS = env_int("RAG_MAX_OUTPUT_TOKENS", 800)
RAG_CHAT_OVERHEAD_TOKENS = env_int("RAG_CHAT_OVERHEAD_TOKENS", 256)
RAG_HYDE_MAX_OUTPUT_TOKENS = env_int("RAG_HYDE_MAX_OUTPUT_TOKENS", 256)
RAG_HYDE_MAX_OUTPUT_CHARS = env_int("RAG_HYDE_MAX_OUTPUT_CHARS", 2_000)
RAG_HYDE_TIMEOUT_MS = env_int("RAG_HYDE_TIMEOUT_MS", 3_000)
RAG_TEMPERATURE = float(os.getenv("RAG_TEMPERATURE", "0"))
RAG_PROVIDER_TIMEOUT_MS = env_int("RAG_PROVIDER_TIMEOUT_MS", 10_000)
RAG_PROVIDER_MAX_RETRIES = env_int("RAG_PROVIDER_MAX_RETRIES", 0)

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "sentence-transformers/all-MiniLM-L6-v2",
)
MAX_UPLOAD_SIZE_MB = env_int("MAX_UPLOAD_SIZE_MB", 25)
VECTOR_CHUNK_SIZE = env_int("VECTOR_CHUNK_SIZE", 1000)
VECTOR_CHUNK_OVERLAP = env_int("VECTOR_CHUNK_OVERLAP", 150)
VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "ravid_documents")

INGESTION_MAX_PDF_PAGES = env_int("INGESTION_MAX_PDF_PAGES", 200)
INGESTION_MAX_EXTRACTED_CHARS = env_int("INGESTION_MAX_EXTRACTED_CHARS", 2_000_000)
INGESTION_MAX_CHUNKS = env_int("INGESTION_MAX_CHUNKS", 2_500)
INGESTION_LEASE_SAFETY_SECONDS = env_int("INGESTION_LEASE_SAFETY_SECONDS", 300)
INGESTION_STALE_PENDING_SECONDS = env_int("INGESTION_STALE_PENDING_SECONDS", 300)
INGESTION_STALE_PROCESSING_SECONDS = env_int(
    "INGESTION_STALE_PROCESSING_SECONDS",
    CELERY_TASK_TIME_LIMIT + INGESTION_LEASE_SAFETY_SECONDS,
)
INGESTION_MAX_RECOVERY_ATTEMPTS = env_int("INGESTION_MAX_RECOVERY_ATTEMPTS", 3)
INGESTION_OUTBOX_MAX_ATTEMPTS = env_int("INGESTION_OUTBOX_MAX_ATTEMPTS", 5)
INGESTION_OUTBOX_CLAIM_SECONDS = env_int("INGESTION_OUTBOX_CLAIM_SECONDS", 60)
INGESTION_OUTBOX_BACKOFF_SECONDS = env_int("INGESTION_OUTBOX_BACKOFF_SECONDS", 30)
INGESTION_CLEANUP_GRACE_SECONDS = env_int(
    "INGESTION_CLEANUP_GRACE_SECONDS",
    CELERY_TASK_TIME_LIMIT + INGESTION_LEASE_SAFETY_SECONDS,
)
INGESTION_CLEANUP_MAX_ATTEMPTS = env_int("INGESTION_CLEANUP_MAX_ATTEMPTS", 5)
INGESTION_CLEANUP_BACKOFF_SECONDS = env_int("INGESTION_CLEANUP_BACKOFF_SECONDS", 300)
INGESTION_ORPHAN_UPLOAD_GRACE_SECONDS = env_int("INGESTION_ORPHAN_UPLOAD_GRACE_SECONDS", 3600)


def _validate_positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer.")


for _positive_setting in (
    "MAX_UPLOAD_SIZE_MB",
    "VECTOR_CHUNK_SIZE",
    "INGESTION_MAX_PDF_PAGES",
    "INGESTION_MAX_EXTRACTED_CHARS",
    "INGESTION_MAX_CHUNKS",
    "INGESTION_LEASE_SAFETY_SECONDS",
    "INGESTION_STALE_PENDING_SECONDS",
    "INGESTION_STALE_PROCESSING_SECONDS",
    "INGESTION_MAX_RECOVERY_ATTEMPTS",
    "INGESTION_OUTBOX_MAX_ATTEMPTS",
    "INGESTION_OUTBOX_CLAIM_SECONDS",
    "INGESTION_OUTBOX_BACKOFF_SECONDS",
    "INGESTION_CLEANUP_GRACE_SECONDS",
    "INGESTION_CLEANUP_MAX_ATTEMPTS",
    "INGESTION_CLEANUP_BACKOFF_SECONDS",
    "INGESTION_ORPHAN_UPLOAD_GRACE_SECONDS",
):
    _validate_positive_int(_positive_setting, globals()[_positive_setting])

if (
    isinstance(VECTOR_CHUNK_OVERLAP, bool)
    or not isinstance(VECTOR_CHUNK_OVERLAP, int)
    or VECTOR_CHUNK_OVERLAP < 0
    or VECTOR_CHUNK_OVERLAP >= VECTOR_CHUNK_SIZE
):
    raise ValueError("VECTOR_CHUNK_SIZE must be greater than VECTOR_CHUNK_OVERLAP >= 0.")

if INGESTION_STALE_PROCESSING_SECONDS < CELERY_TASK_TIME_LIMIT + INGESTION_LEASE_SAFETY_SECONDS:
    raise ValueError("INGESTION_STALE_PROCESSING_SECONDS must exceed the Celery task time limit.")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
