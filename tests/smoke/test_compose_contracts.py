import subprocess
import tomllib
from pathlib import Path

import yaml


def load_compose():
    return yaml.safe_load(Path("compose.yaml").read_text())


def test_web_worker_and_flower_share_application_image():
    services = load_compose()["services"]

    assert services["web"]["image"] == "ravid-app:local"
    assert services["celery"]["image"] == "ravid-app:local"
    assert services["flower"]["image"] == "ravid-app:local"
    assert "build" not in services["celery"]
    assert "build" not in services["flower"]


def test_web_and_worker_share_media_and_model_cache_volumes():
    services = load_compose()["services"]

    web_volumes = set(services["web"]["volumes"])
    worker_volumes = set(services["celery"]["volumes"])

    assert "media_data:/app/media" in web_volumes
    assert "media_data:/app/media" in worker_volumes
    assert "hf_cache:/home/app/.cache/huggingface" in web_volumes
    assert "hf_cache:/home/app/.cache/huggingface" in worker_volumes


def test_infrastructure_ports_are_not_publicly_published():
    services = load_compose()["services"]

    assert "ports" not in services["db"]
    assert "ports" not in services["redis"]
    assert "ports" not in services["chroma"]
    assert services["web"]["ports"] == ["127.0.0.1:8000:8000"]
    assert services["flower"]["ports"] == ["127.0.0.1:5555:5555"]


def test_application_image_runs_as_non_root_user():
    dockerfile = Path("docker/django/Dockerfile").read_text()

    assert "\nUSER app\n" in dockerfile


def test_application_image_installs_vector_ingestion_dependencies():
    dockerfile = Path("docker/django/Dockerfile").read_text()

    assert "uv sync --frozen --no-dev --extra vector-ingestion --no-install-project" in dockerfile


def test_runtime_and_test_images_keep_dev_dependencies_separate():
    services = load_compose()["services"]
    dockerfile = Path("docker/django/Dockerfile").read_text()

    assert services["web"]["build"]["target"] == "runtime"
    assert services["test"]["profiles"] == ["test"]
    assert services["test"]["build"]["target"] == "test"
    assert services["test"]["environment"]["DJANGO_SETTINGS_MODULE"] == (
        "config.settings.production"
    )
    assert "FROM base AS runtime" in dockerfile
    assert "FROM base AS test" in dockerfile
    assert "uv sync --frozen --all-extras --dev --no-install-project" in dockerfile


def test_openrouter_secret_is_forwarded_only_to_web():
    services = load_compose()["services"]

    assert "OPENROUTER_API_KEY" in services["web"]["environment"]
    for service_name in ("celery", "flower", "test"):
        assert "OPENROUTER_API_KEY" not in services[service_name]["environment"]


def test_web_forwards_free_router_and_rag_defaults():
    web_environment = load_compose()["services"]["web"]["environment"]

    assert web_environment["OPENROUTER_MODEL"] == "${OPENROUTER_MODEL:-openrouter/free}"
    assert web_environment["DEFAULT_DAILY_TOKEN_LIMIT"] == "${DEFAULT_DAILY_TOKEN_LIMIT:-20000}"
    assert web_environment["RAG_RETRIEVAL_K"] == "${RAG_RETRIEVAL_K:-4}"
    assert web_environment["RAG_MAX_CONTEXT_CHARS"] == "${RAG_MAX_CONTEXT_CHARS:-6000}"
    assert web_environment["RAG_MAX_OUTPUT_TOKENS"] == "${RAG_MAX_OUTPUT_TOKENS:-800}"
    assert web_environment["RAG_CHAT_OVERHEAD_TOKENS"] == ("${RAG_CHAT_OVERHEAD_TOKENS:-256}")
    assert web_environment["RAG_TEMPERATURE"] == "${RAG_TEMPERATURE:-0}"
    assert web_environment["RAG_PROVIDER_TIMEOUT_MS"] == "${RAG_PROVIDER_TIMEOUT_MS:-10000}"
    assert web_environment["RAG_PROVIDER_MAX_RETRIES"] == ("${RAG_PROVIDER_MAX_RETRIES:-0}")


def test_chroma_image_runs_as_non_root_user():
    dockerfile = Path("docker/chroma/Dockerfile").read_text()

    assert "\nUSER chroma\n" in dockerfile


def test_chroma_client_and_server_versions_are_aligned():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    vector_dependencies = pyproject["project"]["optional-dependencies"]["vector-ingestion"]
    services = load_compose()["services"]
    dockerfile = Path("docker/chroma/Dockerfile").read_text()

    assert "chromadb==1.5.9" in vector_dependencies
    assert services["chroma"]["image"] == "ravid-chroma:1.5.9"
    assert dockerfile.startswith("FROM chromadb/chroma:1.5.9\n")


def test_imported_runtime_packages_are_direct_dependencies():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    vector_dependencies = pyproject["project"]["optional-dependencies"]["vector-ingestion"]

    assert any(dependency.startswith("langchain-core") for dependency in vector_dependencies)
    assert any(dependency.startswith("langchain-openrouter") for dependency in vector_dependencies)
    assert any(dependency.startswith("openrouter") for dependency in vector_dependencies)
    assert any(dependency.startswith("httpx") for dependency in vector_dependencies)
    assert not any(dependency.startswith("langchain>=") for dependency in vector_dependencies)


def test_required_dockerfiles_are_not_git_ignored():
    required_paths = ["docker/django/Dockerfile", "docker/chroma/Dockerfile"]

    result = subprocess.run(
        ["git", "check-ignore", *required_paths],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1, result.stdout
