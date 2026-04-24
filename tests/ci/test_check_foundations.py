"""Tests for ci/check_foundations.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "ci" / "check_foundations.py"
assert _SCRIPT_PATH.is_file(), f"script not found: {_SCRIPT_PATH}"


def _load():
    spec = importlib.util.spec_from_file_location("check_foundations", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


mod = _load()


def test_real_repo_passes() -> None:
    """The kanon repo itself must pass foundation checks."""
    errors, _warnings = mod.check(
        _REPO_ROOT / "docs" / "foundations",
        _REPO_ROOT / "docs" / "specs",
    )
    assert errors == [], "check_foundations failed:\n  " + "\n  ".join(errors)


def test_main_exits_zero_on_ok(capsys: pytest.CaptureFixture[str]) -> None:
    rc = mod.main([
        "--foundations", str(_REPO_ROOT / "docs" / "foundations"),
        "--specs", str(_REPO_ROOT / "docs" / "specs"),
    ])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == "ok"


def test_missing_foundation_ref(tmp_path: Path) -> None:
    """A spec referencing a non-existent foundation slug should error."""
    foundations = tmp_path / "foundations"
    foundations.mkdir()
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "bad-spec.md").write_text(
        "---\nserves:\n  - nonexistent-slug\nstatus: deferred\n---\n# Bad\n",
        encoding="utf-8",
    )
    errors, _ = mod.check(foundations, specs)
    assert len(errors) > 0
    assert "nonexistent-slug" in errors[0]


def test_invalid_principle_kind(tmp_path: Path) -> None:
    """A principle with an invalid kind should error."""
    foundations = tmp_path / "foundations"
    foundations.mkdir()
    principles = foundations / "principles"
    principles.mkdir()
    (principles / "bad.md").write_text(
        "---\nid: bad-principle\nkind: invalid\nstatus: accepted\n---\n# Bad\n",
        encoding="utf-8",
    )
    specs = tmp_path / "specs"
    specs.mkdir()
    errors, _ = mod.check(foundations, specs)
    assert len(errors) > 0
    assert "invalid" in errors[0]
