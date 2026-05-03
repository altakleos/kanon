"""Tests for _manifest.py and _scaffold.py edge cases not covered by CLI tests.

Targets uncovered lines: fenced-code-block parsing, section removal,
symlink handling, and unicode path handling.
"""

from __future__ import annotations

from pathlib import Path

# --- _manifest.py: _fenced_ranges edge cases ---


def test_fenced_ranges_unclosed_fence() -> None:
    """Unclosed fence treats rest of file as fenced (lines 86-87)."""
    from kernel._manifest import _fenced_ranges

    text = "before\n```\nfenced content\nno closing fence\n"
    ranges = _fenced_ranges(text)
    assert len(ranges) == 1
    # Unclosed fence extends to end of text.
    assert ranges[0][1] == len(text)


def test_fenced_ranges_tilde_fence() -> None:
    """Tilde fences (~~~) are recognized (lines 74-79)."""
    from kernel._manifest import _fenced_ranges

    text = "before\n~~~\nfenced\n~~~\nafter\n"
    ranges = _fenced_ranges(text)
    assert len(ranges) == 1
    start, end = ranges[0]
    assert "fenced" in text[start:end]


def test_fenced_ranges_nested_different_delimiters() -> None:
    """Backtick fence inside tilde fence doesn't close the tilde fence."""
    from kernel._manifest import _fenced_ranges

    text = "before\n~~~\n```\nnested\n```\n~~~\nafter\n"
    ranges = _fenced_ranges(text)
    # The ~~~ fence should close at the ~~~ closer, not the ``` closer.
    assert len(ranges) == 1


def test_fenced_ranges_longer_closer() -> None:
    """A closer with more backticks than the opener still closes (line 78)."""
    from kernel._manifest import _fenced_ranges

    text = "before\n```\nfenced\n````\nafter\n"
    ranges = _fenced_ranges(text)
    assert len(ranges) == 1


# --- _scaffold.py: _remove_section ---


def test_remove_section_missing_section() -> None:
    """_remove_section returns text unchanged when section doesn't exist."""
    from kernel._scaffold import _remove_section

    text = "# Header\n\nSome content.\n"
    assert _remove_section(text, "nonexistent") == text


def test_remove_section_present() -> None:
    """_remove_section strips the section and its markers."""
    from kernel._scaffold import _remove_section

    text = (
        "# Header\n\n"
        "<!-- kanon:begin:test-section -->\n"
        "section content\n"
        "<!-- kanon:end:test-section -->\n\n"
        "## Footer\n"
    )
    result = _remove_section(text, "test-section")
    assert "test-section" not in result
    assert "Footer" in result


# --- Edge case: symlink target directory ---


def test_write_tree_atomically_with_symlink_in_path(tmp_path: Path) -> None:
    """Scaffold writes work when target contains a symlink component."""
    from kernel._scaffold import _write_tree_atomically

    real_dir = tmp_path / "real"
    real_dir.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real_dir)
    _write_tree_atomically(link, {"test.txt": "content"}, force=True)
    assert (real_dir / "test.txt").read_text() == "content"


# --- Edge case: unicode in file paths ---


def test_write_tree_atomically_unicode_path(tmp_path: Path) -> None:
    """Scaffold handles unicode characters in file paths."""
    from kernel._scaffold import _write_tree_atomically

    _write_tree_atomically(tmp_path, {"docs/日本語.md": "# テスト\n"}, force=True)
    assert (tmp_path / "docs" / "日本語.md").read_text(encoding="utf-8") == "# テスト\n"


def test_atomic_write_text_unicode_content(tmp_path: Path) -> None:
    """atomic_write_text handles unicode content correctly."""
    from kernel._atomic import atomic_write_text

    target = tmp_path / "émojis_🎉.txt"
    atomic_write_text(target, "Ünïcödé content: 日本語 🚀\n")
    assert target.read_text(encoding="utf-8") == "Ünïcödé content: 日本語 🚀\n"


# --- Edge case: _config_aspects with empty aspects ---


def test_config_aspects_empty() -> None:
    """_config_aspects returns empty dict for empty aspects."""
    from kernel._scaffold import _config_aspects

    assert _config_aspects({}) == {}
    assert _config_aspects({"aspects": {}}) == {}
