"""Tests for CLI commands: graph impact and gates list."""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from kanon_core.cli import main


def test_graph_impact_nonexistent_slug(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(main, ["init", str(tmp_path), "--profile", "solo"])
    result = runner.invoke(main, ["graph", "impact", "nonexistent-slug-xyz", "--target", str(tmp_path)])
    assert result.exit_code != 0


def test_gates_list_valid_project(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(main, ["init", str(tmp_path), "--profile", "solo"])
    result = runner.invoke(main, ["gates", "list", str(tmp_path)])
    assert result.exit_code == 0
    # Output contains a JSON array starting on its own line
    lines = result.output.split("\n")
    json_start = next(i for i, line in enumerate(lines) if line.strip() == "[")
    parsed = json.loads("\n".join(lines[json_start:]))
    assert isinstance(parsed, list)
