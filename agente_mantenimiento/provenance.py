from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

from .config import PROJECT_DIR


METADATA_SCHEMA_VERSION = "2.0"
CORE_SOURCE_PATHS = (
    "agente_mantenimiento",
    "prompts",
    "requirements.txt",
    "requirements-lock.txt",
    "run_agent.py",
    "run_web.py",
    "VERSION",
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256_bytes(encoded)


def _source_files(paths: Iterable[str] = CORE_SOURCE_PATHS) -> list[Path]:
    files: list[Path] = []
    for relative in paths:
        candidate = PROJECT_DIR / relative
        if candidate.is_file():
            files.append(candidate)
        elif candidate.is_dir():
            files.extend(
                path for path in candidate.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            )
    return sorted(files, key=lambda path: path.relative_to(PROJECT_DIR).as_posix())


def source_snapshot_sha256() -> str:
    """Hash the executable source snapshot without depending on Git availability."""
    digest = hashlib.sha256()
    for path in _source_files():
        relative = path.relative_to(PROJECT_DIR).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        payload = path.read_bytes()
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def agent_version() -> str:
    version_path = PROJECT_DIR / "VERSION"
    return version_path.read_text(encoding="utf-8").strip() if version_path.exists() else "unknown"


def git_commit() -> str | None:
    injected = os.environ.get("AGENT_GIT_COMMIT", "").strip()
    if injected:
        return injected
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_DIR,
            check=True, capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    value = completed.stdout.strip()
    return value or None


def runtime_manifest() -> dict[str, Any]:
    dependencies: dict[str, str] = {}
    for name in ("openpyxl", "et_xmlfile"):
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = "not-installed"
    return {
        "metadata_schema_version": METADATA_SCHEMA_VERSION,
        "agent_version": agent_version(),
        "git_commit": git_commit(),
        "source_snapshot_sha256": source_snapshot_sha256(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "dependencies": dependencies,
        "executable_name": Path(sys.executable).name,
    }
