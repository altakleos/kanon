"""Shared fixtures for CI script tests.

CI scripts live in ``ci/`` and are standalone Python files (not part of the
pip package), so they must be loaded via importlib.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parents[2]


def _load_ci_script(name: str) -> ModuleType:
    """Load a CI script by filename and return it as a module."""
    script = REPO_ROOT / "ci" / name
    assert script.is_file(), f"CI script not found: {script}"
    module_name = script.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Resolved path to the repository root."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def load_ci_script() -> Callable[[str], ModuleType]:
    """Factory fixture: call with a script filename to get the loaded module.

    Session-scoped so each script is only loaded once per test run.
    """
    cache: dict[str, ModuleType] = {}

    def _cached_load(name: str) -> ModuleType:
        if name not in cache:
            cache[name] = _load_ci_script(name)
        return cache[name]

    return _cached_load


# ---------------------------------------------------------------------------
# Git helpers for tests that need synthetic repos
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    """Run git in *repo* with a deterministic, non-interactive identity."""
    env = {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(repo),
    }
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


@pytest.fixture()
def git_repo(tmp_path: Path):
    """Create a bare-bones git repo in *tmp_path* and return ``(repo_path, git_fn)``.

    ``git_fn`` is a convenience wrapper: ``git_fn("add", ".")`` runs
    ``git add .`` inside the repo with a deterministic test identity.
    """
    repo = tmp_path
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "commit.gpgsign", "false")

    def git_fn(*args: str) -> str:
        return _git(repo, *args)

    return repo, git_fn
