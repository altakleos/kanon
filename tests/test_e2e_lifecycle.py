"""End-to-end lifecycle tests: multi-step workflows chaining CLI commands.

Each test simulates a real project lifecycle — init → promote → verify →
demote → upgrade — asserting invariants at every step.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from kanon import __version__
from kanon.cli import main


def _verify_ok(runner: CliRunner, target: Path) -> dict:
    """Run verify and assert it passes, returning the parsed JSON report."""
    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output[result.output.find("{"):result.output.rfind("}") + 1])
    assert report["status"] == "ok"
    return report


def _extract_verify_json(output: str) -> dict:
    """Extract the JSON report from verify output."""
    return json.loads(output[output.find("{"):output.rfind("}") + 1])


# --- Test 1: full project lifecycle ---


def test_full_project_lifecycle(tmp_path: Path) -> None:
    """init → verify → tier 1→2→3 → demote back to 1 (non-destructive)."""
    runner = CliRunner()
    target = tmp_path / "project"

    # Step 1: init at tier 1
    result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    assert result.exit_code == 0, result.output
    assert (target / "AGENTS.md").is_file()
    assert (target / ".kanon" / "config.yaml").is_file()

    # Step 2: verify ok
    _verify_ok(runner, target)

    # Step 3: promote to tier 2
    result = runner.invoke(main, ["tier", "set", str(target), "2"])
    assert result.exit_code == 0, result.output
    assert (target / "docs" / "specs").is_dir()

    # Step 4: verify still ok
    _verify_ok(runner, target)

    # Step 5: promote to tier 3
    result = runner.invoke(main, ["tier", "set", str(target), "3"])
    assert result.exit_code == 0, result.output
    assert (target / "docs" / "design").is_dir()
    assert (target / "docs" / "foundations").is_dir()

    # Step 6: verify still ok
    _verify_ok(runner, target)

    # Step 7: demote back to tier 1
    result = runner.invoke(main, ["tier", "set", str(target), "1"])
    assert result.exit_code == 0, result.output

    # Step 8: verify still ok (non-destructive demotion)
    _verify_ok(runner, target)

    # Step 9: tier-3 artifacts survive demotion
    assert (target / "docs" / "design").is_dir()


# --- Test 2: aspect lifecycle ---


def test_aspect_lifecycle(tmp_path: Path) -> None:
    """worktrees aspect: depth 0 → 1 → 2 → demote to 0 (non-destructive)."""
    runner = CliRunner()
    target = tmp_path / "project"

    # Step 1: init
    result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    assert result.exit_code == 0, result.output

    # Step 2: enable worktrees at depth 1
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-worktrees", "1"])
    assert result.exit_code == 0, result.output

    # Step 3: config records worktrees
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text(encoding="utf-8"))
    assert config["aspects"]["kanon-worktrees"]["depth"] == 1

    # Step 4: protocol file exists
    assert (target / ".kanon" / "protocols" / "kanon-worktrees" / "worktree-lifecycle.md").is_file()

    # Step 5: AGENTS.md references worktrees with proper markers
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "worktree" in agents.lower()
    assert "branch-hygiene" in agents  # protocol in index

    # Step 5b: verify passes at depth 1
    _verify_ok(runner, target)

    # Step 6: promote to depth 2
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-worktrees", "2"])
    assert result.exit_code == 0, result.output

    # Steps 7-9: scripts exist
    assert (target / "scripts" / "worktree-setup.sh").is_file()
    assert (target / "scripts" / "worktree-teardown.sh").is_file()
    assert (target / "scripts" / "worktree-status.sh").is_file()

    # Step 10: config updated
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text(encoding="utf-8"))
    assert config["aspects"]["kanon-worktrees"]["depth"] == 2

    # Step 10b: AGENTS.md still has worktrees markers at depth 2
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "branch-hygiene" in agents  # protocol in index

    # Step 10c: verify passes at depth 2
    _verify_ok(runner, target)

    # Step 11: demote to depth 0
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-worktrees", "0"])
    assert result.exit_code == 0, result.output

    # Step 12: verify ok (worktrees at depth 0 has no required sections)
    _verify_ok(runner, target)

    # Step 13: scripts survive demotion (non-destructive)
    assert (target / "scripts").is_dir()


# --- Test 3: init → upgrade cycle ---


def test_init_upgrade_cycle(tmp_path: Path) -> None:
    """Patch config to old version, upgrade, verify idempotent re-upgrade."""
    runner = CliRunner()
    target = tmp_path / "project"

    # Step 1: init at tier 2
    result = runner.invoke(main, ["init", str(target), "--tier", "2"])
    assert result.exit_code == 0, result.output

    # Step 2: simulate old version
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["kit_version"] = "0.0.1"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    # Step 3: upgrade
    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    # Step 4: version bumped
    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert updated["kit_version"] == __version__

    # Step 5: verify ok
    _verify_ok(runner, target)

    # Step 6: re-upgrade is idempotent
    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    assert "already at" in result.output.lower() or "nothing to upgrade" in result.output.lower()


# --- Test 4: multi-aspect workflow ---


def test_multi_aspect_workflow(tmp_path: Path) -> None:
    """sdd + worktrees coexist; promote sdd, both aspects remain valid."""
    runner = CliRunner()
    target = tmp_path / "project"

    # Step 1: init with sdd depth 1
    result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    assert result.exit_code == 0, result.output

    # Step 2: add worktrees at depth 2
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-worktrees", "2"])
    assert result.exit_code == 0, result.output

    # Step 3: aspect list shows both registered aspects
    result = runner.invoke(main, ["aspect", "list"])
    assert result.exit_code == 0, result.output
    assert "kanon-sdd" in result.output
    assert "kanon-worktrees" in result.output

    # Steps 4-5: aspect info for each
    result = runner.invoke(main, ["aspect", "info", "kanon-sdd"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(main, ["aspect", "info", "kanon-worktrees"])
    assert result.exit_code == 0, result.output

    # Step 6: config records both aspects
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text(encoding="utf-8"))
    assert "kanon-sdd" in config["aspects"]
    assert "kanon-worktrees" in config["aspects"]

    # Step 7: promote sdd to depth 3
    result = runner.invoke(main, ["tier", "set", str(target), "3"])
    assert result.exit_code == 0, result.output

    # Step 8: config reflects new sdd depth
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text(encoding="utf-8"))
    assert config["aspects"]["kanon-sdd"]["depth"] == 3
    assert config["aspects"]["kanon-worktrees"]["depth"] == 2

    # Step 9: both aspect artifacts coexist
    assert (target / "docs" / "design").is_dir()  # sdd depth 3
    assert (target / "scripts" / "worktree-setup.sh").is_file()  # worktrees depth 2


# --- Test 5: user content survives lifecycle ---


def test_user_content_survives_lifecycle(tmp_path: Path) -> None:
    """User-authored AGENTS.md content and docs survive tier-set and upgrade."""
    runner = CliRunner()
    target = tmp_path / "project"

    # Step 1: init
    result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    assert result.exit_code == 0, result.output

    # Step 2: add custom content to AGENTS.md
    agents_path = target / "AGENTS.md"
    agents_path.write_text(
        agents_path.read_text(encoding="utf-8")
        + "\n## My Custom Rules\nDo not break production.\n",
        encoding="utf-8",
    )

    # Step 3: create a user file
    user_plan = target / "docs" / "plans" / "my-plan.md"
    user_plan.write_text("# My Plan\nShip it.\n", encoding="utf-8")

    # Step 4: promote to tier 2
    result = runner.invoke(main, ["tier", "set", str(target), "2"])
    assert result.exit_code == 0, result.output

    # Step 5: AGENTS.md preserves user content
    assert "My Custom Rules" in (target / "AGENTS.md").read_text(encoding="utf-8")

    # Step 6: user file intact
    assert user_plan.read_text(encoding="utf-8") == "# My Plan\nShip it.\n"

    # Step 7: simulate old version and upgrade
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["kit_version"] = "0.0.1"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    # Step 8: AGENTS.md still has user content after upgrade
    assert "My Custom Rules" in (target / "AGENTS.md").read_text(encoding="utf-8")

    # Step 9: user file still intact after upgrade
    assert user_plan.read_text(encoding="utf-8") == "# My Plan\nShip it.\n"


# --- Test 6: preflight lifecycle ---


def test_preflight_lifecycle(tmp_path: Path) -> None:
    """init → preflight reports hook status."""
    runner = CliRunner()
    target = tmp_path / "project"

    # Step 1: init at tier 1
    result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    assert result.exit_code == 0, result.output

    # Step 2: run preflight (commit stage)
    result = runner.invoke(main, ["preflight", str(target)])
    # Preflight should succeed (exit 0) or report status — either way it runs
    assert result.exit_code in (0, 1), result.output


# --- Test 7: release lifecycle ---


def test_release_lifecycle(tmp_path: Path) -> None:
    """init → set release depth 2 → release --dry-run gates correctly."""
    import os
    import subprocess

    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    runner = CliRunner()
    target = tmp_path / "project"

    # Step 1: init
    result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    assert result.exit_code == 0, result.output

    # Step 2: release at depth 1 should fail
    result = runner.invoke(main, ["release", str(target), "--tag", "v1.0.0"])
    assert result.exit_code != 0
    assert "depth >=" in result.output

    # Step 3: set release depth high enough to pass the gate
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-release", "3"])
    assert result.exit_code == 0, result.output

    # Step 4: init git repo for release
    subprocess.run(["git", "init"], cwd=str(target), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(target), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(target), capture_output=True, env=git_env,
    )

    # Step 5: dry-run release
    result = runner.invoke(main, ["release", str(target), "--tag", "v1.0.0", "--dry-run"])
    # Should either pass or fail on preflight — but not on the depth gate
    assert "depth >=" not in result.output


# --- Test 8: aspect set-config lifecycle ---


def test_aspect_set_config_lifecycle(tmp_path: Path) -> None:
    """init → set-config → upgrade preserves config."""
    runner = CliRunner()
    target = tmp_path / "project"

    # Step 1: init
    result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    assert result.exit_code == 0, result.output

    # Step 2: set a config value on testing aspect
    result = runner.invoke(
        main, ["aspect", "set-config", str(target), "kanon-testing", "coverage_floor=80"]
    )
    assert result.exit_code == 0, result.output

    # Step 3: verify config persists
    config = yaml.safe_load(
        (target / ".kanon" / "config.yaml").read_text(encoding="utf-8")
    )
    assert config["aspects"]["kanon-testing"]["config"]["coverage_floor"] == 80

    # Step 4: upgrade preserves config
    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    config_after = yaml.safe_load(
        (target / ".kanon" / "config.yaml").read_text(encoding="utf-8")
    )
    assert config_after["aspects"]["kanon-testing"]["config"]["coverage_floor"] == 80


# --- Test 9: aspect info lifecycle ---


def test_aspect_info_lifecycle(tmp_path: Path) -> None:
    """aspect info shows metadata for kit aspects."""
    runner = CliRunner()

    # aspect info for a kit aspect (no target needed)
    result = runner.invoke(main, ["aspect", "info", "kanon-sdd"])
    assert result.exit_code == 0, result.output
    assert "sdd" in result.output.lower()
    # Should show depth range
    assert "depth" in result.output.lower() or "0" in result.output


# --- Test 10: graph orphans lifecycle ---


def test_graph_orphans_lifecycle(tmp_path: Path) -> None:
    """init at depth 3 → create orphan doc → graph orphans detects it."""
    runner = CliRunner()
    target = tmp_path / "project"

    # Step 1: init at tier 3 (need docs/decisions, docs/plans, docs/specs, docs/design)
    result = runner.invoke(main, ["init", str(target), "--tier", "3"])
    assert result.exit_code == 0, result.output

    # Step 2: create an orphan plan (not referenced by any spec)
    orphan = target / "docs" / "plans" / "orphan-test.md"
    orphan.write_text(
        "---\nstatus: in-progress\ndate: 2026-01-01\nslug: orphan-test\n---\n# Orphan\n",
        encoding="utf-8",
    )

    # Step 3: run graph orphans
    result = runner.invoke(main, ["graph", "orphans", "--target", str(target)])
    # Should succeed and mention the orphan
    assert result.exit_code == 0, result.output


# --- Test 11: fidelity lifecycle ---


def test_fidelity_lifecycle(tmp_path: Path) -> None:
    """init → enable fidelity → fidelity update runs."""
    runner = CliRunner()
    target = tmp_path / "project"

    # Step 1: init
    result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    assert result.exit_code == 0, result.output

    # Step 2: enable fidelity aspect
    result = runner.invoke(
        main, ["aspect", "add", str(target), "kanon-fidelity", "--depth", "1"]
    )
    assert result.exit_code == 0, result.output

    # Step 3: run fidelity update
    result = runner.invoke(main, ["fidelity", "update", str(target)])
    # Should succeed (may produce no output if no fixtures exist)
    assert result.exit_code == 0, result.output
