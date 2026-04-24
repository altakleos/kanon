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
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "worktrees", "1"])
    assert result.exit_code == 0, result.output

    # Step 3: config records worktrees
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text(encoding="utf-8"))
    assert config["aspects"]["worktrees"]["depth"] == 1

    # Step 4: protocol file exists
    assert (target / ".kanon" / "protocols" / "worktrees" / "worktree-lifecycle.md").is_file()

    # Step 5: AGENTS.md references worktrees
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "worktree" in agents.lower()

    # Step 6: promote to depth 2
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "worktrees", "2"])
    assert result.exit_code == 0, result.output

    # Steps 7-9: scripts exist
    assert (target / "scripts" / "worktree-setup.sh").is_file()
    assert (target / "scripts" / "worktree-teardown.sh").is_file()
    assert (target / "scripts" / "worktree-status.sh").is_file()

    # Step 10: config updated
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text(encoding="utf-8"))
    assert config["aspects"]["worktrees"]["depth"] == 2

    # Step 11: demote to depth 0
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "worktrees", "0"])
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
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "worktrees", "2"])
    assert result.exit_code == 0, result.output

    # Step 3: aspect list shows both registered aspects
    result = runner.invoke(main, ["aspect", "list"])
    assert result.exit_code == 0, result.output
    assert "sdd" in result.output
    assert "worktrees" in result.output

    # Steps 4-5: aspect info for each
    result = runner.invoke(main, ["aspect", "info", "sdd"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(main, ["aspect", "info", "worktrees"])
    assert result.exit_code == 0, result.output

    # Step 6: config records both aspects
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text(encoding="utf-8"))
    assert "sdd" in config["aspects"]
    assert "worktrees" in config["aspects"]

    # Step 7: promote sdd to depth 3
    result = runner.invoke(main, ["tier", "set", str(target), "3"])
    assert result.exit_code == 0, result.output

    # Step 8: config reflects new sdd depth
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text(encoding="utf-8"))
    assert config["aspects"]["sdd"]["depth"] == 3
    assert config["aspects"]["worktrees"]["depth"] == 2

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
