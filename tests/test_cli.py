"""Tests for the kanon CLI: init, upgrade, verify, tier set.

Includes tier-migration round-trip smoke: 0 → 1 → 2 → 3 → 2 → 1 → 0
preserves user-authored files and verify stays OK at every step.
"""

from __future__ import annotations

import json
from pathlib import Path

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
    assert config["tier"] == tier
    assert config["kit_version"] == __version__
    assert "tier_set_at" in config


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
    assert report["tier"] == tier


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
            # But every non-marker line from the original must still be present.
            new_content = p.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "<!-- kanon:" in line or not line.strip():
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
    text = text.replace("<!-- kanon:begin:plan-before-build -->", "")
    text = text.replace("<!-- kanon:end:plan-before-build -->", "")
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
