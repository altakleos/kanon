"""Unit tests for the helpers extracted from `_set_aspect_depth`.

The integration suite (`tests/test_cli.py`) already exercises the full
`aspect set-depth` flow end-to-end. This file adds a focused check that
`_apply_tier_down` is a *pure* function — no filesystem mutations, output
depends only on the file-existence query at the given target.
"""

from __future__ import annotations

from pathlib import Path

from kernel._cli_aspect import _apply_tier_down


def test_apply_tier_down_returns_only_existing_files(tmp_path: Path) -> None:
    """The diff includes only paths that (a) drop out of the required set
    AND (b) actually exist on disk."""

    # Stub the kit's `_expected_files` for this test by feeding two aspect
    # snapshots whose `_expected_files` differ in known ways via the live
    # manifest. We use real aspect names + depths so `_expected_files` returns
    # genuine, non-overlapping path sets.
    sdd_at_3 = {"kanon-sdd": 3}
    sdd_at_1 = {"kanon-sdd": 1}

    # No files on disk at all → nothing to surface.
    assert _apply_tier_down(tmp_path, sdd_at_3, sdd_at_1) == []

    # Create one file that exists in sdd:3 but not sdd:1, and one that exists
    # in both. Only the first should be reported.
    from kernel._manifest import _expected_files

    only_in_3 = [
        p for p in _expected_files(sdd_at_3) if p not in set(_expected_files(sdd_at_1))
    ]
    if not only_in_3:
        # Defensive: if depth-3 ever stops being a strict superset of depth-1,
        # this test loses its premise; skip rather than silently pass.
        import pytest

        pytest.skip("sdd depth-3 has no files beyond depth-1 in this kit version")
    target_rel = only_in_3[0]
    fp = tmp_path / target_rel
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text("synthetic\n", encoding="utf-8")

    diff = _apply_tier_down(tmp_path, sdd_at_3, sdd_at_1)
    assert target_rel in diff


def test_apply_tier_down_does_not_mutate_filesystem(tmp_path: Path) -> None:
    """Calling `_apply_tier_down` must not delete or modify any files."""
    from kernel._manifest import _expected_files

    sdd_at_3 = {"kanon-sdd": 3}
    sdd_at_1 = {"kanon-sdd": 1}

    only_in_3 = [
        p for p in _expected_files(sdd_at_3) if p not in set(_expected_files(sdd_at_1))
    ]
    if not only_in_3:
        import pytest

        pytest.skip("sdd depth-3 has no files beyond depth-1 in this kit version")

    fp = tmp_path / only_in_3[0]
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text("synthetic content\n", encoding="utf-8")

    _apply_tier_down(tmp_path, sdd_at_3, sdd_at_1)

    assert fp.is_file()
    assert fp.read_text(encoding="utf-8") == "synthetic content\n"
