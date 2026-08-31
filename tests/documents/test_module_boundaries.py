import ast
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import apps.documents
from apps.documents.constants import ALLOWED_UPLOAD_EXTENSIONS, INVALID_FORMAT_ERROR
from apps.documents.contracts import Chunk
from apps.documents.serializers import (
    ALLOWED_UPLOAD_EXTENSIONS as SERIALIZER_UPLOAD_EXTENSIONS,
)
from apps.documents.serializers import INVALID_FORMAT_ERROR as SERIALIZER_FORMAT_ERROR

DOCUMENTS_DIR = Path(apps.documents.__file__).parent
ALLOWED_DOCUMENT_IMPORTS = {
    "constants": set(),
    "contracts": set(),
    "exceptions": set(),
    "chunking": {"exceptions"},
    "extraction": {"constants", "exceptions"},
    "vector_store": {"contracts", "exceptions"},
    "ingestion": {"chunking", "contracts", "exceptions", "extraction", "models", "vector_store"},
    "retrieval": {"exceptions", "models", "vector_store"},
    "dispatch": {"models", "tasks"},
    "recovery": {"dispatch", "exceptions", "models", "vector_store"},
    "tasks": {"dispatch", "exceptions", "ingestion", "models", "recovery"},
}


def _document_imports(module_name: str) -> set[str]:
    tree = ast.parse((DOCUMENTS_DIR / f"{module_name}.py").read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.level:
                imports.add(node.module.split(".", maxsplit=1)[0])
            elif node.module.startswith("apps.documents."):
                prefix = "apps.documents."
                imports.add(node.module.removeprefix(prefix).split(".", maxsplit=1)[0])
            elif node.module == "apps.documents":
                imports.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level:
            imports.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.Import):
            prefix = "apps.documents."
            imports.update(
                alias.name.removeprefix(prefix).split(".", maxsplit=1)[0]
                for alias in node.names
                if alias.name.startswith(prefix)
            )
    return imports


def test_document_modules_follow_the_allowed_dependency_matrix():
    for module_name, allowed_imports in ALLOWED_DOCUMENT_IMPORTS.items():
        assert _document_imports(module_name) <= allowed_imports

    assert not (DOCUMENTS_DIR / "services.py").exists()


def test_document_contract_and_validation_constants_have_one_owner():
    chunk = Chunk(text="hello", metadata={"user_id": 1}, id="chunk-1")

    with pytest.raises(FrozenInstanceError):
        chunk.text = "changed"

    assert SERIALIZER_UPLOAD_EXTENSIONS is ALLOWED_UPLOAD_EXTENSIONS
    assert SERIALIZER_FORMAT_ERROR is INVALID_FORMAT_ERROR


@pytest.mark.parametrize(
    "module_name",
    [
        "apps.documents.chunking",
        "apps.documents.extraction",
        "apps.documents.vector_store",
        "apps.documents.retrieval",
        "apps.documents.ingestion",
        "apps.documents.dispatch",
        "apps.documents.recovery",
        "apps.documents.tasks",
    ],
)
def test_document_modules_import_cleanly(module_name):
    script = f"import django; django.setup(); import {module_name}"
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings.test"}

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
