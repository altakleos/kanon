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

from kanon_core._manifest import _find_section_pair, _iter_markers
from kanon_core._scaffold import (
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
        "<!-- kanon:begin:kanon-sdd/body -->\n"
        "fake content\n"
        "<!-- kanon:end:kanon-sdd/body -->\n"
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
        _real_pair("kanon-sdd/x", "real")
        + "~~~\n<!-- kanon:begin:kanon-sdd/x -->\nspoof\n<!-- kanon:end:kanon-sdd/x -->\n~~~\n"
    )
    out = _replace_section(text, "kanon-sdd/x", "REPLACED")
    assert "REPLACED" in out
    assert "spoof" in out  # untouched inside fence


def test_blockquote_prefixed_pseudo_marker_is_ignored() -> None:
    text = (
        "> <!-- kanon:begin:kanon-sdd/x -->\n"
        "> fake\n"
        "> <!-- kanon:end:kanon-sdd/x -->\n"
    )
    assert _find_section_pair(text, "kanon-sdd/x") is None
    # No-op merge: passing the same text in `new` would normally replace, but
    # since neither side has a real pair, _merge will treat as missing and
    # call _remove_section, which is a no-op when no pair exists.
    out = _replace_section(text, "kanon-sdd/x", "REPLACED")
    assert out == text  # nothing changed


def test_inline_prefixed_pseudo_marker_is_ignored() -> None:
    """A marker preceded by other characters on the same line is not a marker."""
    text = "Inline: <!-- kanon:begin:kanon-sdd/x --> and trailing <!-- kanon:end:kanon-sdd/x -->\n"
    assert _find_section_pair(text, "kanon-sdd/x") is None


def test_marker_with_surrounding_whitespace_is_recognised() -> None:
    """Tabs and spaces around the marker line are tolerated (still on its own line)."""
    text = (
        "intro\n"
        "\t<!-- kanon:begin:kanon-sdd/x --> \t\n"
        "old\n"
        "  <!-- kanon:end:kanon-sdd/x -->\n"
        "tail\n"
    )
    pair = _find_section_pair(text, "kanon-sdd/x")
    assert pair is not None
    out = _replace_section(text, "kanon-sdd/x", "NEW")
    assert "NEW" in out
    assert "old" not in out


def test_balance_counter_skips_fenced_markers() -> None:
    """The balance counter must count only real markers."""
    text = (
        "```\n<!-- kanon:begin:kanon-sdd/a -->\n```\n"
        "```\n<!-- kanon:end:kanon-sdd/a -->\n```\n"
        "```\n<!-- kanon:begin:kanon-sdd/b -->\n```\n"
        + _real_pair("kanon-sdd/x")
        + _real_pair("sdd/y")
    )
    begins = sum(1 for k, _, _, _ in _iter_markers(text) if k == "begin")
    ends = sum(1 for k, _, _, _ in _iter_markers(text) if k == "end")
    assert begins == 2
    assert ends == 2


def test_assembled_agents_md_is_merge_fixed_point() -> None:
    """assemble(...) must round-trip through merge(_, assemble(...)) byte-identically."""
    aspects = {"kanon-sdd": 3, "kanon-worktrees": 2, "kanon-testing": 2}
    fresh = _assemble_agents_md(aspects, "test-project")
    merged = _merge_agents_md(fresh, fresh)
    assert merged == fresh, (
        "merge(existing, fresh) is not the identity for a freshly-assembled AGENTS.md"
    )


def test_repo_agents_md_round_trips() -> None:
    """The repo's own AGENTS.md should be a fixed point of merge(_, assemble(...))."""
    from kanon_core._scaffold import _config_aspects, _read_config

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


# --- ADR-0028 / Phase 2: AGENTS.md marker migration (T18) ---


def test_rewrite_legacy_markers_handles_all_six_bare_aspects() -> None:
    """v0.2 bare-prefixed markers (`<aspect>/<section>`) migrate to v3 namespaced
    (`kanon-<aspect>/<section>`) for every kit-shipped aspect — not just sdd.
    """
    from kanon_core._scaffold import _rewrite_legacy_markers

    bare = "\n".join(
        f"<!-- kanon:begin:{a}/body -->\nbody for {a}\n<!-- kanon:end:{a}/body -->"
        for a in ("sdd", "worktrees", "release", "testing", "security", "deps")
    )
    result = _rewrite_legacy_markers(bare)
    for a in ("sdd", "worktrees", "release", "testing", "security", "deps"):
        assert f"<!-- kanon:begin:kanon-{a}/body -->" in result, (
            f"missing namespaced begin marker for {a}"
        )
        assert f"<!-- kanon:end:kanon-{a}/body -->" in result, (
            f"missing namespaced end marker for {a}"
        )
        assert f"<!-- kanon:begin:{a}/body -->" not in result, (
            f"bare begin marker for {a} not migrated"
        )


def test_rewrite_legacy_markers_idempotent_on_already_namespaced() -> None:
    """A second call on an already-namespaced text is a no-op (project-aspects INV-5)."""
    from kanon_core._scaffold import _rewrite_legacy_markers

    namespaced = (
        "<!-- kanon:begin:kanon-sdd/body -->\n"
        "body\n"
        "<!-- kanon:end:kanon-sdd/body -->\n"
    )
    once = _rewrite_legacy_markers(namespaced)
    twice = _rewrite_legacy_markers(once)
    assert once == namespaced
    assert twice == once


def test_rewrite_legacy_markers_preserves_user_prose_outside_markers() -> None:
    """User-authored prose outside any kit marker survives the rewrite verbatim."""
    from kanon_core._scaffold import _rewrite_legacy_markers

    text = (
        "# AGENTS.md\n"
        "\n"
        "## My team's house rules\n"
        "Some user prose here that mentions sdd in passing.\n"
        "Don't touch this paragraph during migration.\n"
        "\n"
        "<!-- kanon:begin:protocols-index -->\n"
        "kit body\n"
        "<!-- kanon:end:protocols-index -->\n"
        "\n"
        "More user prose after the marker.\n"
    )
    result = _rewrite_legacy_markers(text)
    # protocols-index is unprefixed — should remain unchanged:
    assert "<!-- kanon:begin:protocols-index -->" in result
    # User prose preserved verbatim:
    assert "## My team's house rules" in result
    assert "Some user prose here that mentions sdd in passing." in result
    assert "Don't touch this paragraph during migration." in result
    assert "More user prose after the marker." in result


def test_rewrite_legacy_markers_preserves_balance() -> None:
    """The number of begin and end markers in the migrated text equals the input.
    Migration must not drop, duplicate, or leave half-rewritten pairs.
    """
    import re as _re

    from kanon_core._scaffold import _rewrite_legacy_markers

    text = (
        "<!-- kanon:begin:sdd/plan-before-build -->\nA\n"
        "<!-- kanon:end:sdd/plan-before-build -->\n"
        "<!-- kanon:begin:worktrees/branch-hygiene -->\nB\n"
        "<!-- kanon:end:worktrees/branch-hygiene -->\n"
        "<!-- kanon:begin:protocols-index -->\nC\n"
        "<!-- kanon:end:protocols-index -->\n"
    )
    result = _rewrite_legacy_markers(text)
    in_begins = len(_re.findall(r"<!-- kanon:begin:[^ ]+ -->", text))
    in_ends = len(_re.findall(r"<!-- kanon:end:[^ ]+ -->", text))
    out_begins = len(_re.findall(r"<!-- kanon:begin:[^ ]+ -->", result))
    out_ends = len(_re.findall(r"<!-- kanon:end:[^ ]+ -->", result))
    assert in_begins == out_begins == 3
    assert in_ends == out_ends == 3
    # `protocols-index` stays unprefixed by design (cross-aspect catalog).
    assert "<!-- kanon:begin:protocols-index -->" in result
    assert "<!-- kanon:begin:kanon-protocols-index -->" not in result
