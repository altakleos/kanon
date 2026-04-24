"""Tests for ci/check_links.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "ci" / "check_links.py"
assert _SCRIPT_PATH.is_file(), f"script not found: {_SCRIPT_PATH}"


def _load():
    spec = importlib.util.spec_from_file_location("check_links", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


mod = _load()


def test_real_repo_passes() -> None:
    """The kanon repo's own docs/ must have no broken links."""
    errors = mod.check_links(_REPO_ROOT / "docs")
    assert errors == [], "broken links found:\n  " + "\n  ".join(errors)


def test_main_exits_zero_on_ok(capsys: pytest.CaptureFixture[str]) -> None:
    rc = mod.main(["--root", str(_REPO_ROOT / "docs")])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == "ok"


def test_broken_link_detected(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text(
        "[broken](./nonexistent.md)\n", encoding="utf-8"
    )
    errors = mod.check_links(tmp_path)
    assert len(errors) > 0
    assert "nonexistent.md" in errors[0]


def test_external_links_skipped(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text(
        "[ext](https://example.com)\n", encoding="utf-8"
    )
    errors = mod.check_links(tmp_path)
    assert errors == []


def test_code_block_links_skipped(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text(
        "```\n[link](./missing.md)\n```\n", encoding="utf-8"
    )
    errors = mod.check_links(tmp_path)
    assert errors == []
