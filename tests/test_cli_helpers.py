"""Tests for kanon internal helpers: _manifest.py, _scaffold.py, _cli_aspect.py."""

from __future__ import annotations

from pathlib import Path

import click
import pytest
import yaml


# Helper for fake kit roots used by monkeypatched manifest tests.
def _make_fake_kit(tmp: Path | None, content: str) -> Path:
    import tempfile

    d = Path(tempfile.mkdtemp())
    (d / "manifest.yaml").write_text(content, encoding="utf-8")
    return d






# ---------------------------------------------------------------------------
# Coverage-gap tests: _manifest.py, _scaffold.py, cli.py uncovered branches
# ---------------------------------------------------------------------------


# --- _manifest.py: _load_top_manifest validation errors ---


# NOTE: The six test_load_top_manifest_* tests that lived here previously
# (validating the YAML aspects: block schema by stubbing _kit_root() to point at
# malformed fake kits) were retired by Phase A.2.2 / ADR-0040: under the
# entry-point discovery model, _load_top_manifest() no longer validates the
# YAML's aspects: block (sourced from entry-points instead). Equivalent
# validation against entry-point MANIFESTs lives in tests/test_aspect_registry.py.


# Helper for fake kit roots used by monkeypatched manifest tests.
def _make_fake_kit(tmp: Path | None, content: str) -> Path:
    import tempfile

    d = Path(tempfile.mkdtemp())
    (d / "manifest.yaml").write_text(content, encoding="utf-8")
    return d



# --- _manifest.py: _parse_frontmatter edge cases ---


def test_parse_frontmatter_no_end_marker() -> None:
    """Line 170: frontmatter start but no closing ---."""
    from kanon_core._manifest import _parse_frontmatter

    assert _parse_frontmatter("---\ntitle: hello\nno closing") == {}



def test_parse_frontmatter_non_dict_yaml() -> None:
    """Line 173: frontmatter YAML parses to non-dict."""
    from kanon_core._manifest import _parse_frontmatter

    assert _parse_frontmatter("---\n- a list item\n---\nbody") == {}



# --- _manifest.py: _namespaced_section unprefixed path ---


def test_namespaced_section_unprefixed() -> None:
    """Line 147→149: section in _UNPREFIXED_SECTIONS stays unprefixed."""
    from kanon_core._manifest import _namespaced_section

    assert _namespaced_section("kanon-sdd", "protocols-index") == "protocols-index"



# --- _scaffold.py: _read_config / _migrate_legacy_config ---


def test_read_config_malformed(tmp_path: Path) -> None:
    """Line 45: config.yaml is not a dict."""
    from kanon_core._scaffold import _read_config

    config_dir = tmp_path / ".kanon"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text('"just a string"', encoding="utf-8")
    with pytest.raises(click.ClickException, match="Malformed"):
        _read_config(tmp_path)



def test_load_yaml_invalid_syntax(tmp_path: Path) -> None:
    """_load_yaml wraps yaml.YAMLError into ClickException."""
    from kanon_core._manifest import _load_yaml

    bad = tmp_path / "bad.yaml"
    bad.write_text(":\n  - :\n  bad: [unterminated", encoding="utf-8")
    with pytest.raises(click.ClickException, match="Invalid YAML"):
        _load_yaml(bad)



def test_load_yaml_wrong_type(tmp_path: Path) -> None:
    """_load_yaml raises ClickException when top-level type doesn't match."""
    from kanon_core._manifest import _load_yaml

    f = tmp_path / "list.yaml"
    f.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(click.ClickException, match="expected a YAML mapping"):
        _load_yaml(f, expected_type=dict)



def test_migrate_legacy_config_no_tier_no_aspects() -> None:
    """Line 54: config has neither 'aspects' nor 'tier'."""
    from kanon_core._scaffold import _migrate_legacy_config

    result = _migrate_legacy_config({"kit_version": "1.0"})
    assert result == {"kit_version": "1.0"}



# --- _scaffold.py: _load_harnesses / _render_shims ---


def test_load_harnesses_missing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Line 101: harnesses.yaml doesn't exist."""
    from kanon_core._scaffold import _load_harnesses

    def _missing(filename: str) -> str:
        raise FileNotFoundError(filename)

    monkeypatch.setattr("kanon_core._manifest._kit_data", _missing)
    assert _load_harnesses() == []



def test_load_harnesses_malformed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Line 104: harnesses.yaml is not a list."""
    from kanon_core._scaffold import _load_harnesses

    monkeypatch.setattr(
        "kanon_core._manifest._kit_data", lambda f: "not_a_list: true"
    )
    with pytest.raises(click.ClickException, match="expected a YAML list"):
        _load_harnesses()



def test_render_shims_frontmatter_and_plain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lines 142, 147: _render_shims with and without frontmatter."""
    from kanon_core._scaffold import _render_shims

    harnesses = [
        {"path": "with_fm.md", "body": "hello\n", "frontmatter": {"key": "val"}},
        {"path": "plain.md", "body": "plain body\n"},
    ]
    monkeypatch.setattr(
        "kanon_core._manifest._kit_data",
        lambda f: yaml.safe_dump(harnesses),
    )
    result = _render_shims()
    assert "---" in result["with_fm.md"]
    assert "key: val" in result["with_fm.md"]
    assert result["plain.md"] == "plain body\n"



# --- _scaffold.py: _replace_section / _remove_section / _insert_section ---


def test_replace_section_no_markers() -> None:
    """Line 271→274: markers not found, text returned unchanged."""
    from kanon_core._scaffold import _replace_section

    text = "no markers here"
    assert _replace_section(text, "missing", "content") == text



def test_remove_section_no_markers() -> None:
    """_remove_section with no markers returns text unchanged."""
    from kanon_core._scaffold import _remove_section

    text = "no markers here"
    assert _remove_section(text, "missing") == text



def test_insert_section_no_anchor_no_trailing_newline() -> None:
    """Lines 289-291: no anchor found, text doesn't end with newline."""
    from kanon_core._scaffold import _insert_section

    result = _insert_section("some text", "test-section", "new content")
    assert "<!-- kanon:begin:test-section -->" in result
    assert "<!-- kanon:end:test-section -->" in result
    assert "new content" in result



# --- _scaffold.py: _render_protocols_index edge cases ---


def test_render_protocols_index_no_protocols() -> None:
    """Line 217: no protocols at depth 0 → 'No protocols active' message."""
    from kanon_core._scaffold import _render_protocols_index

    result = _render_protocols_index({"kanon-sdd": 0})
    assert "No protocols active" in result



# --- _scaffold.py: _render_kit_md returns None ---


# Phase A.3: test_render_kit_md_no_kit_file retired with _render_kit_md (per ADR-0048).



# --- _scaffold.py: _migrate_flat_protocols edge cases ---


def test_migrate_flat_protocols_no_flat_files(tmp_path: Path) -> None:
    """Line 375: protocols dir exists but no flat .md files."""
    from kanon_core._scaffold import _migrate_flat_protocols

    protocols_dir = tmp_path / ".kanon" / "protocols"
    protocols_dir.mkdir(parents=True)
    assert _migrate_flat_protocols(tmp_path, {"kanon-sdd": 1}) is False



def test_migrate_flat_protocols_no_sdd_aspect(tmp_path: Path) -> None:
    """Line 380: flat files exist but 'kanon-sdd' not in aspects."""
    from kanon_core._scaffold import _migrate_flat_protocols

    protocols_dir = tmp_path / ".kanon" / "protocols"
    protocols_dir.mkdir(parents=True)
    (protocols_dir / "test.md").write_text("test", encoding="utf-8")
    assert _migrate_flat_protocols(tmp_path, {"other": 1}) is False



def test_migrate_flat_protocols_dest_exists(tmp_path: Path) -> None:
    """Line 386: destination already exists → unlink source instead of rename."""
    from kanon_core._scaffold import _migrate_flat_protocols

    protocols_dir = tmp_path / ".kanon" / "protocols"
    sdd_dir = protocols_dir / "kanon-sdd"
    sdd_dir.mkdir(parents=True)
    (protocols_dir / "dup.md").write_text("flat version", encoding="utf-8")
    (sdd_dir / "dup.md").write_text("already there", encoding="utf-8")
    assert _migrate_flat_protocols(tmp_path, {"kanon-sdd": 1}) is True
    assert not (protocols_dir / "dup.md").exists()
    assert (sdd_dir / "dup.md").read_text() == "already there"



# --- _scaffold.py: _write_tree_atomically skip existing ---


def test_write_tree_atomically_skips_existing(tmp_path: Path) -> None:
    """Line 363: existing file not overwritten when force=False."""
    from kanon_core._scaffold import _write_tree_atomically

    (tmp_path / "existing.txt").write_text("original", encoding="utf-8")
    _write_tree_atomically(tmp_path, {"existing.txt": "new content"}, force=False)
    assert (tmp_path / "existing.txt").read_text() == "original"



def test_write_tree_atomically_rejects_path_traversal(tmp_path: Path) -> None:
    """Scaffold paths escaping the target directory are rejected."""
    from kanon_core._scaffold import _write_tree_atomically

    with pytest.raises(click.ClickException, match="Path escapes target directory"):
        _write_tree_atomically(tmp_path, {"../../escape.txt": "malicious"}, force=True)



def test_rewrite_assembled_views_missing_agents_md(tmp_path: Path) -> None:
    """_rewrite_assembled_views returns early when AGENTS.md is absent."""
    from kanon_core._cli_aspect import _rewrite_assembled_views

    # Should not raise — just returns early.
    _rewrite_assembled_views(tmp_path, {"kanon-sdd": 1}, "test-project")
    assert not (tmp_path / "AGENTS.md").exists()



def test_config_aspects_rejects_malformed_entry(tmp_path: Path) -> None:
    """_config_aspects raises ClickException when an entry is not a dict."""
    from kanon_core._scaffold import _config_aspects

    with pytest.raises(click.ClickException, match="must be a mapping"):
        _config_aspects({"aspects": {"kanon-sdd": 2}})



def test_migrate_legacy_config_rejects_non_dict_aspects() -> None:
    """_migrate_legacy_config raises when aspects is not a dict."""
    from kanon_core._scaffold import _migrate_legacy_config

    with pytest.raises(click.ClickException, match="must be a mapping"):
        _migrate_legacy_config({"aspects": "garbage"})



# --- _scaffold.py: _rewrite_legacy_markers ---


def test_rewrite_legacy_markers() -> None:
    """Covers the legacy marker rewriting path in _rewrite_legacy_markers."""
    from kanon_core._scaffold import _rewrite_legacy_markers

    text = (
        "<!-- kanon:begin:protocols-index -->\nold\n"
        "<!-- kanon:end:protocols-index -->\n"
    )
    result = _rewrite_legacy_markers(text)
    # protocols-index is unprefixed — it should remain unchanged.
    assert "<!-- kanon:begin:protocols-index -->" in result



# --- ADR-0028 / Phase 2: config migration round-trips (T17) ---


def test_migrate_legacy_config_v1_to_v3_produces_namespaced_key() -> None:
    """A v1 config (`tier: N`) migrates to v3 with the canonical `kanon-sdd` key."""
    from kanon_core._scaffold import _migrate_legacy_config

    v1 = {"kit_version": "0.1.0a1", "tier": 2, "tier_set_at": "2026-04-25T00:00:00+00:00"}
    v3 = _migrate_legacy_config(v1)
    assert "tier" not in v3
    assert "aspects" in v3
    assert list(v3["aspects"]) == ["kanon-sdd"]
    assert v3["aspects"]["kanon-sdd"]["depth"] == 2
    assert v3["aspects"]["kanon-sdd"]["enabled_at"] == "2026-04-25T00:00:00+00:00"



def test_migrate_legacy_config_v3_is_idempotent_no_op() -> None:
    """A config already in v3 (namespaced keys) returns unchanged — no rewrite."""
    from kanon_core._scaffold import _migrate_legacy_config

    v3 = {
        "kit_version": "0.3.0",
        "aspects": {
            "kanon-sdd": {"depth": 1, "enabled_at": "x", "config": {}},
            "kanon-worktrees": {"depth": 2, "enabled_at": "x", "config": {}},
            "project-auth-policy": {"depth": 1, "enabled_at": "x", "config": {}},
        },
    }
    out = _migrate_legacy_config(v3)
    assert out == v3, "v3 → v3 must be a no-op (project-aspects INV-5 idempotency)"



def test_migrate_legacy_config_v2_all_six_aspects_round_trip() -> None:
    """A v2 config containing all six bare aspect keys migrates each to its
    `kanon-` form. Insertion order and config blocks survive."""
    from kanon_core._scaffold import _migrate_legacy_config

    v2 = {
        "kit_version": "0.2.0a6",
        "aspects": {
            bare: {
                "depth": 1,
                "enabled_at": f"2026-04-25T00:00:0{i}+00:00",
                "config": {"k": i} if i % 2 else {},
            }
            for i, bare in enumerate(
                ["sdd", "worktrees", "release", "testing", "security", "deps"]
            )
        },
    }
    v3 = _migrate_legacy_config(v2)
    assert set(v3["aspects"].keys()) == {
        "kanon-sdd", "kanon-worktrees", "kanon-release",
        "kanon-testing", "kanon-security", "kanon-deps",
    }
    # Per-entry payloads carry through unchanged.
    assert v3["aspects"]["kanon-sdd"]["depth"] == 1
    assert v3["aspects"]["kanon-sdd"]["enabled_at"] == "2026-04-25T00:00:00+00:00"
    assert v3["aspects"]["kanon-worktrees"]["config"] == {"k": 1}
    assert v3["aspects"]["kanon-release"]["config"] == {}



def test_migrate_legacy_config_mixed_state_hard_fails() -> None:
    """A config with both `<local>` and `kanon-<local>` keys hard-fails with a
    message that names every collision and asks for manual deduplication.
    """
    import click
    import pytest

    from kanon_core._scaffold import _migrate_legacy_config

    mixed = {
        "kit_version": "0.3.0",
        "aspects": {
            "sdd": {"depth": 1, "enabled_at": "a", "config": {}},
            "kanon-sdd": {"depth": 2, "enabled_at": "b", "config": {}},
            "worktrees": {"depth": 1, "enabled_at": "c", "config": {}},
            "kanon-worktrees": {"depth": 2, "enabled_at": "d", "config": {}},
        },
    }
    with pytest.raises(click.ClickException) as excinfo:
        _migrate_legacy_config(mixed)
    msg = excinfo.value.message
    # Both collisions named, sorted, in the canonical "<bare>` and `kanon-<bare>"
    # form so the user can grep for them in their config.
    assert "`sdd` and `kanon-sdd`" in msg
    assert "`worktrees` and `kanon-worktrees`" in msg
    assert "Hand-edit" in msg


# ---------------------------------------------------------------------------
# Coverage-gap tests: _cli_helpers.py uncovered branches
# ---------------------------------------------------------------------------


# --- _value_matches_schema_type (L36, L39-43) ---


@pytest.mark.parametrize(
    "value, expected, result",
    [
        ("hello", "string", True),
        (42, "string", False),
        (7, "integer", True),
        ("x", "integer", False),
        (3.14, "number", True),
        (7, "number", True),
        ("x", "number", False),
        (True, "boolean", True),
        (True, "integer", False),  # bool is subtype of int; must reject
        ("x", "unknown_type", False),  # fallback return False
    ],
)
def test_value_matches_schema_type(value: object, expected: str, result: bool) -> None:
    from kanon_core._cli_helpers import _value_matches_schema_type

    assert _value_matches_schema_type(value, expected) is result


# --- _parse_config_pair (L56, L67-68) ---


def test_parse_config_pair_missing_equals() -> None:
    """L56: no '=' in token raises ClickException."""
    from kanon_core._cli_helpers import _parse_config_pair

    with pytest.raises(click.ClickException, match="expected key=value"):
        _parse_config_pair("no-equals-here", None)


def test_parse_config_pair_malformed_yaml_value() -> None:
    """L67-68: YAML parse error in value raises ClickException."""
    from kanon_core._cli_helpers import _parse_config_pair

    with pytest.raises(click.ClickException, match="Invalid config value"):
        _parse_config_pair("key=: :\n  bad: [unterminated", None)


# --- _parse_aspects_flag (L106, L112, L117-118, L124, L129) ---


def _make_top(*names: str, depth_range: tuple[int, int] = (0, 3)) -> dict:
    """Build a minimal top-manifest dict for _parse_aspects_flag tests."""
    return {
        "aspects": {
            n: {"depth-range": list(depth_range)} for n in names
        }
    }


def test_parse_aspects_flag_missing_colon() -> None:
    """L106: token without ':' raises ClickException."""
    from kanon_core._cli_helpers import _parse_aspects_flag

    with pytest.raises(click.ClickException, match="expected name:depth"):
        _parse_aspects_flag("kanon-sdd", _make_top("kanon-sdd"))


def test_parse_aspects_flag_unknown_aspect() -> None:
    """L112: aspect not in top['aspects'] raises ClickException."""
    from kanon_core._cli_helpers import _parse_aspects_flag

    with pytest.raises(click.ClickException, match="Unknown aspect"):
        _parse_aspects_flag("kanon-nope:1", _make_top("kanon-sdd"))


def test_parse_aspects_flag_non_integer_depth() -> None:
    """L117-118: non-integer depth raises ClickException."""
    from kanon_core._cli_helpers import _parse_aspects_flag

    with pytest.raises(click.ClickException, match="must be an integer"):
        _parse_aspects_flag("kanon-sdd:abc", _make_top("kanon-sdd"))


def test_parse_aspects_flag_depth_out_of_range() -> None:
    """L124: depth outside declared range raises ClickException."""
    from kanon_core._cli_helpers import _parse_aspects_flag

    with pytest.raises(click.ClickException, match="outside range"):
        _parse_aspects_flag("kanon-sdd:9", _make_top("kanon-sdd", depth_range=(0, 3)))


def test_parse_aspects_flag_empty_result() -> None:
    """Whitespace-only tokens hit the missing-colon error."""
    from kanon_core._cli_helpers import _parse_aspects_flag

    with pytest.raises(click.ClickException, match="expected name:depth"):
        _parse_aspects_flag(" , ", _make_top("kanon-sdd"))


# --- _check_removal_dependents (L233, L237-238, L245) ---


def test_check_removal_dependents_depth_predicate() -> None:
    """L237: remaining aspect has a depth-predicate requiring the removed aspect."""
    from kanon_core._cli_helpers import _check_removal_dependents

    top = {
        "aspects": {
            "kanon-sdd": {"provides": [], "requires": []},
            "kanon-testing": {"provides": [], "requires": ["kanon-sdd >= 1"]},
        }
    }
    remaining = {"kanon-testing": 1}
    err = _check_removal_dependents("kanon-sdd", remaining, top)
    assert err is not None
    assert "Cannot remove" in err
    assert "kanon-testing" in err


def test_check_removal_dependents_skips_depth_zero(
) -> None:
    """L233: remaining aspect at depth 0 is skipped (continue branch)."""
    from kanon_core._cli_helpers import _check_removal_dependents

    top = {
        "aspects": {
            "kanon-sdd": {"provides": [], "requires": []},
            "kanon-testing": {"provides": [], "requires": ["kanon-sdd >= 1"]},
        }
    }
    # kanon-testing at depth 0 → skipped, no error
    remaining = {"kanon-testing": 0}
    assert _check_removal_dependents("kanon-sdd", remaining, top) is None


def test_check_removal_dependents_depth_pred_different_aspect() -> None:
    """L237->234: depth-predicate names a different aspect than the one being removed."""
    from kanon_core._cli_helpers import _check_removal_dependents

    top = {
        "aspects": {
            "kanon-sdd": {"provides": [], "requires": []},
            "kanon-worktrees": {"provides": [], "requires": []},
            "kanon-testing": {"provides": [], "requires": ["kanon-worktrees >= 1"]},
        }
    }
    # Removing kanon-sdd, but kanon-testing's predicate references kanon-worktrees → no error
    remaining = {"kanon-testing": 1, "kanon-worktrees": 1}
    assert _check_removal_dependents("kanon-sdd", remaining, top) is None


def test_check_removal_dependents_capability_not_in_provides() -> None:
    """L244-245: remaining aspect requires a capability the removed aspect doesn't provide."""
    from kanon_core._cli_helpers import _check_removal_dependents

    top = {
        "aspects": {
            "kanon-sdd": {"provides": ["planning-discipline"], "requires": []},
            "kanon-testing": {"provides": [], "requires": ["other-capability"]},
        }
    }
    remaining = {"kanon-testing": 1}
    # kanon-sdd doesn't provide "other-capability", so the predicate is skipped (continue).
    err = _check_removal_dependents("kanon-sdd", remaining, top)
    assert err is None


def test_check_removal_dependents_sole_supplier() -> None:
    """L245: removed aspect is the sole supplier of a required capability."""
    from kanon_core._cli_helpers import _check_removal_dependents

    top = {
        "aspects": {
            "kanon-sdd": {"provides": ["planning-discipline"], "requires": []},
            "kanon-testing": {"provides": [], "requires": ["planning-discipline"]},
        }
    }
    remaining = {"kanon-testing": 1}
    err = _check_removal_dependents("kanon-sdd", remaining, top)
    assert err is not None
    assert "capability" in err
    assert "no longer be provided" in err


# --- _check_pending_recovery (L309-310) ---


def test_check_pending_recovery_graph_rename_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L309-310: graph-rename sentinel present but recovery raises ClickException → fallthrough to warning."""
    from kanon_core._cli_helpers import _check_pending_recovery

    kanon_dir = tmp_path / ".kanon"
    kanon_dir.mkdir()
    (kanon_dir / ".pending").write_text("graph-rename", encoding="utf-8")

    def _mock_recover(target: Path) -> bool:
        raise click.ClickException("recovery failed")

    monkeypatch.setattr("kanon_core._cli_helpers.recover_pending_rename", _mock_recover, raising=False)
    # The import is lazy inside the function, so we patch the module-level import target.
    import kanon_core._cli_helpers as mod
    monkeypatch.setattr(mod, "recover_pending_rename", _mock_recover, raising=False)

    # Actually, the function does a local import: `from kanon_core._rename import recover_pending_rename`
    # We need to patch it at the source module.
    monkeypatch.setattr("kanon_core._rename.recover_pending_rename", _mock_recover)

    captured = []
    monkeypatch.setattr(click, "echo", lambda msg, err=False: captured.append(msg))

    _check_pending_recovery(tmp_path)
    assert any("Warning" in m and "graph-rename" in m for m in captured)
