"""Shared fixtures for the agent-sdd test suite."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def repo_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parents[1]
