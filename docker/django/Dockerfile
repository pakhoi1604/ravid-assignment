# syntax=docker/dockerfile:1

# Refresh: pull python:3.12-slim, inspect its RepoDigests, then review and replace this digest.
FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a AS base

ARG UV_VERSION="0.12.7"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:/home/app/.local/bin:${PATH}" \
    HF_HOME=/home/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/home/app/.cache/huggingface

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "uv==${UV_VERSION}"

COPY pyproject.toml uv.lock ./

FROM base AS runtime

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra vector-ingestion --no-install-project

COPY manage.py ./
COPY apps ./apps
COPY config ./config
COPY docker/django/entrypoint.sh ./docker/django/entrypoint.sh
RUN install -d -o app -g app /app/media /home/app/.cache/huggingface

USER app

ENTRYPOINT ["/app/docker/django/entrypoint.sh"]

FROM base AS test

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-extras --dev --no-install-project

COPY manage.py ./
COPY apps ./apps
COPY config ./config
COPY docker/django/entrypoint.sh ./docker/django/entrypoint.sh
COPY tests ./tests
RUN install -d -o app -g app /app/media /home/app/.cache/huggingface

USER app

ENTRYPOINT ["/app/docker/django/entrypoint.sh"]
