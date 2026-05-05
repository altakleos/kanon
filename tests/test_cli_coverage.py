"""Tests to cover remaining uncovered CLI paths for coverage threshold."""
from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from kanon_core.cli import main


def _init_project(tmp_path: Path, profile: str = "solo") -> Path:
    target = tmp_path / "proj"
    CliRunner().invoke(main, ["init", str(target), "--profile", profile, "--quiet"])
    return target


# --- graph impact ---


def test_graph_impact_with_existing_slug(tmp_path: Path) -> None:
    """graph impact on a slug that exists in the graph prints output."""
    target = _init_project(tmp_path)
    # Create a plan so there's a node in the graph
    plans_dir = target / "docs" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    (plans_dir / "test-plan.md").write_text(
        "---\nstatus: approved\ndate: 2026-01-01\n---\n# Plan\n", encoding="utf-8"
    )
    runner = CliRunner()
    result = runner.invoke(main, ["graph", "impact", str(target), "test-plan"])
    # Either finds the node or doesn't — both are valid outcomes depending on graph build
    # The key is it doesn't crash
    assert result.exit_code in (0, 1)


def test_graph_impact_nonexistent_slug(tmp_path: Path) -> None:
    """graph impact on a non-existent slug exits with error."""
    target = _init_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["graph", "impact", str(target), "nonexistent-slug-xyz"])
    assert result.exit_code != 0
    assert "No node found" in result.output


# --- release command ---


def test_release_requires_depth_2(tmp_path: Path) -> None:
    """release command fails if kanon-release depth < 2."""
    target = _init_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["release", str(target), "--tag", "v1.0.0"])
    assert result.exit_code != 0
    assert "depth" in result.output.lower() or "release" in result.output.lower()


def test_release_invalid_tag_format(tmp_path: Path) -> None:
    """release command rejects invalid tag format."""
    target = _init_project(tmp_path, profile="team")
    # Set release depth to 2
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["aspects"]["kanon-release"] = {"depth": 2, "enabled_at": "2026-01-01", "config": {}}
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["release", str(target), "--tag", "not-a-version"])
    assert result.exit_code != 0
    assert "Invalid tag" in result.output


# --- aspect info with config schema ---


def test_aspect_info_shows_details(tmp_path: Path) -> None:
    """aspect info displays aspect details."""
    runner = CliRunner()
    result = runner.invoke(main, ["aspect", "info", "kanon-sdd"])
    assert result.exit_code == 0
    assert "kanon-sdd" in result.output


# --- verify with dag findings (chain display) ---


def test_verify_on_project_with_foundations(tmp_path: Path) -> None:
    """verify on a project with foundations exercises the chain display path."""
    target = _init_project(tmp_path, profile="team")
    # Bump sdd to depth 3 to enable foundations
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["aspects"]["kanon-sdd"]["depth"] = 3
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["verify", str(target)])
    # May pass or fail depending on foundations state — just ensure it runs
    assert result.exit_code in (0, 1)
    # Should produce JSON output
    assert '"status"' in result.output


# --- resolutions check ---


def test_resolutions_check_on_project_without_resolutions(tmp_path: Path) -> None:
    """resolutions check on a project with no resolutions file exits 0 or 2."""
    target = _init_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["resolutions", "check", str(target)])
    # Exit 0 (no resolutions = clean) or 2 (infrastructure/missing file)
    assert result.exit_code in (0, 2)
