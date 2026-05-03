"""Tests for symlink/path-traversal protection in scaffold operations."""
from __future__ import annotations

from pathlib import Path

import pytest


def test_symlink_in_scaffold_target_is_rejected(tmp_path: Path) -> None:
    """A symlink inside the target pointing outside must be caught."""
    from kanon_core._scaffold import _ensure_within

    base = tmp_path / "project"
    base.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = base / "escape"
    link.symlink_to(outside)

    with pytest.raises(Exception, match="Path escapes target directory"):
        _ensure_within(link / "file.txt", base)


def test_normal_path_within_target_succeeds(tmp_path: Path) -> None:
    """A normal path within the target must resolve without error."""
    from kanon_core._scaffold import _ensure_within

    base = tmp_path / "project"
    base.mkdir()
    sub = base / "sub"
    sub.mkdir()

    result = _ensure_within(sub / "file.txt", base)
    assert result.is_relative_to(base.resolve())


def test_dotdot_traversal_is_rejected(tmp_path: Path) -> None:
    """A path using .. to escape the target must be caught."""
    from kanon_core._scaffold import _ensure_within

    base = tmp_path / "project"
    base.mkdir()

    with pytest.raises(Exception, match="Path escapes target directory"):
        _ensure_within(base / "sub" / ".." / ".." / "etc" / "passwd", base)
