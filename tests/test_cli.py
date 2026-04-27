"""Tests for the kanon CLI: init, upgrade, verify, tier set.

Includes tier-migration round-trip smoke: 0 → 1 → 2 → 3 → 2 → 1 → 0
preserves user-authored files and verify stays OK at every step.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

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
    assert config["aspects"]["kanon-sdd"]["depth"] == tier
    assert config["kit_version"] == __version__
    assert "enabled_at" in config["aspects"]["kanon-sdd"]


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
    assert report["aspects"]["kanon-sdd"] == tier


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
    1: {"tier-up-advisor.md", "verify-triage.md", "completion-checklist.md", "scope-check.md"},
    2: {"tier-up-advisor.md", "verify-triage.md", "completion-checklist.md", "scope-check.md", "spec-review.md"},
    3: {"tier-up-advisor.md", "verify-triage.md", "completion-checklist.md", "scope-check.md", "spec-review.md"},
}


@pytest.mark.parametrize("tier", [0, 1, 2, 3])
def test_protocols_scaffolded_at_correct_tier(tmp_path: Path, tier: int) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", str(tier)])
    protocols_dir = target / ".kanon" / "protocols" / "kanon-sdd"
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
    assert "${sdd_depth}" not in text
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
    text = text.replace("<!-- kanon:begin:kanon-sdd/plan-before-build -->", "")
    text = text.replace("<!-- kanon:end:kanon-sdd/plan-before-build -->", "")
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


def test_upgrade_noop_does_not_churn_enabled_at(tmp_path: Path) -> None:
    """A no-op `upgrade` (version unchanged, no edits) must not rewrite the
    config — `enabled_at` must be byte-identical after the call."""
    import time

    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    config_path = target / ".kanon" / "config.yaml"
    captured = yaml.safe_load(config_path.read_text(encoding="utf-8"))[
        "aspects"
    ]["kanon-sdd"]["enabled_at"]

    # Sleep > 1 second so a churn-write would yield a different ISO-second.
    time.sleep(1.1)

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    after = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert after["aspects"]["kanon-sdd"]["enabled_at"] == captured, (
        "upgrade must not rewrite enabled_at on a no-op"
    )


def test_upgrade_heals_edited_markers(tmp_path: Path) -> None:
    """`upgrade` re-renders kit-managed marker sections even when kit_version
    is unchanged. User content outside markers is preserved."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "2"])

    agents_path = target / "AGENTS.md"
    original = agents_path.read_text(encoding="utf-8")

    # Corrupt the body of a kit-managed marker section.
    begin = "<!-- kanon:begin:kanon-sdd/plan-before-build -->"
    end = "<!-- kanon:end:kanon-sdd/plan-before-build -->"
    bi = original.find(begin)
    ei = original.find(end, bi + len(begin))
    assert bi >= 0 and ei > bi
    corrupted = original[: bi + len(begin)] + "\nGARBAGE BODY\n" + original[ei:]
    # Add user content outside markers — must survive.
    corrupted += "\n## My Custom Section\n\nUser-authored. Do not touch.\n"
    agents_path.write_text(corrupted, encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    final = agents_path.read_text(encoding="utf-8")
    assert "GARBAGE BODY" not in final, "upgrade did not re-render marker body"
    assert "My Custom Section" in final, "upgrade clobbered user content"
    assert "User-authored. Do not touch." in final
    # The kit's canonical body is restored — sanity-check it begins with the
    # section's header, which the kit ships in `sections/plan-before-build.md`.
    assert "Required: Plan Before Build" in final


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
    assert "kanon-sdd" in result.output
    assert "stable" in result.output
    assert "0-3" in result.output


def test_aspect_info() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["aspect", "info", "kanon-sdd"])
    assert result.exit_code == 0, result.output
    assert "Aspect: kanon-sdd" in result.output
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

    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-sdd", "3"])
    assert result.exit_code == 0, result.output

    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["kanon-sdd"]["depth"] == 3

    # Tier-3 files should exist.
    assert (target / "docs" / "design").is_dir()


def test_aspect_set_depth_down(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "3"])

    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-sdd", "1"])
    assert result.exit_code == 0, result.output
    assert "non-destructive" in result.output.lower()

    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["kanon-sdd"]["depth"] == 1

    # Tier-3-only files still exist (non-destructive demotion).
    assert (target / "docs" / "design").is_dir()


def test_aspect_set_depth_invalid(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-sdd", "99"])
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
    migrated = protocols_dir / "kanon-sdd" / "some-protocol.md"
    assert migrated.is_file(), "protocol should be at .kanon/protocols/kanon-sdd/some-protocol.md"
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
        lambda: _make_fake_kit(tmp=None, content="aspects:\n  kanon-sdd: not-a-dict"),
    )
    with pytest.raises(click.ClickException, match="must be a mapping"):
        _load_top_manifest()
    _load_top_manifest.cache_clear()


def test_load_top_manifest_missing_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """Line 51: required field missing from aspect entry."""
    import click as _click

    from kanon._manifest import _load_top_manifest

    _load_top_manifest.cache_clear()
    content = yaml.safe_dump({"aspects": {"kanon-sdd": {"path": "x"}}})
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
                "kanon-sdd": {
                    "path": "aspects/kanon-sdd",
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
                "kanon-sdd": {
                    "path": "aspects/kanon-sdd",
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

    assert _namespaced_section("kanon-sdd", "protocols-index") == "protocols-index"


# --- _scaffold.py: _read_config / _migrate_legacy_config ---


def test_read_config_malformed(tmp_path: Path) -> None:
    """Line 45: config.yaml is not a dict."""
    from kanon._scaffold import _read_config

    config_dir = tmp_path / ".kanon"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text('"just a string"', encoding="utf-8")
    with pytest.raises(click.ClickException, match="Malformed"):
        _read_config(tmp_path)


def test_load_yaml_invalid_syntax(tmp_path: Path) -> None:
    """_load_yaml wraps yaml.YAMLError into ClickException."""
    from kanon._manifest import _load_yaml

    bad = tmp_path / "bad.yaml"
    bad.write_text(":\n  - :\n  bad: [unterminated", encoding="utf-8")
    with pytest.raises(click.ClickException, match="Invalid YAML"):
        _load_yaml(bad)


def test_load_yaml_wrong_type(tmp_path: Path) -> None:
    """_load_yaml raises ClickException when top-level type doesn't match."""
    from kanon._manifest import _load_yaml

    f = tmp_path / "list.yaml"
    f.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(click.ClickException, match="expected a YAML mapping"):
        _load_yaml(f, expected_type=dict)


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

    result = _render_protocols_index({"kanon-sdd": 0})
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
        result = _render_kit_md({"kanon-sdd": 0}, "test")
    assert result is None


# --- _scaffold.py: _migrate_flat_protocols edge cases ---


def test_migrate_flat_protocols_no_flat_files(tmp_path: Path) -> None:
    """Line 375: protocols dir exists but no flat .md files."""
    from kanon._scaffold import _migrate_flat_protocols

    protocols_dir = tmp_path / ".kanon" / "protocols"
    protocols_dir.mkdir(parents=True)
    assert _migrate_flat_protocols(tmp_path, {"kanon-sdd": 1}) is False


def test_migrate_flat_protocols_no_sdd_aspect(tmp_path: Path) -> None:
    """Line 380: flat files exist but 'kanon-sdd' not in aspects."""
    from kanon._scaffold import _migrate_flat_protocols

    protocols_dir = tmp_path / ".kanon" / "protocols"
    protocols_dir.mkdir(parents=True)
    (protocols_dir / "test.md").write_text("test", encoding="utf-8")
    assert _migrate_flat_protocols(tmp_path, {"other": 1}) is False


def test_migrate_flat_protocols_dest_exists(tmp_path: Path) -> None:
    """Line 386: destination already exists → unlink source instead of rename."""
    from kanon._scaffold import _migrate_flat_protocols

    protocols_dir = tmp_path / ".kanon" / "protocols"
    sdd_dir = protocols_dir / "kanon-sdd"
    sdd_dir.mkdir(parents=True)
    (protocols_dir / "dup.md").write_text("flat version", encoding="utf-8")
    (sdd_dir / "dup.md").write_text("already there", encoding="utf-8")
    assert _migrate_flat_protocols(tmp_path, {"kanon-sdd": 1}) is True
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
    """Spec invariant 4: an aspect in config not in the installed kit registry
    emits a warning, exit 0 — not a hard failure (`docs/specs/aspects.md`).

    Models the upstream-deprecation scenario: a consumer had aspect X enabled,
    upgraded the kit, and X no longer ships. The opt-in record survives so they
    can clean up — verify must not brick them.
    """
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Inject a fake aspect into a real, otherwise-valid project.
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["aspects"]["bogus"] = {"depth": 1, "enabled_at": "now", "config": {}}
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code == 0, result.output
    report = _extract_verify_json(result.output)
    assert report["status"] == "ok"
    assert report["errors"] == []
    assert any("bogus" in w for w in report["warnings"])
    assert "warning" in result.output.lower()


def test_verify_depth_out_of_range(tmp_path: Path) -> None:
    """Line 193: aspect depth outside valid range."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Manually set depth to 99
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["aspects"]["kanon-sdd"]["depth"] = 99
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
    text = text.replace("<!-- kanon:end:kanon-sdd/plan-before-build -->", "", 1)
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
    assert config["aspects"]["kanon-sdd"]["depth"] == 2


# --- cli.py: init with default tier (no --tier flag) ---


def test_init_default_tier(tmp_path: Path) -> None:
    """Line 98→100: init without --tier uses default-depth from manifest."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target)])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    # default-depth for sdd is 1
    assert config["aspects"]["kanon-sdd"]["depth"] == 1


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
    assert "<!-- kanon:begin:kanon-sdd/plan-before-build -->" in result
    assert "<!-- kanon:end:kanon-sdd/plan-before-build -->" in result


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
        "<!-- kanon:begin:kanon-sdd/plan-before-build -->",
        "<!-- kanon:begin:kanon-sdd/plan-before-build -->\nCORRUPTED CONTENT",
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
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-worktrees", "1"])
    assert result.exit_code == 0, result.output

    assert (target / ".kanon" / "protocols" / "kanon-worktrees" / "worktree-lifecycle.md").is_file()
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "worktree-lifecycle" in agents
    assert "worktrees (depth 1)" in agents
    assert "<!-- kanon:begin:kanon-worktrees/branch-hygiene -->" in agents
    assert "<!-- kanon:end:kanon-worktrees/branch-hygiene -->" in agents
    assert not (target / "scripts").exists()


def test_init_with_worktrees_depth_2(tmp_path: Path) -> None:
    """Depth 2: protocol + AGENTS.md mentions worktrees + shell scripts."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-worktrees", "2"])
    assert result.exit_code == 0, result.output

    assert (target / ".kanon" / "protocols" / "kanon-worktrees" / "worktree-lifecycle.md").is_file()
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "worktree-lifecycle" in agents
    assert "<!-- kanon:begin:kanon-worktrees/branch-hygiene -->" in agents
    assert "<!-- kanon:end:kanon-worktrees/branch-hygiene -->" in agents
    for script in ("worktree-setup.sh", "worktree-teardown.sh", "worktree-status.sh"):
        assert (target / "scripts" / script).is_file(), f"missing scripts/{script}"


def test_worktrees_depth_0_scaffolds_nothing(tmp_path: Path) -> None:
    """Depth 0: no protocol, no scripts, no markers in AGENTS.md."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-worktrees", "0"])
    assert result.exit_code == 0, result.output

    assert not (target / ".kanon" / "protocols" / "kanon-worktrees").exists()
    assert not (target / "scripts").exists()
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:kanon-worktrees/branch-hygiene -->" not in agents


# --- aspect add / remove commands ---


def test_aspect_add(tmp_path: Path) -> None:
    """aspect add enables an aspect at its default depth."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-worktrees"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "kanon-worktrees" in config["aspects"]
    assert (target / ".kanon" / "protocols" / "kanon-worktrees" / "worktree-lifecycle.md").is_file()


def test_aspect_add_already_enabled(tmp_path: Path) -> None:
    """aspect add on an already-enabled aspect fails."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    runner.invoke(main, ["aspect", "add", str(target), "kanon-worktrees"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-worktrees"])
    assert result.exit_code != 0
    assert "already enabled" in result.output.lower()


def test_aspect_add_with_depth(tmp_path: Path) -> None:
    """aspect add --depth N enables at the specified depth."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-worktrees", "--depth", "2"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["kanon-worktrees"]["depth"] == 2


def test_aspect_add_depth_out_of_range(tmp_path: Path) -> None:
    """aspect add --depth with invalid depth fails."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-worktrees", "--depth", "9"])
    assert result.exit_code != 0
    assert "outside range" in result.output.lower()


def test_aspect_add_unknown(tmp_path: Path) -> None:
    """aspect add with an unknown aspect name fails."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "add", str(target), "nonexistent"])
    assert result.exit_code != 0
    assert "unknown aspect" in result.output.lower()


def test_aspect_remove(tmp_path: Path) -> None:
    """aspect remove deletes the aspect from config and AGENTS.md markers."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    runner.invoke(main, ["aspect", "add", str(target), "kanon-worktrees"])
    result = runner.invoke(main, ["aspect", "remove", str(target), "kanon-worktrees"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "kanon-worktrees" not in config["aspects"]
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:kanon-worktrees/branch-hygiene -->" not in agents


def test_aspect_remove_not_enabled(tmp_path: Path) -> None:
    """aspect remove on a non-enabled aspect fails."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "remove", str(target), "kanon-worktrees"])
    assert result.exit_code != 0
    assert "not enabled" in result.output.lower()


def test_aspect_remove_leaves_files(tmp_path: Path) -> None:
    """aspect remove is non-destructive: scaffolded files stay on disk."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-worktrees", "2"])
    # Scripts exist before removal
    assert (target / "scripts" / "worktree-setup.sh").is_file()
    result = runner.invoke(main, ["aspect", "remove", str(target), "kanon-worktrees"])
    assert result.exit_code == 0, result.output
    # Scripts still on disk (non-destructive)
    assert (target / "scripts" / "worktree-setup.sh").is_file()
    assert "non-destructive" in result.output.lower() or "left on disk" in result.output.lower()


def test_aspect_remove_clears_sentinel_on_success(tmp_path: Path) -> None:
    """`aspect remove` writes `.kanon/.pending` during the mutation and
    clears it on success — symmetric with the other mutating commands.
    """
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    runner.invoke(main, ["aspect", "add", str(target), "kanon-worktrees"])

    pending = target / ".kanon" / ".pending"
    assert not pending.exists(), "sentinel should be absent before remove"

    result = runner.invoke(main, ["aspect", "remove", str(target), "kanon-worktrees"])
    assert result.exit_code == 0, result.output
    assert not pending.exists(), "sentinel must be cleared after successful remove"


def test_aspect_remove_persists_sentinel_on_mid_write_failure(tmp_path: Path) -> None:
    """If `_write_config` raises mid-`aspect remove`, the sentinel must
    persist so the next CLI invocation warns the user (ADR-0024 contract).
    """
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    runner.invoke(main, ["aspect", "add", str(target), "kanon-worktrees"])

    pending = target / ".kanon" / ".pending"

    # Patch _write_config to raise after the sentinel write but before clear.
    with patch("kanon.cli._write_config", side_effect=OSError("simulated disk full")):
        runner.invoke(main, ["aspect", "remove", str(target), "kanon-worktrees"])
    assert pending.is_file(), "sentinel must persist after mid-write failure"
    assert pending.read_text(encoding="utf-8").strip() == "aspect-remove"


def test_init_with_aspects_flag(tmp_path: Path) -> None:
    """init --aspects enables multiple aspects at specified depths."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--aspects", "sdd:2,worktrees:1"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["kanon-sdd"]["depth"] == 2
    assert config["aspects"]["kanon-worktrees"]["depth"] == 1


def test_init_aspects_and_tier_mutual_exclusion(tmp_path: Path) -> None:
    """init with both --tier and --aspects fails."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--tier", "1", "--aspects", "sdd:1"])
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output.lower()


def test_init_default_aspects(tmp_path: Path) -> None:
    """init with no --tier and no --aspects uses default aspects."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target)])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "kanon-sdd" in config["aspects"]
    assert config["aspects"]["kanon-sdd"]["depth"] == 1


# --- requires: enforcement tests ---


def test_aspect_add_requires_unmet(tmp_path: Path) -> None:
    """aspect add worktrees fails when sdd is at depth 0 (requires sdd >= 1)."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "0"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-worktrees"])
    assert result.exit_code != 0
    assert "sdd >= 1" in result.output


def test_aspect_remove_blocked_by_dependent(tmp_path: Path) -> None:
    """aspect remove sdd fails when worktrees depends on it."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1,worktrees:1"])
    result = runner.invoke(main, ["aspect", "remove", str(target), "kanon-sdd"])
    assert result.exit_code != 0
    assert "kanon-worktrees" in result.output
    assert "requires" in result.output.lower()


def test_aspect_set_depth_requires_check(tmp_path: Path) -> None:
    """set-depth worktrees 1 fails when sdd is at depth 0."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "0"])
    result = runner.invoke(
        main, ["aspect", "set-depth", str(target), "kanon-worktrees", "1"]
    )
    assert result.exit_code != 0
    assert "sdd >= 1" in result.output


def test_aspect_add_requires_met(tmp_path: Path) -> None:
    """aspect add worktrees succeeds when sdd >= 1."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-worktrees"])
    assert result.exit_code == 0, result.output


def test_aspect_remove_no_dependents(tmp_path: Path) -> None:
    """aspect remove worktrees succeeds (nothing depends on worktrees)."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1,worktrees:1"])
    result = runner.invoke(main, ["aspect", "remove", str(target), "kanon-worktrees"])
    assert result.exit_code == 0, result.output


# --- release aspect CLI tests ---


def test_aspect_add_release(tmp_path: Path) -> None:
    """aspect add release enables the aspect; protocol is scaffolded."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-release"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "kanon-release" in config["aspects"]
    assert (target / ".kanon" / "protocols" / "kanon-release" / "release-checklist.md").is_file()


def test_release_depth_2_has_ci_files(tmp_path: Path) -> None:
    """set-depth release 2 scaffolds CI files."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-release", "2"])
    assert result.exit_code == 0, result.output
    assert (target / "ci" / "release-preflight.py").is_file()
    assert (target / ".github" / "workflows" / "release.yml").is_file()


# --- fidelity lock tests ---


def test_fidelity_update_creates_lock(tmp_path: Path) -> None:
    """init tier 2, create a spec, run fidelity update, assert lock exists."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    spec = target / "docs" / "specs" / "example.md"
    spec.write_text("---\nstatus: accepted\ndate: 2026-01-01\n---\n# Spec: Example\n", encoding="utf-8")
    result = runner.invoke(main, ["fidelity", "update", str(target)])
    assert result.exit_code == 0, result.output
    lock = target / ".kanon" / "fidelity.lock"
    assert lock.is_file()
    data = yaml.safe_load(lock.read_text(encoding="utf-8"))
    assert data["lock_version"] == 1
    assert "example" in data["entries"]
    assert data["entries"]["example"]["spec_sha"].startswith("sha256:")


def test_fidelity_update_idempotent(tmp_path: Path) -> None:
    """Running fidelity update twice produces identical output (except locked_at)."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    spec = target / "docs" / "specs" / "example.md"
    spec.write_text("---\nstatus: accepted\ndate: 2026-01-01\n---\n# Spec: Example\n", encoding="utf-8")
    runner.invoke(main, ["fidelity", "update", str(target)])
    lock1 = yaml.safe_load((target / ".kanon" / "fidelity.lock").read_text(encoding="utf-8"))
    runner.invoke(main, ["fidelity", "update", str(target)])
    lock2 = yaml.safe_load((target / ".kanon" / "fidelity.lock").read_text(encoding="utf-8"))
    assert lock1["entries"]["example"]["spec_sha"] == lock2["entries"]["example"]["spec_sha"]


def test_verify_warns_on_stale_lock(tmp_path: Path) -> None:
    """Modify spec after fidelity update, verify should warn."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    spec = target / "docs" / "specs" / "example.md"
    spec.write_text("---\nstatus: accepted\ndate: 2026-01-01\n---\n# Spec: Example\n", encoding="utf-8")
    runner.invoke(main, ["fidelity", "update", str(target)])
    spec.write_text("---\nstatus: accepted\ndate: 2026-01-01\n---\n# Spec: Example\nChanged.\n", encoding="utf-8")
    result = runner.invoke(main, ["verify", str(target)])
    parsed = _extract_verify_json(result.output)
    assert any("fidelity" in w and "example" in w for w in parsed.get("warnings", []))


def test_verify_no_warning_without_lock(tmp_path: Path) -> None:
    """Without a lock file, verify should not emit fidelity warnings."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    result = runner.invoke(main, ["verify", str(target)])
    parsed = _extract_verify_json(result.output)
    assert not any("fidelity" in w for w in parsed.get("warnings", []))


def test_fidelity_lock_includes_fixture_shas(tmp_path: Path) -> None:
    """Spec with invariant_coverage produces fixture_shas in lock."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    # Create a test file
    test_file = target / "tests" / "test_example.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_one(): pass\n", encoding="utf-8")
    # Create a spec with invariant_coverage pointing to the test file
    spec = target / "docs" / "specs" / "example.md"
    spec.write_text(
        "---\nstatus: accepted\ndate: 2026-01-01\n"
        "invariant_coverage:\n"
        "  INV-example-one:\n"
        "    - tests/test_example.py::test_one\n"
        "---\n# Spec: Example\n",
        encoding="utf-8",
    )
    result = runner.invoke(main, ["fidelity", "update", str(target)])
    assert result.exit_code == 0, result.output
    lock = target / ".kanon" / "fidelity.lock"
    data = yaml.safe_load(lock.read_text(encoding="utf-8"))
    entry = data["entries"]["example"]
    assert "fixture_shas" in entry
    assert "tests/test_example.py" in entry["fixture_shas"]
    expected_sha = "sha256:" + hashlib.sha256(test_file.read_bytes()).hexdigest()
    assert entry["fixture_shas"]["tests/test_example.py"] == expected_sha


def test_verify_warns_on_stale_fixture(tmp_path: Path) -> None:
    """Modify a fixture file after fidelity update, verify should warn."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    test_file = target / "tests" / "test_example.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_one(): pass\n", encoding="utf-8")
    spec = target / "docs" / "specs" / "example.md"
    spec.write_text(
        "---\nstatus: accepted\ndate: 2026-01-01\n"
        "invariant_coverage:\n"
        "  INV-example-one:\n"
        "    - tests/test_example.py::test_one\n"
        "---\n# Spec: Example\n",
        encoding="utf-8",
    )
    runner.invoke(main, ["fidelity", "update", str(target)])
    # Modify the test file (not the spec)
    test_file.write_text("def test_one(): assert True\n", encoding="utf-8")
    result = runner.invoke(main, ["verify", str(target)])
    parsed = _extract_verify_json(result.output)
    assert any(
        "fixture" in w and "test_example.py" in w
        for w in parsed.get("warnings", [])
    )


# --- testing aspect CLI tests ---


def test_aspect_add_testing(tmp_path: Path) -> None:
    """aspect add testing enables the aspect; protocol is scaffolded."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-testing"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "kanon-testing" in config["aspects"]
    assert (target / ".kanon" / "protocols" / "kanon-testing" / "test-discipline.md").is_file()
    assert (target / ".kanon" / "protocols" / "kanon-testing" / "error-diagnosis.md").is_file()


def test_testing_depth_3_has_ci_script(tmp_path: Path) -> None:
    """set-depth testing 3 scaffolds ci/check_test_quality.py."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-testing", "3"])
    assert result.exit_code == 0, result.output
    assert (target / "ci" / "check_test_quality.py").is_file()



def test_aspect_add_security(tmp_path: Path) -> None:
    """aspect add security enables the aspect; protocol is scaffolded."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-security"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "kanon-security" in config["aspects"]
    assert (target / ".kanon" / "protocols" / "kanon-security" / "secure-defaults.md").is_file()


def test_security_depth_2_has_ci_script(tmp_path: Path) -> None:
    """set-depth security 2 scaffolds ci/check_security_patterns.py."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-security", "2"])
    assert result.exit_code == 0, result.output
    assert (target / "ci" / "check_security_patterns.py").is_file()


def test_aspect_add_deps(tmp_path: Path) -> None:
    """aspect add deps enables the aspect; protocol is scaffolded."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-deps"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "kanon-deps" in config["aspects"]
    assert (target / ".kanon" / "protocols" / "kanon-deps" / "dependency-hygiene.md").is_file()


def test_deps_depth_2_has_ci_script(tmp_path: Path) -> None:
    """set-depth deps 2 scaffolds ci/check_deps.py."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-deps", "2"])
    assert result.exit_code == 0, result.output
    assert (target / "ci" / "check_deps.py").is_file()


# --- Sentinel crash-recovery integration tests (ADR-0024) ---


def test_sentinel_absent_after_successful_init(tmp_path: Path) -> None:
    """After a successful init, .kanon/.pending must not exist."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    assert result.exit_code == 0, result.output
    assert not (target / ".kanon" / ".pending").exists()


def test_sentinel_absent_after_successful_upgrade(tmp_path: Path) -> None:
    """After a successful upgrade, .kanon/.pending must not exist."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    assert not (target / ".kanon" / ".pending").exists()


def test_sentinel_absent_after_successful_set_depth(tmp_path: Path) -> None:
    """After a successful set-depth, .kanon/.pending must not exist."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-sdd", "2"])
    assert result.exit_code == 0, result.output
    assert not (target / ".kanon" / ".pending").exists()


def test_pending_sentinel_triggers_warning_on_upgrade(tmp_path: Path) -> None:
    """If .kanon/.pending exists, upgrade warns about interrupted operation."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Simulate interrupted operation by writing sentinel manually.
    (target / ".kanon" / ".pending").write_text("set-depth\n", encoding="utf-8")
    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    assert "interrupted" in result.output.lower()
    # Sentinel should be cleared after successful upgrade.
    assert not (target / ".kanon" / ".pending").exists()


def test_pending_sentinel_triggers_warning_on_verify(tmp_path: Path) -> None:
    """If .kanon/.pending exists, verify warns about interrupted operation."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    (target / ".kanon" / ".pending").write_text("upgrade\n", encoding="utf-8")
    result = runner.invoke(main, ["verify", str(target)])
    # Verify outputs to stderr; CliRunner mixes stdout+stderr by default.
    assert "interrupted" in result.output.lower()


@pytest.mark.parametrize(
    "pending_op,expected_command",
    [
        ("init", "kanon init"),
        ("upgrade", "kanon upgrade"),
        ("set-depth", "kanon aspect set-depth"),
        ("set-config", "kanon aspect set-config"),
        ("aspect-remove", "kanon aspect remove"),
        ("fidelity-update", "kanon fidelity update"),
    ],
)
def test_pending_recovery_warning_uses_correct_user_command(
    tmp_path: Path, pending_op: str, expected_command: str
) -> None:
    """The recovery warning must suggest a valid `kanon` command for each
    known sentinel operation. Sub-group commands like `aspect remove`
    appear with a space, not as `kanon aspect-remove` (which isn't a
    valid CLI invocation)."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    (target / ".kanon" / ".pending").write_text(f"{pending_op}\n", encoding="utf-8")
    # Any mutating command path triggers _check_pending_recovery; verify
    # also prints it. Use verify because it's idempotent and won't clear
    # the sentinel (it has no write side effect).
    result = runner.invoke(main, ["verify", str(target)])
    assert f"Re-run '{expected_command}'" in result.output, (
        f"expected suggestion {expected_command!r} for pending {pending_op!r}; "
        f"got output: {result.output!r}"
    )


def test_pending_recovery_warning_falls_back_for_unknown_op(tmp_path: Path) -> None:
    """An unknown sentinel operation falls back to `kanon {pending}`
    rather than crashing — defensive against future operation strings
    not yet mapped in `_PENDING_OP_TO_COMMAND`."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    (target / ".kanon" / ".pending").write_text("future-op\n", encoding="utf-8")
    result = runner.invoke(main, ["verify", str(target)])
    assert "Re-run 'kanon future-op'" in result.output


# --- ADR-0028: bare-name sugar at every CLI input surface (T12) ---


def test_cli_aspect_set_depth_accepts_bare_and_namespaced(tmp_path: Path) -> None:
    """Bare `sdd` and namespaced `kanon-sdd` both work for `aspect set-depth`."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    # Bare name: should sugar to kanon-sdd.
    r1 = runner.invoke(main, ["aspect", "set-depth", str(target), "sdd", "2"])
    assert r1.exit_code == 0, r1.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["kanon-sdd"]["depth"] == 2

    # Namespaced name: should pass through unchanged.
    r2 = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-sdd", "3"])
    assert r2.exit_code == 0, r2.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["kanon-sdd"]["depth"] == 3


def test_cli_aspect_info_accepts_bare_name() -> None:
    """`kanon aspect info sdd` resolves to `kanon-sdd` via bare-name sugar."""
    runner = CliRunner()
    result = runner.invoke(main, ["aspect", "info", "sdd"])
    assert result.exit_code == 0, result.output
    assert "Aspect: kanon-sdd" in result.output


def test_cli_init_aspects_flag_accepts_bare_names(tmp_path: Path) -> None:
    """`--aspects sdd:1,worktrees:2` sugars each token to the `kanon-` namespace."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--aspects", "sdd:1,worktrees:2"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["kanon-sdd"]["depth"] == 1
    assert config["aspects"]["kanon-worktrees"]["depth"] == 2


def test_cli_init_aspects_flag_accepts_namespaced_names(tmp_path: Path) -> None:
    """`--aspects kanon-sdd:1,kanon-worktrees:2` is also accepted (canonical form)."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(
        main, ["init", str(target), "--aspects", "kanon-sdd:1,kanon-worktrees:2"]
    )
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["kanon-sdd"]["depth"] == 1
    assert config["aspects"]["kanon-worktrees"]["depth"] == 2


def test_cli_aspect_add_remove_accept_bare_name(tmp_path: Path) -> None:
    """`aspect add` and `aspect remove` accept bare names that sugar to `kanon-`."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    add = runner.invoke(main, ["aspect", "add", str(target), "worktrees"])
    assert add.exit_code == 0, add.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "kanon-worktrees" in config["aspects"]

    rem = runner.invoke(main, ["aspect", "remove", str(target), "worktrees"])
    assert rem.exit_code == 0, rem.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "kanon-worktrees" not in config["aspects"]


def test_cli_legacy_v2_config_auto_migrates_to_v3(tmp_path: Path) -> None:
    """A v2 (bare-aspect-key) consumer config auto-migrates to v3 (`kanon-` prefix)
    on first `kanon upgrade`.
    """
    target = tmp_path / "scratch"
    runner = CliRunner()
    # Hand-craft a v2 config: bare `sdd` key, no `kanon-` prefix.
    (target / ".kanon").mkdir(parents=True)
    (target / ".kanon" / "config.yaml").write_text(
        "kit_version: 0.2.0a5\n"
        "aspects:\n"
        "  sdd:\n"
        "    depth: 1\n"
        "    enabled_at: '2026-04-25T00:00:00+00:00'\n"
        "    config: {}\n",
        encoding="utf-8",
    )
    # Minimal AGENTS.md so upgrade has something to merge into; user content
    # outside markers must survive.
    (target / "AGENTS.md").write_text(
        "# Custom AGENTS.md\nUser-authored note.\n", encoding="utf-8"
    )
    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "kanon-sdd" in config["aspects"], (
        f"v2 → v3 migration did not bump bare key: {list(config['aspects'])}"
    )
    assert "sdd" not in config["aspects"]
    # User-authored content outside markers preserved.
    assert "User-authored note." in (target / "AGENTS.md").read_text()


# --- ADR-0028 / Phase 2: config migration round-trips (T17) ---


def test_migrate_legacy_config_v1_to_v3_produces_namespaced_key() -> None:
    """A v1 config (`tier: N`) migrates to v3 with the canonical `kanon-sdd` key."""
    from kanon._scaffold import _migrate_legacy_config

    v1 = {"kit_version": "0.1.0a1", "tier": 2, "tier_set_at": "2026-04-25T00:00:00+00:00"}
    v3 = _migrate_legacy_config(v1)
    assert "tier" not in v3
    assert "aspects" in v3
    assert list(v3["aspects"]) == ["kanon-sdd"]
    assert v3["aspects"]["kanon-sdd"]["depth"] == 2
    assert v3["aspects"]["kanon-sdd"]["enabled_at"] == "2026-04-25T00:00:00+00:00"


def test_migrate_legacy_config_v3_is_idempotent_no_op() -> None:
    """A config already in v3 (namespaced keys) returns unchanged — no rewrite."""
    from kanon._scaffold import _migrate_legacy_config

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
    from kanon._scaffold import _migrate_legacy_config

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

    from kanon._scaffold import _migrate_legacy_config

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


def test_upgrade_v1_legacy_round_trip_preserves_user_content(tmp_path: Path) -> None:
    """End-to-end: a v1-shaped config + AGENTS.md user prose survives upgrade
    intact; resulting config is v3 with `kanon-sdd`.
    """
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    # Hand-rewrite to v1 shape.
    (target / ".kanon" / "config.yaml").write_text(
        yaml.safe_dump({"kit_version": "0.1.0a1", "tier": 2}, sort_keys=False),
        encoding="utf-8",
    )
    # Add user-authored prose outside markers (must survive).
    agents_path = target / "AGENTS.md"
    agents_path.write_text(
        agents_path.read_text(encoding="utf-8")
        + "\n## My private notes\nDo not lose me.\n",
        encoding="utf-8",
    )
    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "tier" not in config
    assert config["aspects"]["kanon-sdd"]["depth"] == 2
    assert "## My private notes" in agents_path.read_text(encoding="utf-8")
    assert "Do not lose me." in agents_path.read_text(encoding="utf-8")


# --- ADR-0028 / Phase 3: project-aspects (T23, T24, T25, T26) ---


_PROJECT_ASPECT_MIN_MANIFEST = (
    "stability: experimental\n"
    "depth-range: [0, 1]\n"
    "default-depth: 1\n"
    "requires: []\n"
    "depth-0:\n"
    "  files: []\n"
    "  protocols: []\n"
    "  sections: []\n"
    "depth-1:\n"
    "  files: []\n"
    "  protocols: []\n"
    "  sections: []\n"
)


def _stage_project_aspect(target: Path, name: str, manifest_text: str) -> Path:
    """Drop a project-aspect manifest at <target>/.kanon/aspects/<name>/manifest.yaml."""
    aspect_dir = target / ".kanon" / "aspects" / name
    aspect_dir.mkdir(parents=True, exist_ok=True)
    (aspect_dir / "manifest.yaml").write_text(manifest_text, encoding="utf-8")
    return aspect_dir


def test_project_aspect_lifecycle_list_info_add_remove(tmp_path: Path) -> None:
    """A project-aspect under .kanon/aspects/project-foo/ participates in
    `aspect list --target`, `aspect info --target`, `aspect add`, and
    `aspect remove` (per ADR-0028 / project-aspects spec INV-1)."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    _stage_project_aspect(target, "project-auth-policy", _PROJECT_ASPECT_MIN_MANIFEST)

    listed = runner.invoke(main, ["aspect", "list", "--target", str(target)])
    assert listed.exit_code == 0, listed.output
    assert "project-auth-policy" in listed.output

    info = runner.invoke(
        main, ["aspect", "info", "project-auth-policy", "--target", str(target)]
    )
    assert info.exit_code == 0, info.output
    assert "Aspect: project-auth-policy" in info.output
    assert "Stability:     experimental" in info.output

    add = runner.invoke(main, ["aspect", "add", str(target), "project-auth-policy"])
    assert add.exit_code == 0, add.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "project-auth-policy" in config["aspects"]
    assert config["aspects"]["project-auth-policy"]["depth"] == 1

    rem = runner.invoke(main, ["aspect", "remove", str(target), "project-auth-policy"])
    assert rem.exit_code == 0, rem.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "project-auth-policy" not in config["aspects"]


def test_project_aspect_kanon_namespace_in_consumer_dir_rejected(tmp_path: Path) -> None:
    """A directory under .kanon/aspects/ may only declare `project-` aspects.
    A `kanon-` namespaced directory there is rejected at load time with a
    single-line error naming the offending path and the namespace-ownership rule
    (ADR-0028 / project-aspects spec INV-4)."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    _stage_project_aspect(target, "kanon-misnamed", _PROJECT_ASPECT_MIN_MANIFEST)

    # Verify surfaces the namespace-ownership error rather than crashing.
    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code != 0, result.output
    assert "namespace ownership" in result.output
    assert "kanon-misnamed" in result.output


def test_project_aspect_cross_source_path_collision_raises(tmp_path: Path) -> None:
    """A project-aspect that scaffolds the same `files/` path as a kit-aspect
    raises a ClickException at scaffold time (`_build_bundle` runtime guard,
    project-aspects spec INV-6 / ADR-0028)."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "2"])

    # Stage a project-aspect whose depth-1.files declares the same path
    # that kanon-sdd already scaffolds at depth-2 (`docs/specs/_template.md`).
    aspect_dir = _stage_project_aspect(
        target,
        "project-collide",
        "stability: experimental\n"
        "depth-range: [0, 1]\n"
        "default-depth: 1\n"
        "depth-0:\n"
        "  files: []\n"
        "  protocols: []\n"
        "  sections: []\n"
        "depth-1:\n"
        "  files: [docs/specs/_template.md]\n"
        "  protocols: []\n"
        "  sections: []\n",
    )
    files_dir = aspect_dir / "files" / "docs" / "specs"
    files_dir.mkdir(parents=True)
    (files_dir / "_template.md").write_text(
        "project's competing _template.md\n", encoding="utf-8"
    )

    add = runner.invoke(main, ["aspect", "add", str(target), "project-collide"])
    assert add.exit_code != 0, add.output
    # Error names both colliding aspects and the path.
    assert "Cross-source scaffold collision" in add.output
    assert "kanon-sdd" in add.output
    assert "project-collide" in add.output
    assert "docs/specs/_template.md" in add.output


def test_project_aspect_capability_substitutes_kit_capability_requirement() -> None:
    """A project-aspect's `provides:` capability satisfies a kit-aspect's
    1-token capability `requires:` predicate (project-aspects spec INV-8 /
    ADR-0028 source-neutral substitutability)."""
    from kanon.cli import _check_requires

    # Synthetic registry: kit-side `kanon-foo` requires `planning-discipline`
    # in capability-presence form (1-token); `project-lean-sdd` provides it.
    top = {
        "aspects": {
            "kanon-foo": {
                "stability": "experimental",
                "depth-range": [0, 1],
                "default-depth": 1,
                "requires": ["planning-discipline"],
            },
            "project-lean-sdd": {
                "stability": "experimental",
                "depth-range": [0, 1],
                "default-depth": 1,
                "requires": [],
                "provides": ["planning-discipline"],
            },
        }
    }
    proposed_at_1 = {"kanon-foo": 1, "project-lean-sdd": 1}
    err_at_1 = _check_requires("kanon-foo", proposed_at_1, top)
    assert err_at_1 is None, (
        f"project-aspect's capability did not satisfy kit-aspect's predicate: {err_at_1}"
    )

    # When the project-aspect supplier is at depth 0, the requirement is unmet.
    proposed_at_0 = {"kanon-foo": 1, "project-lean-sdd": 0}
    err_at_0 = _check_requires("kanon-foo", proposed_at_0, top)
    assert err_at_0 is not None
    assert "planning-discipline" in err_at_0
