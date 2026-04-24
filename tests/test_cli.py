"""Tests for the kanon CLI: init, upgrade, verify, tier set.

Includes tier-migration round-trip smoke: 0 → 1 → 2 → 3 → 2 → 1 → 0
preserves user-authored files and verify stays OK at every step.
"""

from __future__ import annotations

import json
from pathlib import Path

import click
import pytest
import yaml
from click.testing import CliRunner

from kanon import __version__
from kanon.cli import main

# --- init ---


@pytest.mark.parametrize("tier", [0, 1, 2, 3])
def test_init_scaffolds_all_required_files(tmp_path: Path, tier: int) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--tier", str(tier)])
    assert result.exit_code == 0, result.output

    assert (target / "AGENTS.md").is_file()
    assert (target / "CLAUDE.md").is_file()
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["sdd"]["depth"] == tier
    assert config["kit_version"] == __version__
    assert "enabled_at" in config["aspects"]["sdd"]


def _extract_verify_json(output: str) -> dict:
    """Extract the first JSON object from `verify` output (report precedes the human summary)."""
    start = output.find("{")
    end = output.rfind("}")
    return json.loads(output[start:end + 1])


@pytest.mark.parametrize("tier", [1, 2, 3])
def test_init_verify_returns_ok(tmp_path: Path, tier: int) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", str(tier)])
    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code == 0, result.output
    report = _extract_verify_json(result.output)
    assert report["status"] == "ok"
    assert report["aspects"]["sdd"] == tier


def test_init_rejects_existing_without_force(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Second init without --force should fail.
    result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    assert result.exit_code != 0
    assert "already exists" in result.output.lower()


def test_init_writes_all_shims(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    expected_shims = [
        "CLAUDE.md",
        ".kiro/steering/kanon.md",
        ".cursor/rules/kanon.mdc",
        ".github/copilot-instructions.md",
        ".windsurf/rules/kanon.md",
        ".clinerules/kanon.md",
        ".roo/rules/kanon.md",
        ".aiassistant/rules/kanon.md",
    ]
    for shim_path in expected_shims:
        assert (target / shim_path).is_file(), f"missing shim: {shim_path}"


def test_shims_are_pointers_not_duplicates(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    # Shims should be short — well under 1000 chars — and must not contain
    # the plan-before-build rule text (which is AGENTS.md's job).
    for shim_name in ["CLAUDE.md", ".cursor/rules/kanon.mdc", ".windsurf/rules/kanon.md"]:
        content = (target / shim_name).read_text(encoding="utf-8")
        assert len(content) < 1000
        assert "Required: Plan Before Build" not in content


# --- protocol layer + kit.md ---


_EXPECTED_PROTOCOLS_BY_TIER: dict[int, set[str]] = {
    0: set(),
    1: {"tier-up-advisor.md", "verify-triage.md"},
    2: {"tier-up-advisor.md", "verify-triage.md", "spec-review.md"},
    3: {"tier-up-advisor.md", "verify-triage.md", "spec-review.md"},
}


@pytest.mark.parametrize("tier", [0, 1, 2, 3])
def test_protocols_scaffolded_at_correct_tier(tmp_path: Path, tier: int) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", str(tier)])
    protocols_dir = target / ".kanon" / "protocols" / "sdd"
    actual: set[str] = (
        {p.name for p in protocols_dir.glob("*.md")}
        if protocols_dir.exists()
        else set()
    )
    assert actual == _EXPECTED_PROTOCOLS_BY_TIER[tier]


@pytest.mark.parametrize("tier", [0, 1, 2, 3])
def test_kit_md_scaffolded_at_all_tiers(tmp_path: Path, tier: int) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", str(tier)])
    kit_md = target / ".kanon" / "kit.md"
    assert kit_md.is_file(), f"kit.md missing at tier {tier}"
    text = kit_md.read_text(encoding="utf-8")
    # Placeholders fully substituted.
    assert "${tier}" not in text
    assert "${project_name}" not in text
    assert f"**Tier:** {tier}" in text


@pytest.mark.parametrize("tier", [1, 2, 3])
def test_protocols_index_marker_present_tier1_plus(tmp_path: Path, tier: int) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", str(tier)])
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:protocols-index -->" in agents
    assert "<!-- kanon:end:protocols-index -->" in agents
    assert "tier-up-advisor" in agents
    assert "verify-triage" in agents
    if tier >= 2:
        assert "spec-review" in agents
    else:
        assert "spec-review" not in agents


def test_protocols_index_absent_at_tier_0(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "0"])
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:protocols-index -->" not in agents


def test_init_preserves_user_content_outside_markers(tmp_path: Path) -> None:
    """User content in AGENTS.md outside kit markers must survive `upgrade`."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    agents_md = target / "AGENTS.md"
    original = agents_md.read_text(encoding="utf-8")
    # Add a user-authored section at the end.
    user_block = "\n## Project-specific notes (user-authored)\n\nDo not overwrite me.\n"
    agents_md.write_text(original + user_block, encoding="utf-8")

    # `upgrade` should leave user content intact (kit version unchanged so it's a noop,
    # but the merge logic is still exercised on tier-set).
    result = runner.invoke(main, ["tier", "set", str(target), "2"])
    assert result.exit_code == 0, result.output
    after = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "Project-specific notes (user-authored)" in after
    assert "Do not overwrite me." in after


# --- tier set ---


def test_tier_set_idempotent(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    # Running `tier set 2` on a tier-2 project is a noop (exit 0, no changes).
    result = runner.invoke(main, ["tier", "set", str(target), "2"])
    assert result.exit_code == 0
    assert "noop" in result.output.lower() or "tier already 2" in result.output.lower()


def test_tier_up_additive_only(tmp_path: Path) -> None:
    """Tier-up from 1 to 3 adds new files and never touches existing ones."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    # Capture tier-1 file contents.
    tier1_files = {
        p.relative_to(target): p.read_text(encoding="utf-8")
        for p in target.rglob("*")
        if p.is_file() and ".kanon" not in p.parts
    }

    runner.invoke(main, ["tier", "set", str(target), "3"])

    # Every tier-1 file must still exist with identical content (except AGENTS.md,
    # which has new marker sections inserted — but user content outside markers
    # must be preserved).
    for rel, content in tier1_files.items():
        p = target / rel
        assert p.is_file(), f"tier-up removed file: {rel}"
        if rel == Path("AGENTS.md"):
            # AGENTS.md may have gained new marker sections; that's expected.
            # But every non-marker line from the original must still be present,
            # unless it's inside a kit-managed marker block (body, sections).
            new_content = p.read_text(encoding="utf-8")
            marker_depth = 0
            for line in content.splitlines():
                if "<!-- kanon:begin:" in line:
                    marker_depth += 1
                    continue
                if "<!-- kanon:end:" in line:
                    marker_depth -= 1
                    continue
                if marker_depth > 0 or not line.strip():
                    continue
                assert line in new_content or line.startswith("#"), f"tier-up lost non-marker line: {line!r}"
        else:
            assert p.read_text(encoding="utf-8") == content, f"tier-up modified: {rel}"


def test_tier_down_is_non_destructive(tmp_path: Path) -> None:
    """Tier-down from 3 to 0 leaves all artifact directories in place."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "3"])

    # Capture full tier-3 file list.
    tier3_files = {
        p.relative_to(target) for p in target.rglob("*") if p.is_file()
    }

    result = runner.invoke(main, ["tier", "set", str(target), "0"])
    assert result.exit_code == 0
    assert "non-destructive" in result.output.lower()

    # All tier-3 files still exist (except AGENTS.md and config.yaml which are rewritten).
    for rel in tier3_files:
        if rel == Path("AGENTS.md") or rel == Path(".kanon/config.yaml"):
            continue
        assert (target / rel).exists(), f"tier-down removed: {rel}"


@pytest.mark.parametrize(
    "chain",
    [
        [0, 1, 2, 3, 2, 1, 0],  # full up then full down
        [1, 3, 0, 2],            # arbitrary hops
    ],
)
def test_tier_migration_round_trip_preserves_user_file(tmp_path: Path, chain: list[int]) -> None:
    """User-authored files survive every tier migration."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", str(chain[0])])

    # Add a user file and capture its content.
    user_file = target / "USER_NOTES.md"
    user_content = "# User notes\n\nThis file belongs to me, not the kit.\n"
    user_file.write_text(user_content, encoding="utf-8")

    for target_tier in chain[1:]:
        result = runner.invoke(main, ["tier", "set", str(target), str(target_tier)])
        assert result.exit_code == 0, result.output
        assert user_file.is_file(), f"user file deleted after tier set {target_tier}"
        assert user_file.read_text(encoding="utf-8") == user_content, (
            f"user file modified after tier set {target_tier}"
        )
        # verify passes at every step.
        verify_result = runner.invoke(main, ["verify", str(target)])
        assert verify_result.exit_code == 0, f"verify failed at tier {target_tier}: {verify_result.output}"


# --- verify ---


def test_verify_fails_on_missing_file(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    (target / "docs" / "development-process.md").unlink()
    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code != 0
    assert "missing required file" in result.output.lower()


def test_verify_fails_on_missing_marker(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    agents = target / "AGENTS.md"
    # Strip all marker sections.
    text = agents.read_text(encoding="utf-8")
    # Remove plan-before-build markers entirely.
    text = text.replace("<!-- kanon:begin:sdd/plan-before-build -->", "")
    text = text.replace("<!-- kanon:end:sdd/plan-before-build -->", "")
    agents.write_text(text, encoding="utf-8")
    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code != 0
    assert "marker" in result.output.lower()


def test_verify_fails_without_config(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["verify", str(tmp_path)])
    assert result.exit_code != 0


# --- --version ---


def test_version_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


# --- upgrade ---


def test_upgrade_bumps_version(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Patch config to an old version.
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["kit_version"] = "0.0.0"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert updated["kit_version"] == __version__
    assert "0.0.0" in result.output
    assert __version__ in result.output


def test_upgrade_already_current(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    assert "already at" in result.output.lower()


def test_upgrade_not_a_kanon_project(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result.exit_code != 0
    assert "not a kanon project" in result.output.lower()


def test_upgrade_malformed_config(tmp_path: Path) -> None:
    runner = CliRunner()
    config_dir = tmp_path / ".kanon"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("bad", encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result.exit_code != 0
    assert "malformed" in result.output.lower()


def test_upgrade_legacy_v1_migration(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    # Rewrite config to legacy v1 format.
    config_path = target / ".kanon" / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({"kit_version": "0.0.1", "tier": 2}, sort_keys=False),
        encoding="utf-8",
    )

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert "aspects" in updated
    assert "tier" not in updated


def test_upgrade_preserves_user_content(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Add user content to AGENTS.md.
    agents = target / "AGENTS.md"
    agents.write_text(
        agents.read_text(encoding="utf-8") + "\n<!-- MY CUSTOM SECTION -->\nHello world\n",
        encoding="utf-8",
    )
    # Patch config to old version so upgrade actually runs.
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["kit_version"] = "0.0.0"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    assert "MY CUSTOM SECTION" in (target / "AGENTS.md").read_text(encoding="utf-8")


def test_upgrade_creates_agents_md_if_missing(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Delete AGENTS.md and patch config to old version.
    (target / "AGENTS.md").unlink()
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["kit_version"] = "0.0.0"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / "AGENTS.md").is_file()


# --- aspect commands ---


def test_aspect_list() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["aspect", "list"])
    assert result.exit_code == 0, result.output
    assert "sdd" in result.output
    assert "stable" in result.output
    assert "0-3" in result.output


def test_aspect_info() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["aspect", "info", "sdd"])
    assert result.exit_code == 0, result.output
    assert "Aspect: sdd" in result.output
    assert "Stability:" in result.output
    assert "Depth range:" in result.output
    assert "Default depth:" in result.output


def test_aspect_info_unknown_aspect() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["aspect", "info", "nonexistent"])
    assert result.exit_code != 0
    assert "unknown aspect" in result.output.lower()


def test_aspect_set_depth(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    result = runner.invoke(main, ["aspect", "set-depth", str(target), "sdd", "3"])
    assert result.exit_code == 0, result.output

    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["sdd"]["depth"] == 3

    # Tier-3 files should exist.
    assert (target / "docs" / "design").is_dir()


def test_aspect_set_depth_down(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "3"])

    result = runner.invoke(main, ["aspect", "set-depth", str(target), "sdd", "1"])
    assert result.exit_code == 0, result.output
    assert "non-destructive" in result.output.lower()

    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["sdd"]["depth"] == 1

    # Tier-3-only files still exist (non-destructive demotion).
    assert (target / "docs" / "design").is_dir()


def test_aspect_set_depth_invalid(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    result = runner.invoke(main, ["aspect", "set-depth", str(target), "sdd", "99"])
    assert result.exit_code != 0
    assert "outside range" in result.output.lower()


# --- upgrade: flat protocol migration ---


def test_upgrade_migrates_flat_protocols(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "2"])

    # Create a flat protocol file (v1 layout: .kanon/protocols/*.md).
    protocols_dir = target / ".kanon" / "protocols"
    flat_file = protocols_dir / "some-protocol.md"
    flat_file.write_text("# Custom protocol\n\nDo the thing.\n", encoding="utf-8")

    # Patch config to old version so upgrade actually runs.
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["kit_version"] = "0.0.0"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    # Flat file should be moved into sdd/ subdirectory.
    assert not flat_file.exists(), "flat protocol file should have been moved"
    migrated = protocols_dir / "sdd" / "some-protocol.md"
    assert migrated.is_file(), "protocol should be at .kanon/protocols/sdd/some-protocol.md"
    assert "Custom protocol" in migrated.read_text(encoding="utf-8")
    assert "namespaced" in result.output.lower()


# ---------------------------------------------------------------------------
# Coverage-gap tests: _manifest.py, _scaffold.py, cli.py uncovered branches
# ---------------------------------------------------------------------------


# --- _manifest.py: _load_top_manifest validation errors ---


def test_load_top_manifest_not_a_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Line 42: top manifest YAML is not a dict."""
    from kanon._manifest import _load_top_manifest

    _load_top_manifest.cache_clear()
    monkeypatch.setattr(
        "kanon._manifest._kit_root",
        lambda: _make_fake_kit(tmp=None, content="- just a list"),
    )
    with pytest.raises(click.ClickException, match="expected a YAML mapping"):
        _load_top_manifest()
    _load_top_manifest.cache_clear()


def test_load_top_manifest_missing_aspects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Line 45: aspects key missing or empty."""
    from kanon._manifest import _load_top_manifest

    _load_top_manifest.cache_clear()
    monkeypatch.setattr(
        "kanon._manifest._kit_root",
        lambda: _make_fake_kit(tmp=None, content="foo: bar"),
    )
    with pytest.raises(click.ClickException, match="missing or empty"):
        _load_top_manifest()
    _load_top_manifest.cache_clear()


def test_load_top_manifest_aspect_not_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Line 48: an aspect entry is not a dict."""
    from kanon._manifest import _load_top_manifest

    _load_top_manifest.cache_clear()
    monkeypatch.setattr(
        "kanon._manifest._kit_root",
        lambda: _make_fake_kit(tmp=None, content="aspects:\n  sdd: not-a-dict"),
    )
    with pytest.raises(click.ClickException, match="must be a mapping"):
        _load_top_manifest()
    _load_top_manifest.cache_clear()


def test_load_top_manifest_missing_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """Line 51: required field missing from aspect entry."""
    import click as _click

    from kanon._manifest import _load_top_manifest

    _load_top_manifest.cache_clear()
    content = yaml.safe_dump({"aspects": {"sdd": {"path": "x"}}})
    monkeypatch.setattr(
        "kanon._manifest._kit_root",
        lambda: _make_fake_kit(tmp=None, content=content),
    )
    with pytest.raises(_click.ClickException, match="missing required field"):
        _load_top_manifest()
    _load_top_manifest.cache_clear()


def test_load_top_manifest_invalid_stability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Line 55: invalid stability value."""
    import click as _click

    from kanon._manifest import _load_top_manifest

    _load_top_manifest.cache_clear()
    content = yaml.safe_dump(
        {
            "aspects": {
                "sdd": {
                    "path": "aspects/sdd",
                    "stability": "bogus",
                    "depth-range": [0, 3],
                    "default-depth": 1,
                }
            }
        }
    )
    monkeypatch.setattr(
        "kanon._manifest._kit_root",
        lambda: _make_fake_kit(tmp=None, content=content),
    )
    with pytest.raises(_click.ClickException, match="invalid stability"):
        _load_top_manifest()
    _load_top_manifest.cache_clear()


def test_load_top_manifest_bad_depth_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Line 60: depth-range is not a 2-element list."""
    import click as _click

    from kanon._manifest import _load_top_manifest

    _load_top_manifest.cache_clear()
    content = yaml.safe_dump(
        {
            "aspects": {
                "sdd": {
                    "path": "aspects/sdd",
                    "stability": "stable",
                    "depth-range": [0],
                    "default-depth": 1,
                }
            }
        }
    )
    monkeypatch.setattr(
        "kanon._manifest._kit_root",
        lambda: _make_fake_kit(tmp=None, content=content),
    )
    with pytest.raises(_click.ClickException, match="depth-range must be"):
        _load_top_manifest()
    _load_top_manifest.cache_clear()


def test_load_top_manifest_missing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Line 39: manifest.yaml file doesn't exist."""
    import tempfile

    import click as _click

    from kanon._manifest import _load_top_manifest

    _load_top_manifest.cache_clear()
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setattr("kanon._manifest._kit_root", lambda: Path(d))
        with pytest.raises(_click.ClickException, match="kit manifest missing"):
            _load_top_manifest()
    _load_top_manifest.cache_clear()


# Helper for fake kit roots used by monkeypatched manifest tests.
def _make_fake_kit(tmp: Path | None, content: str) -> Path:
    import tempfile

    d = Path(tempfile.mkdtemp())
    (d / "manifest.yaml").write_text(content, encoding="utf-8")
    return d


# --- _manifest.py: _parse_frontmatter edge cases ---


def test_parse_frontmatter_no_end_marker() -> None:
    """Line 170: frontmatter start but no closing ---."""
    from kanon._manifest import _parse_frontmatter

    assert _parse_frontmatter("---\ntitle: hello\nno closing") == {}


def test_parse_frontmatter_non_dict_yaml() -> None:
    """Line 173: frontmatter YAML parses to non-dict."""
    from kanon._manifest import _parse_frontmatter

    assert _parse_frontmatter("---\n- a list item\n---\nbody") == {}


# --- _manifest.py: _namespaced_section unprefixed path ---


def test_namespaced_section_unprefixed() -> None:
    """Line 147→149: section in _UNPREFIXED_SECTIONS stays unprefixed."""
    from kanon._manifest import _namespaced_section

    assert _namespaced_section("sdd", "protocols-index") == "protocols-index"


# --- _scaffold.py: _read_config / _migrate_legacy_config ---


def test_read_config_malformed(tmp_path: Path) -> None:
    """Line 45: config.yaml is not a dict."""
    from kanon._scaffold import _read_config

    config_dir = tmp_path / ".kanon"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text('"just a string"', encoding="utf-8")
    with pytest.raises(click.ClickException, match="Malformed"):
        _read_config(tmp_path)


def test_migrate_legacy_config_no_tier_no_aspects() -> None:
    """Line 54: config has neither 'aspects' nor 'tier'."""
    from kanon._scaffold import _migrate_legacy_config

    result = _migrate_legacy_config({"kit_version": "1.0"})
    assert result == {"kit_version": "1.0"}


# --- _scaffold.py: _load_harnesses / _render_shims ---


def test_load_harnesses_missing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Line 101: harnesses.yaml doesn't exist."""
    import tempfile

    from kanon._scaffold import _load_harnesses

    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setattr("kanon._scaffold._kit_root", lambda: Path(d))
        assert _load_harnesses() == []


def test_load_harnesses_malformed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Line 104: harnesses.yaml is not a list."""
    import tempfile

    from kanon._scaffold import _load_harnesses

    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "harnesses.yaml").write_text("not_a_list: true", encoding="utf-8")
        monkeypatch.setattr("kanon._scaffold._kit_root", lambda: p)
        with pytest.raises(click.ClickException, match="expected a YAML list"):
            _load_harnesses()


def test_render_shims_frontmatter_and_plain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lines 142, 147: _render_shims with and without frontmatter."""
    import tempfile

    from kanon._scaffold import _render_shims

    harnesses = [
        {"path": "with_fm.md", "body": "hello\n", "frontmatter": {"key": "val"}},
        {"path": "plain.md", "body": "plain body\n"},
    ]
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "harnesses.yaml").write_text(
            yaml.safe_dump(harnesses), encoding="utf-8"
        )
        monkeypatch.setattr("kanon._scaffold._kit_root", lambda: p)
        result = _render_shims()
    assert "---" in result["with_fm.md"]
    assert "key: val" in result["with_fm.md"]
    assert result["plain.md"] == "plain body\n"


# --- _scaffold.py: _replace_section / _remove_section / _insert_section ---


def test_replace_section_no_markers() -> None:
    """Line 271→274: markers not found, text returned unchanged."""
    from kanon._scaffold import _replace_section

    text = "no markers here"
    assert _replace_section(text, "missing", "content") == text


def test_remove_section_no_markers() -> None:
    """_remove_section with no markers returns text unchanged."""
    from kanon._scaffold import _remove_section

    text = "no markers here"
    assert _remove_section(text, "missing") == text


def test_insert_section_no_anchor_no_trailing_newline() -> None:
    """Lines 289-291: no anchor found, text doesn't end with newline."""
    from kanon._scaffold import _insert_section

    result = _insert_section("some text", "test-section", "new content")
    assert "<!-- kanon:begin:test-section -->" in result
    assert "<!-- kanon:end:test-section -->" in result
    assert "new content" in result


# --- _scaffold.py: _render_protocols_index edge cases ---


def test_render_protocols_index_no_protocols() -> None:
    """Line 217: no protocols at depth 0 → 'No protocols active' message."""
    from kanon._scaffold import _render_protocols_index

    result = _render_protocols_index({"sdd": 0})
    assert "No protocols active" in result


# --- _scaffold.py: _render_kit_md returns None ---


def test_render_kit_md_no_kit_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Line 232: kit.md doesn't exist → returns None."""
    import tempfile

    from kanon._scaffold import _render_kit_md

    # Use a fake kit root with no kit.md
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        monkeypatch.setattr("kanon._manifest._kit_root", lambda: p)
        monkeypatch.setattr("kanon._scaffold._kit_root", lambda: p)
        result = _render_kit_md({"sdd": 0}, "test")
    assert result is None


# --- _scaffold.py: _migrate_flat_protocols edge cases ---


def test_migrate_flat_protocols_no_flat_files(tmp_path: Path) -> None:
    """Line 375: protocols dir exists but no flat .md files."""
    from kanon._scaffold import _migrate_flat_protocols

    protocols_dir = tmp_path / ".kanon" / "protocols"
    protocols_dir.mkdir(parents=True)
    assert _migrate_flat_protocols(tmp_path, {"sdd": 1}) is False


def test_migrate_flat_protocols_no_sdd_aspect(tmp_path: Path) -> None:
    """Line 380: flat files exist but 'sdd' not in aspects."""
    from kanon._scaffold import _migrate_flat_protocols

    protocols_dir = tmp_path / ".kanon" / "protocols"
    protocols_dir.mkdir(parents=True)
    (protocols_dir / "test.md").write_text("test", encoding="utf-8")
    assert _migrate_flat_protocols(tmp_path, {"other": 1}) is False


def test_migrate_flat_protocols_dest_exists(tmp_path: Path) -> None:
    """Line 386: destination already exists → unlink source instead of rename."""
    from kanon._scaffold import _migrate_flat_protocols

    protocols_dir = tmp_path / ".kanon" / "protocols"
    sdd_dir = protocols_dir / "sdd"
    sdd_dir.mkdir(parents=True)
    (protocols_dir / "dup.md").write_text("flat version", encoding="utf-8")
    (sdd_dir / "dup.md").write_text("already there", encoding="utf-8")
    assert _migrate_flat_protocols(tmp_path, {"sdd": 1}) is True
    assert not (protocols_dir / "dup.md").exists()
    assert (sdd_dir / "dup.md").read_text() == "already there"


# --- cli.py: verify with empty aspects ---


def test_verify_empty_aspects(tmp_path: Path) -> None:
    """Lines 180-182: config.aspects is empty."""
    runner = CliRunner()
    config_dir = tmp_path / ".kanon"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump({"kit_version": "0.1", "aspects": {}}), encoding="utf-8"
    )
    result = runner.invoke(main, ["verify", str(tmp_path)])
    assert result.exit_code != 0
    report = _extract_verify_json(result.output)
    assert "empty" in report["errors"][0].lower()


def test_verify_unknown_aspect(tmp_path: Path) -> None:
    """Lines 187-190: aspect in config not in kit registry."""
    runner = CliRunner()
    config_dir = tmp_path / ".kanon"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "kit_version": "0.1",
                "aspects": {"bogus": {"depth": 1, "enabled_at": "now", "config": {}}},
            }
        ),
        encoding="utf-8",
    )
    result = runner.invoke(main, ["verify", str(tmp_path)])
    assert result.exit_code != 0
    assert "unknown aspect" in result.output.lower() or "bogus" in result.output.lower()


def test_verify_depth_out_of_range(tmp_path: Path) -> None:
    """Line 193: aspect depth outside valid range."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Manually set depth to 99
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["aspects"]["sdd"]["depth"] = 99
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code != 0
    report = _extract_verify_json(result.output)
    assert any("outside range" in e for e in report["errors"])


def test_verify_marker_imbalance(tmp_path: Path) -> None:
    """Lines 207, 220: AGENTS.md has mismatched begin/end markers."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    agents = target / "AGENTS.md"
    text = agents.read_text(encoding="utf-8")
    # Remove one end marker to create imbalance
    text = text.replace("<!-- kanon:end:sdd/plan-before-build -->", "", 1)
    agents.write_text(text, encoding="utf-8")
    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code != 0
    output = result.output.lower()
    assert "imbalance" in output or "marker" in output


# --- cli.py: aspect set-depth unknown aspect ---


def test_aspect_set_depth_unknown_aspect(tmp_path: Path) -> None:
    """Line 322: unknown aspect name in set-depth."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(
        main, ["aspect", "set-depth", str(target), "nonexistent", "1"]
    )
    assert result.exit_code != 0
    assert "unknown aspect" in result.output.lower()


# --- cli.py: init with --force overwrites ---


def test_init_force_overwrites(tmp_path: Path) -> None:
    """Line 98→100: init with --force on existing project."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["init", str(target), "--tier", "2", "--force"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["sdd"]["depth"] == 2


# --- cli.py: init with default tier (no --tier flag) ---


def test_init_default_tier(tmp_path: Path) -> None:
    """Line 98→100: init without --tier uses default-depth from manifest."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target)])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    # default-depth for sdd is 1
    assert config["aspects"]["sdd"]["depth"] == 1


# --- cli.py: tier set with legacy verb messaging ---


def test_tier_set_down_legacy_verb(tmp_path: Path) -> None:
    """Line 399 + tier-down branch: tier set uses 'Tier' verb."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "3"])
    result = runner.invoke(main, ["tier", "set", str(target), "1"])
    assert result.exit_code == 0, result.output
    assert "tier" in result.output.lower()
    assert "non-destructive" in result.output.lower()


# --- _scaffold.py: _write_tree_atomically skip existing ---


def test_write_tree_atomically_skips_existing(tmp_path: Path) -> None:
    """Line 363: existing file not overwritten when force=False."""
    from kanon._scaffold import _write_tree_atomically

    (tmp_path / "existing.txt").write_text("original", encoding="utf-8")
    _write_tree_atomically(tmp_path, {"existing.txt": "new content"}, force=False)
    assert (tmp_path / "existing.txt").read_text() == "original"


# --- _scaffold.py: _rewrite_legacy_markers ---


def test_rewrite_legacy_markers() -> None:
    """Covers the legacy marker rewriting path in _rewrite_legacy_markers."""
    from kanon._scaffold import _rewrite_legacy_markers

    text = (
        "<!-- kanon:begin:plan-before-build -->\nold\n"
        "<!-- kanon:end:plan-before-build -->\n"
    )
    result = _rewrite_legacy_markers(text)
    assert "<!-- kanon:begin:sdd/plan-before-build -->" in result
    assert "<!-- kanon:end:sdd/plan-before-build -->" in result


# --- cli.py: upgrade where AGENTS.md content actually changes ---


def test_upgrade_modifies_agents_md(tmp_path: Path) -> None:
    """Line 145: upgrade path where merged AGENTS.md differs from existing."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Corrupt a marker section so merge produces a diff
    agents = target / "AGENTS.md"
    text = agents.read_text(encoding="utf-8")
    text = text.replace(
        "<!-- kanon:begin:sdd/plan-before-build -->",
        "<!-- kanon:begin:sdd/plan-before-build -->\nCORRUPTED CONTENT",
    )
    agents.write_text(text, encoding="utf-8")
    # Patch config to old version so upgrade runs
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["kit_version"] = "0.0.0"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    # The corrupted content should be replaced by the merge
    final = agents.read_text(encoding="utf-8")
    assert "CORRUPTED CONTENT" not in final


# --- worktrees aspect CLI tests ---


def test_init_with_worktrees_depth_1(tmp_path: Path) -> None:
    """Depth 1: protocol + AGENTS.md protocols-index mentions worktrees, no scripts."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "worktrees", "1"])
    assert result.exit_code == 0, result.output

    assert (target / ".kanon" / "protocols" / "worktrees" / "worktree-lifecycle.md").is_file()
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "worktree-lifecycle" in agents
    assert "worktrees (depth 1)" in agents
    assert "<!-- kanon:begin:worktrees/branch-hygiene -->" in agents
    assert "<!-- kanon:end:worktrees/branch-hygiene -->" in agents
    assert not (target / "scripts").exists()


def test_init_with_worktrees_depth_2(tmp_path: Path) -> None:
    """Depth 2: protocol + AGENTS.md mentions worktrees + shell scripts."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "worktrees", "2"])
    assert result.exit_code == 0, result.output

    assert (target / ".kanon" / "protocols" / "worktrees" / "worktree-lifecycle.md").is_file()
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "worktree-lifecycle" in agents
    assert "<!-- kanon:begin:worktrees/branch-hygiene -->" in agents
    assert "<!-- kanon:end:worktrees/branch-hygiene -->" in agents
    for script in ("worktree-setup.sh", "worktree-teardown.sh", "worktree-status.sh"):
        assert (target / "scripts" / script).is_file(), f"missing scripts/{script}"


def test_worktrees_depth_0_scaffolds_nothing(tmp_path: Path) -> None:
    """Depth 0: no protocol, no scripts, no markers in AGENTS.md."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "worktrees", "0"])
    assert result.exit_code == 0, result.output

    assert not (target / ".kanon" / "protocols" / "worktrees").exists()
    assert not (target / "scripts").exists()
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:worktrees/branch-hygiene -->" not in agents
