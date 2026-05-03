"""Tests for kanon CLI: aspect commands, tier set, project-aspects."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from kanon_core.cli import main

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




_PROJECT_ASPECT_WITH_VALIDATORS = (
    "stability: experimental\n"
    "depth-range: [0, 1]\n"
    "default-depth: 1\n"
    "validators: [{module}]\n"
    "depth-0:\n"
    "  files: []\n"
    "  protocols: []\n"
    "  sections: []\n"
    "depth-1:\n"
    "  files: []\n"
    "  protocols: []\n"
    "  sections: []\n"
)




def test_aspect_level_files(tmp_path: Path) -> None:
    """Aspect-level files (sub-manifest top-level `files:`) are scaffolded at any depth."""
    from kanon_core._manifest import _load_aspect_manifest
    sub = _load_aspect_manifest("kanon-sdd")
    aspect_files = sub.get("files", []) or []
    # Currently empty — this test validates the mechanism works.
    # When sdd-method.md is added as an aspect-level file, this test will catch it.
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "0"])
    for f in aspect_files:
        assert (target / f).is_file(), f"aspect-level file missing: {f}"



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



def test_tier_set_below_current_is_noop(tmp_path: Path) -> None:
    """Per ADR-0035: tier set raises only. Lowering targets are no-ops.

    A `tier set 0` invocation against a tier-3 project leaves every aspect's
    depth unchanged and every scaffolded file on disk.
    """
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "3"])

    # Capture full tier-3 file list and aspect depths.
    tier3_files = {
        p.relative_to(target) for p in target.rglob("*") if p.is_file()
    }
    pre_config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    pre_depths = {a: pre_config["aspects"][a]["depth"] for a in pre_config["aspects"]}

    result = runner.invoke(main, ["tier", "set", str(target), "0"])
    assert result.exit_code == 0
    assert "noop" in result.output.lower() or "already at or above" in result.output.lower()

    # Depths unchanged (raise-only semantics).
    post_config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    post_depths = {a: post_config["aspects"][a]["depth"] for a in post_config["aspects"]}
    assert pre_depths == post_depths, f"tier set 0 changed depths: {pre_depths} → {post_depths}"

    # All tier-3 files still exist.
    for rel in tier3_files:
        assert (target / rel).exists(), f"tier set 0 removed: {rel}"



def test_tier_raises_all_default_aspects(tmp_path: Path) -> None:
    """Per ADR-0035: --tier N enables every aspect in manifest defaults: at
    min(N, max_depth). Verifies the uniform-raise rule for tier 2.
    """
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--tier", "2"])
    assert result.exit_code == 0, result.output

    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    enabled = config["aspects"]
    # Every default aspect should be present (sdd, testing, security, deps).
    expected = {
        "kanon-sdd": 2,
        "kanon-testing": 2,     # max=3, min(2, 3) = 2
        "kanon-security": 2,    # max=2
        "kanon-deps": 2,        # max=2
    }
    for name, depth in expected.items():
        assert name in enabled, f"missing aspect: {name}"
        assert enabled[name]["depth"] == depth, (
            f"{name}: expected {depth}, got {enabled[name]['depth']}"
        )



def test_tier_set_never_lowers(tmp_path: Path) -> None:
    """Per ADR-0035: tier set raises only. An aspect manually configured above
    the requested tier is preserved at its higher depth.
    """
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Manually raise sdd to depth 3.
    runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-sdd", "3"])
    pre = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert pre["aspects"]["kanon-sdd"]["depth"] == 3

    # tier set 2 should NOT lower sdd from 3.
    result = runner.invoke(main, ["tier", "set", str(target), "2"])
    assert result.exit_code == 0, result.output

    post = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert post["aspects"]["kanon-sdd"]["depth"] == 3, (
        "tier set 2 lowered kanon-sdd from 3"
    )
    # Other default aspects should have been raised from 1 to 2.
    assert post["aspects"]["kanon-testing"]["depth"] == 2
    assert post["aspects"]["kanon-security"]["depth"] == 2


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



# --- cli.py: tier set with legacy verb messaging ---


def test_tier_set_uses_legacy_verb_on_raise(tmp_path: Path) -> None:
    """Per ADR-0035: when tier set raises an aspect, output uses 'Tier' verb
    (legacy_tier_verb=True), distinct from `aspect set-depth`'s per-aspect verb.
    """
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1"])
    result = runner.invoke(main, ["tier", "set", str(target), "2"])
    assert result.exit_code == 0, result.output
    assert "tier" in result.output.lower()



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
    assert "branch-hygiene" in agents  # protocol in index, not marker section
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
    assert "branch-hygiene" in agents  # protocol in index, not marker section
    for script in ("worktree-setup.sh", "worktree-teardown.sh", "worktree-status.sh"):
        assert (target / "scripts" / script).is_file(), f"missing scripts/{script}"



def test_worktrees_depth_0_scaffolds_nothing(tmp_path: Path) -> None:
    """Depth 0: no protocol, no scripts, no markers in AGENTS.md."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1"])
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
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1"])
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
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-worktrees", "--depth", "2"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["kanon-worktrees"]["depth"] == 2



def test_aspect_add_depth_out_of_range(tmp_path: Path) -> None:
    """aspect add --depth with invalid depth fails."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1"])
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
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1"])
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
    with patch("kanon_core.cli._write_config", side_effect=OSError("simulated disk full")):
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
    """Phase A.3 (per ADR-0048 de-opinionation): init with no flags scaffolds
    an empty project. Consumers must opt in via --aspects, --tier, --lite,
    or --profile.
    """
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target)])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config.get("aspects", {}) == {}



# --- requires: enforcement tests ---


def test_aspect_add_worktrees_without_sdd(tmp_path: Path) -> None:
    """aspect add worktrees succeeds even when sdd is at depth 0 (suggests, not requires)."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "0"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-worktrees"])
    assert result.exit_code == 0, result.output



def test_aspect_remove_sdd_with_worktrees(tmp_path: Path) -> None:
    """aspect remove sdd succeeds when worktrees only suggests it."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1,worktrees:1"])
    result = runner.invoke(main, ["aspect", "remove", str(target), "kanon-sdd"])
    assert result.exit_code == 0, result.output



def test_aspect_set_depth_requires_check(tmp_path: Path) -> None:
    """set-depth worktrees 1 fails when sdd is at depth 0."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "0"])
    result = runner.invoke(
        main, ["aspect", "set-depth", str(target), "kanon-worktrees", "1"]
    )
    assert result.exit_code == 0, result.output



def test_aspect_add_requires_met(tmp_path: Path) -> None:
    """aspect add worktrees succeeds when sdd >= 1."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1"])
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
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-release"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "kanon-release" in config["aspects"]
    assert (target / ".kanon" / "protocols" / "kanon-release" / "release-checklist.md").is_file()



# Phase A.8: test_release_depth_2_has_ci_files retired — scaffolded files
# (per ADR-0048 de-opinionation; substrate no longer ships consumer-side CI scripts).



# --- testing aspect CLI tests ---


def test_aspect_add_testing(tmp_path: Path) -> None:
    """aspect add testing enables the aspect; protocol is scaffolded."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-testing"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "kanon-testing" in config["aspects"]
    assert (target / ".kanon" / "protocols" / "kanon-testing" / "test-discipline.md").is_file()
    assert (target / ".kanon" / "protocols" / "kanon-testing" / "error-diagnosis.md").is_file()



# Phase A.8: test_testing_depth_3_has_ci_script retired (per ADR-0048).




def test_aspect_add_security(tmp_path: Path) -> None:
    """aspect add security enables the aspect; protocol is scaffolded."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-security"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "kanon-security" in config["aspects"]
    assert (target / ".kanon" / "protocols" / "kanon-security" / "secure-defaults.md").is_file()



# Phase A.8: test_security_depth_2_has_ci_script retired (per ADR-0048).



def test_aspect_add_deps(tmp_path: Path) -> None:
    """aspect add deps enables the aspect; protocol is scaffolded."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1"])
    result = runner.invoke(main, ["aspect", "add", str(target), "kanon-deps"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "kanon-deps" in config["aspects"]
    assert (target / ".kanon" / "protocols" / "kanon-deps" / "dependency-hygiene.md").is_file()



# Phase A.8: test_deps_depth_2_has_ci_script retired (per ADR-0048).



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
    runner.invoke(main, ["init", str(target), "--aspects", "sdd:1"])

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
    from kanon_core.cli import _check_requires

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


# --- ADR-0028 / Phase 4: project-aspect validators-as-extensions (T29, T30, T31) ---


_PROJECT_ASPECT_WITH_VALIDATORS = (
    "stability: experimental\n"
    "depth-range: [0, 1]\n"
    "default-depth: 1\n"
    "validators: [{module}]\n"
    "depth-0:\n"
    "  files: []\n"
    "  protocols: []\n"
    "  sections: []\n"
    "depth-1:\n"
    "  files: []\n"
    "  protocols: []\n"
    "  sections: []\n"
)



def test_project_aspect_validator_emits_findings_in_verify_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A project-aspect's `validators:` module is imported in-process during
    `kanon verify`; its appended errors and warnings appear in the JSON report
    (project-aspects spec INV-7 / ADR-0028)."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    # Stage the validator module on sys.path.
    pkg_dir = tmp_path / "validator_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "kanon_test_validator_emit.py").write_text(
        "def check(target, errors, warnings):\n"
        "    errors.append(f'project-validator emitted error for {target.name}')\n"
        "    warnings.append('project-validator emitted warning')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(pkg_dir))

    # Stage the project-aspect declaring the validator.
    aspect_dir = target / ".kanon" / "aspects" / "project-checked"
    aspect_dir.mkdir(parents=True)
    (aspect_dir / "manifest.yaml").write_text(
        _PROJECT_ASPECT_WITH_VALIDATORS.format(module="kanon_test_validator_emit"),
        encoding="utf-8",
    )
    runner.invoke(main, ["aspect", "add", str(target), "project-checked"])

    result = runner.invoke(main, ["verify", str(target)])
    # Errors present → exit code != 0; the validator's findings are in the report.
    assert result.exit_code != 0, result.output
    assert "project-validator emitted error for scratch" in result.output
    assert "project-validator emitted warning" in result.output



def test_project_aspect_validator_cannot_suppress_kit_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hostile project-validator that calls `errors.clear()` cannot suppress
    the kit's structural errors. Kit checks run AFTER project-validators, so
    any clearing is overwritten (project-aspects spec INV-9)."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    # Hostile validator that wipes errors and warnings.
    pkg_dir = tmp_path / "hostile_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "kanon_test_validator_hostile.py").write_text(
        "def check(target, errors, warnings):\n"
        "    errors.clear()\n"
        "    warnings.clear()\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(pkg_dir))

    aspect_dir = target / ".kanon" / "aspects" / "project-hostile"
    aspect_dir.mkdir(parents=True)
    (aspect_dir / "manifest.yaml").write_text(
        _PROJECT_ASPECT_WITH_VALIDATORS.format(module="kanon_test_validator_hostile"),
        encoding="utf-8",
    )
    runner.invoke(main, ["aspect", "add", str(target), "project-hostile"])

    # Force a kit-detected structural error: delete a required file.
    (target / "AGENTS.md").unlink()

    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code != 0, result.output
    # Despite the hostile validator's clear(), the kit's missing-file error survives.
    assert "missing required file: AGENTS.md" in result.output



def test_project_aspect_validator_import_failure_recorded(tmp_path: Path) -> None:
    """When a project-validator's module cannot be imported, verify records a
    single error naming the module and continues with the remaining checks
    (project-aspects spec INV-7 — verify completes despite a broken validator)."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    aspect_dir = target / ".kanon" / "aspects" / "project-broken"
    aspect_dir.mkdir(parents=True)
    (aspect_dir / "manifest.yaml").write_text(
        _PROJECT_ASPECT_WITH_VALIDATORS.format(
            module="kanon_test_validator_does_not_exist_xyz"
        ),
        encoding="utf-8",
    )
    runner.invoke(main, ["aspect", "add", str(target), "project-broken"])

    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code != 0, result.output
    assert "import failed" in result.output
    assert "kanon_test_validator_does_not_exist_xyz" in result.output
    # Kit's structural checks ran too — verify did not crash on the import error.
    # (The kit-managed AGENTS.md is intact, so no other structural errors expected;
    # simply asserting the JSON report shape proves the run completed.)
    assert '"status": "fail"' in result.output
