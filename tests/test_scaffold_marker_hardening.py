"""Regression tests for line-anchored, fence-aware marker handling.

Covers:
    - Markers quoted inside fenced code blocks (``` and ~~~) are ignored.
    - Markers prefixed by non-whitespace characters (e.g., a `>` blockquote)
      are ignored.
    - Real markers padded with surrounding whitespace are still recognised.
    - The marker-balance counter only counts real markers.
    - A freshly-assembled AGENTS.md is a fixed point of `_merge_agents_md`.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from kanon._manifest import _find_section_pair, _iter_markers
from kanon._scaffold import (
    _assemble_agents_md,
    _merge_agents_md,
    _replace_section,
)


def _real_pair(section: str, body: str = "kit body") -> str:
    return f"<!-- kanon:begin:{section} -->\n{body}\n<!-- kanon:end:{section} -->\n"


def test_quoted_marker_in_backtick_fence_is_ignored() -> None:
    """A marker quoted inside a ``` fenced block must not be matched."""
    text = (
        "# Doc\n\n"
        "Markers look like:\n\n"
        "```markdown\n"
        "<!-- kanon:begin:sdd/plan-before-build -->\n"
        "fake content\n"
        "<!-- kanon:end:sdd/plan-before-build -->\n"
        "```\n\n"
        "Real ones below:\n\n"
        + _real_pair("sdd/plan-before-build", "real body")
    )
    pair = _find_section_pair(text, "sdd/plan-before-build")
    assert pair is not None
    # The pair must point at the real markers, not the quoted ones.
    bs, be, es, ee = pair
    assert "real body" in text[be:es]
    assert "fake content" not in text[be:es]
    # Replacement preserves the fenced block byte-for-byte.
    out = _replace_section(text, "sdd/plan-before-build", "new body")
    assert "fake content" in out
    assert "new body" in out
    assert "real body" not in out


def test_quoted_marker_in_tilde_fence_is_ignored() -> None:
    text = (
        _real_pair("sdd/x", "real")
        + "~~~\n<!-- kanon:begin:sdd/x -->\nspoof\n<!-- kanon:end:sdd/x -->\n~~~\n"
    )
    out = _replace_section(text, "sdd/x", "REPLACED")
    assert "REPLACED" in out
    assert "spoof" in out  # untouched inside fence


def test_blockquote_prefixed_pseudo_marker_is_ignored() -> None:
    text = (
        "> <!-- kanon:begin:sdd/x -->\n"
        "> fake\n"
        "> <!-- kanon:end:sdd/x -->\n"
    )
    assert _find_section_pair(text, "sdd/x") is None
    # No-op merge: passing the same text in `new` would normally replace, but
    # since neither side has a real pair, _merge will treat as missing and
    # call _remove_section, which is a no-op when no pair exists.
    out = _replace_section(text, "sdd/x", "REPLACED")
    assert out == text  # nothing changed


def test_inline_prefixed_pseudo_marker_is_ignored() -> None:
    """A marker preceded by other characters on the same line is not a marker."""
    text = "Inline: <!-- kanon:begin:sdd/x --> and trailing <!-- kanon:end:sdd/x -->\n"
    assert _find_section_pair(text, "sdd/x") is None


def test_marker_with_surrounding_whitespace_is_recognised() -> None:
    """Tabs and spaces around the marker line are tolerated (still on its own line)."""
    text = (
        "intro\n"
        "\t<!-- kanon:begin:sdd/x --> \t\n"
        "old\n"
        "  <!-- kanon:end:sdd/x -->\n"
        "tail\n"
    )
    pair = _find_section_pair(text, "sdd/x")
    assert pair is not None
    out = _replace_section(text, "sdd/x", "NEW")
    assert "NEW" in out
    assert "old" not in out


def test_balance_counter_skips_fenced_markers() -> None:
    """The balance counter must count only real markers."""
    text = (
        "```\n<!-- kanon:begin:sdd/a -->\n```\n"
        "```\n<!-- kanon:end:sdd/a -->\n```\n"
        "```\n<!-- kanon:begin:sdd/b -->\n```\n"
        + _real_pair("sdd/x")
        + _real_pair("sdd/y")
    )
    begins = sum(1 for k, _, _, _ in _iter_markers(text) if k == "begin")
    ends = sum(1 for k, _, _, _ in _iter_markers(text) if k == "end")
    assert begins == 2
    assert ends == 2


def test_assembled_agents_md_is_merge_fixed_point() -> None:
    """assemble(...) must round-trip through merge(_, assemble(...)) byte-identically."""
    aspects = {"sdd": 3, "worktrees": 2, "testing": 2}
    fresh = _assemble_agents_md(aspects, "test-project")
    merged = _merge_agents_md(fresh, fresh)
    assert merged == fresh, (
        "merge(existing, fresh) is not the identity for a freshly-assembled AGENTS.md"
    )


def test_repo_agents_md_round_trips() -> None:
    """The repo's own AGENTS.md should be a fixed point of merge(_, assemble(...))."""
    from kanon._scaffold import _config_aspects, _read_config

    repo_root = Path(__file__).resolve().parents[1]
    config = _read_config(repo_root)
    aspects = _config_aspects(config)
    existing = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    fresh = _assemble_agents_md(aspects, repo_root.name)
    merged = _merge_agents_md(existing, fresh)
    assert merged == existing, textwrap.dedent(
        """\
        AGENTS.md is not a fixed point of merge(existing, assemble()).
        This means a `kanon upgrade` or `aspect set-depth` against the repo
        itself would mutate AGENTS.md — investigate before shipping.
        """
    )
