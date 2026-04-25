"""Tests for the atomic_write_text helper, ported from Sensei.

kanon is POSIX-only (Linux / macOS); these tests assume POSIX semantics —
in particular, the parent-directory fsync that test_fsyncs_parent_directory
asserts. See pyproject.toml's OS classifiers and the README.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from kanon._atomic import atomic_write_text


def test_happy_path(tmp_path: Path) -> None:
    target = tmp_path / "file.yaml"
    atomic_write_text(target, "key: value\n")
    assert target.read_text(encoding="utf-8") == "key: value\n"


def test_no_tmp_left_after_success(tmp_path: Path) -> None:
    target = tmp_path / "file.yaml"
    atomic_write_text(target, "key: value\n")
    tmp = target.with_suffix(target.suffix + ".tmp")
    assert not tmp.exists()


def test_crash_on_replace_leaves_original_untouched(tmp_path: Path) -> None:
    target = tmp_path / "file.yaml"
    original_content = "original: true\n"
    target.write_text(original_content, encoding="utf-8")

    with (
        patch("kanon._atomic.os.replace", side_effect=OSError("disk full")),
        pytest.raises(OSError, match="disk full"),
    ):
        atomic_write_text(target, "new: content\n")

    assert target.read_text(encoding="utf-8") == original_content
    tmp = target.with_suffix(target.suffix + ".tmp")
    assert not tmp.exists()


def test_overwrites_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "file.yaml"
    target.write_text("old: data\n", encoding="utf-8")
    atomic_write_text(target, "new: data\n")
    assert target.read_text(encoding="utf-8") == "new: data\n"


def test_fsyncs_parent_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import kanon._atomic as atomic_mod

    events: list[str] = []
    real_fsync = atomic_mod.os.fsync
    real_replace = atomic_mod.os.replace

    def tracking_fsync(fd: int) -> None:
        try:
            st = os.fstat(fd)
            kind = "dir" if stat.S_ISDIR(st.st_mode) else "file"
        except OSError:
            kind = "?"
        events.append(f"fsync:{kind}")
        return real_fsync(fd)

    def tracking_replace(src: str, dst: str) -> None:
        events.append("replace")
        return real_replace(src, dst)

    monkeypatch.setattr(atomic_mod.os, "fsync", tracking_fsync)
    monkeypatch.setattr(atomic_mod.os, "replace", tracking_replace)

    target = tmp_path / "file.yaml"
    atomic_write_text(target, "key: value\n")

    assert events == ["fsync:file", "replace", "fsync:dir"]
